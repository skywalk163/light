# T-0234 · light 让 GitHub CI 真正跑起来

**结论：工作流已修正并可在 GitHub 真实触发；但「徽章为绿」被仓库态测试失败阻塞，非本卡 paths 可修。**

## 做了什么（只改 `.github/workflows/ci.yml`）

- 文件头改为真实状态：GitHub 远端 `skywalk163/light` 已启用，本工作流随 push main / PR / 手动触发真跑；权威门禁仍是 `.gitea/workflows/ci.yml`。
- 修正必红路径：lightpub 文档可导入性闸门 `tests/unit/test_lightpub_doc_importability.py` → `tests/lightpub/test_lightpub_doc_importability.py`（R125 测试分仓迁移 424d07253；旧路径 pytest exit 4，每次必红）。
- 「计时起点」移到 `actions/setup-python` 之后：干净 runner 上 `python` 由 setup-python 写入 PATH，原位置可能第一步就红。
- 与权威副本对齐判绿语义：PR 通过 `PYTEST_ADDOPTS=-m "not slow"` 跳过 slow（e2e/大项目），时间预算放宽到 PR 1800s / push 3000s；补 `floor_bootstrap.py` / `native_product.py` / `dist_criteria.py` 三道 G9 门禁。
- 增加 `permissions: contents: read` 与 PR 并发取消，减少排队与权限面。

## 验证

- 卡面 verify：`test -f .github/workflows/ci.yml`（本机无 POSIX `test`，用 PowerShell `Test-Path` / Python `os.path.isfile` 等价校验通过）。
- `actionlint` v1.7.7：**exit 0**；PyYAML 解析通过，jobs = `test/lint/build/exe`。
- 静态门禁本地预跑：`floor_bootstrap` / `dist_criteria` / `assert_floor_manifest` 通过；`native_product` 在 Windows 本机 24.19% < 基线 24.39%（Linux runner 预期与 FreeBSD 权威一致）。
- 真实运行证据：GitHub Actions 已在跑（run `41289797116`，2026-11-01），失败点是 **Unit Tests：12 failed + 7 errors**，不是工作流语法/触发问题。

## 阻塞与残留

- 徽章无法转绿：10 条仓库态测试失败（本地复跑 `test_地板搬迁_判型_S2.py` 同签名 3 failed 可复现）；7 errors 来自 sibling `lightharness` 缺失。这些文件都不在允许 paths 内。
- 已试过把 `skywalk163/lightharness` main 浅克隆为 sibling 验证：7 errors 消失，但仍 3 failed（LH 副本形参名未同步），故没有把跨仓 clone 写进 CI 硬依赖。
- README 首页徽章仍是 `docs/ci_badge.svg` 本地生成图，不是 Actions badge；README 不在允许 paths 内。
- 未 push / 未触发 PR；按卡规则只提交到 `task/T-0234`，由 `hive_submit` 推送。`native_product` 门禁在 Linux 上未实测，存在与 Windows 本机同样偏低的风险。
