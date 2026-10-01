# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Tasa de desempleo municipal desde el Censo
# MAGIC
# MAGIC Calcula la tasa de desempleo de los municipios de Cauca y Valle del Cauca con el
# MAGIC **Censo Nacional** (conteo completo) en lugar de la GEIH. Añade la **varianza**
# MAGIC binomial `p(1-p)/PEA` (en pp²), el error estándar y el **coeficiente de variación**.
# MAGIC
# MAGIC ```
# MAGIC tesis.censo_nal.personas → PET / PEA / OCUPADOS / DESOCUPADOS / INACTIVOS por municipio
# MAGIC   → tesis.censo_nal.tasa_desempleo
# MAGIC ```
# MAGIC
# MAGIC El período (`PER`, `MES`) se mantiene en 2018-12 para coincidir con las covariables.

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
from shared.config import *
from shared.tasa_censal import calcular_tasa_desempleo_censal

# COMMAND ----------

# DBTITLE 1,Calcular tasa de desempleo censal
resultado = calcular_tasa_desempleo_censal(
    spark.table(TBL_PERSONAS_CENSO),
    spark.table(TBL_DIM_DIVIPOLA),
    DEPARTAMENTOS_CENSO,
    PER_ESTIMACION,
    MES_ESTIMACION,
).cache()

print(f"Municipios: {resultado.count()}")
print(f"Sin nombre en dim_divipola: {resultado.filter('MUNICIPIO IS NULL').count()}")
print(f"Con PEA = 0: {resultado.filter('PEA = 0').count()}")
print(f"Con tasa 0 (CV indefinido): {resultado.filter('TASA_DESEMPLEO_PCT = 0').count()}")
display(resultado)

# COMMAND ----------

# DBTITLE 1,Exportar a Unity Catalog
(
    resultado.write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TBL_ESTIMACION_DIRECTA)
)
print(f"Tabla escrita: {TBL_ESTIMACION_DIRECTA}")
