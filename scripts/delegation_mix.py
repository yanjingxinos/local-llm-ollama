#!/usr/bin/env python3
import argparse
import json
import pathlib
import sys


def load_plan(path: pathlib.Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def compute(tasks: list[dict]) -> dict:
    totals = {"controller": 0.0, "local": 0.0}
    rows = []

    for index, task in enumerate(tasks, start=1):
        owner = task.get("owner", "")
        units = float(task.get("units", 1))
        name = task.get("name", f"task-{index}")

        if owner not in totals:
            raise SystemExit(f"Invalid owner for {name}: {owner}. Use controller or local.")

        totals[owner] += units
        rows.append((name, owner, units))

    total = totals["controller"] + totals["local"]
    if total == 0:
        raise SystemExit("Total units must be greater than 0.")

    return {
        "rows": rows,
        "total": total,
        "controller_units": totals["controller"],
        "local_units": totals["local"],
        "controller_pct": totals["controller"] / total * 100,
        "local_pct": totals["local"] / total * 100,
    }


def assess(result: dict, min_local: float, min_controller: float) -> list[str]:
    feedback = []
    local_pct = result["local_pct"]
    controller_pct = result["controller_pct"]

    if min_local + min_controller > 100:
        feedback.append("配置不合理：本地模型和主控模型最低占比之和超过 100%。")
        return feedback

    if local_pct + 1e-9 < min_local:
        feedback.append(
            f"本地模型占比不足：当前 {local_pct:.1f}%，低于要求 {min_local:.1f}%。"
        )
    if controller_pct + 1e-9 < min_controller:
        feedback.append(
            f"主控模型占比不足：当前 {controller_pct:.1f}%，低于要求 {min_controller:.1f}%。"
        )

    if local_pct > 75:
        feedback.append("本地模型占比偏高：请确认没有把风险 review、架构判断或最终决策外包。")
    if controller_pct < 25:
        feedback.append("主控模型占比偏低：可能不足以完成监督、验证和最终合并。")
    if local_pct < 20:
        feedback.append("本地模型占比偏低：如果任务有摘要、提取、测试候选或归档整理，可增加本地模型参与。")
    if controller_pct > 80:
        feedback.append("主控模型占比偏高：如果不是高风险任务，可以考虑把摘要、提取或归档交给本地模型。")

    local_tasks = [row for row in result["rows"] if row[1] == "local"]
    controller_tasks = [row for row in result["rows"] if row[1] == "controller"]
    if not local_tasks:
        feedback.append("没有本地模型任务：除非任务完全不可委派，否则应添加可验证的小任务。")
    if not controller_tasks:
        feedback.append("没有主控模型任务：不允许，必须保留主控 review 和最终判断。")

    if not feedback:
        feedback.append("分配看起来合理：满足最低占比，且没有明显过度外包或过度集中在主控模型。")

    return feedback


def main() -> int:
    parser = argparse.ArgumentParser(description="Check controller/local model work split.")
    parser.add_argument("plan_json", help="JSON file containing tasks with owner and units.")
    parser.add_argument("--min-controller", type=float, default=0.0)
    parser.add_argument("--min-local", type=float, default=0.0)
    parser.add_argument("--assess", action="store_true", help="Print allocation quality feedback.")
    args = parser.parse_args()

    plan = load_plan(pathlib.Path(args.plan_json))
    result = compute(plan.get("tasks", []))

    print("Work split")
    print(f"- Controller: {result['controller_units']:.1f} units ({result['controller_pct']:.1f}%)")
    print(f"- Local:      {result['local_units']:.1f} units ({result['local_pct']:.1f}%)")
    print(f"- Total:      {result['total']:.1f} units")
    print()

    print("Tasks")
    for name, owner, units in result["rows"]:
        print(f"- {owner:10s} {units:4.1f}  {name}")

    print()
    if args.assess:
        print("Allocation feedback")
        for item in assess(result, args.min_local, args.min_controller):
            print(f"- {item}")
        print()

    failed = False
    if result["controller_pct"] + 1e-9 < args.min_controller:
        print(f"FAIL: controller is below minimum {args.min_controller:.1f}%")
        failed = True
    if result["local_pct"] + 1e-9 < args.min_local:
        print(f"FAIL: local is below minimum {args.min_local:.1f}%")
        failed = True

    if not failed:
        print("PASS: split satisfies configured minimums.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
