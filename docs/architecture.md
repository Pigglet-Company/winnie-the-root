# Architecture and data flow

Winnie separates telemetry production from ingestion. The modules are parts of one system, so human documentation lives under the root `docs/` directory.

```text
Cowrie       ─┐  native JSON lines
OpenCanary   ─┼─ honeylogs-* volumes ── Vector ── OpenSearch ── Dashboards
FastAPI web  ─┘  Winnie JSON lines     │
                                        └─ malformed input → dead-letter files
```

The producers write to `/logs/cowrie/cowrie.json*`, `/logs/opencanary/opencanary.log*`, and `/logs/web/web.jsonl*`. Each producer writes only to its own volume (`honeylogs-cowrie`, `honeylogs-opencanary`, `honeylogs-web`); Vector mounts all three read-only, tails those paths, applies per-producer normalization and shared classification, then optionally adds GeoIP. OpenSearch stores daily indices behind the `honeypot-events` alias. Treat classifications as rule matches and verify consequential findings against the original events.

The decoys attach to an external `honeynet` Docker network. The network must support the fixed Cowrie and OpenCanary addresses in their Compose file. Pipeline services use separate networks. Dashboards publishes on loopback, while sensor port bindings require operator review. Web uploads and Cowrie session material live on separate volumes. Files and events can contain untrusted or sensitive content.

## First run

Use the [synthetic pipeline procedure](modules/pipeline/guide.md#1-modo-dev-con-datos-sintéticos-sin-módulos-a-y-b) to exercise ingestion without running decoys. Check the Docker Compose v2 and Linux host prerequisites in that guide.

`scripts/init.sh` creates the isolated `honeynet` (no inter-container traffic, no IPv6) and one volume per source owned by its producer, readable only by Vector's group. The egress policy must be applied before the listeners start. Volumes, copies, egress and migration are described in [lab containment](lab-containment.md). The [architecture review](architecture-review.md) records why the existing VPS script is unsuitable as the first verification path.

## Reference

- [SSH integration notes](modules/ssh-honeypot/integration-notes.md)
- [Web integration notes](modules/web-honeypot/integration-notes.md)
- [Pipeline integration notes](modules/pipeline/integration-notes.md) and [fixture guide](modules/pipeline/samples.md)
