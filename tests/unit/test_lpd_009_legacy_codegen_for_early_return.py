# -*- coding: utf-8 -*-
"""LP-D-009 回归：legacy 代码生成器（`_light_import_hook` 路径）在顶层 段落 的
for 体含提前 `返回` 时，不得把后续顶层 段落 缩进嵌套进前一函数体。

缺陷回顾
--------
「运行检视器」复刻期，`从 运行检视器 导入 取差异` 报
`cannot import name '取差异'`（及 `name '存基线' is not defined`）。
推测 legacy 生成器（经 `_light_import_hook` 编译纯光明模块走此路径）在某 段落
的 for 内有提前 `返回` 时，把后续顶层 `段落` 错误缩进嵌套进前一函数体
（曾观察疑似 `nonlocal` 生成），导致这些函数不进模块命名空间。

本回归（核对优先，不预设改代码）
------------------------------
构造纯光明模块：前一段落 for 体含提前 `返回`，后接两个顶层段落。验证两件事：
1) 生成的 Python 中三个 `def` 均在模块级（indent=0），不被前一段落吞并；
2) 经 `_light_import_hook` 实际导入后，两个后接段落都可从模块命名空间取到且可调用。

实测结论（见交付报告 `_task6_LPD009_legacy_codegen_核对.md`）
---------------------------------------------------------
当前编译器（R98 后）所有变体均无法复现，疑于后续编译器轮次修复。
本测试守江湖不再回潮：若有人让顶层段落缩进未复位（+1），取差异/存基线 的
indent != 0，test_生成代码_后续顶层段落缩进为模块级 立即变红。

反跑判据
------
· 临时让 code_generator 顶层段落缩进 +1（模拟缩进未复位）→ 取差异/存基线 的
  indent != 0 → test_生成代码_后续顶层段落缩进为模块级 变红（回到「被前一段落吞并」）。
"""
import importlib
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, "src"), os.path.join(_ROOT, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402

from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402
import _light_import_hook  # noqa: E402


def _gen(src: str) -> str:
    """与 `_light_import_hook._compile_light` 完全一致的编译路径（legacy 生成器）。"""
    module = LightParser().parse(src)
    return PythonCodeGenerator().generate(module, is_main=False)


def _top_level_def_indents(py: str) -> dict:
    out = {}
    for ln in py.splitlines():
        s = ln.lstrip()
        if s.startswith("def "):
            indent = len(ln) - len(s)
            fname = s[4:].split("(")[0].strip()
            out[fname] = indent
    return out


# 形如运行检视器的复刻结构：前一段落 for 体内提前返回，后接两个顶层段落
_MODULE_SRC_BASIC = (
    "段落 取节点属性(快照, 名字):\n"
    "  设 表 为 []\n"
    "  遍历 项 之 快照[\"节点\"]:\n"
    "    如果 项[\"名字\"] == 名字:\n"
    "      返回 项[\"属性\"]\n"
    "  返回 空\n"
    "\n"
    "段落 取差异(旧快照):\n"
    "  返回 旧快照\n"
    "\n"
    "段落 存基线():\n"
    "  返回 空\n"
)

# 带闭包（嵌套段落）的变体：for 体内定义嵌套段落并提前返回（「疑似 nonlocal」指向）
_MODULE_SRC_CLOSURE = (
    "段落 取节点属性(快照, 名字):\n"
    "  遍历 项 之 快照[\"节点\"]:\n"
    "    段落 命中(节点):\n"
    "      如果 节点[\"名字\"] == 名字:\n"
    "        返回 节点[\"属性\"]\n"
    "    设 结果 为 命中(项)\n"
    "  返回 空\n"
    "\n"
    "段落 取差异(旧快照):\n"
    "  返回 旧快照\n"
    "\n"
    "段落 存基线():\n"
    "  返回 空\n"
)

_VARIANTS = (
    ("基本_for早期返回", _MODULE_SRC_BASIC),
    ("闭包_for早期返回", _MODULE_SRC_CLOSURE),
)


class TestLegacyCodegenForEarlyReturn:
    def test_生成代码_后续顶层段落缩进为模块级(self):
        """核心守卫：三个顶层段落的 def 都必须在 indent=0，不得被前一段落吞并。"""
        for label, src in _VARIANTS:
            py = _gen(src)
            ind = _top_level_def_indents(py)
            for f in ("取节点属性", "取差异", "存基线"):
                assert ind.get(f) == 0, (
                    "[%s] 顶层段落 %s 缩进=%s（应=0，被前一段落吞并）"
                    % (label, f, ind.get(f))
                )

    def test_实际导入_后续段落进模块命名空间(self):
        """端到端：经 `_light_import_hook` 导入纯光明模块，两个后接段落都能取到且可调用。"""
        for idx, (label, src) in enumerate(_VARIANTS):
            mod_name = "lpd009_mod_%d" % idx
            # 清掉可能的缓存，避免同名模块复用上一次导入结果
            sys.modules.pop(mod_name, None)
            with tempfile.TemporaryDirectory() as d:
                mod_path = os.path.join(d, mod_name + ".light")
                with open(mod_path, "w", encoding="utf-8") as fh:
                    fh.write(src)
                _light_import_hook.uninstall()  # 先清残留，保证本用例独立
                _light_import_hook.install([d])
                try:
                    mod = importlib.import_module(mod_name)
                    assert hasattr(mod, "取节点属性"), "[%s] 取节点属性 未导入" % label
                    assert hasattr(mod, "取差异"), (
                        "[%s] 取差异 未进模块命名空间（被前一段落吞并）" % label
                    )
                    assert hasattr(mod, "存基线"), (
                        "[%s] 存基线 未进模块命名空间（被前一段落吞并）" % label
                    )
                    # 实际可调用，确认不是仅名字占位
                    assert mod.取差异("x") == "x"
                    assert mod.存基线() is None
                finally:
                    _light_import_hook.uninstall()
                    sys.modules.pop(mod_name, None)
