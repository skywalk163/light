# -*- coding: utf-8 -*-
"""R149-B：L-211 `查找重复文件` 语义对齐（.light vs .py 三腿对拍 + 变异验证）。

背景（R148-D 裁定）：`查找重复文件` 存在语义分歧——
  * `.py`  参考：先按大小分组，**同大小组内再比内容**（比较文件内容），
    只返回「内容真正相同」的分组 → `[[a, b]]`。
  * `.light` 旧实现：只按大小分组 → 把「同大小但内容不同」的文件也并入同一组
    → `[[a, b, c]]`。
登记为 L-211 候选，统一动作交 R149-B。

修复：`stdlib/文件系统.light` 的 查找重复文件 在同大小组内按 MD5（计算文件MD5）
再分组，只返回组内文件数 >= 2 的内容相同分组，与 `.py` 逐项对齐。

变异验证（防假绿）：本用例刻意让 a/b/c **三个文件大小完全相同**（均为 4 字节），
但只有 a、b 内容相同、c 内容不同。若实现退回「只按大小分组」，会产出
`[['a.txt','b.txt','c.txt']]` —— 断言 `c.txt` 不得出现在任何组内即可抓住。
"""
import importlib.util
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_REPO, "src"), os.path.join(_REPO, "stdlib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _light_import_hook  # noqa: E402

_STDLIB = os.path.join(_REPO, "stdlib")
_light_import_hook.install([os.path.abspath(_STDLIB)])

sys.dont_write_bytecode = True


def _load_py(name):
    """按绝对路径加载 .py 参考实现（避开 hook 对同名模块的接管）。"""
    spec = importlib.util.spec_from_file_location(
        name + "_py_ref", os.path.join(_STDLIB, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def fs():
    import 文件系统 as m
    return m


@pytest.fixture()
def fs_ref():
    return _load_py("文件系统")


def _norm(groups):
    """归一化为「组的集合」，组内按文件名排序，组间按首元素排序（顺序无关）。"""
    return sorted(sorted(os.path.basename(p) for p in g) for g in groups)


def _make(tmp_path):
    """a/b 内容相同；c 与它们**同大小**（4 字节）但内容不同。"""
    a, b, c = tmp_path / "a.txt", tmp_path / "b.txt", tmp_path / "c.txt"
    a.write_bytes(b"AAAA")
    b.write_bytes(b"AAAA")
    c.write_bytes(b"BBBB")
    assert a.stat().st_size == b.stat().st_size == c.stat().st_size == 4
    return a, b, c


def test_同大小不同内容不并组(fs, tmp_path):
    """核心断言：c.txt（同大小、不同内容）不得被并入重复分组。"""
    _make(tmp_path)
    got = fs.查找重复文件(str(tmp_path))
    flat = [os.path.basename(p) for g in got for p in g]
    assert "c.txt" not in flat, (
        "L-211 未收口：同大小但内容不同的 c.txt 被并入重复分组 → %s" % got)
    assert sorted(flat) == ["a.txt", "b.txt"], "应只返回内容相同的 a/b：%s" % got


def test_与py参考逐项一致(fs, fs_ref, tmp_path):
    _make(tmp_path)
    got = fs.查找重复文件(str(tmp_path))
    ref = fs_ref.查找重复文件(str(tmp_path))
    assert _norm(got) == _norm(ref), (
        "light 与 .py 参考分歧：light=%s ref=%s" % (_norm(got), _norm(ref)))


def test_无重复时返回空(fs, fs_ref, tmp_path):
    (tmp_path / "x.txt").write_bytes(b"xxxx")
    (tmp_path / "y.txt").write_bytes(b"yyyy")
    assert fs.查找重复文件(str(tmp_path)) == []
    assert _norm(fs_ref.查找重复文件(str(tmp_path))) == []


def test_两组独立重复(fs, fs_ref, tmp_path):
    """两组各自内容相同、彼此不同 → 应返回两个组。"""
    for name, payload in (("p1", b"1111"), ("p2", b"1111"),
                          ("q1", b"2222"), ("q2", b"2222")):
        (tmp_path / (name + ".txt")).write_bytes(payload)
    got = fs.查找重复文件(str(tmp_path))
    assert _norm(got) == [["p1.txt", "p2.txt"], ["q1.txt", "q2.txt"]], got
    assert _norm(got) == _norm(fs_ref.查找重复文件(str(tmp_path)))
