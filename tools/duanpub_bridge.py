#!/usr/bin/env python3
"""
duanpub 桥接模块生成器

从 __index__.py 元数据自动生成 duanpub 桥接模块骨架。
根据 duanpub 包名 → Python stdlib 映射，为每个包生成等价的 Python 桥接模块。

用法:
    python tools/duanpub_bridge.py --list-available
    python tools/duanpub_bridge.py --package 文件系统
    python tools/duanpub_bridge.py --batch P0
    python tools/duanpub_bridge.py --batch 5
    python tools/duanpub_bridge.py --package 文件系统 --with-tests
    python tools/duanpub_bridge.py --package 文件系统 --dry-run
"""

import os
import re
import sys
import argparse
from pathlib import Path


# =============================================================================
# 路径常量
# =============================================================================

# 项目根目录（本脚本位于 tools/ 下）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# stdlib 中的 duanpub 桥接模块目录
_STDLIB_DUANPUB_DIR = _PROJECT_ROOT / 'stdlib' / 'duanpub'

# __index__.py 路径
_INDEX_PATH = _STDLIB_DUANPUB_DIR / '__index__.py'

# __init__.py 路径
_INIT_PATH = _STDLIB_DUANPUB_DIR / '__init__.py'

# 测试目录
_TESTS_DIR = _PROJECT_ROOT / 'tests' / 'duanpub'


# =============================================================================
# 标准库映射表
# 包名 → (stdlib_module, description, is_stdlib)
# =============================================================================

STDLIB_MAP = {
    # ---- P0: 已有桥接的包 ----
    'JSON':          ('json', 'json 解析与序列化', True),
    'CSV':           ('csv', 'CSV 读写与解析', True),
    '文件系统':       ('os', 'os/shutil 文件系统操作', True),
    '正则表达式':     ('re', 're 正则表达式操作', True),
    '日期时间':       ('datetime', 'datetime/time 时间日期', True),
    '数学运算':       ('math', 'math 数学运算', True),
    '加密':          ('hashlib', 'hashlib/hmac 哈希与加密', True),

    # ---- P1: 需新建桥接的包 ----
    'HTTP客户端':     ('urllib.request', 'urllib 客户端', True),
    'SQLite':        ('sqlite3', 'sqlite3 数据库', True),
    'Socket':        ('socket', 'socket 网络通信', True),

    # ---- P2: 其他有 stdlib 对应的包 ----
    '路径处理':       ('os.path', 'os.path 路径操作', True),
    '线程':          ('threading', 'threading 线程操作', True),
    '进程管理':       ('subprocess', 'subprocess 进程管理', True),
    '环境变量':       ('os', 'os.environ 环境变量', True),
    '系统信息':       ('platform', 'platform 系统信息', True),
    '缓存系统':       ('functools', 'functools.lru_cache 缓存', True),
    '集合扩展':       ('itertools', 'itertools 迭代器工具', True),
    '随机数':         ('random', 'random 随机数', True),
    '压缩算法':       ('gzip', 'gzip 压缩解压', True),
    '二进制编码':     ('base64', 'base64 编码解码', True),
    '邮件':          ('smtplib', 'smtplib/email 邮件', True),
    '数据结构':       ('collections', 'collections 数据结构', True),
    '排序与搜索':     ('bisect', 'bisect 二分搜索', True),
    '命令行参数':     ('argparse', 'argparse 参数解析', True),
    '网络工具':       ('ipaddress', 'ipaddress 网络地址', True),
    '日志系统':       ('logging', 'logging 日志记录', True),
    '错误处理':       ('builtins', 'builtins 内置错误', True),
    '类型工具':       ('builtins', 'builtins 类型检查', True),
    '字符串处理':     ('builtins', 'builtins/string 字符串', True),
    'HTTP服务端':     ('http.server', 'http.server HTTP 服务', True),
    'URL解析':       ('urllib.parse', 'urllib.parse URL 解析', True),
    'DNS':          ('socket', 'socket 域名解析', True),
    'TOML':         ('tomllib', 'tomllib TOML 解析', True),
    '数据导入导出':   ('csv', 'csv/json 数据导入导出', True),
    '连接池':        ('queue', 'queue 队列连接池', True),
    '统计分析':       ('statistics', 'statistics 统计分析', True),
    '数值计算':       ('math', 'math 数值计算', True),
    '性能分析':       ('time', 'timeit 性能计时', True),
    '任务队列':       ('queue', 'queue 任务队列', True),
    '事件驱动':       ('asyncio', 'asyncio 事件驱动', True),
    '协程':          ('asyncio', 'asyncio 协程', True),
    '异步运行时':     ('asyncio', 'asyncio 异步运行时', True),
    '迭代器工具':     ('itertools', 'itertools 迭代器工具', True),
    '并行计算':       ('concurrent.futures', 'concurrent.futures 并行', True),
    '文件上传':       ('cgi', 'cgi 文件上传', True),
    '模板渲染':       ('string', 'string.Template 模板', True),
    '算法工具':       ('bisect', 'bisect/heapq 算法', True),
    '科学计算':       ('math', 'math 科学计算', True),
    '日期序列':       ('datetime', 'datetime 日期序列', True),
    '系统托盘':       ('custom', '无直接 stdlib 等效', False),
    'GUI框架':       ('custom', '无直接 stdlib 等效', False),
    '2D绘图':        ('custom', '无直接 stdlib 等效', False),
    '图表':          ('custom', '无直接 stdlib 等效', False),
    '数据可视化':     ('custom', '无直接 stdlib 等效', False),
    '数据框':        ('custom', '无直接 stdlib 等效', False),
    '数据清洗':       ('custom', '无直接 stdlib 等效', False),
    '哈希':          ('hashlib', 'hashlib 哈希', True),
    '域名解析':       ('socket', 'socket 域名解析', True),
    '加密算法':       ('hashlib', 'hashlib 加密算法', True),
    '密码哈希':       ('hashlib', 'hashlib 密码哈希', True),
    '对称加密':       ('cryptography', 'cryptography 对称加密', False),
    '非对称加密':     ('cryptography', 'cryptography 非对称加密', False),
    '数字签名':       ('cryptography', 'cryptography 数字签名', False),
    '证书':          ('ssl', 'ssl 证书', True),
    'JWT':           ('jwt', 'PyJWT JWT 令牌', False),
    'OAuth客户端':   ('custom', '无直接 stdlib 等效', False),
    '图像处理':       ('PIL', 'Pillow 图像处理', False),
    '图像编解码':     ('PIL', 'Pillow 图像编解码', False),
    '字体渲染':       ('PIL', 'Pillow 字体渲染', False),
    '音频处理':       ('wave', 'wave 音频处理', True),
    '视频处理':       ('custom', '无直接 stdlib 等效', False),
    '游戏引擎绑定':   ('custom', '无直接 stdlib 等效', False),
    '文档格式':       ('custom', '无直接 stdlib 等效', False),
    '文档生成':       ('custom', '无直接 stdlib 等效', False),
    '代码格式化':     ('custom', '无直接 stdlib 等效', False),
    '构建工具':       ('custom', '无直接 stdlib 等效', False),
    '静态分析':       ('custom', '无直接 stdlib 等效', False),
    '调试器':        ('custom', '无直接 stdlib 等效', False),
    '测试框架增强':   ('custom', '无直接 stdlib 等效', False),
    '包管理增强':     ('custom', '无直接 stdlib 等效', False),
    '内存管理':       ('custom', '无直接 stdlib 等效', False),
    '响应式编程':     ('custom', '无直接 stdlib 等效', False),
    'Actor模型':     ('custom', '无直接 stdlib 等效', False),
    'AI推理':        ('custom', '无直接 stdlib 等效', False),
    'API文档':       ('custom', '无直接 stdlib 等效', False),
    'RPC框架':       ('custom', '无直接 stdlib 等效', False),
    'Web框架':       ('custom', '无直接 stdlib 等效', False),
    'NoSQL连接器':   ('custom', '无直接 stdlib 等效', False),
    'Redis绑定':     ('custom', '无直接 stdlib 等效', False),
    'WebSocket':     ('custom', '无直接 stdlib 等效', False),
    '控件库':        ('custom', '无直接 stdlib 等效', False),
    '对话框':        ('custom', '无直接 stdlib 等效', False),
    '云存储':        ('custom', '无直接 stdlib 等效', False),
    '字节编码':       ('base64', 'base64 字节编码', True),
    '数据格式':       ('json', 'json 数据格式', True),
    '对象关系映射':   ('custom', '无直接 stdlib 等效', False),
    '查询构建器':     ('custom', '无直接 stdlib 等效', False),
    '地理计算':       ('custom', '无直接 stdlib 等效', False),
    '性能监控':       ('custom', '无直接 stdlib 等效', False),
    '健康检查':       ('custom', '无直接 stdlib 等效', False),
    '访问控制':       ('custom', '无直接 stdlib 等效', False),
    '配置管理':       ('configparser', 'configparser 配置', True),
    '单元测试框架':   ('unittest', 'unittest 测试', True),
    'HTTP服务框架':  ('http.server', 'http.server 服务', True),
    '日志框架':       ('logging', 'logging 日志', True),
    '任务调度':       ('schedule', 'schedule 任务调度', False),
    '消息队列':       ('queue', 'queue 消息队列', True),
    '序列化':        ('pickle', 'pickle 序列化', True),
    '模板引擎':       ('string', 'string.Template 模板', True),
    '国际化和本地化': ('gettext', 'gettext i18n', True),
    '测试':          ('unittest', 'unittest 测试', True),
    '性能分析工具':   ('profile', 'cProfile 性能分析', True),
    '代码覆盖率':     ('coverage', 'coverage 覆盖率', False),
    'Mock框架':      ('unittest.mock', 'unittest.mock Mock', True),
    '属性访问':       ('builtins', 'builtins 属性', True),
    '函数式编程':     ('itertools', 'itertools/functools 函数式', True),
    '元编程':        ('builtins', 'builtins 元编程', True),
    '反射':          ('inspect', 'inspect 反射', True),
    '注解处理':       ('builtins', 'builtins 注解', True),
    '类型提示':       ('typing', 'typing 类型提示', True),
    '时间和日期':     ('datetime', 'datetime 时间日期', True),
    '实用工具':       ('builtins', 'builtins 实用工具', True),
    '数学工具':       ('math', 'math 数学工具', True),
    '字符串工具':     ('string', 'string 字符串工具', True),
    '数据验证':       ('custom', '无直接 stdlib 等效', False),
    '数据转换':       ('custom', '无直接 stdlib 等效', False),
    '数据生成':       ('custom', '无直接 stdlib 等效', False),
    '数据采样':       ('random', 'random 数据采样', True),
    '数据压缩':       ('gzip', 'gzip 数据压缩', True),
    '数据加密':       ('hashlib', 'hashlib 数据加密', True),
    '数据编码':       ('base64', 'base64 数据编码', True),
    '数据序列化':     ('json', 'json 数据序列化', True),
    '数据解析':       ('json', 'json 数据解析', True),
    '数据格式化':     ('json', 'json 数据格式化', True),
    '数据存储':       ('sqlite3', 'sqlite3 数据存储', True),
    '数据同步':       ('custom', '无直接 stdlib 等效', False),
    '数据备份':       ('shutil', 'shutil 数据备份', True),
    '数据恢复':       ('custom', '无直接 stdlib 等效', False),
    '数据迁移':       ('custom', '无直接 stdlib 等效', False),
    '数据索引':       ('custom', '无直接 stdlib 等效', False),
    '数据查询':       ('sqlite3', 'sqlite3 数据查询', True),
    '数据聚合':       ('custom', '无直接 stdlib 等效', False),
    '数据报表':       ('custom', '无直接 stdlib 等效', False),
    '数据管道':       ('custom', '无直接 stdlib 等效', False),
    '数据摄取':       ('custom', '无直接 stdlib 等效', False),
    '数据导出':       ('csv', 'csv 数据导出', True),
    '数据导入':       ('csv', 'csv 数据导入', True),
    'Markdown':      ('markdown', 'markdown 解析', False),
    'YAML':          ('yaml', 'PyYAML 解析', False),
    '请求验证':       ('custom', '无直接 stdlib 等效', False),
    '路由':          ('custom', '无直接 stdlib 等效', False),
    '中间件集合':     ('custom', '无直接 stdlib 等效', False),
    '支付集成':       ('custom', '无直接 stdlib 等效', False),
    '短信':          ('custom', '无直接 stdlib 等效', False),
    '第三方登录':     ('custom', '无直接 stdlib 等效', False),
    '对象存储':       ('custom', '无直接 stdlib 等效', False),
    '全文搜索':       ('custom', '无直接 stdlib 等效', False),
    '认证授权':       ('custom', '无直接 stdlib 等效', False),
    '数据库迁移':     ('custom', '无直接 stdlib 等效', False),
    '数值工具':       ('custom', '无直接 stdlib 等效', False),
    '图形渲染':       ('custom', '无直接 stdlib 等效', False),
    '图像处理增强':   ('custom', '无直接 stdlib 等效', False),
    'XML':           ('xml.etree', 'xml.etree 解析', True),
    '哈希算法':       ('hashlib', 'hashlib 哈希算法', True),
    '随机数':         ('random', 'random 随机数', True),
}


def load_index():
    """加载 __index__.py 中的 PACKAGES 字典"""
    sys.path.insert(0, str(_STDLIB_DUANPUB_DIR.parent))
    try:
        # 动态导入 __index__
        import importlib.util
        spec = importlib.util.spec_from_file_location('__index__', str(_INDEX_PATH))
        if not spec or not spec.loader:
            print("错误: 无法加载 __index__.py", file=sys.stderr)
            sys.exit(1)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.PACKAGES
    except Exception as e:
        print(f"错误: 加载 __index__.py 失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if str(_STDLIB_DUANPUB_DIR.parent) in sys.path:
            sys.path.remove(str(_STDLIB_DUANPUB_DIR.parent))


def get_stdlib_info(pkg_name):
    """获取包对应的 stdlib 信息。返回 (module_name, description, is_stdlib) 或 None"""
    return STDLIB_MAP.get(pkg_name)


def parse_func_name(func_str):
    """
    解析函数名字符串，提取函数名和参数列表。

    '__index__.py' 中的函数名可能为：
    - '解析JSON'        → 纯函数名
    - '创建HTTPServer(host,port):'  → 带参数声明
    - '创建路径：(x, y)' → 带冒号和参数

    返回 (函数名, 参数列表字符串)
    """
    func_str = func_str.strip()

    # 去掉末尾的冒号（如果有）
    func_str = func_str.rstrip(':')

    # 尝试匹配 函数名(参数列表) 模式
    m = re.match(r'^([^（(]+)[（(]([^）)]*)[）)]$', func_str)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # 纯函数名
    return func_str, ''


def generate_param_list(params_str):
    """
    将参数字符串转换为 Python 函数参数列表。

    'host,port' → 'host, port'
    'url, headers=None, timeout=30' → 'url, headers=None, timeout=30'
    '' → ''
    """
    if not params_str:
        return ''
    # 分割参数，处理空白
    parts = [p.strip() for p in params_str.split(',') if p.strip()]
    return ', '.join(parts)


def generate_bridge_content(pkg_name, pkg_info, stdlib_info):
    """
    为指定包生成桥接模块的 Python 代码内容。

    Args:
        pkg_name: 包名（如 'JSON'）
        pkg_info: 包元数据字典（来自 __index__.py）
        stdlib_info: (module_name, description, is_stdlib) 或 None

    Returns:
        Python 源代码字符串
    """
    module_name, stdlib_desc, is_stdlib = stdlib_info or ('custom', '自定义实现', False)
    pkg_desc = pkg_info.get('description', pkg_name)
    functions = pkg_info.get('functions', [])

    lines = []
    desc_lines = []

    # 模块文档字符串
    lines.append(f'"""')
    lines.append(f'{pkg_name} — duanpub 桥接模块')
    lines.append(f'')
    if is_stdlib:
        lines.append(f'基于 Python {module_name} 库封装，函数名对齐 duanpub/packages/{pkg_name}/源.duan。')
        lines.append(f'')
        lines.append(f'duanpub 原始包通过 C FFI 实现 {pkg_desc}，')
        lines.append(f'本桥接模块用 Python {module_name} 模块替代，提供等价的 {pkg_desc} 功能。')
    else:
        lines.append(f'桥接模块骨架 — {pkg_name} ({pkg_desc})')
        lines.append(f'')
        if module_name == 'custom':
            lines.append(f'注意：此包无直接的 Python 标准库等效实现，')
            lines.append(f'需根据实际需求实现具体逻辑。')
        else:
            lines.append(f'基于第三方库 {module_name} 实现 {pkg_desc} 功能。')
    lines.append(f'"""')
    lines.append(f'')

    # 导入语句
    if is_stdlib and module_name != 'builtins':
        if module_name == 'os':
            lines.append('import os as _os')
            lines.append('import shutil as _shutil')
        elif module_name == 'hashlib':
            lines.append('import hashlib as _hashlib')
            lines.append('import hmac as _hmac')
        elif module_name == 'datetime':
            lines.append('import datetime as _datetime')
            lines.append('import time as _time')
        elif module_name == 'base64':
            lines.append('import base64 as _b64')
        elif module_name == 'socket':
            lines.append('import socket as _socket')
        elif module_name == 'queue':
            lines.append('import queue as _queue')
        elif module_name == 'asyncio':
            lines.append('import asyncio as _asyncio')
        elif module_name == 'itertools':
            lines.append('import itertools as _itertools')
        elif module_name == 'concurrent.futures':
            lines.append('import concurrent.futures as _futures')
        elif module_name == 'urllib.request':
            lines.append('import urllib.request')
            lines.append('import urllib.error')
            lines.append('import urllib.parse')
        elif module_name == 'http.server':
            lines.append('import http.server as _http_server')
        elif module_name == 'urllib.parse':
            lines.append('import urllib.parse as _urlparse')
        elif module_name == 'unittest':
            lines.append('import unittest as _unittest')
        elif module_name == 'uuid':
            lines.append('import uuid as _uuid')
        elif module_name == 'gzip':
            lines.append('import gzip as _gzip')
        elif module_name == 'ssl':
            lines.append('import ssl as _ssl')
        elif module_name == 'csv':
            lines.append('import csv as _csv')
        elif module_name == 're':
            lines.append('import re as _re')
        elif module_name == 'json':
            lines.append('import json as _json')
        elif module_name == 'sqlite3':
            lines.append('import sqlite3 as _sqlite3')
        else:
            # 通用导入
            safe_name = module_name.replace('.', '_')
            lines.append(f'import {module_name} as _{safe_name}')
        lines.append('')

    # 非 stdlib 的骨架说明
    if not is_stdlib:
        lines.append('# =============================================================================')
        lines.append(f'# 注意：{pkg_name} 无直接的 Python 标准库等效')
        lines.append('# 以下函数骨架请根据实际需求实现具体逻辑')
        lines.append('# =============================================================================')
        lines.append('')

    # 生成函数
    for func_str in functions:
        func_name, params_str = parse_func_name(func_str)
        py_params = generate_param_list(params_str)

        # 跳过内部函数（以 _ 开头或包含 _内部 标记）
        if func_name.startswith('_') or '_内部' in func_name:
            continue

        # 生成函数文档
        if not is_stdlib:
            doc = f'{func_name} — {pkg_name} 功能函数（需实现）'
        else:
            doc = f'{func_name} — {pkg_desc} 功能函数'

        lines.append(f'')
        lines.append(f'def {func_name}({py_params}):')
        lines.append(f'    """{doc}"""')
        lines.append(f'    # TODO: 实现 {func_name} 逻辑')
        if is_stdlib:
            lines.append(f'    raise Exception("{func_name}失败: 未实现")')
        else:
            lines.append(f'    raise Exception("{func_name}失败: 未实现（需自定义实现）")')
        lines.append(f'')

    return '\n'.join(lines)


def generate_test_content(pkg_name, pkg_info):
    """生成测试文件内容"""
    functions = pkg_info.get('functions', [])
    test_funcs = []
    seen = set()
    for func_str in functions:
        func_name, _ = parse_func_name(func_str)
        if func_name.startswith('_') or '_内部' in func_name:
            continue
        if func_name in seen:
            continue
        seen.add(func_name)
        test_funcs.append(func_name)

    lines = []
    lines.append(f'"""测试 {pkg_name} 桥接模块"""')
    lines.append(f'')
    lines.append(f'import sys')
    lines.append(f'import os')
    lines.append(f'sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stdlib"))')
    lines.append(f'')
    lines.append(f'from duanpub.{pkg_name} import *')
    lines.append(f'')

    for func_name in test_funcs:
        lines.append(f'')
        lines.append(f'def test_{func_name}():')
        lines.append(f'    """测试 {func_name}"""')
        lines.append(f'    # TODO: implement real test')
        lines.append(f'    pass')
        lines.append(f'')

    lines.append(f"if __name__ == '__main__':")
    for func_name in test_funcs:
        lines.append(f'    test_{func_name}()')
    lines.append(f'    print("全部测试通过")')
    lines.append(f'')

    return '\n'.join(lines)


def read_current_bridge_map():
    """读取 __init__.py 中当前的 _STDLIB_BRIDGE 映射"""
    bridge_map = {}
    if not _INIT_PATH.exists():
        return bridge_map
    try:
        content = _INIT_PATH.read_text('utf-8')
        # 找到 _STDLIB_BRIDGE = { ... } 字典
        m = re.search(r'_STDLIB_BRIDGE\s*=\s*\{([^}]+)\}', content, re.DOTALL)
        if m:
            dict_body = m.group(1)
            # 匹配 '包名': '模块名',
            for item in re.finditer(r"['\"](\w+)['\"]\s*:\s*['\"](\w+)['\"]", dict_body):
                bridge_map[item.group(1)] = item.group(2)
    except Exception:
        pass
    return bridge_map


def update_init_bridge_map(new_bridges):
    """
    更新 __init__.py 中的 _STDLIB_BRIDGE 映射，添加新的桥接条目。

    Args:
        new_bridges: dict {包名: 模块名}
    """
    if not _INIT_PATH.exists():
        print(f"警告: {_INIT_PATH} 不存在，跳过更新", file=sys.stderr)
        return

    content = _INIT_PATH.read_text('utf-8')

    # 读取当前映射
    current_map = read_current_bridge_map()

    # 合并新条目
    current_map.update(new_bridges)

    # 按包名排序
    sorted_items = sorted(current_map.items(), key=lambda x: x[0])

    # 构建新的 _STDLIB_BRIDGE 字典文本
    indent = '    '
    dict_lines = [f'{indent}# P0 包名 → duanpub 桥接模块名映射']
    dict_lines.append(f'{indent}# 这些包已有 Python 桥接实现，导入时路由到 stdlib/duanpub/ 下的桥接模块')
    dict_lines.append(f'{indent}# 桥接模块封装 Python 标准库，提供中文名 API')
    dict_lines.append(f'{indent}_STDLIB_BRIDGE = {{')
    for name, mod in sorted_items:
        dict_lines.append(f"{indent}{indent}'{name}':\t'{mod}',\t\t# 桥接: stdlib/duanpub/{mod}.py")
    dict_lines.append(f'{indent}}}')

    new_dict_text = '\n'.join(dict_lines)

    # 替换文件中 _STDLIB_BRIDGE 部分
    pattern = r'_STDLIB_BRIDGE\s*=\s*\{[^}]+\}'
    new_content = re.sub(pattern, new_dict_text, content, count=1, flags=re.DOTALL)

    if new_content != content:
        _INIT_PATH.write_text(new_content, 'utf-8')
        print(f"已更新: {_INIT_PATH}")
    else:
        print(f"无需更新: {_INIT_PATH}")


def list_available():
    """列出所有可桥接的包（有 stdlib 等效的包）"""
    packages = load_index()

    print(f"{'包名':<20} {'优先级':<8} {'Stdlib 模块':<25} {'函数数':<8} 描述")
    print('-' * 90)

    available = []
    for pkg_name in sorted(packages.keys()):
        stdlib_info = get_stdlib_info(pkg_name)
        if stdlib_info and stdlib_info[2]:  # is_stdlib
            available.append(pkg_name)

    # 按优先级排序
    priority_order = {'P0': 0, 'P1': 1, 'P2': 2}
    available.sort(key=lambda n: (
        priority_order.get(packages[n].get('priority', 'P2'), 99),
        n
    ))

    for pkg_name in available:
        info = packages[pkg_name]
        stdlib_info = get_stdlib_info(pkg_name)
        module_name = stdlib_info[0] if stdlib_info else '?'
        priority = info.get('priority', 'P2')
        func_count = info.get('function_count', 0)
        desc = info.get('description', '')[:40]
        print(f"{pkg_name:<20} {priority:<8} {module_name:<25} {func_count:<8} {desc}")

    print(f"\n总计: {len(available)} 个可桥接的包")


def generate_bridge(pkg_name, output_dir, force=False, dry_run=False, with_tests=False, test_dir=None):
    """
    为指定包生成桥接模块。

    Returns:
        (generated_bridge, generated_test) — 是否生成了桥接文件和测试文件
    """
    packages = load_index()

    if pkg_name not in packages:
        print(f"错误: 包 '{pkg_name}' 不存在于索引中", file=sys.stderr)
        return False, False

    pkg_info = packages[pkg_name]
    stdlib_info = get_stdlib_info(pkg_name)

    if not stdlib_info:
        print(f"警告: 包 '{pkg_name}' 无标准库映射，将生成自定义骨架", file=sys.stderr)
        # 使用一个默认的 custom 映射
        stdlib_info = ('custom', '自定义实现', False)

    # 生成桥接模块
    content = generate_bridge_content(pkg_name, pkg_info, stdlib_info)
    bridge_filename = f'{pkg_name}.py'
    bridge_path = os.path.join(output_dir, bridge_filename)

    bridge_generated = False
    if dry_run:
        print(f"\n[DRY RUN] 将生成桥接模块: {bridge_path}")
        print(f"[DRY RUN] 内容预览 ({len(content)} 字符):")
        # 只显示前 20 行
        preview_lines = content.split('\n')[:20]
        for line in preview_lines:
            print(f"  | {line}")
        if len(content.split('\n')) > 20:
            print(f"  | ... (共 {len(content.split('\n'))} 行)")
        bridge_generated = True
    else:
        if os.path.exists(bridge_path) and not force:
            print(f"跳过: {bridge_path} 已存在（使用 --force 覆盖）")
        else:
            os.makedirs(output_dir, exist_ok=True)
            with open(bridge_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"已生成: {bridge_path}")
            bridge_generated = True

    # 生成测试文件
    test_generated = False
    if with_tests:
        test_content = generate_test_content(pkg_name, pkg_info)
        test_dir_path = test_dir or _TESTS_DIR
        test_filename = f'test_{pkg_name}.py'
        test_path = os.path.join(test_dir_path, test_filename)

        if dry_run:
            print(f"\n[DRY RUN] 将生成测试文件: {test_path}")
            print(f"[DRY RUN] 内容预览 ({len(test_content)} 字符):")
            preview_lines = test_content.split('\n')[:10]
            for line in preview_lines:
                print(f"  | {line}")
            if len(test_content.split('\n')) > 10:
                print(f"  | ... (共 {len(test_content.split('\n'))} 行)")
            test_generated = True
        else:
            if os.path.exists(test_path) and not force:
                print(f"跳过: {test_path} 已存在（使用 --force 覆盖）")
            else:
                os.makedirs(test_dir_path, exist_ok=True)
                with open(test_path, 'w', encoding='utf-8') as f:
                    f.write(test_content)
                print(f"已生成: {test_path}")
                test_generated = True

    return bridge_generated, test_generated


def main():
    parser = argparse.ArgumentParser(
        description='duanpub 桥接模块生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --list-available                   # 列出可桥接的包
  %(prog)s --package 文件系统                   # 为单个包生成桥接
  %(prog)s --batch P0                          # 批量生成 P0 优先级的包
  %(prog)s --batch 5                           # 批量生成前5个最高优先级的包
  %(prog)s --package 文件系统 --with-tests      # 同时生成测试文件
  %(prog)s --package 文件系统 --dry-run         # 预览要生成的内容
  %(prog)s --package 文件系统 --force           # 覆盖已存在的桥接模块
        """
    )
    parser.add_argument('--package', type=str, help='要桥接的包名')
    parser.add_argument('--batch', type=str, help='批量生成：P0/P1/P2 优先级，或数字 N 表示前 N 个最高优先级的包')
    parser.add_argument('--list-available', action='store_true', help='列出可桥接的包')
    parser.add_argument('--output-dir', type=str, default=str(_STDLIB_DUANPUB_DIR),
                        help=f'输出目录（默认: {_STDLIB_DUANPUB_DIR}）')
    parser.add_argument('--force', action='store_true', help='覆盖已存在的桥接模块')
    parser.add_argument('--with-tests', action='store_true', help='同时生成测试文件')
    parser.add_argument('--test-dir', type=str, default=str(_TESTS_DIR),
                        help=f'测试文件输出目录（默认: {_TESTS_DIR}）')
    parser.add_argument('--dry-run', action='store_true', help='仅预览，不实际写入文件')
    parser.add_argument('--update-init', action='store_true', help='生成后更新 __init__.py 的 _STDLIB_BRIDGE 映射')

    args = parser.parse_args()

    # --list-available
    if args.list_available:
        list_available()
        return

    # 确定要生成的包列表
    packages_to_generate = []

    if args.package:
        packages_to_generate.append(args.package)

    elif args.batch:
        packages = load_index()
        batch_val = args.batch.strip()

        if batch_val in ('P0', 'P1', 'P2'):
            # 按优先级过滤
            priority_map = {'P0': 0, 'P1': 1, 'P2': 2}
            for pkg_name, info in sorted(packages.items(),
                                         key=lambda x: (priority_map.get(x[1].get('priority', 'P2'), 99), x[0])):
                if info.get('priority') == batch_val:
                    stdlib_info = get_stdlib_info(pkg_name)
                    if stdlib_info and stdlib_info[2]:
                        packages_to_generate.append(pkg_name)
        elif batch_val.isdigit():
            # 取前 N 个最高优先级的可桥接包
            count = int(batch_val)
            priority_map = {'P0': 0, 'P1': 1, 'P2': 2}
            candidates = []
            for pkg_name, info in packages.items():
                stdlib_info = get_stdlib_info(pkg_name)
                if stdlib_info and stdlib_info[2]:
                    candidates.append((pkg_name, info))

            candidates.sort(key=lambda x: (
                priority_map.get(x[1].get('priority', 'P2'), 99),
                x[0]
            ))
            packages_to_generate = [c[0] for c in candidates[:count]]
        else:
            print(f"错误: 无效的 --batch 参数 '{args.batch}'，请使用 P0/P1/P2 或数字", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()
        return

    if not packages_to_generate:
        print("没有需要生成的包。")
        return

    # 生成桥接模块
    generated_bridges = []
    for pkg_name in packages_to_generate:
        bridge_ok, test_ok = generate_bridge(
            pkg_name,
            args.output_dir,
            force=args.force,
            dry_run=args.dry_run,
            with_tests=args.with_tests,
            test_dir=args.test_dir,
        )
        if bridge_ok:
            generated_bridges.append(pkg_name)

    # 更新 __init__.py
    if args.update_init and generated_bridges and not args.dry_run:
        new_bridges = {name: name for name in generated_bridges}
        update_init_bridge_map(new_bridges)

    # 总结
    if not args.dry_run:
        print(f"\n完成: 生成了 {len(generated_bridges)}/{len(packages_to_generate)} 个桥接模块")
        if generated_bridges:
            print(f"已生成: {', '.join(generated_bridges)}")


if __name__ == '__main__':
    main()