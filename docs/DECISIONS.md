# Registro de decisiones

| ID | Decisión | Motivo/consecuencia | Estado |
|---|---|---|---|
| B01 | Clonar SANDBOX, rama bootstrap/stage06-baseline, conservar LICENSE inicial | Repo no vacío: commit 471019a5377f2803612fcbac3ba5774310ec9d08 solo licencia; no reemplazar main | Aplicada |
| B02 | Migrar working tree local con manifiesto, sin refactor | Trabajo sin commit de seis etapas; hashes preservan trazabilidad y origen de lectura | Aplicada |
| B03 | Incluir dos recortes compactos con metadatos | Datos necesarios pequeños; registros de producto USGS declaran dominio público | Aplicada |
| B04 | Entorno nuevo .venv con NumPy 2.2.6; Rasterio solo opcional de preparación | Evitar copiar entornos y dependencias complejas innecesarias | Aplicada |
| B05 | Mantener evidencia y cierres históricos, añadir informes nuevos | No sustituir historia por resultados de bootstrap ni falsificar verificaciones | Aplicada |
| B06 | No corregir semántica rápida en migración | Preservar comportamiento, registrar discrepancia candidata/global para 6.6 | Pendiente de mejora |
| B07 | No asumir licencia raíz sobre originales sin declaración | Conservar advertencia y no inventar autoría; repo privado autorizado | Pendiente antes de publicación pública |
| B08 | Preparación ROS separada del CORE, sin instalar ROS | Etapa posterior explícita | Propuesta |

No hubo cambios de ecuaciones, pesos, heurísticas o geometría en bootstrap. Los requisitos futuros del roadmap no autorizan su implementación automática.
