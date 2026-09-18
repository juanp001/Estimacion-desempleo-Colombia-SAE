# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Análisis descriptivo de los datos previo al modelamiento
# MAGIC
# MAGIC Responde al requerimiento de que, antes del modelamiento, exista una caracterización
# MAGIC descriptiva univariada, bivariada y multivariada de los datos. Cada figura va acompañada
# MAGIC de una guía de lectura y de una interpretación calculada desde los propios datos, de
# MAGIC modo que el texto no queda desactualizado si cambian.
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
# MAGIC        ▼  eda_seleccion_covariables_rev  →  diagnóstico y selección cualitativa
# MAGIC        ▼  fay_herriot_rev
# MAGIC ```
# MAGIC
# MAGIC ## Sobre el tamaño muestral
# MAGIC
# MAGIC El análisis trabaja con los 23 dominios que tienen estimación directa de la GEIH. Con
# MAGIC ese tamaño los estadísticos descriptivos son informativos pero los contrastes de
# MAGIC hipótesis tienen poca potencia. Por eso esta etapa no ejecuta ninguna prueba formal:
# MAGIC describe, y deja los diagnósticos que sí tienen consecuencia para la etapa de
# MAGIC selección.
# MAGIC
# MAGIC ## Salidas
# MAGIC
# MAGIC * `tesis.preprocesamiento.catalogo_literatura_rev`
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
        return "/Workspace" + os.path.dirname(
            os.path.dirname(contexto.notebookPath().get())
        )
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
    .select("CODIGO_INDICADOR", "INDICADOR")
    .collect()
}

cols_covariables = [c for c in df_full.columns if c not in METADATA_COLS]
df_cov_spark = df_full.select(cols_covariables)
for nombre in [
    f.name for f in df_cov_spark.schema.fields if str(f.dataType) == "StringType()"
]:
    df_cov_spark = df_cov_spark.withColumn(nombre, F.col(nombre).cast("double"))

df_meta = df_full.select(METADATA_COLS).toPandas()
df_pd = df_cov_spark.toPandas()

Y = df_meta[VARIABLE_OBJETIVO].values
SE = df_meta["SE_BOOTSTRAP_PCT"].values
PSI = SE**2  # varianza de muestreo que el modelo toma como conocida
entidades = df_meta["MUNICIPIO"].values

df_meta["VARIANZA_MUESTREO"] = PSI

print(f"Dominios de estimación: {len(Y)}")
print(f"Covariables pre-filtradas: {df_pd.shape[1]}")

# COMMAND ----------

# MAGIC %md
# MAGIC # 1. Elegibilidad conceptual de las covariables
# MAGIC
# MAGIC El conjunto pre-filtrado es demasiado grande para describirse variable por variable.
# MAGIC Antes de caracterizarlo se aplica el criterio conceptual: se conservan únicamente las
# MAGIC covariables que la revisión de literatura del proyecto propone con una referencia
# MAGIC bibliográfica y un mecanismo que las vincula con el desempleo, resueltas contra el
# MAGIC diccionario de indicadores de TerriData.
# MAGIC
# MAGIC Este criterio **no usa la variable respuesta**, lo que es esencial: las candidatas no
# MAGIC fueron elegidas por parecerse a la tasa de desempleo, de modo que las correlaciones que
# MAGIC se calculen después conservan su interpretación. Tampoco asigna un «nivel de respaldo»
# MAGIC numérico a cada entrada: o la variable tiene sustento en el documento o no entra.
# MAGIC
# MAGIC El reporte deja constancia de todas las variables de la revisión, incluidas las que no
# MAGIC pueden usarse (sin dato para 2018, solo departamentales o ausentes en los municipios
# MAGIC objetivo sin encuesta), con su motivo. Cada entrada trae además el **signo esperado**
# MAGIC del coeficiente según el mecanismo declarado, que la etapa de selección contrasta con
# MAGIC el signo observado.

# COMMAND ----------

# DBTITLE 1,Resolución del catálogo de elegibilidad conceptual
catalogo_activo, reporte_catalogo = resolver_catalogo(
    indicadores_dict, list(df_pd.columns)
)
CANDIDATAS, ALIAS, SIGNO, DIMENSION = mapas_catalogo(catalogo_activo)

df_cand = df_pd[CANDIDATAS].copy()
NOMBRES = {c: indicadores_dict.get(c, c) for c in CANDIDATAS}

display(spark.createDataFrame(reporte_catalogo))

(
    spark.createDataFrame(reporte_catalogo)
    .write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TBL_CATALOGO_REV)
)
print(f"Tabla escrita: {TBL_CATALOGO_REV}")

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
    VARIABLE_OBJETIVO: "Tasa de desempleo (%)",
    "SE_BOOTSTRAP_PCT": "Error estándar bootstrap (p.p.)",
    "VARIANZA_MUESTREO": "Varianza de muestreo (p.p.²)",
    "CV_PORCENTAJE": "Coeficiente de variación de la estimación directa (%)",
}
desc_respuesta = desc.resumen_univariado(
    df_meta,
    [VARIABLE_OBJETIVO, "SE_BOOTSTRAP_PCT", "VARIANZA_MUESTREO", "CV_PORCENTAJE"],
    etiquetas=etiquetas_respuesta,
)
display(spark.createDataFrame(desc_respuesta))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2.1 Distribución de la respuesta y de su error estándar
# MAGIC
# MAGIC **Cómo leer la figura.** La fila superior describe la tasa de desempleo (histograma a
# MAGIC la izquierda, diagrama de caja a la derecha); la inferior, su error estándar. En cada
# MAGIC histograma la línea discontinua roja es la media y la punteada verde la mediana: cuando
# MAGIC se separan, unos pocos dominios extremos arrastran el promedio. En el diagrama de caja,
# MAGIC la caja cubre el 50 % central de los dominios y los puntos aislados son los que quedan
# MAGIC a más de 1,5 rangos intercuartílicos.
# MAGIC
# MAGIC Lo que importa para el modelo es la fila inferior: los dominios con mayor error
# MAGIC estándar son los que el Fay-Herriot contraerá con más fuerza hacia el predictor
# MAGIC sintético, porque su estimación directa es la menos precisa.

# COMMAND ----------

# DBTITLE 1,Figura: distribución de la respuesta y de su error estándar
fig = desc.figura_respuesta(Y, SE)
desc.guardar_figura(fig, "desc_respuesta_precision", VOLUMEN_FIGURAS)
display(fig)
print(desc.interpretar_respuesta(Y, SE, entidades))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2.2 Distribución territorial de la tasa de desempleo
# MAGIC
# MAGIC **Cómo leer la figura.** Cada barra es un dominio, ordenado de menor a mayor tasa; la
# MAGIC línea discontinua es la media de los 23 dominios. La figura muestra la magnitud de la
# MAGIC heterogeneidad territorial que las covariables deberán explicar y nombra qué ciudades
# MAGIC ocupan cada extremo.
# MAGIC
# MAGIC Es una **descripción territorial**, no un contraste de dependencia espacial: no evalúa
# MAGIC si los territorios próximos entre sí tienen tasas parecidas. El modelo Fay-Herriot
# MAGIC clásico del proyecto supone efectos independientes por dominio y no se ajustan
# MAGIC variantes espaciales, de modo que ese contraste no tendría consecuencia sobre ninguna
# MAGIC decisión.

# COMMAND ----------

# DBTITLE 1,Figura: distribución territorial de la tasa de desempleo
fig = desc.figura_territorial(Y, entidades)
desc.guardar_figura(fig, "desc_territorial_respuesta", VOLUMEN_FIGURAS)
display(fig)
print(desc.interpretar_territorial(Y, entidades))

# COMMAND ----------

# DBTITLE 1,Descriptivos de las covariables candidatas
desc_covariables = desc.resumen_univariado(df_cand, CANDIDATAS, etiquetas=NOMBRES)
desc_covariables.insert(1, "Alias", [ALIAS[c] for c in desc_covariables["Codigo"]])
desc_covariables.insert(
    2, "Dimension", [DIMENSION[c] for c in desc_covariables["Codigo"]]
)
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

# MAGIC %md
# MAGIC ## 2.3 Panel de diagramas de caja de las candidatas
# MAGIC
# MAGIC **Cómo leer la figura.** Cada fila es una covariable, estandarizada (media 0 y
# MAGIC desviación 1) solo para poder compararlas en un mismo eje; los datos que entran al
# MAGIC modelo no se transforman. Una caja desplazada respecto a la línea vertical del cero y
# MAGIC un bigote más largo hacia un lado indican asimetría; los puntos rojos son los dominios
# MAGIC extremos según el rango intercuartílico. Las covariables con cajas estrechas y puntos
# MAGIC lejanos son las que concentran su variación en unos pocos territorios.

# COMMAND ----------

# DBTITLE 1,Figura: panel de diagramas de caja de las candidatas
fig = desc.figura_panel_boxplots(df_cand, CANDIDATAS, alias=ALIAS)
desc.guardar_figura(fig, "desc_boxplots_candidatas", VOLUMEN_FIGURAS)
display(fig)
print(desc.interpretar_boxplots(desc_covariables))

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
# MAGIC covariable se incluye ni se excluye aquí por la magnitud de su correlación. La tabla
# MAGIC incluye el signo esperado del catálogo para que la comparación con el observado quede
# MAGIC a la vista; la consecuencia de una discrepancia se decide en la etapa siguiente.

# COMMAND ----------

# DBTITLE 1,Relación de cada candidata con la tasa de desempleo
bivariado = desc.tabla_bivariada(df_cand, CANDIDATAS, Y, alias=ALIAS)
bivariado.insert(2, "Dimension", [DIMENSION[c] for c in bivariado["Codigo"]])
bivariado.insert(3, "Signo_esperado", [SIGNO[c] for c in bivariado["Codigo"]])
display(spark.createDataFrame(bivariado))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3.1 Panel de dispersión de las candidatas frente a la respuesta
# MAGIC
# MAGIC **Cómo leer la figura.** Cada panel enfrenta una covariable (eje horizontal) con la
# MAGIC tasa de desempleo (eje vertical); cada punto es un dominio y la recta discontinua es
# MAGIC el ajuste de mínimos cuadrados, la misma forma lineal que usa el componente sintético
# MAGIC del modelo. El título trae Pearson (r) y Spearman (ρ): cuando difieren de forma
# MAGIC apreciable, la relación lineal depende de unos pocos puntos alejados. Conviene fijarse
# MAGIC en tres cosas: la pendiente de la recta (dirección de la asociación), cuánto se
# MAGIC dispersan los puntos alrededor de ella (fuerza) y si hay un dominio aislado que parece
# MAGIC sostener la pendiente por sí solo (candidato a influyente).

# COMMAND ----------

# DBTITLE 1,Figura: panel de dispersión de las candidatas frente a la respuesta
fig = desc.figura_panel_dispersion(df_cand, CANDIDATAS, Y, alias=ALIAS)
desc.guardar_figura(fig, "desc_dispersion_candidatas", VOLUMEN_FIGURAS)
display(fig)
print(desc.interpretar_dispersion(bivariado, SIGNO))

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
# MAGIC **No se aplica análisis de componentes principales.** Introduciría componentes sin
# MAGIC interpretación territorial directa y una decisión adicional —cuántos componentes
# MAGIC retener— que esta etapa no necesita.
# MAGIC
# MAGIC **Cómo leer la figura.** Rojo indica correlación positiva y azul negativa; la
# MAGIC intensidad, la magnitud. Los bloques de color intenso alrededor de la diagonal son
# MAGIC grupos de covariables que miden lo mismo; un bloque azul intenso fuera de la diagonal
# MAGIC señala dos indicadores que miden lo mismo en sentido inverso.

# COMMAND ----------

# DBTITLE 1,Figura: estructura de correlación entre las candidatas
fig, orden_agrupado = desc.figura_correlacion_agrupada(
    df_cand,
    CANDIDATAS,
    alias=ALIAS,
    titulo="Estructura de correlación entre las covariables candidatas",
)
desc.guardar_figura(fig, "desc_correlacion_candidatas", VOLUMEN_FIGURAS)
display(fig)

# COMMAND ----------

# DBTITLE 1,Pares de covariables fuertemente asociadas entre sí
pares = desc.tabla_pares_correlacionados(
    df_cand, CANDIDATAS, alias=ALIAS, umbral=UMBRAL_REDUNDANCIA
)
display(
    spark.createDataFrame(pares)
    if not pares.empty
    else spark.createDataFrame(
        pd.DataFrame([{"Mensaje": f"Ningún par supera |r| = {UMBRAL_REDUNDANCIA}"}])
    )
)
print(
    desc.interpretar_correlacion(
        pares, orden_agrupado, ALIAS, umbral=UMBRAL_REDUNDANCIA
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC Estos pares señalan información potencialmente redundante. **Ninguna covariable se
# MAGIC descarta por aparecer aquí.** La decisión formal sobre cuál conservar de cada grupo se
# MAGIC toma en la etapa de selección, con un criterio de desempate explícito.

# COMMAND ----------

# DBTITLE 1,Escritura de las tablas descriptivas
(
    spark.createDataFrame(
        pd.concat(
            [
                desc_respuesta.assign(
                    Bloque="Variable respuesta y precisión", Alias=None, Dimension=None
                ),
                desc_covariables.assign(Bloque="Covariables candidatas"),
            ],
            ignore_index=True,
        )
    )
    .write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TBL_DESCRIPTIVO_UNI)
)

(
    spark.createDataFrame(bivariado)
    .write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TBL_DESCRIPTIVO_BI)
)

print(f"Tablas escritas:\n  · {TBL_DESCRIPTIVO_UNI}\n  · {TBL_DESCRIPTIVO_BI}")
print(f"Candidatas caracterizadas: {len(CANDIDATAS)}")
