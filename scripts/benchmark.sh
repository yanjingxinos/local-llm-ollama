#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-qwen3:8b}"
PROMPT="${2:-请用中文简洁解释：为什么本地大模型在隐私和延迟方面有优势？}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed. Run ./scripts/install_ollama.sh first."
  exit 1
fi

echo "Model: ${MODEL}"
echo "Prompt: ${PROMPT}"
echo

time ollama run "${MODEL}" "${PROMPT}"

