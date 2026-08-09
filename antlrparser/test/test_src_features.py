"""测试src后端新增特性解析（不含代码生成）"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from light_parser_v3 import LightParser, DictLiteral, DictComprehension, DestructuringAssignment, WithStmt, DecoratorDefinition, Paragraph


def test_parse(name: str, code: str):
    """测试解析"""
    parser = LightParser()
    try:
        module = parser.parse(code)
        print(f"[OK]  {name}: 解析成功 ({len(module.statements)} 个语句)")
        for i, stmt in enumerate(module.statements):
            print(f"      语句{i+1}: {type(stmt).__name__}: {stmt}")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")


# 测试1: with语句
test_parse("with语句", """使用 文件 为 f：
  打印 f。
结束。
""")

# 测试2: 装饰器（段落形式）
test_parse("装饰器(v2)", """@日志 标注 段落 测试 参数 甲：
  打印 甲。
结束。
""")

# 测试3: 装饰器（书名号形式）
test_parse("装饰器(v1)", """@日志 标注 《计算》段(甲, 乙) -> 数：
  返回 甲加乙。
结束。
""")

# 测试4: 字典推导
test_parse("字典推导", """定义 平方表为【甲: 甲乘甲 遍历 数 之 列表】。
""")

# 测试5: 字典字面量
test_parse("字典字面量", """定义 数据对为【"甲": 1, "乙": 2】。
""")

# 测试6: 解构赋值
test_parse("解构赋值", """设（甲，乙）为 元组。
""")

print("\n测试完成")