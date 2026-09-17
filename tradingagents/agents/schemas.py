"""智能体结构化输出所使用的 Pydantic schema（防汛水文监测情景）。

框架的主要产出物仍然是自然语言散文：每个智能体的推理文字会被写入本地
markdown 报告，并作为下游智能体的上下文继续读取。结构化输出只叠加在三个
决策类智能体（研判经理、处置员、预警决策员）以及社会影响分析师之上，目的是：

- 让它们的输出在不同模型供应商之间保持一致的章节结构
- 复用各供应商原生的结构化输出能力（OpenAI/xAI 用 json_schema，
  Gemini 用 response_schema，Anthropic 用 tool-use）
- 把 schema 的字段描述直接当作模型的输出指令，提示词正文只需交代上下文与
  预警分级标准
- 各 render 函数把解析后的 Pydantic 实例还原成同样的 markdown 结构，
  因此展示层、记忆日志、报告文件都无需感知结构化输出的存在
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 共用的分级枚举
# ---------------------------------------------------------------------------


class AlertLevel(str, Enum):
    """四级防汛预警等级，由研判经理与预警决策员产出。"""

    RED = "红色预警"
    ORANGE = "橙色预警"
    YELLOW = "黄色预警"
    BLUE = "蓝色预警"


class DispatchAction(str, Enum):
    """三档处置动作，由处置员产出。

    处置员的职责是把研判经理的研判方案落成一条可执行的处置指令：
    这一轮该启动应急响应、加强监测，还是维持常规监测。
    具体的预警等级由后面的预警决策员在三级辩论之后敲定。
    """

    EMERGENCY_RESPONSE = "启动应急响应"
    STRENGTHEN_MONITORING = "加强监测预警"
    ROUTINE_MONITORING = "维持常规监测"


class SocialImpactBand(str, Enum):
    """社会影响程度档位，由社会影响分析师产出。"""

    SEVERE = "严重影响"
    MODERATE = "一般影响"
    LOW = "轻微影响"


# ---------------------------------------------------------------------------
# 研判经理
# ---------------------------------------------------------------------------


class AssessmentPlan(BaseModel):
    """研判经理产出的结构化研判方案。

    交接给处置员：recommendation 给出预警等级的倾向，rationale 记录辩论中
    哪一方的论据更有说服力，strategic_actions 把它转成处置员可执行的
    具体监测与处置动作。
    """

    recommendation: AlertLevel = Field(
        description=(
            "研判建议的预警等级。红/橙/黄/蓝中恰好选一个。"
            "当证据平衡、彼此矛盾、含糊不清或不足以支持更高等级时选蓝色预警；"
            "否则选论据明显更充分的那一侧。不要为了显得果断而硬抬等级。"
        ),
    )
    rationale: str = Field(
        description=(
            "以口语化的方式概括风险侧与安全侧辩论的要点，并说明是哪些论据"
            "导向了最终的等级判断。像在跟同事讲话一样自然。"
        ),
    )
    strategic_actions: str = Field(
        description=(
            "处置员落实该等级所需的具体动作，包括监测频次、巡查范围、"
            "预警发布对象等与等级相匹配的建议。"
        ),
    )


def render_assessment_plan(plan: AssessmentPlan) -> str:
    """把 AssessmentPlan 渲染成 markdown，供存储与处置员的提示词上下文使用。"""
    return "\n".join([
        f"**研判建议**: {plan.recommendation.value}",
        "",
        f"**判断依据**: {plan.rationale}",
        "",
        f"**处置措施**: {plan.strategic_actions}",
    ])


# ---------------------------------------------------------------------------
# 处置员
# ---------------------------------------------------------------------------


class DispatchProposal(BaseModel):
    """处置员产出的结构化处置方案。

    处置员阅读研判经理的研判方案与各分析师报告，把三者转化为一份具体处置
    安排：采取哪一档动作、支撑该动作的理由，以及建议的响应等级。
    """

    action: DispatchAction = Field(
        description=(
            "处置动作。启动应急响应 / 加强监测预警 / 维持常规监测，恰好选一个。"
        ),
    )
    reasoning: str = Field(
        description=(
            "给出该动作的理由，必须落在分析师报告与研判方案的具体证据上。"
            "两到四句话。"
        ),
    )
    response_level: str | None = Field(
        default=None,
        description=(
            "可选的响应等级说明，例如 '区级 IV 级应急响应' 或 "
            "'加密到 1 小时一报'。没有明确安排时留空。"
        ),
    )


def render_dispatch_proposal(proposal: DispatchProposal) -> str:
    """把 DispatchProposal 渲染成 markdown。

    末尾的 ``FINAL DISPATCH PLAN: **启动应急响应/加强监测预警/维持常规监测**``
    是给提示词用的停止信号，也是外部代码检索处置结论的锚点。
    """
    parts = [
        f"**处置动作**: {proposal.action.value}",
        "",
        f"**理由**: {proposal.reasoning}",
    ]
    if proposal.response_level:
        parts.extend(["", f"**响应等级**: {proposal.response_level}"])
    parts.extend([
        "",
        f"FINAL DISPATCH PLAN: **{proposal.action.value}**",
    ])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 预警决策员
# ---------------------------------------------------------------------------


class AlertDecision(BaseModel):
    """预警决策员产出的结构化输出。

    模型在同一次 LLM 调用中填完全部字段，无需额外的抽取步骤。字段描述同时
    充当模型输出指令，因此提示词正文只需提供上下文与分级标准。
    """

    rating: AlertLevel = Field(
        description=(
            "最终预警等级。红/橙/黄/蓝中恰好选一个，依据各分析师报告与三方"
            "辩论作出。当证据平衡、彼此矛盾、含糊不清或不足以支撑更高等级时，"
            "宁可保守也不要为了显得果断而抬高等级。"
        ),
    )
    executive_summary: str = Field(
        description=(
            "简洁的行动安排，涵盖处置动作、影响区域、关键风险水位与时段。"
            "两到四句话。"
        ),
    )
    assessment_thesis: str = Field(
        description=(
            "详细理由，必须引用各分析师报告与辩论中提出的具体证据。"
            "若提示词上下文中给出了历史经验教训，则一并参考；"
            "否则只依据本次分析。"
        ),
    )
    affected_area: str | None = Field(
        default=None,
        description="可选的受影响区域描述，例如 '湘江下游沿岸低洼区'。",
    )
    valid_period: str | None = Field(
        default=None,
        description="可选的预警有效时段，例如 '2024-05-10 至 2024-05-13'。",
    )


def render_alert_decision(decision: AlertDecision) -> str:
    """把 AlertDecision 渲染回系统其余部分消费的 markdown 形态。

    记忆日志、命令行展示、保存的报告文件都读取这段 markdown，
    因此渲染时保留固定的章节标题（``**预警等级**``、``**行动摘要**``、
    ``**研判结论**``）。
    """
    parts = [
        f"**预警等级**: {decision.rating.value}",
        "",
        f"**行动摘要**: {decision.executive_summary}",
        "",
        f"**研判结论**: {decision.assessment_thesis}",
    ]
    if decision.affected_area:
        parts.extend(["", f"**影响区域**: {decision.affected_area}"])
    if decision.valid_period:
        parts.extend(["", f"**预警时段**: {decision.valid_period}"])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 社会影响分析师
# ---------------------------------------------------------------------------


class SocialImpactReport(BaseModel):
    """社会影响分析师产出的结构化报告。

    取代此前的自由散文输出，让下游消费者（看板、审计日志、报告渲染器、
    其他智能体）可以直接读取 overall_band 与 overall_score，而不必维护
    会随模型版本漂移的正则兜底。narrative 保留逐项分析，
    render_social_impact_report 在开头拼一段确定性表头，
    使保存的报告依旧可读。
    """

    overall_band: SocialImpactBand = Field(
        description=(
            "总体社会影响程度。严重影响 / 一般影响 / 轻微影响，恰好选一个。"
            "当各类信号指向不同方向时选一般影响。"
        ),
    )
    overall_score: float = Field(
        ge=0.0,
        le=10.0,
        description=(
            "0–10 的影响强度数值。0 = 几乎无影响，5 = 中等影响，"
            "10 = 影响极其严重。与 overall_band 保持一致的参考区间："
            "严重影响约 6.5–10，一般影响约 3.5–6.4，轻微影响约 0–3.4。"
            "只强制校验 0–10 的边界。"
        ),
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description=(
            "基于数据质量与样本量的判断置信度。当有数据源返回占位内容或"
            "数据点少于 5 个时选 'low'；数据存在但稀薄时选 'medium'；"
            "各数据源都给出实质内容时选 'high'。"
        ),
    )
    narrative: str = Field(
        description=(
            "完整的社会影响报告，依次包含："
            "(1) 逐项列出具体证据（引用观测条数、比例、关键事件）；"
            "(2) 各项信号之间的分歧与一致之处；"
            "(3) 主要的影响主题（受影响人口、交通、农业、转移安置等）；"
            "(4) 由数据揭示的诱因与风险；"
            "(5) 一张 markdown 表格汇总关键信号、其指向、来源与支撑证据。"
            "内容要扎实：每一节都用具体证据展开，为处置员新增有效信息。"
        ),
    )


def render_social_impact_report(report: SocialImpactReport) -> str:
    """把 SocialImpactReport 渲染成系统其余部分消费的 markdown。

    结构化表头（影响档位 + 分值 + 置信度）拼在 narrative 之前，
    使保存的报告既便于人读也便于机器解析，无需正则。
    """
    return "\n".join([
        f"**总体社会影响：** **{report.overall_band.value}** "
        f"(强度: {report.overall_score:.1f}/10)",
        f"**置信度:** {report.confidence}",
        "",
        report.narrative,
    ])
