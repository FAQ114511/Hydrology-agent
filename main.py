import sys
from pathlib import Path

from dotenv import load_dotenv

# 显式加载本目录的 .env，避免依赖运行目录（IDE 直接运行 main.py 时，
# 工作目录可能是工作区根目录，而 find_dotenv(usecwd=True) 从 CWD 向上找会漏掉这里）。
load_dotenv(Path(__file__).resolve().parent / ".env")


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from tradingagents.default_config import build_hydrology_config
from tradingagents.graph.trading_graph import TradingAgentsGraph

# 同一套水文配置供 main.py 与 CLI 使用；环境变量覆盖已包含在返回值中。
config = build_hydrology_config()
config["max_tokens"] = 1500
config["max_debate_rounds"] = 1
config["max_risk_discuss_rounds"] = 1

# 初始化水文研判图
# ta = TradingAgentsGraph(debug=True, config=config)
ta=TradingAgentsGraph(
    debug=True,
    config=config,
    selected_analysts=("market", "social", "news", "fundamentals")
)

# 对湘江站执行 2024-05-10 防汛研判
_, decision = ta.propagate("XIANGJIANG", "2024-05-10", asset_type="flood")
print(decision)
