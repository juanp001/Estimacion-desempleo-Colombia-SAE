# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Adición de Covariables para Modelos SAE - Tabla de Estimaciones Enriquecidas
# MAGIC
# MAGIC Este notebook crea la tabla **`tesis.modelo.tasa_desempleo_covariables`** que combina las **estimaciones directas de tasa de desempleo municipal** con **covariables socioeconómicas de TerriData** para modelado de Small Area Estimation (SAE).
# MAGIC
# MAGIC ## Propósito
# MAGIC
# MAGIC Facilitar la **experimentación y desarrollo de modelos SAE** proporcionando una tabla única que integra:
# MAGIC * **Variable dependiente**: Tasa de desempleo municipal (estimación directa)
# MAGIC * **Medidas de precisión**: Error estándar, intervalos de confianza, CV
# MAGIC * **Covariables auxiliares**: ~1,584 indicadores de TerriData (población, educación, salud, infraestructura, etc.)
# MAGIC
# MAGIC ## Tablas Fuente
# MAGIC
# MAGIC | Tabla | Contenido |
# MAGIC |-------|-----------|
# MAGIC | `tesis.modelo.tasa_desempleo_municipal` | Estimaciones directas por municipio (23 filas, 12 cols) |
# MAGIC | `tesis.terridata.terridata_extendido_plata` | Indicadores TerriData — formato ancho (~1,584 indicadores) |
# MAGIC
# MAGIC ## Estrategia de Join: LEFT JOIN
# MAGIC
# MAGIC ```
# MAGIC Estimaciones (23 municipios)
# MAGIC   LEFT JOIN TerriData
# MAGIC   ON CODIGO_MUNICIPIO = CODIGO_ENTIDAD AND PER = ANO AND MES = MES
# MAGIC   → tesis.modelo.tasa_desempleo_covariables (23 filas × ~1,590 cols)
# MAGIC ```
# MAGIC
# MAGIC LEFT JOIN preserva todas las estimaciones aunque un municipio no tenga
# MAGIC covariables en TerriData (valores NULL en ese caso).
# MAGIC
# MAGIC ## Columnas excluidas de TerriData
# MAGIC
# MAGIC Se descartan las que ya existen en las estimaciones para evitar duplicados:
# MAGIC `CODIGO_DEPARTAMENTO`, `DEPARTAMENTO`, `CODIGO_ENTIDAD`, `ENTIDAD`, `ANO`, `MES`.
# MAGIC
# MAGIC ## Interpretación del CV (columna heredada de estimación directa)
# MAGIC
# MAGIC * CV < 15%: Estimación **confiable** ✅
# MAGIC * 15% ≤ CV < 30%: Estimación **aceptable** ⚠️
# MAGIC * CV ≥ 30%: Estimación **no confiable** ❌
# MAGIC
# MAGIC ## Referencias
# MAGIC
# MAGIC * Rao, J.N.K. & Molina, I. (2015). *Small Area Estimation* (2nd ed.). Wiley.
# MAGIC * TerriData - DNP: https://terridata.dnp.gov.co/

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
from pyspark.sql import functions as F
from shared.config import *

# COMMAND ----------

# DBTITLE 1,Cargar tablas fuente
print("Leyendo estimaciones directas...")
df_estimaciones = spark.table(TBL_ESTIMACION_DIRECTA)
print(f"  {df_estimaciones.count()} filas — {len(df_estimaciones.columns)} columnas")

print("\nLeyendo covariables TerriData...")
df_terridata = spark.table(TBL_TERRIDATA)
print(f"  {df_terridata.count()} filas — {len(df_terridata.columns)} columnas")

# COMMAND ----------

# DBTITLE 1,Preparar columnas de TerriData
# Conservar solo columnas de indicadores (excluir las que ya existen en estimaciones)
columnas_indicadores = [c for c in df_terridata.columns if c not in COLUMNAS_EXCLUIR_JOIN]

# Incluir columnas de join junto con los indicadores
df_terridata_sel = df_terridata.select("CODIGO_ENTIDAD", "ANO", "MES", *columnas_indicadores)

print(f"Covariables seleccionadas de TerriData: {len(columnas_indicadores)}")

# COMMAND ----------

# DBTITLE 1,LEFT JOIN estimaciones × covariables
df_final = (
    df_estimaciones
    .join(
        df_terridata_sel,
        (df_estimaciones.CODIGO_MUNICIPIO == df_terridata_sel.CODIGO_ENTIDAD) &
        (df_estimaciones.PER              == df_terridata_sel.ANO)            &
        (df_estimaciones.MES              == df_terridata_sel.MES),
        how="left",
    )
    .drop("CODIGO_ENTIDAD", "ANO", df_terridata_sel.MES)
)

print(f"Resultado: {df_final.count()} filas — {len(df_final.columns)} columnas")
print(f"  Identificación + estimación: 12")
print(f"  Covariables TerriData: {len(df_final.columns) - 12}")

# COMMAND ----------

# DBTITLE 1,Exportar a Unity Catalog
df_final.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(TBL_COVARIABLES)

print(f"✔ Tabla creada: {TBL_COVARIABLES}")
print(f"  Acceso: SELECT * FROM {TBL_COVARIABLES}")
