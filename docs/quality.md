# Quality checks

Run these from the repository root with Python 3.12 in a virtual environment.

```sh
python -m pip install ruff==0.11.13 -r modules/web-honeypot/requirements-dev.txt
ruff check modules tests
python -m unittest discover -s tests -v
(cd modules/web-honeypot && python -m pytest -q)
(cd modules/pipeline && python tools/build_dashboards.py)
git diff --exit-code -- modules/pipeline/dashboards/honeypot.ndjson
```

[Ruff rules](../ruff.toml) cover invalid syntax, undefined names, and related correctness errors. [CI](../.github/workflows/quality.yml) also checks shell syntax, renders all Compose models, and runs the existing Vector tests in the pinned runtime image. Shell syntax checks cover parsing. Host changes and firewall behavior require testing on a disposable system.

When changing event fields, update the producer fixtures, Vector transformations, index mappings, and dashboards together. Add a test at the boundary where the regression would first appear. When changing a generated dashboard, commit the source and regenerated output in the same change.

For full integration, use the [synthetic pipeline procedure](modules/pipeline/guide.md) and its existing end-to-end check. For the sensors, the module guides document the existing smoke tests. Use a disposable, isolated environment for those checks.
