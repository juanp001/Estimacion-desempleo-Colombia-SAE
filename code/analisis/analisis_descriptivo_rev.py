# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Análisis descriptivo de los datos previo al modelamiento
# MAGIC
# MAGIC Notebook nuevo. Responde al requerimiento de que, antes del modelamiento, exista una
# MAGIC caracterización descriptiva univariada y bivariada o multivariada de los datos.
# MAGIC
# MAGIC ## Qué hace y qué no hace
# MAGIC
# MAGIC El propósito de este notebook es **comprender los datos**: cómo se distribuyen, qué
# MAGIC tan dispersos son, qué territorios se apartan del resto y cómo se relacionan entre sí.
# MAGIC No descarta ninguna covariable. Las decisiones de selección se toman en
# MAGIC `eda_seleccion_covariables_rev`, a partir de los diagnósticos correspondientes.
# MAGIC
# MAGIC La distinción es deliberada y se sostiene a lo largo de todo el flujo:
# MAGIC
# MAGIC | | Análisis descriptivo | Selección de covariables |
# MAGIC |---|---|---|
# MAGIC | Pregunta | ¿Cómo son los datos y cómo se relacionan? | ¿Cuáles entran al modelo? |
# MAGIC | Salida | Tablas y figuras de caracterización | Un subconjunto de covariables |
# MAGIC | Una variable asimétrica | se describe como asimétrica | no se descarta por serlo |
# MAGIC | Un dominio extremo | se identifica y se nombra | no se elimina |
# MAGIC
# MAGIC ## Posición en el flujo
# MAGIC
# MAGIC ```
# MAGIC pre_filtrado_covariables_rev   →  covariables_prefiltradas_rev
# MAGIC        │
# MAGIC        ▼  elegibilidad conceptual (catálogo de literatura, independiente de la respuesta)
# MAGIC        │
# MAGIC        ▼  [ESTE NOTEBOOK]
# MAGIC        │   1. Univariado:    tasa de desempleo, su error estándar y su varianza de
# MAGIC        │                     muestreo, y las covariables candidatas
# MAGIC        │   2. Bivariado:     cada candidata frente a la tasa de desempleo
# MAGIC        │   3. Multivariado:  estructura conjunta de las candidatas
# MAGIC        │
# MAGIC        ▼  eda_seleccion_covariables_rev  →  diagnóstico y selección
# MAGIC        ▼  fay_herriot_rev
# MAGIC ```
# MAGIC
# MAGIC ## Sobre el tamaño muestral
# MAGIC
# MAGIC El análisis trabaja con los 23 dominios que tienen estimación directa de la GEIH. Con
# MAGIC ese tamaño los estadísticos descriptivos son informativos pero los contrastes de
# MAGIC hipótesis tienen poca potencia. Por eso esta etapa no ejecuta ninguna prueba formal:
# MAGIC describe, y deja los contrastes que sí tienen consecuencia para la etapa de
# MAGIC diagnóstico.
# MAGIC
# MAGIC ## Salidas
# MAGIC
# MAGIC * `tesis.preprocesamiento.descriptivo_univariado_rev`
# MAGIC * `tesis.preprocesamiento.descriptivo_bivariado_rev`
# MAGIC * Figuras en el volumen `figuras_eda`, con prefijo `desc_`.

# COMMAND ----------

# DBTITLE 1,Setup: rutas, imports y carga de datos
import os
import sys

import numpy as np
import pandas as pd
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
from analisis.shared_rev import descriptivos as desc
from analisis.shared_rev.catalogo_literatura import resolver_catalogo, mapas_catalogo

# ── Carga ─────────────────────────────────────────────────────────────────────
df_full = spark.table(TBL_PREFILTRADAS_REV)
indicadores_dict = {
    fila["CODIGO_INDICADOR"]: fila["INDICADOR"]
    for fila in spark.table(TBL_DIM_INDICADORES)
    .select("CODIGO_INDICADOR", "INDICADOR").collect()
}

cols_covariables = [c for c in df_full.columns if c not in METADATA_COLS]
df_cov_spark = df_full.select(cols_covariables)
for nombre in [f.name for f in df_cov_spark.schema.fields if str(f.dataType) == "StringType()"]:
    df_cov_spark = df_cov_spark.withColumn(nombre, F.col(nombre).cast("double"))

df_meta = df_full.select(METADATA_COLS).toPandas()
df_pd   = df_cov_spark.toPandas()

Y         = df_meta[VARIABLE_OBJETIVO].values
SE        = df_meta["SE_BOOTSTRAP_PCT"].values
PSI       = SE ** 2                      # varianza de muestreo que el modelo toma como conocida
entidades = df_meta["MUNICIPIO"].values

df_meta["VARIANZA_MUESTREO"] = PSI

print(f"Dominios de estimación: {len(Y)}")
print(f"Covariables pre-filtradas: {df_pd.shape[1]}")

# COMMAND ----------

# MAGIC %md
# MAGIC # 1. Elegibilidad conceptual de las covariables
# MAGIC
# MAGIC El conjunto pre-filtrado es demasiado grande para describirse variable por variable.
# MAGIC Antes de caracterizarlo se aplica el criterio conceptual: se conservan las covariables
# MAGIC para las que existe un mecanismo documentado que las vincula con el desempleo
# MAGIC municipal, organizadas en siete dimensiones.
# MAGIC
# MAGIC Este criterio **no usa la variable respuesta**, lo que es esencial: las candidatas no
# MAGIC fueron elegidas por parecerse a la tasa de desempleo, de modo que las correlaciones que
# MAGIC se calculen después conservan su interpretación. En la versión original esa condición
# MAGIC no se cumplía, porque el pre-filtrado ya había seleccionado por correlación con la
# MAGIC respuesta.
# MAGIC
# MAGIC El reporte deja constancia de qué entradas del catálogo no llegan a candidatas y por
# MAGIC qué motivo. En la versión original esa correspondencia no quedaba registrada y los tres
# MAGIC números no coincidían entre sí: los títulos de las etapas anunciaban dieciséis
# MAGIC candidatas, el catálogo definía quince entradas y el análisis se ejecutaba en realidad
# MAGIC sobre once.

# COMMAND ----------

# DBTITLE 1,Resolución del catálogo de elegibilidad conceptual
catalogo_activo, reporte_catalogo = resolver_catalogo(indicadores_dict, list(df_pd.columns))
CANDIDATAS, ALIAS, LITERATURA, DIMENSION = mapas_catalogo(catalogo_activo)

df_cand = df_pd[CANDIDATAS].copy()
NOMBRES = {c: indicadores_dict.get(c, c) for c in CANDIDATAS}

display(spark.createDataFrame(reporte_catalogo))

# COMMAND ----------

# MAGIC %md
# MAGIC # 2. Análisis descriptivo univariado
# MAGIC
# MAGIC Responde a la pregunta: **¿cómo se comporta cada variable por sí sola?**
# MAGIC
# MAGIC Se caracterizan tres bloques, en este orden:
# MAGIC
# MAGIC 1. **La variable respuesta**, la tasa de desempleo estimada directamente por dominio.
# MAGIC 2. **Su medida de precisión**: el error estándar bootstrap y la varianza de muestreo.
# MAGIC    Caracterizarla no es opcional: el modelo Fay-Herriot la toma como conocida y la
# MAGIC    usa para ponderar cuánto peso recibe la estimación directa de cada dominio frente
# MAGIC    al predictor sintético. Su dispersión determina cuánto suaviza el modelo.
# MAGIC 3. **Las covariables candidatas**.
# MAGIC
# MAGIC Los estadísticos se eligen según lo que cada variable admite: el coeficiente de
# MAGIC variación se calcula solo donde la variable es estrictamente positiva, que es la
# MAGIC condición bajo la cual expresa dispersión relativa.

# COMMAND ----------

# DBTITLE 1,Descriptivos de la variable respuesta y de su precisión
etiquetas_respuesta = {
    VARIABLE_OBJETIVO:   "Tasa de desempleo (%)",
    "SE_BOOTSTRAP_PCT":  "Error estándar bootstrap (p.p.)",
    "VARIANZA_MUESTREO": "Varianza de muestreo (p.p.²)",
    "CV_PORCENTAJE":     "Coeficiente de variación de la estimación directa (%)",
}
desc_respuesta = desc.resumen_univariado(
    df_meta,
    [VARIABLE_OBJETIVO, "SE_BOOTSTRAP_PCT", "VARIANZA_MUESTREO", "CV_PORCENTAJE"],
    etiquetas=etiquetas_respuesta,
)
display(spark.createDataFrame(desc_respuesta))

# COMMAND ----------

# DBTITLE 1,Figura: distribución de la respuesta y de su error estándar
fig = desc.figura_respuesta(Y, SE)
desc.guardar_figura(fig, "desc_respuesta_precision", VOLUMEN_FIGURAS)
display(fig)

# COMMAND ----------

# DBTITLE 1,Figura: distribución territorial de la tasa de desempleo
fig = desc.figura_territorial(Y, entidades)
desc.guardar_figura(fig, "desc_territorial_respuesta", VOLUMEN_FIGURAS)
display(fig)

# COMMAND ----------

# MAGIC %md
# MAGIC La figura anterior es una **descripción territorial**, no un contraste de dependencia
# MAGIC espacial. Muestra qué dominios ocupan cada extremo de la distribución; no evalúa si
# MAGIC los territorios próximos entre sí tienen tasas parecidas. Ese contraste corresponde al
# MAGIC índice de Moran sobre los residuos del modelo, y se realiza en la etapa de diagnóstico,
# MAGIC donde tiene una consecuencia metodológica concreta sobre el supuesto de independencia.

# COMMAND ----------

# DBTITLE 1,Descriptivos de las covariables candidatas
desc_covariables = desc.resumen_univariado(df_cand, CANDIDATAS, etiquetas=NOMBRES)
desc_covariables.insert(1, "Alias", [ALIAS[c] for c in desc_covariables["Codigo"]])
desc_covariables.insert(2, "Dimension", [DIMENSION[c] for c in desc_covariables["Codigo"]])
display(spark.createDataFrame(desc_covariables))

# COMMAND ----------

# DBTITLE 1,Dominios en los extremos de cada covariable
extremos = desc.dominios_extremos(df_cand, CANDIDATAS, entidades, alias=ALIAS)
display(spark.createDataFrame(extremos))

# COMMAND ----------

# MAGIC %md
# MAGIC Los dominios que aparecen en los extremos son territorios reales, no errores de
# MAGIC medición: capitales de gran tamaño, ciudades con historia de conflicto o periferias con
# MAGIC baja cobertura de servicios. Identificarlos es descriptivo. Si alguno de ellos está
# MAGIC además determinando por sí solo la relación entre una covariable y el desempleo es una
# MAGIC pregunta distinta, que se responde con el diagnóstico de influencia en la etapa
# MAGIC siguiente. Ninguna observación se elimina en este notebook ni en el siguiente.

# COMMAND ----------

# DBTITLE 1,Figura: panel de diagramas de caja de las candidatas
fig = desc.figura_panel_boxplots(df_cand, CANDIDATAS, alias=ALIAS)
desc.guardar_figura(fig, "desc_boxplots_candidatas", VOLUMEN_FIGURAS)
display(fig)

# COMMAND ----------

# MAGIC %md
# MAGIC # 3. Análisis descriptivo bivariado
# MAGIC
# MAGIC Responde a la pregunta: **¿cómo se relacionan las variables entre sí y, en particular,
# MAGIC con la tasa de desempleo?**
# MAGIC
# MAGIC Se reportan el coeficiente de Pearson y el de Spearman, y se indica **cuál de los dos
# MAGIC es el interpretable** para cada covariable en lugar de presentar ambos por inercia. El
# MAGIC criterio es explícito: si la covariable tiene valores extremos y las dos medidas
# MAGIC discrepan, la asociación lineal está condicionada por esos puntos y la medida
# MAGIC pertinente es la de rangos; si coinciden, se interpreta Pearson, que es la forma que
# MAGIC supone el componente sintético del modelo.
# MAGIC
# MAGIC Los coeficientes son descriptivos. Una asociación no implica causalidad, y ninguna
# MAGIC covariable se incluye ni se excluye aquí por la magnitud de su correlación.

# COMMAND ----------

# DBTITLE 1,Relación de cada candidata con la tasa de desempleo
bivariado = desc.tabla_bivariada(df_cand, CANDIDATAS, Y, alias=ALIAS)
bivariado.insert(2, "Dimension", [DIMENSION[c] for c in bivariado["Codigo"]])
display(spark.createDataFrame(bivariado))

# COMMAND ----------

# DBTITLE 1,Figura: panel de dispersión de las candidatas frente a la respuesta
fig = desc.figura_panel_dispersion(df_cand, CANDIDATAS, Y, alias=ALIAS)
desc.guardar_figura(fig, "desc_dispersion_candidatas", VOLUMEN_FIGURAS)
display(fig)

# COMMAND ----------

# MAGIC %md
# MAGIC # 4. Análisis descriptivo multivariado
# MAGIC
# MAGIC Responde a la pregunta: **¿qué estructura conjunta presentan las covariables que no se
# MAGIC aprecia al mirarlas de una en una o por pares?**
# MAGIC
# MAGIC La caracterización multivariada es una matriz de correlación reordenada por
# MAGIC agrupamiento jerárquico, de modo que las covariables que miden aspectos parecidos del
# MAGIC territorio queden contiguas y los bloques se vean como tales. Es una técnica
# MAGIC descriptiva, sin parámetros que ajustar ni decisiones arbitrarias, y responde a una
# MAGIC pregunta que el proyecto necesita contestar: qué grupos de indicadores están midiendo
# MAGIC lo mismo. Esos bloques son el insumo del criterio de redundancia de la etapa siguiente.
# MAGIC
# MAGIC **No se aplica análisis de componentes principales.** No se usa en el pre-filtrado ni
# MAGIC como forma de cumplir formalmente con la palabra «multivariado»: introduciría
# MAGIC componentes sin interpretación territorial directa y una decisión adicional —cuántos
# MAGIC componentes retener— que esta etapa no necesita. Queda reservado como escenario
# MAGIC alternativo de modelamiento, sobre el conjunto ya depurado.

# COMMAND ----------

# DBTITLE 1,Figura: estructura de correlación entre las candidatas
fig, orden_agrupado = desc.figura_correlacion_agrupada(
    df_cand, CANDIDATAS, alias=ALIAS,
    titulo="Estructura de correlación entre las covariables candidatas",
)
desc.guardar_figura(fig, "desc_correlacion_candidatas", VOLUMEN_FIGURAS)
display(fig)

# COMMAND ----------

# DBTITLE 1,Pares de covariables fuertemente asociadas entre sí
pares = desc.tabla_pares_correlacionados(df_cand, CANDIDATAS, alias=ALIAS,
                                         umbral=UMBRAL_REDUNDANCIA)
display(spark.createDataFrame(pares) if not pares.empty else spark.createDataFrame(
    pd.DataFrame([{"Mensaje": f"Ningún par supera |r| = {UMBRAL_REDUNDANCIA}"}])))

# COMMAND ----------

# MAGIC %md
# MAGIC Estos pares señalan información potencialmente redundante. **Ninguna covariable se
# MAGIC descarta por aparecer aquí.** La decisión formal sobre cuál conservar de cada grupo se
# MAGIC toma en la etapa de selección, con un criterio de desempate explícito.

# COMMAND ----------

# DBTITLE 1,Escritura de las tablas descriptivas
(spark.createDataFrame(pd.concat([
    desc_respuesta.assign(Bloque="Variable respuesta y precisión", Alias=None, Dimension=None),
    desc_covariables.assign(Bloque="Covariables candidatas"),
], ignore_index=True))
 .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(TBL_DESCRIPTIVO_UNI))

(spark.createDataFrame(bivariado)
 .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(TBL_DESCRIPTIVO_BI))

print(f"Tablas escritas:\n  · {TBL_DESCRIPTIVO_UNI}\n  · {TBL_DESCRIPTIVO_BI}")
print(f"Candidatas caracterizadas: {len(CANDIDATAS)}")

