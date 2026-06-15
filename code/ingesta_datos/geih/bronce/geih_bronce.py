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
# MAGIC * **cabecera**: zonas urbanas · **resto**: zonas rurales · **area**: consolidado
# MAGIC
# MAGIC ## Transformaciones aplicadas
# MAGIC 1. `archivo_origen`: nombre del archivo fuente extraído de metadatos
# MAGIC 2. `AREA`: inicializada como NULL en sección "resto" (no existe en raw)
# MAGIC 3. `MES`: extraído del nombre de archivo para fuerza_trabajo cabecera/resto
# MAGIC 4. `FT="1"`: marcador para fuerza_trabajo + sección resto
# MAGIC 5. `fex_c_2011`: strings vacíos convertidos a NULL (marco antiguo, fuerza_trabajo)

# COMMAND ----------

# DBTITLE 1,Importación de librerías
import sys
import os

# Agregar el directorio padre (geih) al path para importar módulos shared
sys.path.insert(0, os.path.dirname(os.getcwd()))

from pyspark.sql.functions import col, lit, regexp_extract, when, trim

from shared.config.geih_config import TABLAS_CONFIG
from shared.utils.spark_utils import leer_csv, escribir_tabla

# COMMAND ----------

# DBTITLE 1,Cargar tablas
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
        seccion (str, optional): Filtra por sección geográfica: ``"area"``, ``"cabecera"``
            o ``"resto"``. Si es ``None`` no filtra. Por defecto ``None``.
        modulo (str, optional): Filtra por módulo temático: ``"caracteristicas_generales"``,
            ``"fuerza_trabajo"``, ``"ocupados"``, ``"no_ocupados"``, ``"inactivos"`` o
            ``"fex"``. Si es ``None`` no filtra. Por defecto ``None``.

    Raises:
        AnalysisException: Si alguna ruta de volumen no existe o falta acceso.

    Example:
        >>> cargar_tablas_bronce(spark, TABLAS_CONFIG)
        >>> cargar_tablas_bronce(spark, TABLAS_CONFIG, modulo="ocupados", seccion="cabecera")
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
            df = df.withColumn("MES", regexp_extract(col("archivo_origen"), r"_(\d{2})_\d{4}\.csv", 1))

        # Identifica registros de fuerza de trabajo en sección resto
        if tabla["modulo"] == "fuerza_trabajo" and tabla["seccion"] == "resto":
            df = df.withColumn("FT", lit("1"))

        # Marco antiguo trae fex_c_2011 con strings vacíos en vez de NULL
        if tabla["marco"] == "antiguo" and tabla["modulo"] == "fuerza_trabajo":
            df = df.withColumn(
                "fex_c_2011",
                when(trim(col("fex_c_2011")) == "", lit(None).cast("string"))
                .otherwise(col("fex_c_2011")),
            )

        escribir_tabla(df, tabla["table_name"])
        print("Tabla cargada")
        print("-" * 50)


# COMMAND ----------

cargar_tablas_bronce(spark, TABLAS_CONFIG)
