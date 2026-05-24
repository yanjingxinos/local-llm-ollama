#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import sys

import delegation_mix
import local_delegate


ROOT = pathlib.Path(__file__).resolve().parents[1]
TASK_RECORDS_DIR = ROOT / "task_records"


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", text).strip("-")
    return slug[:60] or "task"


def read_text(path: pathlib.Path | None) -> str:
    if not path:
        return ""
    return path.read_text(encoding="utf-8")


def split_report(result: dict, min_local: float, min_controller: float) -> str:
    lines = [
        "# Work Split",
        "",
        f"- Controller: {result['controller_units']:.1f} units ({result['controller_pct']:.1f}%)",
        f"- Local: {result['local_units']:.1f} units ({result['local_pct']:.1f}%)",
        f"- Total: {result['total']:.1f} units",
        f"- Minimum local: {min_local:.1f}%",
        f"- Minimum controller: {min_controller:.1f}%",
        "",
        "## Status",
        "",
    ]

    passed = True
    if result["local_pct"] + 1e-9 < min_local:
        lines.append(f"- FAIL: local is below {min_local:.1f}%")
        passed = False
    if result["controller_pct"] + 1e-9 < min_controller:
        lines.append(f"- FAIL: controller is below {min_controller:.1f}%")
        passed = False
    if passed:
        lines.append("- PASS: split satisfies configured minimums.")

    lines.extend(["", "## Tasks", ""])
    for name, owner, units in result["rows"]:
        lines.append(f"- `{owner}` {units:.1f} units: {name}")
    lines.append("")
    return "\n".join(lines)


def build_summary_prompt(title: str, plan: dict, split_md: str, local_outputs: str, notes: str) -> str:
    return f"""你是本地辅助模型，负责生成任务结束归档正文。
你不能做最终判断，不能声称已经创建文件，不能修改文件，不能引入未提供事实。
主控模型只会对你的最终归档产物做轻量 review。

任务标题：
{title}

工作量计划 JSON：
```json
{json.dumps(plan, ensure_ascii=False, indent=2)}
```

工作量占比统计：
{split_md}

主控模型补充 notes：
{notes or "无"}

本地模型原始输出摘录：
{local_outputs or "无"}

请输出任务结束归档正文，格式如下：
1. 任务目标
2. 本地模型承担的工作
3. 主控模型承担的工作
4. 占比统计结论
5. 已采纳内容
6. 已丢弃或需要谨慎处理的内容
7. 后续建议

边界：
- 不要做风险等级判断。
- 不要做最终决策。
- 信息不足时写“信息不足”。
- 不要根据 notes 为空推断主控模型没有执行某项工作，只能写“未提供主控 notes”。
- 如果原始输出中出现“回归风险”，请在汇总中改写为“回归测试候选”，不要当作风险 review。
- 尽量把归档整理完整，减少主控模型二次改写成本。
- 使用中文。
"""


def collect_recent_runs(limit: int) -> str:
    runs_dir = ROOT / "runs"
    if not runs_dir.exists() or limit <= 0:
        return ""

    paths = sorted(runs_dir.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]
    chunks = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        chunks.append(f"## {path.name}\n\n{text[:4000]}")
    return "\n\n".join(chunks)


def write_json(path: pathlib.Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stop_local_models() -> None:
    script = ROOT / "scripts" / "stop_local_models.sh"
    if script.exists():
        subprocess.run([str(script)], check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a final task record with work split statistics.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--plan-json", required=True)
    parser.add_argument("--min-local", type=float, default=0.0)
    parser.add_argument("--min-controller", type=float, default=0.0)
    parser.add_argument("--summary-model", default="")
    parser.add_argument("--notes-file", default="")
    parser.add_argument("--recent-runs", type=int, default=3)
    parser.add_argument("--stop-after", action="store_true")
    args = parser.parse_args()

    if args.min_local + args.min_controller > 100:
        raise SystemExit("Minimum local and controller percentages cannot sum above 100.")

    plan_path = pathlib.Path(args.plan_json)
    plan = delegation_mix.load_plan(plan_path)
    result = delegation_mix.compute(plan.get("tasks", []))

    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    record_dir = TASK_RECORDS_DIR / f"{timestamp}-{slugify(args.title)}"
    record_dir.mkdir(parents=True, exist_ok=False)

    shutil.copy2(plan_path, record_dir / "work_split.plan.json")
    write_json(
        record_dir / "work_split.result.json",
        {
            "title": args.title,
            "minimums": {
                "local_pct": args.min_local,
                "controller_pct": args.min_controller,
            },
            "result": {
                "controller_units": result["controller_units"],
                "local_units": result["local_units"],
                "total_units": result["total"],
                "controller_pct": result["controller_pct"],
                "local_pct": result["local_pct"],
            },
            "tasks": [
                {"name": name, "owner": owner, "units": units}
                for name, owner, units in result["rows"]
            ],
        },
    )

    split_md = split_report(result, args.min_local, args.min_controller)
    (record_dir / "WORK_SPLIT.md").write_text(split_md, encoding="utf-8")

    notes = read_text(pathlib.Path(args.notes_file) if args.notes_file else None)
    local_outputs = collect_recent_runs(args.recent_runs)

    summary_source = "controller-template"
    if args.summary_model:
        prompt = build_summary_prompt(args.title, plan, split_md, local_outputs, notes)
        try:
            summary = local_delegate.call_ollama(args.summary_model, prompt)
            summary_source = f"local-model:{args.summary_model}"
            (record_dir / "local_summary_prompt.txt").write_text(prompt, encoding="utf-8")
        except SystemExit as exc:
            summary = f"本地模型汇总不可用：{exc}\n\n{split_md}"
    else:
        summary = f"""# Task Summary

任务：{args.title}

本次未调用本地模型生成汇总草稿。

{split_md}
"""

    summary_md = f"""# Task Summary

- Title: {args.title}
- Time: {timestamp}
- Summary source: {summary_source}
- Review required: controller-light-review

{summary}
"""
    (record_dir / "TASK_SUMMARY.md").write_text(summary_md, encoding="utf-8")

    review_md = f"""# Archive Review

- Title: {args.title}
- Time: {timestamp}
- Summary source: {summary_source}
- Status: pending-controller-review

## Controller Review Checklist

- [ ] The archive does not invent facts beyond supplied plan, notes, or local outputs.
- [ ] The archive does not make final risk, architecture, release, or safety decisions.
- [ ] Work split numbers match `WORK_SPLIT.md` and `work_split.result.json`.
- [ ] Accepted/rejected items are clearly marked as controller-reviewed or information-insufficient.
- [ ] Any local-model wording that overreaches has been corrected or noted.

## Controller Notes

Pending.
"""
    (record_dir / "ARCHIVE_REVIEW.md").write_text(review_md, encoding="utf-8")

    if notes:
        (record_dir / "CONTROLLER_NOTES.md").write_text(notes, encoding="utf-8")
    if local_outputs:
        (record_dir / "LOCAL_RUNS_EXCERPT.md").write_text(local_outputs, encoding="utf-8")

    print(f"Task record created: {record_dir}")
    print()
    print(split_md)

    if args.stop_after:
        print("Stopping local models...")
        stop_local_models()

    return 0


if __name__ == "__main__":
    sys.exit(main())
