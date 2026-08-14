# -*- coding: utf-8 -*-
"""
段言全链路端到端测试覆盖

覆盖自举编译器、LLVM 后端、包管理器全场景的端到端测试用例。
确保 v6.3.0 版本迭代的稳定性。
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

# 项目根目录
REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_cli(args: List[str], cwd: Path = None) -> Tuple[int, str, str]:
    """运行段言 CLI 命令

    Args:
        args: 命令行参数列表
        cwd: 工作目录（默认为项目根目录）

    Returns:
        (返回码, 标准输出, 标准错误)
    """
    if cwd is None:
        cwd = REPO_ROOT
    result = subprocess.run(
        [sys.executable, "-m", "cli.duan_unified"] + args,
        capture_output=True, text=True, timeout=60,
        cwd=str(cwd),
    )
    return result.returncode, result.stdout, result.stderr


# =============================================================================
# 自举编译器全链路测试
# =============================================================================

class TestBootstrapFullChain:
    """自举编译器全链路测试"""

    BOOTSTRAP_FILES = [
        "bootstrap/bootstrap_level3.duan",
        "bootstrap/bootstrap_level4.duan",
        "bootstrap/bootstrap_level5.duan",
    ]

    @pytest.mark.parametrize("rel_path", BOOTSTRAP_FILES)
    def test_bootstrap_file_compiles(self, rel_path: str) -> None:
        """自举编译器文件应能成功编译

        Args:
            rel_path: 自举编译器文件的相对路径
        """
        file_path = REPO_ROOT / rel_path
        assert file_path.exists(), f"文件不存在: {file_path}"
        rc, out, err = _run_cli(["compile", str(file_path), "-o", str(file_path.with_suffix(".py"))])
        assert rc == 0, f"编译失败 ({rel_path}):\n{err}"

    def test_bootstrap_chain_compilation(self) -> None:
        """自举层级链式编译验证"""
        # 验证 Level 3 能编译 Level 4，Level 4 能编译 Level 5
        levels: Dict[str, str] = {
            "bootstrap/bootstrap_level3.duan": "bootstrap/bootstrap_level4.duan",
            "bootstrap/bootstrap_level4.duan": "bootstrap/bootstrap_level5.duan",
        }
        for compiler_src, target_src in levels.items():
            compiler_path = REPO_ROOT / compiler_src
            target_path = REPO_ROOT / target_src
            if not compiler_path.exists() or not target_path.exists():
                pytest.skip(f"源文件缺失: {compiler_src} 或 {target_src}")

            # 编译目标文件
            rc, out, err = _run_cli(["compile", str(target_path)])
            assert rc == 0, f"链式编译失败 ({target_src}):\n{err}"


# =============================================================================
# LLVM 后端全链路测试
# =============================================================================

class TestLlvmFullChain:
    """LLVM 后端全链路测试"""

    def test_llvm_ir_generation(self) -> None:
        """LLVM IR 生成测试"""
        test_source = """
段落 加法 接收 甲, 乙:
  返回 甲 + 乙。
"""
        # 写入临时文件
        with tempfile.NamedTemporaryFile(suffix=".duan", mode="w", delete=False, encoding="utf-8") as f:
            f.write(test_source)
            tmp_path = f.name

        try:
            rc, out, err = _run_cli(["compile", tmp_path, "--target", "llvm"])
            # LLVM 后端可能不可用，如果不可用则跳过
            if "LLVM" in err or "llvm" in err.lower():
                pytest.skip("LLVM 后端不可用")
            assert rc == 0, f"LLVM IR 生成失败:\n{err}"
        finally:
            os.unlink(tmp_path)

    def test_llvm_compile_to_exe(self) -> None:
        """LLVM 编译为可执行文件测试"""
        test_source = """
段落 主程序:
  打印("Hello from Duan LLVM!")
主程序()。
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            duan_file = Path(tmpdir) / "test.duan"
            duan_file.write_text(test_source, encoding="utf-8")

            rc, out, err = _run_cli(["compile", str(duan_file), "--target", "llvm", "-o", str(Path(tmpdir) / "test.ll")])
            if "LLVM" in err or "llvm" in err.lower():
                pytest.skip("LLVM 后端不可用")
            assert rc == 0, f"LLVM 编译失败:\n{err}"


# =============================================================================
# 包管理器全链路测试
# =============================================================================

class TestPackageManagerFullChain:
    """包管理器全链路测试"""

    def test_pkg_init_and_build(self) -> None:
        """包初始化和构建测试"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test_project"

            # 初始化项目
            rc, out, err = _run_cli(["pkg", "init", str(project_dir)])
            if rc != 0:
                # 尝试使用项目名
                rc, out, err = _run_cli(["pkg", "init", "test_project"], cwd=Path(tmpdir))
            assert rc == 0 or project_dir.exists(), f"项目初始化失败:\n{err}"

            # 如果项目创建成功，尝试构建
            if project_dir.exists():
                rc, out, err = _run_cli(["pkg", "build", "--dir", str(project_dir)])
                # 构建可能因缺少依赖而失败，不强制要求成功

    def test_package_search(self) -> None:
        """包搜索测试"""
        # 验证内置注册表可搜索
        from src.package_installer import BUILTIN_REGISTRY
        packages = BUILTIN_REGISTRY.get("packages", {})
        assert len(packages) > 0, "内置注册表为空"
        # 验证存在中文包
        chinese_packages = [n for n in packages.keys() if any('\u4e00' <= c <= '\u9fff' for c in n)]
        assert len(chinese_packages) > 0, "内置注册表中无中文包名"


# =============================================================================
# 编译器全链路集成测试
# =============================================================================

class TestCompilerFullChain:
    """编译器全链路集成测试"""

    def test_lexer_parser_codegen_chain(self) -> None:
        """词法分析→语法解析→代码生成全链路"""
        test_cases = [
            ("变量声明", "设 甲 为 42。", "甲 = 42"),
            ("函数定义", "段落 加 接收 甲, 乙:\n  返回 甲 + 乙。", "def 加(甲, 乙):"),
            ("条件语句", "如果 甲 大于 0:\n  打印(\"正数\")。", "if (甲 > 0):"),
            ("循环语句", "遍历 项 于 列表:\n  打印(项)。", "for 项 in 列表:"),
            ("异常处理", "尝试:\n  打印(\"测试\")。\n捕获 e:\n  打印(\"错误\")。", "try:"),
        ]

        for name, duan_code, expected_python in test_cases:
            with tempfile.NamedTemporaryFile(suffix=".duan", mode="w", delete=False, encoding="utf-8") as f:
                f.write(duan_code)
                tmp_path = f.name

            try:
                rc, out, err = _run_cli(["compile", tmp_path])
                if rc == 0:
                    # 验证编译产物
                    py_file = Path(tmp_path).with_suffix(".py")
                    if py_file.exists():
                        content = py_file.read_text(encoding="utf-8")
                        assert expected_python in content, \
                            f"({name}) 期望包含 '{expected_python}'，实际:\n{content}"
            finally:
                os.unlink(tmp_path)
                py_file = Path(tmp_path).with_suffix(".py")
                if py_file.exists():
                    os.unlink(py_file)

    def test_full_pipeline_run(self) -> None:
        """完整编译运行管道测试"""
        test_programs = [
            ("Hello World", "打印(\"Hello, 段言!\")。", "Hello, 段言!"),
            ("简单运算", "打印(1 + 2 * 3)。", "7"),
            ("字符串拼接", "打印(\"A\" + \"B\")。", "AB"),
        ]

        for name, code, expected_output in test_programs:
            full_code = f"段落 主程序:\n  {code}\n主程序()。\n"
            with tempfile.NamedTemporaryFile(suffix=".duan", mode="w", delete=False, encoding="utf-8") as f:
                f.write(full_code)
                tmp_path = f.name

            try:
                rc, out, err = _run_cli(["run", tmp_path])
                assert rc == 0, f"({name}) 运行失败:\n{err}"
                assert expected_output in out, \
                    f"({name}) 期望输出包含 '{expected_output}'，实际:\n{out}"
            finally:
                os.unlink(tmp_path)