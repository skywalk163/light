# 由光明编译器生成
# 源文件: 光明代码

import sys
import os

try:
    import importlib.util
except ImportError:
    importlib = None

# 解析 stdlib 路径（依次尝试多种可能）
_light_stdlib = None
for _try_path in [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stdlib'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'stdlib'),
    os.path.join(os.getcwd(), 'stdlib'),
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'stdlib')),
]:
    if os.path.isdir(_try_path):
        _light_stdlib = _try_path
        break

if _light_stdlib and _light_stdlib not in sys.path:
    sys.path.insert(0, _light_stdlib)

if importlib:
    try:
        _light_builtin_path = os.path.join(_light_stdlib, 'builtins.py')
        if os.path.isfile(_light_builtin_path):
            spec = importlib.util.spec_from_file_location('light_builtins', _light_builtin_path)
            _light_builtin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_light_builtin)
        else:
            raise ImportError()
    except:
        import types
        _light_builtin = types.ModuleType('_light_builtin')
        _light_builtin.读取文件 = lambda path: open(path, 'r', encoding='utf-8').read()
        _light_builtin.写入文件 = lambda path, content: open(path, 'w', encoding='utf-8').write(content) or None
        _light_builtin.文件存在 = lambda path: __import__('os').path.isfile(path)
        _light_builtin.目录存在 = lambda path: __import__('os').path.isdir(path)
        _light_builtin.打印 = print
        _light_builtin.读取行 = lambda: sys.stdin.readline().rstrip('\r\n')
        _light_builtin.读取N字节 = lambda n: sys.stdin.read(n)
        _light_builtin.写入输出 = lambda t: (sys.stdout.write(t), sys.stdout.flush()) and None
        _light_builtin.打印输出 = lambda t: print(t, flush=True)
        _light_builtin.刷新输出 = lambda: sys.stdout.flush()
        _light_builtin.写入错误 = lambda t: (sys.stderr.write(t), sys.stderr.flush()) and None
        _light_builtin.打印错误 = lambda t: print(t, file=sys.stderr, flush=True)
        _light_builtin.解析JSON = lambda t: __import__('json').loads(t)
        _light_builtin.序列化JSON = lambda v, i=None: (__import__('json').dumps(v, ensure_ascii=False, indent=i) if i is not None else __import__('json').dumps(v, ensure_ascii=False))
        _light_builtin.美化JSON = lambda v: __import__('json').dumps(v, ensure_ascii=False, indent=2)
        _light_builtin.转字符串 = str
        _light_builtin.列表创建 = list
        _light_builtin.列表长度 = len
        _light_builtin.列 = lambda *args: list(args)
        _light_builtin.列表追加 = lambda lst, item: lst.append(item)
        _light_builtin.列表包含 = lambda lst, item: item in lst
        _light_builtin.字符串长度 = len
        _light_builtin.字典创建 = dict
        _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
        _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
        _light_builtin.字典键列表 = lambda d: list(d.keys())
        _light_builtin.字典包含键 = lambda d, k: k in d
else:
    import types
    _light_builtin = types.ModuleType('_light_builtin')
    _light_builtin.打印 = print
    _light_builtin.读取行 = lambda: sys.stdin.readline().rstrip('\n')
    _light_builtin.读取N字节 = lambda n: sys.stdin.read(n)
    _light_builtin.写入输出 = lambda t: (sys.stdout.write(t), sys.stdout.flush()) and None
    _light_builtin.打印输出 = lambda t: print(t, flush=True)
    _light_builtin.刷新输出 = lambda: sys.stdout.flush()
    _light_builtin.写入错误 = lambda t: (sys.stderr.write(t), sys.stderr.flush()) and None
    _light_builtin.打印错误 = lambda t: print(t, file=sys.stderr, flush=True)
    _light_builtin.解析JSON = lambda t: __import__('json').loads(t)
    _light_builtin.序列化JSON = lambda v, i=None: (__import__('json').dumps(v, ensure_ascii=False, indent=i) if i is not None else __import__('json').dumps(v, ensure_ascii=False))
    _light_builtin.美化JSON = lambda v: __import__('json').dumps(v, ensure_ascii=False, indent=2)
    _light_builtin.转字符串 = str
    _light_builtin.列表创建 = list
    _light_builtin.列表长度 = len
    _light_builtin.列 = lambda *args: list(args)
    _light_builtin.列表追加 = lambda lst, item: lst.append(item)
    _light_builtin.列表包含 = lambda lst, item: item in lst
    _light_builtin.字符串长度 = len
    _light_builtin.字典创建 = dict
    _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
    _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
    _light_builtin.字典键列表 = lambda d: list(d.keys())
    _light_builtin.字典包含键 = lambda d, k: k in d

# 可空类型解包辅助函数
def _light_unwrap(_x):
    assert _x is not None, "尝试解包空值"
    return _x

# =============================================================================
# 中文关键字文档字典（用于悬停和补全）
# =============================================================================
_light_kw_docs = {
    '设': '**用法**: `设 变量名 = 值。`\n\n**说明**: 声明变量并赋值。',
    '若': '**用法**: `若 条件 则：\n    代码块\n否：\n    代码块`\n\n**说明**: 条件判断。',
    '否': '**用法**: `否：\n    代码块`\n\n**说明**: else 分支。',
    '当': '**用法**: `当 条件：\n    代码块`\n\n**说明**: 条件循环。',
    '遍': '**用法**: `遍 变量 之 列表：\n    代码块`\n\n**说明**: 遍历循环。',
    '段': '**用法**: `段 函数名(参数)：\n    代码块`\n\n**说明**: 函数定义。',
    '返': '**用法**: `返 表达式。`\n\n**说明**: 返回语句。',
    '跳': '**用法**: `跳。`\n\n**说明**: 跳出循环。',
    '过': '**用法**: `过。`\n\n**说明**: 跳过本次迭代。',
    '类': '**用法**: `类 类名：\n    代码块`\n\n**说明**: 类定义。',
    '承': '**用法**: `类 子类 承 父类：\n    代码块`\n\n**说明**: 类继承。',
    '接': '**用法**: `接 接口名：\n    代码块`\n\n**说明**: 接口定义。',
    '配': '**用法**: `配 表达式：\n    情况 模式：\n        代码块`\n\n**说明**: 模式匹配。',
    '试': '**用法**: `试：\n    代码块\n捕 异常：\n    代码块\n终：\n    代码块`\n\n**说明**: 异常处理。',
    '捕': '**用法**: `捕 异常类型：\n    代码块`\n\n**说明**: 捕获异常。',
    '抛': '**用法**: `抛 异常对象。`\n\n**说明**: 抛出异常。',
    '终': '**用法**: `终：\n    代码块`\n\n**说明**: 最终执行块。',
    '导': '**用法**: `导 模块名。`\n\n**说明**: 导入模块。',
    '出': '**用法**: `出 模块名。`\n\n**说明**: 导出模块。',
    '自': '**用法**: `自.属性` 或 `自.方法()`\n\n**说明**: 自引用 (self)。',
    '之': '**用法**: `对象之属性`\n\n**说明**: 属性提取符。',
    '并': '**用法**: `数据 并 处理函数`\n\n**说明**: 管道连接符。',
    '是': '**用法**: `甲 是 乙`\n\n**说明**: 判断相等。',
    '且': '**说明**: 逻辑与 (AND)。',
    '或': '**说明**: 逻辑或 (OR)。',
    '非': '**说明**: 逻辑非 (NOT)。',
    '真': '**说明**: 布尔值真 (True)。',
    '假': '**说明**: 布尔值假 (False)。',
    '空': '**说明**: 空值 (None)。',
    '定义': '**用法**: `定义 变量名 等于 值。`\n\n**说明**: 声明变量（v3.3 兼容语法）。',
    '如果': '**用法**: `如果 条件：\n    代码块\n否则：\n    代码块`\n\n**说明**: 条件判断（v3.3 兼容语法）。',
    '遍历': '**用法**: `遍历 变量 于 列表：\n    代码块`\n\n**说明**: 遍历循环（v3.3 兼容语法）。',
    '段落': '**用法**: `段落 函数名 接收 参数：\n    代码块`\n\n**说明**: 函数定义（v3.3 兼容语法）。',
    '返回': '**用法**: `返回 表达式。`\n\n**说明**: 返回语句（v3.3 兼容语法）。',
    '打印': '**用法**: `打印 值1, 值2, ...`\n\n**说明**: 向控制台输出内容。',
    '输出': '**用法**: `输出 值1, 值2, ...`\n\n**说明**: 向控制台输出内容。',
    '加': '**动词**: `加`\n\n**说明**: 加法运算，也用于字符串连接。',
    '减': '**动词**: `减`\n\n**说明**: 减法运算。',
    '乘': '**动词**: `乘`\n\n**说明**: 乘法运算。',
    '除': '**动词**: `除`\n\n**说明**: 除法运算。',
    '等于': '**动词**: `等于`\n\n**说明**: 赋值运算。',
    '大于': '**动词**: `大于`\n\n**说明**: 大于比较。',
    '小于': '**动词**: `小于`\n\n**说明**: 小于比较。',
    '转串': '**动词**: `转串`\n\n**说明**: 将值转换为字符串。',
    '转整数': '**动词**: `转整数`\n\n**说明**: 将字符串转换为整数。',
    '转浮点': '**动词**: `转浮点`\n\n**说明**: 将字符串转换为浮点数。',
}

# 中文错误消息翻译
_light_error_zh = {
    'unexpected token': '意外的标记，请检查语法',
    'invalid syntax': '语法无效',
    'expected expression': '需要表达式',
    'missing colon': '缺少冒号「：」',
    'missing period': '缺少句号「。」',
    'unclosed string': '字符串未闭合',
    'division by zero': '除数不能为零',
    'type mismatch': '类型不匹配',
    'name not defined': '名称未定义，请先使用「设」或「定义」声明变量',
    'undefined': '未定义',
    'indent': '缩进错误',
    'module': '模块错误',
    'syntax': '语法错误',
    'keyword': '关键字错误',
    'argument': '参数错误',
    'import': '导入错误',
    'recursion': '递归错误',
    'index': '索引错误',
    'key': '键错误',
    'attribute': '属性错误',
}

def _translate_error(msg):
    """翻译错误消息为中文"""
    lower = msg.lower()
    for eng, zh in _light_error_zh.items():
        if eng in lower:
            return zh
    return msg

def 读取LSP消息():
    content_length = -1
    继续读取 = 1
    while (继续读取 == 1):
        行 = _light_builtin.读取行()
        if (行 == ""):
            继续读取 = 0
        if (content_length == -1):
            部分 = _light_builtin.分割字符串(行, ":")
            if (_light_builtin.列表长度(部分) > 1):
                头 = _light_builtin.列表获取(部分, 0)
                if (头 == "Content-Length"):
                    值字符串 = _light_builtin.列表获取(部分, 1)
                    content_length = _light_builtin.转整数(_light_builtin.去除空白(值字符串))
    if (content_length > 0):
        body = _light_builtin.读取N字节(content_length)
        消息 = _light_builtin.解析JSON(body)
        return 消息
    else:
        return None

def 发送LSP响应(id, result):
    响应字典 = _light_builtin.字典创建()
    _light_builtin.字典设置(响应字典, "jsonrpc", "2.0")
    _light_builtin.字典设置(响应字典, "id", id)
    _light_builtin.字典设置(响应字典, "result", result)
    body = _light_builtin.序列化JSON(响应字典)
    长度 = _light_builtin.字符串长度(body)
    header = (("Content-Length: " + _light_builtin.转字符串(长度)) + "\r\n\r\n")
    _light_builtin.写入输出(header)
    _light_builtin.写入输出(body)
    _light_builtin.刷新输出()

def 获取诊断(文本):
    结果 = _light_builtin.列表创建()
    行号 = 0
    行列表 = _light_builtin.分割字符串(文本, "\n")
    索引 = 0
    while (索引 < _light_builtin.列表长度(行列表)):
        本行内容 = _light_builtin.列表获取(行列表, 索引)
        字符索引 = 0
        while (字符索引 < _light_builtin.字符串长度(本行内容)):
            ch = _light_builtin.字符串获取(本行内容, 字符索引)
            if (ch == "?"):
                诊断 = _light_builtin.字典创建()
                _light_builtin.字典设置(诊断, "range", _light_builtin.字典创建())
                _light_builtin.字典设置(_light_builtin.字典获取(诊断, "range"), "start", _light_builtin.字典创建())
                _light_builtin.字典设置(_light_builtin.字典获取(_light_builtin.字典获取(诊断, "range"), "start"), "line", 索引)
                _light_builtin.字典设置(_light_builtin.字典获取(_light_builtin.字典获取(诊断, "range"), "start"), "character", 字符索引)
                _light_builtin.字典设置(_light_builtin.字典获取(诊断, "range"), "end", _light_builtin.字典创建())
                _light_builtin.字典设置(_light_builtin.字典获取(_light_builtin.字典获取(诊断, "range"), "end"), "line", 索引)
                _light_builtin.字典设置(_light_builtin.字典获取(_light_builtin.字典获取(诊断, "range"), "end"), "character", (字符索引 + 1))
                _light_builtin.字典设置(诊断, "severity", 2)
                _light_builtin.字典设置(诊断, "source", "light-lsp")
                _light_builtin.字典设置(诊断, "message", "发现可疑字符")
                _light_builtin.列表追加(结果, 诊断)
            字符索引 = (字符索引 + 1)
        索引 = (索引 + 1)
    return 结果

def 获取补全(行, 字符位置):
    结果 = _light_builtin.列表创建()
    关键词列表 = _light_builtin.列表创建()
    _light_builtin.列表追加(关键词列表, "设")
    _light_builtin.列表追加(关键词列表, "若")
    _light_builtin.列表追加(关键词列表, "否")
    _light_builtin.列表追加(关键词列表, "当")
    _light_builtin.列表追加(关键词列表, "遍")
    _light_builtin.列表追加(关键词列表, "段")
    _light_builtin.列表追加(关键词列表, "返")
    _light_builtin.列表追加(关键词列表, "跳")
    _light_builtin.列表追加(关键词列表, "过")
    _light_builtin.列表追加(关键词列表, "类")
    _light_builtin.列表追加(关键词列表, "承")
    _light_builtin.列表追加(关键词列表, "接")
    _light_builtin.列表追加(关键词列表, "配")
    _light_builtin.列表追加(关键词列表, "试")
    _light_builtin.列表追加(关键词列表, "捕")
    _light_builtin.列表追加(关键词列表, "抛")
    _light_builtin.列表追加(关键词列表, "终")
    _light_builtin.列表追加(关键词列表, "导")
    _light_builtin.列表追加(关键词列表, "出")
    _light_builtin.列表追加(关键词列表, "自")
    _light_builtin.列表追加(关键词列表, "之")
    _light_builtin.列表追加(关键词列表, "并")
    _light_builtin.列表追加(关键词列表, "且")
    _light_builtin.列表追加(关键词列表, "或")
    _light_builtin.列表追加(关键词列表, "非")
    _light_builtin.列表追加(关键词列表, "真")
    _light_builtin.列表追加(关键词列表, "假")
    _light_builtin.列表追加(关键词列表, "空")
    _light_builtin.列表追加(关键词列表, "定义")
    _light_builtin.列表追加(关键词列表, "如果")
    _light_builtin.列表追加(关键词列表, "那么")
    _light_builtin.列表追加(关键词列表, "否则")
    _light_builtin.列表追加(关键词列表, "否则若")
    _light_builtin.列表追加(关键词列表, "遍历")
    _light_builtin.列表追加(关键词列表, "跳出")
    _light_builtin.列表追加(关键词列表, "跳过")
    _light_builtin.列表追加(关键词列表, "返回")
    _light_builtin.列表追加(关键词列表, "段落")
    _light_builtin.列表追加(关键词列表, "函数")
    _light_builtin.列表追加(关键词列表, "导入")
    _light_builtin.列表追加(关键词列表, "导出")
    _light_builtin.列表追加(关键词列表, "从")
    _light_builtin.列表追加(关键词列表, "打印")
    _light_builtin.列表追加(关键词列表, "输出")
    _light_builtin.列表追加(关键词列表, "打印输出")
    _light_builtin.列表追加(关键词列表, "读取行")
    _light_builtin.列表追加(关键词列表, "字典创建")
    _light_builtin.列表追加(关键词列表, "列表创建")
    _light_builtin.列表追加(关键词列表, "字典设置")
    _light_builtin.列表追加(关键词列表, "字典获取")
    _light_builtin.列表追加(关键词列表, "列表追加")
    _light_builtin.列表追加(关键词列表, "解析JSON")
    _light_builtin.列表追加(关键词列表, "序列化JSON")
    _light_builtin.列表追加(关键词列表, "加")
    _light_builtin.列表追加(关键词列表, "减")
    _light_builtin.列表追加(关键词列表, "乘")
    _light_builtin.列表追加(关键词列表, "除")
    _light_builtin.列表追加(关键词列表, "等于")
    _light_builtin.列表追加(关键词列表, "大于")
    _light_builtin.列表追加(关键词列表, "小于")
    _light_builtin.列表追加(关键词列表, "转串")
    _light_builtin.列表追加(关键词列表, "转整数")
    _light_builtin.列表追加(关键词列表, "转浮点")
    _light_builtin.列表追加(关键词列表, "新建")
    _light_builtin.列表追加(关键词列表, "尝试")
    _light_builtin.列表追加(关键词列表, "捕获")
    _light_builtin.列表追加(关键词列表, "抛出")
    _light_builtin.列表追加(关键词列表, "最终")
    _light_builtin.列表追加(关键词列表, "匹配")
    _light_builtin.列表追加(关键词列表, "情况")
    _light_builtin.列表追加(关键词列表, "接口")
    _light_builtin.列表追加(关键词列表, "异步")
    _light_builtin.列表追加(关键词列表, "等待")
    i = 0
    while (i < _light_builtin.列表长度(关键词列表)):
        关键词 = _light_builtin.列表获取(关键词列表, i)
        项 = _light_builtin.字典创建()
        _light_builtin.字典设置(项, "label", 关键词)
        _light_builtin.字典设置(项, "kind", 14)
        # 添加中文文档
        文档 = _light_kw_docs.get(关键词, "")
        if 文档:
            _light_builtin.字典设置(项, "documentation", 文档)
        _light_builtin.列表追加(结果, 项)
        i = (i + 1)
    return 结果

def 主():
    _light_builtin.打印错误("光明 LSP 服务器启动（支持中文补全和悬停提示）")
    运行中 = 1
    while (运行中 == 1):
        请求 = 读取LSP消息()
        if (请求 == None):
            _light_builtin.打印错误("收到空消息，退出")
            运行中 = 0
        else:
            方法 = _light_builtin.字典获取(请求, "method")
            请求id = _light_builtin.字典获取(请求, "id")
            _light_builtin.打印错误(("收到方法: " + _light_builtin.转字符串(方法)))
            if (方法 == "initialize"):
                能力 = _light_builtin.字典创建()
                _light_builtin.字典设置(能力, "textDocumentSync", 1)
                _light_builtin.字典设置(能力, "completionProvider", _light_builtin.字典创建())
                _light_builtin.字典设置(_light_builtin.字典获取(能力, "completionProvider"), "triggerCharacters", _light_builtin.列表创建())
                _light_builtin.字典设置(能力, "hoverProvider", True)
                服务器信息 = _light_builtin.字典创建()
                _light_builtin.字典设置(服务器信息, "name", "light-lsp")
                _light_builtin.字典设置(服务器信息, "version", "2.0.0")
                初始化结果 = _light_builtin.字典创建()
                _light_builtin.字典设置(初始化结果, "capabilities", 能力)
                _light_builtin.字典设置(初始化结果, "serverInfo", 服务器信息)
                发送LSP响应(请求id, 初始化结果)
            else:
                if (方法 == "textDocument/didChange"):
                    文档 = _light_builtin.字典获取(请求, "params")
                    内容 = _light_builtin.字典获取(_light_builtin.字典获取(文档, "contentChanges"), 0)
                    文本 = _light_builtin.字典获取(内容, "text")
                    诊断列表 = 获取诊断(文本)
                    # 翻译诊断消息为中文
                    翻译后列表 = _light_builtin.列表创建()
                    di = 0
                    while (di < _light_builtin.列表长度(诊断列表)):
                        诊断 = _light_builtin.列表获取(诊断列表, di)
                        原消息 = _light_builtin.字典获取(诊断, "message")
                        翻译消息 = _translate_error(原消息)
                        _light_builtin.字典设置(诊断, "message", 翻译消息)
                        _light_builtin.列表追加(翻译后列表, 诊断)
                        di = (di + 1)
                    pub_params = _light_builtin.字典创建()
                    uri = _light_builtin.字典获取(_light_builtin.字典获取(文档, "textDocument"), "uri")
                    _light_builtin.字典设置(pub_params, "uri", uri)
                    _light_builtin.字典设置(pub_params, "diagnostics", 翻译后列表)
                    完整通知 = _light_builtin.字典创建()
                    _light_builtin.字典设置(完整通知, "method", "textDocument/publishDiagnostics")
                    _light_builtin.字典设置(完整通知, "params", pub_params)
                    body = _light_builtin.序列化JSON(完整通知)
                    长度 = _light_builtin.字符串长度(body)
                    header = (("Content-Length: " + _light_builtin.转字符串(长度)) + "\r\n\r\n")
                    _light_builtin.写入输出(header)
                    _light_builtin.写入输出(body)
                    _light_builtin.刷新输出()
                else:
                    if (方法 == "textDocument/didOpen"):
                        文档 = _light_builtin.字典获取(请求, "params")
                        doc = _light_builtin.字典获取(文档, "textDocument")
                        文本 = _light_builtin.字典获取(doc, "text")
                        诊断列表 = 获取诊断(文本)
                        # 翻译诊断消息为中文
                        翻译后列表 = _light_builtin.列表创建()
                        di = 0
                        while (di < _light_builtin.列表长度(诊断列表)):
                            诊断 = _light_builtin.列表获取(诊断列表, di)
                            原消息 = _light_builtin.字典获取(诊断, "message")
                            翻译消息 = _translate_error(原消息)
                            _light_builtin.字典设置(诊断, "message", 翻译消息)
                            _light_builtin.列表追加(翻译后列表, 诊断)
                            di = (di + 1)
                        pub_params = _light_builtin.字典创建()
                        _light_builtin.字典设置(pub_params, "uri", _light_builtin.字典获取(doc, "uri"))
                        _light_builtin.字典设置(pub_params, "diagnostics", 翻译后列表)
                        完整通知 = _light_builtin.字典创建()
                        _light_builtin.字典设置(完整通知, "method", "textDocument/publishDiagnostics")
                        _light_builtin.字典设置(完整通知, "params", pub_params)
                        body = _light_builtin.序列化JSON(完整通知)
                        长度 = _light_builtin.字符串长度(body)
                        header = (("Content-Length: " + _light_builtin.转字符串(长度)) + "\r\n\r\n")
                        _light_builtin.写入输出(header)
                        _light_builtin.写入输出(body)
                        _light_builtin.刷新输出()
                    else:
                        if (方法 == "textDocument/completion"):
                            补全列表 = 获取补全("", 0)
                            发送LSP响应(请求id, 补全列表)
                        else:
                            if (方法 == "textDocument/hover"):
                                # 处理悬停请求
                                参数 = _light_builtin.字典获取(请求, "params", _light_builtin.字典创建())
                                文本文档 = _light_builtin.字典获取(参数, "textDocument", _light_builtin.字典创建())
                                位置 = _light_builtin.字典获取(参数, "position", _light_builtin.字典创建())
                                悬停结果 = _light_builtin.字典创建()
                                _light_builtin.字典设置(悬停结果, "contents", _light_builtin.字典创建())
                                _light_builtin.字典设置(_light_builtin.字典获取(悬停结果, "contents"), "kind", "markdown")
                                _light_builtin.字典设置(_light_builtin.字典获取(悬停结果, "contents"), "value", "光明 LSP 服务器 v2.0.0\n\n支持中文关键字补全和中文文档悬停提示。")
                                发送LSP响应(请求id, 悬停结果)
                            else:
                                if (方法 == "shutdown"):
                                    发送LSP响应(请求id, None)
                                    _light_builtin.打印错误("收到 shutdown，准备退出")
                                else:
                                    if (方法 == "exit"):
                                        运行中 = 0
                                        _light_builtin.打印错误("LSP 服务器退出")
                                    else:
                                        默认结果 = _light_builtin.字典创建()
                                        _light_builtin.字典设置(默认结果, "status", "ok")
                                        _light_builtin.字典设置(默认结果, "method", 方法)
                                        发送LSP响应(请求id, 默认结果)


主()
