# DeepSeek R1 1.5B 光明语言微调数据集

## 📊 数据集信息

- **版本**：v1.0
- **数据量**：103 条
- **格式**：JSONL（每行一个 JSON 对象）
- **用途**：微调 DeepSeek R1 1.5B 模型
- **包含**：思考链 + 最终代码

## 📁 文件结构

```
light-merge/
├── docs/
│   ├── dataset_deepseek_r1_100_examples.md    # Markdown 格式原始数据
│   └── dataset_deepseek_r1_100_examples.jsonl # JSONL 格式训练数据
└── tools/
    └── convert_to_deepseek_r1_format.py       # 转换脚本
```

## 🎯 数据格式

每条数据包含三个字段：

```json
{
  "instruction": "任务描述",
  "thinking": "思考链（推理过程）",
  "response": "光明代码（最终答案）"
}
```

### 示例

```json
{
  "instruction": "根据分数判断成绩等级，分数>=90为优秀，>=60为及格，否则不及格。",
  "thinking": "\n## 任务分析\n\n1. **理解需求**：\n   - 需要完成编程任务\n   - 核心要求是根据分数判断成绩等级\n\n2. **确定技术方案**：\n   - 需要使用光明语言条件判断相关的语法特性\n   - 主要操作包括：条件判断\n\n3. **代码设计**：\n   - 变量命名：使用中文命名\n   - 代码结构：使用 if-else 结构\n\n4. **实现步骤**：\n   执行计算或判断\n\n5. **验证检查**：\n   - 语法是否正确\n   - 逻辑是否完整\n\n## 思考完成，开始编写代码\n",
  "response": "设 分数 为 85\n如果 分数 >= 90：\n    打印(\"等级：优秀\")\n否则如果 分数 >= 60：\n    打印(\"等级：及格\")\n否则：\n    打印(\"等级：不及格\")\n"
}
```

## 📈 数据分布

### 按任务类型分类

| 类别 | 数量 | 占比 |
|------|------|------|
| 基础语法 | 20 | 19.4% |
| 字符串处理 | 20 | 19.4% |
| 文件操作 | 20 | 19.4% |
| JSON 处理 | 10 | 9.7% |
| 网络请求 | 10 | 9.7% |
| 统计与数学 | 10 | 9.7% |
| 实用工具 | 10 | 9.7% |
| 综合应用 | 3 | 2.9% |

### 按难度分类

| 难度 | 数量 | 占比 |
|------|------|------|
| 入门（L1） | 70 | 68.0% |
| 进阶（L2） | 28 | 27.2% |
| 高级（L3） | 5 | 4.8% |

## 🔧 使用方法

### 1. 数据集转换（已完成）

原始 Markdown 数据已转换为 DeepSeek R1 格式（带思考链）：

```bash
python3 tools/convert_to_deepseek_r1_format.py
```

### 2. 微调模型

使用 DeepSeek R1 1.5B 进行微调（示例）：

```bash
# 使用 LLaMA-Factory（推荐）
llamafactory-cli train \
  --model_name deepseek-ai/deepseek-r1-1.5b \
  --dataset dataset_deepseek_r1_100_examples \
  --template default \
  --finetuning_type lora \
  --output_dir ./output/deepseek_r1_light

# 使用 PEFT + Transformers
python train.py \
  --model_name deepseek-ai/deepseek-r1-1.5b \
  --dataset dataset_deepseek_r1_100_examples.jsonl \
  --output_dir ./output/deepseek_r1_light
```

### 3. 推理测试

```bash
# 使用 LLaMA-Factory
llamafactory-cli chat \
  --model_name ./output/deepseek_r1_light \
  --template default

# 或使用 Transformers
python inference.py \
  --model_path ./output/deepseek_r1_light \
  --prompt "创建一个程序，定义整数、浮点数、字符串、布尔值和空值，并打印它们的值。"
```

## 📝 评估指标

### 训练时评估

- **准确率**：代码语法正确性
- **完整性**：是否满足任务需求
- **规范性**：是否符合光明语言语法规范

### 推理时评估

- **代码正确性**：生成的代码能否正确运行
- **语法符合度**：是否符合光明语言语法规范
- **任务匹配度**：是否满足用户需求

## 🚀 最佳实践

### 1. 数据增强

```python
# 可以通过以下方式增强数据：
# - 随机替换变量名
# - 添加注释
# - 生成多个解法
# - 添加边界条件测试
```

### 2. 数据划分

```python
# 建议划分：80% 训练集，10% 验证集，10% 测试集
# 或者：90% 训练集，10% 测试集（数据量较少时）
```

### 3. 微调策略

- **学习率**：1e-5 ~ 5e-5
- **Batch size**：4 ~ 8
- **Epochs**：3 ~ 5
- **LoRA rank**：16 ~ 64
- **LoRA alpha**：32 ~ 128

## 📚 参考资料

- [DeepSeek R1 官方文档](https://github.com/deepseek-ai/deepseek-r1)
- [LLaMA-Factory 使用指南](https://github.com/hiyouga/LLaMA-Factory)
- [光明语言语法规范](https://github.com/skywalk163/light-merge/blob/main/docs/syntax.md)
- [光明语言 AI 编程指南](https://github.com/skywalk163/light-merge/blob/main/docs/AI编程指南.md)

## 🤝 贡献

欢迎贡献更多数据！

### 数据贡献指南

1. **任务描述**：使用自然语言描述编程任务
2. **思考链**：包含需求分析、技术方案、代码设计、实现步骤、验证检查
3. **代码**：符合光明语言语法规范的正确代码

### 数据质量标准

- ✅ 语法正确：代码必须能通过编译/运行
- ✅ 任务完整：代码必须满足任务需求
- ✅ 规范命名：使用中文命名，清晰表达语义
- ✅ 代码简洁：避免冗余，保持清晰

## 📄 许可证

本数据集用于微调 DeepSeek R1 1.5B 模型，遵循项目主许可证。

---

**数据集创建日期**：2026-09-08
**版本**：v1.0
**维护者**：光明语言项目组
