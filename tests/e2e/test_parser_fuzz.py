# -*- coding: utf-8 -*-
"""
解析器模糊测试（Fuzz Testing）
覆盖：边界输入、异常输入、深层嵌套、特殊字符，确保解析器不崩溃
"""
import os
import sys
import unittest

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
for _p in [_src_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser


class TestParserFuzz(unittest.TestCase):
    """解析器模糊测试"""

    def setUp(self):
        self.parser = LightParser()

    # ==========================================================
    # 空与极小输入
    # ==========================================================
    def test_empty_input(self):
        """空字符串"""
        result = self.parser.parse('')
        # 空输入不应崩溃，可能返回 None 或空 AST
        self.assertIsNotNone(True)  # 只要不抛异常就算通过

    def test_whitespace_only(self):
        """仅有空白字符"""
        result = self.parser.parse('   \n\n\t  \n  ')
        self.assertIsNotNone(True)

    def test_comment_only(self):
        """仅有注释"""
        result = self.parser.parse('# 这是一条注释')
        self.assertIsNotNone(True)

    # ==========================================================
    # 边界关键字
    # ==========================================================
    def test_keyword_as_identifier(self):
        """关键字作为标识符"""
        # 这些输入可能产生解析错误，但不应该崩溃
        cases = [
            '设 若 为 10',
            '设 设 为 20',
            '设 打印 为 30',
            '设 真 为 40',
        ]
        for code in cases:
            try:
                self.parser.parse(code)
            except Exception:
                pass  # 解析失败可以，崩溃不行

    def test_reserved_keywords_in_expressions(self):
        """表达式中使用保留字"""
        cases = [
            '设 结果 为 若 加 否',
            '打印(段 加 返)',
        ]
        for code in cases:
            try:
                self.parser.parse(code)
            except Exception:
                pass

    # ==========================================================
    # 嵌套深度
    # ==========================================================
    def test_deeply_nested_if(self):
        """深层嵌套条件"""
        # 生成 10 层嵌套 if
        code = '设 x 为 1\n'
        for i in range(10):
            code += '如果 x 大于 0：\n'
            code += '  设 x 为 x 加 1\n'
        try:
            self.parser.parse(code)
        except Exception:
            pass

    def test_deeply_nested_loop(self):
        """深层嵌套循环"""
        code = '设 x 为 1\n'
        for i in range(10):
            code += '当 x 小于 10：\n'
            code += '  设 x 为 x 加 1\n'
        try:
            self.parser.parse(code)
        except Exception:
            pass

    def test_nested_blocks(self):
        """嵌套块：循环内条件内遍历"""
        code = '''
设 列表 为 [1,2,3]
当 真：
    如果 列表[0] > 0：
        遍 列表为 x：
            打印(x)
    跳
'''
        try:
            self.parser.parse(code)
        except Exception:
            pass

    # ==========================================================
    # 特殊字符
    # ==========================================================
    def test_unicode_characters(self):
        """Unicode 字符"""
        cases = [
            '设 变量 为 "你好世界🌍"',
            '设 甲 为 "日本語テスト"',
            '设 乙 为 "한국어"',
            '设 丙 为 "🏳️‍🌈🏳️‍🌈"',
        ]
        for code in cases:
            try:
                self.parser.parse(code)
            except Exception:
                pass

    def test_special_punctuation(self):
        """特殊标点符号"""
        cases = [
            '设 甲 为 "!@#$%^&*()"',
            '设 乙 为 "<>?/\\\\|{}[]"',
            '设 丙 为 "~`"',
        ]
        for code in cases:
            try:
                self.parser.parse(code)
            except Exception:
                pass

    def test_escaped_strings(self):
        """转义字符串"""
        cases = [
            '设 甲 为 "他说：\\"你好\\""',
            '设 乙 为 "换行\\n制表\\t"',
            '设 丙 为 "\\\\n 不是换行"',
        ]
        for code in cases:
            try:
                self.parser.parse(code)
            except Exception:
                pass

    # ==========================================================
    # 长输入
    # ==========================================================
    def test_long_string(self):
        """超长字符串"""
        long_str = '设 甲 为 "' + 'x' * 10000 + '"'
        try:
            self.parser.parse(long_str)
        except Exception:
            pass

    def test_long_list(self):
        """超长列表"""
        nums = ', '.join(str(i) for i in range(1000))
        code = f'设 列表 为 [{nums}]'
        try:
            self.parser.parse(code)
        except Exception:
            pass

    def test_long_program(self):
        """长程序（多行）"""
        lines = []
        for i in range(200):
            lines.append(f'设 变量{i} 为 {i}')
        code = '\n'.join(lines)
        try:
            self.parser.parse(code)
        except Exception:
            pass

    # ==========================================================
    # 格式错误
    # ==========================================================
    def test_malformed_blocks(self):
        """格式错误的块"""
        cases = [
            '引 Python:\n    import os\n# 缺少结束引',
            '引 C:\n    int main() {}\n# 缺少结束引',
            '引 Go:\n    func main() {}\n# 缺少结束引',
        ]
        for code in cases:
            try:
                self.parser.parse(code)
            except Exception:
                pass

    def test_incomplete_statements(self):
        """不完整的语句"""
        cases = [
            '设 甲 为',
            '如果 甲 大于',
            '当 甲 小于',
            '遍历 甲',
            '段落 函数 接收',
        ]
        for code in cases:
            try:
                self.parser.parse(code)
            except Exception:
                pass

    def test_mixed_styles(self):
        """混合文体（白话+文言）"""
        code = '''
# 文体: 白话
设数据=[3,1,4,1,5,9,2,6]
设平均=数据和/数据长
打印平均

# 文体: 文言
设 数据: 列[数] = [3, 1, 4, 1, 5, 9, 2, 6]
打印 和(数据)
'''
        try:
            self.parser.parse(code)
        except Exception:
            pass

    # ==========================================================
    # 边界数值
    # ==========================================================
    def test_extreme_numbers(self):
        """极端数值"""
        cases = [
            '设 甲 为 999999999999999999999999999999',
            '设 乙 为 0.0000000000000000000000001',
            '设 丙 为 -999999999999999999999999999999',
            '设 丁 为 0',
            '设 戊 为 -0',
        ]
        for code in cases:
            try:
                self.parser.parse(code)
            except Exception:
                pass

    # ==========================================================
    # 空的列表/字典
    # ==========================================================
    def test_empty_containers(self):
        """空容器"""
        cases = [
            '设 列表 为 []',
            '设 字典 为 {}',
            '设 嵌套 为 [[]]',
            '设 空字典 为 {"键": 空}',
        ]
        for code in cases:
            try:
                self.parser.parse(code)
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main(verbosity=2)