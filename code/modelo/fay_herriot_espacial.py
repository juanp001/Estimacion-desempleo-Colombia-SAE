# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Modelo Fay-Herriot espacial (SEBLUP)
# MAGIC
# MAGIC Extiende el Fay-Herriot clásico (`fay_herriot.py`) con **autocorrelación espacial** en los
# MAGIC efectos aleatorios: `u = ρWu + v` (SAR; Morales et al., 2021, §18.2, pp. 490-494). Con ρ = 0
# MAGIC se recupera el modelo clásico, así que la pregunta del notebook es si los datos justifican
# MAGIC ρ ≠ 0 y si eso mejora la predicción en los municipios sin encuesta.
# MAGIC
# MAGIC **Dificultad central.** Los 23 dominios con encuesta son ciudades o áreas metropolitanas
# MAGIC dispersas por el país, y los municipios objetivo (Cauca y Valle) no son contiguos a ellos.
# MAGIC Por eso (a) **ρ solo se puede estimar con los dominios de la GEIH**, que son los únicos con
# MAGIC dato, (b) **W se define sobre todas las unidades** (con y sin encuesta) para poder
# MAGIC predecir, y (c) W se construye por **distancia** entre centroides (kNN o distancia
# MAGIC inversa), no por contigüidad.
# MAGIC
# MAGIC Pasos:
# MAGIC 1. Carga de dominios con encuesta, municipios objetivo y coordenadas.
# MAGIC 2. Diagnóstico de vecindad: ¿qué tan cerca está cada objetivo de un dominio con encuesta?
# MAGIC 3. Fay-Herriot clásico de referencia (mismas covariables del benchmark clásico seleccionado).
# MAGIC 4. I de Moran de los residuos del clásico, por escenario de W.
# MAGIC 5. Ajuste del SEBLUP por escenario y estructura, comparación contra el clásico (LRT de ρ = 0,
# MAGIC    AIC) y cuadro de coeficientes del clásico frente al espacial, más el I de Moran de los
# MAGIC    residuos del SEBLUP.
# MAGIC 6. Perfil de verosimilitud de ρ: ¿está identificado?
# MAGIC 7. Validación dejar-un-dominio-fuera: ¿predice mejor un municipio no visto?
# MAGIC 8. Decisión, sensibilidad de ρ̂ al centroide de los A.M. y a los nodos sin dato, y mapa de
# MAGIC    residuos.
# MAGIC 9. Predicción para los municipios objetivo (con MSE bootstrap): los municipios de un dominio
# MAGIC    A.M. (Cali, Yumbo) se predicen como subáreas de su nodo y se les aplica el benchmarking de
# MAGIC    nivel 2, como en el clásico.
# MAGIC 10. Exportar tablas (`tesis.modelo.fhe_*`) y figuras (`fhe_*` en el volumen de figuras del
# MAGIC    modelo, `VOLUMEN_FIGURAS_MODELO`).
# MAGIC
# MAGIC La lógica vive en `shared/matriz_proximidad.py`, `shared/fay_herriot_espacial.py` y
# MAGIC `shared/figuras_espacial.py`; la explicación completa y los resultados están en
# MAGIC `docs/fay_herriot_espacial.md`.

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


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


CODE_DIR = globals().get("CODE_DIR") or _directorio_codigo()
for _ruta in (CODE_DIR, os.path.join(CODE_DIR, "modelo")):
    if _ruta not in sys.path:
        sys.path.insert(0, _ruta)

from shared.config import *
from shared.datos_modelo import alias_desde_catalogo
from shared.fay_herriot import FayHerriotClasico
from shared.cuadro_comparativo import (
    construir_cuadro_comparativo,
    construir_cuadro_coeficientes,
)
from shared.fay_herriot_espacial import (
    FayHerriotEspacial,
    validacion_dejar_uno_fuera,
    metricas_validacion,
    NOTA_VALIDACION_OPTIMISTA,
)
from shared.matriz_proximidad import (
    distancias_haversine,
    estandarizar_filas,
    filas_moran,
    proximidad_escenario,
    proximidad_total as proximidad_total_compartida,
    resumen_vecindad,
)
from shared.figuras_espacial import (
    figura_perfil_rho,
    figura_validacion,
    figura_mapa_prediccion,
    figura_mapa_residuos,
)
from shared.figuras import guardar_figura as guardar_png
from shared.consolidacion import (
    clasificar_confiabilidad,
    etiqueta_calidad,
)
from shared.diagnosticos import marca_fuera_de_rango
from shared.extrapolacion import estado_extrapolacion
from shared.benchmarking import benchmark_nivel1, benchmark_nivel2, promedio_ponderado
from shared.prediccion_espacial import predecir_subareas
from shared.sensibilidad_espacial import (
    sensibilidad_centroide,
    sensibilidad_rho_objetivos,
)

import warnings

warnings.filterwarnings("ignore")


def mostrar(objeto):
    """Muestra un DataFrame (display en Databricks, print si no existe `display`).

    Args:
        objeto (pd.DataFrame): Tabla a mostrar.
    """
    try:
        display(objeto)
    except NameError:
        print(objeto.to_string())


def guardar_figura(fig, nombre: str) -> None:
    """Guarda una figura en el volumen de figuras del modelo (prefijo `fhe_`) y la muestra.

    Misma regla que el clásico (R-45): cada figura se muestra y se guarda en
    `VOLUMEN_FIGURAS_MODELO`. Si el volumen no existe solo avisa; la figura se muestra de todos
    modos.

    Args:
        fig (plt.Figure): Figura a guardar.
        nombre (str): Nombre del archivo sin extensión (se antepone `fhe_`).
    """
    guardar_png(fig, nombre, "fhe_", VOLUMEN_FIGURAS_MODELO)
    try:
        display(fig)
    except NameError:
        pass
    plt.close(fig)


# COMMAND ----------

# DBTITLE 1,1. Carga de dominios con encuesta, objetivos y coordenadas
# MAGIC %md
# MAGIC ## 1. Datos
# MAGIC
# MAGIC * **Covariables**: las del benchmark seleccionado del Fay-Herriot clásico (tabla
# MAGIC   `fh_coeficientes`), para que la única diferencia entre los dos modelos sea la estructura
# MAGIC   de los efectos aleatorios.
# MAGIC * **Dominios con encuesta**: `covariables_seleccionadas`. Un dominio puede ser un área
# MAGIC   metropolitana (varios municipios); se ubica en la **coordenada de su municipio capital**
# MAGIC   (`CODIGO_DOMINIO`), que es la decisión más simple y se declara como limitación.
# MAGIC * **Objetivos**: `municipios_sin_encuesta` (los mismos 83 que el clásico). Los municipios que
# MAGIC   pertenecen a un dominio A.M. (`CODIGO_DOMINIO_PADRE`: Cali y Yumbo en Cali A.M.) **no son
# MAGIC   nodos de W**, porque su territorio ya está en el nodo del A.M. (R-14): se predicen como
# MAGIC   subáreas de su nodo, `x'β̂ + û_D`, y se les aplica el benchmarking de nivel 2 (sección 9).
# MAGIC   Los demás son nodos sin encuesta.

# COMMAND ----------

# Mapa código → alias desde el catálogo de literatura (R-63), como en fay_herriot.py, en lugar
# de la tabla de documentación `trazabilidad_covariables`.
mapa_alias = alias_desde_catalogo()
alias_a_codigo = {alias: codigo for codigo, alias in mapa_alias.items()}

# Covariables del ganador clásico (todas las filas de Parametro salvo el intercepto).
coef_clasico = spark.table("tesis.modelo.fh_coeficientes").toPandas()
covars = [p for p in coef_clasico["Parametro"] if p != "Intercepto"]
print(f"Covariables (benchmark clásico seleccionado): {' + '.join(covars)}")

divipola = (
    spark.table(TBL_DIM_DIVIPOLA)
    .select("CODIGO_MUNICIPIO", "LATITUD", "LONGITUD")
    .toPandas()
)

# Dominios con encuesta.
df = spark.table(TBL_COVARIABLES_SELECCIONADAS).toPandas()
for col in [Y_COL, SE_COL, "CV_PORCENTAJE", *covars]:
    df[col] = df[col].astype(float)
df = df.merge(
    divipola, left_on="CODIGO_DOMINIO", right_on="CODIGO_MUNICIPIO", how="left"
).drop(columns="CODIGO_MUNICIPIO")
df = df.sort_values("CODIGO_DOMINIO").reset_index(drop=True)

# Municipios objetivo: los 83 del clásico (R-14).
obj_todos = spark.table(TBL_MUNICIPIOS_SIN_ENCUESTA).toPandas()
obj_todos = obj_todos.rename(
    columns={
        alias_a_codigo[a]: a
        for a in covars
        if alias_a_codigo.get(a) in obj_todos.columns
    }
)
obj_todos = obj_todos.merge(divipola, on="CODIGO_MUNICIPIO", how="left")
for col in covars:
    obj_todos[col] = obj_todos[col].astype(float)
obj_todos = obj_todos.sort_values("CODIGO_MUNICIPIO").reset_index(drop=True)

# Subáreas de un dominio A.M.: no son nodos de W (su territorio ya está en el nodo del A.M.).
es_subarea = obj_todos["CODIGO_DOMINIO_PADRE"].notna()
obj_sub = obj_todos.loc[es_subarea].reset_index(drop=True)
print(
    "Municipios que son subáreas de un dominio A.M. (no son nodos de W): "
    + ", ".join(
        f"{m} ({p})"
        for m, p in zip(obj_sub["MUNICIPIO"], obj_sub["CODIGO_DOMINIO_PADRE"])
    )
)
# Los demás son nodos sin encuesta; si alguno ya fuera un dominio con encuesta se excluye.
obj = obj_todos.loc[~es_subarea].copy()
ya_dominio = obj["CODIGO_MUNICIPIO"].isin(df["CODIGO_DOMINIO"])
if ya_dominio.any():
    print(
        "Municipios objetivo que ya son dominio con encuesta (se excluyen): "
        + ", ".join(obj.loc[ya_dominio, "MUNICIPIO"])
    )
obj = obj.loc[~ya_dominio].reset_index(drop=True)

if obj_todos[covars + ["LATITUD", "LONGITUD"]].isna().any().any():
    raise ValueError("Hay municipios objetivo sin covariables o sin coordenadas.")
if df[["LATITUD", "LONGITUD"]].isna().any().any():
    raise ValueError("Hay dominios con encuesta sin coordenadas.")

n, r = len(df), len(obj)
print(
    f"\nDominios con encuesta (n): {n}   Nodos objetivo sin encuesta (r): {r}   "
    f"Subáreas de un A.M.: {len(obj_sub)}   Unidades de W: {n + r}"
)
print(obj.groupby("CODIGO_DEPARTAMENTO").size().rename("n_objetivo").to_string())

# COMMAND ----------

# DBTITLE 1,2. Diagnóstico de vecindad
# MAGIC %md
# MAGIC ## 2. Diagnóstico de vecindad
# MAGIC
# MAGIC Antes de modelar: ¿hay información espacial útil? Se mide (a) la distancia de cada
# MAGIC objetivo al dominio con encuesta más cercano y (b) la distancia entre los propios
# MAGIC dominios con encuesta, que es lo que informa sobre ρ.

# COMMAND ----------

lat = np.concatenate([df["LATITUD"].values, obj["LATITUD"].values])
lon = np.concatenate([df["LONGITUD"].values, obj["LONGITUD"].values])
D_km = distancias_haversine(lat, lon)
idx_dom, idx_obj = range(n), range(n, n + r)

filas = []
for depto, sub in obj.groupby("CODIGO_DEPARTAMENTO"):
    idx = [n + i for i in sub.index]
    filas.append(
        {
            "CODIGO_DEPARTAMENTO": depto,
            "n_objetivos": len(idx),
            **resumen_vecindad(D_km, idx, idx_dom),
        }
    )
df_vecindad = pd.DataFrame(filas)
print("Distancia de cada municipio objetivo al dominio con encuesta más cercano:")
mostrar(df_vecindad.round(1))

D_dom = D_km[:n, :n].copy()
np.fill_diagonal(D_dom, np.inf)
vecino_cercano = D_dom.min(axis=1)
print(
    f"\nEntre los {n} dominios con encuesta, el vecino más cercano está a "
    f"{vecino_cercano.min():.0f}-{vecino_cercano.max():.0f} km (mediana {np.median(vecino_cercano):.0f} km); "
    f"{int((vecino_cercano > 100).sum())} dominios tienen su vecino a más de 100 km."
)

# COMMAND ----------

# DBTITLE 1,3. Fay-Herriot clásico de referencia
# MAGIC %md
# MAGIC ## 3. Fay-Herriot clásico (referencia)
# MAGIC
# MAGIC Mismo modelo y covariables que el benchmark de `fay_herriot.py`. Su AIC (con p + 1
# MAGIC parámetros) es el punto de comparación; el espacial agrega un parámetro (ρ).

# COMMAND ----------

clasico = FayHerriotClasico(covars, df, Y_COL, SE_COL)
clasico.ajustar()
ll_clasico = -(clasico.aic - 2 * (clasico.p + 1)) / 2
print(f"Â = {clasico.A_hat:.4f}   AIC = {clasico.aic:.3f}   R² = {clasico.r2:.4f}")
print("Coeficientes:", dict(zip(["Intercepto"] + covars, clasico.beta_hat.round(4))))
print("p-valores:   ", dict(zip(["Intercepto"] + covars, clasico.p_vals.round(4))))

# COMMAND ----------

# DBTITLE 1,4. Escenarios de W y I de Moran de los residuos
# MAGIC %md
# MAGIC ## 4. Escenarios de W e I de Moran
# MAGIC
# MAGIC Se prueban varias definiciones de W porque con 23 dominios dispersos la conclusión
# MAGIC podría depender de ella: k vecinos más cercanos (k = 3, 5) y distancia inversa
# MAGIC (potencia 1 y 2), siempre estandarizadas por filas.
# MAGIC
# MAGIC El **I de Moran** se calcula sobre los residuos del Fay-Herriot clásico (`y − Xβ̂`), no sobre
# MAGIC la tasa cruda: lo que debe ser independiente en el modelo clásico son los efectos aleatorios,
# MAGIC y la tasa cruda hereda autocorrelación de las covariables. Para el Moran, W se construye solo
# MAGIC entre los dominios con encuesta. Con n = 23 la potencia es baja: un Moran no significativo no
# MAGIC prueba independencia espacial.

# COMMAND ----------


def proximidad_total(tipo: str, parametro, estructura: str) -> np.ndarray:
    """Proximidad de todas las unidades para un escenario y una estructura.

    Envoltorio de `shared.matriz_proximidad.proximidad_total` con las distancias y el número de
    dominios de este notebook.

    Args:
        tipo (str): ``"knn"`` o ``"inversa"``.
        parametro (float): k o potencia.
        estructura (str): ``"completa"`` o ``"muestra"``.

    Returns:
        np.ndarray: Matriz (n + r, n + r).
    """
    return proximidad_total_compartida(D_km, n, tipo, parametro, estructura)


# Residuos crudos (y − Xβ̂) y estandarizados (÷ √(D_d + Â)). Para comparar I_base con
# I_espacial se usa la misma estandarización en ambos (R-12): en el clásico V es diagonal, así
# que el blanqueo de Cholesky es la división por √(D_d + Â); en el SEBLUP es el blanqueo con
# la Cholesky de V completa (`residuals`, sección 5).
residuos_clasico = df[Y_COL].values - clasico.mu_hat
filas = []
for nombre, tipo, parametro in ESCENARIOS_W:
    W_muestra = estandarizar_filas(proximidad_escenario(D_km[:n, :n], tipo, parametro))
    filas += filas_moran(
        nombre,
        {
            "residuos_clasico": residuos_clasico,
            "residuos_clasico_estandarizados": clasico.residuals,
            "tasa_directa": df[Y_COL].values,
        },
        W_muestra,
        N_PERMUTACIONES_MORAN,
        SEMILLA_ESPACIAL,
    )
df_moran = pd.DataFrame(filas)
mostrar(df_moran.round(4))

# COMMAND ----------

# DBTITLE 1,5. Ajuste del SEBLUP y comparación con el clásico
# MAGIC %md
# MAGIC ## 5. Ajuste del SEBLUP
# MAGIC
# MAGIC Para cada escenario de W y cada estructura:
# MAGIC * `muestra`: W solo entre los dominios con encuesta (Petrucci-Salvati). Los objetivos
# MAGIC   reciben el sintético `Xβ̂`.
# MAGIC * `completa`: W entre todas las unidades y verosimilitud marginal sobre la muestra
# MAGIC   (Saei-Chambers; Benedetti et al., 2024). Los objetivos reciben además un efecto
# MAGIC   espacial `û_r = G_rs V⁻¹ (y − Xβ̂)` calculado a partir de los dominios cercanos.
# MAGIC
# MAGIC Se reportan σ̂²_u, ρ̂, AIC (ML) y la **prueba de razón de verosimilitudes** de ρ = 0
# MAGIC contra el clásico (1 grado de libertad). El criterio para preferir el espacial es
# MAGIC p(LRT) < 0.05 (R-43). El ΔAIC (clásico − espacial) se reporta como descripción, pero **no es
# MAGIC un segundo respaldo**: como los modelos difieren en un parámetro y se comparan con la
# MAGIC misma verosimilitud ML, ΔAIC = LRT − 2 exactamente.
# MAGIC
# MAGIC **Qué estructura prueba ρ (R-13).** La prueba principal de ρ es la de la estructura
# MAGIC `muestra`: el SAR solo entre los dominios con encuesta, que son los únicos con dato. En la
# MAGIC estructura `completa` (verosimilitud marginal, MML de Benedetti et al., 2024, ecs. 18-20; no
# MAGIC el estimador de Saei y Chambers) el SAR se impone también sobre los nodos sin dato, que son un
# MAGIC recorte (los objetivos de Cauca y Valle) y no la población de áreas del artículo: su ρ̂ es
# MAGIC **condicional a ese conjunto de nodos** y no tiene lectura de signo (sección 8).

# COMMAND ----------

modelos_esp = {}
filas = []
for nombre, tipo, parametro in ESCENARIOS_W:
    for estructura in ("muestra", "completa"):
        P = proximidad_total(tipo, parametro, estructura)
        modelo = FayHerriotEspacial(
            covars,
            df,
            Y_COL,
            SE_COL,
            P,
            obj,
            estructura=estructura,
            rho_limite=RHO_LIMITE,
        )
        modelo.ajustar()
        modelos_esp[(nombre, estructura)] = modelo
        lrt = max(2 * (modelo.loglik_ml - ll_clasico), 0.0)
        filas.append(
            {
                "escenario": nombre,
                "estructura": estructura,
                "A_hat": modelo.A_hat,
                "rho_hat": modelo.rho_hat,
                "AIC": modelo.aic,
                "AIC_clasico": clasico.aic,
                "Delta_AIC": clasico.aic - modelo.aic,
                "LRT": lrt,
                "p_LRT": stats.chi2.sf(lrt, 1),
                "p_covariables": ", ".join(f"{p:.3f}" for p in modelo.p_vals[1:]),
                "R2": modelo.r2,
            }
        )
df_comparacion = pd.DataFrame(filas)
# R-43: un solo criterio, p(LRT) < ALFA_LRT (ΔAIC = LRT − 2 es el mismo estadístico).
df_comparacion["espacial_preferido"] = df_comparacion["p_LRT"] < ALFA_LRT
df_comparacion["estructura_etiqueta"] = df_comparacion["estructura"].map(
    ETIQUETA_ESTRUCTURA
)
mostrar(df_comparacion.round(4))
print(
    "Delta_AIC = AIC clásico − AIC espacial (positivo favorece al espacial; es LRT − 2). "
    f"Preferido: p(LRT) < {ALFA_LRT}. La prueba principal es la de la estructura «muestra» (R-13)."
)

# I de Moran de los residuos del SEBLUP, blanqueados con la Cholesky de V, con la W entre los
# dominios con encuesta; se compara con el del clásico estandarizado igual (R-12).
filas_moran_esp = []
for nombre, tipo, parametro in ESCENARIOS_W:
    W_muestra = estandarizar_filas(proximidad_escenario(D_km[:n, :n], tipo, parametro))
    for estructura in ("muestra", "completa"):
        filas_moran_esp += filas_moran(
            nombre,
            {"residuos_espacial": modelos_esp[(nombre, estructura)].residuals},
            W_muestra,
            N_PERMUTACIONES_MORAN,
            SEMILLA_ESPACIAL,
            estructura=estructura,
        )
df_moran = pd.concat([df_moran, pd.DataFrame(filas_moran_esp)], ignore_index=True)
print("\nI de Moran: residuos estandarizados del clásico frente a los del SEBLUP")
mostrar(
    df_moran[
        df_moran["variable"].isin(
            ["residuos_clasico_estandarizados", "residuos_espacial"]
        )
    ].round(4)
)

# Coeficientes del clásico y del espacial lado a lado (R-16).
df_coef_comparacion = construir_cuadro_coeficientes(clasico, modelos_esp, covars)
print("\nCoeficientes: clásico frente a espacial (Δβ en errores estándar del clásico)")
mostrar(df_coef_comparacion.round(4))

# COMMAND ----------

# DBTITLE 1,6. Perfil de verosimilitud de ρ
# MAGIC %md
# MAGIC ## 6. ¿Está identificado ρ?
# MAGIC
# MAGIC Para cada ρ de una rejilla se maximiza la log-verosimilitud REML sobre σ²_u. Una curva
# MAGIC plana indica que los datos casi no informan sobre la autocorrelación espacial. La línea
# MAGIC punteada (−1.92) es el corte del intervalo de verosimilitud perfilada del 95 %.

# COMMAND ----------

perfiles = {
    nombre: modelos_esp[(nombre, "completa")].perfil_rho()
    for nombre, _, _ in ESCENARIOS_W
}
df_perfil = pd.concat(
    [p.assign(escenario=nombre) for nombre, p in perfiles.items()], ignore_index=True
)
resumen_perfil = []
for nombre, p in perfiles.items():
    dentro = p.loc[p["delta_vs_rho0"] >= p["delta_vs_rho0"].max() - 1.92, "rho"]
    resumen_perfil.append(
        {
            "escenario": nombre,
            "rho_maximo": p.loc[p["delta_vs_rho0"].idxmax(), "rho"],
            "ganancia_max_vs_rho0": p["delta_vs_rho0"].max(),
            "IC95_rho_min": dentro.min(),
            "IC95_rho_max": dentro.max(),
        }
    )
df_resumen_perfil = pd.DataFrame(resumen_perfil)
mostrar(df_resumen_perfil.round(3))
guardar_figura(figura_perfil_rho(perfiles), "perfil_rho")

# COMMAND ----------

# DBTITLE 1,7. Validación dejar-un-dominio-fuera
# MAGIC %md
# MAGIC ## 7. Validación dejar-un-dominio-fuera
# MAGIC
# MAGIC Es la prueba más cercana al uso real: predecir un municipio **no visto**. Para cada uno
# MAGIC de los 23 dominios se re-estima el modelo sin él y se le predice como si no tuviera
# MAGIC encuesta, con (a) el sintético clásico, (b) el sintético del modelo espacial y (c) el
# MAGIC predictor espacial con efecto. El referente es la estimación directa del dominio, que tiene
# MAGIC ruido; por eso se reporta también el RMSE corregido restando la varianza directa.
# MAGIC
# MAGIC Con n = 23 la diferencia entre predictores es una evidencia modesta, no una prueba.

# COMMAND ----------

validaciones = {}
filas_met = []
for nombre, tipo, parametro in ESCENARIOS_W:
    for estructura in ("muestra", "completa"):
        P = proximidad_total(tipo, parametro, estructura)
        cv = validacion_dejar_uno_fuera(
            covars, df, Y_COL, SE_COL, P, obj, estructura=estructura
        )
        validaciones[(nombre, estructura)] = cv
        met = metricas_validacion(cv)
        met.insert(0, "estructura", estructura)
        met.insert(0, "escenario", nombre)
        filas_met.append(met)
df_validacion = pd.concat(filas_met, ignore_index=True)
mostrar(df_validacion.round(4))
print(NOTA_VALIDACION_OPTIMISTA)

# COMMAND ----------

# DBTITLE 1,7b. Cuadro comparativo (objetivo 1)
# MAGIC %md
# MAGIC ### Cuadro comparativo: benchmark clásico vs. especificaciones espaciales
# MAGIC
# MAGIC Resume en una sola tabla el ajuste (σ̂²_u, ρ̂, AIC, ΔAIC, LRT) y la validación
# MAGIC dejar-un-dominio-fuera (RMSE, RMSE corregido por el ruido de la directa, sesgo). La
# MAGIC primera fila es el benchmark clásico seleccionado; las demás, las ocho especificaciones
# MAGIC espaciales. Todas comparten las covariables.

# COMMAND ----------

df_cuadro = construir_cuadro_comparativo(df_comparacion, df_validacion, clasico, covars)
mostrar(df_cuadro.round(3))

# COMMAND ----------

# DBTITLE 1,8. Decisión
# MAGIC %md
# MAGIC ## 8. Decisión
# MAGIC
# MAGIC Se toma como escenario espacial de referencia el de menor AIC con la estructura completa (la
# MAGIC única que produce efecto espacial en los objetivos) entre los que tienen ρ̂ interior
# MAGIC (|ρ̂| < 0.99; un ρ̂ pegado a la cota es un artefacto de verosimilitud plana). Se declara
# MAGIC **preferido el espacial** solo si la prueba de razón de verosimilitudes de ρ = 0 da
# MAGIC p(LRT) < 0.05 **en la estructura `muestra` de ese mismo escenario** (R-13, R-43): es la que usa
# MAGIC solo los dominios con dato. El ρ̂ de la estructura completa es condicional al conjunto de nodos
# MAGIC sin dato y no se interpreta (ver la sensibilidad más abajo). El resultado de la validación
# MAGIC dejar-uno-fuera se reporta como evidencia complementaria, no como criterio de decisión.

# COMMAND ----------

completas = df_comparacion[df_comparacion["estructura"] == "completa"]
# Un ρ̂ pegado a la cota (|ρ̂| = RHO_LIMITE) no es una estimación sino un artefacto de una
# verosimilitud plana; esos escenarios solo se usan si no queda ninguno con ρ̂ interior.
interiores = completas[completas["rho_hat"].abs() < RHO_LIMITE - 1e-6]
candidatas = interiores if len(interiores) else completas
mejor = candidatas.loc[candidatas["AIC"].idxmin()]
mejor_nombre = mejor["escenario"]
# R-13: la prueba de ρ = 0 es la de la estructura «muestra» del mismo escenario.
prueba_rho = df_comparacion[
    (df_comparacion["estructura"] == "muestra")
    & (df_comparacion["escenario"] == mejor_nombre)
].iloc[0]
espacial_preferido = bool(prueba_rho["p_LRT"] < ALFA_LRT)
en_cota = completas.loc[~completas.index.isin(interiores.index), "escenario"].tolist()
if en_cota:
    print(f"Escenarios con ρ̂ en la cota (descartados como referencia): {en_cota}")

met_mejor = df_validacion[
    (df_validacion["escenario"] == mejor_nombre)
    & (df_validacion["estructura"] == "completa")
].set_index("predictor")
rmse_clasico = met_mejor.loc["pred_clasico", "RMSE"]
rmse_espacial = met_mejor.loc["pred_espacial", "RMSE"]

print(f"Escenario espacial de referencia por AIC (estructura completa): {mejor_nombre}")
print(
    f"  ρ̂ (completa, condicional a los nodos) = {mejor['rho_hat']:.3f}   "
    f"σ̂²_u = {mejor['A_hat']:.3f} (clásico {clasico.A_hat:.3f})"
)
print(
    f"  Prueba de ρ = 0 (estructura muestra): ρ̂ = {prueba_rho['rho_hat']:.3f}   "
    f"LRT = {prueba_rho['LRT']:.3f}   p(LRT) = {prueba_rho['p_LRT']:.4f}   "
    f"(ΔAIC = LRT − 2 = {prueba_rho['Delta_AIC']:.2f})"
)
print(
    f"  Validación dejar-uno-fuera, RMSE: clásico {rmse_clasico:.3f}  vs  "
    f"espacial con efecto {rmse_espacial:.3f}"
)
if espacial_preferido:
    print("  → Se cumple el criterio: el modelo espacial es preferido al clásico.")
else:
    print(
        f"  → NO se cumple el criterio (p(LRT) < {ALFA_LRT} en la estructura muestra): los datos no "
        "justifican ρ ≠ 0; se recomienda el Fay-Herriot clásico y el espacial queda como análisis de "
        "sensibilidad."
    )

# COMMAND ----------

# DBTITLE 1,8b. Residuos del clásico y del espacial sobre el mapa
# MAGIC %md
# MAGIC ### Residuos estandarizados por dominio (R-12)
# MAGIC
# MAGIC Mismo dominio, misma escala de color: residuos estandarizados del clásico (÷ √(D_d + Â)) y del
# MAGIC SEBLUP del escenario de referencia (blanqueados con la Cholesky de V). Si el espacial capturara
# MAGIC dependencia que el clásico deja en los residuos, los colores agrupados del primer panel se
# MAGIC dispersarían en el segundo. El I de Moran de ambos está en la tabla de la sección 5.

# COMMAND ----------

dominios_residuos = pd.DataFrame(
    {
        "LONGITUD": df["LONGITUD"],
        "LATITUD": df["LATITUD"],
        "NOMBRE": df["NOMBRE_DOMINIO"],
    }
)
guardar_figura(
    figura_mapa_residuos(
        dominios_residuos,
        {
            "Clásico": clasico.residuals,
            "Espacial (SEBLUP)": modelos_esp[(mejor_nombre, "completa")].residuals,
        },
    ),
    "mapa_residuos",
)

# COMMAND ----------

# DBTITLE 1,8c. Sensibilidades de la construcción de W
# MAGIC %md
# MAGIC ### Sensibilidad de ρ̂ a la construcción de W (R-13, R-42)
# MAGIC
# MAGIC * **Nodos sin dato (R-13).** ρ̂ de la estructura completa con todos los objetivos, solo los del
# MAGIC   Valle, solo los del Cauca y ninguno (que equivale a la estructura muestra). Si cambia de
# MAGIC   magnitud o de signo, el ρ̂ de la completa lo ponen los nodos sin dato y no los datos: no se
# MAGIC   interpreta su signo.
# MAGIC * **Centroide del A.M. (R-42).** El nodo de un dominio A.M. se ubica por defecto en su
# MAGIC   capital; aquí se compara con la media de las coordenadas de sus municipios miembro
# MAGIC   (`dim_dominio_geih`). Es una sensibilidad: la base sigue siendo la capital.
# MAGIC * **Valores de W.** k ∈ {3, 5} y potencia ∈ {1, 2} se justifican en `config.py`
# MAGIC   (`ESCENARIOS_W`); la conclusión se reporta sobre los cuatro, no sobre uno.

# COMMAND ----------

depto_obj = obj["CODIGO_DEPARTAMENTO"].astype(str)
conjuntos = {
    "todos": np.ones(r, dtype=bool),
    "solo Valle": (depto_obj == "76").to_numpy(),
    "solo Cauca": (depto_obj == "19").to_numpy(),
    "ninguno": np.zeros(r, dtype=bool),
}
df_sens_rho = sensibilidad_rho_objetivos(
    covars, df, Y_COL, SE_COL, obj, clasico, ESCENARIOS_W, conjuntos
)
print("ρ̂ de la estructura completa según los nodos sin dato incluidos:")
mostrar(df_sens_rho.round(3))

miembros = (
    spark.table(TBL_DIM_DOMINIO)
    .select("CODIGO_DOMINIO", "CODIGO_MUNICIPIO")
    .toPandas()
    .merge(divipola, on="CODIGO_MUNICIPIO", how="left")
)
centro_medio = miembros.groupby("CODIGO_DOMINIO")[["LATITUD", "LONGITUD"]].mean()
lat_media = df["CODIGO_DOMINIO"].map(centro_medio["LATITUD"]).to_numpy(dtype=float)
lon_media = df["CODIGO_DOMINIO"].map(centro_medio["LONGITUD"]).to_numpy(dtype=float)
if np.isnan(lat_media).any() or np.isnan(lon_media).any():
    raise ValueError("Hay dominios sin municipios miembro con coordenadas.")
df_sens_centroide = sensibilidad_centroide(
    covars, df, Y_COL, SE_COL, obj, lat_media, lon_media, clasico, ESCENARIOS_W
)
print(
    "\nρ̂ y AIC con el nodo del A.M. en la capital frente a la media de sus municipios:"
)
mostrar(df_sens_centroide.round(3))

# COMMAND ----------

# DBTITLE 1,9. Predicción para los municipios objetivo (MSE bootstrap)
# MAGIC %md
# MAGIC ## 9. Predicción en los municipios objetivo
# MAGIC
# MAGIC Se reajusta el mejor escenario espacial con el **bootstrap paramétrico** del MSE
# MAGIC (Morales et al., §18.2.3, p. 494): en cada réplica se simulan los efectos SAR y los
# MAGIC errores de muestreo, se re-estiman σ²_u y ρ y se acumula el error del predictor frente a
# MAGIC la verdad simulada, de modo que el MSE incluye la incertidumbre de ρ̂.
# MAGIC
# MAGIC La tabla compara tres predictores por municipio:
# MAGIC * `PRED_CLASICO`: sintético del Fay-Herriot clásico, con su MSE `x'Cov(β̂)x + Â` (p. 441).
# MAGIC * `PRED_SINT_ESPACIAL`: `Xβ̂` con el β̂ del modelo espacial.
# MAGIC * `PRED_ESPACIAL`: `Xβ̂ + û_r`, con el efecto espacial predicho desde los dominios cercanos.
# MAGIC
# MAGIC **Subáreas de un A.M. (R-14).** Cali y Yumbo no son nodos: se predicen como
# MAGIC `x_m'β̂ + û_D`, con el efecto espacial predicho del nodo «Cali A.M.», y se les aplica
# MAGIC `benchmark_nivel2` con los mismos pesos de PET que el clásico, para que su promedio ponderado
# MAGIC reproduzca el SEBLUP del A.M. Antes, el EBLUP del espacial pasa por el benchmarking de nivel 1
# MAGIC (mismo valor de referencia que el clásico: la directa del conjunto de los 23 dominios). Su
# MAGIC MSE es el del sintético, `x'Cov(β̂)x + Â`; el de los demás nodos es el del bootstrap.
# MAGIC
# MAGIC **Extrapolación y calidad (R-15).** `ESTADO_EXTRAPOLACION` (B20) se calcula con la
# MAGIC covarianza de β̂ del espacial, no con la del clásico, y la calidad reportada (B21) agrega
# MAGIC «condicional al modelo» y «extrapolado» como en la tabla final del clásico.
# MAGIC
# MAGIC `RECOMENDADO` indica cuál usar según la decisión del paso anterior.

# COMMAND ----------

tipo_mejor, param_mejor = next(
    (t, p) for nm, t, p in ESCENARIOS_W if nm == mejor_nombre
)
P_mejor = proximidad_total(tipo_mejor, param_mejor, "completa")
final = FayHerriotEspacial(
    covars,
    df,
    Y_COL,
    SE_COL,
    P_mejor,
    obj,
    estructura="completa",
    rho_limite=RHO_LIMITE,
    n_bootstrap=BOOTSTRAP_ESPACIAL_REPLICAS,
    semilla=SEMILLA_ESPACIAL,
)
final.ajustar()
print(
    f"Escenario {mejor_nombre}: ρ̂ = {final.rho_hat:.3f}, σ̂²_u = {final.A_hat:.3f}; "
    f"réplicas bootstrap válidas: {final.n_bootstrap_validas} de {BOOTSTRAP_ESPACIAL_REPLICAS}"
)

X_obj = final.X_obj
pred_clasico = X_obj @ clasico.beta_hat
mse_clasico = np.einsum("ij,jk,ik->i", X_obj, clasico.cov_beta, X_obj) + clasico.A_hat

COLS_ID = [
    "CODIGO_DEPARTAMENTO",
    "CODIGO_MUNICIPIO",
    "MUNICIPIO",
    "CODIGO_DOMINIO_PADRE",
    "LATITUD",
    "LONGITUD",
]
# Nodos sin encuesta: efecto espacial y MSE por bootstrap (Morales et al., p. 494).
pred = obj[COLS_ID].copy()
pred["PRED_CLASICO"] = pred_clasico
pred["CV_CLASICO_PCT"] = 100 * np.sqrt(mse_clasico) / np.abs(pred_clasico)
pred["PRED_SINT_ESPACIAL"] = final.sintetico_objetivo
pred["CV_SINT_ESPACIAL_PCT"] = (
    100 * np.sqrt(final.mse_sintetico_objetivo) / np.abs(final.sintetico_objetivo)
)
pred["EFECTO_ESPACIAL"] = final.pred_objetivo - final.sintetico_objetivo
pred["PRED_ESPACIAL"] = final.pred_objetivo
pred["MSE_ESPACIAL"] = final.mse_objetivo
pred["FUENTE_MSE_ESPACIAL"] = "BOOTSTRAP"

# Subáreas de un A.M.: x'β̂ + efecto del nodo padre, MSE del sintético (R-14).
sub = predecir_subareas(obj_sub, covars, final, df["CODIGO_DOMINIO"])
X_sub = np.column_stack([np.ones(len(obj_sub))] + [obj_sub[c].values for c in covars])
pred_sub = obj_sub[COLS_ID].copy()
pred_sub["PRED_CLASICO"] = X_sub @ clasico.beta_hat
pred_sub["CV_CLASICO_PCT"] = (
    100
    * np.sqrt(np.einsum("ij,jk,ik->i", X_sub, clasico.cov_beta, X_sub) + clasico.A_hat)
    / np.abs(pred_sub["PRED_CLASICO"])
)
pred_sub["PRED_SINT_ESPACIAL"] = sub["PRED_SINT_ESPACIAL"]
pred_sub["CV_SINT_ESPACIAL_PCT"] = (
    100 * np.sqrt(sub["MSE_ESPACIAL"]) / np.abs(sub["PRED_SINT_ESPACIAL"])
)
pred_sub["EFECTO_ESPACIAL"] = sub["EFECTO_ESPACIAL"]
pred_sub["PRED_ESPACIAL"] = sub["PRED_ESPACIAL"]
pred_sub["MSE_ESPACIAL"] = sub["MSE_ESPACIAL"]
pred_sub["FUENTE_MSE_ESPACIAL"] = "SINTETICO_SUBAREA"

pred = pd.concat([pred, pred_sub], ignore_index=True)
pred = pred.sort_values("CODIGO_MUNICIPIO").reset_index(drop=True)
pred["CV_ESPACIAL_PCT"] = (
    100 * np.sqrt(pred["MSE_ESPACIAL"]) / np.abs(pred["PRED_ESPACIAL"])
)
pred["DIF_ESPACIAL_VS_CLASICO"] = pred["PRED_ESPACIAL"] - pred["PRED_CLASICO"]

# Distancia al dominio con encuesta más cercano (0 para las subáreas de un A.M. en su capital).
D_pred = distancias_haversine(
    np.concatenate([df["LATITUD"].values, pred["LATITUD"].values]),
    np.concatenate([df["LONGITUD"].values, pred["LONGITUD"].values]),
)
pred["KM_DOMINIO_CERCANO"] = D_pred[n:, :n].min(axis=1)

# Benchmarking, igual que en el clásico (shared/benchmarking.py). Nivel 1: los EBLUP del espacial
# × λ₁ para que Σ PEA·EBLUP/Σ PEA reproduzca la directa del conjunto. Nivel 2: los municipios de
# un A.M. × λ_D para que, ponderados por la PET, reproduzcan el EBLUP ajustado de su dominio.
pea_dominio = df[COL_PESO_NIVEL1].to_numpy(dtype=float)
referencia_n1 = promedio_ponderado(df[Y_COL].to_numpy(dtype=float), pea_dominio)
eblup_n1_esp, lambda_n1_esp = benchmark_nivel1(final.eblup, pea_dominio, referencia_n1)
print(f"λ₁ del espacial = {lambda_n1_esp:.6f} (referencia {referencia_n1:.4f} %)")

per_modelo, mes_modelo = int(obj_todos["PER"].iloc[0]), int(obj_todos["MES"].iloc[0])
pesos_n2 = (
    spark.table(TBL_TERRIDATA)
    .filter(f"ANO = {per_modelo} AND MES = {mes_modelo}")
    .selectExpr(
        "CODIGO_ENTIDAD AS CODIGO_MUNICIPIO", f"{EXPR_PESO_POBLACION} AS PESO_N2"
    )
    .toPandas()
)
pred = pred.merge(pesos_n2, on="CODIGO_MUNICIPIO", how="left", validate="one_to_one")
bm2 = benchmark_nivel2(
    pred.assign(PRED_EXACTA=pred["PRED_ESPACIAL"]),
    col_pred="PRED_EXACTA",
    col_peso="PESO_N2",
    col_padre="CODIGO_DOMINIO_PADRE",
    objetivos=dict(zip(df["CODIGO_DOMINIO"], eblup_n1_esp)),
)
pred["LAMBDA_N2_ESPACIAL"] = bm2["LAMBDA_N2"].round(6)
pred["PRED_ESPACIAL_BENCHMARK"] = bm2["PRED_BENCHMARK"].round(4)
print(f"Subáreas ajustadas a su dominio A.M. (nivel 2): {int(bm2['BENCHMARK'].sum())}")

# Predicción del clásico ya publicada (con su benchmarking), para comparar los mismos 83.
try:
    publicada = (
        spark.table(TBL_FAY_HERRIOT_PREDICCION_SINTETICA)
        .select("CODIGO_MUNICIPIO", "PRED_BENCHMARK")
        .toPandas()
        .rename(columns={"PRED_BENCHMARK": "PRED_CLASICO_BENCHMARK"})
    )
    pred = pred.merge(
        publicada, on="CODIGO_MUNICIPIO", how="left", validate="one_to_one"
    )
except Exception as error:
    print(f"(sin predicción publicada del clásico: {type(error).__name__})")
    pred["PRED_CLASICO_BENCHMARK"] = np.nan

# B20 con la covarianza de β̂ del espacial (R-15): estado de extrapolación y aporte.
X_todos = np.column_stack(
    [np.ones(len(pred))]
    + [
        obj_todos.set_index("CODIGO_MUNICIPIO")
        .loc[pred["CODIGO_MUNICIPIO"], c]
        .to_numpy()
        for c in covars
    ]
)
estado = estado_extrapolacion(final.X, X_todos, final.cov_beta, final.beta_hat, covars)
for col in ["ESTADO_EXTRAPOLACION", "COVARIABLE_PRINCIPAL", "APORTE_EXTRAPOLADO_PP"]:
    pred[col] = estado[col].to_numpy()
pred["EXTRAPOLA"] = pred["ESTADO_EXTRAPOLACION"] != "DENTRO_DEL_RANGO"
pred["FUERA_DE_RANGO_CLASICO"] = marca_fuera_de_rango(
    pred["PRED_CLASICO"].values, TASA_MINIMA, TASA_MAXIMA
)
pred["FUERA_DE_RANGO_ESPACIAL"] = marca_fuera_de_rango(
    pred["PRED_ESPACIAL"].values, TASA_MINIMA, TASA_MAXIMA
)

# B21: la calidad reportada es condicional al modelo y advierte la extrapolación.
pred["RECOMENDADO"] = "ESPACIAL" if espacial_preferido else "CLASICO"
col_rec = "CV_ESPACIAL_PCT" if espacial_preferido else "CV_CLASICO_PCT"
pred["CONFIABILIDAD_RECOMENDADO"] = pred[col_rec].apply(clasificar_confiabilidad)
pred["CALIDAD_REPORTADA_RECOMENDADO"] = [
    etiqueta_calidad("MUNICIPIO", confiabilidad, estado_m)
    for confiabilidad, estado_m in zip(
        pred["CONFIABILIDAD_RECOMENDADO"], pred["ESTADO_EXTRAPOLACION"]
    )
]
pred["PER"], pred["MES"] = per_modelo, mes_modelo
mostrar(pred.round(3))

# COMMAND ----------

# DBTITLE 1,Resumen de la predicción
print("Resumen (puntos porcentuales de la tasa de desempleo):")
resumen = pd.DataFrame(
    {
        "clásico": pred["PRED_CLASICO"].describe(),
        "sintético espacial": pred["PRED_SINT_ESPACIAL"].describe(),
        "espacial con efecto": pred["PRED_ESPACIAL"].describe(),
    }
).round(3)
mostrar(resumen)
print(
    f"Efecto espacial: media {pred['EFECTO_ESPACIAL'].mean():.3f}, "
    f"rango [{pred['EFECTO_ESPACIAL'].min():.3f}, {pred['EFECTO_ESPACIAL'].max():.3f}]; "
    f"|efecto| > 0.5 pp en {int((pred['EFECTO_ESPACIAL'].abs() > 0.5).sum())} de {len(pred)} municipios."
)
print(
    "CV mediano: clásico {:.1f} %, espacial {:.1f} %".format(
        pred["CV_CLASICO_PCT"].median(), pred["CV_ESPACIAL_PCT"].median()
    )
)
print(
    f"Municipios que extrapolan (covariables fuera de la nube de la muestra o combinación "
    f"atípica): {int(pred['EXTRAPOLA'].sum())} de {len(pred)}; tasas fuera de [0, 100]: "
    f"clásico {int(pred['FUERA_DE_RANGO_CLASICO'].sum())}, "
    f"espacial {int(pred['FUERA_DE_RANGO_ESPACIAL'].sum())}."
)
print("Calidad reportada del predictor recomendado:")
print(pred["CALIDAD_REPORTADA_RECOMENDADO"].value_counts().to_string())

# Figuras: validación dejar-uno-fuera y mapas de predicción.
cv_mejor = validaciones[(mejor_nombre, "completa")]
guardar_figura(
    figura_validacion(
        cv_mejor,
        {"Sintético clásico": "pred_clasico", "Espacial con efecto": "pred_espacial"},
    ),
    "validacion",
)
dominios_mapa = pd.DataFrame(
    {
        "LONGITUD": df["LONGITUD"],
        "LATITUD": df["LATITUD"],
        "Y": df[Y_COL],
        "NOMBRE": df["NOMBRE_DOMINIO"],
    }
)
guardar_figura(
    figura_mapa_prediccion(
        pred, dominios_mapa, "PRED_ESPACIAL", "Tasa de desempleo (%)"
    ),
    "mapa_espacial",
)
guardar_figura(
    figura_mapa_prediccion(
        pred, dominios_mapa, "PRED_CLASICO", "Tasa de desempleo (%)"
    ),
    "mapa_clasico",
)

# COMMAND ----------

# DBTITLE 1,10. Exportar resultados
# MAGIC %md
# MAGIC ## 10. Exportar
# MAGIC
# MAGIC Se escriben las tablas `tesis.modelo.fhe_*` (modo `overwrite`; no se tocan las tablas del
# MAGIC modelo clásico). El detalle de la validación cruzada se guarda para el escenario elegido.

# COMMAND ----------


def escribir(df_pandas: pd.DataFrame, tabla: str) -> None:
    """Escribe un DataFrame de pandas como tabla Delta, sobrescribiendo.

    Args:
        df_pandas (pd.DataFrame): Datos a escribir.
        tabla (str): Nombre completo `catalogo.esquema.tabla`.
    """
    (
        spark.createDataFrame(df_pandas)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(tabla)
    )
    print(f"Tabla escrita: {tabla} ({len(df_pandas)} filas)")


coef_final = pd.DataFrame(
    {
        "Parametro": ["Intercepto"] + covars,
        "Coeficiente": final.beta_hat,
        "Error_estandar": final.se_beta,
        "z": final.t_stats,
        "p_valor": final.p_vals,
    }
)
coef_final["Escenario"] = mejor_nombre
coef_final["A_hat"] = final.A_hat
coef_final["rho_hat"] = final.rho_hat
coef_final["AIC"] = final.aic

cv_export = cv_mejor.copy()
cv_export["CODIGO_DOMINIO"] = df["CODIGO_DOMINIO"].values[cv_export["indice"].values]
cv_export["NOMBRE_DOMINIO"] = df["NOMBRE_DOMINIO"].values[cv_export["indice"].values]
cv_export["escenario"] = mejor_nombre

vecindad_export = df_vecindad.copy()

escribir(df_moran, TBL_FHE_MORAN)
escribir(vecindad_export, TBL_FHE_VECINDAD)
escribir(df_comparacion, TBL_FHE_COMPARACION)
escribir(df_cuadro, TBL_FHE_CUADRO_COMPARATIVO)
escribir(df_perfil, TBL_FHE_PERFIL_RHO)
escribir(df_validacion, TBL_FHE_VALIDACION + "_metricas")
escribir(cv_export, TBL_FHE_VALIDACION)
escribir(coef_final, TBL_FHE_COEFICIENTES)
escribir(pred, TBL_FHE_PREDICCION_OBJETIVO)
escribir(df_coef_comparacion, TBL_FHE_COEFICIENTES_COMPARACION)
escribir(df_sens_centroide, TBL_FHE_SENSIBILIDAD_CENTROIDE)
escribir(df_sens_rho, TBL_FHE_SENSIBILIDAD_RHO)

# COMMAND ----------

# DBTITLE 1,Resumen de la corrida
import json

resumen_corrida = {
    "escenario_referencia": str(mejor_nombre),
    "rho_hat": round(float(final.rho_hat), 4),
    "A_hat_espacial": round(float(final.A_hat), 4),
    "A_hat_clasico": round(float(clasico.A_hat), 4),
    "delta_aic": round(float(mejor["Delta_AIC"]), 3),
    "p_lrt": round(float(mejor["p_LRT"]), 4),
    "p_lrt_muestra": round(float(prueba_rho["p_LRT"]), 4),
    "rmse_cv_clasico": round(float(rmse_clasico), 4),
    "rmse_cv_espacial": round(float(rmse_espacial), 4),
    "espacial_preferido": espacial_preferido,
    "bootstrap_validas": int(final.n_bootstrap_validas),
    "n_extrapola": int(pred["EXTRAPOLA"].sum()),
    "n_fuera_de_rango": int(pred["FUERA_DE_RANGO_ESPACIAL"].sum()),
}
print(json.dumps(resumen_corrida, ensure_ascii=False, indent=2))
try:
    dbutils.notebook.exit(json.dumps(resumen_corrida))
except NameError:
    pass
