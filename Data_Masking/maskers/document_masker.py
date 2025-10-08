# 文档脱敏器 - 负责处理整个文档的脱敏和恢复

import os
import re
import json
import concurrent.futures
import tqdm
from typing import Dict, List, Tuple, Union, Optional, Any

from .data_masker import DataMasker


class DocumentMasker:
    """文档脱敏器 - 负责处理整个文档的脱敏和恢复"""
    def __init__(self, masker: Optional[DataMasker] = None, mapping_file: str = "doc_masking_map.pkl"):
        # 数据脱敏器
        self.masker = masker if masker else DataMasker(mapping_file)
    
    def mask_document(self, content_list: List[Dict[str, Any]], save_mapping: bool = True, num_workers: int = 4, enable_parallel: bool = False) -> List[Dict[str, Any]]:
        """对文档内容列表进行脱敏处理
        
        参数:
            content_list (List[Dict[str, Any]]): 文档内容列表
            save_mapping (bool): 是否保存映射表，默认为True
            num_workers (int): 并行处理的工作线程数，默认为4
            enable_parallel (bool): 是否启用并行处理，默认为False
        
        返回:
            List[Dict[str, Any]]: 脱敏后的文档内容列表
        """
        # 第一遍扫描：收集所有实体并建立映射关系
        print("第一遍扫描：收集所有实体并建立映射关系...")
        
        # 先将所有文本合并进行一次完整扫描，确保同一实体在整个文档中使用相同的映射
        all_text = ""
        for item in content_list:
            if "text" in item and item["text"]:
                all_text += item["text"] + "\n\n"
            if "title" in item and item["title"]:
                all_text += item["title"] + "\n\n"
        
        # 对合并后的文本进行一次扫描，建立映射关系
        if all_text:
            self.masker.mask_text(all_text, save_mapping=False)
        
        # 第二遍：使用已建立的映射关系进行实际替换
        print("第二遍：使用已建立的映射关系进行实际替换...")
        
        # 如果内容列表项数量足够多且启用了并行处理，使用并行处理
        if len(content_list) > 5 and enable_parallel:
            # 定义处理单个内容项的函数
            def process_item(item):
                masked_item = item.copy()
                
                # 对文本内容进行脱敏
                if "text" in item and item["text"]:
                    masked_item["text"] = self.masker.mask_text(item["text"], save_mapping=False, num_workers=1, enable_parallel=False)
                
                # 处理其他可能包含文本的字段
                if "title" in item and item["title"]:
                    masked_item["title"] = self.masker.mask_text(item["title"], save_mapping=False, num_workers=1, enable_parallel=False)
                
                return masked_item
            
            # 并行处理所有内容项
            masked_content_list = []
            print(f"处理文档内容: 共{len(content_list)}个内容项，使用{num_workers}个工作线程并行处理...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                # 使用tqdm显示进度
                futures = [executor.submit(process_item, item) for item in content_list]
                for future in tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="内容项脱敏进度"):
                    masked_content_list.append(future.result())
        else:
            # 内容项数量较少，直接顺序处理
            masked_content_list = []
            for item in content_list:
                masked_item = item.copy()
                
                # 对文本内容进行脱敏
                if "text" in item and item["text"]:
                    masked_item["text"] = self.masker.mask_text(item["text"], save_mapping=False)
                
                # 处理其他可能包含文本的字段
                if "title" in item and item["title"]:
                    masked_item["title"] = self.masker.mask_text(item["title"], save_mapping=False)
                
                masked_content_list.append(masked_item)
        
        # 保存映射表
        if save_mapping:
            self.masker._save_mapping()
        
        return masked_content_list
    
    def unmask_document(self, masked_content_list: List[Dict[str, Any]], num_workers: int = 4, enable_parallel: bool = False) -> List[Dict[str, Any]]:
        """恢复脱敏后的文档内容列表
        
        参数:
            masked_content_list (List[Dict[str, Any]]): 脱敏后的文档内容列表
            num_workers (int): 并行处理的工作线程数，默认为4
            enable_parallel (bool): 是否启用并行处理，默认为False
        
        返回:
            List[Dict[str, Any]]: 恢复后的文档内容列表
        """
        # 如果内容列表项数量足够多且启用了并行处理，使用并行处理
        if len(masked_content_list) > 5 and num_workers > 1 and enable_parallel:
            # 定义处理单个内容项的函数
            def process_item(item):
                unmasked_item = item.copy()
                
                # 恢复文本内容
                if "text" in item and item["text"]:
                    unmasked_item["text"] = self.masker.unmask_text(item["text"], num_workers=1, enable_parallel=False)
                
                # 恢复其他可能包含文本的字段
                if "title" in item and item["title"]:
                    unmasked_item["title"] = self.masker.unmask_text(item["title"], num_workers=1, enable_parallel=False)
                
                return unmasked_item
            
            # 并行处理所有内容项
            unmasked_content_list = []
            print(f"恢复文档内容: 共{len(masked_content_list)}个内容项，使用{num_workers}个工作线程并行处理...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                # 使用tqdm显示进度
                futures = [executor.submit(process_item, item) for item in masked_content_list]
                for future in tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="内容项恢复进度"):
                    unmasked_content_list.append(future.result())
        else:
            # 内容项数量较少，直接顺序处理
            unmasked_content_list = []
            for item in masked_content_list:
                unmasked_item = item.copy()
                
                # 恢复文本内容
                if "text" in item and item["text"]:
                    unmasked_item["text"] = self.masker.unmask_text(item["text"])
                
                # 恢复其他可能包含文本的字段
                if "title" in item and item["title"]:
                    unmasked_item["title"] = self.masker.unmask_text(item["title"])
                
                unmasked_content_list.append(unmasked_item)
        
        return unmasked_content_list
    
    def mask_markdown(self, markdown_content: str, save_mapping: bool = True, num_workers: int = 4, enable_parallel: bool = False) -> str:
        """对Markdown文本进行脱敏处理
        
        参数:
            markdown_content (str): 待脱敏的Markdown文本
            save_mapping (bool): 是否保存映射表，默认为True
            num_workers (int): 并行处理的工作线程数，默认为4
            enable_parallel (bool): 是否启用并行处理，默认为False
        
        返回:
            str: 脱敏后的Markdown文本
        """
        # 使用正则表达式匹配Markdown文本中的段落
        paragraphs = re.split(r'(\n\n|\r\n\r\n)', markdown_content)
        
        # 筛选出需要处理的段落（非空行和分隔符）
        paragraphs_to_process = []
        paragraph_indices = []
        
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip() or re.match(r'(\n\n|\r\n\r\n)', paragraph):
                # 空行或分隔符，不需要处理
                continue
            else:
                # 需要处理的段落
                paragraphs_to_process.append(paragraph)
                paragraph_indices.append(i)
        
        # 第一遍扫描：收集所有实体并建立映射关系
        print("第一遍扫描：收集所有实体并建立映射关系...")
        
        # 先对整个Markdown内容进行一次完整扫描，确保同一实体在整个文档中使用相同的映射
        self.masker.mask_text(markdown_content, save_mapping=False)
        
        # 第二遍：使用已建立的映射关系进行实际替换
        print("第二遍：使用已建立的映射关系进行实际替换...")
        
        # 如果段落数量足够多且启用了并行处理，使用并行处理
        if len(paragraphs_to_process) > 5 and enable_parallel:
            # 定义处理单个段落的函数
            def process_paragraph(paragraph):
                return self.masker.mask_text(paragraph, save_mapping=False, num_workers=1, enable_parallel=False)
            
            # 并行处理所有段落
            masked_paragraphs_processed = []
            print(f"处理Markdown文档: 共{len(paragraphs_to_process)}个段落，使用{num_workers}个工作线程并行处理...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                # 使用tqdm显示进度
                futures = [executor.submit(process_paragraph, p) for p in paragraphs_to_process]
                for future in tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="段落脱敏进度"):
                    masked_paragraphs_processed.append(future.result())
            
            # 将处理结果放回原来的位置
            result_paragraphs = paragraphs.copy()
            for idx, masked_paragraph in zip(paragraph_indices, masked_paragraphs_processed):
                result_paragraphs[idx] = masked_paragraph
            
            # 合并脱敏后的段落
            masked_markdown = ''.join(result_paragraphs)
        else:
            # 段落数量较少，直接顺序处理
            masked_paragraphs = []
            for paragraph in paragraphs:
                # 如果是空行或分隔符，直接添加
                if not paragraph.strip() or re.match(r'(\n\n|\r\n\r\n)', paragraph):
                    masked_paragraphs.append(paragraph)
                    continue
                
                # 对段落文本进行脱敏
                masked_paragraph = self.masker.mask_text(paragraph, save_mapping=False)
                masked_paragraphs.append(masked_paragraph)
            
            # 合并脱敏后的段落
            masked_markdown = ''.join(masked_paragraphs)
        
        # 保存映射表
        if save_mapping:
            self.masker._save_mapping()
        
        return masked_markdown
    
    def unmask_markdown(self, masked_markdown: str, num_workers: int = 4, enable_parallel: bool = False) -> str:
        """恢复脱敏后的Markdown文本
        
        参数:
            masked_markdown (str): 脱敏后的Markdown文本
            num_workers (int): 并行处理的工作线程数，默认为4
            enable_parallel (bool): 是否启用并行处理，默认为False
        
        返回:
            str: 恢复后的Markdown文本
        """
        # 使用正则表达式匹配Markdown文本中的段落
        paragraphs = re.split(r'(\n\n|\r\n\r\n)', masked_markdown)
        
        # 筛选出需要处理的段落（非空行和分隔符）
        paragraphs_to_process = []
        paragraph_indices = []
        
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip() or re.match(r'(\n\n|\r\n\r\n)', paragraph):
                # 空行或分隔符，不需要处理
                continue
            else:
                # 需要处理的段落
                paragraphs_to_process.append(paragraph)
                paragraph_indices.append(i)
        
        # 如果段落数量足够多且启用了并行处理，使用并行处理
        if len(paragraphs_to_process) > 5 and enable_parallel:
            # 定义处理单个段落的函数
            def process_paragraph(paragraph):
                return self.masker.unmask_text(paragraph, num_workers=1, enable_parallel=False)
            
            # 并行处理所有段落
            unmasked_paragraphs_processed = []
            print(f"恢复Markdown文档: 共{len(paragraphs_to_process)}个段落，使用{num_workers}个工作线程并行处理...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                # 使用tqdm显示进度
                futures = [executor.submit(process_paragraph, p) for p in paragraphs_to_process]
                for future in tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="段落恢复进度"):
                    unmasked_paragraphs_processed.append(future.result())
            
            # 将处理结果放回原来的位置
            result_paragraphs = paragraphs.copy()
            for idx, unmasked_paragraph in zip(paragraph_indices, unmasked_paragraphs_processed):
                result_paragraphs[idx] = unmasked_paragraph
            
            # 合并恢复后的段落
            unmasked_markdown = ''.join(result_paragraphs)
        else:
            # 段落数量较少，直接顺序处理
            unmasked_paragraphs = []
            for paragraph in paragraphs:
                # 如果是空行或分隔符，直接添加
                if not paragraph.strip() or re.match(r'(\n\n|\r\n\r\n)', paragraph):
                    unmasked_paragraphs.append(paragraph)
                    continue
                
                # 恢复段落文本
                unmasked_paragraph = self.masker.unmask_text(paragraph)
                unmasked_paragraphs.append(unmasked_paragraph)
            
            # 合并恢复后的段落
            unmasked_markdown = ''.join(unmasked_paragraphs)
        
        return unmasked_markdown
    
    def process_document_file(self, file_path: str, mask: bool, output_dir: str = "./output", save_mapping: bool = True, enable_parallel: bool = False, num_workers: int = 4) -> Tuple[str, str]:
        """处理文档文件，支持脱敏和恢复
        
        参数:
            file_path (str): 文档文件路径
            mask (bool): True表示脱敏，False表示恢复
            output_dir (str): 输出目录，默认为"./output"
            save_mapping (bool): 是否保存映射表，默认为True
            enable_parallel (bool): 是否启用并行处理，默认为False
            num_workers (int): 并行处理的工作线程数，默认为4
        
        返回:
            Tuple[str, str]: (处理后的Markdown内容, 内容列表文件路径)
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取文件名（不含扩展名）
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # 根据操作类型确定输出文件名
        operation = "masked" if mask else "unmasked"
        md_output_path = os.path.join(output_dir, f"{file_name}_{operation}.md")
        content_list_output_path = os.path.join(output_dir, f"{file_name}_{operation}_content_list.json")
        
        # 读取文件内容
        # 获取文件扩展名
        _, file_extension = os.path.splitext(file_path)
        # 去掉扩展名前的点号并转为小写
        file_extension = file_extension[1:].lower() if file_extension else ""
        
        # 根据文件类型选择不同的处理方式
        print(f"[DEBUG] process_document_file 被调用")
        print(f"[DEBUG] 文件路径: {file_path}")
        print(f"[DEBUG] 文件扩展名: {file_extension}")
        print(f"[DEBUG] 脱敏模式: {mask}")
        
        # 对于简单的文本文件，直接读取内容，避免导入magic_pdf
        if file_extension in ['txt', 'md']:
            print(f"[DEBUG] 检测到文本文件，使用简单读取方式")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                
                # 构造简单的content_list格式
                content_list = [{"type": "text", "text": text_content}]
                md_content = text_content
                print(f"[DEBUG] 文本文件读取成功，内容长度: {len(text_content)}")
            except Exception as read_error:
                print(f"[ERROR] 读取文本文件失败!")
                print(f"[ERROR] 错误类型: {type(read_error).__name__}")
                print(f"[ERROR] 错误信息: {str(read_error)}")
                import traceback
                traceback.print_exc()
                raise
        else:
            # 对于PDF、Word等复杂文档，使用document_to_markdown
            print(f"[DEBUG] 检测到复杂文档，准备导入 document_to_markdown...")
            try:
                from doc_preprocess.pdf2md import document_to_markdown
                print(f"[DEBUG] document_to_markdown 导入成功")
            except Exception as import_error:
                print(f"[ERROR] 导入 document_to_markdown 失败!")
                print(f"[ERROR] 错误类型: {type(import_error).__name__}")
                print(f"[ERROR] 错误信息: {str(import_error)}")
                print(f"[ERROR] 提示: PDF/Word文档处理需要Python 3.10+")
                import traceback
                traceback.print_exc()
                raise TypeError(
                    f"处理 {file_extension} 文件需要 Python 3.10 或更高版本。\n"
                    f"当前使用的是 Python 3.9。\n"
                    f"建议：\n"
                    f"1. 升级到 Python 3.10+\n"
                    f"2. 或者使用文本文件（.txt, .md）进行测试"
                )
            
            # 使用document_to_markdown处理文档
            print(f"[DEBUG] 开始调用 document_to_markdown...")
            try:
                md_content, content_list = document_to_markdown(file_path)
                print(f"[DEBUG] document_to_markdown 调用成功")
                print(f"[DEBUG] 获得 {len(content_list) if content_list else 0} 个内容项")
            except Exception as convert_error:
                print(f"[ERROR] document_to_markdown 调用失败!")
                print(f"[ERROR] 错误类型: {type(convert_error).__name__}")
                print(f"[ERROR] 错误信息: {str(convert_error)}")
                import traceback
                traceback.print_exc()
                raise
        
        # 根据操作类型进行脱敏或恢复处理
        if mask:
            # 脱敏处理
            processed_content_list = self.mask_document(content_list, save_mapping, num_workers, enable_parallel)
            # 将脱敏后的内容转换为Markdown格式
            md_content = ""
            for item in processed_content_list:
                if item.get("type") == "title":
                    md_content += f"# {item.get('title', '')}\n\n"
                else:
                    md_content += f"{item.get('text', '')}\n\n"
        else:
            # 恢复处理
            # 先读取脱敏后的内容列表文件
            masked_content_list_path = os.path.join(output_dir, f"{file_name}_masked_content_list.json")
            if os.path.exists(masked_content_list_path):
                with open(masked_content_list_path, 'r', encoding='utf-8') as f:
                    masked_content_list = json.load(f)
                # 恢复处理
                processed_content_list = self.unmask_document(masked_content_list, num_workers, enable_parallel)
            else:
                # 如果找不到脱敏后的内容列表文件，直接处理原始内容
                processed_content_list = self.unmask_document(content_list, num_workers, enable_parallel)
            
            # 将恢复后的内容转换为Markdown格式
            md_content = ""
            for item in processed_content_list:
                if item.get("type") == "title":
                    md_content += f"# {item.get('title', '')}\n\n"
                else:
                    md_content += f"{item.get('text', '')}\n\n"
        
        # 保存处理后的Markdown内容
        with open(md_output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # 保存处理后的内容列表
        with open(content_list_output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_content_list, f, ensure_ascii=False, indent=2)
        
        return md_content, content_list_output_path