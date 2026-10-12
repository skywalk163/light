# -*- coding: utf-8 -*-
"""
R143-B 定向用例：L-200 模板 `模板循环` 不展开嵌套 dict 键 `{{item.n}}`。

背景：src 腿 `模板循环` 只替换 `{{item}}`，不展开 `{{item.名}}` 这类点号路径；
      `.py` / oracle 会展开顶层键包（`.py` 把 `{f'{循环变量}.{k}': v}` 打包后替换），
      导致 src 腿与 oracle 分歧。

根因：`stdlib/模板.light:111` 的判型写 `如果 类型(项) == "dict"`。两腿 `类型` 语义
      不一致——src 腿 builtin_map 把 `类型` 映射为 `type()`（返回 `<class 'dict'>`），
      原生腿 codegen_typed.py:3330 走 `dv_get_type_name`（返回 `"dict"`）。于是
      `类型(项) == "dict"` 在 src 腿恒为假，字典项永远走 else 分支（单键打包），
      点号路径 `{{item.名}}` 无法替换。这不是 `模板.light` 写错——`.py` oracle
      用 isinstance 判型，与 src 腿 `类型` 返回值不同名。

修复：`模板.light` 判型改 `是字典(项)`（builtin_map 已映射 `_light_builtin.是字典`
      = isinstance(值, dict)，原生腿 `_gen_type_predicate(('dict',))` 同样 isinstance 语义，
      两腿一致）。

语义对齐口径：`.py` oracle 的 `模板循环` 只做**顶层键包替换**（`{{item.键}}`），
      不递归展开 `{{item.a.b}}`（`.py` 实测 `{{item.信息.名}}` 不替换）。本修复对齐
      该口径——不做超出 `.py` 的递归嵌套，避免制造新的跨腿分歧。

双腿对拍：同一份源码分别走 src（转译腿）与原生腿，逐条断言一致。
"""
import os
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (_ROOT, os.path.join(_ROOT, "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from tests.unit.test_T6B_时间系统内建_原生腿 import _find_msvc_env  # noqa: E402
from tests.unit.test_R131_L186L187_原生腿 import _native_raw, _clang_available  # noqa: E402

# A1：dict 项，`{{item.名}}` 点号路径展开 —— 修复前 src 腿输出原样占位符
A1 = """从 模板 导入 模板循环。
段落 主():
  设 数据们 为 [{"名": "甲", "年": 20}, {"名": "乙", "年": 30}]
  设 模板串 为 "{{item.名}}={{item.年}};"
  输出("循环=" 加上 转字符串(模板循环(模板串, 数据们)))
"""

# A2：非 dict 项（纯标量列表），走单键打包路径
A2 = """从 模板 导入 模板循环。
段落 主():
  输出("非dict=" 加上 转字符串(模板循环("[{{item}}]", ["x", "y"])))
"""

# A3：空 dict 项，点号路径无值保留占位符（.py 同语义）
A3 = """从 模板 导入 模板循环。
段落 主():
  输出("空dict=" 加上 转字符串(模板循环("[{{item.名}}]", [{}])))
"""

# A4：嵌套 dict（`.py` 不做递归展开，`{{item.信息.名}}` 保持占位符）—— 对齐 `.py` 口径
A4 = """从 模板 导入 模板循环。
段落 主():
  设 数据们 为 [{"信息": {"名": "甲"}}, {"信息": {"名": "乙"}}]
  输出("深层=" 加上 转字符串(模板循环("{{item.信息.名}}\\n", 数据们)))
"""

# A5：缺键 dict 项 —— `模板循环` 走 `模板变量替换`（非 `_展开槽`），
#     `.py` oracle 同语义：缺键保留原占位符（不落 `|默认`），两腿一致
A5 = """从 模板 导入 模板循环。
段落 主():
  设 数据们 为 [{"名": "甲"}, {"年": 30}]
  输出("默认=" 加上 转字符串(模板循环("[{{item.名|无名}}]", 数据们)))
"""


def _src_run(src_text, timeout=120):
    """以内联 .light 源码走转译腿（src 后端）运行，返回原始 stdout 文本。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        with tempfile.TemporaryDirectory(prefix="_r143_l200_") as d:
            src = os.path.join(d, "main.light")
            with open(src, "w", encoding="utf-8") as f:
                f.write(src_text)
            proc = subprocess.run(
                [sys.executable, os.path.join("cli", "light.py"), "run", src, "--backend", "src"],
                capture_output=True, timeout=timeout, env=env, cwd=_ROOT,
            )
    except subprocess.TimeoutExpired:
        raise AssertionError(f"src 腿运行超时（>{timeout}s）")
    if proc.returncode != 0:
        raise AssertionError(
            f"src 腿运行失败 rc={proc.returncode}\n"
            f"STDOUT:\n{proc.stdout.decode('utf-8', 'replace')}\n"
            f"STDERR:\n{proc.stderr.decode('utf-8', 'replace')[:2000]}"
        )
    return proc.stdout.decode("utf-8", "replace")


def _keyvals(raw):
    out = {}
    for ln in raw.splitlines():
        if "=" in ln:
            k, _, v = ln.strip().partition("=")
            out[k.strip()] = v.strip()
    return out


class R143L200模板嵌套键(unittest.TestCase):
    """L-200：src 腿 `模板循环` 展开 `{{item.键}}` 点号路径，与 `.py`/原生腿对齐。"""

    def test_A1_点号路径展开(self):
        out = _keyvals(_src_run(A1))
        self.assertEqual(out.get("循环"), "甲=20;乙=30;",
                         f"src 腿应展开 {{item.名}}/{{item.年}}: 实际={out.get('循环')!r}")

    def test_A2_非dict项走标量路径(self):
        out = _keyvals(_src_run(A2))
        self.assertEqual(out.get("非dict"), "[x][y]",
                         f"非 dict 项应替换 {{item}}，实际={out.get('非dict')!r}")

    def test_A3_空dict保留占位符(self):
        out = _keyvals(_src_run(A3))
        self.assertEqual(out.get("空dict"), "[{{item.名}}]",
                         f"空 dict 项点号路径无值应保留占位符，实际={out.get('空dict')!r}")

    def test_A4_嵌套dict不递归展开(self):
        """对齐 .py oracle 口径：`{{item.信息.名}}` 不递归展开，保持占位符。"""
        out = _keyvals(_src_run(A4))
        combined = " ".join(out.values())
        self.assertIn("{{item.信息.名}}", combined,
                      f"嵌套 dict 不应递归展开（.py 同语义），实际输出={out}")

    def test_A5_带默认值缺键保留占位符(self):
        """`.py` oracle 的 `模板循环` 走 `模板变量替换`（非 `_展开槽`），
        缺键时保留原占位符 `{{item.名|无名}}`（不落 `|默认`）。两腿对齐此语义。"""
        out = _keyvals(_src_run(A5))
        self.assertEqual(out.get("默认"), "[{{item.名|无名}}][{{item.名|无名}}]",
                         f"缺键 dict 项应保留占位符（.py 同语义），实际={out.get('默认')!r}")

    def test_双腿对拍dict项一致(self):
        """src 腿与原生腿在 dict 项点号路径上逐条一致。"""
        if not (_clang_available() and (os.name != "nt" or _find_msvc_env()[0])):
            self.skipTest("clang 或 MSVC 环境不可用")
        for name, src_text in (("A1", A1), ("A2", A2), ("A3", A3), ("A4", A4), ("A5", A5)):
            raw_s = _src_run(src_text)
            raw_n = _native_raw(src_text)
            # 统一 CRLF/LF + 去尾部空白：两腿的 `输出` 尾部换行数差异（原生腿多一个
            # 空行）属终端渲染噪声，不是语义分歧；语义断言看剥离尾部空白后的行集合。
            s = "\n".join(ln for ln in raw_s.replace("\r\n", "\n").replace("\r", "\n").splitlines() if ln.strip())
            n = "\n".join(ln for ln in raw_n.replace("\r\n", "\n").replace("\r", "\n").splitlines() if ln.strip())
            self.assertEqual(s, n, f"{name}: src 腿与原生腿输出不一致\n--- src ---\n{raw_s}\n--- native ---\n{raw_n}")


if __name__ == "__main__":
    unittest.main()