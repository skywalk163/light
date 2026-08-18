# -*- coding: utf-8 -*-
"""v7 单 29 回归用例（族 4）：编译产物自洽——L3 运行时模块随产物落盘。

对应 examples/L3_domain/demo4_echarts.light、demo5_markdown.light 只有 product
那条腿打红的根因：

`引 Python:` 块里的代码被**原样**塞进产物的 `_LIGHT_L4_SRC` 字符串里 exec
（src/code_generator.py 的 `_generate_embed_block` python 分支），所以示例里
`from l3_echarts import L3ECharts` 这句在产物里照样要解析。而 `l3_echarts.py`
物理上住在编译器的 `src/` 目录：

- 产物引导段只把 `stdlib/` 与项目根铺进 sys.path（src/code_generator.py:611-639），
  **从来没有 `src/` 那一档**；且 `src/` 是包（有 `__init__.py`），包内模块不会
  作为顶层名暴露，`import l3_echarts` 必然 ModuleNotFoundError。
- `duan run` 那条腿之所以是绿的，纯粹因为 cli/light_unified.py:36-42 为编译器
  自己 insert 了 `src/`，`l3_*` 搭了便车 —— 两条腿产物字节完全相同、cwd 也相同，
  差异只在执行进程的 sys.path 由谁铺。

修法与 `_emit_user_modules`（单 D）同构：Python 跑脚本时 sys.path[0] 是脚本所在
目录，compile 时把用到的运行时模块 `.py` 复制到产物**同目录**。判据是
`src/compiler.py` 的 `L3_MODULES` 白名单——白名单外的名字一律不碰，否则就变成
「允许把任意模块往产物目录搬」。

判据全部走「白名单命中集合」与「落盘文件是否存在/内容是否是那个模块」，
不跑子进程、不依赖 Python 版本或平台。
"""

import ast
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_ROOT, 'src'), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cli.light_unified import LightUnifiedCLI       # noqa: E402
from compiler import L3_MODULES                     # noqa: E402


def _deps(source):
    return sorted(LightUnifiedCLI._iter_runtime_module_deps(source))


class TestL3ModuleRegistry(unittest.TestCase):
    def test_whitelist_is_non_empty_and_maps_to_real_files(self):
        # 机制完全靠这张表驱动；表空或表里的模块不存在，机制就是死的
        self.assertTrue(L3_MODULES, 'L3_MODULES 白名单为空')
        for name in L3_MODULES:
            self.assertTrue(
                os.path.isfile(os.path.join(_ROOT, 'src', '%s.py' % name)),
                'L3_MODULES 登记了 %s，但 src/%s.py 不存在' % (name, name))


class TestRuntimeDepDetection(unittest.TestCase):
    """依赖发现：只认真 import 语句，且只认白名单内的名字。"""

    def test_from_import_form(self):
        src = '引 Python:\n    from l3_echarts import L3ECharts\n结束引\n'
        self.assertEqual(_deps(src), ['l3_echarts'])

    def test_plain_import_form(self):
        src = '引 Python:\n    import l3_markdown\n结束引\n'
        self.assertEqual(_deps(src), ['l3_markdown'])

    def test_multiple_modules(self):
        src = ('引 Python:\n'
               '    from l3_echarts import L3ECharts\n'
               '    import l3_markdown\n'
               '结束引\n')
        self.assertEqual(_deps(src), ['l3_echarts', 'l3_markdown'])

    def test_no_l3_import_yields_nothing(self):
        # 缺陷守卫：不得退化成「凡编译都往产物目录搬东西」
        src = '引 Python:\n    import sqlite3, re, os\n结束引\n'
        self.assertEqual(_deps(src), [])

    def test_non_whitelisted_src_module_is_not_picked(self):
        # src/ 里这些是编译器内部模块（泛用名），绝不能被搬进用户产物目录
        src = ('引 Python:\n'
               '    import errors\n'
               '    from version import VERSION\n'
               '    import tokens\n'
               '结束引\n')
        self.assertEqual(_deps(src), [])

    def test_comment_mention_is_not_an_import(self):
        src = ('# 本例演示 from l3_echarts import L3ECharts 的用法\n'
               '引 Python:\n    import re\n结束引\n')
        self.assertEqual(_deps(src), [])

    def test_mid_line_mention_is_not_an_import(self):
        src = '设 说明 为 "from l3_echarts import L3ECharts"\n'
        self.assertEqual(_deps(src), [])

    def test_duplicate_import_reported_once(self):
        src = ('引 Python:\n    import l3_echarts\n结束引\n'
               '引 Python:\n    from l3_echarts import L3ECharts\n结束引\n')
        self.assertEqual(_deps(src), ['l3_echarts'])


class TestRuntimeModuleEmission(unittest.TestCase):
    """落盘：模块 .py 真的出现在产物同目录，且是那个模块。"""

    def setUp(self):
        self.cli = LightUnifiedCLI()

    def test_emits_module_file_next_to_product(self):
        src = '引 Python:\n    from l3_echarts import L3ECharts\n结束引\n'
        with tempfile.TemporaryDirectory() as tmp:
            written = self.cli._emit_runtime_modules(src, tmp)
            self.assertEqual(written, ['l3_echarts'])
            out = os.path.join(tmp, 'l3_echarts.py')
            self.assertTrue(os.path.isfile(out), '模块未落盘到产物同目录')
            with open(out, encoding='utf-8') as f:
                tree = ast.parse(f.read())
            classes = {n.name for n in ast.walk(tree)
                       if isinstance(n, ast.ClassDef)}
            self.assertIn(L3_MODULES['l3_echarts']['class'], classes,
                          '落盘的文件里没有白名单登记的类')

    def test_emits_nothing_when_no_dep(self):
        src = '引 Python:\n    import re\n结束引\n'
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.cli._emit_runtime_modules(src, tmp), [])
            self.assertEqual(os.listdir(tmp), [], '无依赖时仍往产物目录写了东西')

    def test_emitted_module_is_importable_standalone(self):
        # 产物自洽的实质判据：把落盘目录当唯一 sys.path 入口也能 import 到
        import importlib.util
        src = '引 Python:\n    import l3_markdown\n结束引\n'
        with tempfile.TemporaryDirectory() as tmp:
            self.cli._emit_runtime_modules(src, tmp)
            spec = importlib.util.spec_from_file_location(
                'l3_markdown_emitted', os.path.join(tmp, 'l3_markdown.py'))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertTrue(hasattr(mod, L3_MODULES['l3_markdown']['class']))


if __name__ == '__main__':
    unittest.main()
