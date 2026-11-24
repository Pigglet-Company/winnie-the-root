# Winee de Pou

**Plataforma modular de honeypots para capturar, procesar y analizar
actividad sospechosa en servicios web y de red.**

Winee de Pou reúne varios servicios señuelo en una infraestructura
Docker. Los honeypots registran las interacciones recibidas; un pipeline
centralizado normaliza y clasifica los eventos; y OpenSearch Dashboards
permite explorarlos mediante gráficos, filtros y tablas.

> **Aviso:** este proyecto es un laboratorio de ciberseguridad. No
> despliegues los honeypots en Internet sin revisar antes el
> aislamiento, los puertos publicados, las credenciales, los permisos de
> los volúmenes y la configuración TLS. Los registros pueden contener
> credenciales y otros datos sensibles.

## Contenido

-   [Arquitectura](#arquitectura)
-   [Tecnologías](#tecnologías)
-   [Requisitos](#requisitos)
-   [Despliegue rápido](#despliegue-rápido)
-   [Puertos y acceso a los
    servicios](#puertos-y-acceso-a-los-servicios)
-   [Cómo utilizar los honeypots](#cómo-utilizar-los-honeypots)
-   [Cómo utilizar el dashboard](#cómo-utilizar-el-dashboard)
-   [Consultar los registros](#consultar-los-registros)
-   [Detener y limpiar el entorno](#detener-y-limpiar-el-entorno)
-   [Estructura del repositorio](#estructura-del-repositorio)
-   [Configuración](#configuración)
-   [Limitaciones conocidas](#limitaciones-conocidas)

## Arquitectura

El proyecto se divide en tres módulos:

  -----------------------------------------------------------------------
  Módulo                  Componentes             Función
  ----------------------- ----------------------- -----------------------
  **A. Honeypot de red**  Cowrie + OpenCanary     Simula SSH, Telnet,
                                                  FTP, MySQL y Redis.

  **B. Honeypot web**     FastAPI + Uvicorn       Simula una intranet
                                                  vulnerable y registra
                                                  las peticiones HTTP.

  **C. Pipeline**         Vector + OpenSearch +   Recoge, normaliza,
                          Dashboards              clasifica, almacena y
                                                  visualiza los eventos.
  -----------------------------------------------------------------------

### Flujo de los datos:
<img width="768" height="714" alt="image" src="https://github.com/user-attachments/assets/96146f8e-67eb-4db4-9c18-814af0e58df2" />

Los honeypots escriben sus registros en el volumen compartido
`honeylogs`. Vector lo monta en **solo lectura**, procesa los ficheros y
envía los eventos a OpenSearch. Dashboards permite consultar los datos
almacenados.

Los simuladores del honeypot web no ejecutan comandos del sistema ni
consultas SQL reales, y la simulación LFI no lee archivos reales del
host: las respuestas son ficticias.

## Tecnologías

-   **Docker y Docker Compose:** ejecución y coordinación de los
    servicios.
-   **Python 3.12, FastAPI y Uvicorn:** aplicación web señuelo.
-   **Cowrie:** emulación de SSH y Telnet.
-   **OpenCanary:** emulación de servicios de red adicionales.
-   **Vector y VRL:** lectura, normalización, clasificación y
    enriquecimiento de eventos.
-   **OpenSearch:** almacenamiento e indexación.
-   **OpenSearch Dashboards:** exploración y visualización.
-   **GeoLite2 de MaxMind (opcional):** enriquecimiento geográfico de
    IPs.
-   **pytest y scripts de smoke test:** pruebas del proyecto.

## Requisitos

-   Docker Engine y Docker Compose v2 (`docker compose version`).
-   Python 3 y `curl` disponibles en el host para los scripts
    auxiliares.
-   Aproximadamente **4 GB de RAM libres** para Docker; más memoria
    puede mejorar el funcionamiento.
-   En Linux, OpenSearch requiere `vm.max_map_count` igual o superior a
    `262144`:

``` bash
sudo sysctl -w vm.max_map_count=262144
```

En Windows se recomienda Docker Desktop con WSL2. En macOS, Docker
Desktop.

## Despliegue rápido

Ejecuta los comandos desde la raíz del repositorio.

### Opción 1: probar el dashboard con datos de ejemplo

Esta opción levanta únicamente Vector, OpenSearch y OpenSearch
Dashboards. No inicia los honeypots. El proyecto genera un conjunto de
eventos sintéticos para comprobar el pipeline y explorar los paneles.

``` bash
./scripts/up.sh synthetic
```

Cuando termine, abre:

**http://localhost:5601/app/dashboards#/view/hp-dashboard**

Selecciona un rango de fechas que incluya los últimos 30 días si los
paneles aparecen vacíos.

Para comprobar el recorrido de los datos:

``` bash
cd modules/pipeline
./tests/e2e_check.sh
```

### Opción 2: levantar el sistema completo

Primero, si estabas utilizando el modo sintético, detenlo:

``` bash
./scripts/down.sh
```

Después, desde la raíz del repositorio:

``` bash
./scripts/up.sh full
```

El script prepara los recursos compartidos de Docker y levanta los
honeypots SSH/Telnet, FTP/MySQL/Redis, el honeypot web y el pipeline.

Al finalizar, abre el dashboard:

**http://localhost:5601/app/dashboards#/view/hp-dashboard**

La primera inicialización de OpenSearch puede tardar un poco. Comprueba
el estado de los contenedores con:

``` bash
docker ps
```

Para revisar un servicio concreto:

``` bash
docker logs -f hp-cowrie
docker logs -f hp-opencanary
docker logs -f hp-web
docker logs -f pl-vector
docker logs -f pl-opensearch
docker logs -f pl-dashboards
```

## Puertos y acceso a los servicios

Con la configuración predeterminada del proyecto, los servicios se
publican en estos puertos del host:

  ---------------------------------------------------------------------------------
  Servicio                           Puerto del host Acceso local
  --------------------- ---------------------------- ------------------------------
  SSH (Cowrie)                            `2222/tcp` `ssh -p 2222 root@127.0.0.1`

  Telnet (Cowrie)                         `2223/tcp` `telnet 127.0.0.1 2223`

  FTP (OpenCanary)                        `2121/tcp` Cliente FTP o
                                                     `nc 127.0.0.1 2121`

  MySQL (OpenCanary)                      `3307/tcp` Cliente MySQL contra
                                                     `127.0.0.1:3307`

  Redis (OpenCanary)                      `6380/tcp` Cliente Redis contra
                                                     `127.0.0.1:6380`

  Web Honeypot                            `8080/tcp` http://localhost:8080

  OpenSearch Dashboards                   `5601/tcp` http://localhost:5601
  ---------------------------------------------------------------------------------

OpenSearch escucha en el puerto `9200` **dentro de la red privada de
Docker**; no se publica directamente en el host. Vector también se
comunica con OpenSearch por esa red interna.

### Credenciales de los señuelos

Son credenciales ficticias para interactuar con los servicios simulados,
no credenciales de un sistema real:

  Servicio          Credenciales de ejemplo
  ----------------- -------------------------
  SSH (Cowrie)      `root` / `root`
  Telnet (Cowrie)   `admin` / `admin`

Cowrie utiliza una lista cerrada de credenciales configuradas en
`modules/ssh-honeypot/cowrie/userdb.txt`. Otros intentos se registran
como fallidos.

OpenCanary registra las interacciones con sus servicios; no proporciona
una base de datos MySQL ni un servidor Redis real.

### Dirección de enlace de los puertos

Por defecto, los puertos SSH/Telnet/FTP/MySQL/Redis se enlazan a
`127.0.0.1`. Para cambiar esa dirección, crea
`modules/ssh-honeypot/.env` a partir de `.env.example` y configura
`HP_BIND_ADDR`.

**Atención:** el puerto web se publica mediante `8080:8080` sin
restringir la dirección del host, por lo que Docker puede hacerlo
accesible desde otras interfaces. Dashboards, en cambio, está enlazado
explícitamente a `127.0.0.1:5601`.

No abras estos puertos a Internet sin revisar y adaptar antes las
medidas de seguridad.

## Cómo utilizar los honeypots

### 1. Honeypot web

Entra en **http://localhost:8080**. La aplicación muestra una intranet
ficticia de Nexora Industries.

Puedes navegar por la página y probar las rutas que simulan
comportamientos vulnerables:

  -----------------------------------------------------------------------
  Ruta                                Qué puedes probar
  ----------------------------------- -----------------------------------
  `/`                                 Página principal de la intranet.

  `/login` o `/admin`                 Intentos de inicio de sesión.

  `/search?q=...`                     Entradas que simulan SQL Injection.

  `/view?file=...`                    Rutas que simulan lectura de
                                      archivos (LFI/traversal).

  `/ping?host=...`                    Entradas que simulan Command
                                      Injection.

  `/comment`                          Contenido que simula XSS reflejado.

  `/upload`                           Subida de archivos de prueba.

  `/.env`, `/.git/config`,            Rutas habituales que pueden buscar
  `/robots.txt`                       los escáneres.
  -----------------------------------------------------------------------

Ejemplos de pruebas desde una terminal:

``` bash
# Visitar la página principal
curl -i http://localhost:8080/

# Simular una entrada de SQL Injection
curl -i --get --data-urlencode "q=' OR 1=1--" http://localhost:8080/search

# Simular un intento de traversal
curl -i --get --data-urlencode "file=../../../../etc/passwd" http://localhost:8080/view

# Simular una entrada de Command Injection
curl -i --get --data-urlencode "host=127.0.0.1;whoami" http://localhost:8080/ping
```

Las rutas devuelven respuestas ficticias y registran las peticiones. No
se ejecutan los comandos recibidos ni se leen archivos reales del
sistema.

Por defecto, el acceso al panel falso no se habilita con una contraseña:
`WEAK_PASS` está vacío. Si quieres probar el flujo de sesión, configura
una contraseña ficticia en `modules/web-honeypot/.env` (puedes partir de
`.env.example`) y recrea el contenedor:

``` bash
cd modules/web-honeypot
cp .env.example .env
```

Edita `.env` y define, por ejemplo:

``` dotenv
WEAK_USER=admin
WEAK_PASS=una-clave-de-prueba
```

Después aplica el cambio:

``` bash
docker compose up -d --build
```

Con esa combinación, el login falso acepta la credencial configurada y
redirige al panel simulado. No reutilices contraseñas reales.

### 2. Honeypot SSH y Telnet

SSH:

``` bash
ssh -p 2222 -o PreferredAuthentications=password root@127.0.0.1
```

Contraseña de ejemplo: `root`.

Telnet:

``` bash
telnet 127.0.0.1 2223
```

Credenciales de ejemplo: `admin` / `admin`.

Una vez dentro de Cowrie puedes introducir comandos de Linux como
`whoami`, `uname -a`, `ls -la` o `cat /etc/passwd`. Se trata de una
shell emulada: los comandos se registran y las respuestas son simuladas.

### 3. FTP, MySQL y Redis

OpenCanary simula estos servicios para registrar conexiones e intentos
de autenticación. Puedes interactuar con ellos mediante clientes
compatibles o enviar datos de prueba con `nc`.

Por ejemplo, para comprobar el puerto FTP:

``` bash
printf 'USER admin\r\nPASS prueba\r\nQUIT\r\n' | nc -w3 127.0.0.1 2121
```

No hay un servidor FTP, MySQL o Redis real detrás de estos puertos.

## Cómo utilizar el dashboard

Abre:

**http://localhost:5601**

En el modo de desarrollo predeterminado (`SECURITY_MODE=dev`), la
configuración de Dashboards desactiva la autenticación. La interfaz está
publicada únicamente en `127.0.0.1`, por lo que se accede desde la
propia máquina.

El dashboard principal se puede abrir directamente en:

**http://localhost:5601/app/dashboards#/view/hp-dashboard**

Desde ahí puedes:

-   Consultar el número total de eventos.
-   Ver la evolución de la actividad por horas y días.
-   Comparar los tipos de actividad detectados.
-   Consultar técnicas y tácticas MITRE ATT&CK asociadas.
-   Explorar IPs y países de origen (si GeoIP está configurado).
-   Revisar usuarios, credenciales, comandos y rutas web registrados.
-   Consultar sesiones y abrir el detalle de los eventos.

### Filtros y navegación

1.  Ajusta el selector de tiempo para incluir el periodo en el que se
    generaron los eventos.
2.  Utiliza los controles de servicio, honeypot, tipo de ataque e IP
    para acotar los resultados.
3.  Selecciona valores en gráficos o tablas para aplicar filtros.
4.  Utiliza la tabla de sesiones y la búsqueda guardada de detalle para
    investigar eventos concretos.
5.  Si un panel indica que faltan campos, revisa o actualiza el patrón
    de índice desde **Dashboards Management → Index patterns**.

**GeoIP es opcional.** Sin la base de datos GeoLite2, el pipeline sigue
funcionando, pero los paneles geográficos y los países pueden aparecer
vacíos.

## Consultar los registros

Los eventos originales se guardan en el volumen Docker `honeylogs`:

-   Cowrie: `/logs/cowrie/cowrie.json`
-   OpenCanary: `/logs/opencanary/opencanary.log`
-   Web: `/logs/web/web.jsonl`

Puedes consultar las últimas líneas sin entrar en los contenedores:

``` bash
docker run --rm -v honeylogs:/logs:ro busybox tail -n 20 /logs/web/web.jsonl
```

Para ver los eventos de Cowrie en tiempo real, si tienes `jq` instalado:

``` bash
docker run --rm -v honeylogs:/logs:ro busybox tail -F /logs/cowrie/cowrie.json \
  | jq -c '{time: .timestamp, event: .eventid, ip: .src_ip, user: .username, command: .input}'
```

Vector procesa los registros y los indexa en OpenSearch con índices
diarios `honeypot-events-AAAA.MM.DD` y el alias `honeypot-events`. La
retención configurada por defecto es de 30 días.

Los eventos que no se pueden procesar se desvían a la cola de errores de
Vector (Dead Letter Queue), dentro del volumen `vector-data`.

### Exportar eventos

Desde `modules/pipeline` puedes exportar datos para analizarlos fuera de
Dashboards:

``` bash
cd modules/pipeline

# Exportar los últimos siete días a CSV
python3 tools/export_events.py --format csv --since 7d --out export-7d.csv

# Exportar eventos clasificados como SQL Injection a NDJSON
python3 tools/export_events.py --format ndjson --query 'attack_type:sqli' --out export-sqli.ndjson
```

## Detener y limpiar el entorno

Desde la raíz del repositorio:

``` bash
# Detener los servicios y conservar los datos
./scripts/down.sh
```

Para eliminar también los volúmenes, la red compartida y los logs:

``` bash
./scripts/down.sh --purge
```

> `--purge` elimina datos persistentes. Utilízalo solo si estás seguro
> de que no necesitas conservar los registros ni los índices.

## Estructura del repositorio

``` text
Winee_de_Pou/
├── README.md
├── RUN.md
├── scripts/
│   ├── init.sh
│   ├── up.sh
│   └── down.sh
└── modules/
    ├── ssh-honeypot/
    │   ├── cowrie/
    │   ├── opencanary/
    │   ├── deploy/
    │   ├── scripts/
    │   └── tests/
    ├── web-honeypot/
    │   ├── app/
    │   │   └── sim/
    │   └── tests/
    └── pipeline/
        ├── vector/
        │   └── rules/
        ├── opensearch/
        ├── dashboards/
        ├── tools/
        ├── scripts/
        └── tests/
```

## Configuración

Los archivos `.env.example` muestran las variables disponibles. Cópialos
a `.env` únicamente en el módulo que quieras configurar y modifica los
valores necesarios:

-   `modules/ssh-honeypot/.env.example`: dirección de enlace de los
    puertos y límites de recursos.
-   `modules/web-honeypot/.env.example`: puerto web, credencial débil
    ficticia y confianza en proxy.
-   `modules/pipeline/.env.example`: modo de seguridad, contraseña de
    OpenSearch, memoria y retención.

No subas archivos `.env`, contraseñas ni claves de MaxMind al
repositorio.

Para habilitar GeoIP, configura `MAXMIND_LICENSE_KEY` en
`modules/pipeline/.env` y ejecuta:

``` bash
cd modules/pipeline
./scripts/download_geolite.sh
docker compose restart pl-vector
```

## Limitaciones conocidas

-   Es un laboratorio y no debe considerarse una plataforma de
    producción lista para exponerse a Internet.
-   El volumen compartido `honeylogs` se prepara con permisos amplios
    para facilitar las pruebas locales. Deben revisarse antes de un
    despliegue real.
-   La configuración de desarrollo de OpenSearch/Dashboards no habilita
    autenticación.
-   La configuración de producción requiere revisar y endurecer
    certificados, validación TLS, usuarios y permisos antes de
    utilizarla con datos reales.
-   El honeypot web registra información de las peticiones que puede
    incluir credenciales, cookies, cabeceras o payloads. Protege los
    logs y limita su retención y acceso.
-   En Docker Desktop, la IP de origen registrada puede ser la pasarela
    de Docker y no la IP original del cliente.
-   El firewall de salida incluido para los honeypots SSH está orientado
    a Linux y utiliza iptables; no se aplica de la misma manera en
    Docker Desktop.
-   La clasificación de eventos se basa en reglas y patrones. Una
    etiqueta de ataque es una clasificación automática, no una prueba
    por sí sola de que la explotación haya tenido éxito.

------------------------------------------------------------------------

**Winee de Pou** es un proyecto de laboratorio para estudiar la captura
de actividad sospechosa, el procesamiento de eventos de seguridad y su
análisis centralizado mediante herramientas open source.
