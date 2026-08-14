"""
段言 SFT 训练集构造器 v10（v5.2 扩展版）

为 ERNIE-4.5-0.3B 微调生成 Python→段言 翻译对照数据。
新增 2000+ 条，覆盖以下内容：
  - LLVM 后端新特性：异常处理（try/catch/finally/throw）、async/await
  - 框架库用法：单元测试框架、日志系统、配置管理、HTTP 服务端
  - duanpub 包使用：包导入、搜索、安装
  - 增量编译：--incremental 标志使用
  - 上下文管理器（使用...为...）
  - 迭代器协议
  - 模式匹配（match/case）
  - 编译器缓存相关

用法：
    python build_sft_dataset_v10.py          # 生成训练集到 sft_dataset_v10.jsonl
    python build_sft_dataset_v10.py --stats  # 只显示统计信息
"""

import json
import os
import random
import re
import sys
from collections import Counter

# ── 路径 ──
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_V9_PATH = os.path.join(_SCRIPT_DIR, 'sft_dataset.jsonl')
_OUTPUT_PATH = os.path.join(_SCRIPT_DIR, 'sft_dataset_v10.jsonl')

# ── 指令模板 ──
_INSTRUCTIONS = [
    "将以下Python代码翻译为段言v5.2代码。",
    "请把下面的Python代码转换成段言语法。",
    "翻译：将Python代码改写为段言代码。",
    "用段言v5.2语法重写以下Python代码。",
    "将Python翻译成段言。",
    "将Python代码转为段言代码：",
    "请将以下代码翻译为段言：",
    "Python→段言翻译：",
    "用段言语法表达以下Python代码：",
    "将下面的Python改写成段言v5.2：",
]

# ═══════════════════════════════════════════════════════════════════
# 手工对照对：Python → 段言 v5.2
# 每条 = (category, python_code, duan_code)
# ═══════════════════════════════════════════════════════════════════

_HANDCRAFTED: list = [
    # ── LLVM 后端异常处理（try/catch/finally/throw）───────────────
    ("LLVM异常", "try:\n    result = may_throw()\nexcept Exception as e:\n    print(f'Error: {e}')",
     "尝试：\n    设 result 为 可能抛出()\n捕获 异常 为 e：\n    打印(f\"错误: {e}\")"),
    ("LLVM异常", "try:\n    f = open('data.txt')\n    content = f.read()\nexcept FileNotFoundError:\n    content = ''\nfinally:\n    print('done')",
     "尝试：\n    设 f 为 打开(\"data.txt\")\n    设 content 为 f.读取()\n捕获 文件未找到：\n    设 content 为 \"\"\n最终：\n    打印(\"完成\")"),
    ("LLVM异常", "try:\n    x = int(s)\nexcept ValueError:\n    x = 0\nfinally:\n    cleanup()",
     "尝试：\n    设 x 为 整数(s)\n捕获 数值错误：\n    设 x 为 0\n最终：\n    清理()"),
    ("LLVM异常", "try:\n    conn = open_connection()\n    conn.send(data)\nexcept ConnectionError:\n    retry()\nfinally:\n    conn.close()",
     "尝试：\n    设 conn 为 打开连接()\n    conn.发送(data)\n捕获 连接错误：\n    重试()\n最终：\n    conn.关闭()"),
    ("LLVM异常", "raise ValueError('invalid input')",
     "抛出 数值错误(\"无效输入\")"),
    ("LLVM异常", "raise RuntimeError('system failure')",
     "抛出 运行时错误(\"系统故障\")"),
    ("LLVM异常", "try:\n    process_data()\nexcept (TypeError, ValueError) as e:\n    log_error(e)\n    raise",
     "尝试：\n    处理数据()\n捕获 类型错误, 数值错误 为 e：\n    记录错误(e)\n    抛出"),
    ("LLVM异常", "def safe_divide(a, b):\n    try:\n        return a / b\n    except ZeroDivisionError:\n        return float('inf')",
     "段落 安全除法 接收 a, b：\n    尝试：\n        返回 a 除以 b\n    捕获 除以零：\n        返回 无穷大"),
    ("LLVM异常", "try:\n    obj = registry.get(key)\n    obj.process()\nexcept KeyError:\n    print('not found')\nexcept AttributeError:\n    print('invalid method')",
     "尝试：\n    设 obj 为 注册表.获取(key)\n    obj.处理()\n捕获 键错误：\n    打印(\"未找到\")\n捕获 属性错误：\n    打印(\"无效方法\")"),
    ("LLVM异常", "try:\n    buffer = allocate(size)\n    write(buffer, data)\nexcept MemoryError:\n    free_all()\n    return None\nfinally:\n    release_lock()",
     "尝试：\n    设 buffer 为 分配内存(size)\n    写入(buffer, data)\n捕获 内存错误：\n    全部释放()\n    返回 空\n最终：\n    释放锁()"),
    ("LLVM异常", "raise IOError('disk full')",
     "抛出 IO错误(\"磁盘已满\")"),
    ("LLVM异常", "try:\n    result = risky_call()\nexcept Exception:\n    result = fallback()\nfinally:\n    cleanup()",
     "尝试：\n    设 result 为 危险调用()\n捕获 异常：\n    设 result 为 回退()\n最终：\n    清理()"),
    ("LLVM异常", "def parse_config(text):\n    try:\n        import json\n        return json.loads(text)\n    except json.JSONDecodeError:\n        return {}",
     "段落 解析配置 接收 text：\n    尝试：\n        导入 JSON\n        返回 JSON.解析(text)\n    捕获 JSON.解析错误：\n        返回 {}"),
    ("LLVM异常", "try:\n    with open(path) as f:\n        return f.read()\nexcept (FileNotFoundError, PermissionError) as e:\n    print(f'Cannot read {path}: {e}')\n    return ''",
     "尝试：\n    使用 文件 为 打开(path)：\n        返回 文件.读取()\n捕获 文件未找到, 权限错误 为 e：\n    打印(f\"无法读取 {path}: {e}\")\n    返回 \"\""),
    ("LLVM异常", "raise TimeoutError('operation timed out')",
     "抛出 超时错误(\"操作超时\")"),
    ("LLVM异常", "try:\n    send_request()\nexcept NetworkError:\n    reconnect()\n    send_request()",
     "尝试：\n    发送请求()\n捕获 网络错误：\n    重新连接()\n    发送请求()"),
    ("LLVM异常", "try:\n    value = cache.get(key)\n    if value is None:\n        raise KeyError\n    return value\nexcept KeyError:\n    value = compute(key)\n    cache.put(key, value)\n    return value",
     "尝试：\n    设 value 为 缓存.获取(key)\n    如果 value 等于 空：\n        抛出 键错误\n    返回 value\n捕获 键错误：\n    设 value 为 计算(key)\n    缓存.放入(key, value)\n    返回 value"),
    ("LLVM异常", "try:\n    validate_input(data)\nexcept ValidationError as e:\n    return {'valid': False, 'errors': e.errors}\nfinally:\n    log_attempt()",
     "尝试：\n    验证输入(data)\n捕获 验证错误 为 e：\n    返回 {\"valid\": 假, \"errors\": e.错误列表}\n最终：\n    记录尝试()"),
    ("LLVM异常", "raise NotImplementedError('subclass must implement')",
     "抛出 未实现错误(\"子类必须实现\")"),
    ("LLVM异常", "try:\n    result = do_work()\nexcept:\n    result = None\n    print('work failed')\nfinally:\n    print('work attempted')",
     "尝试：\n    设 result 为 执行工作()\n捕获 异常：\n    设 result 为 空\n    打印(\"工作失败\")\n最终：\n    打印(\"工作已尝试\")"),

    # ── async/await 异步作用域/协程 ──────────────────────────────
    ("异步", "async def fetch_data(url):\n    return await http_get(url)",
     "异步段落 获取数据 接收 url：\n    返回 等待 HTTP获取(url)"),
    ("异步", "async def process_many(items):\n    results = []\n    for item in items:\n        result = await process(item)\n        results.append(result)\n    return results",
     "异步段落 批量处理 接收 items：\n    设 results 为 []\n    遍历 item 于 items：\n        设 result 为 等待 处理(item)\n        results.追加(result)\n    返回 results"),
    ("异步", "async def main():\n    data = await fetch_data('https://example.com')\n    print(data)",
     "异步段落 主函数：\n    设 data 为 等待 获取数据(\"https://example.com\")\n    打印(data)"),
    ("异步", "async def read_all(files):\n    for f in files:\n        content = await read_file(f)\n        print(f'Read {len(content)} bytes')",
     "异步段落 全部读取 接收 files：\n    遍历 f 于 files：\n        设 content 为 等待 读取文件(f)\n        打印(f\"读取了 {len(content)} 字节\")"),
    ("异步", "async def timeout_after(seconds, coro):\n    try:\n        return await asyncio.wait_for(coro, timeout=seconds)\n    except asyncio.TimeoutError:\n        return None",
     "异步段落 超时后 接收 秒数, 协程：\n    尝试：\n        返回 等待 异步等待.等待(协程, 超时=秒数)\n    捕获 超时错误：\n        返回 空"),
    ("异步", "async def gather_example():\n    result1, result2 = await asyncio.gather(task1(), task2())\n    return result1 + result2",
     "异步段落 聚合示例：\n    设 result1, result2 为 等待 异步收集(任务1(), 任务2())\n    返回 result1 加上 result2"),
    ("异步", "async def stream_reader(stream):\n    async for chunk in stream:\n        process(chunk)",
     "异步段落 流读取 接收 stream：\n    异步遍历 chunk 于 stream：\n        处理(chunk)"),
    ("异步", "async def consumer():\n    while True:\n        item = await queue.get()\n        if item is None:\n            break\n        await process(item)",
     "异步段落 消费者：\n    当 真：\n        设 item 为 等待 队列.获取()\n        如果 item 等于 空：\n            跳出\n        等待 处理(item)"),
    ("异步", "async def producer():\n    for i in range(10):\n        await queue.put(i)\n    await queue.put(None)",
     "异步段落 生产者：\n    遍历 i 于 0至9：\n        等待 队列.放入(i)\n    等待 队列.放入(空)"),
    ("异步", "async def retry_async(func, max_retries=3):\n    for attempt in range(max_retries):\n        try:\n            return await func()\n        except Exception:\n            if attempt == max_retries - 1:\n                raise\n            await asyncio.sleep(1)",
     "异步段落 重试异步 接收 函数, 最大重试次数：\n    遍历 attempt 于 0至最大重试次数减去1：\n        尝试：\n            返回 等待 函数()\n        捕获 异常：\n            如果 attempt 等于 最大重试次数 减去 1：\n                抛出\n            等待 异步睡眠(1)"),
    ("异步", "async def file_reader(path):\n    async with aiofiles.open(path) as f:\n        content = await f.read()\n        return content",
     "异步段落 文件读取器 接收 路径：\n    异步使用 文件 为 异步文件.打开(路径)：\n        设 content 为 等待 文件.读取()\n        返回 content"),
    ("异步", "async def multi_fetch(urls):\n    tasks = [fetch(url) for url in urls]\n    return await asyncio.gather(*tasks)",
     "异步段落 多路获取 接收 urls：\n    设 tasks 为 []\n    遍历 url 于 urls：\n        tasks.追加(获取(url))\n    返回 等待 异步收集(*tasks)"),
    ("异步", "async def ping_server():\n    try:\n        response = await http_get('https://server.com/ping')\n        return response.status == 200\n    except Exception:\n        return False",
     "异步段落 测试服务器：\n    尝试：\n        设 response 为 等待 HTTP获取(\"https://server.com/ping\")\n        返回 response.状态码 等于 200\n    捕获 异常：\n        返回 假"),
    ("异步", "async def run_with_timeout(coro, timeout):\n    try:\n        return await asyncio.wait_for(coro, timeout=timeout)\n    except asyncio.TimeoutError:\n        return {'error': 'timeout'}",
     "异步段落 带超时运行 接收 协程, 超时：\n    尝试：\n        返回 等待 异步等待.等待(协程, 超时=超时)\n    捕获 超时错误：\n        返回 {\"error\": \"超时\"}"),
    ("异步", "async def safe_async_call(func):\n    try:\n        return await func()\n    except Exception as e:\n        print(f'Async error: {e}')\n        return None",
     "异步段落 安全异步调用 接收 函数：\n    尝试：\n        返回 等待 函数()\n    捕获 异常 为 e：\n        打印(f\"异步错误: {e}\")\n        返回 空"),

    # ── 单元测试框架 ──────────────────────────────────────────────
    ("单元测试", "def test_addition():\n    assert add(2, 3) == 5\n    assert add(-1, 1) == 0",
     "段落 测试加法：\n    断言 加法(2, 3) 等于 5\n    断言 加法(-1, 1) 等于 0"),
    ("单元测试", "def test_is_empty():\n    assert is_empty([]) == True\n    assert is_empty([1]) == False",
     "段落 测试是否为空：\n    断言 是否为空([]) 等于 真\n    断言 是否为空([1]) 等于 假"),
    ("单元测试", "def test_string_upper():\n    result = to_upper('hello')\n    assert result == 'HELLO'",
     "段落 测试字符串大写：\n    设 result 为 转大写(\"hello\")\n    断言 result 等于 \"HELLO\""),
    ("单元测试", "def test_divide_by_zero():\n    with pytest.raises(ZeroDivisionError):\n        divide(1, 0)",
     "段落 测试除以零：\n    使用 pytest.断言抛出(除以零)：\n        除法(1, 0)"),
    ("单元测试", "def test_user_creation():\n    user = create_user('Alice', 30)\n    assert user.name == 'Alice'\n    assert user.age == 30",
     "段落 测试用户创建：\n    设 user 为 创建用户(\"Alice\", 30)\n    断言 user.名称 等于 \"Alice\"\n    断言 user.年龄 等于 30"),
    ("单元测试", "def test_find_in_list():\n    items = [10, 20, 30, 40]\n    assert find_item(items, 30) == 2\n    assert find_item(items, 99) == -1",
     "段落 测试列表查找：\n    设 items 为 [10, 20, 30, 40]\n    断言 查找项(items, 30) 等于 2\n    断言 查找项(items, 99) 等于 -1"),
    ("单元测试", "def test_validate_email():\n    assert validate_email('test@example.com') == True\n    assert validate_email('invalid') == False",
     "段落 测试邮箱验证：\n    断言 验证邮箱(\"test@example.com\") 等于 真\n    断言 验证邮箱(\"invalid\") 等于 假"),
    ("单元测试", "def test_calculator_add():\n    calc = Calculator()\n    calc.add(5)\n    calc.add(3)\n    assert calc.result == 8",
     "段落 测试计算器加法：\n    设 calc 为 新建 计算器()\n    calc.加法(5)\n    calc.加法(3)\n    断言 calc.结果 等于 8"),
    ("单元测试", "def test_dictionary_merge():\n    d1 = {'a': 1, 'b': 2}\n    d2 = {'c': 3}\n    result = merge_dicts(d1, d2)\n    assert result == {'a': 1, 'b': 2, 'c': 3}",
     "段落 测试字典合并：\n    设 d1 为 {\"a\": 1, \"b\": 2}\n    设 d2 为 {\"c\": 3}\n    设 result 为 合并字典(d1, d2)\n    断言 result 等于 {\"a\": 1, \"b\": 2, \"c\": 3}"),
    ("单元测试", "def test_factorial_edge_cases():\n    assert factorial(0) == 1\n    assert factorial(1) == 1\n    assert factorial(5) == 120",
     "段落 测试阶乘边界：\n    断言 阶乘(0) 等于 1\n    断言 阶乘(1) 等于 1\n    断言 阶乘(5) 等于 120"),
    ("单元测试", "def test_sort_stability():\n    data = [('b', 2), ('a', 1), ('b', 1)]\n    sorted_data = stable_sort(data, key=lambda x: x[0])\n    assert sorted_data[0] == ('a', 1)",
     "段落 测试排序稳定性：\n    设 data 为 [(\"b\", 2), (\"a\", 1), (\"b\", 1)]\n    设 sorted_data 为 稳定排序(data, 键=lambda x: x[0])\n    断言 sorted_data[0] 等于 (\"a\", 1)"),
    ("单元测试", "def test_max_of_three():\n    assert max_of_three(1, 2, 3) == 3\n    assert max_of_three(5, 5, 5) == 5\n    assert max_of_three(-1, -5, 0) == 0",
     "段落 测试三数最大值：\n    断言 三数最大(1, 2, 3) 等于 3\n    断言 三数最大(5, 5, 5) 等于 5\n    断言 三数最大(-1, -5, 0) 等于 0"),

    # ── 日志系统 ──────────────────────────────────────────────────
    ("日志系统", "import logging\nlogging.basicConfig(level=logging.INFO)\nlogger = logging.getLogger(__name__)\nlogger.info('Application started')",
     "导入 日志\n日志.基础配置(级别=日志.信息)\n设 logger 为 日志.获取日志器(__name__)\nlogger.信息(\"应用已启动\")"),
    ("日志系统", "logger.debug('Processing item: %s', item_id)\nlogger.info('Operation completed')\nlogger.warning('Low disk space')\nlogger.error('Failed to connect')",
     "logger.调试(\"处理项目: %s\", item_id)\nlogger.信息(\"操作完成\")\nlogger.警告(\"磁盘空间不足\")\nlogger.错误(\"连接失败\")"),
    ("日志系统", "try:\n    result = process(data)\n    logger.info(f'Processed {len(data)} items: {result}')\nexcept Exception as e:\n    logger.exception(f'Processing failed: {e}')",
     "尝试：\n    设 result 为 处理(data)\n    logger.信息(f\"处理了 {len(data)} 项: {result}\")\n捕获 异常 为 e：\n    logger.异常(f\"处理失败: {e}\")"),
    ("日志系统", "import logging\nlogging.basicConfig(filename='app.log', level=logging.DEBUG,\n                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')",
     "导入 日志\n日志.基础配置(文件名=\"app.log\", 级别=日志.调试,\n                    格式=\"%(asctime)s - %(name)s - %(levelname)s - %(message)s\")"),
    ("日志系统", "logger = logging.getLogger('myapp')\nhandler = logging.FileHandler('myapp.log')\nhandler.setLevel(logging.WARNING)\nlogger.addHandler(handler)",
     "设 logger 为 日志.获取日志器(\"myapp\")\n设 handler 为 日志.文件处理器(\"myapp.log\")\nhandler.设置级别(日志.警告)\nlogger.添加处理器(handler)"),
    ("日志系统", "def setup_logger(name, log_file):\n    logger = logging.getLogger(name)\n    handler = logging.FileHandler(log_file)\n    formatter = logging.Formatter('%(levelname)s: %(message)s')\n    handler.setFormatter(formatter)\n    logger.addHandler(handler)\n    return logger",
     "段落 设置日志器 接收 名称, 日志文件：\n    设 logger 为 日志.获取日志器(名称)\n    设 handler 为 日志.文件处理器(日志文件)\n    设 formatter 为 日志.格式化器(\"%(levelname)s: %(message)s\")\n    handler.设置格式化器(formatter)\n    logger.添加处理器(handler)\n    返回 logger"),
    ("日志系统", "logger.info('User %s logged in from %s', user, ip)\nlogger.warning('Failed login attempt for %s', user)\nlogger.error('Database connection lost')",
     "logger.信息(\"用户 %s 从 %s 登录\", user, ip)\nlogger.警告(\"用户 %s 登录失败\", user)\nlogger.错误(\"数据库连接丢失\")"),
    ("日志系统", "def log_function_call(func):\n    def wrapper(*args, **kwargs):\n        logger.debug(f'Calling {func.__name__}')\n        result = func(*args, **kwargs)\n        logger.debug(f'{func.__name__} returned {result}')\n        return result\n    return wrapper",
     "段落 记录函数调用 接收 函数：\n    段落 包装器 接收 *args, **kwargs：\n        logger.调试(f\"调用 {函数.__name__}\")\n        设 result 为 函数(*args, **kwargs)\n        logger.调试(f\"{函数.__name__} 返回 {result}\")\n        返回 result\n    返回 包装器"),
    ("日志系统", "logging.basicConfig(level=logging.INFO)\nlogger = logging.getLogger(__name__)\nlogger.info('Starting data pipeline')\nlogger.info('Processing batch %d/%d', batch, total)\nlogger.info('Pipeline completed')",
     "日志.基础配置(级别=日志.信息)\n设 logger 为 日志.获取日志器(__name__)\nlogger.信息(\"启动数据管道\")\nlogger.信息(\"处理批次 %d/%d\", batch, total)\nlogger.信息(\"管道完成\")"),

    # ── 配置管理 ──────────────────────────────────────────────────
    ("配置管理", "config = {'host': 'localhost', 'port': 8080, 'debug': True}\nhost = config.get('host', '127.0.0.1')\nport = config.get('port', 3000)",
     "设 config 为 {\"host\": \"localhost\", \"port\": 8080, \"debug\": 真}\n设 host 为 config.get(\"host\", \"127.0.0.1\")\n设 port 为 config.get(\"port\", 3000)"),
    ("配置管理", "def load_config(path):\n    import json\n    with open(path) as f:\n        return json.load(f)\ndef save_config(path, config):\n    import json\n    with open(path, 'w') as f:\n        json.dump(config, f, indent=2)",
     "段落 加载配置 接收 路径：\n    导入 JSON\n    使用 文件 为 打开(路径)：\n        返回 JSON.加载(文件)\n段落 保存配置 接收 路径, 配置：\n    导入 JSON\n    使用 文件 为 打开(路径, \"w\")：\n        JSON.转储(配置, 文件, 缩进=2)"),
    ("配置管理", "DEFAULT_CONFIG = {'timeout': 30, 'retries': 3, 'cache_size': 100}\nconfig = DEFAULT_CONFIG.copy()\nconfig['timeout'] = 60",
     "设 默认配置 为 {\"timeout\": 30, \"retries\": 3, \"cache_size\": 100}\n设 config 为 默认配置.复制()\nconfig[\"timeout\"] = 60"),
    ("配置管理", "def merge_config(base, override):\n    result = base.copy()\n    for key, value in override.items():\n        result[key] = value\n    return result",
     "段落 合并配置 接收 基础, 覆盖：\n    设 result 为 基础.复制()\n    遍历 key, value 于 覆盖.项目()：\n        result[key] = value\n    返回 result"),
    ("配置管理", "db_config = {\n    'host': os.getenv('DB_HOST', 'localhost'),\n    'port': int(os.getenv('DB_PORT', '5432')),\n    'database': os.getenv('DB_NAME', 'app'),\n    'user': os.getenv('DB_USER', 'admin'),\n    'password': os.getenv('DB_PASS', '')\n}",
     "设 db_config 为 {\n    \"host\": 环境变量(\"DB_HOST\", \"localhost\"),\n    \"port\": 整数(环境变量(\"DB_PORT\", \"5432\")),\n    \"database\": 环境变量(\"DB_NAME\", \"app\"),\n    \"user\": 环境变量(\"DB_USER\", \"admin\"),\n    \"password\": 环境变量(\"DB_PASS\", \"\")\n}"),
    ("配置管理", "class Config:\n    def __init__(self):\n        self.settings = {}\n    def get(self, key, default=None):\n        return self.settings.get(key, default)\n    def set(self, key, value):\n        self.settings[key] = value\n    def load(self, path):\n        import json\n        with open(path) as f:\n            self.settings = json.load(f)",
     "类 配置：\n    属性 设置\n    构造：\n        己.设置 为 {}\n    段落 获取 接收 键, 默认值：\n        返回 己.设置.get(键, 默认值)\n    段落 设置 接收 键, 值：\n        己.设置[键] = 值\n    段落 加载 接收 路径：\n        导入 JSON\n        使用 文件 为 打开(路径)：\n            己.设置 为 JSON.加载(文件)"),
    ("配置管理", "app_config = {\n    'app_name': 'MyApp',\n    'version': '2.0.0',\n    'debug': False,\n    'features': ['auth', 'api', 'admin'],\n    'database': {'host': 'localhost', 'port': 3306}\n}",
     "设 app_config 为 {\n    \"app_name\": \"MyApp\",\n    \"version\": \"2.0.0\",\n    \"debug\": 假,\n    \"features\": [\"auth\", \"api\", \"admin\"],\n    \"database\": {\"host\": \"localhost\", \"port\": 3306}\n}"),

    # ── HTTP 服务端 ───────────────────────────────────────────────
    ("HTTP服务", "from http.server import HTTPServer, BaseHTTPRequestHandler\nclass Handler(BaseHTTPRequestHandler):\n    def do_GET(self):\n        self.send_response(200)\n        self.end_headers()\n        self.wfile.write(b'Hello, World!')",
     "从 HTTP服务器 导入 HTTPServer, BaseHTTPRequestHandler\n类 处理器 继承 BaseHTTPRequestHandler：\n    段落 do_GET：\n        己.发送响应(200)\n        己.结束头部()\n        己.输出文件.写入(b\"Hello, World!\")"),
    ("HTTP服务", "def run_server(host='0.0.0.0', port=8080):\n    server = HTTPServer((host, port), Handler)\n    print(f'Server running on {host}:{port}')\n    server.serve_forever()",
     "段落 运行服务器 接收 主机, 端口：\n    设 server 为 新建 HTTPServer((主机, 端口), 处理器)\n    打印(f\"服务器运行于 {主机}:{端口}\")\n    server.永久服务()"),
    ("HTTP服务", "def handle_request(method, path, body):\n    if method == 'GET' and path == '/':\n        return {'status': 200, 'body': 'Welcome'}\n    elif method == 'POST' and path == '/data':\n        return {'status': 201, 'body': 'Created'}\n    else:\n        return {'status': 404, 'body': 'Not Found'}",
     "段落 处理请求 接收 方法, 路径, 正文：\n    如果 方法 等于 \"GET\" 且 路径 等于 \"/\"：\n        返回 {\"status\": 200, \"body\": \"Welcome\"}\n    否则如果 方法 等于 \"POST\" 且 路径 等于 \"/data\"：\n        返回 {\"status\": 201, \"body\": \"Created\"}\n    否则：\n        返回 {\"status\": 404, \"body\": \"Not Found\"}"),
    ("HTTP服务", "def parse_headers(raw):\n    headers = {}\n    for line in raw.split('\\r\\n'):\n        if ': ' in line:\n            key, value = line.split(': ', 1)\n            headers[key.lower()] = value\n    return headers",
     "段落 解析头部 接收 raw：\n    设 headers 为 {}\n    遍历 line 于 字符串分割(raw, \"\\r\\n\")：\n        如果 字符串包含(line, \": \")：\n            设 key, value 为 字符串分割(line, \": \", 1)\n            headers[字符串转小写(key)] = value\n    返回 headers"),
    ("HTTP服务", "def create_response(status, body, content_type='text/plain'):\n    response = f'HTTP/1.1 {status}\\r\\n'\n    response += f'Content-Type: {content_type}\\r\\n'\n    response += f'Content-Length: {len(body)}\\r\\n'\n    response += '\\r\\n'\n    response += body\n    return response",
     "段落 创建响应 接收 状态码, 正文, 内容类型：\n    设 response 为 f\"HTTP/1.1 {状态码}\\r\\n\"\n    设 response 为 response 加上 f\"Content-Type: {内容类型}\\r\\n\"\n    设 response 为 response 加上 f\"Content-Length: {len(正文)}\\r\\n\"\n    设 response 为 response 加上 \"\\r\\n\"\n    设 response 为 response 加上 正文\n    返回 response"),
    ("HTTP服务", "def route_request(path):\n    routes = {\n        '/': home_page,\n        '/about': about_page,\n        '/api/users': users_api,\n        '/api/health': health_check\n    }\n    handler = routes.get(path, not_found)\n    return handler()",
     "段落 路由请求 接收 路径：\n    设 routes 为 {\n        \"/\": 首页,\n        \"/about\": 关于页,\n        \"/api/users\": 用户API,\n        \"/api/health\": 健康检查\n    }\n    设 handler 为 routes.get(路径, 未找到)\n    返回 handler()"),
    ("HTTP服务", "def parse_query_string(query):\n    params = {}\n    if query:\n        for pair in query.split('&'):\n            if '=' in pair:\n                key, value = pair.split('=', 1)\n                params[key] = value\n    return params",
     "段落 解析查询字符串 接收 query：\n    设 params 为 {}\n    如果 query：\n        遍历 pair 于 字符串分割(query, \"&\")：\n            如果 字符串包含(pair, \"=\")：\n                设 key, value 为 字符串分割(pair, \"=\", 1)\n                params[key] = value\n    返回 params"),
    ("HTTP服务", "def json_response(data, status=200):\n    import json\n    body = json.dumps(data, ensure_ascii=False)\n    response = create_response(status, body, 'application/json')\n    return response",
     "段落 JSON响应 接收 data, 状态码：\n    导入 JSON\n    设 body 为 JSON.转储(data, 确保ASCII=假)\n    设 response 为 创建响应(状态码, body, \"application/json\")\n    返回 response"),

    # ── duanpub 包使用 ────────────────────────────────────────────
    ("duanpub", "import duanpub\nresult = duanpub.search('http')\nprint(result)",
     "导入 段言包\n设 result 为 段言包.搜索(\"http\")\n打印(result)"),
    ("duanpub", "from duanpub import install, uninstall\ninstall('json-tools', version='1.2.0')",
     "从 段言包 导入 安装, 卸载\n安装(\"json-tools\", 版本=\"1.2.0\")"),
    ("duanpub", "from duanpub import PackageManager\npm = PackageManager()\npm.install('http-server')\npm.install('test-framework')",
     "从 段言包 导入 包管理器\n设 pm 为 新建 包管理器()\npm.安装(\"http-server\")\npm.安装(\"test-framework\")"),
    ("duanpub", "from duanpub import search, info\nresults = search('logging')\nfor pkg in results:\n    print(f'{pkg.name} - {pkg.version}')\n    details = info(pkg.name)\n    print(f'  Description: {details.description}')",
     "从 段言包 导入 搜索, 信息\n设 results 为 搜索(\"logging\")\n遍历 pkg 于 results：\n    打印(f\"{pkg.名称} - {pkg.版本}\")\n    设 details 为 信息(pkg.名称)\n    打印(f\"  描述: {details.描述}\")"),
    ("duanpub", "from duanpub import PublishCommand\npublish = PublishCommand()\npublish.run(package_dir='./my_package', version='1.0.0')",
     "从 段言包 导入 发布命令\n设 publish 为 新建 发布命令()\npublish.运行(包目录=\"./my_package\", 版本=\"1.0.0\")"),
    ("duanpub", "from duanpub import check_updates\nupdates = check_updates()\nfor pkg in updates:\n    print(f'Update {pkg.name}: {pkg.current_version} -> {pkg.latest_version}')",
     "从 段言包 导入 检查更新\n设 updates 为 检查更新()\n遍历 pkg 于 updates：\n    打印(f\"更新 {pkg.名称}: {pkg.当前版本} -> {pkg.最新版本}\")"),
    ("duanpub", "from duanpub import list_installed\ninstalled = list_installed()\nprint(f'Installed packages: {len(installed)}')",
     "从 段言包 导入 列出已安装\n设 installed 为 列出已安装()\n打印(f\"已安装包数: {len(installed)}\")"),
    ("duanpub", "import duanpub as dp\ndp.add_repository('https://duanpub.example.com/repo')\ndp.update_all()",
     "导入 段言包 为 段包\n段包.添加仓库(\"https://duanpub.example.com/repo\")\n段包.全部更新()"),
    ("duanpub", "from duanpub import resolve_dependencies\ndeps = resolve_dependencies('web-app')\nprint(f'Dependencies: {deps}')",
     "从 段言包 导入 解析依赖\n设 deps 为 解析依赖(\"web-app\")\n打印(f\"依赖: {deps}\")"),
    ("duanpub", "def ensure_package(name):\n    from duanpub import is_installed, install\n    if not is_installed(name):\n        print(f'Installing {name}...')\n        install(name)\n    else:\n        print(f'{name} already installed')",
     "段落 确保包 接收 名称：\n    从 段言包 导入 是否已安装, 安装\n    如果 非 是否已安装(名称)：\n        打印(f\"正在安装 {名称}...\")\n        安装(名称)\n    否则：\n        打印(f\"{名称} 已安装\")"),
    ("duanpub", "from duanpub import Package\npkg = Package('my-app')\npkg.set_version('2.0.0')\npkg.add_dependency('json', '>=1.0')\npkg.save()",
     "从 段言包 导入 包\n设 pkg 为 新建 包(\"my-app\")\npkg.设置版本(\"2.0.0\")\npkg.添加依赖(\"json\", \">=1.0\")\npkg.保存()"),

    # ── 增量编译 ──────────────────────────────────────────────────
    ("增量编译", "duan build --incremental",
     "段言 构建 --增量编译"),
    ("增量编译", "duan build --incremental --output out.duan",
     "段言 构建 --增量编译 --输出 out.duan"),
    ("增量编译", "duan build --incremental --watch",
     "段言 构建 --增量编译 --监视"),
    ("增量编译", "duan build --incremental --verbose",
     "段言 构建 --增量编译 --详细"),
    ("增量编译", "duan build --incremental --cache-dir .duan_cache",
     "段言 构建 --增量编译 --缓存目录 .duan_cache"),
    ("增量编译", "def incremental_build(files):\n    for f in files:\n        if needs_recompile(f):\n            compile_file(f)\n        else:\n            print(f'Skipping {f}, unchanged')",
     "段落 增量构建 接收 files：\n    遍历 f 于 files：\n        如果 需要重编译(f)：\n            编译文件(f)\n        否则：\n            打印(f\"跳过 {f}, 未变更\")"),
    ("增量编译", "duan build --incremental --skip-tests",
     "段言 构建 --增量编译 --跳过测试"),
    ("增量编译", "duan build --incremental --emit=llvm",
     "段言 构建 --增量编译 --输出=llvm"),
    ("增量编译", "duan build --incremental --optimize O2",
     "段言 构建 --增量编译 --优化 O2"),
    ("增量编译", "def check_cache_status(file):\n    import os\n    cache_file = f'.duan_cache/{file}.cache'\n    if os.path.exists(cache_file):\n        cache_time = os.path.getmtime(cache_file)\n        source_time = os.path.getmtime(file)\n        if cache_time >= source_time:\n            return 'cached'\n    return 'stale'",
     "段落 检查缓存状态 接收 file：\n    导入 文件系统\n    设 cache_file 为 f\".duan_cache/{file}.cache\"\n    如果 文件系统.存在(cache_file)：\n        设 cache_time 为 文件系统.获取修改时间(cache_file)\n        设 source_time 为 文件系统.获取修改时间(file)\n        如果 cache_time 大于等于 source_time：\n            返回 \"已缓存\"\n    返回 \"过期\""),

    # ── 编译器缓存 ────────────────────────────────────────────────
    ("编译器缓存", "duan clean-cache",
     "段言 清理缓存"),
    ("编译器缓存", "duan cache-stats",
     "段言 缓存统计"),
    ("编译器缓存", "duan build --cache-dir /tmp/duan_cache",
     "段言 构建 --缓存目录 /tmp/duan_cache"),
    ("编译器缓存", "duan build --no-cache",
     "段言 构建 --无缓存"),
    ("编译器缓存", "duan build --cache-ttl 3600",
     "段言 构建 --缓存生存 3600"),
    ("编译器缓存", "def clear_build_cache():\n    import os\n    cache_dir = '.duan_cache'\n    if os.path.exists(cache_dir):\n        for f in os.listdir(cache_dir):\n            os.remove(os.path.join(cache_dir, f))\n        print('Cache cleared')",
     "段落 清理构建缓存：\n    导入 文件系统\n    设 cache_dir 为 \".duan_cache\"\n    如果 文件系统.存在(cache_dir)：\n        遍历 f 于 文件系统.列表目录(cache_dir)：\n            文件系统.删除(文件系统.连接路径(cache_dir, f))\n        打印(\"缓存已清理\")"),
    ("编译器缓存", "duan build --cache-policy lazy",
     "段言 构建 --缓存策略 懒惰"),
    ("编译器缓存", "duan build --cache-policy eager",
     "段言 构建 --缓存策略 积极"),
    ("编译器缓存", "duan build --cache-compress",
     "段言 构建 --缓存压缩"),
    ("编译器缓存", "duan build --cache-max-size 500MB",
     "段言 构建 --缓存最大大小 500MB"),

    # ── 更多上下文管理器 ──────────────────────────────────────────
    ("上下文", "with open('file.txt', 'r') as f:\n    for line in f:\n        print(line.strip())",
     "使用 文件 为 打开(\"file.txt\", \"r\")：\n    遍历 line 于 文件：\n        打印(字符串去空白(line))"),
    ("上下文", "with open('log.txt', 'a') as f:\n    f.write(f'Event: {event}\\n')",
     "使用 文件 为 打开(\"log.txt\", \"a\")：\n    文件.写入(f\"事件: {event}\\n\")"),
    ("上下文", "with open('src.txt') as src, open('dst.txt', 'w') as dst:\n    for line in src:\n        dst.write(line)",
     "使用 源文件 为 打开(\"src.txt\"), 目标文件 为 打开(\"dst.txt\", \"w\")：\n    遍历 line 于 源文件：\n        目标文件.写入(line)"),
    ("上下文", "class ManagedResource:\n    def __enter__(self):\n        self.acquire()\n        return self\n    def __exit__(self, *args):\n        self.release()",
     "类 托管资源：\n    段落 __进入__：\n        己.获取()\n        返回 己\n    段落 __退出__ 接收 *args：\n        己.释放()"),
    ("上下文", "with db.transaction() as tx:\n    tx.execute('INSERT INTO users VALUES (?, ?)', (name, age))\n    tx.execute('UPDATE counters SET val = val + 1')",
     "使用 tx 为 数据库.事务()：\n    tx.执行(\"INSERT INTO users VALUES (?, ?)\", (name, age))\n    tx.执行(\"UPDATE counters SET val = val + 1\")"),
    ("上下文", "with redirect_stdout(file):\n    print('This goes to file')",
     "使用 重定向标准输出(文件)：\n    打印(\"这将被写入文件\")"),
    ("上下文", "with tempfile.TemporaryDirectory() as tmpdir:\n    process_files(tmpdir)",
     "使用 tmpdir 为 临时文件.临时目录()：\n    处理文件(tmpdir)"),
    ("上下文", "with lock:\n    if shared_resource.available():\n        shared_resource.use()",
     "使用 锁：\n    如果 共享资源.可用()：\n        共享资源.使用()"),
    ("上下文", "class TimeIt:\n    def __enter__(self):\n        self.start = time.time()\n        return self\n    def __exit__(self, *args):\n        self.elapsed = time.time() - self.start\n        print(f'Elapsed: {self.elapsed:.3f}s')",
     "类 计时器：\n    属性 开始\n    属性 已过时间\n    段落 __进入__：\n        己.开始 为 当前时间()\n        返回 己\n    段落 __退出__ 接收 *args：\n        己.已过时间 为 当前时间() 减去 己.开始\n        打印(f\"耗时: {己.已过时间:.3f}秒\")"),
    ("上下文", "with open('data.bin', 'rb') as f:\n    chunk = f.read(1024)\n    while chunk:\n        process(chunk)\n        chunk = f.read(1024)",
     "使用 文件 为 打开(\"data.bin\", \"rb\")：\n    设 chunk 为 文件.读取(1024)\n    当 chunk：\n        处理(chunk)\n        设 chunk 为 文件.读取(1024)"),
    ("上下文", "with open('output.txt', 'w') as f:\n    for i in range(100):\n        f.write(f'Line {i}\\n')",
     "使用 文件 为 打开(\"output.txt\", \"w\")：\n    遍历 i 于 0至99：\n        文件.写入(f\"第 {i} 行\\n\")"),
    ("上下文", "class SuppressErrors:\n    def __enter__(self):\n        return self\n    def __exit__(self, exc_type, exc_val, exc_tb):\n        if exc_type:\n            print(f'Suppressed: {exc_val}')\n            return True",
     "类 抑制错误：\n    段落 __进入__：\n        返回 己\n    段落 __退出__ 接收 异常类型, 异常值, 异常追踪：\n        如果 异常类型：\n            打印(f\"已抑制: {异常值}\")\n            返回 真"),

    # ── 更多迭代器协议 ────────────────────────────────────────────
    ("迭代器", "class MapIterator:\n    def __init__(self, func, iterable):\n        self.func = func\n        self.iter = iter(iterable)\n    def __iter__(self):\n        return self\n    def __next__(self):\n        return self.func(next(self.iter))",
     "类 映射迭代器：\n    属性 函数\n    属性 源迭代器\n    构造 接收 函数, 可迭代对象：\n        己.函数 为 函数\n        己.源迭代器 为 迭代(可迭代对象)\n    段落 __迭代__：\n        返回 己\n    段落 __下一项__：\n        返回 己.函数(下一项(己.源迭代器))"),
    ("迭代器", "class FilterIterator:\n    def __init__(self, predicate, iterable):\n        self.predicate = predicate\n        self.iter = iter(iterable)\n    def __iter__(self):\n        return self\n    def __next__(self):\n        while True:\n            item = next(self.iter)\n            if self.predicate(item):\n                return item",
     "类 筛选迭代器：\n    属性 判断\n    属性 源迭代器\n    构造 接收 判断, 可迭代对象：\n        己.判断 为 判断\n        己.源迭代器 为 迭代(可迭代对象)\n    段落 __迭代__：\n        返回 己\n    段落 __下一项__：\n        当 真：\n            设 item 为 下一项(己.源迭代器)\n            如果 己.判断(item)：\n                返回 item"),
    ("迭代器", "class CountDown:\n    def __init__(self, start):\n        self.current = start\n    def __iter__(self):\n        return self\n    def __next__(self):\n        if self.current < 0:\n            raise StopIteration()\n        val = self.current\n        self.current -= 1\n        return val",
     "类 倒计时器：\n    属性 当前值\n    构造 接收 开始值：\n        己.当前值 为 开始值\n    段落 __迭代__：\n        返回 己\n    段落 __下一项__：\n        如果 己.当前值 小于 0：\n            抛出 迭代停止()\n        设 val 为 己.当前值\n        设 己.当前值 为 己.当前值 减去 1\n        返回 val"),
    ("迭代器", "class Repeat:\n    def __init__(self, value, times):\n        self.value = value\n        self.times = times\n        self.count = 0\n    def __iter__(self):\n        return self\n    def __next__(self):\n        if self.count >= self.times:\n            raise StopIteration()\n        self.count += 1\n        return self.value",
     "类 重复器：\n    属性 值\n    属性 次数\n    属性 计数\n    构造 接收 值, 次数：\n        己.值 为 值\n        己.次数 为 次数\n        己.计数 为 0\n    段落 __迭代__：\n        返回 己\n    段落 __下一项__：\n        如果 己.计数 大于等于 己.次数：\n            抛出 迭代停止()\n        设 己.计数 为 己.计数 加上 1\n        返回 己.值"),
    ("迭代器", "class Cycle:\n    def __init__(self, iterable):\n        self.items = list(iterable)\n        self.index = 0\n    def __iter__(self):\n        return self\n    def __next__(self):\n        if not self.items:\n            raise StopIteration()\n        val = self.items[self.index]\n        self.index = (self.index + 1) % len(self.items)\n        return val",
     "类 循环器：\n    属性 元素列表\n    属性 索引\n    构造 接收 可迭代对象：\n        己.元素列表 为 列表(可迭代对象)\n        己.索引 为 0\n    段落 __迭代__：\n        返回 己\n    段落 __下一项__：\n        如果 非 己.元素列表：\n            抛出 迭代停止()\n        设 val 为 己.元素列表[己.索引]\n        设 己.索引 为 (己.索引 加上 1) 取余 len(己.元素列表)\n        返回 val"),
    ("迭代器", "class TakeWhile:\n    def __init__(self, predicate, iterable):\n        self.predicate = predicate\n        self.iter = iter(iterable)\n        self.done = False\n    def __iter__(self):\n        return self\n    def __next__(self):\n        if self.done:\n            raise StopIteration()\n        item = next(self.iter)\n        if self.predicate(item):\n            return item\n        self.done = True\n        raise StopIteration()",
     "类 条件取迭代器：\n    属性 判断\n    属性 源迭代器\n    属性 已完成\n    构造 接收 判断, 可迭代对象：\n        己.判断 为 判断\n        己.源迭代器 为 迭代(可迭代对象)\n        己.已完成 为 假\n    段落 __迭代__：\n        返回 己\n    段落 __下一项__：\n        如果 己.已完成：\n            抛出 迭代停止()\n        设 item 为 下一项(己.源迭代器)\n        如果 己.判断(item)：\n            返回 item\n        设 己.已完成 为 真\n        抛出 迭代停止()"),
    ("迭代器", "class ZipIterator:\n    def __init__(self, *iterables):\n        self.iters = [iter(it) for it in iterables]\n    def __iter__(self):\n        return self\n    def __next__(self):\n        return tuple(next(it) for it in self.iters)",
     "类 压缩迭代器：\n    属性 迭代器列表\n    构造 接收 *可迭代对象：\n        设 己.迭代器列表 为 []\n        遍历 it 于 可迭代对象：\n            己.迭代器列表.追加(迭代(it))\n    段落 __迭代__：\n        返回 己\n    段落 __下一项__：\n        设 result 为 []\n        遍历 it 于 己.迭代器列表：\n            result.追加(下一项(it))\n        返回 元组(result)"),
    ("迭代器", "for val in countdown:\n    print(f'T-minus {val}')",
     "遍历 val 于 倒计时器：\n    打印(f\"倒计时 {val}\")"),
    ("迭代器", "for item in filter_iter:\n    if item > 0:\n        print(item)",
     "遍历 item 于 筛选迭代器：\n    如果 item 大于 0：\n        打印(item)"),

    # ── 更多模式匹配 ──────────────────────────────────────────────
    ("模式匹配", "match value:\n    case 0:\n        print('none')\n    case 1 | 2 | 3:\n        print('few')\n    case _:\n        print('many')",
     "匹配 值：\n    当 0：\n        打印(\"无\")\n    当 1 | 2 | 3：\n        打印(\"少量\")\n    当 _：\n        打印(\"多个\")"),
    ("模式匹配", "match result:\n    case {'type': 'text', 'content': c}:\n        print(f'Text: {c}')\n    case {'type': 'image', 'url': u}:\n        print(f'Image: {u}')\n    case _:\n        print('Unknown type')",
     "匹配 result：\n    当 {\"type\": \"text\", \"content\": c}：\n        打印(f\"文本: {c}\")\n    当 {\"type\": \"image\", \"url\": u}：\n        打印(f\"图片: {u}\")\n    当 _：\n        打印(\"未知类型\")"),
    ("模式匹配", "match event:\n    case ('click', x, y):\n        handle_click(x, y)\n    case ('keypress', key):\n        handle_keypress(key)\n    case ('resize', w, h):\n        handle_resize(w, h)",
     "匹配 event：\n    当 (\"click\", x, y)：\n        处理点击(x, y)\n    当 (\"keypress\", key)：\n        处理按键(key)\n    当 (\"resize\", w, h)：\n        处理缩放(w, h)"),
    ("模式匹配", "match data:\n    case [x, y, *rest]:\n        print(f'First: {x}, Second: {y}, Rest: {len(rest)}')\n    case [x]:\n        print(f'Only: {x}')\n    case []:\n        print('Empty')",
     "匹配 data：\n    当 [x, y, *rest]：\n        打印(f\"首个: {x}, 第二: {y}, 剩余: {len(rest)}\")\n    当 [x]：\n        打印(f\"唯一: {x}\")\n    当 []：\n        打印(\"空\")"),
    ("模式匹配", "match command.split():\n    case ['git', 'commit', '-m', msg]:\n        git_commit(msg)\n    case ['git', 'push', remote]:\n        git_push(remote)\n    case ['git', 'pull']:\n        git_pull()\n    case _:\n        print('Unknown git command')",
     "匹配 字符串分割(command)：\n    当 [\"git\", \"commit\", \"-m\", msg]：\n        提交(msg)\n    当 [\"git\", \"push\", remote]：\n        推送(remote)\n    当 [\"git\", \"pull\"]：\n        拉取()\n    当 _：\n        打印(\"未知 git 命令\")"),
    ("模式匹配", "match point:\n    case (0, 0):\n        print('origin')\n    case (x, y) if x == y:\n        print(f'on diagonal: ({x},{y})')\n    case (x, y):\n        print(f'point: ({x},{y})')",
     "匹配 point：\n    当 (0, 0)：\n        打印(\"原点\")\n    当 (x, y) 若 x 等于 y：\n        打印(f\"在对角线: ({x},{y})\")\n    当 (x, y)：\n        打印(f\"点: ({x},{y})\")"),
    ("模式匹配", "match status:\n    case 200:\n        return 'OK'\n    case 301 | 302:\n        return 'Redirect'\n    case 401 | 403:\n        return 'Auth Error'\n    case 500 | 502 | 503:\n        return 'Server Error'\n    case code:\n        return f'Unknown: {code}'",
     "匹配 status：\n    当 200：\n        返回 \"OK\"\n    当 301 | 302：\n        返回 \"重定向\"\n    当 401 | 403：\n        返回 \"认证错误\"\n    当 500 | 502 | 503：\n        返回 \"服务器错误\"\n    当 code：\n        返回 f\"未知: {code}\""),
    ("模式匹配", "match config:\n    case {'host': h, 'port': p} if p > 0:\n        connect(h, p)\n    case {'host': h}:\n        connect(h, 8080)\n    case _:\n        print('Invalid config')",
     "匹配 config：\n    当 {\"host\": h, \"port\": p} 若 p 大于 0：\n        连接(h, p)\n    当 {\"host\": h}：\n        连接(h, 8080)\n    当 _：\n        打印(\"无效配置\")"),
    ("模式匹配", "match values:\n    case [a, b, c, *rest]:\n        return a + b + c\n    case [a, b]:\n        return a * b\n    case [a]:\n        return a ** 2\n    case _:\n        return 0",
     "匹配 values：\n    当 [a, b, c, *rest]：\n        返回 a 加上 b 加上 c\n    当 [a, b]：\n        返回 a 乘以 b\n    当 [a]：\n        返回 a 的 2 次方\n    当 _：\n        返回 0"),

    # ── 补充已有类别条目 ──────────────────────────────────────────
    ("复合", "def tokenize(text):\n    tokens = []\n    current = ''\n    for c in text:\n        if c == ' ' or c == '\\n':\n            if current:\n                tokens.append(current)\n                current = ''\n        else:\n            current += c\n    if current:\n        tokens.append(current)\n    return tokens",
     "段落 分词 接收 text：\n    设 tokens 为 []\n    设 current 为 \"\"\n    遍历 c 于 text：\n        如果 c 等于 \" \" 或 c 等于 \"\\n\"：\n            如果 current：\n                tokens.追加(current)\n                设 current 为 \"\"\n        否则：\n            设 current 为 current 加上 c\n    如果 current：\n        tokens.追加(current)\n    返回 tokens"),
    ("复合", "def find_duplicates(items):\n    seen = {}\n    duplicates = []\n    for item in items:\n        if item in seen:\n            if seen[item] == 1:\n                duplicates.append(item)\n            seen[item] += 1\n        else:\n            seen[item] = 1\n    return duplicates",
     "段落 查找重复 接收 items：\n    设 seen 为 {}\n    设 duplicates 为 []\n    遍历 item 于 items：\n        如果 item 于 seen：\n            如果 seen[item] 等于 1：\n                duplicates.追加(item)\n            seen[item] = seen[item] 加上 1\n        否则：\n            seen[item] = 1\n    返回 duplicates"),
    ("复合", "def read_csv_line(line):\n    fields = []\n    current = ''\n    in_quotes = False\n    for c in line:\n        if c == '\"' and not in_quotes:\n            in_quotes = True\n        elif c == '\"' and in_quotes:\n            in_quotes = False\n        elif c == ',' and not in_quotes:\n            fields.append(current)\n            current = ''\n        else:\n            current += c\n    fields.append(current)\n    return fields",
     "段落 解析CSV行 接收 line：\n    设 fields 为 []\n    设 current 为 \"\"\n    设 in_quotes 为 假\n    遍历 c 于 line：\n        如果 c 等于 \"\\\"\" 且 非 in_quotes：\n            设 in_quotes 为 真\n        否则如果 c 等于 \"\\\"\" 且 in_quotes：\n            设 in_quotes 为 假\n        否则如果 c 等于 \",\" 且 非 in_quotes：\n            fields.追加(current)\n            设 current 为 \"\"\n        否则：\n            设 current 为 current 加上 c\n    fields.追加(current)\n    返回 fields"),
    ("复合", "def set_operations(a, b):\n    union = a.copy()\n    for x in b:\n        if x not in union:\n            union.append(x)\n    intersection = []\n    for x in a:\n        if x in b:\n            intersection.append(x)\n    difference = []\n    for x in a:\n        if x not in b:\n            difference.append(x)\n    return {'union': union, 'intersection': intersection, 'difference': difference}",
     "段落 集合运算 接收 a, b：\n    设 union 为 a.复制()\n    遍历 x 于 b：\n        如果 x 不 于 union：\n            union.追加(x)\n    设 intersection 为 []\n    遍历 x 于 a：\n        如果 x 于 b：\n            intersection.追加(x)\n    设 difference 为 []\n    遍历 x 于 a：\n        如果 x 不 于 b：\n            difference.追加(x)\n    返回 {\"union\": union, \"intersection\": intersection, \"difference\": difference}"),
    ("复合", "def encode_base64(data):\n    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'\n    result = ''\n    i = 0\n    while i < len(data):\n        chunk = data[i:i+3]\n        padding = 3 - len(chunk)\n        chunk += [0] * padding\n        b = (chunk[0] << 16) + (chunk[1] << 8) + chunk[2]\n        result += chars[(b >> 18) & 63]\n        result += chars[(b >> 12) & 63]\n        result += chars[(b >> 6) & 63] if padding < 2 else '='\n        result += chars[b & 63] if padding < 1 else '='\n        i += 3\n    return result",
     "段落 编码Base64 接收 data：\n    设 chars 为 \"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/\"\n    设 result 为 \"\"\n    设 i 为 0\n    当 i 小于 len(data)：\n        设 chunk 为 data[i:i+3]\n        设 padding 为 3 减去 len(chunk)\n        设 b 为 (chunk[0] 左移 16) 加上 (chunk[1] 左移 8) 加上 chunk[2]\n        设 result 为 result 加上 chars[(b 右移 18) 且 63]\n        设 result 为 result 加上 chars[(b 右移 12) 且 63]\n        如果 padding 小于 2：\n            设 result 为 result 加上 chars[(b 右移 6) 且 63]\n        否则：\n            设 result 为 result 加上 \"=\"\n        如果 padding 小于 1：\n            设 result 为 result 加上 chars[b 且 63]\n        否则：\n            设 result 为 result 加上 \"=\"\n        设 i 为 i 加上 3\n    返回 result"),
    ("复合", "def group_by(items, key_func):\n    groups = {}\n    for item in items:\n        key = key_func(item)\n        if key not in groups:\n            groups[key] = []\n        groups[key].append(item)\n    return groups",
     "段落 分组 接收 items, 键函数：\n    设 groups 为 {}\n    遍历 item 于 items：\n        设 key 为 键函数(item)\n        如果 key 不 于 groups：\n            groups[key] = []\n        groups[key].追加(item)\n    返回 groups"),
    ("复合", "def chunked(lst, size):\n    result = []\n    for i in range(0, len(lst), size):\n        chunk = []\n        for j in range(i, min(i + size, len(lst))):\n            chunk.append(lst[j])\n        result.append(chunk)\n    return result",
     "段落 分块 接收 lst, 大小：\n    设 result 为 []\n    设 i 为 0\n    当 i 小于 len(lst)：\n        设 chunk 为 []\n        设 j 为 i\n        当 j 小于 i 加上 大小 且 j 小于 len(lst)：\n            chunk.追加(lst[j])\n            设 j 为 j 加上 1\n        result.追加(chunk)\n        设 i 为 i 加上 大小\n    返回 result"),
    ("复合", "def flatten(nested):\n    result = []\n    for item in nested:\n        if isinstance(item, list):\n            sub = flatten(item)\n            for x in sub:\n                result.append(x)\n        else:\n            result.append(item)\n    return result",
     "段落 展平 接收 nested：\n    设 result 为 []\n    遍历 item 于 nested：\n        如果 实例检查(item, 列表)：\n            设 sub 为 展平(item)\n            遍历 x 于 sub：\n                result.追加(x)\n        否则：\n            result.追加(item)\n    返回 result"),
    ("复合", "def parse_query_string(query):\n    params = {}\n    if not query:\n        return params\n    for pair in query.split('&'):\n        if '=' in pair:\n            key, value = pair.split('=', 1)\n            params[key] = value\n    return params",
     "段落 解析查询字符串 接收 query：\n    设 params 为 {}\n    如果 非 query：\n        返回 params\n    遍历 pair 于 字符串分割(query, \"&\")：\n        如果 字符串包含(pair, \"=\")：\n            设 key, value 为 字符串分割(pair, \"=\", 1)\n            params[key] = value\n    返回 params"),

    # ── 更多 LLVM 异常补充 ──
    ("LLVM异常", "try:\n    result = compute()\nexcept ArithmeticError:\n    result = 0\n    print('Arithmetic error suppressed')",
     "尝试：\n    设 result 为 计算()\n捕获 算术错误：\n    设 result 为 0\n    打印(\"算术错误已抑制\")"),
    ("LLVM异常", "try:\n    data = load_resource(name)\nexcept ResourceWarning:\n    data = load_default()\n    print('Using default resource')",
     "尝试：\n    设 data 为 加载资源(name)\n捕获 资源警告：\n    设 data 为 加载默认()\n    打印(\"使用默认资源\")"),
    ("LLVM异常", "try:\n    process_payment(amount)\nexcept InsufficientFunds:\n    print('Insufficient balance')\n    return False\nexcept PaymentFailed:\n    print('Payment service error')\n    return False\nfinally:\n    log_payment_attempt(amount)",
     "尝试：\n    处理支付(amount)\n捕获 余额不足：\n    打印(\"余额不足\")\n    返回 假\n捕获 支付失败：\n    打印(\"支付服务错误\")\n    返回 假\n最终：\n    记录支付尝试(amount)"),
    ("LLVM异常", "try:\n    connect_to_service()\nexcept ConnectionError:\n    print('Reconnecting...')\n    reconnect()\n    connect_to_service()",
     "尝试：\n    连接到服务()\n捕获 连接错误：\n    打印(\"重新连接中...\")\n    重新连接()\n    连接到服务()"),
    ("LLVM异常", "try:\n    parse_user_input(text)\nexcept ParseError as e:\n    print(f'Parse error at line {e.line}: {e.message}')\n    return default_value()",
     "尝试：\n    解析用户输入(text)\n捕获 解析错误 为 e：\n    打印(f\"解析错误 第 {e.行号} 行: {e.消息}\")\n    返回 默认值()"),

    # ── 更多单元测试 ──
    ("单元测试", "def test_stack():\n    s = Stack()\n    assert s.is_empty()\n    s.push(1)\n    s.push(2)\n    assert s.pop() == 2\n    assert s.pop() == 1\n    assert s.is_empty()",
     "段落 测试栈：\n    设 s 为 新建 栈()\n    断言 s.是否为空()\n    s.入栈(1)\n    s.入栈(2)\n    断言 s.出栈() 等于 2\n    断言 s.出栈() 等于 1\n    断言 s.是否为空()"),
    ("单元测试", "def test_list_operations():\n    lst = [3, 1, 4, 1, 5]\n    assert len(lst) == 5\n    assert max(lst) == 5\n    assert min(lst) == 1\n    assert sorted(lst) == [1, 1, 3, 4, 5]",
     "段落 测试列表操作：\n    设 lst 为 [3, 1, 4, 1, 5]\n    断言 len(lst) 等于 5\n    断言 最大值(lst) 等于 5\n    断言 最小值(lst) 等于 1\n    断言 排序(lst) 等于 [1, 1, 3, 4, 5]"),
    ("单元测试", "def test_string_reversal():\n    assert reverse_string('hello') == 'olleh'\n    assert reverse_string('') == ''\n    assert reverse_string('a') == 'a'\n    assert reverse_string('racecar') == 'racecar'",
     "段落 测试字符串反转：\n    断言 反转字符串(\"hello\") 等于 \"olleh\"\n    断言 反转字符串(\"\") 等于 \"\"\n    断言 反转字符串(\"a\") 等于 \"a\"\n    断言 反转字符串(\"racecar\") 等于 \"racecar\""),
    ("单元测试", "def test_calculator_chain():\n    calc = Calculator()\n    calc.add(10)\n    calc.subtract(3)\n    calc.multiply(2)\n    calc.divide(7)\n    assert calc.result == 2",
     "段落 测试计算器链：\n    设 calc 为 新建 计算器()\n    calc.加法(10)\n    calc.减法(3)\n    calc.乘法(2)\n    calc.除法(7)\n    断言 calc.结果 等于 2"),
    ("单元测试", "def test_parse_numbers():\n    assert parse_int('42') == 42\n    assert parse_int('-10') == -10\n    assert parse_float('3.14') == 3.14\n    assert parse_float('1e10') == 1e10",
     "段落 测试数字解析：\n    断言 解析整数(\"42\") 等于 42\n    断言 解析整数(\"-10\") 等于 -10\n    断言 解析浮点数(\"3.14\") 等于 3.14\n    断言 解析浮点数(\"1e10\") 等于 1e10"),

    # ── 更多 duanpub ──
    ("duanpub", "from duanpub import create_project\ncreate_project('my_app', template='web')",
     "从 段言包 导入 创建项目\n创建项目(\"my_app\", 模板=\"web\")"),
    ("duanpub", "from duanpub import add_dependency\ndeps = ['json', 'http', 'test']\nfor dep in deps:\n    add_dependency('my_app', dep)",
     "从 段言包 导入 添加依赖\n设 deps 为 [\"json\", \"http\", \"test\"]\n遍历 dep 于 deps：\n    添加依赖(\"my_app\", dep)"),
    ("duanpub", "from duanpub import build_package\nbuild_package('./src', output_dir='./dist')",
     "从 段言包 导入 构建包\n构建包(\"./src\", 输出目录=\"./dist\")"),

    # ── 更多日志系统 ──
    ("日志系统", "def create_logger(module_name):\n    logger = logging.getLogger(module_name)\n    if not logger.handlers:\n        handler = logging.StreamHandler()\n        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')\n        handler.setFormatter(formatter)\n        logger.addHandler(handler)\n    return logger",
     "段落 创建日志器 接收 模块名：\n    设 logger 为 日志.获取日志器(模块名)\n    如果 非 logger.处理器：\n        设 handler 为 日志.流处理器()\n        设 formatter 为 日志.格式化器(\"%(asctime)s - %(name)s - %(levelname)s - %(message)s\")\n        handler.设置格式化器(formatter)\n        logger.添加处理器(handler)\n    返回 logger"),
    ("日志系统", "logger.info('Batch processing started')\nfor i, item in enumerate(items):\n    logger.debug('Processing item %d: %s', i, item)\n    process(item)\nlogger.info('Batch processing completed: %d items', len(items))",
     "logger.信息(\"批次处理开始\")\n遍历 i, item 于 枚举(items)：\n    logger.调试(\"处理项目 %d: %s\", i, item)\n    处理(item)\nlogger.信息(\"批次处理完成: %d 项\", len(items))"),

    # ── 更多配置管理 ──
    ("配置管理", "config = {\n    'server': {'host': '0.0.0.0', 'port': 8080},\n    'database': {'url': 'sqlite:///app.db', 'pool_size': 10},\n    'logging': {'level': 'INFO', 'file': 'app.log'}\n}\nport = config['server']['port']",
     "设 config 为 {\n    \"server\": {\"host\": \"0.0.0.0\", \"port\": 8080},\n    \"database\": {\"url\": \"sqlite:///app.db\", \"pool_size\": 10},\n    \"logging\": {\"level\": \"INFO\", \"file\": \"app.log\"}\n}\n设 port 为 config[\"server\"][\"port\"]"),
    ("配置管理", "def validate_config(config):\n    required = ['host', 'port', 'database']\n    for key in required:\n        if key not in config:\n            raise ValueError(f'Missing required config: {key}')\n    if not isinstance(config['port'], int):\n        raise TypeError('port must be integer')",
     "段落 验证配置 接收 config：\n    设 required 为 [\"host\", \"port\", \"database\"]\n    遍历 key 于 required：\n        如果 key 不 于 config：\n            抛出 数值错误(f\"缺少必需配置: {key}\")\n    如果 非 实例检查(config[\"port\"], 整数)：\n        抛出 类型错误(\"port 必须是整数\")"),

    # ── 更多 HTTP 服务 ──
    ("HTTP服务", "def handle_post(data):\n    try:\n        parsed = json.loads(data)\n        result = process_data(parsed)\n        return json_response(result, 201)\n    except json.JSONDecodeError:\n        return json_response({'error': 'invalid json'}, 400)",
     "段落 处理POST 接收 data：\n    尝试：\n        设 parsed 为 JSON.解析(data)\n        设 result 为 处理数据(parsed)\n        返回 JSON响应(result, 201)\n    捕获 JSON.解析错误：\n        返回 JSON响应({\"error\": \"无效JSON\"}, 400)"),
    ("HTTP服务", "def serve_static_file(path):\n    import os\n    full_path = os.path.join('www', path)\n    if os.path.exists(full_path) and os.path.isfile(full_path):\n        with open(full_path, 'rb') as f:\n            content = f.read()\n        return create_response(200, content)\n    return create_response(404, 'Not Found')",
     "段落 提供静态文件 接收 路径：\n    导入 文件系统\n    设 full_path 为 文件系统.连接路径(\"www\", 路径)\n    如果 文件系统.存在(full_path) 且 文件系统.是文件(full_path)：\n        使用 文件 为 打开(full_path, \"rb\")：\n            设 content 为 文件.读取()\n        返回 创建响应(200, content)\n    返回 创建响应(404, \"Not Found\")"),

    # ── 更多异步 ──
    ("异步", "async def batch_process(items):\n    results = []\n    for item in items:\n        result = await process_item(item)\n        results.append(result)\n    return results",
     "异步段落 批量处理 接收 items：\n    设 results 为 []\n    遍历 item 于 items：\n        设 result 为 等待 处理项目(item)\n        results.追加(result)\n    返回 results"),
    ("异步", "async def wait_all(tasks):\n    completed = []\n    for task in tasks:\n        result = await task\n        completed.append(result)\n    return completed",
     "异步段落 等待全部 接收 tasks：\n    设 completed 为 []\n    遍历 task 于 tasks：\n        设 result 为 等待 task\n        completed.追加(result)\n    返回 completed"),
    ("异步", "async def poll_until(condition, interval=1):\n    while True:\n        if condition():\n            return True\n        await asyncio.sleep(interval)",
     "异步段落 轮询直至 接收 条件, 间隔：\n    当 真：\n        如果 条件()：\n            返回 真\n        等待 异步睡眠(间隔)"),
    ("异步", "async def safe_fetch(url):\n    try:\n        return await fetch(url)\n    except Exception as e:\n        print(f'Failed to fetch {url}: {e}')\n        return None",
     "异步段落 安全获取 接收 url：\n    尝试：\n        返回 等待 获取(url)\n    捕获 异常 为 e：\n        打印(f\"获取 {url} 失败: {e}\")\n        返回 空"),
    ("异步", "async def parallel_map(func, items):\n    tasks = [func(item) for item in items]\n    return await asyncio.gather(*tasks)",
     "异步段落 并行映射 接收 函数, items：\n    设 tasks 为 []\n    遍历 item 于 items：\n        tasks.追加(函数(item))\n    返回 等待 异步收集(*tasks)"),

    # ── 更多编译器缓存 ──
    ("编译器缓存", "duan build --cache-dir .cache --cache-compress --cache-max-size 1GB",
     "段言 构建 --缓存目录 .cache --缓存压缩 --缓存最大大小 1GB"),
    ("编译器缓存", "duan build --cache-policy eager --cache-ttl 7200",
     "段言 构建 --缓存策略 积极 --缓存生存 7200"),
    ("编译器缓存", "def get_cache_size():\n    import os\n    total = 0\n    cache_dir = '.duan_cache'\n    if os.path.exists(cache_dir):\n        for f in os.listdir(cache_dir):\n            path = os.path.join(cache_dir, f)\n            if os.path.isfile(path):\n                total += os.path.getsize(path)\n    return total",
     "段落 获取缓存大小：\n    导入 文件系统\n    设 total 为 0\n    设 cache_dir 为 \".duan_cache\"\n    如果 文件系统.存在(cache_dir)：\n        遍历 f 于 文件系统.列表目录(cache_dir)：\n            设 path 为 文件系统.连接路径(cache_dir, f)\n            如果 文件系统.是文件(path)：\n                设 total 为 total 加上 文件系统.获取大小(path)\n    返回 total"),

    # ── 更多增量编译 ──
    ("增量编译", "duan build --incremental --cache-dir cache --emit llvm --optimize O3",
     "段言 构建 --增量编译 --缓存目录 cache --输出 llvm --优化 O3"),
    ("增量编译", "duan build --incremental --watch --verbose",
     "段言 构建 --增量编译 --监视 --详细"),
    ("增量编译", "def incremental_compile(project):\n    import os\n    cache = '.duan_cache'\n    if not os.path.exists(cache):\n        os.makedirs(cache)\n    for f in os.listdir(project):\n        if f.endswith('.duan'):\n            src_path = os.path.join(project, f)\n            cache_path = os.path.join(cache, f + '.llvm')\n            if os.path.exists(cache_path):\n                src_mtime = os.path.getmtime(src_path)\n                cache_mtime = os.path.getmtime(cache_path)\n                if cache_mtime >= src_mtime:\n                    print(f'Skipping {f}, up to date')\n                    continue\n            print(f'Compiling {f}...')\n            compile_file(src_path, cache_path)",
     "段落 增量编译 接收 project：\n    导入 文件系统\n    设 cache 为 \".duan_cache\"\n    如果 非 文件系统.存在(cache)：\n        文件系统.创建目录(cache)\n    遍历 f 于 文件系统.列表目录(project)：\n        如果 字符串结尾是(f, \".duan\")：\n            设 src_path 为 文件系统.连接路径(project, f)\n            设 cache_path 为 文件系统.连接路径(cache, f 加上 \".llvm\")\n            如果 文件系统.存在(cache_path)：\n                设 src_mtime 为 文件系统.获取修改时间(src_path)\n                设 cache_mtime 为 文件系统.获取修改时间(cache_path)\n                如果 cache_mtime 大于等于 src_mtime：\n                    打印(f\"跳过 {f}, 已是最新\")\n                    跳过\n            打印(f\"编译 {f}...\")\n            编译文件(src_path, cache_path)"),
]


# ═══════════════════════════════════════════════════════════════════
# 程序化生成：通过模板系统批量生成大量条目
# ═══════════════════════════════════════════════════════════════════

def _generate_programmatic() -> list:
    """通过模板系统批量生成 2000+ 条高质量条目"""
    generated = []

    # ── 通用变量名替换池 ──
    _PY_VARS = ["x", "n", "val", "data", "item", "key", "result", "count", "total", "flag", "name", "tmp"]
    _DUAN_VARS = ["甲", "数", "值", "资料", "项", "键", "结果", "计数", "总计", "标志", "名", "临时"]
    _PY_VARS2 = ["a", "b", "i", "s", "lst", "arr", "res", "cnt", "sum_", "v", "k", "d", "nm"]
    _DUAN_VARS2 = ["a", "b", "序", "文", "列表", "数组", "结果", "计数", "总和", "v", "k", "d", "nm"]

    _NUMBERS = [0, 1, 5, 10, 42, 100, 3.14, 2.5, -1, 999]
    _STRINGS = ["hello", "world", "test", "data", "input", "result", "config", "value", "key", "name"]
    _BOOLEANS = [(True, "真"), (False, "假")]

    # ── 更多的变量组合对 ──
    _VAR_PAIRS = [
        ("x", "甲"), ("n", "数"), ("val", "值"), ("data", "资料"),
        ("item", "项"), ("key", "键"), ("result", "结果"), ("count", "计数"),
        ("total", "总计"), ("flag", "标志"), ("name", "名"), ("tmp", "临时"),
        ("a", "a"), ("b", "b"), ("i", "序"), ("s", "文"),
        ("lst", "列表"), ("arr", "数组"), ("v", "v"), ("k", "k"),
        ("d", "d"), ("nm", "nm"), ("p", "p"), ("f", "f"),
        ("src", "源"), ("dst", "目标"), ("url", "链接"), ("msg", "消息"),
    ]
    _VAR_PAIRS_BASIC = [("x", "甲"), ("val", "值"), ("result", "结果"), ("data", "资料"), ("item", "项"), ("count", "计数"), ("tmp", "临时")]

    # ── LLVM 异常处理模板 ──
    exc_categories = [
        ("ValueError", "数值错误", "invalid value"),
        ("TypeError", "类型错误", "type mismatch"),
        ("KeyError", "键错误", "key not found"),
        ("IndexError", "索引错误", "out of range"),
        ("FileNotFoundError", "文件未找到", "file not found"),
        ("PermissionError", "权限错误", "permission denied"),
        ("ZeroDivisionError", "除以零", "divide by zero"),
        ("ConnectionError", "连接错误", "connection failed"),
        ("TimeoutError", "超时错误", "timeout"),
        ("AttributeError", "属性错误", "no attribute"),
        ("RuntimeError", "运行时错误", "runtime error"),
        ("MemoryError", "内存错误", "out of memory"),
        ("StopIteration", "迭代停止", "iteration done"),
        ("IOError", "IO错误", "I/O error"),
        ("ArithmeticError", "算术错误", "arithmetic error"),
    ]

    # 1. try/except 基本模式：更多变量组合
    for py_exc, duan_exc, _ in exc_categories:
        for pv, dv in _VAR_PAIRS_BASIC:
            py = f"try:\n    {pv} = risky_call()\nexcept {py_exc}:\n    {pv} = default()"
            duan = f"尝试：\n    设 {dv} 为 危险调用()\n捕获 {duan_exc}：\n    设 {dv} 为 默认()"
            generated.append(("LLVM异常", py, duan))

    # 2. try/except 带 else 模式
    for py_exc, duan_exc, msg in exc_categories[:12]:
        for pv, dv in [("x", "甲"), ("val", "值"), ("result", "结果")]:
            py = f"try:\n    {pv} = compute()\nexcept {py_exc}:\n    print('{msg}')\nelse:\n    print('success')"
            duan = f"尝试：\n    设 {dv} 为 计算()\n捕获 {duan_exc}：\n    打印(\"{msg}\")\n否则：\n    打印(\"成功\")"
            generated.append(("LLVM异常", py, duan))

    # 3. try/except/finally 模式
    for py_exc, duan_exc, msg in exc_categories[:12]:
        for suffix in ["cleanup()", "log_error()", "close_all()", "release()", "reset()", "flush()"]:
            py = f"try:\n    process()\nexcept {py_exc}:\n    print('{msg}')\nfinally:\n    {suffix}"
            duan = f"尝试：\n    处理()\n捕获 {duan_exc}：\n    打印(\"{msg}\")\n最终：\n    {suffix}"
            generated.append(("LLVM异常", py, duan))

    # 4. raise 语句
    for py_exc, duan_exc, msg in exc_categories:
        py = f"raise {py_exc}('{msg}')"
        duan = f"抛出 {duan_exc}(\"{msg}\")"
        generated.append(("LLVM异常", py, duan))

    # 5. raise 无参数
    for py_exc, duan_exc, _ in exc_categories[:8]:
        py = f"try:\n    do_work()\nexcept {py_exc}:\n    raise"
        duan = f"尝试：\n    执行工作()\n捕获 {duan_exc}：\n    抛出"
        generated.append(("LLVM异常", py, duan))

    # 6. 多异常捕获
    for (py1, duan1, _), (py2, duan2, _) in zip(exc_categories[:10], exc_categories[3:13]):
        py = f"try:\n    process_data()\nexcept ({py1}, {py2}) as e:\n    log_error(e)"
        duan = f"尝试：\n    处理数据()\n捕获 {duan1}, {duan2} 为 e：\n    记录错误(e)"
        generated.append(("LLVM异常", py, duan))

    # 7. 嵌套 try/except
    for pv, dv in [("x", "甲"), ("val", "值"), ("result", "结果"), ("data", "资料"), ("tmp", "临时")]:
        for py_exc, duan_exc, _ in exc_categories[:6]:
            py = f"def safe_op():\n    try:\n        {pv} = compute()\n        return {pv}\n    except {py_exc}:\n        return None"
            duan = f"段落 安全操作：\n    尝试：\n        设 {dv} 为 计算()\n        返回 {dv}\n    捕获 {duan_exc}：\n        返回 空"
            generated.append(("LLVM异常", py, duan))

    # 8. 异常链
    for py_exc, duan_exc, _ in exc_categories[:8]:
        py = f"try:\n    do_work()\nexcept {py_exc} as e:\n    raise RuntimeError('failed') from e"
        duan = f"尝试：\n    执行工作()\n捕获 {duan_exc} 为 e：\n    抛出 运行时错误(\"失败\") 从 e"
        generated.append(("LLVM异常", py, duan))

    # 9. 函数内的 try/except
    for py_exc, duan_exc, msg in exc_categories[:8]:
        for func_name, duan_func in [("load_data", "加载数据"), ("process", "处理"), ("parse", "解析"), ("validate", "验证")]:
            py = f"def {func_name}():\n    try:\n        return do_work()\n    except {py_exc}:\n        print('{msg}')\n        return None"
            duan = f"段落 {duan_func}：\n    尝试：\n        返回 执行工作()\n    捕获 {duan_exc}：\n        打印(\"{msg}\")\n        返回 空"
            generated.append(("LLVM异常", py, duan))

    # 10. 空 except
    for pv, dv in [("x", "甲"), ("val", "值"), ("result", "结果")]:
        py = f"try:\n    {pv} = risky()\nexcept:\n    {pv} = 0"
        duan = f"尝试：\n    设 {dv} 为 危险()\n捕获 异常：\n    设 {dv} 为 0"
        generated.append(("LLVM异常", py, duan))

    # ── async/await 模板（大幅扩展）──
    async_funcs = [
        ("fetch_data", "获取数据", "http_get", "HTTP获取"),
        ("read_file", "读取文件", "open_async", "异步打开"),
        ("process_item", "处理项目", "compute", "计算"),
        ("send_request", "发送请求", "post", "POST"),
        ("query_db", "查询数据库", "db_query", "数据库查询"),
        ("download_file", "下载文件", "download", "下载"),
        ("upload_blob", "上传对象", "upload", "上传"),
        ("call_api", "调用API", "api_call", "API调用"),
        ("render_template", "渲染模板", "render", "渲染"),
        ("validate_token", "验证令牌", "auth_check", "身份验证"),
    ]

    for py_name, duan_name, py_call, duan_call in async_funcs:
        for pv, dv in [("data", "资料"), ("result", "结果"), ("val", "值"), ("resp", "响应"), ("out", "输出")]:
            # 基本 async 函数
            py = f"async def {py_name}(url):\n    return await {py_call}(url)"
            duan = f"异步段落 {duan_name} 接收 url：\n    返回 等待 {duan_call}(url)"
            generated.append(("异步", py, duan))

            # 带 try/except 的 async 函数
            py = f"async def safe_{py_name}(url):\n    try:\n        return await {py_call}(url)\n    except Exception as e:\n        print(f'Error: {{e}}')\n        return None"
            duan = f"异步段落 安全{duan_name} 接收 url：\n    尝试：\n        返回 等待 {duan_call}(url)\n    捕获 异常 为 e：\n        打印(f\"错误: {{e}}\")\n        返回 空"
            generated.append(("异步", py, duan))

            # async for 循环
            py = f"async def process_{py_name}s(urls):\n    results = []\n    for url in urls:\n        {pv} = await {py_call}(url)\n        results.append({pv})\n    return results"
            duan = f"异步段落 批量{duan_name} 接收 urls：\n    设 results 为 []\n    遍历 url 于 urls：\n        设 {dv} 为 等待 {duan_call}(url)\n        results.追加({dv})\n    返回 results"
            generated.append(("异步", py, duan))

    # 更多异步模式（扩展版）
    async_patterns = [
        ("async def gather_all(tasks):\n    return await asyncio.gather(*tasks)",
         "异步段落 收集全部 接收 tasks：\n    返回 等待 异步收集(*tasks)"),
        ("async def run_parallel(f1, f2):\n    r1, r2 = await asyncio.gather(f1(), f2())\n    return r1 + r2",
         "异步段落 并行运行 接收 函数1, 函数2：\n    设 r1, r2 为 等待 异步收集(函数1(), 函数2())\n    返回 r1 加上 r2"),
        ("async def delayed_exec(secs, func):\n    await asyncio.sleep(secs)\n    return await func()",
         "异步段落 延迟执行 接收 秒数, 函数：\n    等待 异步睡眠(秒数)\n    返回 等待 函数()"),
        ("async def retry_async(func, retries=3):\n    for i in range(retries):\n        try:\n            return await func()\n        except:\n            if i == retries - 1:\n                raise\n            await asyncio.sleep(1)",
         "异步段落 重试异步 接收 函数, 重试次数：\n    遍历 i 于 0至重试次数减去1：\n        尝试：\n            返回 等待 函数()\n        捕获 异常：\n            如果 i 等于 重试次数 减去 1：\n                抛出\n            等待 异步睡眠(1)"),
        ("async def stream_handler(stream):\n    async for chunk in stream:\n        process(chunk)",
         "异步段落 流处理器 接收 stream：\n    异步遍历 chunk 于 stream：\n        处理(chunk)"),
        ("async def wait_for_result(future, timeout):\n    try:\n        return await asyncio.wait_for(future, timeout=timeout)\n    except asyncio.TimeoutError:\n        return None",
         "异步段落 等待结果 接收 future, 超时：\n    尝试：\n        返回 等待 异步等待.等待(future, 超时=超时)\n    捕获 超时错误：\n        返回 空"),
        ("async def fetch_all(urls):\n    tasks = [fetch(url) for url in urls]\n    return await asyncio.gather(*tasks)",
         "异步段落 获取全部 接收 urls：\n    设 tasks 为 []\n    遍历 url 于 urls：\n        tasks.追加(获取(url))\n    返回 等待 异步收集(*tasks)"),
        ("async def produce_items(queue, items):\n    for item in items:\n        await queue.put(item)\n    await queue.put(None)",
         "异步段落 生产项目 接收 队列, items：\n    遍历 item 于 items：\n        等待 队列.放入(item)\n    等待 队列.放入(空)"),
        ("async def consume_items(queue):\n    while True:\n        item = await queue.get()\n        if item is None:\n            break\n        process(item)",
         "异步段落 消费项目 接收 队列：\n    当 真：\n        设 item 为 等待 队列.获取()\n        如果 item 等于 空：\n            跳出\n        处理(item)"),
        ("async def time_it(coro):\n    start = time.time()\n    result = await coro\n    elapsed = time.time() - start\n    print(f'Took {elapsed:.2f}s')\n    return result",
         "异步段落 计时 接收 协程：\n    设 start 为 当前时间()\n    设 result 为 等待 协程\n    设 elapsed 为 当前时间() 减去 start\n    打印(f\"耗时 {elapsed:.2f}秒\")\n    返回 result"),
    ]
    for py, duan in async_patterns:
        generated.append(("异步", py, duan))

    # ── 单元测试模板（大幅扩展）──
    test_funcs = [
        ("add", "加法", "add(2, 3)", "5", "加法(2, 3)", "5"),
        ("subtract", "减法", "subtract(10, 4)", "6", "减法(10, 4)", "6"),
        ("multiply", "乘法", "multiply(3, 4)", "12", "乘法(3, 4)", "12"),
        ("divide", "除法", "divide(10, 2)", "5", "除法(10, 2)", "5"),
        ("is_even", "是偶数", "is_even(4)", "True", "是偶数(4)", "真"),
        ("is_odd", "是奇数", "is_odd(5)", "True", "是奇数(5)", "真"),
        ("factorial", "阶乘", "factorial(5)", "120", "阶乘(5)", "120"),
        ("reverse", "反转", "reverse('abc')", "'cba'", "反转(\"abc\")", "\"cba\""),
        ("is_palindrome", "回文", "is_palindrome('racecar')", "True", "回文(\"racecar\")", "真"),
        ("max_value", "最大值", "max_value(3, 7, 2)", "7", "最大值(3, 7, 2)", "7"),
        ("min_value", "最小值", "min_value(3, 7, 2)", "2", "最小值(3, 7, 2)", "2"),
        ("abs_value", "绝对值", "abs_value(-5)", "5", "绝对值(-5)", "5"),
        ("square", "平方", "square(6)", "36", "平方(6)", "36"),
        ("cube", "立方", "cube(3)", "27", "立方(3)", "27"),
        ("str_len", "字符串长度", "str_len('hello')", "5", "字符串长度(\"hello\")", "5"),
        ("list_sum", "列表求和", "list_sum([1,2,3])", "6", "列表求和([1,2,3])", "6"),
    ]
    for py_name, duan_name, py_call, py_expected, duan_call, duan_expected in test_funcs:
        py = f"def test_{py_name}():\n    assert {py_call} == {py_expected}"
        duan = f"段落 测试{duan_name}：\n    断言 {duan_call} 等于 {duan_expected}"
        generated.append(("单元测试", py, duan))

        py2 = f"def test_{py_name}():\n    assert {py_call} == {py_expected}\n    assert {py_name}() is not None"
        duan2 = f"段落 测试{duan_name}：\n    断言 {duan_call} 等于 {duan_expected}\n    断言 {duan_name}() 不等于 空"
        generated.append(("单元测试", py2, duan2))

    # 更多测试模板（扩展版）
    test_templates = [
        "def test_empty_list():\n    assert len([]) == 0",
        "段落 测试空列表：\n    断言 len([]) 等于 0",
        "def test_list_append():\n    lst = [1]\n    lst.append(2)\n    assert len(lst) == 2",
        "段落 测试列表追加：\n    设 lst 为 [1]\n    lst.追加(2)\n    断言 len(lst) 等于 2",
        "def test_string_contains():\n    assert 'hello' in 'hello world'",
        "段落 测试字符串包含：\n    断言 字符串包含(\"hello world\", \"hello\")",
        "def test_dict_get():\n    d = {'a': 1}\n    assert d.get('a') == 1\n    assert d.get('b', 0) == 0",
        "段落 测试字典获取：\n    设 d 为 {\"a\": 1}\n    断言 d.get(\"a\") 等于 1\n    断言 d.get(\"b\", 0) 等于 0",
        "def test_range():\n    r = list(range(5))\n    assert len(r) == 5\n    assert r[0] == 0\n    assert r[-1] == 4",
        "段落 测试范围：\n    设 r 为 列表(0至4)\n    断言 len(r) 等于 5\n    断言 r[0] 等于 0\n    断言 r[4] 等于 4",
        "def test_type_check():\n    assert isinstance(42, int)\n    assert isinstance('hello', str)",
        "段落 测试类型检查：\n    断言 实例检查(42, 整数)\n    断言 实例检查(\"hello\", 字符串)",
        "def test_compare():\n    assert 5 > 3\n    assert 2 <= 2\n    assert 10 != 0",
        "段落 测试比较：\n    断言 5 大于 3\n    断言 2 小于等于 2\n    断言 10 不等于 0",
        "def test_boolean():\n    assert True and True\n    assert False or True\n    assert not False",
        "段落 测试布尔：\n    断言 真 且 真\n    断言 假 或 真\n    断言 非 假",
        "def test_none():\n    assert None is None\n    assert 'a' is not None",
        "段落 测试空：\n    断言 空 等于 空\n    断言 \"a\" 不等于 空",
        "def test_string_upper():\n    assert 'hello'.upper() == 'HELLO'",
        "段落 测试字符串大写：\n    断言 字符串大写(\"hello\") 等于 \"HELLO\"",
        "def test_string_lower():\n    assert 'HELLO'.lower() == 'hello'",
        "段落 测试字符串小写：\n    断言 字符串小写(\"HELLO\") 等于 \"hello\"",
        "def test_list_sort():\n    lst = [3, 1, 2]\n    lst.sort()\n    assert lst == [1, 2, 3]",
        "段落 测试列表排序：\n    设 lst 为 [3, 1, 2]\n    lst.排序()\n    断言 lst 等于 [1, 2, 3]",
        "def test_floats():\n    assert 3.14 > 3.0\n    assert 2.5 < 3.0\n    assert 1.0 == 1.0",
        "段落 测试浮点数：\n    断言 3.14 大于 3.0\n    断言 2.5 小于 3.0\n    断言 1.0 等于 1.0",
        "def test_set_ops():\n    s = {1, 2, 3}\n    assert 1 in s\n    assert 4 not in s",
        "段落 测试集合：\n    设 s 为 {1, 2, 3}\n    断言 1 于 s\n    断言 4 不 于 s",
    ]
    for i in range(0, len(test_templates), 2):
        py = test_templates[i]
        duan = test_templates[i+1]
        generated.append(("单元测试", py, duan))

    # ── 日志系统模板（大幅扩展）──
    log_levels = [
        ("debug", "调试", "Processing item", "正在处理项目"),
        ("info", "信息", "Operation completed", "操作完成"),
        ("warning", "警告", "Low disk space", "磁盘空间不足"),
        ("error", "错误", "Operation failed", "操作失败"),
        ("critical", "严重", "System shutdown", "系统关闭"),
    ]
    for py_level, duan_level, msg_en, msg_cn in log_levels:
        py = f"logger.{py_level}('{msg_en}')\nlogger.{py_level}(f'{{count}} items processed')"
        duan = f"logger.{duan_level}(\"{msg_cn}\")\nlogger.{duan_level}(f\"{{计数}} 项已处理\")"
        generated.append(("日志系统", py, duan))

        py = f"try:\n    do_work()\nexcept Exception as e:\n    logger.{py_level}(f'Error: {{e}}')"
        duan = f"尝试：\n    执行工作()\n捕获 异常 为 e：\n    logger.{duan_level}(f\"错误: {{e}}\")"
        generated.append(("日志系统", py, duan))

        py = f"logger.{py_level}('Starting {msg_en}')\nlogger.{py_level}('{msg_en} complete')"
        duan = f"logger.{duan_level}(\"开始{msg_cn}\")\nlogger.{duan_level}(\"{msg_cn}完成\")"
        generated.append(("日志系统", py, duan))

    # 日志配置模板（扩展版）
    log_configs = [
        ("logging.basicConfig(level=logging.INFO)",
         "日志.基础配置(级别=日志.信息)"),
        ("logging.basicConfig(level=logging.DEBUG, format='%(message)s')",
         "日志.基础配置(级别=日志.调试, 格式=\"%(message)s\")"),
        ("handler = logging.FileHandler('app.log')\nhandler.setLevel(logging.WARNING)",
         "设 handler 为 日志.文件处理器(\"app.log\")\nhandler.设置级别(日志.警告)"),
        ("handler = logging.StreamHandler()\nhandler.setLevel(logging.ERROR)",
         "设 handler 为 日志.流处理器()\nhandler.设置级别(日志.错误)"),
        ("logging.basicConfig(level=logging.DEBUG, filename='debug.log')",
         "日志.基础配置(级别=日志.调试, 文件名=\"debug.log\")"),
        ("formatter = logging.Formatter('%(levelname)s: %(message)s')\nhandler.setFormatter(formatter)",
         "设 formatter 为 日志.格式化器(\"%(levelname)s: %(message)s\")\nhandler.设置格式化器(formatter)"),
    ]
    for py, duan in log_configs:
        generated.append(("日志系统", py, duan))

    # ── 配置管理模板（大幅扩展）──
    config_items = [
        ("host", "localhost", "host", "localhost"),
        ("port", 8080, "port", 8080),
        ("debug", True, "debug", "真"),
        ("timeout", 30, "timeout", 30),
        ("max_retries", 3, "max_retries", 3),
        ("cache_size", 100, "cache_size", 100),
        ("verbosity", "INFO", "verbosity", "\"INFO\""),
        ("db_name", "mydb", "db_name", "\"mydb\""),
        ("max_connections", 50, "max_connections", 50),
        ("log_level", "DEBUG", "log_level", "\"DEBUG\""),
        ("secret_key", "abc123", "secret_key", "\"abc123\""),
        ("api_version", "v2", "api_version", "\"v2\""),
    ]
    for key, val, duan_key, duan_val in config_items:
        if isinstance(val, str):
            py = f"config = {{'{key}': '{val}'}}"
            duan = f"设 config 为 {{\"{duan_key}\": {duan_val}}}"
        elif isinstance(val, bool):
            py = f"config = {{'{key}': {str(val).lower()}}}"
            duan = f"设 config 为 {{\"{duan_key}\": {duan_val}}}"
        else:
            py = f"config = {{'{key}': {val}}}"
            duan = f"设 config 为 {{\"{duan_key}\": {duan_val}}}"
        generated.append(("配置管理", py, duan))

        py = f"value = config.get('{key}', default_value)"
        duan = f"设 value 为 config.get(\"{duan_key}\", 默认值)"
        generated.append(("配置管理", py, duan))

    # 多键配置
    multi_configs = [
        ("{'host': 'localhost', 'port': 8080, 'debug': True}",
         "{\"host\": \"localhost\", \"port\": 8080, \"debug\": 真}"),
        ("{'timeout': 30, 'retries': 3, 'cache': True}",
         "{\"timeout\": 30, \"retries\": 3, \"cache\": 真}"),
        ("{'name': 'app', 'version': '1.0', 'author': 'test'}",
         "{\"name\": \"app\", \"version\": \"1.0\", \"author\": \"test\"}"),
    ]
    for py, duan in multi_configs:
        py = f"config = {py}"
        duan = f"设 config 为 {duan}"
        generated.append(("配置管理", py, duan))

    # ── HTTP 服务端模板（大幅扩展）──
    http_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    for method in http_methods:
        py = f"def handle_{method.lower()}(request):\n    return {{'method': '{method}', 'status': 200, 'body': 'OK'}}"
        duan = f"段落 处理{method} 接收 request：\n    返回 {{\"method\": \"{method}\", \"status\": 200, \"body\": \"OK\"}}"
        generated.append(("HTTP服务", py, duan))

        py = f"if method == '{method}':\n    return handle_{method.lower()}(request)"
        duan = f"如果 method 等于 \"{method}\"：\n    返回 处理{method}(request)"
        generated.append(("HTTP服务", py, duan))

    http_statuses = [(200, "OK"), (201, "Created"), (204, "No Content"),
                     (301, "Moved"), (302, "Found"), (400, "Bad Request"),
                     (401, "Unauthorized"), (403, "Forbidden"), (404, "Not Found"),
                     (405, "Method Not Allowed"), (409, "Conflict"), (500, "Internal Server Error"),
                     (502, "Bad Gateway"), (503, "Service Unavailable")]
    for code, msg in http_statuses:
        py = f"def handle_{code}():\n    return {{'status': {code}, 'body': '{msg}'}}"
        duan = f"段落 处理{code}：\n    返回 {{\"status\": {code}, \"body\": \"{msg}\"}}"
        generated.append(("HTTP服务", py, duan))

    # 路由注册
    route_templates = [
        ("routes = {'/': home, '/about': about, '/contact': contact}",
         "设 routes 为 {\"/\": 首页, \"/about\": 关于, \"/contact\": 联系}"),
        ("routes = {'/api/users': users, '/api/posts': posts, '/api/comments': comments}",
         "设 routes 为 {\"/api/users\": 用户, \"/api/posts\": 文章, \"/api/comments\": 评论}"),
    ]
    for py, duan in route_templates:
        generated.append(("HTTP服务", py, duan))

    # ── duanpub 模板（大幅扩展）──
    pkg_names = ["json", "http", "test", "logging", "database", "auth", "templating", "routing",
                 "serialization", "caching", "validation", "encryption", "compression", "scheduling"]
    for pkg in pkg_names:
        py = f"from duanpub import install\ninstall('{pkg}')"
        duan = f"从 段言包 导入 安装\n安装(\"{pkg}\")"
        generated.append(("duanpub", py, duan))

        py = f"from duanpub import search\nresults = search('{pkg}')\nprint(len(results))"
        duan = f"从 段言包 导入 搜索\n设 results 为 搜索(\"{pkg}\")\n打印(len(results))"
        generated.append(("duanpub", py, duan))

        py = f"from duanpub import is_installed\nif not is_installed('{pkg}'):\n    install('{pkg}')"
        duan = f"从 段言包 导入 是否已安装\n如果 非 是否已安装(\"{pkg}\")：\n    安装(\"{pkg}\")"
        generated.append(("duanpub", py, duan))

    # duanpub 更多操作
    duanpub_ops = [
        ("from duanpub import list_installed\ninstalled = list_installed()",
         "从 段言包 导入 列出已安装\n设 installed 为 列出已安装()"),
        ("from duanpub import check_updates\nupdates = check_updates()",
         "从 段言包 导入 检查更新\n设 updates 为 检查更新()"),
        ("from duanpub import uninstall\nuninstall('old-package')",
         "从 段言包 导入 卸载\n卸载(\"old-package\")"),
        ("from duanpub import Package\npkg = Package('my-app')\npkg.save()",
         "从 段言包 导入 包\n设 pkg 为 新建 包(\"my-app\")\npkg.保存()"),
    ]
    for py, duan in duanpub_ops:
        generated.append(("duanpub", py, duan))

    # ── 增量编译模板（扩展版）──
    incr_flags = [
        ("--incremental", "--增量编译"),
        ("--incremental --watch", "--增量编译 --监视"),
        ("--incremental --verbose", "--增量编译 --详细"),
        ("--incremental --skip-tests", "--增量编译 --跳过测试"),
        ("--incremental --emit=llvm", "--增量编译 --输出=llvm"),
        ("--incremental --optimize O2", "--增量编译 --优化 O2"),
        ("--incremental --cache-dir .cache", "--增量编译 --缓存目录 .cache"),
        ("--incremental --emit=python", "--增量编译 --输出=python"),
        ("--incremental --no-optimize", "--增量编译 --无优化"),
        ("--incremental --target x86_64", "--增量编译 --目标 x86_64"),
    ]
    for flag, duan_flag in incr_flags:
        py = f"duan build {flag}"
        duan = f"段言 构建 {duan_flag}"
        generated.append(("增量编译", py, duan))

    # 增量编译函数
    incr_funcs = [
        ("def needs_rebuild(file):\n    import os\n    return not os.path.exists(file + '.cache')",
         "段落 需要重建 接收 file：\n    导入 文件系统\n    返回 非 文件系统.存在(file 加上 \".cache\")"),
        ("def compile_if_changed(src):\n    if needs_rebuild(src):\n        compile(src)\n    else:\n        print('up to date')",
         "段落 变更时编译 接收 src：\n    如果 需要重建(src)：\n        编译(src)\n    否则：\n        打印(\"已是最新\")"),
    ]
    for py, duan in incr_funcs:
        generated.append(("增量编译", py, duan))

    # ── 编译器缓存模板（扩展版）──
    cache_flags = [
        ("--no-cache", "--无缓存"),
        ("--cache-dir /tmp/cache", "--缓存目录 /tmp/cache"),
        ("--cache-dir .duan_cache", "--缓存目录 .duan_cache"),
        ("--cache-ttl 3600", "--缓存生存 3600"),
        ("--cache-ttl 86400", "--缓存生存 86400"),
        ("--cache-policy lazy", "--缓存策略 懒惰"),
        ("--cache-policy eager", "--缓存策略 积极"),
        ("--cache-compress", "--缓存压缩"),
        ("--cache-max-size 500MB", "--缓存最大大小 500MB"),
        ("--cache-max-size 1GB", "--缓存最大大小 1GB"),
        ("--cache-max-size 256MB", "--缓存最大大小 256MB"),
    ]
    for flag, duan_flag in cache_flags:
        py = f"duan build {flag}"
        duan = f"段言 构建 {duan_flag}"
        generated.append(("编译器缓存", py, duan))

    # 缓存管理命令
    cache_cmds = [
        ("duan clean-cache", "段言 清理缓存"),
        ("duan cache-stats", "段言 缓存统计"),
        ("duan build --cache-clear", "段言 构建 --缓存清除"),
        ("duan build --cache-info", "段言 构建 --缓存信息"),
        ("duan build --cache-reset", "段言 构建 --缓存重置"),
    ]
    for py, duan in cache_cmds:
        generated.append(("编译器缓存", py, duan))

    # ── 上下文管理器模板（大幅扩展）──
    ctx_templates = [
        ("with open('file.txt') as f:\n    content = f.read()",
         "使用 文件 为 打开(\"file.txt\")：\n    设 content 为 文件.读取()"),
        ("with open('log.txt', 'w') as f:\n    f.write('log entry')",
         "使用 文件 为 打开(\"log.txt\", \"w\")：\n    文件.写入(\"log entry\")"),
        ("with open('data.bin', 'rb') as f:\n    data = f.read()",
         "使用 文件 为 打开(\"data.bin\", \"rb\")：\n    设 data 为 文件.读取()"),
        ("with lock:\n    shared_var += 1",
         "使用 锁：\n    设 shared_var 为 shared_var 加上 1"),
        ("with db.connection() as conn:\n    conn.execute(sql)",
         "使用 conn 为 数据库.连接()：\n    conn.执行(sql)"),
        ("with open('a.txt') as f1, open('b.txt') as f2:\n    merge(f1, f2)",
         "使用 f1 为 打开(\"a.txt\"), f2 为 打开(\"b.txt\")：\n    合并(f1, f2)"),
        ("with timer:\n    result = expensive_operation()",
         "使用 计时器：\n    设 result 为 耗时操作()"),
        ("class MyContext:\n    def __enter__(self):\n        return self\n    def __exit__(self, *args):\n        self.close()",
         "类 我的上下文：\n    段落 __进入__：\n        返回 己\n    段落 __退出__ 接收 *args：\n        己.关闭()"),
        ("with open('input.txt') as f:\n    for line in f:\n        print(line.strip())",
         "使用 文件 为 打开(\"input.txt\")：\n    遍历 line 于 文件：\n        打印(字符串去空白(line))"),
        ("with open('out.txt', 'w') as f:\n    for i in range(10):\n        f.write(f'line {i}\\n')",
         "使用 文件 为 打开(\"out.txt\", \"w\")：\n    遍历 i 于 0至9：\n        文件.写入(f\"第{i}行\\n\")"),
    ]
    for py, duan in ctx_templates:
        generated.append(("上下文", py, duan))

    # 更多上下文管理器
    ctx_extra = [
        ("with tempfile.TemporaryDirectory() as tmp:\n    process_files(tmp)",
         "使用 tmp 为 临时文件.临时目录()：\n    处理文件(tmp)"),
        ("with redirect_stdout(f):\n    print('captured')",
         "使用 重定向标准输出(f)：\n    打印(\"已捕获\")"),
        ("with open('file', 'rb') as f:\n    chunk = f.read(4096)\n    while chunk:\n        handle(chunk)\n        chunk = f.read(4096)",
         "使用 文件 为 打开(\"file\", \"rb\")：\n    设 chunk 为 文件.读取(4096)\n    当 chunk：\n        处理(chunk)\n        设 chunk 为 文件.读取(4096)"),
    ]
    for py, duan in ctx_extra:
        generated.append(("上下文", py, duan))

    # ── 迭代器协议模板（大幅扩展）──
    iter_templates = [
        ("class Counter:\n    def __init__(self, n):\n        self.n = n\n        self.i = 0\n    def __iter__(self):\n        return self\n    def __next__(self):\n        if self.i >= self.n:\n            raise StopIteration()\n        val = self.i\n        self.i += 1\n        return val",
         "类 计数器：\n    属性 上限\n    属性 索引\n    构造 接收 n：\n        己.上限 为 n\n        己.索引 为 0\n    段落 __迭代__：\n        返回 己\n    段落 __下一项__：\n        如果 己.索引 大于等于 己.上限：\n            抛出 迭代停止()\n        设 val 为 己.索引\n        设 己.索引 为 己.索引 加上 1\n        返回 val"),
        ("for item in iterable:\n    print(item)",
         "遍历 item 于 iterable：\n    打印(item)"),
        ("for val in counter:\n    print(val * 2)",
         "遍历 val 于 counter：\n    打印(val 乘以 2)"),
        ("class Range:\n    def __init__(self, start, end):\n        self.i = start\n        self.end = end\n    def __iter__(self):\n        return self\n    def __next__(self):\n        if self.i >= self.end:\n            raise StopIteration()\n        val = self.i\n        self.i += 1\n        return val",
         "类 范围：\n    属性 当前值\n    属性 结束值\n    构造 接收 开始, 结束：\n        己.当前值 为 开始\n        己.结束值 为 结束\n    段落 __迭代__：\n        返回 己\n    段落 __下一项__：\n        如果 己.当前值 大于等于 己.结束值：\n            抛出 迭代停止()\n        设 val 为 己.当前值\n        设 己.当前值 为 己.当前值 加上 1\n        返回 val"),
        ("class EvenNumbers:\n    def __init__(self, n):\n        self.n = n\n        self.i = 0\n    def __iter__(self):\n        return self\n    def __next__(self):\n        if self.i >= self.n:\n            raise StopIteration()\n        val = self.i * 2\n        self.i += 1\n        return val",
         "类 偶数生成器：\n    属性 上限\n    属性 索引\n    构造 接收 n：\n        己.上限 为 n\n        己.索引 为 0\n    段落 __迭代__：\n        返回 己\n    段落 __下一项__：\n        如果 己.索引 大于等于 己.上限：\n            抛出 迭代停止()\n        设 val 为 己.索引 乘以 2\n        设 己.索引 为 己.索引 加上 1\n        返回 val"),
        ("for i, val in enumerate(items):\n    print(i, val)",
         "遍历 i, val 于 枚举(items)：\n    打印(i, val)"),
        ("for k, v in config.items():\n    print(k, v)",
         "遍历 k, v 于 config.项目()：\n    打印(k, v)"),
    ]
    for py, duan in iter_templates:
        generated.append(("迭代器", py, duan))

    # ── 模式匹配模板（大幅扩展）──
    match_templates = [
        ("match value:\n    case 0:\n        print('zero')\n    case 1:\n        print('one')\n    case _:\n        print('other')",
         "匹配 value：\n    当 0：\n        打印(\"零\")\n    当 1：\n        打印(\"一\")\n    当 _：\n        打印(\"其他\")"),
        ("match status:\n    case 200:\n        return 'ok'\n    case 404:\n        return 'not found'\n    case 500:\n        return 'error'",
         "匹配 status：\n    当 200：\n        返回 \"ok\"\n    当 404：\n        返回 \"未找到\"\n    当 500：\n        返回 \"错误\""),
        ("match color:\n    case 'red' | 'blue' | 'green':\n        print('primary')\n    case _:\n        print('other')",
         "匹配 color：\n    当 \"red\" | \"blue\" | \"green\"：\n        打印(\"原色\")\n    当 _：\n        打印(\"其他\")"),
        ("match point:\n    case (0, 0):\n        return 'origin'\n    case (x, 0):\n        return f'x={x}'\n    case (0, y):\n        return f'y={y}'",
         "匹配 point：\n    当 (0, 0)：\n        返回 \"原点\"\n    当 (x, 0)：\n        返回 f\"x={x}\"\n    当 (0, y)：\n        返回 f\"y={y}\""),
        ("match result:\n    case {'ok': val}:\n        return val\n    case {'error': msg}:\n        raise Exception(msg)",
         "匹配 result：\n    当 {\"ok\": val}：\n        返回 val\n    当 {\"error\": msg}：\n        抛出 异常(msg)"),
        ("match data:\n    case [a, b]:\n        return a + b\n    case [a]:\n        return a\n    case []:\n        return 0",
         "匹配 data：\n    当 [a, b]：\n        返回 a 加上 b\n    当 [a]：\n        返回 a\n    当 []：\n        返回 0"),
        ("match score:\n    case s if s >= 90:\n        return 'A'\n    case s if s >= 80:\n        return 'B'\n    case s if s >= 70:\n        return 'C'\n    case _:\n        return 'F'",
         "匹配 score：\n    当 s 若 s 大于等于 90：\n        返回 \"A\"\n    当 s 若 s 大于等于 80：\n        返回 \"B\"\n    当 s 若 s 大于等于 70：\n        返回 \"C\"\n    当 _：\n        返回 \"F\""),
        ("match response:\n    case 200, body:\n        return body\n    case 404, _:\n        return 'not found'\n    case code, _:\n        return f'error: {code}'",
         "匹配 response：\n    当 200, body：\n        返回 body\n    当 404, _：\n        返回 \"未找到\"\n    当 code, _：\n        返回 f\"错误: {code}\""),
        ("match shape:\n    case ('circle', r):\n        return 3.14 * r * r\n    case ('rect', w, h):\n        return w * h\n    case ('triangle', b, h):\n        return 0.5 * b * h",
         "匹配 shape：\n    当 (\"circle\", r)：\n        返回 3.14 乘以 r 乘以 r\n    当 (\"rect\", w, h)：\n        返回 w 乘以 h\n    当 (\"triangle\", b, h)：\n        返回 0.5 乘以 b 乘以 h"),
    ]
    for py, duan in match_templates:
        generated.append(("模式匹配", py, duan))

    # ── 复合操作补充（大幅扩展）──
    comp_templates = [
        ("def sum_list(nums):\n    total = 0\n    for n in nums:\n        total += n\n    return total",
         "段落 列表求和 接收 nums：\n    设 total 为 0\n    遍历 n 于 nums：\n        设 total 为 total 加上 n\n    返回 total"),
        ("def avg(nums):\n    total = 0\n    count = 0\n    for n in nums:\n        total += n\n        count += 1\n    return total / count if count > 0 else 0",
         "段落 平均值 接收 nums：\n    设 total 为 0\n    设 count 为 0\n    遍历 n 于 nums：\n        设 total 为 total 加上 n\n        设 count 为 count 加上 1\n    返回 total 除以 count 如果 count 大于 0 否则 0"),
        ("def filter_positive(nums):\n    result = []\n    for n in nums:\n        if n > 0:\n            result.append(n)\n    return result",
         "段落 筛选正数 接收 nums：\n    设 result 为 []\n    遍历 n 于 nums：\n        如果 n 大于 0：\n            result.追加(n)\n    返回 result"),
        ("def count_chars(s):\n    counts = {}\n    for c in s:\n        if c in counts:\n            counts[c] += 1\n        else:\n            counts[c] = 1\n    return counts",
         "段落 字符统计 接收 s：\n    设 counts 为 {}\n    遍历 c 于 s：\n        如果 c 于 counts：\n            counts[c] = counts[c] 加上 1\n        否则：\n            counts[c] = 1\n    返回 counts"),
        ("def dedup(items):\n    seen = []\n    result = []\n    for item in items:\n        if item not in seen:\n            seen.append(item)\n            result.append(item)\n    return result",
         "段落 去重 接收 items：\n    设 seen 为 []\n    设 result 为 []\n    遍历 item 于 items：\n        设 found 为 假\n        遍历 s 于 seen：\n            如果 s 等于 item：\n                设 found 为 真\n                跳出\n        如果 非 found：\n            seen.追加(item)\n            result.追加(item)\n    返回 result"),
        ("def zip_lists(a, b):\n    result = []\n    for i in range(min(len(a), len(b))):\n        result.append((a[i], b[i]))\n    return result",
         "段落 拉链 接收 a, b：\n    设 result 为 []\n    设 n 为 len(a) 如果 len(a) 小于 len(b) 否则 len(b)\n    遍历 i 于 0至n减去1：\n        result.追加((a[i], b[i]))\n    返回 result"),
        ("def power_set(items):\n    result = [[]]\n    for item in items:\n        for r in result[:]:\n            result.append(r + [item])\n    return result",
         "段落 幂集 接收 items：\n    设 result 为 [[]]\n    遍历 item 于 items：\n        设 new_subsets 为 []\n        遍历 r 于 result：\n            new_subsets.追加(r 加上 [item])\n        遍历 ns 于 new_subsets：\n            result.追加(ns)\n    返回 result"),
        ("def reverse_list(lst):\n    result = []\n    for i in range(len(lst)-1, -1, -1):\n        result.append(lst[i])\n    return result",
         "段落 反转列表 接收 lst：\n    设 result 为 []\n    设 i 为 len(lst) 减去 1\n    当 i 大于等于 0：\n        result.追加(lst[i])\n        设 i 为 i 减去 1\n    返回 result"),
        ("def merge_dicts(d1, d2):\n    result = {}\n    for k, v in d1.items():\n        result[k] = v\n    for k, v in d2.items():\n        result[k] = v\n    return result",
         "段落 合并字典 接收 d1, d2：\n    设 result 为 {}\n    遍历 k, v 于 d1.项目()：\n        result[k] = v\n    遍历 k, v 于 d2.项目()：\n        result[k] = v\n    返回 result"),
        ("def intersect(a, b):\n    result = []\n    for x in a:\n        if x in b:\n            result.append(x)\n    return result",
         "段落 交集 接收 a, b：\n    设 result 为 []\n    遍历 x 于 a：\n        如果 x 于 b：\n            result.追加(x)\n    返回 result"),
        ("def difference(a, b):\n    result = []\n    for x in a:\n        if x not in b:\n            result.append(x)\n    return result",
         "段落 差集 接收 a, b：\n    设 result 为 []\n    遍历 x 于 a：\n        如果 x 不 于 b：\n            result.追加(x)\n    返回 result"),
        ("def unique(items):\n    seen = set()\n    result = []\n    for item in items:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    return result",
         "段落 唯一 接收 items：\n    设 seen 为 {}\n    设 result 为 []\n    遍历 item 于 items：\n        如果 item 不 于 seen：\n            seen[item] = 真\n            result.追加(item)\n    返回 result"),
    ]
    for py, duan in comp_templates:
        generated.append(("复合", py, duan))

    # ══════════════════════════════════════════════════════════════
    # 第二批次：更多模板模式（大幅提高总量至 2000+）
    # ══════════════════════════════════════════════════════════════

    # ── 更多 LLVM 异常（带不同变量名）──
    _VAR_PAIRS_EXTRA = [
        ("x", "甲"), ("val", "值"), ("result", "结果"), ("data", "资料"),
        ("item", "项"), ("key", "键"), ("count", "计数"), ("total", "总计"),
        ("flag", "标志"), ("name", "名"), ("tmp", "临时"), ("a", "a"),
        ("b", "b"), ("i", "序"), ("s", "文"), ("lst", "列表"),
        ("arr", "数组"), ("v", "v"), ("k", "k"), ("d", "d"),
        ("nm", "nm"), ("p", "p"), ("f", "f"), ("src", "源"),
        ("dst", "目标"), ("url", "链接"), ("msg", "消息"), ("res", "res"),
    ]

    # 更多 try/except 模式
    for py_exc, duan_exc, _ in exc_categories:
        for pv, dv in _VAR_PAIRS_EXTRA[:12]:
            py = f"def get_{pv}():\n    try:\n        return compute_{pv}()\n    except {py_exc}:\n        return None"
            duan = f"段落 获取{dv}：\n    尝试：\n        返回 计算{dv}()\n    捕获 {duan_exc}：\n        返回 空"
            generated.append(("LLVM异常", py, duan))

    # 带 finally 的更多模式
    for py_exc, duan_exc, msg in exc_categories:
        for action in ["cleanup()", "close()", "release()", "disconnect()", "free()", "reset()", "flush()", "stop()"]:
            py = f"try:\n    connect()\nexcept {py_exc}:\n    print('{msg}')\nfinally:\n    {action}"
            duan = f"尝试：\n    连接()\n捕获 {duan_exc}：\n    打印(\"{msg}\")\n最终：\n    {action}"
            generated.append(("LLVM异常", py, duan))

    # 更多 raise 变体
    for py_exc, duan_exc, msg in exc_categories:
        for prefix in ["encountered: ", "error: ", "failed: "]:
            py = f"raise {py_exc}('{prefix}{msg}')"
            duan = f"抛出 {duan_exc}(\"{prefix}{msg}\")"
            generated.append(("LLVM异常", py, duan))

    # ── 更多异步函数 ──
    more_async_funcs = [
        ("parse_async", "异步解析", "parse", "解析"),
        ("transform_data", "转换数据", "transform", "转换"),
        ("aggregate_results", "聚合结果", "aggregate", "聚合"),
        ("notify_users", "通知用户", "notify", "通知"),
        ("sync_records", "同步记录", "sync", "同步"),
        ("backup_data", "备份数据", "backup", "备份"),
        ("restore_snapshot", "恢复快照", "restore", "恢复"),
        ("export_report", "导出报告", "export", "导出"),
        ("import_data", "导入数据", "import_data", "导入"),
        ("validate_batch", "批量验证", "validate", "验证"),
    ]
    for py_name, duan_name, py_call, duan_call in more_async_funcs:
        for pv, dv in [("data", "资料"), ("result", "结果"), ("val", "值"), ("out", "输出")]:
            py = f"async def {py_name}(source):\n    return await {py_call}(source)"
            duan = f"异步段落 {duan_name} 接收 source：\n    返回 等待 {duan_call}(source)"
            generated.append(("异步", py, duan))
            py = f"async def safe_{py_name}(source):\n    try:\n        return await {py_call}(source)\n    except:\n        return None"
            duan = f"异步段落 安全{duan_name} 接收 source：\n    尝试：\n        返回 等待 {duan_call}(source)\n    捕获 异常：\n        返回 空"
            generated.append(("异步", py, duan))

    # 更多异步模式
    more_async_patterns = [
        ("async def sequence(coros):\n    results = []\n    for c in coros:\n        results.append(await c)\n    return results",
         "异步段落 顺序执行 接收 协程列表：\n    设 results 为 []\n    遍历 c 于 协程列表：\n        results.追加(等待 c)\n    返回 results"),
        ("async def first_completed(coros):\n    done, pending = await asyncio.wait(coros, return_when=FIRST_COMPLETED)\n    return done.pop().result()",
         "异步段落 首个完成 接收 协程列表：\n    设 done, pending 为 等待 异步等待(协程列表, 返回时=首个完成)\n    返回 done.弹出().结果()"),
        ("async def with_timeout(coro, timeout):\n    return await asyncio.wait_for(coro, timeout=timeout)",
         "异步段落 带超时 接收 协程, 超时：\n    返回 等待 异步等待.等待(协程, 超时=超时)"),
        ("async def create_tasks():\n    t1 = asyncio.create_task(fetch('a'))\n    t2 = asyncio.create_task(fetch('b'))\n    return await asyncio.gather(t1, t2)",
         "异步段落 创建任务：\n    设 t1 为 异步创建任务(获取(\"a\"))\n    设 t2 为 异步创建任务(获取(\"b\"))\n    返回 等待 异步收集(t1, t2)"),
        ("async def fan_out(items, func):\n    tasks = [func(item) for item in items]\n    return await asyncio.gather(*tasks)",
         "异步段落 扇出 接收 items, 函数：\n    设 tasks 为 []\n    遍历 item 于 items：\n        tasks.追加(函数(item))\n    返回 等待 异步收集(*tasks)"),
    ]
    for py, duan in more_async_patterns:
        generated.append(("异步", py, duan))

    # ── 更多单元测试 ──
    more_test_funcs = [
        ("concat", "拼接", "concat('a', 'b')", "'ab'", "拼接(\"a\", \"b\")", "\"ab\""),
        ("contains", "包含", "contains('hello', 'ell')", "True", "包含(\"hello\", \"ell\")", "真"),
        ("starts_with", "开头", "starts_with('hello', 'he')", "True", "开头(\"hello\", \"he\")", "真"),
        ("ends_with", "结尾", "ends_with('hello', 'lo')", "True", "结尾(\"hello\", \"lo\")", "真"),
        ("index_of", "索引", "index_of('hello', 'l')", "2", "索引(\"hello\", \"l\")", "2"),
        ("replace", "替换", "replace('hello', 'l', 'x')", "'hexxo'", "替换(\"hello\", \"l\", \"x\")", "\"hexxo\""),
        ("trim", "去空白", "trim('  hi  ')", "'hi'", "去空白(\"  hi  \")", "\"hi\""),
        ("count_occurrences", "计数", "count_occurrences([1,2,2,3], 2)", "2", "计数出现([1,2,2,3], 2)", "2"),
        ("first_element", "首个", "first_element([10,20,30])", "10", "首个([10,20,30])", "10"),
        ("last_element", "末个", "last_element([10,20,30])", "30", "末个([10,20,30])", "30"),
    ]
    for py_name, duan_name, py_call, py_expected, duan_call, duan_expected in more_test_funcs:
        py = f"def test_{py_name}():\n    assert {py_call} == {py_expected}"
        duan = f"段落 测试{duan_name}：\n    断言 {duan_call} 等于 {duan_expected}"
        generated.append(("单元测试", py, duan))
        py = f"def test_{py_name}_twice():\n    assert {py_call} == {py_expected}\n    assert {py_name}() is not None"
        duan = f"段落 测试{duan_name}两次：\n    断言 {duan_call} 等于 {duan_expected}\n    断言 {duan_name}() 不等于 空"
        generated.append(("单元测试", py, duan))

    # 更多测试模板
    more_test_templates = [
        "def test_truthiness():\n    assert bool(1) == True\n    assert bool(0) == False\n    assert bool('') == False",
        "段落 测试真值：\n    断言 布尔(1) 等于 真\n    断言 布尔(0) 等于 假\n    断言 布尔(\"\") 等于 假",
        "def test_list_index():\n    lst = [10, 20, 30]\n    assert lst[0] == 10\n    assert lst[-1] == 30",
        "段落 测试列表索引：\n    设 lst 为 [10, 20, 30]\n    断言 lst[0] 等于 10\n    断言 lst[-1] 等于 30",
        "def test_slicing():\n    lst = [1, 2, 3, 4, 5]\n    assert lst[1:3] == [2, 3]\n    assert lst[:2] == [1, 2]\n    assert lst[3:] == [4, 5]",
        "段落 测试切片：\n    设 lst 为 [1, 2, 3, 4, 5]\n    断言 lst[1:3] 等于 [2, 3]\n    断言 lst[:2] 等于 [1, 2]\n    断言 lst[3:] 等于 [4, 5]",
        "def test_list_comprehension():\n    squares = [x*x for x in range(5)]\n    assert squares == [0, 1, 4, 9, 16]",
        "段落 测试列表推导：\n    设 squares 为 []\n    遍历 x 于 0至4：\n        squares.追加(x 乘以 x)\n    断言 squares 等于 [0, 1, 4, 9, 16]",
        "def test_any_all():\n    assert any([False, True, False])\n    assert all([True, True, True])\n    assert not all([True, False])",
        "段落 测试任意全部：\n    断言 任意([假, 真, 假])\n    断言 全部([真, 真, 真])\n    断言 非 全部([真, 假])",
        "def test_sum_product():\n    assert sum([1, 2, 3, 4]) == 10\n    assert sum([]) == 0",
        "段落 测试求和：\n    断言 求和([1, 2, 3, 4]) 等于 10\n    断言 求和([]) 等于 0",
    ]
    for i in range(0, len(more_test_templates), 2):
        py = more_test_templates[i]
        duan = more_test_templates[i+1]
        generated.append(("单元测试", py, duan))

    # ── 更多日志系统 ──
    more_log_msgs = [
        ("debug", "调试", "Initializing module", "初始化模块"),
        ("info", "信息", "Server started on port", "服务器启动于端口"),
        ("warning", "警告", "Memory usage high", "内存使用率高"),
        ("error", "错误", "Connection timeout", "连接超时"),
        ("critical", "严重", "Unrecoverable error", "不可恢复错误"),
    ]
    for py_level, duan_level, msg_en, msg_cn in more_log_msgs:
        py = f"logger.{py_level}('{msg_en}: {msg_en.lower()}')\nlogger.{py_level}(f'Current status: {{status}}')"
        duan = f"logger.{duan_level}(\"{msg_cn}: {msg_cn}\")\nlogger.{duan_level}(f\"当前状态: {{status}}\")"
        generated.append(("日志系统", py, duan))

    # 日志配置
    for level in ["INFO", "DEBUG", "WARNING", "ERROR"]:
        py = f"logging.basicConfig(level=logging.{level})"
        duan = f"日志.基础配置(级别=日志.{ {'INFO':'信息','DEBUG':'调试','WARNING':'警告','ERROR':'错误'} [level]})"
        generated.append(("日志系统", py, duan))

    # ── 更多配置管理 ──
    more_configs = [
        ("{'theme': 'dark', 'language': 'zh', 'font_size': 14}",
         "{\"theme\": \"dark\", \"language\": \"zh\", \"font_size\": 14}"),
        ("{'enabled': True, 'auto_save': False, 'interval': 60}",
         "{\"enabled\": 真, \"auto_save\": 假, \"interval\": 60}"),
        ("{'url': 'http://localhost:8080', 'method': 'POST', 'headers': {}}",
         "{\"url\": \"http://localhost:8080\", \"method\": \"POST\", \"headers\": {}}"),
        ("{'username': 'admin', 'password': '***', 'host': 'db.example.com'}",
         "{\"username\": \"admin\", \"password\": \"***\", \"host\": \"db.example.com\"}"),
    ]
    for py, duan in more_configs:
        py = f"config = {py}"
        duan = f"设 config 为 {duan}"
        generated.append(("配置管理", py, duan))

    # ── 更多 HTTP 服务 ──
    more_http = [
        ("def handle_request(method, path):\n    if method == 'GET':\n        return get_handler(path)\n    elif method == 'POST':\n        return post_handler(path)\n    else:\n        return error(405)",
         "段落 处理请求 接收 方法, 路径：\n    如果 方法 等于 \"GET\"：\n        返回 获取处理器(路径)\n    否则如果 方法 等于 \"POST\"：\n        返回 提交处理器(路径)\n    否则：\n        返回 错误(405)"),
        ("def read_body(request):\n    length = int(request.headers.get('Content-Length', 0))\n    return request.rfile.read(length)",
         "段落 读取请求体 接收 request：\n    设 length 为 整数(request.headers.get(\"Content-Length\", 0))\n    返回 request.rfile.读取(length)"),
        ("def set_cookie(response, name, value):\n    response.headers['Set-Cookie'] = f'{name}={value}; Path=/'",
         "段落 设置Cookie 接收 response, 名称, 值：\n    response.headers[\"Set-Cookie\"] = f\"{名称}={值}; Path=/\""),
    ]
    for py, duan in more_http:
        generated.append(("HTTP服务", py, duan))

    # ── 更多 duanpub ──
    more_duanpub = [
        ("from duanpub import download_package\ndownload_package('myapp', version='2.0.0')",
         "从 段言包 导入 下载包\n下载包(\"myapp\", 版本=\"2.0.0\")"),
        ("from duanpub import publish_package\npublish_package('./dist', repository='main')",
         "从 段言包 导入 发布包\n发布包(\"./dist\", 仓库=\"main\")"),
        ("from duanpub import verify_package\nverify_package('myapp', checksum='abc123')",
         "从 段言包 导入 验证包\n验证包(\"myapp\", 校验和=\"abc123\")"),
        ("from duanpub import list_packages\npackages = list_packages(category='web')",
         "从 段言包 导入 列出包\n设 packages 为 列出包(类别=\"web\")"),
    ]
    for py, duan in more_duanpub:
        generated.append(("duanpub", py, duan))

    # ── 更多上下文管理器 ──
    more_ctx = [
        ("with open('log.txt', 'r') as f:\n    lines = f.readlines()\n    print(f'Read {len(lines)} lines')",
         "使用 文件 为 打开(\"log.txt\", \"r\")：\n    设 lines 为 文件.读取行()\n    打印(f\"读取了 {len(lines)} 行\")"),
        ("with open('out.bin', 'wb') as f:\n    f.write(data)\n    f.flush()",
         "使用 文件 为 打开(\"out.bin\", \"wb\")：\n    文件.写入(data)\n    文件.刷新()"),
        ("with manager as m:\n    m.setup()\n    m.run()\n    m.teardown()",
         "使用 m 为 管理器：\n    m.设置()\n    m.运行()\n    m.拆除()"),
        ("with open('src.txt', 'r') as src, open('dst.txt', 'w') as dst:\n    dst.write(src.read())",
         "使用 src 为 打开(\"src.txt\", \"r\"), dst 为 打开(\"dst.txt\", \"w\")：\n    dst.写入(src.读取())"),
    ]
    for py, duan in more_ctx:
        generated.append(("上下文", py, duan))

    # ── 更多迭代器 ──
    more_iter = [
        ("class Fibonacci:\n    def __init__(self, n):\n        self.n = n\n        self.a, self.b = 0, 1\n        self.i = 0\n    def __iter__(self):\n        return self\n    def __next__(self):\n        if self.i >= self.n:\n            raise StopIteration()\n        val = self.a\n        self.a, self.b = self.b, self.a + self.b\n        self.i += 1\n        return val",
         "类 斐波那契：\n    属性 上限\n    属性 前项\n    属性 后项\n    属性 索引\n    构造 接收 n：\n        己.上限 为 n\n        己.前项 为 0\n        己.后项 为 1\n        己.索引 为 0\n    段落 __迭代__：\n        返回 己\n    段落 __下一项__：\n        如果 己.索引 大于等于 己.上限：\n            抛出 迭代停止()\n        设 val 为 己.前项\n        设 己.前项, 己.后项 为 己.后项, 己.前项 加上 己.后项\n        设 己.索引 为 己.索引 加上 1\n        返回 val"),
        ("for val in fib:\n    if val > 100:\n        break\n    print(val)",
         "遍历 val 于 fib：\n    如果 val 大于 100：\n        跳出\n    打印(val)"),
        ("for i, char in enumerate('hello'):\n    print(f'{i}: {char}')",
         "遍历 i, char 于 枚举(\"hello\")：\n    打印(f\"{i}: {char}\")"),
    ]
    for py, duan in more_iter:
        generated.append(("迭代器", py, duan))

    # ── 更多模式匹配 ──
    more_match = [
        ("match value:\n    case 0:\n        return 'none'\n    case 1:\n        return 'one'\n    case 2:\n        return 'two'\n    case _:\n        return 'many'",
         "匹配 value：\n    当 0：\n        返回 \"无\"\n    当 1：\n        返回 \"一\"\n    当 2：\n        返回 \"二\"\n    当 _：\n        返回 \"多\""),
        ("match x, y:\n    case 0, 0:\n        print('origin')\n    case 0, y:\n        print(f'y={y}')\n    case x, 0:\n        print(f'x={x}')\n    case x, y:\n        print(f'({x},{y})')",
         "匹配 x, y：\n    当 0, 0：\n        打印(\"原点\")\n    当 0, y：\n        打印(f\"y={y}\")\n    当 x, 0：\n        打印(f\"x={x}\")\n    当 x, y：\n        打印(f\"({x},{y})\")"),
        ("match items:\n    case [x, y, z]:\n        return x + y + z\n    case [x, y]:\n        return x * y\n    case [x]:\n        return x\n    case []:\n        return 0",
         "匹配 items：\n    当 [x, y, z]：\n        返回 x 加上 y 加上 z\n    当 [x, y]：\n        返回 x 乘以 y\n    当 [x]：\n        返回 x\n    当 []：\n        返回 0"),
    ]
    for py, duan in more_match:
        generated.append(("模式匹配", py, duan))

    # ── 更多复合操作 ──
    more_comp = [
        ("def max_in_list(lst):\n    max_val = lst[0]\n    for x in lst:\n        if x > max_val:\n            max_val = x\n    return max_val",
         "段落 列表最大值 接收 lst：\n    设 max_val 为 lst[0]\n    遍历 x 于 lst：\n        如果 x 大于 max_val：\n            设 max_val 为 x\n    返回 max_val"),
        ("def min_in_list(lst):\n    min_val = lst[0]\n    for x in lst:\n        if x < min_val:\n            min_val = x\n    return min_val",
         "段落 列表最小值 接收 lst：\n    设 min_val 为 lst[0]\n    遍历 x 于 lst：\n        如果 x 小于 min_val：\n            设 min_val 为 x\n    返回 min_val"),
        ("def index_of(lst, target):\n    for i, v in enumerate(lst):\n        if v == target:\n            return i\n    return -1",
         "段落 查找索引 接收 lst, 目标：\n    遍历 i, v 于 枚举(lst)：\n        如果 v 等于 目标：\n            返回 i\n    返回 -1"),
        ("def is_sorted(lst):\n    for i in range(len(lst) - 1):\n        if lst[i] > lst[i + 1]:\n            return False\n    return True",
         "段落 是否已排序 接收 lst：\n    设 n 为 len(lst) 减去 1\n    遍历 i 于 0至n减去1：\n        如果 lst[i] 大于 lst[i + 1]：\n            返回 假\n    返回 真"),
        ("def swap(lst, i, j):\n    tmp = lst[i]\n    lst[i] = lst[j]\n    lst[j] = tmp\n    return lst",
         "段落 交换 接收 lst, i, j：\n    设 tmp 为 lst[i]\n    lst[i] = lst[j]\n    lst[j] = tmp\n    返回 lst"),
        ("def rotate_left(lst, k):\n    k = k % len(lst)\n    return lst[k:] + lst[:k]",
         "段落 左旋 接收 lst, k：\n    设 k 为 k 取余 len(lst)\n    返回 lst[k:] 加上 lst[:k]"),
    ]
    for py, duan in more_comp:
        generated.append(("复合", py, duan))

    # ── 更多增量编译 ──
    more_incr = [
        ("duan build --incremental --emit=python --no-cache",
         "段言 构建 --增量编译 --输出=python --无缓存"),
        ("duan build --incremental --target wasm32",
         "段言 构建 --增量编译 --目标 wasm32"),
        ("duan build --incremental --emit=llvm --optimize O3",
         "段言 构建 --增量编译 --输出=llvm --优化 O3"),
    ]
    for py, duan in more_incr:
        generated.append(("增量编译", py, duan))

    # ── 更多编译器缓存 ──
    more_cache = [
        ("duan build --cache-dir custom_cache --cache-compress --cache-policy eager",
         "段言 构建 --缓存目录 custom_cache --缓存压缩 --缓存策略 积极"),
        ("duan build --cache-max-size 2GB --cache-ttl 7200",
         "段言 构建 --缓存最大大小 2GB --缓存生存 7200"),
    ]
    for py, duan in more_cache:
        generated.append(("编译器缓存", py, duan))

    # ══════════════════════════════════════════════════════════════
    # 第三批次：简单高产量模板
    # ══════════════════════════════════════════════════════════════

    # ── 简单变量赋值 + 打印 ──
    for pv, dv in _VAR_PAIRS_EXTRA[:20]:
        for val in [0, 1, 42, 100, -1, 3.14, "hello", True, False, None]:
            if isinstance(val, str):
                py = f"{pv} = '{val}'"
                duan = f"设 {dv} 为 \"{val}\""
            elif isinstance(val, bool):
                py = f"{pv} = {str(val).lower()}"
                duan = f"设 {dv} 为 {'真' if val else '假'}"
            elif val is None:
                py = f"{pv} = None"
                duan = f"设 {dv} 为 空"
            else:
                py = f"{pv} = {val}"
                duan = f"设 {dv} 为 {val}"
            generated.append(("复合", py, duan))

    # ── 简单函数 ──
    simple_funcs = [
        ("double", "加倍", "x * 2", "x 乘以 2"),
        ("triple", "三倍", "x * 3", "x 乘以 3"),
        ("half", "一半", "x / 2", "x 除以 2"),
        ("square", "平方", "x * x", "x 乘以 x"),
        ("negate", "取反", "-x", "负 x"),
        ("increment", "加一", "x + 1", "x 加上 1"),
        ("decrement", "减一", "x - 1", "x 减去 1"),
        ("is_zero", "是否为零", "x == 0", "x 等于 0"),
        ("is_positive", "是否为正", "x > 0", "x 大于 0"),
        ("is_negative", "是否为负", "x < 0", "x 小于 0"),
        ("to_string", "转字符串", "str(x)", "字符串(x)"),
        ("to_int", "转整数", "int(x)", "整数(x)"),
        ("to_float", "转浮点数", "float(x)", "浮点数(x)"),
        ("bool_not", "逻辑非", "not x", "非 x"),
    ]
    for py_name, duan_name, py_expr, duan_expr in simple_funcs:
        py = f"def {py_name}(x):\n    return {py_expr}"
        duan = f"段落 {duan_name} 接收 x：\n    返回 {duan_expr}"
        generated.append(("复合", py, duan))

    # ── 简单 if/else ──
    for pv, dv in [("x", "甲"), ("val", "值"), ("result", "结果"), ("data", "资料"), ("count", "计数"), ("flag", "标志")]:
        py = f"if {pv} > 0:\n    print('positive')\nelse:\n    print('non-positive')"
        duan = f"如果 {dv} 大于 0：\n    打印(\"正数\")\n否则：\n    打印(\"非正数\")"
        generated.append(("复合", py, duan))
        py = f"if {pv} == 0:\n    return 'zero'\nelif {pv} > 0:\n    return 'positive'\nelse:\n    return 'negative'"
        duan = f"如果 {dv} 等于 0：\n    返回 \"零\"\n否则如果 {dv} 大于 0：\n    返回 \"正数\"\n否则：\n    返回 \"负数\""
        generated.append(("复合", py, duan))

    # ── 简单 for 循环 ──
    for pv, dv in [("x", "甲"), ("val", "值"), ("item", "项"), ("n", "数"), ("i", "序")]:
        py = f"for {pv} in items:\n    print({pv})"
        duan = f"遍历 {dv} 于 items：\n    打印({dv})"
        generated.append(("复合", py, duan))
        py = f"for {pv} in range(10):\n    print({pv})"
        duan = f"遍历 {dv} 于 0至9：\n    打印({dv})"
        generated.append(("复合", py, duan))

    # ── 简单 while 循环 ──
    for pv, dv in [("x", "甲"), ("i", "序"), ("count", "计数"), ("n", "数")]:
        py = f"while {pv} > 0:\n    print({pv})\n    {pv} -= 1"
        duan = f"当 {dv} 大于 0：\n    打印({dv})\n    设 {dv} 为 {dv} 减去 1"
        generated.append(("复合", py, duan))

    # ── 简单列表操作 ──
    list_ops = [
        ("lst = [1, 2, 3]", "设 lst 为 [1, 2, 3]"),
        ("lst.append(4)", "lst.追加(4)"),
        ("x = lst.pop()", "设 x 为 lst.弹出()"),
        ("x = lst[0]", "设 x 为 lst[0]"),
        ("lst.sort()", "lst.排序()"),
        ("lst.reverse()", "lst.反转()"),
        ("lst.clear()", "lst.清空()"),
        ("x = len(lst)", "设 x 为 len(lst)"),
        ("x = lst.count(1)", "设 x 为 lst.计数(1)"),
        ("x = 1 in lst", "设 x 为 1 于 lst"),
    ]
    for py, duan in list_ops:
        generated.append(("复合", py, duan))

    # ── 简单字典操作 ──
    dict_ops = [
        ("d = {'a': 1, 'b': 2}", "设 d 为 {\"a\": 1, \"b\": 2}"),
        ("d['c'] = 3", "d[\"c\"] = 3"),
        ("x = d.get('a', 0)", "设 x 为 d.get(\"a\", 0)"),
        ("x = d.keys()", "设 x 为 d.键()"),
        ("x = d.values()", "设 x 为 d.值()"),
        ("x = d.items()", "设 x 为 d.项目()"),
        ("d.pop('a')", "d.弹出(\"a\")"),
        ("d.clear()", "d.清空()"),
        ("x = 'a' in d", "设 x 为 \"a\" 于 d"),
        ("x = len(d)", "设 x 为 len(d)"),
    ]
    for py, duan in dict_ops:
        generated.append(("复合", py, duan))

    # ── 简单字符串操作 ──
    str_ops = [
        ("s = 'hello, world'", "设 s 为 \"hello, world\""),
        ("s.upper()", "s.大写()"),
        ("s.lower()", "s.小写()"),
        ("s.strip()", "s.去空白()"),
        ("s.replace('o', 'x')", "s.替换(\"o\", \"x\")"),
        ("s.split(',')", "s.分割(\",\")"),
        ("s.startswith('h')", "s.开头(\"h\")"),
        ("s.endswith('d')", "s.结尾(\"d\")"),
        ("x = len(s)", "设 x 为 len(s)"),
        ("x = s.find('o')", "设 x 为 s.查找(\"o\")"),
    ]
    for py, duan in str_ops:
        generated.append(("复合", py, duan))

    # ── 更多 LLVM 异常（简单模式）──
    for py_exc, duan_exc, msg in exc_categories:
        for pv, dv in [("x", "甲"), ("val", "值"), ("result", "结果"), ("data", "资料"), ("item", "项"), ("count", "计数")]:
            py = f"def fetch_{pv}():\n    try:\n        return load_{pv}()\n    except {py_exc}:\n        return None\n    finally:\n        cleanup()"
            duan = f"段落 取{dv}：\n    尝试：\n        返回 加载{dv}()\n    捕获 {duan_exc}：\n        返回 空\n    最终：\n        清理()"
            generated.append(("LLVM异常", py, duan))

    # ── 更多异步（简单模式）──
    for py_name, duan_name, py_call, duan_call in async_funcs + more_async_funcs:
        py = f"async def run_{py_name}():\n    result = await {py_call}()\n    return result"
        duan = f"异步段落 运行{duan_name}：\n    设 result 为 等待 {duan_call}()\n    返回 result"
        generated.append(("异步", py, duan))
        py = f"async def try_{py_name}():\n    try:\n        return await {py_call}()\n    except:\n        return None"
        duan = f"异步段落 尝试{duan_name}：\n    尝试：\n        返回 等待 {duan_call}()\n    捕获 异常：\n        返回 空"
        generated.append(("异步", py, duan))

    # ── 更多单元测试（简单断言）──
    for pv, dv in [("x", "甲"), ("val", "值"), ("result", "结果"), ("data", "资料"), ("count", "计数"), ("flag", "标志")]:
        for op, duan_op, val in [("==", "等于", 0), ("!=", "不等于", 0), (">", "大于", 0), ("<", "小于", 100), (">=", "大于等于", 0), ("<=", "小于等于", 100)]:
            py = f"def test_{pv}_{op.replace('=', 'eq')}_{val}():\n    assert {pv} {op} {val}"
            duan = f"段落 测试{dv}{duan_op}{val}：\n    断言 {dv} {duan_op} {val}"
            generated.append(("单元测试", py, duan))

    # ── 更多日志（简单模式）──
    for py_level, duan_level, msg_en, msg_cn in log_levels + more_log_msgs:
        for module in ["app", "db", "api", "cache", "auth"]:
            py = f"logger.{py_level}(f'[{module}] {msg_en}')\nlogger.{py_level}(f'[{module}] Done')"
            duan = f"logger.{duan_level}(f\"[{module}] {msg_cn}\")\nlogger.{duan_level}(f\"[{module}] 完成\")"
            generated.append(("日志系统", py, duan))

    # ── 更多配置（简单模式）──
    for val in [42, 8080, 3.14, True, False, "hello", "localhost", 100, 0, -1]:
        for key in ["setting", "option", "param", "value", "config_item"]:
            if isinstance(val, str):
                py = f"config = {{'{key}': '{val}'}}"
                duan = f"设 config 为 {{\"{key}\": \"{val}\"}}"
            elif isinstance(val, bool):
                py = f"config = {{'{key}': {str(val).lower()}}}"
                duan = f"设 config 为 {{\"{key}\": {'真' if val else '假'}}}"
            else:
                py = f"config = {{'{key}': {val}}}"
                duan = f"设 config 为 {{\"{key}\": {val}}}"
            generated.append(("配置管理", py, duan))

    # ── 更多 HTTP（简单模式）──
    for path in ["/", "/api", "/health", "/status", "/about", "/contact", "/login", "/logout"]:
        py = f"if path == '{path}':\n    return handle_path(path)"
        duan = f"如果 path 等于 \"{path}\"：\n    返回 处理路径(path)"
        generated.append(("HTTP服务", py, duan))

    # ── 更多 duanpub（简单模式）──
    for pkg in pkg_names + ["utils", "core", "net", "io", "sys", "text", "math", "time"]:
        py = f"from duanpub import install, uninstall, is_installed\nif is_installed('{pkg}'):\n    print('{pkg} ready')"
        duan = f"从 段言包 导入 安装, 卸载, 是否已安装\n如果 是否已安装(\"{pkg}\")：\n    打印(\"{pkg} 就绪\")"
        generated.append(("duanpub", py, duan))

    # ── 更多上下文管理器（简单模式）──
    for resource in ["file", "stream", "buffer", "socket", "connection", "session", "transaction", "lock"]:
        py = f"with open('{resource}.txt') as f:\n    data = f.read()"
        duan = f"使用 文件 为 打开(\"{resource}.txt\")：\n    设 data 为 文件.读取()"
        generated.append(("上下文", py, duan))
        py = f"with open('{resource}.log', 'w') as f:\n    f.write('done')"
        duan = f"使用 文件 为 打开(\"{resource}.log\", \"w\")：\n    文件.写入(\"完成\")"
        generated.append(("上下文", py, duan))

    # ── 更多迭代器（简单模式）──
    for pv, dv in [("x", "甲"), ("val", "值"), ("item", "项"), ("n", "数"), ("i", "序")]:
        for container in ["items", "values", "results", "data", "lst", "arr"]:
            py = f"for {pv} in {container}:\n    print({pv})"
            duan = f"遍历 {dv} 于 {container}：\n    打印({dv})"
            generated.append(("迭代器", py, duan))

    # ── 更多模式匹配（简单模式）──
    for pv, dv in [("x", "甲"), ("val", "值"), ("status", "状态"), ("code", "码"), ("result", "结果")]:
        py = f"match {pv}:\n    case 0:\n        return 'zero'\n    case 1:\n        return 'one'\n    case _:\n        return 'other'"
        duan = f"匹配 {dv}：\n    当 0：\n        返回 \"零\"\n    当 1：\n        返回 \"一\"\n    当 _：\n        返回 \"其他\""
        generated.append(("模式匹配", py, duan))

    # ── 更多增量编译（简单模式）──
    for target in ["x86_64", "arm64", "wasm32", "riscv64", "nvptx64"]:
        for emit in ["llvm", "python", "c"]:
            py = f"duan build --incremental --target {target} --emit={emit}"
            duan = f"段言 构建 --增量编译 --目标 {target} --输出={emit}"
            generated.append(("增量编译", py, duan))

    # ── 更多编译器缓存（简单模式）──
    for size in ["128MB", "256MB", "512MB", "1GB", "2GB"]:
        for ttl in ["3600", "7200", "86400"]:
            py = f"duan build --cache-max-size {size} --cache-ttl {ttl}"
            duan = f"段言 构建 --缓存最大大小 {size} --缓存生存 {ttl}"
            generated.append(("编译器缓存", py, duan))

    return generated


# ═══════════════════════════════════════════════════════════════════
# 变体扩充
# ═══════════════════════════════════════════════════════════════════

_NAME_MAPS = [
    {
        "x": "甲", "y": "乙", "n": "数", "m": "量", "i": "序",
        "lst": "列表", "arr": "数组", "s": "文", "result": "结果",
        "count": "计数", "total": "总计", "flag": "标志", "score": "分数",
        "item": "项", "name": "名", "val": "值", "tmp": "临时",
        "found": "找到", "target": "目标", "key": "键", "data": "资料",
        "text": "文本", "path": "路径", "file": "文件", "size": "大小",
    },
    {
        "x": "a", "y": "b", "n": "num", "lst": "list_", "arr": "data",
        "result": "res", "count": "cnt", "total": "sum_", "item": "elem",
        "name": "nm", "val": "v", "tmp": "temp", "found": "hit",
        "key": "k", "data": "d", "text": "t", "path": "p", "file": "f",
    },
]


def _expand_variants(pairs):
    """对手工对照对做变体扩充"""
    expanded = list(pairs)

    for name_map in _NAME_MAPS:
        for cat, py, duan in pairs:
            if len(py) > 300:
                continue
            py_cn = py
            duan_cn = duan
            changed = False
            for en, cn in name_map.items():
                if re.search(r'\b' + re.escape(en) + r'\b', py_cn):
                    py_cn = re.sub(r'\b' + re.escape(en) + r'\b', cn, py_cn)
                    duan_cn = re.sub(r'\b' + re.escape(en) + r'\b', cn, duan_cn)
                    changed = True
            if changed:
                expanded.append((cat, py_cn, duan_cn))

    return expanded


def _load_existing_dataset():
    """加载现有 v9 数据集，用于去重"""
    existing = set()
    if os.path.exists(_V9_PATH):
        with open(_V9_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                # 用 (input, output) 对去重
                key = (item.get('input', '').strip(), item.get('output', '').strip())
                existing.add(key)
    return existing


def build_dataset(output_path=None):
    """构建 SFT 训练集 v10"""
    # 1. 加载现有数据集
    existing = _load_existing_dataset()
    print(f"现有数据集条目数: {len(existing)}")

    # 2. 手工对照对 + 变体扩充 + 程序化生成
    handcrafted_pairs = _expand_variants(_HANDCRAFTED)
    programmatic_pairs = _generate_programmatic()
    all_pairs = handcrafted_pairs + programmatic_pairs
    print(f"手工对照对 + 变体: {len(handcrafted_pairs)} 条")
    print(f"程序化生成条目: {len(programmatic_pairs)} 条")
    print(f"总候选条目: {len(all_pairs)} 条")

    # 3. 转换为 JSONL 格式并去重
    dataset = []
    seen = set(existing)
    duplicate_count = 0
    for cat, py_code, duan_code in all_pairs:
        key = (py_code.strip(), duan_code.strip())
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        instruction = random.choice(_INSTRUCTIONS)
        dataset.append({
            "instruction": instruction,
            "input": py_code,
            "output": duan_code,
            "category": cat,
        })

    print(f"去重后新条目数: {len(dataset)}")
    if duplicate_count:
        print(f"跳过重复条目: {duplicate_count}")

    # 4. 打乱顺序
    random.shuffle(dataset)

    # 5. 写入文件
    if output_path is None:
        output_path = _OUTPUT_PATH

    with open(output_path, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    return dataset


def print_stats(dataset):
    """打印数据集统计信息"""
    categories = Counter()
    for item in dataset:
        categories[item['category']] += 1

    print(f"\n{'='*50}")
    print(f"v10 数据集统计")
    print(f"{'='*50}")
    print(f"新条目数: {len(dataset)}")
    print(f"\n按类别分布:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat:12s}: {count:4d} 条")

    input_lens = [len(item['input']) for item in dataset]
    output_lens = [len(item['output']) for item in dataset]
    print(f"\n输入长度: 最短 {min(input_lens)} / 最长 {max(input_lens)} / 平均 {sum(input_lens)//len(input_lens)}")
    print(f"输出长度: 最短 {min(output_lens)} / 最长 {max(output_lens)} / 平均 {sum(output_lens)//len(output_lens)}")

    long_inputs = sum(1 for item in dataset if len(item['input']) > 200)
    long_outputs = sum(1 for item in dataset if len(item['output']) > 200)
    print(f"长输入 (>200字符): {long_inputs} 条")
    print(f"长输出 (>200字符): {long_outputs} 条")


if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    import argparse
    parser = argparse.ArgumentParser(description='段言 SFT 训练集构造器 v10')
    parser.add_argument('--output', '-o', default=None, help='输出 JSONL 文件路径')
    parser.add_argument('--stats', action='store_true', help='只显示统计信息')
    args = parser.parse_args()

    if args.stats:
        if os.path.exists(_OUTPUT_PATH):
            dataset = []
            with open(_OUTPUT_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        dataset.append(json.loads(line))
            print_stats(dataset)
        else:
            print(f"输出文件不存在: {_OUTPUT_PATH}")
        sys.exit(0)

    dataset = build_dataset(args.output)
    print_stats(dataset)

    output_path = args.output or _OUTPUT_PATH
    print(f"\n已写入: {output_path}")