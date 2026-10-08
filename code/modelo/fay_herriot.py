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
# MAGIC    `eda_seleccion_covariables`, y aquí se compara con sus **variantes dejando una
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
# MAGIC 5. **Municipios objetivo.** Municipios de `municipios_sin_encuesta` (sin estimación
# MAGIC    directa propia), que reciben la predicción sintética x_m'β̂ del modelo ganador.
# MAGIC 6. **Benchmarking en dos niveles** (`shared/benchmarking.py`, donde está la sustentación
# MAGIC    completa). Nivel 1: los 23 EBLUP se ajustan para que, ponderados por la PEA expandida,
# MAGIC    reproduzcan la tasa directa del total de las 23 ciudades (la cifra oficial del DANE).
# MAGIC    Nivel 2: los municipios de un dominio A.M. (Cali y Yumbo) se ajustan para que,
# MAGIC    ponderados por su población de 15 años y más, reproduzcan el valor ya ajustado de su
# MAGIC    dominio. Es el ajuste de razón de Fay y Herriot (1979) que usan el DANE (nota SAE 2024)
# MAGIC    y el INE de Chile (ENUSC 2018). La celda 12 lo verifica.
# MAGIC
# MAGIC Dominio: PER + MES + `CODIGO_DOMINIO` (código DIVIPOLA de la capital). Cada dominio es una
# MAGIC ciudad o una ciudad con su área metropolitana («Cali A.M.»), porque el campo `AREA` de la
# MAGIC GEIH no separa los municipios del A.M.; sus covariables son el promedio ponderado de los
# MAGIC municipios miembro (`adicion_covariables`). La tabla final tiene dos niveles (dominio y
# MAGIC municipio) y toma los nombres de `dim_dominio_geih` y `dim_divipola` por código.

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
from shared.benchmarking import (
    promedio_ponderado,
    benchmark_nivel1,
    benchmark_nivel2,
    verificar_benchmark,
)

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

# El dominio se identifica por su código (DIVIPOLA de la capital): los nombres cambian de
# formato entre fuentes.
df["DOMINIO"] = (
    df["PER"].astype(str) + "_" + df["MES"].astype(str) + "_" + df["CODIGO_DOMINIO"]
)

print(
    f"Dominios: {len(df)} ({(df['TIPO_DOMINIO'] == 'CIUDAD_AM').sum()} ciudades con área "
    "metropolitana)"
)
print(f"Columnas disponibles:  {df.columns.tolist()}\n")

# COMMAND ----------

# DBTITLE 1,2. Especificaciones a comparar (conjunto del EDA y variantes dejar-una-fuera)
covars_eda = [c for c in df.columns if c in alias_a_codigo]

if not covars_eda:
    raise ValueError(
        f"No se reconoció ninguna covariable en {TBL_COVARIABLES_SELECCIONADAS}. "
        f"Volver a ejecutar eda_seleccion_covariables."
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

nombres_dominio = df["NOMBRE_DOMINIO"].values

# COMMAND ----------

# DBTITLE 1,4. Tablas EBLUP por dominio (por modelo)
eblup_display_cols = [
    "NOMBRE_DOMINIO",
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
        f"  Distancia de Cook máxima:     {cook.max():.4f} en {nombres_dominio[int(np.argmax(cook))]}  "
        f"(umbral 4/n = {umbral_cook:.4f}; {len(influyentes)} dominio(s) lo superan"
        + (f": {', '.join(nombres_dominio[influyentes])})" if len(influyentes) else ")")
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
        "NOMBRE_DOMINIO",
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

    df_cook_variantes = tabla_cook(modelos, nombres_covars, nombres_dominio)
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
fig = figura_cv_directo_vs_eblup(modelo_ganador, nombres_dominio)
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
fig = figura_cook([modelo_ganador], [modelo_ganador.covars], nombres_dominio)
display(fig)
plt.close(fig)

df_sensibilidad = sensibilidad_cook(
    modelo_ganador, FayHerriotClasico, nombres_dominio, alfa=ALFA_SIGNIFICANCIA
)
display(df_sensibilidad)
print(
    interpretar_cook(
        modelo_ganador, nombres_dominio, df_sensibilidad, alfa=ALFA_SIGNIFICANCIA
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
                resultados_ganador["FUERA_DE_RANGO"], ["NOMBRE_DOMINIO", "EBLUP"]
            ].values
        )
    )

# COMMAND ----------

# DBTITLE 1,9b. Benchmarking de nivel 1: dominios → Total 23 ciudades y A.M.
# Sustentación completa en shared/benchmarking.py. Los EBLUP de los dominios se multiplican por
# un factor de razón λ₁ (Fay y Herriot, 1979; DANE, nota SAE 2024, PDF 25; INE Chile, ENUSC
# 2018, PDF 23) para que su promedio ponderado por la PEA expandida reproduzca la tasa directa
# del conjunto de los dominios.
#
# Valor de referencia: Σ PEA_d·TD_d / Σ PEA_d. Por la propiedad de benchmarking del Hájek
# (Molina, 2019, PDF 26) es exactamente la estimación directa de las 23 ciudades juntas, un
# dominio que la GEIH publica cada trimestre (Metodología GEIH v9, PDF 10). Se contrasta con la
# cifra oficial del DANE («Total 23 ciudades y A.M.» en datos_municipales) y la ejecución se
# detiene si difieren más de TOLERANCIA_DANE_PP: un valor de referencia que no reproduce la cifra
# oficial indicaría un problema en los datos, no algo que el ajuste deba absorber.
periodos = df[["PER", "MES"]].drop_duplicates()
if len(periodos) != 1:
    raise ValueError(
        f"El benchmarking se define por período y hay {len(periodos)} períodos en {TBL_COVARIABLES_SELECCIONADAS}."
    )
PER_MODELO, MES_MODELO = int(periodos["PER"].iloc[0]), int(periodos["MES"].iloc[0])

pea_dominio = (
    df.set_index("DOMINIO")
    .loc[resultados_ganador["DOMINIO"], COL_PESO_NIVEL1]
    .to_numpy(dtype=float)
)
referencia_n1 = promedio_ponderado(resultados_ganador[Y_COL], pea_dominio)

total_dane = [
    fila["TASA_DESEMPLEO"]
    for fila in spark.table(TBL_DATOS_MUNICIPALES)
    .filter(
        f"ANIO = {PER_MODELO} AND MES = {MES_MODELO} AND CIUDAD = '{NOMBRE_TOTAL_23}'"
    )
    .select("TASA_DESEMPLEO")
    .collect()
]
if total_dane:
    dif_dane = referencia_n1 - float(total_dane[0])
    print(
        f"Valor de referencia (directa del conjunto): {referencia_n1:.4f} %  |  "
        f"DANE «{NOMBRE_TOTAL_23}»: {float(total_dane[0]):.4f} %  (dif. {dif_dane:+.4f} pp)"
    )
    if abs(dif_dane) > TOLERANCIA_DANE_PP:
        raise ValueError(
            f"La tasa directa del conjunto de dominios ({referencia_n1:.4f}) no reproduce la "
            f"cifra oficial del DANE ({float(total_dane[0]):.4f}). Revisar la estimación directa "
            f"antes de ajustar."
        )
else:
    print(
        f"Sin cifra publicada para {PER_MODELO}-{MES_MODELO:02d}: se usa la estimación directa "
        f"del conjunto ({referencia_n1:.4f} %) sin contraste con el DANE."
    )

eblup_n1, lambda_n1 = benchmark_nivel1(modelo_ganador.eblup, pea_dominio, referencia_n1)

resultados_ganador["PEA_EXPANDIDA"] = pea_dominio.round(0)
resultados_ganador["LAMBDA_N1"] = round(lambda_n1, 6)
resultados_ganador["EBLUP_BENCHMARK"] = eblup_n1.round(4)
# λ se trata como fijo: el RMSE se escala por λ y el CV no cambia (ver shared/benchmarking.py).
resultados_ganador["RMSE_EBLUP_BENCHMARK"] = (modelo_ganador.rmse * lambda_n1).round(4)

print(
    f"λ₁ = {lambda_n1:.6f}  (agregado de los EBLUP antes del ajuste: "
    f"{promedio_ponderado(modelo_ganador.eblup, pea_dominio):.4f} %)"
)

spark_df = spark.createDataFrame(resultados_ganador)
spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_RESULTADOS
)
print(f"Tabla escrita: {TBL_FAY_HERRIOT_RESULTADOS}")

# COMMAND ----------

# DBTITLE 1,10. Predicción sintética para los municipios sin estimación directa propia
# Para municipios sin estimación directa propia (Y ni Di), el EBLUP no puede calcularse: el
# predictor es el sintético ŷ_m = x_m'β̂ del modelo ganador, sin contracción, con las
# covariables del municipio (no las del dominio). Su MSE es x_m'Cov(β̂)x_m + Â (Morales et al.,
# p. 441). Usar el β̂ estimado con dominios para predecir municipios es coherente porque las
# covariables de los dominios A.M. se agregaron con los mismos pesos que la tasa
# (preprocesamiento/shared/agregacion_dominios.py).
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
        f"Revisar la completitud reportada por dominios_sin_encuesta."
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

# Incertidumbre: x_m'Cov(β̂)x_m (estimar β) + Â (efecto aleatorio no observado).
var_beta = np.einsum("ij,jk,ik->i", X_new, modelo_ganador.cov_beta, X_new)
var_sintetico = var_beta + modelo_ganador.A_hat
rmse_sintetico = np.sqrt(var_sintetico)
cv_sintetico = 100 * rmse_sintetico / np.abs(y_sintetico)

df_pred = df_new[["DOMINIO"] + MUNICIPIO_COLS].copy()
df_pred["PRED_SINTETICO"] = y_sintetico.round(4)
df_pred["RMSE_SINTETICO"] = rmse_sintetico.round(4)
df_pred["CV_SINTETICO_PCT"] = cv_sintetico.round(2)
# EXTRAPOLA: x_m'Cov(β̂)x_m mayor que el máximo de la muestra de ajuste, es decir, un
# municipio más alejado del centro de los datos que cualquiera de los que vio el modelo.
df_pred["EXTRAPOLA"] = marca_extrapolacion(var_beta, modelo_ganador)
df_pred["FUERA_DE_RANGO"] = marca_fuera_de_rango(y_sintetico, TASA_MINIMA, TASA_MAXIMA)

print(
    f"\nPredicciones sintéticas para {len(df_pred)} municipios sin estimación directa propia"
)

n_extrapola = int(df_pred["EXTRAPOLA"].sum())
print(
    f"Municipios cuya predicción es una extrapolación: {n_extrapola} de {len(df_pred)}"
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

# COMMAND ----------

# DBTITLE 1,10b. Benchmarking de nivel 2: municipios de un dominio A.M. → valor de su dominio
# Sustentación completa en shared/benchmarking.py. Los municipios que forman un dominio A.M. con
# estimación directa (Cali y Yumbo en Cali A.M.) reciben su predicción sintética y luego un
# factor de razón λ_D por dominio, para que su promedio ponderado por la población de 15 años y
# más (PET CNPV 2018, suma de los grupos de edad de TerriData; aproximación de la PEA municipal)
# reproduzca el valor ya ajustado
# del dominio (nivel 1). Así municipio, ciudad A.M. y total quedan coherentes, como en el DANE
# («departamentales, de ciudades principales y nacional», nota SAE 2024, PDF 25).
#
# Por qué Yumbo recibe estimación propia y no la tasa de Cali A.M.: el modelo anidado
# (Morales et al., p. 462) exige estimaciones directas por municipio, que la GEIH pública no
# permite, y asignarle la tasa del A.M. es el sintético básico, sesgado si Yumbo difiere de Cali
# (Morales et al., p. 42).
#
# El peso es el mismo con el que se agregaron las covariables del dominio, de modo que el
# agregado de los sintéticos municipales es el sintético del dominio y λ_D − 1 mide cuánto se
# separa el dominio de su predicción sintética. Los municipios sin dominio padre no se ajustan:
# no hay un valor de referencia trimestral confiable que los contenga (el departamento solo es
# representativo con datos anuales, Metodología GEIH v9, PDF 9).
pesos_n2 = (
    spark.table(TBL_TERRIDATA)
    .filter(f"ANO = {PER_MODELO} AND MES = {MES_MODELO}")
    .selectExpr(
        "CODIGO_ENTIDAD AS CODIGO_MUNICIPIO",
        f"{EXPR_PESO_POBLACION} AS PESO_N2",
    )
    .toPandas()
)
df_pred = df_pred.merge(
    pesos_n2, on="CODIGO_MUNICIPIO", how="left", validate="one_to_one"
)

# Valor de referencia de cada dominio: su EBLUP ajustado en el nivel 1 (sin redondear).
objetivos_n2 = dict(zip(resultados_ganador["CODIGO_DOMINIO"], eblup_n1))

df_bm2 = benchmark_nivel2(
    df_pred.assign(PRED_EXACTA=y_sintetico),
    col_pred="PRED_EXACTA",
    col_peso="PESO_N2",
    col_padre="CODIGO_DOMINIO_PADRE",
    objetivos=objetivos_n2,
)
df_pred["LAMBDA_N2"] = df_bm2["LAMBDA_N2"].round(6)
df_pred["PRED_BENCHMARK"] = df_bm2["PRED_BENCHMARK"].round(4)
df_pred["RMSE_BENCHMARK"] = (rmse_sintetico * df_bm2["LAMBDA_N2"]).round(4)
df_pred["TIPO"] = np.where(df_bm2["BENCHMARK"], "SINTETICO_BENCHMARK", "SINTETICO")

ajustados = df_pred[df_bm2["BENCHMARK"]]
print(f"Municipios ajustados a su dominio A.M.: {len(ajustados)}")
display(
    ajustados[
        [
            "CODIGO_DOMINIO_PADRE",
            "MUNICIPIO",
            "PESO_N2",
            "PRED_SINTETICO",
            "LAMBDA_N2",
            "PRED_BENCHMARK",
            "CV_SINTETICO_PCT",
        ]
    ]
)

spark_df_pred = spark.createDataFrame(df_pred)
spark_df_pred.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_PREDICCION_SINTETICA
)
print(f"Tabla escrita: {TBL_FAY_HERRIOT_PREDICCION_SINTETICA}")

# COMMAND ----------

# DBTITLE 1,11. Tabla final consolidada (dominios + municipios)
# Dos niveles: los 23 dominios con el EBLUP ajustado (nivel 1) y los municipios objetivo con la
# predicción sintética (ajustada en el nivel 2 cuando pertenecen a un dominio A.M.). La tasa sin
# ajustar se conserva en TASA_SIN_AJUSTE_PCT para trazabilidad.
tabla_dominios = pd.DataFrame(
    {
        "PER": resultados_ganador["PER"],
        "MES": resultados_ganador["MES"],
        "CODIGO": resultados_ganador["CODIGO_DOMINIO"],
        "TASA_DESEMPLEO_PCT": resultados_ganador["EBLUP_BENCHMARK"],
        "TASA_SIN_AJUSTE_PCT": resultados_ganador["EBLUP"],
        "LAMBDA": resultados_ganador["LAMBDA_N1"],
        "CV_PCT": resultados_ganador["CV_EBLUP_PCT"],
        "TIPO": "EBLUP_BENCHMARK",
    }
)
tabla_municipios = pd.DataFrame(
    {
        "PER": df_pred["PER"],
        "MES": df_pred["MES"],
        "CODIGO": df_pred["CODIGO_MUNICIPIO"],
        "CODIGO_DOMINIO_PADRE": df_pred["CODIGO_DOMINIO_PADRE"],
        "TASA_DESEMPLEO_PCT": df_pred["PRED_BENCHMARK"],
        "TASA_SIN_AJUSTE_PCT": df_pred["PRED_SINTETICO"],
        "LAMBDA": df_pred["LAMBDA_N2"],
        "CV_PCT": df_pred["CV_SINTETICO_PCT"],
        "TIPO": df_pred["TIPO"],
    }
)

dim_dominio = spark.table(TBL_DIM_DOMINIO).toPandas()
df_final = construir_tabla_final(
    tabla_dominios,
    tabla_municipios,
    dim_dominio,
    spark.table(TBL_DIM_DIVIPOLA).toPandas(),
)

# Marcas de aviso. Los dominios no extrapolan (están en la muestra de ajuste). Un mismo código
# puede ser dominio y municipio (76001), así que se une por NIVEL + CODIGO.
marcas = pd.concat(
    [
        resultados_ganador[["CODIGO_DOMINIO", "FUERA_DE_RANGO"]]
        .rename(columns={"CODIGO_DOMINIO": "CODIGO"})
        .assign(NIVEL="DOMINIO", EXTRAPOLA=False),
        df_pred[["CODIGO_MUNICIPIO", "FUERA_DE_RANGO", "EXTRAPOLA"]]
        .rename(columns={"CODIGO_MUNICIPIO": "CODIGO"})
        .assign(NIVEL="MUNICIPIO"),
    ],
    ignore_index=True,
)
df_final = df_final.merge(
    marcas, on=["NIVEL", "CODIGO"], how="left", validate="one_to_one"
)

print(
    f"\nTabla final consolidada: {(df_final['NIVEL'] == 'DOMINIO').sum()} dominios + "
    f"{(df_final['NIVEL'] == 'MUNICIPIO').sum()} municipios "
    f"({(df_final['TIPO'] == 'SINTETICO_BENCHMARK').sum()} ajustados a su dominio A.M.)"
)
display(df_final)

spark_df_final = spark.createDataFrame(df_final)
spark_df_final.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_FAY_HERRIOT_ESTIMACIONES_FINALES
)
print(f"Tabla escrita: {TBL_FAY_HERRIOT_ESTIMACIONES_FINALES}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Verificación del benchmarking
# MAGIC
# MAGIC Siguiendo la presentación del DANE (tabla de diferencias entre la estimación directa y el
# MAGIC agregado del modelo antes del ajuste, nota SAE 2024, PDF 19, y diferencias prácticamente
# MAGIC nulas después, PDF 25), para cada nivel se muestra el agregado ponderado antes y después
# MAGIC del ajuste y se comprueba que:
# MAGIC
# MAGIC * **(a) consistencia:** después del ajuste el agregado iguala al valor de referencia;
# MAGIC * **(b) razones conservadas:** todas las unidades de un territorio se multiplicaron por el
# MAGIC   mismo λ, así que el orden entre dominios o municipios no cambia;
# MAGIC * **(c) rango:** las tasas ajustadas siguen en [0, 100];
# MAGIC * **(d) miembros completos:** las unidades son exactamente los miembros del territorio
# MAGIC   (en el nivel 2, los municipios del A.M. según `dim_dominio_geih`).
# MAGIC
# MAGIC Si alguna falla, la celda se detiene. **λ** es además un diagnóstico del modelo: «si el
# MAGIC modelo es adecuado, el factor de ajuste estará en torno a uno» (INE Chile, ENUSC 2018,
# MAGIC PDF 23); se avisa si se aleja de 1 más de `UMBRAL_LAMBDA_AVISO`. Por último se repite la
# MAGIC comprobación sobre la tabla final publicada (valores redondeados a 4 decimales).

# COMMAND ----------

# DBTITLE 1,12. Verificación del benchmarking
# Nivel 1: los 23 dominios frente al total de las 23 ciudades.
print("NIVEL 1 — dominios → «" + NOMBRE_TOTAL_23 + "» (pesos: PEA expandida)")
detalle_n1 = pd.DataFrame(
    {
        "TERRITORIO": NOMBRE_TOTAL_23,
        "CODIGO_DOMINIO": resultados_ganador["CODIGO_DOMINIO"].values,
        "NOMBRE_DOMINIO": resultados_ganador["NOMBRE_DOMINIO"].values,
        "PESO": pea_dominio,
        "DIRECTA": resultados_ganador[Y_COL].values,
        "EBLUP": modelo_ganador.eblup,
        "EBLUP_BENCHMARK": eblup_n1,
    }
)
verificacion_n1 = verificar_benchmark(
    detalle_n1,
    col_grupo="TERRITORIO",
    col_id="CODIGO_DOMINIO",
    col_peso="PESO",
    col_antes="EBLUP",
    col_despues="EBLUP_BENCHMARK",
    objetivos={NOMBRE_TOTAL_23: referencia_n1},
    miembros_esperados={NOMBRE_TOTAL_23: set(df["CODIGO_DOMINIO"])},
    tasa_min=TASA_MINIMA,
    tasa_max=TASA_MAXIMA,
    umbral_lambda=UMBRAL_LAMBDA_AVISO,
)
display(verificacion_n1)
detalle_n1["DIF_EBLUP_DIRECTA_PP"] = detalle_n1["EBLUP"] - detalle_n1["DIRECTA"]
detalle_n1["CAMBIO_AJUSTE_PP"] = detalle_n1["EBLUP_BENCHMARK"] - detalle_n1["EBLUP"]
display(detalle_n1.round(4))

# Nivel 2: municipios de cada dominio A.M. frente al valor ajustado del dominio.
ajustados_bm2 = df_bm2[df_bm2["BENCHMARK"]]
if ajustados_bm2.empty:
    print("\nNIVEL 2 — no hay municipios objetivo dentro de un dominio A.M.")
else:
    print(
        "\nNIVEL 2 — municipios → su dominio A.M. (pesos: población de 15 años y más)"
    )
    miembros_n2 = {
        padre: set(
            dim_dominio.loc[dim_dominio["CODIGO_DOMINIO"] == padre, "CODIGO_MUNICIPIO"]
        )
        for padre in ajustados_bm2["CODIGO_DOMINIO_PADRE"].unique()
    }
    verificacion_n2 = verificar_benchmark(
        ajustados_bm2,
        col_grupo="CODIGO_DOMINIO_PADRE",
        col_id="CODIGO_MUNICIPIO",
        col_peso="PESO_N2",
        col_antes="PRED_EXACTA",
        col_despues="PRED_BENCHMARK",
        objetivos={p: objetivos_n2[p] for p in miembros_n2},
        miembros_esperados=miembros_n2,
        tasa_min=TASA_MINIMA,
        tasa_max=TASA_MAXIMA,
        umbral_lambda=UMBRAL_LAMBDA_AVISO,
    )
    display(verificacion_n2)

# Comprobación sobre la tabla final publicada (redondeada a 4 decimales): los agregados deben
# coincidir con los valores de referencia salvo el redondeo.
TOLERANCIA_REDONDEO = 1e-3
dom_final = df_final[df_final["NIVEL"] == "DOMINIO"].merge(
    detalle_n1[["CODIGO_DOMINIO", "PESO"]].rename(columns={"CODIGO_DOMINIO": "CODIGO"}),
    on="CODIGO",
)
agregado_publicado = promedio_ponderado(
    dom_final["TASA_DESEMPLEO_PCT"], dom_final["PESO"]
)
print(
    f"\nTabla final, nivel 1: agregado {agregado_publicado:.4f} vs referencia "
    f"{referencia_n1:.4f} → "
    + (
        "PASS"
        if abs(agregado_publicado - referencia_n1) <= TOLERANCIA_REDONDEO
        else "FAIL"
    )
)
if abs(agregado_publicado - referencia_n1) > TOLERANCIA_REDONDEO:
    raise ValueError("La tabla final no reproduce el total de las 23 ciudades.")

mun_final = df_final[df_final["TIPO"] == "SINTETICO_BENCHMARK"].merge(
    df_pred[["CODIGO_MUNICIPIO", "PESO_N2"]].rename(
        columns={"CODIGO_MUNICIPIO": "CODIGO"}
    ),
    on="CODIGO",
)
for padre, sub in mun_final.groupby("CODIGO_DOMINIO_PADRE"):
    valor_dominio = dom_final.loc[
        dom_final["CODIGO"] == padre, "TASA_DESEMPLEO_PCT"
    ].iloc[0]
    agregado = promedio_ponderado(sub["TASA_DESEMPLEO_PCT"], sub["PESO_N2"])
    ok = abs(agregado - valor_dominio) <= TOLERANCIA_REDONDEO
    print(
        f"Tabla final, nivel 2 ({padre}): agregado {agregado:.4f} vs dominio "
        f"{valor_dominio:.4f} → {'PASS' if ok else 'FAIL'}"
    )
    if not ok:
        raise ValueError(f"La tabla final no reproduce el valor del dominio {padre}.")
