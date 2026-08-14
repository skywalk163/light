"""
duanpub 标准库包加载器

职责：
1. 将段言 `导入 标准XXX` / `导入 XXX` 路由到正确的 duanpub 包
2. 对已有 Python 实现的包（P0），桥接到现有 stdlib
3. 对需新建的包（P1），返回包元数据供后续桥接模块使用
4. 对纯 duanpub 包（P2），返回源码路径供编译器加载

使用方式：
    from stdlib.duanpub import resolve_import, get_package_info, list_packages

    # 解析导入名
    info = resolve_import("标准文件系统")  # → 返回文件系统包元数据
    info = resolve_import("文件系统")      # 同上

    # 获取包信息
    pkg = get_package_info("JSON")  # → 返回 JSON 包元数据

    # 列出所有包
    all_pkgs = list_packages()
"""

import os
import sys
from pathlib import Path

# 导入自动生成的索引
try:
    from .__index__ import PACKAGES, IMPORT_MAP, CATEGORIES, PRIORITY, TOTAL_PACKAGES
except ImportError:
    # 索引尚未生成，提供空壳
    PACKAGES = {}
    IMPORT_MAP = {}
    CATEGORIES = {}
    PRIORITY = {}
    TOTAL_PACKAGES = 0


# =============================================================================
# 路径解析
# =============================================================================

# duanpub 根目录：优先使用环境变量，其次尝试默认路径
_DUANPUB_ROOT = os.environ.get('DUANPUB_ROOT', r'C:\dumatework\duanpub')

# stdlib 根目录（段言编译器的标准库）
_STDLIB_ROOT = Path(__file__).parent.parent  # stdlib/duanpub/ → stdlib/


def get_duanpub_root() -> str:
    """返回 duanpub 根目录路径"""
    return _DUANPUB_ROOT


def get_package_path(pkg_name: str) -> str | None:
    """返回 duanpub 包的物理路径"""
    pkg = PACKAGES.get(pkg_name)
    if not pkg:
        return None
    return os.path.join(_DUANPUB_ROOT, pkg['path'])


def get_source_path(pkg_name: str) -> str | None:
    """返回 duanpub 包的源.duan 文件路径"""
    pkg_path = get_package_path(pkg_name)
    if not pkg_path:
        return None
    src_path = os.path.join(pkg_path, '源.duan')
    return src_path if os.path.exists(src_path) else None


# =============================================================================
# 导入解析
# =============================================================================

def resolve_import(import_name: str) -> dict | None:
    """
    解析段言导入名，返回包元数据。

    支持的导入名格式：
    - "文件系统"      → 直接匹配 duanpub 包名
    - "标准文件系统"   → 去掉"标准"前缀后匹配
    - "JSON"          → 直接匹配

    返回:
        包元数据字典，或 None（未找到）
    """
    if not import_name:
        return None

    # 1. 直接匹配
    if import_name in PACKAGES:
        return PACKAGES[import_name]

    # 2. 通过 IMPORT_MAP 查找（含"标准"前缀的变体）
    pkg_name = IMPORT_MAP.get(import_name)
    if pkg_name and pkg_name in PACKAGES:
        return PACKAGES[pkg_name]

    # 3. 去掉"标准"前缀后重试
    if import_name.startswith('标准'):
        bare_name = import_name[2:]
        if bare_name in PACKAGES:
            return PACKAGES[bare_name]

    return None


def get_package_info(pkg_name: str) -> dict | None:
    """获取指定包的完整元数据"""
    return PACKAGES.get(pkg_name)


def list_packages(category: str = None, priority: str = None) -> list[str]:
    """
    列出包名。

    Args:
        category: 按分类过滤（如 'dev', 'net', 'database'）
        priority: 按优先级过滤（'P0', 'P1', 'P2'）

    Returns:
        包名列表
    """
    if category and priority:
        return [name for name, info in PACKAGES.items()
                if info['category'] == category and info['priority'] == priority]
    elif category:
        return CATEGORIES.get(category, [])
    elif priority:
        return PRIORITY.get(priority, [])
    return list(PACKAGES.keys())


# =============================================================================
# 桥接：P0 包路由到现有 stdlib Python 实现
# =============================================================================

# P0 包名 → duanpub 桥接模块名映射
# 这些包已有 Python 桥接实现，导入时路由到 stdlib/duanpub/ 下的桥接模块
# 桥接模块封装 Python 标准库，提供中文名 API
_STDLIB_BRIDGE = {
    # ---- P0: 核心包 ----
    '文件系统':   '文件系统',     # 桥接: stdlib/duanpub/文件系统.py → os/shutil
    'JSON':       'JSON',         # 桥接: stdlib/duanpub/JSON.py → json
    'CSV':        'CSV',          # 桥接: stdlib/duanpub/CSV.py → csv
    '正则表达式': '正则表达式',   # 桥接: stdlib/duanpub/正则表达式.py → re
    '日期时间':   '日期时间',     # 桥接: stdlib/duanpub/日期时间.py → datetime/time
    '数学运算':   '数学运算',     # 桥接: stdlib/duanpub/数学运算.py → math
    '加密':       '加密',         # 桥接: stdlib/duanpub/加密.py → hashlib/hmac
    # ---- P1: 高频包 ----
    'HTTP客户端': 'HTTP客户端',   # 桥接: stdlib/duanpub/HTTP客户端.py → urllib.request
    'SQLite':     'SQLite',       # 桥接: stdlib/duanpub/SQLite.py → sqlite3
    'Socket':     'Socket',       # 桥接: stdlib/duanpub/Socket.py → socket
    # ---- 系统工具 ----
    '线程':       '线程',         # 桥接: stdlib/duanpub/线程.py → threading
    '进程管理':   '进程管理',     # 桥接: stdlib/duanpub/进程管理.py → subprocess
    '环境变量':   '环境变量',     # 桥接: stdlib/duanpub/环境变量.py → os.environ
    '系统信息':   '系统信息',     # 桥接: stdlib/duanpub/系统信息.py → platform
    '路径处理':   '路径处理',     # 桥接: stdlib/duanpub/路径处理.py → os.path
    '网络工具':   '网络工具',     # 桥接: stdlib/duanpub/网络工具.py → ipaddress/socket
    '随机数':     '随机数',       # 桥接: stdlib/duanpub/随机数.py → random
    '缓存系统':   '缓存系统',     # 桥接: stdlib/duanpub/缓存系统.py → functools
    '连接池':     '连接池',       # 桥接: stdlib/duanpub/连接池.py → queue
    # ---- 数据结构 ----
    '数据结构':   '数据结构',     # 桥接: stdlib/duanpub/数据结构.py → collections
    '集合扩展':   '集合扩展',     # 桥接: stdlib/duanpub/集合扩展.py → itertools
    '排序与搜索': '排序与搜索',   # 桥接: stdlib/duanpub/排序与搜索.py → bisect/heapq
    '算法工具':   '算法工具',     # 桥接: stdlib/duanpub/算法工具.py → heapq
    # ---- 编码与压缩 ----
    '二进制编码': '二进制编码',   # 桥接: stdlib/duanpub/二进制编码.py → base64
    '压缩算法':   '压缩算法',     # 桥接: stdlib/duanpub/压缩算法.py → gzip/zlib
    # ---- 字符串与类型 ----
    '字符串处理': '字符串处理',   # 桥接: stdlib/duanpub/字符串处理.py → builtins
    '类型工具':   '类型工具',     # 桥接: stdlib/duanpub/类型工具.py → builtins
    '错误处理':   '错误处理',     # 桥接: stdlib/duanpub/错误处理.py → builtins
    # ---- 数值与统计 ----
    '数值计算':   '数值计算',     # 桥接: stdlib/duanpub/数值计算.py → math
    '统计分析':   '统计分析',     # 桥接: stdlib/duanpub/统计分析.py → statistics
    # ---- 安全与加密 ----
    '哈希':       '哈希',         # 桥接: stdlib/duanpub/哈希.py → hashlib
    '加密算法':   '加密算法',     # 桥接: stdlib/duanpub/加密算法.py → hashlib
    '密码哈希':   '密码哈希',     # 桥接: stdlib/duanpub/密码哈希.py → hashlib
    '证书':       '证书',         # 桥接: stdlib/duanpub/证书.py → ssl
    # ---- 异步与并发 ----
    '事件驱动':   '事件驱动',     # 桥接: stdlib/duanpub/事件驱动.py → asyncio
    '协程':       '协程',         # 桥接: stdlib/duanpub/协程.py → asyncio
    '异步运行时': '异步运行时',   # 桥接: stdlib/duanpub/异步运行时.py → asyncio
    '并行计算':   '并行计算',     # 桥接: stdlib/duanpub/并行计算.py → concurrent.futures
    '迭代器工具': '迭代器工具',   # 桥接: stdlib/duanpub/迭代器工具.py → itertools
    # ---- 队列与消息 ----
    '任务队列':   '任务队列',     # 桥接: stdlib/duanpub/任务队列.py → queue
    '消息队列':   '消息队列',     # 桥接: stdlib/duanpub/消息队列.py → queue
    # ---- 网络协议 ----
    'URL解析':    'URL解析',      # 桥接: stdlib/duanpub/URL解析.py → urllib.parse
    '邮件':       '邮件',         # 桥接: stdlib/duanpub/邮件.py → smtplib
    # ---- 数据格式 ----
    '数据导入导出': '数据导入导出', # 桥接: stdlib/duanpub/数据导入导出.py → csv/json
    '文件上传':   '文件上传',     # 桥接: stdlib/duanpub/文件上传.py → cgi
    # ---- 框架工具 ----
    '日志系统':   '日志系统',     # 桥接: stdlib/duanpub/日志系统.py → logging
    '命令行参数': '命令行参数',   # 桥接: stdlib/duanpub/命令行参数.py → argparse
    '性能分析':   '性能分析',     # 桥接: stdlib/duanpub/性能分析.py → time
    '模板渲染':   '模板渲染',     # 桥接: stdlib/duanpub/模板渲染.py → string.Template
    '日期序列':   '日期序列',     # 桥接: stdlib/duanpub/日期序列.py → datetime
    # ---- 框架库 ----
    '单元测试框架': '单元测试框架', # 桥接: stdlib/duanpub/单元测试框架.py → unittest
    '配置管理':   '配置管理',     # 桥接: stdlib/duanpub/配置管理.py → configparser
    'HTTP服务端': 'HTTP服务端',   # 桥接: stdlib/duanpub/HTTP服务端.py → http.server
}


def get_stdlib_bridge(pkg_name: str) -> str | None:
    """
    对于 P0 包，返回对应的 Python/stdlib 模块名。
    段言编译器代码生成器可以用此映射生成 `import <python_module>` 语句。

    Returns:
        Python 模块名，或 None（无桥接）
    """
    return _STDLIB_BRIDGE.get(pkg_name)


def is_p0_package(pkg_name: str) -> bool:
    """判断是否为 P0 包（已有 stdlib 实现）"""
    info = PACKAGES.get(pkg_name)
    return info is not None and info.get('priority') == 'P0'


def is_p1_package(pkg_name: str) -> bool:
    """判断是否为 P1 包（需新建 Python 桥接）"""
    info = PACKAGES.get(pkg_name)
    return info is not None and info.get('priority') == 'P1'


# =============================================================================
# 依赖解析
# =============================================================================

def get_dependencies(pkg_name: str) -> list[str]:
    """获取包的直接依赖列表"""
    info = PACKAGES.get(pkg_name)
    if not info:
        return []
    return info.get('dependencies', [])


def resolve_dependency_chain(pkg_name: str, _visited: set = None) -> list[str]:
    """
    解析包的完整依赖链（递归）。

    Returns:
        按加载顺序排列的依赖包名列表（不含 pkg_name 自身）
    """
    if _visited is None:
        _visited = set()

    if pkg_name in _visited:
        return []  # 循环依赖保护

    _visited.add(pkg_name)

    direct_deps = get_dependencies(pkg_name)
    result = []

    for dep in direct_deps:
        if dep not in _visited:
            result.extend(resolve_dependency_chain(dep, _visited))
            if dep not in result:
                result.append(dep)

    return result


# =============================================================================
# 函数查询
# =============================================================================

def get_functions(pkg_name: str) -> list[str]:
    """获取包的公开函数列表"""
    info = PACKAGES.get(pkg_name)
    if not info:
        return []
    return info.get('functions', [])


def search_functions(keyword: str) -> list[tuple[str, str]]:
    """
    全局搜索函数：在所有包中搜索包含关键词的函数。

    Returns:
        [(包名, 函数名), ...]
    """
    results = []
    for pkg_name, info in PACKAGES.items():
        for func in info.get('functions', []):
            if keyword in func:
                results.append((pkg_name, func))
    return results


# =============================================================================
# 统计信息
# =============================================================================

def get_stats() -> dict:
    """返回 duanpub 生态统计信息"""
    return {
        'total_packages': TOTAL_PACKAGES,
        'total_functions': sum(p.get('function_count', 0) for p in PACKAGES.values()),
        'total_ffi': sum(p.get('ffi_count', 0) for p in PACKAGES.values()),
        'p0_count': len(PRIORITY.get('P0', [])),
        'p1_count': len(PRIORITY.get('P1', [])),
        'p2_count': len(PRIORITY.get('P2', [])),
        'categories': {cat: len(pkgs) for cat, pkgs in CATEGORIES.items()},
    }


# =============================================================================
# 调试/自省
# =============================================================================

def print_summary():
    """打印 duanpub 生态摘要（用于调试）"""
    stats = get_stats()
    print(f"duanpub 包索引摘要")
    print(f"=" * 50)
    print(f"总包数:   {stats['total_packages']}")
    print(f"总函数数: {stats['total_functions']}")
    print(f"总FFI数:  {stats['total_ffi']}")
    print(f"")
    print(f"按优先级:")
    print(f"  P0 (已有stdlib): {stats['p0_count']} 包")
    print(f"  P1 (需新建):     {stats['p1_count']} 包")
    print(f"  P2 (其他):       {stats['p2_count']} 包")
    print(f"")
    print(f"按分类:")
    for cat, count in sorted(stats['categories'].items()):
        print(f"  {cat}: {count} 包")


# =============================================================================
# 友好错误提示：访问不存在的属性时给出迁移建议
# =============================================================================

# 常见 stdlib 函数名 → duanpub 包名映射（用于友好提示）
_FUNCTION_TO_PACKAGE = {
    '读取文件': '文件系统', '写入文件': '文件系统', '文件存在': '文件系统',
    '解析JSON': 'JSON', '生成JSON': 'JSON',
    '读取CSV': 'CSV', '写入CSV': 'CSV',
    '匹配': '正则表达式', '搜索': '正则表达式', '替换': '正则表达式',
    '当前时间': '日期时间', '格式化时间': '日期时间',
    '排序': None, '去重': None,  # 核心动词，无需导入
}


def __getattr__(name):
    """
    模块级 __getattr__：当用户直接访问 stdlib.duanpub.<name> 失败时，
    提供友好提示，引导用户正确导入。
    """
    # 检查是否是已知的 stdlib 函数名
    pkg = _FUNCTION_TO_PACKAGE.get(name)
    if pkg:
        raise AttributeError(
            f"'{name}' 是 duanpub 包 '{pkg}' 中的函数。\n"
            f"请在段言代码中使用：导入 {pkg}\n"
            f"然后调用：{pkg}.{name}(...)"
        )

    # 检查是否是 duanpub 包名（用户可能想获取包信息）
    if name in PACKAGES:
        raise AttributeError(
            f"'{name}' 是 duanpub 包名，不能直接访问。\n"
            f"请使用 get_package_info('{name}') 获取包元数据，\n"
            f"或在段言代码中使用：导入 {name}"
        )

    # 通用提示
    raise AttributeError(
        f"模块 'stdlib.duanpub' 没有属性 '{name}'。\n"
        f"可用函数：resolve_import, get_package_info, list_packages, "
        f"get_functions, search_functions, get_stdlib_bridge\n"
        f"可用包列表：list_packages()"
    )


if __name__ == '__main__':
    print_summary()
