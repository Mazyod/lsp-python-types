# Zuban Backend - Known Limitations

This document describes known limitations and behavioral differences when using the Zuban backend compared to other LSP backends (Pyright, Pyrefly, ty).

## 1. Config Written to `pyproject.toml` (Overwrite Semantics)

**Limitation**: `ZubanBackend.write_config` writes to `pyproject.toml` under `[tool.zuban]`. It does not read, merge, or write `mypy.ini`, `.mypy.ini`, or `setup.cfg`. Any pre-existing content in `pyproject.toml` is replaced.

**Why `pyproject.toml` and not a dedicated file**: Unlike Pyright (`pyrightconfig.json`), Pyrefly (`pyrefly.toml`), and ty (`ty.toml`), Zuban has no dedicated config file in its native "default" mode. The only way to configure Zuban's PyRight-like mode is via `pyproject.toml`'s `[tool.zuban]` table.

**Why `[tool.zuban]` and not `[tool.mypy]`**: Presence of `[tool.zuban]` puts Zuban into its recommended `default` mode (PyRight-like). `[tool.mypy]` would force the Mypy-compatible mode, which is less capable.

**Impact**: In typical test/session use (`tmp_path` or a fresh directory), the overwrite is a no-op because no prior `pyproject.toml` exists. For embedded use against a real project directory, callers must manage the merge themselves before invoking `write_config`. This overwrite contract is pinned by `test_zuban_backend_write_config_overwrites_existing_pyproject` in `tests/test_zuban_config.py`.

## 2. Unused `# type: ignore` Comments Not Reported

**Limitation**: Zuban does not yet report unused `# type: ignore` comments (upstream limitation as of Zuban 0.7.0, per the [features documentation](https://docs.zubanls.com/en/latest/features.html)).

**Impact**: Code that accumulates stale `# type: ignore` comments will not be flagged when using this backend.

## 3. Bounded `TypeVar` Function Bodies Not Fully Type-Checked

**Limitation**: Zuban does not currently type-check function bodies that use bounded `TypeVar` definitions such as `TypeVar("T", str, bytes)` (upstream limitation as of Zuban 0.7.0).

**Impact**: Type errors inside such functions may not surface via diagnostics.

## 4. No CLI Configuration Flags on `zuban server`

**Limitation**: `zuban server` accepts no command-line flags. All configuration is file-based.

**Impact**: No functional impact on this backend — `ZubanBackend` configures Zuban entirely via `pyproject.toml`. Unlike the Pyrefly backend (which exposes `--verbose`, `--threads`, `--indexing-mode` through `ProcessLaunchInfo`), `ZubanBackend.create_process_launch_info` returns a fixed `["zuban", "server"]` command.

---

## Version Information

These limitations were documented based on Zuban version 0.7.0 (April 2026). Future versions may address some of these limitations.
