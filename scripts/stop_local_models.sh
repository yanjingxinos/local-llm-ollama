#!/usr/bin/env bash
set -euo pipefail

echo "Unloading any active Ollama model..."
ollama stop qwen3:8b >/dev/null 2>&1 || true
ollama stop deepseek-r1:8b >/dev/null 2>&1 || true
ollama stop gemma3:12b >/dev/null 2>&1 || true
ollama stop qwen3:14b >/dev/null 2>&1 || true
ollama stop deepseek-r1:14b >/dev/null 2>&1 || true

if command -v brew >/dev/null 2>&1; then
  echo "Stopping Ollama background service..."
  if ! brew services stop ollama; then
    echo "Warning: could not stop Ollama service. You may need to run:"
    echo "  brew services stop ollama"
  fi
fi

echo "Local Ollama models stopped."
