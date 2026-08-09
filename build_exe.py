#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明（Light）Level 7 编译器 - PyInstaller 跨平台构建脚本

在构建各平台原生可执行文件，无需交叉编译。
必须在本机平台上运行（Windows 上构建 .exe，Linux 上构建 ELF，macOS 上构建 Mach-O）。

用法：
    python build_exe.py             # 单文件模式（默认）
    python build_exe.py --onedir    # 目录模式（调试用）
    python build_exe.py --name mylight6  # 自定义输出名称
"""

import os
import sys
import platform
import shutil
import subprocess

# ── 项目路径 ──────────────────────────────────────────────────
_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
_BOOTSTRAP_DIR = os.path.join(_PROJECT_DIR, 'bootstrap')
_ENTRY_SCRIPT = os.path.join(_PROJECT_DIR, 'light6.py')
_DIST_DIR = os.path.join(_PROJECT_DIR, 'dist')
_BUILD_DIR = os.path.join(_PROJECT_DIR, 'build')


def _detect_platform():
    """检测当前平台，返回平台标识"""
    system = platform.system()
    if system == 'Windows':
        return 'windows'
    elif system == 'Linux':
        return 'linux'
    elif system == 'Darwin':
        return 'macos'
    else:
        return system.lower()


def _exe_name(base_name, platform_name):
    """根据平台生成可执行文件名"""
    if platform_name == 'windows':
        return f'{base_name}.exe'
    else:
        return base_name


def _add_data_separator(platform_name):
    """PyInstaller 的 --add-data 分隔符：Windows 用 ;，其他用 :"""
    return ';' if platform_name == 'windows' else ':'


def build_exe(onefile=True, output_name='light7'):
    """使用 PyInstaller 构建当前平台的可执行文件"""
    
    platform_name = _detect_platform()
    print(f"当前平台: {platform_name} ({platform.system()})")
    
    # 检查 PyInstaller 是否安装
    if not shutil.which('pyinstaller'):
        print("[错误] 未找到 PyInstaller，请先安装: pip install pyinstaller", file=sys.stderr)
        sys.exit(1)
    
    # 清理旧的构建产物
    for d in [_DIST_DIR, _BUILD_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
    
    # 构建命令
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        '--name', output_name,
        '--distpath', _DIST_DIR,
        '--workpath', _BUILD_DIR,
        '--specpath', _PROJECT_DIR,
    ]
    
    # 版本信息（仅 Windows 支持）
    if platform_name == 'windows':
        version_file = os.path.join(_PROJECT_DIR, 'file_version_info.txt')
        if os.path.exists(version_file):
            cmd.extend(['--version-file', version_file])
    
    # 隐藏导入：c_backend 在 light6.py 中动态导入，需显式声明
    cmd.extend(['--hidden-import', 'c_backend'])
    
    # 排除不需要的模块以减小体积
    cmd.extend(['--exclude-module', 'tkinter'])
    cmd.extend(['--exclude-module', 'unittest'])
    cmd.extend(['--exclude-module', 'email'])
    cmd.extend(['--exclude-module', 'http'])
    cmd.extend(['--exclude-module', 'xml'])
    
    # macos 额外排除一些不需要的框架
    if platform_name == 'macos':
        cmd.extend(['--exclude-module', 'tcl'])
        cmd.extend(['--exclude-module', 'tk'])
    
    if onefile:
        cmd.append('--onefile')
    else:
        cmd.append('--onedir')
    
    # 添加数据文件：bootstrap 目录
    # 格式: 不同平台分隔符不同
    sep = _add_data_separator(platform_name)
    cmd.extend(['--add-data', f'{_BOOTSTRAP_DIR}{sep}bootstrap'])
    
    # 入口脚本
    cmd.append(_ENTRY_SCRIPT)
    
    # ── 打印构建信息 ──
    print("=" * 60)
    print(f"光明 Level 7 编译器 - 跨平台构建")
    print(f"平台: {platform_name} ({platform.machine()})")
    print(f"Python: {sys.version}")
    print(f"模式: {'单文件 (onefile)' if onefile else '目录 (onedir)'}")
    print(f"输出: {_exe_name(output_name, platform_name)}")
    print("=" * 60)
    print()
    print(f"构建命令:")
    print(f"  {' '.join(cmd)}")
    print()
    
    # 执行构建
    result = subprocess.run(cmd, cwd=_PROJECT_DIR)
    
    if result.returncode == 0:
        print()
        print("=" * 60)
        print("✅ 构建成功!")
        print("=" * 60)
        
        out_name = _exe_name(output_name, platform_name)
        out_path = os.path.join(_DIST_DIR, out_name)
        
        if onefile and os.path.exists(out_path):
            size_mb = os.path.getsize(out_path) / (1024 * 1024)
            print(f"  可执行文件: {out_path}")
            print(f"  文件大小: {size_mb:.2f} MB")
        elif not onefile:
            dir_path = os.path.join(_DIST_DIR, output_name)
            print(f"  输出目录: {dir_path}")
        
        print()
        print("使用方法:")
        exe_display = os.path.join(_DIST_DIR, _exe_name(output_name, platform_name))
        print(f"  {exe_display} <文件.light>")
        print(f"  {exe_display} compile <文件.light>")
        print(f"  {exe_display} --help")
        print()
    else:
        print()
        print("❌ 构建失败!")
        sys.exit(1)


if __name__ == '__main__':
    # 解析命令行参数
    onefile = True
    output_name = 'light7'
    
    for arg in sys.argv[1:]:
        if arg == '--onedir':
            onefile = False
        elif arg.startswith('--name='):
            output_name = arg.split('=', 1)[1]
        elif arg == '--name' and len(sys.argv) > sys.argv.index(arg) + 1:
            # 已由 --name= 处理，忽略 --name value 形式
            pass
    
    # 处理 --name value 形式
    if '--name' in sys.argv:
        idx = sys.argv.index('--name')
        if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith('--'):
            output_name = sys.argv[idx + 1]
    
    build_exe(onefile=onefile, output_name=output_name)