# 自定义替换策略 - 允许用户为每个词自定义唯一替换词

import os
import pickle
import uuid
from typing import Dict
from .base_strategy import MaskingStrategy

class CustomReplacementStrategy(MaskingStrategy):
    """自定义替换策略 - 允许用户为每个词自定义唯一替换词"""
    def __init__(self, mapping_file: str = "custom_mapping.pkl"):
        # 自定义映射表 {原始文本: 替换文本}
        self.custom_mapping = {}
        # 映射文件路径
        self.mapping_file = mapping_file
        # 加载已有的映射表
        self._load_mapping()
    
    def _load_mapping(self):
        """加载自定义映射表"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'rb') as f:
                    self.custom_mapping = pickle.load(f)
            except Exception as e:
                print(f"加载自定义映射表失败: {e}")
                self.custom_mapping = {}
    
    def _save_mapping(self):
        """保存自定义映射表"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(self.mapping_file)), exist_ok=True)
            with open(self.mapping_file, 'wb') as f:
                pickle.dump(self.custom_mapping, f)
        except Exception as e:
            print(f"保存自定义映射表失败: {e}")
    
    def set_custom_replacement(self, original_text: str, replacement_text: str):
        """设置自定义替换文本
        
        参数:
            original_text (str): 原始文本
            replacement_text (str): 替换文本
        """
        self.custom_mapping[original_text] = replacement_text
        self._save_mapping()
    
    def remove_custom_replacement(self, original_text: str):
        """移除自定义替换文本
        
        参数:
            original_text (str): 原始文本
        
        返回:
            bool: 是否成功移除
        """
        if original_text in self.custom_mapping:
            del self.custom_mapping[original_text]
            self._save_mapping()
            return True
        return False
    
    def get_custom_replacements(self) -> Dict[str, str]:
        """获取所有自定义替换文本
        
        返回:
            Dict[str, str]: {原始文本: 替换文本}
        """
        return self.custom_mapping.copy()
    
    def mask(self, text: str, entity_type: str = None) -> str:
        # 如果有自定义替换文本，则使用自定义替换文本
        if text in self.custom_mapping:
            return self.custom_mapping[text]
        
        # 如果没有自定义替换文本，则生成一个唯一标识符
        replacement = f"__CUSTOM_{uuid.uuid4().hex[:8]}__"
        
        # 保存映射关系
        self.custom_mapping[text] = replacement
        self._save_mapping()
        
        return replacement