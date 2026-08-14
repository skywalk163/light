# -*- coding: utf-8 -*-
"""
段言（Duan）编程语言 - VS Code 扩展补全提供器单元测试

针对 vscode-extension/extension.js 中 DuanCompletionProvider 的关键字补全
进行静态结构验证（Node 环境不可用时以源码分析保证回归质量）：
- 新增高/中/低优先级关键字（共 28 个）是否全部注册
- 原有关键字是否保留、总数是否稳定
- 每个关键字是否都有悬浮提示文档与说明
- 关键字标签与悬浮提示键无重复
- insertText 代码片段占位符语法合法
- 补全类别（Keyword/Function/Operator）注册正确
- 移除字符串/注释后代码分隔符平衡
"""

import os
import re

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTENSION_JS = os.path.join(PROJECT_ROOT, 'vscode-extension', 'extension.js')

# 新增高优先级关键字（上下文管理器/数据类型/枚举/FFI/范围/pass/嵌入/管道/装饰器）
HIGH_PRIORITY = ['使用', '数据', '枚举', '外部', '至', '到', '步', 'pass', '嵌入', '并', '标注']
# 新增中优先级关键字（错误类型/Trait/类型别名/推迟/并行/类型检查开关）
MEDIUM_PRIORITY = ['错误', 'trait', '类型别名', '推迟', '并行', '开启类型检查', '关闭类型检查']
# 新增低优先级 FFI 指针/内存操作关键字
LOW_PRIORITY_FFI = ['取地址', '解引用', '指针偏移', '设置指针值', '分配内存', '释放内存',
                    '创建数组', '设置数组', '获取FFI错误', '获取系统错误码']
NEW_KEYWORDS = HIGH_PRIORITY + MEDIUM_PRIORITY + LOW_PRIORITY_FFI

# 新增关键字中刻意不提供代码片段模板的（纯关键字/无参语句）
NO_SNIPPET = {'pass', '开启类型检查', '关闭类型检查', '获取FFI错误', '获取系统错误码'}

# 补全提供器原有的 34 个关键字（回归保护）
ORIGINAL_KEYWORDS = [
    '设', '为', '如果', '否则', '否则如果', '遍历', '当', '段落', '函数', '返回',
    '类', '继承', '属性', '构造', '己', '父', '新建', '导入', '导出', '从',
    '真', '假', '空', '打印', '尝试', '捕获', '抛出', '跳出', '跳过', '异步',
    '等待', '接口', '实现', '匹配',
]
EXPECTED_KEYWORD_TOTAL = len(ORIGINAL_KEYWORDS) + len(NEW_KEYWORDS)  # 34 + 28 = 62


@pytest.fixture(scope='module')
def source():
    """读取扩展源码"""
    assert os.path.exists(EXTENSION_JS), f"扩展文件不存在: {EXTENSION_JS}"
    with open(EXTENSION_JS, encoding='utf-8') as f:
        return f.read()


def _keywords_block(source):
    """提取 keywords 数组文本块"""
    m = re.search(r"const keywords = \[(.*?)\];", source, re.S)
    assert m, "未找到 keywords 数组定义"
    return m.group(1)


def _keyword_entries(source):
    """解析 keywords 数组中每个条目的 (label, detail, insertText)"""
    block = _keywords_block(source)
    entries = []
    for m in re.finditer(r"\{ label: '([^']+)', detail: '([^']*)'(?:, insertText: '([^']*)')?\s*\}",
                         block):
        entries.append((m.group(1), m.group(2), m.group(3) or ''))
    return entries


def _hover_keys(source):
    """提取 hoverDocs 对象的所有键"""
    m = re.search(r"const hoverDocs = \{(.*?)\};", source, re.S)
    assert m, "未找到 hoverDocs 定义"
    return re.findall(r"'([^']+)':\s*'###", m.group(1))


def _strip_strings_and_comments(src):
    """移除字符串字面量、模板串与注释，仅用于分隔符平衡统计"""
    s = re.sub(r"'(?:[^'\\]|\\.)*'", "''", src)
    s = re.sub(r'"(?:[^"\\]|\\.)*"', '""', s)
    s = re.sub(r'`(?:[^`\\]|\\.)*`', '``', s)
    s = re.sub(r'//[^\n]*', '', s)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    return s


# =============================================================================
# 新关键字注册覆盖
# =============================================================================

def test_高优先级关键字全部注册(source):
    labels = [label for label, _, _ in _keyword_entries(source)]
    missing = [kw for kw in HIGH_PRIORITY if kw not in labels]
    assert not missing, f"高优先级关键字未注册: {missing}"


def test_中优先级关键字全部注册(source):
    labels = [label for label, _, _ in _keyword_entries(source)]
    missing = [kw for kw in MEDIUM_PRIORITY if kw not in labels]
    assert not missing, f"中优先级关键字未注册: {missing}"


def test_低优先级FFI关键字全部注册(source):
    labels = [label for label, _, _ in _keyword_entries(source)]
    missing = [kw for kw in LOW_PRIORITY_FFI if kw not in labels]
    assert not missing, f"低优先级 FFI 关键字未注册: {missing}"


def test_关键字总数与新增数量(source):
    """关键字总数 = 原有 34 + 新增 28 = 62"""
    labels = [label for label, _, _ in _keyword_entries(source)]
    assert len(labels) == EXPECTED_KEYWORD_TOTAL, \
        f"关键字总数 {len(labels)} != 期望 {EXPECTED_KEYWORD_TOTAL}"
    added = set(labels) - set(ORIGINAL_KEYWORDS)
    assert len(added) == len(NEW_KEYWORDS), \
        f"新增关键字数量 {len(added)} != 期望 {len(NEW_KEYWORDS)}"


def test_原有关键字保留(source):
    labels = set(label for label, _, _ in _keyword_entries(source))
    missing = [kw for kw in ORIGINAL_KEYWORDS if kw not in labels]
    assert not missing, f"原有关键字被移除: {missing}"


# =============================================================================
# 标签与说明完整性
# =============================================================================

def test_关键字标签无重复(source):
    labels = [label for label, _, _ in _keyword_entries(source)]
    dup = [kw for kw in set(labels) if labels.count(kw) > 1]
    assert not dup, f"存在重复关键字标签: {dup}"


def test_所有关键字都有说明(source):
    empty = [label for label, detail, _ in _keyword_entries(source) if not detail]
    assert not empty, f"缺少 detail 说明的关键字: {empty}"


def test_新增关键字都有悬浮提示文档(source):
    hover = set(_hover_keys(source))
    missing = [kw for kw in NEW_KEYWORDS if kw not in hover]
    assert not missing, f"缺少悬浮提示文档的新增关键字: {missing}"


def test_悬浮提示键无重复(source):
    keys = _hover_keys(source)
    dup = [k for k in set(keys) if keys.count(k) > 1]
    assert not dup, f"悬浮提示键重复: {dup}"


# =============================================================================
# 代码片段模板（insertText）
# =============================================================================

def test_新增关键字都带代码片段模板(source):
    """除刻意无模板的关键字外，新增关键字都应提供 insertText"""
    by_label = {label: (detail, snippet) for label, detail, snippet in _keyword_entries(source)}
    expected = set(NEW_KEYWORDS) - NO_SNIPPET
    missing = [kw for kw in expected if not by_label.get(kw, ('', ''))[1]]
    assert not missing, f"缺少代码片段模板的新增关键字: {missing}"


def test_片段占位符语法合法(source):
    """所有 insertText 中的 $ 必须组成合法占位符 ${N:...} 且编号从 1 开始"""
    bad = []
    for label, _, snippet in _keyword_entries(source):
        if not snippet:
            continue
        for m in re.finditer(r'\$', snippet):
            rest = snippet[m.start():]
            if not re.match(r'\$\{\d+[^}]*\}', rest):
                bad.append((label, rest[:20]))
        for num in re.findall(r'\$\{(\d+):', snippet):
            if int(num) < 1:
                bad.append((label, f'占位符编号 < 1: {num}'))
    assert not bad, f"非法片段占位符: {bad}"


def test_片段占位符编号从1开始(source):
    """每个片段第一个占位符编号必须为 1"""
    bad = []
    for label, _, snippet in _keyword_entries(source):
        if not snippet:
            continue
        nums = re.findall(r'\$\{(\d+):', snippet)
        if nums and int(nums[0]) != 1:
            bad.append((label, nums[0]))
    assert not bad, f"片段占位符未从 1 开始: {bad}"


# =============================================================================
# 补全类别注册
# =============================================================================

def test_关键字使用Keyword类别(source):
    assert re.search(r'new vscode\.CompletionItem\(kw\.label, vscode\.CompletionItemKind\.Keyword\)',
                     source), "关键字未注册为 CompletionItemKind.Keyword"


def test_内置函数使用Function类别(source):
    assert re.search(r'new vscode\.CompletionItem\(fn\.label, vscode\.CompletionItemKind\.Function\)',
                     source), "内置函数未注册为 CompletionItemKind.Function"


def test_运算符使用Operator类别(source):
    assert re.search(r'new vscode\.CompletionItem\(op\.label, vscode\.CompletionItemKind\.Operator\)',
                     source), "运算符未注册为 CompletionItemKind.Operator"


# =============================================================================
# 代码结构完整性
# =============================================================================

@pytest.mark.parametrize('open_ch,close_ch', [('(', ')'), ('[', ']'), ('{', '}')])
def test_分隔符平衡(source, open_ch, close_ch):
    """移除字符串/注释后，圆括号/方括号/花括号必须配对平衡"""
    code = _strip_strings_and_comments(source)
    assert code.count(open_ch) == code.count(close_ch), \
        f"分隔符不平衡: {open_ch} {code.count(open_ch)} 处 vs {close_ch} {code.count(close_ch)} 处"
