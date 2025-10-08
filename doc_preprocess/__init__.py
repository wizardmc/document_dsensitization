# doc_preprocess 包初始化文件

# 使用延迟导入避免在Python 3.9中导入magic-pdf时出错
# 只在实际使用时才导入这些函数

def pdf_to_markdown(*args, **kwargs):
    """延迟导入pdf_to_markdown函数"""
    from .pdf2md import pdf_to_markdown as _pdf_to_markdown
    return _pdf_to_markdown(*args, **kwargs)

def office_to_markdown(*args, **kwargs):
    """延迟导入office_to_markdown函数"""
    from .pdf2md import office_to_markdown as _office_to_markdown
    return _office_to_markdown(*args, **kwargs)

def document_to_markdown(*args, **kwargs):
    """延迟导入document_to_markdown函数"""
    from .pdf2md import document_to_markdown as _document_to_markdown
    return _document_to_markdown(*args, **kwargs)

# 导出模块内容
__all__ = ['pdf_to_markdown', 'office_to_markdown', 'document_to_markdown']