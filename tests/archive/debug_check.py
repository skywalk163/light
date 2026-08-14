import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

with open(os.path.join(os.path.dirname(__file__), 'examples', 'advanced.light'), 'r', encoding='utf-8') as f:
    source = f.read()

parser = LightParser()
module = parser.parse(source)

# Find the 评级 function and check the comparison nodes
for stmt in module.statements:
    if hasattr(stmt, 'name') and stmt.name == '评级':
        for body_stmt in stmt.body:
            if hasattr(body_stmt, 'condition') and hasattr(body_stmt.condition, 'right'):
                print("Condition type:", type(body_stmt.condition).__name__)
                print("Right value:", body_stmt.condition.right.value, type(body_stmt.condition.right.value))
                print("Right repr:", repr(body_stmt.condition.right))
                print("Right is NumberLiteral:", type(body_stmt.condition.right).__name__)

generator = PythonCodeGenerator()
code = generator.generate(module)
# Print just the 评级 function
in_func = False
for line in code.split('\n'):
    if 'def 评级' in line:
        in_func = True
    if in_func:
        print(line)
    if in_func and line.strip() == '' and 'def ' not in line and 'return' not in line:
        if line.strip() == '':
            pass  # end of function