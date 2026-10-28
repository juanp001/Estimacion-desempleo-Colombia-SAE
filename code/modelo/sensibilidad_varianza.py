# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Sensibilidad del Fay-Herriot a la varianza de muestreo ψ_d (G7-B3)
# MAGIC
# MAGIC El modelo trata la varianza de muestreo ψ_d de cada estimación directa como **conocida**
# MAGIC (Morales et al., 2021, p. 427). ψ_d es el bootstrap por viviendas dentro de cada dominio
# MAGIC (`preprocesamiento/shared/bootstrap.py`). Los microdatos no traen el estrato interno ni el
# MAGIC segmento de la GEIH, así que ψ_d es una aproximación a la varianza del diseño: **no se sabe si
# MAGIC esta es mayor o menor, ni por cuánto**, y el DANE no publica los CV por ciudad para
# MAGIC compararla. Este notebook mide cuánto cambian las conclusiones si ψ_d se equivoca.
# MAGIC
# MAGIC 1. **Varianzas directas alternativas** con los mismos microdatos: bootstrap por personas
# MAGIC    (cada persona es su propio conglomerado) y linealización de Taylor con viviendas como
# MAGIC    conglomerado (DANE, GEIH v9, PDF 15). La razón ψ_viviendas / ψ_personas es el efecto de
# MAGIC    remuestrear la vivienda completa.
# MAGIC 2. **Función de varianza generalizada (GVF)**, dos formas sobre la ψ_d base:
# MAGIC    A) `log ψ = b0 + b1·y + b2·n` (Morales, p. 427, ec. 16.6; ejemplo p. 454-455) y
# MAGIC    B) `log ψ = b0 + b1·log(p(1−p)) + b2·log n`, la forma del efecto de diseño
# MAGIC    ψ ≈ deff·p(1−p)/n (Téllez, 2020, p. 15; Chile pobreza 2016, PDF 4). Se retransforma con el
# MAGIC    factor Δ que conserva la media de las ψ (ENUSC 2018, PDF 15-16). Se evalúa con R²,
# MAGIC    residuos y la figura de ψ observada contra predicha (Morales, Fig. 16.1). Es **solo un
# MAGIC    escenario**: la GVF estabiliza ψ̂ inestables por muestras pequeñas (ENUSC, PDF 15) y aquí
# MAGIC    cada dominio tiene miles de viviendas.
# MAGIC 3. **Escenarios del modelo** (R-65): base, Taylor (método independiente), GVF A (la del
# MAGIC    libro) y la grilla ψ_d × k con k ∈ {1/3, 1/2, 2/3, 3/2, 2, 3}, simétrica en escala log
# MAGIC    porque no se presume la dirección del error. El bootstrap por personas y la GVF B quedan
# MAGIC    solo como columnas de `sensibilidad_varianza_directa` (y la GVF B en `gvf_ajuste` y la
# MAGIC    figura): en la corrida anterior cambiaban el EBLUP ≤ 0,0075 pp, eran indistinguibles de
# MAGIC    Taylor y la GVF A y daban el mismo ganador. La razón es una sola: con Â/ψ̄ alto, γ ≈ 1 y
# MAGIC    el EBLUP casi coincide con la directa cualquiera sea ψ (Morales, pp. 427 y 440; Benedetti
# MAGIC    et al., 2024, p. 143). La grilla es la que acota el error desconocido del diseño. En cada uno se reajustan todas las variantes, se elige el ganador con la regla
# MAGIC    del modelo (p. 453) y se comparan con la base: Â/ψ̄ (Benedetti et al., 2024, p. 143:
# MAGIC    subestimar ψ pesa más cuando Â es pequeña frente a ψ), γ, coeficientes, EBLUP, CV y
# MAGIC    confiabilidad, λ₁ del benchmarking y la predicción sintética de los municipios.
# MAGIC
# MAGIC No alimenta al modelo: `fay_herriot.py` sigue usando la ψ_d base.
# MAGIC
# MAGIC ## Salidas
# MAGIC
# MAGIC * `tesis.modelo.sensibilidad_varianza_directa`: una fila por dominio con cada ψ_d
# MAGIC * `tesis.modelo.gvf_ajuste`: coeficientes y bondad de ajuste de las dos GVF
# MAGIC * `tesis.modelo.sensibilidad_varianza_fh`: una fila por escenario
# MAGIC * `tesis.modelo.sensibilidad_varianza_coeficientes`: escenario × parámetro
# MAGIC * `tesis.modelo.sensibilidad_varianza_dominios` y `..._municipios`: escenario × unidad

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# R-67: `code/` en sys.path (el notebook está en code/<carpeta>/); `comun.entorno` hace el resto
_ruta_nb = (
    dbutils.notebook.entry_point.getDbutils()
    .notebook()
    .getContext()
    .notebookPath()
    .get()
)
CODE_DIR = "/Workspace" + os.path.dirname(os.path.dirname(_ruta_nb))
sys.path.insert(0, CODE_DIR)

from comun.entorno import agregar_rutas

agregar_rutas(CODE_DIR, "modelo")

from shared.config import *
from shared.fay_herriot import FayHerriotClasico
from shared.seleccion_modelo import elegir_ganador, subconjuntos_covariables
from shared.datos_modelo import alias_desde_catalogo, periodo_unico, preparar_municipios
from shared.escritura import escribir_tabla
from shared.sensibilidad_varianza import (
    ESCENARIO_BASE,
    ajustar_escenarios,
    ajustar_gvf,
    escenarios_psi,
    figura_escenarios,
    figura_gvf,
    interpretar_sensibilidad,
    tabla_gvf,
)

# La estimación directa y la preparación de la PEA se importan por ruta completa porque
# `shared` aquí es modelo/shared.
from preprocesamiento.shared.config import (
    BOOTSTRAP_REPLICAS,
    BOOTSTRAP_SEED,
    GRUPO_COLS,
)
from preprocesamiento.shared.estimador_sae import EstimacionDirecta
from analisis.shared.ventana_temporal import preparar_datos_ventana

import warnings

warnings.filterwarnings("ignore")

# COMMAND ----------

# DBTITLE 1,1. Carga de datos y modelo base
# Mapa código → alias del catálogo de literatura (R-63), como en fay_herriot.py.
alias_a_codigo = {alias: codigo for codigo, alias in alias_desde_catalogo().items()}

df = (
    spark.table(TBL_COVARIABLES_SELECCIONADAS)
    .toPandas()
    .sort_values("CODIGO_DOMINIO")
    .reset_index(drop=True)
)
covars_eda = [c for c in df.columns if c in alias_a_codigo]
# R-04: subconjuntos del conjunto del EDA más el modelo de solo intercepto (EC0).
nombres_covars = subconjuntos_covariables(covars_eda)

PERIODO = periodo_unico(df, TBL_COVARIABLES_SELECCIONADAS)
PER_MODELO, MES_MODELO = PERIODO["PER"], PERIODO["MES"]
N_MESES_MODELO = PERIODO["N_MESES_VENTANA"]
print(f"Ventana: {PERIODO['PERIODO']} — {len(df)} dominios")

# Modelo base: el mismo que fay_herriot.py (ψ_d = SE_BOOTSTRAP_PCT², bootstrap por viviendas).
modelos_base = [FayHerriotClasico(c, df, Y_COL, SE_COL) for c in nombres_covars]
for m in modelos_base:
    m.ajustar()
ganador_base = (
    elegir_ganador(
        modelos_base,
        nombres_covars,
        delta_aic=DELTA_AIC_EQUIVALENTE,
        alfa=ALFA_SIGNIFICANCIA,
    )
    if len(modelos_base) > 1
    else modelos_base[0]
)
covars_referencia = list(ganador_base.covars)
print(
    "Especificación de referencia: "
    + (" + ".join(covars_referencia) or "EC0 (solo intercepto, R-04)")
)

# COMMAND ----------

# DBTITLE 1,2. Varianzas directas alternativas (mismos microdatos y misma ventana)
# preparar_datos_ventana replica el filtro de estimacion_directa (PEA 15+, ventana, dominio,
# FEX := FEX_C18). Se estima dos veces con la misma semilla: por viviendas (debe reproducir la
# tabla) y por personas.
df_pea, _, _ = preparar_datos_ventana(spark, PER_MODELO, MES_MODELO, N_MESES_MODELO)
estimador = EstimacionDirecta(
    spark, num_replicas=BOOTSTRAP_REPLICAS, seed=BOOTSTRAP_SEED
)

por_viviendas = estimador.estimar(df_pea, GRUPO_COLS, col_conglomerado="ID_VIVIENDA")
por_personas = estimador.estimar(df_pea, GRUPO_COLS, col_conglomerado=None)

directa = (
    df[["CODIGO_DOMINIO", "NOMBRE_DOMINIO", Y_COL, SE_COL, "N_PEA", "N_VIVIENDAS"]]
    .merge(
        por_viviendas[["CODIGO_DOMINIO", "SE_BOOTSTRAP_PCT", "SE_TAYLOR_PCT"]].rename(
            columns={"SE_BOOTSTRAP_PCT": "SE_VIVIENDAS_RECALC_PCT"}
        ),
        on="CODIGO_DOMINIO",
        how="left",
        validate="one_to_one",
    )
    .merge(
        por_personas[["CODIGO_DOMINIO", "SE_BOOTSTRAP_PCT"]].rename(
            columns={"SE_BOOTSTRAP_PCT": "SE_PERSONAS_PCT"}
        ),
        on="CODIGO_DOMINIO",
        how="left",
        validate="one_to_one",
    )
)
directa["PSI_VIVIENDAS"] = directa[SE_COL] ** 2
directa["PSI_PERSONAS"] = directa["SE_PERSONAS_PCT"] ** 2
directa["PSI_TAYLOR"] = directa["SE_TAYLOR_PCT"] ** 2
directa["EFECTO_VIVIENDA"] = directa["PSI_VIVIENDAS"] / directa["PSI_PERSONAS"]
directa["RAZON_BOOT_TAYLOR"] = directa["PSI_VIVIENDAS"] / directa["PSI_TAYLOR"]

dif_recalc = (directa["SE_VIVIENDAS_RECALC_PCT"] - directa[SE_COL]).abs().max()
print(
    f"[{'PASS' if dif_recalc < 1e-9 else 'FAIL'}] el bootstrap por viviendas recalculado "
    f"reproduce SE_BOOTSTRAP_PCT de la tabla (dif. máx. {dif_recalc:.2e} pp)"
)
print(
    "ψ viviendas / ψ personas: mediana "
    f"{directa['EFECTO_VIVIENDA'].median():.3f}, rango "
    f"[{directa['EFECTO_VIVIENDA'].min():.3f}, {directa['EFECTO_VIVIENDA'].max():.3f}]"
)
print(
    "ψ bootstrap / ψ Taylor:      mediana "
    f"{directa['RAZON_BOOT_TAYLOR'].median():.3f}, rango "
    f"[{directa['RAZON_BOOT_TAYLOR'].min():.3f}, {directa['RAZON_BOOT_TAYLOR'].max():.3f}]"
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Función de varianza generalizada
# MAGIC
# MAGIC **Cómo leer la figura.** Izquierda: cada punto es un dominio; si la GVF reprodujera bien la
# MAGIC varianza, los puntos caerían sobre la diagonal (Morales et al., p. 455). Derecha: residuos de
# MAGIC log ψ; se rotulan los que superan dos desviaciones estándar residuales. Un R² bajo indica que
# MAGIC el tamaño de muestra y la tasa no explican bien la varianza, como encontró el Ministerio de
# MAGIC Desarrollo Social de Chile con la Casen (Chile pobreza 2016, PDF 4); en ese caso la GVF
# MAGIC cambiaría las ψ por algo peor sustentado.

# COMMAND ----------

# DBTITLE 1,3. Ajuste y evaluación de la GVF
psi_base = directa["PSI_VIVIENDAS"].to_numpy()
gvf_a = ajustar_gvf(psi_base, directa[Y_COL], directa["N_PEA"], "A")
gvf_b = ajustar_gvf(psi_base, directa[Y_COL], directa["N_PEA"], "B")

df_gvf = tabla_gvf([gvf_a, gvf_b])
display(df_gvf)
for g in (gvf_a, gvf_b):
    razon = g["psi_delta"] / psi_base
    print(
        f"GVF {g['forma']}: R² = {g['r2']:.3f} (ajustado {g['r2_ajustado']:.3f}), "
        f"σ̂² = {g['sigma2']:.4f}, Δ = {g['delta']:.4f}, exp(σ̂²/2) = {np.exp(g['sigma2'] / 2):.4f}; "
        f"ψ_gvf/ψ entre {razon.min():.3f} y {razon.max():.3f}"
    )

directa["PSI_GVF_A"] = gvf_a["psi_delta"]
directa["PSI_GVF_B"] = gvf_b["psi_delta"]
directa["RAZON_GVF_A"] = directa["PSI_GVF_A"] / directa["PSI_VIVIENDAS"]
directa["RAZON_GVF_B"] = directa["PSI_GVF_B"] / directa["PSI_VIVIENDAS"]

fig = figura_gvf(psi_base, [gvf_a, gvf_b], directa["NOMBRE_DOMINIO"])
display(fig)
plt.close(fig)

display(directa)
escribir_tabla(spark, directa, TBL_SENS_VARIANZA_DIRECTA)
escribir_tabla(spark, df_gvf, TBL_GVF_AJUSTE)

# COMMAND ----------

# DBTITLE 1,4. Municipios objetivo (matriz de diseño de la especificación de referencia)
df_new, X_municipios = preparar_municipios(
    spark.table(TBL_MUNICIPIOS_SIN_ENCUESTA).toPandas(),
    covars_referencia,
    alias_a_codigo,
)
print(f"Municipios objetivo: {len(df_new)}")

# COMMAND ----------

# DBTITLE 1,5. Escenarios del modelo
# R-65: solo Taylor (método independiente) y la GVF A (la del libro) reajustan el FH; el bootstrap
# por personas y la GVF B quedan como columnas de `directa`, porque daban lo mismo.
escenarios = escenarios_psi(
    psi_base,
    {
        "Taylor viviendas": directa["PSI_TAYLOR"].to_numpy(),
        "GVF A (Morales)": directa["PSI_GVF_A"].to_numpy(),
    },
)
# `directa` conserva el orden de `df` (merge por la izquierda), así que cada vector ψ está
# alineado con los dominios del modelo.
resumen, coeficientes, dominios, municipios = ajustar_escenarios(
    df,
    escenarios,
    nombres_covars,
    covars_referencia,
    Y_COL,
    df[COL_PESO_NIVEL1].to_numpy(dtype=float),
    X_municipios,
    delta_aic=DELTA_AIC_EQUIVALENTE,
    alfa=ALFA_SIGNIFICANCIA,
)

municipios = municipios.merge(
    df_new[["CODIGO_MUNICIPIO", "MUNICIPIO"]]
    .reset_index(drop=True)
    .rename_axis("FILA_MUNICIPIO")
    .reset_index(),
    on="FILA_MUNICIPIO",
    how="left",
).drop(columns="FILA_MUNICIPIO")

display(resumen)
display(coeficientes)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cambio de los EBLUP por escenario
# MAGIC
# MAGIC **Cómo leer la figura.** Cada columna es un dominio, de menor a mayor ψ base; cada punto es
# MAGIC cuánto cambia su EBLUP frente a la base en un escenario. Si Â es grande frente a ψ, el peso γ
# MAGIC de la estimación directa es cercano a 1 y el EBLUP casi no se mueve aunque ψ cambie; los
# MAGIC dominios de la derecha (ψ más alta) son los primeros en moverse.

# COMMAND ----------

# DBTITLE 1,6. Figura, interpretación y escritura
fig = figura_escenarios(dominios, [e for e in escenarios if e != ESCENARIO_BASE])
display(fig)
plt.close(fig)

print(interpretar_sensibilidad(resumen))

escribir_tabla(spark, resumen, TBL_SENS_VARIANZA_FH)
escribir_tabla(spark, coeficientes, TBL_SENS_VARIANZA_COEFICIENTES)
escribir_tabla(spark, dominios, TBL_SENS_VARIANZA_DOMINIOS)
escribir_tabla(spark, municipios, TBL_SENS_VARIANZA_MUNICIPIOS)
