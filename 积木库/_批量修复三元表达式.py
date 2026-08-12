# -*- coding: utf-8 -*-
"""批量修复 blocks_v5 中的三元表达式问题。

问题：在 `设` 语句中使用 `如果 条件 则 值1 否则 值2` 语法不支持。
修复方案：将行内三元表达式转换为 if/else 语句块。

例如：
  设 结果 为 如果 条件 则 值1 否则 值2
→
  如果 条件：
      设 结果 为 值1
  否则：
      设 结果 为 值2

注意：三元表达式在 `返回` 语句中是可以工作的，不需要修复。
"""
import json
import os
import re
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, '..'))
V5_DIR = os.path.join(_HERE, 'blocks_v5')
LIGHT_CLI = os.path.join(_REPO, 'cli', 'light.py')

# 匹配设语句中的三元表达式（单行模式）
# 设 变量 为 如果 条件 则 值1 否则 值2
设三元模式 = re.compile(
    r'^(?P<indent>\s*)设\s+(?P<var>\S+)\s+为\s+'
    r'如果\s+(?P<cond>.+?)\s+则\s+(?P<val1>.+?)\s+否则\s+(?P<val2>.+?)$'
)

# 多行模式：用于在全文 content 中搜索
设三元模式多行 = re.compile(
    r'^(?P<indent>\s*)设\s+(?P<var>\S+)\s+为\s+'
    r'如果\s+(?P<cond>.+?)\s+则\s+(?P<val1>.+?)\s+否则\s+(?P<val2>.+?)$',
    re.MULTILINE
)

# 匹配返回语句中的三元表达式（不需要修复）
返回三元模式 = re.compile(r'^\s*返回\s+如果\s+.*则\s+.*否则\s+')


def 语法检查(路径):
    """调用 light check 做语法检查。"""
    try:
        r = subprocess.run(
            [sys.executable, LIGHT_CLI, 'check', 路径],
            capture_output=True, text=True, timeout=10,
            cwd=_REPO
        )
        if r.returncode != 0:
            return False, (r.stderr or r.stdout or '').strip()[:200]
        return True, ''
    except subprocess.TimeoutExpired:
        return False, '超时 (10s)'
    except Exception as e:
        return False, str(e)


def 修复三元表达式(内容):
    """修复文件内容中的三元表达式。"""
    行们 = 内容.split('\n')
    新行们 = []
    修改 = False

    for 行 in 行们:
        m = 设三元模式.match(行)
        if m:
            indent = m.group('indent')
            var = m.group('var')
            cond = m.group('cond').strip()
            val1 = m.group('val1').strip()
            val2 = m.group('val2').strip()

            # 如果 val2 等于 var，说明 else 分支是赋值给自身，可以省略
            if val2 == var:
                新行们.append(f'{indent}如果 {cond}：')
                新行们.append(f'{indent}    设 {var} 为 {val1}')
            else:
                新行们.append(f'{indent}如果 {cond}：')
                新行们.append(f'{indent}    设 {var} 为 {val1}')
                新行们.append(f'{indent}否则：')
                新行们.append(f'{indent}    设 {var} 为 {val2}')
            修改 = True
        else:
            新行们.append(行)

    return '\n'.join(新行们), 修改


def main():
    start = time.time()
    print('=== 批量修复三元表达式 ===\n')

    # 收集所有 .light 文件
    所有文件 = []
    for 领域 in sorted(os.listdir(V5_DIR)):
        dir_path = os.path.join(V5_DIR, 领域)
        if not os.path.isdir(dir_path):
            continue
        for fname in sorted(os.listdir(dir_path)):
            if not fname.endswith('.light'):
                continue
            所有文件.append((领域, fname))

    print(f'扫描 {len(所有文件)} 个文件...')

    # 第1轮：扫描并修复
    需修复 = []
    已修复 = []
    修复失败 = []

    for 领域, fname in 所有文件:
        fpath = os.path.join(V5_DIR, 领域, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 只处理包含"如果"、"则"、"否则"的文件
        if '如果' in content and '则' in content and '否则' in content:
            # 检查是否包含设语句中的三元表达式（使用多行模式）
            if 设三元模式多行.search(content):
                # 排除返回语句中的三元表达式
                需修复.append((领域, fname, fpath))

    print(f'发现 {len(需修复)} 个文件包含需要修复的三元表达式\n')

    # 修复前先抽样原始语法检查
    print('=== 修复前抽样语法检查 ===')
    前失败 = 0
    for 领域, fname, fpath in 需修复[:5]:
        ok, err = 语法检查(fpath)
        if not ok:
            前失败 += 1
            print(f'  ❌ {领域}/{fname}: {err}')
        else:
            print(f'  ✅ {领域}/{fname}: 语法通过')
    print(f'抽样 {min(5, len(需修复))} 个, {前失败} 个失败\n')

    # 执行修复
    print('=== 执行修复 ===')
    for 领域, fname, fpath in 需修复:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        新内容, 修改 = 修复三元表达式(content)
        if 修改:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(新内容)

            # 验证语法
            ok, err = 语法检查(fpath)
            if ok:
                已修复.append((领域, fname))
                print(f'  ✅ {领域}/{fname}')
            else:
                修复失败.append((领域, fname, err))
                print(f'  ❌ {领域}/{fname}: {err}')
        else:
            print(f'  ⚠ {领域}/{fname}: 未修改（模式不匹配）')

    print(f'\n修复结果: {len(已修复)} 成功, {len(修复失败)} 失败')

    # 报告修复失败
    if 修复失败:
        print(f'\n=== 修复失败列表 ===')
        for 领域, fname, err in 修复失败:
            print(f'  ❌ {领域}/{fname}: {err}')

    elapsed = time.time() - start
    print(f'\n总耗时: {elapsed:.1f}s')

    # 输出报告
    report = {
        '总文件数': len(所有文件),
        '需修复': len(需修复),
        '已修复': len(已修复),
        '修复失败': len(修复失败),
        '修复列表': [f'{d}/{f}' for d, f in 已修复],
        '失败列表': [f'{d}/{f}: {e}' for d, f, e in 修复失败],
    }
    with open(os.path.join(_HERE, '_修复报告_三元表达式.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\n修复报告已保存到 _修复报告_三元表达式.json')

    return 0 if not 修复失败 else 1


if __name__ == '__main__':
    raise SystemExit(main())