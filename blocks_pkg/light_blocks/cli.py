# -*- coding: utf-8 -*-
"""light-combo 命令入口：定位积木库并转发给 组合.py 的 _cli。

积木库以中文目录/中文模块命名，无法直接作为 Python 包 import，
故用 importlib 按路径加载 组合.py。定位顺序：
  1) 环境变量 LIGHT_BLOCKS_LIB（显式指定积木库绝对路径）
  2) 环境变量 LIGHT_BLOCKS_DIR（R61：积木库拆分为独立 lighting 仓后，指向 lighting 仓库根）
  3) 包内数据目录（wheel 安装版：light_blocks/_data/积木库）
  4) 从当前工作目录向上找仓库内的 积木库（拆分前的开发模式，保留兼容）

运行时（光明）由 组合.py._定位运行时 解析：优先仓库内 cli/light.py，
pip 安装后回退到已安装的 `light` 命令。
"""
import importlib.util
import os
import sys


def _是库(p):
    """库根判定：目录存在且含入口 组合.py。"""
    return bool(p) and os.path.isdir(p) and os.path.isfile(os.path.join(p, '组合.py'))


def 积木库路径():
    """定位积木库目录，找不到抛 RuntimeError。"""
    for 变量 in ('LIGHT_BLOCKS_LIB', 'LIGHT_BLOCKS_DIR'):
        p = os.environ.get(变量)
        if _是库(p):
            return os.path.abspath(p)
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_data', '积木库')
    if _是库(p):
        return p
    cur = os.path.abspath(os.getcwd())
    while True:
        cand = os.path.join(cur, '积木库')
        if _是库(cand):
            return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    raise RuntimeError(
        '找不到积木库目录：请设置 LIGHT_BLOCKS_DIR（R60 拆分后指向 lighting 仓库根）'
        '或 LIGHT_BLOCKS_LIB 指向它')


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
