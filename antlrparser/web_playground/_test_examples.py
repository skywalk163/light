"""测试所有内置示例代码都能正确解析和执行"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import BUILTIN_EXAMPLES
from light_interpreter import run_source

passed = 0
failed = 0

for ex in BUILTIN_EXAMPLES:
    try:
        interp = run_source(ex['code'])
        output = interp.get_output()
        if not output:
            output = '(无输出)'
        print(f'  ✅ {ex["id"]}: {ex["title"]}')
        print(f'     输出: {output[:80]}')
        passed += 1
    except Exception as e:
        print(f'  ❌ {ex["id"]}: {ex["title"]}')
        print(f'     错误: {e}')
        failed += 1

print(f'\n结果: {passed} 通过, {failed} 失败')