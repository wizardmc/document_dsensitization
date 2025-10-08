#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import threading
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Callable

from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QApplication
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# 确保项目根目录在Python路径中
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入模型相关模块
from tqdm import tqdm
from modelscope import snapshot_download


class CustomTqdm(tqdm):
    """自定义tqdm类，用于捕获下载进度"""
    def __init__(self, *args, progress_callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_callback = progress_callback
        self.total_size = kwargs.get('total', 100)
        
    def update(self, n=1):
        # 调用原始的update方法
        super().update(n)
        # 如果有回调函数，则调用它
        if self.progress_callback:
            # 计算百分比进度（10-90之间）
            progress = 10 + int(80 * self.n / self.total_size) if self.total_size else 10
            # 确保进度不超过90（因为90-100是留给配置阶段的）
            progress = min(progress, 89)
            self.progress_callback(progress, f"正在下载{self.desc}... {progress}%")


class ModelDownloadThread(QThread):
    """模型下载线程，避免阻塞GUI主线程"""
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, model_id: str, model_type: str, allow_patterns: List[str] = None):
        super().__init__()
        self.model_id = model_id
        self.model_type = model_type
        self.allow_patterns = allow_patterns
    
    def run(self):
        try:
            self.progress_signal.emit(10, f"开始下载{self.model_type}模型...")
            
            # 导入必要的模块
            import builtins
            from tqdm.auto import tqdm as original_tqdm
            
            # 保存原始的tqdm
            original_tqdm_func = builtins.tqdm if hasattr(builtins, 'tqdm') else original_tqdm
            
            # 替换全局tqdm为我们的自定义版本
            def custom_tqdm(*args, **kwargs):
                return CustomTqdm(*args, progress_callback=self.progress_callback, **kwargs)
            
            # 替换tqdm
            builtins.tqdm = custom_tqdm
            
            try:
                # 下载模型
                if self.allow_patterns:
                    model_dir = snapshot_download(self.model_id, allow_patterns=self.allow_patterns)
                else:
                    model_dir = snapshot_download(self.model_id)
            finally:
                # 恢复原始tqdm
                builtins.tqdm = original_tqdm_func
            
            self.progress_signal.emit(90, f"模型下载完成，正在完成配置...")
            
            # 如果是PDF处理模型，需要额外配置
            if self.model_type == "pdf_extract":
                self._configure_pdf_extract(model_dir)
            
            self.progress_signal.emit(100, f"模型下载和配置完成")
            self.finished_signal.emit(True, model_dir)
            
        except Exception as e:
            self.finished_signal.emit(False, str(e))
    
    def progress_callback(self, value, text):
        """进度回调函数，用于更新进度条"""
        self.progress_signal.emit(value, text)
    
    def _configure_pdf_extract(self, model_dir: str):
        """配置PDF提取模型"""
        try:
            # 从项目根目录导入下载模型脚本中的函数
            sys.path.append(project_root)
            from download_models import download_and_modify_json
            
            # 配置JSON文件
            json_url = 'https://gcore.jsdelivr.net/gh/opendatalab/MinerU@master/magic-pdf.template.json'
            config_file_name = 'magic-pdf.json'
            home_dir = os.path.expanduser('~')
            config_file = os.path.join(home_dir, config_file_name)
            
            # 获取layoutreader模型目录
            layoutreader_model_dir = snapshot_download('ppaanngggg/layoutreader')
            
            # 修改配置
            json_mods = {
                'models-dir': model_dir + '/models',
                'layoutreader-model-dir': layoutreader_model_dir,
            }
            
            # 下载并修改JSON
            download_and_modify_json(json_url, config_file, json_mods)
            
        except Exception as e:
            raise Exception(f"配置PDF提取模型时出错: {str(e)}")


class ModelManager:
    """模型管理器，负责检查模型是否存在并提供下载功能"""

    # 模型信息配置（移除了本地NER模型）
    MODEL_CONFIGS = {
        "pdf_extract": {
            "model_id": "opendatalab/PDF-Extract-Kit-1.0",
            "model_type": "pdf_extract",
            "description": "PDF文档处理模型",
            "allow_patterns": [
                "models/Layout/LayoutLMv3/*",
                "models/Layout/YOLO/*",
                "models/MFD/YOLO/*",
                "models/MFR/unimernet_small_2501/*",
                "models/TabRec/TableMaster/*",
                "models/TabRec/StructEqTable/*",
            ]
        },
        "layoutreader": {
            "model_id": "ppaanngggg/layoutreader",
            "model_type": "layoutreader",
            "description": "布局阅读器模型（PDF处理依赖）",
            "allow_patterns": None
        }
    }
    
    def __init__(self):
        # 获取modelscope的缓存目录
        from modelscope.hub.api import HubApi
        self.hub_api = HubApi()
        # 不需要获取缓存目录，直接使用hub_api对象
    
    def check_model_exists(self, model_type: str) -> Tuple[bool, str]:
        """检查指定类型的模型是否存在
        
        Args:
            model_type: 模型类型，如'ner'或'pdf_extract'
            
        Returns:
            Tuple[bool, str]: (是否存在, 模型路径或错误信息)
        """
        if model_type not in self.MODEL_CONFIGS:
            return False, f"未知的模型类型: {model_type}"
        
        model_config = self.MODEL_CONFIGS[model_type]
        model_id = model_config["model_id"]
        
        try:
            # 检查模型是否已下载
            from modelscope.utils.file_utils import get_model_cache_dir
            model_path = get_model_cache_dir(model_id)
            if os.path.exists(model_path) and os.listdir(model_path):
                return True, model_path
            return False, f"模型未下载: {model_id}"
        except Exception as e:
            return False, str(e)
    
    # 保存所有活动的下载线程
    active_download_threads = []
    
    def download_model(self, model_type: str, parent=None) -> bool:
        """下载指定类型的模型
        
        Args:
            model_type: 模型类型，如'ner'或'pdf_extract'
            parent: 父窗口，用于显示进度对话框
            
        Returns:
            bool: 下载是否成功
        """
        if model_type not in self.MODEL_CONFIGS:
            QMessageBox.critical(parent, "错误", f"未知的模型类型: {model_type}")
            return False
        
        model_config = self.MODEL_CONFIGS[model_type]
        model_id = model_config["model_id"]
        description = model_config["description"]
        allow_patterns = model_config["allow_patterns"]
        
        # 创建进度对话框
        progress_dialog = QProgressDialog(f"正在下载{description}...", "取消", 0, 100, parent)
        progress_dialog.setWindowTitle(f"下载{description}")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setAutoClose(True)
        progress_dialog.setAutoReset(True)
        progress_dialog.setValue(0)
        progress_dialog.show()
        
        # 创建下载线程
        download_thread = ModelDownloadThread(model_id, model_type, allow_patterns)
        
        # 保存线程引用
        ModelManager.active_download_threads.append(download_thread)
        
        # 连接信号
        download_thread.progress_signal.connect(
            lambda value, text: self._update_progress(progress_dialog, value, text)
        )
        download_thread.finished_signal.connect(
            lambda success, msg: self._download_finished(progress_dialog, success, msg, parent, download_thread)
        )
        
        # 启动线程
        download_thread.start()
        
        # 返回True表示下载已启动，实际结果将通过信号通知
        return True
    
    def _update_progress(self, dialog, value, text):
        """更新进度对话框"""
        dialog.setValue(value)
        dialog.setLabelText(text)
        QApplication.processEvents()
    
    def _download_finished(self, dialog, success, message, parent, download_thread=None):
        """下载完成处理"""
        dialog.setValue(100)
        
        if success:
            QMessageBox.information(parent, "下载成功", f"模型下载成功: {message}")
        else:
            QMessageBox.critical(parent, "下载失败", f"模型下载失败: {message}")
            
        # 从活动线程列表中移除已完成的线程
        if download_thread and download_thread in ModelManager.active_download_threads:
            ModelManager.active_download_threads.remove(download_thread)
    
    def check_and_download_models(self, parent=None, auto_check=False, silent=False) -> bool:
        """检查所有必需的模型，如果缺少则提示下载
        
        Args:
            parent: 父窗口，用于显示对话框
            auto_check: 是否为自动检查模式，自动检查模式下只在缺少模型时才弹出对话框
            silent: 是否为静默模式，静默模式下不会弹出任何提示框，只在缺少模型时返回False
            
        Returns:
            bool: 所有模型是否可用
        """
        missing_models = []
        
        # 检查所有模型
        for model_type, config in self.MODEL_CONFIGS.items():
            exists, _ = self.check_model_exists(model_type)
            if not exists:
                missing_models.append((model_type, config["description"]))
        
        # 如果有缺失的模型，提示下载
        if missing_models:
            # 静默模式下直接返回False
            if silent:
                return False
                
            missing_desc = "\n".join([f"- {desc}" for _, desc in missing_models])
            message = f"以下模型未找到，需要下载才能正常使用所有功能：\n{missing_desc}\n\n是否现在下载？"
            
            reply = QMessageBox.question(
                parent, "模型下载", message, 
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # 逐个下载缺失的模型
                for model_type, _ in missing_models:
                    self.download_model(model_type, parent)
                return False  # 返回False表示需要等待下载完成
            else:
                # 用户选择不下载
                warning_msg = """部分功能可能无法正常使用，您可以稍后通过"帮助"菜单下载模型。"""
                QMessageBox.warning(parent, "警告", warning_msg)
                return False
        elif not auto_check and not silent:
            # 非自动检查模式且非静默模式下，如果所有模型都已存在，显示提示信息
            QMessageBox.information(parent, "模型检查", "所有必需的模型已安装完成。")
        
        return True  # 所有模型都可用


# 单例模式实现
_instance = None
_lock = threading.Lock()

def get_model_manager() -> ModelManager:
    """获取ModelManager单例"""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = ModelManager()
    return _instance


# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("模型管理器测试")
    window.setGeometry(100, 100, 400, 200)
    
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    layout = QVBoxLayout(central_widget)
    
    manager = get_model_manager()
    
    # 检查NER模型
    check_ner_btn = QPushButton("检查NER模型")
    check_ner_btn.clicked.connect(lambda: print(manager.check_model_exists("ner")))
    layout.addWidget(check_ner_btn)
    
    # 下载NER模型
    download_ner_btn = QPushButton("下载NER模型")
    download_ner_btn.clicked.connect(lambda: manager.download_model("ner", window))
    layout.addWidget(download_ner_btn)
    
    # 检查PDF模型
    check_pdf_btn = QPushButton("检查PDF模型")
    check_pdf_btn.clicked.connect(lambda: print(manager.check_model_exists("pdf_extract")))
    layout.addWidget(check_pdf_btn)
    
    # 下载PDF模型
    download_pdf_btn = QPushButton("下载PDF模型")
    download_pdf_btn.clicked.connect(lambda: manager.download_model("pdf_extract", window))
    layout.addWidget(download_pdf_btn)
    
    # 检查并下载所有模型
    check_all_btn = QPushButton("检查并下载所有模型")
    check_all_btn.clicked.connect(lambda: manager.check_and_download_models(window))
    layout.addWidget(check_all_btn)
    
    window.show()
    sys.exit(app.exec_())