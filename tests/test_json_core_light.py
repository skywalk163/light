# -*- coding: utf-8 -*-
"""
test_json_core_light.py —— stdlib/JSON核心.light 的纯光明 JSON 解析/序列化/落盘测试

判据（任务书 §3.1）：
1. round-trip 一致：对 examples/harness/评测集.jsonl 的 6 条 + 一组构造样本
   （深嵌套/中文/转义/大整数/浮点指数/空对象空数组），
   `解析 → 序列化 → 解析` 与 JSON.py 的 解析JSON 结果**逐字段相等**。
   JSON.py 作为对照实现（只读参照答案）。
2. 零 引 Python / 不 导入 json（静态检查由交付报告登记）。
3. 反跑守卫：转义相关断言锁定——若把转义分支变异掉，下列用例会变红。
"""
import os
import sys
import json
import tempfile

import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

# 被测（纯光明实现）
from JSON核心 import 解析, 序列化, 写入文件
# 对照（只读参照答案 .py）
from JSON import 解析JSON, 序列化JSON

_EVAL_SET = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "examples", "harness", "评测集.jsonl")


def _eval_lines():
    with open(_EVAL_SET, "r", encoding="utf-8") as fh:
        return [ln for ln in fh.read().splitlines() if ln.strip() != ""]


def test_eval_set_roundtrip_against_json_py():
    """评测集 6 条：解析 == JSON.py 解析；序列化后再解析仍 == JSON.py 解析。"""
    for line in _eval_lines():
        mine = 解析(line)
        ref = 解析JSON(line)
        assert mine == ref, "解析与 JSON.py 不一致: %r" % line
        # 紧凑往返
        rt = 解析(序列化(mine, 0))
        assert rt == ref, "紧凑往返失败: %r" % line
        # 缩进往返（等价 json.dumps(indent=2)）
        rt2 = 解析(序列化(mine, 2))
        assert rt2 == ref, "缩进往返失败: %r" % line
        # 与 json.loads 对拍：我的序列化产物必须是合法 JSON 且语义相等
        assert json.loads(序列化(mine, 2)) == ref


def test_eval_set_serialize_matches_json_dumps():
    """我的 序列化(缩进=2) 与 json.dumps(ensure_ascii=False, indent=2) 逐字节相等。"""
    for line in _eval_lines():
        obj = 解析(line)
        mine = 序列化(obj, 2)
        ref = json.dumps(obj, ensure_ascii=False, indent=2)
        assert mine == ref, "序列化与 json.dumps 不一致: %r\n mine=%r\n ref =%r" % (line, mine, ref)


# 构造样本：深嵌套 / 中文 / 转义 / 大整数 / 浮点指数 / 空对象空数组
构造样本 = {
    "深嵌套": {"a": 1, "b": [1, 2, {"c": [3, 4, {"d": "底"}]}], "e": {"f": {"g": True}}},
    "中文": {"名字": "张三", "城市": "北京", "句子": "今天天气真好，适合写代码。"},
    "转义": {"s": "一行\n二行\t制表\"引号\\反斜杠", "尾": "结尾\r\n"},
    "大整数": {"big": 123456789012345678901234567890, "neg": -9876543210123456789},
    "浮点指数": {"e1": 1.5e10, "e2": -3.14e-2, "zero": 0.0, "one": 1.0},
    "空对象": {},
    "空数组": [],
    "混合": [None, True, False, "文本", 42, 3.14, {"k": [1, "二", None]}],
}


@pytest.mark.parametrize("键", list(构造样本.keys()))
def test_constructed_samples_roundtrip(键):
    obj = 构造样本[键]
    mine = 解析(序列化(obj, 0))
    assert mine == obj, "构造样本往返失败: %s" % 键
    assert json.loads(序列化(obj, 2)) == obj


def test_large_int_precision_preserved():
    """大整数往返不丢精度（Python int 任意精度，与 JSON.py 一致）。"""
    n = 123456789012345678901234567890
    out = 序列化({"n": n}, 0)
    assert 解析(out)["n"] == n
    assert 解析(out)["n"] == 解析JSON(out)["n"]


def test_unicode_escape_roundtrip():
    """\\uXXXX 转义能被正确解析（与 json 一致）；输出沿用 ensure_ascii=False（UTF-8），与 JSON.py 一致。

    注意：任务书 §3.1 的序列化对照基线是 json.dumps(ensure_ascii=False)（见 序列化JSON / test_eval_set_serialize_matches_json_dumps），
    故非 ASCII 字符（é、中文）序列化后保持原样，不再回到 \\uXXXX 形式——这点与 JSON.py 逐字节相等。
    """
    text = '{"x": "\\u00e9\\u4e2d\\u6587"}'  # é中文 的 \u 形式
    mine = 解析(text)
    ref = 解析JSON(text)
    assert mine == ref
    assert mine["x"] == "é中文"  # \u 输入被正确还原为实际字符
    # 输出沿用 ensure_ascii=False（与 JSON.py 的 序列化JSON 一致），不再回到 \u 形式
    assert 序列化(mine, 0) == '{"x": "é中文"}'
    # 与参照实现「紧凑」形态逐字节相等（注意：参照 序列化JSON(缩进=0) 因 `if 缩进 is not None`
    # 而产出「0 缩进换行」形态，与本项目「缩进=0 即紧凑无换行」不同；故用无参紧凑形式对照）。
    assert 序列化(mine, 0) == 序列化JSON(mine)
    # 反向稳定：再解析仍等于自身
    assert 解析(序列化(mine, 0)) == mine


def test_write_file_roundtrip(tmp_path):
    """写入文件(路径, 值) 落盘后解析回来与原文相等。"""
    obj = 构造样本["深嵌套"]
    p = tmp_path / "out.json"
    写入文件(str(p), obj)
    with open(str(p), "r", encoding="utf-8") as fh:
        text = fh.read()
    assert 解析(text) == obj
    # 产物应被美化（含换行与缩进）
    assert "\n" in text


# ---- 反跑守卫：锁死转义行为，变异解析器转义分支会变红 ----
def test_escape_newline_survives_roundtrip():
    """若转义处理被改坏（例如 \n 不再转义），该用例必红。"""
    s = "line1\nline2"
    out = 序列化({"s": s}, 0)
    assert out == '{"s": "line1\\nline2"}', "换行未被正确转义"
    assert 解析(out)["s"] == s


def test_quote_and_backslash_escaped():
    s = 'a"b\\c'
    out = 序列化({"s": s}, 0)
    assert out == '{"s": "a\\"b\\\\c"}', "引号/反斜杠未被正确转义"
    assert 解析(out)["s"] == s


def test_eof_no_artifacts_in_source_tree():
    """产物必须落在临时目录，不在源码树（交 reporter 用 dir 确认）。"""
    d = tempfile.mkdtemp(prefix="_taskD7_")
    p = os.path.join(d, "probe.json")
    写入文件(p, {"ok": 1})
    assert os.path.exists(p)
    # 临时目录在系统 temp 下，不在仓库内
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert not os.path.abspath(p).startswith(os.path.abspath(repo))
