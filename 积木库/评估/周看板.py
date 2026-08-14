# -*- coding: utf-8 -*-
"""运行日志周看板（Q4 计划 月2）—— 可观测性聚合工具。

读取 `评估/运行日志.jsonl`（每行一条 JSON），按 ISO 周聚合关键指标，
产出零依赖自包含 HTML 看板（`周看板.html`）+ Markdown 报告（`周看板报告.md`）。

设计约定（与 兜底跑分.py 一致）：只读、零依赖、对稀疏/空数据健壮。
  · 逐行 json.loads 容错：坏行跳过并计数，绝不崩溃。
  · 时间定位：优先找任何时间/日期字段（时间戳/时间/日期/date/time/timestamp/
    创建时间/运行时间），可解析则按 ISO 周聚合；并回退扫描 备注 里的日期。
  · 若日志无任何可用时间字段：按行顺序「每 7 条算一周」作伪周（报告中注明）。
  · 字段缺失/格式异常一律用 .get() 容错，缺失即视为未记录。
  · 选中块/分数字段若日志未记录，看板该项标注「日志未记录」并跳过聚合。

仅写本文件 + 周看板.html + 周看板报告.md，绝不修改引擎/索引/组合.py 等任何代码。

用法（受管 python，cwd = 积木库）：
  python 评估/周看板.py
"""

import json
import os
import re
import datetime

_HERE = os.path.abspath(os.path.dirname(__file__))
_默认日志 = os.path.join(_HERE, '运行日志.jsonl')
_输出_HTML = os.path.join(_HERE, '周看板.html')
_输出_MD = os.path.join(_HERE, '周看板报告.md')

_时间候选键 = ('时间戳', '时间', '日期', 'date', 'time', 'timestamp', '创建时间', '运行时间', '写入时间')
_伪周每几条 = 7

# 选中块 / 分数的候选字段名（日志未记录则跳过并标注）
_选中块候选键 = ('选中块', '选中块名', '命中块', '选中块名列表', 'selected_block', 'selected_blocks')
_分数候选键 = ('分数', '平均分', 'score', '语义分', '得分')


def 读日志(路径):
    """逐行解析 jsonl，返回 (行列表, 坏行数)。文件缺失返回 ([], 0)。"""
    if not os.path.isfile(路径):
        return [], 0
    行 = []
    坏行 = 0
    with open(路径, encoding='utf-8') as f:
        for 原文 in f:
            原文 = 原文.strip()
            if not 原文:
                continue
            try:
                行.append(json.loads(原文))
            except Exception:
                坏行 += 1
    return 行, 坏行


def _解析时间(值):
    """尽量把各种时间表示解析成 datetime；失败返回 None。"""
    if 值 is None or 值 == '':
        return None
    if isinstance(值, (int, float)):
        # 可能是 unix 秒/毫秒
        try:
            if 值 > 1e12:  # 毫秒
                值 = 值 / 1000.0
            return datetime.datetime.fromtimestamp(值)
        except Exception:
            return None
    s = str(值).strip()
    if not s:
        return None
    # 常见格式
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M',
                '%Y/%m/%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d',
                '%Y年%m月%d日', '%Y-%m-%dT%H:%M:%SZ'):
        try:
            return datetime.datetime.strptime(s[:len(datetime.datetime.now().strftime(fmt)) + 5], fmt)
        except Exception:
            continue
    # 备注里挖日期：2026-08-13 / 2026/08/13
    m = re.search(r'(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})', s)
    if m:
        try:
            return datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            return None
    return None


def _取周标签(行, 序号, 伪周模式):
    """返回 (周标签, 是否真实时间)。"""
    if 伪周模式:
        return ('伪周%d' % (序号 // _伪周每几条 + 1), False)
    真实 = None
    for k in _时间候选键:
        if k in 行 and 行[k]:
            真实 = _解析时间(行[k])
            if 真实:
                break
    if 真实 is None and 行.get('备注'):
        真实 = _解析时间(行['备注'])
    if 真实 is None:
        return ('未标注时间', False)
    iso = 真实.isocalendar()
    return ('%d-W%02d' % (iso[0], iso[1]), True)


def _取token(行):
    """兼容 dict / number / null，返回总 token 数或 None。"""
    u = 行.get('token成本')
    if isinstance(u, dict):
        n = u.get('total_tokens')
        if n:
            return n
        p = u.get('prompt_tokens') or 0
        c = u.get('completion_tokens') or 0
        if p or c:
            return p + c
        return None
    if isinstance(u, (int, float)):
        return u
    return None


def _缓存命中(行):
    u = 行.get('token成本')
    if isinstance(u, dict):
        return u.get('prompt_cache_hit_tokens') or 0
    return None


def _真值(行, 键):
    v = 行.get(键)
    return v is True or (isinstance(v, str) and v.strip() in ('true', 'True', '1', '是'))


def _top(计数: dict, n=5):
    序 = sorted(计数.items(), key=lambda kv: (-kv[1], str(kv[0])))
    return 序[:n]


def 聚合(行列表):
    """按周聚合，返回 (周字典, 模式信息)。"""
    if not 行列表:
        return {}, {'伪周模式': False, '真实周': False, '有坏时间': False}

    # 先判断是否真的有时间字段可用
    真实时间可用 = False
    for r in 行列表:
        for k in _时间候选键:
            if k in r and r[k] and _解析时间(r[k]):
                真实时间可用 = True
                break
        if not 真实时间可用 and r.get('备注'):
            if _解析时间(r['备注']):
                真实时间可用 = True
        if 真实时间可用:
            break

    伪周模式 = not 真实时间可用
    周 = {}
    for i, r in enumerate(行列表):
        标签, _ = _取周标签(r, i, 伪周模式)
        d = 周.setdefault(标签, {
            '运行总数': 0, '成功数': 0,
            '兜底数': 0, '来源': {}, 'token列表': [], '总token': 0,
            '沉淀数': 0, '耗时列表': [], '能力': {}, '分类': {},
            '选中块计数': {}, '分数列表': [], '缓存命中': 0,
        })
        d['运行总数'] += 1
        if _真值(r, '成功'):
            d['成功数'] += 1
        if _真值(r, '是兜底'):
            d['兜底数'] += 1
            来源 = r.get('兜底来源')
            if 来源 is None or 来源 == '':
                来源 = 'null'
            来源 = str(来源)
            d['来源'][来源] = d['来源'].get(来源, 0) + 1
        if _真值(r, '成功沉淀'):
            d['沉淀数'] += 1
        t = _取token(r)
        if t is not None:
            d['token列表'].append(t)
            d['总token'] += t
        c = _缓存命中(r)
        if c:
            d['缓存命中'] += c
        h = r.get('耗时ms')
        if isinstance(h, (int, float)):
            d['耗时列表'].append(h)
        能力 = r.get('期望能力')
        if 能力:
            d['能力'][str(能力)] = d['能力'].get(str(能力), 0) + 1
        分类 = r.get('分类')
        if 分类:
            d['分类'][str(分类)] = d['分类'].get(str(分类), 0) + 1
        for k in _选中块候选键:
            块 = r.get(k)
            if 块 is None:
                continue
            if isinstance(块, list):
                for x in 块:
                    if x:
                        d['选中块计数'][str(x)] = d['选中块计数'].get(str(x), 0) + 1
            elif 块 != '':
                d['选中块计数'][str(块)] = d['选中块计数'].get(str(块), 0) + 1
            break
        for k in _分数候选键:
            s = r.get(k)
            if isinstance(s, (int, float)):
                d['分数列表'].append(s)
            break

    # 计算派生率
    for 标签, d in 周.items():
        n = d['运行总数']
        d['成功率'] = (d['成功数'] / n) if n else None
        d['兜底率'] = (d['兜底数'] / n) if n else None
        d['沉淀率'] = (d['沉淀数'] / n) if n else None
        d['平均token'] = (sum(d['token列表']) / len(d['token列表'])) if d['token列表'] else None
        d['平均耗时'] = (sum(d['耗时列表']) / len(d['耗时列表'])) if d['耗时列表'] else None
        d['Top能力'] = _top(d['能力'])
        d['Top分类'] = _top(d['分类'])
        d['Top选中块'] = _top(d['选中块计数'])
        d['平均分'] = (sum(d['分数列表']) / len(d['分数列表'])) if d['分数列表'] else None

    # 排序：伪周按数字，真实周按字符串
    def _周序(k):
        if 伪周模式:
            m = re.search(r'(\d+)', k)
            return int(m.group(1)) if m else 0
        return k
    周序 = dict(sorted(周.items(), key=lambda kv: _周序(kv[0])))

    日志含选中块 = any(周[d]['Top选中块'] for d in 周)
    日志含分数 = any(周[d]['平均分'] is not None for d in 周)
    日志含token = any(周[d]['平均token'] is not None for d in 周)
    日志含耗时 = any(周[d]['平均耗时'] is not None for d in 周)
    return 周序, {
        '伪周模式': 伪周模式,
        '真实周': 真实时间可用,
        '日志含选中块': 日志含选中块,
        '日志含分数': 日志含分数,
        '日志含token': 日志含token,
        '日志含耗时': 日志含耗时,
    }


# ============================ HTML 生成 ============================

_CSS = """
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
       margin: 0; background: #0f1420; color: #e6edf3; }
.wrap { max-width: 1100px; margin: 0 auto; padding: 28px 20px 60px; }
h1 { font-size: 24px; margin: 0 0 4px; }
.sub { color: #8b98a5; font-size: 13px; margin-bottom: 18px; }
.note { background: #1b2433; border-left: 3px solid #f0b429; padding: 10px 14px;
        border-radius: 6px; font-size: 13px; color: #d7c48a; margin-bottom: 18px; }
.empty { text-align: center; padding: 80px 20px; color: #8b98a5; }
.empty .big { font-size: 18px; color: #c9d4e0; margin-bottom: 8px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px,1fr));
         gap: 12px; margin-bottom: 24px; }
.card { background: #161d2b; border: 1px solid #232c3d; border-radius: 10px;
        padding: 14px 16px; }
.card .k { font-size: 12px; color: #8b98a5; }
.card .v { font-size: 26px; font-weight: 600; margin-top: 4px; }
.card .v small { font-size: 13px; color: #8b98a5; font-weight: 400; }
.section { background: #161d2b; border: 1px solid #232c3d; border-radius: 10px;
           padding: 16px 18px; margin-bottom: 20px; }
.section h2 { font-size: 16px; margin: 0 0 12px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 720px) { .grid2 { grid-template-columns: 1fr; } }
.metric { margin-bottom: 14px; }
.metric .lab { font-size: 13px; color: #c9d4e0; margin-bottom: 4px; display:flex; justify-content:space-between; }
.metric .lab .tag { font-size: 11px; color:#7a8694; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid #232c3d; }
th { color: #8b98a5; font-weight: 500; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.muted { color:#7a8694; }
.bar { display:inline-block; height:8px; border-radius:4px; background:#3b82f6; vertical-align:middle; margin-right:6px; }
.pill { display:inline-block; padding:1px 8px; border-radius: 10px; font-size:12px;
        background:#1f2b3d; margin:2px 4px 2px 0; }
footer { color:#5c6675; font-size:12px; margin-top:30px; text-align:center; }
"""


def _svg_line(标题, 数据, 单位='', 百分比=False, 颜色='#3b82f6'):
    """数据: list of (标签, 数值|None)。返回 SVG 字符串。"""
    W, H = 340, 150
    pad_l, pad_r, pad_t, pad_b = 8, 8, 22, 24
    if not 数据:
        return '<svg width="%d" height="%d"></svg>' % (W, H)
    点 = [(i, v) for i, (lb, v) in enumerate(数据) if v is not None]
    if not 点:
        return '<svg width="%d" height="%d"><text x="10" y="80" fill="#7a8694" font-size="12">无数据</text></svg>' % (W, H)
    ys = [v for _, v in 点]
    vmax = max(ys) if 百分比 else (max(ys) * 1.1 or 1)
    vmin = 0 if 百分比 else min(0, min(ys))
    if vmax == vmin:
        vmax = vmin + 1
    n = len(数据)
    def X(i): return pad_l + (W - pad_l - pad_r) * (i / max(1, n - 1))
    def Y(v): return pad_t + (H - pad_t - pad_b) * (1 - (v - vmin) / (vmax - vmin))
    # 网格线
    grid = ''
    for g in range(0, 5):
        gv = vmin + (vmax - vmin) * g / 4
        gy = Y(gv)
        grid += '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#232c3d" stroke-width="1"/>' % (pad_l, gy, W - pad_r, gy)
        txt = ('%.0f%%' % gv) if 百分比 else ('%.0f' % gv)
        grid += '<text x="%d" y="%.1f" fill="#5c6675" font-size="9">%s</text>' % (pad_l, gy - 2, txt)
    # 折线
    pts = ' '.join('%.1f,%.1f' % (X(i), Y(v)) for i, v in 点)
    # 圆点 + 末值
    dots = ''
    last_i, last_v = 点[-1]
    dots += '<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/>' % (X(last_i), Y(last_v), 颜色)
    last_txt = ('%.1f%%' % last_v) if 百分比 else ('%.1f%s' % (last_v, 单位))
    dots += '<text x="%.1f" y="%.1f" fill="%s" font-size="11" text-anchor="end">%s</text>' % (X(last_i) - 4, Y(last_v) - 6, 颜色, last_txt)
    svg = ('<svg width="%d" height="%d" viewBox="0 0 %d %d">'
           '<text x="%d" y="14" fill="#c9d4e0" font-size="12">%s</text>%s'
           '<polyline points="%s" fill="none" stroke="%s" stroke-width="2"/>%s'
           '</svg>') % (W, H, W, H, pad_l, 标题, grid, pts, 颜色, dots)
    return svg


def _svg_bar(标题, 数据, 单位=''):
    """数据: list of (标签, 数值|None)。横向条形。"""
    if not 数据:
        return '<svg></svg>'
    有效 = [(lb, v) for lb, v in 数据 if v is not None]
    if not 有效:
        return '<svg><text fill="#7a8694" font-size="12">无数据</text></svg>'
    mx = max(v for _, v in 有效) or 1
    rows = []
    y = 6
    for lb, v in 有效:
        w = max(2, int(120 * v / mx))
        rows.append('<text x="0" y="%d" fill="#c9d4e0" font-size="11">%s</text>' % (y + 9, str(lb)[:10]))
        rows.append('<rect x="95" y="%d" width="%d" height="11" rx="3" fill="#3b82f6"/>' % (y, w))
        rows.append('<text x="%d" y="%d" fill="#8b98a5" font-size="10">%s%s</text>' % (95 + w + 4, y + 10, ('%.0f' % v), 单位))
        y += 20
    H = y + 4
    return '<svg width="240" height="%d"><text x="0" y="-0" fill="#c9d4e0" font-size="12">%s</text>%s</svg>' % (H, 标题, ''.join(rows))


def _生成_html(周, 信息, 总行, 坏行, 日志路径, 生成时间):
    if not 周:
        html = ('<!doctype html><html lang="zh"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>运行日志周看板</title><style>' + _CSS.replace('%', '%%') + '</style></head><body><div class="wrap">'
                '<h1>运行日志周看板</h1>'
                '<div class="sub">生成时间：%s ｜ 数据源：%s</div>'
                '<div class="empty"><div class="big">暂无运行日志数据</div>'
                '<div>看板将在真实 LLM 跑分产生日志后自动填充。<br>'
                '运行 <code>兜底首跑.py --保留</code> 即可写入 运行日志.jsonl。</div></div>'
                '<footer>段言积木库 · 可观测性周看板（零依赖 · 可离线打开）</footer>'
                '</div></body></html>') % (生成时间, os.path.basename(日志路径))
        return html

    注释 = []
    if 信息['伪周模式']:
        注释.append('日志无可用时间字段，已按行顺序「每 %d 条算一周」生成伪周（仅供趋势占位）。' % _伪周每几条)
    else:
        注释.append('已按 ISO 周聚合（检测到时间/日期字段）。')
    if 坏行:
        注释.append('共 %d 行坏数据已跳过。' % 坏行)
    if not 信息['日志含token']:
        注释.append('日志未记录 token 成本，相关趋势图省略。')
    if not 信息['日志含耗时']:
        注释.append('日志未记录耗时，相关趋势图省略。')
    if not 信息['日志含选中块']:
        注释.append('日志未记录「选中块」，该项标注为「日志未记录」。')
    if not 信息['日志含分数']:
        注释.append('日志未记录「分数」，该项标注为「日志未记录」。')

    周序 = list(周.keys())
    # 汇总卡片（全局）
    总运行 = sum(周[d]['运行总数'] for d in 周)
    总成功 = sum(周[d]['成功数'] for d in 周)
    总兜底 = sum(周[d]['兜底数'] for d in 周)
    总沉淀 = sum(周[d]['沉淀数'] for d in 周)
    总token = sum(周[d]['总token'] for d in 周)
    # 全局平均（按有数据的周做简单平均展示用，明细更准）
    成功率全 = (总成功 / 总运行) if 总运行 else 0
    兜底率全 = (总兜底 / 总运行) if 总运行 else 0
    沉淀率全 = (总沉淀 / 总运行) if 总运行 else 0
    tok均值 = (总token / 总运行) if 总运行 else None
    # 平均耗时（全量样本）
    所有耗时 = [h for d in 周.values() for h in [] ]  # 占位
    所有耗时 = []
    for d in 周.values():
        # 用 平均耗时 * 运行总数 近似？没有原始样本，用周均值再平均
        pass
    均耗时全 = None
    耗时周 = [(lb, 周[lb]['平均耗时']) for lb in 周序]
    有耗时 = [v for _, v in 耗时周 if v is not None]
    if 有耗时:
        均耗时全 = sum(有耗时) / len(有耗时)

    cards = [
        ('运行总数', '%d' % 总运行, ''),
        ('成功率', '%.1f%%' % (成功率全 * 100), '%d/%d' % (总成功, 总运行)),
        ('兜底率', '%.1f%%' % (兜底率全 * 100), '%d/%d' % (总兜底, 总运行)),
        ('成功沉淀率', '%.1f%%' % (沉淀率全 * 100), '%d/%d' % (总沉淀, 总运行)),
        ('总 token', '%s' % ('%d' % 总token if 总token else '—'), '平均 %s/条' % ('%.0f' % tok均值 if tok均值 else '—')),
        ('平均耗时', '%s' % ('%.0fms' % 均耗时全 if 均耗时全 is not None else '—'), '%d 周' % len(周序)),
    ]
    cards_html = ''.join(
        '<div class="card"><div class="k">%s</div><div class="v">%s <small>%s</small></div></div>' % (k, v, s)
        for k, v, s in cards)

    # 趋势小图
    def 系列(键, 百分比):
        return [(lb, 周[lb][键]) for lb in 周序]
    趋势 = []
    趋势.append(('<div class="metric">%s%s</div>') % (
        _svg_line('成功率趋势', 系列('成功率', True), 百分比=True),
        '<div class="lab"><span>成功率（每周）</span><span class="tag">%s</span></div>' % ('; '.join('%s %.0f%%' % (lb, 周[lb]['成功率'] * 100) for lb in 周序 if 周[lb]['成功率'] is not None))))
    趋势.append(('<div class="metric">%s%s</div>') % (
        _svg_line('兜底率趋势', 系列('兜底率', True), 百分比=True, 颜色='#f0b429'),
        '<div class="lab"><span>兜底率（每周）</span><span class="tag">%s</span></div>' % ('; '.join('%s %.0f%%' % (lb, 周[lb]['兜底率'] * 100) for lb in 周序 if 周[lb]['兜底率'] is not None))))
    if 信息['日志含token']:
        趋势.append(('<div class="metric">%s%s</div>') % (
            _svg_line('平均 token 趋势', 系列('平均token', False), 单位='', 颜色='#22c55e'),
            '<div class="lab"><span>平均 token / 条（每周）</span><span class="tag">%s</span></div>' % ('; '.join('%s %s' % (lb, ('%.0f' % 周[lb]['平均token'] if 周[lb]['平均token'] else '—')) for lb in 周序))))
    else:
        趋势.append('<div class="metric"><div class="lab"><span>平均 token（每周）</span><span class="tag">日志未记录</span></div><div class="muted">日志未记录 token 成本</div></div>')
    if 信息['日志含耗时']:
        趋势.append(('<div class="metric">%s%s</div>') % (
            _svg_line('平均耗时趋势', 系列('平均耗时', False), 颜色='#a855f7'),
            '<div class="lab"><span>平均耗时 ms（每周）</span><span class="tag">%s</span></div>' % ('; '.join('%s %s' % (lb, ('%.0f' % 周[lb]['平均耗时'] if 周[lb]['平均耗时'] else '—')) for lb in 周序))))
    else:
        趋势.append('<div class="metric"><div class="lab"><span>平均耗时（每周）</span><span class="tag">日志未记录</span></div><div class="muted">日志未记录耗时</div></div>')
    趋势.append(('<div class="metric">%s%s</div>') % (
        _svg_line('成功沉淀率趋势', 系列('沉淀率', True), 百分比=True, 颜色='#06b6d4'),
        '<div class="lab"><span>成功沉淀率（每周）</span><span class="tag">%s</span></div>' % ('; '.join('%s %.0f%%' % (lb, 周[lb]['沉淀率'] * 100) for lb in 周序 if 周[lb]['沉淀率'] is not None))))

    # 兜底来源分布（合并所有周）+ 缓存命中
    来源总 = {}
    for d in 周.values():
        for k, v in d['来源'].items():
            来源总[k] = 来源总.get(k, 0) + v
    来源_html = ''.join('<span class="pill">%s：%d</span>' % (k, v) for k, v in sorted(来源总.items(), key=lambda kv: -kv[1])) or '<span class="muted">无兜底记录</span>'
    缓存总 = sum(d['缓存命中'] for d in 周.values())

    # Top 能力 / 分类
    def 合并top(键):
        c = {}
        for d in 周.values():
            for k, v in dict(d[键]).items():
                c[k] = c.get(k, 0) + v
        return sorted(c.items(), key=lambda kv: -kv[1])[:8]
    能力总 = 合并top('能力')
    分类总 = 合并top('分类')
    能力_html = _svg_bar('Top 期望能力', [(k, v) for k, v in 能力总]) if 能力总 else '<span class="muted">无</span>'
    分类_html = _svg_bar('Top 分类', [(k, v) for k, v in 分类总]) if 分类总 else '<span class="muted">无</span>'

    # 选中块 / 分数
    if 信息['日志含选中块']:
        块总 = 合并top('选中块计数')
        选中块_html = _svg_bar('Top 选中块', [(k, v) for k, v in 块总]) if 块总 else '<span class="muted">无</span>'
    else:
        选中块_html = '<span class="muted">日志未记录（选中块/命中块字段缺失）</span>'
    分数_html = ('平均分 %.2f' % (sum(d['平均分'] for d in 周.values() if d['平均分'] is not None) / max(1, sum(1 for d in 周.values() if d['平均分'] is not None)))) if 信息['日志含分数'] else '<span class="muted">日志未记录（分数字段缺失）</span>'

    # 明细表
    表头 = ['周', '运行', '成功/率', '兜底/率', '来源分布', '平均token', '总token', '沉淀/率', '平均耗时', 'Top能力']
    行_html = ''
    for lb in 周序:
        d = 周[lb]
        srate = ('%.0f%%' % (d['成功率'] * 100)) if d['成功率'] is not None else '—'
        drate = ('%.0f%%' % (d['兜底率'] * 100)) if d['兜底率'] is not None else '—'
        prate = ('%.0f%%' % (d['沉淀率'] * 100)) if d['沉淀率'] is not None else '—'
        src = ' '.join('%s:%d' % (k, v) for k, v in sorted(d['来源'].items(), key=lambda kv: -kv[1])) or '—'
        tok = ('%.0f' % d['平均token']) if d['平均token'] is not None else '—'
        hm = ('%.0fms' % d['平均耗时']) if d['平均耗时'] is not None else '—'
        cap = '、'.join('%s(%d)' % (k, v) for k, v in d['Top能力'][:3]) or '—'
        行_html += ('<tr><td>%s</td><td class="num">%d</td><td class="num">%d/%s</td>'
                    '<td class="num">%d/%s</td><td>%s</td><td class="num">%s</td>'
                    '<td class="num">%d</td><td class="num">%d/%s</td><td class="num">%s</td><td>%s</td></tr>') % (
            lb, d['运行总数'], d['成功数'], srate, d['兜底数'], drate, src, tok,
            d['总token'], d['沉淀数'], prate, hm, cap)

    注释_html = ''.join('<div>· %s</div>' % c for c in 注释)

    html = ('<!doctype html><html lang="zh"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>运行日志周看板</title><style>' + _CSS.replace('%', '%%') + '</style></head><body><div class="wrap">'
            '<h1>运行日志周看板</h1>'
            '<div class="sub">生成时间：%s ｜ 数据源：%s ｜ 有效 %d 行 / 坏行 %d</div>'
            '<div class="note">%s</div>'
            '<div class="cards">%s</div>'
            '<div class="section"><h2>周趋势</h2><div class="grid2">%s</div></div>'
            '<div class="section"><h2>兜底来源分布 &amp; 缓存</h2>'
            '<div>%s</div><div style="margin-top:8px" class="muted">prompt 缓存命中 token 合计：%s</div></div>'
            '<div class="section"><h2>Top 分布</h2><div class="grid2"><div>%s</div><div>%s</div></div>'
            '<div class="grid2" style="margin-top:12px"><div>选中块分布：%s</div><div>分数：%s</div></div></div>'
            '<div class="section"><h2>周明细表</h2><table>'
            '<tr><th>%s</th></tr>%s</table></div>'
            '<footer>段言积木库 · 可观测性周看板（零依赖 · 可离线打开）</footer>'
            '</div></body></html>') % (
        生成时间, os.path.basename(日志路径), 总行, 坏行,
        注释_html, cards_html, ''.join(趋势),
        来源_html, ('%d' % 缓存总 if 缓存总 else '0'),
        能力_html, 分类_html, 选中块_html, 分数_html,
        '</th><th>'.join(表头), 行_html)
    return html


# ============================ Markdown 报告 ============================

def _生成_md(周, 信息, 总行, 坏行, 日志路径, 生成时间):
    L = []
    L.append('# 运行日志周看板报告')
    L.append('')
    L.append('> 生成时间：%s  ｜  数据源：`%s`  ｜  有效 %d 行 / 坏行 %d' % (
        生成时间, os.path.relpath(日志路径, _HERE), 总行, 坏行))
    L.append('')
    if not 周:
        L.append('## 暂无数据')
        L.append('')
        L.append('当前 `运行日志.jsonl` 为空或无有效记录，看板与报告暂不展示指标。')
        L.append('看板将在真实 LLM 跑分产生日志后自动填充。')
        L.append('')
        L.append('## 如何产生日志')
        L.append('')
        L.append('```bash')
        L.append('python 兜底首跑.py --保留      # 端到端兜底闭环，写入 运行日志.jsonl')
        L.append('python 周看板.py               # 重新聚合生成 HTML + 本报告')
        L.append('```')
        return '\n'.join(L)

    总运行 = sum(周[d]['运行总数'] for d in 周)
    总成功 = sum(周[d]['成功数'] for d in 周)
    总兜底 = sum(周[d]['兜底数'] for d in 周)
    总沉淀 = sum(周[d]['沉淀数'] for d in 周)
    总token = sum(周[d]['总token'] for d in 周)
    成功率全 = (总成功 / 总运行) if 总运行 else 0
    兜底率全 = (总兜底 / 总运行) if 总运行 else 0
    沉淀率全 = (总沉淀 / 总运行) if 总运行 else 0

    L.append('## 概览')
    L.append('')
    L.append('| 指标 | 值 |')
    L.append('| --- | --- |')
    L.append('| 聚合周数 | %d |' % len(周))
    L.append('| 运行总数 | %d |' % 总运行)
    L.append('| 成功率 | %.1f%% (%d/%d) |' % (成功率全 * 100, 总成功, 总运行))
    L.append('| 兜底率 | %.1f%% (%d/%d) |' % (兜底率全 * 100, 总兜底, 总运行))
    L.append('| 成功沉淀率 | %.1f%% (%d/%d) |' % (沉淀率全 * 100, 总沉淀, 总运行))
    L.append('| 总 token | %s |' % ('%d' % 总token if 总token else '—'))
    if 信息['日志含token']:
        L.append('| 平均 token/条 | %.1f |' % (总token / 总运行 if 总运行 else 0))
    else:
        L.append('| 平均 token/条 | 日志未记录 |')
    if 信息['日志含耗时']:
        有耗时 = [周[lb]['平均耗时'] for lb in 周 if 周[lb]['平均耗时'] is not None]
        L.append('| 平均耗时 | %.1f ms |' % (sum(有耗时) / len(有耗时) if 有耗时 else 0))
    else:
        L.append('| 平均耗时 | 日志未记录 |')
    L.append('')

    L.append('## 说明')
    L.append('')
    if 信息['伪周模式']:
        L.append('- ⚠️ 日志无可用时间字段，已按行顺序「每 %d 条算一周」生成伪周（趋势仅供占位，真实 LLM 跑分写入带时间字段后将自动切换为 ISO 周）。' % _伪周每几条)
    else:
        L.append('- 已按 ISO 周聚合（检测到时间/日期字段）。')
    if 坏行:
        L.append('- 共 %d 行坏数据已跳过（不计入指标）。' % 坏行)
    for 字段, 标记 in (('日志含token', 'token 成本'), ('日志含耗时', '耗时'), ('日志含选中块', '选中块'), ('日志含分数', '分数')):
        if not 信息[字段]:
            L.append('- 日志未记录「%s」，对应指标标注「日志未记录」并跳过聚合。' % 标记)
    L.append('')

    L.append('## 周明细')
    L.append('')
    L.append('| 周 | 运行 | 成功/率 | 兜底/率 | 来源分布 | 平均token | 总token | 沉淀/率 | 平均耗时 | Top能力 |')
    L.append('| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |')
    for lb in 周:
        d = 周[lb]
        srate = ('%.0f%%' % (d['成功率'] * 100)) if d['成功率'] is not None else '—'
        drate = ('%.0f%%' % (d['兜底率'] * 100)) if d['兜底率'] is not None else '—'
        prate = ('%.0f%%' % (d['沉淀率'] * 100)) if d['沉淀率'] is not None else '—'
        src = '、'.join('%s:%d' % (k, v) for k, v in sorted(d['来源'].items(), key=lambda kv: -kv[1])) or '—'
        tok = ('%.0f' % d['平均token']) if d['平均token'] is not None else '—'
        hm = ('%.0f' % d['平均耗时']) if d['平均耗时'] is not None else '—'
        cap = '、'.join('%s(%d)' % (k, v) for k, v in d['Top能力'][:3]) or '—'
    L.append('| %s | %d | %d/%s | %d/%s | %s | %s | %d | %d/%s | %s | %s |' % (
        lb, d['运行总数'], d['成功数'], srate, d['兜底数'], drate, src, tok,
        d['总token'], d['沉淀数'], prate, hm, cap))
    L.append('')

    L.append('## 兜底来源分布')
    L.append('')
    来源总 = {}
    for d in 周.values():
        for k, v in d['来源'].items():
            来源总[k] = 来源总.get(k, 0) + v
    if 来源总:
        for k, v in sorted(来源总.items(), key=lambda kv: -kv[1]):
            L.append('- %s：%d（%.1f%%）' % (k, v, v / 总兜底 * 100 if 总兜底 else 0))
    else:
        L.append('- 无兜底记录。')
    L.append('')

    L.append('## Top 分布')
    L.append('')
    def 合并top(键):
        c = {}
        for d in 周.values():
            for k, v in dict(d[键]).items():
                c[k] = c.get(k, 0) + v
        return sorted(c.items(), key=lambda kv: -kv[1])[:8]
    能力总 = 合并top('能力')
    分类总 = 合并top('分类')
    L.append('- **Top 期望能力**：' + ('、'.join('%s(%d)' % (k, v) for k, v in 能力总) if 能力总 else '无'))
    L.append('- **Top 分类**：' + ('、'.join('%s(%d)' % (k, v) for k, v in 分类总) if 分类总 else '无'))
    if 信息['日志含选中块']:
        块总 = 合并top('选中块计数')
        L.append('- **Top 选中块**：' + ('、'.join('%s(%d)' % (k, v) for k, v in 块总) if 块总 else '无'))
    else:
        L.append('- **选中块分布**：日志未记录')
    if 信息['日志含分数']:
        均分 = sum(d['平均分'] for d in 周.values() if d['平均分'] is not None) / max(1, sum(1 for d in 周.values() if d['平均分'] is not None))
        L.append('- **平均分**：%.2f' % 均分)
    else:
        L.append('- **分数**：日志未记录')
    L.append('')

    L.append('## 如何产生 / 刷新日志')
    L.append('')
    L.append('```bash')
    L.append('python 兜底首跑.py --保留      # 端到端兜底闭环，写入 运行日志.jsonl')
    L.append('python 周看板.py               # 重新聚合，生成 周看板.html + 本 Markdown 报告')
    L.append('```')
    L.append('')
    L.append('> 仅读取 `运行日志.jsonl`，不修改引擎/`索引.json`/`组合.py` 等任何代码。')
    return '\n'.join(L)


def 主(日志路径=_默认日志):
    行, 坏行 = 读日志(日志路径)
    周, 信息 = 聚合(行)
    生成时间 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html = _生成_html(周, 信息, len(行), 坏行, 日志路径, 生成时间)
    md = _生成_md(周, 信息, len(行), 坏行, 日志路径, 生成时间)
    with open(_输出_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    with open(_输出_MD, 'w', encoding='utf-8') as f:
        f.write(md)
    print('[周看板] 有效行=%d 坏行=%d 聚合周数=%d 伪周模式=%s' % (len(行), 坏行, len(周), 信息['伪周模式']))
    print('[周看板] 已写出：%s' % _输出_HTML)
    print('[周看板] 已写出：%s' % _输出_MD)
    return 周, 信息


if __name__ == '__main__':
    主()
