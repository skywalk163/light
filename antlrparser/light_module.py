"""
光明（Light）编程语言 - 模块解析器

实现功能：
1. 模块查找（搜索 .light 文件和目录模块）
2. 模块解析（使用 ANTLR 解析器）
3. 模块缓存（避免重复解析）
4. 搜索路径管理（当前目录 + DUAN_PATH 环境变量）
5. 目录模块（包）支持
6. 循环导入检测
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple

from light_ast import Module, ImportStatement, ExportStatement, SegmentDefinition


# =============================================================================
# 错误类型
# =============================================================================

class ModuleError(Exception):
    """模块相关错误基类"""
    pass


class ModuleNotFoundError(ModuleError):
    """模块未找到"""
    def __init__(self, module_name: str, search_paths: List[str]):
        self.module_name = module_name
        self.search_paths = search_paths
        message = f"模块未找到: '{module_name}'\n搜索路径:\n"
        for path in search_paths:
            message += f"  - {path}\n"
        super().__init__(message)


class ModuleCircularImportError(ModuleError):
    """循环导入错误"""
    def __init__(self, module_name: str, stack: List[str]):
        self.module_name = module_name
        self.stack = stack
        message = f"检测到循环导入: {' → '.join(stack)} → {module_name}"
        super().__init__(message)


# =============================================================================
# 模块解析器
# =============================================================================

class ModuleResolver:
    """模块解析器 - 查找和解析 .light 模块文件"""

    def __init__(self, search_paths: List[str] = None):
        """
        初始化模块解析器

        Args:
            search_paths: 模块搜索路径列表，None 表示使用默认路径
        """
        self.search_paths = search_paths or ['.']
        self.module_cache: Dict[str, Tuple[Module, str]] = {}  # name -> (ast, filepath)
        self._import_stack: List[str] = []  # 循环导入检测栈

    def set_search_paths(self, paths: List[str]):
        """设置搜索路径"""
        self.search_paths = paths

    def find_module_file(self, module_name: str, from_dir: str = None) -> str:
        """
        查找模块文件路径

        Args:
            module_name: 模块名（不含扩展名，支持包路径如 'math.utils'）
            from_dir: 发起导入的模块所在目录（用于相对查找）

        Returns:
            模块文件的绝对路径

        Raises:
            ModuleNotFoundError: 未找到模块
        """
        # 处理包路径（如 'math.utils'）
        parts = module_name.split('.')
        
        # 构建搜索目录列表
        search_dirs = []

        # 1. 从发起导入的模块目录查找
        if from_dir:
            search_dirs.append(from_dir)

        # 2. 从搜索路径查找
        search_dirs.extend(self.search_paths)

        # 3. 从环境变量 DUAN_PATH 查找
        light_path = os.environ.get('DUAN_PATH', '')
        if light_path:
            search_dirs.extend(light_path.split(os.pathsep))

        # 搜索
        searched = []
        for search_dir in search_dirs:
            search_path = Path(search_dir)
            if not search_path.is_absolute():
                search_path = Path.cwd() / search_path

            # 尝试查找文件模块
            module_file = f"{parts[-1]}.light"
            module_path = search_path.joinpath(*parts[:-1]) / module_file
            searched.append(str(module_path))

            if module_path.exists():
                return str(module_path.resolve())

            # 尝试查找目录模块（包）
            dir_module_path = search_path.joinpath(*parts) / "__模块__.light"
            searched.append(str(dir_module_path))

            if dir_module_path.exists():
                return str(dir_module_path.resolve())

        raise ModuleNotFoundError(module_name, searched)

    def load_module(self, module_name: str, from_dir: str = None) -> Tuple[Module, str]:
        """
        加载并解析模块

        Args:
            module_name: 模块名
            from_dir: 发起导入的模块目录

        Returns:
            (AST Module, 文件路径)

        Raises:
            ModuleNotFoundError: 未找到模块
            ModuleCircularImportError: 循环导入
        """
        # 缓存命中
        if module_name in self.module_cache:
            return self.module_cache[module_name]

        # 循环导入检测
        if module_name in self._import_stack:
            raise ModuleCircularImportError(module_name, self._import_stack + [module_name])

        # 查找文件
        filepath = self.find_module_file(module_name, from_dir)

        # 读取源码
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        # 解析（使用 ANTLR 解析器）
        from light_visitor import LightParser
        parser = LightParser()
        module_ast = parser.parse(source)
        if module_ast is None:
            errors = '\n'.join(parser.errors)
            raise ModuleError(f"解析模块 '{module_name}' 失败:\n{errors}")

        # 缓存
        self.module_cache[module_name] = (module_ast, filepath)

        return module_ast, filepath

    def resolve_import(self, import_stmt: ImportStatement, from_dir: str = None) -> Dict[str, object]:
        """
        解析导入语句，返回 {符号名: SegmentDefinition} 字典

        Args:
            import_stmt: 导入语句 AST
            from_dir: 发起导入的模块目录

        Returns:
            符号名到段落定义的映射
        """
        module_name = import_stmt.module
        if not module_name:
            raise ModuleError("导入语句缺少模块名")

        # 加载模块（load_module 内部自行处理循环检测和缓存）
        module_ast, filepath = self.load_module(module_name, from_dir)

        # 收集导出的段落
        export_names = set()
        for exp in module_ast.exports:
            export_names.add(exp.name)

        # 构建 符号名 -> 定义映射（包括段落和类）
        symbols_map = {}
        for seg in module_ast.segments:
            symbols_map[seg.name] = ('segment', seg)
        for cls in module_ast.classes:
            symbols_map[cls.name] = ('class', cls)

        # 如果指定了导入的符号名，只导入这些
        if import_stmt.names:
            result = {}
            for name in import_stmt.names:
                if name not in symbols_map:
                    raise ModuleError(
                        f"模块 '{module_name}' 中未找到导出符号 '{name}'"
                    )
                if export_names and name not in export_names:
                    raise ModuleError(
                        f"符号 '{name}' 未在模块 '{module_name}' 中导出"
                    )
                result[name] = symbols_map[name]
            return result
        else:
            # 导入全部导出符号
            if not export_names:
                return symbols_map  # 无导出声明时导入所有符号（段落和类）
            return {name: symbols_map[name] for name in export_names
                    if name in symbols_map}

    def clear_cache(self):
        """清空模块缓存"""
        self.module_cache.clear()
        self._import_stack.clear()


# =============================================================================
# 快捷函数
# =============================================================================

_default_resolver = None


def get_default_resolver() -> ModuleResolver:
    """获取默认模块解析器（单例）"""
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = ModuleResolver()
    return _default_resolver


def resolve_module(module_name: str, from_dir: str = None) -> Tuple[Module, str]:
    """快捷方式：解析模块"""
    return get_default_resolver().load_module(module_name, from_dir)


def find_module(module_name: str, from_dir: str = None) -> str:
    """快捷方式：查找模块文件"""
    return get_default_resolver().find_module_file(module_name, from_dir)