# 光明词法分析器 - 手写Python版本
# 用于验证光明编译器的正确性

# 创建Token
def 创建Token(类型, 值):
    Token = {}
    Token["类型"] = 类型
    Token["值"] = 值
    return Token

# 符号表初始化
符号表 = {}
符号表["。"] = "DOT"
符号表["："] = "COLON"
符号表["（"] = "LPAREN"
符号表["："] = "RPAREN"

# 双字关键字列表
双字关键 = []
双字关键.append("定义")
双字关键.append("等于")
双字关键.append("如果")
双字关键.append("那么")
双字关键.append("否则")
双字关键.append("返回")
双字关键.append("遍历")
双字关键.append("当")
双字关键.append("导入")
双字关键.append("导出")

# 简单数字列表
简单数字 = []
简单数字.append("一")
简单数字.append("二")
简单数字.append("三")
简单数字.append("四")
简单数字.append("五")
简单数字.append("六")
简单数字.append("七")
简单数字.append("八")
简单数字.append("九")
简单数字.append("十")

# 中文数字映射
中文数字 = {}
中文数字["零"] = 0
中文数字["一"] = 1
中文数字["二"] = 2
中文数字["三"] = 3
中文数字["四"] = 4
中文数字["五"] = 5
中文数字["六"] = 6
中文数字["七"] = 7
中文数字["八"] = 8
中文数字["九"] = 9
中文数字["十"] = 10

# 主词法分析函数
def 分析词法(源码):
    结果 = []
    位置 = 0
    总字符数 = len(源码)
    
    while 位置 < 总字符数:
        字符 = 源码[位置]
        
        # 跳过空白
        if 字符 == " ":
            位置 = 位置 + 1
            continue
        
        # 跳过换行
        if 字符 == "\n":
            位置 = 位置 + 1
            continue
        
        # 跳过注释
        if 字符 == "#":
            while 位置 < 总字符数:
                if 源码[位置] == "\n":
                    break
                位置 = 位置 + 1
            continue
        
        # 处理符号
        符号类型 = 符号表.get(字符, None)
        if 符号类型 != None:
            Token = 创建Token(符号类型, 字符)
            结果.append(Token)
            位置 = 位置 + 1
            continue
        
        # 处理书名号
        if 字符 == "《":
            结果.append(创建Token("LBOOK", 字符))
            位置 = 位置 + 1
            名字 = ""
            while 位置 < 总字符数:
                名字符 = 源码[位置]
                if 名字符 == "》":
                    break
                名字 = 名字 + 名字符
                位置 = 位置 + 1
            结果.append(创建Token("IDENTIFIER", 名字))
            结果.append(创建Token("RBOOK", "》"))
            位置 = 位置 + 1
            continue
        
        # 处理字符串
        if 字符 == '"':
            位置 = 位置 + 1
            串值 = ""
            while 位置 < 总字符数:
                串字符 = 源码[位置]
                if 串字符 == '"':
                    break
                串值 = 串值 + 串字符
                位置 = 位置 + 1
            结果.append(创建Token("STRING", 串值))
            位置 = 位置 + 1
            continue
        
        # 处理中文数字
        if 字符 in 简单数字:
            数值 = 中文数字.get(字符, 0)
            结果.append(创建Token("NUMBER", 数值))
            位置 = 位置 + 1
            continue
        
        # 处理关键字
        if 位置 + 1 < 总字符数:
            候选 = 源码[位置:位置+2]
            if 候选 in 双字关键:
                结果.append(创建Token("KEYWORD", 候选))
                位置 = 位置 + 2
                continue
        
        # 标识符
        结果.append(创建Token("IDENTIFIER", 字符))
        位置 = 位置 + 1
    
    结果.append(创建Token("EOF", None))
    return 结果

# 测试
if __name__ == "__main__":
    测试码 = "定义甲等于三。"
    print(f"测试代码: {测试码!r}")
    结果 = 分析词法(测试码)
    print(f"Token列表 ({len(结果)} tokens):")
    for i, token in enumerate(结果):
        print(f"  {i}: {token}")
