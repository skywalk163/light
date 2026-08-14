#!/usr/bin/env python3
"""
段言 (Duan) API 文档自动生成工具

从 stdlib/ 目录的 Python 源码提取函数签名和文档字符串，
为每个模块生成标准格式的 Markdown API 参考页。

用法:
    python tools/gen_api_docs.py                    # 生成所有 API 文档
    python tools/gen_api_docs.py --module 数学       # 生成指定模块
    python tools/gen_api_docs.py --output-dir docs/api  # 指定输出目录
"""

import os
import sys
import re
import ast
import argparse
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STDLIB_DIR = PROJECT_ROOT / "stdlib"
DUANPUB_DIR = STDLIB_DIR / "duanpub"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "api"

# 模块中文名映射
MODULE_NAME_MAP = {
    "数学": "数学运算",
    "字符串处理": "字符串处理",
    "字符串工具": "字符串工具",
    "字符串常量": "字符串常量",
    "文件系统": "文件系统",
    "日期时间": "日期时间",
    "时间管理": "时间管理",
    "JSON": "JSON 解析与序列化",
    "哈希": "哈希计算",
    "正则表达式": "正则表达式",
    "加密": "加密解密",
    "随机数": "随机数生成",
    "数据结构": "数据结构",
    "集合": "集合操作",
    "集合工具": "集合工具",
    "集合操作": "集合操作",
    "列表工具": "列表工具",
    "迭代器工具": "迭代器工具",
    "排序与搜索": "排序与搜索",
    "统计分析": "统计分析",
    "数值计算": "数值计算",
    "参数解析": "命令行参数解析",
    "外部命令": "外部命令执行",
    "系统接口": "系统接口",
    "编码解码": "编码解码",
    "编码": "编码工具",
    "断言工具": "断言测试",
    "装饰器": "装饰器",
    "函数工具": "函数工具",
    "日志系统增强": "日志系统",
    "缓存系统": "缓存系统",
    "对象池缓存": "对象池与缓存",
    "配置管理": "配置管理",
    "环境变量": "环境变量",
    "进程管理": "进程管理",
    "线程": "线程与并发",
    "网络工具": "网络工具",
    "日期序列": "日期序列",
    "算法工具": "算法工具",
    "类型工具": "类型工具",
    "路径处理": "路径处理",
    "错误处理": "错误处理",
    "连接池": "连接池",
    "二进制编码": "二进制编码",
    "文件匹配": "文件匹配",
    "临时文件": "临时文件",
    "排版": "排版与美化",
    "中文文本": "中文文本处理",
    "历法": "历法工具",
    "FFI": "FFI 外部函数接口",
    "CSV读写器": "CSV 读写",
    "builtins": "内置函数",
}


def extract_functions_from_source(source_path: str) -> list[dict]:
    """从 Python 源码提取函数签名和文档字符串"""
    functions = []
    
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print(f"  [警告] 无法读取文件 {source_path}: {e}")
        return functions

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"  [警告] 语法错误 {source_path}: {e}")
        return functions

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_info = {
                "name": node.name,
                "docstring": ast.get_docstring(node) or "",
                "args": [],
                "has_return": False,
                "return_type": None,
                "line_number": node.lineno,
            }

            # 提取参数
            for arg in node.args.args:
                arg_info = {"name": arg.arg, "type": None}
                if arg.annotation:
                    try:
                        arg_info["type"] = ast.unparse(arg.annotation)
                    except Exception:
                        arg_info["type"] = "..."
                func_info["args"].append(arg_info)

            # 检查是否有默认值
            defaults = [None] * (len(node.args.args) - len(node.args.defaults)) + node.args.defaults
            for i, default in enumerate(defaults):
                if default is not None:
                    try:
                        func_info["args"][i]["default"] = ast.unparse(default)
                    except Exception:
                        func_info["args"][i]["default"] = "..."

            # 检查返回类型注解
            if node.returns:
                try:
                    func_info["return_type"] = ast.unparse(node.returns)
                except Exception:
                    func_info["return_type"] = "..."

            functions.append(func_info)

    return functions


def extract_constants_from_source(source_path: str) -> list[dict]:
    """从 Python 源码提取模块级常量"""
    constants = []
    
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return constants

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return constants

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isidentifier():
                    # 跳过 _ 开头的私有变量
                    if target.id.startswith("_"):
                        continue
                    try:
                        value = ast.unparse(node.value)
                        constants.append({
                            "name": target.id,
                            "value": value,
                            "line_number": node.lineno,
                        })
                    except Exception:
                        pass

    return constants


def generate_module_doc(module_name: str, functions: list[dict], constants: list[dict]) -> str:
    """生成模块的 Markdown API 文档"""
    display_name = MODULE_NAME_MAP.get(module_name, module_name)
    
    lines = [
        f"# {display_name} API",
        "",
        f"> 模块路径：`stdlib/{module_name}.py`",
        f"> 导入方式：`从 {module_name} 导入 函数名` 或 `导入 {module_name}`",
        "",
        "---",
        "",
    ]

    if functions:
        lines.append("## 函数列表")
        lines.append("")
        lines.append("| 函数 | 说明 |")
        lines.append("|------|------|")
        for func in functions:
            brief = func["docstring"].split("\n")[0] if func["docstring"] else ""
            signature = f"{func['name']}({', '.join(a['name'] for a in func['args'])})"
            lines.append(f"| `{signature}` | {brief} |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 详细文档
        lines.append("## 函数详情")
        lines.append("")
        for func in functions:
            # 函数签名
            args_str = []
            for arg in func["args"]:
                arg_str = arg["name"]
                if arg.get("type"):
                    arg_str += f": {arg['type']}"
                if arg.get("default") is not None:
                    arg_str += f" = {arg['default']}"
                args_str.append(arg_str)
            
            signature = f"{func['name']}({', '.join(args_str)})"
            if func["return_type"]:
                signature += f" -> {func['return_type']}"
            
            lines.append(f"### `{signature}`")
            lines.append("")
            
            if func["docstring"]:
                lines.append(func["docstring"])
                lines.append("")
            
            lines.append("**参数：**")
            lines.append("")
            if func["args"]:
                lines.append("| 参数名 | 类型 | 说明 |")
                lines.append("|--------|------|------|")
                for arg in func["args"]:
                    arg_type = arg.get("type", "任意")
                    default_str = f"（默认：{arg['default']}）" if arg.get("default") is not None else ""
                    lines.append(f"| `{arg['name']}` | `{arg_type}` | {default_str} |")
            else:
                lines.append("无参数。")
            lines.append("")
            
            if func["return_type"]:
                lines.append(f"**返回：** `{func['return_type']}`")
                lines.append("")
            
            lines.append("---")
            lines.append("")

    if constants:
        lines.append("## 常量")
        lines.append("")
        lines.append("| 常量名 | 值 |")
        lines.append("|--------|-----|")
        for const in constants:
            lines.append(f"| `{const['name']}` | `{const['value']}` |")
        lines.append("")

    return "\n".join(lines)


def scan_stdlib_modules() -> list[tuple[str, str]]:
    """扫描 stdlib 目录，返回 (模块名, 文件路径) 列表"""
    modules = []
    
    for item in sorted(STDLIB_DIR.iterdir()):
        if item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
            module_name = item.stem
            modules.append((module_name, str(item)))
    
    return modules


def scan_duanpub_modules() -> list[tuple[str, str]]:
    """扫描 duanpub 目录，返回 (模块名, 文件路径) 列表"""
    modules = []
    
    for item in sorted(DUANPUB_DIR.iterdir()):
        if item.is_file() and item.suffix == ".py" and item.name not in ("__init__.py", "__index__.py"):
            module_name = item.stem
            modules.append((module_name, str(item)))
    
    return modules


def generate_index_page(modules: list[tuple[str, str]], source_type: str) -> str:
    """生成 API 文档索引页"""
    title = "duanpub 桥接模块" if source_type == "duanpub" else "标准库模块"
    
    lines = [
        f"# {title} API",
        "",
        f"> 自动从 {source_type}/ 目录提取的模块 API 参考。",
        "",
        "---",
        "",
        "## 模块列表",
        "",
        "| 模块 | 说明 |",
        "|------|------|",
    ]
    
    for module_name, _ in modules:
        display_name = MODULE_NAME_MAP.get(module_name, module_name)
        if source_type == "duanpub":
            lines.append(f"| [{display_name}]({module_name}.md) | duanpub 桥接模块 |")
        else:
            lines.append(f"| [{display_name}]({module_name}.md) | 标准库模块 |")
    
    lines.append("")
    return "\n".join(lines)


def generate_all(output_dir: str, target_modules: list[str] = None):
    """生成所有 API 文档"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 扫描标准库模块
    stdlib_modules = scan_stdlib_modules()
    duanpub_modules = scan_duanpub_modules()

    all_modules = stdlib_modules + duanpub_modules

    if target_modules:
        all_modules = [(name, path) for name, path in all_modules if name in target_modules]
        if not all_modules:
            print(f"[错误] 未找到指定模块: {target_modules}")
            sys.exit(1)

    # 生成模块文档
    generated_count = 0
    for module_name, source_path in all_modules:
        print(f"  生成: {module_name}.py → {module_name}.md")

        functions = extract_functions_from_source(source_path)
        constants = extract_constants_from_source(source_path)

        doc = generate_module_doc(module_name, functions, constants)
        
        output_file = output_path / f"{module_name}.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(doc)
        
        generated_count += 1

    # 生成标准库索引页
    stdlib_index = generate_index_page(stdlib_modules, "stdlib")
    with open(output_path / "index.md", "w", encoding="utf-8") as f:
        f.write(stdlib_index)

    print(f"\n[完成] 生成了 {generated_count} 个模块的 API 文档")
    print(f"[完成] 输出目录: {output_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="段言 API 文档自动生成工具")
    parser.add_argument("--module", "-m", nargs="+", help="指定要生成的模块名（多个用空格分隔）")
    parser.add_argument("--output-dir", "-o", default=str(OUTPUT_DIR), help="输出目录（默认: docs/api）")
    parser.add_argument("--list-modules", "-l", action="store_true", help="列出所有可用的标准库模块")
    
    args = parser.parse_args()

    if args.list_modules:
        stdlib_modules = scan_stdlib_modules()
        duanpub_modules = scan_duanpub_modules()
        print("标准库模块:")
        for name, path in stdlib_modules:
            print(f"  {name}  ({path})")
        print("\nduanpub 桥接模块:")
        for name, path in duanpub_modules:
            print(f"  {name}  ({path})")
        return

    target_modules = args.module
    generate_all(args.output_dir, target_modules)


if __name__ == "__main__":
    main()