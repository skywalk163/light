# 接口与抽象类设计

**日期**：2026-06-15

## 接口定义

```光明
接口 可打印：
  段落 输出 返回 串。
结束。

接口 可保存 继承 可打印：
  段落 保存(路径)。
结束。
```

生成 Python `ABC` + `@abstractmethod`。

## 类实现接口

```光明
类 文档 实现 可打印, 可保存：
  ...
结束。
```

`实现` 子句中的接口名作为基类加入 Python 类定义。

## @抽象 装饰器

```光明
类 形状：
  @抽象
  段落 面积 返回 数：
    结束。
结束。
```

`@抽象` → `@abstractmethod`，类自动继承 ABC。

## 改动的文件

| 文件 | 改动 |
|------|------|
| `src/keywords.py` | KEYWORDS_CLASS 加 `接口`、`实现`；KEYWORDS_DECORATOR 加 `抽象` |
| `src/light_parser_v3.py` | 新增 InterfaceDefinition AST；`_parse_interface_definition`；修改 `_parse_class_definition` 支持 `实现`；`@抽象` 装饰器 |
| `src/code_generator.py` | 接口生成；抽象方法生成；类定义中处理实现子句 |