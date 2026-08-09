#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断训练 loss=0 的根因"""

import json
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

SYSTEM_PROMPT = (
    "你是光明（LightLang）编程语言 v3.2 的翻译专家。"
    "光明是一种中文编程语言，使用中文关键字。"
    "你的任务是将 Python 代码翻译为光明 v3.2 代码。\n"
    "关键规则：\n"
    "- 赋值: 设 x 为 10 (数字/字符串/布尔/None/列表/字典均统一使用 设)\n"
    "- 段落定义: 段落 名 接收 参数：\n"
    "- 条件: 如果 / 否则若 / 否则：\n"
    "- 循环: 遍历 i 于 0至N： / 当 条件：\n"
    "- 运算: 加上/减去/乘以/除以/取余/幂\n"
    "- 比较: 等于/不等于/大于/小于/大于等于/小于等于\n"
    "- 逻辑: 且/或/非\n"
    "- 布尔: 真/假/空\n"
    "- 跳转: 跳出(break)/跳过(continue)/返回(return)\n"
    "- 长度: 用 len() 而非 长度()\n"
    "- 列表索引赋值: lst[0] = 10\n"
    "- 打印: 打印(x)\n"
    "- f-string: 直接保留 f\"...{var}...\" 格式, f-string内的变量名保持原样不翻译\n"
    "- 列表推导: [expr 遍历 var 之 列表 若 条件]\n"
    "- 字典推导: {k: v 遍历 k, v 之 d.items() 若 条件}\n"
    "- 集合推导: {expr 遍历 var 之 列表 若 条件}\n"
    "- 类定义: 类 名：\n"
    "- 类属性: 属性 名\n"
    "- 类构造: 构造 接收 参数：\n"
    "- 类方法: 段落 名：\n"
    "- 类继承: 类 子类 继承 父类：\n"
    "- 父类调用: 父.方法名(参数)\n"
    "- self引用: 己.属性 / 己.方法()\n"
    "- 访问控制: 公有/私有/保护 属性\n"
    "- 静态方法: 静态 段落 名 接收 参数：\n"
    "- 类方法: 类方法 段落 名：\n"
    "- 特性getter: 特性 段落 名：\n"
    "- 特性setter: 段落 set_名 接收 value：\n"
    "- 异常处理: 尝试：/捕获 异常类型 [e]：/最终：\n"
    "- 抛出异常: 抛出 \"message\" / 抛出 新建 异常类型(\"msg\")\n"
    "- with语句: 使用 资源 为 变量：\n"
    "- lambda: 接收 参数：返回 表达式\n"
    "- 高阶函数: 筛选(谓词, 数据) / 映射(函数, 数据) / reduce(函数, 数据)\n"
    "- 排序: sorted(数据, key=接收 x：返回 x[0])\n"
    "- 文件读取: 读取文件(\"file.txt\")\n"
    "- 文件写入: 打开文件(\"file.txt\", \"w\")\n"
    "- 装饰器: @标注名 标注\n"
    "- 变量名保持: 变量名、函数名、类名、方法名保持英文原样，不翻译为中文\n"
    "- 复合赋值: x += y -> 设 x 为 x 加上 y; x -= y -> 设 x 为 x 减去 y; x *= y -> 设 x 为 x 乘以 y; x /= y -> 设 x 为 x 除以 y\n"
    "- 负数字面量: -1, -100 等负数保持原样，返回 -1 而非 返回 减 1\n"
    "- 整除运算: // 翻译为 整除; / 翻译为 除以\n"
    "- 取余运算: % 翻译为 取余\n"
    "- 幂运算: ** 翻译为 幂\n"
    "- 方法调用: 对象方法调用保持原样，如 s.upper(), lst.append(x), d.get(key) 不翻译方法名\n"
    "- break/continue: break -> 跳出; continue -> 跳过; 不可混用 返回 替代 break\n"
    "- 多返回值: return a, b 保持原样; x, y = func() 分别赋值\n"
    "- 产出: yield -> 产出; yield from -> 产出自\n"
    "- 异常类型: 捕获具体异常类型，如 捕获 ZeroDivisionError 为 e\n"
    "只输出光明代码，不要解释。"
)

def main():
    from transformers import AutoTokenizer

    model_path = os.path.join(_SCRIPT_DIR, "model_cache", "qwen2.5-0.5b")
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load dataset
    dataset_path = os.path.join(_SCRIPT_DIR, "sft_dataset_enhanced.jsonl")
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = [json.loads(l) for l in f if l.strip()]

    print(f"Total samples: {len(data)}")

    max_len = 256
    over_count = 0
    zero_output_count = 0

    for i, item in enumerate(data):
        instruction = item.get("instruction", "")
        code_input = item.get("input", "")
        output = item.get("output", "")

        user_msg = f"{instruction}\n\nPython 代码：\n{code_input}" if code_input else instruction
        prompt_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        prompt_text = tokenizer.apply_chat_template(
            prompt_messages, tokenize=False, add_generation_prompt=True
        )
        prompt_ids = tokenizer(
            prompt_text, truncation=True, max_length=max_len, return_tensors=None
        )["input_ids"]

        full_messages = prompt_messages + [{"role": "assistant", "content": output}]
        full_text = tokenizer.apply_chat_template(
            full_messages, tokenize=False, add_generation_prompt=False
        )
        full_ids = tokenizer(
            full_text, truncation=True, max_length=max_len, return_tensors=None
        )["input_ids"]

        prompt_len = len(prompt_ids)
        full_len = len(full_ids)
        # output tokens = tokens after prompt that are not -100
        effective_output = full_len - min(prompt_len, full_len)

        if prompt_len >= max_len:
            over_count += 1
        if effective_output <= 0:
            zero_output_count += 1

        if i < 10:
            print(f"  [{i}] prompt={prompt_len}, full={full_len}, output_tokens={effective_output}, over_256={prompt_len >= max_len}")

    print(f"\n=== Summary ===")
    print(f"Samples with prompt >= max_len(256): {over_count}/{len(data)} ({over_count/len(data)*100:.1f}%)")
    print(f"Samples with 0 output tokens (no loss): {zero_output_count}/{len(data)} ({zero_output_count/len(data)*100:.1f}%)")

    # Also check with max_len=512
    max_len = 512
    over_count_512 = 0
    zero_output_count_512 = 0
    for item in data:
        instruction = item.get("instruction", "")
        code_input = item.get("input", "")
        user_msg = f"{instruction}\n\nPython 代码：\n{code_input}" if code_input else instruction
        prompt_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        prompt_text = tokenizer.apply_chat_template(
            prompt_messages, tokenize=False, add_generation_prompt=True
        )
        prompt_ids = tokenizer(
            prompt_text, truncation=True, max_length=max_len, return_tensors=None
        )["input_ids"]
        full_messages = prompt_messages + [{"role": "assistant", "content": output}]
        full_text = tokenizer.apply_chat_template(
            full_messages, tokenize=False, add_generation_prompt=False
        )
        full_ids = tokenizer(
            full_text, truncation=True, max_length=max_len, return_tensors=None
        )["input_ids"]
        prompt_len = len(prompt_ids)
        full_len = len(full_ids)
        effective_output = full_len - min(prompt_len, full_len)
        if prompt_len >= max_len:
            over_count_512 += 1
        if effective_output <= 0:
            zero_output_count_512 += 1

    print(f"\nWith max_len=512:")
    print(f"  Over: {over_count_512}/{len(data)} ({over_count_512/len(data)*100:.1f}%)")
    print(f"  Zero output: {zero_output_count_512}/{len(data)} ({zero_output_count_512/len(data)*100:.1f}%)")

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
