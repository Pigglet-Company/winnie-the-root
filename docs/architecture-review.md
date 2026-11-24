# Architecture and maintainability review

Winnie has useful components, but the repository fails as an integrated deliverable. A clean checkout gives an operator three Compose projects and no reliable procedure that starts all of them, proves the handoff, and makes failure visible. The most urgent work is at that boundary. More simulated routes or dashboard panels would add maintenance cost before the deployment and data contracts are dependable.

## Findings

| Priority | Finding | Evidence and consequence |
| --- | --- | --- |
| Critical before live deployment | The bootstrap contract exists only in comments and prose. | The sensor Compose files require external resources. [VPS setup](../modules/ssh-honeypot/deploy/setup.sh) calls the absent root `scripts/init.sh` and copies an absent module `.env.example`. The same script installs packages, edits SSH, and applies firewall configuration. Verify deployment and rollback on a disposable host before any real use. |
| Critical before live deployment | The pipeline's `prod` profile falls short of a production access model. | [Compose](../modules/pipeline/compose.yml) gives Vector admin credentials. [Setup](../modules/pipeline/opensearch/setup.sh) uses curl with certificate verification disabled and tolerates failures while removing demo users. Use authenticated TLS, service-specific roles, and verifiable setup outcomes before collecting live traffic. |
| High | Sensitive telemetry is copied through several layers without a repository-wide data policy. | [Web event construction](../modules/web-honeypot/app/events.py) preserves request body excerpts and authentication passwords. The pipeline guide describes password and payload visualizations. Decide which fields may be collected, who may read them, and how raw logs, indexed documents, exports, and artifacts expire. Index retention covers only one copy. |
| High | The schema is an agreement among implementations, without a versioned source of truth. | The [web test schema](../modules/web-honeypot/tests/schema.py), [Vector rules](../modules/pipeline/vector/rules), [index template](../modules/pipeline/opensearch/index_template.json), and dashboard objects describe overlapping parts of the contract. A rename or type change can pass one module and disappear in another. Publish a common, versioned contract and test producer fixtures against the normalized output and index mapping. |
| High | Evidence about delivery stops short of what an operator needs. | The [pipeline notes](modules/pipeline/integration-notes.md) distinguish normalization errors from OpenSearch document rejections, which are logged separately. There is no repository-wide signal for dropped, rejected, or stale telemetry. Track these separately and use an end-to-end synthetic event to detect when a source stops reaching the index. |
| Medium | The web module couples several failure domains in one process. | [Middleware](../modules/web-honeypot/app/middleware.py) owns body buffering, timeouts, dispatch, and logging. [Sessions](../modules/web-honeypot/app/sessions.py) and [rate limits](../modules/web-honeypot/app/ratelimit.py) are process-local, and the [Dockerfile](../modules/web-honeypot/Dockerfile) documents a single-worker constraint for rotation. Separate telemetry ownership and request handling before adding workers. |
| Medium | Classification quality is difficult to measure. | [Vector configuration](../modules/pipeline/vector/vector.yaml) keeps Cowrie protocol state in memory. [Classification rules](../modules/pipeline/vector/rules/classify.vrl) turn patterns into categories and MITRE labels. Preserve unknowns where the inputs are incomplete and validate changes against curated positive and negative examples. |
| Medium | Generated and maintained content are intermingled. | The checked-in web ZIP duplicates source distribution, and dashboard definitions are generated from a Python script. Define which files are authoritative and verify reproducible generated assets in CI. Remove the ZIP after confirming that no delivery process relies on it. |

## Preserve these decisions

The read-only telemetry mount, separate pipeline network, isolated web upload storage, checked-in fixtures, and tests for simulator containment are good foundations. Keep those boundaries explicit as deployment and telemetry contracts evolve.

## Baseline failures found during the review

- The route-test fixture passed an unsupported argument to the pinned Starlette client. The test fixture now supplies the synthetic peer at the ASGI boundary.
- The classification transform failed to compile with Vector 0.43.1. After correcting the VRL, the suite exposed a precedence error when a command also referenced a sensitive path. The command match now takes priority, as the existing test expects.

## Remediation order

1. Establish a reproducible, isolated bootstrap. Verify sensor log ownership, ingestion, clean restart, and rollback.
2. Define a telemetry contract and collection policy. Make rejection, retention, and access controls observable.
3. Separate web request handling from persistence where the runtime needs multiple workers. Validate classification against labeled examples.
4. Retire duplicate distribution artifacts and tighten lint rules after the baseline runs consistently.

Review scope includes the tracked source, configuration, deployment scripts, history of verification recorded in the module notes, and the checks described in [quality](quality.md). Live VPS changes, image execution, and firewall behavior require separate verification.
