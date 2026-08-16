"""
段言（Duan）编程语言 - 上下文管理器测试

测试 使用 关键字资源管理，包括同步/异步上下文管理器、多个上下文管理器
"""

import pytest
import sys
import os

# 确保 src 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from light_parser_v3 import LightParser, ParseError
from ast_nodes_v3 import WithStmt, Module, ReturnStmt, NumberLiteral
from code_generator import PythonCodeGenerator as CodeGenerator


# =============================================================================
# 编译辅助函数
# =============================================================================

def _compile_ok(code: str) -> str:
    """编译代码，成功返回生成的Python代码，失败抛出异常"""
    parser = LightParser()
    module = parser.parse(code)
    gen = CodeGenerator()
    result = gen.generate(module)
    return result


def _compile_error(code: str) -> str:
    """编译代码，期望失败返回错误信息"""
    parser = LightParser()
    try:
        module = parser.parse(code)
        gen = CodeGenerator()
        result = gen.generate(module)
        return f"期望错误但编译成功: {result}"
    except (ParseError, Exception) as e:
        return str(e)


# =============================================================================
# 1. 基本上下文管理器测试
# =============================================================================

class TestBasicWith:
    """测试基本使用 关键字上下文管理器"""

    def test_with_simple_expr(self):
        """基本使用表达式"""
        code = """
使用 打开("test.txt") 为 f:
  输出(f)
"""
        result = _compile_ok(code)
        assert 'with open(' in result or 'with 打开(' in result
        assert 'as f' in result

    def test_with_variable(self):
        """使用变量作为上下文管理器"""
        code = """
设 资源 为 创建资源()
使用 资源:
  输出("使用资源")
"""
        result = _compile_ok(code)
        assert 'with ' in result

    def test_with_body(self):
        """上下文管理器体"""
        code = """
使用 打开("a.txt") 为 f:
  设 内容 为 f.读取()
  输出(内容)
"""
        result = _compile_ok(code)
        assert 'with ' in result
        assert 'f.读取' in result or 'f.read' in result

    def test_without_variable(self):
        """不使用 as 变量"""
        code = """
使用 锁:
  输出("临界区")
"""
        result = _compile_ok(code)
        assert 'with 锁:' in result or 'with lock:' in result


# =============================================================================
# 2. 异步上下文管理器测试
# =============================================================================

class TestAsyncWith:
    """测试使用 异步 上下文管理器"""

    def test_async_with_basic(self):
        """基本异步上下文管理器"""
        code = """
使用 异步 打开文件("test.txt") 为 f:
  等待 f.读取()
"""
        result = _compile_ok(code)
        assert 'async with ' in result

    def test_async_with_await(self):
        """异步上下文管理器 + 等待"""
        code = """
使用 异步 连接数据库() 为 db:
  设 结果 为 等待 db.查询("SELECT 1")
  输出(结果)
"""
        result = _compile_ok(code)
        assert 'async with ' in result

    def test_async_without_variable(self):
        """异步上下文管理器不带变量"""
        code = """
使用 异步 资源锁:
  输出("异步临界区")
"""
        result = _compile_ok(code)
        assert 'async with ' in result

    def test_async_with_return(self):
        """异步上下文管理器 + 返回值"""
        code = """
函数 处理数据():
  使用 异步 打开文件("data.txt") 为 f:
    返回 等待 f.读取()
"""
        result = _compile_ok(code)
        assert 'async with ' in result


# =============================================================================
# 3. AST 结构测试
# =============================================================================

class TestWithAST:
    """测试上下文管理器 AST 结构"""

    def test_ast_with_stmt(self):
        """验证 WithStmt AST 节点"""
        code = """
使用 打开("test.txt") 为 f:
  输出(f)
"""
        parser = LightParser()
        module = parser.parse(code)
        assert len(module.statements) >= 1
        # 找到 WithStmt
        with_stmt = None
        for stmt in module.statements:
            if isinstance(stmt, WithStmt):
                with_stmt = stmt
                break
        assert with_stmt is not None, "未找到 WithStmt 节点"
        assert with_stmt.variable == 'f'

    def test_ast_async_with(self):
        """验证异步上下文管理器 AST 节点"""
        code = """
使用 异步 打开文件("test.txt") 为 f:
  等待 f.读取()
"""
        parser = LightParser()
        module = parser.parse(code)
        with_stmt = None
        for stmt in module.statements:
            if isinstance(stmt, WithStmt):
                with_stmt = stmt
                break
        assert with_stmt is not None
        assert with_stmt.is_async == True

    def test_ast_multiple_items(self):
        """验证多个上下文管理器 AST 节点"""
        code = """
使用 打开("a.txt") 为 f1, 打开("b.txt") 为 f2:
  输出(f1)
"""
        parser = LightParser()
        module = parser.parse(code)
        with_stmt = None
        for stmt in module.statements:
            if isinstance(stmt, WithStmt):
                with_stmt = stmt
                break
        assert with_stmt is not None
        assert with_stmt.items is not None
        assert len(with_stmt.items) == 2


# =============================================================================
# 5. 代码生成测试
# =============================================================================

class TestWithCodeGen:
    """测试上下文管理器代码生成"""

    def test_codegen_sync_with(self):
        """同步上下文管理器代码生成"""
        code = """
使用 打开("test.txt") 为 f:
  输出(f)
"""
        result = _compile_ok(code)
        assert 'with ' in result
        assert 'as f:' in result

    def test_codegen_async_with(self):
        """异步上下文管理器代码生成"""
        code = """
使用 异步 打开文件("test.txt") 为 f:
  等待 f.读取()
"""
        result = _compile_ok(code)
        assert 'async with ' in result


# =============================================================================
# 6. 端到端功能测试
# =============================================================================

class TestWithEndToEnd:
    """上下文管理器端到端测试"""

    def test_with_file_read(self):
        """使用文件读取"""
        code = """
使用 打开("data.txt") 为 f:
  设 内容 为 f.读取()
  输出(内容)
"""
        result = _compile_ok(code)
        assert 'with ' in result
        assert 'f.读取' in result or 'f.read' in result

    def test_async_with_file(self):
        """异步文件读取"""
        code = """
使用 异步 打开文件("data.txt") 为 f:
  设 内容 为 等待 f.读取()
  输出(内容)
"""
        result = _compile_ok(code)
        assert 'async with ' in result


# =============================================================================
# 7. 等待(await) 与复合标识符的消歧边界（v7 单 07 回归）
# =============================================================================

class TestAwaitMemberAccess:
    """`等待 对象.成员` 必须解析成 await 表达式，而 `等待X` 仍是复合标识符

    v7 单 07：`src/parser_expr.py` 的 `等待` 分支原先只把「等待 标识符(」当 await，
    peek2 是 DOT 时误走复合标识符分支，只吃掉 `等待`+`f` 返回 Identifier('等待f')，
    `.读取()` 被丢在 token 流里没人消费 → ParseError「无法识别的语法元素：'.'」。
    修复把 DOT 一并归入 await 一侧。这里两头都测，防止修复方向倒过来打穿复合标识符。
    """

    def test_await_member_call(self):
        """等待 + 内置名成员：不应报错，且成员名不被内置映射改写"""
        result = _compile_ok('等待 f.读取()\n')
        assert 'await f.读取()' in result
        # 单 03 的成员访问护栏仍在：不能退化成 await input(f)
        assert 'input(f)' not in result

    def test_await_member_call_non_builtin(self):
        """等待 + 非内置名成员"""
        result = _compile_ok('等待 f.抓取()\n')
        assert 'await f.抓取()' in result

    def test_await_chained_member(self):
        """等待 + 链式成员访问"""
        result = _compile_ok('等待 甲.乙.丙()\n')
        assert 'await 甲.乙.丙()' in result

    def test_await_plain_call_unchanged(self):
        """等待 + 普通调用：原有行为不变"""
        result = _compile_ok('等待 读取(f)\n')
        assert 'await ' in result

    def test_compound_identifier_before_rparen(self):
        """等待价值 在右括号前仍是复合标识符，不是 await"""
        result = _compile_ok('打印(等待价值)\n')
        assert 'print(等待价值)' in result
        assert 'await' not in result

    def test_compound_identifier_before_newline(self):
        """等待价值 在行尾仍是复合标识符"""
        result = _compile_ok('设 甲 为 等待价值\n')
        assert '甲 = 等待价值' in result
        assert 'await' not in result

    def test_compound_identifier_before_operator(self):
        """等待结果 后跟运算符时仍是复合标识符"""
        result = _compile_ok('设 甲 为 等待结果 加 1\n')
        assert '等待结果' in result
        assert 'await' not in result


class TestBracketCallArity:
    """v7 单 04：括号式调用不再被内置动词的 arity 截断

    `求和` 在 VERB_ARITY 里 arity=1，用户却可以定义 `段 求和(a, b)`。
    原实现用 arity 给括号式收参循环封顶，把 `求和(10, 20)` 编成 `求和(10)`，
    编译期不报错、运行期才炸，属静默错译。括号与逗号已界定边界，不该再套 arity。
    """

    def test_two_args_not_truncated(self):
        result = _compile_ok('段 求和(a, b)：\n  返回 a + b\n打印(求和(10, 20))\n')
        assert '求和(10, 20)' in result

    def test_three_args_not_truncated(self):
        """不是「只丢最后一个」：原实现会丢掉 arity 之后的全部"""
        result = _compile_ok('段 求和(a, b, c)：\n  返回 a + b + c\n打印(求和(1, 2, 3))\n')
        assert '求和(1, 2, 3)' in result

    def test_nested_call_not_truncated(self):
        result = _compile_ok('段 求和(a, b)：\n  返回 a + b\n打印(求和(求和(1, 2), 3))\n')
        assert '求和(求和(1, 2), 3)' in result

    def test_non_verb_name_unchanged(self):
        """名字不撞内置动词时走标识符路径，行为不变"""
        result = _compile_ok('段 加法(a, b)：\n  返回 a + b\n打印(加法(10, 20))\n')
        assert '加法(10, 20)' in result

    def test_args_fewer_than_arity_unchanged(self):
        """实参数 ≤ arity 的旧输入产物不变（收满即遇 RPAREN 停）"""
        result = _compile_ok('打印(长度([1, 2, 3]))\n')
        assert 'len([1, 2, 3])' in result


class TestBracketCallKeywordArgs:
    """v7 新单 B（第 3 票）：括号式调用接受具名实参 `名 = 值`

    与上面 TestBracketCallArity 同族——同一个收参循环
    （src/parser_expr.py:659，单 04 在那里去掉了 arity 上限）。本票让它再认
    `kwarg = value`，堵住 examples/L2_wenyan/主程序.light:58 的
    `排序(学生列表, 依据 = ...)`。

    判据是纯词法的：一串 IDENTIFIER/非停用 KEYWORD + 紧跟一个 EQUALS。
    `=` 是 EQUALS（src/tokens.py:43），比较用的 `==` 是 EQ_EQ（src/tokens.py:54），
    词法上就分开；且赋值在光明是**语句**不是表达式，所以括号实参区里出现裸 `=`
    只可能是具名实参。改前实测：ParseError「意外的标记: 「=」」——
    也就是说本改动只把「原本报错」变成「正确解析」，不改写任何既有产物。

    ⚠ 关于「实参名要不要翻译」：**内置函数必须翻译**。`排序` 经 builtin_map
    映射成 Python 内置 `sorted`，而 CPython 的 `sorted` 只认 `key` / `reverse`；
    若把中文名原样透传就发射 `sorted(xs, 依据=f)`，编译过得去、一跑就
    `TypeError: sorted() got an unexpected keyword argument '依据'`——正是本轮
    要消灭的「静默过、运行炸」。所以下面几条断言期望的是
    `key=` / `reverse=`，由 src/code_generator.py 的
    _BUILTIN_KWARG_NAME_MAP + _kwarg_name() 完成配对翻译。
    用户自定义函数不在表里，仍原样透传（见
    test_positional_before_keyword_order_kept 的 `b=20`）。
    """

    def test_keyword_arg_accepted(self):
        """改前 ParseError，改后收成具名实参；`依据` 翻成 sorted 的 `key`"""
        result = _compile_ok('设 排名 = 排序(学生列表, 依据 = 键函数)\n')
        assert 'sorted(学生列表, key=键函数)' in result

    def test_multiple_keyword_args(self):
        """多个具名实参；`倒序` 与 `逆序` 同为 sorted 的 `reverse`"""
        result = _compile_ok('设 r = 排序(xs, 依据 = f, 倒序 = 真)\n')
        assert 'sorted(xs, key=f, reverse=True)' in result

    def test_positional_before_keyword_order_kept(self):
        """位置实参与具名实参的先后次序必须保持源码顺序"""
        result = _compile_ok('段 求和(a, b)：\n  返回 a + b\n打印(求和(10, b = 20))\n')
        assert '求和(10, b=20)' in result

    def test_comparison_not_mistaken_for_keyword_arg(self):
        """`==` 是 EQ_EQ，绝不能被判成具名实参（否则会静默改写既有产物）"""
        result = _compile_ok('设 c = 排序(学生列表, 甲 == 乙)\n')
        assert 'sorted(学生列表, (甲 == 乙))' in result

    def test_plain_bracket_call_unchanged(self):
        """无 `=` 的括号式调用逐字不变（单向放宽的对照组）"""
        result = _compile_ok('设 排名 = 排序(学生列表)\n')
        assert 'sorted(学生列表)' in result

    def test_keyword_arg_value_is_full_expression(self):
        """具名实参的值是完整表达式，不是单 token"""
        result = _compile_ok('设 r = 排序(xs, 依据 = 甲 + 乙)\n')
        assert 'sorted(xs, key=(甲 + 乙))' in result



class TestContainsOperator:
    """v7 单 08：`包含` 的内部占位符 @@contains@@ 不再泄漏，且操作数方向正确

    `A 包含 B` 语义是「A 含有 B」→ Python `B in A`，操作数必须交换。
    只把占位符替换成 `in` 而不交换，会得到语法通过、语义相反的静默错译，
    比原来的 SyntaxError 更坏。
    """

    _SRC = ('段落 查找 接收 文件名, 关键词:\n'
            '  如果 文件名 包含 关键词:\n'
            '    打印("命中")。\n')

    def test_placeholder_not_leaked(self):
        assert '@@' not in _compile_ok(self._SRC)

    def test_operand_order_swapped(self):
        """容器在左、被找的东西在右 → 产物必须是 关键词 in 文件名"""
        result = _compile_ok(self._SRC)
        assert '(关键词 in 文件名)' in result
        assert '(文件名 in 关键词)' not in result

    def test_compound_or_expression(self):
        """工单原形：或复合条件里也不泄漏、方向不变"""
        result = _compile_ok('段落 查找 接收 文件名, 关键词:\n'
                             '  如果 关键词 等于 "" 或 文件名 包含 关键词:\n'
                             '    打印("命中")。\n')
        assert '@@' not in result
        assert '(关键词 in 文件名)' in result

    def test_parens_kept_to_avoid_chained_comparison(self):
        """括号必须留：in 是比较运算符，裸发射会与外层比较串成链式比较

        `x in y == False` 会被 Python 解释成 `(x in y) and (y == False)`，恒假。
        """
        result = _compile_ok('段落 查找 接收 文件名, 关键词:\n'
                             '  如果 (文件名 包含 关键词) 等于 假:\n'
                             '    打印("未命中")。\n')
        assert '(关键词 in 文件名)' in result

    def test_other_operators_unchanged(self):
        """不含 包含 的运算符不受影响"""
        result = _compile_ok('设 甲 为 1 加 2\n')
        assert '@@' not in result
        assert '(1 + 2)' in result


class TestL2OOPCodegen:
    """v7 新单 B（第 4 票）：codegen 层 L2 OOP 修复（`的项`/`自`→self/构造调用/接口 ABC）。

    为什么手工建 AST 而不是喂源码：本轮 parser 票（parser_stmt/parser_expr）尚在
    飞行中，`类 X:` + `设 属性: 类型` + `类 X 承 Y 接 Z:` 现在还 parse 不过，
    喂 examples/L2_wenyan/学生模块.light 会 ParseError。手工 AST 直接驱动 codegen
    这一层，不受 parser 抖动影响；等 parser 票落地后同一份源码会自然走通。

    断言标准照 TestContainsOperator：断的是**语义 / 运行期行为**，不是「字符串里
    出现了某个词」。每条改动都 exec 起来真跑，确认 `的项` 真迭代出键值对、
    `自` 真绑定 self、`人之构造` 真调到父类 __init__。

    真实词法：`自之成绩的项` -> KEYWORD(自) KEYWORD(之) IDENTIFIER(成绩的项)
    -> MemberAccess(自, '成绩的项')；`的项` 粘在尾部标识符里（lexer 不切 `的`）。
    """

    def _build_module(self):
        from ast_nodes_v3 import (
            Module, ClassDefinition, AttributeDeclaration, MethodDefinition,
            Parameter, InterfaceDefinition, MethodSignature, Assignment,
            MemberAccess, Identifier, VarDecl, ReturnStmt, ForeachStmt,
            BinaryOp, NumberLiteral, StringLiteral, IndexAccess, DictLiteral, IfStmt,
        )
        I = Identifier
        接口 = InterfaceDefinition(
            name='可打印',
            methods=[MethodSignature('字符串化', [], '串', None)],
        )
        # 接口签名带 `自` 形参（docs/L2_文言体语法规范_v4.0.md:590-591）
        接口自 = InterfaceDefinition(
            name='可显示',
            methods=[MethodSignature('打印', [Parameter('自')], '空', None)],
        )
        人 = ClassDefinition(
            name='人',
            attributes=[AttributeDeclaration('姓名', '串'), AttributeDeclaration('年龄', '数')],
            methods=[
                MethodDefinition('构造', [Parameter('姓名', '串'), Parameter('年龄', '数')], [
                    Assignment(MemberAccess(I('自'), '姓名'), I('姓名')),
                    Assignment(MemberAccess(I('自'), '年龄'), I('年龄')),
                ], is_constructor=True),
                MethodDefinition('取姓名', [], [ReturnStmt(MemberAccess(I('自'), '姓名'))], return_type='串'),
            ],
        )
        学生 = ClassDefinition(
            name='学生',
            attributes=[AttributeDeclaration('学号', '串'), AttributeDeclaration('成绩', '典')],
            base_classes=['人'], interfaces=['可打印'],
            methods=[
                MethodDefinition('构造', [Parameter('姓名'), Parameter('年龄'), Parameter('学号')], [
                    MemberAccess(I('人'), '构造', True, [I('自'), I('姓名'), I('年龄')]),
                    Assignment(MemberAccess(I('自'), '学号'), I('学号')),
                    Assignment(MemberAccess(I('自'), '成绩'), DictLiteral([])),
                ], is_constructor=True),
                MethodDefinition('录入成绩', [Parameter('科目'), Parameter('分数')], [
                    Assignment(IndexAccess(MemberAccess(I('自'), '成绩'), I('科目')), I('分数')),
                ]),
                MethodDefinition('取总分', [], [
                    VarDecl('s', NumberLiteral(0)),
                    ForeachStmt('项', MemberAccess(I('自'), '成绩的项'), [
                        Assignment(I('s'), BinaryOp('+', I('s'), IndexAccess(I('项'), NumberLiteral(1)))),
                    ]),
                    ReturnStmt(I('s')),
                ], return_type='数'),
                MethodDefinition('取平均分', [], [
                    IfStmt(BinaryOp('==', MemberAccess(I('自'), '成绩的长度'), NumberLiteral(0)),
                           [ReturnStmt(NumberLiteral(0.0))]),
                    ReturnStmt(BinaryOp('/', MemberAccess(I('自'), '取总分', True, []),
                                        MemberAccess(I('自'), '成绩的长度'))),
                ], return_type='数'),
                # 实现接口 可打印 的 字符串化——必须真给实现，否则 ABC 会拦住
                # 实例化（这条本身也是 Task 4 抽象方法真生效的反证）
                MethodDefinition('字符串化', [], [
                    ReturnStmt(BinaryOp('+', StringLiteral('学生'), MemberAccess(I('自'), '学号'))),
                ], return_type='串'),
                # 显式 `自` 形参落到实现类方法上
                MethodDefinition('自报', [Parameter('自')], [ReturnStmt(MemberAccess(I('自'), '学号'))], return_type='串'),
            ],
        )
        return Module([接口, 接口自, 人, 学生])

    def _gen(self):
        module = self._build_module()
        return CodeGenerator().generate(module)

    def _exec(self):
        g = {'__name__': '__main__'}
        exec(compile(self._gen(), '<l2oop>', 'exec'), g)
        return g

    # ---- Task 1: 的项 / 的长度 ----
    def test_的项_maps_to_items_semantically(self):
        """产物字符串 + 运行期双证：的项 必须迭代出 (k,v) 二元组，项[1] 才拿得到分数"""
        code = self._gen()
        assert 'self.成绩.items()' in code
        assert '的项' not in code
        g = self._exec()
        s = g['学生']('张三', 22, '2026001')
        s.录入成绩('语文', 88); s.录入成绩('数学', 92)
        assert s.取总分() == 180   # 88+92：只有 .items() 才让 项[1] 是分数

    def test_的长度_maps_to_len(self):
        code = self._gen()
        assert 'len(self.成绩)' in code
        assert '的长度' not in code
        g = self._exec()
        s = g['学生']('张三', 22, '2026001')
        s.录入成绩('语文', 88); s.录入成绩('数学', 92)
        assert s.取平均分() == 90.0            # (88+92)/len==2
        assert g['学生']('李四', 25, 'x').取平均分() == 0.0   # 空字典走 len()==0 分支

    # ---- Task 2: 自 -> self（形参 / 实参 / 表达式三处一致）----
    def test_自_param_and_body_both_self(self):
        code = self._gen()
        # 构造形参不重复注入 self；构造体内 自之姓名 归一成 self.姓名
        assert 'self.姓名 = 姓名' in code
        assert 'def __init__(self, self' not in code
        g = self._exec()
        s = g['学生']('张三', 22, '2026001')
        assert s.取姓名() == '张三'   # 自 绑定 self，取姓名走继承

    def test_显式自形参被吞掉(self):
        code = self._gen()
        assert 'def 自报(self)' in code and 'def 自报(self, 自' not in code
        g = self._exec()
        assert g['学生']('张三', 22, '2026001').自报() == '2026001'

    # ---- Task 3: 构造 调用侧 -> __init__ ----
    def test_人之构造_calls_parent_init(self):
        code = self._gen()
        assert '人.__init__(self, 姓名, 年龄)' in code   # 不是 人.构造(...)
        g = self._exec()
        s = g['学生']('张三', 22, '2026001')
        assert s.姓名 == '张三' and s.年龄 == 22   # 父类 __init__ 真被调到

    # ---- Task 4: 接口 -> ABC + @abstractmethod ----
    def test_interface_emits_abc(self):
        code = self._gen()
        assert 'class 可打印(ABC):' in code
        assert '@abstractmethod' in code
        g = self._exec()
        with pytest.raises(TypeError):
            g['可打印']()   # 抽象方法拦住实例化

    def test_接口带自形参不重复注入(self):
        code = self._gen()
        assert 'def 打印(self)' in code and 'def 打印(self, 自)' not in code

    def test_继承与接口都进基类表(self):
        assert 'class 学生(人, 可打印):' in self._gen()


class TestBackendParity:
    """v7 新单 B（第 4 票·任务 5）：src 与 unified 两后端的 OOP 口径必须一致。

    unified 后端补了 InterfaceDefinition 分支后，仍靠这里逐项断言两边的三张
    口径表相等——改一边忘另一边会在本用例当场打红，防止「同一份源码两个后端
    语义不同」重新滋生。
    """

    def _pair(self):
        from code_generator import PythonCodeGenerator
        from code_generator_unified import UnifiedCodeGenerator
        return PythonCodeGenerator, UnifiedCodeGenerator

    def test_self_names_match(self):
        src, uni = self._pair()
        assert tuple(src._SELF_NAMES) == tuple(uni._SELF_NAMES)

    def test_ctor_names_match(self):
        src, uni = self._pair()
        assert tuple(src._CTOR_NAMES) == tuple(uni._CTOR_NAMES)

    def test_member_suffix_map_match(self):
        src, uni = self._pair()
        assert tuple(src._MEMBER_SUFFIX_MAP) == tuple(uni._MEMBER_SUFFIX_MAP)

    def test_unified_interface_not_silently_dropped(self):
        """改前：unified 把 `接 X:` 掉进兜底、只 print 警告、产物里没有 class。
        改后：必须发射出 class X(ABC) + @abstractmethod。"""
        from ast_nodes_v3 import Module, InterfaceDefinition, MethodSignature, Parameter
        from code_generator_unified import UnifiedCodeGenerator
        mod = Module([InterfaceDefinition('可打印', [MethodSignature('字符串化', [], '串', None)])])
        code = UnifiedCodeGenerator().generate(mod)
        assert 'class 可打印(ABC):' in code
        assert '@abstractmethod' in code
        assert '未知语句类型' not in code

    def test_unified_self_and_suffix_resolved(self):
        """unified _resolve_name 同样把 自→self、成绩的项→.items()（类方法内）"""
        from code_generator_unified import UnifiedCodeGenerator
        g = UnifiedCodeGenerator()
        g._in_class_method = True
        assert g._resolve_name('自') == 'self'
        assert g._resolve_name('自.姓名') == 'self.姓名'
        assert g._resolve_name('成绩的项') == '成绩.items()'
        assert g._resolve_name('自.成绩的长度') == 'len(self.成绩)'


# =============================================================================
# v7 新单 B（第 2 票）：L2 语句层 OOP 修复 —— 按裁决 A~E 分类
#
# 覆盖 examples/L2_wenyan/学生模块.light 与 主程序.light 里踩到的语句层缺陷。
# 断言口径：能由 parser 单独决定的（AST 形状）就断 AST，避免与并行的 codegen
# 票互相打红；只有已定稿的产物形态才断生成代码字符串。
# =============================================================================

def _parse_ok(code: str):
    """只跑 parser，返回 Module（语句层测试的首选断言对象）"""
    return LightParser().parse(code)


class TestJueyiA类体成员严格化:
    """裁决 A：类体/接口体成员分派不再 `else: break` 静默漏出，
    并补上 L0 的 `段` 与 `设` 两个引导词。"""

    def test_类体内段被识别为方法而非漏到模块级(self):
        code = """
类 人:
  段 介绍():
    输出("hi")
"""
        result = _compile_ok(code)
        assert 'class 人:' in result
        assert 'def 介绍(self)' in result
        # 改前：类体循环不认 `段`，方法漏成模块级 def（PARSE-OK 且无诊断）
        assert '\ndef 介绍' not in result

    def test_类体内设带初值成为类字段(self):
        code = """
类 人:
  设 总数: 数 = 0
  段 介绍():
    输出("hi")
"""
        result = _compile_ok(code)
        assert 'class 人:' in result
        # 源码自带注解 `: 数`，所以类字段带注解发射（`数` → float，见
        # src/keywords.py BUILTIN_TYPES）。此前这条断言写成 `'总数 = 0'`，
        # 把自己输入里的注解漏掉了，属于断言写错而非产物错。
        assert '总数: float = 0' in result
        # 改前：`设` 同样漏到模块级
        assert '\n总数: float = 0' not in result

    def test_类体内设无初值不报错(self):
        module = _parse_ok("""
类 人:
  设 姓名: 串
  设 年龄: 数
  段 介绍():
    输出("hi")
""")
        cls = module.statements[0]
        names = [a.name for a in cls.attributes]
        assert '姓名' in names and '年龄' in names

    def test_接口体内段被识别为抽象方法(self):
        code = """
接 可打印:
  段 字符串化() -> 串
"""
        result = _compile_ok(code)
        assert 'class 可打印(ABC):' in result
        assert '@abstractmethod' in result
        assert 'def 字符串化(self)' in result

    def test_类体内未知引导词必须显式报错(self):
        code = """
类 人:
  打印 "我不是成员声明"
"""
        msg = _compile_error(code)
        # 改前：静默 break，错误被吞掉；改后：明确指出不支持的成员引导词
        assert '类体内不支持的成员声明' in msg

    def test_接口体内未知引导词必须显式报错(self):
        code = """
接 可打印:
  打印 "我不是成员声明"
"""
        msg = _compile_error(code)
        assert '接口体内不支持的成员声明' in msg

    def test_无成员的类仍可解析(self):
        """严格化不能把空类体/占位类体打红"""
        _compile_ok("""
类 空类:
  过
""")


class TestJueyiB继承与接口列表:
    """裁决 B：`接` 作为 `实现` 的同义词；`承`/`实现`/`接` 均支持逗号多名。"""

    def test_承接组合(self):
        code = """
接 可打印:
  段 字符串化() -> 串

类 人:
  段 介绍():
    输出("hi")

类 学生 承 人 接 可打印:
  段 字符串化() -> 串:
    返 "s"
"""
        result = _compile_ok(code)
        assert 'class 学生(人, 可打印):' in result

    def test_只写接(self):
        module = _parse_ok("""
类 学生 接 可打印:
  段 介绍():
    输出("hi")
""")
        cls = module.statements[0]
        assert cls.interfaces == ['可打印']
        assert not cls.base_classes

    def test_承支持逗号多名(self):
        module = _parse_ok("""
类 学生 承 人, 可打印:
  段 介绍():
    输出("hi")
""")
        assert _parse_ok
        cls = module.statements[0]
        assert cls.base_classes == ['人', '可打印']

    def test_接支持逗号多名(self):
        module = _parse_ok("""
类 学生 承 人 接 可打印, 可序列化:
  段 介绍():
    输出("hi")
""")
        cls = module.statements[0]
        assert cls.base_classes == ['人']
        assert cls.interfaces == ['可打印', '可序列化']

    def test_无继承子句的类名不被吞(self):
        """`承/接` 进停止词表后，普通类头必须仍然完整取到类名"""
        module = _parse_ok("""
类 接口测试:
  段 介绍():
    输出("hi")
""")
        assert module.statements[0].name == '接口测试'


class TestJueyiC设无初值:
    """裁决 C：`设 名: 类型`（无初值）—— docs/L2_文言体语法规范_v4.0.md:599-600, 622-623"""

    def test_模块级设无初值(self):
        module = _parse_ok("设 姓名: 串\n")
        vd = module.statements[0]
        assert vd.name == '姓名'
        assert vd.value is None            # 改前：无条件报「期望'为'或'等于'」
        assert vd.type_annotation is not None

    def test_函数内设无初值(self):
        module = _parse_ok("""
段 甲():
  设 姓名: 串
  返 1
""")
        assert module.statements[0].body[0].value is None

    def test_设有初值仍然正常(self):
        result = _compile_ok("设 年龄: 数 = 18\n")
        assert '18' in result

    def test_设缺类型且缺初值仍应报错(self):
        """无初值只在「有类型标注」时放行，裸 `设 x` 不能被顺带放宽"""
        msg = _compile_error("设 姓名\n")
        assert '期望' in msg or '错误' in msg or 'ParseError' in msg


class TestJueyiD匹配默认分支与布尔守卫:
    """裁决 D：`其他:` → `case _:`；`情况 <布尔表达式>:` → `case _ if ...:`"""

    def test_其他生成通配分支(self):
        code = """
配 x:
  情况 1:
    输出("一")
  其他:
    输出("其他")
"""
        result = _compile_ok(code)
        assert 'case _:' in result

    def test_其他仍可作普通变量名(self):
        """`其他` 只在 parser 侧识别，未提升为关键字，不能打断已有代码"""
        result = _compile_ok("设 其他 = 1\n输出(其他)\n")
        assert '其他' in result

    def test_情况后布尔表达式变守卫(self):
        code = """
配 真:
  情况 a >= 90:
    输出("A")
  其他:
    输出("B")
"""
        result = _compile_ok(code)
        assert 'case _ if' in result
        assert '>=' in result

    def test_情况后裸标识符仍是捕获模式(self):
        """不因主体是 `真` 就把所有 `情况` 读成布尔——判据是模式后是否跟比较/逻辑运算符"""
        code = """
配 x:
  情况 a:
    输出("捕获")
"""
        result = _compile_ok(code)
        assert 'case a:' in result
        assert 'case _ if' not in result

    def test_情况字面量不受影响(self):
        code = """
配 x:
  情况 "A（优秀）":
    输出(1)
  其他:
    输出(2)
"""
        result = _compile_ok(code)
        assert 'case "A（优秀）":' in result or "case 'A（优秀）':" in result


class TestJueyiE遍历为连接词:
    """裁决 E：`遍 <可迭代表达式> 为 项:` —— 语序由连接词决定，
    `为`/`之为` 表示「可迭代对象在前」，此处的 `为` 不得被吞成 `==`。"""

    def _foreach(self, code: str):
        module = _parse_ok(code)
        return module.statements[-1]

    def test_为后是循环变量而非等号比较(self):
        """学生模块.light:39 同形：改前 → `for 自 in (self.成绩.items() == 项)`"""
        fs = self._foreach("""
遍 自之成绩的项 为 项:
  输出(项)
""")
        var = fs.variable
        names = list(var) if isinstance(var, (list, tuple)) else [var]
        assert names == ['项']

    def test_为搭配函数调用(self):
        result = _compile_ok("""
遍 范围(1, 10) 为 i:
  输出(i)
""")
        assert 'for i in range(1, 10):' in result
        assert '==' not in result

    def test_为搭配裸名(self):
        """主程序.light:33 同形：`遍 学生列表 为 s:`"""
        result = _compile_ok("""
设 学生列表 = []
遍 学生列表 为 s:
  输出(s)
""")
        assert 'for s in 学生列表:' in result

    def test_之为不受影响(self):
        result = _compile_ok("""
设 列表 = []
遍 列表 之为 x:
  输出(x)
""")
        assert 'for x in 列表:' in result

    def test_变量在前的之连接词不受影响(self):
        """`之` 属变量在前档，语序不能被 `为` 的前瞻误伤"""
        result = _compile_ok("""
设 列表 = []
遍 x 之 列表:
  输出(x)
""")
        assert 'for x in 列表:' in result

    def test_多变量之连接词不受影响(self):
        result = _compile_ok("""
设 字典 = {}
遍 k, v 之 字典:
  输出(k)
""")
        assert 'for k, v in 字典:' in result


class TestJueyiOOP成员赋值目标:
    """裁决 A~E 落地过程中必须一并修的语句层同族缺陷：
    `自之X = Y` / `自之X[i] = Y` 作为赋值左值。"""

    def test_自之属性赋值(self):
        """学生模块.light:15 同形。改前：ParseError「赋值需要使用「设」或「令」关键字」"""
        result = _compile_ok("""
类 人:
  段 构造(姓名):
    自之姓名 = 姓名
""")
        assert 'self.姓名 = 姓名' in result
        # 改前旧路径把 `之` 粘进属性名：self.之姓名（静默错译）
        assert 'self.之姓名' not in result

    def test_自之属性带索引赋值(self):
        """学生模块.light:35 同形：`自之成绩[科目] = 分数`"""
        result = _compile_ok("""
类 人:
  段 录入(科目, 分数):
    自之成绩[科目] = 分数
""")
        assert 'self.成绩[科目] = 分数' in result

    def test_普通标识符之成员赋值(self):
        result = _compile_ok("""
段 甲(obj):
  obj之字段 = 1
""")
        assert 'obj.字段 = 1' in result

    def test_点号成员赋值未被破坏(self):
        result = _compile_ok("""
段 甲(obj):
  obj.字段 = 1
""")
        assert 'obj.字段 = 1' in result


# =============================================================================
# v7 新单 B（补票）：两处静默错译
#   缺陷 1：`导 X 出 A, B` 未生成 from-import
#   缺陷 2：`终:` 之后的同级语句被吞进 finally 块
#
# 断言标准照 TestContainsOperator：断的是**语义 / 结构**，不是「字符串里出现
# 了某个词」。缺陷 2 用 ast 结构断言 finally 块的成员，并同时断言错误形态
# （兄弟语句落进 finalbody）**不**出现。
# =============================================================================


def _ast_of(code: str):
    import ast
    return ast.parse(code)


class TestB缺陷1_导X出符号是from_import:
    """`导 X 出 A, B, C` 必须是 from-import，而不是 import X + __all__=[...]

    根因：`_parse_import_stmt` 收完模块名后只识别 `从`（倒装 from-import），
    不识别正装的 `出`。于是 `导 X 出 A, B` 只消费成 `导 X`，剩下的 `出 A, B`
    落回语句分发被当成**独立的导出声明**，产出
        import X
        __all__ = ['A', 'B']
    两处都错：A/B 在导入方一个名字都没绑定（用到就 NameError），而 __all__
    是**导出方**声明对外暴露什么用的，写在导入方毫无意义。解析/代码生成/
    python compile 全过，只有运行期才炸 —— 典型静默错译。
    """

    def test_导X出多符号生成from_import(self):
        result = _compile_ok('导 学生模块 出 人, 学生, 可打印\n')
        assert 'from 学生模块 import 人, 学生, 可打印' in result
        # 错误形态必须不出现
        assert 'import 学生模块\n' not in result
        assert '__all__' not in result

    def test_导入X出单符号(self):
        result = _compile_ok('导入 学生模块 出 人\n')
        assert 'from 学生模块 import 人' in result
        assert '__all__' not in result

    def test_导X出符号绑定了名字_运行期无NameError(self):
        """判别性：把 from-import 之外的名字用起来，编译产物的语义结构应正确。

        这里不真正 import（模块不一定存在），只断言产物是 from-import 结构，
        由 .scratch 的 b_runtime.py 做真正的 exec 绑定验证。
        """
        result = _compile_ok('导 学生模块 出 学生\n')
        tree = _ast_of(result)
        import ast
        froms = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        assert any(n.module == '学生模块'
                   and [a.name for a in n.names] == ['学生'] for n in froms)
        # 不得出现 `import 学生模块` 这种 plain import
        plains = [n for n in ast.walk(tree) if isinstance(n, ast.Import)]
        assert all('学生模块' not in a.name for n in plains for a in n.names)

    def test_导X出A为别名(self):
        result = _compile_ok('导 学生模块 出 人 为 P\n')
        assert 'from 学生模块 import 人 as P' in result
        assert '__all__' not in result

    def test_语句开头的出仍是导出声明(self):
        """回归护栏：句首的 `出 A, B` 是导出声明，语义与 import 无关，保持 __all__。"""
        result = _compile_ok('段 甲():\n    返 1\n出 甲\n')
        assert "__all__ = ['甲']" in result
        # 不得误判为 from-import
        import ast as _a
        for _n in _a.walk(_a.parse(result)):
            if isinstance(_n, _a.ImportFrom):
                assert '甲' not in [x.name for x in _n.names]

    def test_长词导出声明不受影响(self):
        result = _compile_ok('导出 人, 学生\n')
        assert "__all__ = ['人', '学生']" in result

    def test_学生模块示例的出仍是__all__(self):
        """examples/L2_wenyan/学生模块.light:61 的 `出 人, 学生, 可打印`
        是导出方声明，必须仍生成 __all__（该处不得被本次修复波及）。"""
        p = os.path.join(os.path.dirname(__file__), '..',
                         'examples', 'L2_wenyan', '学生模块.light')
        with open(p, encoding='utf-8') as f:
            result = _compile_ok(f.read())
        assert "__all__ = ['人', '学生', '可打印']" in result


class TestB缺陷2_finally块正确收束:
    """`终:` 块必须在 DEDENT 处收束，其后的同级语句不得被吞进 finally。

    根因：finally 块过去直接调 `_parse_body()`，而未先消耗本块 INDENT。
    _parse_body 的 depth 契约要求调用者已消耗 INDENT；直接调用时本块 INDENT
    被记成嵌套 depth，块结束的 DEDENT 只把 depth 减回 0 而不停止，后续兄弟
    语句被并入 finally。try/catch 块「碰巧」能停是因为其后紧跟 捕/终 关键字
    触发了 _parse_body 的 break；finally 是最后一个子句，其后是普通语句，
    没有任何 break 条件。

    断言用 ast 结构：finalbody 里应只含 finally 自己的语句，兄弟语句应在
    try 节点之外（函数体/循环体层级）。
    """

    _SRC = ('段 主():\n'
            '    试:\n'
            '        打印 "T"\n'
            '    捕 e:\n'
            '        打印 "C"\n'
            '    终:\n'
            '        打印 "F"\n'
            '    打印 "A1"\n'
            '    打印 "A2"\n')

    def _try_node(self, code):
        import ast
        lines = code.splitlines()
        idx = [k for k, l in enumerate(lines) if l.strip() == 'finally:']
        assert idx, 'no finally: in output'
        for k in idx:
            ind = len(lines[k]) - len(lines[k].lstrip())
            j2 = k + 1
            block = []
            while j2 < len(lines):
                l = lines[j2]
                if not l.strip():
                    j2 += 1
                    continue
                cur = len(l) - len(l.lstrip())
                if cur <= ind:
                    break
                block.append(l)
                j2 += 1
            joined = chr(10).join(block)
            assert '学生排名' not in joined
            assert 'sorted(' not in joined


class TestB补票1_类字段注解:
    """类体 设 名: 类型 必须落成类级注解, 无初值不得退化成 名 = None.

    规范 docs/L2_文言体语法规范_v4.0.md:599-600, 622-623
    修复点 src/code_generator.py::_generate_class_definition
    """

    _SRC = ("类 人:\n"
            "    设 姓名: 串\n"
            "    设 总数: 数 = 0\n"
            "    段 构造(姓名: 串):\n"
            "        自之姓名 = 姓名\n")

    _SRC2 = ("类 容器:\n"
             "    设 标签: 串\n"
             "    段 构造():\n"
             "        自之值 = 1\n")

    def _gen1(self):
        code = _compile_ok(self._SRC)
        ns = {}
        exec(compile(code, "gen_annot1", "exec"), ns)
        return code, ns["人"]

    def test_annot_pure_no_assign(self):
        code, _ = self._gen1()
        assert "姓名: str" in code
        assert "姓名 = None" not in code

    def test_annot_with_default_kept(self):
        code, _ = self._gen1()
        assert "总数: float = 0" in code

    def test_annot_creates_no_class_attr(self):
        code, C = self._gen1()
        assert "姓名" in getattr(C, "__annotations__", {})
        assert "姓名" not in vars(C)

    def test_instance_attrs_still_work(self):
        code, C = self._gen1()
        a = C("甲")
        b = C("乙")
        assert getattr(a, "姓名") == "甲"
        assert getattr(b, "姓名") == "乙"
        assert "姓名" in a.__dict__

    def test_unset_pure_annot_raises(self):
        code = _compile_ok(self._SRC2)
        assert "标签: str" in code
        assert "标签 = None" not in code
        ns = {}
        exec(compile(code, "gen_annot2", "exec"), ns)
        obj = ns["容器"]()
        with pytest.raises(AttributeError):
            getattr(obj, "标签")


class TestB补票2_的X后缀改写:
    """的项 / 的长度 在成员路径上必须与裸标识符路径共用同一张改写表.

    改前实测 self.成绩(的项) / self.成绩(的长度): 能编译, 运行时才炸.
    修复点 src/code_generator.py::_match_orphan_suffix_call
    """

    _SRC = ("类 学生:\n"
            "    设 成绩: 典\n"
            "    段 构造():\n"
            "        自之成绩 = {}\n"
            "    段 取总分():\n"
            "        设 s = 0\n"
            "        遍 自之成绩的项 为 项:\n"
            "            s = s + 项[1]\n"
            "        返 s\n"
            "    段 取个数():\n"
            "        返 自之成绩的长度\n")

    def _gen(self):
        code = _compile_ok(self._SRC)
        ns = {}
        exec(compile(code, "gen_desuffix", "exec"), ns)
        return code, ns["学生"]

    def test_no_orphan_suffix_arg_shape(self):
        code, _ = self._gen()
        assert "成绩(的项" not in code
        assert "成绩(的长度" not in code

    def test_deitems_to_items(self):
        code, _ = self._gen()
        assert "self.成绩.items()" in code

    def test_delen_to_len(self):
        code, _ = self._gen()
        assert "len(self.成绩)" in code

    def test_runtime_items_yields_pairs(self):
        code, C = self._gen()
        obj = C()
        d = getattr(obj, "成绩")
        d[1] = 80
        d[2] = 90
        assert getattr(obj, "取总分")() == 170

    def test_runtime_len_is_length(self):
        code, C = self._gen()
        obj = C()
        d = getattr(obj, "成绩")
        d[1] = 80
        d[2] = 90
        assert getattr(obj, "取个数")() == 2

    def test_bare_identifier_path_not_regressed(self):
        code = _compile_ok("段 甲():\n    设 d: 典 = {}\n    d[1] = 1\n    d[2] = 2\n    返 d的长度\n")
        assert "len(d)" in code
        ns = {}
        exec(compile(code, "gen_bare_len", "exec"), ns)
        assert ns["甲"]() == 2

    def test_user_name_containing_deitems_not_split(self):
        code = _compile_ok("段 甲():\n    设 目的项 = 5\n    返 目的项\n")
        assert "目.items()" not in code
        ns = {}
        exec(compile(code, "gen_false_pos", "exec"), ns)
        assert ns["甲"]() == 5


class TestL0SingleCharClassKeywords:
    """v7 新单 E：L0 v4.0 单字类关键字 `性`(属性) / `构`(构造) / `新`(实例化)。

    被测输入 examples/L0_core/06_类_面向对象.light 用的就是这一套。
    `性`/`构`/`新` **不是**保留字（是高频构词字，升为关键字会在词法层切碎
    性能/结构/新增 之类的标识符），由解析器按位置形状识别，所以这里既断产物
    形状、也 exec 起来真跑，确认没有「编译过、一跑就炸」。
    """

    _SRC = (
        "类 动物：\n"
        "  性 名称\n"
        "  性 年龄\n"
        "\n"
        "  构 接收 名称, 年龄：\n"
        "    己名称 为 名称\n"
        "    己年龄 为 年龄\n"
        "\n"
        "  段 描述：\n"
        "    返 己名称\n"
        "\n"
        "类 狗 承 动物：\n"
        "  性 品种\n"
        "\n"
        "  构 接收 名称, 年龄, 品种：\n"
        "    父.构(名称, 年龄)\n"
        "    己品种 为 品种\n"
        "\n"
        "设 旺财 为 新 狗(\"旺财\", 3, \"金毛\")\n"
    )

    def _gen(self):
        code = _compile_ok(self._SRC)
        ns = {}
        exec(compile(code, "gen_l0_oop", "exec"), ns)
        return code, ns

    def test_性_declares_instance_attr(self):
        code, ns = self._gen()
        assert "def __init__(self, 名称, 年龄)" in code
        assert "self.名称 = 名称" in code

    def test_构_is_init_not_a_plain_method(self):
        code, _ = self._gen()
        assert "def 构(" not in code

    def test_父构_calls_super_init(self):
        code, ns = self._gen()
        # 不能是 super().构(...)——那在 Python 里是 AttributeError
        assert "super().__init__(名称, 年龄)" in code
        assert "super().构(" not in code
        assert ns["旺财"].名称 == "旺财" and ns["旺财"].年龄 == 3

    def test_新_instantiates_class(self):
        code, ns = self._gen()
        assert '狗("旺财", 3, "金毛")' in code
        assert ns["旺财"].品种 == "金毛"

    def test_继承链可用(self):
        _, ns = self._gen()
        assert ns["旺财"].描述() == "旺财"

    def test_新_不吞普通标识符(self):
        """`新` 只在「新 + 标识符 + (」形状下才是实例化，别处仍是普通变量名"""
        code = _compile_ok("段 甲():\n    设 新 为 7\n    返 新\n")
        ns = {}
        exec(compile(code, "gen_xin_var", "exec"), ns)
        assert ns["甲"]() == 7

    def test_性能之类的标识符没被切碎(self):
        """`性`/`构` 未升为保留字的直接体现"""
        code = _compile_ok("段 甲():\n    设 性能 为 1\n    设 结构 为 2\n    返 性能 + 结构\n")
        ns = {}
        exec(compile(code, "gen_no_split", "exec"), ns)
        assert ns["甲"]() == 3


class TestMultiTargetAnnotation:
    """v7 新单 G：多目标带共享类型注解 `设 甲, 乙: 数 为 造()`。

    口径（用户裁定 broadcast）：Python 不允许 `甲, 乙: float = f()`（SyntaxError），
    所以注解**广播**成每个目标一条纯注解行，再发解包语句。无注解的多目标解包
    （语料里的真实形状 `设 表头, 数据 为 读取(...)`）行为完全不变。
    """

    def test_annotation_broadcasts_to_each_target(self):
        code = _compile_ok("段 甲():\n    设 a, b: 数 为 (1, 2)\n    返 a + b\n")
        assert "a: float" in code
        assert "b: float" in code
        assert "a, b = (1, 2)" in code
        # 关键：绝不能发 Python 里非法的 `a, b: float = ...`
        assert "a, b: float" not in code
        ns = {}
        exec(compile(code, "gen_g_annot", "exec"), ns)
        assert ns["甲"]() == 3

    def test_no_annotation_unchanged(self):
        """语料真实形状：无注解多目标解包，产物与从前一致"""
        code = _compile_ok("段 甲():\n    设 表头, 数据 为 (1, 2)\n    返 表头\n")
        assert "表头, 数据 = (1, 2)" in code
        assert ": float" not in code  # 没有注解就不该冒出任何注解行
        ns = {}
        exec(compile(code, "gen_g_plain", "exec"), ns)
        assert ns["甲"]() == 1

    def test_three_targets_annotation(self):
        code = _compile_ok("段 甲():\n    设 a, b, c: 整数 为 (1, 2, 3)\n    返 a + b + c\n")
        assert "a: int" in code and "b: int" in code and "c: int" in code
        assert "a, b, c = (1, 2, 3)" in code
        ns = {}
        exec(compile(code, "gen_g_three", "exec"), ns)
        assert ns["甲"]() == 6


class TestBytesLiteral:
    """v7 新单 H：字节串前缀 `b'...'` / `B'...'`。

    单 C 里明确挂账「b 另立单」——bytes 要语义正确需 codegen 配合。
    原先 b'abc' 被切成 IDENTIFIER('b')+STRING('abc') 发出 b("abc")，编译过、
    运行期 NameError；空的 b'' 在默认参数位置直接 ParseError。
    """

    def test_bytes_literal_emits_b_prefix(self):
        code = _compile_ok("设 x 为 b'abc'。\n")
        assert "x = b'abc'" in code
        assert "b(" not in code  # 绝不能是 b("abc") 那种函数调用错译
        ns = {}
        exec(compile(code, "gen_h_bytes", "exec"), ns)
        assert ns["x"] == b'abc'
        assert isinstance(ns["x"], bytes)

    def test_bytes_double_quote(self):
        code = _compile_ok('设 x 为 b"xy"。\n')
        ns = {}
        exec(compile(code, "gen_h_bytes2", "exec"), ns)
        assert ns["x"] == b'xy' and isinstance(ns["x"], bytes)

    def test_bytes_as_call_argument(self):
        code = _compile_ok("段 甲(数据):\n    返 数据\n设 x 为 甲(b'')。\n")
        assert "甲(b'')" in code
        ns = {}
        exec(compile(code, "gen_h_arg", "exec"), ns)
        assert ns["x"] == b'' and isinstance(ns["x"], bytes)

    def test_uppercase_B_prefix(self):
        code = _compile_ok("设 x 为 B'AB'。\n")
        ns = {}
        exec(compile(code, "gen_h_upper", "exec"), ns)
        assert ns["x"] == b'AB' and isinstance(ns["x"], bytes)

    def test_bytes_non_ascii_escaped(self):
        """非 ASCII 内容必须转成 \\xNN——`b"中文"` 直接写是 SyntaxError"""
        code = _compile_ok("设 x 为 b'中'。\n")
        ns = {}
        exec(compile(code, "gen_h_nonascii", "exec"), ns)
        assert ns["x"] == '中'.encode('utf-8') and isinstance(ns["x"], bytes)

    def test_bare_b_variable_unaffected(self):
        """裸变量 b（不贴引号）不受前缀判据影响"""
        code = _compile_ok("段 甲():\n    设 b 为 1\n    返 b\n")
        assert "b = 1" in code
        ns = {}
        exec(compile(code, "gen_h_bare", "exec"), ns)
        assert ns["甲"]() == 1

    def test_b_space_string_not_prefix(self):
        """b 与引号被逗号隔开：b 是独立标识符，不能被吃成 bytes 前缀"""
        # 不 exec（b 未定义）。断言必须收敛到发射出的那一行——产物前导 preamble
        # 本身就含 b' 子串，全文扫描会误报。
        code = _compile_ok("设 结果 为 拼接(b, \"x\")。\n")
        line = [ln for ln in code.splitlines() if ln.lstrip().startswith("结果 =")][0]
        assert '(b, "x")' in line                        # b 作为独立实参传入
        assert "(b'" not in line and '(b"' not in line    # 没被吃成 bytes 前缀


class TestChaoSuper:
    """v7 新单 I：`超` = super

    L2 v4.0 规范（docs/L2_文言体语法规范_v4.0.md:433/574/927）写的 super 是
    `超.方法()`，实现侧一直只认 `父`——规范承诺从未落地。原先 `超.构(...)`
    发出 `超.__init__(...)`，编译过、运行期 NameError（静默错编）。
    本单把 `超` 按形状接到 `父` 已有的通路上，两者完全等价。
    """

    _SRC = (
        "类 动物：\n"
        "  性 名称\n"
        "\n"
        "  构 接收 名称：\n"
        "    己名称 为 名称\n"
        "\n"
        "  段 描述：\n"
        "    返 己名称\n"
        "\n"
        "类 狗 承 动物：\n"
        "  性 品种\n"
        "\n"
        "  构 接收 名称, 品种：\n"
        "    %s\n"
        "    己品种 为 品种\n"
        "\n"
        "  段 详情：\n"
        "    返 %s\n"
        "\n"
        "设 旺财 为 新 狗(\"旺财\", \"金毛\")\n"
    )

    def _gen(self, ctor, meth):
        code = _compile_ok(self._SRC % (ctor, meth))
        ns = {}
        exec(compile(code, "gen_i_chao", "exec"), ns)
        return code, ns

    def test_chao_dot_ctor_is_super_init(self):
        code, ns = self._gen("超.构(名称)", "超.描述()")
        assert "super().__init__(名称)" in code
        assert "超.__init__" not in code     # 旧的静默错编形状
        assert ns["旺财"].名称 == "旺财"

    def test_chao_dot_plain_method(self):
        code, ns = self._gen("超.构(名称)", "超.描述()")
        assert "return super().描述()" in code
        assert ns["旺财"].详情() == "旺财"

    def test_chao_zhi_form(self):
        """文言体 `超 之 构(...)` 与点号形式等价（`之` 已废弃但仍兼容）"""
        code, ns = self._gen("超 之 构(名称)", "超 之 描述()")
        assert "super().__init__(名称)" in code
        assert ns["旺财"].详情() == "旺财"

    def test_chao_de_form(self):
        """`超 的 构(...)`——`的` 是当前推荐的成员访问符，必须与 `父 的 构` 等价"""
        de = _compile_ok(self._SRC % ("超 的 构(名称)", "超 的 描述()"))
        fu_de = _compile_ok(self._SRC % ("父 的 构(名称)", "父 的 描述()"))
        assert "super().__init__(名称)" in de
        assert de == fu_de
        ns = {}
        exec(compile(de, "gen_i_de", "exec"), ns)
        assert ns["旺财"].详情() == "旺财"


    def test_chao_matches_fu_byte_for_byte(self):
        """`超` 只是 `父` 的另一种写法：两者产物必须逐字节相同"""
        fu = _compile_ok(self._SRC % ("父.构(名称)", "父.描述()"))
        chao = _compile_ok(self._SRC % ("超.构(名称)", "超.描述()"))
        assert fu == chao

    def test_bare_chao_still_identifier(self):
        """裸 `超`（后面没有 . / 之）仍是普通变量，不能变成 super()"""
        code = _compile_ok("段 甲():\n    设 超 为 1\n    返 超\n")
        assert "超 = 1" in code
        assert "super()" not in code
        ns = {}
        exec(compile(code, "gen_i_bare", "exec"), ns)
        assert ns["甲"]() == 1

    def test_compound_words_with_chao_unaffected(self):
        """超时/超集 等复合词不受影响——这是 `超` 不升关键字的原因"""
        code = _compile_ok("段 甲():\n    设 超时 为 5\n    设 超集 为 7\n    返 超时 + 超集\n")
        assert "超时 = 5" in code and "超集 = 7" in code
        assert "super()" not in code
        ns = {}
        exec(compile(code, "gen_i_compound", "exec"), ns)
        assert ns["甲"]() == 12






if __name__ == '__main__':
    pytest.main([__file__, '-v'])