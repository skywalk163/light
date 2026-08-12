# -*- coding: utf-8 -*-
"""
第3周 错误信息与调试体验增强 测试

测试内容：
- LightError 格式化（含 fix_suggestions）
- format_source_context 增强
- format_error_with_context
- LightErrorFormatter
- DebugEngine 基本功能
- REPL 命令处理
"""

import sys
import os
import pytest

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# 3.1 错误格式测试
# =============================================================================

class TestLightErrorFormat:
    """测试 LightError 格式化"""

    def test_light_error_with_fix_suggestions(self):
        """测试带修复建议的 LightError"""
        from errors import LightError
        err = LightError(
            "未定义的变量",
            line=5,
            col=10,
            fix_suggestions=[
                '检查变量名拼写是否正确',
                '在使用变量前先声明: 设 变量名 为 值',
            ]
        )
        assert "未定义的变量" in str(err)
        assert "修复建议" in str(err)
        assert "检查变量名拼写是否正确" in str(err)
        assert err.fix_suggestions == [
            '检查变量名拼写是否正确',
            '在使用变量前先声明: 设 变量名 为 值',
        ]

    def test_light_error_with_source_lines(self):
        """测试带源代码行的 LightError"""
        from errors import LightError
        source_lines = ['设 甲 为 10', '打印(甲)', '打印(乙)']
        err = LightError(
            "未定义的变量: 乙",
            line=3,
            col=4,
            source_lines=source_lines,
        )
        assert err.source_lines == source_lines
        assert "未定义的变量" in str(err)

    def test_light_error_no_fix_suggestions(self):
        """测试不带修复建议的 LightError"""
        from errors import LightError
        err = LightError("简单错误")
        assert err.fix_suggestions == []

    def test_light_error_with_hint(self):
        """测试带提示的 LightError"""
        from errors import LightError
        err = LightError("错误", hint="试试这个", fix_suggestions=['建议1'])
        assert "提示" in str(err)
        assert "试试这个" in str(err)
        assert "修复建议" in str(err)


class TestLexerError:
    """测试 LexerError"""

    def test_lexer_error_with_fix_suggestions(self):
        """测试 LexerError 自动匹配修复建议"""
        from errors import LexerError
        err = LexerError("未闭合的字符串: 以 ' 开头的字符串缺少匹配的引号", line=1, col=1)
        assert "词法分析错误" in str(err)
        # 应自动匹配修复建议
        assert len(err.fix_suggestions) > 0
        assert "闭合引号" in err.fix_suggestions[0]

    def test_lexer_error_unknown_char(self):
        """测试未知字符的修复建议"""
        from errors import LexerError
        err = LexerError("未知字符: '@'", line=2, col=5)
        assert "词法分析错误" in str(err)
        assert len(err.fix_suggestions) > 0
        assert "非法字符" in err.fix_suggestions[0]

    def test_lexer_error_no_match(self):
        """测试无匹配的修复建议"""
        from errors import LexerError
        err = LexerError("一些其他错误", line=1, col=1)
        # 应返回空列表
        assert err.fix_suggestions == []


class TestSemanticError:
    """测试 SemanticError"""

    def test_semantic_error_undefined_var(self):
        """测试未定义变量修复建议"""
        from errors import SemanticError
        err = SemanticError("未定义的变量: 甲", line=1, col=1)
        assert "语义错误" in str(err)
        assert len(err.fix_suggestions) > 0
        assert "检查变量名拼写是否正确" in err.fix_suggestions[0]

    def test_semantic_error_type_mismatch(self):
        """测试类型不匹配修复建议"""
        from errors import SemanticError
        err = SemanticError("类型不匹配: 期望整数, 实际字符串", line=5, col=10)
        assert "语义错误" in str(err)
        assert len(err.fix_suggestions) > 0
        assert any("类型" in s for s in err.fix_suggestions)


class TestFormatSourceContext:
    """测试 format_source_context"""

    def test_format_source_context_basic(self):
        """测试基本源代码上下文格式化"""
        from errors import format_source_context
        source = "第一行\n第二行\n第三行\n第四行\n第五行"
        result = format_source_context(source, 3, 2)
        assert "第二行" in result
        assert "第三行" in result
        assert "第四行" in result
        assert "→" in result  # 错误行标记
        assert "此处" in result  # 列号指示

    def test_format_source_context_no_col(self):
        """测试无列号的源代码上下文"""
        from errors import format_source_context
        source = "行1\n行2\n行3"
        result = format_source_context(source, 2)
        assert "行1" in result
        assert "行2" in result
        assert "行3" in result
        assert "错误位置" in result

    def test_format_source_context_empty(self):
        """测试空源代码"""
        from errors import format_source_context
        result = format_source_context("", 1)
        assert result == ""

    def test_format_source_context_out_of_range(self):
        """测试越界行号"""
        from errors import format_source_context
        source = "行1\n行2"
        result = format_source_context(source, 10)
        assert result == ""

    def test_format_source_context_line_1(self):
        """测试第一个行"""
        from errors import format_source_context
        source = "第一行\n第二行"
        result = format_source_context(source, 1, 1)
        assert "第一行" in result
        assert "此处" in result


class TestFormatErrorWithContext:
    """测试 format_error_with_context"""

    def test_format_error_with_context(self):
        """测试完整错误格式化"""
        from errors import format_error_with_context, LexerError
        source = "设 甲 为 10\n打印(甲)\n打印(乙)"
        err = LexerError("未闭合的字符串", line=3, col=1)
        result = format_error_with_context(err, source, 3, 1)
        assert "LexerError" in result
        assert "未闭合的字符串" in result
        assert "源代码上下文" in result

    def test_format_error_without_source(self):
        """测试无源代码的错误格式化"""
        from errors import format_error_with_context, LightError
        err = LightError("简单错误")
        result = format_error_with_context(err)
        assert "LightError" in result
        assert "简单错误" in result


class TestLightErrorFormatter:
    """测试 LightErrorFormatter"""

    def test_format_light_error(self):
        """测试格式化 LightError"""
        from errors import LightErrorFormatter, LightError
        err = LightError("测试错误", line=1, col=1,
                        fix_suggestions=['建议1', '建议2'])
        result = LightErrorFormatter.format(err)
        assert "LightError" in result
        assert "测试错误" in result
        assert "修复建议" in result
        assert "建议1" in result

    def test_format_regular_exception(self):
        """测试格式化普通异常"""
        from errors import LightErrorFormatter
        try:
            1 / 0
        except Exception as e:
            result = LightErrorFormatter.format(e)
            assert "ZeroDivisionError" in result
            assert "division by zero" in result

    def test_format_with_source(self):
        """测试带源代码的格式化"""
        from errors import LightErrorFormatter, LexerError
        source = "设 甲 为 10\n打印(甲)\n打印(乙)"
        err = LexerError("未闭合的字符串", line=3, col=1)
        result = LightErrorFormatter.format_with_source(err, source, 3, 1)
        assert "LexerError" in result
        assert "源代码上下文" in result

    def test_get_fix_suggestions(self):
        """测试获取修复建议"""
        from errors import LightErrorFormatter
        suggestions = LightErrorFormatter.get_fix_suggestions(
            'LexerError', '未闭合的字符串')
        assert len(suggestions) > 0
        assert "闭合引号" in suggestions[0]

    def test_get_fix_suggestions_no_match(self):
        """测试无匹配的修复建议"""
        from errors import LightErrorFormatter
        suggestions = LightErrorFormatter.get_fix_suggestions(
            'LexerError', '一些不匹配的错误')
        assert suggestions == []


# =============================================================================
# 3.3 调试引擎测试
# =============================================================================

class TestDebugEngine:
    """测试 DebugEngine"""

    def test_import_debug_engine(self):
        """测试导入调试引擎"""
        from debug_engine import DebugEngine, StepMode, Frame
        engine = DebugEngine()
        assert engine is not None
        assert engine.step_mode == StepMode.NONE
        assert not engine.paused

    def test_set_breakpoint(self):
        """测试设置断点"""
        from debug_engine import DebugEngine
        engine = DebugEngine()
        assert engine.set_breakpoint("test.light", 10)
        assert not engine.set_breakpoint("test.light", 10)  # 重复设置

        breakpoints = engine.list_breakpoints()
        assert len(breakpoints) == 1
        assert breakpoints[0] == ("test.light", 10)

    def test_clear_breakpoint(self):
        """测试清除断点"""
        from debug_engine import DebugEngine
        engine = DebugEngine()
        engine.set_breakpoint("test.light", 10)
        assert engine.clear_breakpoint("test.light", 10)
        assert not engine.clear_breakpoint("test.light", 10)  # 不存在
        assert len(engine.list_breakpoints()) == 0

    def test_clear_all_breakpoints(self):
        """测试清除所有断点"""
        from debug_engine import DebugEngine
        engine = DebugEngine()
        engine.set_breakpoint("a.light", 1)
        engine.set_breakpoint("b.light", 2)
        engine.clear_all_breakpoints()
        assert len(engine.list_breakpoints()) == 0

    def test_should_break_breakpoint(self):
        """测试断点命中"""
        from debug_engine import DebugEngine
        engine = DebugEngine()
        engine.set_breakpoint("test.light", 10)
        assert engine.should_break("test.light", 10)
        assert engine.paused

    def test_should_break_no_breakpoint(self):
        """测试未命中断点"""
        from debug_engine import DebugEngine
        engine = DebugEngine()
        engine.set_breakpoint("test.light", 10)
        assert not engine.should_break("test.light", 5)
        assert not engine.paused

    def test_step_into(self):
        """测试单步进入"""
        from debug_engine import DebugEngine, StepMode
        engine = DebugEngine()
        engine.step_into()
        assert engine.step_mode == StepMode.INTO
        assert engine.paused
        assert engine.should_break("test.light", 1)

    def test_step_over(self):
        """测试单步跳过"""
        from debug_engine import DebugEngine, StepMode
        engine = DebugEngine()
        engine.step_over()
        assert engine.step_mode == StepMode.OVER
        assert engine.should_break("test.light", 1)

    def test_continue_execution(self):
        """测试继续执行"""
        from debug_engine import DebugEngine, StepMode
        engine = DebugEngine()
        engine.step_into()
        assert engine.paused
        engine.continue_execution()
        assert not engine.paused
        assert engine.step_mode == StepMode.NONE

    def test_variables(self):
        """测试变量管理"""
        from debug_engine import DebugEngine
        engine = DebugEngine()
        engine.update_local_vars({"甲": 10, "乙": "hello"})
        vars = engine.get_variables()
        assert vars["甲"] == 10
        assert vars["乙"] == "hello"

    def test_watch_vars(self):
        """测试监视变量"""
        from debug_engine import DebugEngine
        engine = DebugEngine()
        engine.add_watch("甲")
        engine.add_watch("乙")
        assert not engine.add_watch("甲")  # 重复添加

        engine.update_local_vars({"甲": 10, "乙": "hello"})
        watch_values = engine.get_watch_values()
        assert watch_values["甲"] == 10
        assert watch_values["乙"] == "hello"

        engine.remove_watch("甲")
        assert "甲" not in engine.get_watch_values()

    def test_call_stack(self):
        """测试调用栈"""
        from debug_engine import DebugEngine
        engine = DebugEngine()
        engine.push_frame("主函数", "main.light", 1, {"甲": 10})
        engine.push_frame("子函数", "sub.light", 5, {"乙": 20})

        stack = engine.get_call_stack()
        assert len(stack) == 2
        assert stack[0]["func_name"] == "主函数"
        assert stack[1]["func_name"] == "子函数"

        popped = engine.pop_frame()
        assert popped["func_name"] == "子函数"
        assert len(engine.get_call_stack()) == 1

    def test_get_status(self):
        """测试获取状态"""
        from debug_engine import DebugEngine
        engine = DebugEngine()
        engine.set_breakpoint("test.light", 10)
        status = engine.get_status()
        assert status["breakpoint_count"] == 1
        assert status["paused"] is False
        assert status["step_mode"] == "none"

    def test_reset(self):
        """测试重置"""
        from debug_engine import DebugEngine
        engine = DebugEngine()
        engine.set_breakpoint("test.light", 10)
        engine.push_frame("main", "test.light", 1, {})
        engine.add_watch("甲")
        engine.reset()
        assert len(engine.list_breakpoints()) == 0
        assert len(engine.get_call_stack()) == 0
        assert len(engine.get_watch_values()) == 0

    def test_breakpoint_callback(self):
        """测试断点回调"""
        from debug_engine import DebugEngine
        engine = DebugEngine()
        callback_results = []

        def on_break(file_path, line):
            callback_results.append((file_path, line))

        engine.on_breakpoint_hit(on_break)
        engine.set_breakpoint("test.light", 10)
        engine.should_break("test.light", 10)
        assert len(callback_results) == 1
        assert callback_results[0] == ("test.light", 10)


# =============================================================================
# 3.4 REPL 命令测试
# =============================================================================

class TestREPLCommands:
    """测试 REPL 命令处理"""

    def test_command_handler_debug(self):
        """测试调试命令"""
        from repl.commands import CommandHandler
        handler = CommandHandler()
        result = handler.handle(":debug on")
        assert "调试模式已开启" in result

        result = handler.handle(":debug off")
        assert "调试模式已关闭" in result

    def test_command_handler_help(self):
        """测试帮助命令"""
        from repl.commands import CommandHandler
        handler = CommandHandler()
        result = handler.handle(":help")
        assert "光明 REPL 帮助" in result
        assert "调试命令" in result

    def test_command_handler_unknown(self):
        """测试未知命令"""
        from repl.commands import CommandHandler
        handler = CommandHandler()
        result = handler.handle(":unknown")
        assert "未知命令" in result

    def test_command_handler_vars_empty(self):
        """测试空变量显示"""
        from repl.commands import CommandHandler
        handler = CommandHandler(env={})
        result = handler.handle(":vars")
        assert "无变量" in result

    def test_command_handler_vars_with_data(self):
        """测试变量显示"""
        from repl.commands import CommandHandler
        handler = CommandHandler(env={"甲": 10, "乙": "hello"})
        result = handler.handle(":vars")
        assert "甲" in result
        assert "乙" in result
        assert "10" in result

    def test_command_handler_stack_no_debug(self):
        """测试无调试模式时调用栈"""
        from repl.commands import CommandHandler
        handler = CommandHandler()
        result = handler.handle(":stack")
        assert "请先开启调试模式" in result

    def test_command_handler_break_no_debug(self):
        """测试无调试模式时断点"""
        from repl.commands import CommandHandler
        handler = CommandHandler()
        result = handler.handle(":break test.light 10")
        assert "请先开启调试模式" in result

    def test_command_handler_watch_no_debug(self):
        """测试无调试模式时监视变量"""
        from repl.commands import CommandHandler
        handler = CommandHandler()
        result = handler.handle(":watch 甲")
        assert "请先开启调试模式" in result

    def test_command_handler_step_no_debug(self):
        """测试无调试模式时单步执行"""
        from repl.commands import CommandHandler
        handler = CommandHandler()
        result = handler.handle(":step")
        assert "请先开启调试模式" in result

    def test_command_handler_continue_no_debug(self):
        """测试无调试模式时继续执行"""
        from repl.commands import CommandHandler
        handler = CommandHandler()
        result = handler.handle(":continue")
        assert "请先开启调试模式" in result


# =============================================================================
# 3.5 补全器测试
# =============================================================================

class TestCompleter:
    """测试自动补全器"""

    def test_completer_keywords(self):
        """测试关键字补全"""
        from repl.completer import LightCompleter
        completer = LightCompleter()
        completions = completer.get_completions("如")
        assert len(completions) > 0
        assert "如果" in completions

    def test_completer_env_vars(self):
        """测试环境变量补全"""
        from repl.completer import LightCompleter
        completer = LightCompleter(env={"甲": 10, "乙": 20})
        completions = completer.get_completions("")
        # 应包含环境变量
        all_names = completer._get_all_names()
        assert "甲" in all_names
        assert "乙" in all_names

    def test_completer_statement_start(self):
        """测试语句开始补全"""
        from repl.completer import LightCompleter
        completer = LightCompleter()
        completions = completer.get_completions("")
        assert len(completions) > 0
        # 应包含语句开始关键字
        assert "设" in completions or "如果" in completions or "导入" in completions

    def test_completer_after_set(self):
        """测试 '设' 关键字后补全"""
        from repl.completer import LightCompleter
        completer = LightCompleter(env={"甲": 10})
        # 设 后应提示变量名
        completions = completer.get_completions("设")
        assert "甲" in completions

    def test_completer_after_set_with_var(self):
        """测试 '设 变量' 后补全"""
        from repl.completer import LightCompleter
        completer = LightCompleter()
        completions = completer.get_completions("设 甲")
        # 应提示 "为"
        assert "为" in completions

    def test_completer_dot_access(self):
        """测试点号访问补全"""
        from repl.completer import LightCompleter
        # 创建一个有属性的对象
        class Obj:
            x = 1
            y = 2
        completer = LightCompleter(env={"obj": Obj()})
        completions = completer.get_completions("obj.")
        assert "x" in completions
        assert "y" in completions


# =============================================================================
# 新增：executor 修复 & 调试引擎集成测试
# =============================================================================

class TestExecutorFix:
    """测试 executor 修复"""

    def test_is_simple_var_decl(self):
        """测试 设 关键字被正确识别为简单"""
        from repl.executor import Executor
        executor = Executor()
        assert executor._is_simple("设 甲 为 10") is True

    def test_is_simple_print(self):
        """测试 打印 被识别为简单"""
        from repl.executor import Executor
        executor = Executor()
        assert executor._is_simple("打印(甲)") is True

    def test_is_simple_expression(self):
        """测试简单表达式"""
        from repl.executor import Executor
        executor = Executor()
        assert executor._is_simple("甲 加 5") is True

    def test_is_complex_function(self):
        """测试函数定义为复杂"""
        from repl.executor import Executor
        executor = Executor()
        assert executor._is_simple("函数 平方(数值): 返回 数值 乘 数值") is False

    def test_is_complex_if(self):
        """测试条件语句为复杂"""
        from repl.executor import Executor
        executor = Executor()
        assert executor._is_simple("如果 甲 大于 5: 打印(甲)") is False

    def test_execute_var_decl(self):
        """测试简单变量声明执行"""
        from repl.executor import Executor
        executor = Executor()
        result = executor.execute("设 甲 为 10")
        assert executor.env.get("甲") == 10
        assert result == 10

    def test_execute_var_decl_string(self):
        """测试字符串变量声明"""
        from repl.executor import Executor
        executor = Executor()
        result = executor.execute("设 乙 为 \"hello\"")
        assert executor.env.get("乙") == "hello"

    def test_execute_print(self):
        """测试打印执行"""
        from repl.executor import Executor
        executor = Executor()
        executor.env.set("甲", 10)
        result = executor.execute("打印(甲)")
        assert result == 10

    def test_execute_arithmetic(self):
        """测试算术运算"""
        from repl.executor import Executor
        executor = Executor()
        executor.env.set("甲", 10)
        result = executor.execute("甲 加 5")
        assert result == 15

    def test_debug_engine_integration(self):
        """测试调试引擎集成"""
        from repl.executor import Executor
        from debug_engine import DebugEngine
        executor = Executor()
        engine = DebugEngine()
        executor.set_debug_engine(engine)
        assert executor.get_debug_engine() is engine
        assert executor._debug_enabled is True

    def test_debug_engine_variable_tracking(self):
        """测试调试引擎变量跟踪"""
        from repl.executor import Executor
        from debug_engine import DebugEngine
        executor = Executor()
        engine = DebugEngine()
        executor.set_debug_engine(engine)
        executor.execute("设 甲 为 10")
        vars = engine.get_variables()
        assert vars.get("甲") == 10

    def test_enhanced_repl_import(self):
        """测试增强 REPL 导入"""
        from repl.enhanced import EnhancedREPL, HAS_PROMPT_TOOLKIT
        assert EnhancedREPL is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])