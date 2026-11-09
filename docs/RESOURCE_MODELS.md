# Modelos de recursos implementados

Fuente: `Consumption.traveling`, `stationary`, `AgentProfile._engine_inputs`, `effective_future_profile`; no se cambian en migración.

Para distancia horizontal d en m, ascenso dz en m, velocidad v en m/min y rugosidad r:

```text
g = max(0,dz)/d
t = d/v * (1 + uphill_speed_penalty*g + roughness_speed_penalty*r)
effort = 1 + uphill_effort_penalty*g
O2 = t * oxygen_movement_rate * effort
agua = t * water_movement_rate * effort
kcal = t * nutrition_movement_rate * effort
batería = t * battery_movement_rate + max(0,dz)*climb_battery_wh_per_m
actividad: t_actividad * tasa_actividad de cada recurso; distancia=0
```

Aristas válidas tienen d>0. Unidades: min, m, Wh, L, kcal de demanda y O2 `simulated_u`. No se convierten unidades ficticias de O2 a masa, volumen o presión. kcal no equivale a obligación de ingestión durante la caminata.

`ResourceAllocation` valida capacidad/reserva/tasas no negativas y finitas; reserva<=capacidad. Tiempo tasa=1. Astronauta requiere recursos humanos o exclusión con motivo; rover rechaza esos recursos. Tiempo y batería no admiten exclusión. `Usage` genérico interno no reemplaza el estado tipado al interpretar ceros.

Movimiento y actividad tienen tasas diferentes. Actividad pendiente se cobra una vez; completada no se repite. Saldos reemplazan capacidades disponibles para el futuro, sin descontar histórico otra vez. `remaining=saldo-consumo_futuro`; `margin=remaining-reserva`. Tolerancia heredada 1e-9.

Escenario nominal factores 1; conservador >=1 en tasas, tiempo 1. No es intervalo estadístico ni peor caso integral: no modifica automáticamente velocidad ni energía Wh/m de ascenso.

Pesos del costo y tasas físicas son conceptos distintos. A* pondera geometría; detallado combina tiempo con penalización de terreno y batería. No afirmar óptimo físico/operacional global.

Todos los ejemplos son simulados. Declarar procedencia measured/estimated no autentica una medición. Masa/altura son informativos sin efecto; edad/sexo no se recopilan. Faltan calibración, fatiga, carga/traje, térmica, CO2, radiación y meteorología. Ver PERSONALIZACION_ETAPA05.md y roadmap 6.5.

## Auditoría numérica 6.5

[Inventario, cuentas independientes, dominio y evidencia](NUMERICAL_MODEL_AUDIT.md).
Las ecuaciones y tolerancias anteriores se conservan. Los números booleanos,
no finitos y fuera del dominio se rechazan; los desbordamientos derivados se
identifican como `NUMERIC_DOMAIN_EXCEEDED` en las fachadas 3.0/5.0, nunca como
inviabilidad física. El modo rápido suma en el orden de los eventos.

El presupuesto `nutrition_kcal` limita demanda energética simulada, no cantidad
de alimento que deba ingerirse durante el trayecto. No modela ingestión,
absorción, nutrición diaria ni reservas fisiológicas. No es prescripción médica.
O2 conserva su unidad ficticia; aprobar las cuentas no calibra el modelo.
