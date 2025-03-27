#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QListWidget, QListWidgetItem, QProgressBar, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon

# 确保项目根目录在Python路径中
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入模型管理器
from Data_Masking.ui.model_manager import get_model_manager


class DownloadModelsDialog(QDialog):
    """模型下载对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模型下载")
        self.setMinimumSize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 获取模型管理器
        self.model_manager = get_model_manager()
        
        # 创建界面
        self.init_ui()
        
        # 加载模型列表
        self.load_model_list()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("可用模型列表")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 说明
        desc_label = QLabel("以下是应用程序所需的模型，请选择需要下载的模型。")
        layout.addWidget(desc_label)
        
        # 模型列表
        self.model_list = QListWidget()
        self.model_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
                color: black;
            }
        """)
        layout.addWidget(self.model_list)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # 按钮区域
        buttons_layout = QHBoxLayout()
        
        self.download_button = QPushButton("下载选中模型")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.download_selected_model)
        
        self.refresh_button = QPushButton("刷新状态")
        self.refresh_button.clicked.connect(self.load_model_list)
        
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        
        buttons_layout.addWidget(self.download_button)
        buttons_layout.addWidget(self.refresh_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.close_button)
        
        layout.addLayout(buttons_layout)
        
        # 连接信号
        self.model_list.itemSelectionChanged.connect(self.on_selection_changed)
    
    def load_model_list(self):
        """加载模型列表"""
        self.model_list.clear()
        
        # 获取所有模型配置
        model_configs = self.model_manager.MODEL_CONFIGS
        
        for model_type, config in model_configs.items():
            # 检查模型是否存在
            exists, path = self.model_manager.check_model_exists(model_type)
            
            # 创建列表项
            item = QListWidgetItem()
            item.setData(Qt.UserRole, model_type)  # 存储模型类型
            
            # 设置显示文本
            status = "[已安装]" if exists else "[未安装]"
            item_text = f"{config['description']} {status}\n模型ID: {config['model_id']}"
            if exists:
                item_text += f"\n路径: {path}"
            
            item.setText(item_text)
            
            # 设置状态样式
            if exists:
                item.setForeground(Qt.darkGreen)
            else:
                item.setForeground(Qt.darkRed)
            
            # 添加到列表
            self.model_list.addItem(item)
    
    def on_selection_changed(self):
        """选择变更处理"""
        selected_items = self.model_list.selectedItems()
        if selected_items:
            item = selected_items[0]
            model_type = item.data(Qt.UserRole)
            exists, _ = self.model_manager.check_model_exists(model_type)
            
            # 只有未安装的模型才能下载
            self.download_button.setEnabled(not exists)
        else:
            self.download_button.setEnabled(False)
    
    def download_selected_model(self):
        """下载选中的模型"""
        selected_items = self.model_list.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        model_type = item.data(Qt.UserRole)
        
        # 禁用按钮，防止重复操作
        self.download_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.close_button.setEnabled(False)
        
        # 开始下载
        self.model_manager.download_model(model_type, self)
        
        # 下载完成后刷新列表
        self.load_model_list()
        
        # 恢复按钮状态
        self.refresh_button.setEnabled(True)
        self.close_button.setEnabled(True)


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = DownloadModelsDialog()
    dialog.show()
    sys.exit(app.exec_())