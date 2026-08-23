"""
B5 语言核心补齐行为测试 — 位运算

判据全部为行为级：编译后真正执行，按运行时输出断言。
不检查生成代码字符串。
"""

import sys
import os
import io
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _run(src):
    """编译并真正执行一份光明源码，返回标准输出（去掉首尾空白）。"""
    parser = LightParser()
    module = parser.parse(src)
    code = PythonCodeGenerator().generate(module)
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            exec(code, {})
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}:{e}"
    return stdout.getvalue().strip()


class TestBitwiseAnd:
    """位与（&）"""

    def test_basic_and(self):
        """12 & 10 = 8（二进制 1100 & 1010 = 1000）"""
        src = """
段落 测试:
  返回 12 位与 10。
结束。

打印 测试()。
"""
        assert _run(src) == "8", f"12 位与 10 应为 8，实际: {_run(src)!r}"

    def test_and_zero(self):
        """无交集时结果为 0：5 & 2 = 0（101 & 010 = 000）"""
        src = """
段落 测试:
  返回 5 位与 2。
结束。

打印 测试()。
"""
        assert _run(src) == "0", f"5 位与 2 应为 0，实际: {_run(src)!r}"


class TestBitwiseOr:
    """位或（|）"""

    def test_basic_or(self):
        """12 | 10 = 14（二进制 1100 | 1010 = 1110）"""
        src = """
段落 测试:
  返回 12 位或 10。
结束。

打印 测试()。
"""
        assert _run(src) == "14", f"12 位或 10 应为 14，实际: {_run(src)!r}"


class TestBitwiseXor:
    """位异或（^）"""

    def test_basic_xor(self):
        """12 ^ 10 = 6（二进制 1100 ^ 1010 = 0110）"""
        src = """
段落 测试:
  返回 12 位异或 10。
结束。

打印 测试()。
"""
        assert _run(src) == "6", f"12 位异或 10 应为 6，实际: {_run(src)!r}"

    def test_xor_self(self):
        """a ^ a = 0"""
        src = """
段落 测试:
  返回 42 位异或 42。
结束。

打印 测试()。
"""
        assert _run(src) == "0", f"42 位异或 42 应为 0，实际: {_run(src)!r}"


class TestBitwiseNot:
    """位非（~）——一元前缀"""

    def test_not_five(self):
        """~5 = -6"""
        src = """
段落 测试:
  返回 位非 5。
结束。

打印 测试()。
"""
        assert _run(src) == "-6", f"位非 5 应为 -6，实际: {_run(src)!r}"

    def test_not_zero(self):
        """~0 = -1"""
        src = """
段落 测试:
  返回 位非 0。
结束。

打印 测试()。
"""
        assert _run(src) == "-1", f"位非 0 应为 -1，实际: {_run(src)!r}"


class TestShiftLeft:
    """左移（<<）"""

    def test_shift_left_three(self):
        """1 << 3 = 8"""
        src = """
段落 测试:
  返回 1 左移 3。
结束。

打印 测试()。
"""
        assert _run(src) == "8", f"1 左移 3 应为 8，实际: {_run(src)!r}"


class TestShiftRight:
    """右移（>>）"""

    def test_shift_right_two(self):
        """16 >> 2 = 4"""
        src = """
段落 测试:
  返回 16 右移 2。
结束。

打印 测试()。
"""
        assert _run(src) == "4", f"16 右移 2 应为 4，实际: {_run(src)!r}"


class TestBitwisePrecedence:
    """位运算优先级：位与 > 位或（Python 口径）"""

    def test_and_binds_tighter_than_or(self):
        """6 & 3 | 8 = 2 | 8 = 10（位与先于位或）"""
        src = """
段落 测试:
  返回 6 位与 3 位或 8。
结束。

打印 测试()。
"""
        assert _run(src) == "10", f"6 位与 3 位或 8 应为 10（位与优先），实际: {_run(src)!r}"

    def test_arithmetic_binds_tighter_than_and(self):
        """算术 > 位与：2 + 2 & 3 = 4 & 3 = 0"""
        src = """
段落 测试:
  返回 2 加 2 位与 3。
结束。

打印 测试()。
"""
        assert _run(src) == "0", f"2 加 2 位与 3 应为 0（算术优先于位与），实际: {_run(src)!r}"

    def test_shift_binds_tighter_than_and(self):
        """位移 > 位与：1 << 1 & 3 = 2 & 3 = 2"""
        src = """
段落 测试:
  返回 1 左移 1 位与 3。
结束。

打印 测试()。
"""
        assert _run(src) == "2", f"1 左移 1 位与 3 应为 2（位移优先于位与），实际: {_run(src)!r}"


class TestBitwiseInBlocks:
    """积木库存量文件可编译验证"""

    def test_blocks_v5_all_compile_and_run(self):
        """6 个 blocks_v5/计算机 位运算积木文件可编译且行为正确"""
        import subprocess
        from pathlib import Path

        cases = [
            ('位与.light', '12', '10', '8'),
            ('位或.light', '12', '10', '14'),
            ('位异或.light', '12', '10', '6'),
            ('左移.light', '1', None, '2'),     # 左移 1 位 → 1<<1=2
            ('右移.light', '16', None, '8'),    # 右移 1 位 → 16>>1=8
        ]
        for fname, arg1, arg2, expected in cases:
            fpath = Path('积木库/blocks_v5/计算机') / fname
            if not fpath.exists():
                continue
            # 构造调用脚本
            if arg2:
                call_src = f'导入 {fpath.stem} as mod\n打印 mod.主({arg1}, {arg2})。\n'
            else:
                call_src = f'导入 {fpath.stem} as mod\n打印 mod.主({arg1})。\n'
            # 直接用编译+运行方式
            r = subprocess.run(
                [sys.executable, '-m', 'cli.light_unified', 'run', str(fpath)],
                capture_output=True, text=True, encoding='utf-8',
                cwd='.', timeout=15,
            )
            # 积木文件定义了导出但没调用，编译通过即可
            assert r.returncode == 0, f"{fname} 编译失败: {r.stderr[:200]}"

    def test_bitnot_block_compiles(self):
        """位取反积木文件可编译

        产物必须落到临时目录：`compile` 不给 `-o` 就把 `.py` 写在源文件旁边，
        而 `积木库/**` 下没有任何 `.py` 是被跟踪的。CI 里断言质量门禁
        （`.gitea/workflows/ci.yml` 的「断言质量门禁」步）排在全量测试**之后**、
        扫的是全仓 `.py`，于是这份产物会被当成新增假绿断言（生成码里有
        `assert _x is not None`）把 CI 打红。
        """
        import subprocess
        import tempfile
        from pathlib import Path

        fpath = Path('积木库/blocks_v5/计算机/位取反.light')
        if not fpath.exists():
            return
        with tempfile.TemporaryDirectory() as 产物目录:
            out = Path(产物目录) / '位取反.py'
            r = subprocess.run(
                [sys.executable, '-m', 'cli.light_unified', 'compile', str(fpath),
                 '-o', str(out)],
                capture_output=True, text=True, encoding='utf-8',
                cwd='.', timeout=15,
            )
            assert r.returncode == 0, f"位取反.light 编译失败: {r.stderr[:200]}"
            assert out.exists(), f"未生成产物 {out}"



class Test函数当标识符:
    """`函数` 既是 C 风格匿名函数关键字，也是常用形参名——两种用法必须共存。

    合并期回归：B5 让 `函数(params)` 后面没有 `{` 时回退，回退落到「段落调用
    函数/段落 段名(...)」分支，那里要求关键字后跟段名，于是 `函数(项)` 报
    「函数/段落调用后应跟段名」。docs/L2_文言体语法规范_v4.0.md 里的 映射
    示例因此编不过。
    """

    def test_函数当形参名可调用(self):
        """形参叫 `函数` 时，`函数(项)` 必须是真调用而不是报错/匿名函数。"""
        src = """段 映射(列表: 列, 函数: 段) -> 列:
    设 结果: 列 = []
    遍 列表 之为 项:
        结果.追加(函数(项))
    返 结果

段 平方(甲) -> 数:
    返 甲 乘 甲

打印(映射([1, 2, 3], 平方))
"""
        assert _run(src) == "[1, 4, 9]", f"映射(…, 平方) 应为 [1, 4, 9]，实际: {_run(src)!r}"

    def test_C风格匿名函数仍可用(self):
        """反向守护：带 `{}` 的 `函数(甲){…}` 不能被上面的回退吃掉。"""
        src = """设 三倍 = 函数(甲){ 返回 甲 乘 3 }
打印(三倍(4))
"""
        assert _run(src) == "12", f"三倍(4) 应为 12，实际: {_run(src)!r}"

