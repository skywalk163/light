"""
光明 Rust FFI 绑定模块
======================
提供 Rust 语言外部函数接口绑定能力。
支持通过 FFI 导出的 Rust 共享库调用。

用法示例（在 .light 文件中）：
    引 Python:
        from ffi_rust import RustFFI
        rust_ffi = RustFFI()
    结束引

    设 库 = rust_ffi.引用Rust库("libcalc.so", "calc")
    设 结果 = rust_ffi.绑定函数(库, "add", "整数", "整数", 返回="整数")
    打印 add(3, 5)
"""

import ctypes
import os
import sys
from typing import Any, Dict, Optional, Callable, List, Tuple


class RustFFIError(Exception):
    """Rust FFI 绑定错误"""
    pass


# 光明类型 -> ctypes 类型映射
TYPE_MAP: Dict[str, Any] = {
    "整数": ctypes.c_int,
    "长整数": ctypes.c_long,
    "长长长整数": ctypes.c_longlong,
    "无符号整数": ctypes.c_uint,
    "无符号长整数": ctypes.c_ulong,
    "无符号长长整数": ctypes.c_ulonglong,
    "小数": ctypes.c_double,
    "浮点": ctypes.c_float,
    "文本": ctypes.c_char_p,
    "布尔": ctypes.c_bool,
    "字节": ctypes.c_char,
    "空": None,
    "指针": ctypes.c_void_p,
    "短整数": ctypes.c_short,
    "无符号短整数": ctypes.c_ushort,
    "无": None,
    "大小": ctypes.c_size_t,
    "int8": ctypes.c_int8,
    "int16": ctypes.c_int16,
    "int32": ctypes.c_int32,
    "int64": ctypes.c_int64,
    "uint8": ctypes.c_uint8,
    "uint16": ctypes.c_uint16,
    "uint32": ctypes.c_uint32,
    "uint64": ctypes.c_uint64,
}


class RustLibrary:
    """已加载的 Rust 共享库"""

    def __init__(self, lib_path: str, alias: str, lib: ctypes.CDLL):
        self.lib_path = lib_path
        self.alias = alias
        self.lib = lib
        self._bound_functions: Dict[str, Callable] = {}

    def __repr__(self) -> str:
        return f"<RustLibrary '{self.alias}' from '{self.lib_path}'>"


class RustFFI:
    """Rust FFI 绑定入口

    支持中文语法：
        - 引用Rust库("路径", "别名") -> 加载 Rust 共享库
        - 绑定函数(库, "函数名", 参数类型..., 返回="返回类型") -> 绑定 Rust 函数
        - 绑定函数_自定义(库, "光明名", "Rust函数名", 参数类型..., 返回="返回类型")
        - 绑定字符串函数(库, "函数名", 参数...) -> 绑定返回字符串的 Rust 函数
    """

    LIB_EXTENSIONS = {
        "win32": ".dll",
        "linux": ".so",
        "darwin": ".dylib",
    }

    def __init__(self):
        self._libraries: Dict[str, RustLibrary] = {}

    # ==================== 公共 API ====================

    def 引用Rust库(self, 路径: str, 别名: str = "") -> RustLibrary:
        """加载 Rust 共享库

        Rust 代码需编译为 cdylib 共享库：
            [lib]
            crate-type = ["cdylib"]

        编译命令：
            cargo build --release
            # 目标文件在 target/release/libxxx.so

        参数:
            路径: 共享库路径
            别名: 库的别名（用于后续引用）

        返回:
            RustLibrary 实例

        示例:
            >>> rust = RustFFI()
            >>> lib = rust.引用Rust库("libcalc.so", "calc")
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
            # 在系统库路径和目标目录中查找
            resolved_path = self._find_lib_path(路径)

        try:
            lib = ctypes.cdll.LoadLibrary(resolved_path)
        except OSError as e:
            raise RustFFIError(f"无法加载 Rust 库 '{路径}': {e}")

        lib_wrapper = RustLibrary(resolved_path, 别名, lib)
        self._libraries[别名] = lib_wrapper
        return lib_wrapper

    def 绑定函数(self,
               库: RustLibrary,
               Rust函数名: str,
               *参数类型: str,
               返回: str = "无") -> Callable:
        """绑定 Rust 共享库中导出的函数

        参数:
            库: RustLibrary 实例
            Rust函数名: Rust 中 #[no_mangle] pub extern "C" 函数名
            *参数类型: 参数对应的光明类型名
            返回: 返回值的光明类型名（默认 "无"）

        返回:
            可调用的 Python 函数

        示例:
            >>> lib = rust.引用Rust库("libcalc.so")
            >>> add = rust.绑定函数(lib, "add", "整数", "整数", 返回="整数")
            >>> add(3, 5)
            8
        """
        return self.绑定函数_自定义(库, Rust函数名, Rust函数名, *参数类型, 返回=返回)

    def 绑定函数_自定义(self,
                       库: RustLibrary,
                       光明名: str,
                       Rust函数名: str,
                       *参数类型: str,
                       返回: str = "无") -> Callable:
        """绑定 Rust 函数，并指定光明侧的函数名

        参数:
            库: RustLibrary 实例
            光明名: 光明中使用的函数名
            Rust函数名: Rust 中导出的函数名
            *参数类型: 参数对应的光明类型名
            返回: 返回值的光明类型名

        返回:
            可调用的 Python 函数
        """
        func = getattr(库.lib, Rust函数名, None)
        if func is None:
            # 尝试 Rust 名称重整后的函数名
            func = getattr(库.lib, f"rust_{Rust函数名}", None)
        if func is None:
            raise RustFFIError(
                f"未找到 Rust 函数 '{Rust函数名}'，请确认已添加 #[no_mangle] pub extern \"C\""
            )

        # 设置参数类型
        argtypes = []
        for t in 参数类型:
            ctype = TYPE_MAP.get(t)
            if ctype is None:
                raise RustFFIError(f"不支持的参数类型: '{t}'")
            argtypes.append(ctype)
        func.argtypes = argtypes

        # 设置返回类型
        ret_type = TYPE_MAP.get(返回)
        if ret_type is None:
            raise RustFFIError(f"不支持的返回类型: '{返回}'")
        func.restype = ret_type

        库._bound_functions[光明名] = func
        return func

    def 绑定字符串函数(self,
                     库: RustLibrary,
                     Rust函数名: str,
                     *参数类型: str) -> Callable:
        """绑定返回字符串的 Rust 函数（自动处理内存释放）

        Rust 侧需返回 *mut c_char，由本模块自动释放。

        参数:
            库: RustLibrary 实例
            Rust函数名: Rust 函数名
            *参数类型: 参数类型列表

        返回:
            可调用函数，返回 Python str
        """
        func = getattr(库.lib, Rust函数名, None)
        if func is None:
            raise RustFFIError(f"未找到 Rust 函数 '{Rust函数名}'")

        argtypes = []
        for t in 参数类型:
            ctype = TYPE_MAP.get(t)
            if ctype is None:
                raise RustFFIError(f"不支持的参数类型: '{t}'")
            argtypes.append(ctype)
        func.argtypes = argtypes
        func.restype = ctypes.c_void_p

        # 查找 Rust 的释放函数
        free_func = getattr(库.lib, f"{Rust函数名}_free", None)

        def wrapper(*args):
            ptr = func(*args)
            if not ptr:
                return ""
            try:
                result = ctypes.cast(ptr, ctypes.c_char_p).value
                return result.decode("utf-8") if result else ""
            finally:
                if free_func:
                    free_func(ctypes.c_void_p(ptr))
                else:
                    # 尝试使用 libc free
                    try:
                        libc = ctypes.cdll.LoadLibrary("libc.so.6")
                        libc.free(ctypes.c_void_p(ptr))
                    except Exception:
                        pass  # 无法释放，由 Rust 侧管理

        库._bound_functions[Rust函数名] = wrapper
        return wrapper

    def 绑定结构体(self, 库: RustLibrary, 结构体名: str, 字段: List[Tuple[str, str]]) -> type:
        """绑定 Rust 结构体（通过 ctypes 模拟 repr(C) 布局）

        参数:
            库: RustLibrary 实例
            结构体名: 结构体名称
            字段: 字段列表，每项为 (字段名, 光明类型名)

        返回:
            ctypes.Structure 子类
        """
        fields_list = []
        for field_name, field_type in 字段:
            ctype = TYPE_MAP.get(field_type)
            if ctype is None:
                raise RustFFIError(f"不支持的字段类型: '{field_type}'")
            fields_list.append((field_name, ctype))

        struct_class = type(结构体名, (ctypes.Structure,), {"_fields_": fields_list})
        return struct_class

    def 绑定数组函数(self,
                    库: RustLibrary,
                    Rust函数名: str,
                    元素类型: str,
                    返回计数类型: str = "整数") -> Callable:
        """绑定返回数组的 Rust 函数

        Rust 侧返回 (*mut T, usize) 或类似模式。
        需要 Rust 侧提供对应的释放函数 {函数名}_free。

        参数:
            库: RustLibrary 实例
            Rust函数名: Rust 函数名
            元素类型: 数组元素的光明类型名
            返回计数类型: 返回数组长度的类型名

        返回:
            可调用函数，返回 Python list
        """
        func = getattr(库.lib, Rust函数名, None)
        if func is None:
            raise RustFFIError(f"未找到 Rust 函数 '{Rust函数名}'")

        elem_ctype = TYPE_MAP.get(元素类型)
        if elem_ctype is None:
            raise RustFFIError(f"不支持的数组元素类型: '{元素类型}'")

        count_ctype = TYPE_MAP.get(返回计数类型, ctypes.c_int)
        func.restype = ctypes.c_void_p

        # 查找对应的数组长度函数
        len_func = getattr(库.lib, f"{Rust函数名}_len", None)
        if len_func:
            len_func.restype = count_ctype
            len_func.argtypes = [ctypes.c_void_p]

        # 查找释放函数
        free_func = getattr(库.lib, f"{Rust函数名}_free", None)

        def wrapper(*args):
            ptr = func(*args)
            if not ptr:
                return []

            if len_func:
                count = len_func(ctypes.c_void_p(ptr))
            else:
                count = 0

            try:
                arr_ptr = ctypes.cast(ptr, ctypes.POINTER(elem_ctype))
                return [arr_ptr[i] for i in range(count)]
            finally:
                if free_func:
                    free_func(ctypes.c_void_p(ptr))

        库._bound_functions[Rust函数名] = wrapper
        return wrapper

    def 获取库(self, 别名: str) -> Optional[RustLibrary]:
        """获取已加载的 Rust 库"""
        return self._libraries.get(别名)

    def 列出库(self) -> Dict[str, RustLibrary]:
        """列出所有已加载的 Rust 库"""
        return dict(self._libraries)

    def 释放库(self, 别名: str) -> bool:
        """释放已加载的 Rust 库"""
        if 别名 in self._libraries:
            del self._libraries[别名]
            return True
        return False

    # ==================== 内部方法 ====================

    def _find_lib_path(self, 路径: str) -> str:
        """在目标目录和系统路径中查找共享库"""
        basename = os.path.basename(路径)

        # 常见 Rust 项目 target 目录
        search_paths = [
            "/usr/lib",
            "/usr/local/lib",
            "/opt/homebrew/lib",
            "/lib",
        ]

        # 尝试在常见的 Rust 构建目录中查找
        cwd = os.getcwd()
        rust_targets = [
            os.path.join(cwd, "target", "release"),
            os.path.join(cwd, "target", "debug"),
            os.path.join(os.path.dirname(cwd), "target", "release"),
            os.path.join(os.path.dirname(cwd), "target", "debug"),
        ]
        search_paths = rust_targets + search_paths

        for sp in search_paths:
            if not os.path.isdir(sp):
                continue
            full_path = os.path.join(sp, basename)
            if os.path.exists(full_path):
                return full_path

            # 尝试 lib 前缀
            lib_name = f"lib{basename}"
            lib_path = os.path.join(sp, lib_name)
            if os.path.exists(lib_path):
                return lib_path

        raise RustFFIError(f"无法在系统路径或 target 目录中找到 Rust 库 '{路径}'")

    def 字符串转字节(self, 文本: str) -> bytes:
        """将光明字符串转为 C 字符串字节"""
        return 文本.encode("utf-8")

    def 字节转字符串(self, 字节: bytes) -> str:
        """将 C 字符串字节转为光明字符串"""
        return 字节.decode("utf-8")