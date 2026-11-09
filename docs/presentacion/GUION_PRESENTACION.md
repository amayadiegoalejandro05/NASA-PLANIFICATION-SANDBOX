# Guion de demostración y resumen de proyecto

Propuesta editorial, no formato de entrega confirmado de 2026. No se generó un video ni una presentación de diapositivas; este archivo sirve de base.

## Mensaje principal

«Planificar una misión no es dibujar el camino más corto: es comprobar si podemos desplazarnos, realizar ciencia y regresar conservando las reservas configuradas».

## Resumen en español

MARS GOD'S EYE — Mission Planning Engine es un prototipo experimental que combina elevaciones orbitales CTX de Jezero con perfiles diferenciados de astronauta y rover. Permite seleccionar puntos, planificar ida, actividad y regreso, explorar presupuestos y evaluar continuidad desde una posición intermedia. Sus resultados incluyen rutas, fases, consumos, reservas y explicaciones. El cálculo disponible cubre 2×2 km y distingue un candidato geométrico rápido de una búsqueda multirrecurso detallada. Los parámetros de consumo son simulados; el sistema no certifica seguridad EVA ni controla hardware.

## English abstract — draft for review

MARS GOD'S EYE Mission Planning Engine is an experimental mission-planning prototype that connects orbital elevation data from Jezero with configurable astronaut and rover profiles. It evaluates travel, a science activity and return while accounting for resource reserves. A local map interface exposes routes, resource estimates and explanations, including interrupted searches. The current planning area is two kilometres square. Consumption parameters are simulated; this prototype is neither an operational EVA safety system nor a rover controller.

## Estructura propuesta de siete láminas

1. Problema, usuario y pregunta de misión.
2. Datos reales: mapa, área de cálculo, resolución y procedencia.
3. Método: A* rápido y búsqueda multirrecurso; restricciones separadas de preferencias.
4. Demo: seleccionar puntos y actividad, calcular y explicar saldo/reserva.
5. Fallo: candidato sin presupuesto o regreso; enseñar diferencia con interrupción.
6. Evidencia: pruebas, reproducción y límites reales.
7. Contribución, atribuciones, trabajo previo y próximos pasos.

Es una estructura compacta inspirada en un antecedente de formato 2025; ajustar a la guía vigente. Una demo interna extensa no equivale al recurso de entrega permitido.

## Protocolo para ensayo

Desde la raíz del checkout, con entorno preparado: `.venv/Scripts/python.exe prototypes/mission_planner/mission_ui.py --port 8767`. Abrir localhost:8767. Verificar que sea esta instancia y no la del proyecto anterior. Consultar REPRODUCIBILITY para instalar y detener.

Usar puntos predeterminados y perfil identificado; registrar captura, configuración, resultado JSON y commit. Comenzar con datos locales si se prevé red inestable. Mostrar la cobertura real; no fingir que toda la imagen del cráter es planificable. Antes de afirmar un resultado nuevo, ejecutarlo y conservarlo.

En misión con déficit, explicar que preparar recursos modifica el escenario simulado y vuelve a comprobarlo; no mostrarlo como solucionar una emergencia real. En límite de cálculo decir «factibilidad desconocida». No seleccionar después un resultado favorable sin explicar qué entradas cambiaron.

## Preguntas esperables

- ¿Qué viene de NASA/USGS? Elevaciones y productos identificados; consumos no.
- ¿Qué algoritmo inventaron? No se inventaron A* o Dijkstra; se integran con modelos, contabilidad, decisiones y trazabilidad.
- ¿La ruta es segura? Es admisible bajo restricciones y datos declarados; faltan peligros/calibración.
- ¿Por qué la ida y vuelta tardan diferente? El ascenso modifica el tiempo y energía del modelo.
- ¿Qué ocurre sin recursos? Detallado y candidato rápido tienen alcances distintos; mostrar método/motivo.
- ¿Sirve peso/altura? Solo información en la implementación actual.
- ¿Qué se ha validado? Regresiones y ejemplos pequeños/CTX, no operaciones físicas.
- ¿Se usa ROS? No; integración posterior.
- ¿Qué hizo cada integrante y la IA? Completar atribuciones reales antes de publicar; no inventar responsabilidades.
