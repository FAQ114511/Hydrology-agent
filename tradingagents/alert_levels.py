"""水文预警等级的确定性解析。"""

ALERT_LEVELS = ("红色预警", "橙色预警", "黄色预警", "蓝色预警")


def parse_alert_level(text: str, default: str = "蓝色预警") -> str:
    """从预警决策文本中提取四级预警；无法识别时返回 ``default``。"""
    for level in ALERT_LEVELS:
        if level in (text or ""):
            return level
    return default
