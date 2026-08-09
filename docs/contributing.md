# 贡献指南

感谢你对光明（LightLang）的兴趣！我们欢迎各种形式的贡献。

## 如何贡献

### 报告 Bug

- 提交 Issue 到 GitHub 仓库
- 包含完整的错误信息和复现步骤
- 附上相关的代码片段

### 提交代码

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 代码风格

- 遵循 Python PEP 8
- 光明代码使用 4 空格缩进
- 添加适当的注释和文档

### 测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/
```

## 开发环境

```bash
# 克隆仓库
git clone https://github.com/light-lang/light.git
cd light

# 安装开发依赖
pip install -e ".[dev]"

# 安装 pre-commit hooks
pre-commit install
```

## 文档

- 文档位于 `docs/` 目录
- 使用 Markdown 格式
- 遵循已有文档的风格

## 社区

- GitHub: https://github.com/light-lang/light