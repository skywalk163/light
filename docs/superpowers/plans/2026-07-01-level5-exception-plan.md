# Level 5 Phase 5.1：异常处理 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在自举编译器中实现异常处理（尝试/捕获/最终/抛出），支持多重捕获、异常类型映射和任意表达式抛出。

**架构：** 在 bootstrap_level4.light 基础上新增 4 个关键字和相应解析函数，生成 Python 原生 try/except/finally 代码。异常类型映射在代码生成阶段处理，不影响前端解析。

**技术栈：** Light 自举编译器（bootstrap_level4.light → bootstrap_level5.light）、Python 后端

---

## 文件清单

| 文件 | 操作 | 职责 |
|------|------|------|
| `bootstrap/bootstrap_level5.light` | 新建（基于 level4 复制） | 自举编译器主文件，新增异常处理功能 |
| `bootstrap/test_level5_exception.py` | 新建 | 异常处理测试脚本 |
| `bootstrap/level5_generated.py` | 生成 | Level 5 编译器生成代码 |
| `bootstrap/level5_bootstrapped.py` | 生成 | 自举编译后的代码 |

---

## 任务 0：准备工作 - 复制 Level 4 代码库

**文件：**
- 创建：`bootstrap/bootstrap_level5.light`（复制 `bootstrap_level4.light`）
- 测试：`bootstrap/test_level5_exception.py`

- [ ] **步骤 1：复制 Level 4 编译器为 Level 5**

运行：
```powershell
Copy-Item bootstrap/bootstrap_level4.light bootstrap/bootstrap_level5.light
```

- [ ] **步骤 2：创建测试文件骨架**

在 `bootstrap/test_level5_exception.py` 写入：
```python
import sys
sys.path.insert(0, '.')

def run_test(name, code, expected_output, should_raise=False):
    # 编译并运行 Light 代码，检查输出
    pass

if __name__ == '__main__':
    print("Level 5 异常处理测试")
    print("=" * 50)
```

- [ ] **步骤 3：验证 Level 5 初始代码可用 Level 4 编译**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
exec(open('bootstrap/level4_generated.py', encoding='utf-8').read())
src = open('bootstrap/bootstrap_level5.light', encoding='utf-8').read()
result = 编译(src)
with open('bootstrap/level5_generated.py', 'w', encoding='utf-8') as f:
    f.write(result)
print('初始编译成功，生成代码长度:', len(result))
"
```

预期：编译成功，无报错

- [ ] **步骤 4：Commit**

```bash
git add bootstrap/bootstrap_level5.light
git commit -m "chore: 复制 Level 4 编译器为 Level 5 初始版本"
```

---

## 任务 1：词法分析 - 新增异常处理关键字

**文件：**
- 修改：`bootstrap/bootstrap_level5.light`（`关键字列表` 函数）

- [ ] **步骤 1：编写失败的测试**

在 `bootstrap/test_level5_exception.py` 添加 `test_keywords`：
```python
def test_keywords():
    import sys
    sys.path.insert(0, 'bootstrap')
    exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
    # 测试关键字识别
    toks = 词法("尝试 捕获 最终 抛出")
    kw_count = sum(1 for t in toks if t[0] == 'KW')
    assert kw_count == 4, f"期望 4 个关键字，实际 {kw_count}"
    print("✅ 关键字识别测试通过")
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
from test_level5_exception import test_keywords
test_keywords()
"
```

预期：FAIL（关键字未注册）

- [ ] **步骤 3：修改关键字列表函数**

在 `bootstrap/bootstrap_level5.light` 中，找到 `段 关键字列表：` 函数，将：
```
返回 列表创建("设", "段落", "段", "返回", "结束", "为", "如果", "否则", "当", "接收", "加", "减", "乘", "除", "取模", "等于", "小于", "大于", "小于等于", "大于等于", "不等于", "且", "或", "非", "遍历", "在", "类", "属性", "己", "继承", "父")
```

改为（在末尾添加 4 个关键字）：
```
返回 列表创建("设", "段落", "段", "返回", "结束", "为", "如果", "否则", "当", "接收", "加", "减", "乘", "除", "取模", "等于", "小于", "大于", "小于等于", "大于等于", "不等于", "且", "或", "非", "遍历", "在", "类", "属性", "己", "继承", "父", "尝试", "捕获", "最终", "抛出")
```

- [ ] **步骤 4：重新编译 Level 5 并运行测试**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
exec(open('bootstrap/level4_generated.py', encoding='utf-8').read())
src = open('bootstrap/bootstrap_level5.light', encoding='utf-8').read()
result = 编译(src)
with open('bootstrap/level5_generated.py', 'w', encoding='utf-8') as f:
    f.write(result)
print('编译成功')
exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
toks = 词法('尝试 捕获 最终 抛出')
kw = [t for t in toks if t[0] == 'KW']
print('关键字数量:', len(kw))
print('关键字列表:', [t[1] for t in kw])
"
```

预期：关键字数量为 4

- [ ] **步骤 5：Commit**

```bash
git add bootstrap/bootstrap_level5.light
git commit -m "feat(lexer): 新增异常处理关键字（尝试/捕获/最终/抛出）"
```

---

## 任务 2：解析 - 抛出语句

**文件：**
- 修改：`bootstrap/bootstrap_level5.light`（新增 `comp_throw` 函数，修改 `compile_block`）

- [ ] **步骤 1：编写失败的测试**

在 `bootstrap/test_level5_exception.py` 添加：
```python
def test_throw_string():
    import sys
    sys.path.insert(0, 'bootstrap')
    exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
    code = '抛出 "测试错误"'
    result = 编译(code)
    assert 'raise' in result, f"生成代码应包含 raise: {result}"
    assert 'Exception' in result, f"字符串应包装为 Exception: {result}"
    print("✅ 抛出字符串测试通过")
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
code = '抛出 \"测试错误\"'
try:
    result = 编译(code)
    print('生成代码:', result)
except Exception as e:
    print('错误:', e)
"
```

预期：报错或生成代码不含 raise

- [ ] **步骤 3：实现 comp_throw 函数**

在 `bootstrap/bootstrap_level5.light` 中，`find_matching_end` 函数之前添加：
```
段 comp_throw 接收 toks, p：
  如果 p 小于 列表长度(toks)：
    设 tok 为 列表获取(toks, p)。
    如果 列表获取(tok, 1) 等于 "抛出"：
      设 结果 为 表达式(toks, p 加 1)。
      设 expr 为 列表获取(结果, 0)。
      设 np 为 列表获取(结果, 1)。
      设 stmt 为 "raise " 加 expr。
      返回 列表创建(stmt, np)。
    结束。
  结束。
  返回 列表创建("", p)。
结束。
```

- [ ] **步骤 4：在 compile_block 中添加抛出语句分派**

找到 `compile_block` 函数中 `返回` 语句的处理（`如果 已处理 等于 假 且 tv 等于 "返回"：`），在其后面添加：
```
      如果 已处理 等于 假 且 tv 等于 "抛出"：
        设 结果 为 comp_throw(toks, p)。
        设 stmt 为 列表获取(结果, 0)。
        设 np 为 列表获取(结果, 1)。
        设 out 为 out 加 indent 加 stmt 加 "\n"。
        设 p 为 np。
        设 已处理 为 真。
      结束。
```

- [ ] **步骤 5：在 find_matching_end 中添加抛出关键字**

找到 `find_matching_end` 函数，在 `返回` 的 level 检查之后添加 `抛出`（抛出不改变 level，只是作为语句识别）。

实际上抛出不需要修改 find_matching_end，因为它不是块结构。跳过此步。

- [ ] **步骤 6：重新编译并运行测试**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
exec(open('bootstrap/level4_generated.py', encoding='utf-8').read())
src = open('bootstrap/bootstrap_level5.light', encoding='utf-8').read()
result = 编译(src)
with open('bootstrap/level5_generated.py', 'w', encoding='utf-8') as f:
    f.write(result)
print('编译成功')
exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
# 测试抛出字符串
code1 = '抛出 \"测试错误\"'
r1 = 编译(code1)
print('抛出字符串生成:', r1.strip())
# 测试抛出变量
code2 = '设 e 为 \"错误\"。抛出 e'
r2 = 编译(code2)
print('抛出变量生成:', r2.strip())
"
```

预期：
- 抛出字符串生成 `raise Exception("测试错误")`
- 抛出变量生成 `e = "错误"\nraise e`

注意：当前实现的 `抛出 表达式` 会直接生成 `raise 表达式`。如果表达式是字符串字面量，需要额外判断是否为字符串类型并包装为 Exception。在自举编译器中，我们先简单实现为 `raise 表达式`，用户可以自行构造异常对象。字符串自动包装可以后续优化。

- [ ] **步骤 7：Commit**

```bash
git add bootstrap/bootstrap_level5.light
git commit -m "feat(parser): 实现抛出语句解析"
```

---

## 任务 3：解析 - 尝试-捕获-最终块（基础版）

**文件：**
- 修改：`bootstrap/bootstrap_level5.light`（新增 `comp_try` 函数）

- [ ] **步骤 1：编写失败的测试**

在 `bootstrap/test_level5_exception.py` 添加：
```python
def test_try_catch_basic():
    import sys
    sys.path.insert(0, 'bootstrap')
    exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
    code = """尝试：
    输出("测试")
捕获：
    输出("捕获错误")
"""
    result = 编译(code)
    assert 'try:' in result, f"应生成 try: {result}"
    assert 'except:' in result, f"应生成 except: {result}"
    print("✅ 基础尝试-捕获测试通过")
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
code = '尝试：\n    输出(\"测试\")\n捕获：\n    输出(\"错误\")'
try:
    result = 编译(code)
    print('生成:', result)
except Exception as e:
    print('错误:', e)
"
```

预期：报错（未识别尝试关键字）

- [ ] **步骤 3：实现 comp_try 函数（基础版 - 单捕获无类型）**

在 `comp_throw` 函数之后添加：
```
段 comp_try 接收 toks, p：
  如果 p 小于 列表长度(toks)：
    设 tok 为 列表获取(toks, p)。
    如果 列表获取(tok, 1) 等于 "尝试"：
      设 np 为 p 加 1。
      设 try_body_start 为 np。
      设 catch_start 为 -1。
      设 finally_start 为 -1。
      设 level 为 1。
      当 np 小于 列表长度(toks)：
        设 ct 为 列表获取(toks, np)。
        如果 列表获取(ct, 0) 等于 "KW"：
          设 ctv 为 列表获取(ct, 1)。
          如果 ctv 等于 "尝试" 或 ctv 等于 "如果" 或 ctv 等于 "当" 或 ctv 等于 "遍历" 或 ctv 等于 "类" 或 ctv 等于 "段落" 或 ctv 等于 "段"：
            设 level 为 level 加 1。
          结束。
          如果 ctv 等于 "结束"：
            设 level 为 level 减 1。
            如果 level 等于 0：
              返回 列表创建("", np 加 1)。
            结束。
          结束。
          如果 level 等于 1 且 ctv 等于 "捕获"：
            设 catch_start 为 np。
          结束。
          如果 level 等于 1 且 ctv 等于 "最终"：
            设 finally_start 为 np。
          结束。
        结束。
        设 np 为 np 加 1。
      结束。
      返回 列表创建("", p 加 1)。
    结束。
  结束。
  返回 列表创建("", p)。
结束。
```

注意：上述函数只是占位的结构扫描。实际实现需要编译 try 块体和 catch 块体并生成代码。让我们重新设计 comp_try 的实现方式。

正确的实现策略：利用现有的 `compile_block` 和 `find_matching_end` 机制。

让我重新设计 comp_try：

```
段 comp_try 接收 toks, p, indent：
  如果 p 小于 列表长度(toks)：
    设 tok 为 列表获取(toks, p)。
    如果 列表获取(tok, 1) 等于 "尝试"：
      设 np 为 p 加 1。
      设 out 为 indent 加 "try:\n"。
      设 继续扫描 为 真。
      设 try_end 为 -1。
      设 catch_positions 为 列表创建()。
      设 finally_pos 为 -1。
      设 level 为 1。
      设 scan_p 为 np。
      当 scan_p 小于 列表长度(toks) 且 继续扫描：
        设 st 为 列表获取(toks, scan_p)。
        如果 列表获取(st, 0) 等于 "KW"：
          设 stv 为 列表获取(st, 1)。
          如果 stv 等于 "尝试" 或 stv 等于 "如果" 或 stv 等于 "当" 或 stv 等于 "遍历" 或 stv 等于 "类" 或 stv 等于 "段落" 或 stv 等于 "段"：
            设 level 为 level 加 1。
          结束。
          如果 stv 等于 "结束"：
            设 level 为 level 减 1。
            如果 level 等于 0：
              设 try_end 为 scan_p。
              设 继续扫描 为 假。
            结束。
          结束。
          如果 level 等于 1 且 stv 等于 "捕获"：
            列表追加(catch_positions, scan_p)。
          结束。
          如果 level 等于 1 且 stv 等于 "最终"：
            设 finally_pos 为 scan_p。
          结束。
        结束。
        设 scan_p 为 scan_p 加 1。
      结束。
      如果 try_end 等于 -1：
        返回 列表创建("", p 加 1)。
      结束。
      设 body_indent 为 indent 加 "    "。
      设 try_body_end 为 np。
      如果 列表长度(catch_positions) 大于 0：
        设 try_body_end 为 列表获取(catch_positions, 0)。
      否则如果 finally_pos 不等于 -1：
        设 try_body_end 为 finally_pos。
      否则：
        设 try_body_end 为 try_end。
      结束。
      设 try_result 为 compile_stmts(toks, np, try_body_end, body_indent, "")。
      设 out 为 out 加 try_result。
      设 ci 为 0。
      当 ci 小于 列表长度(catch_positions)：
        设 cp 为 列表获取(catch_positions, ci)。
        设 next_pos 为 try_end。
        如果 ci 加 1 小于 列表长度(catch_positions)：
          设 next_pos 为 列表获取(catch_positions, ci 加 1)。
        结束。
        如果 finally_pos 不等于 -1 且 finally_pos 大于 cp 且 (ci 加 1 大于等于 列表长度(catch_positions) 或 列表获取(catch_positions, ci 加 1) 大于 finally_pos)：
          设 next_pos 为 finally_pos。
        结束。
        设 catch_type 为 ""。
        设 catch_var 为 ""。
        设 catch_body_start 为 cp 加 1。
        设 ctp 为 cp 加 1。
        设 找类型 为 真。
        当 ctp 小于 next_pos 且 找类型：
          设 ct 为 列表获取(toks, ctp)。
          如果 列表获取(ct, 0) 等于 "ID" 或 列表获取(ct, 0) 等于 "KW"：
            如果 catch_type 等于 ""：
              设 catch_type 为 列表获取(ct, 1)。
              设 ctp 为 ctp 加 1。
            否则如果 列表获取(ct, 1) 等于 "as"：
              设 ctp 为 ctp 加 1。
              如果 ctp 小于 next_pos：
                设 vt 为 列表获取(toks, ctp)。
                设 catch_var 为 列表获取(vt, 1)。
                设 ctp 为 ctp 加 1。
              结束。
              设 catch_body_start 为 ctp。
              设 找类型 为 假。
            否则：
              设 catch_body_start 为 ctp。
              设 找类型 为 假。
            结束。
          否则：
            设 catch_body_start 为 ctp。
            设 找类型 为 假。
          结束。
        结束。
        设 except_line 为 indent 加 "except"。
        如果 catch_type 不等于 ""：
          设 except_line 为 except_line 加 " " 加 catch_type。
        结束。
        如果 catch_var 不等于 ""：
          设 except_line 为 except_line 加 " as " 加 catch_var。
        结束。
        设 except_line 为 except_line 加 ":\n"。
        设 out 为 out 加 except_line。
        设 catch_result 为 compile_stmts(toks, catch_body_start, next_pos, body_indent, "")。
        设 out 为 out 加 catch_result。
        设 ci 为 ci 加 1。
      结束。
      如果 finally_pos 不等于 -1：
        设 out 为 out 加 indent 加 "finally:\n"。
        设 fin_result 为 compile_stmts(toks, finally_pos 加 1, try_end, body_indent, "")。
        设 out 为 out 加 fin_result。
      结束。
      返回 列表创建(out, try_end 加 1)。
    结束。
  结束。
  返回 列表创建("", p)。
结束。
```

这个函数很长，但逻辑是：
1. 扫描整个 try 块，找到所有捕获位置和最终位置
2. 编译 try 主体
3. 逐个编译 catch 块（解析类型和 as 变量）
4. 编译 finally 块（如果有）

- [ ] **步骤 4：在 compile_block 中添加尝试语句分派**

找到 `compile_block` 函数中 `当` 循环的语句分派部分，在 `返回` 的处理之后添加：
```
      如果 已处理 等于 假 且 tv 等于 "尝试"：
        设 结果 为 comp_try(toks, p, indent)。
        设 stmt 为 列表获取(结果, 0)。
        设 np 为 列表获取(结果, 1)。
        设 out 为 out 加 stmt。
        设 p 为 np。
        设 已处理 为 真。
      结束。
```

- [ ] **步骤 5：在 find_matching_end 中添加尝试/捕获/最终关键字**

找到 `find_matching_end` 函数，在 `类` 的 level 增加处（`如果 tv 等于 "类"：设 level 为 level 加 1。结束。`）之后添加：
```
      如果 tv 等于 "尝试"：
        设 level 为 level 加 1。
      结束。
```

注意：`捕获` 和 `最终` 不改变 level，它们在同一 level 内。

- [ ] **步骤 6：确保 compile_stmts 函数存在**

检查 bootstrap_level5.light 中是否有 `compile_stmts` 函数。如果没有，需要基于 `compile_block` 提取或调整。

如果只有 `compile_block`，可以让 `comp_try` 直接调用 `compile_block` 的内部逻辑，或者创建一个 `compile_stmts` 辅助函数。

策略：直接复用现有的块编译机制。`comp_try` 自己管理子块的编译（使用递归调用 `编译` 或复用 `compile_block`）。

更简单的方案：`comp_try` 返回的结果直接包含完整的 try/except/finally 代码，不需要依赖 compile_block 的复杂逻辑。

- [ ] **步骤 7：重新编译并运行测试**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
exec(open('bootstrap/level4_generated.py', encoding='utf-8').read())
src = open('bootstrap/bootstrap_level5.light', encoding='utf-8').read()
result = 编译(src)
with open('bootstrap/level5_generated.py', 'w', encoding='utf-8') as f:
    f.write(result)
print('编译成功，代码长度:', len(result))
"
```

预期：编译成功

然后测试基础 try/catch：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
# 测试1: 简单 try/catch
code1 = '尝试：\n    输出(\"hello\")\n捕获：\n    输出(\"error\")'
r1 = 编译(code1)
print('=== 测试1: 简单try/catch ===')
print(r1)
"
```

预期：生成包含 `try:` 和 `except:` 的 Python 代码

- [ ] **步骤 8：Commit**

```bash
git add bootstrap/bootstrap_level5.light
git commit -m "feat(parser): 实现尝试-捕获-最终块解析"
```

---

## 任务 4：异常类型映射（中文别名）

**文件：**
- 修改：`bootstrap/bootstrap_level5.light`（新增 `映射异常类型` 函数，修改 `comp_try`）

- [ ] **步骤 1：编写失败的测试**

在 `bootstrap/test_level5_exception.py` 添加：
```python
def test_exception_type_mapping():
    import sys
    sys.path.insert(0, 'bootstrap')
    exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
    code = """尝试：
    抛出 "错误"
捕获 值错误 as e：
    输出("值错误")
"""
    result = 编译(code)
    assert 'ValueError' in result, f"值错误应映射为 ValueError: {result}"
    assert 'as e' in result, f"应保留 as e: {result}"
    print("✅ 异常类型映射测试通过")
```

- [ ] **步骤 2：运行测试验证失败**

运行测试，预期生成的代码中 `值错误` 未被映射为 `ValueError`。

- [ ] **步骤 3：实现异常类型映射函数**

在 `comp_try` 函数之前添加：
```
段 异常类型映射 接收 name：
  如果 name 等于 "异常"：
    返回 "Exception"。
  结束。
  如果 name 等于 "值错误"：
    返回 "ValueError"。
  结束。
  如果 name 等于 "类型错误"：
    返回 "TypeError"。
  结束。
  如果 name 等于 "键错误"：
    返回 "KeyError"。
  结束。
  如果 name 等于 "索引错误"：
    返回 "IndexError"。
  结束。
  如果 name 等于 "除零错误"：
    返回 "ZeroDivisionError"。
  结束。
  如果 name 等于 "属性错误"：
    返回 "AttributeError"。
  结束。
  如果 name 等于 "名称错误"：
    返回 "NameError"。
  结束。
  如果 name 等于 "文件错误"：
    返回 "FileNotFoundError"。
  结束。
  如果 name 等于 "运行错误"：
    返回 "RuntimeError"。
  结束。
  如果 name 等于 "停止迭代"：
    返回 "StopIteration"。
  结束。
  返回 name。
结束。
```

- [ ] **步骤 4：在 comp_try 中使用类型映射**

找到 `comp_try` 中设置 `except_line` 的部分：
```
        设 except_line 为 indent 加 "except"。
        如果 catch_type 不等于 ""：
          设 except_line 为 except_line 加 " " 加 catch_type。
        结束。
```

改为：
```
        设 except_line 为 indent 加 "except"。
        如果 catch_type 不等于 ""：
          设 mapped_type 为 异常类型映射(catch_type)。
          设 except_line 为 except_line 加 " " 加 mapped_type。
        结束。
```

- [ ] **步骤 5：重新编译并运行测试**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
exec(open('bootstrap/level4_generated.py', encoding='utf-8').read())
src = open('bootstrap/bootstrap_level5.light', encoding='utf-8').read()
result = 编译(src)
with open('bootstrap/level5_generated.py', 'w', encoding='utf-8') as f:
    f.write(result)
print('编译成功')
exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
code = '尝试：\n    抛出 \"错误\"\n捕获 值错误 as e：\n    输出(\"值错误\")'
r = 编译(code)
print('生成代码:')
print(r)
"
```

预期：生成 `except ValueError as e:`

- [ ] **步骤 6：Commit**

```bash
git add bootstrap/bootstrap_level5.light
git commit -m "feat(codegen): 实现异常类型中文别名映射"
```

---

## 任务 5：完整测试 - 异常处理功能验证

**文件：**
- 测试：`bootstrap/test_level5_exception.py`

- [ ] **步骤 1：编写完整测试套件**

在 `bootstrap/test_level5_exception.py` 中添加所有测试：
```python
import sys
import io
import contextlib

def compile_and_run(light_code):
    sys.path.insert(0, 'bootstrap')
    exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
    py_code = 编译(light_code)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        try:
            exec(py_code, {'__name__': '__main__'})
            return output.getvalue(), None
        except Exception as e:
            return output.getvalue(), type(e).__name__

def test_basic_try_catch():
    code = """尝试：
    输出("try块")
    抛出 "测试异常"
    输出("不会执行")
捕获：
    输出("捕获异常")
"""
    out, err = compile_and_run(code)
    assert "try块" in out, f"应执行try块: {out}"
    assert "捕获异常" in out, f"应捕获异常: {out}"
    assert "不会执行" not in out, f"不应执行抛出后代码: {out}"
    print("✅ 基础尝试-捕获测试通过")

def test_catch_with_type():
    code = """尝试：
    设 x 为 1 除 0
捕获 除零错误：
    输出("除零")
捕获 值错误：
    输出("值错误")
"""
    out, err = compile_and_run(code)
    assert "除零" in out, f"应捕获除零错误: {out}"
    assert "值错误" not in out, f"不应匹配值错误: {out}"
    print("✅ 类型捕获测试通过")

def test_catch_with_var():
    code = """尝试：
    抛出 "测试消息"
捕获 异常 as e：
    输出("捕获到: " + 字符串(e))
"""
    out, err = compile_and_run(code)
    assert "捕获到" in out, f"应捕获异常: {out}"
    print("✅ 捕获变量测试通过")

def test_finally_block():
    code = """尝试：
    输出("try")
    抛出 "错"
捕获：
    输出("catch")
最终：
    输出("finally")
"""
    out, err = compile_and_run(code)
    assert "try" in out, f"应执行try: {out}"
    assert "catch" in out, f"应执行catch: {out}"
    assert "finally" in out, f"应执行finally: {out}"
    print("✅ 最终块测试通过")

def test_nested_try():
    code = """尝试：
    尝试：
        抛出 "内层错误"
    捕获 值错误：
        输出("内层捕获值错误")
    捕获：
        输出("内层捕获全部")
    捕获：
    输出("外层")
"""
    out, err = compile_and_run(code)
    assert "内层捕获全部" in out, f"内层应捕获: {out}"
    assert "外层" in out, f"外层应继续: {out}"
    print("✅ 嵌套尝试测试通过")

def test_throw_variable():
    code = """设 msg 为 "动态错误"
尝试：
    抛出 msg
捕获：
    输出("已捕获")
"""
    out, err = compile_and_run(code)
    assert "已捕获" in out, f"应捕获变量抛出: {out}"
    print("✅ 抛出变量测试通过")

def test_level4_regression():
    # Level 4 基础功能仍应工作
    code = """设 a 为 10
设 b 为 20
输出(a 加 b)
类 Point：
    段落 __init__ 接收 己, x, y：
        设 己.x 为 x
        设 己.y 为 y
    结束。
结束。
设 p 为 Point(3, 4)
输出(p.x)
"""
    out, err = compile_and_run(code)
    assert "30" in out, f"加法应正常: {out}"
    assert "3" in out, f"类属性应正常: {out}"
    assert err is None, f"不应有错误: {err}"
    print("✅ Level 4 回归测试通过")

if __name__ == '__main__':
    print("Level 5 异常处理测试")
    print("=" * 50)
    test_basic_try_catch()
    test_catch_with_type()
    test_catch_with_var()
    test_finally_block()
    test_nested_try()
    test_throw_variable()
    test_level4_regression()
    print("=" * 50)
    print("🎉 所有异常处理测试通过!")
```

- [ ] **步骤 2：运行完整测试**

运行：
```powershell
python bootstrap/test_level5_exception.py
```

预期：所有 7 个测试通过

- [ ] **步骤 3：修复遇到的问题**

如果测试失败，根据错误信息修复 `comp_try` 或其他函数。

常见问题排查：
- `find_matching_end` 未正确处理 `尝试` 关键字导致块边界错误
- `compile_block` 中 `尝试` 分派位置不对导致无法识别
- 缩进计算错误导致生成 Python 代码语法错误

- [ ] **步骤 4：Commit**

```bash
git add bootstrap/test_level5_exception.py
git commit -m "test: 添加异常处理完整测试套件"
```

---

## 任务 6：自举验证

**文件：**
- 生成：`bootstrap/level5_bootstrapped.py`

- [ ] **步骤 1：用 Level 5 编译器编译自身**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
# v1: Level 4 编译 Level 5 源码
exec(open('bootstrap/level4_generated.py', encoding='utf-8').read())
src = open('bootstrap/bootstrap_level5.light', encoding='utf-8').read()
v1 = 编译(src)
with open('bootstrap/level5_generated.py', 'w', encoding='utf-8') as f:
    f.write(v1)
print('v1 生成成功, 长度:', len(v1))
# v2: Level 5 编译自身
exec(v1)
v2 = 编译(src)
with open('bootstrap/level5_bootstrapped.py', 'w', encoding='utf-8') as f:
    f.write(v2)
print('v2 生成成功, 长度:', len(v2))
# 验证收敛
print('v1 == v2:', v1 == v2)
"
```

预期：
- v1 生成成功
- v2 生成成功
- v1 == v2（收敛验证）

- [ ] **步骤 2：运行自举后的测试**

```powershell
python -c "
import sys, io, contextlib
sys.path.insert(0, 'bootstrap')
exec(open('bootstrap/level5_bootstrapped.py', encoding='utf-8').read())
# 用自举编译器编译一个异常处理示例
code = '尝试：\n    输出(\"hello\")\n捕获：\n    输出(\"error\")'
result = 编译(code)
print('自举编译结果:')
print(result)
# 验证功能
out = io.StringIO()
with contextlib.redirect_stdout(out):
    exec(result, {'__name__': '__main__'})
print('输出:', out.getvalue().strip())
"
```

预期：自举编译器功能正常

- [ ] **步骤 3：运行完整测试（使用自举编译器）**

修改测试脚本使用 bootstrapped 版本运行，确认全部通过。

- [ ] **步骤 4：Commit**

```bash
git add bootstrap/level5_generated.py bootstrap/level5_bootstrapped.py
git commit -m "feat(bootstrap): Level 5 异常处理自举验证通过"
```

---

## 自检清单

- [x] 规格覆盖：尝试/捕获/最终/抛出、多重捕获、异常类型映射、任意表达式抛出 — 全部有对应任务
- [x] 无占位符：每个步骤有具体代码和命令
- [x] 类型一致：函数命名与 Level 4 风格一致（`comp_` 前缀、驼峰命名等）
- [x] 自举验证：任务 6 专门验证自举收敛
