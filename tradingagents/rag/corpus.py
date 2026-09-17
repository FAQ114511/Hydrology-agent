from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class KnowledgeDocument:
    doc_id: str
    source: str
    content: str
    station: str | None = None
    date: str | None = None
    kind: str = "knowledge"
    title: str = ""
    metadata: dict = field(default_factory=dict)

_PROJECT_ROOT=Path(__file__).resolve().parents[2]
_DEFAULT_KNOWLEDGE_DIR=_PROJECT_ROOT / "runtime" / "knowledge"
_STATION_RE = re.compile(r"\b([A-Z][A-Z0-9_]{2,})\b")
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)

_STATION_LABELS = {
    "station_name": "站点名称",
    "river": "所在河流",
    "basin": "所属流域",
    "province": "省份",
    "city": "城市",
    "latitude": "纬度",
    "longitude": "经度",
    "warning_level_m": "警戒水位（米）",
    "guarantee_level_m": "保证水位（米）",
    "warning_flow_m3s": "警戒流量（立方米每秒）",
    "guarantee_flow_m3s": "保证流量（立方米每秒）",
    "historical_flood_note": "历史洪水说明",
}

_LEVEL_LABELS = {
    "blue": "蓝色预警",
    "yellow": "黄色预警",
    "orange": "橙色预警",
    "red": "红色预警",
}

_CONDITION_LABELS = {
    "water_level_m": "水位阈值（米）",
    "rainfall_24h_mm": "24小时雨量阈值（毫米）",
}

def _labeled(key:str,labels:dict[str,str])->str:
    label=labels.get(key)
    return f"{label} ({key})" if label else key

def _iter_station_entries(raw:dict):
    for key,value in raw.items():
        if str(key).startswith("_"):
            continue
        if isinstance(value,dict):
            yield str(key).upper(),value

def _compact(value)->str:
    if isinstance(value,(dict,list)):
        return json.dumps(value,ensure_ascii=False,sort_keys=True)
    return str(value)

def load_station_documents(knowledge_dir:Path)->list[KnowledgeDocument]:
    path=Path(knowledge_dir)/"stations.json"
    if not path.exists():
        return []
    raw=json.loads(path.read_text(encoding="utf-8"))
    documents:list[KnowledgeDocument]=[]
    for station,meta in _iter_station_entries(raw):
       lines=[f"站点{station}元数据："]
       lines.extend(
        f"-{_labeled(key, _STATION_LABELS)}: {_compact(value)}"
        for key,value in meta.items()
       )
       documents.append(
        KnowledgeDocument(
            doc_id=f"station:{station}",
            source=path.name,
            content="\n".join(lines),
            station=station,
            kind="station",
            title=f"站点{station}元数据",
        )
       )
    return documents

def load_alert_rule_documents(knowledge_dir:Path)->list[KnowledgeDocument]:
    path = Path(knowledge_dir) / "alert_rules.json"
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    documents: list[KnowledgeDocument] = []
    for station, rules in _iter_station_entries(raw):
        lines = [f"{station} 预警等级阈值："]
        for level, condition in rules.items():
            if isinstance(condition, dict):
                detail = "，".join(
                    f"{_labeled(k, _CONDITION_LABELS)}={v}"
                    for k, v in condition.items()
                )
            else:
                detail = str(condition)
            lines.append(f"- {_LEVEL_LABELS.get(level, level)} ({level}): {detail}")
        documents.append(
            KnowledgeDocument(
                doc_id=f"alert_rules:{station}",
                source=path.name,
                content="\n".join(lines),
                station=station,
                kind="rule",
                title=f"{station} 预警规则",
            )
        )
    return documents

def _detect_station(text: str, known_stations: set[str]) -> str | None:
    for token in _STATION_RE.findall(text):
        if token in known_stations:
            return token
    return None

def load_markdown_documents(
    knowledge_dir: Path, known_stations: set[str] | None = None
) -> list[KnowledgeDocument]:
    known = known_stations or set()
    documents: list[KnowledgeDocument] = []
    for path in sorted(Path(knowledge_dir).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        matches = list(_HEADING_RE.finditer(text))
        if not matches:
            sections = [("总览", text)]
        else:
            sections = []
            for index, match in enumerate(matches):
                end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
                sections.append((match.group(1).strip(), text[match.start():end].strip()))
        for index, (title, body) in enumerate(sections):
            dates = _DATE_RE.findall(body)
            is_case = "案例" in title or "case" in path.stem.lower()
            documents.append(
                KnowledgeDocument(
                    doc_id=f"{path.stem}:{index}",
                    source=path.name,
                    content=body,
                    station=_detect_station(body, known),
                    date=dates[0] if dates else None,
                    kind="case" if is_case else "guideline",
                    title=title,
                )
            )
    return documents


def load_memory_documents(memory_path: Path) -> list[KnowledgeDocument]:
    path = Path(memory_path)
    if not path.exists():
        return []
    from tradingagents.agents.utils.memory import TradingMemoryLog

    log = TradingMemoryLog({"memory_log_path": str(path)})
    documents: list[KnowledgeDocument] = []
    for entry in log.load_entries():
        body = (entry.get("decision") or "").strip()
        if not body:
            continue
        documents.append(
            KnowledgeDocument(
                doc_id=f"memory:{entry['date']}:{entry['station']}",
                source=path.name,
                content=body,
                station=entry["station"],
                date=entry["date"],
                kind="memory",
                title=f"{entry['station']} {entry['date']} 历史研判",
                metadata={"alert_level": entry.get("alert_level")},
            )
        )
    return documents


def build_corpus(
    knowledge_dir: Path | None = None, memory_path: Path | None = None
) -> list[KnowledgeDocument]:
    directory = Path(knowledge_dir) if knowledge_dir else _DEFAULT_KNOWLEDGE_DIR
    documents: list[KnowledgeDocument] = []
    documents.extend(load_station_documents(directory))
    documents.extend(load_alert_rule_documents(directory))
    known = {doc.station for doc in documents if doc.station}
    documents.extend(load_markdown_documents(directory, known_stations=known))
    if memory_path:
        documents.extend(load_memory_documents(memory_path))
    return documents
