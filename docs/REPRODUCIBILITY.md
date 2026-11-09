# Reproducción desde cero

## Entorno realmente utilizado

Fecha 2026-11-08. Python 3.11.9 amd64; NumPy 2.2.6 instalado en `.venv` NUEVO, sin copiar site-packages del proyecto anterior. Node v24.22.1 para dos suites JS. `platform.platform()` devolvió `Windows-10-10.0.26200-SP0` (identificador de plataforma/build, no se infiere edición comercial). Git del runtime local. No se probó Linux ni otra versión Python.

Compatible por sintaxis con Python 3.10+, pero runtime y wheels comprobados solo con 3.11.9. No hay ejecución ROS.

## Obtener el código

```powershell
git clone --branch bootstrap/stage06-baseline https://github.com/amayadiegoalejandro05/NASA-PLANIFICATION-SANDBOX.git
cd NASA-PLANIFICATION-SANDBOX
```

Es privado: requiere acceso autorizado GitHub. No guardar tokens en README, URLs, scripts o .env versionado. El repositorio ya tenía LICENSE; no fue inicializado desde cero ni se reemplazó main.

## Instalación Windows

Comandos ejecutados en esta máquina desde el nuevo SANDBOX:

```powershell
& 'C:\Users\laura\AppData\Local\Programs\Python\Python311\python.exe' -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r prototypes/mission_planner/requirements-jezero.txt
& .\.venv\Scripts\python.exe -m unittest discover -s prototypes/mission_planner -v
& .\.venv\Scripts\python.exe examples/mission_request.py
& .\.venv\Scripts\python.exe prototypes/mission_planner/mission_ui.py --port 8767
```

`requirements.txt` raíz fija el mismo NumPy. Instalación falló inicialmente por DNS restringido; al autorizar red descargó NumPy sin modificar el Python global. Las pruebas HTTP fallaron inicialmente con WinError 10013; repetir con sockets localhost autorizados dio **101/101, 15.892 s, sin skips**. No se cambiaron tests. Logs completos y fallos iniciales se conservan en docs/migration.

En otro PC sustituir solo la ruta de Python por la instalación propia, o `py -3.11`. No es necesario ejecutar Activate.ps1.

Con Node disponible, desde raíz:

```powershell
node prototypes/mission_planner/test_stage06_frontend.cjs
node prototypes/mission_planner/test_stage06_map_frontend.cjs
```

Ambas suites pasaron con Node v24.22.1. Son tests de presentación con doble DOM, no prueba de navegador. En esta máquina se usó el node.exe del runtime Codex; Node no es necesario para ejecutar la app.

## Datos

Los dos recortes compactos están versionados y listos; ver DATA_SOURCES. No hay descarga científica al arrancar o calcular. Las integraciones reales requieren esos archivos y NumPy; no aceptar skips como prueba de funcionamiento completo.

La preparación desde fuente (`requirements-maps-prep.txt` y `prepare_ctx_2km.py`) se documenta en DATA_SOURCES, pero no se reejecutó en esta migración porque ya existe la adquisición y el preparador rechaza sobrescritura. No instalar Rasterio para el uso cotidiano.

## Pruebas sintéticas sin descarga

Con Python 3.11 instalado, sin pip ni NumPy, desde prototypes/mission_planner:

```powershell
python -m unittest test_mars_route_planner test_mars_mission_resources test_stage01 test_stage02 test_stage03 test_stage05 -v
```

Es una selección de 55 pruebas del CORE y escenarios sintéticos, independiente de las integraciones reales. Ver registro de ejecución en MIGRATION_REPORT. Desde raíz `python examples/mission_request.py` también funciona sin NumPy.

## Servidor y comprobación

Abrir http://127.0.0.1:8767/; detener con Ctrl+C en la misma consola. Evita 8766 si mantiene la instancia del proyecto anterior. No parar procesos ajenos. `--port` permite otro puerto (actualizar URL); el script de smoke usa 8767 explícitamente.

Con servidor 8767 iniciado:

```powershell
& .\.venv\Scripts\python.exe examples/http_smoke.py
```

Comprobado: GET raíz/JS/CSS/Leaflet/PNG y catálogo; POST cálculo real de rover, SUCCESS, 80 m. El navegador integrado inicialmente agotó conexión a la instancia aislada; al iniciar con localhost autorizado cargó la aplicación y completó una misión de astronauta por botón. Estado «Misión posible bajo el modelo» y tabla Necesitas/Tienes observados. No se afirma una auditoría visual exhaustiva, ancho reducido, nuevas descargas desde navegador o teselas remotas verificadas en bootstrap. Capturas antiguas son históricas, no capturas de esta migración.

## Linux — procedimiento propuesto, no ejecutado

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s prototypes/mission_planner -v
.venv/bin/python examples/mission_request.py
.venv/bin/python prototypes/mission_planner/mission_ui.py --port 8767
```

Se conserva biblioteca estándar y pathlib, pero no se declara validación Linux. El sistema debe permitir sockets locales; el navegador puede necesitar red para NASA Trek.

## Errores frecuentes

- `py` no encuentra Python: usar ruta real del ejecutable.
- Import de módulos del prototipo falla: ejecutar discovery con `-s` indicado o usar el ejemplo que prepara sys.path.
- NumPy no disponible: instalar requirements en el intérprete correcto; no copiar un entorno ajeno.
- Puerto ocupado: otro puerto, sin matar la app anterior.
- WinError 10013/DNS: restricciones del entorno; solicitar autorización específica, sin debilitar pruebas o seguridad.
- Checksum inválido/datos faltantes: restaurar archivos versionados y verificar hashes; no reemplazar por sintético.
- Imagen orbital no carga: elegir Solo datos locales; no interpretar falta de imagen como falta de elevación.
- `SEARCH_LIMIT_REACHED`: factibilidad desconocida; no aumentar límites automáticamente.
- Rápido rechaza recursos: se rechazó un candidato, no todas las rutas; ver 6.6.

La herramienta de migración raíz es un registro one-shot para el layout original; no es instalador. Para verificar que el origen y copia inicial siguen intactos usar `examples/verify_migration.py` solo donde exista la carpeta original. Sus hashes no se deben actualizar para encubrir cambios posteriores legítimos: preservar manifiesto baseline y registrar diffs nuevos.
