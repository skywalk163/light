"""
异步运行时 — lightpub 桥接模块

基于 Python asyncio 库封装，函数名对齐上游 duanpub（段言时期）packages/异步运行时/源.duan。

上游 duanpub 原始包通过 C FFI 实现异步运行时，
本桥接模块用 Python asyncio 模块替代，提供等价的 Future/Promise/EventLoop 功能。
"""

import asyncio as _asyncio
import threading as _threading
from functools import partial as _partial


# =============================================================================
# Future 相关
# =============================================================================

def 创建Future():
    """创建一个 Future 对象"""
    try:
        loop = _asyncio.get_event_loop()
        return loop.create_future()
    except Exception as e:
        raise Exception("创建Future失败: " + str(e))


def 创建Future完成(result):
    """创建一个已完成的 Future 对象"""
    try:
        fut = _asyncio.get_event_loop().create_future()
        fut.set_result(result)
        return fut
    except Exception as e:
        raise Exception("创建Future完成失败: " + str(e))


def 创建Future失败(exception):
    """创建一个已失败的 Future 对象"""
    try:
        fut = _asyncio.get_event_loop().create_future()
        fut.set_exception(exception if isinstance(exception, Exception) else Exception(str(exception)))
        return fut
    except Exception as e:
        raise Exception("创建Future失败失败: " + str(e))


def 未来完成(fut):
    """设置 Future 为完成状态"""
    if not fut:
        raise Exception("未来完成失败: Future为空")
    try:
        if not fut.done():
            fut.set_result(None)
        return True
    except Exception as e:
        raise Exception("未来完成失败: " + str(e))


def 未来拒绝(fut, exception):
    """设置 Future 为拒绝状态"""
    if not fut:
        raise Exception("未来拒绝失败: Future为空")
    try:
        if not fut.done():
            fut.set_exception(exception if isinstance(exception, Exception) else Exception(str(exception)))
        return True
    except Exception as e:
        raise Exception("未来拒绝失败: " + str(e))


def 未来等待(fut):
    """等待 Future 完成"""
    if not fut:
        raise Exception("未来等待失败: Future为空")
    try:
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(fut)
        return loop.run_until_complete(fut)
    except Exception as e:
        raise Exception("未来等待失败: " + str(e))


def 未来等待超时(fut, timeout):
    """等待 Future 完成，超时返回 None"""
    if not fut:
        raise Exception("未来等待超时失败: Future为空")
    try:
        return _asyncio.wait_for(fut, timeout=timeout)
    except _asyncio.TimeoutError:
        return None
    except Exception as e:
        raise Exception("未来等待超时失败: " + str(e))


def 未来添加回调(fut, callback):
    """添加 Future 完成回调"""
    if not fut:
        raise Exception("未来添加回调失败: Future为空")
    if not callable(callback):
        raise Exception("未来添加回调失败: 回调不是可调用对象")
    try:
        fut.add_done_callback(lambda f: callback(f.result()))
        return True
    except Exception as e:
        raise Exception("未来添加回调失败: " + str(e))


def 未来添加错误回调(fut, callback):
    """添加 Future 错误回调"""
    if not fut:
        raise Exception("未来添加错误回调失败: Future为空")
    if not callable(callback):
        raise Exception("未来添加错误回调失败: 回调不是可调用对象")
    try:
        def _err_cb(f):
            if f.exception():
                callback(f.exception())
        fut.add_done_callback(_err_cb)
        return True
    except Exception as e:
        raise Exception("未来添加错误回调失败: " + str(e))


def 未来是否完成(fut):
    """检查 Future 是否完成"""
    if not fut:
        raise Exception("未来是否完成失败: Future为空")
    return fut.done()


def 未来是否失败(fut):
    """检查 Future 是否失败"""
    if not fut:
        raise Exception("未来是否失败失败: Future为空")
    return fut.done() and fut.exception() is not None


def 未来链式调用(fut, callback):
    """链式调用 Future"""
    return 未来添加回调(fut, callback)


def 未来链式回调(fut, callback):
    """链式回调 Future"""
    return 未来添加回调(fut, callback)


def 未来异常处理(fut, err_callback):
    """Future 异常处理"""
    return 未来添加错误回调(fut, err_callback)


def 未来取消(fut):
    """取消 Future"""
    if not fut:
        raise Exception("未来取消失败: Future为空")
    try:
        return fut.cancel()
    except Exception as e:
        raise Exception("未来取消失败: " + str(e))


def 未来获取结果(fut):
    """获取 Future 结果"""
    if not fut:
        raise Exception("未来获取结果失败: Future为空")
    try:
        return fut.result()
    except Exception as e:
        raise Exception("未来获取结果失败: " + str(e))


# =============================================================================
# Promise 相关
# =============================================================================

class _Promise:
    """Promise 封装，桥接 asyncio.Future"""
    def __init__(self):
        self._loop = _asyncio.get_event_loop()
        self._future = self._loop.create_future()
        self._callbacks = []
        self._err_callbacks = []
        self._finally_callbacks = []

    def then(self, on_fulfilled):
        self._callbacks.append(on_fulfilled)
        return self

    def catch(self, on_rejected):
        self._err_callbacks.append(on_rejected)
        return self

    def finally_(self, on_finally):
        self._finally_callbacks.append(on_finally)
        return self


def 创建Promise():
    """创建一个 Promise 对象"""
    try:
        return _Promise()
    except Exception as e:
        raise Exception("创建Promise失败: " + str(e))


def Promise执行(promise, executor):
    """执行 Promise"""
    if not promise:
        raise Exception("Promise执行失败: Promise为空")
    if not callable(executor):
        raise Exception("Promise执行失败: executor不是可调用对象")
    try:
        def resolve(value):
            Promise解决(promise, value)
        def reject(error):
            Promise拒绝(promise, error)
        executor(resolve, reject)
        return promise
    except Exception as e:
        Promise拒绝(promise, e)
        return promise


def Promise解决(promise, value):
    """解决 Promise"""
    if not promise:
        raise Exception("Promise解决失败: Promise为空")
    try:
        if not promise._future.done():
            promise._future.set_result(value)
            for cb in promise._callbacks:
                try:
                    cb(value)
                except Exception:
                    pass
            for cb in promise._finally_callbacks:
                try:
                    cb()
                except Exception:
                    pass
        return True
    except Exception as e:
        raise Exception("Promise解决失败: " + str(e))


def Promise拒绝(promise, reason):
    """拒绝 Promise"""
    if not promise:
        raise Exception("Promise拒绝失败: Promise为空")
    try:
        if not promise._future.done():
            exc = reason if isinstance(reason, Exception) else Exception(str(reason))
            promise._future.set_exception(exc)
            for cb in promise._err_callbacks:
                try:
                    cb(reason)
                except Exception:
                    pass
            for cb in promise._finally_callbacks:
                try:
                    cb()
                except Exception:
                    pass
        return True
    except Exception as e:
        raise Exception("Promise拒绝失败: " + str(e))


def Promise然后(promise, callback):
    """Promise then 链式调用"""
    if not promise:
        raise Exception("Promise然后失败: Promise为空")
    promise._callbacks.append(callback)
    return promise


def Promise捕获(promise, callback):
    """Promise catch 错误处理"""
    if not promise:
        raise Exception("Promise捕获失败: Promise为空")
    promise._err_callbacks.append(callback)
    return promise


def Promise最终(promise, callback):
    """Promise finally 最终处理"""
    if not promise:
        raise Exception("Promise最终失败: Promise为空")
    promise._finally_callbacks.append(callback)
    return promise


def Promise全部(promises):
    """等待所有 Promise 完成"""
    if not promises:
        raise Exception("Promise全部失败: promises为空")
    try:
        futures = [p._future for p in promises]
        loop = _asyncio.get_event_loop()
        results = loop.run_until_complete(_asyncio.gather(*futures, return_exceptions=True))
        return results
    except Exception as e:
        raise Exception("Promise全部失败: " + str(e))


def Promise竞速(promises):
    """Promise 竞速，返回第一个完成的"""
    if not promises:
        raise Exception("Promise竞速失败: promises为空")
    try:
        futures = [p._future for p in promises]
        loop = _asyncio.get_event_loop()
        done, _ = loop.run_until_complete(_asyncio.wait(futures, return_when=_asyncio.FIRST_COMPLETED))
        for fut in done:
            return fut.result()
        return None
    except Exception as e:
        raise Exception("Promise竞速失败: " + str(e))


def Promise全部完成(promises):
    """等待所有 Promise 完成（忽略错误）"""
    return Promise全部(promises)


def Promise任意(promises):
    """Promise 任意一个完成"""
    return Promise竞速(promises)


def Promise解决已完成(value):
    """返回一个已解决的 Promise"""
    try:
        p = _Promise()
        p._future.set_result(value)
        return p
    except Exception as e:
        raise Exception("Promise解决已完成失败: " + str(e))


def Promise拒绝已完成(reason):
    """返回一个已拒绝的 Promise"""
    try:
        p = _Promise()
        exc = reason if isinstance(reason, Exception) else Exception(str(reason))
        p._future.set_exception(exc)
        return p
    except Exception as e:
        raise Exception("Promise拒绝已完成失败: " + str(e))


# =============================================================================
# 事件循环管理
# =============================================================================

_事件循环实例 = None


def 创建事件循环():
    """创建新的事件循环"""
    global _事件循环实例
    try:
        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)
        _事件循环实例 = loop
        return loop
    except Exception as e:
        raise Exception("创建事件循环失败: " + str(e))


def 事件循环运行(loop):
    """运行事件循环"""
    if not loop:
        raise Exception("事件循环运行失败: 事件循环为空")
    try:
        loop.run_forever()
    except Exception as e:
        raise Exception("事件循环运行失败: " + str(e))


def 事件循环运行单次(loop):
    """运行事件循环单次迭代"""
    if not loop:
        raise Exception("事件循环运行单次失败: 事件循环为空")
    try:
        loop.call_soon(loop.stop)
        loop.run_forever()
        return True
    except Exception as e:
        raise Exception("事件循环运行单次失败: " + str(e))


def 事件循环停止(loop):
    """停止事件循环"""
    if not loop:
        raise Exception("事件循环停止失败: 事件循环为空")
    try:
        loop.stop()
        return True
    except Exception:
        return False


def 事件循环暂停(loop):
    """暂停事件循环"""
    if not loop:
        raise Exception("事件循环暂停失败: 事件循环为空")
    try:
        loop.stop()
        return True
    except Exception:
        return False


def 事件循环恢复(loop):
    """恢复事件循环"""
    if not loop:
        raise Exception("事件循环恢复失败: 事件循环为空")
    try:
        if not loop.is_running():
            _threading.Thread(target=loop.run_forever, daemon=True).start()
        return True
    except Exception as e:
        raise Exception("事件循环恢复失败: " + str(e))


def 事件循环是否运行中(loop):
    """检查事件循环是否运行中"""
    if not loop:
        return False
    return loop.is_running()


def 事件循环设置超时(loop, delay, callback):
    """设置超时定时器"""
    if not loop:
        raise Exception("事件循环设置超时失败: 事件循环为空")
    if not callable(callback):
        raise Exception("事件循环设置超时失败: 回调不是可调用对象")
    try:
        return loop.call_later(delay, callback)
    except Exception as e:
        raise Exception("事件循环设置超时失败: " + str(e))


def 事件循环设置间隔(loop, interval, callback):
    """设置间隔定时器"""
    if not loop:
        raise Exception("事件循环设置间隔失败: 事件循环为空")
    if not callable(callback):
        raise Exception("事件循环设置间隔失败: 回调不是可调用对象")
    try:
        def _repeat():
            callback()
            loop.call_later(interval, _repeat)
        return loop.call_later(interval, _repeat)
    except Exception as e:
        raise Exception("事件循环设置间隔失败: " + str(e))


def 事件循环清除定时器(loop, timer_handle):
    """清除定时器"""
    if not loop:
        raise Exception("事件循环清除定时器失败: 事件循环为空")
    if not timer_handle:
        return False
    try:
        timer_handle.cancel()
        return True
    except Exception:
        return False


def 事件循环清除间隔(loop, interval_handle):
    """清除间隔定时器"""
    return 事件循环清除定时器(loop, interval_handle)


def 事件循环立即执行(loop, callback):
    """立即执行回调"""
    if not loop:
        raise Exception("事件循环立即执行失败: 事件循环为空")
    if not callable(callback):
        raise Exception("事件循环立即执行失败: 回调不是可调用对象")
    try:
        loop.call_soon(callback)
        return True
    except Exception as e:
        raise Exception("事件循环立即执行失败: " + str(e))


def 事件循环创建任务(loop, coro):
    """在事件循环中创建任务"""
    if not loop:
        raise Exception("事件循环创建任务失败: 事件循环为空")
    if not coro:
        raise Exception("事件循环创建任务失败: 协程为空")
    try:
        return loop.create_task(coro)
    except Exception as e:
        raise Exception("事件循环创建任务失败: " + str(e))


def 事件循环任务执行器(loop, func, *args):
    """在事件循环中执行任务"""
    if not loop:
        raise Exception("事件循环任务执行器失败: 事件循环为空")
    if not callable(func):
        raise Exception("事件循环任务执行器失败: 函数不是可调用对象")
    try:
        return loop.run_in_executor(None, func, *args)
    except Exception as e:
        raise Exception("事件循环任务执行器失败: " + str(e))


def 异步任务等待(task):
    """等待异步任务完成"""
    if not task:
        raise Exception("异步任务等待失败: 任务为空")
    try:
        loop = _asyncio.get_event_loop()
        return loop.run_until_complete(task)
    except Exception as e:
        raise Exception("异步任务等待失败: " + str(e))


def 异步任务取消(task):
    """取消异步任务"""
    if not task:
        raise Exception("异步任务取消失败: 任务为空")
    try:
        return task.cancel()
    except Exception as e:
        raise Exception("异步任务取消失败: " + str(e))


def 事件循环等待所有(loop, tasks):
    """等待所有任务完成"""
    if not loop:
        raise Exception("事件循环等待所有失败: 事件循环为空")
    if not tasks:
        raise Exception("事件循环等待所有失败: 任务列表为空")
    try:
        return loop.run_until_complete(_asyncio.gather(*tasks, return_exceptions=True))
    except Exception as e:
        raise Exception("事件循环等待所有失败: " + str(e))


def 事件循环等待任意(loop, tasks):
    """等待任意任务完成"""
    if not loop:
        raise Exception("事件循环等待任意失败: 事件循环为空")
    if not tasks:
        raise Exception("事件循环等待任意失败: 任务列表为空")
    try:
        done, pending = loop.run_until_complete(
            _asyncio.wait(tasks, return_when=_asyncio.FIRST_COMPLETED)
        )
        return list(done)
    except Exception as e:
        raise Exception("事件循环等待任意失败: " + str(e))


def 事件循环注册输入输出(loop, fd, callback):
    """注册 IO 输入输出监听"""
    if not loop:
        raise Exception("事件循环注册输入输出失败: 事件循环为空")
    try:
        loop.add_reader(fd, callback)
        return True
    except Exception as e:
        raise Exception("事件循环注册输入输出失败: " + str(e))


def 事件循环注销输入输出(loop, fd):
    """注销 IO 输入输出监听"""
    if not loop:
        raise Exception("事件循环注销输入输出失败: 事件循环为空")
    try:
        loop.remove_reader(fd)
        loop.remove_writer(fd)
        return True
    except Exception as e:
        raise Exception("事件循环注销输入输出失败: " + str(e))


def 事件循环输入输出轮询(loop, timeout=None):
    """IO 轮询"""
    if not loop:
        raise Exception("事件循环输入输出轮询失败: 事件循环为空")
    try:
        loop._run_once()
        return True
    except Exception as e:
        raise Exception("事件循环输入输出轮询失败: " + str(e))


def 事件循环睡眠(loop, seconds):
    """事件循环睡眠"""
    if not loop:
        raise Exception("事件循环睡眠失败: 事件循环为空")
    try:
        loop.run_until_complete(_asyncio.sleep(seconds))
        return True
    except Exception as e:
        raise Exception("事件循环睡眠失败: " + str(e))


def 事件循环睡眠回调(loop, seconds, callback):
    """睡眠后执行回调"""
    if not loop:
        raise Exception("事件循环睡眠回调失败: 事件循环为空")
    if not callable(callback):
        raise Exception("事件循环睡眠回调失败: 回调不是可调用对象")
    try:
        loop.call_later(seconds, callback)
        return True
    except Exception as e:
        raise Exception("事件循环睡眠回调失败: " + str(e))


def 事件循环延迟(loop, seconds):
    """事件循环延迟"""
    return 事件循环睡眠(loop, seconds)


def 事件循环获取统计(loop):
    """获取事件循环统计信息"""
    if not loop:
        raise Exception("事件循环获取统计失败: 事件循环为空")
    try:
        return {
            'running': loop.is_running(),
            'closed': loop.is_closed(),
            'debug': loop.get_debug(),
        }
    except Exception as e:
        raise Exception("事件循环获取统计失败: " + str(e))


# =============================================================================
# 异步 I/O 操作
# =============================================================================

async def 异步读取文件(路径):
    """异步读取文件内容"""
    import aiofiles
    try:
        async with aiofiles.open(路径, 'r', encoding='utf-8') as 文件:
            return await 文件.read()
    except ImportError:
        # 备选方案：使用 asyncio 的 run_in_executor
        loop = _asyncio.get_event_loop()
        def _read():
            with open(路径, 'r', encoding='utf-8') as f:
                return f.read()
        return await loop.run_in_executor(None, _read)
    except Exception as e:
        raise Exception(f"异步读取文件失败: {str(e)}")


async def 异步写入文件(路径, 内容):
    """异步写入文件内容"""
    import aiofiles
    try:
        async with aiofiles.open(路径, 'w', encoding='utf-8') as 文件:
            await 文件.write(内容)
            return True
    except ImportError:
        loop = _asyncio.get_event_loop()
        def _write():
            with open(路径, 'w', encoding='utf-8') as f:
                f.write(内容)
            return True
        return await loop.run_in_executor(None, _write)
    except Exception as e:
        raise Exception(f"异步写入文件失败: {str(e)}")


async def 异步追加文件(路径, 内容):
    """异步追加文件内容"""
    import aiofiles
    try:
        async with aiofiles.open(路径, 'a', encoding='utf-8') as 文件:
            await 文件.write(内容)
            return True
    except ImportError:
        loop = _asyncio.get_event_loop()
        def _append():
            with open(路径, 'a', encoding='utf-8') as f:
                f.write(内容)
            return True
        return await loop.run_in_executor(None, _append)
    except Exception as e:
        raise Exception(f"异步追加文件失败: {str(e)}")


async def 异步读取二进制(路径):
    """异步读取二进制文件"""
    import aiofiles
    try:
        async with aiofiles.open(路径, 'rb') as 文件:
            return await 文件.read()
    except ImportError:
        loop = _asyncio.get_event_loop()
        def _read():
            with open(路径, 'rb') as f:
                return f.read()
        return await loop.run_in_executor(None, _read)
    except Exception as e:
        raise Exception(f"异步读取二进制失败: {str(e)}")


async def 异步写入二进制(路径, 数据):
    """异步写入二进制文件"""
    import aiofiles
    try:
        async with aiofiles.open(路径, 'wb') as 文件:
            await 文件.write(数据)
            return True
    except ImportError:
        loop = _asyncio.get_event_loop()
        def _write():
            with open(路径, 'wb') as f:
                f.write(数据)
            return True
        return await loop.run_in_executor(None, _write)
    except Exception as e:
        raise Exception(f"异步写入二进制失败: {str(e)}")


async def 异步HTTP获取(url):
    """异步 HTTP GET 请求"""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as 会话:
            async with 会话.get(url) as 响应:
                return await 响应.text()
    except ImportError:
        import urllib.request
        loop = _asyncio.get_event_loop()
        def _get():
            with urllib.request.urlopen(url) as resp:
                return resp.read().decode('utf-8')
        return await loop.run_in_executor(None, _get)
    except Exception as e:
        raise Exception(f"异步HTTP获取失败: {str(e)}")


async def 异步睡眠(秒数):
    """异步睡眠"""
    await _asyncio.sleep(秒数)
    return True