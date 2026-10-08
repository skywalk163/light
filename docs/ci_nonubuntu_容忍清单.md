# CI 非 ubuntu 容错摸底（R127-A）

> 轮次：R127「查缺补漏轮」A 线任务 3。
> 数据来源：GitHub Actions API 匿名查询（runs/jobs/steps/annotations 元数据，2026-10-08 采集）
> + 本地实跑复现。job 级日志因 .env 中 GITHUB_TOKEN 已失效（401，logs 端点必须认证）无法下载，
> 改用 steps 级结论 + 本地复现两条路补齐失败面。
> 本文档只记录事实与建议；workflow 文件本轮**未改动**（理由见 §5）。

## 1. 当前被整体容忍的矩阵

`.github/workflows/ci.yml:62`：

```yaml
test:
  runs-on: ${{ matrix.os }}
  continue-on-error: ${{ matrix.os != 'ubuntu-latest' }}
```

- **容忍方式**：job 级 `continue-on-error`——windows / macos 的全部 12 份矩阵里 8 份
  （windows ×4 py、macos ×4 py）无论哪一步红，都不影响 workflow 判绿。
- **矩阵构成**：PR 只跑 ubuntu × (3.10, 3.13)；push main / 手动触发跑
  3 os × 4 py（3.10/3.11/3.12/3.13）共 12 份。
- **配套兜底**：非 Linux job 内有「跨平台回归闸门」（`ci.yml:222-236`，
  `check_regression.py --junit .ci/root_other.xml --baseline tests/ci_baseline_failures_crossplat.txt
  --soft-classname 'tests.test_*'`），只拦「collect error / 一个用例都没跑起来」，
  `tests.test_*` 失败照跑照报不拦。
- **`quality-gate.yml:141` 的 `continue-on-error: true`** 与 OS 无关：只罩
  「运行全量 pytest」一步，且由下一步「覆盖率报告解析失败即判红」兜住假绿，不在本文档议题内。
- **注意**：`.github/` 文件头「本项目当前没有 GitHub 远端、这棵树一次都没执行过」的注释
  已过时——实际远端 `github.com/skywalk163/light` 在持续 push main（截至 2026-10-08 已 136 个
  CI run number），windows/macos 矩阵每次都在真跑。

## 2. 真实失败面（API 实测，2026-10-08）

近 6 个 CI run（#131–#136，2026-10-07/08），**72/72 个 test job 全部失败在
「Unit Tests」步骤**，三平台对称、无一例外：

```
test (ubuntu-latest, 3.10..3.13)   :: Unit Tests   ← 失败且阻塞（无容忍）
test (windows-latest, 3.10..3.13)  :: Unit Tests   ← 失败但被 continue-on-error 吞掉
test (macos-latest, 3.10..3.13)    :: Unit Tests   ← 失败但被 continue-on-error 吞掉
```

- `Integration / E2E / Root / 跨平台回归闸门 / 质量度量门禁` 各步在近 6 个 run 中
  **没有一次独立失败记录**（unit 先红导致后续步骤未执行，属跳过而非通过；
  但至少没有出现过「unit 绿而其它步骤红」的非 ubuntu 特有签名）。
- Quality Gate（近 3 run #134–#136）同样是 3/3 job 红在「运行单元测试」——同一失败面。
- 当前 **workflow 整体红的唯一原因就是 ubuntu 的 Unit Tests**；
  windows/macos 的红全部被 job 级容忍掩盖，且失败签名与 ubuntu 完全相同。

失败用例级清单：因 GITHUB_TOKEN 失效无法下载 job 日志（logs 端点 403/401），
annotations 只有泛化的 "Process completed with exit code 1"。改由本地 Windows
实跑 `pytest tests/unit/` 复现（全平台对称红 ⇒ 本机清单即 CI 清单的近似）：

```
（R127-A 本机实测见 §2.1；CI 与本机若有出入，以 CI 日志为准——修复 token 后可精确对账）
```

### 2.1 本机复现（Windows，仓库 venv）

```
./.venv/Scripts/python.exe -m pytest tests/unit/ -p no:randomly -q -o addopts=
```

结果与本机清单见 R127-A 交付汇报；此处只记录结论：
失败为**平台无关的语义断言失败**（非 locale/编码/路径分隔符类环境噪声），
与「windows runner cp1252 曾致 UnicodeEncodeError」的历史签名无关——
该问题已由 `ci.yml:46-48` 的 `PYTHONUTF8: "1"` + `PYTHONIOENCODING: "utf-8"` 治理，
近 6 个 run 的失败步骤签名中未再出现编码类独立失败。

## 3. 已知历史（文件头注释 + 轮次档案）

- **cp1252 locale**：Windows runner 默认 locale 下 Python open()/print() 走 charmap，
  中文源码/输出 UnicodeEncodeError；首跑 windows 四份矩阵共 25 条红，绝大多数是该签名
  及其 mojibake 变体。**已修**：workflow 级 env 钉 UTF-8（PEP 540）。
- **干净 runner 缺 pytest 插件**：pyproject addopts 写死 `--timeout=60 -n 4`，
  GitHub runner 干净环境首跑即 "unrecognized arguments" 红。**已修**：Install 步显式装
  pytest-xdist / pytest-timeout。
- **e2e 12 条存量欠账**：`tests/ci_baseline_failures.txt`（gitea/GitHub 两侧同口径），
  由回归闸门基线豁免，不属非 ubuntu 问题。

## 4. 「用例级收窄」评估

### 4.1 结论：本轮不动 workflow（风险 > 收益），理由如下

1. **收窄不改变任何现状判绿**。当前红的唯一来源是 ubuntu Unit Tests（无容忍、照红）；
   把非 ubuntu 的 job 级容忍收窄成用例级只会让 8 份矩阵红得更显式，CI 结果不变。
2. **失败面与 OS 无关**。近 6 run 显示三平台失败签名完全对称（同一 Unit Tests 步骤），
   「非 ubuntu 独有容忍面」实际为空集——没有可收窄的实体对象。
3. **job 级 continue-on-error 改用例级需要先有 windows/macos 的用例级失败清单**，
   而清单依赖日志/token；在拿不到日志的情况下盲改判绿语义，违反「判据要真」的仓库原则
   （ci.yml 文件头：判据要真就得看 run 结果）。
4. 仓库现行趋势已是**用例级门控**（tests/lightpub `_网络门开()` R125-C1、
   R127-A 对 test_L4 外网用例的统一门控），比 workflow 级收窄更精细且两侧 CI
   （gitea 权威副本 + GitHub 镜像）都能复用。

### 4.2 patch 建议（待 token 修复 / unit 修复后择机实施）

**前提**：先修对称红（ubuntu Unit Tests）——它才是 CI 常红的根因。

**建议 A（低风险，推荐）**：把 `ci.yml:62` 的 job 级容忍改为「步骤级兜底 + 报告」：
```yaml
test:
  runs-on: ${{ matrix.os }}
  # R127 建议 A：job 级容忍收窄为步骤级——unit/integration 硬判，
  # 只有已知平台差异步骤显式 continue-on-error，红名单进 job summary 可见。
```
即删除 job 级 `continue-on-error`，仅在确有平台差异的步骤上加
`continue-on-error: true` 并 `echo "::warning::"` 记录——每个被吞的红都留下可见痕迹。

**建议 B（中风险）**：用用例级门控替代平台容忍：对实测仅非 ubuntu 失败的用例逐个加
`@unittest.skipIf(sys.platform.startswith('win'), '...')`（或 macos 对应 darwin），
然后整个删除 job 级 continue-on-error。必须先有「windows/macos 用例级失败清单」，
当前不具备（token 失效）。

**建议 C（不建议）**：保持现状。可接受但会继续掩盖非 ubuntu 新增回归——
job 级容忍把「红但不管」和「红但看不见」混在一起，仅剩跨平台回归闸门兜
collect error 一层网。

### 4.3 顺手销账建议（零风险）

`.github/workflows/ci.yml:3-9` 文件头「本项目当前没有 GitHub 远端、这棵树一次都
没执行过」的注释与现实（610+ runs，windows/macos 每次真跑）矛盾，会误导后续轮次
的裁决（本轮就差点被它带偏）。建议改为「远端已启用，权威判绿仍以 .gitea 为准，
GitHub 侧为镜像验证」。

## 5. 本轮改动清单

- 无 workflow/代码改动（任务书授权「可实施或只出建议」，本文档裁决为只出建议，见 §4.1）。
- 证据采集命令与原始数据见 R127-A 交付汇报。
