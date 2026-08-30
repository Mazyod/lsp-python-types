from __future__ import annotations

import asyncio
import dataclasses as dc
import itertools
import json
import logging
import os
import typing as t
from pathlib import Path

from . import methods, requests, types

CONTENT_LENGTH = "Content-Length: "
ENCODING = "utf-8"
_GRACEFUL_SHUTDOWN_TIMEOUT = 5.0
_PROCESS_EXIT_TIMEOUT = 5.0


logger = logging.getLogger("lsp-types")


@dc.dataclass(kw_only=True)
class ProcessLaunchInfo:
    cmd: list[str]
    env: dict[str, str] = dc.field(default_factory=dict)
    cwd: Path = Path(".")

    def resolved_environment(self) -> dict[str, str]:
        """Return the exact environment that should be passed to the child."""
        child_process_environment = os.environ.copy()
        child_process_environment.pop("PYTHONPATH", None)
        child_process_environment.update(self.env)
        return child_process_environment


class Error(Exception):
    def __init__(self, code: types.ErrorCodes | int, message: str) -> None:
        super().__init__(message)
        self.code = code

    def to_lsp(self) -> types.LSPObject:
        return {"code": self.code, "message": super().__str__()}

    @classmethod
    def from_lsp(cls, d: types.LSPObject) -> Error:
        try:
            code = types.ErrorCodes(d["code"])
        except ValueError:
            code = int(d["code"])

        message = t.cast(str, d["message"])
        return Error(code, message)

    def __str__(self) -> str:
        return f"{super().__str__()} ({self.code})"


async def _run_protected(coroutine: t.Coroutine[t.Any, t.Any, None]) -> None:
    """Run ``coroutine`` to completion before propagating caller cancellation.

    Cleanup must never be interrupted halfway, so the coroutine runs as its own
    task behind ``asyncio.shield``. Cancellation delivered to the caller while it
    waits is saved and re-raised once the task has finished.
    """
    cleanup_task = asyncio.create_task(coroutine)
    cancellation: asyncio.CancelledError | None = None

    while not cleanup_task.done():
        try:
            await asyncio.shield(cleanup_task)
        except asyncio.CancelledError as error:
            cancellation = error
        except BaseException:
            # Anything thrown into the caller while cleanup is still pending
            # (e.g. GeneratorExit during teardown) must propagate untouched.
            if not cleanup_task.done():
                raise
            # The cleanup task itself failed; its outcome is resolved below so a
            # caller cancellation saved earlier still wins.
            break

    if cancellation is None:
        cleanup_task.result()
        return

    # Caller cancellation outranks a cleanup failure: a cancelled caller must never
    # surface a different exception. The task outcome is still consumed so asyncio
    # never reports it as an unretrieved exception.
    if not cleanup_task.cancelled():
        failure = cleanup_task.exception()
        if failure is not None:
            logger.debug(
                "Cleanup failed while its caller was cancelled", exc_info=failure
            )
    raise cancellation


class LSPProcess:
    """
    A process manager for Language Server Protocol communication.
    Provides async/await interface for requests and notification queue for handling server messages.

    Usage:
        async with LSPProcess(process_info) as process:
            # Send request and await response
            init_result = await process.send.initialize(params)

            # Send notifications (awaiting is optional)
            await process.send.did_open_text_document(params)
            process.notify.did_change_text_document(params)

            # Process notifications from server
            async for notification in process.notifications():
                method = notification["method"]
                params = notification["params"]
                # Handle notification
    """

    def __init__(
        self,
        process_launch_info: ProcessLaunchInfo,
        *,
        resolved_environment: t.Mapping[str, str] | None = None,
    ):
        self._process_launch_info = process_launch_info
        self._resolved_environment = (
            dict(resolved_environment) if resolved_environment is not None else None
        )
        self._process: asyncio.subprocess.Process | None = None
        self._notification_listeners: list[asyncio.Queue[types.LSPObject]] = []
        self._pending_requests: dict[int | str, asyncio.Future[t.Any]] = {}
        self._request_id_gen = itertools.count(1)
        self._tasks: set[asyncio.Task[t.Any]] = set()
        self._lifecycle_lock = asyncio.Lock()
        self._stopped = False
        self._open_documents: set[str] = set()
        self._write_lock = asyncio.Lock()
        self._initialize_result: types.InitializeResult | None = None
        self._connection_closed = False

        # Maintain typed interface
        self.send = requests.RequestFunctions(self._send_request)
        self.notify = requests.NotificationFunctions(
            self._send_notification, self._on_notification
        )

    async def __aenter__(self) -> LSPProcess:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    def _lifecycle_error(self, action: str) -> RuntimeError:
        """Describe why the current lifecycle state forbids ``action``."""
        if self._stopped:
            return RuntimeError(f"LSP process has been stopped: cannot {action}")
        return RuntimeError(f"LSP process has not been started: cannot {action}")

    def _writable_stdin(self, method: str) -> asyncio.StreamWriter:
        """Return the running process's stdin, or explain why it is unusable."""
        process = self._process
        if process is None or process.stdin is None:
            raise self._lifecycle_error(f"send {method}")
        return process.stdin

    async def start(self) -> None:
        """Start the LSP server process and initialize communication."""
        async with self._lifecycle_lock:
            if self._stopped:
                raise self._lifecycle_error("restart")
            if self._process:
                raise RuntimeError("LSP process is already running: cannot start")

            child_proc_env = (
                self._process_launch_info.resolved_environment()
                if self._resolved_environment is None
                else self._resolved_environment.copy()
            )

            self._process = await asyncio.create_subprocess_exec(
                *self._process_launch_info.cmd,
                stdout=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=child_proc_env,
                cwd=self._process_launch_info.cwd,
            )

            self._track_task(asyncio.create_task(self._read_stdout()))
            self._track_task(asyncio.create_task(self._read_stderr()))

    async def stop(self) -> None:
        """Stop the LSP server and clean up resources."""
        async with self._lifecycle_lock:
            process = self._process
            if process is None:
                await self._cancel_tasks()
                self._stopped = True
                return

            await _run_protected(self._stop_process(process))

    async def _stop_process(self, process: asyncio.subprocess.Process) -> None:
        """Complete subprocess cleanup independently of caller cancellation."""
        try:
            graceful_exit_sent = await self._request_graceful_shutdown()
            if graceful_exit_sent:
                await self._wait_for_exit(process, _PROCESS_EXIT_TIMEOUT)
        finally:
            await self._terminate_and_reap(process)
            await self._close_stdin(process)
            await self._cancel_tasks()
            self._process = None
            self._stopped = True

    async def _request_graceful_shutdown(self) -> bool:
        """Ask the server to shut down without allowing it to block cleanup."""
        try:
            async with asyncio.timeout(_GRACEFUL_SHUTDOWN_TIMEOUT):
                await self.send.shutdown()
                try:
                    await self.notify.exit()
                except ConnectionError:
                    # Closing the transport immediately after `exit` is valid LSP
                    # server behavior; the notification has already been attempted.
                    logger.debug("LSP server closed while receiving exit notification")
        except TimeoutError:
            logger.warning("Graceful LSP shutdown timed out")
            return False
        except Exception as error:
            # Best effort only: the caller's `finally` reaps the subprocess either
            # way, so a server that errors on - or dies during - `shutdown` merely
            # costs us the clean exit. Cancellation is a BaseException and still
            # propagates, because it can only come from cancelling cleanup itself.
            logger.debug("Graceful LSP shutdown failed", exc_info=error)
            return False
        return True

    @staticmethod
    async def _wait_for_exit(
        process: asyncio.subprocess.Process, timeout: float
    ) -> bool:
        """Wait up to ``timeout`` seconds for a subprocess to exit."""
        if process.returncode is not None:
            return True

        try:
            async with asyncio.timeout(timeout):
                await process.wait()
        except TimeoutError:
            return False
        return True

    async def _terminate_and_reap(self, process: asyncio.subprocess.Process) -> None:
        """Escalate from terminate to kill and always wait for process exit."""
        if process.returncode is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass

        if not await self._wait_for_exit(process, _PROCESS_EXIT_TIMEOUT):
            logger.warning("LSP server did not terminate; killing process")
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.wait()

        if process.returncode not in (0, -15, -9):
            logger.warning("Server exited with return code: %d", process.returncode)

    async def _close_stdin(self, process: asyncio.subprocess.Process) -> None:
        """Close the subprocess input transport after the process has exited."""
        if process.stdin is None:
            return

        async with self._write_lock:
            process.stdin.close()
            try:
                await process.stdin.wait_closed()
            except OSError:
                pass

    def _track_task[ResultT](
        self, task: asyncio.Task[ResultT]
    ) -> asyncio.Task[ResultT]:
        """Own an internal task only while it is running."""
        self._tasks.add(task)
        task.add_done_callback(self._on_task_done)
        return task

    def _on_task_done(self, task: asyncio.Task[t.Any]) -> None:
        """Release a completed task and consume any unobserved exception."""
        self._tasks.discard(task)
        if task.cancelled():
            return

        error = task.exception()
        if error is not None:
            logger.debug("Internal LSP task failed: %s", error)

    async def _cancel_tasks(self) -> None:
        """Cancel and join every internal task still owned by this process."""
        while self._tasks:
            tasks = list(self._tasks)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self._tasks.difference_update(tasks)

    async def reset(self) -> None:
        """Reset the LSP process state for reuse."""
        # Close any open documents
        for uri in self._open_documents:
            try:
                await self.notify.did_close_text_document(
                    {"textDocument": {"uri": uri}}
                )
            except Exception as e:
                logger.warning(f"Failed to close document {uri} during reset: {e}")

        self._open_documents.clear()

        # Clear any pending requests (they should be completed or failed by now)
        for request_id, future in self._pending_requests.items():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

        # Reset request ID generator to avoid conflicts
        self._request_id_gen = itertools.count(1)

        logger.debug("LSP process reset completed")

    def track_document_open(self, uri: str) -> None:
        """Track that a document has been opened."""
        self._open_documents.add(uri)

    @property
    def is_alive(self) -> bool:
        """Whether this process can still serve LSP traffic.

        False before ``start()``, after ``stop()``, once the server subprocess has
        exited, and once the stdout reader has left the transport. The reader owns
        the only connection to the server, so its exit is the earliest reliable
        signal that the server is gone; the subprocess return code is only visible
        after the event loop reaps the child.
        """
        process = self._process
        return (
            not self._stopped
            and not self._connection_closed
            and process is not None
            and process.returncode is None
        )

    @property
    def initialize_result(self) -> types.InitializeResult | None:
        """The initialize response associated with this process."""
        return self._initialize_result

    async def _notifications(self):
        """
        An async generator for processing server notifications.

        Usage:
            async for notification in process.notifications():
                # Process notification
        """
        queue: asyncio.Queue[types.LSPObject] = asyncio.Queue()
        self._notification_listeners.append(queue)

        try:
            while True:
                yield await queue.get()
                queue.task_done()
        finally:
            self._notification_listeners.remove(queue)

    async def _send_request(self, method: str, params: types.LSPAny = None) -> t.Any:
        """Send a request to the server and await the response."""
        stdin = self._writable_stdin(method)

        request_id = next(self._request_id_gen)

        future: asyncio.Future[t.Any] = asyncio.Future()
        self._pending_requests[request_id] = future

        payload = _make_request(method, request_id, params)
        await self._send_payload(stdin, payload)

        try:
            result = await future
            if method == methods.Request.INITIALIZE:
                # Captured here rather than at the call site because the pool
                # re-leases initialized processes without re-sending `initialize`:
                # the result has to survive on the recycled object, which
                # `Session.create` reads back after `acquire`.
                self._initialize_result = t.cast(types.InitializeResult, result)
            return result
        finally:
            self._pending_requests.pop(request_id, None)

    def _send_notification(
        self, method: str, params: types.LSPAny = None
    ) -> asyncio.Task[None]:
        """Send a notification to the server."""
        stdin = self._writable_stdin(method)

        payload = _make_notification(method, params)
        return self._track_task(asyncio.create_task(self._send_payload(stdin, payload)))

    def _on_notification(
        self, method: str, timeout: float | None = None
    ) -> asyncio.Future[types.LSPAny]:
        """Wait for a specific notification from the server."""

        async def _wait_for_notification():
            async for notification in self._notifications():
                if notification["method"] == method:
                    return notification["params"]

        coroutine = _wait_for_notification()
        if timeout is not None:
            coroutine = asyncio.wait_for(coroutine, timeout)

        return self._track_task(asyncio.create_task(coroutine))

    async def _send_payload(
        self, stream: asyncio.StreamWriter, payload: types.LSPObject
    ) -> None:
        """Send a payload to the server asynchronously."""
        logger.debug("Client -> Server: %s", payload)

        body = json.dumps(
            payload, check_circular=False, ensure_ascii=False, separators=(",", ":")
        ).encode(ENCODING)
        message = (
            f"Content-Length: {len(body)}\r\n",
            "Content-Type: application/vscode-jsonrpc; charset=utf-8\r\n\r\n",
        )

        async with self._write_lock:
            stream.writelines([part.encode(ENCODING) for part in message] + [body])
            await stream.drain()

    def _server_request_result(self, method: str, params: t.Any) -> types.LSPObject:
        """Return the result for a server request, or raise ``Error``.

        This client implements no server-to-client requests, so the honest
        answer to almost everything is ``MethodNotFound``. Two exceptions earn
        a real reply because servers block on them: ty stops answering
        entirely — diagnostics, hover and completion all hang indefinitely —
        until its ``workspace/configuration`` request is answered, and an
        error response does not unblock it.

        These are not claims of support. ``[null, ...]`` means "no
        configuration for those scopes" and ``null`` acknowledges a
        registration this client will not act on. Both are only ever reached
        when the caller advertised the corresponding capability.
        """
        match method:
            case "workspace/configuration":
                items = params.get("items") if isinstance(params, dict) else None
                if not isinstance(items, list):
                    raise Error(
                        types.ErrorCodes.InvalidParams,
                        "workspace/configuration requires an 'items' array",
                    )
                # One result per requested item; the lengths must match.
                return t.cast(types.LSPObject, [None] * len(items))
            case "client/registerCapability" | "client/unregisterCapability":
                return t.cast(types.LSPObject, None)
            case _:
                raise Error(
                    types.ErrorCodes.MethodNotFound,
                    f"Unhandled server request: {method}",
                )

    async def _answer_server_request(self, payload: types.LSPObject) -> None:
        """Reply to a server-initiated request.

        JSON-RPC 2.0 requires a response to every request, and a server may
        wait forever without one. Runs as its own task: replying inline would
        take ``_write_lock`` and ``drain()`` from inside the reader, which
        would stop draining stdout.
        """
        method = t.cast(str, payload["method"])
        response: types.LSPObject = {"jsonrpc": "2.0", "id": payload["id"]}
        try:
            response["result"] = self._server_request_result(
                method, payload.get("params")
            )
        except Error as error:
            response["error"] = error.to_lsp()
        except Exception:
            # This function exists to guarantee a reply. A leaked exception
            # would be swallowed by the task-done handler and leave the server
            # waiting forever, which is the bug this whole path fixes.
            logger.exception("Failed to build a reply to server request %s", method)
            response["error"] = Error(
                types.ErrorCodes.InternalError,
                f"Failed to handle server request: {method}",
            ).to_lsp()

        try:
            await self._send_payload(self._writable_stdin(method), response)
        except (RuntimeError, ConnectionError, BrokenPipeError):
            # The process stopped between the request arriving and our reply.
            logger.debug("Could not answer server request %s", method)

    async def _read_stdout(self) -> None:
        """Read and process messages from the server's stdout."""
        try:
            while (
                self._process
                and self._process.stdout
                and not self._process.stdout.at_eof()
            ):
                # Read header
                line = await self._process.stdout.readline()
                if not line.strip():
                    continue

                content_length = 0
                if line.startswith(b"Content-Length: "):
                    content_length = int(line.split(b":")[1].strip())

                if not content_length:
                    continue

                while line and line.strip():
                    line = await self._process.stdout.readline()

                # Read message body
                body = await self._process.stdout.readexactly(content_length)
                payload = json.loads(body.strip())

                logger.debug("Server -> Client: %s", payload)

                # Handle message based on type. A server-initiated *request*
                # carries both "method" and "id", so it must be classified
                # before notifications or it would be silently swallowed.
                if "method" in payload and "id" in payload:
                    self._track_task(
                        asyncio.create_task(self._answer_server_request(payload))
                    )
                elif "method" in payload:
                    # Server notification
                    [q.put_nowait(payload) for q in self._notification_listeners]
                elif "id" in payload:
                    # Response to client request
                    request_id = payload["id"]
                    future = self._pending_requests.get(request_id)
                    if future:
                        if "result" in payload:
                            future.set_result(payload["result"])
                        elif "error" in payload:
                            future.set_exception(Error.from_lsp(payload["error"]))
                        else:
                            future.set_exception(
                                Error(
                                    types.ErrorCodes.InvalidRequest,
                                    "Invalid response",
                                )
                            )
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Client - Error reading stdout")
        finally:
            self._connection_closed = True
            # Server closed the connection (EOF, crash, or task cancel) — reject
            # any outstanding requests so callers don't await forever.
            for future in list(self._pending_requests.values()):
                if not future.done():
                    future.set_exception(
                        Error(
                            types.ErrorCodes.InternalError,
                            "LSP server closed connection before responding",
                        )
                    )

    async def _read_stderr(self) -> None:
        """Read and log messages from the server's stderr."""
        try:
            while (
                self._process
                and self._process.stderr
                and not self._process.stderr.at_eof()
            ):
                line = await self._process.stderr.readline()
                if not line:
                    continue
                logger.error(f"Server - stderr: {line.decode(ENCODING).strip()}")
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Client - Error reading stderr")


def _make_notification(method: str, params: types.LSPAny) -> types.LSPObject:
    return {"jsonrpc": "2.0", "method": method, "params": params}


def _make_request(
    method: str, request_id: int | str, params: types.LSPAny
) -> types.LSPObject:
    return {"jsonrpc": "2.0", "method": method, "id": request_id, "params": params}
