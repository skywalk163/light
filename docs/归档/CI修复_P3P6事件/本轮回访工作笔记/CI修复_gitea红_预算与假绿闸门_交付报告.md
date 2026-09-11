# CI 修复交付报告：gitea 40 红定位 + 预算放宽 50min + pre-push 假绿闸门解锁

日期：2026-09-08
分支：`main`（远端 gitea 已更新 `2e9b6e3f → abc450dd`）

---

## 一、根因（gitea 40 failed 的主因不是测试，是「远端 main 少了 20 个提交」）

gitea 日志里的循环导入栈，行号对上了 **旧版** `_light_import_hook.py`：

```
stdlib/_light_import_hook.py:166: in exec_module
    code = _compile_light(self.light_path, self.stdlib_dir)
ImportError: cannot import name 'LightParser' from partially initialized module 'light_parser_v3'
```

- 远端 `main`（= `2e9b6e3f`，gitea/github 同指）里的钩子是 **249 行**，`_compile_light` 正在 **第 166 行**；
- 本地 `task-CIperf` 分支里的钩子是 **288 行**，已带 `_COMPILE_DEPTH` + `_STDLIB_MODULES` 双重保护。

即：**修复早已写好，只是从未合到 main**。CI 跑的是旧代码。

`main` 与 `task-CIperf` 在 `0f9f6dbe` 处分叉，形成并行重复历史（main 独有 12 个提交，task-CIperf 独有 20 个），
两边 `git diff` 实际只差 **13 个文件 / +750 −19**——task-CIperf 是超集，且含三处关键修复：

| 提交 | 修复内容 | 对应日志症状 |
| --- | --- | --- |
| `49f0d845` (CIC) | 导入钩子不再拦截标准库同名 `.light` 影子 | 循环导入（约 30 条 e2e） |
| `5f575700` | e2e 科学计算库依赖安装（devpi 缺失回退公共 PyPI） | `No module named 'pandas'/'sympy'/'matplotlib'/'sklearn'` |
| `fa14178a` (CIB) | e2e 环境欠账降级为 skip | e2e 环境类失败 |

## 二、做了什么

1. **合并 `task-CIperf` → `main`**（`git merge`，ort 策略，**零冲突**，13 文件）
   - 合并后校验：钩子已含 `_COMPILE_DEPTH` / `_STDLIB_MODULES`；`ci.yml` 已含科学计算库安装（L146-147）。
2. **gitea 时间预算放宽到 50 分钟**（用户裁决）
   - `ci.yml`：`BUDGET=1400 → 3000`（push main，50min）；PR `600 → 1800`（30min）
   - 同步更新三处过期口径注释（L39 / L77 / L364），避免注释与真值打架。
3. **恢复工作树里 314 个被删的 `tests/` 文件**（`git checkout -- tests/`）
   - 合并前 `tests/unit` 只剩 1 个文件（应为 95）。这类状态一旦 `git add .` 就会把 314 个测试删进提交，
     全程坚持**显式列文件提交**。
4. **解 pre-push「假绿断言」闸门**（推送被它拦死，不是认证问题）
   - 首次扫描命中 **271** 条新增，其中 **265 条来自我自己建的临时 venv `.venv_ciperf/`**——
     `.gitignore` 里写的是 `.venv/`（带斜杠），匹配不到 `.venv_ciperf`。
   - 把 venv 移出仓库（`../_venv_ciperf`）后，降到 **6 条真问题**，逐条改成有信号断言（见下）。
5. **提交并推送 gitea**：`2e9b6e3f..abc450dd main -> main` ✅

### 6 条假绿断言的改法（不断 `is not None` / `len > 0`）

| 位置 | 原断言 | 改为 |
| --- | --- | --- |
| `tests/test_entry_function.py:46` | `assert module is not None` | 断 `module.statements` 非空 |
| `tests/test_error_messages.py:682` | `assert len(result) > 0` | 断候选集 `== {"打印","打字","打包"}` |
| `tests/test_error_messages.py:822` | `assert len(result) > 0` | 断输出含中文字符（贴合「输出应含中文」语义） |
| `tests/unit/test_light_import_hook_stdlib.py:43` | `assert spec is not None` | 断 loader 类型是 `LightLoader` |
| `tests/unit/test_light_import_hook_stdlib.py:44` | `assert spec.loader is not None` | 断 `loader.light_path` 指向 `re.light` |
| `tests/unit/test_原生腿_R11B_中文工具.py:696` | `assert len(m) >= 2500` | 断常用字 `{中,华,好}` 在拼音表中 |

踩坑两处（写进注释了，避免下次重犯）：
- `Module` AST 节点的字段是 **`statements`，没有 `body`**——按 `body` 写的第一版把 8 条测试全打红。
- `importlib.util.spec_from_loader` **不填 `origin`**（实测为 `None`），断 `spec.origin` 必失败；
  有信号的是 `spec.loader.light_path`。

## 三、验证证据

| 项 | 命令 | 结果 |
| --- | --- | --- |
| YAML 合法 | `yaml.safe_load(ci.yml)` | 合法 ✅ |
| 预算落地 | `grep BUDGET` | `3000` / PR `1800` ✅ |
| xdist 未被回退 | `grep pytest-xdist` | 无 `\|\| true`，走公共 PyPI ✅ |
| 钩子修复在位 | `grep _COMPILE_DEPTH` | 已在 main ✅ |
| 断言闸门 | `tools/ci/assert_quality.py --root .` | 「无新增违规 / 通过」✅ |
| 改动测试复跑 | `pytest` 3 个文件 | **97 passed** ✅ |
| gitea 推送 | `git push gitea main` | `2e9b6e3f..abc450dd` ✅ |

## 四、现在 / 剩余（诚实披露）

**已完成**：gitea 侧的 40 红根因已消除并推送；预算放宽到 50min；pre-push 闸门解锁。

**未完成 —— GitHub 推送（环境阻断，非代码问题）**
`git push github main` 两次均失败于沙箱代理：
`CONNECT tunnel failed, response 502` / `Empty reply from server`（绕过代理直连同样失败）。
`git ls-remote github` 读操作正常，说明是代理不允许推送这个量级的请求。
**需在正常网络下补一条**：`git push github main`（本地 `main` 已是 `abc450dd`）。

**未完成 —— GitHub 日志里另外 10 红（属既有文档/原生腿欠账，与本次合并无关）**
- 文档门禁 2 条：`test_不许新增ROT`（8 个块：7 个在 `docs/AI编程指南.md` + 1 个在 `docs/syntax.md`）、
  `test_噪声类总数不许涨`（18→20）。本地已复现，属真文档腐烂：示例用了不支持的语法
  （`?` 三元——词法器明说「`?` 永不支持」、`类 狗(动物)` 括号继承、`段落 接收` 旧式形参）。
- 原生腿 6 条：`NameError: 列表/编码解码`、`TypeError: 'int' object is not callable`、
  `AttributeError: _region_code_map`。
- 网络用例 1 条：`test_O0_HTTPS_需网络环境`（CI 无外网，实际=0 期望=200）。

> ⚠️ 注意：本地扫描会显示 **36** 个新增 ROT，比 CI 的 8 个多 28 个——多出来的来自**未跟踪**的
> `docs/dataset_deepseek_r1_100_examples.md` / `docs/dataset_test_report.md`（仅存在于本地工作树）。
> 它们**绝不能顺手提交**，否则 CI 会立刻多出 28 红。

## 五、建议下一步

1. 正常网络下 `git push github main`（补 GitHub）。
2. 单独开单修 `docs/AI编程指南.md` 的 7 个 ROT 块（按门禁口径：要么改成能编过的真语法，
   要么说明为何该进基线；伪代码类应改 ` ```text ` 围栏）。
3. 单独开单修原生腿 6 红（stdlib `字符串工具.light` 的 `列表`/`编码解码` 未定义等）。
4. 网络依赖用例加 skip 守卫，避免 CI 无外网时假红。
