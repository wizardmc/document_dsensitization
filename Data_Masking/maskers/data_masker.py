# 数据脱敏器 - 负责文本脱敏和恢复

import os
import re
import uuid
import pickle
import concurrent.futures
import tqdm
from typing import Dict, List, Tuple, Union, Optional, Any

from ..strategies import MaskingStrategy, ContextAwareStrategy
from ..NER_model import recognize_entities

class DataMasker:
    """数据脱敏器 - 负责文本脱敏和恢复"""
    def __init__(self, mapping_file: str = "masking_map.pkl"):
        # 脱敏映射表文件路径
        self.mapping_file = mapping_file
        # 脱敏映射表 {脱敏后的文本: (原始文本, 实体类型)}
        self.mapping: Dict[str, Tuple[str, str]] = {}
        # 实体到掩码的映射表 {(原始文本, 实体类型): 脱敏后的文本}
        # 用于确保同一实体始终使用相同的掩码
        self.entity_to_mask: Dict[Tuple[str, str], str] = {}
        # 加载已有的映射表
        self._load_mapping()
        # 默认策略
        self.default_strategy = ContextAwareStrategy()
        # 类型策略映射
        self.type_strategies: Dict[str, MaskingStrategy] = {}
        # 正则表达式模式
        self.regex_patterns = {
            "PHONE": r'(?<!\d)(?:(?:1[3-9]\d{9})|(?:0\d{2,3}-?\d{7,8}))(?!\d)',  # 手机号和座机号
            "ID": r'(?<!\d)\d{17}[0-9Xx](?!\d)',  # 身份证号
            "BANK": r'(?<!\d)(?:\d{16}|\d{19})(?!\d)',  # 银行卡号
            "EMAIL": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',  # 电子邮箱
            "IP": r'(?:\d{1,3}\.){3}\d{1,3}',  # IPv4地址
            "DATE": r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?',  # 日期
            "TIME": r'\d{1,2}:\d{1,2}(:\d{1,2})?',  # 时间
            "MONEY": r'\d+(\.\d+)?元|\d+(\.\d+)?万元|\d+(\.\d+)?亿元|\d+(\.\d+)?美元|\d+(\.\d+)?欧元'  # 金额
        }
    
    def _load_mapping(self):
        """加载脱敏映射表"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'rb') as f:
                    data = pickle.load(f)
                    print(f"[DEBUG] 加载映射表: {self.mapping_file}")
                    print(f"[DEBUG] 映射表数据类型: {type(data)}")
                    
                    if isinstance(data, dict):
                        # 兼容旧版本，旧版本只保存了mapping
                        self.mapping = data
                        # 根据mapping重建entity_to_mask
                        self.entity_to_mask = {(original, entity_type): mask_id 
                                              for mask_id, (original, entity_type) in self.mapping.items()}
                        print(f"[DEBUG] 加载旧版本映射表: {len(self.mapping)} 条记录")
                    elif isinstance(data, tuple) and len(data) == 2:
                        # 新版本，保存了mapping和entity_to_mask
                        self.mapping, self.entity_to_mask = data
                        print(f"[DEBUG] 加载新版本映射表: {len(self.mapping)} 条记录")
                    elif isinstance(data, tuple) and len(data) == 3:
                        # 最新版本，包含自定义词汇映射
                        self.mapping, self.entity_to_mask, _ = data
                        print(f"[DEBUG] 加载最新版本映射表(含自定义词汇): {len(self.mapping)} 条记录")
                    else:
                        print(f"[DEBUG] 未知的映射表格式: {type(data)}")
                        self.mapping = {}
                        self.entity_to_mask = {}
            except Exception as e:
                print(f"加载脱敏映射表失败: {e}")
                self.mapping = {}
                self.entity_to_mask = {}
    
    def _save_mapping(self):
        """保存脱敏映射表"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(self.mapping_file)), exist_ok=True)
            
            # 获取自定义词汇映射（如果默认策略是HybridContextStrategy）
            custom_replacements = {}
            strategy = self.default_strategy
            if hasattr(strategy, 'get_custom_replacements') and callable(getattr(strategy, 'get_custom_replacements')):
                custom_replacements = strategy.get_custom_replacements()
            
            with open(self.mapping_file, 'wb') as f:
                # 同时保存mapping、entity_to_mask和custom_replacements三个映射表
                pickle.dump((self.mapping, self.entity_to_mask, custom_replacements), f)
        except Exception as e:
            print(f"保存脱敏映射表失败: {e}")
    
    def set_strategy(self, entity_type: str, strategy: MaskingStrategy):
        """为特定实体类型设置脱敏策略"""
        self.type_strategies[entity_type] = strategy
    
    def set_default_strategy(self, strategy: MaskingStrategy):
        """设置默认脱敏策略"""
        self.default_strategy = strategy
        
    def get_default_strategy(self) -> MaskingStrategy:
        """获取当前默认脱敏策略"""
        return self.default_strategy
    
    def add_regex_pattern(self, entity_type: str, pattern: str):
        """添加正则表达式模式"""
        self.regex_patterns[entity_type] = pattern
    
    def _get_strategy(self, entity_type: str) -> MaskingStrategy:
        """获取特定实体类型的脱敏策略"""
        return self.type_strategies.get(entity_type, self.default_strategy)
    
    def _mask_entity(self, text: str, entity_type: str) -> str:
        """对单个实体进行脱敏"""
        # 检查实体是否已存在于映射表中，确保同一实体始终使用相同的掩码
        entity_key = (text, entity_type)
        if entity_key in self.entity_to_mask:
            return self.entity_to_mask[entity_key]
        
        strategy = self._get_strategy(entity_type)
        masked_text = strategy.mask(text, entity_type) if isinstance(strategy, ContextAwareStrategy) else strategy.mask(text)
        
        # 生成唯一标识符作为脱敏后的文本，使用实体类型作为前缀
        # 格式: __MASKED_{entity_type.lower()}_{uuid.uuid4().hex[:8]}__
        # 这样可以在脱敏后的文本中保留实体类型信息，提高可读性
        unique_id = f"__MASKED_{entity_type.lower()}_{uuid.uuid4().hex[:8]}__"
        
        # 保存映射关系
        self.mapping[unique_id] = (text, entity_type)
        # 保存实体到掩码的映射，确保同一实体始终使用相同的掩码
        self.entity_to_mask[entity_key] = unique_id
        
        return unique_id
    
    def _find_regex_entities(self, text: str) -> List[Dict[str, Any]]:
        """使用正则表达式查找额外的实体"""
        entities = []
        
        for entity_type, pattern in self.regex_patterns.items():
            for match in re.finditer(pattern, text):
                entities.append({
                    "type": entity_type,
                    "start": match.start(),
                    "end": match.end(),
                    "span": match.group(),
                    "prob": 1.0  # 正则匹配的确定性为1
                })
        
        return entities
    
    def mask_text(self, text: str, save_mapping: bool = True, num_workers: int = 4, enable_parallel: bool = False) -> str:
        """对文本进行脱敏处理
        
        参数:
            text (str): 待脱敏的文本
            save_mapping (bool): 是否保存映射表，默认为True
            num_workers (int): 并行处理的工作线程数，默认为4
            enable_parallel (bool): 是否启用并行处理，默认为False
        
        返回:
            str: 脱敏后的文本
        """
        # 使用NER模型识别实体，根据设置决定是否启用并行处理
        ner_result = recognize_entities(text, save_to_file=False, num_workers=num_workers if enable_parallel else 1)
        entities = ner_result.get("output", [])
        
        # 使用正则表达式查找额外的实体
        regex_entities = self._find_regex_entities(text)
        
        # 合并实体列表
        all_entities = entities + regex_entities
        
        # 采用两阶段替换策略，避免位置偏移问题
        # 第一阶段：生成所有实体的脱敏替换文本和唯一标记
        entity_replacements = []
        
        # 如果实体数量较多且启用了并行处理，使用并行处理生成脱敏替换文本
        if len(all_entities) > 10 and enable_parallel:
            # 定义处理单个实体的函数
            def process_entity(entity):
                entity_text = entity["span"]
                entity_type = entity["type"]
                
                # 对实体进行脱敏
                masked_entity = self._mask_entity(entity_text, entity_type)
                
                # 生成唯一标记，用于第一阶段替换
                placeholder = f"__TEMP_PLACEHOLDER_{uuid.uuid4().hex}__"
                
                return (entity_text, placeholder, masked_entity)
            
            # 并行处理所有实体
            print(f"处理实体: 共{len(all_entities)}个实体，使用{num_workers}个工作线程并行处理...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                # 使用tqdm显示进度
                futures = [executor.submit(process_entity, entity) for entity in all_entities]
                for future in tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="实体脱敏进度"):
                    entity_replacements.append(future.result())
        else:
            # 实体数量较少，直接顺序处理
            for entity in all_entities:
                entity_text = entity["span"]
                entity_type = entity["type"]
                
                # 对实体进行脱敏
                masked_entity = self._mask_entity(entity_text, entity_type)
                
                # 生成唯一标记，用于第一阶段替换
                placeholder = f"__TEMP_PLACEHOLDER_{uuid.uuid4().hex}__"
                
                entity_replacements.append((entity_text, placeholder, masked_entity))
        
        # 第二阶段：执行替换
        # 先用唯一标记替换原文本中的实体，避免位置偏移
        masked_text = text
        for original, placeholder, _ in entity_replacements:
            masked_text = masked_text.replace(original, placeholder)
        
        # 再将唯一标记替换为脱敏后的文本
        for _, placeholder, masked_entity in entity_replacements:
            masked_text = masked_text.replace(placeholder, masked_entity)
        
        # 保存映射表
        if save_mapping:
            self._save_mapping()
        
        # 保存映射表
        if save_mapping:
            self._save_mapping()
        
        return masked_text
    
    def get_masked_entities(self, masked_text: str) -> Dict[str, Tuple[str, str]]:
        """获取脱敏实体信息
        
        参数:
            masked_text (str): 脱敏后的文本
        
        返回:
            Dict[str, Tuple[str, str]]: 脱敏标记到原始文本和实体类型的映射
        """
        # 查找所有脱敏标记 - 支持两种格式：旧格式 __MASKED_[hash]__ 和新格式 __MASKED_[type]_[hash]__
        pattern = r'__MASKED_(?:[a-z]+_)?[0-9a-f]{8}__'
        masked_ids = re.findall(pattern, masked_text)
        
        # 创建结果字典
        result = {}
        
        # 从映射表中查找对应的原始文本和实体类型
        for masked_id in masked_ids:
            if masked_id in self.mapping:
                result[masked_id] = self.mapping[masked_id]
        
        # 调试信息
        print(f"[DEBUG] 找到脱敏标记数量: {len(masked_ids)}")
        print(f"[DEBUG] 在映射表中找到的标记数量: {len(result)}")
        if len(masked_ids) > 0 and len(result) == 0:
            print(f"[DEBUG] 映射表类型: {type(self.mapping)}")
            print(f"[DEBUG] 映射表大小: {len(self.mapping)}")
            print(f"[DEBUG] 映射表示例: {list(self.mapping.items())[:2] if len(self.mapping) > 0 else '空'}")
            print(f"[DEBUG] 脱敏标记示例: {masked_ids[:3] if len(masked_ids) > 0 else '空'}")
        
        return result
        
    def unmask_text(self, masked_text: str, num_workers: int = 4, enable_parallel: bool = False) -> str:
        """恢复脱敏后的文本
        
        参数:
            masked_text (str): 脱敏后的文本
            num_workers (int): 并行处理的工作线程数，默认为4
            enable_parallel (bool): 是否启用并行处理，默认为False
        
        返回:
            str: 恢复后的文本
        """
        # 首先尝试使用策略类的unmask方法恢复自定义脱敏词
        # 这样可以处理HybridContextStrategy中的自定义替换
        strategy = self.default_strategy
        if hasattr(strategy, 'unmask') and callable(getattr(strategy, 'unmask')):
            # 确保策略类加载了最新的映射表
            if hasattr(strategy, '_load_mapping') and callable(getattr(strategy, '_load_mapping')):
                strategy._load_mapping()
            # 使用策略类的unmask方法先处理一遍
            masked_text = strategy.unmask(masked_text)
        
        # 查找所有脱敏标记 - 支持两种格式：旧格式 __MASKED_[hash]__ 和新格式 __MASKED_[type]_[hash]__
        pattern = r'__MASKED_(?:[a-z]+_)?[0-9a-f]{8}__'
        masked_ids = re.findall(pattern, masked_text)
        
        # 如果没有脱敏标记，直接返回原文本
        if not masked_ids:
            return masked_text
        
        # 如果脱敏标记数量较多且启用了并行处理，使用并行处理
        if len(masked_ids) > 10 and num_workers > 1 and enable_parallel:
            # 定义处理单个脱敏标记的函数
            def process_masked_id(masked_id):
                if masked_id in self.mapping:
                    original_text, _ = self.mapping[masked_id]
                    return (masked_id, original_text)
                return (masked_id, masked_id)
            
            # 并行处理所有脱敏标记
            replacements = {}
            print(f"恢复脱敏文本: 共{len(masked_ids)}个脱敏标记，使用{num_workers}个工作线程并行处理...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                # 使用tqdm显示进度
                futures = [executor.submit(process_masked_id, masked_id) for masked_id in masked_ids]
                for future in tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="恢复脱敏进度"):
                    masked_id, original_text = future.result()
                    replacements[masked_id] = original_text
            
            # 替换所有脱敏标记
            unmasked_text = masked_text
            for masked_id, original_text in replacements.items():
                unmasked_text = unmasked_text.replace(masked_id, original_text)
        else:
            # 脱敏标记数量较少，直接顺序处理
            def replace_masked(match):
                masked_id = match.group(0)
                if masked_id in self.mapping:
                    original_text, _ = self.mapping[masked_id]
                    return original_text
                return masked_id
            
            # 使用正则表达式替换所有脱敏标记
            unmasked_text = re.sub(pattern, replace_masked, masked_text)
        
        return unmasked_text