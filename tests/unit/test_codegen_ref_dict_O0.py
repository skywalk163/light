# -*- coding: utf-8 -*-
"""
test_codegen_ref_dict_O0.py —— T7B 反跑：REF 参数写回 / 字典句柄 / 变参 / 负数
6 缺陷的 codegen 根因修复（对应 T5C-02/03/04/05/07 + T6A-01）。

判据（见任务 codegen-ref-T7B）：
1. 每个缺陷一个最小复现 .light 程序，显式 optimize_level=0（O0 真编译真跑）；
   修复前行为错误（见各用例 docstring 的修复前现象），修复后与 Python 语义一致。
2. 回溯递归回归：re.light 回溯 VM 深度递归依赖「形参重绑不外泄」——此前
   _collect_rebound_names 漏检 VariableDeclaration.name（查错字段，rebind 恒空），
   全部形参被登记出口写回，深度回溯中途态污染调用方（`a*a`→0 匹配、
   `[a-z]+x`→0、提取邮箱→0）；本文件钉住该回归（根因修复后均恢复正常）。
3. 定向测试：只跑本文件 + 既有原生腿套件，禁止全量。

注：T5C-07 的 .light 层防御（前置快照/先追加后写回）按任务许可保留；本文件经
公共 API 断言其对外行为在双平台正确（存在元素移除成功 / 缺失仍抛值错误 /
分组不丢元素）。
"""
import os
import subprocess
import sys
import tempfile

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO, "src"))


def _编译并运行(code, optimize_level=0):
    """原生腿 O0 编译并运行，返回 (rc, stdout行列表, stderr)。"""
    from llvm.compiler import compile_light_typed
    with tempfile.TemporaryDirectory(prefix="_native_T7B_") as d:
        src = os.path.join(d, "主.light")
        with open(src, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        exe = compile_light_typed(src, os.path.join(d, "产物"),
                                  optimize_level=optimize_level)
        r = subprocess.run([exe], capture_output=True, timeout=180)
        out = r.stdout.decode("utf-8", errors="replace").replace("\r", "").strip()
        err = r.stderr.decode("utf-8", errors="replace")
        return r.returncode, out.split("\n") if out else [], err


def test_T5C02_REF参数追加写回_O0():
    """修复前：函数内对参数列表调 追加 不生效（浅拷贝壳 + 扩容重绑未写回），
    唯一元素(列表(1,2,1,3,2)) 曾得 0 元素。修复后：追加对实参可见。"""
    code = (
        "段落 加元素 接收 容器:\n"
        "  追加(容器, 99)\n"
        "  返回 空\n"
        "\n"
        "段落 主:\n"
        "  设 甲 为 列表(1, 2)\n"
        "  设 空值 为 加元素(甲)\n"
        "  输出(\"LEN=\" 加上 转文本(长(甲)))\n"
        "  输出(\"ITEM2=\" 加上 转文本(甲[2]))\n"
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, "O0 崩溃 rc=%d err=%s" % (rc, err[:400])
    assert out == ["LEN=3", "ITEM2=99"], "实际=%r" % (out,)


def test_T5C03_REF索引赋值_O0():
    """修复前：设 池[0] 为 池[2] 对函数参数不生效且把元素变空（曾得 3,空,空）。
    修复后：索引赋值走类型分派（列表→dv_list_set），REF 实参看到变更。"""
    code = (
        "段落 改首 接收 池:\n"
        "  设 池[0] 为 池[2]\n"
        "  返回 空\n"
        "\n"
        "段落 主:\n"
        "  设 池 为 列表(1, 2, 3)\n"
        "  设 空值 为 改首(池)\n"
        "  输出(\"LEN=\" 加上 转文本(长(池)))\n"
        "  输出(\"A=\" 加上 转文本(池[0]) 加上 \",B=\" 加上 转文本(池[1])\n"
        "        加上 \",C=\" 加上 转文本(池[2]))\n"
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, "O0 崩溃 rc=%d err=%s" % (rc, err[:400])
    assert out == ["LEN=3", "A=3,B=2,C=3"], "实际=%r" % (out,)


def test_T5C04_字典新增键REF写回_O0():
    """修复前：函数内 字典设置(缓存, \"新键\", 42) 对新增键无效（主内读回空）；
    对已有键更新有效。修复后：新增键经 REF 参数写回调用方。"""
    code = (
        "段落 加键 接收 缓存:\n"
        "  字典设置(缓存, \"新键\", 42)\n"
        "  字典设置(缓存, \"旧键\", 7)\n"
        "  返回 空\n"
        "\n"
        "段落 主:\n"
        "  设 缓存 为 {}\n"
        "  字典设置(缓存, \"旧键\", 1)\n"
        "  设 空值 为 加键(缓存)\n"
        "  输出(\"NEW=\" 加上 转文本(字典获取(缓存, \"新键\", 0)))\n"
        "  输出(\"OLD=\" 加上 转文本(字典获取(缓存, \"旧键\", 0)))\n"
        "  输出(\"LEN=\" 加上 转文本(长(字典键列表(缓存))))\n"
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, "O0 崩溃 rc=%d err=%s" % (rc, err[:400])
    assert out == ["NEW=42", "OLD=7", "LEN=2"], "实际=%r" % (out,)


def test_T5C05_变参绑定_O0():
    """修复前：合并(列表(1,2), 列表(3,4)) 把「列表们」绑成字符串 "列表们"
    （parser 产 Parameter(name='*列表们')，codegen 未识别星号）。修复后：
    *args 收集为列表，任意实参数可用。"""
    code = (
        "段落 合并 接收 *列表们:\n"
        "  设 结 为 新建列表()\n"
        "  设 k 为 0\n"
        "  当 k < 长(列表们):\n"
        "    设 甲 为 列表们[k]\n"
        "    设 i 为 0\n"
        "    当 i < 长(甲):\n"
        "      追加(结, 甲[i])\n"
        "      设 i 为 i + 1\n"
        "    设 k 为 k + 1\n"
        "  返回 结\n"
        "\n"
        "段落 主:\n"
        "  输出(\"T=\" 加上 转文本(类型(合并(列表(1, 2), 列表(3), 列表(4, 5)))))\n"
        "  设 们 为 合并(列表(1, 2), 列表(3), 列表(4, 5))\n"
        "  输出(\"LEN=\" 加上 转文本(长(们)))\n"
        "  输出(\"SUM=\" 加上 转文本(们[0]) 加上 \",\" 加上 转文本(们[4]))\n"
        "  设 单 为 合并(列表(9))\n"
        "  输出(\"ONE=\" 加上 转文本(长(单)))\n"
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, "O0 崩溃 rc=%d err=%s" % (rc, err[:400])
    assert out == ["T=list", "LEN=5", "SUM=1,5", "ONE=1"], "实际=%r" % (out,)


def test_T5C07_字典设置句柄失效_公共API_O0():
    """T5C-07：`字典设置` 使「写回前取到的旧列表句柄」失效。stdlib 层已用
    前置快照/先追加后写回防御（任务许可保留）；本用例经公共 API 钉住
    Windows 与 POSIX 双平台行为一致：存在元素移除成功、缺失仍抛值错误、
    分组不丢元素。"""
    code = (
        "从 集合 导入 创建集合 添加元素 移除元素 集合长度\n"
        "段落 主:\n"
        "  设 甲 为 创建集合()\n"
        "  设 空值 为 添加元素(甲, 1)\n"
        "  设 空值 为 添加元素(甲, 2)\n"
        "  设 空值 为 添加元素(甲, 3)\n"
        "  设 空值 为 移除元素(甲, 2)\n"
        "  输出(\"REMOVE_OK=\" 加上 转文本(集合长度(甲)))\n"
        "  设 抛了 为 \"否\"\n"
        "  尝试:\n"
        "    设 空值 为 移除元素(甲, 77)\n"
        "  捕获 错误:\n"
        "    设 抛了 为 \"是\"\n"
        "  输出(\"MISSING_THROW=\" 加上 抛了)\n"
        "  输出(\"AFTER_LEN=\" 加上 转文本(集合长度(甲)))\n"
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, "O0 崩溃 rc=%d err=%s" % (rc, err[:400])
    assert out == ["REMOVE_OK=2", "MISSING_THROW=是", "AFTER_LEN=2"], "实际=%r" % (out,)


def test_T5C07_分组_组内元素不丢失_O0():
    """分组的组内元素值维度（集合操作.分组），跨 T5C-07 句柄失效的防御保证。
    （受 T5C-06 同名段限制单独编译。）"""
    code = (
        "从 集合操作 导入 分组\n"
        "段落 主:\n"
        "  设 结 为 分组(列表(1, 1, 2))\n"
        "  设 键们 为 字典键列表(结)\n"
        "  输出(\"KEYS=\" 加上 转文本(长(键们)))\n"
        "  设 g1 为 字典获取(结, 1, 空)\n"
        "  设 g2 为 字典获取(结, 2, 空)\n"
        "  输出(\"G1=\" 加上 转文本(长(g1)))\n"
        "  输出(\"G2=\" 加上 转文本(长(g2)))\n"
        "  设 结 为 分组(列表(5, 5, 5))\n"
        "  设 g5 为 字典获取(结, 5, 空)\n"
        "  输出(\"G5=\" 加上 转文本(长(g5)))\n"
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, "O0 崩溃 rc=%d err=%s" % (rc, err[:400])
    assert out == ["KEYS=2", "G1=2", "G2=1", "G5=3"], "实际=%r" % (out,)


def test_T6A01_负数字面量_存储读取_O0():
    """修复前：codegen 一元负号（-1）被静默忽略，负数按正数存（-1→1）。
    修复后：负数字面量经 return / 列表元素 / 方法追加均原样存取。"""
    code = (
        "段落 取负:\n"
        "  返回 -1\n"
        "\n"
        "段落 主:\n"
        "  设 甲 为 新建列表()\n"
        "  甲.追加(-1)\n"
        "  输出(\"APP=\" 加上 转文本(甲[0]))\n"
        "  设 乙 为 列表(-1, -2)\n"
        "  输出(\"LIT0=\" 加上 转文本(乙[0]) 加上 \",LIT1=\" 加上 转文本(乙[1]))\n"
        "  输出(\"RET=\" 加上 转文本(取负()))\n"
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, "O0 崩溃 rc=%d err=%s" % (rc, err[:400])
    assert out == ["APP=-1", "LIT0=-1,LIT1=-2", "RET=-1"], "实际=%r" % (out,)


def test_回溯递归_参数写回不污染_O0():
    """回归：参数写回登记曾因 rebind 检测查错字段（漏 VariableDeclaration.name）
    而把所有形参写回，深度回溯递归（re.light 回溯 VM）的中途态污染调用方——
    表现为 `a*a` 对 "aaa" 0 匹配、`[a-z]+x` 对 "abx" 0 匹配、提取邮箱返回空。
    本用例钉住这些路径（根因修复后恢复正确）。"""
    code = (
        "从 正则表达式 导入 查找所有 提取邮箱\n"
        "段落 主:\n"
        "  设 m1 为 查找所有(\"a*a\", \"aaa\")\n"
        "  输出(\"RETRY=\" 加上 转文本(长(m1)))\n"
        "  设 m2 为 查找所有(\"[a-z]+x\", \"abx\")\n"
        "  输出(\"CLASS=\" 加上 转文本(长(m2)))\n"
        "  设 邮们 为 提取邮箱(\"联系 a@x.com 或 b-y@zz.cn\")\n"
        "  输出(\"MAIL=\" 加上 转文本(长(邮们)))\n"
        "  输出(邮们[0])\n"
        "  输出(邮们[1])\n"
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, "O0 崩溃 rc=%d err=%s" % (rc, err[:400])
    assert out == ["RETRY=1", "CLASS=1", "MAIL=2", "a@x.com", "b-y@zz.cn"], \
        "实际=%r" % (out,)
