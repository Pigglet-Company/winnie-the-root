# Cómo ejecutar Winnie

El runbook canónico está en [docs/RUN.md](docs/RUN.md). Visión general: [docs/overview.md](docs/overview.md).

```bash
./scripts/up.sh synthetic   # primera prueba: solo pipeline con datos sintéticos
./scripts/up.sh full        # señuelos + pipeline
./scripts/down.sh           # parar (conserva datos)
```
