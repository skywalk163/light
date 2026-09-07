# 段言 v6.3.0 发布检查清单

> 版本: 6.3.0  
> 日期: 2026-08-07  
> 负责人: [填写负责人姓名]

---

## 1. 版本号校验

- [ ] **pyproject.toml**: 确认 `version = "6.3.0"`
- [ ] **cli/duan_unified.py**: 确认 `--version` 输出 `段言 v6.3.0`
- [ ] **vscode-extension/extension.js**: 确认 `EXTENSION_VERSION = '6.3.0'`
- [ ] **CHANGELOG.md**: 确认 v6.3.0 条目完整且格式正确
- [ ] 所有版本号一致，无残留的旧版本号

## 2. 测试套件验证

- [ ] 全量回归测试通过
  ```
  python -m pytest tests/ -q --tb=short
  ```
- [ ] E2E 测试全部通过
  ```
  python -m pytest tests/e2e/ -q --tb=short
  ```
- [ ] 自举编译器验证通过
  ```
  python -m pytest tests/test_self_host_bootstrap.py -q --tb=short
  ```
- [ ] 全链路覆盖测试通过
  ```
  python -m pytest tests/test_e2e_full_coverage.py -q --tb=short
  ```

### 测试结果记录

| 指标 | 数值 |
|------|------|
| 通过 | 2576 |
| 失败 | 7（pre-existing：stdlib HTTP 模块问题） |
| 跳过 | 52 |
| 总测试数 | 2635 |

> **注意**: 7 个测试失败均为 `test_stdlib_phase3.py::Test网络请求` 中的 `urllib.request.HttpResponse` 属性缺失问题，非本次发布引入，已在 Issue 中追踪。

## 3. CHANGELOG 验证

- [ ] 新增内容完整性：100% 自举编译器、AI 工具链、生态拓展、社区推广、全链路测试
- [ ] 版本变更记录：6.2.1 → 6.3.0
- [ ] 格式符合 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) 规范
- [ ] 日期正确（2026-08-07）

## 4. 示例程序验证

- [ ] 所有示例程序可成功运行
  ```
  python -m cli.duan_unified run examples/calculator_app/主.duan
  python -m cli.duan_unified run examples/file_search/主.duan
  python -m cli.duan_unified run examples/hello.duan
  ```
- [ ] 示例程序可成功编译为 Python 产物
  ```
  python -m cli.duan_unified compile examples/hello.duan
  ```

## 5. 文档验证

- [ ] CONTRIBUTING.md 已更新（含 PR 检查清单、代码审查指南、翻译贡献指南等）
- [ ] README.md 版本号与 v6.3.0 一致
- [ ] 文档站内容与最新版本同步

## 6. 发布步骤

### 6.1 代码合入

- [ ] 确认所有 PR 已合入 `main` 分支
- [ ] 确认 `main` 分支为最新状态
  ```bash
  git checkout main
  git pull origin main
  ```

### 6.2 创建 Release Tag

- [ ] 创建 Git Tag
  ```bash
  git tag -a v6.3.0 -m "段言 v6.3.0 - 100% 自举编译器达成"
  git push origin v6.3.0
  ```

### 6.3 发布到 PyPI

- [ ] 构建分发包
  ```bash
  python -m build
  ```
- [ ] 上传到 PyPI
  ```bash
  python -m twine upload dist/duan-6.3.0*
  ```
- [ ] 验证 PyPI 安装
  ```bash
  pip install duan==6.3.0
  python -m cli.duan_unified --version
  ```

### 6.4 发布 VS Code 扩展

- [ ] 更新 `vscode-extension/package.json` 版本号（如未同步）
- [ ] 打包扩展
  ```bash
  cd vscode-extension
  vsce package
  ```
- [ ] 上传到 VS Code Marketplace

### 6.5 GitHub Release

- [ ] 在 GitHub 上创建 Release
  - Tag: `v6.3.0`
  - 标题: `段言 v6.3.0 - 100% 自举编译器达成`
  - 内容: 复制 CHANGELOG.md 中 v6.3.0 条目内容
- [ ] 上传 PyPI 分发包到 Release Assets

## 7. 发布后检查

- [ ] 验证 PyPI 页面显示正确版本号
- [ ] 验证 GitHub Release 页面显示正确
- [ ] 验证文档站更新（如自动部署）
- [ ] 在社区渠道发布版本更新通知
  - GitHub Discussions
  - 微信群
  - 其他社区渠道

## 8. 回滚计划

如发布后发现严重问题，执行以下回滚步骤：

1. **PyPI**: 告知用户回退到上一版本
   ```bash
   pip install duan==6.2.1
   ```
2. **Git Tag**: 删除已发布的 Tag（如有必要）
   ```bash
   git push --delete origin v6.3.0
   git tag -d v6.3.0
   ```
3. **GitHub Release**: 在 Release 页面标记为 "Pre-release" 或删除

---

## 签署确认

| 检查项 | 签名 | 日期 |
|--------|------|------|
| 版本号校验 | | |
| 测试套件验证 | | |
| CHANGELOG 验证 | | |
| 示例程序验证 | | |
| 文档验证 | | |
| 发布执行 | | |
| 发布后检查 | | |