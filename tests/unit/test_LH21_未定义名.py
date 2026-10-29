# -*- coding: utf-8 -*-
"""LH-21 / LH-09 定向测试：静态名检查 + 导入名被局部遮蔽告警。

覆盖任务卡 T-0199 的六条验收：
  1. `打印 临时目录()` → `check` 报未定义/未知内置（E002，含「临时目录」）；
  2. `设 甲 为 1` + `打印 乙` → 报未定义（局部变量也查）；
  3. **不误报**（最重要）：正常程序 设/打印、从 X 导入 + 调用、段落定义在前调用在后 → 全过；
  4. `tools/内置名清单.py` JSON 含 打印/去除空白/是空，且**不含** 去空白；
  5. 门禁：`docs/AI编程指南.md`「最常用内置函数」表里的名字逐个查存在性（只读文档）；
  6. LH-09：`从 环境 导入 主机名` + 段落内 `设 主机名 为 主机名()` → L-166/「导入名被局部遮蔽」；
     而 `设 主机文本 为 主机名()`（正常写法）**不告警**。
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path

import pytest

# ── 路径设置 ──────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SRC = os.path.join(str(_PROJECT_ROOT), 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from linter.light_linter import LightLinter  # noqa: E402


# =============================================================================
# 辅助
# =============================================================================

def _lint(source: str):
    """用 linter 跑一遍，返回 LintResult 列表。"""
    linter = LightLinter()
    return linter.lint(source)


def _errors_of(results, rule_id: str = 'E002'):
    """取指定规则的结果。"""
    return [r for r in results if r.rule_id == rule_id]


def _has_error_containing(results, text: str):
    """是否存在 E002 错误，文案含 text。"""
    for r in _errors_of(results, 'E002'):
        if text in r.message:
            return True
    return False


def _has_any_error(results):
    """是否存在 E002 错误。"""
    return len(_errors_of(results, 'E002')) > 0


def _has_l166(results):
    """是否存在 L166（导入名被局部遮蔽）告警。"""
    return any(r.rule_id == 'L166' for r in results)


# =============================================================================
# 1. `打印 临时目录()` → 报未定义/未知内置
# =============================================================================

class TestLH21_UndefinedBuiltin:

    def test_临时目录_报未定义(self):
        results = _lint('打印 临时目录()')
        assert _has_any_error(results), f"应报未定义，实际: {[r.message for r in results]}"
        # 文案含「临时目录」与「未定义/未知内置」
        found = [r for r in _errors_of(results, 'E002') if '临时目录' in r.message]
        assert found, f"错误文案应含「临时目录」，实际: {[r.message for r in results]}"
        msg = found[0].message
        assert ('未定义' in msg) or ('未知内置' in msg), f"文案应含「未定义/未知内置」: {msg}"

    def test_临时目录_退出码非零(self):
        """check 退出码非 0：有 E002 错误即视为失败。"""
        results = _lint('打印 临时目录()')
        has_error = _has_any_error(results)
        assert has_error is True, "存在未定义名时 check 应失败"


# =============================================================================
# 2. `设 甲 为 1` + `打印 乙` → 报未定义（局部变量也能查）
# =============================================================================

class TestLH21_LocalUndefined:

    def test_局部未定义_乙(self):
        results = _lint('设 甲 为 1\n打印 乙')
        assert _has_error_containing(results, '乙'), \
            f"应报「乙」未定义，实际: {[r.message for r in results]}"

    def test_局部已定义_不报(self):
        results = _lint('设 甲 为 1\n打印 甲')
        assert not _has_any_error(results), \
            f"「甲」已定义不应报未定义: {[r.message for r in results]}"


# =============================================================================
# 3. 不误报（最重要）
# =============================================================================

class TestLH21_NoFalsePositive:

    def test_设甲打印甲_通过(self):
        results = _lint('设 甲 为 1\n打印 甲')
        assert not _has_any_error(results), \
            f"正常程序误报: {[r.message for r in results]}"

    def test_从数学导入平方根_通过(self):
        results = _lint('从 数学 导入 平方根\n打印 平方根(4)')
        assert not _has_any_error(results), \
            f"导入名不应误报: {[r.message for r in results]}"

    def test_段落定义在前调用在后_通过(self):
        code = ('段落 打招呼():\n'
                '  打印 1\n'
                '打印 打招呼()')
        results = _lint(code)
        assert not _has_any_error(results), \
            f"段落定义在前调用在后不应误报: {[r.message for r in results]}"


# =============================================================================
# 4. tools/内置名清单.py 的 JSON
# =============================================================================

class TestLH21_BuiltinListJson:

    @staticmethod
    def _load_json():
        """运行 tools/内置名清单.py，返回解析后的 dict。"""
        script = str(_PROJECT_ROOT / 'tools' / '内置名清单.py')
        proc = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True, timeout=120, cwd=str(_PROJECT_ROOT),
        )
        assert proc.returncode == 0, f"工具退出码非0: {proc.stderr}"
        return json.loads(proc.stdout)

    def test_json含关键内置名(self):
        data = self._load_json()
        names = set(data.get('内置名', []))
        assert '打印' in names, "应含 打印"
        assert '去除空白' in names, "应含 去除空白"
        assert '是空' in names, "应含 是空"

    def test_json不含去空白(self):
        data = self._load_json()
        names = set(data.get('内置名', []))
        assert '去空白' not in names, "去空白 是不存在的错名，不应出现在真实清单里"

    def test_json结构(self):
        data = self._load_json()
        assert isinstance(data.get('内置名'), list), "内置名 应为列表"
        assert isinstance(data.get('来源'), dict), "来源 应为字典"
        for n in data.get('内置名', []):
            assert n in data['来源'], f"来源缺 {n}"


# =============================================================================
# 5. 门禁：docs/AI编程指南.md「最常用内置函数」表逐个查存在性（只读文档）
# =============================================================================

class TestLH21_DocGate:

    # 文档里「常见但不存在」的错名（真实清单里没有，属文档自身缺陷）。
    # 任务卡明令「只读文档，不改文档」，故这些名字作为已知偏差单独放行，
    # 门禁仍会揪出**新增**的未知名字。真实名见右侧备注。
    _KNOWN_DOC_MISMATCH = {
        '去空白': '真实名为 去除空白（LH-21 症状：去除空白 对 / 去空白 错）',
    }

    @staticmethod
    def _doc_builtin_names():
        """从文档「最常用内置函数」表抽取函数名（第一个反引号列的内容）。"""
        doc = (_PROJECT_ROOT / 'docs' / 'AI编程指南.md').read_text(encoding='utf-8')
        lines = doc.splitlines()
        names = []
        in_section = False
        for line in lines:
            if line.startswith('## 三、最常用内置函数'):
                in_section = True
                continue
            if in_section and line.startswith('## 四、'):
                break
            if not in_section:
                continue
            # 表格行：| `名(...)` | 说明 | 示例 |
            m = re.match(r'^\|\s*`([^`]+)`\s*\|', line)
            if not m:
                continue
            raw = m.group(1).strip()
            # 去掉括号参数，取函数名；形如 打印(...) → 打印
            fn = re.sub(r'\(.*\)$', '', raw).strip()
            if fn:
                names.append(fn)
        return names

    def test_文档内置名逐个存在(self):
        names = self._doc_builtin_names()
        assert names, "文档内置函数表为空，无法对拍"
        from linter.builtins import get_builtin_names
        real = set(get_builtin_names())
        missing = [n for n in names if n not in real]
        unknown = [n for n in missing if n not in self._KNOWN_DOC_MISMATCH]
        assert not unknown, \
            f"文档内置函数表存在真实清单里没有的名字（未在已知偏差内）: {unknown}"


# =============================================================================
# 6. LH-09：导入名被局部遮蔽 → L-166；正常写法不告警
# =============================================================================

class TestLH09_ImportedNameShadow:

    def test_导入名被局部遮蔽_告警(self):
        code = ('从 环境 导入 主机名\n'
                '段落 登记():\n'
                '  设 主机名 为 主机名()')
        results = _lint(code)
        assert _has_l166(results), \
            f"应报 L-166 导入名被局部遮蔽，实际: {[r.rule_id + ':' + r.message for r in results]}"
        # 文案点明「导入名被局部遮蔽」
        msg = next(r.message for r in results if r.rule_id == 'L166')
        assert '导入名被局部遮蔽' in msg, f"文案应点明「导入名被局部遮蔽」: {msg}"

    def test_正常写法不告警(self):
        """`设 主机文本 为 主机名()`：局部名与导入名不同 → 不告警。"""
        code = ('从 环境 导入 主机名\n'
                '段落 登记():\n'
                '  设 主机文本 为 主机名()')
        results = _lint(code)
        assert not _has_l166(results), \
            f"正常写法不应报 L-166: {[r.message for r in results if r.rule_id == 'L166']}"

    def test_无导入不告警(self):
        """模块级变量被遮蔽仍走 W012（既有行为），且不误发 L166。"""
        code = ('设 主机名 为 空\n'
                '段落 登记():\n'
                '  设 主机名 为 主机名()')
        results = _lint(code)
        # 这里是模块级变量遮蔽（W012），不是导入名遮蔽（L166）
        assert not _has_l166(results), \
            f"模块级变量遮蔽不应报 L166: {[r.message for r in results if r.rule_id == 'L166']}"


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
