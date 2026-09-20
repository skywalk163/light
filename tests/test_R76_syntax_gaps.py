# -*- coding: utf-8 -*-
"""R76 任务B · 语法补缺三项回归（G-12 异步生成器 / G-13 walrus / G-14 一等枚举）。

结论速览（**实测定性**，非推断；与 `docs/功能对标/语言缺陷账.md` 的 G-12/G-13/G-14 条目对应）：

* **G-12 异步生成器 + 异步上下文管理器 → 实测「已支持」**（R74-R75 期间落地，
  `examples/harness/编排.light` 等生产代码已在用 `异步 遍历` 消费）。
  本轮不实现新语法，只把它钉成回归护栏，防止将来退化。
* **G-13 walrus `:=` → 「有意不支持」**（设计内，源码原标注 P1-3）。
  `src/parser_expr.py` 的 `_parse_expr` 与 `_parse_logical_expr` 两处主动抛中文错误
  并给出替代写法；本轮如实登记，不实现。
* **G-14 一等枚举 → 本轮新实现**。`枚举 名：成员1, 成员2, …` 编译为
  `class 名(enum.Enum)` + 成员 `= enum.auto()`，天然获得 取值/构造(按值反查)/相等/哈希。
  两个后端（`code_generator` / `code_generator_unified`）必须出等价产物。

反向哨兵（非法形态必须报**中文**编译错误，不得泄漏 Python 原生异常）在本文件下半部。
"""
import contextlib
import io

import pytest


# ---------------------------------------------------------------------------
# 双后端驱动
# ---------------------------------------------------------------------------

def _parse(src: str):
    from light_parser_v3 import LightParser
    return LightParser().parse(src)


def _gen_src(src: str) -> str:
    from code_generator import PythonCodeGenerator
    return PythonCodeGenerator().generate(_parse(src))


def _gen_unified(src: str) -> str:
    from code_generator_unified import UnifiedCodeGenerator
    return UnifiedCodeGenerator().generate(_parse(src))


def _run(code: str) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(code, "<r76_prod>", "exec"), {"__name__": "__main__"})
    return buf.getvalue().strip().replace("\r\n", "\n")


BOTH = pytest.mark.parametrize("gen", [_gen_src, _gen_unified],
                               ids=["src后端", "unified后端"])


# ===========================================================================
# G-12 · 异步生成器 / 异步上下文管理器（已支持，防退化）
# ===========================================================================

GEN_ASYNC_SRC = (
    "异步 段落 计数(上界):\n"
    "  设 序号 为 0\n"
    "  当 序号 小于 上界:\n"
    "    生成 序号\n"
    "    序号 等于 序号 加 1\n"
)

GEN_SYNC_SRC = (
    "段落 计数(上界):\n"
    "  设 序号 为 0\n"
    "  当 序号 小于 上界:\n"
    "    生成 序号\n"
    "    序号 等于 序号 加 1\n"
)

ASYNC_CTX_SRC = (
    "段落 主():\n"
    "  使用 异步 空 为 甲：\n"
    "    打印(甲)\n"
)


class TestG12异步生成器已支持:
    """G-12：结论为「已支持」。这里断言的是**产物结构**，任何一端缺了都会红。"""

    def test_同步生成器_产出_yield(self):
        code = _gen_src(GEN_SYNC_SRC)
        assert "def 计数(" in code
        assert "yield 序号" in code

    @BOTH
    def test_异步生成器_产出_async_def_yield(self, gen):
        code = gen(GEN_ASYNC_SRC)
        assert "async def 计数(" in code, "异步段落的 async 限定丢失"
        assert "yield 序号" in code, "生成（yield）丢失"

    @BOTH
    def test_异步上下文管理器_产出_async_with(self, gen):
        code = gen(ASYNC_CTX_SRC)
        assert "async with " in code and " as 甲:" in code, (
            "「使用 异步 X 为 甲：」未编译成 async with（G-12 后半项退化）"
        )

    def test_异步遍历消费端_可运行(self):
        src = (
            GEN_ASYNC_SRC
            + "\n异步 段落 主测试:\n"
              "  设 累计 为 0\n"
              "  异步 遍历 甲 之 计数(4):\n"
              "    累计 等于 累计 加 甲\n"
              "  打印 累计\n"
              "\n异步 运行 主测试()\n"
        )
        code = _gen_src(src)
        assert _run(code) == "6", "异步生成器经 异步 遍历 消费的求和不对"


# ===========================================================================
# G-13 · walrus（有意不支持）
# ===========================================================================

class TestG13walrus有意不支持:
    """G-13：结论为「有意不支持」。断言错误必须是**中文**且带替代写法。"""

    @pytest.mark.parametrize("src", [
        "段落 主():\n    设 甲 为 (乙 := 5)\n",
        "段落 主():\n    如果 (甲 := 3) 大于 1：\n        打印(甲)\n",
        "段落 主():\n    设 甲 为 0\n    当 (甲 := 甲 加 1) 小于 3：\n        打印(甲)\n",
    ], ids=["赋值位", "条件位", "循环条件位"])
    def test_哨兵_walrus_中文错误(self, src):
        with pytest.raises(Exception) as ei:
            _parse(src)
        msg = str(ei.value)
        assert "海象" in msg, f"未给出海象运算符的中文诊断：{msg[:200]}"
        assert "设" in msg, "未给出「设」语句替代写法"
        assert "Traceback" not in msg, "泄漏了 Python 原生异常"


# ===========================================================================
# G-14 · 一等枚举（本轮实现）
# ===========================================================================

ENUM_BASIC_SRC = (
    "枚举 颜色：红, 绿, 蓝\n"
    "\n"
    "段落 主()：\n"
    "  打印(颜色.红)\n"
    "  打印(颜色.红 等于 颜色.绿)\n"
)

ENUM_SEMANTICS_SRC = (
    "枚举 颜色：红, 绿, 蓝\n"
    "枚举 状态：开, 关\n"
    "\n"
    "段落 主()：\n"
    "  打印(颜色.红 等于 颜色.红)\n"
    "  打印(颜色.红 等于 状态.开)\n"
    "  打印(颜色(2))\n"
    "  设 表 为 {}\n"
    "  表[颜色.蓝] 等于 \"B\"\n"
    "  打印(表[颜色.蓝])\n"
    "\n主()\n"
)


def _enum_keylines(code: str):
    """抽出枚举相关的语义行（两端引导代码不同，只比这些）。"""
    out = []
    for ln in code.splitlines():
        s = ln.strip()
        if s.startswith("class 颜色") or s.startswith("class 状态"):
            out.append(s)
        elif s.endswith("= enum.auto()"):
            out.append(s)
        elif s.startswith("import enum"):
            out.append(s)
    return out


class TestG14一等枚举:

    def test_双后端产物等价(self):
        a, b = _gen_src(ENUM_BASIC_SRC), _gen_unified(ENUM_BASIC_SRC)
        assert _enum_keylines(a) == _enum_keylines(b), (
            "两个后端的枚举产物不parity\nsrc:\n{}\nunified:\n{}".format(
                _enum_keylines(a), _enum_keylines(b))
        )

    def test_产物结构_enum基类与成员(self):
        for gen in (_gen_src, _gen_unified):
            code = gen(ENUM_BASIC_SRC)
            assert "class 颜色(enum.Enum):" in code
            assert "红 = enum.auto()" in code
            assert "绿 = enum.auto()" in code
            assert "蓝 = enum.auto()" in code
            assert "import enum" in code

    def test_四语义_取值构造相等哈希_可运行(self):
        for gen in (_gen_src, _gen_unified):
            out = _run(gen(ENUM_SEMANTICS_SRC))
            lines = out.splitlines()
            assert lines[0] == "True", "同成员相等失败"
            assert lines[1] == "False", "跨枚举同名成员隔离失败"
            assert lines[2] == "颜色.绿", "按值构造（颜色(2)→绿）失败"
            assert lines[3] == "B", "枚举作字典键（哈希）失败"

    def test_双后端运行结果一致(self):
        assert _run(_gen_src(ENUM_SEMANTICS_SRC)) == _run(_gen_unified(ENUM_SEMANTICS_SRC))


class TestG14反向哨兵:
    """非法枚举形态必须报中文编译错误。"""

    @pytest.mark.parametrize("src,片段", [
        ("枚举 颜色：\n\n段落 主()：\n  打印(1)\n", "枚举至少需要一个成员"),
        ("枚举 颜色：红, 绿, 红\n\n段落 主()：\n  打印(1)\n", "重复定义"),
        ("枚举 颜色 红, 绿\n\n段落 主()：\n  打印(1)\n", "枚举"),
    ], ids=["空成员表", "成员重名", "缺冒号"])
    def test_哨兵_中文错误(self, src, 片段):
        with pytest.raises(Exception) as ei:
            _parse(src)
        msg = str(ei.value)
        assert 片段 in msg, f"未命中预期中文诊断片段 {片段!r}：{msg[:200]}"
        assert "Traceback" not in msg, "泄漏了 Python 原生异常"


# ===========================================================================
# 邻项不回归：G-10 记录 / C FFI 的 `外部 枚举`
# ===========================================================================

class Test邻项不回归:

    def test_记录_dataclass_仍生效(self):
        src = "记录 点: x, y\n\n段落 主()：\n  设 甲 为 点(1, 2)\n  打印(甲.x)\n"
        for gen in (_gen_src, _gen_unified):
            code = gen(src)
            assert "@dataclasses.dataclass(unsafe_hash=True)" in code
            assert "enum.Enum" not in code, "记录被误判成枚举"

    def test_C_FFI枚举_仍走独立路径(self):
        # `外部 枚举 X { … }` 是 C FFI 形态（FFIEnumDef），与一等枚举无关
        code = _gen_src("外部 枚举 颜色 { 红 = 1, 绿 = 2 }\n")
        assert "enum.auto" not in code
        assert "enum.Enum" not in code

    def test_普通类不受影响(self):
        src = "类 犬：\n  段落 构造(名)：\n    己.名 等于 名\n\n段落 主()：\n  设 甲 为 犬(\"阿黄\")\n  打印(甲.名)\n"
        for gen in (_gen_src, _gen_unified):
            code = gen(src)
            assert "enum.Enum" not in code
            assert "def __init__(self, 名):" in code
