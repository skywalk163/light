"""
光明 LLVM 编译器入口

使用 SRC 解析器（纯缩进语法）解析源码，通过 AstAdapter 适配，
再经由 LLVMCodeGen 生成 LLVM IR，然后用 clang 编译为原生可执行文件。

完整链路：
  .light → Lexer → LightParser(v3) → AstAdapter → ast_nodes → LLVMCodeGen
  → .ll → clang → 可执行文件 (.exe on Windows, 无后缀 on Linux/macOS)
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# 支持包内相对导入和直接导入两种方式
try:
    from .codegen import LLVMCodeGen
    from .codegen_typed import TypedLLVMCodeGen
    from .optimizer_pipeline import OptimizationPipeline
    from .size_optimizer import SizeOptimizer
    from .startup_optimizer import StartupOptimizer
    from ..lexer import Lexer
    from ..light_parser_v3 import LightParser
    from ..compiler import AstAdapter
    import ast_nodes as ast
except ImportError:
    # 直接导入模式（sys.path 包含 src 目录）
    from llvm.codegen import LLVMCodeGen
    from llvm.codegen_typed import TypedLLVMCodeGen
    from llvm.optimizer_pipeline import OptimizationPipeline
    from llvm.size_optimizer import SizeOptimizer
    from llvm.startup_optimizer import StartupOptimizer
    from lexer import Lexer
    from light_parser_v3 import LightParser
    from compiler import AstAdapter
    import ast_nodes as ast


def get_exe_extension() -> str:
    """根据当前平台返回可执行文件后缀"""
    if sys.platform == 'win32':
        return '.exe'
    return ''


def _strip_exe_ext(path: str) -> str:
    """移除路径中的可执行文件后缀（跨平台）"""
    ext = get_exe_extension()
    if ext and path.endswith(ext):
        return path[:-len(ext)]
    return path


def compile_source(source: str, verbose: bool = False, opt_level: str = 'O2') -> str:
    """
    编译光明源码为 LLVM IR 字符串

    Args:
        source: 光明源码字符串
        verbose: 是否输出详细信息
        opt_level: 优化级别 ('O0', 'O1', 'O2', 'O3', 'Os', 'Oz')，默认 'O2'

    Returns:
        LLVM IR 字符串
    """
    # 1) 语法解析（v3 纯缩进语法，内部完成词法分析）
    if verbose:
        print(f"[1/3] 语法解析: {len(source)} 字符")

    parser = LightParser()
    v3_module = parser.parse(source)
    if v3_module is None:
        errors = '\n'.join(parser.errors) if hasattr(parser, 'errors') and parser.errors else "未知解析错误"
        raise RuntimeError(f"解析失败:\n{errors}")

    # 2) AST 适配（v3 → ast_nodes）
    if verbose:
        print(f"[2/3] AST 适配...")

    adapter = AstAdapter()
    module = adapter.convert_module(v3_module)

    # 3) LLVM IR 生成
    if verbose:
        print(f"[3/3] 生成 LLVM IR...")

    codegen = LLVMCodeGen()
    ir = codegen.generate(module)

    if verbose:
        print(f"  IR 生成完成: {len(ir)} 字符")

    # 4) LLVM IR 优化（根据优化级别运行优化管线）
    if opt_level.upper() not in ('O0', '0'):
        if verbose:
            print(f"[4/4] 运行优化管线 (opt_level={opt_level})...")

        pipeline = OptimizationPipeline(opt_level=opt_level, verbose=verbose)
        optimized_ir = pipeline.run(ir)

        if verbose:
            summary = pipeline.get_summary()
            print(f"  优化完成: {summary['input_size']} -> {summary['output_size']} 字"
                  f" ({summary['reduction_pct']:+.1f}%), {summary['total_time']:.3f}s")

        ir = optimized_ir

    return ir


def _run_type_check_on_ast(source: str, module, verbose: bool = False):
    """在 LLVM 编译管线中运行类型检查"""
    try:
        from core.config import LightConfig, TypeCheckLevel
        from type_checker import create_checker_from_source

        config = LightConfig()
        config.type_check_level = TypeCheckLevel.SIGNATURE
        checker = create_checker_from_source(source, config)

        if checker.config.check_level != TypeCheckLevel.NONE:
            from type_inferencer import TypeInferencer
            inferencer = TypeInferencer()
            inferencer.infer(module)
            checker.check(module, inferencer)

            if checker.has_errors():
                errors = checker.get_errors()
                error_msgs = '\n'.join(str(r) for r in errors)
                raise RuntimeError(f"类型检查失败:\n{error_msgs}")

            if checker.get_warnings() and verbose:
                for w in checker.get_warnings():
                    print(f"  [类型警告] {w.message}")
    except ImportError:
        pass  # 类型检查器不可用时跳过
    except RuntimeError:
        raise
    except Exception as e:
        if verbose:
            print(f"  [类型检查] 跳过: {e}")


def compile_source_typed(source: str, verbose: bool = False, target_platform: str = None,
                         debug: bool = False, opt_level: str = 'O2') -> str:
    """
    编译光明源码为 LLVM IR 字符串（typed 模式）

    Args:
        source: 光明源码字符串
        verbose: 是否输出详细信息
        target_platform: 目标平台（win32/linux/darwin），默认自动检测
        debug: 是否生成 DWARF 调试信息
        opt_level: 优化级别 ('O0', 'O1', 'O2', 'O3', 'Os', 'Oz')，默认 'O2'

    Returns:
        LLVM IR 字符串
    """
    if verbose:
        print(f"[1/3] 语法解析: {len(source)} 字符")

    parser = LightParser()
    v3_module = parser.parse(source)
    if v3_module is None:
        errors = '\n'.join(parser.errors) if hasattr(parser, 'errors') and parser.errors else "未知解析错误"
        raise RuntimeError(f"解析失败:\n{errors}")

    if verbose:
        print(f"[2/3] AST 适配...")

    adapter = AstAdapter()
    module = adapter.convert_module(v3_module)

    # 类型检查（如果配置了检查级别）
    _run_type_check_on_ast(source, module, verbose)

    if verbose:
        print(f"[3/3] 生成 LLVM IR (typed)...")

    codegen = TypedLLVMCodeGen(target_platform=target_platform, debug=debug)
    ir = codegen.generate(module)

    if verbose:
        print(f"  IR 生成完成: {len(ir)} 字符")

    # 4) LLVM IR 优化
    if opt_level.upper() not in ('O0', '0'):
        if verbose:
            print(f"[4/4] 运行优化管线 (opt_level={opt_level})...")

        pipeline = OptimizationPipeline(opt_level=opt_level, verbose=verbose)
        optimized_ir = pipeline.run(ir)

        # 体积优化（Os/Oz 模式）
        if opt_level.upper() in ('OS', 'OZ', 'S', 'Z'):
            size_opt = SizeOptimizer()
            optimized_ir = size_opt.optimize(optimized_ir)
            if verbose:
                print(f"  [体积优化] {len(optimized_ir)} 字")

        # 启动时间优化（O3 模式）
        if opt_level.upper() in ('O3', '3'):
            startup_opt = StartupOptimizer()
            optimized_ir = startup_opt.optimize(optimized_ir)
            if verbose:
                print(f"  [启动优化] {len(optimized_ir)} 字")

        if verbose:
            summary = pipeline.get_summary()
            print(f"  优化完成: {summary['input_size']} -> {len(optimized_ir)} 字"
                  f" ({summary['reduction_pct']:+.1f}%), {summary['total_time']:.3f}s")

        ir = optimized_ir

    return ir


def compile_source_to_ir(source: str, output_ll: str = None, verbose: bool = False) -> str:
    """
    编译光明源码到 .ll 文件

    Args:
        source: 光明源码字符串
        output_ll: .ll 文件输出路径（可选）
        verbose: 是否输出详细信息

    Returns:
        .ll 文件路径
    """
    ir = compile_source(source, verbose=verbose)

    if output_ll is None:
        output_ll = 'output.ll'

    with open(output_ll, 'w', encoding='utf-8') as f:
        f.write(ir)

    if verbose:
        print(f"LLVM IR 已写入: {output_ll}")

    return output_ll


def compile_light(source_path: str, output_path: str = None, verbose: bool = False, optimize_level: int = 2, debug: bool = False):
    """
    编译 .light 文件为原生可执行文件

    Args:
        source_path: .light 源文件路径
        output_path: 输出 .exe 路径（默认与源文件同名）
        verbose: 是否输出详细信息
        optimize_level: 优化级别（0-3），默认 2
        debug: 是否生成 DWARF 调试信息
    """
    # 读取源码
    with open(source_path, 'r', encoding='utf-8') as f:
        source = f.read()

    if verbose:
        print(f"[1/5] 读取源码: {len(source)} 字符")

    # 生成 LLVM IR（传递优化级别）
    opt_level_str = f'O{optimize_level}'
    ir = compile_source(source, verbose=verbose, opt_level=opt_level_str)

    # 写入 .ll 文件
    base_path = output_path or source_path.replace('.light', '')
    if base_path.endswith('.exe'):
        base_path = base_path[:-4]
    ll_path = base_path + '.ll'

    with open(ll_path, 'w', encoding='utf-8') as f:
        f.write(ir)

    if verbose:
        print(f"  IR 已写入: {ll_path} ({len(ir)} 字符)")

    # 查找 clang
    clang = find_clang()
    if verbose:
        print(f"  使用编译器: {clang}")

    # 编译运行时库
    runtime_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    runtime_c = os.path.join(runtime_dir, 'runtime.c')
    runtime_o = base_path + '_runtime.o'

    opt_flag = f'-O{optimize_level}'
    debug_flags = ['-g'] if debug else []

    if verbose:
        print("[3/6] 编译运行时库...")

    result = subprocess.run(
        [clang, '-c', opt_flag, *debug_flags, runtime_c, '-o', runtime_o],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"运行时库编译失败:\n{result.stderr}")

    # 编译 .ll 为 .o
    if verbose:
        print("[3/5] 编译 LLVM IR...")

    ir_o = base_path + '.o'
    result = subprocess.run(
        [clang, '-c', opt_flag, *debug_flags, ll_path, '-o', ir_o],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"IR 编译失败:\n{result.stderr}")

    # 链接为 .exe
    exe_path = base_path + '.exe'
    if verbose:
        print(f"[5/6] 链接为 .exe...")

    link_args = [clang, ir_o, runtime_o, '-o', exe_path]
    if debug:
        link_args.append('-g')
    if not sys.platform.startswith('win'):
        link_args.append('-lm')

    result = subprocess.run(
        link_args,
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"链接失败:\n{result.stderr}")

    # 清理临时文件
    if verbose:
        print(f"[5/5] 清理临时文件...")

    for f in [ir_o, runtime_o]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass

    if verbose:
        size = os.path.getsize(exe_path)
        print(f"编译成功: {source_path} -> {exe_path} ({size} 字节)")

    return exe_path


def compile_light_typed(source_path: str, output_path: str = None, verbose: bool = False, target_platform: str = None, optimize_level: int = 2, debug: bool = False):
    """
    编译 .light 文件为原生可执行文件（typed 模式）

    使用 LightValue 结构体，算术运算直接操作原生类型。

    Args:
        source_path: .light 源文件路径
        output_path: 输出可执行文件路径（默认与源文件同名）
        verbose: 是否输出详细信息
        target_platform: 目标平台（win32/linux/darwin），默认自动检测
        optimize_level: 优化级别（0-3），默认 2
        debug: 是否生成 DWARF 调试信息
    """
    with open(source_path, 'r', encoding='utf-8') as f:
        source = f.read()

    if verbose:
        print(f"[1/5] 读取源码: {len(source)} 字符")

    opt_level_str = f'O{optimize_level}'
    ir = compile_source_typed(source, verbose=verbose, target_platform=target_platform,
                              debug=debug, opt_level=opt_level_str)

    base_path = output_path or source_path.replace('.light', '')
    base_path = _strip_exe_ext(base_path)
    ll_path = base_path + '.ll'

    with open(ll_path, 'w', encoding='utf-8') as f:
        f.write(ir)

    if verbose:
        print(f"  IR 已写入: {ll_path} ({len(ir)} 字符)")

    clang = find_clang()
    if verbose:
        print(f"  使用编译器: {clang}")

    # IR 验证：用 clang 解析 .ll 文件检查语法和结构正确性
    verify_ir_with_clang(ll_path, clang, verbose)

    # 编译 typed 运行时库
    runtime_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    runtime_c = os.path.join(runtime_dir, 'runtime_typed.c')
    runtime_o = base_path + '_runtime.o'

    opt_flag = f'-O{optimize_level}'
    debug_flags = ['-g'] if debug else []

    if verbose:
        print("[3/6] 编译 typed 运行时库...")

    result = subprocess.run(
        [clang, '-c', opt_flag, *debug_flags, runtime_c, '-o', runtime_o],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"运行时库编译失败:\n{result.stderr}")

    # 编译 .ll 为 .o
    if verbose:
        print("[4/6] 编译 LLVM IR...")

    ir_o = base_path + '.o'
    result = subprocess.run(
        [clang, '-c', opt_flag, *debug_flags, ll_path, '-o', ir_o],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"IR 编译失败:\n{result.stderr}")

    # 链接为可执行文件
    exe_ext = get_exe_extension()
    exe_path = base_path + exe_ext
    if verbose:
        print(f"[5/6] 链接为可执行文件...")

    link_args = [clang, ir_o, runtime_o, '-o', exe_path]
    if debug:
        link_args.append('-g')
    if not sys.platform.startswith('win'):
        link_args.append('-lm')

    result = subprocess.run(
        link_args,
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"链接失败:\n{result.stderr}")

    if verbose:
        print(f"[6/6] 清理临时文件...")

    for f in [ir_o, runtime_o]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass

    if verbose:
        size = os.path.getsize(exe_path)
        print(f"编译成功: {source_path} -> {exe_path} ({size} 字节)")

    return exe_path


def verify_ir_with_clang(ll_path: str, clang_path: str = None, verbose: bool = False) -> bool:
    """使用 clang 验证 LLVM IR 文件的语法和结构正确性

    通过 `clang -c -x ir file.ll -o NUL` 让 clang 解析 .ll 文件，
    如果 IR 有语法错误或结构问题（如基本块未终止、类型不匹配等），
    clang 会返回非零退出码并输出错误信息。

    Args:
        ll_path: .ll 文件路径
        clang_path: clang 可执行文件路径（默认自动查找）
        verbose: 是否输出详细信息

    Returns:
        True 表示验证通过

    Raises:
        RuntimeError: IR 验证失败时抛出，包含 clang 的错误信息
    """
    if clang_path is None:
        clang_path = find_clang()

    if verbose:
        print("  验证 LLVM IR (clang -x ir)...")

    result = subprocess.run(
        [clang_path, '-c', '-x', 'ir', ll_path, '-o', os.devnull],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"LLVM IR 验证失败（clang -x ir）:\n{result.stderr}")

    if verbose:
        print("  IR 验证通过")
    return True


def find_clang():
    """查找 clang 编译器（支持 MSVC 和 MinGW 两种模式）"""
    import sys as _sys
    
    # 常见路径（优先 MinGW，因为它自带 C 标准库头文件）
    candidates = [
        # MinGW-w64 LLVM 工具链（自带 C 标准库）
        r'c:\traework\light\llvm-mingw-20240619-ucrt-x86_64\bin\clang.exe',
        r'E:\Program Files\LLVM\bin\clang.exe',
        r'C:\Program Files\LLVM\bin\clang.exe',
        r'D:\Program Files\LLVM\bin\clang.exe',
        '/usr/bin/clang',
        '/usr/local/bin/clang',
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # 从 PATH 查找
    for path in os.environ.get('PATH', '').split(os.pathsep):
        clang_path = os.path.join(path, 'clang.exe' if _sys.platform == 'win32' else 'clang')
        if os.path.exists(clang_path):
            return clang_path
        # 也查找 mingw 版本的 clang
        mingw_clang = os.path.join(path, 'x86_64-w64-mingw32-clang.exe')
        if os.path.exists(mingw_clang):
            return mingw_clang
    raise RuntimeError("未找到 clang 编译器。请安装 LLVM:\n  Windows: https://github.com/llvm/llvm-project/releases\n  macOS: brew install llvm\n  Linux: sudo apt install clang")


def compile_modules_typed(sources: dict, main_module: str = None, verbose: bool = False,
                          target_platform: str = None, debug: bool = False,
                          opt_level: str = 'O2') -> str:
    """
    编译多个光明模块为合并的 LLVM IR（typed 模式）

    使用单个 codegen 实例编译所有模块，避免全局常量和声明重复。

    Args:
        sources: 模块名 -> 源码字符串 的字典
        main_module: 主模块名（生成 main 函数的模块），默认为第一个
        verbose: 是否输出详细信息
        target_platform: 目标平台
        debug: 是否生成 DWARF 调试信息
        opt_level: 优化级别 ('O0', 'O1', 'O2', 'O3', 'Os', 'Oz')，默认 'O2'

    Returns:
        合并的 LLVM IR 字符串
    """
    if not sources:
        raise ValueError("没有源文件可编译")

    if main_module is None:
        main_module = list(sources.keys())[0]

    if verbose:
        print(f"[1/3] 多模块编译: {len(sources)} 个模块")
        for mod_name, src in sources.items():
            print(f"  - {mod_name}: {len(src)} 字符")

    parser = LightParser()
    adapter = AstAdapter()

    # 第一步：解析所有模块，收集 AST
    modules = {}
    for mod_name, source in sources.items():
        if verbose:
            print(f"[2/3] 解析模块: {mod_name}")

        v3_module = parser.parse(source)
        if v3_module is None:
            errors = '\n'.join(parser.errors) if hasattr(parser, 'errors') and parser.errors else "未知解析错误"
            raise RuntimeError(f"模块 {mod_name} 解析失败:\n{errors}")

        module = adapter.convert_module(v3_module)
        module.name = mod_name
        modules[mod_name] = module

    # 第二步：使用单个 codegen 实例编译所有模块
    if verbose:
        print(f"[3/3] 生成合并 IR（{len(modules)} 个模块）")

    codegen = TypedLLVMCodeGen(target_platform=target_platform, debug=debug)

    # 初始化运行时声明（只做一次）
    codegen.declare_runtime()
    codegen._declare_typed_runtime()

    # 初始化调试信息（DWARF）
    if debug:
        codegen._gen_debug_compile_unit()
        codegen._gen_debug_types()

    # 收集所有模块的导入和段落
    all_module_list = list(modules.values())
    main_mod = modules.get(main_module, all_module_list[0])

    # 先处理所有模块的导入语句（记录导入映射）
    for mod in all_module_list:
        codegen._process_imports(mod)

    # 收集所有模块的语句、类和段落（先收集，再生成）
    for mod in all_module_list:
        for stmt in mod.statements:
            if isinstance(stmt, ast.ImportStatement):
                continue
            if isinstance(stmt, ast.ExportStatement):
                continue
            codegen._collect_statement(stmt)
        if hasattr(mod, 'classes'):
            for cls_def in mod.classes:
                codegen._collect_class(cls_def)
        # 收集接口定义（Level 7）
        if hasattr(mod, 'interfaces'):
            for iface_def in mod.interfaces:
                codegen._collect_interface(iface_def)
        for seg in mod.segments:
            codegen._collect_segment(seg)

    # 生成导入的外部段函数声明（仅声明那些不在本地定义的符号）
    # 由于所有模块都在同一个 codegen 中，大部分导入符号都有本地定义
    # 这里只生成真正外部的（不在 _segments 中的）
    # 注意：_module_decls 中的名称是 "模块名_符号名" 经过 safe_func_name 转换的
    # 我们需要跳过那些已经在本地有定义的符号
    local_seg_safe_names = set()
    for seg_name in codegen._segments:
        safe = codegen._safe_func_name(seg_name)
        local_seg_safe_names.add(safe)
        # 同时把模块前缀的也加入（因为导出别名会生成这些名字）
        # 但别名和 define 不会冲突，只有 declare 和 define/alias 会冲突
        # 所以我们只需要从 _module_decls 中移除那些已经有本地定义的
    
    # 过滤 _module_decls：只保留真正外部的（不在本地段名中的）
    # 注意：_module_decls 中的名称是 safe name（如 f2），我们需要反向映射
    # 更简单的方法：直接清空 _module_decls，因为多模块编译时所有符号都有定义
    codegen._module_decls = []
    # 但为了未来支持真正的外部模块（如动态链接库），我们保留机制，只是当前清空

    # 生成全局初始化
    codegen._gen_global_init()

    # 生成类方法
    for cls_name, cls_def in codegen._classes.items():
        codegen._gen_typed_class_methods(cls_name, cls_def)

    # 生成所有段落函数
    for seg_name in codegen._segment_order:
        params = codegen._segments[seg_name]
        body = codegen._segment_bodies.get(seg_name, [])
        codegen._gen_typed_segment(seg_name, params, body)

    # 为所有模块生成导出名别名
    for mod in all_module_list:
        codegen._gen_exported_aliases(mod)

    # 生成 main 函数（主模块的顶层语句）
    codegen._gen_typed_main()

    ir = codegen.finalize()

    # IR 生成阶段验证
    errors = codegen._verify_module_ir(codegen._lines)
    if errors:
        error_msg = '\n'.join(f"  - {e}" for e in errors)
        raise RuntimeError(f"LLVM IR 验证失败，发现 {len(errors)} 个问题:\n{error_msg}")

    # 优化合并后的 IR
    if opt_level.upper() not in ('O0', '0'):
        pipeline = OptimizationPipeline(opt_level=opt_level, verbose=verbose)
        ir = pipeline.run(ir)

        if opt_level.upper() in ('OS', 'OZ', 'S', 'Z'):
            size_opt = SizeOptimizer()
            ir = size_opt.optimize(ir)

        if opt_level.upper() in ('O3', '3'):
            startup_opt = StartupOptimizer()
            ir = startup_opt.optimize(ir)

    return ir


def compile_light_project(source_path: str, output_path: str = None, verbose: bool = False, target_platform: str = None, optimize_level: int = 2, debug: bool = False):
    """
    编译光明项目为原生可执行文件（支持多模块）

    自动解析导入语句，递归编译依赖的模块，合并 IR 后编译。

    Args:
        source_path: 主源文件路径
        output_path: 输出路径
        verbose: 是否输出详细信息
        target_platform: 目标平台
        optimize_level: 优化级别（0-3），默认 2
        debug: 是否生成 DWARF 调试信息
    """
    try:
        from ..module_resolver import ModuleResolver
    except ImportError:
        from module_resolver import ModuleResolver

    with open(source_path, 'r', encoding='utf-8') as f:
        source = f.read()

    source_dir = os.path.dirname(os.path.abspath(source_path))
    resolver = ModuleResolver(search_paths=[source_dir])

    # 递归收集所有依赖的模块
    sources = {}
    visited = set()

    def collect_modules(src, mod_name):
        if mod_name in visited:
            return
        visited.add(mod_name)
        sources[mod_name] = src

        # 解析导入
        parser = LightParser()
        v3_mod = parser.parse(src)
        if v3_mod is None:
            return
        adapter = AstAdapter()
        module = adapter.convert_module(v3_mod)
        for imp in (getattr(module, 'imports', None) or []):
            dep_name = imp.module if hasattr(imp, 'module') else None
            if dep_name and dep_name not in visited:
                dep_path = resolver.find_module(dep_name)
                if dep_path and os.path.exists(dep_path):
                    with open(dep_path, 'r', encoding='utf-8') as f:
                        dep_src = f.read()
                    collect_modules(dep_src, dep_name)

    main_name = os.path.splitext(os.path.basename(source_path))[0]
    collect_modules(source, main_name)

    if verbose:
        print(f"[1/4] 收集到 {len(sources)} 个模块: {', '.join(sources.keys())}")

    # 编译所有模块（传递优化级别）
    opt_level_str = f'O{optimize_level}'
    ir = compile_modules_typed(sources, main_module=main_name, verbose=verbose,
                               target_platform=target_platform, debug=debug,
                               opt_level=opt_level_str)

    # 写入 .ll 文件
    base_path = output_path or source_path.replace('.light', '')
    base_path = _strip_exe_ext(base_path)
    ll_path = base_path + '.ll'

    with open(ll_path, 'w', encoding='utf-8') as f:
        f.write(ir)

    if verbose:
        print(f"  IR 已写入: {ll_path} ({len(ir)} 字符)")

    clang = find_clang()
    if verbose:
        print(f"  使用编译器: {clang}")

    # IR 验证
    verify_ir_with_clang(ll_path, clang, verbose)

    # 编译 typed 运行时库
    runtime_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    runtime_c = os.path.join(runtime_dir, 'runtime_typed.c')
    runtime_o = base_path + '_runtime.o'

    opt_flag = f'-O{optimize_level}'
    debug_flags = ['-g'] if debug else []

    if verbose:
        print("[3/5] 编译 typed 运行时库...")

    result = subprocess.run(
        [clang, '-c', opt_flag, *debug_flags, runtime_c, '-o', runtime_o],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"运行时库编译失败:\n{result.stderr}")

    # 编译 .ll 为 .o
    if verbose:
        print("[4/5] 编译 LLVM IR...")

    ir_o = base_path + '.o'
    result = subprocess.run(
        [clang, '-c', opt_flag, *debug_flags, ll_path, '-o', ir_o],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"IR 编译失败:\n{result.stderr}")

    # 链接为可执行文件
    exe_ext = get_exe_extension()
    exe_path = base_path + exe_ext
    if verbose:
        print(f"[5/5] 链接为可执行文件...")

    link_args = [clang, ir_o, runtime_o, '-o', exe_path]
    if debug:
        link_args.append('-g')
    if not sys.platform.startswith('win'):
        link_args.append('-lm')

    result = subprocess.run(
        link_args,
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"链接失败:\n{result.stderr}")

    if verbose:
        for f in [ir_o, runtime_o]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass
        size = os.path.getsize(exe_path)
        print(f"编译成功: {source_path} -> {exe_path} ({size} 字节)")

    return exe_path


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='光明 LLVM 编译器')
    ap.add_argument('source', help='.light 源文件')
    ap.add_argument('output', nargs='?', help='输出 .exe 路径')
    ap.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    ap.add_argument('--ir-only', action='store_true', help='仅生成 LLVM IR，不编译为 .exe')
    args = ap.parse_args()

    try:
        if args.ir_only:
            source = open(args.source, 'r', encoding='utf-8').read()
            output_ll = (args.output or args.source).replace('.light', '.ll')
            compile_source_to_ir(source, output_ll, verbose=True)
        else:
            compile_light(args.source, args.output, verbose=args.verbose or True)
    except Exception as e:
        print(f"编译错误: {e}", file=sys.stderr)
        sys.exit(1)