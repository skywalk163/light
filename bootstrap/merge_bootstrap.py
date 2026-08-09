"""重新合并 bootstrap_v3.light"""
import os

bootstrap_dir = os.path.dirname(os.path.abspath(__file__))

modules = ['token.light', 'light_ast.light', 'lexer.light', 'parser.light', 'codegen.light', 'compiler.light', 'main.light']

output = """# bootstrap_v3.light - v3.2 自举编译器（合并版）
# 由 merge_bootstrap.py 自动生成

"""

for module in modules:
    path = os.path.join(bootstrap_dir, module)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 去掉导入和导出语句
    lines = content.split('\n')
    filtered = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('导入 ') or stripped.startswith('从 '):
            continue
        if stripped.startswith('导出 '):
            continue
        filtered.append(line)
    
    output += f"\n# ===== {module} =====\n"
    output += '\n'.join(filtered)
    output += '\n'

out_path = os.path.join(bootstrap_dir, 'bootstrap_v3.light')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"已生成: {out_path} ({len(output)} 字符)")
