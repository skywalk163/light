# -*- coding: utf-8 -*-
"""T9B 定向测试：re.light 回溯 VM 根因修复验证（O0）。

覆盖：
  1. T6A-07：IPv4 捕获组模式对 999.1.1.1 正确判定不匹配（mini20）
  2. T6A-07：简化 IPv4 模式（无第三分支）行为一致（mini19）
  3. T6A-07：捕获组多选分支回溯后组表正确（嵌套可选量词）
  4. T6A-11：同一程序内 20 次连续正则验证调用，不崩且结果正确
  5. IP 反例恢复：999.1.1.1 / 256.1.1.1 / 1.2.3 均判定不匹配

反跑判据：
  - 改回原 re.light（git stash）→ T6A-07 mini20 立红（999.1.1.1 误判真）
  - T6A-11 20 次调用在原代码下 Windows 堆崩溃 / POSIX valgrind 11681 错误

仅跑本文件；禁止全量。
"""
import os
import sys
import subprocess as _subproc
import tempfile as _tempfile

import pytest

_HELPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_t6a_native_helper.py')


def _编译并运行(code: str, optimize_level: int = 0) -> tuple:
    with _tempfile.TemporaryDirectory(prefix='_taskT9B_') as d:
        src = os.path.join(d, '主.light')
        exe = os.path.join(d, '产物')
        with open(src, 'w', encoding='utf-8', newline='\n') as f:
            f.write(code)
        r = _subproc.run([sys.executable, _HELPER, src, exe, str(optimize_level)],
                         capture_output=True, timeout=180)
        out = r.stdout.decode('utf-8', errors='replace').strip()
        err = r.stderr.decode('utf-8', errors='replace').strip()
        return r.returncode, out, err


def _行(out: str):
    return [h for h in out.replace('\r', '').split('\n') if h != '']


def _对拍(out: str, 期望):
    实际 = _行(out)
    assert 实际 == [str(e) for e in 期望], f"实际={实际} 期望={期望}"


# ══════════════════════════════════════════════════════════════════════
# T6A-07：IPv4 捕获组模式多选分支回溯
# ══════════════════════════════════════════════════════════════════════

class TestT6A07_IPv4:
    """T6A-07：{n} 重复体含多选分支时回溯恢复不完整。"""

    def test_mini20_完整IPv4_999误判(self):
        """mini20：完整三分支 IPv4 捕获组模式，999.1.1.1 应判定不匹配。"""
        code = (
            '从 正则表达式 导入 验证IP地址\n'
            '段落 主:\n'
            '  输出(验证IP地址("999.1.1.1"))\n'
            '  输出(验证IP地址("192.168.1.1"))\n'
            '  输出(验证IP地址("255.255.255.255"))\n'
            '  输出(验证IP地址("10.0.0.1"))\n'
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, err
        _对拍(out, ['假', '真', '真', '真'])

    def test_mini19_简化IPv4_无第三分支(self):
        """mini19：去掉第三分支 [01]?... 后行为一致（原代码此版正确）。"""
        code = (
            '从 re 导入 re_完全匹配\n'
            '段落 主:\n'
            '  设 段 为 "(?:25[0-5]|2[0-4][0-9])"\n'
            '  设 模式 为 "^(" 加上 段 加上 "\\.){3}" 加上 段 加上 "$"\n'
            '  输出(转文本(re_完全匹配(模式, "99.1.1.1")))\n'
            '  输出(转文本(re_完全匹配(模式, "250.201.202.203")))\n'
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, err
        _对拍(out, ['假', '真'])

    def test_IP反例全集(self):
        """恢复 IP 反例：越界段 / 段数不足均判定不匹配。"""
        code = (
            '从 正则表达式 导入 验证IP地址\n'
            '段落 主:\n'
            '  输出(验证IP地址("999.1.1.1"))\n'
            '  输出(验证IP地址("256.1.1.1"))\n'
            '  输出(验证IP地址("1.2.3"))\n'
            '  输出(验证IP地址("0.0.0.0"))\n'
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, err
        _对拍(out, ['假', '假', '假', '真'])

    def test_捕获组多选分支回溯组表正确(self):
        """捕获组在多选分支回溯后，组表应恢复到分支前状态。"""
        code = (
            '从 re 导入 re_完全匹配\n'
            '段落 主:\n'
            '  # (a|ab)c 对 "abc"：分支1 a 匹配后 c 失败，回溯分支2 ab 匹配后 c 成功\n'
            '  输出(转文本(re_完全匹配("(a|ab)c", "abc")))\n'
            '  输出(转文本(re_完全匹配("(a|ab)c", "ac")))\n'
            '  输出(转文本(re_完全匹配("(a|ab)c", "adc")))\n'
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, err
        _对拍(out, ['真', '真', '假'])


# ══════════════════════════════════════════════════════════════════════
# T6A-11：连续 20 次正则验证调用内存安全
# ══════════════════════════════════════════════════════════════════════

class TestT6A11_MemorySafety:
    """T6A-11：回溯 VM 列表操作内存安全（realloc 后引用失效 + 泄漏）。"""

    def test_20次连续验证调用_不崩且正确(self):
        """同一程序内 20 次连续正则验证调用，O0 下不崩且全部结果正确。"""
        code = (
            '从 正则表达式 导入 验证邮箱 验证手机号 验证身份证号 验证URL 验证IP地址 验证IPv6地址\n'
            '从 正则表达式 导入 验证日期 验证时间 验证日期时间 验证中文字符 验证数字 验证浮点数\n'
            '段落 主:\n'
            '  输出(验证邮箱("a.b-c%d@x-y.co"))\n'
            '  输出(验证邮箱("bad@@x.co"))\n'
            '  输出(验证手机号("13812345678"))\n'
            '  输出(验证手机号("12812345678"))\n'
            '  输出(验证身份证号("11010519491231002X"))\n'
            '  输出(验证身份证号("11010519491231002"))\n'
            '  输出(验证URL("https://a.b/c/d"))\n'
            '  输出(验证URL("ftp://a.b/"))\n'
            '  输出(验证IP地址("192.168.1.1"))\n'
            '  输出(验证IPv6地址("2001:0db8:85a3:0000:0000:8a2e:0370:7334"))\n'
            '  输出(验证日期("2026-06-16"))\n'
            '  输出(验证日期("2026-13-01"))\n'
            '  输出(验证时间("23:59:59"))\n'
            '  输出(验证日期时间("2026-06-16 08:30:00"))\n'
            '  输出(验证中文字符("光明"))\n'
            '  输出(验证中文字符("光明a"))\n'
            '  输出(验证数字("-42"))\n'
            '  输出(验证数字("4-2"))\n'
            '  输出(验证浮点数("3.14"))\n'
            '  输出(验证浮点数("3"))\n'
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, f"20次调用崩溃 rc={rc} err={err}"
        _对拍(out, [
            '真', '假', '真', '假', '真', '假',
            '真', '假', '真', '真',
            '真', '假', '真', '真', '真',
            '假', '真', '假', '真', '假',
        ])

    def test_重复匹配同一模式_不泄漏状态(self):
        """对同一模式重复匹配失败/成功交替，回点列表不应累积污染。"""
        code = (
            '从 re 导入 re_完全匹配\n'
            '段落 主:\n'
            '  设 i 为 0\n'
            '  当 i < 10:\n'
            '    输出(转文本(re_完全匹配("a*b", "aaab")))\n'
            '    输出(转文本(re_完全匹配("a*b", "c")))\n'
            '    设 i 为 i + 1\n'
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, err
        期望 = []
        for _ in range(10):
            期望.extend(['真', '假'])
        _对拍(out, 期望)

    def test_星号量词嵌套回溯_不崩(self):
        """嵌套 * 量词深度回溯，回点列表反复扩容不应失效。"""
        code = (
            '从 re 导入 re_包含\n'
            '段落 主:\n'
            '  输出(转文本(re_包含("(a*)*", "aaa")))\n'
            '  输出(转文本(re_包含("(a*b*)*", "ababab")))\n'
            '  输出(转文本(re_包含("(a|b)*", "abba")))\n'
            '  输出(转文本(re_包含("(a|b)*c", "abba")))\n'
        )
        rc, out, err = _编译并运行(code)
        assert rc == 0, err
        _对拍(out, ['真', '真', '真', '假'])
