# -*- coding: utf-8 -*-
"""批量修复第1批领域（数据/数学/统计/排序/搜索）的剩余问题 v2。

修复类型：
  1. 标识符含 % 字符（如 `导出 减10%`）→ 重命名为中文表述
  2. 标识符含 . 字符（如 `导出 各乘0.01`）→ 重命名为中文表述
  3. 嵌套三元表达式含括号（如 `返回 如果 A 则 (如果 B 则 X 否则 Y) 否则 (如果 C 则 Z 否则 W)`）
     → 重写为 if/else 嵌套块
"""
import json
import os
import re
import subprocess
import sys
import shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, '..'))
V5_DIR = os.path.join(_HERE, 'blocks_v5')
LIGHT_CLI = os.path.join(_REPO, 'cli', 'light.py')
IDX_PATH = os.path.join(_HERE, '索引.json')

# 第1批修复领域
目标领域 = ['数据', '数学', '统计', '排序', '搜索']

# ── 数字转中文 ──────────────────────────────────────────────

_数字中文 = '零一二三四五六七八九'
_单位 = ['', '十', '百', '千', '万']


def _整数转中文(n):
    """将 0-9999 的整数转成中文。"""
    if n == 0:
        return '零'
    if n < 10:
        return _数字中文[n]
    result = ''
    s = str(n)
    length = len(s)
    for i, ch in enumerate(s):
        digit = int(ch)
        pos = length - 1 - i
        if digit == 0:
            if result and not result.endswith('零'):
                result += '零'
        else:
            result += _数字中文[digit] + _单位[pos]
    # 去掉末尾多余的零
    result = result.rstrip('零')
    return result


def _小数部分转中文(frac_str):
    """将小数部分字符串（如 '15'）转成中文（如 '一五'）。"""
    return ''.join(_数字中文[int(d)] for d in frac_str)


# ── % 转中文映射 ────────────────────────────────────────────

_百分映射 = {
    '10%': '百分十',
    '20%': '百分二十',
    '50%': '百分五十',
    '5%': '百分之五',
    '15%': '百分之十五',
    '25%': '百分之二十五',
    '75%': '百分之七十五',
}


def _百分转中文(旧名):
    """将标识符中的 % 替换为中文表述。
    
    如：减10% → 减百分十，各减5% → 各减百分之五
    """
    新名 = 旧名
    for 旧, 新 in sorted(_百分映射.items(), key=lambda x: -len(x[0])):
        if 旧 in 新名:
            新名 = 新名.replace(旧, 新)
    return 新名


# ── .数字 转中文映射 ─────────────────────────────────────────

_小数映射 = {
    '0.01': '百分之一',
    '0.02': '百分之二',
    '0.03': '百分之三',
    '0.05': '百分之五',
    '0.07': '百分之七',
    '0.1': '零点一',
    '0.15': '零点一五',
    '0.25': '零点二五',
    '0.35': '零点三五',
    '0.45': '零点四五',
    '0.5': '一半',
    '0.55': '零点五五',
    '0.65': '零点六五',
    '0.75': '零点七五',
    '0.85': '零点八五',
    '0.95': '零点九五',
    '1.5': '一点五',
    '2.5': '二点五',
}


def _小数转中文(旧名):
    """将标识符中的 .数字 替换为中文表述。
    
    如：各乘0.01 → 各乘百分之一，各乘0.5 → 各乘一半
    """
    新名 = 旧名
    for 旧, 新 in sorted(_小数映射.items(), key=lambda x: -len(x[0])):
        if 旧 in 新名:
            新名 = 新名.replace(旧, 新)
    return 新名


# ── 工具函数 ─────────────────────────────────────────────────


def 语法检查(路径):
    try:
        r = subprocess.run(
            [sys.executable, LIGHT_CLI, 'check', 路径],
            capture_output=True, text=True, timeout=10,
            cwd=_REPO
        )
        if r.returncode != 0:
            err = (r.stderr or r.stdout or '').strip()
            return False, err[:300]
        return True, ''
    except subprocess.TimeoutExpired:
        return False, '超时 (10s)'
    except Exception as e:
        return False, str(e)


def 读取文件(路径):
    with open(路径, 'r', encoding='utf-8') as f:
        return f.read()


def 写入文件(路径, 内容):
    with open(路径, 'w', encoding='utf-8') as f:
        f.write(内容)


def 备份文件(路径):
    """备份文件，返回备份路径。"""
    备份路径 = 路径 + '.bak'
    shutil.copy2(路径, 备份路径)
    return 备份路径


def 恢复备份(路径, 备份路径):
    """从备份恢复文件。"""
    if os.path.exists(备份路径):
        shutil.copy2(备份路径, 路径)
        os.remove(备份路径)


# ── 修复函数 ─────────────────────────────────────────────────


def 修复_百分标识符(路径, 领域, 旧文件名):
    """修复标识符中的 % 字符。
    
    1. 读取文件，替换导出名和段落名中的 %
    2. 重命名文件
    3. 返回新文件名
    """
    内容 = 读取文件(路径)
    旧导出名 = None
    新导出名 = None

    # 从导出行提取旧导出名
    for 行 in 内容.split('\n'):
        m = re.match(r'导出\s+(\S+)', 行)
        if m:
            旧导出名 = m.group(1)
            break

    if not 旧导出名:
        return False, None, '未找到导出名'

    if '%' not in 旧导出名:
        return False, None, '导出名不含 %'

    新导出名 = _百分转中文(旧导出名)
    if 新导出名 == 旧导出名:
        return False, None, '转换后名称无变化'

    # 替换文件内容中的导出名和段落名
    内容 = 内容.replace(f'导出 {旧导出名}', f'导出 {新导出名}')
    内容 = 内容.replace(f'段落 {旧导出名}', f'段落 {新导出名}')

    # 新文件名
    新文件名 = 旧文件名.replace(旧导出名, 新导出名) if 旧导出名 in 旧文件名 else 新导出名 + '.light'
    新路径 = os.path.join(V5_DIR, 领域, 新文件名)

    # 写入新文件
    写入文件(新路径, 内容)

    # 删除旧文件
    if os.path.exists(路径):
        os.remove(路径)

    return True, 新文件名, f'{旧导出名} → {新导出名}'


def 修复_小数标识符(路径, 领域, 旧文件名):
    """修复标识符中的 . 字符。
    
    1. 读取文件，替换导出名和段落名中的 .数字
    2. 重命名文件
    3. 返回新文件名
    """
    内容 = 读取文件(路径)
    旧导出名 = None

    for 行 in 内容.split('\n'):
        m = re.match(r'导出\s+(\S+)', 行)
        if m:
            旧导出名 = m.group(1)
            break

    if not 旧导出名:
        return False, None, '未找到导出名'

    # 检查是否包含 . 且是数字的一部分
    if '.' not in 旧导出名:
        return False, None, '导出名不含 .'

    新导出名 = _小数转中文(旧导出名)
    if 新导出名 == 旧导出名:
        return False, None, '转换后名称无变化'

    # 替换文件内容中的导出名和段落名
    内容 = 内容.replace(f'导出 {旧导出名}', f'导出 {新导出名}')
    内容 = 内容.replace(f'段落 {旧导出名}', f'段落 {新导出名}')

    # 新文件名：用新导出名替换旧文件名中的旧导出名部分
    旧文件名核心 = 旧文件名.rsplit('.', 1)[0]
    if 旧导出名 in 旧文件名核心:
        新文件名 = 旧文件名.replace(旧导出名, 新导出名)
    else:
        # 如果文件名与导出名不匹配，直接基于导出名
        新文件名 = 新导出名 + '.light'
        # 也处理数据后缀
        if '数据' in 旧文件名核心 and '数据' not in 新文件名:
            新文件名 = 新导出名 + '数据.light'

    新路径 = os.path.join(V5_DIR, 领域, 新文件名)

    # 写入新文件
    写入文件(新路径, 内容)

    # 删除旧文件
    if os.path.exists(路径) and 新路径 != 路径:
        os.remove(路径)

    return True, 新文件名, f'{旧导出名} → {新导出名}'


def 修复_嵌套三元(路径, 领域, 旧文件名):
    """修复嵌套三元表达式（含括号）。
    
    将：
        返回 如果 条件1 则 (如果 条件2 则 值1 否则 值2) 否则 (如果 条件3 则 值3 否则 值4)
    重写为：
        如果 条件1：
            如果 条件2：
                返回 值1
            否则：
                返回 值2
        否则：
            如果 条件3：
                返回 值3
            否则：
                返回 值4
    """
    内容 = 读取文件(路径)
    行们 = 内容.split('\n')
    新行们 = []
    修改 = False

    for 行 in 行们:
        # 匹配嵌套三元：返回 如果 条件 则 (子表达式) 否则 (子表达式)
        # 其中子表达式包含 "如果" 和 "则" 和 "否则"
        m = re.match(
            r'^(?P<indent>\s*)返回\s+如果\s+(?P<cond1>.+?)\s+则\s+'
            r'\((?P<inner1>.+?)\)\s+否则\s+'
            r'\((?P<inner2>.+?)\)\s*$',
            行
        )
        if m and '如果' in m.group('inner1') and '如果' in m.group('inner2'):
            indent = m.group('indent')
            cond1 = m.group('cond1').strip()
            inner1 = m.group('inner1').strip()
            inner2 = m.group('inner2').strip()

            # 解析内层表达式
            # inner1: 如果 条件2 则 值1 否则 值2
            m1 = re.match(r'如果\s+(.+?)\s+则\s+(.+?)\s+否则\s+(.+)', inner1)
            m2 = re.match(r'如果\s+(.+?)\s+则\s+(.+?)\s+否则\s+(.+)', inner2)

            if m1 and m2:
                cond2 = m1.group(1).strip()
                val1a = m1.group(2).strip()
                val1b = m1.group(3).strip()
                cond3 = m2.group(1).strip()
                val2a = m2.group(2).strip()
                val2b = m2.group(3).strip()

                新行们.append(f'{indent}如果 {cond1}：')
                新行们.append(f'{indent}    如果 {cond2}：')
                新行们.append(f'{indent}        返回 {val1a}')
                新行们.append(f'{indent}    否则：')
                新行们.append(f'{indent}        返回 {val1b}')
                新行们.append(f'{indent}否则：')
                新行们.append(f'{indent}    如果 {cond3}：')
                新行们.append(f'{indent}        返回 {val2a}')
                新行们.append(f'{indent}    否则：')
                新行们.append(f'{indent}        返回 {val2b}')
                修改 = True
            else:
                新行们.append(行)
        else:
            新行们.append(行)

    if 修改:
        写入文件(路径, '\n'.join(新行们))
        return True, 旧文件名, '嵌套三元重写为 if/else 块'
    return False, 旧文件名, '未匹配嵌套三元模式'


# ── 索引更新 ─────────────────────────────────────────────────


def 更新索引(领域, 旧文件名, 新文件名):
    """更新索引.json 中的路径引用。"""
    if not os.path.exists(IDX_PATH):
        print(f'  ⚠ 索引.json 不存在，跳过更新')
        return False

    with open(IDX_PATH, 'r', encoding='utf-8') as f:
        idx = json.load(f)

    old_ref = f'blocks_v5/{领域}/{旧文件名}'
    new_ref = f'blocks_v5/{领域}/{新文件名}'

    modified = 0
    # 索引结构: {"块": [{"路径": "blocks_v5/数据/xxx.light", "导出名": "xxx"}, ...]}
    if isinstance(idx, dict) and '块' in idx:
        for item in idx['块']:
            if isinstance(item, dict):
                if '路径' in item and item['路径'] == old_ref:
                    item['路径'] = new_ref
                    modified += 1
                # 更新导出名（如果文件名变了，导出名也可能变了）
                if '导出名' in item and old_ref in item.get('路径', ''):
                    # 导出名会在路径更新后自动匹配
                    pass

    if modified > 0:
        with open(IDX_PATH, 'w', encoding='utf-8') as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)
        return True
    return False


# ── 主流程 ───────────────────────────────────────────────────


def 诊断错误类型(错误信息, 文件内容):
    """根据错误信息判断修复类型。"""
    if '%' in 错误信息:
        return '百分号'
    if '0.' in 错误信息 or '无法识别的语法元素' in 错误信息:
        # 检查是否包含 . 在标识符中
        for 行 in 文件内容.split('\n'):
            if 行.startswith('导出'):
                if '.' in 行:
                    return '小数'
    if '(' in 错误信息 and ')' in 错误信息:
        return '嵌套括号'
    return '未知'


def 处理文件(领域, fname):
    """处理单个文件：检查→修复→验证→更新索引。"""
    路径 = os.path.join(V5_DIR, 领域, fname)

    if not os.path.exists(路径):
        return ('跳过', f'文件不存在: {路径}')

    # 1. 语法检查
    ok, err = 语法检查(路径)
    if ok:
        return ('通过', '')

    # 2. 读取内容
    内容 = 读取文件(路径)

    # 3. 分析错误类型
    if '%' in err or ('%' in 内容 and any('导出' in 行 and '%' in 行 for 行 in 内容.split('\n') if 行.startswith('导出'))):
        # 修复百分号
        备份 = 备份文件(路径)
        success, 新文件名, detail = 修复_百分标识符(路径, 领域, fname)
        if success:
            # 验证
            ok2, err2 = 语法检查(os.path.join(V5_DIR, 领域, 新文件名))
            if ok2:
                更新索引(领域, fname, 新文件名)
                if os.path.exists(备份):
                    os.remove(备份)
                return ('修复成功', f'%标识符: {detail}')
            else:
                恢复备份(路径, 备份)
                return ('修复失败', f'%标识符: {detail}, 重检查: {err2[:100]}')
        else:
            恢复备份(路径, 备份)
            return ('修复失败', f'%标识符: {detail}')

    elif '.' in 内容 and any('导出' in 行 and '.' in 行 for 行 in 内容.split('\n') if 行.startswith('导出')):
        # 修复小数标识符
        备份 = 备份文件(路径)
        success, 新文件名, detail = 修复_小数标识符(路径, 领域, fname)
        if success:
            ok2, err2 = 语法检查(os.path.join(V5_DIR, 领域, 新文件名))
            if ok2:
                更新索引(领域, fname, 新文件名)
                if os.path.exists(备份):
                    os.remove(备份)
                return ('修复成功', f'小数标识符: {detail}')
            else:
                恢复备份(路径, 备份)
                return ('修复失败', f'小数标识符: {detail}, 重检查: {err2[:100]}')
        else:
            恢复备份(路径, 备份)
            return ('修复失败', f'小数标识符: {detail}')

    elif '返回 如果' in 内容 and '(' in 内容:
        # 修复嵌套三元
        备份 = 备份文件(路径)
        success, 新文件名, detail = 修复_嵌套三元(路径, 领域, fname)
        if success:
            ok2, err2 = 语法检查(路径)
            if ok2:
                if os.path.exists(备份):
                    os.remove(备份)
                return ('修复成功', f'嵌套三元: {detail}')
            else:
                恢复备份(路径, 备份)
                return ('修复失败', f'嵌套三元: {err2[:100]}')
        else:
            恢复备份(路径, 备份)
            return ('跳过', f'嵌套三元: {detail}')
    else:
        # 检查是否包含嵌套三元但模式不匹配
        if '返回 如果' in 内容:
            return ('需人工检查', f'可能含三元表达式问题: {err[:100]}')
        return ('未知错误', err[:200])


def main():
    print('=== 批量修复第1批领域 v2（剩余240个块）===\n')

    统计 = {'通过': 0, '修复成功': 0, '修复失败': 0, '跳过': 0, '需人工检查': 0, '未知错误': 0}

    for 领域 in 目标领域:
        领域目录 = os.path.join(V5_DIR, 领域)
        if not os.path.isdir(领域目录):
            print(f'[{领域}] 目录不存在，跳过')
            continue

        files = sorted(os.listdir(领域目录))
        print(f'\n── {领域}（共 {len(files)} 个文件）──')

        领域计数 = {'通过': 0, '修复成功': 0, '修复失败': 0, '跳过': 0, '需人工检查': 0, '未知错误': 0}

        for fname in files:
            if not fname.endswith('.light'):
                continue
            if fname.endswith('.bak'):
                continue

            status, detail = 处理文件(领域, fname)
            统计[status] = 统计.get(status, 0) + 1
            领域计数[status] = 领域计数.get(status, 0) + 1

            if status == '通过':
                if 领域计数['通过'] <= 3 or 领域计数['通过'] % 20 == 0:
                    print(f'  ✅ {fname}')
            elif status == '修复成功':
                print(f'  ✅ {fname} → {detail}')
            elif status == '修复失败':
                print(f'  ❌ {fname}: {detail}')
            elif status == '需人工检查':
                print(f'  ⚠ {fname}: {detail}')
            elif status == '跳过':
                pass  # 不打印跳过的
            else:
                print(f'  ❓ {fname}: {detail}')

        print(f'  [{领域}] 通过 {领域计数["通过"]}, 修复成功 {领域计数["修复成功"]}, '
              f'修复失败 {领域计数["修复失败"]}, 跳过 {领域计数["跳过"]}, '
              f'需人工检查 {领域计数["需人工检查"]}')

    print(f'\n=== 汇总 ===')
    print(f'通过: {统计["通过"]}')
    print(f'修复成功: {统计["修复成功"]}')
    print(f'修复失败: {统计["修复失败"]}')
    print(f'跳过: {统计["跳过"]}')
    print(f'需人工检查: {统计["需人工检查"]}')
    print(f'未知错误: {统计["未知错误"]}')

    return 0 if 统计.get('修复失败', 0) == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())