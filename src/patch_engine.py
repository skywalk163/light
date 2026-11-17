# -*- coding: utf-8 -*-
"""光明（Light）局部补丁引擎 —— AST 序列化 / 符号表 / span 级补丁。

这是 **纯模块**：只依赖标准库与仓内 ``light_parser_v3``（与 ``cli/light.py`` 的
``_ast_src`` 同一后端），不 import ``cli``，也不自己写解析器。CLI 接线由 T-0382
统一负责。

坐标口径（与解析器 Token 坐标一致）
------------------------------------
- ``line`` 从 **1** 开始，``col`` 从 **1** 开始；
- ``span`` 是 **半开区间** ``[start, end)``：``end`` 指向最后一个字符的**下一个**
  位置，因此「把第 1 行第 7 列的 ``3`` 换成 ``42``」写作
  ``start=(1,7)``、``end=(1,8)``；
- ``line == 0`` / ``col == 0`` 表示 **AST 没有给出该节点的位置**（未知），
  不是「第 0 行」。语句/定义节点有行号；表达式叶子节点多数没有，见
  ``ast_to_json`` 的 ``span`` 说明。

canonical 口径（与 D 线 ``--canonical`` 的「同语义一个名字」对齐）
------------------------------------------------------------------
符号名统一做 ``unicodedata.normalize('NFKC', name).strip()``。NFKC 会把全角
ASCII 折成半角、把兼容字符折成标准字符——这与 Python 转译腿对标识符的归一
行为一致，所以 ``ａ`` 与 ``a`` 在符号表里是同一个 canonical 名。D 线
（T-0380）以后若扩展别名表，只需要改本模块的 :func:`_canonical_name` 一处。

对外 API
--------
- :func:`ast_to_json`   —— AST 转 JSON（``kind`` / ``span`` / ``children`` / ``value`` / ``fields``）
- :func:`symbols_json`  —— 导出面与符号表（定义、导入、作用域、被引用次数）
- :func:`patch`         —— 按 span 做确定性局部替换（拒绝交叠/越界/不闭合）
- :func:`diff_summary`  —— 改了哪些行、涉及哪些符号（给 Agent 自检）
- :class:`PatchError`   —— ``patch`` 的校验失败异常（中文原因）
"""

from __future__ import annotations

import difflib
import math
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ast_nodes_v3 import ASTNode
from light_parser_v3 import LightParser

__all__ = [
    "PatchError",
    "ast_to_json",
    "symbols_json",
    "patch",
    "diff_summary",
]

SCHEMA_VERSION = 1

#: 解析器 Token 之外、序列化时丢弃的位置/内部字段。
_SKIP_SLOTS = frozenset({"line", "col", "_ast_type_id"})

#: ``_jsonable`` 里表示「容器里没有 AST 子节点」的哨兵。
_MISSING = object()

#: 接收者关键字（`己.宽` / `self.宽` / `自.宽` 里的接收者本身不是符号引用）。
_RECEIVER_NAMES = frozenset({"self", "己", "自"})

#: diff_summary 单个变更块最多保留的字符数（防止超大文件把 JSON 撑爆）。
_MAX_BLOCK_CHARS = 4000


# =============================================================================
# 异常
# =============================================================================

class PatchError(ValueError):
    """局部补丁校验失败。

    所有消息都是中文，并带「第几个编辑 / 具体坐标」，便于 Agent 直接修正。
    ``patch()`` 只在 **参数校验失败** 时抛它；正常替换不会抛异常。
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.reason = message


# =============================================================================
# 通用小工具
# =============================================================================

def _canonical_name(name: str) -> str:
    """符号名的 canonical 形态（NFKC + 去首尾空白）。

    契约见模块头：与 Python 转译腿的标识符归一一致，同一语义一个名字。
    """
    return unicodedata.normalize("NFKC", name).strip()


def _source_lines(source: str) -> List[str]:
    """按 ``\\n`` 切行，并去掉行尾 ``\\r``（兼容 CRLF），供列号计算使用。"""
    return [line[:-1] if line.endswith("\r") else line for line in source.split("\n")]


def _line_starts(source: str) -> List[int]:
    """每行行首在原始字符串中的偏移；长度恒等于 ``len(_source_lines(source))``。"""
    starts = [0]
    for match in re.finditer("\n", source):
        starts.append(match.end())
    return starts


def _span_dict(span: Tuple[int, int, int, int]) -> Dict[str, int]:
    start_line, start_col, end_line, end_col = span
    return {
        "start_line": start_line,
        "start_col": start_col,
        "end_line": end_line,
        "end_col": end_col,
    }


def _jsonable(value: Any) -> Any:
    """把任意 AST 字段值转成 ``json.dumps`` 可序列化的形态。"""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else repr(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, ASTNode):
        # 正常不会走到这里；保留类型名，避免序列化直接失败。
        return {"__ast__": type(value).__name__}
    return repr(value)


def _slots_of(cls: type) -> List[str]:
    """按 MRO 收集 ``__slots__``（子类在前、去重）。"""
    result: List[str] = []
    seen = set()
    for base in reversed(cls.__mro__):
        for name in getattr(base, "__slots__", ()) or ():
            if name not in seen:
                seen.add(name)
                result.append(name)
    return result


def _pos(node: ASTNode, attr: str) -> int:
    value = getattr(node, attr, 0)
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _extract(value: Any) -> Tuple[List[ASTNode], Any]:
    """从 AST 字段值里拆出子节点与剩余标量。

    返回 ``(子节点列表, 剩余标量)``。容器里同时有 AST 节点和标量时（例如
    ``StringInterpolation.parts`` / ``WithStmt.items``），节点进 ``children``，
    标量单独返回并放进 ``fields``——两边的相对位置信息会丢失，这是有意的
    取舍：AST JSON 只承诺「结构 + 标量值」，不承诺重建源码。
    """
    if isinstance(value, ASTNode):
        return [value], _MISSING
    if isinstance(value, (list, tuple)):
        nodes: List[ASTNode] = []
        rest: List[Any] = []
        for item in value:
            child_nodes, child_rest = _extract(item)
            nodes.extend(child_nodes)
            if child_rest is not _MISSING:
                rest.append(child_rest)
        if nodes:
            return nodes, rest if rest else _MISSING
        return [], value
    if isinstance(value, dict):
        nodes = []
        rest_dict: Dict[Any, Any] = {}
        for key, item in value.items():
            child_nodes, child_rest = _extract(item)
            nodes.extend(child_nodes)
            if child_rest is not _MISSING:
                rest_dict[key] = child_rest
        if nodes:
            return nodes, rest_dict if rest_dict else _MISSING
        return [], value
    return [], value


# =============================================================================
# AST 视图：一次性算好 span，ast_to_json / symbols_json 共用
# =============================================================================

class _NodeView:
    """AST 节点 + 已算好的 span + 子节点列表 + 标量字段。"""

    __slots__ = ("kind", "node", "children", "fields", "span")

    def __init__(
        self,
        kind: str,
        node: ASTNode,
        children: List["_NodeView"],
        fields: Dict[str, Any],
        span: Tuple[int, int, int, int],
    ):
        self.kind = kind
        self.node = node
        self.children = children
        self.fields = fields
        self.span = span


def _build_view(node: ASTNode) -> _NodeView:
    """递归构建 ``_NodeView``；span 由「自身位置 + 后代位置」聚合。"""
    kind = type(node).__name__
    own_line = _pos(node, "line")
    own_col = _pos(node, "col")

    raw_children: List[ASTNode] = []
    fields: Dict[str, Any] = {}
    for slot in _slots_of(type(node)):
        if slot in _SKIP_SLOTS or slot.startswith("_"):
            continue
        try:
            value = getattr(node, slot)
        except AttributeError:
            # __slots__ 声明了但该分支没赋值 —— 视为无此字段。
            continue
        child_nodes, rest = _extract(value)
        raw_children.extend(child_nodes)
        if rest is not _MISSING:
            json_value = _jsonable(rest)
            if json_value is None or json_value == [] or json_value == {}:
                continue
            fields[slot] = json_value

    children = [_build_view(child) for child in raw_children]

    # start：自身有行号就用自己的；否则取后代里最小的已知位置。
    if own_line > 0:
        start = (own_line, own_col if own_col > 0 else 1)
    else:
        known_starts = [child.span[:2] for child in children if child.span[0] > 0]
        start = min(known_starts) if known_starts else (0, 0)

    # end：取自身起点与所有已知后代终点的最大值（保证 start <= end）。
    end = start
    for child in children:
        if child.span[0] <= 0:
            continue
        child_end = (child.span[2], child.span[3])
        if child_end > end:
            end = child_end

    return _NodeView(kind, node, children, fields, (start[0], start[1], end[0], end[1]))


def _node_to_json(view: _NodeView) -> Dict[str, Any]:
    """``_NodeView`` → JSON 节点（固定含 kind / span / value / fields / children）。"""
    literal = _literal_value(view)
    fields = dict(view.fields)
    if literal is not _MISSING:
        fields.pop("value", None)

    return {
        "kind": view.kind,
        "span": _span_dict(view.span),
        "value": None if literal is _MISSING else _jsonable(literal),
        "fields": fields,
        "children": [_node_to_json(child) for child in view.children],
    }


def _literal_value(view: _NodeView) -> Any:
    """字面量节点的载荷；其余节点返回哨兵。"""
    try:
        value = getattr(view.node, "value")
    except AttributeError:
        return _MISSING
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return _MISSING


def _tree_stats(view: _NodeView, depth: int = 1) -> Tuple[int, int, int]:
    """返回 ``(节点数, 叶子数, 最大深度)``。"""
    nodes = 1
    leaves = 1 if not view.children else 0
    max_depth = depth
    for child in view.children:
        child_nodes, child_leaves, child_depth = _tree_stats(child, depth + 1)
        nodes += child_nodes
        leaves += child_leaves
        max_depth = max(max_depth, child_depth)
    return nodes, leaves, max_depth


def _walk_json(node: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """深度优先遍历 JSON 树里的所有节点（供测试/消费者使用）。"""
    yield node
    for child in node.get("children", ()):
        yield from _walk_json(child)


def _parse(source: str, file_label: Optional[str] = None):
    """走与 ``cli/light.py::_ast_src`` 相同的后端解析源码。"""
    if not isinstance(source, str):
        raise TypeError("source 必须是 str")
    parser = LightParser()
    return parser.parse(source, filename=file_label)


# =============================================================================
# 1) AST 序列化
# =============================================================================

def ast_to_json(source: str, file_label: Optional[str] = None) -> Dict[str, Any]:
    """把光明源码解析成 JSON 友好的 AST。

    参数
    ----
    source : str
        光明源码。
    file_label : str | None
        只用于元信息与解析错误里的文件名，不读磁盘。

    返回
    ----
    dict
        ``{"file", "language", "schema_version", "source", "root"}``。

        ``root`` 是根节点（``Module``），每个节点固定含：

        - ``kind``：节点类型名（如 ``Paragraph`` / ``VarDecl`` / ``Identifier``）；
        - ``span``：``{start_line, start_col, end_line, end_col}``，1 起、半开区间；
          语句/定义节点有真实行号；表达式叶子节点解析器未记录位置，此时
          ``start_line == 0`` 表示未知（不会伪造成别的行）；
        - ``value``：字面量节点的载荷（数字/字符串/布尔/None），非字面量为 ``null``；
        - ``fields``：节点上的标量字段（``name`` / ``operator`` / ``params`` 等）；
        - ``children``：AST 子节点，顺序为字段声明顺序（**不保证等于源码顺序**，
          跨节点源码顺序请按 ``span`` 排序）。

        ``source`` 段给出行数、节点数、叶子数、最大深度，便于 Agent 判断规模。
    """
    module = _parse(source, file_label)
    root_view = _build_view(module)

    if source:
        # 根节点用整份源码的边界，避免只有注释/空行的文件没有根 span。
        line_count = source.count("\n") + 1
        end_line = max(line_count, root_view.span[2])
        root_view.span = (1, 1, end_line, 1)
    else:
        root_view.span = (0, 0, 0, 0)

    node_count, leaf_count, max_depth = _tree_stats(root_view)

    return {
        "file": file_label,
        "language": "light",
        "schema_version": SCHEMA_VERSION,
        "source": {
            "line_count": source.count("\n") + 1,
            "node_count": node_count,
            "leaf_count": leaf_count,
            "max_depth": max_depth,
        },
        "root": _node_to_json(root_view),
    }


# =============================================================================
# 2) 符号表
# =============================================================================

class _Scope:
    __slots__ = ("id", "name", "kind", "parent", "path", "span")

    def __init__(self, scope_id, name, kind, parent, path, span):
        self.id = scope_id
        self.name = name
        self.kind = kind
        self.parent = parent
        self.path = path
        self.span = span


class _Symbol:
    __slots__ = ("name", "canonical", "kind", "scope_id", "span", "references", "meta")

    def __init__(self, name, canonical, kind, scope_id, span, meta):
        self.name = name
        self.canonical = canonical
        self.kind = kind
        self.scope_id = scope_id
        self.span = span
        self.references = 0
        self.meta = meta


class _Ref:
    __slots__ = ("name", "canonical", "scope_id", "span", "hint", "symbol")

    def __init__(self, name, canonical, scope_id, span, hint):
        self.name = name
        self.canonical = canonical
        self.scope_id = scope_id
        self.span = span
        self.hint = hint
        self.symbol = None


# 定义节点 → 符号 kind。
_DEFINITION_KINDS = {
    "Paragraph": "function",
    "ClassDefinition": "class",
    "RecordDefinition": "record",
    "EnumDefinition": "enum",
    "InterfaceDefinition": "interface",
    "AttributeDeclaration": "attribute",
    "MethodDefinition": "method",
    "MethodSignature": "method_signature",
    "FFIFunctionDecl": "ffi_function",
    "FFIStructDef": "ffi_struct",
    "FFICallbackDef": "ffi_callback",
    "FFIEnumDef": "ffi_enum",
    "FFIUnionDef": "ffi_union",
    "FFITypedefDef": "ffi_typedef",
    "FFIBitfieldDef": "ffi_bitfield",
    "FFIFuncPtrDef": "ffi_func_ptr",
}

# 这些节点在 collect 里有专门分支；这里仅用于文档/兜底。
_CLASS_LIKE = frozenset({"ClassDefinition", "RecordDefinition", "EnumDefinition"})

#: 作用域 kind（不是节点 kind）里属于「类/接口」的取值，成员引用优先在这些作用域解析。
_CLASS_SCOPE_KINDS = frozenset({"class", "interface"})


class _SymbolCollector:
    """在 ``_NodeView`` 树上做一次带作用域的定义 + 引用收集。"""

    def __init__(self):
        self.scopes: List[_Scope] = []
        self.symbols: List[_Symbol] = []
        self.imports: List[Dict[str, Any]] = []
        self.exports: List[Dict[str, Any]] = []
        self.refs: List[_Ref] = []
        self._defs_by_scope: Dict[Tuple[int, str], List[_Symbol]] = {}

    # ---- 作用域 / 定义 / 引用 ------------------------------------------------

    def _new_scope(self, name: str, kind: str, parent: Optional[int],
                   span: Tuple[int, int, int, int]) -> int:
        scope_id = len(self.scopes)
        if parent is None:
            path = "module"
        else:
            parent_path = self.scopes[parent].path
            path = f"{parent_path}.{name}" if name else parent_path
        self.scopes.append(_Scope(scope_id, name or "<anonymous>", kind, parent, path, span))
        return scope_id

    def _define(self, scope_id: int, name: Any, kind: str,
                span: Tuple[int, int, int, int], **meta) -> Optional[_Symbol]:
        if not isinstance(name, str) or not name:
            return None
        canonical = _canonical_name(name)
        symbol = _Symbol(name, canonical, kind, scope_id, span, meta)
        self.symbols.append(symbol)
        self._defs_by_scope.setdefault((scope_id, canonical), []).append(symbol)
        return symbol

    def _add_ref(self, name: Any, scope_id: int, span: Tuple[int, int, int, int],
                 hint: Optional[str] = None) -> None:
        if not isinstance(name, str) or not name:
            return
        self.refs.append(_Ref(name, _canonical_name(name), scope_id, span, hint))

    def _walk_children(self, view: _NodeView, scope_id: int) -> None:
        for child in view.children:
            self._collect(child, scope_id)

    def _resolve(self, ref: _Ref) -> Optional[_Symbol]:
        chain: List[int] = []
        scope_id: Optional[int] = ref.scope_id
        while scope_id is not None:
            chain.append(scope_id)
            scope_id = self.scopes[scope_id].parent

        # 成员引用优先在最近的类/接口作用域里找（`己.宽` 不应该被同名形参抢走）。
        if ref.hint == "member":
            for candidate in chain:
                if self.scopes[candidate].kind in _CLASS_SCOPE_KINDS:
                    symbols = self._defs_by_scope.get((candidate, ref.canonical))
                    if symbols:
                        return symbols[-1]

        for candidate in chain:
            symbols = self._defs_by_scope.get((candidate, ref.canonical))
            if symbols:
                return symbols[-1]
        return None

    # ---- 收集主循环 ----------------------------------------------------------

    def collect(self, root: _NodeView) -> None:
        module_scope = self._new_scope("module", "module", None, root.span)
        self._collect(root, module_scope)

        for ref in self.refs:
            ref.symbol = self._resolve(ref)
            if ref.symbol is not None:
                ref.symbol.references += 1

    def _collect(self, view: _NodeView, scope_id: int) -> None:
        kind = view.kind
        node = view.node

        # ---- 引用位置 --------------------------------------------------------
        if kind == "Identifier":
            name = getattr(node, "name", None)
            # `己`/`自`/`self` 是接收者关键字，不是被引用的符号；`self.宽` 这种
            # 点号写法（解析器在 `己.宽` 分支会归一成 `self.宽`）只统计成员名。
            if isinstance(name, str) and name in _RECEIVER_NAMES:
                return
            if isinstance(name, str) and "." in name:
                prefix, _, member = name.rpartition(".")
                if prefix in _RECEIVER_NAMES and member:
                    self._add_ref(member, scope_id, view.span, hint="member")
                    return
            self._add_ref(name, scope_id, view.span)
            return

        if kind == "ParameterList":
            for name in getattr(node, "params", None) or []:
                self._define(scope_id, name, "parameter", view.span)
            return

        if kind == "ParagraphCall":
            self._add_ref(getattr(node, "name", None), scope_id, view.span)
            self._walk_children(view, scope_id)
            return

        if kind == "ClassInstantiation":
            self._add_ref(getattr(node, "class_name", None), scope_id, view.span)
            self._walk_children(view, scope_id)
            return

        if kind == "MemberAccess":
            self._walk_children(view, scope_id)
            self._add_ref(getattr(node, "member", None), scope_id, view.span, hint="member")
            return

        if kind == "SelfAssignment":
            self._add_ref(getattr(node, "attr_name", None), scope_id, view.span, hint="member")
            self._walk_children(view, scope_id)
            return

        if kind in ("CompoundAssignment", "IndexedAssignment", "IndexedCompoundAssignment"):
            self._add_ref(getattr(node, "target", None), scope_id, view.span)
            self._walk_children(view, scope_id)
            return

        if kind == "DecoratorInfo":
            self._add_ref(getattr(node, "name", None), scope_id, view.span)
            self._walk_children(view, scope_id)
            return

        if kind == "ScopeDeclStmt":
            for name in getattr(node, "names", None) or []:
                self._add_ref(name, scope_id, view.span)
            return

        # ---- 导入 / 导出 -----------------------------------------------------
        if kind == "ImportStmt":
            self._collect_import(node, scope_id, view.span)
            return

        if kind == "ExportStmt":
            names = [n for n in (getattr(node, "symbols", None) or []) if isinstance(n, str)]
            self.exports.append({
                "names": names,
                "canonical_names": [_canonical_name(n) for n in names],
                "scope": self.scopes[scope_id].path,
                "span": _span_dict(view.span),
            })
            return

        # ---- 函数 / 类 / 接口 -------------------------------------------------
        if kind == "Paragraph":
            name = getattr(node, "name", None)
            params = getattr(node, "params", None) or []
            self._define(
                scope_id, name, "function", view.span,
                return_type=getattr(node, "return_type", None),
                access=getattr(node, "access_modifier", "public"),
                modifiers=list(getattr(node, "modifiers", None) or []),
                parameters=[p.get("name") for p in params
                            if isinstance(p, dict) and p.get("name")],
            )
            function_scope = self._new_scope(name or "<function>", "function", scope_id, view.span)
            for param in params:
                if isinstance(param, dict) and isinstance(param.get("name"), str):
                    self._define(
                        function_scope, param["name"], "parameter", view.span,
                        type_annotation=param.get("type") or param.get("type_annotation"),
                    )
            self._walk_children(view, function_scope)
            return

        if kind == "DecoratedFunction":
            self._walk_children(view, scope_id)
            return

        if kind in _CLASS_LIKE:
            name = getattr(node, "name", None)
            symbol_kind = _DEFINITION_KINDS[kind]
            self._define(
                scope_id, name, symbol_kind, view.span,
                base_classes=list(getattr(node, "base_classes", None) or []),
                interfaces=list(getattr(node, "interfaces", None) or []),
            )
            for base in getattr(node, "base_classes", None) or []:
                self._add_ref(base, scope_id, view.span)
            for interface in getattr(node, "interfaces", None) or []:
                self._add_ref(interface, scope_id, view.span)

            class_scope = self._new_scope(name or "<class>", "class", scope_id, view.span)
            if kind == "EnumDefinition":
                for member in getattr(node, "members", None) or []:
                    member_name = member if isinstance(member, str) else getattr(member, "name", None)
                    self._define(class_scope, member_name, "enum_member", view.span)
            self._walk_children(view, class_scope)
            return

        if kind == "InterfaceDefinition":
            name = getattr(node, "name", None)
            self._define(
                scope_id, name, "interface", view.span,
                super_interfaces=list(getattr(node, "super_interfaces", None) or []),
            )
            for parent in getattr(node, "super_interfaces", None) or []:
                self._add_ref(parent, scope_id, view.span)
            interface_scope = self._new_scope(name or "<interface>", "interface", scope_id, view.span)
            self._walk_children(view, interface_scope)
            return

        if kind == "AttributeDeclaration":
            self._define(
                scope_id, getattr(node, "name", None), "attribute", view.span,
                type_annotation=getattr(node, "type_annotation", None),
                access=getattr(node, "access_modifier", "public"),
                static=bool(getattr(node, "is_static", False)),
            )
            self._walk_children(view, scope_id)
            return

        if kind in ("MethodDefinition", "MethodSignature"):
            is_constructor = bool(getattr(node, "is_constructor", False))
            if kind == "MethodSignature":
                method_kind = "method_signature"
            elif is_constructor:
                method_kind = "constructor"
            else:
                method_kind = "method"
            name = getattr(node, "name", None)
            self._define(
                scope_id, name, method_kind, view.span,
                return_type=getattr(node, "return_type", None),
                access=getattr(node, "access_modifier", "public"),
                static=bool(getattr(node, "is_static", False)),
                property=bool(getattr(node, "is_property", False)),
            )
            method_scope = self._new_scope(name or "<method>", "function", scope_id, view.span)
            for child in view.children:
                self._collect(child, method_scope)
            return

        if kind == "Parameter":
            self._define(
                scope_id, getattr(node, "name", None), "parameter", view.span,
                type_annotation=getattr(node, "type_annotation", None),
            )
            self._walk_children(view, scope_id)
            return

        # ---- 变量 / 循环 / 异常 ----------------------------------------------
        if kind == "VarDecl":
            self._define(
                scope_id, getattr(node, "name", None), "variable", view.span,
                type_annotation=getattr(node, "type_annotation", None),
                block_scoped=bool(getattr(node, "block_scoped", False)),
            )
            self._walk_children(view, scope_id)
            return

        if kind == "DestructuringAssignment":
            for name in getattr(node, "variables", None) or []:
                self._define(scope_id, name, "variable", view.span)
            self._walk_children(view, scope_id)
            return

        if kind == "ForeachStmt":
            self._define(scope_id, getattr(node, "variable", None), "variable", view.span)
            self._walk_children(view, scope_id)
            return

        if kind == "WithStmt":
            variable = getattr(node, "variable", None)
            if isinstance(variable, str):
                self._define(scope_id, variable, "variable", view.span)
            for item in getattr(node, "items", None) or []:
                if isinstance(item, (list, tuple)) and len(item) >= 2 and isinstance(item[1], str):
                    self._define(scope_id, item[1], "variable", view.span)
            self._walk_children(view, scope_id)
            return

        if kind == "WithCloseStmt":
            for item in getattr(node, "items", None) or []:
                if isinstance(item, (list, tuple)) and len(item) >= 2 and isinstance(item[1], str):
                    self._define(scope_id, item[1], "variable", view.span)
            self._walk_children(view, scope_id)
            return

        if kind in ("TryStmt", "CatchClause"):
            catch_var = getattr(node, "catch_var", None)
            if isinstance(catch_var, str) and catch_var:
                self._define(scope_id, catch_var, "variable", view.span)
            self._walk_children(view, scope_id)
            return

        if kind == "LambdaExpression":
            lambda_scope = self._new_scope("<lambda>", "function", scope_id, view.span)
            for name in getattr(node, "params", None) or []:
                self._define(lambda_scope, name, "parameter", view.span)
            self._walk_children(view, lambda_scope)
            return

        if kind in ("ListComprehension", "SetComprehension", "DictComprehension"):
            comp_scope = self._new_scope("<comprehension>", "comprehension", scope_id, view.span)
            variable = getattr(node, "variable", None)
            if isinstance(variable, str):
                self._define(comp_scope, variable, "variable", view.span)
            for generator in getattr(node, "generators", None) or []:
                if isinstance(generator, (list, tuple)) and generator and isinstance(generator[0], str):
                    self._define(comp_scope, generator[0], "variable", view.span)
            self._walk_children(view, comp_scope)
            return

        if kind == "MatchPattern":
            pattern_kind = getattr(node, "kind", None)
            binding = getattr(node, "binding", None)
            if pattern_kind in ("variable", "type_check") and isinstance(binding, str) and binding:
                self._define(scope_id, binding, "variable", view.span)
            self._walk_children(view, scope_id)
            return

        if kind == "FFILoadLibrary":
            self._define(
                scope_id, getattr(node, "alias", None), "ffi_library", view.span,
                library=getattr(node, "library_path", None),
            )
            self._walk_children(view, scope_id)
            return

        if kind in _DEFINITION_KINDS:
            self._define(scope_id, getattr(node, "name", None),
                         _DEFINITION_KINDS[kind], view.span)
            self._walk_children(view, scope_id)
            return

        # ---- 兜底 ------------------------------------------------------------
        self._walk_children(view, scope_id)

    def _collect_import(self, node: ASTNode, scope_id: int,
                        span: Tuple[int, int, int, int]) -> None:
        module_name = getattr(node, "module_name", None)
        symbols = [s for s in (getattr(node, "symbols", None) or []) if isinstance(s, str)]
        alias = getattr(node, "alias", None)
        language = getattr(node, "language", None)
        extra_modules = []
        for item in getattr(node, "extra_modules", None) or []:
            if isinstance(item, (list, tuple)) and item:
                extra_modules.append({
                    "module": item[0],
                    "alias": item[1] if len(item) > 1 else None,
                })

        self.imports.append({
            "module": module_name,
            "names": symbols,
            "alias": alias,
            "language": language,
            "extra_modules": extra_modules,
            "scope": self.scopes[scope_id].path,
            "span": _span_dict(span),
        })

        imported_names = symbols or [alias or module_name]
        for imported in imported_names:
            if isinstance(imported, str) and imported:
                self._define(scope_id, imported, "import", span, module=module_name)
        for extra in extra_modules:
            name = extra.get("alias") or extra.get("module")
            if isinstance(name, str) and name:
                self._define(scope_id, name, "import", span, module=extra.get("module"))


def _symbol_to_json(symbol: _Symbol, collector: _SymbolCollector) -> Dict[str, Any]:
    scope = collector.scopes[symbol.scope_id]
    entry: Dict[str, Any] = {
        "name": symbol.name,
        "canonical": symbol.canonical,
        "kind": symbol.kind,
        "scope": scope.path,
        "scope_kind": scope.kind,
        "span": _span_dict(symbol.span),
        "references": symbol.references,
    }
    for key, value in symbol.meta.items():
        if value is None or value == [] or value == {} or value is False:
            continue
        entry[key] = _jsonable(value)
    return entry


def _collect_symbols(source: str, file_label: Optional[str] = None) -> Tuple[_NodeView, _SymbolCollector]:
    module = _parse(source, file_label)
    view = _build_view(module)
    collector = _SymbolCollector()
    collector.collect(view)
    return view, collector


def symbols_json(source: str, file_label: Optional[str] = None) -> Dict[str, Any]:
    """导出符号表：定义、导入、作用域与被引用次数。

    参数
    ----
    source : str
        光明源码。
    file_label : str | None
        只用于元信息，不读磁盘。

    返回
    ----
    dict
        ``definitions``：每个定义一条，含 ``name`` / ``canonical`` / ``kind`` /
        ``scope`` / ``span`` / ``references``（被引用次数）以及该定义特有的
        字段（``parameters`` / ``return_type`` / ``type_annotation`` 等）。

        ``imports``：导入语句（模块、符号、别名、作用域）。

        ``exports``：``导出`` 语句列出的名字。

        ``scopes``：作用域树，``parent`` 为父作用域 path，``module`` 为根。

        ``references``：按 canonical 名聚合的引用（``resolved`` 表示是否落到
        本文件里的某个定义；``打印`` 这类内建/外部名字会落在 ``unresolved``）。

    命名口径
    --------
    ``canonical`` = NFKC 归一后的名字，与 D 线 ``--canonical`` 的「同语义一个
    名字」对齐；定义处 ``name`` 保留源码原样，便于回写。

    作用域口径
    ----------
    作用域按 **模块 / 函数 / 类 / 接口** 建树；``令``（``block_scoped``）这类
    块级声明仍记在所属函数作用域下，只通过 ``block_scoped`` 字段标注，不做
    块级隔离。类成员（属性/方法）定义在类作用域，构造器形参与成员同名时按
    「成员引用优先类作用域、裸名优先最近作用域」解析。

    ``span`` 说明
    --------------
    ``start_line == 0`` 表示解析器没有记录该节点的位置（类成员、形参、
    表达式叶子常见），**不是第 0 行**；需要精确行号时以语句级节点为准。
    """
    _view, collector = _collect_symbols(source, file_label)

    definitions = sorted(
        (_symbol_to_json(symbol, collector) for symbol in collector.symbols),
        key=lambda item: (
            item["scope"],
            item["span"]["start_line"],
            item["span"]["start_col"],
            item["canonical"],
            item["kind"],
        ),
    )

    scopes_json = []
    for scope in collector.scopes:
        scopes_json.append({
            "path": scope.path,
            "name": scope.name,
            "kind": scope.kind,
            "parent": None if scope.parent is None else collector.scopes[scope.parent].path,
            "span": _span_dict(scope.span),
            "definitions": sorted(
                {symbol.canonical for symbol in collector.symbols if symbol.scope_id == scope.id}
            ),
        })

    # 引用聚合：同一 canonical + 同一落点合并。
    buckets: Dict[Tuple[str, Optional[int]], Dict[str, Any]] = {}
    for ref in collector.refs:
        symbol = ref.symbol
        key = (ref.canonical, None if symbol is None else id(symbol))
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {
                "name": ref.name,
                "canonical": ref.canonical,
                "count": 0,
                "resolved": symbol is not None,
                "kind": symbol.kind if symbol is not None else None,
                "scope": collector.scopes[symbol.scope_id].path if symbol is not None else None,
            }
            buckets[key] = bucket
        bucket["count"] += 1

    references = sorted(
        buckets.values(),
        key=lambda item: (-item["count"], item["canonical"], item["scope"] or ""),
    )
    unresolved = sorted({item["canonical"] for item in references if not item["resolved"]})

    return {
        "file": file_label,
        "language": "light",
        "schema_version": SCHEMA_VERSION,
        "canonical_rule": "NFKC",
        "definitions": definitions,
        "imports": collector.imports,
        "exports": collector.exports,
        "scopes": scopes_json,
        "references": references,
        "unresolved": unresolved,
        "stats": {
            "definition_count": len(definitions),
            "scope_count": len(scopes_json),
            "reference_count": sum(item["count"] for item in references),
        },
    }


# =============================================================================
# 3) span 级局部补丁
# =============================================================================

_SPAN_KEYS = ("start_line", "start_col", "end_line", "end_col")


def _validate_int(value: Any, field_name: str, edit_index: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PatchError(
            f"编辑 {edit_index} 的 span.{field_name} 必须是整数，"
            f"实际是 {type(value).__name__}：{value!r}"
        )
    return value


def _offset_for(lines: Sequence[str], line_starts: Sequence[int],
                line: int, col: int, field_name: str, edit_index: int) -> int:
    line_count = len(lines)
    if line < 1 or line > line_count:
        raise PatchError(
            f"编辑 {edit_index} 的 {field_name} 越界：行号 {line} 不在 1..{line_count} 范围内"
        )
    content = lines[line - 1]
    max_col = len(content) + 1  # 允许插入到行尾（end 是半开区间）
    if col < 1 or col > max_col:
        raise PatchError(
            f"编辑 {edit_index} 的 {field_name} 越界：第 {line} 行共 {len(content)} 个字符，"
            f"列号 {col} 不在 1..{max_col} 范围内"
        )
    return line_starts[line - 1] + (col - 1)


def _format_span(item: Dict[str, Any]) -> str:
    span = item["span"]
    return (
        f"[{span['start_line']}:{span['start_col']} -> "
        f"{span['end_line']}:{span['end_col']})"
    )


def patch(source: str, edits: Sequence[Dict[str, Any]]) -> str:
    """按 span 做确定性局部替换，返回新源码。

    参数
    ----
    source : str
        原源码。
    edits : list[dict]
        ``[{"span": {"start_line","start_col","end_line","end_col"}, "text": "..."}]``，
        坐标为 **1 起 + 半开区间**（见模块头）。``text`` 是要替换进去的新文本，
        删除请传空串 ``""``。

    返回
    ----
    str
        替换后的完整源码（未编辑的字节原样保留，不做格式化）。

    异常
    ----
    PatchError
        以下任一情况都会拒绝（中文原因）：

        - ``span`` 缺少字段 / 坐标不是整数；
        - 坐标越界（行号或列号超出源码范围）；
        - ``span`` 不闭合（起点在终点之后）；
        - 多个编辑互相交叠，或同一位置有多个纯插入（顺序不确定）；
        - ``text`` 不是字符串。

    编辑列表**不需要**预先排序；函数会按起点排序后从后往前应用，因此多个
    不交叠编辑可以一次完成，且结果与编辑的书写顺序无关。
    """
    if not isinstance(source, str):
        raise TypeError("source 必须是 str")
    if not isinstance(edits, (list, tuple)):
        raise PatchError(
            f"edits 必须是列表，实际是 {type(edits).__name__}；"
            "格式：[{span: {start_line, start_col, end_line, end_col}, text: str}]"
        )

    lines = _source_lines(source)
    line_starts = _line_starts(source)
    normalized: List[Dict[str, Any]] = []

    for index, raw_edit in enumerate(edits, start=1):
        if not isinstance(raw_edit, dict):
            raise PatchError(
                f"编辑 {index} 必须是字典，实际是 {type(raw_edit).__name__}；"
                "格式：{span: {...}, text: str}"
            )
        if "span" not in raw_edit:
            raise PatchError(f"编辑 {index} 缺少 span 字段")
        if "text" not in raw_edit:
            raise PatchError(f"编辑 {index} 缺少 text 字段")
        span = raw_edit["span"]
        text = raw_edit["text"]
        if not isinstance(span, dict):
            raise PatchError(f"编辑 {index} 的 span 必须是字典，实际是 {type(span).__name__}")
        missing = [key for key in _SPAN_KEYS if key not in span]
        if missing:
            raise PatchError(
                f"编辑 {index} 的 span 缺少字段：{', '.join(missing)}；"
                "需要 start_line / start_col / end_line / end_col"
            )
        values = {key: _validate_int(span[key], key, index) for key in _SPAN_KEYS}
        if not isinstance(text, str):
            raise PatchError(f"编辑 {index} 的 text 必须是字符串，实际是 {type(text).__name__}")

        start_offset = _offset_for(
            lines, line_starts, values["start_line"], values["start_col"], "start_line/start_col", index
        )
        end_offset = _offset_for(
            lines, line_starts, values["end_line"], values["end_col"], "end_line/end_col", index
        )
        if start_offset > end_offset:
            raise PatchError(
                f"编辑 {index} 的 span 不闭合：起点 {_format_span({'span': values})} "
                f"在终点之后（start_line:{values['start_line']}, start_col:{values['start_col']} 晚于 "
                f"end_line:{values['end_line']}, end_col:{values['end_col']}）"
            )

        normalized.append({
            "index": index,
            "span": values,
            "text": text,
            "start_offset": start_offset,
            "end_offset": end_offset,
        })

    normalized.sort(key=lambda item: (item["start_offset"], item["end_offset"], item["index"]))

    for previous, current in zip(normalized, normalized[1:]):
        if previous["end_offset"] > current["start_offset"]:
            raise PatchError(
                f"编辑 {previous['index']} 与编辑 {current['index']} 交叠："
                f"前者结束于 {_format_span(previous)}，后者开始于 {_format_span(current)}；"
                "多个编辑的 span 不允许重叠"
            )
        previous_is_insert = previous["start_offset"] == previous["end_offset"]
        current_is_insert = current["start_offset"] == current["end_offset"]
        if (previous_is_insert and current_is_insert
                and previous["start_offset"] == current["start_offset"]):
            raise PatchError(
                f"编辑 {previous['index']} 与编辑 {current['index']} 在同一位置插入（{_format_span(previous)}），"
                "插入顺序不确定；请合并成一次编辑"
            )

    if not normalized:
        return source

    pieces: List[str] = []
    cursor = len(source)
    for item in reversed(normalized):
        pieces.append(source[item["end_offset"]:cursor])
        pieces.append(item["text"])
        cursor = item["start_offset"]
    pieces.append(source[:cursor])
    return "".join(reversed(pieces))


# =============================================================================
# 4) diff 摘要
# =============================================================================

def _name_in_text(name: str, text: str) -> bool:
    """名字是否出现在某段文本里；ASCII 名字要求词边界，避免 ``a`` 命中一切。"""
    if not name:
        return False
    if name.isascii():
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])"
        return re.search(pattern, text) is not None
    return name in text


def _definition_fingerprint(definition: Dict[str, Any]) -> str:
    """定义内容指纹：排除位置与引用次数，只比较语义字段。"""
    ignored = {"span", "references"}
    parts = [
        f"{key}={definition[key]!r}"
        for key in sorted(definition)
        if key not in ignored
    ]
    return "\n".join(parts)


def _definition_touches_lines(definition: Dict[str, Any], line_numbers: set) -> bool:
    span = definition.get("span") or {}
    start = span.get("start_line") or 0
    end = span.get("end_line") or start
    if start <= 0:
        return False
    return any(start <= line <= end for line in line_numbers)


def _reference_totals(symbols: Optional[Dict[str, Any]]) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    if not symbols:
        return totals
    for item in symbols.get("references", ()):
        canonical = item.get("canonical")
        if canonical:
            totals[canonical] = totals.get(canonical, 0) + int(item.get("count", 0))
    return totals


def _definition_key(definition: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        definition.get("canonical", ""),
        definition.get("kind", ""),
        definition.get("scope", ""),
    )


def diff_summary(old: str, new: str) -> Dict[str, Any]:
    """对比两份源码，给出「改了哪些行 / 涉及哪些符号」。

    参数
    ----
    old, new : str
        修改前后的源码。任一份语法非法时不会抛异常：行级 diff 照常返回，
        ``symbols.available`` 置 ``False`` 并给出 ``error``。

    返回
    ----
    dict
        - ``identical``：两份源码是否逐字相同；
        - ``changed_lines``：``{"old": [...], "new": [...]}``，1 起行号；
        - ``blocks``：按 ``difflib`` 合并后的变更块（``replace`` / ``insert`` / ``delete``）；
        - ``symbols``：``added`` / ``removed`` / ``changed``（定义级）与
          ``affected``（定义 span 覆盖变更行的符号）、``referenced``（名字出现在
          变更行文本里的符号）、``reference_delta``（引用次数变化）。
    """
    if not isinstance(old, str) or not isinstance(new, str):
        raise TypeError("diff_summary 的 old/new 必须是 str")

    old_lines = old.splitlines()
    new_lines = new.splitlines()
    old_changed: List[int] = []
    new_changed: List[int] = []
    blocks: List[Dict[str, Any]] = []

    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    opcode_to_kind = {"replace": "replace", "delete": "delete", "insert": "insert"}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        old_changed.extend(range(i1 + 1, i2 + 1))
        new_changed.extend(range(j1 + 1, j2 + 1))
        old_text = "\n".join(old_lines[i1:i2])
        new_text = "\n".join(new_lines[j1:j2])
        truncated = False
        if len(old_text) > _MAX_BLOCK_CHARS:
            old_text = old_text[:_MAX_BLOCK_CHARS]
            truncated = True
        if len(new_text) > _MAX_BLOCK_CHARS:
            new_text = new_text[:_MAX_BLOCK_CHARS]
            truncated = True
        blocks.append({
            "kind": opcode_to_kind[tag],
            "old_start_line": i1 + 1,
            "old_end_line": i2,
            "new_start_line": j1 + 1,
            "new_end_line": j2,
            "old_text": old_text,
            "new_text": new_text,
            "truncated": truncated,
        })

    old_changed_set = set(old_changed)
    new_changed_set = set(new_changed)

    old_symbols: Optional[Dict[str, Any]] = None
    new_symbols: Optional[Dict[str, Any]] = None
    symbols_error: Optional[str] = None
    try:
        old_symbols = symbols_json(old)
        new_symbols = symbols_json(new)
    except Exception as exc:  # 语法非法也要能给行级 diff
        symbols_error = f"{type(exc).__name__}: {exc}"

    symbol_report: Dict[str, Any] = {
        "available": old_symbols is not None and new_symbols is not None,
        "added": [],
        "removed": [],
        "changed": [],
        "affected": [],
        "referenced": [],
        "reference_delta": [],
        "error": symbols_error,
    }

    if symbol_report["available"]:
        old_defs = {_definition_key(item): item for item in old_symbols["definitions"]}
        new_defs = {_definition_key(item): item for item in new_symbols["definitions"]}

        symbol_report["added"] = [
            new_defs[key] for key in sorted(new_defs) if key not in old_defs
        ]
        symbol_report["removed"] = [
            old_defs[key] for key in sorted(old_defs) if key not in new_defs
        ]
        symbol_report["changed"] = [
            new_defs[key]
            for key in sorted(new_defs)
            if key in old_defs
            and _definition_fingerprint(old_defs[key]) != _definition_fingerprint(new_defs[key])
        ]

        affected: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for key, definition in old_defs.items():
            if _definition_touches_lines(definition, old_changed_set):
                affected[key] = dict(definition, where="old")
        for key, definition in new_defs.items():
            if _definition_touches_lines(definition, new_changed_set):
                if key in affected:
                    affected[key]["where"] = "both"
                else:
                    affected[key] = dict(definition, where="new")
        symbol_report["affected"] = sorted(
            affected.values(),
            key=lambda item: (
                item["span"]["start_line"],
                item["canonical"],
                item["scope"],
            ),
        )

        old_totals = _reference_totals(old_symbols)
        new_totals = _reference_totals(new_symbols)
        symbol_report["reference_delta"] = [
            {
                "canonical": name,
                "old": old_totals.get(name, 0),
                "new": new_totals.get(name, 0),
                "delta": new_totals.get(name, 0) - old_totals.get(name, 0),
            }
            for name in sorted(set(old_totals) | set(new_totals))
            if old_totals.get(name, 0) != new_totals.get(name, 0)
        ]

        changed_text = "\n".join(
            old_lines[line - 1] for line in sorted(old_changed_set)
        ) + "\n" + "\n".join(
            new_lines[line - 1] for line in sorted(new_changed_set)
        )
        known_names = {
            item["canonical"] for item in old_symbols["definitions"] + new_symbols["definitions"]
        }
        known_names.update(old_totals)
        known_names.update(new_totals)
        symbol_report["referenced"] = sorted(
            name for name in known_names if _name_in_text(name, changed_text)
        )

    return {
        "identical": old == new,
        "old_line_count": len(old_lines),
        "new_line_count": len(new_lines),
        "changed_lines": {"old": old_changed, "new": new_changed},
        "changed_line_count": {
            "old": len(old_changed_set),
            "new": len(new_changed_set),
        },
        "blocks": blocks,
        "symbols": symbol_report,
    }
