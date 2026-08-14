# -*- coding: utf-8 -*-
"""积木库文档站 · 块列表生成器（零依赖，仅用标准库）。

读取积木库/索引.json，程序化生成 docs_site/blocks.html，
使「块列表」永远与索引同步、不手抄。

运行（受管 python）：
  C:/Users/skywalk/.workbuddy/binaries/python/versions/3.13.12/python.exe 积木库/docs_site/build_docs.py

输出：积木库/docs_site/blocks.html
"""
import json
import os
import html
import datetime

_HERE = os.path.abspath(os.path.dirname(__file__))
_库根 = os.path.normpath(os.path.join(_HERE, '..'))
_索引 = os.path.join(_库根, '索引.json')
_输出 = os.path.join(_HERE, 'blocks.html')


def 读索引():
    with open(_索引, encoding='utf-8') as f:
        return json.load(f)


def _稳定徽章(稳定性):
    稳定性 = 稳定性 or ''
    cls = 'generated' if 稳定性 == 'generated' else 'stable'
    文案 = 'generated' if 稳定性 == 'generated' else 'stable'
    return '<span class="badge %s">%s</span>' % (cls, 文案)


def _输入摘要(输入):
    if not 输入:
        return '—'
    return '；'.join('%s:%s' % (i.get('名', '?'), i.get('类型', '?')) for i in 输入)


def _行(b):
    名称 = html.escape(str(b.get('名称', '')))
    领域 = html.escape(str(b.get('领域', '')))
    层级 = html.escape(str(b.get('层级', '')))
    描述 = html.escape(str(b.get('描述', '')))
    稳定性 = _稳定徽章(b.get('稳定性'))
    导出名 = html.escape(str(b.get('导出名', '')))
    路径 = html.escape(str(b.get('路径', '')))
    输入 = html.escape(_输入摘要(b.get('输入')))
    输出 = html.escape(str((b.get('输出') or {}).get('类型', '—')))
    return ('<tr>'
            '<td><b>%s</b></td>'
            '<td>%s</td>'
            '<td class="num">%s</td>'
            '<td>%s</td>'
            '<td>%s</td>'
            '<td>%s</td>'
            '<td>%s</td>'
            '<td><code>%s</code></td>'
            '<td><code>%s</code></td>'
            '</tr>') % (名称, 领域, 层级, 描述, 稳定性, 输入, 输出, 导出名, 路径)


def 生成():
    索引 = 读索引()
    块 = 索引.get('块') or []
    协议版本 = html.escape(str(索引.get('协议版本', '') or 索引.get('版本', '')))
    行 = '\n'.join(_行(b) for b in 块)
    计数 = len(块)
    生成时间 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    doc = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>积木库 · 块清单（共 {count} 块）</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<div class="topbar">
  <span class="brand">段言积木库</span>
  <span class="proto">协议 <b>v1.0.0</b>（当前）/ <i>v1.1 规划中</i></span>
  <span class="links">
    <a href="index.html">文档首页</a>
    <a href="../协议.md">协议.md</a>
    <a href="../评估/README.md">评估/README.md</a>
  </span>
</div>
<div class="wrap">
  <header class="hero">
    <h1>积木清单</h1>
    <p>共 <b>{count}</b> 块 · 协议版本 <code>{proto}</code> · 本页由 <code>build_docs.py</code> 从 <code>索引.json</code> 实时生成，切勿手抄。</p>
  </header>

  <div class="toolbar">
    <input id="q" placeholder="搜索名称 / 描述 / 导出名…" oninput="过滤()">
    <select id="dom" onchange="过滤()">
      <option value="">全部领域</option>
    </select>
    <span class="count" id="c"></span>
  </div>

  <table id="tbl">
    <thead>
      <tr><th>名称</th><th>领域</th><th>层级</th><th>描述</th><th>稳定性</th><th>输入</th><th>输出</th><th>导出名</th><th>路径</th></tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>

  <footer>
    生成于 {gentime} · 数据来源 <code>../索引.json</code>（只读，未改动）· 受管 python 运行 build_docs.py 重新生成。
  </footer>
</div>

<script>
function 领域集合(){{
  var s = new Set();
  document.querySelectorAll('#tbl tbody tr').forEach(function(tr){{
    s.add(tr.children[1].textContent.trim());
  }});
  return Array.from(s).sort();
}}
function 填充领域(){{
  var sel = document.getElementById('dom');
  var 现有 = new Set(Array.from(sel.options).map(function(o){{return o.value;}}));
  领域集合().forEach(function(d){{
    if(!现有.has(d)){{ var o=document.createElement('option'); o.value=d; o.textContent=d; sel.appendChild(o); }}
  }});
}}
function 过滤(){{
  var q = document.getElementById('q').value.trim().toLowerCase();
  var dom = document.getElementById('dom').value;
  var n = 0;
  document.querySelectorAll('#tbl tbody tr').forEach(function(tr){{
    var t = tr.textContent.toLowerCase();
    var d = tr.children[1].textContent.trim();
    var ok = (q==='' || t.indexOf(q)>=0) && (dom==='' || d===dom);
    tr.style.display = ok ? '' : 'none';
    if(ok) n++;
  }});
  document.getElementById('c').textContent = '显示 ' + n + ' / {count}';
}}
填充领域(); 过滤();
</script>
</body>
</html>
""".format(count=计数, proto=协议版本, rows=行, gentime=生成时间)

    with open(_输出, 'w', encoding='utf-8') as f:
        f.write(doc)
    print('已生成 %s （%d 块）' % (_输出, 计数))


if __name__ == '__main__':
    生成()
