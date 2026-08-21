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

# P0 包名 → Python 模块名映射。
#
# 2026-08-21 缩表：这里原有 53 条，实测盘点后砍到 4 条。砍掉的不是「指向不存在
# 的模块」——那 53 个桥接文件全都在。砍掉的是**永远查不到的条目**：
#
#   * 本表唯一的调用者是 get_stdlib_bridge()，而它只在
#     src/code_generator.py 的 **P0 分支**里被调用（见该文件
#     _resolve_lightpub_import）。P1/P2 由那个函数统一按
#     「stdlib/ 根目录同名模块优先，否则 stdlib.lightpub.<包名>」处理，
#     根本不看本表。原表 53 条里有 49 条 priority≠P0，等于摆着不生效。
#   * 另有 5 条（加密 / 日期时间 / 数学运算 / 单元测试框架 / 配置管理）连
#     PACKAGES 都没有——它们在外部数据源 C:\dumatework\lightpub\packages\ 里
#     没有对应包，所以 resolve_import() 直接返回 None，本表更没机会被查。
#     其中 `导入 加密` / `导入 日期时间` 目前能用纯属巧合：stdlib/加密.py 与
#     stdlib/日期时间.py 恰好存在，走的是恒等映射那条路。
#     `导入 数学运算` / `导入 单元测试框架` / `导入 配置管理` 则确实不可用，
#     尽管 stdlib/lightpub/ 下有它们的桥接模块——**要启用得先在 lightpub
#     数据源里补包，再重跑 tools/gen_lightpub_index.py**，不能靠手编元数据。
#
# 保留 4 条 P0 的意义也仅在于「显式声明」：P0 分支在本表查不到时会退回
# `return real_name`，结果与恒等映射一致。所以往表里加非 P0 条目**不会有任何
# 效果**，别再加了（tools/lightpub_bridge.py --update-init 已改为只写 P0）。
# 一致性由 tests/unit/test_lightpub_bridge_table.py 守住。
_STDLIB_BRIDGE = {
    # ---- P0: 核心包（唯一会被 get_stdlib_bridge 查到的一档）----
    '文件系统':   '文件系统',     # 桥接: stdlib/lightpub/文件系统.py → os/shutil
    'JSON':       'JSON',         # 桥接: stdlib/lightpub/JSON.py → json
    'CSV':        'CSV',          # 桥接: stdlib/lightpub/CSV.py → csv
    '正则表达式': '正则表达式',   # 桥接: stdlib/lightpub/正则表达式.py → re
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


# =============================================================================
# 友好错误提示：访问不存在的属性时给出迁移建议
# =============================================================================

# 常见 stdlib 函数名 → lightpub 包名映射（用于友好提示）
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
    模块级 __getattr__：当用户直接访问 stdlib.lightpub.<name> 失败时，
    提供友好提示，引导用户正确导入。
    """
    # 检查是否是已知的 stdlib 函数名
    pkg = _FUNCTION_TO_PACKAGE.get(name)
    if pkg:
        raise AttributeError(
            f"'{name}' 是 lightpub 包 '{pkg}' 中的函数。\n"
            f"请在光明代码中使用：导入 {pkg}\n"
            f"然后调用：{pkg}.{name}(...)"
        )

    # 检查是否是 lightpub 包名（用户可能想获取包信息）
    if name in PACKAGES:
        raise AttributeError(
            f"'{name}' 是 lightpub 包名，不能直接访问。\n"
            f"请使用 get_package_info('{name}') 获取包元数据，\n"
            f"或在光明代码中使用：导入 {name}"
        )

    # 通用提示
    raise AttributeError(
        f"模块 'stdlib.lightpub' 没有属性 '{name}'。\n"
        f"可用函数：resolve_import, get_package_info, list_packages, "
        f"get_functions, search_functions, get_stdlib_bridge\n"
        f"可用包列表：list_packages()"
    )


if __name__ == '__main__':
    print_summary()
