# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Consolidación de Mercado Laboral GEIH - Capa Oro
# MAGIC
# MAGIC Genera la tabla analítica final `tesis.geih_oro.mercado_laboral` consolidando
# MAGIC todas las tablas plata en una vista desnormalizada lista para análisis.
# MAGIC
# MAGIC ## Estrategia de joins
# MAGIC LEFT JOIN desde `caracteristicas_generales` (tabla base) hacia todas las demás,
# MAGIC preservando todas las personas aunque no tengan registros en otras tablas.
# MAGIC NULLs en indicadores laborales se reemplazan con 0 via `coalesce`.
# MAGIC
# MAGIC ## Ejemplo de uso
# MAGIC ```sql
# MAGIC SELECT PERIODO, DEPARTAMENTO,
# MAGIC        SUM(DESOCUPADO * FEX_C18) / SUM(PEA * FEX_C18) * 100 AS tasa_desempleo
# MAGIC FROM tesis.geih_oro.mercado_laboral
# MAGIC WHERE PEA = 1
# MAGIC GROUP BY PERIODO, DEPARTAMENTO
# MAGIC ```

# COMMAND ----------

# DBTITLE 1,Importación de librerías
import sys
import os

# Agregar el directorio padre (geih) al path para importar módulos shared
sys.path.insert(0, os.path.dirname(os.getcwd()))

from pyspark.sql.functions import col, coalesce, lit

from shared.config.geih_config import (
    TBL_CG_PLATA, TBL_FT_PLATA, TBL_NO_PLATA, TBL_OC_PLATA, TBL_FEX_PLATA,
    TBL_DIM_DIVIPOLA, TBL_MERCADO_LABORAL,
)
from shared.utils.spark_utils import escribir_tabla

# COMMAND ----------

# DBTITLE 1,Cargar tablas fuente
cg      = spark.table(TBL_CG_PLATA)
ft      = spark.table(TBL_FT_PLATA)
no      = spark.table(TBL_NO_PLATA)
oc      = spark.table(TBL_OC_PLATA)
fex     = spark.table(TBL_FEX_PLATA)
geih_div = spark.table(TBL_DIM_DIVIPOLA)

# COMMAND ----------

# DBTITLE 1,Consolidar y guardar tabla oro
df = (
    cg
    .join(ft,  cg.PK == ft.PK,  "left")
    .join(no,  cg.PK == no.PK,  "left")
    .join(fex, cg.PK == fex.PK, "left")
    .join(oc,  cg.PK == oc.PK,  "left")
    # dim_geih_divipola se une dos veces: una para departamento, otra para municipio
    .join(geih_div.alias("div_dep"), cg.CODIGO_DPTO == col("div_dep.CODIGO_DEPARTAMENTO"), "left")
    .join(geih_div.alias("div_mun"), cg.CODIGO_AREA == col("div_mun.CODIGO_AREA_GEIH"),    "left")
    .select(
        cg.PK,
        cg.PERIODO,
        cg.PER,
        cg.MES,
        cg.CODIGO_DPTO.alias("CODIGO_DEPARTAMENTO"),
        col("div_dep.DEPARTAMENTO"),
        col("div_mun.CODIGO_MUNICIPIO"),
        col("div_mun.MUNICIPIO"),
        cg.FEX,
        coalesce(fex["FEX_C18"], lit(0)).alias("FEX_C18"),
        cg.SEXO,
        cg.EDAD,
        coalesce(ft["PEA"].cast("int"),        lit(0)).alias("PEA"),
        coalesce(ft["PEI"].cast("int"),        lit(0)).alias("PEI"),
        coalesce(ft["PET"].cast("int"),        lit(0)).alias("PET"),
        coalesce(no["DESOCUPADO"].cast("int"), lit(0)).alias("DESOCUPADO"),
        coalesce(oc["OCUPADO"].cast("int"),    lit(0)).alias("OCUPADO"),
    )
)

escribir_tabla(df, TBL_MERCADO_LABORAL)
