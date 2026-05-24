#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-qwen3:8b}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed. Run ./scripts/install_ollama.sh first."
  exit 1
fi

echo "Starting chat with ${MODEL}."
echo "Press Ctrl-D or type /bye to exit."
echo

ollama run "${MODEL}"

