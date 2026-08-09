"""
光明 AI Copilot — Prompt 生成器

核心模块：根据用户的代码需求，生成一个结构化的 prompt，
让 AI（即使算力有限）也能稳定输出正确的光明 v3.2 代码。

设计原则：
  1. 翻译模式优于创作模式（Python→光明，让 AI 做翻译而非创作）
  2. 语法速查卡锁死语法边界（AI 不需要"猜"语法）
  3. 代码片段库提供骨架（AI 只需填充，不需要从零构建）
  4. 同时生成测试断言（运行时校验 > AI 自检）

用法：
    from prompt_generator import generate_prompt
    prompt = generate_prompt("写一个二分查找函数")
    prompt = generate_prompt("def binary_search(arr, target): ...", mode="translate")
"""

from syntax_card import generate_syntax_card, generate_example_pairs
from snippets import SNIPPETS, get_snippets_prompt


# ── Prompt 模板 ──────────────────────────────────────────────────

_TRANSLATE_PROMPT = """\
你是一个光明（LightLang）v3.2 代码翻译器。你的任务是将 Python 代码翻译为光明代码。

{syntax_card}

{example_pairs}

翻译规则：
1. 严格按照上方语法速查卡翻译，不要使用旧语法（如"函数"、"段"、"参数"等）
2. 段落定义只用「段落 名 接收 参数：」形式
3. 冒号必选，句号可选，空格可选
4. 纯缩进代码块，无花括号/无结束关键字
5. 只输出光明代码，不要解释

请将以下 Python 代码翻译为光明 v3.2：

```python
{user_code}
```
"""

_CREATE_PROMPT = """\
你是一个光明（LightLang）v3.2 代码生成器。请根据需求生成光明代码。

{syntax_card}

{snippets}

生成规则：
1. 严格按照上方语法速查卡，不要使用旧语法
2. 段落定义只用「段落 名 接收 参数：」形式
3. 冒号必选，句号可选，空格可选
4. 纯缩进代码块，无花括号/无结束关键字
5. 优先从片段库中选择匹配的模板，填充占位符
6. 同时生成对应的测试断言（使用 测试.light 标准库的 断言相等/断言为真）
7. 只输出光明代码，不要解释

需求：{user_requirement}
"""

_SINGLE_PARAGRAPH_PROMPT = """\
你是一个光明（LightLang）v3.2 代码生成器。请生成一个光明段落。

{compact_card}

规则：
1. 只用「段落 名 接收 参数：」形式
2. 冒号必选，句号可选
3. 只输出一个段落的代码，不要其他内容
4. 同时输出一行测试断言

段落签名：段落 {paragraph_name} 接收 {parameters}：
功能描述：{description}
"""


def generate_prompt(
    user_input: str,
    mode: str = "auto",
    compact: bool = False,
) -> str:
    """生成让 AI 写光明代码的 prompt

    Args:
        user_input: 用户的输入——可以是自然语言需求，也可以是 Python 代码
        mode: 生成模式
            - "auto": 自动判断（检测是否包含 Python 语法特征）
            - "translate": Python→光明翻译模式
            - "create": 从需求直接创作模式
            - "paragraph": 单段落模式（算力最省）
        compact: 是否使用精简语法卡

    Returns:
        结构化 prompt 文本，可直接粘贴给 AI
    """
    if mode == "auto":
        mode = _detect_mode(user_input)

    if mode == "translate":
        return _TRANSLATE_PROMPT.format(
            syntax_card=generate_syntax_card(compact=compact),
            example_pairs=generate_example_pairs(),
            user_code=user_input,
        )
    elif mode == "create":
        return _CREATE_PROMPT.format(
            syntax_card=generate_syntax_card(compact=compact),
            snippets=get_snippets_prompt(),
            user_requirement=user_input,
        )
    elif mode == "paragraph":
        # 解析段落签名信息
        name, params, desc = _parse_paragraph_request(user_input)
        return _SINGLE_PARAGRAPH_PROMPT.format(
            compact_card=generate_syntax_card(compact=True),
            paragraph_name=name,
            parameters=params,
            description=desc,
        )
    else:
        raise ValueError(f"未知模式: {mode}")


def _detect_mode(user_input: str) -> str:
    """自动检测用户输入的模式"""
    python_indicators = [
        "def ", "class ", "import ", "from ", "return ",
        "if ", "elif ", "else:", "for ", "while ",
        "print(", "lambda ", "->", ":",
    ]
    # 统计 Python 语法特征出现次数
    count = sum(1 for ind in python_indicators if ind in user_input)
    # 如果超过 2 个 Python 特征，判定为翻译模式
    if count >= 2:
        return "translate"
    # 如果描述简短且包含"段落"/"函数"关键词，判定为单段落模式
    if len(user_input) < 50 and any(kw in user_input for kw in ["段落", "函数", "写个", "写一个"]):
        return "paragraph"
    return "create"


def _parse_paragraph_request(user_input: str) -> tuple:
    """从用户输入中解析段落签名信息"""
    # 简单启发式解析
    # 格式示例："写一个二分查找段落，接收列表和目标值"
    name = "功能"
    params = "参数"
    desc = user_input

    # 尝试提取段落名
    for prefix in ["写一个", "写个", "帮我写", "生成一个", "创建一个"]:
        if prefix in user_input:
            rest = user_input.split(prefix, 1)[1]
            # 取第一个逗号或句号前的部分作为名称
            for sep in ["段落", "函数", "，", "，", ",", "。"]:
                if sep in rest:
                    name = rest.split(sep)[0].strip()
                    break
            else:
                name = rest.strip()
            break

    # 尝试提取参数
    if "接收" in user_input:
        after_receive = user_input.split("接收", 1)[1]
        params = after_receive.split("，")[0].split(",")[0].strip()
    elif "参数" in user_input:
        after_param = user_input.split("参数", 1)[1]
        params = after_param.split("，")[0].split(",")[0].strip()

    return name, params, desc


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    # 测试三种模式
    print("=" * 70)
    print("【模式1：Python→光明翻译】")
    print("=" * 70)
    prompt1 = generate_prompt(
        "def fibonacci(n):\n"
        "    if n <= 1:\n"
        "        return n\n"
        "    return fibonacci(n-1) + fibonacci(n-2)\n"
        "\n"
        "print(fibonacci(10))",
        mode="translate",
        compact=True,
    )
    print(prompt1[:500] + "...\n")

    print("=" * 70)
    print("【模式2：从需求创作】")
    print("=" * 70)
    prompt2 = generate_prompt(
        "写一个冒泡排序函数，接收一个列表，返回排序后的列表",
        mode="create",
        compact=True,
    )
    print(prompt2[:500] + "...\n")

    print("=" * 70)
    print("【模式3：单段落模式】")
    print("=" * 70)
    prompt3 = generate_prompt(
        "写一个二分查找段落，接收列表和目标值",
        mode="paragraph",
    )
    print(prompt3)
