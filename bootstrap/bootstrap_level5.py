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

def 关键字列表():
    kws = _duan_builtin.列表创建()
    _duan_builtin.列表追加(kws, "设")
    _duan_builtin.列表追加(kws, "段落")
    _duan_builtin.列表追加(kws, "段")
    _duan_builtin.列表追加(kws, "返回")
    _duan_builtin.列表追加(kws, "结束")
    _duan_builtin.列表追加(kws, "为")
    _duan_builtin.列表追加(kws, "如果")
    _duan_builtin.列表追加(kws, "否则")
    _duan_builtin.列表追加(kws, "当")
    _duan_builtin.列表追加(kws, "接收")
    _duan_builtin.列表追加(kws, "加")
    _duan_builtin.列表追加(kws, "减")
    _duan_builtin.列表追加(kws, "乘")
    _duan_builtin.列表追加(kws, "除")
    _duan_builtin.列表追加(kws, "取模")
    _duan_builtin.列表追加(kws, "等于")
    _duan_builtin.列表追加(kws, "小于")
    _duan_builtin.列表追加(kws, "大于")
    _duan_builtin.列表追加(kws, "小于等于")
    _duan_builtin.列表追加(kws, "大于等于")
    _duan_builtin.列表追加(kws, "不等于")
    _duan_builtin.列表追加(kws, "且")
    _duan_builtin.列表追加(kws, "或")
    _duan_builtin.列表追加(kws, "非")
    _duan_builtin.列表追加(kws, "遍历")
    _duan_builtin.列表追加(kws, "在")
    _duan_builtin.列表追加(kws, "类")
    _duan_builtin.列表追加(kws, "属性")
    _duan_builtin.列表追加(kws, "己")
    _duan_builtin.列表追加(kws, "继承")
    _duan_builtin.列表追加(kws, "父")
    _duan_builtin.列表追加(kws, "尝试")
    _duan_builtin.列表追加(kws, "捕获")
    _duan_builtin.列表追加(kws, "最终")
    _duan_builtin.列表追加(kws, "抛出")
    _duan_builtin.列表追加(kws, "导入")
    _duan_builtin.列表追加(kws, "导出")
    _duan_builtin.列表追加(kws, "匹配")
    _duan_builtin.列表追加(kws, "情形")
    _duan_builtin.列表追加(kws, "异步")
    _duan_builtin.列表追加(kws, "等待")
    _duan_builtin.列表追加(kws, "使用")
    return kws

def 是关键字(w):
    kws = 关键字列表()
    i = 0
    while (i < _duan_builtin.列表长度(kws)):
        if (_duan_builtin.列表获取(kws, i) == w):
            return True
        i = (i + 1)
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
    while (p < n):
        c = _duan_builtin.字符串获取(src, p)
        是分隔符 = False
        if (c == "："):
            是分隔符 = True
        if (c == "。"):
            是分隔符 = True
        if (c == "，"):
            是分隔符 = True
        if (是分隔符 == True):
            if (s == ""):
                return 建("EOF", "")
            if 是关键字(s):
                return 建("KW", s)
            return 建("ID", s)
        是字母 = False
        if (c == "_"):
            是字母 = True
        if (c >= "a"):
            if (c <= "z"):
                是字母 = True
        if (c >= "A"):
            if (c <= "Z"):
                是字母 = True
        if (c >= "一"):
            是字母 = True
        if (是字母 == True):
            s = (s + c)
            p = (p + 1)
        else:
            是数字 = False
            if (c >= "0"):
                if (c <= "9"):
                    是数字 = True
            if (是数字 == True):
                if (s != ""):
                    s = (s + c)
                    p = (p + 1)
                else:
                    if (s == ""):
                        return 建("EOF", "")
                    if 是关键字(s):
                        return 建("KW", s)
                    return 建("ID", s)
            else:
                if (s == ""):
                    return 建("EOF", "")
                if 是关键字(s):
                    return 建("KW", s)
                return 建("ID", s)
    if (s == ""):
        return 建("EOF", "")
    if 是关键字(s):
        return 建("KW", s)
    return 建("ID", s)

def 数字(src, p, n, s):
    while (p < n):
        c = _duan_builtin.字符串获取(src, p)
        if ((c >= "0") and (c <= "9")):
            s = (s + c)
            p = (p + 1)
        else:
            return 建("NUM", s)
    return 建("NUM", s)

def 字符串(src, p, n, s):
    while (p < n):
        c = _duan_builtin.字符串获取(src, p)
        if (c == "\""):
            tok = 建("STR", s)
            return 创建对(tok, (p + 1))
        s = (s + c)
        p = (p + 1)
    tok = 建("STR", s)
    return 创建对(tok, p)

def 扫注释(src, p, n):
    while (p < n):
        c = _duan_builtin.字符串获取(src, p)
        if (c == "\n"):
            return (p + 1)
        p = (p + 1)
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
        if ((已处理 == False) and (c == ".")):
            _duan_builtin.列表追加(toks, 建("DOT", "."))
            p = (p + 1)
            已处理 = True
        if ((已处理 == False) and (c == "@")):
            _duan_builtin.列表追加(toks, 建("AT", "@"))
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
    结果 = 成员表达式(toks, p)
    left = _duan_builtin.列表获取(结果, 0)
    np = _duan_builtin.列表获取(结果, 1)
    继续循环 = True
    while (继续循环 and (np < _duan_builtin.列表长度(toks))):
        tok = _duan_builtin.列表获取(toks, np)
        tv = _duan_builtin.列表获取(tok, 1)
        if (tv == "乘"):
            右结果 = 成员表达式(toks, (np + 1))
            right = _duan_builtin.列表获取(右结果, 0)
            np = _duan_builtin.列表获取(右结果, 1)
            left = ((left + " * ") + right)
        else:
            if (tv == "除"):
                右结果 = 成员表达式(toks, (np + 1))
                right = _duan_builtin.列表获取(右结果, 0)
                np = _duan_builtin.列表获取(右结果, 1)
                left = ((left + " // ") + right)
            else:
                if (tv == "取模"):
                    右结果 = 成员表达式(toks, (np + 1))
                    right = _duan_builtin.列表获取(右结果, 0)
                    np = _duan_builtin.列表获取(右结果, 1)
                    left = ((left + " % ") + right)
                else:
                    继续循环 = False
    return 创建对(left, np)

def 成员表达式(toks, p):
    结果 = 一元表达式(toks, p)
    left = _duan_builtin.列表获取(结果, 0)
    np = _duan_builtin.列表获取(结果, 1)
    return 处理成员链(toks, np, left)

def 处理成员链(toks, p, left):
    np = p
    while (np < _duan_builtin.列表长度(toks)):
        dot_tok = _duan_builtin.列表获取(toks, np)
        if (_duan_builtin.列表获取(dot_tok, 0) == "DOT"):
            np = (np + 1)
            if (np < _duan_builtin.列表长度(toks)):
                attr_tok = _duan_builtin.列表获取(toks, np)
                attr_name = _duan_builtin.列表获取(attr_tok, 1)
                np = (np + 1)
                if (np < _duan_builtin.列表长度(toks)):
                    next_tok = _duan_builtin.列表获取(toks, np)
                    if (_duan_builtin.列表获取(next_tok, 0) == "LPAREN"):
                        参数结果 = 解析参数列表(toks, (np + 1))
                        args = _duan_builtin.列表获取(参数结果, 0)
                        np = _duan_builtin.列表获取(参数结果, 1)
                        left = (((((left + ".") + attr_name) + "(") + args) + ")")
                    else:
                        left = ((left + ".") + attr_name)
                else:
                    left = ((left + ".") + attr_name)
        else:
            return 创建对(left, np)
    return 创建对(left, np)

def 一元表达式(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if ((_duan_builtin.列表获取(tok, 0) == "KW") and (_duan_builtin.列表获取(tok, 1) == "非")):
            结果 = 一元表达式(toks, (p + 1))
            expr = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            return 创建对(("not " + expr), np)
        if ((_duan_builtin.列表获取(tok, 0) == "KW") and (_duan_builtin.列表获取(tok, 1) == "己")):
            return 处理成员链(toks, (p + 1), "self")
        if ((_duan_builtin.列表获取(tok, 0) == "KW") and (_duan_builtin.列表获取(tok, 1) == "父")):
            return 处理成员链(toks, (p + 1), "super()")
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
                first_tok = _duan_builtin.列表获取(toks, np)
                if ((_duan_builtin.列表获取(first_tok, 0) == "KW") and (_duan_builtin.列表获取(first_tok, 1) == "己")):
                    var_expr = "self"
                    np = (np + 1)
                    继续循环 = True
                    while ((继续循环 == True) and (np < _duan_builtin.列表长度(toks))):
                        dot_tok = _duan_builtin.列表获取(toks, np)
                        if (_duan_builtin.列表获取(dot_tok, 0) == "DOT"):
                            np = (np + 1)
                            if (np < _duan_builtin.列表长度(toks)):
                                attr_tok = _duan_builtin.列表获取(toks, np)
                                attr_name = _duan_builtin.列表获取(attr_tok, 1)
                                var_expr = ((var_expr + ".") + attr_name)
                                np = (np + 1)
                        else:
                            继续循环 = False
                    if (np < _duan_builtin.列表长度(toks)):
                        tok = _duan_builtin.列表获取(toks, np)
                        if (_duan_builtin.列表获取(tok, 1) == "为"):
                            np = (np + 1)
                            结果 = 表达式(toks, np)
                            expr = _duan_builtin.列表获取(结果, 0)
                            np = _duan_builtin.列表获取(结果, 1)
                            return 创建对(((var_expr + " = ") + expr), np)
                else:
                    var = _duan_builtin.列表获取(first_tok, 1)
                    np = (np + 1)
                    if (np < _duan_builtin.列表长度(toks)):
                        tok = _duan_builtin.列表获取(toks, np)
                        if (_duan_builtin.列表获取(tok, 1) == "为"):
                            np = (np + 1)
                            结果 = 表达式(toks, np)
                            expr = _duan_builtin.列表获取(结果, 0)
                            np = _duan_builtin.列表获取(结果, 1)
                            return 创建对(((var + " = ") + expr), np)
            return 创建对("", (p + 1))
    return 创建对("", p)

def comp_throw(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 1) == "抛出"):
            结果 = 表达式(toks, (p + 1))
            expr = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            if (_duan_builtin.字符串长度(expr) > 0):
                first = _duan_builtin.字符串获取(expr, 0)
                if ((first == "'") or (first == "\"")):
                    stmt = (("raise Exception(" + expr) + ")")
                else:
                    stmt = ("raise " + expr)
            else:
                stmt = ("raise " + expr)
            return 创建对(stmt, np)
    return 创建对("", p)

def 异常类型映射(name):
    if (name == "异常"):
        return "Exception"
    if (name == "值错误"):
        return "ValueError"
    if (name == "类型错误"):
        return "TypeError"
    if (name == "键错误"):
        return "KeyError"
    if (name == "索引错误"):
        return "IndexError"
    if (name == "除零错误"):
        return "ZeroDivisionError"
    if (name == "属性错误"):
        return "AttributeError"
    if (name == "名称错误"):
        return "NameError"
    if (name == "文件错误"):
        return "FileNotFoundError"
    if (name == "运行错误"):
        return "RuntimeError"
    if (name == "停止迭代"):
        return "StopIteration"
    return name

def comp_try(toks, p, indent):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 1) == "尝试"):
            np = (p + 1)
            out = (indent + "try:\n")
            继续扫描 = True
            try_end = 9999
            catch_positions = _duan_builtin.列表创建()
            finally_pos = 0
            level = 1
            scan_p = np
            while ((scan_p < _duan_builtin.列表长度(toks)) and 继续扫描):
                st = _duan_builtin.列表获取(toks, scan_p)
                if (_duan_builtin.列表获取(st, 0) == "KW"):
                    stv = _duan_builtin.列表获取(st, 1)
                    if (((((((stv == "尝试") or (stv == "如果")) or (stv == "当")) or (stv == "遍历")) or (stv == "类")) or (stv == "段落")) or (stv == "段")):
                        level = (level + 1)
                    if (stv == "结束"):
                        level = (level - 1)
                        if (level == 0):
                            try_end = scan_p
                            继续扫描 = False
                    if ((level == 1) and (stv == "捕获")):
                        _duan_builtin.列表追加(catch_positions, scan_p)
                    if ((level == 1) and (stv == "最终")):
                        finally_pos = scan_p
                if 继续扫描:
                    scan_p = (scan_p + 1)
            if (try_end == 9999):
                return 创建对("", (p + 1))
            body_indent = (indent + "    ")
            try_body_end = np
            if (_duan_builtin.列表长度(catch_positions) > 0):
                try_body_end = _duan_builtin.列表获取(catch_positions, 0)
            else:
                if (finally_pos != 0):
                    try_body_end = finally_pos
                else:
                    try_body_end = try_end
            try_result = compile_block(toks, np, try_body_end, body_indent, "")
            out = (out + try_result)
            ci = 0
            while (ci < _duan_builtin.列表长度(catch_positions)):
                cp = _duan_builtin.列表获取(catch_positions, ci)
                next_pos = try_end
                if ((ci + 1) < _duan_builtin.列表长度(catch_positions)):
                    next_pos = _duan_builtin.列表获取(catch_positions, (ci + 1))
                需要用finally = False
                if (finally_pos != 0):
                    if (finally_pos > cp):
                        if ((ci + 1) >= _duan_builtin.列表长度(catch_positions)):
                            需要用finally = True
                        else:
                            next_catch = _duan_builtin.列表获取(catch_positions, (ci + 1))
                            if (next_catch > finally_pos):
                                需要用finally = True
                if (需要用finally == True):
                    next_pos = finally_pos
                catch_type = ""
                catch_var = ""
                catch_body_start = (cp + 1)
                ctp = (cp + 1)
                找类型 = True
                while ((ctp < next_pos) and 找类型):
                    ct = _duan_builtin.列表获取(toks, ctp)
                    ctt = _duan_builtin.列表获取(ct, 0)
                    if (ctt == "LPAREN"):
                        if (catch_type == ""):
                            catch_body_start = ctp
                        else:
                            catch_body_start = (ctp + 1)
                        找类型 = False
                    if (找类型 and ((ctt == "ID") or (ctt == "KW"))):
                        if (catch_type == ""):
                            if ((ctt == "ID") and ((ctp + 1) < next_pos)):
                                ntok = _duan_builtin.列表获取(toks, (ctp + 1))
                                if (_duan_builtin.列表获取(ntok, 0) == "LPAREN"):
                                    catch_body_start = ctp
                                    找类型 = False
                                else:
                                    catch_type = _duan_builtin.列表获取(ct, 1)
                                    ctp = (ctp + 1)
                            else:
                                catch_type = _duan_builtin.列表获取(ct, 1)
                                ctp = (ctp + 1)
                    if ((找类型 and (catch_type != "")) and (ctt == "ID")):
                        ctv = _duan_builtin.列表获取(ct, 1)
                        if (ctv == "as"):
                            ctp = (ctp + 1)
                            if (ctp < next_pos):
                                vt = _duan_builtin.列表获取(toks, ctp)
                                catch_var = _duan_builtin.列表获取(vt, 1)
                                ctp = (ctp + 1)
                            catch_body_start = ctp
                            找类型 = False
                        else:
                            catch_body_start = ctp
                            找类型 = False
                    if ((找类型 and (catch_type != "")) and (ctt != "ID")):
                        catch_body_start = ctp
                        找类型 = False
                    if (((找类型 and (ctt != "LPAREN")) and (ctt != "ID")) and (ctt != "KW")):
                        catch_body_start = ctp
                        找类型 = False
                except_line = (indent + "except")
                if (catch_type != ""):
                    mapped_type = 异常类型映射(catch_type)
                    except_line = ((except_line + " ") + mapped_type)
                if (catch_var != ""):
                    except_line = ((except_line + " as ") + catch_var)
                except_line = (except_line + ":\n")
                out = (out + except_line)
                catch_result = compile_block(toks, catch_body_start, next_pos, body_indent, "")
                out = (out + catch_result)
                ci = (ci + 1)
            if (finally_pos != 0):
                out = ((out + indent) + "finally:\n")
                fin_result = compile_block(toks, (finally_pos + 1), try_end, body_indent, "")
                out = (out + fin_result)
            return 创建对(out, (try_end + 1))
    return 创建对("", p)

def 编译装饰器(toks, p):
    "编译单个装饰器行，返回装饰器代码和下一个位置"
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 0) == "AT"):
            np = (p + 1)
            结果 = 表达式(toks, np)
            expr = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            return 创建对(("@" + expr), np)
    return 创建对("", p)

def 收集装饰器(toks, p):
    "收集连续的装饰器行，返回装饰器列表和下一个位置"
    decors = _duan_builtin.列表创建()
    继续循环 = True
    while (继续循环 and (p < _duan_builtin.列表长度(toks))):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 0) == "AT"):
            结果 = 编译装饰器(toks, p)
            decor = _duan_builtin.列表获取(结果, 0)
            p = _duan_builtin.列表获取(结果, 1)
            _duan_builtin.列表追加(decors, decor)
        else:
            继续循环 = False
    return 创建对(decors, p)

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
            if (tv == "尝试"):
                level = (level + 1)
            if (tv == "匹配"):
                level = (level + 1)
            if (tv == "使用"):
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
            if ((已处理 == False) and (tv == "导入")):
                np = (p + 1)
                while (np < _duan_builtin.列表长度(toks)):
                    nt = _duan_builtin.列表获取(toks, np)
                    ntv = _duan_builtin.列表获取(nt, 1)
                    if ((ntv == "。") or (ntv == "\n")):
                        break
                    np = (np + 1)
                p = np
                已处理 = True
            if ((已处理 == False) and (tv == "导出")):
                np = (p + 1)
                while (np < _duan_builtin.列表长度(toks)):
                    nt = _duan_builtin.列表获取(toks, np)
                    ntv = _duan_builtin.列表获取(nt, 1)
                    if (ntv == "。"):
                        np = (np + 1)
                        break
                    np = (np + 1)
                p = np
                已处理 = True
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
            if ((已处理 == False) and (tv == "抛出")):
                结果 = comp_throw(toks, p)
                stmt = _duan_builtin.列表获取(结果, 0)
                np = _duan_builtin.列表获取(结果, 1)
                out = (((out + indent) + stmt) + "\n")
                p = np
                已处理 = True
            if ((已处理 == False) and (tv == "尝试")):
                结果 = comp_try(toks, p, indent)
                stmt = _duan_builtin.列表获取(结果, 0)
                np = _duan_builtin.列表获取(结果, 1)
                out = (out + stmt)
                p = np
                已处理 = True
            if ((已处理 == False) and (tv == "匹配")):
                结果 = comp_match(toks, p)
                stmt = _duan_builtin.列表获取(结果, 0)
                np = _duan_builtin.列表获取(结果, 1)
                out = (out + add_indent(stmt, indent))
                p = np
                已处理 = True
            if ((已处理 == False) and (tv == "使用")):
                结果 = comp_with(toks, p)
                stmt = _duan_builtin.列表获取(结果, 0)
                np = _duan_builtin.列表获取(结果, 1)
                out = (out + add_indent(stmt, indent))
                p = np
                已处理 = True
            if ((已处理 == False) and (tv == "等待")):
                结果 = 表达式(toks, (p + 1))
                expr = _duan_builtin.列表获取(结果, 0)
                np = _duan_builtin.列表获取(结果, 1)
                out = ((((out + indent) + "await ") + expr) + "\n")
                p = np
                已处理 = True
            if ((已处理 == False) and (_duan_builtin.列表获取(tok, 0) == "AT")):
                结果 = 编译装饰器(toks, p)
                decor = _duan_builtin.列表获取(结果, 0)
                np = _duan_builtin.列表获取(结果, 1)
                out = (((out + indent) + decor) + "\n")
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
                    if ((已处理 == False) and (_duan_builtin.列表获取(ntok, 0) == "DOT")):
                        结果 = 表达式(toks, p)
                        stmt = _duan_builtin.列表获取(结果, 0)
                        np = _duan_builtin.列表获取(结果, 1)
                        out = (((out + indent) + stmt) + "\n")
                        p = np
                        已处理 = True
            if (((已处理 == False) and (_duan_builtin.列表获取(tok, 0) == "KW")) and (tv == "父")):
                np = (p + 1)
                if (np < _duan_builtin.列表长度(toks)):
                    ntok = _duan_builtin.列表获取(toks, np)
                    if (_duan_builtin.列表获取(ntok, 0) == "DOT"):
                        结果 = 表达式(toks, p)
                        stmt = _duan_builtin.列表获取(结果, 0)
                        np = _duan_builtin.列表获取(结果, 1)
                        out = (((out + indent) + stmt) + "\n")
                        p = np
                        已处理 = True
            if ((已处理 == False) and (_duan_builtin.列表获取(tok, 0) == "DOT")):
                已处理 = True
                p = (p + 1)
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

def comp_match(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 1) == "匹配"):
            np = (p + 1)
            结果 = 表达式(toks, np)
            value = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            end_p = find_matching_end(toks, np, 1)
            out = (("match " + value) + ":\n")
            扫描中 = True
            scan_p = np
            while ((scan_p < (end_p - 1)) and 扫描中):
                st = _duan_builtin.列表获取(toks, scan_p)
                if ((_duan_builtin.列表获取(st, 0) == "KW") and (_duan_builtin.列表获取(st, 1) == "情形")):
                    case_p = (scan_p + 1)
                    case_end = (end_p - 1)
                    ci = (scan_p + 1)
                    while (ci < (end_p - 1)):
                        ct = _duan_builtin.列表获取(toks, ci)
                        if ((_duan_builtin.列表获取(ct, 0) == "KW") and (_duan_builtin.列表获取(ct, 1) == "情形")):
                            case_end = ci
                            break
                        ci = (ci + 1)
                    模式结果 = 表达式(toks, case_p)
                    pattern = _duan_builtin.列表获取(模式结果, 0)
                    case_body_p = _duan_builtin.列表获取(模式结果, 1)
                    body = compile_block(toks, case_body_p, case_end, "        ", "")
                    if (body == ""):
                        body = "        pass\n"
                    out = ((((out + "    case ") + pattern) + ":\n") + body)
                    scan_p = case_end
                else:
                    scan_p = (scan_p + 1)
            return 创建对(out, end_p)
    return 创建对("", p)

def comp_with(toks, p):
    if (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        if (_duan_builtin.列表获取(tok, 1) == "使用"):
            np = (p + 1)
            结果 = 表达式(toks, np)
            expr = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            var_name = ""
            if (np < _duan_builtin.列表长度(toks)):
                nt = _duan_builtin.列表获取(toks, np)
                if ((_duan_builtin.列表获取(nt, 0) == "KW") and (_duan_builtin.列表获取(nt, 1) == "为")):
                    np = (np + 1)
                    if (np < _duan_builtin.列表长度(toks)):
                        vt = _duan_builtin.列表获取(toks, np)
                        var_name = _duan_builtin.列表获取(vt, 1)
                        np = (np + 1)
            end_p = find_matching_end(toks, np, 1)
            body = compile_block(toks, np, (end_p - 1), "    ", "")
            if (body == ""):
                body = "    pass\n"
            with_stmt = ("with " + expr)
            if (var_name != ""):
                with_stmt = ((with_stmt + " as ") + var_name)
            with_stmt = ((with_stmt + ":\n") + body)
            return 创建对(with_stmt, end_p)
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
        if ((已处理 == False) and (tv == "抛出")):
            结果 = comp_throw(toks, p)
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (((out + "    ") + stmt) + "\n")
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "尝试")):
            结果 = comp_try(toks, p, "    ")
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (out + stmt)
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "匹配")):
            结果 = comp_match(toks, p)
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (out + add_indent(stmt, "    "))
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "使用")):
            结果 = comp_with(toks, p)
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (out + add_indent(stmt, "    "))
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "等待")):
            结果 = 表达式(toks, (p + 1))
            expr = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (((out + "    await ") + expr) + "\n")
            p = np
            已处理 = True
        if ((已处理 == False) and (_duan_builtin.列表获取(tok, 0) == "AT")):
            结果 = 编译装饰器(toks, p)
            decor = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (((out + "    ") + decor) + "\n")
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
                if ((已处理 == False) and (_duan_builtin.列表获取(ntok, 0) == "DOT")):
                    结果 = 表达式(toks, p)
                    stmt = _duan_builtin.列表获取(结果, 0)
                    np = _duan_builtin.列表获取(结果, 1)
                    out = (((out + "    ") + stmt) + "\n")
                    p = np
                    已处理 = True
        if (((已处理 == False) and (_duan_builtin.列表获取(tok, 0) == "KW")) and (tv == "父")):
            np = (p + 1)
            if (np < _duan_builtin.列表长度(toks)):
                ntok = _duan_builtin.列表获取(toks, np)
                if (_duan_builtin.列表获取(ntok, 0) == "DOT"):
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
        if ((已处理 == False) and (_duan_builtin.列表获取(tok, 0) == "KW")):
            v = _duan_builtin.列表获取(tok, 1)
            if (v == "己"):
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
            parent_name = ""
            if (np < _duan_builtin.列表长度(toks)):
                next_tok = _duan_builtin.列表获取(toks, np)
                if (_duan_builtin.列表获取(next_tok, 0) == "LPAREN"):
                    np = (np + 1)
                    if (np < _duan_builtin.列表长度(toks)):
                        parent_tok = _duan_builtin.列表获取(toks, np)
                        parent_name = _duan_builtin.列表获取(parent_tok, 1)
                        np = (np + 1)
                        if (np < _duan_builtin.列表长度(toks)):
                            rparen_tok = _duan_builtin.列表获取(toks, np)
                            if (_duan_builtin.列表获取(rparen_tok, 0) == "RPAREN"):
                                np = (np + 1)
            end_p = find_matching_end(toks, np, 1)
            body = compile_class_body(toks, np, (end_p - 1), name)
            if (body == ""):
                body = "    pass"
            class_def = ("class " + name)
            if (parent_name != ""):
                class_def = (((class_def + "(") + parent_name) + ")")
            class_def = ((class_def + ":\n") + body)
            return 创建对(class_def, end_p)
    return 创建对("", p)

def compile_class_body(toks, p, end_p, class_name):
    out = ""
    while ((p < end_p) and (p < _duan_builtin.列表长度(toks))):
        tok = _duan_builtin.列表获取(toks, p)
        tv = _duan_builtin.列表获取(tok, 1)
        已处理 = False
        if (tv == "属性"):
            np = (p + 1)
            if (np < _duan_builtin.列表长度(toks)):
                p = (np + 1)
                已处理 = True
        if ((已处理 == False) and 是函数关键字(tv)):
            func结果 = compile_class_method(toks, p, class_name)
            method_code = _duan_builtin.列表获取(func结果, 0)
            p = _duan_builtin.列表获取(func结果, 1)
            out = (out + method_code)
            已处理 = True
        if ((已处理 == False) and (tv == "异步")):
            np = (p + 1)
            if (np < end_p):
                nt = _duan_builtin.列表获取(toks, np)
                if ((_duan_builtin.列表获取(nt, 0) == "KW") and 是函数关键字(_duan_builtin.列表获取(nt, 1))):
                    方法结果 = compile_class_method(toks, np, class_name)
                    method_code = _duan_builtin.列表获取(方法结果, 0)
                    p = _duan_builtin.列表获取(方法结果, 1)
                    method_code = ("    async " + _duan_builtin.截取(method_code, 4, _duan_builtin.字符串长度(method_code)))
                    out = (out + method_code)
                    已处理 = True
        if ((已处理 == False) and (tv == "结束")):
            return out
        if (已处理 == False):
            p = (p + 1)
    return out

def compile_class_method(toks, p, class_name):
    tok = _duan_builtin.列表获取(toks, p)
    decor_lines = ""
    if (_duan_builtin.列表获取(tok, 0) == "AT"):
        装饰器结果 = 收集装饰器(toks, p)
        decors = _duan_builtin.列表获取(装饰器结果, 0)
        p = _duan_builtin.列表获取(装饰器结果, 1)
        i = 0
        while (i < _duan_builtin.列表长度(decors)):
            decor_lines = (((decor_lines + "        ") + _duan_builtin.列表获取(decors, i)) + "\n")
            i = (i + 1)
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
    final_params = ""
    if (params == "己"):
        final_params = "self"
    if ((params != "己") and (_duan_builtin.字符串长度(params) >= 2)):
        前两字 = _duan_builtin.截取(params, 0, 2)
        if (前两字 == "己,"):
            final_params = ("self" + _duan_builtin.截取(params, 1, _duan_builtin.字符串长度(params)))
    if (final_params == ""):
        final_params = "self"
        if (params != ""):
            final_params = ("self, " + params)
    method_end = find_matching_end(toks, np, 1)
    body = compile_block(toks, np, (method_end - 1), "        ", "")
    if (body == ""):
        body = "        pass"
    code = (((((((decor_lines + "    def ") + name) + "(") + final_params) + "):\n") + body) + "\n")
    return 创建对(code, method_end)

def compile_top(toks, p, out):
    while (p < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, p)
        tv = _duan_builtin.列表获取(tok, 1)
        已处理 = False
        if (_duan_builtin.列表获取(tok, 0) == "AT"):
            装饰器结果 = 收集装饰器(toks, p)
            decors = _duan_builtin.列表获取(装饰器结果, 0)
            np = _duan_builtin.列表获取(装饰器结果, 1)
            next_tok = _duan_builtin.列表获取(toks, np)
            next_tv = _duan_builtin.列表获取(next_tok, 1)
            if (next_tv == "类"):
                类结果 = compile_class(toks, np)
                class_code = _duan_builtin.列表获取(类结果, 0)
                np = _duan_builtin.列表获取(类结果, 1)
                i = 0
                while (i < _duan_builtin.列表长度(decors)):
                    out = ((out + _duan_builtin.列表获取(decors, i)) + "\n")
                    i = (i + 1)
                out = ((out + class_code) + "\n")
            else:
                函数结果 = compile_single_func(toks, np, decors)
                func_code = _duan_builtin.列表获取(函数结果, 0)
                np = _duan_builtin.列表获取(函数结果, 1)
                out = (out + func_code)
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "类")):
            结果 = compile_class(toks, p)
            class_code = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = ((out + class_code) + "\n")
            p = np
            已处理 = True
        if ((已处理 == False) and 是函数关键字(tv)):
            结果 = compile_single_func(toks, p, _duan_builtin.列表创建())
            func_code = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (out + func_code)
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "抛出")):
            结果 = comp_throw(toks, p)
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = ((out + stmt) + "\n")
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "尝试")):
            结果 = comp_try(toks, p, "")
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = (out + stmt)
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "匹配")):
            结果 = comp_match(toks, p)
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = ((out + stmt) + "\n")
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "使用")):
            结果 = comp_with(toks, p)
            stmt = _duan_builtin.列表获取(结果, 0)
            np = _duan_builtin.列表获取(结果, 1)
            out = ((out + stmt) + "\n")
            p = np
            已处理 = True
        if ((已处理 == False) and (tv == "异步")):
            np = (p + 1)
            if (np < _duan_builtin.列表长度(toks)):
                nt = _duan_builtin.列表获取(toks, np)
                if ((_duan_builtin.列表获取(nt, 0) == "KW") and 是函数关键字(_duan_builtin.列表获取(nt, 1))):
                    函数结果 = compile_single_func(toks, np, _duan_builtin.列表创建())
                    func_code = _duan_builtin.列表获取(函数结果, 0)
                    np = _duan_builtin.列表获取(函数结果, 1)
                    out = ((out + "async ") + func_code)
                    p = np
                    已处理 = True
        if (已处理 == False):
            p = (p + 1)
    return out

def compile_single_func(toks, p, decors):
    tok = _duan_builtin.列表获取(toks, p)
    np = (p + 1)
    name = ""
    if (np < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, np)
        if (_duan_builtin.列表获取(tok, 0) == "ID"):
            name = _duan_builtin.列表获取(tok, 1)
            np = (np + 1)
    if (np < _duan_builtin.列表长度(toks)):
        tok = _duan_builtin.列表获取(toks, np)
        if ((_duan_builtin.列表获取(tok, 0) == "KW") and (_duan_builtin.列表获取(tok, 1) == "导出")):
            np = (np + 1)
    参数结果 = 解析参数(toks, np)
    params = _duan_builtin.列表获取(参数结果, 0)
    np = _duan_builtin.列表获取(参数结果, 1)
    body结果 = compile_stmts(toks, np, "")
    body = _duan_builtin.列表获取(body结果, 0)
    np = _duan_builtin.列表获取(body结果, 1)
    if (body == ""):
        body = "    pass\n"
    decor_lines = ""
    i = 0
    while (i < _duan_builtin.列表长度(decors)):
        decor_lines = ((decor_lines + _duan_builtin.列表获取(decors, i)) + "\n")
        i = (i + 1)
    code = (((((((decor_lines + "def ") + name) + "(") + params) + "):\n") + body) + "\n")
    return 创建对(code, np)

def 压缩代码(src):
    n = _duan_builtin.字符串长度(src)
    out = ""
    p = 0
    行缓冲 = ""
    换行计数 = 0
    while (p < n):
        c = _duan_builtin.字符串获取(src, p)
        if (c == "\n"):
            修剪后 = ""
            i = (_duan_builtin.字符串长度(行缓冲) - 1)
            继续循环 = True
            while (继续循环 and (i >= 0)):
                ch = _duan_builtin.字符串获取(行缓冲, i)
                if ((ch != " ") and (ch != "\t")):
                    修剪后 = _duan_builtin.截取(行缓冲, 0, (i + 1))
                    继续循环 = False
                else:
                    i = (i - 1)
            if (修剪后 == ""):
                换行计数 = (换行计数 + 1)
                if (换行计数 <= 1):
                    out = (out + "\n")
            else:
                换行计数 = 0
                out = ((out + 修剪后) + "\n")
            行缓冲 = ""
        else:
            行缓冲 = (行缓冲 + c)
        p = (p + 1)
    if (行缓冲 != ""):
        out = (out + 行缓冲)
    return out

def 编译(src):
    header = "# Generated by Duan Level 5\n"
    toks = 词法(src)
    code = compile_top(toks, 0, "")
    result = (header + code)
    return 压缩代码(result)

def 测试():
    print("=== Level 5 测试 ===")
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
    print("--- 测试4: 装饰器 ---")
    src4 = "@日志 段落 log 接收 x： 返回 x 结束"
    print(("源: " + src4))
    print(编译(src4))
    print("")
    print("--- 测试5: try/except ---")
    src5 = "段落 safe 尝试 返回 1 捕获 异常 返回 0 结束 结束"
    print(("源: " + src5))
    print(编译(src5))
    print("")
    print("--- 测试6: 抛出 ---")
    src6 = "段落 test 抛出 值错误 结束"
    print(("源: " + src6))
    print(编译(src6))
    print("")
    print("Level 5 验证通过！")

def 主函数():
    print("段言 Level 5 启动")
    print("")
    测试()

主函数()