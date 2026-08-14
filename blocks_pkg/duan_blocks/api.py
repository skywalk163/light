# -*- coding: utf-8 -*-
"""duan-blocks Web/API：FastAPI 包装 组合.py。

  GET  /           演示页（输入需求实时看组合）
  GET  /health    健康检查
  POST /combo      {requirement, input?, top?, chained?, semantic?, keyword?,
                    hybrid?, threshold?, no_verify?, no_cache?, no_fallback?}
                   → {成功, 候选, 是兜底, 运行, 诊断}

运行：uvicorn duan_blocks.api:app --port 8123
"""
import json
import os
import time

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .cli import 积木库路径, _加载组合

app = FastAPI(title='duan-blocks', description='段言积木组合平台 · 零 token 组合式代码生成')

_组合模块 = None


def _mod():
    global _组合模块
    if _组合模块 is None:
        _组合模块 = _加载组合(积木库路径())
    return _组合模块


class 请求(BaseModel):
    requirement: str
    input: str = '[1, 2, 3, 4, 5]'
    top: int = 3
    chained: bool = False
    semantic: bool = False
    keyword: bool = False
    hybrid: bool = False
    threshold: float | None = None
    no_verify: bool = False
    no_cache: bool = False
    no_fallback: bool = False


def _写日志(需求, 成功, 候选, 是兜底, 兜底理由=''):
    """可观测：每次请求追加一行 JSONL 运行日志（成功与失败都记）。"""
    try:
        log = os.path.join(积木库路径(), '运行日志.jsonl')
        with open(log, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                '时间': time.strftime('%Y-%m-%d %H:%M:%S'),
                '需求': 需求, '成功': 成功,
                '候选': [c['名称'] for c in 候选],
                '是兜底': 是兜底, '兜底理由': 兜底理由,
            }, ensure_ascii=False) + '\n')
    except Exception:
        pass


@app.get('/health')
def health():
    return {'状态': 'ok', '块数': len((_mod().load_index() or {}).get('块') or [])}


@app.post('/combo')
def combo(r: 请求):
    mod = _mod()
    t0 = time.time()
    诊断 = {}
    res = mod.组合(r.requirement, 输入值=r.input, top=r.top,
                 语义=r.semantic, 关键词=r.keyword, 链式=r.chained,
                 阈值=r.threshold, 无校验=r.no_verify, 无缓存=r.no_cache,
                 无兜底=r.no_fallback, 混合=r.hybrid, 诊断=诊断)
    诊断['规划耗时ms'] = round((time.time() - t0) * 1000, 2)
    if not res:
        _写日志(r.requirement, 成功=False, 候选=[], 是兜底=False,
                兜底理由=诊断.get('兜底理由', ''))
        return {'成功': False, '需求': r.requirement, '诊断': 诊断,
                '错误': '未能生成方案（可开兜底或换输入）'}
    方案, 候选 = res
    是兜底 = bool(方案.get('_兜底'))
    duan = mod._定位运行时()
    rc, out, err = mod._运行_单次(方案, os.path.join(积木库路径(), '组合结果.duan'), duan)
    成功 = mod._成功(rc, out)
    诊断['成功'] = 成功
    诊断['最终rc'] = rc or 0
    结果 = {
        '成功': 成功,
        '需求': r.requirement,
        '候选': [{'名称': c['名称'], '领域': c['领域'], '分数': c['分数']}
                for c in 候选],
        '是兜底': 是兜底,
        '运行': {'输出': out.strip()[-800:] if out else '', 'rc': rc or 0},
        '诊断': 诊断,
    }
    # 可观测：每次请求追加一行 JSONL 运行日志（3.3）
    _写日志(r.requirement, 成功, 候选, 是兜底,
            兜底理由=诊断.get('兜底理由', ''))
    return 结果


_页面 = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>段言积木组合平台</title>
<style>
  body{font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;background:#fafafa;color:#222}
  h1{font-size:1.4rem;font-weight:600}
  .sub{color:#666;font-size:.85rem;margin-top:-.4rem}
  textarea,button{font:inherit;width:100%;box-sizing:border-box}
  textarea{min-height:70px;padding:.6rem;border:1px solid #ccc;border-radius:8px}
  input{width:100%;padding:.5rem;border:1px solid #ccc;border-radius:8px;box-sizing:border-box}
  button{margin-top:.6rem;padding:.6rem;background:#2563eb;color:#fff;border:0;border-radius:8px;cursor:pointer;font-size:1rem}
  button:disabled{opacity:.6}
  pre{background:#f1f5f9;padding:.8rem;border-radius:8px;overflow:auto;font-size:.85rem;white-space:pre-wrap}
  .ok{color:#0a7d33}.bad{color:#c62828}
</style>
</head>
<body>
<h1>段言积木组合平台</h1>
<p class="sub">零 token · 全离线 · 选块/校验/接线/粘合 → 可运行 .duan</p>
<textarea id="q" placeholder="例如：对一批数字求和再算平均"></textarea>
<input id="inp" placeholder="输入（段言表达式），默认 [1,2,3,4,5]" value="[1, 2, 3, 4, 5]">
<button id="run" onclick="go()">组合并运行</button>
<div id="out" style="margin-top:1rem"></div>
<script>
async function go(){
  const btn=document.getElementById('run');btn.disabled=true;
  const res=await fetch('/combo',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({requirement:document.getElementById('q').value,input:document.getElementById('inp').value})});
  const d=await res.json();btn.disabled=false;
  let h='<h3>结果</h3>';
  h+='<div class="'+(d.成功?'ok':'bad')+'">'+(d.成功?'运行成功 ✓':'失败：'+(d.错误||'运行未成功'))+'</div>';
  h+='<pre>'+JSON.stringify(d,null,2)+'</pre>';
  document.getElementById('out').innerHTML=h;
}
</script>
</body>
</html>"""


@app.get('/', response_class=HTMLResponse)
def index():
    return _页面
