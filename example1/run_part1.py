#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""光明翻译器分批测试脚本 - Part 1 (示例 01-09)"""

import json
import os
import time
import urllib.request
import urllib.error

MODEL = "airoot/light-translator"
API_URL = "http://localhost:11434/api/generate"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

EXAMPLES = [
    {
        "id": "01_basic_arithmetic",
        "title": "基础算术与变量",
        "category": "基础语法",
        "python": '''x = 10
y = 20
result = x + y
print(result)''',
    },
    {
        "id": "02_conditional",
        "title": "条件分支",
        "category": "基础语法",
        "python": '''score = 85
if score >= 90:
    print("A")
elif score >= 80:
    print("B")
elif score >= 60:
    print("C")
else:
    print("D")''',
    },
    {
        "id": "03_for_loop",
        "title": "for 循环与累加",
        "category": "循环结构",
        "python": '''total = 0
for i in range(1, 101):
    total += i
print(total)''',
    },
    {
        "id": "04_while_loop",
        "title": "while 循环",
        "category": "循环结构",
        "python": '''count = 0
while count < 5:
    print(count)
    count += 1''',
    },
    {
        "id": "05_nested_loop",
        "title": "嵌套循环 - 九九乘法表",
        "category": "循环结构",
        "python": '''for i in range(1, 10):
    for j in range(1, i + 1):
        print(f"{j}x{i}={i*j}", end=" ")
    print()''',
    },
    {
        "id": "06_function",
        "title": "函数定义与调用",
        "category": "函数",
        "python": '''def add(a, b):
    return a + b

result = add(3, 5)
print(result)''',
    },
    {
        "id": "07_recursion",
        "title": "递归 - 阶乘",
        "category": "函数",
        "python": '''def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(5))''',
    },
    {
        "id": "08_fibonacci",
        "title": "递归 - 斐波那契数列",
        "category": "函数",
        "python": '''def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

for i in range(10):
    print(fib(i))''',
    },
    {
        "id": "09_list_operations",
        "title": "列表操作",
        "category": "数据结构",
        "python": '''fruits = ["apple", "banana", "cherry"]
fruits.append("date")
fruits.remove("banana")
print(len(fruits))
for fruit in fruits:
    print(fruit)''',
    },
]


def call_ollama(prompt: str) -> str:
    data = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 4096}
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except Exception as e:
        return f"[ERROR] {e}"


def main():
    results = []
    for i, ex in enumerate(EXAMPLES):
        print(f"[{i+1}/{len(EXAMPLES)}] {ex['id']} - {ex['title']}", flush=True)
        t0 = time.time()
        light_code = call_ollama(ex["python"])
        elapsed = time.time() - t0
        print(f"  {elapsed:.1f}s | {light_code[:60]}...", flush=True)
        results.append({
            "id": ex["id"], "title": ex["title"], "category": ex["category"],
            "python": ex["python"], "light": light_code, "elapsed": round(elapsed, 1)
        })

    # 读取已有结果并合并
    json_path = os.path.join(OUTPUT_DIR, "results.json")
    all_results = []
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            all_results = json.load(f)
    existing_ids = {r["id"] for r in all_results}
    for r in results:
        if r["id"] in existing_ids:
            # 更新已有
            for j, old in enumerate(all_results):
                if old["id"] == r["id"]:
                    all_results[j] = r
                    break
        else:
            all_results.append(r)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n保存 {len(results)} 条，总计 {len(all_results)} 条 -> {json_path}", flush=True)


if __name__ == "__main__":
    main()
