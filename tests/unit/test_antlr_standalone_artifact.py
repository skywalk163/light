# -*- coding: utf-8 -*-
"""L-181 回归：unified/ANTLR 腿 compile 落盘产物可独立运行。

根因：src/code_generator_unified.py 发射产物序言时把 `_light_stdlib`
的赋值缩进进了 `except NameError:` 分支。独立 `python p.py` 时
`__file__` 存在 → 不进 except → `_light_stdlib` 从未赋值 → NameError。

本用例钉住三条链路：
1. hello.light compile → 独立子进程运行 rc=0 + 输出正确
2. 三 FFI 示例 compile rc=0 + py_compile 通过 + 产物含 ctypes.CDLL
   （不在测试里真跑 FFI 产物：示例链接 libm.so.6/libc.so.6，Windows 必败）
3. 反向哨兵：产物源码存在顶格 `_light_stdlib = ` 行（防将来又被缩进回去）
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_EXAMPLES = os.path.join(_ROOT, 'examples')


def _compile(light_rel, out_path):
    """用 unified CLI 的 antlr 后端编译 .light 到 out_path，返回 CompletedProcess。"""
    cmd = [sys.executable, '-m', 'cli.light_unified', 'compile',
           os.path.join(_EXAMPLES, light_rel), '--backend', 'antlr', '-o', out_path]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=_ROOT)


class TestAntlrArtifactStandalone(unittest.TestCase):
    """ANTLR 后端 compile 落盘产物可独立运行（L-181）。"""

    def test_hello_compile_and_run_standalone(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'hello.py')
            r = _compile('hello.light', out)
            self.assertEqual(r.returncode, 0, 'compile failed:\n' + r.stderr)
            self.assertTrue(os.path.isfile(out), '产物未生成')

            # 独立子进程运行（不是 exec，是真正的 python 子进程）
            run = subprocess.run([sys.executable, out], capture_output=True, text=True, cwd=tmp)
            self.assertEqual(run.returncode, 0,
                             '独立运行失败 rc=%d\nSTDOUT:%s\nSTDERR:%s'
                             % (run.returncode, run.stdout, run.stderr))
            self.assertIn('你好，世界！', run.stdout)
            self.assertIn('程序运行完成！', run.stdout)

    def test_ffi_examples_compile_and_py_compile(self):
        """三 FFI 示例：compile rc=0 + py_compile 通过 + 含 ctypes.CDLL。
        不真跑产物（Windows 上 libm.so.6/libc.so.6 不存在）。"""
        for name in ('ffi_math', 'ffi_system', 'ffi_comprehensive'):
            with self.subTest(ffi=name):
                with tempfile.TemporaryDirectory() as tmp:
                    out = os.path.join(tmp, name + '.py')
                    r = _compile(name + '.light', out)
                    self.assertEqual(r.returncode, 0,
                                     name + ' compile failed:\n' + r.stderr)
                    self.assertTrue(os.path.isfile(out))

                    # py_compile
                    pc = subprocess.run(
                        [sys.executable, '-c',
                         'import py_compile;py_compile.compile(' + repr(out) + ',doraise=True)'],
                        capture_output=True, text=True, cwd=tmp)
                    self.assertEqual(pc.returncode, 0,
                                     name + ' py_compile failed:\n' + pc.stderr)

                    # 含 ctypes 绑定
                    with open(out, 'r', encoding='utf-8') as f:
                        src = f.read()
                    self.assertIn('ctypes.CDLL', src,
                                  name + ' 产物不含 ctypes.CDLL 绑定')

    def test_stdlib_assignment_is_top_level_not_in_except(self):
        """反向哨兵：产物中 `_light_stdlib` 的初始赋值必须顶格，
        不能缩进在 except NameError 分支内（L-181 的根因形态）。"""
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'hello.py')
            r = _compile('hello.light', out)
            self.assertEqual(r.returncode, 0)
            with open(out, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # ① 存在顶格的 _light_stdlib = 赋值行
            top_level = [ln for ln in lines if re.match(r'^_light_stdlib\s*=\s*', ln)]
            self.assertTrue(top_level,
                            '产物中不存在顶格的 `_light_stdlib = ` 赋值行——可能又被缩进进 except 分支了')

            # ② except NameError: 块内（缩进行）不应有 _light_stdlib 赋值
            in_except = False
            for ln in lines:
                if ln.startswith('except NameError:'):
                    in_except = True
                    continue
                if in_except:
                    if ln.strip() == '' or ln.startswith('    '):
                        self.assertFalse(
                            re.match(r'^\s+_light_stdlib\s*=\s*', ln),
                            '_light_stdlib 赋值被缩进进 except 分支了: ' + repr(ln))
                    else:
                        in_except = False


if __name__ == '__main__':
    unittest.main()
