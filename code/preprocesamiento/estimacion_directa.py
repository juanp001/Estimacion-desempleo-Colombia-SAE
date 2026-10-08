# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Estimación Directa de Tasa de Desempleo por Dominio (ciudad o ciudad A.M.) con Bootstrap
# MAGIC
# MAGIC Este notebook implementa **estimación directa de áreas pequeñas** usando el **estimador de Hájek** con inferencia basada en **bootstrap simple**.
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
# MAGIC * **Inferencia estadística**: Basada en bootstrap simple (2000 réplicas, semilla 42)
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
# MAGIC ## Periodicidad: trimestre móvil
# MAGIC
# MAGIC Cada dominio es una ciudad o ciudad A.M. en un **trimestre móvil** (tres meses consecutivos, p. ej. Oct-Dic).
# MAGIC Las observaciones de los tres meses se agrupan en un solo dominio, con `FEX_C18` sin reescalar
# MAGIC (el Hájek es una razón, así que dividir el factor mensual entre 3 no cambia la tasa). `PER` y `MES`
# MAGIC de la salida son el año y el mes de cierre del trimestre.
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
# MAGIC ## Bootstrap Simple (Naive Bootstrap)
# MAGIC
# MAGIC **Procedimiento**:
# MAGIC 1. Calcular θ̂ en la muestra original
# MAGIC 2. Crear B réplicas: remuestrear n obs. **con reemplazo** y calcular θ̂_b
# MAGIC 3. SE = desv. estándar de {θ̂_1, ..., θ̂_B}
# MAGIC 4. IC 95% = [percentil 2.5%, percentil 97.5%]
# MAGIC
# MAGIC **Número de réplicas**: B = 2000 (ver `shared/config.py`).
# MAGIC Literatura recomienda B ≥ 500 para SE y B ≥ 1000 para IC.
# MAGIC
# MAGIC ## Parámetros Configurables
# MAGIC
# MAGIC Ver `shared/config.py`:
# MAGIC * `BOOTSTRAP_REPLICAS`: Número de réplicas (default 2000)
# MAGIC * `BOOTSTRAP_SEED`: Semilla aleatoria (default 42)
# MAGIC * `PER_ESTIMACION`, `MES_ESTIMACION`: Año y mes de **cierre** del trimestre móvil a estimar (defaults
# MAGIC   2018 / 12 → Oct-Dic 2018). Se cambian con los parámetros `anio_estimacion` y `mes_estimacion` del
# MAGIC   job (`resolver_periodo`). Los trimestres pueden cruzar el año (2019 / 1 → Nov 2018 - Ene 2019),
# MAGIC   igual que la hoja «areas trim movil» del anexo DANE (`meses_trimestre_movil`)
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
# MAGIC ## Flujo de Datos
# MAGIC
# MAGIC ```
# MAGIC tesis.geih_oro.mercado_laboral
# MAGIC   → filter(PEA == 1, EDAD >= 15, meses del trimestre móvil que cierra en anio_estimacion/mes_estimacion)
# MAGIC   → INNER JOIN tesis.dim.dim_dominio_geih (fila de la capital) → CODIGO_DOMINIO, NOMBRE_DOMINIO, TIPO_DOMINIO
# MAGIC   → FEX := FEX_C18; PER, MES := año y mes de cierre del trimestre
# MAGIC   → EstimacionDirecta.estimar()   [bootstrap 2000 réplicas]
# MAGIC   → + PEA_EXPANDIDA (Σ FEX_C18 de la PEA / 3) y N_MUNICIPIOS del dominio
# MAGIC   → tesis.preprocesamiento.tasa_desempleo_municipal   (una fila por dominio)
# MAGIC ```
# MAGIC
# MAGIC `PEA_EXPANDIDA` es la PEA promedio del trimestre que representa la muestra del dominio. Es el
# MAGIC peso del benchmarking de nivel 1 en `modelo/fay_herriot.py`: con él, el promedio ponderado de
# MAGIC las tasas directas de los dominios reproduce exactamente la tasa directa del conjunto (propiedad
# MAGIC de benchmarking de los estimadores directos, Molina 2019, CEPAL, PDF 26).
# MAGIC
# MAGIC ## Referencias
# MAGIC
# MAGIC * Hájek, J. (1971). "Comment on 'An essay on the logical foundations of survey sampling'".
# MAGIC * Efron, B. & Tibshirani, R. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
# MAGIC * DANE (2020). "Guía de calidad de estimaciones para encuestas de hogares".

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
%pip install tqdm
from pyspark.sql import functions as F
from shared.config import *
from shared.estimador_sae import EstimacionDirecta

# Período a estimar: widgets anio_estimacion / mes_estimacion (parámetros del job).
PER_ESTIMACION, MES_ESTIMACION = resolver_periodo(dbutils)
print(f"Período a estimar: {PER_ESTIMACION}-{MES_ESTIMACION:02d}")

# COMMAND ----------

# DBTITLE 1,Cargar y filtrar datos GEIH
# Peso: FEX_C18 (factor de expansión 2018). EstimacionDirecta lee la columna "FEX", por eso se
# sobrescribe con FEX_C18. Población: personas de 15 años o más (EDAD >= EDAD_MINIMA) en la PEA.
EDAD_MINIMA = 15

# Trimestre móvil que cierra en (PER_ESTIMACION, MES_ESTIMACION): se agrupan las observaciones de
# sus tres meses y PER/MES se reescriben con el año/mes de cierre, de modo que GRUPO_COLS arma un
# dominio por municipio y trimestre (y el esquema de salida no cambia).
MESES_TRIM = meses_trimestre_movil(PER_ESTIMACION, MES_ESTIMACION)
print("Trimestre móvil:", ", ".join(f"{a}-{m:02d}" for a, m in MESES_TRIM))

cond_trimestre = None
for anio, mes in MESES_TRIM:
    cond_mes = (F.col("PER") == anio) & (F.col("MES") == mes)
    cond_trimestre = cond_mes if cond_trimestre is None else (cond_trimestre | cond_mes)

# Dominio de cada registro: geih_oro trae en CODIGO_MUNICIPIO el código de la capital del AREA
# (ciudad con su A.M.); la fila de la capital en dim_dominio_geih da el dominio. El INNER JOIN
# descarta los registros sin AREA (resto de cabeceras y zona rural), que no forman dominio.
df_dominios_capital = (
    spark.table(TBL_DIM_DOMINIO)
    .filter(F.col("ES_CAPITAL"))
    .select("CODIGO_MUNICIPIO", "CODIGO_DOMINIO", "NOMBRE_DOMINIO", "TIPO_DOMINIO")
)
n_municipios_dominio = (
    spark.table(TBL_DIM_DOMINIO).groupBy("CODIGO_DOMINIO").agg(F.count("*").alias("N_MUNICIPIOS"))
)

df_desempleo = (
    spark.table(TBL_MERCADO_LABORAL)
    .filter(
        (F.col("PEA") == 1) &
        (F.col("EDAD") >= EDAD_MINIMA) &
        cond_trimestre
    )
    .join(df_dominios_capital, on="CODIGO_MUNICIPIO", how="inner")
    .withColumn("FEX", F.col("FEX_C18"))
)

print("Observaciones PEA por mes del trimestre:")
df_desempleo.groupBy("PER", "MES").count().orderBy("PER", "MES").show()
meses_presentes = {
    (r["PER"], r["MES"]) for r in df_desempleo.select("PER", "MES").distinct().collect()
}
faltantes = set(MESES_TRIM) - meses_presentes
if faltantes:
    print(f"⚠ Sin datos en GEIH para: {sorted(faltantes)}")

# PEA promedio del trimestre que representa la muestra de cada dominio (peso del benchmarking de
# nivel 1 en el modelo). Se divide entre los meses con datos para que sea un promedio mensual.
df_pea_expandida = (
    df_desempleo.groupBy("CODIGO_DOMINIO")
    .agg((F.sum("FEX") / len(meses_presentes)).alias("PEA_EXPANDIDA"))
    .join(n_municipios_dominio, on="CODIGO_DOMINIO", how="left")
    .toPandas()
)

df_desempleo = df_desempleo.withColumn("PER", F.lit(PER_ESTIMACION)).withColumn(
    "MES", F.lit(MES_ESTIMACION)
)

print(f"Observaciones PEA: {df_desempleo.count():,}")
print(f"Dominios con muestra: {df_desempleo.select('CODIGO_DOMINIO').distinct().count()}")

# COMMAND ----------

# DBTITLE 1,Ejecutar estimación directa con bootstrap
estimador = EstimacionDirecta(spark, num_replicas=BOOTSTRAP_REPLICAS, seed=BOOTSTRAP_SEED)

resultado = estimador.estimar(
    dataframe=df_desempleo,
    grupo_cols=GRUPO_COLS,
    agregacion_anual=False,
)

# Etiqueta del trimestre junto a PER/MES (que ya son el año y mes de cierre), y la PEA expandida y el
# número de municipios de cada dominio. Se asigna a estimador._resultado para que `exportar` lo
# incluya en la tabla destino.
resultado.insert(2, "TRIMESTRE_MOVIL", etiqueta_trimestre_movil(PER_ESTIMACION, MES_ESTIMACION))
resultado = resultado.merge(
    df_pea_expandida, on="CODIGO_DOMINIO", how="left", validate="one_to_one"
)
estimador._resultado = resultado

# COMMAND ----------

# DBTITLE 1,Resumen de resultados
print(f"Dominios estimados: {len(resultado)}")
print(f"  ciudades A.M.: {(resultado['TIPO_DOMINIO'] == 'CIUDAD_AM').sum()}")
print(f"Período: {resultado['PER'].iloc[0]}-{resultado['MES'].iloc[0]:02d}\n")

confiables = (resultado["CV_PORCENTAJE"] < CV_CONFIABLE).sum()
aceptables = ((resultado["CV_PORCENTAJE"] >= CV_CONFIABLE) & (resultado["CV_PORCENTAJE"] < CV_ACEPTABLE)).sum()
no_conf    = (resultado["CV_PORCENTAJE"] >= CV_ACEPTABLE).sum()

print(f"Calidad de estimaciones (CV):")
print(f"  Confiables  (CV < {CV_CONFIABLE}%): {confiables}")
print(f"  Aceptables  ({CV_CONFIABLE}% ≤ CV < {CV_ACEPTABLE}%): {aceptables}")
print(f"  No confiables (CV ≥ {CV_ACEPTABLE}%): {no_conf}")

display(resultado)

# COMMAND ----------

# DBTITLE 1,Validación contra las cifras publicadas por el DANE (informativa)
# Compara cada dominio y el agregado de los 23 con el anexo DANE «Mercado laboral según
# proyecciones CNPV 2018» (tesis.geih_bronce.datos_municipales, cargado por datos_publicados.py).
# Solo imprime PASS/FAIL: el anexo cubre 2016-2021 y fuera de ese rango no hay contra qué comparar.
#
# El agregado Σ PEA_d·TD_d / Σ PEA_d es exactamente el Hájek del conjunto de los dominios (los
# estimadores directos cumplen la propiedad de benchmarking; Molina 2019, PDF 26). Es el valor al
# que el modelo ajusta los EBLUP en el benchmarking de nivel 1.
TOLERANCIA_PP = 0.01

df_publicados = (
    spark.table(TBL_DATOS_MUNICIPALES)
    .filter((F.col("ANIO") == PER_ESTIMACION) & (F.col("MES") == MES_ESTIMACION))
    .select("CIUDAD", "TASA_DESEMPLEO")
    .toPandas()
)

if df_publicados.empty:
    print(f"Sin cifras publicadas para {PER_ESTIMACION}-{MES_ESTIMACION:02d}: no se valida.")
else:
    comparacion = resultado[["NOMBRE_DOMINIO", "TASA_DESEMPLEO_PCT"]].merge(
        df_publicados.rename(columns={"CIUDAD": "NOMBRE_DOMINIO", "TASA_DESEMPLEO": "TD_DANE"}),
        on="NOMBRE_DOMINIO",
        how="left",
    )
    comparacion["DIF_PP"] = comparacion["TASA_DESEMPLEO_PCT"] - comparacion["TD_DANE"]
    ok = comparacion["DIF_PP"].abs() <= TOLERANCIA_PP
    print(
        f"[{'PASS' if ok.all() else 'FAIL'}] {int(ok.sum())} de {len(comparacion)} dominios "
        f"coinciden con el DANE (tolerancia {TOLERANCIA_PP} pp)"
    )
    if not ok.all():
        display(comparacion[~ok])

    td_agregada = (resultado["PEA_EXPANDIDA"] * resultado["TASA_DESEMPLEO_PCT"]).sum() / resultado[
        "PEA_EXPANDIDA"
    ].sum()
    total_dane = df_publicados.loc[df_publicados["CIUDAD"] == NOMBRE_TOTAL_23, "TASA_DESEMPLEO"]
    if total_dane.empty:
        print(f"Sin «{NOMBRE_TOTAL_23}» en {TBL_DATOS_MUNICIPALES}: no se valida el agregado.")
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
