# -*- coding: utf-8 -*-
"""
任务D2-4：路径护栏（纯光明实现）定向测试

**先说清这测的是什么**：`stdlib/路径护栏.light` 是防误操作的**路径名判定**，
不是安全沙箱。所以本文件不写「攻击被挡住」式断言，只钉两类事实：
  (a) 六条口径按设计生效（见 stdlib/路径护栏.light 头部）；
  (b) 两条**已知缺口确实存在**（硬链接、TOCTOU 窗口）——反向钉住，防止后人
      把它当安全边界用；哪天有人以为补上了，那两条会红。

覆盖：
  - 根内可读写（写入→续写→读取 往返）、核准返回归一化路径
  - 根外 / `..` 穿越 / 兄弟目录裸前缀 被拒；越界写入真的没落盘
  - symlink 或 junction 指向根外被拒（realpath **解析链接之后**再比）
  - 尚不存在的路径可判定（写入前必须先判）
  - 白名单（放在根之外）被采纳、清单快照、空根拒绝构造
  - 二进制字节不被 Windows 文本模式截断/改写（0x1A、0x0A）；大文件按块读完整
  - 读失败不吞成空 bytes
  - 环境变量白/黑名单过滤（沿用 进程树.light 思路）

skip 掩盖分析（本机实跑结果：Windows 上 0 skip，junction 与硬链接都真建成了）：
  - `test_链接指向外部被拒` 内部两级回退：os.symlink（要管理员/开发者模式）→
    mklink /J。**两者都失败才 skip**，那时掩盖的是「链接逃逸从未真机验证」。
    本机实测走的是哪条会在断言消息里带出来。
  - `test_junction指向外部被拒` / `test_硬链接是已知封不住的缺口` /
    `test_TOCTOU窗口真实存在` 三条带 `skipif(platform != win32)`：在 POSIX 上
    跳过掩盖的是——这三条结论在 POSIX 上仍只是推导（POSIX 无 junction 概念，
    要改用 symlink/os.link 复现），**未实测**。
  - `test_读失败不被吞成空bytes` 不是 skip，但有一处覆盖不到：Windows 上对目录
    os.open 就直接 PermissionError，所以模块里手写的「os.read 失败 → 先关句柄
    再抛」那条分支本次没被走到（见自测报告未实测项）。
"""
import os
import subprocess
import sys

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT)
sys.path.insert(0, os.path.join(_PROJECT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT, 'stdlib'))

import _light_import_hook
_light_import_hook.install([os.path.join(_PROJECT, 'stdlib'), _PROJECT])

import pytest

from 路径护栏 import 路径护栏, 路径护栏错误


def _新建(root):
    return 路径护栏(str(root), {})


class Test白名单内:
    def test_写入读取往返(self, tmp_path):
        护栏 = _新建(tmp_path)
        目标 = str(tmp_path / "_taskD2_数据.bin")
        assert 护栏.写入(目标, "任务D2护栏内容".encode("utf-8")) is True
        assert 护栏.读取(目标) == "任务D2护栏内容".encode("utf-8")

    def test_追加生效(self, tmp_path):
        护栏 = _新建(tmp_path)
        目标 = str(tmp_path / "_taskD2_追加.txt")
        护栏.写入(目标, "一".encode("utf-8"))
        护栏.续写(目标, "二".encode("utf-8"))
        assert 护栏.读取(目标) == "一二".encode("utf-8")

    def test_根目录本身允许(self, tmp_path):
        护栏 = _新建(tmp_path)
        assert 护栏.检查(str(tmp_path)) is True
        assert 护栏.核准(str(tmp_path)) == os.path.normcase(os.path.realpath(str(tmp_path)))


class Test白名单外:
    def test_越界路径被拒(self, tmp_path):
        护栏 = _新建(tmp_path)
        外面 = str(tmp_path.parent / "_taskD2_外面.txt")
        assert 护栏.检查(外面) is False
        with pytest.raises(路径护栏错误):
            护栏.核准(外面)

    def test_点穿越被拒(self, tmp_path):
        护栏 = _新建(tmp_path)
        穿越 = str(tmp_path / ".." / "_taskD2_穿越.txt")
        assert 护栏.检查(穿越) is False
        with pytest.raises(路径护栏错误):
            护栏.核准(穿越)

    def test_系统目录被拒(self, tmp_path):
        护栏 = _新建(tmp_path)
        assert 护栏.检查(os.environ.get("TEMP", "C:/Windows/Temp")) is False


class Test符号链接逃逸:
    def test_链接指向外部被拒(self, tmp_path):
        """realpath 必须在符号链接解析之后比较：链接在护栏内但指向外面 → 拒。

        Windows 上 os.symlink 可能因缺管理员/开发者模式失败，也可能在受限
        环境下"创建成功"但 islink 为假（实际不是真链接）；此时回退到 junction
        （mklink /J，不需要管理员）。两者都不可用才 skip——该 skip 掩盖了
        「链接逃逸从未真机验证」。
        """
        护栏 = _新建(tmp_path)
        外面目录 = tmp_path.parent / "_taskD2_链接目标目录"
        外面目录.mkdir(exist_ok=True)
        链接 = tmp_path / "_taskD2_逃逸链接"
        模式 = None
        # 先试 symlink（目录链接）
        try:
            os.symlink(str(外面目录), str(链接), target_is_directory=True)
            if os.path.islink(str(链接)):
                模式 = "symlink"
        except (OSError, NotImplementedError):
            pass
        # Windows：symlink 不可用则回退 junction（先清掉 os.symlink 可能留下的残骸；
        # 沙箱会把目录 symlink 模拟成普通目录，os.remove 清不掉 → 用 rmdir 再 remove）
        if 模式 is None and sys.platform == "win32":
            try:
                os.rmdir(str(链接))
            except OSError:
                try:
                    os.remove(str(链接))
                except OSError:
                    pass
            try:
                r = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(链接), str(外面目录)],
                    capture_output=True, text=True, timeout=10,
                )
                if r.returncode == 0 and os.path.exists(str(链接)):
                    模式 = "junction"
            except Exception:
                pass
        if 模式 is None:
            pytest.xfail(f"symlink 与 junction 都不可用（掩盖：链接逃逸从未真机验证）")
        try:
            # 链接在护栏内（realpath 前），但 realpath 后指向外部 → 必须拒
            assert 护栏.检查(str(链接)) is False, \
                f"realpath 应解析{模式}并发现越界"
            with pytest.raises(路径护栏错误):
                护栏.核准(str(链接))
        finally:
            # 只清理自己创建的链接/目标（按路径，绝不碰别的）
            try:
                os.rmdir(str(链接))
            except OSError:
                try:
                    os.remove(str(链接))
                except OSError:
                    pass
            try:
                os.rmdir(str(外面目录))
            except OSError:
                pass

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="junction 是 Windows 专属（mklink /J）。POSIX 上跳过掩盖了："
               "realpath 解析 junction（GetFinalPathNameByHandle）路径从未在"
               "POSIX 上跑过——POSIX 用 symlink 语义，无 junction 概念。",
    )
    def test_junction指向外部被拒(self, tmp_path):
        护栏 = _新建(tmp_path)
        外面 = tmp_path.parent / "_taskD2_junction目标"
        外面.mkdir(exist_ok=True)
        链接 = tmp_path / "_taskD2_junction链接"
        r = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(链接), str(外面)],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0 or not os.path.exists(str(链接)):
            pytest.xfail(f"junction 创建失败（掩盖：junction 逃逸从未真机验证）：{r.stderr}")
        try:
            assert 护栏.检查(str(链接)) is False, "junction 指向外部必须被拒"
            with pytest.raises(路径护栏错误):
                护栏.核准(str(链接))
        finally:
            try:
                os.rmdir(str(链接))
            except OSError:
                pass
            try:
                os.rmdir(str(外面))
            except OSError:
                pass


class Test白名单扩展与环境:
    def test_附加白名单目录可写(self, tmp_path):
        """回归钉子：白名单目录**放在根之外**，才真正测到「白名单被采纳」。

        首版把入参局部变量命名成 白名单（与属性同名），被编译成 self.白名单 后
        又被 `己.白名单 为 []` 清空，传进来的白名单**静默丢弃**。若白名单目录
        建在 tmp_path 里面，那条 bug 会被「根目录本身就放行」掩盖，测试照样绿。
        """
        根 = tmp_path / "_taskD2_主根"
        根.mkdir()
        旁路 = tmp_path / "_taskD2_旁路"          # 刻意在根之外
        旁路.mkdir()
        护栏 = 路径护栏(str(根), {"白名单": [str(旁路)]})
        assert 护栏.检查(str(旁路)) is True
        目标 = str(旁路 / "文件.txt")
        assert 护栏.写入(目标, "旁路可写".encode("utf-8")) is True
        assert 护栏.读取(目标) == "旁路可写".encode("utf-8")
        # 白名单归一化后确实进了快照（根在首位）
        快 = 护栏.清单快照()
        assert 快[0] == os.path.normcase(os.path.realpath(str(根)))
        assert os.path.normcase(os.path.realpath(str(旁路))) in 快
        assert len(快) == 2
        # 根与白名单之外的第三处仍被拒
        第三 = tmp_path / "_taskD2_第三处"
        第三.mkdir()
        assert 护栏.检查(str(第三 / "谁的.txt")) is False

    def test_不给白名单时只认根这一棵树(self, tmp_path):
        根 = tmp_path / "_taskD2_只此一根"
        根.mkdir()
        护栏 = 路径护栏(str(根), {})
        assert 护栏.清单快照() == [os.path.normcase(os.path.realpath(str(根)))]
        assert 护栏.检查(str(tmp_path)) is False

    @pytest.mark.parametrize("坏根", [None, ""])
    def test_空根目录直接拒绝构造而不是放行全盘(self, 坏根):
        """空根**绝不**解释成 allow-all —— 那是护栏最危险的默认值。"""
        with pytest.raises(路径护栏错误):
            路径护栏(坏根, {})

    def test_环境黑名单过滤(self, tmp_path):
        护栏 = _新建(tmp_path)
        os.environ["_TASKD2_秘密"] = "不该外传"
        try:
            环境 = 护栏.构建环境({"拒绝环境": ["_TASKD2_秘密", "PATH"]})
            assert "_TASKD2_秘密" not in 环境
            assert "PATH" not in 环境
            assert len(环境) > 0                  # 不是把整个环境清空了
        finally:
            os.environ.pop("_TASKD2_秘密", None)

    def test_环境白名单只留前缀命中的(self, tmp_path):
        """原版断言是 `len==0 or all(...)` —— 恒真，等于没测。这里给一个
        真实存在的命中项 + 一个真实存在的不命中项，两边都要断。"""
        护栏 = _新建(tmp_path)
        os.environ["_TASKD2_留下我"] = "1"
        try:
            环境 = 护栏.构建环境({"允许环境": ["_TASKD2_"]})
            assert 环境 == {"_TASKD2_留下我": "1"}
            assert "PATH" in os.environ and "PATH" not in 环境
        finally:
            os.environ.pop("_TASKD2_留下我", None)

    def test_环境允许清单为空表示不过滤(self, tmp_path):
        护栏 = _新建(tmp_path)
        assert len(护栏.构建环境({})) == len(dict(os.environ))


class Test口径与已知缺口:
    """本类里有两条测试**断言缺口存在**，不是断言缺口被补上。

    哪天有人以为补上了，它们会红，从而逼他同时改 stdlib/路径护栏.light 的头部
    结论与 自测报告_任务D2.md ——防止「护栏被当成沙箱用」这类误读悄悄发生。
    """

    def test_安全声明自报不是安全边界(self, tmp_path):
        句 = _新建(tmp_path).安全声明()
        for 词 in ("不是安全边界", "TOCTOU", "landlock", "硬链接"):
            assert 词 in 句, f"机读口径声明里缺「{词}」"

    def test_核准返回归一化路径供调用方直接使用(self, tmp_path):
        """判定的路径与随后 open 的路径必须是同一个，否则等于没判。"""
        护栏 = _新建(tmp_path)
        原 = str(tmp_path / "里面" / ".." / "_taskD2_归一.txt")
        assert 护栏.核准(原) == os.path.normcase(
            os.path.realpath(str(tmp_path / "_taskD2_归一.txt")))

    def test_兄弟目录不因裸字符串前缀被误放行(self, tmp_path):
        """按路径分量比而非按裸前缀比：根 `…/_taskD2_根` 不能收 `…/_taskD2_根_旁边`。"""
        根 = tmp_path / "_taskD2_根"
        根.mkdir()
        旁 = tmp_path / "_taskD2_根_旁边"
        旁.mkdir()
        护栏 = 路径护栏(str(根), {})
        实旁 = os.path.normcase(os.path.realpath(str(旁)))
        实根 = os.path.normcase(os.path.realpath(str(根)))
        assert 实旁.startswith(实根)                    # 裸前缀确实成立
        assert 护栏.检查(str(旁 / "东西.txt")) is False  # 但护栏不上钩

    def test_尚不存在的路径也能判定(self, tmp_path):
        """写入前必须先判，所以「路径还不存在」不能因为 stat 失败就放行/误拒。"""
        护栏 = _新建(tmp_path)
        assert 护栏.检查(str(tmp_path / "还没建" / "更深" / "新文件.txt")) is True
        assert 护栏.检查(str(tmp_path.parent / "还没建" / "新文件.txt")) is False

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="用 Windows 的 mklink /H 建硬链接。POSIX 上跳过掩盖了："
               "「硬链接在 POSIX 上同样封不住」这一条仍是推导，未实测。",
    )
    def test_硬链接是已知封不住的缺口(self, tmp_path):
        """硬链接没有可解析的目标，realpath 原样返回根内路径 → 护栏判「在内」，
        而读到的数据其实在根外。**本测试钉住这个缺口存在。**"""
        根 = tmp_path / "_taskD2_硬链根"
        根.mkdir()
        外文件 = tmp_path / "_taskD2_硬链目标.txt"
        外文件.write_bytes("根外的数据".encode("utf-8"))
        链 = 根 / "_taskD2_硬链.txt"
        r = subprocess.run(["cmd", "/c", "mklink", "/H", str(链), str(外文件)],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0 or not os.path.exists(str(链)):
            pytest.xfail("本机 mklink /H 失败（跨卷或策略禁用）。掩盖的事实是："
                         "硬链接缺口本次未实测，头部那句结论仍只是推导")
        护栏 = 路径护栏(str(根), {})
        assert 护栏.检查(str(链)) is True                          # 缺口：判在内
        assert 护栏.读取(str(链)) == "根外的数据".encode("utf-8")   # 数据却在根外

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="用 Windows 的 mklink /J 制造替换。POSIX 上跳过掩盖了："
               "「TOCTOU 窗口」在 POSIX 上未实证（原理相同，用 symlink 复现）。",
    )
    def test_TOCTOU窗口真实存在(self, tmp_path):
        """判定通过之后、真正 open 之前，路径可以被换掉。**本测试钉住窗口存在**，
        证明护栏只拦失误、拦不住并发替换。"""
        根 = tmp_path / "_taskD2_窗口根"
        (根 / "会被换掉").mkdir(parents=True)
        外 = tmp_path / "_taskD2_窗口外"
        外.mkdir()
        护栏 = 路径护栏(str(根), {})
        判 = 护栏.核准(str(根 / "会被换掉" / "文件.txt"))     # 此刻：在根内
        assert 判 == os.path.normcase(os.path.realpath(str(根 / "会被换掉" / "文件.txt")))
        os.rmdir(str(根 / "会被换掉"))
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(根 / "会被换掉"), str(外)],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            pytest.xfail("本机 mklink /J 失败。掩盖的事实是：TOCTOU 窗口本次未实证，"
                         "头部那句「存在 TOCTOU 窗口」仍只是推导")
        # 同一个原始入参，现在解析到根外——判定早已发生，护栏拦不住这次替换
        assert 护栏.检查(str(根 / "会被换掉" / "文件.txt")) is False


class Test读写不吞错:
    def test_二进制字节不被文本模式改写或截断(self, tmp_path):
        """Windows 上 os.open 默认文本模式，两处静默损坏：

          - 读到 0x1A（Ctrl-Z）当 EOF 停下 → 后面的数据凭空消失；
          - 写出时 0x0A 被翻成 0x0D 0x0A → 长度变了、内容变了。

        实测首版写 230400 字节、读回来只有 26 字节（第一个 0x1A 的下标），
        全程不报错。这条用最小料把两个字节都点出来。
        """
        护栏 = _新建(tmp_path)
        目标 = str(tmp_path / "_taskD2_二进制.bin")
        料 = b"\x00\x0a\x1a\x0d\x0a\xff\xfe\x01\x02"
        护栏.写入(目标, 料)
        assert os.path.getsize(目标) == len(料), "落盘长度就变了 → 写出被文本模式改写"
        assert 护栏.读取(目标) == 料

    def test_超过单次读长度的文件被完整读回(self, tmp_path):
        """读实现是 65536 一块的循环；一次读不完的文件不能只回来半截。"""
        护栏 = _新建(tmp_path)
        目标 = str(tmp_path / "_taskD2_大文件.bin")
        料 = bytes(range(256)) * 900          # 230400 字节 > 3 块
        护栏.写入(目标, 料)
        回 = 护栏.读取(目标)
        assert len(回) == len(料)
        assert 回 == 料

    def test_读失败不被吞成空bytes(self, tmp_path):
        """首版 `捕获 错误: 内容 为 b""` 把权限不足/是目录/被占用统统伪装成
        「文件是空的」——本项目最高优先级的静默错误类。现在必须报错。

        注意：Windows 上对目录 os.open 就直接 PermissionError，所以异常来自
        os.open 而非模块里手写的「先关句柄再抛」分支；两者都算「没吞」。**这条
        测试因此没有覆盖到 os.read 失败那条分支**（见自测报告未实测项）。
        """
        护栏 = _新建(tmp_path)
        子目录 = tmp_path / "_taskD2_我是目录"
        子目录.mkdir()
        结果 = None
        try:
            结果 = 护栏.读取(str(子目录))
        except Exception as 错误:
            结果 = 错误
        assert isinstance(结果, Exception), f"读目录必须报错，实际静默返回了 {结果!r}"

    def test_越界写入真的没落盘(self, tmp_path):
        护栏 = _新建(tmp_path)
        坏 = str(tmp_path.parent / "_taskD2_不该出现.txt")
        with pytest.raises(路径护栏错误):
            护栏.写入(坏, b"x")
        with pytest.raises(路径护栏错误):
            护栏.续写(坏, b"x")
        assert not os.path.exists(坏)
