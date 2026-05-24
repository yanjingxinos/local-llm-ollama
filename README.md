# Mac 本地大模型使用指南

适用机器：Apple Silicon Mac，尤其是 24GB 统一内存的 MacBook Pro。

本目录帮你管理这些 Ollama 模型：

- `qwen3:8b`：推荐作为日常主力，中文、英文、代码都比较均衡。
- `deepseek-r1:8b`：推荐用于推理、数学、代码分析。
- `gemma3:12b`：推荐用于通用对话，也适合尝试多模态能力。
- `qwen3:14b`：比 8B 质量更好，但速度更慢。
- `deepseek-r1:14b`：推理质量更好，但速度更慢。

## 1. 安装 Ollama

如果已经安装过，可以跳过。

```bash
cd /Users/yan/个人/local-llm-ollama
./scripts/install_ollama.sh
```

安装完成后检查：

```bash
./scripts/check_ollama.sh
```

看到 `Ollama is running` 或模型列表，就说明服务正常。

## 2. 下载模型

下载全部推荐模型：

```bash
./scripts/pull_models.sh
```

如果网络慢，建议先只下 8B：

```bash
ollama pull qwen3:8b
ollama pull deepseek-r1:8b
```

下载中断也没关系，重新执行同一个 `ollama pull ...` 通常会继续复用已下载的部分。

## 3. 查看已安装模型

```bash
ollama list
```

## 4. 直接聊天

```bash
ollama run qwen3:8b
ollama run deepseek-r1:8b
ollama run gemma3:12b
```

也可以用脚本：

```bash
./scripts/chat.sh qwen3:8b
./scripts/chat.sh deepseek-r1:8b
```

## 5. 单次提问

```bash
ollama run qwen3:8b "用三句话解释什么是向量数据库"
```

## 6. 简单测速

```bash
./scripts/benchmark.sh qwen3:8b
./scripts/benchmark.sh deepseek-r1:8b
./scripts/benchmark.sh qwen3:14b
```

测速脚本会问一个固定问题，方便你比较不同模型的响应速度和答案质量。

## 7. 本地 API 使用

Ollama 默认 API 地址：

```text
http://127.0.0.1:11434
```

curl 示例：

```bash
curl http://127.0.0.1:11434/api/generate \
  -d '{
    "model": "qwen3:8b",
    "prompt": "写一个 SwiftUI 的计时器示例",
    "stream": false
  }'
```

Python 示例见：

```bash
python3 examples/ollama_api_example.py
```

## 8. 推荐使用策略

日常写作、翻译、代码问答：

```bash
ollama run qwen3:8b
```

复杂推理、算法、数学：

```bash
ollama run deepseek-r1:8b
```

想比较更强质量：

```bash
ollama run qwen3:14b
ollama run deepseek-r1:14b
```

如果 14B 感觉卡，就回到 8B。你的 24GB 内存跑 8B 会更舒服。

## 9. 常用维护命令

停止 Ollama 服务：

```bash
brew services stop ollama
```

启动 Ollama 服务：

```bash
brew services start ollama
```

任务结束后停止本地模型和 Ollama 服务：

```bash
./scripts/stop_local_models.sh
```

删除某个模型：

```bash
ollama rm qwen3:14b
```

查看磁盘占用：

```bash
du -sh ~/.ollama
```

## 10. 把子任务分给本地模型

设计文档见：

```bash
open DELEGATION_DESIGN.md
```

默认用法很短：

```text
使用 local-model-delegation，帮我完成这个任务：...
```

或：

```text
$local-model-delegation 帮我 ...
```

只要你点名这个 skill，就默认使用：

- 本地模型占比不低于 50%。
- 主控模型占比不低于 30%。
- 任务结束归档由本地模型写。
- 主控模型只轻量 review 归档产物。
- 任务结束后停止本地模型。

默认配置文件：

```text
config/delegation_defaults.json
```

最小用法：

```bash
./scripts/delegate.sh critic-lite qwen3:8b "列出这个方案可能遗漏或含糊的地方：..."
./scripts/delegate.sh test-ideas deepseek-r1:8b "给登录功能设计测试用例：..."
./scripts/delegate.sh critic qwen3:14b "作为反方审查这个架构方案：..."
```

输出会保存到：

```text
runs/YYYYMMDD-HHMMSS-mode-model.md
```

推荐原则：本地模型只产出候选意见，风险 review、最终判断、取舍和合并仍由 Codex、Claude 或你本人完成。

配置和检查主控/本地模型工作量占比：

```bash
python3 scripts/delegation_mix.py examples/delegation_mix.example.json \
  --min-local 50 \
  --min-controller 30 \
  --assess
```

这里的占比是 `work units`，不是精确 token 数。本地模型占比代表它承担了多少候选摘要、提取、测试想法、轻量扫描等工作；主控模型占比代表监督、review、风险判断、最终合并等工作。

按任务类型建议占比：

```bash
python3 scripts/suggest_work_split.py --profile default
python3 scripts/suggest_work_split.py --profile high-risk
python3 scripts/suggest_work_split.py --profile implementation
python3 scripts/suggest_work_split.py --profile archive
```

主控模型可以调整默认占比，但必须说明原因。

任务结束后创建归档文件夹、写入占比统计，并让本地模型生成汇总草稿：

```bash
python3 scripts/finalize_task.py \
  --title "登录功能测试设计" \
  --plan-json examples/delegation_mix.example.json \
  --min-local 50 \
  --min-controller 30 \
  --summary-model qwen3:8b \
  --stop-after
```

归档会写入：

```text
task_records/YYYYMMDD-HHMMSS-task-title/
```

里面包括：

- `TASK_SUMMARY.md`：本地模型生成的任务结束归档正文。
- `ARCHIVE_REVIEW.md`：主控模型轻量 review 清单。
- `WORK_SPLIT.md`：主控/本地模型占比统计。
- `work_split.plan.json`：任务拆分计划。
- `work_split.result.json`：机器可读统计结果。
- `LOCAL_RUNS_EXCERPT.md`：最近本地模型输出摘录。

原则：归档正文默认交给本地模型做，主控模型只 review 最终产物是否越界、是否编造、占比是否一致。

任务结束后建议执行：

```bash
./scripts/stop_local_models.sh
```
