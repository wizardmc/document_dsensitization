# 上下文感知策略 - 根据实体类型和上下文选择合适的替换方式

import os
import pickle
from typing import Dict, Tuple
from .type_based_strategy import TypeBasedStrategy

class ContextAwareStrategy(TypeBasedStrategy):
    """上下文感知策略 - 根据实体类型和上下文选择合适的替换方式"""
    def __init__(self, mapping_file: str = "context_mapping.pkl"):
        super().__init__()
        # 实体计数器，用于区分同类型的不同实体
        self.entity_counters = {}
        # 实体映射，用于保持同一实体的一致性替换
        self.entity_mapping = {}
        # 映射文件路径
        self.mapping_file = mapping_file
        # 加载已有的映射表
        self._load_mapping()
    
    def _load_mapping(self):
        """加载实体映射表"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'rb') as f:
                    data = pickle.load(f)
                    if isinstance(data, tuple) and len(data) == 2:
                        self.entity_mapping, self.entity_counters = data
                    elif isinstance(data, dict):
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
                print(f"加载实体映射表失败: {e}")
                self.entity_mapping = {}
                self.entity_counters = {}
    
    def _save_mapping(self):
        """保存实体映射表"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(self.mapping_file)), exist_ok=True)
            with open(self.mapping_file, 'wb') as f:
                # 同时保存entity_mapping和entity_counters
                pickle.dump((self.entity_mapping, self.entity_counters), f)
        except Exception as e:
            print(f"保存实体映射表失败: {e}")
    
    def mask(self, text: str, entity_type: str = "DEFAULT") -> str:
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
        return template
    
    def clear_mapping(self, remove_file: bool = False):
        """清除映射表
        
        参数:
            remove_file (bool): 是否删除映射文件，默认为False
        """
        self.entity_mapping = {}
        self.entity_counters = {}
        if remove_file and os.path.exists(self.mapping_file):
            os.remove(self.mapping_file)