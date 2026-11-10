# -*- coding: utf-8 -*-
"""光明报错数据集：错误自动归档、去重与脱敏导出（纯标准库）。

设计目标
--------
把开发过程中暴露的每个 Light 报错，落成一份可以增量喂给
``light-translator`` 微调的数据集，让模型专门记住 Light 的已知暗坑。

三条纪律
--------
* **只存片段，不存整文件**：``source_snippet`` 只保留出错行 ±2 行。
* **先脱敏再落盘**：绝对路径只留 basename，疑似 token 打码；不采集
  环境变量、主机名、用户名等标识信息。
* **去重靠 sidecar**：``index.json`` 记录 ``(code, source_hash)`` 的
  ``hits`` / ``last_seen``，命中时只更新索引，不重写 JSONL。

归档目录默认 ``~/.light/error_corpus``，可用 ``LIGHT_ERROR_CORPUS_DIR``
覆盖（仅读取这一个环境变量）。本模块不联网、不上传、不发遥测。
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import hashlib
import json
import os
import re
import tempfile
import warnings

__all__ = [
    "record",
    "export_pairs",
    "summary",
    "purge",
    "DEFAULT_ROOT",
    "SCHEMA_VERSION",
]

#: 默认归档目录。
DEFAULT_ROOT = os.path.join(os.path.expanduser("~"), ".light", "error_corpus")

#: sidecar 索引版本号。
SCHEMA_VERSION = 1

#: 出错行上下各保留的行数。
SNIPPET_RADIUS = 2

#: source_hash 保留的十六进制前缀长度。
HASH_LEN = 16

#: 单条 snippet 的字符上限，避免异常超长行把数据集撑爆。
MAX_SNIPPET_CHARS = 2000

#: purge 在未显式指定 before 时的默认保留天数。
DEFAULT_RETENTION_DAYS = 90

_INDEX_NAME = "index.json"
_LOCK_NAME = ".lock"

# 绝对路径：POSIX 至少两段，Windows 盘符路径，以及 ~/ 开头。
_POSIX_PATH_RE = re.compile(
    r"(?<![\w:])/(?:[^\s/\\'\"`<>|,;()\[\]{}]+/)+[^\s/\\'\"`<>|,;()\[\]{}]*"
)
_WIN_PATH_RE = re.compile(
    r"[A-Za-z]:[\\/](?:[^\s\\/'\"`<>|,;()\[\]{}]+[\\/])*"
    r"[^\s\\/'\"`<>|,;()\[\]{}]*"
)
_HOME_PATH_RE = re.compile(
    r"~/(?:[^\s/'\"`<>|,;()\[\]{}]+/)+[^\s/'\"`<>|,;()\[\]{}]*"
)
# 疑似 token：32 位以上的连续字母/数字/下划线/短横线。
_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]{32,}")

try:  # POSIX
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - Windows
    _fcntl = None

try:  # Windows
    import msvcrt as _msvcrt
except ImportError:  # pragma: no cover - POSIX
    _msvcrt = None


# ── 基础工具 ────────────────────────────────────────────────────────

def _resolve_root(root=None):
    """解析归档目录：显式参数 > ``LIGHT_ERROR_CORPUS_DIR`` > 默认值。"""
    value = root
    if value is None:
        value = os.environ.get("LIGHT_ERROR_CORPUS_DIR") or DEFAULT_ROOT
    return os.path.expanduser(os.fspath(value))


def _ensure_root(root):
    os.makedirs(root, mode=0o700, exist_ok=True)
    return root


def _now():
    return _dt.datetime.now().astimezone()


def _now_iso():
    return _now().isoformat(timespec="seconds")


def _as_text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def _coerce_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _parse_ts(value):
    if not value:
        return None
    try:
        return _dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _ts_epoch(value):
    parsed = _parse_ts(value)
    if parsed is None:
        return float("-inf")
    try:
        return parsed.timestamp()
    except (OverflowError, OSError, ValueError):  # pragma: no cover - 极端时间
        return float("-inf")


def _source_hash(source):
    normalized = _as_text(source).replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:HASH_LEN]


def _entry_key(code, source_hash):
    return "{}\x1f{}".format(code, source_hash)


# ── 脱敏 ────────────────────────────────────────────────────────────

def _basename(token):
    # 同时按 POSIX / Windows 分隔符切分，只留最后一段。
    parts = [p for p in re.split(r"[\\/]", token) if p]
    return parts[-1] if parts else ""


def _strip_paths(text):
    def repl(match):
        return _basename(match.group(0))

    for pattern in (_WIN_PATH_RE, _POSIX_PATH_RE, _HOME_PATH_RE):
        text = pattern.sub(repl, text)
    return text


def sanitize(text):
    """脱敏：绝对路径只留 basename，32 位以上疑似 token 打码。

    该函数是幂等的，可安全重复调用。
    """
    text = _strip_paths(_as_text(text))
    return _TOKEN_RE.sub("***", text)


# ── 片段 ────────────────────────────────────────────────────────────

def _snippet(source, line):
    """取 ``line`` 上下各 :data:`SNIPPET_RADIUS` 行；行号未知时取开头数行。"""
    lines = _as_text(source).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines:
        return ""
    line = _coerce_int(line)
    if line > 0:
        start = max(0, line - 1 - SNIPPET_RADIUS)
        end = min(len(lines), line + SNIPPET_RADIUS)
    else:
        start = 0
        end = min(len(lines), SNIPPET_RADIUS * 2 + 1)
    return "\n".join(lines[start:end])[:MAX_SNIPPET_CHARS]


# ── diagnostic 归一化 ───────────────────────────────────────────────

def _diagnostic_dict(diagnostic):
    if hasattr(diagnostic, "to_dict"):
        data = diagnostic.to_dict()
    elif isinstance(diagnostic, dict):
        data = diagnostic
    elif diagnostic is None:
        data = {}
    else:
        data = {"message": _as_text(diagnostic)}
    return dict(data)


def _fixes_list(value):
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [_as_text(item) for item in value if item is not None]


# ── 索引读写 ────────────────────────────────────────────────────────

def _index_path(root):
    return os.path.join(root, _INDEX_NAME)


def _load_index(root):
    """读取 sidecar；缺失或损坏时返回空索引（损坏文件会告警）。"""
    path = _index_path(root)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {"version": SCHEMA_VERSION, "entries": {}}
    except (OSError, ValueError) as exc:
        warnings.warn("报错数据集索引读取失败，按空索引继续：{}".format(exc))
        return {"version": SCHEMA_VERSION, "entries": {}}
    if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
        warnings.warn("报错数据集索引结构异常，按空索引继续")
        return {"version": SCHEMA_VERSION, "entries": {}}
    data.setdefault("version", SCHEMA_VERSION)
    return data


def _atomic_write(path, text):
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=directory, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise


def _write_index(root, index):
    text = json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n"
    _atomic_write(_index_path(root), text)


def _save_index(root, index):
    """索引写失败只告警，不打断归档（JSONL 已经落盘）。"""
    try:
        _write_index(root, index)
    except OSError as exc:
        warnings.warn("报错数据集索引写入失败（数据行已保留）：{}".format(exc))


@contextlib.contextmanager
def _locked(root):
    """跨进程写锁；拿不到锁时降级为无锁执行，不阻断归档。"""
    fd = None
    locked = False
    try:
        fd = os.open(os.path.join(root, _LOCK_NAME), os.O_CREAT | os.O_RDWR, 0o600)
        if _fcntl is not None:
            _fcntl.flock(fd, _fcntl.LOCK_EX)
            locked = True
        elif _msvcrt is not None:  # pragma: no cover - Windows
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
            os.lseek(fd, 0, os.SEEK_SET)
            _msvcrt.locking(fd, _msvcrt.LK_LOCK, 1)
            locked = True
    except OSError as exc:
        warnings.warn("报错数据集锁获取失败，降级为无锁写入：{}".format(exc))

    try:
        yield
    finally:
        if fd is not None:
            try:
                if locked and _fcntl is not None:
                    _fcntl.flock(fd, _fcntl.LOCK_UN)
                elif locked and _msvcrt is not None:  # pragma: no cover
                    os.lseek(fd, 0, os.SEEK_SET)
                    _msvcrt.locking(fd, _msvcrt.LK_UNLCK, 1)
            finally:
                os.close(fd)


# ── 对外 API ────────────────────────────────────────────────────────

def record(diagnostic, source, context=None, root=None):
    """归档一条报错，返回落盘/命中的记录 dict。

    :param diagnostic: 诊断信息，支持 ``Diagnostic`` 对象、dict 或纯字符串；
        dict 会读取 ``code/message/hint/fixes/line``。
    :param source: 出错源文件全文（只截取片段存储）。
    :param context: 可选补充字段：``line`` / ``lang_level`` / ``backend`` /
        ``light_version``。
    :param root: 归档目录；默认读 ``LIGHT_ERROR_CORPUS_DIR``。
    """
    root = _ensure_root(_resolve_root(root))
    ctx = dict(context or {})
    diag = _diagnostic_dict(diagnostic)

    line = _coerce_int(diag.get("line")) or _coerce_int(ctx.get("line"))
    code = _as_text(diag.get("code") or ctx.get("code") or "UNKNOWN")
    ts = _now_iso()

    entry = {
        "ts": ts,
        "last_seen": ts,
        "code": code,
        "message": sanitize(diag.get("message", "")),
        "hint": sanitize(diag.get("hint", "")),
        "fixes": [sanitize(item) for item in _fixes_list(diag.get("fixes"))],
        "source_snippet": sanitize(_snippet(source, line)),
        "source_hash": _source_hash(source),
        "lang_level": ctx.get("lang_level"),
        "backend": ctx.get("backend"),
        "light_version": ctx.get("light_version"),
        "hits": 1,
    }
    key = _entry_key(code, entry["source_hash"])

    with _locked(root):
        index = _load_index(root)
        existing = index["entries"].get(key)
        if isinstance(existing, dict):
            existing["hits"] = _coerce_int(existing.get("hits")) + 1
            existing["last_seen"] = ts
            # 最新一次诊断文本可能更完整，非空时顺手刷新。
            for name in ("message", "hint", "fixes"):
                value = entry[name]
                if value:
                    existing[name] = value
            _save_index(root, index)
            return dict(existing)

        month_file = os.path.join(root, "{}.jsonl".format(ts[:7]))
        line_text = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        # 单行一次写入：并发追加不会互相截断半行。
        with open(month_file, "a", encoding="utf-8") as handle:
            handle.write(line_text + "\n")
        index["entries"][key] = entry
        _save_index(root, index)
        return dict(entry)


def export_pairs(min_hits=1, root=None):
    """导出 SFT 风格样本：``[{"prompt": ..., "completion": ...}, ...]``。"""
    root = _resolve_root(root)
    min_hits = _coerce_int(min_hits)
    index = _load_index(root)
    rows = []
    for entry in index["entries"].values():
        if not isinstance(entry, dict):
            continue
        if _coerce_int(entry.get("hits")) < min_hits:
            continue
        rows.append(entry)

    rows.sort(
        key=lambda item: (
            -_coerce_int(item.get("hits")),
            -_ts_epoch(item.get("last_seen")),
            _as_text(item.get("code")),
        )
    )

    pairs = []
    for entry in rows:
        code = _as_text(entry.get("code"))
        message = _as_text(entry.get("message"))
        prompt = "报错代码: {}\n报错信息: {}\n代码片段:\n{}".format(
            code, message, _as_text(entry.get("source_snippet"))
        )
        steps = _fixes_list(entry.get("fixes"))
        if steps:
            completion = "修复步骤:\n" + "\n".join(
                "{}. {}".format(i, step) for i, step in enumerate(steps, 1)
            )
        else:
            completion = "根据报错信息修正上述代码。"
        hint = _as_text(entry.get("hint"))
        if hint:
            completion = "{}提示: {}".format(completion + "\n", hint)
        pairs.append({"prompt": prompt, "completion": completion})
    return pairs


def summary(window_days=30, top=10, root=None):
    """按错误码聚合：``[{code, hits, last_seen}]``，hits 降序。

    只统计 ``last_seen`` 落在窗口内的记录；``window_days`` 为 0 时不包含
    已经过期的条目。
    """
    root = _resolve_root(root)
    cutoff = _now() - _dt.timedelta(days=float(window_days))
    index = _load_index(root)

    aggregated = {}
    for entry in index["entries"].values():
        if not isinstance(entry, dict):
            continue
        last_seen = _parse_ts(entry.get("last_seen"))
        if last_seen is not None:
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=cutoff.tzinfo)
            if last_seen < cutoff:
                continue

        code = _as_text(entry.get("code"))
        bucket = aggregated.setdefault(
            code, {"code": code, "hits": 0, "last_seen": entry.get("last_seen") or ""}
        )
        bucket["hits"] += _coerce_int(entry.get("hits"))
        if _ts_epoch(entry.get("last_seen")) > _ts_epoch(bucket["last_seen"]):
            bucket["last_seen"] = entry.get("last_seen")

    rows = sorted(
        aggregated.values(),
        key=lambda item: (
            -item["hits"],
            -_ts_epoch(item["last_seen"]),
            item["code"],
        ),
    )
    if top is not None and _coerce_int(top) > 0:
        rows = rows[: _coerce_int(top)]
    return rows


def _normalize_before(before):
    if before is None:
        return _now() - _dt.timedelta(days=DEFAULT_RETENTION_DAYS)
    if isinstance(before, _dt.datetime):
        return before if before.tzinfo else before.astimezone()
    parsed = _parse_ts(before)
    if parsed is None:
        raise ValueError("before 必须是 datetime 或 ISO 时间字符串：{!r}".format(before))
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def purge(before=None, dry_run=True, root=None):
    """清理 ``last_seen`` 早于 ``before`` 的条目；默认只报告不落盘。

    ``before`` 缺省为 :data:`DEFAULT_RETENTION_DAYS` 天前。返回 dict 包含
    被清理条目与重写的月文件数量。
    """
    root = _resolve_root(root)
    cutoff = _normalize_before(before)
    index = _load_index(root)

    expired = []
    for key, entry in list(index["entries"].items()):
        if not isinstance(entry, dict):
            continue
        last_seen = _parse_ts(entry.get("last_seen"))
        if last_seen is not None and last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=cutoff.tzinfo)
        if last_seen is not None and last_seen >= cutoff:
            continue
        expired.append(
            {
                "code": entry.get("code"),
                "source_hash": entry.get("source_hash"),
                "hits": _coerce_int(entry.get("hits")),
                "last_seen": entry.get("last_seen"),
            }
        )

    result = {
        "dry_run": bool(dry_run),
        "before": cutoff.isoformat(timespec="seconds"),
        "removed": expired,
        "removed_count": len(expired),
        "files_rewritten": 0,
    }
    if dry_run or not expired:
        return result

    expired_keys = {
        _entry_key(_as_text(item["code"]), _as_text(item["source_hash"]))
        for item in expired
    }

    with _locked(root):
        index = _load_index(root)
        for key in expired_keys:
            index["entries"].pop(key, None)

        rewritten = 0
        try:
            month_files = sorted(
                name for name in os.listdir(root) if name.endswith(".jsonl")
            )
        except OSError:
            month_files = []
        for name in month_files:
            path = os.path.join(root, name)
            kept = []
            try:
                with open(path, encoding="utf-8") as handle:
                    for raw in handle:
                        raw = raw.strip()
                        if not raw:
                            continue
                        try:
                            item = json.loads(raw)
                        except ValueError:
                            kept.append(raw)
                            continue
                        key = _entry_key(
                            _as_text(item.get("code")), _as_text(item.get("source_hash"))
                        )
                        if key not in expired_keys:
                            kept.append(raw)
            except OSError as exc:
                warnings.warn("清理时读取 {} 失败：{}".format(name, exc))
                continue

            try:
                if kept:
                    _atomic_write(path, "".join(raw + "\n" for raw in kept))
                else:
                    os.remove(path)
                rewritten += 1
            except OSError as exc:
                warnings.warn("清理时重写 {} 失败：{}".format(name, exc))

        _save_index(root, index)
        result["files_rewritten"] = rewritten
        result["removed_count"] = len(expired)
    return result
