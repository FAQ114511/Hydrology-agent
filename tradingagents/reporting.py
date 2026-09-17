"""由命令行和程序接口共用的水文研判报告树写入器。"""

from datetime import datetime
from pathlib import Path


def write_report_tree(final_state: dict, area_name: str, save_path) -> Path:
    """把已完成研判的各阶段报告保存到 ``save_path``。"""
    save_path = Path(save_path)
    save_path.mkdir(parents=True, exist_ok=True)
    sections = []

    # 1. 专业分析
    analysts_dir = save_path / "1_analysts"
    analyst_parts = []
    if final_state.get("hydrology_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "hydrology.md").write_text(final_state["hydrology_report"], encoding="utf-8")
        analyst_parts.append(("水文分析师", final_state["hydrology_report"]))
    if final_state.get("social_impact_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "social_impact.md").write_text(final_state["social_impact_report"], encoding="utf-8")
        analyst_parts.append(("社会影响分析师", final_state["social_impact_report"]))
    if final_state.get("meteorology_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "meteorology.md").write_text(final_state["meteorology_report"], encoding="utf-8")
        analyst_parts.append(("气象分析师", final_state["meteorology_report"]))
    if final_state.get("environment_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "environment.md").write_text(final_state["environment_report"], encoding="utf-8")
        analyst_parts.append(("环境风险分析师", final_state["environment_report"]))
    if analyst_parts:
        content = "\n\n".join(f"### {name}\n{text}" for name, text in analyst_parts)
        sections.append(f"## 一、专业分析报告\n\n{content}")

    # 2. 风险研判
    if final_state.get("risk_debate_state"):
        research_dir = save_path / "2_risk_assessment"
        debate = final_state["risk_debate_state"]
        research_parts = []
        if debate.get("high_risk_history"):
            research_dir.mkdir(exist_ok=True)
            (research_dir / "risk.md").write_text(debate["high_risk_history"], encoding="utf-8")
            research_parts.append(("风险研判员", debate["high_risk_history"]))
        if debate.get("safety_history"):
            research_dir.mkdir(exist_ok=True)
            (research_dir / "safety.md").write_text(debate["safety_history"], encoding="utf-8")
            research_parts.append(("安全研判员", debate["safety_history"]))
        if debate.get("judge_decision"):
            research_dir.mkdir(exist_ok=True)
            (research_dir / "manager.md").write_text(debate["judge_decision"], encoding="utf-8")
            research_parts.append(("研判经理", debate["judge_decision"]))
        if research_parts:
            content = "\n\n".join(f"### {name}\n{text}" for name, text in research_parts)
            sections.append(f"## 二、风险研判结论\n\n{content}")

    # 3. 处置方案
    if final_state.get("dispatch_plan"):
        trading_dir = save_path / "3_dispatch"
        trading_dir.mkdir(exist_ok=True)
        (trading_dir / "dispatcher.md").write_text(final_state["dispatch_plan"], encoding="utf-8")
        sections.append(f"## 三、处置方案\n\n### 处置员\n{final_state['dispatch_plan']}")

    # 4. 响应处置辩论
    if final_state.get("response_debate_state"):
        risk_dir = save_path / "4_response_debate"
        risk = final_state["response_debate_state"]
        risk_parts = []
        if risk.get("aggressive_history"):
            risk_dir.mkdir(exist_ok=True)
            (risk_dir / "aggressive.md").write_text(risk["aggressive_history"], encoding="utf-8")
            risk_parts.append(("激进型研判员", risk["aggressive_history"]))
        if risk.get("conservative_history"):
            risk_dir.mkdir(exist_ok=True)
            (risk_dir / "conservative.md").write_text(risk["conservative_history"], encoding="utf-8")
            risk_parts.append(("保守型研判员", risk["conservative_history"]))
        if risk.get("neutral_history"):
            risk_dir.mkdir(exist_ok=True)
            (risk_dir / "neutral.md").write_text(risk["neutral_history"], encoding="utf-8")
            risk_parts.append(("中立型研判员", risk["neutral_history"]))
        if risk_parts:
            content = "\n\n".join(f"### {name}\n{text}" for name, text in risk_parts)
            sections.append(f"## 四、响应处置辩论\n\n{content}")

        # 5. 最终预警决策
        if risk.get("judge_decision"):
            portfolio_dir = save_path / "5_alert"
            portfolio_dir.mkdir(exist_ok=True)
            (portfolio_dir / "decision.md").write_text(risk["judge_decision"], encoding="utf-8")
            sections.append(f"## 五、最终预警决策\n\n### 预警决策员\n{risk['judge_decision']}")

    header = f"# 水文防汛研判报告：{area_name}\n\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    (save_path / "complete_report.md").write_text(header + "\n\n".join(sections), encoding="utf-8")
    return save_path / "complete_report.md"
