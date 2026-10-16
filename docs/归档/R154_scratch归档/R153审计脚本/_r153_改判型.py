# -*- coding: utf-8 -*-
"""R153：以 bytes 改写 .light（严守 CRLF，改完自检 bareLF=0）。"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)


def 替换(path, old, new, 计数=1):
    b = open(path, 'rb').read()
    o = old.encode('utf-8')
    n = new.encode('utf-8')
    c = b.count(o)
    if c != 计数:
        print('!! %s 期望 %d 处，实到 %d 处 —— 未改' % (path, 计数, c))
        return False
    b2 = b.replace(o, n)
    # 自检：CRLF 之外不得残留裸 LF
    bare = b2.replace(b'\r\n', b'').count(b'\n')
    if bare:
        print('!! %s 出现裸 LF %d 处 —— 回滚' % (path, bare))
        return False
    open(path, 'wb').write(b2)
    print('OK %s（%d 处，CRLF=%d，bareLF=0）' % (path, c, b2.count(b'\r\n')))
    return True


ok = True

# ── 1. src 腿真身：stdlib/内置核心判型.light ────────────────────────────────
ok &= 替换(
    'stdlib/内置核心判型.light',
    '# 对齐 stdlib/builtins.py:771 —— 值 is None（光明侧用类型相等表达，不走 __eq__）\r\n'
    '段落 是空(值):\r\n'
    '  返回 类型(值) == 类型(空)\r\n',
    '# 对齐 stdlib/builtins.py:771 —— 值 is None（光明侧用类型相等表达，不走 __eq__）\r\n'
    '# R153 扩语义（业主裁定）：是空 := null 或 ""。\r\n'
    '#   · 纯空白/空格**不算空**（" " -> 假），由 是空白 单独覆盖；\r\n'
    '#   · 空容器（列表()/{}）不算空；bytes 空串 b"" 不算空（只认 str 的 ""）。\r\n'
    '# 不跟着扩的：`断言为无/断言不为无` 契约是「为无」= is None，见 断言工具.light。\r\n'
    '段落 是空(值):\r\n'
    '  如果 类型(值) == 类型(空):\r\n'
    '    返回 真\r\n'
    '  返回 是字符串(值) 且 长(值) == 0\r\n',
)

# ── 2. B1 绕开回归统一语义：stdlib/文件系统.light ───────────────────────────
ok &= 替换(
    'stdlib/文件系统.light',
    '    # 原生腿 `是空` 只判 null（type==0），不认空串；USERPROFILE 缺失时\r\n'
    '    # `环境变量` 返空串而非 null，故改用 `长(家) == 0` 做两腿一致的空判定。\r\n'
    '    如果 长(家) == 0:\r\n',
    '    # R153：`是空` 已统一为「null 或 空串」（两腿一致），这里回到统一语义。\r\n'
    '    # （R152-B1 曾因 是空 只判 null 而临时改用 长(家)==0，属局部绕开，\r\n'
    '    #   按业主裁定「不能长期分叉」，语义统一后回归 是空。）\r\n'
    '    如果 是空(家):\r\n',
)
ok &= 替换(
    'stdlib/文件系统.light',
    '    如果 长(家) == 0:\r\n      返回 路径\r\n',
    '    如果 是空(家):\r\n      返回 路径\r\n',
)

# ── 3. 同类第三处：stdlib/内置核心系统.light 双判断合并 ─────────────────────
ok &= 替换(
    'stdlib/内置核心系统.light',
    '  设 甲 为 环境变量("USERPROFILE")\r\n'
    '  如果 甲 == 空:\r\n'
    '    返回 环境变量("HOME")\r\n'
    '  如果 甲 == "":\r\n'
    '    返回 环境变量("HOME")\r\n'
    '  返回 甲\r\n',
    '  # R153：`是空` 已统一为「null 或 空串」，原先为补 是空 缺口而手写的\r\n'
    '  # 「甲 == 空 / 甲 == ""」双判断，合并为一次 是空 判定（同类第三处）。\r\n'
    '  设 甲 为 环境变量("USERPROFILE")\r\n'
    '  如果 是空(甲):\r\n'
    '    返回 环境变量("HOME")\r\n'
    '  返回 甲\r\n',
)

# ── 4. 防漂移：断言为无/断言不为无 保持「为无」= is None ────────────────────
ok &= 替换(
    'stdlib/断言工具.light',
    '段落 断言为无(值, 消息 = ""):\r\n'
    '  如果 是空(值) == 假:\r\n'
    '    断言失败(消息)\r\n',
    '# R153：是空 扩为「null 或 空串」，但本段落契约是「为**无**」= is None，\r\n'
    '# 不能跟着漂 —— 否则 断言为无("") 会从「失败」变「通过」（清单 §2.2）。\r\n'
    '# 故内部显式用 null 判定（即 是空 的旧语义），与段落名保持一致。\r\n'
    '段落 断言为无(值, 消息 = ""):\r\n'
    '  如果 类型(值) != 类型(空):\r\n'
    '    断言失败(消息)\r\n',
)
ok &= 替换(
    'stdlib/断言工具.light',
    '段落 断言不为无(值, 消息 = ""):\r\n'
    '  如果 是空(值) == 真:\r\n'
    '    断言失败(消息)\r\n',
    '# 同上：契约是「不为无」，判 null，不随 是空 扩语义。\r\n'
    '段落 断言不为无(值, 消息 = ""):\r\n'
    '  如果 类型(值) == 类型(空):\r\n'
    '    断言失败(消息)\r\n',
)

print('ALL_OK' if ok else 'HAS_FAILURE')
sys.exit(0 if ok else 1)
