# 第 61 轮 任务2 交付报告 —— 存量红 `test_paragraph_call` 处置（测试现代化，转绿）

> 日期：2026-09-18 ｜ 修改区域：仅 `tests/`（Python）｜ 红线条数：1 条红（任务书 §2）
> 目标红（基线 201545）：`tests/_test_null_safety.py::TestBackwardsCompatibility::test_paragraph_call`

## 一、改动文件清单（行号级）

| 文件 | 位置 | 改动 |
|---|---|---|
| `light-merge/tests/_test_null_safety.py` | `TestBackwardsCompatibility.test_paragraph_call`（改后约 237–247 行） | 测试源码由旧式段落定义语法改写为现代语法；新增 2 行注释说明改写原因 |

改写内容：

```diff
     def test_paragraph_call(self):
+        # 现代语法：段落 相加 接收 甲，乙：（旧式「段落相加(甲, 乙)：」已废弃，
+        # 旧式语法会 ParseError，与 null-safety 无关）
         src = (
-            '段落相加(甲, 乙)：\n'
-            '    返回甲加乙。\n'
-            '打印相加(1, 2)。\n'
+            '段落 相加 接收 甲，乙：\n'
+            '    返回 甲 加 乙。\n'
            '打印 相加(1, 2)。\n'
         )
         c = compile_source(src)
         # 允许有语法/类型错误，测试意图保持：允许有语法/类型错误，但不能有「可空」之外的崩溃
         self.assertIsNotNone(c._inferencer)
```

未改动编译器、解析器、stdlib 或任何 `src/`、`stdlib/` 文件。

## 二、根因与处置（与 R60 归因一致）

- 旧式语法 `段落相加(甲, 乙)：`（半角冒号 + 括号形参）解析 ParseError → `compile_source` 抛错 → `c._inferencer` 拿不到 → 红。
- 按任务书指定改写为现代语法 `段落 相加 接收 甲，乙：`，保持测试意图（null-safety 推断器不因非可空问题崩溃）。

## 三、验证结果

| 验证项 | 结果 |
|---|---|
| 本机定向（改前） | 1 failed（ParseError：行1列11 无法识别「：」+ 行2 缩进错误），与任务书归因一致 |
| 本机定向（改后） | **1 passed**（rc=0） |
| 本机整文件 | **14 passed**（rc=0，无新增红） |
| 0.82 定向（副本 `/tmp/r44-20260918-202728`，`/usr/local/bin/python3.12` + xdist + timeout） | **1 passed**（rc=0） |
| 0.82 整文件 | **14 passed**（rc=0，无新增红） |
| pytest 收集确认 | `_test` 前缀文件被正常收集，`test_paragraph_call` 在 collect-only 列表中（14 collected） |
| 语义核验 | 现代语法下编译 0 错误（`c.errors == []`）、`c._inferencer` 非 None；测试意图（推断器不因非可空问题崩溃）保持，断言未弱化、非空跑 |

## 四、如实声明（偏差 / 注意事项）

1. **DeprecationWarning（非红）**：现代语法 `段落 名 接收 参数` 触发解析器弃用警告
   （`src/parser_stmt.py:500`，建议改用 `函数 名(参数)` 或 `段落 名(参数)`）。任务书 §2 明确指定该写法，故照用；
   未来若「接收」关键字移除，此用例需再现代化，届时建议直接用 `段落 相加(甲, 乙)：` 括号形参现代形式。
2. **0.82 副本已同步该文件**：已将改后 `_test_null_safety.py` SFTP 上传覆盖至远端副本
   `/tmp/r44-20260918-202728/light-merge/tests/_test_null_safety.py`（9956 字节）。
   路M 全量若**重新 sync 打包**则不受影响；若**复用该副本**跑全量，此文件已是新版（与本地一致，无偏差）。
3. 本机 pytest 需 `-o addopts=""` 覆盖 pyproject 的 xdist/timeout addopts（本机无该插件，属环境差异，非代码问题）。
4. 未跑全量（护栏 2）；未 commit/push（护栏 1）。

## 五、判据核对

- ✅ 目标红本机转绿（1 passed）
- ✅ 0.82 定向（副本）复跑同绿（1 passed）
- ✅ 整文件 14 passed，无新增红
- ✅ 测试意图保持，断言未弱化
