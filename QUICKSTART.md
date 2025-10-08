# 快速开始指南

## 1. 安装依赖

```bash
# 克隆仓库
git clone https://github.com/NextDoorLaoHuang-HF/Local_Document_AI_Desensitization_Tool.git
cd Local_Document_AI_Desensitization_Tool

# 安装依赖
pip install -r requirements.txt
```

## 2. 配置远程模型

### 方式一：使用配置界面（推荐）

1. 启动应用：
   ```bash
   python Data_Masking/ui/gui_app.py
   ```

2. 点击菜单：`设置` -> `远程模型配置`

3. 填写配置信息并测试连接

### 方式二：手动编辑配置文件

1. 复制示例配置：
   ```bash
   cp config.example.json config.json
   ```

2. 编辑 `config.json`，修改以下字段：
   ```json
   {
     "model_config": {
       "api_base": "http://localhost:8000/v1",  // 你的API地址
       "api_key": "your-api-key-here",          // 你的API密钥
       "model_name": "qwen2.5-7b"                // 模型名称
     }
   }
   ```

## 3. 启动 vLLM（可选）

如果使用本地vLLM部署：

```bash
# 安装vLLM
pip install vllm

# 启动模型服务（以Qwen2.5-7B为例）
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --served-model-name qwen2.5-7b \
    --host 0.0.0.0 \
    --port 8000
```

其他推荐模型：
- `Qwen/Qwen2.5-14B-Instruct`
- `meta-llama/Llama-3.1-8B-Instruct`
- `google/gemma-2-9b-it`

## 4. 使用应用

1. 启动GUI：
   ```bash
   python Data_Masking/ui/gui_app.py
   ```

2. 上传文档或输入文本

3. 点击"开始脱敏"处理

4. 下载脱敏后的文档

## 5. PDF处理（可选）

首次处理PDF文档时：

1. 点击菜单：`帮助` -> `下载PDF处理模型`
2. 等待模型下载完成（约5GB）
3. 模型会自动配置

## 常见问题

### Q: 连接失败怎么办？
A:
1. 检查API地址是否正确
2. 确认vLLM服务已启动
3. 测试API连接：
   ```bash
   curl http://localhost:8000/v1/models
   ```

### Q: 识别效果不好？
A:
1. 调整提示词使其更明确
2. 尝试更大的模型
3. 修改Temperature参数（降低可提高确定性）

### Q: 如何使用OpenAI官方API？
A: 在配置中填写：
- API地址: `https://api.openai.com/v1`
- API密钥: 你的OpenAI API Key
- 模型名称: `gpt-3.5-turbo` 或 `gpt-4`

### Q: 需要处理大量文档怎么办？
A:
1. 启用并行处理
2. 增加工作线程数
3. 使用本地vLLM以降低API成本

## 更多帮助

- [远程模型配置详细说明](REMOTE_MODEL_CONFIG.md)
- [完整README](README.md)
- 技术支持：加微信群（见README）
