# -*- coding: utf-8 -*-
"""接线与类型闸门跑分 v0.18。

基准.json 量化「选对块了吗」，本脚本量化「接对线了吗」。两者互补：
选块决定候选集合，接线决定这些块能否真正拼成可运行的代码。

判定的是 接线.规划 / 不可接 与 组合._可单参调用 的真实行为，不做任何生成、
不触碰 索引.json。

用法：
    python 积木库/评估/接线跑分.py
    python 积木库/评估/接线跑分.py --详细
"""

import argparse
import json
import os
import sys

_HERE = os.path.abspath(os.path.dirname(__file__))
_库根 = os.path.normpath(os.path.join(_HERE, '..'))
if _库根 not in sys.path:
    sys.path.insert(0, _库根)

from 选块 import load_index          # noqa: E402
from 接线 import 规划, 不可接, _推断类型, 回退步  # noqa: E402
from 组合 import _可单参调用, _默认常数   # noqa: E402


def 载入用例(路径=None):
    路径 = 路径 or os.path.join(_HERE, '接线基准.json')
    with open(路径, encoding='utf-8') as f:
        return json.load(f)


def 跑链式(用例, 查表):
    缺 = [n for n in 用例['步骤'] if n not in 查表]
    if 缺:
        return False, '库中无此块：' + '、'.join(缺), None
    共享 = [{'名': '赵料', '值': 用例['共享'], '类型': _推断类型(用例['共享'])}]
    步骤 = [{'块': n, '领域': 查表[n].get('领域', ''), '导出名': 查表[n]['导出名'],
            '路径': 查表[n].get('路径', ''), '说明': 查表[n].get('描述', ''),
            '参数': []} for n in 用例['步骤']]
    wired, _ = 规划(步骤, 共享, 查表, _默认常数())
    坏 = 不可接(wired)
    实际 = '不可接' if 坏 else '可接'
    参数 = [s.get('参数') for s in wired]
    退 = 回退步(wired)
    通过 = (实际 == 用例['期望'])
    if 通过 and 用例.get('期望参数'):
        for got, want in zip(参数, 用例['期望参数']):
            if want is not None and list(got) != list(want):
                return False, '参数绑定 %s ≠ 期望 %s' % (参数, 用例['期望参数']), 参数
    if 通过 and '期望回退' in 用例 and 退 != list(用例['期望回退']):
        return False, '回退标记 %s ≠ 期望 %s' % (退 or '无', 用例['期望回退']), 参数
    return 通过, '实际=%s%s' % (实际, ('　回退=' + '、'.join(退)) if 退 else ''), 参数


def 跑闸门(用例, 查表):
    缺 = [n for n in 用例['候选'] if n not in 查表]
    if 缺:
        return False, '库中无此块：' + '、'.join(缺), None
    输入类型 = _推断类型(用例['输入'])
    可用 = [n for n in 用例['候选'] if _可单参调用(查表[n], 输入类型)]
    期望 = list(用例['期望可用'])
    通过 = 可用 == [n for n in 用例['候选'] if n in 期望]
    return 通过, '输入类型=%s 可用=%s' % (输入类型, 可用 or '空'), 可用


def _降级为粗类型(查表):
    """把 列表[T]/字典[K,V] 压回 v0.17 的裸标签，用于量化类型系统 v2 的收益。

    裸「列表」在类型 v2 里等价于 列表[任意]，匹配度 0.6 > 0 ⇒ 任何列表都能互接，
    正是 v0.17 的实际行为。
    """
    import copy
    粗 = {}
    for 名, b in 查表.items():
        b = copy.deepcopy(b)
        槽 = list(b.get('输入') or [])
        out = b.get('输出')
        if isinstance(out, dict):
            槽 = 槽 + [out]
        for p in 槽:
            t = p.get('类型') or ''
            if t.startswith('列表['):
                p['类型'] = '列表'
            elif t.startswith('字典['):
                p['类型'] = '字典'
        粗[名] = b
    return 粗


def 跑(详细=False, 路径=None, 粗类型=False):
    doc = 载入用例(路径)
    查表 = {b['名称']: b for b in (load_index().get('块') or [])}
    if 粗类型:
        查表 = _降级为粗类型(查表)
        print('[对照模式] 契约已降级为 v0.17 粗类型（列表/字典 不带元素类型）\n')
    链式, 闸门, 失败 = [], [], []

    for u in doc['用例']:
        if '步骤' in u:
            ok, 说明, 细节 = 跑链式(u, 查表)
            链式.append(ok)
        else:
            ok, 说明, 细节 = 跑闸门(u, 查表)
            闸门.append(ok)
        if not ok:
            失败.append((u, 说明))
        if 详细:
            print('%s %-5s %s' % ('✓' if ok else '✗', u['编号'], 说明))

    n链, n闸 = len(链式), len(闸门)
    p链 = sum(链式) / n链 if n链 else 0.0
    p闸 = sum(闸门) / n闸 if n闸 else 0.0
    总 = (sum(链式) + sum(闸门)) / (n链 + n闸) if (n链 + n闸) else 0.0

    print('══ 接线 / 类型闸门跑分 ══')
    print('块总数 %d　用例 %d（链式 %d / 闸门 %d）' % (len(查表), n链 + n闸, n链, n闸))
    print('── 链式接线正确率 ──  %.4f  (%d/%d)' % (p链, sum(链式), n链))
    print('── 类型闸门正确率 ──  %.4f  (%d/%d)' % (p闸, sum(闸门), n闸))
    print('── 总正确率 ──        %.4f' % 总)
    if 失败:
        print('\n── 失败用例（%d）──' % len(失败))
        for u, 说明 in 失败:
            期 = u.get('期望') or ('可用=' + '、'.join(u.get('期望可用', [])))
            print('  %-5s %s' % (u['编号'], 说明))
            print('        期望：%s ｜ %s' % (期, u.get('理由', '')))
    return {'链式': p链, '闸门': p闸, '总': 总,
            '失败': [u['编号'] for u, _ in 失败]}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--详细', action='store_true')
    p.add_argument('--基准', default=None)
    p.add_argument('--粗类型', action='store_true',
                   help='对照模式：用 v0.17 粗类型契约跑，量化类型系统 v2 的收益')
    a = p.parse_args()
    r = 跑(详细=a.详细, 路径=a.基准, 粗类型=a.粗类型)
    raise SystemExit(0 if not r['失败'] else 1)
