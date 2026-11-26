"""Integrity and retention rules for lab captures (scripts/evidence.py), without Docker."""

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("evidence", ROOT / "scripts/evidence.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

SHA_A, SHA_B = "a" * 64, "b" * 64
DAY = 86400


def rec(store, path, sha, mtime=0, mode="640"):
    return {f"{store}:{path}": {"store": store, "path": path, "sha256": sha, "size": 1, "mtime": mtime, "mode": mode}}


def issues(current, previous, deleted=(), active=()):
    return [i["issue"] for i in ev.check(current, previous, set(deleted), set(active))[0]]


class ListingTest(unittest.TestCase):
    def test_hex_paths_survive_intruder_names(self):
        name = "evil name\n.sh"
        line = f"{name.encode().hex()} 5 100 640 {SHA_A}"
        files = ev.parse_listing("web-uploads", line + "\nbroken line\n", ["*"])
        self.assertEqual([r["path"] for r in files.values()], [name])

    def test_only_evidence_globs_are_listed(self):
        lines = "\n".join(f"{p.encode().hex()} 1 1 600 {SHA_A}" for p in
                          ("lib/cowrie/ssh_host_ed25519_key", f"lib/cowrie/tty/{SHA_A}", "log/cowrie/cowrie.log.2026-11-01"))
        globs = ev.PRIVATE_STORES["cowrie-data"][1]
        self.assertEqual(sorted(r["path"] for r in ev.parse_listing("cowrie-data", lines, globs).values()),
                         [f"lib/cowrie/tty/{SHA_A}", "log/cowrie/cowrie.log.2026-11-01"])


class IntegrityTest(unittest.TestCase):
    def test_changed_closed_capture_is_an_issue(self):
        self.assertEqual(issues(rec("cowrie", "cowrie.json.2026-11-01", SHA_B), rec("cowrie", "cowrie.json.2026-11-01", SHA_A)),
                         ["closed capture changed"])

    def test_live_log_may_grow(self):
        self.assertEqual(issues(rec("cowrie", "cowrie.json", SHA_B), rec("cowrie", "cowrie.json", SHA_A),
                                active={"cowrie:cowrie.json"}), [])

    def test_missing_needs_a_recorded_deletion(self):
        old = rec("cowrie", "cowrie.json.2026-08-01", SHA_A)
        self.assertEqual(issues({}, old), ["missing without a recorded deletion"])
        self.assertEqual(issues({}, old, deleted={"cowrie:cowrie.json.2026-08-01"}), [])

    def test_numbered_rotation_is_followed_by_content(self):
        old = {**rec("opencanary", "opencanary.log.1", SHA_A), **rec("opencanary", "opencanary.log.5", SHA_B)}
        now = {**rec("opencanary", "opencanary.log.1", "c" * 64), **rec("opencanary", "opencanary.log.2", SHA_A)}
        result = ev.check(now, old, set(), set())
        self.assertEqual(result[0], [])
        self.assertEqual([n["key"] for n in result[1]], ["opencanary:opencanary.log.5"])

    def test_open_tty_is_not_compared_and_closed_one_must_match_its_name(self):
        old = rec("cowrie-data", "lib/cowrie/tty/20261126-abc.log", SHA_A)
        self.assertEqual(issues(rec("cowrie-data", f"lib/cowrie/tty/{SHA_B}", SHA_B), old), [])
        self.assertEqual(issues(rec("cowrie-data", f"lib/cowrie/downloads/{SHA_A}", SHA_B), {}),
                         ["content does not match its sha256 name"])

    def test_executable_capture_is_an_issue(self):
        self.assertEqual(issues(rec("web-uploads", "f00", SHA_A, mode="750"), {}), ["executable"])


class RetentionTest(unittest.TestCase):
    NOW = 1000 * DAY

    def test_expires_after_ttl_except_live_open_and_held(self):
        current = {**rec("cowrie", "cowrie.json.old", SHA_A, mtime=self.NOW - 91 * DAY),
                   **rec("cowrie", "cowrie.json.new", SHA_A, mtime=self.NOW - 89 * DAY),
                   **rec("cowrie", "cowrie.json", SHA_A, mtime=self.NOW - 200 * DAY),
                   **rec("cowrie-data", "lib/cowrie/tty/open.log", SHA_A, mtime=self.NOW - 200 * DAY),
                   **rec("web-uploads", "case42-file", SHA_A, mtime=self.NOW - 200 * DAY)}
        holds = ev.parse_holds("# caso 42, investigación abierta\nweb-uploads case42-*  # hasta revisión\n")
        self.assertEqual(ev.expired(current, self.NOW, 90, holds, {"cowrie:cowrie.json"}), ["cowrie:cowrie.json.old"])

    def test_default_ttl_is_90_days(self):
        self.assertEqual(ev.TTL_DAYS, 90)


class NoDuplicateCopiesTest(unittest.TestCase):
    def test_opencanary_does_not_copy_events_to_stdout(self):
        conf = json.loads((ROOT / "modules/ssh-honeypot/opencanary/opencanary.conf").read_text())
        handlers = conf["logger"]["kwargs"]["handlers"]
        self.assertEqual(list(handlers), ["file"])


if __name__ == "__main__":
    unittest.main()
