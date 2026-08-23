# 任务 C4：非阻塞传输层与 selector（真异步的前置）

> **前置必读**：`第四轮总纲.md`（尤其 §1.1 M7 三重判据、§4.2 签名冻结、§5.1 不许断字符串）
> **独占文件**：`stdlib/流式.light`、`stdlib/SSE.light`、新建 `stdlib/选择器.light`、
> `tests/test_stream_light.py`、`tests/test_sse_light.py`、新建 `tests/test_stream_async_light.py`、
> `tests/test_async.py`
> **越界即停**：不碰 `src/`、不碰 `大模型客户端.light`、不碰 `代理循环.light`。
> 发现语言缺陷写移交清单，不许改 `src/`。

---

## 0. 你要解决的第一性问题

我们的「异步」在业务链路上**一个 await 点都没有**。语言侧是真的
（`异步 运行 主()。` → `asyncio.run`，`并发等待` → `asyncio.gather`），
但传输层是阻塞 socket，任何 asyncio 包装都会堵在 `recv` 上把 event loop 停掉。

`stdlib/代理循环.light:377-384` 的注释已经把结论写明白了：
「要真异步必须先让 流式.light 走非阻塞 socket + selector」。**这一步就是你。**

**注意：解析层不用动。** `流式.light:118-140 read_body`、`:224-247 读分块`、
`:144-174 按行读取` 都是真增量实现（跨块行缓冲、增量 UTF-8 解码器、三种行尾）。
你要改的**只有 I/O 层**：谁去等 fd、怎么等。

---

## 1. 现状定位（已复核，别再重复排查）

- `流式.light:73-74` 建 socket 后 `s.settimeout(己.超时连接)`
- `流式.light:81` 连上后 `s.settimeout(己.超时读取)`
- `流式.light:250-256` 唯一读原语 `段落 收` = 裸 `s.recv(大小)`，异常包成 `读取错误`
- 全 stdlib grep `selector|epoll|setblocking` → `流式.light` 只命中两处 `settimeout`
- 已有但未接的现成件：`stdlib/lightpub/Socket.py:194-198 设置非阻塞`、
  `stdlib/lightpub/__index__.py:260 select读写(...)`、`stdlib/lightpub/协程.py:432-478`
  （channel 级 select，**不是 fd 级 I/O 多路复用**，别误用）
- `stdlib/lightpub/异步运行时.py:746-747` 的「异步 HTTP」是 `urllib.request.urlopen` 包在 executor 里，
  **不是真异步 I/O**，不要参照它

---

## 2. C4-1：新建 `stdlib/选择器.light`（fd 级多路复用）

纯光明实现，`导入 selectors` 是允许的（`引 Python` 才是禁的，stdlib 计数必须保持 0）。

要导出的能力，至少：

- `新建 选择器()`
- `注册(fd_或_socket, 事件)` —— 事件取 `"读"` / `"写"` / `"读写"`
- `注销(fd_或_socket)`
- `等待(超时秒)` → 返回就绪列表；超时返回空列表**而不是抛异常**
- `关闭()`

**判据 C4-1**：
1. 用一对 `socketpair`（或 127.0.0.1 + `bind(0)` 的自连接）注册读事件，
   未写入时 `等待(0.05)` 返回**空列表**；写入后 `等待(1.0)` 返回**含该 fd 的列表**。
2. 注销后再 `等待` 不再返回该 fd。
3. **反跑**：把 `等待` 的超时参数忽略掉（写死 None），用例必须变红（会挂死或超时失败）。

---

## 3. C4-2：`流式.light` 的非阻塞读路径

**签名冻结（总纲 §4.2）**：`创建/连接/请求/read_body/按行读取/收/关闭` 的签名与语义**一律不变**。
新增能力走新名字。

要做的：

1. 连接建立后 `s.setblocking(False)`（或等价），把「等数据」这件事交给选择器。
2. `收` 的内部改为「selector 等 → recv → 处理 EAGAIN/EWOULDBLOCK 重试」。
   **注意跨平台 errno**：第二轮踩过一次「EAGAIN 数值不跨平台」（见 `5e5943ca` 提交）。
   用 `errno.EAGAIN` / `errno.EWOULDBLOCK` 常量，别写数字。
3. TLS 路径要单独处理：`ssl` 包过的 socket 在非阻塞下会抛
   `ssl.SSLWantReadError` / `SSLWantWriteError`，**必须按 want-read/want-write 分别回到选择器等对应事件**，
   不许把它们当普通错误吞掉或当 EAGAIN 一律等读。这条是 TLS + 非阻塞最容易错的地方。
4. 超时语义不许退化：原来 `settimeout(己.超时读取)` 的效果要由「选择器累计等待时间」等价实现，
   超时后仍抛既有的 `读取错误`。

**判据 C4-3（回归不许破）**：改完之后
`tests/test_llm_client_light.py` 与 `tests/test_tls_light.py` **一行都不许动**还能全绿。
这是签名冻结的机读证明。交付报告贴这两个文件的汇总行。

---

## 4. C4-3：M7 的三重判据（本轮硬目标）

新建 `tests/test_stream_async_light.py`，**同一份用例里跑两种模式**：

1. **结构判据**：断言 `流式.light` 的读路径经过选择器
   （允许用「实现里能观察到的行为」而不是 grep 源码；若只能 grep，就 grep 并说明为什么）。
2. **时序判据**：起两个 mock server，各在响应前故意 `sleep(0.5)`：
   - 串行跑两条 → 总耗时 **> 1.0s**
   - 并发跑两条（`并发等待` 或选择器同时等两个 fd）→ 总耗时 **< 0.8s**
   - **断言的是两者的关系，不是单个绝对值**（绝对值在慢机器上会飘）
3. **反跑判据**：把非阻塞那一步改回阻塞，**用例必须变红**。
   交付报告里贴改坏前后的两份实测输出——总纲 §9.3 硬要求。

**不许**用 `assert 'selectors' in source` 这类断字符串式判据充当上面任何一条。

---

## 5. C4-4：清算 `tests/test_async.py` 的假绿

这个文件是全仓最大的一片假绿区。已定位：

| 行号 | 形态 | 怎么改 |
|---|---|---|
| `:88` | 断 `'async def 异步任务' in code` | 改成跑产物，断行为（协程真被 await、返回值对） |
| `:295-317` | **空断言**（`for stmt in ...: pass`） | 要么补真断言，要么删掉并在报告里说明 |
| `:319-343` | `assert isinstance(...) or True` **永真** | 去掉 `or True`，让它真断 |
| `:531-548` | 唯一真跑的 async 用例，跑的是**手写 Python** | 改成跑光明产物 |
| `:573` | 断 `'async for' in py_code` | 改成跑产物断迭代结果 |
| `:659-660` | 断 `'asyncio.gather' in py_code` | 改成断「两个任务真并发」（时序或副作用顺序） |
| `:390` | `assert len(x) >= N` 下界断言 | 改成精确断言 |

**口径**：改成行为断言之后，`assert '<字符串>' in py_code` 这一类**一条都不许留在本文件**。
D4 本轮会把这类形态加进门禁基线，你留一条就要进基线一条。

**允许的例外**：确实只能验证「生成了正确的语法结构」而无法跑（比如需要外部服务），
那就明确 xfail 并写「掩盖了什么」——但总纲 §5.3 说了，xfail 必须对应总纲里的条目，
本轮没给 `test_async` 开 xfail 额度，所以基本上你得让它们真跑。

---

## 6. 边界与已知坑

- **不许改 `SSE.light` 的分帧语义**。它现在是对的（`:35-43 喂入` 增量、`:55-80 拆行` 留尾、
  `:97-98` 空行才产帧），`tests/test_sse_light.py` 覆盖了跨 chunk 断行、切在多字节 UTF-8 中间、
  CR/CRLF/混合行尾。你可以给它加用例，不许改它的行为。
- **端口一律 `bind(("127.0.0.1", 0))`**。写死端口在 `-n auto` 下会被抢（`test_tls_light.py:98-102` 记着这个坑）。
- **mock server 要真 HTTP/1.1**。第三轮的教训：伪造分帧能骗过自己写的解析器。
- 临时文件前缀 `_taskC4_`，收尾删干净。
- `stdlib` 里 `引 Python` 计数必须保持 **0**（`导入 selectors` / `导入 errno` 不算，那是 `导入`）。

---

## 7. 交付格式

按总纲 §9 六项。本任务特别要求：

- **§9.3 反跑证明是硬要求**：C4-1、C4-2、C4-3 每条都要贴「改坏 → 变红」的实测输出。
  这三条只要有一条是「一次就绿且没反跑」，整个交付按未验证退回。
- 时序判据的实测数字要贴原始输出（串行 X.XXs / 并发 Y.YYs），不许只写「符合预期」。
- POSIX 未实测的分支明确标注——你大概只有 Windows，TLS 非阻塞在 POSIX 上的
  want-read/want-write 行为差异要写进未实测项。
