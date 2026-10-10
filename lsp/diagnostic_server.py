# -*- coding: utf-8 -*-
"""
R137 C 线：语义诊断增强型 LSP 服务器入口（**新增文件，不修改 `lsp/` 任何既有文件**）。

作用
----
既有 `lsp/light_lsp.py` 的 `LightLanguageServer` 已经能发「语法/类型」诊断
（`_publish_diagnostics` → `get_diagnostics`）。本模块**不改动它**，而是：

1. 子类化 `LightLanguageServer`，在 `_publish_diagnostics` 里把
   `lsp.diagnostic_extension` 算出的**语义级诊断**（未定义符号等）合并进同一条
   `publishDiagnostics` 通知（按 LSP 语义，同名 uri 的 publishDiagnostics 会整体
   替换，所以必须合并到同一条通知里，否则会冲掉语法诊断）。
2. 提供与 `light_lsp_main.py` 同款的 stdio 主循环，但用子类实例。

开关策略（对齐 R135 / R137 红线）
--------------------------------
`--diagnostic` 默认 `off`。理由：`src/semantic_analyzer.py` 的未定义符号判定
仍有一定假阳性，默认开启会打扰用户。显式 `--diagnostic semantic` 才启用。

为什么是独立文件
----------------
任务书红线「不改 `lsp/` 既有文件逻辑」。`light_lsp.py` 是 145KB 巨物，
`light_lsp_main.py` 是既有入口。两者都不动，只新增本文件承接接线。
"""

import sys
import os
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _ROOT, _HERE):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from lsp.light_lsp import LightLanguageServer, lsp_notification  # 既有文件，只导入（按包路径）

try:
    from lsp.diagnostic_extension import publish_diagnostics_for_source
except ImportError:  # pragma: no cover - 依赖缺失时降级为「无语义诊断」
    publish_diagnostics_for_source = None  # type: ignore[assignment]


class DiagnosticLanguageServer(LightLanguageServer):
    """在语法/类型诊断之外叠加语义诊断的 LSP 服务器。

    仅重写 `_publish_diagnostics` 这一处钩子，其余行为完全继承既有服务器，
    因此不会有「自研一套 LSP 协议」的漂移风险。
    """

    def __init__(self, diag_enabled: bool = False):
        super().__init__()
        self.diag_enabled = bool(diag_enabled)

    def _publish_diagnostics(self, uri: str):
        # 先由基类产出「语法/类型」诊断，并落到 _pending_notifications 末尾
        super()._publish_diagnostics(uri)
        if not self.diag_enabled or publish_diagnostics_for_source is None:
            return

        doc = self.doc_manager.get_document(uri) if hasattr(self, "doc_manager") else None
        text = getattr(doc, "text", "") or ""
        if not text:
            return

        try:
            sem = publish_diagnostics_for_source(uri, text, None)
        except Exception:
            return
        if not sem:
            return

        # 合并进「刚刚由 super() 追加的那条」通知里，避免冲掉语法诊断
        pending = getattr(self, "_pending_notifications", None)
        if not pending:
            # 基类没产出任何诊断（理论上不会发生），自己补一条
            self._pending_notifications = [
                lsp_notification("textDocument/publishDiagnostics",
                                 {"uri": uri, "diagnostics": sem})
            ]
            return
        last = pending[-1]
        if isinstance(last, dict) and isinstance(last.get("params"), dict):
            existing = last["params"].setdefault("diagnostics", [])
            existing.extend(sem)


def _写出帧(out_bytes: bytes) -> None:
    """用二进制写出一帧 LSP 消息，避免 Windows 文本模式下 \\r\\n 被加倍成 \\r\\r\\n。"""
    header = ("Content-Length: %d\r\n\r\n" % len(out_bytes)).encode("ascii")
    sys.stdout.buffer.write(header)
    sys.stdout.buffer.write(out_bytes)
    sys.stdout.buffer.flush()


def run_diagnostic_stdio_server(diag_enabled: bool = False):
    """与 `light_lsp.main()` 等价的 stdio 主循环，但用诊断增强型服务器。

    直接复制既有主循环体（不 import 既有 main，以免牵动其硬编码的
    `LightLanguageServer()`），用 `DiagnosticLanguageServer` 替换实例即可。
    **改进**：头部与正文均走 `sys.stdout.buffer`（二进制），规避 Windows 下
    `sys.stdout.write` 把 `\\r\\n` 加倍成 `\\r\\r\\n` 导致编辑器解析失败的既有坑
    （该坑存在于 `light_lsp.main()`，本新增文件直接修掉，不改写基文件）。
    """
    server = DiagnosticLanguageServer(diag_enabled=diag_enabled)
    buffer = ""
    content_length = 0

    while True:
        while "\r\n\r\n" not in buffer:
            chunk = sys.stdin.buffer.read(4096)
            if not chunk:
                return
            buffer += chunk.decode("utf-8", errors="replace")

        header, _, buffer = buffer.partition("\r\n\r\n")
        for line in header.split("\r\n"):
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":")[1].strip())

        while len(buffer) < content_length:
            chunk = sys.stdin.buffer.read(4096)
            if not chunk:
                return
            buffer += chunk.decode("utf-8", errors="replace")

        content = buffer[:content_length]
        buffer = buffer[content_length:]

        try:
            message = json.loads(content)
            method = message.get("method")
            params = message.get("params")
            msg_id = message.get("id")

            if method == "exit":
                return

            if method == "shutdown":
                if msg_id is not None:
                    response = json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": None},
                                         ensure_ascii=False)
                    _写出帧(response.encode("utf-8"))
                continue

            if method:
                result = server.handle_request(method, params, msg_id)
                if result is not None:
                    response = json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result},
                                         ensure_ascii=False)
                    _写出帧(response.encode("utf-8"))

            # 发送待发通知（语法/类型 + 语义诊断合并后的结果）
            for notification in server.get_pending_notifications():
                notification_json = json.dumps(notification, ensure_ascii=False)
                _写出帧(notification_json.encode("utf-8"))
        except Exception as e:  # pragma: no cover - 主循环兜底
            error_response = json.dumps({
                "jsonrpc": "2.0",
                "id": msg_id if "msg_id" in locals() else None,
                "error": {"code": -32603, "message": str(e)},
            }, ensure_ascii=False)
            _写出帧(error_response.encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="光明 语义诊断增强型 LSP 服务器")
    parser.add_argument("--stdio", action="store_true", help="通过 stdio 通信（默认即此模式）")
    parser.add_argument("--diagnostic", choices=["off", "semantic"], default="off",
                        help="语义诊断开关：off（默认，关闭）/ semantic（开启）。"
                             "开启后 didOpen/didChange 会叠加「未定义符号」等语义诊断。")
    parser.add_argument("--version", action="store_true", help="显示版本信息")
    args = parser.parse_args()

    if args.version:
        print("光明 语义诊断增强型 LSP 服务器 v5.1.0 (R137)")
        return

    run_diagnostic_stdio_server(diag_enabled=(args.diagnostic == "semantic"))


if __name__ == "__main__":
    main()
