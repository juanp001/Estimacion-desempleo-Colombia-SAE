"""Parámetros del modelo Fay-Herriot sobre el conjunto de covariables revisado.

Hereda de `modelo/shared/config.py` todo lo que no cambia (columnas de dominio, variable
respuesta y su error estándar, umbrales de calidad) y redirige las tablas de entrada y
salida a sus versiones `_rev`, de modo que los resultados originales quedan intactos y
pueden compararse.

La diferencia sustantiva está en cómo se obtienen las especificaciones a comparar. En la
versión original era una lista fija de cuatro combinaciones escritas a mano (`COVAR_SETS`),
que había que editar cada vez que cambiaba la selección de covariables. Aquí se parte del
conjunto que eligió `eda_seleccion_covariables_rev` (`covariables_seleccionadas_rev`) y se
comparan ese conjunto y sus variantes dejando una covariable fuera, generadas en
`shared/seleccion_modelo_rev.py`. Así el modelo no puede quedar desincronizado del análisis
exploratorio y la comparación responde a una pregunta concreta: si cada covariable aporta.

El ganador se elige siguiendo a Morales et al. (2021, p. 453): como el modelo se usa para
predecir fuera de muestra, solo compiten las variantes con todas sus covariables
significativas; entre ellas, la de menor AIC y, entre las equivalentes por AIC, la de menos
covariables. El error cuadrático medio del EBLUP y la distancia de Cook se reportan como
diagnósticos (ganancia de precisión y robustez), sin intervenir en la elección.
"""

from modelo.shared.config import *  # noqa: F401,F403

# ── Tablas fuente de la versión revisada ─────────────────────────────────────
TBL_COVARIABLES_SELECCIONADAS_REV = (
    "tesis.preprocesamiento.covariables_seleccionadas_rev"
)
TBL_MUNICIPIOS_SIN_ENCUESTA_REV = "tesis.preprocesamiento.municipios_sin_encuesta_rev"
TBL_TRAZABILIDAD_REV = "tesis.preprocesamiento.trazabilidad_covariables_rev"

# ── Tablas destino de la versión revisada ────────────────────────────────────
TBL_FAY_HERRIOT_RESULTADOS_REV = "tesis.modelo.fay_herriot_resultados_rev"
TBL_FAY_HERRIOT_PREDICCION_SINTETICA_REV = (
    "tesis.modelo.fay_herriot_prediccion_sintetica_rev"
)
TBL_FAY_HERRIOT_ESTIMACIONES_FINALES_REV = (
    "tesis.modelo.fay_herriot_estimaciones_finales_rev"
)
TBL_FH_DIAGNOSTICOS_VARIANTES_REV = "tesis.modelo.fh_diagnosticos_variantes_rev"
TBL_FH_COOK_REV = "tesis.modelo.fh_cook_rev"
TBL_FH_SELECCION_MODELO_REV = "tesis.modelo.fh_seleccion_modelo_rev"
TBL_FH_COEFICIENTES_REV = "tesis.modelo.fh_coeficientes_rev"

# Diferencia de AIC por debajo de la cual dos variantes se consideran equivalentes, según
# la tabla de criterios de decisión del marco teórico. Entre las equivalentes, la
# metodología impone elegir la de menos covariables.
DELTA_AIC_EQUIVALENTE = 2.0

# Nivel de significancia que deben cumplir todas las covariables de una variante para
# competir (Morales et al., p. 453: al predecir fuera de muestra no conviene incluir
# covariables no significativas).
ALFA_SIGNIFICANCIA = 0.05

# ── Avisos ───────────────────────────────────────────────────────────────────
# Si el peso γ de la estimación directa no supera este valor en ningún dominio, Â ≈ 0 y el
# EBLUP coincide con el predictor sintético.
UMBRAL_GAMMA_SIN_PESO = 0.01
# Rango admisible de una tasa en porcentaje.
TASA_MINIMA = 0.0
TASA_MAXIMA = 100.0

# Directorio donde se guardan las figuras del capítulo de resultados. Es el mismo volumen que
# usan los notebooks del análisis descriptivo y de la selección de covariables, de modo que
# todas las figuras de la versión revisada quedan juntas.
VOLUMEN_FIGURAS = "/Volumes/tesis/preprocesamiento/figuras_eda"

# Nombres de las dos figuras que devuelve `graficar_validacion_rev()`, en el orden en que las
# construye: efecto suavizador del EBLUP e histograma de residuos estandarizados. Las figuras
# de la función de varianza generalizada no se muestran porque el modelo usa las varianzas
# bootstrap sin suavizar.
NOMBRES_FIGURAS_VALIDACION_REV = ("suavizador", "histograma")
# Nombre de la figura de distancia de Cook por dominio del modelo elegido.
NOMBRE_FIGURA_COOK = "cook"
# Nombre de la figura de CV directo frente a CV del EBLUP del modelo elegido.
NOMBRE_FIGURA_CV = "cv_directo_eblup"
