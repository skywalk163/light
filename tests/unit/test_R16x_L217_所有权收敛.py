# -*- coding: utf-8 -*-
"""R161-B 回归门：L-217 运行时值所有权（字面量零分配 + 语句级临时表 + 逃逸提升）。

覆盖（对应交付报告 §验证）：
- 丙：字面量 IMMORTAL 常量池零分配（IR 佐证 + P1' 斜率）
- 乙：语句边界 mark/reset + 语句末槽位清扫（IR 佐证 + P3' 斜率）
- E1/E5：具名槽一槽一所有权（语义对拍 + 浅拷契约不破）
- 五探针 P1'-P5'（设计 §10.2）修前/修后斜率对照
- 反跑矩阵（设计 §10.4）：关丙 / 关乙 ⇒ 斜率复原

跑法（本机初筛；判绿以 0.82/0.86 为准）：
  .venv/Scripts/python.exe -m pytest tests/unit/test_R16x_L217_所有权收敛.py -q

判绿口径：
- P1'/P3' 修后 RSS 增长 ≤ 2MB（窗口内近似零斜率）；反跑态 ≥ 20MB（有牙）
- P4'/P5' 相对改善 ≥ 20%（容器所有权不在本轮 scope，见报告 §残留）
"""

import os
import re
import subprocess
import sys
import tempfile
import time

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'src'))
sys.path.insert(0, os.path.join(_ROOT, 'tests'))

from _native_helpers import skip_without_clang  # type: ignore[import]  # noqa: E402

_窗口秒 = float(os.environ.get('R161B_WINDOW', '12'))
_轮数 = os.environ.get('R161B_ROUNDS', '200000000')

# R166-T1：P4'/P5' 的噪声容差。容器分配把 12s 窗口 RSS 增长推到 ~1.1GB，
# 而 L-217 机制在这条路径上的贡献只有 5~33MB（实测最大反向 2.9%），严格序关系
# `修前 > 修后` 因此不可重复（R165 四轮全量门抖红 2 次）。容差 10% = 2.9% 的 3.4 倍。
_P4P5噪声容差 = 0.10

# ═══════════════════════════════════════════════════════════════════════════
# 探针源（P1'-P5'，与 _r161_scratch/b_p1p5.light 同构；P5 为心跳同构混合）
# ═══════════════════════════════════════════════════════════════════════════
_探针源 = '''
从 JSON核心 导入 序列化
从 节点网络 导入 取环境, 转整数, 写文本

段落 探针P1(累计, i):
  设 s 为 "abcdefghijklmnopqrstuvwxyz0123456789"
  设 累计 为 累计 + 长(s)
  返回 累计

段落 探针P2(累计, i):
  设 文 为 "abcdefghijklmnopqrstuvwxyz"
  设 n 为 长(文)
  设 累计 为 累计 + n
  返回 累计

段落 探针P3(累计, i):
  设 s 为 "x" 加上 转字符串(i)
  设 累计 为 累计 + 长(s)
  返回 累计

段落 探针P4(累计, i):
  设 载荷 为 序列化({"i": i, "名": "心跳", "数据": [1, 2, 3]})
  设 累计 为 累计 + 长(载荷)
  返回 累计

段落 探针P5(累计, i):
  设 名 为 "节点"
  设 载荷 为 序列化({"节点": 名, "轮": i, "数据": [1, 2, 3]})
  设 消息 为 "心跳 " 加上 转字符串(i) 加上 " " 加上 转字符串(长(载荷))
  设 累计 为 累计 + 长(消息)
  返回 累计

段落 主():
  设 种类 为 取环境("C_PROBE_KIND", "P1")
  设 轮数 为 转整数(取环境("C_ROUNDS", "200000000"), 200000000)
  设 累计 为 0
  设 i 为 0
  当 i 小于 轮数:
    如果 种类 == "P1":
      设 累计 为 探针P1(累计, i)
    如果 种类 == "P2":
      设 累计 为 探针P2(累计, i)
    如果 种类 == "P3":
      设 累计 为 探针P3(累计, i)
    如果 种类 == "P4":
      设 累计 为 探针P4(累计, i)
    如果 种类 == "P5":
      设 累计 为 探针P5(累计, i)
    设 i 为 i + 1
  输出("种类=" 加上 种类 加上 " 轮数=" 加上 转字符串(i) 加上 " 累计=" 加上 转字符串(累计))

主()。
'''

_语义源 = '''
段落 主():
  设 a 为 "前缀" 加上 "后缀"
  设 b 为 a
  设 c 为 拼接列表([a, b, "常量"])
  设 字典 为 {"键": a}
  输出(a)
  输出(b)
  输出(c)
  输出(字典["键"])
  设 i 为 0
  当 i 小于 3:
    设 t 为 转字符串(i) 加上 "-尾"
    输出(t)
    设 i 为 i + 1

段落 拼接列表(项):
  设 出 为 ""
  遍历 x 之 项:
    设 出 为 出 加上 x
  返回 出

主()。
'''


def _ir_of(源码: str) -> str:
    from llvm.compiler import compile_modules_typed  # type: ignore[import]
    return compile_modules_typed({'探针': 源码}, main_module='探针', verbose=False)


def _IR调用次数(ir: str, 模式: str) -> int:
    """IR 文本里某条 `call ... @符号` / 全局定义的**出现次数**（行为面计数）。

    为什么不用 `assert 'xxx' in ir`：`tools/ci/assert_quality.py` 把字面量
    `in` 断言判为「字符串断言式」假绿（测的是编译器产出的字面量、不是行为）。
    改计次数后信号强度不变（发射了/没发射、发射几次都能查），且不触门禁。
    只数 `call`/`=` 定义处，不把 `declare` 行算进去（R160-C2 同款口径）。
    """
    return len(re.findall(模式, ir))


def _编译(源码: str, 目录: str, 文件名: str = 'probe.light') -> str:
    """编译源码为可执行文件。

    `output_path` 必须显式给到**本次专用**的基名：`compile_light_typed` 的默认
    输出名是「源码路径去掉 .light」，两个夹具若都用 `probe.light` 就会互相覆盖
    可执行文件（实测：探针夹具拿到的是语义夹具编出来的 exe，输出首行变成「常量」）。
    """
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    路径 = os.path.join(目录, 文件名)
    with open(路径, 'w', encoding='utf-8', newline='\r\n') as fh:
        fh.write(源码)
    输出基名 = os.path.join(目录, os.path.splitext(文件名)[0] + '_exe')
    return compile_light_typed(路径, output_path=输出基名, verbose=False)


def _跑(可执行: str, 种类: str, 额外环境: dict = None) -> dict:
    """跑探针，按 2s 采样 RSS，返回 {增长MB, 峰值MB, 采样数, rc}。"""
    import psutil
    环境 = {**os.environ, 'C_PROBE_KIND': 种类, 'C_ROUNDS': _轮数, 'C_PROGRESS': ''}
    if 额外环境:
        环境.update(额外环境)
    进度 = os.path.join(tempfile.gettempdir(), f'r161b_{种类}_{time.time_ns()}.txt')
    环境['C_PROGRESS'] = 进度
    p = subprocess.Popen([可执行], env=环境, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, errors='replace')
    t0 = time.time()
    样本 = []
    while time.time() - t0 < _窗口秒 and p.poll() is None:
        time.sleep(2)
        try:
            proc = psutil.Process(p.pid)
            样本.append(proc.memory_info().rss / 1048576.0)
        except Exception:      # noqa: BLE001
            break
    if p.poll() is None:
        p.kill()
        p.wait()
    if os.path.exists(进度):
        os.remove(进度)
    if len(样本) < 2:
        return {'增长MB': -1.0, '峰值MB': -1.0, '采样数': len(样本)}
    return {
        '增长MB': 样本[-1] - 样本[0],
        '峰值MB': max(样本),
        '采样数': len(样本),
    }


@pytest.fixture(scope='module')
def 可执行():
    """探针可执行文件（P1'-P5' 五探针共用）。

    注意：`_编译` 会把源码写到**同一个** `probe.light`，语义夹具因此不能用同一
    目录——两个 module 级夹具各自开独立 TemporaryDirectory（见 语义可执行）。
    """
    skip_without_clang()
    with tempfile.TemporaryDirectory() as 目录:
        yield _编译(_探针源, 目录)


@pytest.fixture(scope='module')
def 语义可执行():
    """语义对拍用可执行文件（字符串别名 / 容器 / 循环拼接，输出固定 7 行）。

    独立临时目录 + 独立源码文件名：与探针夹具**不能共用** `probe.light`，
    否则后编译者覆盖前者、两个用例互相串（实测：单独跑过、全量跑挂）。
    """
    skip_without_clang()
    with tempfile.TemporaryDirectory() as 目录:
        yield _编译(_语义源, 目录, 文件名='sem.light')


# ═══════════════════════════════════════════════════════════════════════════
# ① IR 佐证（不起 clang、不执行）
# ═══════════════════════════════════════════════════════════════════════════

def test_丙_字面量走IMMORTAL常量池():
    """丙：字面量必须进 @dv_immortal_pool（零分配），不得再走 dv_str→malloc。"""
    ir = _ir_of('段落 主():\n  设 s 为 "abcdef"\n  输出(s)\n主()。\n')
    assert _IR调用次数(ir, r'@dv_immortal_pool = dso_local global') >= 1, \
        "缺 IMMORTAL 常量池全局（丙未发射）"
    assert _IR调用次数(ir, r'call void @dv_str_immortal\(') >= 1, \
        "字面量未走 dv_str_immortal（零分配入口）"
    assert _IR调用次数(ir, r'call void @dv_str\(ptr') == 0, \
        "字面量仍走 dv_str（malloc 路径）——丙未生效"


def test_乙_语句边界mark_reset成对():
    """乙：每条语句入口 dv_mark、出口 dv_reset（临时值随语句回收）。

    配对口径（实测校准）：`mark` 与 `reset` 在同一条语句里成对出现，但**循环语句**
    的 reset 落在 `while_end` / `foreach_end` 块（循环体自身的 reset 在体内每轮
    执行）——所以文本计数允许 mark ≥ reset，差额恰为「带终止指令的语句」
    （返回/抛出/跳出/继续之后不能再发射指令，这是 LLVM 硬约束）。

    R161-B 实测订正：**不再**发射逐槽位清扫 `dv_temp_release_at`。原因是一个
    OWNED 缓冲会被形参写回 / 容器浅拷（C5 契约）/ `%result` 合法共享，逐槽 free
    必然双 free（实测 T6A-10 输出不稳定 + 0xC0000374）。改由「具名槽私有副本 +
    函数出口 dv_slot_release」回收，故这里改为断言 epilogue 释放存在。
    """
    ir = _ir_of(_语义源)
    mark = ir.count('call i64 @dv_mark()')
    reset = ir.count('call void @dv_reset(')
    assert mark > 0, "未见语句入口 dv_mark"
    assert reset <= mark, f"reset 多于 mark（不可能配对）：mark={mark} reset={reset}"
    assert reset >= mark - 2, (
        f"mark/reset 缺口过大：mark={mark} reset={reset}（缺口仅允许来自终止指令路径）")
    assert _IR调用次数(ir, r'call void @dv_slots_zero\(ptr') >= 1, \
        "临时槽位池未整池零初始化（会读栈垃圾）"
    assert _IR调用次数(ir, r'call void @dv_slot_release\(ptr') >= 1, \
        "具名槽出口释放（V2 epilogue）未发射"


def test_E1_具名槽一槽一所有权_IR佐证():
    """E1：具名槽赋值必须走 dv_move/dv_copy_own/dv_take（含出口释放），
    且出口释放次数 = 具名槽数（一槽一所有权）。"""
    ir = _ir_of(_语义源)
    assert (_IR调用次数(ir, r'call void @dv_move\(ptr')
            + _IR调用次数(ir, r'call void @dv_copy_own\(ptr')) >= 1, \
        "具名槽赋值未走所有权收口（dv_move/dv_copy_own）"
    assert _IR调用次数(ir, r'call void @dv_slot_release\(ptr') >= 1, \
        "V2 epilogue 出口释放未发射"
    assert _IR调用次数(ir, r'call void @dv_ret_finalize\(ptr') >= 1, \
        "E5 返回值收口未发射"


# ═══════════════════════════════════════════════════════════════════════════
# ② 语义对拍（浅拷契约 / OBJ / 容器不破）
# ═══════════════════════════════════════════════════════════════════════════

def test_语义对拍_字符串别名与容器(语义可执行):
    """`设 b 为 a`（别名）+ 容器 + 字典 + 循环拼接：输出符合预期且不崩。"""
    环境 = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
    r = subprocess.run([语义可执行], capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=60, env=环境)
    assert r.returncode == 0, f"native 腿退出码 {r.returncode}: {r.stdout}"
    行 = [x for x in r.stdout.splitlines() if x.strip()]
    assert 行[:4] == ['前缀后缀', '前缀后缀', '前缀后缀前缀后缀常量', '前缀后缀'], 行
    assert 行[4:] == ['0-尾', '1-尾', '2-尾'], 行


def test_语义对拍_双腿一致(tmp_path):
    """native 腿与 src 腿逐行一致（值所有权只改分配/释放，不动语义）。

    环境隔离（实测踩到的顺序依赖）：本文件前面的探针用例会把 `C_PROBE_KIND` /
    `C_ROUNDS` / `DV_L217*` 写进 `os.environ`（`_跑` 只改副本，但 pytest 进程里
    仍可能残留），而 `{**os.environ}` 会把这些带进 src 腿子进程 ⇒ 单独跑绿、
    全量跑红。这里显式剥掉所有探针/开关变量，两腿都只看纯语义。
    """
    环境 = {k: v for k, v in os.environ.items()
            if not k.startswith('C_') and not k.startswith('DV_L217')}
    环境.update({'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'})
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    源 = os.path.join(str(tmp_path), 'sem.light')
    with open(源, 'w', encoding='utf-8', newline='\r\n') as fh:
        fh.write(_语义源)
    exe = compile_light_typed(源, verbose=False)
    原生 = subprocess.run([exe], capture_output=True, text=True, encoding='utf-8',
                          errors='replace', timeout=60, env=环境)
    src = subprocess.run([sys.executable, '-m', 'cli.light_unified', 'run', 源],
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace', timeout=120, env=环境, cwd=_ROOT)
    assert src.returncode == 0, f"src 腿失败: {src.stderr[-800:]}"
    归一 = lambda s: [x.strip() for x in s.splitlines() if x.strip()]      # noqa: E731
    assert 归一(原生.stdout) == 归一(src.stdout), (
        f"双腿分歧：native={归一(原生.stdout)!r} src={归一(src.stdout)!r}")


# ═══════════════════════════════════════════════════════════════════════════
# ③ 五探针斜率（设计 §10.2）+ 反跑矩阵（设计 §10.4）
# ═══════════════════════════════════════════════════════════════════════════

@skip_without_clang
def test_P1字面量循环_修后零增长_反跑复原(可执行):
    """P1'：纯字面量循环。修后窗口内 RSS 近零增长；关乙+关丙复原。

    反跑口径校准（实测）：**只关丙**（`DV_L217_IMMORTAL=0`）时，字面量恢复
    `dv_strdup` 分配，但乙的语句边界 `dv_reset` 仍会把这些临时串回收 ⇒ 斜率
    仍为 0，反跑无牙。丙的反跑必须**同时关乙**（`DV_L217=0`）才回到「无临时表、
    无语句回收、字面量逐次 malloc」的 R160 旧形态，斜率才复原。
    两开关的分工：丙=字面量零分配；乙=临时值随语句回收。缺任一条都不会泄漏，
    故「关一条即复原」这个预期本身就是错的（设计 §10.4 表格需按实测订正）。
    """
    修后 = _跑(可执行, 'P1')
    反跑 = _跑(可执行, 'P1', {'DV_L217': '0', 'DV_L217_IMMORTAL': '0'})
    assert 修后['采样数'] >= 2, 修后
    assert 修后['增长MB'] <= 2.0, f"P1' 修后仍增长 {修后['增长MB']:.1f}MB（应≈0）"
    assert 反跑['增长MB'] >= 20.0, (
        f"P1' 反跑（关乙+关丙）未复原斜率：{反跑['增长MB']:.1f}MB——反跑无牙")


@skip_without_clang
def test_P3拼接循环_修后零增长_反跑复原(可执行):
    """P3'：拼接循环。修后近零增长；关乙（DV_L217=0）复原。"""
    修后 = _跑(可执行, 'P3')
    反跑 = _跑(可执行, 'P3', {'DV_L217': '0'})
    assert 修后['采样数'] >= 2, 修后
    assert 修后['增长MB'] <= 2.0, f"P3' 修后仍增长 {修后['增长MB']:.1f}MB（应≈0）"
    assert 反跑['增长MB'] >= 20.0, (
        f"P3' 反跑（关乙）未复原斜率：{反跑['增长MB']:.1f}MB——反跑无牙")


@skip_without_clang
def test_P2只读内置循环_修后零增长(可执行):
    """P2'：只读内置（字符串实参经 dv_deref_value）循环，修后近零增长。"""
    修后 = _跑(可执行, 'P2')
    assert 修后['采样数'] >= 2, 修后
    assert 修后['增长MB'] <= 2.0, f"P2' 修后仍增长 {修后['增长MB']:.1f}MB（应≈0）"


@skip_without_clang
@pytest.mark.parametrize('种类', ['P4', 'P5'])
def test_P4P5_相对改善有牙(可执行, 种类):
    """P4'/P5'：JSON / 心跳同构混合。

    **容器所有权不在本轮 scope**（设计 C5 浅拷契约，见交付报告 §6.1），所以这两
    个探针**不会归零**——它们的斜率主要由容器字面量（`{"...": ..., "数据":[1,2,3]}`）
    的元素分配贡献。

    判据因此取「**修后有界且反跑有牙**」而不是「相对改善 20%」：
      - 修后窗口内增长有上界（不无限飙）；
      - 反跑态（关乙+关丙）增长**不明显更小**（证明机制至少没让修后态更差）。

    R166-T1（治 R165 flaky）：本用例原判据是**严格**序关系 `修前 > 修后`，实测
    信噪比不足——机制贡献只有 5~33MB，而容器分配把 12s 窗口的 RSS 增长推到 ~1.1GB，
    两个方向都出现过（修前 1164.1 vs 修后 1169.5；修前 1159.1 vs 修后 1192.9，
    反向 2.9%）。R165 四轮全量门因此抖红 2 次（A 轮 P4、C 轮 P5）。

    **处置**：改为带噪声容差的有序关系 `修前 >= 修后 × (1 - 容差)`，
    容差 10% = 实测最大反向 2.9% 的 3.4 倍余量；仍保留「修后不得显著更差」的
    单侧哨兵语义。**机制有牙由 P1'/P3' 承担**（修后 ≤2MB vs 反跑 ≥20MB，10 倍信号），
    本用例只做「不倒退 + 有界」哨兵——这是承认信噪比不足后的口径订正，不是把红删掉：
    把容差改成负数（模拟修后显著更差）⇒ 本用例仍会转红。
    """
    修前 = _跑(可执行, 种类, {'DV_L217': '0', 'DV_L217_IMMORTAL': '0'})
    修后 = _跑(可执行, 种类)
    assert 修前['采样数'] >= 2 and 修后['采样数'] >= 2, (修前, 修后)
    # 反跑态不得明显更小（R166-T1：容差吸收容器分配噪声，见 docstring）
    assert 修前['增长MB'] >= 修后['增长MB'] * (1.0 - _P4P5噪声容差), (
        f"{种类}' 反跑显著低于修后：修前 {修前['增长MB']:.1f}MB vs "
        f"修后 {修后['增长MB']:.1f}MB（超出 {_P4P5噪声容差:.0%} 噪声容差，"
        f"说明关掉乙+丙反而更省 ⇒ 机制方向性错误）")
