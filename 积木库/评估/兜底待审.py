"""兜底待审台（Q4 计划 1.3 护栏的人工复审面）。

`组合.py` 的兜底生成块会先过 体检+冒烟 护栏：通过则留在 索引.json（零 token 复用），
不通过则回滚到 `积木库/生成/待审/` 并记入 `待审清单.jsonl`，不污染索引。本脚本是人眼复审入口：

  python 积木库/评估/兜底待审.py                 # 列出待审块
  python 积木库/评估/兜底待审.py --通过 转二进制   # 人工确认无误后正式入库（写 生成/ + 索引）
  python 积木库/评估/兜底待审.py --删除 转二进制   # 确认是坏块，丢弃
  python 积木库/评估/兜底待审.py --试运行 转二进制 # 用 组合 跑一次看输出，辅助判断

注意：自动护栏已拦过一遍（体检+冒烟），这里主要是「人工抽检」与「放行」。
"""
import os, sys, json, argparse, importlib.util

_LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _LIB)

_spec = importlib.util.spec_from_file_location("兜", os.path.join(_LIB, '兜底生成器.py'))
兜 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(兜)

待审目录 = 兜.待审目录(_LIB)
清单路径 = os.path.join(待审目录, '待审清单.jsonl')


def _读清单():
    if not os.path.isfile(清单路径):
        return []
    return [json.loads(l) for l in open(清单路径, encoding='utf-8') if l.strip()]


def _写清单(rows):
    os.makedirs(待审目录, exist_ok=True)
    with open(清单路径, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def 列表():
    rows = _读清单()
    if not rows:
        print('（无待审块）')
        return
    print('══ 待审块 %d 个 ══' % len(rows))
    for r in rows:
        print('  %-14s %s ｜ %s' % (r['名称'], r.get('时间', ''), r.get('原因', '')))


def 通过(名):
    rows = _读清单()
    hit = [r for r in rows if r['名称'] == 名]
    if not hit:
        print('待审中无此块：' + 名)
        return 1
    blk = hit[0]['块']
    # 正式入库：写 生成/<名>.duan 并追加索引
    兜.注册(blk, 库根=_LIB)
    # 删除待审副本
    待审文件 = os.path.join(待审目录, '%s.duan' % 名)
    if os.path.isfile(待审文件):
        os.remove(待审文件)
    _写清单([r for r in rows if r['名称'] != 名])
    print('已正式入库：%s（生成/ + 索引.json）' % 名)
    return 0


def 删除(名):
    rows = _读清单()
    if not any(r['名称'] == 名 for r in rows):
        print('待审中无此块：' + 名)
        return 1
    for r in rows:
        if r['名称'] == 名:
            待审文件 = os.path.join(待审目录, '%s.duan' % 名)
            if os.path.isfile(待审文件):
                os.remove(待审文件)
    _写清单([r for r in rows if r['名称'] != 名])
    print('已丢弃待审块：' + 名)
    return 0


def 试运行(名):
    rows = _读清单()
    hit = [r for r in rows if r['名称'] == 名]
    if not hit:
        print('待审中无此块：' + 名)
        return 1
    需求 = hit[0]['块'].get('描述') or 名
    print('（用 组合 试运行：%s）' % 需求)
    import subprocess
    p = subprocess.run([sys.executable, '组合.py', 需求, '--json', '--无缓存'],
                       cwd=_LIB, capture_output=True, text=True)
    out = p.stdout + p.stderr
    # 打印运行输出尾部
    print(out[-1500:])
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--通过', default=None, help='正式入库某待审块')
    ap.add_argument('--删除', default=None, help='丢弃某待审块')
    ap.add_argument('--试运行', default=None, help='用 组合 试跑某待审块看输出')
    a = ap.parse_args()
    if a.通过:
        raise SystemExit(通过(a.通过))
    if a.删除:
        raise SystemExit(删除(a.删除))
    if a.试运行:
        raise SystemExit(试运行(a.试运行))
    列表()
