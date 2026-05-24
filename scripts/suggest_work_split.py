#!/usr/bin/env python3
import argparse


PROFILES = {
    "default": {
        "local": 50,
        "controller": 30,
        "reason": "适合一般开发、分析、文档、测试设计任务。"
    },
    "high-risk": {
        "local": 20,
        "controller": 60,
        "reason": "安全、隐私、支付、迁移、发布、数据删除等任务需要主控模型承担更多判断。"
    },
    "research": {
        "local": 60,
        "controller": 30,
        "reason": "资料整理、摘要、对比、候选观点较多，适合提高本地模型占比。"
    },
    "implementation": {
        "local": 35,
        "controller": 50,
        "reason": "代码实现需要主控模型读代码、修改、验证，本地模型适合生成候选测试和摘要。"
    },
    "archive": {
        "local": 70,
        "controller": 20,
        "reason": "任务归档、总结、格式化主要是整理工作，本地模型可承担更多，主控轻量 review。"
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Suggest a safe controller/local work split profile.")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="default")
    args = parser.parse_args()

    profile = PROFILES[args.profile]
    print(f"Suggested split for {args.profile}")
    print(f"- Local minimum: {profile['local']}%")
    print(f"- Controller minimum: {profile['controller']}%")
    print(f"- Reason: {profile['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

