# Data_Masking 模块主入口文件
# 提供脱敏策略和脱敏器的统一导入接口

# 导入脱敏策略
from .strategies.base_strategy import MaskingStrategy
from .strategies.replacement_strategy import ReplacementStrategy
from .strategies.hash_strategy import HashStrategy
from .strategies.type_based_strategy import TypeBasedStrategy
from .strategies.context_aware_strategy import ContextAwareStrategy
from .strategies.custom_replacement_strategy import CustomReplacementStrategy

# 导入脱敏器
from .maskers.data_masker import DataMasker
from .maskers.document_masker import DocumentMasker

# 导出所有类和函数
__all__ = [
    # 脱敏策略
    'MaskingStrategy',
    'ReplacementStrategy',
    'HashStrategy',
    'TypeBasedStrategy',
    'ContextAwareStrategy',
    'CustomReplacementStrategy',
    # 脱敏器
    'DataMasker',
    'DocumentMasker'
]

# 便捷函数
def mask_text(text, strategy=None, save_mapping=True):
    """便捷函数：对文本进行脱敏处理
    
    参数:
        text (str): 待脱敏的文本
        strategy (MaskingStrategy, optional): 使用的脱敏策略，默认为None，使用DataMasker默认策略
        save_mapping (bool): 是否保存映射表，默认为True
    
    返回:
        str: 脱敏后的文本
    """
    masker = DataMasker()
    if strategy:
        masker.set_default_strategy(strategy)
    return masker.mask_text(text, save_mapping=save_mapping)

def unmask_text(masked_text):
    """便捷函数：恢复脱敏后的文本
    
    参数:
        masked_text (str): 脱敏后的文本
    
    返回:
        str: 恢复后的文本
    """
    masker = DataMasker()
    return masker.unmask_text(masked_text)

def mask_document(content_list, strategy=None, save_mapping=True):
    """便捷函数：对文档内容列表进行脱敏处理
    
    参数:
        content_list (List[Dict[str, Any]]): 文档内容列表
        strategy (MaskingStrategy, optional): 使用的脱敏策略，默认为None，使用DataMasker默认策略
        save_mapping (bool): 是否保存映射表，默认为True
    
    返回:
        List[Dict[str, Any]]: 脱敏后的文档内容列表
    """
    masker = DataMasker()
    if strategy:
        masker.set_default_strategy(strategy)
    doc_masker = DocumentMasker(masker)
    return doc_masker.mask_document(content_list, save_mapping=save_mapping)

def unmask_document(masked_content_list):
    """便捷函数：恢复脱敏后的文档内容列表
    
    参数:
        masked_content_list (List[Dict[str, Any]]): 脱敏后的文档内容列表
    
    返回:
        List[Dict[str, Any]]: 恢复后的文档内容列表
    """
    doc_masker = DocumentMasker()
    return doc_masker.unmask_document(masked_content_list)

def mask_markdown(markdown_content, strategy=None, save_mapping=True):
    """便捷函数：对Markdown文本进行脱敏处理
    
    参数:
        markdown_content (str): 待脱敏的Markdown文本
        strategy (MaskingStrategy, optional): 使用的脱敏策略，默认为None，使用DataMasker默认策略
        save_mapping (bool): 是否保存映射表，默认为True
    
    返回:
        str: 脱敏后的Markdown文本
    """
    masker = DataMasker()
    if strategy:
        masker.set_default_strategy(strategy)
    doc_masker = DocumentMasker(masker)
    return doc_masker.mask_markdown(markdown_content, save_mapping=save_mapping)

def unmask_markdown(masked_markdown_content):
    """便捷函数：恢复脱敏后的Markdown文本
    
    参数:
        masked_markdown_content (str): 脱敏后的Markdown文本
    
    返回:
        str: 恢复后的Markdown文本
    """
    doc_masker = DocumentMasker()
    return doc_masker.unmask_markdown(masked_markdown_content)