#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光明本地推理器 — 通过本地小模型生成光明代码

支持三种推理后端：
  1. ollama   — 通过 ollama 调用本地模型（推荐，最快）
  2. transformers — 直接用 transformers + peft 推理（无需 ollama）
  3. prompt   — 只生成 prompt 不调用模型（粘贴给外部 AI 用）

两种模式：
  --prompt-only   使用 prompt 工程（无需微调，用 pipeline 组装 prompt）
  --fine-tuned    使用微调后的模型（需要先完成训练）

用法：
    # 使用微调模型推理（默认 ollama 后端）
    python local_infer.py --fine-tuned "写一个冒泡排序"

    # 使用 prompt 工程 + ollama 基础模型
    python local_infer.py "写一个冒泡排序"

    # 使用 transformers 后端（不需要 ollama）
    python local_infer.py --fine-tuned --backend transformers "写一个冒泡排序"

    # 翻译 Python 代码
    python local_infer.py --fine-tuned --mode translate "def add(a, b): return a + b"

    # 交互模式
    python local_infer.py --fine-tuned --interactive

    # 修复代码
    python local_infer.py --fine-tuned --fix hello.light "第3行语法错误"
"""

import argparse
import json
import os
import subprocess
import sys
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

# ── 常量 ──
_DEFAULT_MODEL_OLLAMA = "qwen2.5-coder:1.5b"
_FINETUNED_OLLAMA = "light-translator"
_DEFAULT_MODEL_PATH = os.path.join(_SCRIPT_DIR, "model_cache", "qwen2.5-0.5b")


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
            print(f"[自动检测] LoRA 路径: {p}", file=sys.stderr)
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
            print(f"[自动检测] 合并模型路径: {p}", file=sys.stderr)
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


_LORA_PATH = _find_lora_path()
_MERGED_PATH = os.environ.get(
    "DUAN_MERGED_MODEL",
    _find_merged_path(),
)
# 基础模型路径根据 LoRA 路径自动推断
_DEFAULT_MODEL_PATH = _detect_base_model(_LORA_PATH)
SYSTEM_PROMPT = (
    "你是光明（LightLang）编程语言 v3.2 的翻译专家。"
    "光明是一种中文编程语言，使用中文关键字。"
    "你的任务是将 Python 代码翻译为光明 v3.2 代码。\n"
    "关键规则：\n"
    "- 变量赋值: 设 x 为 10\n"
    "- 字符串赋值: 定义 s 等于 \"hello\"\n"
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
    "- 变量赋值规则: 数字/布尔/None/列表/字典用 设 x 为 Y; 仅纯字符串赋值可用 定义 s 等于 \"hello\"\n"
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
    "- 特性: 特性 段落 名：\n"
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
    "- 异常类型: 捕获具体异常类型，如 捕获 ZeroDivisionError 为 e\n"
    "只输出光明代码，不要解释。"
)


# ═══════════════════════════════════════════════════════════════════
# 后端 1: ollama
# ═══════════════════════════════════════════════════════════════════

def call_ollama(
    model: str,
    prompt: str,
    system: str = "",
    temperature: float = 0.1,
    max_tokens: int = 1024,
    timeout: int = 120,
) -> str:
    """调用 ollama 本地模型

    使用 ollama 的 HTTP API（默认 localhost:11434）。
    """
    import urllib.request
    import urllib.error

    url = "http://localhost:11434/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "system": system or SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "stop": ["<|im_end|>", "```"],
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - t0
            response = result.get("response", "").strip()

            # 打印统计
            eval_count = result.get("eval_count", 0)
            if eval_count and elapsed > 0:
                speed = eval_count / elapsed
                print(f"[ollama] {model} | {eval_count} tokens | {elapsed:.1f}s | {speed:.1f} tok/s",
                      file=sys.stderr)

            return response
    except urllib.error.URLError as e:
        print(f"[ERROR] 无法连接 ollama: {e}", file=sys.stderr)
        print("请确认 ollama 已安装并运行:", file=sys.stderr)
        print("  安装: winget install Ollama.Ollama", file=sys.stderr)
        print("  启动: ollama serve", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"[ERROR] ollama 调用失败: {e}", file=sys.stderr)
        return ""


def check_ollama() -> bool:
    """检查 ollama 是否可用"""
    import urllib.request
    import urllib.error
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return True
    except Exception:
        return False


def list_ollama_models() -> list:
    """列出已安装的 ollama 模型"""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════
# 后端 2: transformers（直接推理，不需要 ollama）
# ═══════════════════════════════════════════════════════════════════

_transformer_pipeline = None


def get_transformer_pipeline(use_finetuned: bool = True):
    """获取或初始化 transformers 推理 pipeline"""
    global _transformer_pipeline

    if _transformer_pipeline is not None:
        return _transformer_pipeline

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # 优先使用合并后的模型，其次使用 LoRA
    if use_finetuned:
        if os.path.exists(_MERGED_PATH):
            print(f"[transformers] 加载合并模型: {_MERGED_PATH}", file=sys.stderr)
            model_path = _MERGED_PATH
            model = AutoModelForCausalLM.from_pretrained(
                model_path, dtype=torch.float32, trust_remote_code=True
            )
            tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        elif os.path.exists(_LORA_PATH):
            from peft import PeftModel
            base_model_path = _detect_base_model(_LORA_PATH)
            print(f"[transformers] 加载基础模型 + LoRA: {base_model_path} + {_LORA_PATH}", file=sys.stderr)
            base = AutoModelForCausalLM.from_pretrained(
                base_model_path, dtype=torch.float32, trust_remote_code=True
            )
            model = PeftModel.from_pretrained(base, _LORA_PATH)
            model = model.merge_and_unload()
            tokenizer = AutoTokenizer.from_pretrained(base_model_path, trust_remote_code=True)
        else:
            print(f"[transformers] 未找到微调模型，使用基础模型: {_DEFAULT_MODEL_PATH}", file=sys.stderr)
            model_path = _DEFAULT_MODEL_PATH
            model = AutoModelForCausalLM.from_pretrained(
                model_path, dtype=torch.float32, trust_remote_code=True
            )
            tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    else:
        model_path = _DEFAULT_MODEL_PATH
        print(f"[transformers] 加载基础模型: {model_path}", file=sys.stderr)
        model = AutoModelForCausalLM.from_pretrained(
            model_path, dtype=torch.float32, trust_remote_code=True
        )
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

    model.eval()

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    _transformer_pipeline = (model, tokenizer)
    return _transformer_pipeline


def call_transformers(
    prompt: str,
    system: str = "",
    temperature: float = 0.1,
    max_tokens: int = 512,
) -> str:
    """使用 transformers 直接推理"""
    import torch

    model, tokenizer = get_transformer_pipeline(use_finetuned=True)

    messages = [
        {"role": "system", "content": system or SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt")

    t0 = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            pad_token_id=tokenizer.pad_token_id,
            top_p=0.9,
        )

    elapsed = time.time() - t0
    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    ).strip()

    token_count = outputs[0][inputs["input_ids"].shape[1]:].shape[0]
    if elapsed > 0:
        speed = token_count / elapsed
        print(f"[transformers] {token_count} tokens | {elapsed:.1f}s | {speed:.1f} tok/s",
              file=sys.stderr)

    return response


# ═══════════════════════════════════════════════════════════════════
# 核心推理函数
# ═══════════════════════════════════════════════════════════════════

def generate_light(
    requirement: str,
    backend: str = "ollama",
    use_finetuned: bool = False,
    mode: str = "auto",
    model_size: str = "small",
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> str:
    """生成光明代码

    Args:
        requirement: 用户需求（自然语言或 Python 代码）
        backend: 推理后端 ("ollama" 或 "transformers")
        use_finetuned: 是否使用微调模型
        mode: 生成模式 ("auto", "translate", "create")
        model_size: prompt 工程模式下的模型大小 ("small", "medium", "large")
        temperature: 生成温度
        max_tokens: 最大生成 token 数

    Returns:
        生成的光明代码
    """
    # 构造 prompt
    if use_finetuned:
        # 微调模型：直接给 Python 代码或需求
        if mode == "translate" or _looks_like_python(requirement):
            prompt = f"将以下 Python 代码翻译为光明 v3.2：\n\n{requirement}"
        else:
            prompt = f"请用光明 v3.2 语法编写以下功能：\n\n{requirement}"
    else:
        # prompt 工程模式：用 pipeline 组装完整 prompt
        from pipeline import generate_pipeline
        prompt = generate_pipeline(requirement, model_size=model_size)

    # 调用后端
    if backend == "ollama":
        model = _FINETUNED_OLLAMA if use_finetuned else _DEFAULT_MODEL_OLLAMA
        return call_ollama(model, prompt, temperature=temperature, max_tokens=max_tokens)
    elif backend == "transformers":
        return call_transformers(prompt, temperature=temperature, max_tokens=max_tokens)
    else:
        raise ValueError(f"未知后端: {backend}")


def fix_light(
    filepath: str,
    error_msg: str,
    backend: str = "ollama",
    use_finetuned: bool = False,
    model_size: str = "small",
) -> str:
    """修复光明代码"""
    # 读取原代码
    if not os.path.exists(filepath):
        return f"[ERROR] 文件不存在: {filepath}"

    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    if use_finetuned:
        prompt = (
            f"以下光明代码有错误，请修复：\n\n"
            f"```光明\n{code}\n```\n\n"
            f"错误信息：{error_msg}\n\n"
            f"请输出修复后的完整光明代码。"
        )
    else:
        from pipeline import fix_pipeline
        prompt = fix_pipeline(filepath, error_msg, model_size=model_size)

    if backend == "ollama":
        model = _FINETUNED_OLLAMA if use_finetuned else _DEFAULT_MODEL_OLLAMA
        return call_ollama(model, prompt, max_tokens=2048)
    elif backend == "transformers":
        return call_transformers(prompt, max_tokens=1024)
    else:
        raise ValueError(f"未知后端: {backend}")


def _looks_like_python(text: str) -> bool:
    """判断文本是否像 Python 代码"""
    indicators = ["def ", "class ", "import ", "for ", "while ", "if ", "return ", "print("]
    return sum(1 for ind in indicators if ind in text) >= 2


# ═══════════════════════════════════════════════════════════════════
# 交互模式
# ═══════════════════════════════════════════════════════════════════

def interactive_mode(backend: str, use_finetuned: bool):
    """交互式对话模式"""
    print("=" * 60)
    print("光明本地推理器 — 交互模式")
    print("=" * 60)

    # 显示当前配置
    if backend == "ollama":
        if not check_ollama():
            print("\n[WARN] ollama 未运行，尝试启动...")
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
            if not check_ollama():
                print("[ERROR] ollama 启动失败")
                return

        model = _FINETUNED_OLLAMA if use_finetuned else _DEFAULT_MODEL_OLLAMA
        models = list_ollama_models()
        print(f"  后端: ollama")
        print(f"  模型: {model}")
        if use_finetuned and model not in models:
            print(f"  [WARN] 模型 {model} 未安装，可用模型: {', '.join(models)}")
            if models:
                model = models[0]
                print(f"  切换到: {model}")
        print(f"  可用模型: {', '.join(models) if models else '无'}")
    else:
        print(f"  后端: transformers")
        print(f"  模型: {'微调' if use_finetuned else '基础'}")

    print(f"  模式: {'微调' if use_finetuned else 'prompt 工程'}")
    print()
    print("输入需求或 Python 代码，按回车生成光明代码。")
    print("输入 'quit' 或 'exit' 退出。")
    print("输入 'translate' 切换到翻译模式。")
    print("输入 'fix <文件> <错误>' 修复代码。")
    print()

    force_translate = False

    while True:
        try:
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break
        if user_input.lower() == "translate":
            force_translate = not force_translate
            print(f"翻译模式: {'开' if force_translate else '关'}")
            continue
        if user_input.lower().startswith("fix "):
            parts = user_input[4:].split(None, 1)
            if len(parts) < 2:
                print("用法: fix <文件路径> <错误信息>")
                continue
            filepath, error = parts[0], parts[1]
            result = fix_light(filepath, error, backend=backend, use_finetuned=use_finetuned)
            print("\n--- 修复结果 ---")
            print(result)
            print()
            continue

        # 生成
        mode = "translate" if force_translate or _looks_like_python(user_input) else "auto"
        result = generate_light(
            user_input,
            backend=backend,
            use_finetuned=use_finetuned,
            mode=mode,
        )

        print("\n--- 光明代码 ---")
        print(result)
        print()


# ═══════════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="光明本地推理器 — 通过本地小模型生成光明代码"
    )
    parser.add_argument("input", nargs="?", help="需求描述或 Python 代码")
    parser.add_argument(
        "--preset",
        choices=["qwen2.5-0.5b", "qwen2.5-1.5b", "qwen3.5-2b"],
        default=None,
        help="指定模型预设，覆盖自动检测",
    )
    parser.add_argument(
        "--backend", choices=["ollama", "transformers"],
        default="ollama", help="推理后端（默认 ollama）",
    )
    parser.add_argument(
        "--fine-tuned", action="store_true",
        help="使用微调后的模型",
    )
    parser.add_argument(
        "--prompt-only", action="store_true",
        help="只输出 prompt 不调用模型",
    )
    parser.add_argument(
        "--mode", choices=["auto", "translate", "create"],
        default="auto", help="生成模式",
    )
    parser.add_argument(
        "--model-size", choices=["small", "medium", "large"],
        default="small", help="prompt 工程模式下的模型大小",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="交互模式",
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="修复模式（需配合 --fix-file 和 --fix-error）",
    )
    parser.add_argument("--fix-file", help="要修复的光明文件路径")
    parser.add_argument("--fix-error", help="错误信息")
    parser.add_argument("--temperature", type=float, default=0.1, help="生成温度")
    parser.add_argument("--max-tokens", type=int, default=1024, help="最大 token 数")
    parser.add_argument("--output", "-o", help="输出文件路径")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # ── 应用模型预设（覆盖全局变量）──
    global _LORA_PATH, _MERGED_PATH, _DEFAULT_MODEL_PATH
    if args.preset:
        preset_map = {
            "qwen2.5-0.5b": ("qwen2.5_0.5b_light_gpu", "light_translator_merged_0.5b", "qwen2.5-0.5b"),
            "qwen2.5-1.5b": ("qwen2.5_1.5b_light_gpu", "light_translator_merged_1.5b", "qwen2.5-1.5b"),
            "qwen3.5-2b":   ("qwen3.5_2b_light_gpu",   "light_translator_merged_3.5_2b", "qwen3.5-2b"),
        }
        lora_dir, merged_dir, model_dir = preset_map[args.preset]
        _LORA_PATH = os.path.join(_SCRIPT_DIR, "output", lora_dir, "final")
        _MERGED_PATH = os.path.join(_SCRIPT_DIR, "output", merged_dir)
        _DEFAULT_MODEL_PATH = os.path.join(_SCRIPT_DIR, "model_cache", model_dir)
        print(f"[预设] {args.preset}: lora={_LORA_PATH}, merged={_MERGED_PATH}", file=sys.stderr)

    # 交互模式
    if args.interactive:
        interactive_mode(args.backend, args.fine_tuned)
        return

    # 修复模式
    if args.fix:
        if not args.fix_file or not args.fix_error:
            print("修复模式需要 --fix-file 和 --fix-error")
            sys.exit(1)
        result = fix_light(
            args.fix_file, args.fix_error,
            backend=args.backend, use_finetuned=args.fine_tuned,
            model_size=args.model_size,
        )
        print(result)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"\n已保存到: {args.output}")
        return

    # prompt-only 模式
    if args.prompt_only:
        from pipeline import generate_pipeline
        prompt = generate_pipeline(args.input or "", model_size=args.model_size)
        print(prompt)
        return

    # 普通生成模式
    if not args.input:
        parser.print_help()
        return

    result = generate_light(
        args.input,
        backend=args.backend,
        use_finetuned=args.fine_tuned,
        mode=args.mode,
        model_size=args.model_size,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )

    if result:
        print(result)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"\n已保存到: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
