# 天气查询示例程序

用段言语言编写的天气查询示例，演示：
- duanpub 标准库导入（文件系统、JSON）
- 多模块项目结构（config + utils + main）
- 文件读写操作
- 异常处理

## 运行

```bash
cd examples/weather_app
python -m duan run main.duan
```

## 项目结构

- `main.duan` — 主程序，天气查询 + 文件保存
- `config.duan` — 配置模块，默认城市
- `utils.duan` — 工具函数，格式化输出
- `duan.json` — 项目配置
