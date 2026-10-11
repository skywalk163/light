# -*- coding: utf-8 -*-
"""R140-B 线：LSP 完整化真实行为断言

覆盖任务书 B1–B4 判绿口径：
- B1 格式化（含 rangeFormatting）对中文关键字/缩进/注释/空行/多行嵌套全绿，且幂等
- B2 重命名支持中文标识符、跨文档引用、冲突/非法名报错
- B3 semanticTokens 覆盖 legend 中的 keyword/function/variable/class/parameter/
     property/string/number/comment 等类别，且 delta 编码可被客户端严格还原
- B4 documentHighlight 与 references 对中文标识符定位准确（区分同名字符串）

断言均为真实行为断言（比较实际输出内容），不使用「只要返回列表即可」式的下界断言。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from lsp.light_lsp import LightLanguageServer   # noqa: E402

URI_A = 'file:///r140a.light'
URI_B = 'file:///r140b.light'


def make_server(docs=None):
    """建一个装好文档的服务器实例；docs = {uri: text}"""
    server = LightLanguageServer()
    for uri, text in (docs or {}).items():
        server._handle_did_open({'textDocument': {'uri': uri, 'text': text}})
    return server


def apply_edits(text, edits):
    """按 LSP range 语义应用 edits（假定互不重叠，倒序应用）"""
    if not edits:
        return text
    lines = text.split('\n')
    norm = []
    for e in edits:
        r = e['range']
        norm.append((r['start']['line'], r['start']['character'],
                     r['end']['line'], r['end']['character'], e['newText']))
    norm.sort(reverse=True)
    for sl, sc, el, ec, new_text in norm:
        head = lines[sl][:sc]
        tail = lines[el][ec:]
        lines[sl:el + 1] = (head + new_text + tail).split('\n')
    return '\n'.join(lines)


def format_once(text, tab_size=4):
    server = make_server({URI_A: text})
    edits = server._handle_formatting({
        'textDocument': {'uri': URI_A},
        'options': {'tabSize': tab_size, 'insertSpaces': True}
    })
    return apply_edits(text, edits)


def decode_semantic_tokens(data, lines):
    """按 LSP 规范严格还原 delta 编码，返回 [(line, col, length, type, 文本)]"""
    decoded = []
    prev_line = 0
    prev_col = 0
    for i in range(0, len(data), 5):
        delta_line, delta_col, length, token_type, modifiers = data[i:i + 5]
        line = prev_line + delta_line
        col = delta_col if delta_line != 0 else prev_col + delta_col
        prev_line, prev_col = line, col
        text = lines[line][col:col + length] if 0 <= line < len(lines) else None
        decoded.append((line, col, length, token_type, text))
    return decoded


# ---------------------------------------------------------------------------
# B1 格式化
# ---------------------------------------------------------------------------

FORMAT_SOURCES = [
    '如果 甲 大于 10 那么：\n返回 甲。\n结束。\n',
    '如果 甲 大于 1 那么：\n返回 1。\n否则：\n返回 2。\n结束。\n',
    '如果 甲 大于 1 那么：\n如果 乙 大于 2 那么：\n返回 1。\n结束。\n结束。\n',
    '段落 测试段(甲, 乙)：\n返回 甲 加 乙。\n结束。\n',
    '类 测试类：\n属性 名称。\n结束。\n',
    '遍历 项 于 列表：\n打印输出(项)。\n结束。\n',
    '当 甲 大于 0：\n设 甲 为 甲 减 1。\n结束。\n',
    '尝试：\n设 甲 为 1。\n捕获 错误：\n打印输出(错误)。\n最终：\n打印输出(1)。\n结束。\n',
    '匹配 甲：\n情况 1：\n打印输出(1)。\n情况 _：\n打印输出(0)。\n结束。\n',
    '# 顶部注释\n设 甲 为 1。\n\n# 第二段注释\n如果 甲 大于 0 那么：\n打印输出(甲)。\n结束。\n',
    '若 甲 大于 1：\n返 1。\n否：\n返 2。\n终。\n',
    '类 容器：\n属性 项。\n段落 取()：\n返回 己.项。\n结束。\n结束。\n',
    '遍历 行 于 行表：\n如果 行 为空 那么：\n跳过。\n结束。\n打印输出(行)。\n结束。\n',
    '设 甲 为 1 加 2 乘 3。\n',
    '段落 主()：\n遍历 甲 于 序列(10)：\n如果 甲 大于 5：\n打印输出(甲)。\n结束。\n结束。\n结束。\n',
    '当 真：\n尝试：\n跳出。\n捕获 错误：\n结束。\n结束。\n',
    '如果 甲 那么：\n设 乙 为 1。\n否则若 丙 那么：\n设 乙 为 2。\n否则：\n设 乙 为 3。\n结束。\n',
    '段落 计算(甲, 乙)：\n返回 甲 加 乙。\n结束。\n设 结果 为 计算(1, 2)。\n',
    '如果 甲 大于 1 那么：\r\n返回 甲。\r\n结束。\r\n',
    '示例标记：\n  # 缩进注释\n  设 甲 为 1。\n  # 末尾注释\n',
]


@pytest.mark.parametrize('src', FORMAT_SOURCES)
def test_formatting_is_idempotent(src):
    """B1：format(format(x)) == format(x)"""
    once = format_once(src)
    twice = format_once(once)
    assert once == twice


@pytest.mark.parametrize('src', FORMAT_SOURCES)
def test_formatting_preserves_code_content(src):
    """B1：格式化不得增删任何非空白字符"""
    out = format_once(src)
    assert ''.join(out.split()) == ''.join(src.split())


def test_formatting_indents_block_body_one_level():
    """B1：块体 4 空格、块头 0 空格"""
    out = format_once('如果 甲 大于 10 那么：\n返回 甲。\n结束。\n')
    lines = out.split('\n')
    assert lines[0] == '如果 甲 大于 10 那么：'
    assert lines[1] == '    返回 甲。'


def test_formatting_dedents_block_closers():
    """B1：结束/否则/捕获/最终/情况 不额外缩进（对齐 light 语料惯例）"""
    out = format_once('尝试：\n设 甲 为 1。\n捕获 错误：\n打印输出(错误)。\n最终：\n打印输出(1)。\n结束。\n')
    lines = out.split('\n')
    assert lines[0] == '尝试：'
    assert lines[1] == '    设 甲 为 1。'
    assert lines[2] == '捕获 错误：'
    assert lines[3] == '    打印输出(错误)。'
    assert lines[4] == '最终：'
    assert lines[5] == '    打印输出(1)。'
    assert lines[6] == '结束。'


def test_formatting_nested_match_case_relative_indent():
    """B1：情况 相对 匹配 缩进一级，case 体再缩进一级"""
    out = format_once('匹配 甲：\n情况 1：\n打印输出(1)。\n情况 _：\n打印输出(0)。\n结束。\n')
    lines = out.split('\n')
    assert lines[0] == '匹配 甲：'
    assert lines[1] == '    情况 1：'
    assert lines[2] == '        打印输出(1)。'
    assert lines[3] == '    情况 _：'
    assert lines[5] == '结束。'


def test_formatting_class_body_method_indent_not_lost():
    """B1：类体内方法体保留缩进（原 AST 路径会整块丢失）"""
    out = format_once('类 容器：\n属性 项。\n段落 取()：\n返回 己.项。\n结束。\n结束。\n')
    lines = out.split('\n')
    assert lines[0] == '类 容器：'
    assert lines[1] == '    属性 项。'
    assert lines[2] == '    段落 取()：'
    assert lines[3] == '        返回 己.项。'
    assert lines[4] == '    结束。'
    assert lines[5] == '结束。'


def test_formatting_respects_extended_tab_size():
    """B1：tabSize 生效"""
    out = format_once('如果 甲 大于 1 那么：\n返回 甲。\n结束。\n', tab_size=2)
    assert out.split('\n')[1] == '  返回 甲。'


def test_range_formatting_edit_round_trips_to_same_document():
    """B1：rangeFormatting 的 newText 行数必须与 range 覆盖行数一致（否则客户端应用后文档损坏）"""
    src = '如果 甲 大于 1 那么：\n返回 甲。\n结束。\n设 尾部 为 1。\n'
    server = make_server({URI_A: src})
    edits = server._handle_range_formatting({
        'textDocument': {'uri': URI_A},
        'range': {'start': {'line': 0, 'character': 0},
                  'end': {'line': 2, 'character': 3}},
        'options': {'tabSize': 4, 'insertSpaces': True}
    })
    for e in edits:
        covered = e['range']['end']['line'] - e['range']['start']['line'] + 1
        assert len(e['newText'].split('\n')) == covered
    assert apply_edits(src, edits) == format_once(src)


def test_formatting_unknown_document_returns_empty():
    """B1：未知文档返回空编辑而非抛异常"""
    server = LightLanguageServer()
    assert server._handle_formatting({
        'textDocument': {'uri': 'file:///不存在.light'},
        'options': {}
    }) == []


# ---------------------------------------------------------------------------
# B2 重命名
# ---------------------------------------------------------------------------

def test_rename_chinese_identifier_all_occurrences():
    """B2：中文标识符定义与引用一并重命名"""
    src = '设 变量1 为 42。\n设 x 为 变量1。\n打印输出(变量1)。\n'
    server = make_server({URI_A: src})
    result = server._handle_rename({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 3},
        'newName': '变量2'
    })
    edits = result['changes'][URI_A]
    assert len(edits) == 3
    assert {e['newText'] for e in edits} == {'变量2'}
    new_text = apply_edits(src, edits)
    assert new_text == '设 变量2 为 42。\n设 x 为 变量2。\n打印输出(变量2)。\n'
    assert '变量1' not in new_text


def test_rename_does_not_touch_string_literal():
    """B2：字符串字面量中的同名词不得被改写"""
    src = '设 变量1 为 "变量1"。\n'
    server = make_server({URI_A: src})
    result = server._handle_rename({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 3},
        'newName': '变量2'
    })
    edits = result['changes'][URI_A]
    assert len(edits) == 1
    new_text = apply_edits(src, edits)
    assert new_text == '设 变量2 为 "变量1"。\n'


def test_rename_does_not_touch_comment():
    """B2：注释中的同名词不得被改写"""
    src = '# 变量1 是注释\n设 变量1 为 1。\n'
    server = make_server({URI_A: src})
    result = server._handle_rename({
        'textDocument': {'uri': URI_A},
        'position': {'line': 1, 'character': 3},
        'newName': '变量2'
    })
    new_text = apply_edits(src, result['changes'][URI_A])
    assert new_text == '# 变量1 是注释\n设 变量2 为 1。\n'


def test_rename_no_prefix_collision():
    """B2：变量1 重命名不得波及 变量10"""
    src = '设 变量1 为 42。\n设 变量10 为 7。\n'
    server = make_server({URI_A: src})
    result = server._handle_rename({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 3},
        'newName': '变量2'
    })
    edits = result['changes'][URI_A]
    assert len(edits) == 1
    new_text = apply_edits(src, edits)
    assert new_text == '设 变量2 为 42。\n设 变量10 为 7。\n'


def test_rename_two_char_chinese_name():
    """B2：2 字中文标识符（撞名关键字书写长度）定位正确"""
    src = '设 字段 为 1。\n打印输出(字段)。\n'
    server = make_server({URI_A: src})
    result = server._handle_rename({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 3},
        'newName': '编号'
    })
    edits = result['changes'][URI_A]
    assert len(edits) == 2
    assert apply_edits(src, edits) == '设 编号 为 1。\n打印输出(编号)。\n'


def test_rename_across_documents():
    """B2：跨文档重命名"""
    server = make_server({
        URI_A: '设 共享名 为 1。\n',
        URI_B: '打印输出(共享名)。\n',
    })
    result = server._handle_rename({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 3},
        'newName': '新名'
    })
    assert set(result['changes']) == {URI_A, URI_B}
    assert len(result['changes'][URI_A]) == 1
    assert len(result['changes'][URI_B]) == 1


def test_rename_conflict_returns_error():
    """B2：重命名为已存在的名字要报错，而不是静默产生重名"""
    src = '设 甲 为 1。\n设 乙 为 2。\n'
    server = make_server({URI_A: src})
    result = server._handle_rename({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 2},
        'newName': '乙'
    })
    assert 'error' in result
    assert result['error']['code'] == -32602
    assert 'changes' not in result


def test_rename_invalid_identifier_returns_error():
    """B2：非法标识符（数字开头 / 含空格）要报错"""
    server = make_server({URI_A: '设 甲 为 1。\n'})
    for bad in ('1不合法', '含 空格', 'a-b'):
        result = server._handle_rename({
            'textDocument': {'uri': URI_A},
            'position': {'line': 0, 'character': 2},
            'newName': bad
        })
        assert 'error' in result, bad
        assert result['error']['code'] == -32602


def test_rename_empty_new_name_returns_none():
    """B2：空新名不产生编辑"""
    server = make_server({URI_A: '设 甲 为 1。\n'})
    assert server._handle_rename({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 2},
        'newName': '   '
    }) is None


def test_rename_workspace_edit_ranges_are_exact():
    """B2：workspaceEdit 的 range 精确覆盖被重命名的词"""
    src = '设 值甲 为 1。\n设 值甲乙 为 2。\n'
    server = make_server({URI_A: src})
    result = server._handle_rename({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 3},
        'newName': '值丙'
    })
    edits = result['changes'][URI_A]
    assert len(edits) == 1
    rng = edits[0]['range']
    assert rng['start'] == {'line': 0, 'character': 2}
    assert rng['end'] == {'line': 0, 'character': 4}   # 只覆盖「值甲」两字，不碰「值甲乙」


# ---------------------------------------------------------------------------
# B3 语义高亮
# ---------------------------------------------------------------------------

SEMANTIC_SRC = '''# 注释行
类 形状：
    属性 名称。
    构造(参数名)：
        设 己.名称 为 参数名。
    结束。
结束。

段落 求面积(半径)：
    设 结果 为 3.14 乘 半径 乘 半径。
    返回 结果。
结束。

设 变量甲 为 "文本"。
设 数字乙 为 42。
'''


def test_semantic_tokens_legend_has_no_duplicate_key_override():
    """B3：capabilities 的 legend 只声明一处，tokenTypes 数量与实现下标表一致"""
    server = LightLanguageServer()
    legend = server.capabilities['semanticTokensProvider']['legend']
    assert legend['tokenTypes'] == [
        'namespace', 'type', 'class', 'enum', 'interface', 'function', 'variable',
        'property', 'parameter', 'keyword', 'method', 'string', 'number', 'operator', 'comment',
    ]
    assert server.semantic_token_types['variable'] == 6
    assert server.semantic_token_types['class'] == 2
    assert server.semantic_token_types['comment'] == 14


def test_semantic_tokens_covers_nine_categories():
    """B3：keyword/function/variable/class/parameter/property/string/number/comment 全覆盖"""
    server = make_server({URI_A: SEMANTIC_SRC})
    data = server._handle_semantic_tokens_full({'textDocument': {'uri': URI_A}})['data']
    legend = server.capabilities['semanticTokensProvider']['legend']['tokenTypes']
    seen = {legend[data[i]] for i in range(3, len(data), 5)}
    assert {'keyword', 'function', 'variable', 'class', 'parameter',
            'property', 'string', 'number', 'comment'} <= seen
    assert 'operator' in seen


def test_semantic_tokens_delta_decodes_to_source_text():
    """B3：delta 编码可被客户端严格还原，且还原文本与源码逐条一致"""
    server = make_server({URI_A: SEMANTIC_SRC})
    data = server._handle_semantic_tokens_full({'textDocument': {'uri': URI_A}})['data']
    lines = SEMANTIC_SRC.split('\n')
    decoded = decode_semantic_tokens(data, lines)
    assert decoded, '不应为空'
    for (line, col, length, _tt, text) in decoded:
        assert 0 <= line < len(lines), f'token 行越界: {line}'
        assert 0 <= col < len(lines[line]), f'token 列越界: {col}'
        assert lines[line][col:col + length] == text
    # 首 token 必须是绝对定位（deltaLine=0, deltaStart=0）
    assert data[0] == 0 and data[1] == 0


def test_semantic_tokens_classification_is_context_aware():
    """B3：同一标识符按上下文分类（类名 vs 变量；参数 vs 变量）"""
    server = make_server({URI_A: SEMANTIC_SRC})
    data = server._handle_semantic_tokens_full({'textDocument': {'uri': URI_A}})['data']
    legend = server.capabilities['semanticTokensProvider']['legend']['tokenTypes']
    decoded = decode_semantic_tokens(data, SEMANTIC_SRC.split('\n'))
    kinds = {(line, col, text): legend[tt] for (line, col, _l, tt, text) in decoded
             if text is not None}
    assert kinds[(1, 2, '形状')] == 'class'
    assert kinds[(3, 7, '参数名')] == 'parameter'
    assert kinds[(8, 3, '求面积')] == 'function'
    assert kinds[(8, 7, '半径')] == 'parameter'
    assert kinds[(2, 7, '名称')] == 'property'
    assert kinds[(13, 8, '"文本"')] == 'string'
    assert kinds[(14, 8, '42')] == 'number'


def test_semantic_tokens_both_entrypoints_agree():
    """B3：两个入口（full 与兼容入口）行为一致，且不再恒为空"""
    server = make_server({URI_A: SEMANTIC_SRC})
    full = server._handle_semantic_tokens_full({'textDocument': {'uri': URI_A}})
    compat = server._handle_semantic_tokens({'textDocument': {'uri': URI_A}})
    assert full['data'] == compat['data']
    # 兼容入口历史上因引用不存在的 TT.COMMENT 恒返回空，这里断言确实产出了 token
    assert len(compat['data']) == 265
    # 5 元组不变量
    assert len(compat['data']) % 5 == 0


def test_semantic_tokens_comments_and_strings_not_tokenized_inside():
    """B3：字符串内部的 # 不当作注释起点"""
    src = '设 甲 为 "含#号文本"。\n'
    server = make_server({URI_A: src})
    data = server._handle_semantic_tokens_full({'textDocument': {'uri': URI_A}})['data']
    legend = server.capabilities['semanticTokensProvider']['legend']['tokenTypes']
    decoded = decode_semantic_tokens(data, src.split('\n'))
    kinds = [legend[tt] for (_l, _c, _n, tt, _t) in decoded]
    assert 'comment' not in kinds
    assert 'string' in kinds
    # 字符串 token 必须覆盖完整引号段
    strings = [t for (_l, _c, _n, tt, t) in decoded if legend[tt] == 'string']
    assert strings == ['"含#号文本"']


def test_semantic_tokens_handler_is_registered_once():
    """B3：handle_request dispatch 表无重复键覆盖"""
    server = LightLanguageServer()
    import inspect
    src = inspect.getsource(server.handle_request)
    assert src.count("'textDocument/semanticTokens/full'") == 1
    assert src.count("'textDocument/signatureHelp'") == 1


# ---------------------------------------------------------------------------
# B4 documentHighlight / references
# ---------------------------------------------------------------------------

HIGHLIGHT_SRC = '''设 变量1 为 42。
设 x 为 "变量1"。
# 变量1 在注释里
打印输出(变量1)。
'''


def test_document_highlight_skips_strings_and_comments():
    """B4：同名字符串与注释不参与高亮"""
    server = make_server({URI_A: HIGHLIGHT_SRC})
    highlights = server._handle_document_highlight({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 3}
    })
    lines = [h['range']['start']['line'] for h in highlights]
    assert lines == [0, 3]


def test_document_highlight_kinds_read_write():
    """B4：光标处为 Write(3)，其余为 Read(2)"""
    server = make_server({URI_A: HIGHLIGHT_SRC})
    highlights = server._handle_document_highlight({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 3}
    })
    kinds = {h['range']['start']['line']: h['kind'] for h in highlights}
    assert kinds[0] == 3
    assert kinds[3] == 2


def test_references_skips_strings_and_comments():
    """B4：references 只返回代码区出现"""
    server = make_server({URI_A: HIGHLIGHT_SRC})
    refs = server._handle_references({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 3}
    })
    lines = sorted(r['range']['start']['line'] for r in refs)
    assert lines == [0, 3]
    assert {r['uri'] for r in refs} == {URI_A}


def test_references_include_declaration_flag():
    """B4：context.includeDeclaration=False 时剔除定义处"""
    server = make_server({URI_A: HIGHLIGHT_SRC})
    include = server._handle_references({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 3},
        'context': {'includeDeclaration': True}
    })
    exclude = server._handle_references({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 3},
        'context': {'includeDeclaration': False}
    })
    assert len(include) == 2
    assert len(exclude) == 1
    assert exclude[0]['range']['start']['line'] == 3


def test_references_ranges_are_exact_chinese_spans():
    """B4：中文标识符 range 的列跨度精确等于词长"""
    server = make_server({URI_A: HIGHLIGHT_SRC})
    refs = server._handle_references({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 3}
    })
    for r in refs:
        start = r['range']['start']['character']
        end = r['range']['end']['character']
        assert end - start == len('变量1')


def test_highlight_on_string_position_falls_back_to_code():
    """B4：光标落在字符串内时退化为该行代码区最近的词，不返回空且不误报"""
    server = make_server({URI_A: '设 甲 为 "甲"。\n'})
    highlights = server._handle_document_highlight({
        'textDocument': {'uri': URI_A},
        'position': {'line': 0, 'character': 7}   # 字符串内
    })
    lines = [h['range']['start']['line'] for h in highlights]
    # 只剩定义处的代码区出现
    assert lines == [0]


def test_highlight_and_references_unknown_document_return_empty():
    """B4：未知文档返回空列表"""
    server = LightLanguageServer()
    assert server._handle_document_highlight({
        'textDocument': {'uri': 'file:///无.light'},
        'position': {'line': 0, 'character': 0}
    }) == []
    assert server._handle_references({
        'textDocument': {'uri': 'file:///无.light'},
        'position': {'line': 0, 'character': 0}
    }) == []


# ---------------------------------------------------------------------------
# B5 语义诊断不退化（联合 R137 能力）
# ---------------------------------------------------------------------------

def test_r137_semantic_diagnostic_still_clean_on_valid_code():
    """B5：R137 语义诊断对合法代码零假阳性残留"""
    from lsp_diagnostic import run_semantic_diagnostic
    src = '设 甲 为 1。\n设 乙 为 甲 加 1。\n打印输出(乙)。\n'
    assert run_semantic_diagnostic(src, 'ok.light') == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
