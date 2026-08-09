#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""光明翻译器 ollama 多维度测试脚本"""

import json
import time
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "light-translator"

# 测试用例: (名称, Python代码, 期望包含的光明关键字)
TEST_CASES = [
    ("1. 基础函数", 
     "def add(a, b):\n    return a + b",
     ["段落", "接收", "返回"]),

    ("2. 条件判断",
     "def check(n):\n    if n > 0:\n        print(\"positive\")\n    elif n < 0:\n        print(\"negative\")\n    else:\n        print(\"zero\")",
     ["段落", "如果", "否则如果", "否则", "打印"]),

    ("3. for循环",
     "def sum_list(lst):\n    total = 0\n    for i in range(len(lst)):\n        total += lst[i]\n    return total",
     ["段落", "遍历", "返回"]),

    ("4. while循环",
     "def countdown(n):\n    while n > 0:\n        print(n)\n        n -= 1",
     ["段落", "当", "打印"]),

    ("5. 列表操作",
     "def process(lst):\n    result = []\n    for x in lst:\n        if x > 10:\n            result.append(x * 2)\n    return result",
     ["段落", "遍历", "如果"]),

    ("6. f-string",
     "def greet(name, age):\n    return f\"Hello {name}, you are {age} years old\"",
     ["段落", "接收", "f\""]),

    ("7. 类定义",
     "class Animal:\n    def __init__(self, name):\n        self.name = name\n    def speak(self):\n        return f\"{self.name} speaks\"",
     ["类", "构造", "接收", "己"]),

    ("8. 类继承",
     "class Dog(Animal):\n    def speak(self):\n        return f\"{self.name} barks\"",
     ["类", "继承"]),

    ("9. 异常处理",
     "def divide(a, b):\n    try:\n        return a / b\n    except ZeroDivisionError as e:\n        print(f\"Error: {e}\")\n    finally:\n        print(\"done\")",
     ["段落", "尝试", "捕获", "最终"]),

    ("10. 列表推导",
     "squares = [x**2 for x in range(10) if x % 2 == 0]",
     ["遍历", "之", "若"]),

    ("11. 字典操作",
     "def count_words(text):\n    words = text.split()\n    counts = {}\n    for w in words:\n        if w in counts:\n            counts[w] += 1\n        else:\n            counts[w] = 1\n    return counts",
     ["段落", "遍历", "如果", "否则"]),

    ("12. 冒泡排序",
     "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr",
     ["段落", "接收", "遍历", "如果"]),

    ("13. with语句",
     "def read_file(path):\n    with open(path, 'r') as f:\n        return f.read()",
     ["段落", "使用", "为"]),

    ("14. lambda和高阶函数",
     "nums = [1, 2, 3, 4, 5]\nevens = list(filter(lambda x: x % 2 == 0, nums))\ndoubled = list(map(lambda x: x * 2, nums))",
     ["筛选", "映射", "接收"]),

    ("15. 递归",
     "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)",
     ["段落", "接收", "如果", "返回"]),
]


def call_ollama(prompt: str, timeout: int = 120) -> dict:
    """Call ollama and return full response dict"""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 1024,
            "stop": ["<|im_end|>", "```"],
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
    
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    elapsed = time.time() - t0
    result["_elapsed"] = elapsed
    return result


def run_tests():
    print("=" * 70)
    print("光明翻译器 (Qwen3.5-2B) ollama 多维度测试")
    print("=" * 70)
    print(f"模型: {MODEL}")
    print()

    results = []
    total_score = 0

    for name, python_code, expected_keywords in TEST_CASES:
        print(f"\n{'=' * 60}")
        print(f"测试 {name}")
        print(f"{'=' * 60}")
        print(f"Python 输入:\n{python_code}")
        print()

        prompt = f"将以下 Python 代码翻译为光明 v3.2：\n\n{python_code}"

        try:
            result = call_ollama(prompt)
            response = result.get("response", "").strip()
            eval_count = result.get("eval_count", 0)
            elapsed = result.get("_elapsed", 0)
            speed = eval_count / elapsed if elapsed > 0 else 0

            print(f"光明输出:\n{response}")
            print()
            print(f"[统计] {eval_count} tokens | {elapsed:.1f}s | {speed:.1f} tok/s")

            # Check expected keywords
            found = [kw for kw in expected_keywords if kw in response]
            missing = [kw for kw in expected_keywords if kw not in response]
            score = len(found) / len(expected_keywords) * 100

            status = "PASS" if score == 100 else ("PARTIAL" if score > 0 else "FAIL")
            print(f"[结果] {status} | 关键字匹配: {len(found)}/{len(expected_keywords)} ({score:.0f}%)")
            if missing:
                print(f"  缺失关键字: {missing}")

            results.append({
                "name": name,
                "status": status,
                "score": score,
                "speed": speed,
                "tokens": eval_count,
                "elapsed": elapsed,
                "response": response,
                "missing": missing,
            })

            if score == 100:
                total_score += 1

        except Exception as e:
            print(f"[ERROR] {e}")
            results.append({
                "name": name,
                "status": "ERROR",
                "score": 0,
                "error": str(e),
            })

    # Summary
    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    partial_count = sum(1 for r in results if r["status"] == "PARTIAL")
    fail_count = sum(1 for r in results if r["status"] in ("FAIL", "ERROR"))
    
    print(f"  PASS: {pass_count}/{len(results)}")
    print(f"  PARTIAL: {partial_count}/{len(results)}")
    print(f"  FAIL: {fail_count}/{len(results)}")
    
    speeds = [r["speed"] for r in results if "speed" in r and r["speed"] > 0]
    if speeds:
        avg_speed = sum(speeds) / len(speeds)
        print(f"  平均速度: {avg_speed:.1f} tok/s")
    
    print()
    for r in results:
        status_icon = {"PASS": "OK", "PARTIAL": "~", "FAIL": "XX", "ERROR": "!!"}[r["status"]]
        speed_str = f"{r.get('speed', 0):.1f} tok/s" if "speed" in r else "N/A"
        print(f"  [{status_icon}] {r['name']} | {speed_str} | {r.get('score', 0):.0f}%")


if __name__ == "__main__":
    run_tests()
