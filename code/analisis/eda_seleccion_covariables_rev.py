# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Diagnóstico y selección final de covariables
# MAGIC
# MAGIC Versión revisada de `Análisis exploratorio`. El notebook original permanece sin
# MAGIC cambios; este escribe en tablas con sufijo `_rev` para poder compararlos.
# MAGIC
# MAGIC Este notebook **decide**. La caracterización de los datos se hizo antes, en
# MAGIC `analisis_descriptivo_rev`, y no se repite aquí. La selección es **cualitativa**: se
# MAGIC apoya en lo que el análisis descriptivo mostró sobre cada covariable (univariado y
# MAGIC bivariado), en el pre-filtrado y en diagnósticos de estadística básica, y cada
# MAGIC covariable entra o sale por una razón única que se puede leer en su fila de la ficha
# MAGIC de decisión.
# MAGIC
# MAGIC ## Qué cambia frente a la versión original
# MAGIC
# MAGIC | Procedimiento original | Decisión | Motivo |
# MAGIC |---|---|---|
# MAGIC | Sensibilidad al umbral de correlación | **Eliminada** | Contaba cuántas covariables superaban umbrales sobre un conjunto ya recortado por ese mismo umbral. |
# MAGIC | Shapiro-Wilk sobre las covariables | **Eliminado** | El modelo supone normalidad de los efectos aleatorios y de los errores de muestreo, no de las covariables. |
# MAGIC | Índice de Moran (sobre la respuesta y sobre los residuos) | **Eliminado** | El modelo Fay-Herriot clásico supone efectos independientes por dominio y el proyecto no ajusta variantes espaciales, de modo que el contraste no cambia ninguna decisión. |
# MAGIC | Búsqueda exhaustiva de especificaciones por AIC | **Eliminada** | Con 23 dominios producía docenas de especificaciones equivalentes y reutilizaba los datos que ajustan el modelo; la elección entre ellas volvía a ser una regla añadida. La comparación entre especificaciones se hace en el notebook del modelo, con AIC, error cuadrático medio y distancia de Cook. |
# MAGIC | Ranking compuesto C y Q, nivel de respaldo L | **Eliminados** | Pesos y topes arbitrarios; el nivel L complicaba el análisis sin decidir nada. |
# MAGIC | Influencia y estabilidad | **Conservado** | Distancia de Cook y exclusión de dominios como dos evidencias de un único criterio de robustez. |
# MAGIC | Redundancia | **Conservado** | Un representante por grupo de covariables equivalentes. |
# MAGIC | — | **Ficha de decisión** | Reúne por covariable la evidencia descriptiva (signo esperado y observado, intervalo de la correlación) y los diagnósticos, y aplica reglas explícitas. |
# MAGIC
# MAGIC ## Procedimiento de selección
# MAGIC
# MAGIC ```
# MAGIC candidatas conceptualmente elegibles (catálogo de literatura)
# MAGIC   → 1. asociación:   correlación con la respuesta, su intervalo y el signo esperado
# MAGIC   → 2. robustez:     se descarta lo que depende de un solo dominio
# MAGIC   → 3. redundancia:  un representante por grupo de covariables equivalentes
# MAGIC   → 4. decisión:     elegibles = intervalo sin cero y signo coherente con el mecanismo;
# MAGIC                       seleccionadas = las de mayor asociación hasta la cota de parsimonia
# MAGIC   → 5. verificación: multicolinealidad del conjunto elegido
# MAGIC ```
# MAGIC
# MAGIC ## Salidas
# MAGIC
# MAGIC * `tesis.preprocesamiento.diagnosticos_covariables_rev`
# MAGIC * `tesis.preprocesamiento.robustez_covariables_rev`
# MAGIC * `tesis.preprocesamiento.redundancia_covariables_rev`
# MAGIC * `tesis.preprocesamiento.decision_covariables_rev`
# MAGIC * `tesis.preprocesamiento.verificacion_seleccion_rev`
# MAGIC * `tesis.preprocesamiento.trazabilidad_covariables_rev`
# MAGIC * `tesis.preprocesamiento.covariables_candidatas_rev` (elegibles)
# MAGIC * `tesis.preprocesamiento.covariables_seleccionadas_rev`
# MAGIC * Figuras en el volumen `figuras_eda`, con prefijo `eda_`.

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
from analisis.shared_rev import diagnosticos as diag
from analisis.shared_rev import seleccion as sel
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
entidades = df_meta["MUNICIPIO"].values

catalogo_activo, reporte_catalogo = resolver_catalogo(
    indicadores_dict, list(df_pd.columns)
)
CANDIDATAS, ALIAS, SIGNO, DIMENSION = mapas_catalogo(catalogo_activo)
df_cand = df_pd[CANDIDATAS].copy()

print(f"Dominios: {len(Y)}  |  Candidatas conceptualmente elegibles: {len(CANDIDATAS)}")

# COMMAND ----------

# MAGIC %md
# MAGIC # 1. Asociación con la respuesta y su incertidumbre
# MAGIC
# MAGIC Se retoma la tabla bivariada del análisis descriptivo (Pearson, Spearman y cuál de los
# MAGIC dos es interpretable para cada covariable) y se le añade el **intervalo de confianza de
# MAGIC Fisher** del coeficiente de Pearson. Con 23 dominios el error estándar de una
# MAGIC correlación es grande, y un valor puntual comunica más certeza de la que hay: un
# MAGIC intervalo que contiene el cero indica que la evidencia no determina siquiera el signo
# MAGIC de la asociación.
# MAGIC
# MAGIC No se reportan p-valores. Se evalúan varias covariables sin corrección por
# MAGIC multiplicidad y su interpretación nominal no sería válida; el intervalo comunica la
# MAGIC misma información sin sugerir una precisión inexistente.
# MAGIC
# MAGIC La tabla trae también el **signo esperado** del catálogo. Una covariable cuyo signo
# MAGIC observado contradice el mecanismo por el que se propuso no puede sustentarse con la
# MAGIC referencia que la respalda; esa comparación es uno de los criterios de la ficha de
# MAGIC decisión.

# COMMAND ----------

# DBTITLE 1,Correlación con la respuesta, intervalo de Fisher y signo esperado
bivariado = desc.tabla_bivariada(df_cand, CANDIDATAS, Y, alias=ALIAS)
df_ic = diag.tabla_ic_correlacion(
    df_cand, CANDIDATAS, Y, alias=ALIAS, alfa=ALFA_IC_CORRELACION
)

df_asociacion = (
    df_ic.merge(bivariado.drop(columns=["Alias", "Pearson_r"]), on="Codigo")
    .assign(
        Dimension=lambda t: [DIMENSION[c] for c in t["Codigo"]],
        Signo_esperado=lambda t: [SIGNO[c] for c in t["Codigo"]],
    )
    .sort_values("Pearson_r", key=abs, ascending=False)
)
display(spark.createDataFrame(df_asociacion))

n_con_cero = int((df_ic["IC_contiene_cero"] == "sí").sum())
print(
    f"{n_con_cero} de {len(CANDIDATAS)} covariables tienen un intervalo que contiene el cero."
)

# COMMAND ----------

# MAGIC %md
# MAGIC # 2. Robustez: ¿la asociación depende de un solo dominio?
# MAGIC
# MAGIC Con 23 observaciones un único territorio puede determinar la pendiente de una
# MAGIC regresión. Se combinan dos evidencias que deben cumplirse **a la vez** para descartar:
# MAGIC
# MAGIC * la distancia de Cook señala que un dominio domina la regresión (umbral 4/n);
# MAGIC * al excluir ese dominio, la correlación cambia más de `UMBRAL_DELTA_LOO` o invierte
# MAGIC   su signo.
# MAGIC
# MAGIC Exigir ambas evita descartar una covariable por tener un valor extremo que, siendo
# MAGIC grande, no altera la relación. La exclusión recorre los 23 dominios.
# MAGIC
# MAGIC **Ninguna observación se elimina.** Los dominios extremos son territorios reales
# MAGIC —capitales de gran tamaño, ciudades con historia de conflicto, periferias con baja
# MAGIC cobertura— y no errores de medición. La consecuencia recae sobre la covariable, que
# MAGIC deja de considerarse utilizable, no sobre el dato.

# COMMAND ----------

# DBTITLE 1,Influencia por dominio (distancia de Cook)
df_influencia = diag.influencia_por_covariable(
    df_cand, CANDIDATAS, Y, entidades, alias=ALIAS
)
display(spark.createDataFrame(df_influencia))

# COMMAND ----------

# DBTITLE 1,Estabilidad de la asociación al excluir cada dominio
df_estabilidad = diag.estabilidad_loo(df_cand, CANDIDATAS, Y, entidades, alias=ALIAS)
display(spark.createDataFrame(df_estabilidad))

# COMMAND ----------

# MAGIC %md
# MAGIC **Cómo leer la figura.** Cada punto es una covariable. El eje horizontal es la
# MAGIC distancia de Cook máxima entre los 23 dominios (cuánto domina un solo territorio la
# MAGIC regresión simple de la tasa sobre esa covariable) y el vertical es cuánto cambia la
# MAGIC correlación al excluir el dominio que más la altera. Las líneas grises son los dos
# MAGIC umbrales. Solo las covariables del cuadrante superior derecho, en rojo, se descartan:
# MAGIC en ellas un dominio domina la regresión *y* su exclusión cambia la asociación. Una
# MAGIC covariable a la derecha pero abajo tiene un dominio extremo que no altera la relación;
# MAGIC una arriba pero a la izquierda cambia algo al excluir un dominio sin que ninguno
# MAGIC domine.

# COMMAND ----------

# DBTITLE 1,Figura: plano de robustez
fig = diag.figura_robustez(df_influencia, df_estabilidad, umbral_delta=UMBRAL_DELTA_LOO)
desc.guardar_figura(fig, "eda_robustez", VOLUMEN_FIGURAS)
display(fig)
print(
    diag.interpretar_robustez(
        df_influencia, df_estabilidad, umbral_delta=UMBRAL_DELTA_LOO
    )
)

# COMMAND ----------

# DBTITLE 1,Filtro de robustez
supervivientes, df_robustez = sel.filtrar_por_robustez(
    CANDIDATAS,
    df_influencia,
    df_estabilidad,
    umbral_delta=UMBRAL_DELTA_LOO,
    alias=ALIAS,
)
display(spark.createDataFrame(df_robustez))

# COMMAND ----------

# MAGIC %md
# MAGIC # 3. Redundancia: un representante por grupo de covariables equivalentes
# MAGIC
# MAGIC Los bloques identificados en el análisis multivariado se resuelven aquí. Dentro de
# MAGIC cada grupo de covariables con correlación de magnitud mayor o igual que
# MAGIC `UMBRAL_REDUNDANCIA` entra una sola, elegida por un desempate determinista: la
# MAGIC asociación menos dependiente de un dominio individual (menor distancia de Cook máxima).
# MAGIC
# MAGIC El criterio no usa la magnitud de la correlación con la respuesta, de modo que resolver
# MAGIC la redundancia no reintroduce selección sobre la variable dependiente. Cubrir
# MAGIC dimensiones distintas no es una regla impuesta: es la consecuencia natural de no admitir
# MAGIC dos covariables que midan lo mismo.

# COMMAND ----------

# DBTITLE 1,Resolución de redundancia sobre las covariables robustas
cook_por_codigo = df_influencia.set_index("Codigo")["Cook_max"].to_dict()

robustas, df_redundancia = sel.resolver_redundancia(
    df_cand,
    supervivientes,
    influencia=cook_por_codigo,
    alias=ALIAS,
    umbral=UMBRAL_REDUNDANCIA,
)
display(spark.createDataFrame(df_redundancia))

# COMMAND ----------

# MAGIC %md
# MAGIC # 4. Ficha de decisión
# MAGIC
# MAGIC Una fila por candidata con toda la evidencia reunida: signo esperado y observado,
# MAGIC coeficiente interpretable, intervalo de la correlación, resultado de robustez y de
# MAGIC redundancia. Sobre ella se aplican, en orden, reglas explícitas:
# MAGIC
# MAGIC 1. descartada por robustez → fuera;
# MAGIC 2. redundante con otra (no representante de su grupo) → fuera;
# MAGIC 3. intervalo de la correlación que contiene el cero → **no elegible**: la evidencia
# MAGIC    no determina el signo de la asociación;
# MAGIC 4. signo observado contrario al mecanismo del catálogo → **no elegible**: la
# MAGIC    covariable no puede sustentarse con la referencia por la que se propuso;
# MAGIC 5. entre las **elegibles**, se seleccionan las `P_MAXIMO` de mayor asociación en
# MAGIC    valor absoluto. La cota proviene de la parsimonia del proyecto: con 23 dominios el
# MAGIC    modelo admite del orden de cuatro covariables más el intercepto.
# MAGIC
# MAGIC Las elegibles que quedan fuera por la cota no son inservibles: son candidatas
# MAGIC legítimas si el número de dominios con encuesta aumenta, y se conservan en la tabla de
# MAGIC candidatas.

# COMMAND ----------

# DBTITLE 1,Ficha de decisión y conjunto seleccionado
SELECCIONADAS, df_ficha = sel.ficha_decision(
    CANDIDATAS,
    bivariado,
    df_ic,
    df_robustez,
    df_redundancia,
    signo_esperado=SIGNO,
    alias=ALIAS,
    dimension=DIMENSION,
    p_maximo=P_MAXIMO,
)
display(spark.createDataFrame(df_ficha))

ELEGIBLES_RESTANTES = df_ficha.loc[
    df_ficha["Decision"] == "no seleccionada", "Codigo"
].tolist()

print("\nCovariables seleccionadas:")
for codigo in SELECCIONADAS:
    print(f"  · {ALIAS[codigo]:20s} {indicadores_dict.get(codigo, codigo)[:60]}")

# COMMAND ----------

# MAGIC %md
# MAGIC # 5. Verificación del conjunto elegido
# MAGIC
# MAGIC **Multicolinealidad.** Si algún factor de inflación de la varianza supera
# MAGIC `VIF_MAXIMO`, la covariable responsable sale del conjunto y entra la siguiente
# MAGIC elegible por asociación; el proceso se repite hasta que el conjunto sea utilizable. Se
# MAGIC calcula sobre el conjunto elegido y no sobre el universo de candidatas: con 23
# MAGIC dominios, un sistema con muchas más covariables que grados de libertad produce un
# MAGIC factor sin sentido.
# MAGIC
# MAGIC Los coeficientes del modelo Fay-Herriot sobre este conjunto, su signo y su precisión
# MAGIC se reportan en `fay_herriot_rev`, que además compara el conjunto con sus variantes
# MAGIC dejando una covariable fuera.

# COMMAND ----------

# DBTITLE 1,Multicolinealidad del conjunto elegido
SELECCIONADAS, df_vif, sustituciones = sel.ajustar_por_vif(
    df_cand, SELECCIONADAS, ELEGIBLES_RESTANTES, vif_max=VIF_MAXIMO, alias=ALIAS
)
display(spark.createDataFrame(df_vif))

if sustituciones:
    # La ficha refleja el conjunto final, no el previo a la verificación.
    for mensaje in sustituciones:
        print(f"  sustitución: {mensaje}")
    df_ficha["Decision"] = np.where(
        df_ficha["Codigo"].isin(SELECCIONADAS),
        "seleccionada",
        np.where(
            df_ficha["Decision"] == "seleccionada",
            "no seleccionada",
            df_ficha["Decision"],
        ),
    )
    df_ficha["Motivo"] = np.where(
        df_ficha["Decision"].isin(["seleccionada", "no seleccionada"]),
        df_ficha["Motivo"] + " (ajustado por multicolinealidad)",
        df_ficha["Motivo"],
    )

df_verificacion = df_vif.assign(
    Umbral_VIF=VIF_MAXIMO,
    Sustituciones="; ".join(sustituciones) if sustituciones else "ninguna",
)

# COMMAND ----------

# MAGIC %md
# MAGIC **Cómo leer la figura.** Matriz de correlación entre las covariables que entran al
# MAGIC modelo. Tras la resolución de redundancia y la verificación de multicolinealidad no
# MAGIC debe aparecer ningún par con color intenso; si lo hubiera, el factor de inflación de la
# MAGIC varianza de la celda anterior lo habría señalado.

# COMMAND ----------

# DBTITLE 1,Figura: correlación entre las covariables seleccionadas
fig, _ = desc.figura_correlacion_agrupada(
    df_cand,
    SELECCIONADAS,
    alias=ALIAS,
    titulo="Correlación entre las covariables seleccionadas",
)
desc.guardar_figura(fig, "eda_correlacion_finales", VOLUMEN_FIGURAS)
display(fig)

# COMMAND ----------

# MAGIC %md
# MAGIC # 6. Trazabilidad
# MAGIC
# MAGIC Una fila por variable de la revisión de literatura, con su recorrido completo: si llegó
# MAGIC a candidata, qué mostró cada diagnóstico, en qué paso quedó fuera y por qué motivo. Las
# MAGIC covariables descartadas durante el pre-filtrado no aparecen aquí una a una porque su
# MAGIC exclusión se explica por el criterio del filtro, registrado en
# MAGIC `cascada_prefiltrado_rev` y en el reporte de variabilidad.

# COMMAND ----------

# DBTITLE 1,Tabla maestra de trazabilidad
ficha_idx = df_ficha.set_index("Codigo")
influencia_idx = df_influencia.set_index("Codigo")
estabilidad_idx = df_estabilidad.set_index("Codigo")
redundancia_idx = df_redundancia.set_index("Codigo")

filas_traza = []
for _, entrada in reporte_catalogo.iterrows():
    codigo = entrada["Codigo"]
    fila = {
        "Alias": entrada["Alias"],
        "Codigo": codigo,
        "Dimension": entrada["Dimension"],
        "Signo_esperado": entrada["Signo_esperado"],
        "Prefiltrado": entrada["Estado"],
        "Pearson_r": None,
        "IC_contiene_cero": None,
        "Signo_observado": None,
        "Cook_max": None,
        "Delta_LOO_max": None,
        "Robustez": None,
        "Grupo_redundancia": None,
        "Representante": None,
        "Decision_final": None,
        "Motivo_final": None,
    }

    if entrada["Estado"] != "activa":
        fila["Decision_final"] = "no evaluada"
        fila["Motivo_final"] = entrada["Estado"]
        filas_traza.append(fila)
        continue

    fila["Pearson_r"] = float(ficha_idx.loc[codigo, "r_interpretable"])
    fila["IC_contiene_cero"] = ficha_idx.loc[codigo, "IC_contiene_cero"]
    fila["Signo_observado"] = ficha_idx.loc[codigo, "Signo_observado"]
    fila["Cook_max"] = float(influencia_idx.loc[codigo, "Cook_max"])
    fila["Delta_LOO_max"] = float(estabilidad_idx.loc[codigo, "Delta_max_abs"])
    fila["Robustez"] = ficha_idx.loc[codigo, "Robustez"]
    if codigo in redundancia_idx.index:
        fila["Grupo_redundancia"] = int(redundancia_idx.loc[codigo, "Grupo"])
        fila["Representante"] = redundancia_idx.loc[codigo, "Representante"]
    else:
        fila["Representante"] = "no evaluada"
    fila["Decision_final"] = ficha_idx.loc[codigo, "Decision"]
    fila["Motivo_final"] = ficha_idx.loc[codigo, "Motivo"]
    filas_traza.append(fila)

df_trazabilidad = pd.DataFrame(filas_traza)
display(spark.createDataFrame(df_trazabilidad))

# COMMAND ----------

# DBTITLE 1,Escritura de las tablas de diagnóstico y trazabilidad
df_diagnosticos = df_ic.merge(df_influencia.drop(columns=["Alias"]), on="Codigo").merge(
    df_estabilidad.drop(columns=["Alias"]), on="Codigo"
)

for tabla, destino in [
    (df_diagnosticos, TBL_DIAGNOSTICOS_REV),
    (df_robustez, TBL_ROBUSTEZ_REV),
    (df_redundancia, TBL_REDUNDANCIA_REV),
    (df_ficha, TBL_DECISION_REV),
    (df_verificacion, TBL_VERIFICACION_REV),
    (df_trazabilidad, TBL_TRAZABILIDAD_REV),
]:
    (
        spark.createDataFrame(tabla)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(destino)
    )
    print(f"Tabla escrita: {destino}")

# COMMAND ----------

# DBTITLE 1,Escritura de las bases de candidatas y de covariables seleccionadas
# Se escriben dos tablas con propósitos distintos:
#  · candidatas: todas las covariables elegibles (seleccionadas o no), por si el número de
#    dominios con encuesta aumenta o se quiere ajustar una especificación alternativa.
#  · seleccionadas: únicamente las covariables del conjunto elegido, que es la entrada del
#    notebook del modelo.
ELEGIBLES = df_ficha.loc[
    df_ficha["Decision"].isin(["seleccionada", "no seleccionada"]), "Codigo"
].tolist()


def escribir_base(codigos, destino):
    """Escribe los metadatos más las covariables indicadas, renombradas a su alias.

    Args:
        codigos (list[str]): Códigos de indicador a incluir.
        destino (str): Nombre completo de la tabla Unity Catalog.

    Returns:
        pyspark.sql.DataFrame: La tabla escrita, para mostrarla.
    """
    cols = METADATA_COLS + [c for c in codigos if c not in METADATA_COLS]
    base = df_full.select(cols)
    for codigo in codigos:
        base = base.withColumnRenamed(codigo, ALIAS[codigo])
    base.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(destino)
    print(f"Tabla escrita: {destino}  ({[ALIAS[c] for c in codigos]})")
    return base


escribir_base(ELEGIBLES, TBL_CANDIDATAS_REV)
display(escribir_base(SELECCIONADAS, TBL_SELECCIONADAS_REV))
