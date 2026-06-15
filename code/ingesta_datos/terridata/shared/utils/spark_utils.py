from pyspark.sql import DataFrame, SparkSession


def leer_parquet(spark: SparkSession, path: str) -> DataFrame:
    """Lee archivos Parquet desde un volumen de Unity Catalog.

    Args:
        spark: SparkSession activa.
        path:  Ruta al directorio o glob de archivos Parquet.

    Returns:
        DataFrame con los datos leídos.
    """
    return spark.read.parquet(path)


def escribir_tabla(df: DataFrame, table_name: str, mode: str = "overwrite") -> None:
    """Persiste un DataFrame en Unity Catalog.

    Args:
        df:         DataFrame a guardar.
        table_name: Nombre completamente calificado (catalog.schema.table).
        mode:       Modo de escritura Spark (por defecto "overwrite").
    """
    df.write.mode(mode).option("overwriteSchema", "true").saveAsTable(table_name)
