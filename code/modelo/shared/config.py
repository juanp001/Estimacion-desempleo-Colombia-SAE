# Tablas fuente
TBL_COVARIABLES_SELECCIONADAS = "tesis.preprocesamiento.covariables_seleccionadas"
TBL_MUNICIPIOS_SIN_ENCUESTA   = "tesis.modelo.municipios_sin_encuesta"

# Tablas destino
TBL_FAY_HERRIOT_RESULTADOS           = "tesis.modelo.fay_herriot_resultados"
TBL_FAY_HERRIOT_PREDICCION_SINTETICA = "tesis.modelo.fay_herriot_prediccion_sintetica"
TBL_FAY_HERRIOT_ESTIMACIONES_FINALES = "tesis.modelo.fay_herriot_estimaciones_finales"

# Variable objetivo y varianza directa
Y_COL  = "TASA_DESEMPLEO_PCT"
SE_COL = "SE_BOOTSTRAP_PCT"

# Columnas que identifican un dominio (PER+MES+DEPARTAMENTO+MUNICIPIO)
DOMINIO_COLS = ["PER", "MES", "DEPARTAMENTO", "MUNICIPIO"]

# Conjuntos de covariables candidatos para el modelo Fay-Herriot
COVAR_SETS = [
    ["IICA_CONFLICTO", "TASA_TRAN_EDU_SUP", "IND_POB_MULT", "IND_PROD"],
    ["TASA_TRAN_EDU_SUP", "IND_POB_MULT"],
    ["IICA_CONFLICTO", "IND_PROD"],
    ["IICA_CONFLICTO", "TASA_TRAN_EDU_SUP"],
]

# Umbrales de calidad de estimación (criterios DANE/CEPAL), iguales a los usados
# en code/preprocesamiento/shared/config.py
CV_CONFIABLE = 15.0   # CV < 15 %  → confiable
CV_ACEPTABLE = 30.0   # CV < 30 %  → aceptable; >= 30 % → no confiable
