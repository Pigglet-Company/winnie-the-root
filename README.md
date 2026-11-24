# Winnie

Winnie is a honeypot telemetry project. It runs decoy network services and a decoy web application, collects records of interactions, and presents the processed data in OpenSearch Dashboards. The intended reader is an operator or analyst who needs to understand what the sensors saw and how the event was classified.

| Component | What it does |
| --- | --- |
| [SSH and service decoys](docs/modules/ssh-honeypot/guide.md) | Cowrie records SSH and Telnet activity. OpenCanary supplies additional protocol decoys. |
| [Web decoy](docs/modules/web-honeypot/guide.md) | A FastAPI app simulates application behavior and writes structured HTTP events. |
| [Telemetry pipeline](docs/modules/pipeline/guide.md) | Vector normalizes and classifies events, OpenSearch indexes them, and Dashboards displays them. |

Start with the [architecture and data flow](docs/architecture.md). Read the [architecture review](docs/architecture-review.md) before considering a deployment with live traffic. The [quality guide](docs/quality.md) explains local checks and CI.
