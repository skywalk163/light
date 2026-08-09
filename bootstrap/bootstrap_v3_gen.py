# 由光明编译器生成
# 源文件: 光明代码

import sys
import os
from typing import Any

try:
    import importlib.util
except ImportError:
    importlib = None

# 解析 stdlib 路径（依次尝试多种可能）
_light_stdlib = None
try:
    _light_file_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _light_file_dir = None
for _try_path in [
    os.path.join(_light_file_dir, 'stdlib') if _light_file_dir else None,
    os.path.join(_light_file_dir, '..', 'stdlib') if _light_file_dir else None,
    os.path.join(os.getcwd(), 'stdlib'),
    os.path.normpath(os.path.join(_light_file_dir, '..', '..', 'stdlib')) if _light_file_dir else None,
]:
    if _try_path and os.path.isdir(_try_path):
        _light_stdlib = _try_path
        break

if _light_stdlib and _light_stdlib not in sys.path:
    sys.path.insert(0, _light_stdlib)

if importlib:
    try:
        _light_builtin_path = os.path.join(_light_stdlib, 'builtins.py')
        if os.path.isfile(_light_builtin_path):
            spec = importlib.util.spec_from_file_location('light_builtins', _light_builtin_path)
            _light_builtin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_light_builtin)
        else:
            raise ImportError()
    except:
        import types
        _light_builtin = types.ModuleType('_light_builtin')
        _light_builtin.读取文件 = lambda path: open(path, 'r', encoding='utf-8').read()
        _light_builtin._读文件 = lambda path: open(path, 'r', encoding='utf-8').read()
        _light_builtin.写入文件 = lambda path, content: open(path, 'w', encoding='utf-8').write(content) or None
        _light_builtin.文件存在 = lambda path: __import__('os').path.isfile(path)
        _light_builtin.目录存在 = lambda path: __import__('os').path.isdir(path)
        _light_builtin.打印 = print
        _light_builtin.读取行 = lambda: sys.stdin.readline().rstrip('\r\n')
        _light_builtin.读取N字节 = lambda n: sys.stdin.read(n)
        _light_builtin.写入输出 = lambda t: (sys.stdout.write(t), sys.stdout.flush()) and None
        _light_builtin.打印输出 = lambda t: print(t, flush=True)
        _light_builtin.刷新输出 = lambda: sys.stdout.flush()
        _light_builtin.写入错误 = lambda t: (sys.stderr.write(t), sys.stderr.flush()) and None
        _light_builtin.打印错误 = lambda t: print(t, file=sys.stderr, flush=True)
        _light_builtin.解析JSON = lambda t: __import__('json').loads(t)
        _light_builtin.序列化JSON = lambda v, i=None: (__import__('json').dumps(v, ensure_ascii=False, indent=i) if i is not None else __import__('json').dumps(v, ensure_ascii=False))
        _light_builtin.美化JSON = lambda v: __import__('json').dumps(v, ensure_ascii=False, indent=2)
        _light_builtin.转字符串 = str
        _light_builtin.列表创建 = list
        _light_builtin.列表长度 = len
        _light_builtin.列 = lambda *args: list(args)
        _light_builtin.列表追加 = lambda lst, item: lst.append(item)
        _light_builtin.列表包含 = lambda lst, item: item in lst
        _light_builtin.字符串长度 = len
        _light_builtin.截取 = lambda s, start, end: s[start:end]
        _light_builtin.转大写 = lambda s: s.upper()
        _light_builtin.转小写 = lambda s: s.lower()
        _light_builtin.字典创建 = dict
        _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
        _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
        _light_builtin.字典键列表 = lambda d: list(d.keys())
        _light_builtin.字典包含键 = lambda d, k: k in d
        _light_builtin.时间戳 = lambda: __import__('time').time()
        _light_builtin.格式化时间 = lambda t, f='%Y-%m-%d %H:%M:%S': __import__('datetime').datetime.fromtimestamp(t).strftime(f) if isinstance(t, (int, float)) else __import__('datetime').datetime.strptime(t, '%Y-%m-%d %H:%M:%S').strftime(f)
else:
    import types
    _light_builtin = types.ModuleType('_light_builtin')
    _light_builtin.打印 = print
    _light_builtin.读取行 = lambda: sys.stdin.readline().rstrip('\n')
    _light_builtin.读取N字节 = lambda n: sys.stdin.read(n)
    _light_builtin.写入输出 = lambda t: (sys.stdout.write(t), sys.stdout.flush()) and None
    _light_builtin.打印输出 = lambda t: print(t, flush=True)
    _light_builtin.刷新输出 = lambda: sys.stdout.flush()
    _light_builtin.写入错误 = lambda t: (sys.stderr.write(t), sys.stderr.flush()) and None
    _light_builtin.打印错误 = lambda t: print(t, file=sys.stderr, flush=True)
    _light_builtin.解析JSON = lambda t: __import__('json').loads(t)
    _light_builtin.序列化JSON = lambda v, i=None: (__import__('json').dumps(v, ensure_ascii=False, indent=i) if i is not None else __import__('json').dumps(v, ensure_ascii=False))
    _light_builtin.美化JSON = lambda v: __import__('json').dumps(v, ensure_ascii=False, indent=2)
    _light_builtin.转字符串 = str
    _light_builtin.列表创建 = list
    _light_builtin.列表长度 = len
    _light_builtin.列 = lambda *args: list(args)
    _light_builtin.列表追加 = lambda lst, item: lst.append(item)
    _light_builtin.列表包含 = lambda lst, item: item in lst
    _light_builtin.字符串长度 = len
    _light_builtin.截取 = lambda s, start, end: s[start:end]
    _light_builtin.转大写 = lambda s: s.upper()
    _light_builtin.转小写 = lambda s: s.lower()
    _light_builtin.字典创建 = dict
    _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
    _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
    _light_builtin.字典键列表 = lambda d: list(d.keys())
    _light_builtin.字典包含键 = lambda d, k: k in d
    _light_builtin.时间戳 = lambda: __import__('time').time()
    _light_builtin.格式化时间 = lambda t, f='%Y-%m-%d %H:%M:%S': __import__('datetime').datetime.fromtimestamp(t).strftime(f) if isinstance(t, (int, float)) else __import__('datetime').datetime.strptime(t, '%Y-%m-%d %H:%M:%S').strftime(f)

# 可空类型解包辅助函数
def _light_unwrap(_x):
    assert _x is not None, "尝试解包空值"
    return _x

def 创建令牌(种别, 值, 横, 纵):
    令牌 = _light_builtin.字典创建()
    _light_builtin.字典设置(令牌, "种别", 种别)
    _light_builtin.字典设置(令牌, "值", 值)
    _light_builtin.字典设置(令牌, "横", 横)
    _light_builtin.字典设置(令牌, "纵", 纵)
    return 令牌

def 令牌种别集():
    种别字典 = _light_builtin.字典创建()
    _light_builtin.字典设置(种别字典, "关键字", "关键字")
    _light_builtin.字典设置(种别字典, "标识符", "标识符")
    _light_builtin.字典设置(种别字典, "数字", "数字")
    _light_builtin.字典设置(种别字典, "字符串", "字符串")
    _light_builtin.字典设置(种别字典, "符号", "符号")
    _light_builtin.字典设置(种别字典, "结束", "结束")
    return 种别字典

def 是关键字(文本):
    关键字列表 = _light_builtin.列表创建()
    _light_builtin.列表追加(关键字列表, "定义")
    _light_builtin.列表追加(关键字列表, "等于")
    _light_builtin.列表追加(关键字列表, "如果")
    _light_builtin.列表追加(关键字列表, "那么")
    _light_builtin.列表追加(关键字列表, "否则")
    _light_builtin.列表追加(关键字列表, "返回")
    _light_builtin.列表追加(关键字列表, "段落")
    _light_builtin.列表追加(关键字列表, "段")
    _light_builtin.列表追加(关键字列表, "接收")
    _light_builtin.列表追加(关键字列表, "当")
    _light_builtin.列表追加(关键字列表, "遍历")
    _light_builtin.列表追加(关键字列表, "跳过")
    _light_builtin.列表追加(关键字列表, "跳出")
    _light_builtin.列表追加(关键字列表, "打印")
    _light_builtin.列表追加(关键字列表, "导入")
    _light_builtin.列表追加(关键字列表, "导出")
    _light_builtin.列表追加(关键字列表, "设")
    _light_builtin.列表追加(关键字列表, "为")
    _light_builtin.列表追加(关键字列表, "从")
    _light_builtin.列表追加(关键字列表, "中的")
    _light_builtin.列表追加(关键字列表, "类")
    _light_builtin.列表追加(关键字列表, "接口")
    _light_builtin.列表追加(关键字列表, "尝试")
    _light_builtin.列表追加(关键字列表, "捕获")
    _light_builtin.列表追加(关键字列表, "抛出")
    return _light_builtin.列表包含(关键字列表, 文本)

def 符号种别():
    符号字典 = _light_builtin.字典创建()
    _light_builtin.字典设置(符号字典, "。", "句号")
    _light_builtin.字典设置(符号字典, "，", "逗号")
    _light_builtin.字典设置(符号字典, "：", "冒号")
    _light_builtin.字典设置(符号字典, "（", "左括号")
    _light_builtin.字典设置(符号字典, "）", "右括号")
    _light_builtin.字典设置(符号字典, "【", "左方括号")
    _light_builtin.字典设置(符号字典, "】", "右方括号")
    _light_builtin.字典设置(符号字典, "《", "左书名号")
    _light_builtin.字典设置(符号字典, "》", "右书名号")
    _light_builtin.字典设置(符号字典, "=", "赋值")
    _light_builtin.字典设置(符号字典, "+", "加")
    _light_builtin.字典设置(符号字典, "-", "减")
    _light_builtin.字典设置(符号字典, "*", "乘")
    _light_builtin.字典设置(符号字典, "/", "除")
    _light_builtin.字典设置(符号字典, "%", "模")
    _light_builtin.字典设置(符号字典, "^", "幂")
    _light_builtin.字典设置(符号字典, "@", "标注")
    _light_builtin.字典设置(符号字典, ".", "点")
    _light_builtin.字典设置(符号字典, ",", "逗号")
    return 符号字典

def make_program(stmt_list):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "program")
    _light_builtin.列表追加(node, stmt_list)
    return node

def make_paragraph_def(name, params, body):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "paragraph_def")
    _light_builtin.列表追加(node, name)
    _light_builtin.列表追加(node, params)
    _light_builtin.列表追加(node, body)
    return node

def make_var_decl(var_name, value):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "var_decl")
    _light_builtin.列表追加(node, var_name)
    _light_builtin.列表追加(node, value)
    return node

def make_assign(var_name, value):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "assign")
    _light_builtin.列表追加(node, var_name)
    _light_builtin.列表追加(node, value)
    return node

def make_compound_assign(var_name, op, value):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "compound_assign")
    _light_builtin.列表追加(node, var_name)
    _light_builtin.列表追加(node, op)
    _light_builtin.列表追加(node, value)
    return node

def make_if_stmt(cond, body, elif_branches, else_body):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "if_stmt")
    _light_builtin.列表追加(node, cond)
    _light_builtin.列表追加(node, body)
    _light_builtin.列表追加(node, elif_branches)
    _light_builtin.列表追加(node, else_body)
    return node

def make_while_loop(cond, body):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "while_loop")
    _light_builtin.列表追加(node, cond)
    _light_builtin.列表追加(node, body)
    return node

def make_for_each(var_name, collection, body):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "for_each")
    _light_builtin.列表追加(node, var_name)
    _light_builtin.列表追加(node, collection)
    _light_builtin.列表追加(node, body)
    return node

def make_return(value):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "return")
    _light_builtin.列表追加(node, value)
    return node

def make_break():
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "break")
    return node

def make_continue():
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "continue")
    return node

def make_print(value):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "print")
    _light_builtin.列表追加(node, value)
    return node

def make_expr_stmt(expr):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "expr_stmt")
    _light_builtin.列表追加(node, expr)
    return node

def make_identifier(name):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "identifier")
    _light_builtin.列表追加(node, name)
    return node

def make_number(value):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "number")
    _light_builtin.列表追加(node, value)
    return node

def make_string(value):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "string")
    _light_builtin.列表追加(node, value)
    return node

def make_boolean(value):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "boolean")
    _light_builtin.列表追加(node, value)
    return node

def make_null():
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "null")
    return node

def make_binary_op(op, left, right):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "binary_op")
    _light_builtin.列表追加(node, op)
    _light_builtin.列表追加(node, left)
    _light_builtin.列表追加(node, right)
    return node

def make_unary_op(op, operand):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "unary_op")
    _light_builtin.列表追加(node, op)
    _light_builtin.列表追加(node, operand)
    return node

def make_func_call(func_name, args):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "func_call")
    _light_builtin.列表追加(node, func_name)
    _light_builtin.列表追加(node, args)
    return node

def make_member_access(object, prop_name):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "member_access")
    _light_builtin.列表追加(node, object)
    _light_builtin.列表追加(node, prop_name)
    return node

def make_list_literal(elements):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "list_literal")
    _light_builtin.列表追加(node, elements)
    return node

def make_dict_literal(pairs):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "dict_literal")
    _light_builtin.列表追加(node, pairs)
    return node

def make_template_string(value):
    node = _light_builtin.列表创建()
    _light_builtin.列表追加(node, "template_string")
    _light_builtin.列表追加(node, value)
    return node

def node_type(node):
    return _light_builtin.列表获取(node, 0)

def node_data(node, index):
    return _light_builtin.列表获取(node, index)

def 创建关键字列表():
    列表 = _light_builtin.列表创建()
    _light_builtin.列表追加(列表, "定义")
    _light_builtin.列表追加(列表, "设")
    _light_builtin.列表追加(列表, "为")
    _light_builtin.列表追加(列表, "等于")
    _light_builtin.列表追加(列表, "返回")
    _light_builtin.列表追加(列表, "如果")
    _light_builtin.列表追加(列表, "否则")
    _light_builtin.列表追加(列表, "那么")
    _light_builtin.列表追加(列表, "当")
    _light_builtin.列表追加(列表, "遍历")
    _light_builtin.列表追加(列表, "中的")
    _light_builtin.列表追加(列表, "段落")
    _light_builtin.列表追加(列表, "段")
    _light_builtin.列表追加(列表, "接收")
    _light_builtin.列表追加(列表, "类")
    _light_builtin.列表追加(列表, "接口")
    _light_builtin.列表追加(列表, "跳出")
    _light_builtin.列表追加(列表, "跳过")
    _light_builtin.列表追加(列表, "导入")
    _light_builtin.列表追加(列表, "导出")
    _light_builtin.列表追加(列表, "从")
    _light_builtin.列表追加(列表, "真")
    _light_builtin.列表追加(列表, "假")
    _light_builtin.列表追加(列表, "空")
    _light_builtin.列表追加(列表, "打印")
    _light_builtin.列表追加(列表, "尝试")
    _light_builtin.列表追加(列表, "捕获")
    _light_builtin.列表追加(列表, "抛出")
    _light_builtin.列表追加(列表, "且")
    _light_builtin.列表追加(列表, "与")
    _light_builtin.列表追加(列表, "或")
    _light_builtin.列表追加(列表, "非")
    _light_builtin.列表追加(列表, "加")
    _light_builtin.列表追加(列表, "减")
    _light_builtin.列表追加(列表, "乘")
    _light_builtin.列表追加(列表, "除")
    _light_builtin.列表追加(列表, "模")
    _light_builtin.列表追加(列表, "幂")
    _light_builtin.列表追加(列表, "加上")
    _light_builtin.列表追加(列表, "减去")
    _light_builtin.列表追加(列表, "乘以")
    _light_builtin.列表追加(列表, "除以")
    _light_builtin.列表追加(列表, "模以")
    _light_builtin.列表追加(列表, "幂以")
    _light_builtin.列表追加(列表, "大于等于")
    _light_builtin.列表追加(列表, "小于等于")
    _light_builtin.列表追加(列表, "不等于")
    _light_builtin.列表追加(列表, "大于")
    _light_builtin.列表追加(列表, "小于")
    _light_builtin.列表追加(列表, "使用")
    _light_builtin.列表追加(列表, "标注")
    _light_builtin.列表追加(列表, "的")
    _light_builtin.列表追加(列表, "常量")
    return 列表

def 创建符号映射():
    映射 = _light_builtin.字典创建()
    _light_builtin.字典设置(映射, "。", "句号")
    _light_builtin.字典设置(映射, ",", "逗号")
    _light_builtin.字典设置(映射, "，", "逗号")
    _light_builtin.字典设置(映射, ":", "冒号")
    _light_builtin.字典设置(映射, "：", "冒号")
    _light_builtin.字典设置(映射, ";", "分号")
    _light_builtin.字典设置(映射, "；", "分号")
    _light_builtin.字典设置(映射, "、", "顿号")
    _light_builtin.字典设置(映射, "(", "左括号")
    _light_builtin.字典设置(映射, "（", "左括号")
    _light_builtin.字典设置(映射, ")", "右括号")
    _light_builtin.字典设置(映射, "）", "右括号")
    _light_builtin.字典设置(映射, "[", "左中括号")
    _light_builtin.字典设置(映射, "【", "左中括号")
    _light_builtin.字典设置(映射, "]", "右中括号")
    _light_builtin.字典设置(映射, "】", "右中括号")
    _light_builtin.字典设置(映射, "{", "左花括号")
    _light_builtin.字典设置(映射, "}", "右花括号")
    _light_builtin.字典设置(映射, "《", "左书名号")
    _light_builtin.字典设置(映射, "》", "右书名号")
    _light_builtin.字典设置(映射, "+", "加")
    _light_builtin.字典设置(映射, "-", "减")
    _light_builtin.字典设置(映射, "*", "乘")
    _light_builtin.字典设置(映射, "×", "乘")
    _light_builtin.字典设置(映射, "/", "除")
    _light_builtin.字典设置(映射, "÷", "除")
    _light_builtin.字典设置(映射, "%", "模")
    _light_builtin.字典设置(映射, "^", "幂")
    _light_builtin.字典设置(映射, "=", "赋值")
    _light_builtin.字典设置(映射, "!", "非")
    _light_builtin.字典设置(映射, "@", "标注")
    _light_builtin.字典设置(映射, "->", "箭头")
    _light_builtin.字典设置(映射, ">", "大于")
    _light_builtin.字典设置(映射, "<", "小于")
    _light_builtin.字典设置(映射, "#", "注释")
    _light_builtin.字典设置(映射, "\\", "反斜线")
    _light_builtin.字典设置(映射, "\n", "换行")
    _light_builtin.字典设置(映射, " ", "空白")
    _light_builtin.字典设置(映射, "\t", "制表")
    return 映射

def 是空白(字符):
    if (((字符 == " ") or (字符 == "\t")) or (字符 == "\r")):
        return True
    return False

def 是数字(字符):
    码 = _light_builtin.字符串获取(字符, 0)
    if ((码 >= "0") and (码 <= "9")):
        return True
    return False

def 是字母(字符):
    码 = _light_builtin.字符串获取(字符, 0)
    if ((码 >= "a") and (码 <= "z")):
        return True
    if ((码 >= "A") and (码 <= "Z")):
        return True
    if (码 == "_"):
        return True
    return False

def 是标识符字符(字符, 符号字典):
    if _light_builtin.字典包含键(符号字典, 字符):
        return False
    if 是字母(字符):
        return True
    if 是数字(字符):
        return True
    if (字符 == "_"):
        return True
    if (字符 > ""):
        return True
    return False

def 匹配关键字(文本, 关键字列表):
    最佳关键字 = None
    索引 = 0
    列表长度 = _light_builtin.列表长度(关键字列表)
    while (索引 < 列表长度):
        关键字 = _light_builtin.列表获取(关键字列表, 索引)
        关键字长度 = _light_builtin.字符串长度(关键字)
        文本长度 = _light_builtin.字符串长度(文本)
        if ((关键字长度 > 0) and (关键字长度 <= 文本长度)):
            if (_light_builtin.截取(文本, 0, 关键字长度) == 关键字):
                if ((最佳关键字 == None) or (关键字长度 > _light_builtin.字符串长度(最佳关键字))):
                    最佳关键字 = 关键字
        索引 += 1
    return 最佳关键字

def 含插值模式(文本):
    长度 = _light_builtin.字符串长度(文本)
    i = 0
    while (i < 长度):
        ch = _light_builtin.字符串获取(文本, i)
        if (ch == "{"):
            if ((i + 1) < 长度):
                后字符 = _light_builtin.字符串获取(文本, (i + 1))
                if ((是字母(后字符) or 是数字(后字符)) or (后字符 == "_")):
                    j = (i + 1)
                    while (j < 长度):
                        c = _light_builtin.字符串获取(文本, j)
                        if (c == "}"):
                            return True
                        elif (c == "{"):
                            break
                        j += 1
        i += 1
    return False

def 收集标识符文本(源码, 位置, 符号字典):
    结果 = ""
    源码长度 = _light_builtin.字符串长度(源码)
    while (位置 < 源码长度):
        字符 = _light_builtin.字符串获取(源码, 位置)
        if 是标识符字符(字符, 符号字典):
            结果 = (结果 + 字符)
            位置 += 1
        else:
            break
    return 结果

def 标识符分词(文本, 关键字列表, 行, 列):
    结果 = _light_builtin.列表创建()
    剩余文本 = 文本
    当前列 = 列
    while (_light_builtin.字符串长度(剩余文本) > 0):
        找到关键字 = 匹配关键字(剩余文本, 关键字列表)
        if (找到关键字 != None):
            找到长度 = _light_builtin.字符串长度(找到关键字)
            剩余长度 = _light_builtin.字符串长度(剩余文本)
            需跳过 = False
            if ((找到长度 == 1) and (找到长度 < 剩余长度)):
                下一个字符 = _light_builtin.字符串获取(剩余文本, 找到长度)
                if (下一个字符 > ""):
                    需跳过 = True
            if 需跳过:
                _light_builtin.列表追加(结果, 创建令牌("标识符", 剩余文本, 行, 当前列))
                剩余文本 = ""
            else:
                _light_builtin.列表追加(结果, 创建令牌("关键字", 找到关键字, 行, 当前列))
                当前列 += 找到长度
                剩余文本 = _light_builtin.截取(剩余文本, 找到长度, 剩余长度)
        else:
            _light_builtin.列表追加(结果, 创建令牌("标识符", 剩余文本, 行, 当前列))
            剩余文本 = ""
    return 结果

def 跳到行尾(源码, 位置):
    源码长度 = _light_builtin.字符串长度(源码)
    while (位置 < 源码长度):
        字符 = _light_builtin.字符串获取(源码, 位置)
        if (字符 == "\n"):
            return 位置
        位置 += 1
    return 位置

def 词法分析(源码):
    令牌列表 = _light_builtin.列表创建()
    源码长度 = _light_builtin.字符串长度(源码)
    关键字列表 = 创建关键字列表()
    符号映射 = 创建符号映射()
    位置 = 0
    行 = 1
    列 = 1
    缩进栈 = _light_builtin.列表创建()
    _light_builtin.列表追加(缩进栈, 0)
    while (位置 < 源码长度):
        字符 = _light_builtin.字符串获取(源码, 位置)
        if ((字符 == " ") or (字符 == "\t")):
            位置 += 1
            列 += 1
            continue
        if (字符 == "\n"):
            _light_builtin.列表追加(令牌列表, 创建令牌("换行", "\n", 行, 列))
            行 += 1
            列 = 1
            位置 += 1
            缩进 = 0
            while (位置 < 源码长度):
                下一个 = _light_builtin.字符串获取(源码, 位置)
                if (下一个 == " "):
                    缩进 += 1
                    位置 += 1
                elif (下一个 == "\t"):
                    缩进 += 4
                    位置 += 1
                else:
                    break
            列 = (缩进 + 1)
            栈顶 = _light_builtin.列表获取(缩进栈, (_light_builtin.列表长度(缩进栈) - 1))
            if (缩进 > 栈顶):
                _light_builtin.列表追加(缩进栈, 缩进)
                _light_builtin.列表追加(令牌列表, 创建令牌("缩进", 缩进, 行, 1))
            elif (缩进 < 栈顶):
                while (_light_builtin.列表获取(缩进栈, (_light_builtin.列表长度(缩进栈) - 1)) > 缩进):
                    _light_builtin.列表弹出(缩进栈)
                    _light_builtin.列表追加(令牌列表, 创建令牌("反缩进", _light_builtin.列表获取(缩进栈, (_light_builtin.列表长度(缩进栈) - 1)), 行, 1))
            else:
                continue
            continue
        if (字符 == "\r"):
            位置 += 1
            continue
        if (字符 == "#"):
            注释结束 = 跳到行尾(源码, (位置 + 1))
            _light_builtin.列表追加(令牌列表, 创建令牌("注释", _light_builtin.截取(源码, 位置, 注释结束), 行, 列))
            位置 = 注释结束
            continue
        if _light_builtin.字典包含键(符号映射, 字符):
            符号名 = _light_builtin.字典获取(符号映射, 字符)
            _light_builtin.列表追加(令牌列表, 创建令牌(符号名, 字符, 行, 列))
            位置 += 1
            列 += 1
            continue
        if ((字符 == "\"") or (字符 == "'")):
            字符串结果 = ""
            分隔符 = 字符
            位置 += 1
            while (位置 < 源码长度):
                字符串字符 = _light_builtin.字符串获取(源码, 位置)
                if (字符串字符 == 分隔符):
                    位置 += 1
                    break
                elif (字符串字符 == "\\"):
                    位置 += 1
                    if (位置 < 源码长度):
                        转义字符 = _light_builtin.字符串获取(源码, 位置)
                        if (转义字符 == "n"):
                            字符串结果 = (字符串结果 + "\n")
                        elif (转义字符 == "t"):
                            字符串结果 = (字符串结果 + "\t")
                        else:
                            字符串结果 = (字符串结果 + 转义字符)
                        位置 += 1
                else:
                    字符串结果 = (字符串结果 + 字符串字符)
                    位置 += 1
            if 含插值模式(字符串结果):
                _light_builtin.列表追加(令牌列表, 创建令牌("模板字符串", 字符串结果, 行, 列))
            else:
                _light_builtin.列表追加(令牌列表, 创建令牌("字符串", 字符串结果, 行, 列))
            列 = ((列 + _light_builtin.字符串长度(字符串结果)) + 2)
            continue
        if ((字符 == "f") and ((位置 + 1) < 源码长度)):
            下一个字符 = _light_builtin.字符串获取(源码, (位置 + 1))
            if ((下一个字符 == "\"") or (下一个字符 == "'")):
                模板内容 = ""
                分隔符 = 下一个字符
                位置 += 2
                while (位置 < 源码长度):
                    字符串字符 = _light_builtin.字符串获取(源码, 位置)
                    if (字符串字符 == 分隔符):
                        位置 += 1
                        break
                    elif (字符串字符 == "\\"):
                        位置 += 1
                        if (位置 < 源码长度):
                            转义字符 = _light_builtin.字符串获取(源码, 位置)
                            if (转义字符 == "n"):
                                模板内容 = (模板内容 + "\n")
                            elif (转义字符 == "t"):
                                模板内容 = (模板内容 + "\t")
                            elif (转义字符 == "{"):
                                模板内容 = (模板内容 + "{")
                            elif (转义字符 == "}"):
                                模板内容 = (模板内容 + "}")
                            else:
                                模板内容 = (模板内容 + 转义字符)
                            位置 += 1
                    else:
                        模板内容 = (模板内容 + 字符串字符)
                        位置 += 1
                _light_builtin.列表追加(令牌列表, 创建令牌("模板字符串", 模板内容, 行, 列))
                列 = ((列 + _light_builtin.字符串长度(模板内容)) + 3)
                continue
        if 是数字(字符):
            数字字符串 = ""
            while (位置 < 源码长度):
                数字字符 = _light_builtin.字符串获取(源码, 位置)
                if 是数字(数字字符):
                    数字字符串 = (数字字符串 + 数字字符)
                    位置 += 1
                else:
                    break
            if ((位置 < 源码长度) and (_light_builtin.字符串获取(源码, 位置) == ".")):
                数字字符串 = (数字字符串 + ".")
                位置 += 1
                while (位置 < 源码长度):
                    小数数字 = _light_builtin.字符串获取(源码, 位置)
                    if 是数字(小数数字):
                        数字字符串 = (数字字符串 + 小数数字)
                        位置 += 1
                    else:
                        break
            _light_builtin.列表追加(令牌列表, 创建令牌("数字", 数字字符串, 行, 列))
            列 = (列 + _light_builtin.字符串长度(数字字符串))
            continue
        if ((字符 > "") or 是字母(字符)):
            标识符文本 = 收集标识符文本(源码, 位置, 符号映射)
            标识符长度 = _light_builtin.字符串长度(标识符文本)
            if (标识符长度 > 0):
                分词结果 = 标识符分词(标识符文本, 关键字列表, 行, 列)
                分词索引 = 0
                while (分词索引 < _light_builtin.列表长度(分词结果)):
                    _light_builtin.列表追加(令牌列表, _light_builtin.列表获取(分词结果, 分词索引))
                    分词索引 += 1
                位置 += 标识符长度
                列 += 标识符长度
            continue
        错误消息 = "未知字符"
        _light_builtin.列表追加(令牌列表, 创建令牌("错误", 错误消息, 行, 列))
        位置 += 1
        列 += 1
    while (_light_builtin.列表长度(缩进栈) > 1):
        _light_builtin.列表弹出(缩进栈)
        _light_builtin.列表追加(令牌列表, 创建令牌("反缩进", _light_builtin.列表获取(缩进栈, (_light_builtin.列表长度(缩进栈) - 1)), 行, 列))
    return 令牌列表

def tok_kw():
    return "关键字"

def tok_id():
    return "标识符"

def tok_num():
    return "数字"

def tok_str():
    return "字符串"

def tok_indent():
    return "缩进"

def tok_dedent():
    return "反缩进"

def tok_newline():
    return "换行"

def tok_eof():
    return "结束"

def tok_comment():
    return "注释"

def sym_period():
    return "句号"

def sym_colon():
    return "冒号"

def sym_comma():
    return "逗号"

def sym_lparen():
    return "左括号"

def sym_rparen():
    return "右括号"

def sym_lbook():
    return "左书名号"

def sym_rbook():
    return "右书名号"

def token_type(tok):
    return _light_builtin.字典获取(tok, "种别")

def token_value(tok):
    return _light_builtin.字典获取(tok, "值")

def is_kw(tok, expected):
    if ((_light_builtin.字典获取(tok, "种别") == "关键字") and (_light_builtin.字典获取(tok, "值") == expected)):
        return True
    return False

def is_sym(tok, expected):
    if (_light_builtin.字典获取(tok, "种别") == expected):
        return True
    return False

def is_eof(tok):
    return (_light_builtin.字典获取(tok, "种别") == "结束")

def skip_newlines(tokens, pos):
    p = pos
    while (p < _light_builtin.列表长度(tokens)):
        tok = _light_builtin.列表获取(tokens, p)
        ttype = _light_builtin.字典获取(tok, "种别")
        if ((ttype == "换行") or (ttype == "注释")):
            p += 1
        else:
            break
    return p

def is_binary_op(ttype, tval):
    if (ttype == "关键字"):
        if ((((tval == "加") or (tval == "减")) or (tval == "乘")) or (tval == "除")):
            return True
        if ((tval == "模") or (tval == "幂")):
            return True
        if ((((tval == "加上") or (tval == "减去")) or (tval == "乘以")) or (tval == "除以")):
            return True
        if ((tval == "等于") or (tval == "不等于")):
            return True
        if ((((tval == "大于") or (tval == "小于")) or (tval == "大于等于")) or (tval == "小于等于")):
            return True
        if (((tval == "且") or (tval == "与")) or (tval == "或")):
            return True
    return False

def parse_expr(tokens, pos):
    result = parse_or_expr(tokens, pos)
    return result

def parse_or_expr(tokens, pos):
    left_result = parse_and_expr(tokens, pos)
    left = _light_builtin.列表获取(left_result, 0)
    p = _light_builtin.列表获取(left_result, 1)
    while (p < _light_builtin.列表长度(tokens)):
        tok = _light_builtin.列表获取(tokens, p)
        ttype = _light_builtin.字典获取(tok, "种别")
        tval = _light_builtin.字典获取(tok, "值")
        if ((ttype == "关键字") and (tval == "或")):
            p += 1
            right_result = parse_and_expr(tokens, p)
            right = _light_builtin.列表获取(right_result, 0)
            p = _light_builtin.列表获取(right_result, 1)
            left = make_binary_op(tval, left, right)
        else:
            break
    return [left, p]

def parse_and_expr(tokens, pos):
    left_result = parse_compare_expr(tokens, pos)
    left = _light_builtin.列表获取(left_result, 0)
    p = _light_builtin.列表获取(left_result, 1)
    while (p < _light_builtin.列表长度(tokens)):
        tok = _light_builtin.列表获取(tokens, p)
        ttype = _light_builtin.字典获取(tok, "种别")
        tval = _light_builtin.字典获取(tok, "值")
        if ((ttype == "关键字") and ((tval == "且") or (tval == "与"))):
            p += 1
            right_result = parse_compare_expr(tokens, p)
            right = _light_builtin.列表获取(right_result, 0)
            p = _light_builtin.列表获取(right_result, 1)
            left = make_binary_op(tval, left, right)
        else:
            break
    return [left, p]

def parse_compare_expr(tokens, pos):
    left_result = parse_add_expr(tokens, pos)
    left = _light_builtin.列表获取(left_result, 0)
    p = _light_builtin.列表获取(left_result, 1)
    if (p < _light_builtin.列表长度(tokens)):
        tok = _light_builtin.列表获取(tokens, p)
        ttype = _light_builtin.字典获取(tok, "种别")
        tval = _light_builtin.字典获取(tok, "值")
        if (ttype == "关键字"):
            if ((((((tval == "等于") or (tval == "不等于")) or (tval == "大于")) or (tval == "小于")) or (tval == "大于等于")) or (tval == "小于等于")):
                p += 1
                right_result = parse_add_expr(tokens, p)
                right = _light_builtin.列表获取(right_result, 0)
                p = _light_builtin.列表获取(right_result, 1)
                left = make_binary_op(tval, left, right)
    return [left, p]

def parse_add_expr(tokens, pos):
    left_result = parse_mul_expr(tokens, pos)
    left = _light_builtin.列表获取(left_result, 0)
    p = _light_builtin.列表获取(left_result, 1)
    while (p < _light_builtin.列表长度(tokens)):
        tok = _light_builtin.列表获取(tokens, p)
        ttype = _light_builtin.字典获取(tok, "种别")
        tval = _light_builtin.字典获取(tok, "值")
        is_add_op = False
        op_name = ""
        if (ttype == "关键字"):
            if ((tval == "加") or (tval == "加上")):
                is_add_op = True
                op_name = "加"
            elif ((tval == "减") or (tval == "减去")):
                is_add_op = True
                op_name = "减"
        elif (ttype == "加"):
            is_add_op = True
            op_name = "加"
        elif (ttype == "减"):
            is_add_op = True
            op_name = "减"
        if is_add_op:
            p += 1
            right_result = parse_mul_expr(tokens, p)
            right = _light_builtin.列表获取(right_result, 0)
            p = _light_builtin.列表获取(right_result, 1)
            left = make_binary_op(op_name, left, right)
        else:
            break
    return [left, p]

def parse_mul_expr(tokens, pos):
    left_result = parse_unary_expr(tokens, pos)
    left = _light_builtin.列表获取(left_result, 0)
    p = _light_builtin.列表获取(left_result, 1)
    while (p < _light_builtin.列表长度(tokens)):
        tok = _light_builtin.列表获取(tokens, p)
        ttype = _light_builtin.字典获取(tok, "种别")
        tval = _light_builtin.字典获取(tok, "值")
        is_mul_op = False
        op_name = ""
        if (ttype == "关键字"):
            if ((tval == "乘") or (tval == "乘以")):
                is_mul_op = True
                op_name = "乘"
            elif ((tval == "除") or (tval == "除以")):
                is_mul_op = True
                op_name = "除"
            elif (tval == "模"):
                is_mul_op = True
                op_name = "模"
            elif (tval == "幂"):
                is_mul_op = True
                op_name = "幂"
        elif (ttype == "乘"):
            is_mul_op = True
            op_name = "乘"
        elif (ttype == "除"):
            is_mul_op = True
            op_name = "除"
        elif (ttype == "模"):
            is_mul_op = True
            op_name = "模"
        elif (ttype == "幂"):
            is_mul_op = True
            op_name = "幂"
        if is_mul_op:
            p += 1
            right_result = parse_unary_expr(tokens, p)
            right = _light_builtin.列表获取(right_result, 0)
            p = _light_builtin.列表获取(right_result, 1)
            left = make_binary_op(op_name, left, right)
        else:
            break
    return [left, p]

def parse_unary_expr(tokens, pos):
    tok = _light_builtin.列表获取(tokens, pos)
    ttype = _light_builtin.字典获取(tok, "种别")
    tval = _light_builtin.字典获取(tok, "值")
    if ((ttype == "关键字") and ((tval == "非") or (tval == "不是"))):
        operand_result = parse_unary_expr(tokens, (pos + 1))
        operand = _light_builtin.列表获取(operand_result, 0)
        node = make_unary_op(tval, operand)
        return [node, _light_builtin.列表获取(operand_result, 1)]
    result = parse_primary(tokens, pos)
    return result

def parse_primary(tokens, pos):
    tok = _light_builtin.列表获取(tokens, pos)
    ttype = _light_builtin.字典获取(tok, "种别")
    tval = _light_builtin.字典获取(tok, "值")
    if (ttype == "数字"):
        node = make_number(tval)
        return [node, (pos + 1)]
    if (ttype == "字符串"):
        node = make_string(tval)
        return [node, (pos + 1)]
    if (ttype == "模板字符串"):
        node = make_template_string(tval)
        return [node, (pos + 1)]
    if ((ttype == "关键字") and ((tval == "真") or (tval == "假"))):
        node = make_boolean(tval)
        return [node, (pos + 1)]
    if ((ttype == "关键字") and (tval == "空")):
        node = make_null()
        return [node, (pos + 1)]
    if (ttype == "标识符"):
        p = (pos + 1)
        if (p < _light_builtin.列表长度(tokens)):
            next_t = _light_builtin.列表获取(tokens, p)
            if (_light_builtin.字典获取(next_t, "种别") == "左括号"):
                name = tval
                args = _light_builtin.列表创建()
                p += 1
                if (p < _light_builtin.列表长度(tokens)):
                    rp_tok = _light_builtin.列表获取(tokens, p)
                    if (_light_builtin.字典获取(rp_tok, "种别") != "右括号"):
                        while True:
                            arg_result = parse_expr(tokens, p)
                            arg = _light_builtin.列表获取(arg_result, 0)
                            p = _light_builtin.列表获取(arg_result, 1)
                            _light_builtin.列表追加(args, arg)
                            if (p < _light_builtin.列表长度(tokens)):
                                sep = _light_builtin.列表获取(tokens, p)
                                if (_light_builtin.字典获取(sep, "种别") == "逗号"):
                                    p += 1
                                    continue
                            break
                if (p < _light_builtin.列表长度(tokens)):
                    rp = _light_builtin.列表获取(tokens, p)
                    if (_light_builtin.字典获取(rp, "种别") == "右括号"):
                        p += 1
                node = make_func_call(name, args)
                return [node, p]
        node = make_identifier(tval)
        return [node, (pos + 1)]
    if (ttype == "左书名号"):
        name_tok = _light_builtin.列表获取(tokens, (pos + 1))
        name = _light_builtin.字典获取(name_tok, "值")
        rbook = _light_builtin.列表获取(tokens, (pos + 2))
        lparen = _light_builtin.列表获取(tokens, (pos + 3))
        args = _light_builtin.列表创建()
        p = (pos + 4)
        rp_tok = _light_builtin.列表获取(tokens, p)
        if (_light_builtin.字典获取(rp_tok, "种别") != "右括号"):
            while True:
                arg_result = parse_expr(tokens, p)
                arg = _light_builtin.列表获取(arg_result, 0)
                p = _light_builtin.列表获取(arg_result, 1)
                _light_builtin.列表追加(args, arg)
                sep = _light_builtin.列表获取(tokens, p)
                if (_light_builtin.字典获取(sep, "种别") == "逗号"):
                    p += 1
                    continue
                break
        rp = _light_builtin.列表获取(tokens, p)
        if (_light_builtin.字典获取(rp, "种别") == "右括号"):
            p += 1
        node = make_func_call(name, args)
        return [node, p]
    if (ttype == "左中括号"):
        首元素后位置 = (pos + 1)
        是不是字典 = False
        if (首元素后位置 < _light_builtin.列表长度(tokens)):
            peek_t = _light_builtin.列表获取(tokens, 首元素后位置)
            if (_light_builtin.字典获取(peek_t, "种别") != "右中括号"):
                first_result = parse_expr(tokens, 首元素后位置)
                after_first = _light_builtin.列表获取(first_result, 1)
                if (after_first < _light_builtin.列表长度(tokens)):
                    next_after = _light_builtin.列表获取(tokens, after_first)
                    if (_light_builtin.字典获取(next_after, "种别") == "冒号"):
                        是不是字典 = True
        if 是不是字典:
            pairs = _light_builtin.列表创建()
            p = (pos + 1)
            while (p < _light_builtin.列表长度(tokens)):
                next_t = _light_builtin.列表获取(tokens, p)
                if (_light_builtin.字典获取(next_t, "种别") == "右中括号"):
                    p += 1
                    break
                key_result = parse_expr(tokens, p)
                key_node = _light_builtin.列表获取(key_result, 0)
                p = _light_builtin.列表获取(key_result, 1)
                if (p < _light_builtin.列表长度(tokens)):
                    colon_t = _light_builtin.列表获取(tokens, p)
                    if (_light_builtin.字典获取(colon_t, "种别") == "冒号"):
                        p += 1
                val_result = parse_expr(tokens, p)
                val_node = _light_builtin.列表获取(val_result, 0)
                p = _light_builtin.列表获取(val_result, 1)
                pair = _light_builtin.列表创建()
                _light_builtin.列表追加(pair, key_node)
                _light_builtin.列表追加(pair, val_node)
                _light_builtin.列表追加(pairs, pair)
                if (p < _light_builtin.列表长度(tokens)):
                    sep = _light_builtin.列表获取(tokens, p)
                    if (_light_builtin.字典获取(sep, "种别") == "逗号"):
                        p += 1
                    else:
                        if (_light_builtin.字典获取(sep, "种别") == "右中括号"):
                            p += 1
                        break
            node = make_dict_literal(pairs)
            return [node, p]
        elems = _light_builtin.列表创建()
        p = (pos + 1)
        while (p < _light_builtin.列表长度(tokens)):
            next_t = _light_builtin.列表获取(tokens, p)
            if (_light_builtin.字典获取(next_t, "种别") == "右中括号"):
                p += 1
                break
            elem_result = parse_expr(tokens, p)
            _light_builtin.列表追加(elems, _light_builtin.列表获取(elem_result, 0))
            p = _light_builtin.列表获取(elem_result, 1)
            if (p < _light_builtin.列表长度(tokens)):
                sep = _light_builtin.列表获取(tokens, p)
                if (_light_builtin.字典获取(sep, "种别") == "逗号"):
                    p += 1
                else:
                    if (_light_builtin.字典获取(sep, "种别") == "右中括号"):
                        p += 1
                    break
        node = make_list_literal(elems)
        return [node, p]
    if (ttype == "左花括号"):
        pairs = _light_builtin.列表创建()
        p = (pos + 1)
        while (p < _light_builtin.列表长度(tokens)):
            next_t = _light_builtin.列表获取(tokens, p)
            if (_light_builtin.字典获取(next_t, "种别") == "右花括号"):
                p += 1
                break
            key_result = parse_expr(tokens, p)
            key_node = _light_builtin.列表获取(key_result, 0)
            p = _light_builtin.列表获取(key_result, 1)
            if (p < _light_builtin.列表长度(tokens)):
                colon_t = _light_builtin.列表获取(tokens, p)
                if (_light_builtin.字典获取(colon_t, "种别") == "冒号"):
                    p += 1
            val_result = parse_expr(tokens, p)
            val_node = _light_builtin.列表获取(val_result, 0)
            p = _light_builtin.列表获取(val_result, 1)
            pair = _light_builtin.列表创建()
            _light_builtin.列表追加(pair, key_node)
            _light_builtin.列表追加(pair, val_node)
            _light_builtin.列表追加(pairs, pair)
            if (p < _light_builtin.列表长度(tokens)):
                sep = _light_builtin.列表获取(tokens, p)
                if (_light_builtin.字典获取(sep, "种别") == "逗号"):
                    p += 1
                else:
                    if (_light_builtin.字典获取(sep, "种别") == "右花括号"):
                        p += 1
                    break
        node = make_dict_literal(pairs)
        return [node, p]
    if (ttype == "左括号"):
        p = (pos + 1)
        expr_result = parse_expr(tokens, p)
        expr = _light_builtin.列表获取(expr_result, 0)
        p = _light_builtin.列表获取(expr_result, 1)
        if (p < _light_builtin.列表长度(tokens)):
            rp = _light_builtin.列表获取(tokens, p)
            if (_light_builtin.字典获取(rp, "种别") == "右括号"):
                p += 1
        return [expr, p]
    node = make_identifier(tval)
    return [node, (pos + 1)]

def parse_return_stmt(tokens, pos):
    tok = _light_builtin.列表获取(tokens, pos)
    p = (pos + 1)
    p = skip_newlines(tokens, p)
    if (p < _light_builtin.列表长度(tokens)):
        next_tok = _light_builtin.列表获取(tokens, p)
        ttype = _light_builtin.字典获取(next_tok, "种别")
        if (ttype == "句号"):
            node = make_return(None)
            return [node, (p + 1)]
        if ((ttype == "反缩进") or (ttype == "结束")):
            node = make_return(None)
            return [node, p]
        result = parse_expr(tokens, p)
        node = make_return(_light_builtin.列表获取(result, 0))
        p = _light_builtin.列表获取(result, 1)
        return [node, p]
    node = make_return(None)
    return [node, p]

def parse_var_decl(tokens, pos):
    tok = _light_builtin.列表获取(tokens, pos)
    p = (pos + 1)
    name_tok = _light_builtin.列表获取(tokens, p)
    var_name = _light_builtin.字典获取(name_tok, "值")
    p += 1
    if (p < _light_builtin.列表长度(tokens)):
        eq_tok = _light_builtin.列表获取(tokens, p)
        if (_light_builtin.字典获取(eq_tok, "种别") == "关键字"):
            if ((_light_builtin.字典获取(eq_tok, "值") == "等于") or (_light_builtin.字典获取(eq_tok, "值") == "为")):
                p += 1
    result = parse_expr(tokens, p)
    node = make_var_decl(var_name, _light_builtin.列表获取(result, 0))
    return [node, _light_builtin.列表获取(result, 1)]

def parse_assign(tokens, pos):
    tok = _light_builtin.列表获取(tokens, pos)
    p = (pos + 1)
    name_tok = _light_builtin.列表获取(tokens, p)
    var_name = _light_builtin.字典获取(name_tok, "值")
    p += 1
    if (p < _light_builtin.列表长度(tokens)):
        as_tok = _light_builtin.列表获取(tokens, p)
        if ((_light_builtin.字典获取(as_tok, "种别") == "关键字") and (_light_builtin.字典获取(as_tok, "值") == "为")):
            p += 1
    result = parse_expr(tokens, p)
    node = make_assign(var_name, _light_builtin.列表获取(result, 0))
    return [node, _light_builtin.列表获取(result, 1)]

def parse_compound_assign(tokens, pos, op):
    tok = _light_builtin.列表获取(tokens, pos)
    var_name = _light_builtin.字典获取(tok, "值")
    p = (pos + 1)
    result = parse_expr(tokens, (p + 1))
    node = make_compound_assign(var_name, op, _light_builtin.列表获取(result, 0))
    return [node, _light_builtin.列表获取(result, 1)]

def parse_block(tokens, pos):
    body = _light_builtin.列表创建()
    p = pos
    while (p < _light_builtin.列表长度(tokens)):
        stmt_tok = _light_builtin.列表获取(tokens, p)
        stype = _light_builtin.字典获取(stmt_tok, "种别")
        if ((stype == "反缩进") or (stype == "结束")):
            break
        stmt_result = parse_stmt(tokens, p)
        _light_builtin.列表追加(body, _light_builtin.列表获取(stmt_result, 0))
        p = _light_builtin.列表获取(stmt_result, 1)
        p = skip_newlines(tokens, p)
    return [body, p]

def parse_while(tokens, pos):
    tok = _light_builtin.列表获取(tokens, pos)
    p = (pos + 1)
    cond_result = parse_expr(tokens, p)
    cond = _light_builtin.列表获取(cond_result, 0)
    p = _light_builtin.列表获取(cond_result, 1)
    if (p < _light_builtin.列表长度(tokens)):
        col_tok = _light_builtin.列表获取(tokens, p)
        if (_light_builtin.字典获取(col_tok, "种别") == "冒号"):
            p += 1
    p = skip_newlines(tokens, p)
    if (p < _light_builtin.列表长度(tokens)):
        indent_tok = _light_builtin.列表获取(tokens, p)
        if (_light_builtin.字典获取(indent_tok, "种别") == "缩进"):
            p += 1
            block_result = parse_block(tokens, p)
            body = _light_builtin.列表获取(block_result, 0)
            p = _light_builtin.列表获取(block_result, 1)
            if (p < _light_builtin.列表长度(tokens)):
                dedent_tok = _light_builtin.列表获取(tokens, p)
                if (_light_builtin.字典获取(dedent_tok, "种别") == "反缩进"):
                    p += 1
            node = make_while_loop(cond, body)
            return [node, p]
    node = make_while_loop(cond, _light_builtin.列表创建())
    return [node, p]

def parse_if(tokens, pos):
    tok = _light_builtin.列表获取(tokens, pos)
    p = (pos + 1)
    cond_result = parse_expr(tokens, p)
    cond = _light_builtin.列表获取(cond_result, 0)
    p = _light_builtin.列表获取(cond_result, 1)
    if (p < _light_builtin.列表长度(tokens)):
        col_tok = _light_builtin.列表获取(tokens, p)
        if (_light_builtin.字典获取(col_tok, "种别") == "冒号"):
            p += 1
    p = skip_newlines(tokens, p)
    body = _light_builtin.列表创建()
    if (p < _light_builtin.列表长度(tokens)):
        indent_tok = _light_builtin.列表获取(tokens, p)
        if (_light_builtin.字典获取(indent_tok, "种别") == "缩进"):
            p += 1
            block_result = parse_block(tokens, p)
            body = _light_builtin.列表获取(block_result, 0)
            p = _light_builtin.列表获取(block_result, 1)
            if (p < _light_builtin.列表长度(tokens)):
                dedent_tok = _light_builtin.列表获取(tokens, p)
                if (_light_builtin.字典获取(dedent_tok, "种别") == "反缩进"):
                    p += 1
    elif_branches = _light_builtin.列表创建()
    while (p < _light_builtin.列表长度(tokens)):
        p = skip_newlines(tokens, p)
        if (p >= _light_builtin.列表长度(tokens)):
            break
        elif_tok = _light_builtin.列表获取(tokens, p)
        is_elif = False
        elif_p = p
        if ((_light_builtin.字典获取(elif_tok, "种别") == "关键字") and (_light_builtin.字典获取(elif_tok, "值") == "否则若")):
            is_elif = True
            elif_p = (p + 1)
        elif ((_light_builtin.字典获取(elif_tok, "种别") == "关键字") and (_light_builtin.字典获取(elif_tok, "值") == "否则")):
            if ((p + 1) < _light_builtin.列表长度(tokens)):
                next_tok = _light_builtin.列表获取(tokens, (p + 1))
                if ((_light_builtin.字典获取(next_tok, "种别") == "关键字") and (_light_builtin.字典获取(next_tok, "值") == "如果")):
                    is_elif = True
                    elif_p = (p + 2)
        if is_elif:
            p = elif_p
            elif_cond = parse_expr(tokens, p)
            elif_cond_node = _light_builtin.列表获取(elif_cond, 0)
            p = _light_builtin.列表获取(elif_cond, 1)
            if (p < _light_builtin.列表长度(tokens)):
                col = _light_builtin.列表获取(tokens, p)
                if (_light_builtin.字典获取(col, "种别") == "冒号"):
                    p += 1
            p = skip_newlines(tokens, p)
            elif_body = _light_builtin.列表创建()
            if (p < _light_builtin.列表长度(tokens)):
                indent = _light_builtin.列表获取(tokens, p)
                if (_light_builtin.字典获取(indent, "种别") == "缩进"):
                    p += 1
                    br = parse_block(tokens, p)
                    elif_body = _light_builtin.列表获取(br, 0)
                    p = _light_builtin.列表获取(br, 1)
                    if (p < _light_builtin.列表长度(tokens)):
                        de = _light_builtin.列表获取(tokens, p)
                        if (_light_builtin.字典获取(de, "种别") == "反缩进"):
                            p += 1
            branch_pair = _light_builtin.列表创建()
            _light_builtin.列表追加(branch_pair, elif_cond_node)
            _light_builtin.列表追加(branch_pair, elif_body)
            _light_builtin.列表追加(elif_branches, branch_pair)
            continue
        break
    else_body = None
    p = skip_newlines(tokens, p)
    if (p < _light_builtin.列表长度(tokens)):
        else_tok = _light_builtin.列表获取(tokens, p)
        if ((_light_builtin.字典获取(else_tok, "种别") == "关键字") and (_light_builtin.字典获取(else_tok, "值") == "否则")):
            p += 1
            if (p < _light_builtin.列表长度(tokens)):
                col = _light_builtin.列表获取(tokens, p)
                if (_light_builtin.字典获取(col, "种别") == "冒号"):
                    p += 1
            p = skip_newlines(tokens, p)
            eb = _light_builtin.列表创建()
            if (p < _light_builtin.列表长度(tokens)):
                indent = _light_builtin.列表获取(tokens, p)
                if (_light_builtin.字典获取(indent, "种别") == "缩进"):
                    p += 1
                    br = parse_block(tokens, p)
                    eb = _light_builtin.列表获取(br, 0)
                    p = _light_builtin.列表获取(br, 1)
                    if (p < _light_builtin.列表长度(tokens)):
                        de = _light_builtin.列表获取(tokens, p)
                        if (_light_builtin.字典获取(de, "种别") == "反缩进"):
                            p += 1
            else_body = eb
    node = make_if_stmt(cond, body, elif_branches, else_body)
    return [node, p]

def parse_paragraph_def(tokens, pos):
    kw = _light_builtin.列表获取(tokens, pos)
    p = (pos + 1)
    name_tok = _light_builtin.列表获取(tokens, p)
    name = _light_builtin.字典获取(name_tok, "值")
    p += 1
    params = _light_builtin.列表创建()
    if (p < _light_builtin.列表长度(tokens)):
        next_tok = _light_builtin.列表获取(tokens, p)
        if ((_light_builtin.字典获取(next_tok, "种别") == "关键字") and (_light_builtin.字典获取(next_tok, "值") == "接收")):
            p += 1
            while (p < _light_builtin.列表长度(tokens)):
                pt = _light_builtin.列表获取(tokens, p)
                pt_type = _light_builtin.字典获取(pt, "种别")
                if (pt_type == "冒号"):
                    break
                if (pt_type == "标识符"):
                    param_name = _light_builtin.字典获取(pt, "值")
                    p += 1
                    default_val = None
                    if (p < _light_builtin.列表长度(tokens)):
                        eq_tok = _light_builtin.列表获取(tokens, p)
                        eq_type = _light_builtin.字典获取(eq_tok, "种别")
                        eq_val = _light_builtin.字典获取(eq_tok, "值")
                        has_default = False
                        if ((eq_type == "赋值") and (eq_val == "=")):
                            has_default = True
                        elif ((eq_type == "关键字") and (eq_val == "等于")):
                            has_default = True
                        if has_default:
                            p += 1
                            default_result = parse_expr(tokens, p)
                            default_val = _light_builtin.列表获取(default_result, 0)
                            p = _light_builtin.列表获取(default_result, 1)
                    param_pair = _light_builtin.列表创建()
                    _light_builtin.列表追加(param_pair, param_name)
                    _light_builtin.列表追加(param_pair, default_val)
                    _light_builtin.列表追加(params, param_pair)
                else:
                    break
                if (p < _light_builtin.列表长度(tokens)):
                    sep = _light_builtin.列表获取(tokens, p)
                    if (_light_builtin.字典获取(sep, "种别") == "逗号"):
                        p += 1
                    else:
                        break
    if (p < _light_builtin.列表长度(tokens)):
        col_tok = _light_builtin.列表获取(tokens, p)
        if (_light_builtin.字典获取(col_tok, "种别") == "冒号"):
            p += 1
    p = skip_newlines(tokens, p)
    body = _light_builtin.列表创建()
    if (p < _light_builtin.列表长度(tokens)):
        indent_tok = _light_builtin.列表获取(tokens, p)
        if (_light_builtin.字典获取(indent_tok, "种别") == "缩进"):
            p += 1
            block_result = parse_block(tokens, p)
            body = _light_builtin.列表获取(block_result, 0)
            p = _light_builtin.列表获取(block_result, 1)
            if (p < _light_builtin.列表长度(tokens)):
                dedent_tok = _light_builtin.列表获取(tokens, p)
                if (_light_builtin.字典获取(dedent_tok, "种别") == "反缩进"):
                    p += 1
    node = make_paragraph_def(name, params, body)
    return [node, p]

def parse_stmt(tokens, pos):
    if (pos >= _light_builtin.列表长度(tokens)):
        return [None, pos]
    tok = _light_builtin.列表获取(tokens, pos)
    ttype = _light_builtin.字典获取(tok, "种别")
    tval = _light_builtin.字典获取(tok, "值")
    if (ttype == "结束"):
        return [None, (pos + 1)]
    if (ttype == "句号"):
        return parse_stmt(tokens, (pos + 1))
    if ((ttype == "关键字") and (tval == "段落")):
        result = parse_paragraph_def(tokens, pos)
        return result
    if ((ttype == "关键字") and (tval == "定义")):
        result = parse_var_decl(tokens, pos)
        return result
    if ((ttype == "关键字") and (tval == "设")):
        result = parse_assign(tokens, pos)
        return result
    if ((ttype == "关键字") and (tval == "返回")):
        result = parse_return_stmt(tokens, pos)
        return result
    if ((ttype == "关键字") and (tval == "如果")):
        result = parse_if(tokens, pos)
        return result
    if ((ttype == "关键字") and (tval == "当")):
        result = parse_while(tokens, pos)
        return result
    if ((ttype == "关键字") and ((tval == "打印") or (tval == "输出"))):
        p = (pos + 1)
        if (p < _light_builtin.列表长度(tokens)):
            next_tok = _light_builtin.列表获取(tokens, p)
            if (_light_builtin.字典获取(next_tok, "种别") == "左括号"):
                name = tval
                args = _light_builtin.列表创建()
                p += 1
                if (p < _light_builtin.列表长度(tokens)):
                    rp_tok = _light_builtin.列表获取(tokens, p)
                    if (_light_builtin.字典获取(rp_tok, "种别") != "右括号"):
                        while True:
                            arg_result = parse_expr(tokens, p)
                            arg = _light_builtin.列表获取(arg_result, 0)
                            p = _light_builtin.列表获取(arg_result, 1)
                            _light_builtin.列表追加(args, arg)
                            if (p < _light_builtin.列表长度(tokens)):
                                sep = _light_builtin.列表获取(tokens, p)
                                if (_light_builtin.字典获取(sep, "种别") == "逗号"):
                                    p += 1
                                    continue
                            break
                if (p < _light_builtin.列表长度(tokens)):
                    rp = _light_builtin.列表获取(tokens, p)
                    if (_light_builtin.字典获取(rp, "种别") == "右括号"):
                        p += 1
                node = make_func_call(name, args)
                return [node, p]
        val_result = parse_expr(tokens, p)
        val = _light_builtin.列表获取(val_result, 0)
        p = _light_builtin.列表获取(val_result, 1)
        node = make_print(val)
        return [node, p]
    if ((ttype == "关键字") and (tval == "跳出")):
        node = make_break()
        return [node, (pos + 1)]
    if ((ttype == "关键字") and (tval == "跳过")):
        node = make_continue()
        return [node, (pos + 1)]
    if (ttype == "标识符"):
        if ((pos + 1) < _light_builtin.列表长度(tokens)):
            next_tok = _light_builtin.列表获取(tokens, (pos + 1))
            nttype = _light_builtin.字典获取(next_tok, "种别")
            ntval = _light_builtin.字典获取(next_tok, "值")
            if (nttype == "关键字"):
                if ((((((ntval == "加上") or (ntval == "减去")) or (ntval == "乘以")) or (ntval == "除以")) or (ntval == "模以")) or (ntval == "幂以")):
                    return parse_compound_assign(tokens, pos, ntval)
                if (ntval == "等于"):
                    var_name = tval
                    p = (pos + 2)
                    result = parse_expr(tokens, p)
                    node = make_var_decl(var_name, _light_builtin.列表获取(result, 0))
                    return [node, _light_builtin.列表获取(result, 1)]
        if ((pos + 1) < _light_builtin.列表长度(tokens)):
            next_tok = _light_builtin.列表获取(tokens, (pos + 1))
            nttype = _light_builtin.字典获取(next_tok, "种别")
            if ((((((nttype == "字符串") or (nttype == "数字")) or (nttype == "标识符")) or (nttype == "左中括号")) or (nttype == "左书名号")) or (nttype == "模板字符串")):
                name = tval
                args = _light_builtin.列表创建()
                p = (pos + 1)
                while True:
                    arg_result = parse_expr(tokens, p)
                    arg = _light_builtin.列表获取(arg_result, 0)
                    p = _light_builtin.列表获取(arg_result, 1)
                    _light_builtin.列表追加(args, arg)
                    if (p < _light_builtin.列表长度(tokens)):
                        peek_tok = _light_builtin.列表获取(tokens, p)
                        pt = _light_builtin.字典获取(peek_tok, "种别")
                        if ((((((pt == "字符串") or (pt == "数字")) or (pt == "标识符")) or (pt == "左中括号")) or (pt == "左书名号")) or (pt == "模板字符串")):
                            continue
                    break
                node = make_func_call(name, args)
                return [node, p]
    result = parse_expr(tokens, pos)
    node = make_expr_stmt(_light_builtin.列表获取(result, 0))
    return [node, _light_builtin.列表获取(result, 1)]

def parse(tokens):
    stmts = _light_builtin.列表创建()
    pos = 0
    tok_count = _light_builtin.列表长度(tokens)
    while (pos < tok_count):
        p = skip_newlines(tokens, pos)
        if (p >= tok_count):
            break
        tok = _light_builtin.列表获取(tokens, p)
        ttype = _light_builtin.字典获取(tok, "种别")
        tval = _light_builtin.字典获取(tok, "值")
        if (ttype == "结束"):
            break
        if (ttype == "注释"):
            pos = (p + 1)
            continue
        if ((ttype == "关键字") and (tval == "导出")):
            while (p < tok_count):
                t = _light_builtin.列表获取(tokens, p)
                if ((_light_builtin.字典获取(t, "种别") == "换行") or (_light_builtin.字典获取(t, "种别") == "句号")):
                    pos = (p + 1)
                    break
                p += 1
            continue
        if ((ttype == "关键字") and (tval == "导入")):
            pos = (p + 1)
            continue
        if ((ttype == "关键字") and (tval == "从")):
            while (p < tok_count):
                t = _light_builtin.列表获取(tokens, p)
                if ((_light_builtin.字典获取(t, "种别") == "换行") or (_light_builtin.字典获取(t, "种别") == "句号")):
                    pos = (p + 1)
                    break
                p += 1
            continue
        result = parse_stmt(tokens, p)
        stmt = _light_builtin.列表获取(result, 0)
        if (stmt != None):
            _light_builtin.列表追加(stmts, stmt)
        pos = _light_builtin.列表获取(result, 1)
    program = make_program(stmts)
    return program

def init_generator():
    state = _light_builtin.字典创建()
    _light_builtin.字典设置(state, "lines", _light_builtin.列表创建())
    _light_builtin.字典设置(state, "indent", 0)
    _light_builtin.字典设置(state, "indent_str", "    ")
    return state

def add_line(state, line):
    lines = _light_builtin.字典获取(state, "lines")
    indent = _light_builtin.字典获取(state, "indent")
    indent_str = _light_builtin.字典获取(state, "indent_str")
    line_str = _light_builtin.转字符串(line)
    prefix = ""
    i = 0
    while (i < indent):
        prefix = (prefix + indent_str)
        i += 1
    _light_builtin.列表追加(lines, (prefix + line_str))

def indent_push(state):
    indent = _light_builtin.字典获取(state, "indent")
    _light_builtin.字典设置(state, "indent", (indent + 1))

def indent_pop(state):
    indent = _light_builtin.字典获取(state, "indent")
    if (indent > 0):
        _light_builtin.字典设置(state, "indent", (indent - 1))

def get_output(state):
    lines = _light_builtin.字典获取(state, "lines")
    result = ""
    i = 0
    while (i < _light_builtin.列表长度(lines)):
        if (i > 0):
            result = (result + "\n")
        result = (result + _light_builtin.列表获取(lines, i))
        i += 1
    return result

def map_builtin(name):
    if (name == "打印"):
        return "_light_builtin.打印"
    if (name == "输出"):
        return "_light_builtin.打印"
    if ((name == "输入") or (name == "读取")):
        return "_light_builtin.读取"
    if (name == "转字符串"):
        return "_light_builtin.转字符串"
    if (name == "转整数"):
        return "_light_builtin.转整数"
    if (name == "转浮点"):
        return "_light_builtin.转浮点"
    if ((name == "列表创建") or (name == "列")):
        return "_light_builtin.列表创建"
    if (name == "列表长度"):
        return "_light_builtin.列表长度"
    if (name == "列表获取"):
        return "_light_builtin.列表获取"
    if (name == "列表追加"):
        return "_light_builtin.列表追加"
    if (name == "列表弹出"):
        return "_light_builtin.列表弹出"
    if (name == "列表包含"):
        return "_light_builtin.列表包含"
    if ((name == "字典创建") or (name == "字典")):
        return "_light_builtin.字典创建"
    if (name == "字典设置"):
        return "_light_builtin.字典设置"
    if (name == "字典获取"):
        return "_light_builtin.字典获取"
    if (name == "字典包含键"):
        return "_light_builtin.字典包含键"
    if (name == "字典键列表"):
        return "_light_builtin.字典键列表"
    if ((name == "字典值列表") or (name == "字典值")):
        return "_light_builtin.字典值列表"
    if ((name == "字典项列表") or (name == "字典项")):
        return "_light_builtin.字典项列表"
    if (name == "字典删除"):
        return "_light_builtin.字典删除"
    if (name == "字符串长度"):
        return "_light_builtin.字符串长度"
    if (name == "字符串获取"):
        return "_light_builtin.字符串获取"
    if (name == "截取"):
        return "_light_builtin.截取"
    if ((name == "分割字符串") or (name == "分割")):
        return "_light_builtin.分割字符串"
    if ((name == "连接字符串") or (name == "连接")):
        return "_light_builtin.连接字符串"
    if ((name == "替换字符串") or (name == "替换")):
        return "_light_builtin.替换字符串"
    if ((name == "去除空白") or (name == "去空格")):
        return "_light_builtin.去除空白"
    if ((name == "列表排序") or (name == "排序")):
        return "_light_builtin.列表排序"
    if ((name == "列表反转") or (name == "反转")):
        return "_light_builtin.列表反转"
    if ((name == "列表创建") or (name == "列")):
        return "_light_builtin.列表创建"
    if (name == "是整数"):
        return "_light_builtin.是整数"
    if (name == "是浮点"):
        return "_light_builtin.是浮点"
    if (name == "是字符串"):
        return "_light_builtin.是字符串"
    if (name == "是列表"):
        return "_light_builtin.是列表"
    if (name == "是字典"):
        return "_light_builtin.是字典"
    if (name == "是空"):
        return "_light_builtin.是空"
    if (name == "随机整数"):
        return "_light_builtin.随机整数"
    if (name == "随机浮点"):
        return "_light_builtin.随机浮点"
    if (name == "随机选择"):
        return "_light_builtin.随机选择"
    if (name == "阶乘"):
        return "_light_builtin.阶乘"
    if (name == "平均数"):
        return "_light_builtin.平均数"
    if (name == "求和"):
        return "_light_builtin.求和"
    if (name == "时间戳"):
        return "_light_builtin.时间戳"
    if (name == "格式化时间"):
        return "_light_builtin.格式化时间"
    if (name == "读取文件"):
        return "_light_builtin.读取文件"
    if (name == "写入文件"):
        return "_light_builtin.写入文件"
    if (name == "追加文件"):
        return "_light_builtin.追加文件"
    if (name == "文件存在"):
        return "_light_builtin.文件存在"
    if (name == "目录存在"):
        return "_light_builtin.目录存在"
    if (name == "创建目录"):
        return "_light_builtin.创建目录"
    if (name == "圆周率"):
        return "_light_builtin.圆周率"
    if (name == "自然常数"):
        return "_light_builtin.自然常数"
    if (name == "创建令牌"):
        return "创建令牌"
    if (name == "_读文件"):
        return "_light_builtin._读文件"
    if (name == "参数列表"):
        return "sys.argv"
    return name

def gen_expr(state, node):
    node_type = _light_builtin.列表获取(node, 0)
    if (node_type == "number"):
        return _light_builtin.列表获取(node, 1)
    if (node_type == "string"):
        引号 = "'"
        原始值 = _light_builtin.列表获取(node, 1)
        转义值 = ""
        k = 0
        while (k < _light_builtin.字符串长度(原始值)):
            ch = _light_builtin.字符串获取(原始值, k)
            if (ch == "\\"):
                转义值 = (转义值 + "\\\\")
            elif (ch == "\n"):
                转义值 = (转义值 + "\\n")
            elif (ch == "\t"):
                转义值 = (转义值 + "\\t")
            elif (ch == "'"):
                转义值 = (转义值 + "\\'")
            else:
                转义值 = (转义值 + ch)
            k += 1
        return ((引号 + 转义值) + 引号)
    if (node_type == "template_string"):
        原始值 = _light_builtin.列表获取(node, 1)
        转义值 = ""
        k = 0
        while (k < _light_builtin.字符串长度(原始值)):
            ch = _light_builtin.字符串获取(原始值, k)
            if (ch == "\\"):
                转义值 = (转义值 + "\\\\")
            elif (ch == "\n"):
                转义值 = (转义值 + "\\n")
            elif (ch == "\t"):
                转义值 = (转义值 + "\\t")
            elif (ch == "\""):
                转义值 = (转义值 + "\\\"")
            else:
                转义值 = (转义值 + ch)
            k += 1
        return (("f\"" + 转义值) + "\"")
    if (node_type == "boolean"):
        val = _light_builtin.列表获取(node, 1)
        if (val == "真"):
            return "True"
        return "False"
    if (node_type == "null"):
        return "None"
    if (node_type == "identifier"):
        return _light_builtin.列表获取(node, 1)
    if (node_type == "func_call"):
        name = _light_builtin.列表获取(node, 1)
        mapped = map_builtin(name)
        args = _light_builtin.列表获取(node, 2)
        result = (mapped + "(")
        i = 0
        while (i < _light_builtin.列表长度(args)):
            if (i > 0):
                result = (result + ", ")
            arg_node = _light_builtin.列表获取(args, i)
            arg_code = gen_expr(state, arg_node)
            result = (result + arg_code)
            i += 1
        result = (result + ")")
        return result
    if (node_type == "binary_op"):
        op = _light_builtin.列表获取(node, 1)
        left = gen_expr(state, _light_builtin.列表获取(node, 2))
        right = gen_expr(state, _light_builtin.列表获取(node, 3))
        py_op = op
        if ((op == "加") or (op == "+")):
            py_op = "+"
        elif ((op == "减") or (op == "-")):
            py_op = "-"
        elif ((op == "乘") or (op == "*")):
            py_op = "*"
        elif ((op == "除") or (op == "/")):
            py_op = "/"
        elif ((op == "模") or (op == "%")):
            py_op = "%"
        elif ((op == "幂") or (op == "^")):
            py_op = "**"
        elif (op == "大于"):
            py_op = ">"
        elif (op == "小于"):
            py_op = "<"
        elif ((op == "等于") or (op == "==")):
            py_op = "=="
        elif (op == "不等于"):
            py_op = "!="
        elif (op == "大于等于"):
            py_op = ">="
        elif (op == "小于等于"):
            py_op = "<="
        elif ((op == "且") or (op == "与")):
            py_op = "and"
        elif (op == "或"):
            py_op = "or"
        return (((((("(" + left) + " ") + py_op) + " ") + right) + ")")
    if (node_type == "unary_op"):
        op = _light_builtin.列表获取(node, 1)
        operand = gen_expr(state, _light_builtin.列表获取(node, 2))
        if ((op == "非") or (op == "!")):
            return ("not " + operand)
        return (op + operand)
    if (node_type == "list_literal"):
        elems = _light_builtin.列表获取(node, 1)
        result = "["
        i = 0
        while (i < _light_builtin.列表长度(elems)):
            if (i > 0):
                result = (result + ", ")
            elem_code = gen_expr(state, _light_builtin.列表获取(elems, i))
            result = (result + elem_code)
            i += 1
        return (result + "]")
    if (node_type == "dict_literal"):
        pairs = _light_builtin.列表获取(node, 1)
        result = "{"
        i = 0
        while (i < _light_builtin.列表长度(pairs)):
            if (i > 0):
                result = (result + ", ")
            pair = _light_builtin.列表获取(pairs, i)
            key_code = gen_expr(state, _light_builtin.列表获取(pair, 0))
            val_code = gen_expr(state, _light_builtin.列表获取(pair, 1))
            result = (((result + key_code) + ": ") + val_code)
            i += 1
        return (result + "}")
    if (node_type == "member_access"):
        obj = gen_expr(state, _light_builtin.列表获取(node, 1))
        prop = _light_builtin.列表获取(node, 2)
        return ((obj + ".") + prop)
    return "None"

def gen_stmt(state, node):
    node_type = _light_builtin.列表获取(node, 0)
    if (node_type == "var_decl"):
        name = _light_builtin.列表获取(node, 1)
        value = gen_expr(state, _light_builtin.列表获取(node, 2))
        add_line(state, ((name + " = ") + value))
        return
    if (node_type == "assign"):
        name = _light_builtin.列表获取(node, 1)
        value = gen_expr(state, _light_builtin.列表获取(node, 2))
        add_line(state, ((name + " = ") + value))
        return
    if (node_type == "compound_assign"):
        name = _light_builtin.列表获取(node, 1)
        op = _light_builtin.列表获取(node, 2)
        value = gen_expr(state, _light_builtin.列表获取(node, 3))
        py_op = "+"
        if (op == "加上"):
            py_op = "+"
        elif (op == "减去"):
            py_op = "-"
        elif (op == "乘以"):
            py_op = "*"
        elif (op == "除以"):
            py_op = "/"
        elif (op == "模以"):
            py_op = "%"
        elif (op == "幂以"):
            py_op = "**"
        add_line(state, ((((name + " ") + py_op) + "= ") + value))
        return
    if (node_type == "return"):
        value = _light_builtin.列表获取(node, 1)
        if (value == None):
            add_line(state, "return")
        else:
            add_line(state, ("return " + gen_expr(state, value)))
        return
    if (node_type == "if_stmt"):
        cond = gen_expr(state, _light_builtin.列表获取(node, 1))
        body = _light_builtin.列表获取(node, 2)
        elif_branches = _light_builtin.列表获取(node, 3)
        else_body = _light_builtin.列表获取(node, 4)
        add_line(state, (("if " + cond) + ":"))
        indent_push(state)
        i = 0
        while (i < _light_builtin.列表长度(body)):
            gen_stmt(state, _light_builtin.列表获取(body, i))
            i += 1
        indent_pop(state)
        j = 0
        while (j < _light_builtin.列表长度(elif_branches)):
            branch = _light_builtin.列表获取(elif_branches, j)
            elif_cond = gen_expr(state, _light_builtin.列表获取(branch, 0))
            elif_body = _light_builtin.列表获取(branch, 1)
            add_line(state, (("elif " + elif_cond) + ":"))
            indent_push(state)
            k = 0
            while (k < _light_builtin.列表长度(elif_body)):
                gen_stmt(state, _light_builtin.列表获取(elif_body, k))
                k += 1
            indent_pop(state)
            j += 1
        if (else_body != None):
            add_line(state, "else:")
            indent_push(state)
            m = 0
            while (m < _light_builtin.列表长度(else_body)):
                gen_stmt(state, _light_builtin.列表获取(else_body, m))
                m += 1
            indent_pop(state)
        return
    if (node_type == "while_loop"):
        cond = gen_expr(state, _light_builtin.列表获取(node, 1))
        body = _light_builtin.列表获取(node, 2)
        add_line(state, (("while " + cond) + ":"))
        indent_push(state)
        i = 0
        while (i < _light_builtin.列表长度(body)):
            gen_stmt(state, _light_builtin.列表获取(body, i))
            i += 1
        indent_pop(state)
        return
    if (node_type == "for_each"):
        var_name = _light_builtin.列表获取(node, 1)
        collection = gen_expr(state, _light_builtin.列表获取(node, 2))
        body = _light_builtin.列表获取(node, 3)
        add_line(state, (((("for " + var_name) + " in ") + collection) + ":"))
        indent_push(state)
        i = 0
        while (i < _light_builtin.列表长度(body)):
            gen_stmt(state, _light_builtin.列表获取(body, i))
            i += 1
        indent_pop(state)
        return
    if (node_type == "print"):
        value = _light_builtin.列表获取(node, 1)
        val_code = gen_expr(state, value)
        add_line(state, (("print(" + val_code) + ")"))
        return
    if (node_type == "func_call"):
        code = gen_expr(state, node)
        add_line(state, code)
        return
    if (node_type == "break"):
        add_line(state, "break")
        return
    if (node_type == "continue"):
        add_line(state, "continue")
        return
    if (node_type == "paragraph_def"):
        name = _light_builtin.列表获取(node, 1)
        params = _light_builtin.列表获取(node, 2)
        body = _light_builtin.列表获取(node, 3)
        param_str = ""
        i = 0
        while (i < _light_builtin.列表长度(params)):
            if (i > 0):
                param_str = (param_str + ", ")
            param_pair = _light_builtin.列表获取(params, i)
            pname = _light_builtin.列表获取(param_pair, 0)
            pdefault = _light_builtin.列表获取(param_pair, 1)
            param_str = (param_str + pname)
            if (pdefault != None):
                default_code = gen_expr(state, pdefault)
                param_str = ((param_str + "=") + default_code)
            i += 1
        add_line(state, (((("def " + name) + "(") + param_str) + "):"))
        indent_push(state)
        j = 0
        while (j < _light_builtin.列表长度(body)):
            gen_stmt(state, _light_builtin.列表获取(body, j))
            j += 1
        indent_pop(state)
        add_line(state, "")
        return
    if (node_type == "expr_stmt"):
        expr = _light_builtin.列表获取(node, 1)
        code = gen_expr(state, expr)
        add_line(state, code)
        return
    return

def gen_header(state):
    add_line(state, "# Generated by Light bootstrap compiler")
    add_line(state, "import sys")
    add_line(state, "import types")
    add_line(state, "_light_builtin = types.ModuleType('_light_builtin')")
    add_line(state, "_light_builtin.打印 = print")
    add_line(state, "_light_builtin.转字符串 = str")
    add_line(state, "_light_builtin.转整数 = int")
    add_line(state, "_light_builtin.列表创建 = list")
    add_line(state, "_light_builtin.列表长度 = len")
    add_line(state, "_light_builtin.列表获取 = lambda lst, i: lst[i]")
    add_line(state, "_light_builtin.列表追加 = lambda lst, item: lst.append(item)")
    add_line(state, "_light_builtin.列表弹出 = lambda lst: lst.pop()")
    add_line(state, "_light_builtin.列表包含 = lambda lst, item: item in lst")
    add_line(state, "_light_builtin.字典创建 = dict")
    左花 = "{"
    右花 = "}"
    add_line(state, (((("_light_builtin.字典设置 = lambda d, k, v: d.update(" + 左花) + "k: v") + 右花) + ")"))
    add_line(state, "_light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)")
    add_line(state, "_light_builtin.字典包含键 = lambda d, k: k in d")
    add_line(state, "_light_builtin.字典键列表 = lambda d: list(d.keys())")
    add_line(state, "_light_builtin.字符串长度 = len")
    add_line(state, "_light_builtin.字符串获取 = lambda s, i: s[i]")
    add_line(state, "_light_builtin.截取 = lambda s, start, end: s[start:end]")
    add_line(state, "_light_builtin.分割字符串 = lambda s, sep=' ': s.split(sep)")
    add_line(state, "_light_builtin.连接字符串 = lambda parts, sep='': sep.join(parts)")
    add_line(state, "_light_builtin.替换字符串 = lambda s, old, new: s.replace(old, new)")
    add_line(state, "_light_builtin.去除空白 = lambda s: s.strip()")
    add_line(state, "_light_builtin.列表排序 = lambda lst, reverse=False: lst.sort(reverse=reverse)")
    add_line(state, "_light_builtin.列表反转 = lambda lst: lst.reverse()")
    add_line(state, "_light_builtin.是整数 = lambda x: isinstance(x, int)")
    add_line(state, "_light_builtin.是浮点 = lambda x: isinstance(x, float)")
    add_line(state, "_light_builtin.是字符串 = lambda x: isinstance(x, str)")
    add_line(state, "_light_builtin.是列表 = lambda x: isinstance(x, list)")
    add_line(state, "_light_builtin.是字典 = lambda x: isinstance(x, dict)")
    add_line(state, "_light_builtin.是空 = lambda x: x is None")
    add_line(state, "_light_builtin.字典值列表 = lambda d: list(d.values())")
    add_line(state, "_light_builtin.字典项列表 = lambda d: list(d.items())")
    add_line(state, "_light_builtin.字典删除 = lambda d, k: d.pop(k, None)")
    add_line(state, "_light_builtin.随机整数 = lambda a, b: __import__('random').randint(a, b)")
    add_line(state, "_light_builtin.随机浮点 = lambda: __import__('random').random()")
    add_line(state, "_light_builtin.随机选择 = lambda lst: __import__('random').choice(lst)")
    add_line(state, "_light_builtin.阶乘 = lambda n: __import__('math').factorial(n)")
    add_line(state, "_light_builtin.平均数 = lambda data: sum(data) / len(data) if data else 0")
    add_line(state, "_light_builtin.求和 = lambda data: sum(data)")
    add_line(state, "_light_builtin.时间戳 = lambda: __import__('time').time()")
    add_line(state, "_light_builtin.格式化时间 = lambda ts, fmt='%Y-%m-%d %H:%M:%S': __import__('time').strftime(fmt, __import__('time').localtime(ts))")
    add_line(state, "_light_builtin.读取文件 = lambda path: open(path, 'r', encoding='utf-8').read()")
    add_line(state, "_light_builtin.写入文件 = lambda path, content: open(path, 'w', encoding='utf-8').write(content)")
    add_line(state, "_light_builtin.追加文件 = lambda path, content: open(path, 'a', encoding='utf-8').write(content)")
    add_line(state, "_light_builtin.文件存在 = lambda path: __import__('os').path.isfile(path)")
    add_line(state, "_light_builtin.目录存在 = lambda path: __import__('os').path.isdir(path)")
    add_line(state, "_light_builtin.创建目录 = lambda path: __import__('os').makedirs(path, exist_ok=True)")
    add_line(state, "_light_builtin.圆周率 = lambda: __import__('math').pi")
    add_line(state, "_light_builtin.自然常数 = lambda: __import__('math').e")
    add_line(state, "_light_builtin._读文件 = lambda path: open(path, 'r', encoding='utf-8').read()")
    add_line(state, "")
    add_line(state, "# 全局绑定：内建函数别名（模块级别，在函数定义之前）")
    add_line(state, "字符串获取 = _light_builtin.字符串获取")
    add_line(state, "字符串长度 = _light_builtin.字符串长度")
    add_line(state, "截取 = _light_builtin.截取")
    add_line(state, "")
    add_line(state, "")

def gen_module_init(state):
    add_line(state, "# 全局绑定：内建函数别名")
    add_line(state, "字符串获取 = _light_builtin.字符串获取")
    add_line(state, "字符串长度 = _light_builtin.字符串长度")
    add_line(state, "截取 = _light_builtin.截取")
    add_line(state, "")

def generate(ast_node):
    stmts_state = init_generator()
    node_type = _light_builtin.列表获取(ast_node, 0)
    if (node_type == "program"):
        stmts = _light_builtin.列表获取(ast_node, 1)
        i = 0
        while (i < _light_builtin.列表长度(stmts)):
            gen_stmt(stmts_state, _light_builtin.列表获取(stmts, i))
            i += 1
    stmts_result = get_output(stmts_state)
    state = init_generator()
    gen_header(state)
    gen_module_init(state)
    header_result = get_output(state)
    return ((header_result + "\n") + stmts_result)

def compile_source(source):
    tokens = 词法分析(source)
    ast = parse(tokens)
    py_code = generate(ast)
    return py_code

def compile_file(filepath):
    content = _light_builtin._读文件(filepath)
    return compile_source(content)

def main(filepath):
    py_code = compile_file(filepath)
    print(py_code)
