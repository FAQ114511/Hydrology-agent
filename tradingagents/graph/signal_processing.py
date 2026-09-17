"""从预警决策员的输出中确定性提取红、橙、黄、蓝预警等级。"""

from __future__ import annotations

from typing import Any

from tradingagents.alert_levels import parse_alert_level

ALERT_REVIEW = "REVIEW"


class SignalProcessor:
    """从预警决策文本读取四级预警。"""

    def __init__(self, quick_thinking_llm: Any = None):
        pass

    def process_signal(self, full_signal: str) -> str:
        """返回红色/橙色/黄色/蓝色预警，无法识别时返回 REVIEW。"""
        result = parse_alert_level(full_signal, default="")
        return result or ALERT_REVIEW
