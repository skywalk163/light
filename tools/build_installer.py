#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
段言（DuanLang）一键安装包构建脚本

用法：
  python tools/build_installer.py                   # 自动检测当前平台并显示构建指导
  python tools/build_installer.py --platform win     # 指定平台构建（win / mac / linux）
  python tools/build_installer.py --validate         # 仅验证环境
  python tools/build_installer.py --all              # 构建所有平台（仅 CI 环境）

本脚本检测当前构建环境，输出构建指导，并可选执行构建步骤。
"""

import sys
import os
import platform
import subprocess
import argparse
import shutil
import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = Path(__file__).resolve().parent
INSTALLER_DIR = TOOLS_DIR / "installer"
OUTPUT_DIR = PROJECT_ROOT / "output"

# 段言元信息（与 pyproject.toml 保持一致）
DUAN_NAME = "duan"
DUAN_VERSION = "6.1.0"
DUAN_DISPLAY_NAME = "段言"
DUAN_MIN_PYTHON = (3, 10)
DUAN_ENTRY_POINTS = {
    "duan": "cli.duan_unified:main",
    "duanc": "cli.duanc:main",
}


def _print_header(title: str) -> None:
    """打印格式化标题"""
    line = "=" * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(f"{line}\n")


def _print_step(step: str, status: str, detail: str = "") -> None:
    """打印步骤状态"""
    status_map = {
        "ok": "  ✓",
        "fail": "  ✗",
        "warn": "  ⚠",
        "info": "  ·",
    }
    icon = status_map.get(status, "  ·")
    print(f"{icon} {step}")
    if detail:
        print(f"    {detail}")


def get_platform() -> str:
    """检测当前平台"""
    system = platform.system().lower()
    if system == "windows":
        return "win"
    elif system == "darwin":
        return "mac"
    elif system == "linux":
        return "linux"
    else:
        return system


def get_python_version() -> Tuple[int, int, int]:
    """获取当前 Python 版本"""
    v = sys.version_info
    return (v.major, v.minor, v.micro)


def check_python_version() -> bool:
    """检查 Python 版本是否满足最低要求"""
    current = get_python_version()[:2]
    if current >= DUAN_MIN_PYTHON:
        _print_step(
            f"Python 版本 {'.'.join(map(str, current))}",
            "ok",
            f"满足最低要求 {'.'.join(map(str, DUAN_MIN_PYTHON))}",
        )
        return True
    else:
        _print_step(
            f"Python 版本 {'.'.join(map(str, current))}",
            "fail",
            f"需要 >= {'.'.join(map(str, DUAN_MIN_PYTHON))}",
        )
        return False


def check_tools() -> Dict[str, bool]:
    """检查构建工具是否可用"""
    results = {}
    system = get_platform()

    if system == "win":
        # 检查 Inno Setup
        inno_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
            r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        ]
        iscc_found = any(os.path.exists(p) for p in inno_paths)
        if iscc_found:
            _print_step("Inno Setup (ISCC.exe)", "ok")
        else:
            _print_step("Inno Setup (ISCC.exe)", "warn", "未安装，请从 https://jrsoftware.org/ 下载")
        results["iscc"] = iscc_found

    elif system == "mac":
        # 检查 pkgbuild/productbuild
        for cmd in ["pkgbuild", "productbuild"]:
            found = shutil.which(cmd) is not None
            if found:
                _print_step(f"{cmd}", "ok")
            else:
                _print_step(f"{cmd}", "warn", "未找到，请安装 Xcode Command Line Tools")
            results[cmd] = found

    elif system == "linux":
        # 检查 dpkg-deb / rpmbuild / fpm
        for cmd in ["dpkg-deb", "rpmbuild", "fpm"]:
            found = shutil.which(cmd) is not None
            if found:
                _print_step(f"{cmd}", "ok")
            else:
                _print_step(f"{cmd}", "warn", f"未安装，可通过包管理器安装")
            results[cmd] = found

    # 通用工具
    has_pip = shutil.which("pip") is not None or shutil.which("pip3") is not None
    if has_pip:
        _print_step("pip", "ok")
    else:
        _print_step("pip", "warn", "未找到 pip，无法构建 wheel 包")
    results["pip"] = has_pip

    has_build = _is_package_installed("build")
    if has_build:
        _print_step("Python build 模块", "ok")
    else:
        _print_step("Python build 模块", "warn", "未安装，请执行: pip install build")
    results["build"] = has_build

    return results


def _is_package_installed(package_name: str) -> bool:
    """检查 Python 包是否已安装"""
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def build_wheel() -> Optional[Path]:
    """构建段言 wheel 包"""
    _print_step("构建段言 wheel 包", "info")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", str(PROJECT_ROOT)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            _print_step("wheel 构建失败", "fail", result.stderr)
            return None

        # 查找 wheel 文件
        dist_dir = PROJECT_ROOT / "dist"
        if not dist_dir.exists():
            _print_step("dist 目录不存在", "fail")
            return None

        wheels = list(dist_dir.glob("*.whl"))
        if not wheels:
            _print_step("未找到 wheel 文件", "fail")
            return None

        wheel_path = wheels[0]
        _print_step("wheel 构建成功", "ok", str(wheel_path))
        return wheel_path

    except FileNotFoundError as e:
        _print_step("wheel 构建失败", "fail", f"命令未找到: {e}")
        return None


def validate_environment() -> bool:
    """验证当前构建环境"""
    _print_header("环境验证")
    success = True

    # 1. 检查 Python 版本
    _print_step("检查 Python 版本", "info")
    if not check_python_version():
        success = False

    # 2. 检查构建工具
    _print_step("检查构建工具", "info")
    tools = check_tools()

    # 3. 检查项目结构
    _print_step("检查项目结构", "info")
    pyproject = PROJECT_ROOT / "pyproject.toml"
    if pyproject.exists():
        _print_step("pyproject.toml", "ok")
    else:
        _print_step("pyproject.toml", "fail", "项目根目录下未找到 pyproject.toml")
        success = False

    src_dir = PROJECT_ROOT / "src"
    if src_dir.exists():
        _print_step("src/", "ok")
    else:
        _print_step("src/", "fail", "未找到源码目录")
        success = False

    cli_dir = PROJECT_ROOT / "cli"
    if cli_dir.exists():
        _print_step("cli/", "ok")
    else:
        _print_step("cli/", "fail", "未找到 CLI 入口目录")
        success = False

    # 4. 检查 Python 嵌入式发行版（Windows）
    if get_platform() == "win":
        _print_step("检查 Python 嵌入式发行版", "info")
        embed_python = INSTALLER_DIR / "windows" / "python-3.10.xx-embed-amd64.zip"
        # 允许用户自行下载，仅检查目录是否存在
        _print_step("Python 嵌入式发行版", "warn", "请手动下载至 tools/installer/windows/")

    print()
    if success:
        _print_step("环境验证通过", "ok")
    else:
        _print_step("环境验证未通过", "fail", "请修复上述问题后重试")

    return success


def build_windows_installer(wheel_path: Optional[Path] = None) -> bool:
    """构建 Windows 安装包"""
    _print_header("Windows 安装包构建")

    # 1. 构建 wheel
    if wheel_path is None:
        wheel_path = build_wheel()
    if wheel_path is None:
        return False

    # 2. 检查 Inno Setup 脚本
    iss_path = INSTALLER_DIR / "windows" / "setup.iss"
    if not iss_path.exists():
        _print_step("Inno Setup 脚本", "fail", f"未找到: {iss_path}")
        _print_step("请先创建 setup.iss 文件", "info")
        return False

    # 3. 检查 Python 嵌入式发行版
    embed_python_dir = INSTALLER_DIR / "windows"
    zip_files = list(embed_python_dir.glob("python-*-embed-amd64.zip"))
    if not zip_files:
        _print_step("Python 嵌入式发行版", "warn", "未找到，请从 python.org 下载")
        _print_step("下载地址: https://www.python.org/downloads/windows/", "info")
        _print_step("下载后请放置到: tools/installer/windows/", "info")

    # 4. 检查 ISCC
    iscc_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    iscc = None
    for p in iscc_paths:
        if os.path.exists(p):
            iscc = p
            break

    if iscc is None:
        _print_step("Inno Setup 未安装", "fail")
        _print_step("请从 https://jrsoftware.org/ 下载安装 Inno Setup 6", "info")
        return False

    # 5. 执行构建
    output_dir = OUTPUT_DIR / "windows"
    output_dir.mkdir(parents=True, exist_ok=True)

    _print_step("执行 Inno Setup 编译...", "info")
    try:
        result = subprocess.run(
            [iscc, str(iss_path)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            _print_step("Windows 安装包构建成功", "ok", str(output_dir))
            return True
        else:
            _print_step("Windows 安装包构建失败", "fail", result.stderr)
            return False
    except FileNotFoundError:
        _print_step("ISCC.exe 未找到", "fail")
        return False


def build_macos_installer(wheel_path: Optional[Path] = None) -> bool:
    """构建 macOS 安装包"""
    _print_header("macOS 安装包构建")

    # 1. 构建 wheel
    if wheel_path is None:
        wheel_path = build_wheel()
    if wheel_path is None:
        return False

    # 2. 检查 pkgbuild 工具
    if shutil.which("pkgbuild") is None:
        _print_step("pkgbuild 未找到", "fail", "请安装 Xcode Command Line Tools")
        _print_step("安装命令: xcode-select --install", "info")
        return False

    # 3. 检查构建脚本
    build_script = INSTALLER_DIR / "macos" / "build_pkg.sh"
    if not build_script.exists():
        _print_step("macOS 构建脚本", "fail", f"未找到: {build_script}")
        _print_step("请先创建 tools/installer/macos/build_pkg.sh", "info")
        return False

    # 4. 执行构建
    output_dir = OUTPUT_DIR / "macos"
    output_dir.mkdir(parents=True, exist_ok=True)

    _print_step("执行 macOS 安装包构建...", "info")
    try:
        result = subprocess.run(
            ["bash", str(build_script)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            _print_step("macOS 安装包构建成功", "ok", str(output_dir))
            return True
        else:
            _print_step("macOS 安装包构建失败", "fail", result.stderr)
            return False
    except FileNotFoundError:
        _print_step("bash 未找到", "fail")
        return False


def build_linux_installer(wheel_path: Optional[Path] = None, pkg_type: str = "deb") -> bool:
    """构建 Linux 安装包"""
    _print_header(f"Linux {pkg_type.upper()} 安装包构建")

    # 1. 构建 wheel
    if wheel_path is None:
        wheel_path = build_wheel()
    if wheel_path is None:
        return False

    # 2. 检查构建工具
    if pkg_type == "deb":
        if shutil.which("dpkg-deb") is None:
            _print_step("dpkg-deb 未找到", "fail", "请安装 dpkg-dev")
            _print_step("安装命令: sudo apt install dpkg-dev", "info")
            return False
    elif pkg_type == "rpm":
        if shutil.which("rpmbuild") is None:
            _print_step("rpmbuild 未找到", "fail", "请安装 rpm-build")
            _print_step("安装命令: sudo dnf install rpm-build", "info")
            return False

    # 3. 检查构建脚本
    build_script = INSTALLER_DIR / "linux" / f"build_{pkg_type}.sh"
    if not build_script.exists():
        _print_step(f"Linux {pkg_type.upper()} 构建脚本", "fail", f"未找到: {build_script}")
        _print_step(f"请先创建 tools/installer/linux/build_{pkg_type}.sh", "info")
        return False

    # 4. 执行构建
    output_dir = OUTPUT_DIR / "linux"
    output_dir.mkdir(parents=True, exist_ok=True)

    _print_step(f"执行 Linux {pkg_type.upper()} 安装包构建...", "info")
    try:
        result = subprocess.run(
            ["bash", str(build_script)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            _print_step(f"Linux {pkg_type.upper()} 安装包构建成功", "ok", str(output_dir))
            return True
        else:
            _print_step(f"Linux {pkg_type.upper()} 安装包构建失败", "fail", result.stderr)
            return False
    except FileNotFoundError:
        _print_step("bash 未找到", "fail")
        return False


def show_build_instructions(target_platform: str) -> None:
    """显示构建指导"""
    instructions = {
        "win": {
            "title": "Windows 安装包构建指导",
            "steps": [
                ("1. 安装 Python 3.10+", "从 https://www.python.org/downloads/ 下载安装"),
                ("2. 安装构建工具", "pip install build"),
                ("3. 下载 Python 嵌入式发行版",
                 "从 https://www.python.org/downloads/windows/ 下载 python-3.10.x-embed-amd64.zip\n"
                 "   放置到 tools/installer/windows/ 目录"),
                ("4. 安装 Inno Setup 6", "从 https://jrsoftware.org/ 下载安装"),
                ("5. 创建 Inno Setup 脚本",
                 "创建 tools/installer/windows/setup.iss（参考设计文档）"),
                ("6. 构建 Wheel 包", "python -m build --wheel"),
                ("7. 编译安装包", f"python {Path(__file__).name} --platform win"),
            ],
        },
        "mac": {
            "title": "macOS 安装包构建指导",
            "steps": [
                ("1. 安装 Python 3.10+", "从 https://www.python.org/downloads/ 下载安装"),
                ("2. 安装构建工具", "pip install build"),
                ("3. 安装 Xcode Command Line Tools", "xcode-select --install"),
                ("4. 创建 macOS 构建脚本",
                 "创建 tools/installer/macos/build_pkg.sh（参考设计文档）"),
                ("5. 准备图标资源",
                 "创建 tools/installer/macos/Resources/duan.icns"),
                ("6. 构建 Wheel 包", "python -m build --wheel"),
                ("7. 构建安装包", f"python {Path(__file__).name} --platform mac"),
            ],
        },
        "linux": {
            "title": "Linux 安装包构建指导",
            "steps": [
                ("1. 安装 Python 3.10+", "从 https://www.python.org/downloads/ 下载安装"),
                ("2. 安装构建工具", "pip install build"),
                ("3. 安装 dpkg-dev（Debian/Ubuntu）", "sudo apt install dpkg-dev"),
                ("  或 rpm-build（Fedora/RHEL）", "sudo dnf install rpm-build"),
                ("4. 创建 Linux 构建脚本",
                 "创建 tools/installer/linux/build_deb.sh（参考设计文档）"),
                ("5. 构建 Wheel 包", "python -m build --wheel"),
                ("6. 构建 .deb 包", f"python {Path(__file__).name} --platform linux"),
            ],
        },
    }

    info = instructions.get(target_platform, instructions["win"])
    _print_header(info["title"])
    for step_name, step_detail in info["steps"]:
        _print_step(step_name, "info", step_detail)
    print()


def show_platform_info() -> None:
    """显示当前平台信息"""
    _print_header("平台信息")
    _print_step("操作系统", "info", f"{platform.system()} {platform.release()}")
    _print_step("架构", "info", platform.machine())
    _print_step("Python 版本", "info", f"{sys.version}")
    _print_step("项目版本", "info", f"{DUAN_DISPLAY_NAME} v{DUAN_VERSION}")
    _print_step("项目路径", "info", str(PROJECT_ROOT))
    print()


def main():
    parser = argparse.ArgumentParser(
        description=f"{DUAN_DISPLAY_NAME} v{DUAN_VERSION} 一键安装包构建脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python tools/build_installer.py                # 检测平台并显示构建指导
  python tools/build_installer.py --validate     # 仅验证环境
  python tools/build_installer.py --platform win # 构建 Windows 安装包
  python tools/build_installer.py --platform mac # 构建 macOS 安装包
  python tools/build_installer.py --platform linux # 构建 Linux 安装包
  python tools/build_installer.py --all          # 构建所有平台（CI 环境）
        """,
    )

    parser.add_argument(
        "--platform",
        choices=["win", "mac", "linux", "auto"],
        default="auto",
        help="目标平台（默认: 自动检测当前平台）",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="仅验证环境，不执行构建",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="构建所有平台（仅 CI 环境使用）",
    )
    parser.add_argument(
        "--wheel",
        type=str,
        default=None,
        help="指定 wheel 文件路径（默认: 自动构建）",
    )

    args = parser.parse_args()

    # 显示启动信息
    _print_header(f"{DUAN_DISPLAY_NAME} 一键安装包构建工具 v1.0")
    print(f"  项目: {DUAN_DISPLAY_NAME} v{DUAN_VERSION}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  平台: {platform.system()} {platform.release()} ({platform.machine()})")
    print()

    # 确定目标平台
    target = args.platform
    if target == "auto":
        target = get_platform()
        _print_step(f"自动检测平台: {target}", "info")
        print()

    # 解析 wheel 路径
    wheel_path = None
    if args.wheel:
        wheel_path = Path(args.wheel)
        if not wheel_path.exists():
            _print_step(f"指定的 wheel 文件不存在: {wheel_path}", "fail")
            return 1
        _print_step("使用指定的 wheel 文件", "ok", str(wheel_path))

    # --validate 模式
    if args.validate:
        validate_environment()
        return 0

    # --all 模式（CI/CD）
    if args.all:
        _print_header("全平台安装包构建")
        # 先构建 wheel
        wheel_path = build_wheel()
        if wheel_path is None:
            return 1

        results = {}
        results["windows"] = build_windows_installer(wheel_path)
        results["macos"] = build_macos_installer(wheel_path)
        results["linux-deb"] = build_linux_installer(wheel_path, "deb")

        _print_header("构建结果汇总")
        all_ok = True
        for platform_name, ok in results.items():
            status = "✓" if ok else "✗"
            print(f"  [{status}] {platform_name}")
            if not ok:
                all_ok = False
        print()
        return 0 if all_ok else 1

    # 单平台构建
    wheel_built = False
    if target == "win":
        show_platform_info()
        wheel_path = build_wheel()
        if wheel_path is None:
            return 1
        wheel_built = True
        build_windows_installer(wheel_path)

    elif target == "mac":
        show_platform_info()
        wheel_path = build_wheel()
        if wheel_path is None:
            return 1
        wheel_built = True
        build_macos_installer(wheel_path)

    elif target == "linux":
        show_platform_info()
        wheel_path = build_wheel()
        if wheel_path is None:
            return 1
        wheel_built = True
        # 优先构建 .deb
        build_linux_installer(wheel_path, "deb")

    else:
        # 未知平台：显示构建指导
        show_build_instructions(target)

    return 0


if __name__ == "__main__":
    sys.exit(main())