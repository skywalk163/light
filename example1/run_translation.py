#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""光明翻译器批量测试脚本
将经典 Python 代码通过 ollama 光明模型翻译为光明代码，并保存到 output 目录。
"""

import json
import os
import time
import urllib.request
import urllib.error

MODEL = "airoot/light-translator"
API_URL = "http://localhost:11434/api/generate"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 经典 Python 代码示例集 - 覆盖各类语法特性
# ============================================================

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
    {
        "id": "10_dict_operations",
        "title": "字典操作",
        "category": "数据结构",
        "python": '''scores = {"Alice": 90, "Bob": 85, "Charlie": 78}
scores["David"] = 92
for name, score in scores.items():
    print(f"{name}: {score}")''',
    },
    {
        "id": "11_list_comprehension",
        "title": "列表推导式",
        "category": "数据结构",
        "python": '''squares = [x**2 for x in range(10) if x % 2 == 0]
print(squares)''',
    },
    {
        "id": "12_f_string",
        "title": "f-string 格式化",
        "category": "高级特性",
        "python": '''name = "Alice"
age = 30
print(f"My name is {name}, I am {age} years old")''',
    },
    {
        "id": "13_class_basic",
        "title": "类定义 - 基础",
        "category": "面向对象",
        "python": '''class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return f"{self.name} speaks"

dog = Animal("Dog")
print(dog.speak())''',
    },
    {
        "id": "14_class_inheritance",
        "title": "类继承",
        "category": "面向对象",
        "python": '''class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return f"{self.name} speaks"

class Dog(Animal):
    def speak(self):
        return f"{self.name} barks"

dog = Dog("Rex")
print(dog.speak())''',
    },
    {
        "id": "15_exception_handling",
        "title": "异常处理",
        "category": "高级特性",
        "python": '''try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"Error: {e}")
finally:
    print("Done")''',
    },
    {
        "id": "16_with_statement",
        "title": "with 语句 - 文件操作",
        "category": "高级特性",
        "python": '''with open("data.txt", "r") as f:
    content = f.read()
    print(content)''',
    },
    {
        "id": "17_lambda",
        "title": "lambda 表达式",
        "category": "高级特性",
        "python": '''square = lambda x: x ** 2
print(square(5))

even = list(filter(lambda x: x % 2 == 0, range(10)))
print(even)''',
    },
    {
        "id": "18_bubble_sort",
        "title": "冒泡排序",
        "category": "经典算法",
        "python": '''def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

nums = [64, 34, 25, 12, 22, 11, 90]
print(bubble_sort(nums))''',
    },
    {
        "id": "19_binary_search",
        "title": "二分查找",
        "category": "经典算法",
        "python": '''def binary_search(arr, target):
    left = 0
    right = len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

nums = [1, 3, 5, 7, 9, 11, 13]
print(binary_search(nums, 7))''',
    },
    {
        "id": "20_decorator",
        "title": "装饰器",
        "category": "高级特性",
        "python": '''def timer(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return result
    return wrapper

@timer
def slow_function():
    return "done"

print(slow_function())''',
    },
    {
        "id": "21_static_class_methods",
        "title": "静态方法与类方法",
        "category": "面向对象",
        "python": '''class MathHelper:
    @staticmethod
    def add(a, b):
        return a + b

    @classmethod
    def create(cls):
        return cls()

print(MathHelper.add(3, 5))''',
    },
    {
        "id": "22_break_continue",
        "title": "break 与 continue",
        "category": "循环结构",
        "python": '''for i in range(10):
    if i == 3:
        continue
    if i == 7:
        break
    print(i)''',
    },
    {
        "id": "23_string_methods",
        "title": "字符串方法",
        "category": "基础语法",
        "python": '''s = "Hello World"
print(s.upper())
print(s.lower())
print(s.split())
print(s.replace("World", "Python"))''',
    },
    {
        "id": "24_dict_comprehension",
        "title": "字典推导式",
        "category": "数据结构",
        "python": '''nums = [1, 2, 3, 4, 5]
squares = {n: n**2 for n in nums}
print(squares)''',
    },
    {
        "id": "25_set_operations",
        "title": "集合操作",
        "category": "数据结构",
        "python": '''a = {1, 2, 3, 4}
b = {3, 4, 5, 6}
print(a & b)
print(a | b)
print(a - b)''',
    },
    {
        "id": "26_multiple_return",
        "title": "多返回值与解包",
        "category": "函数",
        "python": '''def min_max(lst):
    return min(lst), max(lst)

minimum, maximum = min_max([3, 1, 4, 1, 5, 9, 2, 6])
print(f"min={minimum}, max={maximum}")''',
    },
]


def call_ollama(prompt: str) -> str:
    """调用 ollama API 进行翻译"""
    data = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096,
        }
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except urllib.error.URLError as e:
        return f"[ERROR] API 调用失败: {e}"
    except Exception as e:
        return f"[ERROR] {e}"


def main():
    print("=" * 60)
    print("光明翻译器批量测试")
    print(f"模型: {MODEL}")
    print(f"示例数: {len(EXAMPLES)}")
    print("=" * 60)

    results = []
    for i, ex in enumerate(EXAMPLES):
        print(f"\n[{i+1}/{len(EXAMPLES)}] {ex['id']} - {ex['title']}")
        print(f"  分类: {ex['category']}")

        t0 = time.time()
        light_code = call_ollama(ex["python"])
        elapsed = time.time() - t0

        print(f"  耗时: {elapsed:.1f}s")
        # 只打印前3行预览
        lines = light_code.split("\n")
        for line in lines[:3]:
            print(f"  | {line}")
        if len(lines) > 3:
            print(f"  | ... ({len(lines)} 行)")

        results.append({
            "id": ex["id"],
            "title": ex["title"],
            "category": ex["category"],
            "python": ex["python"],
            "light": light_code,
            "elapsed": round(elapsed, 1),
        })

    # 保存汇总 JSON
    json_path = os.path.join(OUTPUT_DIR, "results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n汇总结果已保存: {json_path}")

    # 生成对照 Markdown
    md_path = os.path.join(OUTPUT_DIR, "翻译对照表.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 光明翻译器测试 - Python 与光明对照\n\n")
        f.write(f"> 模型: {MODEL} | 测试数: {len(results)} | 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for r in results:
            f.write(f"## {r['id']} {r['title']}\n\n")
            f.write(f"**分类**: {r['category']} | **耗时**: {r['elapsed']}s\n\n")
            f.write(f"**Python 代码:**\n\n```python\n{r['python']}\n```\n\n")
            f.write(f"**光明翻译:**\n\n```\n{r['light']}\n```\n\n")
            f.write("---\n\n")
    print(f"对照表已保存: {md_path}")

    # 打印统计
    print(f"\n{'=' * 60}")
    print("统计:")
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)
    for cat, items in sorted(categories.items()):
        print(f"  {cat}: {len(items)} 个示例")
    print(f"  总计: {len(results)} 个示例")


if __name__ == "__main__":
    main()
