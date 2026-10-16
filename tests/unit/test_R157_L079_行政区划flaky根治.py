# -*- coding: utf-8 -*-
"""R157 A 线 · L-079 flaky 根治锚点测试。

钉住「秒挂」根因的快速失败路径：`_module_has_imports` 不得 fail-open 静默降级。

历史背景（L-079，缺陷账唯一「待修复」项）：
  `test_原生腿_R13B_能力扩展.py::Test行政区划扩展::test_O0_行政区划代码_对拍与扩展`
  在 0.88 `-n 8` 全量门禁下偶发 0.12s 秒挂（正常 ~5.5s）。
  本轮实测定位：秒挂形态 = `NotImplementedError: 未定义的段落：获取行政区划代码`
  在 ~0.15s 抛出（无需 clang）——这是 `compile_light_typed` 走了**单模块快速路径**
  而非多模块编译。快速路径下 stdlib 导出名全部未注册，任何 stdlib 调用都被
  `_reject_unknown_call` 拒。

  `_module_has_imports` 旧实现 `except Exception: return False`（fail-open）在
  解析器/适配器偶发异常时把「源码明明有导入」判成 False → 必然秒挂。R157-A 改为
  fail-closed + 文本级兜底：parse 异常 + 源码含导入 → 抛原始异常（宁可真报错，
  不许静默走错路径造出误导性秒挂）。

本测试用 monkeypatch 制造「parse 异常」，验证 fail-closed 行为：
  1. 含导入源码 + parse 异常 → 必须抛原始异常（不得返回 False）；
  2. 不含导入源码 + parse 异常 → 返回 False（与真值一致，快速路径合法）；
  3. `_text_has_imports` 兜底判定正确（含导入真、注释假、无导入假）；
  4. 正常路径回归：`_module_has_imports` 对含导入返回 True、不含导入返回 False。

不跑全量；只做定向 + 本文件。
"""
import os
import sys

import pytest

# ── 路径常量（仓库根 / src / stdlib / contrib）──────────────────────
_仓库根 = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_仓库根, 'src'), os.path.join(_仓库根, 'stdlib'),
           os.path.join(_仓库根, 'contrib')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _light_import_hook  # noqa: E402
_light_import_hook.install([os.path.join(_仓库根, 'stdlib'),
                            os.path.join(_仓库根, 'contrib'), _仓库根])

from llvm import compiler as _compiler  # noqa: E402


# ── 真实含导入源码（与 L-079 活样本同构）───────────────────────────
def _行政区划源码() -> str:
    from 中国行政区划 import ChinaRegion
    r = ChinaRegion()
    code = ['从 中国行政区划 导入 获取行政区划代码', '段落 主:']
    for n, c in r._region_code_map.items():
        code.append('  输出(获取行政区划代码("%s"))' % n)
    for n, c in [("湛江市", "440800"), ("中山市", "442000"),
                 ("东莞市", "441900"), ("金华市", "330700")]:
        code.append('  输出(获取行政区划代码("%s"))' % n)
    return '\n'.join(code)


_无导入源码 = '段落 主:\n  输出(1)'


class _模拟解析异常(RuntimeError):
    """标记异常，便于断言「抛的是原始异常」而非别的。"""


def _坏parse(self, source, filename=None, extra_definitions=None):
    raise _模拟解析异常("模拟解析器状态异常")


@pytest.fixture
def 制造parse异常(monkeypatch):
    """monkeypatch LightParser.parse 抛异常，制造 _module_has_imports 内部 except 路径。"""
    monkeypatch.setattr(_compiler.LightParser, 'parse', _坏parse)


class Test秒挂快速失败路径_封死:

    def test_O1_含导入_parse异常_必须抛原始异常(self, 制造parse异常):
        """fail-closed：源码含导入却被判 False 会秒挂，必须让原始异常浮出水面。"""
        with pytest.raises(_模拟解析异常):
            _compiler._module_has_imports(_行政区划源码())

    def test_O2_无导入_parse异常_返回False(self, 制造parse异常):
        """源码确无导入时保持 False：走单模块快速路径是合法决策。"""
        assert _compiler._module_has_imports(_无导入源码) is False


class Test文本兜底判定:

    def test_O3_从X导入Y_判定为真(self):
        assert _compiler._text_has_imports('从 中国行政区划 导入 获取行政区划代码') is True

    def test_O4_行内含导入_判定为真(self):
        assert _compiler._text_has_imports('  导入 某模块') is True

    def test_O5_注释含导入_判定为假(self):
        assert _compiler._text_has_imports('# 从 中国行政区划 导入') is False

    def test_O6_无导入_判定为假(self):
        assert _compiler._text_has_imports('段落 主:\n  输出(1)') is False

    def test_O7_空串_判定为假(self):
        assert _compiler._text_has_imports('') is False


class Test正常路径回归:

    def test_O8_含导入_判定为真(self):
        assert _compiler._module_has_imports(_行政区划源码()) is True

    def test_O9_不含导入_判定为假(self):
        assert _compiler._module_has_imports(_无导入源码) is False

    def test_O10_真实编译_多模块路径_产物可跑(self):
        """回归：真实含导入源码走多模块路径仍能编译出可执行产物。"""
        import subprocess
        import tempfile
        src = _行政区划源码()
        with tempfile.TemporaryDirectory(prefix='_r157_') as d:
            sp = os.path.join(d, '主.light')
            with open(sp, 'w', encoding='utf-8') as f:
                f.write(src)
            exe = _compiler.compile_light_typed(sp, os.path.join(d, '产物'),
                                                optimize_level=0)
            assert os.path.exists(exe), '产物未生成'
            r = subprocess.run([exe], capture_output=True, timeout=300, cwd=d)
            assert r.returncode == 0, (
                f"运行 rc={r.returncode}\nstderr={r.stderr.decode('utf-8','replace')}")
            out = r.stdout.decode('utf-8', 'replace').strip().splitlines()
            assert len(out) >= 4, f"输出行数异常: {len(out)}"