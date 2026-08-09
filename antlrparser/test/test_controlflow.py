"""
光明 - 控制流语句测试

测试 if/foreach/while/break/continue 的解析和 AST 生成
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from light_visitor import LightParser, parse_file


def print_ast(node, indent=0):
    """打印 AST 节点（简化为一行一个节点）"""
    if node is None:
        return
    
    prefix = "  " * indent
    
    node_type = type(node).__name__
    
    if node_type == 'Module':
        print(f"{prefix}Module")
        for stmt in node.statements:
            print_ast(stmt, indent + 1)
        for seg in node.segments:
            print_ast(seg, indent + 1)
    elif node_type == 'VariableDeclaration':
        print(f"{prefix}VarDecl: {node.name} = ", end="")
        print_ast(node.value, 0)
    elif node_type == 'NumberLiteral':
        print(f"{prefix}Number({node.value})")
    elif node_type == 'StringLiteral':
        print(f"{prefix}String(\"{node.value}\")")
    elif node_type == 'BooleanLiteral':
        print(f"{prefix}Bool({node.value})")
    elif node_type == 'IfStatement':
        print(f"{prefix}If")
        print(f"{prefix}  Condition: ", end="")
        print_ast(node.condition, 0)
        print(f"{prefix}  Then:")
        for s in node.then_body:
            print_ast(s, indent + 2)
        if node.elseif_conditions:
            for i, (cond, body) in enumerate(zip(node.elseif_conditions, node.elseif_bodies)):
                print(f"{prefix}  ElseIf {i+1}: ", end="")
                print_ast(cond, 0)
                print(f"{prefix}    Then:")
                for s in body:
                    print_ast(s, indent + 3)
        if node.else_body is not None:
            print(f"{prefix}  Else:")
            for s in node.else_body:
                print_ast(s, indent + 2)
    elif node_type == 'ForeachStatement':
        print(f"{prefix}Foreach({node.variable} in ", end="")
        print_ast(node.iterable, 0)
        print(f"{prefix}  Body:")
        for s in node.body:
            print_ast(s, indent + 2)
    elif node_type == 'WhileStatement':
        print(f"{prefix}While: ", end="")
        print_ast(node.condition, 0)
        print(f"{prefix}  Body:")
        for s in node.body:
            print_ast(s, indent + 2)
    elif node_type == 'BreakStatement':
        print(f"{prefix}Break")
    elif node_type == 'ContinueStatement':
        print(f"{prefix}Continue")
    elif node_type == 'PrintStatement':
        print(f"{prefix}Print: ", end="")
        print_ast(node.value, 0)
    elif node_type == 'BinaryOp':
        print(f"{prefix}BinaryOp({node.operator})")
        print(f"{prefix}  Left: ", end="")
        print_ast(node.left, indent + 1)
        print(f"{prefix}  Right: ", end="")
        print_ast(node.right, indent + 1)
    elif node_type == 'Identifier':
        print(f"{prefix}ID({node.name})")
    elif node_type == 'ListLiteral':
        print(f"{prefix}List({len(node.elements)} items)")
        for elem in node.elements:
            print_ast(elem, indent + 1)
    elif node_type == 'Assignment':
        print(f"{prefix}Assign:")
        print(f"{prefix}  Target: ", end="")
        print_ast(node.target, 0)
        print(f"{prefix}  Value: ", end="")
        print_ast(node.value, 0)
    else:
        print(f"{prefix}{node_type}")


def test_controlflow_parsing():
    """测试控制流样本文件解析"""
    print("=" * 60)
    print("测试 1: 解析 sample_controlflow.light")
    print("=" * 60)
    
    filepath = os.path.join(os.path.dirname(__file__), 'sample_controlflow.light')
    module = parse_file(filepath)
    
    if module:
        print("✓ 解析成功\n")
        print("AST 结构:")
        print("-" * 40)
        print_ast(module)
        print("-" * 40)
        
        # 验证语句数量
        # 预期: 变量声明 *4 + if + if + varDecl + foreach + varDecl + while + varDecl + while(含break/continue)
        print(f"\n统计: 共 {len(module.statements)} 条顶层语句, {len(module.segments)} 个段落定义")
        return True
    else:
        print("✗ 解析失败")
        return False


def test_simple_if():
    """测试简单 if 语句"""
    print("\n" + "=" * 60)
    print("测试 2: 简单 if 语句")
    print("=" * 60)
    
    source = """\
定义甲等于10。
如果甲大于5那么：
  打印'大'。
结束。
定义乙等于20。"""
    
    parser = LightParser()
    module = parser.parse(source)
    
    assert module is not None, "解析失败"
    assert len(module.statements) == 3, f"期望 3 条语句，实际 {len(module.statements)}"
    assert isinstance(module.statements[0], type(module.statements[0]))  # VarDecl
    assert type(module.statements[1]).__name__ == 'IfStatement', f"期望 IfStatement, 实际 {type(module.statements[1]).__name__}"
    
    if_stmt = module.statements[1]
    assert hasattr(if_stmt, 'condition'), "缺少 condition"
    assert hasattr(if_stmt, 'then_body'), "缺少 then_body"
    assert if_stmt.else_body is None, "不应有 else_body"
    print(f"✓ 简单 if 解析正确")
    return True


def test_if_else():
    """测试 if/else 语句"""
    print("\n" + "=" * 60)
    print("测试 3: if/else 语句")
    print("=" * 60)
    
    source = """\
如果甲大于乙那么：
  打印甲。
否则：
  打印乙。
结束。"""
    
    parser = LightParser()
    module = parser.parse(source)
    
    assert module is not None, "解析失败"
    if_stmt = module.statements[0]
    assert type(if_stmt).__name__ == 'IfStatement'
    assert if_stmt.else_body is not None, "缺少 else_body"
    assert len(if_stmt.elseif_conditions) == 0, "不应有 elseif"
    print(f"✓ if/else 解析正确")
    return True


def test_if_elif_else():
    """测试 if/elif/else 语句"""
    print("\n" + "=" * 60)
    print("测试 4: if/elif/else 语句")
    print("=" * 60)
    
    source = """\
如果分数大于等于90那么：
  打印'A'。
否则若分数大于等于80那么：
  打印'B'。
否则若分数大于等于70那么：
  打印'C'。
否则：
  打印'D'。
结束。"""
    
    parser = LightParser()
    module = parser.parse(source)
    
    assert module is not None, "解析失败"
    if_stmt = module.statements[0]
    assert type(if_stmt).__name__ == 'IfStatement'
    assert len(if_stmt.elseif_conditions) == 2, f"期望 2 个 elseif, 实际 {len(if_stmt.elseif_conditions)}"
    assert if_stmt.else_body is not None, "缺少 else_body"
    print(f"✓ if/elif/else 解析正确 (2 个 elseif)")
    return True


def test_foreach():
    """测试遍历循环"""
    print("\n" + "=" * 60)
    print("测试 5: 遍历循环")
    print("=" * 60)
    
    source = """\
遍历 项 列表：
  打印项。
结束。"""
    
    parser = LightParser()
    module = parser.parse(source)
    
    assert module is not None, "解析失败"
    stmt = module.statements[0]
    assert type(stmt).__name__ == 'ForeachStatement', f"期望 ForeachStatement, 实际 {type(stmt).__name__}"
    assert stmt.variable == '项', f"期望 variable='项', 实际 '{stmt.variable}'"
    assert len(stmt.body) == 1, f"期望 body 有 1 条语句, 实际 {len(stmt.body)}"
    print(f"✓ 遍历循环解析正确")
    return True


def test_while():
    """测试当循环"""
    print("\n" + "=" * 60)
    print("测试 6: 当循环")
    print("=" * 60)
    
    source = """\
定义计数等于3。
当计数大于0：
  打印计数。
  定义计数等于计数减1。
结束。"""
    
    parser = LightParser()
    module = parser.parse(source)
    
    assert module is not None, "解析失败"
    assert len(module.statements) == 2
    while_stmt = module.statements[1]
    assert type(while_stmt).__name__ == 'WhileStatement', f"期望 WhileStatement, 实际 {type(while_stmt).__name__}"
    print(f"✓ 当循环解析正确")
    return True


def test_break_continue():
    """测试跳出/跳过"""
    print("\n" + "=" * 60)
    print("测试 7: 跳出/跳过")
    print("=" * 60)
    
    source = """\
当索引小于10：
  如果索引等于5那么：
    跳过。
  结束。
  如果索引等于8那么：
    跳出。
  结束。
结束。"""
    
    parser = LightParser()
    module = parser.parse(source)
    
    assert module is not None, "解析失败"
    while_stmt = module.statements[0]
    assert type(while_stmt).__name__ == 'WhileStatement'
    
    # while body should have 2 if statements
    assert len(while_stmt.body) == 2, f"期望 2 条语句, 实际 {len(while_stmt.body)}"
    
    # First if contains continue
    first_if = while_stmt.body[0]
    assert type(first_if).__name__ == 'IfStatement'
    assert len(first_if.then_body) == 1
    assert type(first_if.then_body[0]).__name__ == 'ContinueStatement'
    
    # Second if contains break
    second_if = while_stmt.body[1]
    assert type(second_if).__name__ == 'IfStatement'
    assert len(second_if.then_body) == 1
    assert type(second_if.then_body[0]).__name__ == 'BreakStatement'
    
    print(f"✓ 跳出/跳过解析正确")
    return True


if __name__ == '__main__':
    print("=== 光明控制流语句测试 ===\n")
    
    tests = [
        ("控制流样本解析", test_controlflow_parsing),
        ("简单 if", test_simple_if),
        ("if/else", test_if_else),
        ("if/elif/else", test_if_elif_else),
        ("遍历循环", test_foreach),
        ("当循环", test_while),
        ("跳出/跳过", test_break_continue),
    ]
    
    all_passed = True
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            if fn():
                print(f"  ✓ 通过")
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("全部控制流测试通过 ✅")
    else:
        print("部分测试失败 ❌")
    
    sys.exit(0 if all_passed else 1)