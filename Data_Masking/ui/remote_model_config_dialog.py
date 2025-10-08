#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QGroupBox, QMessageBox, QSpinBox, QDoubleSpinBox,
    QTabWidget, QWidget, QTextEdit
)
from PyQt5.QtCore import Qt


class RemoteModelConfigDialog(QDialog):
    """远程模型配置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'config.json'
        )
        self.init_ui()
        self.load_config()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("远程模型配置")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()

        # 创建标签页
        tab_widget = QTabWidget()

        # 模型配置标签页
        model_tab = self.create_model_config_tab()
        tab_widget.addTab(model_tab, "模型配置")

        # NER配置标签页
        ner_tab = self.create_ner_config_tab()
        tab_widget.addTab(ner_tab, "NER配置")

        # Prompt配置标签页
        prompt_tab = self.create_prompt_config_tab()
        tab_widget.addTab(prompt_tab, "提示词配置")

        layout.addWidget(tab_widget)

        # 按钮组
        button_layout = QHBoxLayout()

        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(test_btn)

        button_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def create_model_config_tab(self):
        """创建模型配置标签页"""
        widget = QWidget()
        layout = QFormLayout()

        # API类型
        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["openai", "anthropic", "custom"])
        layout.addRow("API类型:", self.api_type_combo)

        # API地址
        self.api_base_input = QLineEdit()
        self.api_base_input.setPlaceholderText("http://localhost:8000/v1")
        layout.addRow("API地址:", self.api_base_input)

        # API密钥
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("your-api-key-here")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        layout.addRow("API密钥:", self.api_key_input)

        # 模型名称
        self.model_name_input = QLineEdit()
        self.model_name_input.setPlaceholderText("gpt-3.5-turbo")
        layout.addRow("模型名称:", self.model_name_input)

        # Temperature
        self.temperature_input = QDoubleSpinBox()
        self.temperature_input.setRange(0.0, 2.0)
        self.temperature_input.setSingleStep(0.1)
        self.temperature_input.setValue(0.1)
        layout.addRow("Temperature:", self.temperature_input)

        # Max Tokens
        self.max_tokens_input = QSpinBox()
        self.max_tokens_input.setRange(1, 128000)
        self.max_tokens_input.setValue(4096)
        layout.addRow("Max Tokens:", self.max_tokens_input)

        # Timeout
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(10, 600)
        self.timeout_input.setValue(60)
        layout.addRow("超时时间(秒):", self.timeout_input)

        widget.setLayout(layout)
        return widget

    def create_ner_config_tab(self):
        """创建NER配置标签页"""
        widget = QWidget()
        layout = QFormLayout()

        # 并行处理
        self.enable_parallel_combo = QComboBox()
        self.enable_parallel_combo.addItems(["否", "是"])
        layout.addRow("启用并行处理:", self.enable_parallel_combo)

        # 工作线程数
        self.num_workers_input = QSpinBox()
        self.num_workers_input.setRange(1, 16)
        self.num_workers_input.setValue(4)
        layout.addRow("工作线程数:", self.num_workers_input)

        # 最大分块大小
        self.max_chunk_size_input = QSpinBox()
        self.max_chunk_size_input.setRange(100, 2000)
        self.max_chunk_size_input.setValue(450)
        layout.addRow("最大分块大小:", self.max_chunk_size_input)

        # 支持的实体类型
        self.entity_types_input = QTextEdit()
        self.entity_types_input.setPlaceholderText("每行一个实体类型，例如：\n人名\n地名\n机构名")
        self.entity_types_input.setMaximumHeight(150)
        layout.addRow("支持的实体类型:", self.entity_types_input)

        widget.setLayout(layout)
        return widget

    def create_prompt_config_tab(self):
        """创建提示词配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()

        # System Prompt
        system_group = QGroupBox("系统提示词")
        system_layout = QVBoxLayout()
        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setPlaceholderText("输入系统提示词...")
        system_layout.addWidget(self.system_prompt_input)
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)

        # User Prompt
        user_group = QGroupBox("用户提示词模板")
        user_layout = QVBoxLayout()

        # 提示信息
        info_label = QLabel("使用 {text} 作为占位符，将被实际文本替换")
        info_label.setStyleSheet("color: #666;")
        user_layout.addWidget(info_label)

        self.user_prompt_input = QTextEdit()
        self.user_prompt_input.setPlaceholderText("输入用户提示词模板，使用{text}作为占位符...")
        user_layout.addWidget(self.user_prompt_input)
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)

        widget.setLayout(layout)
        return widget

    def load_config(self):
        """加载配置"""
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 加载模型配置
            model_config = config.get('model_config', {})
            self.api_type_combo.setCurrentText(model_config.get('api_type', 'openai'))
            self.api_base_input.setText(model_config.get('api_base', ''))
            self.api_key_input.setText(model_config.get('api_key', ''))
            self.model_name_input.setText(model_config.get('model_name', ''))
            self.temperature_input.setValue(model_config.get('temperature', 0.1))
            self.max_tokens_input.setValue(model_config.get('max_tokens', 4096))
            self.timeout_input.setValue(model_config.get('timeout', 60))

            # 加载NER配置
            ner_config = config.get('ner_config', {})
            self.enable_parallel_combo.setCurrentText("是" if ner_config.get('enable_parallel', False) else "否")
            self.num_workers_input.setValue(ner_config.get('num_workers', 4))
            self.max_chunk_size_input.setValue(ner_config.get('max_chunk_size', 450))

            entity_types = ner_config.get('supported_entity_types', [])
            self.entity_types_input.setText('\n'.join(entity_types))

            # 加载提示词配置
            prompt_template = config.get('prompt_template', {})
            self.system_prompt_input.setText(prompt_template.get('system_prompt', ''))
            self.user_prompt_input.setText(prompt_template.get('user_prompt', ''))

        except Exception as e:
            QMessageBox.warning(self, "加载配置失败", f"无法加载配置: {str(e)}")

    def save_config(self):
        """保存配置"""
        config = {
            "model_config": {
                "model_type": "remote",
                "api_type": self.api_type_combo.currentText(),
                "api_base": self.api_base_input.text(),
                "api_key": self.api_key_input.text(),
                "model_name": self.model_name_input.text(),
                "temperature": self.temperature_input.value(),
                "max_tokens": self.max_tokens_input.value(),
                "timeout": self.timeout_input.value()
            },
            "ner_config": {
                "enable_parallel": self.enable_parallel_combo.currentText() == "是",
                "num_workers": self.num_workers_input.value(),
                "max_chunk_size": self.max_chunk_size_input.value(),
                "supported_entity_types": [
                    line.strip() for line in self.entity_types_input.toPlainText().split('\n')
                    if line.strip()
                ]
            },
            "prompt_template": {
                "system_prompt": self.system_prompt_input.toPlainText(),
                "user_prompt": self.user_prompt_input.toPlainText()
            }
        }

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "保存成功", "配置已成功保存")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"无法保存配置: {str(e)}")

    def test_connection(self):
        """测试连接"""
        try:
            from openai import OpenAI

            api_base = self.api_base_input.text()
            api_key = self.api_key_input.text()
            model_name = self.model_name_input.text()

            if not api_base or not model_name:
                QMessageBox.warning(self, "参数错误", "请填写API地址和模型名称")
                return

            # 创建客户端
            client = OpenAI(
                base_url=api_base,
                api_key=api_key or "dummy-key",
                timeout=10
            )

            # 测试简单请求
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "你是一个测试助手"},
                    {"role": "user", "content": "请回复'连接成功'"}
                ],
                max_tokens=50
            )

            result = response.choices[0].message.content
            QMessageBox.information(self, "连接成功", f"远程模型响应:\n{result}")

        except Exception as e:
            QMessageBox.critical(self, "连接失败", f"无法连接到远程模型:\n{str(e)}")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    dialog = RemoteModelConfigDialog()
    dialog.show()
    sys.exit(app.exec_())
