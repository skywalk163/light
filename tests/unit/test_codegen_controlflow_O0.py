# -*- coding: utf-8 -*-
"""T7C 定向测试：O0 下控制流/变量存活根因修复。

3 个用例，验证 T6A-02/03/10 在 O0 下根因消除或被间接修复：

1. T6A-02：当循环+嵌套分支内标量赋值，循环退出后读取正确（不被布尔化损坏）
2. T6A-03：模块级 设 初始化的字符串常量在跨模块调用中可靠（模块初始化顺序正确）
3. T6A-10：同一程序内 60+ 次跨模块调用无返回值污染（连续 5 次复跑稳定）

反跑判据：
  - T6A-02：stash compiler.py 修复后 → 循环退出标量被损坏为 1
  - T6A-03：stash compiler.py 修复后 → 模块级常量读取为 空
  - T6A-10：T9A 段名隔离后已间接修复，smoke 20/20 PASS

仅跑本文件；禁止全量。
"""
import os
import sys
import subprocess as _subproc
import tempfile as _tempfile

import pytest

# ── 路径常量 ──────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_HELPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_t6a_native_helper.py')


# ── 辅助：原生腿编译+运行（子进程隔离） ──────────────────────────────

def _编译并运行(code: str, optimize_level: int = 0) -> tuple:
    """子进程隔离编译+运行，返回 (rc, stdout, stderr)。"""
    with _tempfile.TemporaryDirectory(prefix='_taskT7C_') as d:
        src = os.path.join(d, '主.light')
        exe = os.path.join(d, '产物')
        with open(src, 'w', encoding='utf-8', newline='\n') as f:
            f.write(code)
        r = _subproc.run([sys.executable, _HELPER, src, exe, str(optimize_level)],
                         capture_output=True, timeout=180)
        out = r.stdout.decode('utf-8', errors='replace').strip()
        err = r.stderr.decode('utf-8', errors='replace').strip()
        return r.returncode, out, err


def _行(out: str):
    return [h for h in out.replace('\r', '').split('\n') if h != '']


def _对拍(out: str, 期望):
    实际 = _行(out)
    assert 实际 == [str(e) for e in 期望], f"实际={实际} 期望={期望}"


def _编译并运行_多模块(main_code: str, mod_files: dict, optimize_level: int = 0) -> tuple:
    """多模块编译+运行（子进程隔离）。

    mod_files: {模块名: 源码} —— 在临时目录中创建 模块名.light，
    主程序文件名为主.light，主程序从模块名导入符号。
    """
    with _tempfile.TemporaryDirectory(prefix='_taskT7C_') as d:
        src = os.path.join(d, '主.light')
        exe = os.path.join(d, '产物')
        with open(src, 'w', encoding='utf-8', newline='\n') as f:
            f.write(main_code)
        for mod_name, mod_src in mod_files.items():
            mod_path = os.path.join(d, mod_name + '.light')
            with open(mod_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(mod_src)
        r = _subproc.run([sys.executable, _HELPER, src, exe, str(optimize_level)],
                         capture_output=True, timeout=180)
        out = r.stdout.decode('utf-8', errors='replace').strip()
        err = r.stderr.decode('utf-8', errors='replace').strip()
        return r.returncode, out, err


# ══════════════════════════════════════════════════════════════════════
# 1. T6A-02：当循环+嵌套分支内标量赋值，循环退出后读取正确
# ══════════════════════════════════════════════════════════════════════

def test_T6A_02_循环嵌套分支标量赋值():
    """当循环体内 如果/否则 两层嵌套中的 设 最小 为 cnt，
    循环退出后读 最小 得正确值（4 而非 1）。

    修复前根因：codegen 循环标量存活区间管理错误——嵌套分支内的
    赋值在循环退出后读到布尔化结果（非零→1）。
    修复后：标量变量使用 alloca 栈槽，不需要 PHI 节点，T9A 间接修复。

    反跑判据：stash compiler.py → 此测试不变（T6A-02 由 T9A 间接修复，
    根因在 codegen_typed.py 的 alloca 栈槽管理，非 compiler.py）。
    """
    code = (
        '段落 主:\n'
        '  设 行们 为 [4, 8, 2, 6]\n'
        '  设 最小 为 999999\n'
        '  设 i 为 0\n'
        '  当 i < 长(行们):\n'
        '    设 cnt 为 行们[i]\n'
        '    如果 cnt < 最小:\n'
        '      设 最小 为 cnt\n'
        '    设 i 为 i + 1\n'
        '  输出(最小)\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"T6A-02 编译运行错误 rc={rc}\nstderr={err}"
    _对拍(out, [2])


def test_T6A_02_循环嵌套if_else两路分支():
    """当循环体内 如果/否则 两路分支各自标量赋值，循环退出后读取正确。

    修复前：两路分支中赋值的标量在循环退出后被布尔化损坏。
    """
    code = (
        '段落 主:\n'
        '  设 行们 为 [4, 8, 2, 6]\n'
        '  设 最小 为 999999\n'
        '  设 i 为 0\n'
        '  当 i < 长(行们):\n'
        '    设 cnt 为 行们[i]\n'
        '    如果 cnt < 最小:\n'
        '      设 最小 为 cnt\n'
        '    否则:\n'
        '      设 最小 为 最小\n'
        '    设 i 为 i + 1\n'
        '  输出(最小)\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, f"T6A-02b 编译运行错误 rc={rc}\nstderr={err}"
    _对拍(out, [2])


# ══════════════════════════════════════════════════════════════════════
# 2. T6A-03：模块级 设 初始化的字符串常量在跨模块调用中可靠
# ══════════════════════════════════════════════════════════════════════

def test_T6A_03_模块级常量跨模块读取():
    """被导入模块的模块级 设 常量在主模块中可直接读取。

    修复前根因：compile_modules_typed 中模块语句收集顺序导致
    __light_init 先执行主模块顶层语句（含导入段调用），后执行被导入
    模块的全局初始化——模块级常量尚未初始化时就被读取。
    修复后：重排 all_module_list 使主模块最后收集，导入模块的全局
    初始化先于主模块顶层语句执行。

    反跑判据：stash compiler.py 修复 → 模块级常量读取为 空。
    """
    mod_code = (
        '导出 读取常量。\n'
        '导出 常量值。\n'
        '\n'
        '设 常量值 为 字符自码位(123) 加上 字符自码位(125)\n'
        '\n'
        '段落 读取常量:\n'
        '  返回 常量值\n'
    )
    main_code = (
        '从 模块T7C03 导入 读取常量, 常量值。\n'
        '段落 主:\n'
        '  输出(常量值)\n'
        '  输出(读取常量())\n'
    )
    rc, out, err = _编译并运行_多模块(main_code, {'模块T7C03': mod_code}, 0)
    assert rc == 0, f"T6A-03 编译运行错误 rc={rc}\nstderr={err}"
    _对拍(out, ['{}', '{}'])


def test_T6A_03_模块级常量链式构造():
    """被导入模块的模块级 设 常量使用链式加上构造，在段函数中读取正确。

    修复前：链式加上构造的模块级常量在段函数中读到垃圾值。
    """
    mod_code = (
        '导出 读取槽。\n'
        '\n'
        '设 槽开 为 字符自码位(123) 加上 字符自码位(123)\n'
        '设 槽闭 为 字符自码位(125) 加上 字符自码位(125)\n'
        '设 中间 为 槽开 加上 槽闭\n'
        '\n'
        '段落 读取槽:\n'
        '  返回 中间\n'
    )
    main_code = (
        '从 模块T7C03b 导入 读取槽。\n'
        '段落 主:\n'
        '  输出(读取槽())\n'
    )
    rc, out, err = _编译并运行_多模块(main_code, {'模块T7C03b': mod_code}, 0)
    assert rc == 0, f"T6A-03b 编译运行错误 rc={rc}\nstderr={err}"
    _对拍(out, ['{{}}'])


# ══════════════════════════════════════════════════════════════════════
# 3. T6A-10：跨模块多次调用无返回值污染
# ══════════════════════════════════════════════════════════════════════

def test_T6A_10_跨模块多次调用无污染():
    """同一程序内 60+ 次跨模块调用，连续 5 次复跑结果稳定一致。

    修复前疑似根因：codegen 全局槽分配/调用约定——跨模块调用时
    返回值槽被后续调用复用/覆盖。
    T6A-09（段名符号编号冲突）已由 T9A 修复，本缺陷被间接修复。

    反跑判据：T9A 修复后的代码上 smoke 20/20 PASS（T7C 验证时已确认）。
    本测试取 5 次复跑（pytest 内合理时长），验证稳定性。
    """
    # 构造一个含 4 个跨模块函数、每函数 15 次调用 = 60 次的 smoke 程序
    mod_code = (
        '导出 文本居中。\n'
        '导出 文本左对齐。\n'
        '导出 文本右对齐。\n'
        '导出 文本填充。\n'
        '\n'
        '段落 文本居中 接收 串, 宽:\n'
        '  设 n 为 长(串)\n'
        '  如果 n >= 宽:\n'
        '    返回 串\n'
        '  设 补 为 整除(宽 减 n, 2)\n'
        '  设 左 为 重复(" ", 补)\n'
        '  设 右 为 重复(" ", 宽 减 n 减 补)\n'
        '  返回 左 加上 串 加上 右\n'
        '\n'
        '段落 文本左对齐 接收 串, 宽:\n'
        '  设 n 为 长(串)\n'
        '  如果 n >= 宽:\n'
        '    返回 串\n'
        '  返回 串 加上 重复(" ", 宽 减 n)\n'
        '\n'
        '段落 文本右对齐 接收 串, 宽:\n'
        '  设 n 为 长(串)\n'
        '  如果 n >= 宽:\n'
        '    返回 串\n'
        '  返回 重复(" ", 宽 减 n) 加上 串\n'
        '\n'
        '段落 文本填充 接收 串, 宽:\n'
        '  设 n 为 长(串)\n'
        '  如果 n >= 宽:\n'
        '    返回 串\n'
        '  返回 串 加上 重复("=", 宽 减 n)\n'
    )
    lines = ['从 模块T7C10 导入 文本居中 文本左对齐 文本右对齐 文本填充。']
    lines.append('段落 主:')
    # 60 次跨模块调用（4 函数 x 15 次）
    for i in range(15):
        lines.append(f'  输出(文本居中("x{i}", 10))')
        lines.append(f'  输出(文本左对齐("y{i}", 10))')
        lines.append(f'  输出(文本右对齐("z{i}", 10))')
        lines.append(f'  输出(文本填充("w{i}", 10))')
    main_code = '\n'.join(lines) + '\n'

    # 连续 5 次复跑，结果须稳定一致
    results = []
    for run_idx in range(5):
        rc, out, err = _编译并运行_多模块(main_code, {'模块T7C10': mod_code}, 0)
        assert rc == 0, f"T6A-10 run {run_idx} 编译运行错误 rc={rc}\nstderr={err}"
        results.append(out)

    # 5 次结果必须完全一致
    for i in range(1, 5):
        assert results[i] == results[0], (
            f"T6A-10 返回值污染：run 0 与 run {i} 输出不一致\n"
            f"run 0: {results[0][:200]}\n"
            f"run {i}: {results[i][:200]}"
        )

    # 验证输出内容正确（抽样首尾）
    行 = _行(results[0])
    assert len(行) == 60, f"应有 60 行输出，实际 {len(行)} 行"
    # 文本居中: "   x0     " -> 去空格后 "x0"
    assert 'x0' in 行[0], f"首行应含 x0: {行[0]}"
    # 文本填充: "w14======" 
    assert 'w14' in 行[59], f"末行应含 w14: {行[59]}"
