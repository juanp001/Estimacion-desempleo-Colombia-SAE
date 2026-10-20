# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Modelo Fay-Herriot
# MAGIC
# MAGIC Las decisiones metodológicas se apoyan en Morales et al. (2021), *A Course on Small
# MAGIC Area Estimation and Mixed Models*.
# MAGIC
# MAGIC Es el modelo base (**benchmark**) Fay-Herriot **clásico**: efectos aleatorios
# MAGIC independientes por dominio, sin componente espacial. Â se estima por REML, β̂ por
# MAGIC mínimos cuadrados generalizados y el AIC con la verosimilitud ML
# MAGIC (`shared/fay_herriot.py`).
# MAGIC
# MAGIC **EC1…EC5 no son los modelos finales del objetivo 1.** Son *especificaciones
# MAGIC candidatas del modelo base Fay-Herriot clásico*; de ellas sale el benchmark
# MAGIC seleccionado. La comparación del objetivo 1 se hace después, en
# MAGIC `fay_herriot_espacial`, entre ese benchmark y las especificaciones espaciales.
# MAGIC
# MAGIC 1. **MSE del EBLUP.** Estimador de Prasad-Rao para REML del libro (p. 440), con
# MAGIC    `g3 = D²/(D+Â)³ · avar(Â)`.
# MAGIC 2. **De dónde salen las covariables.** El conjunto lo elige
# MAGIC    `eda_seleccion_covariables` (EC1) y aquí se compara con las **especificaciones que
# MAGIC    dejan una covariable fuera** (EC2…), para responder si cada covariable aporta.
# MAGIC 3. **Cómo se elige el benchmark.** El modelo se usa para predecir municipios sin
# MAGIC    encuesta. Según Morales et al. (p. 453), los modelos de área suelen servir para
# MAGIC    predecir lo observado y admiten sobreparametrizar; pero si además se predice fuera de
# MAGIC    muestra (aquí, la predicción sintética) no conviene sobreparametrizar y se recomienda
# MAGIC    que todas las covariables sean significativas (p < 0.05). Esa es la regla estricta que
# MAGIC    se aplica: solo compiten las especificaciones que la cumplen. El libro admite incluir
# MAGIC    alguna covariable con p > 0.05 si tiene interpretación razonable (p. 454); eso debe
# MAGIC    reportarse como excepción explícita, no aplicarse en silencio. Entre las que compiten
# MAGIC    se elige la de menor AIC y, entre las equivalentes (ΔAIC ≤ 2), la de menos covariables.
# MAGIC    El umbral ΔAIC ≤ 2 y el AICc son convenciones externas al libro. El **AICc** se calcula
# MAGIC    como complemento (no cambia la decisión) porque con 23 dominios el AIC penaliza poco; en
# MAGIC    Fay-Herriot es una aproximación (la fórmula viene de regresión con errores iid y aquí las
# MAGIC    D_i son heterogéneas), y el libro remite a Marhuenda et al. (2014) para criterios de
# MAGIC    información propios del modelo (p. 420). Sirve para decir que el benchmark se eligió entre
# MAGIC    varias especificaciones con soporte similar mediante la regla de parsimonia. El MSE del EBLUP y la
# MAGIC    distancia de Cook se muestran después como diagnósticos del benchmark: ganancia de
# MAGIC    precisión y robustez.
# MAGIC 4. **Avisos.** Encuesta sin peso en el EBLUP (Â ≈ 0), tasas fuera de [0, 100] y
# MAGIC    municipios cuya predicción sintética es una extrapolación. La celda 10a (B20)
# MAGIC    documenta la extrapolación: rango de cada covariable en dominios y municipios, qué
# MAGIC    covariable saca a cada municipio del rango, cuántos puntos de su predicción vienen de
# MAGIC    fuera y cuánto cambia la predicción con las covariables acotadas al rango o al quitar
# MAGIC    un dominio. La tasa publicada no cambia (`shared/extrapolacion.py`). La celda 11a
# MAGIC    (B21) lleva ese estado a la tabla final: `CALIDAD_REPORTADA` dice que el CV de un
# MAGIC    municipio es condicional al modelo y, si extrapola, lo marca como extrapolado.
# MAGIC 5. **Municipios objetivo.** Municipios de `municipios_sin_encuesta` (sin estimación
# MAGIC    directa propia), que reciben la predicción sintética x_m'β̂ del benchmark seleccionado.
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
# MAGIC (GVF). Aquí se usa la alternativa (a): σ²_d es la varianza **bootstrap por viviendas
# MAGIC dentro de cada dominio** de la estimación directa (`estimacion_directa`, G7-B3), sin
# MAGIC suavizar: se remuestrean viviendas completas, con el dominio como estrato (p. 61).
# MAGIC
# MAGIC Limitación: los microdatos no traen el estrato interno ni el segmento de la GEIH, así que
# MAGIC σ²_d es una aproximación a la varianza del diseño. No se sabe si esta es mayor o menor,
# MAGIC ni por cuánto. `modelo/sensibilidad_varianza.py` reajusta el modelo con otras σ²_d
# MAGIC (bootstrap por personas, Taylor, dos GVF y σ²_d multiplicada por factores de 1/3 a 3) y
# MAGIC muestra cuánto cambian el ganador, los coeficientes, los EBLUP y las predicciones.

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
    etiqueta_especificacion,
    variantes_dejar_una_fuera,
    distancia_cook,
    tabla_diagnosticos,
    tabla_cook,
    tabla_seleccion,
    elegir_ganador,
    redaccion_seleccion,  # Punto 2: texto de soporte de la selección (AIC + AICc)
    sensibilidad_cook,
    figura_cook,
    interpretar_cook,
)
from shared.estabilidad_coeficientes import (
    ADVERTENCIA_POST_SELECCION,
    dejar_uno_fuera_coeficientes,
    resumen_dejar_uno_fuera,
    bootstrap_dominios,
    resumen_bootstrap,
    tabla_estabilidad,
    interpretar_estabilidad,
    dejar_uno_fuera_predicciones,  # G7-B18: LOAO completo y efecto en predicciones
    resumen_influencia_dominios,
    top_dominios_por_parametro,
    interpretar_influencia,
    figura_influencia,
)
from shared.diagnosticos import (
    graficar_validacion,
    explicacion_graficas,
    interpretar_validacion,
    figura_cv_directo_vs_eblup,
    interpretar_cv,
    aviso_encuesta_sin_peso,
    marca_fuera_de_rango,
)
from shared.extrapolacion import (
    ESTADO_DENTRO,
    estado_extrapolacion,
    rangos_covariables,
    sensibilidad_quitar_dominio,
    figura_rangos,
    figura_sensibilidad,
    interpretar_extrapolacion,
)
from shared.consolidacion import (
    construir_tabla_final,
    resumen_calidad,
    interpretar_calidad,
)

# Cifra oficial del DANE de la ventana de la estimación directa (año reconstruido o trimestre
# publicado). Se importa por ruta completa porque `shared` aquí es modelo/shared.
from preprocesamiento.shared.ventana import td_dane_ventana
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

# DBTITLE 1,2. Especificaciones candidatas del modelo base (conjunto del EDA y dejar-una-fuera)
covars_eda = [c for c in df.columns if c in alias_a_codigo]

if not covars_eda:
    raise ValueError(
        f"No se reconoció ninguna covariable en {TBL_COVARIABLES_SELECCIONADAS}. "
        f"Volver a ejecutar eda_seleccion_covariables."
    )

nombres_covars = variantes_dejar_una_fuera(covars_eda)

print(f"Conjunto elegido por el análisis exploratorio: {' + '.join(covars_eda)}")
print(
    f"Especificaciones candidatas del modelo base Fay-Herriot clásico "
    f"({len(nombres_covars)}):"
)
for i, covars in enumerate(nombres_covars, 1):
    excluida = set(covars_eda) - set(covars)
    etiqueta = f"(sin {next(iter(excluida))})" if excluida else "(conjunto completo)"
    print(f"  {etiqueta_especificacion(i)}: {' + '.join(covars)}  {etiqueta}")

# COMMAND ----------

# DBTITLE 1,3. Ajuste de todos los modelos
print(f"\nAjustando {len(nombres_covars)} especificación(es) candidata(s)...\n")
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
    print(
        f"{etiqueta_especificacion(i)}: {' + '.join(covars)} — RESULTADOS EBLUP POR DOMINIO"
    )
    print("=" * 65)
    display(modelo.resultados[eblup_display_cols])

# COMMAND ----------

# DBTITLE 1,5. Gráficas de validación (por modelo)
for i, (modelo, covars) in enumerate(zip(modelos, nombres_covars), 1):
    etiqueta = f"{etiqueta_especificacion(i)}: {' + '.join(covars)}"
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
    print(f"{etiqueta_especificacion(i)}: {' + '.join(covars)}")
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

# DBTITLE 1,7. Selección del benchmark (solo cuando hay más de una especificación)
if len(modelos) > 1:
    print("=" * 65)
    print("TABLA 1 — DIAGNÓSTICOS POR ESPECIFICACIÓN CANDIDATA (informativa)")
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
    print("TABLA 2 — SELECCIÓN DEL BENCHMARK (significancia + AIC + parsimonia)")
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
        "(Morales et al., p. 453: no sobreparametrizar al predecir fuera de muestra; "
        "p. 454 admite una covariable con p > 0.05 si es interpretable, a reportar aparte)"
    )
    print(
        f"  Equivalente_AIC: ΔAIC ≤ {DELTA_AIC_EQUIVALENTE} frente a la mejor candidata; "
        "entre ellas se elige la de menos covariables"
    )
    print("  MSE_medio y Cook_max: informativas, no intervienen en la decisión")
    # Punto 2: AICc como complemento (n pequeño); tampoco interviene en la decisión.
    print(
        "  AICc / Delta_AICc: AIC con corrección de muestra pequeña (n = "
        f"{modelos[0].n} dominios), complemento que no interviene en la decisión"
    )

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

# DBTITLE 1,8. Benchmark seleccionado (Fay-Herriot clásico)
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
        "\nAVISO: el benchmark seleccionado no coincide con el conjunto completo (EC1) elegido por el análisis"
    )
    print(
        "exploratorio: alguna covariable no es significativa o no aporta ajuste suficiente."
    )
    print("Ambas cifras deben reportarse y la diferencia explicarse en el documento.")
    print(f"  conjunto del EDA: {' + '.join(covars_eda)}")
    print(f"  benchmark:        {' + '.join(modelo_ganador.covars)}")

print("\nNOTA SOBRE LA INFERENCIA: " + ADVERTENCIA_POST_SELECCION)

aviso = aviso_encuesta_sin_peso(modelo_ganador, UMBRAL_GAMMA_SIN_PESO)
if aviso:
    print("\n" + aviso)

# Punto 2: redacción calculada desde los datos («seleccionado entre varias especificaciones
# con soporte similar, mediante la regla de parsimonia predefinida») con la lectura de AICc.
if len(modelos) > 1:
    print("\nREDACCIÓN SUGERIDA PARA EL DOCUMENTO:")
    print(
        redaccion_seleccion(
            modelos,
            nombres_covars,
            delta_aic=DELTA_AIC_EQUIVALENTE,
            alfa=ALFA_SIGNIFICANCIA,
        )
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ganancia de precisión del benchmark seleccionado
# MAGIC
# MAGIC **Cómo leer la figura.** Cada columna es un dominio, ordenados de menor a mayor
# MAGIC varianza directa D_d. El punto gris es el CV de la estimación directa y el azul el CV
# MAGIC del EBLUP; el segmento entre ambos es la ganancia. Las líneas discontinuas marcan los
# MAGIC umbrales de confiabilidad (5 % y 20 %). Es la misma lectura que las comparaciones de
# MAGIC RMSE directo frente a EBLUP del libro (Fig. 17.2, Tabla 19.5): la ganancia debe ser
# MAGIC grande a la derecha (muestras pequeñas) y casi nula a la izquierda, donde el MSE del
# MAGIC EBLUP tiende a D_d (p. 440).

# COMMAND ----------

# DBTITLE 1,Figura: CV directo vs CV EBLUP del benchmark
fig = figura_cv_directo_vs_eblup(modelo_ganador, nombres_dominio)
display(fig)
plt.close(fig)
print(interpretar_cv(modelo_ganador))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Robustez del benchmark seleccionado: distancia de Cook
# MAGIC
# MAGIC **Cómo leer la figura.** Cada barra es un dominio y su altura es la distancia de Cook
# MAGIC en el ajuste por mínimos cuadrados generalizados del benchmark: cuánto cambiarían
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

# DBTITLE 1,Figura y tabla: distancia de Cook y sensibilidad del benchmark
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

# MAGIC %md
# MAGIC ## Estabilidad de los coeficientes del benchmark (análisis de sensibilidad)
# MAGIC
# MAGIC Los mismos 23 dominios filtran, seleccionan, comparan y luego calculan los p-valores,
# MAGIC así que **la significancia es descriptiva y condicional a la selección**; los
# MAGIC coeficientes se reportan como asociaciones preliminares. Para medir cuánto dependen de
# MAGIC los dominios se hacen dos ejercicios con la especificación **fija**: (1) dejar un
# MAGIC dominio fuera, reajustando todo el modelo (incluida Â), y (2) bootstrap de dominios
# MAGIC (remuestreo con reemplazo, `ESTABILIDAD_REPLICAS`). El bootstrap no repite la
# MAGIC selección, así que subestima la incertidumbre de haber escogido las covariables con
# MAGIC estos mismos datos. Es un análisis propio: ni Morales et al. (§16.8.2, pp. 453-454) ni
# MAGIC los artículos espaciales consultados lo tratan.

# COMMAND ----------

# DBTITLE 1,Estabilidad de coeficientes: dejar-uno-fuera y bootstrap de dominios
detalle_loo = dejar_uno_fuera_coeficientes(
    modelo_ganador, FayHerriotClasico, nombres_dominio, alfa=ALFA_SIGNIFICANCIA
)
resumen_loo = resumen_dejar_uno_fuera(detalle_loo, modelo_ganador.n)
replicas_boot = bootstrap_dominios(
    modelo_ganador,
    FayHerriotClasico,
    replicas=ESTABILIDAD_REPLICAS,
    semilla=ESTABILIDAD_SEMILLA,
)
resumen_boot = resumen_bootstrap(modelo_ganador, replicas_boot, alfa=ALFA_SIGNIFICANCIA)
df_estabilidad = tabla_estabilidad(resumen_loo, resumen_boot)
display(df_estabilidad.round(4))
print(interpretar_estabilidad(df_estabilidad))

# COMMAND ----------

# DBTITLE 1,9. Exportar resultados del benchmark seleccionado
# Coeficientes del modelo benchmark, para el capítulo de resultados.
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
# Punto 2: AICc del benchmark junto al AIC (columna nueva en fh_coeficientes).
df_coef_ganador["AICc"] = round(float(modelo_ganador.aicc), 3)
df_coef_ganador["Cook_max"] = round(float(cook_ganador.max()), 4)
(
    spark.createDataFrame(df_coef_ganador)
    .write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TBL_FH_COEFICIENTES)
)
print(f"Tabla escrita: {TBL_FH_COEFICIENTES}")

for _tabla, _destino in (
    (df_estabilidad, TBL_FH_ESTABILIDAD),
    (detalle_loo, TBL_FH_ESTABILIDAD_LOO),
):
    (
        spark.createDataFrame(_tabla)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(_destino)
    )
    print(f"Tabla escrita: {_destino}")

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
# (Molina, 2019, PDF 26) es exactamente la estimación directa de las 23 ciudades juntas en la
# misma ventana que las directas (por defecto el año calendario, G7-B2). Se contrasta con la cifra
# oficial del DANE del «Total 23 ciudades y A.M.» en esa ventana: la publicada si es un trimestre
# móvil, o la reconstruida con los 4 trimestres que no se pisan si es el año, porque el anexo no
# publica la serie anual de las 23 ciudades (preprocesamiento/shared/ventana.py). La ejecución se
# detiene si difieren más de TOLERANCIA_DANE_PP: un valor de referencia que no reproduce la cifra
# oficial indicaría un problema en los datos, no algo que el ajuste deba absorber.
periodos = df[["PER", "MES", "PERIODO", "N_MESES_VENTANA"]].drop_duplicates()
if len(periodos) != 1:
    raise ValueError(
        f"El benchmarking se define por período y hay {len(periodos)} períodos en {TBL_COVARIABLES_SELECCIONADAS}."
    )
PER_MODELO, MES_MODELO = int(periodos["PER"].iloc[0]), int(periodos["MES"].iloc[0])
N_MESES_MODELO = int(periodos["N_MESES_VENTANA"].iloc[0])
PERIODO_MODELO = periodos["PERIODO"].iloc[0]
print(
    f"Ventana de las estimaciones directas: {PERIODO_MODELO} ({N_MESES_MODELO} meses)"
)

pea_dominio = (
    df.set_index("DOMINIO")
    .loc[resultados_ganador["DOMINIO"], COL_PESO_NIVEL1]
    .to_numpy(dtype=float)
)
referencia_n1 = promedio_ponderado(resultados_ganador[Y_COL], pea_dominio)

cifras_dane = td_dane_ventana(
    spark.table(TBL_DATOS_MUNICIPALES).toPandas(),
    PER_MODELO,
    MES_MODELO,
    N_MESES_MODELO,
)
total_dane = cifras_dane.loc[
    cifras_dane["CIUDAD"] == NOMBRE_TOTAL_23, "TD_DANE"
].tolist()
if total_dane:
    dif_dane = referencia_n1 - float(total_dane[0])
    print(
        f"Valor de referencia (directa del conjunto): {referencia_n1:.4f} %  |  "
        f"DANE «{NOMBRE_TOTAL_23}» {PERIODO_MODELO}: {float(total_dane[0]):.4f} %  "
        f"(dif. {dif_dane:+.4f} pp)"
    )
    if abs(dif_dane) > TOLERANCIA_DANE_PP:
        raise ValueError(
            f"La tasa directa del conjunto de dominios ({referencia_n1:.4f}) no reproduce la "
            f"cifra oficial del DANE ({float(total_dane[0]):.4f}). Revisar la estimación directa "
            f"antes de ajustar."
        )
else:
    print(
        f"Sin cifra oficial para {PERIODO_MODELO}: se usa la estimación directa "
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
# predictor es el sintético ŷ_m = x_m'β̂ del benchmark seleccionado, sin contracción, con las
# covariables del municipio (no las del dominio). Su MSE es x_m'Cov(β̂)x_m + Â (Morales et al.,
# p. 441). Usar el β̂ estimado con dominios para predecir municipios supone que el modelo de
# enlace vale también para los municipios; por eso las covariables de los dominios A.M. se
# agregaron con el denominador de cada indicador: x_D y x_m son el mismo indicador sobre
# territorios distintos (preprocesamiento/shared/reglas_agregacion.py).
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
        f"del benchmark y no admiten predicción sintética: {municipios_sin_dato}. "
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
# Extrapolación (B20, shared/extrapolacion.py), con cualquier número de covariables:
# FUERA_DEL_RANGO si alguna covariable del municipio sale del [mín, máx] de los dominios;
# COMBINACION_ATIPICA si todas están dentro pero x_m'Cov(β̂)x_m supera el máximo de la muestra
# (Morales et al., p. 441). Se agregan la covariable responsable, la predicción con las
# covariables acotadas al rango y la parte de la predicción que viene de fuera (pp).
estado_ext = estado_extrapolacion(
    modelo_ganador.X,
    X_new,
    modelo_ganador.cov_beta,
    beta_ganador,
    covars_ganador,
)
for col in estado_ext.columns:
    df_pred[col] = estado_ext[col].to_numpy()
df_pred["EXTRAPOLA"] = df_pred["ESTADO_EXTRAPOLACION"] != ESTADO_DENTRO
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

# DBTITLE 1,10a. Extrapolación: rangos, responsables y sensibilidad (B20)
# β̂ se estimó solo con los dominios con encuesta y se aplica a municipios cuyas covariables
# pueden quedar fuera del rango que tomaron esos dominios (Benedetti et al., 2024, p. 144: en un
# área fuera de muestra el estimador es solo X_r β̂). Allí la predicción supone que la recta
# sigue valiendo donde el modelo no vio datos; el libro advierte que al predecir fuera de muestra
# se pueden obtener predicciones absurdas (Morales et al., p. 453) y el CV del sintético no mide
# ese riesgo (Molina, 2019, PDF 40-41). Esta celda lo documenta sin cambiar la tasa publicada:
#   1. rango de cada covariable en los dominios frente a los municipios;
#   2. estado de cada municipio, covariable responsable y parte de la predicción que viene de
#      fuera del rango (calculados en la celda 10);
#   3. sensibilidad: la predicción con las covariables acotadas al rango y el mín–máx al
#      reajustar el modelo quitando un dominio cada vez (como la sensibilidad de Cook de la
#      celda 8, pero para todos los dominios).
rangos = rangos_covariables(
    modelo_ganador.X, X_new, covars_ganador, df["NOMBRE_DOMINIO"].values
)
display(rangos)

fig = figura_rangos(modelo_ganador.X, X_new, covars_ganador)
if fig is not None:
    plt.show()

sens_mun, sens_dom = sensibilidad_quitar_dominio(
    modelo_ganador, FayHerriotClasico, X_new, df["NOMBRE_DOMINIO"].values
)
df_sens = pd.concat(
    [
        df_pred[
            [
                "PER",
                "MES",
                "CODIGO_DEPARTAMENTO",
                "DEPARTAMENTO",
                "CODIGO_MUNICIPIO",
                "MUNICIPIO",
                "ESTADO_EXTRAPOLACION",
                "COVARIABLES_FUERA",
                "COVARIABLE_PRINCIPAL",
                "RAZON_H",
                "PRED_SINTETICO",
                "CV_SINTETICO_PCT",
                "PRED_ACOTADA",
                "APORTE_EXTRAPOLADO_PP",
            ]
        ].reset_index(drop=True),
        sens_mun.drop(columns="PRED_BASE"),
    ],
    axis=1,
)

print(
    "Sensibilidad al quitar cada dominio (de mayor a menor cambio medio de las predicciones):"
)
display(sens_dom)
print("Municipios que extrapolan, de mayor a menor aporte de fuera del rango:")
display(
    df_sens[df_sens["ESTADO_EXTRAPOLACION"] != ESTADO_DENTRO].sort_values(
        "APORTE_EXTRAPOLADO_PP", key=np.abs, ascending=False
    )
)

max_directa = float(df[Y_COL].max())
fig = figura_sensibilidad(df_sens, max_directa)
if fig is not None:
    plt.show()

print(interpretar_extrapolacion(rangos, df_sens, sens_dom, max_directa))

spark.createDataFrame(
    rangos.assign(PER=int(df["PER"].iloc[0]), MES=int(df["MES"].iloc[0]))
).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    TBL_FH_RANGOS_COVARIABLES
)
spark.createDataFrame(df_sens).write.mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(TBL_FH_SENSIBILIDAD_EXTRAPOLACION)
print(
    f"Tablas escritas: {TBL_FH_RANGOS_COVARIABLES}, {TBL_FH_SENSIBILIDAD_EXTRAPOLACION}"
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sensibilidad a dominios individuales: dejar-un-dominio-fuera completo (G7-B18)
# MAGIC
# MAGIC Con 23 dominios, retirar uno puede mover los coeficientes (la revisión citó cambios de
# MAGIC ~37 % y ~47 % al retirar un solo dominio). Esta celda reajusta el benchmark (**incluida
# MAGIC Â**) 23 veces, una por dominio, y reporta:
# MAGIC
# MAGIC 1. **Coeficientes**: por β_j el mínimo y el máximo de β̂_j(-d) con el dominio que los produce,
# MAGIC    el cambio relativo máximo, el **cambio estandarizado Δβ/EE(β̂)** (estilo DFBETAS: el
# MAGIC    porcentual se infla cuando |β̂| es pequeño), los cambios de signo y los cruces del umbral
# MAGIC    de significancia. Los 3 dominios que más mueven cada coeficiente y un mapa de calor.
# MAGIC 2. **Predicciones**: EBLUP de los 22 dominios que quedan, la predicción sintética del
# MAGIC    dominio retirado (error de predecirlo como si no tuviera encuesta), la predicción
# MAGIC    sintética de los municipios objetivo (separando los que extrapolan, B20), Â y los
# MAGIC    cambios de clase de confiabilidad por CV.
# MAGIC
# MAGIC **Cómo leer.** Se marca un coeficiente como movido si cambia más de `LOAO_UMBRAL_CAMBIO_EE`
# MAGIC errores estándar y una predicción si cambia más de `LOAO_UMBRAL_PRED_PP` puntos
# MAGIC porcentuales; ambos son convenciones propias (`shared/config.py`). El LOAO es un
# MAGIC diagnóstico de sensibilidad: no interviene en la selección ni cambia las tasas publicadas.
# MAGIC Ni Morales et al. ni los artículos espaciales consultados tratan este análisis; sí respaldan
# MAGIC su lectura: en un área fuera de muestra el predictor es solo x'β̂ (Benedetti et al., 2024,
# MAGIC p. 144; Morales et al., p. 441), así que un β̂ que depende de un dominio mueve directamente
# MAGIC las predicciones de los municipios.

# COMMAND ----------

# DBTITLE 1,10a-bis. Dejar-un-dominio-fuera completo: coeficientes y predicciones (G7-B18)
nombres_municipio = (
    df_pred["MUNICIPIO"].astype(str)
    + " ("
    + df_pred["CODIGO_MUNICIPIO"].astype(str)
    + ")"
).to_numpy()
municipios_extrapolan = dict(zip(nombres_municipio, df_pred["EXTRAPOLA"].astype(bool)))

# `detalle_loo` y `resumen_loo` salen de la celda de estabilidad (8): mismos 23 reajustes.
detalle_pred_loao, por_dominio_loao = dejar_uno_fuera_predicciones(
    modelo_ganador,
    FayHerriotClasico,
    nombres_dominio,
    X_obj=X_new,
    nombres_obj=nombres_municipio,
)
df_influencia = resumen_influencia_dominios(
    detalle_loo,
    detalle_pred_loao,
    por_dominio_loao,
    municipios_extrapolan=municipios_extrapolan,
    umbral_ee=LOAO_UMBRAL_CAMBIO_EE,
    umbral_pp=LOAO_UMBRAL_PRED_PP,
)

print("Cada coeficiente: mínimo y máximo de β̂(-d) y dominio responsable")
display(
    resumen_loo[
        [
            "Parametro",
            "Beta_completo",
            "Beta_min",
            "Dominio_beta_min",
            "Beta_max",
            "Dominio_beta_max",
            "Cambio_pct_max_abs",
            "Cambio_en_EE_max_abs",
            "Dominio_max_cambio",
            "N_cambia_signo",
            "N_cruza_alfa",
        ]
    ].round(4)
)
print("Los 3 dominios que más mueven cada coeficiente:")
display(top_dominios_por_parametro(detalle_loo, k=3).round(4))

fig = figura_influencia(detalle_loo)
if fig is not None:
    display(fig)
    plt.close(fig)

print("Influencia de cada dominio en coeficientes y predicciones (de mayor a menor):")
display(df_influencia.round(4))
print(
    interpretar_influencia(
        resumen_loo, df_influencia, LOAO_UMBRAL_CAMBIO_EE, LOAO_UMBRAL_PRED_PP
    )
)

_periodo = {"PER": int(df["PER"].iloc[0]), "MES": int(df["MES"].iloc[0])}
for _tabla, _destino in (
    (detalle_loo.assign(**_periodo), TBL_FH_LOAO_COEFICIENTES),
    (detalle_pred_loao.assign(**_periodo), TBL_FH_LOAO_PREDICCIONES),
    (df_influencia.assign(**_periodo), TBL_FH_LOAO_DOMINIOS),
):
    (
        spark.createDataFrame(_tabla)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(_destino)
    )
    print(f"Tabla escrita: {_destino}")

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
# El peso es el denominador de la tasa (PEA ≈ PET). Las covariables del dominio se agregaron con
# el denominador de cada indicador, así que el agregado de los sintéticos municipales,
# Σ w_m x_m'β̂ / Σ w_m, no es exactamente el sintético del dominio x̄_D'β̂: λ_D − 1 combina la
# separación del dominio respecto de su predicción sintética y esa brecha de agregación, que se
# imprime abajo; la consistencia del ajuste sigue siendo exacta. Los municipios sin dominio padre
# no se ajustan: el único territorio de la GEIH que los contiene es el departamento, que con la
# ventana anual sí es representativo (Metodología GEIH v9, PDF 9), pero su estimación directa
# exige los registros sin AREA (resto de cabeceras y zona rural), que el proyecto decidió no usar.
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

# Brecha de agregación de cada dominio A.M.: sintético del dominio (x̄_D'β̂, con las covariables
# agregadas por su denominador) frente al promedio ponderado por la PET de los sintéticos de sus
# municipios, que es la base del λ_D. Solo se imprime.
sintetico_dominio = dict(
    zip(resultados_ganador["CODIGO_DOMINIO"], resultados_ganador["PRED_SINTETICO"])
)
pred_exacta = pd.Series(y_sintetico, index=df_pred.index)
for padre, grupo in df_pred[df_bm2["BENCHMARK"]].groupby("CODIGO_DOMINIO_PADRE"):
    agregado = float(
        (pred_exacta[grupo.index] * grupo["PESO_N2"]).sum() / grupo["PESO_N2"].sum()
    )
    sint_d = float(sintetico_dominio[padre])
    print(
        f"Dominio {padre}: x̄_D'β̂ = {sint_d:.4f} | Σw·x_m'β̂/Σw = {agregado:.4f} "
        f"| brecha = {agregado - sint_d:+.4f} pp | EBLUP ajustado = {objetivos_n2[padre]:.4f}"
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
        # Estado de extrapolación (B20): entra a la etiqueta CALIDAD_REPORTADA (B21).
        "ESTADO_EXTRAPOLACION": df_pred["ESTADO_EXTRAPOLACION"],
    }
)

# CONFIABILIDAD (solo por el CV), BASE_CV y CALIDAD_REPORTADA (B21, shared/consolidacion.py):
# la etiqueta que se cita es CALIDAD_REPORTADA; en los municipios dice «condicional al modelo»
# y, si extrapolan, «extrapolado».
dim_dominio = spark.table(TBL_DIM_DOMINIO).toPandas()
df_final = construir_tabla_final(
    tabla_dominios,
    tabla_municipios,
    dim_dominio,
    spark.table(TBL_DIM_DIVIPOLA).toPandas(),
)

# Marcas de aviso. Los dominios no extrapolan (están en la muestra de ajuste y definen el rango).
# Un mismo código puede ser dominio y municipio (76001), así que se une por NIVEL + CODIGO.
marcas = pd.concat(
    [
        resultados_ganador[["CODIGO_DOMINIO", "FUERA_DE_RANGO"]]
        .rename(columns={"CODIGO_DOMINIO": "CODIGO"})
        .assign(
            NIVEL="DOMINIO",
            EXTRAPOLA=False,
            APORTE_EXTRAPOLADO_PP=0.0,
        ),
        df_pred[
            [
                "CODIGO_MUNICIPIO",
                "FUERA_DE_RANGO",
                "EXTRAPOLA",
                "APORTE_EXTRAPOLADO_PP",
            ]
        ]
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
# MAGIC ## 11a. Calidad reportada de los municipios (B21)
# MAGIC
# MAGIC **Qué significa el CV de cada nivel.** En un dominio, el CV es el del EBLUP, que combina
# MAGIC la estimación directa de la encuesta con el modelo. En un municipio, el CV es el del
# MAGIC sintético x_m'β̂, y su MSE x_m'Cov(β̂)x_m + Â se deriva **suponiendo que el modelo es
# MAGIC correcto también en ese municipio** (Morales et al., p. 3 y p. 441). Ese CV no incluye la
# MAGIC incertidumbre por la selección del modelo, por una mala especificación ni por aplicar la
# MAGIC recta fuera de los datos con que se estimó: el sintético es sesgado si el modelo no se
# MAGIC cumple, aunque su varianza sea pequeña (Molina, 2019, PDF 37 y 41; Benedetti et al., 2024,
# MAGIC p. 144).
# MAGIC
# MAGIC **Cómo se reporta.** La tabla final conserva `CONFIABILIDAD` (solo por el CV) y agrega
# MAGIC `BASE_CV` y `CALIDAD_REPORTADA`, que es la que debe citarse:
# MAGIC
# MAGIC * dominio → la categoría por CV («Confiable»);
# MAGIC * municipio dentro del rango → «… · condicional al modelo»;
# MAGIC * municipio extrapolado (celda 10a) → «… · condicional al modelo · extrapolado».
# MAGIC
# MAGIC Así «Aceptable» en un municipio nunca se lee como una validación empírica. La etiqueta sale
# MAGIC del modelo ganador y de los umbrales de `config.py`: si cambian las covariables, el estado
# MAGIC de extrapolación y la etiqueta se recalculan solos. La tasa publicada no cambia.

# COMMAND ----------

# DBTITLE 1,11a. Calidad reportada de los municipios (B21)
# Resumen por estado de extrapolación y categoría por CV: muestra si el CV distingue o no a los
# municipios extrapolados (CV = RMSE / tasa predicha).
display(resumen_calidad(df_pred))

print("Etiquetas publicadas en la tabla final (CALIDAD_REPORTADA):")
display(
    df_final.groupby(["NIVEL", "BASE_CV", "CALIDAD_REPORTADA"])
    .size()
    .rename("N")
    .reset_index()
)
print(interpretar_calidad(df_pred))

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
