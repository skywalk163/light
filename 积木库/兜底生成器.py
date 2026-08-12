# -*- coding: utf-8 -*-
"""LLM 兜底生成器 v0.14。

触发场景：选块器对某个需求「选不准」——无候选 或 top 分数低于阈值，或契约级
接线出现无法补齐的参数（无匹配类型且无可默认）。此时调用 LLM（OpenAI 兼容的
chat/completions）按契约生成一块全新的光明积木；无 API key 时降级为本地规则
生成器（覆盖 方差/标准差/中位数/绝对值 等常见但库内缺失的块）。

生成的块写入 积木库/生成/<名称>.light，并注册进 索引.json，下次同需求零 token 复用。

配置（任选其一）：
  - 环境变量：OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL
  - 文件：积木库/llm_config.json {"api_key": "...", "base_url": "...", "model": "..."}
"""

import json
import os
import urllib.request

_HERE = os.path.abspath(os.path.dirname(__file__))


def load_config():
    cfg = {
        'base_url': os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
        'api_key': os.environ.get('OPENAI_API_KEY', ''),
        'model': os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
    }
    p = os.path.join(_HERE, 'llm_config.json')
    if os.path.isfile(p):
        try:
            cfg.update(json.load(open(p, encoding='utf-8')))
        except Exception:
            pass
    return cfg


_SYSTEM = """你是一个光明(Light)中文编程语言的积木生成器。光明使用中文关键字：
段落 名 接收 参数： 定义函数；设 x 为 表达式。 赋值；返回 表达式。 返回；
当 条件： ... 当 结束 循环；如果 条件： 否则如果 条件： 否则： 分支；
列表索引 表[i]（i 必须是整数，用 整数(...) 取整）；长度(表)；
中缀算术：A 加 B / A 减 B / A 乘 B / A 除 B（除 是真除法返回浮点，整数除法用 整数(A 除 B) 或 A 整除 B）；
取余：A 模 B；布尔比较：A 大于 B / A 小于 B / A 等于 B / A 不等于 B。
整数循环：设 i 为 0；当 i 小于 长度(表)： ... 设 i 为 i 加 1。
列表排序用 表.排序()（原地排序，作为语句调用，不接收返回值）。

一个积木文件的格式（注意：导出 名 与 段落 名 必须一致）：
# 注释
导出 块名
段落 块名 接收 输入名：
    设 ... 为 ...
    返回 结果

请只输出一个 JSON 对象，结构：
{"名称":"...","领域":"生成","层级":0,"描述":"...","输入":[{"名":"序列","类型":"列表"}],"输出":{"类型":"数"},"导出名":"块名","源码":"<完整 .light 文件文本，含注释/导出/段落，换行用 \\n>"}
不要输出任何 JSON 以外的解释文字。"""


def _call_llm(需求, 候选, cfg):
    if not cfg.get('api_key'):
        return None
    url = cfg['base_url'].rstrip('/') + '/chat/completions'
    cands = '、'.join(c.get('名称', '') for c in (候选 or [])[:5]) or '（无）'
    user = '需求：%s\n已选候选（可能不对）：%s\n请生成一块能直接满足该需求的光明积木。' % (需求, cands)
    payload = {
        'model': cfg['model'],
        'messages': [
            {'role': 'system', 'content': _SYSTEM},
            {'role': 'user', 'content': user},
        ],
        'temperature': 0.2,
        'response_format': {'type': 'json_object'},
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + cfg['api_key'],
                 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode('utf-8'))
        content = data['choices'][0]['message']['content']
        return json.loads(content)
    except Exception as e:
        print('[兜底] LLM 调用失败，降级本地规则：%s' % e)
        return None


# ---------------------------------------------------------------------------
# 本地规则生成器（无 key 时也能端到端跑通）
# ---------------------------------------------------------------------------
def _本地规则生成(需求):
    q = 需求
    if '方差' in q:
        return _方差模板(总体=('样本' not in q))
    if '中位数' in q or '中位' in q:
        return _中位数模板()
    if '绝对值' in q or '取绝对' in q:
        return _绝对值模板()
    # v0.15：库外『数列/数论』意图的本地兜底（零 token，无需 LLM key）
    if '斐波那契' in q or 'fib' in q.lower():
        return _斐波那契模板()
    if '阶乘' in q or 'factorial' in q.lower():
        return _阶乘模板()
    if '素数' in q or '质数' in q:
        return _素数模板()
    if '累加和' in q or '高斯和' in q or '1到' in q or '1至' in q:
        return _累加和模板()
    return None


def _斐波那契模板():
    名 = '斐波那契'
    src = (
        '# 积木：斐波那契（数列生成，本地规则生成）\n'
        '# 契约：输入 [数 n] → 输出 列表（前 n 项）\n'
        '导出 斐波那契\n'
        '段落 斐波那契 接收 n：\n'
        '    如果 n 等于 1：\n'
        '        返回 [1]\n'
        '    设 表 为 [1, 1]\n'
        '    设 i 为 2\n'
        '    当 i 小于 n：\n'
        '        设 末 为 表[长度(表) 减 1]\n'
        '        设 次 为 表[长度(表) 减 2]\n'
        '        表.追加(末 加 次)\n'
        '        设 i 为 i 加 1\n'
        '    返回 表\n'
    )
    return {
        '名称': 名, '领域': '生成', '层级': 0,
        '描述': '生成斐波那契数列前 n 项',
        '输入': [{'名': 'n', '类型': '数'}],
        '输出': {'类型': '列表'},
        '稳定性': 'generated',
        '导出名': 名,
        '源码': src,
    }


def _阶乘模板():
    名 = '阶乘'
    src = (
        '# 积木：阶乘（数列生成，本地规则生成）\n'
        '# 契约：输入 [数 n] → 输出 数\n'
        '导出 阶乘\n'
        '段落 阶乘 接收 n：\n'
        '    设 结果 为 1\n'
        '    设 i 为 1\n'
        '    设 上限 为 n 加 1\n'
        '    当 i 小于 上限：\n'
        '        设 结果 为 结果 乘 i\n'
        '        设 i 为 i 加 1\n'
        '    返回 结果\n'
    )
    return {
        '名称': 名, '领域': '生成', '层级': 0,
        '描述': '计算 n 的阶乘（n!）',
        '输入': [{'名': 'n', '类型': '数'}],
        '输出': {'类型': '数'},
        '稳定性': 'generated',
        '导出名': 名,
        '源码': src,
    }


def _素数模板():
    名 = '素数'
    src = (
        '# 积木：素数（数论，本地规则生成）\n'
        '# 契约：输入 [数 n] → 输出 数（1=素数，0=非素数）\n'
        '导出 素数\n'
        '段落 素数 接收 n：\n'
        '    如果 n 小于 2：\n'
        '        返回 0\n'
        '    设 i 为 2\n'
        '    当 i 小于 n：\n'
        '        如果 n 模 i 等于 0：\n'
        '            返回 0\n'
        '        设 i 为 i 加 1\n'
        '    返回 1\n'
    )
    return {
        '名称': 名, '领域': '生成', '层级': 0,
        '描述': '判断 n 是否为素数（1=是，0=否）',
        '输入': [{'名': 'n', '类型': '数'}],
        '输出': {'类型': '数'},
        '稳定性': 'generated',
        '导出名': 名,
        '源码': src,
    }


def _累加和模板():
    名 = '累加和'
    src = (
        '# 积木：累加和（数论，本地规则生成）\n'
        '# 契约：输入 [数 n] → 输出 数（1+2+...+n）\n'
        '导出 累加和\n'
        '段落 累加和 接收 n：\n'
        '    返回 (n 乘 (n 加 1)) 除 2\n'
    )
    return {
        '名称': 名, '领域': '生成', '层级': 0,
        '描述': '计算 1+2+...+n 的累加和',
        '输入': [{'名': 'n', '类型': '数'}],
        '输出': {'类型': '数'},
        '稳定性': 'generated',
        '导出名': 名,
        '源码': src,
    }


def _方差模板(总体=True):
    名 = '方差' if 总体 else '样本方差'
    分母 = '计数' if 总体 else '(计数 减 1)'
    src = (
        '# 积木：%s（数据领域，本地规则生成）\n'
        '# 契约：输入 [列表] → 输出 数（%s）\n'
        '导出 %s\n'
        '段落 %s 接收 序列：\n'
        '    设 计数 为 长度(序列)\n'
        '    设 和 为 0\n'
        '    设 i 为 0\n'
        '    当 i 小于 计数：\n'
        '        设 和 为 和 加 序列[i]\n'
        '        设 i 为 i 加 1\n'
        '    设 均值 为 和 除 计数\n'
        '    设 平方和 为 0\n'
        '    设 j 为 0\n'
        '    当 j 小于 计数：\n'
        '        设 差 为 序列[j] 减 均值\n'
        '        设 平方和 为 平方和 加 (差 乘 差)\n'
        '        设 j 为 j 加 1\n'
        '    返回 (平方和 除 %s)\n'
    ) % (名, 名, 名, 名, 分母)
    return {
        '名称': 名, '领域': '生成', '层级': 0,
        '描述': '计算一组数的%s' % 名,
        '输入': [{'名': '序列', '类型': '列表'}],
        '输出': {'类型': '数'},
        '稳定性': 'generated',
        '导出名': 名,
        '源码': src,
    }


def _中位数模板():
    名 = '中位数'
    src = (
        '# 积木：中位数（数据领域，本地规则生成）\n'
        '# 契约：输入 [列表] → 输出 数\n'
        '导出 中位数\n'
        '段落 中位数 接收 序列：\n'
        '    设 排序表 为 []\n'
        '    设 i 为 0\n'
        '    当 i 小于 长度(序列)：\n'
        '        排序表.追加(序列[i])\n'
        '        设 i 为 i 加 1\n'
        '    排序表.排序()\n'
        '    设 计数 为 长度(排序表)\n'
        '    设 中 为 整数(计数 除 2)\n'
        '    如果 计数 模 2 等于 0：\n'
        '        返回 ((排序表[中 减 1] 加 排序表[中]) 除 2)\n'
        '    否则：\n'
        '        返回 排序表[中]\n'
    )
    return {
        '名称': 名, '领域': '生成', '层级': 0,
        '描述': '计算一组数的中位数',
        '输入': [{'名': '序列', '类型': '列表'}],
        '输出': {'类型': '数'},
        '稳定性': 'generated',
        '导出名': 名,
        '源码': src,
    }


def _绝对值模板():
    名 = '绝对值'
    src = (
        '# 积木：绝对值（工具领域，本地规则生成）\n'
        '# 契约：输入 [数] → 输出 数\n'
        '导出 绝对值\n'
        '段落 绝对值 接收 数：\n'
        '    如果 数 小于 0：\n'
        '        返回 (0 减 数)\n'
        '    否则：\n'
        '        返回 数\n'
    )
    return {
        '名称': 名, '领域': '生成', '层级': 0,
        '描述': '取一个数的绝对值',
        '输入': [{'名': '数', '类型': '数'}],
        '输出': {'类型': '数'},
        '稳定性': 'generated',
        '导出名': 名,
        '源码': src,
    }


def generate_block(需求, 索引=None, 候选=None, 库根=None):
    """生成一块满足需求的新积木（dict）。返回 None 表示连本地规则都覆盖不了。"""
    blk = _call_llm(需求, 候选, load_config())
    if blk is None:
        blk = _本地规则生成(需求)
    if blk is None:
        return None
    # 补默认字段 + 兜底拼装最小可用源码
    blk.setdefault('领域', '生成')
    blk.setdefault('层级', 0)
    blk.setdefault('稳定性', 'generated')
    源 = (blk.get('源码') or '').strip()
    if '导出 ' not in 源:
        名 = blk.get('导出名') or blk.get('名称')
        源 = '# 自动生成\n导出 %s\n段落 %s 接收 序列：\n    返回 序列\n' % (名, 名)
        blk['源码'] = 源
    if not blk.get('导出名'):
        blk['导出名'] = blk.get('名称')
    return blk


def local_rule_block(需求):
    """仅用本地规则判断需求是否命中「库缺失但可模板生成」的能力（零 token，不调 LLM）。"""
    return _本地规则生成(需求)


def 注册(块, 库根=None):
    """把生成块写入 生成/<名称>.light 并追加进 索引.json。返回 .light 路径（相对库根）。"""
    库根 = 库根 or _HERE
    名 = 块.get('名称') or 块.get('导出名')
    路径 = '生成/%s.light' % 名
    目录 = os.path.join(库根, '生成')
    os.makedirs(目录, exist_ok=True)

    idx_path = os.path.join(库根, '索引.json')
    idx = json.load(open(idx_path, encoding='utf-8'))
    # 去重：已存在则仅更新文件与路径
    if any(b.get('名称') == 名 for b in idx['块']):
        with open(os.path.join(库根, 路径), 'w', encoding='utf-8') as f:
            f.write(块.get('源码', ''))
        for b in idx['块']:
            if b.get('名称') == 名:
                b['路径'] = 路径
    else:
        with open(os.path.join(库根, 路径), 'w', encoding='utf-8') as f:
            f.write(块.get('源码', ''))
        块['路径'] = 路径
        idx['块'].append(块)
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    return 路径


def _cli(argv=None):
    p = argparse.ArgumentParser(
        description='LLM 兜底生成器（零 token 本地规则 / 配置 key 后调真实 LLM）')
    p.add_argument('需求', help='自然语言需求文本')
    p.add_argument('--注册', action='store_true', help='生成后写入 生成/ 并注册进索引')
    p.add_argument('--库根', default=_HERE)
    args = p.parse_args(argv)

    blk = generate_block(args.需求, 库根=args.库根)
    if not blk:
        print('无法生成（本地规则不覆盖，且未配置真实 LLM）：' + args.需求)
        return 1
    if args.注册:
        注册(blk, 库根=args.库根)
        print('已注册：%s（%s）' % (blk['名称'], blk.get('路径')))
    print(json.dumps(blk, ensure_ascii=False, indent=2,
                     default=lambda o: o if isinstance(o, str) else str(o)))
    return 0


if __name__ == '__main__':
    import argparse  # noqa: E402  (置于文件尾，避免顶层 import 顺序问题)
    raise SystemExit(_cli())