# ETAPA 06 — Interfaz local del Mission Planner

**Estado: INCOMPLETA.** Fecha: 2026-11-05, America/Bogota.

La implementación local y su puente ejecutan el motor real y tienen pruebas
automatizadas aprobadas. No se pudo comprobar la interfaz en un navegador real
ni obtener capturas. Este requisito obligatorio impide declarar COMPLETADA la
etapa. No se inicia etapa 7.

## Checkout y preservación

- Checkout: `C:\Users\laura\OneDrive\Escritorio\MARS GOD EYE\NASA-Sandbox-etapa01`.
- Rama comprobada: `etapa01-base-confiable`.
- HEAD/commit base comprobado: `0d5a444f5444b4dfa574224c9f7d09652dad1df5`.
- Estado heredado: `.gitignore` modificado; `docs/continuidad/` y `prototypes/`
  sin seguimiento. Se preservó el trabajo de etapas anteriores.
- Se leyeron AGENTS.md raíz, README y procedencia del repositorio, cierres 01–05,
  README del prototipo, contratos/motor/adaptador, demos y pruebas pertinentes,
  y PERSONALIZACION_ETAPA05.md. No se localizaron AGENTS.md anidados aplicables.
- No se modificaron el CORE, los contratos 3.0/5.0, los datos Jezero, Gods Eye
  View, el visor del piloto, los originales ni los cierres anteriores.
- Antes de editar: discovery en `.venv-stage04`: **71/71 OK, 3.437 s, sin skips**.
  La transcripción de esa primera ejecución está en el chat.
- Python global comprobado: 3.11.9, ruta solicitada. Git comprobado: 2.56.0.windows.4,
  ruta solicitada. Se usó `.venv-stage04\Scripts\python.exe` con NumPy existente.

## Arquitectura y archivos

Aplicación independiente: Python `ThreadingHTTPServer` ligado explícitamente a
`127.0.0.1`; documentos estáticos HTML/CSS/JavaScript y retícula de botones con
SVG superpuesto para rutas. No servicios externos, claves, cuentas ni paquetes
nuevos. Solo NumPy ya instalado para el adaptador CTX; el puente HTTP usa la
biblioteca estándar. Node existente se usa exclusivamente para pruebas unitarias.

La selección de puntos consulta transitabilidad al motor Python; no mueve una
selección inválida a otra celda. Las entradas manuales de fila/columna se validan
al calcular. `compare_alternatives` y `evaluate_options` realizan las acciones
principales. No se copiaron búsqueda, fórmulas de consumo ni reglas de decisión
a JavaScript. El CORE no importa interfaz, servidor, navegador o sockets.

Archivos bajo `prototypes/mission_planner/`:

| Archivo | Cambio / propósito |
|---|---|
| `mission_ui.py` | Nuevo: catálogo acotado, construcción de contratos, transporte localhost, inspección y exportación |
| `web/index.html` | Nuevo: controles en español y estructura semántica |
| `web/style.css` | Nuevo: estilos, estados, retícula y adaptación de ancho |
| `web/app.js` | Nuevo: entradas, selección, presentación, solicitudes y descargas |
| `test_stage06.py` | Nuevo: 10 pruebas de puente/HTTP/independencia del CORE |
| `verify_stage06.py` | Nuevo: 14 casos finitos de evidencia real y catálogo; nunca alimenta la aplicación |
| `test_stage06_frontend.cjs` | Nuevo: pruebas de presentación y concurrencia con doble mínimo del DOM |
| `README.md` | Añade arranque, parada, uso y estado incompleto |
| `evidence/stage06/*` | Nuevas evidencias descritas abajo |

Este cierre es el único documento de continuidad añadido en la etapa.

## Abrir y detener

Comando exacto, desde cualquier directorio en PowerShell:

```powershell
& 'C:\Users\laura\OneDrive\Escritorio\MARS GOD EYE\NASA-Sandbox-etapa01\.venv-stage04\Scripts\python.exe' 'C:\Users\laura\OneDrive\Escritorio\MARS GOD EYE\NASA-Sandbox-etapa01\prototypes\mission_planner\mission_ui.py'
```

Abrir **[http://127.0.0.1:8766](http://127.0.0.1:8766)**.
Detener con **Ctrl+C en la consola donde se lanzó**. El servidor cierra el socket
al finalizar. Si ya está iniciado, usar esa instancia o detenerla antes de
repetir el comando. `--port` permite otro puerto local sin cambiar el bind.
No usar un servidor de archivos estáticos para reemplazar el puente.

Al cerrar este trabajo hay una instancia iniciada por Codex en el puerto 8766;
su endpoint de catálogo y un cálculo CTX recibieron HTTP 200 desde Python local.
Se puede solicitar a Codex detener esa instancia. Para arranques manuales futuros,
Ctrl+C en la consola propia es el procedimiento de parada.

## Controles y flujos implementados

1. Mapa CTX o sintético; astronauta o rover; cargar de nuevo el perfil simulado.
   Cambiar mapa/agente recarga los valores predefinidos de esa combinación.
2. Selección explícita de base, posición manual u objetivo mediante celda;
   modo de consulta, etiquetas B/P/O, entrada numérica de fila/columna.
   Botones por celda, Tab/Enter y flechas para navegar la retícula.
3. Actividad pendiente/completada, minutos pendientes, escenario nominal o
   conservador y factor de sensibilidad. Completada establece minutos a cero.
4. Capacidades originales, saldos actuales, reservas absolutas y tasas editables.
   Tiempo tiene tasa 1. Rover muestra recursos humanos como No aplica.
   Astronauta permite exclusión experimental explícita con motivo obligatorio.
5. Movilidad y coeficientes en panel avanzado con unidades; masa/altura opcionales,
   informativas y solo para astronauta. Sin edad, sexo o género.
6. Comparación de tres políticas y evaluación continuar/regresar; alternativa
   seleccionable para inspección, distancias, duración, recursos, fases y eventos.
7. Modo de obstáculos simulados para alternar celdas; restaurar terreno original.
8. Descargas separadas de configuración, resultado y rutas/waypoints JSON.

Estas son funciones implementadas y examinadas por pruebas de código/puente;
su operabilidad visual y por teclado real continúa pendiente.

## Contratos, estados y errores

Construye `AgentProfile`, asignaciones/exclusiones, `Mobility`, `MotionModel`,
`MissionState`, `RateScenario`, procedencias simuladas y `DecisionRequest` 5.0.
Conserva versión de misión 3.0 como antecedente y no modifica su API.

Errores esperados al construir/deserializar son HTTP 400 `INVALID_INPUT` con
mensaje; errores semánticos de `DecisionRequest` mantienen los resultados
`INVALID_INPUT` de la fachada. En estos últimos se conserva la configuración
enviada aunque `request` sea null porque una solicitud inválida no admite
`to_dict()` validado. Errores internos inesperados son HTTP 500 `INTERNAL_ERROR`,
no se convierten en inviabilidad ni en un resultado de búsqueda.

La presentación conserva códigos SUCCESS, INFEASIBLE, SEARCH_LIMIT_REACHED e
INVALID_INPUT, texto y color. Interrupción: «Búsqueda interrumpida; factibilidad
desconocida». Conserva/traduce CONTINUE, RETURN, REVIEW_CONTINUATION_UNKNOWN,
REVIEW_RETURN_UNCONFIRMED y REVIEW_INVALID_INPUT. Las cinco decisiones siguen
siendo calculadas por el motor; no se promete un regreso sin SUCCESS.

Recomendación de comparación explícita: menor tiempo total entre SUCCESS,
luego batería y desempate por balanced/minimum_time/terrain_caution. No se
denomina más segura. Se muestran grupos coincidentes suministrados por la
fachada y se dibuja solo la alternativa inspeccionada, sin diversidad ficticia.

Continuar visita el objetivo aunque la actividad esté completada; no vuelve a
cobrar actividad. Regresar vuelve directamente sin revisitar el objetivo. Las
reservas permanecen absolutas y el histórico no se descuenta de nuevo.

## Mapas y perturbaciones

CTX: se conserva `CropWindow(60,60,7,7)` de etapa 4, 28×28 m, retícula 4 m,
información CTX nativa de 20 m, afín `[-16,4,0,16,0,-4]`. Solo prior CTX;
el adaptador existente verifica hashes y no decodifica HiRISE ni máscara conjunta.
Cada celda permite consultar altura CTX absoluta, XY interno y coordenadas E/N.

Norte arriba, este a la derecha. Filas crecen hacia sur; columnas hacia este.
El mapa representa centros de celda, X interno este/Y interno sur. En Jezero:
`E=-16+X`, `N=16-Y`. Base inicial (4,2): XY=(10,18) m y E/N=(-6,-2) m.
La escala se declara por celda y ancho total. La tonalidad procede exclusivamente
de alturas del recorte; no es fotografía ni reconstrucción realista.

Escenario sintético 7×7 a 1 m, plano, con franja de penalización simulada central
del escenario de etapa 5; muestra alternativas distintas. Norte/este son
convenciones sintéticas, sin datum planetario.

Cada cálculo copia obstáculos sobre el snapshot original y captura otro
`TerrainReference`; el estado usa su revisión nueva. Restaurar elimina la lista
de perturbaciones y recupera el hash original. Son cambios SIMULADOS, nunca
observaciones científicas. No se toca CTX en disco ni se mutan búsquedas activas.
Ida sólida y regreso discontinuo se superponen en los mismos centros cuando
coinciden; el selector de fases permite inspeccionarlos sin desplazar rutas.

## Ejecución y resultados anteriores

Botones de cálculo deshabilitados durante solicitud activa; configuración aún
editable. Guardia `busy` evita doble solicitud en la página; un lock no bloqueante
del servidor rechaza trabajo simultáneo con HTTP 409. No hay cancelación ficticia.
No hay reintentos automáticos ni aumento de límite: máximo 5000 etiquetas por
búsqueda, casos de interrupción con 1, misma semántica heredada de etiquetas.

Cada edición incrementa la revisión de entradas. La respuesta se asocia a la
revisión capturada al enviar. Una edición posterior marca «Resultados anteriores»
y oculta las rutas superpuestas; si llega una respuesta tras una edición también
queda marcada anterior. Un token de solicitud evita sobrescritura por respuestas
anteriores; otro protege la selección de celdas. Las exportaciones conservan
las entradas del cálculo mostrado, no las nuevas entradas pendientes.

Solo se sirven tres archivos web y dos operaciones POST acotadas, más catálogo.
Se comprueban Host/Origin locales; sin CORS, acceso a archivos arbitrarios ni
backend general. Solicitud limitada a 64 KiB. No se escribe una base de datos.

## Exportaciones

- Configuración JSON: entradas enviadas, contrato válido cuando existe, terreno,
  procedencia y perturbaciones.
- Resultado JSON estricto: envolvente 6.0, versiones 3.0/5.0, ID/fecha/hash de
  entradas, configuración, perfil predefinido, solicitud, resultado del motor,
  perfiles originales/efectivos por alternativa, escenarios/factores y estados.
- Rutas/waypoints JSON: todas las alternativas exitosas, modo/política, índice,
  celda, fase, XY interno, E/N y altura, marcos/unidades, revisión y procedencia.
  Cuando no hay rutas confirmadas, la lista está vacía.

Serialización con `allow_nan=False`. No se importa configuración ni se mantienen
resultados guardados como origen de las acciones principales. El catálogo y
las evidencias JSON no sustituyen llamadas al motor. Los botones de descarga
real en navegador están pendientes de verificación.

## Pruebas y resultados reales

Desde la raíz del checkout:

```powershell
& .\.venv-stage04\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -v
& .\.venv-stage04\Scripts\python.exe prototypes/mission_planner/verify_stage06.py
& 'C:\Users\laura\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' prototypes/mission_planner/test_stage06_frontend.cjs
```

- Suite final: **81/81 OK, 7.839 s, sin skips**. Incluye las 71 regresiones
  heredadas y 10 nuevas pruebas. Log `evidence/stage06/tests.log`.
- Las primeras pruebas HTTP en sandbox fallaron con WinError 10013 (sockets
  restringidos). Se reejecutaron fuera del sandbox con autorización y pasaron,
  sin skips ni debilitamiento de expectativas.
- Las pruebas nuevas comprueban HTTP real, equivalencia de resultados con la
  fachada, entradas modificadas, escenarios/estados, reservas/saldos, no aplica,
  exclusión con motivo, selección, snapshots/restauración, marcos/exportaciones,
  rechazo de concurrencia y diferenciación de error interno. Un subproceso `-S`
  prohíbe importar UI/servidor/socket/navegador y ejecuta una decisión del CORE.
- 14 casos finitos registrados: 13 resultados de comparación/evaluación y un
  error de construcción; 33 resultados individuales de planificación. CTX nominal
  conserva **6.462977601 min, 16.970562748 m, 17.146292116 Wh** desde posición
  intermedia. Cambiar actividad 2→3 min añade un minuto al total calculado.
  CTX bloqueando objetivo produce INFEASIBLE/SUCCESS y RETURN; límite 1 produce
  dos interrupciones; saldo bajo reserva produce inviabilidad sin rebajar reservas.
- HTTP contra la instancia final exacta `127.0.0.1:8766`: catálogo y comparación
  CTX devuelven 200, tres SUCCESS; respuesta íntegra en `live-http.json`.
- JavaScript: sintaxis comprobada con Node; pruebas unitarias con doble de DOM
  pasan usando salidas reales del motor: configuración/49 celdas, coordenadas,
  centros SVG, fases/recursos, rover, estados, actividad completada, resultados
  anteriores, solicitudes duplicadas, edición durante cálculo y errores HTTP.
  **No son pruebas visuales ni end-to-end de navegador**.
- `git diff --check` sin incidencias. No se modificaron pruebas heredadas.

## Evidencia y bloqueo visual

Todo bajo `prototypes/mission_planner/evidence/stage06/`:

| Archivo | Evidencia |
|---|---|
| `tests.log` | 81 pruebas finales, sin skips |
| `functional.json`, `functional-summary.txt` | 14 casos ejecutados con motor real |
| `catalog.json` | Catálogo real usado por pruebas unitarias de presentación |
| `live-http.json` | Respuesta de la instancia final en 8766 |
| `frontend-unit.log` | Verificación de presentación con doble DOM, con límite explícito |
| `preserved-core-sha256.json` | Hashes actuales de siete fuentes del CORE/adaptador/demos conservadas |
| `browser-blocker.md` | Intentos y mensajes concretos de bloqueo de navegador |

**No hay captura representativa ni evidencias visuales verificadas.** El
navegador integrado agotó la conexión a localhost. La alternativa de Firefox
fue detenida por la herramienta al seleccionar la ventana porque la aplicación
de políticas de URL no está soportada en ese navegador Windows. No se burló
ese bloqueo con otra tecnología. La instancia final fuera del sandbox sí responde
a HTTP, pero no se reanudó Computer Use tras su detención en este turno.

## Tabla de aceptación

«Puente comprobado» no significa que el flujo visual esté aprobado.

| # | Requisito | Resultado real |
|---|---|---|
| 1 | Abrir con comando documentado | Servidor iniciado y HTTP 200; apertura visual pendiente |
| 2 | Astronauta y rover | Ambos SUCCESS mediante puente; selector visual pendiente |
| 3 | Seleccionar puntos | Inspección/transitabilidad y validación probadas; clic/teclado real pendientes |
| 4 | Misión sobre CTX | Tres SUCCESS por HTTP en instancia final; presentación pendiente |
| 5 | Entrada modificada y recálculo | Hash y consumo nuevos comprobados; interacción real pendiente |
| 6 | Políticas/coincidencias | CTX una ruta y sintético rutas distintas comprobados; vista pendiente |
| 7 | Continuar/regresar desde intermedia | Comprobado en puente y regresiones |
| 8 | Presupuesto insuficiente | INFEASIBLE y reserva absoluta comprobados; vista pendiente |
| 9 | Búsqueda interrumpida | SEARCH_LIMIT_REACHED comprobado; vista pendiente |
| 10 | Entrada inválida | Construcción HTTP 400 y fachada INVALID_INPUT comprobadas; vista pendiente |
| 11 | Obstáculos/recalcular/restaurar | Hashes y rutas comprobados; interacción visual pendiente |
| 12 | Actividad completada sin recobro | Eventos sin science comprobados y objetivo visitado |
| 13 | Saldos/reservas/no aplica | Comprobados por puente y presentación unitaria |
| 14 | Exportaciones | Contenido JSON/marcos comprobados; descarga real pendiente |
| 15 | Obsoletos/duplicados | Lock HTTP y lógica de revisión probados; navegador pendiente |
| 16 | Alineación celdas/coordenadas | Transformaciones y centros SVG unitarios; alineación visual pendiente |
| 17 | Escritorio/ancho reducido | CSS implementado; **no verificado visualmente** |
| 18 | 71 regresiones | Todas pasan en suite final 81/81 sin skips |
| 19 | CORE independiente | Subproceso sin servidor/UI/socket y regresiones aprobados |

## Pendiente para completar etapa 6

En una herramienta de navegador que pueda alcanzar el localhost de Windows:

1. Iniciar el comando indicado y comprobar la carga de controles y mapa.
2. Recorrer los 19 criterios anteriores en la interfaz real. Para inválido,
   introducir objetivo igual a base o actividad negativa; para interrupción,
   límite 1; para insuficiencia, saldo de batería 9 Wh con reserva 10 Wh.
3. Comparar CTX con astronauta y rover; editar actividad; probar sintético con
   políticas distintas; bloquear objetivo y evaluar regreso; restaurar.
4. Seleccionar las tres posiciones y consultar base (4,2), XY (10,18), E/N (-6,-2).
   Comprobar huella y rechazo de celda bloqueada sin cambio silencioso.
5. Marcar actividad completada, inspeccionar eventos; comprobar recursos humanos
   no aplicables/excluidos, reservas y perfil efectivo conservador.
6. Cambiar entradas durante/después del cálculo y comprobar rótulo de anterior,
   ausencia de superposición engañosa y prevención de doble solicitud.
7. Descargar los tres JSON desde sus botones y verificar su contenido; comprobar
   Tab, flechas, Enter, etiquetas y foco. Comprobar escritorio y ancho reducido.
8. Capturar pantalla de éxito, comparación/decisión, interrupción, inviabilidad,
   entrada inválida y ancho reducido. Guardar bajo `evidence/stage06/`, registrar
   la verificación real, corregir defectos si aparecen y repetir pruebas afectadas.

Solo entonces actualizar este cierre a COMPLETADA. No sustituir esa comprobación
por el HTML, el arranque del servidor, los JSON o el doble DOM.

## Limitaciones e instrucciones para etapa 7

Conserva las limitaciones de resolución CTX y del modelo paramétrico, geometría
conservadora y búsqueda acotada. Perfiles/objetivos simulados, sin garantía EVA,
seguridad humana, regreso físico, sensores, streaming o telemetría. La licencia
de originales sigue pendiente antes de distribución; esta implementación es local.

No avanzar a etapa 7 mientras falten los requisitos visuales de etapa 6. Una vez
cerrada, la etapa 7 requerirá autorización propia: conservar el CORE independiente,
consumir contratos tipados y trazabilidad existente y acordar ROS 2 o preparación
verificable para ella. **No se implementó ROS 2 ni se inició esa etapa.**

No se hicieron commits, push ni PR; tampoco clone, reset, clean, cambio de rama
u operaciones destructivas. Se detiene la implementación con el bloqueo visual
documentado y la aplicación local disponible para su comprobación.
