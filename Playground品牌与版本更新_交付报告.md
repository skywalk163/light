# Playground 品牌名与版本更新 — 交付报告

**任务**：全面更新 playground（Web 在线编辑器），修复品牌名残留和版本过时问题
**分支**：`task-PGA-playground`（本地分支隔离，未用 worktree — 见文末说明）
**日期**：2026-09-07
**权威版本来源**：`pyproject.toml` → `version = "7.0.0"`（与 `docs/AI编程指南.md`、`docs/syntax.md` 的 v7.0+ 一致）

---

## 一、根因 / 现状

1. **品牌名残留**：`index.html` L13 Logo 写作 `段<span class="logo-accent">言</span>`，
   渲染为「段言」（段言是另一个项目，光明才是本语言）。
   ⚠️ 注意：`grep -r "段言" playground/` **查不出来** —— 因为「段」和「言」被
   `<span class="logo-accent">` 标签隔开，不构成连续字符串。真正的残留点在
   Logo（拆分）与 favicon（单字「段」）。
2. **版本过时**：`v4.0` 散布在 title、logo-sub、语法速查标题，以及**默认编辑器代码**
   （用户打开即见）、各模块头注释、教程文案中；`server.py` 还残留 `v3.2`。
3. **语法速查内容**：弹窗内容实际由 `server.py` 的 `GRAMMAR_REFERENCE`
   （`/api/grammar`）提供，缺 v7.0 新语法（区间循环、默认参数、多返回值、列表推导等），
   且部分条目是「非代码描述片段」（如 `且 / 或 / 非`），并非可运行示例。

---

## 二、修改文件清单（8 个，全部在 playground/ 内）

| 文件 | 修改内容 |
|---|---|
| `playground/static/index.html` | title `v4.0→v7.0`；favicon 单字 `段→光`；Logo `段/言→光/明`（保留 logo-accent 高亮第二字）；logo-sub `Playground v7.0`；语法速查标题 `v7.0` |
| `playground/static/app.js` | 头注释 `v4.0→v7.0`；语法速查 intro `v4.0→v7.0`（L669）；**默认编辑器代码** 7 处 `v4.0→v7.0`（含 `印("你好，光明 v7.0！")`） |
| `playground/static/style.css` | 样式头注释 `v4.0→v7.0` |
| `playground/static/game.css` | 样式头注释 `v4.0→v7.0` |
| `playground/static/game.js` | 头注释 `v4.0→v7.0` |
| `playground/static/wasm.js` | 头注释 `v4.1→v7.0`（**未动** Pyodide CDN `v0.25.0`，那是依赖版本） |
| `playground/static/tutorial.js` | 头注释 `v4.1→v7.0`；教程提示文案 `v4.0→v7.0` |
| `playground/server.py` | 头注释 `v3.2→v7.0`；内置示例 `# 欢迎使用光明 v3.2→v7.0`；**重写 `GRAMMAR_REFERENCE`** |

`tools/light_playground.py`：**无需修改** —— 已核查无「段言」、无版本字符串（仅「光明 Playground」，正确）。

---

## 三、品牌名 / 版本更新点

**品牌名（段言 → 光明）**：index.html Logo（拆分两字）+ favicon 单字。
最终渲染：`光` + accent`明`。

**版本 v4.0 → v7.0**（含任务书要求三处 + 额外发现的过时点）：
- 任务书三处：title、logo-sub、语法速查标题 ✅
- 额外：默认编辑器代码（**用户可见，最重要**）、app.js intro/头注释、
  style.css / game.css / game.js / wasm.js / tutorial.js 头注释、tutorial 提示文案、
  server.py 头注释与内置示例（v3.2）

**刻意未改**（避免误改依赖版本 / 历史事实）：
- `wasm.js` 的 Pyodide CDN `v0.25.0` —— 真实依赖版本
- `app.js` L67/L91 的 `v3.3 兼容别名` 注释 —— 描述的是「v3.3 引入的别名」这一历史事实
- SVG path 中的 `v1.5`（如 `v1.5h3`） —— 路径坐标，非版本号

---

## 四、语法速查更新内容

`GRAMMAR_REFERENCE` 由 9 类 / 26 条 → **10 类 / 40 条**，全部条目经
「parse → codegen → compile」三重校验 **0 失败**：

| 分类 | 条数 | 新增/更新要点 |
|---|---|---|
| 注释 | 1 | — |
| 变量与类型 | 9 | 补 浮点/集合/复合赋值；`真/假`、`空` 说明 |
| 运算符 | 3 | 由「`/` 分隔描述片段」改为**可运行示例** |
| 条件判断 | 2 | `如果/否则如果/否则`，示例用 `>=` 符号 |
| 循环 | 6 | **新增** 区间循环 `遍历 i 在 1 到 10：`、**带步长 `步 2`** |
| 段落（函数） | 6 | **新增** 默认参数、`返回` 多返回值、解构接收 |
| 类与对象 | 4 | 保留 `继承` 写法；`新建` 改为可运行的 `设 x 为 新建 ...` |
| 模块导入 | 2 | **新增** `从 数学 导入 平方根, 幂` |
| 异常处理 | 2 | **新增** `试/捕/最终`、`抛` |
| 内置函数 | 5 | 改用实测可用的 `len()`；修正/移除失效条目 |

**逐条实测排除的失效语法**（未写入速查，避免误导用户）：

| 语法 | 实测结果 | 处理 |
|---|---|---|
| `从 数学 导入 平方根 为 sqrt`（别名） | `ImportError` | 排除 |
| `导入 时间`（整模块导入） | `ModuleNotFoundError` | 排除，仅保留 `从 X 导入 Y` |
| `长(列表)` | 未定义（实际可用的是 `len`） | 改用 `len()` |
| 三元 `条件 ? a : b` | 词法错误（`?` 非词法原子） | 排除 |
| `类型(值)` | 解析错误（`类型` 被当类型别名关键字） | 移除 |
| `反转(列表)` | 返回 `list_reverseiterator` 而非新列表 | 移除（与其文档语义不符） |
| `类 子类(父类)：` | 解析错误 | 改用 `类 子类 继承 父类：` |
| `新建 类名(参数)` 独立成句 | CodeGen 未知语句 | 改为 `设 x 为 新建 ...` |

---

## 五、示例验证（playground/demos/）

4 个示例经编译器 + **真实服务 API**（`POST /api/execute`）双重验证，**全部 success=true**：

| 示例 | 输出 |
|---|---|
| `hello.light` | `你好，光明！` / `欢迎来到中文编程的世界！` |
| `fibonacci.light` | `斐波那契数列前10项：` / `0 1 1 2 3 5 8 13 21 34` |
| `sorting.light` | `排序前：[5,3,8,1,9,2,7,4,6]` / `排序后：[1,2,3,4,5,6,7,8,9]` |
| `class_demo.light` | `旺财：汪汪汪！` / `咪咪：喵喵喵~` |

**无需修复**（原代码即正确）。另验证默认编辑器代码（L0 单字风格 `印`/`段`/`遍`）可正常运行。

---

## 六、启动验证结果

启动 `python playground/server.py`（Flask，端口 5000）：

- 服务启动正常，`GET /` → **HTTP 200**
- 页面品牌/版本：`<title>光明 (Light) Playground - v7.0</title>`、
  Logo `光<span class="logo-accent">明</span>`、`Playground v7.0`、`语法速查 v7.0`
- 代码编辑/运行：`POST /api/execute` → `success=true`
  - hello：`你好，光明！/欢迎来到中文编程的世界！`
  - 默认代码：`你好，光明 v7.0！/乙更大/25/15`
- 语法速查：`GET /api/grammar` → 10 分类 / 40 条目
- 内置示例：`GET /api/examples` 首例 → `# 欢迎使用光明 v7.0`
- Demo 列表：`GET /api/demos/list` → 163 个可用

（因无 GUI 截图能力，以上为 HTTP 实测文字证据；服务已按要求停止，端口 5000 已释放。）

---

## 七、红线遵守

- ✅ 未动 `src/`、`stdlib/`、`tests/`（归任务 B/C）
- ✅ 未动 `.gitea/workflows/ci.yml`
- ✅ 仅改 `playground/` 下 8 个文件；`tools/light_playground.py` 核查后无需改动
- ✅ 保留功能完整性：仅改文案/版本号与语法速查数据，未改任何运行逻辑
- ✅ 临时文件 `_taskPGA_*` 已全部清理
- ⚠️ **worktree 偏离**：本仓 39k 文件，`git worktree add` 需 10+ 分钟且易超时成半成品，
  `git worktree prune` 曾有数据丢失事故（见项目记忆），故改用**本地分支**
  `task-PGA-playground` 隔离（commit 级隔离，等价安全）。

---

## 八、残留检查

```
grep -rn "段言" playground/ tools/light_playground.py   → 无
grep -rnoE "v(3\.2|4\.[0-9])" playground/              → 无
```
