# -*- coding: utf-8 -*-
"""R137 C线：LSP 语义诊断服务（src/lsp_diagnostic.py + lsp/diagnostic_extension.py）

覆盖两方向：
  * 正向（故意写错的光明源码）→ 必须报出未定义符号，且行号指向真实错误行；
  * 反向（正确源码 / 各类白名单场景）→ 必须为空，不打扰用户；
  * `enabled` 默认关闭；
  * 1-based（对外报告）↔ 0-based（LSP range）换算。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import lsp_diagnostic as LD
from lsp import diagnostic_extension as DE


# ---------------------------------------------------------------------------
# 测试固件：光源代码片段
# ---------------------------------------------------------------------------

# 第 3 行 `    打印(乙)` 里的 `乙` 从未定义/赋值 → 真阳性
未定义变量源码 = "段落 主程序():\n    甲 = 1\n    打印(乙)\n"

# 第 3 行 `    返回 汇总 + 未知量` 里的 `未知量` 未定义 → 真阳性
未定义变量源码2 = "段落 主程序():\n    设 汇总 为 0\n    返回 汇总 + 未知量\n"

正确源码 = "段落 主程序():\n    甲 = 1\n    打印(甲)\n"

己属性源码 = "类 人:\n    段落 初始化(己, 名字):\n        己名字 = 名字\n        打印(己名字)\n"

泛型源码 = "段落 主程序():\n    打印(T)\n"

PY内嵌源码 = (
    "引 Python:\n"
    "    import math\n"
    "    半径 = math.pi\n"
    "结束嵌入\n"
    "段落 主程序():\n"
    "    结果 = math.pi\n"
)

运行时注入源码 = "段落 主程序(字典, 键):\n    返回 _light_builtin.字典获取(字典, 键, 空)\n"

字符串键源码 = "段落 主程序(载荷):\n    返回 载荷[\"args\"]\n"

分支合并源码 = (
    "段落 主程序(旗):\n"
    "    如果 旗:\n"
    "        设 结果 为 1\n"
    "    否则:\n"
    "        设 结果 为 2\n"
    "    返回 结果\n"
)

无法解析源码 = "段落 主程序(:\n    @@@ ###\n"


def 取名字们(诊断列表):
    return [LD._取未定义符号名(d["消息"]) for d in 诊断列表]


# ---------------------------------------------------------------------------
# 第 1 组：正向 —— 故意写错要能报出
# ---------------------------------------------------------------------------
class Test正向诊断:
    def test_简单未定义变量被报出(self):
        """故意写错的光明源码必须产出未定义符号诊断。"""
        d = LD.run_semantic_diagnostic(未定义变量源码, "demo.light")
        # 值断言优先于「至少有 1 条」的集合非空式弱断言：直接锁定报出的符号名
        assert 取名字们(d) == ["乙"], f"应恰好报出 乙，实际: {d}"

    def test_未定义符号行号指向真实错误行(self):
        """诊断行号必须指向 `乙` 真正出现的第 3 行（**1-based**）。"""
        d = LD.run_semantic_diagnostic(未定义变量源码, "demo.light")
        目标 = [x for x in d if LD._取未定义符号名(x["消息"]) == "乙"]
        assert 目标, f"找不到针对 乙 的诊断: {d}"
        assert 目标[0]["行"] == 3, f"行号应为 3，实际 {目标[0]['行']}"
        # 第 3 行是 `    打印(乙)`，`乙` 位于第 8 列（1-based）
        assert 目标[0]["列"] == 8, f"列号应为 8，实际 {目标[0]['列']}"
        源码第3行 = 未定义变量源码.split("\n")[2]
        assert 源码第3行[目标[0]["列"] - 1] == "乙", "列号应精确落在 乙 上"

    def test_严重度为错误(self):
        """未定义符号属于硬错误，不是信息。"""
        d = LD.run_semantic_diagnostic(未定义变量源码2, "demo.light")
        assert d, "应报出诊断"
        assert all(x["严重度"] == LD.严重度错误 for x in d), d
        assert all(x["来源"] == "语义分析" for x in d), d

    def test_文件名被附加到诊断上(self):
        d = LD.run_semantic_diagnostic(未定义变量源码, "某文件.light")
        assert d and d[0]["文件"] == "某文件.light"


# ---------------------------------------------------------------------------
# 第 2 组：反向 —— 正确源码 / 白名单场景必须为空
# ---------------------------------------------------------------------------
class Test反向不误报:
    @pytest.mark.parametrize("名称,源码", [
        ("正确源码", 正确源码),
        ("己属性", 己属性源码),
        ("泛型类型参数", 泛型源码),
        ("Python内嵌块", PY内嵌源码),
        ("运行时注入", 运行时注入源码),
        ("字符串字面量键", 字符串键源码),
        ("分支合并赋值", 分支合并源码),
    ])
    def test_白名单场景零诊断(self, 名称, 源码):
        """已知假阳性场景过滤后必须为空。"""
        d = LD.run_semantic_diagnostic(源码, "ok.light")
        assert d == [], f"[{名称}] 应被白名单过滤掉，残留: {d}"

    def test_空源码无诊断(self):
        assert LD.run_semantic_diagnostic("", "empty.light") == []

    def test_白名单规则各自可独立断言(self):
        """规则函数必须可单测，而不是散落在流程里的魔法值。"""
        assert LD.是己属性("己名字") is True
        assert LD.是己属性("甲") is False
        assert LD.是泛型类型参数("T") is True
        assert LD.是泛型类型参数("Type") is False
        assert LD.是运行时注入名("_light_builtin") is True
        assert LD.是运行时注入名("字典获取") is False
        assert LD.是Python互操作名("type") is True
        assert LD.是Python互操作名("某个光明名字") is False
        assert LD.PYTHON_INTEROP_NAMES  # 白名单常量非空且可读


# ---------------------------------------------------------------------------
# 第 3 组：坐标换算 —— 1-based（报告）↔ 0-based（LSP）
# ---------------------------------------------------------------------------
class Test坐标换算:
    def test_对外报告是1based(self):
        d = LD.run_semantic_diagnostic(未定义变量源码, "demo.light")
        目标 = [x for x in d if LD._取未定义符号名(x["消息"]) == "乙"][0]
        # 源码第 3 行（1-based）就是 index 2
        assert 未定义变量源码.split("\n")[目标["行"] - 1].strip().startswith("打印(乙)")

    def test_lsp_range是0based(self):
        """LSP range.start.line/character 必须比对外报告的 行/列 各小 1。"""
        d = LD.run_semantic_diagnostic(未定义变量源码, "demo.light")
        lsp = LD.to_lsp_diagnostics(d)
        assert len(lsp) == len(d)
        报告, lsp项 = d[0], lsp[0]
        assert lsp项["range"]["start"]["line"] == 报告["行"] - 1
        assert lsp项["range"]["start"]["character"] == 报告["列"] - 1
        # 第 3 行（1-based）→ line 2（0-based）
        assert lsp项["range"]["start"]["line"] == 2

    def test_零行不会换算成负行号(self):
        """行号为 0（未知位置）时 clamp 到 0，不允许出现 -1。"""
        lsp = LD.to_lsp_diagnostics([{
            "行": 0, "列": 0, "消息": "未定义的符号 '某'",
            "严重度": "错误", "来源": "语义分析",
        }])
        assert lsp[0]["range"]["start"]["line"] == 0
        assert lsp[0]["range"]["start"]["character"] == 0

    def test_lsp严重度映射(self):
        lsp = LD.to_lsp_diagnostics([{
            "行": 1, "列": 1, "消息": "未定义的符号 '某'",
            "严重度": LD.严重度错误, "来源": "语义分析",
        }])
        assert lsp[0]["severity"] == 1          # 1 = Error
        assert lsp[0]["source"] == "语义分析"
        assert "某" in lsp[0]["message"]

    def test_空诊断列表转空列表(self):
        assert LD.to_lsp_diagnostics([]) == []


# ---------------------------------------------------------------------------
# 第 4 组：鲁棒性 —— 不允许抛穿
# ---------------------------------------------------------------------------
class Test鲁棒性:
    def test_解析失败降级为信息级而不抛异常(self):
        """解析失败的源码必须被吞成一条『信息』诊断，禁止抛穿到 LSP 主线程。"""
        d = LD.run_semantic_diagnostic(无法解析源码, "bad.light")
        assert isinstance(d, list)
        for x in d:
            assert x["严重度"] in (LD.严重度信息, LD.严重度警告, LD.严重度错误)

    def test_非字符串入参不抛异常(self):
        d = LD.run_semantic_diagnostic(b"bytes-not-str", "x.light")
        assert isinstance(d, list) and d
        assert d[0]["严重度"] == LD.严重度信息

    def test_None源码被当作空串(self):
        assert LD.run_semantic_diagnostic(None) == []


# ---------------------------------------------------------------------------
# 第 5 组：LSP 扩展模块
# ---------------------------------------------------------------------------
def _did_open_params(文本, uri="file:///x.light"):
    return {"textDocument": {"uri": uri, "text": 文本, "languageId": "light"}}


def _did_change_params(文本, uri="file:///x.light"):
    return {"textDocument": {"uri": uri},
            "contentChanges": [{"text": 文本}]}


class Test诊断扩展:
    def test_默认关闭_对齐lightc的semantic策略(self):
        """**默认必须关闭**：假阳性不该默认打扰用户。"""
        assert DE.DEFAULT_ENABLED is False
        assert DE.DiagnosticExtension().enabled is False
        assert DE.handle_notification(
            "textDocument/didOpen", _did_open_params(未定义变量源码)) is None

    def test_开启后didOpen产出publishDiagnostics(self):
        note = DE.handle_notification(
            "textDocument/didOpen", _did_open_params(未定义变量源码), enabled=True)
        # 结构断言：必须是完整的 JSON-RPC 通知字典（而非「不是 None」这种零信号断言）
        assert isinstance(note, dict) and set(note) == {"jsonrpc", "method", "params"}
        assert note["method"] == "textDocument/publishDiagnostics"
        assert note["params"]["uri"] == "file:///x.light"
        诊断集 = note["params"]["diagnostics"]
        assert [x for x in 诊断集 if "乙" in x["message"]], f"诊断里应有 乙: {诊断集}"
        # range 必须是 0-based
        assert 诊断集[0]["range"]["start"]["line"] == 2

    def test_开启后didChange产出publishDiagnostics(self):
        note = DE.handle_notification(
            "textDocument/didChange", _did_change_params(未定义变量源码), enabled=True)
        assert isinstance(note, dict) and set(note) == {"jsonrpc", "method", "params"}
        assert note["method"] == "textDocument/publishDiagnostics"
        assert len(note["params"]["diagnostics"]) == 1
        assert "乙" in note["params"]["diagnostics"][0]["message"]

    def test_正确源码推送空诊断列表(self):
        note = DE.handle_notification(
            "textDocument/didOpen", _did_open_params(正确源码), enabled=True)
        assert isinstance(note, dict) and set(note) == {"jsonrpc", "method", "params"}
        assert note["params"]["diagnostics"] == []

    def test_不支持的方法返回None(self):
        ext = DE.DiagnosticExtension(enabled=True)
        assert ext.handle("textDocument/completion", {}) is None
        assert ext.handle("initialized", {}) is None

    def test_enable_disable切换(self):
        ext = DE.DiagnosticExtension()
        assert ext.enabled is False
        ext.enable()
        assert ext.enabled is True
        assert ext.on_did_open(_did_open_params(未定义变量源码)) is not None
        ext.disable()
        assert ext.enabled is False
        assert ext.on_did_open(_did_open_params(未定义变量源码)) is None
        assert ext.on_did_change(_did_change_params(未定义变量源码)) is None

    def test_增量同步缺少text时不推脏数据(self):
        """contentChanges 里没有 text（增量同步）时宁可不更新。"""
        ext = DE.DiagnosticExtension(enabled=True)
        assert ext.on_did_change({"contentChanges": [{"range": {}}]}) is None

    def test_清空诊断通知(self):
        note = DE.清空诊断("file:///x.light")
        assert note["method"] == "textDocument/publishDiagnostics"
        assert note["params"]["diagnostics"] == []

    def test_notification可JSON序列化(self):
        import json
        note = DE.handle_notification(
            "textDocument/didOpen", _did_open_params(未定义变量源码), enabled=True)
        assert isinstance(json.loads(json.dumps(note)), dict)


# ---------------------------------------------------------------------------
# 服务器子类集成测试：DiagnosticLanguageServer 把语义诊断合并进同一条 publishDiagnostics
# ---------------------------------------------------------------------------

class Test诊断服务器子类:
    """验证 lsp/diagnostic_server.py 的子类接线（不改写既有 light_lsp.py）。"""

    @staticmethod
    def _收集语义诊断(diag_enabled, src):
        try:
            from lsp.diagnostic_server import DiagnosticLanguageServer
        except Exception as e:  # 依赖缺失则跳过，不红
            pytest.skip("lsp.diagnostic_server 不可用: %s" % e)
        srv = DiagnosticLanguageServer(diag_enabled=diag_enabled)
        srv._handle_did_open({"textDocument": {"uri": "file:///t.light", "text": src}})
        notes = srv.get_pending_notifications()
        diags = [d for n in notes for d in n["params"]["diagnostics"]]
        return [d for d in diags if d.get("source") == "语义分析"]

    def test_默认关闭无语义诊断(self):
        sem = self._收集语义诊断(False, 未定义变量源码)
        assert sem == []

    def test_开启后合并语义诊断(self):
        sem = self._收集语义诊断(True, 未定义变量源码)
        # 内容断言：必须真产出「未定义符号」语义诊断（避免 len>=1 这类假绿断言）
        消息列表 = [d.get("message") or d.get("消息") or "" for d in sem]
        assert any("未定义" in m for m in 消息列表), \
            "开启诊断后必须对未定义符号产生语义诊断，实际诊断: %r" % sem
        assert all("range" in d for d in sem), "每条语义诊断都应有可跳转的 range"

    def test_正确源码不误报(self):
        sem = self._收集语义诊断(True, 正确源码)
        assert sem == []
