# -*- coding: utf-8 -*-
"""修复第1轮批量修复三元表达式后剩余的 9 个语法错误。

问题类型：
  1. 导出名以数字开头（如 `导出 01间数`）→ 改为中文数字
  2. 函数名含 `10数`/`100数`/`01数` 导致解析器 bug → 改用纯中文名
"""
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, '..'))
V5_DIR = os.path.join(_HERE, 'blocks_v5')
LIGHT_CLI = os.path.join(_REPO, 'cli', 'light.py')

# 重命名映射：旧名 → 新名
重命名映射 = {
    # 数字开头的导出名
    '01间数': '零一间数',
    '10100间数': '十到百间数',
    '10倍数数': '十倍数数',
    '2倍数数': '二倍数数',
    '3倍数数': '三倍数数',
    '5倍数数': '五倍数数',
    # 函数名含数字+中文导致解析 bug
    '大于10数': '超过十数',
    '大于100数': '超过百数',
    '小于01数': '小于零点一数',
}

领域 = '统计'


def 语法检查(路径):
    try:
        r = subprocess.run(
            [sys.executable, LIGHT_CLI, 'check', 路径],
            capture_output=True, text=True, timeout=10,
            cwd=_REPO
        )
        return r.returncode == 0, (r.stderr or r.stdout or '').strip()[:200]
    except subprocess.TimeoutExpired:
        return False, '超时 (10s)'
    except Exception as e:
        return False, str(e)


def 修复文件(旧名, 新名):
    old_path = os.path.join(V5_DIR, 领域, f'{旧名}.light')
    new_path = os.path.join(V5_DIR, 领域, f'{新名}.light')

    if not os.path.exists(old_path):
        print(f'  ⚠ 文件不存在: {旧名}.light')
        return False

    # 读取文件内容
    with open(old_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换导出名和段落名
    content = content.replace(f'导出 {旧名}', f'导出 {新名}')
    content = content.replace(f'段落 {旧名}', f'段落 {新名}')

    # 写入新文件
    with open(new_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # 删除旧文件
    os.remove(old_path)

    # 语法检查
    ok, err = 语法检查(new_path)
    if ok:
        print(f'  ✅ {旧名}.light → {新名}.light')
        return True
    else:
        print(f'  ❌ {旧名}.light → {新名}.light: {err}')
        # 恢复
        with open(new_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace(f'导出 {新名}', f'导出 {旧名}')
        content = content.replace(f'段落 {新名}', f'段落 {旧名}')
        with open(old_path, 'w', encoding='utf-8') as f:
            f.write(content)
        if os.path.exists(new_path):
            os.remove(new_path)
        return False


def 更新索引(旧名, 新名):
    """更新索引.json 中的路径引用。"""
    idx_path = os.path.join(_HERE, '索引.json')
    if not os.path.exists(idx_path):
        print(f'  ⚠ 索引.json 不存在，跳过更新')
        return

    with open(idx_path, 'r', encoding='utf-8') as f:
        idx = json.load(f)

    old_ref = f'统计/{旧名}'
    new_ref = f'统计/{新名}'

    modified = 0
    if isinstance(idx, dict):
        # 遍历所有值
        for key in list(idx.keys()):
            val = idx[key]
            if isinstance(val, str) and old_ref in val:
                idx[key] = val.replace(old_ref, new_ref)
                modified += 1
            elif isinstance(val, dict):
                for sub_key in val:
                    sub_val = val[sub_key]
                    if isinstance(sub_val, str) and old_ref in sub_val:
                        val[sub_key] = sub_val.replace(old_ref, new_ref)
                        modified += 1
    elif isinstance(idx, list):
        for i, item in enumerate(idx):
            if isinstance(item, dict) and '路径' in item:
                if old_ref in item['路径']:
                    item['路径'] = item['路径'].replace(old_ref, new_ref)
                    modified += 1

    if modified > 0:
        with open(idx_path, 'w', encoding='utf-8') as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)
        print(f'  📝 索引.json 更新了 {modified} 处引用')


def main():
    print('=== 修复 9 个语法错误 ===\n')

    成功 = 0
    失败 = 0

    for 旧名, 新名 in 重命名映射.items():
        ok = 修复文件(旧名, 新名)
        if ok:
            更新索引(旧名, 新名)
            成功 += 1
        else:
            失败 += 1

    print(f'\n结果: {成功} 成功, {失败} 失败')
    return 0 if 失败 == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())