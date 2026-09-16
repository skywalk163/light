#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI 基线门 `check_ci_baseline.py` —— 拦「基线之外的新增打红」，并给出失败原因摘要。

与本仓 `tools/ci/check_regression.py` 的关系
--------------------------------------------
`tools/ci/check_regression.py` 是 **CI 内部用的极简闸门**：只吃 junit，只打印用例 key。
本脚本是它的「开发机友好超集」，用于把「基线外新增打红」这件事变成**本地可自查**的能力：

  * 可以**自己跑 pytest**（不必先手工产出 junit），也可以复用已有 `--junit` 报告；
  * 输出 `测试名 + 失败原因摘要 + 是否基线内` 三列，而不是只给 key；
  * `--warn` 只警告不阻断（观察模式），默认阻断（退出码 1）。

⚠️ 本脚本修掉了本仓基线文件的一个**真实身份格式缺陷**（2026-09-16 R40 实测）
----------------------------------------------------------------------------
`tests/ci_baseline_failures.txt` 里 12 条 e2e 记录是**转义形态**：
    tests.e2e.test_e2e_chain::test_duan_run[E\\u9636\\u6bb5_L3L4\\u539f\\u751f\\u8bed\\u6cd5/E4_L4_...]
而 `pytest --junitxml` 写出的 `name` 属性是**原始汉字**：
    test_duan_run[E阶段_L3L4原生语法/E4_L4_沙箱隔离验证.light]
两边做集合差时**永远不会相交** ⇒ 这 12 条会被**永久误报为「新增打红」**，
CI 回归闸门因此恒红（与 memory 记录的 "run 182 = failure / 基线已过期" 现象一致）。
本脚本在比较前对 **两侧**都做 `unicode_escape` 解码归一，因此能正确识别它们「在基线内」。
（不改基线文件本身：`tools/ci/check_regression.py` 是 CI 在跑的脚本，改动它属另一 PR 范围；
  详见交付报告 `_task4_R40_互举回归基建.md` 的「基线身份格式失配」一节。）

用法
----
    # ① 自行跑 pytest（默认；最省事，开发机用）
    python scripts/check_ci_baseline.py                     # 默认跑 tests/ 全量
    python scripts/check_ci_baseline.py tests/unit tests/e2e/test_e2e_chain.py
    python scripts/check_ci_baseline.py -k "lexer"          # 透传 -k（写法见 --pytest-args）

    # ② 复用已有 junit（CI 用；也避开 Windows 控制台中文用例名的双重编码损坏）
    python scripts/check_ci_baseline.py --junit .ci/report.xml
    python scripts/check_ci_baseline.py --junit '.ci/*.xml'

    # ③ 只警告不阻断
    python scripts/check_ci_baseline.py --junit .ci/report.xml --warn

    # ④ 修好一批后刷新基线
    python scripts/check_ci_baseline.py --junit .ci/report.xml --write-baseline

    # ⑤ 只跑基线里登记的那些测试文件（CI 上省时）
    python scripts/check_ci_baseline.py --junit .ci/report.xml --only-baseline

    # ⑥ 额外产出一份 JSON 报告
    python scripts/check_ci_baseline.py --junit .ci/report.xml --json gate.json

三种「不在打红清单里」的基线条目要分清
--------------------------------------
    * **已转绿**    本跑通过            → 提示刷新基线
    * **被跳过(SKIP)** 本跑 `pytest.skip()` → **既非绿也非红**，单独列出并警告「勿据此刷新基线」
    * **本次未收集到** 没跑那个文件       → 同「已转绿」的告警口径
第 2 类是本脚本踩过的坑：本机缺 pandas/matplotlib 等三方库时，大量基线用例会 SKIP 掉，
若把 SKIP 当成「已转绿」，使用者一刷新基线就把真实欠账**静默删掉**了。

退出码
------
    0   无基线外新增打红（绿）
    1   存在基线外新增打红（红 / 回归）
    2   用法或环境错误（找不到 junit / 基线，或 pytest 跑不起来）

只依赖 Python 标准库（argparse / fnmatch / glob / json / subprocess / xml.etree）。
"""

from __future__ import annotations

import argparse
import fnmatch
import glob
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

# ── 路径：本脚本位于 <repo>/scripts/ 下，仓库根 = 上一级 ─────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BASELINE = os.path.join(ROOT, 'tests', 'ci_baseline_failures.txt')


# =============================================================================
# 工具
# =============================================================================
def _utf8_stdout():
    """Windows 控制台默认 GBK/cp1252，print 中文会 UnicodeEncodeError 堵死整步。

    与 tools/ci/check_regression.py 同口径：强制 UTF-8 输出（reconfigure 自 3.7 起可用）。
    """
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8')
            except Exception:                                   # noqa: BLE001
                pass


def norm_key(key: str) -> str:
    """把用例身份归一为「原始字符」形态。

    基线文件里部分条目是 `\\u9636` 这样的转义文本，而 junit 里是原始汉字；
    不归一就永远匹配不上（见模块 docstring 的「身份格式缺陷」一节）。
    对**两侧**都做同样归一，所以幂等、无副作用：

      * `'E\\u9636\\u6bb5'` → `'E阶段'`
      * `'E阶段'`          → `'E阶段'`（解码后不含反斜杠，原样返回）

    用 `unicode_escape` 解码时只对含反斜杠的串做，且失败则原样返回——
    绝不因某个奇怪用例名把整个闸门弄崩。
    """
    if not key or '\\' not in key:
        return key
    try:
        # latin-1 往返保住「本来就不是转义」的字符
        return key.encode('latin-1', 'backslashreplace').decode('unicode_escape')
    except Exception:                                           # noqa: BLE001
        return key


def load_baseline(path: str) -> set:
    """读基线：跳过空行与 `#` 注释，逐行归一。"""
    out = set()
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith('#'):
                out.add(norm_key(line))
    return out


def _reason_of(case) -> str:
    """从 junit testcase 里取「失败原因摘要」（单行、截断）。"""
    node = case.find('failure')
    if node is None:
        node = case.find('error')
    if node is None:
        return ''
    text = (node.get('message') or '').strip()
    if not text:
        text = (node.text or '').strip()
    # 多行堆栈只留第一行有意义的部分（跳过空行与 E/pytest 装饰行）
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith('E ') or s == 'E':
            continue
        s = s.lstrip('E').strip() or s
        return s[:160]
    return text.replace('\n', ' ')[:160]


def collect_from_junit(patterns) -> tuple:
    """从一个或多个 junit xml（支持通配）收集打红集合、跳过集合与统计。

    返回 `(failed, keys_raw, skipped, stats, files)`：
      * `failed`   归一 key -> 失败原因摘要
      * `keys_raw` 归一 key -> junit 原始 key（展示用）
      * `skipped`  归一 key 的**被跳过**用例集合（基线里却 skip 的条目**不算「已转绿」**，
                   否则会诱导使用者刷新基线、把真实欠账静默删掉——见 main() 的 SKIP 处理）
    """
    files = []
    for p in patterns:
        if os.path.isabs(p):
            files.extend(sorted(glob.glob(p)))
        else:
            files.extend(sorted(glob.glob(os.path.join(ROOT, p))))
            files.extend(sorted(glob.glob(os.path.join(os.getcwd(), p))))
    files = sorted(set(files))
    if not files:
        raise FileNotFoundError('; '.join(patterns))

    failed = {}                     # 归一 key -> 原因摘要
    keys_raw = {}                   # 归一 key -> junit 原始 key（展示用）
    skipped = set()                 # 归一 key 的被跳过用例
    stats = {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
    for path in files:
        root = ET.parse(path).getroot()
        suites = root.findall('testsuite') if root.tag == 'testsuites' else [root]
        for suite in suites:
            for key in stats:
                stats[key] += int(suite.get(key, 0) or 0)
            for case in suite.iter('testcase'):
                raw = '%s::%s' % (case.get('classname') or '', case.get('name') or '')
                if case.find('failure') is not None or case.find('error') is not None:
                    k = norm_key(raw)
                    failed[k] = _reason_of(case)
                    keys_raw[k] = raw
                elif case.find('skipped') is not None:
                    skipped.add(norm_key(raw))
    return failed, keys_raw, skipped, stats, files


def run_pytest(targets, extra_args, tmpdir) -> str:
    """自己跑 pytest 并产出 junit（永远用 junit，绝不解析控制台输出——

    Windows 控制台对中文用例名是双重编码，`-rf` 日志里的 nodeid **有损**，
    按 classname+name 重建 junit 才是可信采集口径）。
    """
    xml = os.path.join(tmpdir, 'check_ci_baseline.xml')
    cmd = [sys.executable, '-m', 'pytest', '-p', 'no:cacheprovider',
           '-q', '--no-header', '--junitxml=' + xml] + list(extra_args) + list(targets)
    print('[门] 运行：%s' % ' '.join(cmd[:6] + (['...'] if len(cmd) > 6 else [])))
    proc = subprocess.run(cmd, cwd=ROOT)
    if not os.path.isfile(xml):
        raise RuntimeError('pytest 未产出 junit（退出码 %d）' % proc.returncode)
    return xml


def baseline_test_files(baseline) -> list:
    """把基线里的 `classname::name` 还原成 pytest 可传的测试文件路径（用于 --only-baseline）。

    `tests.e2e.test_e2e_chain` → `tests/e2e/test_e2e_chain.py`
    目录形式的 classname（如 `tests.unit` 没有具体文件）→ `tests/unit`
    """
    paths = set()
    for key in baseline:
        classname = key.split('::', 1)[0]
        if not classname.startswith('tests'):
            continue
        rel = classname.replace('.', '/')
        cand_py = os.path.join(ROOT, rel + '.py')
        if os.path.isfile(cand_py):
            paths.add(rel + '.py')
        elif os.path.isdir(os.path.join(ROOT, rel)):
            paths.add(rel)
        else:
            # 退一步：用其所在目录
            d = os.path.dirname(rel)
            if d and os.path.isdir(os.path.join(ROOT, d)):
                paths.add(d)
    return sorted(paths)


def write_baseline(path, failed_raw, stats):
    """生成/刷新基线（身份用 junit 原始形态；不再写入转义形态）。"""
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# CI 回归基线：本仓库当前的既有失败用例（存量欠账，非本次引入）\n')
        fh.write('# 身份格式：junit 的 classname::name（原始字符，**不要**写 \\uXXXX 转义形态）\n')
        fh.write('# 语义：CI 只拦「基线之外」的新增打红；修好一批后重新生成并提交本文件。\n')
        fh.write('#   python scripts/check_ci_baseline.py --junit .ci/report.xml --write-baseline\n')
        fh.write('# 快照汇总：collected=%d failures=%d errors=%d skipped=%d\n'
                 % (stats['tests'], stats['failures'], stats['errors'], stats['skipped']))
        fh.write('# 生成机：%s  python %s\n'
                 % (sys.platform, '.'.join(map(str, sys.version_info[:3]))))
        for key in sorted(failed_raw):
            fh.write(key + '\n')


# =============================================================================
# 主流程
# =============================================================================
def main(argv=None):
    _utf8_stdout()
    ap = argparse.ArgumentParser(
        description='基线外打红 CI 门：拦「基线之外的新增打红」，可自跑 pytest 或复用 junit。',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('targets', nargs='*',
                    help='pytest 目标（自跑模式使用；默认 tests）')
    ap.add_argument('--junit', action='append', default=[],
                    help='复用已有 pytest --junitxml 报告（可多次/支持通配）；给了就不再自跑')
    ap.add_argument('--baseline', default=DEFAULT_BASELINE,
                    help='基线文件（默认 tests/ci_baseline_failures.txt）')
    ap.add_argument('--write-baseline', action='store_true',
                    help='把本次打红结果写成新基线（生成模式）')
    ap.add_argument('--warn', action='store_true',
                    help='只警告不阻断（退出码恒 0，除非环境错误）')
    ap.add_argument('--only-baseline', action='store_true',
                    help='自跑模式下只跑基线里登记过的测试文件/目录（省时）')
    ap.add_argument('--soft-classname', action='append', default=[],
                    help='classname 通配符：命中的用例只报不拦（与 tools/ci/check_regression.py 同口径）')
    ap.add_argument('--pytest-args', default='',
                    help='透传给 pytest 的额外参数（空格分隔），如 --pytest-args "-k lexer -x"')
    ap.add_argument('--json', default='',
                    help='额外输出 JSON 报告到该路径')
    args = ap.parse_args(argv)

    baseline_path = args.baseline if os.path.isabs(args.baseline) \
        else os.path.join(ROOT, args.baseline)

    baseline = set()
    if os.path.isfile(baseline_path):
        try:
            baseline = load_baseline(baseline_path)
        except Exception as exc:                                # noqa: BLE001
            print('[门] 基线读取失败 %s：%s' % (baseline_path, exc))
            return 2
    elif not args.write_baseline:
        print('[门] 找不到基线 %s。首次接入请加 --write-baseline 生成并提交。' % baseline_path)
        return 2

    tmpdir_obj = None
    try:
        # ── 采集打红清单 ────────────────────────────────────────────────
        if args.junit:
            failed, keys_raw, skipped, stats, files = collect_from_junit(args.junit)
            print('[门] 读入 %d 份 junit；collected=%d failures=%d errors=%d skipped=%d'
                  % (len(files), stats['tests'], stats['failures'], stats['errors'], stats['skipped']))
        else:
            targets = list(args.targets)
            if args.only_baseline and baseline:
                derived = baseline_test_files(baseline)
                if derived:
                    targets = derived
                    print('[门] --only-baseline：只跑基线登记的 %d 个目标' % len(derived))
            if not targets:
                targets = ['tests']
            extra = args.pytest_args.split() if args.pytest_args.strip() else []
            tmpdir_obj = tempfile.TemporaryDirectory(prefix='ci_baseline_')
            xml = run_pytest(targets, extra, tmpdir_obj.name)
            failed, keys_raw, skipped, stats, files = collect_from_junit([xml])
            print('[门] 自跑完成；collected=%d failures=%d errors=%d skipped=%d'
                  % (stats['tests'], stats['failures'], stats['errors'], stats['skipped']))
    except FileNotFoundError as exc:
        print('[门] 找不到 junit 报告：%s —— pytest 那步可能没跑起来' % exc)
        return 2
    except ET.ParseError as exc:
        print('[门] junit 解析失败：%s' % exc)
        return 2
    except RuntimeError as exc:
        print('[门] %s' % exc)
        return 2
    finally:
        if tmpdir_obj is not None:
            try:
                tmpdir_obj.cleanup()
            except Exception:                                   # noqa: BLE001
                pass

    # ── 软通配（只报不拦）──────────────────────────────────────────────
    def hit_soft(key):
        classname = key.split('::', 1)[0]
        return any(fnmatch.fnmatch(classname, p) for p in args.soft_classname)

    soft = {k: v for k, v in failed.items() if hit_soft(k)}
    hard = {k: v for k, v in failed.items() if not hit_soft(k)}
    baseline_hard = {k for k in baseline if not hit_soft(k)}

    # ── 生成模式 ────────────────────────────────────────────────────────
    if args.write_baseline:
        raw = sorted(keys_raw.get(k, k) for k in hard)
        if soft:
            print('[门] 注意：%d 条软通配命中项**未写入**基线（它们本就非阻塞）' % len(soft))
        write_baseline(baseline_path, raw, stats)
        print('[门] 已写入基线 %s（%d 条）' % (baseline_path, len(raw)))
        return 0

    new_red = sorted(set(hard) - baseline_hard)
    # 基线内、本次**被跳过（SKIP）**的条目：既不是红、也不是绿。
    # ⚠️ 若直接把它算作「已转绿」，会诱导使用者 `--write-baseline` 刷新基线
    #    从而把真实欠账条目**静默删掉**（本机缺三方库时大量用例 SKIP，极易踩）。
    skipped_baseline = [k for k in sorted(baseline_hard) if k in skipped and k not in hard]
    fixed = sorted(baseline_hard - set(hard) - set(skipped_baseline))

    # ── 报告 ────────────────────────────────────────────────────────────
    print('\n' + '=' * 78)
    print('基线门报告：基线 %d 条 ｜ 本次打红 %d 条（硬） + %d 条（软）｜ 新增打红 %d 条'
          % (len(baseline_hard), len(hard), len(soft), len(new_red)))
    print('=' * 78)
    print('%-6s %-64s %s' % ('状态', '测试名', '失败原因摘要'))
    print('-' * 78)
    for k in sorted(hard):
        in_base = '基线内' if k in baseline_hard else '新增'
        print('%-6s %-64s %s' % (in_base, keys_raw.get(k, k), hard[k]))
    for k in sorted(soft):
        print('%-6s %-64s %s' % ('软忽略', keys_raw.get(k, k), soft[k]))

    if fixed:
        print('\n以下用例相比基线已转绿（修好请刷新基线，别让基线虚高）：')
        for k in fixed:
            print('   - ' + k)
        print('   ⚠️ 注意：若本次只跑了部分用例（如只给了一个 junit），'
              '「已转绿」可能只是**这次没收集到**，不代表真的修好了。')

    if skipped_baseline:
        print('\n以下基线条目本次**被跳过（SKIP，未真正执行）**——'
              '既非转绿也非回归，**请勿据此刷新基线**（会静默删掉真实欠账）：')
        for k in skipped_baseline:
            print('   ~ ' + k)
        print('   ℹ️ 常见原因：依赖的第三方库/外部程序在当前机器不可见，'
              '用例 `pytest.skip()` 掉了。换到基线同平台的机器上跑才有意义。')

    if new_red:
        print('\n基线外新增打红（视为回归）：')
        for k in new_red:
            print('   ! ' + keys_raw.get(k, k) + '   ← ' + hard.get(k, ''))
        print('\n判据：新增打红 %d 条 ⇒ %s'
              % (len(new_red), '仅警告（--warn）' if args.warn else '阻断（退出码 1）'))
        rc = 0 if args.warn else 1
    else:
        print('\n通过：无基线外新增打红。')
        rc = 0

    if args.json:
        out = args.json if os.path.isabs(args.json) else os.path.join(ROOT, args.json)
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump({'root': ROOT, 'baseline_file': baseline_path,
                       'baseline_count': len(baseline_hard),
                       'stats': stats,
                       'failed_hard': [{'id': keys_raw.get(k, k), 'reason': hard[k],
                                        'in_baseline': k in baseline_hard} for k in sorted(hard)],
                       'failed_soft': [keys_raw.get(k, k) for k in sorted(soft)],
                       'new_red': [keys_raw.get(k, k) for k in new_red],
                       'skipped_in_baseline': skipped_baseline,
                       'fixed': fixed, 'exit_code': rc},
                      fh, ensure_ascii=False, indent=2)
        print('[门] JSON 报告：%s' % out)
    return rc


if __name__ == '__main__':
    sys.exit(main())
