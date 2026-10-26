# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Tabla Dimensional GEIH-DIVIPOLA - Traducción del AREA de la GEIH a municipio
# MAGIC
# MAGIC Crea `tesis.dim.dim_geih_divipola`: una fila por cada una de las **32 capitales** de la GEIH,
# MAGIC con el código `CODIGO_AREA_GEIH` que trae la encuesta en el campo `AREA`.
# MAGIC
# MAGIC ## Qué es `CODIGO_AREA_GEIH`
# MAGIC
# MAGIC En los microdatos de la GEIH el campo `AREA` es el código de **departamento** de la ciudad
# MAGIC (`76` = Cali A.M.), y cada departamento tiene una sola ciudad en la muestra. Por eso
# MAGIC `CODIGO_AREA_GEIH` es igual a `CODIGO_DEPARTAMENTO` de la capital, y el mapeo `AREA` → capital
# MAGIC es correcto: con él la estimación directa de los 23 dominios con muestra coincide con la que
# MAGIC publica el DANE (anexo «Mercado laboral según proyecciones CNPV 2018»).
# MAGIC
# MAGIC ## De dónde sale la lista de capitales (R-24)
# MAGIC
# MAGIC Las capitales se definen **una sola vez**, en `DOMINIOS_GEIH` de `dim_dominio_geih.py` (DANE,
# MAGIC Metodología GEIH v9, PDF 9-10: 13 ciudades con A.M., 11 intermedias y 8 capitales nuevas).
# MAGIC Este notebook toma las filas `ES_CAPITAL` de `tesis.dim.dim_dominio_geih` y les agrega las
# MAGIC coordenadas de `tesis.dim.dim_divipola`; por eso en el job `dimensiones` corre después de
# MAGIC `dim_dominio_geih`. Antes la lista estaba escrita a mano en los dos notebooks.
# MAGIC
# MAGIC Validaciones: 32 filas y un `CODIGO_AREA_GEIH` distinto por fila (si dos capitales
# MAGIC compartieran departamento, el join de `geih_oro` duplicaría personas).
# MAGIC
# MAGIC ## Columnas
# MAGIC * `CODIGO_DEPARTAMENTO`, `DEPARTAMENTO`: departamento de la capital
# MAGIC * `CODIGO_AREA_GEIH`: código `AREA` de la GEIH (= `CODIGO_DEPARTAMENTO`)
# MAGIC * `CODIGO_MUNICIPIO`, `MUNICIPIO`: la capital (Bogotá D.C. con `11001`; Yopal con `85001`)
# MAGIC * `LONGITUD`, `LATITUD`
# MAGIC
# MAGIC ## Uso
# MAGIC `geih_oro` la une por `CODIGO_AREA` para asignar `CODIGO_MUNICIPIO` y `MUNICIPIO` (constante
# MAGIC `TBL_DIM_DIVIPOLA`). Fuera de estas 32 áreas `MUNICIPIO` queda NULL. El nombre del departamento
# MAGIC ya no sale de aquí sino de `dim_divipola` (R-24), así que no queda NULL en departamentos sin
# MAGIC capital en la lista (p. ej. Cundinamarca, 25). `preprocesamiento` la usa para traer el código
# MAGIC de área de cada dominio.

# COMMAND ----------

# DBTITLE 1,Importación de librerías
from pyspark.sql.functions import col

# COMMAND ----------

# DBTITLE 1,Crear tabla dimensional GEIH
N_CAPITALES = 32

capitales = (
    spark.table("tesis.dim.dim_dominio_geih")
    .filter(col("ES_CAPITAL"))
    .select("CODIGO_MUNICIPIO")
)

df_geih_divipola = (
    spark.table("tesis.dim.dim_divipola")
    .join(capitales, "CODIGO_MUNICIPIO", "inner")
    .select(
        "CODIGO_DEPARTAMENTO",
        "DEPARTAMENTO",
        # El AREA de la GEIH es el código de departamento de la ciudad
        col("CODIGO_DEPARTAMENTO").alias("CODIGO_AREA_GEIH"),
        "CODIGO_MUNICIPIO",
        "MUNICIPIO",
        "LONGITUD",
        "LATITUD",
    )
)

n_filas = df_geih_divipola.count()
n_areas = df_geih_divipola.select("CODIGO_AREA_GEIH").distinct().count()
if n_filas != N_CAPITALES or n_areas != N_CAPITALES:
    raise ValueError(
        f"Se esperaban {N_CAPITALES} capitales con CODIGO_AREA_GEIH único; "
        f"hay {n_filas} filas y {n_areas} códigos de área"
    )
print(f"Capitales GEIH: {n_filas}  |  códigos de área distintos: {n_areas}")

# COMMAND ----------

# DBTITLE 1,Guardar tabla dimensional
df_geih_divipola.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.dim.dim_geih_divipola"
)
print("Tabla escrita: tesis.dim.dim_geih_divipola")
