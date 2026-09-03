"""
光明（Light）编程语言 - Python代码生成器（统一AST版本）

支持统一AST格式，兼容来自light_ast和ast_unified的AST节点
集成类型推断系统，正确处理字符串连接和数字加法
"""

from typing import List, Optional, Dict
from dataclasses import dataclass, field

# 导入类型推断器
from type_inferencer import (
    TypeInferencer, StringType, NumberType, ListType, DictType,
    BooleanType, NullType, FunctionType, EnumType,
    OptionalTypeWrapper, GenericTypeInstance, FutureType,
)


# =============================================================================
# 工具函数
# =============================================================================

def is_instance(node, class_name):
    """检查节点是否为指定类型（通过名称检查，支持多个模块）"""
    if node is None:
        return False
    return type(node).__name__ == class_name


def get_attr(node, attr_name, default=None):
    """安全获取节点属性"""
    return getattr(node, attr_name, default)


# =============================================================================
# Python代码生成器
# =============================================================================

class UnifiedCodeGenerator:
    """光明到Python代码生成器（支持统一AST）"""
    
    def __init__(self, stdlib_dir: Optional[str] = None):
        self.indent_level = 0
        self.indent_str = "    "  # 4空格缩进
        self.output_lines: List[str] = []
        self._indent_cache: Dict[int, str] = {}
        # 编译期注入的 stdlib 绝对路径（修复产物找不到标准库/钩子的根因，见
        # src/code_generator.py 同名字段注释）。
        self._stdlib_dir = stdlib_dir
        self.type_inferencer = TypeInferencer()
        self.type_cache: Dict[int, 'Type'] = {}  # 存储推断的类型
        self.user_functions = set()  # 用户定义的函数名
        self._in_function = False  # 是否在函数/段落内部（控制 return 生成）
        self._in_class_method = False  # 是否在类方法/构造函数内部（控制 己→self 映射）
        self._needs_asyncio = False  # B5：是否需要 import asyncio
        self._needs_async_iter = False  # B5：是否需要 _light_async_iter 辅助
        
        # 运算符映射
        self.operator_map = {
            '+': '+',
            '-': '-',
            '*': '*',
            '/': '/',
            '%': '%',
            '^': '**',
            '>': '>',
            '<': '<',
            '==': '==',
            '!=': '!=',
            '>=': '>=',
            '<=': '<=',
            '加': '+',
            '减': '-',
            '乘': '*',
            '除': '//',
            '除以': '//',
            '模': '%',
            '幂': '**',
            '大于': '>',
            '小于': '<',
            '等于': '==',
            '不等于': '!=',
            '大于等于': '>=',
            '小于等于': '<=',
            '且': 'and',
            '或': 'or',
            '与': 'and',
        }
        
        # 内置函数映射
        self.builtin_map = {
            '印': 'print',
            '打印': 'print',
            '显示': 'print',
            # L-045：`写` 与 src 后端同口径（不换行写输出），并为输出拼接合并
            # 提供内置目标（_try_merge_output_concat 依赖此映射识别写族调用）。
            '写': '_light_builtin.写入输出',
            '读取': 'input',
            '输入': 'input',
            # 列表操作动词
            '长': 'len',
            '首': '__import__("operator").itemgetter(0)',
            '末': '__import__("operator").itemgetter(-1)',
            '余': '__import__("builtins").slice(1, None)',
            '排序': '_light_builtin.列表排序',
            '排序列表': '_light_builtin.排序列表',
            '反转': '_light_builtin.列表反转',
            '求和': 'sum',
            '求最大': 'max',
            '求最小': 'min',
            '去重': 'lambda x: list(dict.fromkeys(x))',
            '筛选': 'filter',
            '映射': 'map',
            # 文件操作动词
            '读取文件': '_light_builtin.读取文件',
            '写入文件': '_light_builtin.写入文件',
            '追加文件': '_light_builtin.追加文件',
            '文件存在': '_light_builtin.文件存在',
            '是文件': '_light_builtin.是文件',
            '目录存在': '_light_builtin.目录存在',
            '路径存在': '_light_builtin.路径存在',
            '创建目录': '_light_builtin.创建目录',
            '删除文件': '_light_builtin.删除文件',
            '删除目录': '_light_builtin.删除目录',
            '列出目录': '_light_builtin.列出目录',
            '列出文件': '_light_builtin.列出文件',
            '文件大小': '_light_builtin.文件大小',
            '绝对路径': '_light_builtin.绝对路径',
            '连接路径': '_light_builtin.连接路径',
            '目录名': '_light_builtin.目录名',
            '文件名': '_light_builtin.文件名',
            '扩展名': '_light_builtin.扩展名',
            # JSON 操作（模块方法调用）
            'JSON.序列化': '_light_builtin.JSON序列化',
            'JSON.解析': 'json.loads',
            'json.序列化': '_light_builtin.JSON序列化',
            'json.解析': 'json.loads',
            # 时间操作
            '时间戳': '_light_builtin.时间戳',
            '格式化时间': '_light_builtin.格式化时间',
            # 系统操作动词
            '环境变量': '_light_builtin.环境变量',
            '设置环境变量': '_light_builtin.设置环境变量',
            '参数列表': '_light_builtin.参数列表',
            '退出程序': '_light_builtin.退出程序',
            '当前目录': '_light_builtin.当前目录',
            '切换目录': '_light_builtin.切换目录',
            '执行命令': '_light_builtin.执行命令',
            # 字符串操作动词
            '整数': '_light_builtin.整数',
            '转整数': '_light_builtin.转整数',
            '转浮点': '_light_builtin.转浮点',
            '转字符串': '_light_builtin.转字符串',
            # L-044：类型转内置以变量/索引为实参时曾漏出裸名（name '文本' is not
            # defined）；与 src 后端同表，统一生成 str() 内置调用。
            '文本': 'str',
            '字符串': 'str',
            '字符串长度': '_light_builtin.字符串长度',
            '显示宽度': '_light_builtin.显示宽度',
            '分割字符串': '_light_builtin.分割字符串',
            '连接字符串': '_light_builtin.连接字符串',
            '替换字符串': '_light_builtin.替换字符串',
            '去除空白': '_light_builtin.去除空白',
            # 列表操作（备用）
            '列表长度': '_light_builtin.列表长度',
            '列表获取': '_light_builtin.列表获取',
            '列表追加': '_light_builtin.列表追加',
            '列表弹出': '_light_builtin.列表弹出',
            '列表插入': '_light_builtin.列表插入',
            '列表排序': '_light_builtin.列表排序',
            '列表反转': '_light_builtin.列表反转',
            '列表包含': '_light_builtin.列表包含',
            '列表创建': '_light_builtin.列表创建',
            '副本': '_light_builtin.副本',
            '字典创建': '_light_builtin.字典创建',
            '字典设置': '_light_builtin.字典设置',
            '字典删除': '_light_builtin.字典删除',
            '字典键列表': '_light_builtin.字典键列表',
            '字典值列表': '_light_builtin.字典值列表',
            '字典项列表': '_light_builtin.字典项列表',
            '字典包含键': '_light_builtin.字典包含键',
            '字典获取': '_light_builtin.字典获取',
            '是整数': '_light_builtin.是整数',
            '是浮点': '_light_builtin.是浮点',
            '是字符串': '_light_builtin.是字符串',
            '是列表': '_light_builtin.是列表',
            '是字典': '_light_builtin.是字典',
            '是空': '_light_builtin.是空',
            '是字母': '_light_builtin.是字母',
            '是数字符': '_light_builtin.是数字',
            '是空白': '_light_builtin.是空白',
            # 随机函数
            '随机整数': '_light_builtin.随机整数',
            '随机浮点': '_light_builtin.随机浮点',
            '随机选择': '_light_builtin.随机选择',
            # 统计函数
            '阶乘': '_light_builtin.阶乘',
            '平均数': '_light_builtin.平均数',
            '中位数': '_light_builtin.中位数',
            '众数': '_light_builtin.众数',
            '方差': '_light_builtin.方差',
            '标准差': '_light_builtin.标准差',
            '样本方差': '_light_builtin.样本方差',
            '样本标准差': '_light_builtin.样本标准差',
            '累积和': '_light_builtin.累积和',
            # 数学常量
            '圆周率': '_light_builtin.圆周率',
            '自然常数': '_light_builtin.自然常数',
            '角度转弧度': '_light_builtin.角度转弧度',
            '弧度转角度': '_light_builtin.弧度转角度',
            # 字符串扩展
            '截取': '_light_builtin.截取',
            '字符串获取': '_light_builtin.字符串获取',
            # 列表扩展
            '列表弹出': '_light_builtin.列表弹出',
            '列': '_light_builtin.列',
            '副本': '_light_builtin.副本',
            # 字典扩展
            '字典键列表': '_light_builtin.字典键列表',
            '字典值列表': '_light_builtin.字典值列表',
            '字典项列表': '_light_builtin.字典项列表',
            '字典包含键': '_light_builtin.字典包含键',
            '字典删除': '_light_builtin.字典删除',
            # 路径操作
            '分割路径': '_light_builtin.分割路径',
            '分割扩展名': '_light_builtin.分割扩展名',
            # 系统操作
            '读取行': '_light_builtin.读取行',
            '写入输出': '_light_builtin.写入输出',
            '刷新输出': '_light_builtin.刷新输出',
            '写入错误': '_light_builtin.写入错误',
            '打印错误': '_light_builtin.打印错误',
            # JSON 操作
            '解析JSON': '_light_builtin.解析JSON',
            '序列化JSON': '_light_builtin.序列化JSON',
            '美化JSON': '_light_builtin.美化JSON',
        }
    
    def generate(self, module) -> str:
        """生成Python代码"""
        self.output_lines = []
        
        # 先进行类型推断
        self.type_cache = self.type_inferencer.infer(module)
        
        # 添加文件头
        self._add_line("# 由光明编译器生成")
        self._add_line("# 源文件: 光明代码")
        self._add_line("")
        
        # 添加标准库导入
        self._add_line("# 导入光明标准库")
        self._add_line("import sys")
        self._add_line("import os")
        self._add_line("import asyncio")  # 用于 async/await 支持
        self._add_line("from typing import Any, Callable, Optional")  # 类型注解（段->Callable 等）求值所需
        self._add_line("")
        self._add_line("try:")
        self._add_line("    import importlib.util")
        self._add_line("except ImportError:")
        self._add_line("    importlib = None")
        self._add_line("")
        self._add_line("try:")
        self._add_line("    _light_file_dir = os.path.dirname(os.path.abspath(__file__))")
        self._add_line("except NameError:")
        self._add_line("    _light_file_dir = None")
        if self._stdlib_dir:
            self._add_line(f"    _light_stdlib = {self._stdlib_dir!r}")
        else:
            self._add_line("    _light_stdlib = os.path.join(_light_file_dir, 'stdlib') if _light_file_dir else None")
        self._add_line("if not _light_stdlib or not os.path.isdir(_light_stdlib):")
        self._add_line("    _light_stdlib = os.path.join(os.getcwd(), 'stdlib')")
        self._add_line("    if not os.path.isdir(_light_stdlib):")
        self._add_line("        parent_stdlib = os.path.normpath(os.path.join(os.getcwd(), '..', 'stdlib'))")
        self._add_line("        if os.path.isdir(parent_stdlib):")
        self._add_line("            _light_stdlib = parent_stdlib")
        self._add_line("")
        self._add_line("if os.path.isdir(_light_stdlib) and _light_stdlib not in sys.path:")
        self._add_line("    sys.path.insert(0, _light_stdlib)")
        self._add_line("if os.path.isdir(_light_stdlib):")
        self._add_line("    _light_parent = os.path.dirname(_light_stdlib)")
        self._add_line("    if _light_parent not in sys.path:")
        self._add_line("        sys.path.insert(0, _light_parent)")
        self._add_line("")
        self._add_line("if importlib:")
        self._add_line("    try:")
        self._add_line("        _light_builtin_path = os.path.join(_light_stdlib, 'builtins.py')")
        self._add_line("        if os.path.isfile(_light_builtin_path):")
        self._add_line("            spec = importlib.util.spec_from_file_location('light_builtins', _light_builtin_path)")
        self._add_line("            _light_builtin = importlib.util.module_from_spec(spec)")
        self._add_line("            spec.loader.exec_module(_light_builtin)")
        self._add_line("        else:")
        self._add_line("            raise ImportError()")
        self._add_line("    except:")
        self._add_line("        import types")
        self._add_line("        _light_builtin = types.ModuleType('_light_builtin')")
        self._add_line("        _light_builtin.读取文件 = lambda path: open(path, 'r', encoding='utf-8').read()")
        self._add_line("        _light_builtin.写入文件 = lambda path, content: open(path, 'w', encoding='utf-8').write(content) or None")
        self._add_line("        _light_builtin.文件存在 = lambda path: __import__('os').path.isfile(path)")
        self._add_line("        _light_builtin.目录存在 = lambda path: __import__('os').path.isdir(path)")
        self._add_line("        _light_builtin.打印 = print")
        self._add_line("        _light_builtin.列表创建 = list")
        self._add_line("        _light_builtin.列表追加 = lambda lst, item: lst.append(item)")
        self._add_line("        _light_builtin.列表获取 = lambda lst, i: lst[i]")
        self._add_line("        _light_builtin.列表弹出 = lambda lst, i=-1: lst.pop(i)")
        self._add_line("        _light_builtin.列表插入 = lambda lst, i, v: lst.insert(i, v)")
        self._add_line("        _light_builtin.列表包含 = lambda lst, item: item in lst")
        self._add_line("        _light_builtin.字符串长度 = len")
        self._add_line("        _light_builtin.显示宽度 = lambda text: sum(2 if __import__('unicodedata').east_asian_width(ch) in ('W', 'F') else 1 for ch in str(text))")
        self._add_line("        _light_builtin.字典创建 = dict")
        self._add_line("        _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})")
        self._add_line("        _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)")
        self._add_line("        _light_builtin.转整数 = lambda text: int(text)")
        self._add_line("        _light_builtin.转浮点 = lambda text: float(text)")
        self._add_line("        _light_builtin.时间戳 = lambda: int(__import__('time').time())")
        self._add_line("        _light_builtin.格式化时间 = lambda ts, fmt: __import__('time').strftime(fmt, __import__('time').localtime(ts))")
        self._add_line("        _light_builtin.JSON序列化 = lambda obj, indent=2: json.dumps(obj, ensure_ascii=False, indent=indent)")
        self._add_line("else:")
        self._add_line("    import types")
        self._add_line("    _light_builtin = types.ModuleType('_light_builtin')")
        self._add_line("    _light_builtin.打印 = print")
        self._add_line("    _light_builtin.转整数 = lambda text: int(text)")
        self._add_line("    _light_builtin.转浮点 = lambda text: float(text)")
        self._add_line("    _light_builtin.时间戳 = lambda: int(__import__('time').time())")
        self._add_line("    _light_builtin.格式化时间 = lambda ts, fmt: __import__('time').strftime(fmt, __import__('time').localtime(ts))")
        self._add_line("    _light_builtin.JSON序列化 = lambda obj, indent=2: json.dumps(obj, ensure_ascii=False, indent=indent)")
        self._add_line("")
        
        self._add_line("# stdlib 物理缺失时的兜底：补齐常用 builtin + 注册 文件系统 模块")
        self._add_line("for _light_n, _light_f in [")
        self._add_line("    ('列表排序', lambda lst, 反向=False: lst.sort(reverse=反向)),")
        self._add_line("    ('列表反转', lambda lst: lst.reverse()),")
        self._add_line("    ('列表清空', lambda lst: lst.clear()),")
        self._add_line("    ('列表移除', lambda lst, item: lst.remove(item)),")
        self._add_line("    ('列表长度', len),")
        self._add_line("    ('追加文件', lambda path, content, encoding='utf-8': open(path, 'a', encoding=encoding).write(content) or None),")
        self._add_line("    ('删除文件', lambda path: __import__('os').remove(path) if __import__('os').path.isfile(path) else None),")
        self._add_line("    ('复制文件', lambda src, dst: __import__('shutil').copy2(src, dst)),")
        self._add_line("    ('移动文件', lambda src, dst: __import__('shutil').move(src, dst)),")
        self._add_line("    ('创建目录', lambda path: __import__('os').makedirs(path, exist_ok=True)),")
        self._add_line("    ('删除目录', lambda path: __import__('shutil').rmtree(path)),")
        self._add_line("    ('路径连接', lambda *parts: __import__('os').path.join(*parts)),")
        self._add_line("    ('当前工作目录', lambda: __import__('os').getcwd()),")
        self._add_line("]:")
        self._add_line("    if not hasattr(_light_builtin, _light_n):")
        self._add_line("        setattr(_light_builtin, _light_n, _light_f)")
        self._add_line("if (not _light_stdlib) or (not os.path.isdir(_light_stdlib or '')):")
        self._add_line("    try:")
        self._add_line("        import types as _light_types")
        self._add_line("        _light_fs = _light_types.ModuleType('文件系统')")
        self._add_line("        for _light_fn in ('读取文件', '写入文件', '追加文件', '文件存在', '删除文件', '复制文件', '移动文件', '创建目录', '删除目录', '目录存在', '路径连接', '当前工作目录', '读取行'):")
        self._add_line("            if hasattr(_light_builtin, _light_fn):")
        self._add_line("                setattr(_light_fs, _light_fn, getattr(_light_builtin, _light_fn))")
        self._add_line("        sys.modules.setdefault('文件系统', _light_fs)")
        self._add_line("    except Exception:")
        self._add_line("        pass")

        # 生成导入语句
        if hasattr(module, 'imports') and module.imports:
            for imp in module.imports:
                self._generate_import_stmt(imp)
            self._add_line("")
        
        # 生成枚举定义（ADT）
        if hasattr(module, 'enums'):
            for enum_def in module.enums:
                self._generate_enum(enum_def)
        
        # 生成 trait 定义
        if hasattr(module, 'trait_defs'):
            for trait_def in module.trait_defs:
                self._generate_trait_def(trait_def)
        
        # 生成 trait 实现
        if hasattr(module, 'trait_impls'):
            for trait_impl in module.trait_impls:
                self._generate_trait_impl(trait_impl)
        
        # 生成段落定义
        if hasattr(module, 'segments'):
            for segment in module.segments:
                self._generate_segment(segment)
        
        # 生成类定义
        if hasattr(module, 'classes'):
            for cls in module.classes:
                self._generate_class(cls)
        
        # 生成语句
        if hasattr(module, 'statements'):
            # B5：检查模块级语句是否含 DeferStatement，如有则包 try/finally
            _has_defer = any(is_instance(s, 'DeferStatement') for s in module.statements)
            if _has_defer:
                self._add_line("_light_defers = []")
                self._add_line("try:")
                self.indent_level += 1
            for stmt in module.statements:
                self._generate_statement(stmt)
            if _has_defer:
                self.indent_level -= 1
                self._add_line("finally:")
                self.indent_level += 1
                self._add_line("for _d in reversed(_light_defers):")
                self.indent_level += 1
                self._add_line("_d()")
                self.indent_level -= 1
        
        # 如果定义了主程序函数，且模块顶层没有显式调用，自动添加入口调用
        has_main = '主程序' in self.user_functions or 'mean' in self.user_functions
        has_explicit_call = False
        if has_main and hasattr(module, 'statements'):
            main_name = '主程序' if '主程序' in self.user_functions else 'mean'
            for stmt in module.statements:
                if is_instance(stmt, 'ExpressionStatement'):
                    expr = stmt.expression
                    if is_instance(expr, 'FunctionCall'):
                        if is_instance(expr.name, 'Identifier') and expr.name.name == main_name:
                            has_explicit_call = True
                            break
                elif is_instance(stmt, 'FunctionCall'):
                    if is_instance(stmt.name, 'Identifier') and stmt.name.name == main_name:
                        has_explicit_call = True
                        break
                elif is_instance(stmt, 'Identifier') and stmt.name == main_name:
                    has_explicit_call = True
                    break
        
        if has_main and not has_explicit_call:
            main_name = '主程序' if '主程序' in self.user_functions else 'mean'
            self._add_line('')
            self._add_line(f'if __name__ == \'__main__\':')
            self.indent_level += 1
            self._add_line(f'{main_name}()')
            self.indent_level -= 1
        
        # 单 B·修复4：接口/抽象方法产物用到 ABC/abstractmethod，需在文件头后补导入。
        # 与 src 后端 code_generator.py:827-838 同一机制（找到头部注释/空行后插入）。
        if getattr(self, '_needs_abc', False):
            insert_pos = 0
            for i, line in enumerate(self.output_lines):
                if line.startswith("#") or line == "":
                    insert_pos = i + 1
                else:
                    break
            self.output_lines.insert(insert_pos, "")
            self.output_lines.insert(insert_pos, "from abc import ABC, abstractmethod")

        # B5：异步遍历泛化——按需插入 _light_async_iter 与 asyncio 导入
        if self._needs_asyncio:
            insert_pos = 0
            for i, line in enumerate(self.output_lines):
                if line.startswith("#") or line == "":
                    insert_pos = i + 1
                else:
                    break
            self.output_lines.insert(insert_pos, "")
            self.output_lines.insert(insert_pos, "import asyncio")
        if self._needs_async_iter:
            insert_pos = 0
            for i, line in enumerate(self.output_lines):
                if line.startswith("#") or line == "":
                    insert_pos = i + 1
                else:
                    break
            block = [
                "async def _light_async_iter(_iterable):",
                "    if hasattr(_iterable, '__aiter__'):",
                "        async for _item in _iterable:",
                "            yield _item",
                "    else:",
                "        for _item in _iterable:",
                "            yield _item",
                "",
            ]
            for line in reversed(block):
                self.output_lines.insert(insert_pos, line)

        return self._build_output()

    
    def _build_output(self) -> str:
        """构建最终输出字符串"""
        return '\n'.join(self.output_lines)
    
    def _get_indent(self, level: int) -> str:
        """获取指定层级的缩进字符串（带缓存）"""
        if level not in self._indent_cache:
            self._indent_cache[level] = self.indent_str * level
        return self._indent_cache[level]
    
    def _add_line(self, line: str):
        """添加一行代码"""
        if line:
            self.output_lines.append(self._get_indent(self.indent_level) + line)
        else:
            self.output_lines.append('')
    
    def _sanitize_name(self, name: str) -> str:
        """清理名称（处理Python关键字冲突）"""
        python_keywords = {'def', 'class', 'if', 'else', 'for', 'while', 'return', 'import', 'from', 'print'}
        if name in python_keywords:
            return f"_{name}"
        return name
    
    # ---- 与 src 后端对齐的三张表（单 B·修复5）----------------------------
    # 权威定义在 code_generator.PythonCodeGenerator 上（_SELF_NAMES /
    # _CTOR_NAMES / _MEMBER_SUFFIX_MAP）。这里刻意**不 import** 那个模块（它
    # `from light_parser_v3 import *`，为三个常量拖进整条解析链不值当），而是
    # 抄一份并由 tests/test_context_manager.py::TestBackendParity 断言两边逐项
    # 相等——改一边忘另一边会当场打红，不会再出现「同一份源码两个后端语义不同」。
    _SELF_NAMES = ('己', '自')
    _CTOR_NAMES = ('构造', '初始化', '构')
    # 协议魔术方法名（定义侧）：与 code_generator.py::_generate_method(:2722-2730)
    # 的 if/elif 链同义。src 后端是内联链、无表可比对，故这里**不做**表级 parity
    # 断言，改由 tests/test_context_manager.py::TestCtorNameMapping 用「双后端各编译
    # 一遍、产物都必须含 __iter__/__next__/__enter__/__exit__」的行为级 parity 锁住，
    # 避免为抽表而改动 src 后端（改它会漂 assert_quality 行号基线）。
    _PROTOCOL_METHOD_MAP = {
        '__迭代__': '__iter__',
        '__下一项__': '__next__',
        '__进入__': '__enter__',
        '__退出__': '__exit__',
    }
    _MEMBER_SUFFIX_MAP = (
        ('的长度', 'len({o})'),
        ('的项', '{o}.items()'),
        ('的键', '{o}.keys()'),
        ('的值', '{o}.values()'),
    )

    def _is_self_param(self, param_name) -> bool:
        """形参名是否是 self 引用（己/自）——方法定义已无条件注入 self，
        源码里显式写出的 自/己 必须吃掉，否则 `def 打印(self, 自)` 重复注入。"""
        return isinstance(param_name, str) and param_name in self._SELF_NAMES

    def _is_ctor_method(self, method) -> bool:
        """方法是否为构造函数——定义侧唯一判据，与 src 后端
        code_generator.py::_generate_method(:2716) 的 is_ctor 同口径：

            is_ctor = getattr(method, 'is_constructor', False) or method_name in _CTOR_NAMES

        必须读同一张 _CTOR_NAMES，否则「`构造 接收 …` 译成 __init__、而
        `段 构造(…)` 仍发 def 构造」会分叉——两种写法都是合法语法，
        parser 只对前者归一成 __init__（见 parser 输出的
        MethodDefinition.name='__init__', is_constructor=True）。
        """
        return bool(getattr(method, 'is_constructor', False)) or getattr(method, 'name', None) in self._CTOR_NAMES

    def _split_member_suffix(self, name):
        """拆 `X的项` 这类复合标识符的成员后缀，命中返回 (对象原名, 输出模板)。
        与 code_generator.py::_split_member_suffix 同语义（含「对象部分非空」约束）。"""
        if not isinstance(name, str):
            return None
        for suffix, tmpl in self._MEMBER_SUFFIX_MAP:
            if name.endswith(suffix) and len(name) > len(suffix):
                obj = name[:-len(suffix)]
                if obj and not obj.endswith('.'):
                    return obj, tmpl
        return None

    def _resolve_name(self, name: str) -> str:
        """解析标识符名：先做 己/自 → self 映射与 `的X` 后缀改写，再做关键字清理。

        对齐 code_generator.py::_resolve_identifier_name：
        - 己 / 自            → self
        - 己.属性 / 自.属性   → self.属性
        - X的长度/的项/的键/的值 → len(X) / X.items() / X.keys() / X.values()
        self 映射仅在类方法/构造函数内生效，避免把类外的普通变量名「己」（天干）误映射。
        `的X` 改写不受此限：它是词法层不切 `的` 带来的必然后果，与是否在类里无关。
        """
        if not isinstance(name, str):
            return self._sanitize_name(name)

        split = self._split_member_suffix(name)
        if split is not None:
            obj_raw, tmpl = split
            # 对象部分必须再走一遍本函数：`自.成绩的项` 里的 自 也要归一成 self
            return tmpl.format(o=self._resolve_name(obj_raw))

        if self._in_class_method:
            for sref in self._SELF_NAMES:
                if name == sref:
                    return 'self'
                if name.startswith(sref + '.'):
                    return 'self.' + name[len(sref) + 1:]
        return self._sanitize_name(name)


    def _generate_statement(self, stmt):
        """生成语句（支持统一AST）"""
        if stmt is None:
            return

        # L-061：为每个光明语句嵌入源行号映射注释（# LIGHT_SRC:<行号>），
        # 供 enhanced_errors/error_formatter 把运行时 traceback 的 .py 行号
        # 还原为光明源码行号，避免行号错位。
        _src_line = getattr(stmt, 'line', None)
        if isinstance(_src_line, int) and _src_line > 0:
            self._add_line(f"# LIGHT_SRC:{_src_line}")
        
        node_type = type(stmt).__name__
        
        # 变量声明
        if is_instance(stmt, 'VariableDeclaration') or is_instance(stmt, 'VarDecl'):
            self._generate_var_decl(stmt)
        
        # 条件语句
        elif is_instance(stmt, 'IfStatement') or is_instance(stmt, 'IfStmt'):
            self._generate_if_stmt(stmt)
        
        # 遍历循环
        elif is_instance(stmt, 'ForeachStatement') or is_instance(stmt, 'ForEachStmt') or is_instance(stmt, 'ForeachStmt'):
            self._generate_foreach_stmt(stmt)
        
        # 当循环
        elif is_instance(stmt, 'WhileStatement') or is_instance(stmt, 'WhileStmt'):
            self._generate_while_stmt(stmt)
        
        # 返回语句
        elif is_instance(stmt, 'ReturnStatement') or is_instance(stmt, 'ReturnStmt'):
            self._generate_return_stmt(stmt)
        
        # 打印语句
        elif is_instance(stmt, 'PrintStatement') or is_instance(stmt, 'PrintStmt'):
            self._generate_print_stmt(stmt)
        
        # 断言语句（L-037：与 src 后端同口径，支持括号两参写法）
        elif is_instance(stmt, 'AssertStmt') or is_instance(stmt, 'AssertStatement'):
            self._generate_assert_stmt(stmt)
        
        # 表达式语句
        elif is_instance(stmt, 'ExpressionStatement') or is_instance(stmt, 'ExprStmt'):
            expr_code = self._generate_expr(stmt.expression)
            self._add_line(expr_code)
        
        # 二元运算作为独立语句（L-045：`写 "a" + 标签` 被 parser 拆成 BinaryOp
        # 语句；与 src 后端同口径——路由到 _generate_expr，其内已挂输出拼接合并）
        elif is_instance(stmt, 'BinaryOp'):
            expr_code = self._generate_expr(stmt)
            self._add_line(expr_code)
        
        # 赋值语句
        elif is_instance(stmt, 'Assignment') or is_instance(stmt, 'AssignStmt'):
            target_code = self._generate_expr(stmt.target)
            value_code = self._generate_expr(stmt.value)
            self._add_line(f"{target_code} = {value_code}")
        
        # 复合赋值语句
        elif is_instance(stmt, 'CompoundAssignment'):
            op_map = {
                '加': '+=', '减': '-=', '乘': '*=', '除': '//=',
                '模': '%=', '幂': '**=',
                '加上': '+=', '减去': '-=', '乘以': '*=', '除以': '//=',
            }
            target_code = self._sanitize_name(stmt.target) if isinstance(stmt.target, str) else self._generate_expr(stmt.target)
            op = op_map.get(stmt.operator, '+=')
            value_code = self._generate_expr(stmt.value)
            self._add_line(f"{target_code} {op} {value_code}")
        
        # 跳出语句
        elif is_instance(stmt, 'BreakStatement') or is_instance(stmt, 'BreakStmt'):
            self._add_line("break")
        
        # 跳过语句
        elif is_instance(stmt, 'ContinueStatement') or is_instance(stmt, 'ContinueStmt'):
            self._add_line("continue")
        
        # 异常处理
        elif is_instance(stmt, 'TryStatement') or is_instance(stmt, 'TryStmt'):
            self._generate_try_stmt(stmt)
        
        # 抛出异常
        elif is_instance(stmt, 'ThrowStatement') or is_instance(stmt, 'ThrowStmt'):
            value_code = self._generate_expr(stmt.value)
            # Python 要求异常派生自 BaseException，字符串需包装在 Exception() 中
            if is_instance(stmt.value, 'StringLiteral'):
                value_code = f"Exception({value_code})"
            self._add_line(f"raise {value_code}")
        
        # 模式匹配
        elif is_instance(stmt, 'MatchStatement') or is_instance(stmt, 'MatchStmt'):
            self._generate_match_stmt(stmt)
        
        # 上下文管理器
        elif is_instance(stmt, 'WithStatement') or is_instance(stmt, 'WithStmt'):
            self._generate_with_stmt(stmt)
        
        # 解构赋值
        elif is_instance(stmt, 'DestructuringAssignment'):
            self._generate_destructuring(stmt)
        
        # 装饰器定义
        elif is_instance(stmt, 'DecoratorDefinition'):
            self._generate_decorator(stmt)
        
        # 装饰器链（多个装饰器 + 函数）
        elif is_instance(stmt, 'DecoratedFunction'):
            self._generate_decorated_function_unified(stmt)
        
        # 导入语句
        elif is_instance(stmt, 'ImportStatement') or is_instance(stmt, 'ImportStmt'):
            self._generate_import_stmt(stmt)
        
        # 导出语句
        elif is_instance(stmt, 'ExportStatement') or is_instance(stmt, 'ExportStmt'):
            pass  # Python中不需要特殊处理
        
        # 函数调用作为语句
        elif is_instance(stmt, 'FunctionCall') or is_instance(stmt, 'ParagraphCall') or is_instance(stmt, 'FunctionCallExpr'):
            expr_code = self._generate_expr(stmt)
            self._add_line(expr_code)
        
        # 成员访问作为独立语句（如 结果.追加(...)）
        # 单 B·Gap B 修复：对齐 code_generator.py:1353 的 MemberAccess 语句分支。
        # 此前 unified 缺此分支，导致「成员方法调用作语句」被静默吞掉、
        # for 循环体变空 → IndentationError（实测复现：警告「未知语句类型: MemberAccess」）。
        elif is_instance(stmt, 'MemberAccess'):
            expr_code = self._generate_expr(stmt)
            self._add_line(expr_code)
        
        # 标识符作为语句（调用）
        elif is_instance(stmt, 'Identifier'):
            name = self._sanitize_name(stmt.name)
            self._add_line(f"{name}()")
        
        # 段落定义
        elif is_instance(stmt, 'SegmentDefinition') or is_instance(stmt, 'Paragraph') or is_instance(stmt, 'FunctionDefinition'):
            self._generate_segment(stmt)
        
        # 类定义
        elif is_instance(stmt, 'ClassDefinition'):
            self._generate_class(stmt)
        
        # 接口定义（`接 X:`）
        # 单 B·修复4：本分支原先缺失，InterfaceDefinition 会掉进下面的兜底
        # `print("警告：未知语句类型")` —— 只打印警告、不抛错，于是 unified 后端把
        # 接口声明**静默丢弃**（实测产物里连 class 都没有）。src 后端有
        # code_generator.py:_generate_interface_definition，两后端语义因此分叉。
        elif is_instance(stmt, 'InterfaceDefinition'):
            self._generate_interface_definition(stmt)
        

        # 推迟语句（defer）
        elif is_instance(stmt, 'DeferStatement') or is_instance(stmt, 'DeferStmt'):
            self._generate_defer_stmt(stmt)
        
        # 并行作用域（结构化并发）
        elif is_instance(stmt, 'AsyncScope'):
            self._generate_async_scope(stmt)
        
        # 未知类型
        else:
            print(f"警告：未知语句类型: {node_type}")
    
    def _generate_var_decl(self, stmt):
        """生成变量声明"""
        name = self._sanitize_name(stmt.name)
        value = self._generate_expr(stmt.value)
        self._add_line(f"{name} = {value}")
    
    def _generate_if_stmt(self, stmt):
        """生成条件语句"""
        # ========== 死代码消除优化 ==========
        # 检查条件是否是常量
        condition_val = None
        if hasattr(stmt.condition, 'value'):
            cond_val = stmt.condition.value
            if isinstance(cond_val, bool):
                condition_val = cond_val
            elif is_instance(stmt.condition, 'BooleanLiteral'):
                condition_val = stmt.condition.value
        
        if condition_val is True:
            # 条件恒为真，只生成 then 分支
            self._add_line("# 常量条件优化 (恒真)")
            then_body = getattr(stmt, 'then_body', []) or []
            for s in then_body:
                self._generate_statement(s)
            return
        elif condition_val is False:
            # 条件恒为假，跳过 then 分支，只生成 else 分支（如果有）
            self._add_line("# 常量条件优化 (恒假)")
            # 处理 else 分支
            if hasattr(stmt, 'else_body') and stmt.else_body:
                if isinstance(stmt.else_body, list):
                    for s in stmt.else_body:
                        self._generate_statement(s)
                elif is_instance(stmt.else_body, 'IfStmt'):
                    # 嵌套的 if (elif/else)
                    self._generate_if_stmt(stmt.else_body)
            return
        # ========== 死代码消除优化结束 ==========
        
        condition = self._generate_expr(stmt.condition)
        self._add_line(f"if {condition}:")
        
        self.indent_level += 1
        then_body = getattr(stmt, 'then_body', []) or []
        for s in then_body:
            self._generate_statement(s)
        self.indent_level -= 1
        
        # 处理elif：检查 elseif_conditions/elseif_bodies 格式
        if hasattr(stmt, 'elseif_conditions') and stmt.elseif_conditions:
            for i, elif_cond in enumerate(stmt.elseif_conditions):
                elif_body = stmt.elseif_bodies[i] if hasattr(stmt, 'elseif_bodies') and i < len(stmt.elseif_bodies) else []
                cond_code = self._generate_expr(elif_cond)
                self._add_line(f"elif {cond_code}:")
                self.indent_level += 1
                for s in elif_body:
                    self._generate_statement(s)
                self.indent_level -= 1
        # 处理elif：检查 else_body 是否是嵌套的 IfStmt（elif 链）
        elif hasattr(stmt, 'else_body') and stmt.else_body and isinstance(stmt.else_body, type(stmt)):
            # else_body 是嵌套的 IfStmt，表示 elif
            current = stmt.else_body
            while current and isinstance(current, type(stmt)):
                cond_code = self._generate_expr(current.condition)
                self._add_line(f"elif {cond_code}:")
                self.indent_level += 1
                current_then = getattr(current, 'then_body', []) or []
                for s in current_then:
                    self._generate_statement(s)
                self.indent_level -= 1
                current = getattr(current, 'else_body', None)
                if current and not isinstance(current, type(stmt)):
                    # 最后一个 else
                    self._add_line("else:")
                    self.indent_level += 1
                    if isinstance(current, list):
                        for s in current:
                            self._generate_statement(s)
                    else:
                        self._generate_statement(current)
                    self.indent_level -= 1
                    current = None
            return
        
        # 处理else
        if hasattr(stmt, 'else_body') and stmt.else_body and isinstance(stmt.else_body, list):
            self._add_line("else:")
            self.indent_level += 1
            for s in stmt.else_body:
                self._generate_statement(s)
            self.indent_level -= 1
    
    def _generate_foreach_stmt(self, stmt):
        """生成遍历循环"""
        var_name = self._sanitize_name(stmt.variable)
        iterable = self._generate_expr(stmt.iterable)
        is_async = getattr(stmt, 'is_async', False)
        if is_async:
            # B5：异步遍历泛化——用 _light_async_iter 包装，普通 list 也能 async for
            self._needs_async_iter = True
            self._needs_asyncio = True
            self._add_line(f"async for {var_name} in _light_async_iter({iterable}):")
        else:
            self._add_line(f"for {var_name} in {iterable}:")
        
        self.indent_level += 1
        for s in stmt.body:
            self._generate_statement(s)
        self.indent_level -= 1
    
    def _generate_while_stmt(self, stmt):
        """生成当循环"""
        condition = self._generate_expr(stmt.condition)
        self._add_line(f"while {condition}:")
        
        self.indent_level += 1
        for s in stmt.body:
            self._generate_statement(s)
        self.indent_level -= 1
    
    def _generate_return_stmt(self, stmt):
        """生成返回语句

        模块级 return 在 Python 中非法，仅在函数/段落内部生成 return。
        否则将返回值作为裸表达式输出（用于 REPL 或模块级执行）。
        """
        if self._in_function:
            if stmt.value is not None:
                value_code = self._generate_expr(stmt.value)
                self._add_line(f"return {value_code}")
            else:
                self._add_line("return")
    
    def _generate_print_stmt(self, stmt):
        """生成打印语句"""
        value_code = self._generate_expr(stmt.value)
        self._add_line(f"print({value_code})")
    
    def _generate_assert_stmt(self, stmt):
        """生成断言语句（L-037：括号两参 `断言(条件, 标签)` 拆回 assert 条件, 标签）。

        parser 把括号两参解析成 AssertStmt(condition=TupleLiteral(条件, 标签), message=None)，
        直接发射会得到 `assert (条件, 标签)`（非空元组恒真，断言静默 no-op）。
        与 code_generator.py 的 _generate_assert_stmt 同口径处理。
        """
        cond = getattr(stmt, 'condition', None)
        msg = getattr(stmt, 'message', None)
        if (msg is None and cond is not None and is_instance(cond, 'TupleLiteral')):
            elems = getattr(cond, 'elements', None)
            if elems and len(elems) == 2:
                msg = elems[1]
                cond = elems[0]
        cond_code = self._generate_expr(cond)
        if msg is not None:
            self._add_line(f"assert {cond_code}, {self._generate_expr(msg)}")
        else:
            self._add_line(f"assert {cond_code}")
    
    def _generate_try_stmt(self, stmt):
        """生成异常处理"""
        self._add_line("try:")
        
        self.indent_level += 1
        for s in stmt.try_body:
            self._generate_statement(s)
        self.indent_level -= 1
        
        # L-016：`捕获 全部` / 裸 `捕获:` → except BaseException（可接住 asyncio.CancelledError）。
        # 与 code_generator.py 的 _generate_catch_clause 同口径：
        #   `捕获:`            —— 裸捕获，catch_type/catch_var 均空；
        #   `捕获 全部:`        —— parser 把「全部」当变量名放进 catch_var；
        #   `捕获 全部 为 变量:` —— parser 把「全部」当类型名放进 catch_type，变量单独绑定。
        # 裸 `捕获:` 也映射 BaseException（Python 裸 except: 语义，也是 test_L016 的验收语义）。
        catch_type = getattr(stmt, 'catch_type', None)
        catch_var = getattr(stmt, 'catch_var', None)
        catch_body = getattr(stmt, 'catch_body', None)
        is_all = (catch_type == '全部') or (catch_type is None and (catch_var is None or catch_var == '全部'))
        if is_all or catch_var or catch_type:
            # 构建 except 子句
            if is_all:
                if catch_type == '全部' and catch_var:
                    self._add_line(f"except BaseException as {catch_var}:")
                else:
                    self._add_line("except BaseException:")
            else:
                exc_type = catch_type if catch_type else "Exception"
                if catch_var:
                    self._add_line(f"except {exc_type} as {catch_var}:")
                else:
                    self._add_line(f"except {exc_type}:")
            self.indent_level += 1
            for s in catch_body:
                self._generate_statement(s)
            self.indent_level -= 1
        
        if hasattr(stmt, 'finally_body') and stmt.finally_body:
            self._add_line("finally:")
            self.indent_level += 1
            for s in stmt.finally_body:
                self._generate_statement(s)
            self.indent_level -= 1
        elif not (catch_var or catch_type) and not is_all:
            # Python 要求 try 必须有 except 或 finally
            self._add_line("finally:")
            self.indent_level += 1
            self._add_line("pass")
            self.indent_level -= 1
    
    def _generate_match_stmt(self, stmt):
        """生成模式匹配语句 — 匹配 值：情况 ... 结束。"""
        subject = self._generate_expr(stmt.subject)
        self._add_line(f"match {subject}:")
        self.indent_level += 1
        for case in stmt.cases:
            pattern_code = self._generate_match_pattern(case.pattern)
            guard_code = ""
            if hasattr(case, 'guard') and case.guard:
                guard_code = f" if {self._generate_expr(case.guard)}"
            self._add_line(f"case {pattern_code}{guard_code}:")
            self.indent_level += 1
            for s in case.body:
                self._generate_statement(s)
            self.indent_level -= 1
        # 如果没有任何case，添加pass
        if not stmt.cases:
            self._add_line("pass")
        self.indent_level -= 1
    
    def _generate_match_pattern(self, pattern):
        """生成匹配模式"""
        if pattern is None:
            return "_"
        
        kind = pattern.kind if hasattr(pattern, 'kind') else 'wildcard'
        
        if kind == 'number':
            return self._generate_expr(pattern.value)
        elif kind == 'string':
            return self._generate_expr(pattern.value)
        elif kind == 'bool':
            return self._generate_expr(pattern.value)
        elif kind == 'null':
            return "None"
        elif kind == 'wildcard':
            return "_"
        elif kind == 'variable':
            binding = pattern.binding if hasattr(pattern, 'binding') else ''
            return self._sanitize_name(binding)
        elif kind == 'list':
            elements = []
            if hasattr(pattern, 'elements') and pattern.elements:
                for e in pattern.elements:
                    elements.append(self._generate_match_pattern(e))
            return f"[{', '.join(elements)}]"
        elif kind == 'type_check':
            type_name = pattern.type_name if hasattr(pattern, 'type_name') else ''
            binding = pattern.binding if hasattr(pattern, 'binding') else ''
            type_name_py = self._sanitize_name(type_name)
            if binding:
                binding_py = self._sanitize_name(binding)
                return f"{type_name_py}() as {binding_py}"
            return f"{type_name_py}()"
        
        return "_"
    
    def _generate_with_stmt(self, stmt):
        """生成上下文管理器语句：使用 表达式 作为 变量：...结束。"""
        prefix = "async " if hasattr(stmt, 'is_async') and stmt.is_async else ""
        
        # 检查是否有多个上下文管理器
        items = getattr(stmt, 'items', None)
        if items and len(items) > 1:
            parts = []
            for expr, var in items:
                expr_str = self._generate_expr(expr)
                if var:
                    var_name = self._sanitize_name(var)
                    parts.append(f"{expr_str} as {var_name}")
                else:
                    parts.append(expr_str)
            context_str = ', '.join(parts)
            self._add_line(f"{prefix}with {context_str}:")
        else:
            context_expr = self._generate_expr(stmt.context_expr)
            if hasattr(stmt, 'variable') and stmt.variable:
                var = self._sanitize_name(stmt.variable)
                self._add_line(f"{prefix}with {context_expr} as {var}:")
            else:
                self._add_line(f"{prefix}with {context_expr}:")
        
        self.indent_level += 1
        if hasattr(stmt, 'body') and stmt.body:
            for s in stmt.body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
    
    def _generate_destructuring(self, stmt):
        """生成解构赋值：设 (甲, 乙) 为 元组"""
        variables = ', '.join(self._sanitize_name(v) for v in stmt.variables)
        value = self._generate_expr(stmt.value)
        # 多目标共享注解（新单 G）：与 src 后端同口径——Python 不允许
        # `甲, 乙: T = f()`，所以先给每个目标发一条纯注解行再发解包语句。
        ann = getattr(stmt, 'type_annotation', None)
        if ann:
            mapped = self._map_return_type(ann)
            for v in stmt.variables:
                self._add_line(f"{self._sanitize_name(v)}: {mapped}")
        self._add_line(f"{variables} = {value}")


    def _generate_defer_stmt(self, stmt):
        """生成推迟语句（B5：defer —— FILO 延迟执行）

        新语义：推迟体在作用域退出时执行（栈序 FILO），不再就地内联。
        实现：把推迟体注册到 _light_defers 列表，由段落作用域的
        try/finally 反序执行。
        """
        defer_id = getattr(self, '_defer_counter', 0)
        self._defer_counter = defer_id + 1
        func_name = f"_light_defer_{defer_id}"

        self._add_line(f"def {func_name}():")
        self.indent_level += 1
        if stmt.body:
            for s in stmt.body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
        self._add_line(f"_light_defers.append({func_name})")


    def _generate_async_scope(self, stmt):
        """生成并行作用域（结构化并发，使用 asyncio.gather 实现）"""
        # 并行 { 任务1 任务2 }
        # 转换为：result1, result2 = await asyncio.gather(task1(), task2())
        task_codes = []
        result_vars = getattr(stmt, 'result_vars', [])
        tasks = getattr(stmt, 'tasks', [])
        
        for task in tasks:
            task_code = self._generate_expr(task)
            task_codes.append(task_code)
        
        if task_codes:
            tasks_str = ', '.join(task_codes)
            if result_vars:
                vars_str = ', '.join(self._sanitize_name(v) for v in result_vars)
                self._add_line(f"{vars_str} = await asyncio.gather({tasks_str})")
            else:
                self._add_line(f"await asyncio.gather({tasks_str})")
        else:
            self._add_line("pass")
    
    def _generate_decorator(self, stmt):
        """生成装饰器定义：@段落名 标注 段落 ..."""
        decorator_name = self._sanitize_name(stmt.decorator_name)
        # 先生成装饰器行
        self._add_line(f"@{decorator_name}")
        # 再生成被装饰的段落
        if hasattr(stmt, 'paragraph') and stmt.paragraph:
            self._generate_segment(stmt.paragraph)
    
    def _generate_decorated_function_unified(self, stmt):
        """生成装饰器链（多个装饰器 + 函数定义）"""
        for decorator_info in getattr(stmt, 'decorators', []):
            decorator_name = self._sanitize_name(decorator_info.name)
            decorator_args = getattr(decorator_info, 'args', None)
            if decorator_args:
                args_parts = []
                for a in decorator_args:
                    if hasattr(a, 'name'):
                        args_parts.append(f"{a.name}={self._generate_expr(a.value)}")
                    else:
                        args_parts.append(self._generate_expr(a))
                args_str = ', '.join(args_parts)
                self._add_line(f"@{decorator_name}({args_str})")
            else:
                self._add_line(f"@{decorator_name}")
        # 生成被装饰的函数
        func = getattr(stmt, 'function', None)
        if func:
            self._generate_segment(func)
    
    def _generate_import_stmt(self, stmt):
        """生成导入语句"""
        module_name = getattr(stmt, 'module', None) or getattr(stmt, 'module_name', '')
        if isinstance(module_name, str):
            module_name = module_name.replace('《', '').replace('》', '')
        # 模块名映射：光明标准库模块 → Python 模块
        # 注意：有独立 stdlib 实现（含中文函数名）的模块不要映射到 Python 标准库
        # 只有 Python 原生模块名不同且函数名也相同时才需要映射
        module_map = {'系统': 'sys', '操作系统': 'os'}
        names = getattr(stmt, 'names', None) or getattr(stmt, 'symbols', None)
        if names:
            names_list = []
            for name in names:
                if isinstance(name, str):
                    names_list.append(name.replace('《', '').replace('》', ''))
                elif hasattr(name, 'name'):
                    names_list.append(name.name.replace('《', '').replace('》', ''))
                else:
                    names_list.append(str(name))
            names_str = ', '.join(names_list)
            if module_name:
                mapped = module_map.get(module_name, module_name)
                self._add_line(f"from {mapped} import {names_str}")
            else:
                # 直接导入：检查每个名字是否需要映射
                mapped_names = []
                for name in names_list:
                    mapped_names.append(module_map.get(name, name))
                names_str = ', '.join(mapped_names)
                self._add_line(f"import {names_str}")
        else:
            mapped = module_map.get(module_name, module_name)
            self._add_line(f"import {mapped}")
    
    def _generate_segment(self, segment):
        """生成段落定义"""
        name = self._sanitize_name(segment.name)
        
        # 记录用户定义的函数名
        self.user_functions.add(name)
        
        # 提取参数
        params = []
        if hasattr(segment, 'parameters'):
            for param in segment.parameters:
                params.append(self._sanitize_name(param.name))
        elif hasattr(segment, 'params'):
            for param in segment.params:
                if isinstance(param, dict) and 'name' in param:
                    params.append(self._sanitize_name(param['name']))
                else:
                    params.append(self._sanitize_name(str(param)))
        
        params_str = ', '.join(params) if params else ''
        
        # 检查是否为异步函数
        is_async = '异步' in getattr(segment, 'modifiers', [])
        def_keyword = 'async def' if is_async else 'def'
        
        # 函数定义
        self._add_line(f"{def_keyword} {name}({params_str}):")
        old_in_function = self._in_function
        self._in_function = True
        
        self.indent_level += 1
        if hasattr(segment, 'body') and segment.body:
            for s in segment.body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
        self._in_function = old_in_function
        
        self._add_line("")
    
    def _generate_enum(self, enum_def):
        """生成枚举/ADT 定义（Python 中转换为继承自 object 的类）"""
        name = self._sanitize_name(enum_def.name)
        
        # 使用类模拟枚举
        self._add_line(f"class {name}:")
        self.indent_level += 1
        
        # 生成变体作为类属性，每个变体是一个简单命名元组
        for variant in enum_def.variants:
            variant_name = self._sanitize_name(variant.name)
            if variant.fields:
                # 带字段的变体用 __init__ 初始化
                field_names = [f.name for f in variant.fields]
                field_str = ', '.join(f"self.{f} = {f}" for f in field_names)
                self._add_line(f"def __init__(self, {', '.join(field_names)}):")
                self.indent_level += 1
                self._add_line(f"self._variant = '{variant_name}'")
                for f in field_names:
                    self._add_line(f"self.{f} = {f}")
                self.indent_level -= 1
            else:
                # 无字段的变体用类属性
                self._add_line(f"pass")
        
        self._add_line("")
        self._add_line("@classmethod")
        self._add_line("def _variants(cls):")
        self.indent_level += 1
        variant_names = [v.name for v in enum_def.variants]
        names_str = ", ".join(f"'{n}'" for n in variant_names)
        self._add_line(f"return [{names_str}]")
        self.indent_level -= 1
        
        self.indent_level -= 1
        self._add_line("")

    def _generate_trait_def(self, trait_def):
        """生成 trait 定义（Python 中转换为抽象基类）"""
        name = self._sanitize_name(trait_def.name)
        
        self._add_line(f"class {name}(ABC):")
        self.indent_level += 1
        
        for method in trait_def.methods:
            params = ['self']
            for p in method.parameters:
                params.append(self._sanitize_name(p.name))
            params_str = ', '.join(params)
            
            if method.has_default:
                # 有默认实现的方法
                self._add_line(f"def {method.name}({params_str}):")
                self.indent_level += 1
                self._add_line(f"raise NotImplementedError")
                self.indent_level -= 1
            else:
                # 无默认实现的抽象方法
                self._add_line("@abstractmethod")
                self._add_line(f"def {method.name}({params_str}):")
                self.indent_level += 1
                self._add_line(f"pass")
                self.indent_level -= 1
        
        self.indent_level -= 1
        self._add_line("")
        self._needs_abc = True

    def _generate_trait_impl(self, trait_impl):
        """生成 trait 实现（Python 中混入继承或注册）"""
        type_name = self._sanitize_name(trait_impl.type_name)
        trait_name = self._sanitize_name(trait_impl.trait_name)
        
        # 将 trait 的方法添加到类型上（作为独立函数）
        for method in trait_impl.methods:
            params = ['self']
            for p in method.parameters:
                params.append(self._sanitize_name(p.name))
            params_str = ', '.join(params)
            
            self._add_line(f"def {method.name}({params_str}):")
            old_in_class_method = self._in_class_method
            self._in_class_method = True
            self.indent_level += 1
            for stmt in method.body:
                self._generate_statement(stmt)
            self.indent_level -= 1
            self._in_class_method = old_in_class_method
            self._add_line("")
        
        # 注册实现关系
        self._add_line(f"# {type_name} implements {trait_name}")
        self._add_line("")

    # ---- 接口定义（单 B·修复4：与 src 后端对齐）--------------------------
    # 参照 src/code_generator.py:1697-1766 的
    # _generate_interface_definition / _generate_abstract_method 实现，
    # 语义必须一致：接口 -> class X(ABC)；无方法体 -> @abstractmethod + pass；
    # 有方法体 -> 普通方法（默认实现）。
    _LIGHT_TYPE_MAP = {
        '整数': 'int', '小数': 'float', '浮数': 'float', '数': 'float',
        '文本': 'str', '串': 'str', '布尔': 'bool',
        '列表': 'list', '列': 'list', '字典': 'dict', '典': 'dict',
        '集合': 'set', '集': 'set', '任意': 'Any', '空': 'None',
        '段': 'Callable', '函数型': 'Callable',
    }

    def _map_return_type(self, light_type):
        """光明类型名 -> Python 类型名。

        必须做映射：直接把 `串` 写进 `-> 串` 注解会在运行期 NameError
        （注解在 def 执行时求值）。表与 src 的 _map_type 保持一致；
        表外的名字原样透传（用户自定义类名本就该原样出现）。
        """
        if not light_type:
            return None
        t = str(light_type).strip()
        return self._LIGHT_TYPE_MAP.get(t, self._sanitize_name(t))

    def _generate_interface_definition(self, stmt):
        """生成接口定义（`接 X:` -> class X(ABC)）"""
        self._needs_abc = True
        class_name = self._sanitize_name(stmt.name)

        bases = ['ABC']
        for sup in (getattr(stmt, 'super_interfaces', None) or []):
            bases.append(self._sanitize_name(sup if isinstance(sup, str) else getattr(sup, 'name', str(sup))))

        self._add_line(f"class {class_name}({', '.join(bases)}):")
        self.indent_level += 1

        methods = getattr(stmt, 'methods', None) or []
        for method in methods:
            self._generate_abstract_method(method)
        if not methods:
            self._add_line("pass")

        self.indent_level -= 1
        self._add_line("")

    def _generate_abstract_method(self, method):
        """生成协议方法：无方法体 -> 抽象方法；有方法体 -> 默认实现。"""
        method_name = self._sanitize_name(method.name)

        params = ['self']
        for param in (getattr(method, 'parameters', None) or []):
            raw = param.name if hasattr(param, 'name') else str(param)
            # self 已在上一行注入；接口签名恰恰最常显式写 `自`
            # （docs/L2_文言体语法规范_v4.0.md:590-591 的 `段 打印(自) -> 空`），
            # 不过滤会发射 `def 打印(self, 自)`。与 src 侧同一口径。
            if self._is_self_param(raw):
                continue
            params.append(self._sanitize_name(raw))
        params_str = ', '.join(params)

        has_body = bool(getattr(method, 'body', None))
        if not has_body:
            self._needs_abc = True
            self._add_line("@abstractmethod")

        ret_type = self._map_return_type(getattr(method, 'return_type', None))
        if ret_type:
            self._add_line(f"def {method_name}({params_str}) -> {ret_type}:")
        else:
            self._add_line(f"def {method_name}({params_str}):")

        self.indent_level += 1
        if has_body:
            emitted = len(self.output_lines)
            prev_in_function = self._in_function
            self._in_function = True
            try:
                for s in method.body:
                    self._generate_statement(s)
            finally:
                self._in_function = prev_in_function
            # 方法体可能全是注释等不产出代码的节点，兜底补 pass
            if len(self.output_lines) == emitted:
                self._add_line("pass")
        else:
            self._add_line("pass")
        self.indent_level -= 1

    def _generate_class(self, cls):
        """生成类定义"""
        name = self._sanitize_name(cls.name)
        
        # 处理继承
        #
        # 与 src 后端 code_generator.py:2249 同口径：基类 = base_classes + interfaces。
        # 这里还必须兼容 legacy v2 AST 的 `superclasses`（src/ast_nodes.py）——改动前
        # 只读后者，而 v3 生产路径的 ClassDefinition（ast_nodes_v3.py 的 __slots__
        # 里根本没有 superclasses）永远落空，于是 `类 犬 继承 动物：` 被静默发成
        # `class 犬:`：继承关系整个消失，方法解析、`父.构造(...)`（super().__init__）
        # 全部退化成 object.__init__ → TypeError。全仓 12 处 `继承` 在踩。
        bases = []
        raw_bases = list(getattr(cls, 'base_classes', None) or [])
        raw_bases += list(getattr(cls, 'superclasses', None) or [])
        raw_bases += list(getattr(cls, 'interfaces', None) or [])
        for base in raw_bases:
            if isinstance(base, str):
                bases.append(self._sanitize_name(base))
            elif hasattr(base, 'name'):
                bases.append(self._sanitize_name(base.name))
        # 去重保序：`继承` 与 interfaces 叠加时可能重复，重复基类 → TypeError
        bases = list(dict.fromkeys(bases))
        
        bases_str = ', '.join(bases) if bases else ''
        
        # 类定义
        if bases_str:
            self._add_line(f"class {name}({bases_str}):")
        else:
            self._add_line(f"class {name}:")
        
        self.indent_level += 1
        
        # 生成字段（只在构造函数中初始化，不在类体级别）
        # 属性声明如"属性 名称"只是声明，实际赋值在构造函数中进行
        # 只生成有默认值的字段
        if hasattr(cls, 'fields') and cls.fields:
            for field in cls.fields:
                if is_instance(field, 'VariableDeclaration') or is_instance(field, 'AttributeDeclaration'):
                    # 只有有默认值的字段才在类体级别生成
                    if hasattr(field, 'default_value') and field.default_value is not None:
                        field_name = self._sanitize_name(field.name)
                        value_code = self._generate_expr(field.default_value)
                        self._add_line(f"self.{field_name} = {value_code}")
        
        # 生成构造函数（dedicated 语法路径，如 parser 产出的 ConstructorDefinition）
        emitted_init = False
        if hasattr(cls, 'constructor') and cls.constructor:
            self._generate_constructor(cls.constructor)
            emitted_init = True

        # 生成方法
        if hasattr(cls, 'methods') and cls.methods:
            for method in cls.methods:
                is_ctor = self._is_ctor_method(method)
                if is_ctor and emitted_init:
                    # 同一个类里同时出现 `构造 接收 …`（已归一成 __init__）和
                    # `段 构造(…)`：改名后两者都叫 __init__，后者会在 Python 里
                    # **静默覆盖**前者。不静默丢——落成注释把冲突摊开。
                    self._add_line(
                        f"# 警告：类 {name} 重复定义构造函数，已忽略「段 {getattr(method, 'name', '?')}」"
                    )
                    continue
                if is_ctor:
                    emitted_init = True
                self._generate_method(method)
        
        self.indent_level -= 1
        self._add_line("")
    
    def _generate_constructor(self, constructor):
        """生成构造函数"""
        params = ['self']
        if hasattr(constructor, 'parameters'):
            for param in constructor.parameters:
                params.append(self._sanitize_name(param.name))
        
        params_str = ', '.join(params)
        self._add_line(f"def __init__({params_str}):")
        
        old_in_function = self._in_function
        old_in_class_method = self._in_class_method
        self._in_function = True
        self._in_class_method = True
        self.indent_level += 1
        
        # 不自动调用父类构造函数，让用户在构造函数体中显式处理
        # 如果父类没有构造函数，这会导致问题，所以需要检查父类是否需要初始化
        # 简化方案：不调用super().__init__()，由构造函数体中的语句决定
        

        # 生成构造函数体（用户自己写赋值语句）
        if hasattr(constructor, 'body') and constructor.body:
            for s in constructor.body:
                self._generate_statement(s)
        
        self.indent_level -= 1
        self._in_function = old_in_function
        self._in_class_method = old_in_class_method
    
    def _generate_method(self, method):
        """生成方法定义

        定义侧改名的两条规则，均与 src 后端 code_generator.py::_generate_method
        (:2715-2730) 同口径：
          ① 构造名（构造 / 初始化 / 构，或 is_constructor=True）→ __init__
          ② 协议魔术名（__迭代__ / __下一项__ / __进入__ / __退出__）→ Python dunder

        ① 的缺失是硬崩点：parser 只把 `构造 接收 …` 归一成 __init__，**不**处理
        `段 构造(…)`（后者 MethodDefinition.name 仍是 '构造'）。于是 unified 下
        `类 犬: 段 构造(名, 岁)` 发成 `def 构造(self, 名, 岁)`，实例化的 `犬(名=…, 岁=…)`
        走 object.__init__ → 运行期 `TypeError: 犬() takes no arguments`。
        `段 构造` 全仓 11 处、`段 初始化` 1 处在用，危害面覆盖所有走 unified 的 OOP 代码。
        """
        raw_name = getattr(method, 'name', '')
        name = self._sanitize_name(raw_name)

        # ① 构造函数名映射（用 raw_name 判定，_CTOR_NAMES 是中文名不受 sanitize 影响）
        if self._is_ctor_method(method):
            name = '__init__'

        # ② 协议魔术方法名映射（__init__ 不在表内，原样返回）
        name = self._PROTOCOL_METHOD_MAP.get(name, name)

        # 方法参数（第一个是self）
        params = ['self']
        if hasattr(method, 'parameters'):
            for param in method.parameters:
                params.append(self._sanitize_name(param.name))
        
        params_str = ', '.join(params)
        
        # 方法定义
        self._add_line(f"def {name}({params_str}):")
        
        old_in_function = self._in_function
        old_in_class_method = self._in_class_method
        self._in_function = True
        self._in_class_method = True
        self.indent_level += 1
        if hasattr(method, 'body') and method.body:
            for s in method.body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
        self._in_function = old_in_function
        self._in_class_method = old_in_class_method
    
    # L-045：输出类内置目标（写 族），与 code_generator.py 的 _OUTPUT_TARGETS 同口径。
    _OUTPUT_TARGETS = frozenset({
        '_light_builtin.写入输出',
        '_light_builtin.写入错误',
        '_light_builtin.打印错误',
        'print',
    })

    # L-055：write 族要求值必须是 str（写入输出/写入错误），print 族接受任意类型。
    _WRITE_NEEDS_STR = frozenset({
        '_light_builtin.写入输出',
        '_light_builtin.写入错误',
    })

    def _try_merge_output_concat(self, expr):
        """L-045/L-055：检测「输出类内置调用」形态并合并为整体写出。

        L-045 形态①（BinaryOp 拼接尾巴）：`写 "x=" + 标签` 被 parser 拆成
        BinaryOp(写("x=") + 标签)，直接生成是 `写入输出("x=") + 标签`（写返回
        None → TypeError）。这里合并成 `输出目标(str(整条拼接表达式))`。

        L-055 形态②（裸函数调用实参）：`写 f(x)` 被解析成
        FunctionCallExpr(callee=写(f), args=[x])，直接生成是 `写入输出(f)(x)`
        （f 当值传给 write、x 被丢成对 write 结果的调用）。合并成
        `输出目标(str(f(x)))`——正确传递函数调用结果并自动 str()。

        L-055 形态③（写族裸调用 + 非字符串实参）：`写 n`（n 为 int）直接生成
        `写入输出(n)` → write() argument must be str, not int。非字符串字面量实参
        自动包 str()；字符串字面量保持原样。

        非该形态（或输出名与用户函数重名）返回 None，调用方走常规生成。
        """
        def _resolve_call_name(node):
            raw = node.name
            if isinstance(raw, str):
                return self._resolve_name(raw)
            if is_instance(raw, 'Identifier') or hasattr(raw, 'name'):
                return self._resolve_name(getattr(raw, 'name', ''))
            return None

        def _call_args(node):
            return getattr(node, 'arguments', None) or getattr(node, 'args', None) or []

        # 形态③：写族 ParagraphCall/FunctionCall 裸调用（`写 n` / `写 表达式`）。
        if is_instance(expr, 'ParagraphCall') or is_instance(expr, 'FunctionCall'):
            func_name = _resolve_call_name(expr)
            if func_name is None or func_name in self.user_functions:
                return None
            target = self.builtin_map.get(func_name)
            if target not in self._OUTPUT_TARGETS:
                return None
            args = _call_args(expr)
            if len(args) != 1:
                return None
            arg = args[0]
            arg_str = self._generate_expr(arg)
            if is_instance(arg, 'StringLiteral') or target not in self._WRITE_NEEDS_STR:
                return f"{target}({arg_str})"
            return f"{target}(str({arg_str}))"

        # 形态②：FunctionCallExpr(callee=写族ParagraphCall)（`写 f(x)`）。
        if is_instance(expr, 'FunctionCallExpr'):
            callee = expr.callee
            if not (is_instance(callee, 'ParagraphCall') or is_instance(callee, 'FunctionCall')):
                return None
            func_name = _resolve_call_name(callee)
            if func_name is None or func_name in self.user_functions:
                return None
            target = self.builtin_map.get(func_name)
            if target not in self._OUTPUT_TARGETS:
                return None
            cargs = _call_args(callee)
            if not cargs:
                return None
            inner = self._generate_expr(cargs[0])
            # L-055 补：`写 转字符串(3)` 的 f 是裸 Identifier（_resolve_name 不查
            # builtin_map，返回原名），内置名裸引用会运行期 NameError；
            # 对内置名补 _light_builtin. 前缀，用户函数/局部变量保持原样。
            _fnode = cargs[0]
            _fname = getattr(_fnode, 'name', None)
            if (is_instance(_fnode, 'Identifier') and isinstance(_fname, str)
                    and _fname in self.builtin_map
                    and _fname not in self.user_functions):
                inner = self.builtin_map[_fname]
            tail = self._translate_args(getattr(expr, 'args', []))
            _call_txt = f"{inner}({', '.join(tail)})"
            if target in self._WRITE_NEEDS_STR:
                _call_txt = f"str({_call_txt})"
            return f"{target}({_call_txt})"

        # 形态①：BinaryOp 拼接尾巴（既有 L-045）。
        node = expr
        while is_instance(node, 'BinaryOp'):
            node = node.left
        if not (is_instance(node, 'ParagraphCall') or is_instance(node, 'FunctionCall')):
            return None
        func_name = _resolve_call_name(node)
        if func_name is None or func_name in self.user_functions:
            return None
        target = self.builtin_map.get(func_name)
        if target not in self._OUTPUT_TARGETS:
            return None
        args = _call_args(node)
        if not args:
            return None
        if node is expr:
            return None
        merged = self._gen_write_merged(expr, node)
        if target in self._WRITE_NEEDS_STR:
            return f"{target}(str({merged}))"
        return f"{target}({merged})"
    def _gen_write_merged(self, expr, write_call):
        """把 expr 中的 write_call（二叉链最左叶）替换为其首个实参后生成表达式。"""
        if expr is write_call:
            args = getattr(write_call, 'arguments', None) or getattr(write_call, 'args', None) or []
            return self._generate_expr(args[0])
        if is_instance(expr, 'BinaryOp'):
            left = self._gen_write_merged(expr.left, write_call)
            right = self._gen_write_merged(expr.right, write_call)
            if expr.operator == '@@contains@@':
                return f"({right} in {left})"
            op = self.operator_map.get(expr.operator, expr.operator)
            return f"({left} {op} {right})"
        return self._generate_expr(expr)

    def _translate_args(self, args):
        """把实参列表翻译成 Python 实参片段，支持关键字参数（KeywordArg）。

        对齐 code_generator.py 的各调用分支（FunctionCallExpr / MethodCall /
        MemberAccess / NewExpression）：`KeywordArg(name, value)` 应发射成
        `name=_generate_expr(value)`，而不是把 KeywordArg 对象原样 str() 出来。

        单 B·bug A 修复：unified 此前对每个实参直接 `_generate_expr`、漏了 KeywordArg
        分支，导致 `狗(名="阿黄")` 发射成 `狗(KeywordArg(名="阿黄"))` 这种非法
        Python（运行期 NameError / SyntaxError）。这里集中处理，避免 5 处实参
        遍历各自再写一遍。"""
        parts = []
        for arg in args:
            if is_instance(arg, 'KeywordArg'):
                parts.append(f"{arg.name}={self._generate_expr(arg.value)}")
            else:
                parts.append(self._generate_expr(arg))
        return parts

    def _generate_expr(self, expr):
        """生成表达式"""
        if expr is None:
            return "None"
        
        node_type = type(expr).__name__
        
        # 字面量
        if is_instance(expr, 'NumberLiteral'):
            return str(expr.value)
        
        elif is_instance(expr, 'StringLiteral'):
            # 字节串（v7 新单 H）：与 src 后端同口径，必须发 b'...'。
            # 非 ASCII 要转 \xNN（`b"中文"` 是 SyntaxError），交给 repr(bytes) 保证。
            if getattr(expr, 'is_bytes', False):
                return repr(expr.value.encode('utf-8'))
            return repr(expr.value)

        
        elif is_instance(expr, 'BooleanLiteral'):
            return 'True' if expr.value else 'False'
        
        elif is_instance(expr, 'NullLiteral'):
            return "None"
        
        # 标识符
        elif is_instance(expr, 'Identifier'):
            # 己 → self / 己.attr → self.attr（仅类方法内），对齐 code_generator.py:2041-2046
            return self._resolve_name(expr.name)
        
        elif is_instance(expr, 'SegmentName'):
            # 粘连的自身方法调用会以 SegmentName('己.方法') 出现，同样需要映射
            return self._resolve_name(expr.name)
        
        # 二元运算
        elif is_instance(expr, 'BinaryOp'):
            # L-045：写/印/显示 的输出实参拼接被 parser 拆成 输出(首参) op 尾巴，
            # 合并为 输出(整条表达式)，与 src 后端同口径。
            _merged = self._try_merge_output_concat(expr)
            if _merged is not None:
                return _merged
            left = self._generate_expr(expr.left)
            right = self._generate_expr(expr.right)
            op = self.operator_map.get(expr.operator, expr.operator)
            
            # ========== 常量折叠优化 ==========
            # 如果两个操作数都是数字常量，在编译时计算结果
            try:
                left_val = expr.left.value if hasattr(expr.left, 'value') else None
                right_val = expr.right.value if hasattr(expr.right, 'value') else None
                
                # 纯数字运算常量折叠
                if (left_val is not None and right_val is not None and
                    isinstance(left_val, (int, float)) and
                    isinstance(right_val, (int, float)) and
                    op in ('+', '-', '*', '/', '%', '**')):
                    if op == '+':
                        result = left_val + right_val
                    elif op == '-':
                        result = left_val - right_val
                    elif op == '*':
                        result = left_val * right_val
                    elif op == '/':
                        result = left_val / right_val
                    elif op == '%':
                        result = left_val % right_val
                    elif op == '**':
                        result = left_val ** right_val
                    return str(result)
            except (TypeError, ZeroDivisionError):
                pass  # 运行时错误，保持原样
            
            # 字符串字面量拼接常量折叠
            if (op == '+' and expr.operator in ['+', '加'] and
                hasattr(expr.left, 'value') and isinstance(expr.left.value, str) and
                hasattr(expr.right, 'value') and isinstance(expr.right.value, str)):
                return repr(expr.left.value + expr.right.value)
            # ========== 常量折叠优化结束 ==========

            # 处理包含关系：左包含右 → right in left
            if expr.operator == '@@contains@@':
                return f"({right} in {left})"

            # 处理加法：如果任一操作数是字符串，需要进行类型转换
            if op == '+' and expr.operator in ['+', '加']:
                expr_type = self.type_cache.get(id(expr))
                left_type = self.type_cache.get(id(expr.left))
                right_type = self.type_cache.get(id(expr.right))
                
                if isinstance(expr_type, StringType):
                    # 结果是字符串，需要确保两边都是字符串
                    if not isinstance(left_type, StringType):
                        left = f"str({left})"
                    if not isinstance(right_type, StringType):
                        right = f"str({right})"
            
            return f"({left} {op} {right})"
        
        # 一元运算
        elif is_instance(expr, 'UnaryOp'):
            operand = self._generate_expr(expr.operand)
            # 中文运算符映射
            unary_op_map = {
                '非': 'not ',
                '不是': 'not ',
                '-': '-',
            }
            op = unary_op_map.get(expr.operator, expr.operator)
            return f"({op}{operand})"
        
        # 函数调用
        elif is_instance(expr, 'FunctionCall') or is_instance(expr, 'ParagraphCall'):
            # L-055：写族裸调用 写 n / 写 表达式 —— 非字符串实参自动 str()（形态③）。
            _merged = self._try_merge_output_concat(expr)
            if _merged is not None:
                return _merged
            # 正确处理函数名（可能是 PropertyAccess、Identifier 等）
            func_expr = expr.name
            if is_instance(func_expr, 'PropertyAccess'):
                # 方法调用：obj.method(args)
                obj = self._generate_expr(func_expr.obj)
                method_name = func_expr.property_name
                # 中文方法名映射到 Python 方法名
                method_map = {
                    '清空': 'clear', '追加': 'append', '弹出': 'pop',
                    '排序': 'sort', '反转': 'reverse', '拷贝': 'copy',
                    '长度': '__len__', '获取': 'get', '设置': 'update',
                    '删除': 'remove', '包含': '__contains__',
                    # 单 B·修复3 的 unified 侧对齐：调用侧 构造/初始化 -> __init__，
                    # 与 code_generator.py 的 MemberAccess 分支（member in _CTOR_NAMES）
                    # 同口径。否则 `父之构造(...)` 在 unified 里发 `父.构造(...)`，
                    # 运行期 AttributeError —— 与 src 侧分叉。
                    # `构` 是 L0 v4.0 单字构造写法（examples/L0_core/06_...），同口径。
                    '构造': '__init__', '初始化': '__init__', '构': '__init__',
                }
                mapped_method = method_map.get(method_name, method_name)
                func_name = f"{obj}.{mapped_method}"
            elif is_instance(func_expr, 'Identifier'):
                func_name = self._resolve_name(func_expr.name)
            elif hasattr(func_expr, 'name'):
                # SegmentName 等：粘连写法 己方法() 会以 SegmentName('己.方法') 出现
                func_name = self._resolve_name(func_expr.name)
            elif isinstance(func_expr, str):
                # 部分解析路径直接把被调名放成字符串（可能是 '己.方法'）
                func_name = self._resolve_name(func_expr)
            else:
                func_name = self._generate_expr(func_expr)
            
            # 检查是否是内置函数（用户定义的函数优先）
            if func_name not in self.user_functions and func_name in self.builtin_map:
                func_name = self.builtin_map[func_name]
            
            args = self._translate_args(getattr(expr, 'arguments', None) or getattr(expr, 'args', []))
            args_str = ', '.join(args)
            return f"{func_name}({args_str})"

        # 链式函数调用（v3 后端 AST）：callee(args)，如 表["甲"](1)
        # L-014：与 code_generator.py 的 FunctionCallExpr 分支同构，语句/表达式两层都要能生成。
        elif is_instance(expr, 'FunctionCallExpr'):
            # L-055：写 f(x) 裸函数调用实参 —— 合并为 输出(str(f(x)))（形态②）。
            _merged = self._try_merge_output_concat(expr)
            if _merged is not None:
                return _merged
            callee = self._generate_expr(expr.callee)
            args = self._translate_args(getattr(expr, 'args', []))
            args_str = ', '.join(args)
            return f"{callee}({args_str})"
        
        # 成员访问（方法调用 / 属性读取）—— 单 B·Gap B 修复：
        # `结果.追加(...)` 这种「成员方法调用」在 unified 里被解析为 MemberAccess 节点，
        # 此前 _generate_expr 缺此分支（默认 return str(expr) 输出垃圾对象地址）。
        # 对齐 code_generator.py:3219 的 MemberAccess 分支，及本文件 FunctionCall/
        # PropertyAccess 分支（1633-1651）的方法名映射口径。
        elif is_instance(expr, 'MemberAccess'):
            obj = self._generate_expr(expr.obj)
            member = self._sanitize_name(expr.member)
            # 与 FunctionCall/PropertyAccess 分支同口径的方法名映射
            method_map = {
                '清空': 'clear', '追加': 'append', '弹出': 'pop',
                '排序': 'sort', '反转': 'reverse', '拷贝': 'copy',
                '长度': '__len__', '获取': 'get', '设置': 'update',
                '删除': 'remove', '包含': '__contains__',
                '构造': '__init__', '初始化': '__init__', '构': '__init__',
            }
            mapped_member = method_map.get(expr.member, member)
            if getattr(expr, 'is_method_call', False):
                args = self._translate_args(getattr(expr, 'args', None) or [])
                args_str = ', '.join(args)
                # 父.构造(...) -> super().__init__(...)：与 FunctionCall/PropertyAccess 同口径
                if obj == 'super()' and expr.member in ('构造', '初始化', '构'):
                    return f"super().__init__({args_str})"
                return f"{obj}.{mapped_member}({args_str})"
            return f"{obj}.{mapped_member}"
        
        # 属性访问
        elif is_instance(expr, 'PropertyAccess'):
            obj = self._generate_expr(expr.obj)
            # 特殊处理：长度 -> len()
            if expr.property_name == '长度':
                if hasattr(expr, 'obj') and is_instance(expr.obj, 'FunctionCall'):
                    return f"len({obj})"
                return f"len({obj})"
            return f"{obj}.{expr.property_name}"
        
        # 索引访问
        elif is_instance(expr, 'IndexAccess'):
            obj = self._generate_expr(expr.obj)
            index = self._generate_expr(expr.index)
            return f"{obj}[{index}]"
        
        # 列表字面量
        elif is_instance(expr, 'ListLiteral'):
            elements = [self._generate_expr(e) for e in expr.elements]
            return f"[{', '.join(elements)}]"
        
        # 字典字面量
        elif is_instance(expr, 'DictLiteral'):
            entries = []
            raw = getattr(expr, 'entries', None) or getattr(expr, 'elements', None) or []
            for entry in raw:
                if isinstance(entry, (tuple, list)) and len(entry) == 2:
                    key, value = entry
                    if key is None:
                        # **展开（_convert_dict_literal 以 (None, expr) 表示）
                        entries.append(f"**{self._generate_expr(value)}")
                    else:
                        # L-063：裸 Identifier 键转字符串键（unified 后端无绑定表，
                        # 统一 JS 风格；SRC 后端对已绑定名字保留变量键）。需要变量键
                        # 时请用字典推导式 / ** 展开 / 计算表达式。
                        if type(key).__name__ == 'Identifier':
                            entries.append(f"'{key.name}': {self._generate_expr(value)}")
                        else:
                            entries.append(f"{self._generate_expr(key)}: {self._generate_expr(value)}")
                elif hasattr(entry, 'key') and hasattr(entry, 'value'):
                    if type(entry.key).__name__ == 'Identifier':
                        entries.append(f"'{entry.key.name}': {self._generate_expr(entry.value)}")
                    else:
                        entries.append(f"{self._generate_expr(entry.key)}: {self._generate_expr(entry.value)}")
                else:
                    entries.append(self._generate_expr(entry))
            return f"{{{', '.join(entries)}}}"
        
        # 范围表达式：1至10 -> range(1, 11), 1到10步2 -> range(1, 11, 2)
        elif is_instance(expr, 'RangeExpr'):
            start = self._generate_expr(expr.start)
            end = self._generate_expr(expr.end)
            # 光明的范围是包含结束值的，所以需要 +1
            if expr.step:
                step = self._generate_expr(expr.step)
                return f"range({start}, {end} + 1, {step})"
            else:
                return f"range({start}, {end} + 1)"
        
        # 类实例化
        elif is_instance(expr, 'NewExpression'):
            class_name = self._sanitize_name(expr.class_name)
            args = self._translate_args(getattr(expr, 'arguments', []))
            args_str = ', '.join(args)
            return f"{class_name}({args_str})"
        
        # 管道表达式
        elif is_instance(expr, 'PipeExpression'):
            exprs = [self._generate_expr(e) for e in expr.expressions]
            return '('.join(exprs) + ')' * (len(exprs) - 1)
        
        # 方法调用
        elif is_instance(expr, 'MethodCall'):
            obj = self._generate_expr(expr.obj)
            args = self._translate_args(getattr(expr, 'arguments', []))
            args_str = ', '.join(args)
            return f"{obj}.{expr.method}({args_str})"
        
        # Self引用
        elif is_instance(expr, 'SelfReference'):
            return "self"
        
        # 字符串插值
        elif is_instance(expr, 'StringInterpolation'):
            # 生成 f"str_part{expr_part}str_part"
            f_parts = []
            for part in expr.parts:
                if isinstance(part, str):
                    f_parts.append(part.replace('{', '{{').replace('}', '}}'))
                elif isinstance(part, tuple):
                    # 带格式说明符：(expr_node, format_spec)
                    f_parts.append('{' + self._generate_expr(part[0]) + ':' + part[1] + '}')
                else:
                    f_parts.append('{' + self._generate_expr(part) + '}')
            return 'f' + repr(''.join(f_parts))
        
        # 列表推导
        elif is_instance(expr, 'ListComprehension'):
            output = self._generate_expr(expr.expression)
            var = self._sanitize_name(expr.variable)
            iterable = self._generate_expr(expr.iterable)
            if expr.condition:
                cond = self._generate_expr(expr.condition)
                return f"[{output} for {var} in {iterable} if {cond}]"
            return f"[{output} for {var} in {iterable}]"
        
        # 匿名函数
        elif is_instance(expr, 'LambdaExpression'):
            params = ', '.join(self._sanitize_name(p.name) for p in expr.parameters)
            body = self._generate_expr(expr.body) if expr.body else "None"
            return f"lambda {params}: {body}"
        
        # 三元条件表达式
        elif is_instance(expr, 'ConditionalExpression'):
            condition = self._generate_expr(expr.condition)
            then_expr = self._generate_expr(expr.then_expr)
            if expr.else_expr:
                else_expr = self._generate_expr(expr.else_expr)
                return f"({then_expr} if {condition} else {else_expr})"
            else:
                return f"({then_expr} if {condition} else None)"
        
        # 字典推导
        elif is_instance(expr, 'DictComprehension'):
            key = self._generate_expr(expr.key_expr)
            val = self._generate_expr(expr.value_expr)
            var = self._sanitize_name(expr.variable)
            iterable = self._generate_expr(expr.iterable)
            if expr.condition:
                cond = self._generate_expr(expr.condition)
                return f"{{{key}: {val} for {var} in {iterable} if {cond}}}"
            return f"{{{key}: {val} for {var} in {iterable}}}"
        
        # 异步等待表达式
        elif is_instance(expr, 'AwaitExpression'):
            inner_code = self._generate_expr(expr.expression)
            return f"await {inner_code}"
        
        # 默认：尝试直接转换为字符串
        return str(expr)


# 保持向后兼容性：旧名称别名
CodeGenerator = UnifiedCodeGenerator
