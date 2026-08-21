# -*- coding: utf-8 -*-
"""
test_schema_light.py —— stdlib/模式校验.light JSON Schema 校验器测试

纯离线，覆盖：type / enum / const / required / properties / items / $ref / $defs /
allOf / anyOf / oneOf / not / minLength / maxLength / pattern / minimum /
maximum / minItems / maxItems / uniqueItems，以及结构化错误结果与 JSON Pointer 路径。
"""
import os
import sys
import pytest

_STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stdlib")
if _STDLIB not in sys.path:
    sys.path.insert(0, _STDLIB)
import _light_import_hook
_light_import_hook.install([_STDLIB])

from 模式校验 import 模式校验器


@pytest.fixture
def v():
    return 模式校验器()


def errs_of(result):
    """从校验结果取错误列表。"""
    assert isinstance(result, dict)
    return result.get("错误", [])


class TestType:
    def test_integer_ok(self, v):
        assert v.校验(5, {"type": "integer"})["通过"]

    def test_integer_bad(self, v):
        r = v.校验("x", {"type": "integer"})
        assert not r["通过"]
        assert errs_of(r)[0]["关键字"] == "type"

    def test_number_accepts_int_and_float(self, v):
        assert v.校验(5, {"type": "number"})["通过"]
        assert v.校验(3.5, {"type": "number"})["通过"]

    def test_boolean_not_integer(self, v):
        assert not v.校验(True, {"type": "integer"})["通过"]
        assert v.校验(True, {"type": "boolean"})["通过"]

    def test_null(self, v):
        assert v.校验(None, {"type": "null"})["通过"]

    def test_object_and_array(self, v):
        assert v.校验({"a": 1}, {"type": "object"})["通过"]
        assert v.校验([1], {"type": "array"})["通过"]


class TestEnumConst:
    def test_enum_ok(self, v):
        assert v.校验("a", {"enum": ["a", "b"]})["通过"]

    def test_enum_bad(self, v):
        r = v.校验("c", {"enum": ["a", "b"]})
        assert not r["通过"]
        assert errs_of(r)[0]["关键字"] == "enum"

    def test_const_ok(self, v):
        assert v.校验(7, {"const": 7})["通过"]

    def test_const_bad(self, v):
        assert not v.校验(8, {"const": 7})["通过"]

    def test_const_deep_equality(self, v):
        assert v.校验({"x": [1, 2]}, {"const": {"x": [1, 2]}})["通过"]
        assert not v.校验({"x": [1, 3]}, {"const": {"x": [1, 2]}})["通过"]


class TestObject:
    SCH = {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string", "minLength": 2},
            "age": {"type": "integer", "minimum": 0},
        },
    }

    def test_ok(self, v):
        assert v.校验({"name": "ab", "age": 3}, self.SCH)["通过"]

    def test_required_missing(self, v):
        r = v.校验({"age": 3}, self.SCH)
        assert not r["通过"]
        assert "" in [e["路径"] for e in errs_of(r)]
        assert "required" in [e["关键字"] for e in errs_of(r)]

    def test_nested_property_errors_with_pointer(self, v):
        r = v.校验({"name": "a", "age": -1}, self.SCH)
        assert not r["通过"]
        paths = set(e["路径"] for e in errs_of(r))
        assert "/name" in paths
        assert "/age" in paths
        kws = set(e["关键字"] for e in errs_of(r))
        assert kws == {"minimum", "minLength"}


class TestArray:
    def test_items_ok(self, v):
        sch = {"type": "array", "items": {"type": "integer"}}
        assert v.校验([1, 2, 3], sch)["通过"]

    def test_items_bad_pointer(self, v):
        sch = {"type": "array", "items": {"type": "integer"}}
        r = v.校验([1, "x", 3], sch)
        assert not r["通过"]
        assert [e["路径"] for e in errs_of(r)] == ["/1"]

    def test_min_max_items(self, v):
        assert not v.校验([1], {"minItems": 2})["通过"]
        assert not v.校验([1, 2, 3], {"maxItems": 2})["通过"]
        assert v.校验([1, 2], {"minItems": 1, "maxItems": 3})["通过"]

    def test_unique_items(self, v):
        assert v.校验([1, 2, 3], {"uniqueItems": True})["通过"]
        assert not v.校验([1, 2, 1], {"uniqueItems": True})["通过"]

    def test_unique_deep(self, v):
        assert not v.校验([{"a": 1}, {"a": 1}], {"uniqueItems": True})["通过"]


class TestStringNumber:
    def test_min_max_length(self, v):
        assert not v.校验("ab", {"minLength": 3})["通过"]
        assert not v.校验("abcd", {"maxLength": 3})["通过"]
        assert v.校验("abc", {"minLength": 2, "maxLength": 4})["通过"]

    def test_pattern(self, v):
        sch = {"pattern": "^[a-z]+[0-9]+$"}
        assert v.校验("abc123", sch)["通过"]
        assert not v.校验("123abc", sch)["通过"]

    def test_min_max(self, v):
        assert not v.校验(-1, {"minimum": 0})["通过"]
        assert not v.校验(11, {"maximum": 10})["通过"]
        assert v.校验(5, {"minimum": 0, "maximum": 10})["通过"]


class TestRefDefs:
    SCH = {
        "$defs": {
            "pos": {
                "type": "object",
                "required": ["x", "y"],
                "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
            }
        },
        "type": "object",
        "properties": {"p": {"$ref": "#/$defs/pos"}},
    }

    def test_ref_ok(self, v):
        assert v.校验({"p": {"x": 1, "y": 2}}, self.SCH)["通过"]

    def test_ref_bad_root_pointer(self, v):
        r = v.校验({"p": {"x": 1}}, self.SCH)
        assert not r["通过"]
        assert [e["路径"] for e in errs_of(r)] == ["/p"]

    def test_ref_nested_pointer(self, v):
        r = v.校验({"p": {"x": "a", "y": 2}}, self.SCH)
        assert not r["通过"]
        assert [e["路径"] for e in errs_of(r)] == ["/p/x"]

    def test_ref_unresolvable_reports_error(self, v):
        r = v.校验(1, {"$ref": "#/$defs/nope"})
        assert not r["通过"]
        assert errs_of(r)[0]["关键字"] == "$ref"


class TestCombinators:
    def test_allOf_ok(self, v):
        sch = {"allOf": [{"type": "integer"}, {"minimum": 0}]}
        assert v.校验(5, sch)["通过"]
        assert not v.校验(-1, sch)["通过"]

    def test_anyOf(self, v):
        sch = {"anyOf": [{"type": "string"}, {"type": "integer"}]}
        assert v.校验("x", sch)["通过"]
        assert v.校验(3, sch)["通过"]
        assert not v.校验(1.5, sch)["通过"]

    def test_oneOf_exactly_one(self, v):
        sch = {"oneOf": [{"type": "integer"}, {"type": "string"}]}
        assert v.校验(5, sch)["通过"]
        assert not v.校验(True, sch)["通过"]  # 0 个
        assert not v.校验(5, {"oneOf": [{"type": "number"}, {"minimum": 0}]})["通过"]  # 2 个

    def test_not(self, v):
        assert v.校验(5, {"not": {"type": "string"}})["通过"]
        assert not v.校验("x", {"not": {"type": "string"}})["通过"]


class TestResultStructure:
    def test_result_shape(self, v):
        r = v.校验("x", {"type": "integer"})
        assert set(r.keys()) == {"通过", "错误"}
        e0 = errs_of(r)[0]
        assert set(e0.keys()) == {"路径", "关键字", "消息"}
        assert e0["路径"] == ""
        assert e0["关键字"] == "type"

    def test_empty_schema_always_passes(self, v):
        assert v.校验({"anything": [1, 2]}, {})["通过"]

    def test_defs_do_not_leak_across_calls(self, v):
        sch_a = {"$defs": {"t": {"type": "string"}}, "$ref": "#/$defs/t"}
        assert v.校验("s", sch_a)["通过"]
        # 第二次校验没有 $defs，不应复用上次的
        assert v.校验(5, {"type": "integer"})["通过"]
