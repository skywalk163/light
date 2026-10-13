# -*- coding: utf-8 -*-
"""R145-C：stdlib/文件系统.light 缺口补齐对拍测试（src 腿）。

口径：经 _light_import_hook 加载 stdlib/文件系统.light（首行魔数，取代同名 .py），
逐函数与 Python os/shutil/hashlib 参考实现语义对拍。仅覆盖本轮新补齐段落；
runtime 无原语的（归档/磁盘用量/which/chmod/chown/锁/目录监控/seek/islink/
os.access/MIME/编码探测）不在此测，登记 _R145_C线交付报告.md「未实现边界」。
R145 收口调整（2026-10-13）：native 腿编译期硬拒绝 16 段（stat 时间族/二进制族/
环境枚举/真实路径/路径比较/筛选目录列表/比较文件信息——无地板原语），已从
文件系统.light 下架登记 R146，对应断言/用例（真实路径/时间属性/展开环境变量/
二进制读写）同步移除；其余补齐段落改为原生腿安全实现（纯光明重写），本文件
剩余 9 个用例即收口态对拍口径。
"""
import hashlib
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


@pytest.fixture()
def fsys():
    """加载 .light 文件系统模块（hook 已 install）。"""
    import 文件系统 as m
    return m


def _write(p, text):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def test_路径工具(fsys, tmp_path):
    p = str(tmp_path / "sub" / "c.txt")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    assert fsys.获取扩展名(p) == ".txt"
    assert fsys.获取目录名(p) == os.path.dirname(p)
    assert fsys.获取文件名不含扩展名(p) == "c"
    d, n = fsys.路径分割(p)
    assert d == os.path.dirname(p) and n == "c.txt"
    stem, ext = fsys.扩展名分割("c.txt")
    assert stem == "c" and ext == ".txt"
    _write(p, "x")
    assert fsys.路径存在(p) is True
    assert fsys.文件扩展名匹配("a/b/x.png", ".png") is True
    assert fsys.文件扩展名匹配("a/b/x.png", ".jpg") is False


def test_复制移动重命名删除(fsys, tmp_path):
    src = str(tmp_path / "a.txt")
    _write(src, "AAA")
    dst = str(tmp_path / "b.txt")
    fsys.复制文件(src, dst)
    assert os.path.isfile(dst)
    moved = str(tmp_path / "c.txt")
    fsys.移动文件(dst, moved)
    assert (not os.path.exists(dst)) and os.path.isfile(moved)
    renamed = str(tmp_path / "d.txt")
    fsys.重命名(moved, renamed)
    assert os.path.isfile(renamed)
    d = str(tmp_path / "emptydir")
    os.makedirs(d)
    fsys.删除空目录(d)
    assert not os.path.exists(d)


def test_创建触摸临时(fsys, tmp_path):
    p = str(tmp_path / "new.txt")
    assert not os.path.exists(p)
    fsys.创建文件(p)
    assert os.path.isfile(p)
    fsys.触摸文件(p)  # 已存在不报错
    tdir = fsys.创建临时目录()
    assert os.path.isdir(tdir)
    fsys.删除临时目录(tdir)
    assert not os.path.exists(tdir)



def test_列表遍历筛选(fsys, tmp_path):
    (tmp_path / "x.txt").write_text("1", encoding="utf-8")
    (tmp_path / "y.txt").write_text("2", encoding="utf-8")
    (tmp_path / "z.log").write_text("3", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "deep.txt").write_text("4", encoding="utf-8")
    td = str(tmp_path)
    names = fsys.目录列表(td)
    assert isinstance(names, list) and len(names) >= 3
    subs = fsys.子目录列表(td)
    assert sub.name in [os.path.basename(s) for s in subs]
    tree = fsys.遍历目录树(td)
    assert any("deep.txt" in f for f in tree)
    txts = fsys.按扩展名筛选(td, ".txt")
    assert len(txts) == 2  # 非递归：只顶层 x.txt/y.txt（deep.txt 在 sub/ 不计）
    assert fsys.目录大小(td) == sum(
        os.path.getsize(os.path.join(r, f))
        for r, _, fs in os.walk(td) for f in fs
    )


def test_哈希族(fsys, tmp_path):
    p = str(tmp_path / "h.txt")
    _write(p, "hello")
    expect = hashlib.md5("hello".encode("utf-8")).hexdigest()
    assert fsys.计算文件MD5(p) == expect
    expect256 = hashlib.sha256("hello".encode("utf-8")).hexdigest()
    assert fsys.计算文件SHA256(p) == expect256
    assert fsys.计算文件哈希(p, "sha256") == expect256


def test_比较与重复(fsys, tmp_path):
    a = str(tmp_path / "a.txt")
    b = str(tmp_path / "b.txt")
    c = str(tmp_path / "c.txt")
    _write(a, "SAME")
    _write(b, "SAME")
    _write(c, "DIFF")
    assert fsys.比较文件内容(a, b) is True
    assert fsys.比较文件内容(a, c) is False
    assert fsys.比较文件内容(a, str(tmp_path / "nope")) is False
    dup = fsys.查找重复文件(str(tmp_path))
    assert len(dup) >= 1


def test_安全备份删除(fsys, tmp_path):
    p = str(tmp_path / "s.txt")
    _write(p, "v1")
    bak = fsys.安全写入文件(p, "v2", True)
    assert bak.endswith(".bak")
    assert (tmp_path / "s.txt.bak").read_text(encoding="utf-8") == "v1"
    assert (tmp_path / "s.txt").read_text(encoding="utf-8") == "v2"
    b2 = fsys.备份文件(p)
    assert b2.endswith(".bak")
    assert fsys.安全删除文件(p) is True
    assert not os.path.exists(p)


def test_环境变量与cwd(fsys, monkeypatch):
    fsys.设置环境变量("R145C_PROBE", "yes")
    assert fsys.获取环境变量("R145C_PROBE") == "yes"
    assert fsys.获取环境变量("R145C_NOPE", "def") == "def"
    assert isinstance(fsys.当前工作目录(), str)


def test_路径验证(fsys, tmp_path):
    p = str(tmp_path / "pv.txt")
    _write(p, "z")
    v = fsys.路径验证(p)
    assert v["存在"] is True
    assert v["是文件"] is True
    assert v["是目录"] is False


