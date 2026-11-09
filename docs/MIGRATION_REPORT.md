# Migración controlada — baseline stage06

Fecha: 2026-11-08, America/Bogota. Alcance: preservar código, datos compactos y trazabilidad; documentar y reproducir. No se implementaron etapas 6.5–6.9 ni ROS.

## Estado inicial

Destino privado autorizado: amayadiegoalejandro05/NASA-PLANIFICATION-SANDBOX. No estaba vacío: main contenía LICENSE Apache-2.0 en commit `471019a5377f2803612fcbac3ba5774310ec9d08`. Se clonó y creó `bootstrap/stage06-baseline`, sin alterar main.

Origen: working tree local NASA-Sandbox-etapa01. Se eligió frente al ZIP porque existe implementación inspeccionable con datos/evidencias; no se extrajo el ZIP ni se reconstruyó desde el commit base, que no contiene todo el trabajo sin commit. Origen fue tratado solo como lectura.

## Incorporación y diferencias

185 archivos, 15.222.048 bytes, copiados con hashes idénticos. Manifiesto por archivo en `migration/source-manifest.json`. Incluye prototipo completo, originales, pruebas, web/Leaflet con licencia, 117 evidencias históricas, cierres y dos recortes compactos.

No se copiaron .git, entornos virtuales, cachés, credenciales, ZIP, pilotos/Gazebo ni backend general. Búsqueda limitada de patrones de tokens GitHub y claves privadas no encontró coincidencias en archivos incluidos; no equivale a una auditoría universal de secretos.

Los 185 archivos migrados NO se editaron. README antiguo se conserva como antecedente con sus rutas absolutas, advertencias y resultados históricos; nueva documentación raíz es la guía actual. No cambian fórmulas, geometría, rutas, interfaces o resultados esperados.

Archivos añadidos: README, AGENTS, .gitignore, requirements.txt, THIRD_PARTY_NOTICES; guías ARCHITECTURE, INTEGRATION_GUIDE, RESOURCE_MODELS, DATA_SOURCES, REPRODUCIBILITY, DEVELOPMENT_ROADMAP, AI_HANDOFF, DECISIONS; ejemplo Python, smoke HTTP y verificación de integridad. `migrate_baseline.py` registra la copia inicial y no debe repetirse sobre el destino ocupado.

## Resultados nuevos

| Verificación | Resultado real |
|---|---|
| Clon privado | Éxito con acceso de red autorizado tras fallo DNS restringido |
| Entorno nuevo | Python 3.11.9, NumPy 2.2.6; sin copia de entornos |
| Suite restringida inicial | 101 ejecutadas; 1 fallo/5 errores de pruebas HTTP por sockets; no se ocultaron |
| Suite autorizada | **101/101, 15.892 s, sin skips** |
| JavaScript | Ambas suites PASS con Node v24.22.1 |
| Ejemplo público Python | SUCCESS 3.0, rover sintético, 4 m/6 min/18 Wh |
| Integridad | 185 origen y 185 destino coinciden con manifiesto; changed_source=[], changed_target=[] |
| HTTP instancia migrada | 7 recursos estáticos/PNG + catálogo 200; cálculo rover SUCCESS, 80 m |
| Navegador | Aplicación migrada cargada y cálculo por botón astronauta completado; tabla y éxito observados |

El primer intento de navegador/HTTP a la instancia aislada agotó conexión. Se detuvo esa instancia propia y se inició servidor autorizado en 8767; HTTP y navegador funcionaron. No se cambió seguridad del sistema ni se detuvo el proyecto anterior.

Entorno reportado: Windows build 26200, Python 3.11.9; `platform.platform()` registra Windows-10-10.0.26200-SP0. Linux, otros Python y adquisición GDAL desde cero no ejecutados en bootstrap. La guía distingue propuestas de comandos comprobados.

## Riesgos y pendientes preservados

- Cierre ampliado de etapa 6 sigue INCOMPLETO: todo Jezero/color/curvas y última revisión estrecha pendientes; no se redefinen como terminados por migrar.
- `INFEASIBLE/FAST_ROUTE_NEEDS_RESOURCES` solo rechaza un candidato rápido. Corregir contrato con pruebas en 6.6, no durante bootstrap.
- Tasas simuladas sin certificación; preparar recursos ajusta escenario, no equipo físico.
- Licencia/autoría de originales pendiente antes de distribución pública; LICENSE del destino no la resuelve. Leaflet y productos científicos tienen avisos específicos.
- Evidencia histórica contiene rutas locales y no sustituye mediciones nuevas. No publicar credenciales ni convertir este servidor en servicio de red.
- No se repitió inspección visual exhaustiva, mobile, descargas UI ni acceso a teselas remotas en esta migración. El usuario puede abrir localhost; se conservan pruebas históricas por separado.

## Aceptación

Código, datos necesarios, pruebas y evidencia preservados; origen sin cambios de archivos migrados; instalación aislada, pruebas y arranque comprobados; documentación autocontenida y roadmap añadido. Los endpoints principales y cálculo real se verificaron por HTTP y navegador. Bootstrap no equivale a cerrar alcance científico/visual pendiente de etapa 6.

Primera intervención propuesta 6.5: verificar unidades y cuentas independientes por fase/recurso y coherencia de reservas, sin inventar calibración. Ver DEVELOPMENT_ROADMAP.

La publicación de la rama/PR y la comprobación de checkout limpio se registrarán en un anexo antes de finalizar. Nunca auto-merge ni operaciones remotas en el repositorio anterior/principal.
