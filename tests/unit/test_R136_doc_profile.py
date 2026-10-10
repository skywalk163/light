# -*- coding: utf-8 -*-
"""R136 D线：doc_generator / profiler 单元测试。

覆盖：
- doc_generator 模块可导入，run_doc 可调用
- 对最小 .light 源抽出段落名 / 类名 / 全局变量
- Markdown 输出含概览与真实符号
- profiler 模块可导入，run_profile 可调用
- profiler 输出含分阶段（词法/语法/代码生成）
- 写文件模式落盘成功

不引入新依赖，仅用标准库 tempfile / os / sys。
"""
import os
import sys
import unittest
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_HERE, '..', '..', 'src'))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


SAMPLE_LIGHT = """\
导入 内置核心字典。

《加一》段(值: 数) -> 数:
  返回 值 加 一。
结束。

《造点》段(x: 数, y: 数):
  打印 x。
结束。

设 计数 为 零。

类 校验器:
  属性 占位 等于 空

  段落 构造:
    设 己.占位 为 0

  段落 取占位(己) -> 数:
    返回 己.占位
结束。
"""


class TestDocGenerator(unittest.TestCase):
    def test_importable(self):
        import doc_generator
        self.assertTrue(callable(doc_generator.run_doc))
        self.assertTrue(hasattr(doc_generator, 'DocGenerator'))

    def test_extracts_paragraph_names(self):
        from doc_generator import DocGenerator
        with tempfile.NamedTemporaryFile('w', suffix='.light', delete=False, encoding='utf-8') as f:
            f.write(SAMPLE_LIGHT)
            path = f.name
        try:
            md = DocGenerator().generate_markdown(path)
            # 真实符号必须出现在输出里
            self.assertIn('加一', md)
            self.assertIn('造点', md)
            self.assertIn('段落（函数）：**2**', md)
        finally:
            os.unlink(path)

    def test_extracts_class(self):
        from doc_generator import DocGenerator
        with tempfile.NamedTemporaryFile('w', suffix='.light', delete=False, encoding='utf-8') as f:
            f.write(SAMPLE_LIGHT)
            path = f.name
        try:
            md = DocGenerator().generate_markdown(path)
            self.assertIn('校验器', md)
            self.assertIn('类：**1**', md)
            self.assertIn('取占位', md)
        finally:
            os.unlink(path)

    def test_markdown_overview_section(self):
        from doc_generator import DocGenerator
        with tempfile.NamedTemporaryFile('w', suffix='.light', delete=False, encoding='utf-8') as f:
            f.write(SAMPLE_LIGHT)
            path = f.name
        try:
            md = DocGenerator().generate_markdown(path)
            self.assertIn('# API 文档', md)
            self.assertIn('## 概览', md)
            self.assertIn('## 段落（函数）', md)
        finally:
            os.unlink(path)

    def test_run_doc_writes_file(self):
        import doc_generator
        with tempfile.NamedTemporaryFile('w', suffix='.light', delete=False, encoding='utf-8') as f:
            f.write(SAMPLE_LIGHT)
            src = f.name
        out_dir = tempfile.mkdtemp()
        out_file = os.path.join(out_dir, 'out.md')
        try:
            doc_generator.run_doc(src, 'markdown', out_file)
            self.assertTrue(os.path.exists(out_file))
            with open(out_file, encoding='utf-8') as f:
                content = f.read()
            self.assertIn('加一', content)
            self.assertIn('校验器', content)
        finally:
            os.unlink(src)


class TestProfiler(unittest.TestCase):
    def test_importable(self):
        import profiler
        self.assertTrue(callable(profiler.run_profile))

    def test_profile_returns_phase_breakdown(self):
        # run_profile 打印到 stdout；重定向捕获
        import profiler
        import io
        from contextlib import redirect_stdout
        with tempfile.NamedTemporaryFile('w', suffix='.light', delete=False, encoding='utf-8') as f:
            f.write(SAMPLE_LIGHT)
            path = f.name
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                profiler.run_profile(path, memory=True, report=False, cprofile=False)
            out = buf.getvalue()
            # 分阶段必须出现
            self.assertIn('词法分析', out)
            self.assertIn('语法解析', out)
            self.assertIn('代码生成', out)
            self.assertIn('编译耗时', out)
        finally:
            os.unlink(path)

    def test_profile_memory_shown(self):
        import profiler
        import io
        from contextlib import redirect_stdout
        with tempfile.NamedTemporaryFile('w', suffix='.light', delete=False, encoding='utf-8') as f:
            f.write(SAMPLE_LIGHT)
            path = f.name
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                profiler.run_profile(path, memory=True, report=False, cprofile=False)
            out = buf.getvalue()
            self.assertIn('内存', out)
            self.assertIn('峰值', out)
        finally:
            os.unlink(path)


if __name__ == '__main__':
    unittest.main()
