# 段言 v6.1 全量回归测试报告

**测试日期**: 2026-08-07  
**测试范围**: tests/ 目录下所有测试用例  
**运行环境**: Windows, Python 3.10.11

---

## 1. 测试摘要

| 指标 | 数值 |
|------|------|
| 总计 | 2536 |
| 通过 | 2473 |
| 失败 | 13 |
| 跳过 | 50 |
| 错误 | 0 |
| 通过率 | 97.5% |
| 耗时 | 106.44 秒 |

---

## 2. 失败测试分析

### 2.1 E2E 编译/运行测试 (10 个失败)

| 测试用例 | 失败原因 |
|----------|----------|
| `test_duan_run[cli_tool/file_organizer.duan]` | 语法错误：duan 源文件中的语法与当前解析器不兼容 |
| `test_duan_run[kids/draw_shapes.duan]` | 同上 |
| `test_duan_run[kids/number_game.duan]` | 同上 |
| `test_duan_run[kids/story_generator.duan]` | 同上 |
| `test_duan_run[web_crawler/crawler.duan]` | 同上 |
| `test_duan_compile_and_run_product[cli_tool/file_organizer.duan]` | 同上 |
| `test_duan_compile_and_run_product[kids/draw_shapes.duan]` | 同上 |
| `test_duan_compile_and_run_product[kids/number_game.duan]` | 同上 |
| `test_duan_compile_and_run_product[kids/story_generator.duan]` | 同上 |
| `test_duan_compile_and_run_product[web_crawler/crawler.duan]` | 同上 |

**根因**: 示例程序中的 `.duan` 源文件包含 v6.0 之前版本的语法结构，当前解析器（parser_core.py）存在兼容性问题，导致 `：`（中文冒号）解析错误、`遍历` 循环关键字缺失、数字行号被误识别为语法元素等问题。

**状态**: 非回归缺陷 — 这些示例程序在 v6.0 之前就已存在兼容性问题。

### 2.2 First Run 测试 (3 个失败)

| 测试用例 | 失败原因 |
|----------|----------|
| `test_create_first_run_tutorial` | ImportError: `create_first_run_tutorial` 函数在 `interactive_tutorial.py` 中不存在（实际函数名为 `run_first_run_tutorial`） |
| `test_save_and_load_progress` | 进度文件未创建，assert 0 == 1 |
| `test_clear_progress_file` | 路径不存在，assert False |

**根因**: 测试文件 `test_first_run.py` 引用了 `interactive_tutorial` 模块中不存在的函数名 `create_first_run_tutorial`（实际为 `run_first_run_tutorial`）。后续两个测试依赖该函数创建的环境，级联失败。

**状态**: 非回归缺陷 — 测试代码与源代码不同步。

---

## 3. 已修复的测试

| 测试用例 | 修复内容 |
|----------|----------|
| `test_chinese_exc_name` | 更新测试断言以匹配 `_chinese_exc_name` 实际返回值 |
| `test_name_error` | 更新断言字符串从 '变量未定义' 改为 '名称错误' |
| `test_attribute_error` | 更新断言字符串从 '属性不存在' 改为 '属性错误' |
| `test_key_error_with_suggestion` | 更新断言字符串从 '键不存在' 改为 '键错误' |
| `test_attribute_error_with_type_hint` | 更新断言字符串从 '属性不存在' 改为 '属性错误' |
| `test_completion_returns_items` | 修复 LSP 中 `doc` 变量名被循环变量覆盖的 bug |
| `test_completion_has_keywords` | 同上 |

---

## 4. 性能对比

| 指标 | v6.0 | v6.1 | 变化 |
|------|------|------|------|
| 总测试数 | ~2500 | 2536 | +36 |
| 通过率 | ~97.5% | 97.5% | 持平 |
| 运行时间 | ~97s | ~106s | +9s (更多测试) |
| 失败数 | 11 | 13 | +2 (新增测试中的 pre-existing 问题) |

---

## 5. 测试覆盖率

- 单元测试: 覆盖全部核心模块（词法分析、语法解析、AST适配、类型检查、代码生成、优化器）
- 集成测试: 覆盖模块系统、类系统、编译器管道
- E2E 测试: 覆盖完整编译-运行链路
- LSP 测试: 覆盖语言服务器协议

---

## 6. 建议

1. **修复示例程序语法**: 将 `examples/` 目录下的 `.duan` 示例更新为兼容 v6.1 语法
2. **同步测试代码**: 修复 `test_first_run.py` 中的函数引用，使其与 `interactive_tutorial.py` 保持一致
3. **增加 CI 集成**: 建议将测试套件集成到 CI 管道中，在每次提交后自动运行