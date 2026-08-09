"""导入链诊断脚本 - 逐步排查哪个模块导入失败"""
import sys
import traceback

print("Python:", sys.version)
print("cwd:", sys.executable)

# Step 1: add src/ to path
sys.path.insert(0, "src")

steps = [
    ("tokens", "from tokens import Token, TokenType"),
    ("keywords", "from keywords import VERB_ARITY"),
    ("lexer", "from lexer import Lexer"),
    ("ast_nodes_v3", "from ast_nodes_v3 import EmbedBlock"),
    ("parser_core", "from parser_core import DuanParserCore"),
    ("parser_stmt", "from parser_stmt import ParserStmtMixin"),
    ("parser_expr", "from parser_expr import ParserExprMixin"),
    ("light_parser_v3", "from light_parser_v3 import DuanParser, ImportStmt"),
    ("module_resolver", "from module_resolver import ModuleResolver"),
    ("code_generator", "from code_generator import PythonCodeGenerator"),
]

for name, code in steps:
    try:
        exec(code, {"__name__": "__main__"})
        print(f"  OK: {name}")
    except Exception as e:
        print(f"  FAIL: {name}")
        traceback.print_exc()
        break

print("\n=== 如果以上全部 OK，测试 ModuleResolver ===")
try:
    from module_resolver import ModuleResolver
    r = ModuleResolver()
    print("search_paths:", r.search_paths)
    
    # 测试找到 contrib 模块
    p = r.find_module("日期时间增强")
    print("找到 日期时间增强:", p)
except Exception as e:
    traceback.print_exc()

print("\n=== 测试 CodeGenerator (C embed) ===")
try:
    from code_generator import PythonCodeGenerator
    from ast_nodes_v3 import EmbedBlock
    g = PythonCodeGenerator()
    g._generate_embed_block(EmbedBlock('C', 'double add(double a, double b) { return a + b; }'))
    print("C codegen lines:", len(g.output_lines))
    print("\n".join(g.output_lines[:8]))
except Exception as e:
    traceback.print_exc()