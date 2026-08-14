# -*- coding: utf-8 -*-
"""契约级类型化数据流规划 v0.18（类型系统 v2）。

解决 v0.13 链式接线的「多步同类型误接」问题：不再只按「输出类型==输入类型」
就近瞎接，而是维护符号表（变量→类型），对每个输入槽位做：
  1) 结构化类型匹配（类型.py：列表[T]/可选/联合/字典[K,V]，返回 0~1 匹配度）
  2) 按「类型匹配度」降序 —— 精确 1.0 优先于渐进 0.6，这是 v0.18 新增的第一排序键，
     可直接分开 列表[数] 与 列表[文本]，杜绝 求和(切分文本(...)) 这类荒谬接线
  3) 同匹配度时按「参数名 vs 来源块名/描述 的字符相似度」排序
  4) 再相同时取最近上游（确定性，非随机）
  5) 无匹配且提供了默认常量 → 填默认；否则标记 None（不可接，交由兜底生成器）
"""

import os
import sys

_HERE = os.path.abspath(os.path.dirname(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import 类型 as T


def _匹配度(need, have):
    """槽位需要 need、变量拥有 have 时的贴合度（0=接不上）。"""
    try:
        return T.匹配度(need, have)
    except T.类型错误:
        # 契约里写了非法类型串时退化为字符串相等，保证不崩
        return 1.0 if (need or '') == (have or '') else 0.0


def _兼容(need, have):
    return _匹配度(need, have) > 0.0


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
    """从段言字面量推断结构化类型串，如 "[1, 2, 3]" -> "列表[数]"。"""
    try:
        return T.格式化(T.推断(值))
    except Exception:
        return '任意'


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

    # 符号表：(变量名, 类型, 来源块名, 来源描述)。前 n共享 个是共享输入，其后是步骤产物。
    符号表 = []
    n共享 = len(共享)
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
        本步已用 = set()   # 同一步骤内尽量不把同一个变量塞进多个槽位
        回退 = False       # 本步有上游产物可用却只能退回共享输入 ⇒ 链式语义被削弱
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
                合 = _匹配度(ptype, vtype)
                if 合 <= 0:
                    continue
                名分 = max(_名相似(pname, vsrc), _名相似(pname, vdesc),
                          _名相似(pname, vname))
                重复 = 1 if vname in 本步已用 else 0
                if idx < n共享:
                    # 共享输入：按声明序（第 1 个共享通常是主数据），且整体让位于上游产物
                    组, 次 = 1, idx
                else:
                    # 步骤产物：最近上游优先
                    组, 次 = 0, -idx
                候选池.append((vname, 合, 名分, 重复, 组, 次))
            if 候选池:
                # 类型匹配度↓ → 未重复占用 → 上游产物优先 → 名相似度↓ → 位置序
                候选池.sort(key=lambda x: (-x[1], x[3], x[4], -x[2], x[5]))
                选中, _, _, _, 组, _ = 候选池[0]
                if i > 0 and 组 == 1:
                    # 前面有步骤产物，本槽位却只能用共享输入 ⇒ 这不是真正的串联
                    回退 = True
                本步已用.add(选中)
                参数.append(选中)
            else:
                参数.append(None)  # 无匹配且无可默认 → 不可接，交由兜底生成器

        输出 = (ent.get('输出') or {}).get('类型')
        符号表.append((
            '赵果%d' % (i + 1),
            输出,
            s.get('块') or s.get('导出名'),
            s.get('说明', ''),
        ))
        wired.append({**s, '参数': 参数, '_回退': 回退})

    return wired, 符号表


def 回退步(步骤):
    """返回「本该串联却退回共享输入」的步骤块名列表（--链式 时用于提示用户）。"""
    return [s.get('块') or s.get('导出名') for s in 步骤 if s.get('_回退')]


def 不可接(步骤):
    """返回所有含 None 参数的步骤索引（供兜底触发判断）。"""
    bad = []
    for i, s in enumerate(步骤):
        if None in (s.get('参数') or []):
            bad.append(i)
    return bad
