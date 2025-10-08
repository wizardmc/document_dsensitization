import os
import sys

# 导入远程NER模型
# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Data_Masking.remote_ner_model import RemoteNERModel

# NER模型加载器单例类（现在使用远程模型）
class NERModelLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NERModelLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # 使用远程NER模型
        self.ner_pipeline = RemoteNERModel()

    def get_pipeline(self):
        return self.ner_pipeline

    def process_text(self, text):
        """直接处理单个文本"""
        return self.ner_pipeline.process_text(text)

def recognize_entities(text, save_to_file=True, output_dir='output', output_filename='result.json', max_chunk_size=450, num_workers=4, enable_parallel=False):
    """
    使用远程NER模型识别文本中的实体

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
    # 直接使用远程NER模型的recognize_entities函数
    from Data_Masking.remote_ner_model import recognize_entities as remote_recognize_entities
    return remote_recognize_entities(text, save_to_file, output_dir, output_filename, max_chunk_size, num_workers, enable_parallel)

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
    # 直接使用远程NER模型的batch_recognize_entities函数
    from Data_Masking.remote_ner_model import batch_recognize_entities as remote_batch_recognize_entities
    return remote_batch_recognize_entities(texts, save_to_file, output_dir, output_filename_prefix, max_chunk_size, num_workers, enable_parallel)


# 示例用法
if __name__ == "__main__":
    sample_text = """庭审中，王鸿雁称王晗因违规直播而不能注册帐号，但其不清楚王晗违规直播的具体情况；双方口头约定以王鸿雁的身份信息进行实名注册并绑定其银行卡帐号，由王晗进行直播并向王鸿雁支付分红款，帐号归王鸿雁所有。王晗称其未违规直播；双方是出于娱乐的心态注册帐号并无盈利目的，当时是以王鸿雁的身份信息注册了涉案帐号，双方未对帐号归属进行约定，其也未向王鸿雁分红。繁星公司称未查询到王晗在其平台存在违规直播的记录。本院经审查认为，当事人对自己提出的主张，有责任提供证据。王鸿雁主张王晗存在违规直播记录，且双方曾对帐号归属、分红进行约定，但均未提交相关证据予以证实且王晗予以否认，违规直播方面的主张亦与中国演出协会网络表演（直播）分会回复的情况不符，故本院对王鸿雁的上述主张均不予采信。"""
    
    # 单个文本处理示例
    result = recognize_entities(sample_text)
    
    # 批量处理示例
    sample_texts = [sample_text, sample_text[:100], sample_text[100:200]]
    batch_results = batch_recognize_entities(sample_texts, save_to_file=True, enable_parallel=True)
