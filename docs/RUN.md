# Cómo ejecutar Winnie (runbook)

Runbook canónico: los demás documentos remiten aquí para arrancar, comprobar y parar.
Visión general, estado actual y problemas conocidos: [overview.md](overview.md).

Winnie = señuelos (A: SSH/Telnet/FTP/MySQL/Redis con Cowrie + OpenCanary; B: intranet web FastAPI)
+ pipeline (C: Vector → OpenSearch → Dashboards). Todo corre en Docker.

## Requisitos

Los comprueba `./scripts/preflight.sh <perfil>` sin cambiar nada. `up.sh` lo ejecuta antes de
tocar el host. El contrato (perfiles, puertos, requisitos) vive en `scripts/lib/contract.sh`.

- Docker + Docker Compose v2 (`docker compose version`), `python3` y `curl`.
- **Linux**: `sudo sysctl -w vm.max_map_count=262144` (OpenSearch lo exige). Mac/Windows: Docker Desktop (WSL2 en Windows).
- Unos 4 GB de RAM libres para Docker.

## Perfiles

| Perfil | Qué arranca | Puertos en el host |
|---|---|---|
| `synthetic` | Solo el pipeline, con datos inventados. Nada expuesto | 5601 |
| `full` | Señuelos A y B + pipeline | 2222, 2223, 2121, 3307, 6380, 8080, 5601 |

Todos los puertos escuchan en **127.0.0.1** por defecto, tanto desde `scripts/up.sh` como al lanzar
un módulo a mano (`docker compose up` dentro de `modules/<módulo>`). Para abrir los señuelos a
otras interfaces, pon `HP_BIND_ADDR=0.0.0.0` en el `.env` del módulo. Dashboards queda siempre en
127.0.0.1:5601 y OpenSearch (9200) solo en la red interna de Docker.

## Configuración

Cada módulo lee un `.env` opcional. Las plantillas, sin secretos, son
`modules/ssh-honeypot/.env.example`, `modules/web-honeypot/.env.example` y
`modules/pipeline/.env.example`. Precedencia: variable del shell > `.env` del módulo > valor por
defecto. El preflight imprime la configuración efectiva.

## Primera ejecución: datos sintéticos

```bash
./scripts/preflight.sh synthetic       # opcional: up.sh también lo ejecuta
./scripts/up.sh synthetic
./modules/pipeline/tests/e2e_check.sh  # verificación extremo a extremo
```
Abre http://localhost:5601/app/dashboards#/view/hp-dashboard (rango: últimos 30 días).
Si el checkout perdió los permisos de ejecución (p. ej. descargado como ZIP), usa `bash scripts/up.sh …`.

## Sistema completo

```bash
./scripts/down.sh synthetic   # los dos perfiles comparten los contenedores pl-*
./scripts/up.sh full
```

| Qué | Dónde |
|---|---|
| SSH señuelo (Cowrie) | `ssh -p 2222 root@127.0.0.1` (contraseña `root`) |
| Telnet señuelo | `telnet 127.0.0.1 2223` (admin / admin) |
| FTP / MySQL / Redis (OpenCanary) | 2121 / 3307 / 6380 |
| Web señuelo | http://localhost:8080 |
| Dashboards | http://localhost:5601 |

Pruebas de humo: `modules/ssh-honeypot/tests/smoke_ssh.sh` (necesita `sshpass` y `jq`) y
`modules/web-honeypot/tests/smoke_web.sh`.

## Parar y limpiar

```bash
./scripts/down.sh                     # para el perfil full (todo); conserva datos
./scripts/down.sh synthetic           # para solo el pipeline
./scripts/down.sh synthetic --purge   # borra además los volúmenes del pipeline
./scripts/down.sh full --purge        # borra volúmenes de los tres módulos, red y logs compartidos
```
`down.sh` sale con error y muestra la causa si algo no se pudo parar. `--purge` solo borra la red
`honeynet` y el volumen `honeylogs` si llevan la etiqueta `io.winnie.project=winnie-the-root` (los
crea así `init.sh`); si se crearon con una versión anterior, te dice cómo borrarlos a mano.

## Avisos importantes

- **No lo expongas a Internet tal cual.** `honeylogs` queda con permisos 0777 (solo pruebas; W04),
  el perfil `prod` usa certificados de demo y `admin` para Vector.
- `modules/ssh-honeypot/deploy/setup.sh` toca SSH y firewall del servidor: comprueba sus
  prerrequisitos antes de cambiar nada, pero ensáyalo en una máquina desechable y con autorización
  antes de usarlo en un VPS real.
- Si `hp-cowrie` falla al arrancar, mira `docker logs hp-cowrie` (§7 de la guía del módulo SSH).
- La web señuelo guarda contraseñas y cuerpos de petición recibidos: trátalos como datos sensibles.
