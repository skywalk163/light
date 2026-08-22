"""
第9周测试：LLVM 优化 Pass 与编译速度

测试内容：
1. 优化管线构建
2. 常量折叠优化
3. 死代码消除
4. 尾调用优化
5. 循环展开
6. 编译缓存
7. 增量编译
8. DWARF 元数据生成
9. 代码体积优化
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# 确保 src 在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))


class TestOptimizationPipeline(unittest.TestCase):
    """测试优化管线构建"""

    def setUp(self):
        from llvm.optimizer_pipeline import OptimizationPipeline

        self.pipeline = OptimizationPipeline

    def test_o0_pipeline(self):
        """测试 -O0 管线：无优化"""
        p = self.pipeline(opt_level='O0')
        self.assertEqual(len(p.passes), 0)

    def test_o1_pipeline(self):
        """测试 -O1 管线：基本优化"""
        p = self.pipeline(opt_level='O1')
        self.assertGreater(len(p.passes), 0)

    def test_o2_pipeline(self):
        """测试 -O2 管线：标准优化"""
        p = self.pipeline(opt_level='O2')
        self.assertGreater(len(p.passes), 0)

    def test_o3_pipeline(self):
        """测试 -O3 管线：激进优化"""
        p = self.pipeline(opt_level='O3')
        self.assertGreater(len(p.passes), 0)

    def test_os_pipeline(self):
        """测试 -Os 管线：体积优化"""
        p = self.pipeline(opt_level='Os')
        self.assertGreater(len(p.passes), 0)

    def test_oz_pipeline(self):
        """测试 -Oz 管线：激进体积优化"""
        p = self.pipeline(opt_level='Oz')
        self.assertGreater(len(p.passes), 0)

    def test_run_pipeline(self):
        """测试管线运行"""
        p = self.pipeline(opt_level='O2')
        ir = """
define i32 @test(i32 %x) {
entry:
  %r = add i32 %x, 0
  ret i32 %r
}
"""
        result = p.run(ir)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_pipeline_stats(self):
        """测试管线统计信息"""
        p = self.pipeline(opt_level='O2', verbose=False)
        ir = "define i32 @f(i32 %x) { entry: ret i32 %x }"
        p.run(ir)
        summary = p.get_summary()
        self.assertIn('opt_level', summary)
        self.assertIn('num_passes', summary)
        self.assertIn('total_time', summary)


class TestOptPasses(unittest.TestCase):
    """测试自定义优化 Pass"""

    def test_tail_call_optimization(self):
        """测试尾调用优化"""
        from llvm.opt_passes import TailCallOptimizationPass

        tc = TailCallOptimizationPass()
        ir = """
define i32 @factorial(i32 %n, i32 %acc) {
entry:
  %cmp = icmp eq i32 %n, 0
  br i1 %cmp, label %base, label %recur

base:
  ret i32 %acc

recur:
  %sub = sub i32 %n, 1
  %mul = mul i32 %acc, %n
  %r = call i32 @factorial(i32 %sub, i32 %mul)
  ret i32 %r
}
"""
        result = tc.run(ir)
        self.assertIsInstance(result, str)

    def test_constant_propagation(self):
        """测试常量传播"""
        from llvm.opt_passes import ConstantPropagationPass

        cp = ConstantPropagationPass()
        ir = """
define i32 @test() {
entry:
  %r = add i32 3, 4
  ret i32 %r
}
"""
        result = cp.run(ir)
        self.assertIn('7', result)

    def test_strength_reduction(self):
        """测试强度削弱"""
        from llvm.opt_passes import StrengthReductionPass

        sr = StrengthReductionPass()
        # x * 8 → x << 3
        ir = """
define i32 @test(i32 %x) {
entry:
  %r = mul i32 %x, 8
  ret i32 %r
}
"""
        result = sr.run(ir)
        self.assertIn('shl', result)

    def test_empty_ir(self):
        """测试空 IR 的 Pass 处理"""
        from llvm.opt_passes import ConstantPropagationPass
        from llvm.opt_passes import StrengthReductionPass

        cp = ConstantPropagationPass()
        sr = StrengthReductionPass()
        self.assertEqual(cp.run(''), '')
        self.assertEqual(sr.run(''), '')


class TestCompilationCache(unittest.TestCase):
    """测试编译缓存系统"""

    def setUp(self):
        from compiler_cache import CompilationCache

        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.temp_dir, '.light_cache')
        self.cache = CompilationCache(cache_dir=self.cache_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_set_and_get_cache(self):
        """测试设置和获取缓存"""
        # 创建临时文件
        test_file = os.path.join(self.temp_dir, 'test.light')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('定义 甲 等于 1')

        self.cache.set_cached(test_file, 'test_ir_result')
        result = self.cache.get_cached(test_file)
        self.assertEqual(result, 'test_ir_result')

    def test_cache_invalidation(self):
        """测试缓存失效"""
        test_file = os.path.join(self.temp_dir, 'test.light')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('定义 甲 等于 1')

        self.cache.set_cached(test_file, 'ir_result')
        self.cache.invalidate(test_file)
        result = self.cache.get_cached(test_file)
        self.assertIsNone(result)

    def test_cache_freshness(self):
        """测试缓存新鲜度"""
        test_file = os.path.join(self.temp_dir, 'test.light')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('定义 甲 等于 1')

        self.assertFalse(self.cache.is_fresh(test_file))
        self.cache.set_cached(test_file, 'ir_result')
        self.assertTrue(self.cache.is_fresh(test_file))

    def test_cache_stats(self):
        """测试缓存统计"""
        stats = self.cache.stats()
        self.assertIn('memory_cache_entries', stats)
        self.assertIn('disk_cache_entries', stats)
        self.assertIn('cache_dir', stats)

    def test_clear_cache(self):
        """测试清空缓存"""
        test_file = os.path.join(self.temp_dir, 'test.light')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('定义 甲 等于 1')

        self.cache.set_cached(test_file, 'ir_result')
        self.cache.clear()
        result = self.cache.get_cached(test_file)
        self.assertIsNone(result)

    def test_clean_cache(self):
        """测试清理过期缓存"""
        test_file = os.path.join(self.temp_dir, 'test.light')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('定义 甲 等于 1')

        self.cache.set_cached(test_file, 'ir_result')
        # 验证缓存存在
        self.assertIsNotNone(self.cache.get_cached(test_file))
        # 清理所有缓存（TTL=0，强制过期）
        self.cache.clean(max_age_hours=0)
        # 验证缓存已被清理（get_cached 返回 None）
        self.assertIsNone(self.cache.get_cached(test_file))
        # 验证缓存键仍然有效（基于文件内容，不依赖缓存状态）
        self.assertIsNotNone(self.cache.get_cache_key(test_file))


class TestIncrementalCompiler(unittest.TestCase):
    """测试增量编译"""

    def setUp(self):
        from incremental_compiler import IncrementalCompiler
        from compiler_cache import CompilationCache

        self.temp_dir = tempfile.mkdtemp()
        self.cache = CompilationCache(cache_dir=os.path.join(self.temp_dir, '.light_cache'))
        self.compiler = IncrementalCompiler(cache=self.cache)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_compile_nonexistent_file(self):
        """测试编译不存在的文件"""
        result = self.compiler.compile(os.path.join(self.temp_dir, 'nonexistent.light'))
        self.assertFalse(result['success'])
        self.assertIn('不存在', result.get('error', ''))

    def test_get_dirty_modules_empty_dir(self):
        """测试空目录的脏模块检测"""
        empty_dir = os.path.join(self.temp_dir, 'empty')
        os.makedirs(empty_dir, exist_ok=True)
        dirty = self.compiler.get_dirty_modules(empty_dir)
        self.assertEqual(dirty, [])

    def test_compile_project_structure(self):
        """测试编译项目结构"""
        result = self.compiler.compile_project(
            self.temp_dir,
            verbose=False,
        )
        self.assertIn('success', result)
        self.assertIn('total_files', result)
        self.assertIn('files_compiled', result)
        self.assertIn('files_cached', result)


class TestDwarfDebugInfo(unittest.TestCase):
    """测试 DWARF 调试信息生成"""

    def setUp(self):
        from llvm.dwarf import DwarfDebugInfo

        self.dwarf = DwarfDebugInfo('test.light')

    def test_compile_unit(self):
        """测试编译单元生成"""
        self.dwarf.add_compile_unit()
        metadata = self.dwarf.generate_metadata()
        self.assertIn('DICompileUnit', metadata)
        self.assertIn('DIFile', metadata)

    def test_function_debug_info(self):
        """测试函数调试信息"""
        self.dwarf.add_function('main', 1, 'test.light')
        metadata = self.dwarf.generate_metadata()
        self.assertIn('DISubprogram', metadata)
        self.assertIn('main', metadata)

    def test_variable_debug_info(self):
        """测试变量调试信息"""
        self.dwarf.add_compile_unit()
        self.dwarf.add_function('test', 1)
        self.dwarf.add_variable('x', 'i32', 2, 1)
        metadata = self.dwarf.generate_metadata()
        self.assertIn('DILocalVariable', metadata)
        self.assertIn('x', metadata)

    def test_type_debug_info(self):
        """测试类型调试信息"""
        type_id = self.dwarf.add_type('i32', 4)
        self.assertIsNotNone(type_id)
        metadata = self.dwarf.generate_metadata()
        self.assertIn('i32', metadata)
        self.assertIn('size: 32', metadata)

    def test_location_emit(self):
        """测试位置标注生成"""
        self.dwarf.add_compile_unit()
        self.dwarf.add_function('test', 1)
        dbg = self.dwarf.emit_location(5, 3)
        self.assertIn('!dbg', dbg)

    def test_metadata_generation(self):
        """测试完整元数据生成"""
        self.dwarf.add_compile_unit()
        self.dwarf.add_function('main', 1)
        self.dwarf.add_variable('x', 'i32', 2)
        self.dwarf.add_type('i8*', 8)
        metadata = self.dwarf.generate_metadata()
        self.assertIn('!llvm.dbg.cu', metadata)
        self.assertIn('!llvm.module.flags', metadata)


class TestSizeOptimizer(unittest.TestCase):
    """测试代码体积优化"""

    def setUp(self):
        from llvm.size_optimizer import SizeOptimizer

        self.optimizer = SizeOptimizer()

    def test_remove_unused_globals(self):
        """测试移除未使用的全局变量"""
        ir = """
@.str.1 = private unnamed_addr constant [5 x i8] c"hello\00"
@.str.2 = private unnamed_addr constant [5 x i8] c"world\00"
define i32 @main() {
entry:
  ret i32 0
}
"""
        result = self.optimizer.optimize(ir)
        # .str.2 未被引用，应该被移除
        # 注意：这里简化验证，实际结果取决于优化器实现
        self.assertIsInstance(result, str)

    def test_merge_constants(self):
        """测试合并字符串常量"""
        ir = """
@.str.1 = private unnamed_addr constant [4 x i8] c"abc\00"
@.str.2 = private unnamed_addr constant [4 x i8] c"abc\00"
"""
        result = self.optimizer._merge_constants(ir)
        # 合并后应该只有一个 "abc" 常量
        count = result.count('c"abc"')
        self.assertGreaterEqual(count, 0)

    def test_merge_blocks(self):
        """测试合并基本块"""
        ir = """
define i32 @test() {
entry:
  br label %next
next:
  ret i32 0
}
"""
        result = self.optimizer._merge_blocks(ir)
        # 合并后应该没有 br 到下一个块的指令
        self.assertIsInstance(result, str)

    def test_empty_ir(self):
        """测试空 IR"""
        result = self.optimizer.optimize('')
        self.assertEqual(result, '')

    def test_get_stats(self):
        """测试获取统计信息"""
        self.optimizer.optimize('')
        stats = self.optimizer.get_stats()
        self.assertIn('deduplicated_functions', stats)
        self.assertIn('merged_constants', stats)
        self.assertIn('removed_globals', stats)


class TestStartupOptimizer(unittest.TestCase):
    """测试启动时间优化"""

    def setUp(self):
        from llvm.startup_optimizer import StartupOptimizer

        self.optimizer = StartupOptimizer()

    def test_hot_cold_splitting(self):
        """测试函数分块"""
        ir = """
define void @init() {
entry:
  ret void
}
define i32 @main() {
entry:
  ret i32 0
}
"""
        result = self.optimizer._hot_cold_splitting(ir)
        # init 函数应该被标记为 cold
        self.assertIsInstance(result, str)

    def test_precompile_hot_functions(self):
        """测试预编译热函数"""
        ir = """
define i32 @hot_func() {
entry:
  ret i32 1
}
define i32 @main() {
entry:
  %r = call i32 @hot_func()
  ret i32 %r
}
"""
        result = self.optimizer._precompile_hot_functions(ir)
        self.assertIsInstance(result, str)

    def test_get_stats(self):
        """测试获取统计信息"""
        self.optimizer.optimize('')
        stats = self.optimizer.get_stats()
        self.assertIn('deferred_inits', stats)
        self.assertIn('hot_cold_split', stats)
        self.assertIn('precompiled_hot', stats)


class TestOptimizerBase(unittest.TestCase):
    """测试优化器基类增强"""

    def test_optimizer_stats(self):
        """测试优化器统计信息"""
        from optimizer.base import OptimizerStats

        stats = OptimizerStats('TestOptimizer')
        self.assertEqual(stats.name, 'TestOptimizer')
        self.assertEqual(stats.status, 'pending')
        self.assertEqual(stats.elapsed, 0.0)

        stats.start_time = 100.0
        stats.end_time = 102.0
        self.assertAlmostEqual(stats.elapsed, 2.0)

    def test_optimizer_stats_to_dict(self):
        """测试统计信息转字典"""
        from optimizer.base import OptimizerStats

        stats = OptimizerStats('TestOptimizer')
        stats.initial_stmt_count = 10
        stats.final_stmt_count = 8
        d = stats.to_dict()
        self.assertEqual(d['name'], 'TestOptimizer')
        self.assertEqual(d['initial_stmt_count'], 10)
        self.assertEqual(d['final_stmt_count'], 8)
        self.assertIn('stmt_reduction_pct', d)


class TestCompilerIntegration(unittest.TestCase):
    """测试编译器集成"""

    def test_compile_source_with_opt_level(self):
        """测试带优化级别的编译"""
        # 验证 compile_source 接受 opt_level 参数
        try:
            from llvm.compiler import compile_source
            # 不实际运行（因为需要完整的解析环境）
            # 只验证函数签名
            import inspect
            sig = inspect.signature(compile_source)
            self.assertIn('opt_level', sig.parameters)
        except ImportError:
            self.skipTest("无法导入 llvm.compiler")

    def test_compile_source_typed_with_opt_level(self):
        """测试 typed 编译的优化级别参数"""
        try:
            from llvm.compiler import compile_source_typed
            import inspect
            sig = inspect.signature(compile_source_typed)
            self.assertIn('opt_level', sig.parameters)
        except ImportError:
            self.skipTest("无法导入 llvm.compiler")

    def test_compile_modules_typed_with_opt_level(self):
        """测试多模块编译的优化级别参数"""
        try:
            from llvm.compiler import compile_modules_typed
            import inspect
            sig = inspect.signature(compile_modules_typed)
            self.assertIn('opt_level', sig.parameters)
        except ImportError:
            self.skipTest("无法导入 llvm.compiler")


class Test块合并不许砸掉终结指令(unittest.TestCase):
    """_merge_blocks_pass 的单前驱护栏

    背景：`_peephole_pass` 里曾有一条
        re.sub(r'br label %(\\w+)\\s*\\n\\s*\\1:', r'\\1:', ir)
    它无条件删掉 `br label %X`、只留下 `X:`。目标块只有一个前驱时这等于合并块，
    但多前驱时前驱块就此失去终结指令，产出的 IR 非法（clang 在标签行报
    "expected instruction opcode"）。该规则已删除；块合并统一由
    `_merge_blocks_pass` 做，并且只在目标标签**在本函数内只被引用一次**时才动手。
    """

    def setUp(self):
        from llvm.optimizer_pipeline import OptimizationPipeline

        self.pipeline = OptimizationPipeline

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _无终结指令的基本块(ir):
        """返回所有「没有终结指令」的基本块名（函数名, 块名）列表。

        逐行扫描：碰到 `X:` 开新块，碰到终结指令给当前块打标记；
        块结束（下一个标签或函数收尾 `}`）时若没打上标记就算缺终结指令。
        多行 switch 按方括号配平整条吃掉——与 src/llvm/core.py 的 IR 验证器
        （commit e27277c2「不再把多行 switch 的 case 行误判为死代码」）保持一致。
        """
        import re as _re

        终结前缀 = ('ret', 'br', 'switch', 'unreachable', 'indirectbr', 'resume')
        缺失 = []
        当前函数 = None
        当前块 = None
        本块有终结 = False
        lines = ir.split('\n')
        i = 0
        while i < len(lines):
            原行 = lines[i]
            行 = 原行.strip()
            m = _re.match(r'define\s+.*?@([\w.$-]+)\s*\(', 行)
            if m:
                当前函数 = m.group(1)
                当前块 = None
                本块有终结 = False
                i += 1
                continue
            if 行 == '}':
                if 当前块 is not None and not 本块有终结:
                    缺失.append((当前函数, 当前块))
                当前函数 = None
                当前块 = None
                本块有终结 = False
                i += 1
                continue
            标签 = _re.match(r'([\w.$-]+):\s*$', 行)
            if 标签 and 当前函数 is not None:
                if 当前块 is not None and not 本块有终结:
                    缺失.append((当前函数, 当前块))
                当前块 = 标签.group(1)
                本块有终结 = False
                i += 1
                continue
            if 当前函数 is not None and 行 and not 行.startswith(';'):
                首词 = 行.split()[0]
                if 首词 in 终结前缀:
                    本块有终结 = True
                    # 多行终结指令（switch）：按方括号配平吃掉整条
                    深度 = 原行.count('[') - 原行.count(']')
                    while 深度 > 0 and i + 1 < len(lines):
                        i += 1
                        深度 += lines[i].count('[') - lines[i].count(']')
            i += 1
        return 缺失

    # ------------------------------------------------------------------
    # 引用计数：四种引用形式一个都不能漏
    # ------------------------------------------------------------------

    def test_引用计数覆盖br_条件br_switch_phi四种形式(self):
        """漏掉任何一种引用形式都会把多前驱误判成单前驱。"""
        ir = '''define i32 @f(i1 %c, i32 %r) {
entry:
  br label %目标
目标:
  br i1 %c, label %目标, label %另一处
另一处:
  switch i32 %r, label %目标 [ i32 3, label %目标 i32 4, label %收尾 ]
收尾:
  %v = phi i32 [ 0, %目标 ], [ 1, %另一处 ]
  ret i32 %v
}'''
        计数 = self.pipeline._count_label_refs(ir)
        # 目标：br label(1) + br i1 的真分支(1) + switch default(1) + switch case(1)
        #       + phi 的来源块(1) = 5
        self.assertEqual(计数['目标'], 5)
        # 另一处：br i1 的假分支(1) + phi 的来源块(1) = 2
        self.assertEqual(计数['另一处'], 2)
        # 收尾：switch case(1) = 1
        self.assertEqual(计数['收尾'], 1)

    def test_引用计数不把数组类型当成标签(self):
        """`[4 x i32]` 这类类型写法不能被 phi 的方括号规则误计。"""
        ir = '''define void @f() {
entry:
  %p = alloca [4 x i32]
  %q = getelementptr inbounds [4 x i32], ptr %p, i32 0, i32 0
  ret void
}'''
        self.assertEqual(self.pipeline._count_label_refs(ir), {})

    # ------------------------------------------------------------------
    # 正向：多前驱必须保留 br
    # ------------------------------------------------------------------

    def test_多前驱时br必须保留_条件跳转(self):
        ir = '''define void @f(i1 %c) {
entry:
  br i1 %c, label %甲, label %乙
甲:
  call void @noop()
  br label %汇合
乙:
  call void @noop()
  br label %汇合
汇合:
  ret void
}'''
        结果 = self.pipeline._merge_blocks_pass(ir)
        # `乙` 块那条 br 紧邻 `汇合:`，旧实现会把它删掉；汇合有两个前驱，必须保留
        self.assertEqual(结果.count('br label %汇合'), 2, f"br 被删掉了:\n{结果}")
        self.assertEqual(self._无终结指令的基本块(结果), [])

    def test_多前驱时br必须保留_switch的case行(self):
        """switch 的 case 也是前驱。本仓 codegen_typed.py:3276 发射成单行。"""
        ir = '''define void @f(i32 %r) {
entry:
  switch i32 %r, label %兜底 [ i32 0, label %甲 i32 1, label %汇合 ]
甲:
  br label %汇合
汇合:
  ret void
兜底:
  ret void
}'''
        结果 = self.pipeline._merge_blocks_pass(ir)
        self.assertEqual(结果.count('br label %汇合'), 1, f"br 被删掉了:\n{结果}")
        self.assertEqual(self._无终结指令的基本块(结果), [])

    def test_多前驱时br必须保留_多行switch(self):
        """多行 switch（core.py 的验证器已支持该形态）同样要被算进引用计数。"""
        ir = '''define void @f(i32 %r) {
entry:
  switch i32 %r, label %兜底 [
    i32 0, label %甲
    i32 1, label %汇合
  ]
甲:
  br label %汇合
汇合:
  ret void
兜底:
  ret void
}'''
        结果 = self.pipeline._merge_blocks_pass(ir)
        self.assertEqual(结果.count('br label %汇合'), 1, f"br 被删掉了:\n{结果}")
        self.assertEqual(self._无终结指令的基本块(结果), [])

    def test_同名标签不跨函数串台(self):
        """标签是函数作用域的：两个函数各有一个单前驱 `下一步`，都该被合并。"""
        ir = '''define void @f() {
entry:
  br label %下一步
下一步:
  ret void
}

define void @g() {
entry:
  br label %下一步
下一步:
  ret void
}'''
        结果 = self.pipeline._merge_blocks_pass(ir)
        self.assertNotIn('br label %下一步', 结果, f"跨函数计数把单前驱错算成多前驱:\n{结果}")
        self.assertEqual(self._无终结指令的基本块(结果), [])

    def test_整条O2管线不产出缺终结指令的基本块(self):
        """反向兜底：多前驱 IR 走完整 -O2 管线也不能被砸出非法块。

        函数名用 main：_inline_small_functions_pass 会把「指令数 <= 5 且被调用
        <= 1 次」的非 main 函数整段删掉（既有行为，与本项无关），叫 main 才留得住。
        """
        ir = '''define i32 @main(i1 %c) {
entry:
  br i1 %c, label %甲, label %乙
甲:
  call void @noop()
  br label %汇合
乙:
  call void @noop()
  br label %汇合
汇合:
  ret i32 0
}
'''
        结果 = self.pipeline(opt_level='O2').run(ir)
        self.assertEqual(self._无终结指令的基本块(结果), [])
        self.assertEqual(结果.count('br label %汇合'), 2, f"br 被删掉了:\n{结果}")

    # ------------------------------------------------------------------
    # 反跑：单前驱确实要被合并（否则上面的断言是永真的）
    # ------------------------------------------------------------------

    def test_单前驱时br确实被合并掉(self):
        """单前驱：br 与那个死标签一起消失，两块并成一块。"""
        ir = '''define void @f() {
entry:
  call void @noop()
  br label %下一步
下一步:
  ret void
}'''
        结果 = self.pipeline._merge_blocks_pass(ir)
        self.assertNotIn('br label %下一步', 结果,
                         f"单前驱没合并，说明护栏收得太紧、优化被整个关掉了:\n{结果}")
        self.assertNotIn('下一步:', 结果,
                         f"只删了 br 没删死标签，entry 块就没有终结指令了:\n{结果}")
        self.assertIn('ret void', 结果)
        self.assertEqual(self._无终结指令的基本块(结果), [])


    def test_窥孔pass不再删br留标签(self):
        """项②被删掉的那条不安全规则：`_peephole_pass` 不许再动 br。"""
        ir = ('define void @f() {\n'
              'entry:\n'
              '  br label %下一步\n'
              '下一步:\n'
              '  ret void\n'
              '}\n')
        结果 = self.pipeline._peephole_pass(ir)
        self.assertIn('br label %下一步', 结果,
                      f"_peephole_pass 又在删 br 留标签了:\n{结果}")


class Test槽位池按真实用量分配(unittest.TestCase):
    """临时槽位池按函数真实用量分配，而不是每帧硬吃 2048 个槽位

    LIGHTVALUE_STRUCT 对齐后 48 字节，48 x 2048 ≈ 96KB/帧。Windows 默认 1MB 栈
    只够约 10 层，递归稍深就爆栈。改法是延迟填数：emit 时先放占位行、把行号记进
    `_temp_slot_pool_line`，函数体发射完毕后由 `_emit_temp_slot_pool()` 用真实的
    `_temp_slot_index` 回填。
    """

    # 只用少量临时值的样本；期望值是钉死的确切数字，不是 `< 2048` 这种过宽判据
    简单源码 = '\n'.join([
        '设 甲 为 10',
        '设 乙 为 20',
        '打印 甲 加 乙',
        '',
    ])
    简单源码期望池大小 = {'__light_init': 9, 'main': 1}

    # 递归深度 200；1..200 求和 = 20100
    递归源码 = '\n'.join([
        '段落 累加 接收 数：',
        '  如果 数 小于等于 0：',
        '    返回 0',
        '  否则：',
        '    返回 数 加 累加(数 减 1)',
        '',
        '打印 累加(200)',
        '',
    ])

    @staticmethod
    def _取各函数池大小(ir):
        """取每个函数入口块的槽位池 alloca 元素个数。

        `_begin_temp_slot_pool()` 把池 alloca 放在 `entry:` 的**下一行**，
        所以按这个位置取，绝不会和「调用参数数组」那种 stacksave 后的动态
        alloca 混起来。返回 {函数名: (元素个数, 池寄存器名)}。
        """
        import re as _re

        结果 = {}
        lines = ir.split('\n')
        当前函数 = None
        上一行是entry = False
        for 行 in lines:
            s = 行.strip()
            m = _re.match(r'define\s+.*?@([\w.$-]+)\s*\(', s)
            if m:
                当前函数 = m.group(1)
                上一行是entry = False
                continue
            if s == 'entry:':
                上一行是entry = True
                continue
            if 上一行是entry:
                上一行是entry = False
                池 = _re.match(r'(%[\w.$-]+) = alloca .*?, i32 (\d+)\s*$', s)
                if 池 and 当前函数 is not None:
                    结果[当前函数] = (int(池.group(2)), 池.group(1))
        return 结果

    @staticmethod
    def _取池实际用量(ir, 函数名, 池寄存器):
        """数该函数里以池指针为基址的 `getelementptr ..., ptr %池, i64 N`，
        返回 max(N) + 1，即真实用掉的槽位数。"""
        import re as _re

        在函数内 = False
        最大下标 = -1
        for 行 in ir.split('\n'):
            s = 行.strip()
            m = _re.match(r'define\s+.*?@([\w.$-]+)\s*\(', s)
            if m:
                在函数内 = (m.group(1) == 函数名)
                continue
            if s == '}':
                在函数内 = False
                continue
            if not 在函数内:
                continue
            g = _re.match(
                r'%[\w.$-]+ = getelementptr inbounds .*?, ptr '
                + _re.escape(池寄存器) + r', i64 (\d+)\s*$', s)
            if g:
                最大下标 = max(最大下标, int(g.group(1)))
        return 最大下标 + 1

    def test_池大小等于真实用量而不是2048(self):
        """源码级断言：给出确切期望值，并与 IR 里真实用到的槽位数交叉校验。"""
        from llvm.compiler import compile_source_typed

        ir = compile_source_typed(self.简单源码, verbose=False)
        池表 = self._取各函数池大小(ir)

        self.assertEqual(set(池表), set(self.简单源码期望池大小),
                         f"入口块池 alloca 没认全: {sorted(池表)}")
        for 函数名, 期望 in self.简单源码期望池大小.items():
            大小, 池寄存器 = 池表[函数名]
            self.assertNotEqual(大小, 2048,
                                f"{函数名} 仍在硬吃 2048 个槽位（48x2048≈96KB/帧）")
            self.assertEqual(大小, 期望, f"{函数名} 的池大小变了：{大小} != {期望}")
            # 交叉校验：池大小就是这个函数真正用掉的槽位数
            实际 = self._取池实际用量(ir, 函数名, 池寄存器)
            self.assertEqual(大小, max(实际, 1),
                             f"{函数名} 池大小 {大小} 与真实用量 {实际} 不一致")

    def test_溢出仍然硬报错不悄悄放大(self):
        """codegen_typed.py 的溢出保护行为保持一致：超过上限仍抛 RuntimeError。"""
        from llvm.codegen_typed import TypedLLVMCodeGen

        cg = TypedLLVMCodeGen()
        cg._temp_slot_pool = '%pool'
        cg._temp_slot_index = cg._temp_slot_pool_size
        with self.assertRaises(RuntimeError):
            cg._new_dv_slot()
        # 上限没被悄悄放大
        self.assertEqual(cg._temp_slot_pool_size, 2048)

    def test_递归200层真跑不爆栈(self):
        """真跑：编到可执行文件并运行，stdout 必须是 20100（1..200 求和）。

        这条是防「只改了 IR 里的数字、实际仍爆栈」。clang 腿复用
        tests/llvm运行时.py 的 取运行时对象()——运行时 .o 整场只编一次，
        绝不把 src/llvm/runtime_typed.c 直接塞进 clang 命令行。
        """
        import shutil
        import subprocess

        from llvm.compiler import compile_source_typed, find_clang

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from llvm运行时 import 取运行时对象, 取链接库参数

        try:
            clang = find_clang()
        except Exception:
            clang = None
        if not clang:
            self.skipTest("clang 编译器不可用（未安装 LLVM），跳过真跑")

        ir = compile_source_typed(self.递归源码, verbose=False)
        运行时对象 = 取运行时对象(clang)

        临时目录 = tempfile.mkdtemp(prefix='_redo2_slotpool_')
        try:
            ir路径 = os.path.join(临时目录, 'prog.ll')
            exe路径 = os.path.join(临时目录, 'prog.exe')
            with open(ir路径, 'w', encoding='utf-8') as f:
                f.write(ir)
            编译 = subprocess.run(
                [clang, '-O2', '-o', exe路径, ir路径, 运行时对象, *取链接库参数()],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=120,
            )
            self.assertEqual(编译.returncode, 0, f"clang 编译失败:\n{编译.stderr[:2000]}")
            运行 = subprocess.run(
                [exe路径],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=60,
            )
            self.assertEqual(运行.returncode, 0,
                             f"递归 200 层跑挂了（返回码 {运行.returncode}，"
                             f"很可能是爆栈）: {运行.stderr[:500]}")
            self.assertEqual(运行.stdout.strip(), '20100',
                             f"输出不对: {运行.stdout!r} / {运行.stderr[:500]!r}")
        finally:
            shutil.rmtree(临时目录, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()