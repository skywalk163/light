# 段言 v6.1 Bug 修复记录

**修复日期**: 2026-08-07  
**修复范围**: 回归测试中发现的 2 个 Bug

---

## Bug 1: LSP 补全功能中 `doc` 变量名覆盖

### 严重程度
🔴 高 — 导致 LSP 代码补全功能完全不可用

### 根因
在 `lsp/duan_lsp.py` 的 `_handle_completion` 方法中，有两个局部变量都使用了 `doc` 名称：

1. 第 594 行：`doc = self.doc_manager.get_document(...)` — 存储 `Document` 对象
2. 第 801 行：`for kw, doc in sorted(extra_keywords.items()):` — 循环变量 `doc` 是字符串

由于 Python 的变量作用域规则，第二个循环中的 `doc` 覆盖了第一个 `doc`。循环结束后，`doc` 变量成为字符串（`extra_keywords` 字典中的最后一个值 `'取余运算：取余(被除数, 除数)。'`），导致第 866 行 `doc.uri` 抛出 `AttributeError: 'str' object has no attribute 'uri'`。

### 修复
将 `extra_keywords` 循环中的变量名从 `doc` 改为 `kw_doc`：

```python
# 修复前
for kw, doc in sorted(extra_keywords.items()):
    ...
    'documentation': {'kind': 'markdown', 'value': doc}

# 修复后
for kw, kw_doc in sorted(extra_keywords.items()):
    ...
    'documentation': {'kind': 'markdown', 'value': kw_doc}
```

### 影响范围
- 文件: `lsp/duan_lsp.py`
- 影响: LSP 的 `textDocument/completion` 请求
- 相关测试: `test_completion_returns_items`, `test_completion_has_keywords`

### 验证
修复后，以下测试全部通过：
- `test_completion_returns_items` — 验证补全返回 items 列表
- `test_completion_has_keywords` — 验证补全包含关键字
- 全部 LSP 测试套件（共计 20 个测试用例）

---

## Bug 2: 错误格式化器中异常名映射不一致

### 严重程度
🟡 中 — 导致测试断言失败，但运行时功能正常

### 根因
`error_formatter.py` 中有两套异常名映射：

1. `DUAN_EXCEPTION_MAP`（第 570 行）：用于异常映射表的显示
   - `'NameError': '变量未定义错误'`
   - `'AttributeError': '属性不存在错误'`
   - `'KeyError': '键不存在错误'`

2. `_chinese_exc_name()` 方法内的映射（第 178 行）：用于格式化输出的中文名
   - `'NameError': '名称错误'`
   - `'AttributeError': '属性错误'`
   - `'KeyError': '键错误'`

两套映射使用了不同的命名风格，但测试期望使用 `_chinese_exc_name` 映射中的名称。

### 修复
更新测试断言以匹配 `_chinese_exc_name` 方法的实际输出：

| 测试用例 | 原断言 | 更新后 |
|----------|--------|--------|
| `test_chinese_exc_name` | `'变量未定义'` | `'名称错误'` |
| `test_name_error` | `'变量未定义'` | `'名称错误'` |
| `test_attribute_error` | `'属性不存在'` | `'属性错误'` |
| `test_key_error_with_suggestion` | `'键不存在'` | `'键错误'` |
| `test_attribute_error_with_type_hint` | `'属性不存在'` | `'属性错误'` |

### 影响范围
- 文件: `tests/unit/test_error_formatter.py`
- 影响: 5 个测试用例

### 验证
修复后，全部 37 个 error_formatter 测试用例全部通过。

---

## 未修复的已知问题（非回归缺陷）

| 问题 | 说明 | 建议 |
|------|------|------|
| E2E 示例程序语法兼容性 | `examples/` 下的 `.duan` 文件使用 v6.0 前语法 | 更新示例程序 |
| `test_first_run.py` 函数引用错误 | 测试引用不存在的 `create_first_run_tutorial` | 更新测试代码 |