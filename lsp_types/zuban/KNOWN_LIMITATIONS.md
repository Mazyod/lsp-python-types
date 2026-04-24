# Zuban Backend - Known Limitations

This document describes known limitations and behavioral differences when using the Zuban backend compared to other LSP backends (Pyright, Pyrefly, ty).

## 1. Config Written to `pyproject.toml`

**Behavior**: `ZubanBackend.write_config` adds or updates `[tool.zuban]` inside `pyproject.toml`, preserving any existing `[project]` metadata and other `[tool.*]` sections. It does not read, merge, or write `mypy.ini`, `.mypy.ini`, or `setup.cfg`.

**Why `pyproject.toml` and not a dedicated file**: Unlike Pyright (`pyrightconfig.json`), Pyrefly (`pyrefly.toml`), and ty (`ty.toml`), Zuban has no dedicated config file in its native "default" mode. The only way to configure Zuban's PyRight-like mode is via `pyproject.toml`'s `[tool.zuban]` table.

**Why `[tool.zuban]` and not `[tool.mypy]`**: Presence of `[tool.zuban]` puts Zuban into its recommended `default` mode (PyRight-like). `[tool.mypy]` would force the Mypy-compatible mode, which is less capable.

**Impact**: Re-invoking `write_config` replaces the previous `[tool.zuban]` table in place; nothing else is touched. This is safe even when `base_path` points at a real project root (as happens when `Session.create()` is called with the default `base_path=Path(".")`).

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
