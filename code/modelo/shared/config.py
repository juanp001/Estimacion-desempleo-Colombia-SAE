"""Parámetros del modelo Fay-Herriot.

Las especificaciones a comparar no se escriben a mano: se parte del conjunto que eligió
`eda_seleccion_covariables_rev` (`covariables_seleccionadas_rev`) y se comparan ese conjunto
y sus variantes dejando una covariable fuera, generadas en `shared/seleccion_modelo.py`. Así
el modelo no puede quedar desincronizado del análisis exploratorio y la comparación responde
a una pregunta concreta: si cada covariable aporta.

El ganador se elige siguiendo a Morales et al. (2021, p. 453): como el modelo se usa para
predecir fuera de muestra, solo compiten las variantes con todas sus covariables
significativas; entre ellas, la de menor AIC y, entre las equivalentes por AIC, la de menos
covariables. El error cuadrático medio del EBLUP y la distancia de Cook se reportan como
diagnósticos (ganancia de precisión y robustez), sin intervenir en la elección.
"""

# ── Tablas fuente (salidas del flujo de selección de covariables) ────────────
TBL_COVARIABLES_SELECCIONADAS = "tesis.preprocesamiento.covariables_seleccionadas_rev"
TBL_MUNICIPIOS_SIN_ENCUESTA = "tesis.preprocesamiento.municipios_sin_encuesta_rev"
TBL_TRAZABILIDAD = "tesis.preprocesamiento.trazabilidad_covariables_rev"
# Nombres oficiales de departamento y municipio por código DIVIPOLA: las dos fuentes de
# dominios escriben los nombres con distinto formato, así que la tabla final se une por
# código y toma los nombres de aquí.
TBL_DIM_DIVIPOLA = "tesis.dim.dim_divipola"

# ── Tablas destino ───────────────────────────────────────────────────────────
TBL_FAY_HERRIOT_RESULTADOS = "tesis.modelo.fay_herriot_resultados"
TBL_FAY_HERRIOT_PREDICCION_SINTETICA = "tesis.modelo.fay_herriot_prediccion_sintetica"
TBL_FAY_HERRIOT_ESTIMACIONES_FINALES = "tesis.modelo.fay_herriot_estimaciones_finales"
TBL_FH_DIAGNOSTICOS_VARIANTES = "tesis.modelo.fh_diagnosticos_variantes"
TBL_FH_COOK = "tesis.modelo.fh_cook"
TBL_FH_SELECCION_MODELO = "tesis.modelo.fh_seleccion_modelo"
TBL_FH_COEFICIENTES = "tesis.modelo.fh_coeficientes"

# ── Variable objetivo y varianza directa ─────────────────────────────────────
Y_COL = "TASA_DESEMPLEO_PCT"
SE_COL = "SE_PCT"

# Columnas que identifican un dominio. La clave es PER + MES + CODIGO_MUNICIPIO (DIVIPOLA);
# los nombres acompañan para lectura, pero no se usan para unir.
DOMINIO_COLS = [
    "PER",
    "MES",
    "CODIGO_DEPARTAMENTO",
    "CODIGO_MUNICIPIO",
    "DEPARTAMENTO",
    "MUNICIPIO",
]

# ── Umbrales de confiabilidad del CV ─────────────────────────────────────────
CV_CONFIABLE = 5.0  # CV < 5 %   → confiable
CV_ACEPTABLE = 20.0  # CV < 20 %  → aceptable; >= 20 % → no confiable

# ── Selección de modelo ──────────────────────────────────────────────────────
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
