# -*- coding: utf-8 -*-
"""light-merge Windows 本机门禁「环境红」判据脚本（R90-B）。

为什么要有它：
  Windows 本机 LM 全量长期有若干条**与本轮改动无因果关系**的红（环境/负载归因），
  但一直靠人肉分辨「存量 / 环境 / 真回归」；而 `多平台矩阵.py --mode lm-full
  --refresh-local` 会把新基线写进 latest 再自比，「新增红 0」是自比、恒为 0、没有意义。
  本脚本把判据固定下来：对拍**上一份时间戳基线**（不是 latest），台账内的红容忍，
  台账外的红 = 回归红。

判据：
  新增红 = 本轮失败集合 − 基线失败集合（基线缺省 = 环境红台账全集）
  新增红 == 0 → rc 0（绿）；> 0 → rc 1（红）

子命令：
  judge       对拍本轮失败集合与基线，输出报告 + 退出码
  self-check  对 R89 基线（2026-09-24-003348）重放，须输出新增红 0；
              并做反向演示（注入 1 条合成红必须被识别）证明判据不是 no-op

输入：
  --current   junit XML（*.xml，pytest --junitxml 产物）或失败集合 JSON
  --baseline  基线 JSON（`lightharness/reports/本机lm基线_<ts>.json`）；缺省取台账全集
  --ledger    台账路径（缺省 tests/ci_environment_reds.txt）

退出码：0=绿 / 1=存在新增红 / 2=参数或 IO 错误
"""
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEDGER = os.path.join(_HERE, "ci_environment_reds.txt")

# self-check 用的历史基线（R89 收口时的 Windows 全量）
DEFAULT_SELF_CHECK_BASELINE = os.path.join(
    _HERE, "..", "..", "lightharness", "reports", "本机lm基线_2026-09-24-003348.json")


# ── 台账 ────────────────────────────────────────────────────────────────────
def load_ledger(path=DEFAULT_LEDGER):
    """解析环境红台账 → (nodeids: set[str], meta: list[dict])

    台账格式（tab 分隔，与 lightharness 对齐）：
        <编号>\t<nodeid>\t<类别>\t<是否负载敏感 0/1>\t<说明>
    以 `#` 开头的行为注释，不解析。
    """
    nodeids, meta = set(), []
    if not os.path.isfile(path):
        return nodeids, meta
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            eid = parts[0].strip()
            nodeid = parts[1].strip()
            if not nodeid:
                continue
            category = parts[2].strip() if len(parts) > 2 else ""
            load_sensitive = (parts[3].strip() if len(parts) > 3 else "0") in ("1", "true", "True")
            note = parts[4].strip() if len(parts) > 4 else ""
            nodeids.add(nodeid)
            meta.append({"id": eid, "nodeid": nodeid, "category": category,
                         "load": load_sensitive, "note": note})
    return nodeids, meta


# ── 失败集合 ────────────────────────────────────────────────────────────────
def load_failures_from_junit(xml_path):
    """从 pytest --junitxml 产物取失败/错误用例的 nodeid。

    junit 只给 classname（点分）+ name，没有 file 属性，需要还原成
    pytest 风格的 nodeid 才能与台账/基线对拍（`tests/x.py::Class::test_y`）。
    还原规则：把 classname 按点拆开拼成路径试文件系统——
      · 全部段拼起来 + ".py" 存在 → 最后一段是文件名（模块级函数）；
      · 否则最后一段是类名，去掉它再拼，并把类名插回 nodeid。
    """
    repo_root = os.path.dirname(_HERE)
    root = ET.parse(xml_path).getroot()
    out = []
    for tc in root.iter("testcase"):
        if not any(child.tag in ("failure", "error") for child in tc):
            continue
        cls = tc.get("classname") or ""
        name = tc.get("name") or ""
        if "::" in name:
            out.append(name)
            continue
        parts = cls.split(".") if cls else []
        file_part, cls_part = "", None
        if parts:
            cand = os.path.join(repo_root, *parts) + ".py"
            if os.path.isfile(cand):
                file_part = "/".join(parts) + ".py"
            elif len(parts) >= 2:
                file_part = "/".join(parts[:-1]) + ".py"
                cls_part = parts[-1]
            else:
                file_part = parts[0] + ".py"
        nodeid = f"{file_part}::{cls_part}::{name}" if cls_part else (
            f"{file_part}::{name}" if file_part else name)
        out.append(nodeid)
    return out


def load_failures(path):
    """统一入口：按扩展名分派（.xml → junit；.json → 基线/列表）。"""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"失败集合文件不存在: {path}")
    if path.lower().endswith(".xml"):
        return load_failures_from_junit(path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        failed = data.get("failed")
        if failed is None:
            for key in ("failures", "red"):
                if key in data:
                    failed = data[key]
                    break
        if failed is None:
            raise ValueError(f"无法从 JSON 解析失败集合: {path}")
        data = failed
    if not isinstance(data, list):
        raise ValueError(f"失败集合必须是列表: {path}")
    out = []
    for x in data:
        if isinstance(x, dict):
            nid = x.get("id") or x.get("nodeid")
        else:
            nid = x
        if nid:
            out.append(str(nid).strip())
    return out


# ── 判据核心 ────────────────────────────────────────────────────────────────
def judge(current, baseline):
    cur, base = set(current), set(baseline)
    return {
        "new_reds": cur - base,
        "env_reds_present": cur & base,
        "recovered": base - cur,
        "counts": {"current": len(cur), "baseline": len(base),
                   "new": len(cur - base), "present": len(cur & base),
                   "recovered": len(base - cur)},
    }


def _print_report(result, baseline_label):
    c = result["counts"]
    print("=" * 64)
    print("[Windows LM 环境红判据] 新增红对拍报告")
    print("-" * 64)
    print(f"  基线来源          : {baseline_label}")
    print(f"  本轮失败数        : {c['current']}")
    print(f"  基线失败数        : {c['baseline']}")
    print(f"  命中基线/台账     : {c['present']} 条")
    print(f"  已恢复(基线有本轮无): {c['recovered']} 条")
    print(f"  ** 新增红 **      : {c['new']} 条")
    if result["new_reds"]:
        print("  新增红清单（疑似回归，必须逐条给解释）:")
        for f in sorted(result["new_reds"]):
            print(f"    x {f}")
    if result["env_reds_present"]:
        print("  命中基线/台账:")
        for f in sorted(result["env_reds_present"]):
            print(f"    . {f}")
    print("-" * 64)
    print(f"  判据结论          : "
          f"{'绿（新增红 = 0）' if c['new'] == 0 else '红（存在新增红）'}")
    print("=" * 64)


# ── 子命令 ──────────────────────────────────────────────────────────────────
def cmd_judge(args):
    try:
        current = load_failures(args.current)
    except Exception as e:
        print(f"[错误] 读取当前失败集合失败: {e}", file=sys.stderr)
        return 2
    ledger_ids, _ = load_ledger(args.ledger)
    if args.baseline:
        try:
            baseline = load_failures(args.baseline)
            label = args.baseline
        except Exception as e:
            print(f"[错误] 读取基线失败: {e}", file=sys.stderr)
            return 2
    else:
        baseline = ledger_ids
        label = f"环境红台账 ({os.path.basename(args.ledger)})，{len(ledger_ids)} 条"
    _print_report(judge(current, baseline), label)
    return 0 if not (set(current) - set(baseline)) else 1


def cmd_self_check(args):
    """对历史基线重放 + 反向演示，证明判据可复现且不是 no-op。"""
    print("[self-check] 重放历史基线 + 反向演示")
    all_ok = True

    base_path = args.baseline or DEFAULT_SELF_CHECK_BASELINE
    if os.path.isfile(base_path):
        baseline = load_failures(base_path)
        print(f"  历史基线: {os.path.basename(base_path)}（{len(baseline)} 条失败）")
        r = judge(baseline, baseline)
        n = r["counts"]["new"]
        status = "PASS" if n == 0 else "FAIL"
        all_ok = all_ok and (n == 0)
        print(f"  [{status}] 基线自对拍: 失败 {r['counts']['current']} / 新增红 {n}")
    else:
        print(f"  [WARN] 历史基线不存在，跳过重放: {base_path}")

    # 反向演示：台账之外注入 1 条合成红，必须被识别为新增红
    ledger_ids, _ = load_ledger(args.ledger)
    print(f"  台账条目数: {len(ledger_ids)}")
    synthetic = sorted(ledger_ids) + ["tests/test_合成_new_regression.py::test_never_exists"]
    demo = judge(synthetic, ledger_ids)
    if demo["counts"]["new"] == 1:
        print(f"  [PASS] 反向演示: 注入 1 条合成红 → 正确识别新增红 {demo['counts']['new']} 条")
    else:
        print(f"  [FAIL] 反向演示: 应识别 1 条，实际 {demo['counts']['new']}", file=sys.stderr)
        all_ok = False

    print("=" * 64)
    print(f"[self-check] 结论: {'全部通过' if all_ok else '存在失败'}")
    print("=" * 64)
    return 0 if all_ok else 1


def build_parser():
    p = argparse.ArgumentParser(description="light-merge Windows 门禁环境红判据脚本")
    sub = p.add_subparsers(dest="cmd", required=True)

    j = sub.add_parser("judge", help="对拍本轮失败集合与基线")
    j.add_argument("--current", required=True, help="junit XML 或失败集合 JSON")
    j.add_argument("--baseline", default=None, help="基线 JSON（缺省=台账全集）")
    j.add_argument("--ledger", default=DEFAULT_LEDGER, help="台账路径")
    j.set_defaults(func=cmd_judge)

    s = sub.add_parser("self-check", help="重放历史基线 + 反向演示")
    s.add_argument("--baseline", default=None, help="历史基线 JSON（缺省=R89 基线）")
    s.add_argument("--ledger", default=DEFAULT_LEDGER, help="台账路径")
    s.set_defaults(func=cmd_self_check)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
