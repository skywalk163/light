# -*- coding: utf-8 -*-
"""
LP-D-002：报错定位与归因修复测试

三个场景：
  (a) 只调 子串位置 不导入 → 提示含「从 字符串处理 导入 子串位置」，
      且不出现「先通过『设』定义变量」；
  (b) 变量名拼错（打印(甲甲)）→ 给拼写建议，行号 == 真实出错行；
  (c) 真的未定义变量且不属于任何 stdlib 导出 → 不得误报「缺导入」。

断言方式：跑真实的 cli/light.py 入口取 stderr，正则解析行号与提示文本。
"""

import os
import re
import subprocess
import sys
import tempfile

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_light(source: str) -> tuple:
    """写临时 .light 文件并通过 cli/light.py 运行，返回 (returncode, stderr_text)。"""
    fd, path = tempfile.mkstemp(suffix='.light', dir=REPO_ROOT)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(source)
        proc = subprocess.run(
            [sys.executable, '-m', 'cli.light', 'run', path],
            capture_output=True, text=True, timeout=30,
            cwd=REPO_ROOT, encoding='utf-8', errors='replace',
        )
        return proc.returncode, proc.stderr + proc.stdout
    finally:
        os.unlink(path)


class TestStdlibImportHint:
    """场景 (a)：未导入的 stdlib 函数 → 缺导入提示，而非「先定义变量」"""

    def test_zichuan_weizhi_gives_import_hint(self):
        """调用 子串位置 不导入 → 提示从 字符串处理 导入"""
        source = '打印(子串位置("hello", "ll"))\n'
        rc, output = _run_light(source)
        assert rc != 0, f'应当报错退出，实际 rc={rc}'
        # 必须包含导入提示
        assert '从 字符串处理 导入 子串位置' in output, \
            f'输出中应包含导入提示，实际:\n{output}'
        assert '字符串处理' in output
        # 不得出现误导性的「先通过设定义变量」建议
        assert '先通过「设」定义变量' not in output, \
            f'输出不应包含「先通过设定义变量」误导提示，实际:\n{output}'

    def test_stdlib_hint_not_for_builtin(self):
        """全局内置名（如 长度）不应被误报为缺导入"""
        # 长度 是 builtin_map 里的 'len'，裸调用不会 NameError
        # 但我们测的是：即使拼错内置名，也不应报「从 X 导入」
        source = '打印(长度x("hello"))\n'  # 长度x 不是任何 stdlib 导出
        rc, output = _run_light(source)
        assert rc != 0
        # 长度x 不在生成表里，不应报缺导入
        assert '导入' not in output or '从' not in output.split('导入')[0] if '导入' in output else True
        # 更精确：不应出现「该函数来自」
        assert '该函数来自' not in output, \
            f'长度x 不是 stdlib 导出，不应报缺导入，实际:\n{output}'


class TestLineAnchor:
    """场景 (b)：行号锚定到真实出错行"""

    def test_line_number_points_to_error_line(self):
        """打印(甲甲) 在第 3 行 → 报错高亮第 3 行"""
        source = (
            '设 甲 为 10\n'
            '设 乙 为 20\n'
            '打印(甲甲)\n'
        )
        rc, output = _run_light(source)
        assert rc != 0, f'应当报错退出，实际 rc={rc}'
        # 正则找代码片段中的行号——应高亮第 3 行
        # 输出格式：行号 后面跟源码，错误行有箭头标记
        lines = output.split('\n')
        # 找到包含 打印(甲甲) 的那一行，确认它前面的行号是 3
        found_line3 = False
        for i, line in enumerate(lines):
            if '打印(甲甲)' in line:
                # 行首应该是 "3 "
                stripped = line.strip()
                if stripped.startswith('3 ') or stripped.startswith('3\t'):
                    found_line3 = True
                break
        assert found_line3, \
            f'报错应高亮第 3 行（打印(甲甲)），实际输出:\n{output}'

    def test_line_number_not_guessed(self):
        """拿不到行号时不应猜一个错误的数字（显示行号未知或正确行）"""
        source = '打印(不存在的变量xyz)\n'
        rc, output = _run_light(source)
        assert rc != 0
        # 不应出现明显错误的行号（如行号远超源码行数）
        # 源码只有 1 行，行号应为 1 或 行号未知
        m = re.search(r'位置.*?(\d+)', output)
        if m:
            reported_line = int(m.group(1))
            assert reported_line <= 1, \
                f'源码只有 1 行，报告行号={reported_line} 不合理，实际:\n{output}'


class TestNoFalseImportHint:
    """场景 (c)：真未定义变量且非 stdlib 导出 → 不误报缺导入"""

    def test_random_undefined_no_import_hint(self):
        """甲甲 不是任何 stdlib 导出 → 不报「从 X 导入」"""
        source = '设 甲 为 10\n打印(甲甲)\n'
        rc, output = _run_light(source)
        assert rc != 0
        # 不应出现「该函数来自」或「从 ... 导入 ...」提示
        assert '该函数来自' not in output, \
            f'甲甲 不是 stdlib 导出，不应报缺导入，实际:\n{output}'
        # 应给通用的 NameError 建议
        assert '拼写' in output or '设' in output or '定义' in output, \
            f'应给通用变量未定义建议，实际:\n{output}'


class TestGeneratorCheck:
    """验证生成脚本 --check 通过"""

    def test_gen_script_check(self):
        """scripts/gen_stdlib_name_map.py --check 应 rc=0"""
        proc = subprocess.run(
            [sys.executable, 'scripts/gen_stdlib_name_map.py', '--check'],
            capture_output=True, text=True, timeout=30,
            cwd=REPO_ROOT, encoding='utf-8', errors='replace',
        )
        assert proc.returncode == 0, \
            f'gen_stdlib_name_map.py --check 应通过，stdout={proc.stdout}, stderr={proc.stderr}'
