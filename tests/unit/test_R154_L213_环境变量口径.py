# -*- coding: utf-8 -*-
"""R154-A：L-213 根治 —— 原生腿 `环境变量()` 与 src 腿三态对齐。

## 病灶（三条，均为 R154 起草时一手实测）

src 腿真身是 `stdlib/builtins.py:环境变量` = `os.environ.get(name, default)`，三态：

| 场景 | src 腿 | 原生腿（R154 前） |
|---|---|---|
| 缺 key，1 参 `环境变量(名)` | `None` | `""`（分歧） |
| 缺 key，2 参 `环境变量(名, 默认)` | `默认` | `""` —— **默认参数被静默丢弃** |
| key 存在 | 变量值 | 变量值（对齐） |

第三条是**连带损伤**：`stdlib/os.light:getenv(名, 默认 等于 "")` 写的是
`值 == 空` 判缺 key；原生腿缺 key 返 `""` 而非 null，`"" == 空` 为假
⇒ **非空默认值在原生腿永远丢失**（src 腿因返 None 而正常）。

## 修法（为什么必须用指针表达“缺失”）

`""` 是**合法**的环境变量值（`export X=`），与“变量根本不存在”是两种状态。
旧实现缺 key 返 `dv_strdup("")`，调用方拿到非 NULL 指针后**无从分辨**，只能一律
当空串 —— 三态必然塌成两态。故：

* C 侧 `dv_getenv` 缺 key 返 **NULL**（不再用空串冒充）；
* codegen 侧据 `icmp ne ptr out, null` 显式 br 分流：命中 → 变量值；
  缺失且有默认值 → 实参默认值；缺失且无默认值 → `_create_null_dv()`。

## 覆盖（对应任务书 §A-5 断言清单）

1. 三态对拍（两腿逐行一致）；
2. `os.light` 非空默认不再丢失（门面层真实调用）；
3. 源码级守：codegen 必须真把 `args[1]` 传下去（防回归到只传 `args[0]`）；
4. 反跑有牙：把修法改回旧行为 → 测试由绿转红。

两腿布尔/空值 repr 口径：探针一律把结果转成字符串再输出，两腿逐行对拍，
不比对 repr 本身（L-193 已另案裁定布尔 repr 差异为文档口径）。
"""
import os
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (_ROOT, os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tests.unit.test_T6B_时间系统内建_原生腿 import _find_msvc_env  # noqa: E402

_缺 = "R154A_MISSING_KEY"
_有 = "R154A_PRESENT"
_空值 = "R154A_EMPTYVAL"

# 三态 + 空值变量：一个探针覆盖三态对拍与“空值是合法值”这两件事。
# 用 `判()` 归一化，避免把 null/""/缺失在打印层的差异误当语义差异。
_三态源 = '''段落 判(值):
  如果 是空(值):
    返回 "<null_or_empty>"
  返回 值

段落 主:
  输出("miss1=" 加上 判(环境变量("R154A_MISSING_KEY")))
  输出("miss2=" 加上 判(环境变量("R154A_MISSING_KEY", "DEF")))
  输出("present=" 加上 判(环境变量("R154A_PRESENT")))
  输出("emptyval=" 加上 判(环境变量("R154A_EMPTYVAL")))
'''

_期望 = [
    "miss1=<null_or_empty>",   # 缺 key 1 参 → 判定为空（修复前 native 也是"空"，但机制不同）
    "miss2=DEF",               # 缺 key 2 参 → 默认值（修复前 native 是 "<null_or_empty>"）
    "present=present_value",
    "emptyval=<null_or_empty>",  # 存在的空值变量：合法空串，不是"缺失"
]


def _env():
    env = dict(os.environ)
    env[_有] = "present_value"
    env[_空值] = ""
    env.pop(_缺, None)
    env["PYTHONIOENCODING"] = "utf-8"
    if os.name == "nt" and not env.get("INCLUDE"):
        inc, lib = _find_msvc_env()
        if inc:
            env["INCLUDE"] = inc
        if lib:
            env["LIB"] = lib
    return env


def _src_run(src_text, timeout=180):
    with tempfile.TemporaryDirectory(prefix="_r154a_py_") as d:
        src = os.path.join(d, "main.light")
        with open(src, "w", encoding="utf-8", newline="\n") as f:
            f.write(src_text)
        proc = subprocess.run(
            [sys.executable, os.path.join("cli", "light.py"), "run", src],
            capture_output=True, timeout=timeout, env=_env(), cwd=_ROOT,
        )
    if proc.returncode != 0:
        raise AssertionError(
            "src 腿运行失败 rc=%d\nSTDERR:\n%s"
            % (proc.returncode, proc.stderr.decode("utf-8", "replace")[:2000])
        )
    return proc.stdout.decode("utf-8", "replace").replace("\r", "").strip().split("\n")


def _native_run(src_text, timeout=300):
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t6b_native_helper.py")
    try:
        with tempfile.TemporaryDirectory(prefix="_r154a_") as d:
            src = os.path.join(d, "main.light")
            with open(src, "w", encoding="utf-8", newline="\n") as f:
                f.write(src_text)
            exe = os.path.join(d, "main")
            proc = subprocess.run(
                [sys.executable, helper, src, exe],
                capture_output=True, timeout=timeout + 60, env=_env(), cwd=_ROOT,
            )
    except subprocess.TimeoutExpired:
        raise AssertionError("原生腿编译/运行超时（>%ss）" % timeout)
    if proc.returncode != 0:
        raise AssertionError(
            "原生腿编译/运行失败 rc=%d\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (proc.returncode, proc.stdout.decode("utf-8", "replace"),
               proc.stderr.decode("utf-8", "replace")[:3000])
        )
    return proc.stdout.decode("utf-8", "replace").replace("\r", "").strip().split("\n")


# ── 一、三态对拍 ──────────────────────────────────────────────────────────────

class R154_L213_三态对拍(unittest.TestCase):
    """两条腿对同一探针必须逐行一致——这是 L-213 的销账判据。"""

    def test_src腿三态(self):
        self.assertEqual(_src_run(_三态源), _期望)

    def test_原生腿三态(self):
        self.assertEqual(_native_run(_三态源), _期望)

    def test_两腿逐行一致(self):
        n, s = _native_run(_三态源), _src_run(_三态源)
        self.assertEqual(n, s, "L-213 未对齐：native=%s src=%s" % (n, s))


class R154_L213_缺key缺省到底(unittest.TestCase):
    """把“缺 key 1 参”的**返回值本体**问清楚：必须是 null，不是空串。

    上面那个探针用 `是空()` 归一化，无法区分 null 与 ""——而 L-213 的核心
    病灶恰恰是“用空串冒充缺失”。故这里补一条直接问“== 空 是否成立”的探针。
    对“存在的空值变量”则必须 **`== 空` 为假**（它是 "" 不是 null）。
    """

    _源 = '''段落 主:
  设 甲 为 环境变量("R154A_MISSING_KEY")
  如果 甲 == 空:
    输出("miss_is_null")
  否则:
    输出("miss_not_null")
  设 乙 为 环境变量("R154A_EMPTYVAL")
  如果 乙 == 空:
    输出("emptyval_is_null")
  否则:
    输出("emptyval_not_null")
'''

    _期望 = ["miss_is_null", "emptyval_not_null"]

    def test_缺key返null_空值变量不是null_src腿(self):
        self.assertEqual(_src_run(self._源), self._期望)

    def test_缺key返null_空值变量不是null_原生腿(self):
        self.assertEqual(_native_run(self._源), self._期望)

    def test_两腿一致(self):
        self.assertEqual(_native_run(self._源), _src_run(self._源))


# ── 二、os.light 门面：非空默认不再丢失（第三病灶） ──────────────────────────

class R154_L213_os门面默认值(unittest.TestCase):
    """`stdlib/os.light:getenv(名, 默认 等于 "")` —— 原生腿非空默认必须生效。

    修复前：`值 == 空` 判缺 key，而原生腿缺 key 返 "" ⇒ `"" == 空` 假
    ⇒ 直接 `返回 值`（空串），默认被静默丢弃。
    """

    _源 = '''从 os 导入 getenv

段落 判(值):
  如果 是空(值):
    返回 "<empty>"
  返回 值

段落 主:
  输出("miss1=" 加上 判(getenv("R154A_MISSING_KEY")))
  输出("miss2=" 加上 判(getenv("R154A_MISSING_KEY", "DEF")))
  输出("present=" 加上 判(getenv("R154A_PRESENT")))
  输出("emptyval=" 加上 判(getenv("R154A_EMPTYVAL")))
  输出("emptyval_def=" 加上 判(getenv("R154A_EMPTYVAL", "DEF2")))
'''

    # ⚠️ 最后一条是**刻意保留的已知边界**：`值 == 空` 判缺 key，
    # “存在但值为空串”在 src 腿（真 Python os.getenv）返回 ""，两腿同形。
    # 若把 os.light 改写成 `是空(值)`，该行会变 "DEF2" 而与 src 腿分叉 ——
    # 实测复现，故 os.light 保持 `值 == 空`（见 stdlib/os.light 处的注记）。
    _期望 = [
        "miss1=<empty>",
        "miss2=DEF",
        "present=present_value",
        "emptyval=<empty>",
        "emptyval_def=<empty>",
    ]

    def test_原生腿非空默认生效(self):
        out = _native_run(self._源)
        self.assertIn("miss2=DEF", out, "非空默认值在原生腿仍丢失：%s" % out)

    def test_src腿口径(self):
        self.assertEqual(_src_run(self._源), self._期望)

    def test_原生腿口径(self):
        self.assertEqual(_native_run(self._源), self._期望)

    def test_两腿一致(self):
        self.assertEqual(_native_run(self._源), _src_run(self._源))


# ── 三、源码级守（防回归到“只传 args[0]”） ─────────────────────────────────

class R154_L213_源码级守(unittest.TestCase):
    """行为测试在两端都能过的情况下，源码级守钉死实现不能退回旧形态。

    为什么需要它：旧实现在“缺 key + 1 参”这一格与目标态**恰好同形**
    （都是"空"），单靠行为对拍挡不住“把 args[1] 又删掉、只留 src 口径
    看起来对”的退化；而“默认值丢失”只在 2 参时暴露。
    """

    def _codegen(self):
        return open(os.path.join(_ROOT, "src", "llvm", "codegen_typed.py"),
                    encoding="utf-8").read()

    def _runtime(self):
        return open(os.path.join(_ROOT, "src", "llvm", "runtime_typed.c"),
                    encoding="utf-8").read()

    def test_codegen_环境变量分支覆盖args1(self):
        """`环境变量` 分派必须引用 args[1]（默认值真的被传下去）。"""
        src = self._codegen()
        i = src.find("if name in ('环境变量', 'getenv', 'get_env'):")
        self.assertGreater(i, 0, "codegen 找不到 环境变量 分派分支")
        # 分支体到下一条同级 `if name in (` 为止
        j = src.find("if name in ('设置环境变量'", i)
        self.assertGreater(j, i, "找不到 环境变量 分支的结束边界")
        body = src[i:j]
        self.assertIn("args[1]", body,
                      "环境变量 分支没引用 args[1] —— 默认参数又被丢掉了（L-213 回归）")
        self.assertIn("dv_getenv", body, "环境变量 分支必须调用 dv_getenv")

    def test_codegen_用指针判缺失而非串内容(self):
        """判据必须是“返回指针为 null”，不能是“返回串为空”。

        ⚠️ 不断言 `_create_null_dv`：缺失且无默认值时实现是 `call void @dv_null(ptr
        result_slot)` —— 与 `_create_null_dv()` 内部动作等价（它也是 dv_null 到一个
        新槽），只是这里必须落到**同一个合并槽**，故直接发射更直接。断言的是
        “缺省路径产出 null”这个语义，不是某个 helper 的名字。
        """
        src = self._codegen()
        i = src.find("if name in ('环境变量', 'getenv', 'get_env'):")
        j = src.find("if name in ('设置环境变量'", i)
        body = src[i:j]
        self.assertIn("icmp ne ptr", body,
                      "环境变量 分支未按返回指针判缺失（会把空值变量误判成缺失）")
        self.assertIn("call void @dv_null(ptr {result_slot})", body,
                      "缺 key 且无默认值时未把合并槽置为 null")

    def _getenv_body(self):
        """精确截取 dv_getenv 函数体（到首个 `\\n}` 为止），避免越界到 dv_str_join。"""
        rt = self._runtime()
        i = rt.find("char* dv_getenv(const char* name) {")
        self.assertGreater(i, 0, "runtime 找不到 dv_getenv 定义")
        j = rt.find("\n}", i)
        self.assertGreater(j, i, "dv_getenv 函数体未闭合")
        return rt[i:j]

    def test_runtime_缺key返NULL(self):
        """C 侧缺 key 必须返 NULL，不能继续用 dv_strdup("") 冒充。"""
        body = self._getenv_body()
        self.assertIn("NULL", body, "dv_getenv 缺 key 未用 NULL 表达缺失（L-213 回归）")
        self.assertNotIn('dv_strdup("")', body,
                         'dv_getenv 仍在用空串冒充“缺失”')


# ── 四、反跑有牙 ─────────────────────────────────────────────────────────────

class R154_L213_反跑有牙(unittest.TestCase):
    """证明测试真的能红：把 codegen 的 args[1] 支持去掉，源码级守必须失败。

    做法：把 codegen 复制到临时文件、模拟旧实现（删掉缺失分支的 args[1] 支持），
    再对**那份源码文本**施加与 test_codegen_环境变量分支覆盖args1 相同的判据。
    这不是“改测试期望消红”——原文件一个字节都没动。
    """

    def test_反跑_旧实现会被源码级守抓住(self):
        real = open(os.path.join(_ROOT, "src", "llvm", "codegen_typed.py"),
                    encoding="utf-8").read()
        i = real.find("if name in ('环境变量', 'getenv', 'get_env'):")
        j = real.find("if name in ('设置环境变量'", i)
        self.assertGreater(j, i)

        # 模拟 R154 前的旧分支：只取 args[0]，返回值直接 dv_str。
        old_branch = (
            "if name in ('环境变量', 'getenv', 'get_env'):\n"
            "            if args:\n"
            "                out = self.new_register()\n"
            "                self.emit(f'{out} = call ptr @dv_getenv(ptr null)')\n"
            "                return self._create_str_dv(out), 'dv'\n"
            "            return self._create_str_dv(self.gen_string_constant(\"\")), 'dv'\n"
            "\n        "
        )
        mutated = real[:i] + old_branch + real[j:]

        # 同一判据施加在变异体上必须失败（= 测试有牙）
        mi = mutated.find("if name in ('环境变量', 'getenv', 'get_env'):")
        mj = mutated.find("if name in ('设置环境变量'", mi)
        mbody = mutated[mi:mj]
        self.assertNotIn("args[1]", mbody,
                         "反跑装置失效：变异体竟然仍含 args[1]")
        self.assertIn("args[1]", real[i:j],
                      "真实源码里没有 args[1]，本轮修复未落地")

    def test_反跑_runtime空串冒充会被抓住(self):
        rt = open(os.path.join(_ROOT, "src", "llvm", "runtime_typed.c"),
                  encoding="utf-8").read()
        i = rt.find("char* dv_getenv(const char* name) {")
        j = rt.find("\n}", i)
        self.assertGreater(j, i)
        old = ('char* dv_getenv(const char* name) {\n'
               '    if (!name) return dv_strdup("");\n'
               '    const char* val = getenv(name);\n'
               '    return dv_strdup(val ? val : "");\n')
        mutated = rt[:i] + old + rt[j:]
        mi = mutated.find("char* dv_getenv(const char* name) {")
        mbody = mutated[mi:mutated.find("\n}", mi)]
        # 同一判据施加在旧实现上必须失败（= 测试有牙）
        self.assertNotIn("NULL", mbody, "反跑装置失效：变异体仍含 NULL")
        self.assertIn('dv_strdup("")', mbody,
                      "反跑装置没造出“空串冒充”形态")
        self.assertNotIn('dv_strdup("")',
                         rt[i:rt.find("\n}", i)],
                         "真实 runtime 仍在用空串冒充缺失")


if __name__ == "__main__":
    unittest.main()
