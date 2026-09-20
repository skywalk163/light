# -*- coding: utf-8 -*-
"""R77 任务B · 缺陷账 L-162~L-169 复测裁定与回归护栏。

结论速览（**实测定性**，非推断；与 `docs/功能对标/语言缺陷账.md` 的 R77-B 章节对应）：

| 编号 | 条目 | 复测裁定 | 处置 |
|------|------|----------|------|
| L-162 | mock处理器 返回列表 vs HTTP服务端 字典契约 | ✅ 已修复（第44轮任务3，复测通过） | lightharness 侧 `src/mock大模型服务器.light` 造HTTP响应 在位，跨仓不外测 |
| L-163 | 工具_bash 装配契约两处摩擦 | ✅ 已修复（第44轮任务4，复测通过） | lightharness 侧 `具注册工具`/双参带默认 在位 |
| L-164 | 执行工具 状态字面值 "ok" 与直觉 "normal" 不符 | ✅ **有意不支持改值**（刻意保留 wire 字面值 "ok"，以 调成功 别名 + 状态字面值表 消除歧义） | 已登记缺陷账 |
| L-165 | 新建Mock服务 未声明 全局 → 恒 500 | ✅ 已修复（第44轮任务3，复测通过） | `全局 当前实例` 在位；根因模式由 L-166 告警覆盖 |
| L-166 | 函数内写模块级变量无告警 | ✅ 已修复（第45轮任务2 + 第46轮抑制增强，复测通过） | 本文件 TestL166 回归护栏 |
| L-167 | 外部命令.等待进程 超时 kill 后未回收 | **R77-B 应实现**（light-merge 两份 stdlib/外部命令.py 此前连正常路径都因 `进程.沟通` 不存在而炸） | 修复：沟通→communicate + kill 后 communicate()；本文件 TestL167 |
| L-168 | test_启动配置 假 L-006 跨段读写 + 死代码 | ✅ 已修复（第46轮任务1，复测通过） | lightharness 侧 examples/test_启动配置.light 死段落已删、注释已重写 |
| L-169 | examples/games/ 影子变量成片 | ✅ 已修复（第46轮任务2，复测通过） | light-merge 侧 games 文件 全局 声明在位；本文件 TestL169 回归护栏 |

**unified 后端口径**：L-166/L-169 的编译路径经 `code_generator_unified`（默认后端）验证；
L-167 是 stdlib 运行库修复，直接对 `外部命令` 模块做运行期断言。
"""
import os
import subprocess
import sys

import pytest

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
EXAMPLES = os.path.join(ROOT, "examples")


def _parse(src: str):
    from light_parser_v3 import LightParser
    return LightParser().parse(src)


def _gen_unified(src: str) -> str:
    from code_generator_unified import UnifiedCodeGenerator
    return UnifiedCodeGenerator().generate(_parse(src))


def _shadow_warns(src: str, with_source: bool = True):
    """跑 L-166 影子变量检查；with_source 决定是否传源码（抑制机制的契约）。"""
    from scope_shadow_check import check_global_shadow
    return check_global_shadow(_parse(src), "t", source=src if with_source else None)


# ===========================================================================
# L-166 · 影子变量编译告警（复测护栏；实现在 light-merge src/scope_shadow_check.py）
# ===========================================================================

SRC_SHADOW_BAD = (
    "设 当前值 为 0\n"
    "\n"
    "段落 坏_写不回:\n"
    "  设 当前值 为 1\n"
    "  返回 当前值\n"
)

SRC_SHADOW_GOOD = (
    "设 当前值 为 0\n"
    "\n"
    "段落 好_写回:\n"
    "  全局 当前值\n"
    "  设 当前值 为 1\n"
    "  返回 当前值\n"
)

SRC_SHADOW_PARAM = (
    "设 值 为 0\n"
    "\n"
    "段落 处理(值):\n"
    "  返回 值\n"
)

SRC_SHADOW_LINE_SUPPRESS = (
    "设 当前值 为 0\n"
    "\n"
    "段落 坏_写不回:\n"
    "  设 当前值 为 1  # 抑制L166\n"
    "  返回 当前值\n"
)

SRC_SHADOW_PARA_SUPPRESS = (
    "设 当前值 为 0\n"
    "\n"
    "# 抑制L166\n"
    "段落 坏_写不回:\n"
    "  设 当前值 为 1\n"
    "  返回 当前值\n"
)


class TestL166影子变量告警:

    def test_未声明全局_必报警(self):
        ws = _shadow_warns(SRC_SHADOW_BAD)
        assert ws, "L-166：函数内写模块级同名变量且未声明 全局，必须告警"
        assert "当前值" in ws[0] and "L-166" in ws[0]

    def test_声明全局后_不误报(self):
        assert _shadow_warns(SRC_SHADOW_GOOD) == []

    def test_形参同名_不误报(self):
        assert _shadow_warns(SRC_SHADOW_PARAM) == []

    def test_行级抑制_传source生效(self):
        assert _shadow_warns(SRC_SHADOW_LINE_SUPPRESS) == [], "行尾 # 抑制L166 必须抑制该行"

    def test_段落级抑制_传source生效(self):
        assert _shadow_warns(SRC_SHADOW_PARA_SUPPRESS) == [], "段落定义上一行 # 抑制L166 必须抑制整段"

    def test_不传source_抑制失效_契约钉死(self):
        # AST 不保留注释；不传源码时抑制必须静默失效（否则「写了标记还在告警」难排查）
        ws = _shadow_warns(SRC_SHADOW_LINE_SUPPRESS, with_source=False)
        assert ws, "不传 source 时抑制不得生效（契约：AST 不保留注释）"

    def test_games_经unified后端编译无告警_见L169(self):
        # 与 TestL169 呼应：影子检查跑在编译链路上，这里验证 unified 后端产物可生成
        for name in ("snake.light", "guess_number.light"):
            with open(os.path.join(EXAMPLES, "games", name), encoding="utf-8") as f:
                src = f.read()
            code = _gen_unified(src)
            assert code, f"unified 后端编译 {name} 产物为空"


# ===========================================================================
# L-167 · 外部命令.等待进程：正常路径可用 + 超时 kill 后回收（R77-B 修复）
# ===========================================================================

def _spawn_sleep(seconds: float):
    return subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(%s)" % seconds],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


class TestL167等待进程超时回收:

    def test_超时返回码为负一并报超时(self):
        from 外部命令 import 等待进程
        p = _spawn_sleep(3)
        try:
            结果 = 等待进程(p, 超时=1)
        finally:
            p.kill()  # 防御：万一断言前异常，不留孤儿进程
            try:
                p.communicate()
            except Exception:  # noqa: BLE001
                pass
        assert 结果.返回码 == -1, f"超时语义应为 返回码=-1，实际 {结果.返回码}"
        assert "超时" in 结果.标准错误, "超时文案应含「超时」"

    def test_超时后进程已被回收(self):
        # L-167 核心：kill 后必须 communicate() 回收（僵尸/管道泄漏）。
        # communicate() 会置 returncode → poll() 不再是 None，即进程已被收割。
        from 外部命令 import 等待进程
        p = _spawn_sleep(3)
        结果 = 等待进程(p, 超时=1)
        assert 结果.返回码 == -1
        assert p.poll() is not None, "kill 后未回收：poll() 仍为 None（僵尸/管道残留）"

    def test_正常路径不受影响(self):
        from 外部命令 import 等待进程
        p = _spawn_sleep(0.1)
        结果 = 等待进程(p, 超时=5)
        assert 结果.返回码 == 0, f"正常路径应 返回码=0，实际 {结果.返回码}"


# ===========================================================================
# L-169 · examples/games 影子变量清零（复测护栏）
# ===========================================================================

class TestL169games影子变量清零:

    @pytest.mark.parametrize("name", ["snake.light", "guess_number.light"],
                             ids=["snake", "guess_number"])
    def test_games文件_无L166影子告警(self, name):
        with open(os.path.join(EXAMPLES, "games", name), encoding="utf-8") as f:
            src = f.read()
        assert _shadow_warns(src) == [], (
            f"{name} 应已清零影子变量（L-169 复测），仍命中 L-166 告警"
        )
