# API参考文档

本文档详细介绍法律文档脱敏工具提供的API接口及其使用方法。

## API概述

法律文档脱敏工具提供了一组RESTful API接口，便于与其他系统集成。所有API接口均返回JSON格式的响应。

## 接口列表

### 1. 文本脱敏

**接口**：`/api/mask_text`

**方法**：POST

**功能**：对文本进行脱敏处理

**请求参数**：

```json
{
  "text": "待脱敏的文本内容"
}
```

**响应**：

```json
{
  "masked_text": "脱敏后的文本内容",
  "masked_entities": {
    "__MASKED_per_12345678__": {
      "original_text": "张三",
      "entity_type": "PER"
    },
    "__MASKED_org_87654321__": {
      "original_text": "北京市海淀区人民法院",
      "entity_type": "ORG"
    }
  }
}
```

**示例**：

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

### 2. 文本恢复

**接口**：`/api/unmask_text`

**方法**：POST

**功能**：恢复脱敏后的文本

**请求参数**：

```json
{
  "masked_text": "脱敏后的文本内容"
}
```

**响应**：

```json
{
  "unmasked_text": "恢复后的原始文本内容"
}
```

**示例**：

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

### 3. 文档脱敏

**接口**：`/api/mask_document`

**方法**：POST

**功能**：对文档进行脱敏处理

**请求参数**：

使用`multipart/form-data`格式上传文件，参数名为`file`

**响应**：

```json
{
  "masked_md_file": "脱敏后的Markdown文件名",
  "masked_content_list_file": "脱敏后的内容列表文件名",
  "download_url": "下载脱敏后文件的URL"
}
```

**示例**：

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

### 4. 文档恢复

**接口**：`/api/unmask_document`

**方法**：POST

**功能**：恢复脱敏后的文档

**请求参数**：

```json
{
  "masked_file": "脱敏后的文件名"
}
```

**响应**：

```json
{
  "unmasked_md_file": "恢复后的Markdown文件名",
  "unmasked_content_list_file": "恢复后的内容列表文件名",
  "download_url": "下载恢复后文件的URL"
}
```

**示例**：

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

### 5. 获取脱敏映射表

**接口**：`/api/get_mapping`

**方法**：GET

**功能**：获取脱敏映射表

**请求参数**：无

**响应**：

```json
{
  "mapping": {
    "__MASKED_per_12345678__": {
      "original_text": "张三",
      "entity_type": "PER"
    },
    "__MASKED_org_87654321__": {
      "original_text": "北京市海淀区人民法院",
      "entity_type": "ORG"
    }
  }
}
```

**示例**：

```python
import requests
import json

url = "http://localhost:8080/api/get_mapping"

response = requests.get(url)
result = response.json()

print("脱敏映射表：", json.dumps(result["mapping"], ensure_ascii=False, indent=2))
```

## 错误处理

所有API接口在发生错误时，都会返回包含错误信息的JSON响应，HTTP状态码为4xx或5xx。

**错误响应格式**：

```json
{
  "error": "错误信息"
}
```

**常见错误码**：

- 400：请求参数错误
- 404：资源不存在
- 500：服务器内部错误

## 安全性考虑

1. API接口默认只监听本地地址，如需对外提供服务，请配置适当的身份验证和授权机制
2. 敏感数据只在本地处理，不会上传到云端
3. 映射表存储在本地文件系统，请确保文件系统的安全性