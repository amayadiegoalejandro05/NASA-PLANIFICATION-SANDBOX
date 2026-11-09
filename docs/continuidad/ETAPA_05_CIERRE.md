# ETAPA 05 — Decisiones, personalización, replanificación y evaluación

**Estado: COMPLETADA.** Fecha: 2026-11-05, America/Bogota.

## Alcance y checkout comprobado

Motor experimental Python para comparar hasta tres políticas, continuar desde
una posición intermedia o regresar usando saldos y terreno actualizado. Incluye
personalización honesta, incertidumbre explícita, pruebas independientes y
evaluación finita reproducible. No es certificación EVA ni controlador de emergencia.
No se implementaron interfaz, adaptador ROS, Gazebo, backend ni telemetría.

- Checkout: `C:\Users\laura\OneDrive\Escritorio\MARS GOD EYE\NASA-Sandbox-etapa01`.
- Rama: `etapa01-base-confiable`.
- HEAD/base: `0d5a444f5444b4dfa574224c9f7d09652dad1df5`.
- Estado heredado: `.gitignore` modificado, `docs/continuidad/` y `prototypes/`
  sin seguimiento; trabajo válido de etapas 1–4 preservado.
- Python global y `.venv-stage04\Scripts\python.exe`: **3.11.9**.
  Git indicado: **2.56.0.windows.4**. NumPy opcional del entorno Jezero: **2.2.6**.
  No se instalaron paquetes ni se modificaron entornos.
- Primera suite antes de editar: **53/53, 1.930 s, sin skips**. Se repitió antes
  de editar para guardar `baseline-tests.log`: **53/53, 2.148 s, sin skips**.

Se leyeron AGENTS.md raíz (único localizado), README raíz, escenario/procedencia,
cierres 01–04, README, módulos y pruebas del prototipo, documentación del piloto
Jezero, contexto maestro en `originals/` y auditoría inicial en la carpeta padre.
Las instrucciones de ejecutar Gazebo pertenecen al piloto/mundo que no se toca;
la autorización actual limita el trabajo a etapa 5. No se reconstruyó desde HEAD,
clonó, cambió de rama, limpió ni revirtió el checkout.

El manifiesto `inherited-sha256.json`, capturado antes de editar, y
`verification.json` registran preservación: 56 archivos comprobados, 53 intactos.
Solo se editaron tres archivos
preexistentes: motor de recursos, fachada privada de desglose y README. Los 53
tests heredados, originales, evidencias anteriores y cierres 01–04 se conservan
byte a byte. Datos/piloto/mundo y `.gitignore` no fueron editados en esta etapa.

## Archivos de etapa 5

Rutas del prototipo bajo `prototypes/mission_planner/`:

| Archivo | Cambio |
|---|---|
| `mars_mission_resources.py` | Extensión mínima de la única búsqueda: base terminal separada, regreso y actividad inicial/completada |
| `mission_api.py` | Desglose compartido admite ciencia inicial/omitida y objetivo null en regreso; API 3.0 conserva significado |
| `mission_decisions.py` | Contratos 5.0, características, procedencia, escenarios, políticas, comparación y recomendación |
| `demo_stage05.py` | Casos fijados antes de ejecutar, snapshots simulados y evaluación con métricas |
| `test_stage05.py` | 16 pruebas con subcasos, aritmética esperada, oráculo y CORE sin opcionales |
| `test_stage05_integration.py` | Dos pruebas nuevas sobre CTX real, sin sustitución sintética |
| `PERSONALIZACION_ETAPA05.md` | Clasificación de parámetros, fuentes, dominio y decisión de no usar fórmula antropométrica |
| `README.md` | Contratos, uso y reproducción |
| `evidence/stage05/*` | Baseline, manifiesto heredado, pruebas, evaluación estricta, resumen y verificación |

Este documento es nuevo; no reemplaza cierres anteriores.

## Personalización y fuentes

Revisión primaria:
[NASA Human Performance](https://www.nasa.gov/reference/4-0-human-performance/),
[NASA Spacesuits](https://www.nasa.gov/reference/11-0-spacesuits-vol-2/),
[Cox et al., NTRS 20240009328](https://ntrs.nasa.gov/citations/20240009328), incluida
su presentación original. La decisión y clasificación completa están en
[PERSONALIZACION_ETAPA05.md](../../prototypes/mission_planner/PERSONALIZACION_ETAPA05.md).

No se identificó en lo revisado una fórmula apropiada para trasladar antropometría
a consumo EVA marciano en este motor. **No se implementó tal fórmula**. Masa kg y
altura m opcionales son metadatos positivos finitos sin efecto en consumos o
movilidad. Edad/sexo biológico no se recopilan porque no hay modelo que los necesite;
identidad de género no es coeficiente fisiológico.

Utilizados: tasas individuales de movimiento/actividad, velocidad, coeficientes
heredados de ascenso/esfuerzo/rugosidad, geometría, saldos, reservas y factores de
escenario. Informativos: masa, altura, procedencia y consumo histórico. Pendientes:
efectos de composición corporal, condición física, fatiga, adaptación, carga y
ajuste/presión del traje. Introducir metadatos no implica modelar esos efectos.

Nutrición diaria no se calcula; kcal son demanda parametrizada, no comida exigida
durante una EVA breve. O2 permanece en unidades simuladas. Agua no integra un
balance fisiológico ni refrigeración. Capacidades del equipo siguen configurables.
No se modelan CO2, autonomía térmica, radiación ni meteorología.

Cada recurso modelado exige procedencia `measured/estimated/simulated`, fuente y
alcance de sus dos tasas. Se conserva como declaración del llamador, sin autenticar
la medición. Todos los perfiles evaluados son simulados; los tests measured/estimated
son fixtures ficticios. No se solicitaron datos personales reales.

Escenario nominal: factores 1. Conservador: factores explícitos >=1, tiempo 1.
Multiplican tasas por recurso en ambas fases, manteniendo velocidad, Wh/m de
ascenso y reservas. El +20% del ejemplo es sensibilidad ficticia; no es probabilidad
calibrada, percentil ni garantía de peor caso.

## Contratos, versiones y compatibilidad

`MissionRequest/MissionResult` y `plan_mission` **3.0** siguen exigiendo inicio=base
y objetivo distinto. No se cambia silenciosamente ese significado. Los ejemplos
y las 53 regresiones anteriores conservan su comportamiento.

Entrada nueva: `DecisionRequest(schema_version="5.0", request_id, terrain, frame,
profile, state, rate_provenance, scenario, max_labels, personal=None)`.
`MissionState` incluye ID de misión, base original, posición actual, objetivo,
estado de actividad y minutos pendientes, saldos, reservas, identidad/versión/hash
de perfil, ID/revisión de terreno e histórico opcional. Solo admite centros de
celda `(fila,columna)` con enteros estrictos, dentro del snapshot.

El perfil de entrada contiene capacidades/reservas originales. Se validan claves
exactas de recursos modelados, saldos finitos no negativos y no mayores que sus
capacidades, reservas iguales a las originales y hashes de perfil/terreno
coherentes. El histórico admite un subconjunto de recursos modelados con valores
finitos no negativos; no se reconcilia como libro contable de toda la misión.
Es una declaración informativa y **nunca se vuelve a descontar**.

Recursos restantes son la única disponibilidad para el futuro. Se crea un perfil
efectivo con capacidad=saldo y la misma reserva absoluta. Un saldo inferior a
reserva da `INFEASIBLE/BALANCE_BELOW_RESERVE`; no se reduce la reserva como porcentaje.
En eventos y total, `capacity` significa saldo al solicitar; perfil original y
efectivo se exportan separados. `remaining=saldo-consumo_futuro` y
`margin_above_reserve=remaining-reserva`.

Construcción de contratos anidados inválidos falla con ValueError/TypeError antes
de la fachada. Errores semánticos de `DecisionRequest` producen INVALID_INPUT;
errores internos inesperados se propagan. `DecisionResult.to_json()` usa
`allow_nan=False`; `to_dict()` devuelve copia JSON independiente. No se creó
deserializador JSON, protocolo remoto o framework. El JSON de evidencia incluye
snapshots íntegros, marcos, perfiles, factores y procedencias para reproducir.

## Continuar, regresar y contabilidad

`plan_future(q, "continue", policy)` evalúa actual→objetivo→actividad pendiente→base.
`plan_future(q, "return", policy)` evalúa actual→base sin ciencia; no exige que el
objetivo sea transitable. Ambos usan `ResourceMissionPlanner.plan` y las mismas
fórmulas, dominancia, geometría, tolerancia 1e-9 y contabilidad por fases/eventos.
No se duplicó el buscador ni se cambiaron heurísticas/dominancia.

Actividad `completed` exige minutos pendientes cero y no genera ciencia; en modo
continue se sigue visitando el objetivo. Si actual=objetivo, la actividad pendiente
se cobra al inicio exactamente una vez. Duración pendiente cero conserva un evento
de ciencia de duración cero. Regreso nunca genera ese evento.

Desde la base, regresar devuelve SUCCESS con una celda, costo y todos los consumos
cero, eventos vacíos y una etiqueta inicial. En regreso `goal_cell/goal_index` son
null y todo movimiento pertenece a inbound. outbound/activity/inbound permanecen
como resúmenes, con cero en fases omitidas. Recursos excluidos/no aplicables siguen
exportándose con cantidades null y razón cuando corresponde.

Referencia manual de línea 1×3, resolución/velocidad 1, actual (0,1), base (0,0),
objetivo (0,2), actividad 2: continuar recorre 3 m, tarda 5 min, consume 16 Wh,
9 u O2, 1.1 L y 24 kcal. Regresar recorre 1 m, tarda 1 min y consume 2 Wh.
Actividad completada: continuar consume 6 Wh/3 min. Actual en objetivo con actividad
pendiente: 14 Wh/4 min. Historial no altera ninguno de esos futuros.

## Políticas y regla de preferencia

Se calculan exactamente tres políticas deterministas, sin optimizar pesos:

| Política | Objetivo sobre el motor existente |
|---|---|
| balanced | Pesos originales del perfil |
| minimum_time | hazard_cost_weight=0 y battery_cost_weight=0 |
| terrain_caution | hazard_cost_weight=max(4,2×original); resto conservado |

Los pesos geométricos, movilidad, límites, saldos, reservas, tasas y actividad son
comunes. Los pesos efectivos se exportan junto con distancia, tiempo, consumos,
márgenes y estado de cada alternativa. La cautela es respecto de las penalizaciones
disponibles; no se inventa una capa de riesgo Jezero ni se denomina más segura una ruta.

Regla fijada antes de implementar: entre SUCCESS calculados, menor tiempo total;
desempate por batería total y después orden balanced/minimum_time/terrain_caution.
Los costos de funciones con pesos diferentes no se comparan entre sí. Solo se
comparan las alternativas calculadas; no se afirma optimalidad global. Una
alternativa interrumpida conserva factibilidad desconocida y no se declara peor.
Rutas coincidentes se agrupan por secuencia exacta de celdas. En CTX las tres
coinciden; en la penalización sintética se obtienen dos rutas distintas y se
recomienda minimum_time. No se fabrica diversidad ni un frente de Pareto.

`evaluate_options` conserva resultados separados de continuar/regresar:

| Continuación | Regreso | Decisión |
|---|---|---|
| SUCCESS | SUCCESS | CONTINUE |
| INFEASIBLE | SUCCESS | RETURN |
| SEARCH_LIMIT_REACHED | SUCCESS | REVIEW_CONTINUATION_UNKNOWN |
| Cualquier estado no inválido | INFEASIBLE o SEARCH_LIMIT_REACHED | REVIEW_RETURN_UNCONFIRMED |
| INVALID_INPUT en cualquiera | Cualquiera | REVIEW_INVALID_INPUT |

Es recomendación experimental de planificación, no control de emergencia ni
evacuación garantizada. Se admite `return_max_labels` explícito para evaluar el
regreso con otro límite; queda registrado en su solicitud. La evaluación medida
usa el mismo límite en ambos modos; el test de incertidumbre usa 1/5000 sin
reintentar ni reinterpretar la búsqueda de continuación.

## Terreno actualizado e interrupciones

Se captura otro TerrainReference y se actualiza explícitamente la revisión del
estado. Se conservan solicitud/snapshot anteriores y se rechaza combinar revisión
vieja con snapshot nuevo. No se muta una búsqueda en ejecución.

Fixtures: obstáculo en (3,3) obliga a desvío en 7×7; muro de columna 3 impide
continuar y permite regresar; elevación 10 m en (3,3) cambia transitabilidad y
trayectoria. Desconocido en posición actual produce CURRENT_UNKNOWN; bloqueo
produce CURRENT_NOT_TRAVERSABLE, sin desplazamiento silencioso. También se
diagnostican base/objetivo no transitables. Los obstáculos/desconocidos añadidos
a CTX son **perturbaciones simuladas del escenario**, no observaciones científicas.

SEARCH_LIMIT_REACHED mantiene factibilidad desconocida. Solo agotamiento o
restricciones explícitas producen INFEASIBLE. En éxito/interrupción se registra
generated_labels; en agotamiento y diagnósticos previos es null porque el motor
no expone ese conteo. Etiquetas incluyen inicial e inactivas, no expansiones.

## Evaluación finita y métricas reales

Configuración fijada en `demo_stage05.py` antes de la primera ejecución:
línea 1×3 a 1 m; sintético 7×7 a 1 m; CTX filas/columnas [60,67), 7×7 a 4 m,
28×28 m, información nativa 20 m. Límite **5000 por búsqueda**, fixtures de
interrupción **1**. No se aumentó ningún límite ni se intentó resolver el parent
128×128. Una ejecución medida por caso; sin ajuste iterativo por rendimiento.

17 casos, 39 solicitudes: **27 SUCCESS, 8 INFEASIBLE, 4 SEARCH_LIMIT_REACHED**.
Las entradas inválidas se cubren en pruebas, sin fabricar métricas de búsqueda.

Tiempo medido con perf_counter para toda la llamada compare/evaluate, incluida
validación, hashes y copias JSON, excluida la carga CTX. Cada llamada contiene dos
o tres planes, no son tiempos exclusivos del buscador. Pico por llamada con
tracemalloc: **asignaciones Python, no toda la memoria del proceso ni NumPy nativo**.
La primera llamada incluye calentamiento; no se infiere distribución estadística,
capacidad de tiempo real ni límite operativo a partir de una sola repetición.
La captura inicial se hizo con tracemalloc activo y un proceso de pruebas unitarias
concurrente; no es una medición aislada del hardware. Esa condición queda registrada
en el JSON y puede influir en los tiempos.
Se registran versión Python/plataforma, tamaños, perfil, política, límite y
etiquetas disponibles de cada plan en `evaluation.json`.

S=SUCCESS, I=INFEASIBLE, L=SEARCH_LIMIT_REACHED. Estados de modo compare siguen
orden balanced/minimum_time/terrain_caution; modo evaluate, continuar/regresar.

| Caso | Estados | Tiempo s | Pico Python bytes |
|---|---|---:|---:|
| line_nominal | S/S | 0.063374 | 321694 |
| line_conservative | I/S | 0.037631 | 215029 |
| line_completed | S/S | 0.044584 | 297300 |
| line_at_goal | S/S | 0.046092 | 307844 |
| line_at_base | S/S | 0.046520 | 312734 |
| line_low | I/S | 0.040035 | 212829 |
| line_limit | L/L | 0.031478 | 170211 |
| line_unknown | I/I | 0.021643 | 136769 |
| grid_original | S/S/S | 0.498208 | 1038385 |
| grid_detour | S/S/S | 0.575026 | 872665 |
| grid_wall | I/S | 0.107727 | 243226 |
| grid_elevation | S/S/S | 0.467362 | 1029338 |
| grid_penalty | S/S/S | 0.512540 | 870066 |
| ctx_nominal | S/S/S | 0.455719 | 666918 |
| ctx_obstacle | I/S | 0.062337 | 263690 |
| ctx_unknown | I/I | 0.035942 | 200587 |
| ctx_limit | L/L | 0.050405 | 240181 |

Desvío sintético: distancia de 9 a **10.656854249 m**, 97→95 etiquetas balanced.
Elevación: **14.071067812 m**, 87 etiquetas. Muro agota continuación; regreso
1 m/2 Wh, 12 etiquetas. Penalización sintética: minimum_time 9 m/10 min/23 Wh;
balanced y terrain_caution 10.656854249 m/11.656854249 min/26.313708499 Wh.

CTX real, perfil sim-jezero-ctx-astronaut 4.0: base (4,2), actual (3,3), objetivo
(2,4), actividad 2 min. Ruta de las tres políticas:
(3,3)→(2,4)→(3,3)→(4,2). **16.970562748 m, 6.462977601 min,
17.146292116 Wh**, etiquetas **106/92/106**. O2 **1.775119960 u**, agua
**0.087004798 L**, demanda **28.801919365 kcal**. Márgenes nominales:
48.537022399 min, 72.853707884 Wh, 16.224880040 u O2, 1.712995202 L,
151.198080635 kcal. Los saldos de este fixture son declarados, no inferidos del
trayecto histórico. Retorno CTX del caso objetivo bloqueado: 5.656854249 m,
1.523588562 min, 3.156552125 Wh, 22 etiquetas. Límites 1 interrumpen ambos modos
sin declarar imposibilidad.

SHA-256 del producto real conservado:
`18d20b39a680d93addc3c3151bb3f19a5f41fc8f9a170396d4094694bbd76d6b`.
Snapshot CTX original:
`639340f9c4b722cc9f445c9b10398bcea90f56988cc5f3fc59f0434bc2013e1f`.
Solo se decodifica prior CTX, no alturas HiRISE, máscara conjunta ni origin_z_m.
La integración verifica que buscar después de adaptar no vuelve a acceder a
archivos/NPZ. Marcos y límites de resolución siguen siendo los de etapa 4.

## Comandos y pruebas ejecutadas

Desde la raíz del checkout, PowerShell:

```powershell
$plannerPython = 'C:\Users\laura\AppData\Local\Programs\Python\Python311\python.exe'
$plannerGit = 'C:\Users\laura\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'
& $plannerPython --version
& $plannerGit --version
& $plannerGit status --short
& $plannerGit branch --show-current
& $plannerGit rev-parse HEAD
& .\.venv-stage04\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -v
& .\.venv-stage04\Scripts\python.exe prototypes/mission_planner/demo_stage05.py --output prototypes/mission_planner/evidence/stage05
& $plannerPython -m unittest discover -s prototypes/mission_planner -p test_stage05.py -v
& $plannerGit diff --check
```

Suite final Jezero: **71/71, 3.380 s, sin skips**, 53 regresiones + 16 unidades
nuevas + 2 integraciones CTX nuevas. Python global: **16/16, 1.342 s**, pruebas
etapa 5 con biblioteca estándar. Además, subproceso `-S` bloquea imports de NumPy,
Rasterio, PyProj, SciPy y Matplotlib y ejecuta comparación/decisión con éxito.
No se usa una ejecución omitida para declarar integración completada.

Oráculo independiente: enumera todos los caminos simples en dos fases de una
retícula plana 2×2 con penalizaciones conocidas, sin usar _edge, traveling,
dominancia ni el buscador del motor. Costos/recursos positivos permiten excluir
ciclos dentro de cada fase. Compara costo y factibilidad en continuación/regreso
para baterías 30, 4 y 1 Wh. Se añaden cuentas manuales independientes de línea,
reservas exactas y sumas de eventos/fases. No prueba optimalidad operacional global.

Los 16 tests iniciales de etapa 5 pasaron en su primera ejecución; la primera
suite ampliada de 71 también pasó. No se relajaron tests anteriores ni se ocultaron
fallos con skips. No se ejecutaron Gazebo, ROS ni simulación/visor del piloto.

## Tabla de aceptación

Todos los criterios obligatorios se cumplen; referencias a tests bajo el prototipo.

| # | Requisito | Evidencia |
|---|---|---|
| 1 | Validación/significado personales | test_personal_validation_and_no_effect y documento de personalización |
| 2 | Metadatos sin efecto | Mismo test: tres características y ausencia, plan/consumo idéntico |
| 3 | Procedencia y conservador | test_provenance_and_conservative_scenario; line_conservative I/S |
| 4 | Regla y restricciones comunes | test_comparison_common_constraints_and_coincidence; test_preferences_use_computed_metrics |
| 5 | Coincidencia honesta | Mismo test y ctx_nominal, una ruta para tres políticas |
| 6 | Continuar fuera de base | test_continuation_independent_expected_accounts; CTX nuevo |
| 7 | Regreso sin ciencia | test_direct_return_and_base_zero; CTX nuevo |
| 8 | Actividad completada sin recobro | test_completed_and_initial_goal_science_once |
| 9 | Saldo sin doble descuento | test_history_not_debited_reserves_absolute |
| 10 | Reservas absolutas | Mismo test, reservas exactas y saldo inferior; test_state_validation_and_identity |
| 11 | Regreso en base cero | test_direct_return_and_base_zero; line_at_base |
| 12 | Nuevos snapshots | test_new_snapshots_detour_wall_unknown_elevation; CTX perturbado |
| 13 | Actual bloqueada/desconocida | test_position_blocked_unknown_no_relocation; CTX desconocido |
| 14 | Continuar inviable/regresar factible | test_decision_infeasible_interrupted_and_no_confirmed_return; muro y CTX objetivo bloqueado |
| 15 | Interrupción distinta | Mismo test con límite 1/5000; ctx_limit |
| 16 | Sin regreso confirmado exige revisión | Mismo test y ctx_unknown/ctx_limit |
| 17 | Eventos/fases consistentes | test_events_phases_and_strict_json y contabilidad CTX |
| 18 | JSON/versiones | test_events_phases_and_strict_json; test_excluded_and_v3_compatibility; tests de validación |
| 19 | Referencia independiente | test_independent_small_reference_continue_return y cuentas de línea |
| 20 | 53 regresiones | Suite final 71/71 y verificación de hashes de pruebas heredadas |
| 21 | CORE sin GIS | test_core_without_optional_dependencies y core-tests.log |
| 22 | CTX real ejecutado sin skips | Cinco integraciones heredadas y dos nuevas; tests.log |

## Evidencias y limitaciones

Todo bajo `prototypes/mission_planner/evidence/stage05/`:

- `baseline-tests.log`, `baseline.json`, `inherited-sha256.json`: estado previo.
- `tests.log`, `core-tests.log`: resultados ejecutados.
- `evaluation.json`: 17 casos íntegros, solicitudes/snapshots, perfiles, políticas,
  decisiones, estados, eventos, fases, márgenes y métricas reales.
- `summary.txt`: resumen de rendimiento y estados.
- `verification.json`: preservación, JSON estricto, conteos y estado Git final.

Tiempos y asignaciones varían entre máquinas/ejecuciones; estados y cálculos
son deterministas para estos datos. No hay medición completa de memoria nativa,
calibración fisiológica, autenticación de tasas medidas ni validación física.
CTX a 4 m de retícula no crea información nativa de 4 m. Sin mapa de riesgo
observado, suelo granular, obstáculos observados, refugios múltiples, movimiento
continuo ni múltiples objetivos. Límites de geometría conservadora y escalabilidad
multietiqueta heredados siguen vigentes. Licencia/autoría de originales permanece
pendiente antes de redistribuir; no bloquea el uso local autorizado.

## Instrucciones concretas para etapa 6

No hay interfaz implementada. Cuando se autorice etapa 6:

1. Leer cierres 01–05 y preservar checkout local; ejecutar las 71 pruebas con
   `.venv-stage04`. No asumir que una búsqueda interrumpida es inviable.
2. Consumir DecisionRequest 5.0 y sus resultados; conservar 3.0 para consumidores
   antiguos. Capturar errores de construcción antes de llamar a la fachada.
3. Presentar saldo, reserva absoluta y margen por separado, perfil original y
   escenario efectivo; historial solo informativo. Etiquetar masa/altura sin
   efecto y no solicitar edad/sexo para este motor.
4. Mostrar cada estado, política/pesos y coincidencias; no llamar segura a una
   ruta ni esconder alternativas interrumpidas. REVIEW requiere explicación,
   no una afirmación de evacuación disponible.
5. Usar centros de celda y los marcos documentados de etapa 4; no redondear ni
   mover posiciones bloqueadas silenciosamente. Conservar snapshot/revisión de
   cada solicitud y registrar explícitamente cambios simulados.
6. Usar evaluación JSON como fixture de presentación, sin incorporar búsqueda,
   consumos duplicados ni ROS en la interfaz. Etapa 7 permanece fuera de alcance.

No hay bloqueos obligatorios. **No se hicieron commits, push ni PR**, ni operaciones
destructivas. La implementación se detiene al cumplir exclusivamente la etapa 5.
