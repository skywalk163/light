# 段言（DuanLang）发布检查清单

> 版本：1.0 | 最后更新：2026-08-07

---

## 1. 代码质量检查

### 1.1 编译器核心

- [ ] 所有 `.duan` 示例文件能通过 `duan run` 正常运行
- [ ] SRC 后端编译通过（`python -m cli.duan_unified compile --backend src`）
- [ ] ANTLR 后端编译通过（`python -m cli.duan_unified compile --backend antlr`）
- [ ] REPL 模式正常启动并执行语句
- [ ] 回归测试全部通过（`python -m pytest tests/` 或 `python examples/test_all_examples.py`）
- [ ] 无新引入的 Python 语法错误或 ImportError
- [ ] 代码风格符合规范（`flake8` / `pylint` 无新增警告）

### 1.2 打包工具

- [ ] `tools/packager/build_example.py` 可正常运行
- [ ] SRC 后端打包成功（`python tools/packager/build_example.py --backend src`）
- [ ] 生成的 `.bat` / shell 包装脚本可执行
- [ ] 生成的 `.py` 文件无语法错误
- [ ] LLVM 后端至少生成 LLVM IR（`python tools/packager/build_example.py --backend llvm`）
- [ ] 输出目录结构符合预期

### 1.3 安装包构建

- [ ] Windows Inno Setup 脚本编译通过（`ISCC.exe tools/installer/windows/setup.iss`）
- [ ] macOS `.pkg` 构建脚本可运行（`bash tools/installer/macos/build_pkg.sh`）
- [ ] Linux `.deb` 构建脚本可运行（`bash tools/installer/linux/build_deb.sh`）

---

## 2. 文档检查

### 2.1 用户文档

- [ ] `README.md` 中的版本号已更新
- [ ] `docs/一键安装包方案.md` 中的版本号已更新
- [ ] 示例 README 中的运行命令已验证正确
- [ ] CLI `--help` 输出信息完整准确
- [ ] API 文档或使用说明已更新（如有变更）

### 2.2 打包与发布文档

- [ ] `RELEASE_CHECKLIST.md` 检查项全部确认
- [ ] 发布说明（Release Notes）已起草
- [ ] CHANGELOG 已更新（如有）

---

## 3. 打包检查

### 3.1 示例工具打包

- [ ] 所有已配置的示例项目入口文件存在
- [ ] 所有附加文件（README.md、sample_data.csv 等）存在
- [ ] SRC 后端：编译后的 `.py` 文件内容完整
- [ ] SRC 后端：包装脚本能正确调用 Python 解释器
- [ ] 输出目录结构正确：

```
output/
  示例名称/
    示例名称.bat（或 示例名称）  # 可执行包装脚本
    示例名称.py                   # 编译后的 Python 代码
    README.md
    sample_data.csv（如有）
```

### 3.2 安装包构建

- [ ] 安装包版本号一致（pyproject.toml / setup.iss / 构建脚本）
- [ ] 安装包输出目录结构正确
- [ ] 安装包内容无遗漏文件
- [ ] 安装包体积可接受（参考基准：Windows ~40MB，macOS ~50MB，Linux ~35MB）
- [ ] 安装包文件名符合命名规范

### 3.3 跨平台注意事项

- [ ] Windows 路径分隔符使用 `\` 或 `os.path.join`
- [ ] macOS 安装包已签名（如发布正式版）
- [ ] Linux 包依赖声明正确（`python3 >= 3.10`）

---

## 4. 发布检查

### 4.1 版本号检查

- [ ] `pyproject.toml` 中的版本号已更新
- [ ] `cli/duan_unified.py` 中的 `--version` 输出版本号正确
- [ ] 所有安装包构建脚本中的版本号一致
- [ ] Git tag 版本号与代码版本号一致

### 4.2 发布前最终验证

- [ ] 在**全新环境**（无预装段言）中测试安装包安装
- [ ] 安装后验证 `duan --version` 输出正确版本
- [ ] 安装后验证 `duan run examples/hello.duan` 正常运行
- [ ] 验证示例工具可执行文件能独立运行
- [ ] 验证卸载功能彻底清除安装文件
- [ ] 测试静默安装模式（`/VERYSILENT` 或等效参数）

### 4.3 发布后操作

- [ ] 创建 GitHub Release 并上传安装包
- [ ] 编写 Release Notes（中文/英文）
- [ ] 更新官网下载链接（如有）
- [ ] 通知用户社区新版本发布

---

## 5. 快速检查命令

```bash
# 版本一致性检查
grep -r "version" pyproject.toml | head -3
grep "MyAppVersion" tools/installer/windows/setup.iss
grep "VERSION=" tools/installer/macos/build_pkg.sh
grep "VERSION=" tools/installer/linux/build_deb.sh

# 示例打包测试
python tools/packager/build_example.py --list
python tools/packager/build_example.py --backend src

# 核心功能验证
python -m cli.duan_unified --version
python -m cli.duan_unified run examples/hello.duan
python -m cli.duan_unified run examples/basic.duan --backend src

# 安装包构建（Windows）
# ISCC.exe tools/installer/windows/setup.iss
```

---

## 6. 签署

| 检查人 | 日期 | 签字 |
|--------|------|------|
| 代码质量 | ____-__-__ | ______ |
| 文档完整性 | ____-__-__ | ______ |
| 打包验证 | ____-__-__ | ______ |
| 发布审批 | ____-__-__ | ______ |