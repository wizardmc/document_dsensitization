# 脱敏策略

本文档详细介绍法律文档脱敏工具支持的各种脱敏策略及其使用方法。

## 策略概述

脱敏策略是决定如何替换敏感信息的关键组件。本系统采用策略模式设计，提供多种脱敏策略，用户可以根据需求选择合适的策略。

## 基础策略（MaskingStrategy）

所有脱敏策略的基类，定义了策略的基本接口。

### 主要方法

- **mask(text: str) -> str**：将文本进行脱敏处理
- **get_name() -> str**：获取策略名称
- **clear_mapping(remove_file: bool = False)**：清除映射表

### 示例代码

```python
class MaskingStrategy:
    """脱敏策略基类"""
    def mask(self, text: str) -> str:
        """将文本进行脱敏处理"""
        raise NotImplementedError("子类必须实现此方法")
    
    def get_name(self) -> str:
        """获取策略名称"""
        return self.__class__.__name__
    
    def clear_mapping(self, remove_file: bool = False):
        """清除映射表，基类中为空实现，由需要的子类重写"""
        pass
```

## 类型替换策略（TypeBasedStrategy）

根据实体类型使用不同的替换模板，是最基本的脱敏策略。

### 特点

- 根据实体类型选择不同的替换模板
- 支持自定义替换模板
- 简单直观，易于理解和使用

### 默认替换模板

| 实体类型 | 默认替换模板 |
|---------|------------|
| PER     | 某人        |
| ORG     | 某机构      |
| LOC     | 某地点      |
| GPE     | 某地区      |
| PHONE   | 电话号码    |
| ID      | 身份证号    |
| BANK    | 银行卡号    |
| EMAIL   | 电子邮箱    |
| IP      | IP地址     |
| DATE    | 某日期      |
| TIME    | 某时间      |
| MONEY   | 某金额      |
| DEFAULT | ***       |

### 示例代码

```python
from strategies.type_based_strategy import TypeBasedStrategy

# 创建类型替换策略实例
strategy = TypeBasedStrategy()

# 自定义替换模板
strategy.set_template("PER", "张某")

# 使用策略进行脱敏
masked_text = strategy.mask("张三", "PER")  # 返回 "张某"
```

## 替换策略（ReplacementStrategy）

使用固定文本替换所有敏感信息，不区分实体类型。

### 特点

- 简单高效，实现简单
- 所有敏感信息使用相同的替换文本
- 适用于只需要隐藏敏感信息而不关心区分不同类型的场景

### 示例代码

```python
from strategies.replacement_strategy import ReplacementStrategy

# 创建替换策略实例，指定替换文本
strategy = ReplacementStrategy(replacement_text="***")

# 使用策略进行脱敏
masked_text = strategy.mask("张三")  # 返回 "***"
```

## 上下文感知策略（ContextAwareStrategy）

根据实体类型和上下文选择合适的替换方式，保持同一实体的一致性替换。

### 特点

- 继承自类型替换策略，支持所有类型替换策略的功能
- 为同类型的不同实体添加编号，提高可读性
- 保持同一实体的一致性替换
- 支持保存和加载映射表，便于多次处理保持一致

### 示例代码

```python
from strategies.context_aware_strategy import ContextAwareStrategy

# 创建上下文感知策略实例
strategy = ContextAwareStrategy(mapping_file="context_mapping.pkl")

# 使用策略进行脱敏
masked_text1 = strategy.mask("张三", "PER")  # 返回 "某人 1"
masked_text2 = strategy.mask("李四", "PER")  # 返回 "某人 2"
masked_text3 = strategy.mask("张三", "PER")  # 返回 "某人 1"（保持一致性）

# 清除映射表
strategy.clear_mapping(remove_file=True)
```

## 自定义替换策略（CustomReplacementStrategy）

允许用户为每个词自定义唯一替换词。

### 特点

- 高度灵活，用户可以完全控制替换结果
- 支持保存和加载自定义映射表
- 对于未指定替换文本的敏感信息，自动生成唯一标识符

### 示例代码

```python
from strategies.custom_replacement_strategy import CustomReplacementStrategy

# 创建自定义替换策略实例
strategy = CustomReplacementStrategy(mapping_file="custom_mapping.pkl")

# 设置自定义替换文本
strategy.set_custom_replacement("张三", "张某某")
strategy.set_custom_replacement("李四", "李某")

# 使用策略进行脱敏
masked_text1 = strategy.mask("张三")  # 返回 "张某某"
masked_text2 = strategy.mask("王五")  # 返回自动生成的唯一标识符，如 "__CUSTOM_a1b2c3d4__"

# 获取所有自定义替换文本
custom_replacements = strategy.get_custom_replacements()

# 移除自定义替换文本
strategy.remove_custom_replacement("张三")
```

## 哈希策略（HashStrategy）

使用哈希值替换敏感信息，提供不可逆的脱敏方式。

### 特点

- 不可逆，无法从脱敏后的文本恢复原始信息
- 相同的输入产生相同的输出，保持一致性
- 支持添加盐值增强安全性
- 可以控制哈希值长度

### 示例代码

```python
from strategies.hash_strategy import HashStrategy

# 创建哈希策略实例，指定盐值和哈希长度
strategy = HashStrategy(salt="my_secret_salt", hash_length=8)

# 使用策略进行脱敏
masked_text = strategy.mask("张三")  # 返回哈希值，如 "a1b2c3d4"
```

## 策略选择建议

根据不同的需求场景，可以选择不同的脱敏策略：

1. **简单隐藏敏感信息**：使用替换策略（ReplacementStrategy）
2. **区分不同类型的敏感信息**：使用类型替换策略（TypeBasedStrategy）
3. **保持文档可读性和一致性**：使用上下文感知策略（ContextAwareStrategy）
4. **需要高度自定义替换规则**：使用自定义替换策略（CustomReplacementStrategy）
5. **需要不可逆的脱敏方式**：使用哈希策略（HashStrategy）