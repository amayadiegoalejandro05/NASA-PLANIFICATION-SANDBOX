# Auditoría numérica — etapa 6.5

Estado: **COMPLETADA**, 2026-11-08. Checkout `NASA-PLANIFICATION-SANDBOX`,
baseline `ab257374700665c47d049ae3d24fd0ba884eca62`. Cambios locales, sin publicación.
La evidencia nueva está en [stage065](../prototypes/mission_planner/evidence/stage065/).
No cierra los pendientes visuales/cartográficos de etapa 6.

## Frontera de la comprobación

| Concepto | Resultado de esta auditoría |
|---|---|
| Corrección del cálculo | Ecuaciones, cuentas independientes, presupuestos, contabilidad y dominio numérico comprobados con los casos finitos descritos aquí |
| Validez del modelo | Se documentan supuestos simplificados; aprobar aritmética no demuestra que describan una EVA real |
| Calibración | No realizada; perfiles, tasas, penalizaciones y pesos continúan simulados |
| Validación física | No realizada; sin certificación de traje, movilidad, provisión, seguridad o fisiología |

No se añaden parámetros científicos ni afirmaciones de calibración externa.
Las ecuaciones son las del modelo declarado del prototipo; los números de los
fixtures son elegidos para comprobar aritmética, no recomendaciones operacionales.
El DEM CTX y sus metadatos se usan sin modificarlos ni descargar nuevos datos.

## Inventario de ecuaciones y unidades

Rutas de código bajo [prototypes/mission_planner](../prototypes/mission_planner/).
Pruebas nuevas en [test_stage065_numerical.py](../prototypes/mission_planner/test_stage065_numerical.py).
En la columna de pruebas se abrevia `IndependentAccounts` como IA y
`BudgetAndDomain` como BD; ambos pertenecen a ese archivo.

Símbolos: s=resolución; d=distancia horizontal; dz=altura final menos inicial;
g=max(0,dz)/d; r=promedio de rugosidad de extremos; v=velocidad; t=minutos;
M/A=tasas de movimiento/actividad. No se usa longitud 3D como distancia declarada.

| Magnitud / campo | Unidad | Fórmula o conversión; dominio | Naturaleza y responsable | Prueba |
|---|---|---|---|---|
| Resolución `Terrain.resolution_m` | m/celda | s>0, finita; dimensiones métricas representables | Dato de snapshot; `Terrain.__post_init__` | IA.geometry_units_and_weighted_cost; BD.invalid_public_numbers |
| Distancia `Route.distance_m`, `Usage.distance_m` | m | d=hypot(dr,dc)*s, vecinos de ocho direcciones; total suma aristas | Geometría; `RiskAwareAStar._edge/plan` | IA.geometry_units_and_weighted_cost; IA.flat_ascent_descent_rough_diagonal |
| Centro `LocalFrame.waypoint` | m | origen+((c+.5)s,(r+.5)s); X columnas, Y filas | Convención local, sin datum terrestre; `LocalFrame` | IA.geometry_units_and_weighted_cost; regresiones stage04/maps |
| Altura y ascenso `heights_m`, `rise_m` | m | dz=zb-za; solo max(0,dz) penaliza consumo; alturas finitas o None desconocido | DEM o fixture identificado; `movement_usage` | IA.flat_ascent_descent_rough_diagonal; IA.shared_accounting_same_sloped_path_v3_v5 |
| Pendiente local/arista `_slopes`, `edge_slope` | grados | atan(hypot(gradX,gradY)) y atan(abs(dz)/d), convertidos con degrees; diferencias centrales o unilaterales | Geometría discreta; `_terrain_slope`, `_edge` | IA.geometry_units_and_weighted_cost; stage01 |
| Grado ascendente `uphill_grade` | adimensional | max(0,dz)/d; d>0 | Modelo simplificado; `Consumption.traveling` | IA.flat_ascent_descent_rough_diagonal |
| Rugosidad `roughness` y riesgo `risk` | adimensional [0,1] | Media aritmética de extremos para arista; no probabilidad calibrada | Capas declaradas; neutras en CTX, simuladas en fixtures | IA.geometry_units_and_weighted_cost; IA.flat_ascent_descent_rough_diagonal |
| Velocidad `speed_m_per_min` | m/min | v>0; no se usa km/h ni m/s | Simulada; `Consumption`/`MotionModel` | IA.flat_ascent_descent_rough_diagonal; BD.invalid_public_numbers |
| Tiempo movimiento `Usage.minutes` | min | t=d/v*(1+uphill_speed_penalty*g+roughness_speed_penalty*r) | Modelo simulado; `Consumption.traveling` | IA.flat_ascent_descent_rough_diagonal |
| Esfuerzo `uphill_effort_penalty` | adimensional | e=1+uphill_effort_penalty*g | Simulado, no fisiología validada; `Consumption.traveling` | IA.flat_ascent_descent_rough_diagonal |
| Batería `battery_wh` | Wh | t*M_battery+max(0,dz)*climb_battery_wh_per_m | Tasas Wh/min y ascenso Wh/m simulados; `Consumption.traveling` | IA.flat_ascent_descent_rough_diagonal; IA.scenario_scales_rates_only |
| Agua `water_l` | L | t*M_water*e; tasa L/min | Simulada; `Consumption.traveling` | IA.flat_ascent_descent_rough_diagonal |
| Oxígeno `oxygen_u` | simulated_u | t*M_oxygen*e; tasa simulated_u/min | Unidad ficticia sin conversión física; `Consumption.traveling` | IA.flat_ascent_descent_rough_diagonal |
| Demanda energética `nutrition_kcal` | kcal | t*M_nutrition*e; tasa kcal/min | Demanda parametrizada simulada; `Consumption.traveling` | IA.flat_ascent_descent_rough_diagonal |
| Actividad `stationary`, `activity_min` | min, unidades de recurso | t>=0; incremento=t*A para cada recurso, distancia=0; tasa tiempo=1 | Tasas A independientes de M; `Consumption.stationary`, `AgentProfile._engine_inputs` | IA.stationary_and_distinct_activity_rates |
| Capacidades originales `ResourceAllocation.capacity` | unidad de cada recurso | >=reserva>=0, finitas; no magnitud física certificada | Entrada declarada; `ResourceAllocation` | BD.exact_insufficient_and_tolerance; BD.zero_capacity_equal_reserve_and_below |
| Saldo actual `MissionState.remaining` | unidad de cada recurso | 0<=saldo<=capacidad original; histórico es informativo | Estado manual; `MissionState`, `DecisionRequest.validate` | BD.exact_insufficient_and_tolerance; stage05 |
| Reserva `reserve`, `state.reserves` | unidad de cada recurso | Absoluta, igual a original; no se escala por saldo o escenario | Contrato; `Budget`, `DecisionRequest.validate` | BD.exact_insufficient_and_tolerance |
| Consumo futuro y restante `_resources` | unidad de cada recurso | usado=sum(incrementos); remaining=saldo-usado; margin=remaining-reserva | Fuente común de contabilidad y salida; `_breakdown`, `_resources` | IA.roundtrip_completed_initial_goal_and_direct_returns; BD.exact_insufficient_and_tolerance |
| Factibilidad `Budget.fits` | comparación por recurso | usado<=saldo-reserva+1e-9; no restringido si presupuesto legado None | Regla declarada, no seguridad física; `Budget.fits` | BD.exact_insufficient_and_tolerance |
| Escenario `RateScenario.factors` | adimensional | Nominal=1; conservador>=1, tiempo=1; M'=M*f y A'=A*f | Sensibilidad determinista; `effective_future_profile` | IA.scenario_scales_rates_only |
| Preparación `required_initial` | unidad de cada recurso | consumo completo candidato+reserva; nuevo saldo=max(saldo,required); capacidad=max(capacidad,nuevo saldo) | Simulación del escenario; `fast_mission`, botón `adjustResources` | FastAccounting.preparation_complete_candidate_preserves_rates_and_scenario; test_stage065_preparation.cjs |
| Exportaciones | m, min, Wh, L, simulated_u, kcal | Valores sin redondeo decisorio; JSON allow_nan=False; estados y None conservados | `MissionResult`, `DecisionResult`, `mission_ui.strict` | IA.roundtrip_completed_initial_goal_and_direct_returns; BD.applicability_at_events_phases_totals_json; FastAccounting |

Los nombres de test de la tabla omiten únicamente el prefijo `test_`.
La tolerancia no convierte recursos con unidades distintas: cada comparación
usa la unidad de su propio campo.

### Costos: significado y pesos implícitos

`RiskAwareAStar._edge` usa:

```text
p = max(pendiente local A, pendiente local B, pendiente arista)
near = max(0,(near_obstacle_m-clearance)/near_obstacle_m), o 0 si denominador=0
coste = d*(1 + slope_weight*(p/max_slope_deg)^2
             + risk_weight*riesgo_medio + roughness_weight*rugosidad_media
             + proximity_weight*near)
```

Pendientes, huella, obstáculos, esquina y barrido son restricciones previas.
Los pesos son adimensionales; este costo tiene dimensión de longitud ponderada,
no energía física ni probabilidad de riesgo. La heurística sigue siendo distancia
euclídea. No se cambian aristas, heurística, pesos nominales ni condiciones duras.

La búsqueda detallada suma:

```text
move_min*(1 + hazard_cost_weight*max(0,edge_cost/d-1))
    + activity_min + battery_cost_weight*(move_Wh+activity_Wh)
```

`hazard_cost_weight` es adimensional; `battery_cost_weight` tiene unidad implícita
min/Wh. El costo agregado es tiempo ponderado, no energía, y no se comparan
costos entre políticas con pesos distintos. La recomendación conserva menor
tiempo total, después menor batería y orden balanced/minimum_time/terrain_caution.
Dominancia y tolerancias heredadas permanecen sin cambios.

## Cuentas independientes finitas

Todos los esperados se escriben como números o expresiones matemáticas en tests;
ninguna función de producción genera su propio valor esperado. Tupla usada aquí:
**(min, O2 simulated_u, agua L, batería Wh, demanda kcal, distancia m)**.

Para movimiento elemental se fija v=10 m/min; M=(O2=1, agua=.1,
batería=2, kcal=4) por minuto; penalizaciones ascenso=2, rugosidad=.5,
esfuerzo=2 y ascenso batería=3 Wh/m.

| Caso | Cuenta independiente | Esperado |
|---|---|---|
| 1. Plano | d=10; t=10/10=1; esfuerzo=1 | (1,1,.1,2,4,10) |
| 2. Ascenso | dz=2; g=.2; t=1*(1+2*.2)=1.4; e=1.4; batería=1.4*2+2*3 | (1.4,1.96,.196,8.8,7.84,10) |
| 3. Descenso | dz=-2; g=0; sin regeneración ni penalización descendente | (1,1,.1,2,4,10) |
| 4. Rugosidad | r=.4; t=1*(1+.5*.4)=1.2 | (1.2,1.2,.12,2.4,4.8,10) |
| 5. Diagonal | d=10√2, t=√2; misma tasa plana | (√2,√2,.1√2,2√2,4√2,10√2) |
| 6. Estacionaria | 2 min; A=(3,.4,5,6) por min; sin distancia/ascenso | (2,6,.8,10,12,0) |
| 7. Tasas distintas | 2 m a 1 m/min con M=(1,.1,2,4), comparado con 2 min de A anterior | Movimiento (2,2,.2,4,8,2); actividad (2,6,.8,10,12,0) |
| 8. Ida, actividad, regreso | Línea 0→1→2→1→0, s=1 m, v=1; 4 min M +2 min A | (6,10,1.2,18,28,4) |
| 9. Actividad completada | Mismo path; 4 min M, cero A | (4,4,.4,8,16,4) |
| 10. Inicio en objetivo | 2 min A al inicio, 2 m vuelta hasta base | (4,8,1,14,20,2) |
| 11. Regreso directo | Celda1→base0, 1 m; sin revisita ni A | (1,1,.1,2,4,1) |
| 12. Regreso desde base | Path de una celda, sin movimiento ni A | (0,0,0,0,0,0) |

La prueba `roundtrip_completed_initial_goal_and_direct_returns` contrasta también
incrementos, acumulados de eventos, fases y total. Prueba pendiente al inicio como
primer evento de ciencia y cero eventos de ciencia al regresar/completar.

Fixture adicional con pendiente y rugosidad: línea de alturas [0,2,4] m,
s=10 m, r=.4, ida y regreso. Cada arista ascendente dura 1.6 min y tiene
esfuerzo 1.4; cada descendente dura 1.2 min. Actividad 2 min con A anterior.
Resultado (7.6,12.88,1.488,33.2,39.52,40). Solicitudes 3.0 y 5.0 coinciden;
el modo rápido y detallado se comparan cuando efectivamente tienen el mismo path.
No se exige que métodos distintos siempre elijan igual recorrido.

Costos geométricos: cuadrado s=10 m, riesgo=.5, rugosidad=.4, pesos 2 y 1.5,
otros pesos cero: multiplicador 2.6; diagonal d=10√2, costo=26√2; centros
(5,5)→(15,15) m. Ascenso 2/10 tiene pendiente atan(.2)=11.309932°.

## Capacidades, saldos, reservas y bordes

Se utilizan reservas diferentes: tiempo10 min, batería7 Wh, O2 3 simulated_u,
agua .2 L, demanda11 kcal. El presupuesto exacto de la misión plana de caso8 es
saldo=(16 min,25 Wh,13 simulated_u,1.4 L,39 kcal).
El consumo se resta una sola vez; restante final=reservas y margen≈0.
Histórico informativo batería123 Wh no se vuelve a restar.
Reducir separadamente cada saldo en 1e-7 de su unidad produce INFEASIBLE.

Capacidad igual a reserva admite consumo cero (regreso desde base), pero no
permite una misión que necesite consumir ese recurso. Saldo menor que reserva
produce BALANCE_BELOW_RESERVE incluso con futuro cero. La validación no rebaja
reservas. También se comprueba recurso modelado con tasa cero.

Tolerancia heredada de presupuesto/dominancia/desglose: **absoluta 1e-9** en
cada unidad (min, Wh, L, simulated_u, kcal; distancia m en consistencia).
La dominancia aplica además 1e-9 a su costo ponderado. A* conserva 1e-10 en
comparaciones de costo geométrico. No son incertidumbres instrumentales ni
tolerancias relativas. Ejemplo: presupuesto útil 7 min acepta 7+5e-10,
rechaza 7+2e-9. Por ello SUCCESS puede tener un margen negativo de magnitud
no superior a 1e-9; no se recorta el saldo de exportación para ocultarlo.
Los perfiles/saldos/reservas se validan con desigualdades estrictas heredadas,
no con esa tolerancia de búsqueda.

## Dominio numérico y errores

Entradas numéricas del CORE auditadas: `int`/`float` de Python, finitos y
representables por binary64, sin bool, cadenas ni tipos incompatibles. Enteros
tan grandes que `math.isfinite` desborda se rechazan con ValueError. No se promete
soporte de Decimal, Fraction o escalares NumPy en contratos públicos tipados.
Alturas negativas y descenso son válidos; alturas desconocidas son None.
Resolución, velocidad y distancia de movimiento requieren >0; duración y tasas
pueden ser cero; riesgo/rugosidad están en [0,1]; pendiente límite en (0,90).
Capacidades y reservas no negativas, reserva<=capacidad; límites de búsqueda
enteros positivos sin bool. Tiempo siempre tiene presupuesto y tasas 1.

No basta que cada entrada sea finita: diferencias de alturas, gradientes,
extensiones, costos, prioridades, factores aplicados, consumos, acumulados y
márgenes comprobados deben seguir siendo representables. No se promete exactitud
decimal arbitraria ni precisión relativa para magnitudes subnormales. El caso
de tiempo de viaje que subdesborda a cero con distancia positiva se rechaza.
No se agregan cotas operacionales artificiales para masas, tasas o distancias.

`numeric_domain.py` centraliza validación aritmética, sin fórmulas de recursos.
`NumericDomainError(ValueError)` identifica desbordamientos derivados soportados:

- Constructores y métodos numéricos directos: ValueError; derivación fuera de
  dominio: NumericDomainError.
- Fachadas 3.0/5.0: INVALID_INPUT / NUMERIC_DOMAIN_EXCEEDED, plan=None.
- Modo rápido: UIInputError, que el transporte local trata como entrada inválida
  HTTP400. No se devuelve candidato con consumos no finitos.
- SEARCH_LIMIT_REACHED sigue significando cálculo interrumpido, factibilidad
  desconocida; INFEASIBLE mantiene su significado previo dentro de cada método.
- Errores internos inesperados no son capturados por un `except Exception` nuevo:
  una regresión inyecta RuntimeError en el motor y verifica su propagación.
  Desacuerdos genuinos de desglose siguen siendo RuntimeError.

No se modifica versión 3.0/5.0/6.1 ni estructura de campos; se amplían el rechazo
de entradas inválidas y el reason_code de un estado existente. Los consumos de
entradas ordinarias válidas conservan ecuaciones y unidades.

## Defectos ejecutados y correcciones

| Defecto reproducido | Antes | Corrección mínima / regresión |
|---|---|---|
| Distancia negativa, NaN en ascenso, bool numérico | traveling(-1,0,0) daba -1 min; rise NaN se ocultaba en max(0,NaN); velocidad y actividad True aceptadas | Comprobación de tipo/dominio en primitivas y constructores; BD.invalid_public_numbers |
| Uso no finito incluso sin presupuesto humano | Usage(oxygen_u=inf) podía pasar Budget(10,0).fits | Usage valida acumulados finitos/no negativos, incluidos recursos no restringidos; BD.overflow_usage_addition_and_geometry_are_not_infeasibility |
| Desbordamiento de consumo | 2 min*1e308 Wh/min daba inf Wh | Rechazo de resultados y sumas fuera de dominio; fachadas no lo llaman inviabilidad; BD.overflow_facades_strict_json_and_unexpected_error |
| Desbordamiento geométrico | d=2, riesgo1, peso1e308 terminaba en NoSafeRouteError | Comprobar costo/prioridad y derivadas antes de usarlos; BD.overflow_usage_addition_and_geometry_are_not_infeasibility |
| Escenario con producto desbordado | factor batería1e308 sobre tasa actividad5 escapaba como ValueError sin resultado 5.0 | Guardar multiplicación con NumericDomainError y frontera específica INVALID_INPUT; BD.overflow_facades_strict_json_and_unexpected_error |
| Orden de suma rápido | Actividad1e8 min y cuatro movimientos .1 min provocaban desacuerdo >1e-9 con eventos | Suma cronológica ida→actividad→regreso, incluyendo actividad al inicio; FastAccounting.large_finite_activity_same_chronological_sum |
| Subdesbordamiento de duración | d=1e-308 m y v=1e308 m/min devolvía 0 min | NumericDomainError para viaje de duración numérica cero; BD.overflow_usage_addition_and_geometry_are_not_infeasibility |

Evidencia previa: `reproduced-before.json`, `underflow-before.json` y
`numerical-second.log` (desacuerdo de suma). `numerical-first.log` conserva un
error del test nuevo: pretendía que nutrición modelada fuese cero, corregido para
comprobar únicamente O2 con tasa cero. `preparation-js.log` conserva un fallo del
doble DOM por prototipos entre contextos VM; se corrigió la comparación del test,
sin tocar la aplicación. No se debilitan resultados esperados para ocultar fallos.

## Perfiles, demanda energética y escenarios

Astronauta: recursos humanos modelados o excluidos con motivo explícito.
Rover: recursos humanos ausentes del perfil tipado; intentar añadirlos se rechaza.
Modelado con tasa cero mantiene capacidad/reserva y consumo0; excluded y
not_applicable mantienen cantidades null, no disponibilidad física cero.
Se comprueban estados en eventos/total y null en incrementos, fases y JSON,
conservando el contrato existente de fases que no tiene campo status propio.
Masa y altura siguen como metadatos informativos sin efecto.

`nutrition_kcal` es una **demanda energética estimada bajo tasas simuladas**.
Su presupuesto limita esa demanda contabilizada; no representa automáticamente
alimento transportado o cantidad que deba ingerirse durante la misión. El modelo
no describe ingestión, absorción, metabolismo individual, nutrición diaria ni
reservas fisiológicas. No se renombra el contrato ni se prescribe alimentación.
O2 continúa en simulated_u: sin equivalencia a masa, presión o volumen físico.

Escenario conservador multiplica ambas tasas de cada recurso modelado excepto
tiempo; no cambia velocidad, coeficiente de ascenso Wh/m, movilidad, reservas o
histórico. Ejemplo ascenso: t=1.4, batería 2→4 Wh/min, dz=2 m y coeficiente
3 Wh/m: 1.4*4+2*3=11.6 Wh; no 17.6 Wh. No es percentil, intervalo de confianza
ni peor caso integral.

## Preparación y consistencia de exportaciones

Fixture pendiente/rugoso de 40 m con factor1.25: batería de dos subidas
1.6*2.5+6 cada una, dos bajadas1.2*2.5 y actividad2*6.25 =38.5 Wh;
reserva7 Wh exige45.5 Wh. Solo se aumenta batería cuando los otros saldos ya
alcanzan. No se recalculan tasas ni se cambia terreno, actividad, puntos o factores.

Ensayo adicional real, sin descargar CTX: salida [50,49], destino [50,80],
obstáculos simulados [49,60],[50,60],[51,60], modo rápido astronauta.
`preparation.json` guarda configuración, candidato, ajuste y nuevo SUCCESS con
el mismo path; consumo batería680.5748291304726 Wh +reserva10 Wh requiere
690.5748291304726 Wh. Se conservan unidades, perfiles, factores, identidad
de snapshot y coordenadas/waypoints del puente existente.

La nueva suite JS ejecuta **el manejador real** de preparación con ese payload:
comprueba precisión sin redondear, un recurso que ya alcanza, tasas/reservas,
configuración relevante, registro de ajustes, una solicitud de recálculo y bloqueo
de resultado obsoleto. El transporte se sustituye por un capturador para comprobar
la configuración enviada; la verificación del candidato con el motor se ejecuta
separadamente en Python. Es un doble DOM, no nueva evidencia de navegador.
El redondeo a tres decimales queda solo en presentación.

Se conserva explícitamente el límite semántico rápido: rechazar SU candidato por
recursos no prueba imposibilidad de todas las misiones. No se corrige aquí el
código INFEASIBLE/FAST_ROUTE_NEEDS_RESOURCES: intervención reservada a 6.6.

## Reproducción y resultados reales

Desde raíz SANDBOX en PowerShell, con `.venv` existente:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -v
& .\.venv\Scripts\python.exe prototypes/mission_planner/evidence/stage065/generate_evidence.py
& 'C:\Users\laura\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' prototypes/mission_planner/evidence/stage065/run_frontends.cjs
```

El generador reescribe únicamente sus dos archivos nuevos en stage065, no evidencia
histórica ni datos. El runner Node redirige las escrituras de logs históricos a
stage065 manteniendo las dos suites originales sin editar.

Para la selección CORE sin dependencias, desde `prototypes/mission_planner`:

```powershell
& ..\..\.venv\Scripts\python.exe -S -m unittest test_mars_route_planner test_mars_mission_resources test_stage01 test_stage02 test_stage03 test_stage05 test_stage065_numerical -v
```

| Ejecución | Resultado | Evidencia stage065 |
|---|---|---|
| Referencia antes de instalar dependencia | 64 tests; 5 errores y 6 skips por NumPy ausente | baseline-initial.log |
| Dependencia existente declarada | Instalado NumPy2.2.6 en .venv propio; Python3.11.9, pip24.0, setuptools65.5.0 | install.log, dependencies*.txt, environment.json |
| Referencia completa antes de editar motor | 101/101, 18.507 s, sin skips | baseline.log |
| Dos suites JS originales antes de editar | PASS ambas, Node24.22.1; logs redirigidos | stage06-baseline-js.log, stage06_maps-baseline-js.log |
| Suite final tras correcciones | **117/117, 19.168 s, sin skips** | tests-final.log |
| CORE -S (55 heredadas+16 nuevas) | **71/71, 2.623 s, sin skips** | core-no-site.log |
| Dos suites JS originales+preparación nueva | **3 PASS** | javascript-final.log |
| CTX preparación y revalidación | SUCCESS mismo path; exportación JSON estricta | preparation.json, generate.log |

Se autorizó ejecución fuera del aislamiento que impedía Git/acceso al checkout;
las pruebas HTTP locales pudieron ejecutarse sin omisiones. No se copiaron entornos.
Un intento de selección sintética desde raíz produjo errores de import por cwd;
se corrigió al directorio del prototipo (comando anterior). No era fallo del CORE.
No se repite navegador en esta auditoría sin cambios de interfaz.

## Continuidad acotada

6.6 debe empezar por un caso donde el candidato rápido falle y el detallado pueda
encontrar otra ruta, y versionar/definir su semántica antes de cambiar estados.
6.7 revisará comunicación visual; 6.8 contratos/integración; 6.9 rendimiento.
Nada de ello se implementa en 6.5. Permanecen sin calibrar consumos humanos,
movilidad, esfuerzo y O2 ficticio; faltan procesos fisiológicos y ambientales.
El CORE conserva únicamente biblioteca estándar, sin imports de UI, red o ROS.
