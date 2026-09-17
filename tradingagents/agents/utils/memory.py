"""Append-only markdown log of hydrology decisions."""

import re
from pathlib import Path

from tradingagents.alert_levels import parse_alert_level


class TradingMemoryLog:
    """Append-only markdown log of station alert decisions."""

    _SEPARATOR = "\n\n<!-- ENTRY_END -->\n\n"
    _DECISION_RE = re.compile(r"DECISION:\n(.*?)\Z", re.DOTALL)

    def __init__(self, config: dict | None = None):
        path = (config or {}).get("memory_log_path")
        self._log_path = Path(path).expanduser() if path else None
        if self._log_path:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def store_decision(
        self,
        station: str,
        analysis_date: str,
        final_alert_decision: str,
    ) -> None:
        """Append one decision unless this station/date is already logged."""
        if not self._log_path:
            return

        prefix = f"[{analysis_date} | {station} |"
        if self._log_path.exists():
            for line in self._log_path.read_text(encoding="utf-8").splitlines():
                if line.startswith(prefix):
                    return

        alert_level = parse_alert_level(final_alert_decision)
        tag = f"[{analysis_date} | {station} | {alert_level} | logged]"
        entry = (
            f"{tag}\n\nDECISION:\n{final_alert_decision}{self._SEPARATOR}"
        )
        with open(self._log_path, "a", encoding="utf-8") as handle:
            handle.write(entry)

    def load_entries(self) -> list[dict]:
        """Parse all decisions from the log."""
        if not self._log_path or not self._log_path.exists():
            return []
        text = self._log_path.read_text(encoding="utf-8")
        entries = []
        for raw in text.split(self._SEPARATOR):
            entry = self._parse_entry(raw.strip())
            if entry:
                entries.append(entry)
        return entries

    def get_past_context(
        self,
        station: str,
        n_same: int = 5,
        n_cross: int = 3,
        as_of: str | None = None,
    ) -> str:
        """Format earlier station decisions for prompt injection.

        When ``as_of`` is provided, only decisions strictly before that date are
        included so a historical run cannot consume a future decision.
        """
        entries = self.load_entries()
        if as_of is not None:
            entries = [entry for entry in entries if entry["date"] < as_of]
        if not entries:
            return ""

        same, cross = [], []
        for entry in reversed(entries):
            if len(same) >= n_same and len(cross) >= n_cross:
                break
            if entry["station"] == station and len(same) < n_same:
                same.append(entry)
            elif entry["station"] != station and len(cross) < n_cross:
                cross.append(entry)

        parts = []
        if same:
            parts.append(f"Past analyses of {station} (most recent first):")
            parts.extend(self._format_entry(entry) for entry in same)
        if cross:
            parts.append("Recent analyses of other stations:")
            parts.extend(self._format_entry(entry) for entry in cross)
        return "\n\n".join(parts)

    @staticmethod
    def _parse_entry(raw: str) -> dict | None:
        lines = raw.strip().splitlines()
        if not lines:
            return None
        tag_line = lines[0].strip()
        if not (tag_line.startswith("[") and tag_line.endswith("]")):
            return None
        fields = [field.strip() for field in tag_line[1:-1].split("|")]
        if len(fields) < 4:
            return None

        body = "\n".join(lines[1:]).strip()
        decision_match = TradingMemoryLog._DECISION_RE.search(body)
        return {
            "date": fields[0],
            "station": fields[1],
            "alert_level": fields[2],
            "status": fields[3],
            "decision": decision_match.group(1).strip() if decision_match else "",
        }

    @staticmethod
    def _format_entry(entry: dict) -> str:
        tag = (
            f"[{entry['date']} | {entry['station']} | "
            f"{entry['alert_level']} | {entry['status']}]"
        )
        return f"{tag}\nDECISION:\n{entry['decision']}"
