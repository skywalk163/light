import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'cli')

from light_parser_v3 import LightParser

code = """段落 求和 参数 甲 乙 
   返回 甲 加 乙。 
 结束"""

parser = LightParser()
module = parser.parse(code)

# 查看第一个语句（Paragraph）
para = module.statements[0]
print(f"段落名: {para.name}")
print(f"参数: {para.params}")
print(f"体语句数: {len(para.body)}")
for i, s in enumerate(para.body):
    print(f"  体[{i}]: type={type(s).__name__}, value={s}")

# 检查 ReturnStmt
for i, s in enumerate(para.body):
    if hasattr(s, 'value'):
        print(f"  ReturnStmt.value type: {type(s.value).__name__}")
        print(f"  ReturnStmt.value: {s.value}")