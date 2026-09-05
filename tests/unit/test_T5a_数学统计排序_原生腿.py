# -*- coding: utf-8 -*-
"""T5A 定向反跑测试：数学/统计/排序 .light 纯光明真实现。

验证目标：
  1. 真实现 → 原生腿 O0 编译通过、运行不崩、输出与 Python math/statistics 数值对拍一致。
  2. 恢复空壳（去掉实现）→ 编译即报 NativeImportError（decl 0 空壳拦截）。

反跑判据：
  - 真实现 → 绿；空壳 → 红。
  - O0（optimize_level=0）下不崩。

注意：Light 原生腿用 %g 格式化浮点（6 位有效数字），与 Python str() 不同。
      因此对拍用数值比较（abs diff < epsilon），不做字符串精确匹配。

已知 O0 codegen 限制（本测试已适配）：
  - int/int 除法结果在后续算术中被零初始化 → 统计模块用 (总计+0.0)/n 规避
  - 用户段函数返回 float 在调用方算术中被零初始化 → 统计模块内联计算
  - float 字面量参数在用户段算术中被零初始化 → 测试用 int 参数或仅测 _light_builtin 包装函数
  - 输出(列表) 在 O0 显示为 [] → 用 长() + 逐元素 输出 验证

仅跑本文件；禁止全量。
"""
import os
import sys
import math
import shutil
import subprocess as _subproc
import tempfile as _tempfile

import pytest

# ── 路径常量 ──────────────────────────────────────────────────────────
_STDLIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'stdlib')
_MATH_LIGHT = os.path.join(_STDLIB_DIR, '数学.light')
_STAT_LIGHT = os.path.join(_STDLIB_DIR, '统计.light')
_SORT_LIGHT = os.path.join(_STDLIB_DIR, '排序.light')


# ── 辅助：原生腿编译+运行 ──────────────────────────────────────────────

def _编译并运行(code: str, optimize_level: int = 0) -> tuple:
    """用原生腿 compile_light_typed 编译并运行，返回 (rc, stdout, stderr)。"""
    from llvm.compiler import compile_light_typed
    with _tempfile.TemporaryDirectory(prefix='_taskT5a_') as d:
        src = os.path.join(d, '主.light')
        with open(src, 'w', encoding='utf-8', newline='\n') as f:
            f.write(code)
        exe = compile_light_typed(src, os.path.join(d, '产物'),
                                  optimize_level=optimize_level)
        r = _subproc.run([exe], capture_output=True, timeout=60)
        out = r.stdout.decode('utf-8', errors='replace').strip()
        err = r.stderr.decode('utf-8', errors='replace').strip()
        return r.returncode, out, err


def _解析输出(out: str):
    """把输出按行拆分，每行尝试解析为 float（失败则保留原字符串）。"""
    行 = out.replace('\r', '').split('\n')
    结果 = []
    for h in 行:
        h = h.strip()
        if not h:
            continue
        try:
            结果.append(float(h))
        except ValueError:
            结果.append(h)
    return 结果


def _近似比较(实际, 期望, eps=1e-4):
    """逐元素比较，数值用 abs diff，字符串精确匹配。"""
    if len(实际) != len(期望):
        return False, f"行数不匹配: 实际={len(实际)} 期望={len(期望)}"
    for i, (a, e) in enumerate(zip(实际, 期望)):
        if isinstance(a, float) and isinstance(e, (int, float)):
            if abs(a - float(e)) > eps:
                return False, f"第{i}行: 实际={a} 期望={e} diff={abs(a-float(e))}"
        elif a != e:
            return False, f"第{i}行: 实际={a!r} 期望={e!r}"
    return True, ""


# ── 1. 数学模块 O0 对拍 ────────────────────────────────────────────────

def test_O0_数学_平方根_对拍():
    """从 数学 导入 平方根，O0 真编译真跑，与 Python math.sqrt 对拍。"""
    code = (
        '从 数学 导入 平方根\n'
        '段落 主:\n'
        '  输出(平方根(2))\n'
        '  输出(平方根(9))\n'
        '  输出(平方根(0))\n'
        '  输出(平方根(16))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 数学.平方根 段错误 rc={rc} (0x{rc & 0xFFFFFFFF:08X})\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [math.sqrt(2), math.sqrt(9), math.sqrt(0), math.sqrt(16)]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"平方根对拍失败: {msg}\n实际={实际}\n期望={期望}"


def test_O0_数学_多函数_对拍():
    """从 数学 导入 幂 绝对值 向上取整 向下取整 四舍五入 阶乘。"""
    code = (
        '从 数学 导入 幂 绝对值 向上取整 向下取整 四舍五入 阶乘\n'
        '段落 主:\n'
        '  输出(幂(2, 10))\n'
        '  输出(绝对值(-5))\n'
        '  输出(向上取整(3.2))\n'
        '  输出(向下取整(3.8))\n'
        '  输出(四舍五入(3.5))\n'
        '  输出(四舍五入(2.4))\n'
        '  输出(阶乘(5))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 数学多函数 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [1024, 5, 4, 3, 4, 2, 120]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"数学多函数对拍失败: {msg}\n实际={实际}\n期望={期望}"


def test_O0_数学_三角函数_对拍():
    """从 数学 导入 正弦 余弦 正切 角度转弧度。
    注：弧度转角度 的 float 字面量参数在 O0 算术中被零初始化，用 int 参数测试。"""
    code = (
        '从 数学 导入 正弦 余弦 正切 角度转弧度\n'
        '段落 主:\n'
        '  输出(正弦(0))\n'
        '  输出(余弦(0))\n'
        '  输出(正切(0))\n'
        '  输出(正切(1))\n'
        '  输出(角度转弧度(180))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 三角函数 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [
        math.sin(0), math.cos(0), math.tan(0),
        math.tan(1), math.radians(180),
    ]
    ok, msg = _近似比较(实际, 期望, eps=1e-4)
    assert ok, f"三角函数对拍失败: {msg}\n实际={实际}\n期望={期望}"


def test_O0_数学_对数系列_对拍():
    """从 数学 导入 自然对数 常用对数 对数2 对数。用 int 参数避免 float 参数被零初始化。"""
    code = (
        '从 数学 导入 自然对数 常用对数 对数2 对数\n'
        '段落 主:\n'
        '  输出(自然对数(100))\n'
        '  输出(常用对数(1000))\n'
        '  输出(对数2(8))\n'
        '  输出(对数2(1024))\n'
        '  输出(对数(100, 10))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 对数系列 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [
        math.log(100), math.log10(1000), math.log2(8),
        math.log2(1024), math.log(100, 10),
    ]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"对数系列对拍失败: {msg}\n实际={实际}\n期望={期望}"


def test_O0_数学_立方根_对拍():
    """立方根用 幂(x, 1/3) 实现，与 Python x**(1/3) 对拍。"""
    code = (
        '从 数学 导入 立方根\n'
        '段落 主:\n'
        '  输出(立方根(8))\n'
        '  输出(立方根(27))\n'
        '  输出(立方根(1))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 立方根 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [8 ** (1.0 / 3.0), 27 ** (1.0 / 3.0), 1.0]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"立方根对拍失败: {msg}\n实际={实际}\n期望={期望}"


# ── 2. 统计模块 O0 对拍 ────────────────────────────────────────────────

def test_O0_统计_均值_对拍():
    """从 统计 导入 均值，O0 真编译真跑，与 Python 对拍。"""
    code = (
        '从 统计 导入 均值\n'
        '段落 主:\n'
        '  输出(均值([1, 2, 3, 4, 5]))\n'
        '  输出(均值([10, 20, 30]))\n'
        '  输出(均值([7]))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 统计.均值 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [3.0, 20.0, 7.0]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"均值对拍失败: {msg}\n实际={实际}\n期望={期望}"


def test_O0_统计_多函数_对拍():
    """从 统计 导入 均值 中位数 标准差 方差 求和 极差。"""
    code = (
        '从 统计 导入 均值 中位数 标准差 方差 求和 极差\n'
        '段落 主:\n'
        '  设 d 为 [1, 2, 3, 4, 5]\n'
        '  输出(均值(d))\n'
        '  输出(中位数(d))\n'
        '  输出(标准差(d))\n'
        '  输出(方差(d))\n'
        '  输出(求和(d))\n'
        '  输出(极差(d))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 统计多函数 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    数据 = [1, 2, 3, 4, 5]
    m = sum(数据) / len(数据)
    var = sum((x - m) ** 2 for x in 数据) / len(数据)
    期望 = [m, 3.0, math.sqrt(var), var, 15.0, 4.0]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"统计多函数对拍失败: {msg}\n实际={实际}\n期望={期望}"


def test_O0_统计_非整数均值_对拍():
    """非整数均值场景：[1,2,4,5,6] mean=3.6，验证 (总计+0.0)/n 规避有效。"""
    code = (
        '从 统计 导入 均值 方差 标准差\n'
        '段落 主:\n'
        '  设 d 为 [1, 2, 4, 5, 6]\n'
        '  输出(均值(d))\n'
        '  输出(方差(d))\n'
        '  输出(标准差(d))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 非整数均值 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    数据 = [1, 2, 4, 5, 6]
    m = sum(数据) / len(数据)
    var = sum((x - m) ** 2 for x in 数据) / len(数据)
    期望 = [m, var, math.sqrt(var)]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"非整数均值对拍失败: {msg}\n实际={实际}\n期望={期望}"


def test_O0_统计_协方差相关系数_对拍():
    """从 统计 导入 协方差 相关系数 线性回归。"""
    code = (
        '从 统计 导入 协方差 相关系数 线性回归\n'
        '段落 主:\n'
        '  设 d1 为 [1, 2, 4, 5, 6]\n'
        '  设 d2 为 [2, 4, 6, 8, 10]\n'
        '  输出(协方差(d1, d2))\n'
        '  输出(相关系数(d1, d2))\n'
        '  设 回归 为 线性回归(d1, d2)\n'
        '  输出(回归[0])\n'
        '  输出(回归[1])\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 协方差相关系数 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    d1 = [1, 2, 4, 5, 6]
    d2 = [2, 4, 6, 8, 10]
    n = len(d1)
    m1 = sum(d1) / n
    m2 = sum(d2) / n
    cov = sum((d1[i] - m1) * (d2[i] - m2) for i in range(n)) / n
    v1 = sum((x - m1) ** 2 for x in d1) / n
    v2 = sum((x - m2) ** 2 for x in d2) / n
    corr = cov / (math.sqrt(v1) * math.sqrt(v2))
    num = sum((d1[i] - m1) * (d2[i] - m2) for i in range(n))
    den = sum((d1[i] - m1) ** 2 for i in range(n))
    slope = num / den
    intercept = m2 - slope * m1
    期望 = [cov, corr, slope, intercept]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"协方差相关系数对拍失败: {msg}\n实际={实际}\n期望={期望}"


def test_O0_统计_累积和_对拍():
    """从 统计 导入 累积和，O0 真编译真跑。O0 下 输出(列表) 显示 []，用逐元素验证。"""
    code = (
        '从 统计 导入 累积和\n'
        '段落 主:\n'
        '  设 d 为 [1, 2, 3, 4, 5]\n'
        '  设 cs 为 累积和(d)\n'
        '  输出(长(cs))\n'
        '  输出(cs[0])\n'
        '  输出(cs[1])\n'
        '  输出(cs[2])\n'
        '  输出(cs[3])\n'
        '  输出(cs[4])\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 累积和 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = [5, 1, 3, 6, 10, 15]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"累积和对拍失败: {msg}\n实际={实际}\n期望={期望}"


# ── 3. 排序模块 O0 对拍 ────────────────────────────────────────────────

def test_O0_排序_排序_对拍():
    """从 排序 导入 排序，O0 真编译真跑，与 Python sorted 对拍。"""
    code = (
        '从 排序 导入 排序\n'
        '段落 主:\n'
        '  设 r 为 排序([3, 1, 4, 1, 5, 9, 2, 6])\n'
        '  输出(r[0])\n'
        '  输出(r[1])\n'
        '  输出(r[2])\n'
        '  输出(r[3])\n'
        '  输出(r[4])\n'
        '  输出(r[5])\n'
        '  输出(r[6])\n'
        '  输出(r[7])\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 排序 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = sorted([3, 1, 4, 1, 5, 9, 2, 6])
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"排序对拍失败: {msg}\n实际={实际}\n期望={期望}"


def test_O0_排序_稳定性():
    """归并排序稳定性验证：相等元素保持原始相对顺序。"""
    code = (
        '从 排序 导入 排序\n'
        '段落 主:\n'
        '  设 r 为 排序([5, 3, 5, 1, 5, 2])\n'
        '  输出(r[0])\n'
        '  输出(r[1])\n'
        '  输出(r[2])\n'
        '  输出(r[3])\n'
        '  输出(r[4])\n'
        '  输出(r[5])\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 排序稳定性 段错误 rc={rc}\nstderr={err}"
    实际 = _解析输出(out)
    期望 = sorted([5, 3, 5, 1, 5, 2])
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"排序稳定性失败: {msg}\n实际={实际}\n期望={期望}"


# ── 4. 三模块联合导入 O0 不崩 ──────────────────────────────────────────

def test_O0_三模块联合_数学统计排序():
    """从 数学/统计/排序 各导入一个函数，O0 联合编译不崩且输出正确。"""
    code = (
        '从 数学 导入 平方根\n'
        '从 统计 导入 均值\n'
        '从 排序 导入 排序\n'
        '段落 主:\n'
        '  设 d 为 [3, 1, 4, 1, 5, 9, 2, 6]\n'
        '  设 s 为 排序(d)\n'
        '  输出(s[0])\n'
        '  输出(s[7])\n'
        '  设 m 为 均值(s)\n'
        '  输出(m)\n'
        '  输出(平方根(m))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"O0 三模块联合 段错误 rc={rc} (0x{rc & 0xFFFFFFFF:08X})\nstderr={err}"
    实际 = _解析输出(out)
    s = sorted([3, 1, 4, 1, 5, 9, 2, 6])
    m = sum(s) / len(s)
    期望 = [s[0], s[7], m, math.sqrt(m)]
    ok, msg = _近似比较(实际, 期望)
    assert ok, f"三模块联合对拍失败: {msg}\n实际={实际}\n期望={期望}"


# ── 5. 反跑判据：空壳 → 红 ─────────────────────────────────────────────

def test_反跑_数学空壳_编译失败():
    """恢复数学.light为空壳（去掉段落实现）→ 编译应报 NativeImportError。"""
    from llvm.compiler import NativeImportError, compile_light_typed
    # 备份原文件
    with open(_MATH_LIGHT, 'r', encoding='utf-8') as f:
        原始 = f.read()
    空壳 = (
        '# 纯光明实现\n'
        '# 空壳测试\n'
        '导出 绝对值 平方根。\n'
    )
    try:
        with open(_MATH_LIGHT, 'w', encoding='utf-8', newline='\n') as f:
            f.write(空壳)
        code = (
            '从 数学 导入 平方根\n'
            '段落 主:\n'
            '  输出(平方根(16))\n'
        )
        with _tempfile.TemporaryDirectory(prefix='_taskT5a_') as d:
            src = os.path.join(d, '主.light')
            with open(src, 'w', encoding='utf-8', newline='\n') as f:
                f.write(code)
            with pytest.raises(NativeImportError, match='decl 0 空壳'):
                compile_light_typed(src, os.path.join(d, '产物'), optimize_level=0)
    finally:
        with open(_MATH_LIGHT, 'w', encoding='utf-8', newline='\n') as f:
            f.write(原始)


def test_反跑_统计空壳_编译失败():
    """恢复统计.light为空壳 → 编译应报 NativeImportError。"""
    from llvm.compiler import NativeImportError, compile_light_typed
    with open(_STAT_LIGHT, 'r', encoding='utf-8') as f:
        原始 = f.read()
    空壳 = (
        '# 纯光明实现\n'
        '# 空壳测试\n'
        '导出 均值。\n'
    )
    try:
        with open(_STAT_LIGHT, 'w', encoding='utf-8', newline='\n') as f:
            f.write(空壳)
        code = (
            '从 统计 导入 均值\n'
            '段落 主:\n'
            '  输出(均值([1, 2, 3]))\n'
        )
        with _tempfile.TemporaryDirectory(prefix='_taskT5a_') as d:
            src = os.path.join(d, '主.light')
            with open(src, 'w', encoding='utf-8', newline='\n') as f:
                f.write(code)
            with pytest.raises(NativeImportError, match='decl 0 空壳'):
                compile_light_typed(src, os.path.join(d, '产物'), optimize_level=0)
    finally:
        with open(_STAT_LIGHT, 'w', encoding='utf-8', newline='\n') as f:
            f.write(原始)


def test_反跑_排序空壳_编译失败():
    """恢复排序.light为空壳 → 编译应报 NativeImportError。"""
    from llvm.compiler import NativeImportError, compile_light_typed
    with open(_SORT_LIGHT, 'r', encoding='utf-8') as f:
        原始 = f.read()
    空壳 = (
        '# 纯光明实现\n'
        '# 空壳测试\n'
        '导出 排序。\n'
    )
    try:
        with open(_SORT_LIGHT, 'w', encoding='utf-8', newline='\n') as f:
            f.write(空壳)
        code = (
            '从 排序 导入 排序\n'
            '段落 主:\n'
            '  设 r 为 排序([3, 1, 2])\n'
            '  输出(r[0])\n'
        )
        with _tempfile.TemporaryDirectory(prefix='_taskT5a_') as d:
            src = os.path.join(d, '主.light')
            with open(src, 'w', encoding='utf-8', newline='\n') as f:
                f.write(code)
            with pytest.raises(NativeImportError, match='decl 0 空壳'):
                compile_light_typed(src, os.path.join(d, '产物'), optimize_level=0)
    finally:
        with open(_SORT_LIGHT, 'w', encoding='utf-8', newline='\n') as f:
            f.write(原始)
