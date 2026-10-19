#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R160-A L-219 协程缺陷回归门（主 agent 收口「修假绿」后重写）。

修前 A 线版本把断言包在 `try/except Exception: return False`：SIGSEGV/断言失败
都被吞 → pytest 下用例**永不失败**（假绿，A 的「回归/反跑」证据因此无效）。本版：
· 去掉一切吞异常，原生编译+跑产物，直接对「退出码 + 输出」断言，回归即红；
· 复跑复用 test_native_cli 同款 harness（`_native_helpers.仓库根` + `compile_light_typed`），
  产物落 TemporaryDirectory，源码树不留 .ll/.o/.exe；`@skip_without_clang` 无 clang 则跳。

钉住 L-219 两个子缺陷：
  1. 恢复分派：协程 await 后恢复不得跳过后续语句（R159 L1 `协程-0` 红）。
  2. self 绑定：类内异步方法协程 resume 后 `自.字段` 可读、进程不 SIGSEGV。
"""
import os
import sys
import subprocess
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _native_helpers import 仓库根, skip_without_clang  # type: ignore[import]

sys.path.insert(0, os.path.join(仓库根, 'src'))

子进程口径 = dict(capture_output=True, text=True, encoding='utf-8', errors='replace')


def _编译并运行(源码文本, 名字, 优化级别=0):
    """`compile_light_typed` → 跑 exe，返回 (退出码, stdout 非空行列表)。"""
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    with tempfile.TemporaryDirectory(prefix=f'_r160a_{名字}_') as 临时目录:
        源文件 = os.path.join(临时目录, f'{名字}.light')
        with open(源文件, 'w', encoding='utf-8') as fh:
            fh.write(源码文本)
        产物基名 = os.path.join(临时目录, f'{名字}_O{优化级别}')
        exe = compile_light_typed(源文件, 产物基名, optimize_level=优化级别)
        结果 = subprocess.run([exe], timeout=60, **子进程口径)
        return 结果.returncode, [行.strip() for 行 in 结果.stdout.splitlines() if 行.strip()]


# 子缺陷①：顶层异步段 + 事件循环（R159 L1 协程-0 红即此），与 test_native_cli 同源。
_恢复源码 = (
    '异步 段落 测试睡眠：\n'
    '    输出("sleep前")\n'
    '    睡眠(2)\n'
    '    输出("sleep后")\n'
    '结束\n'
    '\n'
    '输出("开始")\n'
    '测试睡眠()\n'
    '运行事件循环()\n'
    '输出("结束")\n'
)

# 子缺陷②：类内异步方法 + 创建任务 + 事件循环；resume 后访问 `自.名字`
# ——self 绑定为空即空取下标 SIGSEGV（rc=-11）、且缺「心跳后」。
# 语法照节点核心.light：类体字段 `设 X 等于 初值`；构造 `段落 构造():`；实例化用 `新建`；`
# `创建任务(实例.类内异步方法())` 在异步段内创协程（= L-219 子缺陷② 触发路径）。
_自绑源码 = (
    '类 测试类:\n'
    '    设 名字 等于 ""\n'
    '\n'
    '    段落 构造():\n'
    '        设 己.名字 为 "节点A"\n'
    '\n'
    '    异步 段落 心跳一次(自):\n'
    '        输出("心跳 " + 自.名字)\n'
    '        等待 异步睡眠(0.05)\n'
    '        输出("心跳后 " + 自.名字)\n'
    '\n'
    '异步 段落 跑():\n'
    '    设 实例 为 新建 测试类()\n'
    '    设 任 为 创建任务(实例.心跳一次())\n'
    '\n'
    '跑()\n'
    '运行事件循环()\n'
)


@skip_without_clang
class TestL219协程:
    def test_恢复分派_await后语句不跳过(self):
        """子缺陷①：await 后恢复不得跳过后续语句（L1 协程-0 红）。"""
        退出码, 输出行 = _编译并运行(_恢复源码, '恢复')
        assert 退出码 == 0, f'退出码异常: {退出码}'
        assert 输出行 == ['开始', 'sleep前', 'sleep后', '结束'], f'输出不符: {输出行}'

    def test_self绑定_类内异步方法协程不崩(self):
        """子缺陷②：类内异步方法协程 resume 后 `自.字段` 可读、进程不 SIGSEGV。"""
        退出码, 输出行 = _编译并运行(_自绑源码, '自绑')
        assert 退出码 == 0, f'退出码异常（可能 SIGSEGV={退出码}）: {退出码}'
        for 需有 in ('心跳 节点A', '心跳后 节点A'):
            assert 需有 in 输出行, f'缺少预期输出 {需有!r}: {输出行}'
