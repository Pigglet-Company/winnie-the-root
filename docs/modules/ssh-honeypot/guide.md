# Módulo A — SSH/Telnet honeypot (Cowrie + OpenCanary)

Los comandos que usan rutas relativas a este módulo se ejecutan desde `modules/ssh-honeypot/`, salvo donde se indique que el punto de partida es la raíz del repositorio. Consulta los [recursos compartidos](../../architecture.md#first-run).

Honeypots defensivos para el TFM. Registran intentos de login, comandos, descargas y sesiones
en sus volúmenes `honeylogs-cowrie` y `honeylogs-opencanary` ([contención](../../lab-containment.md)). **Todo es simulado**: nada de lo que escribe el atacante se ejecuta.

| Servicio | Contenedor | Puerto host | Log nativo |
|---|---|---|---|
| SSH (Cowrie) | `hp-cowrie` | 2222 | `honeylogs-cowrie`: `cowrie.json` |
| Telnet (Cowrie) | `hp-cowrie` | 2223 | idem |
| FTP (OpenCanary) | `hp-opencanary` | 2121 | `honeylogs-opencanary`: `opencanary.log` |
| MySQL (OpenCanary) | `hp-opencanary` | 3307 | idem |
| Redis (OpenCanary) | `hp-opencanary` | 6380 | idem |

## 1. Requisitos
Docker + Compose v2. Para el test: `sudo apt install openssh-client sshpass jq`.
El firewall de salida solo funciona en **Linux** (iptables). En Docker Desktop (Mac/Windows) no aplica.

## 2. Arranque (Fase 1, red aislada)
```bash
# Prepara los recursos compartidos según la guía de arquitectura.

cd modules/ssh-honeypot
docker compose up -d --build
docker compose ps          # ambos "Up (healthy)" en ~40 s
```

## 3. Verificación
```bash
# 3.1 Prueba de humo automática (debe terminar en "OK")
./tests/smoke_ssh.sh

# 3.2 Log en tiempo real
docker run --rm -v honeylogs-cowrie:/logs/cowrie:ro busybox:1.36 tail -F /logs/cowrie/cowrie.json \
  | jq -c '{t: .timestamp, ev: .eventid, ip: .src_ip, user: .username, cmd: .input}'

# 3.3 A mano
ssh -p 2222 -o PreferredAuthentications=password root@127.0.0.1     # contraseña: root
telnet 127.0.0.1 2223                                               # admin / admin

# 3.4 OpenCanary
printf 'USER admin\r\nPASS prueba\r\nQUIT\r\n' | nc -w3 127.0.0.1 2121
printf '*2\r\n$4\r\nAUTH\r\n$6\r\nsecret\r\n' | nc -w2 127.0.0.1 6380
mysql -h127.0.0.1 -P3307 -uroot -pprueba          # (si tienes cliente mysql)
docker run --rm -v honeylogs-opencanary:/logs/opencanary:ro busybox:1.36 tail -n 5 /logs/opencanary/opencanary.log

# 3.5 Comprobaciones de seguridad
docker inspect hp-cowrie hp-opencanary --format '{{.Name}} user={{.Config.User}} ro={{.HostConfig.ReadonlyRootfs}} caps_drop={{.HostConfig.CapDrop}}'
docker inspect hp-cowrie --format '{{range .Mounts}}{{.Source}} {{end}}' | grep -c docker.sock   # debe dar 0
```
> En pruebas locales `src_ip` será `172.30.0.1` (la pasarela de Docker). Con tráfico externo y DNAT se ve la IP real.

## 4. Qué hace cada configuración
- **`cowrie/cowrie.cfg`**: hostname `srv-prod-01`, banner SSH y kernel coherentes con Debian 12,
  shell emulada (`backend = shell`), SSH 2222 + Telnet 2223, `forward_redirect/forward_tunnel = false`
  (se registran peticiones de túnel, no se reenvía tráfico), y JSON nativo a `/logs/cowrie/cowrie.json`.
  `cowrie.log`, TTY logs, descargas y claves de host van al volumen privado `cowrie-data`.
- **`cowrie/userdb.txt`**: lista **cerrada** de credenciales débiles que dejan entrar (root/root, admin/admin, ...).
  Todo lo demás falla y genera `cowrie.login.failed` (material para fuerza bruta).
- **`cowrie/honeyfs/etc/*`**: `hostname`, `issue` y `motd` coherentes con el resto de la huella.
- **`opencanary/`**: imagen propia (no root, UID 10002) con solo FTP/MySQL/Redis activos;
  el resto de servicios están desactivados. Log con `RotatingFileHandler` de 50 MB × 5.
- **`compose.yml`**: `cap_drop: ALL`, `no-new-privileges`, `read_only`, `pids_limit`, CPU/RAM limitadas,
  versiones fijas, solo red `honeynet`, **sin** `docker.sock`. IPs fijas `172.30.0.10` (Cowrie) y `.11` (OpenCanary).

## 5. Firewall de salida (`scripts/egress-firewall.sh`)
```bash
sudo ./scripts/egress-firewall.sh                    # bloqueo total de salida
sudo ./scripts/egress-firewall.sh --allow-downloads  # modo controlado
sudo ./scripts/egress-firewall.sh --status | --remove
```
Crea la cadena `HONEYNET_EGRESS` (enganchada en `DOCKER-USER`) y `HONEYNET_INPUT` (en `INPUT`):
solo se permiten respuestas a conexiones entrantes y tráfico interno de `honeynet`; se bloquea la salida
nueva hacia Internet y hacia redes privadas.

**Consecuencia del bloqueo total:** Cowrie **registrará la URL** de `wget`/`curl`/`tftp` del atacante
(`cowrie.command.input` y, normalmente, `cowrie.session.file_download.failed`), pero **no podrá descargar el fichero**:
no habrá muestra de malware ni SHA-256. El módulo C sigue clasificando `malware_download` porque lo deduce de la URL en el comando.
Además, los `wget` del atacante tardarán hasta agotar el tiempo de espera, lo que puede delatar el señuelo.

**`--allow-downloads`** (solo en un entorno aislado y controlado): permite salida nueva únicamente a TCP 80/443 y DNS,
con límite de ritmo, y sigue bloqueando redes privadas y metadatos cloud. Las muestras se guardan en `cowrie-data`
(`var/lib/cowrie/downloads`), nunca se ejecutan ni se sirven. No lo uses en el VPS público.

Nota: las reglas se pierden al reiniciar; en el VPS las persiste el servicio `honeypot-firewall` (§8).

## 6. Hardening aplicado (contrato §9)
| Requisito | Implementación |
|---|---|
| Sin root | Cowrie: usuario de la imagen; OpenCanary: UID 10002; cada uno solo escribe en su volumen |
| `cap_drop: [ALL]`, `no-new-privileges` | `compose.yml` |
| `read_only` | rootfs de solo lectura + `tmpfs` en `/tmp` |
| Límites CPU/RAM | `cpus`, `mem_limit`, `pids_limit` (ajustables en `.env`) |
| Versión fija | `cowrie/cowrie:v2.6.1`, `python:3.11.11-slim-bookworm`, `opencanary==0.9.4` |
| Sin `docker.sock`, solo `honeynet` | verificable con 3.5 |
| Nada ejecutado/leído del host | shells y servicios emulados; sin montajes del host salvo configs en `:ro` |
| Descargas aisladas | volumen privado `cowrie-data`, ficheros sin permiso de ejecución, sin servir |
| Secretos | el módulo no usa; `.env` fuera de git |

## 7. Problemas frecuentes
- **`hp-cowrie` no arranca con `read_only`**: mira `docker logs hp-cowrie`; prueba a comentar `read_only: true` solo para ese servicio y avísanos.
- **`unhealthy`**: la imagen no trae shell y el healthcheck usa `/cowrie/cowrie-env/bin/python`; si la ruta difiere, ajústala (el honeypot sigue funcionando).
- **El tag de imagen no existe**: `docker pull cowrie/cowrie:<tag>` con uno válido y cámbialo en `compose.yml`.
- **`smoke_ssh.sh` falla por permisos de Docker**: ejecútalo con un usuario del grupo `docker` o con `sudo`.

## 8. Diseño de despliegue en VPS (pendiente de validación)

El script presupone un inicializador y una plantilla de entorno ausentes en este checkout. Revisa los riesgos de cambios en SSH y firewall en el [análisis](../../architecture-review.md) antes de considerar este flujo.
Copia el repo al VPS (p. ej. `/opt/honeypot-tfm`) y, **con tu clave pública ya instalada**:
```bash
sudo modules/ssh-honeypot/deploy/setup.sh prepare --admin-user TU_USUARIO [--wireguard]
# En OTRA terminal:  ssh -p 22022 TU_USUARIO@IP_VPS     <- debe funcionar
sudo modules/ssh-honeypot/deploy/setup.sh finalize
```
`prepare` instala Docker y ufw, deja el SSH real en 22022 (solo clave, `AllowUsers`, `MaxAuthTries 3`),
mantiene el 22 abierto **temporalmente**, ejecuta `scripts/init.sh`, levanta los honeypots y activa el servicio `honeypot-firewall`
(egress-firewall + redirecciones `23→2223`, `21→2121`, `3306`, `6379`). `finalize` retira el 22 del SSH real y redirige `22→2222`.

Las redirecciones usan **DNAT a la IP fija del contenedor** (no `REDIRECT`): así Cowrie ve la IP real del atacante.
Los puertos publicados por Docker **saltan las reglas de ufw**: ufw protege solo los servicios del propio VPS (SSH real).

`--wireguard` crea un servidor `wg0` (10.8.0.1/24, UDP 51820). Para el panel de Dashboards (solo `127.0.0.1:5601`):
`ssh -p 22022 -L 5601:127.0.0.1:5601 TU_USUARIO@IP_VPS`.

### Recuperar el acceso si el SSH real queda inaccesible
1. Entra por la **consola web/VNC** del proveedor (no depende de la red).
2. `sudo /opt/honeypot-tfm/modules/ssh-honeypot/deploy/setup.sh rollback` (reabre el SSH real en el 22 y quita la redirección).
3. Comprueba `ss -ltnp | grep sshd` y `sudo ufw status`.
4. Si perdiste la clave: modo *rescue* del proveedor, monta el disco y añade tu clave a `~/.ssh/authorized_keys`.
5. Si `sshd` no arranca: `sshd -t` indica el error; el fichero gestionado es `/etc/ssh/sshd_config.d/00-honeypot-admin.conf`.

## 9. Limitaciones conocidas
- El `fs.pickle` por defecto de Cowrie contiene el usuario `phil`, una huella conocida de honeypot. Para un despliegue más creíble
  genera uno propio con `bin/fsctl` desde un checkout de Cowrie y móntalo (línea comentada en `compose.yml`).
- Rotación: Cowrie rota a diario (5 días en el VPS); OpenCanary rota a 50 MB × 5. Ver [notas de integración](integration-notes.md).
- `samples/` son sintéticos con el formato nativo exacto; sustitúyelos por capturas reales tras la primera ejecución.
