#!/usr/bin/env python3
import argparse
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_metrics() -> list[dict]:
    paths = list((ROOT / "runs").glob("*.metrics.json")) if (ROOT / "runs").exists() else []
    paths += list((ROOT / "task_records").glob("*/local_summary_metrics.json")) if (ROOT / "task_records").exists() else []

    rows = []
    for path in sorted(paths, key=lambda item: item.stat().st_mtime):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        data["path"] = str(path)
        rows.append(data)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize actual local Ollama token usage.")
    parser.add_argument("--recent", type=int, default=0, help="Only include the most recent N calls.")
    args = parser.parse_args()

    rows = load_metrics()
    if args.recent > 0:
        rows = rows[-args.recent :]

    prompt_tokens = sum(row.get("usage", {}).get("prompt_tokens", 0) for row in rows)
    output_tokens = sum(row.get("usage", {}).get("output_tokens", 0) for row in rows)
    total_tokens = sum(row.get("usage", {}).get("total_tokens", 0) for row in rows)
    total_seconds = sum(row.get("usage", {}).get("total_duration_seconds", 0) for row in rows)

    print("Local model actual usage")
    print(f"- Calls: {len(rows)}")
    print(f"- Prompt tokens: {prompt_tokens}")
    print(f"- Output tokens: {output_tokens}")
    print(f"- Total tokens: {total_tokens}")
    print(f"- Total duration: {total_seconds:.2f}s")
    print()

    for row in rows:
        usage = row.get("usage", {})
        print(
            f"- {row.get('model', 'unknown')} {row.get('mode', 'unknown')}: "
            f"{usage.get('total_tokens', 0)} tokens "
            f"({usage.get('prompt_tokens', 0)} prompt + {usage.get('output_tokens', 0)} output), "
            f"{usage.get('total_duration_seconds', 0):.2f}s"
        )

    if not rows:
        print("No metrics yet. New local_delegate.py/finalize_task.py calls will create metrics files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
