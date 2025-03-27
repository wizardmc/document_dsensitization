#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QGroupBox, QFormLayout, QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

class TextInputWidget(QWidget):
    """文本输入组件，允许用户直接输入或粘贴文本进行脱敏处理"""
    
    # 定义信号
    text_submitted = pyqtSignal(str)  # 文本提交信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # 创建说明标签
        desc_label = QLabel("在下方输入或粘贴文本进行脱敏处理")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("font-size: 16px; margin-bottom: 10px;")
        
        # 创建文本编辑区
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("请在此处输入或粘贴需要脱敏的文本...")
        self.text_edit.setMinimumHeight(200)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
                background-color: #fff;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #0078d7;
            }
        """)
        
        # 创建按钮区域
        buttons_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("清空")
        self.clear_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 6px 12px;
                background-color: #f8f8f8;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        
        buttons_layout.addWidget(self.clear_button)
        buttons_layout.addStretch()
        
        # 添加所有组件到主布局
        layout.addWidget(desc_label)
        layout.addWidget(self.text_edit, 1)  # 1是拉伸因子，使文本编辑区占据大部分空间
        layout.addLayout(buttons_layout)
        
        # 连接信号
        self.clear_button.clicked.connect(self.clear_text)
        
        # 连接文本编辑区的textChanged信号，以便在文本变化时自动验证
        self.text_edit.textChanged.connect(self.validate_text)
    
    def clear_text(self):
        """清空文本编辑区"""
        self.text_edit.clear()
    
    def validate_text(self):
        """验证文本并在有效时发送信号"""
        text = self.text_edit.toPlainText()
        
        # 只有当文本非空时才发送信号
        if text.strip():
            # 发送文本提交信号
            self.text_submitted.emit(text)
    
    def submit_text(self):
        """提交文本进行处理（保留此方法以兼容现有代码）"""
        text = self.text_edit.toPlainText()
        
        if not text.strip():
            QMessageBox.warning(self, "输入错误", "请输入需要处理的文本")
            return
        
        # 发送文本提交信号
        self.text_submitted.emit(text)
    
    def get_text(self):
        """获取当前文本内容"""
        return self.text_edit.toPlainText()
    
    def set_text(self, text):
        """设置文本内容"""
        self.text_edit.setText(text)