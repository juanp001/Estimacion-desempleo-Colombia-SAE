# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Dominios objetivo sin cobertura muestral — versión revisada
# MAGIC
# MAGIC Construye la tabla de covariables de los municipios de Cauca y Valle del Cauca sobre
# MAGIC los que se producirán estimaciones sintéticas, es decir, aquellos donde la GEIH no
# MAGIC tiene muestra y por tanto no existe estimación directa.
# MAGIC
# MAGIC ## Por qué existe este notebook
# MAGIC
# MAGIC La versión original consume `tesis.modelo.municipios_sin_encuesta`, una tabla que
# MAGIC **ningún notebook del repositorio construye** y que contiene solo cinco covariables,
# MAGIC ya renombradas a los alias del conjunto seleccionado en su momento. Eso tiene dos
# MAGIC consecuencias: el paso de predicción sintética no es reproducible desde el código, y
# MAGIC queda acoplado a un conjunto concreto de covariables, de modo que cualquier cambio en
# MAGIC la selección lo rompe.
# MAGIC
# MAGIC Aquí la tabla se deriva de las fuentes, con **todas** las covariables que superaron el
# MAGIC pre-filtrado y conservando los códigos de indicador. El notebook del modelo toma
# MAGIC después las que necesite y las renombra, de forma que la predicción sintética funciona
# MAGIC con cualquier conjunto seleccionado.
# MAGIC
# MAGIC ## Definición de los dominios
# MAGIC
# MAGIC Municipios de los departamentos objetivo presentes en TerriData para el período de
# MAGIC estimación, **excluyendo** aquellos que sí tienen estimación directa. La exclusión se
# MAGIC hace por código DIVIPOLA y no por nombre, evitando el cotejo de cadenas de texto.
# MAGIC
# MAGIC ## Salida
# MAGIC
# MAGIC * `tesis.preprocesamiento.municipios_sin_encuesta_rev`

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
import os
import sys

from pyspark.sql import functions as F


def _directorio_codigo() -> str:
    """Ruta absoluta de `code/`, tanto en ejecución interactiva como en un job."""
    try:
        contexto = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
        return "/Workspace" + os.path.dirname(os.path.dirname(contexto.notebookPath().get()))
    except Exception:
        return os.path.dirname(os.getcwd())


CODE_DIR = _directorio_codigo()
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from preprocesamiento.shared.config_rev import *

# COMMAND ----------

# DBTITLE 1,Covariables que superaron el pre-filtrado
df_prefiltradas = spark.table(TBL_PREFILTRADAS_REV)
codigos_prefiltrados = [c for c in df_prefiltradas.columns if c not in METADATA_COLS]

dominios_con_encuesta = [
    fila["CODIGO_MUNICIPIO"]
    for fila in df_prefiltradas.select("CODIGO_MUNICIPIO").distinct().collect()
]

print(f"Covariables pre-filtradas: {len(codigos_prefiltrados)}")
print(f"Dominios con estimación directa: {len(dominios_con_encuesta)}")

# COMMAND ----------

# DBTITLE 1,Municipios objetivo sin estimación directa
df_terridata = spark.table(TBL_TERRIDATA)

df_objetivo = (
    df_terridata
    .filter(F.col("CODIGO_DEPARTAMENTO").cast("int").isin(DEPARTAMENTOS_OBJETIVO))
    .filter(F.col("ANO") == PER_ESTIMACION)
    .filter(F.col("MES") == MES_ESTIMACION)
    # TerriData incluye, junto a los municipios, una fila agregada por departamento cuyo
    # código DIVIPOLA termina en 000 (19000 para Cauca, 76000 para Valle del Cauca). No es un
    # dominio de estimación y se excluye; de lo contrario aparecería entre las estimaciones
    # sintéticas como si fuera un municipio más.
    .filter(F.col("CODIGO_ENTIDAD").cast("int") % 1000 != 0)
    .filter(~F.col("CODIGO_ENTIDAD").isin(dominios_con_encuesta))
    .select(
        F.col("ANO").alias("PER"),
        F.col("MES"),
        F.col("CODIGO_DEPARTAMENTO"),
        F.col("DEPARTAMENTO"),
        F.col("CODIGO_ENTIDAD").alias("CODIGO_MUNICIPIO"),
        F.col("ENTIDAD").alias("MUNICIPIO"),
        *[F.col(f"`{c}`").cast("double").alias(c) for c in codigos_prefiltrados],
    )
)

n_objetivo = df_objetivo.count()
print(f"Municipios objetivo sin estimación directa: {n_objetivo}")

if n_objetivo == 0:
    raise ValueError(
        f"No se encontraron municipios objetivo para ANO={PER_ESTIMACION}, "
        f"MES={MES_ESTIMACION} en los departamentos {DEPARTAMENTOS_OBJETIVO}. "
        f"Verificar el período disponible en {TBL_TERRIDATA}."
    )

display(df_objetivo.select("CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO"))

# COMMAND ----------

# DBTITLE 1,Completitud de las covariables en los dominios objetivo
# Una covariable con faltantes en los dominios objetivo no puede usarse para predecir en
# ellos, aunque estuviera completa en los dominios con encuesta. Se reporta aquí para que
# la etapa de selección pueda tenerlo en cuenta si el conjunto elegido resulta afectado.
conteos = df_objetivo.select([
    F.sum(F.col(c).isNull().cast("int")).alias(c) for c in codigos_prefiltrados
]).collect()[0].asDict()

incompletas = {k: v for k, v in conteos.items() if v > 0}
print(f"Covariables con faltantes en los dominios objetivo: {len(incompletas)} de "
      f"{len(codigos_prefiltrados)}")
if incompletas:
    ejemplos = list(incompletas.items())[:15]
    print("  ejemplos (código: n.º de municipios sin dato):")
    for codigo, n in ejemplos:
        print(f"    {codigo}: {n}")

# COMMAND ----------

# DBTITLE 1,Escritura de la tabla de dominios objetivo
(df_objetivo.write.mode("overwrite").option("overwriteSchema", "true")
 .saveAsTable(TBL_SIN_ENCUESTA_REV))

print(f"Tabla escrita: {TBL_SIN_ENCUESTA_REV}  ({n_objetivo} municipios)")

