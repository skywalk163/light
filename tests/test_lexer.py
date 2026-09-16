"""
光明（Light）词法分析器测试

验证决策29的三层分词机制：
1. 类型切换自动分词 - 甲加1 → [甲] [加] [1]
2. 双字关键词优先匹配 - 定义甲 → [定义] [甲]
3. 元数驱动参数收集
"""

import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import Lexer
from tokens import Token, TokenType


def test_basic_keywords():
    """测试基本关键字识别

    R36 任务2 重写（方案B）：原用例用无空格粘连写法 `设甲为三。` 并断言
    tokens[0]==KEYWORD('设')、tokens[1]==IDENTIFIER('甲')，那是旧版确定性切词的
    行为。现词法中 `为` 属于 `_EMBED_MAX_MATCH_KEYWORDS`（为/返回/尝试，见
    lexer.py 的「任务1（L-084/L-092/L-137）：嵌入关键字最大匹配」分支），黏在更长
    汉字游程里必为标识符的一部分，故 `设甲为三` 整体成一个 IDENTIFIER。

    根因是测试假设过时，不是实现回归——按任务铁律不为此修改 lexer.py。
    原始意图（关键字 设/为 被识别、操作数 甲 是标识符）在规范写法
    （关键字与操作数之间带空格）下仍然成立，故用规范写法重写，并额外钉住
    无空格粘连形态的当前行为，防止静默漂移。
    """
    lexer = Lexer()

    # 规范写法：设 甲 为 三。 → 设(KEYWORD) 甲(IDENTIFIER) 为(KEYWORD) 三(CHINESE_NUM) 。
    tokens = lexer.tokenize("设 甲 为 三。")
    print("测试1: 设 甲 为 三。")
    for tok in tokens:
        if tok.type != TokenType.EOF:
            print(f"  {tok}")

    assert tokens[0].type == TokenType.KEYWORD
    assert tokens[0].value == "设"
    print("  [OK] '设' 被正确识别为关键字")

    assert tokens[1].type == TokenType.IDENTIFIER
    assert tokens[1].value == "甲"
    print("  [OK] '甲' 被正确识别为标识符")

    # 赋值关键字 为 是「设 X 为 Y」的第三个 token（原用例漏断言，补齐）
    assert tokens[2].type == TokenType.KEYWORD
    assert tokens[2].value == "为"
    print("  [OK] '为' 被正确识别为赋值关键字")

    assert tokens[3].type == TokenType.CHINESE_NUM
    assert tokens[3].value == 3
    print("  [OK] '三' 被识别为中文数字")

    # R36 钉现状：无空格粘连形态整体成词（`为` 被嵌入关键字最大匹配并入标识符）
    glued = [t.value for t in lexer.tokenize("设甲为三。") if t.type != TokenType.EOF]
    assert glued == ["设甲为三", "。"], \
        f"R36 钉现状失败：无空格 设甲为三 应整体成一个标识符，得到 {glued}"
    print("  [OK] 无空格粘连形态整体成词（现状已钉住）")

    print()


def test_no_space_separation():
    """测试无空格分词"""
    lexer = Lexer()
    
    # 核心测试：甲加1 应该分为 [甲] [加] [1]
    tokens = lexer.tokenize("甲加1。")
    print("测试2: 甲加1。")
    for tok in tokens:
        if tok.type != TokenType.EOF:
            print(f"  {tok}")
    
    assert len([t for t in tokens if t.type != TokenType.EOF and t.type not in (TokenType.NEWLINE,)]) == 4, \
        f"期望4个token（标识符、关键字、数字、句号），得到 {len(tokens)}"
    
    assert tokens[0].type == TokenType.IDENTIFIER
    assert tokens[0].value == "甲"
    print("  [OK] '甲' 被正确分离")
    
    assert tokens[1].type == TokenType.KEYWORD
    assert tokens[1].value == "加"
    print("  [OK] '加' 被正确识别为关键字")
    
    assert tokens[2].type == TokenType.NUMBER
    assert tokens[2].value == 1
    print("  [OK] '1' 被正确识别为数字")
    
    print()


def test_keyword_priority():
    """测试关键字优先匹配"""
    lexer = Lexer()
    
    # 定义甲 → [定义] [甲]
    tokens = lexer.tokenize("定义甲。")
    print("测试3: 定义甲。")
    for tok in tokens:
        if tok.type != TokenType.EOF:
            print(f"  {tok}")
    
    assert tokens[0].type == TokenType.KEYWORD
    assert tokens[0].value == "定义"
    print("  [OK] '定义' 被正确识别（双字关键字优先匹配）")
    
    assert tokens[1].type == TokenType.IDENTIFIER
    assert tokens[1].value == "甲"
    print("  [OK] '甲' 被正确分离")
    
    print()


def test_if_statement():
    """测试条件语句"""
    lexer = Lexer()
    
    # 如果甲大于乙那么打印甲。
    tokens = lexer.tokenize("如果甲大于乙那么打印甲。")
    print("测试4: 如果甲大于乙那么打印甲。")
    for tok in tokens:
        if tok.type != TokenType.EOF and tok.type not in (TokenType.NEWLINE,):
            print(f"  {tok}")
    
    # 验证关键字序列
    keywords = [t.value for t in tokens if t.type == TokenType.KEYWORD]
    print(f"  识别到的关键字: {keywords}")
    
    assert "如果" in keywords, "应该识别到 '如果'"
    assert "大于" in keywords, "应该识别到 '大于'"
    assert "那么" in keywords, "应该识别到 '那么'"
    assert "打印" in keywords, "应该识别到 '打印'"
    print("  [OK] 所有关键字被正确识别")
    
    print()


def test_multiple_keywords():
    """测试多个连续关键字

    R36 任务2 重写（方案B）：原用例写 `遍历列表映射筛选`（四个词粘连），断言
    keywords 含 遍历/映射/筛选。现词法只在**独立汉字游程的词首**切关键字：
    `列表` 不是关键字（不在 _ALL_KEYWORDS_WITH_VERBS 中），于是从 列表 起的那整段
    游程整体成一个 IDENTIFIER，把 映射/筛选 吞在里面——实测输出为
    [KEYWORD 遍历, IDENTIFIER 列表映射筛选]。

    根因是原用例把非关键字 `列表` 混进了「连续关键字」序列，假设过时，
    不是实现回归（同文件 test_keyword_priority/test_if_statement 在规范写法下
    已覆盖关键字优先匹配）。故改为真正的连续关键字序列，并单独钉住
    「非关键字保持标识符」这一原用例注释里点明的意图。
    """
    lexer = Lexer()

    # 真正的连续关键字：遍历映射 → 遍历(KEYWORD) 映射(KEYWORD)
    tokens = lexer.tokenize("遍历映射。")
    print("测试5a: 遍历映射。")
    for tok in tokens:
        if tok.type != TokenType.EOF and tok.type not in (TokenType.NEWLINE,):
            print(f"  {tok}")

    keywords = [t.value for t in tokens if t.type == TokenType.KEYWORD]
    print(f"  识别到的关键字: {keywords}")

    assert "遍历" in keywords
    assert "映射" in keywords
    print("  [OK] 连续关键字 遍历/映射 都被正确识别")

    # 另一组连续关键字：映射 筛选
    keywords2 = [t.value for t in lexer.tokenize("映射 筛选。")
                 if t.type == TokenType.KEYWORD]
    assert "映射" in keywords2 and "筛选" in keywords2, \
        f"映射/筛选 应都被识别为关键字，得到 {keywords2}"
    print("  [OK] 连续关键字 映射/筛选 都被正确识别")

    # 原用例注释点明的意图：列表 不是关键字，应保持标识符
    toks = lexer.tokenize("遍历 列表。")
    ids = [t.value for t in toks if t.type == TokenType.IDENTIFIER]
    kws = [t.value for t in toks if t.type == TokenType.KEYWORD]
    assert "列表" in ids, f"'列表' 应作为标识符，得到 ids={ids}"
    assert "列表" not in kws, f"'列表' 不应被当作关键字，得到 kws={kws}"
    assert "遍历" in kws
    print("  [OK] 非关键字 '列表' 保持标识符，'遍历' 仍是关键字")

    print()


def test_chinese_numbers():
    """测试中文数字"""
    lexer = Lexer()
    
    # 甲加三
    tokens = lexer.tokenize("甲加三。")
    print("测试6: 甲加三。")
    for tok in tokens:
        if tok.type != TokenType.EOF and tok.type not in (TokenType.NEWLINE,):
            print(f"  {tok}")
    
    assert tokens[0].type == TokenType.IDENTIFIER
    assert tokens[0].value == "甲"
    print("  [OK] '甲' 被正确识别")
    
    assert tokens[1].type == TokenType.KEYWORD
    assert tokens[1].value == "加"
    print("  [OK] '加' 被正确识别")
    
    assert tokens[2].type == TokenType.CHINESE_NUM
    assert tokens[2].value == 3
    print("  [OK] '三' 被识别为中文数字")
    
    print()


def test_symbols():
    """测试符号识别"""
    lexer = Lexer()
    
    # 甲，乙，丙。
    tokens = lexer.tokenize("甲，乙，丙。")
    print("测试7: 甲，乙，丙。")
    for tok in tokens:
        if tok.type != TokenType.EOF and tok.type not in (TokenType.NEWLINE,):
            print(f"  {tok}")
    
    commas = [t for t in tokens if t.type == TokenType.COMMA]
    assert len(commas) == 2, "应该有2个逗号"
    print("  [OK] 逗号被正确识别")
    
    dots = [t for t in tokens if t.type == TokenType.PERIOD]
    assert len(dots) == 1, "应该有1个句号"
    print("  [OK] 句号被正确识别")
    
    print()


def test_complex_expression():
    """测试复杂表达式

    R36 任务2 重写（方案B）：原用例写 `设甲为三加五。`（无空格粘连），断言
    keywords 含 设/为/加。实测输出是单个 IDENTIFIER('设甲为三加五')——`为` 属于
    `_EMBED_MAX_MATCH_KEYWORDS`，黏在更长汉字游程里整体并入标识符（L-084/L-092/
    L-137 修复）。根因是测试假设过时，不是实现回归，按铁律不改 lexer.py。

    原始意图（一条赋值语句里同时出现 设/为/加 三个关键字）在规范写法
    `设 甲 为 三 加 五。` 下完全成立，故用规范写法重写；并额外钉住两个易误判的
    现状：`三加五` 粘连时整体成词（中缀运算符不切开中文数字游程）、
    `三 加 五` 带空格时才切成 三/加/五。
    """
    lexer = Lexer()

    # 规范写法：设 甲 为 三 加 五。
    tokens = lexer.tokenize("设 甲 为 三 加 五。")
    print("测试8: 设 甲 为 三 加 五。")
    for tok in tokens:
        if tok.type != TokenType.EOF and tok.type not in (TokenType.NEWLINE,):
            print(f"  {tok}")

    keywords = [t.value for t in tokens if t.type == TokenType.KEYWORD]
    print(f"  识别到的关键字: {keywords}")

    assert "设" in keywords
    assert "为" in keywords
    assert "加" in keywords
    print("  [OK] 复杂表达式里的 设/为/加 三个关键字都被正确识别")

    # 值部分：三(CHINESE_NUM) 加(KEYWORD) 五(CHINESE_NUM)
    values = [t.value for t in tokens if t.type == TokenType.CHINESE_NUM]
    assert values == [3, 5], f"中文数字应为 [3, 5]，得到 {values}"
    print("  [OK] 中文数字 三/五 被正确识别为值")

    # R36 钉现状：数字与运算符粘连时整体成词（不加空格不会切成 三+加+五）
    glued = [t.value for t in lexer.tokenize("设 甲 为 三加五。")
             if t.type != TokenType.EOF]
    assert "三加五" in glued, \
        f"R36 钉现状失败：三加五 粘连应整体成词，得到 {glued}"
    assert "加" not in [t.value for t in lexer.tokenize("设 甲 为 三加五。")
                        if t.type == TokenType.KEYWORD], \
        "R36 钉现状失败：三加五 粘连时 加 不应被切出为关键字"
    print("  [OK] 数字+运算符粘连时整体成词（现状已钉住）")

    print()


def test_indentation():
    """测试缩进处理"""
    lexer = Lexer()
    
    source = """如果甲大于乙：
    打印甲。
否则：
    打印乙。"""
    
    tokens = lexer.tokenize(source)
    print("测试9: 缩进处理")
    for tok in tokens:
        if tok.type not in (TokenType.EOF, TokenType.NEWLINE):
            print(f"  {tok}")
    
    indents = [t for t in tokens if t.type == TokenType.INDENT]
    dedents = [t for t in tokens if t.type == TokenType.DEDENT]
    
    print(f"  INDENT 数量: {len(indents)}")
    print(f"  DEDENT 数量: {len(dedents)}")
    
    print()


def test_l010_keyword_split_regression():
    """L-010 回归：含关键字的模块名必须整体成词，不得被劈开。

    背景（commit 629efd99 / merge 73b001bd）：预扫描把短名（主/入口/命令）收进
    user_definitions 后，`从 主程序 导入` 会被劈成 主+程序；`外部命令` 也被词首
    关键字切成 外部+命令。本测试锁定三个修复点 + 一个禁止回归点：
      · 主程序 / 主入口 → 单个 IDENTIFIER（Fix A）
      · 外部命令 → 单个 IDENTIFIER（Fix B，仅「外部」允许词首合并）
      · `返回` 语句关键字仍单独成 token，绝不词首合并（否则 返回 斐波那契 会
        被拼成 返回斐波那契 → NameError）
    """
    lexer = Lexer()

    def idents(src):
        return [t.value for t in lexer.tokenize(src)
                if t.type == TokenType.IDENTIFIER]

    # Fix A：主程序 / 主入口 作为模块名整体为标识符
    for module, short in [('主程序', '主'), ('主入口', '入口')]:
        src = f'从 {module} 导入 {short}。'
        got = idents(src)
        assert module in got, f'L-010 FixA 失败：{src!r} 未把 {module} 切为整体标识符，得到 {got}'
        assert short in got, f'L-010 FixA 失败：{src!r} 丢失导入名 {short}，得到 {got}'
    print("  [OK] L-010 FixA：主程序/主入口 整体成词")

    # Fix B：外部命令 词首合并为整体标识符
    got = idents('从 外部命令 导入 命令。')
    assert '外部命令' in got, f'L-010 FixB 失败：外部命令 未合并，得到 {got}'
    assert '命令' in got, f'L-010 FixB 失败：外部命令 丢失导入名 命令，得到 {got}'
    print("  [OK] L-010 FixB：外部命令 整体成词")

    # 禁止回归：返回 语句关键字绝不词首合并
    src = '段落 斐波那契(n)：\n    返回 n。'
    toks = [t for t in lexer.tokenize(src) if t.type != TokenType.EOF]
    assert any(t.type == TokenType.KEYWORD and t.value == '返回' for t in toks), \
        f'L-010 回归失败：返回 应保持独立关键字，得到 {[(t.type.name, t.value) for t in toks]}'
    assert not any(t.type == TokenType.IDENTIFIER and '返回' in t.value and t.value != '返回'
                   for t in toks), 'L-010 回归失败：返回 被错误并入标识符'
    print("  [OK] L-010 回归：返回 保持独立关键字")

    print()


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("光明词法分析器测试")
    print("=" * 60)
    print()
    
    try:
        test_basic_keywords()
        test_no_space_separation()
        test_keyword_priority()
        test_if_statement()
        test_multiple_keywords()
        test_chinese_numbers()
        test_symbols()
        test_complex_expression()
        test_indentation()
        test_l010_keyword_split_regression()
        
        print("=" * 60)
        print("[OK] 所有测试通过！")
        print("=" * 60)
        return True
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"✗ 测试失败: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
