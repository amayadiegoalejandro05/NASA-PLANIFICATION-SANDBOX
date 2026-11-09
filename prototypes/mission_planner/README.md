# Prototipo independiente Mission Planner

## Interfaz local — ampliación en curso

Mapa real navegable de Jezero, selección por clic y cálculo Python. En PowerShell,
desde cualquier directorio:

```powershell
& 'C:\Users\laura\OneDrive\Escritorio\MARS GOD EYE\NASA-Sandbox-etapa01\.venv-stage04\Scripts\python.exe' 'C:\Users\laura\OneDrive\Escritorio\MARS GOD EYE\NASA-Sandbox-etapa01\prototypes\mission_planner\mission_ui.py'
```

Abrir [http://127.0.0.1:8766/](http://127.0.0.1:8766/). Detener con **Ctrl+C** en
la consola de arranque. Si ya existe una instancia, usarla o detenerla primero.
Solo escucha en 127.0.0.1. Usa NumPy del entorno Jezero existente y Leaflet 1.9.4
local con su licencia; no necesita cuentas ni claves.

1. Explorar Jezero y cambiar imagen CTX, relieve o elevación.
2. Pulsar **Área de cálculo**: 2 × 2 km, celdas CTX de 20 m. La cobertura
   cartográfica es mayor; no se puede calcular fuera del polígono habilitado.
3. Elegir agente y usar **Marcar salida / Marcar destino** antes de clicar en el
   mapa. Se indica el ajuste del clic al centro utilizado por el motor.
4. Configurar actividad y pulsar **Calcular misión**. El modo rápido usa A*: si faltan recursos, **Preparar recursos para este recorrido** ajusta los saldos simulados y vuelve a verificar, conservando reservas. Se muestran ida,
   actividad, regreso, políticas coincidentes, recursos y motivo de selección.
5. Para posición intermedia/saldos, elegir **Misión en curso** y evaluar continuar
   o regresar. Para pruebas sintéticas o CTX original a 4 m, abrir **Laboratorio**.

Las imágenes remotas requieren internet; **Solo datos locales**, dentro de
Fuentes y leyenda, permite usar relieve/elevación CTX, motor y exportaciones sin
solicitar teselas. Sin sustitución silenciosa por datos sintéticos. Los perfiles
son simulados y no certifican seguridad EVA; masa/altura solo informativas.

Estado comprobado: **101 pruebas Python sin skips**, ambas suites JavaScript y
flujo real en navegador de escritorio/ancho reducido. Capturas, fuentes,
resoluciones, marcos, rendimiento y límites:
[ETAPA_06_CIERRE.md](../../docs/continuidad/ETAPA_06_CIERRE.md).
El cierre anterior se conserva como `ETAPA_06_CIERRE_PRE_MAPA.md`.

Desde la raíz del checkout:

```powershell
& .\.venv-stage04\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -v
& 'C:\Users\laura\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' prototypes/mission_planner/test_stage06_frontend.cjs
& 'C:\Users\laura\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' prototypes/mission_planner/test_stage06_map_frontend.cjs
```

Los tests HTTP necesitan permitir sockets locales. Las pruebas JavaScript con
doble DOM complementan las capturas y comprobaciones del navegador real.

Módulos importables en esta carpeta: `mars_route_planner` y
`mars_mission_resources`. Ejecutar desde aquí o usar unittest discovery con `-s`.
CORE con biblioteca estándar, Python 3.11.9 reproducido. La integración opcional
Jezero CTX de etapa 4 usa solo NumPy en un entorno aislado; no modifica el piloto.

Los seis archivos en `originals/` fueron aportados en `Documents/` de la carpeta
MARS GOD EYE. Se conservan byte a byte, incluidos nombres descargados. Los cuatro
Python iniciales coinciden con `.audit/baseline`; hashes en
`evidence/source-sha256.json`. Los documentos originales describen el estado
previo; el contrato actualizado está en `../../docs/continuidad/ETAPA_01_CIERRE.md`.
No contienen licencia explícita: autoría/licencia y permiso de distribución
pendientes de confirmar; no se les atribuye Apache-2.0 automáticamente.
La incorporación local fue solicitada por el usuario; no se publica.

Pruebas desde esta carpeta:

```powershell
$plannerPython = 'C:\Users\laura\AppData\Local\Programs\Python\Python311\python.exe'
& $plannerPython -m unittest discover -s . -v
& $plannerPython mars_route_planner.py
& $plannerPython mars_mission_resources.py
```

Terrain es un constructor mutable de entradas. Cada planificador captura una
copia validada e inmutable (`nav.t`). Cambiar entradas no modifica esa instancia;
crear otro planificador para obstáculos, alturas, desconocidos o resolución nuevos.
No existe método de actualización ni replanificación durante búsqueda.

Las celdas ocupadas y desconocidas son cuadrados completos. La huella circular
usa radio + margen. El chequeo de segmentos usa cuadrados expandidos en ambos
ejes: una sobreaproximación conservadora de la suma circular, que puede rechazar
pasos posibles cerca de esquinas. Intersección o tangencia con ese envolvente se
rechaza. La frontera exterior permite tangencia sin salir; su convexidad asegura
contención entre extremos con clearance suficiente. Las diagonales requieren
además ambas celdas laterales transitables. Esto no certifica seguridad física.

max_labels es entero positivo (bool no admitido), incluye etiqueta inicial e
inactivas; permite almacenar/procesar exactamente N etiquetas. Antes de insertar
la N+1 no dominada y admisible lanza SearchLimitReachedError(limit,
generated_labels). Llegar a N no interrumpe por sí solo: todavía puede devolver
éxito o agotar frontera. El límite no mide expansiones ni tiempo. La interrupción
no determina factibilidad. NoFeasibleMissionError conserva el rechazo por
extremos no transitables y agotamiento de frontera.

## Entrada validada de etapa 2

Usar `ResourceMissionPlanner.from_profile(terrain, profile)` con `AgentProfile`.
Es una unión discriminada cerrada: `agent_type` solo admite `astronaut` o `rover`.
Son obligatorios identificador, versión, naturaleza de parámetros, procedencia,
limitaciones, `Mobility`, `MotionModel` y mapa de recursos. Los contratos son
inmutables y el mapa de recursos se copia al construir.

| Clave | Unidad de capacidad/reserva | Astronauta | Rover |
|---|---|---|---|
| time | minutos | obligatorio | obligatorio |
| battery | Wh (traje en astronauta) | obligatorio | obligatorio |
| oxygen | unidades simuladas | presupuesto o exclusión | no aplica |
| water | litros | presupuesto o exclusión | no aplica |
| nutrition | kcal de demanda energética | presupuesto o exclusión | no aplica |

`ResourceAllocation(capacity, reserve, movement_rate, activity_rate)` exige
valores finitos no negativos y reserva <= capacidad; igualdad es válida.
Las tasas usan la unidad del recurso por minuto; ambas tasas de tiempo deben
ser 1. Velocidad en m/min estrictamente positiva; radio/margen en metros y
pendiente en grados. Distancia horizontal en metros es métrica sin presupuesto.

Para astronautas, una omisión humana requiere `ExcludedResource(reason)` con
motivo no vacío, sin tasas, capacidad ni reserva. No equivale a consumo cero:
`resource_status` devuelve `modeled`, `excluded` o `not_applicable`. Un recurso
modelado puede tener tasas cero. El rover rechaza toda clave humana, incluso
presupuesto/tasa/reserva cero o exclusión. Tiempo y batería no se excluyen.
`None`, claves desconocidas y recursos obligatorios ausentes se rechazan.

Movimiento conserva las fórmulas: g=max(0,ascenso)/distancia;
t=d/v*(1+penalización_ascenso*g+penalización_rugosidad*r).
O2/agua/kcal se multiplican por t y (1+penalización_esfuerzo*g).
Batería=t*tasa_movimiento+ascenso_positivo*coeficiente_Wh_por_m.
Actividad=t_actividad*tasa_actividad, una sola vez al llegar al objetivo.
Duración cero no agrega consumo. Todas las fases comparten capacidades/reservas.
Tolerancia absoluta de presupuestos y dominancia conservada: 1e-9.

`small_example_profile('astronaut')` y `small_example_profile('rover')` ofrecen
conjuntos simulados versión 2.0. `small_demo(tipo)` recorre 2 m de ida y 2 m de
regreso a 1 m/min, más 2 minutos de ciencia. Resultado: 6 min y 18 Wh;
astronauta además 10 unidades O2 simuladas, 1.2 L y 28 kcal. No son parámetros
calibrados ni validación EVA. No se convierte O2 a volumen, masa o presión;
kcal no impone ingerir alimento durante una misión breve.

Ejemplo mínimo (desde esta carpeta):

```python
from mars_mission_resources import small_demo
astronaut = small_demo('astronaut')
rover = small_demo('rover')
```

Para configurar: construir un perfil con los campos anteriores o usar
`dataclasses.replace` sobre el ejemplo (se vuelve a validar); después llamar
`from_profile(...).plan(start, goal, activity_min=...)`.

Compatibilidad: el constructor anterior `(terrain, PlannerConfig, Consumption,
Budget)` sigue disponible como API heredada sin separación garantizada de agentes.
Mantiene tasas de actividad iguales a movimiento. No debe usarse para nuevas
entradas basadas en perfiles. `Mobility.agent_radius_m` se traduce internamente
al nombre histórico `PlannerConfig.rover_radius_m`; solo hay un cálculo y una
búsqueda. `Usage` sigue siendo el acumulador genérico: sus ceros internos para
recursos omitidos no expresan aplicabilidad; consultar el perfil para ello.
La salida CLI genérica conserva esos ceros; los recursos humanos del rover
no aplican. Los perfiles/metadatos quedan accesibles en `planner.profile`.

Las dos demos grandes usan perfiles explícitos y conservan sus parámetros y
límite; la CLI también ejecuta los dos ejemplos pequeños. Cierre y evidencias:
`../../docs/continuidad/ETAPA_02_CIERRE.md`, `evidence/stage02-*.log`.

## Misión explícita de etapa 3

Entrada pública: `mission_api.plan_mission(MissionRequest(...))`. Solicitud y
resultado usan `schema_version="3.0"`. Una única búsqueda con `from_profile`
produce SUCCESS, INFEASIBLE, SEARCH_LIMIT_REACHED o INVALID_INPUT. El límite
conserva factibilidad desconocida. Errores internos inesperados se propagan.

`MissionRequest` exige todos sus campos y difiere la validación semántica a la
fachada. Argumentos Python ausentes (`TypeError`) y errores al construir
`TerrainReference`, `LocalFrame` o `AgentProfile` quedan fuera de esa frontera:
el llamador los maneja como errores de construcción. No hay deserializador JSON.

```python
from demo_stage03 import example_request
from mission_api import plan_mission
result = plan_mission(example_request("astronaut"))
print(result.status.value)
data = result.to_dict()
text = result.to_json()  # allow_nan=False; solo tipos JSON
```

`TerrainReference.capture(terrain, terrain_id)` conserva el snapshot inmutable y
calcula su revisión SHA-256 reproducible. `LocalFrame(frame_id, resolution_m,
origin_xy_m)` define origen en la esquina exterior anterior a (fila=0,columna=0),
X positivo hacia columnas crecientes, Y positivo hacia filas crecientes.
Centros XY = origen + ((columna+.5)*resolución, (fila+.5)*resolución), en metros.
Origen (0,0) reproduce exactamente la convención anterior; no se invierte Y.
No se asignan direcciones geográficas ni proyección planetaria.

SUCCESS incluye ruta, índice/celda objetivo, waypoints XY, eventos ordenados,
ciencia estacionaria una vez (también como evento de duración cero), fases
outbound/activity/inbound y totales. Los eventos incluyen incrementos, acumulados
y recursos restantes = capacidad - consumo; reserva y margen se dan aparte.
Recursos excluded/not_applicable conservan su estado y cantidades `null`, incluso
en fases y eventos. La capacidad/reserva vive exclusivamente en el perfil de la
solicitud. El resultado copia la configuración del perfil para trazabilidad.
Tolerancia absoluta de consistencia y presupuestos: 1e-9 en unidades respectivas.
Distancia es horizontal en m; tiempo min; batería Wh; O2 simulated_u; agua L;
nutrición kcal. El costo es el objetivo ponderado preexistente, no una unidad
física ni una certificación de seguridad u optimalidad operacional global.

```powershell
& $plannerPython demo_stage03.py
& $plannerPython demo_stage03.py --json
```

Cinco casos pequeños simulados: astronauta/rover exitosos, presupuesto
insuficiente, límite de etiquetas y entrada inválida. Evidencias actuales en
`evidence/stage03-*`; contrato completo, códigos, ejemplos JSON y aceptación en
[`ETAPA_03_CIERRE.md`](../../docs/continuidad/ETAPA_03_CIERRE.md).

## Integración acotada Jezero CTX — etapa 4

`jezero_adapter.load_ctx_crop(folder, CropWindow(...))` valida SHA-256, metadatos,
forma/dtype de las tres capas y alineación declarada. Solo decodifica `prior`
(CTX). No llama a `pilots/jezero/mission.load_data`, no importa el piloto, no lee
alturas HiRISE ni utiliza `valid` (máscara conjunta) o `origin_z_m` (derivado de
HiRISE). La validez se deriva únicamente del prior CTX. No existe un mapa estimado
público persistido en este checkout que haga falta para esta demostración.

Devuelve `AdaptedTerrain`: `TerrainReference` inmutable, `LocalFrame`, `GridMapping`
y procedencia JSON separada, con producto, hash NPZ/metadatos, snapshot, ventana,
transformaciones, política de capas y hash de la adaptación. La procedencia se
transporta junto al resultado en cada registro de ejecución. El hash histórico
de ventana nativa se conserva como declaración del importador; esa ventana no
está disponible para verificarlo nuevamente. El hash del NPZ sí se verifica.

Se admite el contrato existente: CTX nativo de 20 m, parent cuadrado norte→sur
con cálculo a 4 m y CRS equirectangular marciano documentado. Se rechazan otros
contratos; no es un lector geoespacial general. No se remuestrea, interpola ni
rellena. NaN/Inf/sentinel nodata se convierten en `None`, bloqueado por el CORE.
Alturas CTX absolutas en metros, sin sustraer `origin_z_m`. Riesgo y rugosidad no
disponibles: cero desactiva penalizaciones adicionales. Obstáculos adicionales
no observados: `False` es una hipótesis del escenario, sin afirmar ausencia física.
La pendiente se calcula mediante el CORE sobre el recorte; usa derivadas de un
lado en los bordes. No hay halo ni información exterior oculta en la búsqueda.

Marcos explícitos:

- Producto y recorte: celda `(fila,columna)`; filas hacia sur, columnas hacia este.
- Planner: `JEZERO_CTX_CROP_EAST_SOUTH`, X este, Y sur, origen esquina NW del recorte.
- Jezero: `JEZERO_LOCAL_EQUIRECTANGULAR_EAST_NORTH`, E este, N norte; esfera Marte
  radio 3 396 190 m, centro 18.45° N planetocéntrico / 77.45° E. Sin WGS84 terrestre.
- Para ventana `[60:67,60:67]`, afín GDAL `[-16,4,0,16,0,-4]`;
  `E=-16+X`, `N=16-Y`. Vértices de píxel en índices enteros; centros en +0.5.
- Contención de puntos semiabierta en índices: `[0,filas) × [0,columnas)`;
  borde norte/oeste incluido, sur/este excluido. El transporte de esquinas permite
  todos los vértices exteriores, pero esos vértices no se convierten en celdas
  fuera del raster. No hay clipping silencioso ni conversión lat/lon nueva.

`GridMapping` ofrece conversiones de celda de recorte↔producto, celda↔Jezero,
celda↔XY interno, XY interno↔Jezero, y esquinas. El CSV distingue ambos marcos.
Una muestra: base recorte (4,2) = producto (64,62) = planner (10,18) m = Jezero
(-6,-2) m; altura CTX -2571.708984375 m. Referencia vertical declarada por fuente:
MOLA topography / DeltaGeoid, sin conversión de datum terrestre.

Desde la raíz del checkout, con el Python indicado:

```powershell
$plannerPython = 'C:\Users\laura\AppData\Local\Programs\Python\Python311\python.exe'
& $plannerPython -m venv .venv-stage04
& .\.venv-stage04\Scripts\python.exe -m pip install -r prototypes/mission_planner/requirements-jezero.txt
& .\.venv-stage04\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -v
& .\.venv-stage04\Scripts\python.exe prototypes/mission_planner/demo_stage04.py --output prototypes/mission_planner/evidence/stage04
& .\.venv-stage04\Scripts\python.exe prototypes/mission_planner/demo_stage04.py --json
```

No se instala nada en Python global. NumPy 2.2.6 es opcional y se importa dentro
del cargador. El CORE y las unidades de transformación importan sin él. La suite
global puede indicar skip explícito de NPZ/integración si falta NumPy o el producto;
eso no basta para declarar completada la etapa. Para separar pruebas:

```powershell
& .\.venv-stage04\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -p test_jezero_adapter.py -v
& .\.venv-stage04\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -p test_stage04_integration.py -v
& $plannerPython -m unittest discover -s prototypes/mission_planner -v
```

`demo_stage04.py` fija antes de ejecutar un único recorte de 7×7 (28×28 m), base
(4,2), objetivo (2,4), actividad 2 min y límite 5000. No son sitios detectados.
Cinco escenarios: rover/astronauta SUCCESS, batería insuficiente INFEASIBLE,
límite 1 SEARCH_LIMIT_REACHED y coordenada inválida INVALID_INPUT. Mantiene datos
idénticos, perfiles simulados explícitos versión 4.0 y contabilidad de etapa 3.
No se ajustaron las tasas/capacidades tras ejecutar; los dos éxitos iniciales
usaron 107 etiquetas cada uno. No hay calibración ni validación física/EVA.

Evidencia: `evidence/stage04/` contiene solicitud, perfil completo y hash,
procedencia, MissionResult íntegro, transformaciones, eventos/fases/recursos,
waypoints Jezero separados, CSV de éxitos y resumen. Los cinco JSON son estrictos.
Errores del adaptador (integridad/contrato) lanzan `ValueError` antes de construir
una solicitud; no se convierten en inviabilidad ni se ocultan. La fachada conserva
la frontera de INVALID_INPUT descrita en etapa 3.

Cierre, inventario, aceptación y resultados ejecutados:
[`ETAPA_04_CIERRE.md`](../../docs/continuidad/ETAPA_04_CIERRE.md).

## Decisiones y replanificación — etapa 5

API nueva `mission_decisions`, **schema_version 5.0**. La fachada 3.0 conserva
inicio=base, ida/ciencia/regreso y su significado anterior. No existe un lector
JSON ni transporte remoto. Los contratos anidados validan al construirse; la
fachada nueva devuelve INVALID_INPUT para errores semánticos de solicitud.

`DecisionRequest` contiene terreno capturado, marco, perfil original, `MissionState`,
procedencia por recurso, escenario nominal/conservador, límite y características
personales opcionales. [Clasificación y fuentes](PERSONALIZACION_ETAPA05.md).
Masa/altura son metadatos sin efecto; edad/sexo no se recopilan al no existir
un cálculo que los necesite. Las tasas individuales siguen siendo configurables.

`MissionState.capture` recibe ID, base original, posición actual, objetivo,
actividad pendiente, saldos restantes y opcionalmente consumo histórico.
Posiciones = centros de celda enteros. Conserva ID/versión/hash de perfil,
ID/hash de terreno y reservas absolutas originales. El historial es informativo:
**no se descuenta del saldo**. Saldos inferiores a reservas son inviables,
no motivo para rebajarlas. Actividad `completed` exige minutos pendientes cero.

```python
from demo_stage05 import make_request  # fixture ficticio, no datos del usuario
from mission_decisions import plan_future, compare_alternatives, evaluate_options
q = make_request()  # base (0,0), actual (0,1), objetivo (0,2)
continuation = plan_future(q, "continue")
returning = plan_future(q, "return")
comparison = compare_alternatives(q)
decision = evaluate_options(q)
print(decision.to_json())
```

Continuar: actual→objetivo→actividad pendiente→base. Si ya está completada,
seguir visitando el objetivo no repite ciencia. Regresar: actual→base sin ciencia,
incluso si el objetivo es intransitable; desde la base devuelve ruta de una celda,
eventos vacíos y costo/consumo cero. Si actual=objetivo, la ciencia pendiente se
contabiliza al inicio. Los tres resúmenes de fase permanecen presentes, con cero
en las fases omitidas; regreso usa `goal_cell/goal_index=null`.

Políticas acotadas: balanced conserva pesos, minimum_time pone pesos externos de
penalización/batería a cero, terrain_caution eleva peso de penalización a
max(4,2×original). Comparten movilidad, saldos, tasas y reservas. Se exportan
pesos, estados y planes completos. La recomendación elige menor tiempo total
entre SUCCESS calculados, luego menor batería y orden fijo de política.
No compara costos de funciones distintas ni afirma optimalidad global o mayor
seguridad. Rutas iguales se agrupan explícitamente sin fabricar diversidad.

La decisión continuar/regresar requiere un regreso SUCCESS para recomendar
continuar. Continuación inviable y regreso SUCCESS recomienda RETURN; continuación
interrumpida exige revisión con factibilidad desconocida. Regreso no confirmado
exige revisión y nunca garantiza evacuación. Cada búsqueda conserva su estado.

Actualizar terreno exige otro `TerrainReference` y actualizar explícitamente
la revisión del estado; conservar la solicitud anterior. No hay mutación de una
búsqueda en ejecución. Bloqueo/desconocimiento de posición tiene código explícito,
sin mover el agente. `demo_stage05.updated_request` demuestra perturbaciones
simuladas en la misma retícula; no son observaciones científicas CTX.

```powershell
& .\.venv-stage04\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -v
& .\.venv-stage04\Scripts\python.exe prototypes/mission_planner/demo_stage05.py --output prototypes/mission_planner/evidence/stage05
```

Evaluación finita: 17 casos, 39 solicitudes de plan; retículas 1×3 y 7×7,
CTX 7×7 del recorte previo, límites 5000 y fixtures de interrupción 1. Registra
tiempo de la llamada completa compare/evaluate y pico de asignaciones Python
con tracemalloc (no memoria total del proceso), estados, perfiles, pesos,
etiquetas disponibles, snapshots y procedencia. No intenta resolver todo Jezero.
NumPy sigue solo en el adaptador; CORE funciona con biblioteca estándar.
Ver [cierre de etapa 5](../../docs/continuidad/ETAPA_05_CIERRE.md) y evidencia
`evidence/stage05/evaluation.json`. No se implementaron interfaz ni ROS.
