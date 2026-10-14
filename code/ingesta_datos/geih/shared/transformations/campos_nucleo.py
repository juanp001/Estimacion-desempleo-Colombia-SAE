from pyspark.sql.functions import col, concat, lit, regexp_extract, regexp_replace, trim

# Campos núcleo para marco nuevo.
# El marco nuevo entrega PERIODO, MES y FEX_C18 directamente en las tablas bronce.
# MARCO identifica el origen de cada fila en plata: geih_oro lo usa para elegir el factor de
# expansión (G7-B6), porque en el marco nuevo FEX ya es el factor calibrado con el CNPV 2018.
CAMPOS_NUCLEO_MARCO_NUEVO = [
    concat(col("PERIODO"), col("DIRECTORIO"), col("SECUENCIA_P"), col("ORDEN")).alias(
        "PK"
    ),
    col("PERIODO"),
    col("PER").cast("int").alias("PER"),
    col("MES").cast("int").alias("MES"),
    col("DIRECTORIO"),
    col("SECUENCIA_P"),
    col("ORDEN"),
    col("HOGAR"),
    col("REGIS"),
    trim(col("AREA")).alias("CODIGO_AREA"),
    col("FEX_C18").alias("FEX"),
    trim(col("DPTO")).alias("CODIGO_DPTO"),
    lit("NUEVO").alias("MARCO"),
]

# Campos núcleo para marco antiguo.
# PERIODO y PER se extraen del nombre del archivo origen con regex.
# FEX_C_2011 requiere reemplazar comas por puntos antes de castear a double. Es el factor
# calibrado con las proyecciones del censo 2005: el factor CNPV 2018 viene de dim_fex.
CAMPOS_NUCLEO_MARCO_ANTIGUO = [
    concat(
        regexp_extract(col("archivo_origen"), r"(\d{4})", 1),
        col("MES"),
        col("DIRECTORIO"),
        col("SECUENCIA_P"),
        col("ORDEN"),
    ).alias("PK"),
    concat(
        regexp_extract(col("archivo_origen"), r"(\d{4})", 1),
        col("MES"),
    ).alias("PERIODO"),
    regexp_extract(col("archivo_origen"), r"(\d{4})", 1).cast("int").alias("PER"),
    col("MES").cast("int").alias("MES"),
    col("DIRECTORIO"),
    col("SECUENCIA_P"),
    col("ORDEN"),
    col("HOGAR"),
    col("REGIS"),
    trim(col("AREA")).alias("CODIGO_AREA"),
    regexp_replace(col("FEX_C_2011"), ",", ".").cast("double").alias("FEX"),
    trim(col("DPTO")).alias("CODIGO_DPTO"),
    lit("ANTIGUO").alias("MARCO"),
]
