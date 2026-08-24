# -*- coding: utf-8 -*-
"""D9-S1：`stdlib/路径运算.light` 与 `stdlib/操作系统.light` 定向测试。

**这两个模块是本轮「去 Python 直调」的落点**（路径护栏 32→16、代理工具集 48→2），
所以这里钉的不是「函数能调通」，而是三件会直接影响沙箱判定的事实：

  (a) `归一大小写` 与 `os.path.normcase` **逐字符相等**——护栏的 `核准` 返回值被
      `tests/test_path_guard_light.py:75` 拿 normcase(realpath(...)) 直接比，
      差一个字符就是越界判定错位；
  (b) `分量表` / `在目录树内` 是**分量级**比较，不是裸字符串前缀——兄弟目录
      `根_旁边` 不许被收进 `根`；
  (c) **POSIX 分支在 Windows 上真跑真断言**。平台是入参而不是全局探测，正是为了
      这一条：不然 POSIX 语义永远只能在交付报告里写「未实测」。

每条测试的 docstring 末尾写明**反跑方式**（改哪一行会让它立红）。
"""
import ntpath
import os
import posixpath
import sys

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT)
sys.path.insert(0, os.path.join(_PROJECT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT, 'stdlib'))

import _light_import_hook
_light_import_hook.install([os.path.join(_PROJECT, 'stdlib'), _PROJECT])

import pytest

from 路径运算 import 分隔符, 归一分隔符, 归一大小写, 是绝对, 分量表, 在目录树内
from 操作系统 import 本机平台, 是视窗, 子项表, 子项详表


class Test分隔符与归一:
    def test_两平台分隔符(self):
        """反跑：把 路径运算.light `分隔符` 的 "win32" 判断删掉（永远返回 "/"），
        本条立红。"""
        assert 分隔符("win32") == "\\"
        assert 分隔符("posix") == "/"

    def test_归一分隔符只动Windows(self):
        """POSIX 上 `\\` 是合法文件名字符，动它就是改文件名。

        反跑：把 `归一分隔符` 的平台判断去掉（两平台都替换），
        `test_归一分隔符只动Windows` 的 posix 断言立红。"""
        assert 归一分隔符("a/b\\c", "win32") == "a\\b\\c"
        assert 归一分隔符("a/b\\c", "posix") == "a/b\\c"

    @pytest.mark.parametrize("样本", [
        "C:/A/b", "c:\\A", "X", "C:/MiXeD/Path.TXT", "\\\\主机\\共享\\X",
    ])
    def test_归一大小写与normcase逐字符相等(self, 样本):
        """这条是护栏归一化的**等价性判据**，不是「差不多就行」。

        反跑：把 `归一大小写` 里的 `转小写(...)` 去掉，只留分隔符归一 → 立红。"""
        assert 归一大小写(样本, "win32") == ntpath.normcase(样本)
        assert 归一大小写(样本, "posix") == posixpath.normcase(样本)


class Test绝对性判定:
    @pytest.mark.parametrize("样本,期望", [
        ("c:\\x", True), ("c:/x", True), ("\\x", True), ("/x", True),
        ("\\\\主机\\共享", True),
        ("c:x", False), ("x", False), ("sub\\x", False), ("", False),
    ])
    def test_win32口径(self, 样本, 期望):
        """Windows：分隔符开头（当前盘根）或 `盘符:分隔符` 算绝对；
        `c:x` 是**盘内相对路径**，不算——这条差别是 ntpath.isabs 的真实语义。

        与本机 Python 的一处**刻意差异**：3.13 起 ntpath.isabs("/x") 返回假，
        本实现返回真。差异不改变沙箱结论（见 stdlib/代理工具集.light 解析路径
        的注释：两条路最后都落到 核准 判越界），所以这里断言的是**本模块自己的
        口径**，不跟随解释器版本漂移。

        反跑：把 `是绝对` 里 `如果 开头(归一, 分隔)` 那条删掉，`\\x` / `/x` 两格立红。"""
        assert 是绝对(样本, "win32") is 期望

    @pytest.mark.parametrize("样本,期望", [
        ("/x", True), ("//x", True), ("x", False), ("", False), ("\\x", False),
    ])
    def test_posix口径与posixpath一致(self, 样本, 期望):
        """POSIX 分支在 Windows 机器上真跑（平台是入参）。

        反跑：把 `是绝对` 的 `如果 平台标识 不等于 "win32": 返回 假` 去掉，
        `\\x` 那格会被当成绝对路径 → 立红。"""
        assert 是绝对(样本, "posix") is 期望
        assert 是绝对(样本, "posix") is posixpath.isabs(样本)


class Test分量表:
    @pytest.mark.parametrize("样本,平台,期望", [
        ("/a//b/", "posix", ["/", "a", "b"]),
        ("a/b", "posix", ["a", "b"]),
        ("//srv/x", "posix", ["//", "srv", "x"]),
        ("C:\\a\\b", "win32", ["C:", "a", "b"]),
        ("C:/a/b", "win32", ["C:", "a", "b"]),
        ("c:\\", "win32", ["c:"]),
        ("\\\\主机\\共享\\x", "win32", ["\\\\", "主机", "共享", "x"]),
        ("", "posix", []),
    ])
    def test_拆分结果逐项相等(self, 样本, 平台, 期望):
        """前导分隔符被保留成第一个分量，是为了让绝对路径与同名相对路径拆出
        **不同**的表（否则分量级前缀比会把 `a/b` 判进 `/a` 里）。

        反跑：把 `分量表` 里 `如果 前导 大于 0: 表.追加(...)` 那两行删掉，
        `/a//b/` 与 `a/b` 会拆成同一张表 → 本条与
        `test_相对路径不算落在绝对根内` 同时立红。"""
        assert 分量表(样本, 平台) == 期望


class Test在目录树内:
    def test_根本身与根内路径都算在内(self):
        """反跑：把 `在目录树内` 的循环改成 `位 小于 长度(实表)`（拿实路径长度
        当上界），根内子路径会因越界索引/比较错位而立红。"""
        assert 在目录树内("c:\\r", "c:\\r", "win32") is True
        assert 在目录树内("c:\\r\\a\\b.txt", "c:\\r", "win32") is True
        assert 在目录树内("/r/a/b.txt", "/r", "posix") is True

    def test_兄弟目录不因裸前缀被收进来(self):
        """这是护栏第 (2) 条口径的算法级判据：`c:\\r_旁边` 的裸字符串前缀
        确实是 `c:\\r`，但分量不同。

        反跑：把 `在目录树内` 换成 `开头(实路径, 根目录)`（裸前缀比），立红。"""
        assert "c:\\r_旁边\\x".startswith("c:\\r") is True      # 裸前缀确实成立
        assert 在目录树内("c:\\r_旁边\\x", "c:\\r", "win32") is False
        assert 在目录树内("/r_旁边/x", "/r", "posix") is False

    def test_根外路径与空根都判假(self):
        """空根**绝不**解释成放行全盘（护栏第 (5) 条口径的算法侧）。

        反跑：把 `如果 长度(根表) 等于 0: 返回 假` 删掉，空根那两格会变成
        「任何路径都在内」→ 立红。"""
        assert 在目录树内("c:\\其它\\x", "c:\\r", "win32") is False
        assert 在目录树内("c:\\x", "", "win32") is False
        assert 在目录树内("/x", "", "posix") is False

    def test_卷根做根目录时不再全盘判越界(self):
        """旧实现 `实.startswith(根 + os.sep)` 在根是卷根（`c:\\`）时，
        拼出的前缀是 `c:\\\\`，任何路径都匹配不上 → 整个卷被判越界。
        分量比没有这个洞（方向上旧实现偏保守，所以六轮没暴露）。

        反跑：把 `在目录树内` 改回 `实路径.startswith(根目录 + 分隔符(平台))`，
        本条立红。"""
        assert 在目录树内("c:\\任意\\x", "c:\\", "win32") is True
        assert 在目录树内("/任意/x", "/", "posix") is True

    def test_相对路径不算落在绝对根内(self):
        """反跑：见 `Test分量表.test_拆分结果逐项相等` 的反跑——去掉前导分隔符
        分量后，本条立红。"""
        assert 在目录树内("a/b", "/a", "posix") is False
        assert 在目录树内("/a/b", "a", "posix") is False


class Test操作系统查询层:
    def test_平台判定与os_sep一致(self):
        """`本机平台` 用内置 `连接路径` 给出的分隔符反推平台，换掉了护栏与
        工具集里 5 处 `sys.platform` 直调。

        反跑：把 `本机平台` 里 `字符串包含(样本, "\\\\")` 的判断取反，本条立红。"""
        期望 = "win32" if os.sep == "\\" else "posix"
        assert 本机平台() == 期望
        assert 是视窗() is (os.sep == "\\")

    def test_子项表已排序且与listdir同集合(self, tmp_path):
        """排序是刻意的：目录项的原生顺序在不同文件系统上不一样，
        list_dir / grep 的输出要可复现。

        反跑：把 `子项表` 里的 `列表排序(表)` 删掉，本条的「已排序」断言立红
        （用例刻意按倒序建目录项）。"""
        for 名 in ["_taskD9_c.txt", "_taskD9_b.txt", "_taskD9_a.txt"]:
            (tmp_path / 名).write_text("x", encoding="utf-8")
        (tmp_path / "_taskD9_dir").mkdir()
        得 = 子项表(str(tmp_path))
        assert 得 == sorted(os.listdir(str(tmp_path)))
        assert 得 == ["_taskD9_a.txt", "_taskD9_b.txt", "_taskD9_c.txt", "_taskD9_dir"]

    def test_子项详表给出名_全路径_是否目录(self, tmp_path):
        """一次调用取代 listdir + join + isdir 三处直调，所以三项都要对。

        反跑：把 `子项详表` 里 `目录存在(全路径)` 换成 `路径存在(全路径)`，
        文件那一行的第三项会变成真 → 立红。"""
        (tmp_path / "_taskD9_文件.txt").write_text("x", encoding="utf-8")
        (tmp_path / "_taskD9_子目录").mkdir()
        得 = 子项详表(str(tmp_path))
        # 顺序按 子项表 的排序结果（"子" 的码位小于 "文"）
        assert 得 == [
            ["_taskD9_子目录", os.path.join(str(tmp_path), "_taskD9_子目录"), True],
            ["_taskD9_文件.txt", os.path.join(str(tmp_path), "_taskD9_文件.txt"), False],
        ]


class Test纯光明与零直调:
    """这两个模块的**存在理由**就是「不碰 Python 模块」，所以它俩自己有直调
    就等于本轮白做。这条用源码级断言守住，不依赖门禁基线。"""

    @pytest.mark.parametrize("模块文件", ["路径运算.light", "操作系统.light"])
    def test_没有导入任何Python模块也没有引Python(self, 模块文件):
        """反跑：在 `stdlib/路径运算.light` 顶部加一行 `导入 os`，本条立红。"""
        全路 = os.path.join(_PROJECT, "stdlib", 模块文件)
        with open(全路, encoding="utf-8") as fh:
            码行 = [l.split("#", 1)[0].strip() for l in fh]
        导入行 = [l for l in 码行 if l.startswith("导入") or l.startswith("从")]
        assert 导入行 == []
        assert [l for l in 码行 if "引 Python" in l or "引Python" in l] == []

    @pytest.mark.parametrize("模块文件", ["路径运算.light", "操作系统.light"])
    def test_没有同名py影子(self, 模块文件):
        """同名 `.py` 会让 `.light` 在运行期被遮蔽（除非首两行挂魔数），
        新模块一律不许造影子（第九轮总纲 §5 红线 1）。

        反跑：新建 `stdlib/路径运算.py`，本条立红。"""
        影子 = os.path.join(_PROJECT, "stdlib", 模块文件[:-len(".light")] + ".py")
        assert os.path.exists(影子) is False
