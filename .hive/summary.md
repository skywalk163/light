# T-0199 工作总结（LH-21 未定义名 / LH-09 导入名遮蔽）

## 交付
1. **`src/linter/light_linter.py`**：新增 E016「未定义的名字」(error) + W016「导入名被局部遮蔽」(warning)。
   - `check_undefined_names()` / `check_import_shadow()` 两个纯函数 + `lint_names()`/`lint_names_file()` opt-in 入口；**不进默认 `lint()`**（误报零污染）。
   - 内置名登记 `builtin_names()`：合并 `code_generator*.builtin_map`(319/268) + `exception_name_map`(18) + `BUILTIN_TYPES` + `真/假/空` + `stdlib/builtins.py.__all__`(129) + **`stdlib/lightpub/__index__.py:functions`(2591)** = **2904 个**。
   - 误报防线：`X 的 Y` 属性访问、ASCII 互操作名、`self/己/_`、Python 内建名、变参 `*集合们` 星号剥离、作用域（模块级段落/局部/参数/导入名）逐类判定。
   - 修了一个隐蔽 bug：本模块既可 `import linter.light_linter`（测试/conftest）也可 `import src.linter.light_linter`（`python -m src.linter.cli`）。后一种引法下 `from code_generator import ...` 这类绝对导入静默失败，内置名登记少 212 条、E016 全哑。已在模块顶部把 `src/` 无条件放进 sys.path，两种引法行为一致。
2. **`src/linter/cli.py`**：`--check-names`（+ `--json`）开关，遍历 `.light` 跑 E016/W016，有 error 退出码非 0。
3. **`tools/内置名清单.py`**：输出 `{"内置名":[...],"来源":{...},"统计":{...}}` JSON，支持 `--pretty/--grep/--out`，可直接给 AI 生成光明代码前对拍。
4. **`tests/unit/test_LH21_未定义名.py`**：18 条用例，覆盖全部验收点。`python -m pytest -q tests/unit/test_LH21_未定义名.py` → **18 passed**；既有 `tests/test_linter.py` 25 passed，无回归。

## 关键发现（校正任务书两处错误）
- **任务书示例 `打印 临时目录()` 是真实内置函数**（`stdlib/系统接口.py:326`、`stdlib/环境.py:164`，且登记在 lightpub），按「宁可漏报」红线**不报**。E016 正例改用真伪内置名 `去空白`（真名 `去除空白`）。
- **任务书把 `转布尔` 列为文档错误，但实测它登记在 lightpub `functions` 里，是真实内置函数**。文档「最常用内置函数」表实测仅 3 个伪内置名：`去空白`/`集合创建`/`repr`，文档门禁按此设允许名单。

## 采样（`check_undefined_names`，纯函数）
examples **15/95**、stdlib **2/119**、edu **1/10**、demos **0/6**。
stdlib/协程.light 的 `运行事件循环` 是**真 bug**（该文件注释自证 src 腿不存在 ⇒ NameError）；examples 里 `打开/编码/转成整数/到光明` 等多为示例真错，属正确检出。残余误报仅限未纳入登记的真实内置名（`编译正则表达式` 等）。

## 未动
`cli/light.py`（另一张卡在改）、`docs/AI编程指南.md`（只读门禁守卫）。E016/W016 默认不并入 `lint()`，全仓 check 行为不变。
