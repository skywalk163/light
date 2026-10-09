# -*- coding: utf-8 -*-
"""纯光明模块 **Python 腿**运行期冒烟（R123-B3 首建）。

姊妹工具关系
------------
`tools/ci/probe_light_compile.py`（R122-C1）管**原生腿**：把 .light 送去
`compile_light_typed` 看能不能编。
本工具管**Python 腿**：把 .light 真加载起来，看**导出面齐备**、**零参调用不炸**。

为什么必须专门做这件事
----------------------
目标集合是「**NO-PY + 有魔数**」的模块（当前 39 个）：它们**没有同名 .py**，
`.light` 就是**唯一**的运行期实现 ⇒ 任何缺陷都**直接在线咬人**，
而且原生腿探针完全看不见这类缺陷（能编 ≠ 能跑）。

⚠️ 已知盲区（必须处理，别踩）
----------------------------
这 39 个里有 **7 个没有 `导出` 声明**：`JSONL` / `事件总线` / `代理工具集` /
`并发` / `度量` / `插件` / `重试`。若只按 `导出` 行取被验集合，这 7 个会**静默空转**
（"导出 0 / 缺 0 / 失败 0" 看着全绿，实际什么都没验）。
⇒ 本工具对这 7 个改用**回退口径**：取 `.light` **顶层**（零缩进）`段落`/`类` 名作为
被验集，并在输出里**显式标注**「无 `导出` 声明，按顶层定义名验」。
   ⚠️ 回退口径必须**只收零缩进定义**：`类 插件` 里的**方法**也是 `段落 加载插件(x)`，
   带缩进。若不分缩进，会把「类方法」误报成「缺导出」（R123 首跑实测踩过）。

⚠️ 第三条必须处理的坑：**与 Python 标准库同名的模块**
----------------------------------------------------
`re` / `sys` / `time` / `inspect` 这 4 个名字在 `stdlib/` 下都有「纯光明实现」，
但 `_light_import_hook.find_spec` 有**标准库保护**：`import re` 会**故意**放行给
真 CPython `re`（避免编译期 `inspect.light` → 编译器 的循环导入）。
纯光明实现只能经**别名** `_light_re` / `_light_sys` / … 到达（这是
`code_generator` 的 `_PYTHON_LEG_PURE_LIGHT_ALIAS` 设计）。
⇒ 本工具对这 4 个走**别名口径**验（`import _light_re`），并单独归入
「标准库同名（设计边界）」一节，**不**与普通模块混在一起判红。

异常分类（不自造，沿用 R122-D 口径）
-----------------------------------
  `NameError` / `AttributeError` → **红**（导出面缺失或名字解析不到，必须修）
  `TypeError`（缺参）            → **正常跳过**（零参冒烟对带参函数不适用）
  `SystemExit` / `KeyboardInterrupt` → **正常跳过**（如 `sys.exit`，零参调用即退出进程）
  `OSError` / 网络不可达          → **环境跳过**（如实列出，不计红，标注「环境相关」）
  `其它异常`                     → **黄**（如实列出，不计红：零参调用本就可能合法抛错）

退出码：0=正常跑完探测（**诊断工具，不做门禁**）；2=用法错误。

用法（在本仓 venv python 下）：
  .venv/Scripts/python.exe tools/ci/smoke_pure_light_exports.py
  ... 默认口径：扫 stdlib/（递归）里全部「有魔数且无同名 .py」的 .light。
  .venv/Scripts/python.exe tools/ci/smoke_pure_light_exports.py 内置核心判型 列表工具
  ... 只验指定模块名（可多个）。
  .venv/Scripts/python.exe tools/ci/smoke_pure_light_exports.py --timeout 120
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys

# 复用 bootstrap_rate 的魔数口径（同目录导入），不自造。
_CI_DIR = os.path.dirname(os.path.abspath(__file__))
if _CI_DIR not in sys.path:
    sys.path.insert(0, _CI_DIR)
from bootstrap_rate import _是纯光明  # noqa: E402

_DEFAULT_ROOT = os.path.dirname(os.path.dirname(_CI_DIR))
_结果前缀 = "RESULT:"

# 每模块一个子进程：全新解释器防内存累积与跨模块状态污染；stdout 只认 RESULT: 行。
_CHILD = r'''
import json, os, re, sys

def emit(payload):
    print("RESULT:" + json.dumps(payload, ensure_ascii=False))

def main():
    root, light_path, mod_name = sys.argv[1], sys.argv[2], sys.argv[3]
    stdlib = os.path.join(root, "stdlib")
    subdirs = [stdlib]
    # `stdlib/分布式/` 里的纯光明模块（主控/节点/节点核心/调度核心）必须也能被钩子找到：
    # 它们的 .light 在子目录，而钩子只按给定目录平层查找。
    for d in sorted(os.listdir(stdlib)):
        cand = os.path.join(stdlib, d)
        if os.path.isdir(cand) and d not in ("__pycache__", ".git"):
            subdirs.append(cand)
    for p in (root, os.path.join(root, "src"), stdlib) + tuple(subdirs):
        if p not in sys.path:
            sys.path.insert(0, p)

    try:
        with open(light_path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError as e:
        emit({"mod": mod_name, "fatal": "读不动 .light: %s" % e})
        return 0

    # ---- 被验集合：优先 `导出` 声明；无声明则回退到**顶层**（零缩进）`段落`/`类` 名 ----
    export_lines = re.findall(r"(?m)^\s*导出\s+(.+?)[。.]?\s*$", src)
    names = []
    for line in export_lines:
        for tok in re.split(r"[ \t、,，]+", line):
            tok = tok.strip().rstrip("。.")
            if tok:
                names.append(tok)
    fallback = not names
    if fallback:
        # ⚠️ 必须零缩进：类方法在 .light 里也是 `  段落 加载插件(x)`，带缩进时必须排除，
        #    否则会把「类方法」误报成「缺导出」。
        names = re.findall(r"(?m)^(?:段落|类)\s+(\S+?)\s*[(:]", src)
    seen = set()
    uniq = []
    for n in names:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    names = uniq

    # ---- 标准库同名：Python 腿**故意**走真标准库，纯光明实现只能经 `_light_<名>` 别名 ----
    stdlib_same = mod_name in getattr(sys, "stdlib_module_names", frozenset())
    import_name = ("_light_" + mod_name) if stdlib_same else mod_name

    try:
        import _light_import_hook
    except Exception as e:
        emit({"mod": mod_name, "fatal": "导入钩子失败: %r" % (e,)})
        return 0
    _light_import_hook.install(subdirs + [stdlib])

    # 顶层就 `运行 xxx()。` 的**入口型**模块：import 即执行主流程（读写状态文件/绑端口），
    # 不适合做 import 期冒烟。这类模块改用**静态导出面校验**（编译后看生成的 Python
    # 顶层 def/class 名），仍然把「导出面齐备」验掉，只是不跑运行期。
    entrance = re.search(r"(?m)^(?:异步\s+)?运行\s+\S+\([^)]*\)\s*[。.]?\s*$", src) is not None

    try:
        mod = __import__(import_name)
    except Exception as e:
        info = {"mod": mod_name, "exports": len(names), "fallback": fallback,
                "stdlib_same": stdlib_same, "import_name": import_name,
                "entrance": entrance, "missing": [], "ran": 0, "skipped": 0,
                "warn": [], "envskip": [], "static": None,
                "fatal": "import(%s) 失败: %s: %s" % (import_name, type(e).__name__, str(e)[:300])}
        if entrance:
            info["static"] = _静态导出面(light_path, stdlib, names)
        emit(info)
        return 0

    loader = type(getattr(mod, "__loader__", None)).__name__
    src_file = getattr(mod, "__file__", "")
    missing, ran, skipped, warn, envski = [], 0, 0, [], []
    for n in names:
        if not hasattr(mod, n):
            missing.append(n)
            continue
        obj = getattr(mod, n)
        if not callable(obj):
            continue
        try:
            obj()
            ran += 1
        except TypeError:
            skipped += 1          # 缺参：零参冒烟不适用，正常跳过
        except (SystemExit, KeyboardInterrupt):
            skipped += 1          # 如 sys.exit：零参调用即退出进程，正常跳过
        except (NameError, AttributeError) as e:
            warn.append({"call": n, "kind": type(e).__name__, "msg": str(e)[:160], "red": True})
        except OSError as e:
            envski.append({"call": n, "kind": type(e).__name__, "msg": str(e)[:160]})
        except Exception as e:
            warn.append({"call": n, "kind": type(e).__name__, "msg": str(e)[:160], "red": False})

    emit({"mod": mod_name, "exports": len(names), "fallback": fallback,
          "stdlib_same": stdlib_same, "import_name": import_name,
          "entrance": entrance, "loader": loader, "file": src_file,
          "missing": missing, "ran": ran, "skipped": skipped, "warn": warn,
          "envskip": envski, "static": None, "fatal": ""})
    return 0


def _静态导出面(light_path, stdlib, names):
    """不执行模块体，只编译后检查生成的 Python 里顶层 def/class 名是否覆盖 names。"""
    try:
        import _light_import_hook as _h
        code = _h._compile_light(light_path, stdlib)
    except Exception as e:
        return {"ok": False, "err": "%s: %s" % (type(e).__name__, str(e)[:200]), "found": [], "missing": []}
    found = re.findall(r"(?m)^def\s+(\S+?)\s*\(", code) + re.findall(r"(?m)^class\s+(\S+?)\s*[:\(]", code)
    # 再导出的名（`from X import Y` / `import X as Y`）也算导出面齐备：
    # 如 `主控`/`节点` 的 `主` 来自 `from 调度核心 import 主` + `__all__ = ['主']`。
    for m in re.finditer(r"(?m)^from\s+\S+\s+import\s+(.+?)\s*$", code):
        for tok in m.group(1).replace("(", "").replace(")", "").split(","):
            tok = tok.strip().split(" as ")[-1].strip()
            if tok and tok != "*":
                found.append(tok)
    for m in re.finditer(r"(?m)^import\s+(\S+)(?:\s+as\s+(\S+))?\s*$", code):
        found.append(m.group(2) or m.group(1))
    fset = set(found)
    miss = [n for n in names if n not in fset]
    return {"ok": True, "found": sorted(fset), "missing": miss}

sys.exit(main())
'''


def 遍历_候选(root):
    """扫 stdlib/（递归）里「有魔数 + 无同名 .py」的 .light，返回 [(模块名, 绝对路径)]。

    口径与 tools/ci/llvm_stdlib_readiness.py 的魔数判定同源（`_是纯光明`），
    与 R122-D 的「NO-PY + 魔数 = 39」逐字一致。
    """
    stdlib_dir = os.path.join(root, "stdlib")
    found = []
    for dirpath, dirnames, filenames in os.walk(stdlib_dir):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in sorted(filenames):
            if not fn.endswith(".light"):
                continue
            name = fn[:-len(".light")]
            path = os.path.join(dirpath, fn)
            if not _是纯光明(path):
                continue
            if os.path.isfile(os.path.join(dirpath, name + ".py")):
                continue  # HAS-PY：Python 腿走 .py，不属本工具范围
            found.append((name, path))
    found.sort()
    return found


def probe_one(root, name, light_path, timeout):
    """子进程里真加载一个纯光明模块并冒烟。返回 dict。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _CHILD, root, light_path, name],
            capture_output=True, timeout=timeout, env=env, cwd=root,
        )
    except subprocess.TimeoutExpired:
        return {"mod": name, "fatal": "超时(>%gs) —— 疑似 import 期挂死" % timeout,
                "exports": 0, "fallback": False, "stdlib_same": False,
                "missing": [], "ran": 0, "skipped": 0, "warn": [], "envskip": []}
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith(_结果前缀):
            try:
                return json.loads(line[len(_结果前缀):])
            except ValueError:
                break
    head = (proc.stderr.decode("utf-8", "replace").strip().splitlines() or ["<无 stderr>"])[0]
    return {"mod": name, "fatal": "子进程异常退出 rc=%d: %s" % (proc.returncode, head[:300]),
            "exports": 0, "fallback": False, "stdlib_same": False,
            "missing": [], "ran": 0, "skipped": 0, "warn": [], "envskip": []}


def main(argv=None):
    ap = argparse.ArgumentParser(description="纯光明模块 Python 腿运行期冒烟（诊断，不做门禁）")
    ap.add_argument("targets", nargs="*", metavar="模块名", help="只验指定模块名（默认全扫）")
    ap.add_argument("--root", default=_DEFAULT_ROOT, help="仓库根（默认本脚本上两级）")
    ap.add_argument("--timeout", type=float, default=120, help="单模块冒烟超时秒数（默认 120）")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)

    all_cands = 遍历_候选(root)
    if args.targets:
        want = set(args.targets)
        modules = [(n, p) for n, p in all_cands if n in want]
        if len(modules) != len(want):
            got = {n for n, _ in modules}
            print("找不到这些模块（或它们不属 NO-PY+魔数 口径）：%s"
                  % "、".join(sorted(want - got)))
            return 2
    else:
        modules = all_cands

    print("口径：stdlib/（递归）里 **有魔数 + 无同名 .py** 的 .light —— 它们的 .light 是"
          "唯一运行期实现")
    print("探测模块数：%d（Python 腿真加载；最多 2 路并发；单模块超时 %gs）"
          % (len(modules), args.timeout))
    print("")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for r in pool.map(lambda it: probe_one(root, it[0], it[1], args.timeout), modules):
            results.append(r)

    红模块, 盲区, 标准库同名, 红项, 环境项, 内部名项 = [], [], [], [], [], []
    for r in results:
        tag = "（无 `导出` 声明，按顶层定义名验）" if r.get("fallback") else ""
        if r.get("fallback"):
            盲区.append(r["mod"])
        if r.get("stdlib_same"):
            标准库同名.append(r["mod"])
            tag += "（标准库同名：Python 腿走真标准库，此处经别名 %s 验）" % r.get("import_name")
        miss = r.get("missing") or []
        warns = r.get("warn") or []
        内部名re = re.compile(r"'(?:_dv_|_clock|_sleep_sec|_strftime"
                              # R128-F 三门面（stdlib/socket.light、stdlib/selectors.light、
                              # stdlib/errno.light）经 _light_<名> 别名诊断验时，段落链
                              # 调用的 socket/poller 族内建只在原生腿 codegen_typed.py
                              # 暴露（创建socket/…/poller计数），Python 腿
                              # builtin_map 无对应名 —— 与 time.light 的 _dv_timestamp/
                              # _clock 同款「边界·原生腿内部名」：设计边界、非缺陷。
                              # （用户代码不可触发：codegen 别名白名单仅 {'re'}，
                              # _light_socket 只被本工具的诊断口径构造。）
                              r"|创建socket|连接socket|发送socket|接收socket|关闭socket"
                              r"|socket错误|socket错误码|socket_last_error|socket_last_error_code"
                              r"|创建poller|注册poller|poller_wait|销毁poller"
                              r"|poller错误|poller后端|poller计数"
                              r"|socket_create|socket_connect|socket_send|socket_recv|socket_close"
                              r"|poller_create|poller_register|poller_destroy"
                              r"|poller_last_error|poller_backend|poller_count)")
        reds = [w for w in warns if w.get("red") and not 内部名re.search(w["msg"])]
        边界项 = [w for w in warns if w.get("red") and 内部名re.search(w["msg"])]
        if r.get("fatal"):
            if r.get("entrance") and r.get("static"):
                st = r["static"]
                if st.get("ok") and not st.get("missing"):
                    print("  OK  %-14s 入口型（import 即执行）：跳过运行期，静态导出面齐备"
                          "（导出 %d）" % (r["mod"], r.get("exports", 0)))
                else:
                    print("  ERR %-14s 入口型静态导出面缺口：%s"
                          % (r["mod"], st.get("err") or "、".join(st.get("missing") or [])))
                    红模块.append(r["mod"])
                    红项.append("%s：入口型静态导出面缺口 %s"
                              % (r["mod"], st.get("err") or "、".join(st.get("missing") or [])))
                continue
            print("  ERR %-14s %s" % (r["mod"], r["fatal"]))
            红模块.append(r["mod"])
            红项.append("%s：%s" % (r["mod"], r["fatal"]))
            continue
        mark = "ERR" if (reds or miss) else "OK "
        print("  %s %-14s 导出 %d / 缺导出 %d / 运行失败 %d%s"
              % (mark, r["mod"], r.get("exports", 0), len(miss), len(reds), tag))
        if miss:
            print("        缺导出：%s" % "、".join(miss))
            红模块.append(r["mod"])
            红项.append("%s：缺导出 %s" % (r["mod"], "、".join(miss)))
        for w in reds:
            print("        %s(%s): %s" % (w["kind"], w["call"], w["msg"]))
            红项.append("%s.%s：%s: %s" % (r["mod"], w["call"], w["kind"], w["msg"]))
        for w in 边界项:
            print("        [边界·原生腿内部名] %s(%s): %s" % (w["kind"], w["call"], w["msg"]))
            内部名项.append("%s.%s" % (r["mod"], w["call"]))
        if reds:
            红模块.append(r["mod"])
        for w in warns:
            if not w.get("red"):
                print("        [黄] %s(%s): %s" % (w["kind"], w["call"], w["msg"]))
        for w in (r.get("envskip") or []):
            print("        [环境跳过] %s(%s): %s" % (w["kind"], w["call"], w["msg"]))
            环境项.append("%s.%s：%s: %s" % (r["mod"], w["call"], w["kind"], w["msg"]))

    print("")
    总导出 = sum(r.get("exports", 0) for r in results)
    总缺 = sum(len(r.get("missing") or []) for r in results)
    内部名re = re.compile(r"'(?:_dv_|_clock|_sleep_sec|_strftime)")
    总红 = sum(len([w for w in (r.get("warn") or [])
                    if w.get("red") and not 内部名re.search(w["msg"])]) for r in results)
    总黄 = sum(len([w for w in (r.get("warn") or []) if not w.get("red")]) for r in results)
    总环 = sum(len(r.get("envskip") or []) for r in results)
    总跑 = sum(r.get("ran", 0) for r in results)
    总跳 = sum(r.get("skipped", 0) for r in results)
    print("汇总：%d 模块 ｜ 导出 %d / 缺导出 %d / 运行失败 %d ｜ 零参调用成功 %d、"
          "缺参或退出类跳过 %d ｜ 环境跳过 %d ｜ 黄 %d"
          % (len(results), 总导出, 总缺, 总红, 总跑, 总跳, 总环, 总黄))
    print("红模块：%s" % ("、".join(sorted(set(红模块))) if 红模块 else "无"))
    print("⚠️ 盲区（无 `导出` 声明，按顶层定义名回退验）：%s"
          % ("、".join(盲区) if 盲区 else "（本批无）"))
    if 标准库同名:
        print("⚠️ 标准库同名（设计边界：Python 腿走真标准库，经 `_light_<名>` 别名验）：%s"
              % "、".join(标准库同名))
    if 环境项:
        print("⚠️ 环境跳过（非导出面缺陷）：%s" % "；".join(环境项))
    if 内部名项:
        print("⚠️ 边界（原生腿内部名下探到 Python 腿：`_dv_*`/`_clock`/`_sleep_sec`/`_strftime`"
              "——设计边界、非缺陷，见各文件头登记）：%s" % "、".join(内部名项))
    if 红项:
        print("")
        print("红项明细：")
        for x in 红项:
            print("  - %s" % x)
    print("")
    print("（诊断工具，不做门禁；退出码恒 0。）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
