# -*- coding: utf-8 -*-
"""v0.21：把 混合选块 与 计划缓存 接进 组合.py。一次性脚本。"""
import io

p = '组合.py'
s = io.open(p, encoding='utf-8').read()

改 = [
    # 1) 引入模块
    ("from embedding选块 import embedding_select\n",
     "from embedding选块 import embedding_select\n"
     "from 混合选块 import hybrid_select\n"
     "import 计划缓存\n"),

    # 2) 阈值：混合策略沿用概念图阈值（补召回候选自带 0.5 待裁决分，必过阈值，
    #    交由校验器裁决——这正是混合的设计意图）
    ("def _默认阈值(关键词, 语义):\n"
     "    if 关键词:\n"
     "        return 3.0\n"
     "    if 语义:\n"
     "        return 0.12\n"
     "    return 0.06  # embedding 概念图（余弦，已内置 0.08 地板）\n",
     "def _默认阈值(关键词, 语义):\n"
     "    if 关键词:\n"
     "        return 3.0\n"
     "    if 语义:\n"
     "        return 0.12\n"
     "    return 0.06  # embedding 概念图 / 混合（余弦，已内置 0.08 地板）\n"),

    # 3) 函数签名
    ("def 组合(需求, 输入值=\"[1, 2, 3, 4, 5]\", top=3, 语义=False, 关键词=False,\n"
     "        链式=False, 阈值=None, 无兜底=False, 无校验=False, 自动层级=False):\n"
     "    索引 = load_index()\n"
     "    查表 = _全量查表(索引)\n"
     "\n"
     "    # 1) 选块\n"
     "    if 关键词:\n"
     "        候选 = select_blocks(需求, 索引, top=top)\n"
     "    elif 语义:\n"
     "        候选 = semantic_select(需求, 索引, top=top)\n"
     "    else:\n"
     "        候选 = embedding_select(需求, 索引, top=top)\n",

     "def 组合(需求, 输入值=\"[1, 2, 3, 4, 5]\", top=3, 语义=False, 关键词=False,\n"
     "        链式=False, 阈值=None, 无兜底=False, 无校验=False, 自动层级=False,\n"
     "        混合=False, 无缓存=False):\n"
     "    索引 = load_index()\n"
     "    查表 = _全量查表(索引)\n"
     "    策略 = ('关键词' if 关键词 else '语义' if 语义\n"
     "            else '混合' if 混合 else '概念图')\n"
     "    输入类型 = _推断类型(输入值)\n"
     "\n"
     "    # 0) 计划缓存：同一需求 + 同一库 + 同一策略 ⇒ 选块/校验/接线的结论必然相同。\n"
     "    #    库指纹变了（兜底生成新块、契约改动）缓存自动整体作废，不会拿旧方案硬套。\n"
     "    if not 无缓存:\n"
     "        命中 = 计划缓存.读(需求, 索引, 策略=策略, top=top, 阈值=阈值,\n"
     "                        链式=链式, 输入类型=输入类型)\n"
     "        if 命中:\n"
     "            print('[缓存] 命中计划（第 %d 次复用）：%s'\n"
     "                  % (命中['命中次数'], '+'.join(s.get('块', '?')\n"
     "                                              for s in 命中['步骤'])))\n"
     "            共享 = [{'名': '赵料', '值': 输入值, '类型': 输入类型}]\n"
     "            方案 = _造方案(需求, 共享, 命中['步骤'])\n"
     "            候选 = [_条目转候选(查表[n]) for n in 命中['候选'] if n in 查表]\n"
     "            return 方案, 候选\n"
     "\n"
     "    # 1) 选块\n"
     "    if 关键词:\n"
     "        候选 = select_blocks(需求, 索引, top=top)\n"
     "    elif 语义:\n"
     "        候选 = semantic_select(需求, 索引, top=top)\n"
     "    elif 混合:\n"
     "        候选 = hybrid_select(需求, 索引, top=top)\n"
     "    else:\n"
     "        候选 = embedding_select(需求, 索引, top=top)\n"),

    # 4) 返回前写缓存
    ("    # 5) 生成块自动织入 L1+（可选）\n"
     "    if 自动层级:\n"
     "        from 层级生成 import 自动织\n"
     "        建 = 自动织(_HERE)\n"
     "        if 建:\n"
     "            print('[自动层级] 新建 L1 积木：' + '、'.join(建))\n"
     "\n"
     "    return 方案, 候选\n",

     "    # 5) 生成块自动织入 L1+（可选）\n"
     "    if 自动层级:\n"
     "        from 层级生成 import 自动织\n"
     "        建 = 自动织(_HERE)\n"
     "        if 建:\n"
     "            print('[自动层级] 新建 L1 积木：' + '、'.join(建))\n"
     "\n"
     "    # 6) 落缓存。兜底/自动层级刚改过库，这里重新 load 一次让库指纹对上新状态，\n"
     "    #    否则写进去的条目下一次必然因指纹不符而作废。\n"
     "    if not 无缓存:\n"
     "        try:\n"
     "            计划缓存.写(需求, load_index(), 方案['步骤'], 候选, 策略=策略,\n"
     "                      top=top, 阈值=阈值, 链式=链式, 输入类型=输入类型,\n"
     "                      兜底=bool(方案.get('_兜底')))\n"
     "        except Exception as e:\n"
     "            print('[缓存] 写入失败（不影响本次结果）：%s' % e)\n"
     "\n"
     "    return 方案, 候选\n"),

    # 5) CLI 开关
    ("    p.add_argument('--自动层级', action='store_true', help='把 生成/ 积木自动织成 L1+')\n",
     "    p.add_argument('--自动层级', action='store_true', help='把 生成/ 积木自动织成 L1+')\n"
     "    p.add_argument('--混合', action='store_true',\n"
     "                   help='混合选块：概念图召回（空则 TF-IDF 补召回）+ 并列群语义重排')\n"
     "    p.add_argument('--无缓存', action='store_true', help='跳过计划缓存，强制重算')\n"),
]

for a, b in 改:
    if a not in s:
        raise SystemExit('未找到片段：\n%s' % a[:120])
    s = s.replace(a, b)

io.open(p, 'w', encoding='utf-8').write(s)
print('组合.py 已接入 混合选块 + 计划缓存（%d 处）' % len(改))
