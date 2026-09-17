from enum import Enum


class AnalystType(str, Enum):
    # Wire values stay stable; the CLI labels them with hydrology roles.
    MARKET = "market"
    SOCIAL = "social"
    NEWS = "news"
    FUNDAMENTALS = "fundamentals"
