# R160-A 追加任务文本 —— 收口 new_reds=6 中的 #3~#6：native 协程连带回归处置

> 本文件是派给 A 线的追加任务（自包含）。权威背景见 `light-merge/_R160_收口报告.md` §2.1 +
> `docs/功能对标/语言缺陷账.md` §二十（L-227/L-228）。**未 commit / 未 push / 不做任何 git 写操作。**
> 工作目录：`G:\dswork\duan-light-merge\light-merge`。
>
> **背景**：R160 你对 L-219 的修复已在本机 + 0.82 权威验证两子缺陷全绿（协程四档含 R159 L1 红
> `协程-0` 转绿 + 自绑 resume 后不崩）。但 R160 收口 L1 0.82 全量门 **new_reds=6**——主 agent 已快修
> 其中 **#1**（运行时符号清单补 `dv_coro_create_bound`/`dv_coro_self_writeback`）与 **#2**（stdlib 模块表
> 补 `协程`），本机已复跑转绿。**剩余 #3~#6 交你处置。**
>
> **业主裁定（2026-10-19，先于本任务）**：**L-227/L-228 排入 R161（A 线修 codegen/runtime）**。
> ⇒ #3~#6 中任何一条只要坐实属 L-227/L-228 家族（HEAD 纯树可复现），R160 **不修**、登记为 R161
> 输入；只有确证「你 R160-A 引入且非 L-227/L-228 家族」才在 R160 修。#3/#4 当前疑点直接指向你的
> `_gen_async_method`/self 写回，优先做纯树对照。

## 你的任务：逐条定位 #3~#6，给出「修 / 定位登记 / 判 flaky」结论

### #3 #4 · `tests/unit/test_R143_L198_嵌套异步写实例.py::test_P2_嵌套方法写属性_读9` / `test_P3_嵌套方法写新属性_读9`
- **现象**：R143 为已关闭缺陷 L-198（判定为命名碰撞假象）建的回归门，断言「嵌套异步方法写实例后再读 = 9」；R160-A 后 0.82 复跑红。疑你 `_gen_async_method` / `dv_coro_self_writeback` 改变了类内异步方法的 self 写回 / 帧语义。
- **步骤**：① 本机复现（`.venv/Scripts/python.exe -m pytest tests/unit/test_R143_L198_嵌套异步写实例.py -p no:cacheprovider -q`，贴 rc + 实际读值）；② `git stash` 把你的 `src/llvm/codegen_typed.py`+`runtime_typed.c` 还原到 `335b6c742` 复跑，确认真伪归属（HEAD 纯树应绿 ⇒ 你引入；HEAD 纯树也红 ⇒ pre-existing，按业主裁定登记 R161）。
- **处置**：确证你引入且非 L-227/L-228 家族 ⇒ **必须修**（最小侵入）。改后本机 + 0.82 双复跑该门，并**重跑 `test_R160_L219_协程恢复.py` 确认不回退**（2 passed 保持）。pre-existing ⇒ 登记归因证据转 R161，不修。

### #5 #6 · `tests/unit/test_R143_L200_模板嵌套键.py::test_双腿对拍dict项一致` / `tests/unit/test_R140_L182_L191_原生腿.py::test_L191_节点作被导入模块_顶层段名不再串作用域`
- **现象**：两条均在 0.82 **Timeout >60s**（非 assert 失败）。疑 R160-A 的 codegen 改动（`_gen_async_method` / self 绑定 / 事件循环 `continue`）使 native 编译或运行变慢，或撞 L-228（协程帧局部非持久 → 挂死）——`节点` 正是多函数大模块 + worker 心跳协程（`创建任务`+共享参数），与 L-227-b/L-228 签名高度吻合。
- **业主裁定（2026-10-19）**：**L-227/L-228 排入 R161（A 线修 codegen/runtime）** ⇒ 若 #5/#6 坐实为该家族，**R160 不修**，登记为 R161 输入即可；只有确证「你 R160-A 引入且非 L-227/L-228 家族」才在 R160 修。
- **步骤**：① 本机单独复跑各条（贴 rc + 用时；可能本机不慢，0.82 并行下 60s 偏紧）；② `git stash` 到 `335b6c742` 在 **0.82** 复跑对照——纯树也超时 ⇒ pre-existing（L-227/L-228 家族），登记 R161；纯树绿、你的改动红 ⇒ 你引入的回归，按下方处置。
- **处置**：确证你引入且非 L-227/L-228 家族 ⇒ 修（编译膨胀找 codegen 放大点；运行期挂死挖根因）；判 L-227/L-228 家族 ⇒ **不修**，写归因证据（0.82 纯树对照 + 签名）回主 agent，转 R161；判 flaky ⇒ 写明抖动率 + 复现条件，交主 agent 裁是否上调 timeout（**不准自己静默改 timeout/改断言**）。

## 附带：E-5 native 腿阻塞的测试侧设计（业主已裁定，知悉即可）
- `tests/unit/test_R160_E5协程库.py` 的 `_native_或_已知阻塞` 仅在命中已知签名（`does not dominate all uses` / `use of undefined value '@_seg_` / 超时 / 已知崩溃码）时 xfail；R161 修了 L-227/L-228 后**该文件无需改动、自动转正常断言**。你 R161 修完三个最小复现（C 段②报告 §5.1-5.3）即自动验证。

## 红线与判据
- **红线**：不 commit / 不 push / 不做 git 写；只改 `src/llvm/**`（若判定要修）+ 必要新回归门；禁 `git add .`（须逐文件）。
- **判绿**：#3/#4 修后本机 + 0.82 双绿（或纯树对照 pre-existing 登记 R161）；#5/#6 要么转绿、要么给出 0.82 HEAD-纯树对照的 pre-existing/flaky 证据；**L-219 两子缺陷不得回退**（`test_R160_L219_协程恢复.py` 2 passed 保持）。
- **新发现**：若定位到新根因，登记（L 编号从 **L-229** 起，立号前先 grep），不擅自扩 scope。

## 铁律（派单提示词已含，须逐条遵守）
1. 先加载技能：`light-llvm-backend-gap-closure` + `light-language-pitfalls`。
2. 汇报必须含真实命令与退出码；没跑的写「未跑」，禁止为凑数改数据 / 改测试期望。
3. 完成后 **SendMessage 给 main**（附 test 输出 / 报告路径 / 一句话结论）；阻塞也发（原因）。
4. 只改红线指定落点；判绿以 **0.82 权威 + 0.86 Linux** 为准，本机只初筛；本机 pytest 用 `G:\dswork\duan-light-merge\light-merge\.venv\Scripts\python.exe`，远端登录一律 `ai` 账号。
5. **新写测试一律顶层 `assert`、禁 `try/except` 吞断言**（R160 假绿门教训，坑 12；`字段`/`创建实例` 是错关键字，正确的是 `设 X 等于` / `新建 类名()`）。
