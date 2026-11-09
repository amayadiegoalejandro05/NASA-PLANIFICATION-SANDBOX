# MARS GOD'S EYE — Documento maestro de continuidad

> **Estado:** concepto y arquitectura preliminar; no equivale a un sistema implementado.  
> **Fecha del contexto:** 17 de octubre de 2026.  
> **Propósito:** trasladar el contexto completo a otra conversación de ChatGPT y continuar el proyecto sin empezar desde cero.  
> **Nombre provisional:** **MARS GOD'S EYE — Martian Mission Intelligence & Rover Operations**. El nombre puede cambiar.

---

## 0. Resumen ejecutivo

El proyecto propone desarrollar un **centro avanzado de exploración marciana** que combine un **mapa 3D de Marte basado en datos geoespaciales y científicos**, un **motor de planificación de misiones y rutas**, un **rover físico de seis ruedas tipo NASA JPL** y un **sistema experimental de navegación bioinspirada** basado en el software del repositorio `Spot-micro-twins` (módulo `fly_brain`, documentado en su **README V2**).

La demostración se realizará sobre un **terreno marciano análogo**, construido con paneles de espuma rígida tallada y pintada, y digitalizado/calibrado para que el rover pueda recorrer rutas propuestas por el mapa. El vehículo estará conectado con **Raspberry Pi y WebSocket** al computador que ejecuta la estación de control. El mapa presentará en tiempo real la trayectoria, la telemetría, los objetivos científicos y las decisiones del sistema.

La idea busca sobresalir en un **reto internacional relacionado con NASA** (en la conversación se mencionó NASA Space Apps y el tema de mapas marcianos). **La convocatoria, el reto concreto, sus reglas y las restricciones de tiempo/equipo siguen pendientes de confirmación antes de delimitar el entregable competitivo.** No atribuir al reto obligaciones que no estén escritas en la convocatoria oficial.

**Diferenciador principal:** no es solamente un rover por control remoto ni solamente un mapa 3D. Es un sistema de **planificación científica + autonomía experimental + validación física y trazabilidad de decisiones**.

## 1. Visión de la demostración

1. Abrir una estación de control basada en **God's Eye View**, adaptada a Marte (sin módulos específicos de la Tierra).
2. Seleccionar una región, inicialmente **el cráter Jezero** como candidato, por su disponibilidad de datos de exploración.
3. Activar capas como imágenes orbitales, elevación, pendientes, geología y áreas potencialmente transitables.
4. Marcar inicio, destino y puntos de interés científico sobre el mapa.
5. Calcular una **ruta global** con costos por distancia, pendiente, obstáculos y riesgo.
6. Relacionar una sección del mapa de Marte con un **terreno físico análogo** de espuma (sin afirmar una réplica geológica exacta).
7. Enviar waypoints locales mediante un servidor WebSocket a un **agente en Raspberry Pi**, con supervisión de seguridad y control de actuadores separado.
8. Ejecutar la misión en el rover físico, con **piloto neuronal experimental o controlador clásico** seleccionable.
9. Mostrar en tiempo real pose, progreso de misión, obstáculos, alertas, estado de conexión, trayectoria planeada vs. ejecutada y métricas.
10. Exportar resultados y comparar el desempeño de enfoques de navegación.

**Principio de diseño:** el rover físico valida operaciones sobre un **análogo terrestre**; no «se mueve realmente sobre Marte». Mantener explícita la separación entre datos planetarios, maqueta física, simulación y sensores reales.

## 2. Repositorios y roles

### A. Spot Micro Twins — principal base de software experimental
- Repositorio: https://github.com/jorgefajardom-coder/Spot-micro-twins
- README V2 a revisar prioritariamente: https://github.com/jorgefajardom-coder/Spot-micro-twins/blob/main/desktop/fly_brain/README.md
- Función propuesta: motor de comportamiento autónomo, conectoma/simulación neuronal, piloto reactivo, herramientas de percepción y simulación, exportaciones, mecanismos de evaluación y, cuando convenga, componentes de comunicación.
- **Prioridad del usuario:** **examinar el SOFTWARE y el README V2, no centrar el análisis en el hardware del robot Spot Micro.**
- La conversación previa identificó estos archivos o carpetas como relevantes (verificar ruta y versión en el repositorio antes de programar):
  - `desktop/fly_brain/pilot.py`
  - `desktop/fly_brain/lif.py` y `lif_gpu.py`
  - `desktop/sim_world.py`
  - `desktop/spot_brain.py`
  - `desktop/cave_explorer.py`
  - `desktop/gait.py` y `kinematics.py` (referencias de locomoción original, a reemplazar o aislar)
  - `firmware/spotmicro_esp32/` (referencia secundaria para arquitectura de comunicación, **no** base del controlador de locomoción del rover)
- Hallazgos expuestos en la conversación previa, **a contrastar directamente con el código/README actual**:
  - Se describe un conectoma basado en FlyWire de unas **138.639 neuronas**; modelo de neuronas LIF con implementaciones CPU/Numba y GPU/CuPy.
  - `FlyPilot`/`Senses` expresaría objetivos, dirección, distancia y amenaza, y produciría comandos de avance/giro como `vx` y `wz`.
  - Simulación con escaneo LiDAR 360°, visualización y reconstrucción/almacenamiento de puntos o vóxeles.
  - Algunos sensores y la pose del simulador son **idealizados**; acumulación de puntos con posición verdadera del simulador **no demuestra SLAM físico completo**.
  - El desempeño citado anteriormente (por ejemplo, `r = 0,999`, «8,3× tiempo real en GPU», «0,29× en CPU») son **cifras reportadas en documentación anterior**, no benchmarks reproducidos en esta planificación. Verificar definición de cada métrica, hardware, versión y metodología.
- Decisión propuesta: **desacoplar motor neuronal, simulación, navegación, sensores y GUI**. No integrar toda una GUI Python/PyVista dentro del visor web.

### B. God's Eye View — base de interfaz/centro de operaciones
- Repositorio: https://github.com/bilawalsidhu/gods-eye-view
- Función: HUD, interfaz, visualización de globo, gestión de capas y experiencia de centro de misión.
- Adaptación: sustituir la orientación terrestre por un **modo Marte**; conservar módulos genéricos y deshabilitar/eliminar progresivamente los servicios terrestres.
- **Desactivar/excluir del modo Marte:** ADS-B/tráfico aéreo, AIS/marítimo, tráfico de carreteras, cámaras CCTV terrestres, terremotos de la Tierra, climatología terrestre, dependencias directas de cartografía Earth/OSM/Google Earth que no apliquen.
- **Conservar y transformar:** globo/cámara 3D, HUD, paneles, capas, marcadores, rutas, notificaciones, interfaces de datos, estado de sesión y control de misión.
- Evitar una eliminación destructiva inicial: crear fork y separar módulos mediante una configuración `mars` o estructura de proveedores/escenas. Revisar licencias y dependencias reales antes de modificar.
- Proyecto anterior citado sobre Marte en God's Eye View (confirmar su vigencia): https://github.com/bilawalsidhu/gods-eye-view/issues/738

### C. NASA JPL Open Source Rover — referencia mecánica
- Repositorio: https://github.com/nasa-jpl/open-source-rover
- Código de referencia: https://github.com/nasa-jpl/osr-rover-code
- Función: arquitectura de rover de **seis ruedas**, suspensión **rocker-bogie** y sistemas de dirección/locomoción del vehículo.
- Decisión del usuario: **buscar el rover más avanzado y profesional posible**. Se prefiere un diseño inspirado en NASA JPL a un kit educativo básico.
- **Alcance de este documento:** el software es el elemento diferenciador; mecánica, presupuesto, impresión/fabricación, motores y controladores se dimensionarán más adelante.
- La estimación publicada para construir el rover JPL es elevada, del orden de **100 horas-persona o más**; no asumir que el hardware será ejecutable en un hackathon corto sin preparación previa y sin verificar reglas.

## 3. Recursos marcianos previstos

Fuentes candidatas, no integración terminada:

- **Cesium Mars** como posible base de globo/escena planetaria: https://cesium.com/platform/cesium-ion/content/cesium-mars/
- **NASA Mars Trek** para acceso a capas/servicios geoespaciales: https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars
- **MOLA, HRSC, CTX, HiRISE**: terreno, altimetría e imágenes, según disponibilidad y licencia.
- **USGS**: cartografía geológica y modelos topográficos.
- Datos de misiones (rovers) y meteorología marciana **histórica**, si aportan al objetivo.

**Regla de rigor:** cada capa debe mostrar procedencia, escala/resolución, sistema de coordenadas, fecha/época y limitaciones. Un mosaico orbital no equivale a un DEM de alta resolución; una imagen de Marte no mide por sí sola la transitabilidad. No mezclar latitudes planetocéntricas/planetográficas, longitudes este/oeste ni marcos de referencia sin conversión explícita. Confirmar soporte de Marte y servicios de Cesium antes de implementar.

## 4. Terreno marciano análogo (maqueta)

- El usuario propuso **fabricar el terreno con espuma y pintarlo**.
- Diseño preliminar: **2,4 × 1,2 m**, dividido en paneles transportables, ajustable según espacio real.
- Construcción candidata: espuma rígida **XPS**, capas talladas, sellador compatible, pintura acrílica, textura superficial y base rígida estable.
- Formas: cráter, pendientes, relieve irregular, rocas/obstáculos, rutas seguras y de riesgo, puntos de interés.
- Se recomienda medir alturas y pendientes e identificar obstáculos en un sistema métrico local.
- Para validación de pose: **cámara cenital + marcadores ArUco** en el entorno; comparar con odometría e IMU. Calibrar cámara y transformación, no suponer exactitud perfecta.
- **Cuidado con la nomenclatura:** es un **terreno análogo inspirado en una región marciana**, no una réplica exacta. Para reproducir un DEM se necesitan datos adecuados y una transformación de escala documentada; donde falte resolución, el relieve será esquemático.
- Evitar superficies que patinen demasiado o destruyan ruedas/transmisión; comprobar estabilidad mecánica y seguridad eléctrica.

## 5. Arquitectura objetivo del sistema

```text
NASA / ESA / USGS / Cesium / Mars Trek
      │ Datos geoespaciales + metadatos
      ▼
┌──────────────────────────────────────────────────────────────┐
│ GOD'S EYE VIEW — MARS / MISSION CONTROL (web)                │
│  - Globo 3D marciano y capas                                 │
│  - Selección científica de objetivos                         │
│  - Rutas, riesgos, waypoints                                 │
│  - HUD, estado de misión y telemetría                         │
└─────────────────────────┬────────────────────────────────────┘
                          │ API y WebSocket autenticados
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ MISSION BACKEND (PC anfitrión)                               │
│  - Planificación global y mapa de costos                    │
│  - Orquestación, validación de comandos y logging            │
│  - Coordenadas Marte ↔ terreno análogo (calibración)          │
│  - Registro, métricas, replay y telemetría                    │
└────────────────────┬────────────────────┬────────────────────┘
                     │                    │
                     ▼                    ▼
┌──────────────────────────┐ ┌────────────────────────────────┐
│ FLY BRAIN / PILOTO V2    │ │ PERCEPCIÓN / LOCALIZACIÓN       │
│ en PC potente, opcional  │ │ odometría + IMU + cámara        │
│ GPU: comportamiento      │ │ LiDAR/depth opcional;          │
│ reactivo experimental    │ │ mapa local y SLAM si se valida │
└────────────┬─────────────┘ └──────────────┬─────────────────┘
             └─────────────┬───────────────┘
                           ▼
                    SUPERVISOR DE SEGURIDAD
                (límites, prioridades, watchdog)
                           │ comandos autorizados
                           ▼
                 WebSocket / red local Wi-Fi
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ RASPBERRY PI — ROVER AGENT                                   │
│  - Cliente WebSocket, telemetría, estados                    │
│  - Adaptador de comandos / enlace con control de motores     │
│  - Adquisición de cámara y sensores                           │
│  - Freno/parada por pérdida de comunicación                   │
└─────────────────────────┬────────────────────────────────────┘
                          ▼
              CONTROLADOR DEDICADO (p. ej., ESP32)
           velocidades de motores, encoders, PID, E-STOP
                          ▼
                ROVER 6 RUEDAS ROCKER-BOGIE
```

### Distribución de cómputo propuesta

- **PC/servidor**: Cesium/visualización web, datos de Marte, planificación, tareas intensivas de visión y **conectoma completo** experimental en CPU/GPU según benchmarks reales.
- **Raspberry Pi (versión por decidir; Pi 5 como candidata)**: nodo/agente del vehículo, adquisición y publicación de datos, enlace con control de bajo nivel. No dar por garantizado que ejecuta el conectoma completo en tiempo real.
- **Microcontrolador/controlador dedicado**: bucles deterministas de control de motores, encoders, protecciones y parada segura. El navegador nunca debe accionar los motores directamente.
- **ROS 2**: opción de integración futura para nodos, TF, navegación, SLAM y rosbag; **no incluirlo por inercia** si añade complejidad y no resuelve una necesidad en el MVP.

## 6. Reutilización real del software de Spot Micro V2

**Conservar (después de inspección de código, pruebas y licencias):**
- Abstracción percepción → `Senses` → `FlyPilot` → comando de velocidad.
- Motor neuronal LIF, variantes CPU/GPU, estados y visualización de actividad como herramienta investigativa.
- Registro de decisiones, trazas del simulador, utilidades de entorno, herramientas 3D y exportación.
- Ideas de ensayos comparativos, pruebas unitarias y separación de módulos.

**Reemplazar/reescribir:**
- `gait.py`, cinemática de patas, postura corporal y servos propios del Spot Micro.
- Modelo de locomoción: usar cinemática y restricciones de **rover de seis ruedas**, dirección por ruedas, velocidad angular, saturaciones y maniobrabilidad.
- Entradas ideales de simulación: convertir a interfaces de observación con calidad/confianza e indicar claramente qué es simulado o real.
- Integración GUI: publicar datos y eventos por API, no embebido de toda la aplicación de escritorio en Cesium.
- Puente `FlyPilot` → sistema de navegación: el piloto neuronal **propone** comandos; el supervisor y controlador determinista **autorizan/ejecutan**.

**Advertencia científica:** la capacidad de generar comportamientos reactivos no significa que exista navegación autonóma integral, planificación global, SLAM real ni validación para Marte. Presentar el conectoma como módulo de investigación y comparar contra una referencia clásica.

## 7. Navegación jerárquica y seguridad

- **Nivel global:** representación de terreno + mapa de costos (pendiente, distancia, riesgo, obstáculos y objetivos científicos); algoritmo A*, Dijkstra o equivalente apropiado a la resolución.
- **Nivel local:** seguimiento de waypoints, control de velocidad, evasión ante nuevos obstáculos; pilotos intercambiables:
  1. **Baseline clásico** y verificable (seguimiento y evasión convencionales).
  2. **Fly Brain V2** como controlador de comportamiento **experimental**.
- **Supervisor:** geocerca de maqueta, límites de velocidad, inclinación, proximidad, prioridad de comandos, estados de seguridad, mando manual y parada de emergencia.
- **Ante desconexión:** watchdog local, timeout de órdenes, velocidad a cero y procedimiento de recuperación; no depender de una reconexión WebSocket para poder detener el vehículo.
- No pretender que la red local reproduce comunicaciones reales Tierra–Marte; si se simula latencia marciana, declararla como escenario separado de demostración.

## 8. Contrato de comunicaciones propuesto (todavía NO implementado)

Un **servidor WebSocket** en el computador se comunica con un **cliente/agent** en la Raspberry Pi. Diferenciar eventos de telemetría, estado y comandos. La frecuencia debe dimensionarse según enlace, sensores y control de bajo nivel.

**Telemetría (ejemplo de diseño):**

```json
{
  "type": "rover.telemetry",
  "schema_version": "0.1",
  "mission_id": "mars-analog-001",
  "seq": 1042,
  "timestamp_utc": "2026-10-17T21:00:00Z",
  "frame": "analog_map",
  "pose": {"x_m": 1.2, "y_m": 0.8, "yaw_rad": 0.35},
  "navigation": {
    "mode": "autonomous",
    "controller": "fly_brain",
    "waypoint_index": 3,
    "safety_state": "normal"
  },
  "link": {"connected": true}
}
```

**Comando (ejemplo de diseño):**

```json
{
  "type": "rover.command_velocity",
  "schema_version": "0.1",
  "mission_id": "mars-analog-001",
  "command_id": "cmd-204",
  "frame": "base_link",
  "vx_mps": 0.12,
  "wz_radps": 0.20,
  "ttl_ms": 300,
  "source": "mission_supervisor"
}
```

Requisitos de implementación: handshake/versiones, identificación de misión, confirmación de mensajes críticos, validación de rango y unidad, estados de conexión, reconexión con parada segura, registro de eventos, control de acceso y, si procede, TLS. Video por canal separado (WebRTC/MJPEG) si facilita rendimiento.

## 9. Marcos de referencia y vínculo con el mapa

Mantener al menos **tres marcos diferentes**:

1. **Marte planetario:** coordenadas planetarias y elevación, según fuente científica.
2. **Mapa análogo físico:** coordenadas métricas `(x_m, y_m, z_m)` sobre la maqueta; origen y escala establecidos por calibración.
3. **Base del rover:** movimiento local y sensores a través de transformaciones relativas.

Crear un **archivo de calibración** versionado que relacione una zona seleccionada de Marte con el escenario análogo (por ejemplo, escala, rotación, origen y puntos de control). Una vez creada, la maqueta funciona como banco de ensayo; sus rocas y microrelieves no se deben presentar como datos observados por satélite.

Comparar siempre **ruta deseada** y **ruta ejecutada**, conservando la fuente de la estimación de pose: odometría, cámara cenital, SLAM, etc.

## 10. Métricas para demostrar valor técnico

**Comparación:** ejecutar las mismas misiones con controlador clásico y con Fly Brain V2, bajo condiciones equivalentes; repetir ensayos.

| Métrica | Qué revela |
|---|---|
| Éxito de misión (%) | Objetivos alcanzados dentro de reglas |
| Error lateral medio y máximo (m) | Fidelidad al recorrido planificado |
| Longitud total de ruta y tiempo (m, s) | Eficiencia operacional |
| Colisiones / intervenciones de seguridad | Riesgo y robustez |
| Violaciones de pendiente y margen ante obstáculos | Transitabilidad real del análogo |
| Latencia extremo a extremo y pérdida de mensajes | Calidad de comunicación |
| Error de localización con respecto a referencia externa | Calidad de percepción/odometría |
| Tiempo de cómputo por decisión y uso de recursos | Viabilidad de la arquitectura |

Se deben comparar escenarios nominales y perturbados (obstáculos reubicados, pérdida breve de red, variaciones de iluminación). No afirmar superioridad del piloto neuronal sin datos estadísticos y resultados reproducibles. Documentar también los fallos.

## 11. Priorización para asegurar un demostrador competitivo

### P0 — Núcleo indispensable (MVP)
1. Un **mapa marciano 3D** funcional, con al menos una capa científica y metadatos de fuente.
2. Selección de ruta, waypoints y evaluación simple de pendiente/riesgo.
3. Maqueta análoga, rover conectado por WebSocket, telemetría real y seguimiento de ruta **seguro**.
4. Comparación mapa/ruta planificada contra trayectoria medida y reproducción de una misión.
5. Guion de demostración claro y reproducible, incluso ante conectividad limitada.

### P1 — Diferenciadores de alta prioridad
1. Piloto neuronal Fly Brain V2 como controlador alternativo, con baseline clásico.
2. Percepción local, detección de obstáculos y relocalización mediante cámara cenital/ArUco.
3. Visualización de decisiones, actividad neuronal, alertas y métricas comparativas.
4. Exportación de resultados y reporte científico de misión.

### P2 — Investigación y ampliaciones
1. SLAM 2D/3D real sin posición perfecta del simulador.
2. Fusión LiDAR/profundidad/IMU y terreno 3D más exigente.
3. Integración ROS 2/Nav2 si aporta valor probado.
4. Planificación avanzada con incertidumbre, cobertura, energía y múltiples objetivos.
5. Simulaciones de delay de comunicaciones interplanetarias y mayor autonomía.

## 12. Orden de trabajo recomendado

| Fase | Trabajo principal | Criterio de salida |
|---|---|---|
| 0. Auditoría de repositorios | Inspeccionar código real, README V2, versiones, licencias y ejecutabilidad | Inventario comprobado y módulos reutilizables definidos |
| 1. Diseño de interfaces | Contratos `Senses` / `Pilot` / `Waypoint` / WebSocket / transformaciones | Simuladores y mocks intercambiables |
| 2. Marte en God's Eye View | Desactivar módulos Tierra, activar Cesium/Marte, cargar datos | Globo marciano navegable y capa verificable |
| 3. Planificador de misión | Grafo/malla, costos de ruta y riesgos | Ruta reproducible y metadatos visibles |
| 4. Simulador rover | Adaptar locomoción y terreno; aislar `fly_brain` | Comparación clásica vs bioinspirada en simulación |
| 5. Rover Agent | Raspberry Pi, enlace, estados, watchdog y telemetría | Comandos y mediciones seguros en banco |
| 6. Maqueta y calibración | Construcción y marco análogo, localización externa | Pose medida y transformación comprobada |
| 7. Integración y ensayo | Rutas reales, alertas, logs y métricas | Demostración repetible en terreno |
| 8. Entrega | Video, demo, README, reproducibilidad y pitch | Evidencia ligada a criterios reales del reto |

**Estimación conversada, no cotización:** aproximadamente **142–275 horas-persona** para integración ambiciosa, potencialmente más según fabricación, dependencias y alcance. Se necesita reducir alcance si las reglas exigen producirlo dentro de un evento corto.

## 13. Riesgos y decisiones técnicas pendientes

1. **Requisitos del concurso:** confirmar desafío, reglas de construcción previa, uso de hardware, datos permitidos, propiedad intelectual, fecha y criterios de evaluación.
2. **Capacidad del hardware disponible:** revisar computador anfitrión y GPU real antes de prometer conectoma completo a tasa de control útil.
3. **Complejidad del rover JPL:** presupuesto, fabricación, energía, tiempo y tolerancia a fallas. Si no llega el vehículo definitivo, mantener simulador/software reproducible como ruta de contingencia.
4. **Integración de Cesium Mars:** soporte marciano real, proyecciones, datasets y licencias; no limitarse a colorear el planeta Tierra de rojo.
5. **Cálculo científico:** usar DEM correcto para pendientes; verificar resolución y incertidumbre.
6. **Simulación vs realidad:** no usar pose perfecta del simulador como prueba de SLAM; distinguir sensores ideales y reales.
7. **Conectoma y rendimiento:** evaluar CPU/GPU y frecuencia de actualización, no pasar matrices neuronales gigantes por la red en cada ciclo.
8. **Seguridad del rover:** arquitectura de control local con parada autónoma y E-STOP.
9. **Licencias de los tres repositorios y datasets:** inspeccionar archivos LICENSE/NOTICE y restricciones de servicios/datos antes de redistribuir.
10. **Nombre y marca:** MARS GOD'S EYE es provisional; no implicar aval oficial de NASA/ESA.

## 14. Estructura inicial sugerida de software

```text
mars-gods-eye/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── nasa-challenge-requirements.md
│   ├── data-provenance.md
│   └── experiment-protocol.md
├── apps/
│   └── mission-control-web/      # Adaptación/fork God's Eye View
├── services/
│   ├── mission-api/              # Orquestación y WebSocket
│   ├── route-planner/            # Planificación y riesgo
│   ├── fly-brain-adapter/        # Adaptador Spot Micro V2
│   ├── perception-localization/  # Pose/mapa real o simulado
│   └── rover-simulator/         # Rover, terreno y pruebas
├── rover/
│   └── raspberry-agent/         # Telemetría, control seguro
├── datasets/
│   └── README.md                 # Solo metadatos y enlaces autorizados
├── configs/
│   ├── mars-region.yaml
│   ├── analog-calibration.yaml
│   └── rover-limits.yaml
└── tests/
    ├── integration/
    └── evaluation/
```

Es **una propuesta de organización**, no un árbol que exista ya. Mantener los forks y créditos de repositorios externos claramente identificados.

---

## 15. Solicitud precisa para la próxima conversación

> Estamos desarrollando **MARS GOD'S EYE**, una plataforma de misión marciana orientada a un reto internacional NASA: God's Eye View adaptado a Marte, datos geoespaciales científicos, planificación de rutas, rover de seis ruedas tipo NASA JPL, terreno físico análogo fabricado con espuma y pintado, y conexión de Raspberry Pi por WebSocket. Queremos reutilizar **sobre todo el SOFTWARE de `Spot-micro-twins`, especialmente el README V2 de `desktop/fly_brain`**, como piloto neuronal experimental y motor de simulación/percepción. Lee este documento completo. **Primero verifica directamente el repositorio y su README V2**; distingue lo existente de lo propuesto y evita centrarte en el hardware del cuadrúpedo. Después presenta una auditoría técnica de módulos reutilizables y una arquitectura de interfaces concreta. Prioriza un MVP que integre mapa marciano, rutas científicas, telemetría física, seguridad y ensayo repetible; el conectoma neuronal debe compararse frente a un baseline clásico, no asumirse superior. Avancemos por fases, con decisiones justificadas, criterios de aceptación y sin rehacer componentes que ya funcionen.

### Primera tarea sugerida

**Revisar `Spot-micro-twins/desktop/fly_brain/README.md` y los módulos importados por el piloto V2**, entregando:

1. Mapa real de dependencias y puntos de entrada ejecutables.
2. Funciones/clases efectivamente implementadas, citas a rutas/líneas o commits cuando sea posible.
3. Separación entre motor neuronal, lógica reactiva, simulación, visualización y datos sintéticos.
4. Propuesta mínima de interfaz `PilotAdapter` para un rover diferencial/direccionable de seis ruedas.
5. Prueba inicial simulada para confirmar que el piloto emite velocidades coherentes y puede ser desactivado por el supervisor.

---

*Fin del documento maestro. Este archivo documenta la intención y decisiones discutidas; la inspección exhaustiva del código, el control de versiones y la implementación siguen siendo actividades pendientes.*
