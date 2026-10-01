# Tablas fuente
TBL_MERCADO_LABORAL  = "tesis.geih_oro.mercado_laboral"
TBL_TERRIDATA        = "tesis.terridata.terridata_extendido_plata"
TBL_DIM_INDICADORES  = "tesis.dim.dim_indicadores"

# Tablas destino
TBL_PERSONAS_CENSO     = "tesis.censo_nal.personas"
TBL_DIM_DIVIPOLA       = "tesis.dim.dim_divipola"
DEPARTAMENTOS_CENSO    = [19, 76]
TBL_ESTIMACION_DIRECTA = "tesis.censo_nal.tasa_desempleo"
TBL_COVARIABLES        = "tesis.preprocesamiento.tasa_desempleo_covariables"
TBL_PREFILTRADAS = "tesis.preprocesamiento.covariables_prefiltradas"

# Parámetros de estimación directa
BOOTSTRAP_REPLICAS  = 2000
BOOTSTRAP_SEED      = 42
PER_ESTIMACION      = 2018
MES_ESTIMACION      = 12

# Columnas de agrupación para estimación directa
GRUPO_COLS = [
    "PER", "MES",
    "CODIGO_DEPARTAMENTO", "DEPARTAMENTO",
    "CODIGO_MUNICIPIO", "MUNICIPIO",
]

# Columnas que NO son covariables (identificación + estimaciones)
METADATA_COLS = [
    "PER", "MES",
    "CODIGO_DEPARTAMENTO", "DEPARTAMENTO",
    "CODIGO_MUNICIPIO", "MUNICIPIO",
    "TASA_DESEMPLEO_PCT", "VARIANZA", "SE_PCT", "CV_PORCENTAJE",
    "PET", "PEA", "OCUPADOS", "DESOCUPADOS", "INACTIVOS",
    "DEPARTAMENTO_NORMALIZADO", "ENTIDAD_NORMALIZADO",
]

# Columnas a excluir de TerriData al hacer el join (ya existen en estimaciones)
COLUMNAS_EXCLUIR_JOIN = [
    "CODIGO_DEPARTAMENTO", "DEPARTAMENTO",
    "CODIGO_ENTIDAD", "ENTIDAD",
    "ANO", "MES",
]

# Parámetros de filtrado y selección de covariables
VARIABLE_OBJETIVO = "TASA_DESEMPLEO_PCT"
UMBRAL_VARIANZA   = 0.00001
CORR_MODO         = "threshold"
CORR_VALOR        = 0.4

# Umbrales de calidad de estimación (criterios DANE/CEPAL)
CV_CONFIABLE = 5.0    # CV < 5 %   → confiable
CV_ACEPTABLE = 20.0   # CV < 20 %  → aceptable; >= 20 % → no confiable
