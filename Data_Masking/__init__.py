# Data_Masking 包初始化文件

# 导入NER模型相关功能
from .NER_model import recognize_entities, NERModelLoader, batch_recognize_entities

# 导入脱敏相关功能
from .masking import (
    MaskingStrategy, ReplacementStrategy, HashStrategy, TypeBasedStrategy,
    DataMasker, DocumentMasker
)

# 导出模块内容
__all__ = [
    # NER模型相关
    'recognize_entities', 'NERModelLoader', 'batch_recognize_entities',
    # 脱敏策略相关
    'MaskingStrategy', 'ReplacementStrategy', 'HashStrategy', 'TypeBasedStrategy',
    # 脱敏器相关
    'DataMasker', 'DocumentMasker'
]