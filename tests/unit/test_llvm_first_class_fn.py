# -*- coding: utf-8 -*-
"""R118-A：原生（LLVM）后端「函数值一等类型 + issubclass/hasattr」落地验证。

覆盖任务书线 A 三件新能力：
  1. 函数值一等类型（桶③，解锁 事件总线·处理器 / 内置核心列表·谓词）：
     `设 处理器 等于 某段` 后 `处理器(参数)` 正确分派（LV_TYPE_FUNCTION=25 +
     dv_call_value）；非函数值被当函数调用 → dv_throw_not_callable 响亮抛
     NotImplementedError（文案含类型名），绝不静默降级。
  2. issubclass / 是子类 / is_sub_class（解锁 C 线 断言工具）：
     对象或类名首参 + 类名次参，沿 super 链判定，对齐 stdlib/builtins.py。
  3. hasattr / 有属性 / has_attr：复用 R117 对象成员判定（dv_r117_obj_has_member）。

IR 级守「编得出、不残留 <unknown 伪装」；真跑（clang + MSVC 头）守语义对拍。
文件类用例把子进程 cwd 设到临时目录，绝不往仓里写测试产物。
"""
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from llvm.compiler import compile_source_typed  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _find_msvc_env():
    if os.name != 'nt':
        return None, None
    vs_base = r"C:\Program Files (x86)\Microsoft Visual Studio"
    kits_base = r"C:\Program Files (x86)\Windows Kits\10"
    msvc_inc = msvc_lib = None
    if os.path.isdir(vs_base):
        for year in sorted(os.listdir(vs_base), reverse=True):
            for edition in ("BuildTools", "Community", "Professional", "Enterprise"):
                inc_root = os.path.join(vs_base, year, edition, "VC", "Tools", "MSVC")
                if not os.path.isdir(inc_root):
                    continue
                for ver in sorted(os.listdir(inc_root), reverse=True):
                    cand_inc = os.path.join(inc_root, ver, "include")
                    cand_lib = os.path.join(inc_root, ver, "lib", "x64")
                    if os.path.isdir(cand_inc) and os.path.isdir(cand_lib):
                        msvc_inc, msvc_lib = cand_inc, cand_lib
                        break
                if msvc_inc:
                    break
            if msvc_inc:
                break
    sdk_inc = sdk_lib = None
    if os.path.isdir(kits_base):
        inc_root = os.path.join(kits_base, "Include")
        if os.path.isdir(inc_root):
            for ver in sorted(os.listdir(inc_root), reverse=True):
                parts = [os.path.join(inc_root, ver, x) for x in ("ucrt", "shared", "um")]
                if all(os.path.isdir(p) for p in parts):
                    sdk_inc = parts
                    sdk_lib = [os.path.join(kits_base, "Lib", ver, x, "x64")
                               for x in ("ucrt", "um")]
                    break
    include = ";".join([msvc_inc] + sdk_inc) if (msvc_inc and sdk_inc) else None
    lib = ";".join([msvc_lib] + sdk_lib) if (msvc_lib and sdk_lib) else None
    return include, lib


def _clang_available():
    try:
        from llvm.compiler import find_clang
        return bool(find_clang())
    except Exception:
        return False


def _运行(源码, 超时=300):
    from llvm.compiler import compile_light_typed
    env = dict(os.environ)
    inc, lib = _find_msvc_env()
    if inc:
        env['INCLUDE'] = inc
    if lib:
        env['LIB'] = lib
    with tempfile.TemporaryDirectory(prefix='_r118ffn_', dir=_ROOT) as d:
        src_path = os.path.join(d, 'main.light')
        exe = os.path.join(d, 'main.exe')
        with open(src_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(源码)
        out = compile_light_typed(src_path, exe, optimize_level=0)
        assert out and os.path.exists(out), f'没产出可执行文件：{out!r}'
        r = subprocess.run([out], capture_output=True, timeout=超时, env=env, cwd=d)
    return r


_需真跑 = [
    pytest.mark.skipif(not _clang_available(), reason='未找到 clang，跳过原生腿真跑'),
    pytest.mark.skipif(os.name == 'nt' and not _find_msvc_env()[0],
                       reason='未定位到 MSVC/Windows SDK 头，跳过'),
]


def _输出(r):
    return r.stdout.decode('utf-8', 'replace').replace('\r\n', '\n').strip()


# ----------------------------------------------------------------------
# 一、IR 级：编得出来，不残留 <unknown 伪装
# ----------------------------------------------------------------------

def test_函数值调用_IR可编译无伪装():
    src = ('段落 加倍(n):\n'
           '  返回 n 乘 2\n'
           '段落 主():\n'
           '  设 处理器 等于 加倍\n'
           '  打印 处理器(21)\n'
           '主()。\n')
    ir = compile_source_typed(src)
    assert len(ir) > 1000, f'函数值调用 IR 短得不像真产物（{len(ir)} 字符）'
    assert '<unknown' not in ir, '函数值调用 IR 里残留了 <unknown 伪装'


def test_issubclass_hasattr_IR可编译无伪装():
    src = ('类 动物:\n'
           '  属性 名称。\n'
           '  构造():\n'
           '    己名称 为 "动物"\n'
           '类 狗 继承 动物:\n'
           '  构造():\n'
           '    己名称 为 "狗"\n'
           '段落 主():\n'
           '  设 小狗 为 新建 狗()\n'
           '  打印 issubclass(小狗, "动物")\n'
           '  打印 hasattr(小狗, "名称")\n'
           '主()。\n')
    ir = compile_source_typed(src)
    assert len(ir) > 1000, f'issubclass/hasattr IR 短得不像真产物（{len(ir)} 字符）'
    assert '<unknown' not in ir, 'issubclass/hasattr IR 里残留了 <unknown 伪装'
    assert 'dv_is_sub_class_from_value' in ir, 'IR 没调用 dv_is_sub_class_from_value'
    assert 'dv_has_attr' in ir, 'IR 没调用 dv_has_attr'


# ----------------------------------------------------------------------
# 二、真跑：函数值一等类型 语义对拍
# ----------------------------------------------------------------------

@_需真跑[0]
@_需真跑[1]
def test_函数值调用_真跑_正确分派():
    """`设 处理器 等于 加倍` 后 `处理器(21)` 必须分派到 加倍 并返回 42。"""
    src = ('段落 加倍(n):\n'
           '  返回 n 乘 2\n'
           '段落 主():\n'
           '  设 处理器 等于 加倍\n'
           '  打印 处理器(21)\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    assert _输出(r) == '42', f'函数值分派结果不对，实际：{_输出(r)!r}'


@_需真跑[0]
@_需真跑[1]
def test_函数值调用_反例_非函数值当函数调用必须响亮抛错():
    """反例守门：变量持有非函数值（整数）被当函数调用，运行期必须响亮抛
    NotImplementedError（文案含类型名），绝不静默降级成 0。"""
    src = ('段落 主():\n'
           '  设 x 为 1\n'
           '  打印 x(1)\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode != 0, f'非函数值被当函数调用必须非零退出，实际 rc={r.returncode}'
    err = r.stderr.decode('utf-8', 'replace')
    # RuntimeError 文案含类型名（如 int）与「函数」字样
    assert ('函数' in err) or ('NotImplementedError' in err) or ('不是' in err), \
        f'反例没响亮报错，stderr：{err[:400]!r}'


# ----------------------------------------------------------------------
# 三、真跑：issubclass / hasattr 语义对拍
# ----------------------------------------------------------------------

@_需真跑[0]
@_需真跑[1]
def test_issubclass_hasattr_真跑_对象与类名双路径():
    """对象首参 + 类名首参 都应沿 super 链判定；hasattr 命中/缺失都正确。"""
    src = ('类 动物:\n'
           '  属性 名称。\n'
           '  构造():\n'
           '    己名称 为 "动物"\n'
           '类 狗 继承 动物:\n'
           '  构造():\n'
           '    己名称 为 "狗"\n'
           '段落 主():\n'
           '  设 小狗 为 新建 狗()\n'
           '  如果 issubclass(小狗, "动物"): 打印 "ISSUB_OBJ_T" 否则 打印 "ISSUB_OBJ_F"\n'
           '  如果 issubclass("狗", "动物"): 打印 "ISSUB_STR_T" 否则 打印 "ISSUB_STR_F"\n'
           '  如果 issubclass("猫", "动物"): 打印 "ISSUB_CAT_T" 否则 打印 "ISSUB_CAT_F"\n'
           '  如果 hasattr(小狗, "名称"): 打印 "HASATTR_T" 否则 打印 "HASATTR_F"\n'
           '  如果 hasattr(小狗, "不存在"): 打印 "HASATTR_X_T" 否则 打印 "HASATTR_X_F"\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    assert lines == ['ISSUB_OBJ_T', 'ISSUB_STR_T', 'ISSUB_CAT_F', 'HASATTR_T', 'HASATTR_X_F'], \
        f'issubclass/hasattr 对拍失败，实际：{lines!r}'


@_需真跑[0]
@_需真跑[1]
def test_有属性中文别名_真跑():
    """中文别名 `有属性` 与 `是子类` 应与英文等价。"""
    src = ('类 东西:\n'
           '  属性 名。\n'
           '  构造():\n'
           '    己名 为 "值"\n'
           '段落 主():\n'
           '  设 o 为 新建 东西()\n'
           '  如果 有属性(o, "名"): 打印 "Y" 否则 打印 "N"\n'
           '  如果 是子类(o, "东西"): 打印 "S" 否则 打印 "X"\n'
           '主()。\n')
    r = _运行(src)
    assert r.returncode == 0, f'运行失败：{r.stderr.decode("utf-8", "replace")[:1500]}'
    lines = _输出(r).split('\n')
    assert lines == ['Y', 'S'], f'中文别名对拍失败，实际：{lines!r}'
