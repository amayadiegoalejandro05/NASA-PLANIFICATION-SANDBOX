# ETAPA 04 — Mission Planner sobre el prior CTX de Jezero

**Estado: COMPLETADA.** Fecha: 2026-11-05, America/Bogota.

## Alcance y estado heredado

Se conectó la fachada `MissionRequest` / `plan_mission` con un recorte del prior
orbital real MRO/CTX mediante un adaptador independiente. Se ejecutaron misiones
de rover y astronauta con ida, ciencia y regreso, más inviabilidad, interrupción
y entrada inválida. Se preservan motor, fórmulas, snapshot, perfiles explícitos,
contabilidad y reservas de etapa 3. No se implementó otra etapa.

- Checkout: `C:\Users\laura\OneDrive\Escritorio\MARS GOD EYE\NASA-Sandbox-etapa01`.
- Rama comprobada: `etapa01-base-confiable`.
- HEAD/base comprobado: `0d5a444f5444b4dfa574224c9f7d09652dad1df5`.
- Repositorio: https://github.com/dryanguasr/NASA-Sandbox.
- Estado inicial: `?? docs/continuidad/`, `?? prototypes/`; se preservó todo el
  trabajo local heredado, incluso sin commit o sin seguimiento.
- Python indicado disponible: **3.11.9**; Git indicado: **2.56.0.windows.4**.
- Referencia antes de implementar: **39/39 OK**, registrada en
  `prototypes/mission_planner/evidence/stage04-baseline-tests.log`.
- `stage04-baseline.json` registra estado inicial, dependencias y SHA-256 de
  **50 archivos preexistentes** del prototipo, cierres, piloto y datos. El único
  archivo de ese conjunto editado es el README del prototipo. Los módulos del
  motor, todas sus pruebas, originales, evidencias anteriores, cierres 01/02/03,
  piloto Jezero y datos siguen byte a byte intactos: `stage04-verification.json`.

Se leyeron AGENTS.md raíz (único encontrado), README raíz, escenario, procedencia,
cierres 01/02/03, README/módulos/pruebas del prototipo, README/instrucciones del
piloto, importador, partes pertinentes de `mission.py`, reporte existente y
metadatos/datos. Las instrucciones históricas sobre otros módulos se trataron
como antecedentes. No se ejecutaron Gazebo, ROS, firmware, visor ni la simulación
completa Jezero; tampoco se modificaron sus archivos ni resultados.

## Inventario, integridad y decisión de entrada

Archivos disponibles en `data/jezero/`: `terrain.npz` (**79 786 bytes**) y
`metadata.json`. No hay GeoTIFF locales ni `belief_final.npz` / `belief_frames.npz`
persistidos en la evidencia de este checkout. Los resúmenes/figuras del piloto
no son un mapa estimado público con retícula exportada. El prior existente basta;
no se fabricó una entrada ejecutando la simulación.

| Miembro NPZ | Forma / tipo | Papel / acceso de esta etapa |
|---|---|---|
| `prior` | 128×128, float32 | Prior público CTX; única matriz decodificada |
| `reference` | 128×128, float32 | DEM HiRISE del simulador; solo cabecera de forma/tipo, sin decodificar alturas |
| `valid` | 128×128, bool | Máscara **conjunta** finito(CTX) AND finito(HiRISE); solo cabecera, no usada para transitabilidad |

El SHA-256 calculado del NPZ coincide con los metadatos existentes:

```text
18d20b39a680d93addc3c3151bb3f19a5f41fc8f9a170396d4094694bbd76d6b
```

Se valida ese hash antes de abrir las matrices y se conserva además el hash de
los bytes de `metadata.json` en cada ejecución. Esto verifica integridad respecto
a los metadatos locales, no autenticidad mediante una firma externa. Los hashes
históricos `source_window_sha256` corresponden a ventanas nativas leídas por el
importador: se conservan como procedencia declarada, pero **no se verifican de
nuevo**, porque los tiles nativos no están guardados. No se descargaron mosaicos,
se ejecutó `--refresh-data` ni se sustituyó relieve real por sintético.

CTX tiene **16 384 alturas conocidas y 0 desconocidas** en el parent; rango
[-2575.459716796875, -2564.3076171875] m. La validez usada es finito(CTX) y distinto
del sentinel nodata de fuente, sin consultar HiRISE ni `valid`. Los huecos se
ensayan únicamente en fixtures sintéticos etiquetados, separados del producto.

| Propiedad | CTX operacional experimental | HiRISE reservado, solo inventario/procedencia |
|---|---|---|
| Instrumento/misión | MRO/CTX | MRO/HiRISE |
| Producto DOI | `10.5066/P906QQT8` | `10.5066/P9REJ9JN` |
| DTM USGS | `JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif` | `JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif` |
| Postes nativos | 20 m | 1 m |
| Forma nativa declarada | 1512×1596 | 21488×21400 |
| Ventana nativa declarada (col,fila,ancho,alto) | (841,787,34,33) | (13186,12740,547,519) |
| Cálculo existente | 4 m; bilineal previo | 4 m, no usado para decidir rutas |

Las URL/citas completas del producto CTX se preservan en cada JSON; las dos
fuentes están documentadas en `data/jezero/metadata.json`. El remuestreo previo
CTX **no produce información real de 4 m**. Se trata de planificación experimental
con conocimiento local incompleto, sin terreno certificado.

## Adaptador y límites de validación

`prototypes/mission_planner/jezero_adapter.py` devuelve un `AdaptedTerrain` con:

- `TerrainReference` y snapshot inmutable compatibles con el CORE.
- `LocalFrame` y `GridMapping` explícitos, más ventana e índices parent.
- Procedencia separada, serializable y no mutable por referencia, que viaja junto
  a cada solicitud/resultado en el registro de evidencia.
- Identidad de producto, hash NPZ, hash de metadatos, hash de snapshot y hash de
  adaptación que incluye la procedencia/transformación/ventana y el snapshot.

La identidad del snapshot usa el contrato histórico `terrain-snapshot-v1`:

```text
639340f9c4b722cc9f445c9b10398bcea90f56988cc5f3fc59f0434bc2013e1f
```

La adaptación usa SHA-256 de JSON canónico, claves ordenadas, ASCII, separadores
compactos, UTF-8, sin NaN/Infinity, excluyendo únicamente `adaptation_sha256`.
Su formato queda escrito en el propio registro. El hash de contenido del snapshot
permanece separado del marco; la adaptación sí vincula ambos.

Se rechazan schema incompatible, fuente distinta de CTX, resolución/extent/afín
contradictorios, WKT local incompatible con esfera/centro/ejes/unidades declarados,
ventanas inválidas, hashes incorrectos, miembros/dtypes/formas NPZ inesperados y
fracción de validez CTX inconsistente. El adaptador es deliberadamente acotado al
contrato del importador existente, no un lector general de rasters planetarios.
Errores de datos lanzan `ValueError` antes de construir la solicitud, conforme a
la frontera de construcción de etapa 3. No se disfrazan como INFEASIBLE.

NumPy se importa solo dentro de `load_ctx_crop`; no se importa el piloto ni su
`load_data`, que cargaría la referencia. Las cabeceras de las tres capas verifican
dimensiones alineadas bajo el afín compartido; no contienen afines independientes
por matriz que puedan verificarse adicionalmente. La única lectura de payload
por clave NPZ es `prior`. La prueba intercepta esa operación y rechaza cualquier
otra clave. Otra prueba impide acceso a NPZ/archivos durante la búsqueda.

No hay A*, búsqueda multirrecurso, pendientes ni fórmulas de consumo duplicadas:
se usan `plan_mission`, `from_profile` y los cálculos existentes del CORE.

## Coordenadas, escala y alturas

El parent es de 512×512 m, 128×128 celdas de 4 m. Afín GDAL parent:
`[-256,4,0,256,0,-4]`. Filas norte→sur, columnas oeste→este. CRS métrico local
equirectangular sobre esfera de Marte de radio **3 396 190 m**, centro **18.45° N
planetocéntrico, 77.45° E**, longitud positiva al este. No se usa WGS84 terrestre
ni se implementa conversión nueva de latitud/longitud.

Ventana determinista: **filas [60,67), columnas [60,67)**, sin remuestreo:
7×7 celdas, 28×28 m. Afín del recorte `[-16,4,0,16,0,-4]`.

| Marco | Origen y ejes | Centro de celda local (r,c) |
|---|---|---|
| Producto parent | esquina NW (-256,256) m; E este / N norte | (-256+(C+.5)×4, 256-(R+.5)×4) |
| Planner `JEZERO_CTX_CROP_EAST_SOUTH` | esquina NW del recorte, (0,0); X este / Y sur | ((c+.5)×4, (r+.5)×4) |
| Jezero `JEZERO_LOCAL_EQUIRECTANGULAR_EAST_NORTH` | marco métrico del importador, E este / N norte | (-16+(c+.5)×4, 16-(r+.5)×4) |

`R=r+60`, `C=c+60`; transporte: **E=-16+X, N=16-Y**. Inversa:
**X=E+16, Y=16-N**. `LocalFrame` global no se modifica. `GridMapping` valida y
convierte celdas parent/recorte, centros, esquinas, XY interno/Jezero y sus inversas.
Sin clipping ni redondeo al vecino más cercano.

Esquinas de píxel en índices enteros; centros +0.5. El recorte cubre E∈[-16,12)
y N∈(-12,16] para contener puntos: norte/oeste incluidos, sur/este excluidos.
Los puntos en límites internos pertenecen a la fila/columna siguiente en orden
de índices. Los métodos de transporte/esquinas admiten el contorno cerrado para
representarlo; la conversión de punto a celda conserva el límite semiabierto.

| Punto demostrativo | Celda recorte | Celda parent | Planner XY m | Jezero EN m | Altura CTX m |
|---|---|---|---|---|---|
| Base/inicio | (4,2) | (64,62) | (10,18) | (-6,-2) | -2571.708984375 |
| Objetivo | (2,4) | (62,64) | (18,10) | (2,6) | -2572.149658203125 |

Referencia vertical declarada: **source product MOLA topography / DeltaGeoid;
no Earth datum conversion**. Se conserva exactamente el float32 de CTX al
convertirlo a float de Python. **Desplazamiento aplicado = 0 m**. No se sustrae
`origin_z_m=-2569.886962890625`, porque el importador lo calculó con la mediana
HiRISE para representación del simulador. El motor solo usa diferencias de las
alturas CTX del snapshot. No se interpola en el adaptador ni en los waypoints.

## Capas ausentes y geometría

Alturas desconocidas NaN/Inf/sentinel se convierten a `None`, bloqueadas por el
CORE como áreas de celda completas. No se rellena ni se inventa altura.
La máscara conjunta puede ser totalmente falsa en el fixture sin borrar alturas
CTX conocidas: demuestra que no hay dependencia operacional de HiRISE.

No hay capas de obstáculos observados, riesgo o rugosidad. Obstáculos `False`
significa **sin obstáculos adicionales especificados en el escenario**, no
ausencia física. Riesgo/rugosidad a cero desactivan penalizaciones adicionales;
sus pesos también se fijan a cero en los perfiles de demostración. No se les
atribuye medición científica. No se detectaron sitios, rocas ni minerales.

Pendiente: cálculo existente del CORE (gradiente local y pendiente de arista) a
partir del mismo snapshot CTX. En bordes del recorte se usa la diferencia de un
lado del CORE; no se agrega halo ni se usa referencia exterior. Huella circular,
margen, diagonales y envolventes conservadoras permanecen intactos. Ninguno de
estos chequeos certifica tránsito real, mecánica del suelo, soporte vital o EVA.

## Escenarios y resultados ejecutados

Configuración fija en `demo_stage04.py`, definida antes de la primera ejecución:
base (4,2), objetivo (2,4), ciencia estacionaria **2 min**, límite suficiente
**5000 etiquetas**. La selección es por índices fijos, no por información HiRISE
ni detección de un sitio científico. La primera ejecución tuvo éxito para ambos
agentes; no se ajustaron tasas/capacidades/objetivos ni se incrementó el límite.

Perfiles: `sim-jezero-ctx-rover` / `sim-jezero-ctx-astronaut`, versión **4.0**,
naturaleza **simulated**, procedencia/limitaciones y hash propios en cada JSON.
Velocidad 4 m/min; movimiento 2 Wh/min, actividad 4 Wh/min; ascenso 0.5 Wh/m;
coeficientes de ascenso heredados 2. Tiempo capacidad/reserva 60/5 min; batería
100/10 Wh. Rover radio/margen 0.6/0.2 m y pendiente máxima 18°; astronauta
0.35/0.15 m y 15°. Son hipótesis aritméticas, no capacidades calibradas.

Astronauta: O2 capacidad/reserva 20/2 unidades simuladas, tasas 0.25 movimiento /
0.3 actividad por min; agua 2/0.2 L, tasas 0.01/0.02 L/min; nutrición 200/20 kcal,
tasas 4/5 kcal/min. O2 sin conversión a masa/volumen/presión; kcal como demanda,
sin necesidad de ingerir esa cantidad durante esta misión. Rover: esos tres
recursos son `not_applicable`, cantidades exportadas `null`.

| Escenario | Estado / motivo | Resultado |
|---|---|---|
| rover_success | SUCCESS / MISSION_FOUND | 22.627416998 m; 7.877191164 min; 19.974719241 Wh; 107 etiquetas; costo 8.696289726 |
| astronaut_success | SUCCESS / MISSION_FOUND | Misma ruta/distancia/tiempo/batería; 107 etiquetas; costo 8.968804329 |
| insufficient_budget | INFEASIBLE / SEARCH_EXHAUSTED | Batería capacidad 6/reserva 1 Wh: 5 utilizables < 8 Wh de ciencia sola |
| label_limit | SEARCH_LIMIT_REACHED / LABEL_LIMIT_REACHED | Misión rover idéntica, límite 1; 1 etiqueta generada; factibilidad desconocida |
| invalid_request | INVALID_INPUT / REQUEST_VALIDATION_FAILED | Objetivo (7,4) fuera del recorte, datos intactos |

En los éxitos: ruta recorte **(4,2)→(3,3)→(2,4)→(3,3)→(4,2)**. Ida
11.313708499 m / 2.828427125 min; actividad 0 m / 2 min; regreso 11.313708499 m /
3.048764039 min. El regreso asciende en el CTX, de ahí la diferencia de tiempo.
El costo conserva el objetivo ponderado del motor y depende del umbral de
pendiente del perfil; no es una unidad física ni una certificación de seguridad.

| Recurso modelado | Consumido | Restante | Reserva |
|---|---:|---:|---:|
| Tiempo, ambos, min | 7.877191164 | 52.122808836 | 5 |
| Batería, ambos, Wh | 19.974719241 | 80.025280759 | 10 |
| O2 astronauta, simulated_u | 2.128673351 | 17.871326649 | 2 |
| Agua astronauta, L | 0.101146934 | 1.898853066 | 0.2 |
| Nutrición astronauta, kcal | 34.458773615 | 165.541226385 | 20 |

Cada JSON conserva precisión completa, solicitud, perfil, fuentes/hashes, ventana,
transformación, snapshot, `MissionResult` original, ruta, fases/eventos, consumos,
restantes, márgenes y límites. `jezero_waypoints` y CSV de éxitos están separados
de los waypoints XY internos y declaran ambos marcos/índices/altura CTX.

La prueba de batería conserva exactamente el relieve y el resto del perfil
rover; su ID lleva sufijo `-insufficient`. La causa aritmética está probada en
este escenario, pero el mensaje general del motor mantiene su alcance: agotó
la búsqueda y no identifica automáticamente una causa única. En agotamiento el
conteo es `null`, porque el motor no lo expone. En éxito/interrupción cuenta
etiquetas generadas/almacenadas, incluidas inicial/inactivas, **no expansiones**.
La interrupción queda guardada y no se reinterpreta como inviabilidad.

## Entorno, reproducción y pruebas

Python global inicialmente sin NumPy/Rasterio/PyProj/Matplotlib. Se creó
`.venv-stage04/` (ignorado en Git), con el Python indicado, y se instaló únicamente
**NumPy 2.2.6** para leer NPZ. El primer intento en sandbox falló por DNS; la
descarga con autorización de red tuvo éxito. El entorno contiene NumPy, pip y
setuptools; no se modificó Python global ni se instaló otra pila geoespacial.

Desde la raíz del checkout:

```powershell
$plannerPython = 'C:\Users\laura\AppData\Local\Programs\Python\Python311\python.exe'
$plannerGit = 'C:\Users\laura\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'
& $plannerPython --version
& $plannerGit --version
& $plannerPython -m venv .venv-stage04
& .\.venv-stage04\Scripts\python.exe -m pip install -r prototypes/mission_planner/requirements-jezero.txt
& .\.venv-stage04\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -v
& .\.venv-stage04\Scripts\python.exe prototypes/mission_planner/demo_stage04.py --output prototypes/mission_planner/evidence/stage04
& .\.venv-stage04\Scripts\python.exe prototypes/mission_planner/demo_stage04.py --json
& $plannerPython -m unittest discover -s prototypes/mission_planner -v
& $plannerPython prototypes/mission_planner/demo_stage03.py --json
```

Resultado final funcional: **53/53 OK, sin skips**, incluidas 39 regresiones,
9 pruebas unitarias de transformación/contrato/fixtures NPZ y 5 integraciones
con el producto **real existente**. Las pruebas unitarias y de integración están
en archivos separados, con comandos de descubrimiento individuales en el README.
La suite inicial ampliada también pasó 53/53; no hubo fallos ocultados ni
expectativas heredadas relajadas.

Sin NumPy, la suite global reporta **48 pruebas, OK (skipped=5)**: las cuatro
pruebas de fixtures NPZ y la clase de integración explican la ausencia de la
dependencia; las 39 regresiones y las cinco unidades de coordenadas/contratos
sí se ejecutan. Esa ejecución no se usa para declarar completas las integraciones:
se ejecutaron y aprobaron aparte en el entorno aislado dentro de la suite 53/53.
Un subproceso `-S` prohíbe importaciones NumPy/Rasterio/PyProj/Matplotlib/SciPy y
ejecuta una misión del CORE satisfactoriamente.

Se ejecutaron CLI legible y `--json` de etapa 4 (código 0); los cinco registros
se releen con JSON estricto y coinciden con `--json`. Las pruebas verifican
repetición determinista de los registros y coherencia de hashes/coordenadas.
Los cinco escenarios anteriores de etapa 3 siguen produciendo sus cinco estados
esperados con el Python global. `git diff --check` sin incidencias.

## Aceptación

| # | Requisito | Evidencia ejecutada |
|---|---|---|
| 1 | Producto existente/hash | `test_existing_product_integrity_shape_crop_and_absolute_heights` |
| 2 | Rechazo metadatos/dimensiones/integridad | `test_metadata_contract_rejections`, `test_integrity_and_all_layer_dimensions_rejected`, `test_validity_metadata_rejected_and_provenance_hash_detached` |
| 3 | Celdas/coordenadas/vuelta | `test_centers_orientation_and_inverse` |
| 4 | Centros/esquinas/orientación/límites | `test_corners_and_half_open_bounds` |
| 5 | Posición del recorte | `test_crop_position_and_rejections`, integración de alturas |
| 6 | Resolución/alturas sin offset | Integración de alturas; fixture con origin_z_m distinto ignorado |
| 7 | Nodata desconocido bloqueado | `test_nodata_is_none_and_blocked_no_filling_or_vertical_offset` |
| 8 | Solo CTX/sin acceso HiRISE | `test_only_ctx_payload_is_read_even_with_invalid_joint_mask`, `test_ctx_only_payload_and_no_raster_access_from_search` |
| 9 | Capas ausentes explícitas | Segunda prueba anterior, procedencia y perfiles |
| 10 | Rover real SUCCESS | `test_rover_and_astronaut_success_phases_resources_reserves`, `rover_success.json` |
| 11 | Astronauta real SUCCESS | Mismo test, `astronaut_success.json` |
| 12 | Presupuesto INFEASIBLE | `test_insufficient_budget_limit_and_invalid_distinct_same_terrain`, aritmética 5<8 Wh |
| 13 | Límite vs éxito misma misión | Mismo test, límite 1 y 5000 |
| 14 | Fases/consumos/restantes/reservas | Integración contable por evento y fase, tolerancia absoluta 1e-9 |
| 15 | JSON estricto/procedencia/transporte | `test_strict_json_provenance_waypoints_and_reproducible_exports` |
| 16 | 39 regresiones | Suite completa 53/53 y registro sin dependencias opcionales |
| 17 | CORE importable sin opcionales | `test_core_and_transform_import_without_optional_dependencies`, subproceso `-S` |

## Archivos y evidencia

Nuevos bajo `prototypes/mission_planner/`: `jezero_adapter.py`, `demo_stage04.py`,
`test_jezero_adapter.py`, `test_stage04_integration.py`, `requirements-jezero.txt`.
README actualizado; `.gitignore` agrega solo `.venv-stage04/`. Este cierre es
el único documento nuevo de continuidad de esta etapa.

Evidencia bajo `prototypes/mission_planner/evidence/`:

- `stage04-baseline.json` y `stage04-baseline-tests.log`: referencia previa.
- `stage04-tests.log`: 53 pruebas aprobadas, sin skips.
- `stage04-core-without-numpy.log`: regresión sin dependencia opcional.
- `stage04-demo.log`: salida legible de los cinco escenarios.
- `stage04-verification.json`: CLI JSON/etapa 3 y preservación por hashes.
- `stage04/rover_success.json`, `astronaut_success.json`,
  `insufficient_budget.json`, `label_limit.json`, `invalid_request.json`:
  registros completos individuales.
- `stage04/rover_success-waypoints.csv`, `astronaut_success-waypoints.csv`,
  `summary.txt`: coordenadas y resumen legible.

## Límites y cierre de operaciones

Terreno orbital real; prior de resolución limitada; objetivos, movilidad y
consumos simulados. No se afirma detalle topográfico de 4 m, obstáculos detectados,
seguridad física, certificación humana/EVA, calibración ni optimalidad operacional
global. No hay replanificación, nuevo visor, ROS 2, hardware ni simulación completa.
La licencia/autoría de los originales mantiene el pendiente heredado antes de
redistribuir; esta etapa es local y no publica material.

Todos los criterios obligatorios se ejecutaron satisfactoriamente, incluidas
integraciones reales. No hay bloqueos. **No se hicieron commits, push ni pull
requests**; tampoco clone/reset/clean ni cambio de rama. Estado final esperado:
`.gitignore` modificado, `docs/continuidad/` y `prototypes/` sin seguimiento.
La implementación se detiene en etapa 4.
