#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 stdlib/ 与 spec/ 导出（中文需求, 光明代码）配对语料。

产物（默认 build/corpus/，该目录已在 .gitignore 中）：
    light_sft.jsonl   每行一条配对样本
    manifest.json     条数、level/source 分布、可运行条数、生成器版本

设计要点：
    * 纯标准库，不联网、不调用任何模型 API；
    * 素材只取 stdlib/*.light 顶层「段落」定义，关键字与导出清单取 spec/light.spec.json；
    * 超过 60 行（含签名）的样本一律跳过；
    * 需求侧由模块主题、函数名动宾结构、参数名合成，并用中文同义词改写，
      保证 prompt 不含 code 中出现的光明关键字与 ASCII 标识符（防泄题）；
    * runnable 表示样本是否不依赖外部资源且不引用未知标识符（可在抽样池里送 light check）；
    * 同一份输入重复运行时输出逐字节一致（排序、固定 id、无时间戳）。

用法：
    python tools/gen_ai_corpus.py --out build/corpus/ --min 500 --stats
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

GENERATOR_VERSION = "1.1.0"
JSONL_NAME = "light_sft.jsonl"
MANIFEST_NAME = "manifest.json"
DEFAULT_OUT = "build/corpus"
DEFAULT_MIN = 500
MAX_SAMPLE_LINES = 60
LEVELS = ("L1", "L2", "L3", "L4")

REPO_ROOT = Path(__file__).resolve().parents[1]
STDLIB_DIR = REPO_ROOT / "stdlib"
SPEC_PATH = REPO_ROOT / "spec" / "light.spec.json"

RE_PARA = re.compile(
    r"^(?P<indent>[ \t]*)段落\s+(?P<name>[^\s(:]+)\s*"
    r"(?P<params>\([^)]*\))?\s*:\s*(?P<tail>.*)$"
)
RE_ASCII_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")
RE_CJK_IDENT = re.compile(r"[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9_]*")
RE_COMMENT = re.compile(r"#.*$")
RE_STRING = re.compile(r'"[^"\n]*"')
RE_SENSITIVE = re.compile(
    r"(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{16,}|AKIA[A-Z0-9]{12,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._-]{20,}"
    r"|(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3})"
)

# 依赖外部资源、无法离线验证的实现特征
RISKY_TOKENS = (
    "读取文件", "写入文件", "创建目录", "文件存在", "列目录", "删除文件",
    "HTTP", "http", "URL", "请求", "客户端", "服务器", "网页", "套接字",
    "进程", "环境变量", "命令行", "终端", "FFI", "网络", "socket",
    "子进程", "代理", "密码", "凭据", "下载", "上传",
)

# 单字也容易泄题的结构性关键字（用于 prompt 检查）
STRUCTURAL_SINGLE_KEYWORDS = ("设", "若", "且", "与", "为", "从", "在", "的", "是", "空", "长")

# 函数名动词 → 需求侧同义动词短语（按长度降序匹配）
VERB_PHRASES: Tuple[Tuple[str, str], ...] = tuple(
    sorted(
        (
            ("居中填充", "居中补齐"), ("去除空白", "清除空格"), ("左填充", "左侧补齐"),
            ("右填充", "右侧补齐"), ("逐行读", "逐行取出"), ("最大值", "找出最大项"),
            ("最小值", "找出最小项"), ("标准差", "算出标准差"), ("相关系数", "算出相关系数"),
            ("字符串长度", "统计文本规模"), ("缓存清空", "清空缓存"),
            ("定时缓存刷新", "定时刷新缓存"), ("定时缓存清除", "定时清理缓存"),
            ("清除缓存", "清空缓存"), ("缓存大小", "统计缓存规模"),
            ("深度相等", "比较深层内容是否一致"), ("以子串开头", "判断片段是否位于开头"),
            ("以子串结尾", "判断片段是否位于结尾"), ("以开头", "判断片段是否位于开头"),
            ("以结尾", "判断片段是否位于结尾"), ("提取文本中的数字", "挑出文本里数字"),
            ("读取", "取出"), ("写入", "保存"), ("排序", "排列"), ("筛选", "挑选"),
            ("过滤", "滤出"), ("查找", "定位"), ("搜索", "检索"), ("替换", "换成"),
            ("编码", "编成编码文本"), ("解码", "还原成原文"), ("解析", "拆解"),
            ("序列化", "整理成文本"), ("合并", "拼合"), ("分割", "切分"),
            ("拆分", "切分"), ("拼接", "接合"), ("连接", "接合"), ("计数", "统计数量"),
            ("求和", "求合计"), ("验证", "核对"), ("校验", "核对"), ("断言", "核对"),
            ("判断", "判定"), ("比较", "对比"), ("转换", "换成"), ("转成", "换成"),
            ("格式化", "整理"), ("美化", "整理"), ("生成", "产出"), ("创建", "建立"),
            ("新建", "建立"), ("添加", "追加"), ("追加", "追加"), ("删除", "移除"),
            ("清空", "清空"), ("清除", "清除"), ("去除", "清除"), ("去掉", "移除"),
            ("获取", "取得"), ("设置", "配置"), ("加载", "载入"), ("保存", "存档"),
            ("遍历", "逐个处理"), ("截取", "切出"), ("提取", "挑出"), ("反转", "颠倒"),
            ("去重", "去掉重复项"), ("包含", "判断是否含有"), ("转大写", "变成大写字母"),
            ("转小写", "变成小写字母"), ("转字符串", "换成文本"), ("填充", "补齐"),
            ("截断", "裁短"), ("打印", "显示"), ("输出", "呈现"), ("计算", "算出"),
            ("求最大", "找最大项"), ("求最小", "找最小项"), ("分词", "切词"),
            ("随机", "任意取值"), ("日期", "日期"), ("农历", "传统历法"),
            ("拼音", "读音"), ("对齐", "按宽度对齐"), ("缩进", "调整缩进"),
            ("压缩", "压缩"), ("解压", "展开"), ("加密", "加密"), ("解密", "还原密文"),
            ("哈希", "算出摘要"), ("重复", "重复"), ("转", "换成"), ("拼", "接合"),
            ("取", "取出"), ("找", "找出"), ("判", "判定"), ("比", "对比"),
            ("求", "算出"), ("按", "按规则处理"), ("检查", "检查"),
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
)

# 名词性函数名的需求改写规则（优先于动词拆分）
NOUN_PATTERNS: Tuple[Tuple[re.Pattern, str], ...] = (
    (re.compile(r"^(.+)最大值$"), "找出{obj}最大项"),
    (re.compile(r"^(.+)最小值$"), "找出{obj}最小项"),
    (re.compile(r"^(?:样本)?标准差$"), "算出样本波动幅度"),
    (re.compile(r"^方差$"), "算出数值波动幅度"),
    (re.compile(r"^均值$"), "算出平均值"),
    (re.compile(r"^中位数$"), "算出中间位置数值"),
    (re.compile(r"^(.+)长度$"), "统计{obj}规模"),
    (re.compile(r"^(.+)大小$"), "统计{obj}规模"),
    (re.compile(r"^(.+)数量$"), "统计{obj}条数"),
    (re.compile(r"^(.+)哈希$"), "算出{obj}摘要"),
    (re.compile(r"^(.+)类型$"), "判断{obj}种类"),
    (re.compile(r"^(.+)转JSON文件$"), "把{obj}存成结构化文本文件"),
    (re.compile(r"^(.+)转JSON$"), "把{obj}整理成结构化文本"),
    (re.compile(r"^(.+)装饰器$"), "提供{obj}增强能力"),
)

# 对象词的中文化改写，避免出现代码里的关键字/标识符
OBJECT_REPLACEMENTS: Tuple[Tuple[str, str], ...] = tuple(
    sorted(
        (
            ("字符串", "文本"), ("子串", "片段"), ("长度", "数量"), ("空白", "空格"),
            ("数据组", "数据表"), ("代码组", "编号表"), ("城市代码", "城市编号"),
            ("数组", "序列"), ("列表", "序列"), ("字典", "键值表"), ("集合", "集合"),
            ("大写", "大写字母"), ("小写", "小写字母"), ("数字字符", "数字字符"),
            ("JSONL", "结构化文本"), ("JSON", "结构化文本"), ("HTML", "网页标记"),
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
)

# 模块主题 → 五类 source
SOURCE_RULES: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    (("HTTP", "网络", "套接字", "服务器", "客户端", "代理", "URL", "协议"), "网络"),
    (("文件", "进程", "终端", "系统", "FFI", "农历", "行政区划", "时间"), "系统"),
    (("JSON", "CSV", "数据", "编码", "Base64", "压缩", "缓存", "池", "数据库"), "数据"),
    (("字符串", "文本", "正则", "re", "中文", "拼音", "分词", "字符"), "文本"),
    (("数学", "排序", "集合", "列表", "字典", "结构", "位", "算法", "哈希"), "算法"),
)
SOURCE_CLASSES = ("文本", "数据", "算法", "系统", "网络")

CONTEXT_BY_SOURCE = {
    "文本": "一段中文文本",
    "数据": "一组结构化内容",
    "算法": "一组数值或序列",
    "系统": "本机环境里的内容",
    "网络": "一次远端交互",
}

# 10 个需求句式模板；{task} 为动宾短语，{ctx} 为语境描述
PROMPT_TEMPLATES: Tuple[str, ...] = (
    "请给出代码，完成这项任务：{ctx}，{task}。",
    "任务目标：{ctx}，{task}。",
    "需要一段代码：{ctx}，{task}。",
    "请提供示例代码：{ctx}，{task}。",
    "目标：{ctx}，{task}，可直接使用。",
    "这项任务需要代码支持：{ctx}，{task}。",
    "示例需求：{ctx}，{task}。",
    "请提供一段代码，{ctx}，{task}，并保证产物符合预期。",
    "任务：{ctx}，{task}，用光明语言完成。",
    "请给出可直接运行的代码：{ctx}，{task}。",
)

# 泄题词兜底同义替换
SANITIZE_MAP = {
    "的": "", "是": "属于", "在": "位于", "从": "由", "到": "至",
    "与": "和", "且": "同时", "为": "作为", "设": "配置", "若": "需要时",
    "长": "大小", "空": "无内容", "打印": "显示", "返回": "给出",
    "读取": "取出", "写入": "保存", "排序": "排列", "筛选": "挑选",
    "遍历": "逐个处理", "生成": "产出", "输出": "呈现", "导入": "引入",
    "导出": "提供", "模块": "部件", "类型": "种类", "函数": "功能",
    "实现": "完成", "使用": "采用", "定义": "声明", "情况": "场景",
}


class SpecInfo:
    """spec/light.spec.json 中与语料生成相关的信息。"""

    def __init__(self, raw: dict) -> None:
        self.version: str = str(raw.get("version", ""))
        self.keywords: Tuple[str, ...] = tuple(
            str(item.get("字", "")) for item in raw.get("keywords", []) if item.get("字")
        )
        self.multi_keywords = tuple(k for k in self.keywords if len(k) >= 2)
        self.exports: set[str] = set()
        stdlib = raw.get("stdlib", {}) or {}
        for module in stdlib.get("模块", []) or []:
            for entry in module.get("导出", []) or []:
                name = str(entry.get("名字", "")).strip()
                if name:
                    self.exports.add(name)


def load_spec(path: Path = SPEC_PATH) -> SpecInfo:
    with path.open("r", encoding="utf-8") as handle:
        return SpecInfo(json.load(handle))


def indent_width(text: str) -> int:
    expanded = text.expandtabs(4)
    return len(expanded) - len(expanded.lstrip())


def strip_inline_comment(line: str) -> str:
    if "#" not in line:
        return line
    return RE_COMMENT.sub("", line).rstrip()


def iter_paragraphs(lines: Sequence[str]):
    """产出顶层段落：(start_idx, end_idx_exclusive, name, params)。"""
    for index, raw in enumerate(lines):
        match = RE_PARA.match(raw)
        if not match or match.group("indent"):
            continue
        base = indent_width(raw)
        end = index + 1
        while end < len(lines):
            line = lines[end]
            if not line.strip():
                end += 1
                continue
            if indent_width(line) <= base:
                break
            end += 1
        yield index, end, match.group("name"), (match.group("params") or "").strip()


def build_code(lines: Sequence[str], start: int, end: int) -> str:
    """签名行 + 去注释段体，保留原始缩进。"""
    body: List[str] = []
    for line in lines[start:end]:
        cleaned = strip_inline_comment(line)
        if cleaned.strip():
            body.append(cleaned.rstrip())
    while body and not body[-1].strip():
        body.pop()
    return "\n".join(body)


def parse_params(params: str) -> List[str]:
    inner = params.strip()
    if inner.startswith("(") and inner.endswith(")"):
        inner = inner[1:-1]
    names: List[str] = []
    for part in inner.split(","):
        name = part.strip().split("=")[0].split("等于")[0].strip()
        if name:
            names.append(name)
    return names


def classify_source(file_stem: str) -> str:
    for tokens, label in SOURCE_RULES:
        if any(token in file_stem for token in tokens):
            return label
    return "算法"


def cn_only(text: str) -> str:
    return re.sub(r"[A-Za-z0-9_]+", "", text)


def strip_strings(code: str) -> str:
    return RE_STRING.sub('""', RE_COMMENT.sub("", code))


def free_identifiers(code: str) -> set[str]:
    """在样本内被使用、但既非参数也非局部绑定的标识符。"""
    text = strip_strings(code)
    identifiers = set(RE_CJK_IDENT.findall(text))
    identifiers.update(RE_ASCII_IDENT.findall(text))
    bound: set[str] = set()
    for pattern in (
        r"段落\s+([\u4e00-\u9fffA-Za-z0-9_]+)",
        r"(?:设|定义)\s+([\u4e00-\u9fffA-Za-z0-9_]+)",
        r"遍历\s+([\u4e00-\u9fffA-Za-z0-9_]+)",
        r"对于\s+([\u4e00-\u9fffA-Za-z0-9_]+)",
        r"捕获\s+([\u4e00-\u9fffA-Za-z0-9_]+)",
    ):
        bound.update(re.findall(pattern, text))
    return identifiers - bound


def is_runnable(code: str, params: Sequence[str], spec: SpecInfo) -> bool:
    if any(token in code for token in RISKY_TOKENS):
        return False
    known = set(params)
    known.update(STRUCTURAL_SINGLE_KEYWORDS)
    known.update(spec.keywords)
    known.update(spec.exports)
    text = strip_strings(code)
    ascii_used = set(RE_ASCII_IDENT.findall(text))
    if ascii_used - set(params):
        return False
    unknown = {name for name in free_identifiers(code) if name not in known}
    return not unknown


def assign_level(body_lines: int, control_flow: int) -> str:
    if body_lines <= 5 and control_flow == 0:
        return "L1"
    if body_lines <= 15 and control_flow <= 2:
        return "L2"
    if body_lines <= 35:
        return "L3"
    return "L4"


def banned_tokens_for(code: str, spec: SpecInfo) -> set[str]:
    """prompt 中不允许出现的词：code 内出现的关键字、ASCII 标识符、结构性单字。"""
    banned: set[str] = set()
    for keyword in spec.multi_keywords:
        if keyword and keyword in code:
            banned.add(keyword)
    banned.update(RE_ASCII_IDENT.findall(code))
    for single in STRUCTURAL_SINGLE_KEYWORDS:
        if single in code:
            banned.add(single)
    return banned


def sanitize(text: str, banned: Sequence[str]) -> str:
    banned_set = set(banned)
    result = text
    for token in sorted(banned_set, key=len, reverse=True):
        if token and token in result:
            result = result.replace(token, SANITIZE_MAP.get(token, ""))
    result = re.sub(r"[A-Za-z0-9_]+", "", result)
    result = re.sub(r"\s{2,}", " ", result)
    result = re.sub(r"[，。；]{2,}", "，", result)
    return result.strip(" ，。；")


def rewrite_object(text: str) -> str:
    result = cn_only(text)
    for word, replacement in OBJECT_REPLACEMENTS:
        if word in result:
            result = result.replace(word, replacement)
    return result.strip()


# 需要调整语序的动词短语 → 需求模板
ORDER_TEMPLATES = {
    "统计数量": "统计{obj}条数",
    "求合计": "算出{obj}合计",
    "判断是否含有": "判断{obj}是否含有目标项",
    "找出最大项": "找出{obj}最大项",
    "找出最小项": "找出{obj}最小项",
    "按规则处理": "按规则处理{obj}",
    "逐个处理": "逐个处理{obj}",
}

# 这些动作短语更适合「把 + 对象 + 动作」语序
BA_PHRASES = {
    "排列", "颠倒", "接合", "切分", "对比", "裁短", "补齐", "左侧补齐",
    "右侧补齐", "居中补齐", "按宽度对齐", "调整缩进", "压缩", "展开",
    "加密", "还原密文", "算出摘要", "清除空格",
}


def _phrase_with_object(phrase: str, obj: str) -> str:
    if not obj:
        return phrase
    if phrase in ORDER_TEMPLATES:
        return ORDER_TEMPLATES[phrase].format(obj=obj)
    if phrase in BA_PHRASES:
        return f"把{obj}{phrase}"
    return phrase + obj


def build_task_phrase(name: str, module_stem: str) -> str:
    cleaned = cn_only(name)
    stem = rewrite_object(module_stem)
    if not cleaned:
        return f"完成{stem}相关处理" if stem else "完成一组内容处理"
    for pattern, template in NOUN_PATTERNS:
        match = pattern.match(cleaned)
        if match:
            obj = rewrite_object(match.group(1)) if match.groups() else ""
            return template.format(obj=obj or stem or "内容")
    for word, phrase in VERB_PHRASES:
        if cleaned.startswith(word):
            obj = rewrite_object(cleaned[len(word):])
            return _phrase_with_object(phrase, obj or stem)
        if cleaned.endswith(word) and len(cleaned) > len(word):
            obj = rewrite_object(cleaned[: -len(word)])
            return _phrase_with_object(phrase, obj or stem)
    obj_text = rewrite_object(cleaned)
    if not obj_text:
        return f"完成{stem}相关处理" if stem else "完成一组内容处理"
    return f"完成{obj_text}相关功能"


def build_prompt(name: str, module_stem: str, source: str, code: str, spec: SpecInfo) -> str:
    """合成人话需求；多个模板中取第一条不含禁忌词的版本。"""
    banned = banned_tokens_for(code, spec)
    task = build_task_phrase(name, module_stem)
    context = CONTEXT_BY_SOURCE.get(source, "一段内容")
    for template in PROMPT_TEMPLATES:
        candidate = sanitize(template.format(ctx=context, task=task), banned)
        if len(candidate) < 8:
            continue
        if any(token in candidate for token in banned):
            continue
        if RE_ASCII_IDENT.search(candidate):
            continue
        if not candidate.endswith("。"):
            candidate += "。"
        return candidate
    return ""


def collect_samples(spec: SpecInfo, max_lines: int) -> Tuple[List[dict], Counter]:
    samples: List[dict] = []
    skipped: Counter = Counter()
    for path in sorted(STDLIB_DIR.glob("*.light")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            skipped["读取失败"] += 1
            continue
        module_stem = path.stem
        source_class = classify_source(module_stem)
        rel_source = f"stdlib/{path.name}"
        for start, end, name, params in iter_paragraphs(lines):
            code = build_code(lines, start, end)
            if not code.strip():
                skipped["空段体"] += 1
                continue
            line_count = len(code.splitlines())
            if line_count > max_lines:
                skipped["超过行数上限"] += 1
                continue
            if RE_SENSITIVE.search(code):
                skipped["敏感信息"] += 1
                continue
            prompt = build_prompt(name, module_stem, source_class, code, spec)
            if not prompt:
                skipped["需求合成失败"] += 1
                continue
            param_names = parse_params(params)
            control = sum(
                code.count(token)
                for token in ("如果", "遍历", "当", "尝试", "对于", "循环")
            )
            samples.append(
                {
                    "prompt": prompt,
                    "code": code,
                    "level": assign_level(max(1, line_count - 1), control),
                    "runnable": is_runnable(code, param_names, spec),
                    "source": rel_source,
                    "_start": start,
                    "_path": path.name,
                    "_class": source_class,
                }
            )
    samples.sort(key=lambda item: (item["_path"], item["_start"]))
    return samples, skipped


def finalize(samples: Sequence[dict]) -> List[dict]:
    records: List[dict] = []
    for index, sample in enumerate(samples, start=1):
        code = sample["code"]
        records.append(
            {
                "id": f"L-{index:04d}",
                "prompt": sample["prompt"],
                "code": code,
                "level": sample["level"],
                "source": sample["source"],
                "runnable": sample["runnable"],
                "sha256": hashlib.sha256(code.encode("utf-8")).hexdigest(),
            }
        )
    return records


def write_outputs(
    records: Sequence[dict], out_dir: Path, skipped: Counter, samples: Sequence[dict]
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / JSONL_NAME
    payload = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
    )
    jsonl_path.write_bytes(payload.encode("utf-8"))

    matrix: Dict[str, Dict[str, int]] = {
        level: {name: 0 for name in SOURCE_CLASSES} for level in LEVELS
    }
    for record, sample in zip(records, samples):
        matrix[record["level"]][sample["_class"]] += 1
    by_level = Counter(record["level"] for record in records)
    by_class = Counter(sample["_class"] for sample in samples)
    by_file = Counter(record["source"].split("/")[-1] for record in records)
    runnable_count = sum(1 for record in records if record["runnable"])

    manifest = {
        "generator": "tools/gen_ai_corpus.py",
        "generator_version": GENERATOR_VERSION,
        "count": len(records),
        "runnable": runnable_count,
        "max_lines": MAX_SAMPLE_LINES,
        "by_level": {level: by_level.get(level, 0) for level in LEVELS},
        "by_source_class": {name: by_class.get(name, 0) for name in SOURCE_CLASSES},
        "by_source": dict(sorted(by_file.items())),
        "matrix": matrix,
        "jsonl": JSONL_NAME,
        "jsonl_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "skipped": dict(sorted(skipped.items())),
    }
    (out_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def print_stats(manifest: dict) -> None:
    header = "level | " + " | ".join(f"{name:^8}" for name in SOURCE_CLASSES) + " | 合计"
    print(header)
    print("-" * len(header))
    matrix = manifest["matrix"]
    for level in LEVELS:
        cells = [matrix[level][name] for name in SOURCE_CLASSES]
        total = sum(cells)
        row = [f"{level:5}", *(f"{value:^8}" for value in cells), f"{total:^6}"]
        print(" | ".join(row))
    totals = [sum(matrix[level][name] for level in LEVELS) for name in SOURCE_CLASSES]
    print("-" * len(header))
    print(" | ".join([f"{'合计':5}", *(f"{value:^8}" for value in totals), f"{sum(totals):^6}"]))
    print()
    print(f"条数：{manifest['count']}，可运行：{manifest['runnable']}")
    print("按 level：", manifest["by_level"])


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从 stdlib/ 与 spec/ 生成（中文需求, 光明代码）配对语料"
    )
    parser.add_argument("--out", default=DEFAULT_OUT, help="产物目录，默认 build/corpus/")
    parser.add_argument("--min", type=int, default=DEFAULT_MIN, help="最少条数，默认 500")
    parser.add_argument(
        "--max-lines", type=int, default=MAX_SAMPLE_LINES, help="单样本最大行数，默认 60"
    )
    parser.add_argument("--stats", action="store_true", help="打印 level × source 分布表")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    spec = load_spec()
    samples, skipped = collect_samples(spec, args.max_lines)
    records = finalize(samples)
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    manifest = write_outputs(records, out_dir, skipped, samples)
    if args.stats:
        print_stats(manifest)
    print(f"已生成 {len(records)} 条 → {out_dir / JSONL_NAME}")
    if len(records) < args.min:
        print(
            f"条数不足：{len(records)} < {args.min}（跳过原因：{dict(skipped)}）",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())