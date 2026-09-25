# -*- coding: utf-8 -*-
"""
光明代码格式化器 (Light Formatter)

提供光明代码的格式化功能，包括缩进、空格、换行、空行、导入排序等。
"""

from src.formatter.light_formatter import LightFormatter, format_code, check_format

__version__ = '1.1.0'

__all__ = ['LightFormatter', 'format_code', 'check_format', 'run_formatter']

_DEFAULT_EXTS = ('.light',)


def run_formatter(target, check_only=False, indent_size=4, max_line_length=80,
                  extensions=_DEFAULT_EXTS, verbose=False):
    """CLI 入口（`light fmt`）：格式化光明代码文件或目录。

    参数:
        target: 文件或目录路径
        check_only: True 时只检查不写回（CI 场景）
        indent_size: 缩进宽度
        max_line_length: 单行最大长度
        extensions: 目录递归时纳入的文件后缀
        verbose: 是否打印「合规」文件的明细

    返回:
        int 退出码：0=全部合规或已格式化；1=存在需格式化的文件 / 处理出错；
        2=目标路径不存在。

    说明:
        为保持仓库既有行尾风格（Windows CRLF / POSIX LF），读写按原样处理，
        格式化前后若行尾不一致会原样还原，避免误伤整个工作树。
    """
    import os

    def _处理单文件(path):
        """返回 (状态, 详情)；状态 ∈ {'ok', 'changed', 'error'}"""
        try:
            raw = open(path, 'rb').read()
            crlf = b'\r\n' in raw
            source = raw.decode('utf-8').replace('\r\n', '\n')
            if check_only:
                issues = check_format(source, indent_size, max_line_length)
                return ('changed' if issues else 'ok', issues)
            formatted = format_code(source, indent_size, max_line_length)
            formatted = formatted.replace('\r\n', '\n')
            if formatted != source:
                payload = formatted.replace('\n', '\r\n') if crlf else formatted
                open(path, 'wb').write(payload.encode('utf-8'))
                return ('changed', None)
            return ('ok', None)
        except Exception as exc:  # CLI 不应向用户抛 traceback
            return ('error', '%s: %s' % (type(exc).__name__, exc))

    目标列表 = []
    if os.path.isfile(target):
        目标列表 = [target]
    elif os.path.isdir(target):
        for root, _dirs, files in os.walk(target):
            for name in sorted(files):
                if name.endswith(extensions):
                    目标列表.append(os.path.join(root, name))
    else:
        print('错误: 路径不存在: %s' % target)
        return 2

    if not 目标列表:
        print('未找到待处理文件（后缀: %s）: %s' % ('/'.join(extensions), target))
        return 0

    退出码 = 0
    变更列表 = []
    for path in 目标列表:
        状态, 详情 = _处理单文件(path)
        if 状态 == 'changed':
            变更列表.append(path)
            if check_only:
                print('需要格式化: %s' % path)
                for issue in (详情 or []):
                    print('    行 %s' % issue.get('line'))
            else:
                print('已格式化: %s' % path)
        elif 状态 == 'error':
            退出码 = 1
            print('跳过（处理失败）: %s -> %s' % (path, 详情))
        elif verbose:
            print('合规: %s' % path)

    if 变更列表:
        print('')
        print('共 %d 个文件%s。' % (len(变更列表), '需要格式化' if check_only else '已格式化'))
    else:
        print('全部文件已完成格式化。')
    if check_only and 变更列表:
        退出码 = 1
    return 退出码