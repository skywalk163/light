# -*- coding: utf-8 -*-
"""积木库契约体检 v0.18 —— 索引与 .duan 源文件的一致性检查。

为什么需要它：本项目有两条踩过坑的铁律，靠人眼在 80+ 块规模上是守不住的。

  铁律一  段落名 必须 == 导出名。调用方按索引里的 导出名 生成调用代码，
          文件里若写成别的名字，粘合后直接 NameError。
  铁律二  导出名不能互为前缀。段言词法器全文件预扫描 + 最长匹配，
          若同一份合成文件里同时内联了 中位 与 中位数，短名会有把长名切开的风险。

检查项（E=错误，W=警告）：
  E1 名称重复            E2 导出名重复           E3 路径不存在
  E4 文件缺少「段落 <导出名> 接收」  E5 文件缺少「导出 <导出名>」
  E6 类型标注非法        E7 索引入参数量 ≠ 段落签名参数数
  E8 路径未纳入 git 跟踪（漏提交，CI 全新 checkout 将缺失）
  W1 导出名互为前缀（词法器风险）    W2 描述过短/缺失
  W3 导出名与名称不同且无描述佐证（可读性）   W4 类型标注仍是裸「列表」/「字典」

用法：
    python 评估/体检.py            # 全量体检
    python 评估/体检.py --严格      # 警告也算失败（CI 用）

对外接口：
    收集() -> {'块总数': int, '错': [str], '警': [str]}   纯数据、不打印，供 ci_eval 汇总
    体检(严格=False) -> int                              打印报告并返回退出码
"""

import argparse
import io
import os
import re
import subprocess
import sys

_HERE = os.path.abspath(os.path.dirname(__file__))
_库根 = os.path.normpath(os.path.join(_HERE, '..'))
if _库根 not in sys.path:
    sys.path.insert(0, _库根)

import 类型 as T           # noqa: E402
from 选块 import load_index  # noqa: E402

_段落头 = re.compile(r'^\s*段落\s+([^\s（(：:]+)\s*(?:接收\s*([^：:]*))?[：:]', re.M)
_导出行 = re.compile(r'^\s*导出\s+(\S+)\s*$', re.M)


# ---- E8 辅助：索引路径 vs git 跟踪 ----
# 块在磁盘、索引也引用，但既未 git 跟踪、又不被 .gitignore 放行 → 漏提交。
# 设计要点：
#   · 用 git check-ignore 自动放行合法忽略目录（生成/待审、生成/_验证、脚手架），
#     不硬编码忽略名单，未来新增忽略目录也无需改这里。
#   · 非 git 环境（无 .git / git 不可用）整体跳过 E8，不误报、不崩溃。
#   · 已跟踪集只取一次（git ls-files -- 积木库/），避免逐块 subprocess。
_仓库根 = None
_仓库根就绪 = False
_已跟踪集 = None
_已跟踪集就绪 = False


def _取仓库根():
    global _仓库根, _仓库根就绪
    if not _仓库根就绪:
        _仓库根就绪 = True
        try:
            r = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                               cwd=_库根, capture_output=True, text=True, timeout=20)
            _仓库根 = r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            _仓库根 = None
    return _仓库根


def _取已跟踪集():
    global _已跟踪集, _已跟踪集就绪
    if not _已跟踪集就绪:
        _已跟踪集就绪 = True
        root = _取仓库根()
        if not root:
            return None
        try:
            # -c core.quotepath=0：关闭非 ASCII 路径的八进制转义，否则中文路径
            # 会变成 "\347\..." 串，与真实 git_rel 比对失败 → 全部误报。
            r = subprocess.run(['git', '-c', 'core.quotepath=0', 'ls-files',
                                '--', '积木库/'],
                               cwd=root, capture_output=True, text=True, timeout=30)
            _已跟踪集 = set(r.stdout.splitlines()) if r.returncode == 0 else None
        except Exception:
            _已跟踪集 = None
    return _已跟踪集


def _被git忽略(git_rel):
    root = _取仓库根()
    if not root:
        return False
    try:
        r = subprocess.run(['git', 'check-ignore', '--', git_rel],
                           cwd=root, capture_output=True, text=True, timeout=20)
        return r.returncode == 0  # 0 = 被忽略（合法草稿/脚手架，放行）
    except Exception:
        return False


def _读源(路径):
    try:
        return io.open(路径, encoding='utf-8').read()
    except Exception as e:
        return None if isinstance(e, FileNotFoundError) else ''


def 收集():
    """跑全部检查项，返回结构化结果（不打印）。CI 汇总与人眼报告共用同一份计算。"""
    idx = load_index()
    块 = idx.get('块') or []
    错, 警 = [], []

    名计, 导计 = {}, {}
    for b in 块:
        名计.setdefault(b.get('名称'), []).append(b)
        导计.setdefault(b.get('导出名'), []).append(b.get('名称'))
    for 名, arr in 名计.items():
        if len(arr) > 1:
            错.append('E1 名称重复 ×%d：%s' % (len(arr), 名))
    for 导, arr in 导计.items():
        if len(arr) > 1:
            错.append('E2 导出名重复「%s」被这些块共用：%s' % (导, '、'.join(arr)))

    # W1 导出名互为前缀
    导名 = sorted([d for d in 导计 if d], key=len)
    for i, 短 in enumerate(导名):
        for 长 in 导名[i + 1:]:
            if 长 != 短 and 长.startswith(短):
                警.append('W1 导出名前缀风险：「%s」是「%s」的前缀（%s vs %s）'
                          % (短, 长, '、'.join(导计[短]), '、'.join(导计[长])))

    for b in 块:
        名 = b.get('名称')
        导 = b.get('导出名')
        rel = b.get('路径') or ''
        abspath = os.path.join(_库根, rel.replace('/', os.sep))

        for 问题 in T.校验契约(b):
            错.append('E6 %s：%s' % (名, 问题))
        for p in (b.get('输入') or []):
            if p.get('类型') in ('列表', '字典'):
                警.append('W4 %s：输入「%s」仍是裸类型 %s，应标注元素类型'
                          % (名, p.get('名'), p.get('类型')))
        out = b.get('输出') or {}
        if isinstance(out, dict) and out.get('类型') in ('列表', '字典'):
            警.append('W4 %s：输出仍是裸类型 %s，应标注元素类型' % (名, out.get('类型')))

        if len(b.get('描述') or '') < 6:
            警.append('W2 %s：描述过短（选块全靠描述，建议 ≥12 字）' % 名)

        src = _读源(abspath)
        if src is None:
            错.append('E3 %s：路径不存在 %s' % (名, rel))
            continue

        # E8 路径未纳入 git 跟踪：块在磁盘、索引已引用，但既未跟踪又不被忽略
        #     → 漏提交。CI 全新 checkout 会缺文件（第一轮 19 条路径错误的根因）。
        #     用 git check-ignore 自动放行合法草稿/脚手架（生成/待审、生成/_验证 等）。
        root = _取仓库根()
        if root is not None:
            git_rel = os.path.relpath(abspath, root).replace(os.sep, '/')
            已跟踪 = _取已跟踪集()
            if 已跟踪 is not None and git_rel not in 已跟踪 and not _被git忽略(git_rel):
                错.append('E8 %s：路径未纳入 git 跟踪 %s（块已索引但漏提交，CI 全新 checkout 将缺失）'
                          % (名, rel))

        导出集 = set(_导出行.findall(src))
        if 导 not in 导出集:
            错.append('E5 %s：文件里没有「导出 %s」（实际导出：%s）'
                      % (名, 导, '、'.join(sorted(导出集)) or '无'))

        段落 = dict((m.group(1), (m.group(2) or '').strip())
                   for m in _段落头.finditer(src))
        if 导 not in 段落:
            错.append('E4 %s：文件里没有「段落 %s」（实际段落：%s）'
                      % (名, 导, '、'.join(sorted(段落)) or '无'))
        else:
            签名 = [x.strip() for x in re.split(r'[,，]', 段落[导]) if x.strip()]
            期望 = len(b.get('输入') or [])
            if len(签名) != 期望:
                错.append('E7 %s：索引声明 %d 个入参，段落签名有 %d 个（%s）'
                          % (名, 期望, len(签名), '、'.join(签名) or '无'))

    return {'块总数': len(块), '错': 错, '警': 警}


def 体检(严格=False):
    r = 收集()
    块, 错, 警 = range(r['块总数']), r['错'], r['警']

    print('══ 积木库契约体检 ══')
    print('块总数 %d　错误 %d　警告 %d' % (len(块), len(错), len(警)))
    if 错:
        print('\n── 错误 ──')
        for x in 错:
            print('  ' + x)
    if 警:
        print('\n── 警告 ──')
        for x in 警:
            print('  ' + x)
    if not 错 and not 警:
        print('\n全部通过 ✓')
    return 1 if (错 or (严格 and 警)) else 0


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--严格', action='store_true', help='警告也算失败')
    a = p.parse_args()
    raise SystemExit(体检(严格=a.严格))
