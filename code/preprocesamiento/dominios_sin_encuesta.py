# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Municipios objetivo sin estimación directa propia
# MAGIC
# MAGIC Construye la tabla de covariables **municipales** de los municipios de Cauca y Valle del Cauca
# MAGIC que recibirán una estimación sintética, es decir, los que no tienen una estimación directa
# MAGIC propia de la GEIH.
# MAGIC
# MAGIC ## Por qué existe este notebook
# MAGIC
# MAGIC La predicción sintética del modelo necesita las covariables de los municipios que no
# MAGIC tienen estimación directa. Para que el paso sea reproducible desde el código y no
# MAGIC quede acoplado a un conjunto concreto de covariables (de modo que un cambio en la
# MAGIC selección no lo rompa), la tabla se deriva de las fuentes con **todas** las
# MAGIC covariables que superaron el pre-filtrado y conservando los códigos de indicador. El
# MAGIC notebook del modelo toma después las que necesite y las renombra, de forma que la
# MAGIC predicción sintética funciona con cualquier conjunto seleccionado.
# MAGIC
# MAGIC ## Definición de los municipios objetivo
# MAGIC
# MAGIC Los dominios con estimación directa son ciudades o ciudades con su área metropolitana
# MAGIC (`tesis.dim.dim_dominio_geih`). Un municipio tiene estimación directa **propia** solo si él
# MAGIC solo forma un dominio con muestra (Popayán). Los municipios de un área metropolitana (Cali y
# MAGIC Yumbo en Cali A.M.) **no** la tienen: la GEIH pública no identifica el municipio dentro del
# MAGIC A.M., así que su muestra solo da la tasa del conjunto.
# MAGIC
# MAGIC Por eso la tabla contiene:
# MAGIC
# MAGIC * los municipios de los departamentos objetivo presentes en TerriData para el período, menos
# MAGIC   los que forman por sí solos un dominio con estimación directa;
# MAGIC * todos los miembros de cualquier dominio de varios municipios con estimación directa que toque
# MAGIC   los departamentos objetivo, con `CODIGO_DOMINIO_PADRE` igual al código de ese dominio.
# MAGIC
# MAGIC Yumbo no se excluye ni recibe la tasa de Cali A.M.: el DANE da estimación propia a cada
# MAGIC municipio de un A.M. y la hace coherente con la de la ciudad mediante benchmarking (nota SAE
# MAGIC 2024, PDF 25); el modelo anidado (Morales et al., p. 462) exigiría estimaciones directas por
# MAGIC municipio, que no existen, y asignarle la tasa del A.M. sería el sintético básico, sesgado si
# MAGIC Yumbo difiere de Cali (Morales et al., p. 42). Los miembros con padre se ajustan al valor de su
# MAGIC dominio en el benchmarking de nivel 2 del modelo, que exige que estén **todos**.
# MAGIC
# MAGIC Las covariables son las del municipio (sin agregar): el modelo predice con x_m'β̂.
# MAGIC
# MAGIC ## Salida
# MAGIC
# MAGIC * `tesis.preprocesamiento.municipios_sin_encuesta`

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
import os
import sys

from pyspark.sql import functions as F


def _directorio_codigo() -> str:
    """Ruta absoluta de `code/`, tanto en ejecución interactiva como en un job."""
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

# Período a estimar: widgets anio_estimacion / mes_estimacion (parámetros del job).
PER_ESTIMACION, MES_ESTIMACION = resolver_periodo(dbutils)

# COMMAND ----------

# DBTITLE 1,Covariables que superaron el pre-filtrado y dominios con encuesta
df_prefiltradas = spark.table(TBL_PREFILTRADAS)
codigos_prefiltrados = [c for c in df_prefiltradas.columns if c not in METADATA_COLS]

dominios_con_encuesta = {
    fila["CODIGO_DOMINIO"]
    for fila in df_prefiltradas.select("CODIGO_DOMINIO").distinct().collect()
}

print(f"Covariables pre-filtradas: {len(codigos_prefiltrados)}")
print(f"Dominios con estimación directa: {len(dominios_con_encuesta)}")

# COMMAND ----------

# DBTITLE 1,Clasificación de los municipios según su dominio
# Para cada municipio de un dominio con encuesta: si el dominio tiene un solo municipio, ese
# municipio ya tiene estimación directa propia y se excluye; si tiene varios, el municipio necesita
# estimación propia y queda con el dominio como padre del benchmarking de nivel 2.
df_miembros = spark.table(TBL_DIM_DOMINIO).filter(
    F.col("CODIGO_DOMINIO").isin(list(dominios_con_encuesta))
)
n_por_dominio = df_miembros.groupBy("CODIGO_DOMINIO").agg(
    F.count("*").alias("N_MUNICIPIOS")
)
df_miembros = df_miembros.join(n_por_dominio, on="CODIGO_DOMINIO")

municipios_con_directa_propia = [
    fila["CODIGO_MUNICIPIO"]
    for fila in df_miembros.filter(F.col("N_MUNICIPIOS") == 1)
    .select("CODIGO_MUNICIPIO")
    .collect()
]

df_padres = df_miembros.filter(F.col("N_MUNICIPIOS") > 1).select(
    "CODIGO_MUNICIPIO", F.col("CODIGO_DOMINIO").alias("CODIGO_DOMINIO_PADRE")
)

# Dominios de varios municipios que tocan los departamentos objetivo: entran todos sus miembros,
# aunque alguno estuviera en otro departamento, para que el benchmarking de nivel 2 sea completo.
padres_objetivo = [
    fila["CODIGO_DOMINIO"]
    for fila in df_miembros.filter(
        (F.col("N_MUNICIPIOS") > 1)
        & F.col("CODIGO_DEPARTAMENTO").cast("int").isin(DEPARTAMENTOS_OBJETIVO)
    )
    .select("CODIGO_DOMINIO")
    .distinct()
    .collect()
]
miembros_padres_objetivo = [
    fila["CODIGO_MUNICIPIO"]
    for fila in df_padres.filter(F.col("CODIGO_DOMINIO_PADRE").isin(padres_objetivo))
    .select("CODIGO_MUNICIPIO")
    .collect()
]

print(
    f"Municipios con estimación directa propia (excluidos): {sorted(municipios_con_directa_propia)}"
)
print(
    f"Dominios de varios municipios en los departamentos objetivo: {sorted(padres_objetivo)}"
)

# COMMAND ----------

# DBTITLE 1,Municipios objetivo sin estimación directa propia
df_terridata = spark.table(TBL_TERRIDATA)

df_objetivo = (
    df_terridata.filter(F.col("ANO") == PER_ESTIMACION)
    .filter(F.col("MES") == MES_ESTIMACION)
    .filter(
        F.col("CODIGO_DEPARTAMENTO").cast("int").isin(DEPARTAMENTOS_OBJETIVO)
        | F.col("CODIGO_ENTIDAD").isin(miembros_padres_objetivo)
    )
    # TerriData incluye, junto a los municipios, una fila agregada por departamento cuyo
    # código DIVIPOLA termina en 000 (19000 para Cauca, 76000 para Valle del Cauca). No es un
    # dominio de estimación y se excluye; de lo contrario aparecería entre las estimaciones
    # sintéticas como si fuera un municipio más.
    .filter(F.col("CODIGO_ENTIDAD").cast("int") % 1000 != 0)
    .filter(~F.col("CODIGO_ENTIDAD").isin(municipios_con_directa_propia))
    .join(
        df_padres.withColumnRenamed("CODIGO_MUNICIPIO", "CODIGO_ENTIDAD"),
        on="CODIGO_ENTIDAD",
        how="left",
    )
    .select(
        F.col("ANO").alias("PER"),
        F.col("MES"),
        F.col("CODIGO_DEPARTAMENTO"),
        F.col("DEPARTAMENTO"),
        F.col("CODIGO_ENTIDAD").alias("CODIGO_MUNICIPIO"),
        F.col("ENTIDAD").alias("MUNICIPIO"),
        F.col("CODIGO_DOMINIO_PADRE"),
        # try_cast: un texto en un indicador queda NULL y se reporta como faltante abajo.
        *[F.expr(f"try_cast(`{c}` AS DOUBLE)").alias(c) for c in codigos_prefiltrados],
    )
)

n_objetivo = df_objetivo.count()
print(f"Municipios objetivo sin estimación directa propia: {n_objetivo}")

if n_objetivo == 0:
    raise ValueError(
        f"No se encontraron municipios objetivo para ANO={PER_ESTIMACION}, "
        f"MES={MES_ESTIMACION} en los departamentos {DEPARTAMENTOS_OBJETIVO}. "
        f"Verificar el período disponible en {TBL_TERRIDATA}."
    )

# Todos los miembros de cada padre deben estar: el benchmarking de nivel 2 reparte la tasa del
# dominio entre sus municipios y un miembro ausente lo haría incorrecto.
con_padre = {
    fila["CODIGO_MUNICIPIO"]
    for fila in df_objetivo.filter(F.col("CODIGO_DOMINIO_PADRE").isNotNull())
    .select("CODIGO_MUNICIPIO")
    .collect()
}
faltan_miembros = sorted(set(miembros_padres_objetivo) - con_padre)
if faltan_miembros:
    raise ValueError(
        f"Miembros de dominios A.M. sin fila en TerriData para el período: {faltan_miembros}. "
        f"El benchmarking de nivel 2 necesita todos los municipios del dominio."
    )

print(f"  con dominio padre (benchmarking de nivel 2): {len(con_padre)}")
display(
    df_objetivo.select(
        "CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO", "CODIGO_DOMINIO_PADRE"
    ).orderBy("CODIGO_MUNICIPIO")
)

# COMMAND ----------

# DBTITLE 1,Completitud de las covariables en los dominios objetivo
# Una covariable con faltantes en los dominios objetivo no puede usarse para predecir en
# ellos, aunque estuviera completa en los dominios con encuesta. Se reporta aquí para que
# la etapa de selección pueda tenerlo en cuenta si el conjunto elegido resulta afectado.
conteos = (
    df_objetivo.select(
        [F.sum(F.col(c).isNull().cast("int")).alias(c) for c in codigos_prefiltrados]
    )
    .collect()[0]
    .asDict()
)

incompletas = {k: v for k, v in conteos.items() if v > 0}
print(
    f"Covariables con faltantes en los dominios objetivo: {len(incompletas)} de "
    f"{len(codigos_prefiltrados)}"
)
if incompletas:
    ejemplos = list(incompletas.items())[:15]
    print("  ejemplos (código: n.º de municipios sin dato):")
    for codigo, n in ejemplos:
        print(f"    {codigo}: {n}")

# COMMAND ----------

# DBTITLE 1,Escritura de la tabla de dominios objetivo
(
    df_objetivo.write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TBL_SIN_ENCUESTA)
)

print(f"Tabla escrita: {TBL_SIN_ENCUESTA}  ({n_objetivo} municipios)")
