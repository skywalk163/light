"""校验 .duan 清单文件的「导出」名是否都能在配对的 .py 实现里真实导入。

用途：stdlib/contrib 下的 .duan 是导出清单（manifest），真正实现在同名 .py。
若清单里写了 .py 并未提供的名字，用户 `从《模块》导入《名字》` 时会在运行期炸掉，
而语法体检（syntax_audit）是发现不了的——它只管解析。

用法:
    python tools/manifest_check.py            # 检查 stdlib + contrib
    python tools/manifest_check.py stdlib     # 只检查某个目录
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_DIRS = ['stdlib', 'contrib']

# 导出 名1 名2 名3。 / 导出 名1、名2。
EXPORT_RX = re.compile(r'^\s*导出\s+(.+?)[。\.]?\s*$')
SPLIT_RX = re.compile(r'[\s,，、]+')


def manifest_exports(duan_path: pathlib.Path) -> list[str]:
    """从 .duan 清单里抽出所有导出名（忽略 # 注释行）。"""
    names: list[str] = []
    for line in duan_path.read_text(encoding='utf-8').splitlines():
        if line.lstrip().startswith('#'):
            continue
        m = EXPORT_RX.match(line)
        if not m:
            continue
        for n in SPLIT_RX.split(m.group(1).strip()):
            n = n.strip('《》()（）')
            if n:
                names.append(n)
    return names


def py_public_names(py_path: pathlib.Path) -> set[str] | None:
    """静态解析 .py 顶层可导入名。解析失败返回 None（跳过，不误报）。"""
    try:
        tree = ast.parse(py_path.read_text(encoding='utf-8'), filename=str(py_path))
    except SyntaxError:
        return None

    # 优先 __all__
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if '__all__' not in targets:
            continue
        if isinstance(node.value, (ast.List, ast.Tuple)):
            vals = {
                e.value for e in node.value.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)
            }
            if vals:
                return vals

    # 回退：所有顶层可导入名（含 import 引入的别名，import 语句本身也让名字可导入）
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                if a.name == '*':
                    return None  # 有 star import，静态判断不可靠，跳过
                names.add(a.asname or a.name.split('.')[0])
    return names


def main(argv: list[str]) -> int:
    dirs = argv[1:] or DEFAULT_DIRS
    total = checked = clean = 0
    problems: list[dict] = []
    no_py: list[str] = []
    skipped: list[str] = []

    for d in dirs:
        base = ROOT / d
        if not base.is_dir():
            print(f'跳过（目录不存在）: {d}')
            continue
        for duan in sorted(base.glob('*.duan')):
            total += 1
            py = duan.with_suffix('.py')
            if not py.exists():
                no_py.append(f'{d}/{duan.name}')
                continue
            exports = manifest_exports(duan)
            if not exports:
                continue
            available = py_public_names(py)
            if available is None:
                skipped.append(f'{d}/{duan.name}')
                continue
            checked += 1
            missing = [n for n in exports if n not in available]
            if missing:
                problems.append({
                    'file': f'{d}/{duan.name}',
                    'exports': len(exports),
                    'missing': missing,
                })
            else:
                clean += 1

    print('=' * 62)
    print('段言清单一致性检查（.duan 导出名 ⇄ .py 实现）')
    print('=' * 62)
    print(f'.duan 总数: {total}   有 .py 配对且已检查: {checked}   全部匹配: {clean}')
    print(f'无 .py 配对（纯段言模块，跳过）: {len(no_py)}')
    if skipped:
        print(f'静态解析不可靠（star import 等）: {len(skipped)} -> {", ".join(skipped)}')
    print()

    if not problems:
        print('✅ 没有发现「清单声明了但实现里没有」的导出名。')
    else:
        miss_total = sum(len(p['missing']) for p in problems)
        print(f'❌ {len(problems)} 个文件共 {miss_total} 个导出名在 .py 里不存在：')
        print('   （这些名字一旦被 `从《模块》导入《名字》` 就会在运行期报 ImportError）')
        print()
        for p in problems:
            print(f'  ✗ {p["file"]}  ({len(p["missing"])}/{p["exports"]} 缺失)')
            for n in p['missing']:
                print(f'      - {n}')

    out = ROOT / 'tools' / 'manifest_check_report.json'
    out.write_text(
        json.dumps(
            {'checked': checked, 'clean': clean, 'problems': problems,
             'no_py': no_py, 'unreliable': skipped},
            ensure_ascii=False, indent=2),
        encoding='utf-8')
    print(f'\n明细已写入: {out.relative_to(ROOT)}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
