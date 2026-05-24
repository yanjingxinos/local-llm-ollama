#!/usr/bin/env bash
set -euo pipefail

MODELS=(
  "qwen3:8b"
  "deepseek-r1:8b"
  "gemma3:12b"
  "qwen3:14b"
  "deepseek-r1:14b"
)

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed. Run ./scripts/install_ollama.sh first."
  exit 1
fi

echo "Starting Ollama service if needed..."
brew services start ollama >/dev/null 2>&1 || true

for model in "${MODELS[@]}"; do
  echo
  echo "Pulling ${model}..."
  echo "If the network is interrupted, rerun this script later."
  ollama pull "${model}"
done

echo
echo "All requested models are installed:"
ollama list

