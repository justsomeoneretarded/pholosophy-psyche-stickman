#!/usr/bin/env bash
# Start a local Ollama server with the fallback writer model (only used if Groq is unavailable).
set -euo pipefail
model="${1:-gemma4:12b}"
url="${OLLAMA_URL:-http://127.0.0.1:11434}"
if ! command -v ollama >/dev/null 2>&1; then
  curl --fail --show-error --location --retry 3 https://ollama.com/install.sh -o "${RUNNER_TEMP:-/tmp}/ollama.sh"
  sh "${RUNNER_TEMP:-/tmp}/ollama.sh"
fi
if ! curl -sf "$url/api/tags" >/dev/null; then
  (ollama serve > "${RUNNER_TEMP:-/tmp}/ollama.log" 2>&1 &)
  for i in $(seq 1 90); do curl -sf "$url/api/tags" >/dev/null && break; sleep 1; done
fi
ollama pull "$model"
