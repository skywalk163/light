# -*- coding: utf-8 -*-
"""构建 wheel 数据：把积木库复制进 light_blocks/_data/积木库，随 light-blocks 分发。

用法：python blocks_pkg/打包数据.py   （先跑它，再 pip wheel / pip install）

【R61 拆分】R60 起 `积木库/` 已拆分为独立 lighting 仓，本仓不再有此目录。
源目录解析顺序：
  1) 环境变量 LIGHT_BLOCKS_DIR（指向 lighting 仓库根）
  2) 同级 ../lighting（本仓与 lighting 同处一个工作区时的默认位置）
  3) 旧路径 ./积木库（兼容拆分前的工作树）
**不得**只写裸路径 `积木库`——拆分后它必然 SystemExit（同类缺陷见 L-177）。
"""
import os
import shutil

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _源目录():
    cands = []
    env = os.environ.get('LIGHT_BLOCKS_DIR')
    if env:
        cands.append(env)
    cands.append(os.path.join(os.path.dirname(_ROOT), 'lighting'))
    cands.append(os.path.join(_ROOT, '积木库'))
    for c in cands:
        if c and os.path.isdir(c):
            return os.path.abspath(c)
    raise SystemExit(
        '找不到积木库（LIGHT_BLOCKS_DIR / ../lighting / ./积木库 均不存在）：\n  '
        + '\n  '.join(cands))


_SRC = _源目录()
_DST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'light_blocks', '_data', '积木库')

_排除名 = {'__pycache__', '.embed_cache', '组合结果.light', '_冒烟工位.light',
           '_验块工位.light', '_冒烟写.txt', '节点缓存'}
_排除尾 = ('.pyc',)


def main():
    if not os.path.isdir(_SRC):
        raise SystemExit('找不到 积木库：' + _SRC)
    shutil.rmtree(_DST, ignore_errors=True)
    os.makedirs(_DST, exist_ok=True)
    n = 0
    for dirpath, dirnames, filenames in os.walk(_SRC):
        dirnames[:] = [d for d in dirnames if d not in _排除名]
        rel = os.path.relpath(dirpath, _SRC)
        for f in filenames:
            if f.endswith(_排除尾) or f in _排除名:
                continue
            dst_dir = os.path.join(_DST, rel) if rel != '.' else _DST
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(os.path.join(dirpath, f), os.path.join(dst_dir, f))
            n += 1
    print('已复制 %d 个文件 → %s' % (n, _DST))


if __name__ == '__main__':
    main()
