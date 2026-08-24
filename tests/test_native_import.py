"""原生腿的模块导入用例（B9 S1 2.3 / M23 前置）

第一层（test_llvm_*.py）验 IR 正确性、照发裸 clang；第二层（test_native_cli.py）
验 `light run/compile --backend native` 命令。本文件专挑「导入」这一条，且
**一律走生产路径 `compile_light_typed`**（有导入时内部委托 `compile_light_project`
递归编译）—— 不自己拼 IR、不发裸 clang，这正是用户敲 `compile --backend native`
走的链路。

四条判据（任务书 §2.3）：
① 单层导入真跑
② 两层传递导入真跑
③ `从 X 导入 Y` 别名真跑
④ **反跑**：导入空壳/纯 py 模块必须报 `NativeImportError`，绝不静默产出一个
   「跑起来就崩」的 exe。

产物一律落 `tempfile.TemporaryDirectory()`，源码树不留 `.ll`/`.o`/`.exe`。
"""
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _native_helpers import 仓库根, skip_without_clang  # type: ignore[import]

sys.path.insert(0, os.path.join(仓库根, 'src'))

子进程口径 = dict(capture_output=True, text=True, encoding='utf-8', errors='replace')


def 写文件(目录, 文件名, 内容):
    """无 BOM 写入 .light/.py，避免词法层被 0xFEFF 卡掉"""
    路径 = os.path.join(目录, 文件名)
    with open(路径, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(内容)
    return 路径


def 编译并跑(主文件, 目录, 优化级别=2):
    """生产路径编译 + 跑产物，返回 (退出码, 非空输出行列表)"""
    from llvm.compiler import compile_light_typed  # type: ignore[import]

    exe = compile_light_typed(主文件, os.path.join(目录, '产物'),
                              optimize_level=优化级别)
    结果 = subprocess.run([exe], timeout=60, **子进程口径)
    return 结果.returncode, [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()]


@skip_without_clang
class Test原生导入真跑:
    """①~③：单层 / 传递 / 别名导入都能编译出可跑产物"""

    def test_单层导入真跑(self):
        with tempfile.TemporaryDirectory(prefix='_taskB9_') as 目录:
            写文件(目录, '丙.light', '段落 丙函数：\n  返回 7\n结束\n')
            主 = 写文件(目录, '主.light', '从 丙 导入 丙函数。\n输出(丙函数())\n')
            退出码, 输出行 = 编译并跑(主, 目录)
        assert 退出码 == 0, f'rc={退出码}'
        assert 输出行 == ['7'], f'单层导入输出不符: {输出行}'

    def test_两层传递导入真跑(self):
        """主 → 乙 → 丙；乙体内调用丙的段落，主只调乙的段落。"""
        with tempfile.TemporaryDirectory(prefix='_taskB9_') as 目录:
            写文件(目录, '丙.light', '段落 底层值：\n  返回 7\n结束\n')
            写文件(目录, '乙.light',
                    '从 丙 导入 底层值。\n段落 中层值：\n  返回 底层值() + 1\n结束\n')
            主 = 写文件(目录, '主.light', '从 乙 导入 中层值。\n输出(中层值())\n')
            退出码, 输出行 = 编译并跑(主, 目录)
        assert 退出码 == 0, f'rc={退出码}'
        assert 输出行 == ['8'], f'传递导入输出不符: {输出行}'

    def test_从X导入Y别名真跑(self):
        """`从 X 导入 Y`：一个模块里取多个符号，按名字直接调用（不挂模块名前缀）。"""
        with tempfile.TemporaryDirectory(prefix='_taskB9_') as 目录:
            写文件(目录, '工具.light',
                    '段落 甲：\n  返回 100\n结束\n段落 乙：\n  返回 200\n结束\n')
            主 = 写文件(目录, '主.light',
                        '从 工具 导入 甲。\n从 工具 导入 乙。\n输出(甲() + 乙())\n')
            退出码, 输出行 = 编译并跑(主, 目录)
        assert 退出码 == 0, f'rc={退出码}'
        assert 输出行 == ['300'], f'别名导入输出不符: {输出行}'


@skip_without_clang
class Test原生导入反跑:
    """④：导入「原生腿装不下的模块」必须显式报错，不许静默降级"""

    def test_导入同名py影子空壳模块必须报错(self):
        """`.light` 是 decl 0 空壳 + 同名 `.py` 实现在 → 必须 `NativeImportError`。"""
        from llvm.compiler import NativeImportError, compile_light_typed  # type: ignore[import]

        with tempfile.TemporaryDirectory(prefix='_taskB9_') as 目录:
            写文件(目录, '影子.light', '从 外部 导入 模板。\n')   # decl 0 空壳
            写文件(目录, '影子.py', 'def 模板():\n    return 1\n')
            主 = 写文件(目录, '主.light', '从 影子 导入 模板。\n输出(模板())\n')
            with pytest.raises(NativeImportError) as 错误:
                compile_light_typed(主, os.path.join(目录, '产物'))
        信息 = str(错误.value)
        assert '影子' in 信息, f'错误信息应点名模块: {信息!r}'
        assert '原生腿不加载 Python' in 信息, f'应说明不加载 py 实现: {信息!r}'

    def test_导入纯Python模块必须报错(self):
        """只有 `.py` 没有 `.light` → 解析到的是 python 文件，必须 `NativeImportError`。"""
        from llvm.compiler import NativeImportError, compile_light_typed  # type: ignore[import]

        with tempfile.TemporaryDirectory(prefix='_taskB9_') as 目录:
            写文件(目录, '纯py.py', 'def f():\n    return 1\n')
            主 = 写文件(目录, '主.light', '从 纯py 导入 f。\n输出(f())\n')
            with pytest.raises(NativeImportError) as 错误:
                compile_light_typed(主, os.path.join(目录, '产物'))
        信息 = str(错误.value)
        assert '原生腿不加载 .py' in 信息, f'错误信息应说明不加载 .py: {信息!r}'