"""Utilidades de Spark comunes a toda la ingesta (R-67).

Antes vivían duplicadas en `ingesta_datos/geih/shared/utils` y `ingesta_datos/terridata/shared/utils`.
"""

import glob
from functools import reduce

from pyspark.sql import DataFrame, SparkSession


def leer_csv(spark: SparkSession, path: str) -> DataFrame:
    """Lee archivos CSV del formato GEIH desde un volumen de Unity Catalog.

    Los archivos GEIH usan delimitador punto y coma. La columna ``archivo_origen``
    se agrega automáticamente desde los metadatos del archivo para permitir extraer
    año y mes en la capa plata.

    Cada archivo se lee por separado y se une **por nombre de columna**. Leer el glob
    de una vez no sirve: Spark toma el encabezado de un solo archivo y asigna las
    columnas de los demás por posición. En la GEIH 2018 los archivos de enero a marzo
    traen otro orden (``AREA`` al final, sin ``MES``), así que la lectura por
    posición corría los valores (p. ej. ``FT`` quedaba con el código de departamento
    e ``INI`` con el mes).

    Args:
        spark (SparkSession): Sesión de Spark activa.
        path (str): Ruta glob hacia los archivos CSV
            (ej. ``/Volumes/tesis/geih_bronce/ocupados/marco_nuevo/*.csv``).

    Returns:
        DataFrame: DataFrame con la unión de las columnas de todos los archivos (las
        que falten en un archivo quedan en NULL) más ``archivo_origen``.

    Raises:
        FileNotFoundError: Si el glob no encuentra ningún archivo.
        AnalysisException: Si el clúster no tiene acceso al volumen.

    Example:
        >>> df = leer_csv(spark, "/Volumes/tesis/geih_bronce/ocupados/marco_nuevo/*.csv")  # doctest: +SKIP
    """
    archivos = sorted(glob.glob(path))
    if not archivos:
        raise FileNotFoundError(f"No hay archivos en {path}")

    partes = [
        spark.read.option("header", "true")
        .option("delimiter", ";")
        .csv(archivo)
        .select("*", "_metadata.file_name")
        .withColumnRenamed("file_name", "archivo_origen")
        for archivo in archivos
    ]
    return reduce(lambda a, b: a.unionByName(b, allowMissingColumns=True), partes)


def leer_parquet(spark: SparkSession, path: str) -> DataFrame:
    """Lee archivos Parquet desde un volumen de Unity Catalog.

    Args:
        spark (SparkSession): Sesión de Spark activa.
        path (str): Ruta al directorio o glob de archivos Parquet.

    Returns:
        DataFrame: Datos leídos.

    Example:
        >>> df = leer_parquet(spark, "/Volumes/tesis/terridata_archivos/consolidado")  # doctest: +SKIP
    """
    return spark.read.parquet(path)


def escribir_tabla(df: DataFrame, table_name: str, mode: str = "overwrite") -> None:
    """Escribe un DataFrame en una tabla de Unity Catalog.

    Args:
        df (DataFrame): DataFrame de Spark a persistir.
        table_name (str): Nombre completamente calificado de la tabla destino
            en formato ``catalog.schema.table``.
        mode (str): Modo de escritura. Por defecto ``"overwrite"``.

    Raises:
        AnalysisException: Si la ruta de la tabla es inválida o faltan permisos.

    Example:
        >>> escribir_tabla(df, "tesis.geih_plata.ocupados_consolidado")  # doctest: +SKIP
    """
    df.write.mode(mode).option("overwriteSchema", "true").saveAsTable(table_name)
