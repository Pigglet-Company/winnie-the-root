# Contención del laboratorio

Cómo se separan los productores de logs, qué copias de datos existen, qué tráfico puede salir de la
honeynet y cómo se migra desde la disposición anterior. Cubre SEC-CONT-001 y PRIV-MIN-001 para el
**laboratorio** (W04), incluida la gestión de las capturas como evidencia. La contención exterior de un sensor (ACL de red, vNIC, revocación, H02) no está
aquí. Esta prueba no la demuestra.

## Volúmenes y UIDs

Cada productor escribe solo en su volumen. El colector (Vector) los monta todos en solo lectura.
La fuente única de verdad es `SOURCE_VOLUMES` en `scripts/lib/contract.sh`.

| Fuente | Volumen | Escritor (UID) | Lector | Cuota comprobada |
|---|---|---|---|---|
| Cowrie | `honeylogs-cowrie` | 999 (usuario de `cowrie/cowrie:2.9.0`) | Vector `1000:1000`, RO | 2048 MiB |
| OpenCanary | `honeylogs-opencanary` | 10002 | Vector, RO | 512 MiB |
| Web | `honeylogs-web` | 10001 | Vector, RO | 512 MiB |

- La raíz de cada volumen es `UID:1000` con modo `2750`. El bit setgid hace que los ficheros nuevos
  tengan grupo 1000. Con `umask 022` quedan `0644`, legibles por el grupo del colector y por nadie más,
  porque la raíz no es atravesable para «otros».
- `scripts/init.sh` crea los volúmenes y la red. Repetirlo vuelve a poner `UID:1000 2750` y **nunca
  reabre permisos**. Ya no existe el `0777` anterior.
- Cada productor monta solo su volumen. Aunque montara uno ajeno por error, su UID no podría leerlo,
  escribir en él ni borrar nada. `tests/check_isolation_docker.sh` lo prueba con los UIDs reales.
- OpenCanary pasa de 10001 a 10002 para no compartir UID con la web. Se cambió OpenCanary y no la web
  porque el volumen de subidas de la web ya pertenece a 10001, y así la vuelta atrás no exige `chown`.

### Cuotas

Por decisión, de momento las cuotas quedan **registradas y comprobadas**, sin imponer: `./scripts/volume_usage.sh` sale con
1 si un volumen supera la suya. Una cuota dura (por ejemplo, `pquota` de XFS por volumen) necesita root
en el host y un sistema de ficheros preparado, así que queda fuera del laboratorio. Los límites que sí
se imponen son estos:

| Copia | Límite impuesto |
|---|---|
| OpenCanary, log nativo | rotación 50 MB × 5 |
| Web, log nativo | rotación 50 MB × 5 |
| Web, subidas | 256 MB y 1000 ficheros |
| Cowrie, descargas | 10 MB por fichero (`download_limit_size`) |
| stdout de cualquier contenedor | `json-file` 10 MB × 3 |

## Inventario de copias

| Copia | Dónde | Para qué | Quién accede | Retención |
|---|---|---|---|---|
| JSON nativo de Cowrie y rotaciones diarias | `honeylogs-cowrie` (`cowrie.json*`) | fuente del pipeline y evidencia | Cowrie escribe, Vector lee | 90 d con bloqueo por caso |
| Log nativo de OpenCanary y rotaciones | `honeylogs-opencanary` (`opencanary.log*`) | fuente del pipeline y evidencia | OpenCanary escribe, Vector lee | 90 d, pero solo 5 rotaciones de 50 MB |
| Log nativo de la web y rotaciones | `honeylogs-web` (`web.jsonl*`) | fuente del pipeline y evidencia | web escribe, Vector lee | 90 d, pero solo 5 rotaciones de 50 MB |
| stdout de los contenedores (sin eventos de OpenCanary) | log `json-file` de Docker | diagnóstico | quien pueda usar `docker logs` | 10 MB × 3 |
| TTY de Cowrie, descargas y `cowrie.log` | `cowrie-data`, privado del módulo | evidencia: sesión, comandos, malware | solo Cowrie; nunca se sirve | 90 d con bloqueo por caso |
| Claves de host de Cowrie | `cowrie-data` | identidad estable del señuelo | solo Cowrie | hasta `down.sh --purge` |
| Subidas a la web | `web-honeypot_hp_web_uploads` | evidencia: ficheros del intruso | solo la web | 90 d con bloqueo por caso; tope de tamaño y número |
| Manifiestos, bloqueos y registro de borrados | `var/evidence/` (fuera de git) | integridad y rendición de cuentas | quien administra el host | sin plazo; solo hashes y rutas |
| Muestras **sintéticas** | `modules/pipeline/sample-logs/` (perfil sintético) | pruebas y demo | repositorio | versionadas, sin datos reales |

El modo **full** captura tráfico real. El modo **sintético** solo lee las muestras del repositorio:
`init.sh` crea los volúmenes `honeylogs-*` vacíos, pero el pipeline no los monta (`compose.dev.yml`).

### Capturas como evidencia

Las contraseñas probadas, los comandos y TTY, los ficheros y los payloads se producen en equipos propios
por un acceso no autorizado. Son la prueba del intento y la fuente de IOC, así que el modo full los
captura (`docs/design.md` §10, «Gestión de las capturas de evidencia»). Cowrie mantiene `ttylog`,
sftp/exec y la contraseña de cada login.

Aplicado en el laboratorio:

- **Integridad.** `./scripts/evidence.py manifest` guarda el sha256, el tamaño, la fecha y el modo de
  cada captura en `var/evidence/manifest-<fecha>.json`, encadenado al manifiesto anterior. Sale con 1
  en estos casos:
  - Una captura cerrada cambia.
  - Una captura desaparece sin borrado registrado.
  - Un TTY o una descarga no coincide con el sha256 de su nombre.
  - Una captura tiene permiso de ejecución.
  Un log vivo puede crecer. Una rotación numerada se sigue por su contenido.
- **Plazo.** `./scripts/evidence.py retention` lista lo que tiene más de 90 d (`EVIDENCE_TTL_DAYS`), sin
  borrar. `--apply` lo borra y anota cada fichero con su hash en `var/evidence/deletions.ndjson`.
  Nunca borra un log vivo ni un TTY abierto. En el VPS, `deploy/setup.sh` instala ambas órdenes en el
  cron diario, en lugar de la poda anterior de 5 días.
- **Bloqueo por caso.** Cada línea de `var/evidence/holds.txt` (`<almacén> <patrón>  # motivo`)
  conserva lo que coincide, aunque haya caducado.
- **Una copia menos.** OpenCanary ya no duplica sus eventos, con las contraseñas, en el stdout de Docker.
- **Contenido inerte.** Ningún componente ejecuta ni sirve lo capturado. Las subidas se guardan con
  `0640` y nombre aleatorio; las descargas de Cowrie con el sha256 por nombre. El manifiesto avisa si
  algo tiene permiso de ejecución.

Pendiente, sin unidad asignada en este documento:

- Las lecturas no se auditan: quien usa Docker en el host lo lee todo.
- El manifiesto no está firmado; la custodia firmada y el almacén de evidencia separado son de H03.
- `cowrie.log` (texto) repite las contraseñas en `cowrie-data`. Figura en el inventario y tiene el
  mismo plazo.
- OpenCanary y la web rotan 5 × 50 MB. Con mucho tráfico, lo más antiguo se pierde antes de 90 d: el
  manifiesto lo anota como «rotated out by the producer».

### Identidades ficticias

El modo de captura académico solo usa identidades inventadas:

- Los correos señuelo de la web usan el dominio reservado `intranet.nexora.local`.
- Las cuentas de Cowrie son genéricas (`root`, `admin`, `ubuntu`…).
- El hostname es `srv-prod-01`.
- Las IP que aparecen son privadas o de documentación (`10.10.4.0/24`, `203.0.113.7`).

`tests/test_lab_containment.py` impide que entren dominios o IP públicas reales.

## Política de salida

La honeynet `172.30.0.0/24` se crea con `enable_icc=false` y sin IPv6. Las reglas
`modules/ssh-honeypot/scripts/egress-firewall.sh` (requiere root) añaden:

| Destino | Conexión nueva desde la honeynet | Mecanismo |
|---|---|---|
| Internet (IPv4) | bloqueada; opcional TCP 80/443 + DNS con límite de ritmo (`--allow-downloads`) | `DOCKER-USER` → `HONEYNET_EGRESS` |
| Otros contenedores de la honeynet | bloqueada | `icc=false` y DROP de la subred |
| Redes privadas, CGNAT, loopback | bloqueada | DROP de RFC 1918, `100.64.0.0/10`, `127.0.0.0/8` |
| Metadatos cloud `169.254.169.254` | bloqueada | DROP de `169.254.0.0/16` |
| El propio host (gateway `172.30.0.1` y demás IP) | bloqueada | `INPUT` → `HONEYNET_INPUT` |
| IPv6 (cualquier destino) | no hay ruta | red sin IPv6 y `net.ipv6.conf.all.disable_ipv6=1` en cada señuelo |
| Respuestas a conexiones entrantes | permitidas | `ESTABLISHED,RELATED` |

- **Instalación a prueba de fallos.** El script inserta antes que nada un *guard* (comentario
  `winnie-egress-guard`) que descarta toda conexión nueva desde la subred, y lo quita solo al terminar
  bien. Si falla a medias, la salida queda **cerrada**. `--remove` limpia cadenas, saltos y guard
  también tras un fallo.
- **Antes de los listeners.** `./scripts/up.sh full` ejecuta `scripts/check_egress.sh` antes de
  arrancar los señuelos. La sonda es un contenedor efímero sin privilegios que intenta salir a
  Internet, a DNS externo y a metadatos. Si alguna conexión sale, `up.sh` se detiene.
  `WINNIE_ALLOW_EGRESS=1` permite seguir solo si todos los puertos publicados escuchan en `127.*`.
  En el VPS, la unidad systemd aplica las reglas con `Before=docker.service`.
- Las reglas no limitan IPv6 porque la honeynet no tiene IPv6. Si se activa, hay que añadir
  `ip6tables`.

## Migración desde `honeylogs`

La disposición anterior tenía un solo volumen `honeylogs` con `0777` y una honeynet sin aislar.
`init.sh` se niega a seguir con esa red y remite a la migración.

```bash
./scripts/down.sh full            # sin --purge: la migración es en frío
./scripts/migrate_honeylogs.sh    # recrea la red aislada y copia cada fuente a su volumen
./scripts/up.sh full
```

- El legado se monta en **solo lectura** y no se modifica ni se borra.
- Ningún destino se sobrescribe: si alguno ya tiene datos, la migración no copia nada.
- El manifiesto `var/migrations/honeylogs-<fecha>.json` (fuera de git) guarda el sha256 de cada fichero
  en origen y destino. También lista los ficheros que quedan solo en el legado por no pertenecer a una
  fuente. La migración falla si algún hash no coincide.
- Vector identifica los ficheros por su contenido, así que no debería reingerir los ficheros migrados.
  Esto no se ha verificado; compruébalo en el primer arranque.

**Vuelta atrás**:

1. `./scripts/down.sh full`.
2. `git checkout` del commit anterior a W04.
3. `./scripts/up.sh full`.

Los módulos vuelven a montar `honeylogs`, que sigue intacto. Lo escrito después de migrar queda solo en
los volúmenes nuevos. `down.sh --purge` nunca borra el legado: bórralo a mano
(`docker volume rm honeylogs`) cuando ya no lo necesites.

## Verificación

- `python3 -m unittest discover -s tests`: montajes por fuente, ausencia de `0777`, UIDs distintos,
  límites de logs de Docker e identidades ficticias; reglas de integridad y plazo de `scripts/evidence.py`.
- `tests/check_isolation_docker.sh`, solo en un host desechable (CI, `WINNIE_DISPOSABLE_HOST=1`):
  - Migración, con el legado sin cambios y una segunda migración rechazada.
  - `init.sh` repetido sin reabrir permisos.
  - Fallo inyectado a medias en el firewall, que deja la salida cerrada.
  - Sondas a Internet, DNS, metadatos, host y pares.
  - IPv6 ausente.
  - Respuestas SSH, FTP y HTTP con la salida cerrada.
  - Escritura propia y denegación cruzada con los UIDs reales.
  - Lectura del colector.
  - Persistencia tras reinicio.
  - Capturas: alteración detectada, bloqueo por caso, simulación y borrado registrado, log vivo
    conservado, OpenCanary sin eventos en stdout.
  - Retirada de reglas.

  Nunca lo lances en un VPS real.
