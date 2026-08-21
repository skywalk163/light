# -*- coding: utf-8 -*-
"""冻结表 ↔ 实现 一致性门禁（v7 版本口径单，阶段 2）。

## 这是全仓第一个真的会打开 `.md` 文件的测试

阶段 2 立项前实测：`tests/` 下**没有任何测试读取过 `docs/`**。27 处 `docs/`
引用全部在注释里当「依据某文档某行」用，断言的都是硬编码字符串。后果就是
`掷`/`断`/`跃`/`现`/`匹`/`例`/`等`/`异` 这一整族「文档承诺了、`src/` 从缺」的
缺陷只能靠人肉在 v7 工单里逐条排查——文档可以任意腐烂而 CI 不报警。

本文件把「冻结表承诺的每个字都必须有落地路径」变成可执行断言。

## 为什么不能直接断言 `文档字集 ⊆ ALL_KEYWORDS`

因为落地有**三种范式**（口径 16 / 18），只有一种进关键字表：

- **范式 B**：进 `keywords.ALL_KEYWORDS` + `lexer._COMPOUND_SAFE_SINGLE_KEYWORDS`，
  成为真关键字。
- **范式 A**：parser 判裸 `IDENTIFIER`，词法层零改动、**故意不进** `ALL_KEYWORDS`
  （`性`/`构`/`新`/`约`/`护`/`私`/`公`/`静`）。
- **范式 C**：`code_generator.builtin_map` 加映射，只在调用点生效（`印`/`写`）。

实测：44 个承诺字里只有 33 个在 `ALL_KEYWORDS`。天真地写 `⊆ ALL_KEYWORDS`
会红 11 条，其中 10 条是**按既定口径故意不进表的**——那种断言会逼着后人把
`护`/`私`/`静` 塞进关键字表，正是口径 16 明确否掉的方向。

所以门禁的形态是：**每个承诺字必须落在 `_落地范式` 登记表里，且该范式对应的
落地位置必须真的能查到**。新增一个承诺字时，登记表里没有它 → 红，逼人做范式
决策，不能静默滑过。

## 「30 字」标题已修正为 44、代码侧死表已删除（2026-08-20）

此前 `l0-core.md` 首行与 `keywords.md` 标题都自称「30 字」而实列 **44** 个字。
这个 30 抄自 `keywords.py:KEYWORDS_L0_CORE`——那张表确实恰好 30 字，但**是另一
组字**（含 `跳 过 接 配 抛 终 之 并 从 导` 等旧世代写法），且 lexer 从不消费它。

三处已一并处理：
- 两份文档标题改为 44，并补 `test_两份冻结表的总数声明都等于实际字数`——此前
  门禁只逐章节比、只比字集，管不到顶部总数，所以这个矛盾长期没红。
- `KEYWORDS_L0_CORE` 整个删掉（零生产消费者 + 与文档是两组字 + 形态误导）。
  `test_代码侧不得再有L0核心镜像表` 守住这个决定，防有人重建镜像表。

L0 字表此后**唯一权威**是 `docs/language/l0-core.md` + `keywords.md`，代码侧
与之的连接只剩本文件的 `_落地范式` 登记表。

## 缺口基线：只有 `常`

`常`（常量修饰符）全 `src/` 零命中（`== '常'` / `'常':` 均无），是唯一真缺口，
与口径 19(6)「六字里只剩 `常` 未落地」一致。基线钉成**精确相等**而非「不超过」：

- 新增缺口 → 红（防腐烂）
- `常` 落地后 → 也红，逼人从基线里删掉它（防基线虚高，口径 10 的教训）

2026-08-20 起两份冻结表在 `常` 那一行写明「保留字，暂未实现」，并由
`test_文档的保留字标注与缺口清单精确一致` 与本基线**双向咬合**：落地了忘删标注、
或标了保留字却没登记 GAP，两种腐烂都会红。

## 反跑（防永真式，口径 17）

**不能用 `git stash push -- src/keywords.py`** —— 这些别名是 31-A…31-G 各单
分别落地的，早已在 HEAD 里，本单没改 `keywords.py`，stash 会直接回
`No local changes to save`，反跑退化成「又跑了一遍正向」。初版就是这么写的，
实测 10 passed / 10 passed，等于没反跑。

有效反跑是**临时打断三条落地路径各一处**，确认对应判据会红：

- 范式 B：`keywords.py` 的 `'掷'` 改名 → `test_范式B承诺字确实在ALL_KEYWORDS` 红
- 范式 C：`code_generator.py` 的 `'写'` 改名 → `test_范式C承诺字确实在builtin_map` 红
- 范式 A：`parser_expr.py` 的 `tok.value == '新'` 改写成 `in ('新',)`
  → `test_范式A承诺字确实在parser里` 红

实测：只断 B+C 得 **2 failed / 8 passed**；三条全断得 **3 failed / 7 passed**。
改完全部还原，正向 10 passed。

**已知弱点（不掩盖）**：范式 A 的判据是字符串查 `== '字'`，属形态敏感——
把 parser 里的等值判断重构成 `in (...)` 会让它假红（上面第三条反跑正是利用
这一点）。这条判据只能证明「parser 里提到了这个字」，证明不了语义正确；范式 A
各字的真实行为由 `test_l0_char_aliases_paradigm_ac.py` 等专项用例守。

## 第一次跑就抓到的真缺陷

本门禁首次运行即抓到 `docs/language/l0-core.md` 的 `## 修饰（4字）` 实际列了
5 个字（`常护私公静`）。已改成 `（5字）`。这类「章节声明与表格不符」正是纯人肉
维护无法长期兜住、而机器一眼就看见的东西。

"""

import os
import re
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_ROOT, 'src'), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from keywords import ALL_KEYWORDS  # noqa: E402
import keywords as _keywords_mod  # noqa: E402

_L0_CORE_MD = os.path.join(_ROOT, 'docs', 'language', 'l0-core.md')
_KEYWORDS_MD = os.path.join(_ROOT, 'docs', 'language', 'keywords.md')

# 范式登记表：承诺字 → 落地范式。见模块文档串。
# 'B' = 进 ALL_KEYWORDS；'A' = parser 判裸 IDENTIFIER；'C' = builtin_map；
# 'GAP' = 尚未落地（当前只允许 `常`）。
_落地范式 = {
    # 范式 B —— 真关键字
    '设': 'B', '为': 'B', '若': 'B', '则': 'B', '否': 'B', '当': 'B', '遍': 'B',
    '断': 'B', '跃': 'B', '段': 'B', '返': 'B', '类': 'B', '承': 'B',
    '己': 'B', '父': 'B', '现': 'B', '引': 'B', '出': 'B', '自': 'B',
    '且': 'B', '或': 'B', '非': 'B', '真': 'B', '假': 'B', '空': 'B',
    '试': 'B', '捕': 'B', '掷': 'B', '匹': 'B', '例': 'B',
    '异': 'B', '等': 'B', '是': 'B',
    # v7 单 33：`常`（常量修饰符）落地，范式 B。原为本表唯一 'GAP'。
    # 形态：`常 设 名 为 值。` 前缀修饰符（`常量` 同义双字写法一并收）。
    '常': 'B',
    # 范式 A —— parser 判裸 IDENTIFIER，故意不进关键字表（口径 16/18）
    '性': 'A', '构': 'A', '新': 'A', '约': 'A',
    '护': 'A', '私': 'A', '公': 'A', '静': 'A',
    # 范式 C —— builtin_map，只在调用点生效（口径 18）
    '印': 'C', '写': 'C',
}

# 缺口基线：精确相等，不是「不超过」。
# v7 单 33 起为**空集** —— 44 个承诺字全部落地。新增缺口会立刻红。
_缺口基线 = set()

# 范式 A 的落地位置（parser 两个文件都要看——`新` 在 parser_expr.py 而非 stmt）
_范式A源文件 = [
    os.path.join(_ROOT, 'src', 'parser_stmt.py'),
    os.path.join(_ROOT, 'src', 'parser_expr.py'),
]


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _parse_l0_core_md():
    """解析 l0-core.md，返回 (声明总数, [(章节名, 声明字数, [字...])])。"""
    text = _read(_L0_CORE_MD)
    m = re.search(r'包含 (\d+) 个单字关键字', text)
    declared_total = int(m.group(1)) if m else None

    sections = []
    current = None
    for line in text.splitlines():
        hm = re.match(r'^## (.+)（(\d+)字）\s*$', line)
        if hm:
            current = (hm.group(1), int(hm.group(2)), [])
            sections.append(current)
            continue
        if current is None:
            continue
        rm = re.match(r'^\| `(.)` \| (.+?) \|\s*$', line)
        if rm:
            current[2].append(rm.group(1))
    return declared_total, sections


def _parse_keywords_md():
    """解析 keywords.md 的 L0 表，返回其承诺字集合。"""
    text = _read(_KEYWORDS_MD)
    # 只取 `## v4.0 L0 核心关键字` 到下一个 `## ` 之间
    m = re.search(r'^## v4\.0 L0 核心关键字.*?$(.*?)^## ', text,
                  re.MULTILINE | re.DOTALL)
    body = m.group(1) if m else ''
    chars = set()
    for line in body.splitlines():
        if not line.startswith('|') or line.startswith('|---'):
            continue
        cols = [c.strip() for c in line.strip('|').split('|')]
        if len(cols) < 2 or cols[0] in ('类别',):
            continue
        for tok in re.findall(r'`(.+?)`', cols[1]):
            if len(tok) == 1:
                chars.add(tok)
    return chars


def _keywords_md_declared_total():
    """取 keywords.md 的 `## v4.0 L0 核心关键字（N字）` 里的 N。"""
    m = re.search(r'^## v4\.0 L0 核心关键字（(\d+)字）', _read(_KEYWORDS_MD),
                  re.MULTILINE)
    return int(m.group(1)) if m else None


# 文档里标注「尚未落地」的统一措辞。改这个串等于改口径，两份表要一起改。
_保留字标记 = '保留字'


def _l0_core_md_保留字():
    """返回 l0-core.md 里语义栏带 `保留字` 标记的字集合。"""
    chars = set()
    for line in _read(_L0_CORE_MD).splitlines():
        m = re.match(r'^\| `(.)` \| (.+?) \|\s*$', line)
        if m and _保留字标记 in m.group(2):
            chars.add(m.group(1))
    return chars




class TestSpecDocsSync(unittest.TestCase):

    # ---- 一、文档本身可解析、且自洽 -------------------------------------

    def test_冻结表可被解析(self):
        """解析器不许空转——空转会让下面所有断言退化成永真式。"""
        declared_total, sections = _parse_l0_core_md()
        self.assertIsNotNone(declared_total, '首行「包含 N 个单字关键字」不见了')
        self.assertGreaterEqual(len(sections), 10, f'只解析到 {len(sections)} 个章节')
        chars = [c for _, _, cs in sections for c in cs]
        self.assertGreaterEqual(len(chars), 40, f'只解析到 {len(chars)} 个字')
        for c in chars:
            self.assertEqual(1, len(c), f'{c!r} 不是单字')

    def test_章节声明字数与表格行数一致(self):
        """`## 修饰（4字）` 下面列 5 行 —— 这类错必须由机器抓。"""
        _, sections = _parse_l0_core_md()
        problems = [
            f'「{name}（{declared}字）」实际列了 {len(cs)} 个：{"".join(cs)}'
            for name, declared, cs in sections if declared != len(cs)
        ]
        self.assertEqual([], problems, '章节字数声明与表格不符：\n' + '\n'.join(problems))

    def test_两份冻结表的总数声明都等于实际字数(self):
        """两份表的**标题总数**必须等于表格实际字数。

        这条是补漏：`test_章节声明字数与表格行数一致` 只逐章节比，管不到顶部的
        总数；`test_两份冻结表字集一致` 只比字集，也管不到数字。于是两份表长期
        自称「30 字」而实列 44 个字，谁也没红——正是外部使用者按「30 字核心」
        去理解、结果撞上第 31~44 个字的来源。

        修正记录（2026-08-20）：`l0-core.md` 首行与 `keywords.md` 标题的 30
        均改为 44。那个 30 疑似是从 `keywords.py:KEYWORDS_L0_CORE` 抄来的——
        那张表确实恰好 30 字，但**是另一组字**（见
        `test_代码侧L0核心表仍是30字`）。
        """
        declared_total, sections = _parse_l0_core_md()
        actual = [c for _, _, cs in sections for c in cs]
        self.assertEqual(
            len(actual), declared_total,
            f'l0-core.md 首行声明 {declared_total} 字，表格实列 {len(actual)} 个：'
            f'{"".join(actual)}')
        self.assertEqual(
            len(actual), sum(d for _, d, _ in sections),
            'l0-core.md 各章节声明字数之和与实际字数不符')

        kw_declared = _keywords_md_declared_total()
        self.assertIsNotNone(kw_declared,
                             'keywords.md 的「## v4.0 L0 核心关键字（N字）」标题不见了')
        self.assertEqual(
            len(_parse_keywords_md()), kw_declared,
            f'keywords.md 标题声明 {kw_declared} 字，表格实列 '
            f'{len(_parse_keywords_md())} 个')


    def test_两份冻结表字集一致(self):
        """l0-core.md 与 keywords.md 是同一份承诺的两种排版，字集必须相等。"""
        _, sections = _parse_l0_core_md()
        a = {c for _, _, cs in sections for c in cs}
        b = _parse_keywords_md()
        self.assertGreaterEqual(len(b), 40, 'keywords.md 的 L0 表解析空转')
        self.assertEqual(a, b,
                         f'只在 l0-core: {"".join(sorted(a - b))}；'
                         f'只在 keywords.md: {"".join(sorted(b - a))}')

    # ---- 二、每个承诺字都有落地路径 -------------------------------------

    def test_每个承诺字都已登记范式(self):
        """新增承诺字必须显式做范式决策，不能静默滑过。"""
        _, sections = _parse_l0_core_md()
        doc_chars = {c for _, _, cs in sections for c in cs}
        unregistered = doc_chars - set(_落地范式)
        self.assertEqual(set(), unregistered,
                         f'冻结表新增了未登记范式的字：{"".join(sorted(unregistered))}'
                         f'——请按口径 16/18 选 A/B/C 并登记，别直接删本断言')
        stale = set(_落地范式) - doc_chars
        self.assertEqual(set(), stale,
                         f'登记表里有冻结表已不再承诺的字：{"".join(sorted(stale))}')

    def test_范式B承诺字确实在ALL_KEYWORDS(self):
        missing = sorted(c for c, p in _落地范式.items()
                         if p == 'B' and c not in ALL_KEYWORDS)
        self.assertEqual([], missing,
                         f'登记为范式 B 但不在 ALL_KEYWORDS：{"".join(missing)}')

    def test_范式C承诺字确实在builtin_map(self):
        from code_generator import PythonCodeGenerator
        bm = PythonCodeGenerator().builtin_map
        missing = sorted(c for c, p in _落地范式.items()
                         if p == 'C' and c not in bm)
        self.assertEqual([], missing,
                         f'登记为范式 C 但不在 builtin_map：{"".join(missing)}')

    def test_范式A承诺字确实在parser里(self):
        """范式 A 靠 parser 判裸 IDENTIFIER，查 `value == '字'` 形态。"""
        sources = ''.join(_read(p) for p in _范式A源文件)
        missing = sorted(c for c, p in _落地范式.items()
                         if p == 'A' and f"== '{c}'" not in sources)
        self.assertEqual([], missing,
                         f'登记为范式 A 但 parser 里查不到判定：{"".join(missing)}')

    def test_范式A承诺字确实不在ALL_KEYWORDS(self):
        """反向守卫：范式 A 是**故意**不进表的（口径 16），把这个决定钉住。

        没有这条，后人会「顺手」把 `护`/`私`/`静` 塞进关键字表——那是口径 16
        用「全仓词首 224 处，进表要动最长匹配」明确否掉的方向。
        """
        leaked = sorted(c for c, p in _落地范式.items()
                        if p == 'A' and c in ALL_KEYWORDS)
        self.assertEqual([], leaked,
                         f'范式 A 的字漏进了 ALL_KEYWORDS：{"".join(leaked)}'
                         f'——若确要改范式，先过全仓 token A/B（口径 15）')

    def test_文档的保留字标注与缺口清单精确一致(self):
        """文档说「暂未实现」的字，必须正好是登记表里的 GAP 字。

        双向咬合，堵住两种腐烂：
        - 落地了却忘了删文档标注 → 文档继续骗人说「暂未实现」
        - 标了保留字却没登记成 GAP → 缺口不在基线里，无人跟踪

        当前唯一的保留字是 `常`（常量修饰符），全 `src/` 零命中。
        """
        gaps = {c for c, p in _落地范式.items() if p == 'GAP'}
        marked = _l0_core_md_保留字()
        self.assertEqual(
            gaps, marked,
            f'登记为 GAP 的：{"".join(sorted(gaps))}；'
            f'l0-core.md 标了「{_保留字标记}」的：{"".join(sorted(marked))}。'
            f'两边必须一致——落地了就把标注删掉，新增缺口就把标注加上。')
        # keywords.md 也要带同样的标注（两份表是同一份承诺的两种排版）
        kw_text = _read(_KEYWORDS_MD)
        for c in gaps:
            self.assertIn(
                _保留字标记, kw_text,
                f'keywords.md 没有标注 {c} 是{_保留字标记}')

    def test_缺口清单精确等于基线(self):

        """精确相等：新增缺口会红，`常` 落地后也会红（逼人下线基线条目）。"""
        gaps = {c for c, p in _落地范式.items() if p == 'GAP'}
        self.assertEqual(_缺口基线, gaps,
                         f'缺口清单变了：当前 {"".join(sorted(gaps))}，'
                         f'基线 {"".join(sorted(_缺口基线))}。'
                         f'若某字已落地，请改登记表并从 _缺口基线 里删掉它')
        # 缺口字确实在全 src/ 查不到落地痕迹——否则这条基线是虚高的
        sources = ''.join(_read(p) for p in _范式A源文件)
        for c in gaps:
            self.assertNotIn(f"== '{c}'", sources,
                             f'{c} 其实已在 parser 落地，基线虚高')
            self.assertNotIn(c, ALL_KEYWORDS, f'{c} 其实已在 ALL_KEYWORDS')

    # ---- 三、守住「代码侧不再有规范镜像表」这个决定 -----------------------

    def test_代码侧不得再有L0核心镜像表(self):
        """`keywords.KEYWORDS_L0_CORE` 已删除，不许重建。

        它曾是一张自称「冻结 30 字」却零生产消费者的表，且那 30 字与
        `docs/language/l0-core.md` 的 44 字**是两组字**——两份文档标题里那个错的
        「30」正是从它抄过去的。删除理由完整写在 `src/keywords.py` 文件头。

        为什么要专门加一条守卫：`keywords.py` 里其余每张表都是**真关键字集**，
        再放一张「规范镜像表」进去，读者必然误以为它也进 lexer；而 44 字里有 8 个
        是范式 A（故意不进关键字表）、2 个范式 C、1 个尚未落地。规范条目与关键字
        集必须分家——规范归 `docs/`，关键字集归本文件。
        """
        self.assertFalse(
            hasattr(_keywords_mod, 'KEYWORDS_L0_CORE'),
            'keywords.py 又出现了 KEYWORDS_L0_CORE。L0 字表的权威是 '
            'docs/language/l0-core.md；要在代码里表达 L0 语义请改 _落地范式 '
            '登记表，别重建镜像表。')

    def test_L0承诺字里的范式B部分都是真关键字(self):
        """删掉镜像表后，「文档 ↔ 代码」的唯一连接就是 `_落地范式` 登记表。

        本条是那条连接的完整性冒烟：44 字里登记为 B 的必须全都在 `ALL_KEYWORDS`
        且数量对得上，防止登记表被整体注水成空壳（例如有人把所有字都改成 'A'
        来让门禁变绿）。
        """
        _, sections = _parse_l0_core_md()
        doc_chars = {c for _, _, cs in sections for c in cs}
        b_chars = {c for c, p in _落地范式.items() if p == 'B'}
        self.assertTrue(b_chars <= doc_chars, 'B 组里有文档没承诺的字')
        self.assertTrue(b_chars <= ALL_KEYWORDS, 'B 组里有不在 ALL_KEYWORDS 的字')
        self.assertGreaterEqual(
            len(b_chars), 30,
            f'范式 B 只剩 {len(b_chars)} 个字（应约 33）——登记表疑似被注水')



if __name__ == '__main__':
    unittest.main()
