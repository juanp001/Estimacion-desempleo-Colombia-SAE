# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Diagnóstico y selección final de covariables
# MAGIC
# MAGIC Versión revisada de `Análisis exploratorio`. El notebook original permanece sin
# MAGIC cambios; este escribe en tablas con sufijo `_rev` para poder compararlos.
# MAGIC
# MAGIC Este notebook **decide**. La caracterización de los datos se hizo antes, en
# MAGIC `analisis_descriptivo_rev`, y no se repite aquí.
# MAGIC
# MAGIC ## Qué cambia frente a la versión original
# MAGIC
# MAGIC La versión original recorría siete etapas y cerraba con un ranking compuesto
# MAGIC `C = (1-α)·Q + α·(L/3)`. Se retiran tres etapas y el ranking:
# MAGIC
# MAGIC | Procedimiento original | Decisión | Motivo |
# MAGIC |---|---|---|
# MAGIC | Etapa 1: sensibilidad al umbral de correlación | **Eliminada** | Contaba cuántas covariables superaban umbrales sobre un conjunto que ya había sido recortado por ese mismo umbral. Era tautológica por construcción, y el umbral que la motivaba ya no existe. |
# MAGIC | Etapa 3: contraste de Shapiro-Wilk sobre las covariables | **Eliminado** | El modelo Fay-Herriot supone normalidad de los efectos aleatorios y de los errores de muestreo, no de las covariables. No producía ninguna decisión y con 23 dominios carece de potencia. La forma de las distribuciones se describe con asimetría y diagramas de caja en el análisis descriptivo. |
# MAGIC | Etapa 6: índice de Moran sobre la respuesta cruda | **Eliminado** | El supuesto de independencia del modelo es sobre los residuos. Calcularlo dos veces duplicaba el procedimiento sin añadir una decisión; se conserva únicamente el contraste sobre residuos. |
# MAGIC | Etapa 5: influencia y estabilidad | **Conservado y unificado** | Distancia de Cook y exclusión de dominios pasan a ser las dos evidencias de un único criterio de robustez, en lugar de dos componentes independientes de un promedio. La exclusión recorre los 23 dominios en vez de cinco elegidos a mano. |
# MAGIC | Etapa 7: ranking compuesto C y Q | **Sustituido** | Pesos y topes arbitrarios; tres de las cinco componentes de Q medían lo mismo; la componente de no redundancia dependía de qué otras candidatas estuvieran presentes; y el resultado lo fijaba en realidad la restricción de una covariable por dimensión, no el score. |
# MAGIC | Restricción de una covariable por dimensión | **Eliminada** | Era la regla que determinaba el conjunto ganador sin tener fundamento estadístico. La cobertura de dimensiones distintas pasa a ser consecuencia del criterio de redundancia. |
# MAGIC
# MAGIC ## Procedimiento de selección
# MAGIC
# MAGIC ```
# MAGIC candidatas conceptualmente elegibles
# MAGIC   → 1. robustez:     se descarta lo que depende de un solo dominio
# MAGIC   → 2. redundancia:  un representante por grupo de covariables equivalentes
# MAGIC   → 3. AIC:          búsqueda exhaustiva de subconjuntos de tamaño <= 4
# MAGIC   → 4. verificación: multicolinealidad, signo de los coeficientes, independencia espacial
# MAGIC ```
# MAGIC
# MAGIC Cada paso descarta por una razón única y verificable, y el recorrido completo de cada
# MAGIC covariable queda registrado en `trazabilidad_covariables_rev`.
# MAGIC
# MAGIC ## Sobre el uso repetido de los mismos datos
# MAGIC
# MAGIC Elegir por AIC utiliza los mismos 23 dominios que ajustan el modelo. Esto se declara
# MAGIC explícitamente y no se presenta como evidencia confirmatoria. La diferencia respecto
# MAGIC del pre-filtro por correlación que se eliminó es sustantiva: aquél descartaba
# MAGIC covariables por su asociación marginal con la respuesta y después leía esa misma
# MAGIC asociación como si fuera un hallazgo; aquí el conjunto de partida se fijó por criterio
# MAGIC conceptual, y el AIC solo compara especificaciones entre sí.
# MAGIC
# MAGIC ## Salidas
# MAGIC
# MAGIC * `tesis.preprocesamiento.diagnosticos_covariables_rev`
# MAGIC * `tesis.preprocesamiento.busqueda_aic_rev`
# MAGIC * `tesis.preprocesamiento.trazabilidad_covariables_rev`
# MAGIC * `tesis.preprocesamiento.covariables_seleccionadas_rev`
# MAGIC * Figuras en el volumen `figuras_eda`, con prefijo `eda_`.

# COMMAND ----------

# DBTITLE 1,Setup: rutas, imports y carga de datos
import os
import sys

import numpy as np
import pandas as pd
from pyspark.sql import functions as F


def _directorio_codigo() -> str:
    """Ruta absoluta de `code/`, tanto en ejecución interactiva como en un job."""
    try:
        contexto = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
        return "/Workspace" + os.path.dirname(os.path.dirname(contexto.notebookPath().get()))
    except Exception:
        return os.path.dirname(os.getcwd())


CODE_DIR = _directorio_codigo()
# `code/` permite importar por ruta completa (preprocesamiento.…, analisis.…);
# `code/modelo` resuelve el `shared.…` interno de la implementación del modelo, que se
# reutiliza tal cual para la búsqueda por AIC.
for _ruta in (CODE_DIR, os.path.join(CODE_DIR, "modelo")):
    if _ruta not in sys.path:
        sys.path.insert(0, _ruta)

from preprocesamiento.shared.config_rev import *
from analisis.shared_rev import descriptivos as desc
from analisis.shared_rev import diagnosticos as diag
from analisis.shared_rev import seleccion as sel
from analisis.shared_rev.catalogo_literatura import resolver_catalogo, mapas_catalogo
from shared.fay_herriot import FayHerriotClasico

# ── Carga ─────────────────────────────────────────────────────────────────────
df_full = spark.table(TBL_PREFILTRADAS_REV)
indicadores_dict = {
    fila["CODIGO_INDICADOR"]: fila["INDICADOR"]
    for fila in spark.table(TBL_DIM_INDICADORES)
    .select("CODIGO_INDICADOR", "INDICADOR").collect()
}

cols_covariables = [c for c in df_full.columns if c not in METADATA_COLS]
df_cov_spark = df_full.select(cols_covariables)
for nombre in [f.name for f in df_cov_spark.schema.fields if str(f.dataType) == "StringType()"]:
    df_cov_spark = df_cov_spark.withColumn(nombre, F.col(nombre).cast("double"))

df_meta = df_full.select(METADATA_COLS).toPandas()
df_pd   = df_cov_spark.toPandas()

Y         = df_meta[VARIABLE_OBJETIVO].values
entidades = df_meta["MUNICIPIO"].values

catalogo_activo, reporte_catalogo = resolver_catalogo(indicadores_dict, list(df_pd.columns))
CANDIDATAS, ALIAS, LITERATURA, DIMENSION = mapas_catalogo(catalogo_activo)
df_cand = df_pd[CANDIDATAS].copy()

print(f"Dominios: {len(Y)}  |  Candidatas conceptualmente elegibles: {len(CANDIDATAS)}")

# COMMAND ----------

# MAGIC %md
# MAGIC # 1. Precisión de las asociaciones observadas
# MAGIC
# MAGIC Antes de decidir, se cuantifica cuánta incertidumbre tiene cada correlación. Con 23
# MAGIC dominios el error estándar de un coeficiente de correlación es grande, y un valor
# MAGIC puntual comunica más certeza de la que hay. El intervalo bootstrap hace visible ese
# MAGIC margen: un intervalo que contiene el cero indica que la evidencia no determina
# MAGIC siquiera el signo de la asociación.
# MAGIC
# MAGIC Se reportan dos intervalos que se calculan de forma independiente: el bootstrap de
# MAGIC percentiles y el de la transformación de Fisher. El motivo es que el bootstrap pierde
# MAGIC fiabilidad cuando la relación está dominada por un único dominio de gran influencia: al
# MAGIC remuestrear, la anchura del intervalo pasa a depender de cuántas veces se extrae ese
# MAGIC punto y puede quedar artificialmente estrecha, llegando a excluir el cero para
# MAGIC correlaciones débiles. Cuando ambos intervalos discrepan, la conclusión no es que uno
# MAGIC sea correcto, sino que la incertidumbre de ese coeficiente no está bien caracterizada y
# MAGIC su evidencia debe considerarse débil con independencia de la magnitud observada.
# MAGIC
# MAGIC No se reportan p-valores. Se evalúan varias covariables sin corrección por
# MAGIC multiplicidad y su interpretación nominal no sería válida; los intervalos comunican la
# MAGIC misma información sin sugerir una precisión inexistente.

# COMMAND ----------

# DBTITLE 1,Intervalos bootstrap de la correlación con la respuesta
filas_ic = []
for codigo in CANDIDATAS:
    x = df_cand[codigo].values
    inferior, superior = diag.ic_bootstrap_pearson(
        x, Y, n_replicas=BOOTSTRAP_CORR_REPLICAS, semilla=BOOTSTRAP_CORR_SEED
    )
    f_inferior, f_superior = diag.ic_fisher_pearson(x, Y)
    r = float(np.corrcoef(x, Y)[0, 1])

    cruza_bootstrap = inferior <= 0 <= superior
    cruza_fisher    = f_inferior <= 0 <= f_superior
    # Los dos intervalos deben contar la misma historia. Si discrepan, la incertidumbre del
    # coeficiente no está bien caracterizada y la evidencia se considera débil.
    if cruza_bootstrap == cruza_fisher:
        lectura = "sí" if cruza_bootstrap else "no"
    else:
        lectura = "discrepan"

    filas_ic.append({
        "Alias":            ALIAS[codigo],
        "Codigo":           codigo,
        "Pearson_r":        round(r, 3),
        "IC_boot_inf":      round(inferior, 3),
        "IC_boot_sup":      round(superior, 3),
        "IC_fisher_inf":    round(f_inferior, 3),
        "IC_fisher_sup":    round(f_superior, 3),
        "Contiene_cero":    lectura,
    })

df_ic = pd.DataFrame(filas_ic).sort_values("Pearson_r", key=abs, ascending=False)
display(spark.createDataFrame(df_ic))

n_discrepan = int((df_ic["Contiene_cero"] == "discrepan").sum())
if n_discrepan:
    print(f"\n{n_discrepan} covariables con intervalos discrepantes entre bootstrap y Fisher.")
    print("En ellas la anchura del intervalo bootstrap depende de cuántas veces se remuestrea")
    print("un dominio de gran influencia, por lo que ninguno de los dos intervalos caracteriza")
    print("bien la incertidumbre. Su evidencia se considera débil con independencia de |r|.")

# COMMAND ----------

# MAGIC %md
# MAGIC # 2. Robustez: ¿la asociación depende de un solo dominio?
# MAGIC
# MAGIC Con 23 observaciones un único territorio puede determinar la pendiente de una
# MAGIC regresión. Se combinan dos evidencias que deben cumplirse **a la vez** para descartar:
# MAGIC
# MAGIC * la distancia de Cook señala que un dominio domina la regresión (umbral 4/n);
# MAGIC * al excluir ese dominio, la correlación cambia más de `UMBRAL_DELTA_LOO` o invierte
# MAGIC   su signo.
# MAGIC
# MAGIC Exigir ambas evita descartar una covariable por tener un valor extremo que, siendo
# MAGIC grande, no altera la relación. La exclusión recorre los 23 dominios, no un subconjunto
# MAGIC elegido por inspección visual como en la versión original.
# MAGIC
# MAGIC **Ninguna observación se elimina.** Los dominios extremos son territorios reales
# MAGIC —capitales de gran tamaño, ciudades con historia de conflicto, periferias con baja
# MAGIC cobertura— y no errores de medición. La consecuencia recae sobre la covariable, que
# MAGIC deja de considerarse utilizable, no sobre el dato.

# COMMAND ----------

# DBTITLE 1,Influencia por dominio (distancia de Cook)
df_influencia = diag.influencia_por_covariable(df_cand, CANDIDATAS, Y, entidades, alias=ALIAS)
display(spark.createDataFrame(df_influencia))

# COMMAND ----------

# DBTITLE 1,Estabilidad de la asociación al excluir cada dominio
df_estabilidad = diag.estabilidad_loo(df_cand, CANDIDATAS, Y, entidades, alias=ALIAS)
display(spark.createDataFrame(df_estabilidad))

# COMMAND ----------

# DBTITLE 1,Figura: plano de robustez
fig = diag.figura_robustez(df_influencia, df_estabilidad, umbral_delta=UMBRAL_DELTA_LOO)
desc.guardar_figura(fig, "eda_robustez", VOLUMEN_FIGURAS)
display(fig)

# COMMAND ----------

# DBTITLE 1,Filtro de robustez
supervivientes, df_robustez = sel.filtrar_por_robustez(
    CANDIDATAS, df_influencia, df_estabilidad,
    umbral_delta=UMBRAL_DELTA_LOO, alias=ALIAS,
)
display(spark.createDataFrame(df_robustez))

# COMMAND ----------

# MAGIC %md
# MAGIC # 3. Redundancia: un representante por grupo de covariables equivalentes
# MAGIC
# MAGIC Los bloques identificados en el análisis multivariado se resuelven aquí. Dentro de
# MAGIC cada grupo de covariables con correlación de magnitud mayor o igual que
# MAGIC `UMBRAL_REDUNDANCIA` entra una sola, elegida por un desempate determinista: mayor
# MAGIC respaldo conceptual, y a igualdad de respaldo, la asociación menos dependiente de un
# MAGIC dominio individual.
# MAGIC
# MAGIC Ninguno de los dos criterios usa la magnitud de la correlación con la respuesta, de
# MAGIC modo que resolver la redundancia no reintroduce selección sobre la variable dependiente.
# MAGIC
# MAGIC Esta es también la razón por la que desaparece la restricción de una covariable por
# MAGIC dimensión conceptual: cubrir dimensiones distintas deja de ser una regla impuesta y
# MAGIC pasa a ser la consecuencia natural de no admitir dos covariables que midan lo mismo.

# COMMAND ----------

# DBTITLE 1,Resolución de redundancia sobre las covariables robustas
cook_por_codigo = df_influencia.set_index("Codigo")["Cook_max"].to_dict()

robustas, df_redundancia = sel.resolver_redundancia(
    df_cand, supervivientes,
    literatura=LITERATURA,
    influencia=cook_por_codigo,
    alias=ALIAS,
    umbral=UMBRAL_REDUNDANCIA,
)
display(spark.createDataFrame(df_redundancia))

# COMMAND ----------

# MAGIC %md
# MAGIC # 4. Selección final por criterio de información
# MAGIC
# MAGIC Sobre las covariables que sobreviven se ajustan **todas** las especificaciones del
# MAGIC modelo Fay-Herriot de hasta `P_MAXIMO` covariables y se ordenan por AIC. El límite
# MAGIC proviene de la cota de parsimonia del proyecto: con 23 dominios el modelo admite del
# MAGIC orden de cuatro covariables más el intercepto.
# MAGIC
# MAGIC La búsqueda es exhaustiva y no por pasos: no depende del orden de entrada y no deja
# MAGIC combinaciones sin evaluar. Con esta cantidad de candidatas son unos pocos cientos de
# MAGIC ajustes, y el resultado es reconstruible en su totalidad.
# MAGIC
# MAGIC Se usa la implementación del modelo que ya existe en `modelo/shared/fay_herriot.py`,
# MAGIC sin modificarla: la selección se hace con el mismo estimador que después producirá las
# MAGIC estimaciones, no con una regresión auxiliar distinta.

# COMMAND ----------

# DBTITLE 1,Búsqueda exhaustiva de especificaciones
df_modelo = pd.concat([df_meta.reset_index(drop=True), df_cand.reset_index(drop=True)], axis=1)

busqueda = sel.busqueda_exhaustiva_aic(
    df_modelo, robustas, FayHerriotClasico,
    y_col=VARIABLE_OBJETIVO, se_col="SE_BOOTSTRAP_PCT",
    p_maximo=P_MAXIMO, alias=ALIAS,
)
display(spark.createDataFrame(busqueda.head(25)))

# COMMAND ----------

# DBTITLE 1,Figura: comparación de especificaciones por AIC
fig = sel.figura_aic(busqueda)
desc.guardar_figura(fig, "eda_busqueda_aic", VOLUMEN_FIGURAS)
display(fig)

# COMMAND ----------

# DBTITLE 1,Conjunto seleccionado
# Entre las especificaciones que el AIC declara equivalentes se toma la más parsimoniosa, en
# lugar de la de menor AIC sin más: con diferencias de unas centésimas, elegir por el valor
# puntual haría depender el resultado de ruido que el propio criterio considera irrelevante.
elegida = sel.elegir_con_parsimonia(busqueda, delta_max=DELTA_AIC_EQUIVALENTE)
SELECCIONADAS = elegida["Codigos"].split(",")

print("\nCovariables seleccionadas:")
for codigo in SELECCIONADAS:
    print(f"  · {ALIAS[codigo]:20s} {indicadores_dict.get(codigo, codigo)[:60]}")

# COMMAND ----------

# MAGIC %md
# MAGIC # 5. Verificación del conjunto elegido
# MAGIC
# MAGIC Tres comprobaciones, cada una con una consecuencia declarada de antemano:
# MAGIC
# MAGIC 1. **Multicolinealidad.** Si algún factor de inflación de la varianza supera
# MAGIC    `VIF_MAXIMO`, el conjunto no es utilizable y se toma la siguiente especificación
# MAGIC    del orden por AIC. Se calcula sobre el conjunto elegido y no sobre el universo de
# MAGIC    candidatas: con 23 dominios, un sistema con muchas más covariables que grados de
# MAGIC    libertad produce un factor sin sentido.
# MAGIC 2. **Signo de los coeficientes.** Se contrasta el signo estimado con el mecanismo
# MAGIC    declarado en el catálogo conceptual. Un signo contrario al esperado no invalida el
# MAGIC    modelo, pero debe explicarse en el documento y no pasarse por alto.
# MAGIC 3. **Independencia espacial.** El índice de Moran sobre los residuos contrasta el
# MAGIC    supuesto de errores independientes entre dominios del modelo Fay-Herriot estándar.
# MAGIC    Si se rechaza, el supuesto queda comprometido y debe reportarse como limitación.

# COMMAND ----------

# DBTITLE 1,Multicolinealidad del conjunto elegido
df_vif = diag.vif_conjunto(df_cand, SELECCIONADAS, alias=ALIAS)
display(spark.createDataFrame(df_vif))

vif_maximo_observado = float(df_vif["VIF"].max())
print(f"VIF máximo: {vif_maximo_observado:.3f}  (umbral: {VIF_MAXIMO})")
if vif_maximo_observado > VIF_MAXIMO:
    raise ValueError(
        f"El conjunto elegido supera el umbral de multicolinealidad "
        f"(VIF {vif_maximo_observado:.3f} > {VIF_MAXIMO}). Revisar la siguiente "
        f"especificación del orden por AIC antes de continuar."
    )

# COMMAND ----------

# DBTITLE 1,Coeficientes y signo esperado
modelo_final = FayHerriotClasico(SELECCIONADAS, df_modelo, VARIABLE_OBJETIVO, "SE_BOOTSTRAP_PCT")
modelo_final.ajustar()

df_coef = pd.DataFrame({
    "Termino":  ["Intercepto"] + [ALIAS[c] for c in SELECCIONADAS],
    "Codigo":   ["—"] + SELECCIONADAS,
    "Dimension": ["—"] + [DIMENSION[c] for c in SELECCIONADAS],
    "Coeficiente": np.round(modelo_final.beta_hat, 4),
    "Error_estandar": np.round(modelo_final.se_beta, 4),
    "Signo": ["—"] + ["positivo" if b > 0 else "negativo" for b in modelo_final.beta_hat[1:]],
})
display(spark.createDataFrame(df_coef))
print(f"R² del predictor sintético: {modelo_final.r2:.4f}  |  AIC: {modelo_final.aic:.3f}")

# COMMAND ----------

# DBTITLE 1,Independencia espacial de los residuos
df_coords = (
    df_meta[["CODIGO_MUNICIPIO"]]
    .merge(
        spark.table("tesis.dim.dim_divipola")
        .filter(F.col("CODIGO_MUNICIPIO").isin(df_meta["CODIGO_MUNICIPIO"].tolist()))
        .select("CODIGO_MUNICIPIO", "LATITUD", "LONGITUD").toPandas(),
        on="CODIGO_MUNICIPIO", how="left",
    )
)
coordenadas = df_coords[["LATITUD", "LONGITUD"]].values.astype(float)

if np.isnan(coordenadas).any():
    faltantes = df_coords.loc[np.isnan(coordenadas).any(axis=1), "CODIGO_MUNICIPIO"].tolist()
    raise ValueError(
        f"Faltan coordenadas en dim_divipola para los municipios {faltantes}. "
        f"Imputarlas con la media del grupo, como hacía la versión original, sitúa esos "
        f"dominios en el centroide del conjunto y distorsiona la matriz de pesos."
    )

W = diag.matriz_pesos_distancia_inversa(coordenadas)
resultado_moran = diag.moran_permutacion(
    modelo_final.residuals, W,
    n_permutaciones=MORAN_PERMUTACIONES, semilla=MORAN_SEED,
)

print(f"Índice de Moran sobre los residuos: {resultado_moran['I_observado']:.4f}")
print(f"Valor esperado bajo independencia:  {resultado_moran['E_bajo_H0']:.4f}")
print(f"p-valor por permutación:            {resultado_moran['p_valor']:.4f}")
if resultado_moran["p_valor"] < 0.05:
    print("→ Se rechaza la independencia espacial de los residuos. El supuesto del modelo")
    print("  Fay-Herriot estándar queda comprometido y debe reportarse como limitación.")
else:
    print("→ No se rechaza la independencia espacial de los residuos.")

fig = diag.figura_moran(resultado_moran, titulo="Índice de Moran sobre los residuos del modelo")
desc.guardar_figura(fig, "eda_moran_residuos", VOLUMEN_FIGURAS)
display(fig)

# COMMAND ----------

# DBTITLE 1,Figura: correlación entre las covariables seleccionadas
fig, _ = desc.figura_correlacion_agrupada(
    df_cand, SELECCIONADAS, alias=ALIAS,
    titulo="Correlación entre las covariables seleccionadas",
)
desc.guardar_figura(fig, "eda_correlacion_finales", VOLUMEN_FIGURAS)
display(fig)

# COMMAND ----------

# MAGIC %md
# MAGIC # 6. Trazabilidad
# MAGIC
# MAGIC Una fila por entrada del catálogo conceptual, con su recorrido completo: si llegó a
# MAGIC candidata, qué mostró cada diagnóstico, en qué paso quedó fuera y por qué motivo. Las
# MAGIC covariables descartadas durante el pre-filtrado no aparecen aquí una a una porque su
# MAGIC exclusión se explica por el criterio del filtro, registrado en
# MAGIC `cascada_prefiltrado_rev` y en el reporte de variabilidad.

# COMMAND ----------

# DBTITLE 1,Tabla maestra de trazabilidad
influencia_idx  = df_influencia.set_index("Codigo")
estabilidad_idx = df_estabilidad.set_index("Codigo")
redundancia_idx = df_redundancia.set_index("Codigo")
robustez_idx    = df_robustez.set_index("Codigo")
ic_idx          = df_ic.set_index("Codigo")

filas_traza = []
for _, entrada in reporte_catalogo.iterrows():
    codigo = entrada["Codigo"]
    fila = {
        "Alias":      entrada["Alias"],
        "Codigo":     codigo,
        "Dimension":  entrada["Dimension"],
        "L":          entrada["L"],
        "Prefiltrado": entrada["Estado"],
        "Pearson_r":  None, "IC_contiene_cero": None,
        "Cook_max":   None, "Delta_LOO_max": None,
        "Grupo_redundancia": None, "Representante": None,
        "Robustez":   None,
        "Decision_final": None, "Motivo_final": None,
    }

    if entrada["Estado"] != "activa":
        fila["Decision_final"] = "no evaluada"
        fila["Motivo_final"] = entrada["Estado"]
        filas_traza.append(fila)
        continue

    fila["Pearson_r"]        = float(ic_idx.loc[codigo, "Pearson_r"])
    fila["IC_contiene_cero"] = ic_idx.loc[codigo, "Contiene_cero"]
    fila["Cook_max"]         = float(influencia_idx.loc[codigo, "Cook_max"])
    fila["Delta_LOO_max"]    = float(estabilidad_idx.loc[codigo, "Delta_max_abs"])
    fila["Robustez"] = robustez_idx.loc[codigo, "Decision"]

    if fila["Robustez"] == "descartada":
        # La redundancia solo se evalúa sobre las covariables robustas, de modo que estas no
        # llegan a tener grupo asignado.
        fila["Grupo_redundancia"] = None
        fila["Representante"] = "no evaluada"
        fila["Decision_final"] = "descartada"
        fila["Motivo_final"] = robustez_idx.loc[codigo, "Motivo"]
    else:
        fila["Grupo_redundancia"] = int(redundancia_idx.loc[codigo, "Grupo"])
        fila["Representante"] = redundancia_idx.loc[codigo, "Representante"]
        if fila["Representante"] == "no":
            fila["Decision_final"] = "descartada"
            fila["Motivo_final"] = redundancia_idx.loc[codigo, "Motivo"]
        elif codigo in SELECCIONADAS:
            fila["Decision_final"] = "seleccionada"
            fila["Motivo_final"] = ("integra la especificación elegida entre las equivalentes por "
                                    f"AIC de hasta {P_MAXIMO} covariables")
        else:
            fila["Decision_final"] = "no seleccionada"
            fila["Motivo_final"] = ("candidata válida; no integra la especificación elegida bajo "
                                    "la cota de parsimonia")

    filas_traza.append(fila)

df_trazabilidad = pd.DataFrame(filas_traza)
display(spark.createDataFrame(df_trazabilidad))

# COMMAND ----------

# MAGIC %md
# MAGIC Las covariables marcadas como «no seleccionada» no son inservibles: superaron el
# MAGIC criterio conceptual, no son redundantes con otra y su asociación con el desempleo es
# MAGIC estable. Quedan fuera únicamente porque la cota de parsimonia limita el número de
# MAGIC covariables y otra especificación ajusta mejor. Son candidatas legítimas si el número
# MAGIC de dominios con encuesta aumenta.

# COMMAND ----------

# DBTITLE 1,Escritura de las tablas de diagnóstico y trazabilidad
df_diagnosticos = (
    df_ic.merge(df_influencia.drop(columns=["Alias"]), on="Codigo")
         .merge(df_estabilidad.drop(columns=["Alias"]), on="Codigo")
)

# La verificación del conjunto elegido se persiste para que el capítulo de resultados pueda
# citar sus cifras sin recalcularlas: factor de inflación de la varianza, coeficiente y signo
# de cada covariable, y el contraste de independencia espacial sobre los residuos.
df_verificacion = df_coef.merge(
    df_vif[["Codigo", "VIF"]], on="Codigo", how="left"
).assign(
    Moran_I=round(resultado_moran["I_observado"], 4),
    Moran_E_H0=round(resultado_moran["E_bajo_H0"], 4),
    Moran_p=round(resultado_moran["p_valor"], 4),
    R2_sintetico=round(float(modelo_final.r2), 4),
    AIC=round(float(modelo_final.aic), 3),
)

for tabla, destino in [
    (df_diagnosticos,  TBL_DIAGNOSTICOS_REV),
    (busqueda,         TBL_SELECCION_AIC_REV),
    (df_trazabilidad,  TBL_TRAZABILIDAD_REV),
    (df_verificacion,  TBL_VERIFICACION_REV),
    (df_redundancia,   TBL_REDUNDANCIA_REV),
    (df_robustez,      TBL_ROBUSTEZ_REV),
]:
    (spark.createDataFrame(tabla)
     .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(destino))
    print(f"Tabla escrita: {destino}")

# COMMAND ----------

# DBTITLE 1,Escritura de las bases de candidatas y de covariables seleccionadas
# Se escriben dos tablas con propósitos distintos:
#  · candidatas: todas las covariables que llegaron a la búsqueda exhaustiva. El notebook del
#    modelo la necesita porque las especificaciones que compara no se limitan a las del
#    conjunto ganador.
#  · seleccionadas: únicamente las covariables del conjunto elegido, conservando el
#    significado que esta tabla tenía en la versión original.
def escribir_base(codigos, destino):
    """Escribe los metadatos más las covariables indicadas, renombradas a su alias."""
    cols = METADATA_COLS + [c for c in codigos if c not in METADATA_COLS]
    base = df_full.select(cols)
    for codigo in codigos:
        base = base.withColumnRenamed(codigo, ALIAS[codigo])
    base.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(destino)
    print(f"Tabla escrita: {destino}  ({[ALIAS[c] for c in codigos]})")
    return base


escribir_base(robustas, TBL_CANDIDATAS_REV)
display(escribir_base(SELECCIONADAS, TBL_SELECCIONADAS_REV))

