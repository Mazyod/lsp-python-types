# Usage details

## Low-level stdio

> [!TIP]
> Recommend using [basedpyright](https://github.com/DetachHead/basedpyright) for extended features.

```python
from lsp_types.process import LSPProcess, ProcessLaunchInfo

process_info = ProcessLaunchInfo(cmd=[
    "pyright-langserver", "--stdio"
])

async with LSPProcess(process_info) as process:
    # Initialize the process
    ...

    # Grab a typed listener
    diagnostics_listener = process.notify.on_publish_diagnostics(timeout=1.0)

    # Send a notification (`await` is optional. It ensures messages have been drained)
    await process.notify.did_open_text_document(...)

    # Wait for diagnostics to come in
    diagnostics = await diagnostics_listener
```

`LSPProcess.stop()` is terminal — including the implicit stop() when the `async with`
block exits. Calling `start()` on a stopped process raises `RuntimeError` instead
of relaunching the server, and requests and notifications sent through it raise
`RuntimeError` too (notifications are no longer dropped with a warning). The
messages name the state they came from (`LSP process has been stopped` vs. `LSP
process has not been started`). Construct a new `LSPProcess` when you need to
restart a server.


## Session lifecycle

After `shutdown()`, a session's operational methods raise `RuntimeError`; its
captured server and semantic-token metadata remain readable. Calling
`shutdown()` while other operations are in flight is safe: it waits up to five
seconds for them to finish, and if any are still running it stops the language
server process instead of returning it to the pool, keeping stale operations
out of the next session's protocol stream. (One narrow exception: cancelling
an operation ends its in-flight accounting even if a notification write it
already queued is still being flushed.)


Internal generated types whose names start with `__` are not public API.
