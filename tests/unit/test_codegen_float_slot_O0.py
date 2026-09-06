"""T7A 定向测试：O0 下 float DV 类型推断/slot 管理根因修复。

6 个最小复现 + 对拍，验证 T5A-01/02/03/04/06 + T6A-08 在 O0 下根因消除。
"""
import math
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


def _编译并运行(code: str, optimize_level: int = 0):
    """编译并运行 .light 代码，返回 (rc, stdout, stderr)。"""
    from llvm.compiler import compile_light_typed
    with tempfile.NamedTemporaryFile(
        suffix='.light', mode='w', encoding='utf-8', delete=False
    ) as f:
        f.write(code)
        src_path = f.name
    exe_path = src_path.replace('.light', '.exe')
    compile_light_typed(src_path, exe_path, optimize_level=optimize_level)
    r = subprocess.run([exe_path], capture_output=True, timeout=30)
    try:
        os.unlink(src_path)
        os.unlink(exe_path)
    except OSError:
        pass
    return r.returncode, r.stdout.decode('utf-8', errors='replace'), r.stderr.decode('utf-8', errors='replace')


def _解析输出(stdout: str):
    lines = [l.strip() for l in stdout.strip().splitlines() if l.strip()]
    return [float(l) for l in lines]


def _近似比较(实际, 期望, tol=1e-4):
    if len(实际) != len(期望):
        return False, f"长度不符: 实际{len(实际)} 期望{len(期望)}"
    for i, (a, e) in enumerate(zip(实际, 期望)):
        if abs(a - e) > tol:
            return False, f"第{i}行: 实际={a} 期望={e} diff={abs(a-e)}"
    return True, ""


# ── T5A-02: int/int 除法结果在后续算术中被零初始化 ──
def test_T5A_02_int_div_arithmetic():
    """设 q 为 10/3; q*2 结果应为 6.66667 而非 0 或垃圾值。"""
    code = (
        '段落 主:\n'
        '  设 q 为 10/3\n'
        '  输出(q)\n'
        '  设 r 为 q * 2\n'
        '  输出(r)\n'
        '  设 s 为 q + 1.0\n'
        '  输出(s)\n'
    )
    rc, out, err = _编译并运行(code, 0)
    assert rc == 0, f"T5A-02 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [10/3, (10/3)*2, (10/3)+1.0]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"T5A-02 对拍失败: {msg}\n实际={实际}\n期望={期望}"


# ── T5A-01: 跨段 float 返回值在算术中被零初始化 ──
def test_T5A_01_cross_seg_float_return():
    """设 m 为 均值(d); m*2 结果应为 5.0 而非 0 或垃圾值。"""
    code = (
        '段落 均值 接收 d:\n'
        '  设 n 为 长(d)\n'
        '  如果 n == 0:\n'
        '    返回 0.0\n'
        '  设 s 为 0\n'
        '  设 i 为 0\n'
        '  当 i < n:\n'
        '    设 s 为 s + d[i]\n'
        '    设 i 为 i + 1\n'
        '  返回 s / n\n'
        '\n'
        '段落 主:\n'
        '  设 d 为 [1, 2, 3, 4]\n'
        '  设 m 为 均值(d)\n'
        '  输出(m)\n'
        '  输出(m * 2)\n'
        '  输出(m + 0.0)\n'
        '  输出(m * 3)\n'
    )
    rc, out, err = _编译并运行(code, 0)
    assert rc == 0, f"T5A-01 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [2.5, 5.0, 2.5, 7.5]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"T5A-01 对拍失败: {msg}\n实际={实际}\n期望={期望}"


# ── T5A-01b: 跨段 int 参数除法 ──
def test_T5A_01b_cross_seg_param_div():
    """段内 int 参数做 / 除法，返回值在主段算术正确。"""
    code = (
        '段落 div_in_seg 接收 a, b:\n'
        '  返回 a / b\n'
        '\n'
        '段落 主:\n'
        '  设 r 为 div_in_seg(10, 4)\n'
        '  输出(r)\n'
        '  输出(r * 2)\n'
        '  输出(r + 0.0)\n'
    )
    rc, out, err = _编译并运行(code, 0)
    assert rc == 0, f"T5A-01b 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [2.5, 5.0, 2.5]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"T5A-01b 对拍失败: {msg}\n实际={实际}\n期望={期望}"


# ── T5A-03: builtin 平方根() 返回值存入变量后在算术中正确 ──
def test_T5A_03_builtin_sqrt_arithmetic():
    """设 s 为 平方根(2.0); s*s 结果应近似 2.0 而非 0。"""
    code = (
        '段落 主:\n'
        '  设 s 为 平方根(2.0)\n'
        '  输出(s)\n'
        '  输出(s * s)\n'
        '  设 s2 为 平方根(9.0)\n'
        '  输出(s2)\n'
        '  输出(s2 * 2)\n'
    )
    rc, out, err = _编译并运行(code, 0)
    assert rc == 0, f"T5A-03 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [math.sqrt(2), math.sqrt(2)**2, math.sqrt(9), math.sqrt(9)*2]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"T5A-03 对拍失败: {msg}\n实际={实际}\n期望={期望}"


# ── T5A-04: float 字面量作为用户段函数参数时正确 ──
def test_T5A_04_float_param():
    """float 参数传入用户段函数后参与算术正确。"""
    code = (
        '段落 compute 接收 x:\n'
        '  输出(x)\n'
        '  输出(x * 2.0)\n'
        '  输出(x / 2.0)\n'
        '  返回 x * 3.0\n'
        '\n'
        '段落 主:\n'
        '  设 r 为 compute(2.718)\n'
        '  输出(r)\n'
        '  设 v 为 compute(3.14)\n'
        '  输出(v)\n'
        '  输出(v * 2)\n'
    )
    rc, out, err = _编译并运行(code, 0)
    assert rc == 0, f"T5A-04 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [2.718, 5.436, 1.359, 8.154, 3.14, 6.28, 1.57, 9.42, 18.84]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"T5A-04 对拍失败: {msg}\n实际={实际}\n期望={期望}"


# ── T5A-06: 自然对数 float 参数不被零初始化 ──
def test_T5A_06_natural_log():
    """自然对数(2.718...) 应返回 1.0 而非超时或 0。"""
    code = (
        '从 数学 导入 自然对数\n'
        '段落 主:\n'
        '  输出(自然对数(2.718281828459045))\n'
        '  输出(自然对数(1.0))\n'
        '  输出(自然对数(10.0))\n'
    )
    rc, out, err = _编译并运行(code, 0)
    assert rc == 0, f"T5A-06 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [1.0, 0.0, math.log(10)]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"T5A-06 对拍失败: {msg}\n实际={实际}\n期望={期望}"


# ── T6A-08: builtin 整除结果参与后续算术正确 ──
def test_T6A_08_builtin_div_arithmetic():
    """整除(宽度-n, 2) 应返回正确整数而非恒 0。"""
    code = (
        '段落 主:\n'
        '  设 宽度 为 20\n'
        '  设 n 为 4\n'
        '  设 左 为 整除(宽度 - n, 2)\n'
        '  输出(左)\n'
        '  输出(左 * 3)\n'
        '  设 左2 为 整除(15, 2)\n'
        '  输出(左2)\n'
    )
    rc, out, err = _编译并运行(code, 0)
    assert rc == 0, f"T6A-08 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [8, 24, 7]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"T6A-08 对拍失败: {msg}\n实际={实际}\n期望={期望}"


# ── stdlib 对拍：数学.light ──
def test_stdlib_数学_对拍():
    """移除 workaround 后的数学.light 与 Python math 对拍。"""
    code = (
        '从 数学 导入 自然对数 常用对数 对数2 对数 指数 平方根\n'
        '段落 主:\n'
        '  输出(自然对数(2.718281828459045))\n'
        '  输出(常用对数(1000.0))\n'
        '  输出(对数2(8.0))\n'
        '  输出(对数(100.0, 10.0))\n'
        '  输出(指数(1.0))\n'
        '  输出(平方根(2.0))\n'
        '  输出(平方根(2.0) * 平方根(2.0))\n'
    )
    rc, out, err = _编译并运行(code, 0)
    assert rc == 0, f"stdlib 数学 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [1.0, 3.0, 3.0, 2.0, math.e, math.sqrt(2), 2.0]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"stdlib 数学 对拍失败: {msg}\n实际={实际}\n期望={期望}"


# ── stdlib 对拍：统计.light ──
def test_stdlib_统计_对拍():
    """移除 workaround 后的统计.light 与 Python statistics 对拍。"""
    code = (
        '从 统计 导入 均值 方差 标准差 相关系数 标准化 中位数\n'
        '段落 主:\n'
        '  设 d 为 [1, 2, 3, 4, 5]\n'
        '  输出(均值(d))\n'
        '  输出(方差(d))\n'
        '  输出(标准差(d))\n'
        '  输出(中位数(d))\n'
        '  设 d2 为 [2, 4, 6, 8, 10]\n'
        '  输出(相关系数(d, d2))\n'
        '  设 z 为 标准化(d)\n'
        '  设 i 为 0\n'
        '  当 i < 长(z):\n'
        '    输出(z[i])\n'
        '    设 i 为 i + 1\n'
    )
    rc, out, err = _编译并运行(code, 0)
    assert rc == 0, f"stdlib 统计 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    m = 3.0
    var = sum((x - m)**2 for x in [1,2,3,4,5]) / 5
    std = math.sqrt(var)
    z = [(x - m) / std for x in [1,2,3,4,5]]
    期望 = [m, var, std, 3.0, 1.0] + z
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"stdlib 统计 对拍失败: {msg}\n实际={实际}\n期望={期望}"


# ── stdlib 对拍：格式化.light 文本居中 ──
def test_stdlib_格式化_文本居中_对拍():
    """移除 workaround 后的格式化.light 文本居中与 Python str.center 对拍。"""
    code = (
        '从 格式化 导入 文本居中\n'
        '段落 主:\n'
        '  输出(文本居中("hi", 10))\n'
        '  输出(文本居中("hello", 11))\n'
        '  输出(文本居中("test", 8, "-"))\n'
        '  输出(文本居中("abc", 7, "."))\n'
        '  输出(文本居中("x", 5))\n'
    )
    rc, out, err = _编译并运行(code, 0)
    assert rc == 0, f"stdlib 格式化 段错误 rc={rc}\nstderr={err}"
    # 不对整体 strip——居中结果可能带前导空格
    lines = [line for line in out.splitlines() if line != '']
    # 跳过可能的空行/末尾换行
    lines = [l for l in lines if l.strip() or ' ' in l]
    期望 = [
        "hi".center(10),
        "hello".center(11),
        "test".center(8, "-"),
        "abc".center(7, "."),
        "x".center(5),
    ]
    assert len(lines) >= len(期望), f"行数不足: 实际={len(lines)} 期望>={len(期望)}\n实际={lines}"
    for i in range(len(期望)):
        a = lines[i]
        e = 期望[i]
        assert a == e, f"第{i}行: 实际='{a}' 期望='{e}' (len: {len(a)} vs {len(e)})"
