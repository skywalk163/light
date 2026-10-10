#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R137：LSP 诊断扩展（**新增文件，不修改 `lsp/` 既有任何文件**）。

作用：给既有光明 LSP 服务器补上**语义级**诊断（未定义符号等），替代原来
`lsp/light_lsp_server.py:215` 里「扫描可疑字符 `?`」的占位实现。

为什么是独立模块
----------------
`lsp/light_lsp.py` 是 145KB 的巨物、`lsp/light_lsp_server.py` 是光明源码编译
出来的产物。本扩展**不改写它们**，只暴露可被调用的函数/类，由外部接线：

    from lsp.diagnostic_extension import handle_notification
    note = handle_notification("textDocument/didOpen", params, enabled=True)

开关策略（对齐 R135）
--------------------
`enabled` **默认 False**。理由与 `cli/lightc.py:166` 的 `--semantic` 一致：
v3 语义分析的未定义符号判定存在假阳性，默认开启会打扰用户。上层 CLI 的
`--diagnostic` 开关（`cli/light.py`，由主控接入）显式打开后才启用。

坐标换算
--------
`textDocument/publishDiagnostics` 的 `range` 一律 **0-based**。
`src/lsp_diagnostic.run_semantic_diagnostic()` 返回的「行/列」是 1-based，
转换在 `src/lsp_diagnostic.to_lsp_diagnostics()` 里统一完成，本模块不再二次换算。
"""

import os
import sys
from typing import Any, Dict, List, Optional

# 让 `src/` 在 path 上（与 cli/lightc.py 的做法一致），这样直接从任意 cwd
# import 本模块都能拿到语义分析器。
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _ROOT):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from lsp_diagnostic import run_semantic_diagnostic, to_lsp_diagnostics
except ImportError:  # pragma: no cover - 依赖缺失时降级为「无诊断」
    run_semantic_diagnostic = None  # type: ignore[assignment]
    to_lsp_diagnostics = None  # type: ignore[assignment]

__all__ = [
    "DiagnosticExtension",
    "DEFAULT_ENABLED",
    "handle_notification",
    "publish_diagnostics_for_source",
    "build_publish_diagnostics",
    "DIAGNOSTIC_SOURCE_NAME",
]

#: 诊断来源标识，客户端可按 source 过滤
DIAGNOSTIC_SOURCE_NAME = "语义分析"

#: **默认关闭** —— 见模块 docstring「开关策略」
DEFAULT_ENABLED = False

_PUBLISH_METHOD = "textDocument/publishDiagnostics"

def _get(d: Any, key: str, default: Any = None) -> Any:
    """安全的字典取值（params 可能来自不受信任的 JSON-RPC）。"""
    if isinstance(d, dict):
        return d.get(key, default)
    return default


def _抽取didOpen文本(params: Any) -> str:
    """`didOpen`：params.textDocument.text。"""
    doc = _get(params, "textDocument", {})
    return _get(doc, "text", "") or ""


def _抽取didChange文本(params: Any) -> str:
    """`didChange`：优先取全量同步的 contentChanges[0].text。

    增量同步（缺 text 字段）时无法还原全文，返回空串，由调用方决定是否清空调。
    """
    changes = _get(params, "contentChanges") or []
    if isinstance(changes, (list, tuple)) and changes:
        return _get(changes[0], "text", "") or ""
    return ""


def _抽取uri(params: Any) -> str:
    """从 params 里取出文档 uri（didOpen/didChange 结构不同）。"""
    doc = _get(params, "textDocument")
    if isinstance(doc, dict):
        uri = _get(doc, "uri")
        if uri:
            return uri
    return _get(params, "uri", "") or ""


def publish_diagnostics_for_source(uri: str, 源码: str, 文件名: Optional[str] = None) -> List[Dict[str, Any]]:
    """对一段源码跑语义诊断并转成 LSP `Diagnostic[]`。

    任一步异常都被吞掉并返回空列表——诊断失败不应该让编辑器会话崩掉。
    """
    if run_semantic_diagnostic is None or to_lsp_diagnostics is None:
        return []
    if not isinstance(源码, str) or not 源码:
        return []
    try:
        诊断列表 = run_semantic_diagnostic(源码, 文件名)
        return to_lsp_diagnostics(诊断列表)
    except Exception:
        return []


def build_publish_diagnostics(uri: str, 源码: str,
                              文件名: Optional[str] = None) -> Dict[str, Any]:
    """构造一条完整的 `textDocument/publishDiagnostics` 通知字典。"""
    return {
        "jsonrpc": "2.0",
        "method": _PUBLISH_METHOD,
        "params": {
            "uri": uri,
            "diagnostics": publish_diagnostics_for_source(uri, 源码, 文件名),
        },
    }


class DiagnosticExtension:
    """语义诊断扩展：可复用于既有 LSP 服务器的独立对象。

    用法::

        ext = DiagnosticExtension()                 # 默认关闭
        ext = DiagnosticExtension(enabled=True)     # 显式打开
        note = ext.on_did_open(params)              # -> dict | None

    关闭时所有回调返回 `None`，调用方应以「不发通知」处理——**注意**：这意味
    着不会向客户端推送空 diagnostics 去清掉旧波浪线。上层若要清除旧诊断，
    需自行发一条 `diagnostics: []` 的通知（见 `handle_notification` 的注释）。
    """

    def __init__(self, enabled: bool = DEFAULT_ENABLED, 源标识: str = DIAGNOSTIC_SOURCE_NAME):
        self.enabled = bool(enabled)
        self.源标识 = 源标识

    # ---- 生命周期 -----------------------------------------------------
    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    # ---- 事件处理 -----------------------------------------------------
    def on_did_open(self, params: Any) -> Optional[Dict[str, Any]]:
        """处理 `textDocument/didOpen`。"""
        if not self.enabled:
            return None
        return build_publish_diagnostics(_抽取uri(params), _抽取didOpen文本(params))

    def on_did_change(self, params: Any) -> Optional[Dict[str, Any]]:
        """处理 `textDocument/didChange`。

        增量同步（contentChanges 无 `text`）时返回 None，宁可不更新也不推脏数据。
        """
        if not self.enabled:
            return None
        源码 = _抽取didChange文本(params)
        if not 源码:
            return None
        return build_publish_diagnostics(_抽取uri(params), 源码)

    def handle(self, 方法: str, params: Any) -> Optional[Dict[str, Any]]:
        """按方法名分派；不支持的方法返回 None。"""
        if not self.enabled:
            return None
        if 方法 == "textDocument/didOpen":
            return self.on_did_open(params)
        if 方法 == "textDocument/didChange":
            return self.on_did_change(params)
        return None


def handle_notification(方法: str, params: Any,
                        enabled: bool = DEFAULT_ENABLED) -> Optional[Dict[str, Any]]:
    """无状态便捷入口：等价于 `DiagnosticExtension(enabled).handle(...)`。

    返回可直接 JSON 序列化的通知字典；关闭/不支持时返回 `None`。

    ⚠️ 关闭时不发通知意味着客户端不会自动清掉上一次的波浪线。上层若需要「开关
    切换后立刻清空」，应在关闭时自行补发
    `{"method": "textDocument/publishDiagnostics", "params": {"uri": ..., "diagnostics": []}}`。
    """
    return DiagnosticExtension(enabled=enabled).handle(方法, params)


def 清空诊断(uri: str) -> Dict[str, Any]:
    """构造一条清空该 uri 诊断的通知（供上层在开关关闭时使用）。"""
    return {
        "jsonrpc": "2.0",
        "method": _PUBLISH_METHOD,
        "params": {"uri": uri, "diagnostics": []},
    }
