"""测试 bootstrap/token.py 生成的函数"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'stdlib'))
import builtins as _light_builtin

# 读取生成的代码并执行
with open(os.path.join(os.path.dirname(__file__), 'token.py'), 'r', encoding='utf-8') as f:
    code = f.read()
# 提取 __all__ 之后的函数定义部分
exec(code.split('__all__')[1])

# 测试创建令牌
tok = 创建令牌('标识符', '甲', 1, 5)
print('创建令牌:', tok)
assert tok['种别'] == '标识符', f"种别错误: {tok['种别']}"
assert tok['值'] == '甲', f"值错误: {tok['值']}"
assert tok['横'] == 1, f"横错误: {tok['横']}"
assert tok['纵'] == 5, f"纵错误: {tok['纵']}"
print('✓ 创建令牌测试通过')

# 测试关键字检查
assert 是关键字('定义') == True, "'定义'应是关键字"
assert 是关键字('如果') == True, "'如果'应是关键字"
assert 是关键字('变量') == False, "'变量'不应是关键字"
print('✓ 关键字检查测试通过')

print('所有测试通过!')