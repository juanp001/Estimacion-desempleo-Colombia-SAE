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
# MAGIC | Índice de Moran (sobre la respuesta y sobre los residuos) | **No se hace aquí** | El selector de covariables no lo necesita: el contraste de dependencia espacial se aplica a los residuos del benchmark y de las variantes espaciales en `modelo/fay_herriot_espacial.py`, donde sí informa la comparación entre el Fay-Herriot clásico y el espacial. |
# MAGIC | Búsqueda exhaustiva de especificaciones por AIC | **No se hace** | Con 23 dominios produciría docenas de especificaciones equivalentes y reutilizaría los datos que ajustan el modelo; la elección entre ellas volvería a ser una regla añadida. La comparación entre especificaciones se hace en el notebook del modelo (significancia de los coeficientes y AIC). |
# MAGIC | Ranking compuesto C y Q, nivel de respaldo L | **No se usan** | Pesos y topes arbitrarios; el nivel L complicaría el análisis sin decidir nada. |
# MAGIC | Modelo Fay-Herriot univariado por covariable | **Se hace** | La respuesta tiene error de muestreo de varianza ψ_d distinta en cada dominio; el modelo la incorpora y la correlación no (G7-B8). Su p-valor para la pendiente, ajustado por Benjamini-Hochberg sobre todas las candidatas (G7-B9), decide la elegibilidad; Pearson, Spearman y Fisher quedan como descripción. |
# MAGIC | Filtro de robustez (Cook y dejar-uno-fuera) | **No se aplica como filtro (R-03)** | La regla `4/n` sirve para inspeccionar observaciones, no para excluir variables; el umbral de cambio (0,10) queda por debajo del error de muestreo de r con n = 23 y separaba casos casi idénticos. Morales et al. (pp. 453-454) no usan la influencia como criterio de selección. |
# MAGIC | Influencia y estabilidad | **Se hace, como diagnóstico** | Distancia de Cook y exclusión de dominios, sobre el mismo Fay-Herriot univariado. Se reportan en la ficha (`Robustez`) y su motivo advierte las covariables elegibles que dependen de un dominio; ninguna se descarta. |
# MAGIC | Soporte en los municipios objetivo | **Se hace, como advertencia (R-02)** | Proporción de los municipios objetivo dentro del rango [mín, máx] de los dominios, sin usar la respuesta. La ficha advierte las que extrapolan (por debajo de `SOPORTE_MINIMO`). Una covariable incompleta en los objetivos no es candidata (condición (iii) del catálogo). |
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
# MAGIC   → 2. robustez:     diagnóstico de si la asociación depende de un solo dominio (en el
# MAGIC                       Fay-Herriot univariado); se reporta, no descarta
# MAGIC   → 3. redundancia:  un representante por grupo de covariables equivalentes (el primer
# MAGIC                       integrante elegible por orden de Cook: retroceso)
# MAGIC   → 4. decisión:     elegibles = pendiente del FH univariado con q de Benjamini-Hochberg
# MAGIC                       ≤ Q_FDR_ELEGIBILIDAD (el signo esperado es diagnóstico);
# MAGIC                       seleccionadas = las de mayor correlación ponderada hasta la cota de
# MAGIC                       parsimonia, `cota_covariables(n)` = n // 10 (R-07); el soporte en los
# MAGIC                       objetivos se advierte
# MAGIC   → 5. verificación: multicolinealidad y residuos parciales del conjunto elegido
# MAGIC ```
# MAGIC
# MAGIC ## Salidas
# MAGIC
# MAGIC * `tesis.preprocesamiento.diagnosticos_covariables` (incluye la lectura de robustez)
# MAGIC * `tesis.preprocesamiento.soporte_covariables`
# MAGIC * `tesis.preprocesamiento.redundancia_covariables`
# MAGIC * `tesis.preprocesamiento.decision_covariables`
# MAGIC * `tesis.preprocesamiento.verificacion_seleccion`
# MAGIC * `tesis.preprocesamiento.trazabilidad_covariables`
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
    """Ruta absoluta de `code/`, tanto en ejecución interactiva como en un job.

    Resuelve el directorio con el contexto de `dbutils` cuando corre como notebook o job y, si
    no existe (ejecución local), usa el directorio padre del directorio de trabajo.

    Returns:
        str: Ruta del directorio `code/` del repositorio.

    Example:
        >>> _directorio_codigo()  # doctest: +SKIP
        '/Workspace/Users/usuario/.bundle/.../files/code'
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
from analisis.shared import descriptivos as desc
from analisis.shared import diagnosticos as diag
from analisis.shared import seleccion as sel
from analisis.shared.datos_analisis import cargar_datos_analisis

# ── Carga (la misma que analisis_descriptivo, R-32) ──────────────────────────
datos = cargar_datos_analisis(
    spark,
    TBL_PREFILTRADAS,
    TBL_DIM_INDICADORES,
    METADATA_COLS,
    VARIABLE_OBJETIVO,
    tabla_objetivos=TBL_SIN_ENCUESTA,
)
df_full = datos["df_full"]
indicadores_dict = datos["indicadores_dict"]
df_meta, df_pd = datos["df_meta"], datos["df_pd"]
# PSI = ψ_d = SE² (G7-B8): la misma varianza de muestreo que usa el modelo Fay-Herriot.
Y, PSI, entidades = datos["Y"], datos["PSI"], datos["entidades"]
reporte_catalogo = datos["reporte_catalogo"]
CANDIDATAS, ALIAS, SIGNO, DIMENSION = (
    datos["CANDIDATAS"],
    datos["ALIAS"],
    datos["SIGNO"],
    datos["DIMENSION"],
)
df_cand = datos["df_cand"]
# Municipios objetivo con las candidatas (R-02): mide el soporte y exige completitud.
df_objetivos = datos["df_objetivos"]

print(f"Dominios: {len(Y)}  |  Candidatas conceptualmente elegibles: {len(CANDIDATAS)}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Una sola cadena (R-32).** Los pasos de selección (Fay-Herriot univariado, robustez,
# MAGIC redundancia, ficha de decisión y verificación de multicolinealidad) se ejecutan con
# MAGIC `sel.ejecutar_seleccion`, la misma función que repite el notebook del modelo dentro de
# MAGIC su validación cruzada. Las secciones siguientes muestran el resultado de cada paso.

# COMMAND ----------

# DBTITLE 1,Ejecución de la cadena de selección
# Cota de parsimonia calculada desde n (R-07): 23 dominios → 2 covariables.
P_MAXIMO = cota_covariables(len(Y))
print(f"Cota de covariables: {P_MAXIMO} ({OBS_POR_PARAMETRO} dominios por covariable)")
try:
    SELECCION = sel.ejecutar_seleccion(
        df_cand,
        CANDIDATAS,
        Y,
        PSI,
        entidades,
        SIGNO,
        alias=ALIAS,
        dimension=DIMENSION,
        p_maximo=P_MAXIMO,
        q_fdr=Q_FDR_ELEGIBILIDAD,
        umbral_delta=UMBRAL_DELTA_LOO,
        umbral_redundancia=UMBRAL_REDUNDANCIA,
        vif_max=VIF_MAXIMO,
        alfa_ic=ALFA_IC_CORRELACION,
        df_objetivos=df_objetivos,
        soporte_minimo=SOPORTE_MINIMO,
        con_forma=True,
        silencioso=False,
    )
except sel.SeleccionVaciaError as error:
    # Sin covariables elegibles el modelo sería solo de intercepto (R-01): no se escribe una
    # tabla de seleccionadas vacía y el job se detiene para que se revise la ficha.
    raise RuntimeError(
        "Ninguna candidata resulta elegible; el Fay-Herriot sería un modelo de solo "
        "intercepto. No se escriben tablas: revisar los diagnósticos y el catálogo."
    ) from error
# Fay-Herriot univariado (G7-B8) y forma funcional de las elegibles (R-62).
df_fh, df_forma = SELECCION["df_fh"], SELECCION["df_forma"]
# Intervalo de Fisher: solo descripción en la tabla bivariada, ya no entra a la ficha (R-62).
df_ic = diag.tabla_ic_correlacion(
    df_cand, CANDIDATAS, Y, alias=ALIAS, alfa=ALFA_IC_CORRELACION
)
df_influencia, df_estabilidad = (
    SELECCION["df_influencia"],
    SELECCION["df_estabilidad"],
)

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
# MAGIC del modelo final, que pesa cada dominio por 1/(Â + ψ_d). Su intervalo al 95 % de β1 y
# MAGIC su p-valor describen la asociación; la elegibilidad la decide el q de
# MAGIC Benjamini-Hochberg (ver «Multiplicidad»). La correlación y su intervalo de Fisher se conservan como
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
# MAGIC covariable elegible queda en «revisar», la ficha lo advierte. Se calcula solo para las
# MAGIC candidatas elegibles (R-62); las que ya quedaron fuera por la asociación no se examinan.
# MAGIC
# MAGIC **Multiplicidad (G7-B9).** Exigir que el intervalo al 95 % de cada candidata excluya el
# MAGIC cero es la misma prueba al 5 % repetida 19 veces sin corrección. Por eso la elegibilidad
# MAGIC se decide con el p-valor de β1 ajustado por **Benjamini-Hochberg** sobre todas las
# MAGIC candidatas (`q_FH`): es elegible la que tiene `q_FH ≤ Q_FDR_ELEGIBILIDAD` (0,10), lo que
# MAGIC controla en 10 % la proporción esperada de falsos descubrimientos entre las elegibles. Es
# MAGIC un tamizaje previo al modelo; la decisión final sobre los coeficientes la toma el
# MAGIC notebook del modelo. La estabilidad de la selección frente al remuestreo de dominios no se
# MAGIC calcula aquí (R-62): la frecuencia con que se elige cada covariable al repetir toda la
# MAGIC cadena es `fh_validacion_cruzada_frecuencia` (G7-B19, notebook del modelo).
# MAGIC
# MAGIC La tabla trae también el **signo esperado** del catálogo. Es un **diagnóstico de
# MAGIC coherencia sustantiva, no un filtro** (G7-B12): una asociación de signo contrario a la
# MAGIC literatura puede contener información, y el signo bivariado no tiene por qué coincidir
# MAGIC con el coeficiente parcial del modelo. La ficha lo registra y lo advierte, y la sección 5
# MAGIC muestra qué cambiaría si se excluyeran las covariables de signo inesperado.

# COMMAND ----------

# DBTITLE 1,Correlación con la respuesta, intervalo de Fisher y signo esperado
bivariado = desc.tabla_bivariada(df_cand, CANDIDATAS, Y, alias=ALIAS)

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
n_q = int((df_fh["q_FH"] <= Q_FDR_ELEGIBILIDAD).sum())
print(
    f"Con q de Benjamini-Hochberg ≤ {Q_FDR_ELEGIBILIDAD}: {n_q} de {len(CANDIDATAS)} (decide). "
    f"Intervalo al 95 % sin cero, sin corrección: {len(CANDIDATAS) - n_con_cero_fh} en el "
    f"Fay-Herriot univariado y {len(CANDIDATAS) - n_con_cero} con Fisher (descriptivos)."
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
display(spark.createDataFrame(df_forma))

a_revisar = df_forma.loc[df_forma["Forma_funcional"] == "revisar", "Alias"].tolist()
print(
    f"Forma lineal adecuada en {len(df_forma) - len(a_revisar)} de {len(df_forma)} "
    f"candidatas elegibles; a revisar: {', '.join(a_revisar) if a_revisar else 'ninguna'}."
)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Soporte en los municipios objetivo (R-02)
# MAGIC
# MAGIC El modelo se usa para predecir los municipios sin encuesta con `x'β̂`, pero la asociación se
# MAGIC mide solo en los 23 dominios urbanos. Para cada candidata se calcula, **sin usar la
# MAGIC respuesta**, qué proporción de los municipios objetivo cae dentro del rango [mín, máx] de
# MAGIC los dominios: fuera de él la predicción extrapola y su varianza crece con la distancia a la
# MAGIC muestra (Morales et al., p. 441), y un buen ajuste dentro de la muestra puede dar
# MAGIC predicciones absurdas fuera de ella (p. 453). Es una **advertencia, no un filtro**: por
# MAGIC debajo de `SOPORTE_MINIMO` la ficha lo dice en el motivo de la covariable. La completitud sí
# MAGIC es condición del catálogo (iii): una candidata con faltantes en los objetivos no entra.

# COMMAND ----------

# DBTITLE 1,Soporte de cada candidata en los municipios objetivo
df_soporte = SELECCION["soporte"]
display(spark.createDataFrame(df_soporte))
con_aviso = df_soporte.loc[df_soporte["Soporte"] == "advertencia", "Alias"].tolist()
print(
    f"Soporte ≥ {SOPORTE_MINIMO:.0%} de los objetivos en el rango de los dominios: "
    f"{len(CANDIDATAS) - len(con_aviso)} de {len(CANDIDATAS)} candidatas; con advertencia: "
    f"{', '.join(con_aviso) if con_aviso else 'ninguna'}."
)

# COMMAND ----------

# MAGIC %md
# MAGIC # 2. Robustez: ¿la asociación depende de un solo dominio?
# MAGIC
# MAGIC Con 23 observaciones un único territorio puede determinar la pendiente de una
# MAGIC regresión. Se calculan dos evidencias sobre el **Fay-Herriot univariado** de la sección 1
# MAGIC (G7-B8) y se **reportan como diagnóstico (R-03), no como filtro**:
# MAGIC
# MAGIC * la distancia de Cook señala que un dominio domina el ajuste (umbral 4/n). Es la
# MAGIC   misma fórmula que usa el notebook del modelo (`distancia_cook`), con Â fijo;
# MAGIC * al excluir un dominio y reajustar el modelo, reestimando Â, la correlación ponderada
# MAGIC   cambia más de `UMBRAL_DELTA_LOO` o la pendiente invierte su signo.
# MAGIC
# MAGIC Una covariable «depende de un dominio» si se cumplen ambas (evaluadas sobre cualquier
# MAGIC dominio). Antes eso la descartaba; con 23 dominios eliminó 12 de 19 candidatas, cuatro
# MAGIC con q ≤ 0,10. `4/n` es una regla para inspeccionar observaciones, no para excluir variables,
# MAGIC y el umbral de 0,10 queda por debajo del error de muestreo de r con n = 23. Ahora la
# MAGIC covariable sigue compitiendo y, si resulta elegible, su motivo en la ficha advierte la
# MAGIC dependencia para que se interprete en el documento. La exclusión recorre los 23 dominios.
# MAGIC
# MAGIC **Ninguna observación se elimina.** Los dominios extremos son territorios reales
# MAGIC —capitales de gran tamaño, ciudades con historia de conflicto, periferias con baja
# MAGIC cobertura— y no errores de medición.

# COMMAND ----------

# COMMAND ----------

# DBTITLE 1,Influencia por dominio (distancia de Cook en el Fay-Herriot univariado)
display(spark.createDataFrame(df_influencia))

# COMMAND ----------

# DBTITLE 1,Estabilidad de la asociación al excluir cada dominio (Fay-Herriot univariado)
display(spark.createDataFrame(df_estabilidad))

# COMMAND ----------

# MAGIC %md
# MAGIC **Cómo leer la figura.** Cada punto es una covariable. El eje horizontal es la
# MAGIC distancia de Cook máxima entre los 23 dominios (cuánto domina un solo territorio el
# MAGIC Fay-Herriot univariado de la tasa sobre esa covariable) y el vertical es cuánto cambia
# MAGIC la correlación ponderada al excluir el dominio que más la altera. Las líneas grises son los dos
# MAGIC umbrales. Las covariables del cuadrante superior derecho, en rojo, «dependen de un
# MAGIC dominio»: en ellas un dominio domina la regresión *y* su exclusión cambia la asociación
# MAGIC (o invierte su signo); se reportan, no se descartan. Una
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

# DBTITLE 1,Diagnóstico de robustez
df_robustez = SELECCION["df_robustez"]
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

# DBTITLE 1,Resolución de redundancia sobre las candidatas
# Con el retroceso (G7-B11) el representante usa las reglas de elegibilidad de la ficha
# (q de Benjamini-Hochberg del FH univariado), df_elegibilidad.
df_elegibilidad = SELECCION["df_elegibilidad"]
df_redundancia = SELECCION["df_redundancia"]
display(spark.createDataFrame(df_redundancia))

# COMMAND ----------

# MAGIC %md
# MAGIC # 4. Ficha de decisión
# MAGIC
# MAGIC Una fila por candidata con toda la evidencia reunida: signo esperado y observado,
# MAGIC coeficiente interpretable, intervalo de la correlación, pendiente del Fay-Herriot
# MAGIC univariado con su intervalo, lectura de robustez, soporte en los objetivos y redundancia.
# MAGIC Sobre ella se aplican, en orden, reglas explícitas:
# MAGIC
# MAGIC 1. la robustez (R-03) y el soporte (R-02) son **diagnósticos, no filtros**: no descartan,
# MAGIC    pero el motivo de una covariable elegible advierte si depende de un dominio o extrapola;
# MAGIC 2. redundante con otra (no representante de su grupo) → fuera; con el retroceso del
# MAGIC    paso 3 el representante ya es el primer integrante elegible del grupo;
# MAGIC 3. p-valor de la pendiente del Fay-Herriot univariado (G7-B8) con q de
# MAGIC    Benjamini-Hochberg mayor que `Q_FDR_ELEGIBILIDAD` → **no elegible**: la evidencia no
# MAGIC    alcanza para distinguir la asociación del azar entre las candidatas evaluadas
# MAGIC    (G7-B9);
# MAGIC 4. signo observado contrario a la asociación del catálogo → **se conserva** y su motivo
# MAGIC    lo advierte: el signo es un diagnóstico que se interpreta en el documento, no un
# MAGIC    filtro (G7-B12);
# MAGIC 5. entre las **elegibles**, se seleccionan las `P_MAXIMO` de mayor correlación
# MAGIC    ponderada del Fay-Herriot univariado en valor absoluto, la misma medida que decide la
# MAGIC    elegibilidad (G7-B13). La cota se calcula desde n (R-07): `cota_covariables(n)` =
# MAGIC    n // 10, es decir 2 con 23 dominios. Es la regla de 10 observaciones por parámetro
# MAGIC    (convención externa a Morales et al., que piden no sobreparametrizar al predecir fuera
# MAGIC    de la muestra, p. 453). Con una cota de 2, el modelo compara EC1 con las variantes que
# MAGIC    quitan una covariable, así que un conjunto de 2 incluye también cada covariable sola;
# MAGIC 6. forma funcional a revisar → **se conserva** y su motivo lo advierte: la covariable
# MAGIC    entra en su escala original y la advertencia se resuelve en el documento (G7-B13).
# MAGIC
# MAGIC Las elegibles que quedan fuera por la cota no son inservibles: son candidatas
# MAGIC legítimas si el número de dominios con encuesta aumenta, y se conservan en la tabla de
# MAGIC candidatas.

# COMMAND ----------

# DBTITLE 1,Ficha de decisión y conjunto seleccionado
# La ficha ya refleja el conjunto final, tras la verificación de multicolinealidad de la
# sección 5 (las que entran o salen por VIF llevan la nota en su motivo).
df_ficha = SELECCION["ficha"]
SELECCIONADAS = SELECCION["seleccionadas"]
display(spark.createDataFrame(df_ficha))

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
df_vif, sustituciones = SELECCION["df_vif"], SELECCION["sustituciones"]
display(spark.createDataFrame(df_vif))
for mensaje in sustituciones:
    print(f"  sustitución: {mensaje}")

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
# Reutiliza los diagnósticos de la cadena principal; solo cambia la regla de elegibilidad.
try:
    SELECCION_SIGNO = sel.ejecutar_seleccion(
        df_cand,
        CANDIDATAS,
        Y,
        PSI,
        entidades,
        SIGNO,
        alias=ALIAS,
        dimension=DIMENSION,
        p_maximo=P_MAXIMO,
        q_fdr=Q_FDR_ELEGIBILIDAD,
        umbral_delta=UMBRAL_DELTA_LOO,
        umbral_redundancia=UMBRAL_REDUNDANCIA,
        vif_max=VIF_MAXIMO,
        alfa_ic=ALFA_IC_CORRELACION,
        exigir_signo=True,
        diagnosticos=SELECCION,
    )
    df_ficha_signo = SELECCION_SIGNO["ficha"]
    seleccionadas_signo = SELECCION_SIGNO["seleccionadas"]
except sel.SeleccionVaciaError:
    # Si todas las elegibles tienen el signo contrario al esperado, exigirlo no deja ninguna: el
    # resultado de la sensibilidad es el conjunto vacío, no un error del notebook.
    seleccionadas_signo = []
    df_ficha_signo = df_ficha.assign(
        Decision=np.where(
            df_ficha["Decision"].isin(["seleccionada", "no seleccionada"]),
            "no elegible",
            df_ficha["Decision"],
        )
    )
df_sensibilidad_signo = sel.sensibilidad_signo(
    df_ficha, SELECCIONADAS, df_ficha_signo, seleccionadas_signo, alias=ALIAS
)
# R-62: el resultado es una línea impresa, no una tabla (sin tabla en Unity Catalog).
print(
    "Sensibilidad al signo esperado (selección exigiendo el signo): "
    + df_sensibilidad_signo.loc[1, "Diferencia_con_base"]
    + f". Elegibles de signo inesperado en el base: "
    + df_sensibilidad_signo.loc[0, "Elegibles_signo_inesperado"]
    + "."
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
ic_idx = df_ic.set_index("Codigo")
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
        "r_ponderada": None,
        "IC_contiene_cero": None,
        "IC_FH_contiene_cero": None,
        "q_FH": None,
        "Signo_observado": None,
        "Cook_max": None,
        "Delta_LOO_max": None,
        "Robustez": None,
        "Prop_objetivos_en_rango": None,
        "Soporte": None,
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

    fila["r_ponderada"] = float(ficha_idx.loc[codigo, "r_interpretable"])
    fila["IC_contiene_cero"] = ic_idx.loc[codigo, "IC_contiene_cero"]
    fila["IC_FH_contiene_cero"] = ficha_idx.loc[codigo, "IC_FH_contiene_cero"]
    fila["q_FH"] = float(ficha_idx.loc[codigo, "q_FH"])
    fila["Signo_observado"] = ficha_idx.loc[codigo, "Signo_observado"]
    fila["Cook_max"] = float(influencia_idx.loc[codigo, "Cook_max"])
    fila["Delta_LOO_max"] = float(estabilidad_idx.loc[codigo, "Delta_max_abs"])
    fila["Robustez"] = ficha_idx.loc[codigo, "Robustez"]
    fila["Prop_objetivos_en_rango"] = ficha_idx.loc[codigo, "Prop_objetivos_en_rango"]
    fila["Soporte"] = ficha_idx.loc[codigo, "Soporte"]
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
    .merge(df_forma.drop(columns=["Alias"]), on="Codigo", how="left")
    .merge(df_influencia.drop(columns=["Alias"]), on="Codigo")
    .merge(df_estabilidad.drop(columns=["Alias"]), on="Codigo")
    # R-63: la lectura de robustez va aquí en lugar de una tabla aparte que repetía
    # Cook_max, Delta_LOO_max e Invierte_signo.
    .merge(
        df_robustez[["Codigo", "Lectura", "Motivo"]].rename(
            columns={"Lectura": "Robustez_lectura", "Motivo": "Robustez_nota"}
        ),
        on="Codigo",
    )
)

for tabla, destino in [
    (df_diagnosticos, TBL_DIAGNOSTICOS),
    (df_redundancia, TBL_REDUNDANCIA),
    (df_soporte, TBL_SOPORTE),
    (df_ficha, TBL_DECISION),
    (df_verificacion, TBL_VERIFICACION),
    (df_trazabilidad, TBL_TRAZABILIDAD),
]:
    (
        spark.createDataFrame(tabla)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(destino)
    )
    print(f"Tabla escrita: {destino}")

# COMMAND ----------

# DBTITLE 1,Escritura de la base de covariables seleccionadas
# Solo las covariables del conjunto elegido, que es la entrada del notebook del modelo. Las
# elegibles que quedaron fuera por la cota se consultan en `decision_covariables`
# (Decision = «no seleccionada»); ya no se escribe una tabla aparte de candidatas (R-63).


def escribir_base(codigos, destino):
    """Escribe los metadatos más las covariables indicadas, renombradas a su alias.

    Args:
        codigos (list[str]): Códigos de indicador a incluir.
        destino (str): Nombre completo de la tabla Unity Catalog.

    Returns:
        pyspark.sql.DataFrame: La tabla escrita, para mostrarla.

    Example:
        >>> escribir_base(SELECCIONADAS, TBL_SELECCIONADAS)  # doctest: +SKIP
    """
    cols = METADATA_COLS + [c for c in codigos if c not in METADATA_COLS]
    base = df_full.select(cols)
    for codigo in codigos:
        base = base.withColumnRenamed(codigo, ALIAS[codigo])
    base.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(destino)
    print(f"Tabla escrita: {destino}  ({[ALIAS[c] for c in codigos]})")
    return base


display(escribir_base(SELECCIONADAS, TBL_SELECCIONADAS))
