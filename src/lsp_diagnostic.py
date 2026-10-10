#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R137：LSP 语义诊断适配层。

把 `src/semantic_analyzer.py` 的 `SemanticError` 转成可被 LSP
`textDocument/publishDiagnostics` 消费的结构化诊断。

设计边界（红线）
----------------
* **不重写**语义分析器：只做「调用 + 过滤 + 结构化」。
* 任何解析/词法/分析异常都被吞掉，转换成一条 `信息` 级诊断，绝不抛穿到 LSP
  主线程（否则一次解析失败会拖垮整个编辑器会话）。

行号换算（重要）
----------------
LSP 的 `range.start.line` 是 **0-based**，而对外报告的坐标需要是人习惯的
**1-based**。因此本模块对外同时保留两套坐标：

* `run_semantic_diagnostic()` 返回的 `行` / `列` 一律 **1-based**（给人看、给
  命令行报告用，与 `cli/lightc.py` 的 `[语义警告] 文件:行` 保持一致）；
* `to_lsp_diagnostics()` 里写入 `range.start.line` / `range.start.character`
  时统一 `-1` 转成 **0-based**（给 LSP 客户端用），并 clamp 到 ≥ 0。

换算只在 `to_lsp_diagnostics()` 一处发生，避免双重转换。

⚠️ **v3 AST 节点普遍没有 `line` 属性**，`SemanticError.line` 恒为 0（见
`semantic_analyzer.py:204` 的 `add_error`）。因此本模块在 `line <= 0` 时退化为
「按标识符在源码中的出现次序匹配」还原坐标：同名第 n 条诊断对应源码里第 n 次
出现。这是启发式，重名密集的文件里可能偏移 1~2 行。
"""

import re
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "严重度错误", "严重度警告", "严重度信息",
    "LSP_SEVERITY", "未定义符号前缀",
    "PYTHON_INTEROP_NAMES", "GENERIC_PARAM_PATTERN",
    "RUNTIME_INJECTED_PREFIXES",
    "是己属性", "是泛型类型参数", "是Python互操作名", "是本文件已赋值的名字",
    "是运行时注入名", "是字符串字面量误报", "去掉注释", "提取裸代码",
    "误报名", "收集python内嵌块名字", "收集赋值目标名", "去掉字符串字面量",
    "构建诊断上下文",
    "run_semantic_diagnostic", "to_lsp_diagnostics", "diagnostic_from_source",
]

# --------------------------------------------------------------------------
# 常量：严重度
# --------------------------------------------------------------------------
严重度错误 = "错误"
严重度警告 = "警告"
严重度信息 = "信息"

# 人类可读严重度 → LSP Diagnostic.severity（1 错误 / 2 警告 / 3 信息 / 4 提示）
LSP_SEVERITY = {
    严重度错误: 1,
    严重度警告: 2,
    严重度信息: 3,
}

未定义符号前缀 = "未定义的符号 "

_DIAGNOSTIC_SOURCE = "语义分析"

# 诊断键名（光明侧对外统一用中文键）
键行 = "行"
键列 = "列"
键消息 = "消息"
键严重度 = "严重度"
键来源 = "来源"

# --------------------------------------------------------------------------
# 白名单：假阳性过滤规则
# --------------------------------------------------------------------------
# 每个规则都是独立可测函数，禁止在别处散落魔法值。

# 光明标识符：`己X` 前缀表示实例属性/自身引用，语义分析器在类外见到会误报。
_己属性前缀 = "己"
_己访问模式 = re.compile(r"己(?=[一-鿿A-Za-z0-9_])")

# 泛型类型参数：单个大写字母（T/U/K/V…）占位名。
GENERIC_PARAM_PATTERN = re.compile(r"^[A-Z]$")

# Python 互操作名：`引 Python` 内嵌块把 Python 名字泄漏进光明作用域。
# 这里覆盖 CPython builtins + 语料里实际出现最多的 stdlib 模块/函数。
PYTHON_INTEROP_NAMES = frozenset({
    # builtins 函数/类型
    "type", "dict", "str", "int", "list", "bool", "float", "set", "tuple",
    "bytes", "bytearray", "complex", "frozenset", "object", "super",
    "isinstance", "issubclass", "hasattr", "getattr", "setattr", "delattr",
    "len", "id", "chr", "ord", "abs", "min", "max", "sum", "round", "sorted",
    "reversed", "enumerate", "zip", "map", "filter", "range", "print", "repr",
    "hash", "iter", "next", "callable", "any", "all", "dir", "vars", "open",
    "format", "input", "hex", "oct", "bin", "pow", "divmod", "staticmethod",
    "classmethod", "property", "Exception", "BaseException", "ValueError",
    "TypeError", "KeyError", "IndexError", "AttributeError", "RuntimeError",
    "StopIteration", "ImportError", "IOError", "OSError", "NameError",
    # stdlib 模块名
    "math", "os", "sys", "re", "json", "time", "datetime", "random", "copy",
    "collections", "itertools", "functools", "pathlib", "typing", "subprocess",
    "shutil", "socket", "threading", "asyncio", "traceback", "logging", "uuid",
    # 类型注解常量
    "None", "True", "False", "Any", "Optional", "List", "Dict", "Tuple",
})

# `引 Python` / `引入 Python` 等嵌入块起止标记
_PYTHON_BLOCK_START = re.compile(r"^\s*引\s*(入)?\s*Python\b", re.MULTILINE)
_PYTHON_BLOCK_END = re.compile(r"^\s*结束(嵌入|引)\b", re.MULTILINE)
# Python 内嵌块里的 import 目标名
_PY_IMPORT_PATTERN = re.compile(
    r"^\s*(?:from\s+[A-Za-z_][\w.]*\s+import\s+|import\s+)([A-Za-z_][\w.]*)",
    re.MULTILINE,
)

# 光明标识符正则（含中文）
_标识符模式 = re.compile(r"[一-鿿A-Za-z_][一-鿿A-Za-z0-9_]*")

# 赋值目标：`设 X 为 ...` / 行首 `X 为 ...` / `X = ...`
_设赋值模式 = re.compile(r"设\s+([一-鿿A-Za-z_][一-鿿A-Za-z0-9_]*)\s+为")
_行首赋值模式 = re.compile(
    r"^[ \t]*([一-鿿A-Za-z_][一-鿿A-Za-z0-9_]*)[ \t]*(?:为\s*[^=]|=(?!=))",
    re.MULTILINE,
)

# 运行时注入的命名空间：编译器/标准库 delegate 到宿主里的内建表的写法
# （如 `_light_builtin.字典获取(...)`），光明符号表里自然查不到。
RUNTIME_INJECTED_PREFIXES = ("_light_", "__light_", "_内置")

# 字符串字面量（双引号 / 单引号），用于剔除「只出现在字符串里」的名字
_字符串字面量模式 = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'')


def 是己属性(名字: str) -> bool:
    """`己X` 前缀（实例属性 / 自身引用）误报。"""
    return bool(名字) and (名字.startswith(_己属性前缀) or bool(_己访问模式.match(名字)))


def 是泛型类型参数(名字: str) -> bool:
    """泛型类型参数误报：单大写字母（T/U/K/V…）占位名。"""
    return bool(名字) and bool(GENERIC_PARAM_PATTERN.match(名字)) and len(名字) == 1


def 收集python内嵌块名字(源码: str) -> frozenset:
    """从 `引 Python:` … `结束嵌入/结束引` 块里抽取 Python 侧名字。

    这些名字由 Python 块引入，光明符号表不可见，一律视为已知。
    """
    if not 源码:
        return frozenset()
    名字 = set()
    for m in _PYTHON_BLOCK_START.finditer(源码):
        rest = 源码[m.end():]
        end = _PYTHON_BLOCK_END.search(rest)
        块体 = rest[:end.start()] if end else rest
        for im in _PY_IMPORT_PATTERN.finditer(块体):
            首段 = im.group(1).split(".")[0]
            if 首段:
                名字.add(首段)
        for ident in _标识符模式.findall(块体):
            名字.add(ident)
    return frozenset(名字)


def 是Python互操作名(名字: str, python名字: Optional[frozenset] = None) -> bool:
    """`引 Python` 内嵌块 / Python 互操作引入的名字误报。"""
    if not 名字:
        return False
    if 名字 in PYTHON_INTEROP_NAMES:
        return True
    return bool(python名字) and 名字 in python名字


def 是本文件已赋值的名字(名字: str, 赋值名集合: Optional[frozenset] = None) -> bool:
    """分支合并（flow-join）误报：名字在本文件的某条分支里被赋过值。

    语义分析器不做流敏感分析，「在 `如果/否则` 两分支内各自赋值、分支结束后
    使用」会被判为未定义。实测这是 `lightharness/src` 语料里除 Python 互操作
    外唯一剩余的假阳性类别（详见 docs/AI编程指南.md LSP 章节）。
    """
    if not 名字:
        return False
    return bool(赋值名集合) and 名字 in 赋值名集合


def 收集赋值目标名(源码: str) -> frozenset:
    """抽取源码里所有被赋值过的名字（`设 X 为` / 行首 `X 为` / `X =`）。"""
    if not 源码:
        return frozenset()
    名字 = set()
    名字.update(_设赋值模式.findall(源码))
    名字.update(_行首赋值模式.findall(源码))
    return frozenset(名字)


# 行注释（需在去掉字面量之后再跑，否则会把字面量里的 '#' 当注释起点）
_行注释模式 = re.compile(r"#[^\n]*")


def 去掉字符串字面量(源码: str) -> str:
    """把源码里的字符串字面量替换成等长空格（保留行号列号对齐）。

    用于判定一个名字是否「只出现在字符串里」——这类名字被语义分析器当成
    标识符引用是误报（如 `载荷["args"]`、`返回 {"candidates": 观察}`）。
    """
    if not 源码:
        return ""

    def _blank(m):
        return " " * (m.end() - m.start())

    return _字符串字面量模式.sub(_blank, 源码)


def 去掉注释(源码: str) -> str:
    """把 `#` 行注释替换成空串（保留换行数以维持行号）。"""
    if not 源码:
        return ""
    return _行注释模式.sub("", 源码)


def 提取裸代码(源码: str) -> str:
    """去掉字符串字面量与注释后剩下的「真代码」。

    一个名字若只出现在字符串/注释中、在裸代码里查不到，则它被报「未定义符号」
    必然是误报。
    """
    return 去掉注释(去掉字符串字面量(源码))


def 是运行时注入名(名字: str) -> bool:
    """运行时注入的命名空间误报（`_light_builtin.字典获取(...)` 一类）。"""
    return bool(名字) and 名字.startswith(RUNTIME_INJECTED_PREFIXES)


def 是字符串字面量误报(名字: str, 裸代码: Optional[str] = None) -> bool:
    """名字只出现在字符串字面量/注释里、不是真正的标识符引用。

    `裸代码` 由 `提取裸代码()` 生成；为 None 时不做此判定（返回 False，即不误杀）。
    """
    if not 名字 or 裸代码 is None:
        return False
    return not re.search(
        r"(?<![一-鿿A-Za-z0-9_])" + re.escape(名字) + r"(?![一-鿿A-Za-z0-9_])", 裸代码
    )


class 诊断上下文:
    """一次诊断所需的源码级上下文（白名单判据的预计算结果）。

    独立成类是为了让每条规则函数都能被单测直接喂参，而不是在函数内部偷偷
    对源码做一次计算。
    """

    __slots__ = ("源码", "python名字", "赋值名集合", "裸代码")

    def __init__(self, 源码: str):
        self.源码 = 源码 or ""
        self.python名字 = 收集python内嵌块名字(self.源码)
        self.赋值名集合 = 收集赋值目标名(self.源码)
        self.裸代码 = 提取裸代码(self.源码)


def 构建诊断上下文(源码: str) -> 诊断上下文:
    """供调用方复用的上下文构造入口。"""
    return 诊断上下文(源码)


def 误报名(名字: str, 上下文: Optional[诊断上下文] = None) -> Tuple[bool, str]:
    """综合判定一个「未定义符号」是否属于已知误报。

    返回 `(是否误报, 命中的规则名)`；规则名用于调试与度量统计。

    规则顺序按**实测命中频次**从高到低（`lightharness/src` 全 240 文件语料）：
    Python互操作 > 分支合并赋值 > 运行时注入 > 字符串字面量 > 己属性 > 泛型。
    """
    if not 名字:
        return False, ""
    if 是Python互操作名(名字, 上下文.python名字 if 上下文 else None):
        return True, "Python互操作"
    if 是本文件已赋值的名字(名字, 上下文.赋值名集合 if 上下文 else None):
        return True, "分支合并赋值"
    if 是运行时注入名(名字):
        return True, "运行时注入"
    if 上下文 is not None and 是字符串字面量误报(名字, 上下文.裸代码):
        return True, "字符串字面量/注释"
    if 是己属性(名字):
        return True, "己属性"
    if 是泛型类型参数(名字):
        return True, "泛型类型参数"
    return False, ""


# 旧名字兼容（内部脚本/度量脚本可能引用）
是误报名 = 误报名


# --------------------------------------------------------------------------
# 行号定位兜底
# --------------------------------------------------------------------------
def _构建行定位器(源码: str):
    """v3 AST 节点普遍没有 `line` 属性，`SemanticError.line` 恒为 0。

    这里用「在源码里顺序匹配标识符」的方式还原 1-based 行号：同一名字第 n 次
    出现在输出里就对应源码里第 n 次出现。
    """
    行列表 = (源码 or "").split("\n")
    出现位置: Dict[str, List[int]] = {}
    for i, line in enumerate(行列表):
        for tok in _标识符模式.finditer(line):
            出现位置.setdefault(tok.group(0), []).append(i)
    return 行列表, 出现位置


def _取行列(名字: str,
            行列表: List[str],
            出现位置: Dict[str, List[int]],
            计数: Dict[str, int]) -> Tuple[int, int]:
    """取名字第 n 次出现的 (1-based 行, 1-based 列)。找不到返回 (0, 0)。"""
    if not 名字:
        return 0, 0
    n = 计数.get(名字, 0)
    计数[名字] = n + 1
    idxs = 出现位置.get(名字)
    if not idxs:
        return 0, 0
    li = idxs[min(n, len(idxs) - 1)]
    line = 行列表[li]
    pos = line.find(名字)
    return li + 1, (pos + 1) if pos >= 0 else 1


# --------------------------------------------------------------------------
# 主入口
# --------------------------------------------------------------------------
def _取未定义符号名(消息: str) -> Optional[str]:
    """从 `未定义的符号 'X'` 里抽出 X。"""
    if not 消息.startswith(未定义符号前缀):
        return None
    尾 = 消息[len(未定义符号前缀):]
    if len(尾) >= 2 and 尾[0] == "'" and 尾[-1] == "'":
        return 尾[1:-1]
    return None


def _跑分析器(源码: str):
    """按 `cli/lightc.py:59-100` 的标准姿势跑一遍语义分析。

    返回 `(errors, fatal_message)`；任一步异常都被收敛成 `fatal_message`。
    """
    try:
        from lexer import Lexer  # noqa: F401  # 确保 src 在 path 上时词法器可用
        from light_parser_v3 import LightParser
        from semantic_analyzer import SemanticAnalyzer
    except Exception as ex:  # pragma: no cover - 依赖缺失
        return None, f"语义分析依赖不可用：{type(ex).__name__}: {ex}"

    try:
        module = LightParser().parse(源码)
    except Exception as ex:
        return None, f"语法/词法解析失败：{type(ex).__name__}: {ex}"
    if module is None:
        return None, "语法解析返回空 Module"

    try:
        analyzer = SemanticAnalyzer(module)
        if not getattr(analyzer, "v3_mode", False):
            analyzer.visit_Module(module)
        else:
            analyzer.analyze_v3(module)
    except Exception as ex:
        return None, f"语义分析异常：{type(ex).__name__}: {ex}"

    return list(getattr(analyzer, "errors", []) or []), None


def run_semantic_diagnostic(源码: str, 文件名: Optional[str] = None) -> List[Dict[str, Any]]:
    """对一段光明源码跑语义诊断，返回结构化诊断列表。

    每条诊断形如::

        {"行": 3, "列": 5, "消息": "未定义的符号 '乙'",
         "严重度": "错误", "来源": "语义分析"}

    `行` / `列` **均为 1-based**。解析失败或不支持的节点类型不会产生异常，
    而是降级成一条 `信息` 级诊断。白名单命中的误报已被剔除。
    """
    if 源码 is None:
        源码 = ""
    if not isinstance(源码, str):
        # 非字符串入参（bytes/int/对象）不该让 LSP 会话炸掉，降级成一条信息诊断
        return [{
            键行: 0, 键列: 0,
            键消息: f"诊断入参不是字符串：{type(源码).__name__}",
            键严重度: 严重度信息, 键来源: _DIAGNOSTIC_SOURCE,
        }]

    errors, fatal = _跑分析器(源码)
    结果: List[Dict[str, Any]] = []
    if fatal is not None:
        return [{键行: 0, 键列: 0, 键消息: fatal,
                键严重度: 严重度信息, 键来源: _DIAGNOSTIC_SOURCE}]

    行列表, 出现位置 = _构建行定位器(源码)
    计数: Dict[str, int] = {}
    上下文 = 构建诊断上下文(源码)

    for err in errors or []:
        消息 = str(getattr(err, "message", err))
        名字 = _取未定义符号名(消息)
        line = int(getattr(err, "line", 0) or 0)
        col = int(getattr(err, "column", 0) or 0)

        if 名字 is not None:
            # 先按出现次序占位再判白名单：过滤掉的诊断也要消耗一次出现，
            # 否则残留诊断的 occurrence 序号会被“跳过的位置”带偏。
            if line <= 0:
                line, col = _取行列(名字, 行列表, 出现位置, 计数)
            命中, _规则 = 误报名(名字, 上下文)
            if 命中:
                continue
        else:
            if line <= 0:
                line, col = 0, max(col, 0)

        结果.append({
            键行: max(line, 0),
            键列: max(col, 0),
            键消息: 消息,
            键严重度: 严重度错误 if 名字 is not None else 严重度警告,
            键来源: _DIAGNOSTIC_SOURCE,
        })

    if 文件名:
        for d in 结果:
            d["文件"] = 文件名
    return 结果


def to_lsp_diagnostics(诊断列表: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把 `run_semantic_diagnostic()` 的结果转成 LSP `Diagnostic[]`。

    **这里是唯一的 1-based → 0-based 换算点**：
    `行的零基 = 行 - 1`、`列的零基 = 列 - 1`，并用 `max(..., 0)` clamp。
    """
    if not 诊断列表:
        return []
    lsp列表: List[Dict[str, Any]] = []
    for d in 诊断列表:
        line0 = max(int(d.get(键行, 0)) - 1, 0)
        ch0 = max(int(d.get(键列, 1)) - 1, 0)
        消息 = d.get(键消息, "")
        # 结束位置：至少占 1 个字符，避免零宽 range 被客户端忽略
        end_ch = ch0 + max(len(_取未定义符号名(消息) or 消息[:1]), 1)
        lsp列表.append({
            "range": {
                "start": {"line": line0, "character": ch0},
                "end": {"line": line0, "character": end_ch},
            },
            "severity": LSP_SEVERITY.get(d.get(键严重度), 2),
            "source": d.get(键来源, _DIAGNOSTIC_SOURCE),
            "message": 消息,
        })
    return lsp列表


# 兼容下划线别名（便于其它 Python 侧调用方 / 测试使用）
diagnostic_from_source = run_semantic_diagnostic


def __getattr__(name: str):
    """导出少量英文别名，方便跨模块调用。"""
    aliases = {
        "SEVERITY_ERROR": 严重度错误,
        "SEVERITY_WARNING": 严重度警告,
        "SEVERITY_INFO": 严重度信息,
        "SOURCE_NAME": _DIAGNOSTIC_SOURCE,
    }
    if name in aliases:
        return aliases[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
