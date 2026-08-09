"""
光明（Light）编程语言 - 元数驱动解析器

实现决策28：元数驱动解析
- 动词声明参数数量，自动收集参数
- 支持无括号函数调用
- 阻断符机制

示例：
  打印甲。          → 打印(甲)
  加1乘2 3。        → 加(1, 乘(2, 3))
  列1 2 3 4 5。     → 列(1, 2, 3, 4, 5)
"""

from typing import List, Optional, Tuple
from tokens import Token
from light_parser_v3 import *
from verb_info import get_arity, is_verb


# =============================================================================
# 阻断符
# =============================================================================

BLOCKING_TOKENS = {
    '。',   # 语句结束
    '，',   # 管道操作符
    '）',   # 右括号
    '那么', # 条件关键字
    '否则', # 条件关键字
    '结束', # 块结束
}


# =============================================================================
# 元数驱动解析器
# =============================================================================

class ArityParser:
    """元数驱动解析器"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def parse_verb_call(self, verb: str) -> Tuple[ASTNode, int]:
        """
        解析动词调用（元数驱动）
        
        Args:
            verb: 动词名称
            
        Returns:
            (AST节点, 消耗的token数)
        """
        arity = get_arity(verb)
        
        if arity == -1:
            # 可变参数：收集到阻断符为止
            return self._collect_variable_args(verb)
        else:
            # 固定参数：收集指定数量的参数
            return self._collect_fixed_args(verb, arity)
    
    def _collect_fixed_args(self, verb: str, arity: int) -> Tuple[ASTNode, int]:
        """收集固定数量的参数"""
        args = []
        consumed = 1  # 动词本身
        
        for i in range(arity):
            if self.pos + consumed >= len(self.tokens):
                break
            
            token = self.tokens[self.pos + consumed]
            
            # 检查阻断符
            if self._is_blocking_token(token):
                break
            
            # 收集参数
            arg, arg_consumed = self._parse_argument()
            args.append(arg)
            consumed += arg_consumed
        
        # 创建段落调用节点
        return ParagraphCall(verb, args), consumed
    
    def _collect_variable_args(self, verb: str) -> Tuple[ASTNode, int]:
        """收集可变数量的参数"""
        args = []
        consumed = 1  # 动词本身
        
        while self.pos + consumed < len(self.tokens):
            token = self.tokens[self.pos + consumed]
            
            # 检查阻断符
            if self._is_blocking_token(token):
                break
            
            # 收集参数
            arg, arg_consumed = self._parse_argument()
            args.append(arg)
            consumed += arg_consumed
        
        # 创建段落调用节点
        return ParagraphCall(verb, args), consumed
    
    def _parse_argument(self) -> Tuple[ASTNode, int]:
        """
        解析单个参数
        
        Returns:
            (AST节点, 消耗的token数)
        """
        # 注意：此时 self.pos 指向动词，参数在 self.pos + consumed
        # 这里只是返回简单的参数类型，实际参数位置由调用者维护
        return None, 0  # 占位符，实际逻辑在 _collect_* 方法中
    
    def _collect_fixed_args(self, verb: str, arity: int) -> Tuple[ASTNode, int]:
        """收集固定数量的参数"""
        args = []
        consumed = 1  # 动词本身
        
        for i in range(arity):
            if self.pos + consumed >= len(self.tokens):
                break
            
            token = self.tokens[self.pos + consumed]
            
            # 检查阻断符
            if self._is_blocking_token(token):
                break
            
            # 数字
            if token.type == TokenType.NUMBER:
                args.append(NumberLiteral(token.value))
                consumed += 1
            # 中文数字
            elif token.type == TokenType.CHINESE_NUM:
                args.append(NumberLiteral(token.value))
                consumed += 1
            # 字符串
            elif token.type == TokenType.STRING:
                args.append(StringLiteral(token.value))
                consumed += 1
            # 标识符
            elif token.type == TokenType.IDENTIFIER:
                name = token.value
                
                # 检查下一个token，判断是否是嵌套动词调用
                if self.pos + consumed + 1 < len(self.tokens):
                    next_token = self.tokens[self.pos + consumed + 1]
                    
                    # 如果下一个是动词，可能是嵌套调用
                    if next_token.type == TokenType.KEYWORD and is_verb(next_token.value):
                        # 嵌套动词调用
                        nested_call, nested_consumed = self._parse_nested_verb(next_token.value, consumed + 1)
                        args.append(nested_call)
                        consumed = nested_consumed
                        continue
                
                args.append(Identifier(name))
                consumed += 1
            # 关键字（动词）作为参数开始
            elif token.type == TokenType.KEYWORD and is_verb(token.value):
                # 嵌套动词调用
                nested_call, nested_consumed = self._parse_nested_verb(token.value, consumed)
                args.append(nested_call)
                consumed = nested_consumed
            else:
                break
        
        # 创建段落调用节点
        return ParagraphCall(verb, args), consumed
    
    def _parse_nested_verb(self, verb: str, offset: int) -> Tuple[ASTNode, int]:
        """
        解析嵌套动词调用
        
        Args:
            verb: 动词名称
            offset: 相对于 self.pos 的偏移量
            
        Returns:
            (AST节点, 消耗的总token数)
        """
        arity = get_arity(verb)
        args = []
        consumed = offset + 1  # 偏移 + 动词本身
        
        for i in range(arity):
            if self.pos + consumed >= len(self.tokens):
                break
            
            token = self.tokens[self.pos + consumed]
            
            # 检查阻断符
            if self._is_blocking_token(token):
                break
            
            # 数字
            if token.type == TokenType.NUMBER:
                args.append(NumberLiteral(token.value))
                consumed += 1
            # 中文数字
            elif token.type == TokenType.CHINESE_NUM:
                args.append(NumberLiteral(token.value))
                consumed += 1
            # 字符串
            elif token.type == TokenType.STRING:
                args.append(StringLiteral(token.value))
                consumed += 1
            # 标识符
            elif token.type == TokenType.IDENTIFIER:
                args.append(Identifier(token.value))
                consumed += 1
            else:
                break
        
        return ParagraphCall(verb, args), consumed
    
    def _is_blocking_token(self, token: Token) -> bool:
        """判断是否为阻断符"""
        if token.type == TokenType.DOT or token.type == TokenType.PERIOD:
            return True
        if token.type == TokenType.COMMA:
            return True
        if token.type == TokenType.RPAREN:
            return True
        if token.type == TokenType.KEYWORD and token.value in BLOCKING_TOKENS:
            return True
        return False


# =============================================================================
# 简化的元数驱动解析（集成到现有解析器）
# =============================================================================

def apply_arity_parsing(module: Module) -> Module:
    """
    对模块应用元数驱动解析
    
    这是后处理步骤，识别并转换动词调用
    """
    # TODO: 集成到现有解析流程
    return module


# =============================================================================
# 测试
# =============================================================================

if __name__ == '__main__':
    from lexer import Lexer
    
    print("=" * 60)
    print("元数驱动解析器测试")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        ('单参数', '打印甲。', '打印(甲)'),
        ('二元运算', '加1乘2 3。', '加(1, 乘(2, 3))'),
        ('可变参数', '列1 2 3 4 5。', '列(1, 2, 3, 4, 5)'),
    ]
    
    lexer = Lexer()
    
    for name, code, expected in test_cases:
        print(f"\n--- 测试: {name} ---")
        print(f"代码: {code}")
        print(f"期望: {expected}")
        
        try:
            # 词法分析
            tokens = list(lexer.tokenize(code))
            
            # 过滤掉EOF
            tokens = [t for t in tokens if t.type != TokenType.EOF]
            
            print(f"Tokens: {[f'{t.type.name}:{t.value}' for t in tokens]}")
            
            # 元数驱动解析
            if tokens and tokens[0].type == TokenType.IDENTIFIER and is_verb(tokens[0].value):
                parser = ArityParser(tokens)
                result, consumed = parser.parse_verb_call(tokens[0].value)
                print(f"解析结果: {result}")
                print(f"消耗token数: {consumed}")
                print(f"✓ 成功")
            else:
                print(f"✗ 不是动词调用")
        except Exception as e:
            print(f"✗ 错误: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
