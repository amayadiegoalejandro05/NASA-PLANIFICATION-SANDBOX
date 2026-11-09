# ETAPA 02 — Perfiles y recursos

Estado: COMPLETADA. Fecha: 2026-11-05, America/Bogota.

## Alcance y estado heredado

Se incorporaron perfiles explícitos y contratos de recursos, tasas de movimiento
 y actividad diferenciadas, validación previa a búsqueda, ejemplos simulados,
pruebas y documentación. No se inició etapa 3 ni se implementaron HTTP, interfaz,
ROS, hardware, DEM, telemetría, múltiples objetivos o nuevas fases.

Checkout: `C:\Users\laura\OneDrive\Escritorio\MARS GOD EYE\NASA-Sandbox-etapa01`.
Rama comprobada: `etapa01-base-confiable`.
Commit base/HEAD: `0d5a444f5444b4dfa574224c9f7d09652dad1df5`.
Estado inicial: `?? docs/continuidad/` y `?? prototypes/`; trabajo válido heredado
sin commit, preservado en este mismo checkout. No hubo diferencias con el cierre.
No se clonó, cambió de rama, limpió ni revirtió trabajo desconocido.

Se leyeron AGENTS.md raíz (único localizado), README raíz, escenario y procedencia,
cierre 01, README y módulos/pruebas del prototipo. Contexto maestro localizado en
`prototypes/mission_planner/originals/Proyecto_MARS_GODS_EYE_Contexto_Maestro.md`;
auditoría en `../AUDITORIA_MISSION_PLANNER_2026-11-05.md`. Sus propuestas futuras
se trataron como antecedentes, sin ejecutar instrucciones históricas de expansión.
Las instrucciones Gazebo se refieren al mundo/piloto que no se modifica aquí.
No se usaron cifras científicas externas ni se instalaron dependencias.

## Archivos de esta etapa

| Archivo | Propósito |
|---|---|
| prototypes/mission_planner/mars_mission_resources.py | Contratos, adaptación única al motor, tasas de ciencia y demos explícitas |
| prototypes/mission_planner/test_stage02.py | Nueve pruebas con subcasos de aceptación |
| prototypes/mission_planner/README.md | Entrada, unidades, fórmulas, exclusiones y migración |
| prototypes/mission_planner/evidence/stage02-baseline.txt | Referencia inicial registrada tras ejecución |
| prototypes/mission_planner/evidence/stage02-tests.log | Resultado real de suite ampliada |
| prototypes/mission_planner/evidence/stage02-resources.log | Demos grandes y pequeñas |
| prototypes/mission_planner/evidence/stage02-route.log | Demo geométrica de regresión |
| docs/continuidad/ETAPA_02_CIERRE.md | Este cierre |

No se modificaron motor geométrico, originales, cierre 01 ni las 21 regresiones.
Los archivos del prototipo siguen sin seguimiento respecto a HEAD.

## Contrato de perfiles y recursos

Entrada nueva: `ResourceMissionPlanner.from_profile(terrain, profile)`.
`AgentProfile` es un contrato discriminado cerrado: `astronaut` o `rover`.
Obligatorios: agent_type, profile_id, version, parameter_nature, provenance,
limitations, Mobility, MotionModel y resources. Texto no vacío; variantes
inválidas y claves inesperadas se rechazan al construir, antes de búsqueda.
Perfil, movilidad, modelo y asignaciones son frozen; resources se copia y expone
como MappingProxyType. El planificador conserva el perfil en `planner.profile`.

| Recurso | Unidad | Astronauta | Rover |
|---|---|---|---|
| time | min | presupuesto obligatorio | presupuesto obligatorio |
| battery | Wh | batería del traje obligatoria | presupuesto obligatorio |
| oxygen | unidades simuladas | presupuesto o exclusión explícita | no aplica |
| water | L | presupuesto o exclusión explícita | no aplica |
| nutrition | kcal de demanda energética | presupuesto o exclusión explícita | no aplica |

ResourceAllocation exige capacidad, reserva, tasa de movimiento y tasa de
actividad, todos finitos >=0; reserva <= capacidad. Igualdad válida, aunque el
consumo puede hacer inviable la misión. Tasas en unidad/minuto, salvo tiempo
que exige ambas tasas =1. Velocidad m/min >0; huella circular de radio y margen
en m; pendiente en grados y coeficientes no negativos, finitos. Distancia m es
métrica horizontal, sin presupuesto duro.

Un recurso aplicable con tasas cero es `modeled`. Un humano omitido del modelo
experimental requiere `ExcludedResource(reason)` no vacío, sin campos de tasas,
reserva o capacidad: `excluded`. Para rover, la ausencia de todas las claves
humanas significa `not_applicable`; incluir cualquiera se rechaza incluso a
cero o como exclusión. No se usan None/ceros de entrada para ocultar omisiones.
Tiempo/batería no admiten exclusión. resource_status distingue los tres estados.
Usage conserva acumulados genéricos; consultar perfil para interpretar ceros.

Todo el conjunto de ejemplos tiene naturaleza `simulated`, versión 2.0,
identificador, procedencia y limitaciones explícitas. Son supuestos configurables
heredados o aritméticos, sin calibración fisiológica o mecánica. O2 no tiene
conversión a litros, masa ni presión. kcal no exige ingestión en misión breve.
No hay validación de seguridad humana/EVA.

## Movimiento, actividad y compatibilidad

Se conservan fórmulas de Consumption.traveling:
g=max(0,ascenso)/distancia;
t=distancia/velocidad*(1+penalización_ascenso*g+penalización_rugosidad*r).
O2/agua/nutrición = t*tasa_movimiento*(1+penalización_esfuerzo*g).
Batería=t*tasa_movimiento+ascenso_positivo*Wh_por_m.
Actividad = duración*tasa_actividad, más su tiempo, exactamente una vez en la
primera llegada al objetivo. Duración cero no agrega consumo. Se comprueba
capacidad menos reserva sobre el acumulado común. Sin regeneración ni recarga.

No cambian objetivo, ordenación, dominancia, snapshot, geometría ni excepciones.
Tolerancia absoluta preexistente 1e-9 para presupuestos y dominancia.
max_labels sigue entero positivo excluyendo bool, incluida etiqueta inicial;
no se elevó el límite de 120.000 ni se optimizó el algoritmo.

Constructor heredado `(terrain, config, consumption, budget)` conservado; no
ofrece separación garantizada de perfiles. Sigue usando tasas iguales para ambas
fases. Migración: expresar movilidad con `Mobility.agent_radius_m`, modelo con
MotionModel y recursos con asignaciones/exclusiones; llamar from_profile.
Internamente se adapta al nombre histórico PlannerConfig.rover_radius_m,
Consumption/Budget y la misma búsqueda. No hay motor duplicado ni plugins.
Los ejemplos principales ya no usan el constructor heredado.

## Ejemplos mínimos reproducibles

Desde prototypes/mission_planner:

```python
from mars_mission_resources import small_demo, small_example_profile
astronaut = small_demo('astronaut')
rover = small_demo('rover')
profile = small_example_profile('astronaut')
```

Ambos recorren (0,0)->(0,1)->(0,2)->(0,1)->(0,0), resolución 1 m,
velocidad 1 m/min, ciencia 2 min. Cuatro minutos de movimiento más dos de
actividad = 6 min; batería 4*2+2*5=18 Wh. Astronauta: O2 4*1+2*3=10 u
simuladas; agua 4*.1+2*.4=1.2 L; demanda 4*4+2*6=28 kcal.
Rover: recursos humanos no aplican, acumulados internos cero.

## Entorno, comandos y resultados

Windows/PowerShell, Python 3.11.9, biblioteca estándar (compatible por sintaxis
con 3.10+; no se ejecutó otra versión). Ejecutables comprobados:

- Python: `C:\Users\laura\AppData\Local\Programs\Python\Python311\python.exe`
- Git: `C:\Users\laura\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe`

Desde el checkout indicado:

```powershell
$plannerPython = 'C:\Users\laura\AppData\Local\Programs\Python\Python311\python.exe'
& $plannerPython -m unittest discover -s prototypes/mission_planner -v
& $plannerPython prototypes/mission_planner/mars_route_planner.py
& $plannerPython prototypes/mission_planner/mars_mission_resources.py
```

Referencia inicial ejecutada antes de editar: 21/21 OK, 0.305 s; sin fallos previos.
Suite ampliada: 30/30 OK, 0.309 s. Las 21 regresiones permanecen intactas.
Demo A*: 28 celdas, 6.39 m, costo 7.56, pendiente 1.0 grados; código 0.
Los detalles de recursos se registran en stage02-resources.log.

## Tabla de aceptación

| Criterio | Evidencia | Resultado |
|---|---|---|
| 1 Perfiles válidos | test_small_astronaut, test_small_rover | Cumple |
| 2 Rover rechaza humanos, tasas/reservas | test_rover_rejects_human_inputs con cada clave y tasas cero/activas, reservas, exclusión | Cumple |
| 3 No aplica/excluido/cero | test_status_and_exclusion | Cumple |
| 4 Negativos, NaN, infinitos, velocidad cero | test_numeric_validation, todos los coeficientes y campos de asignación | Cumple |
| 5 Reserva > capacidad | test_numeric_validation | Cumple |
| 6 Presupuesto exacto y reserva | test_exact_reserves_and_short_budget: todos los recursos | Cumple |
| 7 Inferior causa inviabilidad | mismo test, déficit 1e-6 por recurso; excepción distinta de límite | Cumple |
| 8 Tasas de ciencia distintas | test_activity_once_and_zero, 2 vs 5 Wh/min | Cumple |
| 9 Ciencia una vez y duración cero | mismo test, acumulados manuales | Cumple |
| 10 Astronauta ida/ciencia/regreso | test_small_astronaut, vector manual | Cumple |
| 11 Rover sin humanos | test_small_rover, 6 min y 18 Wh | Cumple |
| 12 Movilidad diferenciada | test_mobility, radio .6 y pendientes 10/30 grados | Cumple |
| 13 Metadatos y ejemplos simulados | test_metadata y factories inspeccionadas | Cumple |
| 14 Regresiones | 21 tests anteriores sin cambios, 30 total | Cumple |
| 15 Demos controladas | logs stage02-route/resources; test_cli_interrupted y pruebas de inviabilidad/límite | Cumple |

## Limitaciones y pendientes fuera de alcance

Modelo determinista sintético, sin calibración ni certificación EVA. La huella
conservadora y crecimiento multietiqueta mantienen sus límites de etapa 1. La
interrupción computacional no demuestra inviabilidad. Sin Jezero/Gazebo/ROS
 ejecutados en esta etapa. No se han incorporado contratos generales de misión.
La cuestión de autoría/licencia de originales sigue pendiente antes de
redistribución, sin bloquear el trabajo local autorizado.

Pendientes: licencia antes de distribución; contratos y coordenadas de etapa 3;
calibración real y escalabilidad quedan para encargos futuros. No se implementan.

## Inicio concreto de etapa 3

Leer cierres 01 y 02 y README; comprobar rama/HEAD y preservar archivos locales
sin commit. Reejecutar discovery anterior (30 pruebas). Usar from_profile como
entrada validada, mantener API heredada solo como compatibilidad. Acordar alcance
de contratos de misión/coordenadas antes de implementarlos; no mezclar con
Jezero, telemetría o transporte implícitamente. Mantener tres resultados distintos
y no interpretar la demo grande interrumpida como misión aprobada.

No se hicieron commits, push ni pull requests. No hay bloqueos obligatorios.
Implementación detenida al cumplir la etapa 2.

## Resultado ejecutado de las demos de recursos

`mars_mission_resources.py` finalizó con código 0:

| Demo | Resultado observado |
|---|---|
| Astronauta grande | SearchLimitReachedError controlado: 120.000 etiquetas; factibilidad no determinada |
| Rover grande | Éxito: 12.8 m, 91.0 min, 81.9 Wh, 1.145 etiquetas; humanos no aplican |
| Astronauta pequeño | Éxito: 4 m, 6 min, 10 u O2 simulado, 1.2 L, 18 Wh, 28 kcal, 5 etiquetas |
| Rover pequeño | Éxito: 4 m, 6 min, 18 Wh, 5 etiquetas; humanos no aplican |

La CLI continuó tras la interrupción. La inviabilidad se ejecutó en pruebas con
presupuesto insuficiente y en la prueba de clasificación CLI (sin confundirla
con interrupción). No se afirma que la demo grande del astronauta haya completado.
