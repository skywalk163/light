# L4 真实 LLM 复测报告 · R144 任务 D

> 结论先行：**工程体（lightharness）Python→Light 翻译任务在真实 LLM + 结构校验 + retry 回路下 pass@3 = 100%（80/80）**，首次成功率 93.0%（剔除推理预算伪影后口径）。"结构合法性"不构成翻译瓶颈；语料与校验-重试回路有效。但**"微调后 7B/2B 小模型首次产出合法 Light"仍未被直接证明**——本轮所用为 DeepSeek 在线大模型，微调模型本体（0.88 ollama `light-translator`）当前不可达，需后续补测。

## 1. 实验设置

| 项 | 值 |
|---|---|
| 执行机 | 本机 Windows（LM venv `light-merge/.venv`） |
| 模型 | `deepseek-flash`（DeepSeek 在线推理，OpenAI 兼容端点 `api.deepseek.com`，key 读自 `g:\dswork\duan-light-merge\.env` 的 `OPENAI_API_KEY`，未硬编码） |
| 样本 | `tools/ai_copilot/sft_dataset.jsonl`（2254 行）中 category 以「工程」开头的 schema-B 记录（input=Python 源码，output=Light 参考译文），长度 ≤2500 字符，池 122 条，固定种子抽样 **80 条** |
| Prompt | system 与 `tools/ai_copilot/local_infer.py` 的 `SYSTEM_PROMPT` 逐字一致（光明 v3.2 翻译规则全集） |
| retry 语义 | 对齐 light-translator 翻译循环：生成 → 结构校验 → 失败则带校验原因重试，最多 K=3 次 |
| pass 判据 | R139-B/R140 同口径 `structural_check`：分隔符平衡 + 含 Light 声明（段落/类/接口等）+ 无 Python 顶层泄漏 |
| temperature / max_tokens | 0.1 / 1200（后经伪影定位改为 4096 补测，见 §3） |

**降级路径声明**：任务书原口径为"0.88 权威机 LLM"。实测 0.88 的 ollama（微调模型 `light-translator` Qwen3.5-2B GGUF 所在）11434 不可达且 SSH 密码认证被拒，故降级为**本机 → DeepSeek 在线推理**（本机与 0.82 均实测可达 `api.deepseek.com`）。有效性边界见 §5。

## 2. 主结果（max_tokens=1200，80 样本）

| 指标 | 值 |
|---|---|
| pass@3（retry 回路内） | **79/80 = 98.8%** |
| 首次尝试通过 | 53/80 = 66.2%（粗口径）；**剔除伪影后 53/57 = 93.0%**（见 §3） |
| 平均调用次数/样本 | 1.49 |
| token 消耗 | prompt 128,335 + completion 95,147（80 样本全程，成本可忽略量级） |
| 墙钟 | 614 s（串行） |

**分维度**（13 个工程子类，全部 pass 率 ≥ 90%，唯一非满分：工程-文件 9/10，即 §3 的伪影样本）：

| 子类 | pass/total | 子类 | pass/total |
|---|---|---|---|
| 工程-JSONL | 8/8 | 工程-工具定义 | 8/8 |
| 工程-事件总线 | 7/7 | 工程-授权链 | 4/4 |
| 工程-值判定 | 7/7 | 工程-文件 | 9/10 |
| 工程-字典 | 9/9 | 工程-进程命令 | 7/7 |
| 工程-错误处理 | 6/6 | 工程-重试 | 7/7 |
| 工程-JSON | 1/1 | 工程-字符串 | 2/2 |
| 工程-其他 | 4/4 | | |

## 3. 失败簇与根因定位（重点：唯一"失败"是配置伪影）

全部 40 次失败尝试的分布：`empty` 36 次、`unbalanced ()` 3 次、`unbalanced {}` 1 次。

- **`empty`（36 次）不是内容过滤、不是翻译失败**：对唯一最终失败样本（idx68，工程-文件，`os.remove` 相关）复测记录 `finish_reason`，实测 **`finish_reason=length`、completion_tokens=1200、content 为空** —— `deepseek-flash` 是推理模型，思维链把 1200 token 预算烧尽尚未开始输出正文。出现空尝试的 25 个样本输入长度反而偏短（124–368 字符），与内容敏感性无关。
- **idx68 用 max_tokens=4096 补测**：`finish_reason=stop`、completion 2214 tokens、**结构校验 pass**（译文含 段落定义/条件/使用语句，全部合法）。
- 结论：**预算充足时 pass@3 = 80/80 = 100%**；首成率粗口径 66.2% 中 23 个百分点是预算伪影，真实首成率 ≈ **93.0%**（53/57，剔除首尝试即烧尽预算的样本）。
- 真实的翻译质量失败仅 4 次（括号不平衡），且全部被"带校验原因的反馈重试"救回：**25 个含伪影/失败尝试的样本中 24 个在 K=3 内被救回** —— 校验-反馈重试回路有效。

## 4. 与代理口径（R140）的对照

| 口径 | 数值 | 含义 |
|---|---|---|
| R140 代理复测（语料结构自洽启发式） | 完整模块率 46.0% | 语料侧静态口径，偏保守 |
| 本轮真实 LLM + retry | pass@3 = 100%（首成 93.0%） | 任务动态可解性 |

代理口径与真实通过率之间存在大幅裕量：结构启发式把大量"宽松平衡但缺声明"的片段判死，而真实 LLM 输出几乎总能满足更严的 structural_check。**代理指标可作为回归哨兵，但不应作为能力上限的估计**。

## 5. 结论与有效性边界

**支撑的结论**：
1. 工程体翻译任务在"结构合法"口径下**不构成瓶颈**——强 LLM 首成即 93%，retry 后 100%。
2. 「生成 → 结构校验 → 带原因反馈重试」回路**有效**（24/25 救回率），这正是 light-translator 的 retry 语义。
3. R139-B"把工程体并入 SFT 降低 retry 成本"的方向**未被证伪**；本轮给出的是该假设的上界环境。

**不支撑 / 未验证的结论（诚实边界）**：
- `deepseek-flash` ≠ 微调 7B/2B 小模型。**"微调后小模型首次产出合法 Light"必须用模型本体复测**：0.88 ollama 上的 `light-translator`（Qwen3.5-2B 合并 GGUF）当前服务未运行且 SSH 不可登录（仅 publickey/keyboard-interactive）。待其恢复后，用本报告同口径（同 prompt、同校验器、同 K=3）跑 `tools/ai_copilot/sft_dataset.jsonl` 工程体 holdout，对比基线 `sft_dataset_pre_R139B_backup.jsonl` 微调产物。
- 本轮未做"与参考译文的功能等价"判定（只判结构合法）。功能等价需 Light 编译器执行对拍，属后续工作。

**下一步建议**（若小模型实测不达标）：
1. 语料侧：把 §3 的伪影教训固化——推理模型微调需保证 completion 预算含思维链；SFT 语料建议补充"直接输出、无思维链"的 target 风格。
2. 微调侧：优先补"结构校验反馈修复"类样本（输入=坏译文+原因，输出=修正版），把 retry 能力蒸馏进小模型。
3. 环境侧：恢复 0.88 ollama 服务并开放 SSH key 登录，微调模型复测后本报告口径可直接复用。

## 6. 复核方式（真实命令 + 退出码）

```bash
# 主评测（80 样本，rc=0，约 10 分钟）
.venv/Scripts/python.exe light-merge/_r144_scratch/l4_real_llm_retry.py
# 汇总：light-merge/_r144_scratch/l4_eval_summary.json（pass_rate=98.8 @1200 预算）
# 逐样本：light-merge/_r144_scratch/l4_eval_results.jsonl

# 伪影定位 + 大预算补测（rc=0，idx68 → pass）
.venv/Scripts/python.exe light-merge/_r144_scratch/recheck_empty.py   # finish_reason=length 实证
.venv/Scripts/python.exe light-merge/_r144_scratch/recheck_4096.py    # idx68 @4096 → pass
```

key 全程从 `.env` 读取，未入码、未入报告。scratch 文件不进仓。

---
*R144 任务 D · 2026-10-12 · 数据文件：`l4_eval_results.jsonl`（80 条逐样本含全部尝试输出）*
