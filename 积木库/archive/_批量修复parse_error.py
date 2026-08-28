"""
批量修复光明积木库中所有剩余的 ParseError
覆盖模式1~7，修改前自动备份，输出详细统计
"""

import os
import re
import shutil
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent / "blocks_v5"
BACKUP_DIR = Path(__file__).parent / "_parse_error_backup"

# ========== 统计 ==========
stats = {
    "pattern1_decimal_renamed": 0,    # 模式1：重命名含小数文件
    "pattern1_decimal_deleted": 0,    # 模式1：删除（已有中文版）
    "pattern2_percent_renamed": 0,    # 模式2：% → 百分比
    "pattern3_跳出值_fixed": 0,       # 模式3：p_跳出值值值 → p_跳出值
    "pattern4_operator_fixed": 0,     # 模式4：大于 等于 → 大于等于
    "pattern5_param_space_fixed": 0,  # 模式5：参数名空格 → 下划线
    "pattern6_rmsprop_fixed": 0,      # 模式6：RMSprop括号修复
    "pattern7_kr20_fixed": 0,         # 模式7：KR20求和关键字
}

# ========== 工具函数 ==========

def log(msg):
    print(f"  [修复] {msg}")

def backup_file(filepath):
    """修改前备份文件"""
    if not filepath.exists():
        return
    rel = filepath.relative_to(BASE_DIR.parent)
    dst = BACKUP_DIR / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(filepath, dst)

def safe_read(filepath):
    try:
        return filepath.read_text("utf-8")
    except Exception as e:
        print(f"  [警告] 读取失败 {filepath}: {e}")
        return None

def safe_write(filepath, content):
    filepath.write_text(content, "utf-8")


# ========== 模式1：函数名含小数 ==========

# 小数 → 中文数字映射
DECIMAL_TO_CHINESE = {
    "0.01": "零点零一", "0.02": "零点零二", "0.03": "零点零三",
    "0.05": "零点零五", "0.07": "零点零七",
    "0.1": "零点一", "0.15": "零点一五", "0.25": "零点二五",
    "0.35": "零点三五", "0.45": "零点四五", "0.55": "零点五五",
    "0.65": "零点六五", "0.75": "零点七五", "0.85": "零点八五",
    "0.95": "零点九五", "0.5": "零点五",
    "1.5": "一点五", "2.5": "二点五",
}

# 已有中文版本用的"百分之"映射（0.01~0.07 实际用百分之N）
# 这些文件已存在且是正确的中文版本
DECIMAL_TO_PERCENT = {
    "0.01": "百分之一", "0.02": "百分之二", "0.03": "百分之三",
    "0.05": "百分之五", "0.07": "百分之七",
}

# 四种操作前缀
OPS = ["各乘", "各加", "各减", "各除"]

def _decimal_name_to_chinese(name, decimal, chinese):
    """将文件名中的小数替换为中文数字"""
    return name.replace(decimal, chinese)

def fix_pattern1():
    """修复模式1：函数名含小数"""
    print("\n===== 模式1：函数名含小数 =====")
    data_dir = BASE_DIR / "数据"
    fixed_files = []

    for f in sorted(data_dir.glob("*.light")):
        stem = f.stem  # 不含扩展名的文件名

        for op in OPS:
            # 跳过不以当前操作前缀开头的文件
            if not stem.startswith(op):
                continue

            suffix = stem[len(op):]  # 操作后面的部分，如 "0.01" 或 "0.01数据"

            # 检查是否是含小数的文件
            for decimal, chinese in DECIMAL_TO_CHINESE.items():
                if decimal not in suffix:
                    continue

                # 判断是否带 "数据" 后缀
                has_data_suffix = suffix.endswith("数据")
                decimal_part = decimal
                if has_data_suffix:
                    # 检查后缀是否以 decimal 开头
                    if suffix == decimal + "数据":
                        pass  # 匹配
                    else:
                        continue
                else:
                    if suffix != decimal:
                        continue

                # 构建中文版本的文件名
                chinese_suffix = chinese + ("数据" if has_data_suffix else "")
                chinese_stem = op + chinese_suffix
                chinese_file = data_dir / f"{chinese_stem}.light"

                # 也检查是否有"百分之"版本
                percent_suffix = DECIMAL_TO_PERCENT.get(decimal, "")
                if percent_suffix:
                    pc_stem = op + percent_suffix + ("数据" if has_data_suffix else "")
                    percent_file = data_dir / f"{pc_stem}.light"
                else:
                    percent_file = None

                # 决定是删除还是重命名
                if chinese_file.exists() or (percent_file and percent_file.exists()):
                    # 中文版本已存在，删除含小数文件
                    existing = chinese_file if chinese_file.exists() else percent_file
                    backup_file(f)
                    f.unlink()
                    stats["pattern1_decimal_deleted"] += 1
                    log(f"删除 {f.name}（已有中文版 {existing.name}）")
                else:
                    # 需要重命名并更新内容
                    content = safe_read(f)
                    if content is None:
                        continue

                    # 在内容中替换函数名
                    new_content = content.replace(stem, chinese_stem)

                    # 也替换注释中的名字
                    new_content = new_content.replace(
                        f"（数据领域，自动生成桩）",
                        "（数据领域，自动生成桩）"
                    )

                    backup_file(f)
                    new_file = data_dir / f"{chinese_stem}.light"
                    safe_write(new_file, new_content)
                    f.unlink()  # 删除旧文件
                    stats["pattern1_decimal_renamed"] += 1
                    log(f"重命名 {f.name} → {new_file.name}")

                # 已处理此文件，跳出内层循环
                break
            # end for decimal
        # end for op
    # end for f


# ========== 模式2：% 符号 ==========

def fix_pattern2():
    """修复模式2：文件名含%符号"""
    print("\n===== 模式2：文件名含%符号 =====")
    data_dir = BASE_DIR / "数据"

    percent_files = [
        "加10%.light", "加10%数据.light",
        "减10%.light", "减10%数据.light",
        "加20%.light", "加20%数据.light",
        "减20%.light", "减20%数据.light",
        "加50%.light", "加50%数据.light",
        "减50%.light", "减50%数据.light",
    ]

    for fname in percent_files:
        f = data_dir / fname
        if not f.exists():
            continue

        # 新文件名：% → 百分比
        new_fname = fname.replace("%", "百分比")
        new_f = data_dir / new_fname

        if new_f.exists():
            # 目标文件已存在，只需删除旧文件
            backup_file(f)
            f.unlink()
            stats["pattern2_percent_renamed"] += 1
            log(f"删除 {f.name}（已有 {new_f.name}）")
        else:
            # 内容中已经包含"百分比"（之前已修复），只需重命名
            backup_file(f)
            f.rename(new_f)
            stats["pattern2_percent_renamed"] += 1
            log(f"重命名 {f.name} → {new_f.name}")


# ========== 模式3：p_跳出值值值 → p_跳出值 ==========

def fix_pattern3():
    """修复模式3：p_跳出值值值 和 p_p_跳出值值值"""
    print("\n===== 模式3：p_跳出值值值 → p_跳出值 =====")

    # 搜索所有包含 p_跳出值值值 的文件
    pattern = re.compile(r"p_p_跳出值值值|p_跳出值值值")
    affected = []

    for f in BASE_DIR.rglob("*.light"):
        try:
            content = f.read_text("utf-8")
            if pattern.search(content):
                affected.append(f)
        except Exception:
            continue

    for f in affected:
        content = f.read_text("utf-8")
        new_content = content.replace("p_p_跳出值值值", "p_跳出值跳出值")
        new_content = new_content.replace("p_跳出值值值", "p_跳出值")
        if new_content != content:
            backup_file(f)
            safe_write(f, new_content)
            stats["pattern3_跳出值_fixed"] += 1
            log(f"{f.relative_to(BASE_DIR)}")


# ========== 模式4：大于 等于 → 大于等于 ==========

def fix_pattern4():
    """修复模式4：大于 等于 → 大于等于，小于 等于 → 小于等于"""
    print("\n===== 模式4：大于 等于 / 小于 等于 → 大于等于 / 小于等于 =====")

    pattern = re.compile(r"(大于|小于|不) 等于")
    affected = []

    for f in BASE_DIR.rglob("*.light"):
        try:
            content = f.read_text("utf-8")
            if pattern.search(content):
                affected.append(f)
        except Exception:
            continue

    for f in affected:
        content = f.read_text("utf-8")
        new_content = content.replace("大于 等于", "大于等于")
        new_content = new_content.replace("小于 等于", "小于等于")
        new_content = new_content.replace("不 等于", "不等于")
        if new_content != content:
            backup_file(f)
            safe_write(f, new_content)
            stats["pattern4_operator_fixed"] += 1
            log(f"{f.relative_to(BASE_DIR)}")


# ========== 模式5：参数名含空格 p_i 加 2 → p_i_加_2 ==========

def fix_pattern5():
    """修复模式5：参数名 p_i 加 2 → p_i_加_2"""
    print("\n===== 模式5：参数名空格 → 下划线 =====")

    pattern = re.compile(r"p_i 加 2")
    affected = []

    for f in BASE_DIR.rglob("*.light"):
        try:
            content = f.read_text("utf-8")
            if pattern.search(content):
                affected.append(f)
        except Exception:
            continue

    for f in affected:
        content = f.read_text("utf-8")
        new_content = content.replace("p_i 加 2", "p_i_加_2")
        if new_content != content:
            backup_file(f)
            safe_write(f, new_content)
            stats["pattern5_param_space_fixed"] += 1
            log(f"{f.relative_to(BASE_DIR)}")


# ========== 模式6：RMSprop 括号修复 ==========

def fix_pattern6():
    """修复模式6：函数RMSprop.light 括号平衡"""
    print("\n===== 模式6：RMSprop 括号修复 =====")

    f = BASE_DIR / "函数" / "函数RMSprop.light"
    if not f.exists():
        print("  [跳过] 文件不存在")
        return

    content = safe_read(f)
    if content is None:
        return

    # 原行:
    # 返回 学习率 除 平方根(累积 乘 衰减 加 (1 减 衰减) 乘 cb_梯度 乘 cb_梯度 加 小量) 乘 梯度函数(输入)
    # 问题: 平方根(...) 中缺少一对括号，导致 ) 在错误位置闭合
    # 修复: 平方根(累积 乘 衰减 加 (1 减 衰减) 乘 (cb_梯度 乘 cb_梯度) 加 小量)
    old_line = "返回 学习率 除 平方根(累积 乘 衰减 加 (1 减 衰减) 乘 cb_梯度 乘 cb_梯度 加 小量) 乘 梯度函数(输入)"
    new_line = "返回 学习率 除 平方根(累积 乘 衰减 加 (1 减 衰减) 乘 (cb_梯度 乘 cb_梯度) 加 小量) 乘 梯度函数(输入)"

    if old_line in content:
        backup_file(f)
        new_content = content.replace(old_line, new_line)
        safe_write(f, new_content)
        stats["pattern6_rmsprop_fixed"] += 1
        log("函数RMSprop.light 括号修复完成")
    else:
        print("  [跳过] 未找到需要修复的行（可能已修复）")


# ========== 模式7：KR20 求和关键字 ==========

def fix_pattern7():
    """修复模式7：教育KR20.light 求和关键字"""
    print("\n===== 模式7：KR20 求和关键字修复 =====")

    f = BASE_DIR / "教育" / "KR20.light"
    if not f.exists():
        print("  [跳过] 文件不存在")
        return

    content = safe_read(f)
    if content is None:
        return

    # 原行:
    # 返回 题数 除 (题数 减 1) 乘 (1 减 (正确率 乘 错误率) 求和 除 方差)
    # 问题: "求和" 是关键字，不应出现在表达式中
    # 修复: 参数名改为 p_求和，引用改为 p_求和
    old_line = "返回 题数 除 (题数 减 1) 乘 (1 减 (正确率 乘 错误率) 求和 除 方差)"
    # 注意：参数名 "求和" 也要改为 "p_求和"
    old_params = "段落 KR20 接收 输入, 题数, 正确率, 错误率, 求和, 方差:"
    new_params = "段落 KR20 接收 输入, 题数, 正确率, 错误率, p_求和, 方差:"
    new_line = "返回 题数 除 (题数 减 1) 乘 (1 减 (正确率 乘 错误率) p_求和 除 方差)"

    if old_params in content:
        backup_file(f)
        new_content = content.replace(old_params, new_params)
        new_content = new_content.replace(old_line, new_line)
        safe_write(f, new_content)
        stats["pattern7_kr20_fixed"] += 1
        log("教育KR20.light 求和关键字修复完成")
    else:
        print("  [跳过] 未找到需要修复的参数行（可能已修复）")


# ========== 主函数 ==========

def main():
    print("=" * 60)
    print("光明积木库 ParseError 批量修复脚本")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"工作目录: {BASE_DIR}")
    print("=" * 60)

    # 创建备份目录
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n备份目录: {BACKUP_DIR}")

    # 执行各模式修复
    fix_pattern1()
    fix_pattern2()
    fix_pattern3()
    fix_pattern4()
    fix_pattern5()
    fix_pattern6()
    fix_pattern7()

    # 输出统计
    print("\n" + "=" * 60)
    print("修复统计")
    print("=" * 60)
    total = sum(stats.values())
    for key, val in stats.items():
        label = {
            "pattern1_decimal_renamed": "模式1-重命名（含小数→中文）",
            "pattern1_decimal_deleted": "模式1-删除（已有中文版）",
            "pattern2_percent_renamed": "模式2-%→百分比",
            "pattern3_跳出值_fixed": "模式3-p_跳出值值值→p_跳出值",
            "pattern4_operator_fixed": "模式4-大于 等于→大于等于",
            "pattern5_param_space_fixed": "模式5-参数空格→下划线",
            "pattern6_rmsprop_fixed": "模式6-RMSprop括号",
            "pattern7_kr20_fixed": "模式7-KR20求和关键字",
        }.get(key, key)
        print(f"  {label}: {val}")
    print(f"  {'='*30}")
    print(f"  总计修复: {total}")
    print(f"结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()