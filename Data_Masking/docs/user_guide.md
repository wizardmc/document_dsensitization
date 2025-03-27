# 使用指南

本文档详细介绍法律文档脱敏工具的使用方法和最佳实践。

## 系统概述

法律文档脱敏工具提供了Web界面和API接口两种使用方式，用户可以根据需求选择合适的方式。

## Web界面使用

### 访问Web界面

启动系统后，通过浏览器访问以下地址：

```
http://localhost:8080
```

### 文档脱敏

1. 在首页点击"选择文档文件"按钮，选择需要脱敏的文档文件（支持PDF、DOC、DOCX、TXT、MD等格式）
2. 配置脱敏策略：
   - 选择默认脱敏策略（上下文感知策略或自定义替换策略）
   - 根据需要配置实体类型替换模板
3. 点击"上传并脱敏"按钮，系统将对文档进行脱敏处理
4. 处理完成后，系统会自动跳转到结果页面，显示脱敏后的文档内容和脱敏实体信息
5. 在结果页面，可以：
   - 查看脱敏后的文档内容
   - 下载脱敏后的文档
   - 恢复原始文档

### 脱敏策略配置

#### 上下文感知策略（ContextAwareStrategy）

上下文感知策略是最智能的脱敏策略，它会根据实体类型和上下文选择合适的替换方式，并确保同一实体在整个文档中使用相同的替换文本。

配置方法：
1. 在默认脱敏策略下拉框中选择"ContextAwareStrategy"
2. 根据需要配置各实体类型的替换模板

#### 自定义替换策略（CustomReplacementStrategy）

自定义替换策略允许用户为每个词自定义唯一替换词，提供最大的灵活性。

配置方法：
1. 在默认脱敏策略下拉框中选择"CustomReplacementStrategy"
2. 在自定义替换规则部分，添加需要替换的原始文本和替换文本

### 文档恢复

1. 在脱敏结果页面，点击"恢复原始文档"按钮
2. 系统将根据保存的映射关系，恢复脱敏后的文档
3. 恢复完成后，系统会自动跳转到恢复结果页面，显示恢复后的文档内容
4. 在恢复结果页面，可以：
   - 查看恢复后的文档内容
   - 下载恢复后的文档
   - 返回脱敏结果页面

## API接口使用

### 文本脱敏

使用`/api/mask_text`接口对文本进行脱敏处理：

```python
import requests
import json

url = "http://localhost:8080/api/mask_text"
data = {
  "text": "张三是北京市海淀区人民法院的法官，电话是13800138000。"
}

response = requests.post(url, json=data)
result = response.json()

print("脱敏后的文本：", result["masked_text"])
print("脱敏实体信息：", json.dumps(result["masked_entities"], ensure_ascii=False, indent=2))
```

### 文本恢复

使用`/api/unmask_text`接口恢复脱敏后的文本：

```python
import requests

url = "http://localhost:8080/api/unmask_text"
data = {
  "masked_text": "__MASKED_per_12345678__是__MASKED_org_87654321__的法官，电话是__MASKED_phone_abcdef12__。"
}

response = requests.post(url, json=data)
result = response.json()

print("恢复后的文本：", result["unmasked_text"])
```

### 文档脱敏

使用`/api/mask_document`接口对文档进行脱敏处理：

```python
import requests

url = "http://localhost:8080/api/mask_document"
files = {
  "file": open("example.pdf", "rb")
}

response = requests.post(url, files=files)
result = response.json()

print("脱敏后的文件：", result["masked_md_file"])
print("下载URL：", result["download_url"])
```

### 文档恢复

使用`/api/unmask_document`接口恢复脱敏后的文档：

```python
import requests

url = "http://localhost:8080/api/unmask_document"
data = {
  "masked_file": "example_masked.md"
}

response = requests.post(url, json=data)
result = response.json()

print("恢复后的文件：", result["unmasked_md_file"])
print("下载URL：", result["download_url"])
```

## 最佳实践

### 选择合适的脱敏策略

- 对于需要保持文档可读性的场景，推荐使用上下文感知策略（ContextAwareStrategy）
- 对于需要最高安全性的场景，推荐使用哈希策略（HashStrategy）
- 对于需要自定义替换规则的场景，推荐使用自定义替换策略（CustomReplacementStrategy）

### 批量处理文档

对于需要批量处理大量文档的场景，推荐使用API接口结合脚本进行处理：

```python
import os
import requests
import glob

url = "http://localhost:8080/api/mask_document"
doc_dir = "./documents/"
output_dir = "./masked_documents/"

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

# 获取所有文档文件
doc_files = glob.glob(os.path.join(doc_dir, "*.pdf")) + \
           glob.glob(os.path.join(doc_dir, "*.docx")) + \
           glob.glob(os.path.join(doc_dir, "*.txt"))

# 批量处理文档
for doc_file in doc_files:
    print(f"处理文件：{doc_file}")
    with open(doc_file, "rb") as f:
        files = {"file": f}
        response = requests.post(url, files=files)
        if response.status_code == 200:
            result = response.json()
            print(f"脱敏成功：{result['masked_md_file']}")
        else:
            print(f"脱敏失败：{response.text}")
```

### 安全性建议

1. 定期清理映射表，避免敏感信息长期存储
2. 对于高度敏感的文档，建议在离线环境中使用本工具
3. 使用API接口时，建议配置适当的身份验证和授权机制
4. 定期更新系统，确保获取最新的安全补丁