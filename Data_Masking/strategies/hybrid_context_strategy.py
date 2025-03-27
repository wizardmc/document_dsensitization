# 混合上下文感知策略 - 结合上下文感知和自定义替换功能

import os
import pickle
import uuid
from typing import Dict, Tuple, List
from .type_based_strategy import TypeBasedStrategy

class CustomWordManager:
    """自定义词汇管理器，负责自定义脱敏词的持久化存储和管理"""
    
    def __init__(self, mapping_file: str = "custom_words.pkl"):
        self.mapping_file = mapping_file
        self.custom_words = {}
        self._load_custom_words()
    
    def _load_custom_words(self):
        """加载自定义词汇"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'rb') as f:
                    self.custom_words = pickle.load(f)
            except Exception as e:
                print(f"加载自定义词汇失败: {e}")
                self.custom_words = {}
    
    def _save_custom_words(self):
        """保存自定义词汇"""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.mapping_file)), exist_ok=True)
            with open(self.mapping_file, 'wb') as f:
                pickle.dump(self.custom_words, f)
        except Exception as e:
            print(f"保存自定义词汇失败: {e}")
    
    def add_custom_word(self, original: str, replacement: str) -> bool:
        """添加自定义词汇"""
        if not original or not replacement:
            return False
        self.custom_words[original] = replacement
        self._save_custom_words()
        return True
    
    def remove_custom_word(self, original: str) -> bool:
        """移除自定义词汇"""
        if original in self.custom_words:
            del self.custom_words[original]
            self._save_custom_words()
            return True
        return False
    
    def get_custom_words(self) -> Dict[str, str]:
        """获取所有自定义词汇"""
        return self.custom_words.copy()
    
    def clear_custom_words(self):
        """清空所有自定义词汇"""
        self.custom_words.clear()
        self._save_custom_words()

class HybridContextStrategy(TypeBasedStrategy):
    """混合上下文感知策略 - 结合上下文感知和自定义替换功能
    
    特点:
    - 继承自类型替换策略，支持所有类型替换策略的功能
    - 为同类型的不同实体添加编号，提高可读性
    - 保持同一实体的一致性替换
    - 支持用户自定义替换文本
    - 只维护一份映射表，同时包含自动生成的替换和用户自定义的替换
    """
    def __init__(self, mapping_file: str = "hybrid_mapping.pkl"):
        super().__init__()
        # 实体计数器，用于区分同类型的不同实体
        self.entity_counters = {}
        # 实体映射，用于保持同一实体的一致性替换，同时包含自定义替换
        self.entity_mapping = {}
        # 专门存储自定义替换词
        self.custom_replacements = {}
        # 映射文件路径
        self.mapping_file = mapping_file
        # 加载已有的映射表
        self._load_mapping()
    
    def _load_mapping(self):
        """加载映射表"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'rb') as f:
                    data = pickle.load(f)
                    if isinstance(data, tuple) and len(data) == 2:
                        self.entity_mapping, self.entity_counters, self.custom_replacements = data
                    elif isinstance(data, dict):  # 兼容旧版本
                        # 兼容旧版本，只保存了entity_mapping
                        self.entity_mapping = data
                        # 根据映射重建计数器
                        self.entity_counters = {}
                        for _, masked_text in self.entity_mapping.items():
                            for entity_type in ["PER", "ORG", "LOC", "GPE"]:
                                template = self.templates.get(entity_type, "")
                                if template and masked_text.startswith(template):
                                    try:
                                        counter = int(masked_text.split()[-1])
                                        self.entity_counters[entity_type] = max(
                                            self.entity_counters.get(entity_type, 0), counter
                                        )
                                    except (ValueError, IndexError):
                                        pass
            except Exception as e:
                print(f"加载映射表失败: {e}")
                self.entity_mapping = {}
                self.entity_counters = {}
    
    def _save_mapping(self):
        """保存映射表"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(self.mapping_file)), exist_ok=True)
            with open(self.mapping_file, 'wb') as f:
                # 同时保存entity_mapping和entity_counters
                pickle.dump((self.entity_mapping, self.entity_counters, self.custom_replacements), f)
        except Exception as e:
            print(f"保存映射表失败: {e}")
    
    def mask(self, text: str, entity_type: str = "DEFAULT") -> str:
        """对文本进行脱敏处理
        
        参数:
            text (str): 原始文本
            entity_type (str): 实体类型，默认为DEFAULT
        
        返回:
            str: 脱敏后的文本
        """
        # 如果已经有映射，则使用已有的替换文本保持一致性
        if text in self.entity_mapping:
            return self.entity_mapping[text]
        
        # 获取基本模板
        template = self.templates.get(entity_type, self.templates["DEFAULT"])
        
        # 为不同类型的实体添加编号，提高可读性
        if entity_type in ["PER", "ORG", "LOC", "GPE"]:
            # 更新计数器
            if entity_type not in self.entity_counters:
                self.entity_counters[entity_type] = 0
            self.entity_counters[entity_type] += 1
            
            # 生成带编号的替换文本
            masked_text = f"{template} {self.entity_counters[entity_type]}"
            
            # 保存映射关系
            self.entity_mapping[text] = masked_text
            
            # 保存映射表
            self._save_mapping()
            
            return masked_text
        
        # 对于其他类型，使用基本模板
        masked_text = template
        
        # 保存映射关系
        self.entity_mapping[text] = masked_text
        self._save_mapping()
        
        return masked_text
    
    def set_custom_replacement(self, original_text: str, replacement_text: str):
        """设置自定义替换文本
        
        参数:
            original_text (str): 原始文本
            replacement_text (str): 替换文本
        """
        if not original_text or not replacement_text:
            return False
            
        self.entity_mapping[original_text] = replacement_text
        self.custom_replacements[original_text] = replacement_text
        self._save_mapping()  # 保存映射表
        return True
    
    def remove_custom_replacement(self, original_text: str):
        """移除自定义替换文本
        
        参数:
            original_text (str): 原始文本
        
        返回:
            bool: 是否成功移除
        """
        if original_text in self.entity_mapping:
            del self.entity_mapping[original_text]
            if original_text in self.custom_replacements:
                del self.custom_replacements[original_text]
            self._save_mapping()
            return True
        return False
    
    def get_custom_replacements(self) -> Dict[str, str]:
        """获取所有替换文本
        
        返回:
            Dict[str, str]: {原始文本: 替换文本}
        """
        # 确保加载最新映射表
        self._load_mapping()
        return self.custom_replacements.copy()
    
    def clear_mapping(self, remove_file: bool = False):
        """清除映射表
        
        参数:
            remove_file (bool): 是否删除映射文件，默认为False
        """
        self.entity_mapping = {}
        self.entity_counters = {}
        self.custom_replacements = {}
        if remove_file and os.path.exists(self.mapping_file):
            os.remove(self.mapping_file)
    
    def unmask(self, masked_text: str) -> str:
        """恢复脱敏后的文本
        
        参数:
            masked_text (str): 脱敏后的文本
        
        返回:
            str: 恢复后的文本
        """
        # 创建反向映射表 {脱敏后的文本: 原始文本}
        reverse_mapping = {masked: original for original, masked in self.entity_mapping.items()}
        
        # 替换所有脱敏文本
        unmasked_text = masked_text
        for masked, original in reverse_mapping.items():
            unmasked_text = unmasked_text.replace(masked, original)
        
        return unmasked_text