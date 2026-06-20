# Unity Catalog
CATALOG = "tesis"
SCHEMA_BRONCE = "geih_bronce"
SCHEMA_PLATA  = "geih_plata"
SCHEMA_ORO    = "geih_oro"

# Base path for raw CSV volumes
VOLUME_BASE = f"/Volumes/{CATALOG}/{SCHEMA_BRONCE}"

# Destination table names — plata
TBL_CG_PLATA  = f"{CATALOG}.{SCHEMA_PLATA}.caracteristicas_generales_consolidado"
TBL_FT_PLATA  = f"{CATALOG}.{SCHEMA_PLATA}.fuerza_trabajo_consolidado"
TBL_NO_PLATA  = f"{CATALOG}.{SCHEMA_PLATA}.no_ocupados_consolidado"
TBL_OC_PLATA  = f"{CATALOG}.{SCHEMA_PLATA}.ocupados_consolidado"
TBL_FEX_PLATA = f"{CATALOG}.{SCHEMA_PLATA}.dim_fex"

# Destination table names — oro
TBL_MERCADO_LABORAL = f"{CATALOG}.{SCHEMA_ORO}.mercado_laboral"

# Dimension tables
TBL_DIM_DIVIPOLA = f"{CATALOG}.dim.dim_geih_divipola"

# Source table names — bronce (marco nuevo)
TBL_CG_BRONCE  = f"{CATALOG}.{SCHEMA_BRONCE}.caracteristicas_generales"
TBL_FT_BRONCE  = f"{CATALOG}.{SCHEMA_BRONCE}.fuerza_trabajo"
TBL_NO_BRONCE  = f"{CATALOG}.{SCHEMA_BRONCE}.no_ocupados"
TBL_OC_BRONCE  = f"{CATALOG}.{SCHEMA_BRONCE}.ocupados"
TBL_FEX_BRONCE = f"{CATALOG}.{SCHEMA_BRONCE}.dim_fex"

# Source table names — bronce (marco antiguo, características generales)
TBL_CG_AREA_MA     = f"{CATALOG}.{SCHEMA_BRONCE}.caracteristicas_generales_area_marco_antiguo"
TBL_CG_CAB_MA      = f"{CATALOG}.{SCHEMA_BRONCE}.caracteristicas_generales_cabecera_marco_antiguo"
TBL_CG_RESTO_MA    = f"{CATALOG}.{SCHEMA_BRONCE}.caracteristicas_generales_resto_marco_antiguo"

# Source table names — bronce (marco antiguo, fuerza de trabajo)
TBL_FT_AREA_MA     = f"{CATALOG}.{SCHEMA_BRONCE}.fuerza_trabajo_area_marco_antiguo"
TBL_FT_CAB_MA      = f"{CATALOG}.{SCHEMA_BRONCE}.fuerza_trabajo_cabecera_marco_antiguo"
TBL_FT_RESTO_MA    = f"{CATALOG}.{SCHEMA_BRONCE}.fuerza_trabajo_resto_marco_antiguo"

# Source table names — bronce (marco antiguo, inactivos)
TBL_IN_AREA_MA     = f"{CATALOG}.{SCHEMA_BRONCE}.inactivos_area_marco_antiguo"
TBL_IN_CAB_MA      = f"{CATALOG}.{SCHEMA_BRONCE}.inactivos_cabecera_marco_antiguo"
TBL_IN_RESTO_MA    = f"{CATALOG}.{SCHEMA_BRONCE}.inactivos_resto_marco_antiguo"

# Source table names — bronce (marco antiguo, no ocupados)
TBL_NO_AREA_MA     = f"{CATALOG}.{SCHEMA_BRONCE}.no_ocupados_area_marco_antiguo"
TBL_NO_CAB_MA      = f"{CATALOG}.{SCHEMA_BRONCE}.no_ocupados_cabecera_marco_antiguo"
TBL_NO_RESTO_MA    = f"{CATALOG}.{SCHEMA_BRONCE}.no_ocupados_resto_marco_antiguo"

# Source table names — bronce (marco antiguo, ocupados)
TBL_OC_AREA_MA     = f"{CATALOG}.{SCHEMA_BRONCE}.ocupados_area_marco_antiguo"
TBL_OC_CAB_MA      = f"{CATALOG}.{SCHEMA_BRONCE}.ocupados_cabecera_marco_antiguo"
TBL_OC_RESTO_MA    = f"{CATALOG}.{SCHEMA_BRONCE}.ocupados_resto_marco_antiguo"


# Ingestion configuration for the bronce layer.
# Each entry maps a module/section/marco combination to its destination table and source path.
# Fields:
#   table_name   : Fully qualified destination table in Unity Catalog
#   path         : Glob path to source CSV files in the volume
#   seccion      : Geographic section — "area", "cabecera", "resto", or None (marco nuevo)
#   modulo       : Thematic module — see module names below
#   aplicar_mes  : True to extract MES from the filename, None otherwise
#   marco        : "antiguo", "nuevo", or None (fex)
TABLAS_CONFIG = {
    "config": [
        # ========== MARCO ANTIGUO - CARACTERÍSTICAS GENERALES ==========
        {
            "table_name": TBL_CG_AREA_MA,
            "path": f"{VOLUME_BASE}/caracteristicas_generales/marco_antiguo/area/*.csv",
            "seccion": "area",
            "modulo": "caracteristicas_generales",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
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
            "table_name": TBL_FT_AREA_MA,
            "path": f"{VOLUME_BASE}/fuerza_de_trabajo/marco_antiguo/area/*.csv",
            "seccion": "area",
            "modulo": "fuerza_trabajo",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
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
            "table_name": TBL_OC_AREA_MA,
            "path": f"{VOLUME_BASE}/ocupados/marco_antiguo/area/*.csv",
            "seccion": "area",
            "modulo": "ocupados",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
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
            "table_name": TBL_IN_AREA_MA,
            "path": f"{VOLUME_BASE}/inactivos/marco_antiguo/area/*.csv",
            "seccion": "area",
            "modulo": "inactivos",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
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
            "table_name": TBL_NO_AREA_MA,
            "path": f"{VOLUME_BASE}/no_ocupados/marco_antiguo/area/*.csv",
            "seccion": "area",
            "modulo": "no_ocupados",
            "aplicar_mes": None,
            "marco": "antiguo",
        },
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
