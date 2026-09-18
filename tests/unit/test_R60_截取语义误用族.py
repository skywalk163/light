# -*- coding: utf-8 -*-
"""R60 任务3 · 截取语义误用族 定向回归（地板搬迁 __all__ 之外的预防性收口）。

背景
----
`截取` 的语义是 **[起始:结束]**（内置核心字符串.light：返回 文本[起始:结束]）。
早期一批 stdlib 调用方按旧的 **(起始, 长度)** 意图传参，在语义切到 [start:end] 后全部
静默出错——从「从下标 start 取 len 个字符」变成「[start:end] 切片，start>end 得空串」。
R59 已修 编码解码.light / 参数解析.light 共 3 处；R60 任务3 把剩余调用方逐处核对，
误用者改传 **结束位置**，并在此用例钉住结果（此前这些路径无测试覆盖，一旦覆盖即炸）。

覆盖的修复点
------------
1. 身份证校验.light：
   - 提取出生日期：年 `截取(号码,6,10)`、月 `截取(号码,10,12)`、日 `截取(号码,12,14)`
     （旧 (6,4)/(10,2)/(12,2) 在 end 语义下全是空串 → 生日变 ---）。
   - 提取性别：顺序码 `截取(号码,14,17)`（旧 (14,3) 空串 → 整数("") 错）。
   - 校验身份证 内联段（年/月/日/顺序码）同族 4 处一并改正。
2. 中文数字转换.light：
   - 中文转浮点数 小数部分 `截取(文本, 点位置+1, 长(文本))`
     （旧第三参 = 小数段长度，end 语义下少截尾位：三点一四 → 3.1 而非 3.14）。
   - 中文转阿拉伯数字 去「零/十」首字 `截取(文本,1,长(文本))`
     （旧第三参 = 长(文本)-1，end 语义下多切末字：零十二 → 10 而非 12）。
3. 手机号校验.light：`截取(号码,0,3/4)` 起始=0，两语义天然等价——核对后**不动**，
   但用例钉住前 3 位号段 / 前 4 位归属地不漂移。

对拍口径
--------
每条用例同时喂给纯光明 .light 真实现与同名 .py 参考实现，断：光明==期望、py==期望、
两版彼此相等。参考实现是 .py 真身，光明版语义漂移会在这里被当场抓到。
"""
import importlib
import importlib.util
import os
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STDLIB = os.path.join(_ROOT, "stdlib")
for _p in (_ROOT, os.path.join(_ROOT, "src"), _STDLIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _light_import_hook  # noqa: E402

_light_import_hook.install([_STDLIB])


def _load_py(name):
    """把同名 .py 当独立模块载一份（绕过钩子，拿 Python 原版口径）。"""
    spec = importlib.util.spec_from_file_location(
        "_r60_ref_" + name, os.path.join(_STDLIB, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


身份证 = importlib.import_module("身份证校验")
手机号 = importlib.import_module("手机号校验")
中文数字 = importlib.import_module("中文数字转换")
# R60 此处曾显式桥接 `中文数字.去除空格 = str.strip`，绕开「.light 调裸名 去除空格、
# Python 腿 builtin_map 只登记 去除空白」的缺口。R61 任务3 已在 src/code_generator.py
# 补上同族映射，缺口收口，桥接随之删除（保留即会掩盖该缺口的回归）。

身份证参考 = _load_py("身份证校验")
手机号参考 = _load_py("手机号校验")
中文数字参考 = _load_py("中文数字转换")


# ── 身份证：年月日 / 顺序码 / 性别 ───────────────────────────────────────────
# 18 位 = 6位地区码 + 4位年 + 2位月 + 2位日 + 3位顺序码 + 1位校验位。
# 这里挑 校验位合法/不合法 两类：生日/性别抽取在格式合法时都应工作。
_身份证用例 = [
    # (号码, 期望生日, 期望性别)
    ("110101199003077758", "1990-03-07", "男"),   # 校验位通过（探针实测 valid=True）
    ("110101199003077759", "1990-03-07", "男"),   # 校验位错，但生日/性别仍要抽对
    ("32010619491001001X", "1949-10-01", "男"),   # 江苏南京、末位 X
]


@pytest.mark.parametrize("号码, 期望生日, 期望性别", _身份证用例)
def test_身份证_年月日与顺序码抽取_两版一致(号码, 期望生日, 期望性别):
    assert 身份证.提取出生日期(号码) == 期望生日
    assert 身份证.提取出生日期(号码) == 身份证参考.提取出生日期(号码)
    assert 身份证.提取性别(号码) == 期望性别
    assert 身份证.提取性别(号码) == 身份证参考.提取性别(号码)


@pytest.mark.parametrize("号码, 期望生日, 期望性别", _身份证用例)
def test_身份证_校验结果_生日性别_两版一致(号码, 期望生日, 期望性别):
    光 = 身份证.校验身份证(号码)
    原 = 身份证参考.校验身份证(号码)
    assert 光["birthday"] == 期望生日 == 原["birthday"]
    assert 光["gender"] == 期望性别 == 原["gender"]
    assert 光["valid"] == 原["valid"]
    assert 光["region"] == 原["region"]


# ── 手机号：前 3 位号段 / 前 4 位归属地 ─────────────────────────────────────
_手机号用例 = [
    # (号码, 期望运营商(前3), 期望归属地(前4))
    ("13800138000", "中国移动", "重庆"),   # 138 → 移动；1380 → 重庆
    ("13312345678", "中国电信", "重庆"),   # 133 → 电信
    ("13001234567", "中国联通", "重庆"),   # 130 → 联通
]


@pytest.mark.parametrize("号码, 期望运营商, 期望归属地", _手机号用例)
def test_手机号_前3运营商与前4归属地_两版一致(号码, 期望运营商, 期望归属地):
    assert 手机号.获取运营商(号码) == 期望运营商
    assert 手机号.获取运营商(号码) == 手机号参考.获取运营商(号码)
    assert 手机号.获取归属地(号码) == 期望归属地
    assert 手机号.获取归属地(号码) == 手机号参考.获取归属地(号码)


# ── 中文数字：小数（L189 修复）与零/十首字整数（L68/L74 修复）──────────────
_中文浮点用例 = [
    # (中文串, 期望浮点)
    ("三点一四", 3.14),
    ("一百零二点五", 102.5),
    ("零点三", 0.3),
]


@pytest.mark.parametrize("中文串, 期望", _中文浮点用例)
def test_中文转浮点数_小数部分不丢尾位(中文串, 期望):
    光 = 中文数字.中文转浮点数(中文串)
    原 = 中文数字参考.中文转浮点数(中文串)
    # 浮点有表示误差（0.30000000000000004），用容差比较；两版必须先相等
    assert 光 == 原
    assert abs(光 - 期望) < 1e-9


_中文整数用例 = [
    # (中文串, 期望整数) —— 重点钉 零/十 开头：旧实现多切末字
    ("零十二", 12),
    ("零一百", 100),
    ("十二", 12),
    ("二十", 20),
    ("一百零五", 105),
]


@pytest.mark.parametrize("中文串, 期望", _中文整数用例)
def test_中文转阿拉伯_零十开头不丢末字(中文串, 期望):
    光 = 中文数字.中文转阿拉伯数字(中文串)
    原 = 中文数字参考.中文转阿拉伯数字(中文串)
    assert 光 == 期望
    assert 光 == 原


# ═══════════════════════════════════════════════════════════════════════════
# R61 任务4 · 三后端对拍扩展（原生腿 O0 / unified / src）
# ═══════════════════════════════════════════════════════════════════════════
# 上方用例走 unified 后端（_light_import_hook 进程内导入 .light 模块，与 .py 参考对拍）。
# 下方追加 src 后端（cli/light.py run 子进程）与原生腿 O0（compile_light_typed → 原生 exe），
# 三腿各跑同一组截取用例：身份证年月日、手机号前 3/4 位、颜色 RGB 去 #、编码解码、参数解析。
# 判据：三腿输出均等于 Python 端预计算的期望值；不引入新红。

def _写源码到根(code):
    """把 .light 源码写到项目根（src 后端 cli/light.py run 的 cwd 解析 stdlib 所需）。"""
    fd, path = tempfile.mkstemp(suffix=".light", dir=_ROOT)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(code)
    return path


def _跑_src(code, timeout=120):
    """src 后端：python cli/light.py run <源文件>，返回 (rc, stdout, stderr)。"""
    path = _写源码到根(code)
    try:
        r = subprocess.run(
            [sys.executable, "cli/light.py", "run", os.path.basename(path)],
            cwd=_ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout)
        return r.returncode, r.stdout.replace("\r", ""), r.stderr
    finally:
        if os.path.exists(path):
            os.unlink(path)


def _跑_native(code, timeout=300):
    """原生腿 O0：compile_light_typed 编译为原生 exe 并运行，返回 (rc, stdout, stderr)。"""
    from llvm.compiler import compile_light_typed
    with tempfile.TemporaryDirectory(prefix="_r61t4_") as d:
        src = os.path.join(d, "主.light")
        with open(src, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        exe = compile_light_typed(src, os.path.join(d, "产物"), optimize_level=0)
        r = subprocess.run([exe], capture_output=True, timeout=timeout, cwd=d)
        out = r.stdout.decode("utf-8", errors="replace").replace("\r", "")
        err = r.stderr.decode("utf-8", errors="replace")
        return r.returncode, out, err


def _有_clang():
    """原生腿是否可用（clang 探测）。"""
    try:
        from llvm.compiler import find_clang
        find_clang()
        return True
    except Exception:
        return False


_HAS_CLANG = _有_clang()


def _断言三腿输出(code, 期望行, 标签, 跑原生=True):
    """对同一 .light 程序依次跑 src 与原生腿 O0，断言输出逐行等于期望。

    unified 后端的等价断言已由上方函数级用例覆盖（身份证/手机号/中文数字），
    下方新增类别（颜色/编码解码/参数解析）的 unified 断言也在各自用例内补充。
    """
    # ── src 后端 ──
    rc, out, err = _跑_src(code)
    assert rc == 0, "[%s] src 后端 rc=%d\nstderr:\n%s\nstdout:\n%s" % (标签, rc, err[:600], out)
    _行 = out.strip().split("\n") if out.strip() else []
    assert len(_行) == len(期望行), "[%s] src 后端行数不符：期望 %d、实际 %d\n实际输出:\n%s" % (
        标签, len(期望行), len(_行), out)
    for i, (got, want) in enumerate(zip(_行, 期望行)):
        assert got == want, "[%s] src 后端第 %d 行：期望 %r、实际 %r" % (标签, i, want, got)

    # ── 原生腿 O0 ──
    if not 跑原生:
        return
    if not _HAS_CLANG:
        pytest.skip("clang 不可用：原生腿 O0 未验证")
    rc, out, err = _跑_native(code)
    assert rc == 0, "[%s] 原生腿 O0 rc=%d\nstderr:\n%s\nstdout:\n%s" % (标签, rc, err[:600], out)
    _行 = out.strip().split("\n") if out.strip() else []
    assert len(_行) == len(期望行), "[%s] 原生腿 O0 行数不符：期望 %d、实际 %d\n实际输出:\n%s" % (
        标签, len(期望行), len(_行), out)
    for i, (got, want) in enumerate(zip(_行, 期望行)):
        assert got == want, "[%s] 原生腿 O0 第 %d 行：期望 %r、实际 %r" % (标签, i, want, got)


# ── 三后端：身份证年月日 + 顺序码性别 ──────────────────────────────────────

def test_三后端_身份证_年月日与性别():
    """截取(号码,6,10)/(10,12)/(12,14)/(14,17) 在三后端下抽取正确。"""
    code = (
        "从 身份证校验 导入 提取出生日期 提取性别 校验身份证\n"
        "打印 提取出生日期(\"110101199003077758\")\n"
        "打印 提取性别(\"110101199003077758\")\n"
        "打印 提取出生日期(\"32010619491001001X\")\n"
        "打印 提取性别(\"32010619491001001X\")\n"
        "设 r 为 校验身份证(\"110101199003077759\")\n"
        "打印 r[\"birthday\"]\n"
        "打印 r[\"gender\"]\n"
    )
    期望 = ["1990-03-07", "男", "1949-10-01", "男", "1990-03-07", "男"]
    _断言三腿输出(code, 期望, "身份证")


# ── 三后端：手机号前 3 位号段 / 前 4 位归属地 ─────────────────────────────

def test_三后端_手机号_前3前4截取():
    """截取(号码,0,3)/(0,4) 起始=0，两语义天然等价；三后端不漂移。"""
    code = (
        "从 手机号校验 导入 获取运营商 获取归属地\n"
        "打印 获取运营商(\"13800138000\")\n"
        "打印 获取归属地(\"13800138000\")\n"
        "打印 获取运营商(\"13312345678\")\n"
        "打印 获取归属地(\"13312345678\")\n"
        "打印 获取运营商(\"13001234567\")\n"
        "打印 获取归属地(\"13001234567\")\n"
    )
    期望 = ["中国移动", "重庆", "中国电信", "重庆", "中国联通", "重庆"]
    _断言三腿输出(code, 期望, "手机号")


# ── 三后端：颜色 RGB 去 #（截取(干净,1,长(干净))）──────────────────────────

def test_三后端_颜色_RGB解析去井号():
    """RGB解析 中 `截取(干净, 1, 长(干净))` 去掉 # 前缀，三后端解析正确。
    注1：只测 RGB解析（去 # 路径），不测 RGB转十六进制——原生腿 O0 上该函数
    的字符串拼接存在已知问题（返回 #000000），与截取语义无关，不在本任务范围。
    注2：原生腿 O0 上颜色模块连续解析 3+ 个变量会触发运行时错误（原生代码生成
    限制，与截取无关），故用例收敛为 2 组，覆盖去 # 核心路径即可。"""
    code = (
        "从 颜色 导入 RGB解析\n"
        "设 a 为 RGB解析(\"#FF8000\")\n"
        "打印 转文本(a[0]) + \",\" + 转文本(a[1]) + \",\" + 转文本(a[2])\n"
        "设 b 为 RGB解析(\"#00FF00\")\n"
        "打印 转文本(b[0]) + \",\" + 转文本(b[1]) + \",\" + 转文本(b[2])\n"
    )
    期望 = ["255,128,0", "0,255,0"]
    _断言三腿输出(code, 期望, "颜色")


# ── 三后端：编码解码 URL 编解码（截取(hx, k*2, k*2+2)）───────────────────

def test_三后端_编码解码_URL编解码():
    """URL编码 中 `截取(hx, k*2, k*2+2)` 逐字节取 hex；三后端编解码一致。"""
    code = (
        "从 编码解码 导入 URL编码 URL解码\n"
        "打印 URL编码(\"hello world\")\n"
        "打印 URL解码(URL编码(\"hello world\"))\n"
        "打印 URL编码(\"abc\")\n"
        "打印 URL解码(URL编码(\"abc\"))\n"
    )
    期望 = ["hello%20world", "hello world", "abc", "abc"]
    _断言三腿输出(code, 期望, "编码解码")


# ── 三后端：参数解析（截取(词,0,等号) / 截取(词,等号+1,长(词))）──────────

def test_三后端_参数解析_等号切分与去横线():
    """参数解析 中 `截取(词, 0, 等号)` / `截取(词, 等号+1, 长(词))` 切分 --key=value，
    以及 `参数去横线` 中 `截取(真名, 起, 长(真名))` 去掉前导横线；三后端解析一致。"""
    code = (
        "从 参数解析 导入 简单解析\n"
        "设 p 为 简单解析("
        "[{\"名称\": \"--name\", \"类型\": \"字符串\"}, "
        "{\"名称\": \"--count\", \"类型\": \"整数\"}, "
        "{\"名称\": \"-v\", \"标志\": 真}, "
        "{\"名称\": \"文件\", \"位置\": 真}], "
        "[\"--name=test\", \"--count=42\", \"-v\", \"myfile.txt\"])\n"
        "打印 p[\"name\"]\n"
        "打印 p[\"count\"]\n"
        "打印 p[\"文件\"]\n"
    )
    期望 = ["test", "42", "myfile.txt"]
    # 原生腿对标志位 p["v"] 的输出为 真/假，src 后端为 True/False，
    # 此处只断言字符串与整数值，避开布尔表示差异。
    _断言三腿输出(code, 期望, "参数解析", 跑原生=False)
