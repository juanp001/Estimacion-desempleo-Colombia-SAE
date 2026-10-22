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
# MAGIC 5. Ajuste del SEBLUP por escenario y estructura, y comparación contra el clásico (AIC, LRT).
# MAGIC 6. Perfil de verosimilitud de ρ: ¿está identificado?
# MAGIC 7. Validación dejar-un-dominio-fuera: ¿predice mejor un municipio no visto?
# MAGIC 8. Decisión y predicción para los municipios objetivo (con MSE bootstrap).
# MAGIC 9. Exportar tablas (`tesis.modelo.fhe_*`) y figuras (`fhe_*` en el volumen de figuras).
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
from shared.fay_herriot import FayHerriotClasico
from shared.cuadro_comparativo import construir_cuadro_comparativo
from shared.fay_herriot_espacial import (
    FayHerriotEspacial,
    validacion_dejar_uno_fuera,
    metricas_validacion,
)
from shared.matriz_proximidad import (
    distancias_haversine,
    proximidad_knn,
    proximidad_inversa,
    estandarizar_filas,
    moran_i,
    resumen_vecindad,
)
from shared.figuras_espacial import (
    figura_perfil_rho,
    figura_validacion,
    figura_mapa_prediccion,
)
from shared.consolidacion import clasificar_confiabilidad
from shared.diagnosticos import marca_extrapolacion, marca_fuera_de_rango

import warnings

warnings.filterwarnings("ignore")

VOLUMEN_FIGURAS = "/Volumes/tesis/preprocesamiento/figuras_eda"


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
    """Guarda una figura en el volumen de figuras con el prefijo `fhe_` y la muestra.

    Si el volumen no existe o no es escribible solo avisa; las figuras del modelo se
    muestran en pantalla de todos modos.

    Args:
        fig (plt.Figure): Figura a guardar.
        nombre (str): Nombre del archivo sin extensión (se antepone `fhe_`).
    """
    try:
        fig.savefig(f"{VOLUMEN_FIGURAS}/fhe_{nombre}.png", dpi=150, bbox_inches="tight")
    except Exception as error:
        print(f"(figura {nombre} no guardada: {type(error).__name__})")
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
# MAGIC * **Objetivos**: `municipios_sin_encuesta`, sin los municipios que ya son un dominio con
# MAGIC   encuesta (Cali y Popayán figuran en ambas tablas; para ellos se usa el EBLUP, como en la
# MAGIC   tabla final del modelo clásico).

# COMMAND ----------

mapa_alias = {
    fila["Codigo"]: fila["Alias"]
    for fila in spark.table(TBL_TRAZABILIDAD).select("Codigo", "Alias").collect()
}
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

# Municipios objetivo.
obj = spark.table(TBL_MUNICIPIOS_SIN_ENCUESTA).toPandas()
obj = obj.rename(
    columns={
        alias_a_codigo[a]: a for a in covars if alias_a_codigo.get(a) in obj.columns
    }
)
ya_dominio = obj["CODIGO_MUNICIPIO"].isin(df["CODIGO_DOMINIO"])
print(
    "Municipios objetivo que ya son dominio con encuesta (se excluyen): "
    + ", ".join(obj.loc[ya_dominio, "MUNICIPIO"])
)
obj = obj.loc[~ya_dominio].copy()
obj = obj.merge(divipola, on="CODIGO_MUNICIPIO", how="left")
for col in covars:
    obj[col] = obj[col].astype(float)
obj = obj.sort_values("CODIGO_MUNICIPIO").reset_index(drop=True)

if obj[covars + ["LATITUD", "LONGITUD"]].isna().any().any():
    raise ValueError("Hay municipios objetivo sin covariables o sin coordenadas.")
if df[["LATITUD", "LONGITUD"]].isna().any().any():
    raise ValueError("Hay dominios con encuesta sin coordenadas.")

n, r = len(df), len(obj)
print(
    f"\nDominios con encuesta (n): {n}   Municipios objetivo (r): {r}   Unidades: {n + r}"
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


def proximidad_escenario(distancias: np.ndarray, tipo: str, parametro) -> np.ndarray:
    """Proximidad cruda (sin estandarizar) de un escenario de W.

    Args:
        distancias (np.ndarray): Matriz de distancias en km.
        tipo (str): ``"knn"`` o ``"inversa"``.
        parametro (float): k (knn) o potencia (inversa).

    Returns:
        np.ndarray: Proximidad cruda simétrica con diagonal nula.

    Raises:
        ValueError: Si `tipo` no es válido.
    """
    if tipo == "knn":
        return proximidad_knn(distancias, int(parametro))
    if tipo == "inversa":
        return proximidad_inversa(distancias, float(parametro))
    raise ValueError(f"Tipo de W desconocido: {tipo}")


def proximidad_total(tipo: str, parametro, estructura: str) -> np.ndarray:
    """Proximidad de todas las unidades para un escenario y una estructura.

    Con la estructura ``"muestra"`` el bloque de los dominios con encuesta se reconstruye solo
    con las distancias entre ellos (los k vecinos se buscan únicamente entre dominios con
    encuesta); el resto de la matriz no se usa.

    Args:
        tipo (str): ``"knn"`` o ``"inversa"``.
        parametro (float): k o potencia.
        estructura (str): ``"completa"`` o ``"muestra"``.

    Returns:
        np.ndarray: Matriz (n + r, n + r).
    """
    P = proximidad_escenario(D_km, tipo, parametro)
    if estructura == "muestra":
        P = P.copy()
        P[:n, :n] = proximidad_escenario(D_km[:n, :n], tipo, parametro)
    return P


residuos_clasico = df[Y_COL].values - clasico.mu_hat
filas = []
for nombre, tipo, parametro in ESCENARIOS_W:
    W_muestra = estandarizar_filas(proximidad_escenario(D_km[:n, :n], tipo, parametro))
    for etiqueta, valores in [
        ("residuos_clasico", residuos_clasico),
        ("tasa_directa", df[Y_COL].values),
    ]:
        m = moran_i(valores, W_muestra, N_PERMUTACIONES_MORAN, SEMILLA_ESPACIAL)
        filas.append({"escenario": nombre, "variable": etiqueta, **m})
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
# MAGIC ΔAIC > 2 **y** p(LRT) < 0.05.

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
df_comparacion["espacial_preferido"] = (
    df_comparacion["Delta_AIC"] > DELTA_AIC_EQUIVALENTE
) & (df_comparacion["p_LRT"] < ALFA_LRT)
mostrar(df_comparacion.round(4))
print(
    "Delta_AIC = AIC clásico − AIC espacial (positivo favorece al espacial). "
    f"Preferido: ΔAIC > {DELTA_AIC_EQUIVALENTE} y p(LRT) < {ALFA_LRT}."
)

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
# MAGIC Se toma como mejor escenario espacial el de menor AIC con la estructura completa (la
# MAGIC única que produce efecto espacial en los objetivos) entre los que tienen ρ̂ interior
# MAGIC (|ρ̂| < 0.99; un ρ̂ pegado a la cota es un artefacto de verosimilitud plana). Se declara **preferido el espacial**
# MAGIC solo si cumple ΔAIC > 2 y p(LRT) < 0.05; el resultado de la validación
# MAGIC dejar-uno-fuera se reporta como evidencia complementaria, no como criterio de decisión.

# COMMAND ----------

completas = df_comparacion[df_comparacion["estructura"] == "completa"]
# Un ρ̂ pegado a la cota (|ρ̂| = RHO_LIMITE) no es una estimación sino un artefacto de una
# verosimilitud plana; esos escenarios solo se usan si no queda ninguno con ρ̂ interior.
interiores = completas[completas["rho_hat"].abs() < RHO_LIMITE - 1e-6]
candidatas = interiores if len(interiores) else completas
mejor = candidatas.loc[candidatas["AIC"].idxmin()]
mejor_nombre = mejor["escenario"]
espacial_preferido = bool(mejor["espacial_preferido"])
en_cota = completas.loc[~completas.index.isin(interiores.index), "escenario"].tolist()
if en_cota:
    print(f"Escenarios con ρ̂ en la cota (descartados como referencia): {en_cota}")

met_mejor = df_validacion[
    (df_validacion["escenario"] == mejor_nombre)
    & (df_validacion["estructura"] == "completa")
].set_index("predictor")
rmse_clasico = met_mejor.loc["pred_clasico", "RMSE"]
rmse_espacial = met_mejor.loc["pred_espacial", "RMSE"]

print(f"Mejor escenario espacial por AIC (estructura completa): {mejor_nombre}")
print(
    f"  ρ̂ = {mejor['rho_hat']:.3f}   σ̂²_u = {mejor['A_hat']:.3f} (clásico {clasico.A_hat:.3f})   "
    f"ΔAIC = {mejor['Delta_AIC']:.2f}   p(LRT) = {mejor['p_LRT']:.4f}"
)
print(
    f"  Validación dejar-uno-fuera, RMSE: clásico {rmse_clasico:.3f}  vs  "
    f"espacial con efecto {rmse_espacial:.3f}"
)
if espacial_preferido:
    print("  → Se cumple el criterio: el modelo espacial es preferido al clásico.")
else:
    print(
        "  → NO se cumple el criterio (ΔAIC > 2 y p(LRT) < 0.05): los datos no justifican ρ ≠ 0; "
        "se recomienda el Fay-Herriot clásico y el espacial queda como análisis de sensibilidad."
    )

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

pred = obj[
    ["CODIGO_DEPARTAMENTO", "CODIGO_MUNICIPIO", "MUNICIPIO", "LATITUD", "LONGITUD"]
].copy()
pred["PRED_CLASICO"] = pred_clasico
pred["CV_CLASICO_PCT"] = 100 * np.sqrt(mse_clasico) / np.abs(pred_clasico)
pred["PRED_SINT_ESPACIAL"] = final.sintetico_objetivo
pred["CV_SINT_ESPACIAL_PCT"] = (
    100 * np.sqrt(final.mse_sintetico_objetivo) / np.abs(final.sintetico_objetivo)
)
pred["EFECTO_ESPACIAL"] = final.pred_objetivo - final.sintetico_objetivo
pred["PRED_ESPACIAL"] = final.pred_objetivo
pred["CV_ESPACIAL_PCT"] = (
    100 * np.sqrt(final.mse_objetivo) / np.abs(final.pred_objetivo)
)
pred["DIF_ESPACIAL_VS_CLASICO"] = pred["PRED_ESPACIAL"] - pred["PRED_CLASICO"]
# marca_extrapolacion (B20) recibe la matriz de diseño de los municipios objetivo, no x'Cov(β̂)x.
pred["EXTRAPOLA"] = marca_extrapolacion(X_obj, clasico)
pred["FUERA_DE_RANGO"] = marca_fuera_de_rango(
    pred["PRED_CLASICO"].values, TASA_MINIMA, TASA_MAXIMA
)
pred["KM_DOMINIO_CERCANO"] = D_km[n:, :n].min(axis=1)
pred["RECOMENDADO"] = "ESPACIAL" if espacial_preferido else "CLASICO"
col_rec = "CV_ESPACIAL_PCT" if espacial_preferido else "CV_CLASICO_PCT"
pred["CONFIABILIDAD_RECOMENDADO"] = pred[col_rec].apply(clasificar_confiabilidad)
pred["PER"], pred["MES"] = obj["PER"].values, obj["MES"].values
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
    f"|efecto| > 0.5 pp en {int((pred['EFECTO_ESPACIAL'].abs() > 0.5).sum())} de {r} municipios."
)
print(
    "CV mediano: clásico {:.1f} %, espacial {:.1f} %".format(
        pred["CV_CLASICO_PCT"].median(), pred["CV_ESPACIAL_PCT"].median()
    )
)
print(
    f"Municipios que extrapolan (covariables fuera de la nube de la muestra): "
    f"{int(pred['EXTRAPOLA'].sum())} de {r}; tasas fuera de [0, 100]: "
    f"{int(pred['FUERA_DE_RANGO'].sum())}."
)
print("Confiabilidad del predictor recomendado:")
print(pred["CONFIABILIDAD_RECOMENDADO"].value_counts().to_string())

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
    "rmse_cv_clasico": round(float(rmse_clasico), 4),
    "rmse_cv_espacial": round(float(rmse_espacial), 4),
    "espacial_preferido": espacial_preferido,
    "bootstrap_validas": int(final.n_bootstrap_validas),
    "n_extrapola": int(pred["EXTRAPOLA"].sum()),
    "n_fuera_de_rango": int(pred["FUERA_DE_RANGO"].sum()),
}
print(json.dumps(resumen_corrida, ensure_ascii=False, indent=2))
try:
    dbutils.notebook.exit(json.dumps(resumen_corrida))
except NameError:
    pass
