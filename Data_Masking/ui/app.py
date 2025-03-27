import os
import json
import tempfile
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from typing import Dict, List, Any, Optional

# 导入脱敏相关功能
import sys
sys.path.append('/Users/huangweihao/all_in_one_lawchat')
from Data_Masking.masking import (
    MaskingStrategy, TypeBasedStrategy, ContextAwareStrategy, CustomReplacementStrategy,
    DataMasker, DocumentMasker
)
from Data_Masking.NER_model import NERModelLoader, batch_recognize_entities

# 创建Flask应用
app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用于flash消息

# 配置上传文件夹
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
MAP_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'maps')

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(MAP_FOLDER, exist_ok=True)

# 允许上传的文件类型
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'md'}

# 全局脱敏器实例
masker = DataMasker(mapping_file=os.path.join(MAP_FOLDER, 'masking_map.pkl'))
doc_masker = DocumentMasker(masker=masker, mapping_file=os.path.join(MAP_FOLDER, 'doc_masking_map.pkl'))

# 设置默认策略
type_strategy = TypeBasedStrategy()  # 保留用于获取实体类型列表
context_strategy = ContextAwareStrategy(mapping_file=os.path.join(MAP_FOLDER, 'context_mapping.pkl'))
masker.set_default_strategy(context_strategy)


def allowed_file(filename):
    """检查文件类型是否允许上传"""
    print(f"[DEBUG] 检查文件类型: {filename}")
    if '.' not in filename:
        print(f"[DEBUG] 文件名中没有扩展名: {filename}")
        return False
    
    # 处理特殊情况：文件名以点开头或只有扩展名没有文件名
    parts = filename.rsplit('.', 1)
    if len(parts) == 2:
        # 正常情况或文件名以点开头
        extension = parts[1].lower()
    else:
        # 异常情况，无法正确分割
        extension = ""
    
    print(f"[DEBUG] 提取的文件扩展名: '{extension}'")
    result = extension in ALLOWED_EXTENSIONS
    print(f"[DEBUG] 文件类型是否允许: {result}, 允许的类型: {ALLOWED_EXTENSIONS}")
    return result


@app.route('/')
def index():
    """首页 - 显示上传表单和配置选项"""
    # 获取可用的实体类型和脱敏策略
    entity_types = list(type_strategy.templates.keys())
    strategy_types = ['ContextAwareStrategy', 'CustomReplacementStrategy']
    
    return render_template(
        'index.html',
        entity_types=entity_types,
        strategy_types=strategy_types
    )


@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传和脱敏配置"""
    # 检查是否有文件上传
    if 'file' not in request.files:
        flash('没有选择文件')
        return redirect(request.url)
    
    file = request.files['file']
    print(f"[DEBUG] 接收到上传文件: {file.filename}")
    
    # 检查文件名是否为空
    if file.filename == '':
        flash('没有选择文件')
        return redirect(request.url)
    
    # 检查文件类型是否允许
    if not allowed_file(file.filename):
        print(f"[DEBUG] 文件类型不允许: {file.filename}")
        flash(f'不支持的文件类型，请上传 {", ".join(ALLOWED_EXTENSIONS)} 格式的文件')
        return redirect(request.url)
    
    # 保存上传的文件
    # 确保保留文件扩展名
    if '.' in file.filename:
        parts = file.filename.rsplit('.', 1)
        if len(parts) == 2:
            filename_base, extension = parts
            # 处理只有扩展名没有文件名的情况
            if filename_base == "":
                filename_base = "document"
            filename = secure_filename(filename_base) + '.' + extension.lower()
        else:
            # 异常情况，使用默认文件名
            filename = secure_filename("document")
    else:
        filename = secure_filename(file.filename)
    
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    print(f"[DEBUG] 文件已保存到: {file_path}")
    
    # 获取脱敏配置
    default_strategy_type = request.form.get('default_strategy', 'TypeBasedStrategy')
    print(f"[DEBUG] 使用脱敏策略: {default_strategy_type}")
    
    # 设置默认策略
    if default_strategy_type == 'CustomReplacementStrategy':
        # 创建自定义替换策略实例
        custom_strategy = CustomReplacementStrategy(mapping_file=os.path.join(MAP_FOLDER, 'custom_mapping.pkl'))
        masker.set_default_strategy(custom_strategy)
    else:  # ContextAwareStrategy
        # 创建上下文感知策略实例
        context_strategy = ContextAwareStrategy(mapping_file=os.path.join(MAP_FOLDER, 'context_mapping.pkl'))
        masker.set_default_strategy(context_strategy)
    
    # 处理文档
    try:
        print(f"[DEBUG] 开始处理文档: {file_path}")
        # 执行脱敏处理
        masked_md_content, masked_content_list_path = doc_masker.process_document_file(
            file_path=file_path,
            mask=True,
            output_dir=OUTPUT_FOLDER,
            save_mapping=True,
            enable_parallel=False
        )
        print(f"[DEBUG] 文档处理完成")
        
        # 获取输出文件路径
        original_name = os.path.splitext(os.path.basename(file_path))[0]
        masked_md_file_path = os.path.join(OUTPUT_FOLDER, f'{original_name}_masked.md')
        
        flash('文档脱敏成功')
        
        # 重定向到结果页面
        return redirect(url_for('result', filename=os.path.basename(masked_md_file_path)))
    
    except Exception as e:
        print(f"[DEBUG] 处理文档时出错: {str(e)}")
        flash(f'处理文档时出错: {str(e)}')
        return redirect(url_for('index'))


@app.route('/result/<filename>')
def result(filename):
    """显示脱敏结果"""
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    
    # 读取脱敏后的Markdown内容
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            masked_content = f.read()
        
        # 获取脱敏实体信息
        masked_entities = masker.get_masked_entities(masked_content)
        
        # 调试信息
        print(f"[DEBUG] 脱敏实体信息: {masked_entities}")
        print(f"[DEBUG] 脱敏内容长度: {len(masked_content)}")
        print(f"[DEBUG] 脱敏内容前100字符: {masked_content[:100]}")
        
        return render_template(
            'result.html',
            filename=filename,
            masked_content=masked_content,
            masked_entities=masked_entities
        )
    
    except Exception as e:
        flash(f'读取脱敏结果时出错: {str(e)}')
        return redirect(url_for('index'))


@app.route('/download/<filename>')
def download_file(filename):
    """下载脱敏后的文件"""
    return send_file(
        os.path.join(OUTPUT_FOLDER, filename),
        as_attachment=True,
        download_name=filename
    )


@app.route('/unmask/<filename>', methods=['POST'])
def unmask_file(filename):
    """恢复脱敏后的文件"""
    try:
        # 获取原始文件名（不含扩展名和_masked后缀）
        original_name = filename.replace('_masked.md', '')
        
        # 直接使用映射表恢复脱敏内容，不需要原始文件
        masked_file_path = os.path.join(OUTPUT_FOLDER, filename)
        
        if not os.path.exists(masked_file_path):
            raise FileNotFoundError(f"找不到脱敏文件: {filename}")
            
        # 读取脱敏后的内容
        with open(masked_file_path, 'r', encoding='utf-8') as f:
            masked_content = f.read()
            
        # 直接使用映射表恢复内容
        unmasked_content = masker.unmask_text(masked_content)
        
        # 获取恢复后的文件路径
        unmasked_md_file_path = os.path.join(OUTPUT_FOLDER, f'{original_name}_unmasked.md')
        
        # 保存恢复后的内容
        with open(unmasked_md_file_path, 'w', encoding='utf-8') as f:
            f.write(unmasked_content)
        
        flash('文档恢复成功')
        
        # 重定向到恢复结果页面
        return redirect(url_for('unmasked_result', filename=os.path.basename(unmasked_md_file_path)))
        
        # 查找原始文件
        original_file = None
        for ext in ALLOWED_EXTENSIONS:
            potential_file = os.path.join(UPLOAD_FOLDER, f'{original_name}.{ext}')
            if os.path.exists(potential_file):
                original_file = potential_file
                break
        
        if not original_file:
            return jsonify({'error': f'找不到原始文件: {original_name}.*'}), 404
        
        # 执行恢复处理
        unmasked_md_content, unmasked_content_list_path = doc_masker.process_document_file(
            file_path=original_file,
            mask=False,
            output_dir=OUTPUT_FOLDER,
            save_mapping=True,
            enable_parallel=False
        )
        
        # 获取恢复后的文件路径
        unmasked_md_file_path = os.path.join(OUTPUT_FOLDER, f'{original_name}_unmasked.md')
        
        flash('文档恢复成功')
        
        # 重定向到恢复结果页面
        return redirect(url_for('unmasked_result', filename=os.path.basename(unmasked_md_file_path)))
    
    except Exception as e:
        flash(f'恢复文档时出错: {str(e)}')
        return redirect(url_for('result', filename=filename))


@app.route('/unmasked_result/<filename>')
def unmasked_result(filename):
    """显示恢复结果"""
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    
    # 读取恢复后的Markdown内容
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            unmasked_content = f.read()
        
        return render_template(
            'unmasked_result.html',
            filename=filename,
            unmasked_content=unmasked_content
        )
    
    except Exception as e:
        flash(f'读取恢复结果时出错: {str(e)}')
        return redirect(url_for('index'))


@app.route('/api/mask_text', methods=['POST'])
def api_mask_text():
    """API接口 - 对文本进行脱敏处理"""
    data = request.json
    
    if not data or 'text' not in data:
        return jsonify({'error': '缺少必要的参数'}), 400
    
    text = data['text']
    
    try:
        # 执行脱敏处理
        masked_text = masker.mask_text(text)
        
        return jsonify({
            'masked_text': masked_text,
            'masked_entities': {
                k: {'original_text': v[0], 'entity_type': v[1]}
                for k, v in masker.get_masked_entities(masked_text).items()
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/unmask_text', methods=['POST'])
def api_unmask_text():
    """API接口 - 恢复脱敏后的文本"""
    data = request.json
    
    if not data or 'masked_text' not in data:
        return jsonify({'error': '缺少必要的参数'}), 400
    
    masked_text = data['masked_text']
    
    try:
        # 执行恢复处理
        unmasked_text = masker.unmask_text(masked_text)
        
        return jsonify({'unmasked_text': unmasked_text})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mask_document', methods=['POST'])
def api_mask_document():
    """API接口 - 对文档进行脱敏处理"""
    # 检查是否有文件上传
    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    file = request.files['file']
    
    # 检查文件名是否为空
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    # 检查文件类型是否允许
    if not allowed_file(file.filename):
        return jsonify({'error': f'不支持的文件类型，请上传 {", ".join(ALLOWED_EXTENSIONS)} 格式的文件'}), 400
    
    # 保存上传的文件
    # 确保保留文件扩展名
    if '.' in file.filename:
        parts = file.filename.rsplit('.', 1)
        if len(parts) == 2:
            filename_base, extension = parts
            # 处理只有扩展名没有文件名的情况
            if filename_base == "":
                filename_base = "document"
            filename = secure_filename(filename_base) + '.' + extension.lower()
        else:
            # 异常情况，使用默认文件名
            filename = secure_filename("document")
    else:
        filename = secure_filename(file.filename)
    
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    print(f"[DEBUG] 文件已保存到: {file_path}")
    print(f"[DEBUG] 文件已保存到: {file_path}")
    
    try:
        # 执行脱敏处理
        masked_md_content, masked_content_list_path = doc_masker.process_document_file(
            file_path=file_path,
            mask=True,
            output_dir=OUTPUT_FOLDER,
            save_mapping=True,
            enable_parallel=False
        )
        
        # 获取输出文件路径
        original_name = os.path.splitext(os.path.basename(file_path))[0]
        masked_md_file_path = os.path.join(OUTPUT_FOLDER, f'{original_name}_masked.md')
        
        return jsonify({
            'masked_md_file': os.path.basename(masked_md_file_path),
            'masked_content_list_file': os.path.basename(masked_content_list_path),
            'download_url': url_for('download_file', filename=os.path.basename(masked_md_file_path))
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/get_mapping', methods=['GET'])
def api_get_mapping():
    """API接口 - 获取脱敏映射表"""
    try:
        # 获取脱敏映射表
        mapping = {}
        for key, (original, entity_type) in masker.mapping.items():
            mapping[key] = {
                'original_text': original,
                'entity_type': entity_type
            }
        
        return jsonify({
            'mapping': mapping
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/unmask_document', methods=['POST'])
def api_unmask_document():
    """API接口 - 恢复脱敏后的文档"""
    data = request.json
    
    if not data or 'masked_file' not in data:
        return jsonify({'error': '缺少必要的参数'}), 400
    
    masked_file = data['masked_file']
    
    try:
        # 获取原始文件名（不含扩展名和_masked后缀）
        original_name = masked_file.replace('_masked.md', '')
        
        # 直接使用映射表恢复脱敏内容，不需要原始文件
        masked_file_path = os.path.join(OUTPUT_FOLDER, masked_file)
        
        if not os.path.exists(masked_file_path):
            raise FileNotFoundError(f"找不到脱敏文件: {masked_file}")
            
        # 读取脱敏后的内容
        with open(masked_file_path, 'r', encoding='utf-8') as f:
            masked_content = f.read()
            
        # 直接使用映射表恢复内容
        unmasked_content = masker.unmask_text(masked_content)
        for ext in ALLOWED_EXTENSIONS:
            potential_file = os.path.join(UPLOAD_FOLDER, f'{original_name}.{ext}')
            if os.path.exists(potential_file):
                original_file = potential_file
                break
        
        if not original_file:
            return jsonify({'error': f'找不到原始文件: {original_name}.*'}), 404
        
        # 执行恢复处理
        unmasked_md_content, unmasked_content_list_path = doc_masker.process_document_file(
            file_path=original_file,
            mask=False,
            output_dir=OUTPUT_FOLDER,
            save_mapping=True,
            enable_parallel=False
        )
        
        # 获取恢复后的文件路径
        unmasked_md_file_path = os.path.join(OUTPUT_FOLDER, f'{original_name}_unmasked.md')
        
        return jsonify({
            'unmasked_md_file': os.path.basename(unmasked_md_file_path),
            'unmasked_content_list_file': os.path.basename(unmasked_content_list_path),
            'download_url': url_for('download_file', filename=os.path.basename(unmasked_md_file_path))
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # 启动Flask应用
    app.run(host='0.0.0.0', port=8080, debug=True)