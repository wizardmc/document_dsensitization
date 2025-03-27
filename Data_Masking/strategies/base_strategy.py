# 脱敏策略基类

class MaskingStrategy:
    """脱敏策略基类"""
    def mask(self, text: str) -> str:
        """将文本进行脱敏处理"""
        raise NotImplementedError("子类必须实现此方法")
    
    def get_name(self) -> str:
        """获取策略名称"""
        return self.__class__.__name__
    
    def clear_mapping(self, remove_file: bool = False):
        """清除映射表，基类中为空实现，由需要的子类重写
        
        参数:
            remove_file (bool): 是否删除映射文件，默认为False
        """
        pass