# -*- coding: utf-8 -*-
"""
外发任务_内置与直调S2（task-BI2）：20 条系统原语内置的定向测试。

被测对象：`stdlib/builtins.py` 新增的 12 函数 + 8 常量（全部 native_required）。
注册表在 `src/code_generator.py` 的 `builtin_map`，两处必须咬合（空壳 = 调用即错误）。

测试策略：
  1. `test_注册表与实现咬合`：20 个名字同时在 builtin_map 与 stdlib/builtins 里，
     且 builtin_map 值以 `_light_builtin.` 结尾（非空壳）。
  2. 函数语义测试：与对应的 os.* / time.* / hmac.* 原语等价值做**判别性断言**，
     不是复制原语实现（避免 tautology）。
  3. 反跑（§5 红线：改了实现某行、某条断言就红）逐条在 docstring 里写清
     「改哪行 → 哪条断言红」。

平台说明：本机只有 Windows。凡断言标「仅 Windows 实跑」者 POSIX 上为推断；
POSIX 专门的（不跟随符号链接 真值、O_EXCL 语义）以「断言与 os 原语相等」
跨平台自洽，不必真机。
"""
import os
import importlib.util
import sys
import time as _py_time

import pytest

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PROJECT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT, 'stdlib'))
sys.path.insert(0, _PROJECT)

import _light_import_hook
_light_import_hook.install([os.path.join(_PROJECT, 'stdlib'), _PROJECT])

# 以独立模块名加载 stdlib 的 builtins.py，避免与 Python 内置 `builtins` 模块撞名。
def _load_builtins():
    _path = os.path.join(_PROJECT, 'stdlib', 'builtins.py')
    _spec = importlib.util.spec_from_file_location('light_builtins_bi2', _path)
    _m = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    return _m


_b = _load_builtins()


# 12 个函数 + 8 个常量 = 20
新内置函数 = [
    '真实路径', '文件状态', '句柄状态', '低级打开', '低级读', '低级写', '低级关闭',
    '随机字节', '原子替换', '环境枚举', '单调时钟', '常量时间比较',
]
新内置常量 = [
    '只读', '只写', '新建', '截断', '追加', '独占', '二进制', '不跟随符号链接',
]
全部20 = 新内置函数 + 新内置常量


class Test注册表与实现咬合:
    """§7.4 的扩展；改 `src/code_generator.py` 漏掉某条，或 builtins.py 删了某条，都红。"""

    def test_全部20在builtins且可调用(self):
        for 名 in 全部20:
            assert hasattr(_b, 名), f"builtins.py 缺 {名}"
            assert callable(getattr(_b, 名)), f"{名} 不是可调用（常量应为零参函数形态）"

    def test_全部20在builtin_map且非空壳(self):
        from code_generator import PythonCodeGenerator
        映射 = PythonCodeGenerator().builtin_map
        for 名 in 全部20:
            assert 名 in 映射, f"builtin_map 缺 {名}"
            assert 映射[名].startswith('_light_builtin.'), f"{名} 映射不是内置函数 {映射[名]}"


class Test路径与状态:
    """真实路径 / 文件状态 / 句柄状态。"""

    def test_真实路径解析junction(self):
        """反跑：把 builtins.py:1144 改回 os.path.abspath(路径) → 本断言红。
        abspath 是词法拼接，不解析链接；junction 指向根外会被放行，正是护栏第一条口径要拦的。"""
        if not sys.platform.startswith('win'):
            pytest.skip('junction 用 mklink /J 仅 Windows 可建，POSIX 需 os.symlink+权限，留作推断')
        import subprocess
        import tempfile
        root = tempfile.mkdtemp(prefix="_bi2_realpath_")
        target_dir = os.path.join(root, "target")
        os.makedirs(target_dir)
        链接 = os.path.join(root, "link_junc")
        subprocess.run(["cmd", "/c", "mklink", "/J", 链接, target_dir],
                       check=True, capture_output=True)
        try:
            # 关键反跑断言：真实路径 必须把 junction 解析到 target（abspath 只会返回链接本身）。
            assert _b.真实路径(链接) == os.path.realpath(target_dir), (
                "真实路径 未解析 junction，疑似退回 绝对路径/abspath")
        finally:
            subprocess.run(["cmd", "/c", "rmdir", 链接], capture_output=True)

    def test_真实路径与realpath等价(self):
        根 = os.path.abspath('stdlib')
        路 = os.path.join(根, '子', '..', 'builtins.py')
        assert _b.真实路径(路) == os.path.realpath(路)
        # 反跑：把 :1144 改成 os.path.abspath → 对含 junction/真链接路径会分叉（上面已验），
        # 静态 `..` 两者都折，故这里只钉「与 realpath 一致」这一语义锚。

    def test_文件状态与句柄状态往返(self, tmp_path):
        """反跑：文件状态 改成 return None（取不到即空）→ 本断言红。"""
        f = tmp_path / "_bi2_stat.bin"
        f.write_bytes(b"hello")
        路径 = str(f)
        状态 = _b.文件状态(路径)
        assert isinstance(状态, os.stat_result)  # 是真实 stat_result 才有 st_nlink/st_ino 可查
        assert 状态.st_size == 5
        assert 状态.st_nlink >= 1  # st_nlink 是护栏硬链接判定的依据，缺它即空壳
        # 句柄状态：从同一个句柄回查，与 文件状态(路径) 在同一文件对象上一致
        fd = os.open(路径, os.O_RDONLY)
        try:
            句柄 = _b.句柄状态(fd)
            assert isinstance(句柄, os.stat_result)
            assert 句柄.st_ino == 状态.st_ino  # 反跑：句柄状态 用 文件状态(路径) 顶替 → 打开后又被替换就分叉
            assert 句柄.st_dev == 状态.st_dev
        finally:
            os.close(fd)

    def test_文件状态缺失返回空(self):
        assert _b.文件状态(os.path.join(str(_PROJECT), '_不存在_bi2_.tmp')) is None


class Test低级IO与标志:
    """低级打开/读/写/关闭 + 8 个常量组合的端到端往返。这是 O_BINARY 数据正确性的主战场。"""

    def test_二进制写读往返不被文本模式破坏(self, tmp_path):
        """反跑：A) 低级打开 退回 open()；B) 二进制 硬编码 0（Windows 上文本模式）→ 本断言红。
        写入含 0x1A(EOF) 与 0x0A(CR) 的字节；文本模式会在 0x1A 处截断或改写换行。"""
        path = str(tmp_path / "_bi2_bin.dat")
        数据 = bytes(range(256)) + b"\x1aX\x0aY\x00Z"
        写 = _b.只写() + _b.新建() + _b.截断() + _b.二进制()
        fd = _b.低级打开(path, 写, 0o600)
        try:
            assert _b.低级写(fd, 数据) == len(数据)
        finally:
            _b.低级关闭(fd)
        读 = _b.只读() + _b.二进制()
        fd2 = _b.低级打开(path, 读, 0)
        try:
            chunks = []
            while True:
                块 = _b.低级读(fd2, 64)
                if not 块:
                    break
                chunks.append(块)
            结果 = b"".join(chunks)
        finally:
            _b.低级关闭(fd2)
        assert 结果 == 数据

    def test_常量与os原语等价(self):
        """反跑：任一条把 os.O_* 值硬编码成异平台数字 → 该断言红。"""
        assert _b.只读() == os.O_RDONLY
        assert _b.只写() == os.O_WRONLY
        assert _b.新建() == os.O_CREAT
        assert _b.截断() == os.O_TRUNC
        assert _b.追加() == os.O_APPEND
        assert _b.独占() == os.O_EXCL
        if hasattr(os, 'O_BINARY'):
            assert _b.二进制() == os.O_BINARY  # 仅 Windows
        else:
            assert _b.二进制() == 0  # POSIX 语义：无此概念取 0
        if hasattr(os, 'O_NOFOLLOW'):
            assert _b.不跟随符号链接() == os.O_NOFOLLOW
        else:
            assert _b.不跟随符号链接() == 0  # Windows：无此概念取 0

    def test_独占拒绝预置文件(self, tmp_path):
        """反跑：新建 或 独占 少或一个 → 预置文件被静默打开覆盖。"""
        目标 = str(tmp_path / "_bi2_excl.dat")
        with open(目标, 'w') as f:
            f.write("已存在")
        标志 = _b.只写() + _b.新建() + _b.独占()
        with pytest.raises(OSError):
            _b.低级打开(目标, 标志, 0o600)


class Test随机与原子替换:
    def test_随机字节长度与变化(self):
        a = _b.随机字节(32)
        b = _b.随机字节(32)
        assert len(a) == 32 and len(b) == 32
        # 反跑：改成 random.getrandbits（伪随机可预测）→ 仍可能撞，故只钉 CSPRNG 长度与存在性；
        # 明确不允用伪随机的强断言见护栏测试（临时文件撞名即失败）。
        assert isinstance(a, bytes)

    def test_原子替换覆盖已存在目标(self, tmp_path):
        """反跑：改成 shutil.move（目标已存在即抛）→ 本断言红。"""
        源 = str(tmp_path / "_bi2_src.txt")
        目标 = str(tmp_path / "_bi2_dst.txt")
        # 写侧必须显式 encoding='utf-8'：不写就跟随 locale（GBK 机器上「新内容」落成
        # D0 C2 C4 DA），:201 用 utf-8 读回就 UnicodeDecodeError——绿只在 UTF-8 模式下成立。
        with open(源, 'w', encoding='utf-8') as f:
            f.write("新内容")
        with open(目标, 'w', encoding='utf-8') as f:  # 预置已存在目标
            f.write("旧内容")
        _b.原子替换(源, 目标)
        assert not os.path.exists(源)
        assert open(目标, encoding='utf-8').read() == "新内容"


class Test环境与时钟:
    def test_环境枚举形状(self):
        """反跑：改成返回 dict（少了二元子表）→ 本断言红；或返回硬编码表 → 覆盖断言红。"""
        项 = _b.环境枚举()
        assert isinstance(项, list)
        for 一对 in 项:
            assert isinstance(一对, (list, tuple)) and len(一对) == 2
            assert isinstance(一对[0], str)
        # 覆盖：当前进程里必然有 PATH 这个键（Windows 大小写不敏感，含不区分大小写的比对）
        # 该断言同时保证 项 非空（空表拿不到 PATH，反跑 环境枚举 改成 return [] 即红）。
        assert any(k.upper() == 'PATH' for k, _ in 项)

    def test_单调时钟递增(self):
        """反跑：改成 time.time()（墙钟可回跳）→ 绝大多数时候仍单调，但语义锚被破坏；
        这里只钉「两次隔 20ms 调用返回严格递增的浮点秒」。"""
        t0 = _b.单调时钟()
        t1 = _b.单调时钟()
        assert isinstance(t0, float)
        _py_time.sleep(0.02)
        t2 = _b.单调时钟()
        assert t1 >= t0
        assert t2 > t1

    def test_环境枚举与进程环境一致(self):
        snap = {k.upper(): v for k, v in os.environ.items()}
        got = dict(_b.环境枚举())
        # 环境枚举 的键集必须是当前进程的子集，且与 os.environ 逐项一致
        for k, v in got.items():
            assert snap.get(k.upper()) == v


class Test常量时间比较:
    def test_相等与不等(self):
        assert _b.常量时间比较(b"abc", b"abc") is True
        assert _b.常量时间比较(b"abc", b"abd") is False

    def test_混型抛错(self):
        """反跑：把 builtins.py:1211 换成 `return 甲 == 乙` → 本断言红。
        `==` 对 bytes vs str 返回 False 而不抛；hmac.compare_digest 则抛 TypeError。
        这正是「不泄露长度/前缀」语义区别于短路相等的关键。"""
        with pytest.raises(TypeError):
            _b.常量时间比较(b"abc", "abc")


class Test光明绑定冒烟:
    """走一遍「光明源码 → 词法 → 语法 → codegen」，证明 builtin_map 的
    `_light_builtin.*` 发射对新内置确实可用，且产物可 exec。不依赖 light CLI。"""

    def test_光明程序调用新内置(self):
        import io
        import contextlib

        from lexer import Lexer
        from light_parser_v3 import LightParser
        from code_generator import PythonCodeGenerator

        源码 = """设 起始 为 单调时钟()。
设 项 为 环境枚举()。
设 字节 为 随机字节(8)。
设 输出 为 "BI2_BAD"。
如果 长度(项) 大于 0 且 单调时钟() 大于等于 起始 且 长度(字节) 等于 8:
  设 输出 为 "BI2_OK"。
结束。
写入输出(输出)。
"""
        # 反跑1：builtin_map 把 单调时钟 等注册成空壳（非 _light_builtin）→ 调用直达 Python 调用，
        #         分裂短路链语义；反跑2：环境枚举/随机字节 从 builtin_map 摘掉 → 未定义段落，codegen
        #         直接抛错。两条都让本断言红。
        module = LightParser().parse(源码)
        py_code = PythonCodeGenerator().generate(module)
        # 行为判据：真跑编译产物（不只是检查产物字符串），成功命中短路链的信令值。
        捕获 = io.StringIO()
        with contextlib.redirect_stdout(捕获):
            exec(compile(py_code, '<bi2_smoke>', 'exec'), {})
        assert "BI2_OK" == 捕获.getvalue().strip(), "编译产物跑通后应命中 BI2_OK 分支"