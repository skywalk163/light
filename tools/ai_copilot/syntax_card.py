"""
光明语法速查卡生成器

从 keywords.py 和 stdlib/builtins.py 自动提取 v3.2 语法的精简参照，
生成可直接嵌入 prompt 的速查卡文本，让 AI 在生成光明代码时
不用凭"印象"猜语法，而是按卡片精确翻译。

v2 改进：
  - 从 stdlib/builtins.py 自动提取内建函数，按类别分组
  - 标注 SRC/LLVM 后端差异（类系统、内建函数可用性）
  - 新增暗坑说明（列表索引赋值、变量名冲突等）
  - 修正 len() 在 SRC 后端的实际用法

用法：
    from syntax_card import generate_syntax_card
    card = generate_syntax_card()          # 完整卡
    card = generate_syntax_card(compact=True)  # 精简卡（约300字）
"""

import os
import sys
import ast as _ast

# 确保能导入 keywords 和 builtins
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_PROJECT_DIR, 'src'))

from keywords import (
    KEYWORDS_DEFINE, KEYWORDS_CONDITION, KEYWORDS_LOOP,
    KEYWORDS_FUNCTION, KEYWORDS_EXCEPTION, KEYWORDS_CLASS,
    KEYWORDS_LOGIC, KEYWORDS_SPECIAL, KEYWORDS_RESERVED,
    VERB_ARITY, BUILTIN_TYPES, SYMBOL_MAP,
)


# ── 从 builtins.py 自动提取内建函数 ───────────────────────────────

def _extract_builtins() -> dict:
    """从 stdlib/builtins.py 提取所有导出函数，按类别分组

    Returns:
        {类别名: [(函数名, 参数签名, 简介), ...]}
    """
    builtins_path = os.path.join(_PROJECT_DIR, 'stdlib', 'builtins.py')
    with open(builtins_path, encoding='utf-8') as f:
        source = f.read()

    tree = _ast.parse(source)

    # 从 __all__ 提取导出名
    exported = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Assign):
            for target in node.targets:
                if isinstance(target, _ast.Name) and target.id == '__all__':
                    if isinstance(node.value, _ast.List):
                        for elt in node.value.elts:
                            if isinstance(elt, _ast.Constant):
                                exported.add(elt.value)

    # 提取函数定义
    functions = {}
    for node in _ast.iter_child_nodes(tree):
        if isinstance(node, _ast.FunctionDef) and node.name in exported:
            name = node.name
            # 提取参数签名
            args = [a.arg for a in node.args.args]
            sig = f"{name}({', '.join(args)})"
            # 提取 docstring 第一行
            doc = _ast.get_docstring(node) or ""
            brief = doc.split('\n')[0].strip().rstrip('。')
            functions[name] = {'sig': sig, 'brief': brief, 'args': args}

    # 按类别分组
    categories = {
        "文件I/O": ["读取文件", "写入文件", "追加文件", "文件存在", "目录存在",
                    "路径存在", "创建目录", "删除文件", "删除目录", "列出目录", "文件大小"],
        "路径操作": ["绝对路径", "连接路径", "目录名", "文件名", "扩展名",
                    "分割路径", "分割扩展名"],
        "字符串工具": ["转整数", "转浮点", "转字符串", "字符串长度", "字符串获取",
                     "截取", "分割字符串", "连接字符串", "替换字符串", "去除空白",
                     "转大写", "转小写"],
        "列表工具": ["列", "列表长度", "列表追加", "列表弹出", "列表排序",
                    "列表反转", "列表包含"],
        "字典工具": ["字典创建", "字典设置", "字典删除", "字典键列表", "字典值列表",
                    "字典项列表", "字典包含键", "字典获取"],
        "类型检查": ["是整数", "是浮点", "是字符串", "是列表", "是字典", "是空",
                    "是字母", "是数字", "是空白"],
        "数学统计": ["阶乘", "平均数", "中位数", "众数", "方差", "标准差",
                    "样本方差", "样本标准差", "求和", "累积和", "圆周率", "自然常数",
                    "角度转弧度", "弧度转角度"],
        "随机": ["随机整数", "随机浮点", "随机选择"],
        "JSON": ["解析JSON", "序列化JSON", "美化JSON"],
        "系统": ["环境变量", "设置环境变量", "参数列表", "退出程序",
                "当前目录", "切换目录", "执行命令"],
        "输入输出": ["读取行", "读取N字节", "写入输出", "打印输出",
                   "刷新输出", "写入错误", "打印错误"],
    }

    result = {}
    for cat, names in categories.items():
        entries = []
        for n in names:
            if n in functions:
                entries.append((n, functions[n]['sig'], functions[n]['brief']))
        if entries:
            result[cat] = entries

    return result


def _generate_builtins_section() -> str:
    """生成内建函数速查卡段落"""
    builtins = _extract_builtins()
    lines = []
    for cat, entries in builtins.items():
        funcs = " / ".join(f"{name}" for name, _, _ in entries)
        lines.append(f"  {cat}：{funcs}")
    return "\n".join(lines)


def _generate_builtins_detail() -> str:
    """生成内建函数详细参照（含签名和简介）"""
    builtins = _extract_builtins()
    lines = []
    for cat, entries in builtins.items():
        lines.append(f"\n  【{cat}】")
        for name, sig, brief in entries:
            lines.append(f"    {sig}  — {brief}")
    return "\n".join(lines)


# ── 暗坑说明 ──────────────────────────────────────────────────────

_PITFALLS = """\
【光明暗坑 — AI 生成时必须注意】

1. 列表索引赋值：不能用"设 列表[i] 为 值"，正确写法是"列表[i] = 值"
   ✗ 设 列表[0] 为 10    （语法错误）
   ✓ 列表[0] = 10         （正确）

2. 变量名不能与内建函数同名：
   ✗ 设 长度 为 10        （"长度"会遮蔽内建函数）
   ✓ 设 n 为 10           （正确）

3. SRC 后端内建函数差异：
   · len()/str()/int()/float()/type()/range() 等Python内建可用
   · 中文内建函数（读取文件/列表长度等）需 "从 标准库 导入 ..." 或 "导入 标准库"
   · 长度() 不是SRC后端内建！用 len() 或 列表长度()

4. 类系统后端差异：
   · SRC 后端：类定义可解析，但运行时行为有限
   · LLVM 后端：完整支持类、继承、方法重写
   · 含类代码建议用 LLVM 后端：light compile file.light --backend llvm-typed

5. 运算符不能混用Python写法：
   ✗ a + b / a - b / a <= b / a != b / a >= b
   ✓ a 加 b / a 减 b / a 小于等于 b / a 不等于 b / a 大于等于 b
   例外：列表索引赋值中 = 可用

6. 循环变量更新必须用"设"：
   ✗ i = i + 1
   ✓ 设 i 为 i 加 1  /  i 加上 1

7. 遍历范围用"至"不用逗号：
   ✗ 遍历 i 于 range(1, 10)：
   ✓ 遍历 i 于 1至10：
"""


# ── 语法速查卡模板 ──────────────────────────────────────────────

_FULL_CARD = """\
【光明 v3.2 语法速查卡】

一、变量与赋值
  声明：设 甲 为 10 / 定义 乙 等于 "你好"
  赋值：甲 等于 30 / 甲 为 40 / 甲加上1 / 甲减去2 / 甲乘以3 / 甲除以4
  注意：空格可选，设甲为10 合法

二、段落（函数）
  定义：段落 名 接收 参数1, 参数2：  （仅"段落"+"接收"，无旧形式）
  无参：段落 名：
  类型：段落 名 接收 甲:数, 乙:文本：
  返回：返回 值

三、条件
  如果 条件：/ 否则如果 条件：/ 否则：
  单行：如果 条件：语句
  简写：若 代替 如果
  冒号必选

四、循环
  当 条件：          （while）
  遍历 项 于 列表：   （for-in，于/在/之/中的 均可）
  遍历 i 于 1至10：  （范围遍历，步长：1至10步2）
  跳出 / 跳过         （break/continue，无句号）

五、运算符
  算术：加/减/乘/除以/取余/幂
  复合：加上/减去/乘以/除以
  比较：等于/不等于/大于/小于/大于等于/小于等于
  逻辑：且/或/非

六、异常
  尝试：…捕获 异常：…最终：…
  抛出 异常

七、类
  类 名：/ 类 子 继承 父：
  属性 名 / 构造 接收 …：
  己.属性 / 父.构造(…)
  新建 类名(参数)
  ⚠ 类系统建议用 LLVM 后端运行

八、导入导出
  导入 模块 / 从 模块 导入 符号 / 导出 符号1, 符号2

九、特殊值
  真/假/空

十、内置类型
  {builtin_types}

十一、SRC后端可用内建函数（Python内建，直接可用）
  len()/str()/int()/float()/type()/range()/abs()/round()/min()/max()
  print()已映射为打印

十二、中文内建函数（需导入或已内置，按类别）
{builtins_section}

十三、核心规则
  · 冒号必选（块级语句末尾）
  · 句号可选（所有语句）
  · 空格可选（关键字/变量/运算符间）
  · 纯缩进表示代码块（无花括号/无结束关键字）
"""

_COMPACT_CARD = """\
【光明v3.2速查】
变量：设甲为10 / 定义乙等于"你好" / 甲等于30 / 甲加上1
段落：段落名接收a,b： / 返回值 / 段落名：（无参）
条件：如果条件：/ 否则如果条件：/ 否则：/ 冒号必选
循环：当条件：/ 遍历i于1至10：/ 遍历项于列表：/ 跳出/跳过
运算：加/减/乘/除以/取余/等于/不等于/大于/小于/大于等于/小于等于/且/或/非
异常：尝试：…捕获异常：…/ 抛出异常
类：类名：/ 构造接收…：/ 己.属性/ 父.构造/ 新建类名() ⚠需LLVM后端
导入：从模块导入符号 / 导出符号1,符号2
特殊：真/假/空
SRC内建：len()/str()/int()/float()/type()/range()/print()→打印
暗坑：列表[i]=值✓ | 设列表[i]为值✗ | 变量名≠内建函数名 | 运算用中文不用符号
规则：冒号必选·句号可选·空格可选·纯缩进代码块
"""


def _generate_verb_table() -> str:
    """生成动词（运算符/函数）快速参照表"""
    lines = []
    categories = {
        "算术": ["加", "减", "乘", "除以", "取余", "幂", "乘以", "加上", "减去"],
        "比较": ["等于", "不等于", "大于", "小于", "大于等于", "小于等于"],
        "列表": ["首", "末", "余", "长", "排序", "反转", "求和", "求最大", "求最小", "去重", "筛选", "映射"],
        "IO": ["打印", "读取", "输出"],
        "文件": ["读取文件", "写入文件", "追加文件", "文件存在", "目录存在", "创建目录", "列出目录"],
        "字符串": ["转整数", "转浮点", "转字符串", "分割字符串", "连接字符串", "替换字符串", "去除空白"],
        "类型": ["是整数", "是浮点", "是字符串", "是列表", "是字典", "是空"],
    }

    for cat, verbs in categories.items():
        entries = []
        for v in verbs:
            arity = VERB_ARITY.get(v, "?")
            entries.append(f"{v}({arity}参)")
        lines.append(f"  {cat}：" + " / ".join(entries))

    return "\n".join(lines)


def generate_syntax_card(compact: bool = False, include_verbs: bool = False,
                         include_pitfalls: bool = False) -> str:
    """生成语法速查卡

    Args:
        compact: True 返回精简版（约300字），False 返回完整版
        include_verbs: 是否包含动词参数参照表
        include_pitfalls: 是否包含暗坑说明

    Returns:
        速查卡文本，可直接嵌入 prompt
    """
    if compact:
        card = _COMPACT_CARD
    else:
        builtin_str = " / ".join(sorted(BUILTIN_TYPES))
        builtins_section = _generate_builtins_section()
        card = _FULL_CARD.format(builtin_types=builtin_str,
                                 builtins_section=builtins_section)

    if include_verbs:
        card += "\n\n【动词参数参照】\n" + _generate_verb_table()

    if include_pitfalls:
        card += "\n\n" + _PITFALLS

    return card


def generate_pitfalls() -> str:
    """单独输出暗坑说明"""
    return _PITFALLS


def generate_example_pairs() -> str:
    """生成 Python→光明 对照示例，用于翻译模式 prompt

    v2 修正：len() → len()（SRC后端）/ 长度() 不可用
    """
    pairs = """\
【Python→光明 对照示例】

# 1. 变量
x = 10           →  设 x 为 10
name = "hello"   →  定义 name 等于 "你好"
x += 1           →  x 加上 1

# 2. 函数
def add(a, b):   →  段落 加法 接收 a, b：
    return a + b →      返回 a 加 b

# 3. 条件
if x > 5:        →  如果 x 大于 5：
    print("大")  →      打印 "大"
elif x > 3:      →  否则如果 x 大于 3：
    print("中")  →      打印 "中"
else:            →  否则：
    print("小")  →      打印 "小"

# 4. 循环
while x < 10:    →  当 x 小于 10：
    x += 1       →      设 x 为 x 加 1

for i in range(1, 11):  →  遍历 i 于 1至10：
    print(i)             →      打印(i)

for item in lst:  →  遍历 项 于 lst：
    print(item)   →      打印(项)

# 5. 列表
lst = [1, 2, 3]  →  设 lst 为 [1, 2, 3]
lst.append(4)    →  lst.追加(4)
len(lst)         →  len(lst)  （SRC后端用Python内建len）

# ⚠ 暗坑：列表索引赋值
lst[0] = 10      →  lst[0] = 10  （不能用"设 lst[0] 为 10"）

# 6. 类（建议用LLVM后端）
class Dog:             →  类 狗：
    def __init__(self, name):  →      构造 接收 名称：
        self.name = name       →          己名称 为 名称
    def speak(self):           →      段落 发声：
        print("汪")            →          打印 "汪"
dog = Dog("旺财")     →  设 小狗 为 新建 狗("旺财")

# 7. 异常
try:               →  尝试：
    risky()        →      危险操作()
except Exception:  →  捕获 异常：
    handle()       →      处理()

# 8. 导入
from math import factorial  →  从 数学工具 导入 阶乘
"""
    return pairs


if __name__ == "__main__":
    import sys as _sys
    if hasattr(_sys.stdout, 'reconfigure'):
        _sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("【完整速查卡】")
    print("=" * 60)
    print(generate_syntax_card(include_pitfalls=True))
    print()
    print("=" * 60)
    print("【精简速查卡】")
    print("=" * 60)
    print(generate_syntax_card(compact=True))
    print()
    print("=" * 60)
    print("【内建函数详细参照】")
    print("=" * 60)
    print(_generate_builtins_detail())
    print()
    print("=" * 60)
    print("【暗坑说明】")
    print("=" * 60)
    print(generate_pitfalls())
