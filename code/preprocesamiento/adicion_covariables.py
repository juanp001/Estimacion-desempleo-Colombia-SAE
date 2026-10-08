# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Adición de Covariables para Modelos SAE - Tabla de Estimaciones Enriquecidas
# MAGIC
# MAGIC Este notebook crea la tabla **`tesis.preprocesamiento.tasa_desempleo_covariables`** que combina las **estimaciones directas de tasa de desempleo por dominio** (ciudad o ciudad A.M.) con **covariables socioeconómicas de TerriData agregadas al mismo dominio** para modelado de Small Area Estimation (SAE).
# MAGIC
# MAGIC ## Propósito
# MAGIC
# MAGIC Facilitar la **experimentación y desarrollo de modelos SAE** proporcionando una tabla única que integra:
# MAGIC * **Variable dependiente**: Tasa de desempleo por dominio (estimación directa)
# MAGIC * **Medidas de precisión**: Error estándar, intervalos de confianza, CV
# MAGIC * **Covariables auxiliares**: ~1,584 indicadores de TerriData (población, educación, salud, infraestructura, etc.)
# MAGIC
# MAGIC ## Tablas Fuente
# MAGIC
# MAGIC | Tabla | Contenido |
# MAGIC |-------|-----------|
# MAGIC | `tesis.preprocesamiento.tasa_desempleo_municipal` | Estimaciones directas por dominio (23 filas) |
# MAGIC | `tesis.terridata.terridata_extendido_plata` | Indicadores TerriData por municipio — formato ancho (~1,584 indicadores) |
# MAGIC | `tesis.dim.dim_dominio_geih` | Municipios que forman cada dominio (ciudad o ciudad A.M.) |
# MAGIC
# MAGIC ## Agregación de las covariables al dominio
# MAGIC
# MAGIC La tasa de un dominio con área metropolitana describe a todos sus municipios (Cali A.M. = Cali +
# MAGIC Yumbo), así que cada indicador se agrega sobre los municipios miembro con un promedio ponderado
# MAGIC por la población de 15 años y más (`EXPR_PESO_POBLACION`, PET de la GEIH CNPV 2018, aproximación
# MAGIC de la PEA):
# MAGIC
# MAGIC ```
# MAGIC x̄_D = Σ_{m∈D} w_m · x_m / Σ_{m∈D} w_m
# MAGIC ```
# MAGIC
# MAGIC En los 16 dominios de un solo municipio el resultado es el valor del municipio. La sustentación
# MAGIC (Morales et al., 2021, p. 425: `x_d` son valores agregados del área; coherencia con la tasa
# MAGIC ponderada por PEA) está en `shared/agregacion_dominios.py`.
# MAGIC
# MAGIC ## Estrategia de Join: LEFT JOIN
# MAGIC
# MAGIC ```
# MAGIC Estimaciones (23 dominios)
# MAGIC   LEFT JOIN TerriData agregada por dominio
# MAGIC   ON CODIGO_DOMINIO AND PER = ANO AND MES = MES
# MAGIC   → tesis.preprocesamiento.tasa_desempleo_covariables (23 filas × ~1,590 cols)
# MAGIC ```
# MAGIC
# MAGIC LEFT JOIN preserva todas las estimaciones aunque un dominio no tenga covariables en TerriData
# MAGIC (valores NULL en ese caso).
# MAGIC
# MAGIC ## Columnas excluidas de TerriData
# MAGIC
# MAGIC Se descartan las que ya existen en las estimaciones o que no son indicadores:
# MAGIC `CODIGO_DEPARTAMENTO`, `DEPARTAMENTO`, `CODIGO_ENTIDAD`, `ENTIDAD`, `ANO`, `MES` y las columnas
# MAGIC `*_NORMALIZADO`.
# MAGIC
# MAGIC ## Interpretación del CV (columna heredada de estimación directa)
# MAGIC
# MAGIC * CV < 5%: Estimación **confiable** ✅
# MAGIC * 5% ≤ CV < 20%: Estimación **aceptable** ⚠️
# MAGIC * CV ≥ 20%: Estimación **no confiable** ❌
# MAGIC
# MAGIC ## Referencias
# MAGIC
# MAGIC * Morales, D., Esteban, M. D., Pérez, A. & Hobza, T. (2021). *A Course on Small Area Estimation and Mixed Models*. Springer.
# MAGIC * Rao, J.N.K. & Molina, I. (2015). *Small Area Estimation* (2nd ed.). Wiley.
# MAGIC * TerriData - DNP: https://terridata.dnp.gov.co/

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
import os
import sys

from pyspark.sql import functions as F


def _directorio_codigo() -> str:
    """Ruta absoluta de `code/`, tanto en ejecución interactiva como en un job.

    Returns:
        str: Ruta del directorio `code/` del repositorio.
    """
    try:
        contexto = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
        return "/Workspace" + os.path.dirname(
            os.path.dirname(contexto.notebookPath().get())
        )
    except Exception:
        return os.path.dirname(os.getcwd())


CODE_DIR = _directorio_codigo()
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from preprocesamiento.shared.config import *
from preprocesamiento.shared.agregacion_dominios import agregar_covariables_dominio

# COMMAND ----------

# DBTITLE 1,Cargar tablas fuente
print("Leyendo estimaciones directas...")
df_estimaciones = spark.table(TBL_ESTIMACION_DIRECTA)
print(f"  {df_estimaciones.count()} filas — {len(df_estimaciones.columns)} columnas")

print("\nLeyendo covariables TerriData...")
df_terridata = spark.table(TBL_TERRIDATA)
print(f"  {df_terridata.count()} filas — {len(df_terridata.columns)} columnas")

# Solo los dominios con estimación directa: los demás (San Andrés y las capitales de los nuevos
# departamentos, sin muestra en los microdatos) no se modelan y algunos no tienen el peso en
# TerriData (88001), que haría fallar la agregación sin necesidad.
df_dim_dominio = spark.table(TBL_DIM_DOMINIO).join(
    df_estimaciones.select("CODIGO_DOMINIO").distinct(),
    on="CODIGO_DOMINIO",
    how="inner",
)

# COMMAND ----------

# DBTITLE 1,Verificar que TerriData cubra el período estimado
# El período lo fija estimacion_directa (parámetros anio_estimacion / mes_estimacion). Si TerriData
# no tiene ese ANO/MES, el LEFT JOIN dejaría todas las covariables en NULL sin avisar.
periodos_estimados = [
    (fila["PER"], fila["MES"])
    for fila in df_estimaciones.select(
        F.col("PER").cast("int").alias("PER"), F.col("MES").cast("int").alias("MES")
    )
    .distinct()
    .collect()
]
periodos_terridata = {
    (fila["ANO"], fila["MES"])
    for fila in df_terridata.select(
        F.col("ANO").cast("int").alias("ANO"), F.col("MES").cast("int").alias("MES")
    )
    .distinct()
    .collect()
}
sin_cobertura = [p for p in periodos_estimados if p not in periodos_terridata]

if sin_cobertura:
    raise ValueError(
        f"TerriData no tiene datos para el período estimado (ANO, MES) = {sin_cobertura}. "
        f"Períodos disponibles en {TBL_TERRIDATA}: {sorted(periodos_terridata)}."
    )

# COMMAND ----------

# DBTITLE 1,Preparar columnas de TerriData
# Solo columnas de indicadores: se excluyen las de identificación (ya existen en las estimaciones) y
# las de texto normalizado, que no son covariables.
columnas_indicadores = [
    c
    for c in df_terridata.columns
    if c not in COLUMNAS_EXCLUIR_JOIN and c not in METADATA_COLS
]

print(f"Covariables seleccionadas de TerriData: {len(columnas_indicadores)}")

# COMMAND ----------

# DBTITLE 1,Agregar las covariables municipales al dominio
# Un bloque por período estimado (normalmente uno). Promedio ponderado por la población de 15 años
# y más sobre los municipios de cada dominio; ver shared/agregacion_dominios.py.
df_terridata_dominio = None
for per, mes in periodos_estimados:
    df_periodo = agregar_covariables_dominio(
        df_terridata,
        df_dim_dominio,
        columnas_indicadores,
        EXPR_PESO_POBLACION,
        per,
        mes,
    )
    df_terridata_dominio = (
        df_periodo
        if df_terridata_dominio is None
        else df_terridata_dominio.unionByName(df_periodo)
    )

print(
    "Dominios con varios municipios (covariables agregadas): "
    f"{df_estimaciones.filter(F.col('TIPO_DOMINIO') == 'CIUDAD_AM').count()}"
)

# COMMAND ----------

# DBTITLE 1,LEFT JOIN estimaciones × covariables agregadas
df_final = (
    df_estimaciones.alias("est")
    .join(
        df_terridata_dominio.alias("td"),
        (F.col("est.CODIGO_DOMINIO") == F.col("td.CODIGO_DOMINIO"))
        & (F.col("est.PER").cast("int") == F.col("td.ANO").cast("int"))
        & (F.col("est.MES").cast("int") == F.col("td.MES").cast("int")),
        how="left",
    )
    .select("est.*", *[F.col(f"td.`{c}`") for c in columnas_indicadores])
)

n_ident = len(df_estimaciones.columns)
print(f"Resultado: {df_final.count()} filas — {len(df_final.columns)} columnas")
print(f"  Identificación + estimación: {n_ident}")
print(f"  Covariables TerriData: {len(df_final.columns) - n_ident}")

# COMMAND ----------

# DBTITLE 1,Exportar a Unity Catalog
df_final.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_COVARIABLES
)

print(f"✔ Tabla creada: {TBL_COVARIABLES}")
print(f"  Acceso: SELECT * FROM {TBL_COVARIABLES}")
