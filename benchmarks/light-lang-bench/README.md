# light-lang-bench · 光明语言专项评测（6 项落地交付）

> 对应方案：`06-design/评测方案修订版.md`
> 生成日期：2026-11-16 · 基准仓库：`/home/skywalk/dswork/light` v0.4.2

## 目录

```
01-spec/MiniLog规格.md          语言无关规格（v1/v2），276 行
02-tests/
  generate_suite.py             生成 fixtures + 用例表
  run_suite.py                  黑盒 runner（只依赖 ./minilog）
  cases/visible.json            33 例，随任务包下发
  cases/hidden.json             20 例，物理隔离，最终评分才用
  fixtures/                     19 个文件（含 1 MiB 单行、5000 行批量）
03-judge/
  rubric.md                     地道度 5 指标 + 实测标定阈值 + kappa 流程
  examples/E-01..E-06.md        6 份人工标注校准样例
04-reference/python/minilog.py  Python oracle（不计入评测）
05-analysis/
  l0_density.py                 L0 密度静态分析（校准样例上验证过）
  dsh_analyze.py                DSH 轨迹分析（3 adapter + selftest）
06-design/评测方案修订版.md    逐条审查 + 事实核实 + 修订后的执行流程
minilog                         oracle 的副本，用于本地验收
```

## 快速验收（30 秒）

```bash
cd light-lang-bench

# 1. 重新生成用例与 fixtures
python3 02-tests/generate_suite.py

# 2. 用 oracle 对拍全部 53 例（应 100% 通过）
cp 04-reference/python/minilog.py ./minilog
python3 02-tests/run_suite.py --target ./minilog --suite all --stage v2 \
    --json /tmp/minilog-report.json

# 3. 静态分析器在 6 份校准样例上的实测值（用于 rubric D2 阈值复标）
python3 05-analysis/l0_density.py /tmp/judge_code/*.light   # 需先抽取，见下

# 4. 轨迹分析器自测
python3 05-analysis/dsh_analyze.py --selftest
```

抽取校准样例代码到 `/tmp/judge_code/`：

```bash
mkdir -p /tmp/judge_code
python3 - <<'PY'
import re, os
for fn in sorted(os.listdir("03-judge/examples")):
    s = open("03-judge/examples/"+fn, encoding="utf-8").read()
    m = re.search(r"```光明\n(.*?)\n```", s, re.S)
    if m:
        open("/tmp/judge_code/"+fn.replace(".md",".light"),"w",encoding="utf-8").write(m.group(1))
PY
```

## 验收结果（本机实测）

| 项 | 结果 |
|----|------|
| 规格 ↔ 用例 ↔ oracle 对拍 | **53 / 53 PASS**（visible 33 + hidden 20，v2 含 v1 回归） |
| 规格自洽性 | 对拍过程中抓到并修正 1 个用例期望值错误（H-02），证明 oracle 有效 |
| D2 阈值 | 由 6 份校准样例实测标定：0.0000 / 0.2405 / 0.3000 / 0.3171 / 0.3333 / 0.4400 |
| `l0_density.py` | 修正了 `结束引` 定界符 bug；输出 3 类防作弊 flag |
| `dsh_analyze.py --selftest` | 4 组自测全过（normalized / Track B / editlog / unparsed） |

## 用你自己的实现跑

把任意语言实现编译成工作目录下的 `./minilog`（无扩展名、可执行），然后：

```bash
python3 02-tests/run_suite.py --target ./minilog --suite visible --stage v1
python3 02-tests/run_suite.py --target ./minilog --suite visible --stage v2
python3 02-tests/run_suite.py --target ./minilog --suite hidden  --stage v2   # 最终评分
```

runner 逐字节比对 stdout / stderr / `--output` 文件，并检查退出码；
每个用例独立临时目录，输出 JSON 报告可交给 `dsh_analyze.py` 合并。

## 三条不可违背的约定

1. **`hidden.json` 与仅隐藏用例用到的 fixture 不下发给 Agent**，且评测会话之外独立运行。
2. **地道度不参与 Pass@1、不参与六语言排名**；只对 Light 的多次 trial 做纵向观测。
3. **Light trial 必须记录 `backend` / `python_runtime_version` / `uses_ctypes`**，
   环境相关失败从语言能力指标中剥离（详见修订版 §1.4）。

## 已知限制

- 本机没有 DSH Minimal 会话日志的真实 schema 样本，`dsh_analyze.py` 采用公开规范化
  中间格式 + 3 adapter；正式跑之前必须用 1 个真实 trial 确认 adapter 选择。
- 只有 Python 一份 oracle；修订版 §7.1 建议再用 Go 实现做交叉对拍，排除同源错误。
- L3–L7 在光明 v0.4.2 属实验态，Track B 结论只对被测版本 + commit 成立。
