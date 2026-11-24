"""Check the handoff formats using committed, synthetic telemetry."""

import ipaddress
import json
import unittest
import uuid
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1] / "modules" / "pipeline"


def records(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


class TelemetryFixturesTest(unittest.TestCase):
    def test_fixture_formats(self):
        for filename, required in {
            "cowrie.json.sample": {"eventid", "src_ip", "session", "timestamp"},
            "opencanary.log.sample": {"logtype", "src_host", "utc_time", "logdata"},
            "web.jsonl.sample": {"event_id", "@timestamp", "src_ip", "service", "event_type"},
        }.items():
            with self.subTest(filename=filename):
                events = records(PIPELINE / "samples" / filename)
                self.assertTrue(events)
                for event in events:
                    self.assertIsInstance(event, dict)
                    self.assertFalse(required - event.keys(), event.keys())

    def test_web_fixture_matches_index_identity_fields(self):
        mapping_path = PIPELINE / "opensearch" / "index_template.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        fields = mapping["template"]["mappings"]["properties"]
        expected = {"@timestamp": "date", "event_id": "keyword", "src_ip": "ip"}
        for field, field_type in expected.items():
            self.assertEqual(fields[field]["type"], field_type)

        events = records(PIPELINE / "samples" / "web.jsonl.sample")
        identifiers = set()
        for event in events:
            identifier = uuid.UUID(event["event_id"])
            self.assertEqual(identifier.version, 4)
            self.assertNotIn(identifier, identifiers)
            identifiers.add(identifier)
            ipaddress.ip_address(event["src_ip"])
            self.assertEqual(event["honeypot"], "web")
