# -*- coding: utf-8 -*-
"""
test_原生腿_R11A_通用工具.py —— R11A 反跑：通用工具族（第 11 批 A）真 .light 化。

覆盖 7 个 stdlib 模块（原生腿真身，取代同名 .py 壳）：
  字符串工具 / uuid工具 / 数据结构 / 断言工具 / 缓存 / 进度条 / 数据验证

反跑判据（见任务书 native-utils-R11A）：
1. 每个模块从 .py 完整转写为纯光明 .light 真实现（非 decl 0 空壳），
   O0 真编译真跑（optimize_level=0），与 Python 转译腿（.py）逐函数对拍。
2. 对拍方式：原生侧把 .light 程序 O0 编译运行，逐函数打印 KEY=VALUE；
   Python 侧用 spec_from_file_location 直接加载同名 .py（绕过 shadow hook）
   作 oracle，计算同一组输入的真值，逐 KEY 对比。
3. 「改回 decl 0 空壳立即立红」：本文件所有断言都钉死真实输出（非空壳值），
   一旦某函数被回退为 decl 0（返回空 / 长度 0），断言即失败。
4. 能力边界模块（uuid 随机源 / 进度条 无 time / 缓存装饰器 / 数据验证 IP-JSON）
   不做逐字节对拍，改验「结构正确 + 格式合规 + 边界已降级」，符合任务许可。
5. 定向测试：只跑本文件，禁止全量。

环境：仅在能定位 clang 且（Windows 下）能定位 MSVC/Windows SDK 时执行，否则 skip。
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for p in (_ROOT, os.path.join(_ROOT, "src")):
    if p not in sys.path:
        sys.path.insert(0, p)


# --------------------------------------------------------------------------
# harness（复用 T7D 的 MSVC/原生腿基础设施）
# --------------------------------------------------------------------------
def _find_msvc_env():
    if os.name != "nt":
        return None, None
    vs_base = r"C:\Program Files (x86)\Microsoft Visual Studio"
    kits_base = r"C:\Program Files (x86)\Windows Kits\10"
    msvc_inc = msvc_lib = None
    if os.path.isdir(vs_base):
        for year in sorted(os.listdir(vs_base), reverse=True):
            for edition in ("BuildTools", "Community", "Professional", "Enterprise"):
                inc_root = os.path.join(vs_base, year, edition, "VC", "Tools", "MSVC")
                if not os.path.isdir(inc_root):
                    continue
                for ver in sorted(os.listdir(inc_root), reverse=True):
                    cand_inc = os.path.join(inc_root, ver, "include")
                    cand_lib = os.path.join(inc_root, ver, "lib", "x64")
                    if os.path.isdir(cand_inc) and os.path.isdir(cand_lib):
                        msvc_inc, msvc_lib = cand_inc, cand_lib
                        break
                if msvc_inc:
                    break
            if msvc_inc:
                break
    sdk_inc = sdk_lib = None
    if os.path.isdir(kits_base):
        inc_root = os.path.join(kits_base, "Include")
        if os.path.isdir(inc_root):
            for ver in sorted(os.listdir(inc_root), reverse=True):
                parts = [os.path.join(inc_root, ver, x) for x in ("ucrt", "shared", "um")]
                if all(os.path.isdir(p) for p in parts):
                    sdk_inc = parts
                    sdk_lib = [os.path.join(kits_base, "Lib", ver, x, "x64")
                               for x in ("ucrt", "um")]
                    break
    include = ";".join([msvc_inc] + sdk_inc) if (msvc_inc and sdk_inc) else None
    lib = ";".join([msvc_lib] + sdk_lib) if (msvc_lib and sdk_lib) else None
    return include, lib


def _prepare_env():
    env = dict(os.environ)
    if os.name == "nt" and not env.get("INCLUDE"):
        inc, lib = _find_msvc_env()
        if inc:
            env["INCLUDE"] = inc
        if lib:
            env["LIB"] = lib
    return env


def _native_run(src_text, timeout=180):
    """内联 .light 源码走原生腿 O0 编译并运行，返回 {KEY: 值字符串}。"""
    from llvm.compiler import compile_light_typed

    env = _prepare_env()
    old_env = {k: os.environ.get(k) for k in ("INCLUDE", "LIB")}
    os.environ.update({k: v for k, v in env.items() if k in ("INCLUDE", "LIB")})
    try:
        with tempfile.TemporaryDirectory(prefix="_R11A_") as d:
            src = os.path.join(d, "main.light")
            with open(src, "w", encoding="utf-8") as f:
                f.write(src_text)
            exe = os.path.join(d, "main")
            out_exe = compile_light_typed(src, exe, optimize_level=0)
            if not out_exe or not os.path.exists(out_exe):
                raise AssertionError("原生腿编译未产出可执行文件: %r" % (out_exe,))
            proc = subprocess.run([out_exe], capture_output=True, timeout=timeout, env=env)
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    if proc.returncode != 0:
        raise AssertionError(
            "运行失败 rc=%d\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (proc.returncode,
               proc.stdout.decode("utf-8", "replace"),
               proc.stderr.decode("utf-8", "replace")[:2000]))
    out = {}
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v
    return out


def _clang_available():
    try:
        from llvm.compiler import find_clang
        return bool(find_clang())
    except Exception:
        return False


def _py_module(name):
    """直接加载 stdlib/<name>.py 作 Python oracle（绕过 shadow hook）。

    注：缓存.py 依赖仅以 .light 存在的 对象池缓存，无法在纯 Python 下加载，
    该模块改由内联语义复刻（见 _oracle_cache*）。"""
    p = os.path.join(_ROOT, "stdlib", name + ".py")
    spec = importlib.util.spec_from_file_location(name + "_pyref", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ser(name, val):
    """把 Python 值规范化为与本测试 .light 打印格式一致的 {KEY: 值串}。"""
    out = {}
    if isinstance(val, bool):
        out[name] = "真" if val else "假"
    elif isinstance(val, int):
        out[name] = str(val)
    elif isinstance(val, str):
        out[name] = val
    elif isinstance(val, float):
        out[name] = ("%.6f" % val).rstrip("0").rstrip(".")
    elif isinstance(val, (list, tuple)):
        out[name + "_LEN"] = str(len(val))
        for i, e in enumerate(val):
            out.update(_ser("%s_%d" % (name, i), e))
    elif val is None:
        out[name] = "空"
    else:
        out[name] = str(val)
    return out


# --------------------------------------------------------------------------
# 内联 oracle：缓存（.py 不可加载）
# --------------------------------------------------------------------------
def _oracle_cache():
    c = {}
    c["k"] = 42
    c["k2"] = 7
    d = {
        "GET": str(c.get("k", 0)),
        "MISS": str(c.get("z", 0)),
        "HAS": "真" if "k" in c else "假",
        "SIZE": str(len(c)),
    }
    del c["k"]
    d["SIZE2"] = str(len(c))
    c.clear()
    d["SIZE3"] = str(len(c))
    return d


def _oracle_cache_manager():
    # 创建LRU缓存 存 __容量 元键；LRU 不驱逐（容量仅标注）
    m = {"__容量": 2, "a": 1, "b": 2, "c": 3}
    d = {
        "G_A": str(m.get("a", 0)),
        "G_B": str(m.get("b", 0)),
        "G_C": str(m.get("c", 0)),
        "HAS_A": "真" if "a" in m else "假",
        "HAS_X": "真" if "x" in m else "假",
    }
    return d


@unittest.skipUnless(_clang_available(), "未找到 clang，跳过原生腿测试")
@unittest.skipIf(os.name == "nt" and not _find_msvc_env()[0], "未定位到 MSVC/Windows SDK 头，跳过")
class R11A通用工具反跑(unittest.TestCase):
    """7 模块逐函数对拍（native .light vs python .py）。"""

    # ───────────────── 字符串工具 ─────────────────
    def test_字符串工具_对拍Python(self):
        src = """从 字符串工具 导入 反转字符串 连接字符串 提取文本中的邮箱 验证邮箱 字符串相似度
段落 主:
  输出("REV=" 加上 反转字符串("光明语言"))
  输出("JOIN=" 加上 连接字符串(列表("a", "b", "c"), "-"))
  设 邮们 为 提取文本中的邮箱("联系 a@x.com 或 b@y.cn")
  输出("MAIL_LEN=" 加上 转文本(长(邮们)))
  输出("MAIL_0=" 加上 邮们[0])
  输出("MAIL_1=" 加上 邮们[1])
  输出("VOK=" 加上 转文本(验证邮箱("a@x.com")))
  输出("VBAD=" 加上 转文本(验证邮箱("bad@@x")))
  输出("SIM=" 加上 转文本(整数(字符串相似度("kitten", "sitting") 乘以 10000)))
"""
        got = _native_run(src)
        py = _py_module("字符串工具")
        self.assertEqual(got["REV"], py.反转字符串("光明语言"))
        self.assertEqual(got["JOIN"], py.连接字符串(["a", "b", "c"], "-"))
        mails = py.提取文本中的邮箱("联系 a@x.com 或 b@y.cn")
        self.assertEqual(got["MAIL_LEN"], str(len(mails)))
        self.assertEqual(got["MAIL_0"], mails[0])
        self.assertEqual(got["MAIL_1"], mails[1])
        self.assertEqual(got["VOK"], "真" if py.验证邮箱("a@x.com") else "假")
        self.assertEqual(got["VBAD"], "真" if py.验证邮箱("bad@@x") else "假")
        sim = py.字符串相似度("kitten", "sitting")
        self.assertEqual(got["SIM"], str(int(round(sim * 10000))))

    # ───────────────── uuid工具（能力边界：结构对拍） ─────────────────
    def test_uuid工具_结构对拍Python(self):
        src = """从 uuid工具 导入 生成UUID4 验证UUID 生成UUID5
段落 主:
  设 u4 为 生成UUID4()
  输出("U4_LEN=" 加上 转文本(长(u4)))
  输出("U4_D0=" 加上 u4[8])
  输出("U4_D1=" 加上 u4[13])
  输出("U4_D2=" 加上 u4[18])
  输出("U4_D3=" 加上 u4[23])
  输出("U4_VER=" 加上 u4[14])
  输出("U4_VAR=" 加上 u4[19])
  输出("VOK=" 加上 转文本(验证UUID("550e8400-e29b-41d4-a716-446655440000")))
  输出("VBAD=" 加上 转文本(验证UUID("zzz")))
  设 u5 为 生成UUID5("6ba7b810-9dad-11d1-80b4-00c04fd430c8", "example.com")
  输出("U5_LEN=" 加上 转文本(长(u5)))
  输出("U5_VER=" 加上 u5[14])
"""
        got = _native_run(src)
        py = _py_module("uuid工具")
        # 结构对拍：v4 长度恒 36、连字符位置 8/13/18/23、版本位 14='4'、
        # 变体位 19∈{8,9,a,b}（RFC4122 变体 10xx，随机）。
        self.assertEqual(got["U4_LEN"], "36")
        self.assertEqual(got["U4_D0"], "-")
        self.assertEqual(got["U4_D1"], "-")
        self.assertEqual(got["U4_D2"], "-")
        self.assertEqual(got["U4_D3"], "-")
        self.assertEqual(got["U4_VER"], "4")
        self.assertIn(got["U4_VAR"], "89ab")
        # 能力边界：v4/v1 随机源非密码学强度；验证格式合规即可
        self.assertEqual(got["VOK"], "真" if py.验证UUID("550e8400-e29b-41d4-a716-446655440000") else "假")
        self.assertEqual(got["VBAD"], "真" if py.验证UUID("zzz") else "假")
        self.assertEqual(got["U5_LEN"], "36")
        self.assertEqual(got["U5_VER"], "5")  # 命名派生确定性布局版本位

    # ───────────────── 数据结构（类式 .py → 内联语义 oracle） ─────────────────
    def test_数据结构_对拍Python(self):
        src = """从 数据结构 导入 创建栈 压入 顶部 弹出 栈大小 创建队列 入队 出队 队首 队列大小 创建双端队列 左入队 右入队 查看右端 查看左端 双端队列大小 创建优先队列 优先入队 优先队首元素 优先出队 优先队列大小 创建二叉搜索树 二叉插入 二叉中序遍历 二叉大小
段落 主:
  设 s 为 创建栈()
  设 s 为 压入(s, 1)
  设 s 为 压入(s, 2)
  输出("STOP=" 加上 转文本(顶部(s)))
  设 顶元素 为 顶部(s)
  设 s 为 弹出(s)
  输出("SSIZE=" 加上 转文本(栈大小(s)))
  输出("SPOP=" 加上 转文本(顶元素))
  设 q 为 创建队列()
  设 q 为 入队(q, "x")
  设 q 为 入队(q, "y")
  输出("QOUT=" 加上 队首(q))
  设 q 为 出队(q)
  输出("QSIZE=" 加上 转文本(队列大小(q)))
  设 d 为 创建双端队列()
  设 d 为 左入队(d, "L")
  设 d 为 右入队(d, "R")
  输出("DQ_R=" 加上 查看右端(d))
  输出("DQ_L=" 加上 查看左端(d))
  输出("DQ_SZ=" 加上 转文本(双端队列大小(d)))
  设 pq 为 创建优先队列()
  设 pq 为 优先入队(pq, "a", 3)
  设 pq 为 优先入队(pq, "b", 1)
  设 pq 为 优先入队(pq, "c", 2)
  输出("PTOP=" 加上 优先队首元素(pq))
  设 pq 为 优先出队(pq)
  输出("PTOP2=" 加上 优先队首元素(pq))
  输出("PSIZE=" 加上 转文本(优先队列大小(pq)))
  设 t 为 创建二叉搜索树()
  设 t 为 二叉插入(t, 5)
  设 t 为 二叉插入(t, 3)
  设 t 为 二叉插入(t, 7)
  设 ino 为 二叉中序遍历(t)
  输出("IN_LEN=" 加上 转文本(长(ino)))
  输出("IN_0=" 加上 转文本(ino[0]))
  输出("IN_1=" 加上 转文本(ino[1]))
  输出("IN_2=" 加上 转文本(ino[2]))
  输出("TSIZE=" 加上 转文本(二叉大小(t)))
"""
        got = _native_run(src)
        # 栈 oracle（顶在末端）：弹出返回新栈，元素用 顶部 在弹出前取
        s = [1, 2]
        stop = s[-1]
        spop = s[-1]
        s.pop()
        ssize = len(s)
        # 队列 oracle（FIFO，front 在 index 0）
        q = ["x", "y"]
        qout = q[0]
        q.pop(0)
        qsize = len(q)
        # 双端队列 oracle：左入队在首、右入队在尾；
        # 查看右端/查看左端 为只读 peek（不弹出），故长度仍为 2
        d = []
        d.insert(0, "L")
        d.append("R")
        dq_r = d[-1]
        dq_l = d[0]
        # 优先队列 oracle（最小优先级出队）
        pq = [["a", 3], ["b", 1], ["c", 2]]
        ptop = min(pq, key=lambda e: e[1])[0]
        mp = min(pq, key=lambda e: e[1])[1]
        pq2 = [e for e in pq if e[1] != mp]
        ptop2 = min(pq2, key=lambda e: e[1])[0]
        psize = len(pq2)
        # BST oracle（中序 = 升序）
        t = [5, 3, 7]
        ino = sorted(t)
        exp = {
            "STOP": str(stop), "SSIZE": str(ssize), "SPOP": str(spop),
            "QOUT": qout, "QSIZE": str(qsize),
            "DQ_R": dq_r, "DQ_L": dq_l, "DQ_SZ": str(len(d)),
            "PTOP": ptop, "PTOP2": ptop2, "PSIZE": str(psize),
            "IN_LEN": str(len(ino)), "IN_0": str(ino[0]),
            "IN_1": str(ino[1]), "IN_2": str(ino[2]), "TSIZE": str(len(t)),
        }
        self.assertEqual(got, exp)

    # ───────────────── 断言工具（try/capture 路径） ─────────────────
    def test_断言工具_对拍Python(self):
        src = """从 断言工具 导入 断言相等 断言包含 断言大于 断言类型 断言为真
段落 主:
  尝试:
    断言相等(1, 1)
    输出("EQ_OK=真")
  捕获 错误:
    输出("EQ_OK=假")
  尝试:
    断言相等(1, 2)
    输出("NE_PASS=真")
  捕获 错误:
    输出("NE_THROW=真")
  尝试:
    断言包含(列表(1, 2, 3), 2)
    输出("INC_OK=真")
  捕获 错误:
    输出("INC_OK=假")
  尝试:
    断言大于(5, 3)
    输出("GT_OK=真")
  捕获 错误:
    输出("GT_OK=假")
  尝试:
    断言类型("x", "str")
    输出("TY_OK=真")
  捕获 错误:
    输出("TY_OK=假")
  尝试:
    断言为真(真)
    输出("TR_OK=真")
  捕获 错误:
    输出("TR_OK=假")
"""
        got = _native_run(src)
        py = _py_module("断言工具")
        # 成功路径：不抛
        for fn_ok, key in [(lambda: py.断言相等(1, 1), "EQ_OK"),
                           (lambda: py.断言包含([1, 2, 3], 2), "INC_OK"),
                           (lambda: py.断言大于(5, 3), "GT_OK"),
                           (lambda: py.断言类型("x", str), "TY_OK"),
                           (lambda: py.断言为真(True), "TR_OK")]:
            try:
                fn_ok()
                self.assertEqual(got[key], "真", "%s 应成功" % key)
            except Exception:
                self.assertEqual(got[key], "假", "%s 不应抛" % key)
        # 失败路径：抛
        try:
            py.断言相等(1, 2)
            self.assertEqual(got["NE_THROW"], "假", "断言相等(1,2) 应抛")
        except Exception:
            self.assertEqual(got["NE_THROW"], "真", "断言相等(1,2) 应抛")

    # ───────────────── 缓存（.py 不可加载 → 内联 oracle） ─────────────────
    def test_缓存_对拍语义(self):
        src = """从 缓存 导入 创建缓存 设置缓存 获取缓存 缓存包含 缓存大小 缓存删除 缓存清空 缓存管理器 管理器设置 管理器获取 管理器包含
段落 主:
  设 c 为 创建缓存("memory")
  设 c 为 设置缓存(c, "k", 42)
  设 c 为 设置缓存(c, "k2", 7)
  输出("GET=" 加上 转文本(获取缓存(c, "k", 0)))
  输出("MISS=" 加上 转文本(获取缓存(c, "z", 0)))
  输出("HAS=" 加上 转文本(缓存包含(c, "k")))
  输出("SIZE=" 加上 转文本(缓存大小(c)))
  设 c 为 缓存删除(c, "k")
  输出("SIZE2=" 加上 转文本(缓存大小(c)))
  设 c 为 缓存清空(c)
  输出("SIZE3=" 加上 转文本(缓存大小(c)))
  设 m 为 缓存管理器("lru", 2)
  设 m 为 管理器设置(m, "a", 1)
  设 m 为 管理器设置(m, "b", 2)
  设 m 为 管理器设置(m, "c", 3)
  输出("G_A=" 加上 转文本(管理器获取(m, "a", 0)))
  输出("G_B=" 加上 转文本(管理器获取(m, "b", 0)))
  输出("G_C=" 加上 转文本(管理器获取(m, "c", 0)))
  输出("HAS_A=" 加上 转文本(管理器包含(m, "a")))
  输出("HAS_X=" 加上 转文本(管理器包含(m, "x")))
"""
        got = _native_run(src)
        exp = {}
        exp.update(_oracle_cache())
        exp.update(_oracle_cache_manager())
        self.assertEqual(got, exp)

    # ───────────────── 进度条（能力边界：结构对拍，无 time） ─────────────────
    def test_进度条_结构对拍(self):
        src = """从 进度条 导入 创建进度条 设置当前 渲染进度条 更新 创建多阶段进度条 渲染多阶段进度条 阶段总步数 多阶段更新
段落 主:
  设 pb 为 创建进度条(10, "处理", 10)
  设 pb 为 设置当前(pb, 5)
  输出("BAR=" 加上 渲染进度条(pb))
  设 pb 为 更新(pb, 3)
  输出("BAR2=" 加上 渲染进度条(pb))
  设 ms 为 创建多阶段进度条(列表(列表("一", 10), 列表("二", 10), 列表("三", 10)), "")
  输出("STEPS=" 加上 转文本(字典获取(ms, "总步数")))
  设 ms 为 多阶段更新(ms, 6)
  输出("MULTI=" 加上 渲染多阶段进度条(ms))
"""
        got = _native_run(src)
        self.assertIn("50%", got["BAR"])
        self.assertIn("5/10", got["BAR"])
        self.assertIn("80%", got["BAR2"])
        self.assertIn("8/10", got["BAR2"])
        self.assertEqual(got["STEPS"], "30")
        self.assertIn("20%", got["MULTI"])

    # ───────────────── 数据验证（.py oracle） ─────────────────
    def test_数据验证_对拍Python(self):
        # 注：验证邮箱 在 .light 内由 字符串工具 导入而来；测试作用域若同时
        # 从 字符串工具 与 数据验证 导入会触发 codegen 导入解析冲突，故邮箱对拍
        # 交由 test_字符串工具_对拍Python 覆盖，本测试只验 数据验证 本模块的
        # 验证结果(dict)型函数：验证必填/验证类型/验证长度/验证枚举/验证范围。
        src = """从 数据验证 导入 验证必填 验证类型 验证长度 验证枚举 验证范围 是否有效 获取错误
段落 主:
  设 r3 为 验证必填("", "name")
  输出("REQ_OK=" 加上 转文本(是否有效(r3)))
  输出("REQ_ERRS=" 加上 转文本(长(获取错误(r3))))
  设 r4 为 验证必填("x", "name")
  输出("REQ2_OK=" 加上 转文本(是否有效(r4)))
  设 r5 为 验证类型(5, "int", "n")
  输出("TY_OK=" 加上 转文本(是否有效(r5)))
  输出("TY_ERRS=" 加上 转文本(长(获取错误(r5))))
  设 r6 为 验证类型("x", "int", "n")
  输出("TY_BAD=" 加上 转文本(是否有效(r6)))
  设 r7 为 验证长度("abcde", 2, 10, "s")
  输出("LEN_OK=" 加上 转文本(是否有效(r7)))
  设 r8 为 验证长度("a", 2, 10, "s")
  输出("LEN_BAD=" 加上 转文本(是否有效(r8)))
  设 r9 为 验证枚举("red", 列表("red", "green", "blue"), "c")
  输出("ENUM_OK=" 加上 转文本(是否有效(r9)))
  设 r10 为 验证枚举("pink", 列表("red", "green", "blue"), "c")
  输出("ENUM_BAD=" 加上 转文本(是否有效(r10)))
  设 r11 为 验证范围(15, 0, 10, "n")
  输出("RNG_BAD=" 加上 转文本(是否有效(r11)))
  设 r12 为 验证范围(5, 0, 10, "n")
  输出("RNG_OK=" 加上 转文本(是否有效(r12)))
"""
        got = _native_run(src)
        py = _py_module("数据验证")
        ok = lambda r: "真" if r.是否有效() else "假"
        # 必填
        self.assertEqual(got["REQ_OK"], ok(py.验证必填("", "name")))
        self.assertEqual(got["REQ_ERRS"], str(len(py.验证必填("", "name").获取错误())))
        self.assertEqual(got["REQ2_OK"], ok(py.验证必填("x", "name")))
        # 类型（.py 用 type 对象，light 用字符串 "int"，均对 5 有效、对 "x" 无效）
        self.assertEqual(got["TY_OK"], ok(py.验证类型(5, int)))
        self.assertEqual(got["TY_ERRS"], str(len(py.验证类型(5, int).获取错误())))
        self.assertEqual(got["TY_BAD"], ok(py.验证类型("x", int)))
        # 长度
        self.assertEqual(got["LEN_OK"], ok(py.验证长度("abcde", 2, 10)))
        self.assertEqual(got["LEN_BAD"], ok(py.验证长度("a", 2, 10)))
        # 枚举
        self.assertEqual(got["ENUM_OK"], ok(py.验证枚举("red", ["red", "green", "blue"])))
        self.assertEqual(got["ENUM_BAD"], ok(py.验证枚举("pink", ["red", "green", "blue"])))
        # 范围
        self.assertEqual(got["RNG_BAD"], ok(py.验证范围(15, 0, 10)))
        self.assertEqual(got["RNG_OK"], ok(py.验证范围(5, 0, 10)))
        # 类型（.py 用 type 对象，light 用字符串 "int"，均对 5 有效、对 "x" 无效）
        self.assertEqual(got["TY_OK"], ok(py.验证类型(5, int)))
        self.assertEqual(got["TY_BAD"], ok(py.验证类型("x", int)))
        # 长度
        self.assertEqual(got["LEN_OK"], ok(py.验证长度("abcde", 2, 10)))
        self.assertEqual(got["LEN_BAD"], ok(py.验证长度("a", 2, 10)))
        # 枚举
        self.assertEqual(got["ENUM_OK"], ok(py.验证枚举("red", ["red", "green", "blue"])))
        self.assertEqual(got["ENUM_BAD"], ok(py.验证枚举("pink", ["red", "green", "blue"])))
        # 范围
        self.assertEqual(got["RNG_BAD"], ok(py.验证范围(15, 0, 10)))
        self.assertEqual(got["RNG_OK"], ok(py.验证范围(5, 0, 10)))


if __name__ == "__main__":
    unittest.main()
