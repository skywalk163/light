# -*- coding: utf-8 -*-
"""
LP-D-002 回归测试：未定义名命中 stdlib 导出表时给出"缺导入"提示。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from enhanced_errors import ErrorFormatter


def _fmt(name):
    err = NameError(f"name '{name}' is not defined")
    src = '段落 主:\n  设 p 为 %s("abc", "b")\n主()\n' % name
    return ErrorFormatter().format_error(src, err)


class TestLpd002ImportHint:
    def test_known_stdlib_fn_suggests_import(self):
        out = _fmt('子串位置')
        assert '从 字符串处理 导入 子串位置' in out, out
        assert '先通过「设」' not in out, out

    def test_dict_keys_import(self):
        out = _fmt('字典键列表')
        assert '从 内置核心字典 导入 字典键列表' in out, out

    def test_generic_name_keeps_generic_advice(self):
        out = _fmt('不存在的变量')
        # 不在 stdlib 表 → 通用"先定义"建议
        assert '先通过「设」' in out, out

    def test_no_false_positive_on_global_builtin_name(self):
        # 打印 是全局内置，不在反查表 → 不应建议"从 X 导入 打印"
        out = _fmt('打印')
        assert '从 ' not in out or '导入 打印' not in out, out


if __name__ == '__main__':
    import pytest
    sys.exit(pytest.main([__file__, '-v']))
