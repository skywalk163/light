# -*- coding: utf-8 -*-
"""
光明编译器 - 将光明代码编译为Python代码（支持缩进）
"""

import sys
import os

def compile_light_to_python(source_code):
    """将光明代码编译为Python代码"""
    lines = source_code.split('\n')
    python_lines = []
    
    # 添加必要的导入
    python_lines.append('import json')
    python_lines.append('import os')
    python_lines.append('import time')
    python_lines.append('')
    
    current_indent = 0
    
    for line in lines:
        # 跳过空行
        if line.strip() == '':
            python_lines.append('')
            continue
        
        # 跳过注释
        if line.strip().startswith('#'):
            python_lines.append('# ' + line[1:].strip() if line.startswith('#') else line)
            continue
        
        # 计算当前缩进级别（光明使用2个空格作为缩进）
        leading_spaces = len(line) - len(line.lstrip())
        indent_level = leading_spaces // 2
        
        # 确定缩进字符串
        indent_str = '    ' * indent_level
        
        # 获取去除缩进后的内容
        content = line.strip()
        
        # 变量声明: 定义 X 等于 Y -> X = Y
        if content.startswith('定义') and '等于' in content:
            after_def = content[2:].strip()
            idx = after_def.find('等于')
            if idx != -1:
                var_name = after_def[:idx].strip()
                var_value = after_def[idx+2:].strip()
                # 只在变量值中替换中文运算符
                var_value = var_value.replace('加', ' + ')
                var_value = var_value.replace('减', ' - ')
                var_value = var_value.replace('乘', ' * ')
                var_value = var_value.replace('除', ' / ')
                content = f"{var_name} = {var_value}"
        
        # 段落定义: 《段名》段(...) -> def 段名(...):
        if '》段(' in content:
            content = content.replace('《', 'def ')
            content = content.replace('》段', '')
        
        # 段落调用: 《段名》(...) -> 段名(...)
        elif '》(' in content:
            content = content.replace('《', '')
            content = content.replace('》', '')
        
        # 导入语句
        content = content.replace('导入', 'import')
        
        # 条件语句 - 注意顺序很重要
        # 先替换"否则如果"，再替换单独的"如果"和"否则"
        content = content.replace('否则如果', 'elif ')
        content = content.replace('如果', 'if ')
        content = content.replace('那么:', ':')
        content = content.replace('否则:', 'else:')
        
        # 循环语句
        content = content.replace('遍历', 'for ')
        content = content.replace('在', ' in ')
        content = content.replace('当', 'while ')
        
        # 结束关键字
        content = content.replace('结束。', '')
        content = content.replace('结束', '')
        
        # 打印语句
        content = content.replace('打印', 'print')
        
        # 真/假
        content = content.replace('真', 'True')
        content = content.replace('假', 'False')
        
        # 返回语句
        content = content.replace('返回', 'return')
        
        # 移除中文句号
        content = content.replace('。', '')
        
        # 相等比较: 等于 -> ==
        content = content.replace('等于', '==')
        
        # 移除多余的空格
        content = ' '.join(content.split())
        
        # 添加缩进
        python_lines.append(indent_str + content)
    
    return '\n'.join(python_lines)

def main():
    if len(sys.argv) < 2:
        print("用法: python simple_compiler.py <source.light> [output.py]")
        sys.exit(1)
    
    source_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 读取源文件
    with open(source_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    print(f"读取文件: {source_path}")
    print(f"代码长度: {len(source_code)} 字符")
    
    # 编译
    python_code = compile_light_to_python(source_code)
    print("编译完成!")
    
    # 写入输出文件
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(python_code)
        print(f"输出文件: {output_path}")
    else:
        # 输出前50行
        print("\n生成的Python代码（前50行）:")
        print("=" * 60)
        for i, line in enumerate(python_code.split('\n')[:50]):
            print(f"{i+1:4d}: {line}")
        
        remaining = len(python_code.split('\n')) - 50
        if remaining > 0:
            print(f"... ({remaining} 行省略)")
    
    return python_code

if __name__ == '__main__':
    main()
