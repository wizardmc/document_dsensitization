# 自定义词汇处理器 - 用于管理自定义脱敏词汇的加载、保存和应用

import os
import pickle
from typing import Dict, Optional

class CustomWordsHandler:
    """自定义词汇处理器，负责自定义脱敏词的加载、保存和应用"""
    
    def __init__(self, mapping_file: str = "custom_words.pkl"):
        """初始化自定义词汇处理器
        
        参数:
            mapping_file (str): 自定义词汇映射文件路径
        """
        self.mapping_file = mapping_file
        self.custom_words = {}
        self._load_custom_words()
    
    def _load_custom_words(self):
        """加载自定义词汇"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'rb') as f:
                    self.custom_words = pickle.load(f)
                print(f"已加载{len(self.custom_words)}个自定义脱敏词")
            except Exception as e:
                print(f"加载自定义词汇失败: {e}")
                self.custom_words = {}
    
    def _save_custom_words(self):
        """保存自定义词汇"""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.mapping_file)), exist_ok=True)
            with open(self.mapping_file, 'wb') as f:
                pickle.dump(self.custom_words, f)
            print(f"已保存{len(self.custom_words)}个自定义脱敏词")
        except Exception as e:
            print(f"保存自定义词汇失败: {e}")
    
    def add_custom_word(self, original: str, replacement: str) -> bool:
        """添加自定义词汇
        
        参数:
            original (str): 原始文本
            replacement (str): 替换文本
            
        返回:
            bool: 是否成功添加
        """
        if not original or not replacement:
            return False
        self.custom_words[original] = replacement
        self._save_custom_words()
        return True
    
    def remove_custom_word(self, original: str) -> bool:
        """移除自定义词汇
        
        参数:
            original (str): 原始文本
            
        返回:
            bool: 是否成功移除
        """
        if original in self.custom_words:
            del self.custom_words[original]
            self._save_custom_words()
            return True
        return False
    
    def get_custom_words(self) -> Dict[str, str]:
        """获取所有自定义词汇
        
        返回:
            Dict[str, str]: {原始文本: 替换文本}
        """
        return self.custom_words.copy()
    
    def clear_custom_words(self):
        """清空所有自定义词汇"""
        self.custom_words.clear()
        self._save_custom_words()
    
    def apply_custom_words(self, text: str) -> str:
        """应用自定义词汇进行替换
        
        参数:
            text (str): 原始文本
            
        返回:
            str: 替换后的文本
        """
        result = text
        for original, replacement in self.custom_words.items():
            result = result.replace(original, replacement)
        return result
    
    def sync_with_strategy(self, strategy):
        """与策略同步自定义词汇
        
        参数:
            strategy: 脱敏策略对象，必须有get_custom_replacements和set_custom_replacement方法
        """
        if hasattr(strategy, 'get_custom_replacements') and hasattr(strategy, 'set_custom_replacement'):
            # 获取策略中的自定义词汇
            strategy_words = strategy.get_custom_replacements()
            
            # 合并策略中的自定义词汇
            for original, replacement in strategy_words.items():
                if original not in self.custom_words:
                    self.custom_words[original] = replacement
            
            # 将本地自定义词汇同步到策略中
            for original, replacement in self.custom_words.items():
                strategy.set_custom_replacement(original, replacement)
            
            # 保存更新后的自定义词汇
            self._save_custom_words()
            
            return True
        return False