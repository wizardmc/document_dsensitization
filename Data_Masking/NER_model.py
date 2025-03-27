from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import os
import json
import numpy as np
import threading

# 自定义JSON编码器处理numpy数据类型
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)


# NER模型加载器单例类，确保模型只初始化一次
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

def recognize_entities(text, save_to_file=True, output_dir='output', output_filename='result.json', max_chunk_size=450, num_workers=4, enable_parallel=False):
    """
    使用命名实体识别模型识别文本中的实体
    
    参数:
        text (str): 待识别的文本
        save_to_file (bool): 是否将结果保存到文件，默认为True
        output_dir (str): 输出目录，默认为'output'
        output_filename (str): 输出文件名，默认为'result.json'
        max_chunk_size (int): 每个文本块的最大字符数，默认为450
        num_workers (int): 并行处理的工作线程数，默认为4
        enable_parallel (bool): 是否启用并行处理，默认为False
    
    返回:
        dict: 识别结果的字典
    """
    # 使用单例模式获取NER管道，避免重复初始化
    ner_pipeline = NERModelLoader().get_pipeline()
    
    # 将长文本分成多个块进行处理，避免张量大小不匹配的问题
    if len(text) > max_chunk_size:
        # 优化分块策略：尝试在句子边界处分割文本
        import re
        # 中文句子结束标志：句号、问号、感叹号、分号等
        sentence_endings = r'[。！？；.!?;]'
        
        # 合并实体列表
        all_entities = []
        
        # 按照起始位置降序排序，以便从后向前替换，避免位置偏移
        all_entities.sort(key=lambda x: x["start"], reverse=True)
        
        # 分块处理，尽量在句子边界处分割
        chunks = []
        start = 0
        while start < len(text):
            # 如果剩余文本长度小于最大块大小，直接作为一个块
            if start + max_chunk_size >= len(text):
                chunks.append(text[start:])
                break
            
            # 在最大块大小范围内寻找最后一个句子结束标志
            end = start + max_chunk_size
            last_sentence_end = end
            
            # 在最大块大小范围内查找最后一个句子结束标志
            matches = list(re.finditer(sentence_endings, text[start:end]))
            if matches:
                # 找到了句子结束标志，在最后一个句子结束标志处分割
                last_match = matches[-1]
                last_sentence_end = start + last_match.end()
            
            # 添加当前块
            chunks.append(text[start:last_sentence_end])
            start = last_sentence_end
        
        # 根据设置决定是否使用多线程并行处理文本块
        import concurrent.futures
        import tqdm
        
        # 处理单个文本块的函数
        def process_chunk(chunk_data):
            chunk, chunk_offset = chunk_data
            chunk_result = ner_pipeline(chunk)
            chunk_entities = chunk_result.get('output', [])
            
            # 调整实体的位置偏移
            for entity in chunk_entities:
                entity['start'] += chunk_offset
                entity['end'] += chunk_offset
            
            return chunk_entities
        
        # 准备带有偏移量的块数据
        chunk_data = []
        offset = 0
        for chunk in chunks:
            chunk_data.append((chunk, offset))
            offset += len(chunk)
        
        # 根据设置决定是否使用并行处理
        all_entities = []
        
        if enable_parallel:
            print(f"处理文本: 共{len(chunks)}个块，使用{num_workers}个工作线程并行处理...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                # 使用tqdm显示进度
                futures = [executor.submit(process_chunk, data) for data in chunk_data]
                for future in tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="实体识别进度"):
                    chunk_entities = future.result()
                    all_entities.extend(chunk_entities)
        else:
            print(f"处理文本: 共{len(chunks)}个块，使用顺序处理...")
            
            # 顺序处理所有块
            for data in tqdm.tqdm(chunk_data, desc="实体识别进度"):
                chunk_entities = process_chunk(data)
                all_entities.extend(chunk_entities)
        
        # 实体去重处理
        unique_entities = {}
        for entity in all_entities:
            # 使用实体文本和类型作为唯一标识
            entity_key = (entity["span"], entity["type"])
            # 如果是新的唯一实体或者当前实体的概率更高，则保留
            if entity_key not in unique_entities or entity.get("prob", 0) > unique_entities[entity_key].get("prob", 0):
                unique_entities[entity_key] = entity
        
        # 转换回列表
        all_entities = list(unique_entities.values())
        
        # 构建最终结果
        result = {'output': all_entities}
    else:
        # 文本长度在可接受范围内，直接处理
        result = ner_pipeline(text)
        
        # 对短文本也进行实体去重处理
        if 'output' in result:
            all_entities = result['output']
            # 实体去重处理
            unique_entities = {}
            for entity in all_entities:
                # 使用实体文本和类型作为唯一标识
                entity_key = (entity["span"], entity["type"])
                # 如果是新的唯一实体或者当前实体的概率更高，则保留
                if entity_key not in unique_entities or entity.get("prob", 0) > unique_entities[entity_key].get("prob", 0):
                    unique_entities[entity_key] = entity
            
            # 更新结果中的实体列表
            result['output'] = list(unique_entities.values())
    
    # 如果需要保存到文件
    if save_to_file:
        # 确保output文件夹存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 将结果保存到指定文件
        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
        
        print(f"结果已保存到: {output_path}")
    
    return result

def batch_recognize_entities(texts, save_to_file=True, output_dir='output', output_filename_prefix='result', max_chunk_size=450, num_workers=4, enable_parallel=False):
    """
    批量处理多个文本的实体识别
    
    参数:
        texts (List[str]): 待识别的文本列表
        save_to_file (bool): 是否将结果保存到文件，默认为True
        output_dir (str): 输出目录，默认为'output'
        output_filename_prefix (str): 输出文件名前缀，默认为'result'
        max_chunk_size (int): 每个文本块的最大字符数，默认为450
        num_workers (int): 并行处理的工作线程数，默认为4
        enable_parallel (bool): 是否启用并行处理，默认为False
    
    返回:
        List[dict]: 识别结果的字典列表
    """
    import concurrent.futures
    import tqdm
    
    results = []
    
    # 使用线程池并行处理多个文本
    if enable_parallel and len(texts) > 1:
        print(f"批量处理文本: 共{len(texts)}个文本，使用{num_workers}个工作线程并行处理...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            # 为每个文本创建一个任务
            futures = []
            for i, text in enumerate(texts):
                output_filename = f"{output_filename_prefix}_{i}.json" if save_to_file else None
                future = executor.submit(
                    recognize_entities, 
                    text, 
                    save_to_file, 
                    output_dir, 
                    output_filename, 
                    max_chunk_size,
                    num_workers,
                    False  # 在内部处理中不再并行
                )
                futures.append(future)
            
            # 使用tqdm显示进度
            for future in tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="批量实体识别进度"):
                result = future.result()
                results.append(result)
    else:
        # 顺序处理所有文本
        print(f"批量处理文本: 共{len(texts)}个文本，使用顺序处理...")
        
        for i, text in enumerate(tqdm.tqdm(texts, desc="批量实体识别进度")):
            output_filename = f"{output_filename_prefix}_{i}.json" if save_to_file else None
            result = recognize_entities(
                text, 
                save_to_file, 
                output_dir, 
                output_filename, 
                max_chunk_size,
                num_workers,
                enable_parallel
            )
            results.append(result)
    
    # 如果处理了多个文本，对所有结果进行合并和去重
    if len(results) > 1:
        # 合并所有文本的实体
        all_entities = []
        for result in results:
            all_entities.extend(result.get('output', []))
        
        # 实体去重处理
        unique_entities = {}
        for entity in all_entities:
            # 使用实体文本和类型作为唯一标识
            entity_key = (entity["span"], entity["type"])
            # 如果是新的唯一实体或者当前实体的概率更高，则保留
            if entity_key not in unique_entities or entity.get("prob", 0) > unique_entities[entity_key].get("prob", 0):
                unique_entities[entity_key] = entity
        
        # 更新第一个结果中的实体列表（作为合并后的结果）
        if results:
            results[0]['output'] = list(unique_entities.values())
    
    return results


# 示例用法
if __name__ == "__main__":
    sample_text = """庭审中，王鸿雁称王晗因违规直播而不能注册帐号，但其不清楚王晗违规直播的具体情况；双方口头约定以王鸿雁的身份信息进行实名注册并绑定其银行卡帐号，由王晗进行直播并向王鸿雁支付分红款，帐号归王鸿雁所有。王晗称其未违规直播；双方是出于娱乐的心态注册帐号并无盈利目的，当时是以王鸿雁的身份信息注册了涉案帐号，双方未对帐号归属进行约定，其也未向王鸿雁分红。繁星公司称未查询到王晗在其平台存在违规直播的记录。本院经审查认为，当事人对自己提出的主张，有责任提供证据。王鸿雁主张王晗存在违规直播记录，且双方曾对帐号归属、分红进行约定，但均未提交相关证据予以证实且王晗予以否认，违规直播方面的主张亦与中国演出协会网络表演（直播）分会回复的情况不符，故本院对王鸿雁的上述主张均不予采信。"""
    
    # 单个文本处理示例
    result = recognize_entities(sample_text)
    
    # 批量处理示例
    sample_texts = [sample_text, sample_text[:100], sample_text[100:200]]
    batch_results = batch_recognize_entities(sample_texts, save_to_file=True, enable_parallel=True)
