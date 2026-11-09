# Arquitectura actual

La migración conserva el prototipo; no aplica todavía una reestructuración de paquetes.

```text
web/index.html + map-app.js + map.css + Leaflet
                 -> mission_ui (HTTP localhost)
                 -> expanded_ui -> regional_ui -> MissionBridge
                    | rápido: fast_mission -> RiskAwareAStar
                    | detallado: mission_decisions -> ResourceMissionPlanner
                    -> mission_api._breakdown -> resultados/recursos/JSON
datos -> jezero_adapter / jezero_map -> TerrainReference + marcos
```

`RiskAwareAStar` usa ocho vecinos, pendiente, riesgo, rugosidad, clearance y control de huella por segmento. Snapshot evita mutaciones incoherentes. A* usa heurística euclídea y límite opcional de expansiones.

`ResourceMissionPlanner` explora etiquetas no dominadas por posición/fase, costo y recursos. Comprueba ida, actividad y base terminal; puede regresar desde posición intermedia. Las etiquetas incluyen consumos y padres. El límite no equivale a inviabilidad.

`mission_api` 3.0 representa misión nueva inicio=base. `mission_decisions` 5.0 añade estado y saldo, políticas, comparación y continuar/regresar. La UI 6.0/6.1 envuelve contratos; no es una API pública de producción.

En rápido se elige camino geométrico antes de comprobar consumos. No equivale a búsqueda con restricciones de recursos. `candidate_plan` no es un plan confirmado. En detallado la selección entre SUCCESS prioriza tiempo y batería, no compara costos de pesos diferentes.

Dependencias: CORE biblioteca estándar; lector NPZ NumPy; preparación offline Rasterio; runtime JSON regional no importa Rasterio. Node sirve para pruebas JS. Leaflet local, imágenes NASA Trek remotas.

Objetivo incremental futuro: CORE puro; DATA ADAPTERS; MISSION API versionada; ROS 2 ADAPTER separado; EVALUATION. El adaptador ROS debe llamar a las mismas fachadas y transportar marcos/recursos por contratos apropiados, sin duplicar búsqueda. Ningún paquete ROS se implementa en bootstrap.
