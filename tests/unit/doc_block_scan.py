# -*- coding: utf-8 -*-
"""文档代码块扫描器 —— 阶段 3 门禁与基线生成器的共用底座。

单独成模块（而非塞进测试文件）的原因：`test_doc_examples_gate.py` 与
`tools/ci/gen_doc_examples_baseline.py` 必须走**完全同一套**提取 + 分类逻辑，
否则基线里的条目和门禁扫出来的条目对不上，`hash` 一错位，门禁要么假红要么假绿。
共用一份源码是唯一能保证二者同口径的办法。

## 提取口径

- 只认围栏语言标签为 light/光明/duan/段言 的块（与 v7 品牌口径一致，四个都收
  是因为迁移期文档新旧标签混用）。
- 用块内容的 sha1 前 12 位做身份（`hash`），**不用行号**：行号会随文档正文
  增删漂移，内容哈希只在「这段代码本身被改」时才变——正是我们想要的失效条件。
- 缩进按围栏起始缩进整体剥离（markdown 允许缩进围栏）。

## 分类口径（与 test_doc_examples_gate.py 模块文档串一致）

- COMPILER_BUG：抛的不是 Lexer/Parse 错（AttributeError/MemoryError…）。这是
  编译器内部炸了，**永不进基线**，必须单独开单修（口径 5/7：实现缺陷）。
- REPL：`>>>`/`...` 会话记录，天然编不过，属文档体裁问题。
- ESCAPED：正文里 `\"` 转义污染（markdown 表格/行内码里抄来的），非真代码。
- PSEUDO：一个光明关键字都没有——纯伪代码/占位。
- ANNOTATED：真代码里夹了行内箭头注解（`← 推断为 …`）等图示字符。
- ROT：以上都不是，即「像真代码但编不过」——这才是文档腐烂，门禁的真正目标。

前五类都是「本来就不该编译」的噪声，进基线只会稀释信号（口径 10：基线虚高等于
没有基线）。门禁对它们的态度是「允许存在，但不许新增」——靠总数上限而非逐条钉。
"""

import os
import re
import io
import sys
import hashlib

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(ROOT, 'src'), ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DOCS = os.path.join(ROOT, 'docs')
LANG_TAGS = {'light', '光明', 'duan', '段言'}
_FENCE = re.compile(r'^([ \t]*)(`{3,}|~{3,})[ \t]*([^\s`~]*)[ \t]*$')
_DIAGRAM_CHARS = set('←→↓↑↔⇒⇐×√≈≤≥─│┌└├┐┘┬┴┼╱╲○●◆▲▼')
_LIGHT_KW = ('定义', '设 ', '段落', '段 ', '类 ', '如果', '若 ', '打印', '返回',
             '导入', '从 ', '尝试', '捕获', '遍历', '当 ', '接收', '外部', '接口',
             '实现', '异步', '使用', '装饰器', '匹配')

# 这些类别是「本来就不该编译」的噪声，不进逐条基线
NOISE_CATEGORIES = ('REPL', 'ESCAPED', 'PSEUDO', 'ANNOTATED')

# ---------------------------------------------------------------------------
# 敌意块名单：**绝对不能在本进程 parse**，会把机器吃干
#
# 2026-08-20 实测事故：本模块的前身在后台跑，15 分钟吃到 15.5GB 且仍在涨
# （~2GB/分钟，只增不减），必须 Stop-Process 掐掉。单变量 A/B 定位
# （子进程 + 900MB 看门狗，手法已固化为 tools/ci/run_with_memory_cap.py）：
#
#   情况 [头, 尾]：     → PARSE_OK，1.0s，峰值 17MB
#   情况 [头, 尾...]：  → 线性增长 ~40MB/s，913MB 被掐，从未返回
#
# 唯一差异是 `...`。即 `匹配`/`情况` 的列表模式里出现 rest 模式 `...` 时，
# parser 进入不终止的分配循环。这是编译器缺陷（DoS 级：9 行源码即可打爆），
# 与文档对错无关，已单独记为待修单。
#
# 为什么用哈希白名单而不是「加超时」：Windows 上 Python 没有 SIGALRM，
# 进程内无法可靠打断一个正在疯狂分配的纯 Python 循环；等到 MemoryError 抛出时
# 机器已经被拖垮了（实测第一次 classify 跑就是这样侥幸拿到 MemoryError 的）。
# 唯一安全的做法是**根本不喂给它**。
#
# 哈希键的好处：文档一改，哈希就变，这个块会重新进入编译——不会永久豁免。
_HOSTILE_HASHES = {
    # docs/语义密度示例集.md 的 `情况 [头, 尾...]` 递归求和示例
    'e40db4b0a844': '匹配 列表 rest 模式 `...` 触发 parser 无限分配',
}



def iter_blocks(text):
    lines = text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        m = _FENCE.match(lines[i])
        if not m:
            i += 1
            continue
        indent, fence, lang = m.group(1), m.group(2), m.group(3)
        body = []
        i += 1
        while i < n:
            m2 = _FENCE.match(lines[i])
            if m2 and m2.group(2)[0] == fence[0] \
                    and len(m2.group(2)) >= len(fence) and not m2.group(3):
                i += 1
                break
            body.append(lines[i])
            i += 1
        start = i - len(body)
        if lang in LANG_TAGS:
            code = '\n'.join(
                (ln[len(indent):] if ln.startswith(indent) else ln) for ln in body
            )
            yield lang, start, code


def _first_line(code):
    for l in code.splitlines():
        if l.strip():
            return l.strip()
    return ''


def classify(code, exc, msg):
    if exc not in ('LexerError', 'ParseError'):
        return 'COMPILER_BUG'
    stripped = [l.strip() for l in code.splitlines() if l.strip()]
    if any(l.startswith('>>>') or l.startswith('...') for l in stripped):
        return 'REPL'
    if '\\"' in code:
        return 'ESCAPED'
    has_kw = any(k in code for k in _LIGHT_KW)
    if not has_kw:
        return 'PSEUDO'
    if any(c in _DIAGRAM_CHARS for c in code):
        return 'ANNOTATED'
    return 'ROT'


def _compile_once(code):
    """返回 (exc_type_name, msg)；成功则 (None, None)。吞掉编译器自身的 stdout。"""
    from lexer import Lexer
    from light_parser_v3 import LightParser
    _o, _e = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        try:
            Lexer().tokenize(code)
            LightParser().parse(code)
            return None, None
        except BaseException as e:      # 含 MemoryError 等非 Exception
            return type(e).__name__, str(e)
    finally:
        sys.stdout, sys.stderr = _o, _e


def scan_all():
    """扫描 docs/ 下所有 light 代码块，返回结果列表。"""
    results = []
    for dirpath, dirnames, filenames in os.walk(DOCS):
        dirnames[:] = [d for d in dirnames if d not in ('.git', 'node_modules')]
        for fn in filenames:
            if not fn.endswith('.md'):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding='utf-8') as f:
                    text = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            rel = os.path.relpath(p, ROOT).replace('\\', '/')
            for lang, ln, code in iter_blocks(text):
                if not code.strip():
                    continue
                h = hashlib.sha1(code.encode('utf-8')).hexdigest()[:12]
                if h in _HOSTILE_HASHES:
                    # 绝不在本进程 parse——见 _HOSTILE_HASHES 注释。
                    # 记为 COMPILER_BUG，不进逐条基线，靠单独待修单跟踪。
                    results.append({
                        'file': rel, 'line': ln, 'lang': lang, 'code': code,
                        'hash': h, 'exc': 'HostileSkipped',
                        'msg': _HOSTILE_HASHES[h],
                        'first_line': _first_line(code),
                    })
                    continue
                exc, msg = _compile_once(code)
                results.append({
                    'file': rel, 'line': ln, 'lang': lang, 'code': code,
                    'hash': h,
                    'exc': exc, 'msg': msg,
                    'first_line': _first_line(code),
                })
    return results
