"""
光明（Light）编程语言 - Python代码生成器

将光明AST转换为Python代码
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from typing import List, Optional, Dict
from light_parser_v3 import *
from keywords import VERB_ARITY
import ast_nodes as ast_nodes_module


# 需要导入新的AST节点类型
from light_parser_v3 import ImportStmt, ExportStmt, IndexAccess, SliceExpr, SetComprehension, TupleLiteral, BreakStmt, ContinueStmt, PassStmt, ClassInstantiation, MemberAccess, TryStmt, ThrowStmt, Parameter, ParameterList, StringInterpolation, ListComprehension, LambdaExpression, MatchStmt, MatchCase, MatchPattern, DictComprehension, DestructuringAssignment, WithStmt, DecoratorDefinition, DictLiteral, InterfaceDefinition, MethodSignature, IndexedAssignment, RangeExpr, FFILoadLibrary, FFIFunctionDecl, FFIStructDef, FFICallbackDef, FFICreateArray, FFISetArrayElement, FFIAllocMemory, FFIFreeMemory, FFISetPointerValue, FFISetErrno, FFITryCatch, FFIEnumDef, FFIUnionDef, FFICreateCallback, FFIVarArgsDecl, FFIStructByValue, FFILibraryPath, FFITypedefDef, FFIBitfieldDef, FFIFuncPtrDef, FFIDebugConfig, FFIPreprocessorDef
from ast_nodes_v3 import Assignment, TypeCheckToggleStmt, AwaitExpr, KeywordArg, IndexedCompoundAssignment, PassStmt, AssignmentExpression, SetLiteral, EmbedBlock


# =============================================================================
# 代码生成错误
# =============================================================================

class CodeGenError(Exception):
    """代码生成错误"""
    def __init__(self, message: str, node_type: str = None):
        self.message = message
        self.node_type = node_type
        msg = f"代码生成错误: {message}"
        if node_type:
            msg += f" (节点类型: {node_type})"
        super().__init__(msg)


# =============================================================================
# Python代码生成器
# =============================================================================

class PythonCodeGenerator:
    """光明到Python代码生成器"""
    
    def __init__(self):
        self.indent_level = 0
        self.indent_str = "    "  # 4空格缩进
        self.output_lines: List[str] = []
        self._indent_cache: Dict[int, str] = {}
        
        # 追踪导入的符号
        self._imported_symbols: set = set()
        
        # 是否需要导入 ABC/abstractmethod
        self._needs_abc = False
        
        # 运行时类型检查开关（默认关闭，零开销）
        self._runtime_type_check = False
        
        # 中文数字映射
        self.chinese_numbers = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '十': 10, '百': 100, '千': 1000, '万': 10000
        }
        
        # 类属性追踪（用于方法内自动添加 self. 前缀）
        self._class_attr_names: set = set()
        # 类方法名追踪（用于方法内自动添加 self. 前缀调用其他方法）
        self._class_method_names: set = set()
        self._in_class_method: bool = False
        # 用户自定义函数名追踪（避免内置函数映射覆盖用户定义）
        self._user_defined_functions: set = set()
        # 当前方法参数名追踪（避免将参数名误判为类属性）
        self._current_method_params: set = set()
        
        # 是否在函数/段落内部（控制 return 生成）
        self._in_function: bool = False
        
        # 是否在循环内部（控制 break/continue 生成）
        self._in_loop: bool = False
        
        # 方法名映射（中文到英文）
        self.method_name_map = {
            '追加': 'append',
            '添加': 'append',
            '长度': '__len__',
            '取长度': '__len__',
            '插入': 'insert',
            '删除': 'remove',
            '弹出': 'pop',
            '清空': 'clear',
            '反转': 'reverse',
            '排序': 'sort',
            '包含': '__contains__',
            '获取': 'get',
            '设置': '__setitem__',
            # 字符串方法
            '转大写': 'upper',
            '转小写': 'lower',
            '替换': 'replace',
            '截取': 'slice',
            '开头': 'startswith',
            '结尾': 'endswith',
            '去除空白': 'strip',
            '分割': 'split',
            '连接': 'join',
            '查找': 'find',
            '计数': 'count',
        }
        
        # 模块名映射（中文到Python模块）
        # 注意：有独立 stdlib 实现（含中文函数名）的模块不要映射到 Python 标准库
        self.module_name_map = {
        }
        
        # 运算符映射
        self.operator_map = {
            '+': '+',
            '-': '-',
            '*': '*',
            '/': '/',
            '>': '>',
            '<': '<',
            '==': '==',
            '!=': '!=',
            '>=': '>=',
            '<=': '<=',
            '加': '+',
            '减': '-',
            '乘': '*',
            '除': '/',
            '除以': '/',
            '整除': '//',  # 整数除法（对应Python的//）
            '模': '%',
            '幂': '**',
            '%': '%',
            '^': '**',
            '大于': '>',
            '小于': '<',
            '等于': '==',
            '不等于': '!=',
            '大于等于': '>=',
            '小于等于': '<=',
            '不小于': '>=',   # P2-3：比较运算符短形式
            '不大于': '<=',   # P2-3：比较运算符短形式
            '且': 'and',
            '与': 'and',
            '或': 'or',
            '非': 'not',
        }
        
        # 内置函数映射
        self.builtin_map = {
            # 基础函数
            '打印': 'print',
            '显示': 'print',
            '输出': 'print',
            '断言': '_light_assert',
            '读取': 'input',
            '长': 'len',
            '长度': 'len',
            '首': 'lambda x: x[0]',
            '末': 'lambda x: x[-1]',
            
            # 数学函数（P1-1：补全反向映射）
            '求和': 'sum',
            '求最大': 'max',
            '求最小': 'min',
            '最大值': 'max',
            '最小值': 'min',
            '绝对值': 'abs',
            '四舍五入': 'round',
            '次方': 'pow',
            '范围': 'range',
            '全部': 'all',
            '任意': 'any',
            '整数': 'int',
            '浮点数': 'float',
            '字符串': 'str',
            '列表': 'list',
            '字典': 'dict',
            '集合': 'set',
            '布尔': 'bool',
            '类型': 'type',
            '去重': 'lambda x: list(set(x))',
            
            # 文件I/O
            '读取文件': '_light_builtin.读取文件',
            '_读文件': '_light_builtin._读文件',
            '写入文件': '_light_builtin.写入文件',
            '追加文件': '_light_builtin.追加文件',
            '文件存在': '_light_builtin.文件存在',
            '目录存在': '_light_builtin.目录存在',
            '路径存在': '_light_builtin.路径存在',
            '创建目录': '_light_builtin.创建目录',
            '删除文件': '_light_builtin.删除文件',
            '删除目录': '_light_builtin.删除目录',
            '列出目录': '_light_builtin.列出目录',
            '文件大小': '_light_builtin.文件大小',
            
            # 路径操作
            '绝对路径': '_light_builtin.绝对路径',
            '连接路径': '_light_builtin.连接路径',
            '目录名': '_light_builtin.目录名',
            '文件名': '_light_builtin.文件名',
            '扩展名': '_light_builtin.扩展名',
            
            # 系统函数
            '环境变量': '_light_builtin.环境变量',
            '设置环境变量': '_light_builtin.设置环境变量',
            '参数列表': '_light_builtin.参数列表',
            '退出程序': '_light_builtin.退出程序',
            '当前目录': '_light_builtin.当前目录',
            '切换目录': '_light_builtin.切换目录',
            '执行命令': '_light_builtin.执行命令',

            # 标准输入输出
            '读取行': '_light_builtin.读取行',
            '读取N字节': '_light_builtin.读取N字节',
            '写入输出': '_light_builtin.写入输出',
            '打印输出': '_light_builtin.打印输出',
            '刷新输出': '_light_builtin.刷新输出',
            '写入错误': '_light_builtin.写入错误',
            '打印错误': '_light_builtin.打印错误',

            # JSON 处理
            '解析JSON': '_light_builtin.解析JSON',
            '序列化JSON': '_light_builtin.序列化JSON',
            '美化JSON': '_light_builtin.美化JSON',

            # 函数式编程
            '筛选': 'filter',
            '映射': 'map',
            '归约': 'functools.reduce',
            '折叠': 'functools.reduce',
            '排序': 'sorted',
            '反转': 'reversed',
            '枚举': 'enumerate',
            '打包': 'zip',

            # 文件操作
            '打开文件': 'open',

            # 字符串工具
            '转整数': '_light_builtin.转整数',
            '转浮点': '_light_builtin.转浮点',
            '转串': '_light_builtin.转字符串',
            '转字符串': '_light_builtin.转字符串',
            '到字符串': '_light_builtin.转字符串',
            '转换字符串': '_light_builtin.转字符串',
            '到数字': '_light_builtin.转浮点',
            '转数字': '_light_builtin.转浮点',
            '字符串长度': '_light_builtin.字符串长度',
            '字符串获取': '_light_builtin.字符串获取',
            '字符串包含': '_light_builtin.字符串包含',
            '包含': '_light_builtin.包含',
            '字符串替换': '_light_builtin.字符串替换',
            '字符串分割': '_light_builtin.字符串分割',
            '分割字符串': '_light_builtin.分割字符串',
            '连接字符串': '_light_builtin.连接字符串',
            '替换字符串': '_light_builtin.替换字符串',
            '去除空白': '_light_builtin.去除空白',
            '转大写': '_light_builtin.转大写',
            '转小写': '_light_builtin.转小写',
            '截取': '_light_builtin.截取',
            '子串': '_light_builtin.截取',
            '字符串截取': '_light_builtin.截取',
            '开头': '_light_builtin.开头',
            '结尾': '_light_builtin.结尾',
            '查找子串': '_light_builtin.查找子串',
            '替换字符串次数': '_light_builtin.替换字符串次数',
            '截取到末尾': '_light_builtin.截取到末尾',
            '字符串计数': '_light_builtin.字符串计数',
            '字符串重复': '_light_builtin.字符串重复',
            '字符串反转': '_light_builtin.字符串反转',
            '转标题': '_light_builtin.转标题',
            '去除左侧空白': '_light_builtin.去除左侧空白',
            '去除右侧空白': '_light_builtin.去除右侧空白',
            '字符串对齐居中': '_light_builtin.字符串对齐居中',
            '字符串对齐左': '_light_builtin.字符串对齐左',
            '字符串对齐右': '_light_builtin.字符串对齐右',
            
            # 列表工具
            '列': '_light_builtin.列',
            '列表长度': '_light_builtin.列表长度',
            '列表获取': '_light_builtin.列表获取',
            '列表追加': '_light_builtin.列表追加',
            '列表弹出': '_light_builtin.列表弹出',
            '列表排序': '_light_builtin.列表排序',
            '列表反转': '_light_builtin.列表反转',
            '列表包含': '_light_builtin.列表包含',
            '列表创建': '_light_builtin.列表创建',
            
            # 字典工具
            '字典': '_light_builtin.字典创建',
            '字典创建': '_light_builtin.字典创建',
            '字典设置': '_light_builtin.字典设置',
            '字典删除': '_light_builtin.字典删除',
            '字典键列表': '_light_builtin.字典键列表',
            '字典值列表': '_light_builtin.字典值列表',
            '字典项列表': '_light_builtin.字典项列表',
            '字典包含键': '_light_builtin.字典包含键',
            '字典获取': '_light_builtin.字典获取',
            
            # 类型检查
            '是整数': '_light_builtin.是整数',
            '是浮点': '_light_builtin.是浮点',
            '是字符串': '_light_builtin.是字符串',
            '是列表': '_light_builtin.是列表',
            '是字典': '_light_builtin.是字典',
            '是空': '_light_builtin.是空',
            
            # 日期时间
            '时间戳': '_light_builtin.时间戳',
            '格式化时间': '_light_builtin.格式化时间',

            # C FFI 指针/数组/错误处理
            '取地址': '_light_ffi.取地址',
            '解引用': '_light_ffi.解引用',
            '指针偏移': '_light_ffi.指针偏移',
            'FFI错误': '_light_ffi.获取FFI错误',
            '系统错误码': '_light_ffi.获取系统错误码',
            '设系统错误码': '_light_ffi.设系统错误码',
            '创建数组': '_light_ffi.创建数组',
            '设置数组': '_light_ffi.设置数组',
            '分配内存': '_light_ffi.分配内存',
            '释放内存': '_light_ffi.释放内存',
            '设指针值': '_light_ffi.设指针值',
            # C FFI 第三阶段
            '创建回调': '_light_ffi.创建回调函数',
            '创建结构体值': '_light_ffi.创建结构体值',
            '创建枚举': '_light_ffi.创建枚举',
            '创建联合体': '_light_ffi.创建联合体',
            '解析库路径': '_light_ffi.解析库路径',
            '变长参数调用': '_light_ffi.变长参数调用',
            '获取平台': '_light_ffi.获取平台',
            '查找库': '_light_ffi.查找库',
            '结构体大小': '_light_ffi.结构体大小',
            '字段偏移': '_light_ffi.字段偏移',
            '结构体转字节': '_light_ffi.结构体转字节',
            '字节转结构体': '_light_ffi.字节转结构体',
            # C FFI 第四阶段
            '注册回调': '_light_ffi.注册回调',
            '注销回调': '_light_ffi.注销回调',
            '获取回调': '_light_ffi.获取回调',
            'FFI调试': '_light_ffi.启用调试',
            'FFI禁用调试': '_light_ffi.禁用调试',
            'FFI获取日志': '_light_ffi.获取日志',
            '位域设置': '_light_ffi.位域设置',
            '位域获取': '_light_ffi.位域获取',
            '创建函数指针': '_light_ffi.创建函数指针',
            '创建类型别名': '_light_ffi.创建类型别名',
            '定义宏': '_light_ffi.定义宏',
            '获取宏': '_light_ffi.获取宏',
        }
    
    def generate(self, module: Module) -> str:
        """生成Python代码"""
        self.output_lines = []
        self.indent_level = 0  # 重置缩进级别，防止跨条目状态污染
        self._user_defined_functions = set()  # 重置用户自定义函数追踪
        
        # 添加文件头
        self._add_line("# 由光明编译器生成")
        self._add_line("# 源文件: 光明代码")
        self._add_line("")
        
        # 添加标准库导入
        self._add_line("import sys")
        self._add_line("import os")
        self._add_line("import ctypes")
        self._add_line("import stdlib.FFI as _light_ffi")
        self._add_line("from typing import Any")
        self._add_line("")
        self._add_line("try:")
        self._add_line("    import importlib.util")
        self._add_line("except ImportError:")
        self._add_line("    importlib = None")
        self._add_line("")
        self._add_line("# 解析 stdlib 路径（依次尝试多种可能）")
        self._add_line("_light_stdlib = None")
        self._add_line("try:")
        self._add_line("    _light_file_dir = os.path.dirname(os.path.abspath(__file__))")
        self._add_line("except NameError:")
        self._add_line("    _light_file_dir = None")
        self._add_line("for _try_path in [")
        self._add_line("    os.path.join(_light_file_dir, 'stdlib') if _light_file_dir else None,")
        self._add_line("    os.path.join(_light_file_dir, '..', 'stdlib') if _light_file_dir else None,")
        self._add_line("    os.path.join(os.getcwd(), 'stdlib'),")
        self._add_line("    os.path.normpath(os.path.join(_light_file_dir, '..', '..', 'stdlib')) if _light_file_dir else None,")
        self._add_line("]:")
        self._add_line("    if _try_path and os.path.isdir(_try_path):")
        self._add_line("        _light_stdlib = _try_path")
        self._add_line("        break")
        self._add_line("")
        self._add_line("if _light_stdlib and _light_stdlib not in sys.path:")
        self._add_line("    sys.path.insert(0, _light_stdlib)")
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
        self._add_line("        _light_builtin.读取文件 = lambda path: open(path, 'r', encoding='utf-8').read() if __import__('os').path.isfile(path) else ''")
        self._add_line("        _light_builtin._读文件 = lambda path: open(path, 'r', encoding='utf-8').read() if __import__('os').path.isfile(path) else ''")
        self._add_line("        _light_builtin.写入文件 = lambda path, content: open(path, 'w', encoding='utf-8').write(content) or None")
        self._add_line("        _light_builtin.删除文件 = lambda path: __import__('os').remove(path) if __import__('os').path.isfile(path) else None")
        self._add_line("        _light_builtin.删除目录 = lambda path: __import__('os').rmdir(path)")
        self._add_line("        _light_builtin.文件存在 = lambda path: __import__('os').path.isfile(path)")
        self._add_line("        _light_builtin.目录存在 = lambda path: __import__('os').path.isdir(path)")
        self._add_line("        _light_builtin.打印 = print")
        self._add_line("        _light_builtin.读取行 = lambda: sys.stdin.readline().rstrip('\\r\\n')")
        self._add_line("        _light_builtin.读取N字节 = lambda n: sys.stdin.read(n)")
        self._add_line("        _light_builtin.写入输出 = lambda t: (sys.stdout.write(t), sys.stdout.flush()) and None")
        self._add_line("        _light_builtin.打印输出 = lambda t: print(t, flush=True)")
        self._add_line("        _light_builtin.刷新输出 = lambda: sys.stdout.flush()")
        self._add_line("        _light_builtin.写入错误 = lambda t: (sys.stderr.write(t), sys.stderr.flush()) and None")
        self._add_line("        _light_builtin.打印错误 = lambda t: print(t, file=sys.stderr, flush=True)")
        self._add_line("        _light_builtin.解析JSON = lambda t: __import__('json').loads(t)")
        self._add_line("        _light_builtin.序列化JSON = lambda v, i=None: (__import__('json').dumps(v, ensure_ascii=False, indent=i) if i is not None else __import__('json').dumps(v, ensure_ascii=False))")
        self._add_line("        _light_builtin.美化JSON = lambda v: __import__('json').dumps(v, ensure_ascii=False, indent=2)")
        self._add_line("        _light_builtin.转字符串 = str")
        self._add_line("        _light_builtin.转整数 = int")
        self._add_line("        _light_builtin.转浮点 = float")
        self._add_line("        _light_builtin.chr = chr")
        self._add_line("        _light_builtin.bin = bin")
        self._add_line("        _light_builtin.hex = hex")
        self._add_line("        _light_builtin.oct = oct")
        self._add_line("        _light_builtin.列表创建 = list")
        self._add_line("        _light_builtin.列表长度 = len")
        self._add_line("        _light_builtin.列 = lambda *args: list(args)")
        self._add_line("        _light_builtin.列表追加 = lambda lst, item: lst.append(item)")
        self._add_line("        _light_builtin.列表包含 = lambda lst, item: item in lst")
        self._add_line("        _light_builtin.包含 = lambda sub, s: sub in s")
        self._add_line("        _light_builtin.字符串长度 = len")
        self._add_line("        _light_builtin.截取 = lambda s, start, end: s[start:end]")
        self._add_line("        _light_builtin.转大写 = lambda s: s.upper()")
        self._add_line("        _light_builtin.转小写 = lambda s: s.lower()")
        self._add_line("        _light_builtin.结尾 = lambda s, suffix: s.endswith(suffix)")
        self._add_line("        _light_builtin.开头 = lambda s, prefix: s.startswith(prefix)")
        self._add_line("        _light_builtin.字典创建 = dict")
        self._add_line("        _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})")
        self._add_line("        _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)")
        self._add_line("        _light_builtin.字典键列表 = lambda d: list(d.keys())")
        self._add_line("        _light_builtin.字典包含键 = lambda d, k: k in d")
        self._add_line("        _light_builtin.时间戳 = lambda: __import__('time').time()")
        self._add_line("        _light_builtin.格式化时间 = lambda t, f='%Y-%m-%d %H:%M:%S': __import__('datetime').datetime.fromtimestamp(t).strftime(f) if isinstance(t, (int, float)) else __import__('datetime').datetime.strptime(t, '%Y-%m-%d %H:%M:%S').strftime(f)")
        self._add_line("else:")
        self._add_line("    import types")
        self._add_line("    _light_builtin = types.ModuleType('_light_builtin')")
        self._add_line("    _light_builtin.打印 = print")
        self._add_line("    _light_builtin.读取行 = lambda: sys.stdin.readline().rstrip('\\n')")
        self._add_line("    _light_builtin.读取N字节 = lambda n: sys.stdin.read(n)")
        self._add_line("    _light_builtin.写入输出 = lambda t: (sys.stdout.write(t), sys.stdout.flush()) and None")
        self._add_line("    _light_builtin.打印输出 = lambda t: print(t, flush=True)")
        self._add_line("    _light_builtin.刷新输出 = lambda: sys.stdout.flush()")
        self._add_line("    _light_builtin.写入错误 = lambda t: (sys.stderr.write(t), sys.stderr.flush()) and None")
        self._add_line("    _light_builtin.打印错误 = lambda t: print(t, file=sys.stderr, flush=True)")
        self._add_line("    _light_builtin.解析JSON = lambda t: __import__('json').loads(t)")
        self._add_line("    _light_builtin.序列化JSON = lambda v, i=None: (__import__('json').dumps(v, ensure_ascii=False, indent=i) if i is not None else __import__('json').dumps(v, ensure_ascii=False))")
        self._add_line("    _light_builtin.美化JSON = lambda v: __import__('json').dumps(v, ensure_ascii=False, indent=2)")
        self._add_line("    _light_builtin.转字符串 = str")
        self._add_line("    _light_builtin.转整数 = int")
        self._add_line("    _light_builtin.转浮点 = float")
        self._add_line("    _light_builtin.chr = chr")
        self._add_line("    _light_builtin.bin = bin")
        self._add_line("    _light_builtin.hex = hex")
        self._add_line("    _light_builtin.oct = oct")
        self._add_line("    _light_builtin.列表创建 = list")
        self._add_line("    _light_builtin.列表长度 = len")
        self._add_line("    _light_builtin.列 = lambda *args: list(args)")
        self._add_line("    _light_builtin.列表追加 = lambda lst, item: lst.append(item)")
        self._add_line("    _light_builtin.列表包含 = lambda lst, item: item in lst")
        self._add_line("    _light_builtin.包含 = lambda sub, s: sub in s")
        self._add_line("    _light_builtin.字符串长度 = len")
        self._add_line("    _light_builtin.截取 = lambda s, start, end: s[start:end]")
        self._add_line("    _light_builtin.转大写 = lambda s: s.upper()")
        self._add_line("    _light_builtin.转小写 = lambda s: s.lower()")
        self._add_line("    _light_builtin.字典创建 = dict")
        self._add_line("    _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})")
        self._add_line("    _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)")
        self._add_line("    _light_builtin.字典键列表 = lambda d: list(d.keys())")
        self._add_line("    _light_builtin.字典包含键 = lambda d, k: k in d")
        self._add_line("    _light_builtin.时间戳 = lambda: __import__('time').time()")
        self._add_line("    _light_builtin.格式化时间 = lambda t, f='%Y-%m-%d %H:%M:%S': __import__('datetime').datetime.fromtimestamp(t).strftime(f) if isinstance(t, (int, float)) else __import__('datetime').datetime.strptime(t, '%Y-%m-%d %H:%M:%S').strftime(f)")
        self._add_line("")

        # 可空类型解包辅助函数：_light_unwrap(x) = assert x is not None; return x
        self._add_line("# 可空类型解包辅助函数")
        self._add_line("def _light_unwrap(_x):")
        self._add_line("    assert _x is not None, \"尝试解包空值\"")
        self._add_line("    return _x")
        self._add_line("")
        self._add_line("# 断言辅助函数")
        self._add_line("def _light_assert(_cond, _msg=''):")
        self._add_line("    if not _cond:")
        self._add_line("        raise AssertionError(_msg)")
        self._add_line("")

        # 生成语句
        for stmt in module.statements:
            self._generate_statement(stmt)
        
        # 如果第一行没有 from abc import ABC, abstractmethod，在前面插入
        # 查找第一个非空且非注释行的位置，在后面插入
        if self._needs_abc:
            abc_import = "from abc import ABC, abstractmethod"
            # 插入在文件头之后，第一个语句之前
            # 找到最后一个空行或注释后的位置
            insert_pos = 0
            for i, line in enumerate(self.output_lines):
                if line.startswith("#") or line == "":
                    insert_pos = i + 1
                else:
                    break
            self.output_lines.insert(insert_pos, "")
            self.output_lines.insert(insert_pos, abc_import)
        
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
    
    def _generate_statement(self, stmt: ASTNode):
        """生成语句"""
        if isinstance(stmt, VarDecl):
            self._generate_var_decl(stmt)
        elif isinstance(stmt, IfStmt):
            self._generate_if_stmt(stmt)
        elif isinstance(stmt, ForeachStmt):
            self._generate_foreach_stmt(stmt)
        elif isinstance(stmt, WhileStmt):
            self._generate_while_stmt(stmt)
        elif isinstance(stmt, Paragraph):
            self._generate_paragraph(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._generate_return_stmt(stmt)
        elif isinstance(stmt, ImportStmt):
            self._generate_import_stmt(stmt)
        elif isinstance(stmt, ast_nodes_module.ImportStatement):
            # 支持 ast_nodes.py 的 ImportStatement
            self._generate_import_statement(stmt)
        elif isinstance(stmt, ExportStmt):
            # 导出语句在Python中不需要生成代码
            # Python通过 __all__ 或直接定义来实现导出
            self._generate_export_stmt(stmt)
        elif isinstance(stmt, BreakStmt):
            if self._in_loop:
                self._add_line("break")
            else:
                self._add_line("pass")
        elif isinstance(stmt, ContinueStmt):
            if self._in_loop:
                self._add_line("continue")
            else:
                self._add_line("pass")
        elif isinstance(stmt, PassStmt):
            self._add_line("pass")
        elif isinstance(stmt, TypeCheckToggleStmt):
            # 类型检查开关
            self._runtime_type_check = stmt.enable
            action = "开启" if stmt.enable else "关闭"
            if stmt.enable:
                # 生成运行时类型检查辅助函数（仅一次）
                if not hasattr(self, '_type_check_helper_added'):
                    self._add_line("# 运行时类型检查已开启")
                    self._add_line("def _light_check_type(value, expected_type, var_name=''):")
                    self.indent_level += 1
                    self._add_line("actual_type = type(value).__name__")
                    self._add_line("type_map = {'int': '整数', 'float': '小数', 'str': '文本', 'bool': '布尔', 'list': '列表', 'dict': '字典', 'set': '集合', 'type(None)': '空'}")
                    self._add_line("actual_cn = type_map.get(actual_type, actual_type)")
                    self._add_line("if expected_type and actual_cn != expected_type and expected_type != '任意':")
                    self.indent_level += 1
                    self._add_line("raise TypeError(f'类型错误: 变量 {var_name} 期望类型 {expected_type}, 实际类型 {actual_cn}')")
                    self.indent_level -= 1
                    self._add_line("return value")
                    self.indent_level -= 1
                    self._type_check_helper_added = True
                else:
                    self._add_line(f"# {action}类型检查")
            else:
                self._add_line(f"# {action}类型检查")
        elif isinstance(stmt, TryStmt):
            self._generate_try_stmt(stmt)
        elif isinstance(stmt, ThrowStmt):
            self._generate_throw_stmt(stmt)
        elif isinstance(stmt, ParagraphCall):
            # 动词调用作为独立语句
            expr_code = self._generate_expr(stmt)
            self._add_line(expr_code)
        elif isinstance(stmt, Identifier):
            # 标识符作为独立语句：生成为段落调用（带括号）
            name = self._sanitize_name(stmt.name)
            self._add_line(f"{name}()")
        elif isinstance(stmt, BinaryOp):
            # 二元运算作为独立语句
            expr_code = self._generate_expr(stmt)
            self._add_line(expr_code)
        elif isinstance(stmt, Pipeline):
            # 管道操作作为独立语句
            expr_code = self._generate_expr(stmt)
            self._add_line(expr_code)
        elif isinstance(stmt, SelfAssignment):
            # self赋值语句
            self._generate_self_assignment(stmt)
        elif isinstance(stmt, CompoundAssignment):
            # 复合赋值语句：甲 加上 1 → 甲 += 1
            self._generate_compound_assignment(stmt)
        elif isinstance(stmt, IndexedCompoundAssignment):
            # 索引复合赋值：甲[丁] 加上 1 → 甲[丁] += 1
            self._generate_indexed_compound_assignment(stmt)
        elif isinstance(stmt, Assignment):
            # 普通赋值语句：甲 = 值
            target = self._generate_expr(stmt.target)
            value = self._generate_expr(stmt.value)
            self._add_line(f"{target} = {value}")
        elif isinstance(stmt, IndexedAssignment):
            # 索引赋值语句：甲[丁] = 值
            self._generate_indexed_assignment(stmt)
        elif isinstance(stmt, ClassDefinition):
            # 类定义
            self._generate_class_definition(stmt)
        elif isinstance(stmt, MemberAccess):
            # 成员访问作为独立语句
            expr_code = self._generate_expr(stmt)
            self._add_line(expr_code)
        elif isinstance(stmt, MatchStmt):
            # 模式匹配语句
            self._generate_match_stmt(stmt)
        elif isinstance(stmt, DestructuringAssignment):
            # 解构赋值：a, b = value
            vars_str = ', '.join(self._sanitize_name(v) for v in stmt.variables)
            value = self._generate_expr(stmt.value)
            self._add_line(f"{vars_str} = {value}")
        elif isinstance(stmt, WithStmt):
            # 上下文管理器
            self._generate_with_stmt(stmt)
        elif isinstance(stmt, DecoratorDefinition):
            # 装饰器定义
            self._generate_decorator_definition(stmt)
        elif isinstance(stmt, InterfaceDefinition):
            # 接口定义
            self._generate_interface_definition(stmt)
        elif isinstance(stmt, Parameter):
            # 参数声明（段落体内部）
            # 顶层参数声明是解析FFI时产生的多余语句，跳过
            pass
        elif isinstance(stmt, ParameterList):
            # 参数列表声明（段落体内部）
            # 顶层参数列表声明是解析FFI时产生的多余语句，跳过
            pass
        elif isinstance(stmt, FFILoadLibrary):
            self._generate_ffi_load_library(stmt)
        elif isinstance(stmt, FFIFunctionDecl):
            self._generate_ffi_function_decl(stmt)
        elif isinstance(stmt, FFIStructDef):
            self._generate_ffi_struct_def(stmt)
        elif isinstance(stmt, FFICallbackDef):
            self._generate_ffi_callback_def(stmt)
        elif isinstance(stmt, FFICreateArray):
            self._generate_ffi_create_array(stmt)
        elif isinstance(stmt, FFISetArrayElement):
            self._generate_ffi_set_array_element(stmt)
        elif isinstance(stmt, FFIAllocMemory):
            self._generate_ffi_alloc_memory(stmt)
        elif isinstance(stmt, FFIFreeMemory):
            self._generate_ffi_free_memory(stmt)
        elif isinstance(stmt, FFISetPointerValue):
            self._generate_ffi_set_pointer_value(stmt)
        elif isinstance(stmt, FFISetErrno):
            self._generate_ffi_set_errno(stmt)
        elif isinstance(stmt, FFITryCatch):
            self._generate_ffi_try_catch(stmt)
        elif isinstance(stmt, FFIEnumDef):
            self._generate_ffi_enum_def(stmt)
        elif isinstance(stmt, FFIUnionDef):
            self._generate_ffi_union_def(stmt)
        elif isinstance(stmt, FFIVarArgsDecl):
            self._generate_ffi_varargs_decl(stmt)
        elif isinstance(stmt, FFICreateCallback):
            self._generate_ffi_create_callback(stmt)
        elif isinstance(stmt, FFIStructByValue):
            self._generate_ffi_struct_by_value(stmt)
        elif isinstance(stmt, FFILibraryPath):
            self._generate_ffi_library_path(stmt)
        elif isinstance(stmt, FFITypedefDef):
            self._generate_ffi_typedef_def(stmt)
        elif isinstance(stmt, FFIBitfieldDef):
            self._generate_ffi_bitfield_def(stmt)
        elif isinstance(stmt, FFIFuncPtrDef):
            self._generate_ffi_funcptr_def(stmt)
        elif isinstance(stmt, FFIDebugConfig):
            self._generate_ffi_debug_config(stmt)
        elif isinstance(stmt, FFIPreprocessorDef):
            self._generate_ffi_preprocessor_def(stmt)
        elif isinstance(stmt, AwaitExpr):
            # 等待语句 → await expression
            inner = self._generate_expr(stmt.expression)
            self._add_line(f"await {inner}")
        elif type(stmt).__name__ == 'CForStmt':
            # C风格for循环
            self._generate_c_for_stmt(stmt)
        elif type(stmt).__name__ == 'Block':
            # 花括号代码块
            for s in stmt.statements:
                self._generate_statement(s)
        elif isinstance(stmt, (IndexAccess, MemberAccess, ParagraphCall)):
            # 表达式语句（如 obj[key].append(v) 或 obj.method()）
            expr_str = self._generate_expr(stmt)
            self._add_line(expr_str)
        elif isinstance(stmt, EmbedBlock):
            self._generate_embed_block(stmt)
        else:
            raise CodeGenError(f"未知语句类型", type(stmt).__name__)
    
    def _generate_var_decl(self, stmt: VarDecl):
        """生成变量声明"""
        name = self._sanitize_name(stmt.name)
        value = self._generate_expr(stmt.value)
        
        # 处理 己.xxx 形式的属性赋值
        if name.startswith('己.'):
            name = 'self.' + name[2:]
        
        type_annotation = ''
        if stmt.type_annotation:
            python_type = self._map_type(stmt.type_annotation)
            type_annotation = f': {python_type}'
        
        # 类方法中，如果变量是类属性，使用 self. 前缀
        if self._in_class_method and stmt.name in self._class_attr_names:
            self._add_line(f"self.{name}{type_annotation} = {value}")
        else:
            self._add_line(f"{name}{type_annotation} = {value}")
        
        # 运行时类型检查（仅在开启时生成）
        if self._runtime_type_check and stmt.type_annotation:
            light_type = stmt.type_annotation
            if self._in_class_method and stmt.name in self._class_attr_names:
                self._add_line(f"_light_check_type(self.{name}, '{light_type}', '{stmt.name}')")
            else:
                self._add_line(f"_light_check_type({name}, '{light_type}', '{stmt.name}')")
    
    def _map_type(self, light_type: str) -> str:
        """将光明类型名映射为Python类型名"""
        type_map = {
            '整数': 'int',
            '小数': 'float',
            '浮数': 'float',
            '文本': 'str',
            '串': 'str',
            '布尔': 'bool',
            '列表': 'list',
            '列': 'list',
            '字典': 'dict',
            '典': 'dict',
            '集合': 'set',
            '集': 'set',
            '任意': 'Any',
            '空': 'None',
            '数': 'float',
        }
        return type_map.get(light_type, light_type)
    
    def _generate_if_stmt(self, stmt: IfStmt):
        """生成条件语句"""
        condition = self._generate_expr(stmt.condition)
        self._add_line(f"if {condition}:")
        
        self.indent_level += 1
        if stmt.then_body:
            for s in stmt.then_body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
        
        if stmt.else_body:
            # 处理否则如果链（else_body 是 IfStmt）
            if isinstance(stmt.else_body, IfStmt):
                self._generate_elif(stmt.else_body)
            elif isinstance(stmt.else_body, list):
                self._add_line("else:")
                self.indent_level += 1
                for s in stmt.else_body:
                    self._generate_statement(s)
                self.indent_level -= 1
    
    def _generate_elif(self, stmt: IfStmt):
        """生成否则如果（elif）分支"""
        condition = self._generate_expr(stmt.condition)
        self._add_line(f"elif {condition}:")
        
        self.indent_level += 1
        if stmt.then_body:
            for s in stmt.then_body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
        
        if stmt.else_body:
            # 进一步嵌套的否则如果链
            if isinstance(stmt.else_body, IfStmt):
                self._generate_elif(stmt.else_body)
            elif isinstance(stmt.else_body, list):
                self._add_line("else:")
                self.indent_level += 1
                for s in stmt.else_body:
                    self._generate_statement(s)
                self.indent_level -= 1
    
    def _generate_foreach_stmt(self, stmt: ForeachStmt):
        """生成遍历循环"""
        var_name = self._sanitize_name(stmt.variable)
        iterable = self._generate_expr(stmt.iterable)
        
        for_keyword = "async for" if getattr(stmt, 'is_async', False) else "for"
        self._add_line(f"{for_keyword} {var_name} in {iterable}:")
        
        old_in_loop = self._in_loop
        self._in_loop = True
        self.indent_level += 1
        if stmt.body:
            for s in stmt.body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
        self._in_loop = old_in_loop
    
    def _generate_while_stmt(self, stmt: WhileStmt):
        """生成当循环"""
        condition = self._generate_expr(stmt.condition)
        
        self._add_line(f"while {condition}:")
        
        old_in_loop = self._in_loop
        self._in_loop = True
        self.indent_level += 1
        if stmt.body:
            for s in stmt.body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
        self._in_loop = old_in_loop
    
    def _generate_c_for_stmt(self, stmt):
        """生成C风格for循环：init; while(cond){ body; incr; }"""
        # 生成初始化语句
        if stmt.init:
            self._generate_statement(stmt.init)
        # 生成while循环
        condition = self._generate_expr(stmt.condition) if stmt.condition else 'True'
        self._add_line(f"while {condition}:")
        old_in_loop = self._in_loop
        self._in_loop = True
        self.indent_level += 1
        if stmt.body:
            for s in stmt.body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        # 生成增量语句
        if stmt.increment:
            self._generate_statement(stmt.increment)
        self.indent_level -= 1
        self._in_loop = old_in_loop
        self._add_line("")

    def _generate_paragraph(self, stmt: Paragraph):
        """生成段落定义"""
        name = self._sanitize_name(stmt.name)
        
        # 从段落体中提取参数声明
        params = []
        body_without_params = []
        for s in (stmt.body or []):
            if isinstance(s, Parameter):
                params.append({'name': self._sanitize_name(s.name), 'type': s.type_annotation})
            elif isinstance(s, ParameterList):
                for param_name in s.params:
                    params.append({'name': self._sanitize_name(param_name), 'type': None})
            else:
                body_without_params.append(s)
        
        # 如果段落头有参数定义，也加入
        for param in (stmt.params or []):
            param_name = self._sanitize_name(param['name'])
            param_type = param.get('type')
            existing = next((p for p in params if p['name'] == param_name), None)
            if existing:
                if param_type:
                    existing['type'] = param_type
            else:
                params.append({'name': param_name, 'type': param_type})
        
        # 生成带类型注解的参数列表
        params_parts = []
        for p in params:
            if p['type']:
                python_type = self._map_type(p['type'])
                params_parts.append(f"{p['name']}: {python_type}")
            else:
                params_parts.append(p['name'])
        
        params_str = ', '.join(params_parts) if params_parts else ''
        
        # 生成返回类型注解
        return_type_annotation = ''
        if stmt.return_type:
            python_return_type = self._map_type(stmt.return_type)
            return_type_annotation = f" -> {python_return_type}"
        
        # 函数定义
        def_prefix = "async def" if '异步' in (stmt.modifiers or []) else "def"
        self._add_line(f"{def_prefix} {name}({params_str}){return_type_annotation}:")
        
        # 记录用户自定义函数名，避免内置函数映射覆盖
        self._user_defined_functions.add(stmt.name)
        
        old_in_function = self._in_function
        self._in_function = True
        self.indent_level += 1
        if body_without_params:
            for s in body_without_params:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
        self._in_function = old_in_function
        
        self._add_line("")
    
    def _generate_return_stmt(self, stmt: ReturnStmt):
        """生成返回语句

        模块级 return 在 Python 中非法，仅在函数/段落内部生成 return。
        否则将返回值作为裸表达式输出（用于 REPL 或模块级执行）。
        """
        if self._in_function:
            if stmt.value:
                value = self._generate_expr(stmt.value)
                self._add_line(f"return {value}")
            else:
                self._add_line("return")
        else:
            # 模块级：将返回值作为表达式输出，不生成 return
            if stmt.value:
                value = self._generate_expr(stmt.value)
                self._add_line(f"print({value})")
            else:
                self._add_line("pass")
    
    def _generate_try_stmt(self, stmt: TryStmt):
        """生成异常捕获语句"""
        # try块
        self._add_line("try:")
        self.indent_level += 1
        if stmt.try_body:
            for s in stmt.try_body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
        
        # except块
        if stmt.catch_body:
            if stmt.catch_type == '外部错误':
                # FFI 外部错误处理
                if stmt.catch_var:
                    self._add_line(f"except (ctypes.ArgumentError, OSError, RuntimeError) as {stmt.catch_var}:")
                else:
                    self._add_line("except (ctypes.ArgumentError, OSError, RuntimeError):")
            elif stmt.catch_type and stmt.catch_var:
                # 捕获指定类型 + 变量：except 值错误 as 错误:
                # 支持多类型捕获：(Type1, Type2) 格式
                ct = stmt.catch_type
                if ',' in ct:
                    ct = f"({ct})"
                self._add_line(f"except {ct} as {stmt.catch_var}:")
            elif stmt.catch_type:
                # 捕获指定类型无变量：except 值错误:
                ct = stmt.catch_type
                if ',' in ct:
                    ct = f"({ct})"
                self._add_line(f"except {ct}:")
            elif stmt.catch_var:
                # 无类型有变量（向后兼容）：except Exception as 错误:
                self._add_line(f"except Exception as {stmt.catch_var}:")
            else:
                # 无类型无变量：except Exception:
                self._add_line("except Exception:")
            
            self.indent_level += 1
            for s in stmt.catch_body:
                self._generate_statement(s)
            self.indent_level -= 1
        else:
            # 有尝试块但没有捕获块：生成默认except块
            self._add_line("except Exception:")
            self.indent_level += 1
            self._add_line("pass")
            self.indent_level -= 1
        
        # finally块
        if stmt.finally_body:
            self._add_line("finally:")
            self.indent_level += 1
            for s in stmt.finally_body:
                self._generate_statement(s)
            self.indent_level -= 1
    
    def _generate_throw_stmt(self, stmt: ThrowStmt):
        """生成抛出异常语句"""
        if stmt.value is None:
            # 裸抛出：重新抛出当前异常
            self._add_line("raise")
            return
        value = self._generate_expr(stmt.value)
        # 确保抛出的是合法异常对象（Python 3 不允许 raise 字符串）
        from_part = ""
        if stmt.from_expr:
            from_val = self._generate_expr(stmt.from_expr)
            from_part = f" from {from_val}"
        self._add_line(f"_light_exc = {value}")
        self._add_line(f"raise _light_exc if isinstance(_light_exc, BaseException) else Exception(_light_exc){from_part}")
    
    def _generate_self_assignment(self, stmt):
        """生成self赋值语句"""
        attr_name = self._sanitize_name(stmt.attr_name)
        value = self._generate_expr(stmt.value)
        self._add_line(f"self.{attr_name} = {value}")
    
    def _generate_compound_assignment(self, stmt):
        """生成复合赋值语句：甲 加上 1 → 甲 += 1"""
        target = self._sanitize_name(stmt.target)
        # 运算符映射
        py_ops = {
            '加': '+=',
            '减': '-=',
            '乘': '*=',
            '除': '/=',
            '除以': '/=',
            '整除': '//=',  # 整数除法复合赋值
            '模': '%=',
            '幂': '**=',
        }
        py_op = py_ops.get(stmt.operator, '+=')
        value = self._generate_expr(stmt.value)
        self._add_line(f"{target} {py_op} {value}")

    def _generate_indexed_compound_assignment(self, stmt):
        """生成索引复合赋值语句：甲[丁] 加上 1 → 甲[丁] += 1"""
        target = self._sanitize_name(stmt.target)
        index = self._generate_expr(stmt.index)
        py_ops = {
            '加': '+=',
            '减': '-=',
            '乘': '*=',
            '除': '/=',
            '除以': '/=',
            '整除': '//=',  # 整数除法复合赋值
            '模': '%=',
            '幂': '**=',
        }
        py_op = py_ops.get(stmt.operator, '+=')
        value = self._generate_expr(stmt.value)
        self._add_line(f"{target}[{index}] {py_op} {value}")

    def _generate_indexed_assignment(self, stmt):
        """生成索引赋值语句：甲[丁] = 值 或 甲[i][j] = 值"""
        if isinstance(stmt.target, ASTNode):
            target = self._generate_expr(stmt.target)
        else:
            target = self._sanitize_name(stmt.target)
        value = self._generate_expr(stmt.value)
        # 多重索引时 index=None，target 已经是 IndexAccess 节点
        if stmt.index is not None:
            index = self._generate_expr(stmt.index)
            self._add_line(f"{target}[{index}] = {value}")
        else:
            self._add_line(f"{target} = {value}")

    def _generate_class_definition(self, stmt):
        """生成类定义"""
        class_name = self._sanitize_name(stmt.name)

        # 检查是否有抽象方法
        has_abstract = False
        if hasattr(stmt, 'methods') and stmt.methods:
            for method in stmt.methods:
                if getattr(method, 'is_abstract', False):
                    has_abstract = True
                    break

        # 类定义行（包含父类和实现的接口）
        all_bases = list(stmt.base_classes) + list(getattr(stmt, 'interfaces', []) or [])
        if has_abstract:
            self._needs_abc = True
            if 'ABC' not in all_bases:
                all_bases.insert(0, 'ABC')
        if all_bases:
            bases = ', '.join(self._sanitize_name(b) for b in all_bases)
            self._add_line(f"class {class_name}({bases}):")
        else:
            self._add_line(f"class {class_name}:")

        self.indent_level += 1

        # 分离静态属性和实例属性
        static_attrs = []
        instance_attrs = []
        if hasattr(stmt, 'attributes') and stmt.attributes:
            for attr in stmt.attributes:
                if getattr(attr, 'is_static', False):
                    static_attrs.append(attr)
                else:
                    instance_attrs.append(attr)

        # 收集类属性名（用于方法内自动添加 self. 前缀）
        self._class_attr_names = set()
        for attr in instance_attrs:
            self._class_attr_names.add(self._sanitize_name(attr.name))
        for attr in static_attrs:
            self._class_attr_names.add(self._sanitize_name(attr.name))

        # 收集类方法名
        self._class_method_names = set()
        if hasattr(stmt, 'methods') and stmt.methods:
            for method in stmt.methods:
                method_name = method.name if hasattr(method, 'name') else ''
                self._class_method_names.add(method_name)

        # 检查是否有用户定义的构造函数
        has_constructor = False
        ctor_method = None
        if hasattr(stmt, 'methods') and stmt.methods:
            for method in stmt.methods:
                method_name = method.name if hasattr(method, 'name') else ''
                is_ctor = getattr(method, 'is_constructor', False) or method_name in ('构造', '初始化')
                if is_ctor or method_name == '__init__':
                    has_constructor = True
                    ctor_method = method
                    break

        # 生成静态属性（类变量）
        for attr in static_attrs:
            attr_name = self._sanitize_name(attr.name)
            if attr.default_value:
                default = self._generate_expr(attr.default_value)
                self._add_line(f"{attr_name} = {default}")
            else:
                self._add_line(f"{attr_name} = None")

        # 如果没有用户构造函数但有实例属性，自动生成 __init__
        if instance_attrs and not has_constructor:
            self._add_line("def __init__(self):")
            self.indent_level += 1
            for attr in instance_attrs:
                attr_name = self._sanitize_name(attr.name)
                if attr.default_value:
                    default = self._generate_expr(attr.default_value)
                    self._add_line(f"self.{attr_name} = {default}")
                else:
                    self._add_line(f"self.{attr_name} = None")
            self.indent_level -= 1

        # 生成方法
        if hasattr(stmt, 'methods') and stmt.methods:
            for method in stmt.methods:
                method_name = method.name if hasattr(method, 'name') else ''
                is_ctor = getattr(method, 'is_constructor', False) or method_name in ('构造', '初始化')
                if is_ctor and instance_attrs:
                    self._generate_method(method, instance_attrs)
                else:
                    self._generate_method(method)

        # 如果类体为空，添加 pass
        if not static_attrs and not instance_attrs and not (hasattr(stmt, 'methods') and stmt.methods):
            self._add_line("pass")

        # 清理类属性追踪
        self._class_attr_names = set()
        self._class_method_names = set()

        self.indent_level -= 1
        self._add_line("")
    
    def _generate_interface_definition(self, stmt: InterfaceDefinition):
        """生成接口定义"""
        self._needs_abc = True
        class_name = self._sanitize_name(stmt.name)
        
        # 基类
        bases = ['ABC']
        for sup in stmt.super_interfaces:
            bases.append(self._sanitize_name(sup))
        bases_str = ', '.join(bases)
        
        self._add_line(f"class {class_name}({bases_str}):")
        self.indent_level += 1
        
        # 生成抽象方法
        for method in stmt.methods:
            self._generate_abstract_method(method)
        
        # 如果没有方法，添加 pass
        if not stmt.methods:
            self._add_line("pass")
        
        self.indent_level -= 1
        self._add_line("")
    
    def _generate_abstract_method(self, method: MethodSignature):
        """生成抽象方法"""
        self._needs_abc = True
        method_name = self._sanitize_name(method.name)
        
        # 参数列表
        params = ['self']
        for param in method.parameters:
            param_name = self._sanitize_name(param.name)
            params.append(param_name)
        
        params_str = ', '.join(params)
        
        self._add_line("@abstractmethod")
        if method.return_type:
            ret_type = self._sanitize_name(method.return_type)
            self._add_line(f"def {method_name}({params_str}) -> {ret_type}:")
        else:
            self._add_line(f"def {method_name}({params_str}):")
        self.indent_level += 1
        self._add_line("pass")
        self.indent_level -= 1
    
    def _generate_match_stmt(self, stmt: MatchStmt):
        """生成模式匹配语句
        
        转换为 Python 3.10+ 的 match/case 语句，
        如果不支持则降级为 if/elif/else 链
        """
        subject = self._generate_expr(stmt.subject)
        self._add_line(f"match {subject}:")
        
        self.indent_level += 1
        for case in stmt.cases:
            self._generate_match_case(case)
        self.indent_level -= 1
        self._add_line("")
    
    def _generate_match_case(self, case: MatchCase):
        """生成匹配分支"""
        pattern = self._generate_match_pattern(case.pattern)
        
        guard_str = ""
        if case.guard:
            guard_str = f" if {self._generate_expr(case.guard)}"
        
        self._add_line(f"case {pattern}{guard_str}:")
        
        self.indent_level += 1
        if case.body:
            for stmt in case.body:
                self._generate_statement(stmt)
        else:
            self._add_line("pass")
        self.indent_level -= 1
    
    def _generate_match_pattern(self, pattern: MatchPattern) -> str:
        """生成匹配模式"""
        if pattern.kind == 'wildcard':
            return '_'
        elif pattern.kind == 'number':
            return str(pattern.value)
        elif pattern.kind == 'string':
            escaped = pattern.value.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        elif pattern.kind == 'bool':
            return 'True' if pattern.value else 'False'
        elif pattern.kind == 'null':
            return 'None'
        elif pattern.kind == 'variable':
            return self._sanitize_name(pattern.binding)
        elif pattern.kind == 'list':
            elements = [self._generate_match_pattern(e) for e in pattern.elements]
            return f"[{', '.join(elements)}]"
        elif pattern.kind == 'type_check':
            type_name = self._sanitize_name(pattern.type_name)
            binding = self._sanitize_name(pattern.binding)
            return f"{type_name}() as {binding}"
        return '_'

    def _generate_with_stmt(self, stmt: WithStmt):
        """生成上下文管理语句"""
        context_expr = self._generate_expr(stmt.context_expr)
        # 在 with 语句中，读取文件(...) 应替换为 open(...)
        context_expr = context_expr.replace('_light_builtin.读取文件', 'open').replace('读取文件', 'open')
        # 写入文件(...) 也应替换为 open(..., 'w')
        context_expr = context_expr.replace('_light_builtin.写入文件', 'open').replace('写入文件', 'open')
        if stmt.variable:
            var_name = self._sanitize_name(stmt.variable)
            self._add_line(f"with {context_expr} as {var_name}:")
        else:
            self._add_line(f"with {context_expr}:")
        self.indent_level += 1
        if stmt.body:
            for s in stmt.body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1

    def _generate_decorator_definition(self, stmt: DecoratorDefinition):
        """生成装饰器定义"""
        decorator_name = stmt.decorator_name
        
        # 内置装饰器映射
        builtin_decorators = {
            '静态方法': '@staticmethod',
            '类方法': '@classmethod',
            '特性': '@property',
            '抽象': '@abstractmethod',
        }
        
        if decorator_name in builtin_decorators:
            self._add_line(builtin_decorators[decorator_name])
            # 抽象装饰器需要导入 ABC
            if decorator_name == '抽象':
                self._needs_abc = True
        else:
            # 自定义装饰器（支持带参数：@decorator(args)）
            sanitized = self._sanitize_name(decorator_name)
            if stmt.args:
                args_parts = []
                for a in stmt.args:
                    if isinstance(a, KeywordArg):
                        args_parts.append(f"{a.name}={self._generate_expr(a.value)}")
                    else:
                        args_parts.append(self._generate_expr(a))
                args_str = ', '.join(args_parts)
                self._add_line(f"@{sanitized}({args_str})")
            else:
                self._add_line(f"@{sanitized}")
        
        if isinstance(stmt.paragraph, Paragraph):
            self._generate_paragraph(stmt.paragraph)
        else:
            raise CodeGenError("装饰器后必须是段落定义", type(stmt.paragraph).__name__)

    def _generate_method(self, method, class_attributes=None):
        """生成方法定义"""
        method_name = method.name

        # 构造函数特殊处理
        is_ctor = getattr(method, 'is_constructor', False) or method_name == '构造'
        if is_ctor:
            method_name = '__init__'

        # 静态方法不需要 self 参数
        is_static = getattr(method, 'is_static', False)
        is_classmethod = getattr(method, 'is_classmethod', False)
        is_abstract = getattr(method, 'is_abstract', False)
        if is_static or is_abstract:
            # 抽象方法可以有 self 也可以没有，但测试用例中的抽象方法通常无参数
            params = [] if is_static else ['self']
        else:
            params = ['self']

        # 访问修饰符：私有方法加 _ 前缀
        access = getattr(method, 'access_modifier', 'public')
        if access == 'private':
            method_name = f"_{method_name}"

        # 收集参数名（用于排除 self. 前缀）
        self._current_method_params = set()
        # 兼容 MethodDefinition(.parameters) 和 Paragraph(.params)
        method_params = getattr(method, 'parameters', None)
        if method_params is None:
            method_params = getattr(method, 'params', None)
        if method_params:
            for param in method_params:
                # Paragraph 的 params 是 List[Dict[str,str]]，MethodDefinition 的是 List[Parameter]
                if isinstance(param, dict):
                    param_name = self._sanitize_name(param.get('name', ''))
                    self._current_method_params.add(param.get('name', ''))
                    if param.get('default'):
                        params.append(f"{param_name}={param['default']}")
                    else:
                        params.append(param_name)
                else:
                    param_name = self._sanitize_name(param.name)
                    self._current_method_params.add(param.name)
                    if getattr(param, 'default_value', None):
                        default = self._generate_expr(param.default_value)
                        params.append(f"{param_name}={default}")
                    else:
                        params.append(param_name)

        params_str = ', '.join(params)

        # 方法定义（必须包含括号）
        if is_abstract:
            self._needs_abc = True
            self._add_line("@abstractmethod")
        if is_static:
            self._add_line(f"@staticmethod")
        if is_classmethod:
            self._add_line(f"@classmethod")
        if getattr(method, 'is_property', False):
            self._add_line("@property")
        self._add_line(f"def {method_name}({params_str}):")

        old_in_function = self._in_function
        old_in_class = self._in_class_method
        self._in_function = True
        self._in_class_method = not is_static
        self.indent_level += 1

        # 如果是构造函数且有类属性，为未在构造函数体中初始化的属性生成默认值
        attr_init_lines = []
        if method_name == '__init__' and class_attributes:
            # 收集已在构造函数中初始化的属性名
            initialized_attrs = set()
            if hasattr(method, 'body') and method.body:
                for stmt in method.body:
                    if isinstance(stmt, tuple):
                        if stmt[0] == 'var':
                            initialized_attrs.add(self._sanitize_name(stmt[1]))
                    elif isinstance(stmt, VarDecl):
                        initialized_attrs.add(self._sanitize_name(stmt.name))
                    elif hasattr(stmt, 'target'):
                        # Assignment 或 SelfAssignment 节点
                        target = stmt.target
                        if isinstance(target, str):
                            initialized_attrs.add(self._sanitize_name(target))
                        elif hasattr(target, 'name'):
                            initialized_attrs.add(self._sanitize_name(target.name))
            # 只为有默认值且未在构造函数中初始化的属性生成初始化语句
            for attr in class_attributes:
                attr_name = self._sanitize_name(attr.name)
                if attr_name not in initialized_attrs and attr.default_value:
                    default = self._generate_expr(attr.default_value)
                    attr_init_lines.append(f"self.{attr_name} = {default}")

        # 先输出属性初始化语句，再生成方法体
        if attr_init_lines:
            for line in attr_init_lines:
                self._add_line(line)

        # 生成方法体
        if hasattr(method, 'body') and method.body:
            for stmt in method.body:
                if isinstance(stmt, tuple):
                    # 简化的语句表示
                    if stmt[0] == 'return':
                        value = self._generate_expr(stmt[1]) if stmt[1] else 'None'
                        self._add_line(f"return {value}")
                    elif stmt[0] == 'var':
                        var_name = self._sanitize_name(stmt[1])
                        var_value = self._generate_expr(stmt[2])
                        self._add_line(f"{var_name} = {var_value}")
                else:
                    # AST节点
                    self._generate_statement(stmt)
        else:
            self._add_line("pass")
        
        self.indent_level -= 1
        self._add_line("")
        
        # 重置上下文
        self._in_function = old_in_function
        self._in_class_method = old_in_class
        self._current_method_params = set()
    
    def _generate_expr(self, expr: ASTNode) -> str:
        """生成表达式"""
        if expr is None:
            return 'None'
        
        if isinstance(expr, str):
            # 字符串字面量
            return f'"{expr}"'
        
        if isinstance(expr, (int, float)):
            # 数字字面量
            return str(expr)
        
        # 解包表达式：值! 或 unwrap(值)
        # 翻译成 (lambda _x: (_light_assert_not_none(_x), _x)[1])(inner_expr)
        if type(expr).__name__ == 'UnwrapExpression':
            inner = self._generate_expr(expr.value)
            return f"(_light_unwrap({inner}))"
        
        if isinstance(expr, NumberLiteral):
            # 检查是否是中文数字
            if expr.value in self.chinese_numbers:
                return str(self.chinese_numbers[expr.value])
            return str(expr.value)
        
        elif isinstance(expr, StringLiteral):
            # 转义引号和不可见字符
            value = expr.value
            # 先处理反斜杠（必须是第一步）
            value = value.replace('\\', '\\\\')
            # 再处理不可见字符
            value = value.replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t').replace('"', '\\"').replace('\0', '\\0').replace('\x00', '\\0')
            return f'"{value}"'
        
        elif isinstance(expr, Identifier):
            name = self._sanitize_name(expr.name)
            # 检查是否是中文数字
            if expr.name in self.chinese_numbers:
                return str(self.chinese_numbers[expr.name])
            # 己 → self，己.attr → self.attr
            if name == '己':
                return 'self'
            if name.startswith('己.'):
                return 'self.' + name[2:]
            # 类方法中，如果引用的是类属性且不是参数名，添加 self. 前缀
            if self._in_class_method and expr.name in self._class_attr_names and expr.name not in self._current_method_params:
                return f"self.{name}"
            return name
        
        # 检查 ast_nodes 模块中的 Identifier（兼容两种定义）
        elif hasattr(expr, 'name') and hasattr(expr, 'line'):
            # 可能是来自 ast_nodes 的 Identifier
            return self._sanitize_name(expr.name)
        
        elif isinstance(expr, BinaryOp):
            left = self._generate_expr(expr.left)
            right = self._generate_expr(expr.right)
            op = self.operator_map.get(expr.operator, expr.operator)
            return f"({left} {op} {right})"
        
        elif isinstance(expr, UnaryOp):
            operand = self._generate_expr(expr.operand)
            op = self.operator_map.get(expr.operator, expr.operator)
            return f"({op} {operand})"
        
        elif isinstance(expr, ParagraphCall):
            name = self._sanitize_name(expr.name)
            
            # 检查是否是内置函数（但不覆盖用户自定义的函数）
            if expr.name in self.builtin_map and expr.name not in self._user_defined_functions:
                py_name = self.builtin_map[expr.name]
            else:
                py_name = name
                # 类方法中，如果调用的是同类其他方法，添加 self. 前缀
                if self._in_class_method and expr.name in self._class_method_names:
                    py_name = f"self.{name}"
            
            # 参数（支持关键字参数）
            args = []
            for arg in expr.args:
                if isinstance(arg, KeywordArg):
                    args.append(f"{arg.name}={self._generate_expr(arg.value)}")
                else:
                    args.append(self._generate_expr(arg))
            args_str = ', '.join(args)
            
            return f"{py_name}({args_str})"
        
        elif isinstance(expr, Pipeline):
            # 管道操作：从左到右依次调用
            # 例如：数据 -> 过滤 -> 排序
            # 转换为：排序(过滤(数据))
            
            if len(expr.stages) == 1:
                return self._generate_expr(expr.stages[0])
            
            # 反向调用
            result = self._generate_expr(expr.stages[-1])
            for stage in reversed(expr.stages[:-1]):
                stage_expr = self._generate_expr(stage)
                result = f"{stage_expr}({result})"
            
            return result
        
        elif isinstance(expr, IndexAccess):
            # 索引访问：obj[index] 或 obj[start:stop:step]（切片）
            obj = self._generate_expr(expr.obj)
            if isinstance(expr.index, SliceExpr):
                start = self._generate_expr(expr.index.start) if expr.index.start else ''
                stop = self._generate_expr(expr.index.stop) if expr.index.stop else ''
                step = self._generate_expr(expr.index.step) if expr.index.step else ''
                if step:
                    return f"{obj}[{start}:{stop}:{step}]"
                else:
                    return f"{obj}[{start}:{stop}]"
            else:
                index = self._generate_expr(expr.index)
                return f"{obj}[{index}]"
        
        elif isinstance(expr, ClassInstantiation):
            # 类实例化：类名(参数...)
            class_name = self._sanitize_name(expr.class_name)
            args = [self._generate_expr(arg) for arg in expr.args]
            args_str = ', '.join(args)
            return f"{class_name}({args_str})"
        
        elif isinstance(expr, MemberAccess):
            # 成员访问：obj.member 或 obj.method(args...)
            obj = self._generate_expr(expr.obj)
            member = self._sanitize_name(expr.member)
            
            # 检查方法名是否需要映射转换
            mapped_member = self.method_name_map.get(expr.member, member)
            
            # 检查导入的模块成员访问映射
            # 如 JSON.序列化 → _light_builtin.序列化JSON, JSON.解析 → _light_builtin.解析JSON
            module_member_map = {
                'JSON.序列化': '_light_builtin.序列化JSON',
                'JSON.解析': '_light_builtin.解析JSON',
                'JSON.美化': '_light_builtin.美化JSON',
            }
            full_access = f"{obj}.{member}"
            if full_access in module_member_map:
                mapped = module_member_map[full_access]
                if expr.is_method_call:
                    args = []
                    for arg in expr.args:
                        if isinstance(arg, KeywordArg):
                            args.append(f"{arg.name}={self._generate_expr(arg.value)}")
                        else:
                            args.append(self._generate_expr(arg))
                    args_str = ', '.join(args)
                    return f"{mapped}({args_str})"
                else:
                    return mapped
            
            if expr.is_method_call:
                # 方法调用（支持关键字参数）
                args = []
                for arg in expr.args:
                    if isinstance(arg, KeywordArg):
                        args.append(f"{arg.name}={self._generate_expr(arg.value)}")
                    else:
                        args.append(self._generate_expr(arg))
                args_str = ', '.join(args)

                # 特殊处理：父.构造(...) -> super().__init__(...)
                if obj == "super()" and expr.member == '构造':
                    return f"super().__init__({args_str})"
                # 特殊处理：长度方法 -> len(obj)
                if expr.member == '长度':
                    return f"len({obj})"
                # 特殊处理：包含方法 -> item in obj
                elif expr.member == '包含':
                    return f"{args_str} in {obj}"

                # P5 核心改造：内置函数式优先
                # 如果方法名在 builtin_map 中且映射到 _light_builtin，转为函数式调用
                # 这样 obj.方法(args) 自动转为 _light_builtin.方法(obj, args)
                # 外部库方法（不在 builtin_map 中）则原样透传 obj.method(args)
                builtin_target = self.builtin_map.get(expr.member)
                if builtin_target and builtin_target.startswith('_light_builtin.'):
                    # 内置函数：转为函数式调用
                    func_name = builtin_target.split('.', 1)[1]
                    if args_str:
                        return f"{builtin_target}({obj}, {args_str})"
                    else:
                        return f"{builtin_target}({obj})"

                return f"{obj}.{mapped_member}({args_str})"
            else:
                # 属性访问
                return f"{obj}.{mapped_member}"
        
        elif isinstance(expr, ListLiteral):
            # 列表字面量
            elements = [self._generate_expr(e) for e in expr.elements]
            return f"[{', '.join(elements)}]"
        
        elif isinstance(expr, TupleLiteral):
            # 元组字面量
            elements = [self._generate_expr(e) for e in expr.elements]
            if len(elements) == 1:
                return f"({elements[0]},)"
            return f"({', '.join(elements)})"
        
        elif isinstance(expr, SetLiteral):
            # 集合字面量
            if not expr.elements:
                return "set()"
            elements = [self._generate_expr(e) for e in expr.elements]
            return f"{{{', '.join(elements)}}}"
        
        elif isinstance(expr, StringInterpolation):
            # 字符串插值 -> f-string
            parts = []
            for part in expr.parts:
                if isinstance(part, str):
                    # 转义特殊字符（反斜杠、换行、回车、制表符）
                    escaped = part.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                    parts.append(escaped)
                elif isinstance(part, tuple):
                    # 带格式说明符的表达式：(expr_node, format_spec)
                    expr_code = self._generate_expr(part[0])
                    parts.append('{' + expr_code + ':' + part[1] + '}')
                elif isinstance(part, ASTNode):
                    # 生成表达式代码并放入花括号
                    expr_code = self._generate_expr(part)
                    parts.append('{' + expr_code + '}')
            fstr = ''.join(parts)
            # 选择合适的外层引号：如果内容包含双引号，使用单引号避免冲突
            if '"' in fstr:
                if "'" in fstr:
                    # 两种引号都有，转义双引号并保留双引号外层
                    fstr = fstr.replace('"', '\\"')
                    return f'f"{fstr}"'
                else:
                    return f"f'{fstr}'"
            else:
                return f'f"{fstr}"'
        
        elif isinstance(expr, ListComprehension):
            # 列表推导 -> [expr for var in iterable if condition ...]
            expression = self._generate_expr(expr.expression)
            if expr.generators and len(expr.generators) > 1:
                # 多重generator
                parts = []
                for var, it, cond in expr.generators:
                    var_name = self._sanitize_name(var)
                    it_str = self._generate_expr(it)
                    part = f"for {var_name} in {it_str}"
                    if cond:
                        cond_str = self._generate_expr(cond)
                        part += f" if {cond_str}"
                    parts.append(part)
                return f"[{expression} {' '.join(parts)}]"
            else:
                variable = self._sanitize_name(expr.variable)
                iterable = self._generate_expr(expr.iterable)
                result = f"[{expression} for {variable} in {iterable}"
                if expr.condition:
                    condition = self._generate_expr(expr.condition)
                    result += f" if {condition}"
                result += "]"
                return result
        
        elif isinstance(expr, SetComprehension):
            # 集合推导 -> {expr for var in iterable if condition ...}
            expression = self._generate_expr(expr.expression)
            if expr.generators and len(expr.generators) > 1:
                # 多重generator
                parts = []
                for var, it, cond in expr.generators:
                    var_name = self._sanitize_name(var)
                    it_str = self._generate_expr(it)
                    part = f"for {var_name} in {it_str}"
                    if cond:
                        cond_str = self._generate_expr(cond)
                        part += f" if {cond_str}"
                    parts.append(part)
                return f"{{{expression} {' '.join(parts)}}}"
            else:
                variable = self._sanitize_name(expr.variable)
                iterable = self._generate_expr(expr.iterable)
                result = f"{{{expression} for {variable} in {iterable}"
                if expr.condition:
                    condition = self._generate_expr(expr.condition)
                    result += f" if {condition}"
                result += "}"
                return result
        
        elif isinstance(expr, LambdaExpression):
            # 匿名函数 -> lambda params: body
            params = ', '.join(self._sanitize_name(p) for p in expr.params)
            body = self._generate_expr(expr.body)
            return f"lambda {params}: {body}"
        
        elif isinstance(expr, DictComprehension):
            # 字典推导 -> {key: value for var in iterable if condition ...}
            key = self._generate_expr(expr.key_expr)
            val = self._generate_expr(expr.value_expr)
            if expr.generators and len(expr.generators) > 1:
                # 多重generator
                parts = []
                for var, it, cond in expr.generators:
                    var_name = self._sanitize_name(var)
                    it_str = self._generate_expr(it)
                    part = f"for {var_name} in {it_str}"
                    if cond:
                        cond_str = self._generate_expr(cond)
                        part += f" if {cond_str}"
                    parts.append(part)
                return f"{{{key}: {val} {' '.join(parts)}}}"
            else:
                var_name = self._sanitize_name(expr.variable)
                iterable = self._generate_expr(expr.iterable)
                result = f"{{{key}: {val} for {var_name} in {iterable}"
                if expr.condition:
                    condition = self._generate_expr(expr.condition)
                    result += f" if {condition}"
                result += "}"
                return result

        elif isinstance(expr, DictLiteral):
            # 字典字面量 -> {key: val, key2: val2, ...} 或 {**d1, key: val}
            items = []
            for k, v in expr.entries:
                if k is None:
                    # **展开
                    items.append(f"**{self._generate_expr(v)}")
                else:
                    items.append(f"{self._generate_expr(k)}: {self._generate_expr(v)}")
            return f"{{{', '.join(items)}}}"

        elif isinstance(expr, ConditionalExpression):
            # 三元条件表达式 -> 值1 if 条件 else 值2
            condition = self._generate_expr(expr.condition)
            then_expr = self._generate_expr(expr.then_expr)
            if expr.else_expr:
                else_expr = self._generate_expr(expr.else_expr)
                return f"({then_expr} if {condition} else {else_expr})"
            else:
                return f"({then_expr} if {condition} else None)"

        elif isinstance(expr, AssignmentExpression):
            # 赋值表达式（海象运算符） -> (name := value)
            name = self._sanitize_name(expr.name)
            value = self._generate_expr(expr.value)
            return f"({name} := {value})"

        elif isinstance(expr, RangeExpr):
            # 范围表达式 -> range(start, end+1) 或 range(start, end+1, step)
            # 处理递减范围：当 start>end 时，自动将步长取反
            start = self._generate_expr(expr.start)
            end = self._generate_expr(expr.end)
            if expr.step:
                step = self._generate_expr(expr.step)
                # 运行时判断方向：start<=end 时正常步长，否则步长取反
                return f"range({start}, ({end}) + (1 if ({start}) <= ({end}) else -1), ({step}) if ({start}) <= ({end}) else -({step}))"
            else:
                return f"range({start}, ({end}) + 1)"

        elif isinstance(expr, AwaitExpr):
            # 等待表达式 → await expression
            inner = self._generate_expr(expr.expression)
            return f"await {inner}"
        
        else:
            raise CodeGenError(f"不支持的表达式类型", type(expr).__name__)
    
    def _sanitize_name(self, name: str) -> str:
        """清理名称（转换为合法Python标识符）"""
        # 中文变量名在Python3中是合法的
        # 但为了更好的兼容性，可以选择转拼音或保留中文
        
        # 如果名称以ASCII数字开头，加前缀"_"
        if name and '0' <= name[0] <= '9':
            return f"_{name}"
        
        # 简单方案：保留中文
        return name
    
    def _generate_import_stmt(self, stmt: ImportStmt):
        """生成导入语句
        
        支持三种语言前缀：
        - None: 光明标准库（中文模块名映射到 stdlib 路径）
        - 'python': Python 第三方库（直接 import 原名）
        - 'c': C 语言库（通过 ctypes/FFI 加载）
        """
        module_name = stmt.module_name
        
        # Python 第三方库导入：直接 import 原名
        if getattr(stmt, 'language', None) == 'python':
            if stmt.symbols:
                symbols_str = ', '.join(stmt.symbols)
                if stmt.alias:
                    self._add_line(f"from {module_name} import {symbols_str} as {stmt.alias}")
                    self._imported_symbols.add(stmt.alias)
                else:
                    self._add_line(f"from {module_name} import {symbols_str}")
                    for symbol in stmt.symbols:
                        self._imported_symbols.add(symbol)
            else:
                if stmt.alias:
                    self._add_line(f"import {module_name} as {stmt.alias}")
                    self._imported_symbols.add(stmt.alias)
                else:
                    self._add_line(f"import {module_name}")
                    self._imported_symbols.add(module_name)
            # 处理多模块导入
            if hasattr(stmt, 'extra_modules') and stmt.extra_modules:
                for extra_mod, extra_alias in stmt.extra_modules:
                    if extra_alias:
                        self._add_line(f"import {extra_mod} as {extra_alias}")
                        self._imported_symbols.add(extra_alias)
                    else:
                        self._add_line(f"import {extra_mod}")
                        self._imported_symbols.add(extra_mod)
            return
        
        # C 语言库导入：通过 ctypes 加载共享库
        if getattr(stmt, 'language', None) == 'c':
            if stmt.symbols:
                # from 模块导入符号 → 声明 ctypes 函数
                symbols_str = ', '.join(stmt.symbols)
                self._add_line(f"# 导入 C 库 {module_name} 的符号: {symbols_str}")
                # 尝试通过 ctypes 加载
                self._add_line(f"try:")
                self._add_line(f"    _c_lib_{module_name} = ctypes.CDLL('{module_name}')")
                self._add_line(f"except:")
                self._add_line(f"    _c_lib_{module_name} = None")
                for symbol in stmt.symbols:
                    if stmt.alias:
                        self._add_line(f"{stmt.alias}_{symbol} = getattr(_c_lib_{module_name}, '{symbol}', None) if _c_lib_{module_name} else None")
                        self._imported_symbols.add(f"{stmt.alias}_{symbol}")
                    else:
                        self._add_line(f"_c_{module_name}_{symbol} = getattr(_c_lib_{module_name}, '{symbol}', None) if _c_lib_{module_name} else None")
                        self._imported_symbols.add(symbol)
            else:
                self._add_line(f"# 导入 C 库: {module_name}")
                self._add_line(f"try:")
                self._add_line(f"    _c_lib_{module_name} = ctypes.CDLL('{module_name}')")
                self._add_line(f"except:")
                self._add_line(f"    _c_lib_{module_name} = None")
                if stmt.alias:
                    self._add_line(f"{stmt.alias} = _c_lib_{module_name}")
                    self._imported_symbols.add(stmt.alias)
                else:
                    self._imported_symbols.add(module_name)
            return
        
        # 光明标准库导入：使用模块名映射转换中文模块名
        # 1. 先查 lightpub 加载器（支持 "标准文件系统" / "文件系统" 等导入名）
        mapped_module = self._resolve_lightpub_import(module_name)
        # 2. 如果 lightpub 没有命中，回退到内置模块名映射
        if mapped_module is None:
            mapped_module = self.module_name_map.get(module_name, module_name)
        
        if stmt.symbols:
            # 从...导入：from 数学 import 平方根, 幂
            symbols_str = ', '.join(stmt.symbols)
            if stmt.alias:
                if mapped_module:
                    self._add_line(f"from {mapped_module} import {symbols_str} as {stmt.alias}")
                else:
                    self._add_line(f"import {symbols_str} as {stmt.alias}")
                self._imported_symbols.add(stmt.alias)
            else:
                if mapped_module:
                    self._add_line(f"from {mapped_module} import {symbols_str}")
                else:
                    self._add_line(f"import {symbols_str}")
                # 追踪导入的符号
                for symbol in stmt.symbols:
                    self._imported_symbols.add(symbol)
        else:
            # 导入整个模块：import 数学
            if stmt.alias:
                self._add_line(f"import {mapped_module} as {stmt.alias}")
                self._imported_symbols.add(stmt.alias)
            else:
                self._add_line(f"import {mapped_module}")
                self._imported_symbols.add(module_name)
        
        # 处理多模块导入（extra_modules）
        if hasattr(stmt, 'extra_modules') and stmt.extra_modules:
            for extra_mod, extra_alias in stmt.extra_modules:
                mapped_extra = self.module_name_map.get(extra_mod, extra_mod)
                if extra_alias:
                    self._add_line(f"import {mapped_extra} as {extra_alias}")
                    self._imported_symbols.add(extra_alias)
                else:
                    self._add_line(f"import {mapped_extra}")
                    self._imported_symbols.add(extra_mod)
    
    def _generate_import_statement(self, stmt):
        """生成 ast_nodes.py 的 ImportStatement"""
        module_name = stmt.module
        
        # 使用模块名映射转换中文模块名
        mapped_module = self.module_name_map.get(module_name, module_name)
        
        if stmt.names:
            # from module import names
            names_str = ', '.join(stmt.names)
            if mapped_module:
                self._add_line(f"from {mapped_module} import {names_str}")
            else:
                self._add_line(f"import {names_str}")
            for name in stmt.names:
                self._imported_symbols.add(name)
        else:
            # import module
            self._add_line(f"import {mapped_module}")
            self._imported_symbols.add(module_name)
    
    def _resolve_lightpub_import(self, module_name: str):
        """
        通过 lightpub 加载器解析导入名，返回 Python 模块名。
        
        解析顺序：
        1. lightpub P0 包 → get_stdlib_bridge() 返回 Python 模块名
        2. lightpub P1 包 → 返回 "stdlib.lightpub.<包名>"（桥接模块路径）
        3. 未命中 → 返回 None（回退到 module_name_map）
        """
        try:
            import sys
            import os
            # 确保 stdlib 目录在 path 中
            stdlib_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'stdlib')
            if stdlib_dir not in sys.path:
                sys.path.insert(0, stdlib_dir)
            from lightpub import resolve_import, get_stdlib_bridge
            
            pkg_info = resolve_import(module_name)
            if pkg_info is None:
                return None
            
            priority = pkg_info.get('priority', 'P2')
            
            # P0: 已有 stdlib 实现，桥接到 Python 模块
            if priority == 'P0':
                # 去掉"标准"前缀后查找桥接
                real_name = module_name[2:] if module_name.startswith('标准') else module_name
                bridge = get_stdlib_bridge(real_name)
                if bridge:
                    return bridge
                # 没有桥接映射时，用真实包名作为 Python 模块名
                return real_name
            
            # P1: 有 Python 桥接模块
            if priority == 'P1':
                # 去掉"标准"前缀后得到真实包名
                real_name = module_name[2:] if module_name.startswith('标准') else module_name
                return 'stdlib.lightpub.' + real_name
        except Exception:
            pass
        return None

    
    def _is_chinese(self, text: str) -> bool:
        """判断字符串是否包含中文"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    def _generate_export_stmt(self, stmt: ExportStmt):
        """生成导出语句"""
        if stmt.symbols == ['*']:
            # 导出全部：生成 __all__ 包含所有函数
            # 注意：这需要在编译器中收集所有函数名
            # 简化处理：生成注释
            self._add_line("# 导出全部")
        else:
            # 导出指定符号：生成 __all__ 列表
            symbols_str = ', '.join(f"'{s}'" for s in stmt.symbols)
            self._add_line(f"__all__ = [{symbols_str}]")

    # =========================================================================
    # C FFI 代码生成方法
    # =========================================================================

    # FFI 类型映射：光明类型 → ctypes 类型
    _ffi_type_map = {
        '整数': 'ctypes.c_int',
        '小数': 'ctypes.c_double',
        '浮数': 'ctypes.c_double',
        '文本': 'ctypes.c_char_p',
        '串': 'ctypes.c_char_p',
        '布尔': 'ctypes.c_bool',
        '空': 'ctypes.c_void_p',
        '数': 'ctypes.c_double',
        '无': 'None',
    }

    def _generate_ffi_load_library(self, stmt: FFILoadLibrary):
        """生成加载动态库代码"""
        path = stmt.library_path
        alias = self._sanitize_name(stmt.alias)
        self._add_line(f"# 加载动态库: {path}")
        self._add_line(f"{alias} = ctypes.CDLL({repr(path)})")

    def _generate_ffi_function_decl(self, stmt: FFIFunctionDecl):
        """生成外部函数声明"""
        name = self._sanitize_name(stmt.name)
        library_alias = self._sanitize_name(stmt.library_alias)
        c_name = stmt.c_name or stmt.name

        # 确定参数类型和返回类型
        arg_types = []
        for p in stmt.params:
            light_type = p.get('type', '整数')
            ctype = self._ffi_type_map.get(light_type, 'ctypes.c_int')
            arg_types.append(ctype)

        restype = 'None'
        if stmt.return_type:
            restype = self._ffi_type_map.get(stmt.return_type, 'ctypes.c_int')

        # 生成 ctypes 函数绑定
        self._add_line(f"# 外部函数声明: {c_name}({', '.join(p['name'] for p in stmt.params)})")
        if library_alias:
            self._add_line(f"_{name}_ffi = {library_alias}.{c_name}")
            if arg_types:
                arg_types_str = ', '.join(arg_types)
                self._add_line(f"_{name}_ffi.argtypes = [{arg_types_str}]")
            self._add_line(f"_{name}_ffi.restype = {restype}")

        # 生成包装函数，处理类型转换
        params_str = ', '.join(self._sanitize_name(p['name']) for p in stmt.params)
        param_names = [self._sanitize_name(p['name']) for p in stmt.params]

        self._add_line(f"def {name}({params_str}):")
        self.indent_level += 1
        # 类型转换：文本类型需要 encode
        for i, p in enumerate(stmt.params):
            pname = self._sanitize_name(p['name'])
            ptype = p.get('type', '')
            if ptype in ('文本', '串'):
                self._add_line(f"{pname}_c = {pname}.encode('utf-8') if isinstance({pname}, str) else {pname}")
        # 调用 FFI 函数
        args_pass = []
        for i, p in enumerate(stmt.params):
            pname = self._sanitize_name(p['name'])
            ptype = p.get('type', '')
            if ptype in ('文本', '串'):
                args_pass.append(f"{pname}_c")
            else:
                args_pass.append(pname)
        args_str = ', '.join(args_pass)
        self._add_line(f"_result = _{name}_ffi({args_str})")
        # 返回类型转换：c_char_p 需要 decode
        if stmt.return_type in ('文本', '串'):
            self._add_line(f"return _result.decode('utf-8') if _result else ''")
        else:
            self._add_line("return _result")
        self.indent_level -= 1
        self._add_line("")

    def _generate_ffi_struct_def(self, stmt: FFIStructDef):
        """生成外部结构体定义"""
        name = self._sanitize_name(stmt.name)
        fields_code = []
        for f in stmt.fields:
            fname = self._sanitize_name(f['name'])
            ftype = self._ffi_type_map.get(f['type'], 'ctypes.c_int')
            fields_code.append(f"('{fname}', {ftype})")
        fields_str = ', '.join(fields_code)
        self._add_line(f"# 外部结构体: {name}")
        self._add_line(f"class {name}(ctypes.Structure):")
        self.indent_level += 1
        self._add_line(f"_fields_ = [{fields_str}]")
        self.indent_level -= 1
        self._add_line("")

    def _generate_ffi_callback_def(self, stmt: FFICallbackDef):
        """生成外部回调类型定义"""
        name = self._sanitize_name(stmt.name)
        arg_types = []
        for p in stmt.params:
            light_type = p.get('type', '整数')
            ctype = self._ffi_type_map.get(light_type, 'ctypes.c_int')
            arg_types.append(ctype)
        restype = 'None'
        if stmt.return_type:
            restype = self._ffi_type_map.get(stmt.return_type, 'ctypes.c_int')
        arg_types_str = ', '.join(arg_types)
        self._add_line(f"# 外部回调类型: {name}")
        self._add_line(f"{name} = ctypes.CFUNCTYPE({restype}, {arg_types_str})")
        self._add_line("")

    def _generate_ffi_create_array(self, stmt: FFICreateArray):
        """生成创建数组代码"""
        base_type = stmt.base_type
        ctype = self._ffi_type_map.get(base_type, 'ctypes.c_int')
        size = self._generate_expr(stmt.size)
        name = self._sanitize_name(stmt.base_type)
        self._add_line(f"# 创建数组: {base_type}[{size}]")
        self._add_line(f"_ffi_arr_{name} = ({ctype} * {size})()")
        self._add_line("")

    def _generate_ffi_set_array_element(self, stmt: FFISetArrayElement):
        """生成设置数组元素代码"""
        arr = self._sanitize_name(stmt.array)
        idx = self._generate_expr(stmt.index)
        val = self._generate_expr(stmt.value)
        self._add_line(f"{arr}[{idx}] = {val}")

    def _generate_ffi_alloc_memory(self, stmt: FFIAllocMemory):
        """生成分配内存代码"""
        size = self._generate_expr(stmt.size)
        self._add_line(f"# 分配内存: {size} 字节")
        self._add_line(f"_ffi_mem = ctypes.create_string_buffer({size})")

    def _generate_ffi_free_memory(self, stmt: FFIFreeMemory):
        """生成释放内存代码"""
        ptr = self._sanitize_name(stmt.pointer)
        self._add_line(f"# 释放内存: {ptr}")
        self._add_line(f"del {ptr}")

    def _generate_ffi_set_pointer_value(self, stmt: FFISetPointerValue):
        """生成设指针值代码"""
        ptr = self._sanitize_name(stmt.pointer)
        val = self._generate_expr(stmt.value)
        self._add_line(f"{ptr}[0] = {val}")

    def _generate_ffi_set_errno(self, stmt: FFISetErrno):
        """生成设系统错误码代码"""
        val = self._generate_expr(stmt.value)
        self._add_line(f"ctypes.set_errno({val})")

    def _generate_ffi_try_catch(self, stmt: FFITryCatch):
        """生成FFI错误捕获代码"""
        self._add_line("try:")
        self.indent_level += 1
        for s in stmt.try_body:
            self._generate_statement(s)
        self.indent_level -= 1
        if stmt.catch_body:
            self._add_line(f"except (ctypes.ArgumentError, OSError, RuntimeError) as {stmt.error_var}:")
            self.indent_level += 1
            for s in stmt.catch_body:
                self._generate_statement(s)
            self.indent_level -= 1

    def _generate_ffi_enum_def(self, stmt: FFIEnumDef):
        """生成C枚举定义代码"""
        name = self._sanitize_name(stmt.name)
        self._add_line(f"# C枚举: {name}")
        self._add_line(f"class {name}:")
        self.indent_level += 1
        for member_name, member_val in stmt.values.items():
            self._add_line(f"{self._sanitize_name(member_name)} = {member_val}")
        self.indent_level -= 1
        self._add_line("")

    def _generate_ffi_union_def(self, stmt: FFIUnionDef):
        """生成C联合体定义代码"""
        name = self._sanitize_name(stmt.name)
        fields_code = []
        for f in stmt.fields:
            fname = self._sanitize_name(f['name'])
            ftype = self._ffi_type_map.get(f['type'], 'ctypes.c_int')
            fields_code.append(f"('{fname}', {ftype})")
        fields_str = ', '.join(fields_code)
        self._add_line(f"# C联合体: {name}")
        self._add_line(f"class {name}(ctypes.Union):")
        self.indent_level += 1
        self._add_line(f"_fields_ = [{fields_str}]")
        self.indent_level -= 1
        self._add_line("")

    def _generate_ffi_varargs_decl(self, stmt: FFIVarArgsDecl):
        """生成变长参数函数声明代码"""
        name = self._sanitize_name(stmt.name)
        library_alias = self._sanitize_name(stmt.library_alias)
        c_name = stmt.c_name or stmt.name
        
        arg_types = []
        for p in stmt.params:
            light_type = p.get('type', '整数')
            ctype = self._ffi_type_map.get(light_type, 'ctypes.c_int')
            arg_types.append(ctype)
        
        restype = 'None'
        if stmt.return_type:
            restype = self._ffi_type_map.get(stmt.return_type, 'ctypes.c_int')
        
        self._add_line(f"# 变长参数函数声明: {c_name}")
        self._add_line(f"_{name}_ffi = {library_alias}.{c_name}")
        if arg_types:
            arg_types_str = ', '.join(arg_types)
            self._add_line(f"_{name}_ffi.argtypes = [{arg_types_str}]")
        self._add_line(f"_{name}_ffi.restype = {restype}")
        
        fixed_params = ', '.join(self._sanitize_name(p['name']) for p in stmt.params)
        self._add_line(f"def {name}({fixed_params}, *args):")
        self.indent_level += 1
        self._add_line(f"return _{name}_ffi({fixed_params}, *args)")
        self.indent_level -= 1
        self._add_line("")

    def _generate_ffi_create_callback(self, stmt: FFICreateCallback):
        """生成创建回调函数代码"""
        cb_type = self._sanitize_name(stmt.callback_type)
        light_func = self._sanitize_name(stmt.light_function)
        self._add_line(f"# 创建回调: {light_func} -> {cb_type}")
        self._add_line(f"_cb_{light_func} = {cb_type}({light_func})")
        self._add_line("")

    def _generate_ffi_struct_by_value(self, stmt: FFIStructByValue):
        """生成结构体按值传递代码"""
        struct_type = self._sanitize_name(stmt.struct_type)
        self._add_line(f"# 结构体按值传递: {struct_type}")
        self._add_line(f"_struct_val = {struct_type}()")
        for fname, fval in stmt.fields.items():
            sfname = self._sanitize_name(fname)
            val_code = self._generate_expr(fval)
            self._add_line(f"_struct_val.{sfname} = {val_code}")
        self._add_line("")

    def _generate_ffi_library_path(self, stmt: FFILibraryPath):
        """生成跨平台库路径解析代码"""
        name = self._sanitize_name(stmt.name)
        self._add_line(f"# 跨平台库路径: {name}")
        self._add_line(f"_platform = sys.platform")
        if stmt.platform_map:
            self._add_line(f"_lib_map_{name} = {{")
            for plat, path in stmt.platform_map.items():
                self._add_line(f"    '{plat}': '{path}',")
            self._add_line("}")
            self._add_line(f"_{name}_libpath = _lib_map_{name}.get(_platform, '')")
        else:
            self._add_line(f"_{name}_libpath = ''")
        self._add_line("")

    def _generate_ffi_typedef_def(self, stmt: FFITypedefDef):
        """生成C类型别名代码"""
        name = self._sanitize_name(stmt.name)
        base_type = self._ffi_type_map.get(stmt.base_type, stmt.base_type)
        self._add_line(f"# C类型别名: {name} -> {base_type}")
        self._add_line(f"{name} = {base_type}")
        self._add_line("")

    def _generate_ffi_bitfield_def(self, stmt: FFIBitfieldDef):
        """生成C位域定义代码"""
        name = self._sanitize_name(stmt.name)
        base_type = self._ffi_type_map.get(stmt.base_type, 'ctypes.c_int')
        fields_code = []
        for f in stmt.fields:
            fname = self._sanitize_name(f['name'])
            bits = f['bits']
            fields_code.append(f"('{fname}', {base_type}, {bits})")
        fields_str = ', '.join(fields_code)
        self._add_line(f"# C位域: {name}")
        self._add_line(f"class {name}(ctypes.Structure):")
        self.indent_level += 1
        self._add_line(f"_fields_ = [{fields_str}]")
        self.indent_level -= 1
        self._add_line("")

    def _generate_ffi_funcptr_def(self, stmt: FFIFuncPtrDef):
        """生成C函数指针类型代码"""
        name = self._sanitize_name(stmt.name)
        arg_types = []
        for p in stmt.params:
            light_type = p.get('type', '整数')
            ctype = self._ffi_type_map.get(light_type, 'ctypes.c_int')
            arg_types.append(ctype)
        restype = 'None'
        if stmt.return_type:
            restype = self._ffi_type_map.get(stmt.return_type, 'ctypes.c_int')
        arg_types_str = ', '.join(arg_types) if arg_types else ''
        self._add_line(f"# C函数指针类型: {name}")
        self._add_line(f"{name} = ctypes.CFUNCTYPE({restype}, {arg_types_str})")
        self._add_line("")

    def _generate_ffi_debug_config(self, stmt: FFIDebugConfig):
        """生成FFI调试配置代码"""
        self._add_line("# FFI调试配置")
        self._add_line(f"_light_ffi.set_debug(")
        self.indent_level += 1
        self._add_line(f"enabled={stmt.enabled},")
        self._add_line(f"log_calls={stmt.log_calls},")
        self._add_line(f"log_types={stmt.log_types},")
        self._add_line(f"trace_memory={stmt.trace_memory},")
        self.indent_level -= 1
        self._add_line(")")
        self._add_line("")

    def _generate_ffi_preprocessor_def(self, stmt: FFIPreprocessorDef):
        """生成C预处理器宏代码"""
        name = self._sanitize_name(stmt.name)
        self._add_line(f"# C预处理器宏: {name} = {stmt.value}")
        self._add_line(f"_light_ffi.定义宏('{name}', {repr(stmt.value)})")
        self._add_line("")

    def _generate_embed_block(self, stmt: EmbedBlock):
        """生成嵌入块代码（v4.0 分层架构 L3/L4 统一入口）

        支持的嵌入类型（自左向右按首词路由）：
        - L4: 引 Python / Py            → 作用域隔离沙箱（E4），只暴露公共函数
        - L3: 引 SQL [库标签]           → 原生参数化 sqlite3（E1），防注入
        - L3: 引 模式/正则/Regex 名     → 命名捕获组成员访问类（E2）
        - L3: 引 公式/数学/Math 名      → sympy 表达式封装（E3）
        -     引 C                      → ctypes 编译（保留原实现）
        -     其他                      → 注释保留（保留原实现）
        """
        import textwrap
        import re as _light_re

        # 拆分首词（真正的语言/领域类型）和剩余标签（库名/正则名/公式名）
        lang_raw = stmt.language.strip() or "Python"
        lang_tokens = lang_raw.split()
        lang_main = lang_tokens[0].lower() if lang_tokens else "python"
        lang_label = "_".join(lang_tokens[1:]) if len(lang_tokens) > 1 else ""
        code = textwrap.dedent(stmt.code).strip()

        # -------- L4: Python / Py 作用域隔离沙箱（E4）--------
        if lang_main in ('python', 'py'):
            self._add_line(f"# --- L4: 引 Python{(' ' + lang_label) if lang_label else ''}（作用域隔离沙箱）---")
            self._add_line("import types as _light_types_mod")
            # 简化：使用 _LIGHT_L4_NS 稳定命名空间，避免递增 id 不稳定
            self._add_line("_LIGHT_L4_NS = _light_types_mod.ModuleType('light_l4')")
            self._add_line("_LIGHT_L4_SRC = '''\n" + code + "\n'''")
            self._add_line("exec(compile(_LIGHT_L4_SRC, '<l4_python>', 'exec'), _LIGHT_L4_NS.__dict__)")
            # 只导出公共标识符：以 l3_ / l4_ 开头 或 不以 _ 开头的 callable / 基本数据
            self._add_line("for _LIGHT_L4_NAME, _LIGHT_L4_OBJ in list(_LIGHT_L4_NS.__dict__.items()):")
            self._add_line("    if _LIGHT_L4_NAME.startswith('__'):")
            self._add_line("        continue")
            self._add_line("    # 规则：l3_* / l4_* 强制导出；其他不以 _ 开头的函数/类/普通数据也导出")
            self._add_line("    _ok = _LIGHT_L4_NAME.startswith('l3_') or _LIGHT_L4_NAME.startswith('l4_')")
            self._add_line("    if (not _ok) and not _LIGHT_L4_NAME.startswith('_'):")
            self._add_line("        import builtins as _light_bi")
            self._add_line("        _ok = callable(_LIGHT_L4_OBJ) or isinstance(_LIGHT_L4_OBJ, (_light_bi.int,_light_bi.float,_light_bi.str,_light_bi.list,_light_bi.dict,_light_bi.tuple,_light_bi.bool,_light_bi.type(None)))")
            self._add_line("    if _ok:")
            self._add_line("        globals()[_LIGHT_L4_NAME] = _LIGHT_L4_OBJ")
            self._add_line("del _LIGHT_L4_SRC, _LIGHT_L4_NAME, _LIGHT_L4_OBJ, _ok")
            self._add_line(f"# --- 结束 L4 引 Python{(' ' + lang_label) if lang_label else ''} ---")
            return

        # -------- L3: SQL 原生参数化封装（E1）--------
        if lang_main == 'sql':
            db_var = lang_label or "default"
            self._add_line(f"# --- L3: 引 SQL {lang_label}（原生参数化 sqlite3，防注入）---")
            self._add_line("import sqlite3 as _light_sqlite3")
            self._add_line(f"if '_DUAN_SQL_CONNS' not in globals(): _DUAN_SQL_CONNS = {{}}")
            self._add_line(f"if '{db_var}' not in _DUAN_SQL_CONNS:")
            self._add_line(f"    _DUAN_SQL_CONNS['{db_var}'] = _light_sqlite3.connect(':memory:' if '{db_var}' == 'default' else '{db_var}.db')")
            self._add_line(f"    _DUAN_SQL_CONNS['{db_var}'].row_factory = _light_sqlite3.Row")
            # 遍历 code（多行按 ; 分语句，允许 -- 注释）
            statements = [s.strip() for s in code.split(';') if s.strip()]
            for idx, raw_sql in enumerate(statements):
                # 跳过纯注释
                if all(line.lstrip().startswith('--') for line in raw_sql.split('\n') if line.strip()):
                    continue
                verb = raw_sql.lstrip().split(None, 1)[0].upper() if raw_sql.strip() else ''
                sql_one_line = " ".join(line.strip() for line in raw_sql.split('\n') if line.strip() and not line.lstrip().startswith('--'))
                sql_py_repr = repr(sql_one_line)
                if verb in ('SELECT', 'PRAGMA', 'WITH', 'EXPLAIN', 'SHOW'):
                    # 返回 list[dict] 的查询函数
                    fn_name = f"l3_sql_{db_var or 'default'}_q{idx}" if statements else f"l3_sql_query_{db_var}"
                    self._add_line(f"def {fn_name}(params=()):")
                    self._add_line(f"    _c = _DUAN_SQL_CONNS['{db_var}'].cursor()")
                    self._add_line(f"    _c.execute({sql_py_repr}, tuple(params))")
                    self._add_line(f"    return [dict(_r) for _r in _c.fetchall()]")
                else:
                    # 返回影响行数的 DDL/DML 函数
                    fn_name = f"l3_sql_{db_var or 'default'}_e{idx}" if statements else f"l3_sql_exec_{db_var}"
                    self._add_line(f"def {fn_name}(params=()):")
                    self._add_line(f"    _c = _DUAN_SQL_CONNS['{db_var}'].cursor()")
                    self._add_line(f"    _c.execute({sql_py_repr}, tuple(params))")
                    self._add_line(f"    _DUAN_SQL_CONNS['{db_var}'].commit()")
                    self._add_line(f"    return _c.rowcount")
            self._add_line(f"# --- 结束 L3 引 SQL {lang_label}（共 {len(statements)} 条语句）---")
            return

        # -------- L3: 模式 / 正则 / Regex 命名捕获组类（E2）--------
        if lang_main in ('模式', '正则', 'regex', 'regexp', 'matcher'):
            pattern_name = lang_label or "Matcher"
            safe_name = _light_re.sub(r'\W|^(?=\d)', '_', pattern_name) if pattern_name else "Matcher"
            # 允许引块里写多行：第一行是正则，后续是注释/别名
            lines = [ln for ln in code.split('\n') if ln.strip() and not ln.lstrip().startswith('#')]
            regex_src = lines[0] if lines else r""
            # 提取命名捕获组名
            named = _light_re.findall(r'\(\?P<([^>]+)>', regex_src)
            group_fields = ",".join(named) if named else ""
            self._add_line(f"# --- L3: 引 模式 {pattern_name}（正则命名捕获组 → 成员访问类）---")
            self._add_line("import re as _light_l3_re")
            self._add_line(f"_LIGHT_L3_RE_{safe_name.upper()} = _light_l3_re.compile({regex_src!r})")
            self._add_line(f"class L3Pattern_{safe_name}:")
            self._add_line(f"    __slots__ = ('_m','hit',{','.join(repr(n) for n in named) if named else '()'})")
            self._add_line(f"    def __init__(self, m):")
            self._add_line(f"        self._m = m; self.hit = m is not None")
            for n in named:
                self._add_line(f"        self.{n} = m.group('{n}') if self.hit else None")
            self._add_line(f"    def __bool__(self): return self.hit")
            self._add_line(f"    def __repr__(self):")
            self._add_line(f"        if not self.hit: return '{safe_name}<未命中>'")
            if named:
                parts = "+','+".join(['f"' + n + '={self.' + n + '}"' for n in named])
                self._add_line(f"        return '{safe_name}<' + {parts} + '>'")
            else:
                self._add_line(f"        return '{safe_name}<命中>'")
            self._add_line(f"    @classmethod")
            self._add_line(f"    def 匹配(cls, text): return cls(_LIGHT_L3_RE_{safe_name.upper()}.fullmatch(text))")
            self._add_line(f"    @classmethod")
            self._add_line(f"    def 搜索(cls, text): return cls(_LIGHT_L3_RE_{safe_name.upper()}.search(text))")
            self._add_line(f"    @classmethod")
            self._add_line(f"    def 查找全部(cls, text):")
            self._add_line(f"        ms = _LIGHT_L3_RE_{safe_name.upper()}.finditer(text)")
            self._add_line(f"        return [cls(m) for m in ms]")
            # 导出一个别名：中文模式名
            self._add_line(f"{pattern_name if pattern_name and pattern_name.isidentifier() else safe_name} = L3Pattern_{safe_name}")
            self._add_line(f"# --- 结束 L3 引 模式 {pattern_name}（命名组: {named or '∅'}）---")
            return

        # -------- L3: 公式 / 数学 / Math  sympy 封装（E3）--------
        if lang_main in ('公式', '数学', 'math', 'formula'):
            expr_name = lang_label or "Expr"
            safe_name = _light_re.sub(r'\W|^(?=\d)', '_', expr_name) if expr_name else "Expr"
            self._add_line(f"# --- L3: 引 公式 {expr_name}（sympy 封装）---")
            self._add_line("try:")
            self._add_line("    import sympy as _light_l3_sym")
            self._add_line("except Exception as _DUAN_L3_SYM_ERR:")
            self._add_line("    _light_l3_sym = None")
            # 解析公式行：支持 解...= / d/dx... / ∫(... →...) / 直接化简 / 矩阵乘法
            for idx, raw_line in enumerate(code.split('\n')):
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue
                # 去掉末尾句号/感叹号
                line_clean = line.rstrip('。！!？?；;')
                # 形式 1: 解 2x^2+5x-3=0
                m_solve = _light_re.match(r'^解\s+(.+?)\s*=\s*(.+?)\s*$', line_clean)
                if m_solve:
                    lhs, rhs = m_solve.group(1), m_solve.group(2)
                    fn_name = f"l3_math_solve_{safe_name}_{idx}"
                    self._add_line(f"def {fn_name}(**kw):")
                    self._add_line("    if not _light_l3_sym: raise RuntimeError(f'sympy未装: {_DUAN_L3_SYM_ERR}')")
                    self._add_line(f"    from sympy import Eq, solve, symbols, sympify")
                    self._add_line(f"    _all_sym = list(set(sympify({lhs!r}).free_symbols) | set(sympify({rhs!r}).free_symbols))")
                    self._add_line(f"    for _s in _all_sym: globals().setdefault(str(_s), _s)")
                    self._add_line(f"    _sol = solve(Eq(sympify({lhs!r}), sympify({rhs!r})), dict=True)")
                    self._add_line(f"    return _sol")
                    continue
                # 形式 2: d/dx (...)
                m_diff = _light_re.match(r'^d\s*/\s*d([a-zA-Z])\s*\((.+)\)$', line_clean)
                if m_diff:
                    vn, ex = m_diff.group(1), m_diff.group(2)
                    fn_name = f"l3_math_diff_{safe_name}_{vn}_{idx}"
                    self._add_line(f"def {fn_name}():")
                    self._add_line("    if not _light_l3_sym: raise RuntimeError(f'sympy未装: {_DUAN_L3_SYM_ERR}')")
                    self._add_line(f"    from sympy import diff, sympify, symbols")
                    self._add_line(f"    v = symbols({vn!r})")
                    self._add_line(f"    return str(diff(sympify({ex!r}), v))")
                    continue
                # 形式 3: 积分 ∫(a→b) f dx  或  积分 f 从 a 到 b
                m_int = _light_re.match(r'^[∫积分]\s*(\()?\s*(.+?)\s*→\s*(.+?)\s*\)?\s*(.+)\s*d([a-zA-Z])$', line_clean)
                m_int2 = _light_re.match(r'^积分\s+(.+?)\s+从\s+(.+?)\s+到\s+(.+?)$', line_clean)
                if m_int or m_int2:
                    if m_int:
                        a, b, f, vn = m_int.group(2), m_int.group(3), m_int.group(4), m_int.group(5)
                    else:
                        f, a, b = m_int2.group(1), m_int2.group(2), m_int2.group(3)
                        vn = 'x'
                    fn_name = f"l3_math_int_{safe_name}_{vn}_{idx}"
                    self._add_line(f"def {fn_name}():")
                    self._add_line("    if not _light_l3_sym: raise RuntimeError(f'sympy未装: {_DUAN_L3_SYM_ERR}')")
                    self._add_line(f"    from sympy import integrate, sympify, symbols")
                    self._add_line(f"    v = symbols({vn!r}); f = sympify({f.strip()!r})")
                    self._add_line(f"    r = integrate(f, (v, sympify({a!r}), sympify({b!r})))")
                    self._add_line(f"    try: return float(r.evalf())")
                    self._add_line(f"    except: return str(r)")
                    continue
                # 形式 4: 矩阵乘法 A * B
                m_mat = _light_re.match(r'^矩阵乘\s+(\[\[.*\]\])\s*\*\s*(\[\[.*\]\])$', line_clean)
                if m_mat:
                    fn_name = f"l3_math_mat_{safe_name}_{idx}"
                    self._add_line(f"def {fn_name}():")
                    self._add_line("    if not _light_l3_sym: raise RuntimeError(f'sympy未装: {_DUAN_L3_SYM_ERR}')")
                    self._add_line(f"    from sympy import Matrix")
                    self._add_line(f"    R = Matrix({m_mat.group(1)}) * Matrix({m_mat.group(2)})")
                    self._add_line(f"    return [list(row) for row in R.tolist()]")
                    continue
                # 默认：表达式化简
                fn_name = f"l3_math_simp_{safe_name}_{idx}"
                self._add_line(f"def {fn_name}():")
                self._add_line("    if not _light_l3_sym: raise RuntimeError(f'sympy未装: {_DUAN_L3_SYM_ERR}')")
                self._add_line(f"    from sympy import simplify, sympify")
                self._add_line(f"    return str(simplify(sympify({line_clean!r})))")
            self._add_line(f"# --- 结束 L3 引 公式 {expr_name} ---")
            return

        # -------- L4: C 嵌入（gcc 编译 + ctypes 动态加载）--------
        if lang_main in ('c',):
            self._add_line(f"# --- L4: 引 C（gcc 编译 + ctypes 动态加载）---")
            self._add_line("import ctypes as _light_ctypes")
            self._add_line("import tempfile as _light_tmp")
            self._add_line("import os as _light_os")
            self._add_line("import subprocess as _light_sp")
            self._add_line("import sys as _light_sys")
            self._add_line("import re as _light_l4_re")
            self._add_line("_DUAN_C_CODE = '''")
            for line in code.split('\n'):
                self._add_line(line)
            self._add_line("'''")
            # 平台检测：.so vs .dll
            self._add_line("_DUAN_C_EXT = '.dll' if _light_sys.platform == 'win32' else '.so'")
            # 编译器检测：gcc > cc > clang
            self._add_line("_DUAN_C_CC = None")
            self._add_line("for _DUAN_C_CAND in ['gcc', 'cc', 'clang']:")
            self._add_line("    try:")
            self._add_line("        _light_sp.run([_DUAN_C_CAND, '--version'], capture_output=True, check=True)")
            self._add_line("        _DUAN_C_CC = _DUAN_C_CAND; break")
            self._add_line("    except Exception: pass")
            # 写临时 C 文件
            self._add_line("_DUAN_C_SRC = _light_tmp.NamedTemporaryFile(suffix='.c', delete=False, mode='w', encoding='utf-8')")
            self._add_line("_DUAN_C_SRC.write('#include <stdlib.h>\\n#include <string.h>\\n#include <math.h>\\n')")
            self._add_line("_DUAN_C_SRC.write(_DUAN_C_CODE)")
            self._add_line("_DUAN_C_SRC.close()")
            self._add_line("_DUAN_C_LIB = _DUAN_C_SRC.name.replace('.c', _DUAN_C_EXT)")
            # 编译
            self._add_line("if _DUAN_C_CC:")
            self._add_line("    _light_sp.run([_DUAN_C_CC, '-shared', '-fPIC', '-O2', '-o', _DUAN_C_LIB, _DUAN_C_SRC.name, '-lm'], check=True)")
            # 加载动态库
            self._add_line("_DUAN_C_DLL = _light_ctypes.CDLL(_DUAN_C_LIB) if _DUAN_C_CC else None")
            # 自动解析 C 函数签名，生成 Python 可调用封装
            self._add_line("_DUAN_C_FUNCS = _light_l4_re.findall(r'(?:int|float|double|void|long|char\\s*\\*)\\s+(\\w+)\\s*\\(', _DUAN_C_CODE)")
            self._add_line("for _DUAN_C_FN in _DUAN_C_FUNCS:")
            self._add_line("    if _DUAN_C_DLL:")
            self._add_line("        try:")
            # 尝试推断返回类型和参数类型
            self._add_line("            _DUAN_C_FN_OBJ = getattr(_DUAN_C_DLL, _DUAN_C_FN)")
            self._add_line("            _DUAN_C_FN_OBJ.restype = _light_ctypes.c_double")
            self._add_line("            globals()[_DUAN_C_FN] = _DUAN_C_FN_OBJ")
            self._add_line("        except Exception:")
            self._add_line("            globals()[_DUAN_C_FN] = lambda *a, _fn=_DUAN_C_FN: f'[C:{_fn} 未加载]'")
            self._add_line("    else:")
            self._add_line("        globals()[_DUAN_C_FN] = lambda *a, _fn=_DUAN_C_FN: f'[C:{_fn} 编译器未找到]'")
            self._add_line("del _DUAN_C_CODE, _DUAN_C_FN, _DUAN_C_FUNCS")
            self._add_line(f"# --- 结束 L4 引 C ---")
            return

        # -------- L4: Go 嵌入（go build -buildmode=c-shared）--------
        if lang_main in ('go', 'golang'):
            self._add_line(f"# --- L4: 引 Go（go build -buildmode=c-shared + ctypes 加载）---")
            self._add_line("import ctypes as _light_ctypes")
            self._add_line("import tempfile as _light_tmp")
            self._add_line("import os as _light_os")
            self._add_line("import subprocess as _light_sp")
            self._add_line("import sys as _light_sys")
            self._add_line("import re as _light_l4_re")
            self._add_line("_DUAN_GO_CODE = '''")
            for line in code.split('\n'):
                self._add_line(line)
            self._add_line("'''")
            # 检测 Go 编译器
            self._add_line("_DUAN_GO_OK = False")
            self._add_line("try:")
            self._add_line("    _light_sp.run(['go', 'version'], capture_output=True, check=True)")
            self._add_line("    _DUAN_GO_OK = True")
            self._add_line("except Exception: pass")
            # 写 Go 源文件
            self._add_line("if _DUAN_GO_OK:")
            self._add_line("    _DUAN_GO_EXT = '.dll' if _light_sys.platform == 'win32' else '.so'")
            self._add_line("    _DUAN_GO_DIR = _light_tmp.mkdtemp(prefix='light_go_')")
            self._add_line("    _DUAN_GO_SRC = _light_os.path.join(_DUAN_GO_DIR, 'main.go')")
            # 包装 Go 代码为 c-shared 导出库
            self._add_line("    _DUAN_GO_WRAPPED = 'package main\\n\\nimport \"C\"\\n\\n' + _DUAN_GO_CODE")
            self._add_line("    with open(_DUAN_GO_SRC, 'w', encoding='utf-8') as _f: _f.write(_DUAN_GO_WRAPPED)")
            # 初始化 go.mod
            self._add_line("    _light_sp.run(['go', 'mod', 'init', 'light_l4_go'], cwd=_DUAN_GO_DIR, capture_output=True)")
            # 编译为 c-shared 库
            self._add_line("    _DUAN_GO_LIB = _light_os.path.join(_DUAN_GO_DIR, 'light_go' + _DUAN_GO_EXT)")
            self._add_line("    try:")
            self._add_line("        _light_sp.run(['go', 'build', '-buildmode=c-shared', '-o', _DUAN_GO_LIB, _DUAN_GO_SRC], cwd=_DUAN_GO_DIR, check=True)")
            self._add_line("        _DUAN_GO_DLL = _light_ctypes.CDLL(_DUAN_GO_LIB)")
            # 自动解析 //export GoFuncName 导出函数
            self._add_line("        _DUAN_GO_EXPORTS = _light_l4_re.findall(r'//export\\s+(\\w+)', _DUAN_GO_CODE)")
            self._add_line("        for _DUAN_GO_FN in _DUAN_GO_EXPORTS:")
            self._add_line("            try:")
            self._add_line("                _DUAN_GO_FN_OBJ = getattr(_DUAN_GO_DLL, _DUAN_GO_FN)")
            self._add_line("                _DUAN_GO_FN_OBJ.restype = _light_ctypes.c_double")
            self._add_line("                globals()[_DUAN_GO_FN] = _DUAN_GO_FN_OBJ")
            self._add_line("            except Exception:")
            self._add_line("                globals()[_DUAN_GO_FN] = lambda *a, _fn=_DUAN_GO_FN: f'[Go:{_fn} 未加载]'")
            self._add_line("    except Exception as _DUAN_GO_ERR:")
            self._add_line("        print(f'[L4 Go] 编译失败: {_DUAN_GO_ERR}')")
            self._add_line("else:")
            self._add_line("    print('[L4 Go] Go 编译器未安装, 跳过')")
            self._add_line("del _DUAN_GO_CODE")
            self._add_line(f"# --- 结束 L4 引 Go ---")
            return

        # -------- L4: MoonBit 嵌入（moon build --target wasm）--------
        if lang_main in ('moonbit', 'mbt', 'moon'):
            self._add_line(f"# --- L4: 引 MoonBit（moon build --target wasm + wasmtime 执行）---")
            self._add_line("import tempfile as _light_tmp")
            self._add_line("import os as _light_os")
            self._add_line("import subprocess as _light_sp")
            self._add_line("import sys as _light_sys")
            self._add_line("import json as _light_json")
            self._add_line("_DUAN_MBT_CODE = '''")
            for line in code.split('\n'):
                self._add_line(line)
            self._add_line("'''")
            # 检测 MoonBit 工具链
            self._add_line("_DUAN_MBT_OK = False")
            self._add_line("try:")
            self._add_line("    _light_sp.run(['moon', 'version'], capture_output=True, check=True)")
            self._add_line("    _DUAN_MBT_OK = True")
            self._add_line("except Exception: pass")
            # 创建 MoonBit 项目并编译
            self._add_line("if _DUAN_MBT_OK:")
            self._add_line("    _DUAN_MBT_DIR = _light_tmp.mkdtemp(prefix='light_mbt_')")
            self._add_line("    _DUAN_MBT_SRC = _light_os.path.join(_DUAN_MBT_DIR, 'main.mbt')")
            self._add_line("    with open(_DUAN_MBT_SRC, 'w', encoding='utf-8') as _f: _f.write(_DUAN_MBT_CODE)")
            # 生成 moon.pkg.json
            self._add_line("    _DUAN_MBT_PKG = _light_os.path.join(_DUAN_MBT_DIR, 'moon.pkg.json')")
            self._add_line("    with open(_DUAN_MBT_PKG, 'w') as _f: _light_json.dump({}, _f)")
            # 编译为 wasm
            self._add_line("    try:")
            self._add_line("        _light_sp.run(['moon', 'build', '--target', 'wasm'], cwd=_DUAN_MBT_DIR, check=True, capture_output=True)")
            # 尝试用 wasmtime 执行
            self._add_line("        _DUAN_MBT_WASM = _light_os.path.join(_DUAN_MBT_DIR, 'target', 'wasm', 'release', 'build', 'main.wasm')")
            self._add_line("        if not _light_os.path.exists(_DUAN_MBT_WASM):")
            # 尝试其他路径
            self._add_line("            _DUAN_MBT_WASM = _light_os.path.join(_DUAN_MBT_DIR, 'target', 'wasm', 'debug', 'build', 'main.wasm')")
            self._add_line("        if _light_os.path.exists(_DUAN_MBT_WASM):")
            self._add_line("            try:")
            self._add_line("                _DUAN_MBT_OUT = _light_sp.run(['wasmtime', _DUAN_MBT_WASM], capture_output=True, text=True, timeout=30)")
            self._add_line("                print(f'[MoonBit wasm] {_DUAN_MBT_OUT.stdout.strip()}')")
            self._add_line("                if _DUAN_MBT_OUT.stderr: print(f'[MoonBit wasm stderr] {_DUAN_MBT_OUT.stderr.strip()}')")
            self._add_line("            except Exception as _DUAN_MBT_WASM_ERR:")
            self._add_line("                print(f'[MoonBit] wasm 编译成功但 wasmtime 执行失败: {_DUAN_MBT_WASM_ERR}')")
            self._add_line("                print(f'[MoonBit] wasm 文件位于: {_DUAN_MBT_WASM}')")
            self._add_line("        else:")
            self._add_line("            print(f'[MoonBit] 编译完成但未找到 wasm 文件')")
            self._add_line("    except Exception as _DUAN_MBT_ERR:")
            self._add_line("        print(f'[L4 MoonBit] 编译失败: {_DUAN_MBT_ERR}')")
            self._add_line("else:")
            self._add_line("    print('[L4 MoonBit] MoonBit 工具链未安装, 跳过')")
            self._add_line("del _DUAN_MBT_CODE")
            self._add_line(f"# --- 结束 L4 引 MoonBit ---")
            return

        # -------- 不支持的语言：注释保留 --------
        self._add_line(f"# --- 嵌入 {lang_raw}（暂不支持直接执行）---")
        for line in code.split('\n'):
            self._add_line(f"# {line}")
        self._add_line(f"# --- 结束嵌入 ---")

    # --- 辅助：生成递增 id（嵌入沙箱变量、SQL 函数名去重）---
    def _fresh_id(self):
        if not hasattr(self, '_light_embed_id_counter'):
            self._light_embed_id_counter = 0
        self._light_embed_id_counter += 1
        self._prev_fresh_id = self._light_embed_id_counter
        return self._light_embed_id_counter


# =============================================================================
# 测试
# =============================================================================

if __name__ == '__main__':
    from light_parser_v3 import LightParser
    
    print("=" * 60)
    print("光明Python代码生成器测试")
    print("=" * 60)
    
    # 测试代码
    test_cases = [
        # 变量声明
        ('变量声明', '定义甲等于三。'),
        
        # 运算
        ('运算', '定义丙等于三加五。'),
        
        # 条件语句
        ('条件', '如果甲大于十那么打印甲。'),
        
        # 段落定义
        ('段落', '《计算》段(甲, 乙)：返回甲加乙。'),
        
        # 管道操作
        ('管道', '数据 -> 过滤 -> 排序。'),
    ]
    
    parser = LightParser()
    generator = PythonCodeGenerator()
    
    for name, code in test_cases:
        print(f"\n--- 测试: {name} ---")
        print(f"光明代码: {code}")
        
        try:
            # 解析
            module = parser.parse(code)
            
            # 生成Python代码
            python_code = generator.generate(module)
            
            print(f"\nPython代码:")
            print(python_code)
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
