# -*- coding: utf-8 -*-
"""
L-255 / L-260 / T-0212 · 写侧比读侧窄 —— 切片赋值不成立、dict 索引赋值不成立。

## 这条门禁在防什么

「读得通的写法，换到写就炸」是最容易让人怀疑自己的一类错误，两条同源：

    设 表 为 [1,2,3,4]
    打印 转字符串(表[1:3])        # ✅ [2, 3]（读走原生切片）
    设 表[0:2] 为 [9,9]           # ✗ 语法错误：期望 右方括号「]」，但得到 冒号「:」  (L-260)

    设 包 为 {"列": [1, 2]}
    打印(包.列[0])                # ✅ 1（读走 _light_attr_get）
    设 包.列[0] 为 5              # ✗ 'dict' object has no attribute '列'          (L-255)

根因（改前）：
- 赋值左值（src/parser_stmt.py）只解析「名字 / 属性 / 单下标」，不认切片下标；
- `设` 路径的属性+索引赋值把「包.列」整个烤进单个 Identifier，写侧照名字发射
  裸 `包.列[0] = 值`，dict 上不成立；
- 读侧有 `_light_attr_get`，写侧没有对称的 `_light_index_set` / `_light_slice_set`。

改后：
- `src/parser_stmt.py`：赋值左值下标位置支持切片（[起:止:步]），与读侧切片文法
  完全对称；`设` 路径的容器 hop 构造成与读侧相同的 MemberAccess 链。
- `src/code_generator.py`：补 `_light_index_set(对象, 键, 索引, 值)` /
  `_light_slice_set(对象, 键, 起, 止, 步, 值)`，与读侧 `_light_attr_get` 对称；
  dict / list / 类实例 × 单下标 / 切片组合矩阵全绿（下方 Test下标与切片写矩阵）。

## 反跑判据（改坏了会红）

- 删掉 `_parse_index_or_slice_suffix` 的切片分支 → Test解析切片左值 全红；
- 把 `_try_emit_container_index_write` 退回裸 `包.列[0] = 值` →
  Test发射形态 与 TestL255dict索引写 全红；
- 删掉 `_light_index_set` / `_light_slice_set` 辅助 → Test发射形态 红；
- 破坏读侧表达式求值（切片/属性读）→ Test边界_读侧既有行为不受影响 红。

运行方式：pytest tests/unit/test_LH38_下标与切片写.py -v
"""

import contextlib
import io
import os
import sys
import types

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, "src"), os.path.join(_ROOT, "stdlib"),
           os.path.join(_ROOT, "cli")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from parser_core import ParseError  # noqa: E402
from light_parser_v3 import LightParser  # noqa: E402
from code_generator import PythonCodeGenerator  # noqa: E402
from cli.light import _run_src  # noqa: E402


# ── 运行辅助：编译 + exec，同时拿 stdout 和命名表 ────────────────────
def _compile(source: str) -> str:
    module = LightParser().parse(source)
    return PythonCodeGenerator().generate(module, is_main=False)


def _exec(source: str):
    """返回 (stdout, 命名空间)。命名空间用于直接断言变量值。"""
    py_code = _compile(source)
    builtin = types.ModuleType('_light_builtin')
    builtin.打印 = print
    builtin.字符串 = str
    namespace = {'_light_builtin': builtin, '__name__': '_lh38_test_'}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(py_code, '<lh38>', 'exec'), namespace)
    return buf.getvalue().replace('\r\n', '\n'), namespace


def _light_run(source: str, tmp_path) -> str:
    """light run 真跑：走 cli.light._run_src（src 后端完整入口，含 stdlib 地板）。"""
    path = tmp_path / '主.light'
    path.write_text(source, encoding='utf-8')
    return _run_src(source, file_path=str(path),
                    stdlib_dir=os.path.join(_ROOT, 'stdlib'))


# ---------------------------------------------------------------------------
# 验收矩阵：dict / list / 类实例 × 单下标 / 切片（light run 真跑）
# ---------------------------------------------------------------------------
class Test下标与切片写矩阵:
    """任务卡组合矩阵全绿；每行都是 light run 真跑（不是只解析）。"""

    def test_list单下标(self, tmp_path):
        out = _light_run(
            '设 表 为 [1,2,3,4]\n'
            '设 表[0] 为 9\n'
            '打印 转字符串(表)\n', tmp_path)
        assert out.strip() == '[9, 2, 3, 4]'

    def test_list切片_长度不变(self, tmp_path):
        out = _light_run(
            '设 表 为 [1,2,3,4]\n'
            '设 表[0:2] 为 [9,9]\n'
            '打印 转字符串(表)\n', tmp_path)
        assert out.strip() == '[9, 9, 3, 4]'

    def test_dict键下标(self, tmp_path):
        out = _light_run(
            '设 包 为 {"列": [1, 2]}\n'
            '设 包["列"][0] 为 5\n'
            '打印 转字符串(包)\n', tmp_path)
        assert out.strip() == '{"列": [5, 2]}'

    def test_dict点属性下标_L255(self, tmp_path):
        out = _light_run(
            '设 包 为 {"列": [1, 2]}\n'
            '设 包.列[0] 为 5\n'
            '打印 转字符串(包)\n', tmp_path)
        assert out.strip() == '{"列": [5, 2]}'

    def test_dict点属性切片(self, tmp_path):
        out = _light_run(
            '设 包 为 {"列": [1, 2]}\n'
            '设 包.列[0:1] 为 [7]\n'
            '打印 转字符串(包)\n', tmp_path)
        assert out.strip() == '{"列": [7, 2]}'

    def test_类实例属性下标_存量不回退(self, tmp_path):
        out = _light_run(
            '类 盒子:\n'
            '  构造:\n'
            '    设 己.列 为 [1, 2]\n'
            '盒甲 为 新建 盒子()\n'
            '设 盒甲.列[0] 为 5\n'
            '打印 转字符串(盒甲.列)\n', tmp_path)
        assert out.strip() == '[5, 2]'

    def test_段落体内写(self, tmp_path):
        """矩阵形态写进段落体（函数内）同样成立。"""
        out = _light_run(
            '段落 改:\n'
            '  设 包 为 {"列": [1, 2]}\n'
            '  设 包.列[0] 为 5\n'
            '  设 表 为 [1,2,3,4]\n'
            '  设 表[0:2] 为 [9,9]\n'
            '  返回 转字符串(包) 加上 转字符串(表)\n'
            '打印 改()\n', tmp_path)
        assert out.strip() == '{"列": [5, 2]}[9, 9, 3, 4]'


# ---------------------------------------------------------------------------
# 读-写对拍：先读后写再读，断言读写路径拿到的是同一处
# ---------------------------------------------------------------------------
class Test读写对拍:
    """读路径拿到的句柄必须与写路径落写的是同一处（写不拷贝、读不脱节）。

    `设 句柄 为 包.列` 走读侧（_light_attr_get）拿到内层列表本体；
    随后 `设 包.列[0] 为 5` 走写侧（_light_index_set → 同一把
    _light_attr_get）。若写路径动了拷贝，句柄[0] 仍是 1 —— 对拍即红。
    """

    def test_dict读写同一处(self, tmp_path):
        out = _light_run(
            '设 包 为 {"列": [1, 2]}\n'
            '设 句柄 为 包.列\n'
            '设 读前 为 句柄[0]\n'
            '设 包.列[0] 为 5\n'
            '设 读后 为 句柄[0]\n'
            '打印 转字符串(读前)\n'
            '打印 转字符串(读后)\n', tmp_path)
        assert out.splitlines() == ['1', '5']

    def test_dict读写同一处_切片(self, tmp_path):
        out = _light_run(
            '设 包 为 {"列": [1, 2, 3]}\n'
            '设 句柄 为 包.列\n'
            '设 包.列[0:2] 为 [7, 8]\n'
            '打印 转字符串(句柄)\n', tmp_path)
        assert out.strip() == '[7, 8, 3]'

    def test_list读写同一处(self, tmp_path):
        out = _light_run(
            '设 表 为 [1,2,3,4]\n'
            '设 句柄 为 表\n'
            '设 表[0] 为 9\n'
            '打印 转字符串(句柄[0])\n', tmp_path)
        assert out.strip() == '9'

    def test_类实例读写同一处(self, tmp_path):
        out = _light_run(
            '类 盒子:\n'
            '  构造:\n'
            '    设 己.列 为 [1, 2]\n'
            '盒甲 为 新建 盒子()\n'
            '设 句柄 为 盒甲.列\n'
            '设 盒甲.列[1] 为 7\n'
            '打印 转字符串(句柄[1])\n', tmp_path)
        assert out.strip() == '7'


# ---------------------------------------------------------------------------
# L-255 同族：设 路径的属性写（无索引 / 多级链）也要与读侧对称
# ---------------------------------------------------------------------------
class TestL255同族属性写:
    """`设 包.列 为 [9]` 与 `设 包.内.列[0] 为 5` 是同一病根的近亲：
    设 路径原先发裸 `包.列 = 值`（dict 上 AttributeError），且多级点链
    只收单级就撞「.」报「期望'为'或'等于'」。裸赋值路径（L-096）一直通，
    这里钉住 设 路径与它对齐。"""

    def test_设无索引点属性写_dict(self, tmp_path):
        out = _light_run(
            '设 包 为 {"列": [1, 2]}\n'
            '设 包.列 为 [9]\n'
            '打印 转字符串(包)\n', tmp_path)
        assert out.strip() == '{"列": [9]}'

    def test_设多级点链下标写_dict(self, tmp_path):
        out = _light_run(
            '设 包 为 {"内": {"列": [1]}}\n'
            '设 包.内.列[0] 为 5\n'
            '打印 转字符串(包)\n', tmp_path)
        assert out.strip() == '{"内": {"列": [5]}}'

    def test_裸赋值点属性下标写_dict(self, tmp_path):
        out = _light_run(
            '设 包 为 {"列": [1, 2]}\n'
            '包.列[0] 为 5\n'
            '打印 转字符串(包)\n', tmp_path)
        assert out.strip() == '{"列": [5, 2]}'

    def test_类实例属性写存量不回退(self, tmp_path):
        out = _light_run(
            '类 盒子:\n'
            '  构造:\n'
            '    设 己.名字 为 "初始"\n'
            '盒甲 为 新建 盒子()\n'
            '设 盒甲.名字 为 "旺财"\n'
            '打印 盒甲.名字\n', tmp_path)
        assert out.strip() == '旺财'


# ---------------------------------------------------------------------------
# 解析层：赋值左值切片下标必须解析得了（L-260 原症状是 ParseError）
# ---------------------------------------------------------------------------
class Test解析切片左值:

    @pytest.mark.parametrize("src", [
        '设 表 为 [1,2,3,4]\n设 表[0:2] 为 [9,9]\n',
        '设 表 为 [1,2,3,4]\n设 表[1:] 为 [9]\n',
        '设 表 为 [1,2,3,4]\n设 表[:2] 为 [9,9]\n',
        '设 表 为 [1,2,3,4]\n设 表[0:4:2] 为 [7,8]\n',
        '设 包 为 {"列": [1, 2]}\n设 包.列[0:1] 为 [7]\n',
        '设 表 为 [1,2,3,4]\n表[0:2] 为 [9,9]\n',      # 裸赋值（无 设）同款
        '设 表 为 [1,2,3,4]\n设 表[0:2][0] 为 9\n',     # 切片后接下标
    ])
    def test_切片左值不报语法错(self, src):
        try:
            _compile(src)
        except ParseError as exc:
            raise AssertionError(f'切片左值被拒（L-260 未修？）：{exc}')

    def test_切片左值写值正确(self, tmp_path):
        out = _light_run(
            '设 表 为 [1,2,3,4]\n'
            '设 表[0:4:2] 为 [7,8]\n'
            '打印 转字符串(表)\n', tmp_path)
        assert out.strip() == '[7, 2, 8, 4]'

    def test_无赋值意图的切片仍回落表达式语句(self):
        """`表[0:2]` 单独成行（无 为/等于）不得被赋值分支吞掉报错。"""
        out, _ = _exec('设 表 为 [1,2,3,4]\n打印 转字符串(表[0:2])\n')
        assert out.strip() == '[1, 2]'


# ---------------------------------------------------------------------------
# 发射形态：写侧 helper 与读侧对称（反跑判据的静态锚点）
# ---------------------------------------------------------------------------
class Test发射形态:

    def test_dict点属性下标发_light_index_set(self):
        py = _compile('设 包 为 {"列": [1, 2]}\n设 包.列[0] 为 5\n')
        assert "_light_index_set(包, '列', 0, 5)" in py, py
        # 绝不能再发裸 `包.列[0] = 5`（dict 上 AttributeError 的旧病）
        assert '包.列[0] = 5' not in py, py

    def test_dict点属性切片发_light_slice_set(self):
        py = _compile('设 包 为 {"列": [1, 2]}\n设 包.列[0:1] 为 [7]\n')
        assert ("_light_slice_set(包, '列', "
                "_light_builtin.切片下标检查(0), _light_builtin.切片下标检查(1), "
                "None, [7])") in py, py

    def test_产物含对称辅助函数定义(self):
        py = _compile('设 包 为 {"列": [1, 2]}\n设 包.列[0] 为 5\n')
        assert 'def _light_attr_get(' in py, py   # 读侧
        assert 'def _light_index_set(' in py, py  # 写侧（新增）
        assert 'def _light_slice_set(' in py, py  # 写侧切片版（新增）

    def test_裸名下标写不发helper_产物不变(self):
        """裸名 / 键下标（表[0]、包["列"][0]）走原生形态，产物逐字不变。"""
        py = _compile('设 表 为 [1,2,3,4]\n设 表[0] 为 9\n设 包 为 {}\n设 包["键"] 为 1\n')
        assert '表[0] = 9' in py, py
        assert '包["键"] = 1' in py, py
        assert '_light_index_set(' not in py.replace('def _light_index_set(', ''), py


# ---------------------------------------------------------------------------
# 边界：读侧表达式求值既有行为一字不动（任务卡边界要求）
# ---------------------------------------------------------------------------
class Test边界_读侧既有行为不受影响:

    def test_列表切片读(self):
        out, _ = _exec('设 表 为 [1,2,3,4]\n打印 转字符串(表[1:3])\n')
        assert out.strip() == '[2, 3]'

    def test_dict属性索引读(self):
        out, _ = _exec('设 包 为 {"列": [1, 2]}\n打印(包.列[0])\n')
        assert out.strip() == '1'

    def test_类实例属性读(self, tmp_path):
        out = _light_run(
            '类 盒子:\n'
            '  构造:\n'
            '    设 己.列 为 [1, 2]\n'
            '盒甲 为 新建 盒子()\n'
            '打印 转字符串(盒甲.列[0])\n', tmp_path)
        assert out.strip() == '1'

    def test_下标增量赋值不受影响(self):
        """G-02 增量赋值（加为）与索引复合赋值（加上）既有路径不回退。

        注意走裸赋值形态（`包["列"][0] 加为 1`）：`设` 路径的下标分支
        一直不支持增量动词（与本卡无关，不在本门禁范围）。
        """
        out, _ = _exec('设 包 为 {"列": [1, 2]}\n包["列"][0] 加为 1\n打印(包["列"][0])\n')
        assert out.strip() == '2'
        out, _ = _exec('设 表 为 [1, 2]\n表[0] 加上 3\n打印(表[0])\n')
        assert out.strip() == '4'

    def test_方法调用语句不受影响(self):
        """`graph[u].append(v)` 这类「索引链 + 方法调用」仍走表达式语句。"""
        out, _ = _exec('设 表 为 [[1]]\n设 边 为 0\n表[边].追加(2)\n打印 转字符串(表)\n')
        assert out.strip() == '[[1, 2]]'

    def test_下标读后写再读_整链(self, tmp_path):
        """同组容器先读后写再读的完整链路（任务卡对拍要求的直白版）。"""
        out = _light_run(
            '设 包 为 {"列": [1, 2]}\n'
            '打印 转字符串(包.列[0])\n'
            '设 包.列[0] 为 5\n'
            '打印 转字符串(包.列[0])\n', tmp_path)
        assert out.splitlines() == ['1', '5']
