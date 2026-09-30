import unittest
import io
import json
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from campus_tasks import (
    FeedFetchError,
    fetch_ical_feed,
    format_alerts,
    load_config,
    main,
    parse_ical,
    update_alert_state,
    validate_feed_url,
)


TZ = ZoneInfo("Europe/Madrid")
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=TZ)


class FeedURLTests(unittest.TestCase):
    def test_requires_https_without_echoing_private_query(self):
        url = "http://campus.example/feed.ics?marker=secret-query-value"

        with self.assertRaises(ValueError) as raised:
            validate_feed_url(url)

        self.assertNotIn("secret-query-value", str(raised.exception))
        self.assertNotIn("marker=", str(raised.exception))

    def test_accepts_https_feed_url(self):
        url = "https://campus.example/feed.ics"
        self.assertEqual(validate_feed_url(url), url)


class ConfigAndFetchTests(unittest.TestCase):
    def test_invalid_private_feed_url_is_not_echoed_from_config_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "timezone": "Europe/Madrid",
                        "feeds": [
                            {
                                "id": "campus",
                                "name": "Campus",
                                "url": "http://campus.example/feed?marker=private-sentinel",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError) as raised:
                load_config(path)

        self.assertNotIn("private-sentinel", str(raised.exception))

    def test_loaded_config_file_is_restricted_to_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "timezone": "Europe/Madrid",
                        "feeds": [
                            {
                                "id": "campus",
                                "name": "Campus",
                                "url": "https://campus.example/feed.ics",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(path)

            self.assertEqual(config["feeds"][0]["name"], "Campus")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_fetch_error_hides_feed_url(self):
        feed = {
            "id": "campus",
            "name": "Campus",
            "url": "https://campus.example/feed?marker=private-sentinel",
        }
        with patch("campus_tasks.urlopen", side_effect=OSError(feed["url"])):
            with self.assertRaises(FeedFetchError) as raised:
                fetch_ical_feed(
                    feed,
                    timezone_name="Europe/Madrid",
                    now=NOW,
                )

        self.assertNotIn("private-sentinel", str(raised.exception))
        self.assertNotIn("campus.example", str(raised.exception))

    def test_alert_text_contains_task_not_feed_url(self):
        task = {
            "uid": "task-1",
            "feed_id": "uva",
            "feed_name": "UVA",
            "summary": "Entrega de prueba",
            "course": "Asignatura",
            "due_at": NOW + timedelta(days=2),
            "description": "",
        }

        text = format_alerts(
            [{"kind": "new", "task": task}], timezone_name="Europe/Madrid"
        )
        self.assertIn("Nueva tarea", text)
        self.assertIn("Entrega de prueba", text)
        self.assertNotIn(".ics", text)


class CliIntegrationTests(unittest.TestCase):
    ical = (
        b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\n"
        b"UID:integration-task\r\n"
        b"DTSTART;TZID=Europe/Madrid:20990101T150000\r\n"
        b"SUMMARY:Entrega de integracion\r\n"
        b"CATEGORIES:Proyecto\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
    )

    def prepare_files(self, directory):
        config_path = Path(directory) / "config.json"
        state_path = Path(directory) / "state.json"
        config_path.write_text(
            json.dumps(
                {
                    "timezone": "Europe/Madrid",
                    "feeds": [
                        {
                            "id": "uva",
                            "name": "Universidad",
                            "url": "https://campus.example/feed.ics?marker=feed-token-sentinel",
                            "enabled": True,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return config_path, state_path

    def test_check_persists_initial_state_then_emits_nothing_on_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path, state_path = self.prepare_files(directory)
            args = ["--check", "--config", str(config_path), "--state", str(state_path)]

            with patch("campus_tasks.urlopen", return_value=FakeResponse(self.ical)):
                first_output = io.StringIO()
                with redirect_stdout(first_output):
                    self.assertEqual(main(args), 0)
                self.assertIn("Seguimiento académico iniciado", first_output.getvalue())
                self.assertTrue(state_path.exists())

                second_output = io.StringIO()
                with redirect_stdout(second_output):
                    self.assertEqual(main(args), 0)

            self.assertEqual(second_output.getvalue(), "")
            self.assertNotIn("feed-token-sentinel", first_output.getvalue())
            self.assertEqual(state_path.stat().st_mode & 0o777, 0o600)

    def test_fetch_failure_keeps_state_and_hides_private_url(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path, state_path = self.prepare_files(directory)
            original_state = '{"keep": "unchanged"}\n'
            state_path.write_text(original_state, encoding="utf-8")
            stderr = io.StringIO()

            with patch(
                "campus_tasks.urlopen",
                side_effect=OSError("https://campus.example/feed.ics?marker=feed-token-sentinel"),
            ):
                with redirect_stderr(stderr):
                    result = main(
                        ["--check", "--config", str(config_path), "--state", str(state_path)]
                    )

            self.assertEqual(result, 2)
            self.assertEqual(state_path.read_text(encoding="utf-8"), original_state)
            self.assertNotIn("feed-token-sentinel", stderr.getvalue())
            self.assertNotIn("campus.example", stderr.getvalue())

    def test_json_output_omits_private_feed_url(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path, state_path = self.prepare_files(directory)
            output = io.StringIO()

            with patch("campus_tasks.urlopen", return_value=FakeResponse(self.ical)):
                with redirect_stdout(output):
                    result = main(
                        ["--json", "--config", str(config_path), "--state", str(state_path)]
                    )

            self.assertEqual(result, 0)
            self.assertIn("Entrega de integracion", output.getvalue())
            self.assertNotIn("feed-token-sentinel", output.getvalue())
            self.assertNotIn("campus.example", output.getvalue())


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit=-1):
        return self.body[:limit]


class AlertStateTests(unittest.TestCase):
    def make_task(self, due_at):
        return {
            "uid": "task-1",
            "feed_id": "uva",
            "feed_name": "UVA",
            "summary": "Entrega de prueba",
            "course": "Asignatura",
            "due_at": due_at,
            "description": "",
        }

    def test_first_run_initializes_once_then_stays_quiet(self):
        task = self.make_task(NOW + timedelta(days=10))

        alerts, state = update_alert_state([task], {}, now=NOW)
        self.assertEqual(["initial"], [alert["kind"] for alert in alerts])
        self.assertTrue(state["initialized"])

        alerts, state = update_alert_state([task], state, now=NOW)
        self.assertEqual([], alerts)

    def test_new_task_and_deadline_thresholds_are_not_repeated(self):
        task = self.make_task(NOW + timedelta(days=6))
        state = {"initialized": True, "seen": {}, "notified": {}}

        alerts, state = update_alert_state([task], state, now=NOW)
        self.assertEqual(["new"], [alert["kind"] for alert in alerts])

        alerts, state = update_alert_state([task], state, now=NOW)
        self.assertEqual([], alerts)

        alerts, state = update_alert_state(
            [task], state, now=NOW + timedelta(days=4)
        )
        self.assertEqual(["3d"], [alert.get("threshold") for alert in alerts])

        urgent_time = NOW + timedelta(days=5, hours=12)
        alerts, state = update_alert_state([task], state, now=urgent_time)
        self.assertEqual(["1d"], [alert.get("threshold") for alert in alerts])

        alerts, state = update_alert_state([task], state, now=urgent_time)
        self.assertEqual([], alerts)


class ICalParsingTests(unittest.TestCase):
    def test_parses_folded_escaped_event_and_ignores_old_deadline(self):
        ical = r"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:assignment-1
DTSTART;TZID=Europe/Madrid:20261007T150000
SUMMARY:Entrega\, práctica
CATEGORIES:Programación (META12-2026)
DESCRIPTION:Primera\\nlínea con detalle y
 continuación del texto
END:VEVENT
BEGIN:VEVENT
UID:old-assignment
DTSTART;TZID=Europe/Madrid:20260920T150000
SUMMARY:Ya vencida
CATEGORIES:Programación
END:VEVENT
END:VCALENDAR
"""
        tasks = parse_ical(
            ical,
            feed_id="uva",
            feed_name="UVA",
            timezone_name="Europe/Madrid",
            now=NOW,
        )

        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task["uid"], "assignment-1")
        self.assertEqual(task["feed_id"], "uva")
        self.assertEqual(task["feed_name"], "UVA")
        self.assertEqual(task["summary"], "Entrega, práctica")
        self.assertEqual(task["course"], "Programación")
        self.assertEqual(task["due_at"], datetime(2026, 10, 7, 15, 0, tzinfo=TZ))
        self.assertEqual(
            task["description"],
            "Primera\\nlínea con detalle ycontinuación del texto",
        )


if __name__ == "__main__":
    unittest.main()
