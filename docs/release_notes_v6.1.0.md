# 段言 v6.1.0 发布公告

> **发布日期：** 2026-11-07  
> **版本号：** 6.1.0  
> **许可证：** MIT

---

段言（DuanLang）团队很高兴地宣布 **v6.1.0** 正式发布！这是段言在 v6.0 大版本后的首个功能更新，聚焦于**中文编程体验的全面升级**——从 100% 中文错误信息到标准库增强，从 LLVM 编译优化到 AI Copilot 升级，共 20+ 项新特性，让中文编程更加顺畅自然。

---

## 🎯 亮点速览

| 特性 | 一句话描述 |
|------|-----------|
| 🌐 **100% 中文错误信息** | 全量替换 20+ 种英文异常为中文，附中文修改指引 |
| 📚 **标准库 4 大增强** | 网络请求、日期时间、文件系统、中文 NLP 全新模块 |
| 🚀 **LLVM 编译体验优化** | 自动下载依赖、EXE 体积优化、增量编译加速 |
| 🤖 **AI Copilot 升级** | 离线轻量模型、Java/C→段言转换、数据集 v12 |
| 🔌 **C FFI 绑定简化** | 一键加载 C 库，预设 libc/libm 等常用库绑定 |
| 🎨 **语义高亮完善** | 装饰器、二进制数字、中文关键字、内置函数高亮 |
| 📦 **一键安装包** | Windows/macOS/Linux 一键安装包方案 |
| 💬 **社区反馈收集** | `duan feedback` 命令，一键反馈到 GitHub |

---

## ✨ 新特性详解

### 🌐 100% 中文错误信息

全量替换了 20+ 种英文异常类型为中文名称，附带中文修改指引，覆盖语法解析错误、类型错误、值错误等所有场景：

```段言
# 以前：SyntaxError: invalid syntax
# 现在：语法错误：第 3 行，不能识别的语法 "undefined"

# 以前：TypeError: unsupported operand type(s)
# 现在：类型错误：不支持整数 和 文本 的加法运算

# 以前：ValueError: invalid literal
# 现在：值错误：无法将"abc"转换为整数
```

### 📚 标准库 4 大增强

#### 网络请求模块全面增强
```段言
# Cookie 会话支持
设 会话 为 创建会话()
会话.设Cookie("session_id", "abc123")
设 响应 为 会话.获取("https://api.example.com/data")

# 代理支持
设 代理 为 { "http": "http://proxy:8080", "https": "https://proxy:8080" }
设 响应 为 获取("https://api.example.com", 代理=代理)

# 异步请求
异步 设 响应 为 异步获取("https://api.example.com/data")

# 文件上传下载
设 结果 为 下载文件("https://example.com/file.zip", "本地路径/file.zip")
设 上传结果 为 上传文件("https://example.com/upload", "本地路径/photo.jpg")
```

#### 日期时间处理模块（农历/时区/中文日期解析）
```段言
# 农历支持
设 农历日期 为 转农历(2026, 11, 7)
打印 农历日期.年  # 输出：丙午年

# 时区转换
设 纽约时间 为 转时区(现在(), "America/New_York")

# 中文日期解析
设 日期 为 解析中文日期("2026年11月7日")
设 日期2 为 解析中文日期("下周三")
```

#### 文件系统模块（文件监控/批量操作/哈希/安全写入）
```段言
# 文件监控
设 监控器 为 创建文件监控器(".")
监控器.当变更(打印)

# 批量操作
设 结果 为 批量重命名("*.txt", "名称_{序号}.txt")

# 文件哈希
设 哈希值 为 计算文件哈希("document.pdf", "SHA256")

# 安全写入
安全写入文件("config.json", 数据)
```

#### 中文 NLP 工具模块
```段言
# 分词
设 词列表 为 分词("段言是一门中文编程语言")
# 输出：["段言", "是", "一门", "中文", "编程", "语言"]

# 拼音转换
设 拼音 为 转拼音("段言")
# 输出：duan yan

# 简繁转换
设 繁体 为 简体转繁体("段言编程语言")
# 输出：段言編程語言

# 文本统计
设 统计 为 文本统计("段言是一门中文编程语言")
# 输出：{字符数: 11, 词数: 6, 句数: 1}
```

### 🚀 LLVM 编译体验优化

```bash
# 自动检测下载 LLVM 依赖（无需手动安装）
duan compile hello.duan --llvm

# EXE 体积优化
duan compile hello.duan --llvm --optimize-size  # 最小体积
duan compile hello.duan --llvm --lto             # 链接时优化
duan compile hello.duan --llvm --strip           # 去除调试符号

# 增量编译加速
duan build --fast  # 并行编译 + 中间结果缓存
```

### 🔌 C FFI 绑定简化

```段言
# 一键加载 C 库
加载C库 "libm.so"  # 自动绑定数学函数

# 预设绑定直接使用
加载C库 "libc"     # 加载 C 标准库
加载C库 "libm"     # 加载数学库
加载C库 "libpthread"  # 加载线程库

# 自动平台检测
加载C库 "libcurl"  # Windows 上自动找 curl.dll，Linux 上找 libcurl.so
```

### 🤖 AI Copilot 升级

```bash
# 离线轻量级模型方案
duan ai local --model 轻量版

# Java/C → 段言代码转换
duan ai convert Main.java        # 将 Java 代码转为段言
duan ai convert main.c           # 将 C 代码转为段言

# 多轮对话交互式代码生成
duan ai chat                     # 交互式对话生成代码
```

### 📦 包注册中心 Web 界面

现在可以通过浏览器访问包注册中心，搜索、浏览、查看包详情，安装命令一键复制：

```bash
# 浏览器访问包注册中心
duan pkg web                     # 打开 Web 界面

# 或者直接搜索
duan pkg search 网络请求 --remote
```

### 🛡️ 包安全认证

```bash
# 包签名验证
duan pkg verify 包名

# 漏洞检查
duan pkg audit                   # 检查所有依赖包的安全漏洞
```

### 💬 社区反馈收集

```bash
# 提交反馈
duan feedback                    # 交互式反馈收集
duan feedback --send             # 发送到 GitHub Issues
duan feedback --list             # 查看本地已收集的反馈
```

---

## 📖 文档与教程更新

- **文档体系全面升级**: README 重写，文档站首页更新，新增《设计哲学与定位》《段言与Python对比案例》文档
- **端到端入门教程升级**: 30 分钟入门教程重写，增加"为什么"解释、调试、编译、常见错误章节
- **教程体系完善**: 分层学习路径（零基础/有经验/教育工作者），少儿编程趣味示例
- **IDE 适配文档**: VS Code/JetBrains/Neovim/Emacs 完整配置指南
- **新增 8 个文档**: 设计哲学、与 Python 对比、一键安装包方案、性能基准 v2、IDE 配置指南、社区讨论指南、2 篇技术博客

---

## 📊 测试覆盖

- 新增 6 个测试文件：`test_chinese_errors.py`、`test_http_client.py`、`test_datetime.py`、`test_filesystem.py`、`test_chinese_nlp.py`、`test_first_run.py`
- 全量回归测试通过

---

## 🛠️ 安装与升级

### 全新安装

```bash
pip install duan
```

### 从 v6.0 升级

```bash
pip install --upgrade duan
```

### 验证安装

```bash
duan --version
# 输出：段言编译器 v6.1.0
```

---

## 🗺️ 未来规划

v6.1 是段言生态建设的重要一步。我们正在为 v7.0 规划以下方向：

- **自举编译器完全替代 Python 实现**
- **Web 框架正式版（1.0）**
- **包注册中心正式上线**
- **移动端/嵌入式支持原型**
- **更丰富的 AI 辅助编程能力**

欢迎关注 [项目路线图](ROADMAP.md) 了解更多。

---

## 🙏 致谢

感谢所有为段言做出贡献的开发者、测试人员和社区成员！你们的反馈、代码贡献和鼓励是段言持续进步的动力。

特别感谢：
- 所有提交 Issue 和 PR 的贡献者
- 在 GitHub Discussions 中积极参与讨论的社区成员
- 使用段言构建实际项目的先行者们

---

## 🔗 相关链接

- [GitHub 仓库](https://github.com/skywalk163/duan)
- [文档站](index.md)
- [Issue 追踪](https://github.com/skywalk163/duan/issues)
- [GitHub Discussions](https://github.com/skywalk163/duan/discussions)
- [变更日志](../CHANGELOG.md)
- [项目路线图](ROADMAP.md)

---

*段言 —— 用中文，写世界。*