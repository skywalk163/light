# -*- coding: utf-8 -*-
"""
P0-A 词法确定性切词 —— 复合词压力测试套件（升级计划 §8.4 验收）

语义（§8.4 L218-221）：
    标识符整体最长匹配优先 / 标识符内部不做拆分（仅词首/词尾做关键字判定）

验收标准（两条，缺一不可）：
    1) 复合词压力用例全部通过；
    2) 通过【不依赖逐词白名单】——即把 COMMON_COMPOUND_WORDS 与
       IDENTIFIER_SAFE_KEYWORDS 清空后，压力用例【仍然全部通过】。

实现要点（src/lexer.py）：
    - Lexer._P0A_MERGE_WHOLE：有界「精确整串」合并集合（存整串，不存词头）。
      整串精确匹配 ⇒ `返回` 永不词首吞并（L-027：`返回 斐波那契(...)` 不会
      并成单标识符触发 NameError）。
    - 确定性模式（deterministic=True）下，单字【非运算符】关键字位于标识符
      【内部】时并入标识符，不拆分（`列表设置` 的 `设`、`伪终端会话` 的 `终`）。
      运算符/成员与关系分隔符（_P0A_OP：之/在/于/为/与/加/减…）不受影响。
    - 全部改动由 self._deterministic 门禁，非确定模式保持旧行为（双门禁零回归）。
"""

import sys
import os
import unittest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


def _pairs(tokens):
    """取 (类型名, 值) 序列，去掉末尾 EOF。"""
    return [(t.type.name, t.value) for t in tokens if t.type.name != 'EOF']


class TestP0A复合词压力(unittest.TestCase):
    """§8.4 点名的历史雷区 + 同构复合词"""

    @classmethod
    def setUpClass(cls):
        try:
            import lexer as lexer_mod
            from lexer import Lexer
            cls.lexer_mod = lexer_mod
            cls.Lexer = Lexer
        except ImportError as e:  # pragma: no cover
            raise unittest.SkipTest(f"Lexer 模块不可用: {e}")

    def _lex(self, src, deterministic=True):
        return _pairs(self.Lexer(src, deterministic=deterministic).tokenize())

    # ---- §8.4 点名的 6 个历史雷区 ----
    def test_六雷区_整体成词(self):
        for word in ['导出事件表', '整理模型消息', '返回码', '退出码', '接收参数', '非空块']:
            with self.subTest(word=word):
                self.assertEqual(self._lex(word), [('IDENTIFIER', word)],
                                 f"{word} 应整体成词")

    # ---- FFI / 排序 / 输出 同构词 ----
    def test_同构复合词_整体成词(self):
        for word in ['外部命令', '排序依据', '输出块表']:
            with self.subTest(word=word):
                self.assertEqual(self._lex(word), [('IDENTIFIER', word)],
                                 f"{word} 应整体成词")

    # ---- 验收条件 2：不依赖逐词白名单 ----
    def test_清空白名单后仍整体成词(self):
        """把两张逐词白名单清空，压力词仍须整体成词 —— 证明不依赖白名单。"""
        mod = self.lexer_mod
        orig_ccw, orig_safe = mod.COMMON_COMPOUND_WORDS, mod.IDENTIFIER_SAFE_KEYWORDS
        mod.COMMON_COMPOUND_WORDS = frozenset()
        mod.IDENTIFIER_SAFE_KEYWORDS = frozenset()
        try:
            for word in ['导出事件表', '整理模型消息', '返回码', '退出码',
                         '接收参数', '非空块', '外部命令', '排序依据', '输出块表']:
                with self.subTest(word=word):
                    self.assertEqual(self._lex(word), [('IDENTIFIER', word)],
                                     f"清空白名单后 {word} 仍应整体成词")
        finally:
            mod.COMMON_COMPOUND_WORDS, mod.IDENTIFIER_SAFE_KEYWORDS = orig_ccw, orig_safe

    def test_压力词不在白名单中(self):
        """压力词本身不应登记在 COMMON_COMPOUND_WORDS 内（否则等于打地鼠）。"""
        mod = self.lexer_mod
        for word in ['导出事件表', '整理模型消息', '返回码', '退出码',
                     '接收参数', '非空块', '外部命令', '排序依据', '输出块表']:
            with self.subTest(word=word):
                self.assertNotIn(word, mod.COMMON_COMPOUND_WORDS,
                                 f"{word} 不应靠 COMMON_COMPOUND_WORDS 登记")


class TestP0A无空格表达式仍切分(unittest.TestCase):
    """确定性切词不得破坏本语言大量使用的无空格写法"""

    @classmethod
    def setUpClass(cls):
        try:
            from lexer import Lexer
            cls.Lexer = Lexer
        except ImportError as e:  # pragma: no cover
            raise unittest.SkipTest(f"Lexer 模块不可用: {e}")

    def _lex(self, src):
        return _pairs(self.Lexer(src, deterministic=True).tokenize())

    def test_二元运算符(self):
        self.assertEqual(self._lex('甲加乙'),
                         [('IDENTIFIER', '甲'), ('KEYWORD', '加'), ('IDENTIFIER', '乙')])
        self.assertEqual(self._lex('甲乘乙'),
                         [('IDENTIFIER', '甲'), ('KEYWORD', '乘'), ('IDENTIFIER', '乙')])
        self.assertEqual(self._lex('甲大于乙'),
                         [('IDENTIFIER', '甲'), ('KEYWORD', '大于'), ('IDENTIFIER', '乙')])
        self.assertEqual(self._lex('甲等于乙'),
                         [('IDENTIFIER', '甲'), ('KEYWORD', '等于'), ('IDENTIFIER', '乙')])

    def test_成员与关系分隔符(self):
        self.assertEqual(self._lex('人之构造'),
                         [('IDENTIFIER', '人'), ('KEYWORD', '之'), ('KEYWORD', '构造')])
        self.assertEqual(self._lex('对象之方法'),
                         [('IDENTIFIER', '对象'), ('KEYWORD', '之'), ('IDENTIFIER', '方法')])
        self.assertEqual(self._lex('不在'), [('IDENTIFIER', '不'), ('KEYWORD', '在')])
        self.assertEqual(self._lex('对于'), [('IDENTIFIER', '对'), ('KEYWORD', '于')])
        self.assertEqual(self._lex('甲属于乙'),
                         [('IDENTIFIER', '甲属'), ('KEYWORD', '于'), ('IDENTIFIER', '乙')])
        self.assertEqual(self._lex('如果为真'),
                         [('KEYWORD', '如果'), ('KEYWORD', '为'), ('KEYWORD', '真')])

    def test_语句关键字词首切分(self):
        self.assertEqual(self._lex('如果数小于等于二那么返回一'),
                         [('KEYWORD', '如果'), ('IDENTIFIER', '数'), ('KEYWORD', '小于等于'),
                          ('CHINESE_NUM', 2), ('KEYWORD', '那么'), ('KEYWORD', '返回'),
                          ('CHINESE_NUM', 1)])
        self.assertEqual(self._lex('己姓名'),
                         [('KEYWORD', '己'), ('IDENTIFIER', '姓名')])
        self.assertEqual(self._lex('段落阶乘接收n'),
                         [('KEYWORD', '段落'), ('IDENTIFIER', '阶乘'),
                          ('KEYWORD', '接收'), ('IDENTIFIER', 'n')])

    def test_L027_返回不词首吞并(self):
        """L-027：`返回 斐波那契(...)` 绝不可并成单标识符（否则 NameError）。"""
        got = self._lex('返回 斐波那契(五)')
        vals = [v for _, v in got]
        self.assertIn('返回', vals, "`返回` 必须是独立 KEYWORD")
        self.assertNotIn('返回斐波那契', vals, "`返回` 绝不可吞并后续标识符")
        self.assertEqual(got[0], ('KEYWORD', '返回'))


class TestP0A标识符内部不拆分(unittest.TestCase):
    """§8.4「标识符内部不做拆分」——真实语料中修掉的两处 L-004 家族缺陷"""

    @classmethod
    def setUpClass(cls):
        try:
            from lexer import Lexer
            cls.Lexer = Lexer
        except ImportError as e:  # pragma: no cover
            raise unittest.SkipTest(f"Lexer 模块不可用: {e}")

    def _lex(self, src, deterministic=True):
        return _pairs(self.Lexer(src, deterministic=deterministic).tokenize())

    def test_列表设置_函数调用(self):
        """src/templates/data_analysis/分析.light 实测：`列表设置(...)` 是函数调用。"""
        got = self._lex('列表设置(结果, 内层, 临时)')
        self.assertEqual(got[0], ('IDENTIFIER', '列表设置'),
                         "内部 `设` 不应拆分，否则函数调用被撕成 列表/设/置")
        self.assertEqual(got[1], ('LPAREN', '('))

    def test_伪终端会话_类名(self):
        """lightharness/src/终端.light 实测：`类 伪终端会话:` 的 `终` 被误当关键字。"""
        got = self._lex('类 伪终端会话:')
        self.assertEqual(got, [('KEYWORD', '类'), ('IDENTIFIER', '伪终端会话'), ('COLON', ':')],
                         "内部 `终` 不应拆分，否则类名被撕成 伪/终/端会话")

    def test_门禁_非确定模式保持旧行为(self):
        """全部改动由 _deterministic 门禁：非确定模式仍是旧行为（双门禁零回归）。"""
        # 非确定模式下 `列表设置` 仍按旧逻辑拆分 —— 保证默认路径零影响
        old = self._lex('列表设置', deterministic=False)
        self.assertNotEqual(old, [('IDENTIFIER', '列表设置')],
                            "非确定模式必须保持旧行为")


if __name__ == '__main__':
    unittest.main()
