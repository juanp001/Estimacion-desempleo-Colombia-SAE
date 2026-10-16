# Databricks notebook source
from pyspark.sql import DataFrame, SparkSession

# COMMAND ----------

tablas_config = {
    "config": [
        {
            "table_name": "tesis.censo_nal.fallecidos",
            "path": "/Volumes/tesis/censo_nal/fallecidos",
            "modulo": "fallecidos",
        },
        {
            "table_name": "tesis.censo_nal.viviendas",
            "path": "/Volumes/tesis/censo_nal/viviendas",
            "modulo": "viviendas",
        },
        {
            "table_name": "tesis.censo_nal.hogares",
            "path": "/Volumes/tesis/censo_nal/hogares",
            "modulo": "hogares",
        },
        {
            "table_name": "tesis.censo_nal.personas",
            "path": "/Volumes/tesis/censo_nal/personas",
            "modulo": "personas",
        },
        {
            "table_name": "tesis.censo_nal.marco_georreferenciacion",
            "path": "/Volumes/tesis/censo_nal/marco_georreferenciacion",
            "modulo": "marco_georreferenciacion",
        },
    ]
}

# COMMAND ----------


def cargar_tablas_bronce(
    spark: SparkSession,
    tablas_config: dict,
    table_number: int = None,
    modulo: str = None,
) -> None:
    """Carga cada volumen de Parquet del censo como tabla bronce en Unity Catalog.

    Recorre ``tablas_config["config"]``, lee todos los archivos Parquet del volumen
    de cada módulo, agrega la columna ``archivo_origen`` y sobrescribe la tabla destino.

    Args:
        spark (SparkSession): sesión de Spark activa.
        tablas_config (dict): diccionario con la clave ``"config"``, lista de dicts con
            ``table_name`` (str, tabla destino), ``path`` (str, carpeta del volumen con
            los Parquet) y ``modulo`` (str, nombre del módulo).
        table_number (int, optional): posición (desde 1) de la única tabla a cargar.
            Si es None se consideran todas.
        modulo (str, optional): nombre del único módulo a cargar. Si es None se
            consideran todos.

    Returns:
        None: escribe las tablas en Unity Catalog y no devuelve valor.

    Ejemplos de uso:
        cargar_tablas_bronce(spark, tablas_config)  # todos los módulos
        cargar_tablas_bronce(spark, tablas_config, modulo="personas")  # solo uno
    """
    for index, tabla in enumerate(tablas_config["config"]):

        if table_number is not None and table_number != index + 1:
            continue

        if modulo is not None and modulo != tabla["modulo"]:
            continue

        print(f"Cargando tabla {index + 1}")
        print(f"Cargando tabla {tabla['table_name']}")
        print(f"Path: {tabla['path']}")

        # Lista los archivos del volumen antes de leerlos
        archivos = dbutils.fs.ls(tabla["path"])
        for archivo in archivos:
            print(f"  - {archivo.name} ({archivo.size} bytes)")

        df: DataFrame = spark.read.parquet(tabla["path"])
        df = df.select("*", "_metadata.file_name").withColumnRenamed(
            "file_name", "archivo_origen"
        )

        df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
            tabla["table_name"]
        )

        print("Tabla cargada")
        print("-" * 50)


cargar_tablas_bronce(spark, tablas_config)
