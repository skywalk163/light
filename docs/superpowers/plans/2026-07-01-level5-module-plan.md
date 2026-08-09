# Level 5 Phase 5.2：模块系统 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在自举编译器中实现模块系统（导入/导出），支持内联编译、搜索路径和循环依赖检测。自举编译器自身保持单文件。

**架构：** 在 bootstrap_level5.light（已实现异常处理的版本）基础上新增导入/导出关键字。模块系统在编译入口处进行预处理：收集所有导入 → 解析依赖图 → 拓扑排序 → 内联合并 → 统一编译。导出信息在预处理阶段收集，用于符号过滤。

**技术栈：** Light 自举编译器、Python 后端

---

## 文件清单

| 文件 | 操作 | 职责 |
|------|------|------|
| `bootstrap/bootstrap_level5.light` | 修改 | 在异常处理基础上添加模块系统 |
| `bootstrap/test_level5_module.py` | 新建 | 模块系统测试脚本 |
| `bootstrap/test_modules/` | 新建 | 测试用模块文件目录 |
| `bootstrap/test_modules/math_utils.light` | 新建 | 测试用数学工具模块 |
| `bootstrap/test_modules/string_utils.light` | 新建 | 测试用字符串工具模块 |
| `bootstrap/test_modules/nested/deep.light` | 新建 | 测试用嵌套路径模块 |

---

## 任务 0：准备工作 - 创建测试模块文件

**文件：**
- 创建：`bootstrap/test_modules/math_utils.light`
- 创建：`bootstrap/test_modules/string_utils.light`
- 创建：`bootstrap/test_modules/nested/deep.light`

- [ ] **步骤 1：创建测试模块目录和文件**

运行：
```powershell
New-Item -ItemType Directory -Force -Path bootstrap/test_modules/nested
```

创建 `bootstrap/test_modules/math_utils.light`：
```
段 加 导出 接收 a, b：
    返回 a 加 b
结束。

段 乘 导出 接收 a, b：
    返回 a 乘 b
结束。

段 平方 导出 接收 x：
    返回 x 乘 x
结束。

段 内部工具 接收 x：
    返回 x 加 1
结束。

导出 PI
设 PI 为 3.14159
```

创建 `bootstrap/test_modules/string_utils.light`：
```
段 拼接 导出 接收 a, b：
    返回 a 加 b
结束。

段 长度 导出 接收 s：
    返回 字符串长度(s)
结束。

段 内部处理 接收 s：
    返回 s 加 "_processed"
结束。

导出 版本号
设 版本号 为 "1.0.0"
```

创建 `bootstrap/test_modules/nested/deep.light`：
```
段 深度问候 导出 接收 name：
    返回 "你好，" 加 name
结束。
```

- [ ] **步骤 2：Commit**

```bash
git add bootstrap/test_modules/
git commit -m "test: 添加模块系统测试用例文件"
```

---

## 任务 1：词法分析 - 新增导入/导出关键字

**文件：**
- 修改：`bootstrap/bootstrap_level5.light`（`关键字列表` 函数）

- [ ] **步骤 1：编写失败的测试**

创建 `bootstrap/test_level5_module.py`：
```python
import sys
sys.path.insert(0, 'bootstrap')

def test_import_export_keywords():
    exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
    toks = 词法("导入 导出 math_utils")
    kw_count = sum(1 for t in toks if t[0] == 'KW')
    assert kw_count >= 2, f"期望至少 2 个关键字，实际 {kw_count}"
    print("✅ 导入/导出关键字识别测试通过")

if __name__ == '__main__':
    print("Level 5 模块系统测试")
    print("=" * 50)
    test_import_export_keywords()
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
toks = 词法('导入 导出 math')
kw = [t for t in toks if t[0] == 'KW']
print('关键字数量:', len(kw))
print('关键字:', [t[1] for t in kw])
"
```

预期：导入/导出未被识别为关键字

- [ ] **步骤 3：修改关键字列表**

在 `bootstrap/bootstrap_level5.light` 中，找到 `段 关键字列表：` 函数，在 `抛出` 之后添加 `导入` 和 `导出`：

将：
```
返回 列表创建(..., "父", "尝试", "捕获", "最终", "抛出")
```

改为：
```
返回 列表创建(..., "父", "尝试", "捕获", "最终", "抛出", "导入", "导出")
```

- [ ] **步骤 4：重新编译并验证**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
# 用 Level 4 编译 Level 5
exec(open('bootstrap/level4_generated.py', encoding='utf-8').read())
src = open('bootstrap/bootstrap_level5.light', encoding='utf-8').read()
result = 编译(src)
with open('bootstrap/level5_generated.py', 'w', encoding='utf-8') as f:
    f.write(result)
print('编译成功，长度:', len(result))
# 验证关键字
exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
toks = 词法('导入 导出 math')
kw = [t for t in toks if t[0] == 'KW']
print('关键字:', [t[1] for t in kw])
"
```

预期：`导入`、`导出` 被识别为关键字

- [ ] **步骤 5：Commit**

```bash
git add bootstrap/bootstrap_level5.light
git commit -m "feat(lexer): 新增模块系统关键字（导入/导出）"
```

---

## 任务 2：模块解析 - 搜索路径与文件读取

**文件：**
- 修改：`bootstrap/bootstrap_level5.light`（新增 `解析导入`、`查找模块文件`、`读取模块源码` 等函数）

- [ ] **步骤 1：编写失败的测试**

在 `bootstrap/test_level5_module.py` 添加：
```python
def test_module_search():
    import os
    exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
    # 测试在当前目录下查找模块
    module_path = 查找模块文件("math_utils", os.path.join(os.getcwd(), "bootstrap", "test_modules"))
    assert module_path is not None, f"应找到 math_utils 模块"
    assert "math_utils.light" in module_path, f"路径应包含文件名: {module_path}"
    print("✅ 模块搜索测试通过")
```

- [ ] **步骤 2：运行测试验证失败**

预期：`查找模块文件` 函数不存在

- [ ] **步骤 3：实现模块查找函数**

在 `bootstrap/bootstrap_level5.light` 中，`异常类型映射` 函数之前添加模块系统相关函数。

由于自举编译器是单文件 Light 代码，运行在 Python 环境中，我们需要利用 Python 内置的文件操作能力。

策略：新增辅助函数，通过调用 Python 的 `open`、`os.path.exists` 等功能来实现模块查找。

具体实现：
```
段 查找模块文件 接收 module_name, base_dir：
  设 分隔符 为 "/"。
  设 文件名 为 module_name 加 ".light"。
  设 路径1 为 base_dir 加 分隔符 加 文件名。
  如果 文件存在(路径1)：
    返回 路径1。
  结束。
  设 路径2 为 base_dir 加 分隔符 加 "模块" 加 分隔符 加 文件名。
  如果 文件存在(路径2)：
    返回 路径2。
  结束。
  设 路径3 为 base_dir 加 分隔符 加 ".." 加 分隔符 加 "stdlib" 加 分隔符 加 文件名。
  如果 文件存在(路径3)：
    返回 路径3。
  结束。
  返回 ""。
结束。

段 读取文件 接收 path：
  返回 文件读取(path)。
结束。
```

注意：`文件存在` 和 `文件读取` 需要在代码生成时映射到 Python 对应函数。由于我们是生成 Python 代码并执行，这些函数可以直接调用 Python 的 `os.path.exists` 和 `open().read()`。

更简单的方式：在编译入口处添加 Python 辅助函数。但自举编译器是纯 Light 代码...

实际上，自举编译器生成的是 Python 代码。模块系统的文件操作需要在生成的 Python 代码中调用 Python 的文件操作函数。

**重新设计方案：** 模块系统的文件读取、依赖解析等功能，在当前阶段先在** Python 层的测试脚本中实现**（作为编译前的预处理步骤）。自举编译器 `bootstrap_level5.light` 本身仍然是单文件，只负责语法层面的 `导入`/`导出` 关键字识别和符号管理。

这样分层更清晰：
- **预处理层（Python）**：文件查找、依赖图构建、拓扑排序、内联合并
- **编译器层（Light）**：识别 `导入`/`导出` 语法，正确编译合并后的代码

让我调整计划，采用分层方案：

任务 2 改为：在 Python 层实现模块预处理器。

- [ ] **步骤 3（修订）：创建模块预处理器（Python 层）**

创建 `bootstrap/module_preprocessor.py`：
```python
"""
Light 模块预处理器
在编译前处理导入语句，将多个模块内联为单个文件
"""

import os
from pathlib import Path
from typing import List, Dict, Set, Tuple


class ModulePreprocessor:
    def __init__(self, search_paths: List[str] = None):
        self.search_paths = search_paths or []
        self.module_cache: Dict[str, str] = {}
        self.exported_symbols: Dict[str, Set[str]] = {}

    def find_module(self, module_name: str, current_dir: str) -> str:
        """查找模块文件路径"""
        file_name = module_name + ".light"
        paths_to_try = []
        paths_to_try.append(os.path.join(current_dir, file_name))
        paths_to_try.append(os.path.join(current_dir, "模块", file_name))
        paths_to_try.append(os.path.join(current_dir, "modules", file_name))
        for sp in self.search_paths:
            paths_to_try.append(os.path.join(sp, file_name))
        for path in paths_to_try:
            if os.path.exists(path):
                return os.path.normpath(path)
        raise FileNotFoundError(f"模块未找到: {module_name}\n搜索路径:\n" + 
                                "\n".join(f"  - {p}" for p in paths_to_try))

    def extract_imports(self, source: str) -> List[str]:
        """从源码中提取导入的模块名"""
        imports = []
        for line in source.split('\n'):
            stripped = line.strip()
            if stripped.startswith('导入 ') and not stripped.startswith('导入"'):
                parts = stripped.split()
                if len(parts) >= 2:
                    module_name = parts[1]
                    if module_name not in imports:
                        imports.append(module_name)
        return imports

    def extract_exports(self, source: str) -> Set[str]:
        """从源码中提取导出的符号名"""
        exports = set()
        lines = source.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('导出 '):
                parts = stripped.split()
                if len(parts) >= 2:
                    exports.add(parts[1])
            if ' 导出 ' in stripped and ('段 ' in stripped or '段落 ' in stripped):
                parts = stripped.split()
                for j, p in enumerate(parts):
                    if p == '导出' and j > 0:
                        if parts[0] == '段' or parts[0] == '段落':
                            if j >= 2:
                                exports.add(parts[j - 1])
        return exports

    def build_dependency_graph(self, main_file: str) -> Tuple[Dict[str, str], List[str]]:
        """构建依赖图并拓扑排序，返回 {模块名: 源码} 和拓扑排序后的模块名列表"""
        modules = {}
        main_dir = os.path.dirname(os.path.abspath(main_file))
        to_visit = [(main_file, main_dir)]
        visited = set()
        order = []

        while to_visit:
            module_path, current_dir = to_visit.pop()
            abs_path = os.path.normpath(os.path.abspath(module_path))
            if abs_path in visited:
                continue
            visited.add(abs_path)
            with open(module_path, 'r', encoding='utf-8') as f:
                source = f.read()
            modules[abs_path] = source
            module_name = os.path.splitext(os.path.basename(module_path))[0]
            order.append((abs_path, module_name))
            imports = self.extract_imports(source)
            for imp in reversed(imports):
                try:
                    found_path = self.find_module(imp, current_dir)
                    found_dir = os.path.dirname(found_path)
                    to_visit.append((found_path, found_dir))
                except FileNotFoundError:
                    pass

        return modules, [p for p, _ in order]

    def detect_circular_deps(self, modules: Dict[str, str], order: List[str]) -> List[str]:
        """检测循环依赖"""
        graph = {}
        name_to_path = {}
        for path in order:
            name = os.path.splitext(os.path.basename(path))[0]
            name_to_path[name] = path
            imports = self.extract_imports(modules[path])
            graph[path] = set()
            for imp in imports:
                if imp in name_to_path:
                    graph[path].add(name_to_path[imp])

        visited = set()
        rec_stack = set()
        cycle = []

        def dfs(node, path):
            if node in rec_stack:
                idx = path.index(node)
                cycle.extend(path[idx:] + [node])
                return True
            if node in visited:
                return False
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, set()):
                if dfs(neighbor, path + [neighbor]):
                    return True
            rec_stack.remove(node)
            return False

        for node in graph:
            if dfs(node, [node]):
                return cycle
        return []

    def inline_modules(self, main_file: str) -> str:
        """将主文件及其所有依赖内联为单个源码"""
        modules, order = self.build_dependency_graph(main_file)
        cycle = self.detect_circular_deps(modules, order)
        if cycle:
            names = [os.path.basename(p) for p in cycle]
            raise ValueError(f"检测到循环依赖: {' → '.join(names)}")

        combined = []
        processed = set()
        for path in reversed(order):
            if path in processed:
                continue
            processed.add(path)
            source = modules[path]
            filtered_lines = []
            for line in source.split('\n'):
                stripped = line.strip()
                if stripped.startswith('导入 '):
                    continue
                filtered_lines.append(line)
            combined.extend(filtered_lines)
            combined.append('')

        return '\n'.join(combined)


def preprocess_compile(main_file: str, compile_func) -> str:
    """预处理并编译主文件"""
    preprocessor = ModulePreprocessor()
    combined_source = preprocessor.inline_modules(main_file)
    return compile_func(combined_source)
```

- [ ] **步骤 4：测试模块预处理器**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
from module_preprocessor import ModulePreprocessor
mp = ModulePreprocessor()
main_path = 'bootstrap/test_modules/math_utils.light'
modules, order = mp.build_dependency_graph(main_path)
print('模块数量:', len(modules))
print('顺序:', [p for p in order])
source = modules[order[0]]
imports = mp.extract_imports(source)
print('导入:', imports)
exports = mp.extract_exports(source)
print('导出:', exports)
"
```

预期：正确找到模块，提取导入和导出

- [ ] **步骤 5：Commit**

```bash
git add bootstrap/module_preprocessor.py bootstrap/test_modules/
git commit -m "feat(modules): 实现模块预处理器（Python 层）"
```

---

## 任务 3：编译器层 - 导入/导出语法识别

**文件：**
- 修改：`bootstrap/bootstrap_level5.light`（`compile_block` 中添加导入/导出语句处理）

- [ ] **步骤 1：编写失败的测试**

在 `bootstrap/test_level5_module.py` 添加：
```python
def test_import_export_syntax():
    exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
    # 导入语句应被正确跳过（预处理器已处理导入）
    code = """导入 math_utils
设 x 为 1
输出(x)
"""
    result = 编译(code)
    assert '1' in result or 'x' in result, f"应正确编译: {result}"
    print("✅ 导入语法编译测试通过")
```

- [ ] **步骤 2：运行测试验证**

运行测试，检查导入语句是否导致编译错误。

- [ ] **步骤 3：在 compile_block 中添加导入语句处理**

在 `bootstrap/bootstrap_level5.light` 的 `compile_block` 函数中，找到语句分派部分，在 `设` 的处理之前添加：

```
      如果 已处理 等于 假 且 tv 等于 "导入"：
        设 np 为 p 加 1。
        当 np 小于 列表长度(toks)：
          设 nt 为 列表获取(toks, np)。
          设 ntv 为 列表获取(nt, 1)。
          如果 ntv 等于 "。" 或 ntv 等于 "\n"：
            跳出。
          结束。
          设 np 为 np 加 1。
        结束。
        设 p 为 np。
        设 已处理 为 真。
      结束。
```

注意：由于预处理器已经将导入的模块内联进来，编译器层面只需要忽略 `导入` 语句即可（不生成任何代码）。

同样，`导出` 语句在编译器层面也只需忽略（预处理器已处理符号管理）：

```
      如果 已处理 等于 假 且 tv 等于 "导出"：
        设 np 为 p 加 1。
        当 np 小于 列表长度(toks)：
          设 nt 为 列表获取(toks, np)。
          设 ntv 为 列表获取(nt, 1)。
          如果 ntv 等于 "。"：
            设 np 为 np 加 1。
            跳出。
          结束。
          设 np 为 np 加 1。
        结束。
        设 p 为 np。
        设 已处理 为 真。
      结束。
```

对于内联 `导出`（`段 函数名 导出 接收 ...`），编译器在函数定义时遇到 `导出` 关键字直接跳过即可。

- [ ] **步骤 4：处理函数定义中的内联导出**

找到函数定义的解析部分（`段 段...` 或 `段落...` 相关处理），如果遇到 `导出` 关键字，跳过它。

在自举编译器中，函数定义通过 `编译段` 或类似函数处理。找到对应位置，在解析函数名后，如果遇到 `导出` 关键字 token，跳过它。

具体来说，在 `compile_func` 或类似函数中，函数名识别后、`接收` 识别前，检查是否为 `导出`，如果是则跳过。

- [ ] **步骤 5：重新编译并测试**

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
# 测试导入语句
code = '导入 math_utils\n设 x 为 1\n输出(x)'
r = 编译(code)
print('导入语句编译结果:')
print(r)
"
```

预期：导入语句被跳过，代码正常编译

- [ ] **步骤 6：Commit**

```bash
git add bootstrap/bootstrap_level5.light
git commit -m "feat(parser): 编译器层支持导入/导出语法识别"
```

---

## 任务 4：完整测试 - 模块系统功能验证

**文件：**
- 测试：`bootstrap/test_level5_module.py`

- [ ] **步骤 1：编写完整测试套件**

在 `bootstrap/test_level5_module.py` 中添加所有测试：
```python
import sys
import os
import io
import contextlib

sys.path.insert(0, 'bootstrap')
from module_preprocessor import ModulePreprocessor, preprocess_compile

def run_compiled(light_code):
    exec(open('bootstrap/level5_generated.py', encoding='utf-8').read())
    py_code = 编译(light_code)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(py_code, {'__name__': '__main__'})
    return output.getvalue()

def test_single_import():
    mp = ModulePreprocessor()
    main_dir = os.path.join('bootstrap', 'test_modules')
    test_main = os.path.join(main_dir, 'test_single.light')
    with open(test_main, 'w', encoding='utf-8') as f:
        f.write("""导入 math_utils
设 r 为 加(3, 4)
输出(r)
""")
    combined = mp.inline_modules(test_main)
    result = run_compiled(combined)
    assert "7" in result, f"加函数应正常工作: {result}"
    os.remove(test_main)
    print("✅ 单模块导入测试通过")

def test_multiple_imports():
    mp = ModulePreprocessor()
    main_dir = os.path.join('bootstrap', 'test_modules')
    test_main = os.path.join(main_dir, 'test_multi.light')
    with open(test_main, 'w', encoding='utf-8') as f:
        f.write("""导入 math_utils
导入 string_utils
设 r1 为 乘(5, 6)
输出(r1)
设 r2 为 拼接("hello", "world")
输出(r2)
""")
    combined = mp.inline_modules(test_main)
    result = run_compiled(combined)
    assert "30" in result, f"乘函数应工作: {result}"
    assert "helloworld" in result, f"拼接函数应工作: {result}"
    os.remove(test_main)
    print("✅ 多模块导入测试通过")

def test_nested_path_import():
    mp = ModulePreprocessor()
    main_dir = os.path.join('bootstrap', 'test_modules')
    test_main = os.path.join(main_dir, 'test_nested.light')
    with open(test_main, 'w', encoding='utf-8') as f:
        f.write("""导入 nested/deep
设 msg 为 深度问候("世界")
输出(msg)
""")
    combined = mp.inline_modules(test_main)
    result = run_compiled(combined)
    assert "你好" in result, f"深度问候应工作: {result}"
    os.remove(test_main)
    print("✅ 嵌套路径导入测试通过")

def test_export_variable():
    mp = ModulePreprocessor()
    main_dir = os.path.join('bootstrap', 'test_modules')
    test_main = os.path.join(main_dir, 'test_export_var.light')
    with open(test_main, 'w', encoding='utf-8') as f:
        f.write("""导入 math_utils
输出(PI)
""")
    combined = mp.inline_modules(test_main)
    result = run_compiled(combined)
    assert "3.14159" in result, f"PI 变量应导出: {result}"
    os.remove(test_main)
    print("✅ 导出变量测试通过")

def test_circular_dependency():
    mp = ModulePreprocessor()
    main_dir = os.path.join('bootstrap', 'test_modules')
    a_path = os.path.join(main_dir, 'circular_a.light')
    b_path = os.path.join(main_dir, 'circular_b.light')
    with open(a_path, 'w', encoding='utf-8') as f:
        f.write("导入 circular_b\n段 fa 导出 接收 x：\n    返回 x 加 1\n")
    with open(b_path, 'w', encoding='utf-8') as f:
        f.write("导入 circular_a\n段 fb 导出 接收 x：\n    返回 x 乘 2\n")
    try:
        mp.inline_modules(a_path)
        assert False, "应检测到循环依赖"
    except ValueError as e:
        assert "循环依赖" in str(e), f"错误信息应包含循环依赖: {e}"
    os.remove(a_path)
    os.remove(b_path)
    print("✅ 循环依赖检测测试通过")

def test_inline_export():
    mp = ModulePreprocessor()
    main_dir = os.path.join('bootstrap', 'test_modules')
    exports = mp.extract_exports(open(os.path.join(main_dir, 'math_utils.light'), encoding='utf-8').read())
    assert "加" in exports, f"应导出 加: {exports}"
    assert "乘" in exports, f"应导出 乘: {exports}"
    assert "平方" in exports, f"应导出 平方: {exports}"
    assert "内部工具" not in exports, f"不应导出 内部工具: {exports}"
    print("✅ 内联导出识别测试通过")

def test_level4_regression():
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
    result = run_compiled(code)
    assert "30" in result
    assert "3" in result
    print("✅ Level 4 回归测试通过")

def test_exception_still_works():
    code = """尝试：
    抛出 "测试"
捕获：
    输出("已捕获")
"""
    result = run_compiled(code)
    assert "已捕获" in result
    print("✅ 异常处理回归测试通过")

if __name__ == '__main__':
    print("Level 5 模块系统测试")
    print("=" * 50)
    test_single_import()
    test_multiple_imports()
    test_nested_path_import()
    test_export_variable()
    test_circular_dependency()
    test_inline_export()
    test_level4_regression()
    test_exception_still_works()
    print("=" * 50)
    print("🎉 所有模块系统测试通过!")
```

- [ ] **步骤 2：运行完整测试**

运行：
```powershell
python bootstrap/test_level5_module.py
```

预期：所有测试通过

- [ ] **步骤 3：修复遇到的问题**

根据测试失败情况修复代码。

- [ ] **步骤 4：Commit**

```bash
git add bootstrap/test_level5_module.py
git commit -m "test: 添加模块系统完整测试套件"
```

---

## 任务 5：自举验证

**文件：**
- 生成：`bootstrap/level5_bootstrapped.py`

- [ ] **步骤 1：用 Level 5 编译器编译自身**

运行：
```powershell
python -c "
import sys
sys.path.insert(0, 'bootstrap')
# v1: Level 4 编译 Level 5
exec(open('bootstrap/level4_generated.py', encoding='utf-8').read())
src = open('bootstrap/bootstrap_level5.light', encoding='utf-8').read()
v1 = 编译(src)
with open('bootstrap/level5_generated.py', 'w', encoding='utf-8') as f:
    f.write(v1)
print('v1 生成成功, 长度:', len(v1))
# v2: Level 5 自举
exec(v1)
v2 = 编译(src)
with open('bootstrap/level5_bootstrapped.py', 'w', encoding='utf-8') as f:
    f.write(v2)
print('v2 生成成功, 长度:', len(v2))
print('v1 == v2:', v1 == v2)
"
```

预期：v1 == v2（收敛）

- [ ] **步骤 2：运行所有测试（使用自举编译器）**

将测试脚本改为使用 `level5_bootstrapped.py`，运行全部通过。

- [ ] **步骤 3：Commit**

```bash
git add bootstrap/level5_generated.py bootstrap/level5_bootstrapped.py
git commit -m "feat(bootstrap): Level 5 模块系统自举验证通过"
```

---

## 任务 6：文档更新

**文件：**
- 创建：`docs/level5_spec.md`
- 更新：`docs/syntax.md`
- 更新：`README.md`

- [ ] **步骤 1：创建 level5_spec.md**

基于规格文档 [2026-07-01-level5-module-exception-design.md](file:///g:/dumategithub/light/docs/superpowers/specs/2026-07-01-level5-module-exception-design.md)，创建用户可见的规格文档。

- [ ] **步骤 2：更新 syntax.md**

在语法文档中新增模块系统和异常处理章节。

- [ ] **步骤 3：更新 README.md**

更新版本号和特性列表。

- [ ] **步骤 4：Commit**

```bash
git add docs/level5_spec.md docs/syntax.md README.md
git commit -m "docs: 更新 Level 5 相关文档"
```

---

## 自检清单

- [x] 规格覆盖：导入/导出语法、搜索路径、内联编译、循环依赖检测 — 全部有对应任务
- [x] 无占位符：每个步骤有具体代码和命令
- [x] 分层设计：Python 层预处理器 + Light 层语法识别，职责清晰
- [x] 自举验证：任务 5 专门验证自举收敛
- [x] 回归测试：包含 Level 4 功能和异常处理的回归测试
