# -*- coding: utf-8 -*-
"""光明高频错误码表与 ``explain()``（纯标准库）。

码段约定见 :data:`CODE_SEGMENTS`，每条规则的 ``source`` 都指向 docs 或代码里
的**真实出处**； ``# source:`` 注释与 ``source`` 字段一一对应，方便人工复核。

红线
----
* 未命中任何规则时 ``explain()`` 返回 ``None``，**不造兜底假码**。
* 不为凑数编造语言里不存在的问题：19 条全部来自
  ``docs/AI编程指南.md``（14 个高频错误 / B 段 / 12A 段）、
  ``docs/STDLIB_REFERENCE.md``、``docs/tools.md`` 或 src 下的真实报错模板。
* 原本是 warning / 合法语法 / 静默行为差异的坑，severity 保持 ``warning``，
  **不升级成 error**（见 L1005 / L1007 / L3002 / L3003 / L3004 / L5002 / L5003）。
* ``to_legacy_entry()`` 只做字段搬运，**不注入错误码、不改写 message**，
  因此 ``src/errors.py::ErrorEntry.format()`` 的文本输出逐字不变。

``provisional`` 说明：本卡只交付码表与框架，CLI / 渲染器由 T-0317、T-0318
并行接入。当前 ``explain()`` 是从自由文本正则推断错误码，所以产出的诊断
一律 ``provisional=True``；等编译器内部异常直接带码时再翻成 ``False``。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .model import MAX_FIXES, SEVERITIES, Diagnostic

__all__ = [
    "CODE_SEGMENTS",
    "CODE_PATTERN",
    "Rule",
    "RULES",
    "all_codes",
    "duplicate_codes",
    "explain",
    "get",
    "to_legacy_entry",
]

#: 码段 → 含义。首位数字即码段号，后三位为段内序号。
CODE_SEGMENTS: Dict[str, str] = {
    "L1": "词法/语法",
    "L2": "类型",
    "L3": "运行时",
    "L4": "模块/导入",
    "L5": "后端差异",
}

CODE_PATTERN = re.compile(r"L[1-5]\d{3}")

_STAGES = ("词法", "语法", "类型", "运行时", "模块", "代码生成")


@dataclass(frozen=True)
class Rule:
    """一条错误码规则。

    前 7 个字段是任务卡固定的 ``Rule(code, title, pattern, stage, hint,
    fixes, candidates)`` 签名；后面的字段都有默认值，属于本卡的增强元数据。
    ``source`` 是出处（文档路径:行号 或 代码路径:行号），不是猜测。
    """

    code: str
    title: str
    pattern: str
    stage: str
    hint: str
    fixes: Sequence[str]
    candidates: Sequence[str]
    severity: str = "error"
    provisional: bool = True
    docs: str = "docs/错误码规范.md"
    source: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "fixes", tuple(self.fixes))
        object.__setattr__(self, "candidates", tuple(self.candidates))
        if not CODE_PATTERN.fullmatch(self.code):
            raise ValueError(f"错误码格式必须是 L[1-5]NNN，收到 {self.code!r}")
        if CODE_SEGMENTS.get(self.code[:2]) is None:
            raise ValueError(f"未知码段：{self.code[:2]}")
        if self.severity not in SEVERITIES:
            raise ValueError(f"severity 非法：{self.severity!r}")
        if self.stage not in _STAGES:
            raise ValueError(f"stage 必须是 {_STAGES} 之一，收到 {self.stage!r}")
        if len(self.fixes) > MAX_FIXES:
            raise ValueError(f"{self.code} fixes 超过 {MAX_FIXES} 条")
        if not self.source:
            raise ValueError(f"{self.code} 缺少 source 出处")
        try:
            re.compile(self.pattern)
        except re.error as exc:
            raise ValueError(f"{self.code} 正则非法：{exc}") from exc


# ---------------------------------------------------------------------------
# 码表：19 条（≥14），按码段分组。每条都带 # source 注释 + source 字段。
# ---------------------------------------------------------------------------
RULES: Tuple[Rule, ...] = (
    # ---------------------------------------------------------------- L1 词法/语法
    # source: docs/AI编程指南.md:531-542（六、错误 1：用 def/function 定义函数）
    Rule(
        code="L1001",
        title="用 def/function 定义函数",
        pattern=r"\b(?:def|function)\b",
        stage="语法",
        hint="光明用「段落」定义函数，def / function 不是本语言的关键字。",
        fixes=[
            "把 `def 名(参数):` 改成 `段落 名 接收 参数：`",
            "函数体返回值用「返回」，不用 return",
        ],
        candidates=["段落 加法 接收 甲, 乙：", "    返回 甲 + 乙"],
        source="docs/AI编程指南.md:531-542",
    ),
    # source: docs/AI编程指南.md:544-555（六、错误 2：用 if/for/while）
    Rule(
        code="L1002",
        title="用英文控制流关键字 if/for/while",
        pattern=r"\b(?:if|for|while)\b(?=[\s(:])",
        stage="语法",
        hint="控制流关键字是中文：如果 / 当 / 遍历；英文关键字不会被识别。",
        fixes=[
            "`if 条件:` 改成 `如果 条件：`",
            "`while 条件:` 改成 `当 条件：`，`for x in xs:` 改成 `遍历 x 于 xs：`",
        ],
        candidates=["如果 x > 0：", "    打印(x)", "遍历 项 于 列表："],
        source="docs/AI编程指南.md:544-555",
    ),
    # source: docs/AI编程指南.md:96（2.2 运算符）、:570-579（六、错误 4）
    Rule(
        code="L1003",
        title="逻辑运算符写成 && / || / !",
        pattern=r"&&|\|\||(?<![!=<>])!(?![=])",
        stage="语法",
        hint="光明没有 && / || / !，逻辑运算用「且」「或」「非」；!= 是合法比较符，不算误用。",
        fixes=[
            "`&&` 改成「且」，`||` 改成「或」，单目 `!` 改成「非」",
            "保留 `!=` / `>=` / `<=`，它们本身就是合法运算符",
        ],
        candidates=["如果 a > 0 且 b > 0 或 非 c：", "设 不等 为 a != b"],
        source="docs/AI编程指南.md:96,570-579",
    ),
    # source: docs/AI编程指南.md:114（2.3 控制流：不支持 ? :）、src/parser_stmt.py:3517
    Rule(
        code="L1004",
        title="使用 C 风格三元表达式 ?:",
        pattern=r"\?[^?\n]{0,24}:",
        stage="语法",
        hint="光明不支持 `条件 ? 真值 : 假值`，三元写成「真值 如果 条件 否则 假值」。",
        fixes=[
            "`a ? b : c` 改成 `b 如果 a 否则 c`",
            "或用完整的 `如果 条件：… 否则：…` 语句块",
        ],
        candidates=["设 结果 为 大值 如果 甲 > 乙 否则 小值", "如果 甲 > 乙："],
        source="docs/AI编程指南.md:114；src/parser_stmt.py:3517",
    ),
    # source: docs/AI编程指南.md:611-618（六、错误 8）、:924-925（B4 字符串字面量）
    Rule(
        code="L1005",
        title="字符串用单引号",
        pattern=r"单引号|single quote",
        stage="词法",
        hint="字符串字面量统一用双引号；部分版本/后端对单引号解析失败。",
        fixes=[
            "把 `'hello'` 改成 `\"hello\"`",
            "插值串用 `f\"你好 {名}\"`（v0.4+）",
        ],
        candidates=['设 s 为 "hello"', '设 问候 为 f"你好 {名}"'],
        severity="warning",  # 文档写「部分版本不支持」，linter I007 是提示级，不升级
        source="docs/AI编程指南.md:611-618,924-925",
    ),
    # source: src/keywords.py:641-685（LP-D-004 保留字误用作标识符）、docs/AI编程指南.md:568
    Rule(
        code="L1006",
        title="保留字/关键字冲突：当标识符用",
        pattern=r"是保留字.*不可作标识符",
        stage="词法",
        hint="真/假/空 等是值类型保留字，不可作变量名、下标名或函数名；作值使用是合法的。",
        fixes=[
            "把作变量名的保留字换成别的名字，例如 `设 空值 为 空`",
            "对照 `src/keywords.py` 的常用保留字清单逐个避开",
        ],
        candidates=["设 标志 为 真", "设 空值 为 空"],
        source="src/keywords.py:641-685；docs/AI编程指南.md:568",
    ),
    # source: src/parser_stmt.py:4519-4527（T-0277 探针 B / L-013：单行段落体）
    Rule(
        code="L1007",
        title="单行段落体导致后续顶层语句静默空跑",
        pattern=r"单行段落|顶层语句静默空跑|冒号后无 NEWLINE",
        stage="语法",
        hint="单行段落体是合法语法（不是编译期错误），但旧解析器会把后续同缩进顶层语句吞进段落体，产物零输出。",
        fixes=[
            "给段落写多行缩进体，别把 `段落 f(x): 返回 …` 和顶层语句挤在一行",
            "升级到带 allow_single_line 的解析器后，确认 `rc=0` 且顶层打印有输出",
        ],
        candidates=["段落 加倍(x)：", "    返回 x * 2", '打印("END")'],
        severity="warning",  # parser_stmt.py 明写「是合法语法，不是编译期错误」
        source="src/parser_stmt.py:4519-4527",
    ),
    # -------------------------------------------------------------------- L2 类型
    # source: src/errors.py:630-648（ParameterCountError）、src/semantic_analyzer.py:495-500
    Rule(
        code="L2001",
        title="段落实参数量与定义不匹配",
        pattern=r"参数数量(?:错误|不匹配|不一致)|期望\s*\d+\s*个参数.*(?:得到|实际传入)",
        stage="类型",
        hint="调用段落时传入的实参个数必须和段落定义的参数个数一致。",
        fixes=[
            "对照段落定义补齐或删掉多余实参",
            "参数之间用逗号分隔；默认参数可省略",
        ],
        candidates=["段落 加法 接收 甲, 乙：", "设 和 为 加法(1, 2)"],
        source="src/errors.py:630-648；src/semantic_analyzer.py:495-500",
    ),
    # source: docs/AI编程指南.md:557-568（六、错误 3：布尔值用 True/False/None）
    Rule(
        code="L2002",
        title="布尔/空值写成 True/False/None",
        pattern=r"\b(?:True|False|None)\b",
        stage="类型",
        hint="光明的字面量是 真 / 假 / 空，Python 的 True / False / None 会被当成未定义名。",
        fixes=[
            "`True` → 「真」，`False` → 「假」，`None` → 「空」",
            "注意 真/假/空 可作值但不可作变量名（见 L1006）",
        ],
        candidates=["设 标志 为 真", "设 值 为 空"],
        source="docs/AI编程指南.md:557-568",
    ),
    # source: docs/AI编程指南.md:930（B5 类与默认参数）
    Rule(
        code="L2003",
        title="默认参数用可变容器或空格等号",
        pattern=r"默认参数.*(?:\[|\{)|(?:列表|字典).*默认参数.*(?:拒绝|不支持)|默认参数用 ASCII",
        stage="类型",
        hint="默认参数只支持标量字面量和「空」，且用 ASCII `=`（不带空格）；可变默认值要在函数体内判空后创建。",
        fixes=[
            "`段落 f(列表 = [])` 改成在函数体内 `设 列表 为 空; 如果 列表 == 空: 设 列表 为 []`",
            "默认参数写成 `超时值=5.0`，不要写成 `超时值 = 5.0`",
        ],
        candidates=["段落 f(a, b = 0, 标记 = 假):", "设 列表 为 []"],
        source="docs/AI编程指南.md:930,1478",
    ),
    # ------------------------------------------------------------------ L3 运行时
    # source: antlrparser/interpreter_core.py:609,996；src/errors.py:66；src/enhanced_errors.py:89
    Rule(
        code="L3001",
        title="列表索引越界",
        pattern=r"列表索引越界|索引.*越界|IndexError",
        stage="运行时",
        hint="光明列表索引从 0 开始，长度为 N 的列表最大下标是 N-1。",
        fixes=[
            "访问前用 `长(列表)` 或 `列表长度(列表)` 检查边界",
            "确认下标是从 0 开始而不是从 1 开始",
        ],
        candidates=["如果 下标 < 长(列表)：", "    打印(列表[下标])"],
        source="antlrparser/interpreter_core.py:609,996；src/errors.py:66；src/enhanced_errors.py:89",
    ),
    # source: docs/tools.md:135（暗坑：列表索引赋值）、docs/AI编程指南.md:1480,1513（L-123 双层下标）
    Rule(
        code="L3002",
        title="索引/下标赋值写法不生效",
        pattern=r"索引赋值|下标赋值|\[[^\]]+\]\s*=",
        stage="运行时",
        hint="下标赋值必须写成 `设 容器[键] 为 值`；直接 `容器[键] = 值` 或双层下标赋值会静默失败。",
        fixes=[
            "改成 `设 己.表[k] 为 v` 形式（保留「设 … 为 …」外壳）",
            "双层路径 `甲[k1][k2] = v` 要逐层取中转容器再写回",
        ],
        candidates=["设 己.表[k] 为 v", "设 当前[键] 为 {}"],
        severity="warning",  # docs/tools.md 归为「暗坑」，是静默行为不是抛出的 error
        source="docs/tools.md:135；docs/AI编程指南.md:1480,1513",
    ),
    # source: docs/STDLIB_REFERENCE.md:109-112（❌ 字典没有的方法 / 置空软删除陷阱）
    Rule(
        code="L3003",
        title="字典置空不等于删键（软删除陷阱）",
        pattern=r"置空|不删键|软删除|字典包含键.*仍为真",
        stage="运行时",
        hint="`设 字典[键] 为 空` 只把值转成空，键仍在；`字典包含键()` 依旧返回真。",
        fixes=[
            "要真删键用 `字典删除(映射, 键)` 或 `字典弹出(映射, 键)`",
            "取值处补判空，或改用 `字典获取(映射, 键, 默认)` 一步兜底",
        ],
        candidates=['字典删除(甲, "旧键")', '设 值 为 字典获取(甲, "键", 0)'],
        severity="warning",  # 文档是 ⚠️ 陷阱提示，运行期不抛错
        source="docs/STDLIB_REFERENCE.md:109-112",
    ),
    # source: docs/AI编程指南.md:939-960（B7 闭包不能重绑外层变量 L-098）、:1479
    Rule(
        code="L3004",
        title="闭包内重绑外层变量不生效",
        pattern=r"闭包.*(?:重绑|外层变量)|L-098",
        stage="运行时",
        hint="闭包里的 `设 计数 为 …` 声明的是新局部变量，外层数值变量不会被改写。",
        fixes=[
            "跨闭包共享状态改用模块级字典/列表原地修改",
            "用 `字典设置(状态, \"计数\", 字典获取(状态, \"计数\", 0) + 1)` 模式",
        ],
        candidates=['设 全局状态 为 {"计数": 0}', '字典设置(全局状态, "计数", 1)'],
        severity="warning",  # 静默不生效，不是抛出的 error
        source="docs/AI编程指南.md:939-960,1479",
    ),
    # ---------------------------------------------------------------- L4 模块/导入
    # source: src/enhanced_errors.py:180-190,876-893（LP-D-002 未定义名 → 缺导入）
    Rule(
        code="L4001",
        title="缺导入：stdlib 导出名被当成未定义变量",
        pattern=r"该函数来自『.*?』模块|请在文件顶部加一行：从|缺导入|未导入|缺少导入",
        stage="模块",
        hint="名字本身存在，只是属于某个 stdlib 模块；不要误报成「先定义变量」。",
        fixes=[
            "按提示在文件顶部补 `从 <模块> 导入 <名字>`",
            "全局内置（如 打印 / 长 / 字符串）无需导入，直接可用",
        ],
        candidates=["从 字符串处理 导入 子串位置", "从 内置核心列表 导入 列表获取"],
        source="src/enhanced_errors.py:180-190,876-893",
    ),
    # source: docs/AI编程指南.md:645-660（六、错误 11/12：英文模块名、print）
    Rule(
        code="L4002",
        title="用英文模块名或英文内置名",
        pattern=r"从\s+math\s+导入|\bprint\s*\(|英文模块名|没有 math 模块",
        stage="模块",
        hint="标准库模块名与内置函数名是中文：`数学` / `平方根`，输出用 `打印`。",
        fixes=[
            "`from math import sqrt` → `从 数学 导入 平方根`",
            "`print(...)` → `打印(...)`",
        ],
        candidates=["从 数学 导入 平方根", '打印("hello")'],
        source="docs/AI编程指南.md:645-660",
    ),
    # ---------------------------------------------------------------- L5 后端差异
    # source: src/llvm/codegen_typed.py:6827-6853（_FALLBACK_HINT / _reject_unsupported_*）
    Rule(
        code="L5001",
        title="原生后端暂不支持该语句/表达式",
        pattern=r"原生后端暂不支持",
        stage="代码生成",
        hint="原生腿（--backend native / llvm-typed）能力边界；报错文本自带回退指引，不要吞掉。",
        fixes=[
            "按报错里的回退指引改用转译后端 `python -m cli.light_unified run`",
            "开发调试一律先用默认 SRC 后端跑通，再考虑原生编译分发",
        ],
        candidates=["python -m cli.light_unified run 文件.light"],
        source="src/llvm/codegen_typed.py:2244,6350,6827-6853",
    ),
    # source: docs/tools.md:130-138（暗坑提醒表：类系统 SRC 后端 → 需切换 LLVM 后端）
    Rule(
        code="L5002",
        title="类系统在 SRC 后端不兼容",
        pattern=r"类系统.*(?:后端|LLVM|SRC)|需切换 LLVM 后端",
        stage="代码生成",
        hint="类系统在 SRC 后端与 LLVM/原生后端的能力不同；同一份类代码换后端可能行为不一致。",
        fixes=[
            "跑类相关代码时切到 LLVM 后端，或先确认当前后端支持该类特性",
            "换后端后重跑类系统用例，不要假定 SRC 的结果可平移",
        ],
        candidates=["light ai check 文件.light"],
        severity="warning",  # docs/tools.md 归为「暗坑」而非编译错误
        source="docs/tools.md:130-138；docs/class_system_design.md:7",
    ),
    # source: docs/AI编程指南.md:919-922（B3 原生腿限制：容器跨段变异不生效）
    Rule(
        code="L5003",
        title="原生腿容器跨段变异不生效",
        pattern=r"跨段变异.*不生效|值拷贝.*不生效|原生腿.*(?:容器|列表|字典).*值拷贝",
        stage="代码生成",
        hint="转译腿是 Python 引用语义，原生腿是值拷贝；把列表/字典传进段落再追加，原生腿看不到改动。",
        fixes=[
            "改用类持有容器：`己.数据.追加(项)`",
            "或显式返回新容器并由调用方接住",
        ],
        candidates=["类 栈容器：", "    己.数据.追加(项)"],
        severity="warning",  # 行为差异，不抛错
        source="docs/AI编程指南.md:919-922",
    ),
)


_BY_CODE: Dict[str, Rule] = {rule.code: rule for rule in RULES}


def get(code: str) -> Optional[Rule]:
    """按错误码精确查询规则；不存在返回 ``None``（大小写敏感）。"""
    return _BY_CODE.get(code)


def all_codes() -> Tuple[str, ...]:
    """按码表顺序返回全部错误码。"""
    return tuple(rule.code for rule in RULES)


def duplicate_codes(rules: Sequence[Rule]) -> List[str]:
    """找出重复出现的错误码，保持首次重复的顺序。

    抽成函数是为了让「同一错误码不得出现在两条规则里」这条判据可被测试
    反向验证：拿一份人为注入重复码的规则列表调用它，必须报出重复项。
    """
    seen = set()
    dups: List[str] = []
    for rule in rules:
        if rule.code in seen and rule.code not in dups:
            dups.append(rule.code)
        seen.add(rule.code)
    return dups


def explain(message: str, stage: Optional[str] = None) -> Optional[Diagnostic]:
    """把一条报错文本解释成结构化诊断；未命中返回 ``None``。

    参数
    ----
    message
        编译器/解释器给出的**原始报错文本**；原样保留进 ``Diagnostic.message``。
    stage
        可选过滤器。给了就只在该 stage 的规则里匹配，避免同一段文本被别的
        阶段规则抢走；不给则按 :data:`RULES` 顺序全表匹配，取第一条命中。

    说明
    ----
    * 位置信息不从文本里猜：``line``/``column`` 恒为 0（位置未知）。
      需要精确坐标时，由调用方（T-0317/T-0318）把真实坐标填进返回值。
    * ``provisional=True``：文本正则推断，尚未与内部异常对象绑定。
    * 没有任何「兜底码」——匹配不上就诚实返回 ``None``。
    """
    if not isinstance(message, str) or not message:
        return None
    for rule in RULES:
        if stage is not None and rule.stage != stage:
            continue
        if re.search(rule.pattern, message):
            return Diagnostic(
                code=rule.code,
                severity=rule.severity,
                stage=rule.stage,
                line=0,
                column=0,
                message=message,
                hint=rule.hint,
                fixes=list(rule.fixes),
                candidates=list(rule.candidates),
                provisional=rule.provisional,
                docs=rule.docs,
            )
    return None


def to_legacy_entry(diag: Diagnostic):
    """Diagnostic → ``src.errors.ErrorEntry``，保证文本输出逐字不变。

    只搬运 ``stage / message / line / column / fixes`` 五个字段：

    * ``fixes`` → ``fix_suggestions``（这也是 ``ErrorEntry.format()`` 唯一
      会用到的建议字段）；
    * 不传 ``source_line`` / ``exception``，让它们保持 dataclass 默认值；
    * **不把 code 拼进 message**——错误码由 T-0318 的 JSON 输出承载，
      塞进文本会破坏「现有文本输出逐字不变」这条兼容承诺。

    导入放在函数内，避免仅用码表时被迫加载整个 ``src.errors``。
    """
    try:
        from src.errors import ErrorEntry
    except ImportError:  # 以 src/ 本身为 sys.path 根的用法
        from errors import ErrorEntry  # type: ignore[no-redef]

    return ErrorEntry(
        stage=diag.stage,
        message=diag.message,
        line=diag.line,
        column=diag.column,
        fix_suggestions=list(diag.fixes),
    )
