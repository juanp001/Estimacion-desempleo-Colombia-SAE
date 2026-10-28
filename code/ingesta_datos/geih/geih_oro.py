# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Consolidación de Mercado Laboral GEIH - Capa Oro
# MAGIC
# MAGIC Genera la tabla analítica final `tesis.geih_oro.mercado_laboral` consolidando
# MAGIC todas las tablas plata en una vista desnormalizada lista para análisis.
# MAGIC
# MAGIC ## Estrategia de joins
# MAGIC LEFT JOIN desde `caracteristicas_generales` (tabla base) hacia todas las demás,
# MAGIC preservando todas las personas aunque no tengan registros en otras tablas.
# MAGIC NULLs en indicadores laborales se reemplazan con 0 via `coalesce`.
# MAGIC
# MAGIC ## Dimensiones y factor de expansión
# MAGIC * Geografía (R-24): el nombre del departamento sale de `tesis.dim.dim_divipola` por
# MAGIC   `CODIGO_DPTO`, así que no queda NULL en departamentos sin capital GEIH (p. ej. Cundinamarca,
# MAGIC   25); el municipio sale de `tesis.dim.dim_geih_divipola` por `CODIGO_AREA`. Fuera de las 32
# MAGIC   áreas de esa tabla, `MUNICIPIO` queda en NULL.
# MAGIC * `FEX_C18` (G7-B6, `shared/transformations/factor_expansion.py`): en el marco nuevo es el `FEX`
# MAGIC   del archivo (ya calibrado con el CNPV 2018); en el marco antiguo sale de `tesis.geih_plata.dim_fex`.
# MAGIC   Un factor faltante ya no se imputa con 0 ni con `FEX_C_2011` (censo 2005): si alguna persona queda
# MAGIC   sin factor el notebook se detiene **antes** de escribir la tabla.
# MAGIC
# MAGIC * `ID_VIVIENDA` (G7-B3) = `PERIODO` + `DIRECTORIO`: identifica la vivienda, que es el conglomerado
# MAGIC   que remuestrea el bootstrap de la estimación directa.
# MAGIC
# MAGIC ## Reconciliación (G7-B5)
# MAGIC Después de escribir la tabla se verifican, solo con PASS/FAIL (no detienen el notebook):
# MAGIC * `llaves_sin_pareja`: % de llaves de cada módulo sin pareja en características generales
# MAGIC   (inactivos frente a fuerza de trabajo, porque esa unión define la PEA del marco antiguo).
# MAGIC   Desde R-17 también en la dirección contraria:
# MAGIC   * `PET_SIN_FT`: personas de 15 años y más sin registro en fuerza de trabajo (el LEFT JOIN
# MAGIC     les daría PET = 0 y PEA = 0 sin aviso). PASS/FAIL.
# MAGIC   * `FEX_SIN_CG`: registros de `dim_fex` sin persona en características generales. Solo AVISO,
# MAGIC     porque no cambian la estimación: en 2018 son 9.866 (≈ 280 viviendas por mes,
# MAGIC     `DIRECTORIO` 4518316-4804436), probablemente San Andrés, que la GEIH publica aparte.
# MAGIC * `reconciliacion_fuerza_trabajo`: por período y dominio, PET, PEA, PEI, OC y DS, y las
# MAGIC   personas que rompen PEA = OC + DS o PET = PEA + PEI. Las identidades se revisan sobre
# MAGIC   toda la PET de la fuente; las columnas `*_15` y `TD_15_PCT` (R-53) dan la versión de 15
# MAGIC   años y más, la comparable con el anexo DANE y con `estimacion_directa`.
# MAGIC
# MAGIC ## PET: 15 años y más (R-53)
# MAGIC En el marco antiguo la bandera `PET` es la de la fuente: 12+ urbana y 10+ rural. La serie
# MAGIC recalibrada con el CNPV 2018 y la estimación directa usan 15+, así que toda tasa que se compare
# MAGIC con ellas debe filtrar `EDAD >= 15` (en 2018 la PET de la fuente trae 40.403 registros de
# MAGIC 10-14 años; en el marco nuevo la PET ya es 15+).
# MAGIC
# MAGIC ## Ejemplo de uso
# MAGIC ```sql
# MAGIC SELECT PERIODO, DEPARTAMENTO,
# MAGIC        SUM(DESOCUPADO * FEX_C18) / SUM(PEA * FEX_C18) * 100 AS tasa_desempleo
# MAGIC FROM tesis.geih_oro.mercado_laboral
# MAGIC WHERE PEA = 1 AND EDAD >= 15
# MAGIC GROUP BY PERIODO, DEPARTAMENTO
# MAGIC ```

# COMMAND ----------

# DBTITLE 1,Importación de librerías
import os
import sys

# R-67: `code/` en sys.path para importar `comun` (el notebook está en code/ingesta_datos/<carpeta>/)
_ruta_nb = (
    dbutils.notebook.entry_point.getDbutils()
    .notebook()
    .getContext()
    .notebookPath()
    .get()
)
sys.path.insert(
    0, "/Workspace" + os.path.dirname(os.path.dirname(os.path.dirname(_ruta_nb)))
)

from pyspark.sql.functions import col, coalesce, concat_ws, lit

from shared.config.geih_config import (
    TBL_CG_PLATA,
    TBL_FT_PLATA,
    TBL_NO_PLATA,
    TBL_OC_PLATA,
    TBL_FEX_PLATA,
    TBL_DIM_DIVIPOLA,
    TBL_DIM_GEIH_DIVIPOLA,
    TBL_MERCADO_LABORAL,
    TBL_IN_CAB_MA,
    TBL_IN_RESTO_MA,
    TBL_DIM_DOMINIO,
    TBL_RECONCILIACION_FT,
    TBL_LLAVES_SIN_PAREJA,
)
from shared.transformations.campos_nucleo import CAMPOS_NUCLEO_MARCO_ANTIGUO
from shared.transformations.factor_expansion import (
    factor_expansion_c18,
    personas_sin_factor,
    verificar_factor_expansion,
)
from shared.transformations.reconciliacion import (
    llaves_sin_pareja,
    reconciliar_fuerza_trabajo,
)
from comun.spark_utils import escribir_tabla

# COMMAND ----------

# DBTITLE 1,Cargar tablas fuente
cg = spark.table(TBL_CG_PLATA)
ft = spark.table(TBL_FT_PLATA)
no = spark.table(TBL_NO_PLATA)
oc = spark.table(TBL_OC_PLATA)
fex = spark.table(TBL_FEX_PLATA)
geih_div = spark.table(TBL_DIM_GEIH_DIVIPOLA)
# R-24: un nombre por departamento, de la DIVIPOLA completa
departamentos = (
    spark.table(TBL_DIM_DIVIPOLA)
    .select("CODIGO_DEPARTAMENTO", "DEPARTAMENTO")
    .distinct()
)

# COMMAND ----------

# DBTITLE 1,Consolidar y guardar tabla oro
df = (
    cg.join(ft, cg.PK == ft.PK, "left")
    .join(no, cg.PK == no.PK, "left")
    .join(fex, cg.PK == fex.PK, "left")
    .join(oc, cg.PK == oc.PK, "left")
    # Departamento desde dim_divipola; municipio desde dim_geih_divipola (32 capitales)
    .join(
        departamentos.alias("div_dep"),
        cg.CODIGO_DPTO == col("div_dep.CODIGO_DEPARTAMENTO"),
        "left",
    )
    .join(
        geih_div.alias("div_mun"),
        cg.CODIGO_AREA == col("div_mun.CODIGO_AREA_GEIH"),
        "left",
    )
    .select(
        cg.PK,
        cg.PERIODO,
        cg.PER,
        cg.MES,
        # Vivienda (G7-B3): conglomerado del bootstrap de la estimación directa. DIRECTORIO se
        # antepone con el período para que la llave no se repita entre meses de una ventana.
        concat_ws("_", cg.PERIODO, cg.DIRECTORIO).alias("ID_VIVIENDA"),
        cg.CODIGO_DPTO.alias("CODIGO_DEPARTAMENTO"),
        col("div_dep.DEPARTAMENTO"),
        col("div_mun.CODIGO_MUNICIPIO"),
        # R-52: MUNICIPIO, FEX y SEXO no los lee ninguna etapa siguiente, pero se conservan a
        # propósito: MUNICIPIO y SEXO para consultar la tabla, FEX para auditar FEX_C18 (G7-B6)
        col("div_mun.MUNICIPIO"),
        cg.MARCO,
        cg.FEX,
        factor_expansion_c18(cg.MARCO, cg.FEX, fex["FEX_C18"]).alias("FEX_C18"),
        cg.SEXO,
        cg.EDAD,
        coalesce(ft["PEA"].cast("int"), lit(0)).alias("PEA"),
        coalesce(ft["PEI"].cast("int"), lit(0)).alias("PEI"),
        coalesce(ft["PET"].cast("int"), lit(0)).alias("PET"),
        coalesce(no["DESOCUPADO"].cast("int"), lit(0)).alias("DESOCUPADO"),
        coalesce(oc["OCUPADO"].cast("int"), lit(0)).alias("OCUPADO"),
    )
)

# G7-B6: ninguna persona puede llegar a oro sin factor; si falla, no se escribe la tabla
df_sin_fex = personas_sin_factor(df)
print(
    df_sin_fex.groupBy("MARCO", "PER")
    .sum("N_PERSONAS", "N_SIN_FEX")
    .orderBy("PER")
    .toPandas()
    .to_string(index=False)
)
verificar_factor_expansion(df_sin_fex)

escribir_tabla(df, TBL_MERCADO_LABORAL)

# COMMAND ----------

# DBTITLE 1,Reconciliación G7-B5 — llaves sin pareja entre módulos
inactivos = (
    spark.table(TBL_IN_CAB_MA)
    .select(*CAMPOS_NUCLEO_MARCO_ANTIGUO)
    .unionByName(spark.table(TBL_IN_RESTO_MA).select(*CAMPOS_NUCLEO_MARCO_ANTIGUO))
)
df_llaves = llaves_sin_pareja(cg, ft, no, oc, fex, inactivos)
escribir_tabla(df_llaves, TBL_LLAVES_SIN_PAREJA)

pdf_llaves = df_llaves.toPandas()
print(
    pdf_llaves.groupby("MODULO")[["N_LLAVES", "N_DUPLICADAS", "N_SIN_PAREJA"]]
    .sum()
    .assign(PCT_SIN_PAREJA=lambda d: (100 * d.N_SIN_PAREJA / d.N_LLAVES).round(4))
    .to_string()
)
# R-17: FEX_SIN_CG solo avisa; los factores sin persona no entran a oro (parte de CG)
SOLO_AVISO = {"FEX_SIN_CG"}
for modulo, g in pdf_llaves.groupby("MODULO"):
    ok = g.N_SIN_PAREJA.sum() == 0 and g.N_DUPLICADAS.sum() == 0
    if ok:
        print(f"PASS: {modulo} sin llaves huérfanas ni duplicadas")
    else:
        estado = "AVISO" if modulo in SOLO_AVISO else "FAIL"
        print(f"{estado}: {modulo} tiene llaves huérfanas o duplicadas")
    if not ok:
        print(g[(g.N_SIN_PAREJA > 0) | (g.N_DUPLICADAS > 0)].to_string(index=False))

# COMMAND ----------

# DBTITLE 1,Reconciliación G7-B5 — PET, PEA, PEI, OC y DS por dominio
df_reconc = reconciliar_fuerza_trabajo(
    spark.table(TBL_MERCADO_LABORAL), spark.table(TBL_DIM_DOMINIO)
)
escribir_tabla(df_reconc, TBL_RECONCILIACION_FT)

pdf_reconc = df_reconc.toPandas()
for columna, regla in [
    ("N_PEA_DISTINTA_OC_DS", "PEA = OC + DS"),
    ("N_PET_SIN_CLASE", "PET = PEA + PEI"),
    ("N_OC_Y_DS", "nadie es OC y DS a la vez"),
]:
    malos = pdf_reconc[pdf_reconc[columna] > 0]
    print(
        f"{'PASS' if malos.empty else 'FAIL'}: {regla} en todos los períodos y dominios"
    )
    if not malos.empty:
        print(malos.groupby(["PER", "MES"])[columna].sum().to_string())
