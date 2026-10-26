# Unity Catalog
CATALOG = "tesis"
SCHEMA_BRONCE = "geih_bronce"
SCHEMA_PLATA = "geih_plata"
SCHEMA_ORO = "geih_oro"

# Base path for raw CSV volumes
VOLUME_BASE = f"/Volumes/{CATALOG}/{SCHEMA_BRONCE}"

# Nombre de los CSV del marco antiguo (R-23): <seccion>_<modulo>_<MM>_<AAAA>.csv, p. ej.
# resto_fuerza_de_trabajo_01_2018.csv. Lo produce code/ingesta_datos/geih/renombrar_geih.py a partir de
# las carpetas del DANE (GEIH/<año>/<Mes>/). El año y, en fuerza de trabajo, el mes salen de
# este nombre; geih_bronce falla si no cumple el patrón o quedan fuera de rango.
PATRON_ANIO_ARCHIVO = r"_\d{2}_(\d{4})\.csv$"
PATRON_MES_ARCHIVO = r"_(\d{2})_\d{4}\.csv$"
# Años que cubre el marco antiguo (GEIH desde 2006; marco 2005 hasta 2022)
ANIO_MIN_MARCO_ANTIGUO = 2006
ANIO_MAX_MARCO_ANTIGUO = 2022

# Datos publicados por el DANE (anexo mercado laboral según proyecciones CNPV 2018)
RUTA_DATOS_PUBLICADOS = (
    f"{VOLUME_BASE}/datos_publicados/"
    "anexo-mercado-laboral-segun-proyecciones-CNPV2018.xlsx"
)
URL_FUENTE_DATOS_PUBLICADOS = (
    "https://www.dane.gov.co/files/investigaciones/boletines/ech/"
    "nuevo-enfoque-conceptual-metodologico-2018/"
    "anexo-mercado-laboral-segun-proyecciones-CNPV2018.xlsx"
)
TBL_DATOS_NACIONALES = f"{CATALOG}.{SCHEMA_BRONCE}.datos_nacionales"
TBL_DATOS_MUNICIPALES = f"{CATALOG}.{SCHEMA_BRONCE}.datos_municipales"
TBL_DATOS_ANUALES = f"{CATALOG}.{SCHEMA_BRONCE}.datos_anuales"
ANIO_INICIO_PUBLICADOS = 2016
ANIO_FIN_PUBLICADOS = 2021

# Destination table names — plata
TBL_CG_PLATA = f"{CATALOG}.{SCHEMA_PLATA}.caracteristicas_generales_consolidado"
TBL_FT_PLATA = f"{CATALOG}.{SCHEMA_PLATA}.fuerza_trabajo_consolidado"
TBL_NO_PLATA = f"{CATALOG}.{SCHEMA_PLATA}.no_ocupados_consolidado"
TBL_OC_PLATA = f"{CATALOG}.{SCHEMA_PLATA}.ocupados_consolidado"
TBL_FEX_PLATA = f"{CATALOG}.{SCHEMA_PLATA}.dim_fex"

# Destination table names — oro
TBL_MERCADO_LABORAL = f"{CATALOG}.{SCHEMA_ORO}.mercado_laboral"
# Reconciliación de la fuerza de trabajo (G7-B5)
TBL_RECONCILIACION_FT = f"{CATALOG}.{SCHEMA_ORO}.reconciliacion_fuerza_trabajo"
TBL_LLAVES_SIN_PAREJA = f"{CATALOG}.{SCHEMA_ORO}.llaves_sin_pareja"

# Dimension tables
# R-54: mismos nombres que preprocesamiento y modelo (TBL_DIM_DIVIPOLA es la DIVIPOLA completa)
# 32 capitales GEIH con CODIGO_AREA_GEIH: de aquí sale el municipio en geih_oro
TBL_DIM_GEIH_DIVIPOLA = f"{CATALOG}.dim.dim_geih_divipola"
# DIVIPOLA completa: de aquí sale el nombre del departamento en geih_oro (R-24)
TBL_DIM_DIVIPOLA = f"{CATALOG}.dim.dim_divipola"
# Dominio de estimación (ciudad o ciudad A.M.) de cada municipio
TBL_DIM_DOMINIO = f"{CATALOG}.dim.dim_dominio_geih"

# Source table names — bronce (marco nuevo)
TBL_CG_BRONCE = f"{CATALOG}.{SCHEMA_BRONCE}.caracteristicas_generales"
TBL_FT_BRONCE = f"{CATALOG}.{SCHEMA_BRONCE}.fuerza_trabajo"
TBL_NO_BRONCE = f"{CATALOG}.{SCHEMA_BRONCE}.no_ocupados"
TBL_OC_BRONCE = f"{CATALOG}.{SCHEMA_BRONCE}.ocupados"
TBL_FEX_BRONCE = f"{CATALOG}.{SCHEMA_BRONCE}.dim_fex"

# Source table names — bronce (marco antiguo, características generales)
TBL_CG_CAB_MA = (
    f"{CATALOG}.{SCHEMA_BRONCE}.caracteristicas_generales_cabecera_marco_antiguo"
)
TBL_CG_RESTO_MA = (
    f"{CATALOG}.{SCHEMA_BRONCE}.caracteristicas_generales_resto_marco_antiguo"
)

# Source table names — bronce (marco antiguo, fuerza de trabajo)
TBL_FT_CAB_MA = f"{CATALOG}.{SCHEMA_BRONCE}.fuerza_trabajo_cabecera_marco_antiguo"
TBL_FT_RESTO_MA = f"{CATALOG}.{SCHEMA_BRONCE}.fuerza_trabajo_resto_marco_antiguo"

# Source table names — bronce (marco antiguo, inactivos)
TBL_IN_CAB_MA = f"{CATALOG}.{SCHEMA_BRONCE}.inactivos_cabecera_marco_antiguo"
TBL_IN_RESTO_MA = f"{CATALOG}.{SCHEMA_BRONCE}.inactivos_resto_marco_antiguo"

# Source table names — bronce (marco antiguo, no ocupados)
TBL_NO_CAB_MA = f"{CATALOG}.{SCHEMA_BRONCE}.no_ocupados_cabecera_marco_antiguo"
TBL_NO_RESTO_MA = f"{CATALOG}.{SCHEMA_BRONCE}.no_ocupados_resto_marco_antiguo"

# Source table names — bronce (marco antiguo, ocupados)
TBL_OC_CAB_MA = f"{CATALOG}.{SCHEMA_BRONCE}.ocupados_cabecera_marco_antiguo"
TBL_OC_RESTO_MA = f"{CATALOG}.{SCHEMA_BRONCE}.ocupados_resto_marco_antiguo"


# Ingestion configuration for the bronce layer.
# Each entry maps a module/section/marco combination to its destination table and source path.
# Fields:
#   table_name   : Fully qualified destination table in Unity Catalog
#   path         : Glob path to source CSV files in the volume
#   seccion      : Geographic section — "cabecera", "resto", or None (marco nuevo)
#                  (R-21: la sección "area" del marco antiguo no se carga; nadie la usaba y la de
#                  características generales solo traía Ene-Mar 2018)
#   modulo       : Thematic module — see module names below
#   aplicar_mes  : True to extract MES from the filename, None otherwise
#   marco        : "antiguo", "nuevo", or None (fex)
TABLAS_CONFIG = {
    "config": [
        # ========== MARCO ANTIGUO - CARACTERÍSTICAS GENERALES ==========
        {
            "table_name": TBL_CG_CAB_MA,
            "path": f"{VOLUME_BASE}/caracteristicas_generales/marco_antiguo/cabecera/*.csv",
            "seccion": "cabecera",
            "modulo": "caracteristicas_generales",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
        {
            "table_name": TBL_CG_RESTO_MA,
            "path": f"{VOLUME_BASE}/caracteristicas_generales/marco_antiguo/resto/*.csv",
            "seccion": "resto",
            "modulo": "caracteristicas_generales",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
        # ========== MARCO ANTIGUO - FUERZA DE TRABAJO ==========
        {
            "table_name": TBL_FT_CAB_MA,
            "path": f"{VOLUME_BASE}/fuerza_de_trabajo/marco_antiguo/cabecera/*.csv",
            "seccion": "cabecera",
            "modulo": "fuerza_trabajo",
            "aplicar_mes": True,
            "marco": "antiguo",
        },
        {
            "table_name": TBL_FT_RESTO_MA,
            "path": f"{VOLUME_BASE}/fuerza_de_trabajo/marco_antiguo/resto/*.csv",
            "seccion": "resto",
            "modulo": "fuerza_trabajo",
            "aplicar_mes": True,
            "marco": "antiguo",
        },
        # ========== MARCO ANTIGUO - OCUPADOS ==========
        {
            "table_name": TBL_OC_CAB_MA,
            "path": f"{VOLUME_BASE}/ocupados/marco_antiguo/cabecera/*.csv",
            "seccion": "cabecera",
            "modulo": "ocupados",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
        {
            "table_name": TBL_OC_RESTO_MA,
            "path": f"{VOLUME_BASE}/ocupados/marco_antiguo/resto/*.csv",
            "seccion": "resto",
            "modulo": "ocupados",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
        # ========== MARCO ANTIGUO - INACTIVOS ==========
        {
            "table_name": TBL_IN_CAB_MA,
            "path": f"{VOLUME_BASE}/inactivos/marco_antiguo/cabecera/*.csv",
            "seccion": "cabecera",
            "modulo": "inactivos",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
        {
            "table_name": TBL_IN_RESTO_MA,
            "path": f"{VOLUME_BASE}/inactivos/marco_antiguo/resto/*.csv",
            "seccion": "resto",
            "modulo": "inactivos",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
        # ========== MARCO ANTIGUO - NO OCUPADOS ==========
        {
            "table_name": TBL_NO_CAB_MA,
            "path": f"{VOLUME_BASE}/no_ocupados/marco_antiguo/cabecera/*.csv",
            "seccion": "cabecera",
            "modulo": "no_ocupados",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
        {
            "table_name": TBL_NO_RESTO_MA,
            "path": f"{VOLUME_BASE}/no_ocupados/marco_antiguo/resto/*.csv",
            "seccion": "resto",
            "modulo": "no_ocupados",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
        # ========== MARCO NUEVO (sin división por sección) ==========
        {
            "table_name": TBL_CG_BRONCE,
            "path": f"{VOLUME_BASE}/caracteristicas_generales/marco_nuevo/*.csv",
            "seccion": None,
            "modulo": "caracteristicas_generales",
            "aplicar_mes": None,
            "marco": "nuevo",
        },
        {
            "table_name": TBL_FT_BRONCE,
            "path": f"{VOLUME_BASE}/fuerza_de_trabajo/marco_nuevo/*.csv",
            "seccion": None,
            "modulo": "fuerza_trabajo",
            "aplicar_mes": None,
            "marco": "nuevo",
        },
        {
            "table_name": TBL_OC_BRONCE,
            "path": f"{VOLUME_BASE}/ocupados/marco_nuevo/*.csv",
            "seccion": None,
            "modulo": "ocupados",
            "aplicar_mes": None,
            "marco": "nuevo",
        },
        {
            "table_name": TBL_NO_BRONCE,
            "path": f"{VOLUME_BASE}/no_ocupados/marco_nuevo/*.csv",
            "seccion": None,
            "modulo": "no_ocupados",
            "aplicar_mes": None,
            "marco": "nuevo",
        },
        # ========== FACTORES DE EXPANSIÓN (FEX) ==========
        {
            "table_name": TBL_FEX_BRONCE,
            "path": f"/Volumes/{CATALOG}/{SCHEMA_BRONCE}/fex/*.csv",
            "seccion": None,
            "modulo": "fex",
            "aplicar_mes": None,
            "marco": None,
        },
    ]
}
