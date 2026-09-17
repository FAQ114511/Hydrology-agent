# TradingAgents/graph/trading_graph.py

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from langgraph.prebuilt import ToolNode

# Import the abstract tool methods from agent_utils
from tradingagents.agents.utils.agent_utils import (
    build_area_context,
    get_environment_risk,
    get_forward_forecast,
    get_hydrology_indicators,
    get_observations,
    get_rainfall_forecast,
    get_realtime_weather,
    get_regional_indicators,
    get_river_flow,
    get_social_impact,
    get_soil_moisture,
    get_verified_observation_snapshot,
    get_water_storage,
    resolve_station_identity,
    search_flood_knowledge,
)
from tradingagents.agents.utils.memory import TradingMemoryLog
from tradingagents.dataflows.config import set_config
from tradingagents.dataflows.utils import safe_ticker_component
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.llm_clients import create_llm_client
from tradingagents.reporting import write_report_tree

from .checkpointer import checkpoint_step, clear_checkpoint, get_checkpointer, thread_id
from .conditional_logic import ConditionalLogic
from .propagation import Propagator
from .setup import GraphSetup
from .signal_processing import SignalProcessor

logger = logging.getLogger(__name__)


def _coerce_max_retries(value):
    """Validate an ``llm_max_retries`` value to a non-negative int.

    Accepts an int or a numeric string (env vars arrive as strings). Rejects
    booleans and negatives loudly so a misconfiguration fails at startup rather
    than silently disabling retries.
    """
    if isinstance(value, bool):
        raise ValueError(f"llm_max_retries must be an integer, not a boolean: {value!r}")
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"llm_max_retries must be an integer, got {value!r}") from exc
    if n < 0:
        raise ValueError(f"llm_max_retries must be >= 0, got {n}")
    return n


def _coerce_max_tokens(value):
    """Validate a ``max_tokens`` value to a positive int (env vars are strings)."""
    if isinstance(value, bool):
        raise ValueError(f"max_tokens must be an integer, not a boolean: {value!r}")
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"max_tokens must be an integer, got {value!r}") from exc
    if n <= 0:
        raise ValueError(f"max_tokens must be > 0, got {n}")
    return n


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=("market", "social", "news", "fundamentals"),
        debug=False,
        config: dict[str, Any] = None,
        callbacks: list | None = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
            callbacks: Optional list of callback handlers (e.g., for tracking LLM/tool stats)
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.callbacks = callbacks or []

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(self.config["data_cache_dir"], exist_ok=True)
        os.makedirs(self.config["results_dir"], exist_ok=True)

        # Initialize LLMs with provider-specific thinking configuration
        llm_kwargs = self._get_provider_kwargs()

        # Add callbacks to kwargs if provided (passed to LLM constructor)
        if self.callbacks:
            llm_kwargs["callbacks"] = self.callbacks

        deep_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["deep_think_llm"],
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )
        quick_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["quick_think_llm"],
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )

        self.deep_thinking_llm = deep_client.get_llm()
        self.quick_thinking_llm = quick_client.get_llm()

        self.memory_log = TradingMemoryLog(self.config)

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.config["max_debate_rounds"],
            max_risk_discuss_rounds=self.config["max_risk_discuss_rounds"],
        )
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.tool_nodes,
            self.conditional_logic,
        )

        self.propagator = Propagator(
            max_recur_limit=self.config.get("max_recur_limit", 100),
        )
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # Graph-shape-affecting run choices, kept for the checkpoint signature.
        self.selected_analysts = tuple(selected_analysts)

        # Set up the graph: keep the workflow for recompilation with a checkpointer.
        self.workflow = self.graph_setup.setup_graph(selected_analysts)
        self.graph = self.workflow.compile()
        self._checkpointer_ctx = None
        self._resuming = False

    def _get_provider_kwargs(self) -> dict[str, Any]:
        """Get provider-specific kwargs for LLM client creation."""
        kwargs = {}
        provider = self.config.get("llm_provider", "").lower()

        if provider == "google":
            thinking_level = self.config.get("google_thinking_level")
            if thinking_level:
                kwargs["thinking_level"] = thinking_level

        elif provider == "openai":
            reasoning_effort = self.config.get("openai_reasoning_effort")
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort

        elif provider == "anthropic":
            effort = self.config.get("anthropic_effort")
            if effort:
                kwargs["effort"] = effort

        # Sampling temperature is cross-provider: forward it whenever set.
        # float() here so a value coming from a TRADINGAGENTS_TEMPERATURE env
        # string ("0.2") works the same as a programmatic float.
        temperature = self.config.get("temperature")
        if temperature is not None and temperature != "":
            kwargs["temperature"] = float(temperature)

        # SDK retry budget is cross-provider. Forward it only when explicitly set
        # so each provider keeps its own default (usually 2) otherwise (#1091).
        max_retries = self.config.get("llm_max_retries")
        if max_retries is not None and max_retries != "":
            kwargs["max_retries"] = _coerce_max_retries(max_retries)

        # Output-token cap is cross-provider, but Gemini names it
        # ``max_output_tokens``; forward under the right key when set (#1204).
        max_tokens = self.config.get("max_tokens")
        if max_tokens is not None and max_tokens != "":
            key = "max_output_tokens" if provider == "google" else "max_tokens"
            kwargs[key] = _coerce_max_tokens(max_tokens)

        return kwargs

    def _create_tool_nodes(self) -> dict[str, ToolNode]:
        """Create tool nodes for different data sources using abstract methods."""
        return {
            "market": ToolNode(
                [
                    # 站点观测数据
                    get_observations,
                    # Technical indicators
                    get_hydrology_indicators,
                    # Deterministic verification snapshot (bound to the analyst
                    # LLM and required by its prompt; must be executable here or
                    # the call fails and the model reports it "unavailable").
                    get_verified_observation_snapshot,
                ]
            ),
            "social": ToolNode(
                [
                    # News tools for social media analysis
                    get_social_impact,
                    get_rainfall_forecast,
                ]
            ),
            "news": ToolNode(
                [
                    # News and insider information
                    get_rainfall_forecast,
                    get_realtime_weather,
                    get_regional_indicators,
                    get_forward_forecast,
                    search_flood_knowledge,
                ]
            ),
            "fundamentals": ToolNode(
                [
                    # Fundamental analysis tools
                    get_environment_risk,
                    get_water_storage,
                    get_river_flow,
                    get_soil_moisture,
                    search_flood_knowledge,
                ]
            ),
        }

    def resolve_area_context(self, area_name: str, asset_type: str = "flood") -> str:
        """解析一次站点身份并返回完整的区域上下文。"""
        identity = resolve_station_identity(area_name, self.config.get("stations_path"))
        return build_area_context(area_name, asset_type, identity)

    def _run_signature(self, asset_type: str) -> str:
        """Graph-shape inputs that must invalidate a checkpoint if changed.

        Keyed into the checkpoint thread ID so a resume under a different analyst
        selection, debate/risk depth, or asset mode starts fresh instead of
        silently continuing the previous graph (#1089).
        """
        return "|".join([
            "analysts=" + ",".join(self.selected_analysts),
            f"debate={self.config['max_debate_rounds']}",
            f"risk={self.config['max_risk_discuss_rounds']}",
            f"asset={asset_type}",
        ])

    def propagate(self, area_name, analysis_date, asset_type: str = "flood"):
        """对指定区域和日期执行水文防汛研判图。

        返回 ``(final_state, signal)``；``signal`` 为红、橙、黄、蓝预警之一，
        最终输出无法识别时返回 ``"REVIEW"``。防汛模式不执行金融收益回溯。
        """
        self.ticker = area_name

        with self.checkpoint_scope(area_name, analysis_date, asset_type) as thread_id_value:
            return self._run_graph(
                area_name, analysis_date, asset_type=asset_type,
                checkpoint_thread_id=thread_id_value,
            )

    def begin_checkpoint(self, company_name, trade_date, asset_type: str = "stock") -> str | None:
        """Recompile the graph with a per-ticker checkpointer and return the
        ``thread_id`` to inject into the stream/invoke ``config`` (or ``None``
        when checkpointing is disabled).

        Pair every call with :meth:`end_checkpoint` in a ``finally``. Both
        ``propagate`` (via :meth:`checkpoint_scope`) and the CLI stream path use
        this so ``--checkpoint`` actually resumes (#1249); previously the setup
        lived only inside ``propagate`` and the CLI streamed the checkpointer-less
        graph, making the flag a no-op.
        """
        self._resuming = False
        if not self.config.get("checkpoint_enabled"):
            return None
        signature = self._run_signature(asset_type)
        self._checkpointer_ctx = get_checkpointer(self.config["data_cache_dir"], company_name)
        saver = self._checkpointer_ctx.__enter__()
        self.graph = self.workflow.compile(checkpointer=saver)

        step = checkpoint_step(
            self.config["data_cache_dir"], company_name, str(trade_date), signature
        )
        self._resuming = step is not None
        if step is not None:
            logger.info("Resuming from step %d for %s on %s", step, company_name, trade_date)
        else:
            logger.info("Starting fresh for %s on %s", company_name, trade_date)
        return thread_id(company_name, str(trade_date), signature)

    def checkpoint_input(self, init_state):
        """The value to stream/invoke: ``None`` to resume an existing checkpoint,
        else the initial state for a fresh run.

        LangGraph resumes an interrupted thread when invoked with ``None``;
        re-passing the initial state instead appends it through the message
        reducer, duplicating messages in the resumed state (#1249).
        """
        return None if self._resuming else init_state

    def end_checkpoint(self):
        """Restore the plain uncheckpointed graph after a checkpointed run."""
        if self._checkpointer_ctx is not None:
            self._checkpointer_ctx.__exit__(None, None, None)
            self._checkpointer_ctx = None
            self.graph = self.workflow.compile()
        self._resuming = False

    @contextmanager
    def checkpoint_scope(self, company_name, trade_date, asset_type: str = "stock"):
        """Context-manager form of begin/end_checkpoint for the propagate path."""
        try:
            yield self.begin_checkpoint(company_name, trade_date, asset_type)
        finally:
            self.end_checkpoint()

    def clear_checkpoint_on_success(self, company_name, trade_date, asset_type: str = "stock"):
        """Drop a completed run's checkpoint so a later run starts fresh (#1249)."""
        if self.config.get("checkpoint_enabled"):
            clear_checkpoint(
                self.config["data_cache_dir"], company_name, str(trade_date),
                self._run_signature(asset_type),
            )

    def save_reports(self, final_state, ticker, save_path=None) -> Path:
        """Write the markdown report tree for a completed run, like the CLI does.

        Programmatic callers get the same on-disk reports the CLI produces. Pass
        an explicit ``save_path`` or let it default under ``results_dir``.
        """
        if save_path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = (
                Path(self.config["results_dir"])
                / "reports"
                / f"{safe_ticker_component(ticker)}_{stamp}"
            )
        return write_report_tree(final_state, ticker, save_path)

    def _run_graph(self, area_name, analysis_date, asset_type: str = "flood",
                   checkpoint_thread_id: str | None = None):
        """Execute the graph and write the resulting state to disk and memory log."""
        # Initialize state — inject memory log context for PM and the
        # deterministically resolved instrument identity for all agents. On a
        # historical run, gate lessons to those whose outcome was known by the
        # trade date so a backtest can't learn from the future (#1251).
        past_context = self.memory_log.get_past_context(
            area_name, as_of=analysis_date
        )
        area_context = self.resolve_area_context(area_name, asset_type)
        init_agent_state = self.propagator.create_initial_state(
            area_name,
            analysis_date,
            asset_type=asset_type,
            past_context=past_context,
            area_context=area_context,
        )
        args = self.propagator.get_graph_args()

        # Inject the checkpoint thread_id (from checkpoint_scope) so the same
        # ticker+date+graph-shape resumes; a different one starts fresh (#1089).
        if checkpoint_thread_id is not None:
            args.setdefault("config", {}).setdefault("configurable", {})["thread_id"] = checkpoint_thread_id

        # None resumes an existing checkpoint; init_agent_state starts fresh (#1249).
        graph_input = self.checkpoint_input(init_agent_state)
        if self.debug:
            trace = []
            last_printed = None
            for chunk in self.graph.stream(graph_input, **args):
                if chunk["messages"]:
                    msg = chunk["messages"][-1]
                    # Nodes after the trader don't append to messages, so the
                    # same trailing message repeats across chunks. Print it only
                    # when it changes (#1027); the trace/state merge is unchanged.
                    signature = (type(msg).__name__, getattr(msg, "content", None))
                    if signature != last_printed:
                        msg.pretty_print()
                        last_printed = signature
                    trace.append(chunk)
            # Streamed chunks are per-node deltas. Merge them so the returned
            # state matches what graph.invoke() yields in the non-debug path.
            final_state = {}
            for chunk in trace:
                final_state.update(chunk)
        else:
            final_state = self.graph.invoke(graph_input, **args)

        # Keep the latest state available to callers.
        self.curr_state = final_state

        # Log state to disk.
        self._log_state(analysis_date, final_state)

        # Store this decision for later runs of the same station.
        self.memory_log.store_decision(
            station=area_name,
            analysis_date=analysis_date,
            final_alert_decision=final_state["final_alert_decision"],
        )

        # Clear checkpoint on successful completion to avoid stale state.
        self.clear_checkpoint_on_success(area_name, analysis_date, asset_type)

        return final_state, self.process_signal(final_state["final_alert_decision"])

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "area_of_interest": final_state["area_of_interest"],
            "analysis_date": final_state["analysis_date"],
            "hydrology_report": final_state["hydrology_report"],
            "social_impact_report": final_state["social_impact_report"],
            "meteorology_report": final_state["meteorology_report"],
            "environment_report": final_state["environment_report"],
            "risk_debate_state": {
                "high_risk_history": final_state["risk_debate_state"]["high_risk_history"],
                "safety_history": final_state["risk_debate_state"]["safety_history"],
                "history": final_state["risk_debate_state"]["history"],
                "current_response": final_state["risk_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["risk_debate_state"][
                    "judge_decision"
                ],
            },
            "dispatch_plan": final_state["dispatch_plan"],
            "response_debate_state": {
                "aggressive_history": final_state["response_debate_state"]["aggressive_history"],
                "conservative_history": final_state["response_debate_state"]["conservative_history"],
                "neutral_history": final_state["response_debate_state"]["neutral_history"],
                "history": final_state["response_debate_state"]["history"],
                "judge_decision": final_state["response_debate_state"]["judge_decision"],
            },
            "assessment_plan": final_state["assessment_plan"],
            "final_alert_decision": final_state["final_alert_decision"],
        }

        # Save to file. Reject ticker values that would escape the
        # results directory when joined as a path component.
        safe_ticker = safe_ticker_component(self.ticker)
        directory = Path(self.config["results_dir"]) / safe_ticker / "TradingAgentsStrategy_logs"
        directory.mkdir(parents=True, exist_ok=True)

        log_path = directory / f"full_states_log_{trade_date}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(self.log_states_dict[str(trade_date)], f, indent=4)

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)
