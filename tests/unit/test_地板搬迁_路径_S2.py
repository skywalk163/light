# -*- coding: utf-8 -*-
"""地板搬迁差分测试（第九轮 S2 · 路径组）：
`stdlib/内置核心路径.light` 的 6 个段落 vs Python 标准库 `posixpath`，逐条对跑。

为什么 oracle 是 `posixpath` 而不是 `os.path`，更不是 `builtins.py`
------------------------------------------------------------------
1. **不是 `builtins.py`**：这批函数正在被搬到光明侧，转发一落地
   `from builtins import 目录名` 就变成「光明版跟光明版自己比」，那种测试永远绿，
   等于没测（见 memory/feedback_先证等价再转发.md）。所以 oracle 必须是一份
   与被测实现无关的独立权威 —— 这里直接调 CPython 自带的 `posixpath`。
2. **不是 `os.path`**：主线已裁决光明的路径语义是 **POSIX 风格**（只认 `/`，
   不管盘符），并明确记为**不兼容变更**。`os.path` 在 Windows 上是 `ntpath`：
   把 `\\` 也当分隔符、把 `C:` 当根。拿它当 oracle 会把裁决测反。
   `posixpath` 恰好就是裁决那套语义的精确实现，所以它是判据，不是近似。

「不兼容变更取证」一节（本文件末尾）是给主线看的证据
--------------------------------------------------
它对含反斜杠 / 含盘符 / 含前导双斜杠的样本同时算 `ntpath` 与 `posixpath`，
断言两者**确实不同**，再把光明侧钉在 `posixpath` 那一侧。差异对是**硬编码的实测
快照**：`ntpath` 与 `posixpath` 任何一侧的行为漂移，或光明侧偷偷倒向 ntpath 语义，
都会让这一节变红，而不是悄悄放过。

契约边界（写在明处）
------------------
- `bytes` 入参**不在契约内**。`builtins.py:239-267` 的标注是 `path: str`，
  `posixpath` 对 bytes 另有一套 `b'/'`/`b'.'` 分隔符行为（实测
  `posixpath.splitext(b"a.tar.gz") == (b'a.tar', b'.gz')`），光明侧不实现、本文件不测。
  另附实测：`posixpath.join(b"a", "b")` 抛 `TypeError: Can't mix strings and bytes`。
- `绝对路径` 不在这批里 —— 它依赖当前工作目录，是 native_required。
"""
import importlib
import ntpath
import os
import posixpath
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STDLIB = os.path.join(_ROOT, "stdlib")
for _p in (_ROOT, os.path.join(_ROOT, "src"), _STDLIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _light_import_hook  # noqa: E402

_light_import_hook.install([_STDLIB])

# 光明侧：钩子把 .light 就地编译执行（内置核心路径 没有同名 .py，走纯光明路径）
光明 = importlib.import_module("内置核心路径")


# ── 0. 模块身份：跑的必须真是 .light（防钩子失效后偷偷去命中别的实现）─────────────
def test_光明模块真的由light文件加载():
    assert 光明.__file__.endswith("内置核心路径.light")
    assert 光明.__light_source__.endswith("内置核心路径.light")
    assert os.path.basename(光明.__light_source__) == "内置核心路径.light"


def test_六个段落都在且都可调用():
    for 名 in ("连接路径", "目录名", "文件名", "扩展名", "分割路径", "分割扩展名"):
        assert callable(getattr(光明, 名)), 名
    assert set(光明.__all__) == {
        "连接路径", "目录名", "文件名", "扩展名", "分割路径", "分割扩展名"}


# ── 1. 全组共用的一份路径样本表 ──────────────────────────────────────────────
# 六个函数各自对整张表逐条断言。任何新边角只加在这里，不许某个函数偷偷用小表。
路径样本 = [
    # 空 / 单段 / 常规
    "", "a", "a/b", "/a/b", "a/", "/a", "a/b/",
    # 连续斜杠（保留规则最反直觉的一档）
    "/", "//", "///", "//a", "//a//b//", "////a////b",
    # 点号相关
    ".", "..", "...", "./a", "../a", "a/b/.", "a/b/..",
    # 扩展名边角
    ".gitignore", "/.gitignore", "a.tar.gz", "x.tar.gz.bak", "a.",
    "a/.b", "a/b.c/d", ".a.b", "a..b",
    # 中文 / 空格
    "中文/目录/文件.txt", "中文", "目录/中文名.文本", "a b/c d.e f",
    " ", " /a", "a/ ",
    # 反斜杠：POSIX 语义下是**普通字符**，这是不兼容点
    "a\\b", "C:\\x\\y", "C:\\x\\y.txt", "a.b\\c", "\\", "\\\\主机\\共享\\f.txt",
    # 盘符：POSIX 语义下不作特殊处理
    "C:/x/y", "C:/x/y.txt", "C:", "C:/",
    # 很长的路径
    "很长/" * 40 + "尾.ext",
    "a/b/c/d/e/f/g/h/i/j/k/l/m/n/o/p.q",
]


def test_样本表规模与无重复():
    assert len(路径样本) == 48
    assert len(set(路径样本)) == len(路径样本)


# ── 2. 五个单参段落：对整张表逐字符等价 ──────────────────────────────────────
@pytest.mark.parametrize("p", 路径样本)
def test_目录名_对齐posixpath_dirname(p):
    assert 光明.目录名(p) == posixpath.dirname(p)


@pytest.mark.parametrize("p", 路径样本)
def test_文件名_对齐posixpath_basename(p):
    assert 光明.文件名(p) == posixpath.basename(p)


@pytest.mark.parametrize("p", 路径样本)
def test_扩展名_对齐posixpath_splitext尾项(p):
    assert 光明.扩展名(p) == posixpath.splitext(p)[1]


@pytest.mark.parametrize("p", 路径样本)
def test_分割路径_值相等且类型是tuple(p):
    got = 光明.分割路径(p)
    assert type(got) is tuple          # 不是 list、不是自造的二元容器
    assert len(got) == 2
    assert got == posixpath.split(p)


@pytest.mark.parametrize("p", 路径样本)
def test_分割扩展名_值相等且类型是tuple(p):
    got = 光明.分割扩展名(p)
    assert type(got) is tuple
    assert len(got) == 2
    assert got == posixpath.splitext(p)


# ── 3. 内部一致性：五个段落之间不许互相跑偏 ──────────────────────────────────
@pytest.mark.parametrize("p", 路径样本)
def test_内部一致性_分割路径与目录名文件名同口径(p):
    甲, 乙 = 光明.分割路径(p)
    assert 甲 == 光明.目录名(p)
    assert 乙 == 光明.文件名(p)


@pytest.mark.parametrize("p", 路径样本)
def test_内部一致性_分割扩展名可无损重组且尾项等于扩展名(p):
    主, 尾 = 光明.分割扩展名(p)
    assert 尾 == 光明.扩展名(p)
    assert 主 + 尾 == p                 # splitext 是**无损**切分，拼回来必须逐字符还原


# ── 4. 连接路径：变参，多参组合逐字符对齐 posixpath.join ─────────────────────
# 覆盖 2/3/4/5 参、绝对路径参数（丢弃前面全部）、空串参数（只补分隔符）、
# 尾斜杠参数（不产生双斜杠）、反斜杠与盘符参数（POSIX 下都是普通字符）。
连接样本 = [
    ("a",),
    ("a", "b"), ("a", "/b"), ("a", ""), ("", "b"), ("a/", "b"), ("a//", "b"),
    ("a/", "/b"), ("", ""), ("/", "a"), ("//", "a"), ("///", ""),
    ("a", "b", "c"), ("a", "b", "/c"), ("a", "", "b"), ("a", ".", "b"),
    ("/a", "b", "c"),
    ("a", "b/", "c", "d"), ("a", "b", "", ""),
    ("x", "x", "x", "x", "x"),
    ("C:\\x", "y"), ("C:/x", "y"), ("a\\", "b"), ("\\a", "b"), ("C:", "x"),
    ("中文", "文件.txt"), ("a b", "c d"),
    ("很长/" * 40, "尾.ext"),
]


def test_连接样本表规模与无重复():
    assert len(连接样本) == 28
    assert len(set(连接样本)) == len(连接样本)
    assert {len(a) for a in 连接样本} == {1, 2, 3, 4, 5}   # 各元数都到场


@pytest.mark.parametrize("args", 连接样本)
def test_连接路径_对齐posixpath_join(args):
    assert 光明.连接路径(*args) == posixpath.join(*args)


def test_连接路径_零参与posixpath同为TypeError():
    """实测：`posixpath.join()` 抛 TypeError（签名是 `join(a, *p)`，a 是必需位置参）。
    光明侧显式抛同类异常，不许返回 "" 之类的自造值。消息文本不作判据，类型作判据。
    """
    with pytest.raises(TypeError):
        posixpath.join()
    with pytest.raises(TypeError):
        光明.连接路径()


# ── 5. 不兼容变更取证（给主线的证据，非可选项）──────────────────────────────
# 硬编码实测快照：(段落名, 样本) -> (ntpath 结果, posixpath 结果)。
# 只列**两者确实不同**的对；下面 test_取证集合与实测逐条相符 会重算一遍并要求集合完全一致。
_取证 = {
    # 目录名 / dirname
    ("目录名", "//a"): ("//a", "//"),
    ("目录名", "a\\b"): ("a", ""),
    ("目录名", "C:\\x\\y"): ("C:\\x", ""),
    ("目录名", "C:\\x\\y.txt"): ("C:\\x", ""),
    ("目录名", "a.b\\c"): ("a.b", ""),
    ("目录名", "\\"): ("\\", ""),
    ("目录名", "\\\\主机\\共享\\f.txt"): ("\\\\主机\\共享\\", ""),
    ("目录名", "C:"): ("C:", ""),
    ("目录名", "C:/"): ("C:/", "C:"),
    # 文件名 / basename
    ("文件名", "//a"): ("", "a"),
    ("文件名", "a\\b"): ("b", "a\\b"),
    ("文件名", "C:\\x\\y"): ("y", "C:\\x\\y"),
    ("文件名", "C:\\x\\y.txt"): ("y.txt", "C:\\x\\y.txt"),
    ("文件名", "a.b\\c"): ("c", "a.b\\c"),
    ("文件名", "\\"): ("", "\\"),
    ("文件名", "\\\\主机\\共享\\f.txt"): ("f.txt", "\\\\主机\\共享\\f.txt"),
    ("文件名", "C:"): ("", "C:"),
    # 分割路径 / split
    ("分割路径", "//a"): (("//a", ""), ("//", "a")),
    ("分割路径", "a\\b"): (("a", "b"), ("", "a\\b")),
    ("分割路径", "C:\\x\\y"): (("C:\\x", "y"), ("", "C:\\x\\y")),
    ("分割路径", "C:\\x\\y.txt"): (("C:\\x", "y.txt"), ("", "C:\\x\\y.txt")),
    ("分割路径", "a.b\\c"): (("a.b", "c"), ("", "a.b\\c")),
    ("分割路径", "\\"): (("\\", ""), ("", "\\")),
    ("分割路径", "\\\\主机\\共享\\f.txt"):
        (("\\\\主机\\共享\\", "f.txt"), ("", "\\\\主机\\共享\\f.txt")),
    ("分割路径", "C:"): (("C:", ""), ("", "C:")),
    ("分割路径", "C:/"): (("C:/", ""), ("C:", "")),
    # 分割扩展名 / splitext —— ntpath 把 `\` 当分隔符，于是 "a.b\c" 的点落在「目录部分」
    ("分割扩展名", "a.b\\c"): (("a.b\\c", ""), ("a", ".b\\c")),
    # 扩展名 = splitext 尾项
    ("扩展名", "a.b\\c"): ("", ".b\\c"),
}

# 段落名 -> (光明实现, ntpath 版, posixpath 版)
_三方 = {
    "目录名": (lambda p: 光明.目录名(p), ntpath.dirname, posixpath.dirname),
    "文件名": (lambda p: 光明.文件名(p), ntpath.basename, posixpath.basename),
    "分割路径": (lambda p: 光明.分割路径(p), ntpath.split, posixpath.split),
    "分割扩展名": (lambda p: 光明.分割扩展名(p), ntpath.splitext, posixpath.splitext),
    "扩展名": (lambda p: 光明.扩展名(p),
             lambda p: ntpath.splitext(p)[1], lambda p: posixpath.splitext(p)[1]),
}


def test_取证前提_os_path在本机就是ntpath():
    """这一节的意义建立在「现状（os.path）与新语义确有分歧」之上。
    在 POSIX runner 上 os.path 就是 posixpath，分歧为零 —— 那时冲击面本来就是 0。
    """
    if sys.platform.startswith("win"):
        assert os.path is ntpath
    else:
        assert os.path is posixpath


@pytest.mark.parametrize("键", sorted(_取证, key=lambda k: (k[0], k[1])))
def test_取证_两侧确实不同且光明钉在posixpath一侧(键):
    段落名, p = 键
    nt期望, posix期望 = _取证[键]
    光明版, nt版, posix版 = _三方[段落名]
    # ① ntpath 与 posixpath 在这条样本上确实分歧（不然这条取证是空话）
    assert nt版(p) != posix版(p)
    # ② 两侧各是什么，逐字符钉住（防标准库行为漂移被静默吞掉）
    assert nt版(p) == nt期望
    assert posix版(p) == posix期望
    # ③ 光明站 posixpath 那一侧，且**确实不等于** ntpath 那一侧
    assert 光明版(p) == posix期望
    assert 光明版(p) != nt期望


def test_取证集合与实测逐条相符():
    """把整张样本表 × 五个段落重算一遍，实际分歧集合必须与 `_取证` 完全一致。
    多一条（新的不兼容面出现）或少一条（标准库/光明侧倒戈）都要红。
    """
    实测 = {}
    for 段落名, (_光明版, nt版, posix版) in _三方.items():
        for p in 路径样本:
            if nt版(p) != posix版(p):
                实测[(段落名, p)] = (nt版(p), posix版(p))
    assert 实测 == _取证
    assert len(实测) == 28              # 48 条样本 × 5 段落 = 240 组里 28 组分歧


# join 的不兼容面更大：POSIX 版一律用 `/` 拼，ntpath 用 `\`。
_取证_连接 = {
    ("a", "b"): ("a\\b", "a/b"),
    ("a", ""): ("a\\", "a/"),
    ("a", "b", "c"): ("a\\b\\c", "a/b/c"),
    ("a", "", "b"): ("a\\b", "a/b"),
    ("a", "b/", "c", "d"): ("a\\b/c\\d", "a/b/c/d"),
    ("a", ".", "b"): ("a\\.\\b", "a/./b"),
    ("C:\\x", "y"): ("C:\\x\\y", "C:\\x/y"),
    ("C:/x", "y"): ("C:/x\\y", "C:/x/y"),
    ("中文", "文件.txt"): ("中文\\文件.txt", "中文/文件.txt"),
    ("a b", "c d"): ("a b\\c d", "a b/c d"),
    ("a", "b", "", ""): ("a\\b\\", "a/b/"),
    ("x", "x", "x", "x", "x"): ("x\\x\\x\\x\\x", "x/x/x/x/x"),
    ("a\\", "b"): ("a\\b", "a\\/b"),        # POSIX 下 `\` 不是分隔符，照补 `/`
    ("\\a", "b"): ("\\a\\b", "\\a/b"),
    ("C:", "x"): ("C:x", "C:/x"),           # ntpath 认盘符相对路径，POSIX 不认
    ("/a", "b", "c"): ("/a\\b\\c", "/a/b/c"),
}


@pytest.mark.parametrize("args", sorted(_取证_连接))
def test_取证_连接路径两侧确实不同且光明钉在posixpath一侧(args):
    nt期望, posix期望 = _取证_连接[args]
    assert ntpath.join(*args) != posixpath.join(*args)
    assert ntpath.join(*args) == nt期望
    assert posixpath.join(*args) == posix期望
    assert 光明.连接路径(*args) == posix期望
    assert 光明.连接路径(*args) != nt期望


def test_取证_连接路径集合与实测逐条相符():
    实测 = {}
    for args in 连接样本:
        if ntpath.join(*args) != posixpath.join(*args):
            实测[args] = (ntpath.join(*args), posixpath.join(*args))
    assert 实测 == _取证_连接
    assert len(实测) == 16
    # 实测记录：超长样本 ("很长/"*40, "尾.ext") **不**分歧 —— 首参已以 `/` 结尾，
    # ntpath 也认 `/` 是分隔符（它的 altsep），于是两侧都不再补分隔符，结果逐字符相同。
    长条 = ("很长/" * 40, "尾.ext")
    assert 长条 in 连接样本
    assert ntpath.join(*长条) == posixpath.join(*长条) == "很长/" * 40 + "尾.ext"
    assert 光明.连接路径(*长条) == "很长/" * 40 + "尾.ext"


# ── 6. posixpath 边角真值表：把实测出来的反直觉输出正面钉住 ───────────────────
# 这一节不经过 ntpath，也不依赖上面的参数化，是「语义规格」本身的快照。
# 它与第 2 节重叠是**故意的**：第 2 节保证等价，这一节保证等价的那个目标值没被写错。
@pytest.mark.parametrize("p, 期望", [
    ("/", "/"), ("//", "//"), ("///", "///"), ("//a", "//"),
    ("a", ""), ("a/", "a"), ("//a//b//", "//a//b"), ("////a////b", "////a"),
    ("", ""), (".", ""), ("./a", "."),
])
def test_真值_目录名连续斜杠保留规则(p, 期望):
    assert posixpath.dirname(p) == 期望            # oracle 自身先自证
    assert 光明.目录名(p) == 期望


@pytest.mark.parametrize("p, 期望", [
    ("/", ""), ("a/", ""), ("//a", "a"), ("//a//b//", ""), ("a", "a"),
    ("", ""), ("/a/b", "b"),
])
def test_真值_文件名可以是空串(p, 期望):
    assert posixpath.basename(p) == 期望
    assert 光明.文件名(p) == 期望


@pytest.mark.parametrize("p, 期望", [
    ("", ("", "")), ("//a", ("//", "a")), ("///", ("///", "")),
    ("//", ("//", "")), ("/", ("/", "")), ("a/", ("a", "")),
    ("//a//b//", ("//a//b", "")), ("////a////b", ("////a", "b")),
])
def test_真值_分割路径连续斜杠(p, 期望):
    assert posixpath.split(p) == 期望
    assert 光明.分割路径(p) == 期望


@pytest.mark.parametrize("p, 期望", [
    (".gitignore", (".gitignore", "")),     # 前导点不算扩展名
    ("/.gitignore", ("/.gitignore", "")),
    ("a/.b", ("a/.b", "")),
    ("..", ("..", "")),
    ("...", ("...", "")),
    (".", (".", "")),
    (".a.b", (".a", ".b")),                 # 前导点之后还有点：在最后一个点处切
    ("a.tar.gz", ("a.tar", ".gz")),         # 只切最后一个点
    ("x.tar.gz.bak", ("x.tar.gz", ".bak")),
    ("a.", ("a", ".")),                     # 尾点：扩展名就是一个点
    ("a..b", ("a.", ".b")),
    ("a/b.c/d", ("a/b.c/d", "")),           # 点在目录部分，不算扩展名
    ("a", ("a", "")),
    ("", ("", "")),
])
def test_真值_分割扩展名前导点与多点(p, 期望):
    assert posixpath.splitext(p) == 期望
    assert 光明.分割扩展名(p) == 期望
    assert 光明.扩展名(p) == 期望[1]


@pytest.mark.parametrize("args, 期望", [
    (("a", "/b"), "/b"),            # 绝对路径参数丢弃前面全部
    (("a", "b", "/c"), "/c"),
    (("a", ""), "a/"),              # 空串参数只补分隔符
    (("", "b"), "b"),
    (("", ""), ""),
    (("a/", "b"), "a/b"),           # 已有尾斜杠不补第二个
    (("a//", "b"), "a//b"),         # 但已有的多余斜杠原样保留
    (("///", ""), "///"),
    (("a",), "a"),
    (("a", "b", "", ""), "a/b/"),
])
def test_真值_连接路径边角(args, 期望):
    assert posixpath.join(*args) == 期望
    assert 光明.连接路径(*args) == 期望
