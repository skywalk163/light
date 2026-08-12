# -*- coding: utf-8 -*-
"""光明积木组合总入口 v0.16：需求 + 输入 → 选块 →（契约级接线）→ 校验 → 内联粘合 → 运行。

v0.16 变更（更细语义召回 + 真实 LLM 校验）：
  - embedding 选块升级：概念图向量（默认，零依赖）之际，若装了 sentence_transformers
    自动改用真·句向量（更细语义召回，块向量磁盘缓存）；--real 可强制走真向量
  - LLM 校验器（校验器.validate）作为运行前第二道闸：本地概念交集 + 真实 LLM 判定，
    系统提示内置 few-shot 覆盖『中文转拼音 vs 数字转中文』等细微错配；传给 LLM 的候选
    已富化含输入/输出类型
  - 生成/ 积木自动织入 L1+（层级生成.自动织，--自动层级 触发）

零 token 为常态：选块/校验/接线/层级均为本地；仅『兜底生成』在本地规则也覆盖不了、
且配置了 LLM key 时，才调用一次模型。无 key 时本地规则已覆盖 方差/中位数/绝对值/
斐波那契/阶乘/素数/累加和 等常见库外意图。

「选不准」触发兜底的三类信号：
  1) 无候选（embedding 概念图相似度≈0，即需求库内无对应概念）
  2) top 分数低于阈值，或 契约级接线不可接
  3) 校验器判定 MISMATCH（本地概念无交集 / LLM 认为组合不满足需求）
真实 LLM 仅在以上且本地规则也覆盖不了时才被调用。
"""

import argparse
import os
import sys
import subprocess

_HERE = os.path.abspath(os.path.dirname(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, '..'))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from 选块 import select_blocks, load_index
from 粘合 import synthesize
from 语义选块 import semantic_select
from embedding选块 import embedding_select
from 校验器 import validate
from 接线 import 规划, 不可接, _推断类型
from 兜底生成器 import generate_block, 注册, local_rule_block


def _全量查表(索引):
    return {b['名称']: b for b in (索引.get('块') or [])}


def _默认常数():
    """链式接线遇同类型缺口时填入的常识默认值（配置型参数优先于数据流变量）。"""
    return {'每页': 10, '每页大小': 10, '页大小': 10, '步': 1, '起': 0, '起值': 0}


def _默认阈值(关键词, 语义):
    if 关键词:
        return 3.0
    if 语义:
        return 0.12
    return 0.06  # embedding 概念图（余弦，已内置 0.08 地板）


def _建步骤(选中):
    return [{
        '块': c['名称'], '领域': c['领域'], '导出名': c['导出名'],
        '路径': c.get('路径', ''), '说明': c['描述'], '参数': [],
    } for c in 选中]


def _造方案(需求, 共享, 步骤):
    return {
        '需求': 需求,
        '共享': 共享,
        '步骤': 步骤,
        '打印': ['赵果%d' % (i + 1) for i in range(len(步骤))],
    }


def _兜底(需求, 索引, 候选, 输入值, 块=None, 理由=''):
    print('[兜底] %s，调用生成器：%s' % (理由 or '选块未命中', 需求))
    blk = 块 if 块 is not None else generate_block(需求, 索引, 候选=候选, 库根=_HERE)
    if not blk:
        print('[兜底] 本地规则也无法生成，需配置真实 LLM（见 llm_config.json）')
        return None
    注册(blk, 库根=_HERE)
    blk = dict(blk)
    blk['分数'] = 0.0
    print('[兜底] 已生成并注册新积木：%s（%s）' % (blk['名称'], blk.get('路径')))

    查表 = _全量查表(load_index())
    步骤 = [{
        '块': blk['名称'], '领域': blk.get('领域', '生成'),
        '导出名': blk['导出名'], '路径': blk.get('路径', ''),
        '说明': blk.get('描述', ''), '参数': [],
    }]
    值类型 = _推断类型(输入值)
    有效值 = 输入值
    if 值类型 == '文本' and not (输入值.startswith('"') or 输入值.startswith("'")):
        有效值 = '"' + 输入值 + '"'
    共享 = [{'名': '赵料', '值': 有效值, '类型': 值类型}]
    wired, _ = 规划(步骤, 共享, 查表, _默认常数())
    步骤 = wired
    if 不可接(步骤):
        for s in 步骤:
            s['参数'] = ['赵料']
    方案 = _造方案(需求, 共享, 步骤)
    return 方案, [blk]


def 组合(需求, 输入值="[1, 2, 3, 4, 5]", top=3, 语义=False, 关键词=False,
        链式=False, 阈值=None, 无兜底=False, 无校验=False, 自动层级=False):
    索引 = load_index()
    查表 = _全量查表(索引)

    # 1) 选块 — 使用 D5(领域分类) + D1(Tfidf 补充) 增强选块器
    from _ml_selector import 统一选块
    候选 = 统一选块(需求, 索引, top=top, 关键词=关键词, 语义=语义)

    # 2) 是否需要兜底
    需要兜底 = False
    理由 = ''
    if not 候选:
        需要兜底, 理由 = True, '无候选（需求未命中任何库内概念）'
    else:
        分数 = 候选[0]['分数']
        if 阈值 is None:
            阈值 = _默认阈值(关键词, 语义)
        if 分数 < 阈值:
            需要兜底, 理由 = True, 'top 分数 %.3f 低于阈值 %.2f' % (分数, 阈值)
        elif not 无校验:
            # 校验器需要候选的完整契约（输入/输出类型），从全量查表还原
            候选_full = [查表.get(c['名称']) or c for c in 候选]
            v = validate(需求, 候选_full)
            if not v['通过']:
                需要兜底, 理由 = True, '校验未过：' + v['理由']

    if 需要兜底:
        if 无兜底:
            print('已关闭兜底，无法生成方案：' + 需求)
            return None
        res = _兜底(需求, 索引, 候选, 输入值, 理由=理由)
        if not res:
            return None
        方案, 候选 = res
    else:
        # 3) 正常装配
        选中 = 候选[:top]
        步骤 = _建步骤(选中)
        值类型 = _推断类型(输入值)
        # 文本类型且无引号包裹时自动加引号
        有效值 = 输入值
        if 值类型 == '文本' and not (输入值.startswith('"') or 输入值.startswith("'")):
            有效值 = '"' + 输入值 + '"'
        共享 = [{'名': '赵料', '值': 有效值, '类型': 值类型}]
        if 链式:
            wired, _ = 规划(步骤, 共享, 查表, _默认常数())
            步骤 = wired
            if 不可接(步骤):
                if 无兜底:
                    print('接线不可接且已关闭兜底：' + 需求)
                    return None
                res = _兜底(需求, 索引, 候选, 输入值, 理由='契约级接线不可接')
                if not res:
                    return None
                方案, 候选 = res
            else:
                方案 = _造方案(需求, 共享, 步骤)
        else:
            for s in 步骤:
                s['参数'] = ['赵料']
            方案 = _造方案(需求, 共享, 步骤)

        # 4) 能力缺失预检（零 token）：库缺失能力命中本地规则 → 走兜底
        if not 无兜底:
            lr = local_rule_block(需求)
            if lr and lr['名称'] not in [c['名称'] for c in 候选]:
                res = _兜底(需求, 索引, 候选, 输入值, 块=lr, 理由='能力缺失（本地规则）')
                if res:
                    方案, 候选 = res

    # 5) 生成块自动织入 L1+（可选）
    if 自动层级:
        from 层级生成 import 自动织
        建 = 自动织(_HERE)
        if 建:
            print('[自动层级] 新建 L1 积木：' + '、'.join(建))

    return 方案, 候选


def _cli(argv=None):
    p = argparse.ArgumentParser(
        description='光明积木组合 v0.16（embedding 真向量选块 + LLM 校验器 + 生成块自动层级）')
    p.add_argument('需求', help='自然语言需求文本')
    p.add_argument('--输入', default='[1, 2, 3, 4, 5]', help='共享输入（光明表达式）')
    p.add_argument('--top', type=int, default=3, help='选块候选数（= 步骤数）')
    p.add_argument('--关键词', action='store_true', help='用 v0 关键词选块（字符重叠）')
    p.add_argument('--语义', action='store_true', help='用语义选块（TF-IDF+同义词）')
    p.add_argument('--链式', action='store_true', help='契约级精确接线（按类型+参数名）')
    p.add_argument('--阈值', type=float, default=None, help='触发兜底的分数阈值')
    p.add_argument('--无兜底', action='store_true', help='关闭 LLM 兜底')
    p.add_argument('--无校验', action='store_true', help='跳过运行前校验器')
    p.add_argument('--自动层级', action='store_true', help='把 生成/ 积木自动织成 L1+')
    p.add_argument('-o', '--输出', default=os.path.join(_HERE, '组合结果.light'))
    args = p.parse_args(argv)

    res = 组合(args.需求, 输入值=args.输入, top=args.top,
              语义=args.语义, 关键词=args.关键词, 链式=args.链式,
              阈值=args.阈值, 无兜底=args.无兜底, 无校验=args.无校验,
              自动层级=args.自动层级)
    if not res:
        print('未能生成方案：' + args.需求)
        return 1
    方案, 候选 = res
    选块法 = '关键词' if args.关键词 else ('语义' if args.语义 else 'embedding')
    是兜底 = any(c.get('领域') == '生成' for c in 候选)
    print('选块候选（%s%s）：' % (选块法, ' + 兜底生成' if 是兜底 else ''))
    for c in 候选:
        print('  %s（%s）分数=%s' % (c['名称'], c['领域'], c['分数']))

    code = synthesize(方案)
    with open(args.输出, 'w', encoding='utf-8') as f:
        f.write(code)
    print('\n已生成：' + args.输出)

    duan = os.path.join(_REPO, 'cli', 'light.py')
    print('\n── 运行结果 ──')
    rc = subprocess.run([sys.executable, duan, 'run', args.输出]).returncode
    if rc != 0 and not args.无兜底:
        print('\n[提示] 组合运行失败，可能所选积木并不完全满足需求（语义错配）。'
              '配置真实 LLM（llm_config.json）后，校验器/兜底生成将能处理此类需求。')
    return rc


if __name__ == '__main__':
    raise SystemExit(_cli())