# -*- coding: utf-8 -*-
"""R125-C4 · 原生腿终局边界登记测试（只登记，不修）

锁定三件事（登记内容见 docs/原生腿能力边界.md §15「终局边界（R125 登记）」）：
  1. L6「其它错误」终局 10 个模块与就绪度基线 buckets['其它错误'] 完全一致
  2. L7 NO-PY 终局 4 个在 §15 显式文档化
  3. L8 嵌套段落 + nonlocal 边界在文档中登记（解锁前置 = 闭包 env 扩展）

终局含义：这些模块被裁定为原生腿不可编译的**设计边界**，任何"修复"都必须先
推翻本登记（改文档 §15 + 改就绪度基线 + 同步改本测试），不许静默翻面。
"""
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
_DOC = _REPO / 'docs' / '原生腿能力边界.md'
_BASELINE = _REPO / 'tools' / 'ci' / 'llvm_stdlib_readiness_baseline.json'

# L6：就绪度基线「其它错误」桶的终局名单（R125 登记，§15.1）
_L6_TERMINAL = [
    'HTTP服务端', '主控', '代理工具集', '代理循环', '大模型客户端',
    '并发', '流式', '调度核心', '选择器', '重试',
]
# L7：NO-PY 终局 4 个（§15.2）
_L7_TERMINAL = ['SSE', '伪终端', '路径护栏', '进程树']


def test_L6_其它错误终局名单与基线一致():
    baseline = json.loads(_BASELINE.read_text(encoding='utf-8'))
    assert sorted(baseline['buckets']['其它错误']) == sorted(_L6_TERMINAL), (
        'L6 终局名单与就绪度基线「其它错误」桶不一致；若为真实能力变化，'
        '须同步修订 docs/原生腿能力边界.md §15 与本测试，不许静默翻面')


def test_L6_L7_L8_终局边界已文档化():
    doc = _DOC.read_text(encoding='utf-8')
    assert '## 15. 终局边界（R125 登记）' in doc
    for name in _L6_TERMINAL + _L7_TERMINAL:
        assert name in doc, f'终局模块 {name} 未在 docs/原生腿能力边界.md §15 登记'
    assert '嵌套段落' in doc, 'L8 嵌套段落边界未登记'
    assert 'nonlocal' in doc, 'L8 nonlocal 边界未登记'
    assert '闭包 env' in doc, 'L8 解锁前置（闭包 env 扩展）未登记'


def test_L7_魔数终局豁免与pure_light_hook一致():
    """§15.2 里 3 个含魔数但不在首两行的模块，须与 test_pure_light_hook 的
    _KNOWN_MAGIC_FINAL 终局豁免名单严格一致（SSE 不含该豁免，因其魔数已居首行）。"""
    hook = (_REPO / 'tests' / 'test_pure_light_hook.py').read_text(encoding='utf-8')
    lines = hook.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith('_KNOWN_MAGIC_FINAL'):
            start = i
            break
    assert start is not None, 'test_pure_light_hook.py 缺少 _KNOWN_MAGIC_FINAL 名单'
    # 名单可能多行：从起始行收集到闭括号为止
    collected = []
    for line in lines[start:]:
        collected.append(line)
        if '}' in line:
            break
    block = '\n'.join(collected)
    for name in ('伪终端', '路径护栏', '进程树'):
        assert name in block, f'_KNOWN_MAGIC_FINAL 缺终局豁免 {name}'
    for name in ('SSE',):
        assert name not in block, f'{name} 不应出现在 _KNOWN_MAGIC_FINAL（其魔数已居首两行）'
