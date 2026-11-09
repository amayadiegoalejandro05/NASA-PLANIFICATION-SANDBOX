# MARS GODS EYE — Mission Planning Engine

SANDBOX privado e independiente para preservar y evaluar el planificador experimental de misiones de astronautas y rovers. No controla motores ni certifica seguridad humana/EVA. No requiere ROS 2.

## Estado

Migración de la implementación acumulada de etapas 1–6, sin rediseñar algoritmos. El origen se conserva sin modificaciones. El repositorio destino ya tenía un commit con LICENSE Apache-2.0; se conserva. Rama de migración: `bootstrap/stage06-baseline`.

La aplicación muestra cartografía marciana y calcula dentro de **2×2 km**, 100×100 celdas de 20 m. No cubre todo Jezero. Consumos y perfiles son simulados. Masa/altura son informativos. Etapas 1–5 cerradas; cierre histórico de etapa 6 ampliada sigue incompleto. No se implementan mejoras 6.5–6.9 ni ROS.

## Windows / PowerShell

Con Python 3.11 instalado, desde este checkout:

```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -v
& .\.venv\Scripts\python.exe examples/mission_request.py
& .\.venv\Scripts\python.exe prototypes/mission_planner/mission_ui.py --port 8767
```

El lanzador `py` puede no detectar Python. En ese caso sustituir únicamente la primera línea por `& 'RUTA\python.exe' -m venv .venv`. No hace falta activar el entorno ni cambiar la política de ejecución de PowerShell. Consultar [reproducción](docs/REPRODUCIBILITY.md) para los comandos realmente ejecutados en este equipo.

Abrir [interfaz local](http://127.0.0.1:8767/). Parar con Ctrl+C en la consola del servidor. Se utiliza 8767 para no confundirla con la instancia previa en 8766. Las teselas orbitales requieren internet; motor, elevaciones y relieve local no. Seleccionar «Solo datos locales» para evitar teselas remotas.

Los recortes científicos compactos están incluidos con sus hashes: no hay descarga automática al calcular. No ejecutar el preparador si los datos existen. Ver [fuentes](docs/DATA_SOURCES.md).

## Uso y límites

Marcar salida/destino dentro del polígono, elegir agente, actividad y recursos. En modo rápido, A* propone un candidato y se comprueba su consumo después. `FAST_ROUTE_NEEDS_RESOURCES` rechaza ese candidato, **no demuestra inviabilidad de toda misión**. El modo detallado considera recursos durante la búsqueda. Preparar recursos modifica presupuestos simulados, no capacidades físicas certificadas. Una interrupción deja factibilidad desconocida.

## Organización

```text
prototypes/mission_planner/  motor, adaptadores, interfaz, tests y originales
data/jezero/                recorte histórico compacto CTX/HiRISE
data/mission_planner_ctx_2km/ CTX regional preparado y metadatos
docs/continuidad/           cierres históricos, sin reinterpretarlos como tareas
docs/migration/             manifiesto de origen y resultados de esta migración
examples/                   ejemplo Python ejecutable
```

Guías: [arquitectura](docs/ARCHITECTURE.md), [integración](docs/INTEGRATION_GUIDE.md), [recursos](docs/RESOURCE_MODELS.md), [reproducción](docs/REPRODUCIBILITY.md), [roadmap](docs/DEVELOPMENT_ROADMAP.md), [handoff IA](docs/AI_HANDOFF.md), [decisiones](docs/DECISIONS.md).

## Licencias y procedencia

La licencia raíz preexistente no prueba la autoría ni relicencia automáticamente los originales importados; su situación se conserva documentada en [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Leaflet mantiene BSD-2-Clause. Los productos USGS concretos se identifican en DATA_SOURCES. No se incorporan el ZIP, entornos, `.git` del origen, credenciales o paquetes científicos globales.

Los resultados de la migración están en [MIGRATION_REPORT.md](docs/MIGRATION_REPORT.md). Los cierres y logs históricos no sustituyen esas ejecuciones nuevas.
