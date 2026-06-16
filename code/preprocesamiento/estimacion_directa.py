# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Estimación Directa de Tasa de Desempleo Municipal con Bootstrap
# MAGIC
# MAGIC Este notebook implementa **estimación directa de áreas pequeñas** (municipios) usando el **estimador de Hájek** con inferencia basada en **bootstrap simple**.
# MAGIC
# MAGIC ## Propósito
# MAGIC
# MAGIC Calcular estimaciones de **tasa de desempleo por municipio** a partir de microdatos de la GEIH, incluyendo:
# MAGIC * **Estimación puntual**: Tasa de desempleo (porcentaje)
# MAGIC * **Medidas de precisión**: Error estándar, intervalos de confianza 95%, coeficiente de variación
# MAGIC * **Inferencia estadística**: Basada en bootstrap simple (600 réplicas)
# MAGIC
# MAGIC ## ¿Qué es Estimación Directa?
# MAGIC
# MAGIC La **estimación directa** usa **solo los datos de la muestra del dominio de interés** (en este caso, el municipio) para calcular la estimación, sin "pedir prestada" información de otros dominios.
# MAGIC
# MAGIC ### Ventajas:
# MAGIC ✅ **Simple y transparente**: Usa solo datos locales
# MAGIC ✅ **Sin supuestos de modelo**: No asume relaciones con covariables
# MAGIC ✅ **Fácil de interpretar**: Es el estimador "natural"
# MAGIC
# MAGIC ### Desventajas:
# MAGIC ❌ **Alta variabilidad en áreas pequeñas**: Muestras chicas → errores grandes
# MAGIC ❌ **Intervalos de confianza amplios**: Poca precisión para municipios pequeños
# MAGIC ❌ **Coeficientes de variación altos**: CV > 30% son comunes en municipios pequeños
# MAGIC ❌ **Imposible estimar dominios con muestra cero**: Sin observaciones → sin estimación
# MAGIC
# MAGIC ### ¿Cuándo usar estimación directa?
# MAGIC
# MAGIC **Usar cuando**:
# MAGIC * El dominio tiene **muestra suficiente** (n ≥ 30 típicamente)
# MAGIC * El **CV es aceptable** (< 15% ideal, < 30% aceptable)
# MAGIC * Se requiere **transparencia metodológica**
# MAGIC * Es el **baseline** para comparar con métodos SAE
# MAGIC
# MAGIC **NO usar cuando**:
# MAGIC * El dominio tiene muestra muy pequeña (n < 10)
# MAGIC * El CV es muy alto (> 30%)
# MAGIC * Se requieren estimaciones para **todos** los municipios (incluso sin muestra)
# MAGIC
# MAGIC ## Estimador de Hájek
# MAGIC
# MAGIC El **estimador de Hájek** es un estimador de **razón** que ajusta por los pesos muestrales:
# MAGIC
# MAGIC ```
# MAGIC θ̂ = Σ(w_i × y_i) / Σ(w_i)
# MAGIC ```
# MAGIC
# MAGIC Donde:
# MAGIC * `w_i`: Peso de expansión (FEX) de la observación i
# MAGIC * `y_i`: Variable binaria (1 = desocupado, 0 = ocupado)
# MAGIC
# MAGIC Para muestras grandes es aproximadamente insesgado, consistente y asintóticamente normal.
# MAGIC Para muestras pequeñas (áreas pequeñas) puede tener alta variabilidad.
# MAGIC
# MAGIC ## Bootstrap Simple (Naive Bootstrap)
# MAGIC
# MAGIC **Procedimiento**:
# MAGIC 1. Calcular θ̂ en la muestra original
# MAGIC 2. Crear B réplicas: remuestrear n obs. **con reemplazo** y calcular θ̂_b
# MAGIC 3. SE = desv. estándar de {θ̂_1, ..., θ̂_B}
# MAGIC 4. IC 95% = [percentil 2.5%, percentil 97.5%]
# MAGIC
# MAGIC **Número de réplicas**: B = 2000 (ver `shared/config.py`).
# MAGIC Literatura recomienda B ≥ 500 para SE y B ≥ 1000 para IC.
# MAGIC
# MAGIC ## Parámetros Configurables
# MAGIC
# MAGIC Ver `shared/config.py`:
# MAGIC * `BOOTSTRAP_REPLICAS`: Número de réplicas (default 2000)
# MAGIC * `BOOTSTRAP_SEED`: Semilla aleatoria (default 42)
# MAGIC * `PER_ESTIMACION`, `MES_ESTIMACION`: Período a estimar
# MAGIC * `GRUPO_COLS`: Columnas que definen los dominios
# MAGIC
# MAGIC ## Interpretación del CV
# MAGIC
# MAGIC ```
# MAGIC CV = (SE / Estimación) × 100
# MAGIC ```
# MAGIC
# MAGIC * **CV < 15%**: Estimación CONFIABLE ✅
# MAGIC * **15% ≤ CV < 30%**: Estimación ACEPTABLE ⚠️
# MAGIC * **CV ≥ 30%**: Estimación NO CONFIABLE ❌
# MAGIC
# MAGIC ## Flujo de Datos
# MAGIC
# MAGIC ```
# MAGIC tesis.geih_oro.mercado_laboral
# MAGIC   → filter(MUNICIPIO not null, PEA == 1, PER == 2018, MES == 12)
# MAGIC   → EstimacionDirecta.estimar()   [bootstrap 2000 réplicas]
# MAGIC   → tesis.modelo.tasa_desempleo_municipal
# MAGIC ```
# MAGIC
# MAGIC ## Referencias
# MAGIC
# MAGIC * Hájek, J. (1971). "Comment on 'An essay on the logical foundations of survey sampling'".
# MAGIC * Efron, B. & Tibshirani, R. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
# MAGIC * DANE (2020). "Guía de calidad de estimaciones para encuestas de hogares".

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
%pip install tqdm
from pyspark.sql import functions as F
from shared.config import *
from shared.estimador_sae import EstimacionDirecta

# COMMAND ----------

# DBTITLE 1,Cargar y filtrar datos GEIH
df_desempleo = (
    spark.table(TBL_MERCADO_LABORAL)
    .filter(
        F.col("MUNICIPIO").isNotNull() &
        (F.col("PEA") == 1) &
        (F.col("PER") == PER_ESTIMACION) &
        (F.col("MES") == MES_ESTIMACION)
    )
)

print(f"Observaciones PEA: {df_desempleo.count():,}")
print(f"Municipios con muestra: {df_desempleo.select('CODIGO_MUNICIPIO').distinct().count()}")

# COMMAND ----------

# DBTITLE 1,Ejecutar estimación directa con bootstrap
estimador = EstimacionDirecta(spark, num_replicas=BOOTSTRAP_REPLICAS, seed=BOOTSTRAP_SEED)

resultado = estimador.estimar(
    dataframe=df_desempleo,
    grupo_cols=GRUPO_COLS,
    agregacion_anual=False,
)

# COMMAND ----------

# DBTITLE 1,Resumen de resultados
print(f"Municipios estimados: {len(resultado)}")
print(f"Período: {resultado['PER'].iloc[0]}-{resultado['MES'].iloc[0]:02d}\n")

confiables = (resultado["CV_PORCENTAJE"] < CV_CONFIABLE).sum()
aceptables = ((resultado["CV_PORCENTAJE"] >= CV_CONFIABLE) & (resultado["CV_PORCENTAJE"] < CV_ACEPTABLE)).sum()
no_conf    = (resultado["CV_PORCENTAJE"] >= CV_ACEPTABLE).sum()

print(f"Calidad de estimaciones (CV):")
print(f"  Confiables  (CV < {CV_CONFIABLE}%): {confiables}")
print(f"  Aceptables  ({CV_CONFIABLE}% ≤ CV < {CV_ACEPTABLE}%): {aceptables}")
print(f"  No confiables (CV ≥ {CV_ACEPTABLE}%): {no_conf}")

display(resultado)

# COMMAND ----------

# DBTITLE 1,Exportar a Unity Catalog
estimador.exportar(
    tabla_destino=TBL_ESTIMACION_DIRECTA,
    tabla_origen=TBL_MERCADO_LABORAL,
)
