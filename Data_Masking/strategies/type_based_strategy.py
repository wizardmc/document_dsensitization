# 基于类型的策略 - 根据实体类型使用不同的替换方式

from .base_strategy import MaskingStrategy

class TypeBasedStrategy(MaskingStrategy):
    """基于类型的策略 - 根据实体类型使用不同的替换方式"""
    def __init__(self):
        # 默认替换模板
        self.templates = {
            "PER": "某人",  # 人名
            "ORG": "某机构",  # 组织机构
            "LOC": "某地点",  # 地点
            "GPE": "某地区",  # 地缘政治实体
            "PHONE": "电话号码",  # 电话号码
            "ID": "身份证号",  # 身份证
            "BANK": "银行卡号",  # 银行卡
            "EMAIL": "电子邮箱",  # 邮箱
            "IP": "IP地址",  # IP地址
            "DATE": "某日期",  # 日期
            "TIME": "某时间",  # 时间
            "MONEY": "某金额",  # 金额
            "DEFAULT": "***"  # 默认替换文本
        }
    
    def set_template(self, entity_type: str, template: str):
        """设置特定类型的替换模板"""
        self.templates[entity_type] = template
    
    def mask(self, text: str, entity_type: str = "DEFAULT") -> str:
        return self.templates.get(entity_type, self.templates["DEFAULT"])