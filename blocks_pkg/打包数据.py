# -*- coding: utf-8 -*-
"""构建 wheel 数据：把 积木库 复制进 duan_blocks/_data/积木库，随 duan-blocks 分发。

用法：python blocks_pkg/打包数据.py   （先跑它，再 pip wheel / pip install）
"""
import os
import shutil

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, '积木库')
_DST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'duan_blocks', '_data', '积木库')

_排除名 = {'__pycache__', '.embed_cache', '组合结果.duan', '_冒烟工位.duan',
           '_验块工位.duan', '_冒烟写.txt', '节点缓存'}
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
