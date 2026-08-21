# -*- coding: utf-8 -*-
"""
test_sse_light.py —— stdlib/SSE.light 增量式 SSE 帧解析器测试

纯离线：直接喂字节串，不依赖网络。
覆盖：单帧/多帧、跨 chunk 断行、跨 chunk 多字节 UTF-8、注释行、
     event/id/retry 字段、多 data 行 \n 拼接、空 data、CRLF/CR 行尾、
     [DONE] 哨兵（作为普通 data 值）、不完整帧抑制。
"""
import os
import sys
import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from SSE import SSE解析器


def feed_all(parser, chunks):
    """按块喂入，收集全部事件（块可以任意切分）。"""
    events = []
    for c in chunks:
        for ev in parser.喂入(c):
            events.append(ev)
    return events


class TestSSEBasic:
    def test_single_data_frame(self):
        p = SSE解析器()
        evs = feed_all(p, [b"data: hello\n\n"])
        assert len(evs) == 1
        assert evs[0]["数据"] == "hello"
        assert evs[0]["事件"] == ""
        assert evs[0]["编号"] == ""
        assert evs[0]["重试"] == ""

    def test_two_frames(self):
        p = SSE解析器()
        evs = feed_all(p, ["data: 一\n\ndata: 二\n\n".encode("utf-8")])
        assert len(evs) == 2
        assert [e["数据"] for e in evs] == ["一", "二"]

    def test_fields_event_id_retry(self):
        p = SSE解析器()
        evs = feed_all(p, [b"event: update\nid: 42\nretry: 3000\ndata: x\n\n"])
        assert len(evs) == 1
        assert evs[0]["事件"] == "update"
        assert evs[0]["编号"] == "42"
        assert evs[0]["重试"] == "3000"
        assert evs[0]["数据"] == "x"

    def test_multi_data_lines_joined_with_nl(self):
        p = SSE解析器()
        evs = feed_all(p, [b"data: a\ndata: b\ndata: c\n\n"])
        assert len(evs) == 1
        assert evs[0]["数据"] == "a\nb\nc"

    def test_leading_single_space_stripped(self):
        # 一个空格被剥掉
        evs1 = feed_all(SSE解析器(), [b"data: hi\n\n"])
        assert evs1[0]["数据"] == "hi"
        # 两个空格只剥一个（符合 SSE 规范：只剥前导单空格）
        evs2 = feed_all(SSE解析器(), [b"data:  hi\n\n"])
        assert evs2[0]["数据"] == " hi"

    def test_empty_data_value(self):
        p = SSE解析器()
        evs = feed_all(p, [b"data:\n\n"])
        assert len(evs) == 1
        assert evs[0]["数据"] == ""

    def test_comment_line_ignored(self):
        p = SSE解析器()
        evs = feed_all(p, [": 注释\n: 再注释\ndata: ok\n\n".encode("utf-8")])
        assert len(evs) == 1
        assert evs[0]["数据"] == "ok"

    def test_unknown_field_ignored(self):
        p = SSE解析器()
        evs = feed_all(p, [b"foo: bar\ndata: ok\n\n"])
        assert len(evs) == 1
        assert evs[0]["数据"] == "ok"

    def test_done_sentinel_as_data(self):
        p = SSE解析器()
        evs = feed_all(p, [b"data: [DONE]\n\n"])
        assert len(evs) == 1
        assert evs[0]["数据"] == "[DONE]"

    def test_incomplete_frame_not_emitted(self):
        p = SSE解析器()
        evs = feed_all(p, ["data: 未完".encode("utf-8")])
        assert evs == []
        assert p.结束() == 0  # 流结束也不应把未闭合帧当完整帧


class TestSSEChunking:
    def test_line_split_across_chunks(self):
        p = SSE解析器()
        evs = feed_all(p, [b"data: he", b"llo\n\n"])
        assert len(evs) == 1
        assert evs[0]["数据"] == "hello"

    def test_frame_split_across_chunks(self):
        p = SSE解析器()
        evs = feed_all(p, [b"data: a\n\ndata: b", b"\n\n"])
        assert len(evs) == 2
        assert [e["数据"] for e in evs] == ["a", "b"]

    def test_utf8_multibyte_split_across_chunks(self):
        # “你” 是 3 字节 UTF-8，切成 1+2 喂入
        p = SSE解析器()
        raw = "data: 你好\n\n".encode("utf-8")
        evs = feed_all(p, [raw[:1], raw[1:]])
        assert len(evs) == 1
        assert evs[0]["数据"] == "你好"

    def test_utf8_split_in_data_body(self):
        p = SSE解析器()
        raw = "data: 你好世界\n\n".encode("utf-8")
        cut = 8  # 切在“好”字中间
        evs = feed_all(p, [raw[:cut], raw[cut:]])
        assert len(evs) == 1
        assert evs[0]["数据"] == "你好世界"


class TestSSELineEndings:
    def test_crlf(self):
        p = SSE解析器()
        evs = feed_all(p, [b"data: x\r\n\r\n"])
        assert len(evs) == 1
        assert evs[0]["数据"] == "x"

    def test_cr_only(self):
        p = SSE解析器()
        evs = feed_all(p, [b"data: x\r\r"])
        assert len(evs) == 1
        assert evs[0]["数据"] == "x"

    def test_mixed_endings(self):
        p = SSE解析器()
        raw = b"data: a\r\ndata: b\r\ndata: c\n\n"
        evs = feed_all(p, [raw])
        assert len(evs) == 1
        assert evs[0]["数据"] == "a\nb\nc"

    def test_crlf_split_across_chunks(self):
        p = SSE解析器()
        evs = feed_all(p, [b"data: x\r", b"\n\r", b"\n"])
        assert len(evs) == 1
        assert evs[0]["数据"] == "x"


class TestSSEState:
    def test_parser_reusable_after_frames(self):
        p = SSE解析器()
        feed_all(p, [b"data: 1\n\n"])
        evs2 = feed_all(p, [b"data: 2\n\n"])
        assert [e["数据"] for e in evs2] == ["2"]

    def test_event_count(self):
        p = SSE解析器()
        feed_all(p, [b"data: 1\n\n", b"data: 2\n\n"])
        assert p.结束() == 2
