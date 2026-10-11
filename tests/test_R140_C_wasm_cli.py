#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R140-C：CLI 端到端接通 `--target wasm` 的门禁测试

背景：R139-D 核实 `cli/light_unified.py::compile_with_src` 只有 `if target=='llvm'`
一个专属分支，`--target wasm` 被静默并入 python 后端产出普通 `.py`（§13.3）。
R140-C 按方案 A 补 `elif target=='wasm':` 分支，路由到 `src/wasm_target.py`。

本测试覆盖：
  1. `--target wasm` 默认产出 standalone `.html`（不再产出 `.py`）
  2. `--target wasm -o xxx.html` 显式 HTML 产物
  3. `--target wasm -o xxx.json` 产出 Pyodide JSON（含 python_code/loader_js/error）
  4. stderr 打印提示「wasm target 实为经 Pyodide 执行的 Python」
  5. `--target py` 对照：产出 `.py`，stderr **不**含 wasm 提示（不回归）
  6. `--target llvm` / `--target js` 不回归
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap

import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LIGHT_UNIFIED = os.path.join(_PROJECT_ROOT, 'cli', 'light_unified.py')

_WASM_HINT = 'wasm target 实为经 Pyodide 执行的 Python'

_HELLO = textwrap.dedent("""\
    段 主函数():
        打印("你好，WebAssembly！")
    主函数()
""")


def _run_compile(source: str, target: str, out_name: str = None):
    """在临时目录写 .light，跑 `light_unified.py compile`。

    在临时目录被清理前就读出产物内容，返回
    (rc, stdout, stderr, out_path, content, sidecar_py_exists)。
    """
    with tempfile.TemporaryDirectory(prefix='_r140c_wasm_') as td:
        src = os.path.join(td, 'demo.light')
        with open(src, 'w', encoding='utf-8') as f:
            f.write(source)
        cmd = [sys.executable, _LIGHT_UNIFIED, 'compile', src,
               '--target', target, '--backend', 'src']
        if out_name:
            out_path = os.path.join(td, out_name)
            cmd += ['-o', out_path]
        else:
            suffix = '.html' if target == 'wasm' else '.py'
            out_path = src.replace('.light', suffix)
        p = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=60,
            cwd=_PROJECT_ROOT,
        )
        content = None
        if os.path.exists(out_path):
            with open(out_path, 'r', encoding='utf-8') as f:
                content = f.read()
        # wasm(.html/.json) 旁是否残留同名 .py
        sidecar_py_exists = (
            out_path.endswith(('.html', '.json'))
            and os.path.exists(os.path.splitext(out_path)[0] + '.py')
        )
        return p.returncode, p.stdout, p.stderr, out_path, content, sidecar_py_exists


class TestWasmTargetCli:
    """`light compile x.light --target wasm` 端到端门禁。"""

    def test_默认产出html不再是py(self):
        """C1：不传 -o 时，--target wasm 产出 .html（standalone），而非 .py。"""
        rc, out, err, out_path, content, sidecar_py = _run_compile(_HELLO, 'wasm')
        assert rc == 0, f"rc={rc}\nstdout={out}\nstderr={err}"
        assert out_path.endswith('.html'), f"默认产物后缀应为 .html: {out_path}"
        # 后续 `<html> in content` 断言隐含 content 非空且为字符串
        assert not sidecar_py, "wasm 目标不应再产出同名 .py"
        assert '<!DOCTYPE html>' in content
        assert 'pyodide' in content.lower()
        assert '你好' in content

    def test_stderr打印wasm提示(self):
        """C1：stderr 必须打印「wasm target 实为经 Pyodide 执行的 Python」。"""
        rc, out, err, _, _, _ = _run_compile(_HELLO, 'wasm')
        assert rc == 0, f"rc={rc}\nstdout={out}\nstderr={err}"
        assert _WASM_HINT in err, \
            f"stderr 缺少 wasm 提示语「{_WASM_HINT}」:\n{err}"

    def test_显式html产物(self):
        """C3：-o xxx.html 显式指定时，产出 standalone HTML。"""
        rc, out, err, out_path, content, _ = _run_compile(_HELLO, 'wasm', out_name='page.html')
        assert rc == 0, f"rc={rc}\nstdout={out}\nstderr={err}"
        assert out_path.endswith('.html')
        assert '<!DOCTYPE html>' in content
        assert 'pyodide' in content.lower()

    def test_json产物含pyodide字段(self):
        """C3：-o xxx.json 产出 Pyodide JSON，含 python_code/loader_js/error 三字段。"""
        rc, out, err, out_path, content, _ = _run_compile(_HELLO, 'wasm', out_name='pkg.json')
        assert rc == 0, f"rc={rc}\nstdout={out}\nstderr={err}"
        assert out_path.endswith('.json')
        data = json.loads(content)
        assert 'python_code' in data
        assert 'loader_js' in data
        assert 'error' in data
        assert data['error'] is None, f"编译应成功，error={data['error']}"
        assert 'print' in data['python_code']

    def test_py目标不打印wasm提示(self):
        """C2：--target py 行为不回归——产出 .py，stderr 不含 wasm 提示。"""
        rc, out, err, out_path, content, _ = _run_compile(_HELLO, 'py')
        assert rc == 0, f"rc={rc}\nstdout={out}\nstderr={err}"
        assert out_path.endswith('.py'), f"py 目标产物应为 .py: {out_path}"
        assert _WASM_HINT not in err, \
            f"--target py 不应打印 wasm 提示语:\n{err}"
        # 产物是 Python 代码（非 HTML）
        assert '<!DOCTYPE html>' not in content
        assert 'print' in content

    def test_llvm目标不回归(self):
        """C2：--target llvm 仍走 LLVM IR 分支，不被 wasm 分支劫持。"""
        rc, out, err, out_path, content, _ = _run_compile(_HELLO, 'llvm')
        # llvm 分支失败时会在 stderr 打印错误；只要它没走 wasm 分支即可
        assert _WASM_HINT not in err, \
            f"--target llvm 误入 wasm 分支（打印了 wasm 提示）:\n{err}"
        if rc == 0 and content:
            assert '<!DOCTYPE html>' not in content[:200], \
                "--target llvm 产物不应是 HTML"

    def test_js目标不回归(self):
        """C2：--target js 仍走既有 else 分支（产出 .py），不被 wasm 劫持。"""
        rc, out, err, out_path, content, _ = _run_compile(_HELLO, 'js')
        assert rc == 0, f"rc={rc}\nstdout={out}\nstderr={err}"
        assert out_path.endswith('.py'), f"js 目标既有行为是产出 .py: {out_path}"
        assert _WASM_HINT not in err, \
            f"--target js 不应打印 wasm 提示:\n{err}"
