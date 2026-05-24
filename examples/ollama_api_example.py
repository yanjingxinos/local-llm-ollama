#!/usr/bin/env python3
import json
import urllib.request


def generate(model: str, prompt: str) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))
        return result["response"]


if __name__ == "__main__":
    answer = generate(
        "qwen3:8b",
        "用中文写一个 5 条要点的本地大模型使用建议。",
    )
    print(answer)

