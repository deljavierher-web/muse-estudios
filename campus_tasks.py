"""Parser seguro y portable de feeds iCalendar de plataformas académicas."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


def validate_feed_url(url: str) -> str:
    """Accept HTTPS feed URLs without ever including them in errors."""
    candidate = url.strip() if isinstance(url, str) else ""
    try:
        parsed = urlsplit(candidate)
        valid = (
            parsed.scheme.lower() == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Feed URL must be a complete HTTPS URL; its value was not logged.")
    return candidate


def _unfold_ical(text: str) -> str:
    """Join RFC 5545 folded lines (CRLF followed by space or tab)."""
    return re.sub(r"\r?\n[ \t]", "", text)


def _unescape_ical(value: str) -> str:
    """Decode the text escapes used by common iCalendar feeds."""
    replacements = {"n": "\n", "N": "\n", ",": ",", ";": ";", "\\": "\\"}
    output: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            escaped = value[index + 1]
            output.append(replacements.get(escaped, escaped))
            index += 2
        else:
            output.append(value[index])
            index += 1
    return html.unescape("".join(output)).strip()


def _property(line: str) -> tuple[str, dict[str, str], str] | None:
    if ":" not in line:
        return None
    left, value = line.split(":", 1)
    pieces = left.split(";")
    name = pieces[0].upper()
    params: dict[str, str] = {}
    for part in pieces[1:]:
        if "=" in part:
            key, item = part.split("=", 1)
            params[key.upper()] = item.strip('"')
    return name, params, value.strip()


def _parse_ical_datetime(value: str, params: dict[str, str], default_tz: ZoneInfo) -> datetime | None:
    try:
        if value.endswith("Z"):
            parsed = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            return parsed.astimezone(default_tz)
        tz = ZoneInfo(params.get("TZID", default_tz.key))
        if len(value) == 8:
            return datetime.strptime(value, "%Y%m%d").replace(tzinfo=tz)
        if len(value) == 15 and "T" in value:
            return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=tz)
    except (ValueError, KeyError):
        return None
    return None


def _clean_course_name(value: str) -> str:
    cleaned = re.sub(r"\s*\([^)]*\d+[^)]*\)\s*$", "", value).strip()
    return cleaned or value.strip() or "General"


def parse_ical(
    text: str,
    *,
    feed_id: str,
    feed_name: str,
    timezone_name: str = "Europe/Madrid",
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Parse future Moodle-style VEVENTs without retaining the feed URL."""
    default_tz = ZoneInfo(timezone_name)
    current = now or datetime.now(default_tz)
    unfolded = _unfold_ical(text)
    events: list[dict[str, Any]] = []

    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", unfolded, re.DOTALL | re.IGNORECASE):
        properties: dict[str, tuple[dict[str, str], str]] = {}
        for line in block.strip().splitlines():
            parsed = _property(line.strip())
            if parsed is not None:
                name, params, value = parsed
                properties[name] = (params, value)

        uid = properties.get("UID", ({}, ""))[1]
        if not uid:
            continue
        date_params, date_value = properties.get("DTSTART", properties.get("DUE", ({}, "")))
        due_at = _parse_ical_datetime(date_value, date_params, default_tz)
        if due_at is None or due_at < current - timedelta(hours=2):
            continue

        summary = _unescape_ical(properties.get("SUMMARY", ({}, "Sin título"))[1]) or "Sin título"
        categories = _unescape_ical(properties.get("CATEGORIES", ({}, ""))[1])
        description = _unescape_ical(properties.get("DESCRIPTION", ({}, ""))[1])
        events.append(
            {
                "uid": uid,
                "feed_id": feed_id,
                "feed_name": feed_name,
                "summary": summary,
                "course": _clean_course_name(categories),
                "due_at": due_at,
                "description": description,
            }
        )

    events.sort(key=lambda event: event["due_at"])
    return events


def update_alert_state(
    events: list[dict[str, Any]],
    state: dict[str, Any],
    *,
    now: datetime | None = None,
    reminder_days: tuple[int, ...] = (7, 3, 1),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Update per-user state and return initial, new, or due-soon alerts."""
    current = now or datetime.now(ZoneInfo("Europe/Madrid"))
    if not isinstance(state, dict):
        state = {}
    state.setdefault("initialized", False)
    if not isinstance(state.get("seen"), dict):
        state["seen"] = {}
    if not isinstance(state.get("notified"), dict):
        state["notified"] = {}
    seen: dict[str, Any] = state["seen"]
    notified: dict[str, Any] = state["notified"]

    def key_for(task: dict[str, Any]) -> str:
        return f"{task.get('feed_id', 'feed')}:{task['uid']}"

    def snapshot(task: dict[str, Any]) -> dict[str, str]:
        return {"summary": task["summary"], "due_at": task["due_at"].isoformat()}

    def crossed_thresholds(days_left: float) -> list[str]:
        return [f"{days}d" for days in reminder_days if days_left <= days]

    if not state["initialized"]:
        for task in events:
            key = key_for(task)
            seen[key] = snapshot(task)
            days_left = (task["due_at"] - current).total_seconds() / 86400
            notified[key] = crossed_thresholds(days_left)
        state["initialized"] = True
        return [{"kind": "initial", "tasks": list(events)}], state

    alerts: list[dict[str, Any]] = []
    for task in events:
        key = key_for(task)
        days_left = (task["due_at"] - current).total_seconds() / 86400
        current_snapshot = snapshot(task)
        previous = seen.get(key)

        if previous is None:
            seen[key] = current_snapshot
            notified[key] = crossed_thresholds(days_left)
            alerts.append({"kind": "new", "task": task})
            continue

        if previous != current_snapshot:
            seen[key] = current_snapshot
            notified[key] = crossed_thresholds(days_left)
            alerts.append({"kind": "updated", "task": task})
            continue

        sent = notified.get(key)
        if not isinstance(sent, list):
            sent = []
            notified[key] = sent
        threshold = None
        for days in sorted(reminder_days):
            label = f"{days}d"
            if days_left <= days and label not in sent:
                threshold = label
                break
        if threshold:
            alerts.append({"kind": "reminder", "threshold": threshold, "task": task})
            # A more urgent reminder replaces all less urgent thresholds.
            sent.extend(label for label in crossed_thresholds(days_left) if label not in sent)

    return alerts, state


class FeedFetchError(RuntimeError):
    """A calendar download failed; the private URL is intentionally hidden."""


def load_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError("Missing config file; copy config.example.json to config.json and fill it locally.") from None
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("Could not read config.json; check its JSON without sharing its contents.") from None

    if not isinstance(data, dict):
        raise ValueError("Configuration must be a JSON object.")
    timezone_name = data.get("timezone", "Europe/Madrid")
    if not isinstance(timezone_name, str):
        raise ValueError("Configured timezone is invalid.")
    try:
        ZoneInfo(timezone_name)
    except (KeyError, ValueError):
        raise ValueError("Configured timezone is not recognized.") from None

    feeds = data.get("feeds")
    if not isinstance(feeds, list) or not feeds:
        raise ValueError("Configuration must contain at least one calendar feed.")

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, feed in enumerate(feeds, start=1):
        if not isinstance(feed, dict):
            raise ValueError(f"Feed entry {index} must be an object.")
        feed_id = str(feed.get("id") or f"feed-{index}").strip()
        name = str(feed.get("name") or feed_id).strip()
        if not feed_id or feed_id in seen_ids:
            raise ValueError(f"Feed entry {index} has a missing or duplicate id.")
        seen_ids.add(feed_id)
        enabled = bool(feed.get("enabled", True))
        url = ""
        if enabled:
            try:
                url = validate_feed_url(feed.get("url", ""))
            except ValueError:
                raise ValueError(f"Feed entry {index} needs a valid HTTPS URL; its value was not logged.") from None
        normalized.append({"id": feed_id, "name": name, "url": url, "enabled": enabled})

    if not any(feed["enabled"] for feed in normalized):
        raise ValueError("At least one calendar feed must be enabled.")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return {"timezone": timezone_name, "feeds": normalized}


def fetch_ical_feed(
    feed: dict[str, Any], *, timezone_name: str, now: datetime | None = None
) -> list[dict[str, Any]]:
    """Download and parse a feed using urllib's normal certificate checks."""
    try:
        url = validate_feed_url(feed.get("url", ""))
        request = Request(url, headers={"User-Agent": "MuseCampusTasks/1.0"})
        with urlopen(request, timeout=20) as response:
            raw = response.read(5_000_001)
        if len(raw) > 5_000_000:
            raise ValueError("feed too large")
        text = raw.decode("utf-8", errors="replace")
    except Exception as exc:
        raise FeedFetchError(
            f"Could not retrieve an academic calendar ({type(exc).__name__}); its URL was withheld."
        ) from None
    return parse_ical(
        text,
        feed_id=feed["id"],
        feed_name=feed["name"],
        timezone_name=timezone_name,
        now=now,
    )


def collect_events(config: dict[str, Any], *, now: datetime | None = None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    failures = 0
    for feed in config["feeds"]:
        if not feed.get("enabled", True):
            continue
        try:
            events.extend(
                fetch_ical_feed(feed, timezone_name=config["timezone"], now=now)
            )
        except FeedFetchError:
            failures += 1
    if failures:
        raise FeedFetchError(
            f"{failures} academic feed(s) could not be updated; saved state was left unchanged."
        )
    events.sort(key=lambda event: event["due_at"])
    return events


_DAYS_ES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MONTHS_ES = (
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def format_due(due_at: datetime, timezone_name: str) -> str:
    local = due_at.astimezone(ZoneInfo(timezone_name))
    return (
        f"{_DAYS_ES[local.weekday()]}, {local.day} de {_MONTHS_ES[local.month]} "
        f"a las {local:%H:%M}"
    )


def format_tasks(tasks: list[dict[str, Any]], timezone_name: str, title: str) -> str:
    lines = [title]
    if not tasks:
        lines.append("No hay tareas o entregas pendientes en el feed.")
        return "\n".join(lines)
    for task in tasks:
        lines.append(
            f"• [{task['feed_name']} | {task['course']}] {task['summary']}"
        )
        lines.append(f"  Entrega: {format_due(task['due_at'], timezone_name)}")
    return "\n".join(lines)


def format_alerts(alerts: list[dict[str, Any]], *, timezone_name: str) -> str:
    output: list[str] = []
    for alert in alerts:
        kind = alert["kind"]
        if kind == "initial":
            output.append(
                format_tasks(alert["tasks"], timezone_name, "🎓 Seguimiento académico iniciado")
            )
            continue
        task = alert["task"]
        if kind == "new":
            heading = "🚨 Nueva tarea o aviso"
        elif kind == "updated":
            heading = "✏️ Ha cambiado una tarea o su fecha"
        else:
            threshold = alert.get("threshold")
            heading = {
                "1d": "🚨 Entrega en 24 horas o menos",
                "3d": "⏳ Entrega en 3 días o menos",
                "7d": "📌 Entrega en 7 días o menos",
            }.get(threshold, "📌 Recordatorio académico")
        output.append(
            f"{heading}\n[{task['feed_name']} | {task['course']}] {task['summary']}\n"
            f"Entrega: {format_due(task['due_at'], timezone_name)}"
        )
    return "\n\n".join(output)


def load_state(state_path: str | Path) -> dict[str, Any]:
    path = Path(state_path)
    if not path.exists():
        return {}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("Could not read local state; remove the state file to initialize it again.") from None
    if not isinstance(state, dict):
        raise ValueError("Local state is invalid; remove the state file to initialize it again.")
    return state


def save_state(state_path: str | Path, state: dict[str, Any]) -> None:
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(path)


def _json_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "feed": event["feed_name"],
            "course": event["course"],
            "summary": event["summary"],
            "due_at": event["due_at"].isoformat(),
        }
        for event in events
    ]


def main(argv: list[str] | None = None) -> int:
    default_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Lista o vigila tareas de feeds iCalendar académicos."
    )
    parser.add_argument("--config", default=str(default_dir / "config.json"))
    parser.add_argument("--state", default=str(default_dir / "campus_tasks_state.json"))
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Comprueba y emite solo novedades/avisos (predeterminado).")
    modes.add_argument("--list", dest="list_mode", action="store_true", help="Lista todas las tareas futuras.")
    modes.add_argument("--json", dest="json_mode", action="store_true", help="Imprime tareas como JSON sin enlaces de feed.")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        events = collect_events(config)
    except (FeedFetchError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json_mode:
        print(json.dumps(_json_events(events), ensure_ascii=False, indent=2))
        return 0
    if args.list_mode:
        print(format_tasks(events, config["timezone"], "📋 Tareas y entregas pendientes"))
        return 0

    try:
        state = load_state(args.state)
        alerts, state = update_alert_state(events, state)
        save_state(args.state, state)
    except (OSError, ValueError, TypeError) as exc:
        print(f"Error de estado local: {exc}", file=sys.stderr)
        return 2
    if alerts:
        print(format_alerts(alerts, timezone_name=config["timezone"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
