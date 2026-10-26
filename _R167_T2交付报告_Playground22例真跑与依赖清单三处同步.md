# R167 · T-2 交付报告 · Playground 22 例真跑 + 依赖清单三处同步

> 基线：`2f359753b`（R166 收口）
> 权威测试机：0.88（FreeBSD 15.1-RELEASE-p1，venv `~/r164venv` = 3.12.13）
> 独立树：`~/r167t2`（`git clone ~/r164clean` → `fetch gitcode` → `merge --ff-only`，HEAD=`2f359753`，建树后 dirty=0）
> 日期：2026-10-26
> 纪律：**未 commit / 未 push / 未 git add**；只改 T-2 点名文件（4 个）

---

## 0. 一句话结论

Playground 22 例从 **22 skipped → 22 passed**，`flask` + `flask-cors` 已固化进 `LOCKED`，三处清单同步完成，
`门禁机自检.py --check --allow-dirty` **全 PASS（exit 0）**，collected **9409 不变**。

⚠️ **但任务书 §0.3 / §3.1-1 有一处前提错误**：缺的**不只是 `flask`**。只装 `flask` 后 22 例**照旧全 skip**，
跳因变成 `No module named 'flask_cors'`。真正要装的是 **`flask` + `flask-cors` 一对**。详见 §2。

---

## 1. 判据对照（§3.2）

| 判据 | 期望 | 实测 | 结论 |
|---|---|---|---|
| `pytest tests/ -k "Playground" -n 0 -p no:randomly -q` | skipped 22 → 0 | **22 passed, 0 skipped, 9387 deselected** | ✅ |
| `python scripts/ensure_venv.py --venv ~/r164venv --check` | flask 项 ✓ | `✓ flask==3.1.3` / `✓ flask-cors==6.0.5` | ✅ |
| `scripts/门禁机自检.py --check --allow-dirty` ③ | LOCKED 全 PASS | 6/6 PASS（含新增两项） | ✅ |
| ④ baseline collected 偏差 | ≤ ±10% | 登记 9409 vs 实际 9409 → **0.0%** | ✅ |

---

## 2. 关键发现：缺的是 `flask` **和** `flask-cors`（任务书前提需订正）

### 2.1 取证过程（三步，每步都有原始输出）

**① 装包前**（`tests/ -k Playground`）：

```
ssssssssssssssssssssss
22 skipped, 9387 deselected, 1 warning in 71.39s
```

**② 只装 `flask`（照任务书 §3.1-1 原话）后 —— 仍然 22 skipped**：

```
$ pip install flask        # → flask-3.1.3 + werkzeug-3.1.9 + blinker-1.9.0
$ pytest tests/integration/test_playground_api.py -q -rs
SKIPPED [22] _pytest/unittest.py:385: Flask 不可用，跳过 Playground API 测试: No module named 'flask_cors'
22 skipped in 0.35s
```

⇒ **任务书 §0.3 表里那行「`No module named 'flask'`」是旧快照的残留**。真实病灶是 `flask_cors`：
`playground/server.py` 的 import 是**两条**——

```python
24: from flask import Flask, request, jsonify, send_from_directory
25: from flask_cors import CORS
```

而 `tests/integration/test_playground_api.py:17-22` 是 `try: from playground.server import app / except ImportError`，
**任一 import 失败都会让整个模块级 `_FLASK_AVAILABLE=False`**，22 例在 `setUpClass` 统一 `raise SkipTest`。
所以「只装 flask」等于没修——这也正好说明**为什么必须把两者成对锁进 LOCKED**（单锁 flask 会造出一个「check 说 ✓、用例仍全 skip」的假固化）。

**③ 补装 `flask-cors` 后**：

```
$ pip install flask-cors   # → flask-cors-6.0.5
$ pytest tests/integration/test_playground_api.py -q
22 passed in 4.80s
```

### 2.2 依赖解析实况（FreeBSD）

| 包 | 来源 | 版本 |
|---|---|---|
| `flask` | 本轮 pip 装进 venv | 3.1.3 |
| `flask-cors` | 本轮 pip 装进 venv | 6.0.5 |
| `werkzeug` / `blinker` | pip 自动带入 venv | 3.1.9 / 1.9.0 |
| `jinja2` / `click` / `itsdangerous` / `markupsafe` | `--system-site-packages` 继承系统包 | 3.1.6 / — / — / 3.0.3 |

⇒ 全是 `py3-none-any` 纯 Python wheel，**FreeBSD 上秒装、无需编译**（与 `cryptography` 要本地编译 2~3 分钟形成对比）。
这也意味着**只锁顶层两个包**就够，不需要把 4 个传递依赖也写进 `LOCKED`（符合该脚本「只锁顶层、其余按现状」的既有纪律）。

---

## 3. 三处同步（§3.1-2/3/4）

| # | 文件 | 改动 |
|---|---|---|
| 1 | `scripts/ensure_venv.py` | `LOCKED` 增 `flask: 3.1.3`、`flask-cors: 6.0.5`；模块 docstring 增 R167-T2 段与「锁版本依据」两条；**放宽证据口径**：由「缺了会红」扩为「缺了会红 **或** 缺了会静默 skip 一整批用例」 |
| 2 | `pyproject.toml` `[dev]` | 增 `flask>=3.1.0`、`flask-cors>=6.0.0`（注释写明「必须与 flask 成对」及 `server.py` 双 import 依据）；dev 组 14 → **16** 项 |
| 3 | `docs/门禁机初始化清单_0.88.md` | §3 LOCKED 表增两行；§5 假红速查增「22 例全 skip、不报红」一行；§6 维护规则写入「静默 skip 也算合格证据」；补 FreeBSD 依赖解析说明 |

**为什么选 `LOCKED` 而非 `WATCH`**（任务书建议 LOCKED，我同意并补了理由）：
`WATCH` 只 WARN 不阻塞，而这 22 例的失败形态是**静默 skip——不产生红**。`-q` 汇总里只表现为「skipped 多 22」，
混在 128 条里根本看不出来；覆盖消失而无人知晓，比红更坏（红会被看见）。故按「缺了会出问题」入 `LOCKED`。

**§7.3 的 baseline 口径订正**（任务书指定 T-2 为核对方）已落在 `tests/ci_baseline_failures.txt`：
写明 `skipped=138` 实为 **128 skipped + 10 xfailed**（junit 把 xfail 也写进 `<skipped type="pytest.xfail">`），
并**逐条核过** 10 处 xfail 的归属（见 §5.3）。

---

## 4. 门禁机自检原始输出

```
$ cd ~/r167t2 && ~/r164venv/bin/python scripts/门禁机自检.py --check --allow-dirty --venv ~/r164venv
  INFO  ①git HEAD：2f359753
  INFO  ①git 工作树（--allow-dirty 跳过干净校验）：未跟踪/改动：M docs/…_0.88.md | M pyproject.toml | M scripts/ensure_venv.py | M tests/ci_baseline_failures.txt
  PASS  ①git 非 shallow 克隆
  PASS  ②LH 独有函数 == LH_ONLY
  PASS  ②LH 不缺真源函数
  PASS  ②LH 公共函数体哈希一致
  PASS  ②LH 内置核心判型.light 判型段落齐
  PASS  ③LOCKED lunardate==0.3.0
  PASS  ③LOCKED requests==2.34.2
  PASS  ③LOCKED cryptography==50.0.2
  PASS  ③LOCKED pytest-timeout==2.4.0
  PASS  ③LOCKED flask==3.1.3
  PASS  ③LOCKED flask-cors==6.0.5
  INFO  ④baseline 登记 collected：9409
  INFO  ④实际门 collected：9409
  PASS  ④baseline collected 偏差 ≤ ±10%
结果：全 PASS
EXIT=0
```

> ②（lightharness 副本）也顺带全 PASS —— 本轮没碰它，说明 `~/lightharness` 仍与 `2f359753b` 对齐。

---

## 5. 有牙复核（不做「改断言换绿」，也不做「假固化」）

### 5.1 `ensure_venv --check` 有牙

用 `python -m venv --without-pip /tmp/t2naked` 造一个空 venv：

```
[ensure_venv] · flask 未安装（期望 3.1.3）
[ensure_venv] · flask-cors 未安装（期望 6.0.5）
[ensure_venv] --check 结论：存在未就位的固化项
```

### 5.2 门禁 ③ 有牙（真正拦截的那一层）

```
$ 门禁机自检.py --check --allow-dirty --venv /tmp/t2naked2
  FAIL  ③LOCKED flask==3.1.3：实得 None（未装或版本漂移）
  FAIL  ③LOCKED flask-cors==6.0.5：实得 None（未装或版本漂移）
结果：7 项 FAIL
```

⇒ 新增两项**确实会把门禁打红**，不是装饰。（`ensure_venv.py` 自身恒 `exit 0` 是既定设计「失败不阻断」，
拦截职责在 `门禁机自检.py`，此处已验到它真的拦。）

### 5.3 「只装 flask」这一中间态本身就是最强的有牙证据

§2.1-② 已实测：`flask` 到位、`flask-cors` 缺失时，**22 例仍全 skip**。
这证明 `flask-cors` 的锁定不是照抄猜测，而是**实测出来的必要条件**。

### 5.4 幂等复核

```
$ ensure_venv.py --venv ~/r164venv        # 非 --check
[ensure_venv] ✓ flask==3.1.3 已就位，跳过
[ensure_venv] ✓ flask-cors==6.0.5 已就位，跳过
[ensure_venv] 完成
```

---

## 6. 无回归佐证

| 检查 | 结果 |
|---|---|
| `pytest tests/ -k "Playground"` | 22 passed / 0 skipped / 9387 deselected（**collected 9409 不变**） |
| `pytest tests/integration/ -n 0` | **82 passed** / 0 failed / 0 skipped（整目录无副作用） |
| `tomllib` 解析 `pyproject.toml` | dev 组 16 项，含 `flask>=3.1.0` / `flask-cors>=6.0.0`；`addopts` 原文未变 |
| 全仓 flask/playground 引用面 | 除 `tests/integration/test_playground_api.py` 外**无**其它测试依赖 flask（`tests/archive/` 被 `--ignore` 排除）⇒ 装包影响面精确等于这 22 例 |

---

## 7. 补齐 §0.3 的 skip 全量归类（128 条，无「其他」）

任务书 §0.3 自陈「只归到 69 条…严格按 skip 计已归类仅 65 条，与 128 差约 63 条，收口时必须补齐」。
我用 R166 F 轮 junit（`~/r166_runF.xml`）做了**全量归类**，并对任务书原表做了三处订正：

| 条数 | 原因 | 性质 | 本轮处置 |
|---|---|---|---|
| **29** | 自举接管：`属纯光明/仅.light 模块`，删 `.py` 后由 `.light` 接管（`_PURE`/`_ONLY_LIGHT` 标记） | 合理·设计如此 | 不清 |
| **22** | `Flask 不可用`（Playground API） | **假绿** | ✅ **T-2 已清（22 passed）** |
| **19** | e2e 平台门 `sys.platform != "linux"`（L3 12 + L4 7） | **假绿** | T-1 |
| 9 | 本机无积木库 `lighting` | 合理 | 不清（任务书原表写 8，**实为 9**） |
| 6 | `junction` 仅 Windows | 合理 | 不清（原表写 4，**实为 6**） |
| 6 | 其它 Windows/POSIX 平台专属（mklink 硬链接、8.3 短名 / `\\?\`、仅 Windows 断言等） | 合理 | 不清（原表**未列**） |
| 5 | ConPTY 仅 Windows（伪控制台/Resize/优雅关闭/错误路径） | 合理 | 不清（原表**未列**） |
| 4 | 外网用例（`LIGHT_TEST_EXTERN=1` 才跑） | 合理 | 不清（原表写 3，**实为 4**） |
| 3 | 未设 `DEEPSEEK_API_KEY` | 合理 | 不清 |
| 2 | 缺 MSVC | 合理 | 不清 |
| 2 | 缺 `libmbedtls` | 合理 | 不清 |
| 2 | Job Object 仅 Windows | 合理 | 不清 |
| **19** | 明细见下表 | 混合 | 见下 |

**19 条明细（逐条，无「其他」）**：

| 条数 | 原因 | 性质 |
|---|---|---|
| 3 | `Bootstrap 编译器不存在: <树>/bootstrap/bootstrap_v3_compiled.py`（含「（可重新生成）」1 条） | 构建产物未生成 ⇒ skip |
| 3 | `星期名称 / 是否工作日 / 星期几 API 不兼容: No module named '时间'` | 生成代码缺 `时间` 模块 |
| 2 | `字典操作函数以关键字开头，parser暂不支持（直接调用）` | 语言级限制（parser） |
| 2 | `解析器未对此输入报错，跳过` | 用例前提自判 |
| 1 | `无法读取 compiler.light: 711 not greater than 1000`（Compiler.light 太短） | 自举产物不完整 |
| 1 | `未生成 ANTLR 词法器 LightLangLexer.py`（antlrparser 旧路径未跑生成） | 旧路径产物未生成 |
| 1 | `反引号转义机制尚未实现（Level 6 规格 §2.3）` | 语言级限制（lexer） |
| 1 | `脚本式测试，需手动运行: tests/test_lsp_protocol_full.py` | 非 pytest 用例 |
| 1 | `测试代码语法不兼容（中文数字在标识符中）` | 用例自身限制 |
| 1 | `类代码生成不完整，属性/构造器/方法未生成` | 产品缺陷（已知） |
| 1 | `lightpub 当前已是仅 .light 形态（无 .py），无「删 .py」反跑对象` | 反跑对象不存在 |
| 1 | `HTML编码/解码 委托 编码解码.light 的能力边界占位（T6C 既有登记）` | 已登记占位 |
| **1** | **`顶层全套真跑门禁尚未武装：未找到基线 <树>/_r159_scratch/e_顶层全套基线.json`** | ⚠️ **门禁未武装，见 §8** |

合计校验：`29+22+19+9+6+6+5+4+3+2+2+2+19 = 128` ✅（`xfail=10` 另计，`junit <skipped>` = 138 ✅）

---

## 8. 遗留观察（**不在 T-2 范围，供收口裁定**）

1. **「顶层全套真跑门禁」是一条未武装的静默 skip**：它要求树内存在 `_r159_scratch/e_顶层全套基线.json`，
   而该文件是 scratch 产物、不在 git 里 ⇒ **换任何一棵干净树都恒 skip**。这与「假绿」同构
   （门写着、从不跑），但它不在本轮 §0.3 的三类假绿里，且武装需一次 20~40min 全量跑。
   建议：单独立号（可作 R168 候选），或至少把 skip 理由改成显式「门禁未武装」并在基线文件里登记。
2. **`Bootstrap 编译器不存在` 3 条 + `compiler.light 太短` 1 条**：都依赖树内构建产物（`bootstrap/*.py`）。
   干净检出必 skip。这属「构建步骤缺失」而非「依赖缺失」，`ensure_venv` 管不到——**不能靠装包解决**。
3. **任务书 §0.3 表的数字偏差**（lighting 8→9、junction 4→6、外网 3→4，且漏列 29+6+5=40 条）
   已在本报告 §7 订正；建议收口报告引用 §7 表，不再引用 §0.3 原表。
4. **§7.2 预期 skipped ≈ 87~88**：T-2 **只实测了这 22 例**（22 skipped → 22 passed），
   故全量门 skipped 应为 128−22 = **106**（**推算，未跑全量门**——§7.2 归主 agent）；
   T-1 若按 §2.1-4 保留 1 例平台相关 skip，则 106−18 = **88**（若 19 例全真跑则为 87）。
   我**未跑全量门**，故 baseline 文件里该数字标注为「预期」，定稿以收口全量门实测为准。

---

## 9. 改动文件（4 个，均在 T-2 文件域内）

```
 M docs/门禁机初始化清单_0.88.md                  | 12 +++++++++++-
 M pyproject.toml                                 |  4 ++++
 M scripts/ensure_venv.py                         | 19 +++++++++++++++++--
 M tests/ci_baseline_failures.txt                 | 15 +++++++++++++++
 4 files changed, 47 insertions(+), 3 deletions(-)
```

> `tests/ci_baseline_failures.txt` 属 §7.3 显式指派给 T-2（原文「核对方为 T-2 的门禁自检 ④」）。
> `tests/test_native_isinstance_typing_modules.py` 的改动属 **T-3**，本线未触碰。
> 0.88 上改动已 scp 到 `~/r167t2`（LF 原样，无 CRLF 归一化需要——4 个文件本机即 LF）。
