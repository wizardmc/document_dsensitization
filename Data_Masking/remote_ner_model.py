#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import threading
from typing import Dict, List, Any, Optional
import requests
from openai import OpenAI


class RemoteNERModel:
    """远程NER模型调用类，支持OpenAI兼容API和vLLM"""

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RemoteNERModel, cls).__new__(cls)
            return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self.config = self._load_config()
                    self.client = self._init_client()
                    self._initialized = True

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config.json'
        )

        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"配置文件不存在: {config_path}\n"
                "请创建config.json文件并配置远程模型信息"
            )

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        return config

    def _init_client(self) -> OpenAI:
        """初始化OpenAI客户端"""
        model_config = self.config.get('model_config', {})

        api_base = model_config.get('api_base', 'http://localhost:8000/v1')
        api_key = model_config.get('api_key', 'dummy-key')

        print(f"初始化远程NER模型...")
        print(f"API地址: {api_base}")

        return OpenAI(
            base_url=api_base,
            api_key=api_key,
            timeout=model_config.get('timeout', 60)
        )

    def _build_prompt(self, text: str) -> List[Dict[str, str]]:
        """构建提示词"""
        prompt_template = self.config.get('prompt_template', {})
        system_prompt = prompt_template.get(
            'system_prompt',
            '你是一个专业的命名实体识别助手。'
        )
        user_prompt_template = prompt_template.get(
            'user_prompt',
            '请识别以下文本中的实体信息：\n\n{text}'
        )

        user_prompt = user_prompt_template.format(text=text)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def _parse_response(self, response_text: str, text: str) -> List[Dict[str, Any]]:
        """解析模型响应，提取实体信息"""
        try:
            # 尝试提取JSON数组
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                entities = json.loads(json_match.group())
            else:
                # 如果没找到JSON数组，尝试直接解析
                entities = json.loads(response_text)

            # 验证和修正实体信息
            valid_entities = []
            for entity in entities:
                if isinstance(entity, dict) and 'span' in entity and 'type' in entity:
                    # 如果缺少位置信息，尝试查找
                    if 'start' not in entity or 'end' not in entity:
                        start = text.find(entity['span'])
                        if start != -1:
                            entity['start'] = start
                            entity['end'] = start + len(entity['span'])
                        else:
                            continue

                    # 确保有置信度
                    if 'prob' not in entity:
                        entity['prob'] = 0.95

                    valid_entities.append(entity)

            return valid_entities

        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"响应内容: {response_text}")
            return []

    def process_text(self, text: str) -> Dict[str, Any]:
        """处理单个文本，返回NER结果"""
        model_config = self.config.get('model_config', {})

        messages = self._build_prompt(text)
        
        # 记录调用参数
        model_name = model_config.get('model_name', 'gpt-3.5-turbo')
        temperature = model_config.get('temperature', 0.1)
        max_tokens = model_config.get('max_tokens', 4096)
        
        print("=" * 80)
        print("【远程模型调用】开始")
        print(f"模型名称: {model_name}")
        print(f"Temperature: {temperature}")
        print(f"Max Tokens: {max_tokens}")
        print(f"输入文本长度: {len(text)} 字符")
        print(f"输入文本预览: {text[:200]}{'...' if len(text) > 200 else ''}")
        print("-" * 80)
        print("提示词消息:")
        for i, msg in enumerate(messages):
            print(f"  [{i+1}] {msg['role']}: {msg['content'][:150]}{'...' if len(msg['content']) > 150 else ''}")
        print("-" * 80)

        try:
            # 构建API调用参数
            api_params = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # 对于支持 enable_thinking 的模型（如通义千问），在非流式调用时必须设置为 false
            # 参考：https://help.aliyun.com/zh/model-studio/developer-reference/use-qwen-by-calling-api
            if 'qwen' in model_name.lower():
                api_params["extra_body"] = {"enable_thinking": False}
            
            response = self.client.chat.completions.create(**api_params)

            response_text = response.choices[0].message.content
            
            # 记录响应结果
            print("【远程模型响应】")
            print(f"响应长度: {len(response_text)} 字符")
            print(f"响应内容: {response_text[:500]}{'...' if len(response_text) > 500 else ''}")
            print("-" * 80)
            
            entities = self._parse_response(response_text, text)
            
            # 记录解析结果
            print("【实体识别结果】")
            print(f"识别到实体数量: {len(entities)}")
            if entities:
                print("实体详情:")
                for i, entity in enumerate(entities[:10], 1):  # 只显示前10个
                    print(f"  [{i}] {entity.get('span')} | 类型: {entity.get('type')} | "
                          f"位置: [{entity.get('start')}, {entity.get('end')}] | "
                          f"置信度: {entity.get('prob', 0):.3f}")
                if len(entities) > 10:
                    print(f"  ... 还有 {len(entities) - 10} 个实体")
            else:
                print("  未识别到任何实体")
            print("=" * 80)
            print()

            return {'output': entities}

        except Exception as e:
            print("【远程模型调用失败】")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {e}")
            print("=" * 80)
            print()
            return {'output': []}

    def get_pipeline(self):
        """兼容旧接口，返回自身"""
        return self


def recognize_entities(text, save_to_file=True, output_dir='output',
                      output_filename='result.json', max_chunk_size=450,
                      num_workers=4, enable_parallel=False):
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
    # 使用单例模式获取远程NER模型
    ner_model = RemoteNERModel()

    # 将长文本分成多个块进行处理
    if len(text) > max_chunk_size:
        import concurrent.futures
        import tqdm

        # 优化分块策略：尝试在句子边界处分割文本
        sentence_endings = r'[。！？；.!?;]'

        chunks = []
        start = 0
        while start < len(text):
            if start + max_chunk_size >= len(text):
                chunks.append(text[start:])
                break

            end = start + max_chunk_size
            last_sentence_end = end

            matches = list(re.finditer(sentence_endings, text[start:end]))
            if matches:
                last_match = matches[-1]
                last_sentence_end = start + last_match.end()

            chunks.append(text[start:last_sentence_end])
            start = last_sentence_end

        # 处理单个文本块的函数
        def process_chunk(chunk_data):
            chunk, chunk_offset = chunk_data
            chunk_result = ner_model.process_text(chunk)
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
                futures = [executor.submit(process_chunk, data) for data in chunk_data]
                for future in tqdm.tqdm(concurrent.futures.as_completed(futures),
                                       total=len(futures), desc="实体识别进度"):
                    chunk_entities = future.result()
                    all_entities.extend(chunk_entities)
        else:
            print(f"处理文本: 共{len(chunks)}个块，使用顺序处理...")

            for data in tqdm.tqdm(chunk_data, desc="实体识别进度"):
                chunk_entities = process_chunk(data)
                all_entities.extend(chunk_entities)

        # 实体去重处理
        unique_entities = {}
        for entity in all_entities:
            entity_key = (entity["span"], entity["type"])
            if entity_key not in unique_entities or \
               entity.get("prob", 0) > unique_entities[entity_key].get("prob", 0):
                unique_entities[entity_key] = entity

        all_entities = list(unique_entities.values())
        result = {'output': all_entities}
    else:
        # 文本长度在可接受范围内，直接处理
        result = ner_model.process_text(text)

        # 对短文本也进行实体去重处理
        if 'output' in result:
            all_entities = result['output']
            unique_entities = {}
            for entity in all_entities:
                entity_key = (entity["span"], entity["type"])
                if entity_key not in unique_entities or \
                   entity.get("prob", 0) > unique_entities[entity_key].get("prob", 0):
                    unique_entities[entity_key] = entity

            result['output'] = list(unique_entities.values())

    # 如果需要保存到文件
    if save_to_file:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"结果已保存到: {output_path}")

    return result


def batch_recognize_entities(texts, save_to_file=True, output_dir='output',
                            output_filename_prefix='result', max_chunk_size=450,
                            num_workers=4, enable_parallel=False):
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

    if enable_parallel and len(texts) > 1:
        print(f"批量处理文本: 共{len(texts)}个文本，使用{num_workers}个工作线程并行处理...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
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
                    False
                )
                futures.append(future)

            for future in tqdm.tqdm(concurrent.futures.as_completed(futures),
                                   total=len(futures), desc="批量实体识别进度"):
                result = future.result()
                results.append(result)
    else:
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

    # 合并和去重
    if len(results) > 1:
        all_entities = []
        for result in results:
            all_entities.extend(result.get('output', []))

        unique_entities = {}
        for entity in all_entities:
            entity_key = (entity["span"], entity["type"])
            if entity_key not in unique_entities or \
               entity.get("prob", 0) > unique_entities[entity_key].get("prob", 0):
                unique_entities[entity_key] = entity

        if results:
            results[0]['output'] = list(unique_entities.values())

    return results


# 示例用法
if __name__ == "__main__":
    sample_text = """庭审中，王鸿雁称王晗因违规直播而不能注册帐号，但其不清楚王晗违规直播的具体情况；双方口头约定以王鸿雁的身份信息进行实名注册并绑定其银行卡帐号，由王晗进行直播并向王鸿雁支付分红款，帐号归王鸿雁所有。"""

    # 单个文本处理示例
    result = recognize_entities(sample_text)
    print(f"识别到 {len(result['output'])} 个实体")

    # 批量处理示例
    sample_texts = [sample_text, sample_text[:100]]
    batch_results = batch_recognize_entities(sample_texts, save_to_file=True, enable_parallel=False)
