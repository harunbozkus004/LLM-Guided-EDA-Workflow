#!/bin/bash
# Local LLM server (llama.cpp) used as the experiment model.
#
#   scripts/llm_server.sh run      # foreground
#   scripts/llm_server.sh start    # background; waits until healthy
#   scripts/llm_server.sh stop
#   scripts/llm_server.sh status
#
# Serves an OpenAI-compatible API on 127.0.0.1 only. All state (pid, log) lives
# in .tools/llm_server. Settings are fixed so experiments are reproducible.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/.tools"
STATE="$TOOLS/llm_server"
mkdir -p "$STATE"

SERVER="$(find "$TOOLS/llama.cpp/b11829" -name llama-server -type f 2>/dev/null | head -1)"
MODEL="$TOOLS/models/Qwen3.6-35B-A3B-Q4_K_M.gguf"
ALIAS="qwen3.6-35b-a3b-q4_k_m"
PORT="${LLM_PORT:-8080}"
SLOTS="${LLM_SLOTS:-4}"
CTX_PER_SLOT="${LLM_CTX_PER_SLOT:-32768}"

ARGS=(-m "$MODEL" --alias "$ALIAS" --host 127.0.0.1 --port "$PORT"
      -c "$((SLOTS * CTX_PER_SLOT))" -np "$SLOTS" -ngl 999 -fa on --jinja --no-webui)

healthy() { curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; }

case "${1:-}" in
  run)
    exec env HOME="$TOOLS/home" LLAMA_CACHE="$TOOLS/cache/llama.cpp" "$SERVER" "${ARGS[@]}"
    ;;
  start)
    if healthy; then echo "already running on port $PORT"; exit 0; fi
    [ -x "$SERVER" ] && [ -f "$MODEL" ] || { echo "run scripts/setup_llm.sh first" >&2; exit 1; }
    env HOME="$TOOLS/home" LLAMA_CACHE="$TOOLS/cache/llama.cpp" nohup "$SERVER" "${ARGS[@]}" \
      > "$STATE/server.log" 2>&1 &
    echo $! > "$STATE/server.pid"
    for _ in $(seq 1 300); do
      if healthy; then echo "llama-server ready on 127.0.0.1:$PORT (pid $(cat "$STATE/server.pid"))"; exit 0; fi
      if ! kill -0 "$(cat "$STATE/server.pid")" 2>/dev/null; then
        echo "llama-server exited; see $STATE/server.log" >&2; exit 1
      fi
      sleep 1
    done
    echo "llama-server did not become healthy in 300 s; see $STATE/server.log" >&2; exit 1
    ;;
  stop)
    if [ -f "$STATE/server.pid" ]; then
      kill "$(cat "$STATE/server.pid")" 2>/dev/null || true
      rm -f "$STATE/server.pid"
      echo "stopped"
    else
      echo "not running (no pid file)"
    fi
    ;;
  status)
    if healthy; then echo "running on 127.0.0.1:$PORT"; else echo "not running"; exit 1; fi
    ;;
  *)
    echo "usage: $0 run|start|stop|status" >&2; exit 2
    ;;
esac
