#!/usr/bin/env python3
"""
光明翻译器测试 - 经典 Python 代码翻译
使用 ollama light-translator-v5 模型
"""
import json
import subprocess
import os
import time

# 读取与 local_infer.py 一致的 SYSTEM_PROMPT
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
    "- 运算: 加/减/乘/除以/取余/幂/加上/减去/乘以\n"
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
    "- 复合赋值: x += y -> 设 x 为 x 加 y; x -= y -> 设 x 为 x 减 y; x *= y -> 设 x 为 x 乘以 y; x /= y -> 设 x 为 x 除以 y\n"
    "- 负数字面量: -1, -100 等负数保持原样，返回 -1 而非 返回 减 1\n"
    "- 整除运算: // 和 / 均翻译为 除以\n"
    "- 取余运算: % 翻译为 取余\n"
    "- 幂运算: ** 翻译为 幂\n"
    "- 方法调用: 对象方法调用保持原样，如 s.upper(), lst.append(x), d.get(key) 不翻译方法名\n"
    "- break/continue: break -> 跳出; continue -> 跳过; 不可混用 返回 替代 break\n"
    "- 多返回值: return a, b 保持原样; x, y = func() 分别赋值\n"
    "- 异常类型: 捕获具体异常类型，如 捕获 ZeroDivisionError 为 e\n"
    "只输出光明代码，不要解释。"
)

MODEL = "light-translator-v5"

# 经典 Python 测试用例 - 覆盖各类语法
TEST_CASES = [
    # === 基础语法 ===
    {
        "id": "basic_01",
        "category": "变量赋值",
        "python": 'x = 10\nname = "hello"\nprint(x, name)',
        "expected_keywords": ["设 x 为", "定义", "打印"],
        "check_rules": ["变量名保持英文", "字符串用定义"]
    },
    {
        "id": "basic_02",
        "category": "条件判断",
        "python": 'score = 85\nif score >= 90:\n    grade = "A"\nelif score >= 80:\n    grade = "B"\nelse:\n    grade = "C"\nprint(grade)',
        "expected_keywords": ["如果", "否则若", "否则"],
        "check_rules": ["elif -> 否则若", "变量名保持英文"]
    },
    {
        "id": "basic_03",
        "category": "for循环",
        "python": 'for i in range(5):\n    print(i)',
        "expected_keywords": ["遍历", "打印"],
        "check_rules": ["range保留", "变量名保持英文"]
    },
    {
        "id": "basic_04",
        "category": "while循环",
        "python": 'count = 0\nwhile count < 10:\n    count += 1\nprint(count)',
        "expected_keywords": ["当", "加上"],
        "check_rules": ["while -> 当", "+= -> 加上"]
    },
    {
        "id": "basic_05",
        "category": "break_continue",
        "python": 'for i in range(10):\n    if i == 3:\n        continue\n    if i == 7:\n        break\n    print(i)',
        "expected_keywords": ["遍历", "跳过", "跳出"],
        "check_rules": ["break -> 跳出", "continue -> 跳过"]
    },

    # === 运算符 ===
    {
        "id": "ops_01",
        "category": "算术运算",
        "python": 'a = 10\nb = 3\nprint(a + b)\nprint(a - b)\nprint(a * b)\nprint(a / b)\nprint(a // b)\nprint(a % b)\nprint(a ** b)',
        "expected_keywords": ["加", "减", "乘", "除以", "取余", "幂"],
        "check_rules": ["// -> 除以", "% -> 取余", "** -> 幂"]
    },
    {
        "id": "ops_02",
        "category": "复合赋值",
        "python": 'x = 10\nx += 5\nx -= 3\nx *= 2\nx //= 4\nprint(x)',
        "expected_keywords": ["加上", "减去", "乘以", "除以"],
        "check_rules": ["+= -> 加上", "-= -> 减去", "*= -> 乘以", "//= -> 除以"]
    },
    {
        "id": "ops_03",
        "category": "负数",
        "python": 'def get_index():\n    return -1\n\ntemp = -100\nprint(get_index(), temp)',
        "expected_keywords": ["返回 -1"],
        "check_rules": ["负数保持原样", "返回 -1 而非 返回 减 1"]
    },
    {
        "id": "ops_04",
        "category": "逻辑运算",
        "python": 'a = True\nb = False\nprint(a and b)\nprint(a or b)\nprint(not a)',
        "expected_keywords": ["且", "或", "非"],
        "check_rules": ["and -> 且", "or -> 或", "not -> 非"]
    },

    # === 函数 ===
    {
        "id": "func_01",
        "category": "函数定义",
        "python": 'def greet(name):\n    return f"Hello, {name}!"\n\nprint(greet("World"))',
        "expected_keywords": ["段落", "接收", "返回"],
        "check_rules": ["def -> 段落", "f-string保留"]
    },
    {
        "id": "func_02",
        "category": "多返回值",
        "python": 'def divmod_result(a, b):\n    return a // b, a % b\n\nq, r = divmod_result(17, 5)\nprint(q, r)',
        "expected_keywords": ["段落", "返回", "除以", "取余"],
        "check_rules": ["多返回值保持原样", "// -> 除以"]
    },
    {
        "id": "func_03",
        "category": "递归",
        "python": 'def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n\nprint(factorial(5))',
        "expected_keywords": ["段落", "如果", "返回", "乘以"],
        "check_rules": ["递归调用保持函数名", "<= -> 小于等于"]
    },
    {
        "id": "func_04",
        "category": "lambda",
        "python": 'square = lambda x: x ** 2\nprint(square(5))',
        "expected_keywords": ["接收", "返回", "幂"],
        "check_rules": ["lambda翻译", "** -> 幂"]
    },

    # === 数据结构 ===
    {
        "id": "data_01",
        "category": "列表操作",
        "python": 'lst = [1, 2, 3]\nlst.append(4)\nlst[0] = 10\nprint(lst)\nprint(len(lst))',
        "expected_keywords": ["设", "append", "len"],
        "check_rules": ["方法名保持英文", "len()保留"]
    },
    {
        "id": "data_02",
        "category": "列表推导",
        "python": 'squares = [x ** 2 for x in range(10)]\nprint(squares)',
        "expected_keywords": ["遍历", "幂"],
        "check_rules": ["列表推导式", "** -> 幂"]
    },
    {
        "id": "data_03",
        "category": "字典操作",
        "python": 'd = {"name": "Alice", "age": 30}\nprint(d["name"])\nd["age"] = 31\nprint(d.get("age"))',
        "expected_keywords": ["设", "打印"],
        "check_rules": ["字典保持原样", "方法名保持英文"]
    },
    {
        "id": "data_04",
        "category": "f-string",
        "python": 'name = "Alice"\nage = 30\nprint(f"{name} is {age} years old")',
        "expected_keywords": ["打印"],
        "check_rules": ["f-string保留", "变量名保持英文"]
    },

    # === 类与OOP ===
    {
        "id": "oop_01",
        "category": "类定义",
        "python": 'class Point:\n    def __init__(self, x, y):\n        self.x = x\n        self.y = y\n    \n    def distance(self):\n        return (self.x ** 2 + self.y ** 2) ** 0.5\n\np = Point(3, 4)\nprint(p.distance())',
        "expected_keywords": ["类", "构造", "己"],
        "check_rules": ["self -> 己", "__init__ -> 构造"]
    },
    {
        "id": "oop_02",
        "category": "类继承",
        "python": 'class Animal:\n    def __init__(self, name):\n        self.name = name\n    \n    def speak(self):\n        return f"{self.name} makes a sound"\n\nclass Dog(Animal):\n    def speak(self):\n        return f"{self.name} barks"\n\nd = Dog("Rex")\nprint(d.speak())',
        "expected_keywords": ["类", "继承", "构造"],
        "check_rules": ["继承语法", "方法重写"]
    },

    # === 异常处理 ===
    {
        "id": "exc_01",
        "category": "try_except",
        "python": 'try:\n    result = 10 / 0\nexcept ZeroDivisionError as e:\n    print(f"Error: {e}")\nfinally:\n    print("Done")',
        "expected_keywords": ["尝试", "捕获", "最终"],
        "check_rules": ["try -> 尝试", "except -> 捕获", "finally -> 最终"]
    },
    {
        "id": "exc_02",
        "category": "raise",
        "python": 'def check_age(age):\n    if age < 0:\n        raise ValueError("Age cannot be negative")\n    return age\n\nprint(check_age(25))',
        "expected_keywords": ["如果", "抛出"],
        "check_rules": ["raise -> 抛出", "异常类型保持英文"]
    },

    # === 文件操作 ===
    {
        "id": "file_01",
        "category": "文件读写",
        "python": 'with open("test.txt", "w") as f:\n    f.write("Hello")\n\nwith open("test.txt", "r") as f:\n    content = f.read()\nprint(content)',
        "expected_keywords": ["使用", "打开文件"],
        "check_rules": ["with -> 使用", "open -> 打开文件"]
    },

    # === 经典算法 ===
    {
        "id": "algo_01",
        "category": "冒泡排序",
        "python": 'def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n - i - 1):\n            if arr[j] > arr[j + 1]:\n                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n    return arr\n\nprint(bubble_sort([64, 34, 25, 12, 22, 11, 90]))',
        "expected_keywords": ["段落", "遍历", "如果"],
        "check_rules": ["嵌套循环", "交换语法"]
    },
    {
        "id": "algo_02",
        "category": "二分查找",
        "python": 'def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n\nprint(binary_search([1, 3, 5, 7, 9], 5))',
        "expected_keywords": ["段落", "当", "如果", "否则若", "返回 -1"],
        "check_rules": ["// -> 除以", "elif -> 否则若", "负数保持原样"]
    },
    {
        "id": "algo_03",
        "category": "Fibonacci",
        "python": 'def fib(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b\n\nfor i in range(10):\n    print(fib(i))',
        "expected_keywords": ["段落", "如果", "遍历", "返回"],
        "check_rules": ["多变量赋值", "range保留"]
    },
    {
        "id": "algo_04",
        "category": "质数判断",
        "python": 'def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n ** 0.5) + 1):\n        if n % i == 0:\n            return False\n    return True\n\nprint(is_prime(17))',
        "expected_keywords": ["段落", "如果", "遍历", "取余", "返回 假"],
        "check_rules": ["% -> 取余", "** -> 幂", "False -> 假"]
    },

    # === 综合复杂 ===
    {
        "id": "complex_01",
        "category": "FizzBuzz",
        "python": 'for i in range(1, 16):\n    if i % 15 == 0:\n        print("FizzBuzz")\n    elif i % 3 == 0:\n        print("Fizz")\n    elif i % 5 == 0:\n        print("Buzz")\n    else:\n        print(i)',
        "expected_keywords": ["遍历", "如果", "否则若", "取余", "打印"],
        "check_rules": ["elif -> 否则若", "% -> 取余", "多分支条件"]
    },
    {
        "id": "complex_02",
        "category": "高阶函数",
        "python": 'nums = [1, 2, 3, 4, 5]\nevens = list(filter(lambda x: x % 2 == 0, nums))\nsquared = list(map(lambda x: x ** 2, nums))\nprint(evens, squared)',
        "expected_keywords": ["筛选", "映射", "接收", "取余", "幂"],
        "check_rules": ["filter -> 筛选", "map -> 映射", "lambda翻译"]
    },
    {
        "id": "complex_03",
        "category": "字典推导",
        "python": 'words = ["hello", "world", "python"]\nword_lens = {w: len(w) for w in words}\nprint(word_lens)',
        "expected_keywords": ["遍历", "len"],
        "check_rules": ["字典推导式", "len()保留"]
    },
    {
        "id": "complex_04",
        "category": "装饰器",
        "python": 'def timer(func):\n    def wrapper(*args, **kwargs):\n        result = func(*args, **kwargs)\n        return result\n    return wrapper\n\n@timer\ndef say_hello():\n    print("Hello!")\n\nsay_hello()',
        "expected_keywords": ["段落", "标注"],
        "check_rules": ["装饰器翻译", "嵌套函数"]
    },
]


def call_ollama(model, prompt, system):
    """Call ollama API"""
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_ctx": 4096,
        }
    }
    
    import urllib.request
    import json as _json
    
    data = _json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        'http://localhost:11434/api/generate',
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = _json.loads(resp.read().decode('utf-8'))
            return result.get('response', '').strip()
    except Exception as e:
        return f"[ERROR] {e}"


def evaluate(test_case, light_output):
    """Evaluate translation quality"""
    issues = []
    passed_checks = []
    
    # Check expected keywords
    for kw in test_case.get('expected_keywords', []):
        if kw in light_output:
            passed_checks.append(f"keyword '{kw}' present")
        else:
            issues.append(f"MISSING keyword: '{kw}'")
    
    # Check specific rules
    for rule in test_case.get('check_rules', []):
        if "变量名保持英文" in rule:
            # Check no Chinese variable names in output (excluding keywords)
            # Simple heuristic: check if common Chinese variable patterns exist
            pass  # Hard to auto-check, skip
        elif "elif -> 否则若" in rule:
            if "否则如果" in light_output:
                issues.append("FOUND 否则如果 instead of 否则若")
            elif "否则若" in light_output or "否则" in light_output:
                passed_checks.append("elif correctly translated")
        elif "** -> 幂" in rule:
            if "次方" in light_output:
                issues.append("FOUND 次方 instead of 幂")
            elif "幂" in light_output:
                passed_checks.append("** correctly translated to 幂")
        elif "% -> 取余" in rule:
            if "模" in light_output and "取余" not in light_output:
                issues.append("FOUND 模 instead of 取余")
            elif "取余" in light_output:
                passed_checks.append("% correctly translated")
        elif "// -> 除以" in rule:
            if "除以" in light_output:
                passed_checks.append("// correctly translated")
            else:
                issues.append("MISSING 除以 for // operator")
        elif "负数保持原样" in rule:
            if "返回 减 1" in light_output or "返回 - 1" in light_output:
                issues.append("Negative number incorrectly translated")
            elif "返回 -1" in light_output:
                passed_checks.append("Negative number preserved")
        elif "break -> 跳出" in rule:
            if "跳出" in light_output:
                passed_checks.append("break correctly translated")
            else:
                issues.append("MISSING 跳出 for break")
        elif "continue -> 跳过" in rule:
            if "跳过" in light_output:
                passed_checks.append("continue correctly translated")
            else:
                issues.append("MISSING 跳过 for continue")
        elif "self -> 己" in rule:
            if "己." in light_output:
                passed_checks.append("self correctly translated")
            else:
                issues.append("MISSING 己. for self")
        elif "try -> 尝试" in rule:
            if "尝试" in light_output:
                passed_checks.append("try correctly translated")
            else:
                issues.append("MISSING 尝试 for try")
        elif "except -> 捕获" in rule:
            if "捕获" in light_output:
                passed_checks.append("except correctly translated")
            else:
                issues.append("MISSING 捕获 for except")
        elif "finally -> 最终" in rule:
            if "最终" in light_output:
                passed_checks.append("finally correctly translated")
            else:
                issues.append("MISSING 最终 for finally")
        elif "raise -> 抛出" in rule:
            if "抛出" in light_output:
                passed_checks.append("raise correctly translated")
            else:
                issues.append("MISSING 抛出 for raise")
        elif "with -> 使用" in rule:
            if "使用" in light_output:
                passed_checks.append("with correctly translated")
            else:
                issues.append("MISSING 使用 for with")
    
    # Check for common errors
    if "否则如果" in light_output:
        issues.append("ERROR: 否则如果 should be 否则若")
    if "次方" in light_output:
        issues.append("ERROR: 次方 should be 幂")
    if "整除" in light_output:
        issues.append("ERROR: 整除 is not a valid keyword")
    if "范围(" in light_output:
        issues.append("ERROR: 范围( should be range(")
    if "长度(" in light_output:
        issues.append("ERROR: 长度( should be len(")
    if "返回 减" in light_output:
        issues.append("ERROR: 返回 减 should be 返回 -")
    if "返回 0" in light_output and "返回 0.5" not in light_output:
        pass  # This is fine, 0 is not a negative
    if "self" in light_output:
        issues.append("WARNING: self found in output, should be 己")
    
    # Check variable name preservation (basic heuristic)
    import re
    # Look for Chinese chars that are NOT known keywords
    # This is a simplified check
    chinese_runs = re.findall(r'[\u4e00-\u9fff]+', light_output)
    # Known safe keywords
    safe = {"段落", "接收", "返回", "如果", "否则", "否则若", "若", "则",
            "遍历", "当", "跳出", "跳过", "设", "为", "定义", "等于",
            "加", "减", "乘", "除", "除以", "取余", "幂", "加上", "减去", "乘以",
            "大于", "小于", "不等于", "大于等于", "小于等于",
            "且", "或", "非", "真", "假", "空",
            "打印", "类", "继承", "属性", "构造", "新建",
            "己", "父", "尝试", "捕获", "最终", "抛出",
            "使用", "标注", "静态", "类方法", "特性",
            "之", "的", "并", "至", "到", "步",
            "读取文件", "打开文件", "写入文件",
            "筛选", "映射", "排序", "反转",
            "匹配", "情况", "导入", "导出", "从",
            "异步", "等待", "模块", "标准库",
            "公有", "私有", "保护"}
    
    for run in chinese_runs:
        if run not in safe and len(run) > 1:
            # Check if it's a compound of safe words
            is_compound = False
            for s in safe:
                if run.startswith(s) and run[len(s):] in safe:
                    is_compound = True
                    break
            if not is_compound:
                issues.append(f"SUSPECT: Chinese text '{run}' may be translated variable name")
    
    # Determine verdict
    critical_errors = [i for i in issues if i.startswith("ERROR")]
    missing_keywords = [i for i in issues if "MISSING keyword" in i]
    
    if critical_errors:
        verdict = "FAIL"
    elif missing_keywords:
        verdict = "PARTIAL"
    elif issues:
        verdict = "PARTIAL"
    else:
        verdict = "PASS"
    
    return {
        "verdict": verdict,
        "issues": issues,
        "passed_checks": passed_checks,
    }


def main():
    print(f"光明翻译器测试 - {MODEL}")
    print(f"测试用例数: {len(TEST_CASES)}")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    results = []
    
    for i, tc in enumerate(TEST_CASES):
        print(f"\n[{i+1}/{len(TEST_CASES)}] {tc['id']} - {tc['category']}")
        print(f"Python:\n{tc['python']}")
        
        prompt = f"用光明v3.2语法重写以下Python代码。\n{tc['python']}"
        
        start_time = time.time()
        light_output = call_ollama(MODEL, prompt, SYSTEM_PROMPT)
        elapsed = time.time() - start_time
        
        print(f"光明:\n{light_output}")
        
        eval_result = evaluate(tc, light_output)
        eval_result["elapsed"] = round(elapsed, 1)
        
        print(f"评估: {eval_result['verdict']} ({eval_result['elapsed']}s)")
        if eval_result["issues"]:
            print(f"问题: {eval_result['issues']}")
        if eval_result["passed_checks"]:
            print(f"通过: {eval_result['passed_checks']}")
        
        results.append({
            "id": tc["id"],
            "category": tc["category"],
            "python": tc["python"],
            "light": light_output,
            "verdict": eval_result["verdict"],
            "issues": eval_result["issues"],
            "passed_checks": eval_result["passed_checks"],
            "elapsed": eval_result["elapsed"],
        })
    
    # Summary
    print("\n" + "=" * 80)
    print("汇总")
    print("=" * 80)
    
    verdicts = {}
    for r in results:
        v = r["verdict"]
        verdicts[v] = verdicts.get(v, 0) + 1
    
    total = len(results)
    print(f"总计: {total}")
    for v in ["PASS", "PARTIAL", "FAIL"]:
        count = verdicts.get(v, 0)
        pct = count / total * 100 if total > 0 else 0
        print(f"  {v}: {count} ({pct:.1f}%)")
    
    # Category breakdown
    print("\n按类别:")
    cat_stats = {}
    for r in results:
        cat = r["category"]
        if cat not in cat_stats:
            cat_stats[cat] = {"PASS": 0, "PARTIAL": 0, "FAIL": 0}
        cat_stats[cat][r["verdict"]] += 1
    
    for cat, stats in sorted(cat_stats.items()):
        print(f"  {cat}: PASS={stats['PASS']} PARTIAL={stats['PARTIAL']} FAIL={stats['FAIL']}")
    
    # Common issues
    print("\n高频问题:")
    issue_freq = {}
    for r in results:
        for issue in r["issues"]:
            # Simplify issue text for frequency counting
            key = issue.split(":")[0] if ":" in issue else issue
            issue_freq[key] = issue_freq.get(key, 0) + 1
    
    for issue, count in sorted(issue_freq.items(), key=lambda x: -x[1]):
        print(f"  [{count}x] {issue}")
    
    # Save results
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Save JSON
    with open(os.path.join(output_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Save markdown report
    with open(os.path.join(output_dir, "翻译对照表.md"), "w", encoding="utf-8") as f:
        f.write("# 光明翻译器测试 - 翻译对照表\n\n")
        f.write(f"**模型**: {MODEL}\n")
        f.write(f"**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**测试用例**: {total}\n\n")
        
        for r in results:
            f.write(f"## {r['id']} - {r['category']} [{r['verdict']}]\n\n")
            f.write(f"**Python:**\n```python\n{r['python']}\n```\n\n")
            f.write(f"**光明:**\n```\n{r['light']}\n```\n\n")
            if r["issues"]:
                f.write(f"**问题:**\n")
                for iss in r["issues"]:
                    f.write(f"- {iss}\n")
                f.write("\n")
            if r["passed_checks"]:
                f.write(f"**通过项:**\n")
                for pc in r["passed_checks"]:
                    f.write(f"- {pc}\n")
                f.write("\n")
            f.write(f"**耗时**: {r['elapsed']}s\n\n---\n\n")
    
    print(f"\n结果已保存到: {output_dir}")
    print(f"  - results.json")
    print(f"  - 翻译对照表.md")


if __name__ == "__main__":
    main()
