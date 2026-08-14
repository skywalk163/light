# -*- coding: utf-8 -*-
"""段言积木『层级生成』v0.13 —— 把若干低级积木组合固化成高级积木（成语式宏）。

把一个组合配方（组成步骤）内联展开为一个导出的 段落，相当于段言的「成语式宏」：
**高级积木 = 低级积木的成语组合**。生成的 .duan 自动注册进 索引.json（层级=1），
即可像普通积木一样被选中、被链式、再被组合成 L2——这正是「3-7 块搭一级、
层层向上」设想的落地点。

配方 JSON 结构见本文档底部示例。核心字段：
  - 名称/领域/层级/描述/导出名：同普通积木契约
  - 输入：模块入参列表（[{名, 类型}]）
  - 组成：底层积木调用步骤（引用 赵果N 实现模块内链式）
  - 返回：模块返回值表达式（可引用 赵果N 或 输入名）
  - 输出（可选）：模块输出类型，缺省 {类型: 数}

用法::
    python 积木库/层级生成.py 积木库/范围跨度配方.json
"""

import argparse
import json
import os
import sys
from collections import defaultdict

_HERE = os.path.abspath(os.path.dirname(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from 粘合 import _提取段落, _安全块路径   # noqa: E402


def _结果变量(i):
    return '赵果%d' % (i + 1)


def _并行输出类型(steps, 块表):
    """并行 L1 的输出 = 各步结果拼成的列表。

    v0.18：各步输出同类型 T 时精确标注为 列表[T]（如 描述统计 -> 列表[数]），
    异构时才退化为 列表[任意]。此前一律写死 '列表'，上层块永远只能渐进匹配。
    """
    ts = set()
    for s in steps:
        b = 块表.get(s.get('块')) or {}
        out = b.get('输出') or {}
        ts.add((out.get('类型') if isinstance(out, dict) else None) or '任意')
    只 = ts.pop() if len(ts) == 1 else '任意'
    return '列表[%s]' % 只


def generate(配方, 库根=_HERE):
    """把配方合成一个 L1+ 积木 .duan，返回 (源码, 索引条目)。"""
    名称 = 配方['名称']
    领域 = 配方['领域']
    层级 = 配方.get('层级', 1)
    导出名 = 配方.get('导出名', 名称)
    输入 = 配方.get('输入') or []
    组成 = 配方.get('组成') or []
    if not 组成:
        raise ValueError('配方缺少非空的 组成 字段')

    入参 = ', '.join(p['名'] for p in 输入) or '入料'

    lines = [
        '# 由 段言积木层级生成 v0.13 自动合成（成语式宏展开）',
        '# 层级：%d · 领域：%s · 名称：%s' % (层级, 领域, 名称),
        '# 描述：' + str(配方.get('描述', '')),
        '',
    ]

    # 1) 内联底层积木段落（去重）
    seen = set()
    for s in 组成:
        key = (s['领域'], s['块'])
        if key in seen:
            continue
        seen.add(key)
        blk_path = _安全块路径(库根, s.get('路径') or '')
        if not os.path.isfile(blk_path):
            blk_path = os.path.join(库根, s['领域'], s['块'] + '.duan')
        if os.path.isfile(blk_path):
            lines.append('# ── 积木：%s（%s）──' % (s['块'], s['领域']))
            lines.append(_提取段落(blk_path))
            lines.append('')

    # 2) 模块主体：调用各组成步
    # 注意：段落名与导出名统一用「导出名」（与 L0 块约定一致：段落名==导出名），
    # 否则索引里的 导出名 与文件里实际函数名不一致，调用方按 导出名 调用会 NameError。
    lines.append('段落 %s 接收 %s：' % (导出名, 入参))
    for i, s in enumerate(组成):
        var = _结果变量(i)
        if s.get('说明'):
            lines.append('    # %s' % s['说明'])
        参数 = ', '.join(str(p) for p in (s.get('参数') or []))
        lines.append('    设 %s 为 %s(%s)。' % (var, s['导出名'], 参数))
    # 3) 返回
    返回 = 配方.get('返回', _结果变量(len(组成) - 1))
    lines.append('    返回 %s。' % 返回)
    lines.append('')
    lines.append('导出 %s' % 导出名)

    源码 = '\n'.join(lines).rstrip() + '\n'

    条目 = {
        '名称': 名称,
        '领域': 领域,
        '层级': 层级,
        '描述': 配方.get('描述', ''),
        '输入': 输入,
        '输出': 配方.get('输出', {'类型': '数'}),
        '稳定性': 配方.get('稳定性', 'stable'),
        '路径': '%s/%s.duan' % (领域, 名称),
        '导出名': 导出名,
    }
    # v0.20：配方里的可选契约字段必须透传，否则 自动织 标的 选块可见=False 会被丢掉，
    # 聚合脚手架又会回到候选池里遮蔽被它包含的精确块（跑分 C04 就是这么退化的）
    for k in ('选块可见', '样例', '期望'):
        if k in 配方:
            条目[k] = 配方[k]
    return 源码, 条目


def _写入索引(条目, 索引路径):
    """幂等追加：同名已存在则跳过，避免重复运行污染索引。"""
    with open(索引路径, 'r', encoding='utf-8') as f:
        索引 = json.load(f)
    块 = 索引.setdefault('块', [])
    if any(b.get('名称') == 条目['名称'] for b in 块):
        return False
    块.append(条目)
    with open(索引路径, 'w', encoding='utf-8') as f:
        json.dump(索引, f, ensure_ascii=False, indent=2)
    return True


# ---------------------------------------------------------------------------
# v0.15：自动织 —— 把 生成/ 积木 + 全库积木自动组合成 L1（成语式宏升级）
# ---------------------------------------------------------------------------
# 策划的高价值组合（把 生成/ 里的方差/中位数 等也编入 L1）
_策划组合 = [
    {
        '名称': '描述统计', '领域': '数据',
        '组成来源': ['均值', '最大', '最小', '计数', '方差', '中位数'],
        '入名': '序列', '入类型': '列表',
        '描述': '基础描述统计：对列表并行给出 均值/最大/最小/计数/方差/中位数',
    },
    {
        '名称': '中文数字', '领域': '中文',
        '组成来源': ['人民币大写', '数字转中文'],
        '入名': '值', '入类型': '数',
        '描述': '中文数字能力：对数值给出 人民币大写 与 中文读数',
    },
]


def _配方到步骤(组成来源, 块表, 入名):
    steps = []
    seen = set()
    for nm in 组成来源:
        b = 块表.get(nm)
        if not b or b['导出名'] in seen:
            return None
        seen.add(b['导出名'])
        steps.append({
            '块': b['名称'], '领域': b['领域'], '导出名': b['导出名'],
            '路径': b.get('路径', ''), '参数': [入名],
        })
    return steps


def 自动织(库根=_HERE):
    """扫描全库（含 生成/），自动织成 L1 积木并幂等注册。返回新建的 L1 名称列表。"""
    索引路径 = os.path.join(库根, '索引.json')
    索引 = json.load(open(索引路径, encoding='utf-8'))
    块 = 索引.get('块') or []
    块表 = {b['名称']: b for b in 块}
    创建 = []

    # 1) 策划组合（高价值、确定性）
    for spec in _策划组合:
        steps = _配方到步骤(spec['组成来源'], 块表, spec['入名'])
        if not steps:
            continue
        n = len(steps)
        配方 = {
            '名称': spec['名称'], '领域': spec['领域'], '层级': 1,
            '描述': spec['描述'], '导出名': spec['名称'],
            '输入': [{'名': spec['入名'], '类型': spec['入类型']}],
            '组成': steps,
            '返回': '[' + ', '.join('赵果%d' % (i + 1) for i in range(n)) + ']',
            '输出': {'类型': _并行输出类型(steps, 块表)}, '稳定性': 'generated',
        }
        源码, 条目 = generate(配方, 库根=库根)
        out = os.path.join(库根, 条目['领域'], 条目['名称'] + '.duan')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(源码)
        if _写入索引(条目, 索引路径):
            创建.append(条目['名称'])

    # 2) 自动聚类：按「领域 + 完整输入类型签名」把同输入的多块聚成「聚合」L1
    #    v0.19 两处修正：
    #      a) 参数元数必须全传——旧版无论签名几元都只传首参，导致生成的 L1 一跑就
    #         「missing positional argument」（冒烟测试首发即抓到 聚合_工具_3项/聚合_文本_2项）
    #      b) 按领域分桶——旧版按类型全库聚类，会把 网络/工具 之类无关块拼成一盘杂烩，
    #         生成的「能力」语义上没有意义
    跳过 = []
    groups = defaultdict(list)
    for b in 块:
        sig = tuple(p.get('类型') for p in (b.get('输入') or []))
        if not sig:
            continue
        groups[(b.get('领域'), sig)].append(b)
    for (领域, sig), grp in groups.items():
        grp = [b for b in grp if b.get('导出名')]
        if not (2 <= len(grp) <= 6):
            continue
        # 入名取首块的参数名（位置调用，命名差异无碍）；缺名时按位补
        首入 = grp[0].get('输入') or []
        入名表 = []
        for i, t in enumerate(sig):
            n = (首入[i].get('名') if i < len(首入) else None) or ('入料%d' % (i + 1))
            while n in 入名表:                      # 同名参数去重
                n += '乙'
            入名表.append(n)
        入类型 = sig[0]
        seen = set()
        steps = []
        for b in grp:
            if b['导出名'] in seen:
                continue
            seen.add(b['导出名'])
            steps.append({
                '块': b['名称'], '领域': b['领域'], '导出名': b['导出名'],
                '路径': b.get('路径', ''), '参数': list(入名表),
            })
        if len(steps) < 2:
            continue
        # 名字必须带上输入签名：只用「领域+项数」会让两组不同签名的块重名，
        # 结果是 .duan 被后者覆盖、索引却留着前者，契约与实现对不上（体检 E7）
        类型标签 = ''.join((t or '任意').split('[')[0] for t in sig)
        名 = '聚合_%s_%s_%d项' % (领域, 类型标签, len(steps))
        配方 = {
            '名称': 名, '领域': 领域, '层级': 1,
            '描述': '自动织成：对%s输入并行执行 %s，返回结果列表' % (
                入类型, '、'.join(s['块'] for s in steps)),
            '导出名': 名,
            '输入': [{'名': n, '类型': t} for n, t in zip(入名表, sig)],
            '组成': steps,
            '返回': '[' + ', '.join('赵果%d' % (i + 1) for i in range(len(steps))) + ']',
            '输出': {'类型': _并行输出类型(steps, 块表)}, '稳定性': 'generated',
            # 自动聚合是组合脚手架，不是一项「能力」：让它参与选块只会遮蔽被它包含的精确块
            '选块可见': False,
        }
        源码, 条目 = generate(配方, 库根=库根)
        out = os.path.join(库根, 领域, 名 + '.duan')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(源码)
        # v0.20 冒烟自检闸门：同输入类型 ≠ 同输入语义。
        # 「地址转数 + 域名提取」都接文本，并联后无论喂什么都必崩一个；
        # 「JSON解析 + 键值解析」同理。织完先真跑一次，跑不通就不注册。
        诊 = _冒烟自检(条目, 库根)
        if 诊 is not None:
            跳过.append((名, 诊))
            continue
        if _写入索引(条目, 索引路径):
            创建.append(名)

    if 跳过:
        print('[自动织] 冒烟未过、未注册：%s'
              % '、'.join('%s(%s)' % (n, d) for n, d in 跳过))
    return 创建


def _冒烟自检(条目, 库根):
    """真跑一次织出来的块。通过返回 None，否则返回简短原因。"""
    try:
        评估目录 = os.path.join(库根, '评估')
        if 评估目录 not in sys.path:
            sys.path.insert(0, 评估目录)
        import 冒烟 as _smoke
    except Exception:
        return None      # 冒烟模块不可用时不阻断织造（退化成 v0.19 行为）
    try:
        r = _smoke.跑一块(条目)
    except Exception as e:
        return '冒烟异常 %s' % e
    if r.get('状态') == '通过':
        return None
    return ('%s %s' % (r.get('状态'), r.get('详情') or ''))[:80]


def _cli(argv=None):
    p = argparse.ArgumentParser(
        description='段言积木层级生成 v0.13（成语式宏：低级积木 → 高级积木）')
    p.add_argument('配方', nargs='?', default=None, help='组合配方 JSON 路径（--自动 时无需提供）')
    p.add_argument('-o', '--输出', default=None,
                   help='输出 .duan 路径（缺省 积木库/<领域>/<名称>.duan）')
    p.add_argument('--写索引', action='store_true',
                   help='把生成的积木条目追加进 索引.json（幂等）')
    p.add_argument('--自动', action='store_true',
                   help='v0.15：扫描全库（含 生成/）自动织成 L1 积木')
    args = p.parse_args(argv)

    if args.自动:
        建 = 自动织(_HERE)
        if 建:
            print('[自动织] 新建 L1 积木：' + '、'.join(建))
        else:
            print('[自动织] 无新组合（均已存在或不足 2 块）')
        return 0

    with open(args.配方, 'r', encoding='utf-8') as f:
        配方 = json.load(f)
    源码, 条目 = generate(配方)

    out = args.输出 or os.path.join(
        _HERE, 条目['领域'], 条目['名称'] + '.duan')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(源码)
    print('已生成积木：' + out)

    if args.写索引:
        if _写入索引(条目, os.path.join(_HERE, '索引.json')):
            print('已注册进 索引.json：%s（层级 %d，导出名 %s）'
                  % (条目['名称'], 条目['层级'], 条目['导出名']))
        else:
            print('索引已含 %s，跳过追加。' % 条目['名称'])
    else:
        print('（未写索引；加 --写索引 可注册为可选积木）')
    return 0


if __name__ == '__main__':
    raise SystemExit(_cli())
