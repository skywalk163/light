#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明训练自动完成脚本

监控训练进程，训练完成后自动：
  1. 合并 LoRA 权重到基础模型
  2. 运行推理测试
  3. 生成质量报告

用法：
    python auto_finish.py
"""

import json
import os
import subprocess
import sys
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TRAIN_OUTPUT = os.path.join(_SCRIPT_DIR, "train_output.log")
_TRAIN_ERROR = os.path.join(_SCRIPT_DIR, "train_error.log")


def _find_lora_path():
    """自动检测 LoRA 权重路径，优先 GPU 训练产物，支持多模型"""
    for name in (
        "qwen3.5_2b_light_gpu",
        "qwen2.5_1.5b_light_gpu",
        "qwen2.5_0.5b_light_gpu",
        "qwen2.5_0.5b_light_cpu",
    ):
        p = os.path.join(_SCRIPT_DIR, "output", name, "final")
        if os.path.isdir(p):
            return p
    return os.path.join(_SCRIPT_DIR, "output", "qwen2.5_0.5b_light_gpu", "final")


def _find_merged_path():
    """自动检测合并后模型路径，支持多模型"""
    for name in (
        "light_translator_merged_3.5_2b",
        "light_translator_merged_1.5b",
        "light_translator_merged_0.5b",
        "light_translator_merged",
    ):
        p = os.path.join(_SCRIPT_DIR, "output", name)
        if os.path.isdir(p):
            return p
    return os.path.join(_SCRIPT_DIR, "output", "light_translator_merged")


def _detect_base_model(lora_path: str) -> str:
    """根据 LoRA 路径推断对应的基础模型路径"""
    lp = lora_path.replace(os.sep, "/").lower()
    if "qwen3.5_2b" in lp or "qwen3_5_2b" in lp:
        return os.path.join(_SCRIPT_DIR, "model_cache", "qwen3.5-2b")
    elif "qwen2.5_1.5b" in lp:
        return os.path.join(_SCRIPT_DIR, "model_cache", "qwen2.5-1.5b")
    else:
        return os.path.join(_SCRIPT_DIR, "model_cache", "qwen2.5-0.5b")


_LORA_OUTPUT = _find_lora_path()
_MERGED_OUTPUT = _find_merged_path()
_BASE_MODEL_PATH = _detect_base_model(_LORA_OUTPUT)

# 测试用例
TEST_CASES = [
    {
        "name": "加法段落",
        "python": "def add(a, b):\n    return a + b",
        "expected_light_keywords": ["段落", "接收", "返回", "加"],
    },
    {
        "name": "循环打印",
        "python": "for i in range(10):\n    print(i)",
        "expected_light_keywords": ["遍历", "打印"],
    },
    {
        "name": "阶乘递归",
        "python": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
        "expected_light_keywords": ["段落", "接收", "如果", "返回", "乘"],
    },
    {
        "name": "条件判断",
        "python": "x = 10\ny = 20\nif x > y:\n    print('x大')\nelse:\n    print('y大')",
        "expected_light_keywords": ["设", "如果", "大于", "否则", "打印"],
    },
    {
        "name": "冒泡排序",
        "python": "arr = [5, 2, 8, 1, 9]\nn = len(arr)\nfor i in range(n-1):\n    for j in range(n-i-1):\n        if arr[j] > arr[j+1]:\n            arr[j], arr[j+1] = arr[j+1], arr[j]",
        "expected_light_keywords": ["设", "遍历", "如果", "大于"],
    },
    {
        "name": "列表操作",
        "python": "nums = [1, 2, 3]\nnums.append(4)\nprint(len(nums))",
        "expected_light_keywords": ["设", "追加", "len", "打印"],
    },
    {
        "name": "while循环",
        "python": "count = 0\nwhile count < 5:\n    print(count)\n    count += 1",
        "expected_light_keywords": ["设", "当", "小于", "打印"],
    },
    {
        "name": "字典操作",
        "python": "d = {'a': 1, 'b': 2}\nfor k, v in d.items():\n    print(k, v)",
        "expected_light_keywords": ["设", "遍历", "打印"],
    },
]


def find_training_pid():
    """查找训练进程PID"""
    result = subprocess.run(
        ["wmic", "process", "where", "name='python.exe'", "get", "ProcessId,CommandLine"],
        capture_output=True, text=True
    )
    for line in result.stdout.split("\n"):
        if "train_cpu_lora" in line:
            parts = line.strip().split()
            for part in reversed(parts):
                if part.isdigit():
                    return int(part)
    return None


def check_training_complete():
    """检查训练是否完成"""
    # 方法1: 检查train_output.log中是否有"训练完成"
    if os.path.exists(_TRAIN_OUTPUT):
        with open(_TRAIN_OUTPUT, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if "训练完成" in content or "全部完成" in content:
            return True
        if "LoRA 权重保存到" in content:
            return True

    # 方法2: 检查LoRA权重文件是否存在
    if os.path.exists(_LORA_OUTPUT):
        files = os.listdir(_LORA_OUTPUT)
        if any(f.endswith(".bin") or f.endswith(".safetensors") for f in files):
            return True

    # 方法3: 检查进程是否已退出
    pid = find_training_pid()
    if pid is None:
        # 进程不在了，检查是否有输出
        if os.path.exists(_LORA_OUTPUT):
            return True
        # 可能崩溃了
        return False

    return False


def get_training_progress():
    """获取训练进度"""
    if not os.path.exists(_TRAIN_ERROR):
        return "未知"

    with open(_TRAIN_ERROR, "rb") as f:
        raw = f.read()

    import re
    # 查找最后的进度条
    matches = list(re.finditer(rb"(\d+)%\|.*?(\d+)/(\d+).*?(\d+\.\d+)(s/it|it/s)", raw))
    if matches:
        last = matches[-1]
        start = max(0, last.start() - 5)
        end = min(len(raw), last.end() + 10)
        return raw[start:end].decode("utf-8", errors="replace").strip()

    return "未找到进度信息"


def merge_lora():
    """合并LoRA权重"""
    print("\n" + "=" * 60)
    print("合并 LoRA 权重")
    print("=" * 60)

    if not os.path.exists(_LORA_OUTPUT):
        print(f"[ERROR] LoRA 权重不存在: {_LORA_OUTPUT}")
        return False

    # 检查是否已有合并模型
    if os.path.exists(_MERGED_OUTPUT):
        print(f"合并模型已存在: {_MERGED_OUTPUT}")
        return True

    # 运行合并脚本
    cmd = [sys.executable, os.path.join(_SCRIPT_DIR, "merge_and_convert.py"), "--merge-only"]
    print(f"运行: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        cwd=_SCRIPT_DIR,
        capture_output=True,
        text=True,
        timeout=600,  # 10分钟超时
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode == 0:
        print("合并成功！")
        return True
    else:
        print(f"合并失败，返回码: {result.returncode}")
        return False


def test_inference():
    """测试微调后的模型推理"""
    print("\n" + "=" * 60)
    print("推理测试")
    print("=" * 60)

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    model_path = _BASE_MODEL_PATH

    # 加载 tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 优先使用合并模型，否则用LoRA
    if os.path.exists(_MERGED_OUTPUT):
        print(f"加载合并模型: {_MERGED_OUTPUT}")
        model = AutoModelForCausalLM.from_pretrained(
            _MERGED_OUTPUT, dtype=torch.float32, trust_remote_code=True
        )
    elif os.path.exists(_LORA_PATH := _LORA_OUTPUT):
        print(f"加载基础模型 + LoRA: {model_path} + {_LORA_PATH}")
        base = AutoModelForCausalLM.from_pretrained(
            model_path, dtype=torch.float32, trust_remote_code=True
        )
        model = PeftModel.from_pretrained(base, _LORA_PATH)
        model = model.merge_and_unload()
    else:
        print("[ERROR] 未找到微调模型")
        return False

    model.eval()

    # 系统提示
    system_prompt = (
        "你是光明（LightLang）编程语言 v3.2 的翻译专家。"
        "光明是一种中文编程语言，使用中文关键字。"
        "你的任务是将 Python 代码翻译为光明 v3.2 代码。\n"
        "关键规则：\n"
        "- 变量赋值: 设 x 为 10\n"
        "- 段落定义: 段落 名 接收 参数：\n"
        "- 条件: 如果 / 否则如果 / 否则：\n"
        "- 循环: 遍历 i 于 0至N： / 当 条件：\n"
        "- 运算: 加上/减去/乘以/除以/取余\n"
        "- 比较: 等于/不等于/大于/小于\n"
        "- 打印: 打印(x)\n"
        "只输出光明代码，不要解释。"
    )

    results = []

    for case in TEST_CASES:
        print(f"\n--- {case['name']} ---")
        print(f"Python: {case['python']}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"将以下 Python 代码翻译为光明 v3.2：\n\n{case['python']}"},
        ]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(text, return_tensors="pt")

        t0 = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.1,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
                top_p=0.9,
            )
        elapsed = time.time() - t0

        response = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        ).strip()

        print(f"光明: {response}")
        print(f"耗时: {elapsed:.1f}s")

        # 检查关键词命中
        keywords = case.get("expected_light_keywords", [])
        hits = sum(1 for kw in keywords if kw in response)
        hit_rate = hits / len(keywords) if keywords else 0

        result = {
            "name": case["name"],
            "python": case["python"],
            "light_output": response,
            "expected_keywords": keywords,
            "keyword_hits": hits,
            "keyword_hit_rate": hit_rate,
            "time_seconds": elapsed,
        }
        results.append(result)

        print(f"关键词命中: {hits}/{len(keywords)} ({hit_rate:.0%})")

    # 汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)

    total_hits = sum(r["keyword_hits"] for r in results)
    total_keywords = sum(len(r["expected_keywords"]) for r in results)
    overall_rate = total_hits / total_keywords if total_keywords else 0

    print(f"总关键词命中: {total_hits}/{total_keywords} ({overall_rate:.1%})")
    print(f"平均推理时间: {sum(r['time_seconds'] for r in results)/len(results):.1f}s")

    # 保存结果
    report_path = os.path.join(_SCRIPT_DIR, "inference_test_report.json")
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_cases": len(results),
        "overall_keyword_hit_rate": overall_rate,
        "results": results,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告保存到: {report_path}")

    return overall_rate >= 0.5  # 至少50%关键词命中才算通过


def main():
    print("=" * 60)
    print("光明训练自动完成脚本")
    print("=" * 60)
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 检查训练是否已完成
    if check_training_complete():
        print("训练已完成！")
    else:
        # 监控训练进度
        print("训练尚未完成，开始监控...")
        check_interval = 300  # 5分钟检查一次
        max_wait = 7 * 3600  # 最多等7小时

        waited = 0
        while waited < max_wait:
            progress = get_training_progress()
            pid = find_training_pid()
            print(f"[{time.strftime('%H:%M:%S')}] PID={pid}, 进度: {progress}")

            if check_training_complete():
                print("\n训练已完成！")
                break

            if pid is None and not check_training_complete():
                print("\n[WARN] 训练进程已退出，但未检测到完成标记")
                print("检查是否生成了LoRA权重...")
                if os.path.exists(_LORA_OUTPUT):
                    print("LoRA权重存在，继续处理")
                    break
                else:
                    print("[ERROR] LoRA权重不存在，训练可能失败")
                    # 打印错误日志
                    if os.path.exists(_TRAIN_ERROR):
                        with open(_TRAIN_ERROR, "r", encoding="utf-8", errors="replace") as f:
                            print(f.read()[-1000:])
                    return

            time.sleep(check_interval)
            waited += check_interval

        if waited >= max_wait:
            print("等待超时（7小时），退出")
            return

    # 合并LoRA
    if not merge_lora():
        print("合并失败，尝试直接用LoRA推理...")

    # 测试推理
    success = test_inference()

    if success:
        print("\n✓ 测试通过！模型可以生成光明代码。")
        print("\n下一步：")
        print(f"  1. 交互模式: python local_infer.py --fine-tuned --backend transformers --interactive")
        print(f"  2. CLI集成:  light ai local --fine-tuned \"写一个冒泡排序\"")
    else:
        print("\n△ 测试结果不理想，模型可能需要更多训练数据或更长训练时间。")
        print("可以尝试：")
        print("  1. 增加epochs到5-10")
        print("  2. 增加训练数据")
        print("  3. 使用prompt工程模式: light ai local --prompt-only \"需求\"")


if __name__ == "__main__":
    main()
