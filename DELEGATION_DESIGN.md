# 本地模型任务分派设计

目标：当你让 Codex 或 Claude 做复杂任务时，可以把一部分低风险、可验证的工作交给本地 Ollama 模型，然后由主模型监督、review、筛选和合并。

## 一句话架构

主模型负责：拆任务、定义验收标准、调用本地模型、审查结果、合并结论。

本地模型负责：并行阅读、初稿、备选方案、候选问题清单、测试想法、摘要和轻量反方检查。

风险 review、严重性判断、架构取舍、最终合并决策必须由 Codex 或 Claude 这样的主控模型完成。

## 默认触发方式

用户不需要每次描述完整策略。只要说：

```text
使用 local-model-delegation，帮我 ...
```

或：

```text
$local-model-delegation 帮我 ...
```

就默认启用：

- 本地模型工作占比不低于 50%。
- 主控模型工作占比不低于 30%。
- 本地模型写任务归档正文。
- 主控模型只轻量 review 归档产物。
- 任务结束后停止本地模型。

默认配置见：

```text
config/delegation_defaults.json
```

## 推荐角色分工

### 适合交给本地模型

- 总结长文档、日志、代码片段。
- 提炼需求、列边界条件。
- 给出实现方案候选。
- 做代码局部问题扫描，输出候选发现。
- 生成测试用例想法。
- 生成命令、配置、文档草稿。
- 作为轻量“反方”列出可能遗漏，不能判断风险等级或最终是否采纳。

### 不适合直接交给本地模型

- 直接改核心代码。
- 做风险 review 或决定最终架构。
- 操作生产数据、密钥、账号、支付、发布。
- 做无法验证的事实判断。
- 处理特别长、特别复杂、上下文依赖很强的任务。

## 工作流

### 1. 主模型拆分任务

主模型先把用户目标拆成：

- 主任务：最终要交付什么。
- 子任务：可以独立完成的部分。
- 输入材料：本地模型需要看的内容。
- 输出格式：必须结构化，方便 review。
- 禁止事项：本地模型不能越界做什么。
- 验收标准：主模型用什么标准筛选结果。
- 工作量占比：用 work units 预估主控模型和本地模型各承担多少候选工作。

### 1.5 配置工作量占比

占比不是精确的 token 数或真实智力贡献，而是可执行的 `work units`：

- 1 unit：很小的摘要、提取、检查或草稿。
- 2 units：中等复杂度的候选测试、候选方案、日志归纳。
- 3 units：较复杂但仍可边界化的多材料整理或对比。

用户可以配置最低占比，例如：

```text
本地模型占比不低于 50%，主控模型占比不低于 30%。
```

解释：

- 本地模型至少承担 50% 的候选工作量。
- 主控模型至少承担 30% 的监督、review、风险判断、最终合并工作量。
- 剩余 20% 可以根据任务需要分配。
- 如果两个最低值相加超过 100%，主控模型必须指出配置不可满足。

检查示例：

```bash
python3 scripts/delegation_mix.py examples/delegation_mix.example.json \
  --min-local 50 \
  --min-controller 30 \
  --assess
```

### 1.6 主控模型评估占比是否合理

默认占比不是硬性凑数。主控模型必须判断当前任务是否适合默认 50/30：

- 如果是高风险任务，提高主控占比，降低本地占比。
- 如果是资料整理、归档、摘要任务，提高本地占比。
- 如果是代码实现任务，主控占比通常要高于本地模型。
- 如果可委派任务不足，报告实际可达占比，不要为了满足数字把不安全任务交给本地模型。

可用建议脚本：

```bash
python3 scripts/suggest_work_split.py --profile high-risk
python3 scripts/suggest_work_split.py --profile implementation
python3 scripts/suggest_work_split.py --profile archive
```

主控模型反馈格式：

```text
占比合理性：
- 默认目标：Local >= 50%，Controller >= 30%
- 本任务建议：Local 35%，Controller 50%
- 调整原因：代码实现需要主控读代码、修改和验证，本地模型只适合做候选测试与摘要。
- 不可外包：风险 review、最终实现判断、文件修改。
```

### 1.7 真实本地模型消耗统计

`work units` 是计划口径；Ollama token 统计是真实本地模型调用口径。

新的本地模型调用会记录：

- prompt tokens
- output tokens
- total local tokens
- total duration
- output tokens/s

查看汇总：

```bash
python3 scripts/local_usage.py
python3 scripts/local_usage.py --recent 5
```

任务归档会额外生成：

```text
LOCAL_MODEL_USAGE.md
```

注意：这个工具不能直接读取云端主控模型 token。主控模型节省量应表达为：

- 精确口径：本地模型实际消耗了多少 token/耗时。
- 近似口径：这些本地 token 对应的摘要、提取、候选测试、归档整理若不分派，将由主控模型承担。

### 2. 本地模型执行子任务

用脚本调用 Ollama：

```bash
./scripts/delegate.sh critic-lite qwen3:8b "列出这段方案中可能遗漏或含糊的地方：..."
./scripts/delegate.sh test-ideas deepseek-r1:8b "给这个功能设计测试用例：..."
./scripts/delegate.sh summarize qwen3:8b "总结下面日志的关键信息：..."
```

脚本会把输出保存到：

```text
runs/YYYYMMDD-HHMMSS-mode-model.md
```

### 2.1 主控模型选择本地模型

主控模型必须为每个子任务选择合适的本地模型，而不是固定使用同一个模型。

默认规则：

- `qwen3:8b`：摘要、提取、文档草稿、归档正文、轻量反方检查。
- `deepseek-r1:8b`：候选测试、bug 假设、小范围推理。
- `qwen3:14b`：质量优先的整理、对比、归档。
- `deepseek-r1:14b`：质量优先的候选推理。
- `gemma3:12b`：多模态候选任务。

选择脚本：

```bash
python3 scripts/select_model.py summarize
python3 scripts/select_model.py test-ideas
python3 scripts/select_model.py compare --quality quality
```

如果推荐模型未安装，主控模型应选择已安装的相近模型，并说明降级原因。

### 3. 主模型 review

主模型必须判断：

- 哪些结论可信。
- 哪些结论需要验证。
- 哪些结论错误或不相关。
- 是否有遗漏的新风险。
- 是否要补问本地模型一轮。

### 4. 合并回主线

只有通过 review 的内容才能进入最终方案、代码或文档。

合并时要明确标记：

- 采纳了什么。
- 丢弃了什么。
- 需要人工确认什么。
- 最终实际占比：主控模型和本地模型各承担了多少 work units。

### 4.5 生成任务归档

任务结束后创建独立归档文件夹，记录本次主控/本地模型分工、占比统计和汇总文档。

本地模型默认负责生成 `TASK_SUMMARY.md` 的归档正文，减少主控模型 token 消耗。

主控模型只做轻量 review：

- 是否编造了未提供事实。
- 是否越界做了风险、架构、发布或最终判断。
- 占比数字是否和 `WORK_SPLIT.md` / `work_split.result.json` 一致。
- 哪些内容需要标记为信息不足。

本地模型不能直接创建文件夹或写文件。文件创建由主控脚本完成。

```bash
python3 scripts/finalize_task.py \
  --title "任务标题" \
  --plan-json examples/delegation_mix.example.json \
  --min-local 50 \
  --min-controller 30 \
  --summary-model qwen3:8b \
  --stop-after
```

输出目录：

```text
task_records/YYYYMMDD-HHMMSS-task-title/
```

固定产物：

- `TASK_SUMMARY.md`
- `ARCHIVE_REVIEW.md`
- `WORK_SPLIT.md`
- `LOCAL_MODEL_USAGE.md`
- `work_split.plan.json`
- `work_split.result.json`
- `LOCAL_RUNS_EXCERPT.md`

### 5. 停止本地模型

任务结束后停止当前本地模型，避免继续占用内存和后台资源：

```bash
./scripts/stop_local_models.sh
```

如果还要继续频繁使用本地模型，可以只卸载当前模型，不停服务：

```bash
ollama stop qwen3:8b
ollama stop deepseek-r1:8b
```

## 推荐模型选择

### `qwen3:8b`

默认选择。适合摘要、文档草稿、普通 review、需求拆解。

### `deepseek-r1:8b`

适合推理、算法、复杂 bug 分析、测试策略。

### `gemma3:12b`

适合通用对话和多模态尝试。

### `qwen3:14b` / `deepseek-r1:14b`

适合质量要求更高但不急的子任务。你的 24GB 内存可以跑，但速度会更慢。

## 分派协议模板

主模型给本地模型的任务建议统一长这样：

```text
你是本地辅助模型，只做子任务，不做最终决策。

任务类型：critic-lite
背景：
...

输入：
...

请输出：
1. 可能遗漏
2. 不确定性
3. 可验证建议
4. 需要主控模型判断的部分

约束：
- 不要假设没有给出的事实。
- 不要修改文件。
- 不要输出风险等级、最终结论或采纳建议，只输出候选意见。
- 如果信息不足，明确写出缺口。
```

## 主模型 review 清单

主模型拿到本地模型结果后，按这个顺序检查：

1. 是否回答了子任务。
2. 是否引入了未经提供的事实。
3. 是否有明显幻觉。
4. 是否和现有代码、文档、日志冲突。
5. 是否可验证。
6. 是否值得合并进主线。
7. 风险等级、架构取舍、最终结论是否由主控模型自己完成。

## 最小可用方式

你可以在跟 Codex 或 Claude 对话时这样说：

```text
请把需求摘要、测试用例候选、轻量反方检查分别委托给本地模型 qwen3:8b 或 deepseek-r1:8b。
本地模型只出候选意见，你负责审查、取舍和合并。
```

更精确一点：

```text
把日志摘要交给 qwen3:8b，把候选 bug 假设交给 deepseek-r1:8b。
你要生成明确子任务指令，调用本地模型，review 输出，然后再给我最终结论。
```

## 推荐落地路线

第一阶段：手动调用脚本，本地模型只做草稿。

第二阶段：Codex 在任务中按需调用 `scripts/local_delegate.py`，把结果保存到 `runs/`。

第三阶段：给项目加一份 `LOCAL_DELEGATION.md`，定义哪些任务可以外包给本地模型。

第四阶段：如果稳定，再做成 MCP 工具或 Claude/Codex 插件。
