# -*- coding: utf-8 -*-
"""段言积木『基准跑分』v1.0 —— 把选块/校验/兜底判定的质量变成可量化、可回归的数字。

为什么需要它：
  v0.16 之前，选块准不准、校验器会不会误拦、兜底该不该触发，全靠单点手测「感觉」。
  没有尺子就无法证明任何改动是提升还是回退。本脚本对 评估/基准.json 里的每条需求
  跑一遍『选块 → 校验 → 兜底判定』（不执行生成、不写盘、不污染索引），产出：

  · 选块质量：Hit@1 / Hit@3 / MRR（仅库内条目）
  · 兜底判定：库外召回率（该兜底的有没有兜底）、库内误兜底率
  · 校验器：库内 FN（把对的拦下）、库外 FP（把错的放行）
  · 链路正确率：库内 top1 正确且不误兜底 + 库外正确判定兜底，占全部条目

用法：
    python 积木库/评估/跑分.py                       # 默认 embedding（装了 st 则真向量）
    python 积木库/评估/跑分.py --策略 概念图 --详细    # 强制概念图向量，打印错误明细
    python 积木库/评估/跑分.py --策略 语义 --标签 report_语义
    python 积木库/评估/跑分.py --对比 评估/报告/xxx.json   # 与历史报告逐指标对比

安全性：只调用 select/validate/local_rule_block（纯判定），绝不调用 注册()，
因此跑分不会向 索引.json 或 生成/ 写入任何东西。
"""

import argparse
import json
import os
import sys
import time

_HERE = os.path.abspath(os.path.dirname(__file__))
_LIB = os.path.normpath(os.path.join(_HERE, '..'))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from 选块 import select_blocks, load_index          # noqa: E402
from 语义选块 import semantic_select                 # noqa: E402
from embedding选块 import embedding_select, _真向量可用  # noqa: E402
from 校验器 import validate                          # noqa: E402
from 兜底生成器 import local_rule_block               # noqa: E402

_默认阈值 = {'embedding': 0.06, '概念图': 0.06, '混合': 0.06,
             '语义': 0.12, '关键词': 3.0}


def 基准路径():
    return os.path.join(_HERE, '基准.json')


def 载入基准(path=None):
    with open(path or 基准路径(), 'r', encoding='utf-8') as f:
        return json.load(f)


def 选块(需求, 索引, 策略, top):
    if 策略 == '关键词':
        return select_blocks(需求, 索引, top=top)
    if 策略 == '语义':
        return semantic_select(需求, 索引, top=top)
    if 策略 == '概念图':
        return embedding_select(需求, 索引, top=top, real=False)
    if 策略 == '混合':
        from 混合选块 import hybrid_select
        return hybrid_select(需求, 索引, top=top)
    return embedding_select(需求, 索引, top=top)


def 判定兜底(需求, 候选, 查表, 阈值, 无校验=False, 含预检=True):
    """复现 组合.py 的兜底触发判定（纯判定，不生成不写盘）。

    返回 (是否兜底, 理由, 校验结果或 None)
    """
    if not 候选:
        return True, '无候选', None
    if 候选[0]['分数'] < 阈值:
        return True, 'top 分数 %.4f 低于阈值 %.2f' % (候选[0]['分数'], 阈值), None

    校验 = None
    if not 无校验:
        候选_full = [查表.get(c['名称']) or c for c in 候选]
        校验 = validate(需求, 候选_full)
        if not 校验['通过']:
            return True, '校验未过：' + 校验['理由'], 校验

    if 含预检:
        lr = local_rule_block(需求)
        if lr and lr['名称'] not in [c['名称'] for c in 候选]:
            if lr['名称'] in 查表:
                # 库内已有该能力，只是没被选上 ⇒ 纠正选块，不算兜底（与 组合.py 一致）
                return False, '[纠正] 库内已有：' + lr['名称'], 校验
            return True, '能力缺失预检命中本地规则：' + lr['名称'], 校验

    return False, '', 校验


def 跑一条(条目, 索引, 查表, 策略, top, 阈值, 无校验, 含预检):
    需求 = 条目['需求']
    期望 = set(条目.get('期望块') or [])
    应兜底 = bool(条目.get('应兜底'))

    t0 = time.time()
    候选 = 选块(需求, 索引, 策略, top)
    耗时 = round((time.time() - t0) * 1000, 1)
    名单 = [c['名称'] for c in 候选]

    位次 = 0
    for i, n in enumerate(名单):
        if n in 期望:
            位次 = i + 1
            break

    是兜底, 理由, 校验 = 判定兜底(需求, 候选, 查表, 阈值, 无校验, 含预检)

    return {
        'id': 条目.get('id'), '需求': 需求, '标签': 条目.get('标签') or [],
        '应兜底': 应兜底, '期望块': sorted(期望),
        '候选': [{'名称': c['名称'], '分数': c['分数']} for c in 候选],
        'hit1': (位次 == 1), 'hit3': (0 < 位次 <= 3), '位次': 位次,
        '判定兜底': 是兜底, '兜底理由': 理由,
        '校验通过': (None if 校验 is None else 校验['通过']),
        '校验理由': ('' if 校验 is None else 校验['理由']),
        '选块耗时ms': 耗时,
    }


def _率(分子, 分母):
    return round(分子 / 分母, 4) if 分母 else None


def 汇总(明细):
    库内 = [r for r in 明细 if not r['应兜底']]
    库外 = [r for r in 明细 if r['应兜底']]

    hit1 = sum(1 for r in 库内 if r['hit1'])
    hit3 = sum(1 for r in 库内 if r['hit3'])
    mrr = sum((1.0 / r['位次']) for r in 库内 if r['位次']) / len(库内) if 库内 else None

    误兜底 = [r for r in 库内 if r['判定兜底']]
    外兜底 = [r for r in 库外 if r['判定兜底']]

    # 校验器单看：库内『校验通过=False』= FN(误拦)；库外『校验通过=True』= FP(误放行)
    校验FN = [r for r in 库内 if r['校验通过'] is False]
    校验FP = [r for r in 库外 if r['校验通过'] is True]

    链路对 = sum(1 for r in 库内 if r['hit1'] and not r['判定兜底']) + len(外兜底)

    return {
        '条目数': len(明细), '库内': len(库内), '库外': len(库外),
        '选块': {
            'Hit@1': _率(hit1, len(库内)), 'Hit@3': _率(hit3, len(库内)),
            'MRR': (round(mrr, 4) if mrr is not None else None),
        },
        '兜底判定': {
            '库外召回': _率(len(外兜底), len(库外)),
            '库内误兜底率': _率(len(误兜底), len(库内)),
            '误兜底条目': [r['id'] for r in 误兜底],
            '库外漏判条目': [r['id'] for r in 库外 if not r['判定兜底']],
        },
        '校验器': {
            'FN误拦': len(校验FN), 'FN条目': [r['id'] for r in 校验FN],
            'FP误放行': len(校验FP), 'FP条目': [r['id'] for r in 校验FP],
        },
        '链路正确率': _率(链路对, len(明细)),
        '平均选块耗时ms': round(sum(r['选块耗时ms'] for r in 明细) / len(明细), 1) if 明细 else None,
    }


def 按标签(明细):
    组 = {}
    for r in 明细:
        for t in r['标签']:
            组.setdefault(t, []).append(r)
    out = {}
    for t, rs in sorted(组.items()):
        库内 = [r for r in rs if not r['应兜底']]
        库外 = [r for r in rs if r['应兜底']]
        对 = sum(1 for r in 库内 if r['hit1'] and not r['判定兜底']) \
            + sum(1 for r in 库外 if r['判定兜底'])
        out[t] = {'条目': len(rs), '正确': 对, '正确率': _率(对, len(rs))}
    return out


def 打印报告(报告, 详细=False):
    m, s = 报告['元信息'], 报告['总体']
    print('══ 段言积木基准跑分 ══')
    print('策略=%s  模式=%s  块总数=%d  条目=%d（库内 %d / 库外 %d）  阈值=%s'
          % (m['策略'], m['模式'], m['块总数'], s['条目数'], s['库内'], s['库外'], m['阈值']))
    print('── 选块 ──  Hit@1=%s  Hit@3=%s  MRR=%s  平均耗时=%sms'
          % (s['选块']['Hit@1'], s['选块']['Hit@3'], s['选块']['MRR'], s['平均选块耗时ms']))
    print('── 兜底判定 ──  库外召回=%s  库内误兜底率=%s'
          % (s['兜底判定']['库外召回'], s['兜底判定']['库内误兜底率']))
    print('── 校验器 ──  FN误拦=%d %s  FP误放行=%d %s'
          % (s['校验器']['FN误拦'], s['校验器']['FN条目'],
             s['校验器']['FP误放行'], s['校验器']['FP条目']))
    print('── 链路正确率 ──  %s' % s['链路正确率'])

    print('── 按标签 ──')
    for t, v in 报告['按标签'].items():
        print('  %-6s %2d/%-2d  %s' % (t, v['正确'], v['条目'], v['正确率']))

    错 = [r for r in 报告['明细']
          if (not r['应兜底'] and (not r['hit1'] or r['判定兜底']))
          or (r['应兜底'] and not r['判定兜底'])]
    print('── 失败条目（%d）──' % len(错))
    for r in 错:
        top = '、'.join('%s(%s)' % (c['名称'], c['分数']) for c in r['候选'][:3]) or '（空）'
        want = '应兜底' if r['应兜底'] else '/'.join(r['期望块'])
        print('  %-4s %-28s 期望=%-14s top=%s%s'
              % (r['id'], r['需求'][:26], want, top,
                 ('  ← 误兜底：' + r['兜底理由']) if (not r['应兜底'] and r['判定兜底']) else ''))
        if 详细 and r['校验理由']:
            print('        校验：%s' % r['校验理由'])


def _cli(argv=None):
    p = argparse.ArgumentParser(description='段言积木基准跑分 v1.0')
    p.add_argument('--策略', default='embedding',
                   choices=['embedding', '概念图', '混合', '语义', '关键词'])
    p.add_argument('--top', type=int, default=3)
    p.add_argument('--阈值', type=float, default=None)
    p.add_argument('--无校验', action='store_true')
    p.add_argument('--无预检', action='store_true', help='不模拟组合.py 的能力缺失预检')
    p.add_argument('--详细', action='store_true')
    p.add_argument('--real', action='store_true',
                   help='embedding 策略下强制走真·句向量（默认已改为概念图，见 README）')
    p.add_argument('--标签', default=None, help='报告文件名后缀，便于区分改动前后')
    p.add_argument('--对比', default=None, help='与历史报告 json 做逐指标对比')
    p.add_argument('--不落盘', action='store_true')
    args = p.parse_args(argv)

    if args.real:
        os.environ['DUAN_EMBED_REAL'] = '1'

    基准 = 载入基准()
    索引 = load_index()
    查表 = {b['名称']: b for b in (索引.get('块') or [])}
    阈值 = args.阈值 if args.阈值 is not None else _默认阈值[args.策略]

    用真 = (args.策略 == 'embedding'
            and os.environ.get('DUAN_EMBED_REAL') == '1' and _真向量可用())
    模式 = ('真·句向量' if 用真 else
            ('概念图向量' if args.策略 in ('embedding', '概念图') else args.策略))

    明细 = [跑一条(c, 索引, 查表, args.策略, args.top, 阈值,
                 args.无校验, not args.无预检)
           for c in 基准['条目']]

    报告 = {
        '元信息': {
            '时间': time.strftime('%Y-%m-%d %H:%M:%S'), '基准版本': 基准.get('版本'),
            '策略': args.策略, '模式': 模式, '阈值': 阈值, 'top': args.top,
            '块总数': len(索引.get('块') or []), '含预检': not args.无预检,
            '含校验': not args.无校验,
        },
        '总体': 汇总(明细), '按标签': 按标签(明细), '明细': 明细,
    }

    打印报告(报告, 详细=args.详细)

    if not args.不落盘:
        目录 = os.path.join(_HERE, '报告')
        os.makedirs(目录, exist_ok=True)
        名 = 'report_%s%s.json' % (args.策略, ('_' + args.标签) if args.标签 else '')
        路径 = os.path.join(目录, 名)
        with open(路径, 'w', encoding='utf-8') as f:
            json.dump(报告, f, ensure_ascii=False, indent=2)
        print('\n已写入报告：%s' % os.path.relpath(路径, _LIB))

    if args.对比:
        旧 = json.load(open(args.对比, encoding='utf-8'))
        print('\n── 对比 %s ──' % os.path.basename(args.对比))
        for 组, 键 in (('选块', 'Hit@1'), ('选块', 'Hit@3'), ('选块', 'MRR'),
                      ('兜底判定', '库外召回'), ('兜底判定', '库内误兜底率')):
            a, b = 旧['总体'][组][键], 报告['总体'][组][键]
            print('  %-8s %s → %s  (%+.4f)' % (键, a, b, (b or 0) - (a or 0)))
        a, b = 旧['总体']['链路正确率'], 报告['总体']['链路正确率']
        print('  %-8s %s → %s  (%+.4f)' % ('链路正确率', a, b, (b or 0) - (a or 0)))
    return 0


if __name__ == '__main__':
    raise SystemExit(_cli())
