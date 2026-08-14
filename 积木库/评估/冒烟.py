# -*- coding: utf-8 -*-
"""段言积木『冒烟测试』v0.19 —— 第四把尺子：每一块**真的跑得起来吗**？

前三把尺子分别量「选块对不对」「接线对不对」「契约自洽吗」，但它们都不执行代码。
一块 `.duan` 完全可能契约漂亮、被正确选中、参数接得完美，然后在运行时炸掉
（词法器把标识符切碎、调了不存在的内建、用了静默失效的默认参数……）。
段言的这些坑都只在**运行期**暴露，所以必须有一把尺子真的把每块跑一遍。

做法：对索引里的每一块，
  1. 按 `样例` 字段（若有）或**结构化类型**推导一组默认实参；
  2. 内联该块源码 + 一行调用，写成临时 .duan；
  3. `python cli/duan.py run` 执行，比对是否报错 / 是否命中 `期望` 值。

类型驱动的默认实参正是类型系统 v2 的红利：契约写成 `列表[数]` 才能自动造出
`[3, 1, 4, 1, 5]` 而不是瞎猜。

用法：
    python 积木库/评估/冒烟.py                 # 跑全库
    python 积木库/评估/冒烟.py --只跑 日期 校验  # 只跑指定领域
    python 积木库/评估/冒烟.py --块 闰年 星期几  # 只跑指定块
    python 积木库/评估/冒烟.py --详细           # 打印每块的实参与返回值
    python 积木库/评估/冒烟.py --并发 8          # 并行跑（CI 用，151 块 2m50s → 30s 级）

v0.27（CI 接入）三处改动：
  1. **缺依赖 ≠ 失败**。少数块（转拼音/公历转农历…）依赖第三方包，环境没装时以前
     一律记「失败」，会把 CI 门槛永远卡死。现在按索引 `依赖` 字段预检，或从运行期
     「pip install X」提示反查，单列为 `缺依赖` 状态，不计入可运行率分母。
  2. **失败要说人话**。段言把运行期错误写在 stderr，而这里只读 stdout，于是问题块的
     「详情」长期是空字符串。现在 stdout 为空时回退取 stderr 首条有效信息。
  3. **可并发**。工位文件从写死一个改为可传入，配合槽位队列并行执行。
"""

import argparse
import importlib.util
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

_HERE = os.path.abspath(os.path.dirname(__file__))
_LIB = os.path.abspath(os.path.join(_HERE, '..'))
_ROOT = os.path.abspath(os.path.join(_LIB, '..'))

sys.path.insert(0, _LIB)
import 类型 as T  # noqa: E402


# ---------------------------------------------------------------------------
# 类型 → 默认实参（段言字面量文本）
# ---------------------------------------------------------------------------
_默认标量 = {
    '数': '6',
    '文本': '"Hello World"',
    '逻辑': '真',
    '任意': '6',
    '空': '空',
}
_默认列表 = {
    '数': '[3, 1, 4, 1, 5]',
    '文本': '["banana", "apple", "cherry"]',
    '逻辑': '[真, 假, 真]',
    '任意': '[3, 1, 4, 1, 5]',
}


def 默认实参(类型串):
    """按结构化类型造一个段言字面量。造不出来返回 None（跳过该块）。"""
    try:
        t = T.解析(类型串 or '任意')
    except Exception:
        return None
    kind = t[0]
    if kind == '基础':
        return _默认标量.get(t[1], '6')
    if kind == '列表':
        inner = t[1]
        if inner[0] == '基础':
            return _默认列表.get(inner[1], '[3, 1, 4, 1, 5]')
        return '[[1, 2], [3, 4]]'
    if kind == '字典':
        return '{"a": 1, "b": 2}'
    if kind == '联合':
        return 默认实参(T.格式化(t[1][0]))
    return None


def 实参表(块):
    """优先用块自带 `样例`（列表，逐参数的段言字面量），否则按类型推导。"""
    样例 = 块.get('样例')
    if isinstance(样例, list) and 样例:
        return [str(x) for x in 样例]
    out = []
    for p in (块.get('输入') or []):
        a = 默认实参(p.get('类型'))
        if a is None:
            return None
        out.append(a)
    return out


# ---------------------------------------------------------------------------
# 第三方依赖预检
# ---------------------------------------------------------------------------
_缺库提示 = re.compile(r'pip install ([A-Za-z0-9_.\-]+)')


def 规范依赖(项):
    """索引里 `依赖` 允许两种写法：'pypinyin' 或 {'包':'opencc-python-reimplemented',
    '模块':'opencc'}（pip 包名与 import 名不一致时必须用后者）。"""
    if isinstance(项, str):
        return {'包': 项, '模块': 项}
    return {'包': 项.get('包') or 项.get('模块'),
            '模块': 项.get('模块') or 项.get('包')}


def 缺哪些依赖(块):
    """返回该块声明了、但当前解释器装不上的 pip 包名列表。"""
    缺 = []
    for 项 in (块.get('依赖') or []):
        d = 规范依赖(项)
        try:
            有 = importlib.util.find_spec(d['模块']) is not None
        except Exception:
            有 = False
        if not 有:
            缺.append(d['包'])
    return 缺


# ---------------------------------------------------------------------------
# 执行
# ---------------------------------------------------------------------------
def _块源码(路径):
    with open(os.path.join(_LIB, 路径), 'r', encoding='utf-8') as f:
        lines = f.readlines()
    out = []
    for ln in lines:
        s = ln.strip()
        if s.startswith('#') or s.startswith('导出'):
            continue
        out.append(ln.rstrip('\n'))
    return '\n'.join(out).strip('\n')


def _stderr摘要(err):
    """段言把运行期错误写在 stderr：首行是「错误: 运行时错误」，真正有用的是第二行。"""
    行 = [l.strip() for l in (err or '').splitlines() if l.strip()]
    行 = [l for l in 行 if not l.startswith('源代码:') and not l.startswith('建议:')]
    return ' '.join(行[:2])[:160]


def 跑一块(块, python=None, 工位=None):
    路径 = 块.get('路径') or ''
    if not os.path.isfile(os.path.join(_LIB, 路径)):
        return {'名称': 块.get('名称'), '状态': '缺文件', '详情': 路径}
    缺 = 缺哪些依赖(块)
    if 缺:
        return {'名称': 块.get('名称'), '状态': '缺依赖',
                '详情': 'pip install ' + ' '.join(缺)}
    args = 实参表(块)
    if args is None:
        return {'名称': 块.get('名称'), '状态': '跳过', '详情': '无法为该契约造默认实参'}

    调用 = '%s(%s)' % (块.get('导出名'), ', '.join(args))
    源 = _块源码(路径) + '\n\n打印 ' + 调用 + '\n'

    # 复用工位文件：逐块建删临时文件会被批量删除保护拦下，也没必要。
    # 并发时由调用方传入不同工位，避免多线程互相覆盖。
    tmp = 工位 or os.path.join(_LIB, '_冒烟工位.duan')
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(源)
    if True:
        r = subprocess.run(
            [python or sys.executable, os.path.join(_ROOT, 'cli', 'duan.py'),
             'run', tmp],
            capture_output=True, text=True, encoding='utf-8',
            errors='replace', cwd=_ROOT, timeout=120)
        out = (r.stdout or '').strip()
        err = (r.stderr or '').strip()
        # v0.24：段言 src 后端会**静默吞掉运行期错误**（越界/除零都 rc=0 且 stdout 空，
        # 仅解析错误才 rc≠0），因此成功信号对齐 组合.py `_成功`：rc==0 且 有非空 stdout。
        ok = (r.returncode == 0) and bool(out) and not out.startswith('错误:') \
            and ('Traceback' not in err)
        if not ok:
            # 没声明依赖、但运行期喊「请执行: pip install X」的，同样归为缺依赖，
            # 顺带提醒把依赖补进索引契约。
            m = _缺库提示.search(err) or _缺库提示.search(out)
            if m:
                return {'名称': 块.get('名称'), '状态': '缺依赖', '实参': args,
                        '详情': 'pip install %s（索引未声明 依赖，建议补上）' % m.group(1)}
            首行 = (out.splitlines() or [''])[0]
            细 = (out.splitlines() or ['', ''])[1].strip() if len(out.splitlines()) > 1 else ''
            详情 = (首行 + ' ' + 细).strip() or _stderr摘要(err) or '无输出（运行期静默失败）'
            return {'名称': 块.get('名称'), '状态': '失败',
                    '实参': args, '详情': 详情[:160]}
        实 = out.splitlines()[-1] if out else ''
        期望 = 块.get('期望')
        if 期望 is not None and str(期望) != 实:
            return {'名称': 块.get('名称'), '状态': '值不符',
                    '实参': args, '详情': '期望 %s 实得 %s' % (期望, 实)}
        return {'名称': 块.get('名称'), '状态': '通过', '实参': args, '返回': 实}


def _并发跑(blocks, 并发):
    """槽位队列：每个工作线程独占一个工位文件，跑完归还，避免互相覆盖。"""
    槽 = queue.Queue()
    工位表 = [os.path.join(_LIB, '_冒烟工位_%d.duan' % i) for i in range(并发)]
    for w in 工位表:
        槽.put(w)

    def 干(b):
        w = 槽.get()
        try:
            return 跑一块(b, 工位=w)
        finally:
            槽.put(w)

    try:
        with ThreadPoolExecutor(max_workers=并发) as ex:
            return list(ex.map(干, blocks))
    finally:
        for w in 工位表:                      # 只删本函数自己建的工位文件
            try:
                os.remove(w)
            except OSError:
                pass


def 跑(领域=None, 块名=None, 详细=False, 并发=1):
    with open(os.path.join(_LIB, '索引.json'), 'r', encoding='utf-8') as f:
        index = json.load(f)
    blocks = index.get('块') or []
    if 领域:
        want = set(领域)
        blocks = [b for b in blocks
                  if want & set(b['领域'] if isinstance(b['领域'], list) else [b['领域']])]
    if 块名:
        want = set(块名)
        blocks = [b for b in blocks if b.get('名称') in want]

    print('══ 积木冒烟测试 ══')
    print('待测 %d 块%s' % (len(blocks), ('　并发 %d' % 并发) if 并发 > 1 else ''))
    结果 = _并发跑(blocks, 并发) if 并发 > 1 else [跑一块(b) for b in blocks]

    统计 = {}
    for r in 结果:
        统计[r['状态']] = 统计.get(r['状态'], 0) + 1
    通过 = 统计.get('通过', 0)
    # 「跳过」（造不出实参）与「缺依赖」（环境没装第三方包）都不是块本身的问题，
    # 不计入分母，否则 CI 门槛会被环境差异卡死。
    可判 = sum(v for k, v in 统计.items() if k not in ('跳过', '缺依赖'))
    print('── 状态 ──  ' + '　'.join('%s %d' % (k, v) for k, v in sorted(统计.items())))
    print('── 可运行率 ──  %.4f  (%d/%d)'
          % ((通过 / 可判) if 可判 else 1.0, 通过, 可判))

    坏 = [r for r in 结果 if r['状态'] in ('失败', '值不符', '缺文件')]
    缺依 = [r for r in 结果 if r['状态'] == '缺依赖']
    if 坏:
        print('── 问题块（%d）──' % len(坏))
        for r in 坏:
            print('  %-12s %-6s %s' % (r['名称'], r['状态'], r.get('详情', '')))
    if 缺依:
        print('── 缺第三方依赖、未实测（%d）──' % len(缺依))
        for r in 缺依:
            print('  %-12s %s' % (r['名称'], r.get('详情', '')))
    if 详细:
        print('── 明细 ──')
        for r in 结果:
            print('  %-12s %-6s %s → %s'
                  % (r['名称'], r['状态'],
                     ', '.join(r.get('实参') or []), r.get('返回', r.get('详情', ''))))
    return {
        '块总数': len(blocks), '统计': 统计, '通过': 通过, '可判': 可判,
        '可运行率': round((通过 / 可判) if 可判 else 1.0, 4),
        '问题块': [{'名称': r['名称'], '状态': r['状态'], '详情': r.get('详情', '')}
                 for r in 坏],
        '缺依赖块': [{'名称': r['名称'], '详情': r.get('详情', '')} for r in 缺依],
        '结果': 结果,
    }


def _cli(argv=None):
    p = argparse.ArgumentParser(description='段言积木冒烟测试（每块真跑一遍）')
    p.add_argument('--只跑', nargs='+', dest='领域', help='只跑这些领域')
    p.add_argument('--块', nargs='+', dest='块名', help='只跑这些块')
    p.add_argument('--详细', action='store_true')
    p.add_argument('--并发', type=int, default=1, help='并行线程数（每块一个子进程，IO 密集）')
    a = p.parse_args(argv)
    r = 跑(领域=a.领域, 块名=a.块名, 详细=a.详细, 并发=max(1, a.并发))
    return 0 if not r['问题块'] else 1


if __name__ == '__main__':
    raise SystemExit(_cli())
