# Datos científicos y cartografía

Se incorporan solo recortes compactos existentes, no mosaicos globales. Los bytes/tamaños/hashes de todos los archivos migrados están en `migration/source-manifest.json`.

| Directorio | Contenido y función |
|---|---|
| data/jezero | terrain.npz 79.786 bytes y metadata.json. 128×128 a 4 m, 512 m. Prior CTX nativo 20 m y reference HiRISE nativo 1 m, remuestreo previo. Adaptador de planificación decodifica solo prior, no alturas HiRISE ni máscara conjunta. |
| data/mission_planner_ctx_2km | terrain.json 180.186 bytes, source-window.npy 45.888 bytes y metadata.json. Ventana CTX 2 km, 100×100 a 20 m; promedio GDAL, sin relleno. |

NPZ esperado: `18d20b39a680d93addc3c3151bb3f19a5f41fc8f9a170396d4094694bbd76d6b`.
Regional JSON: `eacc709117d3fce8863838f3638c9dc00b989215957d274c27edcd98665083db`.
Ventana regional NPY: `0ab1dfdbff9a2801ee4fa86242448a7f95ed248c62eda8e70c510bf1485b515e`.

CTX: Fergason et al. (2020), DOI [10.5066/P906QQT8](https://doi.org/10.5066/P906QQT8). HiRISE: Fergason et al. (2020), DOI [10.5066/P9REJ9JN](https://doi.org/10.5066/P9REJ9JN). Ambos MRO; no afirmar diversidad de misiones por esas dos capas.

Verificación de licencia durante bootstrap (2026-11-08): los registros primarios [CTX](https://data.usgs.gov/datacatalog/data/USGS%3Af354e990-9f17-451b-9006-dcbbdb26ea0c) y [HiRISE](https://data.usgs.gov/datacatalog/data/USGS%3A7a41dc7c-d545-4fac-b042-d40d3fc8227b) declaran acceso público y etiqueta de dominio público. [Política USGS](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits) distingue materiales propios y de terceros. Esta comprobación es específica de productos, no una licencia universal para cualquier imagen. Se conservan citas y metadatos.

Región: esfera Marte R=3.396.190 m; latitud planetocéntrica, longitud este. Origen 18.45 N/77.45 E. E=R*cos(lat0)*(lon-lon0), N=R*(lat-lat0), ángulos en radianes. Afín regional [-1000,20,0,1000,0,-20]. Centros +0,5; filas al sur, columnas al este. Alturas absolutas MOLA/DeltaGeoid, sin offset terrestre. La retícula de 4 m no añade información CTX de 4 m.

No existen obstáculos locales observados ni capas científicas de riesgo/rugosidad. Valores neutrales desactivan esas capas; obstáculos de UI son simulados, 20×20 m en región. No convertir fotografía orbital en transitabilidad certificada.

Runtime verifica checksums y falla sin sustituir datos. En un clon normal no hace falta preparar nada. Si se pierde la región: instalar requisitos de preparación y ejecutar `prepare_ctx_2km.py` solo en una carpeta sin adquisición existente. Ese procedimiento depende de red/Rasterio y NO fue reejecutado en bootstrap para evitar sobrescritura; no garantiza un binario idéntico con otra versión GDAL. El recorte histórico no tiene aquí un importador propio: restaurarlo desde Git por su hash, no generar un sustituto ficticio.

Cartografía: NASA Trek CTX gris y contexto MOLA/HRSC remotos; relieve/elevación local derivados. [Servicios](https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars). Licencias/metadatos consultados durante etapa 6 se conservan en evidence/stage06_maps. No se revalidaron teselas remotas en bootstrap. No hay color orbital validado ni Viking habilitado; conservar atribuciones de la UI.
