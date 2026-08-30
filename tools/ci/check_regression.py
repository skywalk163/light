# -*- coding: utf-8 -*-
"""CI 回归闸门：只拦「新增打红」，不要求全绿。

背景：本仓库当前有一批既有失败（v7 收尾期的存量欠账，见
docs/v7_失败用例根因聚类工单.md，其中最大的一类是「单 02 · 紧凑写法分词族」）。
要求 CI 全绿会让它常红、失去信号，所以判据改成与基线快照对比：

  - 出现基线里没有的 failed/error  → 退出码 1（真回归，必须拦）
  - 基线里有、这次没红             → 只提示（说明修好了，记得更新基线）
  - failed 总数超过基线条数        → 退出码 1（兜底，防止基线文件被绕过）

用例身份用 junit 的 `classname::name`，不用文件路径——路径分隔符在 Windows
开发机和 FreeBSD runner 上不一致，classname 是点号形式，跨平台稳定。

用法：
    # 对比模式（CI 用）
    python3 tools/ci/check_regression.py --junit .ci/report.xml \
        --baseline tests/ci_baseline_failures.txt
    # 生成/刷新基线（修好一批后手工执行并提交）
    python3 tools/ci/check_regression.py --junit .ci/report.xml \
        --write-baseline tests/ci_baseline_failures.txt

`--soft-classname 'tests.test_*'`：命中的用例只报不拦。给根目录那批历史上
`|| true` 跑的测试留的口子——它们并进「一次 pytest tests」是为了省启动开销，
不代表口径升级成判绿点。详见 命中软通配() 的说明。
"""

from __future__ import annotations

import argparse
import fnmatch
import glob
import sys
import xml.etree.ElementTree as ET


def collect_failures(junit_globs):
    """从一个或多个 junit xml 里取出打红用例集合与汇总计数。"""
    failed = set()
    stats = {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
    files = []
    for g in junit_globs:
        files.extend(sorted(glob.glob(g)))
    if not files:
        raise FileNotFoundError('; '.join(junit_globs))

    for path in files:
        root = ET.parse(path).getroot()
        suites = root.findall('testsuite') if root.tag == 'testsuites' else [root]
        for suite in suites:
            for key in stats:
                stats[key] += int(suite.get(key, 0) or 0)
            for case in suite.iter('testcase'):
                if case.find('failure') is not None or case.find('error') is not None:
                    failed.add('%s::%s' % (case.get('classname') or '', case.get('name') or ''))
    return failed, stats, files


def load_baseline(path):
    out = set()
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith('#'):
                out.add(line)
    return out


def 命中软通配(key, patterns):
    """key 是 `classname::name`；只用 classname 部分匹配通配符。

    用途：根目录 tests/test_*.py 这批在历史 CI 里是 `|| true` 跑的（不判绿、也不进
    junit）。v7 后期把它们并进「一次 pytest tests」是为了省掉重复启动，**不是**
    偷偷把它们提升成判绿点——那会让门禁一夜之间多出上百条「新增打红」。
    所以这里保留原口径：命中通配的只打印、不拦。
    """
    classname = key.split('::', 1)[0]
    return any(fnmatch.fnmatch(classname, p) for p in patterns)


def write_baseline(path, failed, stats):
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# CI 回归基线：本仓库当前的既有失败用例（存量欠账，非本次引入）\n')
        fh.write('# 身份格式：junit 的 classname::name\n')
        fh.write('# 语义：CI 只拦「基线之外」的新增打红；修好一批后重新生成并提交本文件。\n')
        fh.write('#   python3 tools/ci/check_regression.py --junit .ci/report.xml \\\n')
        fh.write('#       --write-baseline tests/ci_baseline_failures.txt\n')
        fh.write('# 快照汇总：collected=%d failures=%d errors=%d skipped=%d\n'
                 % (stats['tests'], stats['failures'], stats['errors'], stats['skipped']))
        for key in sorted(failed):
            fh.write(key + '\n')


def main():
    # Windows runner 的默认 stdout 编码是 cp1252（ANSI），本脚本 print 的中文
    # （如 `[CI] 读入 N 份 junit`）编码不了就抛 UnicodeEncodeError，把 Windows
    # 矩阵的「回归闸门」整步堵死。强制 UTF-8 输出即可。reconfigure 自 3.7 起可用。
    if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('--junit', required=True, action='append',
                    help='pytest --junitxml 报告路径，可多次传入或用通配符')
    ap.add_argument('--baseline', help='基线文件（对比模式）')
    ap.add_argument('--write-baseline', help='把本次结果写成新基线（生成模式）')
    ap.add_argument('--soft-classname', action='append', default=[],
                    help='classname 通配符：命中的用例只报不拦（保留「非阻塞」历史口径），可多次传入')
    args = ap.parse_args()

    try:
        failed, stats, files = collect_failures(args.junit)
    except FileNotFoundError as exc:
        print('[CI] 找不到 junit 报告：%s —— pytest 那步可能没跑起来' % exc)
        return 2
    except ET.ParseError as exc:
        print('[CI] junit 报告解析失败：%s' % exc)
        return 2

    soft = {k for k in failed if 命中软通配(k, args.soft_classname)}
    failed -= soft

    print('[CI] 读入 %d 份 junit；collected=%d failures=%d errors=%d skipped=%d 打红=%d（其中非阻塞 %d）'
          % (len(files), stats['tests'], stats['failures'], stats['errors'],
             stats['skipped'], len(failed) + len(soft), len(soft)))

    if soft:
        print('[CI] 非阻塞打红（命中 --soft-classname，只报不拦）：')
        for key in sorted(soft):
            print('       ~ ' + key)

    if args.write_baseline:
        write_baseline(args.write_baseline, failed, stats)
        print('[CI] 已写入基线 %s（%d 条）' % (args.write_baseline, len(failed)))
        return 0

    if not args.baseline:
        ap.error('对比模式需要 --baseline')

    try:
        baseline = load_baseline(args.baseline)
    except FileNotFoundError:
        print('[CI] 找不到基线 %s。首次接入请先用 --write-baseline 生成并提交。' % args.baseline)
        return 2

    # 基线里若混进了非阻塞用例，要一起摘掉，否则它们会被误报成「已转绿」
    baseline = {k for k in baseline if not 命中软通配(k, args.soft_classname)}

    new_red = sorted(failed - baseline)
    fixed = sorted(baseline - failed)

    print('[CI] 基线 %d 条；新增打红 %d 条；相比基线已转绿 %d 条'
          % (len(baseline), len(new_red), len(fixed)))

    if fixed:
        print('[CI] 以下用例已不再打红（修好就更新基线，别让基线虚高）：')
        for key in fixed:
            print('       - ' + key)

    if new_red:
        print('[CI] 新增打红（视为回归，闸门拦下）：')
        for key in new_red:
            print('       ! ' + key)
        return 1

    if len(failed) > len(baseline):
        print('[CI] 打红总数 %d 超过基线 %d，判回归。' % (len(failed), len(baseline)))
        return 1

    print('[CI] 通过：无新增打红。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
