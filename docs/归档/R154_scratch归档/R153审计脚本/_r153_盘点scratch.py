# -*- coding: utf-8 -*-
"""R153 盘点（只读）：历史 scratch / 临时物。本轮**不删任何东西**，只出盘点表。"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)


def git(*args):
    r = subprocess.run(['git'] + list(args), capture_output=True)
    return r.stdout.decode('utf-8', 'replace')


tracked = set(git('ls-files').splitlines())

# 盘点对象：所有 `_` / `.` 开头的疑似临时物（顶层）
条目 = []
for name in sorted(os.listdir('.')):
    if not (name.startswith('_r') or name.startswith('.scratch') or name.startswith('_recover')):
        continue
    if name.endswith(('.md',)) and name.startswith('_R'):
        continue  # _R152_*.md 这类正式报告另算
    p = os.path.join('.', name)
    if os.path.isdir(p):
        大小 = 0
        文件数 = 0
        最新 = 0
        tracked子 = 0
        for dirpath, dirnames, filenames in os.walk(p):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    st = os.stat(fp)
                except OSError:
                    continue
                大小 += st.st_size
                文件数 += 1
                最新 = max(最新, st.st_mtime)
                rel = os.path.relpath(fp, '.').replace('\\', '/')
                if rel in tracked:
                    tracked子 += 1
        条目.append((name, '目录', 文件数, 大小, 最新, tracked子))
    else:
        st = os.stat(p)
        rel = name
        条目.append((name, '文件', 1, st.st_size, st.st_mtime,
                     1 if rel in tracked else 0))

print('%-28s %-5s %6s %12s %-17s %s' % ('名称', '类型', '文件数', '大小', '最后修改', 'tracked数'))
print('-' * 100)
总大小 = 0
for name, 类型, 文件数, 大小, 最新, tk in 条目:
    总大小 += 大小
    print('%-28s %-5s %6d %10.1f KB %s %6d'
          % (name[:28], 类型, 文件数, 大小 / 1024.0,
             time.strftime('%Y-%m-%d %H:%M', time.localtime(最新)), tk))
print('-' * 100)
print('合计 %.1f MB，%d 个顶层条目' % (总大小 / 1024.0 / 1024.0, len(条目)))

# 顶层 `_R*.md` 报告（属于正式交付物，不是 scratch，但要区分 tracked 与否）
print('\n=== 顶层 _R*.md 报告（正式交付物，非 scratch）===')
for name in sorted(os.listdir('.')):
    if name.startswith('_R') and name.endswith('.md'):
        print('  %-34s %s' % (name, 'TRACKED' if name in tracked else 'UNTRACKED'))
