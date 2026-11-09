# Evidencias y afirmaciones permitidas

## Qué se revisó ahora

Lectura del código/contratos, cierres, documentación y logs del baseline ab25737. No se volvieron a ejecutar tests ni navegador para generar este paquete. No se cambiaron expectativas o resultados históricos.

| Evidencia conservada | Resultado registrado | Alcance |
|---|---|---|
| docs/migration/python-tests-authorized.log | 101/101, 15,892 s, sin skips | Python/NumPy y HTTP localhost autorizados |
| docs/migration/clean-checkout-tests.log | 101/101, 17,568 s | Checkout limpio, mismo intérprete preparado |
| docs/migration/synthetic-tests.log | 55/55, 1,922 s | CORE sin NumPy |
| docs/migration/javascript-legacy.log y javascript-map.log | PASS ambas | Doble DOM, no equivalen a E2E |
| docs/migration/http-smoke-authorized.log | SUCCESS rover, 80 m; estáticos/PNG 200 | Instancia migrada anterior en 8767 |
| source-manifest/integrity de migración | 185 archivos idénticos | Preservación, no validación científica |

Python comprobado 3.11.9, NumPy 2.2.6, Node v24.22.1; Windows build 26200. No se probó Linux. Los fallos restringidos DNS/sockets se conservan como historia, no se borran. Las capturas en evidence/stage06_* son históricas, no capturas de hoy.

## Ejemplos documentados, no mediciones físicas

- Etapa 3 sintética: 4 m, 6 min, 18 Wh; cuenta independiente por fases.
- Etapa 4 CTX pequeño: 22,627 m, 7,877 min y 19,975 Wh con perfil simulado; ida/ciencia/regreso.
- Etapa 5: continuación CTX desde posición intermedia, alternativas y regreso; 17 casos/39 solicitudes en evaluación registrada.
- Etapa 6 regional: candidato de aproximadamente 1.233 m y 316,137 min/642,127 Wh después de preparar presupuesto simulado. No mezclarlo con otra ejecución de aproximadamente 1.306 m del cierre.

Los tiempos son resultados del perfil escogido, no tiempos humanos observados. No comparar cifras entre escenarios con escalas/perfiles distintos como si fuera mejora del algoritmo.

## Qué podemos afirmar

| Afirmación | Tratamiento |
|---|---|
| Usa elevaciones orbitales reales CTX identificadas | Sí, con recorte, metadatos y hashes |
| Comprueba ida, ciencia, retorno y reservas | Sí dentro del modelo y método indicado |
| Tiene 101 tests registrados satisfactorios | Sí, con entorno/fecha y alcance |
| Funciona sobre todo Jezero | No; área de cálculo 2 km |
| Encuentra siempre la ruta más segura | No; faltan peligros/calibración y seguridad física |
| Un candidato rápido sin recursos prueba inviabilidad global | No; existe ambigüedad de estado pendiente 6.6 |
| Usa peso/altura para calcular fisiología | No; solo metadatos |
| Opera un rover o recibe telemetría | No; posición manual y simulación |
| ROS listo y comunicación validada | No; etapa futura |
| Ahorra X% o mejora supervivencia | No hay estudio que lo sustente |

## Riesgos antes de presentar

Actualizar una ejecución identificada y captura de la versión que efectivamente se mostrará. Resolver acceso del jurado al repositorio privado sin divulgar secretos. Revisar licencia/autoría de originales; declarar trabajo previo y asistencia IA. No llamar «óptimo multirrecurso» al modo rápido. Preparar escenario de fallo y comportamiento sin teselas remotas.

Las pruebas validan propiedades de software, no consumo humano o movilidad de un vehículo real en Marte. Los oráculos diminutos son referencias locales de corrección y no una demostración global operacional.
