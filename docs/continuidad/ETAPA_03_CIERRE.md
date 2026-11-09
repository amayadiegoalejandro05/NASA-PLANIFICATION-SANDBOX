# ETAPA 03 — Misión completa y explicable

**Estado: COMPLETADA.** Fecha: 2026-11-05, America/Bogota.

## 1. Alcance realizado

Contrato Python explícito de misión, fachada sobre el motor multirrecurso existente,
resultado discriminado, contabilidad de ida/ciencia/regreso, marco local explícito,
JSON estricto, cinco escenarios pequeños simulados y referencia matemática diminuta.
La misión contiene una base/inicio, un objetivo diferente, una actividad estacionaria
y regreso a esa misma base. No se inició etapa 4 ni se implementaron integraciones.

## 2. Checkout, instrucciones y cambios heredados

- Checkout: `C:\Users\laura\OneDrive\Escritorio\MARS GOD EYE\NASA-Sandbox-etapa01`.
- Repositorio: https://github.com/dryanguasr/NASA-Sandbox.
- Rama comprobada: `etapa01-base-confiable`.
- HEAD/commit base comprobado: `0d5a444f5444b4dfa574224c9f7d09652dad1df5`.
- Estado inicial y final de Git: `?? docs/continuidad/` y `?? prototypes/`.
  Las etapas anteriores siguen sin commit y sin seguimiento; se preservaron.
- Leídos AGENTS.md (único localizado), README raíz, escenario y procedencia;
  cierres 01/02; README, módulos y pruebas del prototipo. Se consultaron contexto
  maestro en `prototypes/mission_planner/originals/` y auditoría inicial en
  `../AUDITORIA_MISSION_PLANNER_2026-11-05.md` como antecedentes.
- Las instrucciones históricas sobre ejecutar Gazebo, hardware y Fly Brain no
  amplían este encargo. No se tocaron mundos, pilotos ni datos Jezero.
- No se clonó, reconstruyó desde HEAD, cambió de rama, limpió ni revirtió trabajo.
  Cierres 01/02 y originales permanecen intactos.

Se verificaron snapshot, geometría conservadora, excepción de límite independiente,
perfiles explícitos, `from_profile`, tasas diferenciadas y estados de recursos en
código y mediante las 30 regresiones iniciales aprobadas. No se asumió factible la
demo grande del astronauta: su resultado heredado sigue siendo indeterminado en
120.000 etiquetas. No se elevó el límite ni se optimizó la búsqueda.

## 3. Archivos de esta etapa

| Ruta | Propósito |
|---|---|
| `prototypes/mission_planner/mission_api.py` | Solicitud, identidad de snapshot/perfil, marco, fachada, resultado, desglose y JSON |
| `prototypes/mission_planner/mars_mission_resources.py` | Extracción mínima de `movement_usage`, compartida por búsqueda y desglose |
| `prototypes/mission_planner/demo_stage03.py` | Cinco escenarios pequeños, resumen y `--json` |
| `prototypes/mission_planner/test_stage03.py` | Nueve pruebas con subcasos de aceptación y oráculo independiente |
| `prototypes/mission_planner/README.md` | Entrada pública y convenciones |
| `prototypes/mission_planner/evidence/stage03-baseline.txt` | Registro resumido de la ejecución inicial previa a ediciones |
| `prototypes/mission_planner/evidence/stage03-tests.log` | Suite final ejecutada |
| `prototypes/mission_planner/evidence/stage03-demo.log` | Salidas legibles actuales de cinco escenarios |
| `prototypes/mission_planner/evidence/stage03-results.json` | Los cinco resultados completos actuales en UTF-8 sin BOM |
| `docs/continuidad/ETAPA_03_CIERRE.md` | Este cierre autocontenido |

No se editaron las 30 pruebas anteriores ni sus expectativas, el módulo geométrico,
los originales o las evidencias de etapas anteriores. La única modificación al
motor extrae las mismas lecturas de altura/rugosidad y llamada a `traveling` en
una función compartida. Ordenación, costo, dominancia y fórmulas siguen iguales.

## 4. Solicitud y frontera de validación

Versión de solicitud y resultado: **`schema_version="3.0"`**.

`MissionRequest` es una dataclass frozen con todos estos argumentos obligatorios:

| Campo | Contrato |
|---|---|
| `schema_version` | Exactamente `"3.0"` |
| `request_id` | Texto no vacío |
| `terrain` | `TerrainReference` con identificador, snapshot inmutable y propiedad `revision_sha256` |
| `frame` | `LocalFrame` validado, con resolución igual al snapshot |
| `base`, `start`, `goal` | Tuplas `(fila, columna)`, int estricto sin bool, dentro del mapa |
| `activity_min` | int/float finito y no negativo, sin bool |
| `profile` | `AgentProfile` explícito y validado de etapa 2 |
| `max_labels` | int positivo estricto, sin bool; misma semántica de etapa 1 |

`base == start` y `base != goal`. No se duplican capacidades ni reservas del perfil
en la solicitud. La validez de coordenadas no implica transitabilidad: salir del
mapa es INVALID_INPUT; una celda válida bloqueada puede producir INFEASIBLE.

**Frontera exacta:** el constructor de `MissionRequest` exige los argumentos Python
pero difiere la validación semántica a `plan_mission`. Esta fachada convierte
`RequestValidationError` en INVALID_INPUT, también para un tipo superior distinto
de MissionRequest. La solicitud puede construirse con una duración o coordenadas
incorrectas y será rechazada antes de crear el planificador/buscar.

Argumentos ausentes del constructor producen `TypeError` antes de llamar a la
fachada. `TerrainReference`, `LocalFrame`, `AgentProfile` y sus contratos anidados
validan al construirse y pueden lanzar `ValueError`/errores de argumentos Python.
Esos errores ocurren **fuera de la frontera** de `plan_mission` y debe manejarlos
el llamador; no se promete un MissionResult para objetos que no llegaron a existir.
No hay deserializador JSON, JSON Schema ni validación de objetos manipulados por
fuera de los constructores frozen (por ejemplo mediante `object.__setattr__`).

`TerrainReference.capture(terrain, terrain_id)` copia y valida todas las retículas.
Su revisión SHA-256 usa JSON canónico `sort_keys=True`, separadores `,`/`:`,
`ensure_ascii=True`, `allow_nan=False`, UTF-8 y formato `terrain-snapshot-v1`.
Contenido: heights_m (desconocidos null), risk y roughness normalizados a float;
obstacles bool; resolution_m float; hash_format. No incluye terrain_id, por lo
que el mismo contenido con otro nombre mantiene el hash. La identidad del
resultado incluye ID, hash/formato, filas, columnas y resolución. No referencia
un Terrain mutable para reconstruir consumos.

El resultado copia todos los parámetros y metadatos del perfil, su versión,
estados/unidades y una revisión SHA-256 canónica del objeto de perfil exportado
antes de agregar `revision_sha256`. La naturaleza de los ejemplos es `simulated`;
IDs y versiones se preservan. El marco se exporta por separado: un mismo raster
puede situarse en otro origen local sin cambiar el hash de su contenido.

## 5. Resultado, estados y errores

`MissionResult` incluye schema_version, request_id, status, reason_code, message,
terrain, profile, frame, assumptions, exclusions, search_metrics y plan.
`status` es `MissionStatus`, enum de cuatro valores; `to_dict()` lo exporta como
string. `plan` es null salvo SUCCESS. Identidades no válidas/no disponibles y
request_id no textual se representan como null en INVALID_INPUT; el esquema del
resultado siempre es 3.0, aunque la versión solicitada fuera incompatible.

| Estado | Código | Significado |
|---|---|---|
| SUCCESS | MISSION_FOUND | Misión admisible encontrada bajo snapshot/perfil y sus reservas |
| INFEASIBLE | ENDPOINT_NOT_TRAVERSABLE | Extremo dentro del mapa no transitable según ocupación/desconocidos/geometría/movilidad |
| INFEASIBLE | SEARCH_EXHAUSTED | Motor agotó la búsqueda sin misión admisible; no se deduce una causa única |
| SEARCH_LIMIT_REACHED | LABEL_LIMIT_REACHED | Cálculo interrumpido; factibilidad desconocida |
| INVALID_INPUT | REQUEST_VALIDATION_FAILED | Incumplimiento del contrato dentro de la frontera anterior |

No hay CANCELLED ni búsquedas auxiliares de explicación. No se atribuye un
agotamiento exclusivamente a oxígeno, agua, batería o tiempo. En el escenario
de presupuesto insuficiente la aritmética del fixture prueba la causa, pero
el mensaje general del motor mantiene su alcance real.

Errores inesperados de implementación se propagan con su diagnóstico, sin
catch general que los convierta en entrada inválida o inviabilidad. Una
inconsistencia entre plan y desglose genera RuntimeError. La serialización
rechaza cantidades no finitas en vez de fabricarlas o encubrirlas.

Métrica disponible: `generated_labels`, a partir de `MissionPlan.explored_labels`
en éxito o `SearchLimitReachedError.generated_labels` en interrupción. Cuenta
etiquetas generadas/almacenadas, inicial e inactivas incluidas, **no expansiones**.
Interrupción también incluye el límite observado `max_labels`. En agotamiento,
extremos inválidos para movilidad y entrada inválida la cantidad es null: el
motor no expone ese conteo. No se inventan tiempo de búsqueda ni expansiones.

## 6. Convención de coordenadas locales

`Cell = (fila, columna)`. La fachada exige tuplas y exporta arrays JSON de dos
enteros. `LocalFrame` exige frame_id textual, resolución positiva finita y
origen XY como tupla de dos números finitos. Metadatos admitidos:

- coordinate_unit=`m`, height_unit=`m`, time_unit=`min`.
- cell_order=`row,column`.
- x_axis=`increasing_column`, y_axis=`increasing_row`.
- origin_location=`outer_corner_row0_col0`.
- origin_xy_m: esquina exterior anterior a la celda (0,0), en el marco indicado.

El centro de (r,c) es `(origin_x+(c+0.5)*resolution,
origin_y+(r+0.5)*resolution)`. Con origen (0,0) coincide con el prototipo anterior.
Y crece con la fila: no hay inversión de signo ni atribución implícita a norte.
Los waypoints son XY horizontal; las alturas de terreno se mantienen en metros
en el snapshot, sin datum planetario. Se verifica que los extremos del marco
generen XY finitos. Ejemplo probado: resolución 2, origen (10,-20), celda (0,0)
da (11,-19), celda (1,1) da (13,-17). No hay lat/lon, tf2 o transformación Jezero.

## 7. Fases, eventos y recursos

SUCCESS incluye ruta completa que termina en base, base_cell, goal_cell,
goal_index (primera llegada), waypoints_xy_m y eventos ordenados. Cada movimiento
da fase outbound o inbound; la llegada al objetivo se contabiliza como outbound
y luego se inserta exactamente un evento science/activity con inicio=fin=objetivo.
La actividad tiene distancia cero, incluso si su duración es cero.

Cada evento incluye índice, fase, tipo, celdas inicial/final, duración min,
distancia m, consumo incremental/cumulative por recurso y ficha de recursos
con consumo, capacidad, reserva, remaining y margin_above_reserve. Los acumulados
corresponden al final del evento. `remaining = capacity - cumulative_consumption`;
`margin_above_reserve = remaining - reserve`. No se descuenta la reserva dos veces
ni se recortan residuos numéricos a cero. Se conserva la tolerancia absoluta
1e-9 de los presupuestos del motor.

`phases` resume outbound, activity e inbound: duración, distancia y consumo por
recurso de esa fase. `total` contiene duración/distancia del motor y fichas
finales de recursos. La suma de eventos y de fases coincide con el total dentro
de tolerancia absoluta 1e-9 en las respectivas unidades; hay comprobación del
desglose frente al total del motor y pruebas de sumas por fases. Distancia es
horizontal; no tiene presupuesto duro.

La búsqueda y el desglose usan `planner.nav.t` y el mismo perfil. La función
compartida `movement_usage(a,b,distance)` lee altura/rugosidad de ese snapshot y
llama a la única fórmula `Consumption.traveling`. Ciencia reutiliza
`planner.activity_consumption.stationary`. No se duplicaron las fórmulas.

Se mantiene el objetivo de costo real del motor:

```text
sum(movement.minutes * (1 + hazard_cost_weight * max(0, edge_cost/distance - 1))
    + service.minutes
    + battery_cost_weight * (movement.battery_wh + service.battery_wh))
```

edge_cost es el costo geométrico existente con pendiente/riesgo/rugosidad/
proximidad. El resultado incluye esta expresión y el costo obtenido. Es una
función ponderada configurada, no una unidad física ni prueba de máxima seguridad.
SUCCESS indica admisibilidad y reservas verificadas, sin certificar optimalidad
operacional global ni una ruta físicamente segura.

## 8. Recursos excluidos y no aplicables

Unidades preservadas: time=min, battery=Wh, oxygen=simulated_u, water=L,
nutrition=kcal. Cada ficha incluye status y unit. En rover, oxygen/water/nutrition
son not_applicable; en astronauta una `ExcludedResource(reason)` conserva status
excluded y motivo, incluido en exclusions. Capacidades, reservas, consumos,
remaining y margen sin significado físico son null en esas fichas; incremental,
cumulative y consumed de fases también usan null. En la copia del perfil los
campos inexistentes se omiten, manteniendo status/unit/motivo. Nunca se exportan
los ceros del acumulador interno como disponibilidad física de esos recursos.
Un recurso modeled con tasa cero conserva cantidades numéricas significativas.

## 9. Función pública, ejemplos y JSON

Desde `prototypes/mission_planner` o agregándolo explícitamente a sys.path:

```python
from mars_route_planner import Terrain
from mars_mission_resources import small_example_profile
from mission_api import MissionRequest, TerrainReference, LocalFrame, plan_mission

t = Terrain([[0., 0., 0.]], [[False]*3], [[0.]*3], [[0.]*3], 1.)
request = MissionRequest(
    schema_version="3.0", request_id="simulated-example",
    terrain=TerrainReference.capture(t, "simulated-corridor"),
    frame=LocalFrame("LOCAL_GRID_SIMULATED", 1., (0., 0.)),
    base=(0,0), start=(0,0), goal=(0,2), activity_min=2.,
    profile=small_example_profile("astronaut"), max_labels=100,
)
result = plan_mission(request)
data = result.to_dict()
text = result.to_json()  # indent=2 por defecto; allow_nan=False
```

`to_dict()` devuelve una copia independiente compuesta exclusivamente por tipos
JSON; `to_json()` usa JSON estricto, sin NaN/Infinity. No se agregaron transporte
ni servicios. Para otro ejemplo corto: `plan_mission(example_request("rover"))`
importando example_request de demo_stage03.

Los siguientes son **extractos válidos JSON** de campos reales ejecutados, no
la forma completa del contrato. Los cinco objetos completos (incluidos perfiles,
hashes, marcos, eventos y unidades) están en
[`stage03-results.json`](../../prototypes/mission_planner/evidence/stage03-results.json).

Éxito astronauta:

```json
{
  "schema_version": "3.0",
  "request_id": "simulated-astronaut",
  "status": "SUCCESS",
  "reason_code": "MISSION_FOUND",
  "search_metrics": {
    "generated_labels": 5,
    "meaning": "explored_labels del motor cuenta etiquetas generadas, no expansiones"
  },
  "plan": {
    "path": [[0,0],[0,1],[0,2],[0,1],[0,0]],
    "goal_cell": [0,2],
    "goal_index": 2,
    "cost": 6.18,
    "total": {
      "duration_min": 6.0,
      "distance_m": 4.0,
      "resources": {
        "battery": {
          "status": "modeled", "unit": "Wh", "consumed": 18.0,
          "capacity": 19, "reserve": 1, "remaining": 1.0,
          "margin_above_reserve": 0.0
        }
      }
    }
  }
}
```

Identidad de ese terreno: terrain_id `simulated-corridor`, hash
`806b4fd5cd71437eaf6c0ab3fa3ddfea9188280224ce9b9a714c189636214df4`.
Perfil astronauta: `sim-astronaut-small`, versión `2.0`, hash
`f030cc369c80a0978f614ff3a5c7f1f348812d3a7d3789c87e2847a6d5ea179a`.
Para rover, por ejemplo, la ficha oxygen del total tiene status not_applicable,
unit simulated_u y consumed/capacity/reserve/remaining/margin_above_reserve null.

Errores de los tres escenarios demostrativos:

```json
[
  {
    "schema_version": "3.0",
    "request_id": "simulated-insufficient-budget",
    "status": "INFEASIBLE",
    "reason_code": "SEARCH_EXHAUSTED",
    "message": "Busqueda agotada sin mision admisible con ida, ciencia, regreso y reservas; no se identifica una causa unica.",
    "search_metrics": {"generated_labels": null, "meaning": "Etiquetas generadas, no expansiones"},
    "plan": null
  },
  {
    "schema_version": "3.0",
    "request_id": "simulated-label-limit",
    "status": "SEARCH_LIMIT_REACHED",
    "reason_code": "LABEL_LIMIT_REACHED",
    "message": "Busqueda interrumpida por limite de etiquetas; factibilidad desconocida.",
    "search_metrics": {"generated_labels": 1, "max_labels": 1, "meaning": "Etiquetas generadas, no expansiones"},
    "plan": null
  },
  {
    "schema_version": "3.0",
    "request_id": "simulated-invalid",
    "status": "INVALID_INPUT",
    "reason_code": "REQUEST_VALIDATION_FAILED",
    "message": "goal: coordenadas fuera del mapa",
    "search_metrics": {"generated_labels": null, "meaning": "Etiquetas generadas, no expansiones"},
    "plan": null
  }
]
```

## 10. Entorno, comandos y resultados reales

Windows/PowerShell; Python **3.11.9**, Git **2.56.0.windows.4** comprobados en:

```text
C:\Users\laura\AppData\Local\Programs\Python\Python311\python.exe
C:\Users\laura\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe
```

Solo biblioteca estándar; sin instalaciones, ROS ni Gazebo. Compatible por
sintaxis con Python 3.10+; no se ejecutaron otras versiones. Desde el checkout:

```powershell
$plannerPython = 'C:\Users\laura\AppData\Local\Programs\Python\Python311\python.exe'
& $plannerPython --version
& 'C:\Users\laura\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe' --version
& $plannerPython -m unittest discover -s prototypes/mission_planner -v
& $plannerPython prototypes/mission_planner/demo_stage03.py
& $plannerPython prototypes/mission_planner/demo_stage03.py --json
```

- Inicial antes de editar: **30/30 OK, 0.356 s**, sin fallos heredados;
  registro resumido en stage03-baseline.txt.
- Primera ejecución ampliada: 38 éxitos/1 error en fixture nueva de coordenadas:
  su mayor distancia excedía el presupuesto pequeño y la prueba asumía SUCCESS.
  Se aumentó exclusivamente la capacidad del fixture para probar coordenadas;
  no se relajó ninguna expectativa ni se modificó el motor para ocultar el fallo.
- Final: **39/39 OK, 0.468 s**, incluidas las 30 regresiones sin ediciones;
  detalle en stage03-tests.log.
- CLI legible y CLI `--json`: ambas ejecutadas, código de salida 0.
- Archivo JSON completo guardado en UTF-8 sin BOM, releído estrictamente: cinco
  escenarios. Todas las salidas pasan también serialización estricta en pruebas.
- No se repitió la demo grande astronauta: la extracción de fórmula preserva
  operaciones y no altera el algoritmo; las regresiones pequeñas comprueban el
  cambio. Su factibilidad sigue indeterminada al límite heredado de 120.000.

| Escenario simulado | Estado observado | Datos actuales |
|---|---|---|
| astronaut_success | SUCCESS | 4 m, 6 min, 18 Wh, costo 6.18, 5 etiquetas |
| rover_success | SUCCESS | 4 m, 6 min, 18 Wh, costo 6.18, 5 etiquetas; humanos not_applicable |
| insufficient_budget | INFEASIBLE / SEARCH_EXHAUSTED | Batería configurada 10 Wh, reserva 1; movimiento mínimo 8 Wh + ciencia 10 Wh > 9 Wh utilizables |
| label_limit | SEARCH_LIMIT_REACHED | 1 etiqueta; misma misión rover completa con límite 100 |
| invalid_request | INVALID_INPUT | Objetivo (0,3) fuera del corredor 1×3 |

En éxitos las fases son: outbound 2 m/2 min; activity 0 m/2 min; inbound 2 m/2 min.
Astronauta consume además O2 10 simulated_u, agua 1.2 L y nutrición 28 kcal.
Restantes: tiempo 2 min (reserva 1), batería 1 Wh (reserva 1), O2 1 (reserva 1),
agua 0.8 L (reserva 0.2), nutrición 1 kcal (reserva 1). Son cifras de perfiles
simulados de prueba, sin calibración fisiológica o mecánica.

## 11. Tabla de aceptación

Todas las pruebas nuevas están en test_stage03.py; los nombres siguientes
identifican pruebas ejecutadas en stage03-tests.log.

| # | Requisito | Evidencia aprobada |
|---|---|---|
| 1 | Solicitud astronauta/rover | test_five_scenarios_and_strict_json, test_breakdown_accounting_and_reserves |
| 2 | Versión, coordenadas, duración, metadatos, límite | test_request_validation: subcasos y verificación de que no se construye motor |
| 3 | Ida, actividad y regreso a base | test_breakdown_accounting_and_reserves |
| 4 | Actividad única/cobro exacto | mismo test y test_zero_activity_and_exact_reserves |
| 5 | Incrementos, acumulados, fases, total | test_breakdown_accounting_and_reserves, comparación interna del desglose |
| 6 | Restantes y reservas | test_breakdown_accounting_and_reserves, test_zero_activity_and_exact_reserves |
| 7 | Rover humanos not_applicable | test_breakdown_accounting_and_reserves, JSON de rover |
| 8 | Exclusión humana explícita sin disponibilidad cero | test_explicit_exclusion |
| 9 | Presupuesto insuficiente comprobable | test_five_scenarios_and_strict_json; aritmética del corredor anterior |
| 10 | Límite vs éxito con presupuesto suficiente | test_blocked_vs_invalid_and_explanations |
| 11 | INVALID_INPUT vs extremo válido bloqueado | test_request_validation, test_blocked_vs_invalid_and_explanations |
| 12 | Explicaciones honestas/errores internos | test_blocked_vs_invalid_and_explanations, test_unexpected_engine_errors_propagate |
| 13 | Origen, centros, ejes, resolución y snapshot | test_snapshot_identity_and_local_coordinates, origen no nulo y mutación externa |
| 14 | JSON estricto sin no finitos | test_five_scenarios_and_strict_json, test_request_validation para NaN/inf |
| 15 | Referencia independiente diminuta | test_independent_tiny_reference, factibilidad y costo con dos presupuestos |
| 16 | 30 regresiones conservadas | Los 30 tests de módulos anteriores pasan sin ediciones |
| 17 | Cinco demostraciones | test_five_scenarios_and_strict_json y stage03-demo.log / stage03-results.json |

## 12. Referencia matemática independiente

Retícula 2×2 plana, sin obstáculos, resolución 1 m, conectividad de ocho vecinos,
radio/margen cero, proximidad desactivada, riesgo `[[0,.7],[.1,.2]]`.
Base (0,0), objetivo (1,1), actividad 1 min, velocidad 1 m/min, tiempo capacidad
8/reserva 1. Cada movimiento dura al menos 1 min; una misión admisible puede
tener como máximo **6 movimientos**, pues la actividad consume el minuto restante
del presupuesto utilizable de 7. La enumeración recursiva explora todos los
caminos entre celdas distintas hasta esa cota, cobra ciencia en primera llegada,
y filtra tiempo/batería, incluidas reservas. Detiene un recorrido al completar
el regreso: prolongarlo no mejora costo ni factibilidad, por costos/consumos
estrictamente positivos de movimiento. La cota es completa para este fixture.

El oráculo calcula distancias con hypot y expresiones aritméticas explícitas de
tiempo, batería y riesgo del caso plano, sin llamar al planificador, a _edge ni
a Consumption. No impone desempates de ruta. Con batería 30/reserva 2, el mínimo
independiente coincide con el costo del motor **5.06636651713959** (comparación
a nueve decimales); el motor genera 7 etiquetas y la ejecución inspeccionada da
la diagonal de ida y regreso. Con batería 10/reserva 2, ambos son inviables.
La prueba compara factibilidad y costo, no exige esa ruta específica.

Es una referencia local de corrección del modelo configurado. No demuestra
optimalidad operacional global, movilidad física ni escalabilidad. No se creó
framework de evaluación o benchmark.

## 13. Compatibilidad, límites y supuestos

API heredada y perfiles de etapa 2 conservados. Solicitud nueva usa exclusivamente
from_profile. Snapshot inmutable, geometría conservadora, fórmulas y tolerancias
anteriores preservados. El costo conserva sus pesos; no se agregan heurísticas,
modelos de consumo, recarga, objetivos múltiples o rutas alternativas.

El plan es determinista y local, con terreno/perfiles simulados en ejemplos.
No certifica seguridad humana/EVA, sensores, dinámica ni operación marciana.
O2 sigue en unidades simuladas; kcal representa demanda, sin exigir ingestión.
El límite de etiquetas interrumpe y no decide factibilidad. El JSON es exportación
de resultados, no protocolo remoto. No se ejecutaron Jezero, DEM, ROS, Gazebo,
hardware, servidor o interfaz en esta etapa.

Autoría/licencia de los originales sigue pendiente de aclarar **antes de distribuir**;
no se les asigna automáticamente la licencia del repositorio. No bloqueó el
trabajo local autorizado. Pendientes breves fuera de alcance: licencia antes de
distribución, calibración física, escalabilidad e integración geoespacial futura.

## 14. Inicio de etapa 4 (sin implementación aquí)

Leer cierres 01/02/03 y README del prototipo. Comprobar el mismo checkout,
rama/HEAD y preservar todos los cambios sin commit. Reejecutar discovery (39 tests).
Para un encargo explícito de integración Jezero, inspeccionar entonces
`pilots/jezero/README.md`, `docs/jezero_pilot_codex.md` y metadatos reales del
recorte. Definir una conversión comprobada entre el raster georreferenciado y
este marco local, documentando orientación, origen, resolución, alturas y hash.
No tratar increasing_row como norte ni reemplazar datos reales por sintéticos.
Reutilizar MissionRequest/from_profile, conservar estados y significado del
límite, y acordar el alcance autorizado antes de ampliar integración. Nada de
esa transformación o integración se implementó como parte de etapa 3.

## 15. Cierre de operaciones

Todos los requisitos obligatorios están satisfechos; no hay bloqueos.
**No se hicieron commits, push ni pull requests.** No se ejecutaron clean/reset
ni operaciones destructivas. Se detiene la implementación en esta etapa.
