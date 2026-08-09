#!/usr/bin/env python3
"""
光明语法迁移脚本

将旧语法批量迁移到新语法：
1. 定义 x 等于 y  ->  设 x 为 y
2. 令 x=v / 令 x = v  ->  设 x 为 v  (lightpub 包特有)
3. 使用 模块.*  ->  导入 模块  (lightpub 包特有)
4. 输出(...)  ->  打印(...)  (lightpub 包特有)
5. 段落/函数 名 接收 参数  ->  函数 名(参数)
6. 对象之属性  ->  对象的属性（成员访问符统一）
7. 段落/段 关键词  ->  函数（选词优化，段落 仍向后兼容但推荐用 函数）

用法:
    python tools/migrate_syntax.py <文件或目录>
    python tools/migrate_syntax.py --dry-run <文件或目录>  # 预览模式
    python tools/migrate_syntax.py --lightpub <目录>        # lightpub 包专用模式
"""

import sys
import os
import re
from pathlib import Path


# =============================================================================
# 赋值语法迁移
# =============================================================================

def migrate_assignment(content: str) -> tuple:
    """迁移赋值语法：定义 x 等于 y -> 设 x 为 y"""
    changes = []
    
    pattern = re.compile(
        r'^(\s*)定义\s+(\S+)\s+等于\s+',
        re.MULTILINE
    )
    
    def replacer(m):
        indent, name = m.group(1), m.group(2)
        changes.append(f'  赋值: "{indent}定义 {name} 等于 ..." -> "{indent}设 {name} 为 ..."')
        return f'{indent}设 {name} 为 '
    
    new_content = pattern.sub(replacer, content)
    return new_content, changes


def migrate_ling_assignment(content: str) -> tuple:
    """迁移 lightpub 令 赋值语法：令 x=v / 令 x = v -> 设 x 为 v
    
    匹配模式：
    - 令 变量名=值（等号无空格）
    - 令 变量名 = 值（等号有空格）
    
    注意排除：
    - 命令、令牌、令号、指令等含"令"字的词
    - 注释中的令
    """
    changes = []
    
    # 匹配：行首（可选缩进）+ 令 + 空格 + 标识符 + = （可选空格）
    # 标识符：中文/英文/下划线开头
    pattern = re.compile(
        r'^(\s*)令\s+([\u4e00-\u9fffA-Za-z_][\u4e00-\u9fffA-Za-z_0-9]*)\s*=\s*',
        re.MULTILINE
    )
    
    def replacer(m):
        indent, name = m.group(1), m.group(2)
        changes.append(f'  令赋值: "{indent}令 {name}=..." -> "{indent}设 {name} 为 ..."')
        return f'{indent}设 {name} 为 '
    
    new_content = pattern.sub(replacer, content)
    return new_content, changes


# =============================================================================
# 导入语法迁移
# =============================================================================

def migrate_import(content: str) -> tuple:
    """迁移导入语法：使用 模块.* / 使用 模块 -> 导入 模块
    
    匹配模式：
    - 使用 模块名.*
    - 使用 模块名.子模块.*
    - 使用 模块名（不带 .*）
    - 使用 "模块名"（带引号）
    
    注意：只匹配行首的使用，不匹配注释中的。
    """
    changes = []
    
    # 模式1：使用 模块名.*
    pattern1 = re.compile(
        r'^(\s*)使用\s+([\u4e00-\u9fffA-Za-z_][\u4e00-\u9fffA-Za-z_0-9.]*)\.\*',
        re.MULTILINE
    )
    
    def replacer1(m):
        indent, module_path = m.group(1), m.group(2)
        changes.append(f'  导入: "{indent}使用 {module_path}.*" -> "{indent}导入 {module_path}"')
        return f'{indent}导入 {module_path}'
    
    new_content = pattern1.sub(replacer1, content)
    
    # 模式2：使用 模块名（不带 .*，行首，后面是换行或空格）
    # 排除：使用 "..."（带引号的）
    pattern2 = re.compile(
        r'^(\s*)使用\s+([\u4e00-\u9fffA-Za-z_][\u4e00-\u9fffA-Za-z_0-9]*)\s*$',
        re.MULTILINE
    )
    
    def replacer2(m):
        indent, module_path = m.group(1), m.group(2)
        changes.append(f'  导入: "{indent}使用 {module_path}" -> "{indent}导入 {module_path}"')
        return f'{indent}导入 {module_path}'
    
    new_content = pattern2.sub(replacer2, new_content)
    
    # 模式3：使用 "模块名"（带引号）
    pattern3 = re.compile(
        r'^(\s*)使用\s+"([\u4e00-\u9fffA-Za-z_][\u4e00-\u9fffA-Za-z_0-9]*)"\s*$',
        re.MULTILINE
    )
    
    def replacer3(m):
        indent, module_path = m.group(1), m.group(2)
        changes.append(f'  导入: \'{indent}使用 "{module_path}"\' -> "{indent}导入 {module_path}"')
        return f'{indent}导入 {module_path}'
    
    new_content = pattern3.sub(replacer3, new_content)
    
    return new_content, changes


# =============================================================================
# 输出函数迁移
# =============================================================================

def migrate_output(content: str) -> tuple:
    """迁移输出函数：输出(...) -> 打印(...)
    
    注意：只匹配函数调用，不匹配注释中的"输出"。
    """
    changes = []
    
    # 匹配：输出( 后跟内容，行首或空格后
    pattern = re.compile(
        r'(?<![^\s])输出\('
    )
    
    def replacer(m):
        changes.append('  输出: "输出(" -> "打印("')
        return '打印('
    
    new_content = pattern.sub(replacer, content)
    return new_content, changes


# =============================================================================
# 函数参数语法迁移
# =============================================================================

def migrate_paragraph_params(content: str) -> tuple:
    """迁移函数参数语法：段落/函数 名 接收 参数 -> 段落/函数 名(参数)
    
    支持：
    - 段落 名 接收 参数:
    - 段落 名 接收：           （无参数）
    - 函数 名 接收 参数:
    """
    changes = []
    
    # 匹配：段落/段/函数 名 接收 参数列表: （支持半角:和全角：）
    pattern = re.compile(
        r'^(\s*)(段落|段|函数)\s+(\S+)\s+接收\s+(.+?)(\s*[:：]\s*)$',
        re.MULTILINE
    )
    
    def replacer(m):
        indent, kw, name, params, colon = m.groups()
        params = params.strip()
        # 统一用半角冒号
        colon = ':'
        changes.append(f'  函数参数: "{kw} {name} 接收 {params}:" -> "{kw} {name}({params}):"')
        return f'{indent}{kw} {name}({params}){colon}'
    
    new_content = pattern.sub(replacer, content)
    
    # 匹配无参数：段落/段/函数 名 接收：（支持半角:和全角：）
    pattern_no_params = re.compile(
        r'^(\s*)(段落|段|函数)\s+(\S+)\s+接收(\s*[:：]\s*)$',
        re.MULTILINE
    )
    
    def replacer_no_params(m):
        indent, kw, name, colon = m.groups()
        # 统一用半角冒号
        colon = ':'
        changes.append(f'  函数参数: "{kw} {name} 接收:" -> "{kw} {name}():"')
        return f'{indent}{kw} {name}(){colon}'
    
    new_content = pattern_no_params.sub(replacer_no_params, new_content)
    
    return new_content, changes


# =============================================================================
# 成员访问符迁移
# =============================================================================

def migrate_member_access(content: str) -> tuple:
    """迁移成员访问符：对象之属性 -> 对象的属性"""
    changes = []
    
    comprehension_words = {'列表', '集合', '字典', '映射', '筛选'}
    
    pattern = re.compile(
        r'(?<![\w\'"])([\u4e00-\u9fffA-Za-z_][\u4e00-\u9fffA-Za-z_0-9]*?)之([\u4e00-\u9fffA-Za-z_][\u4e00-\u9fffA-Za-z_0-9]*)'
    )
    
    def replace_zhi(m):
        prefix = m.group(1)
        next_word = m.group(2)
        if next_word in comprehension_words:
            return m.group(0)
        if prefix.endswith(('和', '差', '积', '商', '数', '值')):
            return m.group(0)
        changes.append(f'  成员访问: "{prefix}之{next_word}" -> "{prefix}的{next_word}"')
        return f'{prefix}的{next_word}'
    
    new_content = pattern.sub(replace_zhi, content)
    return new_content, changes


# =============================================================================
# 段落关键词迁移
# =============================================================================

def migrate_paragraph_keyword(content: str) -> tuple:
    """迁移段落关键词：段落 -> 函数"""
    changes = []
    
    pattern = re.compile(
        r'^(\s*(?:(?:严格|松散|异步)\s+)?)段落(\s+)',
        re.MULTILINE
    )
    
    def replacer(m):
        prefix = m.group(1)
        suffix = m.group(2)
        changes.append(f'  关键词: "{prefix}段落{suffix}" -> "{prefix}函数{suffix}"')
        return f'{prefix}函数{suffix}'
    
    new_content = pattern.sub(replacer, content)
    return new_content, changes


# =============================================================================
# 单文件迁移
# =============================================================================

def migrate_file(filepath: str, dry_run: bool = False, lightpub_mode: bool = False) -> list:
    """迁移单个文件
    
    Args:
        filepath: 文件路径
        dry_run: 预览模式
        lightpub_mode: lightpub 包专用模式（启用令赋值、使用导入、输出函数迁移）
    """
    try:
        # 尝试多种编码
        encoding = 'utf-8'
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='gbk') as f:
                content = f.read()
                encoding = 'gbk'
    except Exception as e:
        print(f'  [错误] 无法读取 {filepath}: {e}')
        return []
    
    all_changes = []
    
    # 1. 赋值语法迁移（定义 x 等于 y -> 设 x 为 y）
    content, changes = migrate_assignment(content)
    all_changes.extend(changes)
    
    # 2. lightpub 特有：令 赋值迁移
    if lightpub_mode:
        content, changes = migrate_ling_assignment(content)
        all_changes.extend(changes)
    
    # 3. lightpub 特有：使用 X.* -> 导入 X
    if lightpub_mode:
        content, changes = migrate_import(content)
        all_changes.extend(changes)
    
    # 4. lightpub 特有：输出() -> 打印()
    if lightpub_mode:
        content, changes = migrate_output(content)
        all_changes.extend(changes)
    
    # 5. 函数参数语法迁移
    content, changes = migrate_paragraph_params(content)
    all_changes.extend(changes)
    
    # 6. 成员访问符迁移
    content, changes = migrate_member_access(content)
    all_changes.extend(changes)
    
    # 7. 段落关键词迁移（段落 -> 函数）
    content, changes = migrate_paragraph_keyword(content)
    all_changes.extend(changes)
    
    if all_changes and not dry_run:
        # 备份原文件
        backup_path = filepath + '.bak'
        with open(backup_path, 'w', encoding=encoding) as f:
            # 重新读取原始内容做备份
            try:
                with open(filepath, 'r', encoding=encoding) as orig:
                    f.write(orig.read())
            except Exception:
                pass
        
        # 写入新内容
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f'  [已迁移] {filepath} ({len(all_changes)} 处变更)')
    elif all_changes and dry_run:
        print(f'  [预览] {filepath} ({len(all_changes)} 处变更)')
    
    for change in all_changes:
        print(change)
    
    return all_changes


# =============================================================================
# 统计报告
# =============================================================================

def generate_report(all_results: dict) -> str:
    """生成迁移统计报告"""
    lines = []
    lines.append('=' * 60)
    lines.append('  光明语法迁移统计报告')
    lines.append('=' * 60)
    
    total_files = 0
    total_changes = 0
    category_stats = {}
    failed_files = []
    
    for filepath, changes in all_results.items():
        if changes == 'ERROR':
            failed_files.append(filepath)
            continue
        total_files += 1
        total_changes += len(changes)
        for change in changes:
            # 提取变更类别
            if ':' in change:
                cat = change.strip().split(':')[0].strip().lstrip()
                category_stats[cat] = category_stats.get(cat, 0) + 1
    
    lines.append(f'  迁移文件数: {total_files}')
    lines.append(f'  总变更数: {total_changes}')
    lines.append(f'  失败文件数: {len(failed_files)}')
    lines.append('')
    lines.append('  按类别统计:')
    for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
        lines.append(f'    {cat}: {count} 处')
    
    if failed_files:
        lines.append('')
        lines.append('  失败文件:')
        for f in failed_files:
            lines.append(f'    {f}')
    
    lines.append('=' * 60)
    return '\n'.join(lines)


# =============================================================================
# 主函数
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print('用法: python tools/migrate_syntax.py [--dry-run] [--lightpub] <文件或目录>')
        sys.exit(1)
    
    dry_run = '--dry-run' in sys.argv
    lightpub_mode = '--lightpub' in sys.argv
    paths = [a for a in sys.argv[1:] if not a.startswith('--')]
    
    if not paths:
        print('错误: 请指定文件或目录')
        sys.exit(1)
    
    total_changes = 0
    all_results = {}
    
    for path_str in paths:
        path = Path(path_str)
        
        if path.is_file() and path.suffix == '.light':
            print(f'\n处理: {path}')
            changes = migrate_file(str(path), dry_run, lightpub_mode)
            all_results[str(path)] = changes
            total_changes += len(changes)
        elif path.is_dir():
            light_files = list(path.rglob('*.light'))
            print(f'\n扫描目录: {path} ({len(light_files)} 个 .light 文件)')
            for f in light_files:
                changes = migrate_file(str(f), dry_run, lightpub_mode)
                all_results[str(f)] = changes
                total_changes += len(changes)
        else:
            print(f'\n跳过: {path} (不是 .light 文件或目录)')
    
    # 生成统计报告
    print(generate_report(all_results))
    if dry_run:
        print(f'  (预览模式，未实际修改文件)')


if __name__ == '__main__':
    main()
