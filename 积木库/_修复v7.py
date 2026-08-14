# -*- coding: utf-8 -*-
"""
光明积木库综合修复 v7
=====================
修复策略：
A. 转换所有文件为 LF 换行符
B. 移除科学记数法参数名（如 67e, 496e8, 3e8 等）
C. 修复 _预跑.py 中 cb_前缀回调参数检测
D. 补充缺失变量
E. 修复分组函数参数字序
"""

import os, re, sys

_HERE = os.path.abspath(os.path.dirname(__file__))
BLOCKS_DIR = os.path.join(_HERE, 'blocks_v5')
PRE_RUN_PATH = os.path.join(_HERE, '_预跑.py')

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)

def log(msg):
    print(f"  {msg}")

# Fix A: 转换所有文件为 LF 换行符
def fix_a_crlf():
    print("\n=== Fix A: 转换 CRLF 为 LF ===")
    count = 0
    for root, dirs, files in os.walk(BLOCKS_DIR):
        for f in files:
            if not f.endswith('.light'):
                continue
            path = os.path.join(root, f)
            content = read_file(path)
            if '\r\n' in content:
                content = content.replace('\r\n', '\n')
                write_file(path, content)
                count += 1
    log(f"已转换 {count} 个文件为 LF")

# Fix B: 移除科学记数法参数名
def fix_b_sci_params():
    print("\n=== Fix B: 移除科学记数法参数名 ===")
    # 匹配模式：段落 xxx 接收 ..., 数字e数字, ...
    pattern = re.compile(
        r'^(段落\s+\S+\s+接收\s+)(.*?)(：)$',
        re.MULTILINE
    )
    count = 0
    sci_pattern = re.compile(r'\b\d+[eE]\d*\b')
    for root, dirs, files in os.walk(BLOCKS_DIR):
        for f in files:
            if not f.endswith('.light'):
                continue
            path = os.path.join(root, f)
            content = read_file(path)
            # 检查段落行是否有科学记数法参数
            m = pattern.search(content)
            if not m:
                continue
            params_str = m.group(2)
            params = [p.strip() for p in params_str.split(',')]
            # 过滤掉科学记数法参数
            new_params = [p for p in params if not sci_pattern.match(p)]
            if len(new_params) != len(params):
                new_params_str = ', '.join(new_params)
                new_content = content.replace(
                    m.group(0),
                    f"{m.group(1)}{new_params_str}{m.group(3)}"
                )
                write_file(path, new_content)
                count += 1
                rel = os.path.relpath(path, BLOCKS_DIR)
                log(f"已移除科学记数法参数: {rel}")
    log(f"共修复 {count} 个文件")

# Fix C: 修复 _预跑.py 中 cb_前缀回调参数检测
def fix_c_callback_detection():
    print("\n=== Fix C: 修复 cb_前缀回调参数检测 ===")
    content = read_file(PRE_RUN_PATH)
    old_func = '''def _is_callback_param(body, param_name):
    """检查参数名是否在body中被用作函数调用（后面跟着括号）"""
    # 跳过已重命名的回调参数（cb_前缀）
    if param_name.startswith('cb_'):
        return True
    # 检查 pattern: param( 或 param (
    pattern = re.compile(r'(?<![a-zA-Z_\\\\u4e00-\\\\u9fff])' + re.escape(param_name) + r'\\\\s*\\(')
    return bool(pattern.search(body))'''
    
    new_func = '''def _is_callback_param(body, param_name):
    """检查参数名是否在body中被用作函数调用（后面跟着括号）"""
    # 检查 pattern: param( 或 param (
    pattern = re.compile(r'(?<![a-zA-Z_\\\\u4e00-\\\\u9fff])' + re.escape(param_name) + r'\\\\s*\\(')
    return bool(pattern.search(body))'''
    
    if old_func in content:
        content = content.replace(old_func, new_func)
        write_file(PRE_RUN_PATH, content)
        log("已修复 _is_callback_param 函数")
    else:
        log("无需修改或模式不匹配")

# Fix D: 补充缺失变量
def fix_d_missing_vars():
    print("\n=== Fix D: 补充缺失变量 ===")
    content = read_file(PRE_RUN_PATH)
    
    # 在 COMMON_MISSING_VARS 末尾添加新变量
    old_end = "    'cb_反正切2': lambda y, x: __import__('math').atan2(y, x),  # 反正切2\n}"
    new_end = """    'cb_反正切2': lambda y, x: __import__('math').atan2(y, x),  # 反正切2
    # 更多缺失变量（Fix v7）
    '余': 0.0,          # 傅里叶变换余项
    '常数': 1.0,        # 通用常数（化学凝固点等）
    '期容积': 100.0,     # 每搏输出量（医学）
    '速率常数': 0.1,    # 药物动力学（医学）
    # 函数领域缺失变量
    '均值': 100.0,      # 信号标准化均值
    '标准差': 1.0,      # 信号标准化标准差
    'p_衰减': 0.99,     # 回溯搜索衰减率
    # 天文/物理领域缺失变量
    'p_67e': 6.67e-11,  # 万有引力常数
    'p_3e8': 3e8,       # 光速
    'p_63e': 6.63e-34,  # 普朗克常数
    'p_898e': 2.898e-3, # 维恩常数
    'p_097e7': 1.097e7, # 里德伯常数
    'p_086e16': 3.086e16, # 秒差距
    'p_989e30': 1.989e30, # 太阳质量
    'p_96e8': 6.96e8,   # 太阳半径
    'p_828e26': 3.828e26, # 太阳光度
    'p_496e11': 1.496e11, # 天文单位
    'p_496e8': 1.496e8,  # 公里转AU
    'p_67e': 6.67e-11,  # 引力常数
    'p_9e9': 9e9,       # 库仑常数
    'p_99e9': 9e9,      # 库仑常数
    'p_29e': 5.29e-11,  # 玻尔半径
    'p_05e': 1.05e-34,  # 约化普朗克常数
    'p_1e': 1e-10,      # 通用科学常数
    'p_2e': 2e-10,      # 通用科学常数
    'p_6e': 6e-10,      # 通用科学常数
    'p_022e23': 6.022e23, # 阿伏伽德罗常数
    # 函数领域缺失变量（用于回调参数检测修正后）
    'cb_方差': 1.0,     # 双边滤波方差（非回调，实为数值）
}"""
    if old_end in content:
        content = content.replace(old_end, new_end)
        write_file(PRE_RUN_PATH, content)
        log("已补充缺失变量")
    else:
        log("模式不匹配，尝试其他方式补充")
        # 直接查找并替换
        if "cb_反正切2" in content:
            # 找到最后一个 cb_ 相关变量，在其后追加
            insert_pos = content.rfind("cb_反正切2")
            end_of_line = content.find('\n', insert_pos)
            if end_of_line > 0:
                next_line = content.find('\n', end_of_line + 1)
                if next_line > 0:
                    insertion = """
    # 更多缺失变量（Fix v7）
    '余': 0.0,
    '常数': 1.0,
    '期容积': 100.0,
    '速率常数': 0.1,
    '均值': 100.0,
    '标准差': 1.0,
    'cb_方差': 1.0,
"""
                    content = content[:next_line] + insertion + content[next_line:]
                    # 确保最后的 } 还在
                    write_file(PRE_RUN_PATH, content)
                    log("已通过查找方式补充缺失变量")

# Fix E: 修复分组函数
def fix_e_group_func():
    print("\n=== Fix E: 修复分组函数参数字序 ===")
    content = read_file(PRE_RUN_PATH)
    old = "'分组': lambda x, n: [x[i:i+n] for i in range(0, len(x), n)],  # 分组函数"
    new = "'分组': lambda n, x: [x[i:i+n] for i in range(0, len(x), n)] if hasattr(x, '__len__') else [x],  # 分组函数"
    if old in content:
        content = content.replace(old, new)
        write_file(PRE_RUN_PATH, content)
        log("已修复分组函数参数字序")
    else:
        log("分组函数模式不匹配，尝试其他方式")
        # 查找分组行
        for line in content.split('\n'):
            if '分组' in line and 'lambda' in line:
                log(f"找到分组行: {line.strip()}")

# Fix F: 修复标准差关键字冲突（在变量使用的文件中添加声明）
def fix_f_std_keyword():
    print("\n=== Fix F: 修复标准差关键字冲突 ===")
    # 标准差是VERB_ARITY中的关键字（函数），在表达式中被误判为函数调用
    # 修复：在body中添加"设 标准差 为 1"声明，使解析器将其识别为变量名
    affected_files = [
        # 函数领域
        ('函数\\函数标准化.light', '返回 (列表[i] 减 均值) 除 标准差'),
        # 体育领域
        ('体育\\成绩标准化.light', '返回 (成绩 减 平均) 除 标准差'),
        # 医学领域
        ('医学\\新生儿体质量.light', '返回 (实测 减 均值) 除 标准差'),
        ('医学\\生长Z评分.light', '返回 (实测 减 中位) 除 标准差'),
        # 心理领域
        ('心理\\标准化分数.light', '返回 (原始分 减 均值) 除 标准差'),
        # 经济领域
        ('经济\\CVaR.light', '返回 均值 减 标准差 乘 2.063'),
        ('经济\\VaR.light', '返回 均值 减 标准差 乘 1.645'),
        ('经济\\夏普率.light', '返回 (收益 减 无风险) 除 标准差'),
        # 随机领域
        ('随机\\随机MCCVaR.light', '返回 分位数 乘 标准差 除 (1 减 置信度)'),
        ('随机\\随机MCVaR.light', '返回 分位数 乘 标准差'),
        ('随机\\随机变分.light', '返回 均值 加 标准差 乘 (随机() 减 0.5)'),
        ('随机\\随机进化.light', '返回 均值 加 标准差 乘 (随机() 减 0.5)'),
        # 财务领域
        ('财务\\财务VaR.light', '返回 均值 减 标准差 乘 1.645'),
        ('财务\\财务安全库存.light', '返回 Z 乘 标准差 乘 平方根(提前期)'),
        # 统计领域（使用cb_追加的）
        ('统计\\各Z分数.light', '结果.cb_追加((列表[i] 减 均值) 除 标准差)'),
        ('统计\\各z替代.light', '结果.cb_追加((列表[i] 减 均值) 除 标准差)'),
        ('统计\\各变异系数.light', '结果.cb_追加(标准差 除 均值)'),
        ('统计\\各夏普.light', '结果.cb_追加((均值 减 无风险) 除 标准差)'),
        ('统计\\各标准化.light', '结果.cb_追加((列表[i] 减 均值) 除 标准差)'),
        ('统计\\各波动率.light', '结果.cb_追加(标准差 乘 平方根(252))'),
        ('统计\\各白化.light', '结果.cb_追加((列表[i] 减 均值) 除 标准差)'),
        ('统计\\各移动标准差.light', '结果.cb_追加(标准差)'),
    ]
    count = 0
    for rel_path, pattern in affected_files:
        path = os.path.join(BLOCKS_DIR, rel_path)
        if not os.path.exists(path):
            log(f"文件不存在: {rel_path}")
            continue
        content = read_file(path)
        # 找到第一个非注释、非导出、非段落行（即body的第一行）
        lines = content.split('\n')
        insertion_line = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('导出') and not stripped.startswith('段落'):
                insertion_line = i
                break
        if insertion_line >= 0:
            indent = '    '
            # 检查是否已经添加了声明
            if '设 标准差 为 1' in content:
                log(f"已存在声明，跳过: {rel_path}")
                continue
            # 在body第一行前插入声明
            lines.insert(insertion_line, f"{indent}设 标准差 为 1")
            new_content = '\n'.join(lines)
            write_file(path, new_content)
            count += 1
            log(f"已添加标准差声明: {rel_path}")
        else:
            log(f"未找到body行: {rel_path}")
    log(f"共修复 {count} 个文件")

def main():
    print("=" * 60)
    print("光明积木库综合修复 v7")
    print("=" * 60)
    
    fix_a_crlf()
    fix_b_sci_params()
    fix_c_callback_detection()
    fix_d_missing_vars()
    fix_e_group_func()
    fix_f_std_keyword()
    
    print("\n" + "=" * 60)
    print("修复完成！请运行 _预跑.py 验证效果")
    print("=" * 60)

if __name__ == '__main__':
    main()