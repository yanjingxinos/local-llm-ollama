#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import pathlib
import sys
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"


SYSTEM_RULES = """你是一个本地辅助模型，只负责完成主模型分派的子任务。
你不能做最终决策，不能声称已经修改文件，不能编造未提供的事实。
你的输出会被 Codex 或 Claude review 后才可能合并进主任务。
请保持结构化、可验证、克制。"""


MODE_PROMPTS = {
    "summarize": """任务类型：摘要
请输出：
1. 核心结论
2. 关键信息
3. 不确定或缺失的信息
4. 建议主模型继续追问或验证的点""",
    "review": """任务类型：local-scan
注意：你不是最终 reviewer，不能判断风险等级或最终是否采纳。你只列出候选问题，供主控模型审查。
请输出：
1. 候选问题
2. 支持该问题的输入证据
3. 需要验证的假设
4. 候选修改方向
5. 必须由主控模型判断的内容""",
    "plan": """任务类型：方案设计
请输出：
1. 可行方案
2. 推荐方案
3. 取舍理由
4. 风险
5. 最小落地步骤""",
    "test-ideas": """任务类型：测试设计
你只生成候选测试，不判断风险等级、优先级、发布 readiness 或最终覆盖是否充分。
请输出：
1. 核心测试场景
2. 边界条件
3. 回归测试候选
4. 建议自动化测试
5. 需要主控模型或人工确认的部分""",
    "critic": """任务类型：反方审查
请故意寻找主方案的问题，但不要判断风险等级、架构取舍或最终是否采纳。
请输出：
1. 最可能失败的地方
2. 被忽略的前提
3. 过度设计或欠设计之处
4. 更简单的替代方案
5. 必须由主模型确认的问题""",
    "critic-lite": """任务类型：轻量反方检查
请列出可能遗漏、含糊和需要主控模型确认的点。不要判断风险等级或最终是否采纳。
请输出：
1. 可能遗漏
2. 含糊需求
3. 简单失败场景
4. 给主控模型的问题
5. 超出你范围的内容""",
}


def build_prompt(mode: str, task: str) -> str:
    mode_prompt = MODE_PROMPTS.get(mode, MODE_PROMPTS["review"])
    return f"""{SYSTEM_RULES}

{mode_prompt}

子任务：
{task}

输出要求：
- 使用中文。
- 用清晰小标题。
- 不要输出客套话。
- 不要假设你看过未提供的文件。
- 如果信息不足，明确写“信息不足”。
"""


def call_ollama(model: str, prompt: str) -> str:
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

    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Cannot connect to Ollama: {exc}") from exc


def save_run(mode: str, model: str, task: str, prompt: str, response: str) -> pathlib.Path:
    RUNS_DIR.mkdir(exist_ok=True)
    safe_model = model.replace(":", "-").replace("/", "-")
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = RUNS_DIR / f"{timestamp}-{mode}-{safe_model}.md"
    path.write_text(
        f"""# Local Delegation Run

- Mode: `{mode}`
- Model: `{model}`
- Time: `{timestamp}`

## Task

{task}

## Prompt

```text
{prompt}
```

## Local Model Output

{response}
""",
        encoding="utf-8",
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Delegate a bounded subtask to a local Ollama model.")
    parser.add_argument("--mode", default="review", choices=sorted(MODE_PROMPTS.keys()))
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--task", required=True)
    args = parser.parse_args()

    prompt = build_prompt(args.mode, args.task)
    response = call_ollama(args.model, prompt)
    path = save_run(args.mode, args.model, args.task, prompt, response)

    print(response)
    print()
    print(f"Saved: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
