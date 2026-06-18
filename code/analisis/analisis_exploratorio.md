# Notas sobre el Análisis Exploratorio — para el documento de tesis

Resumen de lo que funcionó bien en `Análisis exploratorio.py` y de los puntos que conviene
explicar con cuidado al lector cuando se redacte el capítulo correspondiente.

## Qué destacar como fortalezas del análisis

- **Reconocimiento explícito del sesgo de selección (double dipping / winner's curse):**
  las covariables ya fueron filtradas por su correlación con Y usando los mismos 23 dominios.
  Explicar esto evita que el lector interprete las correlaciones reportadas como evidencia
  confirmatoria insesgada.
- **Uso de IC bootstrap junto al coeficiente puntual:** con n=23 un r puntual sin intervalo
  es poco informativo; mostrar el rango de incertidumbre es más honesto.
- **Triangulación de métodos** para juzgar si una correlación es "real": Pearson + Spearman
  (concordancia), Cook's D (apalancamiento) y leave-one-out (estabilidad ante exclusión de
  dominios atípicos como Bogotá o Quibdó).
- **Separación temporal entre literatura (L) y evidencia empírica (Q):** L se fija antes de
  calcular las métricas empíricas, evitando circularidad en el score compuesto.
- **Prueba de sensibilidad al parámetro α:** mostrar que la selección final no cambia al
  variar el peso literatura/datos es una validación de robustez que vale la pena resaltar.
- **Restricción de diversidad dimensional:** evita que las 4 covariables finales terminen
  siendo proxies redundantes de la misma dimensión conceptual.

## Consideraciones que deben quedar explícitas en el documento

1. **El filtro cualitativo (Etapa 2, 84→16) es un juicio humano, no un resultado objetivo.**
   Debe presentarse como tal: otra revisión de literatura podría producir un catálogo distinto.
   No describirlo como un paso "automático" o "neutral".
2. **Los umbrales usados son heurísticas (rule of thumb), no derivaciones formales:**
   Cook's D > 4/n, |Δ| LOO < 0.10, |r−ρ| > 0.15. Aclarar que sirven para triaje, no como
   pruebas estadísticas con propiedades de error controladas.
3. **Baja potencia de Shapiro-Wilk y del test de Moran con n=23.** "No rechazar H0" en estos
   tests no debe leerse como "se confirma normalidad/independencia espacial" — el documento
   debe matizar esta conclusión explícitamente para no sobre-interpretar resultados negativos.
4. **El score compuesto C = (1−α)Q + α(L/3) es una heurística de ranking, no una optimización
   formal.** Q es un promedio simple de 5 componentes con pesos iguales; esa elección de
   pesos debe mencionarse como una decisión de diseño, no como algo derivado matemáticamente.
5. **Las variables no seleccionadas no deben presentarse como "descartadas por inútiles".**
   Distinguir en el texto entre "débil genuina" (señal poco fiable) y "frágil a n=23"
   (señal real pero inestable con la muestra actual) — esta distinción es importante para
   no cerrar la puerta a trabajo futuro con más dominios.
6. **La validación confirmatoria real ocurre en `fay_herriot.py`** (AIC/BIC, diagnósticos,
   validación cruzada). El EDA debe presentarse como insumo de triaje, dejando claro que la
   confianza final en las 4 covariables no se basa en este notebook sino en el modelo ajustado.
