# -*- coding: utf-8 -*-
"""
lightpub 文档「可导入性」闸门。

要拦的东西
----------
docs/lightpub/*.md 是 tools/gen_lightpub_docs.py 生成的，每篇两个「导入方式」
代码块。历史上这些块无条件用光明围栏标注，等于对每个包都承诺「照这样写就能用」。
2026-08-21 实测：109 篇 × 2 块 = 218 块里只有 98 块真跑得通。

为什么已有的文档示例扫描面拦不住
--------------------------------
tests/unit/doc_block_scan.py 只验证「能否编译」。`导入 GUI框架` 编译完全正常，
生成 `import stdlib.lightpub.GUI框架`，运行时才 ModuleNotFoundError。
编译期正确、运行期骗人的块，那道闸门一个都抓不到——这道闸门补的正是这一段。

双向断言
--------
1. 标了光明围栏 → 必须真能导入。否则文档在说谎（承诺了做不到的事）。
2. 标了 text 且内容是单行导入 → 必须真的导不进来。否则文档在瞒着好东西：
   包已经通了、文档还挂着「跑不通」的警告，读者会绕开一个可用的包。
   单向断言只能防「吹牛」，防不住「过期的悲观」，而过期的悲观同样会烂。

判据单点
--------
判定一律走 tools/lightpub_importability.py，那里不复刻编译器的 P0/P1/P2
分支，而是直接调真正的代码生成器编译 `导入 X`、抠出它实际吐的 import 行、
再真 import 一遍。所以这道闸门与编译器物理上不可能漂移。

反跑记录（2026-08-21，实测）
--------------------------
基线：3 passed。
- 把 docs/lightpub/GUI框架.md 里 `导入 GUI框架` 的围栏从 text 改成 light
  → **1 failed, 2 passed**，红的正是 test_光明围栏的导入块必须真能导入；
  改回 → 3 passed。
- 把 docs/lightpub/JSON.md 里 `导入 JSON` 的围栏从 light 改成 text
  → **1 failed, 2 passed**，红的正是 test_标成text的导入块必须真的导不进来；
  改回 → 3 passed。
两次都只有对应那一条红，另两条不受污染——正是想要的粒度。
"""

import os
import re
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_DOCS = os.path.join(_ROOT, 'docs', 'lightpub')
_TOOLS = os.path.join(_ROOT, 'tools')
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from lightpub_importability import 判定  # noqa: E402

# 与 doc_block_scan.LANG_TAGS 保持一致：四个标签都算「声称是光明代码」
_光明标签 = frozenset(('light', '光明', 'duan', '段言'))
_围栏 = re.compile(r'^([ \t]*)(?:`{3,}|~{3,})[ \t]*(\w*)[ \t\r]*$')
_导入行 = re.compile(r'^导入\s+\S+$')

# 218 = 109 个包 × 2 种写法。留出余量，只为拦「扫描面塌成 0」这种假绿，
# 不是为了锁死包数量——新增包会让它变大，这里只卡下界。
_最少导入块 = 200


def _遍历导入块():
    """产出 (相对路径, 行号, 围栏标签, 导入语句)。只收单行「导入 …」块。"""
    for 目录, 子目录, 文件名表 in os.walk(_DOCS):
        子目录[:] = [d for d in 子目录 if d not in ('.git', 'node_modules')]
        for fn in sorted(文件名表):
            if not fn.endswith('.md'):
                continue
            p = os.path.join(目录, fn)
            rel = os.path.relpath(p, _ROOT).replace('\\', '/')
            try:
                with open(p, encoding='utf-8') as f:
                    行表 = f.read().split('\n')
            except (OSError, UnicodeDecodeError):
                continue
            i = 0
            while i < len(行表):
                m = _围栏.match(行表[i].rstrip('\r'))
                if not m:
                    i += 1
                    continue
                标签 = m.group(2)
                j = i + 1
                体 = []
                while j < len(行表) and not _围栏.match(行表[j].rstrip('\r')):
                    体.append(行表[j].rstrip('\r'))
                    j += 1
                正文 = '\n'.join(体).strip()
                if _导入行.match(正文):
                    yield rel, i + 1, 标签, 正文
                i = j + 1


class Test_lightpub文档可导入性(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.块表 = list(_遍历导入块())

    def test_扫描面没有塌掉(self):
        """先确认扫到了东西——扫到 0 个块会让下面两条断言退化成永真式。"""
        self.assertGreaterEqual(
            len(self.块表), _最少导入块,
            f'只在 docs/lightpub 扫到 {len(self.块表)} 个单行导入块'
            f'（至少应有 {_最少导入块} 个），提取器或文档目录可能坏了')

    def test_光明围栏的导入块必须真能导入(self):
        谎话 = []
        for rel, 行号, 标签, 语句 in self.块表:
            if 标签 not in _光明标签:
                continue
            结论 = 判定(语句)
            if not 结论.可用:
                谎话.append(f'  {rel}:{行号} ```{标签} {语句!r} → {结论.原因}：{结论.说明}')
        self.assertEqual(
            [], 谎话,
            '这些导入块用光明围栏声称可用，实际跑不通：\n' + '\n'.join(谎话[:20]) +
            '\n要么把包接上（放 stdlib/lightpub/<包名>.py），'
            '要么重跑 tools/gen_lightpub_docs.py 让围栏降级成 text。')

    def test_标成text的导入块必须真的导不进来(self):
        过期的悲观 = []
        for rel, 行号, 标签, 语句 in self.块表:
            if 标签 in _光明标签:
                continue
            结论 = 判定(语句)
            if 结论.可用:
                过期的悲观.append(f'  {rel}:{行号} ```{标签} {语句!r} → 其实已经能用了')
        self.assertEqual(
            [], 过期的悲观,
            '这些导入块被标成非光明围栏（读者会以为不可用），实际已经跑得通：\n' +
            '\n'.join(过期的悲观[:20]) +
            '\n重跑 tools/gen_lightpub_docs.py 把围栏升回 light。')


if __name__ == '__main__':
    unittest.main()
