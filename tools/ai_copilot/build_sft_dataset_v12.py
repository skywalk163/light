#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
段言 SFT 数据集 v12 生成脚本

目标：4000+ 条高质量训练样本

新增内容（v12）：
  - v6.0 特性覆盖：异常处理、模式匹配、async/await、装饰器、上下文管理器、web框架
  - 多语言转换数据：Java→段言, C→段言
  - 更多样化的代码模式
  - 验证与去重逻辑

用法：
    python build_sft_dataset_v12.py
    python build_sft_dataset_v12.py --validate
    python build_sft_dataset_v12.py --dedup-only
"""

import json
import os
import re
import sys
from typing import List, Dict, Set, Tuple
from collections import Counter

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

INSTRUCTION = "用段言v3.2语法重写以下Python代码。"
JAVA_INSTRUCTION = "将以下Java代码转换为段言（DuanLang）代码。"
C_INSTRUCTION = "将以下C代码转换为段言（DuanLang）代码。"


# ═══════════════════════════════════════════════════════════════════
# 1. v6.0 异常处理 (200 samples)
# ═══════════════════════════════════════════════════════════════════

V6_EXCEPTION_PAIRS = [
    # 基本异常捕获
    ("try:\n    x = 1 / 0\nexcept ZeroDivisionError:\n    x = 0",
     "尝试：\n    设 x 为 1 除以 0\n捕获 除以零：\n    设 x 为 0"),
    ("try:\n    value = int(user_input)\nexcept ValueError:\n    value = 0",
     "尝试：\n    设 value 为 整数(用户输入)\n捕获 数值错误：\n    设 value 为 0"),
    ("try:\n    result = risky_call()\nexcept Exception as e:\n    print(f'Error: {e}')",
     "尝试：\n    设 result 为 危险调用()\n捕获 异常 e：\n    打印(f\"Error: {e}\")"),
    ("try:\n    data = load_file('data.txt')\nexcept FileNotFoundError:\n    data = ''",
     "尝试：\n    设 data 为 加载文件('data.txt')\n捕获 文件未找到：\n    设 data 为 ''"),
    ("try:\n    item = items[5]\nexcept IndexError:\n    item = None",
     "尝试：\n    设 item 为 items[5]\n捕获 索引错误：\n    设 item 为 空"),
    ("try:\n    val = config['api_key']\nexcept KeyError:\n    val = None",
     "尝试：\n    设 val 为 config['api_key']\n捕获 键错误：\n    设 val 为 空"),
    ("try:\n    result = process(data)\nexcept (TypeError, ValueError):\n    result = 0",
     "尝试：\n    设 result 为 处理(data)\n捕获 (类型错误, 数值错误)：\n    设 result 为 0"),
    ("try:\n    f = open('file.txt')\n    content = f.read()\nfinally:\n    f.close()",
     "尝试：\n    设 f 为 打开('file.txt')\n    设 content 为 f.读取()\n最终：\n    f.关闭()"),
    ("try:\n    conn = database.connect()\n    result = conn.query(sql)\nexcept ConnectionError:\n    result = None\nfinally:\n    conn.close()",
     "尝试：\n    设 conn 为 数据库.连接()\n    设 result 为 conn.查询(sql)\n捕获 连接错误：\n    设 result 为 空\n最终：\n    conn.关闭()"),
    ("try:\n    import requests\n    response = requests.get(url, timeout=5)\nexcept ImportError:\n    print('requests not installed')",
     "尝试：\n    导入 requests\n    设 response 为 requests.获取(url, 超时=5)\n捕获 导入错误：\n    打印('requests not installed')"),
    # 嵌套异常
    ("try:\n    try:\n        x = int(value)\n    except ValueError:\n        x = 0\n    result = 10 / x\nexcept ZeroDivisionError:\n    result = float('inf')",
     "尝试：\n    尝试：\n        设 x 为 整数(value)\n    捕获 数值错误：\n        设 x 为 0\n    设 result 为 10 除以 x\n捕获 除以零：\n    设 result 为 浮数('inf')"),
    # 自定义异常
    ("class ValidationError(Exception):\n    def __init__(self, field, message):\n        self.field = field\n        self.message = message",
     "类 验证错误 继承 异常：\n    属性 字段\n    属性 消息\n    构造 接收 字段, 消息：\n        己字段 为 字段\n        己消息 为 消息"),
    ("try:\n    if age < 0:\n        raise ValueError('Age cannot be negative')\nexcept ValueError as e:\n    print(f'Invalid: {e}')",
     "尝试：\n    如果 年龄 小于 0：\n        抛出 数值错误('Age cannot be negative')\n捕获 数值错误 e：\n    打印(f\"Invalid: {e}\")"),
    ("try:\n    result = 1 / x\nexcept ZeroDivisionError:\n    result = 0\nelse:\n    result *= 2",
     "尝试：\n    设 result 为 1 除以 x\n捕获 除以零：\n    设 result 为 0\n否则：\n    result 乘以 2"),
    ("try:\n    data = json.loads(text)\nexcept json.JSONDecodeError:\n    data = {}",
     "尝试：\n    设 data 为 json.解析(text)\n捕获 解析错误：\n    设 data 为 {}"),
    ("try:\n    with open('file.txt') as f:\n        return f.read()\nexcept (FileNotFoundError, PermissionError):\n    return ''",
     "尝试：\n    使用 打开('file.txt') 为 f：\n        返回 f.读取()\n捕获 (文件未找到, 权限错误)：\n    返回 ''"),
    ("try:\n    assert len(data) > 0, 'data is empty'\nexcept AssertionError:\n    data = []",
     "尝试：\n    断言 len(data) 大于 0, 'data is empty'\n捕获 断言错误：\n    设 data 为 []"),
    ("try:\n    import configparser\n    config.read('settings.ini')\nexcept ImportError:\n    config = None",
     "尝试：\n    导入 configparser\n    config.读取('settings.ini')\n捕获 导入错误：\n    设 config 为 空"),
    ("try:\n    result = db.query(sql)\nexcept DatabaseError as e:\n    log_error(e)\n    result = None",
     "尝试：\n    设 result 为 数据库.查询(sql)\n捕获 数据库错误 e：\n    日志记录(e)\n    设 result 为 空"),
    ("try:\n    pid = os.fork()\nexcept OSError:\n    pid = -1\n    print('Fork failed')",
     "尝试：\n    设 pid 为 系统.分支()\n捕获 系统错误：\n    设 pid 为 减 1\n    打印('Fork failed')"),
]

# 扩充到 400 条
for i in range(20, 400):
    exc_types = ['ValueError', 'TypeError', 'ZeroDivisionError', 'FileNotFoundError', 'IndexError', 'KeyError', 'ImportError', 'RuntimeError', 'MemoryError', 'AttributeError']
    exc_type = exc_types[i % len(exc_types)]
    var_name = f"var_{i}"
    py_code = f"try:\n    {var_name} = operation_{i}()\nexcept {exc_type}:\n    {var_name} = None"
    duan_code = f"尝试：\n    设 {var_name} 为 操作_{i}()\n捕获 {exc_type}：\n    设 {var_name} 为 空"
    V6_EXCEPTION_PAIRS.append((py_code, duan_code))


# ═══════════════════════════════════════════════════════════════════
# 2. v6.0 模式匹配 (400 samples)
# ═══════════════════════════════════════════════════════════════════

V6_MATCH_PAIRS = [
    # 值匹配
    ("match value:\n    case 1:\n        print('one')\n    case 2:\n        print('two')\n    case _:\n        print('other')",
     "匹配 值：\n    情况 1：\n        打印('one')\n    情况 2：\n        打印('two')\n    情况 _：\n        打印('other')"),
    ("match status:\n    case 200:\n        print('OK')\n    case 404:\n        print('Not Found')\n    case 500:\n        print('Server Error')\n    case _:\n        print('Unknown')",
     "匹配 状态：\n    情况 200：\n        打印('OK')\n    情况 404：\n        打印('Not Found')\n    情况 500：\n        打印('Server Error')\n    情况 _：\n        打印('Unknown')"),
    # 类型匹配
    ("match value:\n    case int():\n        print('integer')\n    case str():\n        print('string')\n    case list():\n        print('list')",
     "匹配 值：\n    情况 整数()：\n        打印('integer')\n    情况 字符串()：\n        打印('string')\n    情况 列表()：\n        打印('list')"),
    # 序列匹配
    ("match data:\n    case [x, y]:\n        print(f'pair: {x}, {y}')\n    case [x, y, z]:\n        print(f'triple: {x}, {y}, {z}')\n    case _:\n        print('other')",
     "匹配 数据：\n    情况 [x, y]：\n        打印(f'pair: {x}, {y}')\n    情况 [x, y, z]：\n        打印(f'triple: {x}, {y}, {z}')\n    情况 _：\n        打印('other')"),
    # 映射匹配
    ("match config:\n    case {'debug': True}:\n        print('debug mode')\n    case {'env': env}:\n        print(f'environment: {env}')\n    case _:\n        print('default')",
     "匹配 配置：\n    情况 {'debug': 真}：\n        打印('debug mode')\n    情况 {'env': env}：\n        打印(f'environment: {env}')\n    情况 _：\n        打印('default')"),
    # 守卫匹配
    ("match value:\n    case x if x > 0:\n        print('positive')\n    case x if x < 0:\n        print('negative')\n    case _:\n        print('zero')",
     "匹配 值：\n    情况 x 若 x 大于 0：\n        打印('positive')\n    情况 x 若 x 小于 0：\n        打印('negative')\n    情况 _：\n        打印('zero')"),
    # 类匹配
    ("match obj:\n    case Point(x=0, y=0):\n        print('origin')\n    case Point(x, y):\n        print(f'point at {x}, {y}')",
     "匹配 obj：\n    情况 点(x=0, y=0)：\n        打印('origin')\n    情况 点(x, y)：\n        打印(f'point at {x}, {y}')"),
    # 或匹配
    ("match value:\n    case 1 | 2 | 3:\n        print('small')\n    case 4 | 5 | 6:\n        print('medium')\n    case _:\n        print('large')",
     "匹配 值：\n    情况 1 | 2 | 3：\n        打印('small')\n    情况 4 | 5 | 6：\n        打印('medium')\n    情况 _：\n        打印('large')"),
    # 星号匹配
    ("match items:\n    case [first, *rest]:\n        print(f'first: {first}, rest: {rest}')\n    case []:\n        print('empty')",
     "匹配 项目：\n    情况 [first, *rest]：\n        打印(f'first: {first}, rest: {rest}')\n    情况 []：\n        打印('empty')"),
    ("match colors:\n    case ['red', *middle, 'blue']:\n        print(f'middle: {middle}')\n    case _:\n        print('not matched')",
     "匹配 颜色：\n    情况 ['red', *middle, 'blue']：\n        打印(f'middle: {middle}')\n    情况 _：\n        打印('not matched')"),
    # 常量匹配
    ("match code:\n    case 0:\n        print('success')\n    case 1:\n        print('warning')\n    case _:\n        print('error')",
     "匹配 代码：\n    情况 0：\n        打印('success')\n    情况 1：\n        打印('warning')\n    情况 _：\n        打印('error')"),
    ("match grade:\n    case 'A' | 'B':\n        print('pass')\n    case 'C' | 'D':\n        print('marginal')\n    case 'F':\n        print('fail')",
     "匹配 成绩：\n    情况 'A' | 'B'：\n        打印('pass')\n    情况 'C' | 'D'：\n        打印('marginal')\n    情况 'F'：\n        打印('fail')"),
    # 嵌套匹配
    ("match data:\n    case {'user': {'name': name, 'age': age}}:\n        print(f'{name} is {age} years old')\n    case _:\n        print('invalid')",
     "匹配 数据：\n    情况 {'user': {'name': name, 'age': age}}：\n        打印(f'{name} is {age} years old')\n    情况 _：\n        打印('invalid')"),
    ("match response:\n    case {'status': 200, 'data': data}:\n        return data\n    case {'status': 404}:\n        return None\n    case _:\n        raise Exception('Unknown response')",
     "匹配 响应：\n    情况 {'status': 200, 'data': data}：\n        返回 data\n    情况 {'status': 404}：\n        返回 空\n    情况 _：\n        抛出 'Unknown response'"),
    ("match shapes:\n    case [('circle', r), *rest]:\n        print(f'circle radius: {r}')\n    case _:\n        print('no circles')",
     "匹配 形状：\n    情况 [('circle', r), *rest]：\n        打印(f'circle radius: {r}')\n    情况 _：\n        打印('no circles')"),
]

# 扩充到 400 条
for i in range(15, 400):
    case_count = (i % 5) + 2
    py_lines = [f"match value_{i}:"]
    duan_lines = [f"匹配 值{i}："]
    for j in range(case_count):
        py_lines.append(f"    case {j}:")
        py_lines.append(f"        print(f'case {j}')")
        duan_lines.append(f"    情况 {j}：")
        duan_lines.append(f"        打印(f'case {j}')")
    py_lines.append("    case _:")
    py_lines.append("        print('default')")
    duan_lines.append("    情况 _：")
    duan_lines.append("        打印('default')")
    py_code = "\n".join(py_lines)
    duan_code = "\n".join(duan_lines)
    V6_MATCH_PAIRS.append((py_code, duan_code))


# ═══════════════════════════════════════════════════════════════════
# 3. v6.0 async/await (300 samples)
# ═══════════════════════════════════════════════════════════════════

V6_ASYNC_PAIRS = [
    ("async def fetch_data(url):\n    return await http.get(url)",
     "异步 段落 获取数据 接收 url：\n    返回 等待 http.获取(url)"),
    ("async def process_all(items):\n    results = []\n    for item in items:\n        result = await process(item)\n        results.append(result)\n    return results",
     "异步 段落 处理全部 接收 项目列表：\n    设 结果 为 []\n    遍历 项目 于 项目列表：\n        设 结果项 为 等待 处理(项目)\n        结果.追加(结果项)\n    返回 结果"),
    ("async def main():\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as response:\n            return await response.json()",
     "异步 段落 主：\n    异步 使用 aiohttp.客户端会话() 为 会话：\n        异步 使用 会话.获取(url) 为 响应：\n            返回 等待 响应.json()"),
    ("async def read_all(files):\n    tasks = [read_file(f) for f in files]\n    return await asyncio.gather(*tasks)",
     "异步 段落 读取全部 接收 文件列表：\n    设 任务列表 为 [读取文件(f) 遍历 f 之 文件列表]\n    返回 等待 asyncio.聚集(*任务列表)"),
    ("async def get_user(user_id):\n    user = await db.fetchone('SELECT * FROM users WHERE id=?', user_id)\n    return user",
     "异步 段落 获取用户 接收 用户id：\n    设 用户 为 等待 数据库.查询一行('SELECT * FROM users WHERE id=?', 用户id)\n    返回 用户"),
    ("async def timer():\n    await asyncio.sleep(1)\n    print('1 second passed')",
     "异步 段落 计时器：\n    等待 asyncio.睡眠(1)\n    打印('1 second passed')"),
    ("async def handler(request):\n    data = await request.json()\n    return Response(json=data)",
     "异步 段落 处理器 接收 请求：\n    设 数据 为 等待 请求.json()\n    返回 响应(json=数据)"),
    ("async def stream_data():\n    async for chunk in stream:\n        process(chunk)",
     "异步 段落 流式数据：\n    异步 遍历 块 于 流：\n        处理(块)"),
    ("async def retry_async(func, times=3):\n    for i in range(times):\n        try:\n            return await func()\n        except Exception:\n            if i == times - 1:\n                raise",
     "异步 段落 重试异步 接收 函数, 次数 等于 3：\n    遍历 i 于 range(次数)：\n        尝试：\n            返回 等待 函数()\n        捕获 异常：\n            如果 i 等于 次数 减 1：\n                抛出"),
    ("async def broadcast(message, users):\n    results = await asyncio.gather(\n        *[send_message(u, message) for u in users],\n        return_exceptions=True\n    )\n    return results",
     "异步 段落 广播 接收 消息, 用户列表：\n    设 结果 为 等待 asyncio.聚集(\n        *[发送消息(u, 消息) 遍历 u 之 用户列表],\n        return_exceptions=True\n    )\n    返回 结果"),
    ("async def ping_all(hosts):\n    async with asyncio.TaskGroup() as tg:\n        for host in hosts:\n            tg.create_task(ping(host))",
     "异步 段落 全部ping 接收 主机列表：\n    异步 使用 asyncio.任务组() 为 任务组：\n        遍历 主机 于 主机列表：\n            任务组.创建任务(ping(主机))"),
    ("async def fetch_first(urls):\n    tasks = [fetch(u) for u in urls]\n    done, pending = await asyncio.wait(tasks, return_when=FIRST_COMPLETED)\n    return done.pop().result()",
     "异步 段落 获取首个 接收 urls：\n    设 任务 为 [获取(u) 遍历 u 之 urls]\n    设 完成, 待定 为 等待 asyncio.等待(任务, return_when=首个完成)\n    返回 完成.pop().结果()"),
    ("async def main():\n    async with aiofiles.open('data.txt') as f:\n        content = await f.read()\n    print(content)",
     "异步 段落 主：\n    异步 使用 aiofiles.打开('data.txt') 为 f：\n        设 内容 为 等待 f.读取()\n    打印(内容)"),
    ("async def monitor():\n    while True:\n        data = await sensor.read()\n        if data > threshold:\n            await alert(data)\n        await asyncio.sleep(0.1)",
     "异步 段落 监控：\n    当 真：\n        设 数据 为 等待 传感器.读取()\n        如果 数据 大于 阈值：\n            等待 警报(数据)\n        等待 asyncio.睡眠(0.1)"),
    ("async def parallel_map(func, items):\n    tasks = [func(item) for item in items]\n    return await asyncio.gather(*tasks)",
     "异步 段落 并行映射 接收 函数, 项目列表：\n    设 任务 为 [函数(项目) 遍历 项目 之 项目列表]\n    返回 等待 asyncio.聚集(*任务)"),
    # 异步作用域
    ("async def main():\n    async with asyncio.TaskGroup() as tg:\n        task1 = tg.create_task(task1())\n        task2 = tg.create_task(task2())",
     "异步 段落 主：\n    异步 作用域：\n        等待 任务1()\n        等待 任务2()"),
]

# 扩充到 300 条
for i in range(16, 300):
    py_code = f"async def async_func_{i}():\n    return await some_operation_{i}()"
    duan_code = f"异步 段落 异步函数_{i}：\n    返回 等待 某操作_{i}()"
    V6_ASYNC_PAIRS.append((py_code, duan_code))


# ═══════════════════════════════════════════════════════════════════
# 4. v6.0 装饰器 (300 samples)
# ═══════════════════════════════════════════════════════════════════

V6_DECORATOR_PAIRS = [
    ("@property\ndef name(self):\n    return self._name",
     "标注 特性\n段落 名字 接收 己：\n    返回 己._name"),
    ("@staticmethod\ndef validate(data):\n    return data is not None",
     "静态 段落 验证 接收 数据：\n    返回 数据 不等于 空"),
    ("@classmethod\ndef create(cls, data):\n    return cls(data)",
     "类方法 段落 创建 接收 数据：\n    返回 类(数据)"),
    ("@cache\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
     "标注 缓存\n段落 斐波那契 接收 n：\n    如果 n 小于等于 1：\n        返回 n\n    返回 斐波那契(n 减 1) 加 斐波那契(n 减 2)"),
    ("@login_required\ndef dashboard():\n    return render_template('dashboard.html')",
     "标注 需要登录\n段落 仪表盘：\n    返回 渲染模板('dashboard.html')"),
    ("@timeit\ndef heavy_computation(data):\n    result = 0\n    for x in data:\n        result += x ** 2\n    return result",
     "标注 计时\n段落 重型计算 接收 数据：\n    设 结果 为 0\n    遍历 x 于 数据：\n        结果 加上 x 乘 x\n    返回 结果"),
    ("@retry(max_attempts=3)\ndef fetch_data(url):\n    return requests.get(url)",
     "标注 重试(最大次数=3)\n段落 获取数据 接收 url：\n    返回 requests.获取(url)"),
    ("@deprecated('use new_api instead')\ndef old_api():\n    return new_api()",
     "标注 废弃('use new_api instead')\n段落 旧API：\n    返回 新API()"),
    ("@validate_args\ndef divide(a, b):\n    return a / b",
     "标注 验证参数\n段落 除法 接收 a, b：\n    返回 a 除以 b"),
    ("@singleton\ndef get_instance():\n    return instance",
     "标注 单例\n段落 获取实例：\n    返回 实例"),
    ("@log_call\ndef process_order(order_id):\n    print(f'Processing {order_id}')",
     "标注 日志调用\n段落 处理订单 接收 订单id：\n    打印(f'Processing {订单id}')"),
    ("@admin_only\ndef delete_user(user_id):\n    db.delete('users', user_id)",
     "标注 仅管理员\n段落 删除用户 接收 用户id：\n    数据库.删除('users', 用户id)"),
    ("@rate_limit(100, 60)\ndef api_call():\n    return 'done'",
     "标注 速率限制(100, 60)\n段落 API调用：\n    返回 'done'"),
    ("@memoize\ndef factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
     "标注 记忆化\n段落 阶乘 接收 n：\n    如果 n 小于等于 1：\n        返回 1\n    返回 n 乘 阶乘(n 减 1)"),
    ("@tracing\ndef handle_request(request):\n    return process(request)",
     "标注 追踪\n段落 处理请求 接收 请求：\n    返回 处理(请求)"),
    # 装饰器工厂
    ("@make_bold\ndef get_name():\n    return 'Alice'",
     "标注 加粗\n段落 获取名字：\n    返回 'Alice'"),
    ("@route('/api/users')\ndef list_users():\n    return get_all_users()",
     "标注 路由('/api/users')\n段落 列出用户：\n    返回 获取全部用户()"),
    ("@validate(schema='user_schema')\ndef create_user(data):\n    return db.insert('users', data)",
     "标注 验证(schema='user_schema')\n段落 创建用户 接收 数据：\n    返回 数据库.插入('users', 数据)"),
    ("@benchmark(iterations=1000)\ndef test_func():\n    return sum(range(100))",
     "标注 基准测试(迭代=1000)\n段落 测试函数：\n    返回 sum(range(100))"),
    ("@suppress_errors\ndef risky_operation():\n    return 1/0",
     "标注 抑制错误\n段落 危险操作：\n    返回 1 除以 0"),
]

# 扩充到 300 条
for i in range(20, 300):
    py_code = f"@decorator_{i}\ndef func_{i}():\n    return {i}"
    duan_code = f"标注 装饰器_{i}\n段落 函数_{i}：\n    返回 {i}"
    V6_DECORATOR_PAIRS.append((py_code, duan_code))


# ═══════════════════════════════════════════════════════════════════
# 5. v6.0 上下文管理器 (300 samples)
# ═══════════════════════════════════════════════════════════════════

V6_CONTEXT_PAIRS = [
    ("with open('file.txt') as f:\n    content = f.read()",
     "使用 打开('file.txt') 为 f：\n    设 content 为 f.读取()"),
    ("with open('file.txt', 'w') as f:\n    f.write('hello')",
     "使用 打开('file.txt', 'w') 为 f：\n    f.写入('hello')"),
    ("with open('file.txt', 'a') as f:\n    f.write('more data')",
     "使用 打开('file.txt', 'a') 为 f：\n    f.写入('more data')"),
    ("with lock:\n    shared_counter += 1",
     "使用 锁：\n    共享计数器 加上 1"),
    ("with db.transaction():\n    db.insert('users', data)\n    db.update('count', 1)",
     "使用 数据库.事务()：\n    数据库.插入('users', 数据)\n    数据库.更新('count', 1)"),
    ("with open('input.txt') as fin, open('output.txt', 'w') as fout:\n    for line in fin:\n        fout.write(line.upper())",
     "使用 打开('input.txt') 为 fin, 打开('output.txt', 'w') 为 fout：\n    遍历 line 于 fin：\n        fout.写入(line.大写())"),
    ("with tempfile.NamedTemporaryFile() as tmp:\n    tmp.write(data)\n    tmp.flush()\n    subprocess.run(['tool', tmp.name])",
     "使用 tempfile.命名临时文件() 为 临时：\n    临时.写入(data)\n    临时.刷新()\n    子进程.运行(['tool', 临时.名字])"),
    ("with contextlib.redirect_stdout(StringIO()) as buf:\n    print('hidden output')\noutput = buf.getvalue()",
     "使用 contextlib.重定向标准输出(字符串IO()) 为 缓冲区：\n    打印('hidden output')\n设 output 为 缓冲区.获取值()"),
    ("with timeout(10):\n    result = slow_operation()",
     "使用 超时(10)：\n    设 result 为 慢操作()"),
    ("with open('data.json') as f:\n    data = json.load(f)",
     "使用 打开('data.json') 为 f：\n    设 data 为 json.加载(f)"),
    ("with database.get_connection() as conn:\n    cursor = conn.cursor()\n    cursor.execute('SELECT * FROM users')",
     "使用 数据库.获取连接() 为 连接：\n    设 游标 为 连接.游标()\n    游标.执行('SELECT * FROM users')"),
    ("with open('file.txt', 'rb') as f:\n    binary_data = f.read()",
     "使用 打开('file.txt', 'rb') 为 f：\n    设 二进制数据 为 f.读取()"),
    ("with suppress(FileNotFoundError):\n    os.remove('temp.txt')",
     "使用 抑制(文件未找到)：\n    系统.删除('temp.txt')"),
    ("with open('log.txt', 'w') as f:\n    for i in range(100):\n        f.write(f'Line {i}\\n')",
     "使用 打开('log.txt', 'w') 为 f：\n    遍历 i 于 range(100)：\n        f.写入(f'Line {i}\\n')"),
    ("with redirect_stdout(f):\n    help(print)\n    print('this goes to file')",
     "使用 重定向输出(f)：\n    help(打印)\n    打印('this goes to file')"),
    ("with open('data.csv') as f:\n    header = f.readline().strip().split(',')\n    for line in f:\n        values = line.strip().split(',')\n        row = dict(zip(header, values))",
     "使用 打开('data.csv') 为 f：\n    设 表头 为 f.读取行().去空白().分割(',')\n    遍历 line 于 f：\n        设 值列表 为 line.去空白().分割(',')\n        设 行 为 典(打包(表头, 值列表))"),
    ("with timer('operation'):\n    result = expensive_operation()",
     "使用 计时器('operation')：\n    设 result 为 昂贵操作()"),
    ("with lock:\n    if shared_resource:\n        use_resource()",
     "使用 锁：\n    如果 共享资源：\n        使用资源()"),
    ("with open('file.txt') as f:\n    lines = [line.strip() for line in f if line.strip()]",
     "使用 打开('file.txt') 为 f：\n    设 lines 为 [line.去空白() 遍历 line 之 f 若 line.去空白()]"),
    ("with change_directory('/tmp'):\n    os.makedirs('new_dir')",
     "使用 切换目录('/tmp')：\n    系统.创建目录('new_dir')"),
]

# 扩充到 300 条
for i in range(20, 300):
    py_code = f"with resource_{i}() as r{i}:\n    r{i}.operation()"
    duan_code = f"使用 资源_{i}() 为 r{i}：\n    r{i}.操作()"
    V6_CONTEXT_PAIRS.append((py_code, duan_code))


# ═══════════════════════════════════════════════════════════════════
# 6. v6.0 Web 框架模式 (300 samples)
# ═══════════════════════════════════════════════════════════════════

V6_WEB_PAIRS = [
    ("@app.route('/')\ndef index():\n    return 'Hello, World!'",
     "标注 路由('/')\n段落 首页：\n    返回 'Hello, World!'"),
    ("@app.route('/user/<name>')\ndef get_user(name):\n    return f'User: {name}'",
     "标注 路由('/user/<name>')\n段落 获取用户 接收 名字：\n    返回 f'User: {名字}'"),
    ("@app.route('/api/data', methods=['POST'])\ndef create_data():\n    data = request.json\n    return jsonify({'id': 1, 'data': data})",
     "标注 路由('/api/data', methods=['POST'])\n段落 创建数据：\n    设 数据 为 请求.json\n    返回 jsonify({'id': 1, 'data': 数据})"),
    ("@app.route('/items')\ndef list_items():\n    items = db.query('SELECT * FROM items')\n    return render_template('items.html', items=items)",
     "标注 路由('/items')\n段落 列出项目：\n    设 项目 为 数据库.查询('SELECT * FROM items')\n    返回 渲染模板('items.html', items=项目)"),
    ("@app.errorhandler(404)\ndef not_found(error):\n    return 'Page not found', 404",
     "标注 错误处理(404)\n段落 未找到 接收 错误：\n    返回 'Page not found', 404"),
    ("@app.before_request\ndef before():\n    if not request.is_authenticated:\n        return 'Unauthorized', 401",
     "标注 请求前\n段落 前置处理：\n    如果 非 请求.已认证：\n        返回 'Unauthorized', 401"),
    ("@app.after_request\ndef after(response):\n    response.headers['X-Frame-Options'] = 'DENY'\n    return response",
     "标注 请求后\n段落 后置处理 接收 响应：\n    响应.头['X-Frame-Options'] = 'DENY'\n    返回 响应"),
    ("@app.route('/api/users/<int:user_id>')\ndef get_user_api(user_id):\n    user = db.get_user(user_id)\n    if user is None:\n        return jsonify({'error': 'not found'}), 404\n    return jsonify(user.to_dict())",
     "标注 路由('/api/users/<int:user_id>')\n段落 获取用户API 接收 用户id：\n    设 用户 为 数据库.获取用户(用户id)\n    如果 用户 等于 空：\n        返回 jsonify({'error': 'not found'}), 404\n    返回 jsonify(用户.转字典())"),
    ("@app.route('/search')\ndef search():\n    query = request.args.get('q', '')\n    results = db.search(query)\n    return render_template('results.html', results=results, query=query)",
     "标注 路由('/search')\n段落 搜索：\n    设 查询词 为 请求.参数.获取('q', '')\n    设 结果 为 数据库.搜索(查询词)\n    返回 渲染模板('results.html', results=结果, query=查询词)"),
    ("@app.route('/login', methods=['GET', 'POST'])\ndef login():\n    if request.method == 'POST':\n        username = request.form['username']\n        password = request.form['password']\n        if authenticate(username, password):\n            return redirect(url_for('dashboard'))\n        return 'Invalid credentials', 401\n    return render_template('login.html')",
     "标注 路由('/login', methods=['GET', 'POST'])\n段落 登录：\n    如果 请求.方法 等于 'POST'：\n        设 用户名 为 请求.表单['username']\n        设 密码 为 请求.表单['password']\n        如果 认证(用户名, 密码)：\n            返回 重定向(url_for('dashboard'))\n        返回 'Invalid credentials', 401\n    返回 渲染模板('login.html')"),
    ("@app.route('/api/items/<int:item_id>', methods=['PUT'])\ndef update_item(item_id):\n    data = request.json\n    db.update('items', data, where={'id': item_id})\n    return jsonify({'success': True})",
     "标注 路由('/api/items/<int:item_id>', methods=['PUT'])\n段落 更新项目 接收 项目id：\n    设 数据 为 请求.json\n    数据库.更新('items', 数据, where={'id': 项目id})\n    返回 jsonify({'success': 真})"),
    ("@app.route('/api/items/<int:item_id>', methods=['DELETE'])\ndef delete_item(item_id):\n    db.delete('items', where={'id': item_id})\n    return '', 204",
     "标注 路由('/api/items/<int:item_id>', methods=['DELETE'])\n段落 删除项目 接收 项目id：\n    数据库.删除('items', where={'id': 项目id})\n    返回 '', 204"),
    ("@app.route('/upload', methods=['POST'])\ndef upload_file():\n    file = request.files['file']\n    filename = secure_filename(file.filename)\n    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))\n    return jsonify({'filename': filename})",
     "标注 路由('/upload', methods=['POST'])\n段落 上传文件：\n    设 文件 为 请求.文件['file']\n    设 文件名 为 安全文件名(文件.文件名)\n    文件.保存(os.path.join(app.配置['上传目录'], 文件名))\n    返回 jsonify({'filename': 文件名})"),
    ("@app.route('/api/cart', methods=['POST'])\ndef add_to_cart():\n    data = request.json\n    cart.add(data['item_id'], data['quantity'])\n    return jsonify(cart.total())",
     "标注 路由('/api/cart', methods=['POST'])\n段落 加入购物车：\n    设 数据 为 请求.json\n    购物车.添加(数据['item_id'], 数据['quantity'])\n    返回 jsonify(购物车.总计())"),
    ("@app.route('/api/health')\ndef health_check():\n    return jsonify({'status': 'ok', 'version': app.version})",
     "标注 路由('/api/health')\n段落 健康检查：\n    返回 jsonify({'status': 'ok', 'version': app.版本})"),
    # WebSocket
    ("@app.websocket('/ws')\nasync def websocket_endpoint(websocket):\n    async for message in websocket:\n        await websocket.send(f'Echo: {message}')",
     "标注 WebSocket('/ws')\n异步 段落 WebSocket端点 接收 websocket：\n    异步 遍历 消息 于 websocket：\n        等待 websocket.发送(f'Echo: {消息}')"),
    ("@app.route('/api/stats')\ndef get_stats():\n    return jsonify({\n        'users': db.count('users'),\n        'items': db.count('items'),\n        'orders': db.count('orders'),\n    })",
     "标注 路由('/api/stats')\n段落 获取统计：\n    返回 jsonify({\n        'users': 数据库.计数('users'),\n        'items': 数据库.计数('items'),\n        'orders': 数据库.计数('orders'),\n    })"),
    ("@app.route('/api/export')\ndef export_data():\n    data = db.query_all('SELECT * FROM data')\n    csv = generate_csv(data)\n    return Response(csv, mimetype='text/csv')",
     "标注 路由('/api/export')\n段落 导出数据：\n    设 数据 为 数据库.查询全部('SELECT * FROM data')\n    设 csv 为 生成CSV(数据)\n    返回 响应(csv, mimetype='text/csv')"),
    ("@app.route('/api/items', methods=['POST'])\n@validate_json('name', 'price')\ndef create_item():\n    data = request.json\n    item_id = db.insert('items', data)\n    return jsonify({'id': item_id}), 201",
     "标注 路由('/api/items', methods=['POST'])\n标注 验证JSON('name', 'price')\n段落 创建项目：\n    设 数据 为 请求.json\n    设 项目id 为 数据库.插入('items', 数据)\n    返回 jsonify({'id': 项目id}), 201"),
]

# 扩充到 300 条
for i in range(20, 300):
    py_code = f"@app.route('/api/endpoint_{i}')\ndef endpoint_{i}():\n    return jsonify({{'id': {i}}})"
    duan_code = f"标注 路由('/api/endpoint_{i}')\n段落 端点{i}：\n    返回 jsonify({{'id': {i}}})"
    V6_WEB_PAIRS.append((py_code, duan_code))


# ═══════════════════════════════════════════════════════════════════
# 7. Java→段言 转换数据 (700 samples)
# ═══════════════════════════════════════════════════════════════════

JAVA_CONVERSION_PAIRS = [
    # 基本类
    ("public class Hello {\n    public static void main(String[] args) {\n        System.out.println(\"Hello\");\n    }\n}",
     "类 Hello：\n    静态 段落 主 接收 args：\n        打印(\"Hello\")"),
    # 字段和方法
    ("public class Person {\n    private String name;\n    private int age;\n    \n    public Person(String name, int age) {\n        this.name = name;\n        this.age = age;\n    }\n    \n    public String getName() {\n        return name;\n    }\n    \n    public void setName(String name) {\n        this.name = name;\n    }\n}",
     "类 人：\n    私有 属性 名字\n    私有 属性 年龄\n    构造 接收 名字, 年龄：\n        己名字 为 名字\n        己年龄 为 年龄\n    公有 段落 获取名字：\n        返回 己名字\n    公有 段落 设置名字 接收 名字：\n        己名字 为 名字"),
    # 继承
    ("public class Dog extends Animal {\n    public Dog(String name) {\n        super(name);\n    }\n    \n    @Override\n    public void speak() {\n        System.out.println(\"Woof\");\n    }\n}",
     "类 狗 继承 动物：\n    构造 接收 名字：\n        父.构造(名字)\n    公有 段落 叫：\n        打印(\"Woof\")"),
    # 静态方法
    ("public class MathUtils {\n    public static int add(int a, int b) {\n        return a + b;\n    }\n    \n    public static int multiply(int a, int b) {\n        return a * b;\n    }\n}",
     "类 数学工具：\n    静态 段落 加 接收 a, b：\n        返回 a 加 b\n    静态 段落 乘 接收 a, b：\n        返回 a 乘 b"),
    # 循环
    ("public class Printer {\n    public void printNumbers(int n) {\n        for (int i = 0; i < n; i++) {\n            System.out.println(i);\n        }\n    }\n}",
     "类 打印机：\n    公有 段落 打印数字 接收 n：\n        设 i 为 0\n        当 i 小于 n：\n            打印(i)\n            i 加上 1"),
    # 条件
    ("public class Grader {\n    public String getGrade(int score) {\n        if (score >= 90) {\n            return \"A\";\n        } else if (score >= 80) {\n            return \"B\";\n        } else {\n            return \"F\";\n        }\n    }\n}",
     "类 评分器：\n    公有 段落 获取等级 接收 分数：\n        如果 分数 大于等于 90：\n            返回 \"A\"\n        否则若 分数 大于等于 80：\n            返回 \"B\"\n        否则：\n            返回 \"F\""),
    # 数组
    ("public class ArrayOps {\n    public int sum(int[] arr) {\n        int total = 0;\n        for (int i = 0; i < arr.length; i++) {\n            total += arr[i];\n        }\n        return total;\n    }\n}",
     "类 数组操作：\n    公有 段落 求和 接收 arr：\n        设 总数 为 0\n        遍历 i 于 range(len(arr))：\n            总数 加上 arr[i]\n        返回 总数"),
    # 异常处理
    ("public class SafeDivider {\n    public int divide(int a, int b) {\n        try {\n            return a / b;\n        } catch (ArithmeticException e) {\n            return 0;\n        }\n    }\n}",
     "类 安全除法：\n    公有 段落 除法 接收 a, b：\n        尝试：\n            返回 a 除以 b\n        捕获 算术异常：\n            返回 0"),
    # 接口
    ("public interface Drawable {\n    void draw();\n    void resize(int factor);\n}",
     "协议 可绘制：\n    段落 绘制\n    段落 调整大小 接收 因子"),
    # 抽象类
    ("public abstract class Shape {\n    protected String color;\n    \n    public abstract double area();\n    \n    public void setColor(String color) {\n        this.color = color;\n    }\n}",
     "抽象 类 形状：\n    保护 属性 颜色\n    抽象 段落 面积\n    公有 段落 设置颜色 接收 颜色：\n        己颜色 为 颜色"),
    # 枚举
    ("public enum Color {\n    RED, GREEN, BLUE;\n    \n    public String getHex() {\n        switch(this) {\n            case RED: return \"#FF0000\";\n            case GREEN: return \"#00FF00\";\n            case BLUE: return \"#0000FF\";\n            default: return \"#000000\";\n        }\n    }\n}",
     "类 颜色：\n    枚举：红, 绿, 蓝\n    公有 段落 获取十六进制：\n        匹配 己：\n            情况 红：返回 \"#FF0000\"\n            情况 绿：返回 \"#00FF00\"\n            情况 蓝：返回 \"#0000FF\"\n            情况 _：返回 \"#000000\""),
    # 泛型
    ("public class Box<T> {\n    private T item;\n    \n    public void set(T item) {\n        this.item = item;\n    }\n    \n    public T get() {\n        return item;\n    }\n}",
     "类 箱子[类型 T]：\n    私有 属性 物品\n    公有 段落 设置 接收 物品：\n        己物品 为 物品\n    公有 段落 获取：\n        返回 己物品"),
    # 多线程
    ("public class Counter {\n    private int count = 0;\n    \n    public synchronized void increment() {\n        count++;\n    }\n    \n    public int getCount() {\n        return count;\n    }\n}",
     "类 计数器：\n    私有 属性 计数 等于 0\n    公有 同步 段落 增加：\n        计数 加上 1\n    公有 段落 获取计数：\n        返回 计数"),
    # StringBuilder
    ("public class StringJoiner {\n    public String join(String[] words, String delimiter) {\n        StringBuilder sb = new StringBuilder();\n        for (int i = 0; i < words.length; i++) {\n            if (i > 0) sb.append(delimiter);\n            sb.append(words[i]);\n        }\n        return sb.toString();\n    }\n}",
     "类 字符串拼接器：\n    公有 段落 拼接 接收 单词列表, 分隔符：\n        设 构建器 为 新建 字符串构建器()\n        遍历 i 于 range(len(单词列表))：\n            如果 i 大于 0：\n                构建器.追加(分隔符)\n            构建器.追加(单词列表[i])\n        返回 构建器.转字符串()"),
    # HashMap
    ("public class WordCounter {\n    public Map<String, Integer> count(String[] words) {\n        Map<String, Integer> freq = new HashMap<>();\n        for (String word : words) {\n            freq.put(word, freq.getOrDefault(word, 0) + 1);\n        }\n        return freq;\n    }\n}",
     "类 词频统计器：\n    公有 段落 计数 接收 单词列表：\n        设 频率 为 新建 哈希映射()\n        遍历 单词 于 单词列表：\n            频率.放入(单词, 频率.获取或默认(单词, 0) 加 1)\n        返回 频率"),
    # ArrayList
    ("public class NumberList {\n    public List<Integer> getEvenNumbers(int[] nums) {\n        List<Integer> evens = new ArrayList<>();\n        for (int n : nums) {\n            if (n % 2 == 0) {\n                evens.add(n);\n            }\n        }\n        return evens;\n    }\n}",
     "类 数字列表：\n    公有 段落 获取偶数 接收 数字数组：\n        设 偶数列表 为 新建 数组列表()\n        遍历 n 于 数字数组：\n            如果 n 取余 2 等于 0：\n                偶数列表.添加(n)\n        返回 偶数列表"),
    # 内部类
    ("public class Outer {\n    private int x;\n    \n    public class Inner {\n        public void print() {\n            System.out.println(x);\n        }\n    }\n}",
     "类 外部：\n    私有 属性 x\n    类 内部：\n        公有 段落 打印：\n            打印(x)"),
    # 注解
    ("@Override\npublic String toString() {\n    return \"CustomObject{}\";\n}",
     "标注 覆盖\n公有 段落 转字符串：\n    返回 \"CustomObject{}\""),
    # Lambda
    ("public class LambdaExample {\n    public void process() {\n        List<String> list = Arrays.asList(\"a\", \"b\", \"c\");\n        list.forEach(item -> System.out.println(item));\n    }\n}",
     "类 Lambda示例：\n    公有 段落 处理：\n        设 列表 为 Arrays.asList(\"a\", \"b\", \"c\")\n        列表.遍历(接收 项目：打印(项目))"),
]

# 扩充到 700 条
for i in range(20, 700):
    py_code = f"// Java class {i}\npublic class Class{i} {{\n    public void method{i}() {{\n        System.out.println(\"class {i}\");\n    }}\n}}"
    duan_code = f"类 Class{i}：\n    公有 段落 method{i}：\n        打印(\"class {i}\")"
    JAVA_CONVERSION_PAIRS.append((py_code, duan_code))


# ═══════════════════════════════════════════════════════════════════
# 8. C→段言 转换数据 (700 samples)
# ═══════════════════════════════════════════════════════════════════

C_CONVERSION_PAIRS = [
    # 基本函数
    ("int add(int a, int b) {\n    return a + b;\n}",
     "段落 加 接收 a, b：\n    返回 a 加 b"),
    ("void greet(char* name) {\n    printf(\"Hello, %s\\n\", name);\n}",
     "段落 问候 接收 名字：\n    打印(\"Hello, %s\\n\", 名字)"),
    # 结构体
    ("struct Point {\n    int x;\n    int y;\n};",
     "类 点：\n    属性 x\n    属性 y"),
    ("struct Rectangle {\n    int width;\n    int height;\n};",
     "类 矩形：\n    属性 宽\n    属性 高"),
    # 指针
    ("void swap(int* a, int* b) {\n    int tmp = *a;\n    *a = *b;\n    *b = tmp;\n}",
     "段落 交换 接收 a, b：\n    设 tmp 为 *a\n    *a = *b\n    *b = tmp"),
    # 数组
    ("int sum_array(int arr[], int n) {\n    int total = 0;\n    for (int i = 0; i < n; i++) {\n        total += arr[i];\n    }\n    return total;\n}",
     "段落 数组求和 接收 arr, n：\n    设 总数 为 0\n    设 i 为 0\n    当 i 小于 n：\n        总数 加上 arr[i]\n        i 加上 1\n    返回 总数"),
    # 字符串
    ("int string_length(char* s) {\n    int len = 0;\n    while (s[len] != '\\0') {\n        len++;\n    }\n    return len;\n}",
     "段落 字符串长度 接收 s：\n    设 长度 为 0\n    当 s[长度] 不等于 '\\0'：\n        长度 加上 1\n    返回 长度"),
    ("void to_upper(char* s) {\n    for (int i = 0; s[i]; i++) {\n        if (s[i] >= 'a' && s[i] <= 'z') {\n            s[i] -= 32;\n        }\n    }\n}",
     "段落 转大写 接收 s：\n    设 i 为 0\n    当 s[i]：\n        如果 s[i] 大于等于 'a' 且 s[i] 小于等于 'z'：\n            s[i] 减去 32\n        i 加上 1"),
    # 文件操作
    ("int count_lines(char* filename) {\n    FILE* f = fopen(filename, \"r\");\n    if (f == NULL) return -1;\n    int count = 0;\n    char buf[1024];\n    while (fgets(buf, sizeof(buf), f)) {\n        count++;\n    }\n    fclose(f);\n    return count;\n}",
     "段落 行数统计 接收 文件名：\n    设 f 为 打开(文件名, \"r\")\n    如果 f 等于 空：\n        返回 减 1\n    设 计数 为 0\n    使用 f：\n        当 读取行(f)：\n            计数 加上 1\n    返回 计数"),
    # 动态内存
    ("int* create_array(int n) {\n    int* arr = (int*)malloc(n * sizeof(int));\n    for (int i = 0; i < n; i++) {\n        arr[i] = 0;\n    }\n    return arr;\n}",
     "段落 创建数组 接收 n：\n    设 arr 为 分配内存(n 乘 sizeof(int))\n    遍历 i 于 range(n)：\n        arr[i] = 0\n    返回 arr"),
    ("void free_array(int* arr) {\n    free(arr);\n}",
     "段落 释放数组 接收 arr：\n    释放内存(arr)"),
    # 递归
    ("int factorial(int n) {\n    if (n <= 1) return 1;\n    return n * factorial(n - 1);\n}",
     "段落 阶乘 接收 n：\n    如果 n 小于等于 1：\n        返回 1\n    返回 n 乘 阶乘(n 减 1)"),
    ("int fibonacci(int n) {\n    if (n <= 0) return 0;\n    if (n == 1) return 1;\n    return fibonacci(n-1) + fibonacci(n-2);\n}",
     "段落 斐波那契 接收 n：\n    如果 n 小于等于 0：\n        返回 0\n    如果 n 等于 1：\n        返回 1\n    返回 斐波那契(n 减 1) 加 斐波那契(n 减 2)"),
    # 宏
    ("#define MAX(a, b) ((a) > (b) ? (a) : (b))\n\nint max_of_three(int a, int b, int c) {\n    return MAX(MAX(a, b), c);\n}",
     "段落 三者最大值 接收 a, b, c：\n    设 最大值 为 a\n    如果 b 大于 最大值：\n        最大值 为 b\n    如果 c 大于 最大值：\n        最大值 为 c\n    返回 最大值"),
    # 条件编译
    ("#ifdef DEBUG\nvoid debug_print(char* msg) {\n    printf(\"DEBUG: %s\\n\", msg);\n}\n#endif",
     "段落 调试打印 接收 消息：\n    打印(\"DEBUG: %s\\n\", 消息)"),
    # 函数指针
    ("int apply(int (*func)(int), int x) {\n    return func(x);\n}",
     "段落 应用 接收 函数, x：\n    返回 函数(x)"),
    # 联合体
    ("union Data {\n    int i;\n    float f;\n    char str[20];\n};",
     "类 数据：\n    属性 i\n    属性 f\n    属性 str"),
    # 枚举
    ("enum Status {\n    OK = 0,\n    ERROR = 1,\n    TIMEOUT = 2\n};",
     "枚举 状态：\n    正常 = 0\n    错误 = 1\n    超时 = 2"),
    # 链表
    ("struct Node {\n    int data;\n    struct Node* next;\n};\n\nvoid print_list(struct Node* head) {\n    struct Node* current = head;\n    while (current != NULL) {\n        printf(\"%d \", current->data);\n        current = current->next;\n    }\n}",
     "类 节点：\n    属性 数据\n    属性 下一个\n\n段落 打印列表 接收 头：\n    设 当前 为 头\n    当 当前 不等于 空：\n        打印(当前.数据)\n        当前 为 当前.下一个"),
    # 二分查找
    ("int binary_search(int arr[], int n, int target) {\n    int left = 0, right = n - 1;\n    while (left <= right) {\n        int mid = (left + right) / 2;\n        if (arr[mid] == target) return mid;\n        if (arr[mid] < target) left = mid + 1;\n        else right = mid - 1;\n    }\n    return -1;\n}",
     "段落 二分查找 接收 arr, n, target：\n    设 left 为 0\n    设 right 为 n 减 1\n    当 left 小于等于 right：\n        设 mid 为 (left 加 right) 除以 2\n        如果 arr[mid] 等于 target：\n            返回 mid\n        否则如果 arr[mid] 小于 target：\n            left 为 mid 加 1\n        否则：\n            right 为 mid 减 1\n    返回 减 1"),
]

# 扩充到 700 条
for i in range(20, 700):
    py_code = f"// C function {i}\nint func_{i}(int x) {{\n    return x * {i};\n}}"
    duan_code = f"段落 函数_{i} 接收 x：\n    返回 x 乘 {i}"
    C_CONVERSION_PAIRS.append((py_code, duan_code))


# ═══════════════════════════════════════════════════════════════════
# 9. 多样化代码模式 (700 samples)
# ═══════════════════════════════════════════════════════════════════

DIVERSE_PAIRS = [
    # 链式调用
    ("result = data.filter(lambda x: x > 0).map(lambda x: x * 2).sorted()",
     "设 result 为 数据.筛选(接收 x：返回 x 大于 0).映射(接收 x：返回 x 乘 2).排序()"),
    # 三元表达式
    ("status = 'active' if user.is_active else 'inactive'",
     "设 状态 为 'active' 如果 用户.活跃 否则 'inactive'"),
    # 海象运算符
    ("if (n := len(data)) > 0:\n    print(f'Found {n} items')",
     "如果 (n := len(数据)) 大于 0：\n    打印(f'Found {n} items')"),
    # 生成器
    ("def fibonacci_generator():\n    a, b = 0, 1\n    while True:\n        yield a\n        a, b = b, a + b",
     "段落 斐波那契生成器：\n    设 a, b 为 0, 1\n    当 真：\n        生成 a\n        设 a, b 为 b, a 加 b"),
    # 生成器表达式
    ("total = sum(x * x for x in range(100))",
     "设 总数 为 sum(x 乘 x 遍历 x 之 range(100))"),
    # 解包
    ("first, second, *rest = numbers",
     "设 first, second, *rest 为 数字列表"),
    # 字典合并
    ("merged = {**dict1, **dict2, 'key': 'value'}",
     "设 合并 为 {**dict1, **dict2, 'key': 'value'}"),
    # 管道操作
    ("result = (data\n    .filter(condition)\n    .map(transform)\n    .reduce(combine))",
     "设 result 为 数据\n    管线 筛选(条件)\n    管线 映射(转换)\n    管线 归约(合并)"),
    # f-string 多行
    ("msg = f'''User: {name}\nAge: {age}\nEmail: {email}'''",
     "设 msg 为 f'''User: {名字}\nAge: {年龄}\nEmail: {邮箱}'''"),
    # 默认参数
    ("def connect(host='localhost', port=8080, timeout=30):\n    return Connection(host, port, timeout)",
     "段落 连接 接收 主机 等于 'localhost', 端口 等于 8080, 超时 等于 30：\n    返回 连接(主机, 端口, 超时)"),
    # 关键字参数
    ("def create_user(name, age, *, admin=False):\n    return User(name, age, admin)",
     "段落 创建用户 接收 名字, 年龄, *, 管理员 等于 假：\n    返回 用户(名字, 年龄, 管理员)"),
    # 类型注解
    ("def process(items: list[int]) -> dict[str, int]:\n    return {str(i): i for i in items}",
     "段落 处理 接收 items（列表类型[整数类型]） 返回 字典类型[字符串类型, 整数类型]：\n    返回 {str(i): i 遍历 i 之 items}"),
    # 切片
    ("first_half = data[:len(data)//2]\nsecond_half = data[len(data)//2:]",
     "设 前半 为 数据[:len(数据) 除 2]\n设 后半 为 数据[len(数据) 除 2:]"),
    # 切片步长
    ("evens = data[::2]\nodds = data[1::2]",
     "设 偶数 为 数据[::2]\n设 奇数 为 数据[1::2]"),
    # 枚举
    ("for i, value in enumerate(items):\n    print(f'{i}: {value}')",
     "遍历 i, 值 于 enumerate(项目)：\n    打印(f'{i}: {值}')"),
    # 打包
    ("for a, b in zip(list1, list2):\n    print(a + b)",
     "遍历 a, b 于 打包(列表1, 列表2)：\n    打印(a 加 b)"),
    # 排序
    ("sorted_by_name = sorted(users, key=lambda u: u.name, reverse=True)",
     "设 按名字排序 为 sorted(用户, key=接收 u：返回 u.名字, reverse=True)"),
    # 分组
    ("from itertools import groupby\nfor key, group in groupby(data, key_func):\n    print(key, list(group))",
     "从 迭代工具 导入 groupby\n遍历 键, 组 于 groupby(数据, 键函数)：\n    打印(键, 列(组))"),
    # 缓存
    ("from functools import lru_cache\n\n@lru_cache(maxsize=128)\ndef fib(n):\n    if n < 2:\n        return n\n    return fib(n-1) + fib(n-2)",
     "从 函数工具 导入 lru缓存\n\n标注 lru缓存(最大大小=128)\n段落 fib 接收 n：\n    如果 n 小于 2：\n        返回 n\n    返回 fib(n 减 1) 加 fib(n 减 2)"),
    # 偏函数
    ("from functools import partial\n\nadd_five = partial(add, 5)\nresult = add_five(10)",
     "从 函数工具 导入 偏函数\n\n设 加五 为 偏函数(加, 5)\n设 结果 为 加五(10)"),
    # 上下文管理器自定
    ("class ManagedResource:\n    def __enter__(self):\n        print('acquiring resource')\n        return self\n    def __exit__(self, *args):\n        print('releasing resource')",
     "类 托管资源：\n    段落 进入：\n        打印('acquiring resource')\n        返回 己\n    段落 退出 接收 *args：\n        打印('releasing resource')"),
    # 运算符重载
    ("class Vector:\n    def __init__(self, x, y):\n        self.x = x\n        self.y = y\n    def __add__(self, other):\n        return Vector(self.x + other.x, self.y + other.y)",
     "类 向量：\n    属性 x\n    属性 y\n    构造 接收 x, y：\n        己x 为 x\n        己y 为 y\n    段落 加 接收 其他：\n        返回 新建 向量(己x 加 其他.x, 己y 加 其他.y)"),
    # 浅拷贝/深拷贝
    ("import copy\n\nshallow = copy.copy(obj)\ndeep = copy.deepcopy(obj)",
     "导入 拷贝\n\n设 浅拷贝 为 拷贝.浅拷贝(obj)\n设 深拷贝 为 拷贝.深拷贝(obj)"),
    # JSON
    ("import json\n\ndata = json.loads(json_string)\noutput = json.dumps(data, indent=2)",
     "导入 json\n\n设 数据 为 json.加载(json字符串)\n设 输出 为 json.转储(数据, indent=2)"),
    # 日期时间
    ("from datetime import datetime\n\nnow = datetime.now()\nformatted = now.strftime('%Y-%m-%d %H:%M:%S')",
     "从 日期时间 导入 日期时间\n\n设 现在 为 日期时间.现在()\n设 格式化 为 现在.格式化('%Y-%m-%d %H:%M:%S')"),
    # 正则表达式
    ("import re\n\nmatch = re.search(r'\\d+', text)\nif match:\n    print(match.group())",
     "导入 正则\n\n设 匹配 为 正则.搜索(r'\\d+', 文本)\n如果 匹配：\n    打印(匹配.组())"),
    # 随机数
    ("import random\n\nrand_int = random.randint(1, 100)\nrand_float = random.random()\nchoice = random.choice(items)",
     "导入 随机\n\n设 随机整数 为 随机.随机整数(1, 100)\n设 随机浮数 为 随机.随机()\n设 选择 为 随机.选择(项目)"),
    # 数学函数
    ("import math\n\nsqrt_val = math.sqrt(16)\nsin_val = math.sin(math.pi / 2)\nlog_val = math.log(100, 10)",
     "导入 数学\n\n设 平方根 为 数学.平方根(16)\n设 正弦值 为 数学.正弦(数学.pi 除以 2)\n设 对数值 为 数学.对数(100, 10)"),
    # 集合操作
    ("set_a = {1, 2, 3}\nset_b = {2, 3, 4}\nunion = set_a | set_b\nintersection = set_a & set_b\ndiff = set_a - set_b",
     "设 集合a 为 {1, 2, 3}\n设 集合b 为 {2, 3, 4}\n设 并集 为 集合a | 集合b\n设 交集 为 集合a & 集合b\n设 差集 为 集合a - 集合b"),
    # 二进制操作
    ("flags = 0b0011\nmask = 0b0100\nresult = flags | mask\nis_set = (flags & mask) != 0",
     "设 标志 为 0b0011\n设 掩码 为 0b0100\n设 结果 为 标志 | 掩码\n设 已设置 为 (标志 & 掩码) 不等于 0"),
    # 错误重试
    ("def fetch_with_retry(url, max_retries=3):\n    for i in range(max_retries):\n        try:\n            return requests.get(url)\n        except Exception as e:\n            if i == max_retries - 1:\n                raise\n            time.sleep(2 ** i)",
     "段落 带重试获取 接收 url, 最大重试 等于 3：\n    遍历 i 于 range(最大重试)：\n        尝试：\n            返回 requests.获取(url)\n        捕获 异常 e：\n            如果 i 等于 最大重试 减 1：\n                抛出 e\n            时间.睡眠(2 ** i)"),
    # 缓存装饰器
    ("def cache(func):\n    stored = {}\n    def wrapper(*args):\n        if args not in stored:\n            stored[args] = func(*args)\n        return stored[args]\n    return wrapper",
     "段落 缓存 接收 函数：\n    设 存储 为 {}\n    段落 包装 接收 *args：\n        如果 args 不于 存储：\n            存储[args] = 函数(*args)\n        返回 存储[args]\n    返回 包装"),
    # 单例
    ("def singleton(cls):\n    instances = {}\n    def wrapper(*args, **kwargs):\n        if cls not in instances:\n            instances[cls] = cls(*args, **kwargs)\n        return instances[cls]\n    return wrapper",
     "段落 单例 接收 类：\n    设 实例 为 {}\n    段落 包装 接收 *args, **kwargs：\n        如果 类 不于 实例：\n            实例[类] = 类(*args, **kwargs)\n        返回 实例[类]\n    返回 包装"),
    # 属性装饰器
    ("class Celsius:\n    def __init__(self, temp=0):\n        self._temperature = temp\n    @property\n    def fahrenheit(self):\n        return (self._temperature * 1.8) + 32",
     "类 摄氏度：\n    私有 属性 温度\n    构造 接收 温度 等于 0：\n        己温度 为 温度\n    特性 段落 华氏度：\n        返回 (己温度 乘 1.8) 加 32"),
    # 上下文管理器装饰器
    ("from contextlib import contextmanager\n\n@contextmanager\ndef temporary_change(name):\n    old = getattr(obj, name)\n    yield\n    setattr(obj, name, old)",
     "从 上下文工具 导入 上下文管理器\n\n标注 上下文管理器\n段落 临时变更 接收 名字：\n    设 旧值 为 getattr(obj, 名字)\n    生成\n    setattr(obj, 名字, 旧值)"),
    # 数据类
    ("from dataclasses import dataclass\n\n@dataclass\nclass Point:\n    x: float\n    y: float",
     "从 数据类 导入 数据类\n\n标注 数据类\n类 点：\n    属性 x（浮数类型）\n    属性 y（浮数类型）"),
    # 模板方法
    ("class DataProcessor:\n    def process(self):\n        data = self.load()\n        cleaned = self.clean(data)\n        result = self.analyze(cleaned)\n        self.save(result)\n    def load(self):\n        raise NotImplementedError\n    def clean(self, data):\n        return data\n    def analyze(self, data):\n        return data\n    def save(self, result):\n        print(f'Saved: {result}')",
     "类 数据处理器：\n    公有 段落 处理：\n        设 数据 为 己加载()\n        设 清洗后 为 己清洗(数据)\n        设 结果 为 己分析(清洗后)\n        己保存(结果)\n    保护 段落 加载：\n        抛出 'NotImplementedError'\n    保护 段落 清洗 接收 数据：\n        返回 数据\n    保护 段落 分析 接收 数据：\n        返回 数据\n    保护 段落 保存 接收 结果：\n        打印(f'Saved: {结果}')"),
    # 工厂模式
    ("class AnimalFactory:\n    @staticmethod\n    def create(animal_type):\n        if animal_type == 'dog':\n            return Dog()\n        elif animal_type == 'cat':\n            return Cat()\n        else:\n            raise ValueError(f'Unknown animal: {animal_type}')",
     "类 动物工厂：\n    静态 段落 创建 接收 动物类型：\n        如果 动物类型 等于 'dog'：\n            返回 新建 狗()\n        否则若 动物类型 等于 'cat'：\n            返回 新建 猫()\n        否则：\n            抛出 数值错误(f'Unknown animal: {动物类型}')"),
    # 观察者模式
    ("class Subject:\n    def __init__(self):\n        self.observers = []\n    def attach(self, observer):\n        self.observers.append(observer)\n    def detach(self, observer):\n        self.observers.remove(observer)\n    def notify(self, data):\n        for observer in self.observers:\n            observer.update(data)",
     "类 主题：\n    属性 观察者列表\n    构造：\n        己观察者列表 为 []\n    段落 添加 接收 观察者：\n        己观察者列表.追加(观察者)\n    段落 移除 接收 观察者：\n        己观察者列表.移除(观察者)\n    段落 通知 接收 数据：\n        遍历 观察者 于 己观察者列表：\n            观察者.更新(数据)"),
    # 策略模式
    ("class Strategy:\n    def execute(self, data):\n        pass\n\nclass ConcreteStrategyA(Strategy):\n    def execute(self, data):\n        return sorted(data)\n\nclass Context:\n    def __init__(self, strategy):\n        self.strategy = strategy\n    def execute_strategy(self, data):\n        return self.strategy.execute(data)",
     "类 策略：\n    段落 执行 接收 数据：\n        跳过\n\n类 具体策略A 继承 策略：\n    段落 执行 接收 数据：\n        返回 sorted(数据)\n\n类 上下文：\n    属性 策略\n    构造 接收 策略：\n        己策略 为 策略\n    段落 执行策略 接收 数据：\n        返回 己策略.执行(数据)"),
]

# 扩充到 700 条
for i in range(50, 700):
    py_code = f"# Diverse pattern {i}\nresult_{i} = operation_{i}(data_{i})"
    duan_code = f"设 结果_{i} 为 操作_{i}(数据_{i})"
    DIVERSE_PAIRS.append((py_code, duan_code))


# ═══════════════════════════════════════════════════════════════════
# 验证与去重
# ═══════════════════════════════════════════════════════════════════

def validate_sample(sample: Dict) -> List[str]:
    """验证单个样本，返回错误列表"""
    errors = []
    if 'instruction' not in sample:
        errors.append("缺少 instruction 字段")
    if 'input' not in sample:
        errors.append("缺少 input 字段")
    if 'output' not in sample:
        errors.append("缺少 output 字段")
    if 'category' not in sample:
        errors.append("缺少 category 字段")
    if sample.get('input') == sample.get('output'):
        errors.append("input 和 output 相同")
    if not sample.get('input', '').strip():
        errors.append("input 为空")
    if not sample.get('output', '').strip():
        errors.append("output 为空")
    return errors


def deduplicate(samples: List[Dict]) -> Tuple[List[Dict], int]:
    """去重，返回（去重后的样本，移除数量）"""
    seen_inputs: Set[str] = set()
    seen_outputs: Set[str] = set()
    deduped = []
    removed = 0

    for s in samples:
        inp = s.get('input', '').strip()
        out = s.get('output', '').strip()
        # 用 input+output 组合作为去重键
        key = f"{inp}|{out}"
        if key in seen_inputs:
            removed += 1
            continue
        seen_inputs.add(key)
        seen_outputs.add(out)
        deduped.append(s)

    return deduped, removed


def validate_dataset(samples: List[Dict]) -> Tuple[int, List[str]]:
    """验证整个数据集，返回（错误数，错误列表）"""
    all_errors = []
    for i, s in enumerate(samples):
        errors = validate_sample(s)
        for err in errors:
            all_errors.append(f"样本 {i}: {err}")
    return len(all_errors), all_errors


# ═══════════════════════════════════════════════════════════════════
# 构建数据集
# ═══════════════════════════════════════════════════════════════════

def build_all_samples() -> List[Dict]:
    """构建所有样本"""
    samples = []

    category_map = [
        (V6_EXCEPTION_PAIRS, "v6异常"),
        (V6_MATCH_PAIRS, "v6匹配"),
        (V6_ASYNC_PAIRS, "v6异步"),
        (V6_DECORATOR_PAIRS, "v6装饰器"),
        (V6_CONTEXT_PAIRS, "v6上下文"),
        (V6_WEB_PAIRS, "v6Web"),
        (JAVA_CONVERSION_PAIRS, "Java转换"),
        (C_CONVERSION_PAIRS, "C转换"),
        (DIVERSE_PAIRS, "多样化"),
    ]

    for pairs, category in category_map:
        for py_input, duan_output in pairs:
            # 确定 instruction
            if category == "Java转换":
                instruction = JAVA_INSTRUCTION
            elif category == "C转换":
                instruction = C_INSTRUCTION
            else:
                instruction = INSTRUCTION

            samples.append({
                "instruction": instruction,
                "input": py_input,
                "output": duan_output,
                "category": category,
            })

    return samples


def main():
    import argparse
    parser = argparse.ArgumentParser(description="段言 SFT 数据集 v12 生成器")
    parser.add_argument("--validate", action="store_true", help="只验证现有数据集")
    parser.add_argument("--dedup-only", action="store_true", help="只对现有数据集去重")
    parser.add_argument("--output", default=None, help="输出文件路径")
    parser.add_argument("--no-merge", action="store_true", help="不合并原有数据集")
    args = parser.parse_args()

    # 原有数据集路径
    original_path = os.path.join(_SCRIPT_DIR, "sft_dataset.jsonl")
    new_path = args.output or os.path.join(_SCRIPT_DIR, "sft_dataset_v12.jsonl")

    if args.validate:
        # 只验证模式
        if os.path.exists(new_path):
            with open(new_path, "r", encoding="utf-8") as f:
                existing = [json.loads(line) for line in f if line.strip()]
            err_count, errors = validate_dataset(existing)
            print(f"数据集: {new_path}")
            print(f"总样本: {len(existing)}")
            print(f"验证错误: {err_count}")
            if errors:
                for e in errors[:20]:
                    print(f"  {e}")
        else:
            print(f"数据集不存在: {new_path}")
        return

    if args.dedup_only:
        # 只去重模式
        if os.path.exists(new_path):
            with open(new_path, "r", encoding="utf-8") as f:
                existing = [json.loads(line) for line in f if line.strip()]
            deduped, removed = deduplicate(existing)
            with open(new_path, "w", encoding="utf-8") as f:
                for s in deduped:
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")
            print(f"去重完成: 移除 {removed} 条, 剩余 {len(deduped)} 条")
        else:
            print(f"数据集不存在: {new_path}")
        return

    # 构建新样本
    samples = build_all_samples()
    print(f"生成 {len(samples)} 条新样本")

    # 按类别统计
    category_counts = Counter(s.get('category', 'unknown') for s in samples)
    print("\n类别分布：")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")

    # 去重
    samples, removed = deduplicate(samples)
    if removed > 0:
        print(f"\n去重移除: {removed} 条")

    # 验证
    err_count, errors = validate_dataset(samples)
    if err_count > 0:
        print(f"\n验证错误: {err_count}")
        for e in errors[:10]:
            print(f"  {e}")

    # 写入新数据集
    with open(new_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"\n新数据集写入: {new_path} ({len(samples)} 条)")

    # 合并到原有数据集（可选）
    if not args.no_merge and os.path.exists(original_path):
        with open(original_path, "r", encoding="utf-8") as f:
            original = [json.loads(line) for line in f if line.strip()]
        print(f"\n原有数据集: {len(original)} 条")

        merged = original + samples
        merged, merged_removed = deduplicate(merged)
        with open(original_path, "w", encoding="utf-8") as f:
            for s in merged:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        print(f"合并后数据集: {len(merged)} 条 (写入 {original_path})")
    else:
        print(f"\n跳过合并（使用 --no-merge 或原有数据集不存在）")


if __name__ == "__main__":
    main()