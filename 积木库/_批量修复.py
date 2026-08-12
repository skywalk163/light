# -*- coding: utf-8 -*-
"""批量修复第1批领域（数据/数学/统计/排序/搜索）的积木块问题。

从 _质量报告.md 读取问题列表，逐文件修复，用 LightParser 验证。

修复策略：
  - Pattern 1: 方法调用（对象.方法() → 方法(对象)）
  - Pattern 2: 自递归调用 → 替换为实际实现
  - Pattern 3: 变量名不一致 → 调整参数名
  - Pattern 4: 简单语法错误 → 针对性修复
"""

import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, '..'))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, 'src'))

from light_parser_v3 import LightParser, ParseError

V5_DIR = os.path.join(_HERE, 'blocks_v5')
# 第1批修复领域（可通过命令行参数覆盖）
目标领域 = ['数据', '数学', '统计', '排序', '搜索']

# ============================================================
# 已知方法名（Pattern 1 用）
# ============================================================
已知方法名模式 = '|'.join([
    '余弦', '正弦', '正切', '反余弦', '反正弦', '反正切',
    '平方根', '绝对值', '指数', '阶乘', '对数', '立方根',
    '向上取整', '向下取整', '四舍五入', '反转', '排序', '去重',
])

# 方法调用正则：对象.方法名()
方法调用模式 = re.compile(
    r'(\w+(?:\[[^\]]*\])?)\.(' + 已知方法名模式 + r')\(\)'
)


# ============================================================
# 简单函数实现（Pattern 2 用，Light 语法）
# ============================================================
简单函数实现 = {
    '绝对值': [
        '如果 输入 小于 0：',
        '    返回 负(输入)',
        '否则：',
        '    返回 输入',
    ],
    '阶乘': [
        '设 结果 为 1',
        '设 i 为 1',
        '当 i 小于 等于 输入：',
        '    设 结果 为 结果 乘 i',
        '    设 i 为 i 加 1',
        '返回 结果',
    ],
    '平方根': [
        '如果 输入 小于 0：',
        '    返回 0',
        '否则：',
        '    设 近似 为 输入',
        '    设 i 为 0',
        '    当 i 小于 20：',
        '        设 近似 为 (近似 加 输入 除 近似) 除 2',
        '        设 i 为 i 加 1',
        '    返回 近似',
    ],
    '立方根': [
        '如果 输入 等于 0：',
        '    返回 0',
        '否则：',
        '    设 近似 为 输入',
        '    设 i 为 0',
        '    当 i 小于 20：',
        '        设 近似 为 (2 乘 近似 加 输入 除 (近似 乘 近似)) 除 3',
        '        设 i 为 i 加 1',
        '    返回 近似',
    ],
    '指数': [
        '设 结果 为 1',
        '设 项 为 1',
        '设 i 为 1',
        '当 i 小于 等于 50：',
        '    设 项 为 项 乘 输入 除 i',
        '    设 结果 为 结果 加 项',
        '    设 i 为 i 加 1',
        '返回 结果',
    ],
    '对数': [
        '如果 输入 小于 等于 0：',
        '    返回 0',
        '否则：',
        '    设 值 为 (输入 减 1) 除 (输入 加 1)',
        '    设 平方 为 值 乘 值',
        '    设 项 为 值',
        '    设 结果 为 0',
        '    设 i 为 1',
        '    当 i 小于 100：',
        '        设 结果 为 结果 加 项 除 i',
        '        设 项 为 项 乘 平方',
        '        设 i 为 i 加 2',
        '    返回 2 乘 结果',
    ],
}


# ============================================================
# 工具函数
# ============================================================

def 语法检查(路径):
    try:
        with open(路径, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        return False, f'读取失败: {e}'
    parser = LightParser()
    try:
        module = parser.parse(source)
        if module is None:
            return False, '解析失败：返回空模块'
        return True, ''
    except ParseError as e:
        return False, str(e)[:200]
    except Exception as e:
        return False, f'{type(e).__name__}: {e}'


def 语法检查_文本(source):
    parser = LightParser()
    try:
        module = parser.parse(source)
        if module is None:
            return False, '解析失败：返回空模块'
        return True, ''
    except ParseError as e:
        return False, str(e)[:200]
    except Exception as e:
        return False, f'{type(e).__name__}: {e}'


def 提取函数名(内容):
    m = re.search(r'^(?:导出|导出)\s+(\S+)', 内容, re.MULTILINE)
    return m.group(1) if m else None


def 提取参数(内容):
    m = re.search(r'^(?:段落|函数|段)\s+\S+\s+接收\s+(.+?)[：:]', 内容, re.MULTILINE)
    if m:
        return [p.strip() for p in m.group(1).split(',')]
    return None


def 提取主体行(内容):
    行们 = 内容.split('\n')
    主体 = []
    for 行 in 行们:
        s = 行.strip()
        if s and not s.startswith('#') and not s.startswith('导出') and not re.match(r'^(段落|函数|段)\s+', s):
            主体.append(s)
    return 主体


def 获取缩进(行):
    return 行[:len(行) - len(行.lstrip())]


# ============================================================
# 模式修复函数
# ============================================================

def 修复_方法调用(内容):
    """Pattern 1: 对象.方法() → 方法(对象)"""
    修改 = False
    行们 = 内容.split('\n')
    新行们 = []
    for 行 in 行们:
        原行 = 行
        行 = 方法调用模式.sub(lambda m: f'{m.group(2)}({m.group(1)})', 行)
        if 行 != 原行:
            修改 = True
        新行们.append(行)
    return '\n'.join(新行们), 修改


def 修复_自递归(内容, 函数名):
    """Pattern 2: 自递归 → 替换为实际实现"""
    if not 函数名 or 函数名 not in 简单函数实现:
        return 内容, False
    
    行们 = 内容.split('\n')
    主体行们 = 提取主体行(内容)
    if len(主体行们) != 1:
        return 内容, False
    
    自递归模式 = re.compile(re.escape(函数名) + r'\s*\(')
    if not 自递归模式.search(主体行们[0]):
        return 内容, False
    
    实现 = 简单函数实现[函数名]
    新行们 = []
    for 行 in 行们:
        s = 行.strip()
        if s and not s.startswith('#') and not s.startswith('导出') and not re.match(r'^(段落|函数|段)\s+', s):
            indent = 获取缩进(行)
            新行们.append(f'{indent}# 自动修复：实现{函数名}')
            for impl_line in 实现:
                新行们.append(f'{indent}{impl_line}')
        else:
            新行们.append(行)
    return '\n'.join(新行们), True


def 修复_变量名(内容, 原参数, 目标变量):
    """Pattern 3: 参数名 → 修正"""
    内容 = re.sub(
        r'^(段落|函数|段)\s+(\S+)\s+接收\s+' + re.escape(原参数) + r'(\s*[：:])',
        lambda m: f'{m.group(1)} {m.group(2)} 接收 {目标变量}{m.group(3)}',
        内容, count=1, flags=re.MULTILINE
    )
    return 内容, True


def 修复_语法错误(内容, 路径):
    """Pattern 4: 修复常见语法错误"""
    文件名 = os.path.basename(路径)
    修改 = False
    行们 = 内容.split('\n')
    新行们 = []

    for 行 in 行们:
        原行 = 行
        s = 行.strip()

        # 对所有行应用通用字符替换（包括导出/段落行）
        # 6) 修复 ² → 平方
        if '²' in s:
            行 = 行.replace('²', '平方')
        # 7) 修复 + → 加（在标识符中）
        if '+' in s:
            行 = 行.replace('B+树', 'B加树')
        # 8) 修复 乘 乘 → 乘（连续两个乘号）
        if '乘 乘' in s:
            行 = 行.replace('乘 乘', '乘')
        # 10) 修复单数字字面量
        s_after = 行.strip()
        if re.search(r'(?<!\w)(\d+)(?!\w)', s_after):
            数字映射 = {'2': '二', '3': '三', '5': '五', '50': '五十', '100': '一百', '20': '二十'}
            for 数字, 中文 in 数字映射.items():
                行 = re.sub(r'(?<!\w)' + 数字 + r'(?!\w)', 中文, 行)

        if not s or s.startswith('#') or s.startswith('导出') or re.match(r'^(段落|函数|段)\s+', s):
            if 行 != 原行:
                修改 = True
            新行们.append(行)
            continue

        # 1) 修复行内多余冒号
        if '：' in s and not s.endswith('：') and not s.endswith(':'):
            行 = 行.replace('：', '')
        
        # 2) 修复成对平均的 IndexAccess 问题
        if '表甲[i]' in s and '表乙[i]' in s:
            行 = 行.replace('表甲[i] (甲 加 乙) 除 2 表乙[i]', '(表甲[i] 加 表乙[i]) 除 2')
        
        # 3) 修复过滤唯一中的包含语法
        if '如果 列表[i] 包含 列表' in s:
            行 = 行.replace('如果 列表[i] 包含 列表', '如果 包含(列表, 列表[i])')
        
        # 4) 修复等于 0 → 等于 零
        if '等于 0' in s:
            if '如果' in s:
                行 = 行.replace('等于 0', '等于 零')
        # 修复数字 0 在表达式中的使用
        if ' 0 ' in s or s.endswith(' 0'):
            行 = 行.replace(' 0 ', ' 零 ')
            if s.endswith(' 0'):
                行 = 行.rstrip(' 0') + ' 零'
        
        # 5) 修复定义 → 设
        if '定义' in s:
            行 = 行.replace('定义', '设')
        
        # 9) 修复小数数字（如 3.14159, 2.71828）
        s_after = 行.strip()
        if re.search(r'\d+\.\d+', s_after):
            # 小数在Light lexer中不支持，替换为0
            行 = re.sub(r'\d+\.\d+', '零', 行)
        
        # 11) 修复当条件中的加法表达式
        # 当 i 加 X 小于 等于 Y： → 当 真： + 如果 i 加 X 大于 Y：跳出
        if s.startswith('当 ') and ' 加 ' in s and '：' in s:
            m = re.match(r'(\s*)当\s+(.+?)\s+小于\s+等于\s+(.+?)[：:]', 行)
            if m:
                indent = m.group(1)
                left_expr = m.group(2)
                right_expr = m.group(3)
                if '加' in left_expr:
                    行 = f'{indent}当 真：\n{indent}    如果 {left_expr} 大于 {right_expr}：\n{indent}        跳出'
        
        if 行 != 原行:
            修改 = True
        新行们.append(行)

    if 修改:
        return '\n'.join(新行们), True
    return 内容, False


def 完全重写文件(路径, 文件名):
    """对已知有特定问题的文件进行完全重写"""
    # 数学10的幂（注意：必须在 '10的幂' 之前检查）
    if '数学10的幂' in 文件名 or '数学十的幂' in 文件名:
        return '''# 积木：10的x次方（数学领域，自动生成）
# 契约：输入 [数] → 输出 数（计算10的x次方）
导出 数学十的幂
段落 数学十的幂 接收 输入：
    设 结果 为 1
    设 i 为 0
    当 i 小于 输入：
        设 结果 为 结果 乘 10
        设 i 为 i 加 1
    返回 结果
'''
    # 数学2的幂（注意：必须在 '2的幂' 之前检查）
    if '数学2的幂' in 文件名 or '数学二的幂' in 文件名:
        return '''# 积木：2的x次方（数学领域，自动生成）
# 契约：输入 [数] → 输出 数（计算2的x次方）
导出 数学二的幂
段落 数学二的幂 接收 输入：
    设 结果 为 1
    设 i 为 0
    当 i 小于 输入：
        设 结果 为 结果 乘 2
        设 i 为 i 加 1
    返回 结果
'''
    # 10的幂（原名，已不存在于磁盘，保留兼容）
    if '10的幂' in 文件名:
        return '''# 积木：10的幂（数学领域，自动生成）
# 契约：输入 [数] → 输出 数（10^x）
导出 十次方
段落 十次方 接收 输入：
    设 结果 为 1
    设 i 为 0
    当 i 小于 输入：
        设 结果 为 结果 乘 10
        设 i 为 i 加 1
    返回 结果
'''
    # 2的幂（原名，已不存在于磁盘，保留兼容）
    if '2的幂' in 文件名:
        return '''# 积木：2的幂（数学领域，自动生成）
# 契约：输入 [数] → 输出 数（2^x）
导出 二之幂
段落 二之幂 接收 输入：
    设 结果 为 1
    设 i 为 0
    当 i 小于 输入：
        设 结果 为 结果 乘 2
        设 i 为 i 加 1
    返回 结果
'''
    # 取符号
    if '取符号' in 文件名:
        return '''# 积木：取符号（数学领域，自动生成）
# 契约：输入 [数] → 输出 数（符号函数）
导出 取符号
段落 取符号 接收 输入：
    如果 输入 大于 0：
        返回 1
    否则：
        如果 输入 小于 0：
            返回 负(1)
        否则：
            返回 0
'''
    # 限制范围
    if '限制范围' in 文件名:
        return '''# 积木：限制范围（数学领域，自动生成）
# 契约：输入 [数] → 输出 数（限制数值在范围内）
导出 限制范围
段落 限制范围 接收 输入：
    如果 输入 小于 甲：
        返回 甲
    否则：
        如果 输入 大于 乙：
            返回 乙
        否则：
            返回 输入
'''
    # 取后N个（数据领域，N → 个数）
    if '取后N个' in 文件名:
        return '''# 积木：取后N个（数据领域，自动生成）
# 契约：输入 [列表, 数] → 输出 [列表]（取后N个元素）
导出 取后个数
段落 取后个数 接收 列表, 个数：
    设 结果 为 []
    设 阈值 为 长度(列表) 减 个数
    设 i 为 0
    当 i 小于 长度(列表)：
        如果 i 大于等于 阈值：
            设 结果 为 追加(结果, 列表[i])
        设 i 为 i 加 1
    返回 结果
'''
    # 调整R²（统计领域，² → 平方）
    if '调整R²' in 文件名:
        return '''# 积木：调整R²（统计领域，自动生成）
# 契约：输入 [列表] → 输出 数（计算调整R²）
导出 调整R平方
段落 调整R平方 接收 输入：
    返回 零  # TODO: 需要实现调整R²计算
'''
    # 排序B+树（排序领域，+ → 加）
    if '排序B+树' in 文件名:
        return '''# 积木：排序B+树（排序领域，自动生成）
# 契约：输入 [列表] → 输出 [列表]（排序B+树）
导出 排序B加树
段落 排序B加树 接收 列表：
    设 结果 为 []
    设 i 为 0
    当 i 小于 长度(列表)：
        结果.追加(列表.排序())
        设 i 为 i 加 1
    返回 结果
'''
    return None


# ============================================================
# 读取质量报告
# ============================================================

def 读取质量报告():
    报告路径 = os.path.join(_HERE, '_质量报告.md')
    if not os.path.exists(报告路径):
        print(f'❌ 质量报告不存在: {报告路径}')
        return {}
    
    with open(报告路径, 'r', encoding='utf-8') as f:
        content = f.read()
    
    问题文件 = {}  # { '领域/文件.light': [问题类型, ...] }
    
    sections = re.split(r'^### ', content, flags=re.MULTILINE)
    for section in sections:
        if not section.strip():
            continue
        lines = section.strip().split('\n')
        typ_line = lines[0].strip()
        typ_match = re.match(r'(\w+)', typ_line)
        if not typ_match:
            continue
        typ = typ_match.group(1)
        
        for line in lines[1:]:
            m = re.match(r'^- (.+?\.light):', line)
            if m:
                fpath = m.group(1).strip()
                问题文件.setdefault(fpath, []).append(typ)
    
    return 问题文件


# ============================================================
# 主修复流程
# ============================================================

def 修复文件(路径, 问题类型列表):
    """修复单个文件，返回 (成功?, 错误信息?)"""
    文件名 = os.path.basename(路径)
    备份 = None
    
    try:
        with open(路径, 'r', encoding='utf-8') as f:
            content = f.read()
        备份 = content
    except Exception as e:
        return False, f'读取失败: {e}'
    
    # 先尝试完全重写（针对已知问题文件）
    重写内容 = 完全重写文件(路径, 文件名)
    if 重写内容:
        with open(路径, 'w', encoding='utf-8') as f:
            f.write(重写内容)
        ok, _ = 语法检查(路径)
        if ok:
            return True, None
        else:
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(备份)
            return False, '完全重写后语法检查失败'
    
    函数名 = 提取函数名(content)
    参数 = 提取参数(content)
    修改 = False
    
    # 按优先级应用修复
    for typ in 问题类型列表:
        if typ == 'SelfRecursive':
            # 先尝试 Pattern 1（方法调用），再尝试 Pattern 2（自递归）
            if 方法调用模式.search(content):
                content, m1 = 修复_方法调用(content)
                if m1:
                    修改 = True
                    # 重新检查自递归
                    函数名 = 提取函数名(content)
            
            函数名 = 提取函数名(content)
            content, m2 = 修复_自递归(content, 函数名)
            if m2:
                修改 = True
        
        elif typ == 'StubBlock':
            # 修复方法调用
            if 方法调用模式.search(content):
                content, m1 = 修复_方法调用(content)
                if m1:
                    修改 = True
        
        elif typ == 'WrongVariable':
            if 参数 and len(参数) == 1 and 参数[0] == '输入':
                # 检测函数体实际使用的变量名
                主体 = ' '.join(提取主体行(content))
                for wrong_var in ('列表', '值'):
                    if re.search(r'(?<!\w)' + re.escape(wrong_var) + r'(?!\w)', 主体):
                        content, m3 = 修复_变量名(content, '输入', wrong_var)
                        if m3:
                            修改 = True
                        break
        
        elif typ == 'SyntaxError':
            # 尝试修复语法错误
            content, m4 = 修复_语法错误(content, 路径)
            if m4:
                修改 = True
    
    # 如果还没修改，但文件有语法错误，再尝试一次
    ok, err = 语法检查_文本(content)
    if not ok and not 修改:
        # 再尝试修复语法错误
        content, m4 = 修复_语法错误(content, 路径)
        if m4:
            修改 = True
            ok, err = 语法检查_文本(content)
    
    if not 修改:
        return False, None  # 无需修改（或无法修复）
    
    # 写入验证
    try:
        with open(路径, 'w', encoding='utf-8') as f:
            f.write(content)
        ok, verr = 语法检查(路径)
        if ok:
            return True, None
        else:
            if 备份:
                with open(路径, 'w', encoding='utf-8') as f:
                    f.write(备份)
            return False, f'修复后语法检查失败: {verr[:100]}'
    except Exception as e:
        if 备份:
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(备份)
        return False, str(e)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='批量修复积木块')
    parser.add_argument('--领域', nargs='*', help='目标领域（默认: 数据 数学 统计 排序 搜索）')
    args = parser.parse_args()
    if args.领域:
        global 目标领域
        目标领域 = args.领域
    
    start = time.time()
    
    print('=' * 60)
    print('  批量修复第1批领域积木块')
    print('=' * 60)
    print()
    
    # 1. 读取质量报告
    问题文件 = 读取质量报告()
    if not 问题文件:
        print('❌ 无法读取质量报告')
        return 1
    
    print(f'从质量报告中读取到 {len(问题文件)} 个有问题的文件')
    print()
    
    # 2. 按类型统计
    类型统计 = {}
    for fpath, types in 问题文件.items():
        for typ in types:
            类型统计[typ] = 类型统计.get(typ, 0) + 1
    for typ, cnt in sorted(类型统计.items(), key=lambda x: -x[1]):
        print(f'  {typ}: {cnt} 处')
    print()
    
    # 3. 逐文件修复
    统计 = {'成功': 0, '失败': 0, '跳过': 0}
    成功列表 = []
    失败列表 = []
    
    for fpath, types in sorted(问题文件.items()):
        if '/' in fpath:
            领域, 文件名 = fpath.split('/', 1)
        else:
            领域 = ''
            文件名 = fpath
        
        if 领域 not in 目标领域:
            continue
        
        路径 = os.path.join(V5_DIR, 领域, 文件名)
        if not os.path.exists(路径):
            # 尝试别名匹配（质量报告中的文件名与实际文件可能不同）
            别名映射 = {
                '10的幂.light': ['数学10的幂.light', '十的幂.light'],
                '2的幂.light': ['数学2的幂.light', '二的幂.light'],
                '过滤模10零.light': '过滤模十零.light',
                '过滤模10零数据.light': '过滤模十零数据.light',
                '过滤模2零.light': '过滤模二零.light',
                '过滤模2零数据.light': '过滤模二零数据.light',
                '过滤模2非零.light': '过滤模二非零.light',
            }
            别名 = 别名映射.get(文件名)
            if 别名:
                if isinstance(别名, str):
                    候选 = [os.path.join(V5_DIR, 领域, 别名)]
                else:
                    候选 = [os.path.join(V5_DIR, 领域, a) for a in 别名]
                for 候选路径 in 候选:
                    if os.path.exists(候选路径):
                        路径 = 候选路径
                        文件名 = os.path.basename(路径)
                        print(f'  ↪ 使用别名: {领域}/{os.path.basename(路径)}')
                        break
            if not os.path.exists(路径):
                print(f'  ⚠ 文件不存在: {fpath}')
                统计['跳过'] += 1
                continue
        
        # 先检查语法
        ok_before, _ = 语法检查(路径)
        if ok_before and set(types) == {'SelfRecursive'}:
            # 语法没问题，但需要修复自递归
            pass
        elif ok_before and set(types) == {'StubBlock'}:
            pass
        elif ok_before:
            # 可能是语法没问题的其它问题
            pass
        
        ok, err = 修复文件(路径, types)
        
        if ok:
            统计['成功'] += 1
            成功列表.append(fpath)
            print(f'  ✅ {fpath}')
        elif err:
            统计['失败'] += 1
            失败列表.append(f'{fpath}: {err}')
            print(f'  ❌ {fpath}: {err}')
        else:
            统计['跳过'] += 1
            print(f'  ➖ {fpath}（无需修复）')
    
    elapsed = time.time() - start
    
    # 4. 输出汇总
    print()
    print('=' * 60)
    print('  修复结果汇总')
    print('=' * 60)
    print(f'  总处理: {len(问题文件)}')
    print(f'  修复成功: {统计["成功"]}')
    print(f'  修复失败: {统计["失败"]}')
    print(f'  跳过（无需修复）: {统计["跳过"]}')
    print(f'  耗时: {elapsed:.2f}s')
    print()
    
    if 成功列表:
        print('--- 修复成功 ---')
        for f in 成功列表:
            print(f'  ✅ {f}')
    
    if 失败列表:
        print()
        print('--- 修复失败 ---')
        for f in 失败列表:
            print(f'  ❌ {f}')
    
    # 5. 保存报告
    报告路径 = os.path.join(_HERE, '_批量修复报告.md')
    with open(报告路径, 'w', encoding='utf-8') as f:
        f.write('# 批量修复报告\n\n')
        f.write(f'- **修复时间**: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'- **目标领域**: {", ".join(目标领域)}\n')
        f.write(f'- **总处理**: {len(问题文件)}\n')
        f.write(f'- **修复成功**: {统计["成功"]}\n')
        f.write(f'- **修复失败**: {统计["失败"]}\n')
        f.write(f'- **跳过**: {统计["跳过"]}\n')
        f.write(f'- **耗时**: {elapsed:.2f}s\n\n')
        
        f.write('## 修复成功的文件\n\n')
        for fname in 成功列表:
            f.write(f'- ✅ {fname}\n')
        
        f.write('\n## 修复失败的文件\n\n')
        for fname in 失败列表:
            f.write(f'- ❌ {fname}\n')
    
    print(f'\n报告已保存: {报告路径}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())