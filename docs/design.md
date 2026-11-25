# Winnie / HoneyGrid · Prompt maestro de implementación revisado

**Instrucción de inicio.** Actúa como responsable de la entrega técnica. En un checkout nuevo ejecuta U00. Si recibes un relevo, recupera su SHA y comprueba la primera aceptación pendiente. Usa las secciones 1–6 para dirigir el trabajo y abre únicamente el contrato aplicable de las secciones 7–12. El resultado de una sesión debe poder reproducirlo otro operador.

**Cómo decidir qué construir.** La investigación identifica necesidades, alternativas y riesgos. Diseño v2 decide el perfil, el orden y la aceptación. Un hallazgo en el informe requiere una decisión trazable, pero sólo entra al código cuando lo activa su perfil. Si el HEAD resuelve una brecha histórica, registra la prueba y pasa a la siguiente. Una referencia A/T, un ejemplo del anexo o una prueba especificada describen evidencia esperada. Sólo el resultado ejecutado sobre un build identificado cuenta para promoción.

## 1. Misión y definición de proyecto terminado

Evoluciona el repositorio Pigglet-Company/winnie-the-root desde su HEAD real hasta una versión on-prem dedicada que un cliente IT pueda instalar, operar, verificar, actualizar y retirar. Entrega primero el TFM: un segundo operador debe poder producir una interacción ficticia, seguirla hasta el dashboard y explicar tanto la clasificación como cualquier hueco de captura. En el producto, el administrador configura la flota, el SOC resuelve si debe investigar una interacción y el custodio entrega un caso que un tercero puede verificar offline.

Usa este documento como contrato operativo durante todas las sesiones. La autoridad sobre alcance y aceptación es **Winnie-HoneyGrid-diseno-v2.md** (V2). **HP | Investigación modular forense con IA.md** (I) justifica sus decisiones. Localiza ambas fuentes por nombre normalizando espacios y acentos; si falta una, solicita esa fuente antes de decidir sobre su contenido. **ENTREGAS.md** contiene los prompts de activación. Puedes ejecutar U00 con la sección 4. En sesiones posteriores abre la ficha activa y el contrato que se le aplica. Si descubres un conflicto, registra ambas secciones, entrega afectada, evidencia e implicación. Conserva V2; escala sólo si existe un impedimento técnico, jurídico o de seguridad. Continúa lo independiente.

Tras el piloto aún debes convertir la candidata en una release soportada: resolver el acta de promoción, reproducir el paquete firmado desde un build identificado, fijar alcance soportado y SLO con los responsables, cerrar derechos por activo, ensayar soporte y recuperación, designar PSIRT, preparar avisos, parcheo, retirada y EOL, y entregar al cliente el expediente y los medios de verificación y migración. La aceptación incluye sensor, consola, reglas/perfiles, documentación operativa y evidence/1 con verificador. Conserva la release académica independiente. Registra el estado de datasets y pesos por separado; su entrega depende de derechos y validación. Servicio gestionado, híbrido y OT tienen puertas propias. La venta dedicada puede cerrarse aunque esos productos y ML sigan aplazados.

## 2. Contexto técnico imprescindible

**Punto de partida contrastado.** El 25-11-2026 origin/main y el checkout consultado apuntaban a 31216e9f3de81c64f8bb54a6dfdbb907026ee100. En ese árbol se localizaron los módulos A/B/C, scripts raíz con modo 100644, la fixture web con client= y las asignaciones VRL cuestionadas. Se ejecutó la suite raíz: dos pruebas de fixtures aprobadas. V2 → «Auditoría del repositorio y evidencia» documenta una ejecución anterior sobre ese mismo SHA: pytest web dio 17 aprobadas, 6 fallidas y 40 errores; la corrección experimental sólo en una copia dio 63/63. Vector 0.43.1 rechazó el clasificador, y los 19 objetos del dashboard se regeneraron idénticos. Docker, puertos efectivos, importación, contención y restauración quedaron sin verificar en esa auditoría. Reproduce sobre tu SHA antes de atribuirle cualquiera de estos resultados. La arquitectura comercial figura como compromiso futuro.

|Decisión que debes preservar|Fuente que debes consultar al tocarla|
|---|---|
|Mantén A (Cowrie/OpenCanary), B (intranet FastAPI simulada) y C (Vector/OpenSearch/Dashboards) y sus pruebas autónomas. Integración gobierna entradas raíz, CI y contratos. Usa perfiles synthetic/full separados hasta almacenamiento e índices. El piloto arranca con HTTP mínimo en zona IT autorizada.|V2 → «Perfiles y propiedad», «Hallazgos por archivo y tramo». Consulta I → «MVP defendible» para entender el conflicto: propone IT e Internet inicialmente; V2 → «Decisión de arquitectura» elige IT para el piloto. La exposición a Internet queda aplazada.|
|Minimiza antes de la primera escritura. Distingue intento, resultado, artefacto realmente preservado y dato desconocido. Trata observación, recepción y anotación como registros con procedencia propia. Conserva lectores N−1 y procedencia histórica.|V2 → «Adaptación de eventos», «Contrato v1.0 y tratamiento de incertidumbre». I → «Catálogo mínimo de eventos» fundamenta la cobertura; aplica únicamente los campos autorizados por perfil.|
|En piloto, conserva Go para nuevo agente/colector según V2, WAL local cifrado, mTLS por sensor y PostgreSQL como autoridad. Asigna identidad durable por ocurrencia; confirma después del commit de original, adquisición y recibo. OpenSearch sirve al TFM; una proyección comercial adicional requiere beneficio medido y reconstrucción.|V2 → «Contrato de implementación v2», párrafos «Frontera de persistencia», «Compatibilidad» y «Salud y control».|
|Supón control total del guest. Conserva ACL y corte externos, plano de gestión separado, perfil declarativo firmado, control por objeto y tenant, revocación y salud contrastada desde fuera. Un sensor válido puede mentir.|I → «El caso adversarial decisivo: sensor totalmente comprometido»; V2 → «Salud y control» y backlog H02.|
|Entrega alerta, sesión, cronología, aristas con fuentes, incertidumbre y paquete offline. Una coincidencia de IP permite pivotar. Mantén el rechazo de Basic con credencial presentada distinguible de un 401 sin credencial. Aplica plazos a todas las copias y vuelve a aplicar borrados al restaurar.|V2 → «Un caso en cuatro vistas» y «Privacidad, custodia y aceptación independiente». I → «Correlación sin atribución excesiva» y «Uso probatorio en la UE» limitan las afirmaciones del informe y del material comercial.|
|Prioriza sesiones sólo cuando exista habilitación. Conserva la regla visible como baseline. Separa sintético, histórico importado y observado en vivo. Exige etiquetas adjudicadas, derechos por finalidad, features disponibles al corte y evaluación retenida.|V2 → «Del registro mínimo a una decisión asistida»; I → «Leakage, contaminación y generalización». La amplitud de modelos explorados en I no amplía H06.|
|Entrega software, evidencia, reglas, datasets y pesos como activos con permisos y ciclos de vida propios. El cliente puede exigir cero salida. Revisa distribución de código propio, transitivas, frontend, imágenes y GeoIP antes de empaquetar.|V2 → «Entrega, mantenimiento y derechos»; I → «Activos comercializables por separado» y «Licencias y estrategia de componentes». Para las obligaciones aplicables identifica responsable y dictamen humano.|

## 3. Ruta completa de entrega

Usa W/H como unidades. Las PRnn son referencias funcionales heredadas de V2, no números de PR de GitHub que debas crear. La última columna remite a V2 → «Backlog v2 ejecutable» y, para el cierre, a «Entrega, mantenimiento y derechos».

|Hito|Depende de|Objetivo y entregables|Evidencia de salida|V2|
|---|---|---|---|---|
|Reconciliación|Fuentes y checkout|Inventario de brechas sobre HEAD y primer incremento elegible|Cada conclusión tiene ruta, clase de evidencia y prueba o motivo pendiente|Auditoría; base W01|
|Arranque local|Base|Entradas públicas, ejemplos de entorno, loopback, preflight|Checkout limpio ejecuta la interfaz documentada; configuración resuelta correcta|W01|
|Web y reglas|Independientes tras reconciliar|Fixture ASGI y normalizador/clasificador compilable en entregas distintas|Suite web, Vector, casos mixtos y negativos; Geo con base autorizada|W02, W03|
|Contención local|W01|Escritura por productor, cuotas, ACL y migración fría|Reinicio, denegación cruzada y de salida observados|W04|
|Contabilidad|W02, W03|Fixtures deterministas, adaptadores, rechazos y estado de almacenamiento|Recuentos exactos por fuente; replay y rotación sin mezcla de perfiles|W05|
|TFM|W01–W05|Release local, runbook, paneles y export redactado|Segundo operador demuestra ambos perfiles y seis servicios, hueco y recuperación|W06|
|Camino mínimo IT|W06|Listener, agente, colector, recibo y salud|Prueba del 401, corte, duplicado, conflicto, reinicio y ausencia de secretos|H01 / 01,03,06–09|
|Control de flota|H01|Identidad, perfil web, MFA/RBAC, ACL y revocación|Denegación desde VM controlada y entre tenants; corte externo|H02 / 02,04,05,14,16|
|Investigación y custodia|H01,H02|Sesión, grafo, expediente, ZIP, verificador, TTL y restore|E1–E7 reproducido por dos operadores; tercero verifica offline, incluyendo resultados negativos|H03 / 10–12,17–18|
|Distribución candidata|H02,H03|Plugin externo, bundle offline, SBOM, canario y rollback|Instalación limpia, ABI incompatible cerrado, update y reversión sin pérdida|H04 / 13,15,19–21|
|Piloto y decisión|H04, autorización del cliente|Acta de utilidad/capacidad/costes y ejercicio PSIRT|Cliente y responsables acuerdan promoción, corrección o repetición con mediciones|H05 / 22,27|
|Entrega comercial dedicada|H05 favorable y controles aplicables|Release soportada, expediente de derechos/seguridad, soporte, migración, EOL y entrega|Digest entregado coincide con el aceptado; evidencias de repo, instalación y firmas de responsables por criterio|H05 y operación de release|
|ML por cliente|H03,H05 y derechos|Snapshot, evaluación, sombra y retirada|Aplica el criterio retenido del anexo. Si falla, conserva baseline y documenta cobertura|H06 / 23–26|
|Extensiones de modalidad|Necesidad y autoridad específicas|Expedientes separados de gestionado/híbrido y OT|Cruces de tenant y salida verificados o validación OT en entorno simulado; de lo contrario permanecen deshabilitados|H07 / 28 y 29|

## 4. Todas las unidades de trabajo

Ejecuta **U00 · Reconciliar el checkout** al iniciar una sesión nueva sin estado previo. Localiza el repo y las dos fuentes; lee AGENTS.md, RUN.md, .github/workflows/quality.yml y V2 → «Auditoría del repositorio y evidencia». Anota rama y SHA, examina cambios locales sin descartarlos, contrasta las entradas y modos Git, la fixture ASGI, el clasificador y los Compose. Ejecuta las comprobaciones disponibles con versiones declaradas; registra límites del entorno. Devuelve una matriz breve de función documentada / código localizado / comportamiento verificado / pendiente, con evidencia por afirmación. Compara cada brecha con V2 y selecciona la primera PR pendiente cuyas dependencias estén satisfechas. Si ya existe una implementación, corre su aceptación antes de proponer cambios. Cierra U00 con esa selección.

Para el resto, usa **ENTREGAS.md**: W01 arranque; W02 web; W03 Vector; W04 aislamiento; W05 contabilidad; W06 TFM; H01 ingesta; H02 flota; H03 custodia; H04 distribución; H05 piloto; **Cierre H05** release comercial; H06 analítica condicional; H07-G gestionado/híbrido y H07-OT industrial, activables por separado. Cada ficha es un prompt inicial completo para la unidad, con lecturas, pregunta, resultados, aceptación y vuelta. Recibe sólo la ficha que corresponda, conserva el maestro y abre las secciones referenciadas cuando el trabajo las necesite. El cierre H05 desglosa el trabajo aprobado de producto y soporte; no añade una modalidad.

## 5. Ejecución por incrementos y subagentes

Usa 200k tokens como límite operativo por compactación. Conserva en contexto activo el maestro, una ficha, el último registro, el contrato vigente y los resultados necesarios. Deja en el repositorio los diffs, logs y fixtures extensos. Divide la unidad en tantas PR verificables como requiera; ninguna PR depende de que una posterior repare su contrato público.

Prepara cada PR con esta ficha breve:

    Objetivo observable:
    Requisito de origen (W/H, sección, ID del informe si procede):
    Alcance y rutas autorizadas:
    Exclusiones:
    Dependencias resueltas y contrato/versiones:
    Entregable y entrada pública:
    Aceptación (entrada → resultado; regresión que debe fallar):
    Evidencia y reversión:

Eres responsable de contratos compartidos, orden de integración y aceptación final. Delega en paralelo sólo trabajos con resultados independientes. W02 y W03 son un ejemplo. Antes de delegar productor y consumidor, fija el esquema y las fixtures compartidas. Para cada subagente transmite **una pregunta o cambio**, SHA, sección y rutas mínimas de lectura, lista cerrada de archivos editables, interfaz congelada y resultado esperado (diff, prueba, evidencia y duda residual). Si necesita otro archivo o cambiar el contrato, debe devolverte el conflicto. Integra sobre el HEAD actualizado y repite las pruebas cruzadas. Acepta un resultado por el comportamiento observado.

## 6. Continuidad y cierre

Respeta AGENTS.md y las convenciones existentes: GitHub Issues para seguimiento, GLOSSARY.md y docs/adr/ para vocabulario y decisiones cuando corresponda. Comprueba qué archivos existen en el checkout. Usa el mecanismo de estado vigente o la incidencia de la unidad. Si careces de acceso de escritura al tracker, conserva el mismo registro junto a la evidencia de aceptación; evita crear un sistema paralelo de gestión. Guarda resultados sin datos sensibles en acceptance/<id>/ según V2.

Al cerrar cada incremento registra sólo **hito activo · SHA · entregado · pruebas y resultados · bloqueos · siguiente acción verificable**. En pruebas distingue ejecutada/aprobada, ejecutada/fallida y pendiente; enlaza el artefacto. En una reanudación lee esos seis campos, inspecciona el diff desde el SHA, comprueba si siguen válidas las dependencias y retoma la acción. Si falta una decisión del cliente, una base autorizada o una VM, identifica el ensayo concreto pendiente y continúa con las unidades independientes autorizadas. Nunca conviertas un bloqueo en aceptación.

Cierra comercialmente con una matriz criterio → versión/activo → evidencia → responsable → dictamen. Comprueba en repo build, contratos, suites, SBOM, firmas y verificador; en infraestructura instalación offline, ACL, revocación, restore y rollback; en piloto utilidad, capacidad, coste, pérdida y carga de soporte; con los responsables, derechos, aplicabilidad, SLO, soporte, retirada y promoción. Una release candidata conserva ese estado hasta que el expediente acredite las cuatro partes. Etiqueta cada extensión como habilitada con su propia evidencia, aplazada o fuera de alcance.

## 7. Cobertura verificable del informe

En U00 crea o actualiza la matriz en el seguimiento existente. Las filas proceden de «Traspaso para el agente de diseño». Conserva el ID aunque cambie la implementación. Para cada fila añade perfil, PR/commit, evidencia reproducible, resultado, responsable y riesgo pendiente. Separa el ensayo de laboratorio de la aceptación en infraestructura del cliente. Si una fila está aplazada, identifica la condición de apertura. En OPS-CRA-001 el ejercicio usa el escenario del informe y el responsable valida la aplicabilidad y los plazos efectivos para el producto.

|ID|Entrega que responde|Qué debe preservar|Prueba de referencia del informe|
|---|---|---|---|
|**SEC-CONT-001**|W04 → H02|Un sensor comprometido no tendrá ruta de confianza hacia otros sensores, cliente o management; egreso definido por perfil y deny-by-default cuando sea viable.|Root en sensor no alcanza targets prohibidos en prueba adversarial.|
|**SEC-MGMT-001**|H02|Plano web tratado como sistema crítico con MFA/RBAC, audit trail y autorización por objeto/tenant.|Suite de authz y pentest sin cross-tenant/privilege escalation.|
|**TEN-ISO-001**|H02 → H07-G|Todos los objetos y búsquedas estarán tenant-scoped desde persistencia hasta export/ML.|Tests negativos de API, search, exports, caches y pipelines.|
|**OBS-EVT-001**|W05 → H01|Envelope común conservará IDs, esquema, tenant/sensor, tiempos, secuencia, procedencia, raw hash/ref y retención.|Reconstruir una sesión completa y verificar raw↔normalized.|
|**OBS-OFF-001**|H01|Sensores tolerarán desconexión con cola limitada y política documentada de overflow.|Soportar duración de corte objetivo al p99 de carga del piloto.|
|**FOR-PROV-001**|H03|Cada evidencia exportada tendrá procedencia, hashes, manifest, accesos y tiempos/incertidumbre.|Validador independiente detecta cambio de cualquier objeto.|
|**FOR-LIMIT-001**|H03|Documentación declarará que integridad no prueba completitud, reloj correcto ni identidad personal.|Revisión de claims antes de lanzamiento.|
|**TIME-001**|W05 → H01/H03|Registrar observación, recepción, estado/offset/incertidumbre de reloj y secuencia monotónica por boot.|Desfase inducido queda visible y no reordena silenciosamente evidencia.|
|**GRAPH-TRACE-001**|H03|Toda arista tendrá semántica observado/derivado/inferido y referencias a eventos fuente.|Click arista → eventos suficientes para reproducirla.|
|**GRAPH-GAP-001**|W06 → H03|Intentos fallidos y gaps de visibilidad no desaparecerán de la narrativa.|Simulación de caída muestra gap, no continuidad falsa.|
|**PRIV-MIN-001**|W04 → H01/H03|PII/credenciales se capturarán sólo con finalidad documentada y controles/retención por clase.|Data inventory mapea cada campo a finalidad, acceso y retención.|
|**PRIV-ID-001**|H03|IP, fingerprint y credencial no se presentarán automáticamente como identidad personal.|UX usa “origen observado/relacionado”, no “persona”.|
|**OPS-UPD-001**|H04|Sensor/consola tendrán actualización verificable, staged rollout, health check, rollback y EOL.|Upgrade+rollback ejecutado con datos intactos.|
|**OPS-SBOM-001**|H04 → cierre H05|Mantener inventario/SBOM y trazabilidad de terceros para cada release.|Release no sale si SBOM/licencias/CVE gate fallan.|
|**OPS-CRA-001**|H05 → cierre H05|PSIRT soportará obligaciones CRA aplicables y plazos de notificación.|Tabletop desde descubrimiento hasta aviso 24/72 h.|
|**LIC-001**|H04 → cierre H05|Cada componente tendrá licencia, versión/commit y forma de distribución registradas; ninguna “licencia global” ocultará obligaciones de terceros.|BOM de release permite reproducir obligaciones.|
|**UI-SESSION-001**|W06 → H03/H05|Analista podrá ir alerta → sesión/timeline → evento original → artefacto sin buscar manualmente en backend.|≥ objetivo de sesiones del piloto resueltas sin herramienta externa.|
|**ML-LEAK-001**|H06|Ningún modelo usa features posteriores al instante de decisión; splits por tiempo y, para claim de generalización, por cliente/sensor/campaña.|Auditoría automática de feature-time y test final bloqueado.|
|**ML-BASE-001**|H06|Toda capacidad ML debe superar baseline sencillo relevante y reportar coste de error, no sólo accuracy.|Métrica y baseline pre-registrados antes de test.|
|**ML-PRED-001**|H06 / investigación futura|No vender predicción de ataque a infraestructura real sin ground truth externo prospectivo.|Estudio prospectivo en activos reales con horizonte predefinido.|
|**OT-ISO-001**|H07-OT|OT será perfil separado, sin proxy/control hacia proceso real por defecto.|Lab y revisión OT antes de cualquier planta.|
|**PLUG-001**|H04 → H05|“Plug \& play” se medirá como acciones, p50/p90 de instalación y tiempo a primer evento sano en entornos soportados.|Objetivo se fija después del piloto, no antes.|

## 8. Auditoría inicial y ámbito de las decisiones

Reconciliación U00. Recorre «Hallazgos por archivo y tramo» de V2 fila por fila. Registra prioridad, ruta y símbolo actuales, unidad, prueba negativa y estado. Usa «Inventario reproducible de cobertura» como mapa histórico de A, B, C e integración. Si el archivo se desplazó, sigue su función. Distingue la ejecución sobre el SHA histórico, la lectura estática y la comprobación sobre HEAD. En particular, desglosa la contención del laboratorio, la demostración académica y la autorización de tráfico real.

|Parte de la investigación|Decisión que debe tomar el agente|Dónde se comprueba|
|---|---|---|
|Casos blue, red y purple, niveles de interacción|Priorizar triage SOC interno. Usar los ejercicios autorizados y controles benignos para medir cobertura. Internet, alta interacción y OT necesitan decisiones independientes.|W06, H02, H05, H07-OT|
|Sensores, plataformas, competidores e interfaces|Conservar A/B/C como banco de pruebas. Documentar qué patrón se adopta, qué dependencia se redistribuye y su coste. Una ficha comercial sirve de referencia de UX. Cowrie, OpenCanary y los demás candidatos se evalúan por perfil.|U00, W06, H04|
|Arquitectura, despliegue y lenguaje|Verificar guest comprometido, control externo y recuperación. Contrastar stack y recursos con carga y mantenimiento medidos. On-prem dedicado es la primera oferta.|H01–H05|
|Telemetría, privacidad, atribución y grafo|Aplicar la lista de campos del perfil incluso cuando el catálogo de investigación permita más. Probar fuente, tiempo, alcance, incertidumbre, expiración y acceso por objeto.|W05, H01–H03|
|Datasets públicos, reglas, estadística, ML y DL|Por fuente candidata registrar procedencia, licencia, población, etiquetas y sesgo. El caso inicial es priorización local de sesiones. La predicción de actividad en activos reales precisa un estudio distinto.|H06 o aplazado|
|Modalidades, activos y licencias|Separar la entrega del software, evidencia, reglas, features, datasets y pesos. Mantener un dictamen por finalidad y activo. Evaluar explícitamente el modo sin salida al proveedor.|H04, H05, H07-G|
|Riesgos, decisiones abiertas y vacíos de evidencia|Recorrer cada fila de «Matriz de riesgos» y las diez «Decisiones abiertas» del informe. Registrar perfil afectado, control, prueba, propietario, riesgo residual y decisión. En el piloto medir carga, coste, esfuerzo y diversidad con unidad, ventana y tamaño muestral.|U00 abre el registro. H05 lo revisa antes de promoción.|

## 9. Contrato para integración e ingesta · W01–H02

Los cuadros siguientes conservan el contrato de V2. Usa el primero para elegir entorno y dueño, y el segundo al implementar un adaptador. Documenta el tipo nativo, su significado y la versión del mapeo. Los nombres del adaptador legado y el catálogo v1.0 pertenecen a contratos distintos. Prueba la traducción explícita en la frontera.

|Perfil|Camino de datos|Estado y condición de uso|
|---|---|---|
|laboratorio/synthetic|Fixtures etiquetados → Vector → índice propio → Dashboards|Primera comprobación de contrato. Sin listeners de señuelo. Restaurar manifiesto y semilla en ejecución aislada.|
|laboratorio/full|A y B → JSONL por productor → C en RO → índice del laboratorio → Dashboards local|Trabajo del máster con participantes informados, identidades ficticias y red aislada. Tras corregir P0, comprobar los seis puertos, procedencia del ID y topología efectiva.|
|piloto/it-minimo|Listener HTTP → agente con cola local → colector mTLS → transacción PostgreSQL → API privada, consola y custodia|Un cliente dedicado, VM sensor y consola separadas, ACL independiente. Exige un segundo operador y validación de seguridad, política, restauración y borrado. El despliegue no importa históricos sensibles del laboratorio.|
|comercial/on-prem|Mismo contrato de piloto, bundle offline firmado, catálogo de módulos verificados y soporte|Promover por versión tras medir valor, coste y capacidad. Internet, OT, gestionado y redistribución de datos o pesos tienen decisiones de salida independientes.|

A mantiene los servicios y sus fixtures. B mantiene la intranet, simuladores y proyección web académica. C mantiene parseo, enriquecimiento, analítica y paneles. Integración mantiene scripts, contratos versionados y pruebas cruzadas. La custodia y el control de flota tienen propietarios y credenciales separados de los productores. El contrato se cambia mediante PR de integración, con consumidor N−1, fixture y migración. Cada módulo puede seguir probándose aisladamente.

### Adaptación de eventos

|Fuente o campo Winnie|Resultado canónico y condición|
|---|---|
|Cowrie connect / closed, session|connection.open / connection.close; correlación por cliente, sensor, arranque y sesión nativa. Preservar duración declarada y huecos.|
|Cowrie login o login de OpenCanary|auth.attempt con resultado según semántica documentada del productor. Distinguir observado, declarado por señuelo y desconocido. Minimizador descarta usuario y contraseña antes de persistir en perfil IT.|
|Cowrie command / OpenCanary Redis command|command.observed con protocolo y política de captura. Redis conserva semántica de servicio. La entrada emulada no demuestra ejecución en el host.|
|Cowrie file_* / web file_upload|file.observed con dirección, bytes y digest si disponibles. artifact.retained sólo tras confirmación del almacén. Una URL en un comando se representa como intento.|
|Web request, auth_attempt, status, session_id|Una petición con su resultado, vinculada por request_id si genera dos hechos. El 401 sólo constituye rechazo emitido. En perfil Basic registrar por separado presencia de credencial y resultado. El probe sin credencial no activa la regla de presentación.|
|src_ip / geo / usuario declarado|Observables sujetos a política, exactitud y caducidad. Guardar peer frente a valor reenviado de origen validado; GeoIP es enriquecimiento opcional con versión. Unir por coincidencia sólo crea un pivote.|
|@timestamp, event_id, raw, attack_type, mitre_*|Preservar reloj e identidad de origen bajo namespace legacy si se permite. El colector añade received_at, sensor/boot/sequence y recibo. raw no pasa automáticamente. MITRE y attack_type son anotaciones de regla versionada con evidencias.|
|Sin correspondencia o sin telemetría|Guardar motivo de desconocido o rechazo acotado; contador por productor y versión. Un campo omitido por política y un valor perdido por fallo reciben motivos diferentes.|

**Frontera de persistencia.** Para el piloto el listener emite un esquema cerrado con clase, resultado, sesión técnica y perfil aplicado. Excluye texto libre de cabeceras, consultas, cuerpos, credenciales, nombres de fichero y terminal. El agente asigna UUID, boot y secuencia una sola vez, y conserva los bytes exactos en SQLite WAL con volumen cifrado. POST /v1/batches autentica sensor y obtiene tenant del certificado. Una transacción valida identidad y tamaño, guarda bytes, hash SHA-256, metadatos de adquisición y recibo. ACK por registro tras commit. Duplicado idéntico devuelve el primer recibo, colisión de contenido abre incidencia. El cursor de publicación de cualquier índice secundario sólo avanza tras proyección confirmada. Reiniciar el proyector permite reconstruirlo con IDs estables. Las lecturas de evidencia consultan el almacén de custodia.

**Compatibilidad.** Congelar un manifiesto de muestras legado con hash por fichero. Identificar línea por ordinal al importar la instantánea. En streaming nuevo, encolar identidad y registro atómicamente; el offset de tail por sí solo no sobrevive a reutilización de archivo. Guardar versión de contrato y de adaptador, política, fuente y clase de procedencia (sintética, importada histórica o en vivo). Un dato legado carece de recibo contemporáneo hasta su importación: el nuevo recibo fecha la adquisición del fichero. Migración aditiva, doble lectura limitada por versión, backfill sólo de material autorizado. Reversión por alias de lectura, con fuentes de cada perfil separadas. Prohibir rehidratar campos eliminados o caducados.

**Salud y control.** Límites iniciales de ensayo heredados: 64 KiB por ítem, 100 ítems y 1 MiB por lote, cola 256 MiB, latido cada 10 s, aviso a tres periodos. Medir y ajustar antes de acordar SLO. Registrar producidos, admitidos, repetidos, impugnados, descartados por política, perdidos y proyectados por sensor, boot e intervalo. Reserva de incidencias al llenar la cola; pérdida de magnitud desconocida si falla el contador. Revisiones desired/applied/error con If-Match. Configuración por formulario generado desde manifiesto firmado, nunca shell remota. Aprovisionar con token de un uso, validación de huella, certificado corto y revocación inmediata. La API privada aplica OIDC/MFA y permisos por objeto y operación, también al descargar exportaciones. Latido desde el guest, temporizador del colector y monitor de red se muestran como fuentes distintas.

**Vista del analista.** El dashboard académico conserva serie temporal, servicios, reglas, mapa y sesiones; datos sintéticos explícitos en paneles de contraseñas y payloads. El panel de piloto muestra origen autorizado, cobertura y motivo de alerta. Tabla de aristas con ID de fuentes como primera interfaz de grafo. El caso IT de aceptación conserva E1–E7 del adjunto: conexiones A y B independientes, una presentación ficticia seguida de 401 en A, latido, silencio observado por colector, nuevo arranque y recuperación. B queda sin cierre observado. El analista puede elegir actividad prevista, investigar o visibilidad insuficiente y citar evidencias. La IP común no fusiona las sesiones. Un desfase +300 s mantiene hora original e incertidumbre visible.

**Custodia y privacidad.** El custodio selecciona caso y watermark, enumera miembros, hash y tamaño, firma el manifiesto con clave separada y registra destinatario, propósito y caducidad. El verificador offline obtiene su raíz por otro canal, comprueba miembros exactos y referencias, rechaza rutas ambiguas y contenido alterado, y distingue íntegro, inválido e íntegro con salvedades. El fixture E1–E7 exige salvedad de reloj/cobertura. La firma acredita los bytes recibidos, y una declaración del sensor comprometido puede ser falsa. Aprobar antes del piloto una tabla de TTL y responsables para originales, proyecciones, logs de servicio, errores, colas, exportaciones, cuarentena, backups y datasets. Al restaurar, reaplicar el registro de borrados antes de servir. Los 30 días del índice legado y los 7 días del fixture IT son valores de perfiles distintos. El responsable del tratamiento debe aprobar los plazos reales y el procedimiento de acceso y retirada.

**Analítica y comercialización.** El baseline académico son reglas versionadas, con controles inocuos e identidades ficticias. La tarea ML inicial es ordenar sesiones para un presupuesto de revisión fijado por el SOC. Etiqueta adjudicada por analista, con desacuerdos y abstenciones. Registrar qué sabía en ese instante y excluir del entrenamiento los intervalos impugnados, el texto de cierre futuro, la etiqueta de escenario y los IDs del generador. Congelar dataset con finalidad y vencimiento, particionar por tiempo y agrupar sesión/campaña; reservar sensor o cliente externo cuando exista. Comparar regla y modelo clásico con precision@K, cobertura de relevantes, minutos por caso e intervalos por grupo. Si el candidato mejora sólo en sintético, se mantiene en investigación. En piloto la inferencia va en sombra con vuelta al baseline. DL necesita evidencia de señal secuencial frente a ablación, volumen, derechos y coste; predicción de compromiso real requeriría resultados externos prospectivos. Emitir fichas y permisos separados para software, dataset y pesos. El permiso de soporte de un cliente no habilita entrenamiento global ni redistribución.

### Fixture de conformidad y contrato de lectura

El original es el registro mínimo exacto emitido por el productor autorizado después de minimizar en origen. La solicitud HTTP completa nunca entra en la cola. El registro de adquisición vincula esos bytes al contexto de transporte y al recibo. Preservar por separado original, contexto de adquisición, proyección normalizada y anotaciones. Prohibir la recodificación de originales al reintentar o exportar. Ejemplo normalizado de E2, con identificadores opacos de fixture admitidos por v1:

```json
{
  "schema_version":"1.0","event_id":"E2","tenant_id":"T1","sensor_id":"S1",
  "boot_id":"B1","sequence":2,"session_id":"A","parent_event_id":"E1",
  "kind":"auth.result","observed_at":"2026-11-25T10:00:02Z",
  "received_at":"2026-11-25T10:00:03Z",
  "clock":{"state":"synced","offset_ms":0,"uncertainty_ms":50,"source":"ntp-1"},
  "provenance":{"producer":"http-decoy","version":"1.0.0","build":"fixture-1","config_ref":"P1","collector":"C1","receipt_id":"R2"},
  "raw_ref":"raw/E2.json","raw_sha256":"e6f1ff7bad3441c854f26f24c0bc948fe0d819a190d2b580c8b8faac24db6e89",
  "sensitivity":"restricted","purpose":"incident-triage","policy":"IT-7d-v1",
  "expires_at":"2026-12-02T10:00:03Z",
  "data":{"method":"basic","outcome":"failed","status":401}
}
```

Bytes del original E2, UTF-8 sin salto final: `{"kind":"auth.result","method":"basic","outcome":"failed","status":401}`. P1 resuelve a una instantánea inmutable de configuración con digest SHA-256 en el registro de adquisición. El recibo firma o se incluye en un lote firmado que cubre hash del contexto, del original y reloj de recepción. El event_id real es UUID aleatorio estable asignado una vez; la unicidad se impone dentro de la identidad autenticada. Cada nuevo arranque asigna boot_id único incluso tras restaurar snapshot; reingreso obligatorio si se clona un sensor. Reutilizar una misma conexión HTTP keep-alive conserva session_id; conexiones diferentes crean sesiones diferentes.

|Grupo|Contrato del escritor y del lector|
|---|---|
|Identidad y origen|IDs UTF-8 opacos, no vacíos y acotados, sequence entero positivo creciente por productor/boot. Tenant y sensor derivan de la identidad autenticada; una discrepancia rechaza el ítem. Para datos de control, sensor_id es el sensor afectado y el productor es el colector, con su propio boot/contador y namespace de secuencia. Nunca permitir que el guest emita un hecho de autoridad del colector.|
|Tiempo y orden|Tiempos RFC 3339 UTC. Observed_at obligatorio como clave, nullable con motivo machine-readable; received_at siempre lo asigna el colector en primer commit. Offset = reloj de sensor menos referencia en ms; incertidumbre no negativa o null si se desconoce. Mostrar intervalo aproximado observado − offset ± incertidumbre, conservar valor declarado. La cola puede explicar una recepción tardía. Orden local por secuencia dentro de boot, entre productores por recepción para presentación, con aviso si el orden real es ambiguo.|
|Procedencia y contexto|Versión de esquema mayor.menor, enum kind, versión/build/config del productor, referencia al recibo, bytes y hash SHA-256 hex de 64 dígitos. Sesión obligatoria en eventos de interacción y null en salud global. Padre opcional o null; pendiente si llega después. Estado de red por campo con motivo (desconocido, redactado, no aplicable); jamás fabricar IP o usuario.|
|Política|Finalidad, clase, policy revision y vencimiento calculados en colector. Etiqueta más restrictiva ante conflicto. El scope de export y acceso se recalcula al leer. Campos nuevos requieren revisión del inventario.|
|Evento tardío|Conservar recepción inicial y secuencia; insertar en posición lógica con marca «recibido después». Crear revisión nueva de la vista. Un export previo sigue ligado a su snapshot. Hueco de secuencia pendiente puede cerrarse; el intervalo de falta de latidos sigue documentado.|
|Errores|Sin identidad, bytes, secuencia o contrato reconocido, rechazo y contador con motivo, sin registrar payload libre. Información optativa ausente queda nula con motivo. Misma identidad con otro contenido o secuencia reutilizada pone la entrada en conflicto, preserva el recibido válido e impugna la fuente.|

Catálogo MVP: network.connection.start/end cuando se observa, protocol.request/response agrupables como resultado de solicitud, auth.result, sensor.lifecycle/heartbeat, clock.sync, config.change, admin.action, collector.receipt, evidence.access/export/seal y observaciones de visibilidad del colector. Reservar familias tipadas session.input/action, file.transfer, artifact.*, process/system.action, network.egress.attempt y correlation.created para capacidades que aporten fuente real. La aceptación de un tipo exige esquema de payload, productor autorizado y política. Conexión incluye tupla y dirección observadas, interfaz y NAT sólo si se conoce; end incluye bytes disponibles y causa observada. Auth guarda presencia, método y resultado; no material de credencial.

## 10. Contrato para SOC, interfaz y custodia · H02–H03

Implementa DEMO-1 como caso de aceptación reproducible. Contrasta las cuatro representaciones con los mismos siete originales, el mismo corte y la misma revisión de reglas. En la revisión del PR adjunta la navegación desde alerta hasta original y la salida del verificador ejecutado por un tercero con una raíz obtenida por separado.

**Eventos.** Extracto cerrado del caso T1/S1: siete registros fuente. Los recibos y el audit trail son metadatos asociados; la regla de alerta es derivada. El sensor termina abruptamente con dos conexiones aún abiertas. El cliente mantiene abiertas las conexiones sintéticas hasta el corte. Último latido en el mismo lote que E3. Hora UTC del 25-11-2026; «+1» significa que el colector recibió un segundo después.

|ID|Productor / boot:seq|Sesión|Observación del productor|Hora observada / recepción|Original|
|---|---|---|---|---|---|
|E1|S1 B1:1|A|Conexión HTTP desde 192.0.2.8:50101 a 192.0.2.20:8080, interfaz decoy0|10:00:01 / +1|raw/E1.json|
|E2|S1 B1:2|A|Credencial Basic presentada, autenticación denegada, 401|10:00:02 / +1|raw/E2.json|
|E3|S1 B1:3|B|Segunda conexión TCP al puerto HTTP desde 192.0.2.8:50102, sin solicitud registrada|10:00:05 / +1|raw/E3.json|
|E4|S1 B1:4|—|Latido, plugin sano, cola 0 en la muestra|10:00:05 / 10:00:06|raw/E4.json|
|E5|C1 BC:1|—|watchdog registra vencimiento de latido, último E4|10:00:36 / 10:00:36|raw/E5.json|
|E6|S1 B2:1|—|Arranque nuevo, reloj adelantado 300 000 ms, incertidumbre 2 000 ms|10:06:00 / 10:01:01|raw/E6.json|
|E7|C1 BC:2|—|Colector registra primera recepción tras el aviso, referencia E6|10:01:01 / 10:01:01|raw/E7.json|

**Cronología.** A las 10:00:03 el SOC recibe la alerta derivada de E2 y abre A. E1→E2 es orden de emisión dentro de B1. B queda como «sin continuación observada al corte». A y B comparten la IP observada; un proxy corporativo explicaría el mismo dato. Entre la última recepción de latido a las 10:00:06 y la nueva recepción a las 10:01:01 la visibilidad queda en duda. El aviso comienza a las 10:00:36; esos dos intervalos se muestran diferenciados. A partir de E6 se observa otro boot. Hora corregida orientativa de E6: 10:01:00 ±2 s. La caída física sólo la conoce quien ejecuta la prueba; estos eventos por sí solos acreditan silencio, recuperación y reinicio declarado.

**Grafo.** Nodos con clave (tenant,tipo,id): Tenant, Sensor, Asset señuelo, Session, Connection, Action, Observable, intervalo de visibilidad y Case. IdentityClaim y Artifact se crean sólo cuando hay observación admisible. Una arista contiene source, target, tipo, semántica, evidence_ids, revisión de regla o modelo, fecha de cálculo y, para inferencias, justificación, alternativa y confianza calibrada o «sin calibrar». La API exige al menos una fuente resoluble o una lápida de expiración. Consultar por caso y corte con presupuesto de nodos y cursor. En la tabla, cada ID abre el detalle y éste el original autorizado con su recibo.

|Desde → hacia|Relación y semántica|Fuente del caso|Interpretación|
|---|---|---|---|
|Conexión A → servicio HTTP; conexión B → servicio HTTP|CONNECTED_TO, observado en sensor|E1; E3 respectivamente|Dos puertos de origen distintos.|
|Acción 401 → sesión A|PART_OF_SESSION, observado|E2|Resultado fallido visible.|
|Sesión A → sesión B|SHARES_SOURCE, derivada por igualdad de la IP, regla ip-eq/1|E1,E3|Pivote técnico; ninguna conclusión sobre una persona.|
|Rama B → estado al corte|NO_FURTHER_OBSERVATION, derivada por consulta acotada al snapshot|E3,E4,E5,E7 + corte|Sin petición ni cierre observados en esa rama.|
|S1 → intervalo; intervalo → recuperación|VISIBILITY_GAP, derivada por timeout/1|E4,E5,E6,E7|Silencio y recuperación; causa pendiente.|
|Caso → hipótesis de origen compartido|INFERRED_RELATED_TO, opcional, anotación del analista|E1,E3|Podría ser un mismo equipo o varios tras NAT. Sin calibrar; oculta por defecto y nunca fusiona sesiones.|

**Extracto de informe exportado, caso DEMO-1, corte 10:01:02Z.** «Dos conexiones observadas en S1. Una autenticación denegada en A [E1,E2]. B carece de continuación observable [E3–E5,E7]. El colector documentó falta de latidos y una nueva recepción [E4–E7]. E6 declara desfase +300 s. La IP justifica consultar el inventario interno. Decisión: abrir investigación; identidad y actividad durante el silencio indeterminadas». El paquete incluye las siete referencias anteriores y la revisión de reglas. Un informe también muestra clases no instrumentadas, redacciones y originales expirados. Si un caso tiene un artefacto autorizado, el enlace pasa de evento a metadatos, hash y objeto de cuarentena; en DEMO-1 la vista muestra «ningún artefacto recogido».

|Pantalla / rol|Pregunta y acción|Permiso mínimo|Estado vacío, incompleto o degradado|
|---|---|---|---|
|Configuración / administrador|¿Qué se aplicó? Comparar revisiones, preflight, aprobar perfil, revertir a revisión firmada.|fleet.write, MFA reciente|Sin sensor: asistente. Offline: aplicado anterior, pendiente y antigüedad.|
|Salud / operador|¿Dónde dejó de fluir? Comparar latido, cola, reloj, ingestión y raíz independiente; aislar mediante rol de respuesta.|fleet.read; revoke separado|Distingue nunca visto, plugin caído, silencio, revocado, DB inaccesible y cola desconocida.|
|Logs / analista|¿Qué recibió el colector? Filtros, paginación, abrir evento y recibo.|events.read; raw.read por caso|Distingue cero coincidencias, sin permisos y datos caducados sin revelar objetos ajenos.|
|Actividad / jefe SOC|¿Cuántas sesiones y fallos por ventana? Cambiar hora de observación/recepción y abrir registros.|metrics.read|Ventana sin cobertura se sombrea; cero sólo con cobertura conocida. Mostrar última actualización y filtros.|
|Sesión / analista|¿Qué justifica escalar? Alerta → línea temporal → original → artefacto; registrar decisión.|sessions.read, case.write; permiso adicional para original|Corte, falta de cierre, reloj incierto, muestra tardía o expiración claramente visibles.|
|Grafo / DFIR|¿Qué une las sesiones? Seleccionar arista, listar fuentes, alternar inferencias.|graph.read, events.read|Sin relaciones: sesión aislada. Paginación y fuentes vencidas visibles; etiqueta temporal en cada consulta.|
|Exportación / custodio|¿Qué entrego y con qué alcance? Elegir corte, motivo y destinatario, generar, descargar, verificar.|export.create y raw.export explícito, MFA reciente|Pendiente, expirado, denegado, parcial por expiración o firma fallida; fallo de firma bloquea descarga como sellado.|

### Privacidad, custodia y aceptación independiente

Antes de captar tráfico real el responsable aprueba inventario de campos, finalidad, base de licitud, necesidad, transparencia, roles y, cuando corresponda, evaluación de impacto, acuerdo de encargo, residencia y transferencias. Un permiso para prestar el servicio no autoriza entrenar, publicar o revender. Política inicial H4 para laboratorio/piloto propuesta al responsable: 7 días para caso técnico, 30 para operación y 90 para custodia. Son máximos de configuración propuestos, revisables a la baja y sujetos a justificación específica; al faltar aprobación se opera sólo con sintéticos. El vencimiento de cualquier derivado está acotado por sus fuentes salvo finalidad y política independientes aprobadas. Bloqueo de conservación por caso, autorizado, con motivo, caducidad/revisión y liberación auditada.

|Clase y origen|Finalidad y sensibilidad|Acceso y destino|Retención propuesta|
|---|---|---|---|
|IP/puerto/socket, destino, interfaz del plugin|Triage y pivote, identificadores potencialmente personales|Analista del tenant, export por caso al custodio autorizado|7 d; NAT anterior/posterior desactivado salvo fuente de red autorizada, misma política.|
|Nombre declarado, cabecera Basic, contraseña, cookie, query, cuerpo|Datos de alto riesgo. Para esta regla basta presencia de método y rechazo.|Sólo tratamiento transitorio mínimo en listener. Sin eco, volcado, hash de contraseña ni log del proxy.|0 persistencia; resultado minimizado 7 d.|
|Comandos/input/TTY, ficheros, payloads, PCAP|Pueden contener secretos, malware o datos de terceros|Desactivados. Perfil futuro de caso con vault local, custodio y acceso explícito, contenido sin ejecución ni previsualización activa.|0; excepción futura con TTL aprobado por clase y caso antes de habilitar.|
|Banner/fingerprint, ASN/geolocalización, NAT|Enriquecimiento potencialmente identificativo, dependiente de punto de observación|Desactivado; futuro scope local analista, fuente/algoritmo/versión obligatorios. Identidad personal nunca se calcula.|0 por defecto.|
|IDs, versiones, perfil, boot, secuencia, reloj del guest y recibo del colector|Procedencia y tiempo; infraestructura sensible|Analista/custodio del tenant; recibo por referencia|7 d con evento, metadatos de salud 30 d bajo política distinta.|
|Original minimizado y proyección|Reconstrucción de caso; hereda sensibilidad de campos|Custodio o raw.read justificado para original, analista para proyección, local|7 d ambos; extensión específica para investigación.|
|Latidos, colas, disco, contadores de egreso, cambios de perfil y fallos|Disponibilidad y contención; infraestructura restringida|Operación de cliente; diagnósticos sanitizados y exportados sólo con aprobación|30 d. Claves privadas fuera del log y del bundle.|
|Accesos, sellos, cambios de privilegio y cadena de custodia|Rendición de cuentas; actores y casos sensibles|Auditor/custodio, copia de auditoría con acceso independiente|90 d bajo aprobación; recibos de entrega conservan sólo referencias necesarias.|
|Grafo, anotaciones humanas, inferencias|Triage, hipótesis y decisión; heredan sensibilidad|SOC local, hipótesis identificada por autor y fuentes|Hasta 7 d o plazo del caso justificado.|
|Features, etiquetas, datasets, pesos|Entrenamiento local opcional; riesgo de reidentificación/memorización|Sin extracción en MVP; analista ML de cliente sólo con permiso específico. Publicación/redistribución separadas.|0 por defecto; snapshot y modelo exigen fecha de revisión, expiración y procedimiento de retirada propios.|
|Paquete, copia externa y backup|Entrega DFIR o recuperación; sensibilidad máxima del contenido|Receptor documentado, backup cifrado separado por tenant y claves locales|Descarga disponible 24 h (H4); receptor pacta conservación. Backup rotativo 7 d propuestos. Registrar entrega; una copia entregada escapa al borrado técnico del proveedor.|

Un job aplica expiración a originales, proyecciones, búsquedas, cachés y features; actualiza aristas y vistas con lápidas mínimas. A la restauración aplica de nuevo borrados y revocaciones desde registro protegido antes de abrir consultas. Credenciales se rotan sin perder la clave pública histórica. Toda lectura sensible, intento de exportación y entrega genera actor, rol, caso, finalidad, objeto, hora, decisión y hash del manifiesto cuando exista. Si no se puede auditar, bloquear lectura sensible. Custodia registra quién obtuvo el paquete, cuándo, cómo verificó y a quién lo entregó; el destinatario continúa su propio registro.

**Formato evidence/1.** ZIP sin cifrado ad hoc, entregado por canal cifrado aprobado o soporte cifrado. Nombres relativos UTF-8 listados exactamente, una entrada por nombre. En el caso de ejemplo:

|Ruta|Contenido obligatorio|
|---|---|
|manifest.json, manifest.sig|Bytes UTF-8 exactos de manifiesto y firma Ed25519 separada sobre esos bytes. Formato, tenant/caso, corte por watermark de commit, emisor, key_id, propósito, alcance, modo completo/parcial, clases omitidas, versión de exportador y lista ordenada de path, bytes y SHA-256 de **cada otro miembro** salvo estas dos entradas.|
|keys/export.pub, keys/receipt.pub, trust.json|Claves públicas e IDs, periodos, rotaciones y referencias al anclaje independiente. Las copias son informativas; raíz y política de revocación se obtienen fuera del ZIP.|
|raw/E1.json … raw/E7.json|Bytes exactos minimizados por productor. Si falta uno, el manifiesto declara el ID, el motivo y el modo parcial. No se genera un archivo vacío que simule el original.|
|acquisition.ndjson, receipts.ndjson, receipts.sig|Contexto por ID: sensor/productor, huella cert, boot/seq, tiempos, build, política, hash original/contexto. Recibos exportables firmados por custodia al sellar lote de adquisición; exportar pruebas firmadas del lote o firma por registro para el subconjunto, sin datos ajenos. En v1 usar firmas por registro en receipts.sig, ligadas a ID y key_id.|
|events.ndjson, edges.ndjson, clocks.ndjson, gaps.ndjson|Proyección y versión, aristas y fuentes, muestras de reloj, intervalos y base de cálculo. IDs y digests deben enlazar con adquisición.|
|profiles.json, rules.json, schemas.json|Configuraciones efectivas sanitizadas con digest, definiciones de regla/transformación y versiones de formatos suficientes para repetir la proyección.|
|audit.ndjson, custody.ndjson, report.md, README.txt|Accesos y custodia hasta el corte de exportación, solicitud, identidad del exportador y procedimiento offline; informe legible con incertidumbre. Entregas posteriores son recibos externos referidos al hash del manifiesto, evitando autofirma circular.|
|artifacts/sha256/&lt;digest&gt;|Sólo si existe y se incluye con permiso; en el ejemplo, cero archivos. Si se omite, se enumeran la referencia, el motivo y el hash si está disponible.|

**Prueba de un tercero.** Recibir por canal separado clave/huella raíz del cliente, estado histórico de claves y verificador firmado con guía de formato. En máquina offline, verificar primero el binario por la raíz de distribución. Rechazar rutas absolutas, traversal, symlinks, entradas duplicadas, expansión excesiva, miembros inesperados y claves sin confianza externa. Verificar firma del manifiesto, hashes y tamaños, las firmas de recibo y sus enlaces raw→acquisición→normalizado, relaciones, perfiles, auditoría y watermark. Recalcular la proyección documentada de los originales. Entregar un resultado por eje: firma/confianza, integridad de bytes, trazabilidad, cobertura del alcance solicitado y calidad temporal. Política de salida del CLI: 0 verificable sin reservas, 2 verificable con salvedades, 1 fallo de integridad/confianza/estructura. Recibo no sellado impide marcar export «verificado». Usar recibos sellados fuera del guest y anclaje independiente periódico para detectar una reescritura anterior a exportar; documentar la ventana hasta el anclaje.

|Ensayo offline sobre DEMO-1|Resultado exigido|
|---|---|
|Paquete intacto y raíz conocida|Firmas y siete originales válidos; salvedades por E4–E7, exit 2. Informe de cobertura incluye los siete registros del snapshot y el intervalo sin visibilidad.|
|Cambiar un byte de raw/E2.json conservando manifiesto y firma|Firma de manifiesto puede seguir válida. Hash del miembro y enlace al recibo fallan; indicar archivo e ID, exit 1.|
|Desfasar el sensor antes de adquirir E6 y exportar normalmente|Integridad válida, offset +300 s e incertidumbre visibles en UI, clocks e informe, exit 2. El reloj se corrige sólo en presentación.|
|Sustituir paquete entero y clave interna por otra autofirmada|Falla confianza frente a raíz externa, exit 1, incluso si coinciden todos los hashes.|
|Un evento plausible fabricado desde sensor válido|Puede pasar integridad. Estado «declarado por S1» y contraste independiente si existe. La firma no acredita identidad humana, completitud, corrección del reloj ni admisibilidad judicial.|

## 11. Contrato experimental, promoción y retirada · H06

La primera función de priorización es una regla visible: abrir revisión cuando el señuelo deniega una credencial presentada; un GET sin credencial no dispara por sí solo la misma alerta. Registrar versión y fuentes y permitir ver todas las sesiones. El primer objetivo ML de piloto es **ordenar sesiones para revisión del SOC local**. La pregunta es si el analista dedicará una de sus plazas de revisión a esa sesión. El coste de equivocarse es tiempo perdido o un caso relevante relegado. No se automatiza el cierre de casos.

|Elemento|Contrato de experimento|
|---|---|
|Unidad, instante, horizonte|Una sesión. t = 30 s después de la primera recepción en colector; generar una sola puntuación sobre hechos recibidos hasta t. Horizonte operativo: cola de revisión del siguiente turno de 8 h (H5, ajustar con SOC antes de congelar). Etiqueta según revisión adjudicada de ese turno; fuera de ventana o sin resolver = desconocida.|
|Entrada / salida|Secuencia canónica del prefijo, cuentas de conexiones/peticiones/fallos, intervalos disponibles y cobertura al corte. Salida: score de prioridad, versión, instante, fuentes y razones; abstención si hay gap relevante, fuente impugnada o esquema desconocido.|
|Etiquetas|Dos revisores, ciegos a score, con adjudicación del desacuerdo. Positivo = merece investigación externa justificada; negativo = actividad prevista confirmada por inventario/calendario del cliente. Retener motivo, fuente, etiqueta, versión y fecha de disponibilidad. Sin confirmar queda sin etiqueta. Muestrear también sesiones sin alerta; reportar cobertura y acuerdo.|
|Captura ahora / activación posterior|Ahora registrar secuencia, doble tiempo, revisiones de regla y configuración, salud, boot, cobertura y decisiones con evidencia. En piloto añadir anotación doble, instantánea de derechos, features y clasificación en sombra. Datos sintéticos identificados y excluidos del test de eficacia.|
|Baselines|Orden cronológico y regla 401 + desempate por recepción. Comparar con regresión logística regularizada; presupuesto K de revisiones por turno fijado con cliente antes del test. Métrica primaria: casos adjudicados positivos entre K revisiones; secundarias: recall de relevantes, minutos por caso confirmado, coste por falso negativo y calibración si se muestran probabilidades.|
|Corte y fuga|Train inicial, validación posterior para hiperparámetros/umbral y test final futuro bloqueado. Embargo de al menos horizonte de etiqueta más máxima ventana histórica usada; campañas/familias casi duplicadas en una sola partición, purgar solapamientos, transformadores ajustados sólo con train. Separar sensor retenido entero; para alegar transferencia entre clientes, cliente completo retenido y permiso previo. Ningún ID, IP, tenant, case_id, dictamen, credencial, cierre futuro o tag de ejercicio como feature.|
|Prueba negativa|Inyectar un evento con observed_at anterior y received_at > t y otra feature que codifique el cierre del turno. El constructor debe conservar inalterado el vector del prefijo y rechazar la columna futura. Auditar feature→filas fuente→available_at. Si grupo compartido cruza splits, abortar.|
|Diversidad y criterio|Medir clientes/sensores/protocolos, turnos y periodos independientes, positivos/negativos/desconocidos, campañas deduplicadas, familias, drift, coste de etiquetado y curva de aprendizaje. Comparación pareada por turno con intervalos por bloques temporales/campaña. Promover sólo si límite inferior del 95 % de mejora en positivos@K > 0 en futuro y sensor retenido, sin empeorar recall crítico ni coste acordado. Muestras insuficientes dejan la regla activa.|

**Ciclo reproducible.** Snapshot Parquet inmutable y manifest firmado por tenant (hash de consulta, filas, intervalos, licencia, usos, clase, vencimiento y splits). Registrar imagen de entrenamiento por digest, revisión de código, semilla, lockfile, CPU y tolerancia numérica. Entrenar → guardar parámetros y vector de prueba → evaluar una vez sobre test congelado → registrar ficha y dictamen firmado → ejecutar localmente en sombra → aprobar alias activo por tenant → comparar por turno drift, cobertura, abstenciones, latencia, precisión adjudicada y coste. Si vence permiso, cambia esquema, sube coste más del umbral acordado o cae por debajo de regla en dos ventanas revisadas, desactivar alias y volver a regla; registrar incidentes, revocar descarga y revisar copias y reentrenamiento por contrato. Si sólo hay datos de un cliente, la alegación de generalización queda acotada a sus sensores.

**Puerta para DL.** Antes de gastar GPU: secuencias suficientemente largas para que orden aporte señal en ablación, diversidad de periodos/sensores y etiquetas para calcular intervalos en cada holdout; dos ampliaciones sucesivas del train con mejora del clásico inferior al mínimo útil fijado por el SOC; análisis de errores que identifique patrón secuencial con casos independientes; derechos de entrenamiento y presupuesto de latencia/coste firmados. Si falta cualquiera, continuar con regla/clásico. Sólo experimentar con DL bajo el mismo test prospectivo reservado para una nueva ronda, baseline, coste y control de memorización. La clase «ataque futuro a activo real» requeriría otro estudio prospectivo con EDR/NDR/SIEM y horizonte predefinido.

## 12. Contrato de producto y expediente de cierre · H04–H07

|Activo|Entrega y despliegue|Permiso o titularidad que debe constar|Firma, actualización y reversión|Soporte y fin de vida|
|---|---|---|---|---|
|Sensor|OCI por digest, agente y unidad systemd, plantillas de ACL y guía local|Licencia del producto, avisos por dependencia, autorización del segmento y mapeo a tenant|Raíz offline, canario por zona, revisión previa aún compatible con WAL y configuración|Matriz de SO/ABI, parches y canal PSIRT; al retirar revocar y eliminar claves.|
|Consola|Bundle de servicios y UI estática offline, backup/restore; on-prem dedicado. Gestionado sólo tras gate|Licencia software + IAM del cliente; encargo y subencargados según roles si gestionado|Firma de release y SBOM; migración expandir→leer ambas→contraer en release posterior. Volver al binario compatible o restaurar snapshot con journal de borrados|Publicar versiones, calendario de soporte y procedimiento de export/migración antes de EOL.|
|Reglas y perfiles|JSON declarativo local, catálogo firmado, versiones conservadas para reproducibilidad|Licencia de reglas e IOC; derechos de terceros documentados|Digest por regla, sombra/canario, volver a revisión anterior|Registro de cambios y retirada de regla defectuosa; informes históricos conservan versión.|
|Informes y evidencia|Markdown, NDJSON y ZIP evidence/1 a destinatario designado|Cliente controla autorización, base y destinatario. Registrar cadena de custodia|Firma cliente y hashes; corrección emite nuevo informe enlazado, sin sobrescritura ni recuperación de copias entregadas|Validador offline, claves públicas históricas y especificaciones compatibles tras EOL.|
|Datasets|Parquet + manifiesto/diccionario/ficha de origen; local, exportación opcional|Permisos separados de servicio, investigación, entrenamiento por cliente/global y redistribución. Confirmar licencias y reidentificación|Versiones inmutables firmadas; deprecar versión, revocar accesos futuros, reconstruir sin fuente retirada|Contacto de incidencias, caducidad, registro de receptores y obligaciones de borrado.|
|Pesos de modelos|Artefacto declarativo de coeficientes o formato aprobado sin deserialización ejecutable, ficha y vectores de prueba; inferencia local|Derecho a entrenar y comercializar pesos, evaluación de memorización y contrato por ámbito|Registro firmado y alias por cliente, canario/sombra, rollback a versión válida o regla|Vigencia, vigilancia de drift, retirada y notificación; pesos ya entregados sujetos a contrato.|

**Operación sin telemetría al proveedor.** Raíces, identidad, reloj, métricas, firmas de evidencia, backups y modelos residen en el cliente; importar actualizaciones en soporte verificado por canal separado. UI sin CDN, analytics, crash reporter, fuentes remotas ni verificación online obligatoria. Soporte mediante reproducción sintética o exportación manual sanitizada y aprobada; con prohibición total se usa sólo reproducción sintética. Probar con WAN bloqueada y contadores externos de conexiones durante instalación, error, investigación, export y actualización. Actualizaciones salientes del proveedor no dan acceso entrante al cliente. Híbrido requiere contrato de campos y destinos permitido; features y salud también pueden identificar. Gestionado añade DPA cuando proceda, residencia, respuesta a brechas y evaluación sectorial (p. ej., aplicabilidad de NIS2).

**Operación de release.** Inventario de versión/commit, origen, licencia, avisos, modificaciones y forma de distribución por componente, incluidas transitivas y frontend. Bloquear dependencias sin decisión de licencia y vulnerabilidades fuera de política. En cada release publicar SBOM SPDX, procedencia de build, digest y firma; mantener claves offline de raíz y delegación revocable, impedir downgrade a versión vetada. Rollback sólo a conjunto permitido. Contrato comercial fija periodo de soporte, fecha EOL, notificación y SLA conforme a evaluación jurídica; responsable PSIRT y suplente ensayan recepción CVD, triaje, mitigación, avisos iniciales 24 h y seguimiento 72 h **para los supuestos aplicables** del art. 14 CRA, y cierre en plazo correspondiente al tipo de incidente. Conservar acuses y cronología. El cliente valida recuperación de backup con sus propias claves y ensaya pérdida del host de consola.

**Acta de piloto.** Vincula la aceptación técnica a la decisión del comprador. Aplica H05 de ENTREGAS.md. Documenta entorno y muestra, tareas de los dos operadores, comparación ciega, instalación y tiempo al primer evento sano, pérdida y recuperación, esfuerzo de soporte y coste. Expresa por separado resultados observados, objetivos acordados y mediciones pendientes. Registra quién acepta qué versión y qué hallazgo exige repetir el piloto.

**Control antes de relevar.** Para la unidad activa selecciona las filas aplicables de §7, el caso de la ficha y los límites de §§9–12. Registra para cada prueba el resultado esperado y el observado. Una prueba de firma correcta puede coexistir con un hueco de observación. Una instalación local válida puede coexistir con una aceptación comercial pendiente. Conserva ambas conclusiones en el relevo.

## Historial de revisión · 25 de noviembre de 2026

La revisión incorpora la matriz individual de 22 requisitos, el recorrido de riesgos y decisiones, los contratos de captura y compatibilidad, la fixture E2, las cuatro vistas de DEMO-1, permisos y retención por clase, el formato evidence/1 y sus ensayos negativos, el experimento H06 y las condiciones de soporte por activo. Mantiene las fichas de ENTREGAS.md como entradas por unidad. Los benchmarks, comparativas de mercado, referencias y auditoría histórica detallada se consultan en sus fuentes. La revisión describe qué se deberá demostrar y conserva el estado de aquellas pruebas que siguen pendientes.
