# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Pre-filtrado de Covariables para Modelos SAE
# MAGIC
# MAGIC Este notebook reduce las ~1,582 covariables de TerriData a un subconjunto
# MAGIC manejable para los modelos SAE, aplicando tres filtros secuenciales:
# MAGIC
# MAGIC ## Etapas
# MAGIC
# MAGIC ### Etapa 1.1 — Datos faltantes
# MAGIC Con solo 23 dominios de estimación, cualquier NA en una covariable la inutiliza.
# MAGIC Se conservan únicamente las columnas con **0 NAs** en los 23 registros.
# MAGIC
# MAGIC ### Etapa 1.2 — Varianza casi cero
# MAGIC Variables constantes producen **singularidad en la matriz de diseño** (colinealidad
# MAGIC con el intercepto), impidiendo la estimación de coeficientes. Se eliminan columnas
# MAGIC con varianza < `UMBRAL_VARIANZA` (ver `shared/config.py`).
# MAGIC
# MAGIC ### Etapa 2 — Correlación con variable objetivo
# MAGIC De las sobrevivientes se seleccionan las que tienen correlación de Pearson
# MAGIC absoluta ≥ `CORR_VALOR` con `TASA_DESEMPLEO_PCT`.
# MAGIC Dos estrategias disponibles (configuradas en `shared/config.py`):
# MAGIC * **threshold**: Variables con |r| ≥ umbral (estrategia activa por defecto)
# MAGIC * **top_n**: Las N variables con mayor correlación absoluta
# MAGIC
# MAGIC ## Parámetros (en `shared/config.py`)
# MAGIC
# MAGIC | Parámetro | Valor | Descripción |
# MAGIC |-----------|-------|-------------|
# MAGIC | `VARIABLE_OBJETIVO` | `"TASA_DESEMPLEO_PCT"` | Variable a predecir |
# MAGIC | `UMBRAL_VARIANZA` | `0.00001` | Varianza mínima aceptable |
# MAGIC | `CORR_MODO` | `"threshold"` | Estrategia de selección |
# MAGIC | `CORR_VALOR` | `0.4` | Umbral de correlación absoluta |
# MAGIC
# MAGIC ## Referencias
# MAGIC
# MAGIC * Rao, J.N.K. & Molina, I. (2015). *Small Area Estimation* (2nd ed.). Wiley.
# MAGIC * DANE (2020). "Guía de calidad de estimaciones para encuestas de hogares".

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
import pandas as pd
from shared.config import *
from shared.feature_selection import (
    filtrar_columnas_sin_na,
    filtrar_varianza_cero,
    seleccionar_variables_por_correlacion,
)

# COMMAND ----------

# DBTITLE 1,Cargar datos y aislar covariables
df_spark = spark.read.table(TBL_COVARIABLES)
df = df_spark.toPandas()

covariables_cols = [c for c in df.columns if c not in METADATA_COLS]
df_covariables = df[covariables_cols].copy()

# Homogenizar tipos: forzar a numérico, textos no parseables → NaN
for col in df_covariables.select_dtypes(include=["object"]).columns:
    df_covariables[col] = pd.to_numeric(df_covariables[col], errors="coerce")

print(f"Covariables candidatas iniciales: {len(covariables_cols)}")

# COMMAND ----------

# DBTITLE 1,Etapa 1.1 — Filtro datos faltantes
df_sin_na = filtrar_columnas_sin_na(df_covariables)

# COMMAND ----------

# MAGIC %md
# MAGIC De las ~1.582 variables originales, solo ~530 están completamente llenas
# MAGIC para los 23 dominios. Las demás se descartan porque introducen vacíos de
# MAGIC información que desestabilizan los cálculos.

# COMMAND ----------

# DBTITLE 1,Etapa 1.2 — Filtro varianza casi cero
df_filtrado = filtrar_varianza_cero(df_sin_na, umbral=UMBRAL_VARIANZA)

# COMMAND ----------

# MAGIC %md
# MAGIC Introducir una variable constante en la regresión del modelo Fay-Herriot
# MAGIC produce singularidad en la matriz de diseño (colinealidad con el intercepto).
# MAGIC El umbral `0.00001` permite tolerar tasas muy pequeñas con variación real,
# MAGIC eliminando solo las verdaderamente constantes.

# COMMAND ----------

# DBTITLE 1,Etapa 2 — Selección por correlación con variable objetivo
df_diccionario = spark.read.table(TBL_DIM_INDICADORES).toPandas()
df_diccionario["CODIGO_INDICADOR"] = df_diccionario["CODIGO_INDICADOR"].astype(str)

variables_ganadoras, df_reporte = seleccionar_variables_por_correlacion(
    df_covariables=df_filtrado,
    df_metadata=df,
    variable_objetivo=VARIABLE_OBJETIVO,
    df_diccionario=df_diccionario,
    modo=CORR_MODO,
    valor=CORR_VALOR,
)

# COMMAND ----------

# DBTITLE 1,Escritura de variables prefiltradas
df_output = pd.concat(
    [df[METADATA_COLS], df[variables_ganadoras]],
    axis=1,
)

spark.createDataFrame(df_output).write.mode("overwrite").option(
    "mergeSchema", "true"
).saveAsTable(TBL_PREFILTRADAS)

print(f"Tabla escrita: {TBL_PREFILTRADAS}  ({len(variables_ganadoras)} covariables prefiltradas)")
display(df_reporte)
