# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Modelo Fay-Herriot
# MAGIC
# MAGIC Las decisiones metodológicas se apoyan en Morales et al. (2021), *A Course on Small
# MAGIC Area Estimation and Mixed Models*.
# MAGIC
# MAGIC Es un Fay-Herriot **clásico**: efectos aleatorios independientes por dominio, sin
# MAGIC componente espacial. Â se estima por REML, β̂ por mínimos cuadrados generalizados y
# MAGIC el AIC con la verosimilitud ML (`shared/fay_herriot.py`).
# MAGIC
# MAGIC 1. **MSE del EBLUP.** Estimador de Prasad-Rao para REML del libro (p. 440), con
# MAGIC    `g3 = D²/(D+Â)³ · avar(Â)`.
# MAGIC 2. **De dónde salen las covariables.** El conjunto lo elige
# MAGIC    `eda_seleccion_covariables_rev`, y aquí se compara con sus **variantes dejando una
# MAGIC    covariable fuera**, para responder si cada covariable aporta.
# MAGIC 3. **Cómo se elige el ganador.** El modelo se usa para predecir municipios sin
# MAGIC    encuesta, y para ese objetivo el libro (p. 453) desaconseja sobreparametrizar y
# MAGIC    recomienda que todas las covariables sean significativas (p < 0.05). Solo compiten
# MAGIC    las variantes que lo cumplen; entre ellas gana la de menor AIC y, entre las
# MAGIC    equivalentes (ΔAIC ≤ 2), la de menos covariables. El MSE del EBLUP y la distancia
# MAGIC    de Cook se muestran después como diagnósticos del modelo elegido: ganancia de
# MAGIC    precisión y robustez.
# MAGIC 4. **Avisos.** Encuesta sin peso en el EBLUP (Â ≈ 0), tasas fuera de [0, 100] y
# MAGIC    municipios cuya predicción sintética es una extrapolación.
# MAGIC 5. **Dominios objetivo.** Municipios de `municipios_sin_encuesta_rev`, que reciben la
# MAGIC    predicción sintética del modelo ganador.
# MAGIC
# MAGIC Dominio: PER + MES + código DIVIPOLA del municipio. La tabla final toma los nombres
# MAGIC de departamento y municipio de `dim_divipola` por código.

# COMMAND ----------

# DBTITLE 1,Nota sobre las varianzas de muestreo
# MAGIC %md
# MAGIC ## Nota sobre las varianzas de muestreo
# MAGIC
# MAGIC El modelo Fay-Herriot trata las varianzas de muestreo σ²_d de las estimaciones directas
# MAGIC como **conocidas**. El libro (Morales et al., 2021, p. 427) da dos maneras de
# MAGIC fijarlas: (a) tomar la varianza estimada con los microdatos de la encuesta y tratarla
# MAGIC como constante conocida, o (b) suavizarla con una función de varianza generalizada
# MAGIC (GVF). Aquí se usa la alternativa (a): σ²_d es la varianza **bootstrap** de la
# MAGIC estimación directa (`estimacion_directa`), sin suavizar.
# MAGIC
# MAGIC Limitación: el bootstrap simple no incorpora el diseño muestral de la GEIH (estratos,
# MAGIC conglomerados), cuyas variables no están disponibles. Si subestima σ²_d, el peso γ_d de
# MAGIC la estimación directa en el EBLUP queda algo sobrestimado.

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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
for _ruta in (CODE_DIR, os.path.join(CODE_DIR, "modelo")):
    if _ruta not in sys.path:
        sys.path.insert(0, _ruta)

from shared.config import *
from shared.fay_herriot import FayHerriotClasico
from shared.seleccion_modelo import (
    variantes_dejar_una_fuera,
    distancia_cook,
    tabla_diagnosticos,
    tabla_cook,
    tabla_seleccion,
    elegir_ganador,
    sensibilidad_cook,
    figura_cook,
    interpretar_cook,
)
from shared.diagnosticos import (
    graficar_validacion,
    explicacion_graficas,
    interpretar_validacion,
    figura_cv_directo_vs_eblup,
    interpretar_cv,
    aviso_encuesta_sin_peso,
    marca_fuera_de_rango,
    marca_extrapolacion,
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
    for fila in spark.table(TBL_TRAZABILIDAD).select("Codigo", "Alias").collect()
}
alias_a_codigo = {alias: codigo for codigo, alias in mapa_alias.items()}

df = spark.table(TBL_COVARIABLES_SELECCIONADAS).toPandas()

# El dominio se identifica por código DIVIPOLA: los nombres cambian de formato entre fuentes.
df["DOMINIO"] = (
    df["PER"].astype(str) + "_" + df["MES"].astype(str) + "_" + df["CODIGO_MUNICIPIO"]
)

print(f"Dominios (municipios): {len(df)}")
print(f"Columnas disponibles:  {df.columns.tolist()}\n")

# COMMAND ----------

# DBTITLE 1,2. Especificaciones a comparar (conjunto del EDA y variantes dejar-una-fuera)
covars_eda = [c for c in df.columns if c in alias_a_codigo]

if not covars_eda:
    raise ValueError(
        f"No se reconoció ninguna covariable en {TBL_COVARIABLES_SELECCIONADAS}. "
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

    for fig in graficar_validacion(modelo):
        display(fig)
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
    aviso = aviso_encuesta_sin_peso(modelo, UMBRAL_GAMMA_SIN_PESO)
    if aviso:
        print(aviso)

    print(
        "\nCOEFICIENTES (prueba z con la normal asintótica de β̂, Morales et al. p. 272):"
    )
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
        f"  Desv. std residuos estand.:   {modelo.residuals.std(ddof=1):.4f}  (esperado ≈ 1)"
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

    # La comparación MSE_EBLUP frente a Di es descriptiva: g1 = γ·Di < Di por construcción,
    # de modo que el EBLUP «mejora» casi siempre; lo informativo es cuánto (p. 440).
    validacion = modelo.validar_mse_directo()
    print(
        "\nGANANCIA DE PRECISIÓN (descriptiva: MSE_EBLUP < Di es lo esperado, p. 440):"
    )
    print(f"  Dominios con MSE_EBLUP < Di: {validacion['dominios_mejoran']*100:.1f}%")
    print(f"  Reducción media del MSE:      {validacion['pct_mejora_mse'].mean():.2f}%")
    print(
        f"  Ratio Di/MSE medio:           {validacion['mse_ratio'].mean():.4f}  (>1 indica ganancia)"
    )
    print(f"  Ratio Di/MSE mediana:         {np.median(validacion['mse_ratio']):.4f}")
    print(
        f"  Wilcoxon (Di > MSE_EBLUP):   W={validacion['wil_stat']:.1f}, "
        f"p={validacion['wil_pval']:.4f}"
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
    print("TABLA 1 — DIAGNÓSTICOS POR MODELO (informativa)")
    print("=" * 65)
    df_diag_variantes = tabla_diagnosticos(modelos, nombres_covars)

    df_cook_variantes = tabla_cook(modelos, nombres_covars, municipios)
    df_diag_variantes = df_diag_variantes.merge(
        df_cook_variantes[["Modelo", "Cook_max", "N_influyentes"]],
        on="Modelo",
        how="left",
    )

    display(df_diag_variantes)
    print("  SW_pval: p-valor Shapiro-Wilk (>0.05 -> normalidad)")
    print("  Pct_dom_mejoran / Ratio_MSE_medio / Wilcoxon_pval: ganancia de precisión")
    print("    del EBLUP frente a la estimación directa (descriptiva, p. 440)")
    print(
        "  Cook_max / N_influyentes: distancia de Cook máxima y dominios que superan 4/n"
    )

    print("\n" + "=" * 65)
    print("TABLA 2 — SELECCIÓN DE MODELO (significancia + AIC + parsimonia)")
    print("=" * 65)
    df_sel_modelo = tabla_seleccion(
        modelos,
        nombres_covars,
        delta_aic=DELTA_AIC_EQUIVALENTE,
        alfa=ALFA_SIGNIFICANCIA,
    )
    display(df_sel_modelo)
    print(
        f"  Candidata: todas las covariables con p < {ALFA_SIGNIFICANCIA} "
        "(Morales et al., p. 453: no sobreparametrizar al predecir fuera de muestra)"
    )
    print(
        f"  Equivalente_AIC: ΔAIC ≤ {DELTA_AIC_EQUIVALENTE} frente a la mejor candidata; "
        "entre ellas se elige la de menos covariables"
    )
    print("  MSE_medio y Cook_max: informativas, no intervienen en la decisión")

    (
        spark.createDataFrame(df_diag_variantes)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(TBL_FH_DIAGNOSTICOS_VARIANTES)
    )
    print(f"Tabla escrita: {TBL_FH_DIAGNOSTICOS_VARIANTES}")

    (
        spark.createDataFrame(df_cook_variantes)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(TBL_FH_COOK)
    )
    print(f"Tabla escrita: {TBL_FH_COOK}")

    (
        spark.createDataFrame(df_sel_modelo)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(TBL_FH_SELECCION_MODELO)
    )
    print(f"Tabla escrita: {TBL_FH_SELECCION_MODELO}")

# COMMAND ----------

# DBTITLE 1,8. Modelo ganador
modelo_ganador = (
    elegir_ganador(
        modelos,
        nombres_covars,
        delta_aic=DELTA_AIC_EQUIVALENTE,
        alfa=ALFA_SIGNIFICANCIA,
    )
    if len(modelos) > 1
    else modelos[0]
)

if set(modelo_ganador.covars) != set(covars_eda):
    print(
        "\nAVISO: el modelo ganador no coincide con el conjunto completo elegido por el análisis"
    )
    print(
        "exploratorio: alguna covariable no es significativa o no aporta ajuste suficiente."
    )
    print("Ambas cifras deben reportarse y la diferencia explicarse en el documento.")
    print(f"  conjunto del EDA: {' + '.join(covars_eda)}")
    print(f"  modelo ganador:   {' + '.join(modelo_ganador.covars)}")

aviso = aviso_encuesta_sin_peso(modelo_ganador, UMBRAL_GAMMA_SIN_PESO)
if aviso:
    print("\n" + aviso)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ganancia de precisión del modelo elegido
# MAGIC
# MAGIC **Cómo leer la figura.** Cada columna es un dominio, ordenados de menor a mayor
# MAGIC varianza directa D_d. El punto gris es el CV de la estimación directa y el azul el CV
# MAGIC del EBLUP; el segmento entre ambos es la ganancia. Las líneas discontinuas marcan los
# MAGIC umbrales de confiabilidad (5 % y 20 %). Es la misma lectura que las comparaciones de
# MAGIC RMSE directo frente a EBLUP del libro (Fig. 17.2, Tabla 19.5): la ganancia debe ser
# MAGIC grande a la derecha (muestras pequeñas) y casi nula a la izquierda, donde el MSE del
# MAGIC EBLUP tiende a D_d (p. 440).

# COMMAND ----------

# DBTITLE 1,Figura: CV directo vs CV EBLUP del modelo elegido
fig = figura_cv_directo_vs_eblup(modelo_ganador, municipios)
display(fig)
plt.close(fig)
print(interpretar_cv(modelo_ganador))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Robustez del modelo elegido: distancia de Cook
# MAGIC
# MAGIC **Cómo leer la figura.** Cada barra es un dominio y su altura es la distancia de Cook
# MAGIC en el ajuste por mínimos cuadrados generalizados del modelo elegido: cuánto cambiarían
# MAGIC los coeficientes si ese dominio no estuviera. La línea discontinua es el umbral
# MAGIC convencional 4/n y las barras rojas lo superan. La tabla siguiente reajusta el modelo
# MAGIC completo (incluida Â) sin el dominio más influyente. `Cambio_signif` marca si una
# MAGIC covariable cruza el umbral de significancia en cualquier sentido (pierde o gana): si
# MAGIC ninguna cambia de signo ni de significancia, la conclusión no depende de un solo
# MAGIC territorio. Si ninguna covariable era significativa en el modelo completo, no perder
# MAGIC significancia no prueba nada y la estabilidad se lee en el cambio relativo de cada
# MAGIC coeficiente. Cook no interviene en la selección; es un diagnóstico de regresión
# MAGIC general, no del libro.

# COMMAND ----------

# DBTITLE 1,Figura y tabla: distancia de Cook y sensibilidad del modelo elegido
fig = figura_cook([modelo_ganador], [modelo_ganador.covars], municipios)
display(fig)
plt.close(fig)

df_sensibilidad = sensibilidad_cook(
    modelo_ganador, FayHerriotClasico, municipios, alfa=ALFA_SIGNIFICANCIA
)
display(df_sensibilidad)
print(
    interpretar_cook(
        modelo_ganador, municipios, df_sensibilidad, alfa=ALFA_SIGNIFICANCIA
    )
)

# COMMAND ----------

# DBTITLE 1,9. Exportar resultados del modelo ganador
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
    .saveAsTable(TBL_FH_COEFICIENTES)
)
print(f"Tabla escrita: {TBL_FH_COEFICIENTES}")

resultados_ganador = modelo_ganador.resultados.copy()
resultados_ganador["COOK_D"] = cook_ganador.round(4)
resultados_ganador["FUERA_DE_RANGO"] = marca_fuera_de_rango(
    modelo_ganador.eblup, TASA_MINIMA, TASA_MAXIMA
)
if resultados_ganador["FUERA_DE_RANGO"].any():
    print(
        f"⚠ AVISO: EBLUP fuera de [{TASA_MINIMA}, {TASA_MAXIMA}] en: "
        + ", ".join(
            f"{m} ({v:.2f})"
            for m, v in resultados_ganador.loc[
                resultados_ganador["FUERA_DE_RANGO"], ["MUNICIPIO", "EBLUP"]
            ].values
        )
    )
spark_df = spark.createDataFrame(resultados_ganador)
spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_RESULTADOS
)
print(f"Tabla escrita: {TBL_FAY_HERRIOT_RESULTADOS}")

# COMMAND ----------

# DBTITLE 1,10. Predicción sintética para dominios sin estimación directa
# Para municipios donde NO existe estimación directa (Y ni Di), el EBLUP no puede
# calcularse: el predictor es el sintético ŷ_d = x_d'β̂ del modelo ganador, sin contracción.
# Su MSE es x_d'Cov(β̂)x_d + Â (Morales et al., p. 441).
covars_ganador = modelo_ganador.covars
beta_ganador = modelo_ganador.beta_hat

# La tabla de dominios objetivo conserva los códigos de indicador; se renombran a los
# alias del modelo usando el mismo mapa que produjo la etapa de selección.
df_new = spark.table(TBL_MUNICIPIOS_SIN_ENCUESTA).toPandas()
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
    + df_new["CODIGO_MUNICIPIO"]
)

X_new = np.column_stack(
    [np.ones(len(df_new))] + [df_new[c].values for c in covars_ganador]
)
y_sintetico = X_new @ beta_ganador

# Incertidumbre: x_d'Cov(β̂)x_d (estimar β) + Â (efecto aleatorio no observado).
var_beta = np.einsum("ij,jk,ik->i", X_new, modelo_ganador.cov_beta, X_new)
var_sintetico = var_beta + modelo_ganador.A_hat
rmse_sintetico = np.sqrt(var_sintetico)
cv_sintetico = 100 * rmse_sintetico / np.abs(y_sintetico)

df_pred = df_new[["DOMINIO"] + DOMINIO_COLS].copy()
df_pred["PRED_SINTETICO"] = y_sintetico.round(4)
df_pred["RMSE_SINTETICO"] = rmse_sintetico.round(4)
df_pred["CV_SINTETICO_PCT"] = cv_sintetico.round(2)
df_pred["TIPO"] = "SINTETICO"
# EXTRAPOLA: x_d'Cov(β̂)x_d mayor que el máximo de la muestra de ajuste, es decir, un
# municipio más alejado del centro de los datos que cualquiera de los que vio el modelo.
df_pred["EXTRAPOLA"] = marca_extrapolacion(var_beta, modelo_ganador)
df_pred["FUERA_DE_RANGO"] = marca_fuera_de_rango(y_sintetico, TASA_MINIMA, TASA_MAXIMA)

print(f"\nPredicciones sintéticas para {len(df_pred)} dominios sin encuesta:")
display(df_pred)

n_extrapola = int(df_pred["EXTRAPOLA"].sum())
print(
    f"\nMunicipios cuya predicción es una extrapolación: {n_extrapola} de {len(df_pred)}"
    + (
        ": " + ", ".join(df_pred.loc[df_pred["EXTRAPOLA"], "MUNICIPIO"])
        if n_extrapola
        else ""
    )
)
if df_pred["FUERA_DE_RANGO"].any():
    print(
        f"⚠ AVISO: predicción sintética fuera de [{TASA_MINIMA}, {TASA_MAXIMA}] en: "
        + ", ".join(
            f"{m} ({v:.2f})"
            for m, v in df_pred.loc[
                df_pred["FUERA_DE_RANGO"], ["MUNICIPIO", "PRED_SINTETICO"]
            ].values
        )
    )

spark_df_pred = spark.createDataFrame(df_pred)
spark_df_pred.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_PREDICCION_SINTETICA
)
print(f"Tabla escrita: {TBL_FAY_HERRIOT_PREDICCION_SINTETICA}")

# COMMAND ----------

# DBTITLE 1,11. Tabla final consolidada (EBLUP + sintético)
tabla_entrenamiento = modelo_ganador.resultados[
    ["DOMINIO"] + DOMINIO_COLS + ["EBLUP", "CV_EBLUP_PCT"]
].rename(columns={"EBLUP": "TASA_DESEMPLEO_PCT", "CV_EBLUP_PCT": "CV_PCT"})
tabla_entrenamiento["TIPO"] = "EBLUP"

tabla_sintetica = df_pred.rename(
    columns={"PRED_SINTETICO": "TASA_DESEMPLEO_PCT", "CV_SINTETICO_PCT": "CV_PCT"}
)[["DOMINIO"] + DOMINIO_COLS + ["TASA_DESEMPLEO_PCT", "CV_PCT", "TIPO"]]

df_final = construir_tabla_final(
    tabla_entrenamiento, tabla_sintetica, spark.table(TBL_DIM_DIVIPOLA).toPandas()
)

# Marcas de aviso por dominio. Los dominios con EBLUP no extrapolan (están en la muestra de
# ajuste).
marcas = pd.concat(
    [
        resultados_ganador[["DOMINIO", "FUERA_DE_RANGO"]].assign(EXTRAPOLA=False),
        df_pred[["DOMINIO", "FUERA_DE_RANGO", "EXTRAPOLA"]],
    ],
    ignore_index=True,
).drop_duplicates(subset="DOMINIO", keep="first")
df_final = df_final.merge(marcas, on="DOMINIO", how="left")

print(
    f"\nTabla final consolidada: {len(df_final)} dominios "
    f"({(df_final['TIPO']=='EBLUP').sum()} EBLUP + {(df_final['TIPO']=='SINTETICO').sum()} sintéticos)"
)
display(df_final.drop(columns=["DOMINIO"]))

spark_df_final = spark.createDataFrame(df_final.drop(columns=["DOMINIO"]))
spark_df_final.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_ESTIMACIONES_FINALES
)
print(f"Tabla escrita: {TBL_FAY_HERRIOT_ESTIMACIONES_FINALES}")
