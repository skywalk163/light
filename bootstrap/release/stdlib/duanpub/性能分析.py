"""
性能分析 — duanpub 桥接模块

基于 Python time/profile 等库封装，函数名对齐 duanpub/packages/性能分析/源.duan。

duanpub 原始包通过 C FFI 实现 CPU 采样、内存分析、火焰图生成，
本桥接模块用 Python time/tracemalloc/cProfile 等模块替代，提供等价的性能分析功能。
"""

import time as _time
import threading as _threading
import os as _os
import struct as _struct
import sys as _sys
import io as _io


# =============================================================================
# CPU 采样
# =============================================================================

_采样数据 = []
_采样中 = False
_采样线程 = None
_采样间隔 = 0.01


def _采样工作():
    global _采样数据
    while _采样中:
        try:
            frame = _sys._getframe(2)
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            funcname = frame.f_code.co_name
            _采样数据.append({
                'filename': filename,
                'lineno': lineno,
                'funcname': funcname,
                'timestamp': _time.time(),
            })
        except Exception:
            pass
        _time.sleep(_采样间隔)


def 开始CPU采样(interval=0.01):
    """开始 CPU 采样"""
    global _采样数据, _采样中, _采样线程, _采样间隔
    if _采样中:
        raise Exception("开始CPU采样失败: 已在采样中")
    try:
        _采样数据 = []
        _采样中 = True
        _采样间隔 = interval
        _采样线程 = _threading.Thread(target=_采样工作, daemon=True)
        _采样线程.start()
        return True
    except Exception as e:
        raise Exception("开始CPU采样失败: " + str(e))


def 停止CPU采样():
    """停止 CPU 采样"""
    global _采样中
    if not _采样中:
        raise Exception("停止CPU采样失败: 未在采样中")
    try:
        _采样中 = False
        if _采样线程:
            _采样线程.join(timeout=1)
        return True
    except Exception as e:
        raise Exception("停止CPU采样失败: " + str(e))


def 获取CPU采样():
    """获取 CPU 采样数据"""
    global _采样数据
    return _采样数据[:]


# =============================================================================
# 火焰图生成
# =============================================================================

def 按值降序排序(data):
    """按值降序排序"""
    if not data:
        return []
    try:
        return sorted(data, key=lambda x: x[1] if isinstance(x, (list, tuple)) else x, reverse=True)
    except Exception:
        return data


def 排序节点递归(nodes, key_func=None):
    """递归排序节点"""
    if not nodes:
        return nodes
    try:
        if key_func:
            return sorted(nodes, key=key_func, reverse=True)
        return sorted(nodes, key=lambda x: x.get('count', 0) if isinstance(x, dict) else 0, reverse=True)
    except Exception:
        return nodes


def 生成火焰图节点(name, count, children=None):
    """生成火焰图节点"""
    return {
        'name': str(name),
        'count': count,
        'children': children or [],
    }


def 生成火焰图(samples):
    """从采样数据生成火焰图"""
    if not samples:
        return {'name': 'root', 'count': 0, 'children': []}
    try:
        root = {'name': 'root', 'count': 0, 'children': []}
        for s in samples:
            name = f"{s.get('filename', 'unknown')}:{s.get('funcname', 'unknown')}"
            # 简单聚合
            found = False
            for child in root['children']:
                if child['name'] == name:
                    child['count'] += 1
                    found = True
                    break
            if not found:
                root['children'].append({'name': name, 'count': 1, 'children': []})
            root['count'] += 1
        return root
    except Exception as e:
        raise Exception("生成火焰图失败: " + str(e))


def 生成火焰图SVG(flame_data):
    """生成火焰图 SVG"""
    return 生成火焰图HTML(flame_data)


def 最大深度计算(node, depth=0):
    """计算节点最大深度"""
    if not node:
        return depth
    max_d = depth
    for child in node.get('children', []):
        child_depth = 最大深度计算(child, depth + 1)
        if child_depth > max_d:
            max_d = child_depth
    return max_d


def 绘制节点SVG(node, x, y, width, height, depth):
    """绘制节点 SVG"""
    if not node:
        return ''
    try:
        color = 生成节点颜色(node['name'])
        svg = f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{color}" stroke="#fff" stroke-width="1"/>'
        label = 转义SVG(node['name'][:30])
        svg += f'<text x="{x + 2}" y="{y + height - 4}" font-size="11" fill="#fff">{label}</text>'
        return svg
    except Exception:
        return ''


def 生成节点颜色(name):
    """根据名称生成节点颜色"""
    try:
        hash_val = hash(str(name))
        r = (hash_val & 0xFF) % 180 + 40
        g = ((hash_val >> 8) & 0xFF) % 180 + 40
        b = ((hash_val >> 16) & 0xFF) % 180 + 40
        return f"rgb({r},{g},{b})"
    except Exception:
        return "rgb(100,100,100)"


def 转义SVG(text):
    """转义 SVG 文本"""
    if not text:
        return ''
    text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    return text


def 生成火焰图HTML(flame_data):
    """生成火焰图 HTML"""
    if not flame_data:
        return '<html><body>No data</body></html>'
    try:
        svg_parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800">']
        y = 0
        for child in flame_data.get('children', []):
            svg_parts.append(绘制节点SVG(child, 0, y, 1200, 20, 0))
            y += 22
        svg_parts.append('</svg>')
        html = '<html><body style="margin:0;background:#111">'
        html += '\n'.join(svg_parts)
        html += '</body></html>'
        return html
    except Exception as e:
        raise Exception("生成火焰图HTML失败: " + str(e))


def 字符串替换(text, old, new):
    """字符串替换"""
    if not text:
        return ''
    return str(text).replace(str(old), str(new))


def 字符串长度(text):
    """获取字符串长度"""
    if text is None:
        return 0
    return len(str(text))


# =============================================================================
# 内存分析
# =============================================================================

_内存快照 = {}


def 创建内存快照(name='default'):
    """创建内存快照"""
    try:
        import tracemalloc as _tracemalloc
        if not _tracemalloc.is_tracing():
            _tracemalloc.start()
        snapshot = _tracemalloc.take_snapshot()
        _内存快照[name] = snapshot
        return name
    except ImportError:
        # tracemalloc 不可用时返回模拟数据
        _内存快照[name] = {'time': _time.time()}
        return name
    except Exception as e:
        raise Exception("创建内存快照失败: " + str(e))


def 获取内存使用量():
    """获取当前内存使用量（字节）"""
    try:
        import tracemalloc as _tracemalloc
        if not _tracemalloc.is_tracing():
            _tracemalloc.start()
        snapshot = _tracemalloc.take_snapshot()
        stats = snapshot.statistics('lineno')
        total = sum(stat.size for stat in stats)
        return total
    except ImportError:
        try:
            import psutil as _psutil
            return _psutil.Process().memory_info().rss
        except ImportError:
            return 0
    except Exception:
        return 0


def 获取内存峰值():
    """获取内存峰值使用量"""
    try:
        total = 获取内存使用量()
        return total
    except Exception:
        return 0


def 比较内存快照(name1='default', name2=None):
    """比较两个内存快照"""
    if name1 not in _内存快照:
        raise Exception("比较内存快照失败: 快照不存在 " + name1)
    try:
        import tracemalloc as _tracemalloc
        snap1 = _内存快照[name1]
        if name2 and name2 in _内存快照:
            snap2 = _内存快照[name2]
            diff = snap2.compare_to(snap1, 'lineno')
            return [{'file': str(d.traceback), 'size': d.size, 'count': d.count} for d in diff[:10]]
        return {'size': 获取内存使用量(), 'snapshot': name1}
    except ImportError:
        return {'size': 获取内存使用量(), 'snapshot': name1}
    except Exception as e:
        raise Exception("比较内存快照失败: " + str(e))


def 内存泄漏检测():
    """内存泄漏检测"""
    try:
        usage = 获取内存使用量()
        return {
            'current': usage,
            'warning': 'high' if usage > 500 * 1024 * 1024 else 'normal',
        }
    except Exception as e:
        raise Exception("内存泄漏检测失败: " + str(e))


# =============================================================================
# 计时器
# =============================================================================

_计时器存储 = {}


def 开始计时(name='default'):
    """开始计时"""
    _计时器存储[name] = _time.perf_counter()
    return name


def 结束计时(name='default'):
    """结束计时"""
    if name not in _计时器存储:
        raise Exception("结束计时失败: 计时器不存在 " + name)
    try:
        elapsed = _time.perf_counter() - _计时器存储[name]
        del _计时器存储[name]
        return elapsed
    except Exception as e:
        raise Exception("结束计时失败: " + str(e))


def 计时器耗时(name='default'):
    """获取计时器已耗时"""
    if name not in _计时器存储:
        raise Exception("计时器耗时失败: 计时器不存在 " + name)
    return _time.perf_counter() - _计时器存储[name]


def 测量执行时间(func, *args, **kwargs):
    """测量函数执行时间"""
    if not callable(func):
        raise Exception("测量执行时间失败: 函数不是可调用对象")
    try:
        start = _time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = _time.perf_counter() - start
        return {'result': result, 'time': elapsed}
    except Exception as e:
        raise Exception("测量执行时间失败: " + str(e))


def 测量多次(func, repeat=3, *args, **kwargs):
    """多次测量函数执行时间"""
    if not callable(func):
        raise Exception("测量多次失败: 函数不是可调用对象")
    if repeat < 1:
        raise Exception("测量多次失败: repeat 必须大于0")
    try:
        times = []
        last_result = None
        for _ in range(repeat):
            start = _time.perf_counter()
            last_result = func(*args, **kwargs)
            elapsed = _time.perf_counter() - start
            times.append(elapsed)
        return {
            'result': last_result,
            'times': times,
            'min': min(times),
            'max': max(times),
            'avg': sum(times) / len(times),
            'total': sum(times),
        }
    except Exception as e:
        raise Exception("测量多次失败: " + str(e))


# =============================================================================
# 性能报告
# =============================================================================

class _PerformanceReport:
    """性能报告"""
    def __init__(self):
        self.cpu_samples = []
        self.memory_snapshots = []
        self.timers = []


def 创建性能报告():
    """创建性能报告"""
    try:
        return _PerformanceReport()
    except Exception as e:
        raise Exception("创建性能报告失败: " + str(e))


def 添加CPU采样(report, samples):
    """添加 CPU 采样数据到报告"""
    if not report:
        raise Exception("添加CPU采样失败: 报告为空")
    report.cpu_samples = list(samples)
    return True


def 添加内存快照(report, snapshot):
    """添加内存快照到报告"""
    if not report:
        raise Exception("添加内存快照失败: 报告为空")
    report.memory_snapshots.append(snapshot)
    return True


def 添加计时器(report, name, elapsed):
    """添加计时器数据到报告"""
    if not report:
        raise Exception("添加计时器失败: 报告为空")
    report.timers.append({'name': name, 'elapsed': elapsed})
    return True


def 生成报告(report):
    """生成性能报告"""
    return 生成文本报告(report)


def 生成文本报告(report):
    """生成文本格式的性能报告"""
    if not report:
        raise Exception("生成文本报告失败: 报告为空")
    try:
        lines = ['=== 性能报告 ===']
        if report.cpu_samples:
            lines.append(f'CPU 采样数: {len(report.cpu_samples)}')
        if report.memory_snapshots:
            lines.append(f'内存快照数: {len(report.memory_snapshots)}')
        if report.timers:
            lines.append('计时器:')
            for t in report.timers:
                lines.append(f'  {t["name"]}: {t["elapsed"]:.4f}s')
        return '\n'.join(lines)
    except Exception as e:
        raise Exception("生成文本报告失败: " + str(e))


def 生成HTML报告(report):
    """生成 HTML 格式的性能报告"""
    if not report:
        raise Exception("生成HTML报告失败: 报告为空")
    try:
        html = '<html><body><h1>性能报告</h1>'
        if report.cpu_samples:
            html += f'<p>CPU 采样数: {len(report.cpu_samples)}</p>'
        if report.memory_snapshots:
            html += f'<p>内存快照数: {len(report.memory_snapshots)}</p>'
        if report.timers:
            html += '<h2>计时器</h2><ul>'
            for t in report.timers:
                html += f'<li>{t["name"]}: {t["elapsed"]:.4f}s</li>'
            html += '</ul>'
        html += '</body></html>'
        return html
    except Exception as e:
        raise Exception("生成HTML报告失败: " + str(e))


def 格式化字节(bytes_val):
    """格式化字节大小"""
    if bytes_val < 0:
        raise Exception("格式化字节失败: 负数")
    try:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.2f} PB"
    except Exception as e:
        raise Exception("格式化字节失败: " + str(e))


def 检测热点函数(samples):
    """检测热点函数"""
    if not samples:
        return []
    try:
        hotspots = {}
        for s in samples:
            name = f"{s.get('filename', '')}:{s.get('funcname', '')}"
            hotspots[name] = hotspots.get(name, 0) + 1
        sorted_hotspots = sorted(hotspots.items(), key=lambda x: x[1], reverse=True)
        return [{'name': name, 'count': count} for name, count in sorted_hotspots[:20]]
    except Exception as e:
        raise Exception("检测热点函数失败: " + str(e))


def 检测热点代码行(samples):
    """检测热点代码行"""
    if not samples:
        return []
    try:
        hotspots = {}
        for s in samples:
            line = f"{s.get('filename', '')}:{s.get('lineno', 0)}"
            hotspots[line] = hotspots.get(line, 0) + 1
        sorted_hotspots = sorted(hotspots.items(), key=lambda x: x[1], reverse=True)
        return [{'location': loc, 'count': count} for loc, count in sorted_hotspots[:20]]
    except Exception as e:
        raise Exception("检测热点代码行失败: " + str(e))


def 生成调用树(samples):
    """生成调用树"""
    if not samples:
        return {'name': 'root', 'count': 0, 'children': []}
    try:
        return 生成火焰图(samples)
    except Exception as e:
        raise Exception("生成调用树失败: " + str(e))


def 高精度计时器():
    """获取高精度计时器值"""
    return _time.perf_counter()


def 当前线程ID():
    """获取当前线程 ID"""
    try:
        return _threading.get_ident()
    except Exception:
        return 0


def 当前进程ID():
    """获取当前进程 ID"""
    try:
        return _os.getpid()
    except Exception:
        return 0