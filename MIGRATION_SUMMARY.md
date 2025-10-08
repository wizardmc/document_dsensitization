# 远程模型改造总结

## 改造目标

将本地NER模型调用改为远程模型（OpenAI API / vLLM），降低系统资源要求，提高部署灵活性。

## 核心改动

### 1. 新增文件

| 文件路径 | 说明 |
|---------|------|
| `config.json` | 远程模型主配置文件（需用户创建） |
| `config.example.json` | 配置示例文件 |
| `Data_Masking/remote_ner_model.py` | 远程NER模型调用实现 |
| `Data_Masking/ui/remote_model_config_dialog.py` | 远程模型配置UI对话框 |
| `requirements.txt` | Python依赖清单 |
| `REMOTE_MODEL_CONFIG.md` | 远程模型配置详细文档 |
| `QUICKSTART.md` | 快速开始指南 |
| `CHANGELOG.md` | 版本更新日志 |

### 2. 修改文件

| 文件路径 | 主要改动 |
|---------|---------|
| `Data_Masking/NER_model.py` | 移除ModelScope依赖，改为调用远程模型 |
| `Data_Masking/ui/model_manager.py` | 移除本地NER模型配置项 |
| `Data_Masking/ui/gui_app.py` | 添加菜单栏和远程模型配置入口 |
| `README.md` | 更新安装说明和功能介绍 |
| `.gitignore` | 添加config.json到忽略列表 |

## 技术实现

### 1. 远程模型调用架构

```
用户输入文本
    ↓
NERModelLoader (单例)
    ↓
RemoteNERModel (远程模型封装)
    ↓
OpenAI Client (使用openai库)
    ↓
远程API (vLLM/OpenAI/自定义)
    ↓
返回实体识别结果
```

### 2. 配置文件结构

```json
{
  "model_config": {
    "api_type": "openai",
    "api_base": "http://localhost:8000/v1",
    "api_key": "your-key",
    "model_name": "qwen2.5-7b",
    "temperature": 0.1,
    "max_tokens": 4096,
    "timeout": 60
  },
  "ner_config": {
    "enable_parallel": false,
    "num_workers": 4,
    "max_chunk_size": 450,
    "supported_entity_types": [...]
  },
  "prompt_template": {
    "system_prompt": "...",
    "user_prompt": "..."
  }
}
```

### 3. 提示词工程

系统提示词定义AI助手角色：
```
你是一个专业的命名实体识别助手。请识别文本中的敏感信息...
```

用户提示词模板（使用{text}占位符）：
```
请识别以下文本中的实体信息，返回JSON格式...
文本：{text}
```

## 功能特性

### ✅ 保留的功能
- 文本分块处理
- 并行/串行处理选择
- 实体去重
- 位置偏移计算
- 批量处理支持
- 与原有接口完全兼容

### ✨ 新增功能
- 远程模型配置界面
- 多种API类型支持
- 自定义提示词
- 连接测试
- 配置持久化

### 🗑️ 移除的功能
- 本地ModelScope NER模型
- 本地模型下载管理

## 优势

1. **降低资源需求**：无需本地NER模型，内存需求从8GB降至4GB
2. **灵活部署**：可使用云端API或本地vLLM
3. **模型可选**：支持任意OpenAI兼容模型
4. **提示词优化**：用户可根据需求调整识别策略
5. **成本控制**：本地vLLM部署免费使用
6. **快速启动**：无需加载大型本地模型

## 使用流程

### 首次配置
1. 安装依赖：`pip install -r requirements.txt`
2. 启动应用：`python Data_Masking/ui/gui_app.py`
3. 配置远程模型：`设置` -> `远程模型配置`
4. 测试连接并保存

### vLLM部署（推荐）
```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --served-model-name qwen2.5-7b \
    --port 8000
```

### 使用OpenAI API
在配置界面填写：
- API地址: `https://api.openai.com/v1`
- API密钥: 你的OpenAI Key
- 模型: `gpt-3.5-turbo` 或 `gpt-4`

## 兼容性

- ✅ 完全向后兼容原有脱敏功能
- ✅ 保持相同的API接口
- ✅ 支持所有原有的文档格式
- ⚠️ 需要配置远程模型才能使用

## 注意事项

1. **配置文件安全**：`config.json`包含API密钥，已加入`.gitignore`
2. **网络要求**：使用云端API需稳定网络连接
3. **提示词调优**：不同模型可能需要调整提示词
4. **成本考虑**：使用付费API注意token消耗

## 测试建议

1. **功能测试**：
   - 测试文本脱敏
   - 测试PDF处理
   - 测试批量处理

2. **配置测试**：
   - 测试OpenAI API
   - 测试本地vLLM
   - 测试自定义API

3. **性能测试**：
   - 并行处理效果
   - 大文档处理
   - 响应时间

## 后续优化方向

1. 支持更多模型类型（Claude、Gemini等）
2. 批量API调用优化
3. 缓存机制减少重复调用
4. 离线模式支持
5. 更智能的提示词自动优化

## 文档资源

- [远程模型配置说明](REMOTE_MODEL_CONFIG.md)
- [快速开始指南](QUICKSTART.md)
- [更新日志](CHANGELOG.md)
- [主README](README.md)
