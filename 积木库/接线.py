# -*- coding: utf-8 -*-
"""契约级类型化数据流规划 v0.14。

解决 v0.13 链式接线的「多步同类型误接」问题：不再只按「输出类型==输入类型」
就近瞎接，而是维护符号表（变量→类型），对每个输入槽位做：
  1) 类型精确匹配（数/文本/列表/逻辑/字典 互不兼容）
  2) 在匹配变量中按「参数名 vs 来源块名/描述 的字符相似度」排序
  3) 相似度相同时取最近上游（确定性，非随机）
  4) 无匹配且提供了默认常量 → 填默认；否则标记 None（不可接，交由兜底生成器）
"""


# 类型兼容性：键=目标类型，值=可接纳的源类型集合（v0.14 仅精确相等）
_兼容表 = {
    '数': {'数'},
    '文本': {'文本'},
    '列表': {'列表'},
    '逻辑': {'逻辑'},
    '字典': {'字典'},
}


def _兼容(need, have):
    return (need or '') in _兼容表.get(have or '', set())


def _名相似(a, b):
    a, b = a or '', b or ''
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    inter = sa & sb
    if not inter:
        return 0.0
    return len(inter) / max(len(sa), len(sb), 1)


def _推断类型(值):
    s = (值 or '').strip()
    if s.startswith('['):
        return '列表'
    if s.startswith('"') or s.startswith("'"):
        return '文本'
    try:
        float(s)
        return '数'
    except Exception:
        return '文本'


def _查表条目(s, 查表):
    for key in (s.get('块'), s.get('导出名'), s.get('名称')):
        if key and key in 查表:
            return 查表[key]
    return None


def 规划(步骤, 共享=None, 查表=None, 默认常量=None):
    """对每个步骤计算每个输入参数应绑定的变量名。

    返回 (wired_steps, 符号表)。wired_steps 为带 参数 字段的步骤副本；
    符号表 为 [(变量名, 类型, 来源块名, 来源描述), ...] 供调试。
    若某参数无匹配且无默认，对应位置为 None（不可接，触发兜底）。
    """
    共享 = 共享 or []
    默认常量 = 默认常量 or {}
    查表 = 查表 or {}

    # 符号表：(变量名, 类型, 来源块名, 来源描述)
    符号表 = []
    for s in 共享:
        符号表.append((
            s['名'],
            s.get('类型') or _推断类型(s.get('值', '')),
            s.get('说明', '共享'),
            '共享输入',
        ))

    wired = []
    for i, s in enumerate(步骤):
        # 显式参数覆盖（手写方案优先）
        if s.get('参数'):
            ent = _查表条目(s, 查表) or {}
            输出 = (ent.get('输出') or {}).get('类型')
            符号表.append((
                '赵果%d' % (i + 1),
                输出,
                s.get('块') or s.get('导出名'),
                s.get('说明', ''),
            ))
            wired.append({**s, '参数': list(s['参数'])})
            continue

        ent = _查表条目(s, 查表) or {}
        输入 = ent.get('输入') or []
        参数 = []
        for p in 输入:
            pname = p.get('名') or p.get('名称')
            ptype = p.get('类型')
            # 配置型参数：参数名命中默认常量 → 配置常量优先于数据流变量，
            # 避免把「每页」之类配置误接成上游的数据（如求和结果）。
            if pname in 默认常量:
                参数.append(str(默认常量[pname]))
                continue
            候选池 = []
            for idx, (vname, vtype, vsrc, vdesc) in enumerate(符号表):
                if _兼容(ptype, vtype):
                    名分 = max(_名相似(pname, vsrc), _名相似(pname, vdesc))
                    候选池.append((vname, 名分, idx))
            if 候选池:
                # 先按名相似度降序，再按出现序号降序（最近上游优先）
                候选池.sort(key=lambda x: (-x[1], -x[2]))
                参数.append(候选池[0][0])
            else:
                参数.append(None)  # 无匹配且无可默认 → 不可接，交由兜底生成器

        输出 = (ent.get('输出') or {}).get('类型')
        符号表.append((
            '赵果%d' % (i + 1),
            输出,
            s.get('块') or s.get('导出名'),
            s.get('说明', ''),
        ))
        wired.append({**s, '参数': 参数})

    return wired, 符号表


def 不可接(步骤):
    """返回所有含 None 参数的步骤索引（供兜底触发判断）。"""
    bad = []
    for i, s in enumerate(步骤):
        if None in (s.get('参数') or []):
            bad.append(i)
    return bad