# -*- coding: utf-8 -*-
"""L-093 / L-094 诊断缺陷定向用例（R74 任务A）。

L-094：入口目录同名文件静默遮蔽项目 src/ 同名模块——
    入口在 examples/、真实模块住在 src/，而 examples/ 里恰好有同名空壳时，
    解析会静默命中空壳，编译期零提示，运行期才炸 `name '...' is not defined`。
    期望：出现点名两条路径的中文遮蔽诊断（stderr，不污染 stdout）。

L-093：跨模块异常位置块错锚——
    依赖模块内抛异常时，位置/片段要指向**真实抛出模块**的 .light 文件与行号；
    入口自身报错时不得错锚到依赖源码；`导入 pkg.深层` 形式下模块对象执行帧
    （filename 为模块名）也要能归因。
"""

import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_ROOT, 'src'), _ROOT, os.path.join(_ROOT, 'cli')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cli.light import _run_src, _resolve_local_imports   # noqa: E402
from enhanced_errors import ErrorFormatter               # noqa: E402


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return path


class TestL094ImportShadowDiagnostic(unittest.TestCase):
    """L-094：同名遮蔽必须给出诊断，禁止静默。"""

    def _make_project(self, tmp, with_src_module=True):
        _write(os.path.join(tmp, 'examples', '主.light'),
               '从 工具 导入 甲。\n输出(甲())。\n')
        # examples/ 下的同名空壳（没有 段落 甲）——遮蔽源
        _write(os.path.join(tmp, 'examples', '工具.light'), '# 空壳\n')
        if with_src_module:
            _write(os.path.join(tmp, 'src', '工具.light'),
                   '段落 甲：\n  返回 7\n结束\n')

    def test_shadow_emits_diagnostic_naming_both_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._make_project(tmp, with_src_module=True)
            entry = os.path.join(tmp, 'examples', '主.light')
            src_main = open(entry, encoding='utf-8').read()
            import io
            from contextlib import redirect_stderr
            err = io.StringIO()
            with redirect_stderr(err):
                _resolve_local_imports(src_main, os.path.dirname(entry))
            msg = err.getvalue()
            self.assertIn('L-094', msg, '缺少 L-094 遮蔽诊断')
            self.assertIn('工具', msg)
            # 诊断必须点名两条路径（解析结果 + src/ 同名模块）
            self.assertIn(os.path.join('examples', '工具.light'), msg)
            self.assertIn(os.path.join(tmp, 'src', '工具.light'), msg)

    def test_no_shadow_no_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._make_project(tmp, with_src_module=False)
            entry = os.path.join(tmp, 'examples', '主.light')
            src_main = open(entry, encoding='utf-8').read()
            import io
            from contextlib import redirect_stderr
            err = io.StringIO()
            with redirect_stderr(err):
                _resolve_local_imports(src_main, os.path.dirname(entry))
            self.assertNotIn('L-094', err.getvalue())

    def test_env_switch_disables_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._make_project(tmp, with_src_module=True)
            entry = os.path.join(tmp, 'examples', '主.light')
            src_main = open(entry, encoding='utf-8').read()
            import io
            from contextlib import redirect_stderr
            old = os.environ.get('LIGHT_WARN_IMPORT_SHADOW')
            os.environ['LIGHT_WARN_IMPORT_SHADOW'] = '0'
            try:
                err = io.StringIO()
                with redirect_stderr(err):
                    _resolve_local_imports(src_main, os.path.dirname(entry))
                self.assertNotIn('L-094', err.getvalue())
            finally:
                if old is None:
                    os.environ.pop('LIGHT_WARN_IMPORT_SHADOW', None)
                else:
                    os.environ['LIGHT_WARN_IMPORT_SHADOW'] = old


class _RunCtx:
    """跑一个临时光明项目，抓取运行期异常与格式化输出。"""

    def __init__(self, files):
        self.tmp = tempfile.mkdtemp(prefix='l093_')
        for rel, text in files.items():
            _write(os.path.join(self.tmp, rel), text)
        self.entry = os.path.join(self.tmp, '主.light')

    def formatted_error(self):
        src_main = open(self.entry, encoding='utf-8').read()
        try:
            _run_src(src_main, file_path=self.entry)
        except Exception as e:  # noqa: BLE001
            self.exc = e
            return ErrorFormatter().format_error(
                src_main, e,
                py_code=getattr(e, '_light_py_code', None),
                file_path=self.entry)
        raise AssertionError('预期运行期异常，但程序正常结束')

    def cleanup(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestL093CrossModuleErrorLocation(unittest.TestCase):
    """L-093：异常位置/片段指向真实抛出模块，而非入口调用点。"""

    def test_dep_module_error_points_to_dep(self):
        ctx = _RunCtx({
            '主.light': '从 依赖 导入 会炸。\n会炸()。\n',
            '依赖.light': '段落 会炸：\n  返回 1/0\n结束\n',
        })
        try:
            out = ctx.formatted_error()
            # 位置标注指向依赖模块与真实行（返回 1/0 在第 2 行）
            self.assertIn('依赖', out)
            self.assertIn('2', out)
            # 片段是依赖模块的真实抛出行，不是入口调用点
            self.assertIn('返回 1/0', out)
            self.assertNotIn('会炸()。', out.split('建议')[0])
        finally:
            ctx.cleanup()

    def test_entry_error_not_anchored_to_dep_source(self):
        # 入口自身 1/0，但带了健康的依赖模块——旧缺陷会把片段错锚到依赖源码
        ctx = _RunCtx({
            '主.light': '从 工具 导入 加倍。\n\n设 x 为 1/0。\n输出(加倍(x))。\n',
            '工具.light': '段落 加倍(n)：\n  返回 n 乘 2\n结束\n',
        })
        try:
            out = ctx.formatted_error()
            self.assertIn('除零', out)
            # 片段必须是入口自己的错误行
            self.assertIn('设 x 为 1/0', out)
            # 不得出现依赖模块的源码内容
            self.assertNotIn('返回 n 乘 2', out)
        finally:
            ctx.cleanup()

    def test_dotted_module_object_frame_attributed(self):
        # `导入 pkg.深层` 形式：依赖以「模块名」为 filename 单独 compile+exec，
        # 其帧既非 .light 也非 <string>，旧版直接漏配到入口帧。
        ctx = _RunCtx({
            '主.light': '导入 pkg.深层。\n\n输出(pkg.深层.炸())。\n',
            os.path.join('pkg', '深层.light'):
                '段落 炸()：\n  返回 1/0\n结束\n\n段落 好()：\n  返回 5\n结束\n',
        })
        try:
            out = ctx.formatted_error()
            self.assertIn('pkg.深层', out, '跨模块异常未标注真实模块名')
            self.assertIn('返回 1/0', out, '片段未指向依赖模块真实抛出行')
            self.assertIn('2', out)
        finally:
            ctx.cleanup()

    def test_deep_chain_error_points_to_innermost_dep(self):
        # 入口 → 工具 → 底层 三级链：异常在 底层，位置/片段要指向 底层 的真实行
        ctx = _RunCtx({
            '主.light': '从 工具 导入 中转。\n\n中转()。\n',
            '工具.light': '从 底层 导入 炸点。\n\n段落 中转()：\n  炸点()\n结束\n',
            '底层.light': '段落 炸点()：\n  设 x 为 1\n  输出(不存在的东西)\n  返回 x\n结束\n',
        })
        try:
            out = ctx.formatted_error()
            self.assertIn('底层', out, '跨模块异常未标注真实模块名')
            self.assertIn('输出(不存在的东西)', out, '片段未指向底层模块真实抛出行')
        finally:
            ctx.cleanup()


if __name__ == '__main__':
    unittest.main()
