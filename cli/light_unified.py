#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明（Light）编程语言 - 统一命令行工具 v2.0

用法：
  light <源文件.light> [选项]
  light run <源文件.light>
  light compile <源文件.light> [-o <输出>]
  light repl
  light --help

示例：
  light hello.light                    # 编译并运行（使用ANTLR后端）
  light hello.light --backend src      # 使用src手写解析器
  light run hello.light                # 解释执行
  light compile hello.light -o hello.py
  light repl                          # 启动REPL
"""
import sys
import os
import argparse
from pathlib import Path
from typing import Optional, List

# 版本信息
try:
    from src.version import DEV_BRANCH, VERSION as LANG_VERSION, is_dev_branch, get_dev_version_string
    DEV_VERSION_STR = f'光明 v{LANG_VERSION}dev (开发分支)'
    STABLE_VERSION_STR = f'光明 v{LANG_VERSION}'
    VERSION_STR = DEV_VERSION_STR if is_dev_branch() else STABLE_VERSION_STR
except ImportError:
    VERSION_STR = '光明 v7.0.0'

# 添加路径 - 先尝试本地路径（开发模式），再尝试已安装路径
_local_src = str(Path(__file__).parent.parent / 'src')
_local_antlr = str(Path(__file__).parent.parent / 'antlrparser')

if os.path.isdir(_local_src):
    sys.path.insert(0, _local_src)
if os.path.isdir(_local_antlr):
    sys.path.insert(0, _local_antlr)

# 已安装版本（pip install），仅在本地 src 不可用时回退
if not os.path.isdir(_local_src):
    try:
        import src as _src_pkg
        _installed_src = str(Path(_src_pkg.__file__).parent)
        if _installed_src not in sys.path and os.path.isdir(_installed_src):
            sys.path.insert(0, _installed_src)
    except ImportError:
        pass


def _resolve_compile_time_stdlib() -> Optional[str]:
    """在编译期解析 Light 标准库目录的绝对路径（修复产物找不到标准库/钩子的根因）。

    产物运行环境通常与 Light 安装目录不相邻，仅靠相对探测（<产物>/stdlib、
    <cwd>/stdlib 等）会落空，于是 `import _light_import_hook` 被静默吞掉、
    `from 中文模块/标准库 import ...` 全部 ModuleNotFoundError。

    这里在「编译器自身可导入」的进程里，从编译器包位置反推 stdlib，把绝对
    路径注入到产物引导段，使产物自带可靠锚点，脱离本仓库也能找到标准库。
    兼容开发布局（.../src 与 .../stdlib 同父）与 pip 安装布局。
    """
    try:
        import light_parser_v3
    except Exception:
        return None
    try:
        pkg = os.path.dirname(os.path.abspath(light_parser_v3.__file__))
    except Exception:
        return None
    candidates = [
        os.path.join(pkg, 'stdlib'),
        os.path.join(os.path.dirname(pkg), 'stdlib'),
        os.path.join(os.path.dirname(os.path.dirname(pkg)), 'stdlib'),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return os.path.normpath(c)
    return None


class LightUnifiedCLI:
    """光明统一CLI"""
    
    def __init__(self):
        self.antlr_available = self._check_antlr()
        self.src_available = self._check_src()
    
    def _check_antlr(self) -> bool:
        """检查ANTLR后端是否可用"""
        try:
            from antlr4 import InputStream, CommonTokenStream
            from LightLangLexer import LightLangLexer
            from LightLangParser import LightLangParser
            from light_visitor import LightLangASTBuilder
            from code_generator_unified import UnifiedCodeGenerator
            return True
        except ImportError:
            return False
    
    def _check_src(self) -> bool:
        """检查src手写解析器是否可用"""
        try:
            from lexer import Lexer
            from light_parser_v3 import LightParser
            from code_generator import PythonCodeGenerator
            return True
        except ImportError:
            return False
    
    def compile_with_antlr(self, source: str, output_file: Optional[str] = None,
                           run: bool = False, source_file: Optional[str] = None) -> int:
        """使用ANTLR后端编译"""
        from light_visitor import LightParser
        from code_generator_unified import UnifiedCodeGenerator
        
        # 使用 LightParser 进行完整的预处理（_auto_close_blocks、_preprocess_async 等）
        light_parser = LightParser()
        module = light_parser.parse(source)
        
        if light_parser.errors:
            for error in light_parser.errors:
                print(error, file=sys.stderr)
            return 1
        
        if module is None:
            print("[错误] 解析失败", file=sys.stderr)
            return 1
        
        # 代码生成（注入编译期解析到的 stdlib 绝对路径，修复产物找不到标准库/钩子）
        generator = UnifiedCodeGenerator(stdlib_dir=_resolve_compile_time_stdlib())
        python_code = generator.generate(module)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(python_code)
            print(f"[成功] 已生成: {output_file}")

            # 让产物自包含：把依赖的用户模块一并编译到产物同目录（与 src 后端的
            # _emit_user_modules 对齐）。否则 `from 学生模块 import …` 在产物换进程
            # 裸跑、且 .light 源不在产物同目录时必炸 ModuleNotFoundError。
            if source_file:
                out_dir = os.path.dirname(os.path.abspath(output_file))
                src_dir = os.path.dirname(os.path.abspath(source_file))
                emitted = self._emit_user_modules(source, src_dir, out_dir)
                if emitted:
                    print("[成功] 已随产物生成依赖模块: "
                          + ', '.join(f'{m}.py' for m in emitted))
                emitted_rt = self._emit_runtime_modules(source, out_dir)
                if emitted_rt:
                    print("[成功] 已随产物生成 L3 运行时模块: "
                          + ', '.join(f'{m}.py' for m in emitted_rt))
        
        if run:
            # 执行代码
            try:
                # 创建执行环境，包含必要的内置变量
                exec_globals = {
                    '__name__': '__main__',
                    '__file__': output_file or '<light_script>',
                    '__builtins__': __builtins__,
                }
                exec(python_code, exec_globals)
            except Exception as e:
                print(f"[运行错误] {e}", file=sys.stderr)
                return 1
        
        return 0
    
    # 已知的标准库 / Python 模块名（不应被当成用户模块预编译或落盘）
    KNOWN_STDLIB = {
        '文件系统', 'JSON', 'sys', '字符串工具', '数学', '时间', '日期时间',
        'csv', 'json', 'os', 're', 'random', 'math', 'datetime', 'time',
        'pathlib', 'typing', 'collections', 'itertools', 'functools',
        'subprocess', 'shutil', 'glob', 'tempfile', 'io', 'builtins',
        '复制', 'os路径',
    }

    @classmethod
    def _find_user_module_path(cls, mod_name: str, source_dir: str):
        """在源文件目录、再退一级目录里找 <模块名>.light，找不到返回 None

        run 路径（_register_user_modules）与 compile 路径（_emit_user_modules）
        必须共用这一套查找判据。两边各写一份是本仓库单 D 的成因：run 找得到、
        compile 找不到，于是 run 绿、产物红。
        """
        mod_path = os.path.join(source_dir, f"{mod_name}.light")
        if os.path.exists(mod_path):
            return mod_path
        alt_path = os.path.join(os.path.dirname(source_dir), f"{mod_name}.light")
        if os.path.exists(alt_path):
            return alt_path
        return None

    @classmethod
    def _iter_user_module_deps(cls, source: str, source_dir: str, seen: set):
        """解析 source，逐个 yield (模块名, 模块文件路径, 模块源码)

        只认用户模块：跳过 KNOWN_STDLIB、跳过 language 为 python/c 的外语导入、
        跳过磁盘上找不到 .light 的（当成标准库或第三方，交给下游报错）。
        yield 之前就把模块名放进 seen，用于防循环依赖。
        """
        from light_parser_v3 import LightParser, ImportStmt

        try:
            module = LightParser().parse(source)
        except Exception:
            return
        if not module:
            return

        for stmt in getattr(module, 'statements', []):
            if not isinstance(stmt, ImportStmt):
                continue
            mod_name = stmt.module_name
            if mod_name in seen or mod_name in cls.KNOWN_STDLIB:
                continue
            if getattr(stmt, 'language', None) in ('python', 'c'):
                continue
            mod_path = cls._find_user_module_path(mod_name, source_dir)
            if mod_path is None:
                continue
            try:
                with open(mod_path, 'r', encoding='utf-8') as f:
                    mod_source = f.read()
            except OSError:
                continue
            seen.add(mod_name)
            yield mod_name, mod_path, mod_source

    def _emit_user_modules(self, source: str, source_dir: str,
                           output_dir: str, emitted: set = None) -> list:
        """把 source 依赖的用户模块一并编译落盘到 output_dir，使产物自包含

        compile 出来的产物里 `导 学生模块 出 …` 被译成
        `from 学生模块 import …`；Python 运行脚本时会把脚本所在目录放到
        sys.path[0]，所以只要把 学生模块.py 落在产物**同目录**，这句 import
        就能解析。不这样做的话产物只在「恰好 cwd 有依赖」时能跑——
        e2e 把产物写到临时目录，于是必炸 ModuleNotFoundError。

        递归处理依赖的依赖。返回已落盘的模块名列表。
        """
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator

        if emitted is None:
            emitted = set()
        written = []

        for mod_name, mod_path, mod_source in self._iter_user_module_deps(
                source, source_dir, emitted):
            # 先递归，保证依赖的依赖也落盘
            written.extend(self._emit_user_modules(
                mod_source, os.path.dirname(mod_path), output_dir, emitted))
            try:
                mod_module = LightParser().parse(mod_source, filename=mod_path)
                if not mod_module:
                    continue
                mod_py_code = PythonCodeGenerator().generate(mod_module)
            except Exception as e:
                # 依赖模块自己编不过：明确告警，不静默产出半残产物
                print(f"[警告] 依赖模块编译失败，产物将不自包含: {mod_path}: {e}",
                      file=sys.stderr)
                continue
            out_path = os.path.join(output_dir, f"{mod_name}.py")
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(mod_py_code)
            written.append(mod_name)

        return written

    @classmethod
    def _iter_runtime_module_deps(cls, source: str):
        """yield 出 source 里被 import 到的「编译器自带 L3 运行时模块」名

        判据是 src/compiler.py 的 `L3_MODULES` 白名单：**不在白名单里的名字一律
        不碰**。不能改成「凡 import 不到的就复制」——那等于允许把任意路径的文件
        往产物目录搬。白名单里新增 l3_* 模块时，本机制自动覆盖到，无需再改这里。

        只匹配真正的 import 语句（行首可有缩进），所以注释或字符串里提到模块名
        不会误命中。
        """
        import re

        try:
            from compiler import L3_MODULES
        except ImportError:
            return

        pattern = re.compile(
            r'(?:^|\n)[ \t]*(?:from[ \t]+([A-Za-z_]\w*)[ \t]+import\b'
            r'|import[ \t]+([A-Za-z_]\w*))')
        seen = set()
        for m in pattern.finditer(source):
            name = m.group(1) or m.group(2)
            if name in L3_MODULES and name not in seen:
                seen.add(name)
                yield name

    def _emit_runtime_modules(self, source: str, output_dir: str) -> list:
        """把 `引 Python:` 块里 import 的编译器自带 L3 运行时模块复制到产物同目录

        `引 Python:` 块的代码被**原样**塞进产物的 `_LIGHT_L4_SRC` 字符串里 exec
        （见 src/code_generator.py 的 `_generate_embed_block` python 分支），所以
        示例里那句 `from l3_echarts import L3ECharts` 在产物里照样要解析。而
        `l3_echarts.py` 物理上住在编译器的 `src/` 目录，产物引导段只把 `stdlib/`
        与项目根铺进 sys.path（src/code_generator.py:611-639），**从来没有 src/
        那一档**；`src/` 是包（有 `__init__.py`），包内模块也不会作为顶层名暴露。

        `duan run` 那条腿之所以是绿的，纯粹因为 cli/light_unified.py:36-42 为编译器
        自己 insert 了 `src/`，`l3_*` 搭了便车；compile 出的产物换进程裸跑就没人铺了。

        修法与 `_emit_user_modules` 同构（单 D 先例）：Python 跑脚本时 sys.path[0]
        是脚本所在目录，把模块 `.py` 复制到产物**同目录**即可解析——产物也就真的
        能脱离本仓库跑，而不是只在「恰好站在仓库里」时能跑。

        用 importlib 定位模块文件而非拼 `<repo>/src/`，这样开发模式与
        `pip install` 后的安装模式都成立。返回已落盘的模块名列表。
        """
        import importlib
        import shutil

        written = []
        for mod_name in self._iter_runtime_module_deps(source):
            try:
                mod = importlib.import_module(mod_name)
                mod_file = getattr(mod, '__file__', None)
            except Exception as e:
                print(f"[警告] L3 运行时模块加载失败，产物将不自包含: {mod_name}: {e}",
                      file=sys.stderr)
                continue
            if not mod_file or not os.path.isfile(mod_file):
                print(f"[警告] L3 运行时模块无源码文件，产物将不自包含: {mod_name}",
                      file=sys.stderr)
                continue
            out_path = os.path.join(output_dir, f"{mod_name}.py")
            if os.path.abspath(out_path) == os.path.abspath(mod_file):
                # 产物就写在模块自己旁边（例如 -o 指到 src/），无需复制
                written.append(mod_name)
                continue
            try:
                shutil.copyfile(mod_file, out_path)
            except OSError as e:
                print(f"[警告] L3 运行时模块复制失败，产物将不自包含: {mod_name}: {e}",
                      file=sys.stderr)
                continue
            written.append(mod_name)

        return written

    def _register_user_modules(self, source: str, source_dir: str,
                                registered: set = None,
                                exported_names: set = None) -> None:
        """预编译用户自定义模块并注册到 sys.modules

        光明的导入语句（如 导入《工具》为 工具）会被翻译为 Python 的
        import 工具 as 工具，但 Python 无法直接找到中文模块名。
        此方法在运行前预编译用户模块的 .light 文件，创建 Python 模块对象
        并注册到 sys.modules 中，使 import 语句能正常解析。

        Args:
            source: 源代码（用于提取导入语句）
            source_dir: 源文件所在目录（用于查找模块文件）
            registered: 已注册的模块名集合（防止循环依赖）
            exported_names: 收集到的所有模块导出函数名集合（用于跨模块标识符识别）
        """
        import types
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator

        if registered is None:
            registered = set()
        # 防止重复收集导出名
        _already_collected = set()

        # 依赖发现走 _iter_user_module_deps（与 compile 路径的
        # _emit_user_modules 共用同一套判据，见该方法注释）
        for mod_name, mod_path, mod_source in self._iter_user_module_deps(
                source, source_dir, registered):
            # 递归注册模块自身的导入
            self._register_user_modules(mod_source, os.path.dirname(mod_path), registered, exported_names)

            # 编译模块并注册为 Python 模块
            try:
                mod_parser = LightParser()
                mod_module = mod_parser.parse(mod_source, filename=mod_path)
                if mod_module:
                    mod_generator = PythonCodeGenerator()
                    mod_py_code = mod_generator.generate(mod_module)
                    mod_ns = {'__builtins__': __builtins__}
                    exec(mod_py_code, mod_ns)
                    mod_obj = types.ModuleType(mod_name)
                    for k, v in mod_ns.items():
                        if not k.startswith('_'):
                            setattr(mod_obj, k, v)
                    sys.modules[mod_name] = mod_obj
                    # 收集模块的导出函数名（用于跨模块标识符识别）
                    if exported_names is not None and mod_name not in _already_collected:
                        _already_collected.add(mod_name)
                        for name in dir(mod_obj):
                            if not name.startswith('_') and callable(getattr(mod_obj, name, None)):
                                exported_names.add(name)
            except Exception:
                # 注册失败时不中断，让后续的 import 抛出更清晰的错误
                pass


    def compile_with_src(self, source: str, output_file: Optional[str] = None,
                         run: bool = False, target: str = 'python',
                         source_file: str = None) -> int:
        """使用src手写解析器编译
        
        Args:
            source: 源代码
            output_file: 输出文件路径
            run: 是否执行
            target: 目标格式 ('python' 或 'llvm')
            source_file: 源文件路径（用于解析用户模块导入）
        """
        from compiler import LightCompiler
        
        compiler = LightCompiler()
        
        if target == 'llvm':
            # LLVM IR 生成：只做解析和适配，跳过类型检查
            try:
                tokens = compiler.tokenize(source)
                raw_ast = compiler.parse_raw(source)
                module = compiler.adapt(raw_ast)
                
                if not module:
                    print("[语法错误] 解析失败", file=sys.stderr)
                    return 1
                
                llvm_ir = compiler.generate_llvm_ir(module)
                
                if output_file:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(llvm_ir)
                    print(f"[成功] 已生成 LLVM IR: {output_file}")
                else:
                    print(llvm_ir)
                
                return 0
            except Exception as e:
                print(f"[LLVM IR 生成错误] {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                return 1
        else:
            # Python 代码生成：直接使用 v3 解析器 + 代码生成器
            # （注意：不走 LightCompiler.compile 的 adapt 步骤 —— adapt 会把
            #   Paragraph/段落定义丢弃，导致运行时 NameError 或生成器报
            #   “未知语句类型 VariableDeclaration”，与 cli/light.py 的
            #   _compile_src 保持一致的可用路径）

            # 解析用户自定义模块导入（预编译并注册模块）
            mod_registered = set()
            mod_exported_names = set()
            if source_file:
                source_dir = os.path.dirname(os.path.abspath(source_file))
                self._register_user_modules(source, source_dir, mod_registered, mod_exported_names)

            from light_parser_v3 import LightParser, ParseError
            from code_generator import PythonCodeGenerator, CodeGenError

            try:
                parser = LightParser()
                module = parser.parse(source, filename=source_file, extra_definitions=mod_exported_names)
                if not module:
                    print(f"[语法错误] 解析失败: {source_file}", file=sys.stderr)
                    return 1
            except ParseError as e:
                print(f"[语法错误]\n{e}", file=sys.stderr)
                return 1

            try:
                generator = PythonCodeGenerator(stdlib_dir=_resolve_compile_time_stdlib())
                python_code = generator.generate(module)
            except CodeGenError as e:
                print(f"[代码生成错误] {e}", file=sys.stderr)
                return 1
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(python_code)
                print(f"[成功] 已生成: {output_file}")

                # 让产物自包含：把依赖的用户模块一并编译到产物同目录。
                # 上面的 _register_user_modules 只往本进程 sys.modules 里塞对象，
                # 进程一退出就没了；写出去的 .py 里那句 `from 学生模块 import …`
                # 于是成为悬空引用（单 D）。
                if source_file:
                    out_dir = os.path.dirname(os.path.abspath(output_file))
                    src_dir = os.path.dirname(os.path.abspath(source_file))
                    emitted = self._emit_user_modules(source, src_dir, out_dir)
                    if emitted:
                        print("[成功] 已随产物生成依赖模块: "
                              + ', '.join(f'{m}.py' for m in emitted))

                # 同理：`引 Python:` 块里 import 的 L3 运行时模块（l3_echarts 等）
                # 住在编译器 src/ 里，产物换进程裸跑时 sys.path 上没有那一档，
                # 也要一并落盘（单 29）。这条不依赖 source_file。
                out_dir = os.path.dirname(os.path.abspath(output_file))
                emitted_rt = self._emit_runtime_modules(source, out_dir)
                if emitted_rt:
                    print("[成功] 已随产物生成 L3 运行时模块: "
                          + ', '.join(f'{m}.py' for m in emitted_rt))

            if run:
                try:
                    exec_globals = {
                        '__name__': '__main__',
                        '__file__': output_file or '<light_script>',
                        '__builtins__': __builtins__,
                    }
                    exec(python_code, exec_globals)
                except SyntaxError as e:
                    print(f"[运行错误] 生成的 Python 代码存在语法错误 (行 {e.lineno}): {e.msg}", file=sys.stderr)
                    return 1
                except Exception as e:
                    print(f"[运行错误] {e}", file=sys.stderr)
                    return 1
            
            return 0
    
    def interpret_run(self, source_file: str, script_args: list = None) -> int:
        """使用编译器编译并运行（替代旧版解释器）
        
        Args:
            source_file: 源文件路径
            script_args: 传递给脚本的参数列表（不含文件路径）
        """
        source_file = os.path.abspath(source_file)
        if not os.path.exists(source_file):
            print(f"[错误] 文件不存在: {source_file}", file=sys.stderr)
            return 1
        
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                source = f.read()
        except IOError as e:
            print(f"[错误] 无法读取文件 {source_file}: {e}", file=sys.stderr)
            return 1
        
        # 设置脚本的 sys.argv
        old_argv = sys.argv
        sys.argv = [source_file] + (script_args or [])
        try:
            return self.compile_with_src(source, run=True, source_file=source_file)
        except Exception as e:
            print(f"[内部错误] 编译器异常: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1
        finally:
            sys.argv = old_argv
    
    def start_repl(self, v3: bool = False) -> int:
        """启动REPL

        Args:
            v3: 是否使用基于 v3 解析器的 REPL
        """
        if v3:
            try:
                from tools.repl_v3 import LightREPLV3
                repl = LightREPLV3()
                repl.run()
                return 0
            except ImportError as e:
                print(f"[错误] REPL v3 模块不可用: {e}", file=sys.stderr)
                # 回退到旧版 REPL
                pass

        try:
            # 先尝试导入 tools.repl（新位置）
            from tools.repl import LightREPL
            repl = LightREPL()
            repl.run()
            return 0
        except ImportError:
            pass
        
        try:
            # 再尝试导入 light_repl（旧位置）
            from light_repl import main as repl_main
            repl_main()
            return 0
        except ImportError:
            # 最后尝试 v3 REPL
            try:
                from tools.repl_v3 import LightREPLV3
                repl = LightREPLV3()
                repl.run()
                return 0
            except ImportError:
                print("[错误] REPL模块不可用", file=sys.stderr)
                return 1
    
    def start_debug_repl(self) -> int:
        """启动调试REPL"""
        try:
            from tools.light_debug_repl import LightDebugREPL
            repl = LightDebugREPL()
            repl.run()
            return 0
        except ImportError:
            print("[错误] 调试REPL模块不可用", file=sys.stderr)
            return 1
    
    def pkg_init(self, project_name: str) -> int:
        """创建新的光明项目骨架"""
        project_dir = Path(project_name)
        if project_dir.exists():
            print(f"[错误] 目录已存在: {project_dir}", file=sys.stderr)
            return 1

        # 创建目录结构
        project_dir.mkdir(parents=True)
        (project_dir / 'src').mkdir()
        (project_dir / 'tests').mkdir()
        (project_dir / 'lib').mkdir()

        # .gitignore - 遵循安全规则，不提交敏感信息
        gitignore = project_dir / '.gitignore'
        gitignore.write_text('''# 光明项目忽略文件

# 编译产物
*.py
!build.py
__pycache__/
*.pyc

# 环境变量与密钥
.env
.env.local
*.key
*.pem

# 系统文件
.DS_Store
Thumbs.db

# 项目构建缓存
.light_cache/
build/
''', encoding='utf-8')

        # light.json - 项目配置
        light_json = project_dir / 'light.json'
        light_json.write_text('''{
    "name": "%s",
    "version": "0.1.0",
    "entry": "main.light",
    "description": "光明项目",
    "dependencies": {},
    "scripts": {
        "build": "light compile main.light",
        "test": "light test",
        "run": "light run main.light"
    }
}
''' % project_name, encoding='utf-8')

        # main.light - 入口文件（展示模块化结构）
        main_light = project_dir / 'main.light'
        main_light.write_text('''# 光明项目入口
# 这是项目的主入口文件，负责初始化并启动应用

导入《工具》为 工具。

段落 主():
    打印("=" * 40)
    打印("欢迎使用 {项目名称}！")
    打印("=" * 40)
    
    设 问候 为 工具.生成问候语("光明开发者")。
    打印(问候)
    
    工具.演示功能()
    
    打印("\\n程序执行完毕。")

# 启动程序
主()。
'''.replace('{项目名称}', project_name), encoding='utf-8')

        # 工具.light - 工具模块示例（放在项目根目录，方便导入）
        utils_light = project_dir / '工具.light'
        utils_light.write_text('''# 工具模块 — 提供通用功能函数

段落 生成问候语(名称):
    返回 "你好，{名称}！欢迎使用光明编程语言。"

段落 演示功能():
    打印("\\n--- 功能演示 ---")
    
    # 变量与计算
    设 数字 为 [1, 2, 3, 4, 5]。
    设 总和 为 0。
    遍历 项 之 数字:
        总和 = 总和 加 项。
    打印("1+2+3+4+5 = ", 总和)
    
    # 条件判断
    设 分数 为 85。
    如果 分数 大于等于 90:
        打印("成绩: 优秀")
    否则 如果 分数 大于等于 80:
        打印("成绩: 良好")
    否则:
        打印("成绩: 一般")
    
    # 字典使用
    设 配置 为 {"语言": "光明", "版本": "0.1", "作者": "开发者"}。
    打印("配置: ", 配置)
    
    # 异常处理
    尝试:
        设 结果 为 10 除以 0。
    捕获 异常 为 错误:
        打印("捕获到异常: ", 错误)
    否则:
        打印("结果: ", 结果)

段落 计算平均数(数字列表):
    """计算数字列表的平均数"""
    设 长度 为 数字列表.长度()。
    如果 长度 等于 0:
        返回 0。
    设 总和 为 0。
    遍历 数 之 数字列表:
        总和 = 总和 加 数。
    返回 总和 除以 长度。
''', encoding='utf-8')

        # src/__init__.light - 源文件目录说明
        src_init = project_dir / 'src' / '__init__.light'
        src_init.write_text('''# 源文件目录
# 将项目的核心代码放在 src/ 目录下
# 大型项目建议按模块拆分到不同文件
# 使用「导入」语句引用其他模块
''', encoding='utf-8')

        # tests/__init__.light - 测试初始化
        tests_init = project_dir / 'tests' / '__init__.light'
        tests_init.write_text('''# 测试目录
# 将测试文件放在 tests/ 目录下
# 使用「断言」关键字编写测试用例
''', encoding='utf-8')

        # tests/test_工具.light - 测试示例
        test_utils = project_dir / 'tests' / 'test_工具.light'
        test_utils.write_text('''# 工具模块测试
导入《工具》为 工具。

段落 测试_生成问候语():
    设 结果 为 工具.生成问候语("测试")。
    断言 字符串包含(结果, "测试")，"问候语应包含名称"。
    断言 字符串包含(结果, "光明")，"问候语应包含语言名称"。
    打印("✓ 测试_生成问候语 通过")

段落 测试_计算平均数():
    断言 工具.计算平均数([1, 2, 3]) 等于 2，"1,2,3的平均数应为2"。
    断言 工具.计算平均数([]) 等于 0，"空列表的平均数应为0"。
    断言 工具.计算平均数([5]) 等于 5，"单元素列表的平均数应为其本身"。
    打印("✓ 测试_计算平均数 通过")

# 运行全部测试
段落 运行测试():
    打印("运行测试...")
    测试_生成问候语()
    测试_计算平均数()
    打印("\\n全部测试通过！")

运行测试()。
''', encoding='utf-8')

        # build.py - 构建脚本
        build_py = project_dir / 'build.py'
        build_py.write_text('''#!/usr/bin/env python3
"""光明项目构建脚本 - 编译 .light 文件为 .py"""

import os
import sys
import subprocess
from pathlib import Path


def build():
    """编译项目中所有 .light 文件"""
    project_dir = Path(__file__).parent
    entry = project_dir / "main.light"

    if not entry.exists():
        print(f"[错误] 入口文件不存在: {entry}")
        return False

    # 编译入口文件
    result = subprocess.run(
        [sys.executable, "-m", "cli.light_unified", "compile", str(entry)],
        capture_output=True, text=True, cwd=str(project_dir)
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout)
        return False

    # 编译测试文件
    test_entry = project_dir / "tests" / "test_工具.light"
    if test_entry.exists():
        result = subprocess.run(
            [sys.executable, "-m", "cli.light_unified", "compile", str(test_entry)],
            capture_output=True, text=True, cwd=str(project_dir)
        )
        if result.returncode != 0:
            print(result.stderr or result.stdout)
            return False

    print(f"[成功] 项目构建完成: {project_dir}")
    return True


def run_tests():
    """运行测试"""
    project_dir = Path(__file__).parent
    test_file = project_dir / "tests" / "test_工具.light"
    
    if not test_file.exists():
        print("[错误] 测试文件不存在")
        return False
    
    result = subprocess.run(
        [sys.executable, "-m", "cli.light_unified", "run", str(test_file)],
        capture_output=True, text=True, cwd=str(project_dir)
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        return False
    return True


if __name__ == "__main__":
    # 默认构建，如果参数是 "test" 则运行测试
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        success = run_tests()
    else:
        success = build()
    sys.exit(0 if success else 1)
''', encoding='utf-8')

        print(f"[成功] 已创建项目: {project_name}/")
        print(f"  main.light            入口文件")
        print(f"  light.json            项目配置")
        print(f"  .gitignore           忽略文件（安全规则）")
        print(f"  工具.light            工具模块示例")
        print(f"  src/                 源文件目录")
        print(f"    __init__.light       模块初始化")
        print(f"  tests/               测试目录")
        print(f"    __init__.light       测试初始化")
        print(f"    test_工具.light      测试文件示例")
        print(f"  lib/                 第三方库目录")
        print(f"  build.py             构建脚本")
        print(f"\n运行: light run {project_name}/main.light")
        print(f"测试: light test {project_name}")
        print(f"构建: cd {project_name} && light pkg build")
        return 0

    def pkg_build(self, project_dir: str = '.') -> int:
        """编译项目中的 .light 文件为 .py"""
        root = Path(project_dir)
        if not root.is_dir():
            print(f"[错误] 目录不存在: {root}", file=sys.stderr)
            return 1

        light_files = list(root.glob('*.light'))
        if not light_files:
            print(f"[错误] 未找到 .light 文件: {root}", file=sys.stderr)
            return 1

        success_count = 0
        for f in light_files:
            source = f.read_text(encoding='utf-8')
            output_file = f.with_suffix('.py')
            try:
                # 尝试 src 后端
                from light_parser_v3 import LightParser
                from code_generator import PythonCodeGenerator
                parser = LightParser()
                module = parser.parse(source)
                if module is None:
                    print(f"[跳过] 解析失败: {f}", file=sys.stderr)
                    continue
                generator = PythonCodeGenerator()
                py_code = generator.generate(module)
                output_file.write_text(py_code, encoding='utf-8')
                print(f"[编译] {f.name} -> {output_file.name}")
                success_count += 1
            except ImportError:
                # 尝试 ANTLR 后端
                try:
                    from light_visitor import LightParser as LightParser2
                    from code_generator_unified import UnifiedCodeGenerator
                    from indent_preprocessor import preprocess_v3_syntax
                    processed = preprocess_v3_syntax(source)
                    parser = LightParser2()
                    module = parser.parse(processed)
                    if module is None:
                        print(f"[跳过] 解析失败: {f}", file=sys.stderr)
                        continue
                    generator = UnifiedCodeGenerator()
                    py_code = generator.generate(module)
                    output_file.write_text(py_code, encoding='utf-8')
                    print(f"[编译] {f.name} -> {output_file.name}")
                    success_count += 1
                except ImportError:
                    print(f"[错误] 无可用编译后端", file=sys.stderr)
                    return 1
            except Exception as e:
                print(f"[错误] 编译 {f.name} 失败: {e}", file=sys.stderr)
                continue

        print(f"\n[摘要] 成功: {success_count}/{len(light_files)}")
        return 0 if success_count > 0 else 1

    def run_tests(self, target: str = None, filter_pattern: str = None, verbose: bool = False) -> int:
        """运行光明测试

        Args:
            target: 项目目录或测试文件路径（默认: 当前目录）
            filter_pattern: 按名称过滤测试文件
            verbose: 详细输出

        Returns:
            退出码（0=全部通过）
        """
        from test_runner import run_tests as _run_tests, run_single_file

        if target and os.path.isfile(target):
            return run_single_file(target, verbose=verbose)
        else:
            directory = target or os.getcwd()
            return _run_tests(directory, filter_pattern=filter_pattern, verbose=verbose)

    def syntax_check(self, source_file: str) -> int:
        """检查文件语法是否正确"""
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                source = f.read()

            # 尝试 src 后端解析
            try:
                from light_parser_v3 import LightParser, ParseError
                parser = LightParser()
                module = parser.parse(source, filename=source_file)
                if module is None:
                    print(f"[语法错误] 解析失败: {source_file}", file=sys.stderr)
                    return 1
                if hasattr(parser, 'errors') and parser.errors:
                    for error in parser.errors:
                        print(error, file=sys.stderr)
                    return 1
                print("[通过] 语法检查通过")
                return 0
            except ParseError as e:
                print(f"[语法错误]\n{e}", file=sys.stderr)
                return 1
            except ImportError:
                pass

            # 尝试 ANTLR 后端解析
            try:
                from antlr4 import InputStream, CommonTokenStream
                from LightLangLexer import LightLangLexer
                from LightLangParser import LightLangParser
                from light_visitor import LightLangASTBuilder

                input_stream = InputStream(source)
                lexer = LightLangLexer(input_stream)
                tokens = CommonTokenStream(lexer)
                parser = LightLangParser(tokens)
                tree = parser.program()
                if parser.getNumberOfSyntaxErrors() > 0:
                    print("[语法错误] 存在语法错误", file=sys.stderr)
                    return 1
                print("[通过] 语法检查通过")
                return 0
            except ImportError:
                print("[错误] 无可用解析后端", file=sys.stderr)
                return 1
        except Exception as e:
            print(f"[错误] 语法检查失败: {e}", file=sys.stderr)
            return 1

    def format_code(self, target: str, check_only: bool = False) -> int:
        """格式化光明代码"""
        try:
            from formatter import run_formatter
            return run_formatter(target, check_only)
        except ImportError as e:
            print(f"[错误] 格式化模块不可用: {e}", file=sys.stderr)
            return 1

    def show_ast(self, source: str, backend: str = 'antlr') -> int:
        """显示AST结构"""
        if backend == 'antlr':
            from antlr4 import InputStream, CommonTokenStream
            from LightLangLexer import LightLangLexer
            from LightLangParser import LightLangParser
            from light_visitor import LightLangASTBuilder
            
            input_stream = InputStream(source)
            lexer = LightLangLexer(input_stream)
            tokens = CommonTokenStream(lexer)
            parser = LightLangParser(tokens)
            tree = parser.program()
            builder = LightLangASTBuilder()
            module = builder.visitProgram(tree)
        else:
            from light_parser_v3 import LightParser
            parser = LightParser()
            module = parser.parse(source)
        
        if module:
            self._print_ast(module, 0)
            return 0
        else:
            print("[错误] 解析失败", file=sys.stderr)
            return 1
    
    def _print_ast(self, node, indent: int):
        """打印AST节点"""
        prefix = "  " * indent
        node_type = type(node).__name__
        
        if hasattr(node, 'name'):
            print(f"{prefix}{node_type}: {node.name}")
        else:
            print(f"{prefix}{node_type}")
        
        # 递归打印子节点
        for attr in ['statements', 'segments', 'classes', 'body', 'parameters', 'arguments']:
            if hasattr(node, attr):
                children = getattr(node, attr)
                if isinstance(children, list):
                    for child in children:
                        self._print_ast(child, indent + 1)
                elif children:
                    self._print_ast(children, indent + 1)


def main():
    """主函数"""
    # 中文别名映射表
    _cn_alias_map = {
        '运行': 'run',
        '编译': 'compile',
        '语法检查': 'check',
        '格式化': 'fmt',
        '项目构建': 'pkg build',
        '原生编译': 'compile --target llvm',
        '交互式': 'repl',
        '调试': 'debug',
        '新建项目': 'new',
        '版本': '--version',
        '帮助': '--help',
    }

    # 检查并转换中文别名
    if len(sys.argv) > 1 and sys.argv[1] in _cn_alias_map:
        mapped = _cn_alias_map[sys.argv[1]]
        mapped_parts = mapped.split()
        # 替换 sys.argv[1] 为映射后的英文命令
        # 例如 'light 项目构建' → 'light pkg build'
        # 例如 'light 版本' → 'light --version'
        sys.argv[1:2] = mapped_parts

    cli = LightUnifiedCLI()
    
    # 检查是否是子命令模式
    if len(sys.argv) > 1 and sys.argv[1] in ['run', 'compile', 'repl', 'debug', 'pkg', 'check', 'fmt', 'new', 'test']:
        # 子命令模式
        parser = argparse.ArgumentParser(description='光明（Light）编程语言编译器')
        parser.add_argument('--version', action='version', version=VERSION_STR)
        parser.add_argument('--dev-version', action='store_true', help='显示开发分支版本信息')
        subparsers = parser.add_subparsers(dest='command', help='子命令')
        
        # run 子命令
        run_parser = subparsers.add_parser('run', help='解释执行文件')
        run_parser.add_argument('file', help='源文件路径')
        
        # compile 子命令
        compile_parser = subparsers.add_parser('compile', help='编译文件')
        compile_parser.add_argument('file', help='源文件路径')
        compile_parser.add_argument('-o', '--output', help='输出文件路径')
        compile_parser.add_argument('--backend', choices=['antlr', 'src'], default='src',
                                   help='选择编译后端（默认：src）')
        compile_parser.add_argument('--target', choices=['py', 'js', 'wasm', 'llvm'], default='py',
                                   help='目标代码（默认：py，llvm 生成 LLVM IR）')
        
        # repl 子命令
        repl_parser = subparsers.add_parser('repl', help='启动交互式REPL')
        repl_parser.add_argument('--v3', action='store_true', help='使用基于 v3 解析器的 REPL（推荐）')
        
        # debug 子命令
        debug_parser = subparsers.add_parser('debug', help='启动调试REPL')
        debug_parser.add_argument('file', nargs='?', help='要调试的文件路径（可选）')
        
        # check 子命令
        check_parser = subparsers.add_parser('check', help='语法检查')
        check_parser.add_argument('file', help='源文件路径')
        check_parser.add_argument('--backend', choices=['antlr', 'src'], default='src',
                                  help='选择解析后端（默认：src）')
        
        # fmt 子命令
        fmt_parser = subparsers.add_parser('fmt', help='格式化代码')
        fmt_parser.add_argument('target', help='文件或目录路径')
        fmt_parser.add_argument('--check', action='store_true', help='仅检查格式，不修改文件')
        
        # new 子命令
        new_parser = subparsers.add_parser('new', help='创建新项目')
        new_parser.add_argument('name', help='项目名称')
        
        # test 子命令
        test_parser = subparsers.add_parser('test', help='运行测试')
        test_parser.add_argument('target', nargs='?', default=None,
                                help='项目目录或测试文件路径（默认: 当前目录）')
        test_parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
        test_parser.add_argument('--filter', help='按名称过滤测试文件')
        
        # pkg 子命令
        pkg_parser = subparsers.add_parser('pkg', help='项目管理（init/build）')
        pkg_sub = pkg_parser.add_subparsers(dest='pkg_command', help='pkg 子命令')
        
        pkg_init_parser = pkg_sub.add_parser('init', help='创建新项目骨架')
        pkg_init_parser.add_argument('name', help='项目名称')
        
        pkg_build_parser = pkg_sub.add_parser('build', help='编译项目中的 .light 文件为 .py')
        pkg_build_parser.add_argument('--dir', default='.', help='项目目录（默认: 当前目录）')
        pkg_build_parser.add_argument('--incremental', action='store_true', help='使用增量编译（仅编译变更文件）')
        pkg_build_parser.add_argument('--force', '-f', action='store_true', help='强制全量编译（忽略增量缓存）')
        
        args, unknown = parser.parse_known_args()
        
        # 处理 --dev-version 标志
        if getattr(args, 'dev_version', False):
            try:
                from src.version import get_dev_version_string
                print(get_dev_version_string())
            except ImportError:
                print(VERSION_STR)
            return 0
        
        if args.command == 'run':
            if not os.path.exists(args.file):
                print(f"[错误] 文件不存在: {args.file}", file=sys.stderr)
                return 1
            # Path A（单条子进程隔离）：把入口文件绝对路径与解释器路径注入环境，
            # 供 eval 链把单条评测项丢进子进程时复用同一入口。.py 不被 python_direct_calls 棘轮扫描。
            os.environ['HARNESS_ENTRY_FILE'] = os.path.abspath(args.file)
            os.environ['HARNESS_PYTHON'] = sys.executable
            # 将未知参数作为脚本参数传递（--input, --output 等）
            return cli.interpret_run(args.file, script_args=unknown)
        
        elif args.command == 'compile':
            if not os.path.exists(args.file):
                print(f"[错误] 文件不存在: {args.file}", file=sys.stderr)
                return 1
            with open(args.file, 'r', encoding='utf-8') as f:
                source = f.read()
            
            output_file = args.output or args.file.replace('.light', '.py')
            
            if args.backend == 'antlr':
                return cli.compile_with_antlr(source, output_file=output_file, run=False, source_file=args.file)
            else:
                return cli.compile_with_src(source, output_file=output_file, run=False, target=args.target, source_file=args.file)
        
        elif args.command == 'repl':
            return cli.start_repl(v3=getattr(args, 'v3', False))
        
        elif args.command == 'debug':
            if args.file:
                # 调试模式下加载文件
                if not os.path.exists(args.file):
                    print(f"[错误] 文件不存在: {args.file}", file=sys.stderr)
                    return 1
                from tools.light_debug_repl import LightDebugREPL
                repl = LightDebugREPL()
                repl.load_file(args.file)
                return 0
            else:
                return cli.start_debug_repl()
        
        elif args.command == 'check':
            if not os.path.exists(args.file):
                print(f"[错误] 文件不存在: {args.file}", file=sys.stderr)
                return 1
            return cli.syntax_check(args.file)
        
        elif args.command == 'fmt':
            return cli.format_code(args.target, check_only=args.check)
        
        elif args.command == 'new':
            return cli.pkg_init(args.name)
        
        elif args.command == 'test':
            return cli.run_tests(
                target=args.target,
                filter_pattern=getattr(args, 'filter', None),
                verbose=args.verbose
            )
        
        elif args.command == 'pkg':
            if not getattr(args, 'pkg_command', None):
                pkg_parser.print_help()
                return 1
            if args.pkg_command == 'init':
                return cli.pkg_init(args.name)
            elif args.pkg_command == 'build':
                if getattr(args, 'incremental', False):
                    try:
                        from incremental_build import incremental_build_cli
                        result = incremental_build_cli(
                            project_dir=args.dir,
                            force=getattr(args, 'force', False),
                            verbose=True
                        )
                        return 0 if result == 0 else 1
                    except ImportError as e:
                        print(f"❌ 增量编译模块不可用: {e}", file=sys.stderr)
                        return 1
                else:
                    return cli.pkg_build(args.dir)
    
    else:
        # 默认模式：编译并运行
        parser = argparse.ArgumentParser(
            description='光明（Light）编程语言编译器',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例：
  light hello.light                      # 编译并运行
  light hello.light --backend src        # 使用src后端
  light run hello.light                  # 解释执行
  light compile hello.light -o hello.py  # 编译为Python文件
  light repl                            # 启动交互式REPL
  light hello.light --ast                # 显示AST结构
            """
        )
        
        parser.add_argument('file', nargs='?', help='源文件路径')
        parser.add_argument('--backend', choices=['antlr', 'src'], default='antlr',
                           help='选择编译后端（默认：antlr）')
        parser.add_argument('-o', '--output', help='输出文件路径')
        parser.add_argument('--run', action='store_true', help='编译并运行')
        parser.add_argument('--ast', action='store_true', help='显示AST结构')
        parser.add_argument('--welcome', action='store_true',
                           help='显示首次运行欢迎引导')
        parser.add_argument('--version', action='version', version=VERSION_STR)
        parser.add_argument('--dev-version', action='store_true', help='显示开发分支版本信息')
        
        args = parser.parse_args()
        
        # --welcome 标志：触发首次运行引导
        if args.welcome:
            try:
                sys.path.insert(0, _local_src)
                from first_run import run_welcome
                result = run_welcome()
                if result == 'repl':
                    from first_run import start_repl
                    start_repl()
            except ImportError as e:
                print(f"[错误] 无法加载首次运行引导模块: {e}", file=sys.stderr)
                return 1
            return 0
        
        # 处理 --dev-version 标志
        if getattr(args, 'dev_version', False):
            try:
                from src.version import get_dev_version_string
                print(get_dev_version_string())
            except ImportError:
                print(VERSION_STR)
            return 0
        
        if args.file:
            if not os.path.exists(args.file):
                print(f"[错误] 文件不存在: {args.file}", file=sys.stderr)
                return 1
            
            with open(args.file, 'r', encoding='utf-8') as f:
                source = f.read()
            
            output_file = args.output
            
            if args.ast:
                return cli.show_ast(source, args.backend)
            
            run_mode = args.run or (not args.output)
            
            if args.backend == 'antlr':
                return cli.compile_with_antlr(source, output_file=output_file, run=run_mode)
            else:
                return cli.compile_with_src(source, output_file=output_file, run=run_mode, source_file=args.file)
        
        else:
            # 无参数时启动REPL
            return cli.start_repl()


if __name__ == '__main__':
    sys.exit(main())
