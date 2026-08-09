#!/usr/bin/env python3
"""
使用Python subprocess调用ANTLR4生成解析器
"""
import subprocess
import sys
from pathlib import Path

def generate_parser():
    """生成ANTLR解析器"""
    antlr_dir = Path(__file__).parent.parent / 'antlrparser'
    
    # 尝试方法1: 使用系统Java + 下载的jar
    jar_file = Path(__file__).parent.parent / 'antlr-4.13.1-complete.jar'
    
    if jar_file.exists():
        # 检查文件大小
        size = jar_file.stat().st_size
        if size < 1000000:  # 小于1MB，文件可能损坏
            print(f'[WARN] jar文件可能损坏: {size} bytes')
            print('尝试重新下载...')
            import urllib.request
            url = 'https://www.antlr.org/download/antlr-4.13.1-complete.jar'
            try:
                urllib.request.urlretrieve(url, str(jar_file))
                print(f'[OK] 下载成功: {jar_file.stat().st_size} bytes')
            except Exception as e:
                print(f'[FAIL] 下载失败: {e}')
                return False
    
    # 尝试方法2: 使用pip安装的antlr4-runtime
    try:
        from antlr4_tool_runner import download_antlr4, antlr4_jar
        print('[INFO] 使用antlr4-tools下载ANTLR jar...')
        jar_path = download_antlr4('4.13.1')
        print(f'[OK] ANTLR jar已下载: {jar_path}')
        
        # 生成词法分析器
        print('\n[STEP 1] 生成词法分析器...')
        cmd = [
            sys.executable, '-m', 'antlr4_tool_runner',
            '-Dlanguage=Python3', '-visitor', '-no-listener',
            str(antlr_dir / 'LightLangLexer.g4')
        ]
        result = subprocess.run(cmd, cwd=antlr_dir, capture_output=True, text=True)
        if result.returncode == 0:
            print('[OK] 词法分析器生成成功')
        else:
            print(f'[FAIL] 词法分析器生成失败:\n{result.stderr}')
            return False
        
        # 生成语法分析器
        print('\n[STEP 2] 生成语法分析器...')
        cmd = [
            sys.executable, '-m', 'antlr4_tool_runner',
            '-Dlanguage=Python3', '-visitor', '-no-listener',
            str(antlr_dir / 'LightLangParser.g4')
        ]
        result = subprocess.run(cmd, cwd=antlr_dir, capture_output=True, text=True)
        if result.returncode == 0:
            print('[OK] 语法分析器生成成功')
        else:
            print(f'[FAIL] 语法分析器生成失败:\n{result.stderr}')
            return False
        
        return True
        
    except ImportError:
        print('[WARN] antlr4_tool_runner不可用')
    
    # 方法3: 直接使用Java命令
    print('\n[INFO] 尝试使用Java命令...')
    
    if not jar_file.exists():
        print('[FAIL] jar文件不存在')
        return False
    
    print('\n[STEP 1] 生成词法分析器...')
    cmd = ['java', '-jar', str(jar_file), '-Dlanguage=Python3', '-visitor', '-no-listener', 'LightLangLexer.g4']
    result = subprocess.run(cmd, cwd=antlr_dir, capture_output=True, text=True)
    if result.returncode == 0:
        print('[OK] 词法分析器生成成功')
    else:
        print(f'[FAIL] 词法分析器生成失败:\n{result.stderr}')
        return False
    
    print('\n[STEP 2] 生成语法分析器...')
    cmd = ['java', '-jar', str(jar_file), '-Dlanguage=Python3', '-visitor', '-no-listener', 'LightLangParser.g4']
    result = subprocess.run(cmd, cwd=antlr_dir, capture_output=True, text=True)
    if result.returncode == 0:
        print('[OK] 语法分析器生成成功')
    else:
        print(f'[FAIL] 语法分析器生成失败:\n{result.stderr}')
        return False
    
    return True

if __name__ == '__main__':
    print('光明编程语言 - ANTLR解析器生成')
    print('=' * 60)
    
    if generate_parser():
        print('\n[SUCCESS] 所有解析器代码生成完成！')
        print('\n下一步:')
        print('  python compile.py test_unified.light')
    else:
        print('\n[FAILED] 解析器生成失败')
        print('\n备选方案:')
        print('  1. 使用现有的手写解析器: python compile.py test_unified.light')
        print('  2. 手动下载ANTLR jar: https://www.antlr.org/download/')
        sys.exit(1)
