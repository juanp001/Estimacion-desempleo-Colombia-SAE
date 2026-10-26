# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Transformación de Datos GEIH - Capa Plata (Silver)
# MAGIC
# MAGIC Consolida los datos bronce en tablas estandarizadas que unifican marco antiguo y
# MAGIC marco nuevo bajo una misma estructura de campos núcleo.
# MAGIC
# MAGIC ## Tablas generadas
# MAGIC | Tabla | Campos específicos |
# MAGIC |---|---|
# MAGIC | `caracteristicas_generales_consolidado` | SEXO, EDAD, ANO_NACIMIENTO, MES_NACIMIENTO |
# MAGIC | `fuerza_trabajo_consolidado` | PEA, PEI, PET |
# MAGIC | `no_ocupados_consolidado` | DESOCUPADO |
# MAGIC | `ocupados_consolidado` | OCUPADO |
# MAGIC | `dim_fex` | ANO, MES, FEX_C18 |
# MAGIC
# MAGIC ## Diferencias entre marcos
# MAGIC * **Marco nuevo**: PERIODO, MES y FEX_C18 vienen directamente de bronce.
# MAGIC * **Marco antiguo**: PERIODO y PER se extraen del nombre de archivo con regex;
# MAGIC   FEX_C_2011 requiere reemplazar comas por puntos.
# MAGIC
# MAGIC ## Uniones y llave (R-22)
# MAGIC * Marco nuevo y antiguo se unen por nombre (`unionByName`), no por posición: reordenar
# MAGIC   `CAMPOS_NUCLEO_*` ya no puede correr columnas sin error.
# MAGIC * `FEX` se castea a double en los dos marcos y `FEX_C18` de `dim_fex` recibe el mismo
# MAGIC   reemplazo de comas.
# MAGIC * `PK` = `PERIODO_DIRECTORIO_SECUENCIA_P_ORDEN` (con separador), igual en `dim_fex`.
# MAGIC
# MAGIC ## Lógica especial — fuerza de trabajo marco antiguo
# MAGIC LEFT JOIN entre fuerza_trabajo e inactivos: PEA = 1 si la persona no aparece
# MAGIC en la tabla de inactivos (PEI es NULL o vacío).

# COMMAND ----------

# DBTITLE 1,Importación de librerías

from pyspark.sql.functions import col, when, expr, regexp_replace

from shared.config.geih_config import (
    TBL_CG_BRONCE,
    TBL_FT_BRONCE,
    TBL_NO_BRONCE,
    TBL_OC_BRONCE,
    TBL_FEX_BRONCE,
    TBL_CG_CAB_MA,
    TBL_CG_RESTO_MA,
    TBL_FT_CAB_MA,
    TBL_FT_RESTO_MA,
    TBL_IN_CAB_MA,
    TBL_IN_RESTO_MA,
    TBL_NO_CAB_MA,
    TBL_NO_RESTO_MA,
    TBL_OC_CAB_MA,
    TBL_OC_RESTO_MA,
    TBL_CG_PLATA,
    TBL_FT_PLATA,
    TBL_NO_PLATA,
    TBL_OC_PLATA,
    TBL_FEX_PLATA,
)
from shared.transformations.campos_nucleo import (
    CAMPOS_NUCLEO_MARCO_NUEVO,
    CAMPOS_NUCLEO_MARCO_ANTIGUO,
    llave_persona,
)
from shared.utils.spark_utils import escribir_tabla

# COMMAND ----------

# MAGIC %md
# MAGIC # Características Generales

# COMMAND ----------

# DBTITLE 1,Características generales — marco nuevo
df_cg_plata = spark.table(TBL_CG_BRONCE).select(
    *CAMPOS_NUCLEO_MARCO_NUEVO,
    when(col("P3271") == 1, "MASCULINO")
    .when(col("P3271") == 2, "FEMENINO")
    .alias("SEXO"),
    col("P6040").cast("int").alias("EDAD"),
    col("P6030S3").cast("int").alias("ANO_NACIMIENTO"),
    col("P6030S1").cast("int").alias("MES_NACIMIENTO"),
)

# COMMAND ----------

# DBTITLE 1,Características generales — marco antiguo
# En marco antiguo los códigos de sexo vienen como string ("1", "2")
# y los demás campos pueden traer valores inválidos — se usa try_cast
select_fields_cg_antiguo = [
    when(col("P6020") == "1", "MASCULINO")
    .when(col("P6020") == "2", "FEMENINO")
    .alias("SEXO"),
    expr("try_cast(P6040 as int)").alias("EDAD"),
    expr("try_cast(P6030S3 as int)").alias("ANO_NACIMIENTO"),
    expr("try_cast(P6030S1 as int)").alias("MES_NACIMIENTO"),
]

df_cg_cabecera_plata = spark.table(TBL_CG_CAB_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, *select_fields_cg_antiguo
)
df_cg_resto_plata = spark.table(TBL_CG_RESTO_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, *select_fields_cg_antiguo
)

# Marco antiguo: solo cabecera y resto (R-21: la sección área no se carga en bronce)
df_cg_consolidado = df_cg_plata.unionByName(df_cg_cabecera_plata).unionByName(
    df_cg_resto_plata
)
escribir_tabla(df_cg_consolidado, TBL_CG_PLATA)

# COMMAND ----------

# MAGIC %md
# MAGIC # Fuerza de Trabajo

# COMMAND ----------

# DBTITLE 1,Fuerza de trabajo — marco nuevo
df_ft_plata = spark.table(TBL_FT_BRONCE).select(
    *CAMPOS_NUCLEO_MARCO_NUEVO,
    col("FT").alias("PEA"),
    col("FFT").alias("PEI"),
    col("PET"),
)

# COMMAND ----------

# DBTITLE 1,Fuerza de trabajo — marco antiguo
# El módulo FT solo trae personas de la PET: FT = "1" en todas las filas (en resto lo fija
# geih_bronce). R-21: en vez de normalizar "" → "1", se verifica que así sea.
df_ft_cabecera = spark.table(TBL_FT_CAB_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("FT").alias("PET")
)
df_ft_resto = spark.table(TBL_FT_RESTO_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("FT").alias("PET")
)
for nombre, df_ft in [("cabecera", df_ft_cabecera), ("resto", df_ft_resto)]:
    n_sin_pet = df_ft.filter(~col("PET").eqNullSafe("1")).count()
    if n_sin_pet:
        raise ValueError(
            f"Fuerza de trabajo {nombre}: {n_sin_pet} filas con FT distinto de '1'"
        )

df_i_cabecera = spark.table(TBL_IN_CAB_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("INI").alias("PEI")
)
df_i_resto = spark.table(TBL_IN_RESTO_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("INI").alias("PEI")
)

df_ft_ma = df_ft_cabecera.unionByName(df_ft_resto)
df_i_ma = df_i_cabecera.unionByName(df_i_resto)

# COMMAND ----------

# PEA = 1 si la persona NO aparece en inactivos (PEI es NULL o vacío)
df_ft_ma_plata = df_ft_ma.join(df_i_ma, "PK", "left").select(
    df_ft_ma["*"],
    df_i_ma["PEI"],
    when((df_i_ma["PEI"].isNull()) | (df_i_ma["PEI"] == ""), 1)
    .otherwise(0)
    .alias("PEA"),
)

df_ft_consolidado = df_ft_plata.unionByName(df_ft_ma_plata)
escribir_tabla(df_ft_consolidado, TBL_FT_PLATA)

# COMMAND ----------

# MAGIC %md
# MAGIC # No Ocupados

# COMMAND ----------

# DBTITLE 1,No ocupados — marco nuevo
df_no_plata = spark.table(TBL_NO_BRONCE).select(
    *CAMPOS_NUCLEO_MARCO_NUEVO,
    col("DSI").alias("DESOCUPADO"),
)

# COMMAND ----------

# DBTITLE 1,No ocupados — marco antiguo
df_no_cabecera_plata = spark.table(TBL_NO_CAB_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("DSI").alias("DESOCUPADO")
)
df_no_resto_plata = spark.table(TBL_NO_RESTO_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("DSI").alias("DESOCUPADO")
)

df_no_consolidado = df_no_plata.unionByName(df_no_cabecera_plata).unionByName(
    df_no_resto_plata
)
escribir_tabla(df_no_consolidado, TBL_NO_PLATA)

# COMMAND ----------

# MAGIC %md
# MAGIC # Ocupados

# COMMAND ----------

# DBTITLE 1,Ocupados — marco nuevo
df_oc_plata = spark.table(TBL_OC_BRONCE).select(
    *CAMPOS_NUCLEO_MARCO_NUEVO,
    col("OCI").alias("OCUPADO"),
)

# COMMAND ----------

# DBTITLE 1,Ocupados — marco antiguo
# Marco antiguo: solo cabecera y resto (R-21: la sección área no se carga en bronce)
df_oc_cabecera_plata = spark.table(TBL_OC_CAB_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("OCI").alias("OCUPADO")
)
df_oc_resto_plata = spark.table(TBL_OC_RESTO_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("OCI").alias("OCUPADO")
)

df_oc_consolidado = df_oc_plata.unionByName(df_oc_cabecera_plata).unionByName(
    df_oc_resto_plata
)
escribir_tabla(df_oc_consolidado, TBL_OC_PLATA)

# COMMAND ----------

# MAGIC %md
# MAGIC # Factores de Expansión

# COMMAND ----------

# DBTITLE 1,FEX — corrección y tipado
df_fex = spark.table(TBL_FEX_BRONCE).select(
    # R-22: misma llave que características generales (TIME_FEXC es el PERIODO AAAAMM)
    llave_persona(
        col("TIME_FEXC"), col("DIRECTORIO"), col("SECUENCIA_P"), col("ORDEN")
    ).alias("PK"),
    "DIRECTORIO",
    "SECUENCIA_P",
    "ORDEN",
    col("Ano").cast("int").alias("ANO"),
    col("Mes").cast("int").alias("MES"),
    regexp_replace(col("FEX_C18"), ",", ".").cast("double").alias("FEX_C18"),
)

escribir_tabla(df_fex, TBL_FEX_PLATA)
