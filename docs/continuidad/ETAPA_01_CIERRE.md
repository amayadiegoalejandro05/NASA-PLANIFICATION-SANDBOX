# ETAPA 01 — Cierre de base confiable

**Estado: COMPLETADA.** Fecha: 2026-11-05, America/Bogota.

## Objetivo y alcance realizado

Base reproducible del prototipo, separación de interrupción e inviabilidad,
snapshot validado e inmutable, geometría conservadora de obstáculos y huella,
regresiones y evidencia. No se reescribió el motor, no se implementó etapa 2.

## Checkout y procedencia

- Checkout: `C:\Users\laura\OneDrive\Escritorio\MARS GOD EYE\NASA-Sandbox-etapa01`.
- Remoto origin: https://github.com/dryanguasr/NASA-Sandbox.git.
- Rama aislada: `etapa01-base-confiable`.
- Commit base: `0d5a444f5444b4dfa574224c9f7d09652dad1df5`.
- Inicialmente no había checkout ni Git en PATH. Se encontró Git en
  `C:\Users\laura\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe`.
  El clon inicial falló por DNS en sandbox; el clon con autorización elevada tuvo éxito.
  Se comprobó rama main limpia, HEAD y remotos antes de crear la rama aislada.
- Se leyó AGENTS.md raíz (único encontrado), README, escenario y procedencia.
  Las instrucciones de ejecutar Gazebo/control pertenecen al mundo/piloto, que
  no se ejecutó ni modificó; esta tarea autoriza exclusivamente núcleo Python.
- Prototipo: `prototypes/mission_planner/`, sin conexión con `pilots/jezero`.
- Originales: seis archivos de `../Documents/`, preservados en `originals/`.
  Los cuatro Python coinciden byte a byte con `../.audit/baseline/`.
  Hashes verificados y guardados en `evidence/source-sha256.json`.
  Auditoría original: `../AUDITORIA_MISSION_PLANNER_2026-11-05.md`.
- Autoría/licencia de originales sin declaración explícita: pendiente de
  confirmar antes de distribuir. No se atribuye automáticamente Apache-2.0.
  Incorporación local autorizada por el encargo, sin publicación.

## Archivos incorporados y propósito

Todos son nuevos respecto al commit base:

| Archivo bajo prototypes/mission_planner | Propósito |
|---|---|
| mars_route_planner.py | Snapshot y validación, clearance a áreas, aristas con huella |
| mars_mission_resources.py | Excepción independiente, límite exacto, comunicación CLI |
| test_mars_route_planner.py | 7 pruebas originales sin modificación |
| test_mars_mission_resources.py | 8 pruebas originales sin modificación |
| test_stage01.py | 6 regresiones con subcasos de los criterios obligatorios |
| README.md | Ejecución, contrato de terreno, límite y geometría, procedencia |
| originals/* | Seis fuentes aportadas, intactas |
| evidence/* | Logs baseline y corregidos, hashes de originales |

Este documento: `docs/continuidad/ETAPA_01_CIERRE.md`.
No hay modificaciones a archivos existentes del repositorio, datos, mundos,
planificador Jezero ni evidencias previas del repositorio.

## Decisiones del contrato

### Excepciones y límite

`SearchLimitReachedError(Exception)` es independiente de `NoFeasibleMissionError`
y `NoSafeRouteError`. Expone `limit` y `generated_labels`, y diagnóstico con ambos.
La CLI distingue interrupción con factibilidad no determinada de misión rechazada.
El agotamiento de frontera y extremos no transitables conservan inviabilidad.

`max_labels` exige tipo int positivo, excluye bool, flotantes, cero y negativos.
Cuenta etiquetas almacenadas/generadas, incluida la inicial y las inactivas.
Se permite procesar exactamente N etiquetas. Se interrumpe antes de insertar
la N+1 candidata admisible y no dominada; llegar exactamente a N puede todavía
dar éxito o inviabilidad por agotamiento. No limita expansiones ni tiempo.
El atributo histórico `explored_labels` sigue contando etiquetas generadas.

### Terreno

Se eligió exclusivamente snapshot: Terrain sigue siendo constructor mutable;
RiskAwareAStar copia todas las retículas a tuplas y revalida al construir.
TerrainSnapshot es frozen; `t` es propiedad sin setter. Pendientes, ocupación y
clearance se calculan de ese mismo snapshot. ResourceMissionPlanner lo usa tanto
para navegación como para consumos. Cambios externos a obstáculos, elevaciones,
None desconocidos, resolución, riesgo o rugosidad no afectan instancias creadas.
Para una solicitud actualizada hay que construir otro planificador. Una resolución
mutada a cero se rechaza en la nueva construcción. No se actualiza una búsqueda
en ejecución ni se implementan eventos.

### Geometría

Celda ocupada o desconocida = superficie cuadrada completa de lado resolución.
Clearance de centros = distancia euclídea al cuadrado, también limitada por mapa.
Huella circular de radio efectivo radio + margen. Cada segmento se contrasta
con cuadrados expandidos en ambos ejes por ese radio; estos contienen la suma de
Minkowski circular. Es una aproximación conservadora que puede rechazar pasos
válidos cerca de esquinas. Se rechaza contacto/tangencia con el envolvente de
obstáculos, incluso con radio cero. Los extremos deben ser transitables.
Ambas celdas laterales deben ser transitables en diagonales: no cortar esquinas.
La frontera rectangular permite tangencia sin salida; la convexidad del mapa
asegura contención del segmento y huella si ambos extremos tienen clearance.
Solo retícula 2D y círculo. No certifica seguridad física, movilidad o EVA.

## Entorno y reproducción

Windows / PowerShell, Python **3.11.9**, biblioteca estándar sin instalaciones.
Desde la carpeta MARS GOD EYE:

```powershell
$plannerPython = 'C:\Users\laura\AppData\Local\Programs\Python\Python311\python.exe'
& $plannerPython --version
Push-Location .audit\baseline
& $plannerPython -m unittest test_mars_route_planner.py test_mars_mission_resources.py -v
& $plannerPython mars_route_planner.py
& $plannerPython mars_mission_resources.py
Pop-Location
& $plannerPython -m unittest discover -s NASA-Sandbox-etapa01\prototypes\mission_planner -v
& $plannerPython NASA-Sandbox-etapa01\prototypes\mission_planner\mars_route_planner.py
& $plannerPython NASA-Sandbox-etapa01\prototypes\mission_planner\mars_mission_resources.py
```

Para reproducir sin la carpeta externa .audit: copiar los cuatro Python de
originals a una carpeta temporal con los nombres canónicos indicados en
`evidence/source-sha256.json`, y ejecutar los comandos baseline allí.
No descubrir tests recursivamente desde la raíz del repo: usar el `-s` anterior
para aislar el prototipo y sus imports. También se puede ejecutar desde su carpeta.

## Resultados reales

- Baseline reejecutado antes de editar: **15/15**, 0,103 s; nueva captura baseline
  en `evidence/baseline-tests.log`. Ambas demostraciones reejecutadas y coincidentes
  con los logs auditados conservados `demo-route.log` y `demo-resources.log`.
- Suite corregida final: **21/21**, 0,291 s (`evidence/stage01-tests.log`).
  Las 15 expectativas heredadas permanecen intactas. Hubo fallos iniciales de
  fixtures nuevas (reserva obligatoria omitida, borde y derivada central de pico);
  se corrigieron los fixtures sin quitar comprobaciones del comportamiento.
- Demo A*: **28 celdas, 6,39 m, costo 7,56, pendiente 1,0°**.
- Demo recursos astronauta: **interrupción controlada en 120.000 etiquetas**,
  factibilidad no determinada, sin resultado de misión ni cifras fabricadas.
- Demo recursos rover: **12,8 m, 91,0 min, 81,9 Wh, 1.145 etiquetas**,
  ida/regreso 28 celdas cada uno; O2, agua y kcal cero.
- Ambas entradas de demo finalizan con código 0; CLI de recursos continúa al
  rover tras comunicar interrupción del astronauta.
- Logs actuales: `evidence/stage01-route.log` y `stage01-resources.log`.

Cambio frente a baseline: A* tenía 26 celdas/6,16 m/costo 7,25; rover tenía
12,6 m/89,4 min/80,5 Wh/2.399 etiquetas; astronauta terminaba en 62.681 etiquetas.
El clearance por áreas y los segmentos conservadores cambian aristas admisibles,
costos y dominancia; ya no se conserva la ruta ni el conteo anterior. El aumento
de etiquetas del astronauta alcanza el límite existente, ahora clasificado
correctamente. No se elevó el límite ni se optimizó fuera del alcance.

## Criterios de aceptación y evidencia

| Criterio | Evidencia ejecutada | Estado |
|---|---|---|
| 1. Misma misión, éxito/límite | test_limit_exact_and_classification: 3 éxito; 1 y 2 interrumpen | Cumple |
| 2. Tipos independientes | mismo test: no instancia de inviabilidad ni ausencia de ruta; test_cli_interrupted | Cumple |
| 3. Imposible conserva inviabilidad | test_exhaustion_is_infeasible_even_at_limit y tests heredados de reservas | Cumple |
| 4. Validación y frontera exacta | límite 1/2/3, inválidos y frontera agotada con N=1 | Cumple |
| 5. Snapshot coherente | test_snapshot_and_updated_requests: reutilización idéntica e inmutabilidad | Cumple |
| 6. Nuevas solicitudes reflejan cambios | mismo test: obstáculo, elevación, None y resolución; revalidación cero | Cumple |
| 7. Huella y mapa | test_area_footprint_and_boundary: área adyacente, bordes y segmento | Cumple |
| 8. Diagonales/esquinas | test_swept_diagonal_and_corners: extremos libres/interior bloqueado y un lateral ocupado | Cumple |
| 9. Originales | 15 originales pasan sin ajustes | Cumple |
| 10. Demos controladas y actuales | tres salidas anteriores en dos módulos, con interrupción explícita | Cumple |

## Compatibilidad, limitaciones y pendientes

Imports canónicos y parámetros conservados; se añade un tipo de excepción que
los consumidores deben capturar explícitamente. Las mutaciones de entrada dejan
de afectar parcialmente instancias existentes: ahora requieren reconstrucción.
La geometría es más restrictiva y puede aumentar costos o interrumpir búsquedas.
No hay dependencias externas, ROS 2, HTTP, UI, integración DEM ni control rover.
El límite no demuestra imposibilidad; el modelo de consumos sigue sintético.
La tolerancia de dominancia preexistente sigue en 1e-9. No se afirma optimalidad
continua, seguridad física ni validación científica.

Pendientes fuera de alcance: aclarar autoría/licencia antes de distribuir;
contratos/perfiles y coordenadas para etapa posterior; calibración física y
consumos reales; escalabilidad y referencia matemática en grafos pequeños.
No se ejecutó Jezero ni Gazebo: no forman parte de la evidencia de esta etapa.

## Inicio concreto de etapa 2

Leer este cierre y README del prototipo; comprobar rama/HEAD y conservar estos
cambios sin commit. Ejecutar el comando discovery anterior. Leer el plan maestro
y auditoría originales conservados antes de definir el alcance autorizado para
etapa 2. Mantener Jezero separado, el snapshot y las tres clases de resultado.
No asumir que la demo astronauta completó una misión: quedó interrumpida.
Resolver la licencia antes de cualquier distribución. Este trabajo no inicia
ni implementa la etapa siguiente.

## Operaciones finales

No se hicieron commits, push ni pull requests. No hay bloqueos obligatorios.
El cierre se guarda con los cambios locales en la rama aislada indicada.
