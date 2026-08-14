# -*- coding: utf-8 -*-
"""
examples 目录示例文件运行测试

编译并运行 examples/ 下可在 src 后端运行的示例文件，使用精确输出断言，
确保以下修复长期稳定：
- 紧凑写法（n减1 / n乘阶乘 / 返回一 / 那么返回一）：词法器 ASCII 标识符合并、
  IDENTIFIER_SAFE_KEYWORDS 词首误吞、parser 函数名合并等修复
- 类与属性语法（属性 名称 等于 默认值）：parser_stmt 属性名收集吞掉等于/为 的修复
- _light_builtin.xxx(...) 调用不再注入 self 参数（test_turing 字典设置 arity 问题）
- 三引号字符串（连续三个双引号括起的 docstring）词法/解析/生成支持
  （bootstrap_eval / bootstrap_lexer）
- f-string 内嵌表达式引号转义（不再产生反斜杠引号的无效语法）
- 旧语法迁移（定义 X 等于 Y → 设 X 为 Y）

新增可运行示例时，在 EXAMPLE_EXPECTED 中补充条目即可。

不纳入的示例（非语法/编译问题，属外部依赖或后端限制）：
- FFI 示例（ffi_*.light）：依赖 Linux 动态库（libc.so.6 / libm.so.6）
- modules/main.light、weather_app/main.light：跨文件模块导入需 ANTLR 后端
"""

import io
import os
import sys
import unittest

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, 'src')
for _p in [_src_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator


def _run_example(rel_path: str) -> str:
    """编译并运行 examples/ 下的 .light 文件，返回去首尾空白的标准输出"""
    path = os.path.join(_project_root, 'examples', rel_path)
    with open(path, 'r', encoding='utf-8') as f:
        code = f.read()
    parser = LightParser()
    ast = parser.parse(code)
    if ast is None:
        errors = '\n'.join(getattr(parser, 'errors', []))
        raise RuntimeError(f"解析失败: {rel_path}\n{errors}")

    py_code = PythonCodeGenerator().generate(ast)
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        exec(py_code, {'__name__': '__main__'})
        return sys.stdout.getvalue().strip().replace('\r\n', '\n')
    finally:
        sys.stdout = old_stdout


# 示例文件 -> 期望输出（精确匹配）
# 紧凑写法/词法器与解析器修复的重点回归项：
#   hello.light        含 n减1 / n乘阶乘（紧凑乘法 + 递归调用）
#   advanced.light     含 数小于等于二 / 那么返回一（紧凑条件 + 关键字词首）
#   basic.light        含 数乘阶乘（紧凑乘法 + 函数调用参数）
EXAMPLE_EXPECTED = {
    # ---- 紧凑写法回归 ----
    'hello.light': '你好，世界！\n'
                  '5的阶乘是：\n'
                  '120\n'
                  '1到10的和：\n'
                  '55\n'
                  '程序运行完成！',
    'advanced.light': '列表：\n'
                     '[1, 2, 3, 4, 5]\n'
                     '斐波那契数列：\n'
                     '1\n1\n2\n3\n5\n8\n13\n21\n34\n55\n'
                     '函数参数：\n'
                     '8\n15\n'
                     '成绩评级：\n'
                     '良好\n'
                     '高级功能演示完成！',
    'basic.light': '变量声明：\n'
                  '123\n8\n'
                  '算术运算：\n'
                  '139\n'
                  '条件语句：\n'
                  '甲大于乙\n'
                  '函数调用：\n'
                  '8\n'
                  '递归函数（阶乘）：\n'
                  '120\n'
                  '循环示例：\n'
                  '1\n2\n3\n4\n5\n'
                  '程序执行完成！',
    # ---- 类与属性语法（属性 名称 等于 默认值）----
    'class_access_control.light': '张三 存入 1000，余额：1000\n'
                                 '张三 取出 300，余额：700\n'
                                 '当前余额：700',
    'class_complete.light': '=== 小狗 ===\n'
                           '我是旺财，今年3岁。\n'
                           '旺财：汪汪汪！\n'
                           '名字：旺财\n'
                           '品种：金毛\n'
                           '物种：犬科\n'
                           '\n'
                           '=== 小猫 ===\n'
                           '我是咪咪，今年2岁。\n'
                           '咪咪：喵喵喵~\n'
                           '名字：咪咪\n'
                           '颜色：白色',
    'class_example.light': '我叫张三，今年20岁。',
    'class_static.light': '姓名：张三，学号：2024001\n'
                         '姓名：李四，学号：2024002\n'
                         '姓名：王五，学号：2024003\n'
                         '学生总数：3\n'
                         '学校名称：段言学院',
    'calculator.light': '计算结果: 15',
    'student_management.light': '=== 学生信息 ===\n'
                               '姓名: 张三\n'
                               '年龄: 18\n'
                               '平均成绩: 84.33333333333333\n'
                               '\n'
                               '姓名: 李四\n'
                               '年龄: 19\n'
                               '平均成绩: 91.66666666666667',
    # ---- 旧语法迁移（定义 X 等于 Y → 设 X 为 Y）----
    'module_demo.light': '=== 数学工具演示 ===\n'
                        '列表: [1, 2, 3, 4, 5]\n'
                        '总和: 15\n'
                        '平均值: 3.0\n'
                        '\n'
                        '模块导入功能在 ANTLR 后端中可用（使用 --backend antlr）。',
    # ---- 其余可运行示例 ----
    'test_fib.light': '0\n1\n1\n2\n3\n5\n8\n13\n21\n34',
    'test_fib_src.light': '0\n1\n1\n2\n3\n5\n8\n13\n21\n34',
    'test_hello.light': '你好，世界！\n84\n8',
    'test_hello_src.light': '你好，世界！\n84\n8',
    'test_para.light': '你好，世界！\n6\n8',
    'test_bubble.light': '排序前：\n[5, 3, 8, 1, 2]\n'
                        '排序后：\n[1, 2, 3, 5, 8]',
    'hanoi.light': '=== 汉诺塔（3层）===\n'
                  '移动盘子 1 从 A 到 C\n'
                  '移动盘子 2 从 A 到 B\n'
                  '移动盘子 1 从 C 到 B\n'
                  '移动盘子 3 从 A 到 C\n'
                  '移动盘子 1 从 B 到 A\n'
                  '移动盘子 2 从 B 到 C\n'
                  '移动盘子 1 从 A 到 C',
    'typed_demo.light': '8\n120',
    # ---- 本轮扫描修复后新增可运行 ----
    #   test_turing.light       _light_builtin.字典设置(...) 不再注入 self 参数（codegen）
    #   type_annotation_demo   π 标识符改 圆周率；处理数据 用 是整数/是浮点/是字符串
    #   bootstrap_eval/lexer   三引号 docstring 支持；继续→跳过；添加→列表追加；
    #                          转换→转整数/转浮点；删除/插入→列表弹出/列表插入
    'test_turing.light': '初始纸带：\n'
                        "['1', '0', '1', '1', ' ']\n"
                        '最终纸带：\n'
                        "['0', '0', '1', '1', ' ']\n"
                        '执行步数：\n'
                        '2',
    'type_annotation_demo.light': '=== 段言类型注解示例 ===\n'
                                 '\n'
                                 '1. 变量类型注解：\n'
                                 '  x: 10 (整数)\n'
                                 '  y: 3.14 (小数)\n'
                                 '  z: hello (文本)\n'
                                 '  标志: True (布尔)\n'
                                 '  列表: [1, 2, 3] (列表)\n'
                                 "  映射: {'名字': '张三', '年龄': 25} (字典)\n"
                                 '\n'
                                 '2. 函数类型注解：\n'
                                 '  加法(5, 3) = 8\n'
                                 '  计算面积(2.5) = 19.6349375\n'
                                 "  格式化名字('张', '三') = '张 三'\n"
                                 '\n'
                                 '3. 混合类型注解：\n'
                                 "  处理数据(42) = 整数: 42\n"
                                 "  处理数据(3.14) = 小数: 3.14\n"
                                 "  处理数据('hello') = 文本: 'hello'\n"
                                 '\n'
                                 '=== 类型注解示例完成 ===',
    'bootstrap_eval.light': '=== 段言自举示例：表达式求值器 ===\n'
                           '测试表达式求值：\n'
                           '  ✓ 1+2 = 3 (预期: 3)\n'
                           '  ✓ 10-5*2 = 0 (预期: 0)\n'
                           '  ✓ 8/2+3 = 7.0 (预期: 7)\n'
                           '  ✓ 100/25+7 = 11.0 (预期: 11)\n'
                           '  ✓ 3.14*2 = 6.28 (预期: 6.28)\n'
                           '\n'
                           '=== 表达式求值完成 ===',
    'bootstrap_lexer.light': '=== 段言自举示例：简单词法分析器 ===\n'
                            '测试源码：\n'
                            '设 x 为 42\n'
                            '打印(x 加 10)\n'
                            '\n'
                            '分词结果：\n'
                            "  [关键字] '设'\n"
                            "  [标识符] 'x'\n"
                            "  [关键字] '为'\n"
                            "  [数字] '42'\n"
                            "  [关键字] '打印'\n"
                            "  [括号] '('\n"
                            "  [标识符] 'x'\n"
                            "  [标识符] '加'\n"
                            "  [数字] '10'\n"
                            "  [括号] ')'\n"
                            '\n'
                            '=== 词法分析完成 ===',
}


class TestExampleFilesRun(unittest.TestCase):
    """逐文件编译运行 examples/ 下的示例并断言精确输出"""

    def test_all_examples_output(self):
        failures = []
        for rel_path, expected in EXAMPLE_EXPECTED.items():
            with self.subTest(example=rel_path):
                try:
                    actual = _run_example(rel_path)
                except Exception as e:  # noqa: BLE001 - 汇总所有失败
                    failures.append(f"{rel_path}: 运行异常 -> {e}")
                    continue
                if actual != expected:
                    failures.append(
                        f"{rel_path}: 输出不匹配\n"
                        f"  期望: {expected!r}\n"
                        f"  实际: {actual!r}"
                    )
        self.assertEqual([], failures)


if __name__ == '__main__':
    unittest.main()
