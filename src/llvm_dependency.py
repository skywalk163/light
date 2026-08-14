"""
段言 LLVM 依赖管理模块

功能：
1. 检测系统是否已安装 LLVM/clang
2. 提供 LLVM 不可用时的降级策略
3. 自动下载预构建的 LLVM 二进制包
4. 与构建系统集成，按需自动下载
5. LLVM 路径检测辅助函数

设计原则：
- 零外部依赖（仅使用标准库）
- 跨平台支持（Windows / Linux / macOS）
- 幂等操作（多次调用安全）
- 详细的错误信息和修复建议
"""

import os
import sys
import subprocess
import platform
import tarfile
import zipfile
import shutil
import json
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, List, Tuple


# =============================================================================
# LLVM 版本与下载 URL 配置
# =============================================================================

# 支持的 LLVM 版本
LLVM_VERSION = "19.1.0"

# 各平台预构建下载 URL
LLVM_DOWNLOAD_URLS: Dict[str, str] = {
    'win32': f'https://github.com/llvm/llvm-project/releases/download/llvmorg-{LLVM_VERSION}/LLVM-{LLVM_VERSION}-win64.exe',
    'linux': f'https://github.com/llvm/llvm-project/releases/download/llvmorg-{LLVM_VERSION}/clang+llvm-{LLVM_VERSION}-x86_64-linux-gnu-ubuntu-18.04.tar.xz',
    'darwin': f'https://github.com/llvm/llvm-project/releases/download/llvmorg-{LLVM_VERSION}/clang+llvm-{LLVM_VERSION}-x86_64-apple-darwin.tar.xz',
}

# 各平台安装后 clang 相对路径
LLVM_CLANG_RELATIVE_PATHS: Dict[str, List[str]] = {
    'win32': [
        'LLVM/bin/clang.exe',
        'bin/clang.exe',
    ],
    'linux': [
        'bin/clang',
        'clang+llvm-*/bin/clang',
    ],
    'darwin': [
        'bin/clang',
        'clang+llvm-*/bin/clang',
    ],
}

# 内置 fallback 安装目录
FALLBACK_LLVM_DIRS = {
    'win32': [
        r'C:\Program Files\LLVM',
        r'C:\Program Files (x86)\LLVM',
        r'E:\Program Files\LLVM',
        r'D:\Program Files\LLVM',
        os.path.expanduser(r'~\AppData\Local\LLVM'),
    ],
    'linux': [
        '/usr/lib/llvm-19',
        '/usr/lib/llvm-18',
        '/usr/lib/llvm-17',
        '/usr/lib/llvm-16',
        '/usr/lib/llvm-14',
        '/usr/local/llvm',
        os.path.expanduser('~/.local/llvm'),
    ],
    'darwin': [
        '/usr/local/opt/llvm',
        '/opt/homebrew/opt/llvm',
        '/usr/local/Cellar/llvm',
        os.path.expanduser('~/.local/llvm'),
    ],
}


# =============================================================================
# LLVM 检测
# =============================================================================

def is_llvm_installed(clang_path: Optional[str] = None) -> bool:
    """检测 LLVM/clang 是否已安装

    Args:
        clang_path: 指定 clang 路径，None 表示自动检测

    Returns:
        True 表示 clang 可用
    """
    if clang_path:
        return os.path.exists(clang_path) and _is_executable(clang_path)

    try:
        path = find_clang()
        return path is not None
    except RuntimeError:
        return False


def _is_executable(file_path: str) -> bool:
    """检查文件是否为可执行文件"""
    if not os.path.isfile(file_path):
        return False
    if sys.platform == 'win32':
        return file_path.endswith('.exe') or file_path.endswith('.bat')
    return os.access(file_path, os.X_OK)


def find_clang() -> Optional[str]:
    """查找系统上的 clang 编译器

    Returns:
        clang 绝对路径，未找到时返回 None
    """
    # 1. 检查 PATH
    clang_name = 'clang.exe' if sys.platform == 'win32' else 'clang'
    path_env = os.environ.get('PATH', '')
    for path_dir in path_env.split(os.pathsep):
        candidate = os.path.join(path_dir, clang_name)
        if os.path.exists(candidate):
            return os.path.abspath(candidate)

    # 2. 检查常见安装目录
    platform_dirs = FALLBACK_LLVM_DIRS.get(sys.platform, [])
    for base_dir in platform_dirs:
        expanded = os.path.expanduser(base_dir)
        for rel_path in LLVM_CLANG_RELATIVE_PATHS.get(sys.platform, []):
            if '*' in rel_path:
                # 通配符匹配
                import glob as _glob
                pattern = os.path.join(expanded, rel_path)
                matches = _glob.glob(pattern)
                if matches:
                    return os.path.abspath(matches[0])
            else:
                candidate = os.path.join(expanded, rel_path)
                if os.path.exists(candidate):
                    return os.path.abspath(candidate)

    # 3. Windows: 检查 MSVC 自带的 LLVM
    if sys.platform == 'win32':
        vs_paths = [
            r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\Llvm\bin\clang.exe',
            r'C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Tools\Llvm\bin\clang.exe',
            r'C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Tools\Llvm\bin\clang.exe',
        ]
        for vs_path in vs_paths:
            if os.path.exists(vs_path):
                return os.path.abspath(vs_path)

    # 4. 检查 llvm-mingw 工具链
    if sys.platform == 'win32':
        mingw_dirs = [
            r'c:\traework\duan\llvm-mingw-20240619-ucrt-x86_64\bin\clang.exe',
            r'c:\traework\duan\llvm-mingw-20240619-ucrt-aarch64\bin\clang.exe',
        ]
        for mingw in mingw_dirs:
            if os.path.exists(mingw):
                return os.path.abspath(mingw)

    return None


def get_clang_version(clang_path: str) -> Optional[str]:
    """获取 clang 版本号

    Args:
        clang_path: clang 可执行文件路径

    Returns:
        版本号字符串，如 '19.1.0'，失败时返回 None
    """
    try:
        result = subprocess.run(
            [clang_path, '--version'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            # 从输出中提取版本号
            first_line = result.stdout.splitlines()[0] if result.stdout else ''
            # 常见格式: "clang version 19.1.0 ..."
            for part in first_line.split():
                if part[0].isdigit():
                    return part
        return None
    except (subprocess.SubprocessError, OSError, IndexError):
        return None


def get_llvm_info() -> Dict[str, object]:
    """获取完整的 LLVM 环境信息

    Returns:
        包含 LLVM 环境信息的字典
    """
    info: Dict[str, object] = {
        'installed': False,
        'clang_path': None,
        'version': None,
        'platform': sys.platform,
        'architecture': platform.machine(),
        'download_url': LLVM_DOWNLOAD_URLS.get(sys.platform, ''),
        'fallback_available': False,
    }

    clang_path = find_clang()
    if clang_path:
        version = get_clang_version(clang_path)
        info['installed'] = True
        info['clang_path'] = clang_path
        info['version'] = version
        info['fallback_available'] = True

    return info


# =============================================================================
# 降级策略
# =============================================================================

class LLVMFallbackStrategy:
    """LLVM 不可用时的降级策略

    提供多种降级方案，按优先级排列：
    1. 使用 llvmlite Python 包做本地验证
    2. 使用系统自带的 C 编译器（gcc/msvc）
    3. 纯 Python 解释执行（SRC 后端）
    """

    @staticmethod
    def try_llvmlite() -> bool:
        """尝试使用 llvmlite 作为验证后端

        Returns:
            True 表示 llvmlite 可用
        """
        try:
            import llvmlite  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def try_system_cc() -> Optional[str]:
        """尝试查找系统自带的 C 编译器

        Returns:
            C 编译器路径，未找到时返回 None
        """
        if sys.platform == 'win32':
            # 尝试 MSVC cl.exe
            for path in os.environ.get('PATH', '').split(os.pathsep):
                cl_path = os.path.join(path, 'cl.exe')
                if os.path.exists(cl_path):
                    return os.path.abspath(cl_path)
            # 尝试 MinGW gcc
            for path in os.environ.get('PATH', '').split(os.pathsep):
                gcc_path = os.path.join(path, 'gcc.exe')
                if os.path.exists(gcc_path):
                    return os.path.abspath(gcc_path)
        else:
            # Linux/macOS: 尝试 gcc
            gcc_name = 'gcc'
            for path in os.environ.get('PATH', '').split(os.pathsep):
                gcc_path = os.path.join(path, gcc_name)
                if os.path.exists(gcc_path):
                    return os.path.abspath(gcc_path)
        return None

    @staticmethod
    def get_recommendation() -> str:
        """获取 LLVM 安装建议"""
        recommendations = []

        if sys.platform == 'win32':
            recommendations.append(
                "Windows 安装 LLVM 的推荐方式：\n"
                "  1. 下载 LLVM 官方安装包：\n"
                f"     {LLVM_DOWNLOAD_URLS.get('win32', '')}\n"
                "  2. 安装时勾选 'Add LLVM to the system PATH'\n"
                "  3. 或使用 Chocolatey: choco install llvm\n"
                "  4. 或使用 winget: winget install LLVM.LLVM"
            )
        elif sys.platform == 'darwin':
            recommendations.append(
                "macOS 安装 LLVM 的推荐方式：\n"
                "  1. brew install llvm\n"
                "  2. 将 /opt/homebrew/opt/llvm/bin 加入 PATH"
            )
        else:
            recommendations.append(
                "Linux 安装 LLVM 的推荐方式：\n"
                "  1. Ubuntu/Debian: sudo apt install clang lld\n"
                "  2. Fedora: sudo dnf install clang lld\n"
                "  3. Arch: sudo pacman -S clang lld"
            )

        recommendations.append(
            "或安装 Python 的 llvmlite 包做本地 IR 验证：\n"
            "  pip install llvmlite"
        )

        return '\n'.join(recommendations)

    @staticmethod
    def get_available_options() -> List[Dict[str, object]]:
        """获取当前可用的所有降级选项

        Returns:
            可用选项列表，每项包含 name 和 available 字段
        """
        options = [
            {'name': 'llvmlite (Python IR 验证)', 'available': LLVMFallbackStrategy.try_llvmlite()},
            {'name': 'system C compiler', 'available': LLVMFallbackStrategy.try_system_cc() is not None},
            {'name': 'SRC backend (pure Python)', 'available': True},
        ]
        return options


# =============================================================================
# 自动下载 LLVM
# =============================================================================

class LLVMAutoDownloader:
    """LLVM 自动下载管理器

    支持从 GitHub Releases 下载预构建的 LLVM 二进制包，
    解压到指定目录并配置环境变量。
    """

    def __init__(self, install_dir: Optional[str] = None):
        self.install_dir = Path(install_dir or self._default_install_dir())
        self.download_url = LLVM_DOWNLOAD_URLS.get(sys.platform, '')
        self._ensure_dir()

    @staticmethod
    def _default_install_dir() -> str:
        """获取默认安装目录"""
        home = os.path.expanduser('~')
        if sys.platform == 'win32':
            return os.path.join(home, 'AppData', 'Local', 'duan', 'llvm')
        return os.path.join(home, '.duan', 'llvm')

    def _ensure_dir(self):
        """确保安装目录存在"""
        self.install_dir.mkdir(parents=True, exist_ok=True)

    def is_downloaded(self) -> bool:
        """检查是否已下载 LLVM

        Returns:
            True 表示已下载且 clang 可执行
        """
        clang_path = self.get_clang_path()
        return clang_path is not None and os.path.exists(clang_path)

    def get_clang_path(self) -> Optional[str]:
        """获取下载目录中的 clang 路径

        Returns:
            clang 绝对路径，未找到时返回 None
        """
        clang_name = 'clang.exe' if sys.platform == 'win32' else 'clang'
        # 递归搜索安装目录
        for root, dirs, files in os.walk(str(self.install_dir)):
            if clang_name in files:
                return os.path.join(root, clang_name)
        return None

    def download(self, progress_callback=None) -> str:
        """下载 LLVM 预构建二进制包

        Args:
            progress_callback: 进度回调函数，接收 (downloaded_bytes, total_bytes)

        Returns:
            下载文件的路径

        Raises:
            RuntimeError: 下载失败或不支持的平台
        """
        if not self.download_url:
            raise RuntimeError(f"不支持的平台: {sys.platform}，无法自动下载 LLVM")

        filename = self.download_url.split('/')[-1]
        download_path = self.install_dir / filename

        # 如果已下载则跳过
        if download_path.exists():
            return str(download_path)

        print(f"[LLVM 下载] 正在下载 LLVM {LLVM_VERSION}...")
        print(f"  来源: {self.download_url}")
        print(f"  目标: {download_path}")

        try:
            def _report_progress(block_count, block_size, total_size):
                downloaded = block_count * block_size
                if total_size > 0:
                    percent = min(100, int(downloaded * 100 / total_size))
                    if progress_callback:
                        progress_callback(downloaded, total_size)
                    if percent % 10 == 0:
                        print(f"  进度: {percent}% ({downloaded // 1024 // 1024}MB / {total_size // 1024 // 1024}MB)")

            urllib.request.urlretrieve(
                self.download_url,
                str(download_path),
                reporthook=_report_progress
            )
            print(f"  下载完成: {download_path}")
            return str(download_path)

        except urllib.error.URLError as e:
            raise RuntimeError(f"LLVM 下载失败: {e.reason}") from e
        except Exception as e:
            raise RuntimeError(f"LLVM 下载失败: {e}") from e

    def extract(self, archive_path: str) -> str:
        """解压 LLVM 二进制包

        Args:
            archive_path: 压缩包路径

        Returns:
            解压后的目录路径

        Raises:
            RuntimeError: 解压失败
        """
        extract_dir = self.install_dir / f'llvm-{LLVM_VERSION}'
        extract_dir.mkdir(parents=True, exist_ok=True)

        print(f"[LLVM 解压] 正在解压到 {extract_dir}...")

        try:
            if archive_path.endswith('.tar.xz') or archive_path.endswith('.tar.gz'):
                mode = 'r:xz' if archive_path.endswith('.xz') else 'r:gz'
                with tarfile.open(archive_path, mode) as tar:
                    tar.extractall(path=str(extract_dir))
            elif archive_path.endswith('.zip') or archive_path.endswith('.exe'):
                # Windows 的 .exe 安装包或 .zip
                if archive_path.endswith('.exe'):
                    # 对于 .exe 安装包，使用 7z 或直接执行
                    try:
                        subprocess.run(
                            [archive_path, '/S', f'/D={extract_dir}'],
                            check=True, timeout=300
                        )
                        return str(extract_dir)
                    except (subprocess.SubprocessError, OSError):
                        # 静默安装失败，尝试作为 ZIP 处理
                        pass

                if archive_path.endswith('.zip') or archive_path.endswith('.exe'):
                    with zipfile.ZipFile(archive_path, 'r') as zf:
                        zf.extractall(path=str(extract_dir))
            else:
                raise RuntimeError(f"不支持的压缩格式: {archive_path}")

            print(f"  解压完成")
            return str(extract_dir)

        except (tarfile.TarError, zipfile.BadZipFile) as e:
            raise RuntimeError(f"LLVM 解压失败: {e}") from e

    def install(self, progress_callback=None) -> str:
        """完整安装流程：下载 + 解压

        Args:
            progress_callback: 进度回调

        Returns:
            clang 可执行文件路径

        Raises:
            RuntimeError: 安装失败
        """
        # 如果已安装则跳过
        clang_path = self.get_clang_path()
        if clang_path:
            print(f"[LLVM 安装] 已安装: {clang_path}")
            return clang_path

        archive_path = self.download(progress_callback)
        extract_dir = self.extract(archive_path)

        # 查找安装后的 clang
        clang_path = self.get_clang_path()
        if not clang_path:
            raise RuntimeError(
                f"LLVM 安装后未找到 clang，请手动检查目录: {extract_dir}"
            )

        print(f"[LLVM 安装] 完成: {clang_path}")
        return clang_path

    def add_to_path(self) -> bool:
        """将 LLVM 安装目录添加到 PATH

        Returns:
            True 表示成功
        """
        clang_path = self.get_clang_path()
        if not clang_path:
            return False

        bin_dir = os.path.dirname(clang_path)
        if bin_dir in os.environ.get('PATH', ''):
            return True  # 已在 PATH 中

        # 仅对当前进程有效
        os.environ['PATH'] = bin_dir + os.pathsep + os.environ.get('PATH', '')
        return True


# =============================================================================
# 构建系统集成
# =============================================================================

def ensure_llvm(verbose: bool = False, auto_download: bool = True) -> Dict[str, object]:
    """确保 LLVM 环境可用，返回检测结果

    这是构建系统集成的主入口函数。按以下顺序尝试：
    1. 检测系统已安装的 LLVM
    2. 如果 auto_download=True，尝试自动下载
    3. 返回降级策略建议

    Args:
        verbose: 是否输出详细信息
        auto_download: 是否允许自动下载 LLVM

    Returns:
        包含 LLVM 环境信息的字典：
        {
            'available': bool,         # 是否可用
            'clang_path': str|None,    # clang 路径
            'version': str|None,       # 版本号
            'source': str,             # 来源 ('system', 'downloaded', 'fallback')
            'fallback': str,           # 降级策略建议
            'options': list,           # 可用降级选项
        }
    """
    result: Dict[str, object] = {
        'available': False,
        'clang_path': None,
        'version': None,
        'source': 'none',
        'fallback': '',
        'options': [],
    }

    # 1. 检测系统安装
    clang_path = find_clang()
    if clang_path:
        version = get_clang_version(clang_path)
        result['available'] = True
        result['clang_path'] = clang_path
        result['version'] = version
        result['source'] = 'system'
        if verbose:
            print(f"[LLVM 检测] 系统已安装: {clang_path} (version: {version or 'unknown'})")
        return result

    # 2. 检查已下载的 LLVM
    downloader = LLVMAutoDownloader()
    if downloader.is_downloaded():
        clang_path = downloader.get_clang_path()
        version = get_clang_version(clang_path) if clang_path else None
        result['available'] = True
        result['clang_path'] = clang_path
        result['version'] = version
        result['source'] = 'downloaded'
        if verbose:
            print(f"[LLVM 检测] 已下载: {clang_path} (version: {version or 'unknown'})")
        return result

    # 3. 自动下载
    if auto_download:
        if verbose:
            print(f"[LLVM 检测] 系统未安装，尝试自动下载...")
        try:
            clang_path = downloader.install()
            version = get_clang_version(clang_path)
            result['available'] = True
            result['clang_path'] = clang_path
            result['version'] = version
            result['source'] = 'downloaded'
            if verbose:
                print(f"[LLVM 检测] 自动下载完成: {clang_path}")
            return result
        except RuntimeError as e:
            if verbose:
                print(f"[LLVM 检测] 自动下载失败: {e}")

    # 4. 降级策略
    fallback = LLVMFallbackStrategy()
    result['available'] = False
    result['source'] = 'fallback'
    result['fallback'] = fallback.get_recommendation()
    result['options'] = fallback.get_available_options()

    if verbose:
        print(f"[LLVM 检测] LLVM 未安装，使用降级策略")
        print(f"  可用选项: {len(result['options'])} 个")
        for opt in result['options']:
            status = '✓' if opt['available'] else '✗'
            print(f"    {status} {opt['name']}")

    return result


def get_llvm_build_flags(optimize_size: bool = False,
                          lto: bool = False,
                          strip: bool = False) -> List[str]:
    """获取 LLVM 构建参数

    根据配置生成 clang 编译和链接参数。

    Args:
        optimize_size: 是否启用 -Os 尺寸优化
        lto: 是否启用 LTO (Link Time Optimization)
        strip: 是否剥离调试符号

    Returns:
        clang 参数列表
    """
    flags: List[str] = []

    if optimize_size:
        flags.extend(['-Os', '-fdata-sections', '-ffunction-sections'])
        if sys.platform != 'darwin':
            flags.extend(['-Wl,--gc-sections'])
        else:
            flags.extend(['-Wl,-dead_strip'])
    else:
        flags.append('-O2')

    if lto:
        flags.append('-flto')
        if sys.platform == 'win32':
            flags.append('-fuse-ld=lld')
        elif sys.platform == 'darwin':
            flags.append('-flto=full')
        else:
            flags.append('-flto=auto')

    if strip:
        if sys.platform == 'darwin':
            flags.append('-Wl,-S')
        elif sys.platform == 'win32':
            # Windows 上 strip 在链接后单独处理
            pass
        else:
            flags.append('-s')

    return flags


def strip_binary(binary_path: str) -> bool:
    """剥离可执行文件中的调试符号

    Args:
        binary_path: 可执行文件路径

    Returns:
        True 表示剥离成功
    """
    if not os.path.exists(binary_path):
        return False

    try:
        if sys.platform == 'win32':
            # Windows 使用 dumpbin / strip 或 llvm-strip
            strip_tools = ['llvm-strip', 'strip']
            for tool in strip_tools:
                try:
                    result = subprocess.run(
                        [tool, binary_path],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        return True
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
            return False
        else:
            # Linux/macOS 使用 strip
            subprocess.run(
                ['strip', binary_path],
                check=True, timeout=30
            )
            return True
    except (subprocess.SubprocessError, OSError):
        return False


# =============================================================================
# 路径检测辅助
# =============================================================================

def get_llvm_paths() -> Dict[str, Optional[str]]:
    """获取 LLVM 相关路径

    Returns:
        包含各组件路径的字典
    """
    clang_path = find_clang()
    if not clang_path:
        return {
            'clang': None,
            'clang_dir': None,
            'llvm_root': None,
            'llvm_bin': None,
            'llvm_lib': None,
            'llvm_include': None,
        }

    bin_dir = os.path.dirname(clang_path)
    llvm_root = os.path.dirname(bin_dir) if bin_dir else None

    return {
        'clang': clang_path,
        'clang_dir': bin_dir,
        'llvm_root': llvm_root,
        'llvm_bin': bin_dir,
        'llvm_lib': os.path.join(llvm_root, 'lib') if llvm_root else None,
        'llvm_include': os.path.join(llvm_root, 'include') if llvm_root else None,
    }


def get_env_setup_script() -> str:
    """生成环境变量设置脚本

    Returns:
        适用于当前平台的 shell 脚本内容
    """
    paths = get_llvm_paths()
    if not paths.get('llvm_bin'):
        return "# LLVM 未安装，无法生成环境设置脚本"

    bin_dir = paths['llvm_bin']

    if sys.platform == 'win32':
        return (
            f"@echo off\n"
            f"set PATH={bin_dir};%PATH%\n"
            f"echo LLVM 环境已设置\n"
        )
    else:
        return (
            f"export PATH=\"{bin_dir}:$PATH\"\n"
            f"echo \"LLVM 环境已设置\"\n"
        )


# =============================================================================
# 便捷入口
# =============================================================================

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='段言 LLVM 依赖管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('action', nargs='?', default='check',
                        choices=['check', 'download', 'install', 'info', 'paths'],
                        help='操作: check=检测, download=下载, install=安装, info=信息, paths=路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--install-dir', help='指定安装目录')

    args = parser.parse_args()

    if args.action == 'check':
        result = ensure_llvm(verbose=True, auto_download=False)
        if result['available']:
            print(f"✓ LLVM 已安装: {result['clang_path']}")
            print(f"  版本: {result['version'] or 'unknown'}")
            print(f"  来源: {result['source']}")
        else:
            print("✗ LLVM 未安装")
            print(f"\n降级建议:\n{result['fallback']}")
        return 0 if result['available'] else 1

    elif args.action in ('download', 'install'):
        downloader = LLVMAutoDownloader(install_dir=args.install_dir)
        if args.action == 'install':
            clang_path = downloader.install()
            print(f"✓ LLVM 安装完成: {clang_path}")
        else:
            archive_path = downloader.download()
            print(f"✓ LLVM 下载完成: {archive_path}")
        return 0

    elif args.action == 'info':
        info = get_llvm_info()
        print(f"平台: {info['platform']} ({info['architecture']})")
        print(f"已安装: {'是' if info['installed'] else '否'}")
        if info['installed']:
            print(f"  clang: {info['clang_path']}")
            print(f"  版本: {info['version'] or 'unknown'}")
        else:
            print(f"  下载地址: {info['download_url']}")
        print(f"  降级可用: {'是' if info['fallback_available'] else '否'}")
        return 0

    elif args.action == 'paths':
        paths = get_llvm_paths()
        print("LLVM 路径:")
        for key, value in paths.items():
            if value:
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: (未找到)")
        return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())