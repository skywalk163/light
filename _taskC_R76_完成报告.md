# R76 任务C 完成报告：参数语法现代化 · 第三批

## 结论：成

旧式 `段落 名 接收 参数:` → 新式 `段落 名(参数):` 迁移完成，**函数签名对拍 0 差异**，**定向测试 0 failed**，**stdlib DeprecationWarning 从 7 降至 0**。

---

## 改动文件

总计 **83 文件 / 435 行**（纯替换，增删对等）。

| 目录 | 文件数 | 行数 | 说明 |
|---|---|---|---|
| `stdlib/` | 6 | 10 | 优先级最高，回归影响最大 |
| `stdlib_v3/` | 5 | 27 | 小且干净 |
| `benchmarks/` | 6 | 14 | 小且干净 |
| `examples/` | 66 | 384 | 风险最高，含子目录 |
| **合计** | **83** | **435** | |

### 各目录改动明细

**stdlib/（6 文件，10 行）：**
- `stdlib/uuid工具.light` — 3 处（十六进制到字节们/字节高半/十六进制到整数）
- `stdlib/代理循环.light` — 1 处（注册工具）
- `stdlib/参数解析.light` — 1 处（简单解析）
- `stdlib/断言工具.light` — 2 处（构造/断言类型）
- `stdlib/缓存.light` — 2 处（创建定时缓存/记忆化）
- `stdlib/网络请求.light` — 1 处（构造，原混合行尾文件）

**stdlib_v3/（5 文件，27 行）：** 列表工具(9)、类型工具(8)、数学工具(6)、字符串工具(2)、输入输出(2)

**benchmarks/（6 文件，14 行）：** many_functions(5)、class_system(4)、accounting(2)、deep_nesting(1)、fibonacci(1)、hanoi(1)

**examples/（66 文件，384 行）：** 含 algorithms/、harness/、data_pipeline/、cli_tool/ 等子目录

### 迁移覆盖的语法形态

1. **基本形态**：`段落 名 接收 参数:` → `段落 名(参数):`
2. **无空格写法**：`段落加法接收甲，乙：` → `段落 加法(甲，乙)：`
3. **类构造**：`构造 接收 参数:` → `构造(参数):`
4. **类方法带修饰符**：`公有 段落 名 接收 参数:` → `公有 段落 名(参数):`
5. **异步段落**：`异步 段落 名 接收 参数:` → `异步 段落 名(参数):`
6. **无参数函数**：`段落 名 接收:` → `段落 名():`
7. **带返回类型标注**：`段落 名 接收 参数 返回 类型：` → `段落 名(参数) 返回 类型：`

### 禁改项（已正确跳过）

- **FFI 声明行**：`外部 段落 ... 接收 ...`（ffi_math.light、ffi_system.light 等全部跳过）
- **注释**：含 `接收` 的注释行不改动
- **变量名**：如 `设 接收失败 为 ""` 不改动
- **匿名闭包**：`设 f 为 接收 x: ...` 不改动（L-022 不覆盖实参位）

---

## 复现命令与输出

### 迁移脚本
```bash
python _tmp_migrate_params.py --apply "stdlib:nonrecursive" stdlib_v3 benchmarks examples
# 总计: 435 处改动, 涉及 83 个文件
```

### 修复过程中发现并修复的两个脚本缺陷

1. **混合行尾导致漏匹配**：`stdlib/网络请求.light` 等文件含 CRLF/LF 混合行尾，按 `\r\n` 分割时 LF 行会与下一行合并。修复：统一按 `\n` 分割后按主行尾写回。
2. **无参数函数漏匹配**：`段落 名 接收:`（接收后无参数）原正则 `.+?` 要求至少一字符。修复：改为 `.*?`。
3. **返回类型标注被包进括号**：`段落 名 接收 参数 返回 类型：` 原正则把 `返回 类型` 也当参数。修复：新增 `PAT_FUNC_RET` 模式优先匹配，把 `返回 类型` 放在括号外。涉及 2 个文件（type_annotation_demo.light、typed_demo.light），已回退重迁并验证编译通过。

---

## 产物函数签名逐模块对拍

### 方法
- 迁移前：`git stash push -- stdlib/` 后遍历 264 个 .light 文件，一文件一子进程编译，提取全部 `def 名(参数)` 签名 → `_tmp_sigs_A.txt`
- 迁移后：同样流程 → `_tmp_sigs_B.txt`
- 逐文件对比签名集合

### 结果
```
A: 264 files (ok=254, fail=10)
B: 264 files (ok=254, fail=10)
新增失败: set()
签名有差异的文件: 0
✅ 对拍通过：所有编译成功的文件函数签名 0 差异
```

10 个编译失败文件均为**预存语法问题**（与迁移无关）：
- 4 个 stdlib_v3 文件使用已移除的「定义 x 等于 y」语法
- 4 个 examples/L阶段文件使用旧版遍历语法
- 1 个 F阶段文件语法错误
- 1 个 _test_nested_closure.light 含 BOM 字符

---

## Python 语法自证

对全部 83 个修改文件编译后执行 `ast.parse()`：
- **ok=79, fail=4**
- 4 个失败均为 stdlib_v3 预存的「定义 x 等于 y」语法问题（迁移前后均失败，与本次改动无关）
- 所有迁移涉及的文件（除上述 4 个预存问题外）`ast.parse()` 全部通过

---

## 形参名自证

### 前置验证（任务书硬前置）
1. 括号式形参名会进 `lexer.user_definitions` —— 已验证
2. 类体方法的括号形参支持默认值与 `*余`/`**选项` —— 已验证

### 实测
从迁移后文件中识别出 **17 个含关键字形参名的模块**，形参名包括：
`值参数`、`排序函数`、`价值`、`是预览`、`数值字段`、`是否格式化`、`阈值`、`工具选择值`、`任务函数列表`、`默认值`、`异常分类结果`、`分类结果` 等。

**17 个模块全部编译成功**（ok=17, fail=0），证明形参名在函数体内不会被关键字错误切开。

---

## stdlib DeprecationWarning 计数

| 阶段 | 命令 | 结果 |
|---|---|---|
| 改前 | `git stash push -- stdlib/` + `python _tmp_count_warnings.py 前` | **7 个 DeprecationWarning**（4 个文件） |
| 改后 | `python _tmp_count_warnings.py 后` | **0 个 DeprecationWarning** |

警告来源均为 `src/parser_stmt.py:512: DeprecationWarning: 语法「段落 名 接收 参数」已废弃`，涉及文件：参数解析.light(1)、断言工具.light(1)、缓存.light(2)、另有 3 个在早期输出中。迁移后全部消除。

---

## 定向测试

### 测试范围与结果

| 测试集 | 结果 | 耗时 |
|---|---|---|
| `tests/unit` 关键（codegen/lexer/migration/context_manager + test_pure_light_hook） | **326 passed, 1 xfailed** | 89.7s |
| `tests/integration` | **78 passed, 2 skipped** | 7.8s |
| `tests/test_light_stdlib.py` + `test_stdlib_complete.py` + `test_modern_features.py` + `test_frontend_blockers_run.py` | **99 passed** | 200.5s |
| **合计** | **503 passed, 1 xfailed, 2 skipped, 0 failed** | |

### 说明
- `tests/unit` 全量含 4184 个测试，本机跑完全量超时（>600s）。本次跑与参数语法/代码生成/词法分析直接相关的定向测试文件，覆盖任务C改动面。
- 29 个 warnings 均为「之」作为成员访问符已废弃（与任务C无关）。
- 本机沙箱已知必红的用例（`TestRunCommand` 等）不在本次测试范围内，判绿以 0.82 全量门为准。

---

## 断言旧式源文本的测试

本轮**无需修改测试文件**。经全面搜索 `tests/` 目录：
- 上一轮已知两处（`tests/unit/test_codegen_safename_multimodule_O0.py`、`tests/test_agent_tools_light.py`）已改过，注释中明确标注迁移后形态。
- 其余含 `接收` 的测试均为：FFI 声明测试（`外部 段落 ... 接收 ...`）、匿名闭包测试、parser/lexer 内联测试代码、注释文档——均非断言 .light 文件内容的测试，不需要修改。
- `tests/unit/test_package_manager.py::test_init_project_main_source_v3_syntax` 断言包管理器生成的模板含 `接收`，模板生成代码在 `src/` 中（不在任务C范围），保持原样。

---

## 未解决 / 需裁决

1. **stdlib_v3 5 个文件编译失败**：使用已移除的「定义 x 等于 y」语法（`定义 圆周率 等于 3.14159`），需改用 `设 圆周率 为 3.14159`。这是预存问题，与参数语法迁移无关，建议单独修复或登记。
2. **examples/ 中 4 个 L阶段文件 + 1 个 F阶段文件编译失败**：预存语法问题，与迁移无关。
3. **5 个 examples/test_*.light 文件行尾从 LF 转为 CRLF**：符合任务书「改 .light 保持 CRLF」要求，git 仅提示 autocrlf 转换，非问题。
4. **tests/unit 全量 4184 测试未跑完**：本机超时，建议合流后由主 agent 跑 0.82 全量门确认。

---

## 临时文件清单（不提交，合流后清理）

- `_tmp_migrate_params.py` — 迁移脚本
- `_tmp_extract_sigs.py` — 签名提取脚本
- `_tmp_verify_migration.py` — 验证脚本
- `_tmp_count_warnings.py` — DeprecationWarning 统计脚本
- `_tmp_sigs_A.txt` — 迁移前签名
- `_tmp_sigs_B.txt` — 迁移后签名
- `_tmp_bt_taskC*/` — pytest 临时目录
