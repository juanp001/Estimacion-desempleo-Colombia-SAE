# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Diagnóstico y selección final de covariables
# MAGIC
# MAGIC Este notebook **decide**. La caracterización de los datos se hizo antes, en
# MAGIC `analisis_descriptivo`, y no se repite aquí. La selección es **cualitativa**: se
# MAGIC apoya en lo que el análisis descriptivo mostró sobre cada covariable (univariado y
# MAGIC bivariado), en el pre-filtrado y en diagnósticos de estadística básica, y cada
# MAGIC covariable entra o sale por una razón única que se puede leer en su fila de la ficha
# MAGIC de decisión.
# MAGIC
# MAGIC Los 23 dominios son ciudades o ciudades con su área metropolitana («Cali A.M.»); en los 7
# MAGIC dominios A.M. las covariables son el promedio ponderado de sus municipios
# MAGIC (`adicion_covariables`), de modo que respuesta y covariables describen el mismo territorio.
# MAGIC
# MAGIC ## Qué no se hace y por qué
# MAGIC
# MAGIC | Procedimiento | Decisión | Motivo |
# MAGIC |---|---|---|
# MAGIC | Sensibilidad al umbral de correlación | **No se hace** | Contaría cuántas covariables superan umbrales sobre un conjunto ya recortado por ese mismo umbral. |
# MAGIC | Shapiro-Wilk sobre las covariables | **No se hace** | El modelo supone normalidad de los efectos aleatorios y de los errores de muestreo, no de las covariables. |
# MAGIC | Índice de Moran (sobre la respuesta y sobre los residuos) | **No se hace** | El modelo Fay-Herriot clásico supone efectos independientes por dominio y el proyecto no ajusta variantes espaciales, de modo que el contraste no cambia ninguna decisión. |
# MAGIC | Búsqueda exhaustiva de especificaciones por AIC | **No se hace** | Con 23 dominios produciría docenas de especificaciones equivalentes y reutilizaría los datos que ajustan el modelo; la elección entre ellas volvería a ser una regla añadida. La comparación entre especificaciones se hace en el notebook del modelo (significancia de los coeficientes y AIC). |
# MAGIC | Ranking compuesto C y Q, nivel de respaldo L | **No se usan** | Pesos y topes arbitrarios; el nivel L complicaría el análisis sin decidir nada. |
# MAGIC | Modelo Fay-Herriot univariado por covariable | **Se hace** | La respuesta tiene error de muestreo de varianza ψ_d distinta en cada dominio; el modelo la incorpora y la correlación no (G7-B8). Su intervalo para la pendiente decide la elegibilidad; Pearson, Spearman y Fisher quedan como descripción. |
# MAGIC | Influencia y estabilidad | **Se hace** | Distancia de Cook y exclusión de dominios, sobre el mismo Fay-Herriot univariado, como dos evidencias de un único criterio de robustez. |
# MAGIC | Redundancia | **Se hace** | Un representante por grupo de covariables equivalentes. |
# MAGIC | Forma funcional | **Se hace** | Curvatura y escala logarítmica en el Fay-Herriot univariado, y residuos parciales del conjunto elegido (G7-B13). Es un diagnóstico: ninguna covariable se transforma, y la ficha advierte las que conviene revisar. |
# MAGIC | Ficha de decisión | **Se hace** | Reúne por covariable la evidencia descriptiva (signo esperado y observado, intervalo de la correlación), el Fay-Herriot univariado y los diagnósticos, y aplica reglas explícitas. |
# MAGIC
# MAGIC ## Procedimiento de selección
# MAGIC
# MAGIC ```
# MAGIC candidatas conceptualmente elegibles (catálogo de literatura)
# MAGIC   → 1. asociación:   correlación con la respuesta y su intervalo (descripción), Fay-Herriot
# MAGIC                       univariado con ψ_d (decisión y medida única), signo esperado y forma
# MAGIC                       funcional
# MAGIC   → 2. robustez:     se descarta lo que depende de un solo dominio (en el Fay-Herriot univariado)
# MAGIC   → 3. redundancia:  un representante por grupo de covariables equivalentes (el primer
# MAGIC                       integrante elegible por orden de Cook: retroceso)
# MAGIC   → 4. decisión:     elegibles = pendiente del FH univariado con intervalo sin cero (el signo
# MAGIC                       esperado es diagnóstico);
# MAGIC                       seleccionadas = las de mayor correlación ponderada hasta la cota de
# MAGIC                       parsimonia
# MAGIC   → 5. verificación: multicolinealidad y residuos parciales del conjunto elegido
# MAGIC ```
# MAGIC
# MAGIC ## Salidas
# MAGIC
# MAGIC * `tesis.preprocesamiento.diagnosticos_covariables`
# MAGIC * `tesis.preprocesamiento.robustez_covariables`
# MAGIC * `tesis.preprocesamiento.redundancia_covariables`
# MAGIC * `tesis.preprocesamiento.decision_covariables`
# MAGIC * `tesis.preprocesamiento.verificacion_seleccion`
# MAGIC * `tesis.preprocesamiento.trazabilidad_covariables`
# MAGIC * `tesis.preprocesamiento.sensibilidad_signo_covariables`
# MAGIC * `tesis.preprocesamiento.covariables_candidatas` (elegibles)
# MAGIC * `tesis.preprocesamiento.covariables_seleccionadas`
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

from preprocesamiento.shared.config import *
from analisis.shared import descriptivos as desc
from analisis.shared import diagnosticos as diag
from analisis.shared import seleccion as sel
from analisis.shared.catalogo_literatura import resolver_catalogo, mapas_catalogo

# ── Carga ─────────────────────────────────────────────────────────────────────
df_full = spark.table(TBL_PREFILTRADAS)
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
# Varianza de muestreo de la estimación directa de cada dominio, ψ_d = SE² (G7-B8): la misma
# que usa el modelo Fay-Herriot.
PSI = df_meta["SE_BOOTSTRAP_PCT"].astype(float).values ** 2
# Etiqueta de cada dominio: la ciudad o la ciudad con su área metropolitana («Cali A.M.»).
entidades = df_meta["NOMBRE_DOMINIO"].values

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
# MAGIC Se retoma la tabla bivariada del análisis descriptivo (Pearson y Spearman) y se le añade
# MAGIC el **intervalo de confianza de Fisher** del coeficiente de Pearson. Con 23 dominios el error estándar de una
# MAGIC correlación es grande, y un valor puntual comunica más certeza de la que hay.
# MAGIC
# MAGIC **La decisión se toma con el modelo, no con la correlación (G7-B8).** La respuesta es
# MAGIC una estimación directa con error de muestreo, θ̂_d = θ_d + e_d con Var(e_d) = ψ_d, y ψ_d
# MAGIC cambia de un dominio a otro. Pearson y Spearman dan el mismo peso a todos. Por eso se
# MAGIC ajusta, para cada covariable, el **Fay-Herriot univariado**
# MAGIC θ̂_d = β0 + β1·x_d + u_d + e_d, con Var(u_d) = A estimada por REML: la misma estructura
# MAGIC del modelo final, que pesa cada dominio por 1/(Â + ψ_d). Si el intervalo al 95 % de β1
# MAGIC contiene el cero, la evidencia no determina siquiera el signo de la asociación y la
# MAGIC covariable no es elegible. La correlación y su intervalo de Fisher se conservan como
# MAGIC descripción. La columna `r_ponderada` expresa la pendiente del modelo en escala de
# MAGIC correlación y `Razon_pesos` (peso máximo / peso mínimo) muestra cuánto se aparta el
# MAGIC ajuste de uno con pesos iguales.
# MAGIC
# MAGIC **Una sola medida (G7-B13).** La misma correlación ponderada es la que ordena las
# MAGIC elegibles en la parsimonia y fija el signo observado. Antes el orden usaba Spearman cuando
# MAGIC valores extremos condicionaban a Pearson, mientras el intervalo que decidía era de Pearson
# MAGIC y la covariable entraba sin transformar a un modelo lineal: tres medidas para una sola
# MAGIC decisión. Spearman queda como descripción de la asociación monótona.
# MAGIC
# MAGIC **Forma funcional (G7-B13).** Antes de fijar el predictor lineal se examina, en el mismo
# MAGIC modelo univariado, si la relación tiene **curvatura** (prueba de Wald del término
# MAGIC cuadrático de la covariable estandarizada) y si la **escala logarítmica** la describe
# MAGIC mejor (AIC con log(x) frente a x, cuando x es positiva). Es un diagnóstico: ninguna
# MAGIC covariable se transforma de forma automática, porque elegir la escala mirando la
# MAGIC respuesta sería otra selección sobre los mismos 23 dominios, y una transformación tendría
# MAGIC que aplicarse también a los municipios objetivo en el notebook del modelo. Si una
# MAGIC covariable elegible queda en «revisar», la ficha lo advierte.
# MAGIC
# MAGIC No se reportan p-valores. Se evalúan varias covariables sin corrección por
# MAGIC multiplicidad y su interpretación nominal no sería válida; el intervalo comunica la
# MAGIC misma información sin sugerir una precisión inexistente.
# MAGIC
# MAGIC La tabla trae también el **signo esperado** del catálogo. Es un **diagnóstico de
# MAGIC coherencia sustantiva, no un filtro** (G7-B12): una asociación de signo contrario a la
# MAGIC literatura puede contener información, y el signo bivariado no tiene por qué coincidir
# MAGIC con el coeficiente parcial del modelo. La ficha lo registra y lo advierte, y la sección 5
# MAGIC muestra qué cambiaría si se excluyeran las covariables de signo inesperado.

# COMMAND ----------

# DBTITLE 1,Correlación con la respuesta, intervalo de Fisher y signo esperado
bivariado = desc.tabla_bivariada(df_cand, CANDIDATAS, Y, alias=ALIAS)
df_ic = diag.tabla_ic_correlacion(
    df_cand, CANDIDATAS, Y, alias=ALIAS, alfa=ALFA_IC_CORRELACION
)
# Fay-Herriot univariado por covariable, con ψ_d (G7-B8): decide la elegibilidad.
df_fh = diag.fh_univariado(
    df_cand, CANDIDATAS, Y, PSI, alias=ALIAS, alfa=ALFA_IC_CORRELACION
)

df_asociacion = (
    df_ic.merge(bivariado.drop(columns=["Alias", "Pearson_r"]), on="Codigo")
    .merge(df_fh.drop(columns=["Alias"]), on="Codigo")
    .assign(
        Dimension=lambda t: [DIMENSION[c] for c in t["Codigo"]],
        Signo_esperado=lambda t: [SIGNO[c] for c in t["Codigo"]],
    )
    .sort_values("Pearson_r", key=abs, ascending=False)
)
display(spark.createDataFrame(df_asociacion))

n_con_cero = int((df_ic["IC_contiene_cero"] == "sí").sum())
n_con_cero_fh = int((df_fh["IC_FH_contiene_cero"] == "sí").sum())
print(
    f"Intervalo que contiene el cero: {n_con_cero_fh} de {len(CANDIDATAS)} en el Fay-Herriot "
    f"univariado (decide) y {n_con_cero} con Fisher (descriptivo)."
)
print(
    f"Razón entre el mayor y el menor peso 1/(Â + ψ_d): de {df_fh['Razon_pesos'].min():.3f} "
    f"a {df_fh['Razon_pesos'].max():.3f} según la covariable "
    f"(ψ_d entre {PSI.min():.3f} y {PSI.max():.3f}; Â entre {df_fh['A_hat_FH'].min():.2f} "
    f"y {df_fh['A_hat_FH'].max():.2f})."
)

# COMMAND ----------

# DBTITLE 1,Forma funcional en el Fay-Herriot univariado
# Curvatura y escala logarítmica (G7-B13): diagnóstico, no transformación.
df_forma = diag.forma_funcional(
    df_cand, CANDIDATAS, Y, PSI, alias=ALIAS, alfa=ALFA_IC_CORRELACION
)
display(spark.createDataFrame(df_forma))

a_revisar = df_forma.loc[df_forma["Forma_funcional"] == "revisar", "Alias"].tolist()
print(
    f"Forma lineal adecuada en {len(CANDIDATAS) - len(a_revisar)} de {len(CANDIDATAS)} "
    f"candidatas; a revisar: {', '.join(a_revisar) if a_revisar else 'ninguna'}."
)

# COMMAND ----------

# MAGIC %md
# MAGIC # 2. Robustez: ¿la asociación depende de un solo dominio?
# MAGIC
# MAGIC Con 23 observaciones un único territorio puede determinar la pendiente de una
# MAGIC regresión. Se combinan dos evidencias que deben cumplirse **a la vez** para descartar,
# MAGIC ambas sobre el **Fay-Herriot univariado** de la sección 1 (G7-B8):
# MAGIC
# MAGIC * la distancia de Cook señala que un dominio domina el ajuste (umbral 4/n). Es la
# MAGIC   misma fórmula que usa el notebook del modelo (`distancia_cook`), con Â fijo;
# MAGIC * al excluir un dominio y reajustar el modelo, reestimando Â, la correlación ponderada
# MAGIC   cambia más de `UMBRAL_DELTA_LOO` o la pendiente invierte su signo.
# MAGIC
# MAGIC Exigir ambas evita descartar una covariable por tener un valor extremo que, siendo
# MAGIC grande, no altera la relación. La exclusión recorre los 23 dominios.
# MAGIC
# MAGIC **Ninguna observación se elimina.** Los dominios extremos son territorios reales
# MAGIC —capitales de gran tamaño, ciudades con historia de conflicto, periferias con baja
# MAGIC cobertura— y no errores de medición. La consecuencia recae sobre la covariable, que
# MAGIC deja de considerarse utilizable, no sobre el dato.

# COMMAND ----------

# DBTITLE 1,Influencia por dominio (distancia de Cook en el Fay-Herriot univariado)
df_influencia = diag.influencia_fh(df_cand, CANDIDATAS, Y, PSI, entidades, alias=ALIAS)
display(spark.createDataFrame(df_influencia))

# COMMAND ----------

# DBTITLE 1,Estabilidad de la asociación al excluir cada dominio (Fay-Herriot univariado)
df_estabilidad = diag.estabilidad_fh(
    df_cand, CANDIDATAS, Y, PSI, entidades, alias=ALIAS
)
display(spark.createDataFrame(df_estabilidad))

# COMMAND ----------

# MAGIC %md
# MAGIC **Cómo leer la figura.** Cada punto es una covariable. El eje horizontal es la
# MAGIC distancia de Cook máxima entre los 23 dominios (cuánto domina un solo territorio el
# MAGIC Fay-Herriot univariado de la tasa sobre esa covariable) y el vertical es cuánto cambia
# MAGIC la correlación ponderada al excluir el dominio que más la altera. Las líneas grises son los dos
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
# MAGIC Los bloques identificados en el análisis multivariado se resuelven aquí. Los grupos se
# MAGIC forman por **enlace completo** sobre la distancia 1 − |r|, de modo que dentro de un grupo
# MAGIC **todos** los pares tienen correlación de magnitud mayor o igual que
# MAGIC `UMBRAL_REDUNDANCIA`. No se usan componentes conexas: la correlación alta no es
# MAGIC transitiva, y dos covariables con |r| < 0,80 terminarían juntas solo por estar
# MAGIC correlacionadas con una tercera (G7-B10). Dentro de cada grupo entra una sola.
# MAGIC
# MAGIC **Representante con retroceso (G7-B11).** Los integrantes se ordenan por la asociación
# MAGIC menos dependiente de un dominio individual (menor distancia de Cook máxima) y entra el
# MAGIC **primero que cumple las reglas de elegibilidad** de la ficha de decisión (intervalo de
# MAGIC la pendiente del Fay-Herriot univariado sin cero). Si el de menor Cook no es elegible se pasa al siguiente, en
# MAGIC lugar de dejarlo como representante y perder después toda la dimensión. Si ninguno es
# MAGIC elegible, queda el de menor Cook y la ficha lo declara no elegible.
# MAGIC
# MAGIC El orden no usa la magnitud de la correlación con la respuesta. El retroceso consulta
# MAGIC las mismas reglas que la ficha aplicaría de todos modos, de modo que no añade ningún
# MAGIC criterio sobre la variable dependiente: solo evita que el orden de los pasos elimine una
# MAGIC dimensión. Cubrir dimensiones distintas no es una regla impuesta: es la consecuencia
# MAGIC natural de no admitir dos covariables que midan lo mismo.

# COMMAND ----------

# DBTITLE 1,Resolución de redundancia sobre las covariables robustas
cook_por_codigo = df_influencia.set_index("Codigo")["Cook_max"].to_dict()
# Reglas de elegibilidad de la ficha (intervalo del FH univariado), para el retroceso (G7-B11).
df_elegibilidad = sel.evaluar_elegibilidad(
    CANDIDATAS, bivariado, df_ic, SIGNO, fh=df_fh
)

robustas, df_redundancia = sel.resolver_redundancia(
    df_cand,
    supervivientes,
    influencia=cook_por_codigo,
    alias=ALIAS,
    umbral=UMBRAL_REDUNDANCIA,
    elegibilidad=df_elegibilidad,
)
display(spark.createDataFrame(df_redundancia))

# COMMAND ----------

# MAGIC %md
# MAGIC # 4. Ficha de decisión
# MAGIC
# MAGIC Una fila por candidata con toda la evidencia reunida: signo esperado y observado,
# MAGIC coeficiente interpretable, intervalo de la correlación, pendiente del Fay-Herriot
# MAGIC univariado con su intervalo, resultado de robustez y de redundancia. Sobre ella se aplican, en orden, reglas explícitas:
# MAGIC
# MAGIC 1. descartada por robustez → fuera;
# MAGIC 2. redundante con otra (no representante de su grupo) → fuera; con el retroceso del
# MAGIC    paso 3 el representante ya es el primer integrante elegible del grupo;
# MAGIC 3. intervalo de la pendiente del Fay-Herriot univariado que contiene el cero → **no
# MAGIC    elegible**: la evidencia no determina el signo de la asociación (G7-B8);
# MAGIC 4. signo observado contrario al mecanismo del catálogo → **se conserva** y su motivo
# MAGIC    lo advierte: el signo es un diagnóstico que se interpreta en el documento, no un
# MAGIC    filtro (G7-B12);
# MAGIC 5. entre las **elegibles**, se seleccionan las `P_MAXIMO` de mayor correlación
# MAGIC    ponderada del Fay-Herriot univariado en valor absoluto, la misma medida que decide la
# MAGIC    elegibilidad (G7-B13). La cota proviene de la parsimonia del proyecto: con 23 dominios
# MAGIC    el modelo admite del orden de cuatro covariables más el intercepto;
# MAGIC 6. forma funcional a revisar → **se conserva** y su motivo lo advierte: la covariable
# MAGIC    entra en su escala original y la advertencia se resuelve en el documento (G7-B13).
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
    fh=df_fh,
    forma=df_forma,
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
# MAGIC se reportan en `fay_herriot`, que además compara el conjunto con sus variantes
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
# MAGIC **Sensibilidad al signo esperado (G7-B12).** Se repiten la redundancia, la ficha y la
# MAGIC verificación exigiendo el signo esperado como filtro, que era la regla anterior. Si el
# MAGIC conjunto final coincide, el signo no condiciona la selección; si difiere, la tabla dice
# MAGIC qué covariables entran o salen, y el documento interpreta el signo inesperado en lugar
# MAGIC de ocultarlo.

# COMMAND ----------

# DBTITLE 1,Sensibilidad: selección sin las covariables de signo inesperado
df_elegibilidad_signo = sel.evaluar_elegibilidad(
    CANDIDATAS, bivariado, df_ic, SIGNO, exigir_signo=True, fh=df_fh
)
_, df_redundancia_signo = sel.resolver_redundancia(
    df_cand,
    supervivientes,
    influencia=cook_por_codigo,
    alias=ALIAS,
    umbral=UMBRAL_REDUNDANCIA,
    elegibilidad=df_elegibilidad_signo,
)
seleccionadas_signo, df_ficha_signo = sel.ficha_decision(
    CANDIDATAS,
    bivariado,
    df_ic,
    df_robustez,
    df_redundancia_signo,
    signo_esperado=SIGNO,
    alias=ALIAS,
    dimension=DIMENSION,
    p_maximo=P_MAXIMO,
    exigir_signo=True,
    fh=df_fh,
    forma=df_forma,
)
seleccionadas_signo, _, _ = sel.ajustar_por_vif(
    df_cand,
    seleccionadas_signo,
    df_ficha_signo.loc[
        df_ficha_signo["Decision"] == "no seleccionada", "Codigo"
    ].tolist(),
    vif_max=VIF_MAXIMO,
    alias=ALIAS,
)
df_sensibilidad_signo = sel.sensibilidad_signo(
    df_ficha, SELECCIONADAS, df_ficha_signo, seleccionadas_signo, alias=ALIAS
)
display(spark.createDataFrame(df_sensibilidad_signo))

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
# MAGIC **Residuos parciales (G7-B13).** Cada panel muestra, para una covariable seleccionada,
# MAGIC la parte de la tasa que queda tras descontar las demás covariables en el Fay-Herriot con
# MAGIC todo el conjunto. La línea discontinua es la recta del modelo y la roja una curva
# MAGIC suavizada (lowess). Si la forma lineal es adecuada, ambas siguen la misma tendencia; una
# MAGIC curva que se aparta de la recta de forma sistemática, y no solo por uno o dos dominios,
# MAGIC indicaría que el predictor lineal no recoge la relación.

# COMMAND ----------

# DBTITLE 1,Figura: residuos parciales del conjunto seleccionado
fig = diag.figura_residuos_parciales(df_cand, SELECCIONADAS, Y, PSI, alias=ALIAS)
desc.guardar_figura(fig, "eda_residuos_parciales", VOLUMEN_FIGURAS)
display(fig)

# COMMAND ----------

# MAGIC %md
# MAGIC # 6. Trazabilidad
# MAGIC
# MAGIC Una fila por variable de la revisión de literatura, con su recorrido completo: si llegó
# MAGIC a candidata, qué mostró cada diagnóstico, en qué paso quedó fuera y por qué motivo. Las
# MAGIC covariables descartadas durante el pre-filtrado no aparecen aquí una a una porque su
# MAGIC exclusión se explica por el criterio del filtro, registrado en
# MAGIC `cascada_prefiltrado` y en el reporte de variabilidad.

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
        "IC_FH_contiene_cero": None,
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
    fila["IC_FH_contiene_cero"] = ficha_idx.loc[codigo, "IC_FH_contiene_cero"]
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
df_diagnosticos = (
    df_ic.merge(df_fh.drop(columns=["Alias"]), on="Codigo")
    .merge(df_forma.drop(columns=["Alias"]), on="Codigo")
    .merge(df_influencia.drop(columns=["Alias"]), on="Codigo")
    .merge(df_estabilidad.drop(columns=["Alias"]), on="Codigo")
)

for tabla, destino in [
    (df_diagnosticos, TBL_DIAGNOSTICOS),
    (df_robustez, TBL_ROBUSTEZ),
    (df_redundancia, TBL_REDUNDANCIA),
    (df_ficha, TBL_DECISION),
    (df_verificacion, TBL_VERIFICACION),
    (df_trazabilidad, TBL_TRAZABILIDAD),
    (df_sensibilidad_signo, TBL_SENSIBILIDAD_SIGNO),
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


escribir_base(ELEGIBLES, TBL_CANDIDATAS)
display(escribir_base(SELECCIONADAS, TBL_SELECCIONADAS))
