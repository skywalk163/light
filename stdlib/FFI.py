"""
光明 C FFI 运行时模块
提供动态库加载、函数调用、类型转换等 FFI 功能
"""

import ctypes
import os
import platform
from typing import Any, Dict, Optional, List, Tuple


class FFILibrary:
    """FFI 动态库包装器"""

    def __init__(self, path: str):
        self._path = path
        self._handle = None
        self._functions: Dict[str, Any] = {}

    def load(self) -> 'FFILibrary':
        """加载动态库"""
        self._handle = ctypes.CDLL(self._path)
        return self

    def get_function(self, name: str) -> Any:
        """获取库中的函数"""
        if name not in self._functions:
            self._functions[name] = getattr(self._handle, name)
        return self._functions[name]

    def declare_function(self, name: str, arg_types: List[Any], restype: Any) -> Any:
        """声明并设置函数签名"""
        func = self.get_function(name)
        func.argtypes = arg_types if arg_types else None
        func.restype = restype
        return func

    def close(self):
        """关闭动态库句柄"""
        self._handle = None
        self._functions.clear()



class FFIManager:
    """FFI 管理器：管理所有加载的动态库"""

    def __init__(self):
        self._libraries: Dict[str, FFILibrary] = {}

    def load_library(self, path: str, alias: str) -> FFILibrary:
        """加载动态库并注册别名"""
        lib = FFILibrary(path)
        lib.load()
        self._libraries[alias] = lib
        return lib

    def get_library(self, alias: str) -> Optional[FFILibrary]:
        """获取已加载的库"""
        return self._libraries.get(alias)

    def close_all(self):
        """关闭所有已加载的库"""
        for lib in self._libraries.values():
            lib.close()
        self._libraries.clear()


# 全局 FFI 管理器
_ffi_manager = FFIManager()

# 用户自定义类型注册表（struct/union/funcptr/typedef 等）
# 运行时通过 注册类型() 注册，供 获取类型() 查找
_type_registry: Dict[str, Any] = {}


def 加载库(路径: str, 别名: str) -> FFILibrary:
    """加载动态库：加载库(路径, 别名)"""
    return _ffi_manager.load_library(路径, 别名)


def 获取库(别名: str) -> Optional[FFILibrary]:
    """获取已加载的库：获取库(别名)"""
    return _ffi_manager.get_library(别名)


# =============================================================================
# 类型映射
# =============================================================================

FFI_TYPE_MAP = {
    '整数': ctypes.c_int,
    '小数': ctypes.c_double,
    '浮数': ctypes.c_double,
    '文本': ctypes.c_char_p,
    '串': ctypes.c_char_p,
    '布尔': ctypes.c_bool,
    '空': ctypes.c_void_p,
    '数': ctypes.c_double,
    '无': None,
    'int': ctypes.c_int,
    'double': ctypes.c_double,
    'float': ctypes.c_float,
    'char': ctypes.c_char,
    'void': None,
    'long': ctypes.c_long,
    'unsigned': ctypes.c_uint,
    'size_t': ctypes.c_size_t,
}


def 注册类型(名称: str, 类型: Any):
    """注册用户自定义类型（struct/union/funcptr/typedef）供 获取类型 查找"""
    _type_registry[名称] = 类型


def 获取类型(类型名: str) -> Any:
    """获取对应的 ctypes 类型。优先查找 FFI_TYPE_MAP，再查找用户自定义类型注册表，
    最后尝试通过 eval 解析全局作用域中的类型名（如 struct/union 类名）。
    """
    # 1) 基本类型映射
    if 类型名 in FFI_TYPE_MAP:
        return FFI_TYPE_MAP[类型名]
    # 2) 用户自定义类型注册表
    if 类型名 in _type_registry:
        return _type_registry[类型名]
    # 3) void* 作为默认回退
    return ctypes.c_void_p


def 获取类型或空(类型名: str) -> Optional[Any]:
    """获取类型，找不到时返回 None 而非默认值"""
    if 类型名 in FFI_TYPE_MAP:
        return FFI_TYPE_MAP[类型名]
    if 类型名 in _type_registry:
        return _type_registry[类型名]
    return None


def 声明函数(库别名: str, 函数名: str, 参数类型: List[str], 返回类型: str) -> Any:
    """声明外部函数"""
    lib = _ffi_manager.get_library(库别名)
    if not lib:
        raise ValueError(f"库 '{库别名}' 未加载")
    arg_types = [获取类型(t) for t in 参数类型]
    restype = 获取类型(返回类型)
    return lib.declare_function(函数名, arg_types, restype)


def 调用函数(库别名: str, 函数名: str, 参数: List[Any]) -> Any:
    """调用外部函数"""
    lib = _ffi_manager.get_library(库别名)
    if not lib:
        raise ValueError(f"库 '{库别名}' 未加载")
    func = lib.get_function(函数名)
    return func(*参数)


def 编码文本(s: str) -> bytes:
    """将文本编码为字节串"""
    if isinstance(s, str):
        return s.encode('utf-8')
    return s


def 解码文本(b) -> str:
    """将字节串解码为文本"""
    if b is None:
        return ''
    if isinstance(b, bytes):
        return b.decode('utf-8')
    return str(b)


def 内存分配(大小: int) -> Any:
    """分配内存块"""
    return ctypes.create_string_buffer(大小)


def 内存释放(ptr: Any):
    """释放内存（Python 自动管理）"""
    pass


def 取地址(变量) -> Any:
    """获取变量的指针"""
    if isinstance(变量, ctypes.Structure):
        return ctypes.byref(变量)
    if isinstance(变量, (ctypes.c_int, ctypes.c_double, ctypes.c_float)):
        return ctypes.byref(变量)
    return 变量


def 创建结构体(结构体类: Any, **字段值) -> Any:
    """创建结构体实例"""
    instance = 结构体类()
    for 字段名, 值 in 字段值.items():
        setattr(instance, 字段名, 值)
    return instance


def 获取字段(结构体实例: Any, 字段名: str) -> Any:
    """获取结构体字段值"""
    return getattr(结构体实例, 字段名)


def 设置字段(结构体实例: Any, 字段名: str, 值: Any):
    """设置结构体字段值"""
    setattr(结构体实例, 字段名, 值)


def 创建回调(回调类型, 回调函数) -> Any:
    """创建 C 回调函数"""
    return 回调类型(回调函数)


# =============================================================================
# 指针/数组操作（第二阶段）
# =============================================================================

def 取地址(变量) -> Any:
    """获取变量的指针（ctypes 指针）"""
    if isinstance(变量, ctypes.Structure):
        return ctypes.pointer(变量)
    if isinstance(变量, ctypes.c_int):
        return ctypes.pointer(变量)
    if isinstance(变量, ctypes.c_double):
        return ctypes.pointer(变量)
    if isinstance(变量, ctypes.c_float):
        return ctypes.pointer(变量)
    if isinstance(变量, ctypes.c_char):
        return ctypes.pointer(变量)
    return 变量


def 解引用(指针) -> Any:
    """解引用指针获取值"""
    if hasattr(指针, 'contents'):
        return 指针.contents.value if hasattr(指针.contents, 'value') else 指针.contents
    if isinstance(指针, ctypes.Array):
        return 指针[0]
    return 指针


def 指针偏移(指针, 偏移量: int) -> Any:
    """指针偏移：返回指针 + 偏移量 的地址"""
    if isinstance(指针, ctypes.Array):
        return ctypes.cast(ctypes.addressof(指针) + 偏移量 * ctypes.sizeof(指针._type_), ctypes.POINTER(指针._type_))
    return 指针


def 创建数组(类型, 大小: int) -> Any:
    """创建 C 类型数组，支持字符串类型名或 ctypes 类对象"""
    if isinstance(类型, str):
        ctype = 获取类型(类型)
    else:
        ctype = 类型
    return (ctype * 大小)()


def 设置数组(数组, 索引: int, 值: Any):
    """设置数组元素值"""
    数组[索引] = 值


def 分配内存(大小: int) -> Any:
    """分配内存块"""
    return ctypes.create_string_buffer(大小)


def 释放内存(指针):
    """释放内存"""
    pass


def 设指针值(指针, 值):
    """通过指针写入值"""
    if hasattr(指针, 'contents'):
        if hasattr(指针.contents, 'value'):
            try:
                指针.contents.value = 值
            except TypeError:
                指针.contents = 值
        else:
            指针.contents = 值
    elif isinstance(指针, ctypes.Array):
        指针[0] = 值


# =============================================================================
# 错误处理（第二阶段）
# =============================================================================

_last_ffi_error = None


def 获取FFI错误() -> str:
    """获取最后一次 FFI 错误消息"""
    global _last_ffi_error
    if _last_ffi_error:
        return str(_last_ffi_error)
    return ''


def _set_ffi_error(error):
    """设置 FFI 错误（内部使用）"""
    global _last_ffi_error
    _last_ffi_error = error


def 获取系统错误码() -> int:
    """获取系统 errno"""
    return ctypes.get_errno()


def 设系统错误码(值: int):
    """设置系统 errno"""
    ctypes.set_errno(值)


def 关闭所有库():
    """关闭所有已加载的库"""
    _ffi_manager.close_all()


# =============================================================================
# 第三阶段：回调/结构体传值/枚举/联合体/变长参数/跨平台路径
# =============================================================================

def 创建回调函数(回调类型, 光明函数):
    """创建C回调函数指针"""
    return 回调类型(光明函数)


def 创建结构体值(结构体类, **字段值):
    """创建结构体实例（用于按值传递）"""
    instance = 结构体类()
    for 字段名, 值 in 字段值.items():
        setattr(instance, 字段名, 值)
    return instance


def 创建枚举(枚举名: str, 值字典: Dict[str, int]) -> type:
    """动态创建C语言兼容的枚举类"""
    enum_type = type(枚举名, (), 值字典)
    return enum_type


def 创建联合体(联合体名: str, 字段列表: List[Tuple[str, Any]]) -> type:
    """动态创建C语言联合体类型"""
    class UnionType(ctypes.Union):
        _fields_ = 字段列表
    UnionType.__name__ = 联合体名
    return UnionType


def 解析库路径(平台映射: Dict[str, str]) -> str:
    """根据当前平台自动选择库文件路径"""
    current_platform = platform.system().lower()
    if current_platform == 'windows':
        plat_key = 'win'
    elif current_platform == 'darwin':
        plat_key = 'mac'
    elif current_platform == 'linux':
        plat_key = 'linux'
    else:
        plat_key = current_platform

    # 平台映射通常只写 win/linux/mac 三键。FreeBSD 等其它 ELF 系统按上面的 else
    # 分支会拿到 'freebsd'，三键里一个都匹配不上，最后 return 出一个空串——
    # 调用方拿到空路径去 load 库，报的错跟平台八竿子打不着。这里让它退到
    # 'linux' 键：同为 ELF + .so 命名约定，是这批系统上唯一说得通的选择。
    # 若映射里显式写了 'freebsd' 键，上面的精确匹配会先命中，这条不会生效。
    if plat_key not in 平台映射 and plat_key not in ('win', 'mac', 'linux'):
        if 'linux' in 平台映射:
            plat_key = 'linux'

    for key, path in 平台映射.items():

        if key.lower() == plat_key:
            if os.path.exists(path):
                return path
            # 尝试在常见库路径中查找
            search_paths = [path, os.path.join('/usr/lib', path), os.path.join('/usr/local/lib', path)]
            if plat_key == 'win':
                search_paths.extend([os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'System32', path)])
            for sp in search_paths:
                if os.path.exists(sp):
                    return sp
    
    return 平台映射.get(plat_key, '')


def 变长参数调用(库别名: str, 函数名: str, 固定参数: List[Any], 可变参数: List[Any]) -> Any:
    """调用变长参数函数"""
    lib = _ffi_manager.get_library(库别名)
    if not lib:
        raise ValueError(f"库 '{库别名}' 未加载")
    func = lib.get_function(函数名)
    all_args = list(固定参数) + list(可变参数)
    return func(*all_args)


def 获取平台() -> str:
    """获取当前平台标识"""
    return platform.system().lower()


def 查找库(库名: str) -> Optional[str]:
    """使用 ctypes.util.find_library 查找系统库"""
    try:
        from ctypes import util
        return util.find_library(库名)
    except (ImportError, AttributeError):
        return None


# 对原有 取地址 函数进行增强（支持结构体按值传递）
# 注意：原有的 取地址 函数在第194行已定义，这里覆盖
def 取地址增强(变量) -> Any:
    """获取变量的指针（增强版：支持结构体按值传递）"""
    if isinstance(变量, ctypes.Structure):
        return ctypes.pointer(变量)
    if isinstance(变量, ctypes.Union):
        return ctypes.pointer(变量)
    if isinstance(变量, (ctypes.c_int, ctypes.c_double, ctypes.c_float, ctypes.c_char)):
        return ctypes.pointer(变量)
    if isinstance(变量, ctypes.Array):
        return ctypes.cast(变量, ctypes.POINTER(变量._type_))
    return 变量


# 结构体操作辅助函数
def 结构体大小(结构体类) -> int:
    """获取结构体的大小（字节）"""
    return ctypes.sizeof(结构体类)


def 字段偏移(结构体类, 字段名: str) -> int:
    """获取结构体字段的偏移量"""
    return getattr(结构体类, 字段名).offset


def 结构体转字节(结构体实例) -> bytes:
    """将结构体序列化为字节串"""
    return bytes(结构体实例)


def 字节转结构体(数据: bytes, 结构体类) -> Any:
    """从字节串反序列化为结构体"""
    instance = 结构体类()
    ctypes.memmove(ctypes.addressof(instance), 数据, min(len(数据), ctypes.sizeof(结构体类)))
    return instance


# =============================================================================
# 第四阶段：回调生命周期/函指/位域/typedef/调试/预处理器
# =============================================================================

# 回调注册表 - 防止回调被GC回收
_callback_registry: Dict[str, Any] = {}
_callback_counter: int = 0


def 注册回调(名称: str, 回调对象: Any) -> str:
    """注册回调函数，防止被GC回收"""
    global _callback_counter
    _callback_counter += 1
    key = f"{名称}_{_callback_counter}"
    _callback_registry[key] = 回调对象
    return key


def 注销回调(键: str) -> bool:
    """注销回调函数"""
    if 键 in _callback_registry:
        del _callback_registry[键]
        return True
    return False


def 获取回调(键: str) -> Optional[Any]:
    """获取已注册的回调函数"""
    return _callback_registry.get(键)


def 列出回调() -> List[str]:
    """列出所有已注册的回调键"""
    return list(_callback_registry.keys())


def 清理回调():
    """清理所有已注册的回调"""
    _callback_registry.clear()


# =============================================================================
# 调试系统
# =============================================================================

_debug_config = {
    'enabled': False,
    'log_calls': False,
    'log_types': False,
    'trace_memory': False,
}
_debug_log: List[str] = []


def 设置调试(**kwargs):
    """设置FFI调试配置"""
    _debug_config.update(kwargs)


def 启用调试():
    """启用FFI调试"""
    _debug_config['enabled'] = True
    _debug_config['log_calls'] = True
    _debug_log.append('[FFI调试] 调试已启用')


def 禁用调试():
    """禁用FFI调试"""
    _debug_config['enabled'] = False
    _debug_log.append('[FFI调试] 调试已禁用')


def 获取日志() -> List[str]:
    """获取FFI调试日志"""
    return list(_debug_log)


def 清空日志():
    """清空FFI调试日志"""
    _debug_log.clear()


# =============================================================================
# 别名（对齐 STDLIB_VERB_ARITY 注册名）
# =============================================================================

def FFI调试():
    """FFI调试（别名）"""
    return 启用调试()


def FFI禁用调试():
    """FFI禁用调试（别名）"""
    return 禁用调试()


def FFI获取日志() -> List[str]:
    """FFI获取日志（别名）"""
    return 获取日志()


def _debug_log_call(函数名: str, 参数: tuple, 返回值: Any = None):
    """内部：记录函数调用"""
    if _debug_config['enabled'] and _debug_config['log_calls']:
        args_str = ', '.join(repr(a) for a in 参数)
        entry = f"[FFI调用] {函数名}({args_str})"
        if 返回值 is not None:
            entry += f" -> {repr(返回值)}"
        _debug_log.append(entry)


def _debug_log_type(类型名: str, 详情: str):
    """内部：记录类型信息"""
    if _debug_config['enabled'] and _debug_config['log_types']:
        _debug_log.append(f"[FFI类型] {类型名}: {详情}")


def _debug_log_memory(操作: str, 大小: int = 0):
    """内部：记录内存操作"""
    if _debug_config['enabled'] and _debug_config['trace_memory']:
        if 大小 > 0:
            _debug_log.append(f"[FFI内存] {操作}: {大小} bytes")
        else:
            _debug_log.append(f"[FFI内存] {操作}")


# =============================================================================
# 位域操作
# =============================================================================

def 位域设置(结构体实例, 字段名: str, 值: int):
    """设置位域字段的值"""
    setattr(结构体实例, 字段名, 值)


def 位域获取(结构体实例, 字段名: str) -> int:
    """获取位域字段的值"""
    return getattr(结构体实例, 字段名)


# =============================================================================
# 函数指针
# =============================================================================

def 创建函数指针(签名类型) -> type:
    """创建C函数指针类型"""
    return 签名类型


# =============================================================================
# 类型别名
# =============================================================================

def 创建类型别名(别名: str, 基础类型: Any) -> Any:
    """创建C类型别名（返回基础类型）"""
    return 基础类型


# =============================================================================
# 预处理器宏
# =============================================================================

_macro_definitions: Dict[str, str] = {}


def 定义宏(名称: str, 值: str):
    """定义C预处理器宏"""
    _macro_definitions[名称] = 值
    if _debug_config['enabled']:
        _debug_log.append(f"[FFI宏] {名称} = {值}")


def 获取宏(名称: str) -> Optional[str]:
    """获取宏的值"""
    return _macro_definitions.get(名称)


def 列出宏() -> Dict[str, str]:
    """列出所有已定义的宏"""
    return dict(_macro_definitions)


def 清理宏():
    """清理所有宏定义"""
    _macro_definitions.clear()