"""
光明（Light）编程语言 - Python代码生成器

将光明AST转换为Python代码
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from typing import List, Optional, Dict
from light_parser_v3 import *
from keywords import VERB_ARITY
# v7 单 20：L4 引 C/Go 块导出名提取，与词法预扫描共用同一份正则（见 lexer.py）
from lexer import extract_embed_export_names
import ast_nodes as ast_nodes_module


# 需要导入新的AST节点类型
from light_parser_v3 import ImportStmt, ExportStmt, IndexAccess, SliceExpr, SetComprehension, TupleLiteral, BreakStmt, ContinueStmt, PassStmt, ClassInstantiation, MemberAccess, TryStmt, ThrowStmt, Parameter, ParameterList, StringInterpolation, ListComprehension, LambdaExpression, MatchStmt, MatchCase, MatchPattern, DictComprehension, DestructuringAssignment, WithStmt, DecoratorDefinition, DictLiteral, InterfaceDefinition, MethodSignature, IndexedAssignment, RangeExpr, FFILoadLibrary, FFIFunctionDecl, FFIStructDef, FFICallbackDef, FFICreateArray, FFISetArrayElement, FFIAllocMemory, FFIFreeMemory, FFISetPointerValue, FFISetErrno, FFITryCatch, FFIEnumDef, FFIUnionDef, FFICreateCallback, FFIVarArgsDecl, FFIStructByValue, FFILibraryPath, FFITypedefDef, FFIBitfieldDef, FFIFuncPtrDef, FFIDebugConfig, FFIPreprocessorDef, FFIPointerType, FFIArrayType, FFIAddressOf, FFIDereference, FFIPointerOffset, FFIGetLastError, FFIGetErrno
from ast_nodes_v3 import Assignment, TypeCheckToggleStmt, AwaitExpr, KeywordArg, IndexedCompoundAssignment, PassStmt, AssignmentExpression, SetLiteral, EmbedBlock, FunctionCallExpr, CatchClause, YieldStmt, AsyncScope, DecoratedFunction, DecoratorInfo, AssertStmt
from ast_nodes import ExpressionStatement, SegmentName


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
        
        # 是否需要导入 asyncio
        self._needs_asyncio = False
        
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
        # 局部变量名追踪（作用域敏感）：一旦某名字被「设/段落参数/循环变量/
        # with-as/解包/异常绑定」等形式绑定为局部变量，它就遮蔽同名的内置函数
        # 映射（映射→map、读取→input、范围→range 等），此后不再做内置式改写。
        # 进出段落/类方法时用 _push_scope/_pop_scope 保存与恢复，防止局部名泄漏
        # 到模块级或污染兄弟段落。存的是「光明源码里的原始名字」（与 expr.name、
        # _user_defined_functions 的键一致），不是 sanitize 之后的 Python 名。
        self._local_variables: set = set()
        
        # 是否在函数/段落内部（控制 return 生成）
        self._in_function: bool = False
        
        # 是否在循环内部（控制 break/continue 生成）
        self._in_loop: bool = False
        
        # 方法名映射（中文到英文）
        self.method_name_map = {
            '追加': 'append',
            '添加': 'append',
            '插入': 'insert',
            '删除': 'remove',
            '弹出': 'pop',
            '清空': 'clear',
            '反转': 'reverse',
            '包含': '__contains__',
            '排序': 'sort',
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

        # 方法定义名映射：与方法调用映射(method_name_map)保持一致，使
        # 用户自定义类的方法“定义名”与“调用名”在生成的 Python 中一致。
        # 调用侧 method_name_map 会把 弹出->pop、插入->insert 等翻译成中文
        # 调用(obj.pop())，但定义侧原先保留中文(def 弹出)，导致
        # 'X' object has no attribute 'pop'。此处把定义名也翻译过去即可对齐。
        # 排除 长度/取长度/包含：它们的调用被特判为 len(obj) / (item in obj)，
        # 与方法签名不匹配，翻译成 __len__/__contains__ 会破坏参数，故保留中文。
        self._method_def_name_map = {
            k: v for k, v in self.method_name_map.items()
            if k not in ('长度', '取长度', '包含')
        }

        # 模块名映射（中文到Python模块）
        # 注意：有独立 stdlib 实现（含中文函数名）的模块不要映射到 Python 标准库
        self.module_name_map = {
        }
        
        # 异常名映射（中文→Python）
        self.exception_name_map = {
            '迭代停止': 'StopIteration',
            '值错误': 'ValueError',
            '类型错误': 'TypeError',
            '索引错误': 'IndexError',
            '键错误': 'KeyError',
            '属性错误': 'AttributeError',
            '导入错误': 'ImportError',
            '零除错误': 'ZeroDivisionError',
            '文件错误': 'FileNotFoundError',
            '运行时错误': 'RuntimeError',
            '溢出错误': 'OverflowError',
            '递归错误': 'RecursionError',
            '内存错误': 'MemoryError',
            '系统错误': 'SystemError',
            '断言错误': 'AssertionError',
            '停止迭代': 'StopIteration',
            '错误': 'Exception',
            '异常': 'Exception',
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
            '印': 'print',
            '打印': 'print',
            '显示': 'print',
            '输出': 'print',
            '断言': '_light_assert',
            '读取': 'input',
            '输入': 'input',
            '长': 'len',
            '长度': 'len',
            '首': 'lambda x: x[0]',
            '末': 'lambda x: x[-1]',
            # 可空类型解包（等价于 值!）
            'unwrap': '_light_unwrap',
            '解包': '_light_unwrap',
            
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
            # 数学函数补充（LLVM后端已有，Python后端补齐）
            '平方根': 'math.sqrt',
            '对数': 'math.log',
            '指数': 'math.exp',
            '正弦': 'math.sin',
            '余弦': 'math.cos',
            '正切': 'math.tan',
            '反正弦': 'math.asin',
            '反余弦': 'math.acos',
            '反正切': 'math.atan',
            '反正切2': 'math.atan2',
            '阶乘': 'math.factorial',
            '向上取整': 'math.ceil',
            '向下取整': 'math.floor',
            '最大公约数': 'math.gcd',
            '幂': 'pow',
            '平方': "lambda x: x*x",
            '立方': "lambda x: x*x*x",
            # 随机函数
            '随机': 'lambda *a: __import__("random").random()',
            '随机整数': 'random.randint',
            '随机浮点': 'random.uniform',
            '随机选择': 'random.choice',
            '洗牌': 'lambda seq: __import__("random").sample(list(seq), len(list(seq))) if hasattr(seq, "__len__") else seq',
            # 字符串操作函数
            '拼接': "lambda *a: (a[-1] if len(a) > 1 else '').join(str(x) for x in a[0])",
            '切分': "lambda x, sep=None: list(x) if sep is None else x.split(sep)",
            
            # 文件I/O
            '读取文件': '_light_builtin.读取文件',
            '_读文件': '_light_builtin._读文件',
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
            '移动文件系统': '_light_builtin.移动文件系统',

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
            # v7 单 19：短类型名兼作转换函数。规范把 串()/整()/列() 当一组三兄弟
            # 明文承诺（docs/L2_文言体语法规范_v4.0.md:287 一行内两种身份并用：
            # 设 文字: 串 = 串(123)；同段 :286 整(...)、:288 列(...)），而实现里
            # 只有 列 落地了（:363 '列': '_light_builtin.列'），串 与 整 从缺。
            # 与长名同族（走 stdlib）而不是映射到 str/int，是为了跟已落地的 列 一致。
            # 类型注解一侧不受影响：注解走 _map_type / _TYPE_NAME_MAP 两个
            # 字符串映射，从不读 builtin_map。
            '串': '_light_builtin.转字符串',
            '整': '_light_builtin.转整数',
            '转字符串': '_light_builtin.转字符串',
            '到字符串': '_light_builtin.转字符串',
            '转换字符串': '_light_builtin.转字符串',
            # v7 新单 B：`转成字符串` 是本族第 6 个拼法。
            # 取证：全仓 grep 只在 examples/L2_wenyan/学生模块.light:34,49 与
            # examples/L1_vs_L2_README.md 出现，**实现里从未定义过**，所以
            # examples/L2_wenyan/主程序.light 跑到 字符串化() 就 NameError。
            # 判为「别名从缺」而非「例子写错」：本族已收 转串/串/转字符串/到字符串/
            # 转换字符串 五个同义拼法（:326,:334,:336-338），可见设计上就是宽松收词；
            # 而例子是被测输入不许改（硬规则 2）。补别名零新机制、零新语义。
            '转成字符串': '_light_builtin.转字符串',
            '到数字': '_light_builtin.转浮点',
            '转数字': '_light_builtin.转浮点',
            '字符串长度': '_light_builtin.字符串长度',
            '显示宽度': '_light_builtin.显示宽度',
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
            '最后索引': '_light_builtin.最后索引',
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
            '列表插入': '_light_builtin.列表插入',
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

            # 随机数
            '随机整数': '_light_builtin.随机整数',
            '随机浮点': '_light_builtin.随机浮点',
            '随机选择': '_light_builtin.随机选择',

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
    
    def _register_imported_names(self, module) -> None:
        """把 import 显式引入的名字登记为「用户已定义」。

        为什么必须做：内置函数映射（builtin_map）是无条件替换的，
        `范围(0,3)` 会被直接翻译成 `range(0,3)`。于是
        `从《列表工具》导入《范围》` 之后再调用 `范围`，拿到的仍是
        Python 的 range —— 用户导入的东西被静默忽略了。更糟的是
        `包含` 这类映射到 `_light_builtin.包含`（该内置并不存在），
        运行期直接 AttributeError。

        显式导入是用户最强的意图表达，必须压过内置映射。否则
        「用光明写光明标准库」只要撞上内置名就永远调不通。

        这里做整棵树的遍历（含类体、函数体里的局部导入），
        并在生成任何代码之前完成，所以不受书写顺序影响。
        """
        # AST 节点用 __slots__，各类块语句的子语句字段名不统一，逐个尝试
        CHILD_ATTRS = (
            'statements', 'body', 'then_body', 'else_body', 'orelse',
            'try_body', 'catch_body', 'finally_body', 'catch_clauses',
            'methods', 'members', 'cases', 'stages',
        )

        seen = set()

        def walk(node):
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for item in node:
                    walk(item)
                return
            if id(node) in seen:
                return
            seen.add(id(node))

            if isinstance(node, ImportStmt):
                for sym in (getattr(node, 'symbols', None) or ()):
                    if isinstance(sym, str) and sym:
                        self._user_defined_functions.add(sym)
                alias = getattr(node, 'alias', None)
                if isinstance(alias, str) and alias:
                    self._user_defined_functions.add(alias)

            # v7 单 20：L4 引 C/Go 块导出的函数名与显式 import 同级 —— 都是
            # 「用户显式声明了这个名字」，必须压过 builtin_map。否则 J2 的
            # `引 Go:` 里 //export 求和，光明侧 求和(...) 仍被顶成 sum(...)。
            # 必须放在这个预扫描里而不是 _generate_embed_block 里懒登记：
            # CodeGenerator 是单遍生成，块写在调用点之后时懒登记来不及。
            if isinstance(node, EmbedBlock):
                self._user_defined_functions |= extract_embed_export_names(
                    getattr(node, 'language', '') or '',
                    getattr(node, 'code', '') or '')

            for attr in CHILD_ATTRS:
                child = getattr(node, attr, None)
                if isinstance(child, (list, tuple)):
                    walk(child)

        try:
            walk(getattr(module, 'statements', None))
        except Exception:
            # 预扫描失败不应阻断编译，最坏退化成旧行为
            pass
    
    # ------------------------------------------------------------------
    # 局部变量作用域跟踪（单 03：内置名劫持局部变量）
    #
    # 为什么不复用 _user_defined_functions：那个集合是「整个模块全局、只增不减」
    # 的（import 符号 + 段落名），语义上是"这个名字是用户的函数"。局部变量必须
    # 是作用域敏感的——`段落 甲` 里的 `设 映射 为 …` 不能让 `段落 乙` 里真正想调
    # 内置 `映射(f, 列)` 的地方跟着失效。所以另开一个可保存/恢复的集合。
    # ------------------------------------------------------------------
    def _bind_local(self, *names) -> None:
        """把名字登记为「当前作用域的局部变量」。

        接受 str / Parameter 节点 / 可迭代（列表、元组），非法值静默跳过——
        代码生成器不应因为一个绑定形式没见过就整体崩掉。
        """
        for n in names:
            if n is None:
                continue
            if isinstance(n, (list, tuple, set)):
                self._bind_local(*n)
                continue
            if not isinstance(n, str):
                # Parameter / Identifier 之类节点：取 .name
                n = getattr(n, 'name', None)
                if not isinstance(n, str):
                    continue
            n = n.strip()
            if not n:
                continue
            # `己.当前` 这类是属性而非局部变量，不登记（否则会误遮蔽同名内置）
            if '.' in n:
                continue
            self._local_variables.add(n)

    def _push_local_scope(self) -> set:
        """进入段落/方法：继承外层可见的局部名，返回快照供 _pop_local_scope 恢复。

        继承（而非清空）是刻意的：Python 里嵌套函数能读到外层/模块级变量，
        所以外层的 `设 映射 为 …` 在内层依然遮蔽内置 `映射`。
        """
        saved = self._local_variables
        self._local_variables = set(saved)
        return saved

    def _pop_local_scope(self, saved: set) -> None:
        """离开段落/方法：丢弃本作用域新增的绑定，恢复外层视图。"""
        self._local_variables = saved

    def _shadows_builtin(self, name) -> bool:
        """该名字是否已被局部变量绑定、从而遮蔽了内置函数映射。

        用户显式定义的函数（_user_defined_functions）走原有护栏，不在此处判定。
        """
        return (isinstance(name, str)
                and name in self._local_variables
                and name not in self._user_defined_functions)

    def generate(self, module: Module) -> str:
        """生成Python代码"""
        self.output_lines = []
        self.indent_level = 0  # 重置缩进级别，防止跨条目状态污染
        self._user_defined_functions = set()  # 重置用户自定义函数追踪
        self._local_variables = set()  # 重置局部变量追踪
        self._ffi_user_types = {}  # 重置 FFI 用户自定义类型注册表
        
        # 预扫描：显式 import 进来的名字优先级高于内置函数映射
        self._register_imported_names(module)
        
        # 添加文件头
        self._add_line("# 由光明编译器生成")
        self._add_line("# 源文件: 光明代码")
        self._add_line("")
        
        # 添加标准库导入
        self._add_line("import sys")
        self._add_line("import os")
        self._add_line("import ctypes")
        self._add_line("from typing import Any, Optional")
        self._add_line("import math")
        self._add_line("import random")
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
        self._add_line("if _light_stdlib:")
        self._add_line("    _light_parent = os.path.dirname(_light_stdlib)")
        self._add_line("    if _light_parent not in sys.path:")
        self._add_line("        sys.path.insert(0, _light_parent)")
        self._add_line("")
        self._add_line("# 让 import 机制认识纯光明模块（只有 .light、没有 .py 的那种）")
        self._add_line("try:")
        self._add_line("    import _light_import_hook as _light_hook")
        self._add_line("    _light_hook.install([_light_stdlib, _light_file_dir, os.getcwd()])")
        self._add_line("except Exception:")
        self._add_line("    pass")
        self._add_line("")
        # FFI 模块：尽量导入；失败时降级为占位对象，避免非 FFI 程序因 stdlib 路径问题整体崩溃。
        # 对应 E2E 失败项 F01：编译产物不可移植，临时目录无 stdlib 时 import 直接抛错。
        # _light_ffi_available 为「FFI 可用」特征位，下游/测试可据此判断 FFI 能力是否具备。
        self._add_line("# FFI 模块：尽量导入；失败则降级为占位对象（见 _light_ffi_available 特征位），避免非 FFI 程序因 stdlib 路径缺失而整体崩溃")
        self._add_line("try:")
        self._add_line("    import stdlib.FFI as _light_ffi")
        self._add_line("    _light_ffi_available = True")
        self._add_line("except Exception:")
        self._add_line("    _light_ffi_available = False")
        self._add_line("    class _LightFFIUnavailable:")
        self._add_line("        def __getattr__(self, _name):")
        self._add_line("            raise RuntimeError('FFI 不可用：未能导入 stdlib.FFI（请确认 stdlib 路径已加入 sys.path）')")
        self._add_line("    _light_ffi = _LightFFIUnavailable()")
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
        self._add_line("        _light_builtin.列表获取 = lambda lst, i: lst[i]")
        self._add_line("        _light_builtin.列表弹出 = lambda lst, i=-1: lst.pop(i)")
        self._add_line("        _light_builtin.列表插入 = lambda lst, i, v: lst.insert(i, v)")
        self._add_line("        _light_builtin.列表包含 = lambda lst, item: item in lst")
        self._add_line("        _light_builtin.包含 = lambda sub, s: sub in s")
        self._add_line("        _light_builtin.字符串包含 = lambda s, sub: sub in s")
        self._add_line("        _light_builtin.字符串替换 = lambda s, old, new: s.replace(old, new)")
        self._add_line("        _light_builtin.字符串反转 = lambda s: s[::-1]")
        self._add_line("        _light_builtin.字符串长度 = len")
        self._add_line("        _light_builtin.显示宽度 = lambda text: sum(2 if __import__('unicodedata').east_asian_width(ch) in ('W', 'F') else 1 for ch in str(text))")
        self._add_line("        _light_builtin.字符串获取 = lambda s, i: s[i]")
        self._add_line("        _light_builtin.截取 = lambda s, start, end: s[start:end]")
        self._add_line("        _light_builtin.转大写 = lambda s: s.upper()")
        self._add_line("        _light_builtin.转小写 = lambda s: s.lower()")
        self._add_line("        _light_builtin.结尾 = lambda s, suffix: s.endswith(suffix)")
        self._add_line("        _light_builtin.开头 = lambda s, prefix: s.startswith(prefix)")
        self._add_line("        _light_builtin.去除空白 = lambda s: s.strip()")
        self._add_line("        _light_builtin.分割字符串 = lambda s, sep=None: s.split(sep)")
        self._add_line("        _light_builtin.连接字符串 = lambda parts, sep='': sep.join(parts)")
        self._add_line("        _light_builtin.替换字符串 = lambda s, old, new: s.replace(old, new)")
        self._add_line("        _light_builtin.字符串分割 = lambda s, sep=None: s.split(sep)")
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
        self._add_line("    _light_builtin.列表获取 = lambda lst, i: lst[i]")
        self._add_line("    _light_builtin.列表弹出 = lambda lst, i=-1: lst.pop(i)")
        self._add_line("    _light_builtin.列表插入 = lambda lst, i, v: lst.insert(i, v)")
        self._add_line("    _light_builtin.列表包含 = lambda lst, item: item in lst")
        self._add_line("    _light_builtin.包含 = lambda sub, s: sub in s")
        self._add_line("    _light_builtin.字符串包含 = lambda s, sub: sub in s")
        self._add_line("    _light_builtin.字符串替换 = lambda s, old, new: s.replace(old, new)")
        self._add_line("    _light_builtin.字符串反转 = lambda s: s[::-1]")
        self._add_line("    _light_builtin.字符串长度 = len")
        self._add_line("    _light_builtin.字符串获取 = lambda s, i: s[i]")
        self._add_line("    _light_builtin.截取 = lambda s, start, end: s[start:end]")
        self._add_line("    _light_builtin.转大写 = lambda s: s.upper()")
        self._add_line("    _light_builtin.转小写 = lambda s: s.lower()")
        self._add_line("    _light_builtin.结尾 = lambda s, suffix: s.endswith(suffix)")
        self._add_line("    _light_builtin.开头 = lambda s, prefix: s.startswith(prefix)")
        self._add_line("    _light_builtin.去除空白 = lambda s: s.strip()")
        self._add_line("    _light_builtin.分割字符串 = lambda s, sep=None: s.split(sep)")
        self._add_line("    _light_builtin.连接字符串 = lambda parts, sep='': sep.join(parts)")
        self._add_line("    _light_builtin.替换字符串 = lambda s, old, new: s.replace(old, new)")
        self._add_line("    _light_builtin.字符串分割 = lambda s, sep=None: s.split(sep)")
        self._add_line("    _light_builtin.字典创建 = dict")
        self._add_line("    _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})")
        self._add_line("    _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)")
        self._add_line("    _light_builtin.字典键列表 = lambda d: list(d.keys())")
        self._add_line("    _light_builtin.字典包含键 = lambda d, k: k in d")
        self._add_line("    _light_builtin.时间戳 = lambda: __import__('time').time()")
        self._add_line("    _light_builtin.格式化时间 = lambda t, f='%Y-%m-%d %H:%M:%S': __import__('datetime').datetime.fromtimestamp(t).strftime(f) if isinstance(t, (int, float)) else __import__('datetime').datetime.strptime(t, '%Y-%m-%d %H:%M:%S').strftime(f)")
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
        # 连接辅助函数：中文里「列表.连接(分隔符)」和「分隔符.连接(列表)」都通顺，
        # 但 join 只接受后者。原先无条件发射 obj.join(arg)，前者一律
        # AttributeError: 'list' object has no attribute 'join'
        # （LLM 兜底生成的「词序反转」块正是栽在这里）。按运行期类型分派即可两种都成立。
        self._add_line("# 连接辅助函数（列表.连接(分隔符) 与 分隔符.连接(列表) 均可）")
        self._add_line("def _light_join(_o, _s=''):")
        self._add_line("    if isinstance(_o, str):")
        self._add_line("        return _o.join(_s)")
        self._add_line("    return _s.join([_x if isinstance(_x, str) else str(_x) for _x in _o])")
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
        
        if self._needs_asyncio:
            asyncio_import = "import asyncio"
            # 插入在文件头之后，第一个语句之前
            insert_pos = 0
            for i, line in enumerate(self.output_lines):
                if line.startswith("#") or line == "":
                    insert_pos = i + 1
                else:
                    break
            self.output_lines.insert(insert_pos, "")
            self.output_lines.insert(insert_pos, asyncio_import)
        
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
        elif isinstance(stmt, AssertStmt):
            self._generate_assert_stmt(stmt)
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
            # 管道操作/因果链作为独立语句
            if stmt.connector == 'comma' and len(stmt.stages) == 2:
                # 因果链语法：条件,动作 → if 条件: 动作
                cond_code = self._generate_expr(stmt.stages[0])
                action_code = self._generate_expr(stmt.stages[1])
                self._add_line(f"if {cond_code}:")
                self.indent_level += 1
                self._add_line(action_code)
                self.indent_level -= 1
            else:
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
            # 绑定形式⑤：普通赋值。target 为简单名字时才算局部绑定；
            # `甲[丁] = …`、`己.X = …` 由各自的分支处理，_bind_local 会跳过带点的名字。
            self._bind_local(stmt.target)
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
            # 绑定形式⑤：解包目标全部登记为局部变量。
            self._bind_local(*stmt.variables)
            vars_str = ', '.join(self._sanitize_name(v) for v in stmt.variables)
            value = self._generate_expr(stmt.value)
            self._add_line(f"{vars_str} = {value}")
        elif isinstance(stmt, WithStmt):
            # 上下文管理器
            self._generate_with_stmt(stmt)
        elif isinstance(stmt, DecoratorDefinition):
            # 装饰器定义
            self._generate_decorator_definition(stmt)
        elif isinstance(stmt, DecoratedFunction):
            # 装饰器链（多个装饰器 + 函数）
            self._generate_decorated_function(stmt)
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
        elif isinstance(stmt, YieldStmt):
            # 生成语句 → yield expression
            if stmt.value:
                value = self._generate_expr(stmt.value)
                self._add_line(f"yield {value}")
            else:
                self._add_line("yield")
        elif isinstance(stmt, AsyncScope):
            # 异步作用域（结构化并发）
            self._generate_async_scope(stmt)
        elif type(stmt).__name__ == 'CForStmt':
            # C风格for循环
            self._generate_c_for_stmt(stmt)
        elif type(stmt).__name__ == 'Block':
            # 花括号代码块
            for s in stmt.statements:
                self._generate_statement(s)
        elif isinstance(stmt, ExpressionStatement):
            # 表达式语句包装（如 "打印 xxx。" 解析为 ExpressionStatement）
            expr_str = self._generate_expr(stmt.expression)
            self._add_line(expr_str)
        elif isinstance(stmt, (IndexAccess, MemberAccess, ParagraphCall)):
            # 表达式语句（如 obj[key].append(v) 或 obj.method()）
            expr_str = self._generate_expr(stmt)
            self._add_line(expr_str)
        elif isinstance(stmt, EmbedBlock):
            self._generate_embed_block(stmt)
        elif isinstance(stmt, StringLiteral):
            # 裸字符串语句（docstring）生成：配合 lexer/parser 的三引号 docstring 修复
            # （lexer.py _tokenize_string、parser_stmt.py _parse_statement），
            # 这里输出 Python 字符串表达式语句——
            # Python 会把函数/类/模块体首行的字符串视为 docstring，
            # 其余位置的裸字符串为无操作表达式（与 Python 语义一致）。
            # 修复前该节点没有语句级分支，会抛 CodeGenError「未知语句类型」。
            self._add_line(self._generate_expr(stmt))
        else:
            raise CodeGenError(f"未知语句类型", type(stmt).__name__)
    
    def _generate_var_decl(self, stmt: VarDecl):
        """生成变量声明"""
        name = self._sanitize_name(stmt.name)
        value = self._generate_expr(stmt.value)
        
        # 绑定形式①：`设 X 为 …`。必须在 value 生成之后登记，否则
        # `设 映射 为 映射(f, 列)`（用内置结果初始化同名变量）的右侧会被自己遮蔽。
        # 类属性赋值（己.X / 类属性名）不是局部变量，不登记。
        if not (self._in_class_method and stmt.name in self._class_attr_names):
            self._bind_local(stmt.name)
        
        # 处理 己.xxx / 自.xxx 形式的属性赋值（两个 self 引用名一视同仁，
        # 见 _SELF_NAMES；只补 己 会让 `自.x 为 …` 发射出裸 `自.x` → NameError）
        name = self._map_self_prefix(name)

        
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
        """将光明类型名映射为Python类型名（支持泛型尖括号/方括号）"""
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
        stripped = (light_type or '').strip()
        # 泛型形式：列表<整数> / 字典<字符串, 小数> / 可选<整数> / 列表[整数]
        if stripped.endswith('>') or stripped.endswith(']'):
            open_char = '<' if stripped.endswith('>') else '['
            bracket = stripped.find(open_char)
            if bracket > 0:
                base = stripped[:bracket].strip()
                args_str = stripped[bracket + 1:-1].strip()
                if base in ('列表', '列', 'List'):
                    if args_str:
                        # 嵌套泛型递归映射：列表<列表<整数>> → list[list[int]]
                        first_arg = args_str.split(',')[0].strip()
                        return f"list[{self._map_type(first_arg)}]"
                    return 'list'
                if base in ('字典', '典', 'Map'):
                    return 'dict'
                if base in ('集合', '集', 'Set'):
                    return 'set'
                if base in ('元组', 'Tuple'):
                    return 'tuple'
                if base in ('可选', '可空', 'Optional'):
                    inner = self._map_type(args_str) if args_str else 'Any'
                    return f"Optional[{inner}]"
                # 未知泛型基名：退化为基名本身
                return type_map.get(base, base)
        return type_map.get(stripped, stripped)
    
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
        
        # 绑定形式③：循环变量。在 iterable 生成之后登记（可迭代对象里若真的调了
        # 同名内置，不该被循环变量遮蔽）。循环变量在 Python 里循环结束后仍然在作用
        # 域内，所以不做出循环即失效的处理。
        self._bind_local(stmt.variable)
        
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
        raw_param_names = []  # 绑定形式②用：参数的「源码原名」（未 sanitize）
        body_without_params = []
        for s in (stmt.body or []):
            if isinstance(s, Parameter):
                params.append({'name': self._sanitize_name(s.name), 'type': s.type_annotation})
                raw_param_names.append(s.name)
            elif isinstance(s, ParameterList):
                for param_name in s.params:
                    params.append({'name': self._sanitize_name(param_name), 'type': None})
                    raw_param_names.append(param_name)
            else:
                body_without_params.append(s)
        
        # 如果段落头有参数定义，也加入
        for param in (stmt.params or []):
            param_name = self._sanitize_name(param['name'])
            param_type = param.get('type')
            raw_param_names.append(param['name'])
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
        # 进入段落作用域：继承外层可见的局部名，再登记本段落的参数
        # （绑定形式②：段落参数）。段落体里 `设 …` 新增的绑定在退出时丢弃，
        # 不会泄漏到模块级、也不会污染兄弟段落。
        saved_locals = self._push_local_scope()
        self._bind_local(*raw_param_names)
        self._in_function = True
        self.indent_level += 1
        if body_without_params:
            for s in body_without_params:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1
        self._in_function = old_in_function
        self._pop_local_scope(saved_locals)
        
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
    
    def _generate_catch_clause(self, catch_type, catch_var, catch_body):
        """生成单个except块"""
        # 绑定形式⑥：异常绑定 `捕获 X 为 变量`。变量在 except 体内是局部名，
        # 必须遮蔽同名内置（否则 `捕获 值错误 为 映射` 后引用 映射 会变成 map()）。
        self._bind_local(catch_var)
        if catch_type == '外部错误':
            # FFI 外部错误处理
            if catch_var:
                self._add_line(f"except (ctypes.ArgumentError, OSError, RuntimeError) as {self._sanitize_name(catch_var)}:")
            else:
                self._add_line("except (ctypes.ArgumentError, OSError, RuntimeError):")
        elif catch_type and catch_var:
            # 捕获指定类型 + 变量：except 值错误 as 错误:
            # 支持多类型捕获：(Type1, Type2) 格式
            ct = self._resolve_exception_type(catch_type)
            if ',' in ct:
                ct = f"({ct})"
            self._add_line(f"except {ct} as {self._sanitize_name(catch_var)}:")
        elif catch_type:
            # 捕获指定类型无变量：except 值错误:
            ct = self._resolve_exception_type(catch_type)
            if ',' in ct:
                ct = f"({ct})"
            self._add_line(f"except {ct}:")
        elif catch_var:
            # 无类型有变量（向后兼容）：except Exception as 错误:
            self._add_line(f"except Exception as {self._sanitize_name(catch_var)}:")
        else:
            # 无类型无变量：except Exception:
            self._add_line("except Exception:")
        
        self.indent_level += 1
        if catch_body:
            for s in catch_body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1

    def _resolve_exception_type(self, type_name: str) -> str:
        """将光明异常类型名解析为Python异常类型名"""
        # 检查是否在异常名映射中
        if type_name in self.exception_name_map:
            return self.exception_name_map[type_name]
        # 检查是否已经是Python内置异常名
        import builtins
        if hasattr(builtins, type_name):
            return type_name
        return type_name

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
        
        # 优先使用 catch_clauses 列表（支持多捕获块）
        if stmt.catch_clauses:
            for clause in stmt.catch_clauses:
                if isinstance(clause, CatchClause):
                    self._generate_catch_clause(clause.catch_type, clause.catch_var, clause.catch_body)
                elif isinstance(clause, tuple) and len(clause) == 3:
                    ct, cv, cb = clause
                    self._generate_catch_clause(ct, cv, cb)
        elif stmt.catch_body:
            # 向后兼容：使用旧的单捕获块字段
            self._generate_catch_clause(stmt.catch_type, stmt.catch_var, stmt.catch_body)
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
        
        # else块（try块没有异常时执行）
        if stmt.else_body:
            self._add_line("else:")
            self.indent_level += 1
            for s in stmt.else_body:
                self._generate_statement(s)
            self.indent_level -= 1
    
    def _generate_throw_stmt(self, stmt: ThrowStmt):
        """生成抛出异常语句"""
        if stmt.value is None:
            # 裸抛出：重新抛出当前异常
            self._add_line("raise")
            return
        # 检查是否抛出已知中文异常名（如 迭代停止 → StopIteration）
        if isinstance(stmt.value, Identifier) and stmt.value.name in self.exception_name_map:
            py_exc_name = self.exception_name_map[stmt.value.name]
            from_part = ""
            if stmt.from_expr:
                from_val = self._generate_expr(stmt.from_expr)
                from_part = f" from {from_val}"
            self._add_line(f"raise {py_exc_name}(){from_part}")
            return
        # 检查是否抛出带参数的中文异常名（如 运行时错误("消息")）
        if isinstance(stmt.value, ParagraphCall) and stmt.value.name in self.exception_name_map:
            py_exc_name = self.exception_name_map[stmt.value.name]
            args = []
            for arg in stmt.value.args:
                args.append(self._generate_expr(arg))
            args_str = ', '.join(args)
            from_part = ""
            if stmt.from_expr:
                from_val = self._generate_expr(stmt.from_expr)
                from_part = f" from {from_val}"
            self._add_line(f"raise {py_exc_name}({args_str}){from_part}")
            return
        value = self._generate_expr(stmt.value)
        # 确保抛出的是合法异常对象（Python 3 不允许 raise 字符串）
        from_part = ""
        if stmt.from_expr:
            from_val = self._generate_expr(stmt.from_expr)
            from_part = f" from {from_val}"
        self._add_line(f"_light_exc = {value}")
        self._add_line(f"raise _light_exc if isinstance(_light_exc, BaseException) else Exception(_light_exc){from_part}")
    
    def _generate_assert_stmt(self, stmt: AssertStmt):
        """生成断言语句
        
        语法：断言 <条件>，<可选消息>。
        生成：assert <条件>, <消息>
        """
        cond = self._generate_expr(stmt.condition)
        if stmt.message:
            msg = self._generate_expr(stmt.message)
            self._add_line(f"assert {cond}, {msg}")
        else:
            self._add_line(f"assert {cond}")
    
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
                is_ctor = getattr(method, 'is_constructor', False) or method_name in self._CTOR_NAMES
                if is_ctor or method_name == '__init__':
                    has_constructor = True
                    ctor_method = method
                    break

        # 生成类级字段（类体内的 `设 名[: 类型] [= 值]`，见
        # src/parser_stmt.py:3526-3558 —— 它给 AttributeDeclaration 带上了
        # type_annotation，is_static=True）。
        #
        # 三形态必须分开发射，混一起就是单 B 那两处缺陷：
        #   ① `设 总数: 数 = 0`  -> `总数: float = 0`
        #      注解**不能丢**。丢了以后类型检查/IDE/文档全瞎，且与模块级
        #      `设 总数: 数 = 0`（走 _generate_var_decl:1120-1123，一直正确发
        #      `总数: float = 0`）行为分叉——同一条语法两个产物。
        #   ② `设 姓名: 串`（无初值）-> `姓名: str`（**纯注解**）
        #      规范依据 docs/L2_文言体语法规范_v4.0.md:599-600 / :622-623。
        #      绝不能补 `= None`：那会真的创建一个类属性，语义从「声明字段类型」
        #      变成「所有实例共享一个默认值」。对可变类型是经典坑（一个实例
        #      改了字典，全类都变），对 examples/L2_wenyan/学生模块.light:24
        #      的 `设 成绩: 典` + 构造里 `自之成绩 = {}` 则是「类属性 None +
        #      实例属性 dict」两套并存的语义混乱。纯注解不产生类属性，实例
        #      属性行为完全由 __init__ 决定，问题自然消失。
        #   ③ 既无注解又无初值 -> 保持 `名 = None`
        #      没有注解可发，又不能什么都不发（字段声明会整个消失），
        #      沿用旧行为不动，避免无谓回归。
        #
        # 类型映射走 _map_type（不是 _sanitize_type_name）：与 VarDecl 同一条
        # 通路，泛型 `列表<整数>` / `可选<整数>` 才能一致地映成 list[int] /
        # Optional[int]。两处用不同映射表迟早再分叉一次。
        for attr in static_attrs:
            attr_name = self._sanitize_name(attr.name)
            light_type = getattr(attr, 'type_annotation', None)
            annotation = f": {self._map_type(light_type)}" if light_type else ''
            if attr.default_value:
                default = self._generate_expr(attr.default_value)
                self._add_line(f"{attr_name}{annotation} = {default}")
            elif annotation:
                self._add_line(f"{attr_name}{annotation}")
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
                is_ctor = getattr(method, 'is_constructor', False) or method_name in self._CTOR_NAMES
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
        """生成协议方法。

        无方法体 → 抽象方法（@abstractmethod + pass）；
        有方法体 → 默认实现（普通方法，实现类可直接继承或覆写）。
        """
        method_name = self._sanitize_name(method.name)

        # 参数列表
        # 与 _generate_method 同一口径：self 已在上一行无条件注入，源码里**显式
        # 写出**的 自/己 形参必须吃掉。接口签名恰恰是最常写 `自` 的地方——
        # docs/L2_文言体语法规范_v4.0.md:590-591 的示范签名就是 `段 打印(自) -> 空`，
        # 不过滤会发射 `def 打印(self, 自)`：实现类按零参调用即 TypeError，
        # 按一参调用又和 `己/自 → self` 的方法体写法对不上。
        params = ['self']
        for param in method.parameters:
            if self._is_self_param(param.name):
                continue
            params.append(self._sanitize_name(param.name))
        params_str = ', '.join(params)

        has_body = bool(getattr(method, 'body', None))
        if not has_body:
            self._needs_abc = True
            self._add_line("@abstractmethod")

        if method.return_type:
            # 必须走 _map_type 做光明→Python 类型映射，
            # 直接用 _sanitize_name 会把「整数」原样写进注解导致 NameError。
            ret_type = self._map_type(method.return_type)
            self._add_line(f"def {method_name}({params_str}) -> {ret_type}:")
        else:
            self._add_line(f"def {method_name}({params_str}):")

        self.indent_level += 1
        if has_body:
            emitted = len(self.output_lines)
            # 必须置位 _in_function，否则方法体里的「返回」会被当成模块级语句
            # 降级成 print(...)，默认实现将永远返回 None。
            prev_in_function = self._in_function
            self._in_function = True
            try:
                for stmt in method.body:
                    self._generate_statement(stmt)
            finally:
                self._in_function = prev_in_function
            # 方法体可能全是注释等不产出代码的节点，兜底补 pass
            if len(self.output_lines) == emitted:
                self._add_line("pass")
        else:
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
    
    _TYPE_NAME_MAP = {
        '整数': 'int', '整数型': 'int', '整型': 'int',
        '小数': 'float', '浮数': 'float', '浮点数': 'float', '浮点': 'float',
        '文本': 'str', '串': 'str', '字符串': 'str',
        '列表': 'list', '列': 'list', '数组': 'list',
        '字典': 'dict', '典': 'dict', '词典': 'dict', '映射': 'dict',
        '集合': 'set', '集': 'set',
        '布尔': 'bool', '布尔值': 'bool',
        '空': 'None', '空值': 'None',
        '任意': 'object', '任意类型': 'object',
    }

    def _sanitize_type_name(self, name: str) -> str:
        """将光明类型名转换为Python类型名"""
        return self._TYPE_NAME_MAP.get(name, self._sanitize_name(name))

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
            type_name = self._sanitize_type_name(pattern.type_name)
            binding = self._sanitize_name(pattern.binding)
            return f"{type_name}() as {binding}"
        return '_'

    def _generate_with_stmt(self, stmt: WithStmt):
        """生成上下文管理语句"""
        prefix = "async " if getattr(stmt, 'is_async', False) else ""
        
        # 检查是否有多个上下文管理器
        items = getattr(stmt, 'items', None)
        if items and len(items) > 1:
            # 多个上下文管理器
            parts = []
            for expr, var in items:
                expr_str = self._generate_expr(expr)
                # 文件操作替换
                expr_str = expr_str.replace('_light_builtin.读取文件', 'open').replace('读取文件', 'open')
                expr_str = expr_str.replace('_light_builtin.写入文件', 'open').replace('写入文件', 'open')
                if var:
                    var_name = self._sanitize_name(var)
                    # 绑定形式④：`使用 … 为 变量`（多上下文管理器形式）
                    self._bind_local(var)
                    parts.append(f"{expr_str} as {var_name}")
                else:
                    parts.append(expr_str)
            context_str = ', '.join(parts)
            self._add_line(f"{prefix}with {context_str}:")
        else:
            context_expr = self._generate_expr(stmt.context_expr)
            # 在 with 语句中，读取文件(...) 应替换为 open(...)
            context_expr = context_expr.replace('_light_builtin.读取文件', 'open').replace('读取文件', 'open')
            # 写入文件(...) 也应替换为 open(..., 'w')
            context_expr = context_expr.replace('_light_builtin.写入文件', 'open').replace('写入文件', 'open')
            if stmt.variable:
                var_name = self._sanitize_name(stmt.variable)
                # 绑定形式④：`使用 … 为 变量`（单上下文管理器形式）
                self._bind_local(stmt.variable)
                self._add_line(f"{prefix}with {context_expr} as {var_name}:")
            else:
                self._add_line(f"{prefix}with {context_expr}:")
        self.indent_level += 1
        if stmt.body:
            for s in stmt.body:
                self._generate_statement(s)
        else:
            self._add_line("pass")
        self.indent_level -= 1

    def _generate_async_scope(self, stmt: AsyncScope):
        """生成异步作用域（结构化并发，使用 asyncio.gather 实现）"""
        if not stmt.tasks:
            self._add_line("pass")
            return
        
        # 生成任务表达式
        task_exprs = []
        for task in stmt.tasks:
            expr = self._generate_expr(task)
            task_exprs.append(expr)
        
        task_str = ', '.join(task_exprs)
        
        # 需要导入 asyncio
        self._needs_asyncio = True
        
        if stmt.result_vars:
            # 绑定形式⑤：异步作用域的结果变量也是解包目标
            self._bind_local(*stmt.result_vars)
            vars_str = ', '.join(self._sanitize_name(v) for v in stmt.result_vars)
            self._add_line(f"{vars_str} = await asyncio.gather({task_str})")
        else:
            self._add_line(f"await asyncio.gather({task_str})")

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
            # 使用 getattr 兼容旧 AST（ast_nodes.DecoratorDefinition 无 args 字段）
            sanitized = self._sanitize_name(decorator_name)
            decorator_args = getattr(stmt, 'args', None)
            if decorator_args:
                args_parts = []
                for a in decorator_args:
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

    def _generate_decorated_function(self, stmt: DecoratedFunction):
        """生成装饰器链（多个装饰器 + 函数定义）"""
        # 按顺序为每个装饰器生成 @ 行
        for decorator_info in stmt.decorators:
            decorator_name = decorator_info.name
            sanitized = self._sanitize_name(decorator_name)
            decorator_args = decorator_info.args
            if decorator_args:
                args_parts = []
                for a in decorator_args:
                    if isinstance(a, KeywordArg):
                        args_parts.append(f"{a.name}={self._generate_expr(a.value)}")
                    else:
                        args_parts.append(self._generate_expr(a))
                args_str = ', '.join(args_parts)
                self._add_line(f"@{sanitized}({args_str})")
            else:
                self._add_line(f"@{sanitized}")
        
        # 生成被装饰的函数
        if isinstance(stmt.function, Paragraph):
            self._generate_paragraph(stmt.function)
        else:
            raise CodeGenError("装饰器链后必须是段落定义", type(stmt.function).__name__)

    def _generate_method(self, method, class_attributes=None):
        """生成方法定义"""
        method_name = method.name

        # 构造函数特殊处理
        is_ctor = getattr(method, 'is_constructor', False) or method_name in self._CTOR_NAMES
        if is_ctor:
            method_name = '__init__'


        # 迭代器协议方法名映射
        if method_name == '__迭代__':
            method_name = '__iter__'
        elif method_name == '__下一项__':
            method_name = '__next__'
        # 上下文管理器协议方法名映射
        elif method_name == '__进入__':
            method_name = '__enter__'
        elif method_name == '__退出__':
            method_name = '__exit__'

        # 方法定义名翻译：与调用侧 method_name_map 对齐（见 _method_def_name_map）
        # 必须在协议名/构造名映射之后、私有前缀之前执行。映射表中不含魔术方法
        # 名，故 __init__/__iter__ 等会原样返回，无需额外判断。
        method_name = self._method_def_name_map.get(method_name, method_name)

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
        # 是否已注入 self —— 只有注入过才吞掉源码里显式写出的 自/己 形参。
        # 静态方法 params 是空的（上方 `[] if is_static`），此时若也吞掉就会
        # 静默少一个形参 → 调用侧 TypeError，比多一个名字更难查。
        swallow_self = 'self' in params
        # 兼容 MethodDefinition(.parameters) 和 Paragraph(.params)
        method_params = getattr(method, 'parameters', None)
        if method_params is None:
            method_params = getattr(method, 'params', None)
        if method_params:
            for param in method_params:
                # Paragraph 的 params 是 List[Dict[str,str]]，MethodDefinition 的是 List[Parameter]
                if isinstance(param, dict):
                    raw_param = param.get('name', '')
                    # 显式写出的 自/己 形参：方法定义已无条件注入 self（上方
                    # params=['self']），这里必须吃掉，否则发射
                    # `def __init__(self, self, ...)` → SyntaxError。
                    # 同时把原名登记进 _current_method_params，让方法体里的
                    # 自/己 走 _resolve_identifier_name 归一成 self。
                    if swallow_self and self._is_self_param(raw_param):
                        self._current_method_params.add(raw_param)
                        continue
                    param_name = self._sanitize_name(raw_param)
                    self._current_method_params.add(raw_param)
                    if param.get('default'):
                        params.append(f"{param_name}={param['default']}")
                    else:
                        params.append(param_name)
                else:
                    if swallow_self and self._is_self_param(param.name):
                        self._current_method_params.add(param.name)
                        continue
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
        # 进入类方法作用域（绑定形式②：方法参数）。_current_method_params 收的是
        # 「排除 self. 前缀」用的同一批原名，直接复用，避免两处各扫一遍参数表。
        saved_locals = self._push_local_scope()
        self._bind_local(*self._current_method_params)
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
        # 离开类方法作用域：方法内的局部绑定不泄漏到类体/模块级
        self._pop_local_scope(saved_locals)
    
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
            # 中文数字整体匹配优先（在任何名字改写之前，避免被后缀规则误切）
            if expr.name in self.chinese_numbers:
                return str(self.chinese_numbers[expr.name])

            # 复合标识符的成员后缀改写。
            # lexer 对纯汉字序列**不切** `的`（设计，见 docs/L1_白话体语法规范_v4.0.md:589），
            # 所以 `成绩的项` 到这里是单个 IDENTIFIER，只能在 codegen 做后缀重写。
            # 白名单（长度/键/值）见 docs/L1_白话体语法规范_v4.0.md:591 与
            # docs/guide/常见问题.md:232；`的项` → .items() 的二元组语义见
            # docs/知识库/最佳实践.md:90（项[0]/项[1]）与 docs/L2_..._v4.0.md:372（`配置.项()`）。
            #
            # 改写必须在 `己 → self` 解析**之后**才算完：对象部分要走同一条
            # 名字解析路径，否则类方法里的 `己之成绩的项` 会漏出裸 `己`。
            # 所以这里把「拆后缀」与「解析对象名」分成两步，两者共用
            # _resolve_identifier_name()，不再各写一份 self 前缀逻辑。
            split = self._split_member_suffix(expr.name)
            if split is not None:
                obj_raw, tmpl = split
                return tmpl.format(o=self._resolve_identifier_name(obj_raw))

            return self._resolve_identifier_name(expr.name)

        
        # 检查 ast_nodes 模块中的 Identifier（兼容两种定义）
        elif hasattr(expr, 'name') and hasattr(expr, 'line'):
            # 可能是来自 ast_nodes 的 Identifier
            name_val = expr.name
            if isinstance(name_val, str):
                return self._sanitize_name(name_val)
            elif hasattr(name_val, 'name'):
                # SegmentName 嵌套：name 字段本身可能是 SegmentName 对象
                # 尝试递归提取字符串
                inner = name_val
                while hasattr(inner, 'name') and not isinstance(inner.name, str):
                    inner = inner.name
                if hasattr(inner, 'name'):
                    return self._sanitize_name(inner.name)
                return self._sanitize_name(str(inner))
            return self._sanitize_name(str(name_val))
        
        elif isinstance(expr, SegmentName):
            # SegmentName 段落名
            name_val = expr.name
            if isinstance(name_val, str):
                return self._sanitize_name(name_val)
            # 递归提取
            while hasattr(name_val, 'name') and not isinstance(name_val.name, str):
                name_val = name_val.name
            if hasattr(name_val, 'name'):
                return self._sanitize_name(name_val.name)
            return self._sanitize_name(str(name_val))
        
        elif isinstance(expr, BinaryOp):
            left = self._generate_expr(expr.left)
            right = self._generate_expr(expr.right)
            # v7 单 08：`包含` 的内部占位符（产生点 src/parser_core.py:270）。
            # 下面那行 operator_map.get(op, op) 的兜底语义是「查不到就原样透传」，
            # 于是 `@@contains@@` 直接漏进产物：
            #   如果 文件名 包含 关键词  ->  if (文件名 @@contains@@ 关键词):
            # SyntaxError。unified 后端 code_generator_unified.py:1247-1248 有这段
            # 处理，本文件漏了——占位符协议只在一个后端落实。
            #
            # 注意方向：`包含` 是唯一一个**操作数需要交换**的比较运算符。
            # `A 包含 B` 语义是「A 含有 B」-> Python `B in A`。
            # 绝不能只往 operator_map 加一条 '@@contains@@': 'in'，那会发射
            # `A in B`，语法过得去而语义反了，把响亮的 SyntaxError 换成 rc=0
            # 无输出的静默错答案，比现状更坏。三处佐证同向：parser_core.py:270
            # 注释、code_generator_unified.py:1248、以及本文件成员形式 :2382。
            #
            # 括号必须留：`in` 是比较运算符，裸发射会与外层比较串成链式比较
            # （`x in y == False` -> `(x in y) and (y == False)`，恒假），
            # 与成员形式 :2378-2381 踩过的是同一个坑。
            if expr.operator == '@@contains@@':
                return f"({right} in {left})"
            op = self.operator_map.get(expr.operator, expr.operator)
            return f"({left} {op} {right})"

        
        elif isinstance(expr, UnaryOp):
            operand = self._generate_expr(expr.operand)
            op = self.operator_map.get(expr.operator, expr.operator)
            # 符号运算符不留空格：(-5) 而非 (- 5)
            # 关键字运算符（not, ~等）需要留空格：(not x) 而非 (notx)
            if op in ('not', '~', 'not '):
                return f"({op} {operand})"
            return f"({op}{operand})"
        
        elif isinstance(expr, ParagraphCall):
            name = self._sanitize_name(expr.name)
            
            # 己.方法() / 自.方法() → self.方法()（粘连写法 己方法() 被 parser
            # 折叠成 '己.方法'）。两个 self 引用名共用 _map_self_prefix，与本文件
            # Identifier 分支 / VarDecl 分支的映射保持同一口径。
            if self._in_class_method and isinstance(expr.name, str):
                name = self._map_self_prefix(expr.name)

            
            # 单 03·路径1：局部变量遮蔽内置名。
            # parser 对「内置/动词名」做了特判——即便是裸引用（如 `映射['a']` 里的
            # `映射`）也会解析成零参 ParagraphCall。若该名字已被绑定为局部变量，它
            # 就不再是内置函数，绝不能翻译成 map()/input()：
            #   - 零参（裸引用）：发射变量名本身，让外层 IndexAccess 等拿到 `映射`
            #     而非 `map()`；
            #   - 带参（把局部变量当可调用对象调用）：发射 `变量名(args)`。
            shadowed = self._shadows_builtin(expr.name)
            
            # 检查是否是内置函数（但不覆盖用户自定义的函数 / 已被局部变量遮蔽的名字）
            if (not shadowed) and expr.name in self.builtin_map and expr.name not in self._user_defined_functions:
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
                    kw = self._kwarg_name(py_name, arg.name)
                    args.append(f"{kw}={self._generate_expr(arg.value)}")
                else:
                    args.append(self._generate_expr(arg))
            args_str = ', '.join(args)
            
            # 被局部变量遮蔽且为裸引用（零参）：发射裸变量名，不加调用括号
            if shadowed and not expr.args:
                return py_name
            
            # 如果函数名是lambda表达式，需要加括号包裹，避免lambda body被误认为函数调用参数
            # 例如：随机(0, 10) → (lambda *a: __import__("random").random())(0, 10)
            if py_name.startswith('lambda '):
                return f"({py_name})({args_str})"
            
            return f"{py_name}({args_str})"
        
        elif isinstance(expr, FunctionCallExpr):
            # 链式函数调用：expr()  → callee(args)
            callee = self._generate_expr(expr.callee)
            args = []
            for arg in expr.args:
                if isinstance(arg, KeywordArg):
                    args.append(f"{arg.name}={self._generate_expr(arg.value)}")
                else:
                    args.append(self._generate_expr(arg))
            args_str = ', '.join(args)
            return f"{callee}({args_str})"
        
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
                # `的X` 后缀被 lexer 从成员名尾部切出、又被无括号成员调用解析
                # 吞成"唯一实参"的修复（见 _match_orphan_suffix_call 的详述）。
                # 必须在生成实参、走方法调用逻辑**之前**拦截，否则会发射
                # `self.成绩(的项)` 这种能编译、运行期才炸的静默错译。
                orphan = self._match_orphan_suffix_call(expr)
                if orphan is not None:
                    return orphan

                # 方法调用（支持关键字参数）
                args = []
                for arg in expr.args:
                    if isinstance(arg, KeywordArg):
                        args.append(f"{arg.name}={self._generate_expr(arg.value)}")
                    else:
                        args.append(self._generate_expr(arg))
                args_str = ', '.join(args)

                # 特殊处理：父.构造(...) -> super().__init__(...)
                if obj == "super()" and expr.member in self._CTOR_NAMES:
                    return f"super().__init__({args_str})"
                # 成员调用侧的构造名映射：`人之构造(...)` -> `人.__init__(...)`。
                # 与方法**定义**侧共用同一张 _CTOR_NAMES（见 _generate_method:
                # is_ctor 判定），避免定义把 构造 译成 __init__ 而调用仍发 .构造
                # 导致运行期 AttributeError（examples/L2_wenyan/学生模块.light:27）。
                # 只作用于成员调用；名字恰好叫「构造」的普通函数是 ParagraphCall，
                # 不经过本分支，不受影响。
                if expr.member in self._CTOR_NAMES:
                    return f"{obj}.__init__({args_str})"
                # 特殊处理：长度方法 -> len(obj)
                if expr.member == '长度':
                    return f"len({obj})"

                # 特殊处理：包含方法 -> item in obj
                # 必须加括号：`in` 在 Python 里是比较运算符，会与外层比较串成链式比较。
                # 例如 `文本.包含("z") 等于 假` 若发射成 `"z" in 文本 == False`，
                # Python 解释为 `("z" in 文本) and (文本 == False)`，恒为假 —— 
                # 分支永不进入、程序静默无输出（rc=0），坏块因此逃过护栏。
                elif expr.member == '包含':
                    return f"({args_str} in {obj})"
                # 特殊处理：连接 -> 运行期分派（见 _light_join）。只接管「带 1 个实参」
                # 的调用，`连接对象.连接()` 这类用户自定义无参方法保持原样透传。
                elif expr.member == '连接' and len(expr.args) == 1:
                    return f"_light_join({obj}, {args_str})"

                # 特殊处理：cb_前缀的回调函数调用
                # obj.cb_xxx(args) → cb_xxx(args)
                # 回调参数在光明语言中通过 obj.回调名(args) 语法调用
                if expr.member.startswith('cb_'):
                    return f"{mapped_member}({args_str})"

                # P5 核心改造：内置函数式优先 —— 单 03 已收窄，见下方边界说明。
                #
                # 原实现：只要 member 在 builtin_map 且不在 method_name_map，就把
                # `obj.成员(args)` 改写成 `内置(obj, args)`。这条改写是**静默错译的
                # 源头**：`计数.读取()` → `input(计数)`（跑到 stdin 上去了）、
                # `f.读取()` → `input(f)`（把文件对象当提示串）。用户写 `obj.成员`
                # 时表达的是「向这个对象要一个方法」，不是「把这个对象喂给内置函数」。
                #
                # 收窄后的边界：**只有 obj 本身就是内置命名空间时才做函数式改写**。
                # 目前唯一的内置命名空间是 `_light_builtin`（见 test_turing.light 的
                # `_light_builtin.字典设置(...)`：方法名已在命名空间上，直接调用即可，
                # 且不能把命名空间自己注入成第一个实参）。其余一切 `obj.成员(...)`
                # 统一按方法调用发射。
                #
                # 为什么这不会伤到「正常映射」——它们根本走不到这里：
                #   · 追加→append、插入→insert、弹出→pop、排序→sort、反转→reverse、
                #     替换→replace、分割→split… 都在 method_name_map 里，被本行的
                #     `expr.member not in self.method_name_map` 条件挡在外面，走
                #     下面的 `obj.{mapped_member}(...)`；
                #   · 长度→len(obj) 在 :2223 单独特判并直接 return；
                #   · 包含→(x in obj) 在 :2230 单独特判并直接 return；
                #   · 连接→_light_join 在 :2234 单独特判并直接 return；
                #   · 函数式的 长度([1,2])/范围(0,3) 是 ParagraphCall，不经过
                #     MemberAccess 分支，内置映射照旧生效。
                builtin_target = self.builtin_map.get(expr.member)
                if (builtin_target and expr.member not in self.method_name_map
                        and obj == '_light_builtin'):
                    # obj 已是内置命名空间：方法名可直接调用，不能再把
                    # _light_builtin 注入为第一个参数（会多出一个实参，TypeError）。
                    return f"{builtin_target}({args_str})"

                return f"{obj}.{mapped_member}({args_str})"
            else:
                # 属性访问
                # 特殊处理：长度属性 -> len(obj)（即使不是方法调用）
                if expr.member == '长度':
                    return f"len({obj})"
                # 复合成员名的后缀改写：`X.成绩的项` -> `X.成绩.items()`。
                # 与 Identifier 分支共用 _split_member_suffix，两处不各写一份表。
                # 只在属性访问侧做：`的项/的键/的值/的长度` 结尾的名字不会是方法名。
                split = self._split_member_suffix(expr.member)
                if split is not None:
                    inner_raw, tmpl = split
                    return tmpl.format(o=f"{obj}.{self._sanitize_name(inner_raw)}")
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
            expr_parts = []  # 表达式部分（花括号内代码），用于选择外层引号
            for part in expr.parts:
                if isinstance(part, str):
                    # 转义特殊字符（反斜杠、换行、回车、制表符）
                    escaped = part.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                    parts.append(escaped)
                elif isinstance(part, tuple):
                    # 带格式说明符的表达式：(expr_node, format_spec)
                    expr_code = self._generate_expr(part[0])
                    parts.append('{' + expr_code + ':' + part[1] + '}')
                    expr_parts.append(expr_code)
                elif isinstance(part, ASTNode):
                    # 生成表达式代码并放入花括号
                    expr_code = self._generate_expr(part)
                    parts.append('{' + expr_code + '}')
                    expr_parts.append(expr_code)

            # 选择外层引号并只在【字面量部分】转义，避免破坏花括号内表达式。
            #
            # Bug 根因：原实现先拼接整个 f-string，再用 fstr.replace('"', '\\"')
            # 全局转义双引号。若花括号内表达式含字符串（如 {处理数据("hello")}），
            # 表达式里的 " 会被转成 \" —— 在 f-string 花括号内属于无效语法
            # （"unexpected character after line continuation character"）。
            #
            # 修复方案：
            # 1) 表达式部分由 _generate_expr 生成（字符串统一用双引号），
            #    因此只要表达式含 "，外层引号就必须选单引号 '（花括号内出现 " 合法）；
            # 2) 外层引号只出现在字面量部分，若字面量含同种引号则仅在该处转义
            #    （花括号外的 \' 或 \" 是合法转义）。
            if any('"' in p for p in expr_parts):
                outer = "'"
            elif any("'" in p for p in parts if isinstance(p, str)):
                outer = '"'
            else:
                outer = '"'
            # 仅转义字面量部分中的外层引号
            out = []
            for p in parts:
                if isinstance(p, str) and outer in p:
                    out.append(p.replace(outer, '\\' + outer))
                else:
                    out.append(p)
            return f"f{outer}{''.join(out)}{outer}"
        
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
        
        # FFI 表达式节点
        elif isinstance(expr, FFIPointerType):
            return self._generate_ffi_pointer_type(expr)
        elif isinstance(expr, FFIArrayType):
            return self._generate_ffi_array_type(expr)
        elif isinstance(expr, FFIAddressOf):
            return self._generate_ffi_address_of(expr)
        elif isinstance(expr, FFIDereference):
            return self._generate_ffi_dereference(expr)
        elif isinstance(expr, FFIPointerOffset):
            return self._generate_ffi_pointer_offset(expr)
        elif isinstance(expr, FFIGetLastError):
            return self._generate_ffi_get_last_error(expr)
        elif isinstance(expr, FFIGetErrno):
            return self._generate_ffi_get_errno(expr)
        
        else:
            raise CodeGenError(f"不支持的表达式类型", type(expr).__name__)
    
    # ---- 构造方法名（定义侧 / 调用侧共用唯一判据）----------------------
    # 定义侧：_generate_method 的 is_ctor 判定
    # 调用侧：MemberAccess 方法调用分支
    # 两侧必须读同一个元组，否则「定义译成 __init__、调用仍发 .构造」会再次分叉
    # （examples/L2_wenyan/学生模块.light:27 就是这么炸的）。
    # `构` 是 L0 v4.0 单字写法（examples/L0_core/06_类_面向对象.light），与
    # `构造` 同义：定义侧 `构 接收 …` 已在 parser_stmt 归一成 __init__，调用侧
    # `父.构(…)` 也必须映射成 super().__init__(…)，否则发出 super().构(…) 运行期
    # AttributeError。三处（super 调用 / obj 调用 / 定义判定）共读本元组。
    _CTOR_NAMES = ('构造', '初始化', '构')

    # ---- self 引用名 -----------------------------------------------------
    # `己` 与 `自` 在 src/parser_expr.py:27 已同为 self 引用登记，codegen 必须
    # 一视同仁：表达式位置、方法形参位置、实参位置三处都要归一成 self，
    # 否则同一个方法里会出现「形参叫 自、方法体里叫 self」两套名字 → NameError。
    _SELF_NAMES = ('己', '自')

    def _is_self_param(self, param_name) -> bool:
        """形参名是否是 self 引用（己/自）。

        方法定义已经无条件注入了 self（见 _generate_method 的 params=['self']），
        所以源码里**显式写出**的 自/己 形参必须被吃掉，否则会发射
        `def __init__(self, self, ...)` —— SyntaxError（duplicate argument）。
        """
        return isinstance(param_name, str) and param_name in self._SELF_NAMES

    # ---- 复合标识符的成员后缀改写（`的X`）------------------------------

    #
    # lexer 对纯汉字序列不切 `的`（设计；docs/L1_白话体语法规范_v4.0.md:589），
    # 于是 `成绩的项` 抵达 codegen 时是**单个** IDENTIFIER。规范给的落地方式是
    # 「代码生成阶段按白名单把已知属性名拆出来」——白名单条文见
    # docs/L1_白话体语法规范_v4.0.md:591 与 docs/guide/常见问题.md:232
    # （列举 长度 / 首 / 尾 / 键 / 值）。
    #
    # 本表只收「有规范条文或实例依据」的四条：
    #   的长度 -> len(X)        原有行为，docs 明列，全仓 27 处在用
    #   的项   -> X.items()     docs/知识库/最佳实践.md:90 用 `的项` + 项[0]/项[1]（二元组）；
    #                           docs/L2_文言体语法规范_v4.0.md:372/482 的方法形式 `配置.项()`
    #                           搭配 `之为 键, 值`，同为 (k,v) 语义；
    #                           examples/L2_wenyan/学生模块.light:39 `自之成绩的项` + 项[1]
    #   的键   -> X.keys()      docs 白名单明列「键」
    #   的值   -> X.values()    docs 白名单明列「值」
    #
    # **不要**继续往这张表里加没有依据的词。全仓 37255 个 .light 扫描结果显示，
    # 内置函数的**中文具名实参名** → Python 形参名（v7 新单 B）
    #
    # 背景：`排序(学生列表, 依据 = 段(x) 返 -x之取平均分())`
    # （examples/L2_wenyan/主程序.light:58）里 `依据` 是中文写的形参名。
    # `排序` 经 builtin_map 映射成 `sorted` 之后，实参名若原样透传就发射
    # `sorted(xs, 依据=...)` → 运行期 `TypeError: sorted() got an unexpected
    # keyword argument '依据'`。语法过得去、跑起来才炸。
    #
    # 判据严格按「(Python 被调名, 中文实参名)」配对，不做单边的按名替换——
    # 否则任何用户函数只要形参恰好叫 `依据` 就会被改名，那是新的静默错译。
    # 表里只收有实例依据的条目；查不到就原样透传（保持改动前行为，且运行期
    # 会立刻抛 TypeError，不会静默跑出错结果）。
    _BUILTIN_KWARG_NAME_MAP = {
        ('sorted', '依据'): 'key',
        # 逆序 / 倒序 都收：单测 test_multiple_keyword_args 写的是 `倒序`，
        # 漏收就会静默发射 `sorted(xs, 倒序=True)` → 运行期 TypeError。
        ('sorted', '逆序'): 'reverse',
        ('sorted', '倒序'): 'reverse',
    }

    def _kwarg_name(self, py_callee: str, raw_name: str) -> str:
        """把中文具名实参名翻译成内置函数的 Python 形参名；查不到则原样返回。"""
        return self._BUILTIN_KWARG_NAME_MAP.get((py_callee, raw_name), raw_name)

    # 高频 `的X` 后缀绝大多数是**用户自己的标识符**而非成员访问：
    #   的量 17（物质的量）、的额 16（标的额）、的幂 8（数学十的幂）、
    #   的大小 6（集合差集的大小）、的第几天 6（年中的第几天）、的物变化 6（标的物变化）、
    #   的个数 3（比当前小的个数）……
    # 把它们纳入改写会把正常变量/函数名直接编坏。
    _MEMBER_SUFFIX_MAP = (
        ('的长度', 'len({o})'),
        ('的项', '{o}.items()'),
        ('的键', '{o}.keys()'),
        ('的值', '{o}.values()'),
    )

    def _is_known_binding(self, name: str) -> bool:
        """名字是否已经是一个「用户自己声明过的名字」。

        用于 `的X` 后缀改写的否决判据：如果整个 `X的Y` 本身就是用户声明的
        变量/字段/形参/函数名，那它是一个普通标识符，绝不能再拆成成员访问。

        为什么必须有这条：`设 目的项 = 5` 后 `打印 目的项` 在加这条之前实测发射
        `目的项 = 5` + `print(目.items())`（.scratch/probe_out.txt:C8）——赋值侧
        按整名发、读取侧按后缀拆，两侧对不上。`目` 通常未定义所以是 NameError，
        但只要恰好存在一个叫 `目` 的名字，就变成「能编译、语义全错」的静默错译。
        全仓 37255 个 .light 实测没有 `目的项/目的` 这类名字（.scratch/de_scan.txt
        C 节），所以这条判据在本仓不改变任何现有产物，纯属护栏。
        """
        if not isinstance(name, str) or not name:
            return False
        return (name in self._local_variables
                or name in self._class_attr_names
                or name in self._current_method_params
                or name in self._user_defined_functions)

    def _split_member_suffix(self, name: str):
        """拆复合标识符的成员后缀。

        命中返回 (对象部分原名, 输出模板)，模板用 `{o}` 占位对象代码；
        不命中返回 None。要求对象部分非空——`的项` 这种整体就是后缀的名字
        不改写（否则会发射出 `.items()` 这种半截表达式）。
        """
        if not isinstance(name, str):
            return None
        # 整名就是用户声明过的名字 -> 普通标识符，不拆（见 _is_known_binding）
        if self._is_known_binding(name):
            return None
        for suffix, tmpl in self._MEMBER_SUFFIX_MAP:
            if name.endswith(suffix) and len(name) > len(suffix):
                obj = name[:-len(suffix)]
                # 对象部分不能以 `.` 收尾（如 `己.的项`），那不是成员访问
                if obj and not obj.endswith('.'):
                    return obj, tmpl
        return None

    def _match_orphan_suffix_call(self, expr):
        """成员访问被 lexer 切碎后错吞成"方法调用"的 `的X` 后缀修复。

        背景（实测取证，见 .scratch/report_annot_member.md）：lexer 对纯汉字
        序列本不切 `的`，但当尾巴前的名字（如 `成绩`）已作为类字段登记进符号表
        时，`成绩的项` 会被切成 IDENTIFIER(成绩) + IDENTIFIER(的项) 两个 token
        （实测 .scratch/lex_prog.txt:S1 与 S2 对照）。于是 `自之成绩的项` 被
        parser_expr.py:2606-2625 的无括号成员调用分支解析成
        MemberAccess(obj=自, member=成绩, is_method_call=True, args=[Id(的项)])
        ——`的项` 被当成了唯一实参。直接发射就是 `self.成绩(的项)`：
        Python 能编译，运行期才炸（AttributeError / 把 dict 当函数调）。

        这里不另起一套后缀表，而是复用 Identifier / 属性访问两条路径共用的
        _MEMBER_SUFFIX_MAP：只要唯一实参**整体**是某个已知后缀 token
        （的项/的长度/的键/的值），就判定这是 `obj.member的X` 的成员后缀访问，
        按同一套模板把 `obj.member` 折进去。命中返回产物字符串，否则 None。

        安全性：全仓 37255 个 .light 扫描（.scratch/de_scan.txt）确认，
        `的项/的长度/的键/的值` 从不作为独立标识符出现（一旦独立就会被切开），
        故「唯一实参恰好整体等于后缀」只可能来自这条切分假象，不会误伤真实实参。
        """
        args = getattr(expr, 'args', None) or []
        if len(args) != 1:
            return None
        arg = args[0]
        arg_name = getattr(arg, 'name', None)
        if not isinstance(arg_name, str):
            return None
        for suffix, tmpl in self._MEMBER_SUFFIX_MAP:
            if arg_name == suffix:
                obj = self._generate_expr(expr.obj)
                member = self._sanitize_name(expr.member)
                return tmpl.format(o=f"{obj}.{member}")
        return None


    def _map_self_prefix(self, name: str) -> str:
        """把 `己.X` / `自.X`（以及裸 `己`/`自`）里的 self 引用名换成 `self`。

        不做类属性 self. 注入，只管「已经带点的 self 引用前缀」这一件事，
        供 VarDecl 赋值目标与 ParagraphCall 粘连方法名两处共用——它们拿到的
        已经是折叠好的带点名字，不能再走 _resolve_identifier_name 的类属性分支
        （否则 `己.x` 会被当成类属性名再套一层 self.）。
        """
        if not isinstance(name, str):
            return name
        for sref in self._SELF_NAMES:
            if name == sref:
                return 'self'
            if name.startswith(sref + '.'):
                return 'self.' + name[len(sref) + 1:]
        return name

    def _resolve_identifier_name(self, raw_name: str) -> str:
        """把光明标识符原名解析成 Python 名（含类方法内的 self 归一）。

        与 Identifier 分支共用：后缀改写拆出的「对象部分」也必须走这里，
        否则 `己之成绩的项` 会漏出裸 `己`（NameError）。
        """
        name = self._sanitize_name(raw_name)
        # 己/自 → self（仅在类方法中），己.attr / 自.attr → self.attr
        if self._in_class_method:
            mapped = self._map_self_prefix(name)
            if mapped != name:
                return mapped

        # 类方法中，如果引用的是类属性且不是参数名，添加 self. 前缀
        if (self._in_class_method and raw_name in self._class_attr_names
                and raw_name not in self._current_method_params):
            return f"self.{name}"
        return name

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

    # FFI 基本类型映射：光明类型 → ctypes 类型表达式
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

    # 用户自定义 FFI 类型名 → 生成的 Python 类型表达式
    # 在 _generate_ffi_struct_def / _union_def / _funcptr_def / _typedef_def 中注册
    _ffi_user_types: Dict[str, str] = {}

    def _get_ffi_type(self, type_name: str) -> str:
        """解析 FFI 类型名 → ctypes 类型表达式。
        优先查找基本类型映射，再查找用户自定义类型。
        """
        if type_name in self._ffi_type_map:
            return self._ffi_type_map[type_name]
        if type_name in self._ffi_user_types:
            return self._ffi_user_types[type_name]
        # 未知类型：回退到 void*
        return 'ctypes.c_void_p'

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
            ctype = self._get_ffi_type(light_type)
            arg_types.append(ctype)

        restype = 'None'
        if stmt.return_type:
            restype = self._get_ffi_type(stmt.return_type)

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
            ftype = self._get_ffi_type(f['type'])
            fields_code.append(f"('{fname}', {ftype})")
        fields_str = ', '.join(fields_code)
        self._add_line(f"# 外部结构体: {name}")
        self._add_line(f"class {name}(ctypes.Structure):")
        self.indent_level += 1
        self._add_line(f"_fields_ = [{fields_str}]")
        self.indent_level -= 1
        self._add_line("")
        # 注册到用户自定义类型表，供后续使用（如作为函数参数/返回类型、嵌套结构体字段）
        self._ffi_user_types[stmt.name] = name
        # 也注册到运行时类型注册表，供 获取类型() 在运行时查找
        self._add_line(f"_light_ffi.注册类型('{stmt.name}', {name})")

    def _generate_ffi_callback_def(self, stmt: FFICallbackDef):
        """生成外部回调类型定义"""
        name = self._sanitize_name(stmt.name)
        arg_types = []
        for p in stmt.params:
            light_type = p.get('type', '整数')
            ctype = self._get_ffi_type(light_type)
            arg_types.append(ctype)
        restype = 'None'
        if stmt.return_type:
            restype = self._get_ffi_type(stmt.return_type)
        arg_types_str = ', '.join(arg_types)
        self._add_line(f"# 外部回调类型: {name}")
        self._add_line(f"{name} = ctypes.CFUNCTYPE({restype}, {arg_types_str})")
        self._add_line("")
        # 注册回调类型，供函数声明等使用
        self._ffi_user_types[stmt.name] = name
        self._add_line(f"_light_ffi.注册类型('{stmt.name}', {name})")

    def _generate_ffi_create_array(self, stmt: FFICreateArray):
        """生成创建数组代码"""
        base_type = stmt.base_type
        ctype = self._get_ffi_type(base_type)
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
            ftype = self._get_ffi_type(f['type'])
            fields_code.append(f"('{fname}', {ftype})")
        fields_str = ', '.join(fields_code)
        self._add_line(f"# C联合体: {name}")
        self._add_line(f"class {name}(ctypes.Union):")
        self.indent_level += 1
        self._add_line(f"_fields_ = [{fields_str}]")
        self.indent_level -= 1
        self._add_line("")
        # 注册联合体类型
        self._ffi_user_types[stmt.name] = name
        self._add_line(f"_light_ffi.注册类型('{stmt.name}', {name})")

    def _generate_ffi_varargs_decl(self, stmt: FFIVarArgsDecl):
        """生成变长参数函数声明代码"""
        name = self._sanitize_name(stmt.name)
        library_alias = self._sanitize_name(stmt.library_alias)
        c_name = stmt.c_name or stmt.name
        
        arg_types = []
        for p in stmt.params:
            light_type = p.get('type', '整数')
            ctype = self._get_ffi_type(light_type)
            arg_types.append(ctype)
        
        restype = 'None'
        if stmt.return_type:
            restype = self._get_ffi_type(stmt.return_type)
        
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
        base_type = self._get_ffi_type(stmt.base_type)
        self._add_line(f"# C类型别名: {name} -> {base_type}")
        self._add_line(f"{name} = {base_type}")
        self._add_line("")
        # 注册类型别名
        self._ffi_user_types[stmt.name] = name
        self._add_line(f"_light_ffi.注册类型('{stmt.name}', {name})")

    def _generate_ffi_bitfield_def(self, stmt: FFIBitfieldDef):
        """生成C位域定义代码"""
        name = self._sanitize_name(stmt.name)
        base_type = self._get_ffi_type(stmt.base_type)
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
            ctype = self._get_ffi_type(light_type)
            arg_types.append(ctype)
        restype = 'None'
        if stmt.return_type:
            restype = self._get_ffi_type(stmt.return_type)
        arg_types_str = ', '.join(arg_types) if arg_types else ''
        self._add_line(f"# C函数指针类型: {name}")
        self._add_line(f"{name} = ctypes.CFUNCTYPE({restype}, {arg_types_str})")
        self._add_line("")
        # 注册函数指针类型
        self._ffi_user_types[stmt.name] = name
        self._add_line(f"_light_ffi.注册类型('{stmt.name}', {name})")

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

    # =========================================================================
    # C FFI 表达式级代码生成（第二阶段：指针/数组/错误处理）
    # =========================================================================

    def _generate_ffi_pointer_type(self, expr: FFIPointerType) -> str:
        """生成指针类型表达式：指针[整数] → ctypes.POINTER(ctypes.c_int)"""
        base_type = self._get_ffi_type(expr.base_type)
        return f"ctypes.POINTER({base_type})"

    def _generate_ffi_array_type(self, expr: FFIArrayType) -> str:
        """生成数组类型表达式：数组[整数, 5] → (ctypes.c_int * 5)"""
        base_type = self._get_ffi_type(expr.base_type)
        if expr.size is not None:
            size = self._generate_expr(expr.size) if isinstance(expr.size, ASTNode) else str(expr.size)
            return f"({base_type} * {size})"
        return f"({base_type} * 0)"

    def _generate_ffi_address_of(self, expr: FFIAddressOf) -> str:
        """生成取地址表达式：取地址(变量) → ctypes.pointer(变量)"""
        target = self._generate_expr(expr.target)
        return f"ctypes.pointer({target})"

    def _generate_ffi_dereference(self, expr: FFIDereference) -> str:
        """生成解引用表达式：解引用(指针) → 指针[0]"""
        pointer = self._generate_expr(expr.pointer)
        return f"{pointer}[0]"

    def _generate_ffi_pointer_offset(self, expr: FFIPointerOffset) -> str:
        """生成指针偏移表达式：指针偏移(指针, 偏移量) → ctypes.cast(指针, ctypes.POINTER(ctypes.c_byte))[偏移量]"""
        pointer = self._generate_expr(expr.pointer)
        offset = self._generate_expr(expr.offset)
        return f"ctypes.cast({pointer}, ctypes.POINTER(ctypes.c_byte))[{offset}]"

    def _generate_ffi_get_last_error(self, expr: FFIGetLastError) -> str:
        """生成获取FFI错误表达式：获取FFI错误() → _light_ffi.获取FFI错误()"""
        return "_light_ffi.获取FFI错误()"

    def _generate_ffi_get_errno(self, expr: FFIGetErrno) -> str:
        """生成获取系统错误码表达式：获取系统错误码() → ctypes.get_errno()"""
        return "ctypes.get_errno()"

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
            self._add_line(f"if '_LIGHT_SQL_CONNS' not in globals(): _LIGHT_SQL_CONNS = {{}}")
            self._add_line(f"if '{db_var}' not in _LIGHT_SQL_CONNS:")
            self._add_line(f"    _LIGHT_SQL_CONNS['{db_var}'] = _light_sqlite3.connect(':memory:' if '{db_var}' == 'default' else '{db_var}.db')")
            self._add_line(f"    _LIGHT_SQL_CONNS['{db_var}'].row_factory = _light_sqlite3.Row")
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
                    self._add_line(f"    _c = _LIGHT_SQL_CONNS['{db_var}'].cursor()")
                    self._add_line(f"    _c.execute({sql_py_repr}, tuple(params))")
                    self._add_line(f"    return [dict(_r) for _r in _c.fetchall()]")
                else:
                    # 返回影响行数的 DDL/DML 函数
                    fn_name = f"l3_sql_{db_var or 'default'}_e{idx}" if statements else f"l3_sql_exec_{db_var}"
                    self._add_line(f"def {fn_name}(params=()):")
                    self._add_line(f"    _c = _LIGHT_SQL_CONNS['{db_var}'].cursor()")
                    self._add_line(f"    _c.execute({sql_py_repr}, tuple(params))")
                    self._add_line(f"    _LIGHT_SQL_CONNS['{db_var}'].commit()")
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
            self._add_line("except Exception as _LIGHT_L3_SYM_ERR:")
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
                    self._add_line("    if not _light_l3_sym: raise RuntimeError(f'sympy未装: {_LIGHT_L3_SYM_ERR}')")
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
                    self._add_line("    if not _light_l3_sym: raise RuntimeError(f'sympy未装: {_LIGHT_L3_SYM_ERR}')")
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
                    self._add_line("    if not _light_l3_sym: raise RuntimeError(f'sympy未装: {_LIGHT_L3_SYM_ERR}')")
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
                    self._add_line("    if not _light_l3_sym: raise RuntimeError(f'sympy未装: {_LIGHT_L3_SYM_ERR}')")
                    self._add_line(f"    from sympy import Matrix")
                    self._add_line(f"    R = Matrix({m_mat.group(1)}) * Matrix({m_mat.group(2)})")
                    self._add_line(f"    return [list(row) for row in R.tolist()]")
                    continue
                # 默认：表达式化简
                fn_name = f"l3_math_simp_{safe_name}_{idx}"
                self._add_line(f"def {fn_name}():")
                self._add_line("    if not _light_l3_sym: raise RuntimeError(f'sympy未装: {_LIGHT_L3_SYM_ERR}')")
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
            self._add_line("_LIGHT_C_CODE = '''")
            for line in code.split('\n'):
                self._add_line(line)
            self._add_line("'''")
            # 平台检测：.so vs .dll
            self._add_line("_LIGHT_C_EXT = '.dll' if _light_sys.platform == 'win32' else '.so'")
            # 编译器检测：gcc > cc > clang
            self._add_line("_LIGHT_C_CC = None")
            self._add_line("for _LIGHT_C_CAND in ['gcc', 'cc', 'clang']:")
            self._add_line("    try:")
            self._add_line("        _light_sp.run([_LIGHT_C_CAND, '--version'], capture_output=True, check=True)")
            self._add_line("        _LIGHT_C_CC = _LIGHT_C_CAND; break")
            self._add_line("    except Exception: pass")
            # 写临时 C 文件
            self._add_line("_LIGHT_C_SRC = _light_tmp.NamedTemporaryFile(suffix='.c', delete=False, mode='w', encoding='utf-8')")
            self._add_line("_LIGHT_C_SRC.write('#include <stdlib.h>\\n#include <string.h>\\n#include <math.h>\\n')")
            self._add_line("_LIGHT_C_SRC.write(_LIGHT_C_CODE)")
            self._add_line("_LIGHT_C_SRC.close()")
            self._add_line("_LIGHT_C_LIB = _LIGHT_C_SRC.name.replace('.c', _LIGHT_C_EXT)")
            # 编译
            self._add_line("if _LIGHT_C_CC:")
            self._add_line("    _light_sp.run([_LIGHT_C_CC, '-shared', '-fPIC', '-O2', '-o', _LIGHT_C_LIB, _LIGHT_C_SRC.name, '-lm'], check=True)")
            # 加载动态库
            self._add_line("_LIGHT_C_DLL = _light_ctypes.CDLL(_LIGHT_C_LIB) if _LIGHT_C_CC else None")
            # 自动解析 C 函数签名，生成 Python 可调用封装
            self._add_line("_LIGHT_C_FUNCS = _light_l4_re.findall(r'(?:int|float|double|void|long|char\\s*\\*)\\s+(\\w+)\\s*\\(', _LIGHT_C_CODE)")
            self._add_line("for _LIGHT_C_FN in _LIGHT_C_FUNCS:")
            self._add_line("    if _LIGHT_C_DLL:")
            self._add_line("        try:")
            # 尝试推断返回类型和参数类型
            self._add_line("            _LIGHT_C_FN_OBJ = getattr(_LIGHT_C_DLL, _LIGHT_C_FN)")
            self._add_line("            _LIGHT_C_FN_OBJ.restype = _light_ctypes.c_double")
            self._add_line("            globals()[_LIGHT_C_FN] = _LIGHT_C_FN_OBJ")
            self._add_line("        except Exception:")
            self._add_line("            globals()[_LIGHT_C_FN] = lambda *a, _fn=_LIGHT_C_FN: f'[C:{_fn} 未加载]'")
            self._add_line("    else:")
            self._add_line("        globals()[_LIGHT_C_FN] = lambda *a, _fn=_LIGHT_C_FN: f'[C:{_fn} 编译器未找到]'")
            # v7 单 20：不要 del 循环变量 _LIGHT_C_FN —— 块内提不出任何函数声明时
            # （如只有 #define 的 C 块）它从未被绑定，del 会 NameError 打断整个产物。
            self._add_line("del _LIGHT_C_CODE, _LIGHT_C_FUNCS")
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
            self._add_line("_LIGHT_GO_CODE = '''")
            for line in code.split('\n'):
                self._add_line(line)
            self._add_line("'''")
            # v7 单 20：导出名提取提到 go 探测之外（对齐 C 路径 :3443 的无条件提取）。
            # 原实现把 findall 放在 build 成功的 try 里，无 go 时连"要绑哪些名字"都不知道。
            self._add_line("_LIGHT_GO_EXPORTS = _light_l4_re.findall(r'//export\\s+(\\w+)', _LIGHT_GO_CODE)")
            # 检测 Go 编译器
            self._add_line("_LIGHT_GO_OK = False")
            self._add_line("try:")
            self._add_line("    _light_sp.run(['go', 'version'], capture_output=True, check=True)")
            self._add_line("    _LIGHT_GO_OK = True")
            self._add_line("except Exception: pass")
            # 写 Go 源文件
            self._add_line("if _LIGHT_GO_OK:")
            self._add_line("    _LIGHT_GO_EXT = '.dll' if _light_sys.platform == 'win32' else '.so'")
            self._add_line("    _LIGHT_GO_DIR = _light_tmp.mkdtemp(prefix='light_go_')")
            self._add_line("    _LIGHT_GO_SRC = _light_os.path.join(_LIGHT_GO_DIR, 'main.go')")
            # 包装 Go 代码为 c-shared 导出库
            self._add_line("    _LIGHT_GO_WRAPPED = 'package main\\n\\nimport \"C\"\\n\\n' + _LIGHT_GO_CODE")
            self._add_line("    with open(_LIGHT_GO_SRC, 'w', encoding='utf-8') as _f: _f.write(_LIGHT_GO_WRAPPED)")
            # 初始化 go.mod
            self._add_line("    _light_sp.run(['go', 'mod', 'init', 'light_l4_go'], cwd=_LIGHT_GO_DIR, capture_output=True)")
            # 编译为 c-shared 库
            self._add_line("    _LIGHT_GO_LIB = _light_os.path.join(_LIGHT_GO_DIR, 'light_go' + _LIGHT_GO_EXT)")
            self._add_line("    try:")
            self._add_line("        _light_sp.run(['go', 'build', '-buildmode=c-shared', '-o', _LIGHT_GO_LIB, _LIGHT_GO_SRC], cwd=_LIGHT_GO_DIR, check=True)")
            self._add_line("        _LIGHT_GO_DLL = _light_ctypes.CDLL(_LIGHT_GO_LIB)")
            self._add_line("        for _LIGHT_GO_FN in _LIGHT_GO_EXPORTS:")
            self._add_line("            try:")
            self._add_line("                _LIGHT_GO_FN_OBJ = getattr(_LIGHT_GO_DLL, _LIGHT_GO_FN)")
            self._add_line("                _LIGHT_GO_FN_OBJ.restype = _light_ctypes.c_double")
            self._add_line("                globals()[_LIGHT_GO_FN] = _LIGHT_GO_FN_OBJ")
            self._add_line("            except Exception:")
            self._add_line("                globals()[_LIGHT_GO_FN] = lambda *a, _fn=_LIGHT_GO_FN: f'[Go:{_fn} 未加载]'")
            self._add_line("    except Exception as _LIGHT_GO_ERR:")
            self._add_line("        print(f'[L4 Go] 编译失败: {_LIGHT_GO_ERR}')")
            self._add_line("else:")
            self._add_line("    print('[L4 Go] Go 编译器未安装, 跳过')")
            # v7 单 20：无论 go 是否安装、build 是否成功，导出名都必须绑上占位，
            # 与 C 路径的三分支全覆盖（:3450/:3452/:3454）对齐。原实现只在
            # build 成功的 try 块里绑定，无 go 时 `斐波那契(10)` 直接 NameError。
            # `not in globals()` 保证 build 成功时不覆盖上面绑好的真实函数对象。
            self._add_line("for _LIGHT_GO_FN in _LIGHT_GO_EXPORTS:")
            self._add_line("    if _LIGHT_GO_FN not in globals():")
            self._add_line("        globals()[_LIGHT_GO_FN] = lambda *a, _fn=_LIGHT_GO_FN: f'[Go:{_fn} 编译器未找到]'")
            # 不要 del 循环变量 _LIGHT_GO_FN：导出名为空时它从未被绑定，del 会 NameError
            self._add_line("del _LIGHT_GO_CODE, _LIGHT_GO_EXPORTS")
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
            self._add_line("_LIGHT_MBT_CODE = '''")
            for line in code.split('\n'):
                self._add_line(line)
            self._add_line("'''")
            # 检测 MoonBit 工具链
            self._add_line("_LIGHT_MBT_OK = False")
            self._add_line("try:")
            self._add_line("    _light_sp.run(['moon', 'version'], capture_output=True, check=True)")
            self._add_line("    _LIGHT_MBT_OK = True")
            self._add_line("except Exception: pass")
            # 创建 MoonBit 项目并编译
            self._add_line("if _LIGHT_MBT_OK:")
            self._add_line("    _LIGHT_MBT_DIR = _light_tmp.mkdtemp(prefix='light_mbt_')")
            self._add_line("    _LIGHT_MBT_SRC = _light_os.path.join(_LIGHT_MBT_DIR, 'main.mbt')")
            self._add_line("    with open(_LIGHT_MBT_SRC, 'w', encoding='utf-8') as _f: _f.write(_LIGHT_MBT_CODE)")
            # 生成 moon.pkg.json
            self._add_line("    _LIGHT_MBT_PKG = _light_os.path.join(_LIGHT_MBT_DIR, 'moon.pkg.json')")
            self._add_line("    with open(_LIGHT_MBT_PKG, 'w') as _f: _light_json.dump({}, _f)")
            # 编译为 wasm
            self._add_line("    try:")
            self._add_line("        _light_sp.run(['moon', 'build', '--target', 'wasm'], cwd=_LIGHT_MBT_DIR, check=True, capture_output=True)")
            # 尝试用 wasmtime 执行
            self._add_line("        _LIGHT_MBT_WASM = _light_os.path.join(_LIGHT_MBT_DIR, 'target', 'wasm', 'release', 'build', 'main.wasm')")
            self._add_line("        if not _light_os.path.exists(_LIGHT_MBT_WASM):")
            # 尝试其他路径
            self._add_line("            _LIGHT_MBT_WASM = _light_os.path.join(_LIGHT_MBT_DIR, 'target', 'wasm', 'debug', 'build', 'main.wasm')")
            self._add_line("        if _light_os.path.exists(_LIGHT_MBT_WASM):")
            self._add_line("            try:")
            self._add_line("                _LIGHT_MBT_OUT = _light_sp.run(['wasmtime', _LIGHT_MBT_WASM], capture_output=True, text=True, timeout=30)")
            self._add_line("                print(f'[MoonBit wasm] {_LIGHT_MBT_OUT.stdout.strip()}')")
            self._add_line("                if _LIGHT_MBT_OUT.stderr: print(f'[MoonBit wasm stderr] {_LIGHT_MBT_OUT.stderr.strip()}')")
            self._add_line("            except Exception as _LIGHT_MBT_WASM_ERR:")
            self._add_line("                print(f'[MoonBit] wasm 编译成功但 wasmtime 执行失败: {_LIGHT_MBT_WASM_ERR}')")
            self._add_line("                print(f'[MoonBit] wasm 文件位于: {_LIGHT_MBT_WASM}')")
            self._add_line("        else:")
            self._add_line("            print(f'[MoonBit] 编译完成但未找到 wasm 文件')")
            self._add_line("    except Exception as _LIGHT_MBT_ERR:")
            self._add_line("        print(f'[L4 MoonBit] 编译失败: {_LIGHT_MBT_ERR}')")
            self._add_line("else:")
            self._add_line("    print('[L4 MoonBit] MoonBit 工具链未安装, 跳过')")
            self._add_line("del _LIGHT_MBT_CODE")
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
