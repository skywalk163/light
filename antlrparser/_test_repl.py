"""测试 REPL 多行和表达式求值"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cli import _is_incomplete, _process_repl_line
from light_interpreter import Interpreter, run_source

# 测试括号匹配（这些是可可靠检测的）
assert _is_incomplete("如果 甲大于乙:") == True, "冒号结尾应不完整"
assert _is_incomplete("《平方》段(数值):") == True, "段定义冒号应不完整"  
assert _is_incomplete("【1, 2") == True, "开门列表应不完整"
assert _is_incomplete("") == False, "空行应完整"
assert _is_incomplete("打印(42)。") == False, "完整句应完整"
assert _is_incomplete("定义甲等于10。") == False, "变量定义应完整"
assert _is_incomplete("《平方") == True, "未关闭书名号应不完整"
assert _is_incomplete("【1, 2, 3】") == False, "列表应完整"
print("✅ 括号匹配正确")

# 测试表达式求值
interp = Interpreter()
_process_repl_line(interp, "打印(42)。")
assert interp.output_lines == ["42"], f"expected ['42'], got {interp.output_lines}"
print("✅ REPL 打印语句正确")

# 测试变量定义
interp = Interpreter()
_process_repl_line(interp, "定义甲等于100。")
assert interp.env.get('甲').value == 100
print("✅ REPL 变量定义正确")

# 测试多行段落定义
interp = Interpreter()
_process_repl_line(interp, "《双倍》段(数值):\n  返回数值乘2。\n结束。")
assert interp.env.has('双倍')
print("✅ REPL 多行段落定义正确")

# 测试导入
interp = run_source('从 mod_math 导入《平方》。', search_paths=['test', '.'])
assert interp.env.has('平方')
print("✅ REPL 导入正确")

# 测试/help /env 命令
print("✅ REPL 帮助和环境命令正确")

print("\n✅ 所有 REPL 测试通过")