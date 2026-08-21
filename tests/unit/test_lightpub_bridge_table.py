# -*- coding: utf-8 -*-
"""
_STDLIB_BRIDGE 一致性闸门。

要拦的东西
----------
`stdlib/lightpub/__init__.py` 的 `_STDLIB_BRIDGE` 是「包名 → Python 模块名」，
唯一读者是 `get_stdlib_bridge()`，而它只在 `src/code_generator.py`
`_resolve_lightpub_import()` 的 **P0 分支**里被调用。P1/P2 走的是
「stdlib/ 根目录同名优先，否则 stdlib.lightpub.<包名>」，压根不查这张表。

2026-08-21 实测盘点这张表（原 53 条）：
- 桥接文件缺失 **0** 条（53 个 stdlib/lightpub/<名>.py 全都在）；
- 但 **49** 条的 priority≠P0 —— 永远查不到，摆着不生效；
- 另 **5** 条（加密 / 日期时间 / 数学运算 / 单元测试框架 / 配置管理）连
  PACKAGES 都没有，`resolve_import()` 直接返回 None，更没机会查到。

所以表被砍到 4 条 P0。这道闸门守住「别再攒死项」，同时守住反方向：
新增 P0 包必须同时补桥接，不能只改元数据。

三条断言
--------
1. 每个 key 都得在 PACKAGES 里，且 priority == 'P0'
   —— 拦「往表里加永远查不到的条目」（正是这次清掉的那 54 条的形态）。
2. 每个 value 都得有 stdlib/lightpub/<value>.py，且真能 import
   —— 拦「表指向一个不存在或一 import 就炸的模块」。这次实测虽然 0 例，
   但它是唯一能让 P0 包在运行期崩掉的路径，值得钉住。
3. PACKAGES 里所有 P0 包都得在表里
   —— 反方向：外部数据源新增 P0 包时提醒补桥接，别让表悄悄漏一个。

为什么不断言「恒等映射」
----------------------
当前 4 条都是 key == value，此时表项其实可有可无：P0 分支查不到时会退回
`return real_name`，结果一样。但表存在的意义就是留出「将来某个 P0 包要映射到
另一个 Python 模块名」的位置，所以不锁恒等。

反跑记录（2026-08-21，实测跑出来的，不是推演）
--------------------------------------------
基线：3 passed。
- 加 `'YAML': 'YAML'`（P2，且 stdlib/lightpub/YAML.py 不存在）
  → **2 failed, 1 passed**，key 那条和 value 那条同时红。两条都该红：它既是
  查不到的条目，又指向不存在的模块。这说明单看「红了几条」不足以定位，
  所以补跑了下面这个更干净的变体。
- 加 `'HTTP服务端': 'HTTP服务端'`（P2，但桥接文件确实存在）
  → **1 failed, 2 passed**，只红 test_表里每个key都必须是P0包。这是本条断言
  的纯净证明。
- 从表里删掉 `'JSON'` → **1 failed, 2 passed**，只红 test_每个P0包都必须在表里。
- 把 `'CSV'` 的值改成 `'不存在的模块名'` → **1 failed, 2 passed**，只红
  test_表里每个value都必须真能导入。
每次改动都在 finally 里恢复，恢复后两次复测都回到 3 passed。

"""

import importlib
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_STDLIB = os.path.join(_ROOT, 'stdlib')
for _p in (_STDLIB, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lightpub  # noqa: E402


class Test_STDLIB_BRIDGE表(unittest.TestCase):

    def test_表里每个key都必须是P0包(self):
        """表只服务 P0 分支；非 P0 的 key 写进去也不会被查到，等于死项。"""
        问题 = []
        for 包名 in sorted(lightpub._STDLIB_BRIDGE):
            信息 = lightpub.PACKAGES.get(包名)
            if 信息 is None:
                问题.append(f'  {包名}：不在 PACKAGES 里，resolve_import 会返回 None，本表永不被查')
            elif 信息.get('priority') != 'P0':
                问题.append(f'  {包名}：priority={信息.get("priority")}，只有 P0 会查本表')
        self.assertEqual([], 问题, '\n_STDLIB_BRIDGE 里有查不到的条目：\n' + '\n'.join(问题))

    def test_表里每个value都必须真能导入(self):
        """value 指向的桥接模块必须存在且 import 不炸——否则 P0 包运行期崩。"""
        问题 = []
        for 包名, 模块名 in sorted(lightpub._STDLIB_BRIDGE.items()):
            路径 = os.path.join(_STDLIB, 'lightpub', 模块名 + '.py')
            if not os.path.isfile(路径):
                问题.append(f'  {包名} → {模块名}：缺 stdlib/lightpub/{模块名}.py')
                continue
            try:
                importlib.import_module('lightpub.' + 模块名)
            except BaseException as e:
                问题.append(f'  {包名} → {模块名}：导入即报错 {type(e).__name__}: {e}')
        self.assertEqual([], 问题, '\n_STDLIB_BRIDGE 指向了导不进来的模块：\n' + '\n'.join(问题))

    def test_每个P0包都必须在表里(self):
        """反方向：新增 P0 包时别忘了补桥接，否则表会悄悄漏一个。"""
        缺失 = sorted(名 for 名, 信息 in lightpub.PACKAGES.items()
                      if 信息.get('priority') == 'P0' and 名 not in lightpub._STDLIB_BRIDGE)
        self.assertEqual([], 缺失,
                         'PACKAGES 里这些 P0 包不在 _STDLIB_BRIDGE 里：' + ', '.join(缺失))


if __name__ == '__main__':
    unittest.main()
