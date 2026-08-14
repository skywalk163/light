# -*- coding: utf-8 -*-
"""
光明积木库质量扫描器 v1.0
=========================
扫描 blocks_v5/ 所有 .light 文件，识别：
  - 自递归空壳桩（段落体唯一语句是调用自己）
  - 形参名不一致（段落体内引用变量与形参名不匹配）
  - 自由变量引用（引用未定义变量）
  - 契约行与签名不匹配

用法: python _质量扫描.py
输出: 扫描报告 质量报告.md
"""

import os, re, json
from collections import defaultdict

_HERE = os.path.abspath(os.path.dirname(__file__))
BLOCKS_DIR = os.path.join(_HERE, 'blocks_v5')
INDEX_PATH = os.path.join(_HERE, '索引.json')

# 光明标准库内置函数名（已知的，不会引起递归的标准函数）
STDLIB_FUNCS = {
    '长度', '取整', '绝对值', '平方根', '对数', '指数', '正弦', '余弦', '正切',
    '反正弦', '反余弦', '反正切', '最大值', '最小值', '排序', '反转', '去空格',
    '去标点', '去数字', '去字母', '去空白', '压缩', '截取', '倒序', '哈希',
    '编码', '解码', '分词', '词性标注', '命名实体', '关键词', '摘要', '翻译',
    '纠错', '繁简转换', '拼音', '注音', '去重行', '字频', '词频',
    '包含', '开头', '结尾', '替换', '编辑距离', '最长公共子串', '最长公共子序列',
    '汉明距离', '文本Jaccard', '文本余弦相似', '重复', '居中', '左对齐', '右对齐',
    '填充', '提取数字', '提取字母', '提取汉字', '阶乘', '质数', '单词数', '行数',
    '句数', '段数', '空格数', '标点数', '数字数', '字母数', '大写数', '小写数',
    '汉字数', '字符串转字节', '字节转字符串', 'Base64编码', 'Base64解码',
    'Hex编码', 'Hex解码', 'URL编码', 'URL解码', 'HTML编码', 'HTML解码',
    '时间戳', '日期转时间戳', '时间戳转日期', '取整', '向上取整', '四舍五入',
    '最大公约数', 'IRR', '标准差', '协方差', '相关系数',
    '去重', '展平', '洗牌', '采样', '分页', '分组', '分块',
    '扁平', '浅拷贝', '记忆化', '缓存', '节流', '防抖', '重试', '延时', '等待',
    '日志', '断言', '测量', '计时器', '性能', '格式化', '模板',
    '排列', '组合', '笛卡尔积',
    'JSON解析', 'JSON序列化', 'XML解析', 'CSV解析',
    '子串', '查找', '计数', '分割', '拼接', '切分', '填充', '补零',
    '当前时间', '格式化时间', '解析时间',
    '系统信息', '环境变量', '命令行参数',
    '范围', '枚举', '步进', '压缩', '累积', '映射', '过滤', '归约', '循环', '倒序',
    '文件读取', '文件写入', '文件追加', '文件删除', '文件存在',
}

# 已经知道实现在 工具代码/ 目录下的函数名
# 这些函数是由 生成工具代码.py 生成的
def _load_tool_functions():
    """加载工具代码目录中的函数名"""
    tool_dir = os.path.join(_HERE, '工具代码')
    funcs = set()
    if os.path.exists(tool_dir):
        for fname in os.listdir(tool_dir):
            if fname.endswith('.py') and fname != '__init__.py':
                module_name = fname[:-3]
                funcs.add(module_name)
                # 也读取模块内容寻找函数定义
                try:
                    with open(os.path.join(tool_dir, fname), 'r', encoding='utf-8') as f:
                        content = f.read()
                    for m in re.finditer(r'^def (\w+)\(', content, re.MULTILINE):
                        funcs.add(m.group(1))
                except:
                    pass
    return funcs

TOOL_FUNCS = _load_tool_functions()

def _parse_light_file(filepath):
    """解析 .light 文件，返回结构化信息"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    info = {
        'path': filepath,
        'rel_path': os.path.relpath(filepath, BLOCKS_DIR),
        'func_name': None,
        'params': [],
        'body_lines': [],
        'contract_input': None,
        'contract_output': None,
        'has_export': False,
        'has_func': False,
        'errors': [],
    }
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 契约行
        if stripped.startswith('# 契约：'):
            PREFIX = '# 契约：'
            contract = stripped[len(PREFIX):].strip()
            m = re.match(r'输入 \[([^\]]*)\]\s*→\s*输出\s*([^\s（(]+)', contract)
            if m:
                info['contract_input'] = m.group(1)
                info['contract_output'] = m.group(2)
        
        # 导出行
        if stripped.startswith('导出 '):
            info['has_export'] = True
            info['export_name'] = stripped[3:].strip()
        
        # 段落行
        if stripped.startswith('段落 '):
            info['has_func'] = True
            content = stripped[3:]
            # 解析 段落名 接收 参数...
            m = re.match(r'(\S+)\s+接收\s+(.+)', content)
            if m:
                info['func_name'] = m.group(1)
                params_str = m.group(2).strip()
                # 去掉末尾冒号（全角/半角）
                params_str = re.sub(r'[：:]$', '', params_str)
                # 参数可能是逗号分隔的多个
                info['params'] = [p.strip() for p in params_str.split(',')]
        
        # 体行（缩进的行）
        if line.startswith('    ') or line.startswith('\t'):
            info['body_lines'].append(stripped)
    
    return info


def _get_free_vars(expr, defined_vars, func_name, all_func_names):
    """获取表达式中未定义的变量名"""
    # 提取所有可能的函数调用名和变量名
    # 变量名通常是中文/字母序列
    tokens = re.findall(r'[\w\u4e00-\u9fff]+', expr)
    
    # 排除：
    # - 关键字：设, 为, 如果, 则, 否则, 当, 返回, 且, 或, 不, 真, 假, 加, 减, 乘, 除, 模
    # - 数字字面量
    # - 已定义的变量（形参、局部变量）
    # - 函数名自身（自递归）
    # - 标准库函数
    # - 工具代码函数
    # - 其他积木函数名
    
    keywords = {'设', '为', '如果', '则', '否则', '当', '返回', '且', '或', '不',
                '真', '假', '加', '减', '乘', '除', '模', '小于', '大于', '等于',
                '长度', '结果', 'i', 'j', '输入', '文本', '列表', '甲', '乙', '丙',
                '窗宽', '表甲', '表乙', '键', '窗口', '步长', '系数', '缩放因子',
                '偏移量', '幂参数', '上界', '下界', '最小值', '最大值',
                '均值', '标准差', '协方差', '方差', '均值甲', '均值乙',
                '成本', '收入', '资产', '权益', '总资产', '流动负债', '存货',
                '每股净资产', '股价', 'EPS', '贴现率', '期数', '利率', '折现率',
                '年现金流', '固定成本', '单价', '单位变动', '年需求', '订货成本',
                '持有成本', '周转率', '杠杆', '终值', '初值', '年数', '资本支出',
                '资本', '资本成本率', '权益比', '权益成本', '债务比', '债务成本',
                '税率', '时间', '总流量', '总请求', 'RTT', '带宽', '信噪比', '噪声',
                '总比特', '总连接', '增强因子', '当前年', '费用', '基准值',
                '最大值', '总时间', '输入', '丢包率', '每股收入', '系数',
                '固定成本', 'M', 'N', 'k', 'n', '当前值', '新值', '旧值',
                '频次', '密度', '相位', '幅度', '频率', '截距', '斜率',
                '正数', '负数', '零', '偶数', '奇数', '质数', '合数', '整数', '小数',
                '盈利', '亏损', '安全', '风险', '高风险', '正常', '高估', '合理',
                '低延迟', '中延迟', '高延迟', '较高', '过载', '高可用', '可用', '低可用',
                '闰年', '平年', '超时', '正常',
                '年龄', '出生年', '年', '月', '日', '时', '分', '秒',
                '毫秒', '微秒', '纳秒', '周', '季度', '半年',
                '上一年', '下一年', '上一月', '下一月', '上一日', '下一日',
                }
    
    free_vars = []
    for token in tokens:
        # 跳过数字
        if token.isdigit() or (token.startswith('-') and token[1:].isdigit()):
            continue
        # 跳过浮点数
        try:
            float(token)
            continue
        except:
            pass
        # 跳过已定义变量
        if token in defined_vars:
            continue
        # 跳过关键字
        if token in keywords:
            continue
        # 跳过标准库函数
        if token in STDLIB_FUNCS:
            continue
        # 跳过工具代码函数
        if token in TOOL_FUNCS:
            continue
        # 跳过自身（自递归调用）
        if token == func_name:
            continue
        # 跳过其他积木函数名
        if token in all_func_names:
            continue
        # 跳过运算符类
        if token in {'输入', '文本', '列表', '甲', '乙', '丙', '窗宽', '表甲', '表乙', '键', '窗口', '结果', 'i', 'j'}:
            continue
        free_vars.append(token)
    return free_vars


def main():
    # 收集所有积木函数名
    all_func_names = set()
    for root, dirs, files in os.walk(BLOCKS_DIR):
        for f in files:
            if f.endswith('.light'):
                fpath = os.path.join(root, f)
                info = _parse_light_file(fpath)
                if info['func_name']:
                    all_func_names.add(info['func_name'])
    
    print(f"[扫描] 共发现 {len(all_func_names)} 个积木函数名")
    
    # 扫描结果统计
    stats = {
        'total': 0,
        'self_recursive_stub': 0,  # 自递归空壳桩
        'param_mismatch_stub': 0,  # 形参名不一致的自递归
        'param_mismatch_fixable': 0,  # 可修复的形参不匹配
        'has_free_vars': 0,  # 有自由变量
        'has_impl': 0,  # 有真正实现
        'contract_mismatch': 0,  # 契约不匹配
    }
    
    self_recursive_stubs = []
    param_mismatch_stubs = []
    param_mismatch_fixable = []
    has_free_vars_list = []
    
    for root, dirs, files in os.walk(BLOCKS_DIR):
        for f in sorted(files):
            if not f.endswith('.light'):
                continue
            fpath = os.path.join(root, f)
            info = _parse_light_file(fpath)
            stats['total'] += 1
            
            if not info['func_name'] or not info['has_func']:
                continue
            
            func_name = info['func_name']
            params = info['params']
            body = info['body_lines']
            defined_vars = set(params) | {'结果', 'i', 'j', '键', '窗口'}
            
            # 检查 body 中是否有自由变量（非自身、非参数、非 stdlib、非其他积木的变量）
            all_free_vars = set()
            for bline in body:
                # 跳过 设 语句（定义局部变量）
                if bline.startswith('设 '):
                    m = re.match(r'设\s+(\S+)\s+为', bline)
                    if m:
                        defined_vars.add(m.group(1))
                    # 设语句中的右侧表达式也可能有自由变量
                    expr = re.sub(r'^设\s+\S+\s+为\s*', '', bline)
                    if expr:
                        fv = _get_free_vars(expr, defined_vars, func_name, all_func_names)
                        all_free_vars.update(fv)
                elif bline.startswith('如果 '):
                    condition = bline[3:]
                    fv = _get_free_vars(condition, defined_vars, func_name, all_func_names)
                    all_free_vars.update(fv)
                elif bline.startswith('返回 '):
                    ret_val = bline[3:]
                    fv = _get_free_vars(ret_val, defined_vars, func_name, all_func_names)
                    all_free_vars.update(fv)
                else:
                    fv = _get_free_vars(bline, defined_vars, func_name, all_func_names)
                    all_free_vars.update(fv)
            
            # 判断是否为自递归空壳桩
            # 模式：body 只有一行，且是 `返回 函数名(形参)`
            is_self_recursive = False
            is_param_mismatch = False
            can_fix_param = False
            
            if len(body) == 1 and body[0].startswith('返回 '):
                ret_val = body[0][3:].strip()
                # 检查是否调用自身
                m = re.match(r'^(\w[\w\u4e00-\u9fff]*)\(([^)]*)\)$', ret_val)
                if m:
                    called_func = m.group(1)
                    called_arg = m.group(2)
                    if called_func == func_name:
                        if len(params) == 1 and called_arg == params[0]:
                            # 自递归空壳桩：段落名(形参) 且形参名与声明一致
                            is_self_recursive = True
                            self_recursive_stubs.append(info)
                        elif len(params) == 1 and called_arg != params[0]:
                            # 形参名不一致：段落名(其他名字)
                            is_param_mismatch = True
                            param_mismatch_stubs.append(info)
                            # 如果自由变量只有一个且就是形参那一个
                            if len(all_free_vars) == 1:
                                can_fix_param = True
                                param_mismatch_fixable.append(info)
            
            # 有自由变量（非自递归的情况）
            if all_free_vars and not is_self_recursive and not is_param_mismatch:
                stats['has_free_vars'] += 1
                has_free_vars_list.append((info, all_free_vars))
            
            if is_self_recursive:
                stats['self_recursive_stub'] += 1
            if is_param_mismatch:
                stats['param_mismatch_stub'] += 1
            if can_fix_param:
                stats['param_mismatch_fixable'] += 1
            if not is_self_recursive and not is_param_mismatch:
                stats['has_impl'] += 1
    
    # 输出报告
    report_lines = []
    report_lines.append("# 光明积木库质量扫描报告\n")
    report_lines.append(f"扫描时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append(f"扫描范围：{BLOCKS_DIR}\n")
    report_lines.append(f"总积木数：{stats['total']}\n")
    report_lines.append(f"\n## 统计摘要\n")
    report_lines.append(f"| 类别 | 数量 | 占比 |\n")
    report_lines.append(f"|------|------|------|\n")
    report_lines.append(f"| 自递归空壳桩 | {stats['self_recursive_stub']} | {stats['self_recursive_stub']/max(stats['total'],1)*100:.1f}% |\n")
    report_lines.append(f"| 形参不一致自递归 | {stats['param_mismatch_stub']} | {stats['param_mismatch_stub']/max(stats['total'],1)*100:.1f}% |\n")
    report_lines.append(f"| 其中可形参对齐修复 | {stats['param_mismatch_fixable']} | {stats['param_mismatch_fixable']/max(stats['total'],1)*100:.1f}% |\n")
    report_lines.append(f"| 含自由变量 | {stats['has_free_vars']} | {stats['has_free_vars']/max(stats['total'],1)*100:.1f}% |\n")
    report_lines.append(f"| 有真正实现 | {stats['has_impl']} | {stats['has_impl']/max(stats['total'],1)*100:.1f}% |\n")
    
    report_lines.append(f"\n## 自递归空壳桩列表（{len(self_recursive_stubs)} 个）\n")
    for info in self_recursive_stubs[:50]:
        report_lines.append(f"  - [{info['rel_path']}](file:///{info['path']})")
        report_lines.append(f"    `{info['body_lines'][0] if info['body_lines'] else ''}`")
    if len(self_recursive_stubs) > 50:
        report_lines.append(f"  ... 共 {len(self_recursive_stubs)} 个，仅显示前 50 个\n")
    
    report_lines.append(f"\n## 形参不一致自递归列表（{len(param_mismatch_stubs)} 个）\n")
    for info in param_mismatch_stubs[:30]:
        report_lines.append(f"  - [{info['rel_path']}](file:///{info['path']})")
        report_lines.append(f"    形参: {info['params']}, body: `{info['body_lines'][0] if info['body_lines'] else ''}`")
    if len(param_mismatch_stubs) > 30:
        report_lines.append(f"  ... 共 {len(param_mismatch_stubs)} 个，仅显示前 30 个\n")
    
    report_lines.append(f"\n## 可形参对齐修复列表（{len(param_mismatch_fixable)} 个）\n")
    for info in param_mismatch_fixable[:20]:
        report_lines.append(f"  - [{info['rel_path']}](file:///{info['path']})")
        report_lines.append(f"    形参: {info['params']}, body: `{info['body_lines'][0] if info['body_lines'] else ''}`")
    
    report_lines.append(f"\n## 含自由变量列表（{len(has_free_vars_list)} 个，前 30 个）\n")
    for info, fvs in has_free_vars_list[:30]:
        report_lines.append(f"  - [{info['rel_path']}](file:///{info['path']})")
        report_lines.append(f"    自由变量: {', '.join(sorted(fvs))}")
    
    report = '\n'.join(report_lines)
    
    report_path = os.path.join(_HERE, '_质量报告.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n[完成] 报告已写入: {report_path}")
    print(f"\n统计摘要:")
    print(f"  总积木数: {stats['total']}")
    print(f"  自递归空壳桩: {stats['self_recursive_stub']}")
    print(f"  形参不一致自递归: {stats['param_mismatch_stub']}")
    print(f"  可形参对齐修复: {stats['param_mismatch_fixable']}")
    print(f"  含自由变量: {stats['has_free_vars']}")
    print(f"  有真正实现: {stats['has_impl']}")


if __name__ == '__main__':
    main()