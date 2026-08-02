from __future__ import annotations

import dataclasses as dc
import datetime as dt
import decimal
import enum
import logging
import typing as t
from pathlib import Path, PurePath

from . import semantic_tokens, types
from .pool import LSPProcessPool
from .process import LSPProcess, ProcessLaunchInfo

logger = logging.getLogger("lsp-types")


class LSPBackend[TConfig: t.Mapping](t.Protocol):
    """Protocol defining backend-specific LSP operations"""

    def write_config(self, base_path: Path, options: TConfig) -> None:
        """Write backend-specific configuration file"""
        ...

    def create_process_launch_info(
        self, base_path: Path, options: TConfig
    ) -> ProcessLaunchInfo:
        """Create process launch info for the LSP server"""
        ...

    def get_lsp_capabilities(self) -> types.ClientCapabilities:
        """Get LSP client capabilities"""
        ...

    def get_workspace_settings(
        self, options: TConfig
    ) -> types.DidChangeConfigurationParams:
        """Get workspace settings for didChangeConfiguration"""
        ...

    def get_semantic_tokens_legend(self) -> types.SemanticTokensLegend | None:
        """Return hardcoded legend if server doesn't advertise one."""
        ...

    def requires_file_on_disk(self) -> bool:
        """Return True if this backend requires files to exist on disk.

        Some LSP backends (like ty) cannot analyze virtual documents opened via
        didOpen without a corresponding file on disk. For these backends, the
        session will write the initial code to disk before opening the document.
        """
        ...

    def consumes_did_change_configuration(self) -> bool:
        """Return True if this backend consumes workspace/didChangeConfiguration.

        Backends that configure themselves exclusively from on-disk config files
        (e.g. Zuban reads `[tool.zuban]` from `pyproject.toml`) ignore this
        notification and may log it as an unhandled-notification error. Override
        to False on those backends to suppress the notification at the source.
        """
        return True


@dc.dataclass(kw_only=True)
class DiagnosticsResult:
    id: str
    value: list[types.Diagnostic]


@dc.dataclass(frozen=True)
class _ProcessCompatibilityKey:
    """Inputs that must match before an initialized process can be reused."""

    backend_type: type[t.Any]
    base_path: str
    command: tuple[str, ...]
    environment: tuple[tuple[str, str], ...]
    working_directory: str
    options: t.Hashable
    initialize_params: t.Hashable


def _stable_repr(frozen: t.Hashable) -> str:
    """Render a frozen token deterministically for sorting mapping items.

    ``repr`` alone is not stable for frozensets: their iteration order depends on
    element insertion history, so equal sets can render differently within one
    process. Sorting their element renderings removes that variance.
    """
    if isinstance(frozen, frozenset):
        return "{" + ", ".join(sorted(_stable_repr(item) for item in frozen)) + "}"
    if isinstance(frozen, tuple):
        return "(" + ", ".join(_stable_repr(item) for item in frozen) + ")"
    return repr(frozen)


def _freeze_for_compatibility(value: t.Any) -> t.Hashable:
    """Convert nested protocol/config values into a deterministic hashable value."""
    # Enum members have the same wire representation as their scalar values.
    if isinstance(value, enum.Enum):
        return _freeze_for_compatibility(value.value)
    if isinstance(value, t.Mapping):
        items = [
            (
                _freeze_for_compatibility(key),
                _freeze_for_compatibility(item_value),
            )
            for key, item_value in value.items()
        ]
        return ("mapping", tuple(sorted(items, key=lambda item: _stable_repr(item[0]))))
    if isinstance(value, (list, tuple)):
        return ("sequence", tuple(_freeze_for_compatibility(item) for item in value))
    if isinstance(value, (set, frozenset)):
        # Frozen elements are not guaranteed to be mutually orderable, so
        # membership rather than a sort order canonicalizes the token.
        return ("set", frozenset(_freeze_for_compatibility(item) for item in value))

    if isinstance(value, float):
        # ``0.0 == -0.0`` even though their serialized forms can differ.
        return ("scalar", float, value.hex())
    if isinstance(value, (bytes, bytearray)):
        # Buffers are snapshotted like the mutable sequences handled above.
        return ("scalar", bytes, bytes(value))
    if isinstance(value, PurePath):
        # Matches pathlib's own equality; a path never matches a plain string.
        return ("path", str(value))
    if isinstance(value, decimal.Decimal):
        # ``Decimal("1.0") == Decimal("1.00")`` even though they serialize apart.
        return ("scalar", decimal.Decimal, str(value))
    if isinstance(value, (dt.date, dt.time)):
        # ``datetime`` subclasses ``date``; the exact type keeps the two apart.
        return ("scalar", type(value), value.isoformat())
    if isinstance(value, dt.timedelta):
        return (
            "scalar",
            dt.timedelta,
            (value.days, value.seconds, value.microseconds),
        )
    if value is None or isinstance(value, (bool, int, str)):
        return ("scalar", type(value), value)

    # Hashability does not guarantee immutability or safe equality. Unknown values
    # therefore get a unique token so custom configurations remain valid but never
    # risk reusing a process initialized from stale state.
    logger.debug(
        "Config value of type %s cannot be compared safely; "
        "process reuse is disabled for this session",
        type(value).__name__,
    )
    return ("unsupported", type(value), object())


def _build_process_compatibility_key(
    backend: LSPBackend,
    *,
    base_path: str,
    process_launch_info: ProcessLaunchInfo,
    resolved_environment: t.Mapping[str, str],
    options: t.Mapping,
    initialize_params: types.InitializeParams,
) -> _ProcessCompatibilityKey:
    """Build the complete identity of an initialized language-server process."""
    return _ProcessCompatibilityKey(
        backend_type=type(backend),
        base_path=base_path,
        command=tuple(process_launch_info.cmd),
        environment=tuple(sorted(resolved_environment.items())),
        working_directory=str(process_launch_info.cwd.resolve()),
        options=_freeze_for_compatibility(options),
        initialize_params=_freeze_for_compatibility(initialize_params),
    )


class Session:
    """Concrete LSP session implementation using pluggable backends"""

    @classmethod
    async def create(
        cls,
        backend: LSPBackend,
        *,
        base_path: Path = Path("."),
        initial_code: str = "",
        options: t.Mapping = {},
        initialize_params: types.InitializeParams | None = None,
        pool: LSPProcessPool | None = None,
    ) -> t.Self:
        """Create a new LSP session using the provided backend"""
        base_path = base_path.resolve()
        base_path_str = str(base_path)

        # Write backend-specific configuration
        backend.write_config(base_path, options)

        process_launch_info = backend.create_process_launch_info(base_path, options)
        resolved_environment = process_launch_info.resolved_environment()
        resolved_initialize_params: types.InitializeParams = {
            "processId": None,
            "rootUri": f"file://{base_path}",
            "rootPath": base_path_str,
            "capabilities": backend.get_lsp_capabilities(),
        }

        if initialize_params is not None:
            resolved_initialize_params = resolved_initialize_params | initialize_params

        compatibility_key = _build_process_compatibility_key(
            backend,
            base_path=base_path_str,
            process_launch_info=process_launch_info,
            resolved_environment=resolved_environment,
            options=options,
            initialize_params=resolved_initialize_params,
        )

        async def create_lsp_process() -> LSPProcess:
            lsp_process = LSPProcess(
                process_launch_info,
                resolved_environment=resolved_environment,
            )
            try:
                await lsp_process.start()

                # Initialize LSP connection
                await lsp_process.send.initialize(resolved_initialize_params)

                # Send initialized notification (required by LSP spec)
                await lsp_process.notify.initialized({})
            except BaseException:
                # Nothing owns the process until this factory returns - the pool
                # only records it afterwards - so it must stop itself on every
                # failure, cancellation included. `stop()` is cancellation-safe:
                # it finishes reaping before re-raising, so no shield is needed.
                await lsp_process.stop()
                raise

            return lsp_process

        # Use pool if provided, otherwise create a default non-pooling pool
        if pool is None:
            pool = LSPProcessPool(max_size=0)  # No recycling, immediate shutdown

        lsp_process = await pool.acquire(
            create_lsp_process,
            base_path_str,
            compatibility_key=compatibility_key,
        )
        try:
            init_result = lsp_process.initialize_result
            server_legend: types.SemanticTokensLegend | None = None
            server_info: types.ServerInfo | None = None
            if init_result:
                capabilities = init_result.get("capabilities", {})
                provider = capabilities.get("semanticTokensProvider")
                if provider and "legend" in provider:
                    server_legend = provider["legend"]
                server_info = init_result.get("serverInfo")

            # Use server legend if advertised, otherwise fall back to backend's legend
            legend = server_legend or backend.get_semantic_tokens_legend()

            session = cls(
                lsp_process,
                backend,
                base_path,
                pool=pool,
                legend=legend,
                server_info=server_info,
            )

            # Update settings via didChangeConfiguration
            if backend.consumes_did_change_configuration():
                workspace_settings = backend.get_workspace_settings(options)
                await lsp_process.notify.workspace_did_change_configuration(
                    workspace_settings
                )

            # Write file to disk if backend requires it (e.g., ty)
            if backend.requires_file_on_disk():
                session._file_path.write_text(initial_code)
                session._file_on_disk = True

            # Simulate opening a document
            await session._open_document(initial_code)

            return session
        except BaseException:
            # Release the process back to the pool (or shut it down for non-pooled)
            # to avoid resource leaks on initialization failure. Cancellation is the
            # most likely trigger - a caller timing out a slow server - so it must be
            # caught too. The release still completes: its bookkeeping runs before
            # any suspension point, and any `stop()` it awaits defers cancellation
            # until cleanup has finished.
            await pool.release(lsp_process)
            raise

    def __init__(
        self,
        lsp_process: LSPProcess,
        backend: LSPBackend,
        base_path: Path,
        *,
        pool: LSPProcessPool,
        legend: types.SemanticTokensLegend | None = None,
        server_info: types.ServerInfo | None = None,
    ):
        self.__process = lsp_process
        self._pool = pool
        self._closed = False
        self._backend = backend
        self._file_path = base_path / "new.py"
        self._document_uri = f"file://{self._file_path}"
        self._document_version = 1
        self._document_text = ""
        self._diag_result: DiagnosticsResult | None = None
        self._file_on_disk = (
            False  # Set to True if file was written for backends that require it
        )
        self._server_info = server_info

        # Semantic tokens normalization
        self._backend_legend = legend
        self._type_map: dict[int, int] | None = None
        self._modifier_map: dict[int, int] | None = None
        if legend:
            self._type_map = semantic_tokens.build_type_mapping(legend)
            self._modifier_map = semantic_tokens.build_modifier_mapping(legend)

    async def shutdown(self) -> None:
        """Close the session and release its process lease exactly once.

        The session remains closed if releasing the process raises because
        ownership may already have been partially transferred.
        """
        if self._closed:
            return  # Already shut down

        # Revoke this session's lease before yielding so concurrent shutdown calls
        # cannot release the same process twice, and stale references cannot use a
        # process after it has been returned to the pool.
        self._closed = True

        # Release back to pool (document cleanup handled by pool/process reset)
        # For max_size=0 pools, this will immediately shutdown the process
        await self._pool.release(self.__process)

    async def update_code(self, code: str) -> int:
        """Update the code in the current document"""
        process = self._process
        self._document_version += 1
        self._document_text = code

        # Keep file on disk in sync if required by backend
        if self._file_on_disk:
            self._file_path.write_text(code)

        document_version = self._document_version
        await process.notify.did_change_text_document(
            {
                "textDocument": {
                    "uri": self._document_uri,
                    "version": self._document_version,
                },
                "contentChanges": [{"text": code}],
            }
        )

        return document_version

    async def get_diagnostics(self) -> list[types.Diagnostic]:
        """Pull diagnostics via textDocument/diagnostic (LSP-3.17)"""
        process = self._process
        params: types.DocumentDiagnosticParams = {
            "textDocument": {"uri": self._document_uri},
        }

        if result := self._diag_result:
            params["previousResultId"] = result.id

        report = await process.send.text_document_diagnostic(params)

        diagnostics: list[types.Diagnostic]
        match report["kind"]:
            case "full":
                diagnostics = report["items"]
            case "unchanged":
                diagnostics = self._diag_result.value if self._diag_result else []

        # Persist token for the next delta request (if present)
        if result_id := report.get("resultId"):
            self._diag_result = DiagnosticsResult(id=result_id, value=diagnostics)

        # For 'unchanged' nothing is appended ⇒ return cached view if desired
        return diagnostics

    async def get_hover_info(self, position: types.Position) -> types.Hover | None:
        """Get hover information at the given position.

        If the backend omits ``range`` (Pyrefly does), it is synthesized as a
        zero-width range at the request position so callers can rely on the
        field being present. The synthesized range marks the request position,
        not the symbol extent — consumers that need the symbol's actual span
        must compute it themselves.
        """
        process = self._process
        hover = await process.send.hover(
            {"textDocument": {"uri": self._document_uri}, "position": position}
        )
        if hover is not None and "range" not in hover:
            hover["range"] = {"start": position, "end": position}
        return hover

    async def get_rename_edits(
        self, position: types.Position, new_name: str
    ) -> types.WorkspaceEdit | None:
        """Get rename edits for the given position"""
        process = self._process
        return await process.send.rename(
            {
                "textDocument": {"uri": self._document_uri},
                "position": position,
                "newName": new_name,
            }
        )

    async def get_signature_help(
        self, position: types.Position
    ) -> types.SignatureHelp | None:
        """Get signature help at the given position"""
        process = self._process
        return await process.send.signature_help(
            {"textDocument": {"uri": self._document_uri}, "position": position}
        )

    async def get_completion(self, position: types.Position) -> types.CompletionList:
        """Get completion items at the given position.

        The LSP spec lets servers reply with a ``CompletionList``, a bare
        ``CompletionItem[]``, or ``null``; this method normalizes all three to
        a ``CompletionList`` so callers always work against the same shape.
        ``null`` and a bare list both map to ``isIncomplete: False`` (the spec
        treats them as complete result sets — empty and given, respectively).
        """
        process = self._process
        result = await process.send.completion(
            {"textDocument": {"uri": self._document_uri}, "position": position}
        )
        if result is None:
            return {"items": [], "isIncomplete": False}
        if isinstance(result, list):
            return {"items": result, "isIncomplete": False}
        return result

    async def resolve_completion(
        self, completion_item: types.CompletionItem
    ) -> types.CompletionItem:
        """Resolve the given completion item"""
        process = self._process
        return await process.send.resolve_completion_item(completion_item)

    async def get_semantic_tokens(
        self, *, normalize: bool = False
    ) -> types.SemanticTokens | None:
        """Get semantic tokens for the current document."""
        process = self._process
        tokens = await process.send.semantic_tokens_full(
            {"textDocument": {"uri": self._document_uri}}
        )

        if not normalize or tokens is None:
            return tokens

        # Remap indices to canonical legend
        if self._type_map is None or self._modifier_map is None:
            # No legend captured, can't normalize
            return tokens

        return semantic_tokens.normalize_tokens(
            tokens, self._type_map, self._modifier_map
        )

    @property
    def canonical_legend(self) -> types.SemanticTokensLegend:
        """The canonical legend for normalized semantic tokens."""
        return semantic_tokens.CANONICAL_LEGEND

    @property
    def backend_legend(self) -> types.SemanticTokensLegend | None:
        """The backend's semantic tokens legend, if available."""
        return self._backend_legend

    @property
    def server_info(self) -> types.ServerInfo | None:
        """The server's self-reported name and version from the initialize response."""
        return self._server_info

    # Private methods

    @property
    def _process(self) -> LSPProcess:
        """Return the process while this session owns its lease."""
        if self._closed:
            raise RuntimeError("Session has been shut down")
        return self.__process

    async def _open_document(self, code: str) -> None:
        """Open a document with the given code"""
        process = self._process
        self._document_text = code
        await process.notify.did_open_text_document(
            {
                "textDocument": {
                    "languageId": types.LanguageKind.Python,
                    "version": self._document_version,
                    "uri": self._document_uri,
                    "text": code,
                }
            }
        )
        # Track the opened document
        process.track_document_open(self._document_uri)
