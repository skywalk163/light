# -*- coding: utf-8 -*-
"""
R12B 定向测试：变量赋值 / 容器索引 / 写回语义族根因修复（codegen-container-writeback-R12B）。

覆盖缺陷（见 docs/known_issues.md「R10-12g R11A」章）：
  R11A-02  内建函数名作局部变量 → 算术静默返 []（现局部变量遮蔽内建）
  R11A-03  读列表下标 0 赋变量返 []（main 已顺带修复，guard 用例）
  R11A-04  `除以` 对 dict 取出值的类型推断（runtime dv_to_float 缺 REF 解引用）
  R11A-10  嵌套容器写回（codegen 多层链写回 + runtime REF 写透/同存储 no-op）
  R11A-11  dict 跨函数写回（T7B 已修复，guard 用例）
  R11C-2   字典取出的容器两段式修改穿透（REF 写透；runtime 所有权重构仍为长期缺口）

全部用例走 O0 真编译真跑（compile_light_typed optimize_level=0 + 真 exe 子进程），
输出经 `KEY=VALUE` 行解析断言。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / 'tests' / 'unit', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from test_runtime_builtin_O0 import _native_run  # noqa: E402  O0 编译 + 真 exe 子进程


class CodegenContainerWritebackR12B(unittest.TestCase):
    """R12B 变量/容器/索引写回根因修复反跑（O0 真编译真跑）。"""

    # ---- R11A-02：内建函数名作局部变量（局部变量遮蔽内建，Python 语义）----

    def test_R11A02_内建名作变量算术(self):
        src = '''段落 主:
  设 删除 为 1
  设 删除 为 删除 加上 1
  设 替换 为 10
  设 替换 为 替换 加上 2
  设 插入 为 20
  设 插入 为 插入 加上 3
  设 最小 为 5
  设 最小 为 最小 加上 4
  输出("A=" 加上 转文本(删除))
  输出("B=" 加上 转文本(替换))
  输出("C=" 加上 转文本(插入))
  输出("D=" 加上 转文本(最小))
'''
        out = _native_run(src)
        self.assertEqual(out['A'], '2')
        self.assertEqual(out['B'], '12')
        self.assertEqual(out['C'], '23')
        self.assertEqual(out['D'], '9')

    def test_R11A02_内建名作变量传参位置(self):
        # 核心解析坑：内建名出现在函数调用括号内会被误解析成无参内建调用
        # `删除()`，如 `转文本(删除)`。修复后应读出变量值 2。
        src = '''段落 主:
  设 删除 为 2
  输出("R=" 加上 转文本(删除))
'''
        out = _native_run(src)
        self.assertEqual(out['R'], '2')

    # ---- R11A-03：读列表下标 0（main 已顺带修复，guard）----

    def test_R11A03_读下标0(self):
        src = '''段落 主:
  设 d 为 列表(10, 20)
  设 x 为 d[0]
  设 y 为 d[1]
  输出("Z0=" 加上 转文本(x))
  输出("Z1=" 加上 转文本(y))
'''
        out = _native_run(src)
        self.assertEqual(out['Z0'], '10')
        self.assertEqual(out['Z1'], '20')

    # ---- R11A-04：`除以`（真除）对容器取出值（REF）的类型推断 ----

    def test_R11A04_dict值真除(self):
        src = '''段落 主:
  设 d 为 字典()
  字典设置(d, "k", 10)
  设 v 为 字典获取(d, "k")
  设 奇 为 字典()
  字典设置(奇, "k", 5)
  设 w 为 字典获取(奇, "k")
  输出("D2=" 加上 转文本(v 除以 2))
  输出("D5=" 加上 转文本(w 除以 2))
'''
        out = _native_run(src)
        self.assertEqual(out['D2'], '5')
        self.assertEqual(out['D5'], '2.5')

    def test_R11A04_list值真除与整除对照(self):
        # list 元素在 main 本就正确（guard）；整除路径不受 REF 影响（guard）。
        src = '''段落 主:
  设 d 为 列表(10, 20)
  设 v 为 d[1]
  设 c 为 字典()
  字典设置(c, "k", 10)
  设 w 为 字典获取(c, "k")
  输出("L3=" 加上 转文本(v 除以 3))
  输出("FD=" 加上 转文本(w 整除 2))
'''
        out = _native_run(src)
        self.assertEqual(out['L3'], '6.66667')
        self.assertEqual(out['FD'], '5')

    # ---- R11A-10：嵌套容器写回 ----

    def test_R11A10_单层索引赋值回归(self):
        src = '''段落 主:
  设 x 为 列表(1, 2)
  设 x[0] 为 7
  输出("S=" 加上 转文本(x[0]))
'''
        out = _native_run(src)
        self.assertEqual(out['S'], '7')

    def test_R11A10_嵌套list写回(self):
        src = '''段落 主:
  设 外 为 列表(列表(1, 2), 列表(3, 4))
  设 外[0][1] 为 88
  输出("L=" 加上 转文本(外[0][1]))
'''
        out = _native_run(src)
        self.assertEqual(out['L'], '88')

    def test_R11A10_dict内list两段式写回(self):
        # taskbook 反跑判据原样：取出到变量 → 改元素 → 外层可见。
        src = '''段落 主:
  设 外 为 字典()
  设 内 为 列表(1, 2)
  字典设置(外, "k", 内)
  设 d 为 字典获取(外, "k")
  设 d[0] 为 99
  设 r 为 字典获取(外, "k")
  输出("R=" 加上 转文本(r[0]))
'''
        out = _native_run(src)
        self.assertEqual(out['R'], '99')

    def test_R11A10_dict内list单语句链写回(self):
        src = '''段落 主:
  设 外 为 字典()
  设 内 为 列表(1, 2)
  字典设置(外, "k", 内)
  设 外["k"][0] 为 99
  设 r 为 字典获取(外, "k")
  输出("R=" 加上 转文本(r[0]))
'''
        out = _native_run(src)
        self.assertEqual(out['R'], '99')

    def test_R11A10_dict内dict写回(self):
        src = '''段落 主:
  设 外 为 字典()
  设 中 为 字典()
  字典设置(中, "x", 1)
  字典设置(外, "k", 中)
  设 外["k"]["x"] 为 88
  设 r 为 字典获取(外, "k")
  输出("R=" 加上 转文本(字典获取(r, "x")))
'''
        out = _native_run(src)
        self.assertEqual(out['R'], '88')

    def test_R11A10_三层链写回(self):
        src = '''段落 主:
  设 外 为 字典()
  设 中 为 列表(列表(1, 2))
  字典设置(外, "k", 中)
  设 外["k"][0][1] 为 55
  设 r 为 字典获取(外, "k")
  输出("R=" 加上 转文本(r[0][1]))
'''
        out = _native_run(src)
        self.assertEqual(out['R'], '55')

    # ---- R11A-11：dict 跨函数写回（T7B 已修复，guard）----

    def test_R11A11_dict参数函数内修改写回(self):
        src = '''段落 改值 接收 缓存, 键:
  字典设置(缓存, 键, 2)
段落 主:
  设 c 为 字典()
  字典设置(c, "k", 1)
  改值(c, "k")
  输出("W=" 加上 转文本(字典获取(c, "k")))
'''
        out = _native_run(src)
        self.assertEqual(out['W'], '2')

    # ---- R11C-2：dict 取出的容器两段式写回穿透（REF 写透）----

    def test_R11C2_dict内dict两段式改键(self):
        src = '''段落 主:
  设 外 为 字典()
  设 中 为 字典()
  字典设置(中, "x", 1)
  字典设置(外, "k", 中)
  设 d 为 字典获取(外, "k")
  设 d["y"] 为 7
  设 r 为 字典获取(外, "k")
  输出("R=" 加上 转文本(字典获取(r, "y")))
'''
        out = _native_run(src)
        self.assertEqual(out['R'], '7')

    def test_R11C2_dict取REF再获取嵌套dict(self):
        # dv_dict_get 缺 REF 解引用修复：内层 dict 取出后再 字典获取 应工作。
        src = '''段落 主:
  设 外 为 字典()
  设 中 为 字典()
  字典设置(中, "x", 42)
  字典设置(外, "k", 中)
  设 r 为 字典获取(外, "k")
  输出("R=" 加上 转文本(字典获取(r, "x")))
'''
        out = _native_run(src)
        self.assertEqual(out['R'], '42')


if __name__ == '__main__':
    unittest.main(verbosity=2)
