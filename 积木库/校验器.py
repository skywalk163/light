# -*- coding: utf-8 -*-
"""光明积木『LLM 校验器』v0.16 —— 选块/接线后的第二道正确性闸门（解决词法盲区 + 细微错配）。

第一道闸是选块（embedding/概念图/关键词）。但选块是『召回』不是『判定』：即使召回了块，
仍可能语义错配。校验器在『运行前』做最后一次判定：

  - 本地校验（零 token，无 key 时启用）：用概念图看『需求概念』与『所选块概念』是否
    有『具体能力概念』交集。无交集 ⇒ 误选 ⇒ MISMATCH。这能拦下『中文转拼音』被误选成
    『数字转中文』这类共享通用『中文』词却能力不同的细微错配。
  - LLM 校验（配置了 api_key 时启用）：把『需求 + 已选块（含输入输出类型/描述）』发给
    大模型判定组合是否真的满足需求。系统提示内置 few-shot，专门覆盖『斐波那契 vs 统计』、
    『中文转拼音 vs 数字转中文』等细微错配。无 key 时降级本地校验。

两类校验都把『判定』与『生成』解耦：判定失败才触发兜底生成，保证零 token 为常态。

用法：
    python 积木库/校验器.py "计算斐波那契数列第10项" --候选 统计双指标
    python 积木库/校验器.py "把中文转成拼音" --候选 数字转中文 --dry-run   # 展示将发给 LLM 的请求体
"""

import argparse
import json
import os
import urllib.request

_HERE = os.path.abspath(os.path.dirname(__file__))


def load_config():
    """复用兜底生成器的配置（环境变量 / llm_config.json）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        '兜底生成器', os.path.join(_HERE, '兜底生成器.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load_config()


from embedding选块 import 概念向量, load_index  # noqa: E402


# ---------------------------------------------------------------------------
# 本地校验（零 token）
# ---------------------------------------------------------------------------
# 仅作「兜底维度」的通用领域概念（命中它们不足以证明块满足需求）
_通用概念 = {'数据', '文本', '财务', '中文', '工具', '生成', '网络'}


def _具体概念(vec):
    return set(vec) - _通用概念


def _local_validate(需求, 候选):
    """需求与所选块的『具体能力概念』无交集 ⇒ 误选 ⇒ 不通过。

    仅共享通用领域词（如「中文」）不算通过——这是修复词法盲区的核心：
    『把中文转拼音』与『数字转中文』都带『中文』，但能力并不相同（前者要拼音、
    后者要数字的中文读法）。v0.16 概念图新增『拼音转换』概念后，二者被清晰区分。
    """
    需概 = 概念向量(需求)
    需特 = _具体概念(需概)
    if not 需特:
        # 需求在概念空间里只有通用领域词，无法判定误选，放行交给运行期
        return {'通过': True, '理由': '需求无具体能力概念，放行'}

    for c in (候选 or [])[:5]:
        文本 = (c.get('名称', '') + ' ' + c.get('描述', '') + ' ' + str(c.get('领域', '')))
        c特 = _具体概念(概念向量(文本))
        if 需特 & c特:
            return {'通过': True,
                    '理由': '所选块「%s」与需求共享具体能力概念 %s' %
                            (c.get('名称'), list(需特 & c特))}

    return {'通过': False,
            '理由': '所选块 %s 的具体能力概念与需求 %s 无交集，疑似误选' %
                    ([c.get('名称') for c in (候选 or [])[:3]], list(需特))}


# ---------------------------------------------------------------------------
# LLM 校验（配置了 key 时启用）
# ---------------------------------------------------------------------------
_SYSTEM = """你是一个光明(Light)积木组合的『校验器』。给定用户需求和已选中的积木列表
（每个含名称、领域、输入类型、输出类型、描述），请判断『这个组合是否真的能满足需求』。

只输出一个 JSON 对象：{"通过": true/false, "理由": "一句话中文说明"}。
- 通过=true：组合语义上确实能满足需求。
- 通过=false：组合语义上不能满足（如需求是生成斐波那契数列却选了统计均值积木；或需求是
  『中文转拼音』却选了『数字转中文』积木——前者要拼音，后者要数字的中文读法，能力不同），
  或需求根本超出当前积木能力。注意：仅共享通用领域词（如都带『中文』）不代表能力相同。

示例：
需求：计算斐波那契数列第10项
已选：统计双指标（领域=数据，输入=[列表]，描述=对数值列表同时给出算术均值与极差跨度）
→ {"通过": false, "理由": "需求是生成斐波那契数列（数列生成），已选块是统计描述，能力不匹配"}

需求：把这段中文转成拼音
已选：数字转中文（领域=中文，输入=[数]，描述=把整数转成中文读法）
→ {"通过": false, "理由": "需求是中文转拼音（拼音转换），已选块是数字→中文读法，目标输出不同"}

需求：计算这组数的方差
已选：方差（领域=数据，输入=[列表]，描述=计算一组数的方差）
→ {"通过": true, "理由": "已选块能力与需求一致"}"""

_NEG = ['不', '否', '错', '误', '无关', '不能', '无法', '不对']


def _构造请求(需求, 候选, cfg):
    """构造发给 LLM 的请求（url, headers, payload）。dry-run 与真实调用共用。"""
    url = cfg['base_url'].rstrip('/') + '/chat/completions'
    cands = '\n'.join(
        '  - %s（领域=%s，输入=%s，输出=%s，描述=%s）' % (
            c.get('名称'), c.get('领域'),
            [p.get('类型') for p in (c.get('输入') or [])],
            (c.get('输出') or {}).get('类型'),
            c.get('描述', ''))
        for c in (候选 or [])[:5]) or '（无）'
    user = '需求：%s\n已选积木：\n%s\n请校验该组合是否满足需求。' % (需求, cands)
    payload = {
        'model': cfg['model'],
        'messages': [
            {'role': 'system', 'content': _SYSTEM},
            {'role': 'user', 'content': user},
        ],
        'temperature': 0.1,
        'response_format': {'type': 'json_object'},
    }
    return url, payload


def _llm_validate(需求, 候选, cfg):
    if not cfg.get('api_key'):
        return None
    url, payload = _构造请求(需求, 候选, cfg)
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + cfg['api_key'],
                 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode('utf-8'))
        content = data['choices'][0]['message']['content']
        obj = json.loads(content)
        通过 = bool(obj.get('通过'))
        if isinstance(通过, str):
            通过 = 通过.strip().lower() not in _NEG
        return {'通过': 通过, '理由': str(obj.get('理由', ''))}
    except Exception as e:
        print('[校验器] LLM 调用失败，降级本地校验：%s' % e)
        return None


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def validate(需求, 候选, 索引=None):
    """返回 {'通过': bool, '理由': str}。优先 LLM（有 key），失败/无 key 用本地。"""
    cfg = load_config()
    if cfg.get('api_key'):
        res = _llm_validate(需求, 候选, cfg)
        if res is not None:
            return res
    return _local_validate(需求, 候选)


def _富化候选(名称列表, 索引=None):
    """把候选名称还原为带 输入/输出/描述 的完整条目（用于更精准的 LLM 校验）。"""
    if 索引 is None:
        return [{'名称': n, '描述': '', '领域': '?'} for n in 名称列表]
    查表 = {b['名称']: b for b in (索引.get('块') or [])}
    out = []
    for n in 名称列表:
        out.append(查表.get(n) or {'名称': n, '描述': '', '领域': '?'})
    return out


def _cli(argv=None):
    p = argparse.ArgumentParser(description='光明积木 LLM 校验器 v0.16')
    p.add_argument('需求', help='自然语言需求')
    p.add_argument('--候选', nargs='+', default=[], help='候选块名称列表')
    p.add_argument('--dry-run', action='store_true',
                   help='仅展示将发给 LLM 的请求体（含已选块输入/输出类型），不实际调用')
    args = p.parse_args(argv)

    索引 = None
    try:
        索引 = load_index() if os.path.isfile(os.path.join(_HERE, '索引.json')) else None
    except Exception:
        索引 = None
    候选 = _富化候选(args.候选, 索引)
    cfg = load_config()

    if args.dry_run:
        url, payload = _构造请求(args.需求, 候选, cfg)
        masked = '（未配置 api_key）' if not cfg.get('api_key') else 'Bearer ' + ('*' * 8)
        print(json.dumps({
            'url': url,
            'headers': {'Authorization': masked, 'Content-Type': 'application/json'},
            'payload': payload,
        }, ensure_ascii=False, indent=2))
        return 0

    res = validate(args.需求, 候选, 索引=索引)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(_cli())