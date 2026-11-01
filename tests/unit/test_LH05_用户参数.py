# -*- coding: utf-8 -*-
"""LH-05 / L-241：CLI 读不到用户参数，`light run -- args` 也不支持。

## 为什么必须 subprocess 真起进程

`参数列表()` 读的是**进程级** `sys.argv`，而 `.light` 不是进程入口 ——
它是被 `light run` 加载执行的，那一刻 `sys.argv` 是 CLI 自己的。
这条缺陷的全部内容都在「进程边界」上：import 一个函数、改一改环境变量就能变绿的测试，
**证不了命令行上真的通**。所以本文件 4 个用例全部 `subprocess.run([sys.executable, '-m', 'cli.light', ...])`。

## 判据

1. `light run <入口> -- 甲 乙` → 脚本拿到的参数恰为 `['甲', '乙']`；
2. 带 `--backend src` 之类的 CLI 选项时，选项**不被 `--` 之后的实参污染**，且实参仍原样透传；
3. 无 `--` 时**维持现状**（退化为宿主 argv），只断言「不崩」，不锁死具体内容；
4. 参数含空格 / 中文 / 引号时**原样到达**（证明没有哪一层做了二次解释）；
5. `用户参数()`（显式别名）与 `参数列表()` 在注入路径下口径一致。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 探针：把两条口径各打一行 JSON，便于断言「到底是什么」而不只是「有没有崩」。
_探针 = """打印 转字符串(参数列表())
打印 转字符串(用户参数())
"""


def _跑(实参, 源码=_探针):
    """真起一个 `python -m cli.light run ...` 子进程，返回 (rc, stdout, stderr)。"""
    with tempfile.TemporaryDirectory() as d:
        入口 = os.path.join(d, "探针.light")
        with open(入口, "w", encoding="utf-8") as f:
            f.write(源码)
        p = subprocess.run(
            [sys.executable, "-m", "cli.light", "run", 入口] + 实参,
            cwd=_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=180,
        )
        return p.returncode, p.stdout, p.stderr


def _取两行(stdout):
    """取探针的两行输出（可能有编译告警混进来，取最后两行非空行）。"""
    行 = [l for l in stdout.splitlines() if l.strip()]
    assert len(行) >= 2, f"探针输出不足两行：{stdout!r}"
    return 行[-2], 行[-1]


class TestLH05用户参数(unittest.TestCase):
    """`light run <入口> -- 用户实参...` 的全链路。"""

    def test_一_分隔符之后的实参原样到达(self):
        rc, out, err = _跑(["--", "甲", "乙"])
        self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
        参数表行, 用户行 = _取两行(out)
        self.assertEqual(json.loads(参数表行), ["甲", "乙"])
        self.assertEqual(json.loads(用户行), ["甲", "乙"])

    def test_二_自带选项不被用户实参污染(self):
        # `--backend src` 在 `--` 之前：它是 CLI 的选项，不是脚本的实参。
        rc, out, err = _跑(["--backend", "src", "--", "甲", "乙"])
        self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
        参数表行, 用户行 = _取两行(out)
        self.assertEqual(json.loads(参数表行), ["甲", "乙"])
        self.assertEqual(json.loads(用户行), ["甲", "乙"])
        # 选项确实被 CLI 吃掉了，没混进用户实参里
        self.assertNotIn("--backend", 用户行)

    def test_三_分隔符之后以短横线开头的实参不被当成选项(self):
        # 用户实参自己带 `--开关`：它属于脚本，不该被 argparse 当 CLI 选项拒掉。
        rc, out, err = _跑(["--", "--开关", "值"])
        self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
        参数表行, 用户行 = _取两行(out)
        self.assertEqual(json.loads(用户行), ["--开关", "值"])

    def test_四_不传分隔符时维持现状且不崩(self):
        # 存量脚本靠 `参数列表()` 拿宿主 argv 也能跑；这里只断言「不崩、有输出」，
        # 不锁死具体内容 —— 宿主 argv 的形状取决于怎么起的进程，锁死就是脆弱断言。
        rc, out, err = _跑([])
        self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
        self.assertTrue(out.strip(), "无 `--` 时脚本应当照常跑出内容")

    def test_五_空格中文引号原样到达(self):
        # 三个值分别含空格 / 中文+空格 / 双引号：证明没有任何一层做了二次解释。
        样本 = ["a b", "甲 乙", 'x"y']
        rc, out, err = _跑(["--"] + 样本)
        self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
        参数表行, 用户行 = _取两行(out)
        self.assertEqual(json.loads(参数表行), 样本)
        self.assertEqual(json.loads(用户行), 样本)

    def test_六_分隔符后无实参时为空表且不崩(self):
        rc, out, err = _跑(["--"])
        self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
        参数表行, 用户行 = _取两行(out)
        self.assertEqual(json.loads(参数表行), [])
        self.assertEqual(json.loads(用户行), [])


class TestLH05边界(unittest.TestCase):
    """别的手不能被动：非 run 子命令的 `--` 语义不被这次改动切走。"""

    def test_非run子命令不切开分隔符(self):
        # `check` 没有 `--` 透传语义；切开用户实参只对 `run` 生效，
        # 所以这里 `--` 应当照旧被 argparse 处理（不崩即可，不锁死具体行为）。
        from cli.light import 切开用户实参
        argv, 用户实参 = 切开用户实参(["check", "x.light", "--", "甲"])
        self.assertIsNone(用户实参, "`check` 不该被切开用户实参")
        self.assertEqual(argv, ["check", "x.light", "--", "甲"])

    def test_只在第一个裸分隔符处切(self):
        from cli.light import 切开用户实参
        argv, 用户实参 = 切开用户实参(["run", "x.light", "--", "--开关", "--", "乙"])
        self.assertEqual(argv, ["run", "x.light"])
        self.assertEqual(用户实参, ["--开关", "--", "乙"])


if __name__ == "__main__":
    unittest.main()
