# Databricks notebook source
from pyspark.sql.functions import lit, regexp_extract, col,when, trim

# COMMAND ----------

tablas_config = {
    "config":[
        {
            "table_name": "tesis.censo_nal.fallecidos",
            "path": "/Volumes/tesis/censo_nal/fallecidos/*.csv",
            "modulo": "fallecidos"
        },
        {
            "table_name": "tesis.censo_nal.viviendas",
            "path": "/Volumes/tesis/censo_nal/viviendas/*.csv",
            "modulo": "viviendas"
        },
        {
            "table_name": "tesis.censo_nal.hogares",
            "path": "/Volumes/tesis/censo_nal/hogares/*.csv",
            "modulo": "hogares"
        },
        {
            "table_name": "tesis.censo_nal.personas",
            "path": "/Volumes/tesis/censo_nal/personas/*.csv",
            "modulo": "personas"
        },
        {
            "table_name": "tesis.censo_nal.marco_georreferenciacion",
            "path": "/Volumes/tesis/censo_nal/marco_georreferenciacion/*.csv",
            "modulo": "marco_georreferenciacion"
        }
    ]
}

# COMMAND ----------

# DBTITLE 1,Cell 3
def cargar_tablas_bronce(
    spark, 
    tablas_config: dict,
    table_number:int = None,
    modulo: str = None
):
    for index, tabla in enumerate(tablas_config["config"]):

        if table_number != None:
            if table_number != index + 1:
                continue
        
        if modulo != None:
            if modulo != tabla["modulo"]:
                continue

        print(f"Cargando tabla {index + 1}")
        print(f"Cargando tabla {tabla['table_name']}")
        print(f"Path: {tabla['path']}")
    
        df= spark.read.option("header", "true").option("delimiter", ",").option("pathGlobFilter", "*.CSV").csv(tabla["path"].replace("*.csv", ""))
        df = df.select("*", "_metadata.file_name").withColumnRenamed("file_name", "archivo_origen")
        
        df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(tabla["table_name"])

        print("Tabla cargada")
        print("-"*50)

cargar_tablas_bronce(
    spark, 
    tablas_config
)