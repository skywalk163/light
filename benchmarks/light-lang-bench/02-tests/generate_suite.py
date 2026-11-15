#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 MiniLog 黑盒测试套件的 fixtures 与用例清单。

用法：python3 generate_suite.py
产物：fixtures/*、cases/visible.json、cases/hidden.json

设计要点：
- 用例是纯数据（JSON），不含任何实现语言的代码；runner 只依赖 ./minilog。
- 大体积用例（1 MiB 单行、5000 条记录）用 fixture 文件承载，避免 MB 级字符串塞进用例表。
- hidden.json 由本脚本生成但**不随任务下发给 Agent**（见 06-design 的隔离约定）。
- output_file=True 时 runner 自动追加 --output=<临时文件>，并把 expected_output_file
  作为该文件的期望内容；同时强制 stdout 必须为 0 字节。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
CASES = os.path.join(HERE, "cases")
os.makedirs(FIX, exist_ok=True)
os.makedirs(CASES, exist_ok=True)


def rec(ts, level, svc, msg, extra=None):
    d = {"timestamp": ts, "level": level, "service": svc, "message": msg}
    if extra:
        d.update(extra)
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


BASIC = [
    rec("2026-11-01T10:00:00Z", "error", "auth", "login failed"),
    rec("2026-11-01T10:01:00Z", "info", "auth", "login ok"),
    rec("2026-11-01T10:02:00Z", "error", "api", "timeout"),
]
BASIC_TEXT = "\n".join(BASIC) + "\n"


def w(name, text):
    with open(os.path.join(FIX, name), "wb") as f:
        f.write(text.encode("utf-8") if isinstance(text, str) else text)


def case(cid, stage, args, stdin="", stdout="", stderr="", exit_code=0,
         stderr_nonempty=False, stdin_file=None, stdout_file=None,
         output_file=False, expected_output_file=None,
         preexisting_output=None, files=None, note=""):
    d = {"id": cid, "stage": stage, "args": args,
         "expected_exit": exit_code, "note": note}
    if stdin_file:
        d["stdin_file"] = stdin_file
    else:
        d["stdin"] = stdin
    if stdout_file:
        d["expected_stdout_file"] = stdout_file
    else:
        d["expected_stdout"] = stdout
    if stderr_nonempty:
        d["expected_stderr_nonempty"] = True
    else:
        d["expected_stderr"] = stderr
    if output_file:
        d["output_file"] = True
        d["expected_output_file"] = expected_output_file or ""
    if preexisting_output is not None:
        d["preexisting_output"] = preexisting_output
    if files:
        d["files"] = files
    return d


# ---------------------------------------------------------------- fixtures
w("basic.ndjson", BASIC_TEXT)
w("empty.ndjson", "")
w("blank_only.ndjson", "\n  \n\t\n\n")
w("crlf.ndjson", "\r\n".join(BASIC) + "\r\n")
w("no_final_newline.ndjson", "\n".join(BASIC))
w("validate_sample.ndjson", "\n".join([
    rec("2026-11-01T10:00:00Z", "info", "auth", "ok"),
    '{"level":"info","service":"auth","message":"no timestamp"}',
    "not json",
    '{"timestamp":123,"level":"error","message":"bad types"}',
]) + "\n")
VALIDATE_EXPECTED = ("2\tmissing_timestamp\n3\tinvalid_json\n"
                     "4\tmissing_timestamp\n4\tmissing_service\n")
VALIDATE_STDERR = "WARN invalid_json index=3\n"
w("mixed_invalid.ndjson", "\n".join([
    BASIC[0], "{broken json", BASIC[1], "[1,2,3]", BASIC[2],
]) + "\n")
MIXED_STDERR = "WARN invalid_json index=2\nWARN invalid_json index=4\n"
w("field_types.ndjson", "\n".join([
    '{"timestamp":null,"level":true,"service":7,"message":{}}',
    '{"timestamp":["a"],"level":{},"service":[],"message":1}',
    '{}',
]) + "\n")
FIELD_TYPES_EXPECTED = "\n".join([
    "%d\tmissing_%s" % (i, k)
    for i in (1, 2, 3)
    for k in ("timestamp", "level", "service", "message")
]) + "\n"
w("extra_fields.ndjson", "\n".join([
    '{"message":"m1","extra":{"a":1},"service":"svc","level":"info","timestamp":"2026-11-01T10:00:00Z","n":42}',
    json.dumps({"timestamp": "2026-11-01T10:00:01Z", "level": "info",
                "service": "svc", "message": 'has "quote" and \\\\ back'},
               ensure_ascii=False, separators=(",", ":")),
]) + "\n")
w("weird_level.ndjson", "\n".join([
    rec("2026-11-01T10:00:00Z", "a b=c", "svc", "weird"),
    rec("2026-11-01T10:00:01Z", "", "svc", "empty level"),
    rec("2026-11-01T10:00:02Z", "ERROR", "svc", "upper"),
]) + "\n")
w("stats_dup_ts.ndjson", "\n".join([
    rec("2026-11-01T10:00:00Z", "info", "b", "1"),
    rec("2026-11-01T10:00:00Z", "info", "b", "2"),
    rec("2025-01-01T00:00:00Z", "error", "b", "older"),
    rec("2027-01-01T00:00:00Z", "error", "a", "newer"),
    rec("2026-11-01T10:00:00Z", "info", "", "blank svc"),
    '{"level":"info","service":"no-ts","message":"skip"}',
    '{"timestamp":5,"level":"info","service":"bad-ts","message":"skip"}',
    "garbage",
]) + "\n")
# 组顺序（UTF-8 字节序）："" < "a" < "b"
STATS_DUP_EXPECTED = ("\t1\t2026-11-01T10:00:00Z\n"
                      "a\t1\t2027-01-01T00:00:00Z\n"
                      "b\t3\t2026-11-01T10:00:00Z\n")
w("stats_utf8.ndjson", "\n".join([
    rec("2026-11-01T10:00:00Z", "info", "Zebra", "z"),
    rec("2026-11-01T10:00:00Z", "info", "auth", "a"),
    rec("2026-11-01T10:00:00Z", "info", "中文服务", "c"),
    rec("2026-11-01T10:00:00Z", "info", "Api", "A"),
    rec("2026-11-01T10:00:00Z", "info", "api", "a2"),
]) + "\n")
w("stats_utf8.expected", "\n".join([
    "Api\t1\t2026-11-01T10:00:00Z",
    "Zebra\t1\t2026-11-01T10:00:00Z",
    "api\t1\t2026-11-01T10:00:00Z",
    "auth\t1\t2026-11-01T10:00:00Z",
    "中文服务\t1\t2026-11-01T10:00:00Z",
]) + "\n")

long_msg = "x" * 1048576
long_line = rec("2026-11-01T10:00:00Z", "error", "bulk", long_msg)
w("long_line.ndjson", long_line + "\n")
w("long_line.expected", long_line + "\n")
w("long_line_tail.ndjson", "\n".join([BASIC[0], long_line, BASIC[2]]) + "\n")
# 3 条记录取 tail --n=2，输出第 2、3 条（= 大行 + BASIC[2]）。
# 注意：早期版本误写成只输出大行，被 oracle 对拍抓出，修复固化在此而非改产物。
w("long_line_tail.expected", long_line + "\n" + BASIC[2] + "\n")

N = 5000
lines, count, maxts = [], {}, {}
for i in range(N):
    svc = ["alpha", "beta", "gamma"][i % 3]
    ts = "2026-11-01T%02d:%02d:%02dZ" % ((i // 3600) % 24,
                                         (i // 60) % 60, i % 60)
    lines.append(rec(ts, "info", svc, "m%d" % i))
    count[svc] = count.get(svc, 0) + 1
    maxts[svc] = max(maxts.get(svc, ""), ts)
w("bulk_5000.ndjson", "\n".join(lines) + "\n")
w("bulk_5000.expected", "".join(
    "%s\t%d\t%s\n" % (k, count[k], maxts[k])
    for k in sorted(count, key=lambda s: s.encode("utf-8"))))

BASIC_STATS = "api\t1\t2026-11-01T10:02:00Z\nauth\t2\t2026-11-01T10:01:00Z\n"
ERROR_LINES = BASIC[0] + "\n" + BASIC[2] + "\n"

# ---------------------------------------------------------------- 可见用例
visible = [
    case("V1-01", "v1", ["filter", "--level=error"], stdin=BASIC_TEXT,
         stdout=ERROR_LINES, note="filter 基本：保持顺序、原样输出"),
    case("V1-02", "v1", ["filter", "--level=warn"], stdin=BASIC_TEXT,
         stdout="", note="无匹配时 stdout 为 0 字节"),
    case("V1-03", "v1", ["filter"], stdin=BASIC_TEXT, exit_code=2,
         stderr_nonempty=True, note="缺必需选项 --level"),
    case("V1-04", "v1", ["filter", "--level=ERROR"], stdin=BASIC_TEXT,
         stdout="", note="level 比较区分大小写"),
    case("V1-05", "v1", ["tail", "--n=2"], stdin=BASIC_TEXT,
         stdout=BASIC[1] + "\n" + BASIC[2] + "\n", note="tail 基本"),
    case("V1-06", "v1", ["tail", "--n=10"], stdin=BASIC_TEXT,
         stdout=BASIC_TEXT, note="n 大于总数时输出全部"),
    case("V1-07", "v1", ["tail", "--n=0"], stdin=BASIC_TEXT, exit_code=2,
         stderr_nonempty=True, note="--n 必须 >= 1"),
    case("V1-08", "v1", ["tail", "--n=abc"], stdin=BASIC_TEXT, exit_code=2,
         stderr_nonempty=True, note="--n 非整数"),
    case("V1-09", "v1", ["tail"], stdin=BASIC_TEXT, exit_code=2,
         stderr_nonempty=True, note="缺必需选项 --n"),
    case("V1-10", "v1", ["validate"], stdin_file="validate_sample.ndjson",
         stdout=VALIDATE_EXPECTED, stderr=VALIDATE_STDERR,
         note="validate 基本：原因码顺序 + 警告"),
    case("V1-11", "v1", ["validate"], stdin=BASIC_TEXT, stdout="",
         note="全部合法时 stdout 0 字节"),
    case("V1-12", "v1", ["validate"], stdin_file="field_types.ndjson",
         stdout=FIELD_TYPES_EXPECTED, note="字段类型不符视为缺失"),
    case("V1-13", "v1", ["filter", "--level=error"], stdin="", stdout="",
         note="0 字节输入"),
    case("V1-14", "v1", ["validate"], stdin="\n  \n\t\n\n", stdout="",
         note="仅空行/空白行：忽略、不编号"),
    case("V1-15", "v1", ["filter", "--level=error"], stdin_file="crlf.ndjson",
         stdout=ERROR_LINES, note="CRLF：输出不含 \\r"),
    case("V1-16", "v1", ["tail", "--n=1"], stdin_file="no_final_newline.ndjson",
         stdout=BASIC[2] + "\n", note="文件末尾无换行仍算一条记录"),
    case("V1-17", "v1", ["filter", "--level=error", "--input=in.ndjson"],
         files={"in.ndjson": "basic.ndjson"}, stdout=ERROR_LINES,
         note="--input 从文件读取"),
    case("V1-18", "v1", ["frobnicate"], stdin=BASIC_TEXT, exit_code=2,
         stderr_nonempty=True, note="未知子命令"),
    case("V1-19", "v1", ["filter", "--level=error"],
         stdin_file="mixed_invalid.ndjson", stdout=ERROR_LINES,
         stderr=MIXED_STDERR,
         note="非法 JSON 行：警告格式、索引按记录计、不影响退出码"),
    case("V1-20", "v1", ["filter", "--level=info"],
         stdin_file="extra_fields.ndjson", stdout_file="extra_fields.ndjson",
         note="额外字段/键序打乱/转义：原样逐字节输出"),

    case("V2-01", "v2", ["stats", "--group-by=service"], stdin=BASIC_TEXT,
         stdout=BASIC_STATS, note="stats 基本 + service 字节序排序"),
    case("V2-02", "v2", ["stats", "--group-by=service"],
         stdin_file="stats_dup_ts.ndjson", stdout=STATS_DUP_EXPECTED,
         stderr="WARN invalid_json index=8\n",
         note="重复时间戳取字典序最大；空 service 是合法组；缺字段跳过"),
    case("V2-03", "v2", ["stats", "--group-by=service"], stdin="", stdout="",
         note="无分组时 stdout 0 字节"),
    case("V2-04", "v2", ["stats", "--group-by=service"],
         stdin_file="stats_utf8.ndjson", stdout_file="stats_utf8.expected",
         note="UTF-8 字节序排序（大小写与中文混合）"),
    case("V2-05", "v2", ["stats"], stdin=BASIC_TEXT, exit_code=2,
         stderr_nonempty=True, note="缺必需选项 --group-by"),
    case("V2-06", "v2", ["stats", "--group-by=level"], stdin=BASIC_TEXT,
         exit_code=2, stderr_nonempty=True, note="--group-by 非法取值"),
    case("V2-07", "v2", ["filter", "--level=error", "--input=-"],
         stdin=BASIC_TEXT, stdout=ERROR_LINES, note="--input=- 等价默认 stdin"),
    case("V2-08", "v2", ["filter", "--level=error"], stdin=BASIC_TEXT,
         stdout="", output_file=True, expected_output_file=ERROR_LINES,
         note="--output 写文件、stdout 0 字节"),
    case("V2-09", "v2", ["validate"], stdin=BASIC_TEXT, stdout="",
         output_file=True, expected_output_file="",
         note="--output 与全合法 validate：目标文件为 0 字节"),
    case("V2-10", "v2", ["stats", "--group-by=service"], stdin=BASIC_TEXT,
         stdout="", output_file=True, expected_output_file=BASIC_STATS,
         note="--output 与 stats 组合"),
    case("V2-11", "v2", ["filter", "--level=error", "--input=missing.ndjson"],
         exit_code=1, stderr_nonempty=True, note="--input 文件不存在 → 退出码 1"),
    case("V2-12", "v2", ["filter", "--level=error", "--level=info"],
         stdin=BASIC_TEXT, exit_code=2, stderr_nonempty=True,
         note="同一选项重复给出 → 退出码 2"),
    case("V2-13", "v2", ["tail", "--n=2"], stdin=BASIC_TEXT,
         stdout=BASIC[1] + "\n" + BASIC[2] + "\n",
         note="v1→v2 回归：tail 行为不变"),
]

# ---------------------------------------------------------------- 隐藏用例
hidden = [
    case("H-01", "v2", ["filter", "--level=error"],
         stdin_file="long_line.ndjson", stdout_file="long_line.expected",
         note="1 MiB 单行：不得截断/固定缓冲区/报错"),
    case("H-02", "v2", ["tail", "--n=2"],
         stdin_file="long_line_tail.ndjson", stdout_file="long_line_tail.expected",
         note="大行 + tail 组合"),
    case("H-03", "v2", ["stats", "--group-by=service"],
         stdin_file="bulk_5000.ndjson", stdout_file="bulk_5000.expected",
         note="5000 条记录的聚合正确性与排序"),
    case("H-04", "v2", ["tail", "--n=3"], stdin_file="mixed_invalid.ndjson",
         stdout="\n".join([BASIC[1], "[1,2,3]", BASIC[2]]) + "\n",
         stderr=MIXED_STDERR,
         note="非法 JSON 行在 tail 中仍计入记录数且原样输出"),
    case("H-05", "v1", ["validate"], stdin='{"x":1}\n',
         stdout=("1\tmissing_timestamp\n1\tmissing_level\n"
                 "1\tmissing_service\n1\tmissing_message\n"),
         note="四字段全缺：固定顺序"),
    case("H-06", "v1", ["validate"], stdin_file="field_types.ndjson",
         stdout=FIELD_TYPES_EXPECTED,
         note="null/数字/布尔/数组/对象均视为字段缺失"),
    case("H-07", "v1", ["filter", "--level=error"],
         stdin="\r\n" + BASIC[0] + "\r\n \r\n" + BASIC[2],
         stdout=ERROR_LINES,
         note="CRLF + 空白行 + 末尾无换行混合；索引仍按记录计"),
    case("H-08", "v1", ["filter", "--level=a b=c"],
         stdin_file="weird_level.ndjson",
         stdout=rec("2026-11-01T10:00:00Z", "a b=c", "svc", "weird") + "\n",
         note="level 值含空格与等号"),
    case("H-09", "v1", ["filter", "--level="],
         stdin_file="weird_level.ndjson",
         stdout=rec("2026-11-01T10:00:01Z", "", "svc", "empty level") + "\n",
         note="空字符串 level 是合法取值"),
    case("H-10", "v2", ["stats", "--group-by=service"],
         stdin_file="stats_utf8.ndjson", stdout_file="stats_utf8.expected",
         note="UTF-8 字节序（隐藏复测）"),
    case("H-11", "v2", ["stats", "--group-by=service"],
         stdin="\n".join([
             rec("2026-11-01T10:00:00Z", "info", "s", "a"),
             rec("2026-11-01T09:00:00Z", "error", "s", "b"),
             rec("2025-12-31T23:59:59Z", "info", "s", "c"),
             rec("2026-11-01T10:00:00Z", "warn", "s", "dup"),
         ]) + "\n",
         stdout="s\t4\t2026-11-01T10:00:00Z\n",
         note="时间戳按字典序而非时间解析；重复值不影响计数"),
    case("H-12", "v2", ["stats", "--group-by=service"],
         stdin="\n".join(["[1,2,3]", '"scalar"', "42", "null",
                          rec("2026-11-01T10:00:00Z", "info", "ok", "m")]) + "\n",
         stdout="ok\t1\t2026-11-01T10:00:00Z\n",
         stderr=("WARN invalid_json index=1\nWARN invalid_json index=2\n"
                 "WARN invalid_json index=3\nWARN invalid_json index=4\n"),
         note="JSON 合法但非对象（数组/标量/null）同样按非法 JSON 处理"),
    case("H-13", "v2", ["filter", "--level=error"], stdin=BASIC_TEXT,
         stdout="", output_file=True, expected_output_file=ERROR_LINES,
         preexisting_output="STALE CONTENT TO BE TRUNCATED",
         note="--output 覆盖已有文件必须截断"),
    case("H-14", "v1", ["tail", "--n=1"], stdin=BASIC_TEXT,
         stdout=BASIC[2] + "\n", note="单条 tail"),
    case("H-15", "v1", ["filter", "--level=info"],
         stdin_file="extra_fields.ndjson", stdout_file="extra_fields.ndjson",
         note="含转义字符与额外字段的行必须逐字节原样输出"),
    case("H-16", "v2", ["stats", "--group-by=service", "--input=-"],
         stdin=BASIC_TEXT, stdout=BASIC_STATS,
         note="--input=- 与 stats 组合"),
    case("H-17", "v2", ["validate", "--input=in.ndjson"],
         files={"in.ndjson": "validate_sample.ndjson"},
         stdout=VALIDATE_EXPECTED, stderr=VALIDATE_STDERR,
         note="validate 与 --input 文件组合"),
    case("H-18", "v2", ["filter", "--level=error", "--bogus=1"],
         stdin=BASIC_TEXT, exit_code=2, stderr_nonempty=True,
         note="未识别选项 → 用法错误"),
    case("H-19", "v2", ["filter", "--level=error", "--output=sub/no.txt"],
         stdin=BASIC_TEXT, exit_code=1, stderr_nonempty=True,
         note="--output 父目录不存在 → 退出码 1"),
    case("H-20", "v2", ["tail", "--n=+2"], stdin=BASIC_TEXT, exit_code=2,
         stderr_nonempty=True, note="--n 带前导 + 号不合法"),
]


def dump(path, cases):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"suite": os.path.basename(path), "cases": cases}, f,
                  ensure_ascii=False, indent=2)
        f.write("\n")


dump(os.path.join(CASES, "visible.json"), visible)
dump(os.path.join(CASES, "hidden.json"), hidden)
print("visible: %d cases -> cases/visible.json" % len(visible))
print("hidden : %d cases -> cases/hidden.json" % len(hidden))
print("fixtures: %d files" % len(os.listdir(FIX)))
