#!/usr/bin/env python3
"""重新生成 `docs/原生腿能力清单.json`（原生腿能力清单的机读版）。

四张表（语句节点 / 表达式节点 / 内置函数 / 运行时符号）全部从源码里抽，
每条带 `文件:行号` 证据。清单由 `tests/unit/test_native_leg_capability.py`
双向咬合：代码加了 JSON 没登记会红（防腐烂），JSON 写了代码没有的也会红（防吹牛）。

所以改了 codegen 的分派链 / 内置表 / `declare` 之后，跑一次本脚本即可：

    python scripts/gen_native_capability_json.py

（第七轮 B7 交付。原名 `_taskB7_gen_json.py`——`_taskB7_` 是按规程收尾要删掉的
临时前缀，而这脚本是长期要留的工具，所以合并期改成了正式名字。）
"""
import json, re, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CG = os.path.join(BASE, 'src', 'llvm', 'codegen_typed.py')
RT = os.path.join(BASE, 'src', 'llvm', 'runtime_typed.c')

with open(CG, encoding='utf-8') as f:
    cg_lines = f.readlines()
cg_src = ''.join(cg_lines)

with open(RT, encoding='utf-8') as f:
    rt_lines = f.readlines()

def get_method_range(src, name):
    lines = src.split('\n')
    start = None
    for i, line in enumerate(lines):
        if f'def {name}(' in line:
            start = i
            break
    if start is None:
        return None, None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith('    def ') and not lines[i].startswith('        '):
            end = i
            break
    return start + 1, end + 1

# 1. Statement nodes
stmt_start, stmt_end = get_method_range(cg_src, '_gen_statement')
stmt_body_lines = cg_lines[stmt_start-1:stmt_end-1] if stmt_start else []
stmt_types = set()
for line in stmt_body_lines:
    for m in re.finditer(r'isinstance\(stmt, ast\.([A-Za-z_]\w*)', line):
        stmt_types.add(m.group(1))

# 2. Expression nodes
expr_start, expr_end = get_method_range(cg_src, '_gen_expression')
expr_body_lines = cg_lines[expr_start-1:expr_end-1] if expr_start else []
expr_types = set()
for line in expr_body_lines:
    for m in re.finditer(r'isinstance\(expr, ast\.([A-Za-z_]\w*)', line):
        expr_types.add(m.group(1))

# 3. Builtin functions with absolute line numbers
builtin_start, builtin_end = get_method_range(cg_src, '_gen_typed_builtin')
builtin_lines = cg_lines[builtin_start-1:builtin_end-1] if builtin_start else []
builtins = {}
for i, line in enumerate(builtin_lines):
    abs_line = builtin_start + i
    m = re.search(r"if name in \(([^)]+)\)", line)
    if m:
        names = re.findall(r"'([^']+)'", m.group(1))
        for n in names:
            if n not in builtins:
                builtins[n] = abs_line
    m2 = re.search(r"\('([^']+)',\s*'([^']+)'\):\s*'([^']+)'", line)
    if m2:
        cn, en, cfunc = m2.groups()
        for n in [cn, en]:
            if n not in builtins:
                builtins[n] = abs_line

# 4. Runtime symbols
runtime_symbols = {}
for i, line in enumerate(cg_lines):
    m = re.search(r"'declare\s+\S+\s+@(\w+)\s*\(", line)
    if m:
        sym = m.group(1)
        if sym not in runtime_symbols:
            runtime_symbols[sym] = {'cg_line': i + 1}

for sym in list(runtime_symbols.keys()):
    if sym in ('setjmp', '_setjmp'):
        runtime_symbols[sym]['rt_line'] = 'C-library'
        continue
    pattern = re.compile(rf'^(?:[\w\s\*]+)\s+{re.escape(sym)}\s*\(')
    for i, line in enumerate(rt_lines):
        if pattern.match(line.rstrip()):
            runtime_symbols[sym]['rt_line'] = i + 1
            break

# --- Categorization ---

def categorize_builtin(name):
    socket_kw = {'socket', 'socket_create', 'socket_connect', 'socket_send', 'socket_recv',
                 'socket_close', 'socket_last_error', 'socket_last_error_code',
                 '创建socket', '连接socket', '发送socket', '接收socket', '关闭socket',
                 'socket错误', 'socket错误码'}
    poller_kw = {'poller_create', 'poller_destroy', 'poller_register', 'poller_wait',
                 'poller_last_error', 'poller_backend', 'poller_count',
                 '创建poller', '销毁poller', '注册poller', 'poller错误', 'poller后端', 'poller计数'}
    eventloop_kw = {'run_event_loop', '运行事件循环', 'sleep', '睡眠', 'await_io'}
    tls_kw = {'tls_wrap', 'tls_handshake', 'tls_want_event', 'tls_is_ready', 'tls_flush',
              'tls_send', 'tls_send_n', 'tls_recv', 'tls_recv_status', 'tls_free',
              'tls_set_verify', 'tls_add_trusted_cert', 'tls_last_error',
              '包装tls', '握手tls', '等待事件tls', '就绪tls', '冲刷tls', '发送tls',
              '发送tls长度', '接收tls', '接收状态tls', '释放tls', '校验tls',
              '信任证书tls', '错误tls'}
    io_kw = {'输出', '打印', 'input', '输入'}
    file_kw = {'file_exists', 'path_exists', 'read_file', 'load_file', '_读文件',
               'write_file', 'save_file', 'append_file', 'write_append',
               'file_size', 'delete_file', 'remove_file', 'list_dir', 'dir_list',
               'mkdir', 'rmdir', 'rename_file', 'copy_file', 'is_file', 'is_dir',
               '文件存在', '读取文件', '写入文件', '追加文件', '文件大小', '删除文件', '列出目录'}
    math_kw = {'sin', 'cos', 'sqrt', 'abs', 'pow', 'floor', 'ceil', 'mod',
               'tan', 'asin', 'acos', 'atan', 'atan2', 'log', 'log2', 'log10',
               'exp', 'round', 'trunc', 'sign', 'hypot', 'degrees', 'radians',
               'min', 'max', 'gcd', 'lcm',
               '正弦', '余弦', '平方根', '绝对值', '幂', '向下取整', '向上取整', '取模'}
    string_kw = {'substr', 'substring', 'find', 'str_find', 'upper', 'to_upper',
                 'lower', 'to_lower', 'trim', 'strip', 'replace', 'str_replace',
                 'split', 'str_split', 'join', 'str_join', 'implode',
                 'str_repeat', 'str_contains', 'str_starts_with', 'str_ends_with',
                 'str_count', 'str_rjust', 'str_ljust', 'str_center', 'str_reverse',
                 '截取', '查找', '大写', '小写', '去除空格', '替换', '分割', '连接字符串'}
    list_kw = {'new_list', 'list', 'append', 'contains', 'insert', 'remove',
               'set', 'list_set', 'index_of', 'list_index', 'list_contains',
               'reverse', 'list_reverse', 'sort', 'list_sort',
               '新建', '新建列表', '列表创建', '列', '列表', '创建列表', '列表追加',
               '包含', '列表包含', '插入', '删除', '设置', '索引查找',
               '反转', '排序', '列表获取', '字符串获取', '获取', '索引'}
    dict_kw = {'dict', '字典', '新建字典', '创建字典', '字典创建', '字典设置',
               '字典添加', '字典获取', '字典包含键', '字典有键', '字典键', '字典键列表'}
    type_kw = {'int', 'to_int', 'float', 'to_float', 'to_bool', 'bool',
               'to_string', 'isinstance', 'instance_of', 'type', 'typeof',
               'type_name', '整数', '转整数', '浮点数', '转浮点', '转布尔',
               '转文本', '转字符串', '转串', '是实例', '是否实例', '是类实例',
               '取类型', '获取类型', '类型名'}
    sys_kw = {'timestamp', 'getenv', 'get_env', 'setenv', 'set_env',
              'getcwd', 'cwd', 'chdir', 'cd', 'system', 'exec',
              'exit', 'argv', 'args',
              '时间戳', '时间', '环境变量', '设置环境变量', '当前目录',
              '切换目录', '执行命令', '退出程序', '退出', '参数列表'}
    null_kw = {'is_null', 'null?', 'null_coalesce', '??', 'safe_get', '?.',
               '是空', '空合并', '安全获取'}

    if name in socket_kw: return 'Socket'
    if name in poller_kw: return 'Poller'
    if name in eventloop_kw: return 'EventLoop'
    if name in tls_kw: return 'TLS'
    if name in io_kw: return 'IO'
    if name in file_kw: return 'File'
    if name in math_kw: return 'Math'
    if name in string_kw: return 'String'
    if name in list_kw: return 'List'
    if name in dict_kw: return 'Dict'
    if name in type_kw: return 'Type'
    if name in sys_kw: return 'System'
    if name in null_kw: return 'NullSafety'
    return 'Other'

def find_runtime_symbol(name):
    m = {
        '输出': 'dv_println', '打印': 'dv_println', '输入': 'dv_input',
        '时间戳': 'dv_timestamp', '时间': 'dv_timestamp',
        '创建socket': 'dv_socket_create', 'socket_create': 'dv_socket_create',
        '连接socket': 'dv_socket_connect', 'socket_connect': 'dv_socket_connect',
        '发送socket': 'dv_socket_send', 'socket_send': 'dv_socket_send',
        '接收socket': 'dv_socket_recv', 'socket_recv': 'dv_socket_recv',
        '关闭socket': 'dv_socket_close', 'socket_close': 'dv_socket_close',
        'socket错误': 'dv_socket_last_error', 'socket_last_error': 'dv_socket_last_error',
        'socket错误码': 'dv_socket_last_error_code', 'socket_last_error_code': 'dv_socket_last_error_code',
        '创建poller': 'dv_poller_create', 'poller_create': 'dv_poller_create',
        '销毁poller': 'dv_poller_destroy', 'poller_destroy': 'dv_poller_destroy',
        '注册poller': 'dv_poller_register', 'poller_register': 'dv_poller_register',
        'poller_wait': 'dv_poller_wait',
        'poller错误': 'dv_poller_last_error', 'poller_last_error': 'dv_poller_last_error',
        'poller后端': 'dv_poller_backend', 'poller_backend': 'dv_poller_backend',
        'poller计数': 'dv_poller_count', 'poller_count': 'dv_poller_count',
        '运行事件循环': 'dv_scheduler_run_event_loop', 'run_event_loop': 'dv_scheduler_run_event_loop',
        '睡眠': 'dv_coro_sleep', 'sleep': 'dv_coro_sleep',
        'await_io': 'dv_coro_await_io',
        '包装tls': 'dv_tls_wrap', 'tls_wrap': 'dv_tls_wrap',
        '握手tls': 'dv_tls_handshake', 'tls_handshake': 'dv_tls_handshake',
        '等待事件tls': 'dv_tls_want_event', 'tls_want_event': 'dv_tls_want_event',
        '就绪tls': 'dv_tls_is_ready', 'tls_is_ready': 'dv_tls_is_ready',
        '冲刷tls': 'dv_tls_flush_public', 'tls_flush': 'dv_tls_flush_public',
        '发送tls': 'dv_tls_send', 'tls_send': 'dv_tls_send',
        '发送tls长度': 'dv_tls_send_n', 'tls_send_n': 'dv_tls_send_n',
        '接收tls': 'dv_tls_recv', 'tls_recv': 'dv_tls_recv',
        '接收状态tls': 'dv_tls_recv_status', 'tls_recv_status': 'dv_tls_recv_status',
        '释放tls': 'dv_tls_free', 'tls_free': 'dv_tls_free',
        '校验tls': 'dv_tls_set_verify', 'tls_set_verify': 'dv_tls_set_verify',
        '信任证书tls': 'dv_tls_add_trusted_cert_file', 'tls_add_trusted_cert': 'dv_tls_add_trusted_cert_file',
        '错误tls': 'dv_tls_last_error', 'tls_last_error': 'dv_tls_last_error',
    }
    return m.get(name)

# --- Build JSON ---

result = {
    "schema_version": "1.0",
    "snapshot_date": "2026-08-24",
    "baseline_commit": "4250f1fc",
    "description": "光明语言原生腿（LLVM typed backend）能力清单 -- 机读数据，由 B7 维护，E7 门禁消费",
    "tables": {}
}

# Table 1: Statement nodes
stmt_desc = {
    'VariableDeclaration': '设 X 为 值。',
    'Assignment': 'X 为 值。（含属性/成员赋值）',
    'SelfAssignment': '己.x 为 ...',
    'CompoundAssignment': '+= 等复合赋值',
    'IfStatement': '如果 ...',
    'ForeachStatement': '遍历 ... 于 ...',
    'WhileStatement': '当 ...',
    'ReturnStatement': '返回 ...',
    'BreakStatement': '循环跳转 break',
    'ContinueStatement': '循环跳转 continue',
    'PrintStatement': '打印 ...',
    'TryStatement': '异常 try/catch',
    'ThrowStatement': '抛出 throw',
    'ExpressionStatement': '表达式语句',
    'ImportStatement': '当 no-op 处理',
    'AsyncScope': '异步 作用域',
}
result["tables"]["statement_nodes"] = {
    "description": "原生腿 _gen_statement 分派链支持的语句节点",
    "evidence_method": "_gen_statement",
    "evidence_file": "src/llvm/codegen_typed.py",
    "count": len(stmt_types),
    "entries": [
        {
            "name": t,
            "supported": True,
            "evidence": "src/llvm/codegen_typed.py (isinstance in _gen_statement)",
            "description": stmt_desc.get(t, "")
        }
        for t in sorted(stmt_types)
    ]
}

# Table 2: Expression nodes
expr_desc = {
    'NumberLiteral': '数字字面量',
    'StringLiteral': '字符串字面量',
    'BooleanLiteral': '布尔字面量',
    'NullLiteral': '空值字面量',
    'Identifier': '变量引用',
    'BinaryOp': '二元运算',
    'UnaryOp': '一元运算',
    'FunctionCall': '函数调用',
    'ParagraphCall': '段落调用',
    'IndexAccess': 'X[k] 索引访问（A9-S2 起含切片 X[a:b]，拦截 FunctionCall(\'slice\')）',
    'ListLiteral': '[1, 2] 列表字面量',
    'DictLiteral': '{键: 值} 字典字面量 (C3-2 新增)',
    'StringInterpolation': 'f"..." 字符串插值 (C3-2 新增)',
    'ConditionalExpression': '条件表达式',
    'PropertyAccess': '成员访问',
    'ClassInstantiation': '类实例化',
    'NewExpression': 'new 表达式',
    'AwaitExpression': '等待 ...',
    'ExpressionStatement': '表达式语句（适配层揭穿）',
    'ListComprehension': '[表达式 遍历 变量 之 列表 若 条件] 列表推导 (A9-S2 新增)',
}
result["tables"]["expression_nodes"] = {
    "description": "原生腿 _gen_expression 分派链支持的表达式节点",
    "evidence_method": "_gen_expression",
    "evidence_file": "src/llvm/codegen_typed.py",
    "count": len(expr_types),
    "entries": [
        {
            "name": t,
            "supported": True,
            "evidence": "src/llvm/codegen_typed.py (isinstance in _gen_expression)",
            "description": expr_desc.get(t, "")
        }
        for t in sorted(expr_types)
    ]
}

# Table 3: Builtin functions
builtin_entries = []
for name in sorted(builtins.keys()):
    line = builtins[name]
    cat = categorize_builtin(name)
    rt_sym = find_runtime_symbol(name)
    entry = {
        "name": name,
        "evidence": f"src/llvm/codegen_typed.py:{line}",
        "category": cat,
    }
    if rt_sym:
        entry["runtime_symbol"] = rt_sym
    builtin_entries.append(entry)

result["tables"]["builtin_functions"] = {
    "description": "原生腿 _gen_typed_builtin 分派链注册的内置函数名（含中英文别名）",
    "evidence_method": "_gen_typed_builtin",
    "evidence_file": "src/llvm/codegen_typed.py",
    "count": len(builtin_entries),
    "entries": builtin_entries
}

# Table 4: Runtime export symbols
rt_entries = []
for sym in sorted(runtime_symbols.keys()):
    info = runtime_symbols[sym]
    if 'socket' in sym: cat = 'Socket'
    elif 'poller' in sym: cat = 'Poller'
    elif 'coro' in sym or 'scheduler' in sym or 'future' in sym: cat = 'Coroutine'
    elif 'tls' in sym: cat = 'TLS'
    elif 'try' in sym or 'throw' in sym or 'exception' in sym: cat = 'Exception'
    elif 'class' in sym or 'method' in sym or 'interface' in sym: cat = 'Class'
    elif 'list' in sym: cat = 'List'
    elif 'dict' in sym: cat = 'Dict'
    elif 'str' in sym or 'concat' in sym: cat = 'String'
    elif any(x in sym for x in ['sin','cos','tan','sqrt','abs','pow','floor','ceil','mod','log','exp','round','trunc','sign','hypot','degree','radian','min','max','gcd','lcm','asin','acos','atan']): cat = 'Math'
    elif any(x in sym for x in ['print','input']): cat = 'IO'
    elif any(x in sym for x in ['file','read','write','append','delete','list_dir','mkdir','rmdir','rename','copy','is_file','is_dir']): cat = 'File'
    elif any(x in sym for x in ['int','float','str','bool','null','to_']): cat = 'Type'
    elif any(x in sym for x in ['getenv','setenv','getcwd','chdir','system','exit','init_args','get_args','platform_sleep']): cat = 'System'
    elif any(x in sym for x in ['stack','format_time','timestamp']): cat = 'System'
    elif any(x in sym for x in ['md5','sha','base64']): cat = 'Hash'
    elif 'setjmp' in sym: cat = 'Platform'
    else: cat = 'Other'

    rt_line_val = info.get('rt_line', '?')
    if rt_line_val == 'C-library':
        ev_define = "C library (not in runtime_typed.c)"
    else:
        ev_define = f"src/llvm/runtime_typed.c:{rt_line_val}"

    entry = {
        "name": sym,
        "evidence_declare": f"src/llvm/codegen_typed.py:{info['cg_line']}",
        "evidence_define": ev_define,
        "category": cat,
    }
    rt_entries.append(entry)

result["tables"]["runtime_symbols"] = {
    "description": "原生腿外部符号声明（_declare_typed_runtime）与 runtime_typed.c 定义",
    "evidence_method": "_declare_typed_runtime",
    "evidence_file": "src/llvm/codegen_typed.py",
    "count": len(rt_entries),
    "entries": rt_entries
}

# Platform notes
result["platform_notes"] = {
    "TLS": {
        "windows": "Windows Schannel 后端，真实现（runtime_typed.c:5111-5745）",
        "posix": "显式降级：dv_tls_* 返回 DV_TLS_ERROR (-1) 并设置 g_tls_error 错误文本（runtime_typed.c:5747-5778），dv_tls_backend() 返回 none",
        "posix_ruling": "B7 首日裁决取显式降级 -- POSIX 不支持 TLS，返回明确错误而非静默失败。改选引 OpenSSL/mbedTLS 必须先拿用户裁决（依赖红线）"
    },
    "Poller": {
        "windows": "WSAPoll（runtime_typed.c:4550-4552）",
        "posix": "poll（runtime_typed.c:4553-4555）",
        "fallback": "select（DV_POLLER_FORCE_SELECT 编译期宏，runtime_typed.c:4547-4549）"
    },
    "Socket": {
        "windows": "Winsock2（WSAStartup, runtime_typed.c:4372-4389）",
        "posix": "BSD socket（同一段代码 #ifdef 分支）"
    },
    "Coroutine": {
        "max_coroutines": 4096,
        "evidence": "DV_MAX_COROUTINES 4096 (runtime_typed.c:4047)",
        "implementation": "单线程 Duff device，codegen 发 IR（入口 switch codegen_typed.py:3459-3475，挂起点 :3634-3651）",
        "threads": "无 pthread（单线程）"
    }
}

out_path = os.path.join(BASE, 'docs', '\u539f\u751f\u817f\u80fd\u529b\u6e05\u5355.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"JSON written to {out_path}")
print(f"  statement_nodes: {len(stmt_types)} entries")
print(f"  expression_nodes: {len(expr_types)} entries")
print(f"  builtin_functions: {len(builtin_entries)} entries")
print(f"  runtime_symbols: {len(rt_entries)} entries")
total = len(stmt_types) + len(expr_types) + len(builtin_entries) + len(rt_entries)
print(f"  Total: {total} entries")
