#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import tempfile
from typing import Dict, List, Any, Optional

# 调试Python路径
print("Python路径:", sys.path)

# 确保项目根目录在Python路径中
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"已添加项目根目录到Python路径: {project_root}")

# 导入自定义词汇处理器
from Data_Masking.ui.custom_words_handler import CustomWordsHandler
from Data_Masking.ui.model_manager import ModelManager

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QComboBox, QTabWidget, 
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, 
    QProgressBar, QMessageBox, QFrame, QSplitter, QLineEdit,
    QGroupBox, QFormLayout, QScrollArea, QStackedWidget, QRadioButton,
    QButtonGroup, QDialog
)

# 导入自定义UI组件
from ui_components import TextInputWidget
from ui_components.temp_file_handler import TempFileHandler
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QUrl, QMimeData
from PyQt5.QtGui import QFont, QIcon, QDragEnterEvent, QDropEvent, QPixmap, QPalette, QColor
from PyQt5.QtWidgets import QApplication

# 导入脱敏相关功能
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..'))
from Data_Masking.masking import (
    MaskingStrategy, TypeBasedStrategy, ContextAwareStrategy, CustomReplacementStrategy,
    DataMasker, DocumentMasker
)
from Data_Masking.strategies import HybridContextStrategy
from Data_Masking.NER_model import NERModelLoader, batch_recognize_entities

# 设置应用样式
def set_macos_style(app):
    """设置类似macOS的应用样式"""
    app.setStyle("Fusion")
    
    # 设置调色板
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    
    app.setPalette(palette)

# 文件处理线程
class ProcessingThread(QThread):
    progress_signal = pyqtSignal(int)
    step_signal = pyqtSignal(str)  # 新增步骤信号
    finished_signal = pyqtSignal(str, str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, file_path, output_dir, masker, doc_masker, custom_words=None, is_mask=True):
        super().__init__()
        self.file_path = file_path
        self.output_dir = output_dir
        self.masker = masker
        self.doc_masker = doc_masker
        
        # 初始化自定义词汇处理器
        self.custom_words_handler = CustomWordsHandler(mapping_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ui', 'maps', 'custom_words.pkl'))
        
        # 从masker的策略中获取最新custom_words
        strategy = masker.get_default_strategy()
        if hasattr(strategy, 'get_custom_replacements'):
            # 获取策略中的自定义词汇
            strategy_words = strategy.get_custom_replacements()
            # 同步策略中的自定义词汇到处理器
            for original, replacement in strategy_words.items():
                self.custom_words_handler.add_custom_word(original, replacement)
            
            # 合并传入的自定义词汇
            if custom_words:
                for original, replacement in custom_words.items():
                    self.custom_words_handler.add_custom_word(original, replacement)
            
            # 获取最终的自定义词汇
            self.custom_words = self.custom_words_handler.get_custom_words()
        else:
            # 如果策略不支持自定义词汇，则直接使用传入的自定义词汇
            self.custom_words = custom_words or {}
            # 将传入的自定义词汇添加到处理器
            for original, replacement in self.custom_words.items():
                self.custom_words_handler.add_custom_word(original, replacement)
        self.is_mask = is_mask  # True表示脱敏，False表示解敏
    
    def run(self):
        try:
            print(f"[DEBUG] 开始处理文件: {self.file_path}")
            print(f"[DEBUG] 输出目录: {self.output_dir}")
            print(f"[DEBUG] 是否脱敏: {self.is_mask}")
            
            # 设置混合上下文感知策略
            print("[DEBUG] 正在设置混合上下文感知策略...")
            hybrid_strategy = HybridContextStrategy(mapping_file=os.path.join(MAP_FOLDER, 'hybrid_mapping.pkl'))
            self.masker.set_default_strategy(hybrid_strategy)
            print("[DEBUG] 策略设置完成")
            
            # 将自定义脱敏词添加到混合策略中
            if self.custom_words:
                print(f"[DEBUG] 添加 {len(self.custom_words)} 个自定义脱敏词...")
                for original, replacement in self.custom_words.items():
                    try:
                        if not hybrid_strategy.set_custom_replacement(original, replacement):
                            print(f"警告: 无法添加自定义脱敏词: {original} -> {replacement}")
                    except Exception as e:
                        print(f"添加自定义脱敏词时出错: {original} -> {replacement}, 错误: {str(e)}")
            
            # 初始化进度
            from Data_Masking.ui.progress_steps import ProgressSteps
            
            # 文件准备阶段
            self.step_signal.emit("准备处理文件...")
            self.progress_signal.emit(10)
            self.msleep(100)
            
            # 策略加载阶段
            self.step_signal.emit("加载脱敏策略...")
            self.progress_signal.emit(20)
            self.msleep(100)
            
            if self.is_mask:
                # 文档转换阶段
                self.step_signal.emit("转换文档格式...（耗时较长，请耐心等待）")
                self.progress_signal.emit(30)
                self.msleep(100)
                
                # 获取输出文件路径
                original_name = os.path.splitext(os.path.basename(self.file_path))[0]
                masked_md_file_path = os.path.join(self.output_dir, f'{original_name}_masked.md')
                masked_content_list_path = os.path.join(self.output_dir, f'{original_name}_masked_content_list.json')
                
                print(f"[DEBUG] 目标输出文件: {masked_md_file_path}")
                
                # 检查是否只需要应用自定义脱敏词（如果文件已存在且有自定义脱敏词）
                if os.path.exists(masked_md_file_path) and self.custom_words:
                    print(f"[DEBUG] 检测到已有脱敏文件，使用混合策略重新处理: {masked_md_file_path}")
                    # 读取现有的脱敏文件
                    with open(masked_md_file_path, 'r', encoding='utf-8') as f:
                        masked_md_content = f.read()
                    
                    # 使用自定义词汇处理器应用自定义脱敏词
                    # 这样可以确保所有自定义词汇都被正确应用
                    masked_md_content = self.custom_words_handler.apply_custom_words(masked_md_content)
                    
                    # 保存修改后的内容
                    with open(masked_md_file_path, 'w', encoding='utf-8') as f:
                        f.write(masked_md_content)
                else:
                    # 执行完整的脱敏处理
                    print(f"[DEBUG] 开始调用 process_document_file...")
                    print(f"[DEBUG] 文件扩展名: {os.path.splitext(self.file_path)[1]}")
                    try:
                        masked_md_content, masked_content_list_path = self.doc_masker.process_document_file(
                            file_path=self.file_path,
                            mask=True,
                            output_dir=self.output_dir,
                            save_mapping=True,
                            enable_parallel=False
                        )
                        print(f"[DEBUG] process_document_file 调用成功")
                    except Exception as doc_error:
                        print(f"[ERROR] process_document_file 调用失败!")
                        print(f"[ERROR] 错误类型: {type(doc_error).__name__}")
                        print(f"[ERROR] 错误信息: {str(doc_error)}")
                        import traceback
                        print(f"[ERROR] 完整堆栈跟踪:")
                        traceback.print_exc()
                        raise
                
                # 提取敏感实体阶段
                self.step_signal.emit("提取敏感实体...")
                for i in range(30, 50):
                    self.progress_signal.emit(i)
                    self.msleep(20)
                
                # 脱敏替换阶段
                self.step_signal.emit("执行脱敏替换...")
                for i in range(50, 70):
                    self.progress_signal.emit(i)
                    self.msleep(20)
                
                # 结果保存阶段
                self.step_signal.emit("保存处理结果...")
                for i in range(70, 90):
                    self.progress_signal.emit(i)
                    self.msleep(20)
                
                # 完成阶段
                self.step_signal.emit("处理完成")
                self.progress_signal.emit(100)
                self.msleep(100)
                
                # 发送完成信号
                self.finished_signal.emit(masked_md_file_path, os.path.basename(masked_md_file_path))
            else:
                # 获取原始文件名（不含扩展名和_masked后缀）
                original_name = os.path.splitext(os.path.basename(self.file_path))[0]
                if original_name.endswith('_masked'):
                    original_name = original_name.replace('_masked', '')
                
                # 读取脱敏后的内容
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    masked_content = f.read()
                
                # 解析脱敏内容阶段
                self.step_signal.emit("解析脱敏内容...")
                self.progress_signal.emit(50)
                self.msleep(100)
                
                # 直接使用映射表恢复内容
                unmasked_content = self.masker.unmask_text(masked_content)
                
                # 执行解敏替换阶段
                self.step_signal.emit("执行解敏替换...")
                self.progress_signal.emit(70)
                self.msleep(100)
                
                # 获取恢复后的文件路径
                unmasked_md_file_path = os.path.join(self.output_dir, f'{original_name}_unmasked.md')
                
                # 保存恢复后的内容
                with open(unmasked_md_file_path, 'w', encoding='utf-8') as f:
                    f.write(unmasked_content)
                
                # 完成进度
                self.progress_signal.emit(100)
                
                # 发送完成信号
                self.finished_signal.emit(unmasked_md_file_path, os.path.basename(unmasked_md_file_path))
            
        except Exception as e:
            self.error_signal.emit(str(e))

# 拖放文件区域
class DropArea(QWidget):
    file_dropped = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # 创建拖放提示标签
        self.drop_label = QLabel("拖放文件到此处或点击选择文件")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 8px;
                padding: 30px;
                background-color: #f8f8f8;
                font-size: 16px;
            }
            QLabel:hover {
                background-color: #f0f0f0;
                border-color: #0078d7;
            }
        """)
        
        # 创建文件名标签
        self.filename_label = QLabel()
        self.filename_label.setAlignment(Qt.AlignCenter)
        self.filename_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #0078d7;
                margin-top: 5px;
            }
        """)
        self.filename_label.setVisible(False)
        
        # 添加到布局
        layout.addWidget(self.drop_label)
        layout.addWidget(self.filename_label)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            # 显示文件名
            self.filename_label.setText(f"已选择文件: {os.path.basename(file_path)}")
            self.filename_label.setVisible(True)
            self.file_dropped.emit(file_path)
    
    def mousePressEvent(self, event):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "支持的文件 (*.pdf *.doc *.docx *.txt *.md)"
        )
        if file_path:
            # 显示文件名
            self.filename_label.setText(f"已选择文件: {os.path.basename(file_path)}")
            self.filename_label.setVisible(True)
            self.file_dropped.emit(file_path)

# 自定义脱敏词对话框
class CustomWordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加自定义脱敏词")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        self.original_word = QLineEdit()
        self.replacement_word = QLineEdit()
        
        form_layout.addRow("原始词汇:", self.original_word)
        form_layout.addRow("替换词汇:", self.replacement_word)
        
        layout.addLayout(form_layout)
        
        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("添加")
        self.cancel_button = QPushButton("取消")
        
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
        # 连接信号
        self.add_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.close)
    
    def accept(self):
        if not self.original_word.text() or not self.replacement_word.text():
            QMessageBox.warning(self, "输入错误", "原始词汇和替换词汇不能为空")
            return
        
        self.close()
    
    def get_values(self):
        return self.original_word.text(), self.replacement_word.text()

# 主窗口
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口属性
        self.setWindowTitle("文档脱敏工具 v0.1.0")
        self.setMinimumSize(900, 600)
        
        # 初始化变量
        self.current_file_path = None
        self.masked_file_path = None
        self.input_text = None  # 存储用户输入的文本
        self.input_mode = "file"  # 输入模式：file或text
        
        # 创建状态栏并添加居中的备注信息
        self.statusBar = self.statusBar()
        # 创建一个标签用于显示状态栏信息
        status_label = QLabel("当前为早期测试版本，可能存在bug，谨慎用于严肃场景。反馈、交流加wx:higher-farther")
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet("color: #666; font-style: italic;") # 应用样式到标签

        # 添加伸缩项、标签、伸缩项以实现居中
        self.statusBar.addWidget(QWidget(), 1)  # 左侧伸缩项
        self.statusBar.addWidget(status_label)  # 居中标签
        self.statusBar.addWidget(QWidget(), 1)  # 右侧伸缩项
        
        # 初始化自定义词汇处理器
        self.custom_words_handler = CustomWordsHandler(mapping_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ui', 'maps', 'custom_words.pkl'))
        self.custom_words = self.custom_words_handler.get_custom_words()
        self.processing_thread = None
        
        # 创建临时文件处理器
        self.temp_file_handler = TempFileHandler()
        
        # 创建堆叠窗口部件，用于切换不同的页面
        self.stacked_widget = QStackedWidget()
        
        # 创建上传页面
        self.upload_page = self.create_upload_page()
        
        # 创建处理页面
        self.process_page = self.create_process_page()
        
        # 添加页面到堆叠窗口部件
        self.stacked_widget.addWidget(self.upload_page)
        self.stacked_widget.addWidget(self.process_page)
        
        # 设置中央窗口部件
        self.setCentralWidget(self.stacked_widget)
        
        # 初始化脱敏器
        self.init_masker()
        
        # 初始化模型管理器
        self.model_manager = None

        # 创建菜单栏
        self.create_menu_bar()

        # 不再在启动时检查模型
        # self.check_models()
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 设置菜单
        settings_menu = menubar.addMenu("设置")

        # 远程模型配置
        remote_model_action = settings_menu.addAction("远程模型配置")
        remote_model_action.triggered.connect(self.open_remote_model_config)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        # 下载模型
        download_models_action = help_menu.addAction("下载PDF处理模型")
        download_models_action.triggered.connect(lambda: self.check_models(silent=False))

    def open_remote_model_config(self):
        """打开远程模型配置对话框"""
        from Data_Masking.ui.remote_model_config_dialog import RemoteModelConfigDialog
        dialog = RemoteModelConfigDialog(self)
        dialog.exec_()

    def init_masker(self):
        """初始化脱敏器"""
        global MAP_FOLDER, OUTPUT_FOLDER, UPLOAD_FOLDER
        
        # 配置文件夹路径
        MAP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'maps')
        OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
        UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        
        # 确保目录存在
        os.makedirs(MAP_FOLDER, exist_ok=True)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # 初始化脱敏器
        self.masker = DataMasker(mapping_file=os.path.join(MAP_FOLDER, 'masking_map.pkl'))
        self.doc_masker = DocumentMasker(masker=self.masker, mapping_file=os.path.join(MAP_FOLDER, 'doc_masking_map.pkl'))
        
        # 设置默认策略
        self.type_strategy = TypeBasedStrategy()  # 保留用于获取实体类型列表
        self.hybrid_strategy = HybridContextStrategy(mapping_file=os.path.join(MAP_FOLDER, 'hybrid_mapping.pkl'))
        self.masker.set_default_strategy(self.hybrid_strategy)
        
        # 同步混合策略和自定义词汇处理器
        self.custom_words_handler.sync_with_strategy(self.hybrid_strategy)
        
        # 获取最终的自定义词汇
        self.custom_words = self.custom_words_handler.get_custom_words()
    
    def create_upload_page(self):
        """创建上传页面"""
        page = QWidget()
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("文档脱敏工具")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        
        # 描述
        desc_label = QLabel("安全处理敏感数据，保护隐私信息")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("font-size: 16px; margin-bottom: 30px;")
        
        # 创建选项卡控件
        self.input_tabs = QTabWidget()
        self.input_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 10px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background-color: #e0e0e0;
            }
        """)
        
        # 创建文件上传选项卡
        file_tab = QWidget()
        file_layout = QVBoxLayout(file_tab)
        
        # 拖放区域
        self.drop_area = DropArea()
        file_layout.addWidget(self.drop_area)
        
        # 创建文本输入选项卡
        text_tab = QWidget()
        text_layout = QVBoxLayout(text_tab)
        
        # 文本输入组件
        self.text_input = TextInputWidget()
        text_layout.addWidget(self.text_input)
        
        # 添加选项卡
        self.input_tabs.addTab(file_tab, "文件上传")
        self.input_tabs.addTab(text_tab, "文本输入")
        
        # 功能选择区域
        function_group = QGroupBox("选择功能")
        function_layout = QVBoxLayout()
        
        # 单选按钮组
        self.mask_radio = QRadioButton("脱敏处理")
        self.unmask_radio = QRadioButton("恢复原文")
        self.mask_radio.setChecked(True)  # 默认选择脱敏处理
        
        function_layout.addWidget(self.mask_radio)
        function_layout.addWidget(self.unmask_radio)
        function_group.setLayout(function_layout)
        
        # 策略信息区域
        strategy_group = QGroupBox("脱敏策略")
        strategy_layout = QVBoxLayout()
        
        strategy_info = QLabel("使用混合上下文感知策略进行脱敏处理")
        strategy_info.setStyleSheet("font-weight: bold;")
        
        strategy_layout.addWidget(strategy_info)
        strategy_group.setLayout(strategy_layout)
        
        # 按钮区域
        buttons_layout = QHBoxLayout()
        self.process_button = QPushButton("开始处理")
        self.process_button.setEnabled(False)  # 初始禁用，直到选择文件或输入文本
        self.process_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0063b1;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.process_button)
        buttons_layout.addStretch()
        
        # 添加所有组件到主布局
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addWidget(self.input_tabs)
        layout.addWidget(function_group)
        layout.addWidget(strategy_group)
        layout.addSpacing(20)
        layout.addLayout(buttons_layout)
        layout.addStretch()
        
        # 设置页面布局
        page.setLayout(layout)
        
        # 连接信号
        self.drop_area.file_dropped.connect(self.on_file_dropped)
        self.text_input.text_submitted.connect(self.on_text_submitted)
        self.process_button.clicked.connect(self.on_process_clicked)
        self.mask_radio.toggled.connect(self.on_function_changed)
        self.input_tabs.currentChanged.connect(self.on_input_tabs_changed)
        
        return page
    
    def create_process_page(self):
        """创建处理页面"""
        page = QWidget()
        layout = QVBoxLayout()
        
        # 标题区域
        header_layout = QHBoxLayout()
        
        self.file_label = QLabel("文件: ")
        self.file_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        back_button = QPushButton("返回")
        back_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        
        header_layout.addWidget(back_button)
        header_layout.addWidget(self.file_label)
        header_layout.addStretch()
        
        # 进度显示区域
        progress_group = QGroupBox("处理进度")
        progress_layout = QVBoxLayout()
        
        # 步骤标签
        self.step_label = QLabel("准备就绪")
        self.step_label.setStyleSheet("font-weight: bold;")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        
        progress_layout.addWidget(self.step_label)
        progress_layout.addWidget(self.progress_bar)
        progress_group.setLayout(progress_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：文档内容
        content_group = QGroupBox("文档内容")
        content_layout = QVBoxLayout()
        
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        
        content_layout.addWidget(self.content_text)
        content_group.setLayout(content_layout)
        
        # 右侧：脱敏实体和自定义脱敏词
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 脱敏实体表格
        entities_group = QGroupBox("脱敏实体")
        entities_layout = QVBoxLayout()
        
        self.entities_table = QTableWidget(0, 3)
        self.entities_table.setHorizontalHeaderLabels(["脱敏ID", "原始文本", "实体类型"])
        self.entities_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        entities_layout.addWidget(self.entities_table)
        entities_group.setLayout(entities_layout)
        
        # 自定义脱敏词区域
        custom_group = QGroupBox("自定义脱敏词")
        custom_layout = QVBoxLayout()
        
        self.custom_table = QTableWidget(0, 2)
        self.custom_table.setHorizontalHeaderLabels(["原始词汇", "替换词汇"])
        self.custom_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        custom_buttons_layout = QHBoxLayout()
        add_custom_button = QPushButton("添加")
        remove_custom_button = QPushButton("删除")
        
        custom_buttons_layout.addWidget(add_custom_button)
        custom_buttons_layout.addWidget(remove_custom_button)
        
        custom_layout.addWidget(self.custom_table)
        custom_layout.addLayout(custom_buttons_layout)
        custom_group.setLayout(custom_layout)
        
        # 添加到右侧布局
        right_layout.addWidget(entities_group)
        right_layout.addWidget(custom_group)
        
        # 添加到分割器
        splitter.addWidget(content_group)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 300])  # 设置初始大小比例
        
        # 操作按钮区域
        buttons_layout = QHBoxLayout()
        
        self.mask_button = QPushButton("执行脱敏")
        self.mask_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0063b1;
            }
        """)
        
        self.unmask_button = QPushButton("恢复原文")
        self.unmask_button.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
        """)
        
        self.save_button = QPushButton("保存文件")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #f0ad4e;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #eea236;
            }
        """)
        
        self.copy_button = QPushButton("复制到剪贴板")
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: #5bc0de;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #46b8da;
            }
        """)
        
        buttons_layout.addWidget(self.mask_button)
        buttons_layout.addWidget(self.unmask_button)
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.copy_button)
        
        # 添加所有组件到主布局
        layout.addLayout(header_layout)
        layout.addWidget(progress_group)
        layout.addWidget(splitter, 1)  # 设置拉伸因子为1，使分割器占据大部分空间
        layout.addLayout(buttons_layout)
        
        # 设置页面布局
        page.setLayout(layout)
        
        # 连接信号
        back_button.clicked.connect(self.on_back_clicked)
        self.mask_button.clicked.connect(self.on_mask_clicked)
        self.unmask_button.clicked.connect(self.on_unmask_clicked)
        self.save_button.clicked.connect(self.on_save_clicked)
        self.copy_button.clicked.connect(self.on_copy_clicked)  # 连接复制按钮的点击事件
        add_custom_button.clicked.connect(self.on_add_custom_clicked)
        remove_custom_button.clicked.connect(self.on_remove_custom_clicked)
        
        return page
    
    def check_models(self, silent=True):
        """检查必要的模型是否存在，如果不存在则提示下载
        
        Args:
            silent: 是否为静默模式，静默模式下不会弹出任何提示框，只在缺少模型时才弹出下载框
        """
        try:
            # 初始化模型管理器
            if self.model_manager is None:
                self.model_manager = ModelManager()
            
            # 检查并下载模型，使用静默模式
            models_available = self.model_manager.check_and_download_models(parent=self, silent=silent)
            
            # 如果静默模式下发现缺少模型，则再次以非静默模式检查，显示下载提示
            if silent and not models_available:
                self.model_manager.check_and_download_models(parent=self, silent=False)
        except Exception as e:
            QMessageBox.warning(self, "模型检查错误", f"检查模型时出错: {str(e)}")
    
    def on_file_dropped(self, file_path):
        """处理文件拖放事件"""
        # 检查文件类型
        if not file_path.lower().endswith(('.pdf', '.doc', '.docx', '.txt', '.md')):
            QMessageBox.warning(self, "文件类型错误", "不支持的文件类型，请上传PDF、DOC、DOCX、TXT或MD格式的文件")
            return
        
        # 保存文件路径
        self.current_file_path = file_path
        self.input_mode = "file"  # 设置输入模式为文件
        self.input_text = None  # 清空文本输入
        
        # 启用处理按钮
        self.process_button.setEnabled(True)
    
    def on_text_submitted(self, text):
        """处理文本提交事件"""
        if not text.strip():
            QMessageBox.warning(self, "输入错误", "请输入需要处理的文本")
            return
        
        # 保存输入文本
        self.input_text = text
        self.input_mode = "text"  # 设置输入模式为文本
        self.current_file_path = None  # 清空文件路径
        
        # 启用处理按钮
        self.process_button.setEnabled(True)
    
    def on_process_clicked(self):
        """处理按钮点击事件"""
        # 检查输入模式
        if self.input_mode == "file" and not self.current_file_path:
            QMessageBox.warning(self, "文件错误", "请先选择文件")
            return
        elif self.input_mode == "text" and not self.input_text:
            QMessageBox.warning(self, "输入错误", "请先输入或粘贴文本")
            return
        
        # 获取选择的功能
        is_mask = self.mask_radio.isChecked()
        
        # 使用混合上下文感知策略
        hybrid_strategy = HybridContextStrategy(mapping_file=os.path.join(MAP_FOLDER, 'hybrid_mapping.pkl'))
        self.masker.set_default_strategy(hybrid_strategy)
        
        # 切换到处理页面
        self.stacked_widget.setCurrentIndex(1)
        
        # 处理文本输入模式
        file_path_to_process = self.current_file_path
        if self.input_mode == "text":
            try:
                # 创建临时文件并写入文本内容
                file_path_to_process = self.temp_file_handler.create_temp_file(
                    content=self.input_text,
                    prefix="text_input_",
                    suffix=".txt"
                )
                # 更新文件标签
                self.file_label.setText(f"文本输入: {os.path.basename(file_path_to_process)}")
            except Exception as e:
                QMessageBox.critical(self, "创建临时文件错误", f"处理文本时出错: {str(e)}")
                return
        else:
            # 更新文件标签
            self.file_label.setText(f"文件: {os.path.basename(self.current_file_path)}")
        
        # 清空内容和表格
        self.content_text.clear()
        self.entities_table.setRowCount(0)
        self.custom_table.setRowCount(0)
        
        # 显示进度条
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # 创建并启动处理线程
        self.processing_thread = ProcessingThread(
            file_path=file_path_to_process,
            output_dir=OUTPUT_FOLDER,
            masker=self.masker,
            doc_masker=self.doc_masker,
            custom_words=self.custom_words,
            is_mask=is_mask
        )
        
        # 连接信号
        self.processing_thread.progress_signal.connect(self.update_progress)
        self.processing_thread.step_signal.connect(self.update_step)  # 连接步骤信号
        self.processing_thread.finished_signal.connect(self.on_processing_finished)
        self.processing_thread.error_signal.connect(self.on_processing_error)
        
        # 启动线程
        self.processing_thread.start()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def update_step(self, step_text):
        """更新步骤显示"""
        self.step_label.setText(step_text)
        self.progress_bar.setVisible(True)
    
    def on_processing_finished(self, file_path, filename):
        """处理完成事件"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 保存处理后的文件路径
        self.masked_file_path = file_path
        
        # 读取处理后的内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 显示内容
            self.content_text.setText(content)
            
            # 如果是脱敏文件，显示脱敏实体信息
            if filename.endswith('_masked.md'):
                # 获取脱敏实体信息
                masked_entities = self.masker.get_masked_entities(content)
                
                # 更新实体表格
                self.entities_table.setRowCount(len(masked_entities))
                for i, (mask_id, (original, entity_type)) in enumerate(masked_entities.items()):
                    self.entities_table.setItem(i, 0, QTableWidgetItem(mask_id))
                    self.entities_table.setItem(i, 1, QTableWidgetItem(original))
                    self.entities_table.setItem(i, 2, QTableWidgetItem(entity_type))
                
                # 更新自定义替换词表格
                self.custom_words = self.hybrid_strategy.get_custom_replacements()
                self.custom_table.setRowCount(0)
                for original, replacement in self.custom_words.items():
                    row = self.custom_table.rowCount()
                    self.custom_table.insertRow(row)
                    self.custom_table.setItem(row, 0, QTableWidgetItem(original))
                    self.custom_table.setItem(row, 1, QTableWidgetItem(replacement))
            
            # 显示成功消息
            QMessageBox.information(self, "处理成功", f"文件处理成功: {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "读取错误", f"读取处理后的文件时出错: {str(e)}")
    
    def on_processing_error(self, error_msg):
        """处理错误事件"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 显示错误消息
        QMessageBox.critical(self, "处理错误", f"处理文件时出错: {error_msg}")
        
        # 切换回上传页面
        self.stacked_widget.setCurrentIndex(0)
    
    def on_back_clicked(self):
        """返回按钮点击事件"""
        # 切换回上传页面
        self.stacked_widget.setCurrentIndex(0)
    
    def on_mask_clicked(self):
        """执行脱敏按钮点击事件"""
        # 检查输入模式
        if self.input_mode == "file" and not self.current_file_path:
            QMessageBox.warning(self, "文件错误", "请先选择文件")
            return
        elif self.input_mode == "text" and not self.input_text:
            QMessageBox.warning(self, "输入错误", "请先输入或粘贴文本")
            return
        
        # 处理文本输入模式
        file_path_to_process = self.current_file_path
        if self.input_mode == "text":
            try:
                # 创建临时文件并写入文本内容
                file_path_to_process = self.temp_file_handler.create_temp_file(
                    content=self.input_text,
                    prefix="text_input_",
                    suffix=".txt"
                )
            except Exception as e:
                QMessageBox.critical(self, "创建临时文件错误", f"处理文本时出错: {str(e)}")
                return
        
        # 显示进度条
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # 创建并启动处理线程
        # 确保使用最新的自定义词汇
        self.custom_words = self.custom_words_handler.get_custom_words()
        
        self.processing_thread = ProcessingThread(
            file_path=file_path_to_process,
            output_dir=OUTPUT_FOLDER,
            masker=self.masker,
            doc_masker=self.doc_masker,
            custom_words=self.custom_words,
            is_mask=True
        )
        
        # 连接信号
        self.processing_thread.progress_signal.connect(self.update_progress)
        self.processing_thread.finished_signal.connect(self.on_processing_finished)
        self.processing_thread.error_signal.connect(self.on_processing_error)
        
        # 启动线程
        self.processing_thread.start()
    
    def on_unmask_clicked(self):
        """恢复原文按钮点击事件"""
        if not self.masked_file_path:
            QMessageBox.warning(self, "文件错误", "没有脱敏后的文件")
            return
        
        # 显示进度条
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # 创建并启动处理线程
        # 确保使用最新的自定义词汇
        self.custom_words = self.custom_words_handler.get_custom_words()
        
        self.processing_thread = ProcessingThread(
            file_path=self.masked_file_path,
            output_dir=OUTPUT_FOLDER,
            masker=self.masker,
            doc_masker=self.doc_masker,
            custom_words=self.custom_words,
            is_mask=False
        )
        
        # 连接信号
        self.processing_thread.progress_signal.connect(self.update_progress)
        self.processing_thread.finished_signal.connect(self.on_processing_finished)
        self.processing_thread.error_signal.connect(self.on_processing_error)
        
        # 启动线程
        self.processing_thread.start()
    
    def on_save_clicked(self):
        """保存文件按钮点击事件"""
        if not self.masked_file_path:
            QMessageBox.warning(self, "文件错误", "没有处理后的文件")
            return
        
        # 选择保存路径
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", os.path.basename(self.masked_file_path), "Markdown文件 (*.md)"
        )
        
        if save_path:
            try:
                # 复制文件
                with open(self.masked_file_path, 'r', encoding='utf-8') as src_file:
                    content = src_file.read()
                
                with open(save_path, 'w', encoding='utf-8') as dst_file:
                    dst_file.write(content)
                
                QMessageBox.information(self, "保存成功", f"文件已保存到: {save_path}")
            
            except Exception as e:
                QMessageBox.critical(self, "保存错误", f"保存文件时出错: {str(e)}")
    
    def on_function_changed(self):
        """功能选择改变事件"""
        # 根据选择的功能启用/禁用相关控件
        is_mask = self.mask_radio.isChecked()
    
    def on_input_tabs_changed(self, index):
        """输入选项卡切换事件"""
        # 根据选择的选项卡更新输入模式
        if index == 0:  # 文件上传选项卡
            self.input_mode = "file"
            # 如果已经选择了文件，启用处理按钮
            self.process_button.setEnabled(self.current_file_path is not None)
        else:  # 文本输入选项卡
            self.input_mode = "text"
            # 如果已经输入了文本，启用处理按钮
            self.process_button.setEnabled(self.input_text is not None and self.input_text.strip() != "")
    
    def on_add_custom_clicked(self):
        """添加自定义脱敏词按钮点击事件"""
        dialog = CustomWordDialog(self)
        
        # 连接信号
        dialog.add_button.clicked.connect(lambda: self.add_custom_word(dialog))
        
        # 显示模态对话框
        dialog.exec_()
    
    def add_custom_word(self, dialog):
        """添加自定义脱敏词"""
        original, replacement = dialog.get_values()
        
        if not original or not replacement:
            return
        
        try:
            # 添加到混合策略并验证
            success = self.hybrid_strategy.set_custom_replacement(original, replacement)
            if not success:
                QMessageBox.warning(self, "添加失败", "自定义脱敏词添加失败")
                return
            
            # 同时添加到自定义词汇处理器
            self.custom_words_handler.add_custom_word(original, replacement)
            
            # 更新UI显示
            self.custom_words = self.hybrid_strategy.get_custom_replacements()
            row = self.custom_table.rowCount()
            self.custom_table.insertRow(row)
            self.custom_table.setItem(row, 0, QTableWidgetItem(original))
            self.custom_table.setItem(row, 1, QTableWidgetItem(replacement))
            
            # 显示成功消息
            QMessageBox.information(self, "添加成功", "自定义脱敏词已添加")
        except Exception as e:
            QMessageBox.critical(self, "添加错误", f"添加自定义脱敏词时出错: {str(e)}")
    
    def on_remove_custom_clicked(self):
        """删除自定义脱敏词按钮点击事件"""
        if not self.custom_table.selectedItems():
            QMessageBox.warning(self, "选择错误", "请先选择要删除的自定义脱敏词")
            return
            
        try:
            # 获取选中的行
            selected_rows = set()
            for item in self.custom_table.selectedItems():
                selected_rows.add(item.row())
            
            # 从后往前删除，避免索引变化
            for row in sorted(selected_rows, reverse=True):
                # 获取原始词汇
                original = self.custom_table.item(row, 0).text()
                
                # 从混合策略中移除
                success = self.hybrid_strategy.remove_custom_replacement(original)
                if not success:
                    QMessageBox.warning(self, "删除失败", f"无法删除'{original}'")
                    continue
                
                # 同时从自定义词汇处理器中移除
                self.custom_words_handler.remove_custom_word(original)
                
                # 更新UI显示
                self.custom_words = self.hybrid_strategy.get_custom_replacements()
                self.custom_table.removeRow(row)
            
            QMessageBox.information(self, "删除成功", "已删除选中的自定义脱敏词")
        except Exception as e:
            QMessageBox.critical(self, "删除错误", f"删除自定义脱敏词时出错: {str(e)}")
    
    def clear_custom_words(self):
        """清空所有自定义脱敏词"""
        try:
            # 清空混合策略中的自定义词汇
            for original in list(self.custom_words.keys()):
                self.hybrid_strategy.remove_custom_replacement(original)
            
            # 同时清空自定义词汇处理器
            self.custom_words_handler.clear_custom_words()
            
            # 更新UI显示
            self.custom_words = {}
            self.custom_table.setRowCount(0)
            
            QMessageBox.information(self, "清空成功", "已清空所有自定义脱敏词")
        except Exception as e:
            QMessageBox.critical(self, "清空错误", f"清空自定义脱敏词时出错: {str(e)}")
    
    def on_copy_clicked(self):
        """复制到剪贴板按钮点击事件"""
        # 获取当前文本内容
        content = self.content_text.toPlainText()
        
        if not content:
            QMessageBox.warning(self, "复制错误", "没有可复制的内容")
            return
        
        try:
            # 获取系统剪贴板
            clipboard = QApplication.clipboard()
            
            # 设置文本到剪贴板
            clipboard.setText(content)
            
            # 显示成功消息
            QMessageBox.information(self, "复制成功", "内容已成功复制到剪贴板")
        
        except Exception as e:
            QMessageBox.critical(self, "复制错误", f"复制到剪贴板时出错: {str(e)}")


    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 处理正在运行的处理线程
        if hasattr(self, 'processing_thread') and self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.wait()
        
        # 处理所有活动的模型下载线程
        if hasattr(self, 'model_manager') and self.model_manager:
            from Data_Masking.ui.model_manager import ModelManager
            for thread in ModelManager.active_download_threads[:]:  # 使用副本遍历
                if thread.isRunning():
                    thread.wait(1000)  # 等待最多1秒
            # 清空活动线程列表
            ModelManager.active_download_threads.clear()
        
        # 接受关闭事件
        event.accept()
    
    def __del__(self):
        """析构函数，确保临时文件被清理"""
        if hasattr(self, 'temp_file_handler'):
            self.temp_file_handler.cleanup()

# 主函数
if __name__ == "__main__":
    # 创建应用
    app = QApplication(sys.argv)
    
    # 设置应用样式
    set_macos_style(app)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())