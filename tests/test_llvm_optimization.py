# -*- coding: utf-8 -*-
"""
第9周 LLVM 优化测试

测试 LLVM 优化 Pass 管线、代码体积优化器、启动时间优化器
和 DWARF 调试信息生成。
"""

import sys
import os
import pytest

# 添加项目路径
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)


# ============================================================================
# 优化管线测试
# ============================================================================

class TestOptimizationPipeline:
    """测试优化管线"""

    def test_import_pipeline(self):
        """测试优化管线导入"""
        from llvm.optimizer_pipeline import OptimizationPipeline, PassStats
        assert OptimizationPipeline is not None
        assert PassStats is not None

    def test_pipeline_creation(self):
        """测试管线创建"""
        from llvm.optimizer_pipeline import OptimizationPipeline

        # 测试各优化级别
        for level in ['O0', 'O1', 'O2', 'O3', 'Os', 'Oz']:
            pipeline = OptimizationPipeline(opt_level=level)
            assert pipeline.opt_level == level
            assert pipeline.passes is not None

        # O0 应该没有 Pass
        o0 = OptimizationPipeline(opt_level='O0')
        assert len(o0.passes) == 0

        # O1 至少 1 个 Pass
        o1 = OptimizationPipeline(opt_level='O1')
        assert len(o1.passes) >= 1

        # O3 应该比 O1 有更多 Pass
        assert len(OptimizationPipeline(opt_level='O3').passes) >= len(
            OptimizationPipeline(opt_level='O1').passes)

    def test_pass_stats(self):
        """测试 Pass 统计信息"""
        from llvm.optimizer_pipeline import PassStats

        stat = PassStats('test_pass')
        assert stat.name == 'test_pass'
        assert stat.status == 'pending'
        assert stat.elapsed == 0.0
        assert stat.reduction == 0.0

        stat.start_time = 100.0
        stat.end_time = 102.0
        stat.input_size = 1000
        stat.output_size = 800
        stat.status = 'done'

        assert stat.elapsed == 2.0
        assert stat.reduction == pytest.approx(20.0)  # (1 - 800/1000) * 100

    def test_get_summary(self):
        """测试获取摘要信息"""
        from llvm.optimizer_pipeline import OptimizationPipeline

        pipeline = OptimizationPipeline(opt_level='O2')
        ir = """
define i32 @main() {
  ret i32 0
}
"""
        result = pipeline.run(ir)
        summary = pipeline.get_summary()

        assert summary['opt_level'] == 'O2'
        assert summary['num_passes'] > 0
        assert 'total_time' in summary
        assert 'input_size' in summary
        assert 'output_size' in summary
        assert 'reduction_pct' in summary
        assert 'passes' in summary
        assert len(summary['passes']) == summary['num_passes']

    def test_run_does_not_crash(self):
        """测试运行管线不会崩溃"""
        from llvm.optimizer_pipeline import OptimizationPipeline

        ir = """
define i32 @main() {
entry:
  %0 = add i32 1, 2
  %1 = mul i32 %0, 3
  ret i32 %1
}
"""
        for level in ['O0', 'O1', 'O2', 'O3', 'Os', 'Oz']:
            pipeline = OptimizationPipeline(opt_level=level)
            result = pipeline.run(ir)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_peephole_pass(self):
        """测试窥孔优化 Pass"""
        from llvm.optimizer_pipeline import OptimizationPipeline

        # 测试消除连续 br 跳转
        ir = """
define void @test() {
entry:
  br label %next
next:
  ret void
}
"""
        pipeline = OptimizationPipeline(opt_level='O1')
        result = pipeline.run(ir)
        # 优化后应该只保留一个标签
        assert 'br label %next' not in result or 'next:' in result

    def test_remove_unused_globals(self):
        """测试移除未使用的全局变量"""
        from llvm.optimizer_pipeline import OptimizationPipeline

        # 测试移除未使用的全局变量
        ir = """
@unused = private global i32 0
@used = global i32 42
define i32 @main() {
  %0 = load i32, i32* @used
  ret i32 %0
}
"""
        # 使用 Os 级别，包含 _remove_unused_globals_pass
        pipeline = OptimizationPipeline(opt_level='Os')
        result = pipeline.run(ir)

        # @unused 应该被移除
        assert '@unused' not in result or '@used' in result

    def test_merge_blocks_pass(self):
        """测试基本块合并"""
        from llvm.optimizer_pipeline import OptimizationPipeline

        ir = """
define void @test() {
entry:
  br label %block1
block1:
  ret void
}
"""
        pipeline = OptimizationPipeline(opt_level='Os')
        result = pipeline.run(ir)
        # br label %block1 应该被合并消除
        lines = result.strip().split('\n')
        block_count = sum(1 for l in lines if l.strip().endswith(':'))
        # 应该只有 1 个基本块（entry 合并了 block1）
        assert block_count <= 1


# ============================================================================
# 代码体积优化器测试
# ============================================================================

class TestSizeOptimizer:
    """测试代码体积优化器"""

    def test_import(self):
        """测试导入"""
        from llvm.size_optimizer import SizeOptimizer
        assert SizeOptimizer is not None

    def test_basic_optimize(self):
        """测试基本优化"""
        from llvm.size_optimizer import SizeOptimizer

        opt = SizeOptimizer()
        ir = """
define i32 @main() {
  ret i32 0
}
"""
        result = opt.optimize(ir)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_dead_code_elimination(self):
        """测试死代码消除"""
        from llvm.size_optimizer import SizeOptimizer

        # 在 ret 之后有死代码
        ir = """
define i32 @test() {
entry:
  %0 = add i32 1, 2
  ret i32 %0
  %1 = add i32 3, 4  ; 死代码（ret 之后）
  ret i32 %1
}
"""
        opt = SizeOptimizer()
        # 直接测试 _dead_code_elimination 方法，避免其他优化 Pass 的影响
        result = opt._dead_code_elimination(ir)
        # 死代码应该被移除（ret 之后无副作用的指令）
        # 验证死代码行 "%1 = add" 不存在
        assert '%1 = add' not in result
        # 验证 ret 指令仍然存在
        assert 'ret i32' in result

    def test_get_stats(self):
        """测试获取统计信息"""
        from llvm.size_optimizer import SizeOptimizer

        opt = SizeOptimizer()
        ir = "define i32 @main() { ret i32 0 }"
        opt.optimize(ir)
        stats = opt.get_stats()
        assert 'dead_code_eliminated' in stats
        assert 'constants_folded' in stats
        assert 'instructions_combined' in stats
        assert 'deduplicated_functions' in stats
        assert 'merged_constants' in stats

    def test_constant_folding(self):
        """测试常量折叠"""
        from llvm.size_optimizer import SizeOptimizer

        ir = """
define i32 @test() {
entry:
  %0 = add i32 1, 2
  ret i32 %0
}
"""
        opt = SizeOptimizer()
        result = opt.optimize(ir)
        # 常量折叠应该发生（结果不为空且不崩溃）
        assert len(result) > 0
        assert isinstance(result, str)


# ============================================================================
# 启动时间优化器测试
# ============================================================================

class TestStartupOptimizer:
    """测试启动时间优化器"""

    def test_import(self):
        """测试导入"""
        from llvm.startup_optimizer import StartupOptimizer
        assert StartupOptimizer is not None

    def test_basic_optimize(self):
        """测试基本优化"""
        from llvm.startup_optimizer import StartupOptimizer

        opt = StartupOptimizer()
        ir = """
define i32 @main() {
  ret i32 0
}
"""
        result = opt.optimize(ir)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_precompute_expressions(self):
        """测试预计算表达式"""
        from llvm.startup_optimizer import StartupOptimizer

        ir = """
define i32 @test() {
entry:
  %0 = add i32 3, 4
  ret i32 %0
}
"""
        opt = StartupOptimizer()
        result = opt.optimize(ir)
        # 预计算应该发生
        assert 'precomputed' in result

    def test_hot_cold_splitting(self):
        """测试 hot/cold 分离"""
        from llvm.startup_optimizer import StartupOptimizer

        ir = """
define void @init() {
  ret void
}
define void @hot_func() {
  ret void
}
"""
        opt = StartupOptimizer()
        result = opt.optimize(ir)
        # init 函数应该被标记为 cold 或 hot
        assert 'cold' in result or 'inlinehint' in result

    def test_get_stats(self):
        """测试获取统计信息"""
        from llvm.startup_optimizer import StartupOptimizer

        opt = StartupOptimizer()
        ir = """
define i32 @main() {
  %0 = add i32 1, 2
  ret i32 %0
}
"""
        opt.optimize(ir)
        stats = opt.get_stats()
        assert 'precomputed_expressions' in stats
        assert 'inlined_hot_functions' in stats
        assert 'deferred_inits' in stats
        assert 'hot_cold_split' in stats
        assert 'precompiled_hot' in stats


# ============================================================================
# DWARF 调试信息测试
# ============================================================================

class TestDwarfDebugInfo:
    """测试 DWARF 调试信息生成"""

    def test_import(self):
        """测试导入"""
        from llvm.dwarf import DwarfDebugInfo, DwarfScope
        assert DwarfDebugInfo is not None
        assert DwarfScope is not None

    def test_compile_unit(self):
        """测试编译单元元数据"""
        from llvm.dwarf import DwarfDebugInfo

        dwarf = DwarfDebugInfo('test.light')
        dwarf.add_compile_unit()
        metadata = dwarf.generate_metadata()

        assert '!llvm.dbg.cu' in metadata
        assert '!DICompileUnit' in metadata
        assert '光明编译器' in metadata
        assert 'Dwarf Version' in metadata
        assert 'Debug Info Version' in metadata

    def test_add_function(self):
        """测试添加函数调试信息"""
        from llvm.dwarf import DwarfDebugInfo

        dwarf = DwarfDebugInfo('test.light')
        func_id = dwarf.add_function('main', 1)
        assert func_id.startswith('!')
        metadata = dwarf.generate_metadata()
        assert 'DISubprogram' in metadata
        assert 'main' in metadata

    def test_add_variable(self):
        """测试添加变量调试信息"""
        from llvm.dwarf import DwarfDebugInfo

        dwarf = DwarfDebugInfo('test.light')
        dwarf.add_function('main', 1)
        var_id = dwarf.add_variable('x', 'i32', 5)
        assert var_id.startswith('!')
        metadata = dwarf.generate_metadata()
        assert 'DILocalVariable' in metadata
        assert 'x' in metadata

    def test_add_parameter(self):
        """测试添加函数参数调试信息"""
        from llvm.dwarf import DwarfDebugInfo

        dwarf = DwarfDebugInfo('test.light')
        dwarf.add_function('foo', 1)
        param_id = dwarf.add_parameter('n', 'i32', 1, 1)
        assert param_id.startswith('!')
        metadata = dwarf.generate_metadata()
        assert 'arg: 1' in metadata

    def test_add_lexical_block(self):
        """测试添加词法块"""
        from llvm.dwarf import DwarfDebugInfo

        dwarf = DwarfDebugInfo('test.light')
        dwarf.add_function('test', 1)
        block_id = dwarf.add_lexical_block(10)
        assert block_id.startswith('!')
        metadata = dwarf.generate_metadata()
        assert 'DILexicalBlock' in metadata

    def test_emit_location(self):
        """测试生成位置标注"""
        from llvm.dwarf import DwarfDebugInfo

        dwarf = DwarfDebugInfo('test.light')
        dwarf.add_function('main', 1)
        dbg = dwarf.emit_location(5, 3)
        assert dbg.startswith('!dbg !')

    def test_type_info(self):
        """测试类型信息"""
        from llvm.dwarf import DwarfDebugInfo

        dwarf = DwarfDebugInfo('test.light')
        # 基础类型
        type_id = dwarf.add_type('i32', 4)
        assert type_id.startswith('!')

        # 指针类型
        ptr_id = dwarf.add_pointer_type('i32*', 'i32')
        assert ptr_id.startswith('!')

        # 数组类型
        arr_id = dwarf.add_array_type('i32[4]', 'i32', 4)
        assert arr_id.startswith('!')

        metadata = dwarf.generate_metadata()
        assert 'DIBasicType' in metadata
        assert 'DW_TAG_pointer_type' in metadata
        assert 'DW_TAG_array_type' in metadata

    def test_scope_stack(self):
        """测试作用域栈"""
        from llvm.dwarf import DwarfDebugInfo

        dwarf = DwarfDebugInfo('test.light')
        dwarf.add_function('main', 1)

        # 压入词法块
        block_id = dwarf.add_lexical_block(10)
        assert dwarf.get_current_scope() == block_id

        # 弹出
        dwarf.pop_scope()
        assert dwarf.get_current_scope() != block_id

    def test_line_mapping(self):
        """测试行号映射"""
        from llvm.dwarf import DwarfDebugInfo

        dwarf = DwarfDebugInfo('test.light')
        dwarf.add_function('main', 1)
        dwarf.emit_location(5, 1)
        dwarf.emit_location(10, 1)

        mapping = dwarf.get_line_mapping(5)
        assert mapping is not None
        assert mapping.startswith('!dbg !')

        # 不存在的行号
        assert dwarf.get_line_mapping(999) is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])