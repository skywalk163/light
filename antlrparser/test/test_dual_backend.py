"""
光明（Light）双后端功能对齐测试

对每个特性同时跑 src 和 ANTLR 两个后端，比较输出结果。
用于确保两个后端的行为一致。

运行方式：
    python -m pytest antlrparser/test/test_dual_backend.py -v
"""

import sys
import os
import traceback
import pytest

# 添加 src 后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
# 添加 ANTLR 后端路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# 添加当前目录
sys.path.insert(0, os.path.dirname(__file__))


# =============================================================================
# SRC 后端（parser_v3 + code_generator）
# =============================================================================

def run_src(code: str) -> str:
    """使用 src 后端（parser_v3 → code_generator → exec）"""
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    parser = LightParser()
    try:
        module = parser.parse(code)
    except Exception as e:
        raise RuntimeError(f"SRC解析失败: {e}")

    generator = PythonCodeGenerator()
    try:
        py_code = generator.generate(module)
    except Exception as e:
        raise RuntimeError(f"SRC代码生成失败: {e}")

    # 执行生成的代码并捕获输出
    output_lines = []
    namespace = {}

    # 替换 print 为捕获输出
    original_print = __builtins__.print if isinstance(__builtins__, dict) else __builtins__.print

    def _capture_print(*args, **kwargs):
        line = ' '.join(str(a) for a in args)
        output_lines.append(line)
        # 同时也输出到控制台（便于调试）
        original_print(*args, **kwargs)

    namespace['print'] = _capture_print

    try:
        exec(py_code, namespace)
    except Exception as e:
        raise RuntimeError(f"SRC执行失败: {type(e).__name__}: {e}")
    return '\n'.join(output_lines)


# =============================================================================
# ANTLR 后端（antlrparser 路径）
# =============================================================================

def run_antlr(code: str) -> str:
    """使用 ANTLR 后端（light_visitor → light_interpreter）"""
    from light_visitor import LightParser
    from light_interpreter import Interpreter

    parser = LightParser()
    module = parser.parse(code)
    if module is None:
        errors = '\n'.join(parser.errors)
        raise RuntimeError(f"ANTLR 解析失败:\n{errors}")

    interpreter = Interpreter()
    interpreter.interpret(module)
    return interpreter.get_output()


# =============================================================================
# 测试用例
# =============================================================================

TEST_CASES = [
    # ─── 基础表达式 ───
    ("整数", "设 甲 为 四十二。\n打印 甲。\n"),
    ("浮点数", "设 甲 为 三点一四。\n打印 甲。\n"),
    ("字符串", '设 甲 为 "你好，世界"。\n打印 甲。\n'),
    ("布尔值", "打印 真。\n打印 假。\n"),

    # ─── 算术运算 ───
    ("加法", "设 甲 为 一 加 二。\n打印 甲。\n"),
    ("减法", "设 甲 为 十 减 三。\n打印 甲。\n"),
    ("乘法", "设 甲 为 六 乘 七。\n打印 甲。\n"),
    ("除法", "设 甲 为 十 除 三。\n打印 甲。\n"),
    ("混合运算", "设 甲 为 一 加 二 乘 三。\n打印 甲。\n"),

    # ─── 比较运算 ───
    ("大于", "设 甲 为 五 大于 三。\n打印 甲。\n"),
    ("小于", "设 甲 为 二 小于 八。\n打印 甲。\n"),
    ("相等", "设 甲 为 三 等于 三。\n打印 甲。\n"),

    # ─── 逻辑运算 ───
    ("且（and）", "设 甲 为 真 且 真。\n打印 甲。\n设 乙 为 真 且 假。\n打印 乙。\n"),
    ("或（or）", "设 甲 为 真 或 假。\n打印 甲。\n设 乙 为 假 或 假。\n打印 乙。\n"),
    ("与（and 别名）", "设 甲 为 真 与 真。\n打印 甲。\n设 乙 为 假 与 真。\n打印 乙。\n"),

    # ─── 变量 ───
    ("变量声明和使用", "设 甲 为 十。\n设 乙 为 甲 加 五。\n打印 乙。\n"),
    ("变量重新赋值", "设 甲 为 一。\n设 甲 为 甲 加 一。\n打印 甲。\n"),

    # ─── 条件语句 ───
    ("如果-真分支", "设 甲 为 五。\n如果 甲 大于 三：\n打印 真。\n结束。\n"),
    ("如果-假分支", "设 甲 为 一。\n如果 甲 大于 三：\n打印 真。\n否则：\n打印 假。\n结束。\n"),

    # ─── 循环 ───
    ("当循环", "设 甲 为 一。\n当 甲 小于 四：\n打印 甲。\n设 甲 为 甲 加 一。\n结束。\n"),

    # ─── 自定义函数 ───
    ("无参数函数", "段 问候 接收：\n打印 \"你好\"。\n结束。\n问候。\n"),
    ("有参数函数", "段 加法 接收 甲, 乙 返回：\n返回 甲 加 乙。\n结束。\n设 结果 为 加法 三 五。\n打印 结果。\n"),

    # ─── 打印 ───
    ("多值打印", "打印 一。\n打印 二。\n打印 三。\n"),
]


@pytest.mark.parametrize("name,code", TEST_CASES, ids=[tc[0] for tc in TEST_CASES])
def test_dual_backend(name: str, code: str):
    """测试单个特性：比较 SRC 和 ANTLR 两个后端的输出"""
    src_output = None
    antlr_output = None
    src_error = None
    antlr_error = None

    try:
        src_output = run_src(code)
    except Exception as e:
        src_error = f"{type(e).__name__}: {e}"

    try:
        antlr_output = run_antlr(code)
    except Exception as e:
        antlr_error = f"{type(e).__name__}: {e}"

    if src_output == antlr_output:
        return  # 测试通过

    # 输出不一致，构造详细的失败信息
    src_display = src_output if src_output is not None else (src_error or "(无输出)")
    antlr_display = antlr_output if antlr_output is not None else (antlr_error or "(无输出)")
    pytest.fail(
        f"[{name}] 双后端输出不一致\n"
        f"     SRC:   {src_display}\n"
        f"     ANTLR: {antlr_display}"
    )


if __name__ == '__main__':
    """直接运行时执行旧风格的测试（兼容）"""
    import subprocess
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', __file__, '-v'],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    sys.exit(result.returncode)