#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniLog 参考实现（Python，仅标准库）。

用途：
1. 验证 MiniLog 规格自身自洽、黑盒用例期望值正确；
2. 作为各语言实现的「语义对拍」基准（oracle）；
3. 不作为参赛提交，不计入任何评测指标。

注意：本文件刻意写成「规格的直译」，不追求性能或代码风格。
"""
import json
import sys

REQUIRED = ("timestamp", "level", "service", "message")
REASON = {k: "missing_" + k for k in REQUIRED}
WARN = "WARN invalid_json index=%d\n"


class UsageError(Exception):
    pass


class IOErrorExit(Exception):
    pass


def parse_opts(argv):
    """解析 --key=value；拒绝重复、未知、缺必需。"""
    opts = {}
    for tok in argv:
        if not tok.startswith("--") or "=" not in tok:
            raise UsageError("bad option: %s" % tok)
        key, val = tok[2:].split("=", 1)
        if key in opts:
            raise UsageError("duplicate option: --%s" % key)
        opts[key] = val
    return opts


def read_input(opts):
    src = opts.get("input", "-")
    try:
        if src == "-":
            data = sys.stdin.buffer.read()
        else:
            with open(src, "rb") as f:
                data = f.read()
    except OSError as e:
        raise IOErrorExit("cannot read input: %s" % e)
    return data


def records(data):
    """产出 (index, raw_bytes, obj_or_None, is_invalid_json)。

    按规格 §0.1：去掉行尾 \\r；strip 后为空则忽略、不编号；
    tail 需要保留 raw，因此非法 JSON 行也作为一条记录返回。
    """
    idx = 0
    for line in data.split(b"\n"):
        if line.endswith(b"\r"):
            line = line[:-1]
        if not line.strip():
            continue
        idx += 1
        obj = None
        invalid = False
        try:
            text = line.decode("utf-8")
            obj = json.loads(text)
            if not isinstance(obj, dict):
                obj, invalid = None, True
        except (UnicodeDecodeError, ValueError):
            obj, invalid = None, True
        yield idx, line, obj, invalid


def warn_invalid(idx, out_err):
    out_err.append(WARN % idx)


def is_str(obj, key):
    return obj is not None and isinstance(obj.get(key), str)


def emit(lines, opts):
    """lines 是 bytes 列表（每行不含 \\n）；返回最终 bytes。"""
    body = b"\n".join(lines) + (b"\n" if lines else b"")
    dest = opts.get("output")
    if dest is None:
        sys.stdout.buffer.write(body)
    else:
        try:
            with open(dest, "wb") as f:
                f.write(body)
        except OSError as e:
            raise IOErrorExit("cannot write output: %s" % e)
    return body


def cmd_filter(opts, recs, errs):
    if "level" not in opts:
        raise UsageError("filter requires --level")
    out = []
    for idx, raw, obj, invalid in recs:
        if invalid:
            warn_invalid(idx, errs)
            continue
        if is_str(obj, "level") and obj["level"] == opts["level"]:
            out.append(raw)
    emit(out, opts)


def cmd_tail(opts, recs, errs):
    if "n" not in opts:
        raise UsageError("tail requires --n")
    v = opts["n"]
    if not v.isascii() or not v.isdigit() or v.startswith("+") or int(v) < 1:
        raise UsageError("--n must be a positive decimal integer")
    n = int(v)
    lines = []
    for idx, raw, obj, invalid in recs:
        if invalid:
            warn_invalid(idx, errs)
        lines.append(raw)
    emit(lines[-n:] if n <= len(lines) else lines, opts)


def cmd_validate(opts, recs, errs):
    out = []
    for idx, raw, obj, invalid in recs:
        if invalid:
            warn_invalid(idx, errs)
            out.append(("%d\tinvalid_json" % idx).encode("utf-8"))
            continue
        for k in REQUIRED:
            if not is_str(obj, k):
                out.append(("%d\t%s" % (idx, REASON[k])).encode("utf-8"))
    emit(out, opts)


def cmd_stats(opts, recs, errs):
    if "group-by" not in opts:
        raise UsageError("stats requires --group-by")
    if opts["group-by"] != "service":
        raise UsageError("--group-by only supports service")
    groups = {}
    for idx, raw, obj, invalid in recs:
        if invalid:
            warn_invalid(idx, errs)
            continue
        if not is_str(obj, "service") or not is_str(obj, "timestamp"):
            continue
        svc, ts = obj["service"], obj["timestamp"]
        if svc not in groups:
            groups[svc] = [0, ""]
        groups[svc][0] += 1
        if ts > groups[svc][1]:
            groups[svc][1] = ts
    out = []
    for svc in sorted(groups, key=lambda s: s.encode("utf-8")):
        cnt, mx = groups[svc]
        out.append(("%s\t%d\t%s" % (svc, cnt, mx)).encode("utf-8"))
    emit(out, opts)


COMMANDS = {"filter": cmd_filter, "tail": cmd_tail,
            "validate": cmd_validate, "stats": cmd_stats}
ALLOWED = {
    "filter": {"level", "input", "output"},
    "tail": {"n", "input", "output"},
    "validate": {"input", "output"},
    "stats": {"group-by", "input", "output"},
}


def main(argv):
    if not argv:
        raise UsageError("missing subcommand")
    cmd = argv[0]
    if cmd not in COMMANDS:
        raise UsageError("unknown subcommand: %s" % cmd)
    opts = parse_opts(argv[1:])
    unknown = set(opts) - ALLOWED[cmd]
    if unknown:
        raise UsageError("unknown option(s): %s" % ", ".join(sorted(unknown)))
    data = read_input(opts)
    recs = list(records(data))
    errs = []
    COMMANDS[cmd](opts, recs, errs)
    if errs:
        sys.stderr.write("".join(errs))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except UsageError as e:
        sys.stderr.write("usage error: %s\n" % e)
        sys.exit(2)
    except IOErrorExit as e:
        sys.stderr.write("io error: %s\n" % e)
        sys.exit(1)
