"""Check the public entry (scripts/) without Docker: modes, env examples, binds, preflight, down."""

import os
import re
import shutil
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("ssh-honeypot", "web-honeypot", "pipeline")
LOOPBACK_DEFAULTS = ("127.0.0.1:", "${HP_BIND_ADDR:-127.0.0.1}:")
# Únicos subcomandos de docker que preflight puede usar: todos de lectura.
READ_ONLY = ("compose version", "info", "network inspect", "volume inspect", "ps ")
FAKE_DOCKER = r"""#!/usr/bin/env bash
echo "$*" >> "$FAKE_DOCKER_LOG"
case "$*" in
  *" inspect -f "*IPAM*) echo "172.30.0.0/24 " ;;
  *" inspect -f "*) [ "$FAKE_DOCKER_SHARED" = labeled ] && echo '{"io.winnie.project":"winnie-the-root"}' || echo '{}' ;;
  *" inspect "*) [ "$FAKE_DOCKER_SHARED" = absent ] && exit 1 ;;
  ps*) printf '%s\n' $FAKE_DOCKER_PS ;;
  compose*" down"*) [ "$FAKE_DOCKER_FAIL" = down ] && { echo "boom: daemon error" >&2; exit 1; } ;;
esac
exit 0
"""


def free_port(port: int) -> bool:
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


class PublicEntryFilesTest(unittest.TestCase):
    def test_shell_scripts_are_executable_in_git(self):
        out = subprocess.run(["git", "ls-files", "-s", "--", "scripts", "modules"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        for line in out.splitlines():
            mode, path = line.split()[0], line.split("\t")[1]
            if path.endswith(".sh") and not path.startswith("scripts/lib/"):
                with self.subTest(path=path):
                    self.assertEqual(mode, "100755")

    def test_help_runs_without_chmod_or_interpreter(self):
        for script in ("up.sh", "down.sh", "preflight.sh"):
            with self.subTest(script=script):
                r = subprocess.run([str(ROOT / "scripts" / script), "--help"], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn(script, r.stdout)

    def test_referenced_env_examples_exist(self):
        docs = [ROOT / "README.md", ROOT / "docs" / "RUN.md", *ROOT.glob("modules/*/README.md")]
        referenced = {m for d in docs for m in re.findall(r"modules/[\w-]+/\.env\.example", d.read_text())}
        referenced |= {f"modules/{m}/.env.example" for m in MODULES}
        for path in sorted(referenced):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())

    def test_env_examples_hold_no_secrets_and_cover_compose(self):
        for module in MODULES:
            example = (ROOT / "modules" / module / ".env.example").read_text()
            values = dict(re.findall(r"^([A-Z_]+)=(.*)$", example, re.M))
            for name, value in values.items():
                if re.search(r"PASS|KEY|TOKEN|SECRET", name):
                    with self.subTest(module=module, secret=name):
                        self.assertEqual(value, "")
            compose = "".join(p.read_text() for p in (ROOT / "modules" / module).glob("compose*.yml"))
            for name in set(re.findall(r"\$\{([A-Z_]+)", compose)):
                with self.subTest(module=module, variable=name):
                    self.assertIn(name, values)

    def test_published_ports_default_to_loopback_and_match_contract(self):
        compose_ports = set()
        for path in ROOT.glob("modules/*/compose*.yml"):
            for spec in re.findall(r'^\s+- "([^"]*:\d+)"', path.read_text(), re.M):
                with self.subTest(file=path.name, port=spec):
                    self.assertTrue(spec.startswith(LOOPBACK_DEFAULTS))
                    self.assertNotIn(":9200", spec)
                resolved = spec.replace("${HP_BIND_ADDR:-127.0.0.1}", "127.0.0.1")
                resolved = resolved.replace("${WEB_HOST_PORT:-8080}", "8080")
                addr, host_port, _ = resolved.split(":")
                compose_ports.add((addr, host_port))
        env = {k: v for k, v in os.environ.items() if k not in ("HP_BIND_ADDR", "WEB_HOST_PORT")}
        out = subprocess.run(["bash", "-c", f'ROOT=/nonexistent; . "{ROOT}/scripts/lib/contract.sh"; '
                              "published_ports full"], env=env, capture_output=True, text=True, check=True)
        contract = {tuple(line.split()[1:3]) for line in out.stdout.splitlines()}
        self.assertEqual(contract, compose_ports)


class ScriptsWithFakeDockerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "docker").write_text(FAKE_DOCKER)
        (self.bin / "docker").chmod(0o755)
        self.log = self.tmp / "docker.log"
        self.log.touch()
        (self.tmp / "max_map_count").write_text("262144\n")
        self.env = {
            **{k: v for k, v in os.environ.items() if k not in ("HP_BIND_ADDR", "WEB_HOST_PORT", "SECURITY_MODE")},
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "FAKE_DOCKER_LOG": str(self.log), "FAKE_DOCKER_SHARED": "absent", "FAKE_DOCKER_PS": "",
            "FAKE_DOCKER_FAIL": "", "MAX_MAP_COUNT_FILE": str(self.tmp / "max_map_count"),
        }
        self.git_status = self.status()

    def status(self):
        return subprocess.run(["git", "status", "--porcelain", "--ignored"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout

    def run_script(self, *args, **env):
        return subprocess.run([str(ROOT / "scripts" / args[0]), *args[1:]], capture_output=True, text=True,
                              env={**self.env, **env})

    def docker_calls(self):
        return self.log.read_text().splitlines()

    def assert_host_untouched(self):
        for call in self.docker_calls():
            self.assertTrue(call.startswith(READ_ONLY), call)
        self.assertEqual(self.status(), self.git_status)

    def hold_port(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen()
        self.addCleanup(s.close)
        return s.getsockname()[1]

    def test_preflight_passes_and_prints_effective_config(self):
        if not free_port(5601):
            self.skipTest("5601 ocupado en este host")
        r = self.run_script("preflight.sh", "synthetic")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("dashboards 127.0.0.1:5601 libre", r.stdout)
        self.assertIn("SECURITY_MODE=dev", r.stdout)
        self.assertIn("9200: solo red interna", r.stdout)
        self.assert_host_untouched()

    def test_preflight_fails_on_occupied_port(self):
        port = self.hold_port()
        r = self.run_script("preflight.sh", "full", WEB_HOST_PORT=str(port))
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"[FALLO] web 127.0.0.1:{port} ocupado", r.stdout)
        self.assertIn("No se ha modificado nada", r.stdout)
        self.assert_host_untouched()

    def test_preflight_accepts_port_already_published_by_this_project(self):
        port = self.hold_port()
        r = self.run_script("preflight.sh", "full", WEB_HOST_PORT=str(port), FAKE_DOCKER_PS="hp-web")
        self.assertIn(f"web 127.0.0.1:{port} ya publicado por hp-web", r.stdout)

    def test_preflight_fails_on_missing_dependency(self):
        tools = self.tmp / "tools"
        tools.mkdir()
        for name in ("bash", "dirname", "sed", "cat", "uname", "grep", "tail", "cut", "python3"):
            (tools / name).symlink_to(shutil.which(name))
        (tools / "docker").symlink_to(self.bin / "docker")
        r = self.run_script("preflight.sh", "synthetic", PATH=str(tools))
        self.assertEqual(r.returncode, 1)
        self.assertIn("[FALLO] falta 'curl'", r.stdout)
        self.assert_host_untouched()

    def test_preflight_fails_on_low_max_map_count_and_prod_without_password(self):
        (self.tmp / "max_map_count").write_text("65530\n")
        r = self.run_script("preflight.sh", "synthetic", SECURITY_MODE="prod", OPENSEARCH_ADMIN_PASSWORD="")
        self.assertEqual(r.returncode, 1)
        self.assertIn("vm.max_map_count=65530", r.stdout)
        self.assertIn("SECURITY_MODE=prod exige OPENSEARCH_ADMIN_PASSWORD", r.stdout)

    def test_up_stops_before_changing_anything_when_preflight_fails(self):
        port = self.hold_port()
        r = self.run_script("up.sh", "full", WEB_HOST_PORT=str(port))
        self.assertNotEqual(r.returncode, 0)
        self.assert_host_untouched()

    def test_down_reports_real_errors(self):
        r = self.run_script("down.sh", "synthetic", FAKE_DOCKER_FAIL="down")
        self.assertEqual(r.returncode, 1)
        self.assertIn("boom: daemon error", r.stderr)
        self.assertNotIn("Datos conservados", r.stdout)

    def test_down_synthetic_only_touches_the_pipeline(self):
        r = self.run_script("down.sh", "synthetic", "--purge", FAKE_DOCKER_SHARED="labeled")
        self.assertEqual(r.returncode, 0, r.stderr)
        mutating = [c for c in self.docker_calls() if not c.startswith(READ_ONLY)]
        self.assertEqual(mutating, ["compose -f compose.yml -f compose.dev.yml down -v"])

    def test_purge_removes_shared_resources_only_with_project_label(self):
        for shared, removed in (("labeled", True), ("unlabeled", False)):
            with self.subTest(shared=shared):
                self.log.write_text("")
                r = self.run_script("down.sh", "full", "--purge", FAKE_DOCKER_SHARED=shared)
                self.assertEqual(r.returncode, 0, r.stderr)
                calls = self.docker_calls()
                for vol in ("honeylogs-cowrie", "honeylogs-opencanary", "honeylogs-web"):
                    self.assertEqual(f"volume rm {vol}" in calls, removed)
                self.assertNotIn("volume rm honeylogs", calls)   # el legado nunca se borra
                self.assertEqual("network rm honeynet" in calls, removed)
                self.assertEqual(sum(c.endswith("down -v") for c in calls), 3)


if __name__ == "__main__":
    unittest.main()
