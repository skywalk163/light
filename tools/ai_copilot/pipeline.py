"""
光明 AI Copilot — 一揽子管线

核心思路：用户不需要手动串联 card→snippets→prompt→check，
只需一条命令即可获得可直接粘贴给 LLM 的完整 prompt。

两条管线：
  generate — 需求描述 → 自动组装 prompt（速查卡 + 匹配片段 + 暗坑 + 任务）
  fix      — 出错代码 + 错误信息 → 修复 prompt（速查卡 + 原码 + 错误 + 暗坑）

模型分级（--model-size）：
  small  (≤7B)  → 极简卡 + 关键片段模板 + 极简暗坑（总 prompt ≤500 字）
  medium (7-14B) → 精简卡 + 匹配片段（含示例）+ 暗坑（总 prompt ≤1500 字）
  large  (≥14B) → 完整卡 + 全部片段 + 完整暗坑 + 动词表（不限制）

用法：
    from pipeline import generate_pipeline, fix_pipeline
    prompt = generate_pipeline("写一个冒泡排序")
    prompt = fix_pipeline("sort.light", "第3行语法错误")
"""

from syntax_card import generate_syntax_card, generate_pitfalls, generate_example_pairs
from snippets import SNIPPETS, get_snippets_prompt, get_snippet


# ═══════════════════════════════════════════════════════════════════
# 片段自动匹配
# ═══════════════════════════════════════════════════════════════════

# 关键词 → 片段名 映射表（一个关键词可匹配多个片段）
_KEYWORD_MAP = {
    # 变量
    "变量": ["变量-整数", "变量-字符串", "变量-列表"],
    "整数": ["变量-整数"],
    "字符串": ["变量-字符串"],
    "列表": ["变量-列表", "列表-累加", "列表-筛选"],
    "数组": ["变量-列表", "列表-累加", "列表-筛选"],
    # 段落/函数
    "段落": ["段落-带返回值", "段落-无返回值", "段落-递归"],
    "函数": ["段落-带返回值", "段落-无返回值", "段落-递归"],
    "递归": ["段落-递归"],
    "返回": ["段落-带返回值"],
    # 条件
    "条件": ["条件-二分支", "条件-多分支"],
    "判断": ["条件-二分支", "条件-多分支"],
    "分支": ["条件-多分支"],
    "if": ["条件-二分支", "条件-多分支"],
    # 循环
    "循环": ["循环-当循环", "循环-遍历范围", "循环-遍历列表"],
    "遍历": ["循环-遍历范围", "循环-遍历列表"],
    "while": ["循环-当循环"],
    "for": ["循环-遍历范围", "循环-遍历列表"],
    "步长": ["循环-遍历带步长"],
    # 列表操作
    "排序": ["循环-遍历范围", "变量-列表", "列表-筛选"],
    "求和": ["列表-累加"],
    "累加": ["列表-累加"],
    "筛选": ["列表-筛选"],
    "过滤": ["列表-筛选"],
    # 类
    "类": ["类-基本", "类-继承"],
    "对象": ["类-基本"],
    "继承": ["类-继承"],
    # 异常
    "异常": ["异常-捕获"],
    "错误处理": ["异常-捕获"],
    # 导入
    "导入": ["导入-标准库"],
    # 测试
    "测试": ["测试-断言相等"],
    "断言": ["测试-断言相等"],
}

# 小模型专用：只推荐最核心的片段
_CORE_SNIPPETS = ["变量-整数", "段落-带返回值", "条件-二分支", "循环-遍历范围", "循环-遍历列表"]


def _match_snippets(requirement: str, model_size: str = "medium") -> list:
    """根据需求描述自动匹配相关片段

    Args:
        requirement: 用户需求描述
        model_size: small/medium/large

    Returns:
        匹配到的片段名列表，按命中次数排序
    """
    if model_size == "small":
        # 小模型只给核心片段
        return _CORE_SNIPPETS[:3]

    # 统计每个片段的命中次数
    hit_count = {}
    for kw, snippet_names in _KEYWORD_MAP.items():
        if kw in requirement:
            for name in snippet_names:
                hit_count[name] = hit_count.get(name, 0) + 1

    if not hit_count:
        # 无命中时返回通用片段
        if model_size == "medium":
            return ["变量-整数", "段落-带返回值", "循环-遍历范围"]
        else:
            return list(SNIPPETS.keys())

    # 按命中次数排序，取 top N
    sorted_names = sorted(hit_count.keys(), key=lambda x: hit_count[x], reverse=True)
    if model_size == "medium":
        return sorted_names[:5]
    else:
        return sorted_names


# ═══════════════════════════════════════════════════════════════════
# 模型分级 prompt 策略
# ═══════════════════════════════════════════════════════════════════

_GENERATE_SMALL = """\
你是光明v3.2代码生成器。严格按照下方规则输出光明代码，不要解释。

{compact_card}

相关片段：
{snippets_block}

⚠暗坑：列表[i]=值✓ | 设列表[i]为值✗ | 变量名≠内建函数名 | 运算用中文

需求：{requirement}
只输出光明代码。"""

_GENERATE_MEDIUM = """\
你是光明（LightLang）v3.2 代码生成器。请根据需求生成光明代码。

{syntax_card}

{snippets_block}

{pitfalls_block}

生成规则：
1. 严格按照上方语法速查卡，不要使用旧语法
2. 段落定义只用「段落 名 接收 参数：」形式
3. 冒号必选，句号可选，空格可选
4. 纯缩进代码块，无花括号/无结束关键字
5. 优先从相关片段中选择匹配的模板，填充占位符
6. 同时生成对应的测试断言（使用 测试.light 标准库）
7. 只输出光明代码，不要解释

需求：{requirement}"""

_GENERATE_LARGE = """\
你是一个专业的光明（LightLang）v3.2 代码生成器。请根据需求生成高质量的光明代码。

{syntax_card}

{verbs_block}

{snippets_block}

{pitfalls_block}

{examples_block}

生成规则：
1. 严格按照上方语法速查卡，不要使用旧语法（如"函数"、"段"、"参数"等）
2. 段落定义只用「段落 名 接收 参数：」形式
3. 冒号必选，句号可选，空格可选
4. 纯缩进代码块，无花括号/无结束关键字
5. 优先从片段库中选择匹配的模板，填充占位符
6. 同时生成对应的测试断言（使用 测试.light 标准库的 断言相等/断言为真）
7. 代码需包含异常处理和边界情况
8. 只输出光明代码，不要解释

需求：{requirement}"""

_FIX_SMALL = """\
你是光明v3.2代码修复器。按下方规则修复代码，只输出修正后的代码。

{compact_card}

⚠暗坑：列表[i]=值✓ | 设列表[i]为值✗ | 变量名≠内建函数名 | 运算用中文

原始代码：
```
{code}
```

错误信息：
{error}

只输出修复后的光明代码。"""

_FIX_MEDIUM = """\
你是光明（LightLang）v3.2 代码修复器。请根据错误信息修复光明代码。

{syntax_card}

{pitfalls_block}

原始代码：
```
{code}
```

错误信息：
{error}

修复规则：
1. 严格按照语法速查卡修复，不要使用旧语法
2. 优先检查暗坑中列出的常见错误
3. 只输出修复后的光明代码，不要解释
4. 如果错误信息不明确，优先检查：列表索引赋值语法、变量名冲突、运算符中文
"""

_FIX_LARGE = """\
你是一个专业的光明（LightLang）v3.2 代码修复器。请根据错误信息修复光明代码。

{syntax_card}

{verbs_block}

{pitfalls_block}

{examples_block}

原始代码：
```
{code}
```

错误信息：
{error}

修复规则：
1. 严格按照语法速查卡修复，不要使用旧语法
2. 优先检查暗坑中列出的常见错误
3. 确保修复后的代码包含异常处理和边界情况
4. 只输出修复后的完整光明代码，不要解释
5. 如果错误信息不明确，按以下顺序排查：
   a. 列表索引赋值是否用了"设 列表[i] 为 值"（应改为"列表[i] = 值"）
   b. 变量名是否与内建函数同名（如"长度"、"类型"）
   c. 运算符是否用了Python符号而非中文（+→加，-→减，<=→小于等于等）
   d. 类系统是否在SRC后端运行（需LLVM后端）
   e. 循环变量更新是否用了"设 i 为 i 加 1"而非"i = i + 1"
"""


# ═══════════════════════════════════════════════════════════════════
# 管线入口
# ═══════════════════════════════════════════════════════════════════

def generate_pipeline(requirement: str, model_size: str = "medium",
                      mode: str = "auto") -> str:
    """一揽子生成管线：需求 → 完整 prompt

    Args:
        requirement: 用户的代码需求描述
        model_size: small(≤7B) / medium(7-14B) / large(≥14B)
        mode: auto/translate/create/paragraph（仅 medium/large 生效）

    Returns:
        可直接粘贴给 LLM 的结构化 prompt
    """
    # 小模型强制用 create 模式（最省 token）
    if model_size == "small":
        mode = "create"

    if model_size == "small":
        return _GENERATE_SMALL.format(
            compact_card=generate_syntax_card(compact=True),
            snippets_block=_build_snippets_block(_match_snippets(requirement, "small"), brief=True),
            requirement=requirement,
        )

    elif model_size == "medium":
        matched = _match_snippets(requirement, "medium")
        return _GENERATE_MEDIUM.format(
            syntax_card=generate_syntax_card(compact=True),
            snippets_block=_build_snippets_block(matched, brief=False),
            pitfalls_block=generate_pitfalls(),
            requirement=requirement,
        )

    else:  # large
        matched = _match_snippets(requirement, "large")
        return _GENERATE_LARGE.format(
            syntax_card=generate_syntax_card(compact=False, include_verbs=False),
            verbs_block=_generate_verb_block(),
            snippets_block=get_snippets_prompt(),
            pitfalls_block=generate_pitfalls(),
            examples_block=generate_example_pairs(),
            requirement=requirement,
        )


def fix_pipeline(filepath: str, error: str, model_size: str = "medium") -> str:
    """一揽子修复管线：出错代码 + 错误 → 修复 prompt

    Args:
        filepath: 出错的光明源文件路径
        error: 错误信息（来自 light ai check 的输出）
        model_size: small/medium/large

    Returns:
        可直接粘贴给 LLM 的修复 prompt
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        code = f.read()

    if model_size == "small":
        return _FIX_SMALL.format(
            compact_card=generate_syntax_card(compact=True),
            code=code,
            error=error,
        )

    elif model_size == "medium":
        return _FIX_MEDIUM.format(
            syntax_card=generate_syntax_card(compact=True),
            pitfalls_block=generate_pitfalls(),
            code=code,
            error=error,
        )

    else:  # large
        return _FIX_LARGE.format(
            syntax_card=generate_syntax_card(compact=False, include_verbs=False),
            verbs_block=_generate_verb_block(),
            pitfalls_block=generate_pitfalls(),
            examples_block=generate_example_pairs(),
            code=code,
            error=error,
        )


# ═══════════════════════════════════════════════════════════════════
# 内部工具
# ═══════════════════════════════════════════════════════════════════

def _build_snippets_block(snippet_names: list, brief: bool = False) -> str:
    """构建片段输出块

    Args:
        snippet_names: 要输出的片段名列表
        brief: True 只输出模板，False 输出模板+示例+暗坑
    """
    lines = ["【相关代码片段】", ""]
    for name in snippet_names:
        snippet = SNIPPETS.get(name)
        if not snippet:
            continue
        lines.append(f"片段：{name}")
        lines.append(f"  用途：{snippet['desc']}")
        lines.append(f"  模板：{snippet['code']}")
        if not brief:
            if 'example' in snippet:
                lines.append(f"  示例：{snippet['example']}")
            if 'pitfall' in snippet:
                lines.append(f"  ⚠暗坑：{snippet['pitfall']}")
        lines.append("")
    return "\n".join(lines)


def _generate_verb_block() -> str:
    """生成动词参数参照块（仅 large 模式使用）"""
    from keywords import VERB_ARITY
    lines = ["【动词参数参照】", ""]
    categories = {
        "算术": ["加", "减", "乘", "除以", "取余", "幂", "乘以", "加上", "减去"],
        "比较": ["等于", "不等于", "大于", "小于", "大于等于", "小于等于"],
        "列表": ["首", "末", "余", "长", "排序", "反转", "求和", "求最大", "求最小", "去重", "筛选", "映射"],
        "IO": ["打印", "读取", "输出"],
    }
    for cat, verbs in categories.items():
        entries = []
        for v in verbs:
            arity = VERB_ARITY.get(v, "?")
            entries.append(f"{v}({arity}参)")
        lines.append(f"  {cat}：" + " / ".join(entries))
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    # 测试 generate 管线
    print("=" * 60)
    print("【generate — small】")
    print("=" * 60)
    p1 = generate_pipeline("写一个冒泡排序", model_size="small")
    print(p1)
    print(f"\n--- 总字数: {len(p1)} ---\n")

    print("=" * 60)
    print("【generate — medium】")
    print("=" * 60)
    p2 = generate_pipeline("写一个冒泡排序", model_size="medium")
    print(p2)
    print(f"\n--- 总字数: {len(p2)} ---\n")

    print("=" * 60)
    print("【generate — large（截断）】")
    print("=" * 60)
    p3 = generate_pipeline("写一个冒泡排序", model_size="large")
    print(p3[:800] + "...")
    print(f"\n--- 总字数: {len(p3)} ---\n")
