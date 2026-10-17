# -*- coding: utf-8 -*-
"""test_R159_L218_ContentLength口径.py —— R159-B（L-218）wire 协议字节口径。

被测缺陷（R158-C 逐请求取证，R159-B 修复）：
  `stdlib/分布式/节点网络.light` 的 HTTP 头用**字符数**声明 Content-Length，
  而 UTF-8 多字节键名（`节点ID` / `在跑任务`）的实际字节数更大：
    v2 727/727 请求 CL声明=84 vs 实际字节=114；
    v3 12874/12874 请求 CL声明=86 vs 实际字节=116。
  迷你主控靠「0.5s 抽干」容错才没暴露；**严格 master 按 CL 截断体 → JSON 截在
  中文键中间 → 解析失败**。
  同族缺陷在解析侧：`解析响应` 拿字节口径的 CL 当**字符下标**切体（截取 是字符语义），
  响应体含中文时被切短/错位。

本文件怎么判（全部真编译 + 真跑原生腿 + 真 socket 对端）：
  A 声明侧：本文件内置**严格 master**（按 CL 精确读体，不抽干），逐请求核对
    「CL 声明值 == 体 UTF-8 字节数」，并核对 master 侧 JSON 能完整解析。
  B 解析侧：master 返回含中文的 JSON 体（CL 用字节数）→ 客户端必须取到完整中文值。
  C 反跑（证明断言有牙）：master 故意按**旧口径**（CL = 字符数）应答 → 客户端
    `解析响应` 必须失败（结构化错误），不得静默取到半截值。
  D 口径自证：同一段中文，`长()` 与 `字节长度(字符串转字节())` 必须不等
    （否则本文件的 A/B 用例根本没有区分力，属假绿）。

平台：本机 Windows 只做初筛（L0）；权威证据在 0.82，Linux 平台证据在 0.86。
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading

import pytest

_测试目录 = os.path.dirname(os.path.abspath(__file__))
_仓库根 = os.path.dirname(os.path.dirname(_测试目录))
if os.path.join(_仓库根, 'src') not in sys.path:
    sys.path.insert(0, os.path.join(_仓库根, 'src'))
if os.path.join(_仓库根, 'tests') not in sys.path:
    sys.path.insert(0, os.path.join(_仓库根, 'tests'))

from _native_helpers import skip_without_clang  # type: ignore[import]  # noqa: E402

子进程口径 = dict(capture_output=True, text=True, encoding='utf-8', errors='replace')


# ═══════════════════════════════════════════════════════════════════════════
# 严格 master：按 Content-Length 精确读体（不抽干），逐请求留证
# ═══════════════════════════════════════════════════════════════════════════
class 严格主控:
    """最小 JSON-RPC over HTTP/1.1 主控。

    `严格=True`   → 应答头 CL = 体 UTF-8 字节数（正确口径）
    `严格=False`  → 应答头 CL = 体字符数（复刻 L-218 旧口径，用于反跑）
    """

    def __init__(self, 应答体, 严格=True):
        self.应答体 = 应答体
        self.严格 = 严格
        self.记录 = []          # [(方法, CL声明, 实际字节数, 体文本)]
        self.解析失败 = 0
        self.端口 = None
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", 0))
        self.端口 = self._srv.getsockname()[1]
        self._srv.listen(8)
        self._srv.settimeout(0.3)
        self._停 = False
        self._线程 = threading.Thread(target=self._循环, daemon=True)

    def __enter__(self):
        self._线程.start()
        return self

    def __exit__(self, *a):
        self._停 = True
        self._线程.join(timeout=3)
        try:
            self._srv.close()
        except OSError:
            pass

    def _循环(self):
        while not self._停:
            try:
                连接, _ = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                self._处理(连接)
            finally:
                try:
                    连接.close()
                except OSError:
                    pass

    def _处理(self, 连接):
        连接.settimeout(5.0)
        缓冲 = b""
        while b"\r\n\r\n" not in 缓冲:
            块 = 连接.recv(4096)
            if not 块:
                return
            缓冲 += 块
        头, 余 = 缓冲.split(b"\r\n\r\n", 1)
        声明 = 0
        for 行 in 头.decode("utf-8", "replace").split("\r\n"):
            if 行.lower().startswith("content-length:"):
                声明 = int(行.split(":", 1)[1].strip())
        体 = 余
        # **严格**：只按 CL 读，不做「抽干」容错 —— 这正是 L-218 的判据
        while len(体) < 声明:
            块 = 连接.recv(4096)
            if not 块:
                break
            体 += 块
        体 = 体[:声明] if 声明 else 体
        方法 = ""
        try:
            载荷 = json.loads(体.decode("utf-8"))
            方法 = 载荷.get("方法", "")
        except Exception:
            self.解析失败 += 1
        self.记录.append((方法, 声明, len(体), 体.decode("utf-8", "replace")))

        文本 = json.dumps(self.应答体, ensure_ascii=False)
        字节体 = 文本.encode("utf-8")
        声明值 = len(字节体) if self.严格 else len(文本)   # 旧口径：字符数
        头文本 = ("HTTP/1.1 200 OK\r\n"
                  "Content-Type: application/json; charset=utf-8\r\n"
                  "Content-Length: %d\r\n"
                  "Connection: close\r\n\r\n" % 声明值).encode("utf-8")
        连接.sendall(头文本 + 字节体)


# ═══════════════════════════════════════════════════════════════════════════
# 辅助：写 .light（无 BOM / LF）、原生腿编译、真跑
# ═══════════════════════════════════════════════════════════════════════════
def _写文件(目录, 名, 内容):
    路径 = os.path.join(目录, 名)
    with open(路径, 'w', encoding='utf-8', newline='\n') as f:
        f.write(内容)
    return 路径


def _编译并跑(源, 目录):
    from llvm.compiler import compile_light_typed  # type: ignore[import]
    主 = _写文件(目录, '主.light', 源)
    产物 = os.path.join(目录, '产物')
    exe = compile_light_typed(主, 产物, optimize_level=0)
    结果 = subprocess.run([exe], cwd=目录, timeout=120, **子进程口径)
    return 结果.returncode, 结果.stdout.replace('\r', '').strip()


def _客户端程序(端口):
    """发一个含中文键名的请求；解析失败时明确打印「解析失败」。"""
    return (
        "从 节点网络 导入 客户端\n"
        "\n"
        "段落 主():\n"
        '  设 客 为 客户端("127.0.0.1", %d, 5.0)\n'
        '  设 回 为 客.请求("领任务", ["节点ID": "N1234", "在跑任务": []])\n'
        '  如果 回["错误"] != 空:\n'
        '    打印("解析失败")\n'
        "  否则:\n"
        '    打印(回["结果"]["消息"])\n'
        "\n"
        "主()。\n" % 端口
    )


# ═══════════════════════════════════════════════════════════════════════════
# 用例
# ═══════════════════════════════════════════════════════════════════════════
@skip_without_clang
def test_A_声明侧_CL等于UTF8字节数(tmp_path):
    """客户端请求头里的 Content-Length 必须等于体 UTF-8 字节数（严格 master 判）。"""
    with 严格主控({"结果": {"消息": "中文测试"}, "错误": None}) as 主控:
        rc, 输出 = _编译并跑(_客户端程序(主控.端口), str(tmp_path))
        assert rc == 0, 输出
        assert 主控.记录, "master 没收到任何请求（客户端没连上/没发出）"
        方法, 声明, 实际, 体 = 主控.记录[0]
        assert 方法 == "领任务", 体
        # ① 声明值必须等于真实字节数（旧实现这里是字符数，必然更小）
        assert 声明 == 实际, "CL 声明 %d != 实际字节 %d（体=%r）" % (声明, 实际, 体)
        # ② 严格 master 按 CL 截断后必须仍能解析出 JSON（截短就会解析失败）
        assert 主控.解析失败 == 0, "按 CL 截断后 JSON 解析失败，说明声明值与实际不一致"
        # ③ 体里确实有中文键名（否则本用例没有区分力）
        assert "节点ID" in 体
        assert len(体.encode("utf-8")) > len(体), "体里没有多字节字符，用例无区分力"


@skip_without_clang
def test_B_解析侧_中文响应体按字节切取(tmp_path):
    """响应体含中文时，解析响应 必须按字节口径切体，取到完整中文值。"""
    with 严格主控({"结果": {"消息": "中文测试"}, "错误": None}) as 主控:
        rc, 输出 = _编译并跑(_客户端程序(主控.端口), str(tmp_path))
    assert rc == 0, 输出
    assert 输出 == "中文测试", "响应体被切错位，实际输出=%r" % 输出


@skip_without_clang
def test_C_反跑_旧口径应答被客户端判为失败(tmp_path):
    """反跑锚点（应答侧）：master 按旧口径（CL=字符数）应答 → 客户端不得当成成功。

    旧口径下客户端只读到「字符数个字节」，体在中文中间被切断。本用例只要求
    「不把半截体当成功值」——具体失败形态（结构化错误 / 进程异常退出）都算失败，
    因为**唯一不能接受的结果是静默取到半截值**。
    （请求侧的严格 master 反跑见 `_r159_scratch/b_*`：旧客户端 + 严格 master
      时 master 侧 JSON 解析必然失败，那是 L-218 的原始缺陷形态。）
    """
    with 严格主控({"结果": {"消息": "中文测试"}}, 严格=False) as 主控:
        rc, 输出 = _编译并跑(_客户端程序(主控.端口), str(tmp_path))
    assert 输出 != "中文测试", "旧口径（CL=字符数）下客户端仍取到完整值 → 用例无区分力"
    assert rc != 0 or 输出 == "解析失败", (
        "旧口径下客户端既没报错也没崩溃，输出了 %r —— 失败形态不明，需人工确认" % 输出)


@skip_without_clang
def test_D_口径自证_字符数不等于字节数(tmp_path):
    """口径自证：同一段中文 `长()` 与 `字节长度(字符串转字节())` 必须不等。"""
    源 = (
        "从 编码 导入 字符串转字节, 字节长度\n"
        "\n"
        "段落 主():\n"
        '  设 体 为 "{\\"节点ID\\": \\"N1A2B3C4\\"}"\n'
        "  打印(长(体))\n"
        "  打印(字节长度(字符串转字节(体)))\n"
        "\n"
        "主()。\n"
    )
    rc, 输出 = _编译并跑(源, str(tmp_path))
    assert rc == 0, 输出
    字符数, 字节数 = [int(x) for x in 输出.split()]
    assert 字符数 < 字节数, "字符数 %d 不小于字节数 %d：用例前提不成立" % (字符数, 字节数)
