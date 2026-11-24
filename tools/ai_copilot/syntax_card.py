# -*- coding: utf-8 -*-
"""
光明语法速查卡生成器（T-0459 三层重写）

从 spec/light.spec.json 派生三层语法卡（compact / standard / full），
让 AI 在生成光明代码时不用凭"印象"猜语法，而是按卡片精确翻译。

设计原则（T-0459 卡面约束）：
  - 所有事实从 spec 取：keywords / l0_core / stdlib / operators / diagnostics
    都来自 spec/light.spec.json；本文件不维护第二份关键字表。
  - 版本号唯一真源是 src/version.py，运行时读取，禁止写死。
  - 取不到的数据在卡里留空并注明，不编造。

三层定位：
  compact  ≤300 字符（len() 计）：6 条硬规则 + L0 分组 + 最小可跑例子。
           这是 agent 的"开机记忆"，默认层。
  standard ≤3000 字符（len() 计）：compact 全文 + 语法骨架（按 spec keywords
           类别过滤）+ 运算符（spec operators）+ stdlib 常用 50（spec stdlib）
           + 暗坑全量（spec diagnostics，一行一条）。
  full     索引页：不给正文，指向 docs/ai/ 三份文档与 light ai snippets 用法。

用法：
    from syntax_card import generate_syntax_card
    card = generate_syntax_card('compact')    # 默认层（≈300 字符内）
    card = generate_syntax_card('standard')   # 标准参照（≈3000 字符内）
    card = generate_syntax_card('full')       # 索引页
    # 旧调用方式（T-0464 接 --level 之前的兼容层）：
    card = generate_syntax_card(compact=True)   # 等价 level='compact'
    card = generate_syntax_card(compact=False)  # 等价 level='standard'

文档落盘（docs/ai/ 三份与生成输出逐字一致，由测试断言防腐烂）：
    from syntax_card import write_ai_docs
    write_ai_docs()   # 生成 docs/ai/compact.md、standard.md、README.md
"""

import json
import os
import re
import sys

_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SRC_DIR = os.path.join(_PROJECT_DIR, 'src')
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# T-0326：速查卡顶部引用 MVP 链接（单一入口）。
# 读不到 / 格式不符一律返回空串，不抛异常、不阻塞卡片生成。
_STATUS_MD = os.path.join(_PROJECT_DIR, 'STATUS.md')
_MVP_LINK = 'docs/MVP_SURFACE.md'

# T-0459：三层卡的事实真源与版本真源。
_SPEC_PATH = os.path.join(_PROJECT_DIR, 'spec', 'light.spec.json')
_VERSION_PATH = os.path.join(_SRC_DIR, 'version.py')

# ── 数据加载（全部事实从 spec / version.py 取，缓存进程内结果）──────────

_SPEC_CACHE = None
_VERSION_CACHE = None


def _load_spec():
    """读取 spec/light.spec.json；读不到返回 None，调用方按空数据处理。"""
    global _SPEC_CACHE
    if _SPEC_CACHE is None:
        try:
            with open(_SPEC_PATH, encoding='utf-8') as handle:
                _SPEC_CACHE = json.load(handle)
        except (OSError, ValueError):
            _SPEC_CACHE = {}
    return _SPEC_CACHE


def read_version() -> str:
    """版本唯一真源：src/version.py 的 __version__。

    读不到 / 格式不符返回空串，不抛异常、不阻塞卡片生成。
    """
    global _VERSION_CACHE
    if _VERSION_CACHE is None:
        try:
            with open(_VERSION_PATH, encoding='utf-8') as handle:
                text = handle.read(16384)
        except (OSError, UnicodeError):
            _VERSION_CACHE = ''
        else:
            match = re.search(r'(?m)^__version__\s*=\s*["\']([^"\']+)["\']', text)
            _VERSION_CACHE = match.group(1).strip() if match else ''
    return _VERSION_CACHE


def _keywords() -> list:
    return _load_spec().get('keywords') or []


def _keywords_by_category() -> dict:
    """把 spec keywords 按「类别」字段机械分组（多类别条目归入每个出现的类别）。"""
    groups = {}
    for item in _keywords():
        word = str(item.get('字') or '').strip()
        raw = str(item.get('类别') or '').strip()
        if not word or not raw:
            continue
        for category in (part.strip() for part in raw.split('、')):
            if category:
                groups.setdefault(category, [])
                if word not in groups[category]:
                    groups[category].append(word)
    return groups


def _operators() -> list:
    return _load_spec().get('operators') or []


def _diagnostics() -> list:
    return _load_spec().get('diagnostics') or []


def _l0_chapters() -> list:
    return (_load_spec().get('l0_core') or {}).get('章节') or []


def _stdlib_modules() -> list:
    return (_load_spec().get('stdlib') or {}).get('模块') or []


def _stdlib_exports() -> dict:
    """{模块名: [导出名, ...]}，保持 spec 顺序。"""
    return {str(m.get('模块') or ''): [str(e.get('名字') or '') for e in (m.get('导出') or [])]
            for m in _stdlib_modules()}


# ── stdlib 常用 50：确定性白名单（选择规则在此，函数名全部来自 spec）──────
# 每模块按 spec 导出顺序取前 N 个，按白名单顺序收集，凑满 50 为止。

_STDLIB_TOP_PLAN = (
    ('文件系统', 10),
    ('字符串工具', 10),
    ('列表工具', 10),
    ('数学统计', 8),
    ('随机', 6),
    ('JSON', 6),
)
_STDLIB_TOP_LIMIT = 50


def _stdlib_top() -> list:
    """[(模块名, [函数名, ...]), ...]；spec 缺模块时跳过，凑不满照实返回。"""
    exports = _stdlib_exports()
    picked = []
    for module, limit in _STDLIB_TOP_PLAN:
        names = exports.get(module) or []
        taken = [n for n in names[:limit] if n]
        if taken:
            picked.append((module, taken))
        if sum(len(names) for _, names in picked) >= _STDLIB_TOP_LIMIT:
            break
    # 收尾截断到 50（模块内保持 spec 顺序，最后一段可能被截）
    total = 0
    trimmed = []
    for module, names in picked:
        room = _STDLIB_TOP_LIMIT - total
        if room <= 0:
            break
        keep = names[:room]
        if keep:
            trimmed.append((module, keep))
            total += len(keep)
    return trimmed


def _stdlib_top_names() -> set:
    return {name for _, names in _stdlib_top() for name in names}


# ── L0 分组（spec l0_core：章节 + 字数；spec 未收录字面，卡里注明）───────

def _l0_line() -> str:
    chapters = _l0_chapters()
    if not chapters:
        return 'L0:（spec 无 l0_core 数据）'
    total = sum(int(c.get('字数') or 0) for c in chapters)
    parts = [f"{c.get('章节')}{c.get('字数')}" for c in chapters if c.get('章节')]
    return f"L0共{total}字{len(chapters)}章:" + ' '.join(parts)


# ── 硬规则（compact 顶部；规则文案是编辑决策，出现的标识符均为 spec 事实）──

_HARD_RULES = (
    '1.读取(x)编译成input(x)等stdin,读文件用读取文件',
    '2.print改打印;冒号必选,块靠缩进',
    '3.赋值:设甲为10/定义甲等于"文本"',
    '4.运算用中文:加减乘除以等于不等于且或非',
    '5.循环变量更新用设:设i为i加1',
    '6.变量名避开内建名(如"长度")',
)

_COMPACT_EXAMPLE = ('【例】设甲为1\n'
                    '如果甲大于0:\n'
                    '    打印"正"')


def generate_compact_card() -> str:
    """compact 层：≤300 字符（len() 计）。"""
    version = read_version()
    head = f'光明v{version}速查(compact)' if version else '光明速查(compact)'
    lines = [
        head,
        '【6条硬规则】',
        *_HARD_RULES,
        f'【{_l0_line()}】',
        _COMPACT_EXAMPLE,
    ]
    return '\n'.join(lines) + '\n'


# ── standard 层 ──────────────────────────────────────────────────────

# spec keywords 中进入骨架的类别 → 展示标题（机械过滤，不编造对应关系）
_SKELETON_SECTIONS = (
    ('条件判断', '条件'),
    ('循环控制', '循环'),
    ('函数定义', '段落(函数)'),
    ('类与对象', '类'),
    ('异常处理', '异常'),
    ('嵌入块', '嵌入(L3域)'),
    ('模块系统', '导入'),
    ('逻辑运算', '逻辑'),
    ('特殊值', '特殊值'),
)


def _skeleton_lines() -> list:
    groups = _keywords_by_category()
    lines = []
    for category, title in _SKELETON_SECTIONS:
        words = groups.get(category) or []
        if words:
            lines.append(f'{title}:' + '/'.join(words))
        else:
            lines.append(f'{title}:(spec 无该类别关键字)')
    return lines


def _operator_lines() -> list:
    operators = _operators()
    if not operators:
        return ['运算符:(spec 无 operators 数据)']
    by_category = {}
    for op in operators:
        name = str(op.get('名称') or '').strip()
        canonical = str(op.get('canonical') or '').strip()
        category = str(op.get('类别') or '').strip() or '其他'
        status = str(op.get('状态') or '').strip()
        if not name and not canonical:
            continue
        label = f'{name}({canonical})' if canonical and canonical != name else name
        if status and status != '可用':
            label += f'[{status}]'
        by_category.setdefault(category, [])
        if label not in by_category[category]:
            by_category[category].append(label)
    lines = []
    for category, labels in by_category.items():
        lines.append(f'  {category}:' + '/'.join(labels))
    return lines


def _stdlib_lines() -> list:
    picked = _stdlib_top()
    if not picked:
        return ['stdlib 常用50:(spec 无 stdlib 数据)']
    lines = []
    for module, names in picked:
        lines.append(f'  {module}:' + '/'.join(names))
    return lines


def _pitfall_lines() -> list:
    diagnostics = _diagnostics()
    if not diagnostics:
        return ['(spec 无 diagnostics 数据)']
    lines = []
    for item in diagnostics:
        code = str(item.get('code') or '').strip()
        title = str(item.get('title') or '').strip()
        lines.append(f'{code} {title}'.strip())
    return lines


def generate_standard_card() -> str:
    """standard 层：≤3000 字符（len() 计）。"""
    version = read_version()
    head = f'光明v{version}语法卡(standard)' if version else '光明语法卡(standard)'
    lines = [
        head,
        '事实来源:spec/light.spec.json(keywords/l0_core/stdlib/operators/diagnostics),版本真源:src/version.py',
        '════compact 层════',
        generate_compact_card(),
        '════语法骨架(关键字来自 spec keywords)════',
        *_skeleton_lines(),
        '嵌入示例:引 SQL: SELECT ... 结束引(SQL/模式/公式 为 L3 域标签示例)',
        '════运算符(spec operators)════',
        *_operator_lines(),
        '════stdlib 常用50(函数名来自 spec stdlib)════',
        *_stdlib_lines(),
        f'════暗坑(共{len(_pitfall_lines())}条,来自 spec diagnostics,一行一条)════',
        *_pitfall_lines(),
    ]
    return '\n'.join(lines) + '\n'


# ── full 层（索引页：不给正文）────────────────────────────────────────

def generate_full_card() -> str:
    """full 层：索引页，指向 docs/ai/ 三份文档与 snippets 用法。"""
    version = read_version()
    head = f'光明语法卡索引(full) v{version}' if version else '光明语法卡索引(full)'
    lines = [
        head,
        '版本真源:src/version.py;事实真源:spec/light.spec.json',
        '三层速查卡(docs/ai/):',
        '- docs/ai/compact.md:≤300字开机卡(agent prompt 默认嵌入这层)',
        '- docs/ai/standard.md:≤3000字标准参照(骨架/运算符/stdlib50/暗坑全量)',
        '- docs/ai/README.md:本索引',
        '片段库:light ai snippets 列出全部片段;light ai snippets <名称> 取单个片段',
        '文档再生成:tools/ai_copilot/syntax_card.py 的 write_ai_docs() 落盘 docs/ai/ 三份,与卡逐字一致',
    ]
    return '\n'.join(lines) + '\n'


# ── 统一入口与兼容层 ─────────────────────────────────────────────────

_LEVEL_GENERATORS = {
    'compact': generate_compact_card,
    'standard': generate_standard_card,
    'full': generate_full_card,
}

_RANKED_HEADER = "## 最近 30 天最常踩的坑（TOP {n}）"


def _render_ranked(ranked) -> str:
    """把 error_stats.rank_pitfalls() 的排行渲染成置顶区块（含尾部空行）。

    `ranked` 为空 / None / 全部条目不可用时返回空串，调用方据此走静态分支，
    保证无数据时输出与静态卡逐字一致。
    """
    items = [item for item in (ranked or [])
             if isinstance(item, dict) and (item.get("code") or item.get("title"))]
    if not items:
        return ""

    lines = [_RANKED_HEADER.format(n=len(items))]
    for index, item in enumerate(items, 1):
        code = str(item.get("code") or "").strip()
        title = str(item.get("title") or "").strip() or code
        # 「正确写法」压成单行；多行 fix 不换行打断卡片
        example = " ".join(str(item.get("example") or "").split())
        tag = f"[{code}] " if code else ""
        line = f"{index}. {tag}{title}"
        if example:
            line += f" —— {example}"
        lines.append(line)

    return "\n".join(lines) + "\n\n"


def generate_syntax_card(level: str = 'compact', compact=None,
                         include_verbs: bool = False, include_pitfalls: bool = False,
                         ranked=None) -> str:
    """生成语法速查卡（T-0459 三层）

    Args:
        level: 'compact' | 'standard' | 'full'。full 是索引页，忽略附加参数。
        compact: 旧签名兼容，三态。True → level='compact'；False →
            level='standard'；None（未传）→ 保持 level（默认 'compact'）。
            （T-0464 接 --level 开关之前，cli/light.py 仍按此映射调用。）
        include_verbs: 是否追加旧式「动词参数参照」附录（full 层忽略）。
        include_pitfalls: 是否追加旧式「暗坑说明」附录（full 层忽略）。
        ranked: 可选，`error_stats.rank_pitfalls()` 的返回值。非空时在最顶部
            插入「最近 30 天最常踩的坑（TOP N）」区块；空/None 时输出与
            静态卡逐字一致（full 层忽略）。

    Returns:
        速查卡文本，可直接嵌入 prompt
    """
    if compact is True:
        level = 'compact'
    elif compact is False:
        level = 'standard'
    elif not level:
        level = 'standard'

    generate = _LEVEL_GENERATORS.get(level)
    if generate is None:
        raise ValueError(f"未知 level: {level!r}（可选 compact/standard/full）")

    card = generate()

    if level != 'full':
        if include_verbs:
            card += "\n\n【动词参数参照】\n" + _generate_verb_table()
        if include_pitfalls:
            card += "\n\n" + generate_pitfalls()
        ranked_block = _render_ranked(ranked)
        if ranked_block:
            card = ranked_block + card

    return card


# ── 文档落盘（docs/ai/ 三份与生成输出逐字一致，测试断言防腐烂）────────────

_AI_DOC_FILES = (
    ('compact.md', generate_compact_card),
    ('standard.md', generate_standard_card),
    ('README.md', generate_full_card),
)


def write_ai_docs(docs_dir=None) -> list:
    """把三层卡写入 docs/ai/（默认项目 docs/ai/），返回写出的文件名列表。

    文件内容与生成函数输出逐字一致（tests 断言两边相等，防止文档腐烂）。
    """
    target = docs_dir or os.path.join(_PROJECT_DIR, 'docs', 'ai')
    os.makedirs(target, exist_ok=True)
    written = []
    for name, generate in _AI_DOC_FILES:
        path = os.path.join(target, name)
        with open(path, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(generate())
        written.append(name)
    return written


# ── 旧附录（pipeline / prompt_generator 等调用方仍在使用，保持兼容）───────

def _generate_verb_table() -> str:
    """生成动词（运算符/函数）快速参照表（旧附录，元数来自 src/keywords.py）。"""
    from keywords import VERB_ARITY
    lines = []
    categories = {
        "算术": ["加", "减", "乘", "除以", "取余", "幂", "乘以", "加上", "减去"],
        "比较": ["等于", "不等于", "大于", "小于", "大于等于", "小于等于"],
        "列表": ["首", "末", "余", "长", "排序", "反转", "求和", "求最大", "求最小", "去重", "筛选", "映射"],
        "IO": ["打印", "读取", "输出"],
        "文件": ["读取文件", "写入文件", "追加文件", "文件存在", "目录存在", "创建目录", "列出目录"],
        "字符串": ["转整数", "转浮点", "转字符串", "分割字符串", "连接字符串", "替换字符串", "去除空白"],
        "类型": ["是整数", "是浮点", "是字符串", "是列表", "是字典", "是空"],
    }

    for cat, verbs in categories.items():
        entries = []
        for v in verbs:
            arity = VERB_ARITY.get(v, "?")
            entries.append(f"{v}({arity}参)")
        lines.append(f"  {cat}：" + " / ".join(entries))

    return "\n".join(lines)


def status_banner() -> str:
    """返回速查卡顶部的状态引用块；读不到版本/MVP 链接时对应行缺省。

    T-0459：版本行改读 src/version.py（版本唯一真源），STATUS.md 只用于
    检查 MVP 链接登记。两处读不到都不抛异常。
    """
    version = read_version()
    lines = []
    if version:
        lines.append(f'当前状态：v{version}（版本真源 src/version.py）')
    try:
        with open(_STATUS_MD, 'r', encoding='utf-8') as handle:
            text = handle.read(8192)
    except (OSError, UnicodeError):
        text = ''
    if text and _MVP_LINK in text:
        lines.append(f'最小可用面：{_MVP_LINK}（见 STATUS.md）')
    return '\n'.join(lines) + '\n' if lines else ''


_PITFALLS = """\
【光明暗坑 — AI 生成时必须注意】

1. 列表索引赋值：不能用"设 列表[i] 为 值"，正确写法是"列表[i] = 值"
   ✗ 设 列表[0] 为 10    （语法错误）
   ✓ 列表[0] = 10         （正确）

2. 变量名不能与内建函数同名：
   ✗ 设 长度 为 10        （"长度"会遮蔽内建函数）
   ✓ 设 n 为 10           （正确）

3. SRC 后端内建函数差异：
   · len()/str()/int()/float()/type()/range() 等Python内建可用
   · 中文内建函数（读取文件/列表长度等）需 "从 标准库 导入 ..." 或 "导入 标准库"
   · 长度() 不是SRC后端内建！用 len() 或 列表长度()

4. 类系统后端差异：
   · SRC 后端：类定义可解析，但运行时行为有限
   · LLVM 后端：完整支持类、继承、方法重写
   · 含类代码建议用 LLVM 后端：light compile file.light --backend llvm-typed

5. 运算符不能混用Python写法：
   ✗ a + b / a - b / a <= b / a != b / a >= b
   ✓ a 加 b / a 减 b / a 小于等于 b / a 不等于 b / a 大于等于 b
   例外：列表索引赋值中 = 可用

6. 循环变量更新必须用"设"：
   ✗ i = i + 1
   ✓ 设 i 为 i 加 1  /  i 加上 1

7. 遍历范围用"至"不用逗号：
   ✗ 遍历 i 于 range(1, 10)：
   ✓ 遍历 i 于 1至10：
"""


def generate_pitfalls() -> str:
    """单独输出旧式暗坑说明（7 条编辑沉淀；三层卡正文用的是 spec diagnostics 全量）。"""
    return _PITFALLS


def generate_example_pairs() -> str:
    """生成 Python→光明 对照示例，用于翻译模式 prompt（旧附录，保持不变）。"""
    pairs = """\
【Python→光明 对照示例】

# 1. 变量
x = 10           →  设 x 为 10
name = "hello"   →  定义 name 等于 "你好"
x += 1           →  x 加上 1

# 2. 函数
def add(a, b):   →  段落 加法 接收 a, b：
    return a + b →      返回 a 加 b

# 3. 条件
if x > 5:        →  如果 x 大于 5：
    print("大")  →      打印 "大"
elif x > 3:      →  否则如果 x 大于 3：
    print("中")  →      打印 "中"
else:            →  否则：
    print("小")  →      打印 "小"

# 4. 循环
while x < 10:    →  当 x 小于 10：
    x += 1       →      设 x 为 x 加 1

for i in range(1, 11):  →  遍历 i 于 1至10：
    print(i)             →      打印(i)

for item in lst:  →  遍历 项 于 lst：
    print(item)   →      打印(项)

# 5. 列表
lst = [1, 2, 3]  →  设 lst 为 [1, 2, 3]
lst.append(4)    →  lst.追加(4)
len(lst)         →  len(lst)  （SRC后端用Python内建len）

# ⚠ 暗坑：列表索引赋值
lst[0] = 10      →  lst[0] = 10  （不能用"设 lst[0] 为 10"）

# 6. 类（建议用LLVM后端）
class Dog:             →  类 狗：
    def __init__(self, name):  →      构造 接收 名称：
        self.name = name       →          己名称 为 名称
    def speak(self):           →      段落 发声：
        print("汪")            →          打印 "汪"
dog = Dog("旺财")     →  设 小狗 为 新建 狗("旺财")

# 7. 异常
try:               →  尝试：
    risky()        →      危险操作()
except Exception:  →  捕获 异常：
    handle()       →      处理()

# 8. 导入
from math import factorial  →  从 数学工具 导入 阶乘
"""
    return pairs


if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("【compact 层】")
    print("=" * 60)
    print(generate_compact_card())
    print("=" * 60)
    print("【standard 层】")
    print("=" * 60)
    print(generate_standard_card())
    print("=" * 60)
    print("【full 层（索引）】")
    print("=" * 60)
    print(generate_full_card())
    print(f"compact len={len(generate_compact_card())} "
          f"standard len={len(generate_standard_card())} full len={len(generate_full_card())}")
