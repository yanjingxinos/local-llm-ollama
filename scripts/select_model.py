#!/usr/bin/env python3
import argparse
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
PROFILES_PATH = ROOT / "config" / "model_profiles.json"


def load_profiles() -> dict:
    with PROFILES_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def choose_model(task_type: str, quality: str, available: set[str] | None) -> tuple[str, str]:
    profiles = load_profiles()
    fallbacks = profiles["fallbacks"]

    candidates = []
    if quality == "quality":
        if task_type in {"summarize", "extract", "draft", "archive", "compare", "critic-lite"}:
            candidates.extend(["qwen3:14b", "qwen3:8b"])
        elif task_type in {"test-ideas", "bug-hypotheses", "local-reasoning"}:
            candidates.extend(["deepseek-r1:14b", "deepseek-r1:8b"])

    candidates.append(fallbacks.get(task_type, "qwen3:8b"))
    candidates.extend(["qwen3:8b", "deepseek-r1:8b"])

    for model in candidates:
        if available is None or model in available:
            notes = profiles["models"].get(model, {}).get("notes", "")
            return model, notes

    return "qwen3:8b", profiles["models"]["qwen3:8b"]["notes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Select a local Ollama model for a delegated subtask.")
    parser.add_argument("task_type", help="summarize, extract, draft, archive, critic-lite, test-ideas, bug-hypotheses, compare, multimodal")
    parser.add_argument("--quality", choices=["fast", "quality"], default="fast")
    parser.add_argument("--available", default="", help="Comma-separated available models. If omitted, assume all configured models may be used.")
    args = parser.parse_args()

    available = None
    if args.available.strip():
        available = {item.strip() for item in args.available.split(",") if item.strip()}

    model, notes = choose_model(args.task_type, args.quality, available)
    print(model)
    print(f"Reason: {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

