"""真实 LLM 兜底首跑 harness（Q4 计划 1.2）。

对 `库外意图20.json` 中每条库外意图跑通「选不准 → 兜底生成新块 → 注册 → 运行」闭环，
记录结构化 `运行日志.jsonl`，并统计「成功沉淀」比例（生成块通过 体检+冒烟 且 组合运行成功）。

用法：
  python 积木库/评估/兜底首跑.py                # 跑全部 20 条，结果写 运行日志.jsonl
  python 积木库/评估/兜底首跑.py --保留         # 不回滚索引/生成（真实沉淀，会改 索引.json）
  python 积木库/评估/兜底首跑.py --只 阶乘       # 只跑含某关键字的意图

说明：
  - 走真实 `组合.py --json` 链路（含执行闭环与运行期兜底），与线上行为一致。
  - 无 api_key 时，本地规则覆盖的 7 类走本地规则生成器跑通；其余需真实 LLM key（见 llm_config.json）。
  - 默认每跑完一条即回滚 索引.json / 生成/，保持仓库干净；要真正沉淀用 --保留。
  - token 成本字段当前为 null；待 1.3 在 兜底生成器 接入用量回传后填充。
"""
import os, sys, json, shutil, importlib.util, subprocess, argparse, time

_LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 积木库/
_PY = sys.executable  # 由调用方用 venv 解释器运行本脚本
sys.path.insert(0, _LIB)


def _载模块(名, 路径):
    spec = importlib.util.spec_from_file_location(名, 路径)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


体 = _载模块('体', os.path.join(_LIB, '评估', '体检.py'))
冒 = _载模块('冒', os.path.join(_LIB, '评估', '冒烟.py'))
兜 = _载模块('兜', os.path.join(_LIB, '兜底生成器.py'))

意图文件 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '库外意图20.json')
日志文件 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '运行日志.jsonl')
索引路径 = os.path.join(_LIB, '索引.json')
生成目录 = os.path.join(_LIB, '生成')


def _有key():
    try:
        cfg = 兜.load_config()
        return bool(cfg.get('api_key'))
    except Exception:
        return False


def _块名集():
    索引 = json.load(open(索引路径, encoding='utf-8'))
    return {b.get('名称') for b in 索引.get('块', [])}


def _生成文件集():
    if not os.path.isdir(生成目录):
        return set()
    s = set()
    for 根, _, 文件 in os.walk(生成目录):
        for f in 文件:
            s.add(os.path.join(根, f))
    return s


def _回滚(索引快照, 生成快照):
    shutil.copy(索引快照, 索引路径)
    now = _生成文件集()
    for f in (now - 生成快照):
        try:
            os.remove(f)
        except OSError:
            pass


def _取诊断(stdout):
    """从 组合.py --json 的输出里抽出 JSON 诊断块（取最后一个，兼容规划失败路径）。"""
    marker = '── JSON 诊断 ──'
    i = stdout.rfind(marker)
    if i < 0:
        return {}
    try:
        return json.loads(stdout[i + len(marker):].strip())
    except Exception:
        return {}


def _体检合规(新名):
    r = 体.收集()
    错 = r.get('错') or []
    return not any(新名 in e for e in 错)


def _冒烟合规(新名):
    res = 冒.跑(块名=[新名], 并发=1)
    问题 = res.get('问题块') or []
    return (len(问题) == 0) and res.get('可运行率', 0) >= 1.0


def 主(只=None, 保留=False, 冷却=0):
    意图 = json.load(open(意图文件, encoding='utf-8'))
    if 只:
        意图 = [x for x in 意图 if 只 in x['需求'] or 只 in x.get('分类', '')]
    有key = _有key()
    来源 = 'LLM' if 有key else '本地规则'
    print('api_key：%s ｜ 兜底来源判定：%s ｜ 回滚：%s'
          % ('已配置' if 有key else '未配置(空)', 来源, '否(保留)' if 保留 else '是'))
    print('待测 %d 条' % len(意图))

    rows = []
    for it in 意图:
        需求 = it['需求']
        输入 = it.get('输入', '[1,2,3,4,5]')
        期望 = it.get('期望')  # 验收语义校验：块在「输入」下的正确输出文本
        索引快照 = 索引路径 + '.runbak'
        shutil.copy(索引路径, 索引快照)
        生成前 = _生成文件集()
        块名前 = _块名集()

        try:
            cmd = [_PY, '组合.py', 需求, '--输入', 输入, '--json', '--无缓存']
            if 期望:
                cmd += ['--期望', 期望]
            p = subprocess.run(cmd, cwd=_LIB, capture_output=True, text=True, timeout=180)
            out = p.stdout + '\n' + p.stderr
            诊断 = _取诊断(p.stdout)
        except Exception as e:
            out = ''
            诊断 = {'异常': repr(e)}

        是兜底 = 诊断.get('是兜底', False)
        成功 = 诊断.get('成功', False)  # 已含语义校验（传了 --期望 时）
        兜底理由 = 诊断.get('兜底理由', '')

        新块 = sorted(_块名集() - 块名前)
        新名 = 新块[0] if 新块 else None
        生成块名 = 诊断.get('生成块名') or 新名
        兜底来源 = 诊断.get('兜底来源') or (来源 if 是兜底 else None)
        token成本 = 诊断.get('token成本')
        体检合规 = _体检合规(新名) if 新名 else False
        冒烟合规 = _冒烟合规(新名) if 新名 else False
        语义正确 = 诊断.get('语义正确') if 期望 else None
        成功沉淀 = bool(是兜底 and 成功 and 新名 and 体检合规 and 冒烟合规)

        row = {
            '需求': 需求, '输入': 输入, '期望': 期望, '分类': it.get('分类'), '期望能力': it.get('期望能力'),
            '是兜底': 是兜底, '成功': 成功, '语义正确': 语义正确, '兜底理由': 兜底理由,
            '兜底来源': 兜底来源, '生成块名': 生成块名,
            '体检合规': 体检合规, '冒烟合规': 冒烟合规, '成功沉淀': 成功沉淀,
            '耗时ms': 诊断.get('规划耗时ms'), 'token成本': token成本,
            '备注': 诊断.get('异常', '') or ('' if 成功 else '组合未成功'),
        }
        rows.append(row)
        mark = '✓沉淀' if 成功沉淀 else ('✗失败' if 是兜底 else '～库内')
        语义标 = '' if 语义正确 is None else (' 语义%s' % ('✓' if 语义正确 else '✗'))
        print('  [%s] %s → 生成=%s 体检=%s 冒烟=%s%s %s'
              % (mark, 需求[:24], 新名 or '-',
                 '✓' if 体检合规 else '✗', '✓' if 冒烟合规 else '✗', 语义标,
                 '' if 成功 else '运行未成功'))
        if not 保留:
            _回滚(索引快照, 生成前)
        try:
            os.remove(索引快照)
        except OSError:
            pass
        if 冷却 and it is not 意图[-1]:
            time.sleep(冷却)

    触发 = sum(1 for r in rows if r['是兜底'])
    沉淀 = sum(1 for r in rows if r['成功沉淀'])
    print('\n══ 兜底首跑汇总 ══')
    print('  触发兜底：%d/%d' % (触发, len(rows)))
    print('  成功沉淀：%d/%d（验收线 ≥15/20）' % (沉淀, len(rows)))
    if 触发:
        print('  沉淀率：%.1f%%' % (100.0 * 沉淀 / 触发))
    if not 有key:
        print('  ⚠ 未配置 api_key：本地规则 7 类已验证；其余 %d 条需真实 LLM key 才能跑通。'
              % (len(rows) - sum(1 for r in rows if r['分类'] == '本地规则')))

    try:
        with open(日志文件, 'w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        print('  日志：%s' % 日志文件)
    except OSError as e:
        # 主日志文件被别的进程占用（重叠跑/编辑器锁）时降级写副本，避免整轮崩溃
        alt = 日志文件.replace('.jsonl', '_明细.jsonl')
        with open(alt, 'w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        print('  日志（主文件被占用，写副本）：%s  [%s]' % (alt, e))
    return 沉淀, len(rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--只', default=None, help='只跑含该关键字的意图')
    ap.add_argument('--保留', action='store_true', help='不回滚，真实沉淀到 索引.json')
    ap.add_argument('--冷却', type=int, default=0, help='每条意图之间的冷却秒数（规避 429 限流）')
    a = ap.parse_args()
    主(只=a.只, 保留=a.保留, 冷却=a.冷却)
