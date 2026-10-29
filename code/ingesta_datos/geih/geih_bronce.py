# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Ingesta de Datos GEIH - Capa Bronce
# MAGIC
# MAGIC Carga archivos CSV desde volúmenes de Unity Catalog hacia tablas estructuradas
# MAGIC en el catálogo `tesis.geih_bronce`, aplicando transformaciones mínimas de normalización.
# MAGIC
# MAGIC ## Módulos
# MAGIC * **caracteristicas_generales** · **fuerza_trabajo** · **ocupados**
# MAGIC * **no_ocupados** · **inactivos** · **fex**
# MAGIC
# MAGIC ## Secciones (marco antiguo)
# MAGIC * **cabecera**: zonas urbanas · **resto**: zonas rurales
# MAGIC * La sección **area** de los archivos fuente no se carga (R-21): ningún paso la usaba.
# MAGIC
# MAGIC ## Transformaciones aplicadas
# MAGIC 1. `archivo_origen`: nombre del archivo fuente extraído de metadatos
# MAGIC 2. `AREA`: inicializada como NULL en sección "resto" (no existe en raw)
# MAGIC 3. `MES`: extraído del nombre de archivo para fuerza_trabajo cabecera/resto
# MAGIC 4. `FT="1"`: marcador para fuerza_trabajo + sección resto (el raw de resto no trae `FT`)
# MAGIC
# MAGIC ## Período del marco antiguo (R-23)
# MAGIC El año (y el mes en fuerza de trabajo) sale del nombre del archivo,
# MAGIC `<seccion>_<modulo>_<MM>_<AAAA>.csv`, que produce `renombrar_geih.py` (en esta carpeta). Antes de
# MAGIC escribir cada tabla se verifica que todo archivo cumpla el patrón, que el año esté entre
# MAGIC `ANIO_MIN_MARCO_ANTIGUO` y `ANIO_MAX_MARCO_ANTIGUO`, que `MES` esté entre 01 y 12 y que
# MAGIC coincida con el mes del nombre; si no, el notebook se detiene (antes quedaban PER y PK
# MAGIC nulos sin aviso).

# COMMAND ----------

# DBTITLE 1,Importación de librerías
import os
import sys

# R-67: `code/` en sys.path para importar `comun` (el notebook está en code/ingesta_datos/<carpeta>/)
_ruta_nb = (
    dbutils.notebook.entry_point.getDbutils()
    .notebook()
    .getContext()
    .notebookPath()
    .get()
)
sys.path.insert(
    0, "/Workspace" + os.path.dirname(os.path.dirname(os.path.dirname(_ruta_nb)))
)

from pyspark.sql.functions import col, lit, regexp_extract

from shared.config.geih_config import (
    ANIO_MAX_MARCO_ANTIGUO,
    ANIO_MIN_MARCO_ANTIGUO,
    PATRON_ANIO_ARCHIVO,
    PATRON_MES_ARCHIVO,
    TABLAS_CONFIG,
)
from comun.spark_utils import leer_csv, escribir_tabla

# COMMAND ----------


# DBTITLE 1,Cargar tablas
def verificar_periodo_archivo(df, nombre_tabla: str) -> None:
    """Verifica el año y el mes que el marco antiguo toma del nombre de archivo (R-23).

    Args:
        df (DataFrame): Tabla bronce del marco antiguo con ``archivo_origen`` y ``MES``.
        nombre_tabla (str): Nombre de la tabla, para el mensaje de error.

    Returns:
        None: no devuelve nada; si el periodo es válido no pasa nada.

    Raises:
        ValueError: Si algún archivo no cumple ``<seccion>_<modulo>_<MM>_<AAAA>.csv``, si el
            año queda fuera de ``ANIO_MIN_MARCO_ANTIGUO``-``ANIO_MAX_MARCO_ANTIGUO`` o si
            ``MES`` no está entre 01 y 12 o no coincide con el mes del nombre.

    Example:
        >>> verificar_periodo_archivo(df, "tesis.geih_bronce.ocupados_resto_marco_antiguo")  # doctest: +SKIP
    """
    anio = regexp_extract(col("archivo_origen"), PATRON_ANIO_ARCHIVO, 1).cast("int")
    mes_archivo = regexp_extract(col("archivo_origen"), PATRON_MES_ARCHIVO, 1)
    malos = (
        df.select("archivo_origen", "MES")
        .distinct()
        .filter(
            anio.isNull()
            | ~anio.between(ANIO_MIN_MARCO_ANTIGUO, ANIO_MAX_MARCO_ANTIGUO)
            | ~col("MES").isin([f"{m:02d}" for m in range(1, 13)])
            | (col("MES") != mes_archivo)
        )
        .collect()
    )
    if malos:
        detalle = ", ".join(f"{r.archivo_origen} (MES={r.MES})" for r in malos[:5])
        raise ValueError(
            f"{nombre_tabla}: período inválido en {len(malos)} archivos: {detalle}"
        )


def cargar_tablas_bronce(
    spark,
    tablas_config: dict,
    table_number: int = None,
    seccion: str = None,
    modulo: str = None,
) -> None:
    """Carga archivos CSV de la GEIH desde volúmenes hacia tablas bronce en Unity Catalog.

    Itera sobre la configuración de tablas y aplica transformaciones específicas
    por módulo y sección antes de persistir en el catálogo.

    Args:
        spark (SparkSession): Sesión de Spark activa.
        tablas_config (dict): Diccionario con clave ``"config"`` conteniendo la lista
            de configuraciones de tablas (ver ``shared.config.geih_config.TABLAS_CONFIG``).
        table_number (int, optional): Índice 1-based para cargar solo una tabla específica.
            Si es ``None`` se cargan todas. Por defecto ``None``.
        seccion (str, optional): Filtra por sección geográfica: ``"cabecera"`` o
            ``"resto"``. Si es ``None`` no filtra. Por defecto ``None``.
        modulo (str, optional): Filtra por módulo temático: ``"caracteristicas_generales"``,
            ``"fuerza_trabajo"``, ``"ocupados"``, ``"no_ocupados"``, ``"inactivos"`` o
            ``"fex"``. Si es ``None`` no filtra. Por defecto ``None``.

    Returns:
        None: no devuelve nada; el efecto es las tablas bronce escritas en Unity Catalog.

    Raises:
        AnalysisException: Si alguna ruta de volumen no existe o falta acceso.

    Example:
        >>> cargar_tablas_bronce(spark, TABLAS_CONFIG)  # doctest: +SKIP
        >>> cargar_tablas_bronce(spark, TABLAS_CONFIG, modulo="ocupados", seccion="cabecera")  # doctest: +SKIP
    """
    for index, tabla in enumerate(tablas_config["config"]):
        if table_number is not None and table_number != index + 1:
            continue
        if seccion is not None and seccion != tabla["seccion"]:
            continue
        if modulo is not None and modulo != tabla["modulo"]:
            continue

        print(f"Cargando tabla {index + 1}: {tabla['table_name']}")
        print(f"Path: {tabla['path']}")

        df = leer_csv(spark, tabla["path"])

        # Sección "resto" no trae columna AREA en el raw — se inicializa como NULL
        if tabla["seccion"] == "resto":
            df = df.withColumn("AREA", lit(None).cast("string"))

        # Extrae mes del nombre de archivo (patrón: resto_fuerza_de_trabajo_01_2018.csv → "01")
        if tabla["aplicar_mes"]:
            df = df.withColumn(
                "MES", regexp_extract(col("archivo_origen"), PATRON_MES_ARCHIVO, 1)
            )

        # R-23: el período del marco antiguo sale del nombre de archivo; se verifica antes de escribir
        if tabla["marco"] == "antiguo":
            verificar_periodo_archivo(df, tabla["table_name"])

        # Identifica registros de fuerza de trabajo en sección resto
        if tabla["modulo"] == "fuerza_trabajo" and tabla["seccion"] == "resto":
            df = df.withColumn("FT", lit("1"))

        # R-21: ya no se limpia fex_c_2011 del módulo FT (no traía vacíos y oro solo usa el FEX
        # de características generales)

        escribir_tabla(df, tabla["table_name"])
        print("Tabla cargada")
        print("-" * 50)


# COMMAND ----------

cargar_tablas_bronce(spark, TABLAS_CONFIG)
