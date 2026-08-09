# -*- coding: utf-8 -*-
"""
光明（Light）文件监视模块

支持文件变化自动重新编译/运行
"""

import os
import sys
import time
import threading


class FileWatcher:

    def __init__(self, target, on_change, interval=1.0):
        """初始化文件监视器

        Args:
            target: 文件路径或目录路径
            on_change: 变化回调函数
            interval: 检查间隔（秒）
        """
        self.target = target
        self.on_change = on_change
        self.interval = interval
        self.running = False
        self.thread = None
        self.last_mtimes = {}

    def _get_mtimes(self):
        """获取目标的修改时间"""
        if os.path.isfile(self.target):
            try:
                return {self.target: os.path.getmtime(self.target)}
            except OSError:
                return {}
        elif os.path.isdir(self.target):
            mtimes = {}
            for root, dirs, files in os.walk(self.target):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                for f in files:
                    if f.endswith('.light'):
                        fpath = os.path.join(root, f)
                        try:
                            mtimes[fpath] = os.path.getmtime(fpath)
                        except OSError:
                            pass
            return mtimes
        return {}

    def _check_changes(self):
        """检查是否有文件变化"""
        current = self._get_mtimes()

        # 检查新增或修改的文件
        for fpath, mtime in current.items():
            if fpath not in self.last_mtimes or self.last_mtimes[fpath] != mtime:
                return True

        # 检查删除的文件
        for fpath in self.last_mtimes:
            if fpath not in current:
                return True

        return False

    def _watch_loop(self):
        """监视循环"""
        self.last_mtimes = self._get_mtimes()

        while self.running:
            if self._check_changes():
                self.last_mtimes = self._get_mtimes()
                try:
                    self.on_change()
                except Exception as e:
                    print(f"执行错误: {e}", file=sys.stderr)

            time.sleep(self.interval)

    def start(self):
        """开始监视"""
        if self.running:
            return

        print(f"开始监视: {self.target}")
        print(f"按 Ctrl+C 停止")
        print("=" * 60)
        print()

        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()

        # 首次执行
        try:
            self.on_change()
        except Exception as e:
            print(f"执行错误: {e}", file=sys.stderr)

        # 主线程等待
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止监视"""
        self.running = False
        print("\n" + "=" * 60)
        print("已停止监视")


def run_with_watch(filepath, backend='src', interval=1.0):
    """以监视模式运行光明文件

    Args:
        filepath: 源文件路径
        backend: 后端类型
        interval: 检查间隔（秒）
    """
    from light_parser_v3 import LightParser
    from code_generator import PythonCodeGenerator

    def _run():
        """执行代码"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()

            print(f"[{time.strftime('%H:%M:%S')}] 检测到变化，重新运行...")
            print("-" * 60)

            parser = LightParser()
            module = parser.parse(source)
            generator = PythonCodeGenerator()
            py_code = generator.generate(module)

            output_lines = []

            def capture_print(*args, **kwargs):
                line = ' '.join(str(a) for a in args)
                output_lines.append(line)

            namespace = {
                'print': capture_print,
                '__name__': '__main__',
                '__file__': filepath
            }

            exec(py_code, namespace)

            if output_lines:
                print('\n'.join(output_lines))

            print("-" * 60)
            print(f"执行完成\n")

        except Exception as e:
            print(f"运行错误: {e}")
            import traceback
            tb = traceback.format_exc()
            for line in tb.split('\n')[-6:]:
                if line.strip():
                    print(f"  {line}")
            print("-" * 60)
            print()

    watcher = FileWatcher(filepath, _run, interval=interval)
    watcher.start()