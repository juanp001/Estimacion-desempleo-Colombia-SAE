# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Sensibilidad de la estimación directa a la ventana temporal (G7-B2)
# MAGIC
# MAGIC El comentario G7-B2 pide justificar con evidencia el período de la tasa directa. Este notebook
# MAGIC calcula la tasa de desempleo de los 23 dominios (ciudades y ciudades A.M.) con tres ventanas que
# MAGIC cierran en el mismo mes (por defecto diciembre de 2018) y las compara. **No cambia el
# MAGIC pipeline**: la tasa que usa el modelo sigue saliendo de `preprocesamiento/estimacion_directa.py`.
# MAGIC
# MAGIC | Ventana | Meses | Período (cierre 2018-12) | Validación contra el DANE |
# MAGIC |---|---|---|---|
# MAGIC | `MES` | 1 | Dic 2018 | No hay cifra mensual por ciudad |
# MAGIC | `TRIMESTRE` | 3 | Oct-Dic 2018 (la ventana actual) | Tasa publicada por ciudad (`datos_municipales`) |
# MAGIC | `ANIO` | 12 | Ene-Dic 2018 | Reconstruida con los 4 trimestres (ver abajo) |
# MAGIC
# MAGIC Por dominio y ventana se reporta la muestra (personas de 15+, PEA y desocupados muestrales), la
# MAGIC tasa (Hájek con `FEX_C18`), su error estándar bootstrap, el IC 95 %, el CV y la diferencia con
# MAGIC el DANE.
# MAGIC
# MAGIC ## Criterios para elegir la ventana
# MAGIC
# MAGIC 1. **Representatividad por diseño.** La GEIH publica resultados mensuales solo para agregados
# MAGIC    (13 ciudades, 11 intermedias, total nacional); por ciudad capital con su A.M. la desagregación
# MAGIC    mínima es trimestral, y también hay semestral y anual (Metodología GEIH v9, PDF 9). Diciembre
# MAGIC    solo queda como referencia de precisión.
# MAGIC 2. **Precisión.** CV, error estándar y tamaño de muestra. La nota SAE del DANE exige a las
# MAGIC    estimaciones directas que entran al Fay-Herriot un tamaño de muestra efectivo ≥ 40 (DANE, nota
# MAGIC    SAE 2024, PDF 22), y el modelo supone conocida la varianza de muestreo (Morales et al., p. 425):
# MAGIC    cuanta más muestra, más creíble es ese supuesto.
# MAGIC 3. **Se pueden juntar meses.** En las capitales un segmento no se repite en por lo menos tres
# MAGIC    años (GEIH v9, PDF 12): sumar 3 o 12 meses suma muestras distintas, no los mismos hogares.
# MAGIC 4. **Alineación con las covariables.** Los indicadores de TerriData son anuales con corte a
# MAGIC    diciembre (celda «TerriData»): una tasa anual describe el mismo período que sus covariables.
# MAGIC 5. **Validación externa** contra el DANE, por dominio y en el agregado de los 23 dominios.
# MAGIC
# MAGIC ## TD anual oficial por ciudad
# MAGIC
# MAGIC El anexo DANE no publica la serie anual por ciudad. Las cifras trimestrales son promedios de tres
# MAGIC meses, así que la TD anual es la razón de las sumas de los cuatro trimestres que no se pisan
# MAGIC (Ene-Mar, Abr-Jun, Jul-Sep, Oct-Dic): `TD = Σ_q DESEMPLEADOS_q / Σ_q PEA_q × 100`. La fórmula se
# MAGIC comprueba contra los dos totales anuales que el anexo sí publica (hoja «Anuales»): «Total 13
# MAGIC ciudades y áreas metropolitanas» y «Total 10 ciudades» (`tesis.geih_bronce.datos_anuales`).
# MAGIC
# MAGIC ## PEA = ocupados + desocupados
# MAGIC
# MAGIC En `tesis.geih_oro.mercado_laboral` la bandera `PEA` está mal en enero-marzo de 2018: todas las
# MAGIC personas de 15+ quedan como PEA (la unión con inactivos no encuentra a nadie), lo que subestima
# MAGIC la tasa de esos meses. Aquí la PEA es `OCUPADO + DESOCUPADO`, que reproduce la cifra del DANE en
# MAGIC esos meses y coincide con la bandera en los demás; la celda «Reconciliación» lo muestra mes a
# MAGIC mes. La corrección en la capa plata corresponde a G7-B5.
# MAGIC
# MAGIC ## Limitación
# MAGIC
# MAGIC El error estándar es el del bootstrap simple de `EstimacionDirecta`, que no reproduce estratos ni
# MAGIC conglomerados (G7-B3). Sirve para comparar ventanas entre sí, no como varianza de diseño.
# MAGIC
# MAGIC ## Salidas
# MAGIC
# MAGIC * `tesis.preprocesamiento.sensibilidad_ventana_temporal`: una fila por ventana y dominio
# MAGIC * `tesis.preprocesamiento.resumen_ventana_temporal`: una fila por ventana
# MAGIC * `tesis.preprocesamiento.validacion_anual_totales`: comprobación de la fórmula anual
# MAGIC * Figura `ventana_sensibilidad` en `/Volumes/tesis/preprocesamiento/figuras_eda`

# COMMAND ----------

# DBTITLE 1,Setup: rutas, imports y período
# MAGIC %pip install tqdm

# COMMAND ----------

import os
import sys

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
from preprocesamiento.shared.estimador_sae import EstimacionDirecta
from analisis.shared import descriptivos as desc
from analisis.shared import ventana_temporal as vt

PER_ESTIMACION, MES_ESTIMACION = resolver_periodo(dbutils)
print(f"Mes de cierre de las ventanas: {PER_ESTIMACION}-{MES_ESTIMACION:02d}")
for nombre, n in VENTANAS_TEMPORALES.items():
    print(f"  {nombre:<10} {vt.etiqueta_ventana(PER_ESTIMACION, MES_ESTIMACION, n)}")

# COMMAND ----------

# DBTITLE 1,Reconciliación de la PEA (bandera PEA vs ocupados + desocupados)
# Meses de la ventana más larga. N_DIFERENCIA > 0 marca los meses en que la bandera PEA cuenta
# inactivos; ahí TD_BANDERA_PCT queda por debajo de TD_OC_DS_PCT.
reconciliacion = vt.reconciliacion_pea(
    spark,
    meses_ventana(PER_ESTIMACION, MES_ESTIMACION, max(VENTANAS_TEMPORALES.values())),
)
display(reconciliacion)
meses_afectados = reconciliacion[reconciliacion["N_DIFERENCIA"] != 0]
if meses_afectados.empty:
    print("La bandera PEA coincide con OCUPADO + DESOCUPADO en todos los meses.")
else:
    print(
        f"⚠ La bandera PEA no coincide con OCUPADO + DESOCUPADO en {len(meses_afectados)} meses: "
        + ", ".join(f"{r.PER}-{r.MES:02d}" for r in meses_afectados.itertuples())
        + ". Este notebook usa OCUPADO + DESOCUPADO (ver la documentación; corrección de fondo: G7-B5)."
    )

# COMMAND ----------

# DBTITLE 1,TerriData: mes de corte de los indicadores
# Cuántos indicadores de TerriData tienen dato en cada mes del año de cierre: si casi todos están en
# diciembre, las covariables describen el año calendario (criterio 4).
corte_terridata = (
    spark.table(TBL_TERRIDATA_BRONCE)
    .filter(F.col("ANO") == PER_ESTIMACION)
    .groupBy("MES")
    .agg(F.countDistinct("CODIGO_INDICADOR").alias("N_INDICADORES"))
    .orderBy("MES")
    .toPandas()
)
corte_terridata["PROPORCION"] = (
    corte_terridata["N_INDICADORES"] / corte_terridata["N_INDICADORES"].sum()
)
display(corte_terridata)
en_diciembre = corte_terridata.loc[corte_terridata["MES"] == 12, "PROPORCION"].sum()
print(
    f"Indicadores de TerriData {PER_ESTIMACION} con corte a diciembre: {100 * en_diciembre:.1f} %"
)

# COMMAND ----------

# DBTITLE 1,Cifras publicadas por el DANE
df_municipales = spark.table(TBL_DATOS_MUNICIPALES).toPandas()
df_anuales = spark.table(TBL_DATOS_ANUALES).toPandas()

# Comprobación de la fórmula anual (solo para el año calendario: ventana de 12 meses que cierra
# en diciembre).
validacion_anual = pd.DataFrame()
if MES_ESTIMACION == 12:
    validacion_anual = vt.validar_formula_anual(
        df_municipales, df_anuales, PER_ESTIMACION
    )
    display(validacion_anual)
    for r in validacion_anual.itertuples():
        print(
            f"[{'PASS' if r.COINCIDE else 'FAIL'}] fórmula anual, {r.CONJUNTO}: reconstruida "
            f"{r.TD_RECONSTRUIDA:.4f} vs publicada {r.TD_PUBLICADA:.4f} (dif. {r.DIF_PP:+.4f} pp)"
        )
else:
    print(
        "El cierre no es diciembre: la ventana de 12 meses no es un año calendario y no se valida."
    )

# COMMAND ----------

# DBTITLE 1,Estimación directa en cada ventana
# Misma estimación que estimacion_directa.py (Hájek con FEX_C18, bootstrap simple con la misma
# semilla y número de réplicas) sobre los meses de cada ventana.
estimador = EstimacionDirecta(
    spark, num_replicas=BOOTSTRAP_REPLICAS, seed=BOOTSTRAP_SEED
)
bloques = []
total_23_dane = {}
for ventana, n_meses in VENTANAS_TEMPORALES.items():
    periodo = vt.etiqueta_ventana(PER_ESTIMACION, MES_ESTIMACION, n_meses)
    print(f"\n── {ventana}: {periodo} ──")
    df_pea, conteos, meses_presentes = vt.preparar_datos_ventana(
        spark, PER_ESTIMACION, MES_ESTIMACION, n_meses
    )
    faltantes = set(meses_ventana(PER_ESTIMACION, MES_ESTIMACION, n_meses)) - set(
        meses_presentes
    )
    if faltantes:
        print(f"⚠ Sin datos en GEIH para: {sorted(faltantes)}")

    resultado = estimador.estimar(dataframe=df_pea, grupo_cols=GRUPO_COLS)
    dane = vt.td_dane_ventana(df_municipales, PER_ESTIMACION, MES_ESTIMACION, n_meses)
    total = dane.loc[dane["CIUDAD"] == NOMBRE_TOTAL_23, "TD_DANE"]
    total_23_dane[ventana] = None if total.empty else float(total.iloc[0])

    bloque = (
        resultado.merge(conteos, on="CODIGO_DOMINIO", how="left", validate="one_to_one")
        .merge(
            dane.rename(columns={"CIUDAD": "NOMBRE_DOMINIO"}),
            on="NOMBRE_DOMINIO",
            how="left",
            validate="one_to_one",
        )
        .assign(VENTANA=ventana, N_MESES_VENTANA=n_meses, PERIODO=periodo)
    )
    bloque["TD_DANE"] = bloque["TD_DANE"].astype(float)
    bloque["DIF_PP"] = bloque["TASA_DESEMPLEO_PCT"] - bloque["TD_DANE"]
    bloques.append(bloque[vt.COLUMNAS_DETALLE])

detalle = pd.concat(bloques, ignore_index=True)
display(detalle)

# COMMAND ----------

# DBTITLE 1,Validaciones (solo informativas)
# 1. La ventana TRIMESTRE debe reproducir la tasa que hoy usa el modelo: confirma que este notebook
#    estima lo mismo que estimacion_directa.py (la PEA por ocupados + desocupados coincide con la
#    bandera en Oct-Dic).
actual = spark.table(TBL_ESTIMACION_DIRECTA).toPandas()
actual = actual[(actual["PER"] == PER_ESTIMACION) & (actual["MES"] == MES_ESTIMACION)]
if actual.empty:
    print(
        f"{TBL_ESTIMACION_DIRECTA} no tiene el período {PER_ESTIMACION}-{MES_ESTIMACION:02d}: no se compara."
    )
else:
    trimestre = detalle[detalle["VENTANA"] == "TRIMESTRE"].merge(
        actual[["CODIGO_DOMINIO", "TASA_DESEMPLEO_PCT"]],
        on="CODIGO_DOMINIO",
        suffixes=("", "_ACTUAL"),
    )
    dif_max = (
        (trimestre["TASA_DESEMPLEO_PCT"] - trimestre["TASA_DESEMPLEO_PCT_ACTUAL"])
        .abs()
        .max()
    )
    print(
        f"[{'PASS' if dif_max < 1e-8 and len(trimestre) == len(actual) else 'FAIL'}] la ventana "
        f"TRIMESTRE reproduce {TBL_ESTIMACION_DIRECTA} ({len(trimestre)} de {len(actual)} dominios; "
        f"dif. máx. {dif_max:.2e} pp)"
    )

# 2. Cada dominio y el agregado de los 23 contra el DANE, por ventana.
for ventana, g in detalle.groupby("VENTANA", sort=False):
    con_dane = g["TD_DANE"].notna()
    if not con_dane.any():
        print(f"[N/A ] {ventana}: el DANE no publica esta ventana por ciudad")
        continue
    ok = g.loc[con_dane, "DIF_PP"].abs() <= vt.TOLERANCIA_PP
    print(
        f"[{'PASS' if ok.all() and con_dane.all() else 'FAIL'}] {ventana}: {int(ok.sum())} de "
        f"{len(g)} dominios coinciden con el DANE (tolerancia {vt.TOLERANCIA_PP} pp)"
    )
    if not ok.all():
        display(
            g.loc[con_dane][~ok][
                ["NOMBRE_DOMINIO", "TASA_DESEMPLEO_PCT", "TD_DANE", "DIF_PP"]
            ]
        )
    total = total_23_dane.get(ventana)
    if total is not None:
        dif = vt.agregado_dominios(g) - total
        print(
            f"[{'PASS' if abs(dif) <= vt.TOLERANCIA_PP else 'FAIL'}] {ventana}: agregado de los "
            f"dominios vs «{NOMBRE_TOTAL_23}» {total:.4f} (dif. {dif:+.4f} pp)"
        )

# COMMAND ----------

# DBTITLE 1,Resumen y comparación entre ventanas
resumen = vt.resumen_ventanas(detalle, total_23_dane)
comparacion = vt.comparar_ventanas(detalle)
display(resumen)
display(comparacion)

# COMMAND ----------

# DBTITLE 1,Figura e interpretación
fig = vt.figura_ventanas(detalle)
desc.guardar_figura(fig, "ventana_sensibilidad", VOLUMEN_FIGURAS)
display(fig)
print(vt.interpretar_ventanas(resumen, comparacion))

# COMMAND ----------

# DBTITLE 1,Escritura de las tablas
for tabla, df in [
    (TBL_SENSIBILIDAD_VENTANA, detalle),
    (TBL_RESUMEN_VENTANA, resumen),
    (TBL_VALIDACION_ANUAL, validacion_anual),
]:
    if df.empty:
        print(f"Sin filas para {tabla}: no se escribe.")
        continue
    (
        spark.createDataFrame(df)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(tabla)
    )
    print(f"Tabla escrita: {tabla} ({len(df)} filas)")
