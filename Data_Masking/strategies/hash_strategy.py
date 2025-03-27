# 哈希策略 - 使用哈希值替换敏感信息

import hashlib
from .base_strategy import MaskingStrategy

class HashStrategy(MaskingStrategy):
    """哈希策略 - 使用哈希值替换敏感信息"""
    def __init__(self, salt: str = "", hash_length: int = 8):
        self.salt = salt
        self.hash_length = hash_length
    
    def mask(self, text: str) -> str:
        salted_text = text + self.salt
        hash_obj = hashlib.md5(salted_text.encode('utf-8'))
        return hash_obj.hexdigest()[:self.hash_length]