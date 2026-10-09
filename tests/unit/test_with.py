# -*- coding: utf-8 -*-
"""R129-D（M3）· `与 表达式 为 变量: 块` 资源管理语法糖测试。

背景（known_issues G3）：AI 写光明代码时第一反应写 `with` / 资源管理语句，
此前没有「与 … 为 …」这类贴近中文直觉的语法糖，且 stdlib 文件 API 多轨并存。
R129-D 在 `parser_stmt.py` 新增语句头 `与`（`与` 在表达式层仍是「逻辑 AND」
中缀运算符，只在语句头劫持），desugar 成：设 变量 为 表达式; 尝试: 块 最终: 变量.关闭()。

与 `使用`（Python 上下文管理器 __enter__/__exit__ 协议）不同，「与」走鸭子类型：
要求被管理对象拥有 `关闭()` 方法（或 Python 内置的 close()）。

判据（R129 任务书 §5.2，均为实跑核对）：
  · 单资源：块结束后 关闭() 被调用（正常路径释放）；
  · 异常路径：块内抛异常，关闭() 仍被调用且异常继续向上传播；
  · 多资源 `与 a 为 x, b 为 y:`：获取在外、释放在内，逆序释放；
  · 文件读 / 文件写 / 互斥锁 三类资源场景资源正确释放；
  · 中缀 `与`（逻辑 AND）不受语句头劫持影响（回归护栏）。
"""
import io
import os
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (_ROOT, os.path.join(_ROOT, "src"), os.path.join(_ROOT, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402


def _gen(code: str):
    """解析 → 生成 Python 源码（不执行），返回源码字符串。"""
    ast = LightParser().parse(code)
    return PythonCodeGenerator().generate(ast)


def _run_light(code: str) -> str:
    """解析 → 生成 Python → exec，返回标准输出（strip 后）。"""
    py_code = _gen(code)
    namespace = {
        "__name__": "__main__",
        "__file__": os.path.join(_ROOT, "_r129_with_probe.py"),
    }
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(compile(py_code, "<r129-with>", "exec"), namespace)
        return sys.stdout.getvalue().strip()
    finally:
        sys.stdout = old_stdout


def _run_light_expect_error(code: str):
    """执行，返回 (stdout, raised_exception)。异常被捕获后向上层报告。"""
    py_code = _gen(code)
    namespace = {
        "__name__": "__main__",
        "__file__": os.path.join(_ROOT, "_r129_with_probe.py"),
    }
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    raised = None
    try:
        try:
            exec(compile(py_code, "<r129-with-err>", "exec"), namespace)
        except Exception as _e:  # noqa: BLE001
            raised = _e
        return sys.stdout.getvalue().strip(), raised
    finally:
        sys.stdout = old_stdout


_TMP = tempfile.gettempdir().replace("\\", "/")


# ── §5.2 基本：单资源正常路径释放 ───────────────────────────────────────────
def test_单资源_正常路径_块后释放():
    """`与 新建 资源("A") 为 r:` → 块结束后 r.关闭() 被调用。"""
    code = (
        "设 关闭记录 为 []\n"
        "类 资源:\n"
        "    段落 构造(名字):\n"
        "        设 己.名字 为 名字\n"
        "    段落 关闭():\n"
        "        关闭记录.追加(己.名字)\n"
        "段落 主():\n"
        "    与 新建 资源(\"A\") 为 r:\n"
        "        打印(r.名字)\n"
        "主()\n"
        "打印(关闭记录)"
    )
    out = _run_light(code)
    assert out == "A\n['A']"


def test_变量可在块内使用():
    """绑定的资源变量在块内可见且可调用方法。"""
    code = (
        "设 日志 为 []\n"
        "类 资源:\n"
        "    段落 构造(名字):\n"
        "        设 己.名字 为 名字\n"
        "    段落 标签():\n"
        "        返回 \"资源-\" + 己.名字\n"
        "    段落 关闭():\n"
        "        设 己.已关闭 为 真\n"
        "段落 主():\n"
        "    与 新建 资源(\"db\") 为 r:\n"
        "        日志.追加(r.标签())\n"
        "主()\n"
        "打印(日志)"
    )
    assert _run_light(code) == "['资源-db']"


# ── §5.2 异常路径：仍释放且异常传播 ───────────────────────────────────────
def test_异常路径_仍释放_且异常传播():
    """块内抛异常：finally 里的 关闭() 仍执行（打印），异常继续向上传播。"""
    code = (
        "类 资源2:\n"
        "    段落 关闭():\n"
        "        打印(\"closed\")\n"
        "段落 主():\n"
        "    与 新建 资源2() 为 r:\n"
        "        抛出 新建 异常(\"boom\")\n"
        "主()"
    )
    out, raised = _run_light_expect_error(code)
    # 关闭() 在 finally 里被调用（异常传播前打印，故仍出现在 stdout）
    # 注：不再单独断 `raised is not None`（零信号断言，assert_quality 门判红）；
    #     下一行 `"boom" in str(raised)` 已同时覆盖「异常非 None」与「异常内容正确」。
    assert "boom" in str(raised)
    assert "closed" in out


# ── §5.2 多资源：逆序释放 ─────────────────────────────────────────────────
def test_多资源_获取在外_逆序释放():
    """`与 新建 R(\"x\") 为 a, 新建 R(\"y\") 为 b:` → 先 body，再 y，再 x。"""
    code = (
        "设 顺序 为 []\n"
        "类 R:\n"
        "    段落 构造(名):\n"
        "        设 己.名 为 名\n"
        "    段落 关闭():\n"
        "        顺序.追加(己.名)\n"
        "段落 主():\n"
        "    与 新建 R(\"x\") 为 a, 新建 R(\"y\") 为 b:\n"
        "        顺序.追加(\"body\")\n"
        "主()\n"
        "打印(顺序)"
    )
    assert _run_light(code) == "['body', 'y', 'x']"


# ── §5.2 文件读 / 文件写 场景 ─────────────────────────────────────────────
def test_文件读写_资源释放():
    """文件读写场景：用中文文件资源类包裹 打开文件，退出块时 关闭() 释放。"""
    path = f"{_TMP}/r129_with_file.tmp"
    try:
        if os.path.exists(path):
            os.remove(path)
        code = (
            "类 文本文件:\n"
            "    段落 构造(路径, 模式):\n"
            "        设 己.句柄 为 打开文件(路径, 模式, encoding=\"utf-8\")\n"
            "    段落 写入(内容):\n"
            "        己.句柄.write(内容)\n"
            "    段落 读取():\n"
            "        返回 己.句柄.read()\n"
            "    段落 关闭():\n"
            "        己.句柄.close()\n"
            "段落 主():\n"
            f"    与 新建 文本文件(\"{path}\", \"w\") 为 f:\n"
            "        f.写入(\"hello\")\n"
            f"    与 新建 文本文件(\"{path}\", \"r\") 为 g:\n"
            "        打印(g.读取())\n"
            "主()"
        )
        assert _run_light(code) == "hello"
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_关闭方法缺失_回退close_原生文件对象():
    """仅带 Python close() 的对象（打开文件返回的裸文件）走 else 分支回退 close()。"""
    path = f"{_TMP}/r129_with_fallback.tmp"
    try:
        if os.path.exists(path):
            os.remove(path)
        code = (
            "段落 主():\n"
            f"    与 打开文件(\"{path}\", \"w\", encoding=\"utf-8\") 为 f:\n"
            "        打印(\"fallback-ok\")\n"
            "主()"
        )
        assert _run_light(code) == "fallback-ok"
    finally:
        if os.path.exists(path):
            os.remove(path)


# ── §5.2 互斥锁 场景 ─────────────────────────────────────────────────────
def test_互斥锁_持有与释放():
    """互斥锁场景：块内持有，块外已释放，块后代码照常执行。"""
    code = (
        "设 状态 为 []\n"
        "类 互斥锁:\n"
        "    段落 构造(名):\n"
        "        设 己.名 为 名\n"
        "    段落 关闭():\n"
        "        状态.追加(\"释放-\" + 己.名)\n"
        "段落 主():\n"
        "    与 新建 互斥锁(\"db\") 为 m:\n"
        "        状态.追加(\"持有-\" + m.名)\n"
        "    状态.追加(\"块外\")\n"
        "主()\n"
        "打印(状态)"
    )
    assert _run_light(code) == "['持有-db', '释放-db', '块外']"


# ── 单行体 ───────────────────────────────────────────────────────────────
def test_单行体_with():
    """`与 … 为 s: 打印("ok")` 单行体也能解析并运行。"""
    code = (
        "类 S:\n"
        "    段落 关闭():\n"
        "        设 己.标志 为 真\n"
        "段落 主():\n"
        "    与 新建 S() 为 s: 打印(\"ok\")\n"
        "主()"
    )
    assert _run_light(code) == "ok"


# ── 嵌套 与 ──────────────────────────────────────────────────────────────
def test_嵌套与_释放顺序():
    """外层 与 的块内含内层 与：内层先释放，外层后释放。"""
    code = (
        "设 记录 为 []\n"
        "类 N:\n"
        "    段落 关闭():\n"
        "        记录.追加(\"N\")\n"
        "段落 主():\n"
        "    与 新建 N() 为 a:\n"
        "        与 新建 N() 为 b:\n"
        "            记录.追加(\"inner\")\n"
        "主()\n"
        "打印(记录)"
    )
    assert _run_light(code) == "['inner', 'N', 'N']"


# ── 回归护栏：中缀 与（逻辑 AND）不受影响 ─────────────────────────────────
def test_中缀与_仍作逻辑AND_回归():
    """`真 与 假` 仍解析为逻辑 AND → False；语句头劫持不破坏中缀 与。"""
    code = (
        "段落 主():\n"
        "    设 r 为 (真 与 假)\n"
        "    打印(r)\n"
        "主()"
    )
    assert _run_light(code) == "False"


def test_中缀与_在表达式内_与语句头共存():
    """块内使用逻辑 与，同文件存在语句头 与，二者互不干扰。"""
    code = (
        "设 日志 为 []\n"
        "类 R:\n"
        "    段落 关闭():\n"
        "        日志.追加(\"closed\")\n"
        "段落 主():\n"
        "    设 条件 为 (真 与 真)\n"
        "    与 新建 R() 为 r:\n"
        "        日志.追加(条件)\n"
        "主()\n"
        "打印(日志)"
    )
    assert _run_light(code) == "[True, 'closed']"


# ── codegen 形态：desugar 成 try/finally + 关闭() ─────────────────────────
def test_codegen_单资源_desugar_形态():
    """生成的 Python 应为 `var = expr; try: ... finally: var.关闭()/var.close()`。"""
    code = "与 打开文件(\"f.txt\") 为 fh:\n    打印(fh)"
    py = _gen(code)
    assert "fh = open(\"f.txt\")" in py
    assert "try:" in py
    assert "finally:" in py
    # 裸文件对象只有 close() → 走 else 分支回退
    assert "fh.close()" in py
    assert "getattr(fh, '关闭', None)" in py


def test_codegen_多资源_嵌套_try_finally():
    """多资源生成两层嵌套 try/finally，释放逆序。"""
    code = "与 新建 A() 为 a, 新建 B() 为 b:\n    打印(\"x\")"
    py = _gen(code)
    # 运行时前导里只有 try/except，没有 finally:；finally: 仅来自本 desugar
    assert py.count("finally:") == 2
    assert py.count("_a__close = getattr") == 1 and py.count("_b__close = getattr") == 1
    # a 在外层、b 在内层：b 的 finally 先于 a 的 finally
    pos_a = py.index("_a__close")
    pos_b = py.index("_b__close")
    assert pos_b < pos_a, "内层资源 b 的释放应排在外层资源 a 之前"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
