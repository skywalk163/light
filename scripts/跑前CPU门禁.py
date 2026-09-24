# -*- coding: utf-8 -*-
"""R94 门禁：Windows 本机全量**跑前 CPU 检查**（裁定 1 的执行件）。

为什么要有它：
  高整机负载（实测 76~99% CPU）下 xdist worker 会被杀（`[gwN] node down` →
  INTERNALERROR 或整轮挂死），该结果**既不能判绿也不能判红**——它与代码无关
  （见 docs/known-issues/R94-xdist-worker-kill.md）。与其事后争论，不如跑前挡住：
  平均负载 ≥ 阈值 → 不跑，标记 **invalid**，退出码 3。

用法：
  # 1) 只检查（放行/拒绝）
  python scripts/跑前CPU门禁.py                     # 默认阈值 80%，采样 10s
  python scripts/跑前CPU门禁.py --threshold 80 --sample 15

  # 2) 门禁 + 执行（推荐：把全量命令接在 -- 之后，不通过就不跑）
  python scripts/跑前CPU门禁.py -- python -m pytest tests/ -q --junitxml=_r94/x.xml

退出码：
  0 = 放行（低负载，可以跑）；3 = 拒绝（高负载，结果应标 invalid，不判红绿）；
  2 = 参数/环境错误（如 psutil 缺失）；子命令退出码 = 被执行命令的原样返回码。

口径说明（R94 裁定）：
  * 判定依据是**整机平均 CPU 利用率**，不是进程级；取样含一次预热（首次
    psutil.cpu_percent() 无基线会返回 0，必须预热后再采）。
  * 阈值默认 80%，与 R93 事故观测（76~99% 翻车 / 低负载 3 轮全净）一致。
  * 本脚本**只挡不修**：它不降低负载、不杀进程、不改任何测试语义。
"""
import argparse
import json
import subprocess
import sys
import time

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


def sample_cpu(seconds: float, interval: float = 0.5):
    """在 seconds 秒内按 interval 采样整机 CPU%，返回 (平均值, 最大值, 样本数)。"""
    psutil.cpu_percent(percpu=False)  # 预热：首次调用无基线会返回 0.0
    vals = []
    end = time.time() + seconds
    while time.time() < end:
        vals.append(psutil.cpu_percent(interval=interval))
    if not vals:
        vals = [psutil.cpu_percent(interval=None)]
    return sum(vals) / len(vals), max(vals), len(vals)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Windows 本机全量跑前 CPU 门禁（高负载不跑 / 标 invalid）")
    ap.add_argument("--threshold", type=float, default=80.0,
                    help="平均 CPU%% 阈值，≥ 该值拒绝运行（默认 80）")
    ap.add_argument("--sample", type=float, default=10.0,
                    help="采样时长（秒，默认 10）")
    ap.add_argument("--json", dest="json_path", default=None,
                    help="把判定结果写到该 JSON 路径")
    ap.add_argument("--force", action="store_true",
                    help="无视门禁强制执行（仅供诊断；结果仍应标 invalid）")
    ap.add_argument("cmd", nargs=argparse.REMAINDER,
                    help="待执行命令，用 `--` 开头与门禁参数隔开")
    args = ap.parse_args(argv)

    if psutil is None:
        print("[CPU门禁] 错误：缺少 psutil，无法采样（pip install psutil）",
              file=sys.stderr)
        return 2

    # argparse.REMAINDER 会把首个 `--` 也收进来，去掉
    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if cmd and cmd[0] == "--":  # 双重 `--` 兜底
        cmd = cmd[1:]

    avg, mx, n = sample_cpu(args.sample)
    passed = avg < args.threshold
    rec = {
        "gate": "跑前CPU门禁",
        "round": "R94",
        "cpu_avg": round(avg, 2),
        "cpu_max": round(mx, 2),
        "samples": n,
        "threshold": args.threshold,
        "sample_seconds": args.sample,
        "verdict": "PASS（低负载，可跑）" if passed else "INVALID（高负载，不跑/不判红绿）",
        "force": bool(args.force),
        "cmd": cmd or None,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_count": psutil.cpu_count(),
    }
    print("=" * 64)
    print("[CPU门禁] 平均 %.1f%% / 峰值 %.1f%%（%d 样本 / %.0fs），阈值 %.0f%%"
          % (avg, mx, n, args.sample, args.threshold))
    print("[CPU门禁] 判定：%s" % rec["verdict"])
    print("=" * 64)
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)
        print("[CPU门禁] 已写 %s" % args.json_path)

    if not cmd:
        return 0 if (passed or args.force) else 3

    if not passed and not args.force:
        print("[CPU门禁] 拒绝执行：%s" % " ".join(cmd), file=sys.stderr)
        return 3

    print("[CPU门禁] 放行，执行：%s" % " ".join(cmd), flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd)
    rec["elapsed"] = round(time.time() - t0, 1)
    rec["cmd_rc"] = proc.returncode
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
