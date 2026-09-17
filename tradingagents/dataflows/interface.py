import logging

from .config import get_config
from .errors import (
    NoMarketDataError,
    VendorNotConfiguredError,
    VendorRateLimitError,
)
from .local_csv import (
    get_environment_risk as get_local_environment_risk,
    get_forward_forecast as get_local_forward_forecast,
    get_hydrology_indicators as get_local_hydrology_indicators,
    get_observations as get_local_observations,
    get_rainfall_forecast as get_local_rainfall_forecast,
    get_regional_indicators as get_local_regional_indicators,
    get_river_flow as get_local_river_flow,
    get_social_impact as get_local_social_impact,
    get_soil_moisture as get_local_soil_moisture,
    get_water_storage as get_local_water_storage,
)
from .weather_api import get_online_rainfall_forecast, get_online_realtime_weather

logger = logging.getLogger(__name__)

# 工具按类别组织
TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "水文站点观测数据（水位/流量/雨量）",
        "tools": [
            "get_observations"
        ]
    },
    "technical_indicators": {
        "description": "水文趋势指标",
        "tools": [
            "get_hydrology_indicators"
        ]
    },
    "fundamental_data": {
        "description": "环境风险与蓄水/河道/墒情",
        "tools": [
            "get_environment_risk",
            "get_water_storage",
            "get_river_flow",
            "get_soil_moisture"
        ]
    },
    "news_data": {
        "description": "降雨预报、实时气象与社会影响",
        "tools": [
            "get_rainfall_forecast",
            "get_realtime_weather",
            "get_social_impact",
        ]
    },
    "macro_data": {
        "description": "区域环境指标",
        "tools": [
            "get_regional_indicators",
        ]
    },
    "prediction_markets": {
        "description": "前瞻性事件的预报信息",
        "tools": [
            "get_forward_forecast",
        ]
    }
}

VENDOR_LIST = [
    "online_api",
    "local_csv",
]

# Optional enrichment categories. These add macro/event context to the news
# analyst but are not core to a decision, so a vendor failure here degrades to a
# sentinel instead of aborting the run (a bad LLM-supplied indicator, a missing
# key, or a network blip should not crash an analysis over flavour data). Core
# categories (prices, fundamentals, news) still raise so a broken primary is loud.
OPTIONAL_CATEGORIES = {"macro_data", "prediction_markets"}

# 方法到本地 CSV 厂商实现的映射（当前唯一数据源）
VENDOR_METHODS = {
    # core_stock_apis
    "get_observations": {
        "local_csv": get_local_observations,
    },
    # technical_indicators
    "get_hydrology_indicators": {
        "local_csv": get_local_hydrology_indicators,
    },
    # fundamental_data
    "get_environment_risk": {
        "local_csv": get_local_environment_risk,
    },
    "get_water_storage": {
        "local_csv": get_local_water_storage,
    },
    "get_river_flow": {
        "local_csv": get_local_river_flow,
    },
    "get_soil_moisture": {
        "local_csv": get_local_soil_moisture,
    },
    # news_data
    "get_rainfall_forecast": {
        "local_csv": get_local_rainfall_forecast,
        "online_api": get_online_rainfall_forecast,
    },
    "get_realtime_weather": {
        "online_api": get_online_realtime_weather,
    },
    "get_social_impact": {
        "local_csv": get_local_social_impact,
    },
    # macro_data
    "get_regional_indicators": {
        "local_csv": get_local_regional_indicators,
    },
    # prediction_markets
    "get_forward_forecast": {
        "local_csv": get_local_forward_forecast,
    },
}

def get_category_for_method(method: str) -> str:
    """Get the category that contains the specified method."""
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method '{method}' not found in any category")

def get_vendor(category: str, method: str = None) -> str:
    """Get the configured vendor for a data category or specific tool method.
    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    # Check tool-level configuration first (if method provided)
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    # Fall back to category-level configuration
    return config.get("data_vendors", {}).get(category, "default")

def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to appropriate vendor implementation with fallback support."""
    category = get_category_for_method(method)
    vendor_config = get_vendor(category, method)
    primary_vendors = [v.strip() for v in vendor_config.split(',')]

    if method not in VENDOR_METHODS:
        raise ValueError(f"Method '{method}' not supported")

    all_available_vendors = list(VENDOR_METHODS[method].keys())

    # The configured vendor list IS the chain: we do NOT silently fall back to
    # vendors the user did not choose (#988/#289) — that returned data from an
    # unexpected source and caused cross-vendor inconsistencies. For multi-vendor
    # fallback, list them in order, e.g. data_vendors="local_csv".
    # The "default" sentinel (no explicit config) uses all available vendors.
    explicit = [v for v in primary_vendors if v and v != "default"]
    if explicit:
        vendor_chain = [v for v in explicit if v in VENDOR_METHODS[method]]
        if not vendor_chain:
            raise ValueError(
                f"Configured vendor(s) {explicit} not available for '{method}'. "
                f"Available: {all_available_vendors}."
            )
    else:
        vendor_chain = all_available_vendors

    last_no_data: NoMarketDataError | None = None
    first_error: Exception | None = None
    for vendor in vendor_chain:
        vendor_impl = VENDOR_METHODS[method][vendor]
        impl_func = vendor_impl[0] if isinstance(vendor_impl, list) else vendor_impl

        try:
            return impl_func(*args, **kwargs)
        except VendorRateLimitError:
            logger.warning("Vendor %r rate-limited for %s; trying next vendor.", vendor, method)
            continue
        except VendorNotConfiguredError as e:
            logger.warning("Vendor %r not configured for %s; trying next vendor.", vendor, method)
            if first_error is None:
                first_error = e  # Surface it if no other vendor can serve the call.
            continue
        except NoMarketDataError as e:
            last_no_data = e  # No data here; another configured vendor may have it
            continue
        except Exception as e:
            # Don't let one vendor's failure crash the call when another can
            # serve it, but never swallow silently: a broken primary must be
            # visible in the logs (#989), not hidden behind a fallback's verdict.
            logger.warning("Vendor %r failed for %s: %s", vendor, method, e)
            if first_error is None:
                first_error = e
            continue

    # If any vendor reported "no data", the symbol is genuinely unavailable.
    # Return one explicit, instructive sentinel rather than a vendor-specific
    # empty string, so the agent reports "unavailable" instead of inventing a
    # value. This takes precedence over incidental fallback errors.
    if last_no_data is not None:
        if first_error is not None:
            # A vendor also hit a real error; surface it in logs so the no-data
            # verdict can't hide a broken primary (network/auth/etc.).
            logger.warning(
                "Returning NO_DATA for %s, but a vendor errored earlier: %s",
                method, first_error,
            )
        sym = last_no_data.symbol
        canonical = last_no_data.canonical
        resolved = "" if canonical == sym else f" (resolved to '{canonical}')"
        # Surface the typed error's detail (e.g. "latest row is 2025-06-11 ...
        # stale") so the agent sees the specific reason — invalid symbol, no
        # coverage, or stale data — not just a generic "unavailable".
        reason = f" ({last_no_data.detail})" if last_no_data.detail else ""
        return (
            f"NO_DATA_AVAILABLE: No usable market data for '{sym}'{resolved} from "
            f"any configured vendor{reason}. The symbol may be invalid, delisted, "
            f"not covered, or the vendor returned stale data. Do not estimate or "
            f"fabricate values — report that data is unavailable for this symbol."
        )

    # No vendor returned data and none reported clean "no data" — surface the
    # first real error (e.g. the primary vendor's network failure). Optional
    # enrichment categories degrade to a sentinel instead, so flavour data can't
    # abort the run.
    if first_error is not None:
        if category in OPTIONAL_CATEGORIES:
            logger.warning("Optional %s unavailable for %s: %s", category, method, first_error)
            return (
                f"DATA_UNAVAILABLE: optional {category} could not be retrieved "
                f"({first_error}). Proceed without it; do not fabricate values."
            )
        raise first_error

    raise RuntimeError(f"No available vendor for '{method}'")
