#!/usr/bin/env bash
set -euo pipefail

if command -v ollama >/dev/null 2>&1; then
  echo "Ollama already installed:"
  ollama --version || true
else
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is not installed. Please install Homebrew first:"
    echo "https://brew.sh"
    exit 1
  fi

  echo "Installing Ollama with Homebrew..."
  brew install ollama
fi

echo "Starting Ollama background service..."
brew services start ollama || true

echo "Done. Run ./scripts/check_ollama.sh to verify."

