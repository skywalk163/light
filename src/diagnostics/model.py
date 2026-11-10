# -*- coding: utf-8 -*-
"""光明编译器结构化诊断的数据模型（纯标准库，无第三方依赖）。

设计要点
--------
* 字段集合与任务卡 T-0316 固定契约一致，顺序即 ``to_dict()`` 的输出顺序，
  因此 ``json.dumps(..., ensure_ascii=False)`` 的结果可以直接 diff。
* ``line == 0`` 表示「位置未知」。序列化时**原样保留 0**，绝不换算成 1、
  绝不猜测行号（见 ``src/llvm/codegen_typed.py::_stmt_source_line`` 的
  「不许伪造一个 0 出来」同类纪律）。``ErrorEntry.format()`` 在 line 为 0
  时本来就不打印位置行，所以兼容层无需特殊处理。
* ``fixes`` 是人类可读的修复建议，最多 3 条；``candidates`` 是机器可读的
  候选写法（可直接贴进源码或喂给 AI），条数不限。
* ``provisional=True`` 表示该诊断由自由文本正则推断而来，**尚未**与编译器
  内部的异常对象绑定。见 ``docs/错误码规范.md`` 的「推断态」一节。

本模块只定义数据，不负责匹配规则（见 ``registry.py``），也不改动
``src/errors.py`` 的任何文本输出。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

__all__ = ["Diagnostic", "SEVERITIES", "MAX_FIXES", "DIAGNOSTIC_FIELDS"]

#: 允许的三个严重度。warning/info 不会被本框架升级成 error。
SEVERITIES: Tuple[str, ...] = ("error", "warning", "info")

#: 修复建议上限（任务卡：fixes ≤ 3）。
MAX_FIXES = 3

#: ``to_dict()`` 的稳定字段顺序，也是 ``from_dict()`` 识别的全部字段。
DIAGNOSTIC_FIELDS: Tuple[str, ...] = (
    "code",
    "severity",
    "stage",
    "line",
    "column",
    "message",
    "hint",
    "fixes",
    "candidates",
    "provisional",
    "docs",
)


@dataclass
class Diagnostic:
    """一条结构化诊断。

    ``message`` 保留编译器/解释器给出的**原始报错文本**；``hint`` 是该错误码
    对应的通用原因说明。二者分开，才能让 ``to_legacy_entry()`` 还原出与直接
    构造 ``ErrorEntry`` 逐字一致的输出。
    """

    code: str
    severity: str = "error"
    stage: str = ""
    line: int = 0
    column: int = 0
    message: str = ""
    hint: str = ""
    fixes: List[str] = field(default_factory=list)
    candidates: List[str] = field(default_factory=list)
    provisional: bool = False
    docs: str = ""

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(
                f"severity 必须是 {SEVERITIES} 之一，收到 {self.severity!r}"
            )
        for name in ("line", "column"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(
                    f"{name} 必须是非负整数；0 表示位置未知，不许编造行号"
                )
        # 拷一份，避免外部 list 与诊断对象互相串改。
        self.fixes = list(self.fixes)
        self.candidates = list(self.candidates)
        if len(self.fixes) > MAX_FIXES:
            raise ValueError(
                f"fixes 最多 {MAX_FIXES} 条，收到 {len(self.fixes)} 条"
            )
        for name in ("fixes", "candidates"):
            for item in getattr(self, name):
                if not isinstance(item, str):
                    raise TypeError(f"{name} 的元素必须是 str，收到 {item!r}")

    def to_dict(self) -> Dict[str, Any]:
        """按 :data:`DIAGNOSTIC_FIELDS` 的顺序导出，可直接 JSON 序列化。

        列表字段返回副本，调用方修改返回值不会污染诊断对象。
        """
        out: Dict[str, Any] = {}
        for name in DIAGNOSTIC_FIELDS:
            value = getattr(self, name)
            out[name] = list(value) if isinstance(value, list) else value
        return out

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Diagnostic":
        """从 ``to_dict()`` 的结果还原；未知字段忽略（前向兼容）。

        忽略未知字段而不是报错，是为了让旧版消费者读到新版诊断时不至于崩；
        缺失字段走 dataclass 默认值。``line`` 缺失即 0 = 位置未知。
        """
        if not isinstance(data, dict):
            raise TypeError(f"from_dict 需要 dict，收到 {type(data).__name__}")
        kwargs = {name: data[name] for name in DIAGNOSTIC_FIELDS if name in data}
        return cls(**kwargs)

    def to_json(self, *, ensure_ascii: bool = False) -> str:
        """便捷方法：稳定顺序的 JSON 文本（仅用标准库 json）。"""
        import json

        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii)
