# -*- coding: utf-8 -*-
"""积木库 CI 闸门 ci_eval v1.0 —— 把五把尺子从「人工记得跑」变成「推送即拦截」。

为什么需要它：
  v1.0 收官时质量数字全绿，但绿的方式是**人手跑五个脚本再用眼睛看**。仓库 CI（ci.yml）
  只跑段言语言本体的 tests/，积木库零覆盖——也就是说，任何人改了选块器、概念词典、
  索引契约，只要他忘了跑尺子，回归就能一路合进 main。本脚本把这件事变成机器的责任。

它做什么：
  1. 依次跑五把尺子（真实语料 / 扰动集 / 主基准 / 接线 / 体检 / 冒烟，共 6 项 7 类指标），
     全部**进程内调用**各尺子的核心函数，不靠解析 stdout，避免脚本改了措辞就误判；
  2. 对关键指标套用 门槛.json 里的硬阈值，任一不达标 → 退出码 1 → PR 检查变红；
  3. 产出机器可读的合并报告 报告/ci_eval.json，并在 GitHub Actions 上写 Step Summary。

设计约定：
  · 门槛是数据不是代码 —— 调阈值改 门槛.json，改代码只在新增指标时；
  · 尺子只被调用、不被修改 —— ci_eval 不重算任何指标，口径与人工跑完全一致；
  · 「缺依赖」不算失败 —— 少数块依赖 pypinyin/lunardate，环境没装时单列，不污染门槛
    （CI 里会装齐，本机没装也能跑，见 冒烟.py v0.27）；
  · 零 token 且可复现 —— 默认置 DUAN_NO_LLM=1，屏蔽校验器的 LLM 判定（本地 .env 配了真实
    key 也不会走网络），否则主基准会随模型漂移；确需真实 LLM 时加 --允许LLM。

用法：
    python 积木库/评估/ci_eval.py                  # 全量，写 报告/ci_eval.json
    python 积木库/评估/ci_eval.py --并发 8          # 冒烟并行（CI 推荐，2m50s → 25s）
    python 积木库/评估/ci_eval.py --快              # 跳过冒烟，秒级回归（改选块器时用）
    python 积木库/评估/ci_eval.py --详细            # 连带打印各尺子原始输出
    python 积木库/评估/ci_eval.py --每日            # 另存 报告/ci_daily.json + 追加历史
    python 积木库/评估/ci_eval.py --对比 积木库/评估/报告/ci_eval.json

退出码：0 全绿 ｜ 1 有闸门未过 ｜ 2 尺子执行本身出错
"""

import argparse
import io
import json
import os
import platform
import subprocess
import sys
import time
import traceback
from contextlib import redirect_stdout

_HERE = os.path.abspath(os.path.dirname(__file__))
_LIB = os.path.normpath(os.path.join(_HERE, '..'))
_ROOT = os.path.normpath(os.path.join(_LIB, '..'))
for p in (_LIB, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


# ---------------------------------------------------------------------------
# 门槛：数据驱动。(组, 项, 方向, 默认值)；门槛.json 同名项覆盖默认值。
# ---------------------------------------------------------------------------
_闸门定义 = [
    ('真实语料', '留出段_concept_Hit@1', '≥', 0.99),
    ('真实语料', '留出段_hybrid_Hit@1', '≥', 0.97),
    ('真实语料', '调参段_concept_Hit@1', '≥', 1.0),
    ('真实语料', '全部_concept_空候选', '≤', 0),
    ('扰动集', '留出段_concept_Hit@1', '≥', 0.95),
    ('扰动集', '留出段_hybrid_Hit@1', '≥', 0.95),
    ('扰动集', '全部_concept_Hit@3', '≥', 0.99),
    ('扰动集', '全部_concept_空候选', '≤', 0),
    ('主基准', 'Hit@1', '≥', 1.0),
    ('主基准', '链路正确率', '≥', 1.0),
    ('主基准', '失败条目数', '≤', 0),
    ('主基准', '库内误兜底率', '≤', 0.0),
    ('主基准', '库外召回', '≥', 1.0),
    ('主基准', '校验FN误拦', '≤', 0),
    ('主基准', '校验FP误放行', '≤', 0),
    ('接线', '链式接线正确率', '≥', 1.0),
    ('接线', '类型闸门正确率', '≥', 1.0),
    ('接线', '总正确率', '≥', 1.0),
    ('体检', '错误数', '≤', 0),
    ('体检', '警告数', '≤', 0),
    ('冒烟', '可运行率', '≥', 1.0),
    ('冒烟', '问题块数', '≤', 0),
    # 兜底闭环（Q4 2.4）：仅当兜底首跑 harness 真跑过足够样本才评，否则跳过——
    # 「没测过」不算失败。阈值见 门槛.json 的 兜底 段。
    ('兜底', '触发率', '≥', 1.0),
    ('兜底', '沉淀成功率', '≥', 0.7),
]


def 载入门槛():
    p = os.path.join(_HERE, '门槛.json')
    try:
        with io.open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _抓输出(fn, *a, **kw):
    """跑一把尺子并吃掉它的 print，返回 (结果, 原始输出)。

    尺子都是给人看的脚本，直接放行会把 CI 日志淹掉；但出问题时又必须能看到原文，
    所以统一收进报告，--详细 时再打印。"""
    buf = io.StringIO()
    with redirect_stdout(buf):
        r = fn(*a, **kw)
    return r, buf.getvalue()


# ---------------------------------------------------------------------------
# 六把尺子
# ---------------------------------------------------------------------------
def 量_真实语料(idx):
    import 真实跑分 as R
    d = R.载入()
    全部 = d['条目']
    段 = {'调参段': [x for x in 全部 if x.get('段') == '调参'],
          '留出段': [x for x in 全部 if x.get('段') == '留出'],
          '全部': 全部}
    指标 = {'语料版本': d.get('版本'), '条目数': len(全部),
            '调参段条数': len(段['调参段']), '留出段条数': len(段['留出段'])}
    错例 = {}
    for 段名, 条目 in 段.items():
        if not 条目:
            continue
        for 名, fn in R.选块器.items():
            r, _ = _抓输出(R.评一段, 名, fn, 条目, idx)
            for k in ('Hit@1', 'Hit@3', 'MRR'):
                指标['%s_%s_%s' % (段名, 名, k)] = r[k]
            指标['%s_%s_空候选' % (段名, 名)] = r['空候选']
            if r['错例']:
                错例['%s_%s' % (段名, 名)] = [
                    {'编号': e, '需求': q, '期望': exp, '实得': got}
                    for e, q, got, exp in r['错例']]
    return 指标, 错例


def 量_扰动集(idx):
    import 扰动跑分 as P
    条目, 版本 = P.载入()
    def 段判(it):
        if it.get('段'):
            return it['段']
        n = int(''.join(c for c in it['编号'] if c.isdigit()) or 0)
        return '调参' if n <= 20 else '留出'
    段 = {'调参段': [x for x in 条目 if 段判(x) == '调参'],
          '留出段': [x for x in 条目 if 段判(x) == '留出'],
          '全部': 条目}
    指标 = {'扰动集版本': 版本, '条目数': len(条目)}
    错例 = {}
    for 段名, 组 in 段.items():
        if not 组:
            continue
        for 名, fn in P.选块器.items():
            r, _ = _抓输出(P.评一个, 名, fn, 组, idx)
            for k in ('Hit@1', 'Hit@3', 'MRR'):
                指标['%s_%s_%s' % (段名, 名, k)] = r[k]
            指标['%s_%s_空候选' % (段名, 名)] = r['空候选']
            if 名 == 'concept' and r['错例']:
                错例[段名] = [{'编号': e, '需求': q, '期望': exp, '实得': got}
                            for e, q, got, exp in r['错例']]
    return 指标, 错例


def 量_主基准(idx):
    import 跑分 as B
    基准 = B.载入基准()
    查表 = {b['名称']: b for b in (idx.get('块') or [])}
    阈值 = B._默认阈值['embedding']
    明细 = [B.跑一条(c, idx, 查表, 'embedding', 3, 阈值, False, True)
            for c in 基准['条目']]
    总体 = B.汇总(明细)
    失败 = [r for r in 明细
            if (not r['应兜底'] and (not r['hit1'] or r['判定兜底']))
            or (r['应兜底'] and not r['判定兜底'])]
    指标 = {
        '基准版本': 基准.get('版本'), '条目数': 总体['条目数'],
        '库内': 总体['库内'], '库外': 总体['库外'], '阈值': 阈值,
        'Hit@1': 总体['选块']['Hit@1'], 'Hit@3': 总体['选块']['Hit@3'],
        'MRR': 总体['选块']['MRR'],
        '库外召回': (1.0 if 总体['兜底判定']['库外召回'] is None
                 else 总体['兜底判定']['库外召回']),
        '库内误兜底率': 总体['兜底判定']['库内误兜底率'],
        '校验FN误拦': 总体['校验器']['FN误拦'],
        '校验FP误放行': 总体['校验器']['FP误放行'],
        '链路正确率': 总体['链路正确率'],
        '失败条目数': len(失败),
        '平均选块耗时ms': 总体['平均选块耗时ms'],
    }
    细 = [{'id': r['id'], '需求': r['需求'], '期望块': r['期望块'],
           '候选': r['候选'][:3], '判定兜底': r['判定兜底'],
           '兜底理由': r['兜底理由']} for r in 失败]
    return 指标, 细


def 量_接线():
    import 接线跑分 as W
    r, 原文 = _抓输出(W.跑)
    return {'链式接线正确率': round(r['链式'], 4),
            '类型闸门正确率': round(r['闸门'], 4),
            '总正确率': round(r['总'], 4),
            '失败用例数': len(r['失败'])}, r['失败'], 原文


def 量_体检():
    import 体检 as H
    r = H.收集()
    return ({'块总数': r['块总数'], '错误数': len(r['错']), '警告数': len(r['警'])},
            {'错': r['错'], '警': r['警']})


def 量_冒烟(并发):
    import 冒烟 as S
    r, 原文 = _抓输出(S.跑, 并发=并发)
    指标 = {'块总数': r['块总数'], '通过': r['通过'], '可判': r['可判'],
            '可运行率': r['可运行率'], '问题块数': len(r['问题块']),
            '缺依赖数': len(r['缺依赖块']),
            '状态分布': r['统计']}
    return 指标, {'问题块': r['问题块'], '缺依赖块': r['缺依赖块']}, 原文


def 量_兜底():
    """兜底闭环跑分（Q4 2.4）。读 运行日志.jsonl；样本不足则返 None → 闸门跳过。"""
    import 兜底跑分 as D
    return D.量()


# ---------------------------------------------------------------------------
# 闸门判定
# ---------------------------------------------------------------------------
def 判闸门(指标, 门槛):
    结果 = []
    for 组, 项, 向, 默认 in _闸门定义:
        if 组 not in 指标:                       # --快 跳过了冒烟之类
            continue
        实测 = 指标[组].get(项)
        阈 = (门槛.get(组) or {}).get(项, 默认)
        if 实测 is None:
            结果.append({'组': 组, '项': 项, '实测': None, '门槛': 阈,
                        '向': 向, '通过': False, '说明': '指标缺失'})
            continue
        通过 = (实测 >= 阈 - 1e-9) if 向 == '≥' else (实测 <= 阈 + 1e-9)
        结果.append({'组': 组, '项': 项, '实测': 实测, '门槛': 阈,
                    '向': 向, '通过': bool(通过), '说明': ''})
    return 结果


def _git提交():
    try:
        return subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                              cwd=_ROOT, capture_output=True, text=True,
                              timeout=10).stdout.strip() or '?'
    except Exception:
        return '?'


def 打印闸门(闸门):
    print('\n══ CI 闸门判定 ══')
    print('%-2s %-8s %-24s %-10s %-10s' % ('', '组', '指标', '实测', '门槛'))
    for g in 闸门:
        print('%-2s %-8s %-24s %-10s %s %s'
              % ('✓' if g['通过'] else '✗', g['组'], g['项'],
                 g['实测'], g['向'], g['门槛']))


def 写StepSummary(报告):
    """GitHub Actions 上把闸门表贴到 job 摘要页，评审不必翻日志。"""
    p = os.environ.get('GITHUB_STEP_SUMMARY')
    if not p:
        return
    结 = 报告['结论']
    行 = ['## 积木库五把尺子 — %s' % ('✅ 全绿' if 结['通过'] else '❌ 有回归'),
          '',
          '提交 `%s` ｜ 块 %s ｜ 耗时 %.1fs'
          % (报告['元信息']['git提交'], 报告['元信息']['块总数'], 结['耗时秒']),
          '', '| | 组 | 指标 | 实测 | 门槛 |', '|---|---|---|---|---|']
    for g in 报告['闸门']:
        行.append('| %s | %s | %s | %s | %s %s |'
                  % ('✅' if g['通过'] else '❌', g['组'], g['项'],
                     g['实测'], g['向'], g['门槛']))
    if not 结['通过']:
        行 += ['', '### 未过闸门', '']
        行 += ['- **%s / %s**：实测 %s，要求 %s %s'
               % (g['组'], g['项'], g['实测'], g['向'], g['门槛'])
               for g in 报告['闸门'] if not g['通过']]
    try:
        with io.open(p, 'a', encoding='utf-8') as f:
            f.write('\n'.join(行) + '\n')
    except Exception:
        pass


def 读旧报告(旧路径):
    """必须在写新报告**之前**读走：默认输出路径和对比路径常常是同一个文件，
    先写后读只会拿到自己刚写的东西，永远显示「完全一致」。"""
    if not 旧路径:
        return None
    try:
        with io.open(旧路径, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print('（对比跳过：%s）' % e)
        return None


def 对比历史(报告, 旧, 旧路径):
    if not 旧:
        return
    print('\n── 对比 %s（%s）──'
          % (os.path.basename(旧路径), 旧.get('元信息', {}).get('时间', '?')))
    变 = 0
    for 组, 项, _向, _默 in _闸门定义:
        a = (旧.get('指标', {}).get(组) or {}).get(项)
        b = (报告.get('指标', {}).get(组) or {}).get(项)
        if a is None or b is None or a == b:
            continue
        变 += 1
        print('  %-8s %-24s %s → %s  (%+.4f)' % (组, 项, a, b, b - a))
    if not 变:
        print('  所有闸门指标与历史完全一致')


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description='积木库五把尺子 CI 闸门')
    ap.add_argument('--并发', type=int, default=4, help='冒烟并行线程数')
    ap.add_argument('--快', action='store_true', help='跳过冒烟（秒级回归）')
    ap.add_argument('--详细', action='store_true', help='打印各尺子原始输出')
    ap.add_argument('--每日', action='store_true',
                    help='另存 报告/ci_daily.json 并追加 报告/ci_history.jsonl')
    ap.add_argument('--对比', default=None, help='与历史报告逐指标对比')
    ap.add_argument('--输出', default=None, help='报告落盘路径（默认 报告/ci_eval.json）')
    ap.add_argument('--允许LLM', action='store_true',
                    help='解除零 token 锁，允许校验器/兜底调用真实 LLM（结果不可复现，慎用）')
    a = ap.parse_args(argv)

    # 零 token 锁：CI 必须可复现且不花钱。
    # 背景（v0.28 实测）：一旦本地 .env 配了真实 api_key，校验器.py 会自动切到「LLM 判定」，
    # 89 条主基准的 兜底理由 变成模型自然语言 → 链路正确率从 1.0 掉到 0.9888，且每跑一次都烧 token。
    # 因此这里默认置 DUAN_NO_LLM=1（load_config 会把 api_key 抹空），除非显式 --允许LLM。
    if not a.允许LLM:
        os.environ['DUAN_NO_LLM'] = '1'

    t0 = time.time()
    旧报告 = 读旧报告(a.对比)          # 先读后写，见 读旧报告 注释
    from 选块 import load_index
    idx = load_index()

    指标, 明细, 原文 = {}, {}, {}
    try:
        print('══ 积木库 CI 闸门 ci_eval v1.0 ══')
        print('块总数 %d ｜ python %s ｜ %s'
              % (len(idx.get('块') or []), platform.python_version(),
                 platform.platform()))

        print('\n[1/6] 真实语料 …', flush=True)
        指标['真实语料'], 明细['真实语料'] = 量_真实语料(idx)
        print('      留出段 concept Hit@1=%s ｜ hybrid Hit@1=%s'
              % (指标['真实语料'].get('留出段_concept_Hit@1'),
                 指标['真实语料'].get('留出段_hybrid_Hit@1')))

        print('[2/6] 扰动集 …', flush=True)
        指标['扰动集'], 明细['扰动集'] = 量_扰动集(idx)
        print('      留出段 concept Hit@1=%s ｜ 全部 Hit@3=%s'
              % (指标['扰动集'].get('留出段_concept_Hit@1'),
                 指标['扰动集'].get('全部_concept_Hit@3')))

        print('[3/6] 主基准 …', flush=True)
        指标['主基准'], 明细['主基准'] = 量_主基准(idx)
        print('      链路正确率=%s ｜ 失败条目=%s'
              % (指标['主基准']['链路正确率'], 指标['主基准']['失败条目数']))

        print('[4/6] 接线与类型闸门 …', flush=True)
        指标['接线'], 明细['接线'], 原文['接线'] = 量_接线()
        print('      总正确率=%s' % 指标['接线']['总正确率'])

        print('[5/6] 契约体检 …', flush=True)
        指标['体检'], 明细['体检'] = 量_体检()
        print('      错误=%s 警告=%s'
              % (指标['体检']['错误数'], 指标['体检']['警告数']))

        if a.快:
            print('[6/6] 冒烟 … 跳过（--快）')
        else:
            print('[6/6] 冒烟（每块真跑一遍，并发 %d）…' % a.并发, flush=True)
            指标['冒烟'], 明细['冒烟'], 原文['冒烟'] = 量_冒烟(a.并发)
            print('      可运行率=%s (%s/%s) ｜ 问题块=%s ｜ 缺依赖=%s'
                  % (指标['冒烟']['可运行率'], 指标['冒烟']['通过'],
                     指标['冒烟']['可判'], 指标['冒烟']['问题块数'],
                     指标['冒烟']['缺依赖数']))
        兜底指标 = 量_兜底()
        if 兜底指标:
            指标['兜底'] = 兜底指标
            print('      兜底闭环：触发率=%s ｜ 沉淀成功率=%s'
                  % (兜底指标['触发率'], 兜底指标['沉淀成功率']))
    except Exception:
        print('\n‼ 尺子执行出错，视同不通过：')
        traceback.print_exc()
        return 2

    闸门 = 判闸门(指标, 载入门槛())
    未过 = [g for g in 闸门 if not g['通过']]
    打印闸门(闸门)

    报告 = {
        '元信息': {
            '时间': time.strftime('%Y-%m-%d %H:%M:%S'),
            'git提交': _git提交(),
            'python': platform.python_version(), '平台': platform.platform(),
            '块总数': len(idx.get('块') or []),
            '模式': '快（跳过冒烟）' if a.快 else '全量',
            '并发': a.并发,
        },
        '指标': 指标,
        '闸门': 闸门,
        '结论': {'通过': not 未过, '未过项': ['%s/%s' % (g['组'], g['项']) for g in 未过],
                '耗时秒': round(time.time() - t0, 1)},
        '明细': 明细,
    }

    目录 = os.path.join(_HERE, '报告')
    os.makedirs(目录, exist_ok=True)
    路径 = a.输出 or os.path.join(目录, 'ci_eval.json')
    with io.open(路径, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(报告, ensure_ascii=False, indent=2))
    print('\n报告：%s' % os.path.relpath(路径, _ROOT))

    if a.每日:
        每日 = os.path.join(目录, 'ci_daily.json')
        with io.open(每日, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(报告, ensure_ascii=False, indent=2))
        史 = os.path.join(目录, 'ci_history.jsonl')
        with io.open(史, 'a', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps({'时间': 报告['元信息']['时间'],
                                'git提交': 报告['元信息']['git提交'],
                                '通过': 报告['结论']['通过'],
                                '未过项': 报告['结论']['未过项'],
                                '指标': {k: v for k, v in 指标.items()}},
                               ensure_ascii=False) + '\n')
        print('每日存档：%s ｜ 历史：%s'
              % (os.path.relpath(每日, _ROOT), os.path.relpath(史, _ROOT)))

    if a.对比:
        对比历史(报告, 旧报告, a.对比)

    if a.详细:
        for k, v in 原文.items():
            print('\n── %s 原始输出 ──\n%s' % (k, v))

    写StepSummary(报告)

    print('\n══ 结论：%s ══ 耗时 %.1fs'
          % ('全部通过 ✓' if not 未过 else
             ('未通过 ✗（%d 项）' % len(未过)), 报告['结论']['耗时秒']))
    for g in 未过:
        # GitHub Actions 注解：直接标红在 PR 的 Checks 里
        print('::error title=积木库回归::%s/%s 实测 %s，要求 %s %s'
              % (g['组'], g['项'], g['实测'], g['向'], g['门槛']))
    已印 = set()
    for g in 未过:                    # 同组只贴一次明细，否则失败越多刷屏越狠
        细 = 明细.get(g['组'])
        if not 细 or g['组'] in 已印:
            continue
        已印.add(g['组'])
        print('\n── %s 掉点明细 ──' % g['组'])
        print(json.dumps(细, ensure_ascii=False, indent=2)[:2000])
    if 未过:
        print('\n完整明细见报告 %s' % os.path.relpath(路径, _ROOT))
    return 1 if 未过 else 0


if __name__ == '__main__':
    raise SystemExit(main())
