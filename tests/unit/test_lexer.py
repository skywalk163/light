# -*- coding: utf-8 -*-
"""
光明词法分析器单元测试

测试 src/lexer.py 的词法分析功能
"""

import sys
import os
import unittest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


class TestLexer(unittest.TestCase):
    """词法分析器测试"""

    @classmethod
    def setUpClass(cls):
        try:
            from lexer import Lexer
            from tokens import TokenType
            cls.Lexer = Lexer
            cls.TokenType = TokenType
        except ImportError as e:
            raise unittest.SkipTest(f"Lexer 模块不可用: {e}")

    def test_simple_tokenize(self):
        """测试简单语句词法分析"""
        lexer = self.Lexer('设甲为三。')
        tokens = lexer.tokenize()
        self.assertGreater(len(tokens), 0)
        # 验证生成了预期的 token 类型
        token_types = [t.type for t in tokens]
        self.assertIn(self.TokenType.KEYWORD, token_types)
        self.assertIn(self.TokenType.IDENTIFIER, token_types)
        self.assertIn(self.TokenType.CHINESE_NUM, token_types)
        # 验证关键字值
        token_values = [t.value for t in tokens if t.type == self.TokenType.KEYWORD]
        self.assertIn('设', token_values)
        self.assertIn('为', token_values)

    def test_number_literal(self):
        """测试数字字面量"""
        lexer = self.Lexer('打印 123')
        tokens = lexer.tokenize()
        number_tokens = [t for t in tokens if t.type == self.TokenType.NUMBER]
        self.assertGreater(len(number_tokens), 0)
        self.assertEqual(number_tokens[0].value, 123)

    def test_string_literal(self):
        """测试字符串字面量"""
        lexer = self.Lexer('打印"你好"。')
        tokens = lexer.tokenize()
        string_tokens = [t for t in tokens if t.type == self.TokenType.STRING]
        self.assertGreater(len(string_tokens), 0)
        self.assertIn('你好', [t.value for t in string_tokens])

    def test_chinese_number(self):
        """测试中文数字"""
        lexer = self.Lexer('三加五')
        tokens = lexer.tokenize()
        cn_num_tokens = [t for t in tokens if t.type == self.TokenType.CHINESE_NUM]
        self.assertEqual(len(cn_num_tokens), 2)

    def _sig(self, source):
        """把源码转成 (类型名, 值) 序列，去掉 EOF/NEWLINE/INDENT/DEDENT 噪声"""
        skip = {'EOF', 'NEWLINE', 'INDENT', 'DEDENT'}
        return [
            (t.type.name, t.value)
            for t in self.Lexer(source).tokenize()
            if t.type.name not in skip
        ]

    # ---- v7 新单 A：中文数词前缀切分收窄 ----
    # 原实现「只要标识符以中文数词开头就切」，把 百分位数 切成
    # CHINESE_NUM(100) + IDENTIFIER(分位数)。这类流往往还能解析通过，
    # 属静默错译。收窄后：仅当数词之后紧跟关键字才切。

    def test_number_prefix_not_split_when_rest_is_not_keyword(self):
        """数词前缀后面不是关键字 → 整体作为标识符，不拆分"""
        for word in ('百分位数', '万能钥匙', '四元数', '二叉树节点',
                     '千粒重', '十六进制数字', '二氧化碳吸收', '五数汇总'):
            with self.subTest(word=word):
                self.assertEqual(self._sig(word), [('IDENTIFIER', word)])

    def test_number_prefix_still_split_when_rest_is_keyword(self):
        """数词前缀后面紧跟关键字 → 仍然拆分（保住原有行为）"""
        sig = self._sig('九十那么大')
        self.assertEqual(sig[0], ('CHINESE_NUM', 90))
        self.assertEqual(sig[1], ('KEYWORD', '那么'))

    def test_whole_identifier_is_number_unaffected(self):
        """整串都是中文数字 → 仍走整串分支，收窄不影响"""
        self.assertEqual(self._sig('一百零一'), [('CHINESE_NUM', 101)])
        self.assertEqual(self._sig('三点一四'), [('CHINESE_NUM', 3.14)])
        self.assertEqual(self._sig('九十九'), [('CHINESE_NUM', 99)])

    def test_number_prefix_word_in_assignment(self):
        """静默错译的原始现场：设 甲 为 百分位数"""
        self.assertEqual(
            self._sig('设 甲 为 百分位数'),
            [('KEYWORD', '设'), ('IDENTIFIER', '甲'),
             ('KEYWORD', '为'), ('IDENTIFIER', '百分位数')],
        )

    def test_number_prefix_word_keeps_embedded_keyword(self):
        """不切数词前缀时，仍须让后续常规流程识别词中关键字

        反例守护：若在数词分支里直接整块吐出标识符并 continue，
        就会绕过嵌入关键字扫描，把 二元运算符表等于甲 吞成一个标识符。
        """
        sig = self._sig('二元运算符表等于甲')
        self.assertEqual(sig[0], ('IDENTIFIER', '二元运算符表'))
        self.assertIn(('KEYWORD', '等于'), sig)

    # ---- v7 新单 C：r"…" 原始字符串前缀 ----
    # 原实现把 r 切成 IDENTIFIER(r)，紧跟字符串独立成 STRING，产物 r(...) 调用，
    # 运行期 NameError。收窄新增：字母紧贴引号才当前缀，且施加 raw 语义。

    def test_raw_string_prefix_double_quote(self):
        """r"…" 整体是一个 STRING，不再切出 IDENTIFIER(r)"""
        sig = self._sig('设 甲 为 r"\\d{4}"')
        self.assertNotIn(('IDENTIFIER', 'r'), sig)
        strings = [v for (typ, v) in sig if typ == 'STRING']
        self.assertEqual(strings, ['\\d{4}'])   # raw：反斜杠原样保留

    def test_raw_string_prefix_single_quote_and_R(self):
        for src, want in [("设 甲 为 r'\\d+'", '\\d+'),
                          ('设 甲 为 R"\\w*"', '\\w*')]:
            with self.subTest(src=src):
                sig = self._sig(src)
                self.assertNotIn(('IDENTIFIER', 'r'), sig)
                self.assertNotIn(('IDENTIFIER', 'R'), sig)
                self.assertIn(('STRING', want), sig)

    def test_raw_string_does_not_translate_escapes(self):
        """raw 语义：\\n \\r 等不翻译，逐字保留"""
        sig = self._sig('设 甲 为 r"a\\nb"')
        self.assertIn(('STRING', 'a\\nb'), sig)          # 未翻译
        self.assertNotIn(('STRING', 'a\nb'), sig)

    def test_plain_string_still_translates_escapes(self):
        """非 raw 字符串仍翻译转义（收窄不影响普通字符串）"""
        sig = self._sig('设 甲 为 "a\\nb"')
        self.assertIn(('STRING', 'a\nb'), sig)           # 翻译成真换行

    def test_r_as_variable_not_prefix_when_spaced(self):
        """r 后有空格 / 不贴引号时仍是普通标识符，不误判为前缀"""
        sig = self._sig('设 r 为 1')
        self.assertIn(('IDENTIFIER', 'r'), sig)
        self.assertNotIn(('STRING', ''), sig)



    def test_arithmetic_operator_compound_words(self):
        """测试算术运算符复合词不拆分（v4.2 修复）
        "加法"、"减法"、"乘法"、"除法" 应整体识别为标识符，不拆分为关键字+字
        """
        test_cases = [
            ('加法(a, b)', '加法 应整体识别'),
            ('减法(a, b)', '减法 应整体识别'),
            ('乘法(a, b)', '乘法 应整体识别'),
            ('除法(a, b)', '除法 应整体识别'),
        ]
        for code, description in test_cases:
            with self.subTest(code=code, desc=description):
                lexer = self.Lexer(code)
                tokens = [t for t in lexer.tokenize() if t.type != self.TokenType.EOF]
                # 第一个 token 应该是完整的标识符，不是关键字
                first_token = tokens[0]
                self.assertEqual(first_token.type, self.TokenType.IDENTIFIER,
                               f"{description}: 期望 IDENTIFIER，实际 {first_token.type}: {first_token.value}")

    def test_arithmetic_operator_mid_expression(self):
        """测试算术运算符在表达式中应识别为关键字
        "甲加乙" → [甲][加][乙]，"加" 应识别为关键字
        """
        test_cases = [
            ('甲加乙', ['甲', '加', '乙']),
            ('甲减乙', ['甲', '减', '乙']),
            ('甲乘乙', ['甲', '乘', '乙']),
            ('甲除乙', ['甲', '除', '乙']),
        ]
        for code, expected_values in test_cases:
            with self.subTest(code=code):
                lexer = self.Lexer(code)
                tokens = [t for t in lexer.tokenize() if t.type != self.TokenType.EOF]
                # 应该有三个 token：标识符、关键字、标识符
                self.assertEqual(len(tokens), 3, f"{code} 应产生3个token，实际 {len(tokens)}")
                self.assertEqual(tokens[0].type, self.TokenType.IDENTIFIER)
                self.assertEqual(tokens[0].value, expected_values[0])
                self.assertEqual(tokens[1].type, self.TokenType.KEYWORD)
                self.assertEqual(tokens[1].value, expected_values[1])
                self.assertEqual(tokens[2].type, self.TokenType.IDENTIFIER)
                self.assertEqual(tokens[2].value, expected_values[2])

    def test_arithmetic_compound_keywords(self):
        """测试双字算术运算符关键字（加上、减去、乘以、除以）"""
        test_cases = [
            ('加上', '加上'),
            ('减去', '减去'),
            ('乘以', '乘以'),
            ('除以', '除以'),
        ]
        for keyword, expected in test_cases:
            with self.subTest(keyword=keyword):
                lexer = self.Lexer(keyword + ' a b')
                tokens = [t for t in lexer.tokenize() if t.type != self.TokenType.EOF]
                keyword_tokens = [t for t in tokens if t.type == self.TokenType.KEYWORD and t.value == expected]
                self.assertGreater(len(keyword_tokens), 0,
                                 f"关键字 {keyword} 未被正确识别")

    def test_list_literal(self):
        """测试列表字面量"""
        lexer = self.Lexer('设列表为[1, 2, 3]。')
        tokens = lexer.tokenize()
        token_types = [t.type for t in tokens]
        self.assertIn(self.TokenType.LBRACKET, token_types)
        self.assertIn(self.TokenType.RBRACKET, token_types)

    def test_keywords(self):
        """测试关键字识别"""
        test_cases = [
            ('如果', '如果'),
            ('那么', '那么'),
            ('否则', '否则'),
            ('遍历', '遍历'),
            ('返回', '返回'),
            ('打印', '打印'),
        ]
        for keyword, expected in test_cases:
            with self.subTest(keyword=keyword):
                lexer = self.Lexer(keyword + ' x')
                tokens = lexer.tokenize()
                keyword_tokens = [t for t in tokens if t.type == self.TokenType.KEYWORD and t.value == expected]
                self.assertGreater(len(keyword_tokens), 0,
                                 f"关键字 {keyword} 未被正确识别")

    def test_compact_ascii_operator(self):
        """测试 ASCII 标识符后紧跟运算符动词的紧凑写法（n减1）"""
        # 运算符动词（减/等于）不在 ALL_KEYWORDS，只在 VERB_ARITY，
        # 之前会被误并进 ASCII 标识符（n减 → 单个标识符），现已修复
        lexer = self.Lexer('n减1')
        tokens = lexer.tokenize()
        non_eof = [t for t in tokens if t.type != self.TokenType.EOF]
        self.assertEqual(
            [(t.type, t.value) for t in non_eof],
            [(self.TokenType.IDENTIFIER, 'n'),
             (self.TokenType.KEYWORD, '减'),
             (self.TokenType.NUMBER, 1)],
        )
        # 紧凑范围表达式：left至right 不再被并成单个标识符
        lexer = self.Lexer('left至right')
        tokens = lexer.tokenize()
        non_eof = [t for t in tokens if t.type != self.TokenType.EOF]
        self.assertEqual(
            [(t.type, t.value) for t in non_eof],
            [(self.TokenType.IDENTIFIER, 'left'),
             (self.TokenType.KEYWORD, '至'),
             (self.TokenType.IDENTIFIER, 'right')],
        )
        # 合法复合标识符仍应整体合并（evennum集）
        lexer = self.Lexer('evennum集')
        tokens = lexer.tokenize()
        non_eof = [t for t in tokens if t.type != self.TokenType.EOF]
        self.assertEqual(
            [(t.type, t.value) for t in non_eof],
            [(self.TokenType.IDENTIFIER, 'evennum集')],
        )

    def test_eof_token(self):
        """测试 EOF token"""
        lexer = self.Lexer('x')
        tokens = lexer.tokenize()
        self.assertEqual(tokens[-1].type, self.TokenType.EOF)

    def test_empty_source(self):
        """测试空源文件"""
        lexer = self.Lexer('')
        tokens = lexer.tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, self.TokenType.EOF)

    # ---- v7 新单 B 改点1：模块/标准库/打印 进 IDENTIFIER_SAFE_KEYWORDS ----
    # 这三个常作复合标识符的词中/词尾成分（学生模块 / 可打印 / 我的标准库），
    # 原先会在那里触发拆分：学生模块 → IDENTIFIER(学生)+KEYWORD(模块)。
    # 但它们只享受「词中/词尾」豁免，词首仍是关键字——打印 是 print，
    # 词首豁免会把 `打印甲` 这种无空格 print 语句吞成一个自由标识符。

    def test_identifier_safe_module_print_merged_inside_word(self):
        """模块/标准库/打印 在词中、词尾时整词不切"""
        cases = {
            '学生模块': '学生模块',
            '可打印': '可打印',
            '可打印标志': '可打印标志',
            '可打印字符': '可打印字符',
            '是可打印': '是可打印',
            '我的标准库': '我的标准库',
        }
        for src, whole in cases.items():
            with self.subTest(src=src):
                self.assertEqual(self._sig(src), [('IDENTIFIER', whole)])

    def test_identifier_safe_module_print_in_real_statements(self):
        """examples/L2_wenyan 的真实写法：导入清单与接口名不再被切碎"""
        self.assertEqual(
            self._sig('导 学生模块 出 人, 学生, 可打印'),
            [('KEYWORD', '导'), ('IDENTIFIER', '学生模块'), ('KEYWORD', '出'),
             ('IDENTIFIER', '人'), ('COMMA', ','), ('IDENTIFIER', '学生'),
             ('COMMA', ','), ('IDENTIFIER', '可打印')],
        )
        self.assertEqual(
            self._sig('接 可打印:'),
            [('KEYWORD', '接'), ('IDENTIFIER', '可打印'), ('COLON', ':')],
        )

    def test_identifier_safe_module_print_still_keyword_at_word_start(self):
        """词首语义不能坏：模块/标准库/打印 在词首仍是 KEYWORD

        `打印` 是全语言最高频关键字（print），且无空格写法是一等写法
        （见 src/lexer.py 顶部 docstring「元数驱动参数收集 - 打印 甲」），
        所以 `打印甲`/`打印结果` 必须仍切出 KEYWORD(打印)。
        """
        expected = {
            '模块 甲:': [('KEYWORD', '模块'), ('IDENTIFIER', '甲'), ('COLON', ':')],
            '打印 "x"': [('KEYWORD', '打印'), ('STRING', 'x')],
            '打印 学生模块': [('KEYWORD', '打印'), ('IDENTIFIER', '学生模块')],
            '标准库 数学': [('KEYWORD', '标准库'), ('IDENTIFIER', '数学')],
            # 无空格写法（最高风险）
            '打印甲': [('KEYWORD', '打印'), ('IDENTIFIER', '甲')],
            '打印结果': [('KEYWORD', '打印'), ('IDENTIFIER', '结果')],
            '打印甲乙丙': [('KEYWORD', '打印'), ('IDENTIFIER', '甲乙丙')],
            '模块甲': [('KEYWORD', '模块'), ('IDENTIFIER', '甲')],
            '标准库甲': [('KEYWORD', '标准库'), ('IDENTIFIER', '甲')],
        }
        for src, sig in expected.items():
            with self.subTest(src=src):
                self.assertEqual(self._sig(src), sig)

    def test_identifier_safe_merge_keeps_embedded_keyword(self):
        """反例守卫：新成员并入标识符时，不许连词中真关键字一起吞掉

        仿 test_number_prefix_word_keeps_embedded_keyword：合并逻辑只能吃掉
        模块/标准库/打印 自己，`学生模块等于甲` 中间的 等于 必须还在；
        `打印甲加1` 的 加 也必须还在（否则 print 的实参表达式会被吞平）。
        """
        self.assertEqual(
            self._sig('学生模块等于甲'),
            [('IDENTIFIER', '学生模块'), ('KEYWORD', '等于'), ('IDENTIFIER', '甲')],
        )
        self.assertEqual(
            self._sig('打印甲加1'),
            [('KEYWORD', '打印'), ('IDENTIFIER', '甲'),
             ('KEYWORD', '加'), ('NUMBER', 1)],
        )
        self.assertEqual(
            self._sig('甲加可打印'),
            [('IDENTIFIER', '甲'), ('KEYWORD', '加'), ('IDENTIFIER', '可打印')],
        )

    # ---- v7 新单 B 改点2：_skip_compound_safe_and_match 返回值失配 ----
    # 原实现命中 compound-safe 单字后递归到 pos+1，把内层关键字的 value 配上
    # 内层的 length 一起返回：_match_keyword('自之姓名',0) → ('之',1)。
    # 调用方消费 1 个字符（自）却记成 之，`自之姓名` 切成
    # KEYWORD(之) KEYWORD(之) IDENTIFIER(姓名)，self 语义静默丢失。

    def test_compound_safe_single_before_member_access(self):
        """自之X 等价于 自.X：首 token 必须是 KEYWORD(自)"""
        self.assertEqual(
            self._sig('自之姓名'),
            [('KEYWORD', '自'), ('KEYWORD', '之'), ('IDENTIFIER', '姓名')],
        )
        self.assertEqual(
            self._sig('自之'),
            [('KEYWORD', '自'), ('KEYWORD', '之')],
        )
        # 不限 自：任何 compound-safe 单字关键字紧跟成员访问符 之 都是同一缺陷
        for ch in ('且', '过', '类', '父', '段'):
            with self.subTest(ch=ch):
                self.assertEqual(
                    self._sig(ch + '之姓名'),
                    [('KEYWORD', ch), ('KEYWORD', '之'), ('IDENTIFIER', '姓名')],
                )

    def test_match_keyword_return_value_is_aligned(self):
        """直接探针：返回的关键字必须就是 text[pos:pos+长度]"""
        lexer = self.Lexer('')
        for text in ('自之姓名', '且之', '过之', '类之', '父之'):
            with self.subTest(text=text):
                kw, length = lexer._match_keyword(text, 0)
                self.assertEqual((kw, length), (text[0], 1))

    def test_compound_safe_control_group_unchanged(self):
        """对照组：改点2 不得改动这些既有切法"""
        expected = {
            # 己 不在 compound-safe 表里，本来就是对的
            '己之姓名': [('KEYWORD', '己'), ('KEYWORD', '之'), ('IDENTIFIER', '姓名')],
            '自': [('KEYWORD', '自')],
            '自.姓名': [('KEYWORD', '自'), ('DOT', '.'), ('IDENTIFIER', '姓名')],
            # compound-safe 的原始用途：单独出现不当关键字、作长词组成部分不拆
            '典': [('IDENTIFIER', '典')],
            '字典': [('IDENTIFIER', '字典')],
            '词典': [('IDENTIFIER', '词典')],
            '路径段': [('IDENTIFIER', '路径段')],
            '甲序': [('IDENTIFIER', '甲序')],
            '自蛙': [('IDENTIFIER', '自蛙')],
            '自动化': [('IDENTIFIER', '自动化')],
            # 后随运算符（而非成员访问符）时仍按原样：自 不升级成关键字
            '自加乙': [('IDENTIFIER', '自'), ('KEYWORD', '加'), ('IDENTIFIER', '乙')],
            # compound-safe 运算符后跟另一个 compound-safe 单字：整体保留
            # （去除空格 是自由的 stdlib 名，切开即 NameError）
            '去除空格': [('IDENTIFIER', '去除空格')],
        }
        for src, sig in expected.items():
            with self.subTest(src=src):
                self.assertEqual(self._sig(src), sig)


if __name__ == '__main__':
    unittest.main()

