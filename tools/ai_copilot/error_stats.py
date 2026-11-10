# -*- coding: utf-8 -*-
"""错误频次统计：把报错语料聚合成「最近最容易踩的坑」排行。

数据来源是报错数据集（T-0319，`tools/ai_copilot/error_corpus.py`）落盘的
`<corpus_dir>/YYYY-MM.jsonl`。本模块只读文件、不写盘、不联网；语料不存在时
返回空列表，调用方据此退回静态卡片。

排序规则（本期刻意保持可解释，不做时间衰减 / 严重度等加权）：
  1. `hits` 次数降序（同一 code 的多行累加，行内 hits 缺省按 1）；
  2. 同 `hits` 按 `last_seen` 倒序（无时间戳的排在有时间戳的后面）。

窗口口径：滚动 `window_days` 天（默认 30），按行内 `last_seen`（缺省用 `ts`）
判断；只读窗口覆盖到的月份文件。没有时间戳的行无法证明过期，保留。

稳健性：目录缺失、文件缺失、权限错误 → 返回空列表；坏行（非 JSON / 非对象 /
缺 code）跳过并计数（通过 `stats` 出参观察），绝不抛异常。
"""

import importlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone


DEFAULT_CORPUS_DIR = os.path.join(os.path.expanduser("~"), ".light", "error_corpus")
ENV_CORPUS_DIR = "LIGHT_ERROR_CORPUS_DIR"

# 让 `from src.diagnostics.registry import get` / `from diagnostics.registry import get`
# 两种写法都有机会命中（项目根与 src 各插一次）。
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SRC_DIR = os.path.join(_PROJECT_DIR, "src")
for _p in (_PROJECT_DIR, _SRC_DIR):
    if _p not in sys.path:
        sys.path.append(_p)


def resolve_corpus_dir(corpus_dir=None):
    """解析语料目录：显式参数 > 环境变量 `LIGHT_ERROR_CORPUS_DIR` > `~/.light/error_corpus`。

    与 T-0319 `error_corpus.record()` 的目录口径一致。
    """
    if corpus_dir:
        return os.path.expanduser(str(corpus_dir))
    env = os.environ.get(ENV_CORPUS_DIR)
    if env and env.strip():
        return os.path.expanduser(env.strip())
    return DEFAULT_CORPUS_DIR


def _month_key(year, month):
    return "%04d-%02d" % (year, month)


def _month_keys(start_dt, end_dt):
    """窗口覆盖的月份文件键，升序（含首尾月）。"""
    keys = []
    year, month = start_dt.year, start_dt.month
    while (year, month) <= (end_dt.year, end_dt.month):
        keys.append(_month_key(year, month))
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return keys


def _to_epoch(value):
    """把 ISO8601 时间戳转成 epoch 秒；无法解析返回 None。

    兼容尾缀 `Z`、带偏移（T-0319 写的是本地 `+08:00`）、不带偏移（按本地时区）。
    兼容 `date` 级别的纯日期字符串。
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.astimezone()  # 不带偏移的时间戳按本机本地时区理解
    return dt.timestamp()


def _coerce_hits(value):
    """行内 hits 规范化：正整数，坏值/缺省按 1。"""
    try:
        hits = int(value)
    except (TypeError, ValueError):
        return 1
    return hits if hits > 0 else 1


def _example_of(record):
    """「正确写法」：fixes 首条 > hint > message；都没有则空串。

    刻意不取 source_snippet（那是错误现场，不是正确写法）。
    """
    fixes = record.get("fixes")
    if isinstance(fixes, (list, tuple)):
        for fix in fixes:
            if isinstance(fix, str) and fix.strip():
                return fix.strip()
    for field in ("hint", "message"):
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _lookup_title(code):
    """错误码标题：优先 `src.diagnostics.registry.get(code).title`，失败则 None。

    registry 未合入 / 导入异常 / 无该 code → 返回 None，调用方退回 code 本身，
    不臆造标题。
    """
    for module_name in ("src.diagnostics.registry", "diagnostics.registry"):
        try:
            module = importlib.import_module(module_name)
        except Exception:  # pragma: no cover - 环境差异，正常路径无 registry
            continue
        getter = getattr(module, "get", None)
        if not callable(getter):
            continue
        try:
            entry = getter(code)
        except Exception:
            continue
        title = getattr(entry, "title", None)
        if title is None and isinstance(entry, dict):
            title = entry.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
    return None


def _empty_stats():
    return {"files_read": 0, "lines_read": 0, "lines_skipped": 0}


def rank_pitfalls(window_days=30, top=10, corpus_dir=None, now=None, stats=None) -> list[dict]:
    """按近 `window_days` 天的报错频次排行。

    Args:
        window_days: 滚动窗口天数，默认 30。<=0 表示不设时间窗口。
        top: 最多返回条数，默认 10。None 或 <=0 表示返回全部。
        corpus_dir: 语料目录；None 时用 `LIGHT_ERROR_CORPUS_DIR` 或
            `~/.light/error_corpus`。
        now: 可注入的“当前时间”（datetime，便于测试）；None 用本机当前时间。
        stats: 可选出参 dict，回填 `files_read / lines_read / lines_skipped`，
            用于观察坏行与文件读取情况。

    Returns:
        `[{code, title, hits, last_seen, example}, ...]`，
        hits 降序，同 hits 按 last_seen 倒序；无数据时 `[]`。
    """
    info = _empty_stats()

    def _finish(result):
        if stats is not None:
            stats.clear()
            stats.update(info)
        return result

    try:
        window_days = int(window_days)
    except (TypeError, ValueError):
        window_days = 30

    if now is None:
        now_dt = datetime.now().astimezone()
    elif isinstance(now, datetime):
        now_dt = now if now.tzinfo is not None else now.astimezone()
    else:
        try:
            now_dt = datetime.fromtimestamp(float(now)).astimezone()
        except (TypeError, ValueError, OSError):
            now_dt = datetime.now().astimezone()

    now_epoch = now_dt.timestamp()
    if window_days > 0:
        cutoff_epoch = now_epoch - window_days * 86400.0
        start_dt = now_dt - timedelta(days=window_days)
        wanted_keys = _month_keys(start_dt, now_dt)
    else:
        cutoff_epoch = None
        start_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
        wanted_keys = None  # 不设窗口：目录里所有月份文件都读

    root = resolve_corpus_dir(corpus_dir)
    try:
        names = os.listdir(root)
    except OSError:
        return _finish([])

    # 只认 `<YYYY-MM>.jsonl`，目录里的 index.json / 锁文件 / 临时文件一律忽略
    available = {}
    for name in names:
        if (len(name) == len("YYYY-MM.jsonl") and name.endswith(".jsonl")
                and name[:4].isdigit() and name[4] == "-"
                and name[5:7].isdigit()):
            available[name[:-len(".jsonl")]] = name

    if wanted_keys is None:
        keys = sorted(available)
    else:
        keys = [key for key in wanted_keys if key in available]

    agg = {}

    for key in keys:
        path = os.path.join(root, available[key])
        try:
            handle = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            info["files_read"] += 1
            try:
                for raw in handle:
                    line = raw.strip()
                    if not line:
                        continue
                    info["lines_read"] += 1
                    try:
                        record = json.loads(line)
                    except (ValueError, TypeError):
                        info["lines_skipped"] += 1
                        continue
                    if not isinstance(record, dict):
                        info["lines_skipped"] += 1
                        continue
                    code = record.get("code")
                    if not isinstance(code, str) or not code.strip():
                        info["lines_skipped"] += 1
                        continue
                    code = code.strip()

                    # 时间戳：last_seen 优先，其次 ts
                    ts_raw = record.get("last_seen")
                    if not isinstance(ts_raw, str) or not ts_raw.strip():
                        ts_raw = record.get("ts")
                        if not isinstance(ts_raw, str) or not ts_raw.strip():
                            ts_raw = ""
                        else:
                            ts_raw = ts_raw.strip()
                    else:
                        ts_raw = ts_raw.strip()
                    epoch = _to_epoch(ts_raw)
                    if cutoff_epoch is not None and epoch is not None and epoch < cutoff_epoch:
                        continue  # 窗口外，不算坏行

                    hits = _coerce_hits(record.get("hits"))
                    slot = agg.get(code)
                    if slot is None:
                        agg[code] = {
                            "code": code,
                            "hits": hits,
                            "last_seen": ts_raw,
                            "epoch": epoch,
                            "example": _example_of(record),
                            "example_epoch": epoch,
                        }
                        continue

                    slot["hits"] += hits
                    prev_epoch = slot["epoch"]
                    if epoch is not None and (prev_epoch is None or epoch > prev_epoch):
                        # 最近的一条决定 last_seen
                        slot["last_seen"] = ts_raw
                        slot["epoch"] = epoch

                    # example 只取「最近的一条带正确写法的记录」：
                    # 最近那条没有 fixes/hint/message 时，不能把已有示例抹掉。
                    example = _example_of(record)
                    if example:
                        example_epoch = slot["example_epoch"]
                        if (example_epoch is None
                                or (epoch is not None and epoch > example_epoch)
                                or slot["example"] == ""):
                            slot["example"] = example
                            slot["example_epoch"] = epoch
            except OSError:
                # 读到一半 I/O 出错：保留已读到的部分，不抛
                continue

    def _sort_key(item):
        epoch = item["epoch"]
        return (-item["hits"], -(epoch if epoch is not None else float("-inf")))

    ordered = sorted(agg.values(), key=_sort_key)

    result = []
    for item in ordered:
        result.append({
            "code": item["code"],
            "title": _lookup_title(item["code"]) or item["code"],
            "hits": item["hits"],
            "last_seen": item["last_seen"],
            "example": item["example"],
        })

    try:
        top_n = int(top)
    except (TypeError, ValueError):
        top_n = 0
    if top_n > 0:
        result = result[:top_n]

    return _finish(result)