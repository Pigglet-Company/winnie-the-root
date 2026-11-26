# Winnie: visión general del proyecto

Esta guía es para alguien con pocos conocimientos técnicos que necesita entender el proyecto,
arrancarlo, saber qué debería ver y qué falta todavía. Los detalles técnicos están en
[README.md](../README.md), [RUN.md](RUN.md) y las guías de cada módulo.

> **Estado descrito:** `main` en `31216e9`, más las PR pendientes de W02 (fixture de pruebas web
> y escape de `/comment`), W01 (arranque fiable), W03 (reglas de clasificación y GeoIP con DB-IP) y W04
> (contención del laboratorio) y el cambio de diseño que trata las capturas como evidencia (PR #14).
> Actualizado el 26-11-2026.
> Si este bloque no coincide con el último trabajo cerrado, la guía está desactualizada.

## 1. Qué es Winnie, en una frase

Winnie es un **honeypot**: una colección de servicios falsos (un servidor SSH, una intranet web,
FTP, MySQL, Redis…) que parecen reales y atraen a los atacantes. No protegen nada de valor.
Su trabajo es **registrar todo lo que intenta el atacante** y mostrarlo en un panel de control
para que una persona lo pueda analizar.

Piénsalo como una casa de muestra con cámaras: nadie vive allí y todo lo que se toca queda grabado.

## 2. Las tres piezas

```
  Atacante (o tú, haciendo pruebas)
        │
        ▼
 ┌──────────────────────┐   ┌──────────────────────┐
 │ A · Señuelos de red  │   │ B · Intranet web     │
 │ SSH, Telnet, FTP,    │   │ falsa (login, panel, │
 │ MySQL, Redis         │   │ buscador, subidas…)  │
 └──────────┬───────────┘   └──────────┬───────────┘
            │  cada interacción = una línea en un fichero de registro
            ▼                          ▼
 ┌─────────────────────────────────────────────────┐
 │ C · Pipeline: Vector lee y clasifica los         │
 │     registros → OpenSearch los guarda →          │
 │     Dashboards los muestra en gráficos           │
 └─────────────────────────────────────────────────┘
                       │
                       ▼
          Tú, en el navegador: http://localhost:5601
```

| Pieza | Carpeta | Qué hace | Tecnología |
|---|---|---|---|
| **A** | `modules/ssh-honeypot/` | Finge ser un servidor Linux con SSH/Telnet y otros servicios de red | Cowrie, OpenCanary |
| **B** | `modules/web-honeypot/` | Finge ser la intranet de una empresa con fallos de seguridad *simulados* | Python, FastAPI |
| **C** | `modules/pipeline/` | Recoge, clasifica (p. ej. «SQL injection») y visualiza los eventos | Vector, OpenSearch, Dashboards |

Cada pieza funciona y se prueba por separado. La raíz del repositorio las une.

### Mapa de carpetas

| Ruta | Para qué sirve |
|---|---|
| `scripts/` | Comprobar (`preflight.sh`), arrancar (`up.sh`), parar (`down.sh`) y preparar (`init.sh`) todo el sistema; `lib/contract.sh` reúne perfiles y puertos |
| `modules/<pieza>/` | Código, configuración Docker (`compose.yml`), pruebas y README de cada pieza |
| `docs/` | Documentación: esta guía, [RUN.md](RUN.md), [arquitectura](architecture.md), [calidad](quality.md), guías por módulo |
| `docs/design.md` | **Contrato de diseño**: manda sobre el alcance, el orden y lo que significa «terminado» |
| `docs/requisites.md`, `docs/investigation.md` | El diseño V2 detallado y la investigación que lo justifica |
| `tests/` | Pruebas de la raíz (comprueban los datos de ejemplo compartidos) |
| `.github/workflows/quality.yml` | La batería automática (CI) que GitHub ejecuta en cada cambio |
| `AGENTS.md` | Reglas para los agentes de IA que trabajan en el repo |

## 3. Cómo lanzarlo

**Necesitas:** Linux (o Docker Desktop en Mac/Windows), Docker con Compose v2, `python3`, `curl`
y unos 4 GB de RAM libres. En Linux, antes de arrancar ejecuta una vez
`sudo sysctl -w vm.max_map_count=262144` (OpenSearch lo exige).

> **Aviso de seguridad:** es un laboratorio. No lo publiques en Internet. Los señuelos registran
> contraseñas, comandos y ficheros del intruso a propósito: son pruebas del delito. Trátalos como datos
> sensibles y no pruebes esas contraseñas en ningún sitio.

Antes de arrancar puedes ejecutar `./scripts/preflight.sh synthetic` (o `full`): revisa programas,
memoria de OpenSearch y puertos **sin cambiar nada** y dice qué falta. `up.sh` lo ejecuta por ti y
se detiene si algo falla. Todo escucha solo en `localhost` (127.0.0.1) salvo que lo cambies en el
`.env` de un módulo (plantillas: `modules/*/.env.example`). Runbook detallado: [RUN.md](RUN.md).

### Opción 1 · Primera prueba: solo el panel con datos inventados

No arranca ningún señuelo, así que no hay nada expuesto.

```bash
./scripts/up.sh synthetic
./modules/pipeline/tests/e2e_check.sh        # comprobación automática de extremo a extremo
```

**Qué deberías ver:** Docker descarga imágenes y arranca los contenedores `pl-*`. Después abre
<http://localhost:5601/app/dashboards#/view/hp-dashboard>, elige «últimos 30 días» y deberías
ver gráficos con ataques ficticios por tipo y servicio. `e2e_check.sh` debe terminar sin
errores.

Si el panel queda vacío, mira `docker logs pl-vector`. En `main` sin la PR de W03 el clasificador
no compila y `pl-vector` no arranca.

### Opción 2 · Sistema completo

```bash
./scripts/down.sh synthetic   # primero para lo anterior
sudo modules/ssh-honeypot/scripts/egress-firewall.sh   # solo Linux; necesita permisos de administrador
./scripts/up.sh full
```

El sistema completo recibe ataques de verdad, así que antes de arrancar los señuelos `up.sh` comprueba
que no pueden **abrir conexiones hacia fuera**: ni a Internet, ni al ordenador que los aloja, ni entre
ellos. Si pueden, se para y te dice qué hacer. La segunda línea instala esas reglas, que solo cortan
lo que sale: los señuelos siguen respondiendo a quien se conecta. Si vienes de una versión anterior,
`init.sh` te pedirá antes `./scripts/migrate_honeylogs.sh`, que copia los registros antiguos sin
borrarlos ([detalle](lab-containment.md)).

| Quieres probar… | Haz esto | Qué debería pasar |
|---|---|---|
| SSH falso | `ssh -p 2222 root@127.0.0.1` (contraseña `root`) | Entras en una «máquina» falsa; tus comandos quedan registrados |
| Telnet falso | `telnet 127.0.0.1 2223` (admin / admin) | Igual que SSH |
| FTP / MySQL / Redis | puertos 2121 / 3307 / 6380 | El servicio responde y anota la conexión |
| Intranet web | <http://localhost:8080> | Ves una intranet corporativa; prueba `/login`, `/search?q=laura`, `/comment` |
| Panel | <http://localhost:5601> | Tus pruebas aparecen como eventos clasificados al cabo de unos segundos |

Para parar: `./scripts/down.sh` (conserva los datos) o `./scripts/down.sh full --purge`
(**borra** volúmenes, red y registros del proyecto). Si algo no se puede parar, `down.sh` lo dice
y termina con error.

### Probar sin Docker (lo que cualquier persona puede repetir)

```bash
python3 -m unittest discover -s tests          # pruebas de la raíz: 36 deben pasar
cd modules/web-honeypot && pip install -r requirements-dev.txt && python -m pytest -q
```

La suite web debe terminar en `69 passed, 1 xfailed` con las PR de W02. El `xfailed` es una
prueba que documenta a propósito una carencia conocida (ver §5).

## 4. Qué funciona hoy y cómo verlo

| Funcionalidad | Cómo verla | Estado |
|---|---|---|
| Comprobación previa: programas, `vm.max_map_count`, configuración efectiva y puertos ocupados, sin tocar nada | `./scripts/preflight.sh full` | Verificada sin Docker por pruebas (W01); con Docker real, en CI |
| Parada que informa de errores y limpieza que solo borra recursos etiquetados del proyecto | `./scripts/down.sh synthetic` | Verificada sin Docker por pruebas (W01); con Docker real, en CI |
| Señuelos SSH/Telnet/FTP/MySQL/Redis | Opción 2 y tabla de arriba | Arrancan y responden por SSH y FTP en CI con Docker (W04). Antes de W04, el FTP/MySQL/Redis falso (OpenCanary) no llegaba a arrancar. Telnet, MySQL y Redis no se prueban uno a uno |
| Intranet web falsa con 18 rutas (login, panel admin, buscador, `/ping`, subidas, ficheros «olvidados» como `/.env` o `/.git/config`) | <http://localhost:8080> o la suite web | Verificada por pruebas automáticas |
| Registro de cada petición web como una línea JSON con identificador único | `docker exec hp-web tail /logs/web/web.jsonl` | Verificado por pruebas (W02) |
| La IP del atacante se toma de la conexión real; cabeceras como `X-Forwarded-For` solo se aceptan si se activa `TRUST_PROXY` | Suite web | Verificado (W02) |
| `/comment` muestra el comentario **escapado** (inofensivo) por defecto; `COMMENT_REFLECT_RAW=true` activa el fallo XSS de laboratorio | Envía `<script>alert(1)</script>` en <http://localhost:8080/comment> | Verificado (W02) |
| Datos de ejemplo y panel con 19 objetos (gráficos, tablas, búsqueda guardada) | Opción 1 | El panel se regenera idéntico; con W03 los 6001 eventos de ejemplo se clasifican igual que en la última versión validada |
| Clasificación de ataques (SQLi, XSS, fuerza bruta…) con mapeo MITRE ATT&CK | Panel, campos `attack_type` y `rule.id` | Verificada con Vector 0.43.1, en local y en CI con Docker (W03): 44 casos, incluidos solapes y controles inocuos, y 6001 eventos de muestra iguales a la versión de referencia |
| Cada evento dice qué regla y qué versión lo clasificó; el hecho (un login, un comando Redis, una descarga) se guarda aparte de su interpretación ATT&CK | Campos `rule.version`, `rule.id`, `rule.matches` | Verificado (W03); se puede volver a la versión anterior con un comando ([guía](../modules/pipeline/README.md#reglas-versiones-y-vuelta-atrás)) |
| Las comprobaciones internas de salud de los señuelos ya no aparecen como «escaneos» | Panel: menos `recon_scan` en un sistema parado | Verificado por pruebas (W03) |
| Mapa y países del atacante con la base gratuita DB-IP City Lite (hay que citar a DB-IP al mostrar los datos) | `modules/pipeline/scripts/download_geoip.sh` y reiniciar `pl-vector` | Verificado en local y en CI con Docker (W03); sin la base, el resto funciona igual |
| Un comando Redis aparece como «comando Redis», sin técnica MITRE: el señuelo solo lo imita y no prueba que se ejecutara nada | Panel: tipo `redis_command` | Verificado por pruebas (W03) |
| Cada señuelo guarda sus registros en su propio almacén; los demás no pueden leerlo, cambiarlo ni borrarlo, y Vector solo puede leer | `./scripts/volume_usage.sh` muestra cada almacén y su cuota | Verificado en CI con Docker y los usuarios reales de cada señuelo (W04) |
| Las contraseñas, comandos, sesiones y ficheros del intruso se guardan como pruebas: cada fichero queda con su huella (hash), se detecta si alguien lo cambia, se borra a los 90 días salvo que un caso lo bloquee y cada borrado queda anotado | `./scripts/evidence.py manifest` y `./scripts/evidence.py retention` | Verificado en CI con Docker, incluida una alteración provocada (W04) |
| Los señuelos no pueden abrir conexiones hacia Internet, hacia el ordenador que los aloja, hacia los metadatos de la nube ni entre ellos; si las reglas se instalan a medias, la salida queda cerrada | `./scripts/check_egress.sh` | Verificado en CI con Docker, incluido un fallo provocado a medias (W04). Es la prueba del laboratorio, no la de un sensor real (H02) |

## 5. Problemas conocidos del estado actual

| Problema | Qué notarás | Se arregla en |
|---|---|---|
| El instalador del VPS (`deploy/setup.sh`) no se ha ensayado en una máquina real | Puede fallar o dejar SSH/firewall a medias; úsalo solo en una máquina desechable | Ensayo autorizado en máquina desechable (pendiente) |
| No existe una lista de proxies autorizados (solo `TRUST_PROXY` sí/no) | Prueba `xfailed` en la suite web | Pendiente de decisión (diseño V2) |
| Las pruebas guardadas aún no tienen control de lectura: quien administra Docker en el servidor puede leerlas todas, y su huella no está firmada | Nadie queda registrado al leer una prueba | Pendiente: la custodia firmada llega con H03 ([detalle](lab-containment.md#capturas-como-evidencia)) |
| Las cuotas de espacio se anotan y se comprueban, pero el sistema no las impide | Un almacén puede pasarse de su cuota; `volume_usage.sh` lo avisa | Decidido así de momento; impedirlo exige preparar el disco del servidor como administrador |
| CI en rojo desde la PR #6 | Marca roja en GitHub | Se corrige al integrar las PR de W02 y W03 |

## 6. Hacia dónde va

El contrato completo está en [design.md](design.md). Resumen:

| Etapa | Unidades | Qué aportará respecto a hoy |
|---|---|---|
| **Arranque fiable** | W01 ✔ (en PR) | Un checkout limpio arranca con un comando, escucha solo en `localhost` por defecto, valida requisitos antes de empezar y `down.sh` informa de errores reales |
| **Web y reglas** | W02 ✔ (en PR), W03 ✔ (en PR) | Pruebas web en verde; clasificador que compila con casos positivos y negativos |
| **Contención** | W04 ✔ (en PR) | Cada servicio escribe solo en su sitio, con cuotas; un señuelo comprometido no contamina a los demás |
| **Contabilidad** | W05 | Recuentos exactos de eventos por fuente: se sabe si se perdió algo |
| **Entrega académica (TFM)** | W06 | Una segunda persona produce una interacción ficticia, la sigue hasta el panel y explica la clasificación y cualquier hueco |
| **Piloto en red IT** | H01–H05 | Sensores con identidad propia, consola para el SOC, expedientes verificables offline, instalación y actualización firmadas, piloto con un cliente |
| **Producto comercial** | Cierre H05 | Versión on-prem soportada que un cliente puede instalar, operar, actualizar y retirar |
| **Opcionales** | H06, H07 | Analítica con ML y modalidades gestionada/híbrida/OT, cada una con su propia puerta de aprobación |

## 7. Consejos para trabajar en el proyecto

- **Qué es «verdad»:** el código y lo que se ha **ejecutado**. Si un documento dice que algo
  funciona pero no hay prueba ejecutada, trátalo como «no verificado».
- **Orden de autoridad:** `docs/design.md` → `docs/requisites.md` (V2) → resto de documentación.
- **Cada cambio va en su propia rama y PR**; nadie sube directamente a `main`. CI
  (`.github/workflows/quality.yml`) tiene que estar en verde antes de integrar.
- **Cada pieza se prueba sola:** `modules/web-honeypot` (pytest), `modules/pipeline`
  (`tests/run_vector_tests.sh`, `tests/e2e_check.sh`), `modules/ssh-honeypot` (`tests/smoke_ssh.sh`,
  necesita `sshpass` y `jq`).
- **Configuración:** cada módulo lee un `.env` propio (nunca se sube a Git). Variables de la web:
  [guía del módulo web](modules/web-honeypot/guide.md).
- **Sin Docker** puedes ejecutar las pruebas de la raíz, la suite web, `ruff` y las pruebas de
  Vector con el binario 0.43.1. Lo que depende de contenedores (puertos, panel, ingestión)
  necesita Docker.
- **Nunca** pongas contraseñas, tokens o claves (p. ej. MaxMind) en ficheros del repositorio.
- **`modules/ssh-honeypot/deploy/setup.sh` modifica SSH y el cortafuegos del servidor:** no lo ejecutes en una
  máquina real sin autorización y un ensayo previo.

## 8. Glosario

| Término | Qué significa aquí |
|---|---|
| **Honeypot / señuelo** | Servicio falso que parece real para atraer atacantes y registrar lo que hacen. No contiene nada de valor. |
| **Cowrie** | Programa que imita un servidor SSH/Telnet: deja «entrar» al atacante en un Linux falso y graba sus comandos (pieza A). |
| **OpenCanary** | Programa que imita servicios como FTP, MySQL o Redis y avisa cuando alguien se conecta (pieza A). |
| **FastAPI** | Herramienta de Python con la que está hecha la intranet web falsa (pieza B). |
| **Vector** | Programa «cartero» de la pieza C. Lee los ficheros de registro de los señuelos, los ordena en un formato común, los **clasifica** (p. ej. «esto es una inyección SQL») y los entrega a OpenSearch. Sus reglas están escritas en un lenguaje propio llamado **VRL**. |
| **Regla versionada** | Cada clasificación indica qué regla la decidió y en qué versión (`rule.id`, `rule.version`). Si una regla nueva clasifica peor, se vuelve a la versión anterior y se compara con su *baseline*: el recuento esperado sobre los datos de ejemplo. |
| **GeoIP / MMDB** | Una base de datos que traduce una dirección IP a país, ciudad y coordenadas aproximadas; el fichero `.mmdb` es su formato. Winnie usa por defecto la gratuita DB-IP City Lite. Es aproximada: no identifica a una persona. |
| **OpenSearch** | Base de datos especializada en guardar y buscar muchos eventos rápidamente (pieza C). Escucha en el puerto 9200, solo dentro de Docker. |
| **OpenSearch Dashboards** | La web con gráficos y tablas para explorar los eventos guardados (<http://localhost:5601>). |
| **Pipeline** | La cadena completa de procesamiento: señuelo → registro → Vector → OpenSearch → Dashboards. |
| **Evento** | Una interacción registrada (una petición web, un intento de login, un comando) guardada como una línea **JSON**, un formato de texto estructurado. |
| **Clasificación / `attack_type`** | Etiqueta que Vector pone a cada evento según el tipo de ataque que parece. |
| **MITRE ATT&CK** | Catálogo público y estándar de técnicas de ataque. Cada clasificación se asocia a una de sus técnicas. |
| **SQLi, XSS, fuerza bruta…** | Tipos de ataque. SQLi: colar órdenes de base de datos en un formulario. XSS: colar código que se ejecute en el navegador de otro. Fuerza bruta: probar muchas contraseñas. |
| **Escapar** | Convertir caracteres especiales (`<`, `>`) en texto inofensivo para que el navegador los muestre en vez de ejecutarlos. |
| **Docker / contenedor** | Docker ejecuta cada programa en una «caja» aislada (contenedor) con todo lo que necesita. |
| **Docker Compose / `compose.yml`** | Fichero que describe qué contenedores arrancar juntos, con qué puertos y qué permisos. |
| **Puerto** | Número que identifica un servicio en una máquina (8080 = web falsa, 5601 = panel). |
| **localhost / 127.0.0.1 (loopback)** | «Esta misma máquina». Un servicio que escucha solo ahí no es visible desde otros equipos. |
| **`.env`** | Fichero local de configuración de cada módulo (contraseñas, puertos). Nunca se sube a Git. `.env.example` es su plantilla sin secretos. |
| **Proxy / `TRUST_PROXY`** | Un proxy es un intermediario que reenvía peticiones. Si se activa `TRUST_PROXY`, la web cree la IP que el proxy indica en una cabecera; si no, usa la IP de la conexión real. |
| **Preflight** | Comprobación previa al arranque (puertos libres, programas instalados…) para fallar pronto y con un mensaje claro. |
| **Git, rama, commit, PR** | Git guarda el historial del código. Una rama es una línea de trabajo aparte; un commit, un cambio guardado; una PR (pull request), la propuesta de integrar una rama en `main` tras revisión. |
| **CI** | Batería de comprobaciones automáticas que GitHub ejecuta en cada PR. «En rojo» = algo falla. |
| **Prueba / fixture / `xfailed`** | Una prueba comprueba un comportamiento automáticamente. Un fixture es la preparación común de las pruebas. `xfailed` = prueba que se sabe que falla y documenta una carencia conocida. |
| **Unidades W/H** | Bloques de trabajo del plan (`docs/design.md`): W01–W06 llevan a la entrega académica, H01–H07 al producto. |
| **TFM** | Trabajo Fin de Máster: la entrega académica del proyecto (unidad W06). |
| **SOC** | Centro de operaciones de seguridad: el equipo que analiza las alertas. |
| **On-prem** | Instalado en las máquinas del propio cliente, no en la nube. |

## Mantener esta guía

Actualiza esta guía al cerrar cada unidad W/H que cambie cómo se lanza el sistema, qué funciona
(§4), los problemas conocidos (§5) o el avance (§6), y cambia la fecha del bloque de estado.
