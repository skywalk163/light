"""
光明（Light）编程语言 - 社区反馈收集器

提供 `light feedback` CLI 命令，用于收集用户反馈。

功能：
  - light feedback              交互式收集反馈（评分、评论、分类）
  - light feedback --list       查看本地反馈记录
  - light feedback --export     导出反馈为 JSON
  - light feedback --send       提交本地反馈到 GitHub Issues

反馈数据存储位置：
  Windows: %USERPROFILE%\\.light\\feedback\\
  macOS/Linux: ~/.light/feedback/
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# 版本号：统一从 version 模块读取，避免硬编码
try:
    from version import VERSION
except ImportError:  # pragma: no cover - 兼容以包方式导入的场景
    try:
        from .version import VERSION
    except ImportError:
        VERSION = "7.0.0"


# =============================================================================
# 反馈数据模型
# =============================================================================

FEEDBACK_CATEGORIES = {
    "bug": "Bug 报告",
    "feature": "功能建议",
    "docs": "文档反馈",
    "general": "一般反馈",
    "performance": "性能问题",
    "ux": "使用体验",
}

RATING_LABELS = {
    1: "非常不满意",
    2: "不满意",
    3: "一般",
    4: "满意",
    5: "非常满意",
}


def get_feedback_dir() -> Path:
    """获取反馈数据存储目录"""
    env_dir = os.environ.get("LIGHT_CONFIG_DIR")
    if env_dir:
        base = Path(env_dir)
    else:
        base = Path.home() / ".light"
    feedback_dir = base / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    return feedback_dir


def _next_id(feedback_dir: Path) -> int:
    """生成下一个反馈 ID"""
    existing = list(feedback_dir.glob("feedback_*.json"))
    if not existing:
        return 1
    ids = []
    for p in existing:
        try:
            ids.append(int(p.stem.split("_")[1]))
        except (IndexError, ValueError):
            continue
    return max(ids) + 1 if ids else 1


def _timestamp() -> str:
    """返回当前时间戳字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =============================================================================
# 反馈数据操作
# =============================================================================


def save_feedback(
    rating: int,
    comments: str,
    category: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """保存一条反馈记录到本地文件

    Args:
        rating: 评分（1-5）
        comments: 反馈内容
        category: 反馈分类
        metadata: 可选的元数据字典

    Returns:
        保存的反馈记录字典
    """
    feedback_dir = get_feedback_dir()
    feedback_id = _next_id(feedback_dir)

    record = {
        "id": feedback_id,
        "rating": rating,
        "rating_label": RATING_LABELS.get(rating, "未知"),
        "comments": comments,
        "category": category,
        "category_label": FEEDBACK_CATEGORIES.get(category, "其他"),
        "timestamp": _timestamp(),
        "version": VERSION,
        "sent": False,
    }

    if metadata:
        record["metadata"] = metadata

    filepath = feedback_dir / f"feedback_{feedback_id:04d}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return record


def list_feedback() -> List[Dict[str, Any]]:
    """列出所有本地反馈记录"""
    feedback_dir = get_feedback_dir()
    records = []
    for filepath in sorted(feedback_dir.glob("feedback_*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                records.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    return records


def export_feedback(output_path: Optional[str] = None) -> str:
    """导出所有反馈为 JSON 文件

    Args:
        output_path: 输出文件路径，默认为当前目录下的 feedback_export.json

    Returns:
        输出文件的绝对路径
    """
    records = list_feedback()
    if output_path:
        out_path = Path(output_path)
    else:
        out_path = Path.cwd() / "feedback_export.json"

    export_data = {
        "export_time": _timestamp(),
        "total_count": len(records),
        "records": records,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    return str(out_path.resolve())


def send_feedback(record: Dict[str, Any]) -> bool:
    """将单条反馈提交到 GitHub Issues

    使用 GitHub API 创建一个 Issue（需要 GITHUB_TOKEN 环境变量）。

    Args:
        record: 反馈记录字典

    Returns:
        是否成功提交
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("[错误] 未设置 GITHUB_TOKEN 环境变量", file=sys.stderr)
        print("[提示] 请设置 GITHUB_TOKEN 以启用提交到 GitHub Issues", file=sys.stderr)
        print("[提示] 也可以直接手动提交：https://github.com/skywalk163/light/issues/new", file=sys.stderr)
        return False

    import urllib.request
    import urllib.parse

    category_label = record.get("category_label", "一般反馈")
    rating_info = f"评分: {record.get('rating')}/5 ({record.get('rating_label', '')})"
    title = f"[反馈] {category_label} - {record.get('comments', '')[:50]}"
    body = f"""## 反馈信息

- **分类**: {category_label}
- **评分**: {record.get('rating')}/5
- **时间**: {record.get('timestamp', '')}
- **版本**: {record.get('version', '')}

## 反馈内容

{record.get('comments', '(无内容)')}

---

> 此 Issue 由 `light feedback --send` 自动创建
"""

    data = json.dumps({
        "title": title,
        "body": body,
        "labels": [record.get("category", "feedback")],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.github.com/repos/skywalk163/light/issues",
        data=data,
        headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v3+json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            issue_url = result.get("html_url", "")
            print(f"[成功] 已提交反馈到 Issue: {issue_url}")

            # 更新本地记录，标记为已发送
            _mark_as_sent(record.get("id"))
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"[错误] 提交失败 (HTTP {e.code}): {error_body}", file=sys.stderr)
        return False
    except urllib.error.URLError as e:
        print(f"[错误] 网络错误: {e.reason}", file=sys.stderr)
        return False


def send_all_feedback() -> int:
    """提交所有未发送的反馈到 GitHub Issues

    Returns:
        成功提交的数量
    """
    records = list_feedback()
    unsent = [r for r in records if not r.get("sent", False)]

    if not unsent:
        print("所有反馈记录已提交，无需重复提交。")
        return 0

    success_count = 0
    for record in unsent:
        print(f"\n正在提交反馈 #{record.get('id', '?')}...")
        if send_feedback(record):
            success_count += 1
        else:
            print(f"  跳过反馈 #{record.get('id', '?')}，稍后可重试。")

    print(f"\n[摘要] 成功提交: {success_count}/{len(unsent)}")
    return success_count


def _mark_as_sent(feedback_id: Optional[int]) -> None:
    """将指定 ID 的反馈记录标记为已发送"""
    if feedback_id is None:
        return
    feedback_dir = get_feedback_dir()
    filepath = feedback_dir / f"feedback_{feedback_id:04d}.json"
    if not filepath.exists():
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            record = json.load(f)
        record["sent"] = True
        record["sent_at"] = _timestamp()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, OSError):
        pass


# =============================================================================
# 交互式反馈收集
# =============================================================================


def _prompt_int(prompt: str, min_val: int, max_val: int) -> int:
    """交互式获取整数输入"""
    while True:
        try:
            val = int(input(prompt).strip())
            if min_val <= val <= max_val:
                return val
            print(f"请输入 {min_val}-{max_val} 之间的数字。")
        except (ValueError, EOFError):
            print("输入无效，请重试。")


def _prompt_choice(prompt: str, choices: Dict[str, str]) -> str:
    """交互式获取选项输入"""
    print(prompt)
    for key, label in choices.items():
        print(f"  [{key}] {label}")
    while True:
        try:
            val = input("请选择: ").strip().lower()
            if val in choices:
                return val
            print(f"无效选择，请输入: {', '.join(choices.keys())}")
        except EOFError:
            print()
            return list(choices.keys())[0]


def _prompt_text(prompt: str) -> str:
    """交互式获取多行文本输入"""
    print(prompt)
    print("（输入空行结束）")
    lines = []
    try:
        while True:
            line = input()
            if not line.strip():
                break
            lines.append(line)
    except EOFError:
        print()
    return "\n".join(lines) if lines else ""


def collect_feedback_interactive() -> Optional[Dict[str, Any]]:
    """交互式收集用户反馈

    Returns:
        保存的反馈记录字典，如果用户取消则返回 None
    """
    print()
    print("=" * 50)
    print("  光明（Light）反馈收集")
    print("=" * 50)
    print()
    print("感谢您使用光明！您的反馈是我们改进的重要依据。")
    print()

    # 评分
    rating = _prompt_int("请为光明评分（1-5，5 为最高）: ", 1, 5)

    # 分类
    category = _prompt_choice(
        "\n请选择反馈分类：",
        FEEDBACK_CATEGORIES,
    )

    # 评论
    print()
    comments = _prompt_text("请详细描述您的反馈或建议：")

    if not comments.strip():
        print("\n[提示] 反馈内容为空，取消保存。")
        return None

    # 确认
    print()
    print("=" * 50)
    print("  反馈摘要")
    print("=" * 50)
    print(f"  评分: {rating}/5 ({RATING_LABELS.get(rating, '')})")
    print(f"  分类: {FEEDBACK_CATEGORIES.get(category, '其他')}")
    print(f"  内容: {comments[:100]}{'...' if len(comments) > 100 else ''}")
    print()

    confirm = _prompt_choice(
        "确认保存此反馈？",
        {"y": "是，保存", "n": "否，取消"},
    )

    if confirm != "y":
        print("已取消。")
        return None

    # 保存
    record = save_feedback(rating, comments, category)
    print(f"\n[成功] 反馈已保存（ID: {record['id']}）")
    print(f"[提示] 运行 `light feedback --send` 提交到 GitHub Issues")
    print()

    return record


# =============================================================================
# 显示格式化
# =============================================================================


def _print_feedback_table(records: List[Dict[str, Any]]) -> None:
    """格式化打印反馈记录列表"""
    if not records:
        print("暂无反馈记录。")
        return

    print(f"\n共 {len(records)} 条反馈记录：")
    print()
    header = f"{'ID':>4} | {'评分':>4} | {'分类':<10} | {'已提交':<6} | {'时间':<19} | {'内容'}"
    print(header)
    print("-" * len(header))
    for r in records:
        rid = r.get("id", "?")
        rating = f"{r.get('rating', '?')}/5"
        cat = r.get("category_label", r.get("category", "?"))
        sent = "是" if r.get("sent", False) else "否"
        ts = r.get("timestamp", "?")
        comments = r.get("comments", "")
        content = comments[:50].replace("\n", " ") if comments else "(空)"
        print(f"{rid:>4} | {rating:>4} | {cat:<10} | {sent:<6} | {ts:<19} | {content}")
    print()


# =============================================================================
# CLI 命令
# =============================================================================


def run_feedback_cli(args: Any) -> int:
    """执行 feedback 命令

    Args:
        args: 命令行参数对象

    Returns:
        退出码（0 表示成功）
    """
    # --list: 查看本地反馈
    if getattr(args, "list_feedback", False):
        records = list_feedback()
        _print_feedback_table(records)
        return 0

    # --export: 导出反馈为 JSON
    if getattr(args, "export", False):
        output = args.export
        if output is True:
            output = None
        try:
            path = export_feedback(output)
            print(f"[成功] 反馈已导出到: {path}")
            return 0
        except Exception as e:
            print(f"[错误] 导出失败: {e}", file=sys.stderr)
            return 1

    # --send: 提交到 GitHub Issues
    if getattr(args, "send", False):
        send_all_feedback()
        return 0

    # 默认：交互式收集
    collect_feedback_interactive()
    return 0


def setup_feedback_subparser(subparsers) -> None:
    """在 CLI 中注册 feedback 子命令

    用法：
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        setup_feedback_subparser(subparsers)
    """
    feedback_parser = subparsers.add_parser(
        "feedback",
        help="收集和查看用户反馈",
        description="光明反馈收集工具 - 收集、查看、导出和提交用户反馈",
    )
    feedback_parser.add_argument(
        "--list",
        "-l",
        dest="list_feedback",
        action="store_true",
        help="查看本地反馈记录",
    )
    feedback_parser.add_argument(
        "--export",
        "-e",
        nargs="?",
        const=True,
        default=False,
        metavar="FILE",
        help="导出反馈为 JSON 文件（可选指定输出路径）",
    )
    feedback_parser.add_argument(
        "--send",
        "-s",
        action="store_true",
        help="提交本地反馈到 GitHub Issues（需要设置 GITHUB_TOKEN）",
    )
    feedback_parser.set_defaults(func=run_feedback_cli)


# =============================================================================
# 独立入口
# =============================================================================

def main():
    """独立运行的命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="光明（Light）反馈收集工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  light feedback              交互式收集反馈
  light feedback --list       查看本地反馈
  light feedback --export     导出反馈为 JSON
  light feedback --send       提交到 GitHub Issues
  light feedback --export ./my_feedback.json  导出到指定文件
        """,
    )
    parser.add_argument(
        "--list", "-l",
        dest="list_feedback",
        action="store_true",
        help="查看本地反馈记录",
    )
    parser.add_argument(
        "--export", "-e",
        nargs="?",
        const=True,
        default=False,
        metavar="FILE",
        help="导出反馈为 JSON 文件",
    )
    parser.add_argument(
        "--send", "-s",
        action="store_true",
        help="提交本地反馈到 GitHub Issues",
    )

    args = parser.parse_args()
    sys.exit(run_feedback_cli(args))


if __name__ == "__main__":
    main()