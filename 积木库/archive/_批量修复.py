# -*- coding: utf-8 -*-
"""
光明积木库批量修复脚本 v1.0
===========================
修复 blocks_v5/ 目录中的积木文件：

P0: 标记自递归空壳桩（# 状态：签名占位，无实现）
P1: 形参名对齐修复（体内变量名修正为形参名）
P2: 更新索引.json（补齐描述、输入、输出、实现、依赖字段）

用法: python _批量修复.py
"""

import os, re, json, glob
from collections import defaultdict

_HERE = os.path.abspath(os.path.dirname(__file__))
BLOCKS_DIR = os.path.join(_HERE, 'blocks_v5')
INDEX_PATH = os.path.join(_HERE, '索引.json')

# 光明标准库内置函数名
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
    '时间戳', '日期转时间戳', '时间戳转日期', '向上取整', '四舍五入',
    '最大公约数', 'IRR', '标准差', '协方差', '相关系数',
    '去重', '展平', '洗牌', '采样', '分页', '分组', '分块',
    '扁平', '浅拷贝', '记忆化', '缓存', '节流', '防抖', '重试', '延时', '等待',
    '日志', '断言', '测量', '计时器', '性能', '格式化', '模板',
    '排列', '组合', '笛卡尔积',
    'JSON解析', 'JSON序列化', 'XML解析', 'CSV解析',
    '子串', '查找', '计数', '分割', '拼接', '切分', '填充', '补零',
    '当前时间', '格式化时间', '解析时间',
    '系统信息', '环境变量', '命令行参数',
    '范围', '枚举', '步进', '累积', '映射', '过滤', '归约', '循环',
    '文件读取', '文件写入', '文件追加', '文件删除', '文件存在',
    '平方', '立方', '四次方', '相反数', '倒数', '符号', '取模', '取反',
    '字节', '字符串', '字节数组', '数组', '字典', '集合', '元组', '列表',
    '整数', '小数', '文本', '逻辑', '颜色', '日期', '时间',
    '误差', '容差', '精度', '迭代', '次数', '步长', '缩放', '因子',
    '生成', '创建', '打开', '关闭', '读', '写', '追加', '删除', '存在',
    '获取', '设置', '调用', '执行', '转换', '解析', '序列化', '反序列化',
    '检查', '验证', '判断', '比较', '计算', '估计', '预测', '拟合',
    '空', '无', '缺省', '默认', '标准', '基准', '参考', '目标',
    '甲', '乙', '丙', '丁', '列表', '文本', '输入', '输出', '结果',
    '初始', '最终', '当前', '历史', '累计', '剩余', '已用', '总',
    '上', '下', '左', '右', '中', '前', '后', '内', '外', '边', '顶', '底',
    '子', '父', '根', '叶', '节', '点', '边', '图', '树', '网',
    '值', '量', '数', '率', '比', '度', '级', '型', '类', '种',
    '最小', '最大', '平均', '中位', '标准', '归一', '正则', '原始',
    '年', '月', '日', '时', '分', '秒', '毫秒', '微秒', '纳秒', '周',
    '季度', '半年', '闰年', '工作日', '自然日', '节假日', '时区', 'UTC',
    '年龄', '时长', '间隔', '周期', '频率', '速率', '速度', '加速度',
    '年化', '月化', '日化', '时化',
    '奇偶', '正负', '整数', '零', '非', '偶数', '奇数', '正数', '负数', '质数', '合数',
    '盈利', '亏损', '安全', '风险', '高风险', '正常', '高估', '合理',
    '低延迟', '中延迟', '高延迟', '较高', '过载', '高可用', '可用', '低可用',
    '闰年', '平年', '超时', '正常',
    '输入', '文本', '列表', '甲', '乙', '丙', '窗宽', '表甲', '表乙', '键', '窗口',
    '结果', 'i', 'j', 'k', 'n', 'm', 'x', 'y', 'z',
    '真', '假', '和', '差', '积', '商', '余', '模', '幂', '根',
    '增', '减', '乘', '除', '加', '减', '乘', '除', '模',
    '且', '或', '不', '如果', '则', '否则', '当', '返回', '设', '为',
    '长', '宽', '高', '半径', '直径', '面积', '体积', '周长', '角度',
    '摄氏度', '华氏度', '开尔文',
    '价格', '成本', '收入', '利润', '税率', '利率', '汇率', '费率',
    '本金', '利息', '本息', '现值', '终值', '年金', '贴现', '折现',
    '资产', '负债', '权益', '现金流', '折旧', '摊销',
    '收入', '成本', '利润', '毛利', '净利', '营收', '净收',
    '流量', '带宽', '延迟', '吞吐', '丢包', '抖动', '并发', '连接',
    '请求', '响应', '超时', '重试', '错误', '成功', '失败',
    '编码', '解码', '加密', '解密', '哈希', '签名', '校验',
    'Base64', 'Hex', 'MD5', 'SHA1', 'SHA256', 'SHA512', 'CRC',
    'ASCII', 'Unicode', 'UTF8', 'UTF16', 'GBK', 'GB2312', 'BIG5',
    'M', 'N', 'K', 'V', 'W', 'H', 'L', 'T', 'S', 'A', 'B', 'C', 'D',
    'x1', 'x2', 'y1', 'y2', 'z1', 'z2',
    'count', 'sum', 'avg', 'min', 'max', 'idx', 'index', 'key', 'val', 'value',
    'tmp', 'temp', 'acc', 'total', 'len', 'size', 'pos', 'prev', 'next', 'cur',
    'p', 'q', 'r', 's', 't', 'u', 'v', 'w',
}

def _load_tool_functions():
    tool_dir = os.path.join(_HERE, '工具代码')
    funcs = set()
    if os.path.exists(tool_dir):
        for fname in os.listdir(tool_dir):
            if fname.endswith('.py') and fname != '__init__.py':
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
    """解析 .light 文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    info = {
        'path': filepath,
        'rel_path': os.path.relpath(filepath, BLOCKS_DIR),
        'func_name': None,
        'params': [],
        'body_lines': [],
        'header_comments': [],
        'contract_input': None,
        'contract_output': None,
        'source_lines': lines,
        'has_export': False,
        'export_name': None,
        'has_func': False,
        'has_status_marker': False,
    }
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 头部注释
        if stripped.startswith('#') and not stripped.startswith('# 契约：') and not stripped.startswith('# 状态：'):
            info['header_comments'].append(stripped[1:].strip())
        
        # 契约行
        if stripped.startswith('# 契约：'):
            PREFIX = '# 契约：'
            contract = stripped[len(PREFIX):].strip()
            # 支持两种格式：输入 [类型] → 输出 类型 和 输入 [类型] → 输出 类型（描述）
            m = re.match(r'输入 \[([^\]]*)\]\s*→\s*输出\s*([^\s（(]+)', contract)
            if m:
                info['contract_input'] = m.group(1)
                info['contract_output'] = m.group(2)
        
        # 状态标记
        if stripped.startswith('# 状态：'):
            info['has_status_marker'] = True
        
        # 导出行
        if stripped.startswith('导出 '):
            info['has_export'] = True
            info['export_name'] = stripped[3:].strip()
        
        # 段落行
        if stripped.startswith('段落 '):
            info['has_func'] = True
            content = stripped[3:]
            m = re.match(r'(\S+)\s+接收\s+(.+)', content)
            if m:
                info['func_name'] = m.group(1)
                params_str = m.group(2).strip()
                params_str = re.sub(r'[：:]$', '', params_str)
                info['params'] = [p.strip() for p in params_str.split(',')]
        
        # 体行
        if line.startswith('    ') or line.startswith('\t'):
            info['body_lines'].append(stripped)
    
    return info


def _get_free_vars(expr, defined_vars, func_name, all_func_names):
    """获取表达式中未定义的变量名"""
    tokens = re.findall(r'[\w\u4e00-\u9fff]+', expr)
    free_vars = []
    for token in tokens:
        if token.isdigit():
            continue
        try:
            float(token)
            continue
        except:
            pass
        if token in defined_vars:
            continue
        if token in STDLIB_FUNCS:
            continue
        if token in TOOL_FUNCS:
            continue
        if token == func_name:
            continue
        if token in all_func_names:
            continue
        free_vars.append(token)
    return free_vars


def _fix_self_recursive_stub(filepath, info):
    """P0: 标记自递归空壳桩"""
    lines = info['source_lines']
    if info['has_status_marker']:
        return False  # 已标记过
    
    # 在第一个 # 注释行后插入状态标记
    # 找到第一个非空注释行之后的位置
    insert_pos = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#') and '契约' not in stripped:
            insert_pos = i + 1
        elif stripped.startswith('导出') or stripped.startswith('段落'):
            break
    
    # 在契约行前插入状态标记
    status_line = '# 状态：签名占位，无实现\n'
    lines.insert(insert_pos, status_line)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    return True


def _fix_param_mismatch(filepath, info):
    """P1: 修复形参名不一致（单参数+单自由变量）"""
    lines = info['source_lines']
    func_name = info['func_name']
    params = info['params']
    
    if len(params) != 1:
        return False
    
    param_name = params[0]
    
    # 找到 body 中调用自身的行，替换参数名
    changed = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('返回 '):
            ret_val = stripped[3:].strip()
            m = re.match(r'^(\w[\w\u4e00-\u9fff]*)\(([^)]*)\)$', ret_val)
            if m and m.group(1) == func_name:
                old_arg = m.group(2)
                if old_arg != param_name:
                    # 替换：把函数调用中的参数名改为形参名
                    old_line = line
                    new_line = line.replace(f'{func_name}({old_arg})', f'{func_name}({param_name})')
                    if new_line != old_line:
                        lines[i] = new_line
                        changed = True
    
    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    return False


def _extract_description(info):
    """从头部注释提取描述文本"""
    # 从第一个注释行提取
    for comment in info['header_comments']:
        # 跳过 "积木：" 开头的注释
        if comment.startswith('积木：') or comment.startswith('光明'):
            continue
        if comment and len(comment) > 2:
            return comment
    return ''


def _get_dependency_funcs(info, all_func_names):
    """从 body 中提取依赖的外部函数名"""
    defined_vars = set(info['params']) | {'结果', 'i', 'j', '键', '窗口'}
    body_text = ' '.join(info['body_lines'])
    tokens = re.findall(r'[\w\u4e00-\u9fff]+', body_text)
    
    deps = set()
    for token in tokens:
        if token in STDLIB_FUNCS:
            continue
        if token in TOOL_FUNCS:
            continue
        if token == info['func_name']:
            continue
        if token in all_func_names:
            deps.add(token)
            continue
        # 检查是否是函数调用（后面跟着括号）
        # 简易判断：如果 token 出现在 xxx(...) 模式中
        if re.search(rf'{re.escape(token)}\s*\(', body_text):
            if token not in defined_vars and token not in STDLIB_FUNCS:
                deps.add(token)
    
    return list(deps)


def _has_real_implementation(info):
    """判断是否有真正实现（非自递归桩）"""
    if len(info['body_lines']) == 1 and info['body_lines'][0].startswith('返回 '):
        ret_val = info['body_lines'][0][3:].strip()
        m = re.match(r'^(\w[\w\u4e00-\u9fff]*)\(([^)]*)\)$', ret_val)
        if m and m.group(1) == info['func_name']:
            return False
    return True


def main():
    # 收集所有积木函数名
    all_func_names = set()
    all_infos = []
    for root, dirs, files in os.walk(BLOCKS_DIR):
        for f in files:
            if f.endswith('.light'):
                fpath = os.path.join(root, f)
                info = _parse_light_file(fpath)
                if info['func_name']:
                    all_func_names.add(info['func_name'])
                all_infos.append(info)
    
    print(f"[信息] 共发现 {len(all_func_names)} 个积木函数名，{len(all_infos)} 个文件")
    
    # ----- P0: 标记自递归空壳桩 -----
    print("\n[P0] 标记自递归空壳桩...")
    p0_count = 0
    p0_files = []
    for info in all_infos:
        if not info['func_name'] or not info['has_func']:
            continue
        func_name = info['func_name']
        params = info['params']
        body = info['body_lines']
        
        if len(body) == 1 and body[0].startswith('返回 '):
            ret_val = body[0][3:].strip()
            m = re.match(r'^(\w[\w\u4e00-\u9fff]*)\(([^)]*)\)$', ret_val)
            if m and m.group(1) == func_name:
                if len(params) == 1 and m.group(2) == params[0]:
                    if _fix_self_recursive_stub(info['path'], info):
                        p0_count += 1
                        p0_files.append(info['rel_path'])
    
    print(f"  已标记 {p0_count} 个自递归空壳桩")
    
    # ----- P1: 形参名对齐修复 -----
    print("\n[P1] 形参名对齐修复...")
    p1_fixed = 0
    p1_skipped = 0
    p1_files = []
    
    for info in all_infos:
        if not info['func_name'] or not info['has_func']:
            continue
        func_name = info['func_name']
        params = info['params']
        body = info['body_lines']
        
        if len(params) != 1:
            continue
        
        # 检查是否是自递归调用且参数名不匹配
        is_param_mismatch = False
        if len(body) == 1 and body[0].startswith('返回 '):
            ret_val = body[0][3:].strip()
            m = re.match(r'^(\w[\w\u4e00-\u9fff]*)\(([^)]*)\)$', ret_val)
            if m and m.group(1) == func_name and m.group(2) != params[0]:
                is_param_mismatch = True
        
        if not is_param_mismatch:
            continue
        
        # 检查自由变量是否只有一个
        defined_vars = set(params) | {'结果', 'i', 'j', '键', '窗口'}
        all_free_vars = set()
        for bline in body:
            fv = _get_free_vars(bline, defined_vars, func_name, all_func_names)
            all_free_vars.update(fv)
        
        if len(all_free_vars) == 1:
            if _fix_param_mismatch(info['path'], info):
                p1_fixed += 1
                p1_files.append(info['rel_path'])
        else:
            p1_skipped += 1
    
    print(f"  已修复 {p1_fixed} 个（形参对齐）")
    print(f"  跳过 {p1_skipped} 个（自由变量>1，需人工审查）")
    
    # ----- P2: 更新索引.json -----
    print("\n[P2] 更新索引.json...")
    
    # 加载旧索引
    old_idx = {}
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
        for b in old_data.get('块', []):
            old_idx[b['名称']] = b
        print(f"  加载旧索引: {len(old_idx)} 个条目")
    
    # 重建索引
    new_blocks = []
    for info in all_infos:
        if not info['func_name']:
            continue
        
        name = info['func_name']
        # 获取领域和路径
        rel_path = info['rel_path']
        domain = rel_path.split('\\')[0] if '\\' in rel_path else rel_path.split('/')[0]
        
        # 保留旧索引中的层级
        old_entry = old_idx.get(name, {})
        level = old_entry.get('层级', 0)
        
        # 提取描述
        description = _extract_description(info)
        
        # 提取输入输出类型
        input_types = []
        output_type = {'类型': '空'}
        if info['contract_input']:
            types = [t.strip() for t in info['contract_input'].split(',')]
            for i, t in enumerate(types):
                if i < len(info['params']):
                    input_types.append({'名': info['params'][i], '类型': t})
                else:
                    input_types.append({'名': f'参数{i+1}', '类型': t})
        if info['contract_output']:
            output_type = {'类型': info['contract_output']}
        
        # 判断是否有实现
        has_impl = _has_real_implementation(info)
        
        # 获取依赖
        deps = _get_dependency_funcs(info, all_func_names)
        
        new_block = {
            '名称': name,
            '领域': domain,
            '层级': level,
            '描述': description,
            '输入': input_types,
            '输出': output_type,
            '实现': has_impl,
            '依赖': deps,
            '稳定性': 'generated',
            '路径': rel_path.replace('\\', '/'),
            '导出名': name,
        }
        new_blocks.append(new_block)
    
    # 检查是否有状态标记的积木
    for b in new_blocks:
        fpath = os.path.join(BLOCKS_DIR, b['路径'].replace('/', os.sep))
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            if '# 状态：签名占位，无实现' in content:
                b['实现'] = False
    
    # 按领域排序
    new_blocks.sort(key=lambda x: (x['领域'], x['名称']))
    
    # 统计
    total = len(new_blocks)
    implemented = sum(1 for b in new_blocks if b['实现'])
    stub_count = total - implemented
    
    index_data = {
        '版本': 'v5.2',
        '生成时间': __import__('datetime').datetime.now().strftime('%Y-%m-%d'),
        '说明': f'光明积木库索引，共 {total} 块，{len(set(b["领域"] for b in new_blocks))} 个领域。实现: {implemented}, 占位桩: {stub_count}',
        '块': new_blocks,
    }
    
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(f"  索引已更新: {total} 块")
    print(f"  实现: {implemented} ({implemented/total*100:.1f}%)")
    print(f"  占位桩: {stub_count} ({stub_count/total*100:.1f}%)")
    
    # 总结
    print(f"\n{'='*60}")
    print(f"修复总结")
    print(f"{'='*60}")
    print(f"P0: 标记自递归空壳桩: {p0_count} 个")
    print(f"P1: 形参对齐修复: {p1_fixed} 个")
    print(f"   跳过（需人工）: {p1_skipped} 个")
    print(f"P2: 索引.json 已更新")
    print(f"   总积木: {total}")
    print(f"   有实现: {implemented} ({implemented/total*100:.1f}%)")
    print(f"   占位桩: {stub_count} ({stub_count/total*100:.1f}%)")
    
    # 写入修复报告
    report_path = os.path.join(_HERE, '_批量修复报告.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 光明积木库批量修复报告\n\n")
        f.write(f"修复时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## P0: 标记自递归空壳桩 ({p0_count} 个)\n\n")
        for fp in p0_files[:50]:
            f.write(f"- {fp}\n")
        if len(p0_files) > 50:
            f.write(f"- ... 共 {len(p0_files)} 个\n")
        f.write(f"\n## P1: 形参对齐修复 ({p1_fixed} 个)\n\n")
        for fp in p1_files[:50]:
            f.write(f"- {fp}\n")
        if len(p1_files) > 50:
            f.write(f"- ... 共 {len(p1_files)} 个\n")
        f.write(f"\n## P2: 索引更新\n\n")
        f.write(f"- 总积木: {total}\n")
        f.write(f"- 有实现: {implemented} ({implemented/total*100:.1f}%)\n")
        f.write(f"- 占位桩: {stub_count} ({stub_count/total*100:.1f}%)\n")
    
    print(f"\n修复报告已写入: {report_path}")


if __name__ == '__main__':
    main()