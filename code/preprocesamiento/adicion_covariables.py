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
# MAGIC **por su propio denominador** `z`:
# MAGIC
# MAGIC ```
# MAGIC x̄_D = Σ_{m∈D} z_m · x_m / Σ_{m∈D} z_m
# MAGIC ```
# MAGIC
# MAGIC Si `x = Y/Z`, el resultado es `ΣY/ΣZ`, el indicador calculado para la unión de los municipios
# MAGIC (Morales et al., 2021, p. 21 y 425). Ejemplos: participación sectorial del valor agregado →
# MAGIC peso = valor agregado; densidad → superficie; valores per cápita, IPM, homicidios → población
# MAGIC total; coberturas educativas y Saber 11 → población del grupo de edad (proxy). La regla de cada
# MAGIC variable del catálogo está en `shared/reglas_agregacion.py` y se guarda en
# MAGIC `tesis.preprocesamiento.reglas_agregacion_covariables`; los indicadores fuera del catálogo usan
# MAGIC la población de 15 años y más. En los 16 dominios de un solo municipio el resultado es el valor
# MAGIC del municipio. Una celda compara, para los 7 dominios A.M., la regla por variable con la
# MAGIC regla anterior (todo ponderado por la población de 15 años y más).
# MAGIC
# MAGIC ## Auditoría de la correspondencia geográfica
# MAGIC
# MAGIC La última celda guarda `tesis.preprocesamiento.auditoria_dominios`: una fila por dominio con
# MAGIC el código `AREA` de la GEIH, el nombre oficial del DANE (y si aparece en el anexo), la
# MAGIC geografía real de la tasa (cabeceras) y de las covariables (municipio completo), los
# MAGIC municipios integrantes con su DIVIPOLA, el DIVIPOLA usado en la unión, la regla de
# MAGIC construcción de `x_d` y la tasa directa frente a la publicada. Se detiene si un dominio no
# MAGIC aparece en la auditoría o si su nombre no está en las cifras oficiales del período.
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

import pandas as pd
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
from preprocesamiento.shared.auditoria_dominios import tabla_auditoria_dominios
from preprocesamiento.shared.reglas_agregacion import (
    PESOS_AGREGACION,
    REGLAS_AGREGACION,
    regla_de,
    tabla_reglas,
)
from analisis.shared.catalogo_literatura import CATALOGO_LITERATURA

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

# Regla de agregación de cada indicador: su denominador si está en el catálogo de literatura, la
# población de 15 años y más si no (shared/reglas_agregacion.py). Toda variable del catálogo debe
# tener una regla explícita, para que ninguna entre al modelo con la regla por defecto.
codigos_catalogo = [e["codigo"] for e in CATALOGO_LITERATURA]
sin_regla = [c for c in codigos_catalogo if c not in REGLAS_AGREGACION]
if sin_regla:
    raise ValueError(
        f"Variables del catálogo sin regla de agregación en reglas_agregacion.py: {sin_regla}"
    )

pesos_por_columna = {c: regla_de(c)["peso"] for c in columnas_indicadores}
expresiones_peso = {
    p: PESOS_AGREGACION[p]["expresion"] for p in set(pesos_por_columna.values())
}
print("Indicadores por peso de agregación:")
for peso in sorted(expresiones_peso):
    n = sum(1 for p in pesos_por_columna.values() if p == peso)
    print(f"  {peso:<16} {n:>5}  ({PESOS_AGREGACION[peso]['descripcion']})")

# COMMAND ----------

# DBTITLE 1,Agregar las covariables municipales al dominio
# Un bloque por período estimado (normalmente uno). Promedio ponderado de cada indicador por su
# propio peso sobre los municipios de cada dominio; ver shared/agregacion_dominios.py.
df_terridata_dominio = None
for per, mes in periodos_estimados:
    df_periodo = agregar_covariables_dominio(
        df_terridata,
        df_dim_dominio,
        pesos_por_columna,
        expresiones_peso,
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

# DBTITLE 1,Sensibilidad: regla por variable vs. regla anterior (PET) en los dominios A.M.
# Solo imprime. La regla anterior ponderaba todos los indicadores por la población de 15 años y
# más; la diferencia muestra qué covariables del catálogo dependen de la regla. Las ponderadas
# por población apenas cambian (la PET es casi proporcional a la población); las que tienen otro
# denominador (valor agregado, superficie) sí.
codigos_catalogo_presentes = [c for c in codigos_catalogo if c in columnas_indicadores]
dominios_am = df_dim_dominio.filter(F.col("TIPO_DOMINIO") == "CIUDAD_AM")
alias_catalogo = {e["codigo"]: e["alias"] for e in CATALOGO_LITERATURA}

comparaciones = []
for per, mes in periodos_estimados:
    reglas = {
        "NUEVA": {c: pesos_por_columna[c] for c in codigos_catalogo_presentes},
        "PET": {c: "PET" for c in codigos_catalogo_presentes},
    }
    valores = {}
    for nombre, pesos in reglas.items():
        valores[nombre] = (
            agregar_covariables_dominio(
                df_terridata,
                dominios_am,
                pesos,
                {p: PESOS_AGREGACION[p]["expresion"] for p in set(pesos.values())},
                per,
                mes,
            )
            .toPandas()
            .melt(id_vars=["CODIGO_DOMINIO", "ANO", "MES"], var_name="CODIGO_INDICADOR")
            .rename(columns={"value": f"VALOR_{nombre}"})
        )
    comparaciones.append(
        valores["NUEVA"].merge(
            valores["PET"], on=["CODIGO_DOMINIO", "ANO", "MES", "CODIGO_INDICADOR"]
        )
    )

df_sensibilidad = pd.concat(comparaciones, ignore_index=True)
df_sensibilidad["ALIAS"] = df_sensibilidad["CODIGO_INDICADOR"].map(alias_catalogo)
df_sensibilidad["PESO"] = df_sensibilidad["CODIGO_INDICADOR"].map(pesos_por_columna)
df_sensibilidad["DIF_RELATIVA_PCT"] = (
    100
    * (df_sensibilidad["VALOR_NUEVA"] - df_sensibilidad["VALOR_PET"])
    / df_sensibilidad["VALOR_PET"].abs()
)
resumen = (
    df_sensibilidad.groupby(["ALIAS", "PESO"])["DIF_RELATIVA_PCT"]
    .agg(lambda s: s.abs().max())
    .rename("MAX_ABS_DIF_RELATIVA_PCT")
    .reset_index()
    .sort_values("MAX_ABS_DIF_RELATIVA_PCT", ascending=False)
)
print(
    "Máxima diferencia relativa (%) entre la regla por variable y la regla PET "
    "(7 dominios A.M.):"
)
print(resumen.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
display(
    df_sensibilidad.loc[df_sensibilidad["DIF_RELATIVA_PCT"].abs() > 1].sort_values(
        ["ALIAS", "CODIGO_DOMINIO"]
    )
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

# COMMAND ----------

# DBTITLE 1,Guardar la regla de agregación de cada covariable del catálogo
indicadores_dict = {
    fila["CODIGO_INDICADOR"]: fila["INDICADOR"]
    for fila in spark.table(TBL_DIM_INDICADORES)
    .select("CODIGO_INDICADOR", "INDICADOR")
    .collect()
}
df_reglas = tabla_reglas(codigos_catalogo, indicadores_dict)
df_reglas.insert(1, "ALIAS", df_reglas["CODIGO_INDICADOR"].map(alias_catalogo))
display(df_reglas)

spark.createDataFrame(df_reglas).write.mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(TBL_REGLAS_AGREGACION)
print(f"✔ Tabla creada: {TBL_REGLAS_AGREGACION}")

# COMMAND ----------

# DBTITLE 1,Tabla de auditoría de los dominios (G7-B1)
# Una fila por dominio con estimación directa: de dónde sale la tasa (AREA de la GEIH, cabeceras)
# y de dónde salen las covariables (municipios integrantes, regla de x_d). Ver
# shared/auditoria_dominios.py.
df_miembros = (
    df_dim_dominio.join(
        spark.table(TBL_DIM_GEIH_DIVIPOLA).select(
            F.col("CODIGO_MUNICIPIO"), "CODIGO_AREA_GEIH"
        ),
        on="CODIGO_MUNICIPIO",
        how="left",
    )
    .select(
        "CODIGO_DOMINIO",
        "NOMBRE_DOMINIO",
        "TIPO_DOMINIO",
        "CODIGO_MUNICIPIO",
        "MUNICIPIO",
        "ES_CAPITAL",
        F.when(F.col("ES_CAPITAL"), F.col("CODIGO_AREA_GEIH")).alias(
            "CODIGO_AREA_GEIH"
        ),
    )
    .toPandas()
)
df_publicados = (
    spark.table(TBL_DATOS_MUNICIPALES)
    .join(
        df_estimaciones.select(
            F.col("PER").cast("int").alias("ANIO"),
            F.col("MES").cast("int").alias("MES"),
        ).distinct(),
        on=["ANIO", "MES"],
        how="inner",
    )
    .select("CIUDAD", "TASA_DESEMPLEO")
    .toPandas()
)
df_auditoria = tabla_auditoria_dominios(
    df_miembros,
    df_estimaciones.toPandas(),
    df_publicados,
    {c: pesos_por_columna.get(c, regla_de(c)["peso"]) for c in codigos_catalogo},
)

n_dominios = df_estimaciones.count()
if len(df_auditoria) != n_dominios:
    raise ValueError(
        f"La auditoría tiene {len(df_auditoria)} filas y hay {n_dominios} dominios estimados"
    )
if not df_publicados.empty and not df_auditoria["EN_ANEXO_DANE"].all():
    raise ValueError(
        "Dominios cuyo nombre no está en las cifras oficiales del DANE: "
        f"{df_auditoria.loc[~df_auditoria['EN_ANEXO_DANE'], 'NOMBRE_DOMINIO'].tolist()}"
    )
print(
    f"Dominios auditados: {len(df_auditoria)} "
    f"({(df_auditoria['TIPO_DOMINIO'] == 'CIUDAD_AM').sum()} A.M., "
    f"{df_auditoria['N_MUNICIPIOS'].sum()} municipios) | "
    f"máx |TD directa − TD DANE| = {df_auditoria['DIF_TD_PP'].abs().max():.4f} pp"
)
display(df_auditoria)

spark.createDataFrame(df_auditoria).write.mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(TBL_AUDITORIA_DOMINIOS)
print(f"✔ Tabla creada: {TBL_AUDITORIA_DOMINIOS}")
