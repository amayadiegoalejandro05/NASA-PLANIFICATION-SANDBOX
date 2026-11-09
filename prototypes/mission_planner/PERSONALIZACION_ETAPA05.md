# Personalización experimental de etapa 5

Decisión: **no implementar una fórmula antropométrica de consumo EVA marciano**.
Las fuentes revisadas no aportan una relación transferible y validada para este
motor, su terreno y un traje marciano. Esto no afirma que tales modelos sean
imposibles: documenta el alcance de esta implementación.

## Fuentes primarias revisadas

Consultadas el 5 de noviembre de 2026 (America/Bogota):

- [NASA, Human Performance, §4.5 y V1 4020](https://www.nasa.gov/reference/4-0-human-performance/):
  el cálculo de requerimientos nutricionales de misión considera edad, sexo,
  masa, altura y actividad. Es provisión nutricional individual; no suministra
  aquí una ecuación de locomoción con traje en Marte.
- [NASA, Spacesuits, §11.2 y §11.4](https://www.nasa.gov/reference/11-0-spacesuits-vol-2/):
  distingue provisión de nutrición e hidratación, capacidades del traje y
  medición/cálculo de tasa metabólica durante EVA. Sus requisitos de disponibilidad
  no se convierten en tasas individuales de consumo de este prototipo.
- [Cox y colaboradores, NTRS 20240009328, 2024](https://ntrs.nasa.gov/citations/20240009328),
  incluida la [presentación original, pp. 3–8 y 18](https://ntrs.nasa.gov/api/citations/20240009328/downloads/ISS%20RDC%202024_Met%20Rate%20Prediction_final_2.pdf):
  usa historial individual por tareas y mediciones respiratorias NBL/ISS; trata
  correcciones entre entornos y limitaciones por tarea. El soporte vital incluye
  restricciones de eliminación de CO2 y calor. Inferencia para este proyecto:
  esa evidencia favorece tasas individuales documentadas; no justifica trasladar
  sus correcciones ni la capacidad de un EMU a locomoción marciana.

## Clasificación de parámetros

| Parámetro | Clasificación | Significado implementado |
|---|---|---|
| Masa corporal, kg | Metadato sin efecto | `PersonalCharacteristics.body_mass_kg`, opcional, positivo finito |
| Altura, m | Metadato sin efecto | `height_m`, opcional, positivo finito |
| Edad y sexo biológico | Pendientes de modelo apropiado; no se recopilan | No existen campos porque ningún cálculo implementado los necesita |
| Identidad de género | Sin uso fisiológico | No es coeficiente ni campo de este contrato |
| Tasas individuales por recurso y fase | Utilizadas | `ResourceAllocation.movement_rate/activity_rate`, unidad/min |
| Velocidad y coeficientes de ascenso/esfuerzo/rugosidad | Utilizados | Fórmulas parametrizadas heredadas; no calibradas por introducir metadatos |
| Radio, margen, pendiente máxima | Utilizados | Admisibilidad geométrica, sin inferirlos de estatura o masa |
| Capacidades, saldos y reservas | Utilizados | Disponibilidad de equipo/experimento y restricciones absolutas |
| Factores nominales/conservadores | Utilizados | Multiplican tasas de ambas fases, salvo tiempo |
| Composición corporal, condición física, fatiga, adaptación, ajuste/presión del traje, carga transportada | Pendientes | No hay un modelo validado para traducirlos a tasas |

No se calculan necesidades nutricionales diarias. `nutrition` representa demanda
energética parametrizada en kcal, no obligación de comer durante una EVA breve.
O2 conserva unidades simuladas sin conversión a masa, volumen o presión. Agua
representa solo el recurso configurado en L: no integra agua de refrigeración
ni un balance hídrico fisiológico. Batería representa Wh del equipo declarado.
CO2, calor, radiación y meteorología no se modelan.

## Procedencia e incertidumbre

La entrada principal sigue siendo el perfil con tasas individuales configurables.
Cada recurso modelado exige `RateProvenance(nature, source, scope)`; `nature` admite
`measured`, `estimated` o `simulated`. La declaración cubre movimiento y actividad;
si difieren sus fuentes, se deben precisar ambas en `source` y `scope`. El motor
preserva esa declaración, sin autenticar mediciones ni prometer su transferencia
a otras tareas. Todos los perfiles de la evaluación son **simulados**. Los tests
de etiquetas measured/estimated usan datos ficticios identificados como fixtures.

`RateScenario` exige un factor explícito para cada recurso modelado. Nominal:
todos 1. Conservador: factores >=1; tiempo siempre 1. Se multiplican las tasas
de movimiento y actividad; velocidad, reservas y Wh/m de ascenso se mantienen.
Por tanto, es una sensibilidad de tasas, no un modelo integral de peor caso.
El ejemplo +20% es una hipótesis ficticia, no un percentil ni una probabilidad
calibrada. No se usa una calculadora basal terrestre ni una ecuación nutricional
para certificar gasto EVA.

Solo se usan perfiles personales ficticios. La prueba de masas/alturas distintas
exige idéntica ruta y consumo; añadir campos no oculta los factores pendientes.
