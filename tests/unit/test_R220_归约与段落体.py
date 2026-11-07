# -*- coding: utf-8 -*-
"""T-0277 / R220：归约传段落报类型错误 + 单行段落体后顶层语句静默空跑。

## 为什么全部真起 CLI 进程

两条缺陷都跨「解析 → 生成 → 运行」三层：

* 探针 A 的「求和」是 keywords.py 里登记过的动词名，parser 会把它做成零参
  ParagraphCall；只有 `python -m cli.light run` 真编译出产物并跑起来，才能看出
  函数位发射的是 `求和()`（立即调用、缺参）还是 `求和`（可调用对象）。
* 探针 B 的「静默空跑」rc=0、零输出、零报错：单看 AST 或生成产物字符串都对不上，
  必须看进程的真实 rc 与 stdout。

所以本文件每个用例都 `subprocess.run([sys.executable, '-m', 'cli.light', 'run', …])`，
断言 rc 与 stdout 的**精确值**（行尾先按 \\r\\n → \\n 归一化，避免 CRLF 平台假红）。
不 import 编译器函数、不靠环境变量改判据。

## 裁定（探针 B）

单行段落体 `段落 加倍(x): 返回 x * 2` 是**合法语法**：本文件 :3384 / :3429 的
L-013 修复早已为 if / while / for 确立「冒号后无 NEWLINE 即单行体」的口径，
段落定义 `_parse_paragraph_v2` 当年漏了这一支。修法不是编译期报错，而是让
`_parse_body(allow_single_line=True)` 在行尾闭合，后续顶层语句照常执行。
下面 test_B* 把这条裁定与多行体对照一起固化。
"""

import os
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _跑(源码):
    """真起一个 `python -m cli.light run <探针>` 子进程，返回 (rc, stdout, stderr)。

    `{临时目录}` 占位会替换成该用例独占临时目录的正斜杠路径（文件 IO 回归用）。
    """
    with tempfile.TemporaryDirectory() as d:
        源码 = 源码.replace("{临时目录}", d.replace("\\", "/"))
        入口 = os.path.join(d, "探针.light")
        with open(入口, "w", encoding="utf-8") as f:
            f.write(源码)
        p = subprocess.run(
            [sys.executable, "-m", "cli.light", "run", 入口],
            cwd=_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
        return p.returncode, p.stdout.replace("\r\n", "\n"), p.stderr


class _基线(unittest.TestCase):
    def 断言(self, 源码, 期望rc, 期望out):
        rc, out, err = _跑(源码)
        self.assertEqual(rc, 期望rc, f"rc={rc} stdout={out!r} stderr={err[-500:]!r}")
        self.assertEqual(out, 期望out, f"stdout={out!r} stderr={err[-500:]!r}")


# ── 探针 A：归约 / 折叠 的段落实参 ───────────────────────────────────────
_探针A_三参 = """段落 求和(a, b):
  返回 a + b
打印 "BEGIN"
设 r 为 归约([1,2,3], 求和, 0)
打印 转字符串(r)
打印 "END"
"""
_探针A_两参 = """段落 求和(a, b):
  返回 a + b
打印 转字符串(归约([1,2,3], 求和))
"""
_探针A_普通名 = """段落 加(a, b):
  返回 a + b
打印 转字符串(归约([1,2,3], 加, 0))
"""


class TestA归约段落实参(_基线):
    def test_A1_三参归约_动词名段落_修复前缺参崩溃(self):
        # 修复前：rc=1、stdout 只有 "BEGIN"（类型错误：求和() missing 2 required …）
        self.断言(_探针A_三参, 0, "BEGIN\n6\nEND\n")

    def test_A2_两参归约_动词名段落(self):
        self.断言(_探针A_两参, 0, "6\n")

    def test_A3_普通段落名不被新分支改坏(self):
        self.断言(_探针A_普通名, 0, "6\n")


# ── 探针 B：单行段落体后顶层语句静默空跑 ────────────────────────────────
_探针B_顶层 = """段落 加倍(x): 返回 x * 2
打印 "END"
"""
_探针B_可调用 = """段落 加倍(x): 返回 x * 2
打印 转字符串(加倍(3))
"""
_探针B_多语句 = """段落 加倍(x): 返回 x * 2
打印 "A"
打印 "B"
"""
_探针B_块内 = """如果 1 == 1:
  段落 加倍(x): 返回 x * 2
  打印 转字符串(加倍(3))
打印 "END"
"""
_探针B_连续定义 = """段落 加倍(x): 返回 x * 2
段落 加三(x): 返回 x + 3
打印 转字符串(加三(加倍(2)))
"""
_对照_多行体 = """段落 加倍(x):
  返回 x * 2
打印 "END"
打印 转字符串(加倍(3))
"""
_对照_嵌套多行体 = """段落 分类(x):
  如果 x > 0:
    返回 "正"
  返回 "非正"
打印 分类(1)
打印 分类(-1)
"""


class TestB单行段落体(_基线):
    def test_B1_修复前静默空跑_现在顶层语句执行(self):
        # 修复前：rc=0、stdout 为空（"END" 被吞进段落体、排在 return 之后不可达）
        self.断言(_探针B_顶层, 0, "END\n")

    def test_B2_单行段落体定义出的函数可调用(self):
        self.断言(_探针B_可调用, 0, "6\n")

    def test_B3_多条顶层语句全部保留在模块级(self):
        self.断言(_探针B_多语句, 0, "A\nB\n")

    def test_B4_块内单行段落体不破坏外层块边界(self):
        self.断言(_探针B_块内, 0, "6\nEND\n")

    def test_B5_连续两个单行段落体(self):
        self.断言(_探针B_连续定义, 0, "7\n")

    def test_B6_多行段落体保持原样_裁定依据(self):
        self.断言(_对照_多行体, 0, "END\n6\n")

    def test_B7_多行段落体含嵌套分支不受影响(self):
        self.断言(_对照_嵌套多行体, 0, "正\n非正\n")


# ── 卡面「已绿能力」6 条回归：本次改动不许把它们改坏 ────────────────────
class Test已绿能力回归(_基线):
    def test_R1_映射返回列表_L258(self):
        self.断言("""段落 加倍(x):
  返回 x * 2
打印 转字符串(映射([1,2,3], 加倍))
""", 0, "[2, 4, 6]\n")

    def test_R2_筛选返回列表(self):
        self.断言("""段落 偶数(x):
  返回 x % 2 == 0
打印 转字符串(筛选([1,2,3], 偶数))
""", 0, "[2]\n")

    def test_R3_切片赋值_L260(self):
        self.断言("""设 表 为 [1,2,3,4]
设 表[0:2] 为 [9,9]
打印 转字符串(表)
""", 0, "[9, 9, 3, 4]\n")

    def test_R4_包内列下标赋值_L255(self):
        self.断言("""设 包 为 {"列": [1,2]}
设 包.列[0] 为 5
打印 转字符串(包)
""", 0, '{"列": [5, 2]}\n')

    def test_R5_具名参数_分割字符串_读写文件_L256(self):
        self.断言("""设 路 为 "{临时目录}/r220.txt"
写入文件(路径=路, 内容="甲乙丙", 编码="utf-8")
打印 读取文件(路径=路, 编码="utf-8")
打印 转字符串(分割字符串("a,b,c", 分隔符=","))
""", 0, '甲乙丙\n["a", "b", "c"]\n')

    def test_R6_解析时间_struct_time_L259(self):
        # 只取 tm_year（t[0]）：struct_time 的完整 repr 含平台相关字段，不锁死。
        self.断言("""从 时间管理 导入 解析时间
设 t 为 解析时间("2026-10-30T15:00:00")
打印 转字符串(t[0])
""", 0, "2026\n")


if __name__ == "__main__":
    unittest.main()
