# -*- coding: utf-8 -*-
"""作用域影子变量检查（L-165 类静默缺陷的编译告警）

背景（第44轮实测发现的 L-165）
------------------------------
`mock大模型服务器.light` 里：

    设 当前实例 为 空                      # 模块级

    段落 新建Mock服务 接收 选项:
      设 实例 为 新建 Mock大模型服务器(选项)
      设 当前实例 为 实例                  # ← 意图是写回模块级变量
      返回 实例

按 Python（也就是光明）的作用域语义，函数体内的 `设 当前实例 为 ...` 一律创建
**局部**变量，模块级 `当前实例` 不受影响。想写回模块级变量必须显式声明
`全局 当前实例。`。

漏声明时**没有任何报错**：不报 NameError（局部赋值合法）、不报警告，只有运行期
表现为「模块级变量恒为初始值」，症状离现场极远（本例中表现为 HTTP 服务恒返回
500 MOCK_NOT_READY，排查成本极高）。

本模块做的事
------------
解析完成后对 AST 做一次静态扫描：

* 收集**模块级**被赋值的名字；
* 对每个顶层 `段落`（函数）收集：形参名、`全局` 声明的名字、函数体内被赋值的名字；
* 若「函数体内赋值名 ∈ 模块级名」且「不在 `全局` 声明里」且「不是形参」，给出告警。

这是**建议性**告警而非错误：函数内刻意用同名局部变量遮蔽模块级变量是完全合法的
写法，所以本检查默认由环境变量 `LIGHT_WARN_GLOBAL_SHADOW` 控制（见 compiler.py
的接入点），便于在 CI 里按需开启，不污染既有构建输出。

刻意不做的事
------------
* 不进入嵌套 `段落` / 类 / 方法体——它们各自是独立作用域，应各自判定；
* 不对「只读不写」的名字告警（读模块级变量是合法且常见的）；
* 不改任何既有语义，只产出字符串列表。
"""
from typing import Any, Dict, List, Set

from ast_nodes_v3 import (  # noqa: F401  —— 仅供类型与常量引用
    ASTNode,
    Assignment,
    ClassDefinition,
    CompoundAssignment,
    DestructuringAssignment,
    Identifier,
    MethodDefinition,
    Module,
    Paragraph,
    ScopeDeclStmt,
    VarDecl,
)

# 进入这些节点意味着进入**新的作用域**，不再算作外层函数体的一部分
_SCOPE_BOUNDARY = (Paragraph, ClassDefinition, MethodDefinition)


def _slots_of(node: Any) -> List[str]:
    """取节点（含基类）声明的全部 __slots__ 字段名。"""
    names: List[str] = []
    for cls in type(node).__mro__:
        s = getattr(cls, '__slots__', ())
        if isinstance(s, str):
            s = (s,)
        names.extend(s)
    return names


def _child_nodes(node: Any) -> List[Any]:
    """取节点的直接 AST 子节点（只走 __slots__，避免扫到 line/col 等标量）。"""
    out: List[Any] = []
    for name in _slots_of(node):
        try:
            val = getattr(node, name, None)
        except Exception:  # noqa: BLE001 —— 槽位未初始化时跳过
            continue
        if isinstance(val, ASTNode):
            out.append(val)
        elif isinstance(val, (list, tuple)):
            out.extend(x for x in val if isinstance(x, ASTNode))
    return out


def _walk(node: Any, stop_at_scope: bool = True):
    """深度优先遍历；stop_at_scope=True 时不进入嵌套函数/类/方法体。"""
    stack = [node]
    while stack:
        cur = stack.pop()
        for child in _child_nodes(cur):
            if stop_at_scope and isinstance(child, _SCOPE_BOUNDARY):
                continue
            yield child
            stack.append(child)


def _assigned_names(nodes) -> Dict[str, int]:
    """从一串语句里收集「被赋值的名字 → 首次出现的行号」。

    覆盖三种写法：
    * `VarDecl`  —— `设 X 为 Y` / `令 X = Y`（光明里绝大多数赋值走这条）；
    * `Assignment` —— `X = Y` 形式的裸赋值；
    * `CompoundAssignment` / `DestructuringAssignment` —— `X 加上 1`、`设 甲, 乙 为 ...`。
    """
    found: Dict[str, int] = {}
    for st in nodes:
        # `设 X 为 Y`：名字直接是字符串
        if isinstance(st, VarDecl):
            name = getattr(st, 'name', None)
            if isinstance(name, str) and name:
                found.setdefault(name, getattr(st, 'line', 0))
            continue
        if isinstance(st, Assignment):
            if isinstance(st.target, Identifier):
                found.setdefault(st.target.name, getattr(st, 'line', 0))
        elif isinstance(st, CompoundAssignment):
            if isinstance(st.target, str):
                found.setdefault(st.target, getattr(st, 'line', 0))
        elif isinstance(st, DestructuringAssignment):
            for v in getattr(st, 'variables', None) or []:
                name = v if isinstance(v, str) else getattr(v, 'name', None)
                if name:
                    found.setdefault(name, getattr(st, 'line', 0))
    return found


def _assigned_names_in_body(body) -> Dict[str, int]:
    """收集函数体（含 if/while/for/try 等嵌套块，但不进嵌套函数）内的赋值名。"""
    found: Dict[str, int] = {}
    if isinstance(body, (list, tuple)):
        stmts = list(body)
    else:
        stmts = [body]

    def _scan(seq):
        for st in seq:
            if isinstance(st, _SCOPE_BOUNDARY):
                continue
            for name, line in _assigned_names([st]).items():
                found.setdefault(name, line)
            for child in _child_nodes(st):
                if isinstance(child, _SCOPE_BOUNDARY):
                    continue
                _scan([child])

    _scan(stmts)
    return found


def _declared_global_names(body) -> Set[str]:
    """函数体内 `全局 X。` 声明过的名字（不进嵌套函数）。"""
    names: Set[str] = set()
    if isinstance(body, (list, tuple)):
        stmts = list(body)
    else:
        stmts = [body]
    for st in _walk_nodes_no_scope(stmts):
        if isinstance(st, ScopeDeclStmt) and st.kind == 'global':
            names.update(st.names or [])
    return names


def _walk_nodes_no_scope(stmts):
    for st in stmts:
        yield st
        for child in _walk(st, stop_at_scope=True):
            yield child


def _param_names(func: Paragraph) -> Set[str]:
    names: Set[str] = set()
    for p in getattr(func, 'params', None) or []:
        if isinstance(p, dict):
            n = p.get('name') or p.get('名称')
        else:
            n = getattr(p, 'name', None)
        if n:
            names.add(n)
    return names


def check_global_shadow(module: Module, filename: str = '') -> List[str]:
    """检查「函数内写模块级同名变量但未声明 全局」的影子变量。

    返回告警字符串列表（可能为空）。纯函数，不改动 AST、不抛异常。
    """
    warnings: List[str] = []
    if not isinstance(module, Module):
        return warnings

    top = list(getattr(module, 'statements', None) or [])
    module_writes = _assigned_names(top)
    if not module_writes:
        return warnings

    for st in top:
        if not isinstance(st, Paragraph):
            continue
        declared = _declared_global_names(st.body)
        params = _param_names(st)
        assigned = _assigned_names_in_body(st.body)
        shadowed = sorted(
            n for n in assigned
            if n in module_writes and n not in declared and n not in params
        )
        for name in shadowed:
            line = assigned[name] or getattr(st, 'line', 0)
            where = f'{filename}:{line}' if filename else f'第{line}行'
            warnings.append(
                f"⚠ 编译警告（L-166 影子变量）：{where} 段落『{st.name}』内给『{name}』赋值，"
                f"但模块级也存在同名变量且未在该段落内声明『全局 {name}。』。"
                f"按作用域语义这里会新建**局部**变量，模块级的『{name}』不会被修改"
                f"（L-165 即此类静默缺陷）。若要写回模块级变量，请在段落内加"
                f"『全局 {name}。』；若本意就是局部变量，可忽略此告警。"
            )
    return warnings
