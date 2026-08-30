# Level 7 实现计划：类型注解 + 自举验证

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 Level 6（无空格分词 + 纯缩进语法）的基础上，实现类型注解系统，并通过自举验证确认编译器收敛。

**架构：** 所有修改集中在 `bootstrap/level6_generated.py`。类型注解是语法层面的增强——在词法分析中识别类型标识符，在语法分析中解析类型标注，在代码生成中可选插入运行时类型检查。

**技术栈：** 纯 Python（自举编译器运行环境）

**前置阅读：**
- 规格文档 `docs/superpowers/specs/2026-07-01-level6-type-annotation-design.md` 第三、四、五章
- 修复报告 `docs/Level6_自举编译器修复报告.md`
- 当前实现 `bootstrap/level6_generated.py`

---

## 文件变更

### 核心文件
- **修改：** `bootstrap/level6_generated.py` — 所有改动

### 测试文件
- **创建：** `bootstrap/test_level7_types.py` — 类型注解专项测试
- **创建：** `bootstrap/test_level7_bootstrap.py` — 自举验证测试

### 文档
- **创建：** `docs/level7_spec.md` — 最终规格总结
- **修改：** `docs/BOOTSTRAP_STRATEGY.md` — 更新 Level 7 状态

---

## 任务 1：变量类型注解

**目标：** 支持 `设x为整数=10` 形式的变量声明，在代码生成阶段保留类型信息。

### 当前状态分析

`level6_generated.py` 的 `comp_set` 函数当前只处理 `设x为10` 这种形式：

```python
def comp_set(toks, p):
    # 跳过 "设" 关键字
    p = p + 1
    # 读取变量名
    var_name = 列表获取(列表获取(toks, p), 1)
    p = p + 1
    # 跳过 "为" 关键字
    p = p + 1
    # 读取初始值表达式
    expr = compile_expression(toks, p)
    ...
```

需要扩展为：`设 变量名 为 [类型] = [初始值]` 或 `设 变量名 为 [类型]` 或 `设 变量名 = 初始值`。

### 类型识别机制

类型名不加入关键字列表（避免命名歧义），而是在语法分析阶段通过上下文识别：

1. `设` 关键字后，读取变量名
2. 遇到 `为` 关键字后，尝试读取类型标识符：
   - 如果下一个 token 是类型名（`整数`、`文本`、`小数`、`布尔`、`列表`、`字典` 等），则作为类型注解
   - 如果下一个 token 不是类型名，则作为初始值表达式（向后兼容 `设x为10`）
3. 类型注解后，如果遇到 `=`，则读取初始值表达式

### 类型列表

| 类型名 | Python 对应 | 说明 |
|-------|------------|------|
| `整数` | int | 整数 |
| `文本` | str | 字符串 |
| `小数` | float | 浮点数 |
| `布尔` | bool | 布尔值 |
| `空` | NoneType | 空值 |
| `列表` | list | 列表 |
| `字典` | dict | 字典 |

- [ ] **步骤 1.1：添加类型名识别函数**

```python
def 是类型名(name):
    return name in ("整数", "文本", "小数", "布尔", "空", "列表", "字典")

def 类型名到Python(tname):
    if tname == "整数": return "int"
    if tname == "文本": return "str"
    if tname == "小数": return "float"
    if tname == "布尔": return "bool"
    if tname == "空": return "None"
    if tname == "列表": return "list"
    if tname == "字典": return "dict"
    return tname
```

- [ ] **步骤 1.2：修改 `comp_set` 函数**

扩展为支持三种变量声明形式：

```python
def comp_set(toks, p, indent):
    # 跳过 "设" 关键字
    p = p + 1
    # 读取变量名
    var_name = 列表获取(列表获取(toks, p), 1)
    p = p + 1
    # 跳过 "为" 关键字
    p = p + 1
    # 检查下一个 token 是否为类型名
    ntt = 列表获取(列表获取(toks, p), 0)
    ntv = 列表获取(列表获取(toks, p), 1)
    if 是类型名(ntv):
        # 形式: 设x为整数 = 10 或 设x为整数
        type_name = ntv
        py_type = 类型名到Python(type_name)
        p = p + 1
        # 检查是否有初始值
        if p < n and 列表获取(列表获取(toks, p), 0) == "ASSIGN":
            p = p + 1  # 跳过 =
            expr = compile_expression(toks, p)
            expr_code = 列表获取(expr, 0)
            p = 列表获取(expr, 1)
            return f"{var_name}: {py_type} = {expr_code}", p
        else:
            return f"{var_name}: {py_type} = None", p
    else:
        # 形式: 设x为10 (向后兼容)
        expr = compile_expression(toks, p)
        expr_code = 列表获取(expr, 0)
        p = 列表获取(expr, 1)
        return f"{var_name} = {expr_code}", p
```

- [ ] **步骤 1.3：添加类型注解测试**

```python
t("变量整数类型注解",
   """
段主函数
    设x为整数=10
    输出(x)
""",
   "10")

t("变量文本类型注解",
   """
段主函数
    设name为文本="hello"
    输出(name)
""",
   "hello")

t("变量类型注解无初始值",
   """
段主函数
    设x为整数
    输出("ok")
""",
   "ok")

t("向后兼容无类型注解",
   """
段主函数
    设x为10
    输出(x)
""",
   "10")
```

- [ ] **步骤 1.4：运行测试并修复**

---

## 任务 2：函数参数和返回类型注解

**目标：** 支持 `段add接收a整数,b整数返回整数：` 形式的函数定义。

### 当前状态分析

`compile_func` 函数当前处理 `段函数名接收参数` 的形式，需要扩展为识别参数后的类型名和返回类型。

### 语法形式

```
# 完整形式
段add接收a整数,b整数返回整数：
    返回a加b

# 无返回类型
段add接收a整数,b整数：
    返回a加b

# 无类型注解（向后兼容）
段add接收a,b：
    返回a加b
```

- [ ] **步骤 2.1：修改函数参数解析**

在 `compile_func` 中，读取参数名后，检查下一个 token 是否为类型名：

```python
def compile_func(toks, p, indent):
    # 跳过 "段" 关键字
    p = p + 1
    # 读取函数名
    func_name = 列表获取(列表获取(toks, p), 1)
    p = p + 1
    # 跳过 "接收" 关键字
    p = p + 1
    # 解析参数列表
    params = []
    while p < n:
        ntv = 列表获取(列表获取(toks, p), 1)
        if ntv == "返回" or ntv == "：" or ntv == ":":
            break
        param_name = 列表获取(列表获取(toks, p), 1)
        p = p + 1
        # 检查是否有类型注解
        if 是类型名(列表获取(列表获取(toks, p), 1)):
            param_type = 列表获取(列表获取(toks, p), 1)
            py_type = 类型名到Python(param_type)
            params.append(f"{param_name}: {py_type}")
            p = p + 1
        else:
            params.append(param_name)
        # 跳过逗号
        if p < n and 列表获取(列表获取(toks, p), 1) == ",":
            p = p + 1
    # 检查返回类型
    return_type = ""
    if p < n and 列表获取(列表获取(toks, p), 1) == "返回":
        p = p + 1
        if 是类型名(列表获取(列表获取(toks, p), 1)):
            return_type = 类型名到Python(列表获取(列表获取(toks, p), 1))
            p = p + 1
    ...
```

- [ ] **步骤 2.2：添加函数类型注解测试**

```python
t("函数参数和返回类型注解",
   """
段add接收a整数,b整数返回整数
    返回a加b
段主函数
    输出(add(3,4))
""",
   "7")

t("函数参数类型注解无返回",
   """
段greet接收name文本
    输出(name)
段主函数
    greet("hello")
""",
   "hello")

t("向后兼容无类型注解函数",
   """
段add接收a,b
    返回a加b
段主函数
    输出(add(3,4))
""",
   "7")
```

- [ ] **步骤 2.3：运行测试并修复**

---

## 任务 3：复合类型注解

**目标：** 支持 `列表[整数]`、`字典[文本, 整数]` 等复合类型。

### 语法形式

```
设arr为列表[整数]=[1,2,3]
设map为字典[文本,整数]={"a":1}
段process接收items列表[整数]
```

- [ ] **步骤 3.1：扩展 `是类型名` 函数**

```python
def 是类型名(name):
    return name in ("整数", "文本", "小数", "布尔", "空", "列表", "字典")

def 解析类型(toks, p):
    """解析类型表达式，返回 (类型字符串, 新位置)"""
    ntv = 列表获取(列表获取(toks, p), 1)
    if not 是类型名(ntv):
        return "", p
    type_str = ntv
    p = p + 1
    # 检查泛型参数: 列表[整数]
    if p < len(toks):
        ntt = 列表获取(列表获取(toks, p), 0)
        if ntt == "LBRACKET":
            type_str += "["
            p = p + 1
            # 解析泛型参数列表
            while p < len(toks):
                elem_ntt = 列表获取(列表获取(toks, p), 0)
                elem_ntv = 列表获取(列表获取(toks, p), 1)
                if elem_ntt == "RBRACKET":
                    type_str += "]"
                    p = p + 1
                    break
                if elem_ntv == ",":
                    type_str += ", "
                    p = p + 1
                    continue
                elem_type, p = 解析类型(toks, p)
                type_str += elem_type
    return type_str, p
```

- [ ] **步骤 3.2：添加复合类型测试**

```python
t("列表类型注解",
   """
段主函数
    设arr为列表[整数]=[1,2,3]
    输出(列表长度(arr))
""",
   "3")
```

- [ ] **步骤 3.3：运行测试并修复**

---

## 任务 4：运行时类型检查

**目标：** 可选启用运行时类型检查，在赋值和函数调用时验证类型。

### 设计

- 默认关闭类型检查（零性能开销）
- 通过 `开启类型检查` / `关闭类型检查` 语句控制范围
- 检查失败时抛出 `类型错误`（TypeError）

### 实现策略

在代码生成阶段，对带类型注解的变量赋值插入类型检查：

```python
# 设x为整数=10
x: int = 10
if not isinstance(x, int):
    raise TypeError(f"期望 int, 实际 {type(x)}")

# 函数参数类型检查
def add(a: int, b: int) -> int:
    if not isinstance(a, int):
        raise TypeError(f"参数 a 期望 int, 实际 {type(a)}")
    if not isinstance(b, int):
        raise TypeError(f"参数 b 期望 int, 实际 {type(b)}")
    result = a + b
    if not isinstance(result, int):
        raise TypeError(f"返回值期望 int, 实际 {type(result)}")
    return result
```

- [ ] **步骤 4.1：添加类型检查函数**

{% raw %}
```python
def 生成类型检查代码(var_name, py_type, indent):
    """生成运行时类型检查代码"""
    indent_str = "    " * indent
    return f'{indent_str}if not isinstance({var_name}, {py_type}):\n' \
           f'{indent_str}    raise TypeError(f"期望 {py_type}, 实际 {{type({var_name})}}")'

def 生成类型检查全局开关():
    """生成类型检查开关变量"""
    return "类型检查开启 = 假"
```
{% endraw %}

- [ ] **步骤 4.2：修改 `comp_set` 支持类型检查**

在生成赋值代码后，如果类型检查开启且变量有类型注解，插入类型检查代码。

- [ ] **步骤 4.3：添加 `开启类型检查` / `关闭类型检查` 语句支持**

在 `compile_block` 中处理这两个关键字：

```python
if ntv == "开启类型检查":
    列表追加(out_lines, "# 类型检查开启")
    out += add_indent("类型检查开启 = 真", indent) + "\n"
    p = p + 1
    已处理 = 真
if ntv == "关闭类型检查":
    列表追加(out_lines, "# 类型检查关闭")
    out += add_indent("类型检查开启 = 假", indent) + "\n"
    p = p + 1
    已处理 = 真
```

- [ ] **步骤 4.4：添加类型检查测试**

```python
t("运行时类型检查通过",
   """
段主函数
    开启类型检查
    设x为整数=10
    输出(x)
    关闭类型检查
""",
   "10")

t("运行时类型检查失败",
   """
段主函数
    开启类型检查
    设x为整数="hello"
    输出("should_not_reach")
    关闭类型检查
""",
   "TypeError",
   "TypeError")  # 应抛出 TypeError
```

- [ ] **步骤 4.5：运行测试并修复**

---

## 任务 5：自举验证

**目标：** 用 Level 7 生成的编译器编译自身，验证自举收敛。

### 5.1 自举验证流程

```
┌─────────────────────────────────────────────────────┐
│  Phase 1: 编译自身                                    │
│  level6_generated.py → 编译 bootstrap_level5.light    │
│                     → level7_generated.py           │
│  验证: 38 个 Level 6 测试用例在 level7 上通过        │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│  Phase 2: 二次自举                                    │
│  level7_generated.py → 编译 bootstrap_level5.light    │
│                     → level7_self_compiled.py        │
│  验证: level7_generated.py == level7_self_compiled.py│
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│  Phase 3: 三次验证                                    │
│  level7_self_compiled.py → 编译 bootstrap_level5.light│
│                         → level7_self_compiled2.py   │
│  验证: level7_self_compiled.py == level7_self_compiled2.py│
└─────────────────────────────────────────────────────┘
```

### 5.2 自举前提条件

在开始自举验证前，必须确保：

1. Level 7 编译器能正确编译所有 Level 6 语法（向后兼容）
2. 类型注解新增的语法特性有完整的测试覆盖
3. 编译器自身的 `.light` 源码（`bootstrap_level5.light`）不需要修改即可在新编译器上运行

### 5.3 自举验证脚本

- [ ] **步骤 5.1：确保向后兼容**

运行所有 38 个 Level 6 测试用例，确认全部通过：
```bash
python bootstrap/test_level6_full.py
python bootstrap/_test_edge_cases.py
```

- [ ] **步骤 5.2：运行类型注解测试**

```bash
python bootstrap/test_level7_types.py
```

- [ ] **步骤 5.3：第一次自举编译**

```python
# 用 level6_generated.py 的编译功能，编译 bootstrap_level5.light
# 输出 level7_generated.py
# 比较 level7_generated.py 与手动修改的版本
```

- [ ] **步骤 5.4：第二次自举编译**

```python
# 用 level7_generated.py 编译 bootstrap_level5.light
# 输出 level7_self_compiled.py
# 比较 level7_generated.py 与 level7_self_compiled.py
```

- [ ] **步骤 5.5：第三次自举验证**

```python
# 用 level7_self_compiled.py 编译 bootstrap_level5.light
# 输出 level7_self_compiled2.py
# 比较 level7_self_compiled.py 与 level7_self_compiled2.py
# 如果一致，自举收敛验证通过
```

- [ ] **步骤 5.6：自举测试脚本**

创建 `bootstrap/test_level7_bootstrap.py`：

```python
def 自举验证():
    """三级自举一致性验证"""
    src_path = "bootstrap/bootstrap_level5.light"
    
    # 阶段1: 用 Python 实现编译自身
    py_code1 = 编译(open(src_path).read())
    with open("bootstrap/level7_generated.py", "w") as f:
        f.write(py_code1)
    
    # 阶段2: 用生成的编译器再次编译
    ns = {...}
    exec(py_code1, ns)
    编译2 = ns['编译']
    py_code2 = 编译2(open(src_path).read())
    with open("bootstrap/level7_self_compiled.py", "w") as f:
        f.write(py_code2)
    
    # 阶段3: 验证收敛
    assert py_code1 == py_code2, "自举未收敛!"
    print("✅ 自举验证通过：两次输出一致")
```

- [ ] **步骤 5.7：Commit**

---

## 任务 6：向后兼容和回归测试

- [ ] **步骤 6.1：运行 Level 5 异常测试**

```bash
python bootstrap/test_level5_exception.py
```

- [ ] **步骤 6.2：运行 Level 5 模块测试**

```bash
python bootstrap/test_level5_module.py
```

- [ ] **步骤 6.3：运行 Level 6 全面测试（38 用例）**

```bash
python bootstrap/test_level6_full.py
python bootstrap/_test_edge_cases.py
```

- [ ] **步骤 6.4：修复所有回归问题**

- [ ] **步骤 6.5：更新文档**

更新 `docs/BOOTSTRAP_STRATEGY.md` 和 `docs/level7_spec.md`。

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 类型名与标识符冲突 | 用户自定义标识符与类型名重名 | 类型名不加入关键字列表，通过上下文识别 |
| 自举不收敛 | 编译器输出有差异 | 仔细检查代码生成逻辑，确保无状态依赖 |
| 性能下降 | 运行时类型检查增加开销 | 默认关闭类型检查，仅按需开启 |
| 向后兼容破坏 | 现有 Level 6 代码不能编译 | 所有测试用例必须在每次修改后通过 |

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-08-05-level7-type-annotation-bootstrap.md`。

两种执行方式：
1. **子代理驱动（推荐）** — 每个任务调度一个新的子代理，任务间进行审查，快速迭代
2. **内联执行** — 在当前会话中逐任务执行，批量执行并设有检查点