# Instrucciones — NASA-PLANIFICATION-SANDBOX

- Trabajar solo en este repositorio privado. El proyecto local anterior y cualquier repositorio principal son fuentes de lectura, nunca destinos de cambios, push o PR.
- Leer README, docs/AI_HANDOFF.md, docs/DECISIONS.md y el cierre pertinente antes de cambiar comportamiento.
- Conservar estructura funcional `prototypes/mission_planner` durante bootstrap. Los imports son módulos de esa carpeta; discovery usa `-s prototypes/mission_planner`.
- CORE: `mars_route_planner`, `mars_mission_resources`, `mission_api`, `mission_decisions`. No introducir ROS, red o UI en ellos. No duplicar fórmulas en JavaScript.
- No cambiar geometría, dominancia, tolerancias, reservas ni significado de contratos 3.0/5.0/6.1 sin justificación y regresión. Documentar candidato rápido frente a inviabilidad global.
- Snapshot inmutable; un cambio de terreno requiere nueva revisión. No modificar datos reales para pruebas: usar fixtures temporales.
- Perfiles/tasas simulados no son calibraciones; masa/altura no afectan cálculo actual. Rover no usa consumibles humanos. No convertir O2 simulado a unidades físicas.
- No leer alturas HiRISE como conocimiento CTX del planificador. La máscara conjunta histórica no es una observación pública.
- Pruebas obligatorias: `.venv/Scripts/python.exe -m unittest discover -s prototypes/mission_planner -v`; ambos `test_stage06*_frontend.cjs` con Node según README/REPRODUCIBILITY. Ejecutar checks del puente para cambios UI. Sin skips para afirmar integración real.
- No instalar ROS ni implementar fases futuras por leer su roadmap. No ejecutar preparación de datos sobre una adquisición existente.
- No copiar `.git`, entornos, cachés o secretos. Conservar licencias, hashes y fuentes. No publicar datos grandes sin verificar procedencia/licencia.
- El servidor es localhost. Probar en puerto distinto al de la app anterior. No detener procesos ajenos.
- Los cierres históricos contienen rutas absolutas y comandos antiguos; la guía actual del SANDBOX tiene prioridad para ejecutar aquí.
- Bootstrap permite commit/push y PR solo en `amayadiegoalejandro05/NASA-PLANIFICATION-SANDBOX`, rama de trabajo. Nunca auto-merge.
