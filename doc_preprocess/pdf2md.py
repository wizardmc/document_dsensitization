import os
import shutil
import subprocess
import json

from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod
from magic_pdf.data.read_api import read_local_office
from magic_pdf.utils.office_to_pdf import ConvertToPdfError


def pdf_to_markdown(pdf_file_path):
    """
    将PDF文件转换为Markdown格式
    
    参数:
        pdf_file_path (str): PDF文件路径
    
    返回:
        tuple: (markdown内容, 内容列表)
    """
    name_without_suff = pdf_file_path.split(".")[0]

    # 准备环境
    local_image_dir, local_md_dir = "output/images", "output"
    image_dir = str(os.path.basename(local_image_dir))

    os.makedirs(local_image_dir, exist_ok=True)

    image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(
        local_md_dir
    )

    # 读取字节
    reader1 = FileBasedDataReader("")
    pdf_bytes = reader1.read(pdf_file_path)  # 读取PDF内容

    # 处理
    ## 创建数据集实例
    ds = PymuDocDataset(pdf_bytes)

    ## 推理
    if ds.classify() == SupportedPdfParseMethod.OCR:
        infer_result = ds.apply(doc_analyze, ocr=True)

        ## 管道
        pipe_result = infer_result.pipe_ocr_mode(image_writer)

    else:
        infer_result = ds.apply(doc_analyze, ocr=False)

        ## 管道
        pipe_result = infer_result.pipe_txt_mode(image_writer)


    ### 获取markdown内容
    md_content = pipe_result.get_markdown(image_dir)

    ### 获取内容列表内容
    content_list_content = pipe_result.get_content_list(image_dir)

    return md_content, content_list_content


def office_to_markdown(office_file_path):
    """
    将Office文档转换为Markdown格式
    
    参数:
        office_file_path (str): Office文档路径
    
    返回:
        tuple: (markdown内容, 内容列表)
    """
    # 检查soffice命令是否存在
    if not shutil.which('soffice'):
        raise FileNotFoundError(
            "无法找到'soffice'命令。请安装LibreOffice或OpenOffice，并确保'soffice'命令在系统PATH中。\n"
            "在macOS上，您可以使用Homebrew安装：brew install --cask libreoffice\n"
            "或者从官方网站下载：https://www.libreoffice.org/download/"
        )
    
    name_without_suff = office_file_path.split(".")[0]
    
    # 准备环境
    local_image_dir, local_md_dir = "output/images", "output"
    image_dir = str(os.path.basename(local_image_dir))
    
    os.makedirs(local_image_dir, exist_ok=True)
    
    image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(
        local_md_dir
    )
    
    try:
        # 处理
        ## 创建数据集实例
        ds = read_local_office(office_file_path)[0]
        
        ## 推理和管道
        pipe_result = ds.apply(doc_analyze, ocr=True).pipe_txt_mode(image_writer)
        
        ### 获取markdown内容
        md_content = pipe_result.get_markdown(image_dir)
        
        ### 获取内容列表内容
        content_list_content = pipe_result.get_content_list(image_dir)
        
        return md_content, content_list_content
    except ConvertToPdfError as e:
        raise ConvertToPdfError(f"Office文档转换失败: {str(e)}")
    except Exception as e:
        raise Exception(f"处理Office文档时出错: {str(e)}")


def document_to_markdown(file_path):
    """
    自动判断文档类型并转换为Markdown格式
    
    参数:
        file_path (str): 文档路径
    
    返回:
        tuple: (markdown内容, 内容列表)
    """
    # 获取文件扩展名
    import os
    print(f"[DEBUG] 处理文件: {file_path}")
    # 使用os.path模块正确提取文件扩展名
    _, file_extension = os.path.splitext(file_path)
    # 去掉扩展名前的点号并转为小写
    file_extension = file_extension[1:].lower() if file_extension else ""
    print(f"[DEBUG] 提取的文件扩展名: '{file_extension}'")
    
    # 尝试从文件名中推断文件类型
    if not file_extension:
        # 如果无法从文件名中提取扩展名，尝试通过文件内容或其他方式判断
        print(f"[DEBUG] 无法从文件名中提取扩展名，尝试通过文件内容判断")
        # 这里可以添加更复杂的文件类型检测逻辑
        # 暂时使用一个简单的方法：检查文件名中是否包含已知扩展名的字符串
        filename = os.path.basename(file_path).lower()
        for ext in ["pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "md"]:
            if ext in filename:
                file_extension = ext
                print(f"[DEBUG] 从文件名中推断文件类型为: {file_extension}")
                break
    
    # 根据扩展名选择处理方法
    print(f"[DEBUG] 开始根据扩展名选择处理方法...")
    if file_extension == "pdf":
        print(f"[DEBUG] 识别为PDF文件，调用pdf_to_markdown")
        return pdf_to_markdown(file_path)
    elif file_extension in ["doc", "docx", "ppt", "pptx", "xls", "xlsx"]:
        print(f"[DEBUG] 识别为Office文件，调用office_to_markdown")
        return office_to_markdown(file_path)
    elif file_extension in ["txt", "md"]:
        print(f"[DEBUG] 识别为文本文件，直接读取内容")
        # 尝试使用不同的编码读取文本文件内容
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        content = None
        
        for encoding in encodings:
            try:
                print(f"[DEBUG] 尝试使用 {encoding} 编码读取文件")
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                print(f"[DEBUG] 使用 {encoding} 编码成功读取文件")
                break
            except UnicodeDecodeError as e:
                print(f"[DEBUG] 使用 {encoding} 编码读取失败: {str(e)}")
                continue
        
        # 如果所有编码都失败，尝试二进制模式读取
        if content is None:
            print(f"[DEBUG] 所有文本编码都失败，尝试二进制模式读取")
            try:
                with open(file_path, 'rb') as f:
                    binary_content = f.read()
                # 尝试使用更宽松的编码处理二进制内容
                content = binary_content.decode('latin-1')
                print(f"[DEBUG] 二进制模式读取成功")
            except Exception as e:
                print(f"[DEBUG] 二进制模式读取失败: {str(e)}")
                raise ValueError(f"无法读取文件内容: {str(e)}")
        
        # 对于文本文件，直接返回内容和简单的内容列表
        content_list = [{
            "type": "text",
            "text": content,
            "page": 1
        }]
        return content, content_list
    else:
        # 如果仍然无法确定文件类型，尝试根据文件内容判断
        # 这里可以添加更复杂的文件内容检测逻辑
        print(f"[DEBUG] 无法确定文件类型，尝试作为Office文件处理")
        try:
            return office_to_markdown(file_path)
        except Exception as e:
            print(f"[DEBUG] 作为Office文件处理失败: {str(e)}")
            print(f"[DEBUG] 不支持的文件类型: {file_extension}")
            raise ValueError(f"不支持的文件类型: {file_extension}，请确保文件名包含正确的扩展名")


if __name__ == '__main__':
    # 示例文档路径
    doc_path = '/Users/huangweihao/all_in_one_lawchat/doc_preprocess/王鸿雁、广州繁星互娱信息科技有限公司等网络侵权责任纠纷民事一审民事判决书.docx'
    
    # 调用document_to_markdown函数
    md_content, content_list = document_to_markdown(doc_path)
    
    # 打印结果
    # 获取原始文件名（不含扩展名）
    original_name = os.path.splitext(os.path.basename(doc_path))[0]
    
    # 保存markdown内容到文件
    md_file_path = os.path.join('output', f'{original_name}.md')
    with open(md_file_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f'Markdown内容已保存至: {md_file_path}')
    
    # 保存内容列表到文件
    content_list_path = os.path.join('output', f'{original_name}_content_list.json')
    with open(content_list_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(content_list, ensure_ascii=False, indent=4))
    print(f'内容列表已保存至: {content_list_path}')

