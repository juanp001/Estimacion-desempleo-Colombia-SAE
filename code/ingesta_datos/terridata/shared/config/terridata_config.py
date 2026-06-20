CATALOG      = "tesis"
SCHEMA_DATOS = "terridata"
SCHEMA_DIM   = "dim"

VOL_CONSOLIDADO = f"/Volumes/{CATALOG}/{SCHEMA_DATOS}/terridata_archivos/consolidado/"

TBL_BRONCE          = f"{CATALOG}.{SCHEMA_DATOS}.terridata_bronce"
TBL_PLATA           = f"{CATALOG}.{SCHEMA_DATOS}.terridata_extendido_plata"
TBL_DIM_INDICADORES = f"{CATALOG}.{SCHEMA_DIM}.dim_indicadores"

# Columnas de identificación en la tabla plata (groupBy del pivot)
COLUMNAS_ID = [
    "CODIGO_DEPARTAMENTO",
    "DEPARTAMENTO",
    "DEPARTAMENTO_NORMALIZADO",
    "CODIGO_ENTIDAD",
    "ENTIDAD",
    "ENTIDAD_NORMALIZADO",
    "ANO",
    "MES",
]

# Umbral para clasificar un indicador como numérico:
# si >= UMBRAL_CLASIFICACION_NUMERICO % de sus valores vienen de DATO_NUMERICO → "numerico"
UMBRAL_CLASIFICACION_NUMERICO = 95

# Umbral de alerta en la verificación de calidad del casteo numérico (% sobre total)
UMBRAL_RIESGO_CASTEO = 5.0
