#!/usr/bin/env bash
# Fetches pre-built WASM modules for Pyrefly and ty from their GitHub releases.
# Run this before `npm run dev` if you want Pyrefly or ty backends.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WASM_DIR="${SCRIPT_DIR}/wasm"

# --- Pyrefly ---
# Build from source using wasm-pack (requires Rust toolchain)
fetch_pyrefly() {
  local dir="${WASM_DIR}/pyrefly"
  mkdir -p "$dir"

  if [ -f "$dir/pyrefly_wasm_bg.wasm" ]; then
    echo "Pyrefly WASM already exists, skipping."
    return
  fi

  echo "Building Pyrefly WASM from source..."
  local tmpdir
  tmpdir=$(mktemp -d)
  trap 'rm -rf "$tmpdir"' RETURN

  git clone --depth=1 https://github.com/facebook/pyrefly.git "$tmpdir/pyrefly"
  cd "$tmpdir/pyrefly/pyrefly_wasm"

  if ! command -v wasm-pack &>/dev/null; then
    echo "Installing wasm-pack..."
    cargo install wasm-pack
  fi

  wasm-pack build --target web --out-dir "$dir" --no-typescript
  echo "Pyrefly WASM built successfully."
}

# --- ty ---
# Build from source using wasm-pack (requires Rust toolchain)
fetch_ty() {
  local dir="${WASM_DIR}/ty"
  mkdir -p "$dir"

  if [ -f "$dir/ty_wasm_bg.wasm" ]; then
    echo "ty WASM already exists, skipping."
    return
  fi

  echo "Building ty WASM from source..."
  local tmpdir
  tmpdir=$(mktemp -d)
  trap 'rm -rf "$tmpdir"' RETURN

  git clone --depth=1 https://github.com/astral-sh/ruff.git "$tmpdir/ruff"
  cd "$tmpdir/ruff"

  if ! command -v wasm-pack &>/dev/null; then
    echo "Installing wasm-pack..."
    cargo install wasm-pack
  fi

  wasm-pack build --target web crates/ty_wasm --out-dir "$dir" --no-typescript
  echo "ty WASM built successfully."
}

echo "=== Fetching WASM modules ==="
echo ""

case "${1:-all}" in
  pyrefly)
    fetch_pyrefly
    ;;
  ty)
    fetch_ty
    ;;
  all)
    fetch_pyrefly
    fetch_ty
    ;;
  *)
    echo "Usage: $0 [pyrefly|ty|all]"
    exit 1
    ;;
esac

echo ""
echo "Done! WASM modules are in ${WASM_DIR}/"
