# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Estimación Directa de Tasa de Desempleo por Dominio (ciudad o ciudad A.M.) con Bootstrap
# MAGIC
# MAGIC Este notebook implementa **estimación directa de áreas pequeñas** usando el **estimador de Hájek** con inferencia basada en un **bootstrap por viviendas dentro de cada dominio**.
# MAGIC
# MAGIC ## Dominio de estimación
# MAGIC
# MAGIC El campo `AREA` de la GEIH identifica la **ciudad con su área metropolitana**, no el municipio
# MAGIC (Metodología GEIH v9, PDF 9): los hogares de Yumbo llegan con el mismo `AREA` que los de Cali.
# MAGIC Por eso cada dominio es una ciudad (`TIPO_DOMINIO = CIUDAD`) o una ciudad con su A.M.
# MAGIC (`CIUDAD_AM`: Medellín, Cali, Barranquilla, Bucaramanga, Manizales, Pereira y Cúcuta), con la
# MAGIC membresía de `tesis.dim.dim_dominio_geih`. `CODIGO_DOMINIO` es el código DIVIPOLA de la capital.
# MAGIC Las tasas coinciden con las que publica el DANE para «Cali A.M.», «Popayán», etc.; la última
# MAGIC celda lo verifica contra `tesis.geih_bronce.datos_municipales`.
# MAGIC
# MAGIC ## Propósito
# MAGIC
# MAGIC Calcular estimaciones de **tasa de desempleo por dominio** a partir de microdatos de la GEIH, incluyendo:
# MAGIC * **Estimación puntual**: Tasa de desempleo (porcentaje)
# MAGIC * **Medidas de precisión**: Error estándar, intervalos de confianza 95%, coeficiente de variación
# MAGIC * **Inferencia estadística**: bootstrap por viviendas dentro del dominio (2000 réplicas, semilla 42)
# MAGIC   y, como control, linealización de Taylor con las mismas unidades
# MAGIC
# MAGIC ## ¿Qué es Estimación Directa?
# MAGIC
# MAGIC La **estimación directa** usa **solo los datos de la muestra del dominio de interés** (en este caso, la ciudad o ciudad A.M.) para calcular la estimación, sin "pedir prestada" información de otros dominios.
# MAGIC
# MAGIC ### Ventajas:
# MAGIC ✅ **Simple y transparente**: Usa solo datos locales
# MAGIC ✅ **Sin supuestos de modelo**: No asume relaciones con covariables
# MAGIC ✅ **Fácil de interpretar**: Es el estimador "natural"
# MAGIC
# MAGIC ### Desventajas:
# MAGIC ❌ **Alta variabilidad en áreas pequeñas**: Muestras chicas → errores grandes
# MAGIC ❌ **Intervalos de confianza amplios**: Poca precisión para municipios pequeños
# MAGIC ❌ **Coeficientes de variación altos**: CV ≥ 20% son comunes en municipios pequeños
# MAGIC ❌ **Imposible estimar dominios con muestra cero**: Sin observaciones → sin estimación
# MAGIC
# MAGIC ### ¿Cuándo usar estimación directa?
# MAGIC
# MAGIC **Usar cuando**:
# MAGIC * El dominio tiene **muestra suficiente** (n ≥ 30 típicamente)
# MAGIC * El **CV es aceptable** (< 5% confiable, < 20% aceptable)
# MAGIC * Se requiere **transparencia metodológica**
# MAGIC * Es el **baseline** para comparar con métodos SAE
# MAGIC
# MAGIC **NO usar cuando**:
# MAGIC * El dominio tiene muestra muy pequeña (n < 10)
# MAGIC * El CV es muy alto (≥ 20%)
# MAGIC * Se requieren estimaciones para **todos** los municipios (incluso sin muestra)
# MAGIC
# MAGIC ## Periodicidad: año calendario (trimestre móvil opcional)
# MAGIC
# MAGIC Cada dominio es una ciudad o ciudad A.M. en una **ventana de meses consecutivos** que cierra en
# MAGIC `anio_estimacion/mes_estimacion`. Por defecto es el **año calendario** (12 meses con cierre en
# MAGIC diciembre: Ene-Dic 2018); con `n_meses_ventana = 3` es el trimestre móvil (Oct-Dic 2018).
# MAGIC Las observaciones de todos los meses se agrupan en un solo dominio, con `FEX_C18` sin reescalar
# MAGIC (el Hájek es una razón, así que dividir el factor mensual entre el número de meses no cambia la
# MAGIC tasa). `PER` y `MES` de la salida son el año y el mes de cierre; `PERIODO` («Ene-Dic 2018») y
# MAGIC `N_MESES_VENTANA` identifican la ventana y viajan con los datos hasta el modelo.
# MAGIC
# MAGIC **Por qué el año (G7-B2).** La sensibilidad `analisis/sensibilidad_ventana_temporal.py` compara
# MAGIC diciembre, Oct-Dic y el año 2018: con el año los 23 dominios son confiables (CV < 5 %) y el error
# MAGIC estándar es cerca de la mitad del trimestral; la GEIH publica resultados anuales por ciudad con su
# MAGIC A.M. (Metodología GEIH v9, PDF 9) y los segmentos no se repiten en tres años (PDF 12), así que juntar
# MAGIC meses suma muestra nueva; y los indicadores de TerriData son anuales con corte a diciembre, de modo
# MAGIC que tasa y covariables describen el mismo período. La ventana anual exige cierre en diciembre.
# MAGIC
# MAGIC ## Estimador de Hájek
# MAGIC
# MAGIC El **estimador de Hájek** es un estimador de **razón** que ajusta por los pesos muestrales:
# MAGIC
# MAGIC ```
# MAGIC θ̂ = Σ(w_i × y_i) / Σ(w_i)
# MAGIC ```
# MAGIC
# MAGIC Donde:
# MAGIC * `w_i`: Peso de expansión `FEX_C18` (factor 2018) de la observación i; solo personas de 15 años o más
# MAGIC * `y_i`: Variable binaria (1 = desocupado, 0 = ocupado)
# MAGIC
# MAGIC Para muestras grandes es aproximadamente insesgado, consistente y asintóticamente normal.
# MAGIC Para muestras pequeñas (áreas pequeñas) puede tener alta variabilidad.
# MAGIC
# MAGIC ## Bootstrap por viviendas dentro del dominio (G7-B3)
# MAGIC
# MAGIC **Procedimiento** (`shared/bootstrap.py`):
# MAGIC 1. Calcular θ̂ en la muestra original
# MAGIC 2. Crear B réplicas: en cada dominio, remuestrear **con reemplazo** tantas viviendas
# MAGIC    (`ID_VIVIENDA`) como tiene la muestra del dominio, con todas sus personas, y calcular θ̂_b
# MAGIC 3. SE = desv. estándar de {θ̂_1, ..., θ̂_B}
# MAGIC 4. IC 95% = [percentil 2.5%, percentil 97.5%]
# MAGIC
# MAGIC **Por qué así.** La GEIH encuesta conglomerados completos (todas las viviendas, hogares y
# MAGIC personas del segmento; metodología v9, PDF 11), así que las personas de una vivienda no son
# MAGIC independientes y se remuestrean juntas (Morales et al., 2021, p. 61). Las A.M. y capitales son
# MAGIC de inclusión forzosa con estimaciones separadas (PDF 11): cada dominio actúa como estrato y su
# MAGIC tamaño de muestra queda fijo en cada réplica.
# MAGIC
# MAGIC **Control.** `SE_TAYLOR_PCT` es la varianza por linealización de Taylor de la razón con las
# MAGIC mismas unidades (conglomerados últimos, PDF 15). Con miles de viviendas por dominio ambas
# MAGIC deben coincidir.
# MAGIC
# MAGIC **Limitación.** Los microdatos no traen el estrato interno ni el segmento (~10 viviendas
# MAGIC contiguas) de la GEIH, que son las unidades de la varianza oficial (PDF 14-15). La varianza es
# MAGIC una aproximación: no se sabe si la del diseño es mayor o menor, ni por cuánto. El notebook
# MAGIC `modelo/sensibilidad_varianza.py` muestra cómo responde el modelo si se equivoca.
# MAGIC
# MAGIC **Número de réplicas**: B = 2000 (ver `shared/config.py`).
# MAGIC Literatura recomienda B ≥ 500 para SE y B ≥ 1000 para IC.
# MAGIC
# MAGIC ## Parámetros Configurables
# MAGIC
# MAGIC Ver `shared/config.py`:
# MAGIC * `BOOTSTRAP_REPLICAS`: Número de réplicas (default 2000)
# MAGIC * `BOOTSTRAP_SEED`: Semilla aleatoria (default 42)
# MAGIC * `PER_ESTIMACION`, `MES_ESTIMACION`: Año y mes de **cierre** de la ventana (defaults 2018 / 12).
# MAGIC   Se cambian con los parámetros `anio_estimacion` y `mes_estimacion` del job (`resolver_periodo`)
# MAGIC * `N_MESES_VENTANA`: meses de la ventana, 12 (año, por defecto) o 3 (trimestre móvil). Se cambia con
# MAGIC   el parámetro `n_meses_ventana` (`resolver_ventana`); el año exige `mes_estimacion = 12`. Los
# MAGIC   trimestres pueden cruzar el año (2019 / 1 → Nov 2018 - Ene 2019), igual que la hoja «areas trim
# MAGIC   movil» del anexo DANE (`meses_ventana`)
# MAGIC * `GRUPO_COLS`: Columnas que definen los dominios
# MAGIC
# MAGIC ## Interpretación del CV
# MAGIC
# MAGIC ```
# MAGIC CV = (SE / Estimación) × 100
# MAGIC ```
# MAGIC
# MAGIC * **CV < 5%**: Estimación CONFIABLE ✅
# MAGIC * **5% ≤ CV < 20%**: Estimación ACEPTABLE ⚠️
# MAGIC * **CV ≥ 20%**: Estimación NO CONFIABLE ❌
# MAGIC
# MAGIC Sustento (G7-B7, detalle en `shared/config.py`): 5 % es la precisión de diseño de la GEIH para
# MAGIC la tasa de desempleo (DANE, Metodología GEIH v9, PDF 12) y 20 % el límite de «no publicable»
# MAGIC de varios institutos de estadística (Molina, 2019, CEPAL, PDF 16-17).
# MAGIC
# MAGIC ## Flujo de Datos
# MAGIC
# MAGIC ```
# MAGIC tesis.geih_oro.mercado_laboral
# MAGIC   → filter(PEA == 1, EDAD >= 15, meses de la ventana que cierra en anio_estimacion/mes_estimacion)
# MAGIC   → INNER JOIN tesis.dim.dim_dominio_geih (fila de la capital) → CODIGO_DOMINIO, NOMBRE_DOMINIO, TIPO_DOMINIO
# MAGIC   → FEX := FEX_C18; PER, MES := año y mes de cierre de la ventana
# MAGIC   → EstimacionDirecta.estimar()   [bootstrap por viviendas, 2000 réplicas + Taylor]
# MAGIC   → + PERIODO, N_MESES_VENTANA, N_PEA, N_DESOCUPADOS, N_VIVIENDAS (muestra), PEA_EXPANDIDA
# MAGIC     (Σ FEX_C18 de la PEA / meses) y N_MUNICIPIOS del dominio
# MAGIC   → validación contra el DANE (año: TD reconstruida con los 4 trimestres; trimestre: publicada)
# MAGIC   → tesis.preprocesamiento.tasa_desempleo_municipal   (una fila por dominio)
# MAGIC ```
# MAGIC
# MAGIC `PEA_EXPANDIDA` es la PEA promedio mensual de la ventana que representa la muestra del dominio. Es el
# MAGIC peso del benchmarking de nivel 1 en `modelo/fay_herriot.py`: con él, el promedio ponderado de
# MAGIC las tasas directas de los dominios reproduce exactamente la tasa directa del conjunto (propiedad
# MAGIC de benchmarking de los estimadores directos, Molina 2019, CEPAL, PDF 26).
# MAGIC
# MAGIC ## Referencias
# MAGIC
# MAGIC * Hájek, J. (1971). "Comment on 'An essay on the logical foundations of survey sampling'".
# MAGIC * Efron, B. & Tibshirani, R. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
# MAGIC * Morales, D. et al. (2021). *A Course on Small Area Estimation and Mixed Models*. Springer (p. 61).
# MAGIC * DANE (2016). Metodología General GEIH v9 (PDF 11-15: diseño y estimación de la varianza).
# MAGIC * DANE (2020). "Guía de calidad de estimaciones para encuestas de hogares".

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
from preprocesamiento.shared.estimador_sae import EstimacionDirecta
from preprocesamiento.shared.ventana import (
    TOLERANCIA_PP,
    etiqueta_ventana,
    td_dane_ventana,
)

# Período a estimar: widgets anio_estimacion / mes_estimacion / n_meses_ventana (parámetros del job).
PER_ESTIMACION, MES_ESTIMACION = resolver_periodo(dbutils)
N_MESES = resolver_ventana(dbutils, MES_ESTIMACION)
PERIODO = etiqueta_ventana(PER_ESTIMACION, MES_ESTIMACION, N_MESES)
print(
    f"Período a estimar: {PERIODO} ({N_MESES} meses con cierre en "
    f"{PER_ESTIMACION}-{MES_ESTIMACION:02d})"
)

# COMMAND ----------

# DBTITLE 1,Cargar y filtrar datos GEIH
# Peso: FEX_C18 (factor de expansión 2018). EstimacionDirecta lee la columna "FEX", por eso se
# sobrescribe con FEX_C18. Población: personas de 15 años o más (EDAD >= EDAD_MINIMA) en la PEA.
EDAD_MINIMA = 15

# Ventana que cierra en (PER_ESTIMACION, MES_ESTIMACION): se agrupan las observaciones de sus meses y
# PER/MES se reescriben con el año/mes de cierre, de modo que GRUPO_COLS arma un dominio por ciudad
# (o ciudad A.M.) y ventana (y el esquema de salida no cambia).
MESES = meses_ventana(PER_ESTIMACION, MES_ESTIMACION, N_MESES)
print("Meses de la ventana:", ", ".join(f"{a}-{m:02d}" for a, m in MESES))

cond_ventana = None
for anio, mes in MESES:
    cond_mes = (F.col("PER") == anio) & (F.col("MES") == mes)
    cond_ventana = cond_mes if cond_ventana is None else (cond_ventana | cond_mes)

# Dominio de cada registro: geih_oro trae en CODIGO_MUNICIPIO el código de la capital del AREA
# (ciudad con su A.M.); la fila de la capital en dim_dominio_geih da el dominio. El INNER JOIN
# descarta los registros sin AREA (resto de cabeceras y zona rural), que no forman dominio.
df_dominios_capital = (
    spark.table(TBL_DIM_DOMINIO)
    .filter(F.col("ES_CAPITAL"))
    .select("CODIGO_MUNICIPIO", "CODIGO_DOMINIO", "NOMBRE_DOMINIO", "TIPO_DOMINIO")
)
n_municipios_dominio = (
    spark.table(TBL_DIM_DOMINIO)
    .groupBy("CODIGO_DOMINIO")
    .agg(F.count("*").alias("N_MUNICIPIOS"))
)

df_desempleo = (
    spark.table(TBL_MERCADO_LABORAL)
    .filter((F.col("PEA") == 1) & (F.col("EDAD") >= EDAD_MINIMA) & cond_ventana)
    .join(df_dominios_capital, on="CODIGO_MUNICIPIO", how="inner")
    .withColumn("FEX", F.col("FEX_C18"))
)

print("Observaciones PEA por mes de la ventana:")
df_desempleo.groupBy("PER", "MES").count().orderBy("PER", "MES").show(N_MESES)
meses_presentes = {
    (r["PER"], r["MES"]) for r in df_desempleo.select("PER", "MES").distinct().collect()
}
# R-27: cada dominio debe tener todos los meses de la ventana; si falta uno, la tasa no es la
# del período que dice la etiqueta (antes solo se avisaba si faltaba en todos los dominios)
meses_por_dominio = (
    df_desempleo.groupBy("CODIGO_DOMINIO", "NOMBRE_DOMINIO")
    .agg(F.countDistinct("PER", "MES").alias("N_MESES_CON_DATOS"))
    .toPandas()
)
incompletos = meses_por_dominio[meses_por_dominio["N_MESES_CON_DATOS"] < len(MESES)]
faltantes = set(MESES) - meses_presentes
if faltantes or not incompletos.empty:
    raise ValueError(
        f"Ventana {PERIODO} incompleta. Meses sin datos en GEIH: {sorted(faltantes)}. "
        f"Dominios sin todos los meses:\n{incompletos.to_string(index=False)}"
    )
print(
    f"✔ Los {len(meses_por_dominio)} dominios tienen los {len(MESES)} meses de la ventana"
)

# Por dominio: PEA promedio mensual de la ventana que representa la muestra (peso del benchmarking
# de nivel 1 en el modelo; R-27: se divide entre los meses con datos de cada dominio, no los
# globales) y conteos muestrales de la PEA y de los desocupados (G7-B2: tamaño de muestra que
# respalda cada tasa).
df_pea_expandida = (
    df_desempleo.groupBy("CODIGO_DOMINIO")
    .agg(
        F.count("*").alias("N_PEA"),
        F.sum("DESOCUPADO").cast("long").alias("N_DESOCUPADOS"),
        (F.sum("FEX") / F.countDistinct("PER", "MES")).alias("PEA_EXPANDIDA"),
    )
    .join(n_municipios_dominio, on="CODIGO_DOMINIO", how="left")
    .toPandas()
)

df_desempleo = df_desempleo.withColumn("PER", F.lit(PER_ESTIMACION)).withColumn(
    "MES", F.lit(MES_ESTIMACION)
)

print(f"Observaciones PEA: {df_desempleo.count():,}")
print(
    f"Dominios con muestra: {df_desempleo.select('CODIGO_DOMINIO').distinct().count()}"
)

# COMMAND ----------

# DBTITLE 1,Ejecutar estimación directa con bootstrap
estimador = EstimacionDirecta(
    spark, num_replicas=BOOTSTRAP_REPLICAS, seed=BOOTSTRAP_SEED
)

resultado = estimador.estimar(
    dataframe=df_desempleo,
    grupo_cols=GRUPO_COLS,
    agregacion_anual=False,
)

# Etiqueta y longitud de la ventana junto a PER/MES (que ya son el año y mes de cierre): viajan en
# los datos para que la auditoría, la sensibilidad y el modelo sepan contra qué cifra del DANE
# validar. Se agregan la PEA expandida, los conteos muestrales y el número de municipios de cada
# dominio. Se asigna a estimador._resultado para que `exportar` lo incluya en la tabla destino.
resultado.insert(2, "PERIODO", PERIODO)
resultado.insert(3, "N_MESES_VENTANA", N_MESES)
resultado = resultado.merge(
    df_pea_expandida, on="CODIGO_DOMINIO", how="left", validate="one_to_one"
)
estimador._resultado = resultado

# COMMAND ----------

# DBTITLE 1,Resumen de resultados
print(f"Dominios estimados: {len(resultado)}")
print(f"  ciudades A.M.: {(resultado['TIPO_DOMINIO'] == 'CIUDAD_AM').sum()}")
print(
    f"Período: {PERIODO} (cierre {resultado['PER'].iloc[0]}-{resultado['MES'].iloc[0]:02d})"
)
print(
    f"Muestra: PEA mínima {resultado['N_PEA'].min():,}, desocupados mínimo "
    f"{resultado['N_DESOCUPADOS'].min():,}\n"
)

confiables = (resultado["CV_PORCENTAJE"] < CV_CONFIABLE).sum()
aceptables = (
    (resultado["CV_PORCENTAJE"] >= CV_CONFIABLE)
    & (resultado["CV_PORCENTAJE"] < CV_ACEPTABLE)
).sum()
no_conf = (resultado["CV_PORCENTAJE"] >= CV_ACEPTABLE).sum()

print(f"Calidad de estimaciones (CV):")
print(f"  Confiables  (CV < {CV_CONFIABLE}%): {confiables}")
print(f"  Aceptables  ({CV_CONFIABLE}% ≤ CV < {CV_ACEPTABLE}%): {aceptables}")
print(f"  No confiables (CV ≥ {CV_ACEPTABLE}%): {no_conf}")

display(resultado)

# COMMAND ----------

# DBTITLE 1,Control: bootstrap por viviendas vs. linealización de Taylor
# Las dos estiman la varianza de la misma razón con las mismas unidades (vivienda dentro del
# dominio): con miles de viviendas por dominio deben coincidir salvo el error Monte Carlo del
# bootstrap (≈ √(2/B) ≈ 3 % en la varianza con B = 2000). Solo informa.
razon_se = resultado["SE_BOOTSTRAP_PCT"] / resultado["SE_TAYLOR_PCT"]
print(
    f"SE bootstrap / SE Taylor: mediana {razon_se.median():.3f}, "
    f"mín {razon_se.min():.3f}, máx {razon_se.max():.3f}"
)
print(
    f"Viviendas por dominio: mín {resultado['N_VIVIENDAS'].min():,}, "
    f"máx {resultado['N_VIVIENDAS'].max():,}"
)

# COMMAND ----------

# DBTITLE 1,Validación contra las cifras oficiales del DANE (informativa)
# Compara cada dominio y el agregado de los 23 con el anexo DANE «Mercado laboral según
# proyecciones CNPV 2018» (tesis.geih_bronce.datos_municipales, cargado por datos_publicados.py).
# Trimestre: la tasa publicada del trimestre móvil. Año: el anexo no publica la TD anual por
# ciudad, así que se reconstruye como Σ desempleados / Σ PEA de los 4 trimestres que no se pisan
# (shared/ventana.py; la fórmula reproduce los totales anuales de 13 y 10 ciudades). Solo imprime
# PASS/FAIL: el anexo cubre 2016-2021 y fuera de ese rango no hay contra qué comparar.
#
# El agregado Σ PEA_d·TD_d / Σ PEA_d es exactamente el Hájek del conjunto de los dominios (los
# estimadores directos cumplen la propiedad de benchmarking; Molina 2019, PDF 26). Es el valor al
# que el modelo ajusta los EBLUP en el benchmarking de nivel 1.
df_publicados = td_dane_ventana(
    spark.table(TBL_DATOS_MUNICIPALES).toPandas(),
    PER_ESTIMACION,
    MES_ESTIMACION,
    N_MESES,
)

if df_publicados.empty:
    print(f"Sin cifras oficiales para {PERIODO}: no se valida.")
else:
    comparacion = resultado[["NOMBRE_DOMINIO", "TASA_DESEMPLEO_PCT"]].merge(
        df_publicados.rename(columns={"CIUDAD": "NOMBRE_DOMINIO"}),
        on="NOMBRE_DOMINIO",
        how="left",
    )
    comparacion["DIF_PP"] = comparacion["TASA_DESEMPLEO_PCT"] - comparacion["TD_DANE"]
    ok = comparacion["DIF_PP"].abs() <= TOLERANCIA_PP
    print(
        f"[{'PASS' if ok.all() else 'FAIL'}] {int(ok.sum())} de {len(comparacion)} dominios "
        f"coinciden con el DANE en {PERIODO} (tolerancia {TOLERANCIA_PP} pp)"
    )
    if not ok.all():
        display(comparacion[~ok])

    td_agregada = (
        resultado["PEA_EXPANDIDA"] * resultado["TASA_DESEMPLEO_PCT"]
    ).sum() / resultado["PEA_EXPANDIDA"].sum()
    total_dane = df_publicados.loc[
        df_publicados["CIUDAD"] == NOMBRE_TOTAL_23, "TD_DANE"
    ]
    if total_dane.empty:
        print(f"Sin «{NOMBRE_TOTAL_23}» para {PERIODO}: no se valida el agregado.")
    else:
        dif = td_agregada - float(total_dane.iloc[0])
        print(
            f"[{'PASS' if abs(dif) <= TOLERANCIA_PP else 'FAIL'}] agregado de los dominios "
            f"{td_agregada:.4f} vs «{NOMBRE_TOTAL_23}» {float(total_dane.iloc[0]):.4f} "
            f"(dif. {dif:+.4f} pp)"
        )

# COMMAND ----------

# DBTITLE 1,Exportar a Unity Catalog
estimador.exportar(
    tabla_destino=TBL_ESTIMACION_DIRECTA,
    tabla_origen=TBL_MERCADO_LABORAL,
)
