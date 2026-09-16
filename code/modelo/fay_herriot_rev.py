# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Modelo Fay-Herriot sobre el conjunto de covariables revisado
# MAGIC
# MAGIC Versión revisada de `fay_herriot`. El notebook original permanece sin cambios; este
# MAGIC escribe en tablas con sufijo `_rev`.
# MAGIC
# MAGIC **La lógica del modelo no se toca.** Se reutilizan sin modificación
# MAGIC `shared/fay_herriot.py`, `shared/modelo_area_pequena.py`, `shared/seleccion_modelo.py`,
# MAGIC `shared/diagnosticos_plot.py` y `shared/consolidacion.py`, y el criterio de selección
# MAGIC del modelo ganador sigue siendo el mismo ranking por posiciones en AIC y error
# MAGIC cuadrático medio. Solo cambian tres cosas:
# MAGIC
# MAGIC 1. **De dónde salen las covariables.** La lista fija `COVAR_SETS` se sustituye por las
# MAGIC    especificaciones mejor ordenadas por AIC que produce `eda_seleccion_covariables_rev`.
# MAGIC    Así el modelo no puede quedar desincronizado del análisis exploratorio.
# MAGIC 2. **De dónde salen los dominios objetivo.** Se usa
# MAGIC    `municipios_sin_encuesta_rev`, derivada de las fuentes por
# MAGIC    `dominios_sin_encuesta_rev`, en lugar de una tabla que ningún notebook construye y
# MAGIC    que traía solo cinco covariables ya renombradas.
# MAGIC 3. **Dónde se escriben los resultados.**
# MAGIC
# MAGIC Dominio: PER + MES + DEPARTAMENTO + MUNICIPIO.

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


def _directorio_codigo() -> str:
    """Ruta absoluta de `code/`, tanto en ejecución interactiva como en un job."""
    try:
        contexto = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
        return "/Workspace" + os.path.dirname(os.path.dirname(contexto.notebookPath().get()))
    except Exception:
        return os.path.dirname(os.getcwd())


CODE_DIR = _directorio_codigo()
for _ruta in (CODE_DIR, os.path.join(CODE_DIR, "modelo")):
    if _ruta not in sys.path:
        sys.path.insert(0, _ruta)

from shared.config_rev import *
from shared.fay_herriot import FayHerriotClasico
from shared.seleccion_modelo import tabla_diagnosticos, tabla_seleccion, elegir_ganador
from shared.diagnosticos_plot import graficar_validacion, explicacion_graficas, interpretar_validacion
from shared.consolidacion import construir_tabla_final

import warnings
warnings.filterwarnings("ignore")

# COMMAND ----------

# DBTITLE 1,1. Carga de datos
# Se carga la tabla de candidatas y no la de seleccionadas: las especificaciones que se
# comparan más abajo incluyen covariables que no forman parte del conjunto ganador.
df = spark.table(TBL_COVARIABLES_CANDIDATAS_REV).toPandas()

df["DOMINIO"] = (
    df["PER"].astype(str) + "_" +
    df["MES"].astype(str) + "_" +
    df["DEPARTAMENTO"] + "_" +
    df["MUNICIPIO"]
)

print(f"Dominios (municipios): {len(df)}")
print(f"Columnas disponibles:  {df.columns.tolist()}\n")

# COMMAND ----------

# DBTITLE 1,2. Especificaciones a comparar (desde la búsqueda por AIC del EDA)
# Las variantes provienen de la búsqueda exhaustiva de la etapa de selección, no de una
# lista escrita a mano: se toman las N_VARIANTES especificaciones de menor AIC. Cualquier
# cambio en el análisis exploratorio se refleja aquí automáticamente.
busqueda = spark.table(TBL_BUSQUEDA_AIC_REV).toPandas().sort_values("AIC")

# La primera variante es siempre el conjunto que eligió el análisis exploratorio, de modo que
# la comparación quede anclada en él y no en una especificación distinta. Las demás son las
# siguientes por AIC, empezando por las que el criterio considera equivalentes.
# El conjunto del EDA se reconoce como las columnas de su tabla que aparecen como covariables
# en la búsqueda; el resto de columnas son metadatos de identificación y de estimación directa.
alias_covariables = {
    alias.strip()
    for fila in busqueda["Covariables"]
    for alias in fila.split(" + ")
}
covars_eda = [c for c in spark.table(TBL_COVARIABLES_SELECCIONADAS_REV).columns
              if c in alias_covariables]

if not covars_eda:
    raise ValueError(
        f"No se reconoció ninguna covariable en {TBL_COVARIABLES_SELECCIONADAS_REV}. "
        f"Volver a ejecutar eda_seleccion_covariables_rev."
    )

nombres_covars = [covars_eda]
for fila in busqueda["Covariables"]:
    candidata = [alias.strip() for alias in fila.split(" + ")]
    if set(candidata) != set(covars_eda) and candidata not in nombres_covars:
        nombres_covars.append(candidata)
    if len(nombres_covars) == N_VARIANTES:
        break

faltantes = sorted({c for covars in nombres_covars for c in covars} - set(df.columns))
if faltantes:
    raise ValueError(
        f"Las covariables {faltantes} figuran en {TBL_BUSQUEDA_AIC_REV} pero no en "
        f"{TBL_COVARIABLES_SELECCIONADAS_REV}. Volver a ejecutar "
        f"eda_seleccion_covariables_rev para que ambas tablas queden alineadas."
    )

print(f"Especificaciones a comparar ({len(nombres_covars)}):")
for i, covars in enumerate(nombres_covars, 1):
    print(f"  M{i}: {' + '.join(covars)}")

# COMMAND ----------

# DBTITLE 1,3. Ajuste de todos los modelos
print(f"\nAjustando {len(nombres_covars)} modelo(s)...\n")
modelos = [FayHerriotClasico(covars, df, Y_COL, SE_COL) for covars in nombres_covars]
for modelo in modelos:
    modelo.ajustar()
    modelo.resultados = modelo.tabla_resultados(metadata_cols=DOMINIO_COLS)

# COMMAND ----------

# DBTITLE 1,4. Tablas EBLUP por dominio (por modelo)
eblup_display_cols = ["MUNICIPIO", Y_COL, "EBLUP", "CV_PORCENTAJE", "CV_EBLUP_PCT",
                       "GAMMA_SHRINKAGE", "MEJORA_CV_PCT"]
for i, (modelo, covars) in enumerate(zip(modelos, nombres_covars), 1):
    print("=" * 65)
    print(f"MODELO {i}: {' + '.join(covars)} — RESULTADOS EBLUP POR DOMINIO")
    print("=" * 65)
    display(modelo.resultados[eblup_display_cols])

# COMMAND ----------

# DBTITLE 1,5. Gráficas de validación (por modelo)
for i, (modelo, covars) in enumerate(zip(modelos, nombres_covars), 1):
    etiqueta = f"Modelo {i}: {' + '.join(covars)}"
    print("=" * 65)
    print(f"{etiqueta} — GRÁFICAS DE VALIDACIÓN")
    print("=" * 65)
    print(explicacion_graficas())

    # Las cuatro figuras que devuelve `graficar_validacion()` llegan en orden fijo. Se guardan
    # con el prefijo `fh_rev_` para que el capitulo de resultados referencie las de esta
    # version y no las del procedimiento anterior, que corresponden a otras covariables.
    figuras = graficar_validacion(modelo, etiqueta)
    for fig, tipo in zip(figuras, NOMBRES_FIGURAS_VALIDACION):
        display(fig)
        if VOLUMEN_FIGURAS:
            os.makedirs(VOLUMEN_FIGURAS, exist_ok=True)
            ruta = os.path.join(VOLUMEN_FIGURAS, f"fh_rev_m{i}_{tipo}.png")
            fig.savefig(ruta, dpi=200, bbox_inches="tight")
            print(f"  figura guardada: {ruta}")
        plt.close(fig)

    print(interpretar_validacion(modelo))
    print()

# COMMAND ----------

# DBTITLE 1,6. Diagnósticos por modelo
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

# DBTITLE 1,7. Selección de modelo (solo cuando hay más de un subconjunto)
if len(modelos) > 1:
    print("=" * 65)
    print("TABLA 1 — DIAGNÓSTICOS POR MODELO")
    print("=" * 65)
    df_diag_variantes = tabla_diagnosticos(modelos, nombres_covars)

    # La metodologia reporta el efecto suavizador para las cuatro variantes, no solo para la
    # elegida: la correlacion entre la estimacion directa y la correccion que el modelo le
    # aplica mide cuanto de esa correccion responde al nivel del dominio. Se anade aqui, y no
    # en `tabla_diagnosticos()`, para no alterar el modulo que comparte el notebook original.
    correlaciones = [stats.pearsonr(m.Y, m.Y - m.eblup) for m in modelos]
    df_diag_variantes["Corr_suavizador"] = [round(float(c[0]), 4) for c in correlaciones]
    df_diag_variantes["Corr_suavizador_pval"] = [round(float(c[1]), 4) for c in correlaciones]

    display(df_diag_variantes)
    print("  SW_pval: p-valor Shapiro-Wilk (>0.05 -> normalidad)")
    print("  Wilcoxon_pval: p-valor test Di>MSE_EBLUP (<0.05 -> reducción significativa)")
    print("  Pct_dom_mejoran: % dominios con MSE_EBLUP < Di")
    print("  Ratio_MSE_medio: Di/MSE_EBLUP medio (>1 indica ganancia de eficiencia)")

    print("\n" + "=" * 65)
    print("TABLA 2 — SELECCIÓN DE MODELO (AIC / MSE medio)")
    print("=" * 65)
    df_sel_modelo = tabla_seleccion(modelos, nombres_covars)
    display(df_sel_modelo)
    print("  Ranking por suma de posiciones en AIC + MSE_medio")
    print("  Delta_AIC: < 2 equivalentes · 2-7 moderado · > 10 sustancial")

    (spark.createDataFrame(df_diag_variantes).write.mode("overwrite")
     .option("overwriteSchema", "true").saveAsTable(TBL_FH_DIAGNOSTICOS_VARIANTES_REV))
    print(f"Tabla escrita: {TBL_FH_DIAGNOSTICOS_VARIANTES_REV}")

# COMMAND ----------

# DBTITLE 1,8. Exportar resultados del modelo ganador
modelo_ganador = elegir_ganador(modelos, nombres_covars) if len(modelos) > 1 else modelos[0]

# La metodología establece que, ante variantes equivalentes, el principio de parsimonia
# impone elegir la de menos covariables. `elegir_ganador()` ordena por la suma de posiciones
# en AIC y error cuadrático medio, pero no aplica ese desempate, de modo que puede devolver
# una especificación más grande que otra estadísticamente indistinguible. Aquí se aplica la
# regla documentada sobre el conjunto de variantes equivalentes.
if len(modelos) > 1:
    mejor_aic = min(m.aic for m in modelos)
    equivalentes = [m for m in modelos if m.aic - mejor_aic <= DELTA_AIC_EQUIVALENTE]
    orden_compuesto = {id(m): i for i, m in enumerate(
        sorted(modelos, key=lambda m: (m.aic, m.mse.mean()))
    )}
    mas_parsimonioso = min(equivalentes,
                           key=lambda m: (len(m.covars), orden_compuesto[id(m)]))
    if mas_parsimonioso is not modelo_ganador:
        print(f"\nVariantes equivalentes (diferencia de AIC <= {DELTA_AIC_EQUIVALENTE}): "
              f"{len(equivalentes)}")
        print(f"  ganador por ranking compuesto: {' + '.join(modelo_ganador.covars)} "
              f"({len(modelo_ganador.covars)} covariables)")
        print(f"  elegido por parsimonia:        {' + '.join(mas_parsimonioso.covars)} "
              f"({len(mas_parsimonioso.covars)} covariables)")
        modelo_ganador = mas_parsimonioso

if set(modelo_ganador.covars) != set(covars_eda):
    print("\nAVISO: el modelo ganador por AIC y error cuadrático medio no coincide con el")
    print("conjunto elegido por el análisis exploratorio. Ambas cifras deben reportarse y la")
    print("discrepancia explicarse en el documento.")
    print(f"  conjunto del EDA: {' + '.join(covars_eda)}")
    print(f"  modelo ganador:   {' + '.join(modelo_ganador.covars)}")

# La tabla de selección se persiste una vez conocida la variante elegida, con una columna que
# la identifica: la marca de `tabla_seleccion()` señala el primer puesto del ranking compuesto,
# que no coincide con la elegida cuando interviene el desempate por parsimonia.
if len(modelos) > 1:
    df_sel_modelo = df_sel_modelo.copy()
    covars_ganador_txt = " + ".join(modelo_ganador.covars)
    df_sel_modelo["Elegida"] = [
        "sí" if fila == covars_ganador_txt else "" for fila in df_sel_modelo["Covariables"]
    ]
    (spark.createDataFrame(df_sel_modelo).write.mode("overwrite")
     .option("overwriteSchema", "true").saveAsTable(TBL_FH_SELECCION_MODELO_REV))
    print(f"Tabla escrita: {TBL_FH_SELECCION_MODELO_REV}")

# Coeficientes del modelo ganador, para el capítulo de resultados.
df_coef_ganador = pd.DataFrame({
    "Parametro": ["Intercepto"] + list(modelo_ganador.covars),
    "Coeficiente": modelo_ganador.beta_hat.round(4),
    "Error_estandar": modelo_ganador.se_beta.round(4),
    "z": modelo_ganador.t_stats.round(3),
    "p_valor": modelo_ganador.p_vals.round(4),
})
df_coef_ganador["Modelo"] = " + ".join(modelo_ganador.covars)
df_coef_ganador["A_hat"] = round(float(modelo_ganador.A_hat), 6)
df_coef_ganador["R2"] = round(float(modelo_ganador.r2), 4)
df_coef_ganador["AIC"] = round(float(modelo_ganador.aic), 3)
(spark.createDataFrame(df_coef_ganador).write.mode("overwrite")
 .option("overwriteSchema", "true").saveAsTable(TBL_FH_COEFICIENTES_REV))
print(f"Tabla escrita: {TBL_FH_COEFICIENTES_REV}")

spark_df = spark.createDataFrame(modelo_ganador.resultados)
spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_RESULTADOS_REV
)

# COMMAND ----------

# DBTITLE 1,9. Predicción sintética para dominios sin estimación directa
# Para municipios donde NO existe estimación directa (Y ni Di), el EBLUP no puede
# calcularse: el predictor óptimo es el sintético ŷ_d = X_d'β̂ del modelo ganador,
# sin contracción (γ=0) porque no hay varianza de muestreo.
covars_ganador = modelo_ganador.covars
beta_ganador   = modelo_ganador.beta_hat

# La tabla de dominios objetivo conserva los códigos de indicador; se renombran a los
# alias del modelo usando el mismo mapa que produjo la etapa de selección.
mapa_alias = {
    fila["Codigo"]: fila["Alias"]
    for fila in spark.table("tesis.preprocesamiento.trazabilidad_covariables_rev")
    .select("Codigo", "Alias").collect()
}
alias_a_codigo = {alias: codigo for codigo, alias in mapa_alias.items()}

df_new = spark.table(TBL_MUNICIPIOS_SIN_ENCUESTA_REV).toPandas()
df_new = df_new.rename(columns={
    alias_a_codigo[alias]: alias
    for alias in covars_ganador if alias_a_codigo.get(alias) in df_new.columns
})

faltantes = [c for c in covars_ganador if c not in df_new.columns]
if faltantes:
    raise ValueError(f"Faltan columnas en los datos nuevos: {faltantes}")

sin_dato = df_new[covars_ganador].isna().any(axis=1)
if sin_dato.any():
    municipios = df_new.loc[sin_dato, "MUNICIPIO"].tolist()
    raise ValueError(
        f"{int(sin_dato.sum())} municipios objetivo no tienen valor para alguna covariable "
        f"del modelo ganador y no admiten predicción sintética: {municipios}. "
        f"Revisar la completitud reportada por dominios_sin_encuesta_rev."
    )

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
spark_df_pred.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_PREDICCION_SINTETICA_REV
)

# COMMAND ----------

# DBTITLE 1,10. Tabla final consolidada (EBLUP + sintético)
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
spark_df_final.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_ESTIMACIONES_FINALES_REV
)
