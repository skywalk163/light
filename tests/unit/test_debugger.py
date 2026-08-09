# -*- coding: utf-8 -*-
"""
光明调试器单元测试

测试 LightDebugger 核心功能：断点管理、单步模式、调用栈跟踪。
"""

import os
import sys
import unittest

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, 'src')
_tools_dir = os.path.join(_project_root, 'tools')
for _p in [_src_dir, _tools_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_debug import LightDebugger, DebuggerContext, Breakpoint, StackFrame, create_debugger


class TestBreakpoint(unittest.TestCase):
    """断点测试"""

    def test_create_breakpoint(self):
        bp = Breakpoint(id=1, line=10)
        self.assertEqual(bp.line, 10)
        self.assertTrue(bp.enabled)
        self.assertIsNone(bp.condition)

    def test_breakpoint_should_stop_no_condition(self):
        bp = Breakpoint(id=1, line=5)
        self.assertTrue(bp.should_stop(0))

    def test_breakpoint_disabled(self):
        bp = Breakpoint(id=1, line=5, enabled=False)
        self.assertFalse(bp.should_stop(0))

    def test_breakpoint_hit_condition_gt(self):
        bp = Breakpoint(id=1, line=5, hit_count=3, hit_condition='>')
        self.assertFalse(bp.should_stop(3))
        self.assertTrue(bp.should_stop(4))

    def test_breakpoint_hit_condition_eq(self):
        bp = Breakpoint(id=1, line=5, hit_count=2, hit_condition='==')
        self.assertFalse(bp.should_stop(1))
        self.assertTrue(bp.should_stop(2))


class TestLightDebugger(unittest.TestCase):
    """调试器核心测试"""

    def setUp(self):
        self.debugger = create_debugger()

    def test_set_and_get_breakpoint(self):
        bp = self.debugger.set_breakpoint('test.light', 10)
        self.assertEqual(bp.line, 10)
        found = self.debugger.get_breakpoint('test.light', 10)
        self.assertIsNotNone(found)
        self.assertEqual(found.line, 10)

    def test_clear_breakpoint(self):
        self.debugger.set_breakpoint('test.light', 10)
        self.assertTrue(self.debugger.clear_breakpoint('test.light', 10))
        self.assertIsNone(self.debugger.get_breakpoint('test.light', 10))

    def test_clear_nonexistent_breakpoint(self):
        self.assertFalse(self.debugger.clear_breakpoint('test.light', 999))

    def test_list_breakpoints(self):
        self.debugger.set_breakpoint('a.light', 5)
        self.debugger.set_breakpoint('a.light', 10)
        self.debugger.set_breakpoint('b.light', 3)
        all_bps = self.debugger.list_breakpoints()
        self.assertEqual(len(all_bps), 3)
        a_bps = self.debugger.list_breakpoints('a.light')
        self.assertEqual(len(a_bps), 2)

    def test_check_breakpoint_hit(self):
        self.debugger.set_breakpoint('test.light', 5)
        bp = self.debugger.check_breakpoint('test.light', 5)
        self.assertIsNotNone(bp)
        self.assertEqual(bp.hit_count, 1)

    def test_check_breakpoint_miss(self):
        self.debugger.set_breakpoint('test.light', 5)
        bp = self.debugger.check_breakpoint('test.light', 10)
        self.assertIsNone(bp)

    def test_step_mode_default(self):
        self.assertEqual(self.debugger.step_mode, LightDebugger.STEP_NONE)

    def test_set_step_over(self):
        self.debugger.set_step(LightDebugger.STEP_OVER)
        self.assertEqual(self.debugger.step_mode, LightDebugger.STEP_OVER)

    def test_set_step_into(self):
        self.debugger.set_step(LightDebugger.STEP_INTO)
        self.assertEqual(self.debugger.step_mode, LightDebugger.STEP_INTO)

    def test_should_stop_on_breakpoint(self):
        self.debugger.set_breakpoint('test.light', 5)
        self.assertTrue(self.debugger.should_stop_here('test.light', 5))

    def test_should_stop_on_step_into(self):
        self.debugger.set_step(LightDebugger.STEP_INTO)
        self.assertTrue(self.debugger.should_stop_here('test.light', 1))

    def test_should_not_stop_no_breakpoint_no_step(self):
        self.assertFalse(self.debugger.should_stop_here('test.light', 1))

    def test_start_and_stop(self):
        self.debugger.start()
        self.assertTrue(self.debugger.running)
        self.debugger.stop()
        self.assertFalse(self.debugger.running)
        self.assertTrue(self.debugger.quitting)

    def test_frame_callback(self):
        """测试帧回调被正确调用"""
        results = []

        def callback(file, line, frame):
            results.append((file, line))

        self.debugger.frame_callback = callback
        self.debugger.set_breakpoint('test.light', 1)
        self.debugger.start()
        self.debugger.on_line_change('test.light', 1, None)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], ('test.light', 1))

    def test_on_line_change_resets_step_mode(self):
        """单步模式在行变化后应重置"""
        self.debugger.set_step(LightDebugger.STEP_OVER)
        self.debugger.start()
        self.debugger.on_line_change('test.light', 1, None)
        self.assertEqual(self.debugger.step_mode, LightDebugger.STEP_NONE)


class TestDebuggerContext(unittest.TestCase):
    """调试上下文管理器测试"""

    def test_context_manager_enters_and_exits(self):
        """测试上下文管理器正确设置和恢复 trace"""
        import sys
        debugger = create_debugger()
        old_trace = sys.gettrace()

        with DebuggerContext(debugger):
            self.assertIsNotNone(sys.gettrace())

        self.assertEqual(sys.gettrace(), old_trace)

    def test_trace_captures_lines(self):
        """测试 trace 函数捕获行执行"""
        debugger = create_debugger()
        lines_hit = []

        def callback(file, line, frame):
            lines_hit.append(line)

        debugger.frame_callback = callback
        debugger.set_step(LightDebugger.STEP_INTO)
        debugger.start()

        with DebuggerContext(debugger):
            # 执行一些简单代码
            x = 1
            y = 2
            z = x + y

        # 应该捕获了至少一些行
        self.assertTrue(len(lines_hit) > 0)


class TestStackFrame(unittest.TestCase):
    """栈帧测试"""

    def test_create_stack_frame(self):
        frame = StackFrame(name='测试', filename='test.light', lineno=5)
        self.assertEqual(frame.name, '测试')
        self.assertEqual(frame.filename, 'test.light')
        self.assertEqual(frame.lineno, 5)
        self.assertEqual(frame.locals, {})
        self.assertEqual(frame.globals, {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
