# 替换策略 - 使用固定文本替换敏感信息

from .base_strategy import MaskingStrategy

class ReplacementStrategy(MaskingStrategy):
    """替换策略 - 使用固定文本替换敏感信息"""
    def __init__(self, replacement_text: str = "***"):
        self.replacement_text = replacement_text
    
    def mask(self, text: str) -> str:
        return self.replacement_text