# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Modelo Fay-Herriot sobre el conjunto de covariables revisado
# MAGIC
# MAGIC Versión revisada de `fay_herriot`. El notebook original permanece sin cambios; este
# MAGIC escribe en tablas con sufijo `_rev`.
# MAGIC
# MAGIC **La lógica del modelo no se toca.** Se reutilizan sin modificación
# MAGIC `shared/fay_herriot.py`, `shared/modelo_area_pequena.py`, `shared/diagnosticos_plot.py`
# MAGIC y `shared/consolidacion.py`. Es un Fay-Herriot **clásico**: efectos aleatorios
# MAGIC independientes por dominio, sin componente espacial, de modo que no se calcula ningún
# MAGIC índice de autocorrelación espacial. Cambian cuatro cosas:
# MAGIC
# MAGIC 1. **De dónde salen las covariables.** El conjunto lo elige
# MAGIC    `eda_seleccion_covariables_rev` con una ficha de decisión cualitativa, y aquí se
# MAGIC    compara ese conjunto con sus **variantes dejando una covariable fuera**. La
# MAGIC    comparación responde a si cada covariable aporta, y el modelo no puede quedar
# MAGIC    desincronizado del análisis exploratorio.
# MAGIC 2. **Cómo se elige el ganador.** Al ranking original por posiciones en AIC y error
# MAGIC    cuadrático medio se añade la **distancia de Cook máxima**: con 23 dominios una
# MAGIC    especificación puede ajustar bien porque un solo territorio sostiene sus
# MAGIC    coeficientes, y eso debe penalizarse. Entre variantes equivalentes por AIC se elige
# MAGIC    la más parsimoniosa (`shared/seleccion_modelo_rev.py`).
# MAGIC 3. **De dónde salen los dominios objetivo.** Se usa
# MAGIC    `municipios_sin_encuesta_rev`, derivada de las fuentes por
# MAGIC    `dominios_sin_encuesta_rev`, en lugar de una tabla que ningún notebook construye.
# MAGIC 4. **Dónde se escriben los resultados.**
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
        return "/Workspace" + os.path.dirname(
            os.path.dirname(contexto.notebookPath().get())
        )
    except Exception:
        return os.path.dirname(os.getcwd())


CODE_DIR = _directorio_codigo()
for _ruta in (CODE_DIR, os.path.join(CODE_DIR, "modelo")):
    if _ruta not in sys.path:
        sys.path.insert(0, _ruta)

from shared.config_rev import *
from shared.fay_herriot import FayHerriotClasico
from shared.seleccion_modelo import tabla_diagnosticos
from shared.seleccion_modelo_rev import (
    variantes_dejar_una_fuera,
    distancia_cook,
    tabla_cook,
    tabla_seleccion_rev,
    elegir_ganador_rev,
    figura_cook,
    interpretar_cook,
)
from shared.diagnosticos_plot import (
    graficar_validacion,
    explicacion_graficas,
    interpretar_validacion,
)
from shared.consolidacion import construir_tabla_final

import warnings

warnings.filterwarnings("ignore")

# COMMAND ----------

# DBTITLE 1,1. Carga de datos
# La tabla de seleccionadas conserva los alias del catálogo; el mapa código → alias de la
# trazabilidad sirve para reconocer qué columnas son covariables y, más adelante, para
# renombrar la tabla de dominios objetivo, que conserva los códigos de indicador.
mapa_alias = {
    fila["Codigo"]: fila["Alias"]
    for fila in spark.table(TBL_TRAZABILIDAD_REV).select("Codigo", "Alias").collect()
}
alias_a_codigo = {alias: codigo for codigo, alias in mapa_alias.items()}

df = spark.table(TBL_COVARIABLES_SELECCIONADAS_REV).toPandas()

df["DOMINIO"] = (
    df["PER"].astype(str)
    + "_"
    + df["MES"].astype(str)
    + "_"
    + df["DEPARTAMENTO"]
    + "_"
    + df["MUNICIPIO"]
)

print(f"Dominios (municipios): {len(df)}")
print(f"Columnas disponibles:  {df.columns.tolist()}\n")

# COMMAND ----------

# DBTITLE 1,2. Especificaciones a comparar (conjunto del EDA y variantes dejar-una-fuera)
covars_eda = [c for c in df.columns if c in alias_a_codigo]

if not covars_eda:
    raise ValueError(
        f"No se reconoció ninguna covariable en {TBL_COVARIABLES_SELECCIONADAS_REV}. "
        f"Volver a ejecutar eda_seleccion_covariables_rev."
    )

nombres_covars = variantes_dejar_una_fuera(covars_eda)

print(f"Conjunto elegido por el análisis exploratorio: {' + '.join(covars_eda)}")
print(f"Especificaciones a comparar ({len(nombres_covars)}):")
for i, covars in enumerate(nombres_covars, 1):
    excluida = set(covars_eda) - set(covars)
    etiqueta = f"(sin {next(iter(excluida))})" if excluida else "(conjunto completo)"
    print(f"  M{i}: {' + '.join(covars)}  {etiqueta}")

# COMMAND ----------

# DBTITLE 1,3. Ajuste de todos los modelos
print(f"\nAjustando {len(nombres_covars)} modelo(s)...\n")
modelos = [FayHerriotClasico(covars, df, Y_COL, SE_COL) for covars in nombres_covars]
for modelo in modelos:
    modelo.ajustar()
    modelo.resultados = modelo.tabla_resultados(metadata_cols=DOMINIO_COLS)

municipios = df["MUNICIPIO"].values

# COMMAND ----------

# DBTITLE 1,4. Tablas EBLUP por dominio (por modelo)
eblup_display_cols = [
    "MUNICIPIO",
    Y_COL,
    "EBLUP",
    "CV_PORCENTAJE",
    "CV_EBLUP_PCT",
    "GAMMA_SHRINKAGE",
    "MEJORA_CV_PCT",
]
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
    # con el prefijo `fh_rev_` para que el capítulo de resultados referencie las de esta
    # versión y no las del procedimiento anterior, que corresponden a otras covariables.
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

# MAGIC %md
# MAGIC ## Influencia por dominio: distancia de Cook
# MAGIC
# MAGIC **Cómo leer la figura.** Un panel por especificación; cada barra es un dominio y su
# MAGIC altura es la distancia de Cook en el ajuste por mínimos cuadrados generalizados del
# MAGIC modelo, es decir, cuánto cambiarían los coeficientes si ese dominio no estuviera. La
# MAGIC línea discontinua es el umbral convencional 4/n y las barras rojas lo superan. Lo que
# MAGIC interesa comparar entre paneles es si al añadir o quitar una covariable aparece un
# MAGIC dominio que pasa a sostener el ajuste por sí solo: esa especificación, aunque tenga
# MAGIC menor AIC, depende de un único territorio y el ranking compuesto la penaliza.

# COMMAND ----------

# DBTITLE 1,Figura: distancia de Cook por dominio y especificación
fig = figura_cook(modelos, nombres_covars, municipios)
display(fig)
if VOLUMEN_FIGURAS:
    os.makedirs(VOLUMEN_FIGURAS, exist_ok=True)
    ruta = os.path.join(VOLUMEN_FIGURAS, f"fh_rev_{NOMBRE_FIGURA_COOK}.png")
    fig.savefig(ruta, dpi=200, bbox_inches="tight")
    print(f"  figura guardada: {ruta}")
plt.close(fig)
print(interpretar_cook(modelos, nombres_covars, municipios))

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
    coef_df = pd.DataFrame(
        {
            "Parametro": param_names,
            "Coef": modelo.beta_hat.round(4),
            "SE": modelo.se_beta.round(4),
            "z": modelo.t_stats.round(3),
            "p_valor": modelo.p_vals.round(4),
        }
    )
    coef_df["Signif"] = [
        "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.10 else ""
        for pv in modelo.p_vals
    ]
    display(coef_df)
    print("Signif: *** p<0.01  ** p<0.05  * p<0.10")

    print("\nDIAGNÓSTICOS:")
    print(f"  R² predictor sintético:       {modelo.r2:.4f}")
    print(
        f"  Media residuos estand.:       {modelo.residuals.mean():.4f}  (esperado ≈ 0)"
    )
    print(
        f"  Desv. std residuos estand.:   {modelo.residuals.std():.4f}  (esperado ≈ 1)"
    )
    sw_ok = modelo.sw_pval > 0.05
    print(
        f"  Shapiro-Wilk: W={modelo.sw_stat:.4f}, p={modelo.sw_pval:.4f}  "
        + ("✓ normalidad" if sw_ok else "✗ revisar normalidad")
    )
    print(
        f"  Reducción media del CV:       {modelo.resultados['MEJORA_CV_PCT'].mean():.2f} pp"
    )
    print(f"  Shrinkage promedio (γ̄):       {modelo.gamma_i.mean():.4f}")

    cook = distancia_cook(modelo)
    umbral_cook = 4 / modelo.n
    influyentes = np.where(cook > umbral_cook)[0]
    print(
        f"  Distancia de Cook máxima:     {cook.max():.4f} en {municipios[int(np.argmax(cook))]}  "
        f"(umbral 4/n = {umbral_cook:.4f}; {len(influyentes)} dominio(s) lo superan"
        + (f": {', '.join(municipios[influyentes])})" if len(influyentes) else ")")
    )

    validacion = modelo.validar_mse_directo()
    print("\nVALIDACIÓN MSE EBLUP vs VARIANZA DIRECTA:")
    print(
        f"  Dominios con MSE_EBLUP < Di: {validacion['dominios_mejoran']*100:.1f}%  "
        + (
            "✓ mejora generalizada"
            if validacion["dominios_mejoran"] >= 0.9
            else (
                "~ mejora parcial"
                if validacion["dominios_mejoran"] >= 0.5
                else "✗ sin mejora clara"
            )
        )
    )
    print(f"  Reducción media del MSE:      {validacion['pct_mejora_mse'].mean():.2f}%")
    print(
        f"  Ratio Di/MSE medio:           {validacion['mse_ratio'].mean():.4f}  (>1 indica ganancia)"
    )
    print(f"  Ratio Di/MSE mediana:         {np.median(validacion['mse_ratio']):.4f}")
    wil_ok = validacion["wil_pval"] < 0.05
    print(
        f"  Wilcoxon (Di > MSE_EBLUP):   W={validacion['wil_stat']:.1f}, p={validacion['wil_pval']:.4f}  "
        + ("✓ reducción significativa" if wil_ok else "✗ no significativa")
    )

    print("\n  Detalle por dominio (Di vs MSE_EBLUP):")
    detail_cols = [
        "MUNICIPIO",
        "VARIANZA_DIRECTA",
        "MSE_EBLUP",
        "RATIO_MSE",
        "MEJORA_MSE_PCT",
        "MEJORA_MSE",
    ]
    display(modelo.resultados[detail_cols])
    print()

# COMMAND ----------

# DBTITLE 1,7. Selección de modelo (solo cuando hay más de una especificación)
if len(modelos) > 1:
    print("=" * 65)
    print("TABLA 1 — DIAGNÓSTICOS POR MODELO")
    print("=" * 65)
    df_diag_variantes = tabla_diagnosticos(modelos, nombres_covars)

    # La metodología reporta el efecto suavizador para todas las variantes, no solo para la
    # elegida: la correlación entre la estimación directa y la corrección que el modelo le
    # aplica mide cuánto de esa corrección responde al nivel del dominio. Se añade aquí, y no
    # en `tabla_diagnosticos()`, para no alterar el módulo que comparte el notebook original.
    correlaciones = [stats.pearsonr(m.Y, m.Y - m.eblup) for m in modelos]
    df_diag_variantes["Corr_suavizador"] = [
        round(float(c[0]), 4) for c in correlaciones
    ]
    df_diag_variantes["Corr_suavizador_pval"] = [
        round(float(c[1]), 4) for c in correlaciones
    ]

    df_cook_variantes = tabla_cook(modelos, nombres_covars, municipios)
    df_diag_variantes = df_diag_variantes.merge(
        df_cook_variantes[["Modelo", "Cook_max", "N_influyentes"]],
        on="Modelo",
        how="left",
    )

    display(df_diag_variantes)
    print("  SW_pval: p-valor Shapiro-Wilk (>0.05 -> normalidad)")
    print(
        "  Wilcoxon_pval: p-valor test Di>MSE_EBLUP (<0.05 -> reducción significativa)"
    )
    print("  Pct_dom_mejoran: % dominios con MSE_EBLUP < Di")
    print("  Ratio_MSE_medio: Di/MSE_EBLUP medio (>1 indica ganancia de eficiencia)")
    print(
        "  Cook_max / N_influyentes: distancia de Cook máxima y dominios que superan 4/n"
    )

    print("\n" + "=" * 65)
    print("TABLA 2 — SELECCIÓN DE MODELO (AIC / MSE medio / Cook máxima)")
    print("=" * 65)
    df_sel_modelo = tabla_seleccion_rev(modelos, nombres_covars)
    display(df_sel_modelo)
    print(
        "  Puntaje: suma de posiciones en AIC + MSE_medio + Cook_max (menor es mejor)"
    )
    print("  Delta_AIC: < 2 equivalentes · 2-7 moderado · > 10 sustancial")

    (
        spark.createDataFrame(df_diag_variantes)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(TBL_FH_DIAGNOSTICOS_VARIANTES_REV)
    )
    print(f"Tabla escrita: {TBL_FH_DIAGNOSTICOS_VARIANTES_REV}")

    (
        spark.createDataFrame(df_cook_variantes)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(TBL_FH_COOK_REV)
    )
    print(f"Tabla escrita: {TBL_FH_COOK_REV}")

# COMMAND ----------

# DBTITLE 1,8. Exportar resultados del modelo ganador
# `elegir_ganador_rev()` ordena por la suma de posiciones en AIC, error cuadrático medio y
# distancia de Cook máxima y, entre las variantes equivalentes por AIC, aplica el principio
# de parsimonia que establece la metodología: elegir la de menos covariables.
modelo_ganador = (
    elegir_ganador_rev(modelos, nombres_covars, delta_aic=DELTA_AIC_EQUIVALENTE)
    if len(modelos) > 1
    else modelos[0]
)

if set(modelo_ganador.covars) != set(covars_eda):
    print(
        "\nAVISO: el modelo ganador no coincide con el conjunto completo elegido por el análisis"
    )
    print(
        "exploratorio: alguna covariable no aporta ajuste suficiente para justificar su inclusión."
    )
    print("Ambas cifras deben reportarse y la diferencia explicarse en el documento.")
    print(f"  conjunto del EDA: {' + '.join(covars_eda)}")
    print(f"  modelo ganador:   {' + '.join(modelo_ganador.covars)}")

# La tabla de selección se persiste una vez conocida la variante elegida, con una columna que
# la identifica: `Rank == 1` señala el primer puesto del ranking compuesto, que no coincide
# con la elegida cuando interviene el desempate por parsimonia.
if len(modelos) > 1:
    df_sel_modelo = df_sel_modelo.copy()
    covars_ganador_txt = " + ".join(modelo_ganador.covars)
    df_sel_modelo["Elegida"] = [
        "sí" if fila == covars_ganador_txt else ""
        for fila in df_sel_modelo["Covariables"]
    ]
    (
        spark.createDataFrame(df_sel_modelo)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(TBL_FH_SELECCION_MODELO_REV)
    )
    print(f"Tabla escrita: {TBL_FH_SELECCION_MODELO_REV}")

# Coeficientes del modelo ganador, para el capítulo de resultados.
cook_ganador = distancia_cook(modelo_ganador)
df_coef_ganador = pd.DataFrame(
    {
        "Parametro": ["Intercepto"] + list(modelo_ganador.covars),
        "Coeficiente": modelo_ganador.beta_hat.round(4),
        "Error_estandar": modelo_ganador.se_beta.round(4),
        "z": modelo_ganador.t_stats.round(3),
        "p_valor": modelo_ganador.p_vals.round(4),
    }
)
df_coef_ganador["Modelo"] = " + ".join(modelo_ganador.covars)
df_coef_ganador["A_hat"] = round(float(modelo_ganador.A_hat), 6)
df_coef_ganador["R2"] = round(float(modelo_ganador.r2), 4)
df_coef_ganador["AIC"] = round(float(modelo_ganador.aic), 3)
df_coef_ganador["Cook_max"] = round(float(cook_ganador.max()), 4)
(
    spark.createDataFrame(df_coef_ganador)
    .write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TBL_FH_COEFICIENTES_REV)
)
print(f"Tabla escrita: {TBL_FH_COEFICIENTES_REV}")

resultados_ganador = modelo_ganador.resultados.copy()
resultados_ganador["COOK_D"] = cook_ganador.round(4)
spark_df = spark.createDataFrame(resultados_ganador)
spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_RESULTADOS_REV
)

# COMMAND ----------

# DBTITLE 1,9. Predicción sintética para dominios sin estimación directa
# Para municipios donde NO existe estimación directa (Y ni Di), el EBLUP no puede
# calcularse: el predictor óptimo es el sintético ŷ_d = X_d'β̂ del modelo ganador,
# sin contracción (γ=0) porque no hay varianza de muestreo.
covars_ganador = modelo_ganador.covars
beta_ganador = modelo_ganador.beta_hat

# La tabla de dominios objetivo conserva los códigos de indicador; se renombran a los
# alias del modelo usando el mismo mapa que produjo la etapa de selección.
df_new = spark.table(TBL_MUNICIPIOS_SIN_ENCUESTA_REV).toPandas()
df_new = df_new.rename(
    columns={
        alias_a_codigo[alias]: alias
        for alias in covars_ganador
        if alias_a_codigo.get(alias) in df_new.columns
    }
)

faltantes = [c for c in covars_ganador if c not in df_new.columns]
if faltantes:
    raise ValueError(f"Faltan columnas en los datos nuevos: {faltantes}")

sin_dato = df_new[covars_ganador].isna().any(axis=1)
if sin_dato.any():
    municipios_sin_dato = df_new.loc[sin_dato, "MUNICIPIO"].tolist()
    raise ValueError(
        f"{int(sin_dato.sum())} municipios objetivo no tienen valor para alguna covariable "
        f"del modelo ganador y no admiten predicción sintética: {municipios_sin_dato}. "
        f"Revisar la completitud reportada por dominios_sin_encuesta_rev."
    )

df_new["DOMINIO"] = (
    df_new["PER"].astype(str)
    + "_"
    + df_new["MES"].astype(str)
    + "_"
    + df_new["DEPARTAMENTO"]
    + "_"
    + df_new["MUNICIPIO"]
)

X_new = np.column_stack(
    [np.ones(len(df_new))] + [df_new[c].values for c in covars_ganador]
)
y_sintetico = X_new @ beta_ganador

# Incertidumbre: solo el componente de varianza del predictor sintético, x_d'Cov(β̂)x_d,
# más A_hat (efecto aleatorio no observado en un dominio sin muestra).
var_beta = np.array(
    [X_new[i] @ modelo_ganador.cov_beta @ X_new[i] for i in range(len(df_new))]
)
var_sintetico = var_beta + modelo_ganador.A_hat
rmse_sintetico = np.sqrt(var_sintetico)
cv_sintetico = 100 * rmse_sintetico / np.abs(y_sintetico)

df_pred = df_new[["DOMINIO"] + DOMINIO_COLS].copy()
df_pred["PRED_SINTETICO"] = y_sintetico.round(4)
df_pred["RMSE_SINTETICO"] = rmse_sintetico.round(4)
df_pred["CV_SINTETICO_PCT"] = cv_sintetico.round(2)
df_pred["TIPO"] = "SINTETICO"

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

print(
    f"\nTabla final consolidada: {len(df_final)} dominios "
    f"({(df_final['TIPO']=='EBLUP').sum()} EBLUP + {(df_final['TIPO']=='SINTETICO').sum()} sintéticos)"
)
display(df_final.drop(columns=["DOMINIO"]))

spark_df_final = spark.createDataFrame(df_final.drop(columns=["DOMINIO"]))
spark_df_final.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_ESTIMACIONES_FINALES_REV
)
