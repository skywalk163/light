# -*- coding: utf-8 -*-
"""
光明 ↔ Python 双向翻译器

提供 Python 代码与光明（LightLang）代码之间的双向翻译功能。

用法:
    from translator import PythonToLightTranslator, LightToPythonTranslator

    # Python → 光明
    translator = PythonToLightTranslator()
    light_code = translator.translate("print('hello')")

    # 光明 → Python
    translator = LightToPythonTranslator()
    python_code = translator.translate('打印("hello")')
"""

import ast
import os
import sys
from typing import Dict, List, Optional, Tuple, Any, Union


# 路径设置
_TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(os.path.dirname(_TOOL_DIR))
sys.path.insert(0, _TOOL_DIR)
sys.path.insert(0, os.path.join(_PROJECT_DIR, 'src'))


# =============================================================================
# 关键字映射表
# =============================================================================

# Python → 光明 关键字映射
PYTHON_TO_LIGHT_KEYWORDS: Dict[str, str] = {
    # 控制流
    'if': '如果',
    'elif': '否则如果',
    'else': '否则',
    'for': '遍历',
    'while': '当',
    'break': '跳出',
    'continue': '跳过',
    'return': '返回',
    'pass': 'pass',
    'match': '匹配',
    'case': '情况',

    # 函数/类定义
    'def': '段落',
    'class': '类',
    'lambda': '接收',
    'yield': '产出',
    'yield from': '产出从',

    # 异常处理
    'try': '尝试',
    'except': '捕获',
    'finally': '最终',
    'raise': '抛出',

    # 异步
    'async': '异步',
    'await': '等待',

    # 上下文管理器
    'with': '使用',
    'as': '为',

    # 导入
    'import': '导入',
    'from': '从',

    # 变量/赋值
    'self': '己',
    'super': '父',
    'True': '真',
    'False': '假',
    'None': '空',
    'global': '全局',
    'nonlocal': '非局部',

    # 运算符
    'and': '且',
    'or': '或',
    'not': '非',
    'is': '是',
    'in': '在',
    'not in': '不在',
    'is not': '不是',
    'del': '删除',
    'assert': '断言',
}

# 光明 → Python 关键字映射
LIGHT_TO_PYTHON_KEYWORDS: Dict[str, str] = {
    # 控制流
    '如果': 'if',
    '否则如果': 'elif',
    '否则若': 'elif',
    '否则': 'else',
    '遍历': 'for',
    '当': 'while',
    '跳出': 'break',
    '跳过': 'continue',
    '返回': 'return',
    '结束': '',
    'pass': 'pass',
    '匹配': 'match',
    '情况': 'case',
    '默认': 'case _',

    # 函数/类定义
    '段落': 'def',
    '函数': 'def',
    '段': 'def',
    '类': 'class',
    '接收': 'lambda',
    '产出': 'yield',
    '产出从': 'yield from',

    # 异常处理
    '尝试': 'try',
    '捕获': 'except',
    '最终': 'finally',
    '抛出': 'raise',

    # 异步
    '异步': 'async',
    '等待': 'await',

    # 上下文管理器
    '使用': 'with',
    '为': 'as',

    # 导入
    '导入': 'import',
    '从': 'from',

    # 变量/赋值
    '设': '',
    '己': 'self',
    '父': 'super',
    '真': 'True',
    '假': 'False',
    '空': 'None',
    '无': 'None',
    '全局': 'global',
    '非局部': 'nonlocal',

    # 运算符
    '且': 'and',
    '与': 'and',
    '或': 'or',
    '非': 'not',
    '是': 'is',
    '在': 'in',
    '不在': 'not in',
    '不是': 'is not',
    '删除': 'del',
    '断言': 'assert',

    # 声明
    '定义': '',
    '属性': '',
    '构造': 'def __init__',
    '新建': '',
    '标注': '@',
    '静态': '@staticmethod',
    '类方法': '@classmethod',
    '特性': '@property',
    '抽象': '@abstractmethod',
    '嵌入': '',
    '结束嵌入': '',
    '导出': '',
    '外部': '',
    '推迟': '',
    '并行': '',
    '并': '|',
    '数据': '',
    '枚举': '',
    '接口': '',
    '实现': '',
    '结构体': '',
    '类型别名': '',
    'trait': '',
    '开启类型检查': '',
    '关闭类型检查': '',
}

# 运算符映射表（中文运算符 → Python 运算符）
OPERATOR_MAP: Dict[str, str] = {
    '加': '+',
    '减': '-',
    '乘': '*',
    '除': '/',
    '除以': '/',
    '整除': '//',
    '模': '%',
    '取余': '%',
    '幂': '**',
    '求幂': '**',
    '大于': '>',
    '小于': '<',
    '等于': '==',
    '不等于': '!=',
    '大于等于': '>=',
    '小于等于': '<=',
    '不小于': '>=',
    '不大于': '<=',
    '且': 'and',
    '与': 'and',
    '或': 'or',
    '非': 'not',
    '异或': '^',
    '左移': '<<',
    '右移': '>>',
}

# 内置函数映射表（中文 → Python）
BUILTIN_FUNC_MAP: Dict[str, str] = {
    '打印': 'print',
    '显示': 'print',
    '输出': 'print',
    '读取': 'input',
    '输入': 'input',
    '长度': 'len',
    '类型': 'type',
    '范围': 'range',
    '整数': 'int',
    '浮数': 'float',
    '小数': 'float',
    '字符串': 'str',
    '串': 'str',
    '列表': 'list',
    '列': 'list',
    '字典': 'dict',
    '典': 'dict',
    '集合': 'set',
    '集': 'set',
    '布尔': 'bool',
    '绝对值': 'abs',
    '最大值': 'max',
    '最小值': 'min',
    '求和': 'sum',
    '排序': 'sorted',
    '反转': 'reversed',
    '筛选': 'filter',
    '映射': 'map',
    '打包': 'zip',
    '枚举': 'enumerate',
    '全部': 'all',
    '任意': 'any',
    '四舍五入': 'round',
    '取整': 'int',
    '转整数': 'int',
    '转小数': 'float',
    '转浮点': 'float',
    '转字符串': 'str',
    '解析JSON': 'json.loads',
    '序列化JSON': 'json.dumps',
    '打开': 'open',
    '关闭': 'close',
    '读取文件': 'open(...).read',
    '写入文件': 'open(...).write',
}

# Python 内置函数 → 光明 映射
PYTHON_TO_LIGHT_BUILTIN: Dict[str, str] = {
    'print': '打印',
    'input': '读取',
    'len': '长度',
    'type': '类型',
    'range': '范围',
    'int': '整数',
    'float': '浮数',
    'str': '串',
    'bool': '布尔',
    'list': '列',
    'dict': '典',
    'set': '集',
    'abs': '绝对值',
    'max': '最大值',
    'min': '最小值',
    'sum': '求和',
    'sorted': '排序',
    'reversed': '反转',
    'filter': '筛选',
    'map': '映射',
    'zip': '打包',
    'enumerate': '枚举',
    'all': '全部',
    'any': '任意',
    'round': '四舍五入',
    'open': '打开',
    'isinstance': '实例检查',
    'super': '父',
}

# 异常名映射表（中文 → Python）
EXCEPTION_MAP: Dict[str, str] = {
    '异常': 'Exception',
    '值错误': 'ValueError',
    '数值错误': 'ValueError',
    '类型错误': 'TypeError',
    '键错误': 'KeyError',
    '索引错误': 'IndexError',
    '属性错误': 'AttributeError',
    '导入错误': 'ImportError',
    '模块未找到': 'ModuleNotFoundError',
    '文件未找到': 'FileNotFoundError',
    '文件错误': 'FileNotFoundError',
    '零除错误': 'ZeroDivisionError',
    '除以零': 'ZeroDivisionError',
    '运行时错误': 'RuntimeError',
    '溢出错误': 'OverflowError',
    '递归错误': 'RecursionError',
    '内存错误': 'MemoryError',
    '系统错误': 'SystemError',
    '断言错误': 'AssertionError',
    '停止迭代': 'StopIteration',
    '迭代停止': 'StopIteration',
    '权限错误': 'PermissionError',
    '连接错误': 'ConnectionError',
    '超时错误': 'TimeoutError',
    '算术错误': 'ArithmeticError',
    '浮点错误': 'FloatingPointError',
    'OS错误': 'OSError',
}

# Python 异常名 → 光明 映射
PYTHON_TO_LIGHT_EXCEPTION: Dict[str, str] = {
    'Exception': '异常',
    'ValueError': '值错误',
    'TypeError': '类型错误',
    'KeyError': '键错误',
    'IndexError': '索引错误',
    'AttributeError': '属性错误',
    'ImportError': '导入错误',
    'ModuleNotFoundError': '模块未找到',
    'FileNotFoundError': '文件未找到',
    'ZeroDivisionError': '除以零',
    'RuntimeError': '运行时错误',
    'OverflowError': '溢出错误',
    'RecursionError': '递归错误',
    'MemoryError': '内存错误',
    'SystemError': '系统错误',
    'AssertionError': '断言错误',
    'StopIteration': '停止迭代',
    'PermissionError': '权限错误',
    'ConnectionError': '连接错误',
    'TimeoutError': '超时错误',
    'ArithmeticError': '算术错误',
    'FloatingPointError': '浮点错误',
    'OSError': 'OS错误',
}

# 类型注解映射表
TYPE_ANNOTATION_MAP: Dict[str, str] = {
    'int': '整数',
    'float': '浮数',
    'str': '字符串',
    'bool': '布尔',
    'list': '列表',
    'dict': '字典',
    'set': '集合',
    'tuple': '元组',
    'None': '空',
    'any': '任意',
    'Any': '任意',
    'Optional': '可选',
    'Union': '联合',
    'Callable': '可调用',
    'Iterable': '可迭代',
    'Iterator': '迭代器',
    'Generator': '生成器',
    'List': '列表类型',
    'Dict': '字典类型',
    'Set': '集合类型',
    'Tuple': '元组类型',
    'Self': '己',
    'Type': '类型',
    'Sequence': '序列',
    'Mapping': '映射',
}


# =============================================================================
# Python → 光明 翻译器
# =============================================================================

class PythonToLightTranslator:
    """Python 代码 → 光明 翻译器

    将 Python 源码通过 AST 分析，逐节点映射为光明 v6.2 代码。
    支持 Python 语法：
    - 基本语法：import, def, class, if/elif/else, for, while, try/except, with, return, yield
    - 高级语法：async/await, 列表/字典/集合推导式, 生成器表达式, 装饰器, lambda, match/case
    - 类型注解：函数参数/返回值类型注解, 变量类型注解
    - 可变参数：*args, **kwargs
    - 赋值：简单赋值, 类型注解赋值, 增强赋值, 元组解包
    - 异常：try/except/else/finally, raise, raise ... from
    Python 关键字被映射为对应的光明中文关键字。
    """

    def __init__(self) -> None:
        """初始化翻译器"""
        self._transpiler = None

    def _get_transpiler(self) -> Any:
        """延迟加载 Py2LightTranspiler

        Returns:
            Py2LightTranspiler 实例

        Raises:
            ImportError: 如果无法加载 py2light_transpiler 模块
        """
        if self._transpiler is None:
            try:
                from py2light_transpiler import Py2LightTranspiler
                self._transpiler = Py2LightTranspiler()
            except ImportError as e:
                raise ImportError(f"无法加载翻译器模块: {e}") from e
        return self._transpiler

    def translate(self, python_code: str) -> str:
        """将 Python 源码翻译为光明代码

        Args:
            python_code: Python 源码字符串

        Returns:
            翻译后的光明代码字符串

        Raises:
            SyntaxError: 如果 Python 代码有语法错误
            RuntimeError: 如果翻译过程中发生错误
        """
        # 先验证 Python 代码语法
        try:
            tree = ast.parse(python_code)
        except SyntaxError as e:
            raise SyntaxError(f"Python 语法错误: {e}") from e

        # 使用 Py2LightTranspiler 进行翻译
        transpiler = self._get_transpiler()
        try:
            result = transpiler.transpile(python_code)
            return result
        except Exception as e:
            raise RuntimeError(f"翻译失败: {e}") from e

    def translate_file(self, file_path: str) -> str:
        """将 Python 文件翻译为光明代码

        Args:
            file_path: Python 文件路径

        Returns:
            翻译后的光明代码字符串

        Raises:
            FileNotFoundError: 如果文件不存在
            SyntaxError: 如果 Python 代码有语法错误
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            python_code = f.read()
        return self.translate(python_code)

    def translate_with_ast(self, python_code: str) -> Tuple[str, ast.AST]:
        """将 Python 源码翻译为光明代码，同时返回 AST

        Args:
            python_code: Python 源码字符串

        Returns:
            (翻译后的光明代码, Python AST 树)
        """
        tree = ast.parse(python_code)
        result = self.translate(python_code)
        return result, tree

    def analyze_features(self, python_code: str) -> Dict[str, int]:
        """分析 Python 代码中使用的语言特性

        Args:
            python_code: Python 源码字符串

        Returns:
            特性名称到使用次数的映射字典
        """
        try:
            from py2light_transpiler import FeatureUsageCollector
            collector = FeatureUsageCollector()
            tree = ast.parse(python_code)
            collector.visit(tree)
            return collector.get_summary()
        except ImportError:
            return {}

    # =========================================================================
    # 批量翻译
    # =========================================================================

    def batch_translate_directory(
        self,
        source_dir: str,
        target_dir: str,
        direction: str = 'to-duan'
    ) -> Dict[str, str]:
        """批量翻译整个目录中的文件

        Args:
            source_dir: 源目录路径
            target_dir: 目标目录路径
            direction: 翻译方向，'to-duan' 或 'to-python'

        Returns:
            文件路径到翻译结果的映射字典

        Raises:
            FileNotFoundError: 如果源目录不存在
        """
        if not os.path.isdir(source_dir):
            raise FileNotFoundError(f"源目录不存在: {source_dir}")

        os.makedirs(target_dir, exist_ok=True)
        results: Dict[str, str] = {}

        if direction == 'to-duan':
            ext_pattern = '.py'
            target_ext = '.duan'
        else:
            ext_pattern = '.duan'
            target_ext = '.py'

        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if not file.endswith(ext_pattern):
                    continue
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, source_dir)
                target_path = os.path.join(
                    target_dir,
                    os.path.splitext(rel_path)[0] + target_ext
                )

                try:
                    with open(src_path, 'r', encoding='utf-8') as f:
                        code = f.read()

                    if direction == 'to-duan':
                        result = self.translate(code)
                    else:
                        from .translator import light_to_python
                        result = light_to_python(light_code=code)

                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(result)

                    results[src_path] = f"成功 -> {target_path}"
                except Exception as e:
                    results[src_path] = f"失败: {e}"

        return results

    def translate_with_style(self, python_code: str, style: str = 'compact') -> str:
        """根据指定风格翻译 Python 代码为光明代码

        Args:
            python_code: Python 源码字符串
            style: 翻译风格，可选 'compact'（紧凑）, 'verbose'（详细）, 'educational'（教学）

        Returns:
            翻译后的光明代码字符串

        Raises:
            ValueError: 如果风格参数无效
        """
        if style not in ('compact', 'verbose', 'educational'):
            raise ValueError(f"无效的风格: {style}，可选: compact, verbose, educational")

        # 基础翻译
        base_result = self.translate(python_code)

        if style == 'compact':
            # 紧凑风格：移除冗余注释，压缩空白行
            lines = base_result.split('\n')
            compact_lines = []
            for line in lines:
                if line.strip().startswith('#') and not line.strip().startswith('# 光明'):
                    continue
                compact_lines.append(line.rstrip())
            return '\n'.join(compact_lines)

        elif style == 'verbose':
            # 详细风格：添加详细注释
            lines = base_result.split('\n')
            verbose_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('段落 ') or stripped.startswith('函数 '):
                    func_name = stripped.split(' ')[1] if len(stripped.split(' ')) > 1 else '未知'
                    indent = line[:len(line) - len(line.lstrip())]
                    verbose_lines.append(line)
                    verbose_lines.append(f"{indent}# 段落「{func_name}」开始")
                elif stripped.startswith('如果 '):
                    indent = line[:len(line) - len(line.lstrip())]
                    verbose_lines.append(line)
                    verbose_lines.append(f"{indent}# 条件判断分支")
                elif stripped.startswith('遍历 '):
                    indent = line[:len(line) - len(line.lstrip())]
                    verbose_lines.append(line)
                    verbose_lines.append(f"{indent}# 循环遍历开始")
                elif stripped == '否则：':
                    indent = line[:len(line) - len(line.lstrip())]
                    verbose_lines.append(f"{indent}# 否则分支")
                    verbose_lines.append(line)
                else:
                    verbose_lines.append(line)
            return '\n'.join(verbose_lines)

        else:  # educational
            # 教学风格：添加中英文对照注释
            lines = base_result.split('\n')
            edu_lines = []
            edu_lines.append("# =============================================")
            edu_lines.append("# 光明 (LightLang) 教学翻译")
            edu_lines.append("# 逐行注释帮助理解中文编程语法")
            edu_lines.append("# =============================================")
            edu_lines.append("")

            # 分析原始 Python 代码获取相关信息
            try:
                tree = ast.parse(python_code)
                has_class = any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
                has_func = any(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
                has_loop = any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(tree))
                has_if = any(isinstance(node, ast.If) for node in ast.walk(tree))
                has_try = any(isinstance(node, ast.Try) for node in ast.walk(tree))

                features = []
                if has_class: features.append("类定义(Class)")
                if has_func: features.append("函数定义(Function)")
                if has_loop: features.append("循环(Loop)")
                if has_if: features.append("条件判断(If)")
                if has_try: features.append("异常处理(Try/Except)")

                if features:
                    edu_lines.append(f"# 本代码使用了以下特性: {', '.join(features)}")
                    edu_lines.append("")
            except Exception:
                pass

            for line in lines:
                stripped = line.strip()
                if stripped.startswith('段落 '):
                    edu_lines.append("# 【函数定义】段落 = def")
                    edu_lines.append(line)
                elif stripped.startswith('类 '):
                    edu_lines.append("# 【类定义】类 = class")
                    edu_lines.append(line)
                elif stripped.startswith('如果 '):
                    edu_lines.append("# 【条件判断】如果 = if")
                    edu_lines.append(line)
                elif stripped == '否则：':
                    edu_lines.append("# 【否则分支】否则 = else")
                    edu_lines.append(line)
                elif stripped.startswith('遍历 '):
                    edu_lines.append("# 【循环遍历】遍历 = for ... in")
                    edu_lines.append(line)
                elif stripped.startswith('当 '):
                    edu_lines.append("# 【条件循环】当 = while")
                    edu_lines.append(line)
                elif stripped.startswith('尝试'):
                    edu_lines.append("# 【异常处理】尝试 = try")
                    edu_lines.append(line)
                elif stripped.startswith('捕获'):
                    edu_lines.append("# 【异常捕获】捕获 = except")
                    edu_lines.append(line)
                elif stripped.startswith('返回 '):
                    edu_lines.append("# 【返回值】返回 = return")
                    edu_lines.append(line)
                elif stripped.startswith('设 '):
                    edu_lines.append("# 【变量赋值】设 = 变量声明")
                    edu_lines.append(line)
                elif stripped.startswith('打印'):
                    edu_lines.append("# 【输出】打印 = print")
                    edu_lines.append(line)
                else:
                    edu_lines.append(line)

            return '\n'.join(edu_lines)

    def roundtrip_verify(self, python_code: str) -> Dict[str, Any]:
        """验证 Python→光明→Python 往返翻译的准确性

        Args:
            python_code: 原始 Python 源码字符串

        Returns:
            包含验证结果的字典:
            {
                "original": 原始 Python 代码,
                "duan": 翻译后的光明代码,
                "roundtrip": 往返后的 Python 代码,
                "valid": 往返翻译是否有效,
                "errors": 错误列表
            }
        """
        result: Dict[str, Any] = {
            "original": python_code,
            "duan": "",
            "roundtrip": "",
            "valid": False,
            "errors": []
        }

        try:
            # Python → 光明
            light_code = self.translate(python_code)
            result["duan"] = light_code
        except Exception as e:
            result["errors"].append(f"Python→光明 翻译失败: {e}")
            return result

        try:
            # 光明 → Python
            from .translator import light_to_python
            roundtrip_code = light_to_python(light_code=light_code)
            result["roundtrip"] = roundtrip_code
        except Exception as e:
            result["errors"].append(f"光明→Python 翻译失败: {e}")
            return result

        # 验证往返结果
        try:
            # 解析两个 AST 并比较
            original_tree = ast.parse(python_code)
            roundtrip_tree = ast.parse(roundtrip_code)

            # 比较 AST 结构（简化版）
            original_dump = ast.dump(original_tree, indent=2)
            roundtrip_dump = ast.dump(roundtrip_tree, indent=2)

            if original_dump == roundtrip_dump:
                result["valid"] = True
            else:
                result["errors"].append("AST 结构不匹配")
                result["valid"] = False

        except SyntaxError as e:
            result["errors"].append(f"往返代码语法错误: {e}")
            result["valid"] = False
        except Exception as e:
            result["errors"].append(f"验证过程异常: {e}")
            result["valid"] = False

        return result


# =============================================================================
# 光明 → Python 翻译器
# =============================================================================

class LightToPythonTranslator:
    """光明代码 → Python 翻译器

    将光明代码通过解析器生成 AST，再通过 PythonCodeGenerator 生成 Python 代码。
    光明的中文关键字被映射为对应的 Python 英文关键字。

    支持完整的光明语法到 Python 的映射：
    - 中文关键字映射（如果→if, 遍历→for, 段落→def 等）
    - 中文运算符映射（加→+, 且→and 等）
    - 中文内置函数映射（打印→print, 长度→len 等）
    - 中文异常名映射（值错误→ValueError 等）
    - 类型注解映射（整数→int, 字符串→str 等）
    """

    # 关键字映射表（类级别，用于直接查询）
    keyword_map: Dict[str, str] = LIGHT_TO_PYTHON_KEYWORDS
    operator_map: Dict[str, str] = OPERATOR_MAP
    builtin_map: Dict[str, str] = BUILTIN_FUNC_MAP
    exception_map: Dict[str, str] = EXCEPTION_MAP
    type_map: Dict[str, str] = TYPE_ANNOTATION_MAP

    def __init__(self) -> None:
        """初始化翻译器"""
        self._generator = None

    def _get_generator(self) -> Any:
        """延迟加载 PythonCodeGenerator

        Returns:
            PythonCodeGenerator 实例

        Raises:
            ImportError: 如果无法加载 code_generator 模块
        """
        if self._generator is None:
            try:
                from code_generator import PythonCodeGenerator
                self._generator = PythonCodeGenerator()
            except ImportError as e:
                raise ImportError(f"无法加载代码生成器模块: {e}") from e
        return self._generator

    def translate(self, light_code: str) -> str:
        """将光明代码翻译为 Python 代码

        Args:
            light_code: 光明源码字符串

        Returns:
            翻译后的 Python 代码字符串

        Raises:
            ValueError: 如果光明代码有语法错误
            RuntimeError: 如果 Python 代码生成失败
        """
        try:
            from light_parser_v3 import LightParser, ParseError
            parser = LightParser()
            ast_tree = parser.parse(light_code)
        except ParseError as e:
            raise ValueError(f"光明语法错误: {e}") from e
        except Exception as e:
            raise ValueError(f"光明解析失败: {e}") from e

        generator = self._get_generator()
        try:
            result = generator.generate(ast_tree)
            return result
        except Exception as e:
            raise RuntimeError(f"Python 代码生成失败: {e}") from e

    def translate_file(self, file_path: str) -> str:
        """将光明文件翻译为 Python 代码

        Args:
            file_path: 光明文件路径 (.duan)

        Returns:
            翻译后的 Python 代码字符串

        Raises:
            FileNotFoundError: 如果文件不存在
            ValueError: 如果光明代码有语法错误
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            light_code = f.read()
        return self.translate(light_code)

    def lookup_keyword(self, keyword: str) -> Optional[str]:
        """查询光明关键字对应的 Python 关键字

        Args:
            keyword: 光明中文关键字

        Returns:
            对应的 Python 关键字，如果未找到则返回 None
        """
        return self.keyword_map.get(keyword)

    def lookup_operator(self, operator: str) -> Optional[str]:
        """查询光明运算符对应的 Python 运算符

        Args:
            operator: 光明中文运算符

        Returns:
            对应的 Python 运算符，如果未找到则返回 None
        """
        return self.operator_map.get(operator)

    def lookup_builtin(self, name: str) -> Optional[str]:
        """查询光明内置函数对应的 Python 内置函数

        Args:
            name: 光明中文内置函数名

        Returns:
            对应的 Python 内置函数名，如果未找到则返回 None
        """
        return self.builtin_map.get(name)

    def lookup_exception(self, name: str) -> Optional[str]:
        """查询光明异常名对应的 Python 异常名

        Args:
            name: 光明中文异常名

        Returns:
            对应的 Python 异常名，如果未找到则返回 None
        """
        return self.exception_map.get(name)

    def lookup_type(self, type_name: str) -> Optional[str]:
        """查询光明类型名对应的 Python 类型名

        Args:
            type_name: 光明中文类型名

        Returns:
            对应的 Python 类型名，如果未找到则返回 None
        """
        return self.type_map.get(type_name)

    def get_all_keywords(self) -> Dict[str, str]:
        """获取完整的光明→Python 关键字映射表

        Returns:
            关键字映射字典
        """
        return dict(self.keyword_map)

    def get_reverse_keywords(self) -> Dict[str, str]:
        """获取 Python→光明 反向关键字映射表

        Returns:
            反向关键字映射字典（Python 关键字 → 光明关键字）
        """
        reverse = {}
        for k, v in self.keyword_map.items():
            if v:
                reverse[v] = k
        return reverse

    # =========================================================================
    # 批量翻译
    # =========================================================================

    def batch_translate_directory(
        self,
        source_dir: str,
        target_dir: str,
        direction: str = 'to-python'
    ) -> Dict[str, str]:
        """批量翻译整个目录中的光明文件为 Python 文件

        Args:
            source_dir: 源目录路径
            target_dir: 目标目录路径
            direction: 翻译方向，固定为 'to-python'

        Returns:
            文件路径到翻译结果的映射字典

        Raises:
            FileNotFoundError: 如果源目录不存在
        """
        if not os.path.isdir(source_dir):
            raise FileNotFoundError(f"源目录不存在: {source_dir}")

        os.makedirs(target_dir, exist_ok=True)
        results: Dict[str, str] = {}

        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if not file.endswith('.duan'):
                    continue
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, source_dir)
                target_path = os.path.join(
                    target_dir,
                    os.path.splitext(rel_path)[0] + '.py'
                )

                try:
                    with open(src_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    result = self.translate(code)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(result)
                    results[src_path] = f"成功 -> {target_path}"
                except Exception as e:
                    results[src_path] = f"失败: {e}"

        return results

    def translate_with_style(self, light_code: str, style: str = 'compact') -> str:
        """根据指定风格翻译光明代码为 Python 代码

        Args:
            light_code: 光明源码字符串
            style: 翻译风格，可选 'compact'（紧凑）, 'verbose'（详细）, 'educational'（教学）

        Returns:
            翻译后的 Python 代码字符串
        """
        base_result = self.translate(light_code)

        if style == 'compact':
            lines = base_result.split('\n')
            compact_lines = [l.rstrip() for l in lines if l.strip()]
            return '\n'.join(compact_lines)

        elif style == 'verbose':
            lines = base_result.split('\n')
            verbose_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('def '):
                    verbose_lines.append(line)
                    func_name = stripped[4:].split('(')[0]
                    verbose_lines.append(f"    # Function: {func_name}")
                elif stripped.startswith('class '):
                    verbose_lines.append(line)
                    class_name = stripped[6:].split('(')[0].rstrip(':')
                    verbose_lines.append(f"    # Class: {class_name}")
                else:
                    verbose_lines.append(line)
            return '\n'.join(verbose_lines)

        else:  # educational
            lines = base_result.split('\n')
            edu_lines = [
                "# =============================================",
                "# Translated from LightLang (光明)",
                "# =============================================",
                ""
            ]
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('def '):
                    edu_lines.append("# Python function definition (from 段落)")
                    edu_lines.append(line)
                elif stripped.startswith('class '):
                    edu_lines.append("# Python class definition (from 类)")
                    edu_lines.append(line)
                elif stripped.startswith('if '):
                    edu_lines.append("# Python conditional (from 如果)")
                    edu_lines.append(line)
                elif stripped.startswith('for '):
                    edu_lines.append("# Python for loop (from 遍历)")
                    edu_lines.append(line)
                elif stripped.startswith('while '):
                    edu_lines.append("# Python while loop (from 当)")
                    edu_lines.append(line)
                elif stripped.startswith('try'):
                    edu_lines.append("# Python try statement (from 尝试)")
                    edu_lines.append(line)
                elif stripped.startswith('except'):
                    edu_lines.append("# Python except clause (from 捕获)")
                    edu_lines.append(line)
                elif stripped.startswith('print'):
                    edu_lines.append("# Python print function (from 打印)")
                    edu_lines.append(line)
                else:
                    edu_lines.append(line)
            return '\n'.join(edu_lines)

    def roundtrip_verify(self, light_code: str) -> Dict[str, Any]:
        """验证光明→Python→光明 往返翻译的准确性

        Args:
            light_code: 原始光明源码字符串

        Returns:
            包含验证结果的字典
        """
        result: Dict[str, Any] = {
            "original": light_code,
            "python": "",
            "roundtrip": "",
            "valid": False,
            "errors": []
        }

        try:
            python_code = self.translate(light_code)
            result["python"] = python_code
        except Exception as e:
            result["errors"].append(f"光明→Python 翻译失败: {e}")
            return result

        try:
            from .translator import python_to_light
            roundtrip_code = python_to_light(python_code=python_code)
            result["roundtrip"] = roundtrip_code
        except Exception as e:
            result["errors"].append(f"Python→光明 翻译失败: {e}")
            return result

        result["valid"] = len(result["errors"]) == 0
        return result


# =============================================================================
# 便捷函数
# =============================================================================

def python_to_light(
    python_code: str = '',
    file_path: Optional[str] = None,
    return_ast: bool = False
) -> Union[str, Tuple[str, ast.AST]]:
    """将 Python 代码翻译为光明代码（便捷函数）

    Args:
        python_code: Python 源码字符串，如果不为空则直接翻译
        file_path: Python 文件路径，如果 python_code 为空则读取文件
        return_ast: 是否同时返回 AST

    Returns:
        如果 return_ast 为 False，返回翻译后的光明代码字符串
        如果 return_ast 为 True，返回 (光明代码, AST) 元组

    Raises:
        ValueError: 如果 python_code 和 file_path 都为空
    """
    translator = PythonToLightTranslator()
    if file_path and not python_code:
        result = translator.translate_file(file_path)
    elif python_code:
        result = translator.translate(python_code)
    else:
        raise ValueError("必须提供 python_code 或 file_path")

    if return_ast:
        tree = ast.parse(python_code or open(file_path, encoding='utf-8').read())
        return result, tree
    return result


def light_to_python(
    light_code: str = '',
    file_path: Optional[str] = None
) -> str:
    """将光明代码翻译为 Python 代码（便捷函数）

    Args:
        light_code: 光明源码字符串，如果不为空则直接翻译
        file_path: 光明文件路径，如果 light_code 为空则读取文件

    Returns:
        翻译后的 Python 代码

    Raises:
        ValueError: 如果 light_code 和 file_path 都为空
    """
    translator = LightToPythonTranslator()
    if file_path and not light_code:
        return translator.translate_file(file_path)
    elif light_code:
        return translator.translate(light_code)
    else:
        raise ValueError("必须提供 light_code 或 file_path")


def analyze_code_features(python_code: str = '', file_path: Optional[str] = None) -> Dict[str, int]:
    """分析代码中使用的语言特性

    Args:
        python_code: Python 源码字符串
        file_path: Python 文件路径

    Returns:
        特性名称到使用次数的映射字典
    """
    if file_path and not python_code:
        with open(file_path, 'r', encoding='utf-8') as f:
            python_code = f.read()
    translator = PythonToLightTranslator()
    return translator.analyze_features(python_code)


# =============================================================================
# CLI 入口
# =============================================================================

def main() -> None:
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        prog='light-translator',
        description='光明 ↔ Python 双向翻译器',
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--to-duan', metavar='FILE',
                       help='将 Python 文件翻译为光明')
    group.add_argument('--to-python', metavar='FILE',
                       help='将光明文件翻译为 Python')
    parser.add_argument('--output', '-o', metavar='FILE',
                        help='输出到文件（默认输出到终端）')
    parser.add_argument('--analyze', action='store_true',
                        help='分析代码中使用的语言特性')
    parser.add_argument('--list-keywords', action='store_true',
                        help='列出光明→Python 关键字映射表')

    args = parser.parse_args()

    try:
        if args.list_keywords:
            translator = LightToPythonTranslator()
            keywords = translator.get_all_keywords()
            print("光明 → Python 关键字映射表:")
            print("=" * 50)
            for k, v in sorted(keywords.items()):
                if v:
                    print(f"  {k:8s} → {v}")
            return

        if args.to_duan:
            if args.analyze:
                features = analyze_code_features(file_path=args.to_duan)
                print(f"Python 文件 {args.to_duan} 特性分析:")
                print("=" * 50)
                if features:
                    for name, count in features.items():
                        print(f"  {name}: {count} 次")
                else:
                    print("  (未检测到特殊 Python 特性)")
                return
            result = python_to_light('', file_path=args.to_duan)
            source_label = f"Python 文件 {args.to_duan}"
        elif args.to_python:
            result = light_to_python('', file_path=args.to_python)
            source_label = f"光明文件 {args.to_python}"
        else:
            parser.print_help()
            return

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"翻译完成，输出到: {args.output}")
        else:
            print(result)

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except (SyntaxError, ValueError) as e:
        print(f"翻译错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()