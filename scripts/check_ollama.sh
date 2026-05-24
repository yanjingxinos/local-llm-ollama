#!/usr/bin/env bash
set -euo pipefail

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed."
  echo "Run: ./scripts/install_ollama.sh"
  exit 1
fi

echo "Ollama version:"
ollama --version || true

echo
echo "Checking local service..."
if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "Ollama is running."
else
  echo "Ollama service is not responding. Trying to start it..."
  brew services start ollama || true
  sleep 2
fi

echo
echo "Installed models:"
ollama list || true

