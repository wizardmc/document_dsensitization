# 部署说明

本文档详细介绍法律文档脱敏工具的部署和配置方法。

## 系统要求

### 硬件要求

- **CPU**：建议4核及以上
- **内存**：建议8GB及以上（NER模型加载需要较大内存）
- **存储**：至少1GB可用空间

### 软件要求

- **操作系统**：Windows、macOS或Linux
- **Python**：3.8及以上版本
- **依赖库**：详见requirements.txt

## 安装步骤

### 1. 克隆代码仓库

```bash
git clone <repository_url>
cd Data_Masking
```

### 2. 创建虚拟环境（可选但推荐）

```bash
# 使用venv创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 下载NER模型

系统首次运行时会自动下载ModelScope NLP RANER 中文命名实体识别模型，也可以通过以下命令手动下载：

```bash
python -m Data_Masking.download_models
```

## 配置说明

### 目录结构配置

系统默认使用以下目录结构：

- **uploads/**：上传文件存储目录
- **output/**：输出文件存储目录
- **maps/**：映射表存储目录

这些目录默认位于`Data_Masking/ui/`下，可以通过修改`app.py`中的以下配置进行自定义：

```python
# 配置上传文件夹
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
MAP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'maps')
```

### 脱敏策略配置

系统默认使用上下文感知策略（ContextAwareStrategy）作为默认脱敏策略，可以通过修改`app.py`中的以下配置进行自定义：

```python
# 设置默认策略
type_strategy = TypeBasedStrategy()  # 保留用于获取实体类型列表
context_strategy = ContextAwareStrategy(mapping_file=os.path.join(MAP_FOLDER, 'context_mapping.pkl'))
masker.set_default_strategy(context_strategy)
```

### Web服务配置

系统默认监听所有网络接口的8080端口，可以通过修改`app.py`末尾的以下配置进行自定义：

```python
if __name__ == '__main__':
    # 启动Flask应用
    app.run(host='0.0.0.0', port=8080, debug=True)
```

## 启动服务

### 开发环境启动

```bash
python -m Data_Masking.ui.app
```

### 生产环境部署

对于生产环境，建议使用Gunicorn或uWSGI等WSGI服务器部署Flask应用。

#### 使用Gunicorn部署（Linux/macOS）

1. 安装Gunicorn

```bash
pip install gunicorn
```

2. 启动服务

```bash
gunicorn -w 4 -b 0.0.0.0:8080 Data_Masking.ui.app:app
```

#### 使用uWSGI部署

1. 安装uWSGI

```bash
pip install uwsgi
```

2. 创建uwsgi.ini配置文件

```ini
[uwsgi]
module = Data_Masking.ui.app:app
master = true
processes = 4
socket = 0.0.0.0