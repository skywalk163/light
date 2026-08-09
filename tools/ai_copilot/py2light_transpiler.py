"""
Python → 光明 确定性转译器
将 Python AST 逐节点映射为光明 v3.2 源码

用法:
    python py2light_transpiler.py input.py > output.light
    echo 'print("hello")' | python py2light_transpiler.py

    from py2light_transpiler import Py2LightTranspiler
    t = Py2LightTranspiler()
    light_code = t.transpile(python_code)

改进（v4.0）:
    - 增强 for 循环处理（支持 for-else）
    - 增强列表推导式（支持条件过滤）
    - 增强字典操作（支持 dict.get, dict.items 等）
    - 增强异常处理（支持 try-else-finally）
    - 增强 walrus 操作符 (:=)
    - 增强 with 语句多上下文管理
"""
import ast


class TranspileError(Exception):
    """转译错误，包含行号信息"""
    def __init__(self, message, lineno=None):
        self.lineno = lineno
        loc = f" (行 {lineno})" if lineno is not None else ""
        super().__init__(f"{message}{loc}")


# === 映射表 ===

BINOP_MAP = {
    ast.Add:      "加上",
    ast.Sub:      "减去",
    ast.Mult:     "乘以",
    ast.Div:      "除以",
    ast.FloorDiv: "整除",
    ast.Mod:      "取余",
    ast.Pow:      "幂",
    ast.LShift:   "<<",
    ast.RShift:   ">>",
    ast.BitOr:    "|",
    ast.BitAnd:   "&",
    ast.BitXor:   "^",
    ast.MatMult:  "@",
}

AUGOP_MAP = {
    ast.Add:      ("加上", "加"),
    ast.Sub:      ("减去", "减"),
    ast.Mult:     ("乘以", "乘"),
    ast.Div:      ("除以", "除"),
    ast.FloorDiv: ("整除", "整除"),
    ast.Mod:      ("取余", "模"),
    ast.Pow:      ("幂",   "幂"),
    ast.LShift:   ("<<",   "<<"),
    ast.RShift:   (">>",   ">>"),
    ast.BitOr:    ("|",    "|"),
    ast.BitAnd:   ("&",    "&"),
    ast.BitXor:   ("^",    "^"),
    ast.MatMult:  ("@",    "@"),
}

COMPARE_MAP = {
    ast.Eq:    "等于",
    ast.NotEq: "不等于",
    ast.Gt:    "大于",
    ast.Lt:    "小于",
    ast.GtE:   "大于等于",
    ast.LtE:   "小于等于",
    ast.In:    "在",
    ast.NotIn: "不 在",
    ast.Is:    "是",
    ast.IsNot: "不 是",
}

BUILTIN_FUNC_MAP = {
    'print':     '打印',
    'input':     '读取',
    'zip':       '打包',
    'filter':    '筛选',
    'map':       '映射',
    'sorted':    '排序',
    'reversed':  '反转',
    'sum':       '求和',
    'int':       '整数',
    'float':     '浮数',
    'str':       '串',
    'bool':      '布尔',
    'list':      '列',
    'dict':      '典',
    'set':       '集',
    'type':      '类型',
    'abs':       '绝对值',
    'round':     '四舍五入',
    'min':       '最小',
    'max':       '最大',
    'any':       '任一',
    'all':       '所有',
    'isinstance': '实例检查',
    'range':     'range',
    'len':       'len',
    'open':      'open',
    'enumerate': 'enumerate',
    'ord':       'ord',       # 保留原名
    'chr':       'chr',       # 保留原名
    'hex':       'hex',       # 保留原名
    'bin':       'bin',       # 保留原名
    'oct':       'oct',       # 保留原名
    'repr':      'repr',      # 保留原名
    'format':    'format',    # 保留原名
    'bytes':     '字节',      # 新增
    'bytearray': '字节数组',  # 新增
    'memoryview':'内存视图',  # 新增
    'iter':      '迭代器',    # 新增
    'next':      '下一个',    # 新增
    'slice':     '切片',      # 新增
    'super':     '父',        # 新增
    'object':    '对象',      # 新增
    'property':  '特性',      # 新增
    'staticmethod':'静态方法',# 新增
    'classmethod':'类方法',   # 新增
    'hasattr':   '有属性',    # 新增
    'getattr':   '获取属性',  # 新增
    'setattr':   '设置属性',  # 新增
    'delattr':   '删除属性',  # 新增
    'callable':  '可调用',    # 新增
    'dir':       '目录',      # 新增
    'vars':      '变量',      # 新增
    'id':        '标识',      # 新增
}

NAME_MAP = {
    'self':  '己',
    'super': '父',
    'True':  '真',
    'False': '假',
    'None':  '空',
}


# === 运算符优先级（用于判断是否需要括号） ===
BINOP_PRECEDENCE = {
    ast.Pow: 7,
    ast.Mult: 6, ast.Div: 6, ast.FloorDiv: 6, ast.Mod: 6, ast.MatMult: 6,
    ast.Add: 5, ast.Sub: 5,
    ast.LShift: 4, ast.RShift: 4,
    ast.BitAnd: 3,
    ast.BitXor: 2,
    ast.BitOr: 1,
}


class Py2LightTranspiler:
    """Python → 光明 确定性转译器"""

    def __init__(self):
        self.indent_level = 0
        self.output_lines = []

    # ==================== 主入口 ====================

    def transpile(self, python_code: str) -> str:
        """将 Python 源码转译为光明源码"""
        tree = ast.parse(python_code)
        self.output_lines = []
        self.indent_level = 0
        self._prev_node_type = None

        BLOCK_STMT_TYPES = (
            ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
            ast.For, ast.AsyncFor, ast.While, ast.If, ast.With, ast.AsyncWith,
            ast.Try, ast.Match,
        )

        for node in tree.body:
            # 顶级块语句之间加空行
            if self._prev_node_type is not None:
                prev_is_block = self._prev_node_type in BLOCK_STMT_TYPES
                curr_is_block = type(node) in BLOCK_STMT_TYPES
                if prev_is_block or curr_is_block:
                    self.output_lines.append("")
            self._visit_stmt(node)
            self._prev_node_type = type(node)

        return "\n".join(self.output_lines)

    # ==================== 工具方法 ====================

    def _emit(self, line: str):
        """输出一行（带缩进）"""
        indent = "    " * self.indent_level
        self.output_lines.append(f"{indent}{line}")

    def _get_lineno(self, node):
        """获取节点行号"""
        return getattr(node, 'lineno', None)

    def _format_str(self, s: str) -> str:
        """格式化字符串，使用双引号"""
        inner = s.replace('\\', '\\\\').replace('"', '\\"')
        result = []
        for ch in inner:
            if ch == '\n':
                result.append('\\n')
            elif ch == '\t':
                result.append('\\t')
            elif ch == '\r':
                result.append('\\r')
            else:
                result.append(ch)
        return '"' + ''.join(result) + '"'

    def _format_target(self, node) -> str:
        """格式化赋值目标，处理元组解包"""
        if isinstance(node, ast.Tuple):
            return ", ".join(self._visit_expr(e) for e in node.elts)
        return self._visit_expr(node)

    def _needs_parens(self, child, parent_op) -> bool:
        """判断子表达式是否需要括号（子表达式优先级低于父运算符时）"""
        if not isinstance(child, ast.BinOp):
            return False
        child_prec = BINOP_PRECEDENCE.get(type(child.op), 0)
        parent_prec = BINOP_PRECEDENCE.get(type(parent_op), 0)
        return child_prec < parent_prec

    # ==================== 语句分派 ====================

    def _visit_stmt(self, node):
        """分派语句节点到对应的处理方法"""
        handler_name = f"_visit_{type(node).__name__}"
        handler = getattr(self, handler_name, None)
        if handler:
            handler(node)
        elif isinstance(node, ast.stmt):
            # 不支持的语句节点：输出注释
            self._emit(f"# [转译器不支持: {type(node).__name__}]")

    # ==================== 表达式分派 ====================

    def _visit_expr(self, node) -> str:
        """分派表达式节点到对应的处理方法，返回字符串"""
        if node is None:
            return "空"
        handler_name = f"_visit_{type(node).__name__}"
        handler = getattr(self, handler_name, None)
        if handler:
            return handler(node)
        else:
            raise TranspileError(
                f"不支持的表达式类型: {type(node).__name__}",
                self._get_lineno(node)
            )

    # ==================== 语句层 ====================

    def _visit_Module(self, node: ast.Module):
        for stmt in node.body:
            self._visit_stmt(stmt)

    def _visit_FunctionDef(self, node: ast.FunctionDef, is_method=False, prefix=""):
        # 装饰器处理
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                if dec.id == 'staticmethod':
                    prefix = "静态 " + prefix
                elif dec.id == 'classmethod':
                    prefix = "类方法 " + prefix
                elif dec.id == 'property':
                    prefix = "特性 " + prefix
                else:
                    self._emit(f"{prefix}标注 {dec.id}")
                    prefix = ""
            elif isinstance(dec, ast.Attribute):
                self._emit(f"{prefix}标注 {self._visit_expr(dec)}")
                prefix = ""
            elif isinstance(dec, ast.Call):
                self._emit(f"{prefix}标注 {self._visit_expr(dec)}")
                prefix = ""
            else:
                self._emit(f"{prefix}标注 {self._visit_expr(dec)}")
                prefix = ""

        name = node.name
        params = self._format_params(node.args, is_method)

        if params:
            self._emit(f"{prefix}函数 {name} 接收 {params}：")
        else:
            self._emit(f"{prefix}函数 {name}：")

        self.indent_level += 1
        for stmt in node.body:
            self._visit_stmt(stmt)
        self.indent_level -= 1

    def _visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_FunctionDef(node, prefix="异步 ")

    def _visit_ClassDef(self, node: ast.ClassDef):
        if node.bases:
            base_names = ", ".join(self._visit_expr(b) for b in node.bases)
            self._emit(f"类 {node.name} 继承 {base_names}：")
        else:
            self._emit(f"类 {node.name}：")

        self.indent_level += 1
        for stmt in node.body:
            # 类属性赋值
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                if isinstance(stmt.targets[0], ast.Name):
                    attr_name = stmt.targets[0].id
                    value_str = self._visit_expr(stmt.value)
                    self._emit(f"属性 {attr_name} 等于 {value_str}")
                    continue

            # __init__ → 构造
            if isinstance(stmt, ast.FunctionDef) and stmt.name == '__init__':
                self._visit_constructor(stmt)
                continue

            # 普通方法
            if isinstance(stmt, ast.FunctionDef):
                self._visit_FunctionDef(stmt, is_method=True)
                continue

            if isinstance(stmt, ast.AsyncFunctionDef):
                self._visit_AsyncFunctionDef(stmt)
                continue

            # 其他语句
            self._visit_stmt(stmt)

        self.indent_level -= 1

    def _visit_constructor(self, node: ast.FunctionDef):
        """处理 __init__ 方法 → 构造"""
        params = self._format_params(node.args, is_method=True)
        self._emit(f"构造 接收 {params}：" if params else "构造 接收：")

        self.indent_level += 1
        for stmt in node.body:
            # self.attr = value → 己.attr 为 value
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
                if isinstance(target, ast.Attribute):
                    if isinstance(target.value, ast.Name) and target.value.id == 'self':
                        value_str = self._visit_expr(stmt.value)
                        self._emit(f"己.{target.attr} 为 {value_str}")
                        continue
            self._visit_stmt(stmt)
        self.indent_level -= 1

    def _visit_Assign(self, node: ast.Assign):
        value_str = self._visit_expr(node.value)

        if len(node.targets) == 1:
            target = node.targets[0]

            # 元组解包: a, b = 1, 2
            if isinstance(target, ast.Tuple):
                targets_str = ", ".join(self._visit_expr(e) for e in target.elts)
                if isinstance(node.value, ast.Tuple):
                    value_str = ", ".join(self._visit_expr(e) for e in node.value.elts)
                self._emit(f"设 {targets_str} 为 {value_str}")
                return

            # 纯字符串赋值 → 定义 X 等于 "..."
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                target_str = self._visit_expr(target)
                self._emit(f"定义 {target_str} 等于 {value_str}")
            else:
                target_str = self._visit_expr(target)
                self._emit(f"设 {target_str} 为 {value_str}")
        else:
            # 链式赋值: a = b = c = 0 → 每个变量分别赋值
            for target in node.targets:
                target_str = self._visit_expr(target)
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self._emit(f"定义 {target_str} 等于 {value_str}")
                else:
                    self._emit(f"设 {target_str} 为 {value_str}")

    def _visit_AugAssign(self, node: ast.AugAssign):
        target_str = self._visit_expr(node.target)
        value_str = self._visit_expr(node.value)
        op_pair = AUGOP_MAP.get(type(node.op))
        if op_pair:
            compound_word = op_pair[0]
            self._emit(f"设 {target_str} 为 {target_str} {compound_word} {value_str}")
        else:
            # 兜底：用 BinOp 表达式
            left = self._visit_expr(node.target)
            right = self._visit_expr(node.value)
            op_str = BINOP_MAP.get(type(node.op), str(type(node.op).__name__))
            self._emit(f"设 {target_str} 为 {left} {op_str} {right}")

    def _visit_AnnAssign(self, node: ast.AnnAssign):
        if node.value is not None:
            target_str = self._visit_expr(node.target)
            value_str = self._visit_expr(node.value)
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                self._emit(f"定义 {target_str} 等于 {value_str}")
            else:
                self._emit(f"设 {target_str} 为 {value_str}")
        else:
            target_str = self._visit_expr(node.target)
            self._emit(f"设 {target_str} 为 空")

    def _visit_If(self, node: ast.If, is_elif=False):
        test_str = self._visit_expr(node.test)

        if is_elif:
            self._emit(f"否则若 {test_str}：")
        else:
            self._emit(f"如果 {test_str}：")

        self.indent_level += 1
        for stmt in node.body:
            self._visit_stmt(stmt)
        self.indent_level -= 1

        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                self._visit_If(node.orelse[0], is_elif=True)
            else:
                self._emit("否则：")
                self.indent_level += 1
                for stmt in node.orelse:
                    self._visit_stmt(stmt)
                self.indent_level -= 1

    def _visit_For(self, node: ast.For, prefix=""):
        target_str = self._format_target(node.target)

        # range() 特殊处理
        if (isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == 'range'):

            args = node.iter.args
            if len(args) == 1:
                start = "0"
                end_expr = args[0]
                step = None
            elif len(args) == 2:
                start = self._visit_expr(args[0])
                end_expr = args[1]
                step = None
            else:
                start = self._visit_expr(args[0])
                end_expr = args[1]
                step = self._visit_expr(args[2])

            # range 上限减 1
            if isinstance(end_expr, ast.Constant) and isinstance(end_expr.value, int):
                end = str(end_expr.value - 1)
            else:
                end = self._visit_expr(end_expr) + "-1"

            range_expr = f"{start}至{end}"
            if step:
                range_expr += f" 步 {step}"

            self._emit(f"{prefix}遍历 {target_str} 于 {range_expr}：")
        else:
            iter_str = self._visit_expr(node.iter)
            self._emit(f"{prefix}遍历 {target_str} 之 {iter_str}：")

        self.indent_level += 1
        for stmt in node.body:
            self._visit_stmt(stmt)
        self.indent_level -= 1

        # for...else
        if node.orelse:
            self._emit("否则：")
            self.indent_level += 1
            for stmt in node.orelse:
                self._visit_stmt(stmt)
            self.indent_level -= 1

    def _visit_AsyncFor(self, node: ast.AsyncFor):
        self._visit_For(node, prefix="异步 ")

    def _visit_While(self, node: ast.While):
        test_str = self._visit_expr(node.test)
        self._emit(f"当 {test_str}：")
        self.indent_level += 1
        for stmt in node.body:
            self._visit_stmt(stmt)
        self.indent_level -= 1

        if node.orelse:
            self._emit("否则：")
            self.indent_level += 1
            for stmt in node.orelse:
                self._visit_stmt(stmt)
            self.indent_level -= 1

    def _visit_Return(self, node: ast.Return):
        if node.value:
            if isinstance(node.value, ast.Tuple):
                value_str = ", ".join(self._visit_expr(e) for e in node.value.elts)
            else:
                value_str = self._visit_expr(node.value)
            self._emit(f"返回 {value_str}")
        else:
            self._emit("返回")

    def _visit_Break(self, node: ast.Break):
        self._emit("跳出")

    def _visit_Continue(self, node: ast.Continue):
        self._emit("跳过")

    def _visit_Pass(self, node: ast.Pass):
        pass  # 不输出任何内容

    def _visit_With(self, node: ast.With, prefix=""):
        items = []
        for item in node.items:
            ctx_str = self._visit_expr(item.context_expr)
            if item.optional_vars:
                var_str = self._visit_expr(item.optional_vars)
                items.append(f"{ctx_str} 为 {var_str}")
            else:
                items.append(ctx_str)
        items_str = ", ".join(items)
        self._emit(f"{prefix}使用 {items_str}：")
        self.indent_level += 1
        for stmt in node.body:
            self._visit_stmt(stmt)
        self.indent_level -= 1

    def _visit_AsyncWith(self, node: ast.AsyncWith):
        self._visit_With(node, prefix="异步 ")

    def _visit_Try(self, node: ast.Try):
        self._emit("尝试：")
        self.indent_level += 1
        for stmt in node.body:
            self._visit_stmt(stmt)
        self.indent_level -= 1

        for handler in node.handlers:
            self._visit_ExceptHandler(handler)

        if node.orelse:
            self._emit("否则：")
            self.indent_level += 1
            for stmt in node.orelse:
                self._visit_stmt(stmt)
            self.indent_level -= 1

        if node.finalbody:
            self._emit("最终：")
            self.indent_level += 1
            for stmt in node.finalbody:
                self._visit_stmt(stmt)
            self.indent_level -= 1

    def _visit_ExceptHandler(self, handler: ast.ExceptHandler):
        if handler.type:
            type_str = self._visit_expr(handler.type)
            if handler.name:
                self._emit(f"捕获 {type_str} 为 {handler.name}：")
            else:
                self._emit(f"捕获 {type_str}：")
        else:
            self._emit("捕获：")

        self.indent_level += 1
        for stmt in handler.body:
            self._visit_stmt(stmt)
        self.indent_level -= 1

    def _visit_Raise(self, node: ast.Raise):
        if node.exc is None:
            self._emit("抛出")
        elif node.cause:
            exc_str = self._visit_expr(node.exc)
            cause_str = self._visit_expr(node.cause)
            self._emit(f"抛出 {exc_str} from {cause_str}")
        else:
            exc_str = self._visit_expr(node.exc)
            self._emit(f"抛出 {exc_str}")

    def _visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.asname:
                self._emit(f"导入 {alias.name} 为 {alias.asname}")
            else:
                self._emit(f"导入 {alias.name}")

    def _visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        names = []
        for alias in node.names:
            if alias.asname:
                names.append(f"{alias.name} 为 {alias.asname}")
            else:
                names.append(alias.name)
        names_str = ", ".join(names)
        self._emit(f"从 {module} 导入 {names_str}")

    def _visit_Match(self, node: ast.Match):
        subject_str = self._visit_expr(node.subject)
        self._emit(f"匹配 {subject_str}：")
        self.indent_level += 1
        for case in node.cases:
            self._visit_match_case(case)
        self.indent_level -= 1

    def _visit_match_case(self, case: ast.match_case):
        pattern_str = self._visit_pattern(case.pattern)
        if case.guard:
            guard_str = self._visit_expr(case.guard)
            self._emit(f"情况 {pattern_str} 若 {guard_str}：")
        else:
            self._emit(f"情况 {pattern_str}：")
        self.indent_level += 1
        for stmt in case.body:
            self._visit_stmt(stmt)
        self.indent_level -= 1

    def _visit_pattern(self, pattern) -> str:
        """处理 match-case 的模式"""
        if isinstance(pattern, ast.MatchValue):
            return self._visit_expr(pattern.value)
        elif isinstance(pattern, ast.MatchSingleton):
            return NAME_MAP.get(str(pattern.value), str(pattern.value))
        elif isinstance(pattern, ast.MatchAs):
            if pattern.pattern:
                inner = self._visit_pattern(pattern.pattern)
                return f"{inner} 为 {pattern.name}" if pattern.name else inner
            else:
                return pattern.name if pattern.name else "_"
        elif isinstance(pattern, ast.MatchOr):
            parts = [self._visit_pattern(p) for p in pattern.patterns]
            return " | ".join(parts)
        elif isinstance(pattern, ast.MatchSequence):
            parts = [self._visit_pattern(p) for p in pattern.patterns]
            return f"[{', '.join(parts)}]"
        elif isinstance(pattern, ast.MatchMapping):
            parts = []
            for k, v in zip(pattern.keys, pattern.patterns):
                k_str = self._visit_expr(k) if k else "_"
                parts.append(f"{k_str}: {self._visit_pattern(v)}")
            return f"{{{', '.join(parts)}}}"
        elif isinstance(pattern, ast.MatchClass):
            cls_str = self._visit_expr(pattern.cls)
            args = [self._visit_pattern(p) for p in pattern.patterns]
            return f"{cls_str}({', '.join(args)})"
        elif isinstance(pattern, ast.MatchStar):
            return f"*{pattern.name}" if pattern.name else "*_"
        else:
            return self._visit_expr(pattern) if hasattr(pattern, 'value') else "_"

    def _visit_Expr(self, node: ast.Expr):
        """表达式语句"""
        # Yield/YieldFrom/Await 在 _visit_Yield/_visit_YieldFrom/_visit_Await 中已 emit
        if isinstance(node.value, (ast.Yield, ast.YieldFrom)):
            self._visit_stmt(node.value)
            return
        # Docstring (独立字符串常量表达式) -> 转为注释，光明不支持独立字符串语句
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            docstring = node.value.value
            for line in docstring.split("\n"):
                self._emit(f"# {line}" if line.strip() else "#")
            return
        value_str = self._visit_expr(node.value)
        self._emit(value_str)

    def _visit_Global(self, node: ast.Global):
        names = ", ".join(node.names)
        self._emit(f"全局 {names}")

    def _visit_Nonlocal(self, node: ast.Nonlocal):
        names = ", ".join(node.names)
        self._emit(f"非局部 {names}")

    def _visit_Delete(self, node: ast.Delete):
        for target in node.targets:
            target_str = self._visit_expr(target)
            self._emit(f"删除 {target_str}")

    def _visit_Assert(self, node: ast.Assert):
        test_str = self._visit_expr(node.test)
        if node.msg:
            msg_str = self._visit_expr(node.msg)
            self._emit(f"断言 {test_str}, {msg_str}")
        else:
            self._emit(f"断言 {test_str}")

    def _visit_Yield(self, node: ast.Yield):
        if node.value:
            value_str = self._visit_expr(node.value)
            self._emit(f"产出 {value_str}")
        else:
            self._emit("产出")

    def _visit_YieldFrom(self, node: ast.YieldFrom):
        value_str = self._visit_expr(node.value)
        self._emit(f"产出 从 {value_str}")

    # ==================== 表达式层 ====================

    def _visit_BinOp(self, node: ast.BinOp) -> str:
        left = self._visit_expr(node.left)
        right = self._visit_expr(node.right)
        # 子表达式如果是低优先级运算，需要加括号
        if self._needs_parens(node.left, node.op):
            left = f"({left})"
        if self._needs_parens(node.right, node.op):
            right = f"({right})"
        op = BINOP_MAP.get(type(node.op), str(type(node.op).__name__))
        return f"{left} {op} {right}"

    def _visit_UnaryOp(self, node: ast.UnaryOp) -> str:
        operand = self._visit_expr(node.operand)
        if isinstance(node.op, ast.Not):
            # 非 运算符优先级较高，如果操作数是低优先级表达式需要加括号
            # 否则 "非 (x 且 y)" 会变成 "非 x 且 y" = "(非 x) 且 y"
            if isinstance(node.operand, (ast.BoolOp, ast.Compare, ast.IfExp)):
                operand = f"({operand})"
            return f"非 {operand}"
        elif isinstance(node.op, ast.USub):
            return f"-{operand}"
        elif isinstance(node.op, ast.UAdd):
            return f"+{operand}"
        elif isinstance(node.op, ast.Invert):
            return f"~{operand}"
        return operand

    def _visit_BoolOp(self, node: ast.BoolOp) -> str:
        op = "且" if isinstance(node.op, ast.And) else "或"
        parts = [self._visit_expr(v) for v in node.values]
        return f" {op} ".join(parts)

    def _visit_Compare(self, node: ast.Compare) -> str:
        left = self._visit_expr(node.left)
        parts = [left]
        for op, comp in zip(node.ops, node.comparators):
            op_str = COMPARE_MAP.get(type(op), "==")
            right = self._visit_expr(comp)
            parts.append(f"{op_str} {right}")
        return " ".join(parts)

    def _visit_Constant(self, node: ast.Constant) -> str:
        if node.value is True:
            return "真"
        elif node.value is False:
            return "假"
        elif node.value is None:
            return "空"
        elif isinstance(node.value, str):
            return self._format_str(node.value)
        elif isinstance(node.value, bytes):
            return self._format_str(node.value.decode('utf-8', errors='replace'))
        elif node.value is ...:
            return "..."
        else:
            return str(node.value)

    def _visit_Name(self, node: ast.Name) -> str:
        return NAME_MAP.get(node.id, node.id)

    def _visit_Attribute(self, node: ast.Attribute) -> str:
        value_str = self._visit_expr(node.value)
        return f"{value_str}.{node.attr}"

    def _visit_Subscript(self, node: ast.Subscript) -> str:
        value_str = self._visit_expr(node.value)
        slice_str = self._visit_slice(node.slice)
        return f"{value_str}[{slice_str}]"

    def _visit_slice(self, node) -> str:
        if isinstance(node, ast.Slice):
            parts = []
            if node.lower:
                parts.append(self._visit_expr(node.lower))
            else:
                parts.append("")
            if node.upper:
                parts.append(self._visit_expr(node.upper))
            else:
                parts.append("")
            if node.step:
                parts.append(self._visit_expr(node.step))
            return ":".join(parts)
        elif isinstance(node, ast.Tuple):
            return ", ".join(self._visit_expr(e) for e in node.elts)
        else:
            return self._visit_expr(node)

    def _visit_Call(self, node: ast.Call) -> str:
        # super() 特殊处理：返回 "父" 不带括号
        if isinstance(node.func, ast.Name) and node.func.id == 'super':
            return '父'

        func_str = self._visit_expr(node.func)

        # 内置函数翻译（仅当 func 是 Name 节点时，且优先保留 _visit_expr 的翻译结果）
        if isinstance(node.func, ast.Name):
            translated = BUILTIN_FUNC_MAP.get(node.func.id, func_str)
            func_str = translated

        args = []
        for arg in node.args:
            if isinstance(arg, ast.Starred):
                args.append(f"*{self._visit_expr(arg.value)}")
            else:
                args.append(self._visit_expr(arg))

        for kw in node.keywords:
            if kw.arg is None:
                args.append(f"**{self._visit_expr(kw.value)}")
            else:
                args.append(f"{kw.arg}={self._visit_expr(kw.value)}")

        args_str = ", ".join(args)
        return f"{func_str}({args_str})"

    def _visit_List(self, node: ast.List) -> str:
        elts = [self._visit_expr(e) for e in node.elts]
        return f"[{', '.join(elts)}]"

    def _visit_Dict(self, node: ast.Dict) -> str:
        pairs = []
        for k, v in zip(node.keys, node.values):
            if k is None:
                # **dict 展开语法：{**a, **b} → 保持原样
                v_str = self._visit_expr(v)
                pairs.append(f"**{v_str}")
            else:
                k_str = self._visit_expr(k)
                v_str = self._visit_expr(v)
                pairs.append(f"{k_str}: {v_str}")
        return f"{{{', '.join(pairs)}}}"

    def _visit_Set(self, node: ast.Set) -> str:
        elts = [self._visit_expr(e) for e in node.elts]
        return f"{{{', '.join(elts)}}}"

    def _visit_Tuple(self, node: ast.Tuple) -> str:
        elts = [self._visit_expr(e) for e in node.elts]
        if len(elts) == 1:
            return f"({elts[0]},)"
        return f"({', '.join(elts)})"

    def _visit_Lambda(self, node: ast.Lambda) -> str:
        params = self._format_params(node.args, is_method=False)
        body_str = self._visit_expr(node.body)
        if params:
            return f"接收 {params}：返回 {body_str}"
        else:
            return f"接收：返回 {body_str}"

    def _visit_IfExp(self, node: ast.IfExp) -> str:
        test_str = self._visit_expr(node.test)
        body_str = self._visit_expr(node.body)
        orelse_str = self._visit_expr(node.orelse)
        return f"{body_str} 如果 {test_str} 否则 {orelse_str}"

    def _visit_ListComp(self, node: ast.ListComp) -> str:
        elt_str = self._visit_expr(node.elt)
        gen_strs = []
        for gen in node.generators:
            target_str = self._format_target(gen.target)
            iter_str = self._visit_expr(gen.iter)
            gen_str = f"遍历 {target_str} 之 {iter_str}"
            for cond in gen.ifs:
                cond_str = self._visit_expr(cond)
                gen_str += f" 若 {cond_str}"
            gen_strs.append(gen_str)
        return f"[{elt_str} {' '.join(gen_strs)}]"

    def _visit_DictComp(self, node: ast.DictComp) -> str:
        key_str = self._visit_expr(node.key)
        value_str = self._visit_expr(node.value)
        gen_strs = []
        for gen in node.generators:
            target_str = self._format_target(gen.target)
            iter_str = self._visit_expr(gen.iter)
            gen_str = f"遍历 {target_str} 之 {iter_str}"
            for cond in gen.ifs:
                cond_str = self._visit_expr(cond)
                gen_str += f" 若 {cond_str}"
            gen_strs.append(gen_str)
        return f"{{{key_str}: {value_str} {' '.join(gen_strs)}}}"

    def _visit_SetComp(self, node: ast.SetComp) -> str:
        elt_str = self._visit_expr(node.elt)
        gen_strs = []
        for gen in node.generators:
            target_str = self._format_target(gen.target)
            iter_str = self._visit_expr(gen.iter)
            gen_str = f"遍历 {target_str} 之 {iter_str}"
            for cond in gen.ifs:
                cond_str = self._visit_expr(cond)
                gen_str += f" 若 {cond_str}"
            gen_strs.append(gen_str)
        return f"{{{elt_str} {' '.join(gen_strs)}}}"

    def _visit_JoinedStr(self, node: ast.JoinedStr) -> str:
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                inner = self._visit_expr(value.value)
                conversion = ""
                if value.conversion == 114:  # ord('r')
                    conversion = "!r"
                elif value.conversion == 115:  # ord('s')
                    conversion = "!s"
                elif value.conversion == 97:  # ord('a')
                    conversion = "!a"

                if value.format_spec:
                    spec_parts = []
                    for spec_val in value.format_spec.values:
                        if isinstance(spec_val, ast.Constant):
                            spec_parts.append(spec_val.value)
                        elif isinstance(spec_val, ast.FormattedValue):
                            spec_parts.append(f"{{{self._visit_expr(spec_val.value)}}}")
                    spec = "".join(spec_parts)
                    parts.append(f"{{{inner}{conversion}:{spec}}}")
                else:
                    parts.append(f"{{{inner}{conversion}}}")
        return f'f"{''.join(parts)}"'

    def _visit_Starred(self, node: ast.Starred) -> str:
        return f"*{self._visit_expr(node.value)}"

    def _visit_Await(self, node: ast.Await) -> str:
        return f"等待 {self._visit_expr(node.value)}"

    def _visit_NamedExpr(self, node: ast.NamedExpr) -> str:
        target_str = self._visit_expr(node.target)
        value_str = self._visit_expr(node.value)
        return f"({target_str} := {value_str})"

    def _visit_FormattedValue(self, node: ast.FormattedValue) -> str:
        return self._visit_expr(node.value)

    def _visit_Slice(self, node: ast.Slice) -> str:
        return self._visit_slice(node)

    # ==================== 参数格式化 ====================

    def _format_params(self, args: ast.arguments, is_method=False) -> str:
        """格式化函数参数列表"""
        parts = []

        # 普通参数
        all_args = list(args.posonlyargs) + list(args.args)

        # 跳过 self/cls
        start_idx = 0
        if is_method and all_args:
            if all_args[0].arg in ('self', 'cls'):
                start_idx = 1

        regular_args = all_args[start_idx:]
        for arg in regular_args:
            parts.append(arg.arg)

        # 默认值（对齐到 args.args 末尾）
        defaults = args.defaults
        num_defaults = len(defaults)
        num_regular = len(parts)
        if num_defaults > 0:
            for i in range(num_defaults):
                idx = num_regular - num_defaults + i
                if idx >= 0:
                    default_val = self._visit_expr(defaults[i])
                    parts[idx] = f"{parts[idx]} 等于 {default_val}"

        # *args
        if args.vararg:
            parts.append(f"*{args.vararg.arg}")

        # **kwargs
        if args.kwarg:
            parts.append(f"**{args.kwarg.arg}")

        return ", ".join(parts)


# === CLI 入口 ===
if __name__ == "__main__":
    import sys

    transpiler = Py2LightTranspiler()

    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            code = f.read()
    else:
        code = sys.stdin.read()

    try:
        result = transpiler.transpile(code)
        print(result)
    except TranspileError as e:
        print(f"转译错误: {e}", file=sys.stderr)
        sys.exit(1)