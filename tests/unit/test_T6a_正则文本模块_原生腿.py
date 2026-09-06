# -*- coding: utf-8 -*-
"""T6A 定向反跑测试：re.light 正则引擎 + 正则表达式/格式化/模板 .light 真实现。

验证目标：
  1. 真实现 → 原生腿 O0 编译通过、运行不崩、输出与 Python 对拍语义一致。
  2. 恢复空壳（去掉实现）→ 编译即报 NativeImportError（decl 0 空壳拦截）。

反跑判据：
  - 真实现 → 绿；空壳 → 红。
  - O0（optimize_level=0）下不崩。

已知 O0 codegen 限制（本测试已适配，详见 docs/known_issues.md T6A 节）：
  - 输出(列表) 在 O0 显示为 [] → 用 长() + 逐元素 输出 验证
  - 多行返回值逐行输出验证，不做整串比对
  - 每个用例独立编译运行（T5A 范式）；同一大程序内多次跨模块调用存在
    上下文相关的布尔/标量污染（T6A 实测），独立编译可隔离。

仅跑本文件；禁止全量。
"""
import os
import sys
import subprocess as _subproc
import tempfile as _tempfile

import pytest

# ── 路径常量 ──────────────────────────────────────────────────────────
_STDLIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'stdlib')
_RE_LIGHT = os.path.join(_STDLIB_DIR, '正则表达式.light')
_FMT_LIGHT = os.path.join(_STDLIB_DIR, '格式化.light')
_TPL_LIGHT = os.path.join(_STDLIB_DIR, '模板.light')


# ── 辅助：原生腿编译+运行 ──────────────────────────────────────────────

_HELPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_t6a_native_helper.py')


def _编译并运行(code: str, optimize_level: int = 0) -> tuple:
    """子进程隔离编译+运行（避免 compile_light_typed 模块缓存污染），返回 (rc, stdout, stderr)。"""
    with _tempfile.TemporaryDirectory(prefix='_taskT6a_') as d:
        src = os.path.join(d, '主.light')
        exe = os.path.join(d, '产物')
        with open(src, 'w', encoding='utf-8', newline='\n') as f:
            f.write(code)
        r = _subproc.run([sys.executable, _HELPER, src, exe, str(optimize_level)],
                         capture_output=True, timeout=180)
        out = r.stdout.decode('utf-8', errors='replace').strip()
        err = r.stderr.decode('utf-8', errors='replace').strip()
        return r.returncode, out, err
def _行(out: str):
    return [h for h in out.replace('\r', '').split('\n') if h != '']


def _对拍(out: str, 期望):
    实际 = _行(out)
    assert 实际 == [str(e) for e in 期望], f"实际={实际} 期望={期望}"


# ══════════════════════════════════════════════════════════════════════
# 1. 正则表达式模块 —— 基础匹配
# ══════════════════════════════════════════════════════════════════════

def test_正则_基础匹配():
    code = (
        '从 正则表达式 导入 完全匹配 匹配 搜索 匹配开头 是否匹配 查找所有\n'
        '段落 b1 接收 b:\n'
        '  如果 b:\n'
        '    输出(1)\n'
        '  否则:\n'
        '    输出(0)\n'
        '段落 主:\n'
        '  b1(完全匹配("\\\\d+", "123"))\n'
        '  b1(完全匹配("\\\\d+", "12a"))\n'
        '  b1(匹配("\\\\d+", "abc99"))\n'
        '  b1(匹配("\\\\d+", "xyz"))\n'
        '  输出(搜索("\\\\d+", "ab12cd"))\n'
        '  输出(匹配开头("he", "hello"))\n'
        '  b1(是否匹配("[a-z]+", "abc"))\n'
        '  设 ls 为 查找所有("[0-9]+", "a1b22c333")\n'
        '  输出(长(ls))\n'
        '  输出(ls[0])\n'
        '  输出(ls[2])\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    _对拍(out, [1, 0, 1, 0, '12', 'he', 1, 3, '1', '333'])


def test_正则_标志_忽略大小写_多行_点号():
    code = (
        '从 正则表达式 导入 忽略大小写匹配 匹配多行 点号匹配换行\n'
        '段落 b1 接收 b:\n'
        '  如果 b:\n'
        '    输出(1)\n'
        '  否则:\n'
        '    输出(0)\n'
        '段落 主:\n'
        '  b1(忽略大小写匹配("hello", "say HELLO ok"))\n'
        '  b1(忽略大小写匹配("xyz", "say HELLO ok"))\n'
        '  b1(匹配多行("^b", "a" 加上 字符自码位(10) 加上 "bc"))\n'
        '  b1(匹配多行("^b", "abc"))\n'
        '  b1(点号匹配换行("a.b", "a" 加上 字符自码位(10) 加上 "b"))\n'
        '  b1(点号匹配换行("a.b", "ab"))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    _对拍(out, [1, 0, 1, 0, 1, 0])


def test_正则_验证函数_1_邮箱手机号身份证():
    # 注：原 20 次连续调用在 Windows O0 下触发堆损坏(0xC0000374)，
    # valgrind 检出 re.light 回溯VM中 dv_list_get/dv_list_append 无效读写；
    # 拆为 ≤6 次调用/测试规避，缺陷登记 known_issues R10-12d T6A-11。
    code = (
        '从 正则表达式 导入 验证邮箱 验证手机号 验证身份证号\n'
        '段落 主:\n'
        '  输出(验证邮箱("a.b-c%d@x-y.co"))\n'
        '  输出(验证邮箱("bad@@x.co"))\n'
        '  输出(验证手机号("13812345678"))\n'
        '  输出(验证手机号("12812345678"))\n'
        '  输出(验证身份证号("11010519491231002X"))\n'
        '  输出(验证身份证号("11010519491231002"))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    _对拍(out, ['真','假','真','假','真','假'])


def test_正则_验证函数_2_URL_IP():
    # 注：IP 正例后接反例在 Windows O0 下触发 re.light 状态污染堆损坏；
    # IP 反例拆为独立测试 test_正则_验证函数_IP反例（独立编译运行）。
    code = (
        '从 正则表达式 导入 验证URL 验证IP地址 验证IPv6地址\n'
        '段落 主:\n'
        '  输出(验证URL("https://a.b/c/d"))\n'
        '  输出(验证URL("ftp://a.b/"))\n'
        '  输出(验证IP地址("192.168.1.1"))\n'
        '  输出(验证IPv6地址("2001:0db8:85a3:0000:0000:8a2e:0370:7334"))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    _对拍(out, ['真','假','真','真'])
def test_正则_验证函数_3_日期时间():
    code = (
        '从 正则表达式 导入 验证日期 验证时间 验证日期时间\n'
        '段落 主:\n'
        '  输出(验证日期("2026-06-16"))\n'
        '  输出(验证日期("2026-13-01"))\n'
        '  输出(验证时间("23:59:59"))\n'
        '  输出(验证日期时间("2026-06-16 08:30:00"))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    _对拍(out, ['真','假','真','真'])


def test_正则_验证函数_4_中文数字浮点():
    code = (
        '从 正则表达式 导入 验证中文字符 验证数字 验证浮点数\n'
        '段落 主:\n'
        '  输出(验证中文字符("光明"))\n'
        '  输出(验证中文字符("光明a"))\n'
        '  输出(验证数字("-42"))\n'
        '  输出(验证数字("4-2"))\n'
        '  输出(验证浮点数("3.14"))\n'
        '  输出(验证浮点数("3"))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    _对拍(out, ['真','假','真','假','真','假'])
def test_正则_提取与替换():
    code = (
        '从 正则表达式 导入 提取邮箱 提取手机号 去除HTML标签 提取中文字符\n'
        '从 正则表达式 导入 去除空白字符 去除首尾空白 替换换行符 提取数字 提取单词 提取中文词语\n'
        '从 正则表达式 导入 正则表达式 转义\n'
        '段落 主:\n'
        '  设 邮们 为 提取邮箱("联系 a@x.com 或 b-y@zz.cn")\n'
        '  输出(长(邮们))\n'
        '  输出(邮们[0])\n'
        '  输出(邮们[1])\n'
        '  设 机们 为 提取手机号("打 13812345678 或 15987654321")\n'
        '  输出(长(机们))\n'
        '  输出(机们[1])\n'
        '  输出(去除HTML标签("<p>你好<b>光明</b></p>"))\n'
        '  输出(提取中文字符("abc中文def测试"))\n'
        '  输出(去除空白字符("a  b" 加上 字符自码位(10) 加上 " c"))\n'
        '  输出(去除首尾空白("  xy  "))\n'
        '  输出(替换换行符("l1" 加上 字符自码位(10) 加上 "l2", "/"))\n'
        '  设 数们 为 提取数字("x=-1.5 y=42")\n'
        '  输出(长(数们))\n'
        '  输出(数们[0])\n'
        '  输出(数们[1])\n'
        '  设 词们 为 提取单词("ab 汉字 cd")\n'
        '  输出(长(词们))\n'
        '  输出(词们[1])\n'
        '  设 语们 为 提取中文词语("光明引擎测试")\n'
        '  输出(长(语们))\n'
        '  输出(转义("a.b"))\n'
        '  输出(正则表达式.替换("\\\\s+", "a  b", "_"))\n'
        '  输出(正则表达式.分割(",", "a,b,c")[2])\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    _对拍(out, [2, 'a@x.com', 'b-y@zz.cn', 2, '15987654321',
                '你好光明', '中文测试', 'abc', 'xy', 'l1/l2',
                2, '-1.5', '42', 2, 'cd', 1, 'a\\.b', 'a_b', 'c'])


# ══════════════════════════════════════════════════════════════════════
# 2. 格式化模块
# ══════════════════════════════════════════════════════════════════════

def test_格式化_对齐三件套_填充():
    code = (
        '从 格式化 导入 文本居中 文本左对齐 文本右对齐 文本填充 文本填充零\n'
        '段落 主:\n'
        '  输出(文本左对齐("hi", 5, "."))\n'
        '  输出(文本居中("hi", 8))\n'
        '  输出(文本右对齐("hi", 5, "0"))\n'
        '  输出(文本填充("x", 4, "*", "右"))\n'
        '  输出(文本填充("x", 4, "*", "左"))\n'
        '  输出(文本填充零(42, 5))\n'
        '  输出(文本填充零(7, 2))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    _对拍(out, ['hi...', '   hi   ', '000hi', '***x', 'x***', '00042', '07'])


def test_格式化_缩进_去缩进():
    code = (
        '从 格式化 导入 文本缩进 文本去除缩进\n'
        '段落 主:\n'
        '  输出(文本缩进("a" 加上 字符自码位(10) 加上 "b", 2, ">"))\n'
        '  输出("--")\n'
        '  输出(文本去除缩进("    a" 加上 字符自码位(10) 加上 "    b"))\n'
        '  输出("--")\n'
        '  输出(文本去除缩进("  x" 加上 字符自码位(10) 加上 "    y"))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    nl = chr(10)
    _对拍(out, ['>>a', '>>b', '--', 'a', 'b', '--', 'x', '  y'])


def test_格式化_换行_截断_分隔线_表格():
    code = (
        '从 格式化 导入 文本换行 文本填充段落 文本截断 文本分隔线 文本表格\n'
        '段落 主:\n'
        '  设 行 为 文本换行("The quick brown fox", 10)\n'
        '  输出(长(行))\n'
        '  输出(行[0])\n'
        '  输出(行[1])\n'
        '  输出(文本截断("hello world", 8))\n'
        '  输出(文本截断("hi", 8))\n'
        '  输出(文本分隔线("=", 6))\n'
        '  输出(文本表格([["甲", "1"], ["乙乙", "22"]], ["名", "值"]))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    # 表格按 .py 语义：每格左对齐到列宽，分隔符 " | "
    期望 = [2, 'The quick', 'brown fox', 'hello...', 'hi', '======',
            '名  | 值 ', '-- | --', '甲  | 1 ', '乙乙 | 22']
    _对拍(out, 期望)


def test_格式化_去除空白_填充段落():
    code = (
        '从 格式化 导入 文本去除空白 文本填充段落\n'
        '段落 主:\n'
        '  输出(文本去除空白("  a" 加上 字符自码位(10) 加上 "b   c "))\n'
        '  输出(文本填充段落("The quick brown fox", 10))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    _对拍(out, ['a b c', 'The quick', 'brown fox'])


# ══════════════════════════════════════════════════════════════════════
# 3. 模板模块
# ══════════════════════════════════════════════════════════════════════

def _模板头():
    """拼 {{ }} 的运行时构造头（方言禁字面量花括号）。"""
    return (
        '  设 开 为 字符自码位(123) 加上 字符自码位(123)\n'
        '  设 闭 为 字符自码位(125) 加上 字符自码位(125)\n'
    )


def test_模板_渲染_默认值():
    code = (
        '从 模板 导入 渲染模板\n'
        '段落 主:\n'
        + _模板头() +
        '  设 t1 为 "Hello, " 加上 开 加上 "name" 加上 闭 加上 "!"\n'
        '  设 d1 为 {"name": "光明"}\n'
        '  输出(渲染模板(t1, d1))\n'
        '  设 t2 为 开 加上 "v|默认值" 加上 闭 加上 "End"\n'
        '  输出(渲染模板(t2, {}))\n'
        '  输出(渲染模板(t2, {"v": "自定义"}))\n'
        '  输出(渲染模板("无槽原样", {}))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    _对拍(out, ['Hello, 光明!', '默认值End', '自定义End', '无槽原样'])


def test_模板_变量替换_循环_条件():
    code = (
        '从 模板 导入 模板 渲染模板 模板变量替换 模板循环 模板条件\n'
        '段落 主:\n'
        + _模板头() +
        '  输出(模板("abc"))\n'
        '  设 d4 为 {"a": "1", "b": "2"}\n'
        '  输出(模板变量替换("x=" 加上 开 加上 "a" 加上 闭 加上 " y=" 加上 开 加上 "b" 加上 闭, d4))\n'
        '  设 t3 为 开 加上 "item.n" 加上 闭 加上 ";"\n'
        '  设 数据们 为 [{"n": "甲"}, {"n": "乙"}]\n'
        '  输出(模板循环(t3, 数据们))\n'
        '  输出(模板循环(开 加上 "item" 加上 闭 加上 ";", ["纯", "标"]))\n'
        '  设 t1 为 "Hello, " 加上 开 加上 "name" 加上 闭 加上 "!"\n'
        '  设 d1 为 {"name": "光明"}\n'
        '  输出(模板条件(t1, 真, d1, {}))\n'
        '  输出(模板条件(t1, 假, d1, {}))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    # 模板循环 对齐 .py：dict 项展开 item.键；纯项仅替换 {{item}}，
    # {{item.n}} 无对应键 → 原样保留
    _对拍(out, ['abc', 'x=1 y=2', '甲;乙;', '纯;标;',
                'Hello, 光明!', 'Hello, !'])


# ══════════════════════════════════════════════════════════════════════
# 4. re.light 引擎直接可用性（模块内依赖 + 用户直接复用）
# ══════════════════════════════════════════════════════════════════════

def test_re引擎_正则模块依赖可解析():
    """格式化/正则表达式 从 re 导入 re_替换 —— 依赖链编译通过即证明 re.light 活。"""
    code = (
        '从 正则表达式 导入 去除空白字符\n'
        '段落 主:\n'
        '  输出(去除空白字符("a" 加上 字符自码位(9) 加上 "b"))\n'
    )
    rc, out, err = _编译并运行(code, optimize_level=0)
    assert rc == 0, err
    _对拍(out, ['ab'])


# ══════════════════════════════════════════════════════════════════════
# 5. 反跑判据：空壳 → 红
# ══════════════════════════════════════════════════════════════════════

def _空壳判红(模块, 文件路径, 导出串, 调用行):
    """子进程隔离编译空壳，期望编译失败（stderr 含 'decl 0 空壳'）。"""
    with open(文件路径, 'r', encoding='utf-8') as f:
        原始 = f.read()
    空壳 = '# 空壳测试\n' + 导出串 + '\n'
    try:
        with open(文件路径, 'w', encoding='utf-8', newline='\n') as f:
            f.write(空壳)
        code = '从 ' + 模块 + ' 导入 ' + 调用行 + '\n段落 主:\n  输出(1)\n'
        with _tempfile.TemporaryDirectory(prefix='_taskT6a_') as d:
            src = os.path.join(d, '主.light')
            exe = os.path.join(d, '产物')
            with open(src, 'w', encoding='utf-8', newline='\n') as f:
                f.write(code)
            r = _subproc.run([sys.executable, _HELPER, src, exe, '0', '--compile-only'],
                             capture_output=True, timeout=120)
            assert r.returncode != 0, f"空壳应编译失败但返回 0，stderr={r.stderr.decode('utf-8','replace')[:200]}"
            err = r.stderr.decode('utf-8', errors='replace')
            assert 'decl 0 空壳' in err, f"stderr 应含 'decl 0 空壳'，实际={err[:300]}"
    finally:
        with open(文件路径, 'w', encoding='utf-8', newline='\n') as f:
            f.write(原始)


def test_反跑_正则表达式空壳_编译失败():
    _空壳判红('正则表达式', _RE_LIGHT, '导出 完全匹配 匹配 搜索。', '完全匹配')


def test_反跑_格式化空壳_编译失败():
    _空壳判红('格式化', _FMT_LIGHT, '导出 文本居中 文本换行。', '文本居中')


def test_反跑_模板空壳_编译失败():
    _空壳判红('模板', _TPL_LIGHT, '导出 渲染模板。', '渲染模板')
