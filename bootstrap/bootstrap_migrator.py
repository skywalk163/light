"""
光明自举编译器迁移辅助工具

帮助将 Python 实现的编译器组件逐步迁移到光明自身实现。
监控迁移进度，生成迁移报告。
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class BootstrapMigrator:
    """自举编译器迁移辅助工具"""
    
    # 编译器核心组件清单
    COMPILER_COMPONENTS = {
        "词法分析器": {
            "python": "src/lexer.py",
            "light": "bootstrap/lexer.light",
            "status": "已完成",
            "lines_python": 0,
            "lines_light": 0,
        },
        "语法解析器": {
            "python": "src/light_parser_v3.py",
            "light": "bootstrap/parser.light",
            "status": "部分完成",
            "lines_python": 0,
            "lines_light": 0,
        },
        "AST定义": {
            "python": "src/ast_nodes_v3.py",
            "light": "bootstrap/light_ast.light",
            "status": "已完成",
            "lines_python": 0,
            "lines_light": 0,
        },
        "代码生成器": {
            "python": "src/code_generator.py",
            "light": "bootstrap/codegen.light",
            "status": "部分完成",
            "lines_python": 0,
            "lines_light": 0,
        },
        "类型检查器": {
            "python": "src/type_checker.py",
            "light": None,
            "status": "未开始",
            "lines_python": 0,
            "lines_light": 0,
        },
        "类型推断器": {
            "python": "src/type_inferencer.py",
            "light": None,
            "status": "未开始",
            "lines_python": 0,
            "lines_light": 0,
        },
        "编译器管道": {
            "python": "src/compiler.py",
            "light": "bootstrap/compiler.light",
            "status": "部分完成",
            "lines_python": 0,
            "lines_light": 0,
        },
        "主程序入口": {
            "python": "cli/light_unified.py",
            "light": "bootstrap/main.light",
            "status": "部分完成",
            "lines_python": 0,
            "lines_light": 0,
        },
    }
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = str(Path(__file__).resolve().parent.parent)
        self.project_root = Path(project_root)
    
    def count_lines(self, filepath: str) -> int:
        """统计文件行数（排除空行和注释）"""
        path = self.project_root / filepath
        if not path.exists():
            return 0
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 排除空行和注释行
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
        return len(code_lines)
    
    def update_component_stats(self) -> Dict:
        """更新所有组件的行数统计"""
        for name, info in self.COMPILER_COMPONENTS.items():
            py_path = info["python"]
            light_path = info["light"]
            info["lines_python"] = self.count_lines(py_path)
            if light_path:
                info["lines_light"] = self.count_lines(light_path)
        return self.COMPILER_COMPONENTS
    
    def calculate_progress(self) -> Dict:
        """计算自举进度"""
        self.update_component_stats()
        
        total_python_lines = sum(
            c["lines_python"] for c in self.COMPILER_COMPONENTS.values()
        )
        total_light_lines = sum(
            c["lines_light"] for c in self.COMPILER_COMPONENTS.values()
        )
        
        # 已完成组件（有光明实现且状态为"已完成"）
        completed = sum(
            1 for c in self.COMPILER_COMPONENTS.values()
            if c["light"] and c["status"] == "已完成"
        )
        # 部分完成组件
        partial = sum(
            1 for c in self.COMPILER_COMPONENTS.values()
            if c["light"] and c["status"] == "部分完成"
        )
        # 未开始组件
        not_started = sum(
            1 for c in self.COMPILER_COMPONENTS.values()
            if not c["light"] or c["status"] == "未开始"
        )
        
        total = len(self.COMPILER_COMPONENTS)
        # 加权进度：已完成=100%，部分完成=50%，未开始=0%
        weighted = (completed * 100 + partial * 50) / total
        
        return {
            "total_components": total,
            "completed": completed,
            "partial": partial,
            "not_started": not_started,
            "progress_percent": round(weighted, 1),
            "total_python_lines": total_python_lines,
            "total_light_lines": total_light_lines,
            "migration_ratio": round(total_light_lines / max(total_python_lines, 1) * 100, 1),
        }
    
    def generate_report(self) -> str:
        """生成自举迁移进度报告"""
        stats = self.calculate_progress()
        self.update_component_stats()
        
        lines = []
        lines.append("=" * 60)
        lines.append("  光明自举编译器迁移进度报告")
        lines.append("=" * 60)
        lines.append(f"  生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        lines.append(f"  总体进度: {stats['progress_percent']}%")
        lines.append(f"  组件: {stats['completed']} 已完成 / {stats['partial']} 部分 / {stats['not_started']} 未开始 (共{stats['total_components']})")
        lines.append(f"  Python: {stats['total_python_lines']} 行  →  光明: {stats['total_light_lines']} 行 (迁移率 {stats['migration_ratio']}%)")
        lines.append("")
        lines.append("-" * 60)
        lines.append(f"  {'组件名称':<12} {'状态':<8} {'Python行数':<10} {'光明行数':<10}")
        lines.append("-" * 60)
        for name, info in self.COMPILER_COMPONENTS.items():
            status = info["status"]
            py_lines = info["lines_python"]
            light_lines = info["lines_light"]
            lines.append(f"  {name:<12} {status:<8} {py_lines:<10} {light_lines:<10}")
        lines.append("-" * 60)
        lines.append("")
        lines.append("  待完成项:")
        for name, info in self.COMPILER_COMPONENTS.items():
            if info["status"] != "已完成":
                lines.append(f"    - {name}: {info['status']}")
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


def main():
    """主函数"""
    migrator = BootstrapMigrator()
    print(migrator.generate_report())


if __name__ == "__main__":
    main()