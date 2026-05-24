#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
MODEL="${2:-qwen3:8b}"
TASK="${3:-}"

if [[ -z "${MODE}" || -z "${TASK}" ]]; then
  echo "Usage:"
  echo "  ./scripts/delegate.sh <mode> <model> <task>"
  echo
  echo "Examples:"
  echo "  ./scripts/delegate.sh critic-lite qwen3:8b \"列出这个方案可能遗漏的点\""
  echo "  ./scripts/delegate.sh test-ideas deepseek-r1:8b \"为登录功能设计测试用例\""
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

python3 "${ROOT_DIR}/scripts/local_delegate.py" \
  --mode "${MODE}" \
  --model "${MODEL}" \
  --task "${TASK}"
