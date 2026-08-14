# -*- coding: utf-8 -*-
"""LLM 调用全局节流（v0.30，跨进程持久化）。

兜底生成器与校验器都会调真实 LLM。早期版本用进程级时间戳 `_LAST`，但兜底首跑
harness 每条意图都 fork 一个 组合.py 子进程，子进程内 `_LAST` 重新归零 → 节流
只对「单子进程内 validate→generate」生效，**跨意图的 40 次 LLM 调用完全不受控**，
于是多条意图在 DeepSeek 上并发/短时爆发被端点限掉或静默报错 → 生成=- 假阴性。

本版改用「共享时间戳文件 + 原子文件锁」：
- 时间戳文件 `.llm_throttle.ts` 记录上次真实发出的 LLM 调用时刻（跨进程可见）；
- 文件锁 `.llm_throttle.lock` 用 O_EXCL 原子创建做互斥，保证「读上次→睡够→写新值」
  这一段在多进程间不被打断；
- 带随机抖动 + 陈旧锁自愈，避免死锁。
这样整批所有 LLM 调用被真实串行隔开 最小 秒，从源头消掉端点限流/并发报错。
"""
import time
import random
import os

_目录 = os.path.dirname(os.path.abspath(__file__))
_TS = os.path.join(_目录, '.llm_throttle.ts')
_LOCK = os.path.join(_目录, '.llm_throttle.lock')
_锁超时 = 60  # 秒，防死锁上限
_锁陈旧 = 30  # 秒，超过此龄的锁视为残留，强制接管


def _取上次():
    try:
        with open(_TS, 'r', encoding='utf-8') as f:
            return float(f.read().strip() or 0)
    except Exception:
        return 0.0


def _写上次(t):
    try:
        with open(_TS, 'w', encoding='utf-8') as f:
            f.write('%.3f' % t)
    except Exception:
        pass


def _抢锁():
    """原子建锁，成功返回 True 并持有锁；超时/陈旧则强制接管返回 True。"""
    截止 = time.time() + _锁超时
    while time.time() < 截止:
        try:
            os.open(_LOCK, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            return True
        except FileExistsError:
            # 陈旧锁自愈：mtime 过老说明持有者已崩，强制删除接管
            try:
                if time.time() - os.path.getmtime(_LOCK) > _锁陈旧:
                    os.remove(_LOCK)
            except OSError:
                pass
            time.sleep(0.1)
        except OSError:
            time.sleep(0.1)
    # 超时仍继续（不阻塞业务），但打印警告
    print('[节流] 抢锁超时，跳过互斥（可能并发）')
    return False


def _放锁():
    try:
        os.remove(_LOCK)
    except OSError:
        pass


def 限流(最小=8):
    """发起下一次 LLM 调用前调用：保证距上次真实调用至少 最小 秒（带 0~1.5s 抖动）。

    跨进程持久化——整批所有 LLM 调用被串行隔开，消掉端点并发/短爆发限流。
    """
    held = _抢锁()
    try:
        last = _取上次()
        等 = 最小 - (time.time() - last)
        if 等 > 0:
            time.sleep(等 + random.uniform(0, 1.5))
        _写上次(time.time())
    finally:
        if held:
            _放锁()
