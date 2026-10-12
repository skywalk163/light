# -*- coding: utf-8 -*-
"""
R142-C 定向用例：L-187 残余「rethrow 保留原始抛出点」（原生腿）。

背景：R138-A 流X 已修掉「栈深度单调累积」（异常对象「栈追踪」带前序残留帧），
      dv_try_pop 把调用栈深度截断回进入 try 前的快照，三次捕获帧数恒等。
      但压力探针暴露**另一类跨腿分叉**：catch 不匹配 rethrow / catch 内再抛 /
      finally 穿透后 rethrow 这三条路径，异常对象的「栈追踪」**丢失原始抛出点**
      （只剩 rethrow 点），而 Python 腿 traceback.format_exc() 保留完整调用链。

根因（runtime_typed.c::dv_throw_exception）：每次调用都**无条件覆盖**「栈追踪」
      字段。rethrow 时 dv_try_pop 已把调用栈截断回外层 try 前的快照，再用截断后
      的栈覆盖「栈追踪」，就把首次抛时的原始抛出点帧（路径甲/深层）抹掉了。

修法：dv_throw_exception 写「栈追踪」前，若异常对象已持有非空「栈追踪」（rethrow
      原异常），不再覆盖；首次抛时 dv_create_exception_with_cause 已把该字段设为
      空串，正常写入。只动 runtime_typed.c 一个函数，codegen 零改动。

跨腿契约：原生腿读 e.栈追踪，Python 腿读 traceback.format_exc()（两者字段名不同，
      已在 R138X 登记）。本用例断言**帧集合一致**：都须含原始抛出点。

「编译 + 运行」整体 fork 到独立子进程（复用 _t6b_native_helper.py）。
"""
import os
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (_ROOT, os.path.join(_ROOT, "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from tests.unit.test_T6B_时间系统内建_原生腿 import _find_msvc_env  # noqa: E402
from tests.unit.test_R131_L186L187_原生腿 import (  # noqa: E402
    _block, _frames, _native_raw, _python_raw, _clang_available,
)

# ---------------------------------------------------------------------------
# 三类 rethrow 场景：catch 不匹配 / catch 内再抛 / finally 穿透后 rethrow
# 原始抛出点均为 路径甲，必须出现在捕获点的栈追踪里（与 Python 腿一致）。
# ---------------------------------------------------------------------------
_SRC_RETHROW = """导出 主。

段落 路径甲():
  抛出 运行时错误("甲")

段落 路径乙():
  抛出 运行时错误("乙")

段落 不匹配():
  尝试:
    路径甲()
  捕获 KeyError 为 e:
    返回 "不该到这"
  返回 "不匹配未捕获"

段落 抛内():
  尝试:
    路径甲()
  捕获 异常 为 e:
    抛出 运行时错误("乙")

段落 finally穿透():
  尝试:
    路径甲()
  捕获 KeyError 为 e:
    返回 "不该到这"
  结束
  返回 "finally未捕获"

段落 捕获第(编号):
  尝试:
    如果 编号 等于 1:
      不匹配()
    否则如果 编号 等于 2:
      抛内()
    否则:
      finally穿透()
  捕获 异常 为 e:
    输出("R" 加上 转字符串(编号) 加上 "B")
    输出(e.栈追踪)
    输出("R" 加上 转字符串(编号) 加上 "E")
    返回 e.栈追踪
  返回 "未捕获"

段落 主():
  捕获第(1)
  捕获第(2)
  捕获第(3)
  设 a 为 捕获第(1)
  设 b 为 捕获第(2)
  设 c 为 捕获第(3)
  输出("FINAL_DONE")
"""

_SRC_PY = """导入 traceback

段落 路径甲():
  抛出 运行时错误("甲")

段落 路径乙():
  抛出 运行时错误("乙")

段落 不匹配():
  尝试:
    路径甲()
  捕获 KeyError 为 e:
    返回 "不该到这"
  返回 "不匹配未捕获"

段落 抛内():
  尝试:
    路径甲()
  捕获 异常 为 e:
    抛出 运行时错误("乙")

段落 finally穿透():
  尝试:
    路径甲()
  捕获 KeyError 为 e:
    返回 "不该到这"
  结束
  返回 "finally未捕获"

段落 捕获第(编号):
  尝试:
    如果 编号 等于 1:
      不匹配()
    否则如果 编号 等于 2:
      抛内()
    否则:
      finally穿透()
  捕获 异常 为 e:
    输出("R" 加上 转字符串(编号) 加上 "B")
    输出(traceback.format_exc())
    输出("R" 加上 转字符串(编号) 加上 "E")
    返回 "ok"
  返回 "未捕获"

段落 主():
  捕获第(1)
  捕获第(2)
  捕获第(3)
"""


@unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿测试")
@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
class R142X_L187_rethrow保留原始抛出点(unittest.TestCase):
    """三类路径的栈追踪语义（原生腿）：

      R1 catch 不匹配 rethrow：**同一异常对象**重新抛出 → 栈追踪须保留原始抛出点 路径甲；
      R2 catch 内抛**新异常**（运行时错误("乙")）：新对象栈 = 新抛出点 抛内，**不含** 路径甲；
      R3 finally 穿透后 rethrow：**同一异常对象**（dv_get_current_exception）→ 保留 路径甲。
    """

    def test_原生腿rethrow保留原始抛出点(self):
        raw = _native_raw(_SRC_RETHROW)
        blk1 = _block(raw, "R1")
        blk3 = _block(raw, "R3")
        self.assertIn(
            "路径甲", blk1,
            f"R1 catch 不匹配 rethrow 丢失原始抛出点 路径甲（rethrow 覆盖了首抛栈）：\n{blk1}",
        )
        self.assertIn(
            "路径甲", blk3,
            f"R3 finally 穿透后 rethrow 丢失原始抛出点 路径甲：\n{blk3}",
        )
        # R2 是新异常，不得带出 路径甲（防止好心修过头把新异常也串帧）
        blk2 = _block(raw, "R2")
        self.assertIn(
            "抛内", blk2,
            f"R2 新异常栈追踪缺新抛出点 抛内：\n{blk2}",
        )
        self.assertNotIn(
            "路径甲", blk2,
            f"R2 新异常不应带出原异常 路径甲 帧（串帧）：\n{blk2}",
        )

    def test_python腿rethrow同样保留原始抛出点(self):
        """Python 腿契约：R1/R3 rethrow 后 traceback 须含原始抛出点 路径甲。"""
        raw = _python_raw(_SRC_PY)
        for tag in ("R1", "R3"):
            blk = _block(raw, tag)
            self.assertIn(
                "路径甲", blk,
                f"Python 腿 {tag} traceback 未含原始抛出点 路径甲：\n{blk}",
            )

    def test_双腿rethrow帧集合一致(self):
        """双腿在 R1/R3 rethrow 场景下，都须含原始抛出点 路径甲。"""
        raw_n = _native_raw(_SRC_RETHROW)
        raw_p = _python_raw(_SRC_PY)
        for tag in ("R1", "R3"):
            fr_n = _frames(_block(raw_n, tag))
            # Python 腿 traceback 帧行形态：'  File "<string>", line N, in 名字'
            # 取 ", in " 之后的名字
            fr_p = []
            for ln in _block(raw_p, tag).splitlines():
                if ", in " in ln:
                    fr_p.append(ln.split(", in ", 1)[1].strip())
            self.assertIn("路径甲", fr_n, f"{tag} 原生腿缺原始抛出点：{fr_n}")
            self.assertIn("路径甲", fr_p, f"{tag} Python 腿缺原始抛出点：{fr_p}")


if __name__ == "__main__":
    unittest.main()