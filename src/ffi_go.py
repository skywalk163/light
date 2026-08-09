"""
光明 Go FFI 绑定模块
====================
提供 Go 语言外部函数接口绑定能力。
支持通过 cgo 编译的共享库调用 Go 函数。

用法示例（在 .light 文件中）：
    引 Python:
        from ffi_go import GoFFI
        go_ffi = GoFFI()
    结束引

    设 库 = go_ffi.引用Go库("libmath.so", "math")
    设 结果 = go_ffi.绑定函数(库, "斐波那契", "整数", 返回="整数")
    打印 斐波那契(10)
"""

import ctypes
import os
import sys
from typing import Any, Dict, Optional, Callable, List, Tuple


class GoFFIError(Exception):
    """Go FFI 绑定错误"""
    pass


# 光明类型 -> ctypes 类型映射
TYPE_MAP: Dict[str, Any] = {
    "整数": ctypes.c_int,
    "长整数": ctypes.c_long,
    "长长长整数": ctypes.c_longlong,
    "无符号整数": ctypes.c_uint,
    "无符号长整数": ctypes.c_ulong,
    "小数": ctypes.c_double,
    "浮点": ctypes.c_float,
    "文本": ctypes.c_char_p,
    "布尔": ctypes.c_bool,
    "字节": ctypes.c_char,
    "空": None,
    "指针": ctypes.c_void_p,
    "短整数": ctypes.c_short,
    "无符号短整数": ctypes.c_ushort,
    "字节数组": ctypes.c_char_p,
    "无": None,
}


class GoLibrary:
    """已加载的 Go 共享库"""

    def __init__(self, lib_path: str, alias: str, lib: ctypes.CDLL):
        self.lib_path = lib_path
        self.alias = alias
        self.lib = lib
        self._bound_functions: Dict[str, Callable] = {}

    def __repr__(self) -> str:
        return f"<GoLibrary '{self.alias}' from '{self.lib_path}'>"


class GoFFI:
    """Go FFI 绑定入口

    支持中文语法：
        - 引用Go库("路径", "别名") -> 加载 Go 共享库
        - 绑定函数(库, "函数名", 参数类型..., 返回="返回类型") -> 绑定 Go 函数
        - 绑定函数_自定义(库, "光明名", "Go函数名", 参数类型..., 返回="返回类型")
    """

    # 跨平台共享库后缀
    LIB_EXTENSIONS = {
        "win32": ".dll",
        "linux": ".so",
        "darwin": ".dylib",
    }

    def __init__(self):
        self._libraries: Dict[str, GoLibrary] = {}

    # ==================== 公共 API ====================

    def 引用Go库(self, 路径: str, 别名: str = "") -> GoLibrary:
        """加载 Go 共享库

        Go 代码需编译为 cgo 共享库：
            go build -buildmode=c-shared -o libxxx.so

        参数:
            路径: 共享库路径
            别名: 库的别名（用于后续引用）

        返回:
            GoLibrary 实例

        示例:
            >>> go = GoFFI()
            >>> lib = go.引用Go库("libmath.so", "math")
        """
        if not 别名:
            别名 = os.path.splitext(os.path.basename(路径))[0]

        # 尝试自动补全扩展名
        resolved_path = 路径
        if not os.path.exists(resolved_path):
            ext = self.LIB_EXTENSIONS.get(sys.platform, ".so")
            if not resolved_path.endswith(ext):
                test_path = resolved_path + ext
                if os.path.exists(test_path):
                    resolved_path = test_path

        if not os.path.exists(resolved_path):
            # 在系统库路径中查找
            resolved_path = self._find_system_lib(路径)

        try:
            lib = ctypes.cdll.LoadLibrary(resolved_path)
        except OSError as e:
            raise GoFFIError(f"无法加载 Go 库 '{路径}': {e}")

        lib_wrapper = GoLibrary(resolved_path, 别名, lib)
        self._libraries[别名] = lib_wrapper
        return lib_wrapper

    def 绑定函数(self,
              库: GoLibrary,
              Go函数名: str,
              *参数类型: str,
              返回: str = "无") -> Callable:
        """绑定 Go 共享库中的函数

        参数:
            库: GoLibrary 实例
            Go函数名: Go 中 //export 导出的函数名
            *参数类型: 参数对应的光明类型名（如 "整数", "小数"）
            返回: 返回值的光明类型名（默认 "无"）

        返回:
            可调用的 Python 函数

        示例:
            >>> lib = go.引用Go库("libmath.so")
            >>> 斐波那契 = go.绑定函数(lib, "斐波那契", "整数", 返回="整数")
            >>> 斐波那契(10)
            55
        """
        return self.绑定函数_自定义(库, Go函数名, Go函数名, *参数类型, 返回=返回)

    def 绑定函数_自定义(self,
                      库: GoLibrary,
                      光明名: str,
                      Go函数名: str,
                      *参数类型: str,
                      返回: str = "无") -> Callable:
        """绑定 Go 函数，并指定光明侧的函数名

        参数:
            库: GoLibrary 实例
            光明名: 光明中使用的函数名
            Go函数名: Go 中 //export 导出的函数名
            *参数类型: 参数对应的光明类型名
            返回: 返回值的光明类型名

        返回:
            可调用的 Python 函数
        """
        func = getattr(库.lib, Go函数名, None)
        if func is None:
            # 尝试 Go 导出的函数名可能有前缀
            func = getattr(库.lib, f"Go{Go函数名}", None)
        if func is None:
            # 尝试小写
            func = getattr(库.lib, Go函数名.lower(), None)
        if func is None:
            raise GoFFIError(f"未找到 Go 函数 '{Go函数名}'，请确认已用 //export 导出")

        # 设置参数类型
        argtypes = []
        for t in 参数类型:
            ctype = TYPE_MAP.get(t)
            if ctype is None:
                raise GoFFIError(f"不支持的参数类型: '{t}'")
            argtypes.append(ctype)
        func.argtypes = argtypes

        # 设置返回类型
        ret_type = TYPE_MAP.get(返回)
        if ret_type is None:
            raise GoFFIError(f"不支持的返回类型: '{返回}'")
        func.restype = ret_type

        库._bound_functions[光明名] = func
        return func

    def 绑定结构体(self, 库: GoLibrary, 结构体名: str, 字段: List[Tuple[str, str]]) -> type:
        """绑定 Go 结构体（通过 ctypes 模拟）

        参数:
            库: GoLibrary 实例
            结构体名: 结构体名称
            字段: 字段列表，每项为 (字段名, 光明类型名)

        返回:
            ctypes.Structure 子类
        """
        fields_list = []
        for field_name, field_type in 字段:
            ctype = TYPE_MAP.get(field_type)
            if ctype is None:
                raise GoFFIError(f"不支持的字段类型: '{field_type}'")
            fields_list.append((field_name, ctype))

        struct_class = type(结构体名, (ctypes.Structure,), {"_fields_": fields_list})
        return struct_class

    def 获取库(self, 别名: str) -> Optional[GoLibrary]:
        """获取已加载的 Go 库"""
        return self._libraries.get(别名)

    def 列出库(self) -> Dict[str, GoLibrary]:
        """列出所有已加载的 Go 库"""
        return dict(self._libraries)

    def 释放库(self, 别名: str) -> bool:
        """释放已加载的 Go 库"""
        if 别名 in self._libraries:
            del self._libraries[别名]
            return True
        return False

    # ==================== 内部方法 ====================

    def _find_system_lib(self, 路径: str) -> str:
        """在系统库路径中查找共享库"""
        # 仅检查文件名
        basename = os.path.basename(路径)
        search_paths = [
            "/usr/lib",
            "/usr/local/lib",
            "/opt/homebrew/lib",
            "/lib",
            "/usr/lib/x86_64-linux-gnu",
        ]

        # Windows 系统库路径
        if sys.platform == "win32":
            search_paths = [
                os.environ.get("SYSTEMROOT", "C:\\Windows") + "\\System32",
                os.environ.get("GOPATH", ""),
            ]

        for sp in search_paths:
            full_path = os.path.join(sp, basename)
            if os.path.exists(full_path):
                return full_path

        raise GoFFIError(f"无法在系统路径中找到 Go 库 '{路径}'")

    def 字符串转字节(self, 文本: str) -> bytes:
        """将光明字符串转为 C 字符串字节"""
        return 文本.encode("utf-8")

    def 字节转字符串(self, 字节: bytes) -> str:
        """将 C 字符串字节转为光明字符串"""
        return 字节.decode("utf-8")