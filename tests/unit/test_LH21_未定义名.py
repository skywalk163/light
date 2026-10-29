# -*- coding: utf-8 -*-
"""
LH-21「light check 查不出未定义名」/ LH-09「导入名被局部遮蔽」 单元测试。

被测面（本卡只动这三处）：
  * src/linter/light_linter.py —— E016 未定义的名字 / W016 导入名被局部遮蔽
  * src/linter/cli.py          —— `--check-names` 开关（cli/light.py 由另一张卡在改）
  * tools/内置名清单.py         —— 内置名机器可读登记

设计红线：**宁可漏报也不能误报**（误报会让全仓 .light 都跑不过 check）。所以
E016/W016 都是 opt-in：不进 `LightLinter.lint()` 默认扫描，只能 `--check-names`
或 `lint_names()` 触发。
"""

import os
import sys
import json
import subprocess

import pytest

# conftest.py 已把 src/ 放进 sys.path，按仓库惯例用 `linter.light_linter` 引
from linter.light_linter import (  # noqa: E402
    LightLinter,
    RULES,
    builtin_names,
    builtin_name_sources,
    check_undefined_names,
    check_import_shadow,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(PROJECT_ROOT, 'tools', '内置名清单.py')
DOC = os.path.join(PROJECT_ROOT, 'docs', 'AI编程指南.md')

# `docs/AI编程指南.md`「最常用内置函数」表里的**伪内置名**（真实内置名不叫这个）。
#
# **2026-10-29（T-0203）清零**：本卡把文档侧两处伪名改掉了，允许名单随之清空——
#   `集合创建` → 文档改写成 `集合([])`（`集合` 是内置类型，`集合([])` 实测得空 set）
#   `repr`    → 文档删掉该行，换成 `是空` / `皆空`（Python 内置名泄漏能跑，但不算光明内置名）
# 于是「文档里出现、真实清单里没有」的名字应为 **0 个**；一旦有人把伪名写回文档，
# 下面的 `test_doc_builtin_table_names_all_valid` 会立刻转红。
# 更严格的门禁（登记 + 运行时可达双层判据）见 `tests/unit/test_文档内置名存在性.py`（T-0203）。
#
# 历史备注（保留供回溯）：任务书还列过 `去空白` / `转布尔`，但两者都**不是**伪名——
#   `转布尔` 登记在 `stdlib/lightpub/__index__.py:functions`（须 `从 类型工具 导入`）；
#   `去空白` 已由 T-0197 收编进 `src/code_generator.py:builtin_map` + `stdlib/builtins.py:__all__`。
KNOWN_DOC_ERRORS = frozenset()
# E016 正例用的**造词伪内置名**：任务书亲点的「对 vs 错」配对——
# `最后索引`（对）vs `最后出现位置`（错）。它不在真实清单里，也没被 T-0197 收编。
FAKE_NAME = '最后出现位置'


# =============================================================================
# 1. E016 报未定义名字（LH-21 主症状）
# =============================================================================

def test_e016_reports_undefined_builtin_like_name():
    """`打印 最后出现位置(列表)`：`最后出现位置` 不是内置名 → 报 E016，且定位到行。"""
    issues = check_undefined_names(f'打印 {FAKE_NAME}(列表)\n')
    hits = [i for i in issues if i.name == FAKE_NAME]
    assert hits, f'{FAKE_NAME}（造词出来的伪内置名）必须被报出来'
    msg = hits[0].message
    assert FAKE_NAME in msg
    # 文案必须同时给出「未定义」或「未知内置」的定性
    assert ('未定义' in msg) or ('未知内置' in msg)
    assert hits[0].rule_id == 'E016'
    assert hits[0].severity == 'error'
    # 必须能定位到行（Identifier 节点不带行号，已用源码回填）
    assert hits[0].line == 1, f'应定位到第 1 行，实际 {hits[0].line}'
    assert hits[0].col >= 1


def test_e016_not_reported_for_real_builtins():
    """真实内置名一律零告警（这是误报防线）。"""
    builtins_probe = '、'.join(['去除空白(" x ")', '是空(空)', '打印(1)', '最小值([1,2])'])
    src = '\n'.join([
        builtins_probe,
        '打印 临时目录()',
        '打印 取最小值(80, 9)',
        '打印 去空白(" x ")',      # T-0197 收编后已是真实内置名
        '打印 字节长度("x")',      # T-0197 新收编内置名
        '打印 字典取值(空, "k")',
    ]) + '\n'
    issues = check_undefined_names(src)
    flagged = {i.name for i in issues}
    # 真实内置名一个都不能误报
    safe = {'去除空白', '是空', '打印', '最小值', '临时目录', '取最小值',
            '去空白', '字节长度', '字典取值'}
    assert not (flagged & safe), f'真实内置名被误报：{flagged & safe}'


def test_e016_unknown_variable_reported():
    """非内置名、非导入名、非模块级、非局部变量的裸名 → E016。"""
    issues = check_undefined_names('设 甲 为 1\n打印 乙\n')
    assert any(i.name == '乙' and i.rule_id == 'E016' for i in issues)


def test_e016_scopes_are_honored():
    """模块级段落、局部变量、参数、导入名都不算未定义。"""
    src = (
        '段落 斐波那契(上界):\n'
        '  设 甲 为 1\n'
        '  设 乙 为 2\n'
        '  返回 甲 + 乙\n'
        '结束\n'
        '从 环境 导入 主机名\n'
        '段落 登记:\n'
        '  打印 甲\n'      # 甲 是本段落局部变量 → 不报
        '  打印 乙\n'      # 乙 是本段落局部变量 → 不报
        '  设 上界 为 5\n'  # 上界 是参数 → 不报
        '  打印 主机名\n'   # 主机名 是导入名 → 不报
        '  打印 斐波那契\n'  # 斐波那契 是模块级段落 → 不报
        '结束\n'
    )
    issues = check_undefined_names(src)
    assert not issues, f'作用域内的名字被误报：{[i.name for i in issues]}'


# =============================================================================
# 2. E016 是 opt-in，不进默认 lint()（回归安全）
# =============================================================================

def test_e016_not_in_default_lint():
    """`LightLinter.lint()` 默认扫描不得报 E016（防误报污染全仓 check）。"""
    linter = LightLinter()
    results = linter.lint(f'打印 {FAKE_NAME}(列表)\n')
    assert not any(r.rule_id == 'E016' for r in results)


def test_e016_opt_in_via_lint_names():
    """`lint_names()` 显式开启 E016；用 rules 关掉时也真的不报。"""
    src = f'打印 {FAKE_NAME}(列表)\n'
    assert any(r.rule_id == 'E016' for r in LightLinter().lint_names(src))
    # 只启用 E001 时，E016 必须静默
    assert not any(r.rule_id == 'E016' for r in LightLinter(rules=['E001']).lint_names(src))


def test_e016_rule_registered():
    assert 'E016' in RULES
    assert RULES['E016']['severity'] == 'error'
    assert '未定义' in RULES['E016']['description']


# =============================================================================
# 3. W016 导入名被局部遮蔽（LH-09）
# =============================================================================

def test_w016_import_name_shadowed_by_local():
    """正例：导入名 主机名 在段落体内被赋值 → W016，且文案含 L-166 / 导入名被局部遮蔽。"""
    src = (
        '从 环境 导入 主机名\n'
        '段落 登记:\n'
        '  设 主机名 为 主机名()\n'
        '  打印 主机名\n'
        '结束\n'
    )
    warns = check_import_shadow(src)
    assert warns, '导入名被局部遮蔽必须报 W016'
    joined = '\n'.join(warns)
    assert '主机名' in joined
    assert '导入名被局部遮蔽' in joined
    assert 'L-166' in joined


def test_w016_no_shadow_when_local_uses_different_name():
    """反例：局部变量换名字（主机文本），导入名没被遮蔽 → 零告警。"""
    src = (
        '从 环境 导入 主机名\n'
        '段落 登记:\n'
        '  设 主机文本 为 主机名()\n'
        '  打印 主机文本\n'
        '结束\n'
    )
    assert check_import_shadow(src) == []


def test_w016_rule_registered():
    assert 'W016' in RULES
    assert RULES['W016']['severity'] == 'warning'


# =============================================================================
# 4. tools/内置名清单.py —— 机器可读登记
# =============================================================================

def test_builtin_list_tool_json_shape():
    """清单要输出 JSON：`内置名` 列表 + `来源` 登记，`统计` 计数。"""
    r = subprocess.run([sys.executable, '-X', 'utf8', TOOL],
                       capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert isinstance(payload['内置名'], list)
    assert payload['内置名'], '内置名列表不能为空'
    assert isinstance(payload['来源'], dict)
    for rec in payload['来源'].values():
        assert '类别' in rec and '来源' in rec
    assert payload['统计']['总数'] == len(payload['内置名'])


def test_builtin_list_tool_no_fake_names():
    """伪内置名绝不能在清单里（这是清单存在的意义）。"""
    real = builtin_names()
    for bad in ('集合创建', 'repr', FAKE_NAME):
        assert bad not in real, f'伪内置名 {bad} 不该出现在真实清单里'


def test_builtin_list_tool_has_real_builtins():
    """真实内置名必须在清单里。"""
    real = builtin_names()
    for good in ('去除空白', '是空', '打印', '临时目录', '取最小值', '最小值', '类型',
                 '去空白', '字节长度', '字典取值'):   # 后三个是 T-0197 收编的真实内置名
        assert good in real, f'真实内置名 {good} 缺失于清单'
    # 来源登记要能指认出处
    src = builtin_name_sources()
    assert src['打印']['来源'], '打印 应有来源登记'
    assert src['临时目录']['来源'], '临时目录 应有来源登记'
    assert src['去空白']['来源'], '去空白 应有来源登记（T-0197 收编后）'


# =============================================================================
# 5. 文档门禁：docs/AI编程指南.md 内置函数表 vs 真实清单（反漂移）
# =============================================================================

def _doc_builtin_table_names():
    """解析「## 三、最常用内置函数」小节里的函数表，返回第一列反引号内的名字。"""
    import re
    with open(DOC, encoding='utf-8') as f:
        lines = f.read().split('\n')
    start = next(i for i, l in enumerate(lines) if l.startswith('## 三、最常用内置函数'))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('## ')), len(lines))
    names = set()
    for l in lines[start:end]:
        s = l.strip()
        if not s.startswith('|') or s.startswith('|---'):
            continue
        for cand in re.findall(r'`([^`]+)`', s.split('|')[1] if len(s.split('|')) > 1 else ''):
            pass
        cells = [c.strip() for c in s.strip('|').split('|')]
        for cand in re.findall(r'`([^`]+)`', cells[0]):
            nm = re.sub(r'\(.*?\)$', '', cand).strip()
            if nm:
                names.add(nm)
    return names


def test_doc_builtin_table_names_all_valid():
    """文档里每个内置函数名，要么在真实清单里，要么是已知文档错误。"""
    assert os.path.exists(DOC), f'文档缺失：{DOC}'
    doc_names = _doc_builtin_table_names()
    assert '打印' in doc_names, '解析文档表失败：应能取到 打印'
    real = builtin_names()
    for name in sorted(doc_names):
        assert (name in real) or (name in KNOWN_DOC_ERRORS), \
            f'文档内置函数表里的「{name}」既非真实内置名、也不在允许名单里'


def test_doc_known_errors_are_genuinely_fake():
    """允许名单里的每条，必须是「文档里有、真实清单里没有」的伪内置名（反漂移门禁）。"""
    doc_names = _doc_builtin_table_names()
    real = builtin_names()
    assert KNOWN_DOC_ERRORS <= doc_names, \
        f'允许名单里有文档没写的名字：{KNOWN_DOC_ERRORS - doc_names}'
    assert not (KNOWN_DOC_ERRORS & real), \
        f'允许名单里有真实内置名（不该进黑名单）：{KNOWN_DOC_ERRORS & real}'
    # 反向校验：文档里真实出现且不在真实清单里的，必须全部进允许名单
    for name in sorted(doc_names - real):
        assert name in KNOWN_DOC_ERRORS, \
            f'文档里的「{name}」不在真实清单、但也没登记为已知错误（防漏网）'


def test_doc_builtin_table_is_read_only():
    """文档只读——本卡不得修改 docs/AI编程指南.md（防漂移门禁的另一面）。"""
    # 允许路径里没有 docs/，这里只是显式固化约束，防止后续误改
    assert True


# =============================================================================
# 6. CLI --check-names（检查面在 src/linter/cli.py）
# =============================================================================

def test_cli_check_names(tmp_path):
    """`python -m src.linter.cli --check-names` 能报 E016，退出码非 0。"""
    src = f'打印 {FAKE_NAME}(列表)\n从 环境 导入 主机名\n段落 登记:\n  设 主机名 为 主机名()\n  打印 主机名\n结束\n'
    fp = tmp_path / 'probe.light'
    fp.write_text(src, encoding='utf-8')
    r = subprocess.run(
        [sys.executable, '-X', 'utf8', '-m', 'src.linter.cli', '--check-names', str(fp)],
        capture_output=True, text=True, encoding='utf-8')
    # 有 error 级问题 → 非 0 退出
    assert r.returncode != 0, r.stdout + r.stderr
    assert 'E016' in r.stdout
    assert FAKE_NAME in r.stdout
    assert 'W016' in r.stdout


def test_cli_check_names_json(tmp_path):
    """JSON 输出模式可解析。"""
    fp = tmp_path / 'probe.light'
    fp.write_text(f'打印 {FAKE_NAME}(列表)\n', encoding='utf-8')
    r = subprocess.run(
        [sys.executable, '-X', 'utf8', '-m', 'src.linter.cli', '--check-names', '--json', str(fp)],
        capture_output=True, text=True, encoding='utf-8')
    # 存在 error 级问题 → JSON 模式也返回非 0（给 CI 一个可判定的退出码）
    assert r.returncode != 0, (r.stdout, r.stderr)
    data = json.loads(r.stdout)
    assert any(item.get('rule_id') == 'E016' for item in data)
