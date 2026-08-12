# -*- coding: utf-8 -*-
"""修复B2.2中因科学计数法/小数导致修复失败的17个文件。"""

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, '..'))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, 'src'))

from light_parser_v3 import LightParser, ParseError

V5_DIR = os.path.join(_HERE, 'blocks_v5')

# 替换映射：科学计数法/小数 → 整数运算
替换表 = [
    # 物理/天文常数（科学计数法 → 整数）
    ('3e8', '300000000'),
    ('3e-5', '3 除 100000'),
    ('2e-5', '2 除 100000'),
    ('6.67e-11', '667 除 10000000000000'),
    ('6.63e-34', '663 除 1000000000000000000000000000000000000'),
    ('9.11e-31', '911 除 1000000000000000000000000000000000'),
    ('5.67e-8', '567 除 10000000000'),
    ('3.156e7', '31560000'),
    ('1.38e-23', '138 除 10000000000000000000000000'),
    # 小数
    ('3.14159', '314159 除 100000'),
    ('67.8', '678 除 10'),
    ('0.25', '1 除 4'),
    ('0.0065', '65 除 10000'),
    ('288.15', '28815 除 100'),
    ('2.512', '2512 除 1000'),
    ('3.5', '7 除 2'),
    ('5.2561', '52561 除 10000'),
    ('0.512', '512 除 1000'),
    ('0.156', '156 除 1000'),
    ('0.14159', '14159 除 100000'),
    ('0.01', '1 除 100'),
    ('0.5', '1 除 2'),
]

# 方法调用修复
方法调用模式 = re.compile(r'(\w+)\.(\w+)\(\)')


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


def 修复文件(路径):
    备份 = None
    try:
        with open(路径, 'r', encoding='utf-8') as f:
            content = f.read()
        备份 = content
    except Exception as e:
        return False, f'读取失败: {e}'
    
    修改 = False
    
    # 1. 替换科学计数法/小数
    for 旧, 新 in 替换表:
        if 旧 in content:
            content = content.replace(旧, 新)
            修改 = True
    
    # 2. 修复方法调用（如 (输入 除 2e-5).对数() → 对数(输入 除 2e-5)）
    # 但注意替换后可能变成 (输入 除 2 除 100000).对数() → 对数(输入 除 2 除 100000)
    if 方法调用模式.search(content):
        content = 方法调用模式.sub(lambda m: f'{m.group(2)}({m.group(1)})', content)
        修改 = True
    
    if not 修改:
        return False, None
    
    # 写前检查
    parser = LightParser()
    try:
        m = parser.parse(content)
        if m is None:
            if 备份:
                with open(路径, 'w', encoding='utf-8') as f:
                    f.write(content)
            return False, '预检查解析失败'
    except:
        pass
    
    with open(路径, 'w', encoding='utf-8') as f:
        f.write(content)
    
    ok, verr = 语法检查(路径)
    if ok:
        return True, None
    else:
        if 备份:
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(备份)
        return False, f'语法检查失败: {verr[:100]}'


def main():
    失败文件 = [
        '物理/声压级.light',
        '物理/康普顿.light',
        '物理/康普顿波长.light', 
        '物理/相对论动能.light',
        '物理/相对论质量.light',
        '天文/临界密度.light',
        '天文/史瓦西半径.light',
        '天文/哈勃距离.light',
        '天文/宇宙年龄.light',
        '天文/引力透镜.light',
        '天文/施瓦西半径.light',
        '天文/星等亮度.light',
        '天文/有效温度.light',
        '天文/质光关系.light',
        '天文/轨道周期.light',
        '天文/霍金温度.light',
        '地理/海拔气压.light',
    ]
    
    成功 = 0
    失败 = 0
    
    for fp in 失败文件:
        路径 = os.path.join(V5_DIR, fp)
        if not os.path.exists(路径):
            print(f'  ⚠ 文件不存在: {fp}')
            continue
        
        ok, err = 修复文件(路径)
        if ok:
            print(f'  ✅ {fp}')
            成功 += 1
        elif err:
            print(f'  ❌ {fp}: {err}')
            失败 += 1
        else:
            print(f'  ➖ {fp}（无需修改）')
    
    print(f'\n结果: 成功 {成功}, 失败 {失败}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())