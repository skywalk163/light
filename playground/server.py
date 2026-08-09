"""
光明（Light）Web Playground - 后端 API 服务
基于 v3.2 语法的 SRC 后端，提供代码执行、解析、词法分析等功能。
"""

import os
import sys
import json
import uuid
import hashlib
import time
import io
import traceback

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_dir = os.path.dirname(_script_dir)
_src_dir = os.path.join(_project_dir, 'src')
_stdlib_dir = os.path.join(_project_dir, 'stdlib')

for _p in [_project_dir, _src_dir, _stdlib_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

SHARED_DIR = os.path.join(_script_dir, 'shared')
PROJECTS_DIR = os.path.join(_script_dir, 'projects')

os.makedirs(SHARED_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)


def run_light_code(source: str) -> dict:
    """执行光明代码，返回输出和错误信息"""
    try:
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator

        parser = LightParser()
        module = parser.parse(source)

        generator = PythonCodeGenerator()
        py_code = generator.generate(module)

        output_lines = []

        def _capture_print(*args, **kwargs):
            line = ' '.join(str(a) for a in args)
            output_lines.append(line)

        namespace = {
            'print': _capture_print,
            '__name__': '__main__',
            '__file__': os.path.join(_script_dir, 'playground.light')
        }

        start_time = time.time()
        exec(py_code, namespace)
        exec_time = (time.time() - start_time) * 1000

        return {
            'success': True,
            'output': '\n'.join(output_lines) if output_lines else '(无输出)',
            'execution_time': round(exec_time, 2),
            'python_code': py_code
        }

    except Exception as e:
        tb = traceback.format_exc()
        error_type = type(e).__name__
        if 'ParseError' in error_type:
            error_msg = f'语法错误: {e}'
        else:
            error_msg = f'运行时错误: {error_type}: {e}'
        return {
            'success': False,
            'error': error_msg,
            'traceback': tb,
            'output': ''
        }


def parse_light_code(source: str) -> dict:
    """解析光明代码，返回 AST 信息"""
    try:
        from light_parser_v3 import LightParser

        parser = LightParser()
        module = parser.parse(source)

        segments = []
        classes = []
        statement_count = 0

        if hasattr(module, 'segments') and module.segments:
            for s in module.segments:
                params = []
                if hasattr(s, 'params'):
                    for p in s.params:
                        if isinstance(p, dict):
                            params.append(p.get('name', str(p)))
                        else:
                            params.append(getattr(p, 'name', str(p)))
                elif hasattr(s, 'parameters'):
                    for p in s.parameters:
                        if isinstance(p, dict):
                            params.append(p.get('name', str(p)))
                        else:
                            params.append(getattr(p, 'name', str(p)))
                segments.append({
                    'name': s.name,
                    'parameters': params,
                    'return_type': getattr(s, 'return_type', None)
                })
        if hasattr(module, 'classes') and module.classes:
            for c in module.classes:
                methods = []
                if hasattr(c, 'methods'):
                    for m in c.methods:
                        if isinstance(m, dict):
                            methods.append(m.get('name', str(m)))
                        else:
                            methods.append(getattr(m, 'name', str(m)))
                classes.append({
                    'name': c.name,
                    'methods': methods,
                    'parent': getattr(c, 'parent', None)
                })

        if hasattr(module, 'statements'):
            for stmt in module.statements:
                type_name = type(stmt).__name__
                is_segment_def = (
                    type_name == 'Paragraph' or
                    type_name == 'SegmentDefinition' or
                    type_name == 'FunctionDefinition' or
                    (hasattr(stmt, 'body') and hasattr(stmt, 'params') and hasattr(stmt, 'name'))
                )
                if is_segment_def:
                    params = []
                    if hasattr(stmt, 'params'):
                        for p in stmt.params:
                            if isinstance(p, dict):
                                params.append(p.get('name', str(p)))
                            else:
                                params.append(getattr(p, 'name', str(p)))
                    elif hasattr(stmt, 'parameters'):
                        for p in stmt.parameters:
                            if isinstance(p, dict):
                                params.append(p.get('name', str(p)))
                            else:
                                params.append(getattr(p, 'name', str(p)))
                    segments.append({
                        'name': stmt.name if hasattr(stmt, 'name') else str(stmt),
                        'parameters': params,
                        'return_type': getattr(stmt, 'return_type', None)
                    })
                elif type_name in ('ClassDefinition',) or (hasattr(stmt, 'methods') and hasattr(stmt, 'name')):
                    methods = []
                    if hasattr(stmt, 'methods'):
                        methods = [m.name if hasattr(m, 'name') else str(m) for m in stmt.methods]
                    classes.append({
                        'name': stmt.name if hasattr(stmt, 'name') else str(stmt),
                        'methods': methods,
                        'parent': getattr(stmt, 'parent', None)
                    })
                else:
                    statement_count += 1

        import_count = len(module.imports) if hasattr(module, 'imports') else 0
        export_count = len(module.exports) if hasattr(module, 'exports') else 0

        return {
            'success': True,
            'segments': segments,
            'classes': classes,
            'statement_count': statement_count,
            'import_count': import_count,
            'export_count': export_count
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'解析错误: {type(e).__name__}: {e}'
        }


def tokenize_light_code(source: str) -> dict:
    """词法分析，返回 Token 列表"""
    try:
        from lexer import Lexer

        lexer = Lexer()
        tokens = lexer.tokenize(source)

        token_list = []
        for t in tokens:
            token_list.append({
                'type': t.type.name if hasattr(t.type, 'name') else str(t.type),
                'text': str(t.value),
                'line': t.line,
                'column': t.col
            })

        return {
            'success': True,
            'tokens': token_list,
            'token_count': len(token_list),
            'errors': []
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'词法分析错误: {type(e).__name__}: {e}',
            'tokens': [],
            'token_count': 0
        }


def generate_llvm_ir(source: str) -> dict:
    """生成 LLVM IR（如果可用）"""
    try:
        sys.path.insert(0, os.path.join(_src_dir, 'llvm'))
        from compiler import compile_source_to_ir

        ir_code = compile_source_to_ir(source, verbose=False)

        return {
            'success': True,
            'ir_code': ir_code
        }

    except ImportError:
        return {
            'success': False,
            'error': 'LLVM 后端不可用（需要安装 llvmlite）'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'LLVM 编译错误: {type(e).__name__}: {e}'
        }


BUILTIN_EXAMPLES = [
    # ==================== 基础入门 ====================
    {
        'category': '基础入门',
        'examples': [
            {
                'id': 'hello',
                'title': '你好，光明',
                'description': '最基础的光明程序，了解打印语句',
                'code': '# 欢迎使用光明 v3.2\n\n打印("你好，光明！")\n打印("欢迎来到中文编程的世界")'
            },
            {
                'id': 'variables',
                'title': '变量与赋值',
                'description': '变量声明、赋值和基本算术运算',
                'code': '# 变量声明\n设 甲 为 10\n设 乙 为 20\n设 丙 为 真\n\n打印("甲 = ")打印(甲)\n打印("乙 = ")打印(乙)\n打印("甲 + 乙 = ")打印(甲 加 乙)\n打印("甲 × 乙 = ")打印(甲 乘 乙)\n\n# 条件判断\n如果 甲 大于 乙：\n  打印("甲更大")\n否则：\n  打印("乙更大")'
            },
            {
                'id': 'operators',
                'title': '算术与比较',
                'description': '加减乘除模幂、大于小于等于不等于',
                'code': '# 算术运算\n设 a 为 15\n设 b 为 4\n\n打印("a = ")打印(a)\n打印("b = ")打印(b)\n\n打印("加法：")打印(a 加 b)\n打印("减法：")打印(a 减 b)\n打印("乘法：")打印(a 乘 b)\n打印("除法：")打印(a 除 b)\n打印("取模：")打印(a 模 b)\n打印("幂运算：")打印(2 幂 10)\n\n# 比较运算\n打印("a > b ？")打印(a 大于 b)\n打印("a == b ？")打印(a 等于 b)\n打印("a != b ？")打印(a 不等于 b)'
            },
            {
                'id': 'types',
                'title': '数据类型',
                'description': '数字、字符串、布尔值和列表的使用',
                'code': '# 数字\n设 整数 为 42\n设 小数 为 3.14\n打印("整数：")打印(整数)\n打印("小数：")打印(小数)\n\n# 字符串\n设 文本 为 "光明编程"\n打印("文本：")打印(文本)\n\n# 布尔值\n设 旗标 为 真\n打印("真值：")打印(旗标)\n\n# 列表\n设 列 为 [1, 2, 3, 4, 5]\n打印("列表：")打印(列)\n打印("长度：")打印(len(列))\n打印("首元素：")打印(列[0])\n打印("末元素：")打印(列[4])'
            },
            {
                'id': 'strings',
                'title': '字符串操作',
                'description': '字符串拼接、索引、长度和比较',
                'code': '# 字符串拼接\n设 姓 为 "张"\n设 名 为 "三"\n设 全名 为 姓 加 名\n打印("全名：")打印(全名)\n\n# 字符串索引\n设 词语 为 "光明编程语言"\n打印("第一个字：")打印(词语[0])\n打印("第二个字：")打印(词语[1])\n\n# 字符串长度\n打印("词语长度：")打印(len(词语))\n\n# 字符串比较\n如果 词语 等于 "光明编程语言"：\n  打印("匹配成功！")'
            },
            {
                'id': 'io_demo',
                'title': '输出格式化',
                'description': '模拟输入输出和格式化成绩单',
                'code': '# 模拟用户输入\n设 用户名 为 "小明"\n设 分数 为 95\n\n打印("请输入姓名：")打印(用户名)\n打印("请输入分数：")打印(分数)\n\n# 格式化输出\n打印("========== 成绩单 ==========")\n打印("姓名：")打印(用户名)\n打印("分数：")打印(分数)\n\n如果 分数 大于等于 90：\n  打印("等级：优秀")\n否则如果 分数 大于等于 60：\n  打印("等级：及格")\n否则：\n  打印("等级：不及格")'
            },
        ]
    },
    # ==================== 控制流程 ====================
    {
        'category': '控制流程',
        'examples': [
            {
                'id': 'controlflow',
                'title': '条件与循环',
                'description': '如果/否则如果/否则、遍历循环、当循环',
                'code': '# 条件判断\n设 分数 为 85\n\n如果 分数 大于等于 90：\n  打印("优秀")\n否则如果 分数 大于等于 80：\n  打印("良好")\n否则如果 分数 大于等于 60：\n  打印("及格")\n否则：\n  打印("不及格")\n\n# 遍历循环\n设 列表 为 [10, 20, 30]\n遍历 项 于 列表：\n  打印(项)\n\n# 当循环\n设 计数 为 3\n当 计数 大于 0：\n  打印(计数)\n  设 计数 为 计数 减 1'
            },
            {
                'id': 'while_demo',
                'title': '当循环详解',
                'description': '正序计数、倒计时、累加求和',
                'code': '# 当循环 - 计数\n设 i 为 1\n打印("正序计数：")\n当 i 小于等于 5：\n  打印(i)\n  设 i 为 i 加 1\n\n# 当循环 - 倒计时\n设 j 为 5\n打印("倒计时：")\n当 j 大于 0：\n  打印(j)\n  设 j 为 j 减 1\n打印("发射！")\n\n# 当循环 - 累加\n设 总和 为 0\n设 k 为 1\n当 k 小于等于 100：\n  设 总和 为 总和 加 k\n  设 k 为 k 加 1\n打印("1到100的和：")打印(总和)'
            },
            {
                'id': 'foreach_demo',
                'title': '遍历循环详解',
                'description': '遍历列表元素、遍历求和求平均',
                'code': '# 遍历列表\n设 水果 为 ["苹果", "香蕉", "橘子", "葡萄", "西瓜"]\n打印("水果列表：")\n遍历 果 于 水果：\n  打印("  - ")打印(果)\n\n# 遍历数字列表\n设 数字 为 [10, 20, 30, 40, 50]\n设 总和 为 0\n遍历 n 于 数字：\n  设 总和 为 总和 加 n\n打印("总和：")打印(总和)\n打印("平均值：")打印(总和 除 len(数字))'
            },
            {
                'id': 'multiplication',
                'title': '九九乘法表',
                'description': '嵌套循环打印经典乘法表',
                'code': '# 九九乘法表\n\n设 i 为 1\n当 i 小于等于 9：\n  设 j 为 1\n  当 j 小于等于 i：\n    打印(j)打印("×")打印(i)打印("=")打印(i 乘 j)打印("  ")\n    设 j 为 j 加 1\n  打印("")\n  设 i 为 i 加 1'
            },
            {
                'id': 'pattern',
                'title': '打印图案',
                'description': '用嵌套循环打印正三角和倒三角',
                'code': '# 打印三角形\n设 n 为 5\n设 i 为 1\n当 i 小于等于 n：\n  设 行 为 ""\n  设 j 为 1\n  当 j 小于等于 i：\n    设 行 为 行 加 "*"\n    设 j 为 j 加 1\n  打印(行)\n  设 i 为 i 加 1\n\n# 打印倒三角形\n打印("")\n设 k 为 n\n当 k 大于 0：\n  设 行 为 ""\n  设 j 为 1\n  当 j 小于等于 k：\n    设 行 为 行 加 "*"\n    设 j 为 j 加 1\n  打印(行)\n  设 k 为 k 减 1'
            },
        ]
    },
    # ==================== 函数与递归 ====================
    {
        'category': '函数与递归',
        'examples': [
            {
                'id': 'function',
                'title': '段落定义',
                'description': '段落（函数）的定义、参数和返回值',
                'code': '# 定义和调用\n段落 平方 接收 数值：\n  返回 数值 乘 数值\n\n段落 双倍 接收 数值：\n  返回 数值 乘 2\n\n段落 阶乘 接收 数值：\n  如果 数值 小于等于 1：\n    返回 1\n  返回 数值 乘 阶乘(数值 减 1)\n\n# 调用\n打印("5 的平方：")打印(平方(5))\n打印("双倍 21：")打印(双倍(21))\n打印("6 的阶乘：")打印(阶乘(6))'
            },
            {
                'id': 'multi_param',
                'title': '多参数函数',
                'description': '多参数段落、求最大值、判断奇偶',
                'code': '# 多参数\n段落 求最大值 接收 a, b, c：\n  设 最大 为 a\n  如果 b 大于 最大：\n    设 最大 为 b\n  如果 c 大于 最大：\n    设 最大 为 c\n  返回 最大\n\n打印("最大(3,7,5)：")打印(求最大值(3, 7, 5))\n打印("最大(10,2,8)：")打印(求最大值(10, 2, 8))\n\n# 计算面积\n段落 矩形面积 接收 宽, 高：\n  返回 宽 乘 高\n\n打印("矩形 5×3 面积：")打印(矩形面积(5, 3))\n\n# 判断奇偶\n段落 是偶数 接收 数：\n  如果 数 模 2 等于 0：\n    返回 真\n  返回 假\n\n打印("8 是偶数？")打印(是偶数(8))\n打印("7 是偶数？")打印(是偶数(7))'
            },
            {
                'id': 'scope',
                'title': '变量作用域',
                'description': '全局变量和局部变量的区别',
                'code': '# 全局变量\n设 全局值 为 100\n打印("全局值：")打印(全局值)\n\n段落 测试作用域 接收 x：\n  设 局部值 为 x 乘 2\n  打印("局部值：")打印(局部值)\n  打印("全局值在内部可见：")打印(全局值)\n  返回 局部值 加 全局值\n\n设 结果 为 测试作用域(3)\n打印("结果：")打印(结果)\n打印("全局值未变：")打印(全局值)'
            },
            {
                'id': 'fibonacci',
                'title': '斐波那契数列',
                'description': '递归计算斐波那契数列前10项',
                'code': '# 递归斐波那契\n段落 斐波那契 接收 n：\n  如果 n 小于等于 1：\n    返回 n\n  返回 斐波那契(n 减 1) 加 斐波那契(n 减 2)\n\n# 输出前 10 项\n设 i 为 0\n当 i 小于 10：\n  打印(斐波那契(i))\n  设 i 为 i 加 1'
            },
            {
                'id': 'hanoi',
                'title': '汉诺塔问题',
                'description': '经典递归问题——汉诺塔3层移动',
                'code': '# 汉诺塔递归\n段落 汉诺塔 接收 n, 起点, 终点, 辅助：\n  如果 n 等于 1：\n    打印(起点)打印(" -> ")打印(终点)\n    返回 0\n  汉诺塔(n 减 1, 起点, 辅助, 终点)\n  打印(起点)打印(" -> ")打印(终点)\n  汉诺塔(n 减 1, 辅助, 终点, 起点)\n  返回 0\n\n打印("汉诺塔 3 层移动步骤：")\n汉诺塔(3, "A", "C", "B")'
            },
        ]
    },
    # ==================== 数据结构 ====================
    {
        'category': '数据结构',
        'examples': [
            {
                'id': 'list_basic',
                'title': '列表基本操作',
                'description': '创建、访问、追加元素和获取长度',
                'code': '# 创建列表\n设 空列 为 []\n设 数列 为 [1, 2, 3, 4, 5]\n\n打印("空列表：")打印(空列)\n打印("数字列表：")打印(数列)\n\n# 访问元素\n打印("第一个：")打印(数列[0])\n打印("第三个：")打印(数列[2])\n\n# 追加元素\n设 数列 为 数列 加 [6]\n设 数列 为 数列 加 [7]\n打印("追加后：")打印(数列)\n\n# 列表长度\n打印("长度：")打印(len(数列))'
            },
            {
                'id': 'list_search',
                'title': '列表查找',
                'description': '线性查找元素位置和统计出现次数',
                'code': '# 线性查找\n段落 查找 接收 列表, 目标：\n  设 i 为 0\n  当 i 小于 len(列表)：\n    如果 列表[i] 等于 目标：\n      返回 i\n    设 i 为 i 加 1\n  返回 -1\n\n设 数据 为 [8, 3, 5, 1, 9, 2, 7]\n\n打印("列表：")打印(数据)\n打印("查找 5：")打印(查找(数据, 5))\n打印("查找 10：")打印(查找(数据, 10))\n\n# 统计\n段落 计数 接收 列表, 目标：\n  设 次数 为 0\n  遍历 项 于 列表：\n    如果 项 等于 目标：\n      设 次数 为 次数 加 1\n  返回 次数\n\n设 数据2 为 [1, 2, 1, 3, 1, 4]\n打印("1 出现次数：")打印(计数(数据2, 1))'
            },
            {
                'id': 'selection_sort',
                'title': '选择排序',
                'description': '每次选出最小元素，构建有序列表',
                'code': '# 选择排序\n段落 选择排序 接收 列表：\n  设 n 为 len(列表)\n  设 结果 为 []\n  设 源列 为 列表\n  设 i 为 0\n  当 i 小于 n：\n    设 最小 为 源列[0]\n    设 最小位 为 0\n    设 j 为 1\n    当 j 小于 len(源列)：\n      如果 源列[j] 小于 最小：\n        设 最小 为 源列[j]\n        设 最小位 为 j\n      设 j 为 j 加 1\n    设 结果 为 结果 加 [最小]\n    设 新源列 为 []\n    设 k 为 0\n    当 k 小于 len(源列)：\n      如果 k 不等于 最小位：\n        设 新源列 为 新源列 加 [源列[k]]\n      设 k 为 k 加 1\n    设 源列 为 新源列\n    设 i 为 i 加 1\n  返回 结果\n\n设 数据 为 [64, 34, 25, 12, 22, 11, 90]\n打印("排序前：")打印(数据)\n打印("排序后：")打印(选择排序(数据))'
            },
            {
                'id': 'quicksort',
                'title': '快速排序',
                'description': '经典的分治排序算法',
                'code': '# 快速排序\n段落 快排 接收 列表：\n  如果 len(列表) 小于等于 1：\n    返回 列表\n  设 基准 为 列表[0]\n  设 左列 为 []\n  设 右列 为 []\n  设 i 为 1\n  当 i 小于 len(列表)：\n    如果 列表[i] 小于 基准：\n      设 左列 为 左列 加 [列表[i]]\n    否则：\n      设 右列 为 右列 加 [列表[i]]\n    设 i 为 i 加 1\n  返回 快排(左列) 加 [基准] 加 快排(右列)\n\n设 数据 为 [5, 3, 8, 1, 9, 2, 7, 4, 6]\n打印("排序前：")打印(数据)\n打印("排序后：")打印(快排(数据))'
            },
            {
                'id': 'palindrome',
                'title': '回文判断',
                'description': '字符串反转和回文检测',
                'code': '# 回文判断\n段落 反转字符串 接收 文本：\n  设 结果 为 ""\n  设 i 为 len(文本) 减 1\n  当 i 大于等于 0：\n    设 结果 为 结果 加 文本[i]\n    设 i 为 i 减 1\n  返回 结果\n\n段落 是回文 接收 文本：\n  设 反转 为 反转字符串(文本)\n  如果 文本 等于 反转：\n    返回 真\n  返回 假\n\n设 词1 为 "上海自来水来自海上"\n设 词2 为 "光明编程语言"\n\n打印(词1)打印(" 是回文？")打印(是回文(词1))\n打印(词2)打印(" 是回文？")打印(是回文(词2))'
            },
        ]
    },
    # ==================== 面向对象 ====================
    {
        'category': '面向对象',
        'examples': [
            {
                'id': 'class_basic',
                'title': '类与对象',
                'description': '类定义、构造函数、创建对象',
                'code': '# 类定义\n类 人：\n  属性 姓名\n  属性 年龄\n\n  构造 接收 姓名, 年龄：\n    己姓名 为 姓名\n    己年龄 为 年龄\n\n  段落 自我介绍：\n    打印("我叫")打印(己姓名)打印("，今年")打印(己年龄)打印("岁")\n\n设 张三 为 新建 人("张三", 18)\n张三.自我介绍()\n\n设 李四 为 新建 人("李四", 20)\n李四.自我介绍()'
            },
            {
                'id': 'class_method',
                'title': '类的方法',
                'description': '计数器类：增加、减少、重置、获取值',
                'code': '# 计算器类\n类 计数器：\n  属性 值\n\n  构造 接收 初始值：\n    己值 为 初始值\n\n  段落 增加 接收 量：\n    己值 为 己值 加 量\n    返回 己值\n\n  段落 减少 接收 量：\n    己值 为 己值 减 量\n    返回 己值\n\n  段落 重置：\n    己值 为 0\n    返回 己值\n\n  段落 获取值：\n    返回 己值\n\n# 使用计数器\n设 计数 为 新建 计数器(0)\n打印("初始：")打印(计数.获取值())\n\n计数.增加(5)\n打印("加5后：")打印(计数.获取值())\n\n计数.增加(3)\n打印("再加3：")打印(计数.获取值())\n\n计数.减少(2)\n打印("减2后：")打印(计数.获取值())\n\n计数.重置()\n打印("重置后：")打印(计数.获取值())'
            },
            {
                'id': 'class_inherit',
                'title': '继承与多态',
                'description': '类继承、方法重写、多态演示',
                'code': '# 基类\n类 动物：\n  属性 名称\n\n  构造 接收 名称：\n    己名称 为 名称\n\n  段落 发出声音：\n    打印("动物发出声音...")\n\n# 子类继承\n类 狗 继承 动物：\n  属性 品种\n\n  构造 接收 名称, 品种：\n    父.构造(名称)\n    己品种 为 品种\n\n  段落 发出声音：\n    打印(己名称)打印("：汪汪汪！")\n\n类 猫 继承 动物：\n  构造 接收 名称：\n    父.构造(名称)\n\n  段落 发出声音：\n    打印(己名称)打印("：喵喵喵~")\n\n# 多态演示\n设 旺财 为 新建 狗("旺财", "金毛")\n设 咪咪 为 新建 猫("咪咪")\n\n旺财.发出声音()\n咪咪.发出声音()'
            },
        ]
    },
    # ==================== 算法实战 ====================
    {
        'category': '算法实战',
        'examples': [
            {
                'id': 'insertion_sort',
                'title': '插入排序',
                'description': '逐个将元素插入到已排序序列中',
                'code': '# 插入排序\n段落 插入排序 接收 列表：\n  设 结果 为 [列表[0]]\n  设 i 为 1\n  当 i 小于 len(列表)：\n    设 当前 为 列表[i]\n    设 新列 为 []\n    设 已插入 为 假\n    设 j 为 0\n    当 j 小于 len(结果)：\n      如果 已插入 等于 假 且 当前 小于 结果[j]：\n        设 新列 为 新列 加 [当前]\n        设 已插入 为 真\n      设 新列 为 新列 加 [结果[j]]\n      设 j 为 j 加 1\n    如果 已插入 等于 假：\n      设 新列 为 新列 加 [当前]\n    设 结果 为 新列\n    设 i 为 i 加 1\n  返回 结果\n\n设 数据 为 [5, 2, 4, 6, 1, 3]\n打印("排序前：")打印(数据)\n打印("排序后：")打印(插入排序(数据))'
            },
            {
                'id': 'gcd_lcm',
                'title': '最大公约数与最小公倍数',
                'description': '辗转相除法求 GCD，以及 LCM',
                'code': '# 最大公约数（辗转相除法）\n段落 最大公约数 接收 a, b：\n  当 b 不等于 0：\n    设 余 为 a 模 b\n    设 a 为 b\n    设 b 为 余\n  返回 a\n\n# 最小公倍数\n段落 最小公倍数 接收 a, b：\n  返回 (a 乘 b) 除 最大公约数(a, b)\n\n打印("gcd(12, 18)：")打印(最大公约数(12, 18))\n打印("gcd(48, 36)：")打印(最大公约数(48, 36))\n打印("lcm(12, 18)：")打印(最小公倍数(12, 18))\n打印("lcm(7, 13)：")打印(最小公倍数(7, 13))'
            },
            {
                'id': 'prime',
                'title': '素数筛选',
                'description': '判断素数并输出100以内的所有素数',
                'code': '# 判断素数\n段落 是素数 接收 数：\n  如果 数 小于 2：\n    返回 假\n  设 i 为 2\n  当 i 乘 i 小于等于 数：\n    如果 数 模 i 等于 0：\n      返回 假\n    设 i 为 i 加 1\n  返回 真\n\n# 输出 100 以内素数\n打印("100 以内的素数：")\n设 n 为 2\n当 n 小于 100：\n  如果 是素数(n)：\n    打印(n)\n  设 n 为 n 加 1'
            },
            {
                'id': 'yanghui',
                'title': '杨辉三角',
                'description': '生成杨辉三角（帕斯卡三角）前6行',
                'code': '# 杨辉三角\n段落 生成杨辉三角 接收 行数：\n  设 结果 为 [[1]]\n  设 i 为 1\n  当 i 小于 行数：\n    设 上行 为 结果[i 减 1]\n    设 当前行 为 [1]\n    设 j 为 1\n    当 j 小于 i：\n      设 当前行 为 当前行 加 [上行[j 减 1] 加 上行[j]]\n      设 j 为 j 加 1\n    设 当前行 为 当前行 加 [1]\n    设 结果 为 结果 加 [当前行]\n    设 i 为 i 加 1\n  返回 结果\n\n打印("杨辉三角前 6 行：")\n设 三角 为 生成杨辉三角(6)\n遍历 行 于 三角：\n  打印(行)'
            },
        ]
    },
    # ==================== 项目实战 ====================
    {
        'category': '项目实战',
        'examples': [
            {
                'id': 'guess_number',
                'title': '猜数字游戏',
                'description': '模拟猜数字过程，学习条件判断',
                'code': '# 猜数字游戏\n打印("=== 猜数字游戏 ===")\n打印("我心里想了一个 1-10 之间的数字")\n\n设 答案 为 7\n设 猜测 为 5\n设 尝试次数 为 0\n\n打印("第1次猜：")打印(猜测)\n设 尝试次数 为 尝试次数 加 1\n\n如果 猜测 大于 答案：\n  打印("太大了！")\n否则如果 猜测 小于 答案：\n  打印("太小了！")\n\n设 猜测 为 8\n打印("第2次猜：")打印(猜测)\n设 尝试次数 为 尝试次数 加 1\n\n如果 猜测 大于 答案：\n  打印("太大了！")\n否则如果 猜测 小于 答案：\n  打印("太小了！")\n\n设 猜测 为 7\n打印("第3次猜：")打印(猜测)\n设 尝试次数 为 尝试次数 加 1\n\n如果 猜测 等于 答案：\n  打印("恭喜你猜对了！")\n  打印("你用了 ")打印(尝试次数)打印(" 次")'
            },
            {
                'id': 'calculator',
                'title': '简易计算器',
                'description': '用段落实现加减乘除四则运算',
                'code': '# 简易计算器\n打印("=== 简易计算器 ===")\n\n段落 计算 接收 a, 运算符, b：\n  如果 运算符 等于 "加"：\n    返回 a 加 b\n  如果 运算符 等于 "减"：\n    返回 a 减 b\n  如果 运算符 等于 "乘"：\n    返回 a 乘 b\n  如果 运算符 等于 "除"：\n    返回 a 除 b\n  返回 0\n\n打印("10 + 5 = ")打印(计算(10, "加", 5))\n打印("10 - 5 = ")打印(计算(10, "减", 5))\n打印("10 × 5 = ")打印(计算(10, "乘", 5))\n打印("10 ÷ 5 = ")打印(计算(10, "除", 5))\n\n# 连续计算\n设 结果 为 计算(3, "加", 4)\n设 结果 为 计算(结果, "乘", 2)\n设 结果 为 计算(结果, "减", 3)\n打印("3 + 4 × 2 - 3 = ")打印(结果)'
            },
            {
                'id': 'grade_manage',
                'title': '成绩管理',
                'description': '打印成绩单，计算平均分/最高分/最低分',
                'code': '# 成绩管理系统\n打印("=== 成绩管理系统 ===")\n\n# 成绩数据\n设 姓名列 为 ["张三", "李四", "王五", "赵六"]\n设 成绩列 为 [85, 92, 78, 66]\n\n# 打印成绩单\n打印("学号  姓名  成绩  等级")\n打印("--------------------")\n设 i 为 0\n当 i 小于 len(姓名列)：\n  设 姓名 为 姓名列[i]\n  设 成绩 为 成绩列[i]\n  \n  设 等级 为 ""\n  如果 成绩 大于等于 90：\n    设 等级 为 "A"\n  否则如果 成绩 大于等于 80：\n    设 等级 为 "B"\n  否则如果 成绩 大于等于 70：\n    设 等级 为 "C"\n  否则如果 成绩 大于等于 60：\n    设 等级 为 "D"\n  否则：\n    设 等级 为 "F"\n  \n  打印(i 加 1)打印("    ")打印(姓名)打印("  ")打印(成绩)打印("  ")打印(等级)\n  设 i 为 i 加 1\n\n# 统计\n设 总和 为 0\n设 最高 为 成绩列[0]\n设 最低 为 成绩列[0]\n设 j 为 0\n当 j 小于 len(成绩列)：\n  设 总和 为 总和 加 成绩列[j]\n  如果 成绩列[j] 大于 最高：\n    设 最高 为 成绩列[j]\n  如果 成绩列[j] 小于 最低：\n    设 最低 为 成绩列[j]\n  设 j 为 j 加 1\n\n打印("--------------------")\n打印("平均分：")打印(总和 除 len(成绩列))\n打印("最高分：")打印(最高)\n打印("最低分：")打印(最低)'
            },
            {
                'id': 'count_words',
                'title': '词频统计',
                'description': '统计列表中每个词语出现的次数',
                'code': '# 词频统计\n打印("=== 词频统计 ===")\n\n# 分词\n设 词列 为 ["苹果", "香蕉", "苹果", "橘子", "香蕉", "苹果", "西瓜", "橘子", "香蕉", "苹果"]\n\n# 去重\n设 唯词列 为 []\n遍历 词 于 词列：\n  设 已存在 为 假\n  遍历 唯词 于 唯词列：\n    如果 唯词 等于 词：\n      设 已存在 为 真\n  如果 已存在 等于 假：\n    设 唯词列 为 唯词列 加 [词]\n\n# 统计\n打印("词语  次数")\n打印("----------")\n遍历 唯词 于 唯词列：\n  设 次数 为 0\n  遍历 词 于 词列：\n    如果 词 等于 唯词：\n      设 次数 为 次数 加 1\n  打印(唯词)打印("  ")打印(次数)'
            },
        ]
    },
]

ALL_EXAMPLES_FLAT = []
for cat in BUILTIN_EXAMPLES:
    for ex in cat['examples']:
        ALL_EXAMPLES_FLAT.append(ex)


GRAMMAR_REFERENCE = [
    {
        'category': '注释',
        'items': [
            {'syntax': '# 注释内容', 'description': '单行注释，以 # 开头'}
        ]
    },
    {
        'category': '变量定义',
        'items': [
            {'syntax': '设 变量名 为 值', 'description': '定义变量并初始化'},
            {'syntax': '设 甲 为 10', 'description': '示例：定义整数变量'},
            {'syntax': '变量名 为 新值', 'description': '修改变量值（省略设）'}
        ]
    },
    {
        'category': '数据类型',
        'items': [
            {'syntax': '42 / 3.14', 'description': '整数和浮点数'},
            {'syntax': '"文本内容"', 'description': '字符串，用双引号包围'},
            {'syntax': '真 / 假', 'description': '布尔值'},
            {'syntax': '空', 'description': '空值'},
            {'syntax': '[1, 2, 3]', 'description': '列表'},
            {'syntax': '{"键": 值, "键2": 值2}', 'description': '字典'}
        ]
    },
    {
        'category': '运算符',
        'items': [
            {'syntax': '加 / 减 / 乘 / 除 / 模 / 幂', 'description': '算术运算符'},
            {'syntax': '大于 / 小于 / 等于 / 不等于', 'description': '比较运算符'},
            {'syntax': '且 / 或 / 非', 'description': '逻辑运算符'}
        ]
    },
    {
        'category': '条件判断',
        'items': [
            {'syntax': '如果 条件：\n  代码', 'description': '基本条件判断'},
            {'syntax': '如果 条件：\n  代码\n否则：\n  代码', 'description': '条件判断带否则分支'},
            {'syntax': '如果 条件：\n  代码\n否则如果 条件：\n  代码\n否则：\n  代码', 'description': '多条件判断链'}
        ]
    },
    {
        'category': '循环',
        'items': [
            {'syntax': '当 条件：\n  代码', 'description': '当循环，条件为真时重复执行'},
            {'syntax': '遍历 项 于 列表：\n  代码', 'description': '遍历列表每个元素'},
            {'syntax': '跳出', 'description': '跳出当前循环'},
            {'syntax': '跳过', 'description': '跳过当前迭代'}
        ]
    },
    {
        'category': '段落（函数）',
        'items': [
            {'syntax': '段落 名称 接收 参数：\n  代码', 'description': '定义段落（函数）'},
            {'syntax': '名称(参数)', 'description': '调用段落'},
            {'syntax': '返回 值', 'description': '从段落返回值'}
        ]
    },
    {
        'category': '类与对象',
        'items': [
            {'syntax': '类 类名：\n  属性 属性名\n  构造 接收 参数：\n    代码\n  段落 方法名：\n    代码', 'description': '类定义'},
            {'syntax': '新建 类名(参数)', 'description': '创建对象实例'},
            {'syntax': '己.属性名 / 己方法名()', 'description': '访问自身属性和方法'},
            {'syntax': '类 子类 继承 父类：', 'description': '类继承'}
        ]
    },
    {
        'category': '内置函数',
        'items': [
            {'syntax': '打印(值)', 'description': '输出值到控制台'},
            {'syntax': '列表之长度', 'description': '获取列表/字符串长度'},
            {'syntax': '转整数(值)', 'description': '转换为整数'},
            {'syntax': '转字符串(值)', 'description': '转换为字符串'}
        ]
    }
]

STDLIB_REFERENCE = [
    {
        'category': '常用模块',
        'items': [
            {'name': '数学', 'desc': '数学运算函数（sin, cos, sqrt, 对数等）'},
            {'name': '字符串处理', 'desc': '字符串操作（分割、替换、大小写等）'},
            {'name': '列表工具', 'desc': '列表操作工具（映射、过滤、归约等）'},
            {'name': '日期时间', 'desc': '日期和时间处理'},
            {'name': 'JSON', 'desc': 'JSON 解析与生成'},
            {'name': '正则', 'desc': '正则表达式匹配'},
            {'name': '文件系统', 'desc': '文件读写与目录操作'},
            {'name': '随机', 'desc': '随机数生成'}
        ]
    }
]


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/grammar', methods=['GET'])
def get_grammar():
    return jsonify({'categories': GRAMMAR_REFERENCE})


@app.route('/api/stdlib', methods=['GET'])
def get_stdlib():
    return jsonify({'categories': STDLIB_REFERENCE})


@app.route('/api/execute', methods=['POST'])
def execute():
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    result = run_light_code(code)
    return jsonify(result)


@app.route('/api/examples', methods=['GET'])
def get_examples():
    return jsonify({'categories': BUILTIN_EXAMPLES, 'examples': ALL_EXAMPLES_FLAT})


@app.route('/api/examples/<example_id>', methods=['GET'])
def get_example(example_id):
    for ex in ALL_EXAMPLES_FLAT:
        if ex['id'] == example_id:
            return jsonify(ex)
    return jsonify({'error': '示例未找到'}), 404


@app.route('/api/parse', methods=['POST'])
def parse_code():
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    result = parse_light_code(code)
    return jsonify(result)


@app.route('/api/tokenize', methods=['POST'])
def tokenize_code():
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    result = tokenize_light_code(code)
    return jsonify(result)


@app.route('/api/llvm', methods=['POST'])
def llvm_ir():
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    result = generate_llvm_ir(code)
    return jsonify(result)


# ==================== 项目管理 API（多文件项目） ====================

import shutil


def _get_project_dir(name: str) -> str:
    """获取项目目录路径"""
    safe_name = name.replace('/', '_').replace('\\', '_').replace('..', '_')
    return os.path.join(PROJECTS_DIR, safe_name)


def _list_project_files(proj_dir: str) -> list:
    """列出项目目录下所有 .light 文件"""
    files = []
    if os.path.isdir(proj_dir):
        for fname in sorted(os.listdir(proj_dir)):
            if fname.endswith('.light'):
                fpath = os.path.join(proj_dir, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    files.append({
                        'name': fname,
                        'path': fname,
                        'content': content,
                        'size': len(content),
                        'updated_at': int(mtime)
                    })
                except Exception:
                    pass
    return files


def _get_entry_file(proj_dir: str) -> str:
    """获取项目入口文件（主.light 或第一个 .light）"""
    if os.path.isdir(proj_dir):
        main_path = os.path.join(proj_dir, '主.light')
        if os.path.exists(main_path):
            return '主.light'
        for fname in sorted(os.listdir(proj_dir)):
            if fname.endswith('.light'):
                return fname
    return ''


def _run_project_code(proj_dir: str, entry_file: str) -> dict:
    """执行多文件项目：编译所有模块并运行入口"""
    try:
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator

        # 收集所有 .light 文件
        all_files = _list_project_files(proj_dir)
        if not all_files:
            return {'success': False, 'error': '项目中没有 .light 文件', 'output': ''}

        # 编译所有模块
        parser = LightParser()
        generator = PythonCodeGenerator()
        compiled_modules = {}

        for finfo in all_files:
            try:
                module = parser.parse(finfo['content'])
                py_code = generator.generate(module)
                mod_name = finfo['name'].replace('.light', '')
                compiled_modules[mod_name] = py_code
            except Exception as e:
                return {
                    'success': False,
                    'error': f'编译 {finfo["name"]} 失败: {e}',
                    'output': ''
                }

        # 执行入口模块
        entry_mod = entry_file.replace('.light', '') if entry_file else list(compiled_modules.keys())[0]
        if entry_mod not in compiled_modules:
            return {'success': False, 'error': f'入口模块 {entry_mod} 未找到', 'output': ''}

        output_lines = []

        def _capture_print(*args, **kwargs):
            line = ' '.join(str(a) for a in args)
            output_lines.append(line)

        # 构建命名空间：先执行所有非入口模块，再执行入口模块
        namespace = {
            'print': _capture_print,
            '__name__': '__main__',
            '__file__': os.path.join(proj_dir, entry_file)
        }

        start_time = time.time()

        # 先加载非入口模块到命名空间
        for mod_name, py_code in compiled_modules.items():
            if mod_name != entry_mod:
                try:
                    mod_ns = {}
                    exec(py_code, mod_ns)
                    namespace[mod_name] = type('Module', (), mod_ns)()
                    for k, v in mod_ns.items():
                        if not k.startswith('_'):
                            setattr(namespace[mod_name], k, v)
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'加载模块 {mod_name} 失败: {e}',
                        'output': ''
                    }

        # 执行入口模块
        try:
            exec(compiled_modules[entry_mod], namespace)
        except Exception as e:
            tb = traceback.format_exc()
            return {
                'success': False,
                'error': f'运行时错误: {type(e).__name__}: {e}',
                'traceback': tb,
                'output': '\n'.join(output_lines) if output_lines else ''
            }

        exec_time = (time.time() - start_time) * 1000

        return {
            'success': True,
            'output': '\n'.join(output_lines) if output_lines else '(无输出)',
            'execution_time': round(exec_time, 2)
        }

    except Exception as e:
        tb = traceback.format_exc()
        return {
            'success': False,
            'error': f'项目执行错误: {type(e).__name__}: {e}',
            'traceback': tb,
            'output': ''
        }


@app.route('/api/projects', methods=['GET'])
def list_projects():
    """列出所有已保存的项目"""
    projects = []
    if os.path.isdir(PROJECTS_DIR):
        for dname in sorted(os.listdir(PROJECTS_DIR)):
            dpath = os.path.join(PROJECTS_DIR, dname)
            if os.path.isdir(dpath):
                mtime = int(os.path.getmtime(dpath))
                file_count = sum(1 for f in os.listdir(dpath) if f.endswith('.light'))
                projects.append({
                    'name': dname,
                    'updated_at': mtime,
                    'file_count': file_count
                })
    return jsonify({'projects': projects})


@app.route('/api/projects/<name>', methods=['GET'])
def load_project(name):
    """加载指定项目（返回所有文件）"""
    proj_dir = _get_project_dir(name)
    if not os.path.isdir(proj_dir):
        return jsonify({'error': '项目未找到'}), 404
    files = _list_project_files(proj_dir)
    entry = _get_entry_file(proj_dir)
    return jsonify({
        'name': name,
        'files': files,
        'entry': entry,
        'updated_at': int(os.path.getmtime(proj_dir))
    })


@app.route('/api/projects/<name>', methods=['PUT'])
def save_project(name):
    """保存/创建项目（接收所有文件）"""
    data = request.get_json(silent=True) or {}
    files = data.get('files', [])
    proj_dir = _get_project_dir(name)
    os.makedirs(proj_dir, exist_ok=True)

    for finfo in files:
        fname = finfo.get('name', '')
        if not fname.endswith('.light'):
            fname += '.light'
        safe_fname = fname.replace('/', '_').replace('\\', '_')
        fpath = os.path.join(proj_dir, safe_fname)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(finfo.get('content', ''))

    return jsonify({'success': True, 'name': name})


@app.route('/api/projects/<name>', methods=['DELETE'])
def delete_project(name):
    """删除项目"""
    proj_dir = _get_project_dir(name)
    if os.path.isdir(proj_dir):
        shutil.rmtree(proj_dir)
        return jsonify({'success': True})
    return jsonify({'error': '项目未找到'}), 404


@app.route('/api/projects/<name>/files/<path:filepath>', methods=['GET'])
def get_project_file(name, filepath):
    """读取项目中的单个文件"""
    proj_dir = _get_project_dir(name)
    fpath = os.path.join(proj_dir, filepath)
    if not os.path.exists(fpath):
        return jsonify({'error': '文件未找到'}), 404
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    return jsonify({'name': filepath, 'content': content})


@app.route('/api/projects/<name>/files/<path:filepath>', methods=['PUT'])
def save_project_file(name, filepath):
    """保存项目中的单个文件"""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    proj_dir = _get_project_dir(name)
    os.makedirs(proj_dir, exist_ok=True)
    safe_path = filepath.replace('/', '_').replace('\\', '_')
    fpath = os.path.join(proj_dir, safe_path)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({'success': True, 'name': filepath})


@app.route('/api/projects/<name>/files', methods=['POST'])
def create_project_file(name):
    """在项目中创建新文件"""
    data = request.get_json(silent=True) or {}
    fname = data.get('name', '')
    content = data.get('content', '')
    if not fname:
        return jsonify({'error': '文件名不能为空'}), 400
    if not fname.endswith('.light'):
        fname += '.light'
    proj_dir = _get_project_dir(name)
    os.makedirs(proj_dir, exist_ok=True)
    safe_name = fname.replace('/', '_').replace('\\', '_')
    fpath = os.path.join(proj_dir, safe_name)
    if os.path.exists(fpath):
        return jsonify({'error': '文件已存在'}), 409
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({'success': True, 'name': fname})


@app.route('/api/projects/<name>/files/<path:filepath>', methods=['DELETE'])
def delete_project_file(name, filepath):
    """删除项目中的文件"""
    proj_dir = _get_project_dir(name)
    fpath = os.path.join(proj_dir, filepath)
    if os.path.exists(fpath):
        os.remove(fpath)
        return jsonify({'success': True})
    return jsonify({'error': '文件未找到'}), 404


@app.route('/api/projects/<name>/run', methods=['POST'])
def run_project(name):
    """运行项目"""
    proj_dir = _get_project_dir(name)
    if not os.path.isdir(proj_dir):
        return jsonify({'success': False, 'error': '项目未找到'})
    entry = _get_entry_file(proj_dir)
    if not entry:
        return jsonify({'success': False, 'error': '项目中没有 .light 文件'})
    result = _run_project_code(proj_dir, entry)
    return jsonify(result)


@app.route('/api/share', methods=['POST'])
def share_code():
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    content_hash = hashlib.md5(code.encode('utf-8')).hexdigest()[:8]
    timestamp = int(time.time())
    share_id = f"{content_hash}-{timestamp}"

    share_file = os.path.join(SHARED_DIR, f"{share_id}.json")
    if not os.path.exists(share_file):
        with open(share_file, 'w', encoding='utf-8') as f:
            json.dump({
                'id': share_id,
                'code': code,
                'created_at': timestamp
            }, f, ensure_ascii=False, indent=2)

    return jsonify({
        'success': True,
        'share_id': share_id,
        'share_url': f"/?share={share_id}"
    })


@app.route('/api/share/<share_id>', methods=['GET'])
def get_shared_code(share_id):
    share_file = os.path.join(SHARED_DIR, f"{share_id}.json")
    if not os.path.exists(share_file):
        return jsonify({'error': '分享内容未找到或已过期'}), 404

    with open(share_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return jsonify(data)


# ==================== 调试 API（Playground 调试器） ====================

import threading

_debug_sessions = {}
_debug_lock = threading.Lock()


def _get_debug_dir() -> str:
    """获取调试会话存储目录"""
    debug_dir = os.path.join(_script_dir, 'debug_sessions')
    os.makedirs(debug_dir, exist_ok=True)
    return debug_dir


class PlaygroundDebugSession:
    """Playground 调试会话"""

    def __init__(self, session_id: str, source: str):
        self.session_id = session_id
        self.source = source
        self.python_code = ''
        self.running = False
        self.paused = False
        self.stopped = False
        self.breakpoints = {}
        self.variables = {}
        self.call_stack = []
        self.current_line = 0
        self.output = []
        self.errors = []
        self._thread = None
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._step_mode = 'none'  # none, over, into, out
        self._debugger = None
        self._exec_namespace = {}
        self._compile_errors = []

    def compile(self):
        """编译源代码"""
        try:
            from light_parser_v3 import LightParser
            from code_generator import PythonCodeGenerator

            parser = LightParser()
            module = parser.parse(self.source)
            generator = PythonCodeGenerator()
            self.python_code = generator.generate(module)
            return True
        except Exception as e:
            self._compile_errors.append(str(e))
            return False

    def set_breakpoints(self, breakpoints: dict):
        """设置断点 {line: condition}"""
        self.breakpoints = breakpoints

    def _trace_func(self, frame, event, arg):
        """Python 跟踪函数"""
        if self.stopped:
            return None

        filename = frame.f_code.co_filename
        lineno = frame.f_lineno

        if event == 'line':
            # 检查是否应该在此行暂停
            should_pause = False

            if self._step_mode == 'into':
                should_pause = True
            elif self._step_mode == 'over':
                should_pause = True
            elif self._step_mode == 'out':
                should_pause = True

            if lineno in self.breakpoints:
                should_pause = True

            if should_pause:
                self.paused = True
                self.current_line = lineno
                self.variables = {k: v for k, v in frame.f_locals.items() if not k.startswith('_')}

                # 收集调用栈
                self.call_stack = []
                f = frame
                while f is not None:
                    self.call_stack.append({
                        'name': f.f_code.co_name,
                        'file': f.f_code.co_filename,
                        'line': f.f_lineno
                    })
                    f = f.f_back

                self._step_mode = 'none'
                self._pause_event.clear()
                self._pause_event.wait()

                if self.stopped:
                    return None

            if self._step_mode == 'none':
                pass

        elif event == 'call':
            if self._step_mode == 'into':
                self.paused = True
                self.current_line = frame.f_lineno
                self.variables = {k: v for k, v in frame.f_locals.items() if not k.startswith('_')}
                self._step_mode = 'none'
                self._pause_event.clear()
                self._pause_event.wait()

        elif event == 'return':
            if self._step_mode == 'out':
                self.paused = True
                self.current_line = frame.f_lineno
                self.variables = {k: v for k, v in frame.f_locals.items() if not k.startswith('_')}
                self._step_mode = 'none'
                self._pause_event.clear()
                self._pause_event.wait()

        return self._trace_func

    def _run_in_thread(self):
        """在线程中执行代码"""
        old_stdout = sys.stdout
        output_capture = io.StringIO()
        sys.stdout = output_capture

        try:
            import sys as _sys
            _sys.settrace(self._trace_func)

            compiled = compile(self.python_code, '<playground_debug>', 'exec')
            self._exec_namespace = {
                'print': lambda *a, **k: print(' '.join(str(x) for x in a), file=output_capture),
                '__name__': '__main__',
                '__file__': '<playground_debug>'
            }
            exec(compiled, self._exec_namespace)

            _sys.settrace(None)
        except Exception as e:
            self.errors.append(f'运行时错误: {type(e).__name__}: {e}')
            import traceback as tb
            self.errors.append(tb.format_exc())
        finally:
            sys.stdout = old_stdout
            self.output = output_capture.getvalue().split('\n')
            self.output = [l for l in self.output if l.strip()]
            self.stopped = True
            self.paused = False
            self.running = False

    def start(self):
        """启动调试会话"""
        if not self.compile():
            return False
        self.running = True
        self._thread = threading.Thread(target=self._run_in_thread, daemon=True)
        self._thread.start()
        return True

    def step_over(self):
        """单步跳过"""
        self._step_mode = 'over'
        self.paused = False
        self._pause_event.set()

    def step_into(self):
        """单步进入"""
        self._step_mode = 'into'
        self.paused = False
        self._pause_event.set()

    def step_out(self):
        """单步跳出"""
        self._step_mode = 'out'
        self.paused = False
        self._pause_event.set()

    def resume(self):
        """继续执行"""
        self._step_mode = 'none'
        self.paused = False
        self._pause_event.set()

    def stop(self):
        """停止调试"""
        self.stopped = True
        self.running = False
        self.paused = False
        self._pause_event.set()

    def get_state(self) -> dict:
        """获取当前调试状态"""
        # 提取源代码行
        source_lines = self.source.split('\n')
        current_source = ''
        if 1 <= self.current_line <= len(source_lines):
            current_source = source_lines[self.current_line - 1].strip()

        return {
            'session_id': self.session_id,
            'running': self.running,
            'paused': self.paused,
            'stopped': self.stopped,
            'current_line': self.current_line,
            'current_source': current_source,
            'variables': self._serialize_variables(),
            'call_stack': self.call_stack,
            'output': self.output[-50:] if self.output else [],
            'errors': self.errors,
            'compile_errors': self._compile_errors,
            'breakpoints': self.breakpoints,
            'total_lines': len(source_lines)
        }

    def _serialize_variables(self) -> list:
        """序列化变量为可JSON格式"""
        result = []
        for name, value in self.variables.items():
            var_info = {
                'name': name,
                'type': type(value).__name__,
                'value': self._format_var(value)
            }
            result.append(var_info)
        return sorted(result, key=lambda x: x['name'])

    def _format_var(self, value) -> str:
        if value is None:
            return '空'
        if isinstance(value, bool):
            return '真' if value else '假'
        if isinstance(value, str):
            if len(value) > 100:
                return f'"{value[:97]}..."'
            return f'"{value}"'
        if isinstance(value, (list, tuple)):
            if len(value) > 10:
                return f'{type(value).__name__}[{len(value)}]'
            return repr(value)
        if isinstance(value, dict):
            if len(value) > 5:
                return f'字典[{len(value)}]'
            return repr(value)
        return repr(value)


@app.route('/api/debug/start', methods=['POST'])
def debug_start():
    """启动调试会话"""
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()
    breakpoints = data.get('breakpoints', {})

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    session_id = str(uuid.uuid4())[:8]
    session = PlaygroundDebugSession(session_id, code)
    session.set_breakpoints(breakpoints)

    if not session.start():
        return jsonify({
            'success': False,
            'error': '编译失败',
            'compile_errors': session._compile_errors
        })

    with _debug_lock:
        _debug_sessions[session_id] = session

    import time as _time
    _time.sleep(0.3)

    state = session.get_state()
    return jsonify({
        'success': True,
        'session_id': session_id,
        'state': state
    })


@app.route('/api/debug/state/<session_id>', methods=['GET'])
def debug_state(session_id):
    """获取调试会话状态"""
    with _debug_lock:
        session = _debug_sessions.get(session_id)

    if not session:
        return jsonify({'error': '调试会话不存在或已结束'}), 404

    state = session.get_state()
    return jsonify(state)


@app.route('/api/debug/step/<session_id>', methods=['POST'])
def debug_step(session_id):
    """单步执行"""
    data = request.get_json(silent=True) or {}
    action = data.get('action', 'over')

    with _debug_lock:
        session = _debug_sessions.get(session_id)

    if not session:
        return jsonify({'error': '调试会话不存在或已结束'}), 404

    if action == 'over':
        session.step_over()
    elif action == 'into':
        session.step_into()
    elif action == 'out':
        session.step_out()
    elif action == 'continue':
        session.resume()

    import time as _time
    _time.sleep(0.3)

    state = session.get_state()
    return jsonify({
        'success': True,
        'state': state
    })


@app.route('/api/debug/stop/<session_id>', methods=['POST'])
def debug_stop(session_id):
    """停止调试会话"""
    with _debug_lock:
        session = _debug_sessions.get(session_id)

    if not session:
        return jsonify({'error': '调试会话不存在或已结束'}), 404

    session.stop()
    state = session.get_state()

    with _debug_lock:
        _debug_sessions.pop(session_id, None)

    return jsonify({
        'success': True,
        'state': state
    })


@app.route('/api/debug/breakpoints/<session_id>', methods=['POST'])
def debug_set_breakpoints(session_id):
    """设置断点"""
    data = request.get_json(silent=True) or {}
    breakpoints = data.get('breakpoints', {})

    with _debug_lock:
        session = _debug_sessions.get(session_id)

    if not session:
        return jsonify({'error': '调试会话不存在或已结束'}), 404

    session.set_breakpoints(breakpoints)
    return jsonify({
        'success': True,
        'breakpoints': breakpoints
    })


# ==================== 20+ Demo 列表 & 自动运行 API ====================

_EXAMPLES_ROOT = os.path.join(_project_dir, 'examples')
_PLAYGROUND_DEMOS_ROOT = os.path.join(_script_dir, 'demos')


def _scan_file_demos(root_dir: str, base_category: str = '示例库') -> list:
    """递归扫描 examples/ 下所有 .light 文件，生成 demo 列表（category: 子目录名）"""
    results = []
    if not os.path.isdir(root_dir):
        return results
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in sorted(filenames):
            if not fn.endswith('.light'):
                continue
            fpath = os.path.join(dirpath, fn)
            try:
                rel = os.path.relpath(fpath, root_dir)
                rel_fwd = rel.replace(os.sep, '/')
                # 第一级子目录作为 category（如果就是根目录则用 base_category）
                if '/' in rel_fwd:
                    category = rel_fwd.split('/', 1)[0]
                else:
                    category = base_category
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                size = len(content)
                # 生成稳定 id：去掉后缀 + 安全符号替换
                raw_id = 'file__' + rel_fwd.replace('.light', '').replace('/', '__').replace(' ', '_')
                safe_id = ''.join(ch if ch.isalnum() or ch in ('_', '-') else '_' for ch in raw_id)
                results.append({
                    'id': safe_id,
                    'source_type': 'file',
                    'category': category,
                    'title': fn.replace('.light', ''),
                    'path': rel_fwd,
                    'description': f'文件 {rel_fwd}（{size} 字节）',
                    'size': size,
                    'lines': content.count('\n') + 1,
                })
            except Exception:
                continue
    return results


def _collect_all_demos() -> list:
    """合并内置 BUILTIN_EXAMPLES（7 大类 30+）+ examples/ 文件扫描，总 50+"""
    demos = []
    # 1) 内置示例（BUILTIN_EXAMPLES 7 大分类）
    for cat in BUILTIN_EXAMPLES:
        cat_name = cat.get('category', '内置')
        for ex in cat.get('examples', []):
            demos.append({
                'id': 'builtin__' + ex.get('id', ''),
                'source_type': 'builtin',
                'category': '入门教程/' + cat_name,
                'title': ex.get('title', ''),
                'description': ex.get('description', ''),
                'size': len(ex.get('code', '')),
                'lines': ex.get('code', '').count('\n') + 1,
            })
    # 2) examples/ 文件库
    demos.extend(_scan_file_demos(_EXAMPLES_ROOT, base_category='示例库/根'))
    # 3) playground/demos/ 文件库
    demos.extend(_scan_file_demos(_PLAYGROUND_DEMOS_ROOT, base_category='Playground 示例'))
    return demos


def _get_demo_source(demo_id: str) -> str:
    """根据 id 获取源码。优先 BUILTIN；否则按 file__<path> 去 examples/ 读文件"""
    # 1) 内置示例
    if demo_id.startswith('builtin__'):
        inner = demo_id[len('builtin__'):]
        for cat in BUILTIN_EXAMPLES:
            for ex in cat.get('examples', []):
                if ex.get('id') == inner:
                    return ex.get('code', '')
        raise FileNotFoundError(f'未找到内置示例: {inner}')
    # 2) 文件示例
    if demo_id.startswith('file__'):
        tail = demo_id[len('file__'):]
        rel = tail.replace('__', '/') + '.light'
        fpath = os.path.join(_EXAMPLES_ROOT, rel)
        if not os.path.exists(fpath):
            # 尝试另一种常见映射：下划线直接转 /（中文路径 __ 分隔可能有歧义，这里放宽）
            alt_candidates = [
                os.path.join(_EXAMPLES_ROOT, tail.replace('_', '/') + '.light'),
                os.path.join(_EXAMPLES_ROOT, tail + '.light'),
            ]
            fpath = None
            for cand in alt_candidates:
                if os.path.exists(cand):
                    fpath = cand
                    break
        if not fpath or not os.path.exists(fpath):
            raise FileNotFoundError(f'未找到文件示例: {demo_id}')
        with open(fpath, 'r', encoding='utf-8') as f:
            return f.read()
    raise ValueError(f'demo_id 格式不支持: {demo_id}')


@app.route('/api/demos', methods=['GET'])
@app.route('/api/demos/list', methods=['GET'])
def list_demos():
    """返回所有 demo 列表：count + categories(按类别分组) + demos(平铺) + categories_tree

    Query 参数：
      category=<str>  可选：仅返回该类别（模糊包含匹配）
      limit=<int>     可选：最多返回 N 条
    """
    raw = _collect_all_demos()
    # 可选过滤
    q_cat = request.args.get('category', '').strip()
    if q_cat:
        raw = [d for d in raw if q_cat in d['category'] or q_cat in d['title']]
    try:
        limit = int(request.args.get('limit', '0'))
        if limit > 0:
            raw = raw[:limit]
    except Exception:
        pass
    # 分类聚合
    cats = {}
    for d in raw:
        cats.setdefault(d['category'], 0)
        cats[d['category']] += 1
    categories = [{'name': k, 'count': v} for k, v in cats.items()]
    return jsonify({
        'success': True,
        'count': len(raw),
        'categories_count': len(categories),
        'categories': categories,
        'demos': raw,
    })


@app.route('/api/demos/run', methods=['POST'])
def run_demo():
    """运行指定 demo：参数 { demo_id }  或 { path: 路径 } 或 { code: 源码 }
    返回与 /api/execute 一致的 run_light_code 结果，额外附带 demo_id / path。
    """
    data = request.get_json(silent=True) or {}
    demo_id = data.get('demo_id', '') or request.args.get('demo_id', '')
    path = data.get('path', '')
    code = data.get('code', '') or ''

    extra = {}
    try:
        if code:
            extra['source'] = 'inline'
        elif demo_id:
            code = _get_demo_source(demo_id)
            extra['demo_id'] = demo_id
            extra['source'] = 'demo_id'
        elif path:
            # 允许直接传相对 examples/ 的路径
            fpath = os.path.join(_EXAMPLES_ROOT, path)
            if not os.path.exists(fpath):
                return jsonify({'success': False, 'error': f'未找到路径: {path}'}), 404
            with open(fpath, 'r', encoding='utf-8') as f:
                code = f.read()
            extra['source'] = 'path'
            extra['path'] = path
        else:
            return jsonify({'success': False, 'error': '请提供 demo_id, path 或 code 三者其一'}), 400
    except FileNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404

    if not code:
        return jsonify({'success': False, 'error': 'demo 源码为空'}), 400

    run_result = run_light_code(code)
    run_result.update(extra)
    return jsonify(run_result)


@app.route('/api/demos/<demo_id>', methods=['GET'])
def get_demo(demo_id):
    """获取单个 demo 详情（含源码）"""
    try:
        code = _get_demo_source(demo_id)
    except FileNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    # 查找元信息
    info = {
        'id': demo_id,
        'code': code,
        'size': len(code),
        'lines': code.count('\n') + 1,
    }
    for d in _collect_all_demos():
        if d['id'] == demo_id:
            for k in ('category', 'title', 'description', 'source_type', 'path'):
                if k in d:
                    info[k] = d[k]
            break
    info['success'] = True
    return jsonify(info)


# ==================== 代码格式化 & 静态分析 API ====================


@app.route('/api/format', methods=['POST'])
def format_code_api():
    """格式化光明代码"""
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    try:
        from src.formatter import format_code as fmt
        formatted = fmt(code)
        return jsonify({'success': True, 'formatted': formatted})
    except ImportError:
        return jsonify({'success': False, 'error': '格式化模块不可用'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'格式化失败: {e}'})


@app.route('/api/lint', methods=['POST'])
def lint_code_api():
    """静态分析光明代码"""
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    try:
        from src.linter.light_linter import LightLinter
        linter = LightLinter()
        results = linter.lint(code)
        return jsonify({
            'success': True,
            'issues': [
                {
                    'line': r.line,
                    'column': r.column,
                    'message': r.message,
                    'severity': r.severity.value if hasattr(r, 'severity') else 'warning'
                }
                for r in results
            ],
            'issue_count': len(results)
        })
    except ImportError:
        return jsonify({'success': False, 'error': '静态分析模块不可用'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'静态分析失败: {e}'})


# ==================== 教程评估 API ====================


@app.route('/api/evaluate', methods=['POST'])
def evaluate_tutorial():
    """评估教程答案：接收代码和期望输出，返回比对结果

    请求体：
      { "code": "光明代码", "expected": "期望输出" }

    返回：
      { "success": true,
        "passed": true/false,
        "output": "实际输出",
        "expected": "期望输出",
        "error": "错误信息（如果有）",
        "execution_time": 12.34 }
    """
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()
    expected = data.get('expected', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    result = run_light_code(code)

    if not result.get('success'):
        return jsonify({
            'success': True,
            'passed': False,
            'output': '',
            'expected': expected,
            'error': result.get('error', '执行失败'),
            'execution_time': result.get('execution_time', 0)
        })

    actual_output = (result.get('output') or '').strip()
    passed = (actual_output == expected)

    return jsonify({
        'success': True,
        'passed': passed,
        'output': actual_output,
        'expected': expected,
        'error': None if passed else '输出不匹配',
        'execution_time': result.get('execution_time', 0)
    })


if __name__ == '__main__':
    print(f"光明 Web Playground 启动中...")
    print(f"  静态文件目录: {app.static_folder}")
    print(f"  分享存储目录: {SHARED_DIR}")
    print(f"  访问地址: http://localhost:5000")
    print(f"  调试器: 已集成")
    n_demos = len(_collect_all_demos())
    print(f"  可用 Demo 数量: {n_demos}  (GET /api/demos)")
    print(f"  教程评估: POST /api/evaluate")
    print()
    app.run(debug=True, host='0.0.0.0', port=5000)
