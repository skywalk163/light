# CI 修复：_light_import_hook 拦截标准库模块导致循环导入（任务 CIC）

- 任务来源：gitea CI run 161 e2e 的 `my_first.light` 循环导入
  `ImportError: cannot import name 'LightParser' from partially initialized module 'light_parser_v3'`
- 分支：`task-CIC-import-hook`（本地分支隔离；本仓 39k 文件 worktree 检出超时且曾出 prune 事故，故不用 worktree）
- 提交见文末

## 一、根因

`stdlib/_light_import_hook.py` 的 `LightFinder.find_spec` 只要搜索路径里存在 `<名>.light`
就接管该名字的 import，没有排除「与 Python 标准库同名」的模块。

编译任意一个 `.light` 时，`_compile_light` 需要载入编译器：
`light_parser_v3 → parser_core → lexer → dataclasses → inspect`。
当导入链走到 `import inspect` 时，钩子发现 `stdlib/inspect.light` 存在 → 转去编译它；
而 `inspect.light` 又 `import light_parser_v3` —— 此时编译器模块只初始化了一半 → 循环导入。

同族纯影子：`sys.light` / `time.light` / `re.light`（均无 `.py` 兄弟），在标准库名被 import 时
也都会被错误接管。

**为什么本地不报错**：本机 venv 的 `sys.meta_path` 中 `DistutilsMetaFinder`（pkg_resources）
排在钩子之前，恰好先把 `inspect` 等解析到真 CPython 模块，掩盖了缺陷；
CI runner 上钩子更靠前才触发。属「环境依赖型隐藏 bug」——本地无法逐条复现，
靠「钩子置顶 + 从 `sys.modules` 驱逐 `inspect`」强模拟 CI 条件才复现。

## 二、修复方案（选 Plan A：hook 层标准库白名单，最优）

| 维度 | 方案 A（hook 层白名单，采用） | 方案 B（改 code_generator 别名逻辑） |
|---|---|---|
| 改动位置 | 仅 `stdlib/_light_import_hook.py` | 动 `src/code_generator.py` 的 `_PYTHON_LEG_PURE_LIGHT_ALIAS` |
| 思路 | `find_spec` 对「非别名 + 标准库名」直接 `return None` 放行 CPython | 给别名逻辑加「编译期/运行期」分支 |
| 通用性 | 用 `sys.stdlib_module_names` 一网打尽 inspect/sys/time/os/dataclasses/json/re… | 需手工枚举，易漏 |
| 与现有设计 | 契合 `code_generator.py:47-51` 注释（sys/time/inspect 的 .light 只是原生腿最小面，Python 腿必须命中真模块） | 把本应跑真模块的逻辑塞进别名，偏离原设计 |
| re 别名 | 不受影响（`_light_re` 是别名，不触发早退） | 需同步改别名生成 |

**采用方案 A**，理由：定位最准（拦截点即修复点）、零枚举、不碰 codegen 别名、
与项目既有设计注释完全一致。

### 具体改动（`stdlib/_light_import_hook.py`）

1. 模块级新增：
   - `_STDLIB_MODULES = frozenset(getattr(sys, 'stdlib_module_names', ()))`（3.10+ 权威标准库名集合）
   - `_COMPILE_DEPTH: int = 0`（编译嵌套深度）
2. `find_spec` 在算出 `realname` 后、进入搜索循环前加早退：
   - 仅对「`fullname == realname`（非 `_light_` 别名）且 `realname in _STDLIB_MODULES`」生效；
   - `_COMPILE_DEPTH > 0`（编译期）：任何标准库名一律 `return None` → 编译器用真 CPython 标准库
     （连 `json.light`/`base64.light` 这种有 `.py` 兄弟的纯光明实现也只在运行期加载，编译期绝不编译同名影子）；
   - 运行期：仅当该名字在搜索路径里**没有 `.py` 兄弟**（inspect/sys/time/re 这类纯影子）时 `return None` 放行；
     有 `.py` 兄弟的（json/base64，真实文件是大写 `JSON.light`/`JSON.py`，本就被 `_exists_exact` 大小写守卫排除）仍由钩子加载纯光明实现，运行期语义不变。
3. `_compile_light` 进入/退出时 `_COMPILE_DEPTH += 1` / `-= 1`（计数而非布尔，正确处理编译嵌套）。

## 三、不破坏的既有能力（已逐项验证）

- **re 纯光明别名**：`从 re 导入 编译` → `from _light_re import 编译`（`_PYTHON_LEG_PURE_LIGHT_ALIAS` 唯一含 `re`，未动）；
  `import re`（非别名）按运行期规则放行给 CPython re；`import_module('_light_re')` → `stdlib/re.light`。
- **中文模块**（数学/列表工具/文件系统/字符串工具）：非标准库名，钩子照常加载。
- **json/base64**：真实文件 `JSON.light`/`JSON.py` 大写，大小写守卫本就排除，行为不变（→ CPython）。

## 四、本地验证结果

| 验证项 | 结果 |
|---|---|
| CI 条件模拟（钩子首位 + 驱逐 inspect）：修复前 `import inspect` 循环导入；修复后 | `import inspect → .../Lib/inspect.py`，**NO CIRCULAR** |
| `find_spec('inspect')` / `find_spec('sys')` | `None`（不再拦截） |
| `find_spec('_light_re')` / `find_spec('数学')` | 仍返回 spec（别名与中文模块不受影响） |
| `import re` | → CPython `re`（不被 re.light 拦截） |
| `import_module('_light_re')` | → `stdlib/re.light`（别名仍加载纯光明实现） |
| `python -m cli.light run examples/my_first.light` | 正常输出「你好，光明！/及格/1到10的总和：55」，RUN_EXIT=0 |
| 新增回归测试 `tests/unit/test_light_import_hook_stdlib.py` | **5 passed** |
| `tests/unit/test_lightpub_doc_importability.py` | 与原代码一致：1 failed 为**预存缺陷**（HTTP客户端 文档围栏过时标成 text 但实际可导入，归任务 B 的 gen_lightpub_docs.py，与本修复无关） |

## 五、修改文件

- `stdlib/_light_import_hook.py`（修复本体）
- `tests/unit/test_light_import_hook_stdlib.py`（新增回归测试）
- `docs/known_issues.md`（登记 R13D 章节）
- 本交付报告

## 六、红线遵守

- 独立本地分支 `task-CIC-import-hook`，未建 worktree（本仓 39k 文件 worktree 检出超时 + prune 事故风险）。
- 未动 `.gitea/workflows/ci.yml`（归任务 B）。
- 未动 `code_generator.py` 的 `_PYTHON_LEG_PURE_LIGHT_ALIAS`（re 别名逻辑保持 `{re}`）。
- `test_lightpub_doc_importability.py` 的 1 failed 为预存无关缺陷，未改测试文件。

## 七、提交

- 分支 `task-CIC-import-hook`，显式 `git add` 仅上述任务文件（临时脚本 `_taskCIC_*` 已删除）。
- 修复 commit + 文档 commit 见 `git log`。
