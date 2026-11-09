# Lectura de mapas y recursos para la presentación

## Productos distintos

| Producto | Aporta | No permite concluir |
|---|---|---|
| Imagen CTX orbital gris | Aspecto fotografiado y contexto | Altura, rocas detectadas o ruta segura |
| DEM CTX | Elevaciones numéricas | Detalle por debajo de su resolución informativa |
| Relieve sombreado | Sombras calculadas a partir de DEM | Fotografía o iluminación contemporánea |
| Elevación coloreada | Alturas según leyenda | Color natural o mineralogía |
| Contexto MOLA/HRSC | Ubicación y forma regional | Movilidad local certificada |

Zoom amplía representación, no crea datos. Imagen visual aproximada 6 m/píxel y DEM 20 m son productos diferentes. Una retícula histórica de 4 m remuestreada no aporta detalle CTX nativo de 4 m.

## Cobertura y coordenadas

Planificación regional: 2×2 km, 100×100 celdas de 20 m; mapa visual mayor. Origen 18.45° N planetocéntrico, 77.45° E; esfera R=3.396.190 m. E=R*cos(lat0)*(lon-lon0), N=R*(lat-lat0), ángulos en radianes. Filas al sur, columnas al este. El punto seleccionado se ajusta al centro utilizado y se muestra ese ajuste. No usar WGS84 terrestre.

Archivos: `data/jezero/` y `data/mission_planner_ctx_2km/`. Procedencia, transformación y hashes: [DATA_SOURCES](../DATA_SOURCES.md). No se releen alturas HiRISE para decidir rutas CTX. Obstáculos de UI son SIMULADOS, cuadrados de 20 m; no detecciones científicas. Ausencia de capa de riesgo no implica riesgo cero en Marte.

## Fórmulas de consumo

Fuente: Consumption.traveling/stationary y adaptación del perfil.

```text
g = max(0,ascenso_m)/distancia_horizontal_m
tiempo_min = distancia/velocidad * (1 + penalizacion_subida*g + penalizacion_rugosidad*r)
esfuerzo = 1 + penalizacion_esfuerzo*g
O2, agua, kcal = tiempo * tasa_movimiento_del_recurso * esfuerzo
bateria_Wh = tiempo*tasa_movimiento_bateria + ascenso_positivo*Wh_por_m
actividad = minutos_actividad*tasa_actividad por recurso
restante = saldo_al_solicitar - consumo_futuro
margen = restante - reserva_absoluta
```

Minutos, metros, m/min, Wh, L, kcal de demanda y O2 simulated_u. Las tasas de ciencia pueden diferir de movimiento. Rover no usa consumibles humanos. Excluido requiere motivo; no aplicable/excluido no se exporta como disponibilidad física cero.

Masa y altura son informativas. No existe fórmula que derive aquí el consumo EVA de antropometría. Kcal no significa ingerir esa energía durante una caminata breve. Agua no incluye refrigeración fisiológicamente validada. Tasas simuladas no están certificadas.

El factor conservador multiplica tasas declaradas, no es intervalo de confianza ni peor caso integral. «Preparar recursos» modifica el escenario: no prueba capacidad transportable ni compatibilidad con traje/equipo. El histórico no se descuenta dos veces y la reserva no se rebaja como porcentaje del saldo.

Fuentes y limitaciones ampliadas: [RESOURCE_MODELS](../RESOURCE_MODELS.md) y `PERSONALIZACION_ETAPA05.md` del prototipo.
