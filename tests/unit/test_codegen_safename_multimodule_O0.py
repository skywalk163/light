# -*- coding: utf-8 -*-
"""
test_codegen_safename_multimodule_O0.py —— T9A 定向测试：_safe_func_name 跨模块同名段根因修复。

验证目标：
  1. 最小复现：同时导入 Base64 和 编码解码（两者都定义 Base64编码 段）
     → 修复前编译报 invalid redefinition of function '_seg_fN'，修复后编译成功且输出正确。
  2. 同时导入 集合 和 集合操作（两者都定义 交集/差集 段）→ 编译成功。
  3. 同时导入 数学 和 统计（两者都定义 最小值/最大值 段）→ 编译成功且各自行为正确。
  4. 导出名一致性：统计.light 导出 最小值/最大值（与 统计.py 对齐，不再是 数据最小值/数据最大值）。
  5. 集合操作.light 内部使用 随机下限（不再是 打乱随机下限 防撞名 workaround）。

反跑判据：
  - 修复前（git stash）→ 最小复现立即立红（redefinition）。
  - 修复后 → 全部用例绿。

约束：
  - optimize_level=0（O0 反跑）。
  - 仅本文件定向测试，禁止全量。
"""
import os
import sys
import tempfile
import subprocess

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO, "src"))
_STDLIB = os.path.join(_REPO, "stdlib")


def _编译并运行(code, optimize_level=0):
    """用原生腿 compile_light_typed 编译并运行，返回 (rc, stdout行列表, stderr)。"""
    from llvm.compiler import compile_light_typed
    with tempfile.TemporaryDirectory(prefix="_T9A_") as d:
        src = os.path.join(d, "主.light")
        with open(src, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        exe = compile_light_typed(src, os.path.join(d, "产物"),
                                  optimize_level=optimize_level)
        r = subprocess.run([exe], capture_output=True, timeout=120)
        out = r.stdout.decode("utf-8", errors="replace").replace("\r", "").strip()
        err = r.stderr.decode("utf-8", errors="replace")
        return r.returncode, out.split("\n") if out else [], err


def _期望编译失败(code, optimize_level=0):
    """断言编译必须抛异常。"""
    from llvm.compiler import compile_light_typed
    with tempfile.TemporaryDirectory(prefix="_T9A_red_") as d:
        src = os.path.join(d, "主.light")
        with open(src, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        with pytest.raises(Exception):
            compile_light_typed(src, os.path.join(d, "产物"),
                                optimize_level=optimize_level)


# ═══════════════════════════════════════════════════════════════════════════
# 1. 最小复现：Base64 + 编码解码 同名段 Base64编码
# ═══════════════════════════════════════════════════════════════════════════

class TestBase64Conflict:
    """T5A-05 / T6A-09 最小复现：Base64 与 编码解码 都定义 Base64编码。"""

    def test_同时导入Base64和编码解码_编译成功(self):
        code = (
            "从 Base64 导入 Base64编码\n"
            "从 编码解码 导入 Base64解码\n"
            "\n"
            "输出 Base64编码(\"hi\")\n"
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, f"编译/运行失败 rc={rc}, err={err[:300]}"
        assert out[0] == "aGk=", f"Base64编码('hi') 期望 aGk=, 实际 {out[0]}"

    def test_编码解码模块的Base64编码可独立调用(self):
        """确认两个模块的 Base64编码 是不同函数，各自可调用。"""
        code = (
            "从 编码解码 导入 Base64编码\n"
            "\n"
            "输出 Base64编码(\"hello\")\n"
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, f"rc={rc}, err={err[:300]}"
        assert out[0] == "aGVsbG8=", f"期望 aGVsbG8=, 实际 {out[0]}"


# ═══════════════════════════════════════════════════════════════════════════
# 2. 集合 + 集合操作 同名段 交集/差集
# ═══════════════════════════════════════════════════════════════════════════

class TestSetConflict:
    """T5C-06：集合 与 集合操作 都定义 交集/差集，联合编译不再冲突。"""

    def test_同时导入集合和集合操作_编译成功(self):
        """移除「同一程序不得同时导入 集合 与 集合操作」的限制。"""
        code = (
            "从 集合 导入 列表转集合 集合转列表 交集 集合长度\n"
            "从 集合操作 导入 差集\n"
            "\n"
            "设 s1 为 列表转集合([1, 2, 3, 4])\n"
            "设 s2 为 列表转集合([3, 4, 5, 6])\n"
            "设 r 为 交集(s1, s2)\n"
            "输出 集合长度(r)\n"
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, f"rc={rc}, err={err[:300]}"
        assert out[0] == "2", f"交集长度期望 2, 实际 {out[0]}"

    def test_集合操作的交集差集_列表操作正确(self):
        """集合操作模块的交集/差集直接操作列表，验证行为正确。"""
        code = (
            "从 集合操作 导入 交集 差集\n"
            "\n"
            "设 甲 为 [1, 2, 3, 4]\n"
            "设 乙 为 [3, 4, 5, 6]\n"
            "输出 长(交集(甲, 乙))\n"
            "输出 长(差集(甲, 乙))\n"
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, f"rc={rc}, err={err[:300]}"
        assert out[0] == "2", f"交集长度期望 2, 实际 {out[0]}"
        assert out[1] == "2", f"差集长度期望 2, 实际 {out[1]}"


# ═══════════════════════════════════════════════════════════════════════════
# 3. 数学 + 统计 同名段 最小值/最大值
# ═══════════════════════════════════════════════════════════════════════════

class TestMathStatsConflict:
    """T5A-05：数学 与 统计 都定义 最小值/最大值，联合编译不再冲突。"""

    def test_同时导入数学和统计_编译成功且行为正确(self):
        code = (
            "从 数学 导入 最小值 最大值\n"
            "从 统计 导入 均值\n"
            "\n"
            "输出 最小值(3, 7)\n"
            "输出 最大值(3, 7)\n"
            "输出 均值([1, 2, 3, 4, 5])\n"
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, f"rc={rc}, err={err[:300]}"
        assert out[0] == "3", f"数学.最小值(3,7) 期望 3, 实际 {out[0]}"
        assert out[1] == "7", f"数学.最大值(3,7) 期望 7, 实际 {out[1]}"
        assert out[2] == "3", f"统计.均值([1..5]) 期望 3, 实际 {out[2]}"

    def test_统计模块的最小值最大值_与Python对拍(self):
        """统计.light 改回 最小值/最大值 后，与 Python statistics 对拍。"""
        import statistics
        data = [5, 2, 8, 1, 9, 3]
        code = (
            "从 统计 导入 最小值 最大值\n"
            "\n"
            f"输出 最小值({data})\n"
            f"输出 最大值({data})\n"
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, f"rc={rc}, err={err[:300]}"
        assert int(out[0]) == min(data), f"最小值期望 {min(data)}, 实际 {out[0]}"
        assert int(out[1]) == max(data), f"最大值期望 {max(data)}, 实际 {out[1]}"


# ═══════════════════════════════════════════════════════════════════════════
# 4. 导出名一致性 / workaround 移除验证
# ═══════════════════════════════════════════════════════════════════════════

class TestWorkaroundRemoved:
    """验证 stdlib 中的防撞名 workaround 已移除。"""

    def test_统计light导出最小值而非数据最小值(self):
        path = os.path.join(_STDLIB, "统计.light")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "数据最小值" not in content, "统计.light 仍包含 数据最小值（workaround 未移除）"
        assert "数据最大值" not in content, "统计.light 仍包含 数据最大值（workaround 未移除）"
        assert "导出 最小值。" in content, "统计.light 未导出 最小值"
        assert "导出 最大值。" in content, "统计.light 未导出 最大值"
        assert "段落 最小值 接收 数据:" in content, "统计.light 未定义 最小值 段"
        assert "段落 最大值 接收 数据:" in content, "统计.light 未定义 最大值 段"

    def test_统计py与统计light导出名对齐(self):
        """原生腿(.light)与解释腿(.py)的 最小值/最大值 导出名一致。"""
        py_path = os.path.join(_STDLIB, "统计.py")
        with open(py_path, "r", encoding="utf-8") as f:
            py_content = f.read()
        assert "def 最小值(" in py_content, "统计.py 未定义 最小值"
        assert "def 最大值(" in py_content, "统计.py 未定义 最大值"

    def test_集合操作使用随机下限而非打乱随机下限(self):
        path = os.path.join(_STDLIB, "集合操作.light")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "打乱随机下限" not in content, "集合操作.light 仍包含 打乱随机下限（workaround 未移除）"
        assert "段落 随机下限 接收 n:" in content, "集合操作.light 未定义 随机下限 段"


# ═══════════════════════════════════════════════════════════════════════════
# 5. 主模块与导入模块同名段（T6A-09）
# ═══════════════════════════════════════════════════════════════════════════

class TestMainModuleConflict:
    """T6A-09：主模块定义与导入模块同名的段，联合编译不再冲突。"""

    def test_主模块与导入模块同名段_编译成功(self):
        code = (
            "从 数学 导入 绝对值\n"
            "\n"
            "段落 最小值 接收 数据:\n"
            "  设 n 为 长(数据)\n"
            "  设 结果 为 数据[0]\n"
            "  设 i 为 1\n"
            "  当 i < n:\n"
            "    如果 数据[i] < 结果:\n"
            "      设 结果 为 数据[i]\n"
            "    设 i 为 i + 1\n"
            "  返回 结果\n"
            "\n"
            "输出 最小值([5, 2, 8, 1])\n"
            "输出 绝对值(-42)\n"
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, f"rc={rc}, err={err[:300]}"
        assert out[0] == "1", f"主模块.最小值([5,2,8,1]) 期望 1, 实际 {out[0]}"
        assert out[1] == "42", f"绝对值(-42) 期望 42, 实际 {out[1]}"
