"""测试 Light 编写的解析器是否正确处理连续的 如果 语句"""
import sys
import os
import types

_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _script_dir)


def _setup_light_builtin():
    _light_builtin = types.ModuleType('_light_builtin')
    _light_builtin.打印 = print
    _light_builtin.输出 = print
    _light_builtin.转字符串 = str
    _light_builtin.转整数 = int
    _light_builtin.转浮点 = float
    _light_builtin.列表创建 = list
    _light_builtin.列表长度 = len
    _light_builtin.列表获取 = lambda lst, i: lst[i]
    _light_builtin.列表追加 = lambda lst, item: lst.append(item)
    _light_builtin.列表弹出 = lambda lst: lst.pop()
    _light_builtin.列表包含 = lambda lst, item: item in lst
    _light_builtin.字典创建 = dict
    _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
    _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
    _light_builtin.字典包含键 = lambda d, k: k in d
    _light_builtin.字典键列表 = lambda d: list(d.keys())
    _light_builtin.字典值列表 = lambda d: list(d.values())
    _light_builtin.字典项列表 = lambda d: list(d.items())
    _light_builtin.字典删除 = lambda d, k: d.pop(k, None)
    _light_builtin.字符串长度 = len
    _light_builtin.字符串获取 = lambda s, i: s[i]
    _light_builtin.截取 = lambda s, start, end: s[start:end]
    _light_builtin.分割字符串 = lambda s, sep=' ': s.split(sep)
    _light_builtin.连接字符串 = lambda parts, sep='': sep.join(parts)
    _light_builtin.替换字符串 = lambda s, old, new: s.replace(old, new)
    _light_builtin.去除空白 = lambda s: s.strip()
    _light_builtin.列表排序 = lambda lst, reverse=False: lst.sort(reverse=reverse)
    _light_builtin.列表反转 = lambda lst: lst.reverse()
    _light_builtin.是整数 = lambda x: isinstance(x, int) and not isinstance(x, bool)
    _light_builtin.是浮点 = lambda x: isinstance(x, float)
    _light_builtin.是字符串 = lambda x: isinstance(x, str)
    _light_builtin.是列表 = lambda x: isinstance(x, list)
    _light_builtin.是字典 = lambda x: isinstance(x, dict)
    _light_builtin.是空 = lambda x: x is None
    _light_builtin.随机整数 = lambda a, b: __import__('random').randint(a, b)
    _light_builtin.随机浮点 = lambda: __import__('random').random()
    _light_builtin.随机选择 = lambda lst: __import__('random').choice(lst)
    _light_builtin._读文件 = lambda path: open(path, 'r', encoding='utf-8').read()
    _light_builtin.范围 = lambda *args: list(range(*args))
    _light_builtin.绝对值 = abs
    _light_builtin.求和 = sum
    _light_builtin.排序 = sorted
    _light_builtin.反转 = lambda lst: list(reversed(lst))
    _light_builtin.长度 = len
    _light_builtin.类型 = lambda x: type(x).__name__
    return _light_builtin


def main():
    # 加载自举编译器 (bootstrap_v3_gen.py)
    gen_path = os.path.join(_script_dir, 'bootstrap_v3_gen.py')
    with open(gen_path, 'r', encoding='utf-8') as f:
        gen_code = f.read()

    _light_builtin = _setup_light_builtin()
    namespace = {'_light_builtin': _light_builtin}
    exec(gen_code, namespace)

    # 测试用例：模仿 gen_stmt 的复杂结构
    test_source = """段落 gen_stmt 接收 state, node：
  定义 node_type 等于 列表获取(node, 0)
  如果 node_type 等于 "var_decl"：
    定义 name 等于 列表获取(node, 1)
    定义 value 等于 gen_expr(state, 列表获取(node, 2))
    add_line(state, name 加 " = " 加 value)
    返回
  如果 node_type 等于 "paragraph_def"：
    定义 name 等于 列表获取(node, 1)
    定义 params 等于 列表获取(node, 2)
    定义 body 等于 列表获取(node, 3)
    定义 param_str 等于 ""
    定义 i 等于 0
    当 i 小于 列表长度(params)：
      如果 i 大于 0：
        定义 param_str 等于 param_str 加 ", "
      定义 param_pair 等于 列表获取(params, i)
      定义 pname 等于 列表获取(param_pair, 0)
      定义 param_str 等于 param_str 加 pname
      i 加上 1
    add_line(state, "def " 加 name 加 "(" 加 param_str 加 "):")
    indent_push(state)
    定义 j 等于 0
    当 j 小于 列表长度(body)：
      gen_stmt(state, 列表获取(body, j))
      j 加上 1
    indent_pop(state)
    返回
  如果 node_type 等于 "expr_stmt"：
    定义 expr 等于 列表获取(node, 1)
    定义 code 等于 gen_expr(state, expr)
    add_line(state, code)
    返回
  返回

段落 gen_header 接收 state：
  add_line(state, "header")
  返回
"""

    # 用自举编译器的 lexer + parser 解析
    词法分析 = namespace.get('词法分析')
    parse = namespace.get('parse')

    if not 词法分析:
        print("错误：找不到 词法分析 函数")
        # 打印可用的函数名
        keys = [k for k in namespace.keys() if not k.startswith('_') and callable(namespace[k])]
        print("可用函数:", keys[:20])
        return

    if not parse:
        print("错误：找不到 parse 函数")
        return

    tokens = 词法分析(test_source)
    print(f"Token 数量: {len(tokens)}")
    print()

    # 打印 token 流（只打印关键部分）
    print("=== Token 流 ===")
    for i, tok in enumerate(tokens):
        ttype = tok.get('种别') if isinstance(tok, dict) else tok[0]
        tval = tok.get('值') if isinstance(tok, dict) else tok[1]
        if ttype in ('缩进', '反缩进', '换行', '结束'):
            print(f"  [{i}] {ttype}: {repr(tval)}")
        elif ttype == '注释':
            pass  # skip comments
        else:
            print(f"  [{i}] {ttype}: {repr(tval)}")
    print()

    # 解析
    ast = parse(tokens)
    print("=== AST 结构 ===")
    print_ast(ast, 0)


def print_ast(node, indent):
    if not isinstance(node, list):
        print("  " * indent + repr(node))
        return
    if len(node) == 0:
        print("  " * indent + "[]")
        return
    head = node[0]
    if isinstance(head, str):
        print("  " * indent + f"[{head}")
        for item in node[1:]:
            print_ast(item, indent + 1)
        print("  " * indent + "]")
    else:
        print("  " * indent + "[")
        for item in node:
            print_ast(item, indent + 1)
        print("  " * indent + "]")


if __name__ == '__main__':
    main()
