"""
段言 C FFI 增强模块 — 简化 C 库加载与调用

提供更加简洁的 C 语言 FFI 接口，自动处理平台差异，内置常用 C 库预设绑定。

快速上手：
    from FFI增强 import 加载C库, 调用C函数, libc, libm

    libc = 加载C库("c")           # 自动检测平台扩展名
    结果 = 调用C函数(libc, "printf", b"Hello %s\\n", b"World")

    # 或使用预设绑定
    from FFI增强 import 预设绑定
    libc = 预设绑定["libc"]
    结果 = libc.printf(b"Hello %s\\n", b"World")
"""

import ctypes
import os
import platform
import sys
from typing import Any, Dict, List, Optional, Tuple, Callable, Union


# =============================================================================
# 平台检测
# =============================================================================

def _检测系统() -> str:
    """返回当前系统类型：'windows', 'linux', 'macos'"""
    system = platform.system().lower()
    if system == 'windows':
        return 'windows'
    elif system == 'darwin':
        return 'macos'
    else:
        return 'linux'


def _库扩展名() -> str:
    """返回当前平台的动态库扩展名"""
    system = _检测系统()
    if system == 'windows':
        return '.dll'
    elif system == 'macos':
        return '.dylib'
    else:
        return '.so'


def _库前缀() -> str:
    """返回当前平台的动态库前缀"""
    system = _检测系统()
    if system == 'windows':
        return ''
    else:
        return 'lib'


# =============================================================================
# 简化库加载
# =============================================================================

# 已知库名到实际文件名的映射
_KNOWN_LIBRARIES = {
    # libc 系列
    'c':       ['libc.so.6', 'libc.so', 'libc.dylib', 'msvcrt.dll', 'ucrtbase.dll'],
    'libc':    ['libc.so.6', 'libc.so', 'libc.dylib', 'msvcrt.dll', 'ucrtbase.dll'],
    'msvcrt':  ['msvcrt.dll'],
    # libm 系列
    'm':       ['libm.so.6', 'libm.so', 'libm.dylib'],
    'libm':    ['libm.so.6', 'libm.so', 'libm.dylib'],
    # pthread
    'pthread':   ['libpthread.so.0', 'libpthread.so', 'libpthread.dylib'],
    'libpthread': ['libpthread.so.0', 'libpthread.so', 'libpthread.dylib'],
    # dl
    'dl':      ['libdl.so.2', 'libdl.so', 'libdl.dylib'],
    'libdl':   ['libdl.so.2', 'libdl.so', 'libdl.dylib'],
    # kernel32 (Windows)
    'kernel32': ['kernel32.dll'],
    # user32 (Windows)
    'user32':   ['user32.dll'],
    # Python 运行时
    'python':   [f'python{sys.version_info.major}{sys.version_info.minor}.dll',
                 f'libpython{sys.version_info.major}.{sys.version_info.minor}.so',
                 f'libpython{sys.version_info.major}.{sys.version_info.minor}.dylib'],
}


def _查找库文件(库名: str) -> Optional[str]:
    """根据库名查找实际的文件路径"""
    # 1. 如果库名本身是文件路径且存在，直接使用
    if os.path.exists(库名):
        return 库名

    # 2. 查找已知库映射
    if 库名 in _KNOWN_LIBRARIES:
        for candidate in _KNOWN_LIBRARIES[库名]:
            # 检查常见路径
            search_paths = [candidate]
            if _检测系统() == 'linux':
                search_paths.extend([
                    f'/usr/lib/{candidate}',
                    f'/usr/lib/x86_64-linux-gnu/{candidate}',
                    f'/usr/lib/aarch64-linux-gnu/{candidate}',
                    f'/lib/{candidate}',
                    f'/lib/x86_64-linux-gnu/{candidate}',
                ])
            elif _检测系统() == 'macos':
                search_paths.extend([
                    f'/usr/lib/{candidate}',
                    f'/usr/local/lib/{candidate}',
                ])
            elif _检测系统() == 'windows':
                system_root = os.environ.get('SYSTEMROOT', 'C:\\Windows')
                search_paths.extend([
                    os.path.join(system_root, 'System32', candidate),
                    os.path.join(system_root, 'SysWOW64', candidate),
                ])
            for sp in search_paths:
                if os.path.exists(sp):
                    return sp

    # 3. 尝试 ctypes.util.find_library
    try:
        from ctypes import util
        found = util.find_library(库名)
        if found:
            return found
    except (ImportError, AttributeError):
        pass

    # 4. 尝试构造常见文件名
    prefix = _库前缀()
    ext = _库扩展名()
    constructed = f"{prefix}{库名}{ext}"
    if os.path.exists(constructed):
        return constructed

    # 5. 尝试直接加载（ctypes 会搜索系统路径）
    return 库名


def 加载C库(库名: str) -> ctypes.CDLL:
    """简化 C 库加载 — 自动检测平台扩展名和搜索路径。

    参数:
        库名: 库名称（如 'c', 'm', 'pthread', 'dl'）或文件路径

    返回:
        ctypes.CDLL 实例

    示例:
        libc = 加载C库('c')           # 加载标准 C 库
        libm = 加载C库('m')           # 加载数学库
        libpthread = 加载C库('pthread')  # 加载线程库
    """
    lib_path = _查找库文件(库名)
    if lib_path is None:
        # 最后的尝试：让 ctypes 自己去搜索
        try:
            return ctypes.CDLL(库名)
        except OSError as e:
            raise OSError(f"无法加载 C 库 '{库名}': {e}")
    try:
        return ctypes.CDLL(lib_path)
    except OSError as e:
        raise OSError(f"无法加载 C 库 '{库名}' (路径: {lib_path}): {e}")


def 调用C函数(lib: ctypes.CDLL, 函数名: str, *参数) -> Any:
    """简化的 C 函数调用 — 自动处理参数类型。

    参数:
        lib: 通过 加载C库() 获取的库实例
        函数名: C 函数名称
        *参数: 函数参数（自动推断类型）

    返回:
        C 函数的返回值

    示例:
        结果 = 调用C函数(libc, 'printf', b"Hello\\n")
        结果 = 调用C函数(libm, 'sqrt', 16.0)
    """
    func = getattr(lib, 函数名)
    return func(*参数)


def 声明并调用C函数(lib: ctypes.CDLL, 函数名: str,
                     参数类型列表: List[Any], 返回类型: Any,
                     *参数) -> Any:
    """声明函数签名并调用 — 适合需要精确控制类型的场景。

    参数:
        lib: 通过 加载C库() 获取的库实例
        函数名: C 函数名称
        参数类型列表: ctypes 参数类型列表（如 [ctypes.c_double, ctypes.c_double]）
        返回类型: ctypes 返回类型（如 ctypes.c_double）
        *参数: 函数参数

    返回:
        C 函数的返回值

    示例:
        result = 声明并调用C函数(libm, 'pow',
                                 [ctypes.c_double, ctypes.c_double],
                                 ctypes.c_double, 2.0, 10.0)
    """
    func = getattr(lib, 函数名)
    func.argtypes = 参数类型列表
    func.restype = 返回类型
    return func(*参数)


# =============================================================================
# 预设绑定 — 常用 C 库函数预设
# =============================================================================

class _LibcPreset:
    """libc（标准 C 库）预设绑定"""

    def __init__(self, lib: ctypes.CDLL):
        self._lib = lib
        # 预设函数签名
        self._初始化函数()

    def _初始化函数(self):
        """初始化常用函数签名"""
        # printf
        self._lib.printf.argtypes = [ctypes.c_char_p]
        self._lib.printf.restype = ctypes.c_int

        # sprintf
        self._lib.sprintf.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.sprintf.restype = ctypes.c_int

        # malloc
        self._lib.malloc.argtypes = [ctypes.c_size_t]
        self._lib.malloc.restype = ctypes.c_void_p

        # free
        self._lib.free.argtypes = [ctypes.c_void_p]
        self._lib.free.restype = None

        # calloc
        self._lib.calloc.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
        self._lib.calloc.restype = ctypes.c_void_p

        # realloc
        self._lib.realloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        self._lib.realloc.restype = ctypes.c_void_p

        # strlen
        self._lib.strlen.argtypes = [ctypes.c_char_p]
        self._lib.strlen.restype = ctypes.c_size_t

        # strcmp
        self._lib.strcmp.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.strcmp.restype = ctypes.c_int

        # strcpy
        self._lib.strcpy.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.strcpy.restype = ctypes.c_char_p

        # memset
        self._lib.memset.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t]
        self._lib.memset.restype = ctypes.c_void_p

        # memcpy
        self._lib.memcpy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        self._lib.memcpy.restype = ctypes.c_void_p

        # memcmp
        self._lib.memcmp.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        self._lib.memcmp.restype = ctypes.c_int

        # atoi
        self._lib.atoi.argtypes = [ctypes.c_char_p]
        self._lib.atoi.restype = ctypes.c_int

        # atof
        self._lib.atof.argtypes = [ctypes.c_char_p]
        self._lib.atof.restype = ctypes.c_double

        # exit
        self._lib.exit.argtypes = [ctypes.c_int]
        self._lib.exit.restype = None

        # abort
        self._lib.abort.argtypes = []
        self._lib.abort.restype = None

        # puts
        self._lib.puts.argtypes = [ctypes.c_char_p]
        self._lib.puts.restype = ctypes.c_int

    def printf(self, 格式: bytes, *args) -> int:
        return self._lib.printf(格式, *args)

    def malloc(self, 大小: int) -> int:
        return self._lib.malloc(大小)

    def free(self, 指针: int):
        self._lib.free(指针)

    def strlen(self, 字符串: bytes) -> int:
        return self._lib.strlen(字符串)

    def strcmp(self, 甲: bytes, 乙: bytes) -> int:
        return self._lib.strcmp(甲, 乙)

    def memset(self, 目标: int, 值: int, 长度: int):
        self._lib.memset(目标, 值, 长度)

    def memcpy(self, 目标: int, 源: int, 长度: int):
        self._lib.memcpy(目标, 源, 长度)

    def atoi(self, 字符串: bytes) -> int:
        return self._lib.atoi(字符串)

    def exit(self, 状态码: int):
        self._lib.exit(状态码)

    def puts(self, 字符串: bytes) -> int:
        return self._lib.puts(字符串)


class _LibmPreset:
    """libm（数学库）预设绑定"""

    def __init__(self, lib: ctypes.CDLL):
        self._lib = lib
        self._初始化函数()

    def _初始化函数(self):
        double = ctypes.c_double
        for name in ['sin', 'cos', 'tan', 'asin', 'acos', 'atan',
                     'sinh', 'cosh', 'tanh',
                     'sqrt', 'log', 'log10', 'log2', 'log1p',
                     'exp', 'exp2', 'expm1',
                     'ceil', 'floor', 'round', 'trunc',
                     'fabs', 'abs']:
            func = getattr(self._lib, name, None)
            if func:
                func.argtypes = [double]
                func.restype = double

        # pow, hypot, atan2, fmod — 2 个参数
        for name in ['pow', 'hypot', 'atan2', 'fmod']:
            func = getattr(self._lib, name, None)
            if func:
                func.argtypes = [double, double]
                func.restype = double

        # frexp, modf
        self._lib.frexp.argtypes = [double, ctypes.POINTER(ctypes.c_int)]
        self._lib.frexp.restype = double
        self._lib.modf.argtypes = [double, ctypes.POINTER(double)]
        self._lib.modf.restype = double

    def sin(self, x: float) -> float:
        return self._lib.sin(x)

    def cos(self, x: float) -> float:
        return self._lib.cos(x)

    def sqrt(self, x: float) -> float:
        return self._lib.sqrt(x)

    def pow(self, 底数: float, 指数: float) -> float:
        return self._lib.pow(底数, 指数)

    def log(self, x: float) -> float:
        return self._lib.log(x)

    def exp(self, x: float) -> float:
        return self._lib.exp(x)

    def ceil(self, x: float) -> float:
        return self._lib.ceil(x)

    def floor(self, x: float) -> float:
        return self._lib.floor(x)

    def fabs(self, x: float) -> float:
        return self._lib.fabs(x)

    def __getattr__(self, name):
        return getattr(self._lib, name)


class _LibpthreadPreset:
    """libpthread（POSIX 线程库）预设绑定"""

    def __init__(self, lib: ctypes.CDLL):
        self._lib = lib
        self._初始化函数()

    def _初始化函数(self):
        # pthread_create
        self._lib.pthread_create.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self._lib.pthread_create.restype = ctypes.c_int

        # pthread_join
        self._lib.pthread_join.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        self._lib.pthread_join.restype = ctypes.c_int

        # pthread_exit
        self._lib.pthread_exit.argtypes = [ctypes.c_void_p]
        self._lib.pthread_exit.restype = None

        # pthread_self
        self._lib.pthread_self.argtypes = []
        self._lib.pthread_self.restype = ctypes.c_void_p

        # pthread_mutex_init
        self._lib.pthread_mutex_init.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self._lib.pthread_mutex_init.restype = ctypes.c_int

        # pthread_mutex_lock
        self._lib.pthread_mutex_lock.argtypes = [ctypes.c_void_p]
        self._lib.pthread_mutex_lock.restype = ctypes.c_int

        # pthread_mutex_unlock
        self._lib.pthread_mutex_unlock.argtypes = [ctypes.c_void_p]
        self._lib.pthread_mutex_unlock.restype = ctypes.c_int

        # pthread_mutex_destroy
        self._lib.pthread_mutex_destroy.argtypes = [ctypes.c_void_p]
        self._lib.pthread_mutex_destroy.restype = ctypes.c_int


class _LibdlPreset:
    """libdl（动态加载库）预设绑定"""

    def __init__(self, lib: ctypes.CDLL):
        self._lib = lib
        self._初始化函数()

    def _初始化函数(self):
        # dlopen
        self._lib.dlopen.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self._lib.dlopen.restype = ctypes.c_void_p

        # dlsym
        self._lib.dlsym.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self._lib.dlsym.restype = ctypes.c_void_p

        # dlclose
        self._lib.dlclose.argtypes = [ctypes.c_void_p]
        self._lib.dlclose.restype = ctypes.c_int

        # dlerror
        self._lib.dlerror.argtypes = []
        self._lib.dlerror.restype = ctypes.c_char_p


# =============================================================================
# 预设绑定工厂
# =============================================================================

class 预设绑定:
    """常用 C 库的预设绑定 — 开箱即用的函数封装。

    用法:
        from FFI增强 import 预设绑定

        # libc 预设
        libc = 预设绑定.libc
        libc.printf(b"Hello World\\n")
        longitud = libc.strlen(b"Hello")

        # libm 预设
        libm = 预设绑定.libm
        r = libm.sqrt(16.0)
        r = libm.sin(3.14159 / 2)

        # libpthread 预设
        pthread = 预设绑定.libpthread
        pthread.pthread_create(...)

        # libdl 预设
        dl = 预设绑定.libdl
        handle = dl.dlopen(b"libfoo.so", 1)
    """

    _libc_instance = None
    _libm_instance = None
    _libpthread_instance = None
    _libdl_instance = None

    @classmethod
    def _获取libc(cls) -> _LibcPreset:
        if cls._libc_instance is None:
            try:
                lib = 加载C库('c')
                cls._libc_instance = _LibcPreset(lib)
            except OSError:
                try:
                    lib = 加载C库('msvcrt')
                    cls._libc_instance = _LibcPreset(lib)
                except OSError:
                    cls._libc_instance = None
        return cls._libc_instance

    @classmethod
    def _获取libm(cls) -> _LibmPreset:
        if cls._libm_instance is None:
            try:
                lib = 加载C库('m')
                cls._libm_instance = _LibmPreset(lib)
            except OSError:
                cls._libm_instance = None
        return cls._libm_instance

    @classmethod
    def _获取libpthread(cls) -> _LibpthreadPreset:
        if cls._libpthread_instance is None:
            try:
                lib = 加载C库('pthread')
                cls._libpthread_instance = _LibpthreadPreset(lib)
            except OSError:
                cls._libpthread_instance = None
        return cls._libpthread_instance

    @classmethod
    def _获取libdl(cls) -> _LibdlPreset:
        if cls._libdl_instance is None:
            try:
                lib = 加载C库('dl')
                cls._libdl_instance = _LibdlPreset(lib)
            except OSError:
                cls._libdl_instance = None
        return cls._libdl_instance

    @property
    def libc(self) -> _LibcPreset:
        return self._获取libc()

    @property
    def libm(self) -> _LibmPreset:
        return self._获取libm()

    @property
    def libpthread(self) -> _LibpthreadPreset:
        return self._获取libpthread()

    @property
    def libdl(self) -> _LibdlPreset:
        return self._获取libdl()


# 模块级便捷引用
libc = 预设绑定().libc
libm = 预设绑定().libm
libpthread = 预设绑定().libpthread
libdl = 预设绑定().libdl


# =============================================================================
# 辅助工具
# =============================================================================

def 获取系统信息() -> Dict[str, str]:
    """获取当前系统信息，用于调试和跨平台开发"""
    return {
        '系统': _检测系统(),
        '架构': platform.machine(),
        '处理器': platform.processor(),
        '库前缀': _库前缀(),
        '库扩展名': _库扩展名(),
        'Python版本': sys.version,
    }


def 列出可用库() -> List[str]:
    """列出已知的可用库名"""
    return sorted(_KNOWN_LIBRARIES.keys())


def 测试库(库名: str) -> Tuple[bool, str]:
    """测试指定库是否能加载成功"""
    try:
        lib = 加载C库(库名)
        return True, f"成功加载 '{库名}': {lib}"
    except OSError as e:
        return False, str(e)


# =============================================================================
# 简化 API 文档
# =============================================================================

__简化API__ = {
    '加载C库': {
        '签名': '加载C库(库名: str) -> ctypes.CDLL',
        '说明': '简化加载 C 动态库。自动检测平台扩展名（.so/.dylib/.dll），'
                '并搜索已知库路径。支持常见库名缩写（c、m、pthread、dl）。',
        '示例': "libc = 加载C库('c')\nlibm = 加载C库('m')",
    },
    '调用C函数': {
        '签名': '调用C函数(lib, 函数名: str, *参数) -> Any',
        '说明': '简化调用 C 库函数。自动传递参数，无需手动声明函数签名。',
        '示例': "调用C函数(libc, 'printf', b'Hello\\n')",
    },
    '声明并调用C函数': {
        '签名': '声明并调用C函数(lib, 函数名, 参数类型列表, 返回类型, *参数) -> Any',
        '说明': '声明函数签名后调用，适合需要精确控制参数类型的场景。',
        '示例': "声明并调用C函数(libm, 'pow', [ctypes.c_double, ctypes.c_double], ctypes.c_double, 2.0, 10.0)",
    },
    '预设绑定': {
        '说明': '提供常用 C 库函数的预设类型绑定，开箱即用。',
        '子模块': {
            'libc': '标准 C 库（printf, malloc, strlen, strcmp, memset 等）',
            'libm': '数学库（sin, cos, sqrt, pow, log, exp 等）',
            'libpthread': 'POSIX 线程库（pthread_create, pthread_join, mutex 等）',
            'libdl': '动态加载库（dlopen, dlsym, dlclose 等）',
        },
        '示例': "from FFI增强 import 预设绑定\n预设绑定.libm.sqrt(16.0)",
    },
}