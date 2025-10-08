# 更新日志 / CHANGELOG

## v0.6.0 (2025-01-XX) - 远程模型支持

### 🎉 重大更新

- **移除本地NER模型依赖**：不再需要下载本地ModelScope NER模型
- **支持远程AI模型**：支持OpenAI API、vLLM等远程模型进行实体识别
- **灵活的模型选择**：可自由选择任意支持OpenAI兼容接口的模型

### ✨ 新功能

- 添加远程模型配置界面
  - 图形化配置API地址、密钥、模型参数
  - 支持自定义提示词模板
  - 内置连接测试功能
- 支持多种API类型
  - OpenAI官方API
  - vLLM本地部署
  - 其他自定义兼容接口
- 新增配置文件管理
  - `config.json`: 主配置文件
  - `config.example.json`: 配置示例文件

### 🔧 改进

- **降低系统要求**：使用远程模型仅需4GB内存
- **更快的启动速度**：无需加载本地NER模型
- **更灵活的部署**：可使用云端API或本地vLLM
- **提示词可定制**：用户可根据需求优化识别效果

### 📝 新增文档

- `REMOTE_MODEL_CONFIG.md`: 远程模型配置详细说明
- `QUICKSTART.md`: 快速开始指南
- `requirements.txt`: Python依赖清单

### 🔄 重构

- 重构 `Data_Masking/NER_model.py`
  - 移除ModelScope依赖
  - 使用远程API调用
- 新增 `Data_Masking/remote_ner_model.py`
  - 实现OpenAI兼容API调用
  - 保持原有接口兼容性
- 更新 `Data_Masking/ui/model_manager.py`
  - 移除本地NER模型配置
  - 仅保留PDF处理模型管理
- 新增 `Data_Masking/ui/remote_model_config_dialog.py`
  - 远程模型配置对话框
- 更新 `Data_Masking/ui/gui_app.py`
  - 添加菜单栏
  - 集成远程模型配置

### ⚠️ 破坏性变更

- **不再支持本地NER模型**：必须配置远程模型才能使用实体识别功能
- **配置文件格式变更**：需要创建新的`config.json`配置文件

### 📦 依赖变更

**新增依赖：**
- `openai>=1.0.0`: OpenAI API客户端

**可选依赖：**
- `modelscope`: 仅PDF处理需要

### 🚀 升级指南

1. **安装新依赖**：
   ```bash
   pip install -r requirements.txt
   ```

2. **配置远程模型**：
   - 启动应用，点击 `设置` -> `远程模型配置`
   - 或复制 `config.example.json` 为 `config.json` 并修改

3. **部署vLLM（可选）**：
   ```bash
   pip install vllm
   python -m vllm.entrypoints.openai.api_server \
       --model Qwen/Qwen2.5-7B-Instruct \
       --port 8000
   ```

4. **测试连接**：
   - 在配置界面点击"测试连接"
   - 确认模型响应正常

### 🐛 已知问题

- 首次使用需要配置远程模型，否则无法进行实体识别
- 某些提示词模板可能需要根据模型调整以获得最佳效果

---

## v0.5.0 及更早版本

详见之前的版本发布说明。
