# -*- coding: utf-8 -*-
"""test_R140_L182_L191_原生腿.py —— R140-A：原生腿「跑得对」

被测缺陷（R128-F / R132-C 登记，本轮修复）：
  - **L-182** 段落形参被同名模块级全局静默穿透。codegen 的 `get_var` 把
    `_globals` 检查排在 `_local_vars` 之前，形参与全局同名时读到的是全局。
    实证：`节点网络.写JSON(路径, 字典)` 段内 `序列化缩进(字典, 2)` 写出的是
    驱动模块的全局 `字典`，而不是实参。
  - **L-191** 多模块编译时，被导入模块的顶层语句被拿主模块上下文生成，
    段名解析串到入口作用域。实证：`stdlib/分布式/节点.light` 顶层
    `异步 运行 主环境()。` 在驱动模块里报「未定义的段落：主环境」
    （编译器符号表却列得出 `主环境`，自相矛盾）——`native_run_readiness.py
    --sample 节点` 因此一直「编不过」。

判实方式（全部**真编译 + 真运行**，两腿对拍；不用 IR 文本做断言）：

  A1-L182 三形态：同名直返 / 撞名跨模块调用 / 不撞名（对照组），
    每条都要求「Python 腿输出 == 原生腿输出」——只验其中一腿等于期望值
    不足以证明两腿一致（那正是 L-182 藏身的方式）。
  A1-L182 系统边界：`节点网络.写JSON(路径, 字典)` 原生腿产物被读回后
    必须是 `{"键": "值"}`，不得是驱动模块的全局 `字典`；参考实现取
    `stdlib/分布式/节点网络.py`（转译腿契约真源）。
  A2-L191：`节点` 模块原生腿由「编不过」转「可编」。

⚠️ 两腿入口口径（写用例前实测确认，别踩）：
  - 两腿都**自动调用** `段落 主()`（原生腿 `codegen_typed.py:8114` main_names
    含 `主`；Python 腿 `cli/light.py:218` 追加 `if __name__ == '__main__': 主()`）。
  - 但**只有原生腿**做了「顶层已显式调过就不重复调」的查重（`main_called`），
    Python 腿没有。所以用例源里**绝不能**再写一次裸 `主()` —— 那会让 Python 腿
    跑两遍、输出翻倍。本文件一律只定义 `段落 主`、不显式调用。

平台：本机 Windows **不实跑**（任务书 A 红线「本机禁止实跑」），全部在
192.168.0.82（FreeBSD 15.1）执行；本文件不下「本机绿 = CI 绿」的结论。
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _native_helpers import 仓库根, skip_without_clang  # type: ignore[import]

_SRC = os.path.join(仓库根, 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

子进程口径 = dict(capture_output=True, text=True, encoding='utf-8', errors='replace')

_节点网络py = os.path.join(仓库根, 'stdlib', '分布式', '节点网络.py')


def 写文件(目录, 文件名, 内容):
    """无 BOM 写 .light/.py（BOM 会被词法层当字符卡住）"""
    路径 = os.path.join(目录, 文件名)
    with open(路径, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(内容)
    return 路径


def 原生腿跑(主文件, 目录, 优化级别=2):
    """生产路径编译 + 真跑，返回 (退出码, 非空输出行列表)。"""
    from llvm.compiler import compile_light_typed  # type: ignore[import]

    exe = compile_light_typed(主文件, os.path.join(目录, '产物'),
                              optimize_level=优化级别)
    结果 = subprocess.run([exe], timeout=120, cwd=目录, **子进程口径)
    return 结果.returncode, [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()]


def python腿跑(主文件, 目录):
    """Python 腿：真跑 `cli/light.py run`（生产入口，不自己拼解释器）。"""
    结果 = subprocess.run(
        [sys.executable, os.path.join(仓库根, 'cli', 'light.py'), 'run', 主文件],
        cwd=目录, timeout=180, **子进程口径)
    return 结果.returncode, [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()]


def 双腿对拍(目录, 源, 名字='主.light'):
    """同一份 .light 源两腿各跑一次，返回 (python行, 原生行)。"""
    主 = 写文件(目录, 名字, 源)
    py_rc, py_行 = python腿跑(主, 目录)
    assert py_rc == 0, 'Python 腿未跑通 rc=%s 输出=%s stderr=%s' % (py_rc, py_行, py_行)
    nat_rc, nat_行 = 原生腿跑(主, 目录)
    assert nat_rc == 0, '原生腿未跑通 rc=%s 输出=%s' % (nat_rc, nat_行)
    return py_行, nat_行


# ---------------------------------------------------------------------------
# A1-L182 形态甲：形参与同名全局 —— 同名直返
# ---------------------------------------------------------------------------
@skip_without_clang
def test_L182_形态甲_同名直返双腿一致():
    """全局 `值`=1，段落形参也叫 `值`，段落体内直返 `值`；实参 2。

    反跑：删掉 `get_var` 里的形参旁路 → 原生腿返回 1（全局），Python 腿返回 2
    → 本用例红。
    """
    with tempfile.TemporaryDirectory(prefix='_r140_甲_') as 目录:
        源 = ('设 值 为 1\n'
              '\n'
              '段落 取(值):\n'
              '  返回 值\n'
              '\n'
              '段落 主():\n'
              '  输出(取(2))\n'
              '  返回 0\n')
        py_行, nat_行 = 双腿对拍(目录, 源)
    assert py_行 == ['2'], 'Python 腿本身就不对，先查源: %s' % py_行
    assert nat_行 == py_行, '两腿分歧：原生=%s Python=%s' % (nat_行, py_行)


# ---------------------------------------------------------------------------
# A1-L182 形态乙：撞名 + 跨模块调用
# ---------------------------------------------------------------------------
@skip_without_clang
def test_L182_形态乙_撞名跨模块调用双腿一致():
    """被调模块的段落形参名撞上调用方模块的全局名。

    `工具.加倍(字典)` 段内 `返回 字典 乘以 10`；驱动方全局 `字典`=1，实参 7。
    形参被穿透时，被调段落读到的是**驱动方**的全局 1 → 输出 10 而不是 70。
    这一形态是本轮缺陷的原始形状（`节点网络.写JSON` 同构）。

    反跑：删掉形参旁路 → 原生腿输出 10，Python 腿输出 70 → 本用例红。
    """
    with tempfile.TemporaryDirectory(prefix='_r140_乙_') as 目录:
        写文件(目录, '工具.light',
              '段落 加倍(字典):\n'
              '  返回 字典 乘以 10\n')
        源 = ('从 工具 导入 加倍\n'
              '\n'
              '设 字典 为 1\n'
              '\n'
              '段落 主():\n'
              '  输出(加倍(7))\n'
              '  返回 0\n')
        py_行, nat_行 = 双腿对拍(目录, 源)
    assert py_行 == ['70'], 'Python 腿本身就不对，先查源: %s' % py_行
    assert nat_行 == py_行, '两腿分歧：原生=%s Python=%s' % (nat_行, py_行)


# ---------------------------------------------------------------------------
# A1-L182 形态丙：不撞名（对照组 —— 防「为了过甲/乙把作用域改坏」）
# ---------------------------------------------------------------------------
@skip_without_clang
def test_L182_形态丙_不撞名对照组双腿一致():
    """形参 `甲参` 与全局 `乙全` 不同名：形参读取、全局读取必须各归各位。

    反跑：若把旁路写成「凡局部名一律压过全局」并误伤模块级读取 → 这里读 `乙全`
    会落空 → 输出不对。
    """
    with tempfile.TemporaryDirectory(prefix='_r140_丙_') as 目录:
        源 = ('设 乙全 为 100\n'
              '\n'
              '段落 取(甲参):\n'
              '  返回 甲参 加上 乙全\n'
              '\n'
              '段落 主():\n'
              '  输出(取(5))\n'
              '  返回 0\n')
        py_行, nat_行 = 双腿对拍(目录, 源)
    assert py_行 == ['105'], 'Python 腿本身就不对，先查源: %s' % py_行
    assert nat_行 == py_行, '两腿分歧：原生=%s Python=%s' % (nat_行, py_行)


# ---------------------------------------------------------------------------
# A1-L182 系统边界：节点网络.写JSON —— 缺陷的原始现场
# ---------------------------------------------------------------------------
def _节点网络真源():
    """按路径直载 `stdlib/分布式/节点网络.py`（转译腿契约真源），不装 import 钩子。

    刻意不装钩子：`节点网络.light` 首两行**故意**不含「纯光明实现」魔数，
    钩子会把 .py 顶掉，那样参考实现就不是契约真源了（见该 .light 头部说明）。
    """
    spec = importlib.util.spec_from_file_location('_r140_节点网络真源', _节点网络py)
    模块 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(模块)
    return 模块


@skip_without_clang
@pytest.mark.skipif(sys.platform == 'win32',
                    reason='本机禁止实跑 A 线原生腿（任务书红线）：原生腿文件 I/O '
                           '在 Windows 运行态不稳定（0.82/0.88 权威门已验证 6 passed）')
def test_L182_写JSON形参不被同名全局遮蔽():
    """`节点网络.写JSON(路径, 字典)` 必须写出**实参**，不是驱动方的全局 `字典`。

    这是 L-182 的原始现场：R128-F 实测原生腿把驱动方全局 `字典` 写进了文件。
    参考实现 = `节点网络.py` 真源写的同一份内容（同一路径、同一入参）。
    两腿对拍以此为契约，避免「自己和自己比」的空转。

    反跑：恢复 `_globals` 先于形参 → 原生腿写出 `{"甲": 1}`（全局）→ 本用例红。
    """
    if not os.path.isfile(_节点网络py):
        pytest.skip('转译腿契约真源 节点网络.py 不存在')

    with tempfile.TemporaryDirectory(prefix='_r140_写json_') as 目录:
        出 = os.path.join(目录, '出.txt').replace('\\', '/')
        参 = os.path.join(目录, '参.txt').replace('\\', '/')

        # 参考实现先行：同一份入参，落参.txt
        真源 = _节点网络真源()
        真源.写JSON(参, {"键": "值"})
        with open(参, 'r', encoding='utf-8') as fh:
            参考 = fh.read()

        源 = ('从 节点网络 导入 写JSON, 读文本\n'
              '\n'
              '设 字典 为 {"甲": 1}\n'
              '\n'
              '段落 主():\n'
              '  写JSON("%s", {"键": "值"})\n'
              '  输出(读文本("%s"))\n'
              '  返回 0\n' % (出, 出))
        主 = 写文件(目录, '主.light', 源)
        nat_rc, nat_行 = 原生腿跑(主, 目录)

    assert json.loads(参考) == {"键": "值"}, '契约真源写错了源语义: %r' % 参考
    assert nat_rc == 0, '原生腿未跑通 rc=%s 输出=%s' % (nat_rc, nat_行)
    产物 = '\n'.join(nat_行)
    try:
        实际 = json.loads(产物)
    except ValueError:
        raise AssertionError('原生腿输出不是 JSON：%r' % 产物)
    assert 实际 == {"键": "值"}, \
        '原生腿写JSON 落到了同名全局（L-182 回归）：%r' % 产物
    # 与契约真源逐字节同构（不只是「看起来对」）
    assert json.loads(产物) == json.loads(参考), '与契约真源不一致'


# ---------------------------------------------------------------------------
# A2-L191：节点模块由「编不过」转「可编」
# ---------------------------------------------------------------------------
@skip_without_clang
def test_L191_节点作被导入模块_顶层段名不再串作用域():
    """驱动 `从 节点 导入 主。` —— 让 `节点` **作为被导入模块**参与多模块编译。

    根因：多模块编译时 `_module_statements` 混装了「先被导入模块、后主模块」
    的顶层语句（T7C 次序），`_gen_global_init` 统一用主模块上下文生成，
    被导入模块顶层的 `异步 运行 主环境()` 段名就解析到了**入口模块**作用域。

    ⚠️ 必须用驱动形态。把 `stdlib/分布式/节点.light` **当入口**直接编译是
    **测不出**这条缺陷的（那种情况下 `_current_module` 本来就是 `节点`，
    回退补丁也照样绿 —— 实测反跑确认过，是典型假绿断言）。

    ⚠️ 只编译、不执行：L-191 修好后 `节点` 顶层会真的启动 worker 守护进程、
    连不上主控而挂死（该现象另立 L-192，见 `docs/功能对标/语言缺陷账.md`）。
    本用例判据**仅限编译期不再串作用域**，刻意不做执行断言。

    反跑：把 `_gen_global_init` 的逐语句模块切换去掉 → 重新抛
    「未定义的段落：主环境」→ 本用例红。
    """
    节点 = os.path.join(仓库根, 'stdlib', '分布式', '节点.light')
    if not os.path.isfile(节点):
        pytest.skip('标准库已无 节点.light')
    from llvm.compiler import compile_light_typed  # type: ignore[import]

    with tempfile.TemporaryDirectory(prefix='_r140_节点_') as 目录:
        驱动 = 写文件(目录, '驱动.light',
                    '从 节点 导入 主。\n段落 主():\n  输出("SMOKE_OK")\n  返回 0\n')
        try:
            compile_light_typed(驱动, os.path.join(目录, '产物'), optimize_level=2)
        except Exception as 错:  # noqa: BLE001 —— 编译期任何异常都是本用例的失败信号
            raise AssertionError(
                'L-191 回归：节点 作为被导入模块仍编不过：%s: %s'
                % (type(错).__name__, str(错).splitlines()[0][:200]))


# ---------------------------------------------------------------------------
# 补丁哨兵：防两处修复被后续合流无声回滚（存在性断言，与上面的行为断言分工）
# ---------------------------------------------------------------------------
def test_补丁哨兵_两处修复都在源码里():
    """行为用例挡语义回归；本条挡「补丁整段消失」。"""
    代码 = os.path.join(_SRC, 'llvm', 'codegen_typed.py')
    with open(代码, 'r', encoding='utf-8') as fh:
        文本 = fh.read()
    assert '_current_seg_param_names' in 文本, 'L-182 形参旁路补丁不见了'
    assert '_module_statement_modules' in 文本, 'L-191 模块切换补丁不见了'
    with open(os.path.join(_SRC, 'llvm', 'compiler.py'), 'r', encoding='utf-8') as fh:
        assert '_collecting_module' in fh.read(), 'L-191 收集阶段标记补丁不见了'
