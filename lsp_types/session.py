import asyncio
import dataclasses as dc
import itertools
import json
import logging
import os
from typing import Any, Mapping

import lsp_types

StringDict = dict[str, Any]
PayloadLike = list[StringDict] | StringDict | Mapping[str, Any] | None
CONTENT_LENGTH = "Content-Length: "
ENCODING = "utf-8"


logger = logging.getLogger("lsp-types")


@dc.dataclass(kw_only=True)
class ProcessLaunchInfo:
    cmd: list[str]
    env: dict[str, str] = dc.field(default_factory=dict)
    cwd: str = os.getcwd()


class Error(Exception):
    def __init__(self, code: lsp_types.ErrorCodes, message: str) -> None:
        super().__init__(message)
        self.code = code

    def to_lsp(self) -> StringDict:
        return {"code": self.code, "message": super().__str__()}

    @classmethod
    def from_lsp(cls, d: StringDict) -> "Error":
        return Error(d["code"], d["message"])

    def __str__(self) -> str:
        return f"{super().__str__()} ({self.code})"


class LSPSession:
    """
    A session manager for Language Server Protocol communication.
    Provides async/await interface for requests and notification queue for handling server messages.

    Usage:
        async with LSPSession(process_info) as session:
            # Send request and await response
            init_result = await session.send.initialize(params)

            # Send notifications (awaiting is optional)
            await session.send.did_open_text_document(params)
            session.notify.did_change_text_document(params)

            # Process notifications from server
            async for notification in session.notifications():
                method = notification["method"]
                params = notification["params"]
                # Handle notification
    """

    def __init__(self, process_launch_info: ProcessLaunchInfo):
        self.process_launch_info = process_launch_info
        self.process: asyncio.subprocess.Process | None = None
        self._notification_queue: asyncio.Queue[StringDict] = asyncio.Queue()
        self._pending_requests: dict[int | str, asyncio.Future[Any]] = {}
        self._request_id_gen = itertools.count(1)
        self._tasks: list[asyncio.Task] = []
        self._shutdown = False

        # Maintain typed interface
        self.send = lsp_types.Request(self._send_request)
        self.notify = lsp_types.Notification(self._send_notification)

    async def __aenter__(self) -> "LSPSession":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    async def start(self) -> None:
        """Start the LSP server process and initialize communication."""
        child_proc_env = os.environ.copy()
        child_proc_env.update(self.process_launch_info.env)

        self.process = await asyncio.create_subprocess_exec(
            *self.process_launch_info.cmd,
            stdout=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=child_proc_env,
            cwd=self.process_launch_info.cwd,
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

        if self.process:
            try:
                return_code = await asyncio.wait_for(self.process.wait(), timeout=5.0)
                if return_code != 0:
                    logging.warning("Server exited with return code: %d", return_code)
            except asyncio.TimeoutError:
                try:
                    self.process.kill()
                except ProcessLookupError:
                    pass
            self.process = None

    async def notifications(self):
        """
        An async generator for processing server notifications.

        Usage:
            async for notification in session.notifications():
                # Process notification
        """
        while True:
            yield await self._notification_queue.get()
            self._notification_queue.task_done()

    async def _send_request(self, method: str, params: Mapping | None = None) -> Any:
        """Send a request to the server and await the response."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("LSP process not available")

        request_id = next(self._request_id_gen)

        future: asyncio.Future[Any] = asyncio.Future()
        self._pending_requests[request_id] = future

        payload = make_request(method, request_id, params)
        await self._send_payload(self.process.stdin, payload)

        try:
            return await future
        finally:
            self._pending_requests.pop(request_id, None)

    def _send_notification(
        self, method: str, params: Mapping | None = None
    ) -> asyncio.Task[None]:
        """Send a notification to the server."""
        if not self.process or not self.process.stdin:
            logging.warning("LSP process not available: [%s]", method)
            return asyncio.create_task(asyncio.sleep(0))

        payload = make_notification(method, params)
        task = asyncio.create_task(self._send_payload(self.process.stdin, payload))
        self._tasks.append(task)

        return task

    @staticmethod
    async def _send_payload(stream: asyncio.StreamWriter, payload: StringDict) -> None:
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
                self.process
                and self.process.stdout
                and not self.process.stdout.at_eof()
            ):
                # Read header
                line = await self.process.stdout.readline()
                if not line.strip():
                    continue

                content_length = 0
                if line.startswith(b"Content-Length: "):
                    content_length = int(line.split(b":")[1].strip())

                if not content_length:
                    continue

                while line and line.strip():
                    line = await self.process.stdout.readline()

                # Read message body
                body = await self.process.stdout.readexactly(content_length)
                payload = json.loads(body.strip())

                logger.debug("Server -> Client: %s", payload)

                # Handle message based on type
                if "method" in payload:
                    # Server notification
                    await self._notification_queue.put(payload)
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
                                    lsp_types.ErrorCodes.InvalidRequest,
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
                self.process
                and self.process.stderr
                and not self.process.stderr.at_eof()
            ):
                line = await self.process.stderr.readline()
                if not line:
                    continue
                logger.error(f"Server - stderr: {line.decode(ENCODING).strip()}")
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Client - Error reading stderr")


def make_notification(method: str, params: PayloadLike) -> StringDict:
    return {"jsonrpc": "2.0", "method": method, "params": params}


def make_request(method: str, request_id: int | str, params: PayloadLike) -> StringDict:
    return {"jsonrpc": "2.0", "method": method, "id": request_id, "params": params}
