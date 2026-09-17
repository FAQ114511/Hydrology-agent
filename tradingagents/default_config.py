import copy
import os

_TRADINGAGENTS_HOME = os.path.join(os.path.expanduser("~"), ".tradingagents")
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# Single source of truth for env-var → config-key overrides. To expose
# a new config key for environment-based override, add a row here — no
# entry-point script changes required. Coercion is driven by the type
# of the existing default, so users can keep writing plain strings in
# their .env file.
_ENV_OVERRIDES = {
    "TRADINGAGENTS_LLM_PROVIDER":         "llm_provider",
    "TRADINGAGENTS_DEEP_THINK_LLM":       "deep_think_llm",
    "TRADINGAGENTS_QUICK_THINK_LLM":      "quick_think_llm",
    "TRADINGAGENTS_LLM_BACKEND_URL":      "backend_url",
    "TRADINGAGENTS_OUTPUT_LANGUAGE":      "output_language",
    "TRADINGAGENTS_MAX_DEBATE_ROUNDS":    "max_debate_rounds",
    "TRADINGAGENTS_MAX_RISK_ROUNDS":      "max_risk_discuss_rounds",
    "TRADINGAGENTS_CHECKPOINT_ENABLED":   "checkpoint_enabled",
    "TRADINGAGENTS_TEMPERATURE":          "temperature",
    "TRADINGAGENTS_LLM_MAX_RETRIES":      "llm_max_retries",
    "TRADINGAGENTS_MAX_TOKENS":           "max_tokens",
    # Provider-specific reasoning/thinking knobs (None = each provider's own
    # default). Settable here for non-interactive runs; the CLI also offers an
    # interactive choice, which is skipped when the matching var is set.
    "TRADINGAGENTS_GOOGLE_THINKING_LEVEL":   "google_thinking_level",
    "TRADINGAGENTS_OPENAI_REASONING_EFFORT": "openai_reasoning_effort",
    "TRADINGAGENTS_ANTHROPIC_EFFORT":        "anthropic_effort",
}


_BOOL_TRUE = ("true", "1", "yes", "on")
_BOOL_FALSE = ("false", "0", "no", "off")


def _coerce(value: str, reference):
    """Coerce env-var string to the type of the existing default value.

    Invalid values raise ``ValueError`` rather than silently falling back to a
    default — a misspelled boolean (e.g. ``treu``) or non-numeric int should fail
    loudly at startup, not quietly misconfigure an unattended run.
    """
    if isinstance(reference, bool):
        normalized = value.strip().lower()
        if normalized in _BOOL_TRUE:
            return True
        if normalized in _BOOL_FALSE:
            return False
        raise ValueError(
            f"expected a boolean ({'/'.join(_BOOL_TRUE + _BOOL_FALSE)}), got {value!r}"
        )
    if isinstance(reference, int) and not isinstance(reference, bool):
        return int(value)
    if isinstance(reference, float):
        return float(value)
    return value


def _apply_env_overrides(config: dict) -> dict:
    """Apply TRADINGAGENTS_* env vars to the config dict in-place."""
    for env_var, key in _ENV_OVERRIDES.items():
        raw = os.environ.get(env_var)
        if raw is None or raw == "":
            continue
        try:
            config[key] = _coerce(raw, config.get(key))
        except ValueError as exc:
            raise ValueError(f"Invalid value for {env_var}: {exc}") from exc
    return config


DEFAULT_CONFIG = _apply_env_overrides({
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", os.path.join(_TRADINGAGENTS_HOME, "logs")),
    "data_cache_dir": os.getenv("TRADINGAGENTS_CACHE_DIR", os.path.join(_TRADINGAGENTS_HOME, "cache")),
    "memory_log_path": os.getenv("TRADINGAGENTS_MEMORY_LOG_PATH", os.path.join(_TRADINGAGENTS_HOME, "memory", "trading_memory.md")),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.6",
    "quick_think_llm": "gpt-5.6-luna",
    # When None, each provider's client falls back to its own default endpoint
    # (api.openai.com for OpenAI, generativelanguage.googleapis.com for Gemini, ...).
    # The CLI overrides this per provider when the user picks one. Keeping a
    # provider-specific URL here would leak (e.g. OpenAI's /v1 was previously
    # being forwarded to Gemini, producing malformed request URLs).
    "backend_url": None,
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    "anthropic_effort": None,           # "high", "medium", "low"
    # Sampling temperature, forwarded to every provider when set. None leaves
    # each provider at its own default. Lower values reduce run-to-run
    # variation on models that honor it; reasoning models largely ignore it
    # and no setting makes LLM output bit-identical across runs (see README).
    "temperature": None,
    # SDK retry budget forwarded to every provider chat client. None leaves each
    # provider/SDK at its own default (usually 2). Raise it to ride out bursty
    # 429 throttling on rate-limited deployments instead of aborting a run (#1091).
    "llm_max_retries": None,
    # Cap on output tokens forwarded to every provider chat client. None leaves
    # each provider at its own default. Set it to bound a model that emits
    # unbounded reasoning/output and hangs or trips a gateway idle timeout
    # (e.g. some deepseek-v4-flash deployments, #1204).
    "max_tokens": None,
    # Checkpoint/resume: when True, LangGraph saves state after each node
    # so a crashed run can resume from the last successful step.
    "checkpoint_enabled": False,
    # Output language for analyst reports and final decision
    # Internal agent debate stays in English for reasoning quality
    "output_language": "English",
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # 资料获取参数：数值越大，回溯范围越广，但提示词 token 占用也越高。
    "news_article_limit": 20,             # 单个站点的资料条目上限
    "global_news_article_limit": 10,      # 区域/宏观资料条目上限
    "global_news_lookback_days": 7,       # 区域资料回溯天数
    # Data vendor configuration
    # 本项目唯一数据源为本地 CSV，所有工具类别统一路由到 local_csv。
    "data_vendors": {
        "core_stock_apis": "local_csv",
        "technical_indicators": "local_csv",
        "fundamental_data": "local_csv",
        "news_data": "local_csv",
        "macro_data": "local_csv",
        "prediction_markets": "local_csv",
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {},
})


def build_hydrology_config() -> dict:
    """Return the shared runtime configuration for hydrology analyses."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    runtime_dir = os.path.join(_PROJECT_ROOT, "runtime")

    config["rag_enabled"] = True
    config["rag_knowledge_dir"] = os.path.join(runtime_dir, "knowledge")
    config["rag_memory_enabled"] = True
    config["rag_top_k"] = 5
    config["rag_mode"] = "keyword"
    config["memory_log_path"] = os.path.join(runtime_dir, "memory", "hydrology_memory.md")
    config["results_dir"] = os.path.join(_PROJECT_ROOT, "results")
    config["data_cache_dir"] = os.path.join(runtime_dir, "cache")
    config["local_data_dir"]=None
    config["stations_path"]=None

    config["weather_api_timeout"] = 10
    config["weather_api_retries"] = 2
    config["weather_retry_backoff_seconds"] = 0.2
    config["weather_cache_ttl_seconds"] = 900
    config["weather_cache_dir"] = os.path.join(runtime_dir, "cache", "weather")
    config["weather_fallback_to_local"] = True
    config["weather_realtime_past_days"] = 7
    # forecast_days 含当天，取 3 才能真正覆盖「未来 48 小时」。
    config["weather_realtime_forecast_days"] = 3

    config["data_vendors"] = {
        "core_stock_apis": "local_csv",
        "technical_indicators": "local_csv",
        "fundamental_data": "local_csv",
        "news_data": "online_api,local_csv",
        "macro_data": "local_csv",
        "prediction_markets": "local_csv",
    }
    config["tool_vendors"] = {
        "get_rainfall_forecast": "online_api,local_csv",
        "get_realtime_weather": "online_api",
        "get_social_impact": "local_csv",
    }
    return config
