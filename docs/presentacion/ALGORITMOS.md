# Algoritmos y modelo matemático implementado

Referencias de implementación: `mars_route_planner.py`, `mars_mission_resources.py`, `mission_decisions.py`, `fast_mission.py` y `mission_api.py` en `prototypes/mission_planner/`. Este documento describe el baseline, no implementa cambios.

## 1. Grafo y transitabilidad

Una celda es (fila,columna); hasta ocho vecinos. Altura desconocida bloquea. Se comprueban extremos, pendiente local, pendiente de arista, bordes, radio+margen y barrido de huella. Las diagonales requieren celdas laterales transitables. La distancia declarada es horizontal, no longitud 3D.

Cada celda ocupada representa un cuadrado completo. El barrido usa envolventes conservadoras; puede rechazar pasos geométricamente posibles cerca de esquinas. No modela rocker-bogie, orientación, adherencia, vuelco ni rocas subpíxel.

El snapshot inmutable impide mezclar elevaciones nuevas con pendientes o clearance antiguos. Un cambio requiere nueva instancia/revisión.

## 2. Costo geométrico

Para arista a→b, resolución s, cambios dr/dc y alturas za/zb:

```text
d = hypot(dr,dc)*s
pendiente_arista = grados(atan(abs(zb-za)/d))
p = max(pendiente_arista, pendiente_local_a, pendiente_local_b)
q = max(0,(distancia_proximidad-clearance)/distancia_proximidad)
    o 0 si distancia_proximidad=0
coste_arista = d*(1 + w_p*(p/limite_pendiente)^2
                   + w_r*riesgo_medio + w_u*rugosidad_media + w_q*q)
```

Pendiente/ocupación/huella son restricciones duras; riesgo/rugosidad/proximidad son penalizaciones. En CTX no hay mediciones de esas capas adicionales: valores neutrales no prueban ausencia de peligro.

## 3. A* y modo rápido

`RiskAwareAStar.plan`: cola por f=g+h, con h distancia euclídea horizontal al destino. Costos de arista >= distancia y pesos no negativos sustentan esa heurística como cota inferior y consistente en el grafo estático. Las tolerancias y límite computacional impiden trasladar esa explicación a promesas absolutas de óptimo físico.

```text
validar extremos y snapshot
insertar inicio
mientras cola:
  extraer menor g+h y descartar entrada obsoleta
  si meta: reconstruir ruta
  si presupuesto de expansiones agotado: interrumpir
  relajar vecinos admisibles
si frontera agotada: no hay camino en ese grafo
```

`fast_calculate` calcula actual→objetivo y objetivo→base y suma actividad/consumos compartidos. Comprueba presupuesto DESPUÉS de seleccionar el candidato. Si cabe, confirma ese recorrido; si no, no demuestra que toda misión sea imposible. El código conserva `INFEASIBLE/FAST_ROUTE_NEEDS_RESOURCES` para candidato: consumidor debe leer método y motivo. Corregir esa ambigüedad pertenece a 6.6.

## 4. Búsqueda multirrecurso

`ResourceMissionPlanner.plan` es búsqueda de costo acumulado tipo Dijkstra sobre etiquetas. No es A* de recursos ni un MILP.

Estado de etiqueta: celda, objetivo visitado, vector de recursos, costo, padre y estado activo. Final: base terminal después de visitar objetivo; regreso directo usa fase ya satisfecha. Ciencia pendiente se cobra una vez; si comienza en objetivo, se cobra al inicio.

```text
crear etiqueta inicial y comprobar presupuesto inicial
mientras cola:
  extraer etiqueta activa de menor costo
  si base terminal y objetivo satisfecho: reconstruir misión
  para cada arista admisible:
    sumar movimiento y ciencia cuando corresponda
    rechazar si consumo > saldo-reserva (tolerancia 1e-9)
    rechazar si otra etiqueta del mismo estado la domina
    si no cabe otra etiqueta en el límite: interrumpir
    desactivar dominadas, insertar y conservar padre
si frontera agotada: no hay misión bajo este modelo
```

Dominancia: costo, tiempo, O2, agua, batería y nutrición <= los de otra etiqueta, con tolerancia 1e-9. Distancia es métrica, no presupuesto duro. El código también compara consumos internos no restringidos, lo que puede retener alternativas innecesarias.

```text
coste_incremental = minutos_mov*(1 + w_peligro*max(0,coste_arista/d-1))
                 + minutos_ciencia
                 + w_bateria*(Wh_mov + Wh_ciencia)
```

La poda presupone futuro dependiente de celda/fase, datos estáticos y costos/consumos aditivos no negativos. No demuestra optimalidad operacional bajo fatiga, clima, cambios durante búsqueda o fisiología no modelada. La referencia exhaustiva diminuta verifica casos concretos, no todos los mapas.

## 5. Comparación y decisiones

Tres políticas: balanced; minimum_time con pesos de peligro y batería cero; terrain_caution aumentando peso de peligro disponible. Selección entre SUCCESS por menor tiempo, batería y orden fijo. No comparar costos de pesos distintos. Agrupar secuencias iguales y conservar alternativas interrumpidas como desconocidas.

`evaluate_options` exige regreso SUCCESS para recomendar CONTINUE; continuidad inviable y regreso satisfactorio → RETURN. Interrupción o regreso sin confirmar → REVIEW. Es recomendación experimental, no orden de emergencia.

## 6. Complejidad y límites

Clearance puede requerir O(N·B) para N celdas/B obstáculos. A* tiene grafo de O(N) aristas, además del costo de barrido; O(N log N) es una orientación para gestión de cola, no todo el runtime geométrico. La búsqueda multirrecurso puede generar exponencialmente etiquetas; dominancia recorre fronteras locales y conserva padres/inactivas.

UI rápida: 5.000 expansiones POR TRAMO. Detallado: 5.000 etiquetas generadas por búsqueda en la configuración UI, incluidas inicial/inactivas. No son la misma métrica. Evitar extrapolar tiempos pequeños a todo Jezero.

No existen curvas continuas comprobadas, D* Lite, SLAM, planificador de múltiples objetivos ni ROS implementados. A* y Dijkstra son algoritmos conocidos: el aporte es su integración trazable con decisiones y recursos, no una invención atribuida a esos nombres.
