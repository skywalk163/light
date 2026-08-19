"""v7 单 31-D：`_skip_compound_safe_and_match` 返回值失配的正面修复。

## 缺陷

`src/lexer.py:_match_keyword` 的契约写在自己的文档串里（`:1021-1023`）：

    (匹配到的关键字, 匹配长度) 或 (None, 0)
    匹配长度恒等于 len(匹配到的关键字)，且关键字恒等于 text[pos:pos+长度]。

`_skip_compound_safe_and_match` 命中 compound-safe 单字后会递归到 `pos+1`。旧实现在
递归找到关键字（且不是 `之`）时**把内层的 `(kw, l)` 原样上报**——`kw` 取自
`text[pos+k : pos+k+l]`，`l` 也以 `pos+k` 为基准，而六处调用方按 **`pos`** 消费 `l` 个
字符、同时把 `kw` 的字面 emit 出去。于是 `pos` 处那个字被丢掉、内层关键字被吐两次：

    等于空那么   → 等于 那么 么      （`空` 消失，`么` 凭空出现）
    种类等于     → 种 等于 于
    索引等于     → 索 等于 于
    除类型错误   → 类型 型错误      （`除` 消失，`型` 凭空出现）
    对于 项 之 列表 → 于 于 项 之 列表 （`对` 消失，`于` 凭空出现）
    10的幂       → 幂 幂

上面每一条都经过「HEAD:src vs 工作树」双跑核对（见下「反跑」一节），**不是推演**。
反过来，`年级常模`、`忽略大小写否则` 这类串**不会**触发本缺陷——`常`/`写` 至今不在
关键字表里（口径 15/16 待补清单），失配的必要条件是 pos 处那个字本身是 compound-safe
单字关键字。谁要往这里补例子，先用 `.scratch/cand31d.py` 那种双跑筛一遍。

改前实测（全仓 37255 个 `.light`）：**6874 处契约违约 / 2192 文件 / 387 种形态**；修复后
同一把尺子归零。⚠️ 这是**函数契约层**的违约数，**不等于 6874 处产物被写坏**——绝大多数
违约点被调用方的 compound-safe 跳过逻辑救回。真正把 token 流写坏的是其中 **31 个文件**，
且**落在自举链上**（`antlrparser/self_hosted/*`、`bootstrap/release/stdlib/*`）——
编译器读自己的源码时就在丢字。这两个数不能混用。


## 修复

`:1104` 起：内层命中但不是 `之` 时**返回 `(None, 0)`**，语义是「pos 处不做关键字承诺」。

三种可能的语义里选了这一种：

- `return kw, l`（旧）——失配本体，见上。
- `return candidate, length`——即断言 pos 处这颗 compound-safe 单字就是词。单 B 试过，
  会让 `除`/`幂`/`于` 作为运算符浮现，把 `去除空格` 之类整词切碎，全仓 A/B 实测
  100+ 处漂移、42 文件受影响，故当年收窄到只认 `之`。
- `return None, 0`（本单）——「这颗单字后面还接着关键字料，别让它在这里成词」，正是
  compound-safe 这套启发式本来要表达的意思；契约由 `kw is None` 平凡满足。下游行为
  不变的原因是：调用方拿到 None 后把 pos 处的字当标识符料继续扫，扫到内层那个位置时
  会**在正确的 pos 上**重新问一次，得到诚实的结果。

全仓 A/B（`HEAD:src` vs 工作树，方向性判据：`IDENTIFIER`/`KEYWORD` 的字面必须是源文本的
子序列，不满足即该侧凭空造字）：**修好 31 文件、回退 0 文件、仅切法变化 2 文件**。

## 反跑（判据不是永真式的证据）

把修复抽掉、用 `git show HEAD:src/*.py` 物化的旧 lexer 跑同一批判据：
`SOURCES` 里 **8/12** 条报契约违约、**7/12** 条造字。更强的一跑是
`git stash push -- src/lexer.py` 后让**本文件整体**对着旧 lexer 跑：
**22 failed / 5 passed**（5 个 pass 正是 `去除空格`/`阶乘`/`自之姓名` 那三条
「必须不动」的保留守卫），恢复后 12 passed。
`对于`→`于于`、`是否为空`→`为为为空`、`等于空那么`→`等于那么么`、`种类等于`→`种等于于`、
`索引等于`→`索等于于`、`除类型错误`→`类型型错误`、`10的幂`→`幂幂`
都在旧 lexer 下**凭空造字**，改后才忠实。


## 判据为什么用「子序列」而不是「两侧 visible 相等」

失配的症状是「丢一个字 **+** 多一份后随关键字的副本」，`len()` 和字符集合对
`那么`+`么`、`于`+`于` 这种形态都是瞎的；`visible(改前) != visible(改后)` 只能说明
两侧不同，**看不出哪一侧在造字**。只有「token 字面必须是源文本的子序列」这条
带方向：不满足的那一侧就是凭空造字的那一侧。

## 本文件不断言什么

- 不断言 `对于` 应该切成**一个** token。改后是 `对`(IDENTIFIER) + `于`(KEYWORD)，
  本文件只断言它**忠实**（两个 token 的字面拼起来仍是源文本的子序列），不断言
  `对于` 成词——那属于口径 9「`对于/在` 推导式无文档承诺」，不在本单范围。
- 不断言 `是否为空` 应该切成**一个** token。改后是 `是否`(IDENTIFIER) +
  `为`(KEYWORD) + `空`(KEYWORD)，本文件只断言 `是否` 不再被压成 `为为`。
- 不断言 `除类型错误` 应该切成一个标识符。改后是 `除` + `类型` + `错误` 三个 token；
  `除类型错误` 在 `断言工具.light` 里本就是已损坏的生成产物里的名字，怎么切都编不过，
  本文件只要求它不丢字。
"""

import os

import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from lexer import Lexer  # noqa: E402


def _named(src):
    """只取带字面的 token（IDENTIFIER/KEYWORD），(类型, 值) 序列。"""
    return [(t.type.name, str(t.value)) for t in Lexer(src).tokenize()
            if t.type.name in ('IDENTIFIER', 'KEYWORD')]


def _visible(src):
    return ''.join(v for _, v in _named(src))


def _is_subseq(small, big):
    it = iter(big)
    return all(ch in it for ch in small)


class TestMatchKeywordContract(unittest.TestCase):
    """契约直测：回报的关键字必须恒等于 text[pos:pos+长度]。

    这是本单的核心判据，且**不依赖任何一处具体切法**——即使将来切法调整，
    「回报的字面必须来自 pos 处」这条也不该松动。
    """

    SOURCES = (
        '设 甲 为 1。\n若 甲 等于空那么：\n    印 1。\n',
        '定义 种类等于 《取关键字类型》。\n',
        '定义 索引等于 1。\n',
        '捕 除类型错误：\n    印 1。\n',
        '设 甲 为 10的幂。\n',
        '印 自之姓名。\n',
        '设 甲 为 去除空格。\n',
        '设 甲 为 是否为空。\n',
        '对于 项 之 列表：\n    印 项。\n',
        '设 甲 为 阶乘。\n',
        '设 年级常模 为 1。\n',
        '设 合约乘数 为 1。\n',
    )

    def test_全部来源零违约(self):

        for src in self.SOURCES:
            lx = Lexer(src)
            bad = []
            for pos in range(len(src)):
                kw, length = lx._match_keyword(src, pos)
                if kw and kw != src[pos:pos + length]:
                    bad.append((pos, src[pos], kw, length))
            with self.subTest(src=src[:24]):
                self.assertEqual(
                    bad, [],
                    '%r 上 _match_keyword 回报的字面不来自 pos：%s' % (src[:24], bad[:5]))


class TestNoFabricatedCharacters(unittest.TestCase):
    """token 流不得凭空造字：字面必须是源文本的子序列。

    失配的可见症状不是「少了一个字」而是「少一个字 + 多一个后随关键字的副本」，
    所以判据用子序列而不是长度或集合——后两者对 `那么`+`么` 这种形态是瞎的。
    """

    SOURCES = TestMatchKeywordContract.SOURCES

    def test_字面是源文本子序列(self):
        for src in self.SOURCES:
            with self.subTest(src=src[:24]):
                self.assertTrue(
                    _is_subseq(_visible(src), src),
                    '%r 的 token 字面 %r 不是源文本的子序列（有凭空造字）'
                    % (src[:24], _visible(src)))


class TestDropSignaturesFixed(unittest.TestCase):
    """逐个钉住语料里真实存在过的损坏形态（改前会写坏，改后必须正确）。

    这些串都取自 A/B 抓到的 31 个文件，不是构造的合成例：
    `等于空那么` 出自 antlrparser/self_hosted/interpreter.light，
    `种类等于` 出自 tokenizer.light，`索引等于` 出自 test/sample_controlflow.light，
    `除类型错误` 出自 bootstrap/release/stdlib/断言工具.light，
    `对于 …` 出自 bootstrap/release/stdlib/CSV读写器.light，
    `是否为…` 出自 bootstrap/release/stdlib/字符串常量.light、系统接口.light，
    `10的幂` 出自 积木库/blocks{,_v4}/数学/10的幂.light。

    **每条都用「HEAD:src 反跑」核对过会红**——加新条目前先跑一遍双跑筛，
    别把改前改后一致的串写进来（`忽略大小写否则`、`年级常模` 就是这样的伪例，
    `写`/`常` 不在关键字表里，根本触发不了失配）。
    """


    def test_等于空那么(self):
        named = _named('若 甲 等于空那么：\n    印 1。\n')
        self.assertIn(('KEYWORD', '等于'), named)
        self.assertIn(('IDENTIFIER', '空'), named)
        self.assertIn(('KEYWORD', '那么'), named)
        # 旧缺陷的签名：`那么` 后紧跟一个凭空的 IDENTIFIER('么')
        self.assertNotIn(('IDENTIFIER', '么'), named)

    def test_种类等于(self):
        named = _named('定义 种类等于 《取关键字类型》。\n')
        self.assertIn(('IDENTIFIER', '种类'), named)
        self.assertIn(('KEYWORD', '等于'), named)
        self.assertNotIn(('IDENTIFIER', '种'), named)
        # 旧缺陷把 `类` 吃掉、把 `于` 吐两次
        self.assertNotIn(('KEYWORD', '于'), named)

    def test_索引等于(self):
        named = _named('定义 索引等于 1。\n')
        self.assertIn(('IDENTIFIER', '索引'), named)
        self.assertIn(('KEYWORD', '等于'), named)
        self.assertNotIn(('IDENTIFIER', '索'), named)

    def test_除类型错误(self):
        """断言工具.light 的真实形态：改前 `捕 类型 型错误`（`除` 丢、`型` 凭空）。"""
        named = _named('捕 除类型错误：\n    印 1。\n')
        self.assertIn(('IDENTIFIER', '除'), named)
        self.assertIn(('KEYWORD', '类型'), named)
        self.assertIn(('IDENTIFIER', '错误'), named)
        # 旧行为的签名：`除` 整字消失、`类型` 后粘出一个凭空的 `型错误`
        self.assertNotIn(('IDENTIFIER', '型错误'), named)

    def test_对于(self):
        """CSV读写器.light 的真实形态：改前 `于 于 项`（`对` 丢、`于` 吐两次）。

        只断言忠实性，**不**断言 `对于` 成词——那属口径 9，不在本单范围。
        """
        named = _named('对于 项 之 列表：\n    印 项。\n')
        self.assertIn(('IDENTIFIER', '对'), named)
        self.assertEqual(sum(1 for _, v in named if v == '于'), 1,
                         '`于` 出现次数应与源文本一致，改前是 2 次（凭空一份）')

    def test_是否为空(self):
        """字符串常量.light/系统接口.light 的真实形态：改前 `为 为 为 空`。

        只断言 `是否` 不被压成 `为为`，不断言 `是否为空` 成词。
        """
        named = _named('设 甲 为 是否为空。\n')
        self.assertIn(('IDENTIFIER', '是否'), named)
        self.assertEqual(sum(1 for _, v in named if v == '为'), 2,
                         '源文本只有 2 个 `为`（`设 甲 为` 与 `是否为空`），改前是 4 个')

    def test_10的幂(self):
        """积木库/数学/10的幂.light 的真实形态：改前 `幂 幂`（`的` 丢、`幂` 吐两次）。"""
        src = '设 甲 为 10的幂。\n'
        named = _named(src)
        # 改后 `的幂` 整体成一个标识符；改前是 KEYWORD(幂) + KEYWORD(幂)
        self.assertIn(('IDENTIFIER', '的幂'), named)
        self.assertNotIn(('KEYWORD', '幂'), named)
        self.assertEqual(_visible(src).count('幂'), 1,
                         '`幂` 在 token 字面里只应出现 1 次，改前是 2 次（凭空一份）')


class TestPreservedSegmentations(unittest.TestCase):

    """必须一字不动的既有切法。

    这一组是本单的**回退守卫**：单 B 的文档串明确警告过，动这处失配时最容易
    连带改掉 `去除空格` 这类「compound-safe 单字被整词吸收」的历史切法。
    """

    def test_去除空格仍是一个标识符(self):
        self.assertIn(('IDENTIFIER', '去除空格'), _named('设 甲 为 去除空格。\n'))

    def test_阶乘仍是一个标识符(self):
        self.assertIn(('IDENTIFIER', '阶乘'), _named('设 甲 为 阶乘。\n'))

    def test_自之X_仍是单B修好的样子(self):
        # 单 B 的成果：`自之姓名` → KEYWORD(自) KEYWORD(之) IDENTIFIER(姓名)
        named = _named('印 自之姓名。\n')
        self.assertIn(('KEYWORD', '自'), named)
        self.assertIn(('KEYWORD', '之'), named)
        self.assertIn(('IDENTIFIER', '姓名'), named)
        # 单 B 修掉的旧形态是 KEYWORD(之) 出现两次
        self.assertEqual(sum(1 for k, v in named if v == '之'), 1)


if __name__ == '__main__':
    unittest.main()
