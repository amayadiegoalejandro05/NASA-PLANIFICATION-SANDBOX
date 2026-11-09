# ETAPA 6.5 — cierre de auditoría numérica

**Estado: COMPLETADA.** Fecha: 2026-11-08, America/Bogota.
Se completa la corrección interna del cálculo en el alcance finito descrito;
no se declara calibración, validación física, seguridad EVA ni cierre visual de
la ampliación histórica de etapa 6. No se inicia 6.6 ni ROS.

## Checkout y preservación

- Exclusivo: `C:\Users\laura\OneDrive\Escritorio\NASA-PLANIFICATION-SANDBOX`.
- Rama conservada: `docs/space-apps-presentation`.
- HEAD inicial y final: `ab257374700665c47d049ae3d24fd0ba884eca62`.
- Origin verificado: `https://github.com/amayadiegoalejandro05/NASA-PLANIFICATION-SANDBOX.git`.
- Sin consulta remota de estado de PR1 ni afirmación de que esté fusionado.
- Cambios heredados: `M README.md` (enlace a presentación), `?? docs/presentacion/`.
  Conservados sin editar, stagear ni publicar; no forman parte de la auditoría.
- No se cambió de rama, clonó, reconstruyó HEAD, hizo clean/reset, commit, push,
  PR o merge. No se modificó ningún proyecto bajo `MARS GOD EYE`.
- Cierres y evidencias anteriores, datasets, manifiestos y documentación de
  presentación se preservan. Toda evidencia nueva está en stage065.

Se leyeron AGENTS, README, AI_HANDOFF, DECISIONS, RESOURCE_MODELS,
REPRODUCIBILITY, DEVELOPMENT_ROADMAP, MIGRATION_REPORT, cierre consolidado06,
presentacion/README y ALGORITMOS, README histórico del prototipo y módulos/tests.
Los documentos de tareas futuras se trataron como antecedentes.

## Alcance realizado

[NUMERICAL_MODEL_AUDIT.md](../NUMERICAL_MODEL_AUDIT.md) contiene el inventario
vinculado al código, fórmulas, unidades, dominio, tolerancias, cuentas manuales,
defectos reproducidos, compatibilidad y limitaciones. Es la referencia detallada.

Se comprobaron A* geométrico, costos de la búsqueda multirrecurso, primitivas
de movimiento/actividad, perfiles tipados, saldos, reservas, histórico, escenarios,
eventos/fases/totales, modo rápido, preparación y JSON estricto. No se duplican
fórmulas en JS ni se cambian heurísticas, dominancia o modelos de consumo.

## Hallazgos inspeccionados y defectos ejecutados

| Hallazgo | Evidencia / acción |
|---|---|
| Unidades, descenso, rugosidad y demanda energética | Cuentas manuales independientes; sin cambio de ecuaciones |
| Reserva absoluta e histórico | Presupuesto exacto, cada recurso insuficiente, saldo bajo reserva, capacidad= reserva, cero; sin doble descuento |
| NaN oculto, negativos y bool en primitivas antiguas | Reproducidos en `reproduced-before.json`; validación uniforme de números finitos y dominio |
| Consumos/sumas no finitos, incluso recurso sin restricción | Usage ahora impide propagarlos; guardas específicas en resultados |
| Costo A* desbordado clasificado como ausencia de ruta | Reproducido con peso1e308 y d2; NumericDomainError evita falsear inviabilidad |
| Factores de escenario y costos derivados desbordados | Frontera explícita INVALID_INPUT/NUMERIC_DOMAIN_EXCEEDED en contratos3.0/5.0 |
| Suma rápida en orden distinto a eventos | Caso grande finito reproducido en numerical-second.log; suma cronológica sin variar tolerancia |
| Duración positiva subdesbordada a cero | `underflow-before.json`; rechazo explícito de ese dominio |
| Preparación de recursos | Candidato completo, pendientes, actividad, vuelta, reservas y recálculo; precisión completa |
| Limitación del candidato rápido frente a inviabilidad global | Documentada y conservada para6.6, sin cambiar su semántica |

Los errores internos inesperados siguen propagándose: test inyecta RuntimeError
y comprueba que no se presenta como entrada inválida. Interrupciones siguen
separadas de inviabilidad. No se elevan max_labels ni max_expansions.

## Archivos de esta intervención

| Archivo/grupo | Cambio |
|---|---|
| `prototypes/mission_planner/numeric_domain.py` | Guardas numéricas de biblioteca estándar y error específico |
| `mars_route_planner.py` en la misma carpeta | Validación de valores y derivaciones geométricas/costos finitos; algoritmo intacto |
| `mars_mission_resources.py` | Dominio de Consumption/Budget/Usage/allocations y costos; duración subdesbordada |
| `mission_api.py`, `mission_decisions.py` | Márgenes finitos, control de desglose, factores y frontera numérica específica |
| `fast_mission.py` | Suma cronológica, guardas de costo/presupuesto y error de entrada del puente |
| `test_stage065_numerical.py` | 16 pruebas nuevas con subcasos independientes y regresiones |
| `test_stage065_preparation.cjs` | Manejador real de preparación, precisión, entradas conservadas, recálculo y resultado obsoleto |
| `evidence/stage065/` | Logs nuevos, reproducciones, entorno, payload CTX; generador y runner JS reproducibles |
| `docs/NUMERICAL_MODEL_AUDIT.md`, este cierre | Inventario, cuentas y continuidad |
| `docs/RESOURCE_MODELS.md` | Dominio y demanda frente a ingestión |
| `docs/REPRODUCIBILITY.md` | Evidencia posterior y comandos que preservan logs |
| `docs/AI_HANDOFF.md`, `docs/DEVELOPMENT_ROADMAP.md` | Estado local6.5 y siguiente intervención propuesta |

No se editan `web/`, datos, scripts de adquisición, cierres anteriores ni suites
heredadas. NumPy no se introduce como dependencia del CORE. Única instalación:
NumPy2.2.6 ya fijado en requirements, en el `.venv` propio existente.

## Entorno y comandos ejecutados

Python: `C:\Users\laura\OneDrive\Escritorio\NASA-PLANIFICATION-SANDBOX\.venv\Scripts\python.exe`,
3.11.9 amd64. NumPy2.2.6, pip24.0, setuptools65.5.0.
Plataforma reportada: Windows-10-10.0.26200-SP0; no se infiere edición comercial.
Node24.22.1 del runtime local; Git del runtime local. Ver environment.json.

Desde raíz:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -v
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -v
```

La primera ejecución fue previa a instalar y editar; la segunda fijó la referencia
completa antes de cambiar el motor. Se registraron errores/skips, no se omitieron.
Tras correcciones se ejecutó de nuevo el discovery con el mismo comando.
La ejecución tuvo autorización fuera del aislamiento que impedía acceso Git al
checkout; pruebas HTTP localhost incluidas, sin fallos de sockets en la final.

Evidencia adicional desde raíz:

```powershell
& .\.venv\Scripts\python.exe prototypes/mission_planner/evidence/stage065/generate_evidence.py
& 'C:\Users\laura\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' prototypes/mission_planner/evidence/stage065/run_frontends.cjs
```

Desde `prototypes/mission_planner`:

```powershell
& ..\..\.venv\Scripts\python.exe -S -m unittest test_mars_route_planner test_mars_mission_resources test_stage01 test_stage02 test_stage03 test_stage05 test_stage065_numerical -v
```

El intento inicial de este último comando desde raíz falló por imports; el cwd
correcto anterior dio71/71. No se cambió código para ocultar ese error operativo.
Un primer test nuevo confundió nutrición con O2 de tasa cero; otro comparó arrays
entre contextos VM con prototipos distintos: ambos tests fueron corregidos,
conservando logs fallidos y comprobaciones sustantivas.

## Resultados y evidencias

Ruta relativa desde raíz: `prototypes/mission_planner/evidence/stage065/`.

| Registro | Resultado real |
|---|---|
| baseline-initial.log | 64 ejecutadas, 5 errores, 6 skips por NumPy ausente |
| install.log, dependencies-initial.txt, dependencies.txt | Entorno propio registrado, dependencia fijada instalada |
| baseline.log | 101/101,18.507s, sin skips, antes de editar motor |
| stage06-baseline-js.log, stage06_maps-baseline-js.log | Ambas suites heredadas PASS antes de editar |
| reproduced-before.json, underflow-before.json | Casos ejecutados antes de corregir cada defecto |
| numerical-first.log, numerical-second.log | Fallo del test de estado; reproducción de desacuerdo real de suma rápida |
| tests.log | 117/117,20.658s; antes del último guarda de subdesbordamiento |
| tests-final.log | **117/117,19.168s, sin skips**, tras últimas correcciones |
| core-no-site.log | **71/71,2.623s, sin skips**, 55 heredadas+16 nuevas sin site-packages |
| javascript-final.log | **3 suites PASS**, dos heredadas y nueva prueba de preparación |
| preparation.json, generate.log | CTX real ya local: candidato rechazado por presupuesto→preparación→SUCCESS, mismo path |
| environment.json | Intérprete, plataforma, dependencias |

En el caso CTX: salida [50,49], destino [50,80], tres obstáculos simulados;
necesidad batería690.5748291304726 Wh incluida reserva10 Wh. Se registra ajuste
por recurso y cálculo nuevo. El JSON contiene perfil original/efectivo, escenario,
marcos, unidades, snapshot y waypoints. La prueba JS verifica el manejador real
con ese payload y un saldo que ya alcanza, sin redondear ni aumentar de más.

No se necesitan capturas ni nueva verificación visual para esta auditoría sin
cambios de interfaz. Los dobles DOM se identifican como tales, no como navegador.
La etapa6 histórica conserva su estado INCOMPLETA y sus pendientes propios.

## Cambios de comportamiento y compatibilidad

Ecuaciones y unidades se conservan. Se endurece el dominio de números antiguos
que aceptaban bool/no finitos o producían negativos. Derivaciones fuera de rango
ya no se confunden con falta física de recursos o ruta. Las fachadas mantienen
contratos3.0/5.0, agregando reason_code NUMERIC_DOMAIN_EXCEEDED dentro de
INVALID_INPUT existente; envolvente rápida6.1 conserva estructura, con errores
numéricos del puente como UIInputError/HTTP400. Excepciones internas inesperadas
siguen fuera de esa captura específica.

Tolerancia de presupuestos, dominancia y consistencia1e-9 absoluta sin cambios;
A* conserva1e-10. No se recorta el margen exportado. No se cambia cálculo por
redondeo de presentación. El orden cronológico evita una discrepancia numérica
concreta, sin modificar las fórmulas ni la selección geométrica del candidato.

## Tabla de aceptación

| Criterio | Estado / comprobación |
|---|---|
| 1. Inventario código/unidades | Cumple: tabla en auditoría |
| 2. Doce cuentas independientes | Cumple: tablas manuales y tests con esperados independientes |
| 3. Exacto frente a insuficiente | Cumple: cada recurso y borde de tolerancia |
| 4. Reservas/histórico sin doble descuento | Cumple: reservas distintas, saldos e histórico informativo |
| 5. Perfiles y estados diferenciados | Cumple: rover, astronauta, modeled0, excluded y not_applicable |
| 6. Demanda frente a ingestión | Cumple: significado documentado sin prescripción |
| 7. Escenarios/preparación | Cumple: tasas, ascenso no escalado, candidato completo y botón real |
| 8. Eventos/fases/totales/JSON | Cumple: sumas, saldos, margenes, JSON estricto y ensayo CTX |
| 9. Dominio numérico | Cumple: inválidos, desbordamiento, subdesbordamiento de duración y fronteras explícitas |
| 10. Defectos y regresiones | Cumple: reproducciones anteriores, correcciones mínimas y tests |
| 11. Regresiones anteriores | Cumple:101 heredadas dentro de117, sin skips;2 JS heredadas |
| 12. CORE independiente | Cumple:71 tests -S e import sin UI/red/ROS/NumPy |
| 13. Reproducción y cierre | Cumple: comandos, entorno, logs, auditoría y este cierre |

## Límites conservados e inicio concreto de 6.6

Los parámetros y perfiles siguen simulados. No se calibra agua/O2/demanda,
traje, movimiento, esfuerzo ni carga. O2 permanece simulated_u. nutrition_kcal
contabiliza demanda estimada y su límite de escenario; no describe ingestión,
absorción, nutrición diaria ni reservas fisiológicas. Masa/altura informativas.
No se añaden datos científicos, capas, cobertura, algoritmos o interfaces.

6.6 solo comenzará con autorización posterior. Su primera tarea concreta:
construir un caso finito en que el candidato A* no quepa en los recursos y
buscar si el detallado encuentra otra alternativa; definir/versionar estados de
candidato frente a inviabilidad global antes de cambiar algoritmos. Conservar
las regresiones numéricas6.5 y no comparar costos con pesos diferentes.
6.7–6.9 y ROS permanecen pendientes. No hay bloqueo obligatorio de6.5.

**No hubo commits, push, PR, merge ni modificaciones al proyecto anterior.**
