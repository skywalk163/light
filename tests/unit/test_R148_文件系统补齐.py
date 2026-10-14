# -*- coding: utf-8 -*-
"""R148-B：stdlib/文件系统.light 补齐段（是否符号链接 / 获取文件所有者）三腿对拍。

口径：经 _light_import_hook 加载 stdlib/文件系统.light（首行魔数，取代同名 .py），
逐函数与 stdlib/文件系统.py（参考实现）语义对拍。仅覆盖本轮新补齐段。

是否可执行 等依赖 os.access 的平台原语本轮登记 R149（见 _R148_B线交付报告），不在此测。
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
    spec = importlib.util.spec_from_file_location(
        name + "_py_ref", os.path.join(_STDLIB, name + ".py")
    )
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


def test_是否符号链接(fs, fs_ref, tmp_path):
    f = str(tmp_path / "a.txt")
    open(f, "w").close()
    # 常规文件：light / .py 参考 / os.path 三者必须一致（均为 假）
    assert fs.是否符号链接(f) == fs_ref.是否符号链接(f) == os.path.islink(f)


def test_获取文件所有者(fs, fs_ref, tmp_path):
    f = str(tmp_path / "a.txt")
    open(f, "w").close()
    got = fs.获取文件所有者(f)
    ref = fs_ref.获取文件所有者(f)
    # light 与 .py 参考键名已对齐为 uid/gid/用户/组；Windows 无 pwd/grp，用户名/组走字符串化
    assert got["uid"] == ref["uid"]
    assert got["gid"] == ref["gid"]
    assert got["用户"] == ref["用户"]
    assert got["组"] == ref["组"]
    assert got["用户"] == str(got["uid"])
