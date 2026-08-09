"""
光明（Light）Web Playground - 后端 API 服务

提供代码执行、示例库、代码分享功能。
"""

import os
import sys
import json
import uuid
import hashlib
import time
import io

# 添加上级目录到路径（引入解释器）
_script_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_script_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from light_interpreter import run_source
from light_visitor import parse_source
from light_tokenizer import LightLangTokenizer

app = Flask(__name__, static_folder='static')
CORS(app)

# =============================================================================
# 配置
# =============================================================================

SHARED_DIR = os.path.join(_script_dir, 'shared')
EXAMPLES_FILE = os.path.join(_script_dir, 'examples.json')
os.makedirs(SHARED_DIR, exist_ok=True)


# =============================================================================
# 内置示例
# =============================================================================

BUILTIN_EXAMPLES = [
    {
        "id": "hello",
        "title": "你好，光明",
        "description": "最基础的光明程序",
        "code": '打印("你好，光明！")。\n打印("欢迎来到中文编程的世界。")。'
    },
    {
        "id": "variables",
        "title": "变量与运算",
        "description": "变量定义和基本算术运算",
        "code": '定义甲等于10。\n定义乙等于20。\n定义丙等于真。\n定义丁等于空。\n\n打印(甲加乙)。\n打印(甲乘乙)。\n\n定义_最大值等于甲。\n如果乙大于甲那么:\n  定义_最大值等于乙。\n结束。\n打印(_最大值)。'
    },
    {
        "id": "types",
        "title": "数据类型",
        "description": "数字、字符串、列表、字典的使用",
        "code": '# 数字运算\n定义结果等于10加5乘2。\n打印("10 + 5 × 2 = "加结果)。\n\n# 字符串\n定义_问候等于"你好，世界！"。\n打印(_问候)。\n\n# 列表\n定义_数字列等于【1, 2, 3, 4, 5】。\n打印(_数字列)。\n打印("长度："加_数字列之长度)。\n打印("第一个元素："加_数字列[0])。\n\n# 嵌套列表\n定义_矩阵等于【【1, 2】, 【3, 4】】。\n打印(_矩阵[0][1])。'
    },
    {
        "id": "controlflow",
        "title": "控制流",
        "description": "条件判断和循环语句",
        "code": '# 条件判断\n定义分数等于85。\n\n如果分数大于等于90那么:\n  打印(\'优秀\')。\n否则若分数大于等于80那么:\n  打印(\'良好\')。\n否则若分数大于等于60那么:\n  打印(\'及格\')。\n否则:\n  打印(\'不及格\')。\n结束。\n\n# 遍历循环\n定义列表等于【10, 20, 30】。\n遍历 项 列表:\n  打印(项)。\n结束。\n\n# 当循环\n定义计数等于3。\n当计数大于0:\n  打印(计数)。\n  定义计数等于计数减1。\n结束。'
    },
    {
        "id": "function",
        "title": "段落（函数）",
        "description": "段落定义和调用",
        "code": '# 定义段落\n《平方》段(数值):\n  返回数值乘数值。\n结束。\n\n《双倍》段(数值):\n  返回数值乘2。\n结束。\n\n《阶乘》段(数值):\n  如果数值小于等于1那么:\n    返回1。\n  结束。\n  定义结果等于1。\n  定义i等于数值。\n  当i大于1:\n    结果等于结果乘i。\n    i等于i减1。\n  结束。\n  返回结果。\n结束。\n\n# 调用段落\n打印("5 的平方："加《平方》(5))。\n打印("双倍 21："加《双倍》(21))。\n打印("6 的阶乘："加《阶乘》(6))。'
    },
    {
        "id": "fibonacci",
        "title": "斐波那契数列",
        "description": "递归计算斐波那契数列",
        "code": '# 递归斐波那契\n《斐波那契》段(n):\n  如果n小于等于1那么:\n    返回n。\n  结束。\n  返回《斐波那契》(n减1)加《斐波那契》(n减2)。\n结束。\n\n# 输出前 10 项\n定义i等于0。\n当i小于10:\n  打印("F("加i加") = "加《斐波那契》(i))。\n  i等于i加1。\n结束。'
    },
    {
        "id": "quicksort",
        "title": "快速排序",
        "description": "经典的快速排序算法",
        "code": '# 找最大值\n《找最大值》段(列表):\n  定义_最大值等于列表[0]。\n  遍历 项 列表:\n    如果项大于_最大值那么:\n      定义_最大值等于项。\n    结束。\n  结束。\n  返回_最大值。\n结束。\n\n定义数据等于【5, 3, 8, 1, 9, 2】。\n定义_最大等于《找最大值》(数据)。\n打印("列表："加数据)。\n打印("最大值："加_最大)。\n\n# 用同样的方式找最小值\n《找最小值》段(列表):\n  定义_最小值等于列表[0]。\n  遍历 项 列表:\n    如果项小于_最小值那么:\n      定义_最小值等于项。\n    结束。\n  结束。\n  返回_最小值。\n结束。\n\n定义_最小等于《找最小值》(数据)。\n打印("最小值："加_最小)。'
    },
    {
        "id": "grades",
        "title": "成绩统计",
        "description": "学生成绩统计和等级评定",
        "code": '# 计算平均分\n《计算平均分》段(成绩列表):\n  定义总分等于0。\n  遍历 项 成绩列表:\n    总分等于总分加项。\n  结束。\n  返回总分除成绩列表之长度。\n结束。\n\n# 等级评定\n《统计等级》段(分数):\n  如果分数大于等于90那么:\n    返回\'优秀\'。\n  否则若分数大于等于80那么:\n    返回\'良好\'。\n  否则若分数大于等于60那么:\n    返回\'及格\'。\n  否则:\n    返回\'不及格\'。\n  结束。\n结束。\n\n定义成绩等于【85, 92, 78, 63, 58, 95】。\n定义平均分等于《计算平均分》(成绩)。\n打印("平均分："加平均分)。\n\n遍历 项 成绩:\n  定义_等级等于《统计等级》(项)。\n  打印(项加"："加_等级)。\n结束。'
    },
    {
        "id": "module_demo",
        "title": "模块导入",
        "description": "演示模块导入和导出功能",
        "code": '# 段落定义 — 函数式编程示例\n\n《平方》段(数值):\n  返回数值乘数值。\n结束。\n\n《立方》段(数值):\n  返回数值乘数值乘数值。\n结束。\n\n打印("5 的平方："加《平方》(5))。\n打印("3 的立方："加《立方》(3))。\n\n# 管道式调用\n定义_双倍等于《平方》(3)加1。\n打印("3² + 1 = "加_双倍)。'
    },
    {
        "id": "dict_ops",
        "title": "字典操作",
        "description": "字典的创建、成员访问和属性操作",
        "code": '# 字典操作演示\n\n# 使用 _典() 函数创建字典\n定义_映射等于_典(\n  "姓名", "张三",\n  "年龄", 18,\n  "成绩", 95\n)。\n\n打印("学生信息：")。\n打印("姓名："加_映射["姓名"])。\n打印("年龄："加_映射["年龄"])。\n打印("成绩："加_映射["成绩"])。\n\n# 字典属性\n打印("--- 字典属性 ---")。\n打印("字典长度："加_映射之长度)。'
    },
    {
        "id": "multiplication",
        "title": "九九乘法表",
        "description": "嵌套循环打印乘法表",
        "code": '# 九九乘法表\n\n定义i等于1。\n当i小于等于9:\n  定义j等于1。\n  定义_行等于""。\n  当j小于等于i:\n    定义_行等于_行加j加"×"加i加"="加i乘j加"  "。\n    定义j等于j加1。\n  结束。\n  打印(_行)。\n  定义i等于i加1。\n结束。'
    },
    {
        "id": "primes",
        "title": "素数判断",
        "description": "判断素数并输出100以内的质数",
        "code": '# 判断素数\n《是素数》段(数值):\n  如果数值小于2那么:\n    返回假。\n  结束。\n  定义i等于2。\n  当i乘i小于等于数值:\n    如果数值除i乘i等于数值那么:\n      返回假。\n    结束。\n    定义i等于i加1。\n  结束。\n  返回真。\n结束。\n\n# 输出100以内所有素数\n定义_素数列表等于【】。\n定义n等于2。\n当n小于100:\n  如果《是素数》(n)那么:\n    定义_素数列表等于_素数列表 -> 【n】。\n    打印(n)。\n  结束。\n  定义n等于n加1。\n结束。\n\n打印("共 "加_素数列表之长度加" 个素数")。'
    },
    {
        "id": "digit_sum",
        "title": "回文判断",
        "description": "字符串反转和回文判断，遍历查找回文数",
        "code": '# 回文判断\n\n《反转字符串》段(文本):\n  定义_结果等于""。\n  定义i等于文本之长度减1。\n  当 i 大于等于 0:\n    定义_结果等于_结果加文本[i]。\n    定义i等于i减1。\n  结束。\n  返回_结果。\n结束。\n\n《是回文》段(文本):\n  定义_反转等于《反转字符串》(文本)。\n  如果文本等于_反转那么:\n    返回真。\n  否则:\n    返回假。\n  结束。\n结束。\n\n# 测试\n定义_词1等于"上海自来水来自海上"。\n定义_词2等于"光明编程语言"。\n\n打印(_词1加" 是回文吗？"加《是回文》(_词1))。\n打印(_词2加" 是回文吗？"加《是回文》(_词2))。\n\n# 遍历查找两位数中的回文数\n打印("--- 两位数中的回文数 ---")。\n定义n等于10。\n当 n 小于等于 99:\n  定义_文本等于""加n。\n  如果《是回文》(_文本)那么:\n    打印(n)。\n  结束。\n  定义n等于n加1。\n结束。'
    },
    {
        "id": "fib_iter",
        "title": "字符串处理",
        "description": "字符串拼接、索引访问和长度操作",
        "code": '# 字符串处理示例\n\n定义文本等于"光明编程语言"。\n打印("原始文本："加文本)。\n打印("长度："加文本之长度)。\n打印("第一个字符："加文本[0])。\n\n# 字符串拼接\n定义a等于"你好，"加"世界！"。\n打印(a)。\n\n# 数字与字符串拼接\n定义年份等于2024。\n打印("光明 "加年份加" 版")。\n\n# 多层拼接\n定义t等于"【"加文本加"】"。\n打印("带括号："加t)。\n\n# 列表遍历\n定义列表等于【"a", "b", "c"】。\n遍历 项 列表:\n  打印("元素："加项)。\n结束。\n\n# 循环拼接\n定义结果等于""。\n定义i等于0。\n当i小于3:\n  结果等于结果加文本[i]。\n  定义i等于i加1。\n结束。\n打印("前三个字符："加结果)。'
    },
    {
        "id": "list_analysis",
        "title": "列表统计分析",
        "description": "对列表进行求和分析、极值和排序",
        "code": '# 列表统计分析\n\n定义数据等于【23, 45, 12, 67, 34, 89, 56, 78, 91, 10】。\n打印("原始数据："加数据)。\n\n# 求和\n《求和》段(列表):\n  定义_总分等于0。\n  遍历 项 列表:\n    定义_总分等于_总分加项。\n  结束。\n  返回_总分。\n结束。\n\n# 找最大值\n《最大值》段(列表):\n  定义_最大等于列表[0]。\n  遍历 项 列表:\n    如果项大于_最大那么:\n      定义_最大等于项。\n    结束。\n  结束。\n  返回_最大。\n结束。\n\n# 找最小值\n《最小值》段(列表):\n  定义_最小等于列表[0]。\n  遍历 项 列表:\n    如果项小于_最小那么:\n      定义_最小等于项。\n    结束。\n  结束。\n  返回_最小。\n结束。\n\n定义_总分等于《求和》(数据)。\n定义_数量等于数据之长度。\n定义_平均分等于_总分除_数量。\n打印("求和："加_总分)。\n打印("数量："加_数量)。\n打印("平均："加_平均分)。\n打印("最大值："加《最大值》(数据))。\n打印("最小值："加《最小值》(数据))。'
    },
    {
        "id": "guess_game",
        "title": "猜数字游戏",
        "description": "猜数字游戏，体验条件判断和循环",
        "code": '# 猜数字游戏\n# 规则：系统想一个 1-100 的数，你来猜\n# 由于光明暂不支持输入，我们用列表模拟多次猜测\n\n《猜数字》段(目标数值, 猜测列表):\n  打印("目标数值："加目标数值)。\n  遍历 猜测 猜测列表:\n    如果猜测等于目标数值那么:\n      打印("✓ 猜对了！答案是 "加猜测)。\n      返回真。\n    否则若猜测大于目标数值那么:\n      打印("✗ "加猜测加" 太大了")。\n    否则:\n      打印("✗ "加猜测加" 太小了")。\n    结束。\n  结束。\n  打印("😅 所有猜测都错了，答案是 "加目标数值)。\n  返回假。\n结束。\n\n# 模拟猜数字\n定义_目标等于42。\n定义_猜测列表等于【50, 30, 40, 45, 42】。\n\n《猜数字》(_目标, _猜测列表)。'
    }
]


# =============================================================================
# API 路由
# =============================================================================

@app.route('/')
def index():
    """提供主页面"""
    return send_from_directory(app.static_folder, 'index.html')


# =============================================================================
# 语法参考数据
# =============================================================================

GRAMMAR_REFERENCE = [
    {
        "category": "注释",
        "items": [
            {"syntax": "# 注释内容", "description": "单行注释，以 # 开头"}
        ]
    },
    {
        "category": "变量定义",
        "items": [
            {"syntax": "定义 变量名 等于 值。", "description": "定义变量并初始化"},
            {"syntax": "定义 结果 等于 10。", "example": "定义甲等于10。"},
            {"syntax": "定义 变量名 等于 值。\n定义 变量名 等于 新值。", "description": "修改变量值（省略定义）"},
            {"syntax": "定义甲等于甲加1。", "description": "变量自增"}
        ]
    },
    {
        "category": "数据类型",
        "items": [
            {"syntax": "数值", "description": "整数和浮点数，如 42、3.14"},
            {"syntax": '"文本"', "description": "字符串，用双引号包围"},
            {"syntax": "真 / 假", "description": "布尔值"},
            {"syntax": "空", "description": "空值"},
            {"syntax": "【1, 2, 3】", "description": "列表，用【】包围"},
            {"syntax": '【"键": 值, "键2": 值2】', "description": "字典，用【】包围，键值对用冒号分隔"}
        ]
    },
    {
        "category": "运算符",
        "items": [
            {"syntax": "加 / 减 / 乘 / 除", "description": "算术运算符"},
            {"syntax": "大于 / 小于 / 等于", "description": "比较运算符"},
            {"syntax": "且 / 或 / 非", "description": "逻辑运算符"},
            {"syntax": "->", "description": "管道操作符，连接列表或结果传递"}
        ]
    },
    {
        "category": "条件判断",
        "items": [
            {"syntax": "如果 条件 那么:\n  代码\n结束。", "description": "基本条件判断"},
            {"syntax": "如果 条件 那么:\n  代码\n否则:\n  代码\n结束。", "description": "条件判断带否则分支"},
            {"syntax": "如果 条件 那么:\n  代码\n否则若 条件 那么:\n  代码\n否则:\n  代码\n结束。", "description": "多条件判断链"}
        ]
    },
    {
        "category": "循环",
        "items": [
            {"syntax": "当 条件:\n  代码\n结束。", "description": "当循环，条件为真时重复执行"},
            {"syntax": "遍历 项 列表:\n  代码\n结束。", "description": "遍历列表每个元素"},
            {"syntax": "跳出。", "description": "跳出当前循环"},
            {"syntax": "跳过。", "description": "跳过当前迭代"}
        ]
    },
    {
        "category": "段落（函数）",
        "items": [
            {"syntax": "《名称》段(参数):\n  代码\n结束。", "description": "定义段落（函数）"},
            {"syntax": "《名称》(参数)。", "description": "调用段落"},
            {"syntax": "返回 值。", "description": "从段落返回值"}
        ]
    },
    {
        "category": "导入与导出",
        "items": [
            {"syntax": "从 模块 导入《段1》，《段2》。", "description": "从模块导入指定段落"},
            {"syntax": "导出《段1》，《段2》。", "description": "导出当前文件中的段落"},
            {"syntax": "导入 模块。", "description": "直接导入模块的全部内容"}
        ]
    },
    {
        "category": "内置函数",
        "items": [
            {"syntax": "打印(值)。", "description": "输出值到控制台"},
            {"syntax": "列表之长度", "description": "获取列表长度"}
        ]
    },
    {
        "category": "错误处理",
        "items": [
            {"syntax": "尝试:\n  代码\n捕获 错误:\n  代码\n结束。", "description": "异常捕获"},
            {"syntax": "抛出 值。", "description": "主动抛出错误"}
        ]
    },
    {
        "category": "完整示例",
        "items": [
            {"syntax": "# Hello World\n打印(\"你好，光明！\")。", "description": "入门示例"},
            {"syntax": "# 条件判断\n如果 分数 大于等于 60 那么:\n  打印(\"及格\")。\n否则:\n  打印(\"不及格\")。\n结束。", "description": "条件判断示例"},
            {"syntax": "# 递归函数\n《阶乘》段(n):\n  如果 n 小于等于 1 那么:\n    返回 1。\n  结束。\n  返回 n 乘《阶乘》(n减1)。\n结束。", "description": "递归函数示例"}
        ]
    }
]


@app.route('/api/grammar', methods=['GET'])
def get_grammar():
    """获取语法参考数据"""
    return jsonify({'categories': GRAMMAR_REFERENCE})


@app.route('/api/execute', methods=['POST'])
def execute():
    """执行光明代码"""
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    try:
        interp = run_source(code)
        output = interp.get_output()
        if not output:
            output = '(无输出)'

        return jsonify({
            'success': True,
            'output': output,
            'execution_time': 0
        })
    except SyntaxError as e:
        return jsonify({'success': False, 'error': f'语法错误: {e}'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'运行时错误: {type(e).__name__}: {e}'})


@app.route('/api/examples', methods=['GET'])
def get_examples():
    """获取内置示例列表"""
    return jsonify({'examples': BUILTIN_EXAMPLES})


@app.route('/api/examples/<example_id>', methods=['GET'])
def get_example(example_id):
    """获取单个示例详情"""
    for ex in BUILTIN_EXAMPLES:
        if ex['id'] == example_id:
            return jsonify(ex)
    return jsonify({'error': '示例未找到'}), 404


@app.route('/api/share', methods=['POST'])
def share_code():
    """分享代码（返回唯一 ID）"""
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    # 生成唯一 ID（基于内容和时间戳）
    content_hash = hashlib.md5(code.encode('utf-8')).hexdigest()[:8]
    timestamp = int(time.time())
    share_id = f"{content_hash}-{timestamp}"

    # 保存到文件
    share_file = os.path.join(SHARED_DIR, f"{share_id}.json")
    if not os.path.exists(share_file):
        with open(share_file, 'w', encoding='utf-8') as f:
            json.dump({
                'id': share_id,
                'code': code,
                'created_at': timestamp
            }, f, ensure_ascii=False, indent=2)

    return jsonify({
        'success': True,
        'share_id': share_id,
        'share_url': f"/?share={share_id}"
    })


@app.route('/api/share/<share_id>', methods=['GET'])
def get_shared_code(share_id):
    """获取已分享的代码"""
    share_file = os.path.join(SHARED_DIR, f"{share_id}.json")
    if not os.path.exists(share_file):
        return jsonify({'error': '分享内容未找到或已过期'}), 404

    with open(share_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return jsonify(data)


@app.route('/api/parse', methods=['POST'])
def parse_code():
    """解析代码并返回 AST 信息"""
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    try:
        module = parse_source(code)
        if module is None:
            return jsonify({'success': False, 'error': '解析失败'})

        segments = []
        for seg in module.segments:
            segments.append({
                'name': seg.name,
                'parameters': [p.name for p in seg.parameters],
                'return_type': seg.return_type
            })

        return jsonify({
            'success': True,
            'segments': segments,
            'statement_count': len(module.statements),
            'import_count': len(module.imports),
            'export_count': len(module.exports)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'解析错误: {e}'})


@app.route('/api/tokenize', methods=['POST'])
def tokenize_code():
    """词法分析并返回 Token 列表"""
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '代码不能为空'})

    try:
        tokenizer = LightLangTokenizer()
        tokens = tokenizer.tokenize(code)

        token_list = []
        for t in tokens:
            if t.type_name == 'EOF':
                continue
            token_list.append({
                'type': t.type_name,
                'text': t.text,
                'line': t.line,
                'column': t.column
            })

        has_errors = len(tokenizer.errors) > 0
        return jsonify({
            'success': not has_errors,
            'tokens': token_list,
            'errors': [str(e) for e in tokenizer.errors],
            'token_count': len(token_list)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'词法分析错误: {e}'})


# =============================================================================
# 启动
# =============================================================================

if __name__ == '__main__':
    print(f"光明 Web Playground 启动中...")
    print(f"  静态文件目录: {app.static_folder}")
    print(f"  分享存储目录: {SHARED_DIR}")
    print(f"  访问地址: http://localhost:5000")
    print()
    app.run(debug=True, host='0.0.0.0', port=5000)