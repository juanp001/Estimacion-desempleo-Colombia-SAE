"""Parámetros del modelo Fay-Herriot sobre el conjunto de covariables revisado.

Hereda de `modelo/shared/config.py` todo lo que no cambia (columnas de dominio, variable
respuesta y su error estándar, umbrales de calidad) y redirige las tablas de entrada y
salida a sus versiones `_rev`, de modo que los resultados originales quedan intactos y
pueden compararse.

La diferencia sustantiva está en `COVAR_SETS`. En la versión original era una lista fija
de cuatro combinaciones escritas a mano, que había que editar cada vez que cambiaba la
selección de covariables; si alguien modificaba el análisis exploratorio sin actualizar
esta constante, el modelo seguía ajustándose sobre covariables antiguas sin avisar. Aquí las
especificaciones a comparar se leen de la tabla `busqueda_aic_rev` que produce la etapa de
selección, de modo que el modelo siempre se ajusta sobre el resultado vigente del análisis.

Esas especificaciones no se limitan a las covariables del conjunto ganador, por lo que el
ajuste se hace sobre `covariables_candidatas_rev`, que contiene todas las que llegaron a la
búsqueda. `covariables_seleccionadas_rev` conserva el significado que tenía en la versión
original: únicamente las covariables del conjunto elegido.
"""

from modelo.shared.config import *  # noqa: F401,F403

# ── Tablas fuente de la versión revisada ─────────────────────────────────────
TBL_COVARIABLES_CANDIDATAS_REV    = "tesis.preprocesamiento.covariables_candidatas_rev"
TBL_COVARIABLES_SELECCIONADAS_REV = "tesis.preprocesamiento.covariables_seleccionadas_rev"
TBL_MUNICIPIOS_SIN_ENCUESTA_REV   = "tesis.preprocesamiento.municipios_sin_encuesta_rev"
TBL_BUSQUEDA_AIC_REV              = "tesis.preprocesamiento.busqueda_aic_rev"

# ── Tablas destino de la versión revisada ────────────────────────────────────
TBL_FAY_HERRIOT_RESULTADOS_REV           = "tesis.modelo.fay_herriot_resultados_rev"
TBL_FAY_HERRIOT_PREDICCION_SINTETICA_REV = "tesis.modelo.fay_herriot_prediccion_sintetica_rev"
TBL_FAY_HERRIOT_ESTIMACIONES_FINALES_REV = "tesis.modelo.fay_herriot_estimaciones_finales_rev"
TBL_FH_DIAGNOSTICOS_VARIANTES_REV        = "tesis.modelo.fh_diagnosticos_variantes_rev"
TBL_FH_SELECCION_MODELO_REV              = "tesis.modelo.fh_seleccion_modelo_rev"
TBL_FH_COEFICIENTES_REV                  = "tesis.modelo.fh_coeficientes_rev"

# Número de especificaciones a comparar, tomadas por orden de AIC de la búsqueda exhaustiva
# de la etapa de selección. Sustituye a la lista fija `COVAR_SETS`.
N_VARIANTES = 4

# Diferencia de AIC por debajo de la cual dos variantes se consideran equivalentes, segun
# la tabla de criterios de decision del marco teorico. Entre las equivalentes, la
# metodologia impone elegir la de menos covariables.
DELTA_AIC_EQUIVALENTE = 2.0

# Directorio donde se guardan las figuras del capitulo de resultados. Es el mismo volumen que
# usan los notebooks del analisis descriptivo y de la seleccion de covariables, de modo que
# todas las figuras de la version revisada quedan juntas.
VOLUMEN_FIGURAS = "/Volumes/tesis/preprocesamiento/figuras_eda"

# Nombres de las cuatro figuras que devuelve `graficar_validacion()`, en el orden en que las
# construye: residuos de la funcion de varianza generalizada, ajuste de esa funcion, efecto
# suavizador del EBLUP e histograma de residuos estandarizados.
NOMBRES_FIGURAS_VALIDACION = ("gvf_residuos", "gvf_ajuste", "suavizador", "histograma")
