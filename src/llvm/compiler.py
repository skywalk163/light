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


class NativeImportError(RuntimeError):
    """原生腿导入不可用：模块要么是纯 Python（无 .light 实现），
    要么 .light 是 decl 0 空壳、实现在同名 .py 里。原生腿不加载 Python，
    这类模块必须显式报错，决不静默降级成「跑起来就崩」的产物。"""


def _is_decl0_shell(light_path) -> bool:
    """判定一个 .light 文件是否是 decl 0 空壳（无段落、无类的纯导出清单）。
    与同名 .py 配对出现时空壳 = 实现在 .py 的 shadow。"""
    try:
        with open(light_path, 'r', encoding='utf-8') as f:
            source = f.read()
        v3_module = LightParser().parse(source)
        if v3_module is None:
            return True
        module = AstAdapter().convert_module(v3_module)
        has_seg = len(getattr(module, 'segments', None) or []) > 0
        has_cls = len(getattr(module, 'classes', None) or []) > 0
        return not (has_seg or has_cls)
    except Exception:
        return False


def get_exe_extension(target_arch: str = None) -> str:
    """根据当前平台返回可执行文件后缀

    Args:
        target_arch: 目标架构（'x64'/'arm64'/None），None 表示本地架构
    """
    if sys.platform == 'win32':
        return '.exe'
    return ''


def get_link_libs() -> list:
    """按平台返回链接可执行文件所需的库参数

    这是全仓唯一的判据来源：生产链路（本文件三处链接点）与测试侧的 clang
    链接命令都必须调它，不允许各自硬编码——否则一边改了另一边不知道，
    就会出现「Windows 上全绿、FreeBSD 上整条 clang 腿链不上」这类只在
    另一个平台才暴露的红。

    - 非 Windows：libm 不自动链，缺 -lm 会 undefined symbol: sin/cos/pow/...
    - Windows：ws2_32 是 socket，secur32/crypt32 是 Schannel TLS 与证书链校验
    """
    if sys.platform == 'win32':
        return ['-lws2_32', '-lsecur32', '-lcrypt32']
    return ['-lm']


def get_lto_link_flags() -> list:
    """LTO 需要的参数（**编译侧与链接侧共用的唯一来源**）

    与 `get_link_libs()` 同一个道理：平台差异只许有一份。

    第七轮 A7 之前的形态是「编译侧 `get_optimization_flags()` 里判平台、
    三个链接点各自只 `append('-flto')`」，于是 Windows 上 `lto=True` 100% 链不上：
    默认链接器不支持 LTO，clang 直接 `error: LTO requires -fuse-ld=lld`。
    编译侧带了 `-fuse-ld=lld` 也没用 —— 那是链接器选择参数，必须出现在链接命令里。

    这条是外部 POSIX 验证那一轮实测出来的（`compile_light_typed(..., lto=True)`
    → `RuntimeError: 链接失败`），在此之前「LTO 未真跑」被记成未验证项。

    - win32：`-flto` + `-fuse-ld=lld`（默认链接器不认 LTO 字节码）
    - darwin：`-flto=full`（ld64 走全量 LTO；不再叠一个裸 `-flto`）
    - 其余（Linux/BSD）：`-flto=auto`（让 clang 按核数选并行 ThinLTO）
    """
    if sys.platform == 'win32':
        return ['-flto', '-fuse-ld=lld']
    if sys.platform == 'darwin':
        return ['-flto=full']
    return ['-flto=auto']


def _strip_exe_ext(path: str) -> str:
    """移除路径中的可执行文件后缀（跨平台）"""
    ext = get_exe_extension()
    if ext and path.endswith(ext):
        return path[:-len(ext)]
    return path


def detect_target_arch(target_arg: str = None) -> str:
    """检测目标架构

    根据 --target 参数或 -arch 参数自动选择 x64/ARM64 目标三元组。

    Args:
        target_arg: 目标架构参数（如 'x86_64'、'aarch64'、'arm64'、'x64'）

    Returns:
        目标架构字符串：'x86_64' 或 'aarch64'
    """
    if target_arg is None:
        return 'x86_64'

    target_lower = target_arg.lower().replace('-', '_').replace(' ', '_')

    # ARM64 架构匹配
    if any(t in target_lower for t in ('aarch64', 'arm64', 'armv8')):
        return 'aarch64'

    # x86_64 架构匹配
    if any(t in target_lower for t in ('x86_64', 'x64', 'amd64', 'x86')):
        return 'x86_64'

    # 默认返回本地架构
    import platform as _platform
    machine = _platform.machine().lower()
    if machine in ('aarch64', 'arm64', 'armv8l', 'armv8b'):
        return 'aarch64'
    return 'x86_64'


def get_target_triple(target_arch: str, target_platform: str = None) -> str:
    """获取 LLVM 目标三元组

    Args:
        target_arch: 目标架构（'x86_64'/'aarch64'）
        target_platform: 目标平台（win32/linux/darwin），None 表示当前平台

    Returns:
        LLVM 目标三元组字符串
    """
    if target_platform is None:
        target_platform = sys.platform

    os_part = {
        'win32': 'windows-msvc',
        'linux': 'linux-gnu',
        'darwin': 'macosx',
    }.get(target_platform, 'linux-gnu')

    if target_arch == 'aarch64':
        if target_platform == 'win32':
            return 'aarch64-pc-windows-msvc'
        elif target_platform == 'darwin':
            return 'arm64-apple-macosx'
        else:
            return 'aarch64-unknown-linux-gnu'
    else:
        if target_platform == 'win32':
            return 'x86_64-pc-windows-msvc'
        elif target_platform == 'darwin':
            return 'x86_64-apple-macosx'
        else:
            return 'x86_64-unknown-linux-gnu'


def get_optimization_flags(optimize_level: int, optimize_size: bool = False,
                           lto: bool = False) -> list:
    """根据优化级别返回 clang 编译参数

    只发 clang 自己认的档位标志（`-O0`/`-O1`/`-O2`/`-O3`、`-Os`、`-flto`），
    **不再用 `-mllvm` 传 legacy pass 名**。

    为什么去掉 `-mllvm -inline -mem2reg -loop-unroll -loop-rotate -gvn
    -loop-vectorize -slp-vectorize -licm -simplifycfg`（第七轮 A7 裁决 (a)）：

    1. 这些名字属于 LLVM 的 legacy PassManager。clang 从新 PassManager 起不再
       注册它们，clang 22 上每一个都报 `Unknown command line argument '-inline'`
       并让整条 clang 调用退非零 —— 于是 O1/O2/O3 全部编译失败，而
       `compile --backend llvm-typed` 的默认档就是 O2（`cli/light.py`），
       也就是「默认档不可用」。
    2. `-O2` 本身就是一整套新 PM 管线（含 inline/mem2reg/gvn/licm/simplifycfg/
       向量化），手动再塞同名 pass 是在重复它、而且顺序更差。
    3. 按 clang 版本探测分支（方案 b）会把版本矩阵引进来：本机 clang 22、
       CI 是 FreeBSD 另一套，两边行为分叉的成本高于收益。

    代价：失去「精细控制 pass 顺序」这一从未被任何用例验证过的能力。

    Args:
        optimize_level: 优化级别（0-3）
        optimize_size: 是否启用 -Os 尺寸优化（覆盖 optimize_level 的 -Ox 标志）
        lto: 是否启用 LTO (Link Time Optimization)

    Returns:
        clang 编译参数列表
    """
    if optimize_size:
        flags = ['-Os', '-fdata-sections', '-ffunction-sections']
        if sys.platform != 'darwin':
            flags.extend(['-Wl,--gc-sections'])
        else:
            flags.extend(['-Wl,-dead_strip'])
    else:
        flags = [f'-O{optimize_level}']

    # LTO (Link Time Optimization)：参数表在 get_lto_link_flags() 里单点维护，
    # 链接侧三个点调的是同一个函数——平台差异不许有第二份。
    if lto:
        flags.extend(get_lto_link_flags())

    return flags


def get_size_reduction_summary(original_size: int, stripped_size: int) -> str:
    """生成体积缩减报告

    Args:
        original_size: 原始文件大小（字节）
        stripped_size: 优化后文件大小（字节）

    Returns:
        格式化的体积缩减报告字符串
    """
    reduction = original_size - stripped_size
    reduction_pct = (reduction / max(original_size, 1)) * 100
    return (
        f"体积优化摘要:\n"
        f"  - 优化前: {_format_size(original_size)}\n"
        f"  - 优化后: {_format_size(stripped_size)}\n"
        f"  - 缩减:   {_format_size(reduction)} ({reduction_pct:.1f}%)"
    )


def _format_size(size_bytes: int) -> str:
    """将字节数格式化为人类可读的大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


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
                         target_arch: str = None, debug: bool = False, opt_level: str = 'O2') -> str:
    """
    编译光明源码为 LLVM IR 字符串（typed 模式）

    Args:
        source: 光明源码字符串
        verbose: 是否输出详细信息
        target_platform: 目标平台（win32/linux/darwin），默认自动检测
        target_arch: 目标架构（'x86_64'/'aarch64'），影响数据模型选择
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

    codegen = TypedLLVMCodeGen(target_platform=target_platform, target_arch=target_arch, debug=debug)
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


def _module_has_imports(source: str) -> bool:
    """检测光明源码是否含**模块级**导入，决定原生腿是否走多模块编译。"""
    try:
        v3_module = LightParser().parse(source)
        module = AstAdapter().convert_module(v3_module)
        return bool(getattr(module, 'imports', None) or [])
    except Exception:
        return False


def compile_light_typed(source_path: str, output_path: str = None, verbose: bool = False,
                        target_platform: str = None, target: str = None,
                        optimize_level: int = 2, debug: bool = False,
                        optimize_size: bool = False, lto: bool = False, strip: bool = False):
    """
    编译 .light 文件为原生可执行文件（typed 模式）

    使用 LightValue 结构体，算术运算直接操作原生类型。

    单文件无导入时走本函数的快速路径（单模块 IR）；一旦源文件含模块级导入，
    就委托 `compile_light_project` 递归解析依赖、合并多模块 IR 后统一编译，
    从而让 `导入`/`从 X 导入 Y` 在原生腿真解析（B9 S1 2.3）。
    同名 `.py` 影子模块在该路径会被显式拒绝（`NativeImportError`）。

    Args:
        source_path: .light 源文件路径
        output_path: 输出可执行文件路径（默认与源文件同名）
        verbose: 是否输出详细信息
        target_platform: 目标平台（win32/linux/darwin），默认自动检测
        target: 目标架构（'x86_64'/'aarch64'/'arm64'），默认本地架构
        optimize_level: 优化级别（0-3），默认 2
        debug: 是否生成 DWARF 调试信息
        optimize_size: 是否启用 -Os 尺寸优化（替代 -O2）
        lto: 是否启用 LTO (Link Time Optimization)
        strip: 是否剥离调试符号
    """
    with open(source_path, 'r', encoding='utf-8') as f:
        source = f.read()

    if verbose:
        print(f"[1/5] 读取源码: {len(source)} 字符")

    # B9 S1 2.3：有模块级导入 → 递归解析依赖，合并多模块后统一编译
    if _module_has_imports(source):
        return compile_light_project(
            source_path, output_path=output_path, verbose=verbose,
            target_platform=target_platform, target=target,
            optimize_level=optimize_level, debug=debug,
            optimize_size=optimize_size, lto=lto, strip=strip,
        )

    # 检测目标架构
    target_arch = detect_target_arch(target)
    if verbose:
        print(f"  目标架构: {target_arch}")

    # IR 侧始终走 O 档优化：体积优化交给 clang 的 -Os（get_optimization_flags），
    # 不在 IR 层跑 SizeOptimizer —— 它生成引用未定义值（%2..%70）的乱 IR（B9 实测：
    # `use of undefined value '%2'`）。`optimize_size` 只影响 clang 档位，是真正的体积优化点。
    opt_level_str = f'O{optimize_level}'
    ir = compile_source_typed(source, verbose=verbose, target_platform=target_platform,
                              target_arch=target_arch, debug=debug, opt_level=opt_level_str)

    base_path = output_path or source_path.replace('.light', '')
    base_path = _strip_exe_ext(base_path)
    ll_path = base_path + '.ll'

    with open(ll_path, 'w', encoding='utf-8') as f:
        f.write(ir)

    if verbose:
        print(f"  IR 已写入: {ll_path} ({len(ir)} 字符)")

    # 根据目标架构查找编译器
    clang = find_clang(target_arch=target_arch)
    if verbose:
        print(f"  使用编译器: {clang}")

    # IR 验证：用 clang 解析 .ll 文件检查语法和结构正确性
    verify_ir_with_clang(ll_path, clang, verbose)

    # 编译 typed 运行时库
    runtime_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    runtime_c = os.path.join(runtime_dir, 'runtime_typed.c')
    runtime_o = base_path + '_runtime.o'

    # 使用优化级别对应的编译参数
    opt_flags = get_optimization_flags(optimize_level, optimize_size=optimize_size, lto=lto)
    arch_flags = get_arch_specific_cflags(target_arch)
    debug_flags = ['-g'] if debug else []

    if verbose:
        print("[3/6] 编译 typed 运行时库...")

    result = subprocess.run(
        [clang, '-c', *opt_flags, *arch_flags, *debug_flags, runtime_c, '-o', runtime_o],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"运行时库编译失败:\n{result.stderr}")

    # 编译 .ll 为 .o
    if verbose:
        print("[4/6] 编译 LLVM IR...")

    ir_o = base_path + '.o'
    result = subprocess.run(
        [clang, '-c', *opt_flags, *arch_flags, *debug_flags, ll_path, '-o', ir_o],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"IR 编译失败:\n{result.stderr}")

    # 链接为可执行文件
    exe_ext = get_exe_extension()
    exe_path = base_path + exe_ext
    if verbose:
        print(f"[5/6] 链接为可执行文件...")

    link_args = [clang, *arch_flags, ir_o, runtime_o, '-o', exe_path]
    if debug:
        link_args.append('-g')
    link_args.extend(get_link_libs())
    if lto:
        link_args.extend(get_lto_link_flags())

    result = subprocess.run(
        link_args,
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"链接失败:\n{result.stderr}")

    # 剥离调试符号
    original_size = os.path.getsize(exe_path) if os.path.exists(exe_path) else 0
    if strip and not debug:
        try:
            if sys.platform == 'win32':
                for tool in ['llvm-strip', 'strip']:
                    try:
                        subprocess.run([tool, exe_path], capture_output=True, timeout=30)
                        break
                    except (subprocess.SubprocessError, FileNotFoundError):
                        continue
            else:
                subprocess.run(['strip', exe_path], check=True, timeout=30)
        except (subprocess.SubprocessError, OSError):
            if verbose:
                print("  [警告] 无法剥离调试符号")

    if verbose:
        print(f"[6/6] 清理临时文件...")

    for f in [ir_o, runtime_o]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass

    if verbose:
        final_size = os.path.getsize(exe_path)
        print(f"编译成功: {source_path} -> {exe_path} ({final_size} 字节)")
        if original_size > 0 and strip:
            print(get_size_reduction_summary(original_size, final_size))

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


def verify_ir_with_llvmlite(ll_path: str, verbose: bool = False) -> bool:
    """使用 llvmlite 本地验证 LLVM IR 文件的语法和结构正确性

    clang 不可用时的替代方案：调用 llvmlite.binding.parse_assembly + verify()
    做与 clang -x ir 等价的语法/结构验证，不依赖外部工具链。

    Args:
        ll_path: .ll 文件路径
        verbose: 是否输出详细信息

    Returns:
        True 表示验证通过

    Raises:
        RuntimeError: llvmlite 未安装或 IR 验证失败
    """
    try:
        import llvmlite.binding as _llvm
    except ImportError:
        raise RuntimeError(
            "llvmlite 未安装，且未找到 clang 编译器，无法验证 IR。\n"
            "请安装 clang（https://llvm.org）或运行 pip install llvmlite。"
        )

    if verbose:
        print("  验证 LLVM IR (llvmlite parse_assembly)...")

    try:
        with open(ll_path, 'r', encoding='utf-8') as f:
            ir_text = f.read()
        module = _llvm.parse_assembly(ir_text)
        module.verify()
    except Exception as e:  # noqa: BLE001 - 统一转为 RuntimeError 报告
        raise RuntimeError(f"LLVM IR 验证失败（llvmlite）:\n{e}") from e

    if verbose:
        print("  IR 验证通过（llvmlite）")
    return True


def verify_ir(ll_path: str, verbose: bool = False) -> bool:
    """验证 LLVM IR 文件（优先 clang，回退 llvmlite）

    优先使用 clang 验证；clang 不可用时回退到 llvmlite 本地验证，
    保证 IR 验证在任何环境下都真实执行（而非跳过）。

    Args:
        ll_path: .ll 文件路径
        verbose: 是否输出详细信息

    Returns:
        True 表示验证通过

    Raises:
        RuntimeError: 两种验证方式均不可用或验证失败
    """
    try:
        return verify_ir_with_clang(ll_path, verbose=verbose)
    except RuntimeError as e:
        if "未找到 clang" in str(e):
            return verify_ir_with_llvmlite(ll_path, verbose=verbose)
        raise


def find_clang(target_arch: str = None):
    """查找 clang 编译器（支持 MSVC 和 MinGW 两种模式）

    Args:
        target_arch: 目标架构（'x86_64'/'aarch64'/None），
                    指定 ARM64 时会检测交叉编译器

    Returns:
        clang 可执行文件路径
    """
    import sys as _sys

    # 显式覆盖，优先级最高：指到一个不存在的路径就等价于「本机没有 clang」。
    # 为什么需要这条：候选表里 `C:\Program Files\LLVM\bin\clang.exe`、
    # `/usr/bin/clang` 是硬编码绝对路径且排在 PATH 探测之前，所以「把 clang 从
    # PATH 里摘掉」根本模拟不出缺 clang（外部 POSIX 验证那轮实测：摘 PATH 后
    # 原生用例照跑 31 passed，不是 skip）。没有这条，「缺 clang 必须 skip 而不是
    # error」这条判据只能靠 monkeypatch `os.path.exists`，等于没有环境级判据。
    覆盖 = os.environ.get('LIGHT_CLANG')
    if 覆盖:
        if os.path.exists(覆盖):
            return 覆盖
        raise RuntimeError(
            f"LIGHT_CLANG 指向的路径不存在: {覆盖}\n"
            "（这个环境变量是显式覆盖，设了就不再回落候选表；"
            "指到不存在的路径即用于模拟「本机没有 clang」）")


    # 如果指定了 ARM64 目标，先尝试查找交叉编译器
    if target_arch == 'aarch64':
        arm64_candidates = get_arm64_cross_compiler_candidates()
        for c in arm64_candidates:
            if os.path.exists(c):
                return c

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


def get_arm64_cross_compiler_candidates() -> list:
    """获取 ARM64 交叉编译器候选路径

    Returns:
        ARM64 交叉编译器候选路径列表
    """
    import sys as _sys
    if _sys.platform == 'win32':
        return [
            # llvm-mingw ARM64 工具链
            r'c:\traework\light\llvm-mingw-20240619-ucrt-aarch64\bin\clang.exe',
            r'c:\traework\light\llvm-mingw-20240619-ucrt-x86_64\bin\clang.exe',
            # MSVC ARM64 交叉编译器
            r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\Llvm\bin\clang.exe',
            # 通用 ARM64 工具链
            r'E:\Program Files\LLVM\bin\clang.exe',
            r'C:\Program Files\LLVM\bin\clang.exe',
        ]
    elif _sys.platform == 'darwin':
        return [
            '/usr/bin/clang',
            '/usr/local/bin/clang',
            '/opt/homebrew/bin/clang',
        ]
    else:
        # Linux
        return [
            'aarch64-linux-gnu-gcc',
            'aarch64-linux-gnu-g++',
            '/usr/bin/aarch64-linux-gnu-gcc',
            '/usr/bin/clang',
            '/usr/local/bin/clang',
        ]


def get_arch_specific_cflags(target_arch: str) -> list:
    """获取架构特定的编译参数

    Args:
        target_arch: 目标架构（'x86_64'/'aarch64'）

    Returns:
        架构特定的编译参数列表
    """
    if target_arch == 'aarch64':
        return ['--target=aarch64-linux-gnu']
    return []


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
    # T7C：将主模块放到最后，使 __light_init 中先执行被导入模块的全局初始化，
    # 再执行主模块的顶层语句（后者可能调用导入段并读取导入模块的全局变量）。
    main_mod = modules.get(main_module)
    if main_mod is None:
        main_mod = list(modules.values())[0]
    all_module_list = [m for m in modules.values() if m is not main_mod] + [main_mod]

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
            # P0-2：顶层 段落 定义已通过 mod.segments 单独收集（见下方循环），
            # 这里必须跳过，否则会被塞进 _module_statements，在 _gen_global_init
            # 里走到 _gen_global_statement → _reject_unsupported_stmt(SegmentDefinition)。
            # 单模块 generate() 路径不存在此问题（段落只进 module.segments），
            # 多模块（含导入）路径才会触发，导致 `段落 主:` 入口在原生腿被拒。
            if isinstance(stmt, ast.SegmentDefinition):
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
            # T9A：传入模块名，使段注册表 key 和 fN 编号按模块隔离
            codegen._collect_segment(seg, module_name=mod.name)

    # 生成导入的外部段函数声明（仅声明那些不在本地定义的符号）
    # 由于所有模块都在同一个 codegen 中，大部分导入符号都有本地定义
    # 这里只生成真正外部的（不在 _segments 中的）
    # 注意：_module_decls 中的名称是 "模块名_符号名" 经过 safe_func_name 转换的
    # 我们需要跳过那些已经在本地有定义的符号
    local_seg_safe_names = set()
    for reg_key in codegen._segments:
        # T9A：reg_key 可能是 (module_name, raw_name) 元组
        raw = reg_key[1] if isinstance(reg_key, tuple) else reg_key
        mod = reg_key[0] if isinstance(reg_key, tuple) else None
        safe = codegen._safe_func_name(raw, mod)
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
    # T9A：设置当前模块为主模块，使全局初始化中的段调用解析到主模块上下文
    codegen._current_module = getattr(main_mod, 'name', None)
    codegen._gen_global_init()
    codegen._current_module = None

    # 生成类方法
    for cls_name, cls_def in codegen._classes.items():
        codegen._gen_typed_class_methods(cls_name, cls_def)

    # 生成所有段落函数
    for reg_key in codegen._segment_order:
        # T9A：reg_key 为 (module_name, raw_name)，解包后传入模块上下文
        seg_name = reg_key[1] if isinstance(reg_key, tuple) else reg_key
        mod_name = reg_key[0] if isinstance(reg_key, tuple) else None
        params = codegen._segments[reg_key]
        body = codegen._segment_bodies.get(reg_key, [])
        codegen._gen_typed_segment(seg_name, params, body, module_name=mod_name)

    # 为所有模块生成导出名别名
    for mod in all_module_list:
        codegen._gen_exported_aliases(mod)

    # 生成 main 函数（主模块的顶层语句）
    # T9A：设置当前模块为主模块，使 main 内的段调用解析到主模块的定义
    codegen._current_module = getattr(main_mod, 'name', None)
    codegen._gen_typed_main()
    codegen._current_module = None

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


def _native_search_paths(source_dir: str) -> list:
    """原生腿的模块搜索路径。

    此前原生腿只传 ``[source_dir]``，项目自带的 stdlib（如 lightharness/stdlib 下的
    SSE.light）根本解析不到，报「模块未找到: 'SSE'」——同一个项目用 src 后端却是好的，
    因为 ``ModuleResolver()`` 不传参时默认含 ``['.', 光明stdlib, contrib]``。

    这里按「自入口目录逐级向上找 stdlib」补齐，两种项目布局都能覆盖：
      - 入口在 src/ 下（lightharness/src/总入口.light）→ 祖先的 lightharness/stdlib
      - 入口就在项目根（proj/总入口.light）          → 自身的 proj/stdlib
    另外并入光明自带 stdlib/contrib，与 src 后端口径一致。
    """
    paths = []
    seen = set()

    def _add(p):
        p = os.path.abspath(p)
        if p not in seen:
            seen.add(p)
            paths.append(p)

    _add(source_dir)

    # 自入口目录向上找含 stdlib/ 的祖先（最多 6 层，避免一路走到磁盘根）
    cur = os.path.abspath(source_dir)
    for _ in range(6):
        parent = os.path.dirname(cur)
        if not parent or parent == cur:
            break
        cur = parent
        stdlib_candidate = os.path.join(cur, 'stdlib')
        if os.path.isdir(stdlib_candidate):
            _add(stdlib_candidate)
        _add(cur)

    # 光明自带 stdlib / contrib（与 ModuleResolver() 默认一致）
    _llvm_dir = os.path.dirname(os.path.abspath(__file__))       # .../src/llvm
    _light_root = os.path.dirname(os.path.dirname(_llvm_dir))    # 仓库根
    for cand in (os.path.join(_light_root, 'stdlib'),
                 os.path.join(_light_root, 'contrib')):
        if os.path.isdir(cand):
            _add(cand)

    _add(os.getcwd())
    return paths


def _is_python_module(name: str) -> bool:
    """该名字能否作为 Python 模块导入（即属 Python 标准库 / 第三方生态，而非光明模块）。

    仅用于给「找不到 .light 实现」的导入做**定性**，好让报错直指真因。
    查找顺序始终是「先 .light 后 Python」——调用方先 find_module，失败了才问这里，
    所以同名的 .light 模块永远优先，不会被误判成 Python 模块。
    """
    if not name or name.startswith('.'):
        return False
    try:
        import importlib.util
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, AttributeError, TypeError, OSError):
        # 点号名字的父包未导入等情形会抛异常，一律按「不是 Python 模块」处理
        return False


def compile_light_project(source_path: str, output_path: str = None, verbose: bool = False,
                          target_platform: str = None, target: str = None,
                          optimize_level: int = 2, debug: bool = False,
                          optimize_size: bool = False, lto: bool = False, strip: bool = False):
    """
    编译光明项目为原生可执行文件（支持多模块）

    自动解析导入语句，递归编译依赖的模块，合并 IR 后编译。

    Args:
        source_path: 主源文件路径
        output_path: 输出路径
        verbose: 是否输出详细信息
        target_platform: 目标平台
        target: 目标架构（'x86_64'/'aarch64'/'arm64'），默认本地架构
        optimize_level: 优化级别（0-3），默认 2
        debug: 是否生成 DWARF 调试信息
        optimize_size: 是否启用 -Os 尺寸优化（替代 -O2）
        lto: 是否启用 LTO (Link Time Optimization)
        strip: 是否剥离调试符号
    """
    # 检测目标架构
    target_arch = detect_target_arch(target)
    if verbose:
        print(f"  目标架构: {target_arch}")

    try:
        from ..module_resolver import ModuleResolver, ModuleNotFoundError
    except ImportError:
        from module_resolver import ModuleResolver, ModuleNotFoundError

    with open(source_path, 'r', encoding='utf-8') as f:
        source = f.read()

    source_dir = os.path.dirname(os.path.abspath(source_path))
    # 此前只搜 source_dir，项目自带 stdlib（lightharness/stdlib）里的模块解析不到。
    # 改为「入口目录 + 逐级向上找到的 stdlib + 光明自带 stdlib/contrib」。
    resolver = ModuleResolver(search_paths=_native_search_paths(source_dir))

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
                try:
                    dep_path = resolver.find_module(dep_name)
                except ModuleNotFoundError:
                    # 找不到 .light 实现：先定性——是不是在找 Python 生态的东西。
                    # 原生运行时是纯 C（runtime_typed.c，不嵌 CPython），没有 Python
                    # 互操作，这类导入原生腿根本做不到。必须直说，否则会报成
                    # 「需要其 .light 源文件」，让人去翻一个并不存在的 .light 文件。
                    if _is_python_module(dep_name):
                        raise NativeImportError(
                            f"'{mod_name}' 导入了 Python 生态/标准库模块 '{dep_name}'，"
                            f"原生腿无法编译：原生运行时是纯 C"
                            f"（src/llvm/runtime_typed.c，不嵌 CPython），"
                            f"没有 Python 互操作，也没有可链接的 Python 符号。\n"
                            f"  可选路径：\n"
                            f"    1) 改用 --backend src（解释后端，支持导入 Python 模块）；\n"
                            f"    2) 为 '{dep_name}' 提供纯光明 (.light) 实现后再导入。")
                    raise NativeImportError(
                        f"模块 '{dep_name}' 未找到：原生腿编译需要其 .light 源文件"
                        f"（由 '{mod_name}' 导入）。")
                # B9 S1 2.3：同名 .py 影子必须显式报错，绝不静默降级
                if dep_path.suffix == '.py':
                    raise NativeImportError(
                        f"模块 '{dep_name}' 在原生腿不可用：解析到的是 Python 文件 "
                        f"'{dep_path}'。原生腿不加载 .py；请在纯光明 (.light) 中实现 "
                        f"'{dep_name}' 后再导入。")
                py_twin = dep_path.with_suffix('.py')
                if py_twin.exists() and _is_decl0_shell(dep_path):
                    raise NativeImportError(
                        f"模块 '{dep_name}' 的 '{dep_path}' 是 decl 0 空壳"
                        f"（实现在同名 '{py_twin}'）。原生腿不加载 Python 实现，"
                        f"请在 .light 里提供真实实现后再导入。")
                with open(dep_path, 'r', encoding='utf-8') as f:
                    dep_src = f.read()
                collect_modules(dep_src, dep_name)

    main_name = os.path.splitext(os.path.basename(source_path))[0]
    collect_modules(source, main_name)

    if verbose:
        print(f"[1/4] 收集到 {len(sources)} 个模块: {', '.join(sources.keys())}")

    # 编译所有模块（传递优化级别）
    opt_level_str = 'Os' if optimize_size else f'O{optimize_level}'
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

    # 根据目标架构查找编译器
    clang = find_clang(target_arch=target_arch)
    if verbose:
        print(f"  使用编译器: {clang}")

    # IR 验证
    verify_ir_with_clang(ll_path, clang, verbose)

    # 编译 typed 运行时库
    runtime_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    runtime_c = os.path.join(runtime_dir, 'runtime_typed.c')
    runtime_o = base_path + '_runtime.o'

    # 使用优化级别对应的编译参数
    opt_flags = get_optimization_flags(optimize_level, optimize_size=optimize_size, lto=lto)
    arch_flags = get_arch_specific_cflags(target_arch)
    debug_flags = ['-g'] if debug else []

    if verbose:
        print("[3/5] 编译 typed 运行时库...")

    result = subprocess.run(
        [clang, '-c', *opt_flags, *arch_flags, *debug_flags, runtime_c, '-o', runtime_o],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"运行时库编译失败:\n{result.stderr}")

    # 编译 .ll 为 .o
    if verbose:
        print("[4/5] 编译 LLVM IR...")

    ir_o = base_path + '.o'
    result = subprocess.run(
        [clang, '-c', *opt_flags, *arch_flags, *debug_flags, ll_path, '-o', ir_o],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"IR 编译失败:\n{result.stderr}")

    # 链接为可执行文件
    exe_ext = get_exe_extension()
    exe_path = base_path + exe_ext
    if verbose:
        print(f"[5/5] 链接为可执行文件...")

    link_args = [clang, *arch_flags, ir_o, runtime_o, '-o', exe_path]
    if debug:
        link_args.append('-g')
    link_args.extend(get_link_libs())
    if lto:
        link_args.extend(get_lto_link_flags())

    result = subprocess.run(
        link_args,
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"链接失败:\n{result.stderr}")

    # 剥离调试符号
    original_size = os.path.getsize(exe_path) if os.path.exists(exe_path) else 0
    if strip and not debug:
        try:
            if sys.platform == 'win32':
                for tool in ['llvm-strip', 'strip']:
                    try:
                        subprocess.run([tool, exe_path], capture_output=True, timeout=30)
                        break
                    except (subprocess.SubprocessError, FileNotFoundError):
                        continue
            else:
                subprocess.run(['strip', exe_path], check=True, timeout=30)
        except (subprocess.SubprocessError, OSError):
            if verbose:
                print("  [警告] 无法剥离调试符号")

    if verbose:
        for f in [ir_o, runtime_o]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass
        final_size = os.path.getsize(exe_path)
        print(f"编译成功: {source_path} -> {exe_path} ({final_size} 字节)")
        if original_size > 0 and strip:
            print(get_size_reduction_summary(original_size, final_size))

    return exe_path


# ===========================================================================
# LLVMCompiler 类
# ===========================================================================


class LLVMCompiler:
    """光明 LLVM 编译器类

    封装了从 .light 源码到原生可执行文件的完整编译流水线。
    支持 Windows、macOS、Linux 三大平台，支持 x86_64 和 ARM64 架构。

    用法:
        compiler = LLVMCompiler()
        # 自动检测当前平台编译
        compiler.compile("hello.light")

        # 指定目标平台
        compiler.compile("hello.light", target="macos")
        compiler.compile("hello.light", target="linux")

        # 直接调用平台特定方法
        compiler.compile_to_macos("hello.light", "hello_macos")
        compiler.compile_to_linux("hello.light", "hello_linux")
    """

    # 平台映射表
    TARGET_PLATFORM_MAP = {
        "macos": "darwin",
        "mac": "darwin",
        "darwin": "darwin",
        "linux": "linux",
        "win": "win32",
        "windows": "win32",
        "win32": "win32",
    }

    def __init__(self, verbose: bool = False, optimize_level: int = 2,
                 debug: bool = False, optimize_size: bool = False,
                 lto: bool = False, strip: bool = False):
        """初始化 LLVM 编译器

        Args:
            verbose: 是否输出详细信息
            optimize_level: 优化级别（0-3），默认 2
            debug: 是否生成 DWARF 调试信息
            optimize_size: 是否启用 -Os 尺寸优化
            lto: 是否启用 LTO (Link Time Optimization)
            strip: 是否剥离调试符号
        """
        self.verbose = verbose
        self.optimize_level = optimize_level
        self.debug = debug
        self.optimize_size = optimize_size
        self.lto = lto
        self.strip = strip

    @staticmethod
    def detect_platform() -> str:
        """自动检测当前运行平台

        Returns:
            "win32" / "darwin" / "linux"
        """
        return sys.platform

    @staticmethod
    def detect_arch() -> str:
        """自动检测当前架构

        Returns:
            "x86_64" / "aarch64"
        """
        import platform as _p
        machine = _p.machine().lower()
        if machine in ('aarch64', 'arm64', 'armv8l', 'armv8b'):
            return 'aarch64'
        return 'x86_64'

    @staticmethod
    def resolve_target_platform(target: str = None) -> str:
        """解析目标平台参数

        Args:
            target: 目标平台名称（'macos'/'linux'/'windows' 或 None）

        Returns:
            平台标识（'darwin'/'linux'/'win32'）
        """
        if target is None:
            return sys.platform
        target_lower = target.lower().strip()
        mapped = LLVMCompiler.TARGET_PLATFORM_MAP.get(target_lower)
        if mapped:
            return mapped
        # 尝试部分匹配
        for key, val in LLVMCompiler.TARGET_PLATFORM_MAP.items():
            if key in target_lower or target_lower in key:
                return val
        # 默认返回当前平台
        return sys.platform

    def compile(self, source_path: str, output_path: str = None,
                target: str = None) -> str:
        """编译 .light 文件为原生可执行文件

        自动检测目标平台，选择合适的编译参数。
        仅走 typed 生产路径（`compile_light_typed`）；string 死腿（`compile_light`，
        引用不存在的 runtime.c）已在 B9 删除，不再回退。

        Args:
            source_path: .light 源文件路径
            output_path: 输出可执行文件路径（默认与源文件同名）
            target: 目标平台（'macos'/'linux'/'windows'/'auto'），
                    'auto' 或 None 表示自动检测当前平台

        Returns:
            可执行文件路径

        Raises:
            RuntimeError: 编译失败时抛出
        """
        # 解析目标平台
        target_platform = self.resolve_target_platform(target)

        if self.verbose:
            current_platform = sys.platform
            print(f"[LLVMCompiler] 当前平台: {current_platform}")
            print(f"[LLVMCompiler] 目标平台: {target_platform} (target={target})")
            print(f"[LLVMCompiler] 目标架构: {self.detect_arch()}")

        # 选择编译方法
        try:
            exe_path = compile_light_typed(
                source_path=source_path,
                output_path=output_path,
                verbose=self.verbose,
                target_platform=target_platform,
                target=self.detect_arch(),
                optimize_level=self.optimize_level,
                debug=self.debug,
                optimize_size=self.optimize_size,
                lto=self.lto,
                strip=self.strip,
            )
            return exe_path
        except Exception:
            if self.verbose:
                print("[LLVMCompiler] 原生编译失败，无 string 回退（string 死腿已在 B9 删除）")
            raise

    def compile_to_macos(self, source_path: str, output_path: str = None) -> str:
        """编译为 macOS 可执行文件

        强制指定目标平台为 macOS (darwin)，
        使用 macOS 对应的目标三元组（如 x86_64-apple-macosx 或 arm64-apple-macosx）。

        Args:
            source_path: .light 源文件路径
            output_path: 输出可执行文件路径（默认与源文件同名）

        Returns:
            可执行文件路径
        """
        if self.verbose:
            print(f"[LLVMCompiler] 目标: macOS ({self.detect_arch()})")

        return self.compile(source_path, output_path, target="darwin")

    def compile_to_linux(self, source_path: str, output_path: str = None) -> str:
        """编译为 Linux 可执行文件

        强制指定目标平台为 Linux，
        使用 Linux 对应的目标三元组（如 x86_64-unknown-linux-gnu 或 aarch64-unknown-linux-gnu）。

        Args:
            source_path: .light 源文件路径
            output_path: 输出可执行文件路径（默认与源文件同名）

        Returns:
            可执行文件路径
        """
        if self.verbose:
            print(f"[LLVMCompiler] 目标: Linux ({self.detect_arch()})")

        return self.compile(source_path, output_path, target="linux")

    def compile_to_windows(self, source_path: str, output_path: str = None) -> str:
        """编译为 Windows 可执行文件

        强制指定目标平台为 Windows，
        使用 Windows 对应的目标三元组（如 x86_64-pc-windows-msvc）。

        Args:
            source_path: .light 源文件路径
            output_path: 输出可执行文件路径（默认与源文件同名）

        Returns:
            可执行文件路径
        """
        if self.verbose:
            print(f"[LLVMCompiler] 目标: Windows ({self.detect_arch()})")

        return self.compile(source_path, output_path, target="win32")


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='光明 LLVM 编译器')
    ap.add_argument('source', help='.light 源文件')
    ap.add_argument('output', nargs='?', help='输出可执行文件路径')
    ap.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    ap.add_argument('--ir-only', action='store_true', help='仅生成 LLVM IR，不编译为 .exe')
    ap.add_argument('--optimize-size', action='store_true',
                    help='启用 -Os 尺寸优化，替代 -O2（可减少 30-50% 体积）')
    ap.add_argument('--lto', action='store_true',
                    help='启用 LTO (Link Time Optimization)，进一步优化体积和性能')
    ap.add_argument('--strip', action='store_true',
                    help='剥离调试符号，减小最终二进制体积')
    ap.add_argument('--target', choices=['auto', 'macos', 'linux', 'windows'],
                    default='auto',
                    help='目标平台（auto/macos/linux/windows，默认 auto 自动检测）')
    args = ap.parse_args()

    try:
        if args.ir_only:
            source = open(args.source, 'r', encoding='utf-8').read()
            output_ll = (args.output or args.source).replace('.light', '.ll')
            compile_source_to_ir(source, output_ll, verbose=True)
        else:
            compiler = LLVMCompiler(
                verbose=args.verbose or True,
                optimize_size=args.optimize_size,
                lto=args.lto,
                strip=args.strip,
            )
            if args.target == 'auto':
                compiler.compile(args.source, args.output)
            else:
                compiler.compile(args.source, args.output, target=args.target)
    except Exception as e:
        print(f"编译错误: {e}", file=sys.stderr)
        sys.exit(1)