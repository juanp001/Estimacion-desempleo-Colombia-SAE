# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Modelo Fay-Herriot para Estimación de Tasa de Desempleo
# MAGIC
# MAGIC Ajusta y compara modelos Fay-Herriot clásicos sobre distintos subconjuntos de
# MAGIC covariables, selecciona el ganador por AIC + MSE medio, y produce una tabla
# MAGIC consolidada de estimaciones (EBLUP donde hay encuesta directa, sintético donde
# MAGIC no la hay).
# MAGIC
# MAGIC Dominio: PER + MES + DEPARTAMENTO + MUNICIPIO.
# MAGIC La lógica del modelo vive en `shared/` (ver `shared/modelo_area_pequena.py` y
# MAGIC `shared/fay_herriot.py`); este notebook es un orquestador fino.

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from shared.config import *
from shared.fay_herriot import FayHerriotClasico
from shared.seleccion_modelo import tabla_diagnosticos, tabla_seleccion, elegir_ganador
from shared.diagnosticos_plot import graficar_validacion, explicacion_graficas, interpretar_validacion
from shared.consolidacion import construir_tabla_final

import warnings
warnings.filterwarnings("ignore")

# COMMAND ----------

# DBTITLE 1,1. Carga de datos
df = spark.table(TBL_COVARIABLES_SELECCIONADAS).toPandas()

df["DOMINIO"] = (
    df["PER"].astype(str) + "_" +
    df["MES"].astype(str) + "_" +
    df["DEPARTAMENTO"] + "_" +
    df["MUNICIPIO"]
)

print(f"Dominios (municipios): {len(df)}")
print(f"Columnas disponibles:  {df.columns.tolist()}\n")

# COMMAND ----------

# DBTITLE 1,2. Ajuste de todos los modelos
nombres_covars = COVAR_SETS

print(f"Ajustando {len(nombres_covars)} modelo(s)...\n")
modelos = [FayHerriotClasico(covars, df, Y_COL, SE_COL) for covars in nombres_covars]
for modelo in modelos:
    modelo.ajustar()
    modelo.resultados = modelo.tabla_resultados(metadata_cols=DOMINIO_COLS)

# COMMAND ----------

# DBTITLE 1,3. Tablas EBLUP por dominio (por modelo)
eblup_display_cols = ["MUNICIPIO", Y_COL, "EBLUP", "CV_PORCENTAJE", "CV_EBLUP_PCT",
                       "GAMMA_SHRINKAGE", "MEJORA_CV_PCT"]
for i, (modelo, covars) in enumerate(zip(modelos, nombres_covars), 1):
    print("=" * 65)
    print(f"MODELO {i}: {' + '.join(covars)} — RESULTADOS EBLUP POR DOMINIO")
    print("=" * 65)
    display(modelo.resultados[eblup_display_cols])

# COMMAND ----------

# DBTITLE 1,4. Gráficas de validación (por modelo)
for i, (modelo, covars) in enumerate(zip(modelos, nombres_covars), 1):
    etiqueta = f"Modelo {i}: {' + '.join(covars)}"
    print("=" * 65)
    print(f"{etiqueta} — GRÁFICAS DE VALIDACIÓN")
    print("=" * 65)
    print(explicacion_graficas())

    figuras = graficar_validacion(modelo, etiqueta)
    for fig in figuras:
        display(fig)
        plt.close(fig)

    print(interpretar_validacion(modelo))
    print()

# COMMAND ----------

# DBTITLE 1,5. Diagnósticos por modelo
for i, (modelo, covars) in enumerate(zip(modelos, nombres_covars), 1):
    param_names = ["Intercepto"] + covars

    print("=" * 65)
    print(f"MODELO {i}: {' + '.join(covars)}")
    print("=" * 65)

    print(f"\nVarianza de efectos aleatorios (Â):   {modelo.A_hat:.6f}")
    print(f"Desv. estándar de efectos aleatorios: {np.sqrt(modelo.A_hat):.6f}")

    print("\nCOEFICIENTES:")
    coef_df = pd.DataFrame({
        "Parametro": param_names,
        "Coef":      modelo.beta_hat.round(4),
        "SE":        modelo.se_beta.round(4),
        "z":         modelo.t_stats.round(3),
        "p_valor":   modelo.p_vals.round(4),
    })
    coef_df["Signif"] = [
        "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.10 else ""
        for pv in modelo.p_vals
    ]
    display(coef_df)
    print("Signif: *** p<0.01  ** p<0.05  * p<0.10")

    print("\nDIAGNÓSTICOS:")
    print(f"  R² predictor sintético:       {modelo.r2:.4f}")
    print(f"  Media residuos estand.:       {modelo.residuals.mean():.4f}  (esperado ≈ 0)")
    print(f"  Desv. std residuos estand.:   {modelo.residuals.std():.4f}  (esperado ≈ 1)")
    sw_ok = modelo.sw_pval > 0.05
    print(f"  Shapiro-Wilk: W={modelo.sw_stat:.4f}, p={modelo.sw_pval:.4f}  "
          + ("✓ normalidad" if sw_ok else "✗ revisar normalidad"))
    print(f"  Reducción media del CV:       {modelo.resultados['MEJORA_CV_PCT'].mean():.2f} pp")
    print(f"  Shrinkage promedio (γ̄):       {modelo.gamma_i.mean():.4f}")

    validacion = modelo.validar_mse_directo()
    print("\nVALIDACIÓN MSE EBLUP vs VARIANZA DIRECTA:")
    print(f"  Dominios con MSE_EBLUP < Di: {validacion['dominios_mejoran']*100:.1f}%  "
          + ("✓ mejora generalizada" if validacion["dominios_mejoran"] >= 0.9 else
             "~ mejora parcial"      if validacion["dominios_mejoran"] >= 0.5 else
             "✗ sin mejora clara"))
    print(f"  Reducción media del MSE:      {validacion['pct_mejora_mse'].mean():.2f}%")
    print(f"  Ratio Di/MSE medio:           {validacion['mse_ratio'].mean():.4f}  (>1 indica ganancia)")
    print(f"  Ratio Di/MSE mediana:         {np.median(validacion['mse_ratio']):.4f}")
    wil_ok = validacion["wil_pval"] < 0.05
    print(f"  Wilcoxon (Di > MSE_EBLUP):   W={validacion['wil_stat']:.1f}, p={validacion['wil_pval']:.4f}  "
          + ("✓ reducción significativa" if wil_ok else "✗ no significativa"))

    print("\n  Detalle por dominio (Di vs MSE_EBLUP):")
    detail_cols = ["MUNICIPIO", "VARIANZA_DIRECTA", "MSE_EBLUP", "RATIO_MSE",
                   "MEJORA_MSE_PCT", "MEJORA_MSE"]
    display(modelo.resultados[detail_cols])
    print()

# COMMAND ----------

# DBTITLE 1,6. Selección de modelo (solo cuando hay más de un subconjunto)
if len(modelos) > 1:
    print("=" * 65)
    print("TABLA 1 — DIAGNÓSTICOS POR MODELO")
    print("=" * 65)
    display(tabla_diagnosticos(modelos, nombres_covars))
    print("  SW_pval: p-valor Shapiro-Wilk (>0.05 -> normalidad)")
    print("  Wilcoxon_pval: p-valor test Di>MSE_EBLUP (<0.05 -> reducción significativa)")
    print("  Pct_dom_mejoran: % dominios con MSE_EBLUP < Di")
    print("  Ratio_MSE_medio: Di/MSE_EBLUP medio (>1 indica ganancia de eficiencia)")

    print("\n" + "=" * 65)
    print("TABLA 2 — SELECCIÓN DE MODELO (AIC / MSE medio)")
    print("=" * 65)
    display(tabla_seleccion(modelos, nombres_covars))
    print("  Ranking por suma de posiciones en AIC + MSE_medio")
    print("  Delta_AIC: < 2 equivalentes · 2-7 moderado · > 10 sustancial")

# COMMAND ----------

# DBTITLE 1,7. Exportar resultados del modelo ganador
modelo_ganador = elegir_ganador(modelos, nombres_covars) if len(modelos) > 1 else modelos[0]

spark_df = spark.createDataFrame(modelo_ganador.resultados)
spark_df.write.mode("overwrite").option("mergeSchema", "true").saveAsTable(TBL_FAY_HERRIOT_RESULTADOS)

# COMMAND ----------

# DBTITLE 1,8. Predicción sintética para dominios sin estimación directa
# Para municipios donde NO existe estimación directa (Y ni Di), el EBLUP no puede
# calcularse: el predictor óptimo es el sintético ŷ_d = X_d'β̂ del modelo ganador,
# sin contracción (γ=0) porque no hay varianza de muestreo.
covars_ganador = modelo_ganador.covars
beta_ganador   = modelo_ganador.beta_hat

df_new = spark.table(TBL_MUNICIPIOS_SIN_ENCUESTA).toPandas()

faltantes = [c for c in covars_ganador if c not in df_new.columns]
if faltantes:
    raise ValueError(f"Faltan columnas en los datos nuevos: {faltantes}")

df_new["DOMINIO"] = (
    df_new["PER"].astype(str) + "_" +
    df_new["MES"].astype(str) + "_" +
    df_new["DEPARTAMENTO"] + "_" +
    df_new["MUNICIPIO"]
)

X_new       = np.column_stack([np.ones(len(df_new))] + [df_new[c].values for c in covars_ganador])
y_sintetico = X_new @ beta_ganador

# Incertidumbre: solo el componente de varianza del predictor sintético, x_d'Cov(β̂)x_d,
# más A_hat (efecto aleatorio no observado en un dominio sin muestra).
var_beta       = np.array([X_new[i] @ modelo_ganador.cov_beta @ X_new[i] for i in range(len(df_new))])
var_sintetico  = var_beta + modelo_ganador.A_hat
rmse_sintetico = np.sqrt(var_sintetico)
cv_sintetico   = 100 * rmse_sintetico / np.abs(y_sintetico)

df_pred = df_new[["DOMINIO"] + DOMINIO_COLS].copy()
df_pred["PRED_SINTETICO"]   = y_sintetico.round(4)
df_pred["RMSE_SINTETICO"]   = rmse_sintetico.round(4)
df_pred["CV_SINTETICO_PCT"] = cv_sintetico.round(2)
df_pred["TIPO"]             = "SINTETICO"

print(f"\nPredicciones sintéticas para {len(df_pred)} dominios sin encuesta:")
display(df_pred)

spark_df_pred = spark.createDataFrame(df_pred)
spark_df_pred.write.mode("overwrite").option("mergeSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_PREDICCION_SINTETICA
)

# COMMAND ----------

# DBTITLE 1,9. Tabla final consolidada (EBLUP + sintético)
tabla_entrenamiento = modelo_ganador.resultados[
    ["DOMINIO"] + DOMINIO_COLS + ["EBLUP", "CV_EBLUP_PCT"]
].rename(columns={"EBLUP": "TASA_DESEMPLEO_PCT", "CV_EBLUP_PCT": "CV_PCT"})
tabla_entrenamiento["TIPO"] = "EBLUP"

tabla_sintetica = df_pred.rename(
    columns={"PRED_SINTETICO": "TASA_DESEMPLEO_PCT", "CV_SINTETICO_PCT": "CV_PCT"}
)[["DOMINIO"] + DOMINIO_COLS + ["TASA_DESEMPLEO_PCT", "CV_PCT", "TIPO"]]

df_final = construir_tabla_final(tabla_entrenamiento, tabla_sintetica)

print(f"\nTabla final consolidada: {len(df_final)} dominios "
      f"({(df_final['TIPO']=='EBLUP').sum()} EBLUP + {(df_final['TIPO']=='SINTETICO').sum()} sintéticos)")
display(df_final.drop(columns=["DOMINIO"]))

spark_df_final = spark.createDataFrame(df_final.drop(columns=["DOMINIO"]))
spark_df_final.write.mode("overwrite").option("mergeSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_ESTIMACIONES_FINALES
)
