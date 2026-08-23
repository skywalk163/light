# -*- coding: utf-8 -*-
# _taskD4_ 反跑探针（D4-3）：import 一个不存在的模块，制造 collect error。
import 不存在的模块_xyz


def test_never_runs():
    assert True

