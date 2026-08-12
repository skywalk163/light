# -*- coding: utf-8 -*-
"""光明积木粘合器 v0 —— 把「选块方案」内联合成为单一可运行 .light。

移植自 jikuai tools/ai-bridge/glue.py，但关键差异：**内联而非 import**。
原因：光明单文件 `run` 当前不支持跨 .light 导入（导入走 Python import
机制，需整个项目 build 合并）。所以把选中积木的段落定义直接拼进生成文件，
相当于「成语式宏展开」的简化版——单文件即可 `light run`，零外部依赖。

方案 JSON 结构见 `协议.md`（与 jikuai 一致），示例::
    {
      "需求": "对一批数字求和再算平均",
      "共享": [{"名": "赵料", "值": "[1, 2, 3, 4, 5]"}],
      "步骤": [
        {"块": "求和", "领域": "数据", "导出名": "汇总", "说明": "求和", "参数": ["赵料"]},
        {"块": "均值", "领域": "数据", "导出名": "中位", "说明": "算平均", "参数": ["赵料"]}
      ],
      "打印": ["赵果1", "赵果2"]
    }

用法::
    python 积木库/粘合.py 方案.json -o 组合结果.light
"""

import argparse
import json
import os
import sys

_HERE = os.path.abspath(os.path.dirname(__file__))


def _提取段落(路径):
    """读取积木 .light，去掉注释行与 `导出` 声明，返回纯段落源码。

    每块文件主体即单一导出段落；去掉头部 `#` 注释与 `导出 X` 行后，
    剩余即是可内联的段落定义。
    """
    with open(路径, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    out = []
    for ln in lines:
        s = ln.strip()
        if s.startswith('#'):
            continue
        if s.startswith('导出'):
            continue
        out.append(ln.rstrip('\n'))
    return '\n'.join(out).strip('\n')


def _结果变量(i):
    """第 i 步（0 基）的结果变量名，沿用 jikuai 的「赵果N」约定。"""
    return '赵果%d' % (i + 1)


def synthesize(方案, 库根=_HERE):
    """把选块方案合成为单一 .light 源码字符串。"""
    步骤 = 方案.get('步骤') or []
    if not 步骤:
        raise ValueError('方案缺少非空的 步骤 字段')

    lines = ['# 由 光明积木桥接 v0（选块 + 内联粘合）自动合成', '']
    if 方案.get('需求'):
        lines.append('# 需求：' + str(方案['需求']))
        lines.append('')

    # 1) 内联积木段落（按步骤首次出现去重）
    seen = set()
    for s in 步骤:
        key = (s['领域'], s['块'])
        if key in seen:
            continue
        seen.add(key)
        # 路径查找优先级：索引路径 > 领域/名称.light > blocks_v5/领域/名称.light
        blk_path = os.path.join(库根, s.get('路径') or '')
        if not (blk_path and os.path.isfile(blk_path) and os.path.getsize(blk_path) > 0):
            blk_path = os.path.join(库根, s['领域'], s['块'] + '.light')
        if not (os.path.isfile(blk_path) and os.path.getsize(blk_path) > 0):
            blk_path = os.path.join(库根, 'blocks_v5', s['领域'], s['块'] + '.light')
        if os.path.isfile(blk_path) and os.path.getsize(blk_path) > 0:
            lines.append('# ── 积木：%s（%s）──' % (s['块'], s['领域']))
            lines.append(_提取段落(blk_path))
            lines.append('')

    # 2) 共享常量 / 输入
    共享 = 方案.get('共享') or []
    if 共享:
        for item in 共享:
            if not item.get('名') or item.get('值') is None:
                raise ValueError('共享项须含 名 与 值：%r' % (item,))
            lines.append('设 %s 为 %s。' % (item['名'], item['值']))
        lines.append('')

    # 3) 步骤调用
    结果变量 = []
    for i, s in enumerate(步骤):
        var = _结果变量(i)
        结果变量.append(var)
        if s.get('说明'):
            lines.append('# 步骤 %d：%s' % (i + 1, s['说明']))
        参数 = s.get('参数') or []
        实参 = ', '.join(str(p) for p in 参数)
        lines.append('设 %s 为 %s(%s)。' % (var, s['导出名'], 实参))

    # 4) 打印
    lines.append('')
    打印列表 = 方案.get('打印') or 结果变量
    for 名 in 打印列表:
        lines.append('打印(%s)。' % 名)

    return '\n'.join(lines).rstrip() + '\n'


def _cli(argv=None):
    p = argparse.ArgumentParser(description='光明积木粘合器 v0（内联合成 .light）')
    p.add_argument('方案', help='选块方案 JSON 文件路径')
    p.add_argument('-o', '--输出', default=None, help='输出 .light 路径（缺省则打印到 stdout）')
    args = p.parse_args(argv)

    with open(args.方案, 'r', encoding='utf-8') as f:
        方案 = json.load(f)
    code = synthesize(方案)
    if args.输出:
        with open(args.输出, 'w', encoding='utf-8') as f:
            f.write(code)
        print('已生成：' + args.输出)
    else:
        sys.stdout.write(code)
    return 0


if __name__ == '__main__':
    raise SystemExit(_cli())