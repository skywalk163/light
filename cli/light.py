#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明（Light）编译器命令行工具 — 统一入口（默认使用 SRC 后端）

用法：
  light run <源文件.light>            解释执行
  light compile <源文件.light> [-o 输出]  编译为 Python 文件
  light ast <源文件.light>            显示 AST
  light tokens <源文件.light>         显示 Token 流
  light --help
  light --version

示例：
  light run hello.light                # 用 SRC 后端执行（无需额外依赖）
  light run hello.light --backend antlr  # 用 ANTLR 后端执行（需安装 antlr4-python3-runtime）
  light compile hello.light -o out.py  # 编译为 Python
"""

import ast
import re
import sys
import os
import argparse
import subprocess
from pathlib import Path

# ── 路径设置 ──────────────────────────────────────────────────────
_CLI_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_CLI_DIR)

# 确保各模块路径可访问
sys.path.insert(0, os.path.join(_PROJECT_DIR, 'antlrparser'))
sys.path.insert(0, os.path.join(_PROJECT_DIR, 'src'))
sys.path.insert(0, _PROJECT_DIR)

# 从 version 模块导入版本信息
try:
    from src.version import DEV_BRANCH, VERSION as LANG_VERSION, is_dev_branch, get_dev_version_string
    VERSION = f'光明编译器 v{LANG_VERSION}'
    if is_dev_branch():
        VERSION = f'光明编译器 v{LANG_VERSION}dev (开发分支)'
except ImportError:
    VERSION = '光明编译器 v7.0.0'

# 反馈收集子命令
from feedback_collector import setup_feedback_subparser, run_feedback_cli


# ═══════════════════════════════════════════════════════════════════
# ANTLR 后端（默认）
# ═══════════════════════════════════════════════════════════════════

def _preprocess_v3(source: str) -> str:
    """预处理 v3 纯缩进语法（转换为带结束标记的形式）"""
    from indent_preprocessor import preprocess_v3_syntax
    return preprocess_v3_syntax(source)


def _run_antlr(source: str) -> str:
    """用 ANTLR 解释器执行代码，返回输出"""
    from light_visitor import LightParser
    from light_interpreter import Interpreter

    # 预处理 v3 语法
    processed_source = _preprocess_v3(source)

    parser = LightParser()
    module = parser.parse(processed_source)
    if module is None:
        errors = '\n'.join(parser.errors)
        raise RuntimeError(f"解析失败:\n{errors}")

    interpreter = Interpreter()
    interpreter.interpret(module)
    return interpreter.get_output()


def _ast_antlr(source: str):
    """用 ANTLR 后端构建并打印 AST"""
    from light_visitor import LightParser

    # 预处理 v3 语法
    processed_source = _preprocess_v3(source)

    parser = LightParser()
    module = parser.parse(processed_source)
    if module is None:
        errors = '\n'.join(parser.errors)
        raise RuntimeError(f"解析失败:\n{errors}")
    _print_ast(module)


# ═══════════════════════════════════════════════════════════════════
# SRC 后端（旧版）
# ═══════════════════════════════════════════════════════════════════

def _compile_src(source: str) -> str:
    """用 src 后端编译为 Python 代码"""
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    parser = LightParser()
    module = parser.parse(source)

    generator = PythonCodeGenerator()
    return generator.generate(module)


def _resolve_module_path(mod_name: str, base_dir: str):
    """把模块名解析为磁盘上的 .light / .py 文件（L-001 修复核心）。

    支持点号分层目录：
      - 平铺 `数据`              → `<base_dir>/数据.light`（或 .py）
      - 点号 `a.b.c`             → `<base_dir>/a/b/c.light`（或 .py）
      - 点号 `_import_test.数据` → `<base_dir>/_import_test/数据.light`

    原实现只认平铺 `<base_dir>/<mod_name>.light`，导致
    `从 子目录.模块 导入 符号` 永远找不到文件，运行期 `No module named`。
    """
    if not mod_name:
        return None
    from pathlib import Path
    parts = mod_name.split('.')
    base = Path(base_dir)
    for ext in ('.light', '.py'):
        cand = base.joinpath(*parts)
        if cand.suffix != ext:
            cand = cand.with_suffix(ext)
        if cand.is_file():
            return cand
    return None


def _resolve_local_imports(source: str, source_dir: str) -> dict:
    """解析源代码中的本地模块导入，递归查找所有 .light 依赖（含点号分层目录）。

    Returns:
        {module_name: compiled_python_code, ...}
        其中 module_name 保留原始点号形式（如 '_import_test.数据' 或 'pkg.sub.深层'），
        编译产物会被内联进主代码，import 语句随后被注释掉（见 _run_src）。

    L-001 修复点：
      1. 用 `_resolve_module_path` 解析点号分层模块（a.b.c → a/b/c.light）。
      2. 子导入基于「被解析模块自身所在目录」继续查找，而非入口目录，
         使分层包内的相对点号导入也能正确定位。
    """
    from light_parser_v3 import LightParser, ImportStmt
    from code_generator import PythonCodeGenerator

    parser = LightParser()
    module = parser.parse(source)
    if module is None:
        return {}

    def _collect_imports(mod):
        """从模块的 statements 中收集所有 ImportStmt"""
        result = []
        for stmt in getattr(mod, 'statements', None) or []:
            if isinstance(stmt, ImportStmt):
                result.append(stmt)
        return result

    result = {}
    visited = set()

    def _resolve_one(mod_name: str, base_dir: str):
        if mod_name in visited:
            return
        visited.add(mod_name)

        # 查找 .light / .py 文件（支持点号分层目录，L-001）
        mod_path = _resolve_module_path(mod_name, base_dir)
        if mod_path is None:
            return

        mod_src = mod_path.read_text(encoding='utf-8')
        mod_parser = LightParser()
        mod_module = mod_parser.parse(mod_src)
        if mod_module is None:
            return

        # 编译
        gen = PythonCodeGenerator()
        code = gen.generate(mod_module)
        result[mod_name] = code

        # 递归解析子导入（L-001 修正）：
        # - 点号模块名（a.b.c）是「从项目根目录出发的绝对包路径」，
        #   必须基于入口搜索根 source_dir 解析；否则包内子模块再导入点号模块
        #   （如 pkg/sub/内嵌.light 里的 `从 pkg.sub.深层 导入`）会落到
        #   pkg/sub/pkg/sub/深层.light 这种错误目录。
        # - 平铺模块名（相对/兄弟模块）才基于「被解析模块自身所在目录」解析。
        mod_dir = str(mod_path.parent)
        for imp in _collect_imports(mod_module):
            child_mod = imp.module_name
            if child_mod not in visited and getattr(imp, 'language', None) is None:
                child_base = source_dir if ('.' in child_mod) else mod_dir
                _resolve_one(child_mod, child_base)

    # 解析主文件的所有导入
    for imp in _collect_imports(module):
        mod_name = imp.module_name
        if getattr(imp, 'language', None) is None:
            _resolve_one(mod_name, source_dir)

    return result


def _run_src(source: str, file_path: str | None = None) -> str:
    """用 src 后端执行，返回输出（支持多模块依赖自动解析）"""
    import os
    from pathlib import Path

    # 解析本地模块依赖
    source_dir = os.path.dirname(os.path.abspath(file_path)) if file_path else os.getcwd()
    dep_modules = _resolve_local_imports(source, source_dir)

    # 编译主文件
    main_code = _compile_src(source)

    # 构建完整代码：依赖模块在前，主文件在后
    # 注意：生成的代码中 import 语句会引用光明模块名（如 '引擎'），
    # 而 Python 找不到这些模块。因此我们注入依赖模块的代码，
    # 并替换所有代码中的 "from 模块名 import" 为注释，
    # 因为依赖模块的代码已经定义了所有需要的符号。

    import re

    # 先收集所有代码（deps + main）到一个字符串
    combined_parts = []
    for mod_name, dep_code in dep_modules.items():
        combined_parts.append(f"# === 光明模块: {mod_name} ===\n")
        combined_parts.append(dep_code)
        combined_parts.append("\n")
    combined_parts.append(main_code)
    py_code = ''.join(combined_parts)

    # ── L-001：识别「点号 + 普通 import」(`导入 a.b.c` → `import a.b.c`) ──
    # 这类导入 Python 只会把顶层包 `a` 绑进命名空间，末段 `c` 不会绑定，
    # 导致 `c.符号` 成员访问 NameError。收集它们以便下面构造模块对象并绑定末段名。
    # （`从 a.b.c 导入 符号` 形式由下方注释替换直接把符号提到顶层，无需模块对象。）
    _dotted_plain_set = set()
    _dotted_plain_list = []  # (fullname, bind_name)
    try:
        from light_parser_v3 import LightParser as _LP, ImportStmt as _IS
        _main_ast = _LP().parse(source)
        for _stmt in getattr(_main_ast, 'statements', None) or []:
            if (isinstance(_stmt, _IS) and getattr(_stmt, 'language', None) is None
                    and getattr(_stmt, 'symbols', None) is None
                    and '.' in _stmt.module_name):
                _bind = _stmt.alias or _stmt.module_name.split('.')[-1]
                _dotted_plain_set.add(_stmt.module_name)
                _dotted_plain_list.append((_stmt.module_name, _bind))
    except Exception:
        _dotted_plain_list = []
        _dotted_plain_set = set()

    # 对所有代码，替换本地模块的 import 为注释
    for mod_name in dep_modules:
        py_code = re.sub(
            rf'^from\s+{re.escape(mod_name)}\s+import\s+.*$',
            f'# 已注入: from {mod_name} import ... (模块代码已内联)',
            py_code,
            flags=re.MULTILINE
        )
        # 点号普通 import 不在此处注释——下方会构造模块对象并替换该行
        if mod_name not in _dotted_plain_set:
            py_code = re.sub(
                rf'^import\s+{re.escape(mod_name)}\s*$',
                f'# 已注入: import {mod_name} (模块代码已内联)',
                py_code,
                flags=re.MULTILINE
            )

    # 执行
    output_lines = []
    import sys as _sys
    def _capture_print(*args, **kwargs):
        line = ' '.join(str(a) for a in args)
        output_lines.append(line)
        # 实时输出并立即刷新，避免运行中途异常导致缓冲内容（已打印的部分）丢失
        print(*args, **kwargs)
        _sys.stdout.flush()

    namespace = {'print': _capture_print, '__name__': '__main__'}
    if file_path:
        namespace['__file__'] = os.path.abspath(file_path)
    # 添加源文件目录到 Python 路径，确保 `导入 Python:` 能找到本地 .py 模块
    import sys
    sys.path.insert(0, source_dir)

    # ── L-001：为「点号普通 import」构造真正的模块对象并绑定末段名 ──
    # `导入 a.b.c` 生成 `import a.b.c`，Python 只绑定顶层包 `a`，末段 `c` 不绑定。
    # 这里把内联的模块代码执行进一个 ModuleType，注册进 sys.modules，并把末段名
    # （或 as 别名）绑定进执行命名空间，使 `c.符号` / `别名.符号` 成员访问可用。
    import types as _types
    for _full, _bind in _dotted_plain_list:
        _code = dep_modules.get(_full)
        if _code is None:
            continue
        _mod = _types.ModuleType(_full)
        _path = _resolve_module_path(_full, source_dir)
        if _path is not None:
            _mod.__file__ = str(_path)
        # 执行内联代码进独立模块命名空间（借 __file__ 让 stdlib 引导找到正确 stdlib）
        try:
            exec(compile(_code, _full, 'exec'), _mod.__dict__)
        except Exception:
            pass
        _sys.modules[_full] = _mod
        # 建立父包链，使 `a` / `a.b` 也可被访问
        _parts = _full.split('.')
        for _i in range(len(_parts) - 1):
            _pname = '.'.join(_parts[:_i + 1])
            _pm = _sys.modules.get(_pname)
            if _pm is None:
                _pm = _types.ModuleType(_pname)
                _sys.modules[_pname] = _pm
            _child = '.'.join(_parts[:_i + 2])
            if _child not in _sys.modules:
                _sys.modules[_child] = _mod
            setattr(_pm, _parts[_i + 1], _sys.modules[_child])
        # 末段 / 别名 绑定进执行命名空间，使 `c.符号` / `别名.符号` 可用
        namespace[_bind] = _mod
        # 同时把顶层包名（如 `pkg`）绑进命名空间，使 `pkg.sub.深层.符号`
        # 这类全路径成员访问也可用（Python 的 `import a.b.c` 本就只绑顶层包）。
        _top = _parts[0]
        if _top in _sys.modules:
            namespace[_top] = _sys.modules[_top]
        # 中性化原 import 行（模块对象已注册，无需 Python 再次发起 import）
        py_code = re.sub(
            rf'^import\s+{re.escape(_full)}(\s+as\s+\w+)?\s*$',
            f'# 已内联: import {_full} (模块对象已注册，"{_bind}" 已绑定)',
            py_code,
            flags=re.MULTILINE
        )

    try:
        exec(py_code, namespace)
    finally:
        # 执行后移除临时路径，避免影响后续调用
        if sys.path[0] == source_dir:
            sys.path.pop(0)
    return '\n'.join(output_lines)


def _tokens_src(source: str) -> list:
    """用 src 后端获取 Token 流"""
    from lexer import Lexer
    lexer = Lexer()
    return lexer.tokenize(source)


def _ast_src(source: str):
    """用 src 后端构建并打印 AST"""
    from light_parser_v3 import LightParser
    parser = LightParser()
    module = parser.parse(source)
    _print_ast(module)


# ═══════════════════════════════════════════════════════════════════
# 通用工具
# ═══════════════════════════════════════════════════════════════════

def _print_ast(node, indent=0):
    """递归打印 AST 节点"""
    prefix = "  " * indent
    node_type = type(node).__name__
    print(f"{prefix}{node_type}")

    if hasattr(node, '__dict__'):
        for key, value in node.__dict__.items():
            if isinstance(value, list):
                print(f"{prefix}  {key}:")
                for item in value:
                    if hasattr(item, '__dict__'):
                        _print_ast(item, indent + 2)
                    else:
                        print(f"{'  ' * (indent + 2)}{item}")
            elif hasattr(value, '__dict__'):
                print(f"{prefix}  {key}:")
                _print_ast(value, indent + 2)
            elif value is not None:
                print(f"{prefix}  {key}: {value}")


def _read_source(file_path: str) -> str:
    """读取源代码文件"""
    path = Path(file_path)
    if not path.exists():
        print(f"错误: 文件不存在: {file_path}", file=sys.stderr)
        sys.exit(1)
    return path.read_text(encoding='utf-8')


# ═══════════════════════════════════════════════════════════════════
# 子命令实现
# ═══════════════════════════════════════════════════════════════════

def cmd_harness(args):
    """light harness run：deepseek-harness MVP 的 CLI 包装（第五轮 D5）。

    把 --channel/--eval-set/--report/--concurrency/--rate/--retries/--delay 映射成
    HARNESS_* 环境变量，转发到 examples/harness/评测驱动.light 的 run。
    评测驱动.light 是 D5 的端到端主入口（读 JSONL → 并发跑 LLM → 打分 →
    Markdown+JSON 报告），CLI 包装只是让它有一个干净的入口，不重复实现。

    `--channel real` 走真实 DeepSeek（第六轮把真实通道从「临时文件跑完即删」
    改成常驻可选后端）；缺 DEEPSEEK_API_KEY 时驱动直接退 2，不降级回 mock。
    """
    if getattr(args, 'harness_cmd', None) != 'run':
        print("用法: light harness run [--channel mock|real] [--eval-set 路径] "
              "[--report 前缀] [--concurrency N] [--rate N] [--retries N] [--delay 秒] "
              "[--mode single|agent] [--tools off|on] [--price-in 单价] [--price-out 单价]",
              file=sys.stderr)

        sys.exit(1)

    评测驱动 = os.path.join(_PROJECT_DIR, "examples", "harness", "评测驱动.light")
    if not os.path.exists(评测驱动):
        print(f"错误: 未找到 harness 主入口 {评测驱动}", file=sys.stderr)
        sys.exit(2)
    # 参数 → 环境变量（未传的参数不覆盖，让 评测驱动.light 用它的默认值）
    参数表 = [
        ("channel", "HARNESS_CHANNEL"),
        ("eval_set", "HARNESS_EVAL_SET"),
        ("report", "HARNESS_REPORT"),
        ("concurrency", "HARNESS_CONCURRENCY"),
        ("rate", "HARNESS_RATE"),
        ("retries", "HARNESS_RETRIES"),
        ("delay", "HARNESS_DELAY_SEC"),
        # 第七轮 §4.2 冻结的三组：语义归 C7/D7，转发归 A7。
        # A7 排在合并顺序第 2 位，C7/D7 在后面，所以这里先只保证
        # 「参数被转发成正确的环境变量」，`.light` 侧何时消费与本条无关。
        ("mode", "HARNESS_MODE"),
        ("tools", "HARNESS_TOOLS"),
        ("price_in", "HARNESS_PRICE_IN"),
        ("price_out", "HARNESS_PRICE_OUT"),
    ]


    for 属性, 环境名 in 参数表:
        值 = getattr(args, 属性, None)
        # 注意判空口径：`if 值:` 会把 `--delay 0`、`--rate 0` 这类**有意义的 0**
        # 当假值静默丢弃，于是用户以为自己关掉了延迟、实际跑的是驱动默认 0.2s。
        # 只有「没传」才不覆盖，传了就一律转发。
        if 值 is not None:
            os.environ[环境名] = 值

    # 复用 cmd_run 的执行链路（src 后端，依赖内联 + import hook）
    run_args = argparse.Namespace(
        file=评测驱动,
        backend=args.backend,
        watch=False,
        verbose=args.verbose,
    )
    cmd_run(run_args)


def _native_backend_compile(file_path: str, backend: str, out_base: str,
                            opt_level: int, verbose: bool, optimize_size: bool = False):
    """走生产路径把 .light 编成可执行文件，返回 exe 路径

    与 `cmd_compile` 用的是同一批入口（`compile_light_typed`），
    刻意不另开一条链路：`run --backend native` 必须和
    `compile --backend native` 编出来的是同一个东西（B9 S1 2.2）。

    `native` 与 `llvm-typed` 等价，都走 `compile_light_typed`；
    `--backend llvm`（string 腿，引用不存在的 runtime.c）已在 B9 删除，不接受该值。
    """
    try:
        from src.llvm.compiler import compile_light_typed
    except ImportError:
        try:
            from llvm.compiler import compile_light_typed
        except ImportError:
            from ..llvm.compiler import compile_light_typed

    return compile_light_typed(file_path, out_base, verbose=verbose,
                              optimize_level=opt_level, optimize_size=optimize_size)


def _run_native(args):
    """原生后端的 run：编译到临时目录 → 执行产物 → 透传退出码

    三条硬口径：
    1. **产物一律落 `tempfile.TemporaryDirectory()`**，不写源码树（`.ll`/`.o`/
       `.exe` 都在临时目录里生灭）。
    2. **退出码原样透传**：源码里 `退出(3)` → 本命令 rc == 3。
       不做 `rc in [0,1]` 那种「反正非崩就算过」的处理。
    3. 编译失败时给一行人能读的错误（clang 的 stderr 摘要），
       traceback 只在 `--verbose` 下出现。
    """
    import tempfile

    opt_level = 2
    optimize_size = False
    优化 = getattr(args, 'optimize', None)
    if 优化 in ('Os', 'Oz'):
        optimize_size = True
    elif 优化 and 优化.startswith('O'):
        try:
            opt_level = int(优化[1:])
        except ValueError:
            opt_level = 2

    源文件 = args.file
    if not os.path.exists(源文件):
        print(f"错误: 文件不存在 {源文件}", file=sys.stderr)
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix='light_native_') as 临时目录:
        产物基名 = os.path.join(临时目录, Path(源文件).stem)


        try:
            exe = _native_backend_compile(源文件, args.backend, 产物基名,
                                          opt_level, args.verbose,
                                          optimize_size)
        except Exception as e:
            print(f"原生编译失败（--backend {args.backend}）: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        if not os.path.exists(exe):
            print(f"原生编译未产出可执行文件: {exe}", file=sys.stderr)
            sys.exit(1)

        # 不捕获子进程输出：让它直接写到本进程的 stdout/stderr，
        # 避免多一层编码转换（中文输出在 Windows 控制台上尤其容易被打坏）。
        结果 = subprocess.run([exe])
        sys.stdout.flush()
        if 结果.returncode != 0:
            sys.exit(结果.returncode)




def cmd_run(args):
    """解释执行光明源代码"""
    from enhanced_errors import format_error

    if args.backend in ('native', 'llvm-typed'):
        # 原生后端不是解释执行：编译到临时目录再跑产物
        if args.watch:
            print("错误: --watch 不支持原生后端（native/llvm-typed）", file=sys.stderr)
            sys.exit(1)
        _run_native(args)
        return

    if args.watch:

        from file_watcher import run_with_watch
        run_with_watch(args.file, backend=args.backend)
        return

    source = _read_source(args.file)

    try:
        if args.backend == 'src':
            # 输出已由 _run_src 实时打印（含异常前的部分），不再二次打印
            _run_src(source, file_path=args.file)
        else:
            _run_antlr(source)

    except SystemExit:
        # 运行期若经 光明 运行时走到 sys.exit（含非零码，代表运行期错误），
        # 必须原样上浮，不能当作成功（rc==0 会被护栏误判为通过）。
        raise
    except Exception as e:
        # 运行期错误（越界/除零/NameError…）必须「浮出水面」：打 stderr 且返回非零 rc，
        # 否则护栏（组合.py `_成功` / 冒烟.py）依赖的「rc==0 且 非空 stdout」会把它误判为成功。
        print(format_error(source, e), file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def cmd_compile(args):
    """编译光明源代码为 Python 文件或可执行文件"""
    source = _read_source(args.file)

    # 解析优化级别（'O0' -> 0, 'O1' -> 1, etc.；'Os'/'Oz' -> 体积优化）
    opt_level = 2
    optimize_size = False
    if args.optimize in ('Os', 'Oz'):
        optimize_size = True
    elif args.optimize and args.optimize.startswith('O'):
        try:
            opt_level = int(args.optimize[1:])
        except ValueError:
            opt_level = 2

    # 原生后端（native / llvm-typed，同一生产路径：compile_light_typed）。
    # --backend llvm（string 死腿，引用不存在的 runtime.c）已在 B9 S1 2.1 删除。
    if args.backend in ('native', 'llvm-typed'):
        try:
            from src.llvm.compiler import compile_light_typed, get_exe_extension
        except ImportError:
            try:
                from llvm.compiler import compile_light_typed, get_exe_extension
            except ImportError:
                from ..llvm.compiler import compile_light_typed, get_exe_extension
        # 默认输出名用平台扩展名（Windows .exe / 其他无后缀），不再硬编码 .exe（B9 S1 2.2）
        output = args.output or (Path(args.file).stem + get_exe_extension())
        try:
            compile_light_typed(args.file, output, verbose=args.verbose,
                               optimize_level=opt_level,
                               optimize_size=optimize_size, debug=args.debug)
            return
        except Exception as e:
            print(f"原生（{args.backend}）编译错误: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    try:
        if args.backend == 'src':
            py_code = _compile_src(source)
        else:
            # ANTLR 后端：使用 code_generator_unified 生成 Python
            from light_visitor import LightParser
            from code_generator_unified import UnifiedCodeGenerator

            # 预处理 v3 语法
            processed_source = _preprocess_v3(source)

            parser = LightParser()
            module = parser.parse(processed_source)
            if module is None:
                errors = '\n'.join(parser.errors)
                raise RuntimeError(f"解析失败:\n{errors}")
            generator = UnifiedCodeGenerator()
            py_code = generator.generate(module)

    except Exception as e:
        print(f"编译错误: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # 确定输出路径
    output_path = args.output or (Path(args.file).stem + '.py')
    output_path = Path(output_path)

    # 如果目标是 .exe，使用 PyInstaller 打包
    if output_path.suffix.lower() == '.exe':
        _compile_to_exe(py_code, output_path, args)
    else:
        output_path.write_text(py_code, encoding='utf-8')
        print(f"编译成功: {args.file} -> {output_path}")


def _compile_to_exe(py_code: str, exe_path: Path, args):
    """使用 PyInstaller 将 Python 代码打包为 .exe"""
    import tempfile
    import subprocess
    import shutil

    exe_name = exe_path.stem
    exe_dir = exe_path.parent.resolve()

    # 写入临时 .py 文件
    py_path = exe_dir / f"{exe_name}.py"
    py_path.write_text(py_code, encoding='utf-8')
    print(f"生成 Python 代码: {py_path}")

    # 调用 PyInstaller 打包
    print(f"正在打包为 .exe（使用 PyInstaller）...")
    try:
        result = subprocess.run(
            [
                sys.executable, '-m', 'PyInstaller',
                '--onefile', '--console',
                '--name', exe_name,
                '--distpath', str(exe_dir),
                '--workpath', str(exe_dir / 'build'),
                '--specpath', str(exe_dir / 'build'),
                str(py_path),
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=str(exe_dir),
        )
        if result.returncode != 0:
            # 输出 PyInstaller 的错误信息
            error_msg = result.stderr or result.stdout
            if error_msg:
                # 只显示最后几行关键错误
                lines = error_msg.strip().split('\n')
                error_detail = '\n'.join(lines[-10:])
                print(f"PyInstaller 错误:\n{error_detail}", file=sys.stderr)
            raise RuntimeError(f"PyInstaller 打包失败 (exit code {result.returncode})")

        # 清理构建文件
        build_dir = exe_dir / 'build'
        if build_dir.exists():
            shutil.rmtree(build_dir, ignore_errors=True)

        print(f"编译成功: {args.file} -> {exe_path}")

    except FileNotFoundError:
        print("错误: 未找到 PyInstaller。请运行: pip install pyinstaller", file=sys.stderr)
        print(f"已生成 Python 文件: {py_path}，可直接用 python 运行", file=sys.stderr)
        sys.exit(1)


def cmd_ast(args):
    """显示 AST"""
    source = _read_source(args.file)

    try:
        if args.backend == 'src':
            _ast_src(source)
        else:
            _ast_antlr(source)
    except Exception as e:
        print(f"AST 错误: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def cmd_tokens(args):
    """显示 Token 流"""
    source = _read_source(args.file)

    try:
        tokens = _tokens_src(source)
        print("Token 流:")
        print("-" * 60)
        for i, token in enumerate(tokens, 1):
            print(f"{i:3d}. {token}")
    except Exception as e:
        print(f"Token 分析错误: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def cmd_check(args):
    """语法检查：解析源代码但不执行"""
    from enhanced_errors import format_error
    source = _read_source(args.file)

    errors = []
    warnings = []
    module = None

    try:
        if args.backend == 'src':
            from light_parser_v3 import LightParser
            parser = LightParser()
            module = parser.parse(source)
            if module is None:
                first_unparsed = None
                for i in range(parser.pos, len(parser.tokens)):
                    t = parser.tokens[i]
                    if t.type.name not in ('NEWLINE', 'DEDENT', 'INDENT', 'DOT', 'EOF'):
                        first_unparsed = t
                        break
                if first_unparsed:
                    err_msg = f"解析失败：无法识别语法 '{first_unparsed.value}'"
                    formatted = format_error(source, Exception(err_msg), first_unparsed.line, first_unparsed.col)
                    errors.append(formatted)
                else:
                    errors.append("解析失败：返回空模块")
            else:
                # 检查是否有未消费的实质性 token（解析器提前停止）
                first_unparsed = None
                for i in range(parser.pos, len(parser.tokens)):
                    t = parser.tokens[i]
                    if t.type.name not in ('NEWLINE', 'DEDENT', 'INDENT', 'DOT', 'EOF'):
                        first_unparsed = t
                        break
                if first_unparsed:
                    err_msg = f"解析失败：无法识别语法 '{first_unparsed.value}'"
                    formatted = format_error(source, Exception(err_msg), first_unparsed.line, first_unparsed.col)
                    errors.append(formatted)
        else:
            from light_visitor import LightParser
            from code_generator_unified import UnifiedCodeGenerator
            processed_source = _preprocess_v3(source)
            parser = LightParser()
            module = parser.parse(processed_source)
            if module is None:
                for err in parser.errors:
                    errors.append(err)
    except Exception as e:
        # 使用增强错误格式化器
        try:
            formatted = format_error(source, e)
            errors.append(formatted)
        except Exception:
            errors.append(str(e))

    # 解析通过 ≠ 能跑：再走一遍代码生成，拦截「check 通过但 run 失败」的情况
    if not errors and module is not None and args.backend == 'src':
        try:
            from code_generator import PythonCodeGenerator
            generated = PythonCodeGenerator().generate(module)
            try:
                compile(generated, args.file, 'exec')
            except SyntaxError as se:
                errors.append(
                    f"代码生成结果非法（生成的 Python 无法编译）：{se.msg}"
                    f"（生成代码第 {se.lineno} 行）"
                )
        except Exception as e:
            errors.append(f"代码生成失败：{type(e).__name__}: {e}")

    # 简单统计
    lines = source.split('\n')
    def _is_comment_line(l):
        s = l.strip()
        return s.startswith('#') or s.startswith('//')
    stats = {
        'total_lines': len(lines),
        'code_lines': sum(1 for l in lines if l.strip() and not _is_comment_line(l)),
        'comment_lines': sum(1 for l in lines if _is_comment_line(l)),
    }

    print(f"📄 检查文件: {args.file}")
    print(f"   总行数: {stats['total_lines']}")
    print(f"   代码行: {stats['code_lines']}")
    print(f"   注释行: {stats['comment_lines']}")

    if errors:
        print(f"\n❌ 发现 {len(errors)} 个错误:")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        print(f"\n✅ 语法检查通过，未发现错误。")

    # 默认启用类型检查（除非显式指定 --no-type-check）
    if not getattr(args, 'no_type_check', False):
        _run_type_check(source, getattr(args, 'type_check', '表达式'), args.file)


def _run_type_check(source: str, level_str: str, file_path: str):
    """运行类型检查并输出结果"""
    from compiler import LightCompiler
    from core.config import TypeCheckLevel
    from enhanced_errors import format_error

    level_map = {
        '签名': TypeCheckLevel.SIGNATURE, 'signature': TypeCheckLevel.SIGNATURE,
        '变量': TypeCheckLevel.VARIABLE, 'variable': TypeCheckLevel.VARIABLE,
        '表达式': TypeCheckLevel.EXPRESSION, 'expression': TypeCheckLevel.EXPRESSION,
    }
    level = level_map.get(level_str, TypeCheckLevel.EXPRESSION)

    # 创建编译器实例并配置类型检查级别
    compiler = LightCompiler()
    compiler._config.type_check_level = level

    # 解析并运行类型检查
    try:
        result = compiler.compile(source, optimize=False)
    except Exception as e:
        print(format_error(source, e), file=sys.stderr)
        sys.exit(1)

    print(f"\n━━━ 类型检查（级别: {level_str}）━━━")

    if compiler.warnings:
        print(f"\n⚠ 警告 ({len(compiler.warnings)} 个):")
        for w in compiler.warnings:
            print(f"  {w}")

    type_errors = [e for e in compiler.errors if '类型错误' in e]
    if type_errors:
        print(f"\n❌ 类型错误 ({len(type_errors)} 个):")
        for e in type_errors:
            # 尝试提取行号并显示源码上下文
            import re
            line_match = re.search(r'第(\d+)行', e)
            if line_match:
                line_num = int(line_match.group(1))
                formatted = format_error(source, Exception(e), line_num)
                print(f"  {formatted}")
            else:
                print(f"  {e}")
        sys.exit(1)
    else:
        print("✅ 类型检查通过")


def cmd_type_check(args):
    """独立类型检查命令"""
    source = _read_source(args.file)
    _run_type_check(source, args.level, args.file)


def cmd_init(args):
    """初始化光明项目"""
    from templates import create_project, list_templates

    project_name = args.name
    project_dir = Path(project_name)

    if project_dir.exists():
        print(f"错误: 目录已存在: {project_dir}", file=sys.stderr)
        sys.exit(1)

    project_dir.mkdir(parents=True)

    template = create_project(project_dir, args.template)

    print(f"✅ 项目 '{project_name}' 初始化完成")
    print(f"   模板: {template.name} ({template.description})")
    print(f"   目录: {project_dir.resolve()}")
    print(f"   配置: light.json")
    print(f"   入口: 主.light")
    print(f"   目录结构:")
    print(f"     {project_name}/")
    print(f"     ├── light.json      项目配置文件")
    print(f"     ├── 主.light        入口文件")
    print(f"     ├── src/            源代码目录")
    print(f"     └── tests/          测试目录")
    print(f"\n可用命令:")
    print(f"   light pkg run                  运行项目")
    print(f"   light pkg build                编译项目")
    print(f"   light run {project_name}/主.light      直接运行入口")
    print(f"\n可用模板:")
    for t in list_templates():
        print(f"   {t['name']:8} - {t['description']}")


def _load_lightpub_index():
    """加载 lightpub 包索引"""
    try:
        from stdlib.lightpub.__index__ import PACKAGES, CATEGORIES, PRIORITY
        return PACKAGES, CATEGORIES, PRIORITY
    except ImportError:
        try:
            sys.path.insert(0, os.path.join(_PROJECT_DIR, 'stdlib'))
            from lightpub.__index__ import PACKAGES, CATEGORIES, PRIORITY
            return PACKAGES, CATEGORIES, PRIORITY
        except ImportError:
            return {}, {}, {}


CATEGORY_NAMES = {
    'dev': '开发工具', 'net': '网络通信', 'database': '数据库',
    'security': '安全加密', 'language': '语言特性', 'media': '多媒体',
    'graphics': '图形渲染', 'infrastructure': '基础设施', 'output': '输出生成',
}


def cmd_pkg_search(args):
    """按关键词搜索 lightpub 包"""
    # 远程搜索
    if getattr(args, 'remote', False):
        from package_installer import PackageInstaller
        project_root = Path(getattr(args, 'project', '.')).resolve()
        registry_url = getattr(args, 'registry_url', None)
        if not registry_url:
            registry_url = 'http://localhost:8000'
        installer = PackageInstaller(project_root=project_root, registry_url=registry_url)
        results = installer.remote_search(args.keyword)
        if not results:
            print(f"未找到匹配 '{args.keyword}' 的包")
        return

    PACKAGES, _, _ = _load_lightpub_index()
    keyword = args.keyword.lower()
    results = []

    for name, info in PACKAGES.items():
        # 搜索包名
        if keyword in name.lower():
            results.append((name, info))
            continue
        # 搜索关键词
        for kw in info.get('keywords', []):
            if keyword in kw.lower():
                results.append((name, info))
                break
        # 搜索描述
        if keyword in info.get('description', '').lower():
            if (name, info) not in results:
                results.append((name, info))

    if not results:
        print(f"未找到匹配 '{args.keyword}' 的包")
        return

    print(f"找到 {len(results)} 个匹配包:")
    print()
    for name, info in sorted(results, key=lambda x: x[0]):
        priority = info.get('priority', '')
        desc = info.get('description', '')
        version = info.get('version', '')
        print(f"  {name:20} v{version:6} [{priority}] {desc}")


def cmd_pkg_info(args):
    """查看包详情"""
    PACKAGES, _, _ = _load_lightpub_index()
    pkg_name = args.package_name
    info = PACKAGES.get(pkg_name)

    if not info:
        # 尝试模糊匹配
        matches = [n for n in PACKAGES if pkg_name.lower() in n.lower()]
        if matches:
            print(f"未找到包 '{pkg_name}'，您是不是要找：")
            for m in matches[:5]:
                print(f"  - {m}")
        else:
            print(f"错误: 未找到包 '{pkg_name}'")
        return

    cat_name = CATEGORY_NAMES.get(info.get('category', ''), info.get('category', '未分类'))
    print(f"=== {pkg_name} ===")
    print(f"  描述:     {info.get('description', '')}")
    print(f"  版本:     {info.get('version', '')}")
    print(f"  分类:     {cat_name}")
    print(f"  优先级:   {info.get('priority', '')}")
    print(f"  函数数:   {info.get('function_count', 0)}")
    print(f"  FFI 数:   {info.get('ffi_count', 0)}")

    stdlib_eq = info.get('stdlib_equivalent')
    if stdlib_eq:
        print(f"  stdlib:   {stdlib_eq}")

    deps = info.get('dependencies', [])
    if deps:
        print(f"  依赖:     {', '.join(deps)}")

    keywords = info.get('keywords', [])
    if keywords:
        print(f"  关键词:   {', '.join(keywords)}")

    note = info.get('note', '')
    if note:
        print(f"  备注:     {note}")

    functions = info.get('functions', [])
    if functions:
        print(f"\n  函数列表 ({len(functions)} 个):")
        for func in functions:
            print(f"    - {func}")

    print(f"\n  导入方式: 导入 {pkg_name} 或 导入 标准{pkg_name}")


def cmd_pkg_list(args):
    """按类别列出包"""
    PACKAGES, CATEGORIES, PRIORITY = _load_lightpub_index()

    if args.category:
        cat_name = CATEGORY_NAMES.get(args.category, args.category)
        pkg_list = CATEGORIES.get(args.category, [])
        if not pkg_list:
            print(f"分类 '{cat_name}' 中没有包")
            return
        print(f"=== {cat_name} ({len(pkg_list)} 个包) ===")
        print()
        for name in sorted(pkg_list):
            info = PACKAGES.get(name, {})
            desc = info.get('description', '')
            priority = info.get('priority', '')
            print(f"  {name:20} [{priority}] {desc}")
    elif args.priority:
        label = {'P0': '核心包', 'P1': '高频包', 'P2': '扩展包'}.get(args.priority, args.priority)
        pkg_list = PRIORITY.get(args.priority, [])
        if not pkg_list:
            print(f"优先级 '{args.priority}' 中没有包")
            return
        print(f"=== {label} ({len(pkg_list)} 个包) ===")
        print()
        for name in sorted(pkg_list):
            info = PACKAGES.get(name, {})
            desc = info.get('description', '')
            print(f"  {name:20} {desc}")
    else:
        print(f"=== lightpub 包列表 ({len(PACKAGES)} 个包) ===")
        print()
        print(f"可用分类: {', '.join(sorted(CATEGORIES.keys()))}")
        print(f"可用优先级: P0 (核心), P1 (高频), P2 (扩展)")
        print()
        print(f"用法: light pkg list --category <分类名>")
        print(f"      light pkg list --priority P0")
        print(f"      light pkg search <关键词>")


def cmd_pkg(args):
    """包管理子命令（统一入口：init/build/run/native/search/info/list/update/publish）"""
    pkg_command = getattr(args, 'pkg_command', None)

    # 搜索/信息/列表命令直接处理
    if pkg_command == 'search':
        cmd_pkg_search(args)
        return
    elif pkg_command == 'info':
        cmd_pkg_info(args)
        return
    elif pkg_command == 'list':
        cmd_pkg_list(args)
        return
    elif pkg_command == 'update':
        cmd_pkg_update(args)
        return
    elif pkg_command == 'publish':
        cmd_pkg_publish(args)
        return

    # 其余命令需要 PackageManager
    from package_manager import PackageManager

    project_root = Path(getattr(args, 'project', None) or '.').resolve()

    if pkg_command == 'init':
        name = args.name
        if name:
            # 在 ./name/ 子目录下初始化
            target_root = project_root / name
            if target_root.exists():
                print(f"错误: 目录已存在: {target_root}", file=sys.stderr)
                sys.exit(1)
            target_root.mkdir(parents=True)
            pkg_name = name
        else:
            target_root = project_root
            pkg_name = project_root.name
        pm = PackageManager(project_root=target_root)
        if pm.init_project(name=pkg_name):
            print(f"✅ 包 '{pkg_name}' 初始化完成")
            print(f"   配置: {target_root / 'package.toml'}")
            if pm.config:
                print(f"   入口: {target_root / pm.config.entry}")
        else:
            print("❌ 初始化失败", file=sys.stderr)
            sys.exit(1)

    elif args.pkg_command == 'build':
        if getattr(args, 'incremental', False):
            # 增量编译
            try:
                from incremental_build import incremental_build_cli
                result = incremental_build_cli(
                    project_dir=project_root,
                    force=getattr(args, 'force', False),
                    verbose=True
                )
                if result == 0:
                    print(f"✅ 增量构建成功")
                else:
                    print(f"❌ 增量构建失败", file=sys.stderr)
                    sys.exit(1)
            except ImportError as e:
                print(f"❌ 增量编译模块不可用: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            pm = PackageManager(project_root=project_root)
            result = pm.build_project()
            if result.get('success'):
                print(f"✅ 构建成功")
                print(f"   入口: {result.get('entry', '')}")
                order = result.get('order', [])
                if order:
                    print(f"   模块拓扑顺序: {' -> '.join(order)}")
            else:
                print("❌ 构建失败:", file=sys.stderr)
                for err in result.get('errors', []):
                    print(f"   - {err}", file=sys.stderr)
                sys.exit(1)

    elif args.pkg_command == 'run':
        pm = PackageManager(project_root=project_root)
        ret = pm.run_project()
        if ret != 0:
            sys.exit(ret)

    elif args.pkg_command == 'native':
        pm = PackageManager(project_root=project_root)
        try:
            output = pm.build_project_native(
                output_path=args.output,
                verbose=args.verbose,
                target=args.target
            )
            print(f"✅ 原生编译成功: {output}")
        except Exception as e:
            print(f"❌ 原生编译失败: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    else:
        print(f"未知子命令: {args.pkg_command}", file=sys.stderr)
        sys.exit(1)


def cmd_test(args):
    """运行光明测试"""
    from test_runner import run_tests, run_single_file

    if args.file:
        if os.path.isdir(args.file):
            return run_tests(
                args.file,
                filter_pattern=args.filter,
                verbose=args.verbose
            )
        return run_single_file(args.file, verbose=args.verbose)
    else:
        return run_tests(
            os.getcwd(),
            filter_pattern=args.filter,
            verbose=args.verbose
        )


def cmd_fmt(args):
    """格式化光明代码"""
    from formatter import run_formatter
    exit_code = run_formatter(args.target, check_only=args.check)
    sys.exit(exit_code)


def cmd_doc(args):
    """生成光明代码文档"""
    from doc_generator import run_doc
    fmt = 'html' if args.html else 'markdown'
    run_doc(args.target, fmt, args.output)


def cmd_profile(args):
    """性能分析"""
    from profiler import run_profile
    run_profile(args.file, memory=args.memory, report=args.report, cprofile=args.cprofile)


def cmd_install(args):
    """安装光明包"""
    from package_installer import run_install
    run_install(args)


def cmd_publish(args):
    """发布光明包"""
    from package_installer import run_publish
    run_publish(args)


def cmd_pkg_update(args):
    """更新光明包"""
    from package_installer import run_update
    run_update(args)


def cmd_pkg_publish(args):
    """发布光明包（pkg 子命令）"""
    from package_installer import run_publish
    run_publish(args)


# ═══════════════════════════════════════════════════════════════════
# py2light 转译命令
# ═══════════════════════════════════════════════════════════════════

def cmd_py2light(args):
    """将 Python 代码转译为光明代码"""
    _AI_DIR = os.path.join(_PROJECT_DIR, 'tools', 'ai_copilot')
    sys.path.insert(0, _AI_DIR)

    from py2light_transpiler import Py2LightTranspiler, TranspileError, FeatureUsageCollector

    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            code = f.read()
    else:
        code = sys.stdin.read()

    if args.stats:
        collector = FeatureUsageCollector()
        tree = compile(code, '<input>', 'exec', ast.PyCF_ONLY_AST)
        collector.visit(tree)
        print("Python 特性统计:")
        for line in collector.get_report_lines():
            print(line)
        return

    transpiler = Py2LightTranspiler()
    try:
        result = transpiler.transpile(code)
        print(result)
    except TranspileError as e:
        print(f"转译错误: {e}", file=sys.stderr)
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
# AI Copilot 子命令
# ═══════════════════════════════════════════════════════════════════

def _ensure_utf8():
    """确保 stdout 使用 UTF-8 编码"""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')


def _cmd_ai(args):
    """AI Copilot 入口"""
    _ensure_utf8()

    # 动态导入，避免影响非 AI 命令的启动速度
    _AI_DIR = os.path.join(_PROJECT_DIR, 'tools', 'ai_copilot')
    sys.path.insert(0, _AI_DIR)

    ai_cmd = getattr(args, 'ai_command', None)
    if not ai_cmd:
        print('用法: light ai <子命令> [选项]')
        print('子命令: prompt, card, snippets, examples, check')
        return

    if ai_cmd == 'prompt':
        from prompt_generator import generate_prompt
        mode = args.mode or 'auto'
        compact = not args.full
        user_input = args.input
        if os.path.isfile(user_input):
            with open(user_input, encoding='utf-8') as f:
                user_input = f.read()
        prompt = generate_prompt(user_input, mode=mode, compact=compact)
        print(prompt)

    elif ai_cmd == 'card':
        from syntax_card import generate_syntax_card
        compact = not args.full
        card = generate_syntax_card(compact=compact, include_verbs=args.verbs)
        print(card)

    elif ai_cmd == 'snippets':
        from snippets import list_snippets, get_snippet
        if args.name:
            snippet = get_snippet(args.name)
            if not snippet:
                print(f"片段不存在: {args.name}")
                return
            print(f"名称：{args.name}")
            print(f"用途：{snippet['desc']}")
            print(f"模板：\n{snippet['code']}")
            if 'example' in snippet:
                print(f"示例：\n{snippet['example']}")
            if 'pitfall' in snippet:
                print(f"⚠暗坑：{snippet['pitfall']}")
        else:
            print(list_snippets())

    elif ai_cmd == 'examples':
        from syntax_card import generate_example_pairs
        print(generate_example_pairs())

    elif ai_cmd == 'check':
        filepath = args.file
        if not os.path.isfile(filepath):
            print(f"文件不存在: {filepath}")
            return

        # ── 后端感知检测 ──
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        _LLVM_KEYWORDS = {
            '类': 'class 定义',
            '继承': '类继承',
            '构造': '构造函数',
            '属性': '类属性',
            '方法': '类方法',
            '静态方法': '静态方法',
            '抽象': '抽象类/方法',
        }
        detected = []
        for kw, desc in _LLVM_KEYWORDS.items():
            # 匹配独立关键字：前面不是标识符字符，后面是空格/冒号/换行/括号
            if re.search(r'(?<![a-zA-Z0-9_\u4e00-\u9fff])' + re.escape(kw) + r'(?![a-zA-Z0-9_\u4e00-\u9fff])', source):
                detected.append((kw, desc))

        if detected:
            print(f"[0/2] ⚠ 后端感知检测")
            for kw, desc in detected:
                print(f"  · 检测到「{kw}」({desc})")
            print(f"  → 类系统在 SRC 后端下运行无输出，建议使用 LLVM 后端：")
            print(f"     light compile {filepath} --backend llvm-typed")
            print()

        # 语法检查
        print(f"[1/2] 语法检查: {filepath}")
        result = subprocess.run(
            [sys.executable, '-X', 'utf8', '-m', 'cli.light', 'check', filepath],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            cwd=_PROJECT_DIR,
        )
        if result.returncode != 0:
            print(f"  ✗ 语法检查失败:")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
        else:
            print(f"  ✓ 语法检查通过")

        if args.run:
            print(f"[2/2] 运行测试: {filepath}")
            try:
                result = subprocess.run(
                    [sys.executable, '-X', 'utf8', '-m', 'cli.light', 'run', filepath],
                    capture_output=True, text=True, encoding='utf-8', errors='replace',
                    cwd=_PROJECT_DIR,
                    timeout=args.timeout,
                )
                if result.returncode != 0:
                    print(f"  ✗ 运行失败:")
                    if result.stdout:
                        print(result.stdout)
                    if result.stderr:
                        print(result.stderr)
                else:
                    print(f"  ✓ 运行成功")
                    if result.stdout and result.stdout.strip():
                        print(f"  输出:")
                        for line in result.stdout.strip().split('\n'):
                            print(f"    {line}")
            except subprocess.TimeoutExpired:
                print(f"  ✗ 运行超时（{args.timeout}秒）")
        else:
            print("[2/2] 跳过运行检查（使用 --run 启用）")

    elif ai_cmd == 'generate':
        from pipeline import generate_pipeline
        prompt = generate_pipeline(
            requirement=args.requirement,
            model_size=args.model_size,
            mode=args.mode,
        )
        print(prompt)

    elif ai_cmd == 'fix':
        from pipeline import fix_pipeline
        if not os.path.isfile(args.file):
            print(f"文件不存在: {args.file}")
            return
        prompt = fix_pipeline(
            filepath=args.file,
            error=args.error,
            model_size=args.model_size,
        )
        print(prompt)

    elif ai_cmd == 'translate':
        from translator import PythonToLightTranslator, LightToPythonTranslator

        if args.to_light:
            src_path, translator, err_label = args.to_light, PythonToLightTranslator(), 'Python 语法错误'
        else:
            src_path, translator, err_label = args.to_python, LightToPythonTranslator(), '光明语法错误'

        if not os.path.isfile(src_path):
            print(f"文件不存在: {src_path}")
            return
        try:
            result = translator.translate_file(src_path)
        except (SyntaxError, ValueError) as e:
            print(f"{err_label}: {e}", file=sys.stderr)
            sys.exit(1)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"翻译完成，输出到: {args.output}")
        else:
            print(result)



# ═══════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        prog='light',
        description='光明（Light）编程语言编译器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  light run hello.light                 解释执行
  light compile hello.light             编译为 Python 文件
  light compile hello.light --src       用旧版后端编译
  light ast hello.light                 显示 AST
  light tokens hello.light              显示 Token 流
  light --version                      显示版本
        """
    )

    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--dev-version', action='store_true', help='显示开发分支版本信息')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # ── run ──
    run_p = subparsers.add_parser('run', help='解释执行光明源代码')
    run_p.add_argument('file', help='源文件路径')
    run_p.add_argument('--backend', choices=['antlr', 'src', 'native', 'llvm-typed'], default='src',
                       help='使用的后端（默认: src，无需额外依赖；antlr 需安装 antlr4-python3-runtime；'
                            'native/llvm-typed 走原生腿：编译到临时目录再执行产物，需安装 clang）。'
                            'native 是 llvm-typed 的一等别名（B9 S1 2.2）；--backend llvm（string 死腿，'
                            '引用不存在的 runtime.c）已在 B9 移除。')
    run_p.add_argument('--optimize', choices=['O0', 'O1', 'O2', 'O3', 'Os', 'Oz'], default='O2',
                       help='原生后端（native/llvm-typed）的优化级别（默认: O2；Os/Oz 为体积优化；'
                            '解释后端忽略此项）')

    run_p.add_argument('--watch', '-w', action='store_true',
                       help='监视文件变化，自动重新运行')

    # ── harness（第五轮 D5：deepseek-harness MVP 的 CLI 包装）──
    # 转发到 examples/harness/评测驱动.light；参数映射为 HARNESS_* 环境变量。
    harness_p = subparsers.add_parser('harness', help='deepseek-harness MVP（examples/harness/）')
    harness_sub = harness_p.add_subparsers(dest='harness_cmd', help='harness 子命令')
    harness_run_p = harness_sub.add_parser('run', help='端到端评测：读 JSONL → 并发跑 LLM → 打分 → 出报告')
    harness_run_p.add_argument('--channel', choices=['mock', 'real'], default=None,
                               help='LLM 通道：mock=确定性桩零发网（默认）/ real=真实 DeepSeek（需 DEEPSEEK_API_KEY）')

    harness_run_p.add_argument('--eval-set', default=None, help='评测集 JSONL 路径（默认 examples/harness/评测集.jsonl）')
    harness_run_p.add_argument('--report', default=None, help='报告输出前缀（默认 examples/harness/评测报告）')
    harness_run_p.add_argument('--concurrency', default=None, help='并发上限（默认 2）')
    harness_run_p.add_argument('--rate', default=None, help='每秒请求上限（默认 10）')
    harness_run_p.add_argument('--retries', default=None, help='重试次数（默认 3）')
    harness_run_p.add_argument('--delay', default=None, help='mock 通道每请求延迟秒（默认 0.2）')
    # 第七轮 §4.2：语义由 C7/D7 定义，A7 只负责转发成 HARNESS_* 环境变量。
    harness_run_p.add_argument('--mode', choices=['single', 'agent'], default=None,
                               help='评测模式：single=单轮（默认，保持现有行为）/ agent=多轮 agent（C7）')
    harness_run_p.add_argument('--tools', choices=['off', 'on'], default=None,
                               help='是否给模型下发工具（默认 off）（C7）')
    harness_run_p.add_argument('--price-in', default=None,
                               help='输入词元单价（默认空 = 不算成本）（D7）')
    harness_run_p.add_argument('--price-out', default=None,
                               help='输出词元单价（默认空 = 不算成本）（D7）')

    harness_run_p.add_argument('--backend', choices=['antlr', 'src'], default='src',
                               help='使用的后端（默认: src）')
    harness_run_p.add_argument('--verbose', action='store_true', help='详细输出')

    # ── compile ──
    comp_p = subparsers.add_parser('compile', help='编译为 Python 文件')
    comp_p.add_argument('file', help='源文件路径')
    comp_p.add_argument('-o', '--output', help='输出文件路径（默认: 同名 .py）')
    comp_p.add_argument('--backend', choices=['antlr', 'src', 'native', 'llvm-typed'], default='src',
                        help='使用的后端（默认: src；antlr 需安装 antlr4-python3-runtime；'
                             'native/llvm-typed 走原生腿，需安装 clang）。native 是 llvm-typed 的一等别名'
                             '（B9 S1 2.2）；--backend llvm（string 死腿，引用不存在的 runtime.c）已在 B9 移除。')
    comp_p.add_argument('--optimize', choices=['O0', 'O1', 'O2', 'O3', 'Os', 'Oz'], default='O2',
                        help='原生后端（native/llvm-typed）优化级别（默认: O2；Os/Oz 为体积优化）')
    comp_p.add_argument('--debug', action='store_true',
                        help='生成 DWARF 调试信息')

    # ── ast ──
    ast_p = subparsers.add_parser('ast', help='显示 AST')
    ast_p.add_argument('file', help='源文件路径')
    ast_p.add_argument('--backend', choices=['antlr', 'src'], default='src',
                       help='使用的后端（默认: src）')

    # ── tokens ──
    tok_p = subparsers.add_parser('tokens', help='显示 Token 流')
    tok_p.add_argument('file', help='源文件路径')

    # ── check ──
    check_p = subparsers.add_parser('check', help='语法检查（默认启用类型检查）')
    check_p.add_argument('file', help='源文件路径')
    check_p.add_argument('--backend', choices=['antlr', 'src'], default='src',
                         help='使用的后端（默认: src）')
    check_p.add_argument('--type-check', choices=['签名', '变量', '表达式', 'signature', 'variable', 'expression'],
                         default='表达式', help='类型检查级别（默认: 表达式）')
    check_p.add_argument('--no-type-check', action='store_true',
                         help='跳过类型检查')

    # ── type-check ──
    tc_p = subparsers.add_parser('type-check', help='独立类型检查')
    tc_p.add_argument('file', help='源文件路径')
    tc_p.add_argument('--level', choices=['签名', '变量', '表达式', 'signature', 'variable', 'expression'],
                      default='表达式', help='类型检查级别（默认: 表达式）')

    # ── init ──
    init_p = subparsers.add_parser('init', help='初始化光明项目')
    init_p.add_argument('name', help='项目名称')
    init_p.add_argument('--template', '-t', choices=['default', 'cli', 'lib', 'web'],
                        default='default', help='项目模板（默认: default）')

    # ── pkg ──
    pkg_p = subparsers.add_parser('pkg', help='包管理（init/build/run/native/search/info/list/update/publish）')
    pkg_p.add_argument('--project', '-p', default='.', help='项目根目录（默认: 当前目录）')
    pkg_sub = pkg_p.add_subparsers(dest='pkg_command', help='包管理子命令')

    pkg_init = pkg_sub.add_parser('init', help='初始化新包（创建 package.toml 与 主.light）')
    pkg_init.add_argument('name', nargs='?', default=None, help='包名（默认: 目录名）')

    pkg_build = pkg_sub.add_parser('build', help='编译整个项目')
    pkg_build.add_argument('--incremental', action='store_true', help='使用增量编译（仅编译变更文件）')
    pkg_build.add_argument('--force', '-f', action='store_true', help='强制全量编译（忽略增量缓存）')

    pkg_sub.add_parser('run', help='运行项目入口')

    pkg_native = pkg_sub.add_parser('native', help='使用 LLVM 后端编译为原生可执行文件')
    pkg_native.add_argument('-o', '--output', default=None, help='输出文件路径')
    pkg_native.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    pkg_native.add_argument('--target', default=None,
                            choices=['auto', 'macos', 'linux', 'windows'],
                            help='目标平台（auto/macos/linux/windows，默认 auto 自动检测）')

    # ── pkg search ──
    pkg_search = pkg_sub.add_parser('search', help='搜索 lightpub 包')
    pkg_search.add_argument('keyword', help='搜索关键词（包名/描述/关键词）')
    pkg_search.add_argument('--remote', '-r', action='store_true', help='从远程注册中心搜索')
    pkg_search.add_argument('--registry-url', default=None, help='远程注册中心 URL（默认: http://localhost:8000）')

    # ── pkg info ──
    pkg_info = pkg_sub.add_parser('info', help='查看 lightpub 包详情')
    pkg_info.add_argument('package_name', help='包名')

    # ── pkg list ──
    pkg_list = pkg_sub.add_parser('list', help='列出 lightpub 包')
    pkg_list.add_argument('--category', '-c', default=None, help='按分类筛选（dev/net/database/security/language 等）')
    pkg_list.add_argument('--priority', '-p', default=None, choices=['P0', 'P1', 'P2'], help='按优先级筛选')

    # ── pkg update ──
    pkg_update = pkg_sub.add_parser('update', help='更新包到最新版本')
    pkg_update.add_argument('package', nargs='?', default=None, help='包名（默认空）')
    pkg_update.add_argument('--all', '-a', action='store_true', help='更新所有已安装包')
    pkg_update.add_argument('--check', '-c', action='store_true', help='检查可用更新，不安装')

    # ── pkg publish ──
    pkg_publish = pkg_sub.add_parser('publish', help='发布包到本地索引')
    pkg_publish.add_argument('--path', default=None, help='包项目路径（默认: 当前目录）')

    # ── ai ──
    ai_p = subparsers.add_parser('ai', help='AI Copilot 辅助工具（算力不足场景下的光明代码生成）')
    ai_sub = ai_p.add_subparsers(dest='ai_command', help='AI 子命令')

    ai_prompt = ai_sub.add_parser('prompt', help='生成让 AI 写光明代码的 prompt')
    ai_prompt.add_argument('input', help='需求描述或 Python 代码（也支持文件路径）')
    ai_prompt.add_argument('--mode', choices=['auto', 'translate', 'create', 'paragraph'],
                           default='auto', help='生成模式（默认 auto 自动检测）')
    ai_prompt.add_argument('--full', action='store_true', help='使用完整语法卡（默认精简卡）')

    ai_card = ai_sub.add_parser('card', help='输出光明语法速查卡')
    ai_card.add_argument('--full', action='store_true', help='完整版（默认精简版）')
    ai_card.add_argument('--verbs', action='store_true', help='包含动词参数参照表')

    ai_snippets = ai_sub.add_parser('snippets', help='列出代码片段库')
    ai_snippets.add_argument('name', nargs='?', help='查看指定片段详情')

    ai_sub.add_parser('examples', help='Python→光明对照示例')

    ai_check = ai_sub.add_parser('check', help='校验光明代码（语法+运行+后端感知）')
    ai_check.add_argument('file', help='光明代码文件路径')
    ai_check.add_argument('--run', action='store_true', help='同时运行测试')
    ai_check.add_argument('--timeout', type=int, default=10, help='运行超时秒数（默认10）')

    ai_gen = ai_sub.add_parser('generate', help='★ 一键生成：需求→完整prompt（推荐）')
    ai_gen.add_argument('requirement', help='代码需求描述，如"写一个冒泡排序"')
    ai_gen.add_argument('--model-size', choices=['small', 'medium', 'large'],
                        default='medium', help='目标模型大小（默认medium）：small≤7B / medium7-14B / large≥14B')
    ai_gen.add_argument('--mode', choices=['auto', 'translate', 'create', 'paragraph'],
                        default='auto', help='生成模式（默认auto）')

    ai_fix = ai_sub.add_parser('fix', help='★ 一键修复：出错代码→修复prompt')
    ai_fix.add_argument('file', help='出错的光明代码文件路径')
    ai_fix.add_argument('error', help='错误信息（可用引号包裹）')
    ai_fix.add_argument('--model-size', choices=['small', 'medium', 'large'],
                        default='medium', help='目标模型大小（默认medium）')

    ai_translate = ai_sub.add_parser(
        'translate',
        help='Python ↔ 光明 双向翻译（文件级；交互模式见 tools/ai_copilot/cli.py translate --interactive）')
    ai_tr_group = ai_translate.add_mutually_exclusive_group(required=True)
    ai_tr_group.add_argument('--to-light', metavar='FILE', help='将 Python 文件翻译为光明')
    ai_tr_group.add_argument('--to-python', metavar='FILE', help='将光明文件翻译为 Python')
    ai_translate.add_argument('-o', '--output', metavar='FILE',
                              help='输出文件路径（默认打印到标准输出）')


    # ── test ──
    test_p = subparsers.add_parser('test', help='运行光明测试')
    test_p.add_argument('file', nargs='?', help='测试文件路径（默认自动发现）')
    test_p.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    test_p.add_argument('--filter', help='按文件名过滤测试')

    # ── fmt ──
    fmt_p = subparsers.add_parser('fmt', help='格式化光明代码')
    fmt_p.add_argument('target', help='文件或目录路径')
    fmt_p.add_argument('--check', action='store_true', help='仅检查格式，不修改文件')

    # ── doc ──
    doc_p = subparsers.add_parser('doc', help='生成光明代码文档')
    doc_p.add_argument('target', help='文件或目录路径')
    doc_p.add_argument('--html', action='store_true', help='生成 HTML 格式文档')
    doc_p.add_argument('-o', '--output', help='输出文件或目录路径')

    # ── profile ──
    profile_p = subparsers.add_parser('profile', help='性能分析')
    profile_p.add_argument('file', help='源文件路径')
    profile_p.add_argument('--memory', '-m', action='store_true', help='包含内存分析')
    profile_p.add_argument('--report', '-r', action='store_true', help='生成详细报告')
    profile_p.add_argument('--cprofile', action='store_true', help='使用 cProfile 详细分析')

    # ── install ──
    install_p = subparsers.add_parser('install', help='安装光明包')
    install_p.add_argument('package', nargs='?', default=None, help='包名')
    install_p.add_argument('--git', default=None, help='从 Git 仓库安装')
    install_p.add_argument('--path', default=None, help='从本地路径安装')
    install_p.add_argument('--search', default=None, help='搜索包')
    install_p.add_argument('--list', action='store_true', help='列出已安装的包')
    install_p.add_argument('--registry', action='store_true', help='列出包库中所有包')
    install_p.add_argument('--uninstall', default=None, help='卸载包')
    install_p.add_argument('--update-registry', action='store_true', help='从远程更新本地包库缓存')
    install_p.add_argument('--registry-url', default=None, help='远程包库 URL')
    install_p.add_argument('--with-deps', action='store_true', help='自动安装依赖')
    install_p.add_argument('-p', '--project', default='.', help='项目目录')

    # ── publish ──
    publish_p = subparsers.add_parser('publish', help='发布包到本地索引')
    publish_p.add_argument('--path', default=None, help='包项目路径（默认: 当前目录）')
    publish_p.add_argument('-p', '--project', default='.', help='项目目录')

    # ── repl ──
    repl_p = subparsers.add_parser('repl', help='启动光明交互式解释器 (REPL)')
    repl_p.add_argument('--enhanced', action='store_true', help='使用增强模式（prompt_toolkit，需安装）')

    # ── tutorial ──
    tutorial_p = subparsers.add_parser('tutorial', help='30 分钟入门光明交互式教程')
    tutorial_p.add_argument('--step', action='store_true', help='逐步运行（每节暂停）')
    tutorial_p.add_argument('--repl', action='store_true', help='交互式练习模式')

    # ── py2light ──
    py2light_p = subparsers.add_parser('py2light', help='将 Python 代码转译为光明代码')
    py2light_p.add_argument('file', nargs='?', help='Python 源文件路径（默认从 stdin 读取）')
    py2light_p.add_argument('--stats', action='store_true', help='显示 Python 特性统计信息')

    # ── feedback ──
    setup_feedback_subparser(subparsers)

    args = parser.parse_args()

    # 处理 --dev-version 标志
    if getattr(args, 'dev_version', False):
        try:
            from src.version import get_dev_version_string
            print(get_dev_version_string())
        except ImportError:
            print(VERSION)
        sys.exit(0)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'run':
        cmd_run(args)
    elif args.command == 'compile':
        cmd_compile(args)
    elif args.command == 'ast':
        cmd_ast(args)
    elif args.command == 'tokens':
        cmd_tokens(args)
    elif args.command == 'check':
        cmd_check(args)
    elif args.command == 'type-check':
        cmd_type_check(args)
    elif args.command == 'init':
        cmd_init(args)
    elif args.command == 'ai':
        _cmd_ai(args)
    elif args.command == 'pkg':
        if not getattr(args, 'pkg_command', None):
            parser.parse_args(['pkg', '--help'])
        else:
            cmd_pkg(args)
    elif args.command == 'test':
        exit_code = cmd_test(args)
        sys.exit(exit_code)
    elif args.command == 'fmt':
        exit_code = cmd_fmt(args)
        sys.exit(exit_code)
    elif args.command == 'doc':
        cmd_doc(args)
        sys.exit(0)
    elif args.command == 'profile':
        cmd_profile(args)
        sys.exit(0)
    elif args.command == 'install':
        cmd_install(args)
        sys.exit(0)
    elif args.command == 'publish':
        cmd_publish(args)
        sys.exit(0)
    elif args.command == 'repl':
        from src.repl.core import LightREPL
        repl = LightREPL(enhanced=args.enhanced)
        repl.run()
    elif args.command == 'tutorial':
        from cli.tutorial import main as tutorial_main
        sys.argv = ['light tutorial']
        if args.step:
            sys.argv.append('--step')
        if args.repl:
            sys.argv.append('--repl')
        tutorial_main()

    elif args.command == 'py2light':
        cmd_py2light(args)

    elif args.command == 'feedback':
        exit_code = run_feedback_cli(args)
        sys.exit(exit_code)

    elif args.command == 'harness':
        cmd_harness(args)


if __name__ == '__main__':
    main()