#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
from typing import Optional

class TempFileHandler:
    """临时文件处理类，用于将文本内容保存为临时文件"""
    
    def __init__(self):
        self.temp_files = []  # 存储创建的临时文件路径
    
    def create_temp_file(self, content: str, prefix: str = "text_input_", suffix: str = ".txt") -> str:
        """创建临时文件并写入内容
        
        Args:
            content: 要写入的文本内容
            prefix: 临时文件名前缀
            suffix: 临时文件扩展名
            
        Returns:
            临时文件的完整路径
        """
        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        
        try:
            # 写入内容
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 添加到临时文件列表
            self.temp_files.append(temp_path)
            
            return temp_path
        except Exception as e:
            # 发生错误时关闭文件描述符
            os.close(fd)
            raise e
    
    def cleanup(self):
        """清理所有创建的临时文件"""
        for temp_path in self.temp_files:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                print(f"清理临时文件时出错: {str(e)}")
        
        # 清空列表
        self.temp_files = []
    
    def __del__(self):
        """析构函数，确保临时文件被清理"""
        self.cleanup()