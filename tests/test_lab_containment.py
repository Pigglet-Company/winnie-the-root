"""W04 without Docker: one log volume per producer, read-only collector, no reopened permissions,
distinct UIDs and fictitious identities in the academic capture mode."""

import ipaddress
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCERS = {   # servicio: (fuente, compose del módulo)
    "hp-cowrie": ("cowrie", "modules/ssh-honeypot/compose.yml"),
    "hp-opencanary": ("opencanary", "modules/ssh-honeypot/compose.yml"),
    "hp-web": ("web", "modules/web-honeypot/compose.yml"),
}
RESERVED_TLDS = {"local", "example", "test", "invalid", "localhost"}
DECOY_DIRS = ("modules/web-honeypot/app", "modules/ssh-honeypot/cowrie", "modules/ssh-honeypot/opencanary")


def contract():
    out = subprocess.run(["bash", "-c", f'. "{ROOT}/scripts/lib/contract.sh"; echo "$SOURCE_VOLUMES"; echo "$READER_GID"'],
                         capture_output=True, text=True, check=True).stdout.split("\n")
    specs = {s.split(":")[0]: s.split(":")[1:] for s in out[0].split()}
    return {src: (vol, int(uid), int(quota)) for src, (vol, uid, quota) in specs.items()}, int(out[1])


def service_block(compose: str, name: str) -> str:
    text = (ROOT / compose).read_text()
    start = text.index(f"\n  {name}:\n")
    nxt = re.search(r"\n  [\w-]+:\n|\n\S", text[start + 1:])
    return text[start: start + 1 + nxt.start()] if nxt else text[start:]


def decoy_files():
    for d in DECOY_DIRS:
        for p in (ROOT / d).rglob("*"):
            if p.is_file() and p.suffix in {".py", ".txt", ".cfg", ".conf", ""} and "__pycache__" not in p.parts:
                yield p


class VolumesAndPermissionsTest(unittest.TestCase):
    def test_each_producer_mounts_only_its_own_log_volume(self):
        sources, _ = contract()
        for svc, (src, compose) in PRODUCERS.items():
            with self.subTest(service=svc):
                mounts = re.findall(r"^\s+- (honeylogs[\w-]*):(\S+)", service_block(compose, svc), re.M)
                self.assertEqual(mounts, [(sources[src][0], f"/logs/{src}")])

    def test_collector_reads_every_source_read_only(self):
        sources, _ = contract()
        block = service_block("modules/pipeline/compose.yml", "pl-vector")
        mounts = re.findall(r"^\s+- (honeylogs[\w-]*):(\S+)", block, re.M)
        self.assertEqual(sorted(mounts), sorted((v, f"/logs/{s}:ro") for s, (v, _, _) in sources.items()))
        dev = (ROOT / "modules/pipeline/compose.dev.yml").read_text()
        self.assertEqual(sorted(re.findall(r":(/logs/\w+):ro", dev)), sorted(f"/logs/{s}" for s in sources))

    def test_no_compose_mounts_the_legacy_volume(self):
        for path in ROOT.glob("modules/*/compose*.yml"):
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertIsNone(re.search(r"^\s+(- )?honeylogs:", path.read_text(), re.M))

    def test_init_never_reopens_permissions(self):
        init = (ROOT / "scripts/init.sh").read_text()
        self.assertNotRegex(init, r"0?777|a\+rwX|o\+w")
        self.assertIn("chmod 2750", init)

    def test_producer_uids_are_distinct_and_match_images(self):
        sources, reader = contract()
        uids = [uid for _, uid, _ in sources.values()]
        self.assertEqual(len(set(uids + [reader])), len(uids) + 1)
        self.assertIn(f'user: "{sources["web"][1]}:', service_block("modules/web-honeypot/compose.yml", "hp-web"))
        canary = (ROOT / "modules/ssh-honeypot/opencanary/Dockerfile").read_text()
        self.assertIn(f"USER {sources['opencanary'][1]}:", canary)
        self.assertIn(f'user: "{reader}:{reader}"', service_block("modules/pipeline/compose.yml", "pl-vector"))
        # Cowrie: la imagen fijada corre como 999:999 (passwd de cowrie/cowrie:2.9.0).
        self.assertEqual(sources["cowrie"][1], 999)
        self.assertIn("cowrie/cowrie:2.9.0@sha256:", service_block("modules/ssh-honeypot/compose.yml", "hp-cowrie"))

    def test_docker_stdout_copies_are_bounded(self):
        for compose in ("modules/ssh-honeypot/compose.yml", "modules/web-honeypot/compose.yml"):
            with self.subTest(file=compose):
                self.assertRegex((ROOT / compose).read_text(), r'max-size: "10m", max-file: "3"')


class FictitiousIdentitiesTest(unittest.TestCase):
    def test_decoy_mail_domains_are_reserved(self):
        for p in decoy_files():
            for domain in re.findall(r"[\w.+-]+@([a-z0-9-]+(?:\.[a-z0-9-]+)+)", p.read_text(errors="ignore")):
                with self.subTest(file=str(p.relative_to(ROOT)), domain=domain):
                    self.assertIn(domain.rsplit(".", 1)[1], RESERVED_TLDS)

    def test_decoy_addresses_are_private_or_documentation(self):
        for p in decoy_files():
            for literal in set(re.findall(r"(?<![\w.])\d{1,3}(?:\.\d{1,3}){3}(?![\w.])", p.read_text(errors="ignore"))):
                try:
                    ip = ipaddress.ip_address(literal)
                except ValueError:
                    continue
                with self.subTest(file=str(p.relative_to(ROOT)), ip=literal):
                    self.assertTrue(ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_unspecified)

    def test_cowrie_accounts_are_generic(self):
        generic = {"root", "admin", "ubuntu", "pi", "user", "test", "oracle", "postgres"}
        users = {line.split(":")[0] for line in (ROOT / "modules/ssh-honeypot/cowrie/userdb.txt").read_text().splitlines()
                 if line and not line.startswith("#")}
        self.assertLessEqual(users, generic)


if __name__ == "__main__":
    unittest.main()
