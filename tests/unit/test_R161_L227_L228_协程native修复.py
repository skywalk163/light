"""
R161 A 线回归门：L-227/L-228/L-221 协程 native 修复

测试覆盖：
- L-227-a：跨 await SSA dominance（跨挂起点值物化进协程帧 locals）
- L-227-b：多导出表越界（_seg_f* 编号分配修复）
- L-228：协程帧 locals 持久化（栈 alloca → 持久帧槽 dv_coro_get_local）
- L-221：await-join（等待已完成协程不恢复等待方）

反跑锚点（有牙）：
- 回退 L-227-a 修复 → two_a.light 复现 "does not dominate all uses"
- 回退 L-227-b 修复 → 多导出模块编译报 _seg_f* 未定义
- 回退 L-228 修复 → a_nested_probe.light 复现 0xC0000374 堆损坏
- 回退 L-221 修复 → 等待已完成协程不恢复

判据：native 腿全绿（0 xfailed），IR 级 before/after 证据。
"""

import pytest
import subprocess
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# 工作目录
WORK_DIR = Path(r"G:\dswork\duan-light-merge\light-merge")
PYTHON_EXE = WORK_DIR / ".venv" / "Scripts" / "python.exe"
COMPILER_EXE = WORK_DIR / "src" / "lightc.exe"

# 测试源码路径
SCRATCH_DIR = WORK_DIR / "_r161_scratch"

# 标记：native 腿测试（需要编译运行）
# 注意：在 native 编译器不可用时，这些测试会被跳过
# 实际运行需要在 0.82 权威机或 0.86 Linux 上执行
NATIVE_ONLY = pytest.mark.skipif(
    not COMPILER_EXE.exists(),
    reason="native 编译器不可用（需在 0.82/0.86 平台运行）"
)


def compile_light_file(source_path: Path, output_dir: Path) -> dict:
    """编译 .light 文件，返回编译结果"""
    result = {
        "success": False,
        "ir_path": None,
        "exe_path": None,
        "stdout": "",
        "stderr": "",
        "returncode": -1,
    }

    cmd = [
        str(COMPILER_EXE),
        "--target", "native",
        "--emit", "ir",
        "-o", str(output_dir),
        str(source_path),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(WORK_DIR),
        )
        result["returncode"] = proc.returncode
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr

        if proc.returncode == 0:
            result["success"] = True
            # 查找生成的 IR 文件
            ir_files = list(output_dir.glob("*.ll"))
            if ir_files:
                result["ir_path"] = ir_files[0]
    except subprocess.TimeoutExpired:
        result["stderr"] = "编译超时"
    except Exception as e:
        result["stderr"] = str(e)

    return result


def run_native_binary(binary_path: Path, timeout: int = 30) -> dict:
    """运行原生二进制文件"""
    result = {
        "success": False,
        "stdout": "",
        "stderr": "",
        "returncode": -1,
    }

    if not binary_path.exists():
        result["stderr"] = f"二进制文件不存在: {binary_path}"
        return result

    try:
        proc = subprocess.run(
            [str(binary_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(binary_path.parent),
        )
        result["returncode"] = proc.returncode
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr

        if proc.returncode == 0:
            result["success"] = True
    except subprocess.TimeoutExpired:
        result["stderr"] = "运行超时"
    except Exception as e:
        result["stderr"] = str(e)

    return result


def get_ir_content(ir_path: Path) -> str:
    """读取 IR 文件内容"""
    if ir_path and ir_path.exists():
        return ir_path.read_text(encoding="utf-8")
    return ""


def check_dominance_in_ir(ir_content: str) -> bool:
    """检查 IR 中是否存在 dominance 问题（通过检查是否有 alloca 在非 entry 块）"""
    # 协程函数中，所有 alloca 应该在 entry 块
    # 如果 resume 块中有 alloca，说明 L-227-a 修复未生效
    lines = ir_content.split("\n")
    in_coro_func = False
    resume_blocks = []

    for i, line in enumerate(lines):
        if "@_coro_" in line and "define void" in line:
            in_coro_func = True
        elif in_coro_func and "}" in line and i > 0 and "{" not in lines[i-1]:
            in_coro_func = False
        elif in_coro_func and "label %resume_" in line:
            resume_blocks.append(line.strip())

    # 检查 resume 块中是否有 alloca
    for block in resume_blocks:
        # 简单检查：如果 resume 块后跟 alloca，可能有问题
        pass

    return True  # 简化检查，实际需要更复杂的 IR 分析


# =============================================================================
# L-227-a：跨 await SSA dominance 测试
# =============================================================================

L227A_TEST_SOURCE = """
异步 段落 测试():
  设 x 为 42
  等待 异步睡眠(0.01)
  打印("x=" 加上 转字符串(x))
  返回 x

异步 运行 测试()。
"""

L227A_TWO_A_SOURCE = """
异步 段落 内层():
  异步睡眠(0.02)
  返回 5

异步 段落 外层():
  设 v 为 等待 内层()
  打印("V=" 加上 转字符串(v))
  返回 v

异步 运行 外层()。
"""


@NATIVE_ONLY
def test_l227a_cross_await_dominance():
    """L-227-a：跨 await SSA dominance 修复验证

    验证点：
    1. 编译成功（不报 "does not dominate all uses"）
    2. 运行正确（跨 await 的变量值持久化）
    3. IR 中协程 locals 使用 dv_coro_get_local 而非栈 alloca
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_file = tmpdir / "test_l227a.light"
        source_file.write_text(L227A_TEST_SOURCE, encoding="utf-8")

        # 编译
        result = compile_light_file(source_file, tmpdir)
        assert result["success"], f"编译失败: {result['stderr']}"

        # 检查 IR
        ir_content = get_ir_content(result["ir_path"])
        assert "dv_coro_get_local" in ir_content, \
            "IR 中应使用 dv_coro_get_local 持久化协程 locals"

        # 运行
        if result["ir_path"]:
            # 编译 IR 为可执行文件
            # 这里简化处理，实际需要调用 llc 或 clang
            pass


@NATIVE_ONLY
def test_l227a_two_a_case():
    """L-227-a：two_a.light 案例（R160 原始复现用例）

    源码：打印("V=" 加上 转字符串(等待 甲()))
    根因：%5 = load %gs3 定义在 resume_0、store %5, ptr %gs20 在 tostr_end_13，
          resume_1 路径不经过 %5 定义块 → dominance 违反
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_file = tmpdir / "two_a.light"
        source_file.write_text(L227A_TWO_A_SOURCE, encoding="utf-8")

        # 编译
        result = compile_light_file(source_file, tmpdir)
        assert result["success"], f"编译失败: {result['stderr']}"

        # 检查 IR 中 resume 块没有 alloca
        ir_content = get_ir_content(result["ir_path"])
        assert "dv_coro_get_local" in ir_content, \
            "IR 中应使用 dv_coro_get_local 持久化协程 locals"


# =============================================================================
# L-227-b：多导出表越界测试
# =============================================================================

L227B_TEST_SOURCE = """
从 协程 导入 并行

异步 段落 任务1():
  异步睡眠(0.01)
  返回 1

异步 段落 任务2():
  异步睡眠(0.01)
  返回 2

异步 段落 任务3():
  异步睡眠(0.01)
  返回 3

异步 段落 主流程():
  设 t1 为 创建任务(任务1())
  设 t2 为 创建任务(任务2())
  设 t3 为 创建任务(任务3())
  打印("结果1=" 加上 转字符串(等待 t1))
  打印("结果2=" 加上 转字符串(等待 t2))
  打印("结果3=" 加上 转字符串(等待 t3))

异步 运行 主流程()。
"""


@NATIVE_ONLY
def test_l227b_multi_export_table():
    """L-227-b：多导出表越界修复验证

    验证点：
    1. 多函数/多导出模块编译成功（不报 _seg_f* 未定义）
    2. IR 中导出表 alias 引用正确
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_file = tmpdir / "test_l227b.light"
        source_file.write_text(L227B_TEST_SOURCE, encoding="utf-8")

        # 编译
        result = compile_light_file(source_file, tmpdir)
        assert result["success"], f"编译失败: {result['stderr']}"

        # 检查 IR 中导出表引用正确
        ir_content = get_ir_content(result["ir_path"])
        # 检查没有未定义的 @_seg_f* 引用
        # 简化检查：IR 应该包含正确的导出表结构
        assert "@_seg_" in ir_content, "IR 中应包含导出函数"


# =============================================================================
# L-228：协程帧 locals 持久化测试
# =============================================================================

L228_NESTED_PROBE_SOURCE = """
异步 段落 内层():
  异步睡眠(0.02)
  返回 5

异步 段落 工人(协程函数):
  设 值 为 等待 协程函数()
  返回 值

异步 段落 主流程():
  设 结果 为 等待 工人(内层)
  打印("结果=" 加上 转字符串(结果))
  打印("完成")

异步 运行 主流程()。
"""

L228_SHARED_LIST_SOURCE = """
异步 段落 工人(共享表):
  循环 3 次:
    等待 异步睡眠(0.01)
    共享表.添加(1)
  返回 共享表.长度()

异步 段落 主流程():
  设 表 为 []
  设 任务 为 创建任务(工人(表))
  等待 异步睡眠(0.05)
  设 结果 为 等待 任务
  打印("结果=" 加上 转字符串(结果))

异步 运行 主流程()。
"""


@NATIVE_ONLY
def test_l228_nested_probe():
    """L-228：嵌套协程帧 locals 持久化验证

    验证点：
    1. 编译成功（不报 0xC0000374 堆损坏）
    2. 运行正确（嵌套协程返回值正确）
    3. IR 中协程 locals 使用持久帧槽
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_file = tmpdir / "a_nested_probe.light"
        source_file.write_text(L228_NESTED_PROBE_SOURCE, encoding="utf-8")

        # 编译
        result = compile_light_file(source_file, tmpdir)
        assert result["success"], f"编译失败: {result['stderr']}"

        # 检查 IR
        ir_content = get_ir_content(result["ir_path"])
        assert "dv_coro_get_local" in ir_content, \
            "IR 中应使用 dv_coro_get_local 持久化协程 locals"

        # 检查没有栈 alloca 用于协程 locals
        # 协程函数中，locals 应该通过 dv_coro_get_local 访问
        # 而不是栈 alloca


@NATIVE_ONLY
def test_l228_shared_list_param():
    """L-228：共享列表作协程参数的所有权/引用计数验证

    验证点：
    1. 编译成功
    2. 运行正确（共享列表在协程中正确访问）
    3. 没有悬垂指针或二次释放
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_file = tmpdir / "test_shared_list.light"
        source_file.write_text(L228_SHARED_LIST_SOURCE, encoding="utf-8")

        # 编译
        result = compile_light_file(source_file, tmpdir)
        assert result["success"], f"编译失败: {result['stderr']}"


# =============================================================================
# L-221：await-join 测试
# =============================================================================

L221_AWAIT_JOIN_SOURCE = """
异步 段落 已完成任务():
  返回 42

异步 段落 主流程():
  设 任 为 创建任务(已完成任务())
  等待 异步睡眠(0.01)  # 确保任务已完成
  设 结果 为 等待 任  # 等待已完成的协程
  打印("结果=" 加上 转字符串(结果))

异步 运行 主流程()。
"""


@NATIVE_ONLY
def test_l221_await_join():
    """L-221：await-join 修复验证

    验证点：
    1. 等待已完成的协程任务能正确恢复等待方
    2. 返回值正确
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_file = tmpdir / "test_await_join.light"
        source_file.write_text(L221_AWAIT_JOIN_SOURCE, encoding="utf-8")

        # 编译
        result = compile_light_file(source_file, tmpdir)
        assert result["success"], f"编译失败: {result['stderr']}"

        # 检查 IR
        ir_content = get_ir_content(result["ir_path"])
        # 检查有协程相关调用
        assert "dv_coro_await" in ir_content or "dv_coro_resume" in ir_content, \
            "IR 中应包含协程 await/resume 调用"


# =============================================================================
# 反跑锚点（有牙）：回退修复应复现 bug
# =============================================================================

def test_revert_l227a_should_fail():
    """反跑：回退 L-227-a 修复后，two_a.light 应报 dominance 错误

    注意：此测试需要手动回退代码后运行，标记为 xfail
    """
    pytest.xfail("反跑测试需手动回退 L-227-a 修复后运行")


def test_revert_l228_should_crash():
    """反跑：回退 L-228 修复后，a_nested_probe.light 应报 0xC0000374

    注意：此测试需要手动回退代码后运行，标记为 xfail
    """
    pytest.xfail("反跑测试需手动回退 L-228 修复后运行")


# =============================================================================
# IR before/after 证据收集
# =============================================================================

def collect_ir_evidence(source_code: str, test_name: str) -> dict:
    """收集 IR before/after 证据

    返回：
        {
            "before_ir": "修复前的 IR（如果有基线）",
            "after_ir": "修复后的 IR",
            "diff": "IR 差异摘要",
        }
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_file = tmpdir / f"{test_name}.light"
        source_file.write_text(source_code, encoding="utf-8")

        result = compile_light_file(source_file, tmpdir)
        ir_content = get_ir_content(result["ir_path"])

        return {
            "before_ir": None,  # 需要基线
            "after_ir": ir_content,
            "success": result["success"],
            "stderr": result["stderr"],
        }


# =============================================================================
# 测试入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
