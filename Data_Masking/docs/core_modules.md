# 核心模块

本文档详细介绍法律文档脱敏工具的核心模块及其功能。

## NER模型模块

### 概述

NER（命名实体识别）模型模块是系统的基础组件，负责识别文本中的敏感实体。该模块使用ModelScope NLP RANER 中文命名实体识别模型，能够准确识别人名、组织机构、地点等敏感信息。

### 主要组件

#### NERModelLoader 类

采用单例模式设计的NER模型加载器，确保模型只初始化一次，避免重复加载带来的资源浪费。

```python
class NERModelLoader:
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(NERModelLoader, cls).__new__(cls)
            return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    print("初始化NER模型...")
                    self.ner_pipeline = pipeline(Tasks.named_entity_recognition, 'iic/nlp_raner_named-entity-recognition_chinese-base-generic')
                    self._initialized = True
    
    def get_pipeline(self):
        return self.ner_pipeline
    
    def process_text(self, text):
        """直接处理单个文本"""
        return self.ner_pipeline(text)
```

#### recognize_entities 函数

核心函数，负责识别文本中的实体，支持长文本分块处理和并行优化。

**主要特点**：
- 自动处理长文本，避免张量大小不匹配问题
- 优化分块策略，在句子边界处分割文本
- 支持并行处理，提高处理效率
- 合并分块结果，确保实体完整性

## 脱敏策略模块

### 概述

脱敏策略模块采用策略模式设计，提供多种脱敏策略实现，用户可以根据需求选择合适的策略。

### 主要组件

#### MaskingStrategy 类

所有脱敏策略的基类，定义了策略的基本接口。

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

#### TypeBasedStrategy 类

根据实体类型使用不同的替换模板，是最基本的脱敏策略。

**主要特点**：
- 支持多种实体类型（人名、组织机构、地点等）
- 可自定义替换模板
- 简单直观，易于理解和使用

#### ContextAwareStrategy 类

继承自TypeBasedStrategy，根据实体类型和上下文选择合适的替换方式，是最智能的脱敏策略。

**主要特点**：
- 为同一类型的不同实体分配不同的替换文本
- 维护实体映射表，确保同一实体在整个文档中使用相同的替换文本
- 支持持久化存储映射关系，便于后续恢复

#### CustomReplacementStrategy 类

允许用户为每个词自定义唯一替换词，提供最大的灵活性。

**主要特点**：
- 支持用户自定义替换规则
- 维护自定义映射表，确保替换的一致性
- 支持持久化存储映射关系，便于后续恢复

#### HashStrategy 类

使用哈希值替换敏感信息，提供更高的安全性。

**主要特点**：
- 使用MD5哈希算法对敏感信息进行不可逆转换
- 支持添加盐值增强安全性
- 可配置哈希结果的长度

## 数据脱敏器模块

### 概述

数据脱敏器模块是系统的核心组件，负责文本脱敏和恢复，集成了NER模型和脱敏策略。

### 主要组件

#### DataMasker 类

数据脱敏器类，负责文本脱敏和恢复。

**主要功能**：
- 文本脱敏处理
- 映射表管理
- 正则表达式匹配
- 文本恢复处理

**核心方法**：
- `mask_text(text: str) -> str`：对文本进行脱敏处理
- `unmask_text(masked_text: str) -> str`：恢复脱敏后的文本
- `get_masked_entities(masked_text: str) -> Dict`：获取脱敏实体信息

**实现细节**：
- 使用NER模型识别文本中的敏感实体
- 使用正则表达式识别额外的敏感信息（电话号码、身份证号等）
- 根据配置的脱敏策略，对敏感实体进行替换
- 维护脱敏映射表，确保同一实体在整个文档中使用相同的替换文本
- 支持并行处理，提高处理效率

## 文档脱敏器模块

### 概述

文档脱敏器模块负责处理整个文档的脱敏和恢复，支持多种文档格式。

### 主要组件

#### DocumentMasker 类

文档脱敏器类，负责处理整个文档的脱敏和恢复。

**主要功能**：
- 文档解析和转换
- 文档内容脱敏
- 文档内容恢复
- 批量处理优化

**核心方法**：
- `mask_document(content_list: List[Dict]) -> List[Dict]`：对文档内容列表进行脱敏处理
- `unmask_document(masked_content_list: List[Dict]) -> List[Dict]`：恢复脱敏后的文档内容列表
- `process_document_file(file_path: str, mask: bool) -> Tuple[str, str]`：处理文档文件，支持脱敏和恢复

**实现细节**：
- 支持多种文档格式（PDF、DOC、DOCX、TXT、MD等）
- 两遍扫描策略：第一遍收集所有实体并建立映射关系，第二遍