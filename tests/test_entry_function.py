# -*- coding: utf-8 -*-
"""L-070：入口函数（`函数 主()` / `段落 主：`）自动调用回归测试。

背景：光明约定 `主` 为程序入口（等价 Python 的 `if __name__ == '__main__': main()`），
但 `src/code_generator.py` 的 `generate()` 只发 `def 主():` 定义、不发调用，
导致所有以 `主` 为入口的程序 `light run` 无输出且 exit 0。

本文件覆盖：
1. `函数 主()` 自动调用有输出
2. `段落 主：` 自动调用有输出
3. 模块级显式 `主()` 不重复调用（输出只出现一次）
4. `异步 运行 主()` 不冲突（不追加同步调用）
5. 有参 `函数 主(参数)` 不自动调用（无法确定实参）
6. 依赖模块里定义的 `主()` 不被调用（依赖模块非主文件）
7. 汉诺塔完整程序经入口自动调用后输出正确

定向运行：
    python -m pytest tests/test_entry_function.py -q
"""

import io
import os
import sys
from contextlib import redirect_stdout

import pytest

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, 'src')
for _p in (_src_dir, _project_root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402


# =============================================================================
# 辅助函数
# =============================================================================

def _compile(source: str, is_main: bool = True) -> str:
    """编译光明源码为 Python 代码（默认按主文件编译）"""
    parser = LightParser()
    module = parser.parse(source)
    if module is None:
        raise AssertionError("解析失败：" + '\n'.join(getattr(parser, 'errors', []) or []))
    # 不断 `is not None`（零信号）：要断「确实解析出了语句」，否则后续对生成码的
    # 断言会建立在一个空模块上，红绿都失去意义。
    assert getattr(module, 'statements', None), (
        f"解析结果不含任何语句：type={type(module).__name__}"
    )
    return PythonCodeGenerator().generate(module, is_main=is_main)


def _run(source: str, is_main: bool = True) -> str:
    """编译（主文件）并执行，返回标准输出"""
    py_code = _compile(source, is_main=is_main)
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(py_code, {'__name__': '__main__', '__file__': 'test_entry.light'})
    return buf.getvalue().strip().replace('\r\n', '\n')


def _run_cli(source: str, file_path: str) -> str:
    """走 cli.light._run_src（真实 `light run` 路径），返回输出"""
    from cli.light import _run_src
    buf = io.StringIO()
    with redirect_stdout(buf):
        out = _run_src(source, file_path=file_path)
    return (out or '').strip().replace('\r\n', '\n')


HANOI_SOURCE = '''段落 汉诺塔 接收 层数, 源柱, 目标柱, 辅助柱:
  如果 层数 等于 1 那么:
    打印("移动盘子 1 从 " 加上 源柱 加上 " 到 " 加上 目标柱)。
  否则:
    汉诺塔(层数 减 1, 源柱, 辅助柱, 目标柱)。
    打印("移动盘子 " 加上 转字符串(层数) 加上 " 从 " 加上 源柱 加上 " 到 " 加上 目标柱)。
    汉诺塔(层数 减 1, 辅助柱, 目标柱, 源柱)。
  结束。
结束。

函数 主():
  打印("=== 汉诺塔（3层）===")。
  汉诺塔(3, "A", "C", "B")。
结束。
'''

HANOI_EXPECTED = '''=== 汉诺塔（3层）===
移动盘子 1 从 A 到 C
移动盘子 2 从 A 到 B
移动盘子 1 从 C 到 B
移动盘子 3 从 A 到 C
移动盘子 1 从 B 到 A
移动盘子 2 从 B 到 C
移动盘子 1 从 A 到 C'''


# =============================================================================
# 用例
# =============================================================================

def test_函数主自动调用():
    """`函数 主()` 无显式调用也应执行并输出"""
    out = _run('函数 主():\n    打印("hello")\n')
    assert out == "hello"


def test_段落主自动调用():
    """`段落 主：` 同样作为入口被自动调用"""
    out = _run('段落 主：\n    打印("hi")\n结束。\n')
    assert out == "hi"


def test_主程序与main同样是入口():
    """入口名集合与原生腿对齐：主程序 / 主入口 / main"""
    assert _run('函数 主程序():\n    打印("A")\n') == "A"
    assert _run('函数 主入口():\n    打印("B")\n') == "B"
    assert _run('函数 main():\n    打印("C")\n') == "C"


def test_显式调用不重复():
    """模块级已写 `主()` → 不追加第二次调用，输出只出现一次"""
    out = _run('函数 主():\n    打印("x")\n主()\n')
    assert out == "x"


def test_异步运行不冲突():
    """`异步 运行 主()` 已启动入口 → 不追加同步调用"""
    out = _run('异步 段落 主：\n    打印("async-ok")\n结束。\n\n异步 运行 主()。\n')
    assert out == "async-ok"


def test_有参主不自动调用():
    """入口有形参时无法确定实参 → 不自动生成调用（运行后无输出）"""
    out = _run('函数 主(参数):\n    打印("never")\n')
    assert out == ""


def test_生成代码含入口守卫():
    """主文件产物含 `if __name__ == '__main__': 主()`；非主文件产物不含"""
    src = '函数 主():\n    打印("x")\n'
    code_main = _compile(src, is_main=True)
    assert "if __name__ == '__main__':" in code_main
    assert "主()" in code_main
    code_dep = _compile(src, is_main=False)
    assert "if __name__ == '__main__':" not in code_dep


def test_依赖模块的主不被调用(tmp_path):
    """依赖模块（非主文件）里定义的 `主()` 不得被调用"""
    dep = tmp_path / '任务依赖.light'
    dep.write_text(
        '函数 辅助():\n'
        '    返回 "辅助值"\n'
        '结束。\n'
        '\n'
        '函数 主():\n'
        '    打印("DEP_MAIN_CALLED")\n'
        '结束。\n',
        encoding='utf-8')
    main = tmp_path / '主文件.light'
    main_src = ('从 任务依赖 导入 辅助\n'
                '打印("MAIN:" 加上 辅助())。\n')
    main.write_text(main_src, encoding='utf-8')

    out = _run_cli(main_src, file_path=str(main))
    assert "MAIN:辅助值" in out
    assert "DEP_MAIN_CALLED" not in out


def test_主文件依赖导入仍自动调用入口(tmp_path):
    """主文件自身有 `主` 且带依赖模块时，入口仍被自动调用"""
    dep = tmp_path / '任务依赖.light'
    dep.write_text('函数 辅助():\n    返回 "辅助值"\n结束。\n', encoding='utf-8')
    main_src = ('从 任务依赖 导入 辅助\n'
                '\n'
                '函数 主():\n'
                '    打印("MAIN:" 加上 辅助())。\n')
    main = tmp_path / '主文件.light'
    main.write_text(main_src, encoding='utf-8')

    out = _run_cli(main_src, file_path=str(main))
    assert "MAIN:辅助值" in out


def test_汉诺塔完整程序通过():
    """汉诺塔（3 层）经入口自动调用后输出完整 7 步"""
    assert _run(HANOI_SOURCE) == HANOI_EXPECTED
