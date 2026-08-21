# -*- coding: utf-8 -*-
"""文档示例编译门禁（v7 版本口径单，阶段 3）。

## 立项由来

阶段 2 建成「冻结表 ↔ 实现」门禁后，还剩一个更直接的洞：**文档里的
` ```light ` 代码块从来没被编译过**。`scripts/migrate_docs.py` 是迁移器、
`tools/gen_*` 是生成器，全是单向的；没有任何东西反过来验证「照文档抄的代码
到底编不编得过」。

首次全量实测（1052 个块）：**747 通过 / 305 失败（29%）**。外部 AI 照文档写光明
写不出来、最后降级到 Python，这 29% 就是直接原因。

## 为什么把 305 条分了六类，而不是整体冻成一张基线

因为它们**不是同一种东西**。整体冻结会让基线不携带信息（口径 10：基线虚高
等于没有基线）。当前分布（2026-08-20 修完 parser 两处笔误后重生成）：

- **ROT 238** —— 像真代码但编不过，是真文档腐烂。大宗是 `定义 x 等于 y`
  （已移除语法，`file_io_design.md` / `FILE_IO_REPORT.md` 成片还在教）。
  **这才是本门禁逐条钉住的目标。**
- **ANNOTATED 18** —— 真代码里夹了行内箭头注解（`← 推断为 数|空`）。
  修法是把注解挪进注释，不是改代码。
- **ESCAPED 17** —— 引号被反斜杠转义污染（`定义列表等于\\"甲\\"，…`），
  集中在 `LANGUAGE_EXTENSIONS.md`(14) 与 `tutorials/进阶教程.md`(3)。
- **PSEUDO 17** —— 一个光明关键字都没有，纯伪代码/签名说明。
- **REPL 14** —— `>>>` 会话记录，天然编不过（`五分钟入门光明.md` 占 10）。
- **COMPILER_BUG 1** —— 编译器自己炸了，**与文档对错无关**，见下。

后四类的修法都是「改文档体裁/标签」，不是「改代码」，所以门禁对它们只卡总数
不卡逐条；ROT 才逐条钉 `(file, hash)`。

## COMPILER_BUG：永不进逐条基线，必须单独修

首轮扫描抓到 4 条，已修掉 3 条、剩 1 条：

**已修（2026-08-20）**：3 × `AttributeError: TokenType has no attribute 'ASSIGN'`
（`docs/ffi.md`、`docs/api/stdlib.md`、`docs/blog/段言自举编译器架构解析.md`）。
根因在 `src/parser_stmt.py::_parse_type_alias`：词法器发的是 `EQUALS`，parser
却查了不存在的 `ASSIGN`。修完立刻暴露同一函数里第二处笔误——`result.line,
result.col = …`，而 `ASTNode` 的字段叫 `column`，且 `TypeAlias` 是
`@dataclass(slots=True)` 没有 `__dict__`，于是硬崩。两处都补了源码级回归用例
（`tests/unit/test_a2_1_generics_unions_patterns.py::TestTypeAliasFromSource`）——
原有 `TestTypeAlias` 全是直接 new 节点，一条都没走 parser，这才是笔误活下来的原因。

**注意口径**：这 3 条修的是**编译器崩溃**，不是**文档**。修完它们从
COMPILER_BUG 转成了 ROT（`ParseError`），failing 总数仍是 305——文档本身照旧腐烂。
别把「少了 3 条 COMPILER_BUG」说成「修好了 3 个文档示例」。

**未修（1 条）**：`docs/语义密度示例集.md` 的 `情况 [头, 尾...]` 触发
**parser 无限分配**。


后者引发过一次真实事故：2026-08-20 我裸跑基线生成器，进程 15 分钟吃到
**15.5GB 且仍在涨**（~2GB/分钟，只增不减），必须 `Stop-Process` 掐掉。单变量
A/B 定位（子进程 + 900MB 看门狗）：

    情况 [头, 尾]：     → PARSE_OK，1.0s，峰值 17MB
    情况 [头, 尾...]：  → 线性 ~40MB/s，913MB 被掐，从未返回

唯一差异是 `...`。这是 DoS 级缺陷：9 行源码即可打爆编译器。该块已进
`doc_block_scan._HOSTILE_HASHES`，**扫描时根本不喂给 parser**——否则本门禁
每次跑都会重演事故。

## 门禁的四条判据

1. 不许新增 ROT（逐条按 `(file, hash)` 比对）
2. 不许新增 COMPILER_BUG
3. 噪声四类总数不许涨（允许降）
4. 基线里已修好的条目必须从基线里删掉（防基线虚高）

身份用**内容哈希**而非行号：改正文不会误伤，改代码块本身才会失效。

## 反跑（口径 17）

在 docs 下新建一个含坏语法 light 块的文件（`定义 甲 等于 1。`）→
**1 failed / 5 passed**，`test_不许新增ROT` 点名 `file:hash`；删掉即恢复
**6 passed**。只红一条，说明四条判据互不串味。实测于 2026-08-20。

## 基线怎么重生成

    python tools/ci/run_with_memory_cap.py tools/ci/gen_doc_examples_baseline.py

**必须在内存上限下跑**——原因见 `tools/ci/run_with_memory_cap.py` 文档串。
修好一批文档后重生成，让基线只降不升。
"""

import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASELINE = os.path.join(_HERE, 'doc_examples_baseline.json')
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from doc_block_scan import scan_all, classify, NOISE_CATEGORIES  # noqa: E402


def _load_baseline():
    with open(_BASELINE, encoding='utf-8') as f:
        return json.load(f)


class TestDocExamplesGate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.baseline = _load_baseline()
        cls.results = scan_all()
        cls.current = {}
        for r in cls.results:
            if r['exc'] is None:
                continue
            cat = classify(r['code'], r['exc'], r['msg'])
            cls.current[(r['file'], r['hash'])] = cat
        cls.base_map = {(e['file'], e['hash']): e['category']
                        for e in cls.baseline['entries']}

    def test_扫描面没有塌掉(self):
        """先确认扫到了东西——扫到 0 个块会让下面所有断言退化成永真式。"""
        self.assertGreater(len(self.results), 900,
                           f'只扫到 {len(self.results)} 个块，提取器可能坏了')
        ok = sum(1 for r in self.results if r['exc'] is None)
        self.assertGreater(ok, 600, f'只有 {ok} 个块能编过，疑似编译器整体退化')

    def test_不许新增ROT(self):
        """核心判据：新写的文档代码块必须能编过。

        反跑实测（2026-08-20）：新建 `docs/_反跑临时.md`，内含一个
        ` ```light ` 块 `定义 甲 等于 1。`（已移除语法）→ **1 failed / 5 passed**，
        本条红并点名 `docs/_反跑临时.md hash=2188db0a955e`；删文件后恢复 6 passed。
        注意只有本条红——正是想要的粒度：新增 ROT 不会污染其余三条判据。
        """
        new_rot = sorted(k for k, cat in self.current.items()
                         if cat == 'ROT' and k not in self.base_map)
        self.assertEqual([], new_rot,
                         '文档里新增了编不过的代码块（前 10 条）：\n' +
                         '\n'.join(f'  {f} hash={h}' for f, h in new_rot[:10]) +
                         '\n修好它，或说明为什么该进基线。')

    def test_不许新增编译器缺陷块(self):
        """COMPILER_BUG 是编译器炸了，新增说明又踩到一个内部缺陷。"""
        new_bugs = sorted(k for k, cat in self.current.items()
                          if cat == 'COMPILER_BUG' and k not in self.base_map)
        self.assertEqual([], new_bugs,
                         '新增编译器内部缺陷（AttributeError/无限分配等）：\n' +
                         '\n'.join(f'  {f} hash={h}' for f, h in new_bugs))

    def test_噪声类总数不许涨(self):
        """REPL/ESCAPED/PSEUDO/ANNOTATED 允许存在但不许变多。"""
        base_n = sum(1 for c in self.base_map.values() if c in NOISE_CATEGORIES)
        cur_n = sum(1 for c in self.current.values() if c in NOISE_CATEGORIES)
        self.assertLessEqual(
            cur_n, base_n,
            f'噪声块从 {base_n} 涨到 {cur_n}：新写的文档又混进了 '
            f'REPL 记录/伪代码/箭头注解/转义污染。非代码块请改用 ```text 标签。')

    def test_基线里修好的条目必须下线(self):
        """防基线虚高（口径 10）：修好了就得从基线删，否则基线不再是真话。

        修好一批后跑 `python tools/ci/gen_doc_examples_baseline.py` 重生成即可。
        """
        fixed = sorted(k for k in self.base_map if k not in self.current)
        self.assertEqual(
            [], fixed,
            f'基线里有 {len(fixed)} 条已经不再失败（前 10 条）：\n' +
            '\n'.join(f'  {f} hash={h}' for f, h in fixed[:10]) +
            '\n请重生成基线，别让它虚高。')

    def test_敌意块被拦在parser外(self):
        """守卫那次 15.5GB 事故不再重演。

        若哪天 `情况 [头, 尾...]` 的无限分配修好了，本条会红——那时应把该哈希
        从 `_HOSTILE_HASHES` 里删掉，让它重新参与真实编译。
        """
        from doc_block_scan import _HOSTILE_HASHES
        self.assertTrue(_HOSTILE_HASHES, '敌意名单被清空了，扫描会重演 OOM 事故')
        skipped = [r for r in self.results if r['exc'] == 'HostileSkipped']
        self.assertEqual(
            len(_HOSTILE_HASHES), len(skipped),
            f'敌意名单 {len(_HOSTILE_HASHES)} 条，实际跳过 {len(skipped)} 条'
            f'——名单里的哈希对不上任何块，说明文档已改，该重新评估')


if __name__ == '__main__':
    unittest.main()
