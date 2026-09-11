#!/usr/bin/env bash
# Fetch Pyrefly's release WASM and build ty from its matching release source.
# ty needs Rust (rustup) and a native compiler; wasm-pack runs through npm.
# Update release versions and their SHA256 sums together during maintenance.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WASM_DIR="${SCRIPT_DIR}/wasm"
PYREFLY_VERSION="1.3.0"
TY_VERSION="0.0.80"
WASM_PACK_VERSION="0.15.0"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

fetch_pyrefly() {
  local dir="${WASM_DIR}/pyrefly"
  if [ -f "$dir/pyrefly_wasm_bg.wasm" ] && [ -f "$dir/pyrefly_wasm.js" ] &&
    [ "$(cat "$dir/.version" 2>/dev/null || true)" = "$PYREFLY_VERSION" ]; then
    echo "Pyrefly ${PYREFLY_VERSION} WASM already exists."
    return
  fi

  echo "Downloading Pyrefly ${PYREFLY_VERSION} WASM..."
  curl --fail --location --retry 3 \
    "https://github.com/facebook/pyrefly/releases/download/${PYREFLY_VERSION}/pyrefly-wasm.tar.gz" \
    -o "$TMP_DIR/pyrefly-wasm.tar.gz"
  (cd "$TMP_DIR" && echo "6a70781b5e70ad505f18cade35bf64bfc83cfee14437e07fceafd374cc358fd0  pyrefly-wasm.tar.gz" | shasum -a 256 --check)
  mkdir -p "$dir"
  tar -xzf "$TMP_DIR/pyrefly-wasm.tar.gz" -C "$dir"
  echo "$PYREFLY_VERSION" > "$dir/.version"
}

fetch_ty() {
  local dir="${WASM_DIR}/ty"
  if [ -f "$dir/ty_wasm_bg.wasm" ] && [ -f "$dir/ty_wasm.js" ] &&
    [ "$(cat "$dir/.version" 2>/dev/null || true)" = "$TY_VERSION" ]; then
    echo "ty ${TY_VERSION} WASM already exists."
    return
  fi

  command -v cargo >/dev/null || { echo "Install Rust with rustup before building ty WASM." >&2; exit 1; }
  echo "Building ty ${TY_VERSION} WASM from release source..."
  curl --fail --location --retry 3 \
    "https://github.com/astral-sh/ty/releases/download/${TY_VERSION}/source.tar.gz" \
    -o "$TMP_DIR/ty-source.tar.gz"
  (cd "$TMP_DIR" && echo "a039d7e66d362e1707fc494f2c69dfdd2eb5333dc8fa9ad582edc125932fa5fa  ty-source.tar.gz" | shasum -a 256 --check)
  tar -xzf "$TMP_DIR/ty-source.tar.gz" -C "$TMP_DIR"
  # The source archive contains the exact Ruff workspace used for this ty release.
  (cd "$TMP_DIR/ruff" && npm exec --yes --package="wasm-pack@${WASM_PACK_VERSION}" -- \
    wasm-pack build crates/ty_wasm --target web --out-dir "$dir" --no-typescript -- --locked)
  echo "$TY_VERSION" > "$dir/.version"
}

case "${1:-all}" in
  pyrefly) fetch_pyrefly ;;
  ty) fetch_ty ;;
  all) fetch_pyrefly; fetch_ty ;;
  *) echo "Usage: $0 [pyrefly|ty|all]" >&2; exit 1 ;;
esac

echo "WASM modules are in ${WASM_DIR}/"
