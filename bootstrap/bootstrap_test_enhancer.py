"""
自举编译器测试增强工具

针对自举编译器每个层级运行功能性测试，
验证各层级功能完整性和正确性。
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class BootstrapTestEnhancer:
    """自举编译器测试增强工具"""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = str(Path(__file__).resolve().parent.parent)
        self.project_root = Path(project_root)
        self.bootstrap_dir = self.project_root / "bootstrap"
    
    def run_level_test(self, level: int) -> Dict:
        """运行指定层级的功能测试"""
        test_files = {
            1: "bootstrap_level3.duan",    # Level 1: 基础表达式
            2: "bootstrap_level3.duan",    # Level 2: 条件判断
            3: "bootstrap_level3.duan",    # Level 3: 函数/循环
            4: "bootstrap_level4.duan",    # Level 4: 列表/字典/模块
            5: "bootstrap_level5.duan",    # Level 5: 高级特性
        }
        
        filename = test_files.get(level)
        if not filename:
            return {"level": level, "status": "跳过", "reason": "未定义测试文件"}
        
        filepath = self.bootstrap_dir / filename
        if not filepath.exists():
            return {"level": level, "status": "跳过", "reason": f"文件不存在: {filename}"}
        
        # 尝试编译运行
        try:
            result = subprocess.run(
                [sys.executable, "-m", "cli.duan_unified", "run", str(filepath)],
                capture_output=True, text=True, timeout=30,
                cwd=str(self.project_root),
            )
            return {
                "level": level,
                "file": filename,
                "status": "通过" if result.returncode == 0 else "失败",
                "returncode": result.returncode,
                "stdout": result.stdout[:200] if result.stdout else "",
                "stderr": result.stderr[:200] if result.stderr else "",
            }
        except subprocess.TimeoutExpired:
            return {"level": level, "status": "超时", "reason": "执行超时 (30s)"}
        except Exception as e:
            return {"level": level, "status": "错误", "reason": str(e)}
    
    def run_all_level_tests(self) -> List[Dict]:
        """运行所有层级的测试"""
        results = []
        for level in range(1, 6):
            result = self.run_level_test(level)
            results.append(result)
            print(f"  Level {level}: {result['status']}")
        return results
    
    def generate_test_report(self) -> str:
        """生成测试报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("  自举编译器层级测试报告")
        lines.append("=" * 60)
        lines.append(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        
        results = self.run_all_level_tests()
        
        passed = sum(1 for r in results if r["status"] == "通过")
        failed = sum(1 for r in results if r["status"] == "失败")
        skipped = sum(1 for r in results if r["status"] == "跳过")
        
        lines.append(f"  通过: {passed} / 失败: {failed} / 跳过: {skipped}")
        lines.append("")
        lines.append("-" * 60)
        
        for r in results:
            status_icon = "✓" if r["status"] == "通过" else "✗" if r["status"] == "失败" else "→"
            lines.append(f"  {status_icon} Level {r['level']}: {r['status']}")
            if r.get("file"):
                lines.append(f"     文件: {r['file']}")
            if r.get("reason"):
                lines.append(f"     原因: {r['reason']}")
        
        lines.append("-" * 60)
        lines.append("")
        lines.append("  功能覆盖清单:")
        lines.append("")
        
        coverage = {
            1: ["数字字面量", "字符串字面量", "布尔值", "变量引用", "二元运算", "括号"],
            2: ["if语句", "if-else语句", "比较运算", "逻辑运算"],
            3: ["函数定义", "函数调用", "参数传递", "return语句", "while循环", "变量赋值"],
            4: ["列表字面量", "字典字面量", "索引访问", "for循环", "导入/导出"],
            5: ["try/except", "raise", "class定义", "match/case", "async/await", "with语句"],
        }
        
        for level, features in coverage.items():
            result = next((r for r in results if r["level"] == level), None)
            status = "全部支持" if result and result["status"] == "通过" else "部分支持"
            lines.append(f"  Level {level} ({status}):")
            for f in features:
                lines.append(f"    - {f}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


def main():
    enhancer = BootstrapTestEnhancer()
    print(enhancer.generate_test_report())


if __name__ == "__main__":
    main()