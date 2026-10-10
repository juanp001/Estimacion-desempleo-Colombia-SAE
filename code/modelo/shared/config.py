"""Parámetros del modelo Fay-Herriot.

Las especificaciones a comparar no se escriben a mano: se parte del conjunto que eligió
`eda_seleccion_covariables` (`covariables_seleccionadas`) y se comparan ese conjunto
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
TBL_COVARIABLES_SELECCIONADAS = "tesis.preprocesamiento.covariables_seleccionadas"
TBL_MUNICIPIOS_SIN_ENCUESTA = "tesis.preprocesamiento.municipios_sin_encuesta"
TBL_TRAZABILIDAD = "tesis.preprocesamiento.trazabilidad_covariables"
# Nombres oficiales de departamento y municipio por código DIVIPOLA: las dos fuentes de
# dominios escriben los nombres con distinto formato, así que la tabla final se une por
# código y toma los nombres de aquí.
TBL_DIM_DIVIPOLA = "tesis.dim.dim_divipola"
# Dominios GEIH (ciudad o ciudad A.M.) y sus municipios miembro: nombres de los dominios y
# membresía que verifica el benchmarking de nivel 2.
TBL_DIM_DOMINIO = "tesis.dim.dim_dominio_geih"
# Indicadores municipales de TerriData: de aquí sale el peso del benchmarking de nivel 2.
TBL_TERRIDATA = "tesis.terridata.terridata_extendido_plata"
# Cifras oficiales publicadas por el DANE: valor de control del benchmarking de nivel 1.
TBL_DATOS_MUNICIPALES = "tesis.geih_bronce.datos_municipales"
NOMBRE_TOTAL_23 = "Total 23 ciudades y A.M."

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
SE_COL = "SE_BOOTSTRAP_PCT"

# Columnas que identifican un dominio de estimación (ciudad o ciudad A.M.). La clave es
# PER + MES + CODIGO_DOMINIO (código DIVIPOLA de la capital); los nombres acompañan para
# lectura, pero no se usan para unir.
DOMINIO_COLS = [
    "PER",
    "MES",
    "CODIGO_DEPARTAMENTO",
    "CODIGO_DOMINIO",
    "DEPARTAMENTO",
    "NOMBRE_DOMINIO",
    "TIPO_DOMINIO",
]

# Columnas que identifican un municipio objetivo (predicción sintética). CODIGO_DOMINIO_PADRE es
# el dominio con estimación directa que lo contiene (NULL si no hay ninguno): define el grupo del
# benchmarking de nivel 2.
MUNICIPIO_COLS = [
    "PER",
    "MES",
    "CODIGO_DEPARTAMENTO",
    "CODIGO_MUNICIPIO",
    "DEPARTAMENTO",
    "MUNICIPIO",
    "CODIGO_DOMINIO_PADRE",
]

# ── Benchmarking (ver shared/benchmarking.py) ───────────────────────────────
# Peso del nivel 1 (dominios → total de las 23 ciudades): PEA expandida de cada dominio, que
# calcula estimacion_directa con los factores de expansión.
COL_PESO_NIVEL1 = "PEA_EXPANDIDA"
# Peso del nivel 2 (municipios → su dominio A.M.): población de 15 años y más (PET de la serie
# GEIH con proyecciones CNPV 2018), aproximación de la PEA municipal, que es el denominador de la
# tasa de desempleo. Las covariables de los dominios A.M. se agregan con el denominador de cada
# indicador (preprocesamiento/shared/reglas_agregacion.py). Suma de los grupos quinquenales por
# sexo de 15-19 a 80 y más de TerriData (02001xxxx hombres, 02002xxxx mujeres).
COLS_PESO_POBLACION = [
    f"0200{sexo}0{grupo:03d}" for sexo in ("1", "2") for grupo in range(4, 18)
]
EXPR_PESO_POBLACION = " + ".join(
    f"try_cast(`{c}` AS DOUBLE)" for c in COLS_PESO_POBLACION
)
# Aviso cuando el factor de ajuste se aleja de 1 más de esta fracción: «si el modelo es
# adecuado, el factor de ajuste estará en torno a uno» (INE Chile, ENUSC 2018, PDF 23).
UMBRAL_LAMBDA_AVISO = 0.20
# Tolerancia (puntos porcentuales) entre el valor de control del nivel 1 calculado con la
# muestra y la cifra publicada por el DANE.
TOLERANCIA_DANE_PP = 0.01

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
