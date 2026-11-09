# MARS GOD'S EYE — Avances y análisis de las etapas 1–6

Fecha: 6 de noviembre de 2026, America/Bogota.

## 1. Entregable y estado actual

El entregable es un motor reutilizable de planificación de misiones para astronautas y rovers, acompañado de una interfaz local para demostrarlo y, posteriormente, de integración o preparación verificable para ROS 2.

Una misión considera desplazamiento, actividad científica y regreso, con restricciones de movilidad, recursos y reservas. El sistema explica los resultados y distingue una búsqueda interrumpida de una imposibilidad demostrada dentro del modelo.

Ya existe una aplicación navegable sobre cartografía real de Jezero. Permite marcar puntos, calcular recorridos, consultar recursos, comparar políticas en modo detallado y evaluar continuación o regreso desde una posición manual.

**Estado formal:** etapas 1–5 cerradas; etapa 6 funcional pero declarada INCOMPLETA respecto del alcance ampliado de su último cierre. Etapa 7 no iniciada.

Este resumen se basa en los cierres del proyecto, las verificaciones efectuadas anteriormente en este chat y la lectura del cierre consolidado de etapa 6. En esta revisión se consultaron también el código del modo rápido y su log de pruebas. No se volvió a ejecutar la suite completa ni a verificar el navegador en esta revisión documental.

## 2. Qué aportó cada etapa

| Etapa | Trabajo realizado | Resultado principal |
|---|---|---|
| 1 — Base confiable | Snapshot inmutable del terreno, coherencia de derivados, geometría conservadora de obstáculos/huella y excepción independiente para límite de búsqueda. | Las modificaciones externas dejan de mezclar terreno nuevo con cachés antiguas. |
| 2 — Perfiles y recursos | Perfiles astronauta/rover, capacidades, reservas, tasas de movimiento y actividad, recursos excluidos/no aplicables y procedencia. | El rover no recibe consumibles humanos en la entrada tipada. |
| 3 — Misión explicable | Solicitud/resultado 3.0, fases, eventos, acumulados, recursos restantes, coordenadas locales y JSON estricto. | Otro programa puede solicitar e inspeccionar una misión sin copiar algoritmos. |
| 4 — Jezero | Adaptador al prior CTX, checksum, transformaciones y prueba de misiones sobre un recorte real de 28×28 m. | Se conectó el motor con elevaciones orbitales trazables. |
| 5 — Decisiones y replanificación | Estado de misión, saldos, reservas absolutas, continuación/regreso, tres políticas y sensibilidad de tasas. | Se puede evaluar el futuro desde una posición intermedia sin descontar otra vez el histórico. |
| 6 — Interfaz cartográfica | Aplicación localhost, selección geográfica, capas reales, DEM regional, modos rápido/detallado, exportaciones y verificación de navegador documentada. | El usuario puede explorar un mapa y ejecutar el motor con sus entradas. |

Progresión de pruebas registrada: 21 al cierre de etapa 1; 30 en etapa 2; 39 en etapa 3; 53 en etapa 4; 71 en etapa 5; **101 Python sin skips en el último log de etapa 6**. Las cifras corresponden a suites de distinto alcance, no a un porcentaje de validación científica.

## 3. Componentes que existen

El prototipo está en `prototypes/mission_planner/`:

- `mars_route_planner.py`: terreno, geometría y A*.
- `mars_mission_resources.py`: consumos, presupuestos y búsqueda multietiqueta.
- `mission_api.py`: contratos 3.0 y contabilidad por fases/eventos.
- `mission_decisions.py`: contratos 5.0, políticas y evaluación de opciones futuras.
- `jezero_adapter.py`, `jezero_map.py`: datos y transformaciones.
- `prepare_ctx_2km.py`: preparación acotada del DEM regional.
- `fast_mission.py`: candidato geométrico y comprobación posterior de consumos.
- `mission_ui.py`, `regional_ui.py`, `expanded_ui.py`: puente local y adaptación de entradas.
- `web/`: interfaz cartográfica, Leaflet local e interfaz anterior conservada.
- `evidence/`: pruebas, escenarios, capturas y resultados de cada etapa.

No se desarrollaron firmware, control de motores, telemetría real, ROS 2 ni integración definitiva con Gods Eye View.

## 4. Cómo funciona ahora la aplicación

1. Elegir astronauta o rover.
2. Acercarse a la zona habilitada.
3. Marcar salida y destino.
4. Definir actividad y recursos.
5. Calcular y revisar recorrido y tabla «Necesitas / Tienes».
6. En una misión en curso, declarar posición manual y saldos para evaluar continuar o regresar.

Los cambios de configuración invalidan visualmente el resultado anterior. Las exportaciones conservan entradas y resultados del cálculo mostrado, con identidad de datos, métodos, unidades y revisiones.

El botón «Preparar recursos para este recorrido» aumenta disponibilidades simuladas conforme al consumo calculado más la reserva y verifica de nuevo. No proporciona equipo real ni demuestra que esas capacidades puedan transportarse o pertenezcan a un traje existente. Es una herramienta de exploración de escenarios.

La ruta es poligonal, entre centros de celdas. Los giros de retícula son parte de la solución actual; el aspecto redondeado de una línea no constituye una curva continua validada.

## 5. Los dos algoritmos que debe distinguir el usuario

### Modo rápido: A* geométrico

Busca un candidato de ida y regreso utilizando costo geométrico ponderado por terreno. Después contabiliza movimiento y actividad con las fórmulas compartidas y comprueba recursos/reservas.

Tiene un límite de 5.000 expansiones por tramo. No compara tres políticas ni busca alternativas por presupuesto.

Si el candidato cumple presupuesto, existe una misión admisible bajo ese modelo. Si excede presupuesto, **solo se ha rechazado ese candidato**: podría existir otro recorrido factible que el método rápido no examinó.

Observación del código: ese rechazo usa `INFEASIBLE` con motivo `FAST_ROUTE_NEEDS_RESOURCES`, dentro de la envolvente rápida 6.1. Por tanto, los consumidores deben interpretar método y motivo, no convertir ese estado aislado en «no existe ninguna misión». Conviene resolver esta ambigüedad de contrato antes de exponer resultados a ROS u otros consumidores.

### Modo detallado: búsqueda multirrecurso

Conserva alternativas no dominadas por celda/fase y considera consumos durante la búsqueda. Puede encontrar opciones que un único candidato geométrico no representa. Su crecimiento computacional es mayor.

Su límite de 5.000 corresponde a etiquetas generadas, incluidas inicial e inactivas; **no equivale a las expansiones de A***.

Las políticas son equilibrada, menor tiempo y mayor penalización de terreno disponible. La recomendación entre resultados satisfactorios prioriza tiempo y después batería. No certifica la ruta más segura ni compara directamente costos obtenidos con pesos diferentes.

## 6. Qué datos y mapas se utilizan

La cobertura actual de cálculo es **2×2 km**, representada por **100×100 celdas de 20 m**. La vista cartográfica puede explorar un territorio mayor, pero el motor no tiene habilitado todo el cráter.

Los datos regionales están en `data/mission_planner_ctx_2km/`. Proceden de una ventana CTX identificada y reproyectada por promedio a 20 m; conservan metadatos y hashes. Los datos anteriores y los del piloto permanecen separados.

| Vista | Qué representa | Qué no demuestra |
|---|---|---|
| Imagen orbital gris CTX | Apariencia observada desde órbita; cobertura parcial. | Elevación, consumo o ausencia de obstáculos. |
| Contexto sombreado MOLA/HRSC | Contexto topográfico regional. | Detalle suficiente para desplazamiento local. |
| Relieve sombreado local | Iluminación calculada sobre el DEM CTX de 20 m. | Fotografía o iluminación real del momento. |
| Elevación local coloreada | Alturas del DEM con una escala de colores. | Color natural ni composición del suelo. |

La imagen CTX visual tiene aproximadamente 6 m/píxel según el cierre, mientras el DEM de cálculo tiene 20 m. Son productos distintos: una imagen más nítida no aumenta la resolución del modelo de elevación.

Viking no se integró debido a metadatos de acceso/uso contradictorios. No hay capa orbital en color verificada. No se aplicó un filtro rojo para fingir color natural.

Marcos: esfera de Marte, latitud planetocéntrica y longitud este; proyección local equirectangular. El mapa sitúa norte arriba. En el motor las filas crecen hacia el sur. Las conversiones deben conservar esa diferencia.

## 7. Personalización y realismo

Las tasas, capacidades, límites de movilidad y objetivos de ejemplo siguen siendo simulados. Masa corporal y altura son metadatos informativos: no modifican los consumos actuales. No se incorporó una fórmula antropométrica EVA sin respaldo apropiado.

Se distinguen recursos modelados, excluidos explícitamente y no aplicables. El rover no consume oxígeno, agua o nutrición humana. O2 permanece en unidades simuladas y kcal representa demanda parametrizada.

No se modelan de forma validada fatiga, ajuste/presión del traje, carga transportada, fisiología, CO2, autonomía térmica, meteorología, radiación ni suelo granular. El DEM CTX no resuelve rocas o peligros de escala inferior a su información disponible.

Los obstáculos añadidos en pantalla son perturbaciones simuladas de celdas de 20×20 m, no detecciones científicas.

## 8. Análisis del cierre de etapa 6

### Avance confirmado por la documentación y evidencia consultada

El problema inicial de una interfaz limitada a texto/retícula fue abordado: ahora existe navegación cartográfica, selección de puntos y cálculo conectado al motor. El cierre documenta verificación real en navegador, descargas y pruebas de error; el log consultado registra 101 pruebas Python aprobadas en 21,295 s.

Un ejemplo documentado de aproximadamente 1.233 m consumió 316,137 min y 642,127 Wh con su perfil simulado. No es una predicción para un astronauta real: refleja, entre otras entradas, la velocidad configurada de ese ejemplo.

Las mediciones del modo rápido del orden de medio segundo son observaciones de casos concretos, no una garantía de tiempo real.

### Pendientes expresos del cierre

- Planificación de todo Jezero.
- Capa orbital en color verificada.
- Curvas continuas validadas geométricamente.
- Repetir el flujo rápido final en ancho reducido.

Los tres primeros son ampliaciones que deben evaluarse según el entregable: color no mejora por sí solo el cálculo, curvas continuas añaden un problema de seguimiento/validación y cubrir todo el cráter requiere datos y escalabilidad. No conviene convertirlos automáticamente en requisitos indispensables para integrar el motor si se acuerda un demostrador regional de rutas poligonales.

**No se cambia aquí el alcance ni se cierra la etapa.** El documento vigente la declara INCOMPLETA. Corresponde resolver esos pendientes o acordar explícitamente una frontera de aceptación regional antes de pasar a etapa 7.

### Aspectos relevantes para integración futura

1. Distinguir resultado de candidato rápido de conclusión de búsqueda multirrecurso.
2. No convertir «Preparar recursos» en autorización operacional ni capacidad física certificada.
3. Mantener cobertura, resolución y método visibles en cada solicitud/resultado.
4. Preservar las diferencias entre expansiones, etiquetas e interrupciones.
5. Conservar el CORE separado de interfaz, servidor y ROS.

## 9. Qué conviene aprender para utilizarlo

- Imagen orbital frente a DEM: una muestra apariencia y el otro elevación.
- Resolución frente a zoom: ampliar la pantalla no crea información nueva.
- Relieve sombreado frente a elevación: sombras sintéticas y alturas no son el mismo producto.
- Coordenadas planetarias, E/N locales y fila/columna: representan el mismo lugar con convenciones diferentes.
- A* frente a búsqueda multirrecurso: candidato geométrico y restricciones durante la búsqueda son procesos distintos.
- Reserva frente a saldo: el saldo es lo disponible; la reserva debe permanecer al terminar.
- Factibilidad frente a preferencia: cumplir restricciones y elegir entre candidatos son decisiones distintas.
- Interrupción frente a inviabilidad: detener el cálculo no demuestra ausencia de solución.

## 10. Arranque y siguiente etapa

Desde el checkout, en PowerShell:

```powershell
& .\.venv-stage04\Scripts\python.exe prototypes/mission_planner/mission_ui.py
```

Abrir `http://127.0.0.1:8766/`. Detener con Ctrl+C en la consola que inició el servidor. No se ha iniciado ni detenido ninguna instancia para generar este resumen.

La etapa 7 sigue pendiente: comunicación ROS 2 o preparación verificable mediante un adaptador separado, contratos y pruebas. Una preparación documentada y una comunicación ejecutada deben declararse como resultados distintos.

El trabajo continúa en la rama local documentada, sin commits, push ni PR según los cierres. La autoría/licencia de los originales conserva su pendiente antes de distribuir. Los cierres de cada etapa y las evidencias son la referencia detallada; este archivo es su síntesis y análisis.
