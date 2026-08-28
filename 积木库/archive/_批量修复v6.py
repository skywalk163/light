# -*- coding: utf-8 -*-
"""
批量修复v6 - 修复 blocks_v5 目录下的 .light 文件
涵盖修复1~修复11，不包含修复4（柯里化.light 需修改 _预跑.py）
"""

import os
import re
import shutil

BASE = os.path.join(os.path.dirname(__file__), 'blocks_v5')

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def log(msg):
    print(f"  [INFO] {msg}")

# ============================================================
# 修复1：空参数列表 + 使用列表[i]
# 文件：函数均值.light, 函数平滑.light, 函数滤波.light, 函数高通.light
# 修复：将 `接收 ：` 改为 `接收 列表：`
# ============================================================
def fix_1():
    print("\n=== 修复1：空参数列表 ===")
    files = [
        '函数\\函数均值.light',
        '函数\\函数平滑.light',
        '函数\\函数滤波.light',
        '函数\\函数高通.light',
    ]
    for rel in files:
        path = os.path.join(BASE, rel)
        if not os.path.exists(path):
            log(f"文件不存在，跳过: {rel}")
            continue
        content = read_file(path)
        # 匹配 `接收 ：` 或 `接收  ：` 等
        new_content = re.sub(r'^(段落\s+\S+\s+接收)\s*：', r'\1 列表：', content, flags=re.MULTILINE)
        if new_content != content:
            write_file(path, new_content)
            log(f"已修复: {rel}")
        else:
            log(f"无需修改: {rel}")

# ============================================================
# 修复2：参数列表含数字
# 移除数字参数，只保留中文/英文参数名
# ============================================================
def fix_2():
    print("\n=== 修复2：移除数字参数 ===")
    files = [
        # 单位
        '单位\\兆欧转欧姆.light', '单位\\兆赫转赫兹.light',
        '单位\\光年转千米.light', '单位\\千瓦时转焦耳.light',
        '单位\\千米转光年.light', '单位\\吉赫转赫兹.light',
        '单位\\居里转贝克勒尔.light', '单位\\微摩尔转摩尔.light',
        '单位\\微法转法拉.light', '单位\\摩尔转微摩尔.light',
        '单位\\欧姆转兆欧.light', '单位\\法拉转微法.light',
        '单位\\法拉转皮法.light', '单位\\焦耳转千瓦时.light',
        '单位\\焦耳转电子伏.light', '单位\\电子伏转焦耳.light',
        '单位\\皮法转法拉.light', '单位\\贝克勒尔转居里.light',
        '单位\\赫兹转兆赫.light', '单位\\赫兹转吉赫.light',
        # 化学
        '化学\\化学位移.light', '化学\\原子半径.light',
        '化学\\跃迁能量.light', '化学\\过渡态理论.light',
        '化学\\配位数化学.light',
        # 地理
        '地理\\方位角.light',
        # 天文
        '天文\\AU转公里.light', '天文\\主序寿命.light', '天文\\光年.light',
    ]
    # 匹配数字参数：类似 `1e6`, `461e12`, `1e`, `63e`, `38e`, `496e8`, `242e18`, `6e6`, `7e10`, `1e12`, `1e9`, `1e-10`, `3e8` 等
    num_pattern = re.compile(r'^[\d.]+e?-?[\d]*$', re.IGNORECASE)
    
    for rel in files:
        path = os.path.join(BASE, rel)
        if not os.path.exists(path):
            log(f"文件不存在，跳过: {rel}")
            continue
        content = read_file(path)
        lines = content.split('\n')
        changed = False
        new_lines = []
        for line in lines:
            # 匹配段落定义行: `段落 XXX 接收 ...：`
            m = re.match(r'^(段落\s+\S+\s+接收\s+)(.*?)：$', line)
            if m:
                prefix = m.group(1)
                params_str = m.group(2)
                # 分割参数
                params = [p.strip() for p in params_str.split(',')]
                # 过滤掉数字参数
                new_params = [p for p in params if not num_pattern.match(p)]
                if len(new_params) != len(params):
                    changed = True
                    new_line = prefix + ', '.join(new_params) + '：'
                    new_lines.append(new_line)
                    log(f"{rel}: 移除数字参数 [{', '.join(set(params) - set(new_params))}]")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        if changed:
            write_file(path, '\n'.join(new_lines))
            log(f"已修复: {rel}")
        else:
            log(f"无需修改: {rel}")

# ============================================================
# 修复3：`p_二阶` 未重命名问题
# 文件：函数泰勒二阶.light
# ============================================================
def fix_3():
    print("\n=== 修复3：函数泰勒二阶 ===")
    rel = '函数\\函数泰勒二阶.light'
    path = os.path.join(BASE, rel)
    if not os.path.exists(path):
        log(f"文件不存在: {rel}")
        return
    content = read_file(path)
    # 参数: `二阶` → `cb_二阶`
    content = content.replace('接收 cb_梯度, cb_func, 甲, 乙, 二阶：', '接收 cb_梯度, cb_func, 甲, 乙, cb_二阶：')
    # 体中 `p_二阶` → `cb_二阶`
    content = content.replace('p_二阶', 'cb_二阶')
    write_file(path, content)
    log(f"已修复: {rel}")

# ============================================================
# 修复4：柯里化.light
# 注意：`cb_func(甲)(乙)` 语法解析器不支持。
# 当前方案：跳过此文件，需要修改 _预跑.py 注入特殊处理。
# ============================================================
def fix_4():
    print("\n=== 修复4：柯里化.light（跳过） ===")
    print("  [SKIP] 柯里化.light 的 `cb_func(甲)(乙)` 语法无法通过修改 .light 文件解决。")
    print("  [SKIP] 需要修改 _预跑.py，将柯里化作为特殊积木处理。")

# ============================================================
# 修复5：医学文件含连字符
# 重命名文件 + 替换内容中的 `-` 为 `_`
# ============================================================
def fix_5():
    print("\n=== 修复5：医学文件连字符 ===")
    # (原文件名, 新文件名, 需替换的导出名/段落名中的模式)
    # 对于 FEV1_FVC.light，文件名已含 `_`，但内容中导出名含 `/`
    replacements = [
        ('A-a梯度.light', 'A_a梯度.light', 'A-cb_a梯度', 'A_cb_a梯度'),
        ('CKD-EPI.light', 'CKD_EPI.light', 'CKD-EPI', 'CKD_EPI'),
        ('CURB-65.light', 'CURB_65.light', 'CURB-65', 'CURB_65'),
        ('Child-Pugh.light', 'Child_Pugh.light', 'Child-Pugh', 'Child_Pugh'),
        ('FEV1_FVC.light', 'FEV1_FVC.light', 'FEV1/FVC', 'FEV1_FVC'),
        ('HOMA-IR.light', 'HOMA_IR.light', 'HOMA-IR', 'HOMA_IR'),
        ('HOMA-β.light', 'HOMA_beta.light', 'HOMA-beta', 'HOMA_beta'),
        ('Harris-Benedict.light', 'Harris_Benedict.light', 'Harris-Benedict', 'Harris_Benedict'),
        ('MELD-Na.light', 'MELD_Na.light', 'MELD-Na', 'MELD_Na'),
    ]
    med_dir = os.path.join(BASE, '医学')
    for old_name, new_name, old_str, new_str in replacements:
        old_path = os.path.join(med_dir, old_name)
        new_path = os.path.join(med_dir, new_name)
        if not os.path.exists(old_path):
            log(f"文件不存在: {old_name}")
            continue
        content = read_file(old_path)
        # 替换内容中的导出名/段落名
        new_content = content.replace(old_str, new_str)
        if old_name == new_name:
            # 只需写回，不重命名
            if new_content != content:
                write_file(old_path, new_content)
                log(f"已修复内容: {old_name}")
            else:
                log(f"无需修改: {old_name}")
        else:
            # 需要重命名
            write_file(new_path, new_content)
            os.remove(old_path)
            log(f"已重命名: {old_name} → {new_name}")

# ============================================================
# 修复6：函数共轭.light 参数名含"方向"关键字
# ============================================================
def fix_6():
    print("\n=== 修复6：函数共轭 ===")
    rel = '函数\\函数共轭.light'
    path = os.path.join(BASE, rel)
    if not os.path.exists(path):
        log(f"文件不存在: {rel}")
        return
    content = read_file(path)
    # 参数: `共轭方向` → `p_共轭方向`
    content = content.replace('共轭方向', 'p_共轭方向')
    write_file(path, content)
    log(f"已修复: {rel}")

# ============================================================
# 修复7：函数特征.light 参数名含"值"关键字
# ============================================================
def fix_7():
    print("\n=== 修复7：函数特征 ===")
    rel = '函数\\函数特征.light'
    path = os.path.join(BASE, rel)
    if not os.path.exists(path):
        log(f"文件不存在: {rel}")
        return
    content = read_file(path)
    # 当前: `接收 输入, 特征值：` 体中 `列表[i] 乘 特征值`
    # 修复: 参数 `特征值` → `p_特征值`，体中 `特征值` → `p_特征值`
    # 注意：要同时添加 `列表` 参数（修复9）
    content = content.replace(
        '段落 函数特征 接收 输入, 特征值：',
        '段落 函数特征 接收 输入, p_特征值, 列表：'
    )
    # 体中 `特征值` → `p_特征值`（注意不要替换刚写入的 `p_特征值`）
    # 只替换非 `p_` 前缀的 `特征值`
    content = content.replace(' 乘 特征值', ' 乘 p_特征值')
    write_file(path, content)
    log(f"已修复: {rel}")

# ============================================================
# 修复8：函数量化.light 参数名含"步长"关键字
# ============================================================
def fix_8():
    print("\n=== 修复8：函数量化 ===")
    rel = '函数\\函数量化.light'
    path = os.path.join(BASE, rel)
    if not os.path.exists(path):
        log(f"文件不存在: {rel}")
        return
    content = read_file(path)
    # 当前: `接收 输入, 量化步长：` 体中 `整数(列表[i] 除 量化步长) 乘 量化步长`
    # 修复: 参数 `量化步长` → `p_量化步长`，体中对应修改
    # 同时添加 `列表` 参数（修复9）
    content = content.replace(
        '段落 函数量化 接收 输入, 量化步长：',
        '段落 函数量化 接收 输入, p_量化步长, 列表：'
    )
    # 体中 `量化步长` → `p_量化步长`（注意顺序）
    content = content.replace(' 除 量化步长', ' 除 p_量化步长')
    content = content.replace(' 乘 量化步长', ' 乘 p_量化步长')
    write_file(path, content)
    log(f"已修复: {rel}")

# ============================================================
# 修复9：`列表` 作为参数缺失
# 文件：函数互相关.light, 函数卷积.light, 函数带通.light, 函数带阻.light,
#       函数相关.light, 函数非局部.light, 函数高斯.light, 函数标准化.light,
#       函数字典.light, 函数特征.light, 函数量化.light
# 注意：函数互相关.light 实际使用 `甲[i]` 而非 `列表[i]`，排除
#       函数特征.light 和 函数量化.light 已在修复7/8中处理
# ============================================================
def fix_9():
    print("\n=== 修复9：添加列表参数 ===")
    files = [
        ('函数卷积.light', '接收 输入, 核, 核长：', '接收 输入, 核, 核长, 列表：'),
        ('函数带通.light', '接收 输入, 低通：', '接收 输入, 低通, 列表：'),
        ('函数带阻.light', '接收 输入, 带通：', '接收 输入, 带通, 列表：'),
        ('函数相关.light', '接收 输入, 核：', '接收 输入, 核, 列表：'),
        ('函数非局部.light', '接收 输入, 距离, 方差：', '接收 输入, 距离, 方差, 列表：'),
        ('函数高斯.light', '接收 输入, 方差：', '接收 输入, 方差, 列表：'),
        ('函数标准化.light', '接收 输入：', '接收 输入, 列表：'),
        ('函数字典.light', '接收 输入：', '接收 输入, 列表：'),
    ]
    func_dir = os.path.join(BASE, '函数')
    for fname, old_sig, new_sig in files:
        path = os.path.join(func_dir, fname)
        if not os.path.exists(path):
            log(f"文件不存在: {fname}")
            continue
        content = read_file(path)
        if old_sig in content:
            content = content.replace(old_sig, new_sig)
            write_file(path, content)
            log(f"已修复: {fname}")
        else:
            log(f"签名不匹配: {fname} (期望: {old_sig})")

# ============================================================
# 修复10：函数双边.light 参数名冲突
# `方差` 在体中用作函数调用但实际上是参数
# ============================================================
def fix_10():
    print("\n=== 修复10：函数双边 ===")
    rel = '函数\\函数双边.light'
    path = os.path.join(BASE, rel)
    if not os.path.exists(path):
        log(f"文件不存在: {rel}")
        return
    content = read_file(path)
    # 当前: `接收 方差：` 体中 `列表[i] 乘 ... 除 (2 乘 方差)`
    # 修复: `方差` → `cb_方差`，同时添加 `列表` 参数
    content = content.replace(
        '段落 函数双边 接收 方差：',
        '段落 函数双边 接收 cb_方差, 列表：'
    )
    # 体中 `方差` → `cb_方差`（注意只替换非 `cb_` 前缀的）
    content = content.replace(' 乘 方差)', ' 乘 cb_方差)')
    write_file(path, content)
    log(f"已修复: {rel}")

# ============================================================
# 修复11：函数RMSprop.light 缺失 `累积` 变量
# ============================================================
def fix_11():
    print("\n=== 修复11：函数RMSprop ===")
    rel = '函数\\函数RMSprop.light'
    path = os.path.join(BASE, rel)
    if not os.path.exists(path):
        log(f"文件不存在: {rel}")
        return
    content = read_file(path)
    # 当前: `接收 学习率, 小量, cb_梯度, 衰减, 输入：`
    # 体中用 `累积` 但未声明
    # 修复: 添加 `累积` 参数
    content = content.replace(
        '接收 学习率, 小量, cb_梯度, 衰减, 输入：',
        '接收 学习率, 小量, cb_梯度, 衰减, 累积, 输入：'
    )
    write_file(path, content)
    log(f"已修复: {rel}")

# ============================================================
# 主函数
# ============================================================
def main():
    print("=" * 60)
    print("批量修复v6 - 开始修复 blocks_v5 目录下的 .light 文件")
    print("=" * 60)
    
    fix_1()
    fix_2()
    fix_3()
    fix_4()
    fix_5()
    fix_6()
    fix_7()
    fix_8()
    fix_9()
    fix_10()
    fix_11()
    
    print("\n" + "=" * 60)
    print("批量修复v6 - 完成！")
    print("注意：修复4（柯里化.light）已跳过，需要修改 _预跑.py")
    print("=" * 60)

if __name__ == '__main__':
    main()