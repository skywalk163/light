"""
光明（Light）编程语言 - 语义识别器

实现决策34：主谓/谓宾语义识别

主谓结构：对象 操作 → 原地修改
  示例：列表排序 → 列表.sort()

谓宾结构：操作 对象 → 返回新对象
  示例：排序列表 → sorted(列表)

定语结构：包含"的" → 临时生成
  示例：排序后的列表 → sorted(列表)
"""

from typing import Optional, Tuple
from light_parser_v3 import *
from verb_info import supports_modify, supports_functional


# =============================================================================
# 语义结构类型
# =============================================================================

class SemanticType:
    """语义类型"""
    SUBJECT_VERB = 'subject_verb'      # 主谓结构（原地修改）
    VERB_OBJECT = 'verb_object'        # 谓宾结构（返回新对象）
    ATTRIBUTE = 'attribute'            # 定语结构（临时生成）
    FUNCTIONAL = 'functional'          # 函数式调用


# =============================================================================
# 语义识别器
# =============================================================================

class SemanticIdentifier:
    """语义识别器 - 识别主谓/谓宾语义"""
    
    def __init__(self, symbol_table: dict = None):
        """
        Args:
            symbol_table: 符号表（变量定义）
        """
        self.symbol_table = symbol_table or {}
    
    def identify(self, expr: ASTNode) -> Tuple[str, Optional[str]]:
        """
        识别表达式的语义类型
        
        Args:
            expr: AST节点
            
        Returns:
            (语义类型, 操作符/动词名称)
        """
        if isinstance(expr, BinaryOp):
            return self._identify_binary_op(expr)
        
        elif isinstance(expr, ParagraphCall):
            return self._identify_paragraph_call(expr)
        
        elif isinstance(expr, Identifier):
            return SemanticType.FUNCTIONAL, expr.name
        
        else:
            return SemanticType.FUNCTIONAL, None
    
    def _identify_binary_op(self, expr: BinaryOp) -> Tuple[str, Optional[str]]:
        """
        识别二元运算的语义类型
        
        示例：
        - 列表排序（主谓） → subject_verb
        - 排序列表（谓宾） → verb_object
        """
        left = expr.left
        right = expr.right
        operator = expr.operator
        
        # 检查是否是主谓结构
        if isinstance(left, Identifier) and isinstance(right, Identifier):
            # 左边是变量，右边是动词
            if left.name in self.symbol_table and supports_modify(right.name):
                return SemanticType.SUBJECT_VERB, right.name
            
            # 左边是动词，右边是变量
            if supports_functional(left.name) and right.name in self.symbol_table:
                return SemanticType.VERB_OBJECT, left.name
        
        return SemanticType.FUNCTIONAL, operator
    
    def _identify_paragraph_call(self, expr: ParagraphCall) -> Tuple[str, Optional[str]]:
        """
        识别段落调用的语义类型
        """
        verb = expr.name
        
        # 检查是否支持原地修改
        if supports_modify(verb):
            # 检查第一个参数是否是变量
            if expr.args and isinstance(expr.args[0], Identifier):
                if expr.args[0].name in self.symbol_table:
                    return SemanticType.SUBJECT_VERB, verb
        
        return SemanticType.VERB_OBJECT, verb


# =============================================================================
# Python代码生成辅助
# =============================================================================

def generate_python_code(semantic_type: str, verb: str, args: list, symbol_table: dict = None) -> str:
    """
    根据语义类型生成Python代码
    
    Args:
        semantic_type: 语义类型
        verb: 动词名称
        args: 参数列表
        symbol_table: 符号表
        
    Returns:
        Python代码字符串
    """
    from verb_info import get_python_mapping
    
    mapping = get_python_mapping(verb)
    if not mapping:
        # 默认函数调用
        return f"{verb}({', '.join(args)})"
    
    py_name, py_type = mapping
    
    if semantic_type == SemanticType.SUBJECT_VERB:
        # 主谓结构：原地修改
        if py_type == 'method':
            # object.method(args)
            obj = args[0] if args else 'obj'
            method_args = args[1:] if len(args) > 1 else []
            if method_args:
                return f"{obj}.{py_name}({', '.join(method_args)})"
            else:
                return f"{obj}.{py_name}()"
        else:
            # 函数式（但标记为原地修改）
            return f"{py_name}({', '.join(args)})"
    
    elif semantic_type == SemanticType.VERB_OBJECT:
        # 谓宾结构：返回新对象
        return f"{py_name}({', '.join(args)})"
    
    else:
        # 默认函数式
        return f"{py_name}({', '.join(args)})"


# =============================================================================
# 测试
# =============================================================================

if __name__ == '__main__':
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("语义识别器测试")
    print("=" * 60)
    
    # 创建符号表
    symbol_table = {'列表': 'list', '数据': 'list'}
    
    identifier = SemanticIdentifier(symbol_table)
    
    # 测试1：主谓结构
    print("\n--- 测试1: 主谓结构（原地修改） ---")
    expr1 = BinaryOp('排序', Identifier('列表'), None)
    semantic_type, verb = identifier.identify(expr1)
    print(f"表达式: 列表排序")
    print(f"语义类型: {semantic_type}")
    print(f"动词: {verb}")
    python_code = generate_python_code(semantic_type, '排序', ['列表'], symbol_table)
    print(f"Python代码: {python_code}")
    
    # 测试2：谓宾结构
    print("\n--- 测试2: 谓宾结构（返回新对象） ---")
    expr2 = BinaryOp('排序', None, Identifier('列表'))
    semantic_type, verb = identifier.identify(expr2)
    print(f"表达式: 排序列表")
    print(f"语义类型: {semantic_type}")
    print(f"动词: {verb}")
    python_code = generate_python_code(semantic_type, '排序', ['列表'], symbol_table)
    print(f"Python代码: {python_code}")
    
    # 测试3：段落调用
    print("\n--- 测试3: 段落调用 ---")
    expr3 = ParagraphCall('排序', [Identifier('列表')])
    semantic_type, verb = identifier.identify(expr3)
    print(f"表达式: 《排序》(列表)")
    print(f"语义类型: {semantic_type}")
    print(f"动词: {verb}")
    python_code = generate_python_code(semantic_type, '排序', ['列表'], symbol_table)
    print(f"Python代码: {python_code}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
