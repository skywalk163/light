# -*- coding: utf-8 -*-
"""
任务D2-4 + B4：路径护栏（纯光明实现）定向测试

**先说清这测的是什么**：`stdlib/路径护栏.light` 是防误操作的**路径名判定**，
不是安全沙箱。所以本文件不写「攻击被挡住」式断言，只钉两类事实：
  (a) 六条口径按设计生效（见 stdlib/路径护栏.light 头部）；
  (b) 两条缺口（硬链接、TOCTOU 窗口）在 B4 轮已裁决做真防护并**翻成正向
      断言**：硬链接以「拒绝 st_nlink>1 的文件」封住，TOCTOU 以「打开后
      os.fstat 复核」收窄——对应的测试现在断言缺口被补上（见
      test_硬链接指向根外被拒 / test_TOCTOU复核抓住判定后替换）。

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
  - `test_junction指向外部被拒` / `test_硬链接指向根外被拒` 两条带
    skipif(platform != win32)：在 POSIX 上跳过掩盖的是——这两条结论在 POSIX
    上仍只是推导（POSIX 无 junction 概念，要改用 symlink/os.link 复现），
    **未实测**。
  - `test_TOCTOU复核抓住判定后替换` 用普通文件替换复现（os.replace +
    重建），跨平台可跑，无 skip。
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
    """本类里的两条缺口测试（硬链接、TOCTOU）在 B4 轮已从「断言缺口存在」
    翻转为「断言缺口被补上」——同时更新了 stdlib/路径护栏.light 的头部结论
    与机读 安全声明（代码修了声明没改 = 交付缺陷，第三轮 D3 被退回过）。
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
               "「st_nlink>1 拒绝」在 POSIX 上是同一套 os.stat 语义（st_nlink 同为真值），"
               "但本用例的链路未在 POSIX 实测，仍属推导。",
    )
    def test_硬链接指向根外被拒(self, tmp_path):
        """B4-2：根内硬链接指向根外文件——拒绝 st_nlink>1 的文件。

        原来这是「封不住的缺口」钉子（realpath 解析不了硬链接，判「在内」、
        数据在根外）。本轮裁决做真防护：检查必须判拒、读取必须抛错；
        根内普通文件（nlink==1）不得被误伤。"""
        根 = tmp_path / "_taskD2_硬链根"
        根.mkdir()
        外文件 = tmp_path / "_taskD2_硬链目标.txt"
        外文件.write_bytes("根外的数据".encode("utf-8"))
        链 = 根 / "_taskD2_硬链.txt"
        r = subprocess.run(["cmd", "/c", "mklink", "/H", str(链), str(外文件)],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0 or not os.path.exists(str(链)):
            pytest.xfail("本机 mklink /H 失败（跨卷或策略禁用）。掩盖的事实是："
                         "硬链接拒绝本次未实测，结论仍只是推导")
        护栏 = 路径护栏(str(根), {})
        # 修复后：硬链接不再算「在护栏内」——检查判拒、读取/写入抛错
        assert 护栏.检查(str(链)) is False, "硬链接文件必须被判拒（st_nlink>1）"
        with pytest.raises(路径护栏错误):
            护栏.读取(str(链))
        with pytest.raises(路径护栏错误):
            护栏.写入(str(链), b"x")
        # 误伤面检查：根内普通文件（nlink==1）不受影响
        普通 = 根 / "_taskD2_普通.txt"
        普通.write_bytes("普通".encode("utf-8"))
        assert 护栏.检查(str(普通)) is True
        assert 护栏.读取(str(普通)) == "普通".encode("utf-8")
        # 原文件在根外照旧被拒（护栏对越界的判定没有因为 nlink 检查而松动）
        assert 护栏.检查(str(外文件)) is False

    def test_TOCTOU复核抓住判定后替换(self, tmp_path):
        """B4-3：判定通过之后、真正 open 之前路径被换掉——打开后 fstat 复核
        必须抓住 inode 变化并拒绝，不许读到被换入的文件。

        用 护栏.测试钩子 注入替换：钩子在「核准之后、os.open 之前」被调用。
        原来这是「窗口真实存在」钉子（判定后替换拦不住）；本轮裁决做真防护，
        窗口必须被复核收窄。跨平台：普通文件替换即可复现，不依赖 junction。
        """
        根 = tmp_path / "_taskD2_窗口根"
        根.mkdir()
        护栏 = 路径护栏(str(根), {})
        目标 = 根 / "_taskD2_文件.txt"
        目标.write_bytes("内部数据".encode("utf-8"))
        备份 = 根 / "_taskD2_被挪走的旧inode.txt"
        calls = []

        def 换掉(实):
            # 判定后、打开前：把目标文件换成另一个 inode（旧文件挪走）
            calls.append(实)
            os.replace(str(目标), str(备份))
            目标.write_bytes("外部数据".encode("utf-8"))  # 新 inode，内容不同

        护栏.测试钩子 = 换掉
        try:
            结果 = 护栏.读取(str(目标))
        except Exception as 错误:
            结果 = 错误
        finally:
            护栏.测试钩子 = None
        assert len(calls) == 1, "测试钩子必须被调用（否则用例自身失效）"
        assert isinstance(结果, Exception), \
            f"读取必须被复核拦下（inode 变了），实际竟成功返回：{结果!r}"
        assert "TOCTOU" in str(结果), f"错误消息必须点明 TOCTOU，实际：{结果!r}"
        # 复核拒绝的是「读进被换入的文件」；旧 inode 的数据没有被侧信道读出
        assert 备份.read_bytes() == "内部数据".encode("utf-8")


class Test对抗用例_D9:
    """D9-S1 改写护栏（32 行 os 直调 → 16 行系统边界段）之后新增的三条对抗用例。

    改写红线是「不许降低安全性」，所以这三条按攻击面分：**词法穿越**、
    **链接穿透**、**Windows 路径别名**。每条都带反跑；其中链接穿透那条的反跑是
    **可执行的变异探针**（把 realpath 换成词法 abspath，同一条穿越立刻通过），
    不是注释里的一句话。
    """

    def test_多级点穿越与混合分隔符全被拒(self, tmp_path):
        """`..` 穿越的四种形态：单级、多级、混合分隔符、先进子目录再退两级。

        同时钉住**不许误伤**：`根/子/../文件` 折回根内，必须放行——把 `..`
        一律当越界是最省事也最错的实现。

        反跑：把 `规范路径` 里的 `己.真实路径(路径)` 换成内置 `绝对路径(路径)`
        （abspath 是纯词法的，会把 `根/../外面` 折成 `根/外面`）→ 前四格立红。
        """
        根 = tmp_path / "_taskD9_沙箱"
        根.mkdir()
        (根 / "子").mkdir()
        护栏 = 路径护栏(str(根), {})
        外文件 = tmp_path / "_taskD9_外面.txt"
        外文件.write_bytes("根外的数据".encode("utf-8"))

        穿越形态 = [
            os.path.join(str(根), "..", "_taskD9_外面.txt"),
            os.path.join(str(根), "子", "..", "..", "_taskD9_外面.txt"),
            str(根).replace(os.sep, "/") + "/../_taskD9_外面.txt",
            os.path.join(str(根), "子", "..", "..", "..",
                         os.path.basename(str(tmp_path)), "_taskD9_外面.txt"),
        ]
        for 形态 in 穿越形态:
            assert 护栏.检查(形态) is False, "穿越形态没被拦：" + 形态
            with pytest.raises(路径护栏错误):
                护栏.核准(形态)
            with pytest.raises(路径护栏错误):
                护栏.读取(形态)

        # 误伤面：折回根内的 `..` 必须放行，且真的能写进去
        回内 = os.path.join(str(根), "子", "..", "_taskD9_回内.txt")
        assert 护栏.检查(回内) is True
        assert 护栏.写入(回内, b"in") is True
        assert (根 / "_taskD9_回内.txt").read_bytes() == b"in"

    def test_链接指向沙箱外时经过链接的子路径也被拒_附变异反跑(self, tmp_path):
        """既有用例只断「链接本身被拒」。攻击者不会去读链接本身，而是读
        `根/链接/秘密.txt` —— 这条把**穿过链接的子路径**钉住。

        末尾是反跑（变异探针）：把实例的 `真实路径` 换成词法 abspath，
        同一条子路径立刻被判「在护栏内」。这证明本条判据靠的是 realpath 那一步，
        不是碰巧通过。
        """
        根 = tmp_path / "_taskD9_链根"
        根.mkdir()
        外目录 = tmp_path / "_taskD9_链外目录"
        外目录.mkdir()
        (外目录 / "_taskD9_秘密.txt").write_bytes("外部机密".encode("utf-8"))
        链接 = 根 / "_taskD9_逃逸"
        模式 = None
        try:
            os.symlink(str(外目录), str(链接), target_is_directory=True)
            if os.path.islink(str(链接)):
                模式 = "symlink"
        except (OSError, NotImplementedError):
            pass
        if 模式 is None and sys.platform == "win32":
            r = subprocess.run(["cmd", "/c", "mklink", "/J", str(链接), str(外目录)],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and os.path.exists(str(链接)):
                模式 = "junction"
        if 模式 is None:
            pytest.xfail("symlink 与 junction 都建不起来（掩盖：链接穿透从未真机验证）")

        子路径 = os.path.join(str(链接), "_taskD9_秘密.txt")
        护栏 = 路径护栏(str(根), {})
        assert 护栏.检查(子路径) is False, "穿过链接的子路径必须被拒（%s）" % 模式
        with pytest.raises(路径护栏错误):
            护栏.读取(子路径)

        # —— 反跑：把 realpath 这一步替换成词法 abspath，穿越必须变成「通过」——
        护栏.真实路径 = lambda 路径: os.path.abspath(路径)
        assert 护栏.检查(子路径) is True, \
            "变异探针失效：去掉 realpath 之后本用例仍然判拒，说明它不是靠 realpath 拦住的"

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="8.3 短名 / `\\\\?\\` 扩展形态 / 大小写不敏感都是 Windows 专属。"
               "POSIX 上跳过掩盖了：这三种别名形态在 POSIX 上不存在（短名无、"
               "扩展前缀无、大小写敏感），对应结论未在 POSIX 实测。",
    )
    def test_Windows短名与UNC与大小写变体(self, tmp_path):
        r"""Windows 上同一个文件有多种写法。护栏的口径是「realpath 展开 +
        normcase 归一之后再比」，所以：

          - 8.3 短名（`很长的~1`）指向沙箱内 → 放行（realpath 会展开）；
          - 全大写形态 → 放行（normcase 归一大小写）；
          - 沙箱外的大写形态 → 仍然拒（归一化不等于放松）；
          - `\\?\` 扩展长度形态 → **一律拒**（本机 Python 3.14 的 realpath 把
            `\\?\C:\x` 变成 `\\C:x` 这种非法 UNC 形状，归一后分量对不上根）。
            这是**可用性限制而非安全漏洞**（方向是 fail-closed），本轮记录在案。

        反跑：把 `规范路径` 里的 `归一大小写(实, 己.平台代号)` 改成直接 `返回 实`，
        「全大写形态放行」那格立红。
        """
        import ctypes
        根 = tmp_path / "_taskD9_很长的沙箱目录名字LongSandboxName"
        根.mkdir()
        文件 = 根 / "_taskD9_目标.txt"
        文件.write_bytes(b"inside")
        护栏 = 路径护栏(str(根), {})

        缓冲 = ctypes.create_unicode_buffer(1024)
        长度 = ctypes.windll.kernel32.GetShortPathNameW(str(文件), 缓冲, 1024)
        if 长度 and 缓冲.value != str(文件):
            assert 护栏.检查(缓冲.value) is True, "短名指向沙箱内却被拒：" + 缓冲.value
            assert 护栏.读取(缓冲.value) == b"inside"
        else:
            pytest.xfail("本卷未启用 8.3 短名（掩盖：短名展开本次未实测）")

        assert 护栏.检查(str(文件).upper()) is True
        assert 护栏.读取(str(文件).upper()) == b"inside"

        外文件 = tmp_path / "_taskD9_外面大写.TXT"
        外文件.write_bytes(b"outside")
        assert 护栏.检查(str(外文件).upper()) is False

        扩展形态 = "\\\\?\\" + str(文件)
        assert 护栏.检查(扩展形态) is False, \
            "扩展长度形态的实测结论变了（原为 fail-closed 一律拒），口径要重新记录"


class Test原子写入_D9:
    """D9-S1 新增 `原子写入`：临时文件 + 原子替换。原来这段在
    `stdlib/代理工具集.light` 里有**两份**拷贝（write_file / edit_file 各一套，
    共 20 行 Python 直调），搬进护栏后去重，并且临时文件路径也过 `核准`。
    """

    def test_覆盖写成功且不留临时文件(self, tmp_path):
        """反跑：把 `原子写入` 里的 `己.落位替换(临时路径, 实)` 删掉，
        「目标内容被更新」立红；把 `己.清除(临时路径)` 之外的成功路径改成
        不替换（只写临时文件），「不留临时文件」也会立红。"""
        护栏 = _新建(tmp_path)
        目标 = str(tmp_path / "_taskD9_原子.txt")
        assert 护栏.原子写入(目标, b"first") is True
        assert 护栏.读取(目标) == b"first"
        assert 护栏.原子写入(目标, b"second-longer") is True
        assert 护栏.读取(目标) == b"second-longer"
        残留 = [n for n in os.listdir(str(tmp_path)) if n.endswith(".tmp")]
        assert 残留 == []

    def test_越界目标抛错且沙箱外无落盘(self, tmp_path):
        """反跑：把 `原子写入` 首行 `己.核准(路径)` 换成 `己.规范路径(路径)`
        （只归一化、不判越界）→ 本条立红且沙箱外真会落盘。"""
        根 = tmp_path / "_taskD9_原子根"
        根.mkdir()
        护栏 = 路径护栏(str(根), {})
        坏 = str(tmp_path / "_taskD9_原子越界.txt")
        with pytest.raises(路径护栏错误):
            护栏.原子写入(坏, b"x")
        assert os.path.exists(坏) is False
        assert [n for n in os.listdir(str(tmp_path)) if n.endswith(".tmp")] == []


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
