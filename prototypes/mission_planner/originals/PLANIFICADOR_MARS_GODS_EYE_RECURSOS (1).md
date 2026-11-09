# MARS GOD'S EYE - Planificador de rutas y recursos V0.1

## Responsabilidad
Construir un planificador que seleccione un recorrido de **base -> objetivo cientifico -> base** respetando la transitabilidad del terreno y los presupuestos de recursos con reservas. El modo astronauta y el modo rover comparten el mapa, pero **usan modelos de consumo y limites distintos**.

**Estado:** prototipo probado con datos completamente sinteticos. No es un sistema de navegacion operativa ni un modelo validado de astronauta o rover marciano.

## Entradas
- Mapa cuadriculado: elevacion por celda (m), obstaculos, riesgo (0 a 1), rugosidad (0 a 1), resolucion (m/celda).
- Punto de partida/base y objetivo en coordenadas de celda.
- Tiempo de trabajo en el objetivo (min).
- Perfil de movimiento: velocidad en m/min, limite de pendiente, huella del vehiculo, consumos por minuto y penalizaciones de ascenso/rugosidad.
- Presupuesto total y reserva obligatoria por recurso: tiempo, oxigeno simulado, agua potable, bateria y demanda energetica nutricional.

## Salidas
- Ruta completa de ida y regreso, con indice del objetivo.
- Distancia total (m), tiempo total con actividad (min).
- Consumos acumulados: O2 en unidades ficticias, agua (L), bateria (Wh), demanda calorica (kcal).
- Rechazo explicito si no existe una mision completa admisible.

## Archivos
- `mars_route_planner.py`: A* del terreno, mapa de riesgo, obstaculos, pendientes y margen de seguridad. Existia previamente; no se modifica.
- `mars_mission_resources.py`: capa NUEVA de planificacion con restricciones multirrecurso y regreso a base.
- `test_mars_route_planner.py`: pruebas del planificador del terreno (existentes).
- `test_mars_mission_resources.py`: nuevas pruebas de ida y regreso, reservas, pendientes, baterias y rechazos.

## Modelo y algoritmo
Para cada tramo transitable, estimar:

    tiempo = distancia / velocidad_base * (1 + penalizacion_subida + penalizacion_rugosidad)
    O2 = tiempo * tasa_O2 * factor_esfuerzo
    agua = tiempo * tasa_agua * factor_esfuerzo
    bateria = tiempo * tasa_bateria + energia_extra_subida
    kcal = tiempo * tasa_metabolica * factor_esfuerzo

El planificador usa busqueda de etiquetas no dominadas: cada estado incorpora celda y un indicador de que ya visito el objetivo, junto con costo y recursos consumidos. Una etiqueta se descarta solo si otra es al menos tan buena en costo y todos los recursos restringidos. El objetivo final es **volver a la base tras visitar el destino**, no solo llegar a destino. Las limitaciones fisicas de la ruta del A* existente son restricciones duras.

    consumo_total_recurso <= disponibilidad - reserva

La prioridad de optimizacion combina tiempo estimado y penalizaciones por terreno y bateria. Los pesos se deben justificar y calibrar; encontrar una ruta factible **no demuestra** seguridad de una EVA real.

## Modos
### Astronauta
Consumibles de soporte vital, agua, bateria, tiempo y demanda calorica. Las unidades de O2 son **ficticias** y no representan una cantidad real de gas. El modelo calorico solo estima demanda energetica; NO supone que toda esa energia se ingiera durante una caminata breve. El minimo de 240 mL/h de hidratacion EVA y la provision de nutricion para EVA de superficie superiores a 4 horas constan en NASA-STD-3001; la fisiologia real requiere un modelo validado y mas variables.

### Rover
Se modelan bateria, tiempo y limites del terreno; O2, agua y comida no aplican. El modelo de energia no incorpora aun corriente medida, motor por rueda, deslizamiento, variacion termica ni traccion real.

## Como ejecutar
Python 3.10+ y archivos colocados en la misma carpeta:

    python mars_mission_resources.py
    python -m unittest test_mars_route_planner.py test_mars_mission_resources.py -v

Resultado de la demo sintetica actual:

| Modo | Distancia total | Tiempo total | Bateria estimada | Otros |
|---|---:|---:|---:|---|
| Astronauta | 1232.0 m | 53.1 min | 37.1 Wh | O2: 13.27 u inventadas; agua: 0.212 L; demanda: 212 kcal |
| Rover | 12.6 m | 89.4 min | 80.5 Wh | O2, agua y comida: no aplican |

Pruebas automáticas: 15/15 aprobadas, 7 heredadas del A* y 8 nuevas del planificador de recursos.

## Pendientes antes de integracion
1. DEM georreferenciado real de Marte, con metadatos de resolucion y fuente; no usar la maqueta como si fuera la superficie orbital.
2. Modelo de movilidad distinto para astronauta y rover: pendiente transversal, estabilidad, terreno suelto y transitabilidad, calibrados.
3. Modelos de consumo basados en estudios/fichas del equipo real; confirmar unidades de O2 y CO2, autonomia termica y agua, y limites de operaciones EVA.
4. Replanificar continuamente con telemetria REAL de posicion y consumos. En cada punto verificar que queda un trayecto de regreso con reserva; si no, detener/exigir decision humana.
5. Representar incertidumbre cartografica, comunicacion, visibilidad, climatologia, iluminacion/radiacion y ventanas de mision solo si hay datos fiables.
6. Mejorar escalabilidad: busqueda multirrecurso puede crecer en costo computacional; probar mapas grandes, preprocesado, jerarquia de resoluciones y cotas.
7. Exportar ruta y consumos acumulados por segmento mediante API para mostrar en God's Eye View, evitando llamar seguro a un plan solo por estar dentro de los limites simulados.

## Criterios de aceptacion siguientes
- El usuario selecciona base, objetivo y reservas en un mapa sintetico.
- El sistema muestra ida, regreso, consumos estimados y recursos restantes.
- Aumentar la reserva o el tiempo de trabajo puede volver inviable una ruta.
- Un obstaculo nuevo provoca nueva planificacion o rechazo explicito.
- Los modelos de astronauta y rover tienen perfiles y unidades diferentes.

## Documentacion
- NASA-STD-3001, seccion 11, trajes espaciales: https://www.nasa.gov/reference/11-0-spacesuits-vol-2/
- NASA JPL, navegacion de rover y evaluacion de terreno: https://robotics.jpl.nasa.gov/what-we-do/flight-projects/mars-science-laboratory/surface-system-software-and-rover-navigation/
- NASA Space Apps, desafio Martian Map: https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/
