# 🔌 Low-level API & lifecycle

`Session` handles initialization and document management. Use `LSPProcess` for
direct access to typed LSP requests and notifications.

## Low-level stdio

This example requires `pyright-langserver` on your `PATH`.

```python
import asyncio
from pathlib import Path

from lsp_types.process import LSPProcess, ProcessLaunchInfo


async def main():
    root = Path.cwd()
    process_info = ProcessLaunchInfo(cmd=["pyright-langserver", "--stdio"])

    async with LSPProcess(process_info) as process:
        await process.send.initialize({
            "processId": None,
            "rootUri": root.as_uri(),
            "capabilities": {},
        })
        await process.notify.initialized({})

        # Register before opening the document so the response is captured.
        listener = process.notify.on_publish_diagnostics(timeout=10.0)
        await process.notify.did_open_text_document({
            "textDocument": {
                "uri": (root / "example.py").as_uri(),
                "languageId": "python",
                "version": 1,
                "text": "value: int = 'hello'\n",
            }
        })
        print(await listener)


asyncio.run(main())
```

Requests require `await`. Notifications queue immediately; awaiting one also
waits for its bytes to drain to the server.

## Process lifecycle

`LSPProcess.stop()` permanently closes the process. Exiting its `async with`
block calls `stop()` automatically. Starting a stopped process, or sending
requests or notifications through it, raises `RuntimeError`. Create a new
`LSPProcess` to restart a server.

## Session lifecycle

Always call `await session.shutdown()` in a `finally` block. Shutdown rejects
new operations immediately and gives active operations up to five seconds to
finish. If any remain, it stops the server process. Otherwise, it releases the
process to the pool, or stops it when no reusable pool was supplied.

After shutdown, operational methods raise `RuntimeError`. Captured server
information and semantic-token legends remain readable.

Await document updates before shutting down. Cancelling an operation can leave
an already-queued notification flushing after the operation ends.

Generated types whose names start with `__` are internal and outside the public API.
