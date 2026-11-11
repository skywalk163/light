# -*- coding: utf-8 -*-
"""扫描 stdlib/*.light 的「导出」清单，生成 src/stdlib_name_map.py。

生成物：NAME_TO_MODULE: dict[str, str] —— 未导入即调用的 stdlib 函数名 → 所属模块名。
过滤规则：只收「必须显式导入」的名字；已在编译器 builtin_map 里的全局内置名不收
（否则会把「忘打括号」误报成缺导入）。

用法：
    python scripts/gen_stdlib_name_map.py           # 生成/刷新 src/stdlib_name_map.py
    python scripts/gen_stdlib_name_map.py --check   # CI 校验：不一致则 rc=1
"""

import os
import re
import sys

# 项目根目录（本脚本在 scripts/ 下）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STDLIB_DIR = os.path.join(ROOT, 'stdlib')
SRC_DIR = os.path.join(ROOT, 'src')
OUTPUT_PATH = os.path.join(SRC_DIR, 'stdlib_name_map.py')

# 导出行格式：导出 名字1 名字2 ... 名字N。
# 名字之间用空格分隔，行尾以「。」结束。
_EXPORT_RE = re.compile(r'^导出\s+(.+?)[。；]?\s*$')


def _get_builtin_names() -> set:
    """从 code_generator 的 builtin_map 提取全局内置名集合。

    这些名字在编译器层面已映射到 _light_builtin.X 或 Python 内建，
    裸调用不会 NameError，因此不需要「缺导入」提示。
    """
    builtin_names = set()
    try:
        sys.path.insert(0, SRC_DIR)
        from code_generator import PythonCodeGenerator
        gen = PythonCodeGenerator()
        builtin_names = set(gen.builtin_map.keys())
    except Exception:
        # 提取失败时回退到硬编码最小集（保证脚本本身不崩）
        # 这些是最容易误判的高频内置名
        builtin_names = {
            '打印', '输入', '长', '长度', '整数', '文本', '字符串', '浮点数',
            '列表', '字典', '集合', '元组', '布尔', '范围', '求和', '最大值',
            '最小值', '绝对值', '平方根', '随机', '排序', '反转', '追加',
            '删除', '弹出', '连接路径', '读取文件', '写入文件', '文件存在',
            '目录存在', '退出程序', '当前目录', '环境变量',
        }
    return builtin_names


def scan_exports() -> dict:
    """扫描 stdlib/*.light，返回 {导出名: 模块名}。"""
    name_to_module = {}
    if not os.path.isdir(STDLIB_DIR):
        print(f'错误: stdlib 目录不存在: {STDLIB_DIR}', file=sys.stderr)
        sys.exit(1)

    for fname in sorted(os.listdir(STDLIB_DIR)):
        if not fname.endswith('.light'):
            continue
        module_name = fname[:-len('.light')]
        fpath = os.path.join(STDLIB_DIR, fname)
        try:
            with open(fpath, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith('导出'):
                        continue
                    m = _EXPORT_RE.match(line)
                    if not m:
                        continue
                    names_str = m.group(1)
                    # 按空白分割名字
                    for name in names_str.split():
                        name = name.strip().rstrip('。；，,')
                        if name and name not in name_to_module:
                            name_to_module[name] = module_name
        except Exception as e:
            print(f'警告: 读取 {fname} 失败: {e}', file=sys.stderr)
    return name_to_module


def generate_map() -> dict:
    """生成过滤后的 NAME_TO_MODULE 映射。"""
    raw = scan_exports()
    builtins = _get_builtin_names()

    # 过滤：排除全局内置名（裸调用不会 NameError）
    filtered = {}
    for name, module in sorted(raw.items()):
        if name in builtins:
            continue
        filtered[name] = module
    return filtered


def render_py(names: dict) -> str:
    """渲染为 Python 模块源码。"""
    lines = [
        '# -*- coding: utf-8 -*-',
        '# 本文件由 scripts/gen_stdlib_name_map.py 自动生成，请勿手动修改。',
        '# 修改导出清单请编辑 stdlib/*.light 的「导出 ...」行，然后重新运行生成脚本。',
        '',
        '# stdlib 导出名 → 模块名映射表。',
        '# 只收录「必须显式导入」的名字；全局内置（builtins）已过滤。',
        'NAME_TO_MODULE: dict = {',
    ]
    for name in sorted(names.keys()):
        module = names[name]
        lines.append(f"    {name!r}: {module!r},")
    lines.append('}')
    lines.append('')
    lines.append(f'# 共 {len(names)} 条')
    lines.append('')
    return '\n'.join(lines)


def main():
    check_only = '--check' in sys.argv
    names = generate_map()
    content = render_py(names)

    if check_only:
        if not os.path.isfile(OUTPUT_PATH):
            print(f'--check: {OUTPUT_PATH} 不存在，需要生成。')
            sys.exit(1)
        with open(OUTPUT_PATH, encoding='utf-8') as f:
            existing = f.read()
        if existing.strip() == content.strip():
            print(f'--check: OK，{len(names)} 条映射与 stdlib 导出表一致。')
            sys.exit(0)
        else:
            # 打印 diff 摘要
            print(f'--check: 不一致！现有文件需要重新生成。')
            # 找出差异
            import ast
            try:
                old_ast = ast.parse(existing)
                old_dict = {}
                for node in ast.walk(old_ast):
                    if isinstance(node, ast.Dict):
                        for k, v in zip(node.keys, node.values):
                            if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                                old_dict[k.value] = v.value
                        break
                new_keys = set(names.keys())
                old_keys = set(old_dict.keys())
                added = new_keys - old_keys
                removed = old_keys - new_keys
                if added:
                    print(f'  新增: {sorted(added)}')
                if removed:
                    print(f'  移除: {sorted(removed)}')
                # 值变更
                changed = [k for k in new_keys & old_keys if old_dict[k] != names[k]]
                if changed:
                    print(f'  变更模块: {sorted(changed)}')
            except Exception:
                pass
            sys.exit(1)
    else:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'已生成 {OUTPUT_PATH}（{len(names)} 条映射）')


if __name__ == '__main__':
    main()
