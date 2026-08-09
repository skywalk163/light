"""
光明 SFT 训练集构造器

为 ERNIE-4.5-0.3B 微调生成 Python→光明 翻译对照数据。
输出 JSONL 格式，符合 ERNIEKit SFT 规范。

数据来源：
  1. 手工编写的高质量 v3.2 对照对（核心，按语法类别系统覆盖）
  2. 从 examples/ 目录 .light 文件提取（需标注是否旧语法）
  3. 变体扩充：对每条基础对照对做等价变换，扩充训练规模

注意：
  光明 v3.2 有两套语法风格并存：
  - 新语法（SRC 后端）：设/段落...接收/遍历...于...至/加/减/取余
  - 旧语法（ANTLR）：变量/段落。参数。/结束。/模
  本脚本统一使用 v3.2 新语法（SRC 后端），因为这是当前默认后端。

用法：
    python build_sft_dataset.py          # 生成训练集到 sft_dataset.jsonl
    python build_sft_dataset.py --stats  # 只显示统计信息
"""

import json
import os
import random
import re
import sys
from typing import List, Dict

# ── 路径 ──
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ═══════════════════════════════════════════════════════════════════
# 手工对照对：Python → 光明 v3.2（新语法/SRC后端）
# 每条 = (category, python_code, light_code)
# ═══════════════════════════════════════════════════════════════════

_HANDCRAFTED: List[tuple] = [
    # ── 变量与赋值 ────────────────────────────────────────────────
    ("变量", "x = 10", "设 x 为 10"),
    ("变量", "name = 'hello'", "设 name 为 \"hello\""),
    ("变量", "lst = [1, 2, 3]", "设 lst 为 [1, 2, 3]"),
    ("变量", "x = 5\ny = 3", "设 x 为 5\n设 y 为 3"),
    ("变量", "flag = True", "设 flag 为 真"),
    ("变量", "empty = None", "设 empty 为 空"),
    ("变量", "pi = 3.14", "设 pi 为 3.14"),
    ("变量", "x = 10\nx = x + 1", "设 x 为 10\n设 x 为 x 加上 1"),
    ("变量", "count = 0\ncount += 1", "设 count 为 0\n设 count 为 count 加上 1"),
    ("变量", "total = 100\ntotal -= 20", "设 total 为 100\n设 total 为 total 减去 20"),
    ("变量", "n = 5\nn *= 3", "设 n 为 5\n设 n 为 n 乘以 3"),
    ("变量", "d = 10\nd /= 2", "设 d 为 10\n设 d 为 d 除以 2"),
    ("变量", 's = "world"', "设 s 为 \"world\""),
    ("变量", "nums = []", "设 nums 为 []"),
    ("变量", "pairs = {}", "设 pairs 为 {}"),

    # ── 段落（函数）─────────────────────────────────────────────
    ("段落", "def add(a, b):\n    return a + b", "段落 加法 接收 a, b：\n    返回 a 加上 b"),
    ("段落", "def greet():\n    print('hello')", "段落 打招呼：\n    打印(\"hello\")"),
    ("段落", "def square(n):\n    return n * n", "段落 平方 接收 n：\n    返回 n 乘以 n"),
    ("段落", "def is_positive(n):\n    return n > 0", "段落 是正数 接收 n：\n    返回 n 大于 0"),
    ("段落", "def max_of_two(a, b):\n    if a >= b:\n        return a\n    return b", "段落 最大值 接收 a, b：\n    如果 a 大于等于 b：\n        返回 a\n    返回 b"),
    ("段落", "def abs_val(n):\n    if n < 0:\n        return -n\n    return n", "段落 绝对值 接收 n：\n    如果 n 小于 0：\n        返回 0 减去 n\n    返回 n"),
    ("段落", "def fib(n):\n    if n <= 2:\n        return 1\n    return fib(n-1) + fib(n-2)", "段落 斐波那契 接收 n：\n    如果 n 小于等于 2：\n        返回 1\n    返回 斐波那契(n 减去 1) 加上 斐波那契(n 减去 2)"),
    ("段落", "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)", "段落 阶乘 接收 n：\n    如果 n 小于等于 1：\n        返回 1\n    返回 n 乘以 阶乘(n 减去 1)"),
    ("段落", "def area(width, height):\n    return width * height", "段落 面积 接收 宽, 高：\n    返回 宽 乘以 高"),
    ("段落", "def celsius_to_fahrenheit(c):\n    return c * 9 / 5 + 32", "段落 摄氏转华氏 接收 c：\n    返回 c 乘以 9 除以 5 加上 32"),
    ("段落", "def greet_name(name):\n    print('Hello, ' + name)",
     "段落 打招呼 接收 name：\n    打印(\"Hello, \" 加上 name)"),
    ("段落", "def count_down(n):\n    while n > 0:\n        print(n)\n        n -= 1", "段落 倒计时 接收 n：\n    当 n 大于 0：\n        打印(n)\n        设 n 为 n 减去 1"),

    
    # ── 复合赋值 (补充) ──
    ("复合", "x = 100\\nx %= 7", "设 x 为 100\\n设 x 为 x 取余 7"),
    ("复合", "a = 5\\na ^= 3", "设 a 为 5\\n设 a 为 a 异或 3"),
    ("复合", "x = 16\\nx >>= 2", "设 x 为 16\\n设 x 为 x 右移 2"),
    ("复合", "x = 1\\nx <<= 3", "设 x 为 1\\n设 x 为 x 左移 3"),
    ("复合", "n = 50\\nn //= 6", "设 n 为 50\\n设 n 为 n 整除 6"),
    # ── for…else 补充 ──
    ("for…else", "for i in range(5):\\n    if i == 3:\\n        break\\nelse:\\n    print('no break')",
     "遍历 i 于 0至4：\\n    如果 i 等于 3：\\n        跳出\\n否则：\\n    打印('no break')"),

# ── 条件 ──────────────────────────────────────────────────────
    ("条件", "if x > 0:\n    print('positive')", "如果 x 大于 0：\n    打印(\"positive\")"),
    ("条件", "if x > 0:\n    print('yes')\nelse:\n    print('no')",
     "如果 x 大于 0：\n    打印(\"yes\")\n否则：\n    打印(\"no\")"),
    ("条件", "if score >= 90:\n    grade = 'A'\nelif score >= 80:\n    grade = 'B'\nelse:\n    grade = 'C'",
     "如果 score 大于等于 90：\n    设 grade 为 \"A\"\n否则如果 score 大于等于 80：\n    设 grade 为 \"B\"\n否则：\n    设 grade 为 \"C\""),
    ("条件", "if x == 0:\n    print('zero')", "如果 x 等于 0：\n    打印(\"zero\")"),
    ("条件", "if x != 0:\n    print('not zero')", "如果 x 不等于 0：\n    打印(\"not zero\")"),
    ("条件", "if a and b:\n    print('both')", "如果 a 且 b：\n    打印(\"both\")"),
    ("条件", "if a or b:\n    print('either')", "如果 a 或 b：\n    打印(\"either\")"),
    ("条件", "if not flag:\n    print('off')", "如果 非 flag：\n    打印(\"off\")"),
    ("条件", "if x > 0 and x < 10:\n    print('in range')",
     "如果 x 大于 0 且 x 小于 10：\n    打印(\"in range\")"),
    ("条件", "if x <= 0:\n    print('non-positive')\nelse:\n    print('positive')",
     "如果 x 小于等于 0：\n    打印(\"non-positive\")\n否则：\n    打印(\"positive\")"),
    ("条件", "if n % 2 == 0:\n    print('even')\nelse:\n    print('odd')",
     "如果 n 取余 2 等于 0：\n    打印(\"even\")\n否则：\n    打印(\"odd\")"),

    # ── 循环 ──────────────────────────────────────────────────────
    ("循环", "while x > 0:\n    x -= 1", "当 x 大于 0：\n    设 x 为 x 减去 1"),
    ("循环", "while True:\n    if x == 0:\n        break\n    x -= 1", "当 真：\n    如果 x 等于 0：\n        跳出\n    设 x 为 x 减去 1"),
    ("循环", "for i in range(10):\n    print(i)", "遍历 i 于 0至9：\n    打印(i)"),
    ("循环", "for i in range(1, 11):\n    print(i)", "遍历 i 于 1至10：\n    打印(i)"),
    ("循环", "for i in range(0, 10, 2):\n    print(i)", "遍历 i 于 0至9步2：\n    打印(i)"),
    ("循环", "for item in lst:\n    print(item)", "遍历 item 于 lst：\n    打印(item)"),
    ("循环", "for i in range(len(lst)):\n    print(lst[i])", "遍历 i 于 0至len(lst)减去1：\n    打印(lst[i])"),
    ("循环", "i = 0\nwhile i < 10:\n    print(i)\n    i += 1", "设 i 为 0\n当 i 小于 10：\n    打印(i)\n    设 i 为 i 加上 1"),
    ("循环", "total = 0\nfor n in numbers:\n    total += n", "设 total 为 0\n遍历 n 于 numbers：\n    设 total 为 total 加上 n"),
    ("循环", "for i in range(5):\n    if i == 3:\n        continue\n    print(i)", "遍历 i 于 0至4：\n    如果 i 等于 3：\n        跳过\n    打印(i)"),
    ("循环", "found = False\nfor item in lst:\n    if item == target:\n        found = True\n        break", "设 found 为 假\n遍历 item 于 lst：\n    如果 item 等于 target：\n        设 found 为 真\n        跳出"),

    # ── 列表操作 ──────────────────────────────────────────────────
    ("列表", "lst.append(10)", "lst.追加(10)"),
    ("列表", "x = lst[0]", "设 x 为 lst[0]"),
    ("列表", "lst[0] = 10", "lst[0] = 10"),
    ("列表", "n = len(lst)", "设 n 为 len(lst)"),
    ("列表", "result = [x for x in lst if x > 0]", "设 result 为 []\n遍历 x 于 lst：\n    如果 x 大于 0：\n        result.追加(x)"),
    ("列表", "total = sum(lst)", "设 total 为 0\n遍历 x 于 lst：\n    设 total 为 total 加上 x"),
    ("列表", "lst.sort()", "设 n 为 len(lst)\n遍历 i 于 0至n减去2：\n    遍历 j 于 0至n减去i减去2：\n        如果 lst[j] 大于 lst[j 加上 1]：\n            设 tmp 为 lst[j]\n            lst[j] = lst[j 加上 1]\n            lst[j 加上 1] = tmp"),
    ("列表", "lst.reverse()", "设 n 为 len(lst)\n设 i 为 0\n设 j 为 n 减去 1\n当 i 小于 j：\n    设 tmp 为 lst[i]\n    lst[i] = lst[j]\n    lst[j] = tmp\n    设 i 为 i 加上 1\n    设 j 为 j 减去 1"),
    ("列表", "if 5 in lst:\n    print('found')",
     "设 found 为 假\n遍历 x 于 lst：\n    如果 x 等于 5：\n        设 found 为 真\n        跳出\n如果 found：\n    打印(\"found\")"),
    ("列表", "new_lst = lst[1:3]", "设 new_lst 为 []\n设 i 为 1\n当 i 小于 3：\n    new_lst.追加(lst[i])\n    设 i 为 i 加上 1"),
    ("列表", "count = lst.count(5)", "设 count 为 0\n遍历 x 于 lst：\n    如果 x 等于 5：\n        设 count 为 count 加上 1"),

    # ── 字符串 ────────────────────────────────────────────────────
    ("字符串", "s = 'hello' + ' world'", "设 s 为 \"hello\" 加上 \" world\""),
    ("字符串", "n = len(s)", "设 n 为 len(s)"),
    ("字符串", "upper_s = s.upper()", "设 upper_s 为 字符串转大写(s)"),
    ("字符串", "if 'hello' in s:\n    print('found')",
     "如果 字符串包含(s, \"hello\")：\n    打印(\"found\")"),
    ("字符串", "parts = s.split(',')",
     "设 parts 为 字符串分割(s, \",\")"),
    ("字符串", "result = s.replace('old', 'new')",
     "设 result 为 字符串替换(s, \"old\", \"new\")"),
    ("字符串", "idx = s.find('abc')",
     "设 idx 为 字符串查找(s, \"abc\")"),
    ("字符串", "print(f'{name} is {age} years old')",
     "打印(f\"{name} is {age} years old\")"),

    # ── 字典 ──────────────────────────────────────────────────────
    ("字典", "d = {'a': 1, 'b': 2}", "设 d 为 {\"a\": 1, \"b\": 2}"),
    ("字典", "d['key'] = 10", "d[\"key\"] = 10"),
    ("字典", "val = d.get('key', 0)", "设 val 为 d.get(\"key\", 0)"),
    ("字典", "if 'key' in d:\n    print(d['key'])",
     "如果 \"key\" 于 d：\n    打印(d[\"key\"])"),
    ("字典", "for k, v in d.items():\n    print(k, v)", "遍历 k 于 d：\n    打印(k)\n    打印(d[k])"),

    # ── 异常 ──────────────────────────────────────────────────────
    ("异常", "try:\n    x = int(s)\nexcept:\n    x = 0", "尝试：\n    设 x 为 int(s)\n捕获 异常：\n    设 x 为 0"),
    ("异常", "try:\n    f = open('data.txt')\nexcept FileNotFoundError:\n    print('file not found')",
     "尝试：\n    设 f 为 读取文件(\"data.txt\")\n捕获 异常：\n    打印(\"file not found\")"),
    ("异常", "raise ValueError('invalid')",
     "抛出 异常(\"invalid\")"),

    # ── 导入 ──────────────────────────────────────────────────────
    ("导入", "import math", "导入 数学工具"),
    ("导入", "from math import sqrt", "从 数学工具 导入 平方"),
    ("导入", "from collections import Counter", "从 集合操作 导入 计数"),

    # ── 类（需 LLVM 后端）────────────────────────────────────────
    ("类", "class Dog:\n    def __init__(self, name):\n        self.name = name\n    def speak(self):\n        print(f'{self.name}: woof!')",
     "类 狗：\n    属性 名字\n    构造 接收 名字：\n        己.名字 为 名字\n    段落 说话：\n        打印(f\"{己.名字}: woof!\")"),
    ("类", "class Cat(Dog):\n    def speak(self):\n        print(f'{self.name}: meow!')",
     "类 猫 继承 狗：\n    段落 说话：\n        打印(f\"{己.名字}: meow!\")"),
    ("类", "class Point:\n    def __init__(self, x, y):\n        self.x = x\n        self.y = y\n    def distance(self):\n        return (self.x**2 + self.y**2)**0.5", "class Point：\n    属性 x\n    属性 y\n    构造 接收 x, y：\n        己.x 为 x\n        己.y 为 y\n    段落 距离：\n        返回 (己.x 乘以 己.x 加上 己.y 乘以 己.y) 的 0.5 次方"),
    ("类", "obj = Dog('Rex')\nobj.speak()",
     "设 obj 为 新建 狗(\"Rex\")\nobj.说话()"),

    # ── 复合示例（多语法混用）────────────────────────────────────
    ("复合", "def binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1", "段落 二分查找 接收 arr, target：\n    设 low 为 0\n    设 high 为 len(arr) 减去 1\n    当 low 小于等于 high：\n        设 mid 为 (low 加上 high) 除以 2\n        如果 arr[mid] 等于 target：\n            返回 mid\n        否则如果 arr[mid] 小于 target：\n            设 low 为 mid 加上 1\n        否则：\n            设 high 为 mid 减去 1\n    返回 -1"),
    ("复合", "def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True", "段落 是素数 接收 n：\n    如果 n 小于 2：\n        返回 假\n    设 limit 为 int(n 的 0.5 次方) 加上 1\n    遍历 i 于 2至limit减去1：\n        如果 n 取余 i 等于 0：\n            返回 假\n    返回 真"),
    ("复合", "def fizzbuzz(n):\n    for i in range(1, n+1):\n        if i % 15 == 0:\n            print('FizzBuzz')\n        elif i % 3 == 0:\n            print('Fizz')\n        elif i % 5 == 0:\n            print('Buzz')\n        else:\n            print(i)",
     "段落 FizzBuzz 接收 n：\n    遍历 i 于 1至n：\n        如果 i 取余 15 等于 0：\n            打印(\"FizzBuzz\")\n        否则如果 i 取余 3 等于 0：\n            打印(\"Fizz\")\n        否则如果 i 取余 5 等于 0：\n            打印(\"Buzz\")\n        否则：\n            打印(i)"),
    ("复合", "def count_words(text):\n    words = text.split()\n    counts = {}\n    for w in words:\n        if w in counts:\n            counts[w] += 1\n        else:\n            counts[w] = 1\n    return counts", "段落 统计词频 接收 text：\n    设 words 为 字符串分割(text)\n    设 counts 为 {}\n    遍历 w 于 words：\n        如果 w 于 counts：\n            counts[w] = counts[w] 加上 1\n        否则：\n            counts[w] = 1\n    返回 counts"),
    ("复合", "def gcd(a, b):\n    while b != 0:\n        a, b = b, a % b\n    return a", "段落 最大公约数 接收 a, b：\n    当 b 不等于 0：\n        设 tmp 为 a 取余 b\n        设 a 为 b\n        设 b 为 tmp\n    返回 a"),
    ("复合", "def power(base, exp):\n    result = 1\n    for _ in range(exp):\n        result *= base\n    return result", "段落 幂运算 接收 base, exp：\n    设 result 为 1\n    遍历 _ 于 0至exp减去1：\n        设 result 为 result 乘以 base\n    返回 result"),
    ("复合", "def reverse_string(s):\n    result = ''\n    for i in range(len(s)-1, -1, -1):\n        result += s[i]\n    return result",
     "段落 反转字符串 接收 s：\n    设 result 为 \"\"\n    设 i 为 len(s) 减去 1\n    当 i 大于等于 0：\n        设 result 为 result 加上 s[i]\n        设 i 为 i 减去 1\n    返回 result"),
    ("复合", "def find_max(lst):\n    max_val = lst[0]\n    for item in lst[1:]:\n        if item > max_val:\n            max_val = item\n    return max_val", "段落 求最大值 接收 lst：\n    设 max_val 为 lst[0]\n    遍历 item 于 lst：\n        如果 item 大于 max_val：\n            设 max_val 为 item\n    返回 max_val"),
    ("复合", "def remove_duplicates(lst):\n    seen = []\n    result = []\n    for item in lst:\n        if item not in seen:\n            seen.append(item)\n            result.append(item)\n    return result", "段落 去重 接收 lst：\n    设 seen 为 []\n    设 result 为 []\n    遍历 item 于 lst：\n        设 found 为 假\n        遍历 s 于 seen：\n            如果 s 等于 item：\n                设 found 为 真\n                跳出\n        如果 非 found：\n            seen.追加(item)\n            result.追加(item)\n    返回 result"),
    ("复合", "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr", "段落 冒泡排序 接收 arr：\n    设 n 为 len(arr)\n    遍历 i 于 0至n减去1：\n        遍历 j 于 0至n减去i减去2：\n            如果 arr[j] 大于 arr[j 加上 1]：\n                设 tmp 为 arr[j]\n                arr[j] = arr[j 加上 1]\n                arr[j 加上 1] = tmp\n    返回 arr"),
    ("复合", "def selection_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        min_idx = i\n        for j in range(i+1, n):\n            if arr[j] < arr[min_idx]:\n                min_idx = j\n        arr[i], arr[min_idx] = arr[min_idx], arr[i]\n    return arr", "段落 选择排序 接收 arr：\n    设 n 为 len(arr)\n    遍历 i 于 0至n减去1：\n        设 min_idx 为 i\n        遍历 j 于 i加上1至n减去1：\n            如果 arr[j] 小于 arr[min_idx]：\n                设 min_idx 为 j\n        设 tmp 为 arr[i]\n        arr[i] = arr[min_idx]\n        arr[min_idx] = tmp\n    返回 arr"),

    # ── 补充：更多变量变体 ───────────────────────────────────────
    ("变量", "a = 1\nb = 2\nc = a + b", "设 a 为 1\n设 b 为 2\n设 c 为 a 加上 b"),
    ("变量", "width = 10\nheight = 5", "设 width 为 10\n设 height 为 5"),
    ("变量", "msg = 'ok'", "设 msg 为 \"ok\""),
    ("变量", "items = [10, 20, 30]", "设 items 为 [10, 20, 30]"),
    ("变量", "active = False", "设 active 为 假"),
    ("变量", "data = None", "设 data 为 空"),
    ("变量", "ratio = 2.5", "设 ratio 为 2.5"),
    ("变量", "x = 100\nx += 5", "设 x 为 100\n设 x 为 x 加上 5"),
    ("变量", "y = 50\ny -= 10", "设 y 为 50\n设 y 为 y 减去 10"),
    ("变量", "z = 3\nz *= 4", "设 z 为 3\n设 z 为 z 乘以 4"),
    ("变量", "w = 100\nw /= 5", "设 w 为 100\n设 w 为 w 除以 5"),

    # ── 补充：更多段落变体 ──────────────────────────────────────
    ("段落", "def double(n):\n    return n * 2", "段落 双倍 接收 n：\n    返回 n 乘以 2"),
    ("段落", "def subtract(a, b):\n    return a - b", "段落 减法 接收 a, b：\n    返回 a 减去 b"),
    ("段落", "def multiply(a, b):\n    return a * b", "段落 乘法 接收 a, b：\n    返回 a 乘以 b"),
    ("段落", "def divide(a, b):\n    return a / b", "段落 除法 接收 a, b：\n    返回 a 除以 b"),
    ("段落", "def modulo(a, b):\n    return a % b", "设 段落 为 段落 取余 接收 a, b：\n    返回 a 取余 b"),
    ("段落", "def is_even(n):\n    return n % 2 == 0", "段落 是偶数 接收 n：\n    返回 n 取余 2 等于 0"),
    ("段落", "def is_odd(n):\n    return n % 2 != 0", "段落 是奇数 接收 n：\n    返回 n 取余 2 不等于 0"),
    ("段落", "def clamp(val, lo, hi):\n    if val < lo:\n        return lo\n    if val > hi:\n        return hi\n    return val", "段落 限值 接收 val, lo, hi：\n    如果 val 小于 lo：\n        返回 lo\n    如果 val 大于 hi：\n        返回 hi\n    返回 val"),
    ("段落", "def sign(n):\n    if n > 0:\n        return 1\n    elif n < 0:\n        return -1\n    return 0", "段落 符号 接收 n：\n    如果 n 大于 0：\n        返回 1\n    否则如果 n 小于 0：\n        返回 -1\n    返回 0"),
    ("段落", "def min_of_three(a, b, c):\n    m = a\n    if b < m:\n        m = b\n    if c < m:\n        m = c\n    return m", "段落 三数最小 接收 a, b, c：\n    设 m 为 a\n    如果 b 小于 m：\n        设 m 为 b\n    如果 c 小于 m：\n        设 m 为 c\n    返回 m"),
    ("段落", "def swap(a, b):\n    return b, a", "段落 交换 接收 a, b：\n    返回 b, a"),
    ("段落", "def power2(n):\n    return 2 ** n", "段落 二的幂 接收 n：\n    返回 2 的 n 次方"),
    ("段落", "def negate(n):\n    return -n", "段落 取反 接收 n：\n    返回 0 减去 n"),

    # ── 补充：更多条件变体 ──────────────────────────────────────
    ("条件", "if age >= 18:\n    print('adult')", "如果 age 大于等于 18：\n    打印(\"adult\")"),
    ("条件", "if score > 60:\n    print('pass')\nelse:\n    print('fail')",
     "如果 score 大于 60：\n    打印(\"pass\")\n否则：\n    打印(\"fail\")"),
    ("条件", "if n > 0:\n    print('positive')\nelif n == 0:\n    print('zero')\nelse:\n    print('negative')",
     "如果 n 大于 0：\n    打印(\"positive\")\n否则如果 n 等于 0：\n    打印(\"zero\")\n否则：\n    打印(\"negative\")"),
    ("条件", "if a == b and b == c:\n    print('all equal')",
     "如果 a 等于 b 且 b 等于 c：\n    打印(\"all equal\")"),
    ("条件", "if x < 0 or x > 100:\n    print('out of range')",
     "如果 x 小于 0 或 x 大于 100：\n    打印(\"out of range\")"),
    ("条件", "if not done:\n    print('continue')",
     "如果 非 done：\n    打印(\"continue\")"),
    ("条件", "if len(s) > 0:\n    print('not empty')",
     "如果 len(s) 大于 0：\n    打印(\"not empty\")"),
    ("条件", "if n % 3 == 0:\n    print('divisible by 3')",
     "如果 n 取余 3 等于 0：\n    打印(\"divisible by 3\")"),
    ("条件", "if x >= 0 and x <= 100:\n    print('valid')",
     "如果 x 大于等于 0 且 x 小于等于 100：\n    打印(\"valid\")"),
    ("条件", "grade = 'A' if score >= 90 else 'B'",
     "如果 score 大于等于 90：\n    设 grade 为 \"A\"\n否则：\n    设 grade 为 \"B\""),

    # ── 补充：更多循环变体 ──────────────────────────────────────
    ("循环", "for i in range(5, 15):\n    print(i)", "遍历 i 于 5至14：\n    打印(i)"),
    ("循环", "for i in range(100, 0, -1):\n    print(i)", "遍历 i 于 100至1步1：\n    打印(i)"),
    ("循环", "total = 0\ni = 1\nwhile i <= 100:\n    total += i\n    i += 1", "设 total 为 0\n设 i 为 1\n当 i 小于等于 100：\n    设 total 为 total 加上 i\n    设 i 为 i 加上 1"),
    ("循环", "for c in 'hello':\n    print(c)", "遍历 c 于 \"hello\"：\n    打印(c)"),
    ("循环", "for key in d:\n    print(key, d[key])", "遍历 key 于 d：\n    打印(key)\n    打印(d[key])"),
    ("循环", "while True:\n    cmd = input()\n    if cmd == 'quit':\n        break",
     "当 真：\n    设 cmd 为 输入()\n    如果 cmd 等于 \"quit\"：\n        跳出"),
    ("循环", "for i in range(10):\n    if i % 2 == 0:\n        continue\n    print(i)", "遍历 i 于 0至9：\n    如果 i 取余 2 等于 0：\n        跳过\n    打印(i)"),
    ("循环", "i = 0\nwhile i < len(lst):\n    print(lst[i])\n    i += 1", "设 i 为 0\n当 i 小于 len(lst)：\n    打印(lst[i])\n    设 i 为 i 加上 1"),
    ("循环", "count = 0\nfor x in lst:\n    if x > 0:\n        count += 1", "设 count 为 0\n遍历 x 于 lst：\n    如果 x 大于 0：\n        设 count 为 count 加上 1"),
    ("循环", "for i in range(3):\n    for j in range(3):\n        print(i, j)", "遍历 i 于 0至2：\n    遍历 j 于 0至2：\n        打印(i)\n        打印(j)"),

    # ── 补充：更多列表操作 ──────────────────────────────────────
    ("列表", "first = lst[0]\nlast = lst[-1]", "设 first 为 lst[0]\n设 last 为 lst[len(lst) 减去 1]"),
    ("列表", "lst[2] = 99", "lst[2] = 99"),
    ("列表", "if len(lst) == 0:\n    print('empty')",
     "如果 len(lst) 等于 0：\n    打印(\"empty\")"),
    ("列表", "doubled = [x * 2 for x in lst]", "设 doubled 为 []\n遍历 x 于 lst：\n    doubled.追加(x 乘以 2)"),
    ("列表", "evens = [x for x in lst if x % 2 == 0]", "设 evens 为 []\n遍历 x 于 lst：\n    如果 x 取余 2 等于 0：\n        evens.追加(x)"),
    ("列表", "merged = a + b", "设 merged 为 []\n遍历 x 于 a：\n    merged.追加(x)\n遍历 x 于 b：\n    merged.追加(x)"),
    ("列表", "lst.insert(0, 10)", "设 new_lst 为 [10]\n遍历 x 于 lst：\n    new_lst.追加(x)\n设 lst 为 new_lst"),
    ("列表", "lst.pop()", "设 last 为 lst[len(lst) 减去 1]\n设 new_lst 为 []\n遍历 i 于 0至len(lst)减去2：\n    new_lst.追加(lst[i])\n设 lst 为 new_lst"),
    ("列表", "lst.remove(5)", "设 new_lst 为 []\n设 skip 为 假\n遍历 x 于 lst：\n    如果 x 等于 5 且 非 skip：\n        设 skip 为 真\n    否则：\n        new_lst.追加(x)\n设 lst 为 new_lst"),

    # ── 补充：更多字符串 ────────────────────────────────────────
    ("字符串", "greeting = 'hi' + ' ' + name", "设 greeting 为 \"hi\" 加上 \" \" 加上 name"),
    ("字符串", "print(f'Result: {x}')", "打印(f\"Result: {x}\")"),
    ("字符串", "lower_s = s.lower()", "设 lower_s 为 字符串转小写(s)"),
    ("字符串", "stripped = s.strip()", "设 stripped 为 字符串去空白(s)"),
    ("字符串", "if s.startswith('http'):", "如果 字符串开头是(s, \"http\")："),
    ("字符串", "if s.endswith('.txt'):", "如果 字符串结尾是(s, \".txt\")："),
    ("字符串", "idx = s.index('abc')", "设 idx 为 字符串查找(s, \"abc\")"),
    ("字符串", "repeated = s * 3", "设 repeated 为 字符串重复(s, 3)"),
    ("字符串", "clean = s.replace(' ', '_')", "设 clean 为 字符串替换(s, \" \", \"_\")"),

    # ── 补充：更多字典 ──────────────────────────────────────────
    ("字典", "d = {}", "设 d 为 {}"),
    ("字典", "d['name'] = 'test'", "d[\"name\"] = \"test\""),
    ("字典", "del d['key']", "d.删除(\"key\")"),
    ("字典", "keys = list(d.keys())", "设 keys 为 []\n遍历 k 于 d：\n    keys.追加(k)"),
    ("字典", "if 'age' in d:\n    age = d['age']",
     "如果 \"age\" 于 d：\n        设 age 为 d[\"age\"]"),
    ("字典", "for key in sorted(d):", "设 keys 为 []\n遍历 k 于 d：\n    keys.追加(k)\n# sorted需要自行实现"),

    # ── 补充：更多异常 ──────────────────────────────────────────
    ("异常", "try:\n    result = 10 / 0\nexcept ZeroDivisionError:\n    result = 0", "尝试：\n    设 result 为 10 除以 0\n捕获 异常：\n    设 result 为 0"),
    ("异常", "try:\n    x = int(input())\nexcept ValueError:\n    x = 0\n    print('invalid')",
     "尝试：\n    设 x 为 int(输入())\n捕获 异常：\n    设 x 为 0\n    打印(\"invalid\")"),
    ("异常", "try:\n    f = open('data.txt')\n    content = f.read()\nexcept:\n    content = ''",
     "尝试：\n    设 f 为 读取文件(\"data.txt\")\n捕获 异常：\n    设 content 为 \"\""),
    ("异常", "raise Exception('error')", "抛出 异常(\"error\")"),
    ("异常", "try:\n    x = lst[100]\nexcept IndexError:\n    x = None", "尝试：\n    设 x 为 lst[100]\n捕获 异常：\n    设 x 为 空"),

    # ── 补充：更多导入 ──────────────────────────────────────────
    ("导入", "import json", "导入 JSON"),
    ("导入", "import os", "导入 文件系统"),
    ("导入", "from math import sqrt, pi", "从 数学工具 导入 平方, 圆周率"),
    ("导入", "from typing import List", "从 类型工具 导入 列表类型"),
    ("导入", "import random\nx = random.randint(1, 10)", "导入 随机数据\n设 x 为 随机整数(1, 10)"),

    # ── 补充：更多类 ────────────────────────────────────────────
    ("类", "class Counter:\n    def __init__(self):\n        self.count = 0\n    def increment(self):\n        self.count += 1\n    def get(self):\n        return self.count", "类 计数器：\n    属性 计数值\n    构造：\n        己.计数值 为 0\n    段落 增加：\n        己.计数值 加上 1\n    段落 获取：\n        返回 己.计数值"),
    ("类", "class Rect:\n    def __init__(self, w, h):\n        self.w = w\n        self.h = h\n    def area(self):\n        return self.w * self.h", "类 矩形：\n    属性 宽\n    属性 高\n    构造 接收 宽, 高：\n        己.宽 为 宽\n        己.高 为 高\n    段落 面积：\n        返回 己.宽 乘以 己.高"),
    ("类", "class Animal:\n    def __init__(self, name):\n        self.name = name\n    def speak(self):\n        pass", "类 动物：\n    属性 名字\n    构造 接收 名字：\n        己.名字 为 名字\n    段落 说话：\n        空操作"),
    ("类", "class Bird(Animal):\n    def speak(self):\n        print(f'{self.name}: chirp!')",
     "类 鸟 继承 动物：\n    段落 说话：\n        打印(f\"{己.名字}: chirp!\")"),
    ("类", "class Stack:\n    def __init__(self):\n        self.items = []\n    def push(self, item):\n        self.items.append(item)\n    def pop(self):\n        return self.items.pop()\n    def is_empty(self):\n        return len(self.items) == 0", "类 栈：\n    属性 元素列表\n    构造：\n        己.元素列表 为 []\n    段落 入栈 接收 item：\n        己.元素列表.追加(item)\n    段落 出栈：\n        返回 己.元素列表.弹出()\n    段落 是否为空：\n        返回 len(己.元素列表) 等于 0"),
    ("类", "class BankAccount:\n    def __init__(self, owner, balance=0):\n        self.owner = owner\n        self.balance = balance\n    def deposit(self, amount):\n        self.balance += amount\n    def withdraw(self, amount):\n        if amount <= self.balance:\n            self.balance -= amount", "类 银行账户：\n    属性 户主\n    属性 余额\n    构造 接收 owner, balance：\n        己.户主 为 owner\n        己.余额 为 balance\n    段落 存款 接收 amount：\n        己.余额 加上 amount\n    段落 取款 接收 amount：\n        如果 amount 小于等于 己.余额：\n            己.余额 减去 amount"),

    # ── 补充：更多复合示例 ──────────────────────────────────────
    ("复合", "def linear_search(lst, target):\n    for i in range(len(lst)):\n        if lst[i] == target:\n            return i\n    return -1", "段落 线性查找 接收 lst, target：\n    遍历 i 于 0至len(lst)减去1：\n        如果 lst[i] 等于 target：\n            返回 i\n    返回 -1"),
    ("复合", "def insertion_sort(arr):\n    for i in range(1, len(arr)):\n        key = arr[i]\n        j = i - 1\n        while j >= 0 and arr[j] > key:\n            arr[j+1] = arr[j]\n            j -= 1\n        arr[j+1] = key\n    return arr", "段落 插入排序 接收 arr：\n    遍历 i 于 1至len(arr)减去1：\n        设 key 为 arr[i]\n        设 j 为 i 减去 1\n        当 j 大于等于 0 且 arr[j] 大于 key：\n            arr[j 加上 1] = arr[j]\n            设 j 为 j 减去 1\n        arr[j 加上 1] = key\n    返回 arr"),
    ("复合", "def palindrome_check(s):\n    return s == s[::-1]",
     "段落 回文判断 接收 s：\n    设 reversed 为 \"\"\n    设 i 为 len(s) 减去 1\n    当 i 大于等于 0：\n        设 reversed 为 reversed 加上 s[i]\n        设 i 为 i 减去 1\n    返回 s 等于 reversed"),
    ("复合", "def count_vowels(s):\n    vowels = 'aeiou'\n    count = 0\n    for c in s:\n        if c in vowels:\n            count += 1\n    return count",
     "段落 统计元音 接收 s：\n    设 vowels 为 \"aeiou\"\n    设 count 为 0\n    遍历 c 于 s：\n        如果 字符串包含(vowels, c)：\n            设 count 为 count 加上 1\n    返回 count"),
    ("复合", "def matrix_sum(matrix):\n    total = 0\n    for row in matrix:\n        for val in row:\n            total += val\n    return total", "段落 矩阵求和 接收 matrix：\n    设 total 为 0\n    遍历 row 于 matrix：\n        遍历 val 于 row：\n            设 total 为 total 加上 val\n    返回 total"),
    ("复合", "def leap_year(year):\n    if year % 400 == 0:\n        return True\n    if year % 100 == 0:\n        return False\n    if year % 4 == 0:\n        return True\n    return False", "段落 闰年判断 接收 year：\n    如果 year 取余 400 等于 0：\n        返回 真\n    如果 year 取余 100 等于 0：\n        返回 假\n    如果 year 取余 4 等于 0：\n        返回 真\n    返回 假"),
    ("复合", "def sum_digits(n):\n    total = 0\n    while n > 0:\n        total += n % 10\n        n //= 10\n    return total", "段落 数位求和 接收 n：\n    设 total 为 0\n    当 n 大于 0：\n        设 total 为 total 加上 n 取余 10\n        设 n 为 n 除以 10\n    返回 total"),
    ("复合", "def fibonacci_iter(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n+1):\n        a, b = b, a+b\n    return b", "段落 斐波那契迭代 接收 n：\n    如果 n 小于等于 1：\n        返回 n\n    设 a 为 0\n    设 b 为 1\n    遍历 _ 于 2至n：\n        设 tmp 为 b\n        设 b 为 a 加上 b\n        设 a 为 tmp\n    返回 b"),
    ("复合", "def temperature_report(celsius):\n    if celsius < 0:\n        return 'freezing'\n    elif celsius < 15:\n        return 'cold'\n    elif celsius < 25:\n        return 'comfortable'\n    elif celsius < 35:\n        return 'warm'\n    else:\n        return 'hot'",
     "段落 温度报告 接收 celsius：\n    如果 celsius 小于 0：\n        返回 \"freezing\"\n    否则如果 celsius 小于 15：\n        返回 \"cold\"\n    否则如果 celsius 小于 25：\n        返回 \"comfortable\"\n    否则如果 celsius 小于 35：\n        返回 \"warm\"\n    否则：\n        返回 \"hot\""),
    ("复合", "def rock_paper_scissors(p1, p2):\n    if p1 == p2:\n        return 'draw'\n    if (p1 == 'rock' and p2 == 'scissors') or (p1 == 'scissors' and p2 == 'paper') or (p1 == 'paper' and p2 == 'rock'):\n        return 'p1 wins'\n    return 'p2 wins'",
     "段落 石头剪刀布 接收 p1, p2：\n    如果 p1 等于 p2：\n        返回 \"draw\"\n    如果 (p1 等于 \"rock\" 且 p2 等于 \"scissors\") 或 (p1 等于 \"scissors\" 且 p2 等于 \"paper\") 或 (p1 等于 \"paper\" 且 p2 等于 \"rock\")：\n        返回 \"p1 wins\"\n    返回 \"p2 wins\""),
    ("复合", "def collatz(n):\n    steps = 0\n    while n != 1:\n        if n % 2 == 0:\n            n = n // 2\n        else:\n            n = 3 * n + 1\n        steps += 1\n    return steps", "段落 考拉兹 接收 n：\n    设 steps 为 0\n    当 n 不等于 1：\n        如果 n 取余 2 等于 0：\n            设 n 为 n 除以 2\n        否则：\n            设 n 为 3 乘以 n 加上 1\n        设 steps 为 steps 加上 1\n    返回 steps"),
    ("复合", "def caesar_cipher(text, shift):\n    result = ''\n    for c in text:\n        if c.isalpha():\n            base = ord('a') if c.islower() else ord('A')\n            result += chr((ord(c) - base + shift) % 26 + base)\n        else:\n            result += c\n    return result",
     "段落 凯撒加密 接收 text, shift：\n    设 result 为 \"\"\n    遍历 c 于 text：\n        如果 字符串包含(小写字母表, c) 或 字符串包含(大写字母表, c)：\n            设 shifted 为 字符偏移(c, shift)\n            设 result 为 result 加上 shifted\n        否则：\n            设 result 为 result 加上 c\n    返回 result"),
    ("复合", "def histogram(data, bins):\n    counts = [0] * bins\n    for val in data:\n        idx = min(int(val * bins), bins - 1)\n        counts[idx] += 1\n    return counts", "段落 直方图 接收 data, bins：\n    设 counts 为 []\n    遍历 _ 于 0至bins减去1：\n        counts.追加(0)\n    遍历 val 于 data：\n        设 idx 为 int(val 乘以 bins)\n        如果 idx 大于等于 bins：\n            设 idx 为 bins 减去 1\n        counts[idx] = counts[idx] 加上 1\n    返回 counts"),

    # ── 补充：暗坑修正对照（教模型避开常见错误）──────────────────
    ("暗坑", "lst[0] = 10", "lst[0] = 10"),
    ("暗坑", "n = len(lst)", "设 n 为 len(lst)"),
    ("暗坑", "i = i + 1", "设 i 为 i 加上 1"),
    ("暗坑", "a + b", "设 a 为 a 加上 b"),
    ("暗坑", "a - b", "设 a 为 a 减去 b"),
    ("暗坑", "a * b", "设 a 为 a 乘以 b"),
    ("暗坑", "a / b", "设 a 为 a 除以 b"),
    ("暗坑", "a % b", "设 a 为 a 取余 b"),
    ("暗坑", "a == b", "a 等于 b"),
    ("暗坑", "a != b", "a 不等于 b"),
    ("暗坑", "a > b", "a 大于 b"),
    ("暗坑", "a < b", "a 小于 b"),
    ("暗坑", "a >= b", "a 大于等于 b"),
    ("暗坑", "a <= b", "a 小于等于 b"),
    ("暗坑", "a and b", "a 且 b"),
    ("暗坑", "a or b", "a 或 b"),
    ("暗坑", "not a", "非 a"),
    ("暗坑", "a += 1", "设 a 为 a 加上 1"),
    ("暗坑", "a -= 1", "设 a 为 a 减去 1"),
    ("暗坑", "a *= 2", "设 a 为 a 乘以 2"),
    ("暗坑", "a /= 2", "设 a 为 a 除以 2"),
    ("暗坑", "True", "真"),
    ("暗坑", "False", "假"),
    ("暗坑", "None", "空"),
    ("暗坑", "break", "跳出"),
    ("暗坑", "continue", "跳过"),
    ("暗坑", "return x", "返回 x"),
    ("暗坑", "def f(a, b):", "段落 f 接收 a, b："),
    ("暗坑", "while cond:", "当 cond："),
    ("暗坑", "for i in range(n):", "遍历 i 于 0至n减去1："),
    ("暗坑", "class Foo:", "类 Foo："),
    ("暗坑", "try:", "尝试："),
    ("暗坑", "except:", "捕获 异常："),
    ("暗坑", "raise Exception()", "抛出 异常()"),
    ("暗坑", "import math", "导入 数学工具"),
    ("暗坑", "from math import sqrt", "从 数学工具 导入 平方"),
    ("暗坑", "for x in lst:", "遍历 x 于 lst："),
    ("暗坑", "print('hello')", "打印(\"hello\")"),
]


# ═══════════════════════════════════════════════════════════════════
# 变体扩充：对基础对照对做等价变换
# ═══════════════════════════════════════════════════════════════════

def _expand_variants(pairs: List[tuple]) -> List[tuple]:
    """对手工对照对做变体扩充，增加训练数据量

    变体策略：
    1. 变量名替换：x→甲, y→乙, n→数, lst→列表 等中文名
    2. 指令变体：同一个翻译任务换不同说法（×2倍）
    """
    expanded = list(pairs)  # 保留原始数据

    # 变量名替换映射（两组，用于产生不同变体）
    name_maps = [
        {
            "x": "甲", "y": "乙", "n": "数", "m": "量", "i": "序",
            "lst": "列表", "arr": "数组", "s": "文", "result": "结果",
            "count": "计数", "total": "总计", "flag": "标志", "score": "分数",
            "item": "项", "name": "名", "val": "值", "max_val": "最大",
            "tmp": "临时", "found": "找到", "target": "目标",
        },
        {
            "x": "a", "y": "b", "n": "num", "lst": "list_", "arr": "data",
            "result": "res", "count": "cnt", "total": "sum_", "item": "elem",
            "name": "nm", "val": "v", "tmp": "temp", "found": "hit",
        },
    ]

    for name_map in name_maps:
        for cat, py, light in pairs:
            # 只对变量名含英文的短片段做变体
            if len(py) > 200:
                continue

            py_cn = py
            light_cn = light
            changed = False

            for en, cn in name_map.items():
                # 简单的全词替换
                if re.search(r'\b' + re.escape(en) + r'\b', py_cn):
                    py_cn = re.sub(r'\b' + re.escape(en) + r'\b', cn, py_cn)
                    # 光明端：对应的变量名
                    light_cn = re.sub(r'\b' + re.escape(en) + r'\b', cn, light_cn)
                    changed = True

            if changed:
                expanded.append((cat, py_cn, light_cn))

    # 指令倍增：对每条数据用2种不同指令各生成一条
    # （最终每条基础数据会有 ~2 条不同指令的副本）
    doubled = []
    for cat, py, light in pairs:
        doubled.append((cat, py, light))
    # 不做额外复制，因为 build_dataset 已经用 random.choice 选指令了
    # 但我们可以对非暗坑类数据各生成一条"指令不同"的副本
    for cat, py, light in pairs:
        if cat != "暗坑" and len(py) > 0:
            doubled.append((cat, py, light))

    return expanded + doubled


# ═══════════════════════════════════════════════════════════════════
# 从 examples 目录自动提取（辅助数据源）
# ═══════════════════════════════════════════════════════════════════

def _extract_from_examples() -> List[tuple]:
    """从 examples/ 目录的 .light 文件提取代码片段

    注意：部分 .light 文件使用旧语法，需要标注但不用于核心训练
    """
    examples_dir = os.path.join(_PROJECT_DIR, 'examples')
    pairs = []

    if not os.path.isdir(examples_dir):
        return pairs

    for fname in sorted(os.listdir(examples_dir)):
        if not fname.endswith('.light'):
            continue
        filepath = os.path.join(examples_dir, fname)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        if not content:
            continue

        # 检测是否为旧语法（含"结束"、"变量"、"参数"等旧关键字）
        is_old_syntax = any(kw in content for kw in ['结束', '变量 ', '参数。', '模 '])

        # 检测是否为 v3.2 新语法
        is_new_syntax = any(kw in content for kw in ['接收', '遍历', '设 '])

        if is_new_syntax and not is_old_syntax:
            pairs.append(("示例-" + fname.replace('.light', ''), "", content))

    return pairs


# ═══════════════════════════════════════════════════════════════════
# 指令模板
# ═══════════════════════════════════════════════════════════════════

_INSTRUCTIONS = [
    "将以下Python代码翻译为光明v3.2代码。",
    "请把下面的Python代码转换成光明语法。",
    "翻译：将Python代码改写为光明代码。",
    "用光明v3.2语法重写以下Python代码。",
    "将Python翻译成光明。",
    "将Python代码转为光明代码：",
    "请将以下代码翻译为光明：",
    "Python→光明翻译：",
    "用光明语法表达以下Python代码：",
    "将下面的Python改写成光明v3.2：",
]


# ═══════════════════════════════════════════════════════════════════
# 输出 JSONL
# ═══════════════════════════════════════════════════════════════════

def build_dataset(output_path: str = None) -> List[Dict]:
    """构建 SFT 训练集

    Args:
        output_path: 输出 JSONL 文件路径，None 则输出到 tools/ai_copilot/sft_dataset.jsonl

    Returns:
        数据列表
    """
    # 1. 手工对照对 + 变体扩充
    all_pairs = _expand_variants(_HANDCRAFTED)

    # 2. 转换为 JSONL 格式
    dataset = []
    for cat, py_code, light_code in all_pairs:
        instruction = random.choice(_INSTRUCTIONS)
        dataset.append({
            "instruction": instruction,
            "input": py_code,
            "output": light_code,
            "category": cat,
        })

    # 3. 打乱顺序
    random.shuffle(dataset)

    # 4. 写入文件
    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'sft_dataset.jsonl'
        )

    with open(output_path, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    return dataset


def print_stats(dataset: List[Dict]):
    """打印数据集统计信息"""
    print(f"总条数: {len(dataset)}")
    print()

    # 按类别统计
    categories = {}
    for item in dataset:
        cat = item['category']
        categories[cat] = categories.get(cat, 0) + 1

    print("按语法类别:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat:8s} {count:4d} 条")

    # 输入/输出长度统计
    input_lens = [len(item['input']) for item in dataset]
    output_lens = [len(item['output']) for item in dataset]
    print()
    print(f"输入长度: 最短 {min(input_lens)} / 最长 {max(input_lens)} / 平均 {sum(input_lens)//len(input_lens)}")
    print(f"输出长度: 最短 {min(output_lens)} / 最长 {max(output_lens)} / 平均 {sum(output_lens)//len(output_lens)}")

    # 空输入条目（纯光明示例，无对应 Python）
    no_input = sum(1 for item in dataset if not item['input'].strip())
    if no_input:
        print(f"\n⚠ 无Python输入的条目: {no_input} 条（仅含光明端）")


if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    import argparse
    parser = argparse.ArgumentParser(description='光明 SFT 训练集构造器')
    parser.add_argument('--output', '-o', default=None, help='输出 JSONL 文件路径')
    parser.add_argument('--stats', action='store_true', help='只显示统计信息')
    args = parser.parse_args()

    dataset = build_dataset(args.output)
    print_stats(dataset)

    output_path = args.output or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'sft_dataset.jsonl'
    )
    print(f"\n已写入: {output_path}")
