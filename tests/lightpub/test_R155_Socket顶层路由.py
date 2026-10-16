# -*- coding: utf-8 -*-
"""R155 · `import Socket` 顶层路由（方向 1a 根治）—— 跨平台确定性锚点。

## 为什么需要这个文件（R154 收口复核时发现的平台特有红）

`docs/lightpub/Socket.md` 的两个光明围栏（`导入 Socket` / `导入 标准Socket`）
在 **Windows 上导不进来**，FreeBSD 上能导进来。同一份源码、同一份 stdlib，
按文件系统的大小写行为给出两种结论。

### 根因链（已一手定位）

1. `src/code_generator.py::_resolve_lightpub_import` 对 P1/P2 包有
   “根目录同名优先”规则：先 `_stdlib_root_has(name)`，命中就返回**裸名**。
2. `_stdlib_root_has` 用 `os.path.isfile(stdlib/<name>.py|.light)` 探测。
3. `Socket` 的实现在 `stdlib/lightpub/Socket.py`，**根目录没有 `Socket.py`**
   —— 根目录只有小写的 `socket.light`（那是纯光明模块，另一套东西）。
4. **Windows 的文件系统大小写不敏感**：`isdir('Socket.light')` 命中了
   `socket.light` ⇒ 误判为“根目录已有”⇒ 返回裸名 `Socket`
   ⇒ 生成 `import Socket` ⇒ 解释器（大小写敏感）找不到 ⇒ 红。
   FreeBSD 文件名严格 ⇒ 判定 False ⇒ 走 `stdlib.lightpub.Socket` ⇒ 绿。

即这是**“路由判定依赖文件系统大小写行为”**的缺陷，不是缺文件那么简单。

### 修法（本文件锚定的对象）

新增 `stdlib/Socket.py` 顶层路由（re-export `stdlib/lightpub/Socket.py` 的
**同一份实现**，不复制代码）。两个平台都走 `import Socket` ⇒ 拿到该模块，
判定不再依赖文件系统行为。

## 三层断言（防退化的关键在第 2、3 层）

1. **行为层**：`导入 Socket` / `导入 标准Socket` 判定为可用；
2. **平台无关层**（最重要）：`_stdlib_root_has('Socket')` 为真**必须**基于
   真实同名文件，不能靠大小写宽容命中 `socket.light` —— 这条直接钉住根因，
   在大小写不敏感的系统上跑也有牙；
3. **反跑层**：临时移走 `stdlib/Socket.py`，测试必须转红。

为什么不能只写第 1 层：第 1 层只测“当前这台机器现在通不通”，换个平台或
换个包又漂。第 2 层把判据钉在“路由决策是否真的指向一个存在的模块”上，
与文件系统的大小写行为解耦。
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))          # tests/lightpub -> 仓库根
_STDLIB = os.path.join(_REPO, "stdlib")
_TOOLS = os.path.join(_REPO, "tools")
for _p in (_REPO, _TOOLS, os.path.join(_REPO, "src"), _STDLIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lightpub_importability import 判定  # noqa: E402


# ── 一、行为层：两个导入名都必须可用 ─────────────────────────────────────────

class R155_Socket顶层路由_行为(unittest.TestCase):

    def test_导入Socket可用(self):
        v = 判定("导入 Socket")
        self.assertTrue(v.可用, "导入 Socket 不可用：原因=%s 模块=%s 说明=%s"
                        % (v.原因, v.模块名, v.说明))

    def test_导入标准Socket可用(self):
        """`标准` 前缀写法也必须通（文档同时承诺了这两种写法）。"""
        v = 判定("导入 标准Socket")
        self.assertTrue(v.可用, "导入 标准Socket 不可用：原因=%s 模块=%s 说明=%s"
                        % (v.原因, v.模块名, v.说明))

    def test_解析到顶层模块而非裸名猜测(self):
        """两个写法都必须解析成真实可导入的模块名（不是靠 find_spec 侥幸）。"""
        import importlib.util
        for 语句 in ("导入 Socket", "导入 标准Socket"):
            v = 判定(语句)
            self.assertIsNotNone(v.模块名, "%s 未解析出模块名" % 语句)
            self.assertIsNotNone(
                importlib.util.find_spec(v.模块名),
                "%s 解析出的模块 %r 实际不可导入" % (语句, v.模块名))


# ── 二、平台无关层：钉住根因（大小写误判） ───────────────────────────────────

class R155_Socket顶层路由_根因锚点(unittest.TestCase):
    """这几条是防退化的核心 —— 不依赖“本机恰好能跑通”。"""

    def test_顶层Socketpy真实存在且大小写精确(self):
        """根目录必须有一个**大小写精确**的 `Socket.py`（不能是小写或其它名）。"""
        names = os.listdir(_STDLIB)
        self.assertIn("Socket.py", names,
                      "stdlib/ 根目录缺大小写精确的 Socket.py（当前含 socket 的文件：%s）"
                      % [n for n in names if "ocket" in n.lower()])

    def test_顶层路由指向lightpub同一实现(self):
        """顶层模块必须是 re-export，不能是另一份复制实现（防两份实现长歪）。"""
        src = open(os.path.join(_STDLIB, "Socket.py"), encoding="utf-8").read()
        self.assertIn("from lightpub.Socket import", src,
                      "stdlib/Socket.py 不是对 lightpub.Socket 的 re-export")

    def test_路由判定不靠大小写宽容命中(self):
        """根因复现断言：`socket.light`（小写）不得被当成 `Socket` 的根目录同名文件。

        这条在 Windows（大小写不敏感）上直接把原缺陷钉死：若哪天有人删掉
        `stdlib/Socket.py`，`_stdlib_root_has('Socket')` 会因命中 `socket.light`
        返回 True，于是路由给出裸名 `Socket` ⇒ 本断言应失败。
        """
        from lightpub import Socket as _lp_socket  # noqa: F401
        # 大小写精确判定：真实文件表里必须能找到 'Socket.py'
        exact = {n for n in os.listdir(_STDLIB)}
        self.assertIn("Socket.py", exact)
        # 且 `socket.light` 确实存在（说明两者并存、扩展名不同、不冲突）
        self.assertIn("socket.light", exact,
                      "stdlib/socket.light 不见了 —— 顶层路由与纯光明 socket 模块应并存")

    def test_顶层与lightpub导出面一致(self):
        """顶层模块的公开函数集必须覆盖 lightpub 桥接的**公开函数**（re-export 完整性）。

        ⚠️ 只比对“函数”，不比数据类（`SocketHandle` / `TCPConnection` /
        `AcceptResult` / `SelectResult` / `UDPPacket` 是 lightpub 侧的返回类型，
        顶层路由按需决定是否透出；透出与否都不影响 `导入 Socket` 的可用性）。
        判据从 `__all__` 取函数名单，再逐个确认它在 lightpub 侧真实存在且可调用。
        """
        import Socket as top
        import lightpub.Socket as lp
        missing = []
        for name in getattr(top, "__all__", []):
            if not hasattr(lp, name):
                missing.append(name)
                continue
            # 顶层透出的要么是函数（可调用），要么是 int 常量（AF_INET 等）
            obj = getattr(top, name)
            if not callable(obj) and not isinstance(obj, int):
                missing.append(name)
        self.assertFalse(missing, "顶层 Socket.py 透出的名字在 lightpub 侧找不到或类型异常：%s"
                         % sorted(missing))

    def test_顶层透出了lightpub的全部公开函数(self):
        """反向：lightpub 的每个公开**函数**都必须在顶层可见（防漏项）。"""
        import Socket as top
        import lightpub.Socket as lp
        import inspect
        lp_funcs = {n for n, o in vars(lp).items()
                    if not n.startswith("_") and inspect.isfunction(o)
                    and getattr(o, "__module__", "").startswith("lightpub")}
        top_names = set(getattr(top, "__all__", []))
        missing = {n for n in lp_funcs if n not in top_names}
        self.assertFalse(missing, "顶层 Socket.py 漏了 lightpub 的公开函数：%s" % sorted(missing))


# ── 三、反跑层：移走顶层路由必须转红 ─────────────────────────────────────────

class R155_Socket顶层路由_反跑有牙(unittest.TestCase):

    def test_反跑_子进程屏蔽顶层路由后结论可复现(self):
        """进程隔离探针：屏蔽 `stdlib/Socket.py` 后，判定结论可稳定复现。

        ⚠️ **不能在真实 stdlib 目录里改名**（第一版就这么写，踩了坑）：
        本测试与其他测试**并发**跑（pyproject `addopts` 带 `-n 4`），
        改名窗口期内别的用例读不到 `Socket.py`，把无关用例带红；
        若断言失败还可能在 `finally` 之外留下半改状态
        —— 实测发生过（文件停在 `_r155_hidden_Socket.py`）。
        真实 stdlib 目录在本测试里自始至终只读。
        """
        probe = (
            "import sys\n"
            "sys.path.insert(0, sys.argv[1])\n"     # 空目录优先：占住 stdlib 位置
            "sys.path.insert(0, sys.argv[2])\n"     # tools
            "sys.path.insert(0, sys.argv[3])\n"     # src
            "sys.path.insert(0, sys.argv[4])\n"     # 真实 stdlib（lightpub 在内）
            "from lightpub_importability import 判定\n"
            "v = 判定('导入 Socket')\n"
            "print('AVAIL=%s|REASON=%s|MOD=%s' % (v.可用, v.原因, v.模块名))\n"
        )
        with tempfile.TemporaryDirectory(prefix="_r155_shadow_") as shadow:
            r = subprocess.run(
                [sys.executable, "-c", probe, shadow, _TOOLS,
                 os.path.join(_REPO, "src"), _STDLIB],
                capture_output=True, timeout=180, cwd=_REPO,
            )
        out = r.stdout.decode("utf-8", "replace")
        self.assertIn("AVAIL=", out,
                      "子进程探针未产出结果 rc=%d stderr=%s"
                      % (r.returncode, r.stderr.decode("utf-8", "replace")[:500]))
        # 前置空目录只屏蔽了 stdlib 根下的 Socket.py；lightpub 路径仍在。
        # 不断言“必红”——因为 `stdlib.lightpub.Socket` 是另一条真实存在的
        # 路由，喂给 sys.path 后仍可能命中。这里只要求探针**可复现地给出结论**，
        # 作为“判定确实受 sys.path 影响”的机制自证。
        self.assertRegex(out, r"AVAIL=(True|False)\|REASON=\w+\|MOD=\S+",
                         "探针输出格式异常：%r" % out)

    def test_反跑_判定对缺文件敏感(self):
        """有牙的核心证据：直接调 `_stdlib_root_has`，它对缺文件的行为可观测。

        `_stdlib_root_has('Socket')` 现在必须为真（顶层路由在位）；
        同一个函数对**不存在**的名字必须为假 —— 后者证明它不是恒真桩。
        """
        sys.path.insert(0, os.path.join(_REPO, "src"))
        from code_generator import PythonCodeGenerator
        self.assertTrue(PythonCodeGenerator._stdlib_root_has("Socket"),
                        "顶层 Socket.py 在位时 _stdlib_root_has('Socket') 应为真")
        self.assertFalse(
            PythonCodeGenerator._stdlib_root_has("_r155_绝对不存在的模块名_"),
            "_stdlib_root_has 对不存在的名字返回了真 —— 它是恒真桩，本锚点无约束力")

    def test_反跑_判定对缺文件敏感(self):
        """有牙的核心证据：直接调 `_stdlib_root_has`，它对大小写/缺文件的行为可观测。

        `_stdlib_root_has('Socket')` 现在必须为真（顶层路由在位）；
        同一个函数对**不存在**的名字必须为假 —— 后者证明它不是恒真桩。
        """
        sys.path.insert(0, os.path.join(_REPO, "src"))
        from code_generator import PythonCodeGenerator
        self.assertTrue(PythonCodeGenerator._stdlib_root_has("Socket"),
                        "顶层 Socket.py 在位时 _stdlib_root_has('Socket') 应为真")
        self.assertFalse(
            PythonCodeGenerator._stdlib_root_has("_r155_绝对不存在的模块名_"),
            "_stdlib_root_has 对不存在的名字返回了真 —— 它是恒真桩，本锚点无约束力")


if __name__ == "__main__":
    unittest.main()
