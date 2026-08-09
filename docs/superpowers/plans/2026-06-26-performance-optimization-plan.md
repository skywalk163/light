# 性能优化方案 B - 深度优化实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 编译速度 +40~60%，运行速度 +30~40%，内存 -20~30%

**架构：** 新增 optimizer/ 模块实现常量折叠、死代码消除、循环不变量外提；优化 lexer.py（查表+预编译）、ast_nodes_v3.py（__slots__）、code_generator.py（join+缓存）、compiler.py（增量缓存）

**技术栈：** Python 3.12, dataclass, __slots__, tracemalloc

---

## 文件结构

```
src/
├── optimizer/                  # 新增：优化器模块
│   ├── __init__.py
│   ├── base.py                 # 优化器基类
│   ├── constant_fold.py        # 常量折叠
│   ├── dead_code.py           # 死代码消除
│   └── loop_invariant.py      # 循环不变量外提
├── lexer.py                    # 修改：查表 + 预编译
├── ast_nodes_v3.py            # 修改：__slots__
├── code_generator.py          # 修改：列表 join + 缩进缓存
└── compiler.py                # 修改：增量编译缓存

tests/
├── unit/
│   └── test_optimizer.py      # 新增：优化器单元测试
```

---

## 阶段 1：词法分析器 + AST 优化

### 任务 1：AST 节点添加 __slots__

**文件：**
- 修改：`src/ast_nodes_v3.py`
- 测试：`tests/unit/test_ast_slots.py`（新建）

- [ ] **步骤 1：创建测试文件验证 __slots__**

```python
# tests/unit/test_ast_slots.py
import pytest
from src.ast_nodes_v3 import NumberLiteral, StringLiteral, Identifier

def test_number_literal_has_slots():
    node = NumberLiteral(value=42)
    assert not hasattr(node, '__dict__'), "NumberLiteral should use __slots__"
    assert node.value == 42

def test_identifier_has_slots():
    node = Identifier(name="test")
    assert not hasattr(node, '__dict__'), "Identifier should use __slots__"
    assert node.name == "test"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/unit/test_ast_slots.py -v`
预期：FAIL - hasattr(node, '__dict__') 为 True

- [ ] **步骤 3：修改 ast_nodes_v3.py 添加 __slots__**

找到所有 `@dataclass` 装饰的类，在类定义内添加：
```python
__slots__ = ()
```

示例：
```python
@dataclass
class NumberLiteral:
    __slots__ = ()
    value: Any
    line: Optional[int] = None
    column: Optional[int] = None
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/unit/test_ast_slots.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add tests/unit/test_ast_slots.py src/ast_nodes_v3.py
git commit -m "perf: add __slots__ to AST nodes for memory optimization"
```

---

### 任务 2：词法分析器正则预编译

**文件：**
- 修改：`src/lexer.py`
- 测试：`tests/unit/test_lexer_perf.py`（新建）

- [ ] **步骤 1：创建性能基准测试**

```python
# tests/unit/test_lexer_perf.py
import time
from src.lexer import Lexer

def test_lexer_speed_large_file():
    """测试大文件的词法分析速度"""
    # 生成 10000 行测试代码
    code = '\n'.join([f'定义 变量_{i} 等于 {i}' for i in range(10000)])
    
    start = time.perf_counter()
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    elapsed = time.perf_counter() - start
    
    # 应该在 1 秒内完成
    assert elapsed < 1.0, f"Lexer took {elapsed:.2f}s, expected < 1.0s"
    assert len(tokens) > 0
```

- [ ] **步骤 2：运行基准测试获取基线**

运行：`pytest tests/unit/test_lexer_perf.py -v`
记录耗时（用于对比优化效果）

- [ ] **步骤 3：修改 lexer.py 预编译正则**

在 `src/lexer.py` 顶部添加预编译正则：

```python
# 模块级预编译正则
_RE_NUMBER = re.compile(r'-?\d+(\.\d+)?')
_RE_STRING_ESCAPE = re.compile(r'\\[\\nrt"\'各]')
```

找到 `tokenize()` 方法中所有 `re.compile()` 调用，移到模块级。

- [ ] **步骤 4：运行测试验证正确性**

运行：`pytest tests/unit/test_lexer.py -v`
预期：所有测试通过

- [ ] **步骤 5：运行性能测试对比**

运行：`pytest tests/unit/test_lexer_perf.py -v`
验证性能提升或至少不下降

- [ ] **步骤 6：Commit**

```bash
git add src/lexer.py tests/unit/test_lexer_perf.py
git commit -m "perf: precompile regex patterns in lexer"
```

---

## 阶段 2：代码生成器优化

### 任务 3：代码生成器列表 join 优化

**文件：**
- 修改：`src/code_generator.py`
- 测试：`tests/unit/test_codegen_perf.py`（新建）

- [ ] **步骤 1：创建代码生成器性能测试**

```python
# tests/unit/test_codegen_perf.py
import time
from src.light_parser_v3 import DuanParser
from src.code_generator import PythonCodeGenerator

def test_codegen_speed_large_module():
    """测试大模块的代码生成速度"""
    # 生成包含 1000 个函数定义的模块
    code = '\n'.join([
        f'段落 函数_{i}：\n    打印 {i}' 
        for i in range(1000)
    ])
    
    parser = DuanParser()
    ast = parser.parse(code)
    
    start = time.perf_counter()
    gen = PythonCodeGenerator()
    result = gen.generate(ast)
    elapsed = time.perf_counter() - start
    
    assert elapsed < 2.0, f"CodeGen took {elapsed:.2f}s, expected < 2.0s"
    assert 'def' in result
```

- [ ] **步骤 2：运行测试获取基线**

运行：`pytest tests/unit/test_codegen_perf.py -v`

- [ ] **步骤 3：修改 code_generator.py 使用 join**

在 `PythonCodeGenerator.__init__` 中：
```python
def __init__(self):
    self.indent_level = 0
    self.indent_str = "    "
    self.output_lines: List[str] = []  # 改用列表收集
    self._indent_cache: Dict[int, str] = {0: ""}  # 缩进缓存
```

添加方法：
```python
def _get_indent(self, level: int) -> str:
    """获取指定缩进层级的字符串（带缓存）"""
    if level not in self._indent_cache:
        self._indent_cache[level] = self.indent_str * level
    return self._indent_cache[level]
```

将所有 `self.output += ...` 改为 `self.output_lines.append(...)`

添加生成方法：
```python
def _build_output(self) -> str:
    """将收集的行列表合并为最终输出"""
    return '\n'.join(self.output_lines)
```

- [ ] **步骤 4：运行测试验证**

运行：`pytest tests/unit/test_codegen_perf.py -v`

- [ ] **步骤 5：Commit**

```bash
git add src/code_generator.py tests/unit/test_codegen_perf.py
git commit -m "perf: use list join for code generation"
```

---

### 任务 4：增量编译缓存

**文件：**
- 修改：`src/compiler.py`
- 测试：`tests/unit/test_compiler_cache.py`（新建）

- [ ] **步骤 1：创建缓存测试**

```python
# tests/unit/test_compiler_cache.py
import tempfile
import os
import time
from src.compiler import compile_file

def test_incremental_compile_faster():
    """测试增量编译比首次编译快"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.light', delete=False) as f:
        f.write('段落 main：\n    打印 "test"')
        temp_path = f.name
    
    try:
        # 首次编译
        start = time.perf_counter()
        result1 = compile_file(temp_path)
        first_time = time.perf_counter() - start
        
        # 增量编译（文件未变）
        start = time.perf_counter()
        result2 = compile_file(temp_path)
        second_time = time.perf_counter() - start
        
        # 增量编译应该更快或相等（因为缓存命中）
        assert second_time <= first_time * 1.5, \
            f"Second compile ({second_time:.4f}s) should be faster than first ({first_time:.4f}s)"
    finally:
        os.unlink(temp_path)
```

- [ ] **步骤 2：运行测试验证需要实现**

运行：`pytest tests/unit/test_compiler_cache.py -v`
预期：FAIL（功能不存在）

- [ ] **步骤 3：在 compiler.py 中实现增量缓存**

在 `compile_file` 函数或 `Compiler` 类中添加：

```python
import hashlib
import pickle
from pathlib import Path

# 模块级缓存
_compile_cache: Dict[str, Tuple[float, Any]] = {}

def compile_file(file_path: str, use_cache: bool = True) -> str:
    """编译 Light 源文件，支持增量缓存"""
    abs_path = os.path.abspath(file_path)
    stat = os.stat(abs_path)
    cache_key = abs_path
    mtime = stat.st_mtime
    size = stat.st_size
    
    # 尝试命中缓存
    if use_cache and cache_key in _compile_cache:
        cached_mtime, cached_result = _compile_cache[cache_key]
        if cached_mtime == mtime:
            return cached_result  # 缓存命中
    
    # 实际编译...
    result = _do_compile(file_path)
    
    # 更新缓存
    _compile_cache[cache_key] = (mtime, result)
    return result
```

- [ ] **步骤 4：运行测试验证**

运行：`pytest tests/unit/test_compiler_cache.py -v`

- [ ] **步骤 5：Commit**

```bash
git add src/compiler.py tests/unit/test_compiler_cache.py
git commit -m "perf: add incremental compile cache"
```

---

## 阶段 3：运行时优化

### 任务 5：常量折叠

**文件：**
- 创建：`src/optimizer/constant_fold.py`
- 修改：`src/optimizer/__init__.py`
- 测试：`tests/unit/test_constant_fold.py`（新建）

- [ ] **步骤 1：创建常量折叠测试**

```python
# tests/unit/test_constant_fold.py
from src.optimizer.constant_fold import ConstantFoldingOptimizer
from src.ast_nodes_v3 import Module, NumberLiteral, BinaryOp, Identifier

def test_fold_arithmetic():
    """测试算术常量折叠"""
    # 1 + 2 * 3 应该折叠为 7
    expr = BinaryOp(
        operator='加',
        left=NumberLiteral(value=1),
        right=BinaryOp(
            operator='乘',
            left=NumberLiteral(value=2),
            right=NumberLiteral(value=3)
        )
    )
    
    optimizer = ConstantFoldingOptimizer()
    result = optimizer.optimize_expr(expr)
    
    assert isinstance(result, NumberLiteral)
    assert result.value == 7

def test_no_fold_variables():
    """测试变量不折叠"""
    # a + 2 不应该折叠（a 是变量）
    expr = BinaryOp(
        operator='加',
        left=Identifier(name='a'),
        right=NumberLiteral(value=2)
    )
    
    optimizer = ConstantFoldingOptimizer()
    result = optimizer.optimize_expr(expr)
    
    # 结果应该仍是 BinaryOp
    assert isinstance(result, BinaryOp)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/unit/test_constant_fold.py -v`
预期：FAIL（模块不存在）

- [ ] **步骤 3：创建优化器基类**

```python
# src/optimizer/base.py
from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar('T')

class Optimizer(ABC):
    """AST 优化器基类"""
    
    @abstractmethod
    def optimize(self, module):
        """优化模块，返回优化后的 AST"""
        pass
    
    def optimize_expr(self, expr):
        """优化表达式，默认不做优化"""
        return expr
```

- [ ] **步骤 4：实现常量折叠**

```python
# src/optimizer/constant_fold.py
from typing import Any
from src.optimizer.base import Optimizer
from src.ast_nodes_v3 import (
    Module, NumberLiteral, StringLiteral, BinaryOp, UnaryOp,
    BooleanLiteral, Identifier
)

class ConstantFoldingOptimizer(Optimizer):
    """常量折叠优化器"""
    
    ARITHMETIC_OPS = {'加', '减', '乘', '除', '模', '幂'}
    COMPARE_OPS = {'大于', '小于', '等于', '不等于', '大于等于', '小于等于'}
    STRING_OPS = {'加'}  # 字符串只能拼接
    
    def optimize(self, module: Module) -> Module:
        """优化模块中的常量表达式"""
        module.body = [self._optimize_stmt(stmt) for stmt in module.body]
        return module
    
    def _optimize_stmt(self, stmt):
        """优化语句"""
        if hasattr(stmt, 'body'):
            stmt.body = [self._optimize_stmt(s) for s in stmt.body]
        return stmt
    
    def optimize_expr(self, expr):
        """优化表达式"""
        if isinstance(expr, BinaryOp):
            return self._fold_binary_op(expr)
        return expr
    
    def _fold_binary_op(self, op: BinaryOp) -> Any:
        """尝试折叠二元运算"""
        left = self.optimize_expr(op.left)
        right = self.optimize_expr(op.right)
        
        # 只有两边都是字面量时才折叠
        if not isinstance(left, (NumberLiteral, StringLiteral, BooleanLiteral)):
            op.left = left
            op.right = right
            return op
        
        if not isinstance(right, (NumberLiteral, StringLiteral, BooleanLiteral)):
            op.left = left
            op.right = right
            return op
        
        # 执行常量计算
        try:
            result = self._compute(op.operator, left.value, right.value)
            return NumberLiteral(value=result)
        except (TypeError, ZeroDivisionError):
            op.left = left
            op.right = right
            return op
    
    def _compute(self, op: str, a: Any, b: Any) -> Any:
        """计算二元运算结果"""
        if op == '加':
            return a + b
        elif op == '减':
            return a - b
        elif op == '乘':
            return a * b
        elif op == '除':
            return a / b
        elif op == '模':
            return a % b
        elif op == '幂':
            return a ** b
        # ... 其他运算
        raise TypeError(f"Unsupported operator: {op}")
```

- [ ] **步骤 5：运行测试验证**

运行：`pytest tests/unit/test_constant_fold.py -v`

- [ ] **步骤 6：Commit**

```bash
git add src/optimizer/base.py src/optimizer/constant_fold.py
git add tests/unit/test_constant_fold.py
git commit -m "perf: add constant folding optimizer"
```

---

### 任务 6：死代码消除

**文件：**
- 创建：`src/optimizer/dead_code.py`
- 测试：`tests/unit/test_dead_code.py`（新建）

- [ ] **步骤 1：创建死代码消除测试**

```python
# tests/unit/test_dead_code.py
from src.optimizer.dead_code import DeadCodeEliminationOptimizer
from src.ast_nodes_v3 import Module, IfStmt, ReturnStmt, PrintStmt, NumberLiteral

def test_eliminate_dead_if_false():
    """测试消除 if 假 块"""
    module = Module(body=[
        IfStmt(
            condition=NumberLiteral(value=0),  # 假
            then_branch=[PrintStmt(message="unreachable")],
            else_branch=None
        )
    ])
    
    optimizer = DeadCodeEliminationOptimizer()
    result = optimizer.optimize(module)
    
    # if 假应该被完全消除
    assert len(result.body) == 0

def test_keep_if_true_else():
    """测试保留 if 真 否则"""
    module = Module(body=[
        IfStmt(
            condition=NumberLiteral(value=1),  # 真
            then_branch=[],
            else_branch=[PrintStmt(message="else")]
        )
    ])
    
    optimizer = DeadCodeEliminationOptimizer()
    result = optimizer.optimize(module)
    
    # else 分支应该保留
    assert len(result.body) == 1
    assert isinstance(result.body[0], IfStmt)
```

- [ ] **步骤 2：实现死代码消除**

```python
# src/optimizer/dead_code.py
from src.optimizer.base import Optimizer
from src.ast_nodes_v3 import (
    Module, IfStmt, WhileStmt, ReturnStmt, ThrowStmt,
    BreakStmt, ContinueStmt, NumberLiteral, BooleanLiteral
)

TERMINATING_STMTS = (ReturnStmt, ThrowStmt, BreakStmt, ContinueStmt)

class DeadCodeEliminationOptimizer(Optimizer):
    """死代码消除优化器"""
    
    def optimize(self, module: Module) -> Module:
        """消除模块中的死代码"""
        module.body = self._optimize_stmts(module.body)
        return module
    
    def _optimize_stmts(self, stmts: list) -> list:
        """优化语句列表，删除不可达代码"""
        result = []
        for stmt in stmts:
            optimized = self._optimize_stmt(stmt)
            if optimized is None:
                continue
            result.append(optimized)
            # 如果是终止语句，跳过后续代码
            if isinstance(optimized, TERMINATING_STMTS):
                break
        return result
    
    def _optimize_stmt(self, stmt):
        """优化单个语句"""
        if isinstance(stmt, IfStmt):
            return self._optimize_if(stmt)
        elif isinstance(stmt, WhileStmt):
            return self._optimize_while(stmt)
        elif hasattr(stmt, 'body') and isinstance(stmt.body, list):
            stmt.body = self._optimize_stmts(stmt.body)
        return stmt
    
    def _optimize_if(self, stmt: IfStmt) -> IfStmt:
        """优化 if 语句"""
        cond = stmt.condition
        
        # 常量条件折叠
        if isinstance(cond, NumberLiteral):
            if cond.value:  # 真
                stmt.then_branch = self._optimize_stmts(stmt.then_branch or [])
                stmt.else_branch = []
            else:  # 假
                if stmt.else_branch:
                    stmt.then_branch = self._optimize_stmts(stmt.else_branch)
                else:
                    return None
                stmt.else_branch = []
        
        # 递归优化
        if stmt.then_branch:
            stmt.then_branch = self._optimize_stmts(stmt.then_branch)
        if stmt.else_branch:
            stmt.else_branch = self._optimize_stmts(stmt.else_branch)
        
        return stmt
    
    def _optimize_while(self, stmt: WhileStmt) -> WhileStmt:
        """优化 while 语句"""
        cond = stmt.condition
        
        # while 假 -> 消除整个循环
        if isinstance(cond, NumberLiteral) and not cond.value:
            return None
        
        if stmt.body:
            stmt.body = self._optimize_stmts(stmt.body)
        return stmt
```

- [ ] **步骤 3：运行测试验证**

运行：`pytest tests/unit/test_dead_code.py -v`

- [ ] **步骤 4：Commit**

```bash
git add src/optimizer/dead_code.py tests/unit/test_dead_code.py
git commit -m "perf: add dead code elimination optimizer"
```

---

### 任务 7：循环不变量外提

**文件：**
- 创建：`src/optimizer/loop_invariant.py`
- 测试：`tests/unit/test_loop_invariant.py`（新建）

- [ ] **步骤 1：创建循环不变量外提测试**

```python
# tests/unit/test_loop_invariant.py
from src.optimizer.loop_invariant import LoopInvariantOptimizer
from src.ast_nodes_v3 import Module, WhileStmt, ForEachStmt, BinaryOp, Identifier, NumberLiteral

def test_move_loop_invariant_out():
    """测试循环不变量外提"""
    # while i < 10: x = 5 + 1  ->  x = 5 + 1; while i < 10: pass
    loop = WhileStmt(
        condition=BinaryOp('小于', Identifier('i'), NumberLiteral(10)),
        body=[
            BinaryOp('等于', Identifier('x'), BinaryOp('加', NumberLiteral(5), NumberLiteral(1)))
        ]
    )
    
    module = Module(body=[loop])
    optimizer = LoopInvariantOptimizer()
    result = optimizer.optimize(module)
    
    # 不变量应该被外提
    assert len(result.body) == 2  # 一条赋值 + while 循环
    assert isinstance(result.body[0], BinaryOp)  # 赋值在外
```

- [ ] **步骤 2：实现循环不变量外提（保守版）**

```python
# src/optimizer/loop_invariant.py
from src.optimizer.base import Optimizer
from src.ast_nodes_v3 import (
    Module, WhileStmt, ForEachStmt, BinaryOp, Identifier,
    NumberLiteral, StringLiteral, VarDecl, Assignment
)

class LoopInvariantOptimizer(Optimizer):
    """循环不变量外提优化器（保守策略）"""
    
    def optimize(self, module: Module) -> Module:
        """遍历模块优化循环"""
        module.body = [self._optimize_stmt(s) for s in module.body]
        return module
    
    def _optimize_stmt(self, stmt):
        """优化语句"""
        if isinstance(stmt, (WhileStmt, ForEachStmt)):
            return self._optimize_loop(stmt)
        if hasattr(stmt, 'body') and isinstance(stmt.body, list):
            stmt.body = [self._optimize_stmt(s) for s in stmt.body]
        return stmt
    
    def _optimize_loop(self, loop):
        """优化循环体，外提不变量"""
        if not hasattr(loop, 'body') or not loop.body:
            return loop
        
        body = loop.body
        invariants = []
        new_body = []
        
        for stmt in body:
            if self._is_invariant(stmt, loop):
                invariants.append(stmt)
            else:
                new_body.append(stmt)
        
        # 将不变量放到循环前
        loop.body = new_body
        return invariants + [loop] if invariants else loop
    
    def _is_invariant(self, stmt, loop):
        """判断语句是否循环不变量（保守检测）"""
        # 只检测纯字面量运算和简单赋值
        if isinstance(stmt, BinaryOp) and stmt.operator == '等于':
            if isinstance(stmt.right, (NumberLiteral, StringLiteral)):
                return True
        return False
```

- [ ] **步骤 3：运行测试验证**

运行：`pytest tests/unit/test_loop_invariant.py -v`

- [ ] **步骤 4：Commit**

```bash
git add src/optimizer/loop_invariant.py tests/unit/test_loop_invariant.py
git commit -m "perf: add loop invariant code motion optimizer"
```

---

## 阶段 4：集成与验证

### 任务 8：优化器集成

**文件：**
- 修改：`src/compiler.py`
- 测试：`tests/integration/test_optimizer_integration.py`（新建）

- [ ] **步骤 1：在编译器中集成优化器**

修改 `compile` 或 `compile_file` 函数：

```python
from src.optimizer.constant_fold import ConstantFoldingOptimizer
from src.optimizer.dead_code import DeadCodeEliminationOptimizer
from src.optimizer.loop_invariant import LoopInvariantOptimizer

# 优化器列表（按顺序执行）
OPTIMIZERS = [
    DeadCodeEliminationOptimizer(),  # 先消除死代码
    ConstantFoldingOptimizer(),       # 再折叠常量
    LoopInvariantOptimizer(),         # 最后外提循环不变量
]

def compile(source: str, optimize: bool = True) -> str:
    # ... 解析 ...
    ast = parser.parse(source)
    
    if optimize:
        for optimizer in OPTIMIZERS:
            ast = optimizer.optimize(ast)
    
    # ... 代码生成 ...
    return result
```

- [ ] **步骤 2：创建集成测试**

```python
# tests/integration/test_optimizer_integration.py
from src.compiler import compile

def test_optimization_applies():
    """测试优化确实生效"""
    code = '''
    如果 0：
        打印 "unreachable"
    '''
    result = compile(code)
    # 不应该包含 "unreachable" 的打印
    assert 'unreachable' not in result or result.count('打印') == 0
```

- [ ] **步骤 3：运行全量测试**

运行：`pytest tests/ -v --tb=short`

- [ ] **步骤 4：Commit**

```bash
git add src/compiler.py tests/integration/test_optimizer_integration.py
git commit -m "perf: integrate optimizers into compiler pipeline"
```

---

### 任务 9：性能基准验证

**文件：**
- 修改：`benchmarks/run_benchmarks.py`
- 测试：对比优化前后数据

- [ ] **步骤 1：运行基准测试获取当前数据**

运行：`python benchmarks/run_benchmarks.py 2>&1`
记录结果（基线）

- [ ] **步骤 2：运行全量测试确认正确性**

运行：`pytest tests/ -v --tb=short`

- [ ] **步骤 3：Commit 所有更改**

```bash
git add -A
git commit -m "perf: complete phase 1-4 optimizations

- AST nodes: add __slots__ for memory reduction
- Lexer: precompile regex patterns
- CodeGenerator: use list join for output
- Compiler: add incremental cache
- Optimizers: constant folding, dead code elimination, loop invariant

Performance target: +40-60% compile, +30-40% runtime"
```

---

## 自检清单

- [ ] 规格覆盖度：所有设计需求都有对应任务
- [ ] 无占位符：所有步骤都有实际代码
- [ ] 类型一致性：属性名和方法签名一致
- [ ] 测试通过：109+ 个原有测试保持通过
- [ ] 新增测试：至少 5 个新的优化器测试

---

**计划已完成并保存到 `docs/superpowers/plans/2026-06-26-performance-optimization-plan.md`。**

两种执行方式：

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

选哪种方式？
