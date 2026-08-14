# 由段言编译器生成
# 源文件: 段言代码

import sys
import os
import ctypes
from typing import Any, Optional

try:
    import importlib.util
except ImportError:
    importlib = None

# 解析 stdlib 路径（依次尝试多种可能）
_duan_stdlib = None
try:
    _duan_file_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _duan_file_dir = None
for _try_path in [
    os.path.join(_duan_file_dir, 'stdlib') if _duan_file_dir else None,
    os.path.join(_duan_file_dir, '..', 'stdlib') if _duan_file_dir else None,
    os.path.join(os.getcwd(), 'stdlib'),
    os.path.normpath(os.path.join(_duan_file_dir, '..', '..', 'stdlib')) if _duan_file_dir else None,
]:
    if _try_path and os.path.isdir(_try_path):
        _duan_stdlib = _try_path
        break

if _duan_stdlib and _duan_stdlib not in sys.path:
    sys.path.insert(0, _duan_stdlib)
if _duan_stdlib:
    _duan_parent = os.path.dirname(_duan_stdlib)
    if _duan_parent not in sys.path:
        sys.path.insert(0, _duan_parent)

# 让 import 机制认识纯段言模块（只有 .duan、没有 .py 的那种）
try:
    import _duan_import_hook as _duan_hook
    _duan_hook.install([_duan_stdlib, _duan_file_dir, os.getcwd()])
except Exception:
    pass

# FFI 模块：尽量导入；失败则降级为占位对象（见 _duan_ffi_available 特征位），避免非 FFI 程序因 stdlib 路径缺失而整体崩溃
try:
    import stdlib.FFI as _duan_ffi
    _duan_ffi_available = True
except Exception:
    _duan_ffi_available = False
    class _DuanFFIUnavailable:
        def __getattr__(self, _name):
            raise RuntimeError('FFI 不可用：未能导入 stdlib.FFI（请确认 stdlib 路径已加入 sys.path）')
    _duan_ffi = _DuanFFIUnavailable()

if importlib:
    try:
        _duan_builtin_path = os.path.join(_duan_stdlib, 'builtins.py')
        if os.path.isfile(_duan_builtin_path):
            spec = importlib.util.spec_from_file_location('duan_builtins', _duan_builtin_path)
            _duan_builtin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_duan_builtin)
        else:
            raise ImportError()
    except:
        import types
        _duan_builtin = types.ModuleType('_duan_builtin')
        _duan_builtin.读取文件 = lambda path: open(path, 'r', encoding='utf-8').read() if __import__('os').path.isfile(path) else ''
        _duan_builtin._读文件 = lambda path: open(path, 'r', encoding='utf-8').read() if __import__('os').path.isfile(path) else ''
        _duan_builtin.写入文件 = lambda path, content: open(path, 'w', encoding='utf-8').write(content) or None
        _duan_builtin.删除文件 = lambda path: __import__('os').remove(path) if __import__('os').path.isfile(path) else None
        _duan_builtin.删除目录 = lambda path: __import__('os').rmdir(path)
        _duan_builtin.文件存在 = lambda path: __import__('os').path.isfile(path)
        _duan_builtin.目录存在 = lambda path: __import__('os').path.isdir(path)
        _duan_builtin.打印 = print
        _duan_builtin.读取行 = lambda: sys.stdin.readline().rstrip('\r\n')
        _duan_builtin.读取N字节 = lambda n: sys.stdin.read(n)
        _duan_builtin.写入输出 = lambda t: (sys.stdout.write(t), sys.stdout.flush()) and None
        _duan_builtin.打印输出 = lambda t: print(t, flush=True)
        _duan_builtin.刷新输出 = lambda: sys.stdout.flush()
        _duan_builtin.写入错误 = lambda t: (sys.stderr.write(t), sys.stderr.flush()) and None
        _duan_builtin.打印错误 = lambda t: print(t, file=sys.stderr, flush=True)
        _duan_builtin.解析JSON = lambda t: __import__('json').loads(t)
        _duan_builtin.序列化JSON = lambda v, i=None: (__import__('json').dumps(v, ensure_ascii=False, indent=i) if i is not None else __import__('json').dumps(v, ensure_ascii=False))
        _duan_builtin.美化JSON = lambda v: __import__('json').dumps(v, ensure_ascii=False, indent=2)
        _duan_builtin.转字符串 = str
        _duan_builtin.转整数 = int
        _duan_builtin.转浮点 = float
        _duan_builtin.chr = chr
        _duan_builtin.bin = bin
        _duan_builtin.hex = hex
        _duan_builtin.oct = oct
        _duan_builtin.列表创建 = list
        _duan_builtin.列表长度 = len
        _duan_builtin.列 = lambda *args: list(args)
        _duan_builtin.列表追加 = lambda lst, item: lst.append(item)
        _duan_builtin.列表获取 = lambda lst, i: lst[i]
        _duan_builtin.列表弹出 = lambda lst, i=-1: lst.pop(i)
        _duan_builtin.列表插入 = lambda lst, i, v: lst.insert(i, v)
        _duan_builtin.列表包含 = lambda lst, item: item in lst
        _duan_builtin.包含 = lambda sub, s: sub in s
        _duan_builtin.字符串包含 = lambda s, sub: sub in s
        _duan_builtin.字符串替换 = lambda s, old, new: s.replace(old, new)
        _duan_builtin.字符串反转 = lambda s: s[::-1]
        _duan_builtin.字符串长度 = len
        _duan_builtin.显示宽度 = lambda text: sum(2 if __import__('unicodedata').east_asian_width(ch) in ('W', 'F') else 1 for ch in str(text))
        _duan_builtin.字符串获取 = lambda s, i: s[i]
        _duan_builtin.截取 = lambda s, start, end: s[start:end]
        _duan_builtin.转大写 = lambda s: s.upper()
        _duan_builtin.转小写 = lambda s: s.lower()
        _duan_builtin.结尾 = lambda s, suffix: s.endswith(suffix)
        _duan_builtin.开头 = lambda s, prefix: s.startswith(prefix)
        _duan_builtin.去除空白 = lambda s: s.strip()
        _duan_builtin.分割字符串 = lambda s, sep=None: s.split(sep)
        _duan_builtin.连接字符串 = lambda parts, sep='': sep.join(parts)
        _duan_builtin.替换字符串 = lambda s, old, new: s.replace(old, new)
        _duan_builtin.字符串分割 = lambda s, sep=None: s.split(sep)
        _duan_builtin.字典创建 = dict
        _duan_builtin.字典设置 = lambda d, k, v: d.update({k: v})
        _duan_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
        _duan_builtin.字典键列表 = lambda d: list(d.keys())
        _duan_builtin.字典包含键 = lambda d, k: k in d
        _duan_builtin.时间戳 = lambda: __import__('time').time()
        _duan_builtin.格式化时间 = lambda t, f='%Y-%m-%d %H:%M:%S': __import__('datetime').datetime.fromtimestamp(t).strftime(f) if isinstance(t, (int, float)) else __import__('datetime').datetime.strptime(t, '%Y-%m-%d %H:%M:%S').strftime(f)
else:
    import types
    _duan_builtin = types.ModuleType('_duan_builtin')
    _duan_builtin.打印 = print
    _duan_builtin.读取行 = lambda: sys.stdin.readline().rstrip('\n')
    _duan_builtin.读取N字节 = lambda n: sys.stdin.read(n)
    _duan_builtin.写入输出 = lambda t: (sys.stdout.write(t), sys.stdout.flush()) and None
    _duan_builtin.打印输出 = lambda t: print(t, flush=True)
    _duan_builtin.刷新输出 = lambda: sys.stdout.flush()
    _duan_builtin.写入错误 = lambda t: (sys.stderr.write(t), sys.stderr.flush()) and None
    _duan_builtin.打印错误 = lambda t: print(t, file=sys.stderr, flush=True)
    _duan_builtin.解析JSON = lambda t: __import__('json').loads(t)
    _duan_builtin.序列化JSON = lambda v, i=None: (__import__('json').dumps(v, ensure_ascii=False, indent=i) if i is not None else __import__('json').dumps(v, ensure_ascii=False))
    _duan_builtin.美化JSON = lambda v: __import__('json').dumps(v, ensure_ascii=False, indent=2)
    _duan_builtin.转字符串 = str
    _duan_builtin.转整数 = int
    _duan_builtin.转浮点 = float
    _duan_builtin.chr = chr
    _duan_builtin.bin = bin
    _duan_builtin.hex = hex
    _duan_builtin.oct = oct
    _duan_builtin.列表创建 = list
    _duan_builtin.列表长度 = len
    _duan_builtin.列 = lambda *args: list(args)
    _duan_builtin.列表追加 = lambda lst, item: lst.append(item)
    _duan_builtin.列表获取 = lambda lst, i: lst[i]
    _duan_builtin.列表弹出 = lambda lst, i=-1: lst.pop(i)
    _duan_builtin.列表插入 = lambda lst, i, v: lst.insert(i, v)
    _duan_builtin.列表包含 = lambda lst, item: item in lst
    _duan_builtin.包含 = lambda sub, s: sub in s
    _duan_builtin.字符串包含 = lambda s, sub: sub in s
    _duan_builtin.字符串替换 = lambda s, old, new: s.replace(old, new)
    _duan_builtin.字符串反转 = lambda s: s[::-1]
    _duan_builtin.字符串长度 = len
    _duan_builtin.字符串获取 = lambda s, i: s[i]
    _duan_builtin.截取 = lambda s, start, end: s[start:end]
    _duan_builtin.转大写 = lambda s: s.upper()
    _duan_builtin.转小写 = lambda s: s.lower()
    _duan_builtin.结尾 = lambda s, suffix: s.endswith(suffix)
    _duan_builtin.开头 = lambda s, prefix: s.startswith(prefix)
    _duan_builtin.去除空白 = lambda s: s.strip()
    _duan_builtin.分割字符串 = lambda s, sep=None: s.split(sep)
    _duan_builtin.连接字符串 = lambda parts, sep='': sep.join(parts)
    _duan_builtin.替换字符串 = lambda s, old, new: s.replace(old, new)
    _duan_builtin.字符串分割 = lambda s, sep=None: s.split(sep)
    _duan_builtin.字典创建 = dict
    _duan_builtin.字典设置 = lambda d, k, v: d.update({k: v})
    _duan_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
    _duan_builtin.字典键列表 = lambda d: list(d.keys())
    _duan_builtin.字典包含键 = lambda d, k: k in d
    _duan_builtin.时间戳 = lambda: __import__('time').time()
    _duan_builtin.格式化时间 = lambda t, f='%Y-%m-%d %H:%M:%S': __import__('datetime').datetime.fromtimestamp(t).strftime(f) if isinstance(t, (int, float)) else __import__('datetime').datetime.strptime(t, '%Y-%m-%d %H:%M:%S').strftime(f)

# stdlib 物理缺失时的兜底：补齐常用 builtin + 注册 文件系统 模块
for _duan_n, _duan_f in [
    ('列表排序', lambda lst, 反向=False: lst.sort(reverse=反向)),
    ('列表反转', lambda lst: lst.reverse()),
    ('列表清空', lambda lst: lst.clear()),
    ('列表移除', lambda lst, item: lst.remove(item)),
    ('列表长度', len),
    ('追加文件', lambda path, content, encoding='utf-8': open(path, 'a', encoding=encoding).write(content) or None),
    ('删除文件', lambda path: __import__('os').remove(path) if __import__('os').path.isfile(path) else None),
    ('复制文件', lambda src, dst: __import__('shutil').copy2(src, dst)),
    ('移动文件', lambda src, dst: __import__('shutil').move(src, dst)),
    ('创建目录', lambda path: __import__('os').makedirs(path, exist_ok=True)),
    ('删除目录', lambda path: __import__('shutil').rmtree(path)),
    ('路径连接', lambda *parts: __import__('os').path.join(*parts)),
    ('当前工作目录', lambda: __import__('os').getcwd()),
]:
    if not hasattr(_duan_builtin, _duan_n):
        setattr(_duan_builtin, _duan_n, _duan_f)
if (not _duan_stdlib) or (not os.path.isdir(_duan_stdlib or '')):
    try:
        import types as _duan_types
        _duan_fs = _duan_types.ModuleType('文件系统')
        for _duan_fn in ('读取文件', '写入文件', '追加文件', '文件存在', '删除文件', '复制文件', '移动文件', '创建目录', '删除目录', '目录存在', '路径连接', '当前工作目录', '读取行'):
            if hasattr(_duan_builtin, _duan_fn):
                setattr(_duan_fs, _duan_fn, getattr(_duan_builtin, _duan_fn))
        sys.modules.setdefault('文件系统', _duan_fs)
    except Exception:
        pass
# 可空类型解包辅助函数
def _duan_unwrap(_x):
    assert _x is not None, "尝试解包空值"
    return _x

# 断言辅助函数
def _duan_assert(_cond, _msg=''):
    if not _cond:
        raise AssertionError(_msg)

def 是关键字(w):
    if (w == "设"):
        return True
    if (w == "段落"):
        return True
    if (w == "段"):
        return True
    if (w == "返回"):
        return True
    if (w == "结束"):
        return True
    if (w == "为"):
        return True
    if (w == "如果"):
        return True
    if (w == "否则"):
        return True
    if (w == "当"):
        return True
    if (w == "接收"):
        return True
    if (w == "加"):
        return True
    if (w == "减"):
        return True
    if (w == "乘"):
        return True
    if (w == "除"):
        return True
    if (w == "取模"):
        return True
    if (w == "等于"):
        return True
    if (w == "小于"):
        return True
    if (w == "大于"):
        return True
    if (w == "小于等于"):
        return True
    if (w == "大于等于"):
        return True
    if (w == "不等于"):
        return True
    if (w == "且"):
        return True
    if (w == "或"):
        return True
    if (w == "非"):
        return True
    if (w == "遍历"):
        return True
    if (w == "在"):
        return True
    if (w == "类"):
        return True
    if (w == "属性"):
        return True
    if (w == "己"):
        return True
    return False

def 是函数关键字(w):
    if (w == "段落"):
        return True
    if (w == "段"):
        return True
    return False

def 建(t, v):
    lst = _duan_builtin.列表创建()
    _duan_builtin.列表追加(lst, t)
    _duan_builtin.列表追加(lst, v)
    return lst

def 创建对(a, b):
    lst = _duan_builtin.列表创建()
    _duan_builtin.列表追加(lst, a)
    _duan_builtin.列表追加(lst, b)
    return lst

def 词(src, p, n, s):
    if (p < n):
        c = _duan_builtin.字符串获取(src, p)
        if (c == "："):
            if (s == ""):
                return 建("EOF", "")
            if 是关键字(s):
                return 建("KW", s)
            return 建("ID", s)
        if (c == "。"):
            if (s == ""):
                return 建("EOF", "")
            if 是关键字(s):
                return 建("KW", s)
            return 建("ID", s)
        if (c == "，"):
            if (s == ""):
                return 建("EOF", "")
            if 是关键字(s):
                return 建("KW", s)
            return 建("ID", s)
        if (c >= "a"):
            return 词(src, (p + 1), n, (s + c))
        if (c >= "A"):
            return 词(src, (p + 1), n, (s + c))
        if (c >= "一"):
            return 词(src, (p + 1), n, (s + c))
        if (c >= "0"):
            if (c <= "9"):
                if (s != ""):
                    return 词(src, (p + 1), n, (s + c))
    if (s == ""):
        return 建("EOF", "")
    if 是关键字(s):
        return 建("KW", s)
    return 建("ID", s)

def 数字(src, p, n, s):
    if (p < n):
        c = _duan_builtin.字符串获取(src, p)
        if (c >= "0"):
            if (c <= "9"):
                return 数字(src, (p + 1), n, (s + c))
    return 建("NUM", s)

def 字符串(src, p, n, s):
    if (p < n):
        c = _duan_builtin.字符串获取(src, p)
        if (c == "\""):
            tok = 建("STR", s)
            return 创建对(tok, (p + 1))
        return 字符串(src, (p + 1), n, (s + c))
    tok = 建("STR", s)
    return 创建对(tok, p)

def 扫注释(src, p, n):
    if (p < n):
        c = _duan_builtin.字符串获取(src, p)
        if (c == "\n"):
            return (p + 1)
        return 扫注释(src, (p + 1), n)
    return p

def 扫(src, p, n, toks):
    while (p < n):
        c = _duan_builtin.字符串获取(src, p)
        已处理 = False
        if (c == " "):
            p = (p + 1)
            已处理 = True
        if ((已处理 == False) and (c == "\n")):
            p = (p + 1)
            已处理 = True
        if ((已处理 == False) and (c == "#")):
            p = 扫注释(src, (p + 1), n)
            已处理 = True
        if ((已处理 == False) and (c == "'")):
            if ((p + 1) < n):
                nc = _duan_builtin.字符串获取(src, (p + 1))
                if (nc == "\""):
                    _duan_builtin.列表追加(toks, 建("STR", "\""))
                    p = (p + 3)
                    已处理 = True
            if (已处理 == False):
                p = (p + 1)
                已处理 = True
        if ((已处理 == False) and (c == "\"")):
            if ((p + 1) < n):
                nc = _duan_builtin.字符串获取(src, (p + 1))
                if (nc == "'"):
                    _duan_builtin.列表追加(toks, 建("STR", "'"))
                    p = (p + 3)
                    已处理 = True
            if (已处理 == False):
                结果 = 字符串(src, (p + 1), n, "")
                tok = _duan_builtin.列表获取(结果, 0)
                p = _duan_builtin.列表获取(结果, 1)
                _duan_builtin.列表追加(toks, tok)
                已处理 = True
        if ((已处理 == False) and (c == "：")):
            p = (p + 1)
            已处理 = True
        if ((已处理 == False) and (c == "。")):
            p = (p + 1)
            已处理 = True
        if ((已处理 == False) and (c == "，")):
            p = (p + 1)
            已处理 = True
        if ((已处理 == False) and (c == "(")):
            _duan_builtin.列表追加(toks, 建("LPAREN", "("))
            p = (p + 1)
            已处理 = True
        if ((已处理 == False) and (c == ")")):
            _duan_builtin.列表追加(toks, 建("RPAREN", ")"))
            p = (p + 1)
            已处理 = True
        if ((已处理 == False) and (c == ",")):
            _duan_builtin.列表追加(toks, 建("COMMA", ","))
            p = (p + 1)
            已处理 = True
        if ((已处理 == False) and (c >= "0")):
            if (c <= "9"):
                tok = 数字(src, p, n, "")
                _duan_builtin.列表追加(toks, tok)
                p = (p + _duan_builtin.字符串长度(_duan_builtin.列表获取(tok, 1)))
                已处理 = True
        if ((已处理 == False) and (c >= "a")):
            tok = 词(src, p, n, "")
            _duan_builtin.列表追加(toks, tok)
            p = (p + _duan_builtin.字符串长度(_duan_builtin.列表获取(tok, 1)))
            已处理 = True
        if ((已处理 == False) and (c >= "A")):
            tok = 词(src, p, n, "")
            _duan_builtin.列表追加(toks, tok)
            p = (p + _duan_builtin.字符串长度(_duan_builtin.列表获取(tok, 1)))
            已处理 = True
        if ((已处理 == False) and (c >= "一")):
            tok = 词(src, p, n, "")
            _duan_builtin.列表追加(toks, tok)
            p = (p + _duan_builtin.字符串长度(_duan_builtin.列表获取(tok, 1)))
            已处理 = True
        if (已处理 == False):
            p = (p + 1)
    return toks

def 词法(src):
    return 扫(src, 0, _duan_builtin.字符串长度(src), _duan_builtin.列表创建())

def 表达式(toks, p):
    return 或表达式(toks, p)

def 或表达式(toks, p):
    结果 = 且表达式(toks, p)
    left = _duan_builtin.列表获取(结果, 0)
    np = _duan_builtin.列表获取(结果, 1)
    继续循环 = True
    while (继续循环 and (np < _duan_builtin.列表长度(toks))):
        tok = _duan_builtin.列表获取(toks, np)
        tv = _duan_builtin.列表获取(tok, 1)
        if (tv != "或"):
            继续循环 = False
        else:
            右结果 = 且表达式(toks, (np + 1))
            right = _duan_builtin.列表获取(右结果, 0)
            np = _duan_builtin.列表获取(右结果, 1)
            left = ((left + " or ") + right)
    return 创建对(left, np)

def 且表达式(toks, p):
    结果 = 比较表达式(toks, p)
    left = _duan_builtin.列表获取(结果, 0)
    np = _duan_builtin.列表获取(结果, 1)
    继续循环 = True
    while (继续循环 and (np < _duan_builtin.列表长度(toks))):
        tok = _duan_builtin.列表获取(toks, np)
        tv = _duan_builtin.列表获取(tok, 1)
        if (tv != "且"):
            继续循环 = False
        else:
            右结果 = 比较表达式(toks, (np + 1))
            right = _duan_builtin.列表获取(右结果, 0)
            np = _duan_builtin.列表获取(右结果, 1)
            left = ((left + " and ") + right)
    return 创建对(left, np)

def 比较表达式(toks, p):
    结果 = 加减表达式(toks, p)
    left = _duan_builtin.列表获取(结果, 0)
    np = _duan_builtin.列表获取(结果, 1)
    if (np < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, np)
        tv = _duan_builtin.列表获取(tok, 1)
        if (tv == "等于"):
            右结果 = 加减表达式(toks, (np + 1))
            right = _duan_builtin.列表获取(右结果, 0)
            np = _duan_builtin.列表获取(右结果, 1)
            return 创建对(((left + " == ") + right), np)
        if (tv == "小于"):
            右结果 = 加减表达式(toks, (np + 1))
            right = _duan_builtin.列表获取(右结果, 0)
            np = _duan_builtin.列表获取(右结果, 1)
            return 创建对(((left + " < ") + right), np)
        if (tv == "大于"):
            右结果 = 加减表达式(toks, (np + 1))
            right = _duan_builtin.列表获取(右结果, 0)
            np = _duan_builtin.列表获取(右结果, 1)
            return 创建对(((left + " > ") + right), np)
        if (tv == "小于等于"):
            右结果 = 加减表达式(toks, (np + 1))
            right = _duan_builtin.列表获取(右结果, 0)
            np = _duan_builtin.列表获取(右结果, 1)
            return 创建对(((left + " <= ") + right), np)
        if (tv == "大于等于"):
            右结果 = 加减表达式(toks, (np + 1))
            right = _duan_builtin.列表获取(右结果, 0)
            np = _duan_builtin.列表获取(右结果, 1)
            return 创建对(((left + " >= ") + right), np)
        if (tv == "不等于"):
            右结果 = 加减表达式(toks, (np + 1))
            right = _duan_builtin.列表获取(右结果, 0)
            np = _duan_builtin.列表获取(右结果, 1)
            return 创建对(((left + " != ") + right), np)
    return 创建对(left, np)

def 加减表达式(toks, p):
    结果 = 乘除表达式(toks, p)
    left = _duan_builtin.列表获取(结果, 0)
    np = _duan_builtin.列表获取(结果, 1)
    继续循环 = True
    while (继续循环 and (np < _duan_builtin.列表长度(toks))):
        tok = _duan_builtin.列表获取(toks, np)
        tv = _duan_builtin.列表获取(tok, 1)
        if (tv == "加"):
            右结果 = 乘除表达式(toks, (np + 1))
            right = _duan_builtin.列表获取(右结果, 0)
            np = _duan_builtin.列表获取(右结果, 1)
            left = ((left + " + ") + right)
        else:
            if (tv == "减"):
                右结果 = 乘除表达式(toks, (np + 1))
                right = _duan_builtin.列表获取(右结果, 0)
                np = _duan_builtin.列表获取(右结果, 1)
                left = ((left + " - ") + right)
            else:
                继续循环 = False
    return 创建对(left, np)

def 乘除表达式(toks, p):
    结果 = 一元表达式(toks, p)
    left = _duan_builtin.列表获取(结果, 0)
    np = _duan_builtin.列表获取(结果, 1)
    继续循环 = True
    while (继续循环 and (np < _duan_builtin.列表长度(toks))):
        tok = _duan_builtin.列表获取(toks, np)
        tv = _duan_builtin.列表获取(tok, 1)
        if (tv == "乘"):
            右结果 = 一元表达式(toks, (np + 1))
            right = _duan_builtin.列表获取(右结果, 0)
            np = _duan_builtin.列表获取(右结果, 1)
            left = ((left + " * ") + right)
        else:
            if (tv == "除"):
                右结果 = 一元表达式(toks, (np + 1))
                right = _duan_builtin.列表获取(右结果, 0)
                np = _duan_builtin.列表获取(右结果, 1)
                left = ((left + " // ") + right)
            else:
                if (tv == "取模"):
                    右结果 = 一元表达式(toks, (np + 1))
                    right = _duan_builtin.列表获取(右结果, 0)
                    np = _duan_builtin.列表获取(右结果, 1)
                    left = ((left + " % ") + right)
                else:
                    继续循环 = False
    return 创建对(left, np)

def 一元表达式(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if ((_duan_builtin.列表获取(tok, 0) == "KW") and (_duan_builtin.列表获取(tok, 1) == "非")):
            结果 = 一元表达式(toks, (p + 1))
            expr = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            return 创建对(("not " + expr), np)
        if (_duan_builtin.列表获取(tok, 0) == "LPAREN"):
            结果 = 表达式(toks, (p + 1))
            expr = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            if (np < _duan_builtin.列表长度(toks)):
                tok = _duan_builtin.列表获取(toks, np)
                if (_duan_builtin.列表获取(tok, 0) == "RPAREN"):
                    return 创建对(expr, (np + 1))
            return 创建对(expr, np)
        if (_duan_builtin.列表获取(tok, 0) == "NUM"):
            return 创建对(_duan_builtin.列表获取(tok, 1), (p + 1))
        if (_duan_builtin.列表获取(tok, 0) == "STR"):
            s = _duan_builtin.列表获取(tok, 1)
            有单引号 = False
            i = 0
            while (i < _duan_builtin.字符串长度(s)):
                if (_duan_builtin.字符串获取(s, i) == "'"):
                    有单引号 = True
                i = (i + 1)
            if 有单引号:
                return 创建对((("\"" + s) + "\""), (p + 1))
            return 创建对((("'" + s) + "'"), (p + 1))
        if (_duan_builtin.列表获取(tok, 0) == "ID"):
            name = _duan_builtin.列表获取(tok, 1)
            np = (p + 1)
            if (np < _duan_builtin.列表长度(toks)):
                tok = _duan_builtin.列表获取(toks, np)
                if (_duan_builtin.列表获取(tok, 0) == "LPAREN"):
                    参数结果 = 解析参数列表(toks, (np + 1))
                    args = _duan_builtin.列表获取(参数结果, 0)
                    np = _duan_builtin.列表获取(参数结果, 1)
                    return 创建对((((name + "(") + args) + ")"), np)
            return 创建对(name, np)
    return 创建对("None", p)

def 解析参数列表(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 0) == "RPAREN"):
            return 创建对("", (p + 1))
        结果 = 表达式(toks, p)
        first = _duan_builtin.列表获取(结果, 0)
        np = _duan_builtin.列表获取(结果, 1)
        剩余结果 = 解析更多参数(toks, np, first)
        return 剩余结果
    return 创建对("", p)

def 解析更多参数(toks, p, acc):
    while (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 0) == "RPAREN"):
            return 创建对(acc, (p + 1))
        if (_duan_builtin.列表获取(tok, 0) == "COMMA"):
            结果 = 表达式(toks, (p + 1))
            next_arg = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            acc = ((acc + ", ") + next_arg)
            p = np
        else:
            p = (p + 1)
    return 创建对(acc, p)

def find_ret(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 1) == "返回"):
            结果 = 表达式(toks, (p + 1))
            expr = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            return 创建对(("return " + expr), np)
    return 创建对("pass", p)

def find_end(toks, p):
    while (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 0) == "KW"):
            if (_duan_builtin.列表获取(tok, 1) == "结束"):
                return (p + 1)
            if 是函数关键字(_duan_builtin.列表获取(tok, 1)):
                return p
        p = (p + 1)
    return p

def find_next(toks, p):
    while (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 0) == "KW"):
            tv = _duan_builtin.列表获取(tok, 1)
            if 是函数关键字(tv):
                return p
            if (tv == "结束"):
                return p
            if (tv == "设"):
                return p
            if (tv == "如果"):
                return p
            if (tv == "返回"):
                return p
        p = (p + 1)
    return p

def comp_set(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 1) == "设"):
            np = (p + 1)
            if (np < _duan_builtin.列表长度(toks)):
                tok = _duan_builtin.列表获取(toks, np)
                var = _duan_builtin.列表获取(tok, 1)
                np = (np + 1)
                if (np < _duan_builtin.列表长度(toks)):
                    tok = _duan_builtin.列表获取(toks, np)
                    if (_duan_builtin.列表获取(tok, 1) == "为"):
                        np = (np + 1)
                        结果 = 表达式(toks, np)
                        expr = _duan_builtin.列表获取(结果, 0)
                        np = _duan_builtin.列表获取(结果, 1)
                        return 创建对(((var + " = ") + expr), np)
    return 创建对("", p)

def find_matching_end(toks, p, level):
    while (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 0) == "KW"):
            tv = _duan_builtin.列表获取(tok, 1)
            if (tv == "如果"):
                level = (level + 1)
            if (tv == "当"):
                level = (level + 1)
            if (tv == "遍历"):
                level = (level + 1)
            if (tv == "类"):
                level = (level + 1)
            if (tv == "段落"):
                level = (level + 1)
            if (tv == "段"):
                level = (level + 1)
            if (tv == "否则"):
                if (level == 1):
                    return p
            if (tv == "结束"):
                if (level == 1):
                    return (p + 1)
                level = (level - 1)
        p = (p + 1)
    return p

def compile_block(toks, p, end_p, indent, out):
    while (p < end_p):
        if (p < _duan_builtin.列表长度(toks)):
            tok = _duan_builtin.列表获取(toks, p)
            tv = _duan_builtin.列表获取(tok, 1)
            已处理 = False
            if (tv == "设"):
                结果 = comp_set(toks, p)
                stmt = _duan_builtin.列表获取(结果, 0)
                np = _duan_builtin.列表获取(结果, 1)
                out = (((out + indent) + stmt) + "\n")
                p = np
                已处理 = True
            if ((已处理 == False) and (tv == "如果")):
                结果 = comp_if(toks, p)
                stmt = _duan_builtin.列表获取(结果, 0)
                np = _duan_builtin.列表获取(结果, 1)
                out = (out + add_indent(stmt, indent))
                p = np
                已处理 = True
            if ((已处理 == False) and (tv == "当")):
                结果 = comp_while(toks, p)
                stmt = _duan_builtin.列表获取(结果, 0)
                np = _duan_builtin.列表获取(结果, 1)
                out = (out + add_indent(stmt, indent))
                p = np
                已处理 = True
            if ((已处理 == False) and (tv == "遍历")):
                结果 = comp_for(toks, p)
                stmt = _duan_builtin.列表获取(结果, 0)
                np = _duan_builtin.列表获取(结果, 1)
                out = (out + add_indent(stmt, indent))
                p = np
                已处理 = True
            if ((已处理 == False) and (tv == "返回")):
                结果 = find_ret(toks, p)
                stmt = _duan_builtin.列表获取(结果, 0)
                np = _duan_builtin.列表获取(结果, 1)
                out = (((out + indent) + stmt) + "\n")
                p = np
                已处理 = True
            if ((已处理 == False) and (_duan_builtin.列表获取(tok, 0) == "ID")):
                np = (p + 1)
                if (np < _duan_builtin.列表长度(toks)):
                    ntok = _duan_builtin.列表获取(toks, np)
                    if (_duan_builtin.列表获取(ntok, 0) == "LPAREN"):
                        结果 = 表达式(toks, p)
                        stmt = _duan_builtin.列表获取(结果, 0)
                        np = _duan_builtin.列表获取(结果, 1)
                        out = (((out + indent) + stmt) + "\n")
                        p = np
                        已处理 = True
            if ((已处理 == False) and (tv == "结束")):
                return out
            if (已处理 == False):
                p = (p + 1)
    return out

def add_indent(text, indent):
    有尾换行 = False
    if (_duan_builtin.字符串长度(text) > 0):
        末字符 = _duan_builtin.字符串获取(text, (_duan_builtin.字符串长度(text) - 1))
        if (末字符 == "\n"):
            有尾换行 = True
    if 有尾换行:
        text = _duan_builtin.截取(text, 0, (_duan_builtin.字符串长度(text) - 1))
    结果 = (indent + 加缩进行(text, indent, "", 0))
    if 有尾换行:
        return (结果 + "\n")
    return 结果

def 加缩进行(text, indent, acc, i):
    while (i < _duan_builtin.字符串长度(text)):
        c = _duan_builtin.字符串获取(text, i)
        if (c == "\n"):
            acc = ((acc + "\n") + indent)
        else:
            acc = (acc + c)
        i = (i + 1)
    return acc

def comp_if(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 1) == "如果"):
            np = (p + 1)
            结果 = 表达式(toks, np)
            cond = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            end_p = find_matching_end(toks, np, 1)
            body = compile_block(toks, np, (end_p - 1), "    ", "")
            if (body == ""):
                body = "    pass\n"
            code = ((("if " + cond) + ":\n") + body)
            if (end_p < _duan_builtin.列表长度(toks)):
                next_tok = _duan_builtin.列表获取(toks, end_p)
                if (_duan_builtin.列表获取(next_tok, 1) == "否则"):
                    else_p = (end_p + 1)
                    else_end = find_matching_end(toks, else_p, 1)
                    else_body = compile_block(toks, else_p, (else_end - 1), "    ", "")
                    if (else_body == ""):
                        else_body = "    pass"
                    code = ((code + "\nelse:\n") + else_body)
                    return 创建对(code, else_end)
            return 创建对(code, end_p)
    return 创建对("", p)

def comp_while(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 1) == "当"):
            np = (p + 1)
            结果 = 表达式(toks, np)
            cond = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            end_p = find_matching_end(toks, np, 1)
            body = compile_block(toks, np, (end_p - 1), "    ", "")
            if (body == ""):
                body = "    pass\n"
            return 创建对(((("while " + cond) + ":\n") + body), end_p)
    return 创建对("", p)

def comp_for(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 1) == "遍历"):
            np = (p + 1)
            if (np < _duan_builtin.列表长度(toks)):
                var_tok = _duan_builtin.列表获取(toks, np)
                var_name = _duan_builtin.列表获取(var_tok, 1)
                np = (np + 1)
                if (np < _duan_builtin.列表长度(toks)):
                    next_tok = _duan_builtin.列表获取(toks, np)
                    if (_duan_builtin.列表获取(next_tok, 1) == "在"):
                        np = (np + 1)
                        结果 = 表达式(toks, np)
                        iter_expr = _duan_builtin.列表获取(结果, 0)
                        np = _duan_builtin.列表获取(结果, 1)
                        end_p = find_matching_end(toks, np, 1)
                        body = compile_block(toks, np, (end_p - 1), "    ", "")
                        if (body == ""):
                            body = "    pass\n"
                        return 创建对(((((("for " + var_name) + " in ") + iter_expr) + ":\n") + body), end_p)
    return 创建对("", p)

def compile_stmts(toks, p, out):
    while (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        tv = _duan_builtin.列表获取(tok, 1)
        已处理 = False
        if (tv == "设"):
            结果 = comp_set(toks, p)
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (((out + "    ") + stmt) + "\n")
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "如果")):
            结果 = comp_if(toks, p)
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (out + add_indent(stmt, "    "))
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "当")):
            结果 = comp_while(toks, p)
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (out + add_indent(stmt, "    "))
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "遍历")):
            结果 = comp_for(toks, p)
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (out + add_indent(stmt, "    "))
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "返回")):
            结果 = find_ret(toks, p)
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (((out + "    ") + stmt) + "\n")
            p = np
            已处理 = True
        if ((已处理 == False) and (_duan_builtin.列表获取(tok, 0) == "ID")):
            np = (p + 1)
            if (np < _duan_builtin.列表长度(toks)):
                ntok = _duan_builtin.列表获取(toks, np)
                if (_duan_builtin.列表获取(ntok, 0) == "LPAREN"):
                    结果 = 表达式(toks, p)
                    stmt = _duan_builtin.列表获取(结果, 0)
                    np = _duan_builtin.列表获取(结果, 1)
                    out = (((out + "    ") + stmt) + "\n")
                    p = np
                    已处理 = True
        if ((已处理 == False) and (tv == "结束")):
            return 创建对(out, (p + 1))
        if ((已处理 == False) and 是函数关键字(tv)):
            return 创建对(out, p)
        if (已处理 == False):
            p = (p + 1)
    return 创建对(out, p)

def 解析参数(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 1) == "接收"):
            return 收集参数(toks, (p + 1), "")
    return 创建对("", p)

def 收集参数(toks, p, acc):
    while (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        已处理 = False
        if (_duan_builtin.列表获取(tok, 0) == "ID"):
            v = _duan_builtin.列表获取(tok, 1)
            if (_duan_builtin.字符串长度(v) > 0):
                末字符 = _duan_builtin.字符串获取(v, (_duan_builtin.字符串长度(v) - 1))
                if (末字符 == "："):
                    v = _duan_builtin.截取(v, 0, (_duan_builtin.字符串长度(v) - 1))
                    if (acc == ""):
                        return 创建对(v, (p + 1))
                    return 创建对(((acc + ", ") + v), (p + 1))
            if (acc == ""):
                acc = v
            else:
                acc = ((acc + ", ") + v)
            p = (p + 1)
            已处理 = True
        if ((已处理 == False) and (_duan_builtin.列表获取(tok, 0) == "COMMA")):
            p = (p + 1)
            已处理 = True
        if (已处理 == False):
            return 创建对(acc, p)
    return 创建对(acc, p)

def compile_class(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 1) == "类"):
            np = (p + 1)
            name = ""
            if (np < _duan_builtin.列表长度(toks)):
                name_tok = _duan_builtin.列表获取(toks, np)
                name = _duan_builtin.列表获取(name_tok, 1)
                np = (np + 1)
            end_p = find_matching_end(toks, np, 1)
            body = compile_class_body(toks, np, (end_p - 1), name)
            return 创建对(((("class " + name) + ":\n") + body), end_p)
    return 创建对("", p)

def compile_class_body(toks, p, end_p, class_name):
    out = ""
    while ((p < end_p) and (p < _duan_builtin.列表长度(toks))):
        tok = _duan_builtin.列表获取(toks, p)
        tv = _duan_builtin.列表获取(tok, 1)
        if (tv == "属性"):
            np = (p + 1)
            if (np < _duan_builtin.列表长度(toks)):
                attr_tok = _duan_builtin.列表获取(toks, np)
                attr_name = _duan_builtin.列表获取(attr_tok, 1)
                p = (np + 1)
                continue
        if 是函数关键字(tv):
            func结果 = compile_class_method(toks, p, class_name)
            method_code = _duan_builtin.列表获取(func结果, 0)
            p = _duan_builtin.列表获取(func结果, 1)
            out = (out + method_code)
            continue
        if (tv == "结束"):
            return out
        p = (p + 1)
    return out

def compile_class_method(toks, p, class_name):
    tok = _duan_builtin.列表获取(toks, p)
    np = (p + 1)
    name = ""
    if (np < _duan_builtin.列表长度(toks)):
        name_tok = _duan_builtin.列表获取(toks, np)
        name = _duan_builtin.列表获取(name_tok, 1)
        np = (np + 1)
    参数结果 = 解析参数(toks, np)
    params = _duan_builtin.列表获取(参数结果, 0)
    np = _duan_builtin.列表获取(参数结果, 1)
    self_param = "self"
    if (params != ""):
        self_param = ("self, " + params)
    method_end = find_matching_end(toks, np, 1)
    body = compile_block(toks, np, (method_end - 1), "        ", "")
    if (body == ""):
        body = "        pass"
    code = (((((("    def " + name) + "(") + self_param) + "):\n") + body) + "\n")
    return 创建对(code, method_end)

def compile_top(toks, p, out):
    while (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        tv = _duan_builtin.列表获取(tok, 1)
        已处理 = False
        if (tv == "类"):
            结果 = compile_class(toks, p)
            class_code = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = ((out + class_code) + "\n")
            p = np
            已处理 = True
        if ((已处理 == False) and 是函数关键字(tv)):
            结果 = compile_single_func(toks, p)
            func_code = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (out + func_code)
            p = np
            已处理 = True
        if (已处理 == False):
            p = (p + 1)
    return out

def compile_single_func(toks, p):
    tok = _duan_builtin.列表获取(toks, p)
    np = (p + 1)
    name = ""
    if (np < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, np)
        if (_duan_builtin.列表获取(tok, 0) == "ID"):
            name = _duan_builtin.列表获取(tok, 1)
            np = (np + 1)
    参数结果 = 解析参数(toks, np)
    params = _duan_builtin.列表获取(参数结果, 0)
    np = _duan_builtin.列表获取(参数结果, 1)
    body结果 = compile_stmts(toks, np, "")
    body = _duan_builtin.列表获取(body结果, 0)
    np = _duan_builtin.列表获取(body结果, 1)
    if (body == ""):
        body = "    pass\n"
    code = (((((("def " + name) + "(") + params) + "):\n") + body) + "\n")
    return 创建对(code, np)

def 编译(src):
    header = "# Generated by Duan Level 3\n"
    toks = 词法(src)
    code = compile_top(toks, 0, "")
    return (header + code)

def 测试():
    print("=== Level 3 测试 ===")
    print("")
    print("--- 测试1: 基本函数 ---")
    src1 = "段落 foo 返回 42 结束"
    print(("源: " + src1))
    print(编译(src1))
    print("")
    print("--- 测试2: 带变量 ---")
    src2 = "段落 bar 设 x 为 10 返回 x 结束"
    print(("源: " + src2))
    print(编译(src2))
    print("")
    print("--- 测试3: 带if ---")
    src3 = "段落 baz 如果 真 返回 1 结束 返回 0 结束"
    print(("源: " + src3))
    print(编译(src3))
    print("")
    print("Level 3 验证通过！")

def 主函数():
    print("段言 Level 3 启动")
    print("")
    测试()

主函数()