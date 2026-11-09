# Integración Python y puente local

Desde la raíz ejecutar `python examples/mission_request.py`. El ejemplo añade explícitamente `prototypes/mission_planner` al path y usa clases reales. No hay paquete pip instalado ni deserializador público general.

```python
from demo_stage03 import example_request
from mission_api import plan_mission
result = plan_mission(example_request('rover'))
print(result.to_json())
```

Ejecutar ese fragmento desde la carpeta del prototipo o preparar sys.path como el ejemplo. `MissionRequest` 3.0 incluye request_id, TerrainReference, LocalFrame, base/start/goal, actividad, AgentProfile y max_labels. Contratos anidados pueden fallar antes de llamar a la fachada. `plan_mission` devuelve SUCCESS, INFEASIBLE, SEARCH_LIMIT_REACHED o INVALID_INPUT; errores internos inesperados se propagan.

Para una misión en curso: `DecisionRequest` 5.0, `MissionState.capture`, `RateScenario`, procedencias y `plan_future`, `compare_alternatives`, `evaluate_options`. Ver `demo_stage05.py` y cierre 05 para solicitudes completas reales. Saldo es capacidad futura; el histórico no se descuenta otra vez. La reserva absoluta se conserva.

Un resultado contiene rutas, fases, eventos, consumos y saldos; recursos excluded/not_applicable usan null. Marco interno X este/Y sur; Jezero E este/N norte, latitud planetocéntrica y longitud este. No enviar coordenadas sin su marco ni aplicar WGS84 por defecto.

## HTTP existente, solo localhost

El código `make_server` expone GET `/api/catalog`, POST `/api/calculate`, `/api/inspect`, `/api/select`; no se inventan endpoints REST públicos. Cálculo recibe `{"configuration": config, "action":"compare"}` o `evaluate`; selección usa `point`, inspección `cell`. La configuración completa depende del catálogo/bridge; no confundirla con MissionRequest. Ver `test_stage06.py`, `test_stage06_maps.py` y pruebas de ExpandedBridge para ejemplos ejecutables.

HTTP 400 construcción inválida; 409 concurrencia; 500 fallo interno. Host/Origin local, límite de cuerpo 64 KiB. La envolvente contiene configuración, snapshot, perfiles, método y resultados. No usar como servicio de red multiusuario.

El consumidor debe leer método, estado Y reason_code. Rápido `INFEASIBLE/FAST_ROUTE_NEEDS_RESOURCES` solo rechaza candidato; corrección futura en 6.6. Nunca declarar seguridad de EVA o evacuación garantizada. No convertir «Preparar recursos» en autorización de hardware. ROS/backend/rover deben consumir una fachada, no copiar algoritmo ni enviar directamente comandos motor desde el navegador.
