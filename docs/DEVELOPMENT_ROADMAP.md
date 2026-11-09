# Roadmap posterior al baseline

Bootstrap preserva, documenta y ejecuta; no implementa estas mejoras.

| Fase | Estado/objetivo | Criterio de salida propuesto |
|---|---|---|
| 1 | Completada: snapshots, errores y geometría | Regresiones preservadas |
| 2 | Completada: perfiles y recursos | Contratos humanos/rover separados |
| 3 | Completada: misión 3.0 explicable | Contabilidad, estados y JSON |
| 4 | Completada: CTX local | Datos y marcos comprobados |
| 5 | Completada experimental: decisiones 5.0 | Continuar/regresar y pruebas pequeñas |
| 6 | Funcional; ampliación histórica incompleta | Acordar alcance regional vs todo cráter, color y curvas; última vista estrecha pendiente |
| 6.5 | Rigor numérico | Auditoría de unidades y cuentas independientes; demanda separada de alimentación; procedencia por perfil; sin falsa calibración |
| 6.6 | Algoritmos | Semántica de candidato rápido corregida/versionada; comparación A*/Dijkstra; alternativas, restricciones e incertidumbre comprobadas |
| 6.7 | Interfaz | Desglose, perfil de elevación, alertas, estados y alternativas entendibles; validación de navegador real |
| 6.8 | Integración | Contratos públicos estables, ejemplos ejecutados y guía para otros equipos; no confundir puente local con API pública |
| 6.9 | Rendimiento | Benchmark reproducible; perfiles ligero/estándar/investigación con límites medidos; optimización justificada |
| 7 | ROS posterior | Adaptador separado y evidencia explícita de preparación vs comunicación ejecutada |

Dependencias: baseline reproducible antes de 6.5; reglas semánticas antes de exponer resultados en 6.8; medir antes de optimizar; ROS después de consolidación. No prometer cubrir todo Jezero ampliando solamente el mapa. Autoría/licencia de originales debe aclararse antes de distribución pública.

Primera intervención 6.5: tabla verificable de unidades/tasas por fase y recurso con fixtures aritméticos independientes (plano, ascenso, actividad, saldos/reservas), contrastada contra funciones existentes, sin ajustar coeficientes a un resultado deseado. Evaluar desbordamientos y tolerancias; cambios solo cuando un fallo concreto esté reproducido.
