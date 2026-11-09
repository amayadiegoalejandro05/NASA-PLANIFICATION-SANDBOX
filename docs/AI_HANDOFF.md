# Continuidad para otra IA

Este es el SANDBOX privado autorizado; nunca modificar ni publicar en el proyecto anterior/principal. Leer AGENTS, README, DECISIONS y MIGRATION_REPORT. Conservar estructura inicial; no iniciar fases futuras sin encargo.

Origen: working tree local NASA-Sandbox-etapa01, incluye cambios sin commit de etapas 1–6. La base Git de aquel origen no contiene todo ese trabajo; no reconstruir desde su HEAD. Manifiesto de hashes en docs/migration/source-manifest.json.

Funciona según evidencia de migración: ver resultados nuevos en docs/migration, no tomar los logs históricos como ejecución actual. Motor puro, NPZ NumPy, datos regionales JSON, UI localhost, Leaflet local y teselas remotas opcionales.

Conservar contratos 3.0/5.0 y envolventes 6.0/6.1. Modo rápido rechaza candidato por recursos, no prueba imposibilidad global. max_expansions A* y max_labels son diferentes. No esconder interrupciones. Masa/altura sin efecto; tasas simuladas; reservas absolutas; histórico no descontado otra vez. CORE sin ROS/UI/red.

Bootstrap no corrigió esas limitaciones. La auditoría local 6.5 está completada:
leer [NUMERICAL_MODEL_AUDIT](NUMERICAL_MODEL_AUDIT.md) y
[cierre 6.5](continuidad/ETAPA_06_5_CIERRE.md). Sus cambios siguen sin commit;
no confundirlos con la documentación de presentación heredada. Conserva
ecuaciones/tolerancias, rechaza dominio numérico inválido y ordena la suma rápida.
6.6 requiere encargo posterior: no iniciar automáticamente. Documentar pruebas
reales, skips, entorno, límites y fallos. No declarar seguridad EVA ni telemetría
real. Los cierres históricos tienen rutas y comandos antiguos; guía raíz actual
para ejecución en este repositorio.

Autoría/licencia de originales sigue sin resolver para redistribución pública; Leaflet y datos tienen avisos separados. No copiar entornos, credenciales o `.git` ajenos. No auto-merge.
