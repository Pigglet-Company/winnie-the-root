# Cómo ejecutar Winnie (guía rápida)

Winnie = honeypots (SSH/Telnet/FTP/MySQL/Redis con Cowrie + OpenCanary, y una web señuelo FastAPI)
+ pipeline (Vector → OpenSearch → Dashboards). Todo corre en Docker.
Visión general, estado actual y problemas conocidos: [docs/overview.md](https://github.com/Pigglet-Company/winnie-the-root/blob/main/docs/overview.md).

## Requisitos
- Docker + Docker Compose v2 (`docker compose version`).
- `python3` y `curl` en el host.
- **Linux**: `sudo sysctl -w vm.max_map_count=262144` (OpenSearch lo exige). Mac/Windows: Docker Desktop (en Windows, usa WSL2).
- Unos 4 GB de RAM libres para Docker.

## Primera ejecución recomendada: solo el pipeline con datos sintéticos
No arranca ningún señuelo. Sirve para ver que Vector, OpenSearch y Dashboards funcionan.
```bash
cd winnie-the-root-main
./scripts/up.sh synthetic
(cd modules/pipeline && ./tests/e2e_check.sh)      # verificación extremo a extremo
```
Abre http://localhost:5601/app/dashboards#/view/hp-dashboard (rango de tiempo: últimos 30 días).

## Sistema completo (señuelos + pipeline)
Primero para lo anterior: `./scripts/down.sh` (los dos modos usan los mismos contenedores `pl-*`).
```bash
./scripts/up.sh full
```
Puertos (los señuelos SSH quedan en 127.0.0.1 por defecto; `HP_BIND_ADDR=0.0.0.0` para abrirlos):

| Qué | Dónde |
|---|---|
| SSH señuelo (Cowrie) | `ssh -p 2222 root@127.0.0.1` (contraseña `root`) |
| Telnet señuelo | `telnet 127.0.0.1 2223` (admin / admin) |
| FTP / MySQL / Redis (OpenCanary) | 2121 / 3307 / 6380 |
| Web señuelo | http://localhost:8080 (**publicado en todas las interfaces**) |
| Dashboards | http://localhost:5601 (solo localhost) |

Pruebas de humo: `modules/ssh-honeypot/tests/smoke_ssh.sh` (necesita `sshpass` y `jq`) y
`modules/web-honeypot/tests/smoke_web.sh`.

## Parar / limpiar
```bash
./scripts/down.sh            # para, conserva datos
./scripts/down.sh --purge    # borra también volúmenes, red y logs
```

## Qué se ha añadido al repo
```
winnie-the-root-main/
├── scripts/
│   ├── init.sh      <- NUEVO: crea la red honeynet (172.30.0.0/24) y el volumen honeylogs
│   ├── up.sh        <- NUEVO: arranque (synthetic | full)
│   └── down.sh      <- NUEVO: parada / limpieza
├── docs/RUN.md      <- NUEVO: esta guía
└── modules/
    ├── pipeline/.env.example        <- NUEVO (opcional)
    ├── web-honeypot/.env.example    <- NUEVO (opcional)
    └── ssh-honeypot/.env.example    <- NUEVO (lo exige deploy/setup.sh)
```
No he modificado ningún archivo existente.

## Avisos importantes
- **No lo expongas a Internet tal cual.** `honeylogs` queda con permisos 0777 (solo pruebas), el perfil `prod`
  usa certificados de demo y `admin` para Vector, y `deploy/setup.sh` toca SSH y firewall del servidor.
  El propio `docs/architecture-review.md` lo marca como bloqueante antes de tráfico real.
- Valores no verificados por los autores (imagen sin shell de Cowrie, rutas internas, `read_only`): si `hp-cowrie`
  falla al arrancar, mira `docker logs hp-cowrie` (ver §7 de la guía del módulo SSH).
- La web señuelo guarda contraseñas y cuerpos de petición recibidos: trátalos como datos sensibles.
