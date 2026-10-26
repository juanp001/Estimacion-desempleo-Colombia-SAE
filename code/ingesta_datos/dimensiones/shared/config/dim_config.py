# Configuración de las tablas dimensionales (R-54). Los nombres de las constantes son los mismos
# que usan geih_config, preprocesamiento/shared/config.py y modelo/shared/config.py.

# Unity Catalog
CATALOG = "tesis"
SCHEMA_DIM = "dim"

# Fuente: CSV de la DIVIPOLA (DANE) cargado en el volumen del esquema dim
RUTA_DIVIPOLA_CSV = f"/Volumes/{CATALOG}/{SCHEMA_DIM}/divipola/*.csv"

# Tablas que escribe el job dimensiones
# Nomenclatura DIVIPOLA de todos los municipios
TBL_DIM_DIVIPOLA = f"{CATALOG}.{SCHEMA_DIM}.dim_divipola"
# 32 capitales GEIH con CODIGO_AREA_GEIH (traducción del AREA de la encuesta)
TBL_DIM_GEIH_DIVIPOLA = f"{CATALOG}.{SCHEMA_DIM}.dim_geih_divipola"
# Dominio de estimación (ciudad o ciudad A.M.) de cada municipio
TBL_DIM_DOMINIO = f"{CATALOG}.{SCHEMA_DIM}.dim_dominio_geih"
