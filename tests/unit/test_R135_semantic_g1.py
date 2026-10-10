# -*- coding: utf-8 -*-
"""R135-A · L5 SemanticAnalyzer G1 适配层测试。

背景：`SemanticAnalyzer` 原本只认 `ast_unified.Module`，而 `light_parser_v3`
产出 `ast_nodes_v3.Module`（两套 AST 节点命名与结构都不同）→ `test_semantic.py`
整体 skip、编译链跳过语义分析（docs/known_issues.md G1）。

本文件固化适配层的**正例**（不误报）与**反例**（该报就报），并守住三条硬约束：
  1. 不向 v3 节点写回属性（ast_nodes_v3 全族 __slots__）；
  2. unified 路径行为不变（既有 visit_* 语义零回归）；
  3. 未知 v3 节点不抛异常（保守递归）。
"""

import os
import sys

import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SRC = os.path.join(_PROJECT_ROOT, 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from light_parser_v3 import LightParser          # noqa: E402
from ast_nodes_v3 import Module as V3Module      # noqa: E402
from semantic_analyzer import (                  # noqa: E402
    SemanticAnalyzer,
    V3_TO_UNIFIED,
    _is_known_callable,
    _is_v3_module,
)


@pytest.fixture
def parser():
    return LightParser()


def _分析(parser, code):
    """解析 + v3 语义分析，返回 (module, analyzer)。"""
    module = parser.parse(code)
    analyzer = SemanticAnalyzer(module)
    analyzer.visit_Module(module)
    return module, analyzer


class TestV3AdaptationPositive:
    """正例：合法光明代码不得有语义错误。"""

    def test_变量声明无错误(self, parser):
        module, analyzer = _分析(parser, '设 甲 为 1。')
        assert analyzer.v3_mode is True
        assert analyzer.errors == []

    def test_字符串与中文数字字面量无错误(self, parser):
        module, analyzer = _分析(parser, '设 甲 为 "你好"。设 乙 为 三 加 五。')
        assert analyzer.errors == []

    def test_段落定义与调用无错误(self, parser):
        code = '《计算》段(甲, 乙)：返回 甲 加 乙。\n设 结果 为 计算(1, 2)。'
        module, analyzer = _分析(parser, code)
        assert analyzer.errors == []

    def test_内建调用不误报为未定义(self, parser):
        """`打印`/`输出`/`显示` 是内置名，不是用户符号，不得报未定义。"""
        for code in ('打印("x")。', '输出("x")。', '显示("x")。'):
            _module, analyzer = _分析(parser, code)
            assert analyzer.errors == [], f'{code} 误报: {analyzer.errors}'

    def test_真值字面量不误报(self, parser):
        """解析器把 `真`/`假` 折成 Identifier('True'/'False')，不得当未定义符号。"""
        _module, analyzer = _分析(parser, '如果 真 那么：\n  打印 甲。\n结束。')
        # 只有 `甲` 未定义，`True` 本身不得报错
        assert all("'True'" not in str(e) and "'False'" not in str(e)
                   for e in analyzer.errors)

    def test_条件与循环变量不误报(self, parser):
        code = ('《总和》段(列表)：\n'
                '  设 累加 为 0。\n'
                '  遍历 项 在 列表：\n'
                '    遍历 数量 在 项：\n'
                '      返回 数量。\n'
                '  返回 累加。\n')
        _module, analyzer = _分析(parser, code)
        assert analyzer.errors == [], f'误报: {analyzer.errors}'


class TestV3AdaptationNegative:
    """反例：真语义错误必须被报出（证明分析器真跑）。"""

    def test_未定义符号被报出(self, parser):
        _module, analyzer = _分析(parser, '打印(乙)。')
        # 精确断言：恰好 1 条，且就是 `乙`（不用 >= 下界式，那是假绿形态）
        assert [str(e) for e in analyzer.errors] == ["未定义的符号 '乙'"]

    def test_未定义符号出现在二元运算(self, parser):
        _module, analyzer = _分析(parser, '设 甲 为 未知甲 加 未知乙。')
        assert sorted(str(e) for e in analyzer.errors) == [
            "未定义的符号 '未知乙'", "未定义的符号 '未知甲'"]

    def test_未定义函数调用被报出(self, parser):
        _module, analyzer = _分析(parser, '甲乙丙(1)。')
        assert any('甲乙丙' in str(e) for e in analyzer.errors), analyzer.errors

    def test_自定义段落可被后续调用解析(self, parser):
        """反例的反证：定义过的段落名不得被报未定义（证明符号表真入表）。"""
        code = '《我的段》段(甲)：\n  返回 甲。\n我的段(1)。'
        _module, analyzer = _分析(parser, code)
        assert all('我的段' not in str(e) for e in analyzer.errors), analyzer.errors


class TestV3HardConstraints:
    """硬约束：不写回节点、不回归 unified、未知节点不炸。"""

    def test_不向v3节点写回属性(self, parser):
        """v3 全族 __slots__：适配层若写回属性会 AttributeError。"""
        module, analyzer = _分析(parser, '设 甲 为 1。设 乙 为 2。')
        node = module.statements[0]
        # 分析前后节点属性集合完全一致（没有任何新增）
        assert not hasattr(node, 'symbol')
        assert not hasattr(node, 'inferred_type')
        assert not hasattr(node, 'scope_id')
        assert not hasattr(node, 'type')

    def test_v3模块判定(self, parser):
        module = parser.parse('设 甲 为 1。')
        assert isinstance(module, V3Module)
        assert _is_v3_module(module) is True
        assert _is_v3_module(None) is False

    def test_unified路径行为不变(self):
        """unified Module 仍走 module 上挂的符号表（R135-A 重构了符号表入口，
        用本用例锁住既有语义不被适配层带偏）。"""
        from ast_unified import (
            Module as UModule, VariableDeclaration, NumberLiteral,
            GlobalVariable, FunctionDefinition, Parameter, Block,
            ReturnStatement, BinaryOp, Identifier, TYPE_INT,
        )

        um = UModule()
        um.globals.append(GlobalVariable(name='全局量', initializer=NumberLiteral(value=5)))
        um.functions.append(FunctionDefinition(
            name='加一',
            parameters=[Parameter(name='甲', type=TYPE_INT)],
            return_type=TYPE_INT,
            body=Block(statements=[
                VariableDeclaration(name='乙', initializer=NumberLiteral(value=1)),
                ReturnStatement(value=BinaryOp(
                    left=Identifier(name='甲'), operator='+', right=Identifier(name='乙'))),
            ])))
        analyzer = SemanticAnalyzer(um)
        assert analyzer.v3_mode is False
        assert analyzer.analyze() is analyzer.errors      # 触发遍历
        # 符号表仍挂在 module 上（而不是分析器自带）
        # 注：unified 路径的既有行为是 __init__ 里 current_scope_id=0，
        #     再调 add_scope() 另建一个空作用域 1 —— 全局符号落在 0。
        assert '全局量' in um.scopes[0]
        assert '加一' in um.scopes[0]
        # 函数参数 / 函数体局部变量各自进了新作用域
        assert '甲' in um.scopes[2]
        assert '乙' in um.scopes[3]
        # 只有既有的「GlobalVariable 默认 void 类型」告警，无新增错误
        assert [str(e) for e in analyzer.errors] == [
            '类型不匹配（全局变量初始化）：期望 void，得到 int']

    def test_unified路径重复定义仍报错(self):
        """v3 口径是重绑定、不报；unified 口径保持原样、仍报。两种模式不得串味。"""
        from ast_unified import Module as UModule, GlobalVariable, NumberLiteral, TYPE_INT

        um = UModule()
        analyzer = SemanticAnalyzer(um)
        node = GlobalVariable(name='同名', type=TYPE_INT, initializer=NumberLiteral(value=1))
        assert analyzer.declare_symbol('同名', TYPE_INT, node) is not None
        # 同一作用域内再声明一次 → unified 口径必须报错（v3 口径不报）
        assert analyzer.declare_symbol('同名', TYPE_INT, node) is None
        assert any('已在当前作用域定义' in str(e) for e in analyzer.errors)

    def test_未知v3节点不抛异常(self, parser):
        """构造一个解析器产不出的节点名，验证保守递归兜底。"""
        import ast_nodes_v3 as v3

        class 未知节点(v3.ASTNode):
            __slots__ = ('child',)

            def __init__(self, child=None):
                super().__init__(0, 0)
                self.child = child

        module = parser.parse('设 甲 为 1。')
        module.statements.append(未知节点(child=v3.Identifier(name='未定义名')))
        analyzer = SemanticAnalyzer(module)
        analyzer.visit_Module(module)      # 不得抛异常
        assert any('未定义名' in str(e) for e in analyzer.errors)

    def test_可调用名识别表可用(self):
        assert _is_known_callable('打印') is True
        assert _is_known_callable('输出') is True
        assert _is_known_callable('True') is True
        assert _is_known_callable('绝不存在这个名字') is False
        assert _is_known_callable(None) is False

    def test_映射表覆盖主要v3节点(self):
        for v3名 in ('VarDecl', 'Paragraph', 'ParagraphCall', 'IfStmt',
                    'WhileStmt', 'ForeachStmt', 'ReturnStmt'):
            assert v3名 in V3_TO_UNIFIED

    def test_错误对象带行列信息(self, parser):
        module, analyzer = _分析(parser, '打印(乙)。')
        assert analyzer.errors[0].line >= 0


class TestCliIntegration:
    """接入编译链（判据 §3.4：至少 1 条路径调用语义分析）。"""

    def _run_lightc(self, source, *extra):
        import subprocess
        import tempfile

        lightc = os.path.join(_PROJECT_ROOT, 'cli', 'lightc.py')
        with tempfile.TemporaryDirectory(prefix='_r135_semantic_') as td:
            src = os.path.join(td, 'test.light')
            with open(src, 'w', encoding='utf-8') as f:
                f.write(source)
            p = subprocess.run(
                [sys.executable, lightc, src, '-o', os.path.join(td, 'out.py')] + list(extra),
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=60, cwd=_PROJECT_ROOT)
            return p.returncode, p.stdout, p.stderr

    def test_默认关闭时无语义警告(self):
        rc, out, err = self._run_lightc('打印(乙)。')
        assert rc == 0, (out, err)
        assert '语义警告' not in err

    def test_semantic开关报出未定义符号(self):
        rc, out, err = self._run_lightc('打印(乙)。', '--semantic')
        assert rc == 0, (out, err)          # 只警告、不阻断
        assert '未定义的符号' in err and '乙' in err, err

    def test_semantic开关对合法代码无警告(self):
        rc, out, err = self._run_lightc('设 甲 为 1\n打印(甲)。\n', '--semantic')
        assert rc == 0, (out, err)
        assert '语义警告' not in err, err

    def test_lightc仍无无参构造(self):
        """守住既有反跑判据（tests/test_lightc_cli.py）。"""
        with open(os.path.join(_PROJECT_ROOT, 'cli', 'lightc.py'), encoding='utf-8') as f:
            assert 'SemanticAnalyzer()' not in f.read()
