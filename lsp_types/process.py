import asyncio
import dataclasses as dc
import itertools
import json
import logging
import os
import typing as t
from pathlib import Path

from . import requests, types

CONTENT_LENGTH = "Content-Length: "
ENCODING = "utf-8"


logger = logging.getLogger("lsp-types")


@dc.dataclass(kw_only=True)
class ProcessLaunchInfo:
    cmd: list[str]
    env: dict[str, str] = dc.field(default_factory=dict)
    cwd: Path = Path(".")


class Error(Exception):
    def __init__(self, code: types.ErrorCodes, message: str) -> None:
        super().__init__(message)
        self.code = code

    def to_lsp(self) -> types.LSPObject:
        return {"code": self.code, "message": super().__str__()}

    @classmethod
    def from_lsp(cls, d: types.LSPObject) -> "Error":
        code = types.ErrorCodes(d["code"])
        message = t.cast(str, d["message"])
        return Error(code, message)

    def __str__(self) -> str:
        return f"{super().__str__()} ({self.code})"


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

    def __init__(self, process_launch_info: ProcessLaunchInfo):
        self._process_launch_info = process_launch_info
        self._process: asyncio.subprocess.Process | None = None
        self._notification_listeners: list[asyncio.Queue[types.LSPObject]] = []
        self._pending_requests: dict[int | str, asyncio.Future[t.Any]] = {}
        self._request_id_gen = itertools.count(1)
        self._tasks: list[asyncio.Task] = []
        self._shutdown = False
        self._open_documents: set[str] = set()

        # Maintain typed interface
        self.send = requests.RequestFunctions(self._send_request)
        self.notify = requests.NotificationFunctions(
            self._send_notification, self._on_notification
        )

    async def __aenter__(self) -> "LSPProcess":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    async def start(self) -> None:
        """Start the LSP server process and initialize communication."""
        if self._process:
            raise RuntimeError("LSP process already started")

        child_proc_env = os.environ.copy()
        child_proc_env.pop("PYTHONPATH", None)
        child_proc_env.update(self._process_launch_info.env)

        self._process = await asyncio.create_subprocess_exec(
            *self._process_launch_info.cmd,
            stdout=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=child_proc_env,
            cwd=self._process_launch_info.cwd,
        )

        self._tasks.extend(
            [
                asyncio.create_task(self._read_stdout()),
                asyncio.create_task(self._read_stderr()),
            ]
        )

    async def stop(self) -> None:
        """Stop the LSP server and clean up resources."""
        if not self._shutdown:
            try:
                await self.send.shutdown()
                await self.notify.exit()
            except ConnectionResetError:
                pass  # Server already closed

            self._shutdown = True

        for task in self._tasks:
            task.cancel()

        if self._process:
            try:
                self._process.terminate()
                return_code = await asyncio.wait_for(self._process.wait(), timeout=5.0)
                if return_code not in (0, -15):
                    logger.warning("Server exited with return code: %d", return_code)
            except asyncio.TimeoutError:
                try:
                    self._process.kill()
                except ProcessLookupError:
                    pass
            self._process = None

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
        if not self._process or not self._process.stdin:
            raise RuntimeError("LSP process not available")

        request_id = next(self._request_id_gen)

        future: asyncio.Future[t.Any] = asyncio.Future()
        self._pending_requests[request_id] = future

        payload = _make_request(method, request_id, params)
        await self._send_payload(self._process.stdin, payload)

        try:
            return await future
        finally:
            self._pending_requests.pop(request_id, None)

    def _send_notification(
        self, method: str, params: types.LSPAny = None
    ) -> asyncio.Task[None]:
        """Send a notification to the server."""
        if not self._process or not self._process.stdin:
            logger.warning("LSP process not available: [%s]", method)
            return asyncio.create_task(asyncio.sleep(0))

        payload = _make_notification(method, params)
        task = asyncio.create_task(self._send_payload(self._process.stdin, payload))
        self._tasks.append(task)

        return task

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

        wait_task = asyncio.create_task(coroutine)
        self._tasks.append(wait_task)
        wait_task.add_done_callback(self._tasks.remove)

        return wait_task

    @staticmethod
    async def _send_payload(
        stream: asyncio.StreamWriter, payload: types.LSPObject
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

        # TODO: Maybe use a lock to avoid interleaving messages?
        stream.writelines([part.encode(ENCODING) for part in message] + [body])
        await stream.drain()

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

                # Handle message based on type
                if "method" in payload:
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
