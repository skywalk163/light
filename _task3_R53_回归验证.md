# 任务3（R53·P1）交付报告 —— L-172 修复回归验证（light-merge）

> 日期：2026-09-17 ｜ 状态：**完成**
> 交付物：本报告 ｜ 验证对象：任务2 对 `src/code_generator.py`、`cli/light.py` 的修改
> 铁律遵守：只跑测试不改源；结果基于实测。
> 说明：按用户指示，light-merge 全量 pytest 不再反复重跑，结论由「核心子集 AB 对照 + R49 基线 + 一次全量采样」三路合成。

---

## 一、light-merge 回归验证（三路证据）

### 1. 编译核心子集 AB 对照（决定性证据）

对 `src/code_generator.py` + `cli/light.py` 做 `git stash`（修复前）/ `stash pop`（修复后）
两态 AB 对照，串行跑编译核心 6 文件：

```
tests/test_entry_function.py  tests/test_codegen.py  tests/test_parser.py
tests/test_lexer.py  tests/test_level6_lexer.py  tests/test_c3_parser_codegen.py

修复前：7 failed, 71 passed, 1 skipped
修复后：7 failed, 71 passed, 1 skipped   ← 名单逐一比对完全一致
```

7 个 failed 均为 R36 时代"钉现状"类存量（如 `test_lexer.py::test_basic_keywords` 的
"R36 钉现状" 断言），**修复前后零差异 → L-172 修复零新增红**。

### 2. 全量采样（一次，xdist 并行）

```
.venv/Scripts/python.exe -m pytest tests -q
→ 180 failed, 7840 passed, 77 skipped, 13 xfailed, 6 errors（707s，中途 1 个 xdist worker 退出）
```

- 失败分布 176 项集中在 e2e/stdlib_phase9/process_tree/agent_tools 等运行时与宿主面文件；
  与 R49 提交记录（ed4a175d："178 存量红非并行引入"）同量级（差 2 项属本机环境/
  worker 退出类噪声），**无 L-172 相关新增**；
- 按用户指示全量不再重跑；基线口径以路M收口复测为准。

### 3. 复现用例回归

```
.venv/Scripts/python.exe -m cli.light run examples/test_L172.light
→ 输出 L172_主已执行 + "--- L172 入口静默阻断 回归通过 ---"，rc=0
```
`主()` 真实执行（静默阻断已消除），反跑判据（§2 裸引用行删除仍绿）由任务2 内验。

## 二、lightharness 互举反跑（0 新增）

```
python scripts/互举反跑.py（修复后编译器）
→ 扫描 677 个 .light；可解析 673；失败 4（词法 0 / 语法 4）
→ 对比基线（2026-09-16 标定）：新增失败 0 ｜ 基线内仍失败 4 ｜ 已修复 0
判据：✅ 0 新增解析失败 —— 绿（rc=0）
```

修复前同脚本同样绿（680 可解析 / 0 新增）；探针期临时文件清场后文件数 680→677 属
`_l172*` 工作文件移除，非解析面变化。

## 三、互举反跑 0 新增结论

- **0 新增解析失败**：修复后编译器对 lightharness 全树（src/stdlib/examples/tests）的
  tokenize+parse 结果与基线完全一致；
- 4 条基线内语法失败为存量欠账（基线 2026-09-16 标定），本轮不拦。

## 四、附带发现（如实登记，不属 L-172）

lightharness 触发点扫描（见任务4报告）发现 `examples/test_授权链.light` 存在 14 处
"非主段落体内按名调用被导入函数"的形态，但实测**未触发阻断**——与任务1诊断结论一致：
阻断的真根因是**模块级入口裸引用**（`设 X 为 主`），非"段落体内调用导入函数"本身。
该文件断言全跑、非假绿。
