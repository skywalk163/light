# -*- coding: utf-8 -*-
"""duan-combo 命令入口：定位积木库并转发给 组合.py 的 _cli。

积木库以中文目录/中文模块命名，无法直接作为 Python 包 import，
故用 importlib 按路径加载 组合.py。定位顺序：
  1) 环境变量 DUAN_BLOCKS_LIB（显式指定积木库绝对路径）
  2) 包内数据目录（wheel 安装版：duan_blocks/_data/积木库）
  3) 从当前工作目录向上找仓库内的 积木库（开发模式）

运行时（段言）由 组合.py._定位运行时 解析：优先仓库内 cli/duan.py，
pip 安装后回退到已安装的 `duan` 命令。
"""
import importlib.util
import os
import sys


def 积木库路径():
    """定位积木库目录，找不到抛 RuntimeError。"""
    p = os.environ.get('DUAN_BLOCKS_LIB')
    if p and os.path.isdir(p):
        return os.path.abspath(p)
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_data', '积木库')
    if os.path.isdir(p) and os.path.isfile(os.path.join(p, '组合.py')):
        return p
    cur = os.path.abspath(os.getcwd())
    while True:
        cand = os.path.join(cur, '积木库')
        if os.path.isdir(cand) and os.path.isfile(os.path.join(cand, '组合.py')):
            return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    raise RuntimeError(
        '找不到 积木库 目录：请设置 DUAN_BLOCKS_LIB 指向它，或在 duan 仓库内运行')


def _加载组合(库):
    sys.path.insert(0, 库)
    spec = importlib.util.spec_from_file_location('组合', os.path.join(库, '组合.py'))
    if spec is None or spec.loader is None:
        raise RuntimeError('无法加载 组合.py（importlib spec 失败）')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    库 = 积木库路径()
    mod = _加载组合(库)
    return mod._cli(argv)


if __name__ == '__main__':
    raise SystemExit(main())
