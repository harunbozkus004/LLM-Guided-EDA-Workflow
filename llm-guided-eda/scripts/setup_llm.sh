#!/bin/bash
# Free, local LLM backend: llama.cpp server + an open-weights model, installed
# under ./.tools (nothing outside the repository). Both downloads are pinned and
# verified by SHA-256.
#
#   llama.cpp  b11829 (2026-10-22) macOS arm64 build, ggml-org/llama.cpp releases
#   model      Qwen3.6-35B-A3B Q4_K_M GGUF (Apache-2.0), ggml-org/Qwen3.6-35B-A3B-GGUF
#              revision 7878dc9a905c7c9379e5e8d6a1aa9affdd6839c5 (20.4 GB)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/.tools"
export HOME="$TOOLS/home"

LLAMA_TAG="b11829"
LLAMA_TGZ="llama-${LLAMA_TAG}-bin-macos-arm64.tar.gz"
LLAMA_SHA256="e006ea32abe757c10a93718d246796b9bb7eafd309398927ff7b69139e4ba27e"

MODEL_REPO="ggml-org/Qwen3.6-35B-A3B-GGUF"
MODEL_REV="7878dc9a905c7c9379e5e8d6a1aa9affdd6839c5"
MODEL_FILE="Qwen3.6-35B-A3B-Q4_K_M.gguf"
MODEL_SHA256="671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7"

if [ "$(uname -s)-$(uname -m)" != "Darwin-arm64" ]; then
  echo "setup_llm.sh targets Apple Silicon; on Linux use an equivalent llama.cpp build (see README)." >&2
  exit 1
fi

log() { printf '[setup_llm %s] %s\n' "$(date +%H:%M:%S)" "$*"; }
verify() {  # verify <file> <sha256>
  local actual; actual="$(shasum -a 256 "$1" | awk '{print $1}')"
  if [ "$actual" != "$2" ]; then echo "checksum mismatch for $1" >&2; exit 1; fi
}

# ---------------------------------------------------------------- llama.cpp
LDIR="$TOOLS/llama.cpp/$LLAMA_TAG"
if [ ! -d "$LDIR" ]; then
  log "Downloading llama.cpp $LLAMA_TAG"
  mkdir -p "$TOOLS/llama.cpp"
  curl -fsSL -o "$TOOLS/llama.cpp/$LLAMA_TGZ" \
    "https://github.com/ggml-org/llama.cpp/releases/download/$LLAMA_TAG/$LLAMA_TGZ"
  verify "$TOOLS/llama.cpp/$LLAMA_TGZ" "$LLAMA_SHA256"
  mkdir -p "$LDIR"
  tar -xzf "$TOOLS/llama.cpp/$LLAMA_TGZ" -C "$LDIR"
  rm "$TOOLS/llama.cpp/$LLAMA_TGZ"
fi
SERVER="$(find "$LDIR" -name llama-server -type f | head -1)"
log "llama-server: $SERVER"
"$SERVER" --version 2>&1 | tail -2

# -------------------------------------------------------------------- model
MDIR="$TOOLS/models"
mkdir -p "$MDIR"
if [ ! -f "$MDIR/$MODEL_FILE" ]; then
  log "Downloading $MODEL_REPO/$MODEL_FILE @ ${MODEL_REV:0:12} (20.4 GB, resumable)"
  curl -fL --retry 5 --retry-delay 5 -C - -o "$MDIR/$MODEL_FILE.part" \
    "https://huggingface.co/$MODEL_REPO/resolve/$MODEL_REV/$MODEL_FILE"
  log "Verifying checksum"
  verify "$MDIR/$MODEL_FILE.part" "$MODEL_SHA256"
  mv "$MDIR/$MODEL_FILE.part" "$MDIR/$MODEL_FILE"
fi
log "Done: $MDIR/$MODEL_FILE"
