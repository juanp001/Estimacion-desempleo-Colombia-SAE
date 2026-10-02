"""Parámetros del preprocesamiento, el análisis descriptivo y la selección de covariables.

Reúne las tablas fuente y destino, las columnas de metadatos, los parámetros de la estimación
directa, los umbrales de calidad, los criterios de pre-filtrado y los de diagnóstico y
selección de covariables.
"""

# ── Tablas fuente ─────────────────────────────────────────────────────────────
TBL_MERCADO_LABORAL = "tesis.geih_oro.mercado_laboral"
TBL_TERRIDATA = "tesis.terridata.terridata_extendido_plata"
TBL_DIM_INDICADORES = "tesis.dim.dim_indicadores"

# ── Tablas destino ────────────────────────────────────────────────────────────
TBL_ESTIMACION_DIRECTA = "tesis.preprocesamiento.tasa_desempleo_municipal"
TBL_COVARIABLES = "tesis.preprocesamiento.tasa_desempleo_covariables"
TBL_PREFILTRADAS = "tesis.preprocesamiento.covariables_prefiltradas"
TBL_CASCADA = "tesis.preprocesamiento.cascada_prefiltrado"
TBL_SENSIBILIDAD = "tesis.preprocesamiento.sensibilidad_variabilidad"
TBL_SIN_ENCUESTA = "tesis.preprocesamiento.municipios_sin_encuesta"
TBL_CATALOGO = "tesis.preprocesamiento.catalogo_literatura"
TBL_DESCRIPTIVO_UNI = "tesis.preprocesamiento.descriptivo_univariado"
TBL_DESCRIPTIVO_BI = "tesis.preprocesamiento.descriptivo_bivariado"
TBL_DIAGNOSTICOS = "tesis.preprocesamiento.diagnosticos_covariables"
TBL_ROBUSTEZ = "tesis.preprocesamiento.robustez_covariables"
TBL_REDUNDANCIA = "tesis.preprocesamiento.redundancia_covariables"
TBL_DECISION = "tesis.preprocesamiento.decision_covariables"
TBL_VERIFICACION = "tesis.preprocesamiento.verificacion_seleccion"
TBL_TRAZABILIDAD = "tesis.preprocesamiento.trazabilidad_covariables"
TBL_CANDIDATAS = "tesis.preprocesamiento.covariables_candidatas"
TBL_SELECCIONADAS = "tesis.preprocesamiento.covariables_seleccionadas"

# ── Volumen para las figuras destinadas al documento ──────────────────────────
VOLUMEN_FIGURAS = "/Volumes/tesis/preprocesamiento/figuras_eda"

# ── Parámetros de estimación directa ──────────────────────────────────────────
BOOTSTRAP_REPLICAS = 2000
BOOTSTRAP_SEED = 42
# Período por defecto; en un job se sobrescribe con los parámetros anio_estimacion y
# mes_estimacion (ver `resolver_periodo`).
PER_ESTIMACION = 2018
MES_ESTIMACION = 12


def resolver_periodo(dbutils) -> tuple:
    """Resuelve el período a estimar a partir de los widgets del notebook o del job.

    Declara los widgets `anio_estimacion` y `mes_estimacion` con `PER_ESTIMACION` y
    `MES_ESTIMACION` como valores por defecto y los lee. Un parámetro de job con el mismo
    nombre reemplaza el valor del widget.

    Args:
        dbutils: Objeto `dbutils` del notebook (se pasa explícitamente porque un módulo
            importado no tiene acceso a él).

    Returns:
        tuple: `(per, mes)`, ambos `int`, con `mes` entre 1 y 12.

    Raises:
        ValueError: Si el año o el mes no son enteros, o si el mes está fuera de 1-12.

    Casos de uso:
        En `estimacion_directa.py` y `dominios_sin_encuesta.py`:
        `PER_ESTIMACION, MES_ESTIMACION = resolver_periodo(dbutils)`. En ejecución
        interactiva sin parámetros devuelve `(2018, 12)`.
    """
    dbutils.widgets.text("anio_estimacion", str(PER_ESTIMACION), "Año a estimar")
    dbutils.widgets.text("mes_estimacion", str(MES_ESTIMACION), "Mes a estimar (1-12)")
    anio = dbutils.widgets.get("anio_estimacion").strip()
    mes = dbutils.widgets.get("mes_estimacion").strip()
    try:
        per, mes = int(anio), int(mes)
    except ValueError:
        raise ValueError(
            f"anio_estimacion y mes_estimacion deben ser enteros; se recibió "
            f"anio_estimacion={anio!r}, mes_estimacion={mes!r}."
        )
    if not 1 <= mes <= 12:
        raise ValueError(f"mes_estimacion debe estar entre 1 y 12; se recibió {mes}.")
    return per, mes


# Columnas de agrupación para estimación directa
GRUPO_COLS = [
    "PER",
    "MES",
    "CODIGO_DEPARTAMENTO",
    "DEPARTAMENTO",
    "CODIGO_MUNICIPIO",
    "MUNICIPIO",
]

# Columnas que NO son covariables (identificación + estimaciones)
METADATA_COLS = [
    "PER",
    "MES",
    "CODIGO_DEPARTAMENTO",
    "DEPARTAMENTO",
    "CODIGO_MUNICIPIO",
    "MUNICIPIO",
    "TASA_DESEMPLEO_PCT",
    "SE_BOOTSTRAP_PCT",
    "IC_INF_PCT",
    "IC_SUP_PCT",
    "AMPLITUD_IC",
    "CV_PORCENTAJE",
    "DEPARTAMENTO_NORMALIZADO",
    "ENTIDAD_NORMALIZADO",
]

# Columnas a excluir de TerriData al hacer el join (ya existen en estimaciones)
COLUMNAS_EXCLUIR_JOIN = [
    "CODIGO_DEPARTAMENTO",
    "DEPARTAMENTO",
    "CODIGO_ENTIDAD",
    "ENTIDAD",
    "ANO",
    "MES",
]

# Variable respuesta
VARIABLE_OBJETIVO = "TASA_DESEMPLEO_PCT"

# Umbrales de calidad de estimación (criterios DANE/CEPAL)
CV_CONFIABLE = 5.0  # CV < 5 %   → confiable
CV_ACEPTABLE = 20.0  # CV < 20 %  → aceptable; >= 20 % → no confiable

# ── Pre-filtrado (independiente de la variable respuesta) ─────────────────────
# Umbral de coeficiente de variación por debajo del cual la columna se considera
# constante a efectos prácticos. Es invariante a las unidades del indicador.
CV_MINIMO = 0.001
# Proporción máxima de dominios que puede acumular el valor modal.
PROP_MODAL_MAXIMA = 0.90
# Magnitud de correlación a partir de la cual dos covariables se consideran duplicadas.
UMBRAL_DUPLICADO = 0.999

# ── Diagnóstico y selección ──────────────────────────────────────────────────
# Magnitud de correlación a partir de la cual dos candidatas se consideran redundantes y
# solo una de ellas puede entrar al modelo.
UMBRAL_REDUNDANCIA = 0.80
# Cambio máximo tolerado en la correlación con la respuesta al excluir un dominio.
UMBRAL_DELTA_LOO = 0.10
# Número máximo de covariables por parsimonia: n/5 con n = 23 dominios.
P_MAXIMO = 4
# Umbral de multicolinealidad para el conjunto finalmente seleccionado.
VIF_MAXIMO = 5.0
# Nivel de confianza del intervalo de Fisher para la correlación con la respuesta.
ALFA_IC_CORRELACION = 0.05

# ── Dominios objetivo sin cobertura muestral ─────────────────────────────────
# Códigos DIVIPOLA de los departamentos del estudio: Cauca (19) y Valle del Cauca (76).
DEPARTAMENTOS_OBJETIVO = [19, 76]
