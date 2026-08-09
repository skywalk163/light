"""
lightpub 标准库包加载器

职责：
1. 将光明 `导入 标准XXX` / `导入 XXX` 路由到正确的 lightpub 包
2. 对已有 Python 实现的包（P0），桥接到现有 stdlib
3. 对需新建的包（P1），返回包元数据供后续桥接模块使用
4. 对纯 lightpub 包（P2），返回源码路径供编译器加载

使用方式：
    from stdlib.lightpub import resolve_import, get_package_info, list_packages

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

# lightpub 根目录：优先使用环境变量，其次尝试默认路径
_LIGHTPUB_ROOT = os.environ.get('LIGHTPUB_ROOT', r'C:\dumatework\lightpub')

# stdlib 根目录（光明编译器的标准库）
_STDLIB_ROOT = Path(__file__).parent.parent  # stdlib/lightpub/ → stdlib/


def get_lightpub_root() -> str:
    """返回 lightpub 根目录路径"""
    return _LIGHTPUB_ROOT


def get_package_path(pkg_name: str) -> str | None:
    """返回 lightpub 包的物理路径"""
    pkg = PACKAGES.get(pkg_name)
    if not pkg:
        return None
    return os.path.join(_LIGHTPUB_ROOT, pkg['path'])


def get_source_path(pkg_name: str) -> str | None:
    """返回 lightpub 包的源.light 文件路径"""
    pkg_path = get_package_path(pkg_name)
    if not pkg_path:
        return None
    src_path = os.path.join(pkg_path, '源.light')
    return src_path if os.path.exists(src_path) else None


# =============================================================================
# 导入解析
# =============================================================================

def resolve_import(import_name: str) -> dict | None:
    """
    解析光明导入名，返回包元数据。

    支持的导入名格式：
    - "文件系统"      → 直接匹配 lightpub 包名
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

# P0 包名 → stdlib Python 模块名映射
# 这些包已有 Python 实现，导入时直接路由到 stdlib
_STDLIB_BRIDGE = {
    '文件系统':   '文件系统',     # stdlib/文件系统.py
    'JSON':       'JSON',         # stdlib/JSON.py（含中文函数名）
    'CSV':        'csv',          # Python 标准库 csv（无中文函数名，直接透传）
    '正则表达式': '正则表达式',   # stdlib/正则表达式.py（含中文函数名）
    '日期时间':   '日期时间',     # stdlib/日期时间.py（含中文函数名）
}


def get_stdlib_bridge(pkg_name: str) -> str | None:
    """
    对于 P0 包，返回对应的 Python/stdlib 模块名。
    光明编译器代码生成器可以用此映射生成 `import <python_module>` 语句。

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
    """返回 lightpub 生态统计信息"""
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
    """打印 lightpub 生态摘要（用于调试）"""
    stats = get_stats()
    print(f"lightpub 包索引摘要")
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


if __name__ == '__main__':
    print_summary()
