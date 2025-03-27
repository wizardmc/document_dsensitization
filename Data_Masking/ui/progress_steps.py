#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class ProgressSteps:
    """进度步骤管理类"""
    
    @staticmethod
    def get_steps(is_mask=True):
        """获取处理步骤列表
        
        参数:
            is_mask (bool): 是否为脱敏处理(True)或解敏处理(False)
            
        返回:
            list: 包含(进度百分比, 步骤描述)的列表
        """
        if is_mask:
            return [
                (10, "准备处理文件..."),
                (20, "加载脱敏策略..."),
                (30, "转换文档格式..."),
                (50, "提取敏感实体..."), 
                (70, "执行脱敏替换..."),
                (90, "保存处理结果..."),
                (100, "处理完成")
            ]
        else:
            return [
                (10, "准备处理文件..."),
                (30, "加载解敏策略..."),
                (50, "解析脱敏内容..."),
                (70, "执行解敏替换..."),
                (90, "保存处理结果..."),
                (100, "处理完成")
            ]

    @staticmethod
    def get_step_description(progress):
        """根据进度百分比获取步骤描述
        
        参数:
            progress (int): 当前进度百分比
            
        返回:
            str: 步骤描述文本
        """
        steps = ProgressSteps.get_steps()
        for step in steps:
            if progress <= step[0]:
                return step[1]
        return "处理中..."