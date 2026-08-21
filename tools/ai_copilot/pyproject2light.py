#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python 项目 -> 光明项目 批量转译器

将一个完整的 Python 项目（多文件、目录结构、import 关系）批量转译为光明项目。
基于单文件转译器 py2light_transpiler.py 扩展。

用法:
    python pyproject2light.py <源项目目录> [-o <输出目录>] [--dry-run] [--verbose]

示例:
    python pyproject2light.py ./my_python_project -o ./my_light_project
    python pyproject2light.py ./my_python_project --dry-run --verbose

产物:
    输出目录/
        (保留原始目录结构)
        *.light          -- 转译后的光明源文件
        (非 .py 文件原样复制)
        light.json        -- 项目清单
        CONVERSION_REPORT.md -- 转译报告
        build.py         -- 构建脚本（.light -> .py 编译运行）
"""
import ast
import json
import os
import sys
import shutil
import argparse
import sysconfig
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 确保能导入同目录下的单文件转译器
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from py2light_transpiler import Py2LightTranspiler, TranspileError, FeatureUsageCollector


# ==================== 常量 ====================

SKIP_DIRS = {
    "__pycache__", ".git", ".hg", ".svn",
    "venv", ".venv", "env", ".env",
    "node_modules", "build", "dist", ".eggs",
    ".mypy_cache", ".pytest_cache", ".tox", ".ruff_cache",
    "__pypackages__", ".idea", ".vscode",
}

SKIP_SUFFIXES = {".pyc", ".pyo", ".pyd", ".so", ".dll", ".egg"}

# 标准库顶层模块集合（用于 import 分类）
_STDLIB_PATHS = set()
try:
    _STDLIB_PATHS = set(
        Path(p).resolve() for p in sysconfig.get_paths().values()
        if "site-packages" not in p
    )
except Exception:
    pass

_STDLIB_TOP_MODULES = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else {
    "os", "sys", "re", "json", "csv", "math", "random", "datetime",
    "collections", "itertools", "functools", "pathlib", "typing",
    "io", "abc", "argparse", "subprocess", "threading", "multiprocessing",
    "socket", "http", "urllib", "logging", "warnings", "traceback",
    "unittest", "copy", "enum", "dataclasses", "contextlib",
    "time", "struct", "base64", "hashlib", "hmac", "secrets",
    "sqlite3", "xml", "html", "email", "pickle", "shelve",
    "tempfile", "shutil", "glob", "fnmatch", "inspect",
    "string", "textwrap", "unicodedata", "codecs", "locale",
    "platform", "getpass", "signal", "errno", "stat",
    "operator", "decimal", "fractions", "numbers",
    "calendar", "heapq", "bisect", "array", "queue",
    "types", "weakref", "gc", "atexit",
}


# ==================== Import 分析器 ====================

class ImportAnalyzer(ast.NodeVisitor):
    """分析单个 Python 文件的 import 语句，分类为本地/标准库/第三方"""

    def __init__(self, file_rel_path: str, local_module_names: set):
        self.file_rel_path = file_rel_path
        self.local_module_names = local_module_names  # 项目内顶层模块名集合
        self.local_imports = []
        self.stdlib_imports = []
        self.thirdparty_imports = []

    def _classify(self, top_module: str) -> str:
        """分类 import 来源"""
        if top_module in self.local_module_names:
            return "local"
        if top_module in _STDLIB_TOP_MODULES:
            return "stdlib"
        return "thirdparty"

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            top = alias.name.split(".")[0]
            cat = self._classify(top)
            entry = {
                "module": alias.name,
                "asname": alias.asname,
                "line": node.lineno,
            }
            if cat == "local":
                self.local_imports.append(entry)
            elif cat == "stdlib":
                self.stdlib_imports.append(entry)
            else:
                self.thirdparty_imports.append(entry)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            top = node.module.split(".")[0]
            # 相对导入 (level > 0) 视为本地
            if node.level and node.level > 0:
                self.local_imports.append({
                    "module": node.module or "",
                    "names": [a.name for a in node.names],
                    "level": node.level,
                    "line": node.lineno,
                })
            else:
                cat = self._classify(top)
                entry = {
                    "module": node.module,
                    "names": [a.name for a in node.names],
                    "line": node.lineno,
                }
                if cat == "local":
                    self.local_imports.append(entry)
                elif cat == "stdlib":
                    self.stdlib_imports.append(entry)
                else:
                    self.thirdparty_imports.append(entry)
        self.generic_visit(node)


# ==================== 项目级转译器 ====================

class ProjectTranspiler:
    """Python 项目 -> 光明项目 批量转译器"""

    def __init__(self, src_dir: str, out_dir: str,
                 dry_run: bool = False, verbose: bool = False):
        self.src_dir = Path(src_dir).resolve()
        self.out_dir = Path(out_dir).resolve()
        self.dry_run = dry_run
        self.verbose = verbose

        self.transpiler = Py2LightTranspiler()

        # 统计数据
        self.stats = {
            "total_py_files": 0,
            "transpiled": 0,
            "failed": 0,
            "skipped": 0,
            "copied_files": 0,
            "parse_validated": 0,
            "parse_failed": 0,
        }

        # 文件级结果
        self.file_results = []  # [{rel_path, status, error, ...}]

        # import 汇总
        self.all_imports = {
            "local": defaultdict(list),      # module -> [files]
            "stdlib": defaultdict(list),
            "thirdparty": defaultdict(list),
        }

        # 项目内顶层模块名（用于 import 分类）
        self.local_module_names = set()

        # Python 特性使用统计
        self.feature_stats = defaultdict(int)

        # 建议规则（用于修复建议）
        self._suggestion_rules = {
            "Match": "match-case 模式匹配：光明不直接支持 match-case，转译为「匹配...情况」结构。",
            "AsyncFunctionDef": "async/await 异步函数：光明支持「异步 函数」语法，但运行时需要 asyncio 支持。",
            "decorator": "装饰器：光明使用「标注」关键字替代 Python 的 @decorator 语法。",
            "type_annotation": "类型注解：光明不直接支持类型注解，已忽略类型信息。",
            "Lambda": "lambda 匿名函数：光明支持「接收...返回...」匿名函数语法。",
            "Yield": "生成器：光明支持「产出」关键字替代 yield。",
            "NamedExpr": "海象运算符 (:=)：光明不支持海象运算符，请改用普通赋值。",
            "AnnAssign": "类型注解赋值：光明不支持类型注解，已忽略注解部分。",
            "chain_call": "链式调用：光明支持 obj.方法().属性 链式语法。",
            "fstring": "f-string：光明不直接支持 f-string，已转译为普通字符串拼接或格式化。",
        }

    # ---------- 主流程 ----------

    def run(self):
        """执行项目级转译"""
        self._log(f"源项目目录: {self.src_dir}")
        self._log(f"输出目录:   {self.out_dir}")
        if self.dry_run:
            self._log("模式: dry-run (预览，不写入文件)")

        # 1. 扫描项目，确定本地模块名
        self._scan_local_modules()

        # 2. 创建输出目录
        if not self.dry_run:
            self.out_dir.mkdir(parents=True, exist_ok=True)

        # 3. 遍历转译
        self._walk_and_transpile()

        # 4. 生成 light.json
        if not self.dry_run:
            self._generate_light_json()

        # 5. 生成 CONVERSION_REPORT.md
        if not self.dry_run:
            self._generate_report()

        # 6. 生成 build.py
        if not self.dry_run:
            self._generate_build_script()

        # 7. 打印摘要
        self._print_summary()

    # ---------- 扫描本地模块名 ----------

    def _scan_local_modules(self):
        """扫描项目目录，收集所有顶层模块名（用于 import 分类）"""
        for entry in self.src_dir.iterdir():
            if entry.name in SKIP_DIRS:
                continue
            if entry.is_file() and entry.suffix == ".py":
                # 顶层 .py 文件 -> 模块名 = stem
                self.local_module_names.add(entry.stem)
            elif entry.is_dir():
                # 目录可能是包
                if (entry / "__init__.py").exists() or any(entry.glob("*.py")):
                    self.local_module_names.add(entry.name)

        self._log(f"检测到本地模块: {sorted(self.local_module_names)}")

    # ---------- 遍历转译 ----------

    def _walk_and_transpile(self):
        """递归遍历源目录，转译 .py 文件，复制其他文件"""
        for root, dirs, files in os.walk(self.src_dir):
            # 过滤跳过目录
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            rel_root = Path(root).relative_to(self.src_dir)

            for fname in sorted(files):
                src_file = Path(root) / fname
                rel_path = rel_root / fname

                # 跳过构建产物
                if any(suffix in fname for suffix in SKIP_SUFFIXES):
                    continue

                if fname.endswith(".py"):
                    self.stats["total_py_files"] += 1
                    self._transpile_file(src_file, rel_path)
                else:
                    self._copy_file(src_file, rel_path)

    def _transpile_file(self, src_file: Path, rel_path: Path):
        """转换单个 .py 文件为 .light"""
        light_rel_path = rel_path.with_suffix(".light")
        result = {
            "src": str(rel_path),
            "dst": str(light_rel_path),
            "status": "pending",
            "error": None,
            "parse_ok": None,
            "parse_error": None,
            "parse_error_type": None,
            "parse_lineno": None,
            "source_lines": [],
            "feature_stats": {},
        }

        try:
            # 读取 Python 源码
            encoding = self._detect_encoding(src_file)
            with open(src_file, "r", encoding=encoding) as f:
                py_code = f.read()

            # 保存源码行（用于报告）
            result["source_lines"] = py_code.split("\n")

            # 分析 imports
            self._analyze_imports(py_code, str(rel_path))

            # 收集 Python 特性统计
            try:
                tree = ast.parse(py_code)
                collector = FeatureUsageCollector()
                collector.visit(tree)
                result["feature_stats"] = collector.get_summary()
                # 汇总到项目级统计
                for feat_key, feat_count in collector.get_summary().items():
                    self.feature_stats[feat_key] += feat_count
            except SyntaxError:
                pass

            # 转译
            light_code = self.transpiler.transpile(py_code)
            result["status"] = "transpiled"
            self.stats["transpiled"] += 1

            # import 路径重写：光明的"从 X.Y 导入 Z"不支持点号路径
            light_code = self._rewrite_imports(light_code, rel_path)

            # 光明解析器验证（返回详细结果）
            validate_result = self._validate_light(light_code)
            result["parse_ok"] = validate_result["success"]
            result["parse_error"] = validate_result["error"]
            result["parse_error_type"] = validate_result["error_type"]
            result["parse_lineno"] = validate_result["lineno"]
            if validate_result["success"]:
                self.stats["parse_validated"] += 1
            else:
                self.stats["parse_failed"] += 1

            # 写入 .light 文件
            if not self.dry_run:
                dst_file = self.out_dir / light_rel_path
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                with open(dst_file, "w", encoding="utf-8") as f:
                    f.write(light_code)

            self._log(f"  [OK] {rel_path} -> {light_rel_path}"
                      + ("" if validate_result["success"] else "  [PARSE WARNING]"))

        except TranspileError as e:
            result["status"] = "failed"
            result["error"] = str(e)
            result["parse_error"] = str(e)
            result["parse_error_type"] = "TranspileError"
            result["parse_lineno"] = getattr(e, 'lineno', None)
            self.stats["failed"] += 1
            self._log(f"  [FAIL] {rel_path}: {e}")

            # 失败时仍然复制原始 .py 文件作为 fallback
            if not self.dry_run:
                dst_file = self.out_dir / rel_path
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)

        except SyntaxError as e:
            result["status"] = "failed"
            result["error"] = f"Python 语法错误: {e}"
            result["parse_error"] = f"Python 语法错误: {e.msg}"
            result["parse_error_type"] = "SyntaxError"
            result["parse_lineno"] = e.lineno
            self.stats["failed"] += 1
            self._log(f"  [FAIL] {rel_path}: Python 语法错误 (行 {e.lineno}): {e.msg}")

            if not self.dry_run:
                dst_file = self.out_dir / rel_path
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            result["parse_error"] = str(e)
            result["parse_error_type"] = type(e).__name__
            self.stats["failed"] += 1
            self._log(f"  [FAIL] {rel_path}: {e}")

            if not self.dry_run:
                dst_file = self.out_dir / rel_path
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)

        self.file_results.append(result)

    def _copy_file(self, src_file: Path, rel_path: Path):
        """复制非 Python 文件"""
        if self.dry_run:
            self._log(f"  [COPY] {rel_path}")
            self.stats["copied_files"] += 1
            return

        dst_file = self.out_dir / rel_path
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        self.stats["copied_files"] += 1
        self._log(f"  [COPY] {rel_path}")

    # ---------- Import 分析 ----------

    def _analyze_imports(self, py_code: str, rel_path: str):
        """分析单个文件的 import 语句"""
        try:
            tree = ast.parse(py_code)
        except SyntaxError:
            return

        analyzer = ImportAnalyzer(rel_path, self.local_module_names)
        analyzer.visit(tree)

        for entry in analyzer.local_imports:
            mod = entry.get("module", "")
            if mod:
                self.all_imports["local"][mod].append(rel_path)
        for entry in analyzer.stdlib_imports:
            mod = entry.get("module", "")
            if mod:
                self.all_imports["stdlib"][mod].append(rel_path)
        for entry in analyzer.thirdparty_imports:
            mod = entry.get("module", "")
            if mod:
                self.all_imports["thirdparty"][mod].append(rel_path)

    # ---------- Import 路径重写 ----------

    def _rewrite_imports(self, light_code: str, rel_path: Path) -> str:
        """重写光明代码中的 import 语句，使其兼容光明解析器。

        光明的"从 X.Y 导入 Z"不支持模块路径中的点号。
        光明的"导入 X.Y"也不支持（点号被当语句分隔）。

        策略：对带点号的 import，用特殊注释保留原始 Python import，
        build.py 编译后会恢复这些 import 语句。

        注释格式: # @import: from X.Y import Z
                  # @import: import X.Y as Z
        """
        import re

        lines = light_code.split("\n")
        rewritten = []

        for line in lines:
            # 匹配: 从 X.Y.Z 导入 name1, name2 [为 alias]
            m = re.match(r'^(\s*)从\s+(\S+)\s+导入\s+(.+)$', line)
            if m:
                indent, module_path, names = m.groups()
                if "." in module_path:
                    # 带点号 -> 注释保留原始 Python from...import
                    # 还原 Python 语法
                    py_names = names.replace(" 为 ", " as ")
                    rewritten.append(f"{indent}# @import: from {module_path} import {py_names}")
                    continue

            # 匹配: 导入 X.Y.Z [为 alias]
            m2 = re.match(r'^(\s*)导入\s+(\S+?)(\s+为\s+(.+))?$', line)
            if m2:
                indent, module_path, _as, alias = m2.groups()
                if "." in module_path:
                    # 带点号 -> 注释保留原始 Python import
                    if alias:
                        rewritten.append(f"{indent}# @import: import {module_path} as {alias}")
                    else:
                        rewritten.append(f"{indent}# @import: import {module_path}")
                    continue

            rewritten.append(line)

        return "\n".join(rewritten)

    # ---------- 光明解析器验证 ----------

    def _validate_light(self, light_code: str) -> dict:
        """用光明解析器验证 .light 代码是否能成功解析

        Returns:
            dict with keys:
                success: bool
                error: str or None (error message)
                error_type: str or None (type of error)
                lineno: int or None (line number of error)
        """
        try:
            src_dir = Path(_SCRIPT_DIR).parent.parent / "src"
            if str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))

            from light_parser_v3 import LightParser
            parser = LightParser()
            module = parser.parse(light_code)
            if module is not None:
                return {"success": True, "error": None, "error_type": None, "lineno": None}
            else:
                return {"success": False, "error": "解析返回空模块", "error_type": "ParseError", "lineno": None}
        except Exception as e:
            error_msg = str(e)
            # 尝试提取行号
            lineno = None
            error_type = type(e).__name__
            # 从错误信息中提取行号
            import re
            m = re.search(r'[线行]\s*(\d+)', error_msg)
            if m:
                lineno = int(m.group(1))
            return {"success": False, "error": error_msg, "error_type": error_type, "lineno": lineno}

    # ---------- 生成 light.json ----------

    def _generate_light_json(self):
        """生成项目清单 light.json"""
        light_files = []
        for r in self.file_results:
            if r["status"] == "transpiled":
                light_files.append({
                    "light": r["dst"],
                    "original_py": r["src"],
                    "parse_validated": r["parse_ok"],
                })

        manifest = {
            "project_name": self.src_dir.name,
            "transpiled_at": datetime.now().isoformat(),
            "source_dir": str(self.src_dir),
            "output_dir": str(self.out_dir),
            "stats": self.stats,
            "feature_stats": dict(self.feature_stats),
            "light_files": light_files,
            "imports": {
                "local": {k: v for k, v in sorted(self.all_imports["local"].items())},
                "stdlib": {k: v for k, v in sorted(self.all_imports["stdlib"].items())},
                "thirdparty": {k: v for k, v in sorted(self.all_imports["thirdparty"].items())},
            },
            "local_modules": sorted(self.local_module_names),
        }

        json_path = self.out_dir / "light.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        self._log(f"生成项目清单: {json_path}")

    # ---------- 生成转译报告 ----------

    def _generate_report(self):
        """生成 CONVERSION_REPORT.md"""
        lines = []
        lines.append("# Python -> 光明 项目转译报告\n")
        lines.append(f"- **源项目**: `{self.src_dir}`")
        lines.append(f"- **输出目录**: `{self.out_dir}`")
        lines.append(f"- **转译时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 统计摘要
        lines.append("## 统计摘要\n")
        lines.append(f"| 指标 | 数量 |")
        lines.append(f"|------|------|")
        lines.append(f"| Python 文件总数 | {self.stats['total_py_files']} |")
        lines.append(f"| 成功转译 | {self.stats['transpiled']} |")
        lines.append(f"| 转译失败 | {self.stats['failed']} |")
        lines.append(f"| 解析验证通过 | {self.stats['parse_validated']} |")
        lines.append(f"| 解析验证失败 | {self.stats['parse_failed']} |")
        lines.append(f"| 复制非 Python 文件 | {self.stats['copied_files']} |")
        success_rate = 0
        if self.stats["total_py_files"] > 0:
            success_rate = self.stats["transpiled"] / self.stats["total_py_files"] * 100
        lines.append(f"| 转译成功率 | {success_rate:.1f}% |")
        lines.append("")

        # Python 特性使用统计
        lines.append("## Python 特性使用统计\n")
        if self.feature_stats:
            lines.append("| 特性 | 使用次数 | 光明支持情况 |")
            lines.append("|------|---------|-------------|")
            support_map = {
                "match_case": "✅ 支持 (匹配...情况)",
                "async_await": "✅ 支持 (异步 函数/等待)",
                "decorator": "✅ 支持 (标注)",
                "type_annotation": "⚠️ 不支持 (已忽略)",
                "lambda": "✅ 支持 (接收...返回...)",
                "generator": "✅ 支持 (产出)",
                "list_comp": "✅ 支持 ([...遍历...])",
                "dict_comp": "✅ 支持 ({...遍历...})",
                "set_comp": "✅ 支持 ({...遍历...})",
                "generator_expr": "⚠️ 部分支持",
                "fstring": "⚠️ 部分支持 (转普通字符串)",
                "star_import": "⚠️ 不支持 (逐名导入)",
                "relative_import": "⚠️ 部分支持",
                "named_expr": "❌ 不支持 (改用赋值)",
                "exception_chain": "⚠️ 部分支持",
                "class": "✅ 支持 (类)",
                "dataclass": "⚠️ 部分支持",
                "property": "✅ 支持 (特性)",
                "staticmethod": "✅ 支持 (静态)",
                "classmethod": "✅ 支持 (类方法)",
                "with": "✅ 支持 (使用)",
                "try_except": "✅ 支持 (尝试/捕获)",
            }
            for feat_key in sorted(self.feature_stats.keys()):
                label = FeatureUsageCollector.FEATURE_CATEGORIES.get(feat_key, feat_key)
                count = self.feature_stats[feat_key]
                support = support_map.get(feat_key, "⚠️ 未知")
                lines.append(f"| {label} | {count} | {support} |")
        else:
            lines.append("(未检测到特殊 Python 特性)\n")
        lines.append("")

        # 本地模块
        lines.append("## 本地模块\n")
        if self.local_module_names:
            lines.append(", ".join(f"`{m}`" for m in sorted(self.local_module_names)))
        else:
            lines.append("(未检测到)")
        lines.append("")

        # Import 分类
        for cat_name, cat_label in [("local", "本地模块"), ("stdlib", "标准库"), ("thirdparty", "第三方库")]:
            lines.append(f"## Import 分类 - {cat_label}\n")
            cat_imports = self.all_imports[cat_name]
            if cat_imports:
                lines.append("| 模块 | 引用文件数 |")
                lines.append("|------|-----------|")
                for mod, files in sorted(cat_imports.items()):
                    lines.append(f"| `{mod}` | {len(set(files))} |")
            else:
                lines.append("(无)")
            lines.append("")

        # 文件级详情
        lines.append("## 文件转译详情\n")
        lines.append("| 源文件 | 光明文件 | 状态 | 解析验证 |")
        lines.append("|--------|----------|------|---------|")
        for r in self.file_results:
            status_icon = {"transpiled": "OK", "failed": "FAIL"}.get(r["status"], r["status"])
            parse_icon = "-"
            if r["parse_ok"] is True:
                parse_icon = "PASS"
            elif r["parse_ok"] is False:
                parse_icon = "FAIL"
            lines.append(f"| `{r['src']}` | `{r['dst']}` | {status_icon} | {parse_icon} |")
        lines.append("")

        # 失败详情（含源码行）
        failed = [r for r in self.file_results if r["status"] == "failed"]
        parse_failed = [r for r in self.file_results if r["status"] == "transpiled" and not r["parse_ok"]]
        if failed or parse_failed:
            lines.append("## 失败详情\n")
            seq = 1
            for r in failed:
                lines.append(f"### {seq}. `{r['src']}` — 转译失败\n")
                lines.append(f"- **错误类型**: {r.get('parse_error_type', 'Unknown')}")
                if r.get("parse_lineno"):
                    lines.append(f"- **行号**: {r['parse_lineno']}")
                lines.append(f"- **错误信息**: {r['error']}")
                # 显示源码行
                if r.get("source_lines") and r.get("parse_lineno"):
                    lineno = r["parse_lineno"]
                    idx = lineno - 1
                    if 0 <= idx < len(r["source_lines"]):
                        lines.append(f"\n  ```python")
                        lines.append(f"  # {r['src']}:{lineno}")
                        lines.append(f"  {r['source_lines'][idx].rstrip()}")
                        lines.append(f"  ```")
                lines.append("")
                seq += 1

            for r in parse_failed:
                lines.append(f"### {seq}. `{r['src']}` — 解析验证失败\n")
                lines.append(f"- **错误类型**: {r.get('parse_error_type', 'ParseError')}")
                if r.get("parse_lineno"):
                    lines.append(f"- **行号**: {r['parse_lineno']}")
                if r.get("parse_error"):
                    err_msg = r["parse_error"][:200]
                    if len(r["parse_error"]) > 200:
                        err_msg += "..."
                    lines.append(f"- **错误信息**: {err_msg}")
                # 显示源码行上下文
                if r.get("source_lines") and r.get("parse_lineno"):
                    lineno = r["parse_lineno"]
                    idx = lineno - 1
                    if 0 <= idx < len(r["source_lines"]):
                        start = max(0, idx - 1)
                        end = min(len(r["source_lines"]), idx + 2)
                        lines.append(f"\n  ```python")
                        lines.append(f"  # {r['src']} (行 {lineno} 附近)")
                        for i in range(start, end):
                            prefix = "  →" if i == idx else "   "
                            lines.append(f"  {prefix} {r['source_lines'][i].rstrip()}")
                        lines.append(f"  ```")
                lines.append("")
                seq += 1

        # 修复建议
        total_issues = len(failed) + len(parse_failed)
        if total_issues > 0:
            lines.append("## 修复建议\n")
            lines.append(f"发现 {total_issues} 个问题文件需要处理。\n")

            # 根据特性统计生成建议
            active_suggestions = set()
            for feat_key in self.feature_stats:
                if feat_key in self._suggestion_rules:
                    active_suggestions.add(self._suggestion_rules[feat_key])

            # 根据失败类型生成建议
            for r in failed:
                err_type = r.get("parse_error_type", "")
                if "TranspileError" in err_type:
                    active_suggestions.add(
                        "转译错误：某些 Python 语法光明不支持。请检查错误信息并手动修复对应代码。"
                    )

            for r in parse_failed:
                err_type = r.get("parse_error_type", "")
                if "ParseError" in err_type:
                    active_suggestions.add(
                        "解析错误：转译后的光明代码无法被光明解析器解析。"
                        "常见原因：链式调用不完整、装饰器语法不兼容、import 路径包含点号。"
                    )

            if active_suggestions:
                lines.append("### 建议列表\n")
                for i, suggestion in enumerate(sorted(active_suggestions), 1):
                    lines.append(f"{i}. {suggestion}")

            lines.append("")
            lines.append(f"### 手动修复步骤\n")
            lines.append("1. 查看上方的失败详情，定位具体文件和行号")
            lines.append("2. 对照原始 Python 源码和转译后的光明代码，找出差异")
            lines.append("3. 手动编辑 `.light` 文件修复问题")
            lines.append("4. 运行 `python -m light_parser_v3 <file>.light` 验证修复")
            lines.append("")

        # 使用说明
        lines.append("## 使用说明\n")
        lines.append("### 编译运行\n")
        lines.append("```bash")
        lines.append("# 方法 1: 使用 build.py 一键编译")
        lines.append("python build.py")
        lines.append("")
        lines.append("# 方法 2: 使用光明 CLI 逐文件编译")
        lines.append("light compile main.light -o main.py")
        lines.append("python main.py")
        lines.append("```")
        lines.append("")
        lines.append("### 注意事项\n")
        lines.append("- 第三方库 import 保持原样，运行时需要 `pip install` 对应的包")
        lines.append("- 转译失败的文件已保留原始 .py 文件作为 fallback")
        lines.append("- `build.py` 会将所有 .light 文件编译为 .py 并保留目录结构")

        report_path = self.out_dir / "CONVERSION_REPORT.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        self._log(f"生成转译报告: {report_path}")

    # ---------- 生成 build.py ----------

    def _generate_build_script(self):
        """生成 build.py 构建脚本"""
        # 确定 light CLI 路径
        project_root = Path(_SCRIPT_DIR).parent.parent
        light_cli = project_root / "cli" / "light.py"

        build_code = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py - 光明项目构建脚本
将项目中所有 .light 文件编译为 .py 文件，保留目录结构。

用法:
    python build.py              # 编译所有 .light 文件
    python build.py --run <file> # 编译并运行指定文件
    python build.py --clean      # 清理编译产物
"""
import os
import sys
import json
import shutil
import argparse
from pathlib import Path

# 光明项目根目录
LIGHT_PROJECT_ROOT = r"{project_root}"
SRC_DIR = os.path.join(LIGHT_PROJECT_ROOT, "src")
CLI_DIR = os.path.join(LIGHT_PROJECT_ROOT, "cli")

# 确保 import 路径
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, CLI_DIR)
sys.path.insert(0, LIGHT_PROJECT_ROOT)

# 当前光明项目目录（即 build.py 所在目录）
PROJECT_DIR = Path(__file__).parent.resolve()


def compile_light_to_py(light_path: Path, py_path: Path = None) -> bool:
    """编译单个 .light 文件为 .py 文件"""
    if py_path is None:
        py_path = light_path.with_suffix(".py")

    try:
        with open(light_path, "r", encoding="utf-8") as f:
            source = f.read()

        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator

        parser = LightParser()
        module = parser.parse(source)
        if module is None:
            print(f"  [FAIL] {{light_path}}: 解析失败")
            return False

        generator = PythonCodeGenerator()
        py_code = generator.generate(module)

        # 后处理：恢复 @import 注释为真正的 Python import 语句
        py_code = _restore_imports(py_code, source)

        # 后处理：恢复光明内置函数名为 Python 原名
        py_code = _restore_builtins(py_code)

        py_path.parent.mkdir(parents=True, exist_ok=True)
        with open(py_path, "w", encoding="utf-8") as f:
            f.write(py_code)

        print(f"  [OK] {{light_path}} -> {{py_path}}")
        return True

    except Exception as e:
        print(f"  [FAIL] {{light_path}}: {{e}}")
        return False


def _restore_imports(py_code: str, light_source: str) -> str:
    """从 .light 源码中提取 @import 注释，注入到生成的 .py 代码中。

    光明编译器在解析时会丢弃注释行，所以 @import 注释不会出现在 .py 中。
    本函数从 .light 源文件提取这些注释，转为 Python import 语句，
    插入到 .py 代码的用户代码区域开头。
    """
    import re

    # 从 .light 源码提取 @import 行
    import_lines = []
    for line in light_source.split("\\n"):
        m = re.match(r'^\\s*# @import: (.+)$', line)
        if m:
            import_lines.append(m.group(1).strip())

    if not import_lines:
        return py_code

    # 在 .py 代码中找到用户代码区域的开头
    # 光明代码生成器在运行时前导代码之后输出用户代码
    # 找到最后一个 _light_assert 函数定义后的位置
    py_lines = py_code.split("\\n")
    insert_pos = None

    for i, line in enumerate(py_lines):
        if "_light_assert" in line and "def " in line:
            # 找到 _light_assert 函数结束位置
            j = i + 1
            while j < len(py_lines):
                if py_lines[j].strip() and not py_lines[j].startswith(" ") and not py_lines[j].startswith("\\t"):
                    break
                j += 1
            insert_pos = j
            break

    if insert_pos is None:
        # fallback: 插入到文件开头
        insert_pos = 0

    # 在插入位置添加 import 语句
    import_block = "\\n".join(import_lines)
    py_lines.insert(insert_pos, "")
    py_lines.insert(insert_pos + 1, import_block)

    return "\\n".join(py_lines)


# 光明内置函数名 -> Python 函数名映射
# 只包含光明代码生成器未正确映射回 Python 的函数
_LIGHT_BUILTIN_REVERSE = {{
    '求和': 'sum', '整数': 'int', '浮数': 'float', '串': 'str',
    '布尔': 'bool', '典': 'dict', '集': 'set', '类型': 'type',
    '绝对值': 'abs', '四舍五入': 'round', '最小': 'min', '最大': 'max',
    '任一': 'any', '所有': 'all', '实例检查': 'isinstance',
    '打包': 'zip', '筛选': 'filter', '映射': 'map',
    '排序': 'sorted', '反转': 'reversed', '列': 'list',
}}


def _restore_builtins(py_code: str) -> str:
    """将光明代码生成器遗留的中文内置函数名替换回 Python 原名。

    光明代码生成器对部分内置函数（如 求和->sum）没有做反向映射，
    导致生成的 .py 中出现 NameError。
    """
    import re

    for light_name, py_name in _LIGHT_BUILTIN_REVERSE.items():
        # 匹配: 函数名( 参数 -> py_name( 参数
        # 需要确保前面不是 . 或字母（避免替换方法名/变量名的一部分）
        py_code = re.sub(
            r'(?<![.\\w])' + light_name + r'\\(',
            py_name + '(',
            py_code
        )

    return py_code


def build_all():
    """编译项目中所有 .light 文件"""
    # 读取项目清单
    manifest_path = PROJECT_DIR / "light.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        light_files = [entry["light"] for entry in manifest.get("light_files", [])]
    else:
        # 退化为扫描目录
        light_files = [str(p.relative_to(PROJECT_DIR))
                      for p in PROJECT_DIR.rglob("*.light")
                      if "build" not in str(p)]

    if not light_files:
        print("未找到 .light 文件")
        return False

    print(f"开始编译 {{len(light_files)}} 个光明文件...")
    success = 0
    failed = 0

    for light_rel in light_files:
        light_path = PROJECT_DIR / light_rel
        py_path = light_path.with_suffix(".py")

        if not light_path.exists():
            print(f"  [SKIP] {{light_rel}}: 文件不存在")
            continue

        if compile_light_to_py(light_path, py_path):
            success += 1
        else:
            failed += 1

    print(f"\\n编译完成: {{success}} 成功, {{failed}} 失败")
    return failed == 0


def run_file(light_rel: str):
    """编译并运行指定光明文件"""
    light_path = PROJECT_DIR / light_rel
    if not light_path.exists():
        print(f"文件不存在: {{light_path}}")
        sys.exit(1)

    py_path = light_path.with_suffix(".py")
    print(f"编译 {{light_rel}} ...")
    if not compile_light_to_py(light_path, py_path):
        sys.exit(1)

    print(f"\\n运行 {{py_path.relative_to(PROJECT_DIR)}} ...")
    print("=" * 60)
    os.chdir(PROJECT_DIR)
    os.execv(sys.executable, [sys.executable, str(py_path)])


def clean():
    """清理编译产物（删除所有 .py 文件，保留 .light）"""
    count = 0
    for py_file in PROJECT_DIR.rglob("*.py"):
        if py_file.name == "build.py":
            continue
        py_file.unlink()
        count += 1
        print(f"  删除: {{py_file.relative_to(PROJECT_DIR)}}")
    print(f"\\n清理完成: 删除 {{count}} 个 .py 文件")


def main():
    parser = argparse.ArgumentParser(description="光明项目构建脚本")
    parser.add_argument("--run", metavar="FILE", help="编译并运行指定 .light 文件")
    parser.add_argument("--clean", action="store_true", help="清理编译产物")
    args = parser.parse_args()

    if args.clean:
        clean()
    elif args.run:
        run_file(args.run)
    else:
        build_all()


if __name__ == "__main__":
    main()
'''

        build_path = self.out_dir / "build.py"
        with open(build_path, "w", encoding="utf-8") as f:
            f.write(build_code)

        self._log(f"生成构建脚本: {build_path}")

    # ---------- 工具方法 ----------

    def _detect_encoding(self, filepath: Path) -> str:
        """检测文件编码"""
        import tokenize
        try:
            with open(filepath, "rb") as f:
                encoding = tokenize.detect_encoding(f.readline)[0]
            return encoding or "utf-8"
        except Exception:
            return "utf-8"

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    def _print_summary(self):
        """打印转译摘要"""
        print()
        print("=" * 60)
        print("Python -> 光明 项目转译完成")
        print("=" * 60)
        print(f"  源项目:     {self.src_dir}")
        print(f"  输出目录:   {self.out_dir}")
        print(f"  Python 文件: {self.stats['total_py_files']}")
        print(f"  成功转译:   {self.stats['transpiled']}")
        print(f"  转译失败:   {self.stats['failed']}")
        print(f"  解析验证:   {self.stats['parse_validated']} 通过 / {self.stats['parse_failed']} 失败")
        print(f"  复制文件:   {self.stats['copied_files']}")

        if self.stats["total_py_files"] > 0:
            rate = self.stats["transpiled"] / self.stats["total_py_files"] * 100
            print(f"  转译成功率: {rate:.1f}%")

        if self.dry_run:
            print("  (dry-run 模式，未实际写入文件)")
        else:
            print()
            print("  产物文件:")
            print(f"    - light.json (项目清单)")
            print(f"    - CONVERSION_REPORT.md (转译报告)")
            print(f"    - build.py (构建脚本)")
            print()
            print("  下一步:")
            print("    python build.py          # 编译 .light -> .py")
            print("    python build.py --run main.light  # 编译并运行")

        print("=" * 60)


# ==================== CLI 入口 ====================

def main():
    parser = argparse.ArgumentParser(
        prog="pyproject2light",
        description="Python 项目 -> 光明项目 批量转译器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python pyproject2light.py ./my_project -o ./my_light_project
  python pyproject2light.py ./my_project --dry-run --verbose
  python pyproject2light.py ./my_project -o ./output -v
        """,
    )
    parser.add_argument("src", help="Python 源项目目录")
    parser.add_argument("-o", "--output", default=None,
                        help="输出目录（默认: <源目录>_light）")
    parser.add_argument("--dry-run", action="store_true",
                        help="预览模式，不实际写入文件")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="详细输出")

    args = parser.parse_args()

    src_dir = args.src
    if not os.path.isdir(src_dir):
        print(f"错误: 源目录不存在: {src_dir}", file=sys.stderr)
        sys.exit(1)

    out_dir = args.output
    if out_dir is None:
        out_dir = str(Path(src_dir).resolve()) + "_light"

    transpiler = ProjectTranspiler(
        src_dir=src_dir,
        out_dir=out_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    transpiler.run()


if __name__ == "__main__":
    main()
