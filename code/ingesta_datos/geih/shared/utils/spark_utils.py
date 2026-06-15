from pyspark.sql import DataFrame, SparkSession


def leer_csv(spark: SparkSession, path: str) -> DataFrame:
    """Lee archivos CSV del formato GEIH desde un volumen de Unity Catalog.

    Los archivos GEIH usan delimitador punto y coma. La columna ``archivo_origen``
    se agrega automáticamente desde los metadatos del archivo para permitir extraer
    año y mes en la capa plata.

    Args:
        spark (SparkSession): Sesión de Spark activa.
        path (str): Ruta glob hacia los archivos CSV
            (ej. ``/Volumes/tesis/geih_bronce/ocupados/marco_nuevo/*.csv``).

    Returns:
        DataFrame: DataFrame con todas las columnas del CSV más ``archivo_origen``.

    Raises:
        AnalysisException: Si la ruta no existe o el clúster no tiene acceso al volumen.

    Example:
        >>> df = leer_csv(spark, "/Volumes/tesis/geih_bronce/ocupados/marco_nuevo/*.csv")
    """
    return (
        spark.read
        .option("header", "true")
        .option("delimiter", ";")
        .csv(path)
        .select("*", "_metadata.file_name")
        .withColumnRenamed("file_name", "archivo_origen")
    )


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
        >>> escribir_tabla(df, "tesis.geih_plata.ocupados_consolidado")
    """
    df.write.mode(mode).option("overwriteSchema", "true").saveAsTable(table_name)
