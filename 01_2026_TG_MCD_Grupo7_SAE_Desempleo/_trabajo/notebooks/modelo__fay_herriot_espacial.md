# modelo__fay_herriot_espacial


## Celda 0

```python
%md
# Modelo Fay-Herriot espacial (SEBLUP)

Extiende el Fay-Herriot clásico (`fay_herriot.py`) con **autocorrelación espacial** en los
efectos aleatorios: `u = ρWu + v` (SAR; Morales et al., 2021, §18.2, pp. 490-494). Con ρ = 0
se recupera el modelo clásico, así que la pregunta del notebook es si los datos justifican
ρ ≠ 0 y si eso mejora la predicción en los municipios sin encuesta.

**Dificultad central.** Los 23 dominios con encuesta son ciudades o áreas metropolitanas
dispersas por el país, y los municipios objetivo (Cauca y Valle) no son contiguos a ellos.
Por eso (a) **ρ solo se puede estimar con los dominios de la GEIH**, que son los únicos con
dato, (b) **W se define sobre todas las unidades** (con y sin encuesta) para poder
predecir, y (c) W se construye por **distancia** entre centroides (kNN o distancia
inversa), no por contigüidad.

Pasos:
1. Carga de dominios con encuesta, municipios objetivo y coordenadas.
2. Diagnóstico de vecindad: ¿qué tan cerca está cada objetivo de un dominio con encuesta?
3. Fay-Herriot clásico de referencia (mismas covariables del benchmark clásico seleccionado).
4. I de Moran de los residuos del clásico, por escenario de W.
5. Ajuste del SEBLUP por escenario y estructura, comparación contra el clásico (LRT de ρ = 0,
   AIC) y cuadro de coeficientes del clásico frente al espacial, más el I de Moran de los
   residuos del SEBLUP.
6. Perfil de verosimilitud de ρ: ¿está identificado?
7. Validación dejar-un-dominio-fuera: ¿predice mejor un municipio no visto?
8. Decisión, sensibilidad de ρ̂ al centroide de los A.M. y a los nodos sin dato, y mapa de
   residuos.
9. Predicción para los municipios objetivo (con MSE bootstrap): los municipios de un dominio
   A.M. (Cali, Yumbo) se predicen como subáreas de su nodo y se les aplica el benchmarking de
   nivel 2, como en el clásico.
10. Exportar tablas (`tesis.modelo.fhe_*`) y figuras (`fhe_*` en el volumen de figuras del
   modelo, `VOLUMEN_FIGURAS_MODELO`).

La lógica vive en `shared/matriz_proximidad.py`, `shared/fay_herriot_espacial.py` y
`shared/figuras_espacial.py`; la explicación completa y los resultados están en
`docs/fay_herriot_espacial.md`.
```


## Celda 1

```python
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


# R-67: `code/` en sys.path (el notebook está en code/<carpeta>/); `comun.entorno` hace el resto
if "CODE_DIR" not in globals():
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

    Returns:
        None: no devuelve nada; el efecto es la tabla mostrada en pantalla.

    Example:
        >>> mostrar(df_resultados)  # doctest: +SKIP
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

    Returns:
        None: no devuelve nada; el efecto es el PNG guardado y la figura mostrada.

    Example:
        >>> guardar_figura(fig, 'moran_residuos')  # doctest: +SKIP
    """
    guardar_png(fig, nombre, "fhe_", VOLUMEN_FIGURAS_MODELO)
    try:
        display(fig)
    except NameError:
        pass
    plt.close(fig)

```


## Celda 2

```python
%md
## 1. Datos

* **Covariables**: las del benchmark seleccionado del Fay-Herriot clásico (tabla
  `fh_coeficientes`), para que la única diferencia entre los dos modelos sea la estructura
  de los efectos aleatorios.
* **Dominios con encuesta**: `covariables_seleccionadas`. Un dominio puede ser un área
  metropolitana (varios municipios); se ubica en la **coordenada de su municipio capital**
  (`CODIGO_DOMINIO`), que es la decisión más simple y se declara como limitación.
* **Objetivos**: `municipios_sin_encuesta` (los mismos 83 que el clásico). Los municipios que
  pertenecen a un dominio A.M. (`CODIGO_DOMINIO_PADRE`: Cali y Yumbo en Cali A.M.) **no son
  nodos de W**, porque su territorio ya está en el nodo del A.M. (R-14): se predicen como
  subáreas de su nodo, `x'β̂ + û_D`, y se les aplica el benchmarking de nivel 2 (sección 9).
  Los demás son nodos sin encuesta.
```


## Celda 3

```python
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
```

**Salida:**

```
Covariables (benchmark clásico seleccionado): TASA_HOMICIDIOS
Municipios que son subáreas de un dominio A.M. (no son nodos de W): Cali (76001), Yumbo (76001)

Dominios con encuesta (n): 23   Nodos objetivo sin encuesta (r): 81   Subáreas de un A.M.: 2   Unidades de W: 104
CODIGO_DEPARTAMENTO
19    41
76    40

```


## Celda 4

```python
%md
## 2. Diagnóstico de vecindad

Antes de modelar: ¿hay información espacial útil? Se mide (a) la distancia de cada
objetivo al dominio con encuesta más cercano y (b) la distancia entre los propios
dominios con encuesta, que es lo que informa sobre ρ.
```


## Celda 5

```python
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
```

**Salida:**

```
Distancia de cada municipio objetivo al dominio con encuesta más cercano:

```
| CODIGO_DEPARTAMENTO | n_objetivos | min_km | mediana_km | max_km | n_a_50km | n_a_100km |
|---|---|---|---|---|---|---|
| 19 | 41 | 15.5 | 46.3 | 143.7 | 22 | 39 |
| 76 | 40 | 11.4 | 44.6 | 79.5 | 25 | 40 |
```

Entre los 23 dominios con encuesta, el vecino más cercano está a 30-158 km (mediana 106 km); 12 dominios tienen su vecino a más de 100 km.

```


## Celda 6

```python
%md
## 3. Fay-Herriot clásico (referencia)

Mismo modelo y covariables que el benchmark de `fay_herriot.py`. Su AIC (con p + 1
parámetros) es el punto de comparación; el espacial agrega un parámetro (ρ).
```


## Celda 7

```python
clasico = FayHerriotClasico(covars, df, Y_COL, SE_COL)
clasico.ajustar()
ll_clasico = -(clasico.aic - 2 * (clasico.p + 1)) / 2
print(f"Â = {clasico.A_hat:.4f}   AIC = {clasico.aic:.3f}   R² = {clasico.r2:.4f}")
print("Coeficientes:", dict(zip(["Intercepto"] + covars, clasico.beta_hat.round(4))))
print("p-valores:   ", dict(zip(["Intercepto"] + covars, clasico.p_vals.round(4))))
```

**Salida:**

```
Â = 5.5288   AIC = 108.904   R² = 0.2689
Coeficientes: {'Intercepto': 9.1908, 'TASA_HOMICIDIOS': 0.0993}
p-valores:    {'Intercepto': 0.0, 'TASA_HOMICIDIOS': 0.0058}

```


## Celda 8

```python
%md
## 4. Escenarios de W e I de Moran

Se prueban varias definiciones de W porque con 23 dominios dispersos la conclusión
podría depender de ella: k vecinos más cercanos (k = 3, 5) y distancia inversa
(potencia 1 y 2), siempre estandarizadas por filas.

El **I de Moran** se calcula sobre los residuos del Fay-Herriot clásico (`y − Xβ̂`), no sobre
la tasa cruda: lo que debe ser independiente en el modelo clásico son los efectos aleatorios,
y la tasa cruda hereda autocorrelación de las covariables. Para el Moran, W se construye solo
entre los dominios con encuesta. Con n = 23 la potencia es baja: un Moran no significativo no
prueba independencia espacial.
```


## Celda 9

```python

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

    Example:
        >>> W = proximidad_total('knn', 5, 'completa')  # doctest: +SKIP
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
```

**Salida:**

| escenario | variable | I | esperado | z_perm | p_valor |
|---|---|---|---|---|---|
| knn3 | residuos_clasico | 0.0923 | -0.0455 | 0.9812 | 0.3346 |
| knn3 | residuos_clasico_estandarizados | 0.0925 | -0.0455 | 0.9832 | 0.3331 |
| knn3 | tasa_directa | 0.0033 | -0.0455 | 0.3672 | 0.7323 |
| knn5 | residuos_clasico | 0.0047 | -0.0455 | 0.5016 | 0.6062 |
| knn5 | residuos_clasico_estandarizados | 0.005 | -0.0455 | 0.5048 | 0.6049 |
| knn5 | tasa_directa | -0.022 | -0.0455 | 0.2429 | 0.8018 |
| inversa1 | residuos_clasico | -0.0237 | -0.0455 | 0.4493 | 0.6535 |
| inversa1 | residuos_clasico_estandarizados | -0.0234 | -0.0455 | 0.4558 | 0.6496 |
| inversa1 | tasa_directa | -0.0275 | -0.0455 | 0.3742 | 0.7178 |
| inversa2 | residuos_clasico | 0.0127 | -0.0455 | 0.5412 | 0.6044 |
| inversa2 | residuos_clasico_estandarizados | 0.0134 | -0.0455 | 0.5479 | 0.5988 |
| inversa2 | tasa_directa | -0.0004 | -0.0455 | 0.4238 | 0.6884 |


## Celda 10

```python
%md
## 5. Ajuste del SEBLUP

Para cada escenario de W y cada estructura:
* `muestra`: W solo entre los dominios con encuesta (Petrucci-Salvati). Los objetivos
  reciben el sintético `Xβ̂`.
* `completa`: W entre todas las unidades y verosimilitud marginal sobre la muestra
  (Saei-Chambers; Benedetti et al., 2024). Los objetivos reciben además un efecto
  espacial `û_r = G_rs V⁻¹ (y − Xβ̂)` calculado a partir de los dominios cercanos.

Se reportan σ̂²_u, ρ̂, AIC (ML) y la **prueba de razón de verosimilitudes** de ρ = 0
contra el clásico (1 grado de libertad). El criterio para preferir el espacial es
p(LRT) < 0.05 (R-43). El ΔAIC (clásico − espacial) se reporta como descripción, pero **no es
un segundo respaldo**: como los modelos difieren en un parámetro y se comparan con la
misma verosimilitud ML, ΔAIC = LRT − 2 exactamente.

**Qué estructura prueba ρ (R-13).** La prueba principal de ρ es la de la estructura
`muestra`: el SAR solo entre los dominios con encuesta, que son los únicos con dato. En la
estructura `completa` (verosimilitud marginal, MML de Benedetti et al., 2024, ecs. 18-20; no
el estimador de Saei y Chambers) el SAR se impone también sobre los nodos sin dato, que son un
recorte (los objetivos de Cauca y Valle) y no la población de áreas del artículo: su ρ̂ es
**condicional a ese conjunto de nodos** y no tiene lectura de signo (sección 8).
```


## Celda 11

```python
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
```

**Salida:**

| escenario | estructura | A_hat | rho_hat | AIC | AIC_clasico | Delta_AIC | LRT | p_LRT | p_covariables | R2 | espacial_preferido | estructura_etiqueta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| knn3 | muestra | 5.3831 | 0.2335 | 110.5722 | 108.9036 | -1.6686 | 0.3314 | 0.5648 | 0.003 | 0.2684 | False | Muestra (Petrucci-Salvati) |
| knn3 | completa | 4.8251 | 0.3724 | 109.4033 | 108.9036 | -0.4997 | 1.5003 | 0.2206 | 0.004 | 0.2687 | False | MML (Benedetti et al., 2024) |
| knn5 | muestra | 5.5408 | 0.2064 | 110.9011 | 108.9036 | -1.9975 | 0.0025 | 0.9604 | 0.005 | 0.2686 | False | Muestra (Petrucci-Salvati) |
| knn5 | completa | 5.4691 | 0.2223 | 110.8616 | 108.9036 | -1.958 | 0.042 | 0.8377 | 0.004 | 0.2684 | False | MML (Benedetti et al., 2024) |
| inversa1 | muestra | 5.6307 | 0.3257 | 110.7904 | 108.9036 | -1.8868 | 0.1132 | 0.7366 | 0.006 | 0.2689 | False | Muestra (Petrucci-Salvati) |
| inversa1 | completa | 5.4792 | 0.891 | 110.8941 | 108.9036 | -1.9905 | 0.0095 | 0.9223 | 0.006 | 0.268 | False | MML (Benedetti et al., 2024) |
| inversa2 | muestra | 5.5288 | 0.1865 | 110.8904 | 108.9036 | -1.9868 | 0.0132 | 0.9087 | 0.005 | 0.2689 | False | Muestra (Petrucci-Salvati) |
| inversa2 | completa | 5.1013 | 0.6069 | 110.1046 | 108.9036 | -1.201 | 0.799 | 0.3714 | 0.005 | 0.2645 | False | MML (Benedetti et al., 2024) |
```
Delta_AIC = AIC clásico − AIC espacial (positivo favorece al espacial; es LRT − 2). Preferido: p(LRT) < 0.05. La prueba principal es la de la estructura «muestra» (R-13).

I de Moran: residuos estandarizados del clásico frente a los del SEBLUP

```
| escenario | variable | I | esperado | z_perm | p_valor | estructura |
|---|---|---|---|---|---|---|
| knn3 | residuos_clasico_estandarizados | 0.0925 | -0.0455 | 0.9832 | 0.3331 | None |
| knn5 | residuos_clasico_estandarizados | 0.005 | -0.0455 | 0.5048 | 0.6049 | None |
| inversa1 | residuos_clasico_estandarizados | -0.0234 | -0.0455 | 0.4558 | 0.6496 | None |
| inversa2 | residuos_clasico_estandarizados | 0.0134 | -0.0455 | 0.5479 | 0.5988 | None |
| knn3 | residuos_espacial | -0.0426 | -0.0455 | 0.042 | 0.9843 | muestra |
| knn3 | residuos_espacial | -0.1099 | -0.0455 | -0.4265 | 0.6576 | completa |
| knn5 | residuos_espacial | -0.0381 | -0.0455 | 0.0799 | 0.9382 | muestra |
| knn5 | residuos_espacial | -0.0378 | -0.0455 | 0.0822 | 0.9357 | completa |
| inversa1 | residuos_espacial | -0.0546 | -0.0455 | -0.1619 | 0.8483 | muestra |
| inversa1 | residuos_espacial | -0.0569 | -0.0455 | -0.2054 | 0.8185 | completa |
| inversa2 | residuos_espacial | -0.0689 | -0.0455 | -0.1936 | 0.8295 | muestra |
| inversa2 | residuos_espacial | -0.1151 | -0.0455 | -0.6124 | 0.5215 | completa |
```

Coeficientes: clásico frente a espacial (Δβ en errores estándar del clásico)

```
| escenario | estructura | Parametro | beta_clasico | EE_clasico | p_clasico | beta_espacial | EE_espacial | p_espacial | Delta_beta | Delta_beta_sobre_EE_clasico | rho_hat |
|---|---|---|---|---|---|---|---|---|---|---|---|
| knn3 | muestra | Intercepto | 9.1908 | 0.979 | 0.0 | 9.1323 | 1.047 | 0.0 | -0.0585 | -0.0597 | 0.2335 |
| knn3 | muestra | TASA_HOMICIDIOS | 0.0993 | 0.0359 | 0.0058 | 0.1035 | 0.0351 | 0.0032 | 0.0043 | 0.1185 | 0.2335 |
| knn3 | completa | Intercepto | 9.1908 | 0.979 | 0.0 | 9.1145 | 1.0935 | 0.0 | -0.0763 | -0.078 | 0.3724 |
| knn3 | completa | TASA_HOMICIDIOS | 0.0993 | 0.0359 | 0.0058 | 0.1017 | 0.0354 | 0.004 | 0.0025 | 0.0686 | 0.3724 |
| knn5 | muestra | Intercepto | 9.1908 | 0.979 | 0.0 | 9.1191 | 1.0501 | 0.0 | -0.0717 | -0.0732 | 0.2064 |
| knn5 | muestra | TASA_HOMICIDIOS | 0.0993 | 0.0359 | 0.0058 | 0.1008 | 0.0357 | 0.0048 | 0.0015 | 0.0415 | 0.2064 |
| knn5 | completa | Intercepto | 9.1908 | 0.979 | 0.0 | 9.0673 | 1.0683 | 0.0 | -0.1235 | -0.1261 | 0.2223 |
| knn5 | completa | TASA_HOMICIDIOS | 0.0993 | 0.0359 | 0.0058 | 0.1038 | 0.0364 | 0.0044 | 0.0045 | 0.1264 | 0.2223 |
| inversa1 | muestra | Intercepto | 9.1908 | 0.979 | 0.0 | 9.1843 | 1.1204 | 0.0 | -0.0065 | -0.0066 | 0.3257 |
| inversa1 | muestra | TASA_HOMICIDIOS | 0.0993 | 0.0359 | 0.0058 | 0.0995 | 0.0359 | 0.0055 | 0.0002 | 0.0058 | 0.3257 |
| inversa1 | completa | Intercepto | 9.1908 | 0.979 | 0.0 | 9.283 | 2.2709 | 0.0 | 0.0922 | 0.0941 | 0.891 |
| inversa1 | completa | TASA_HOMICIDIOS | 0.0993 | 0.0359 | 0.0058 | 0.0993 | 0.0358 | 0.0055 | 0.0 | 0.0004 | 0.891 |
| inversa2 | muestra | Intercepto | 9.1908 | 0.979 | 0.0 | 9.2156 | 1.0407 | 0.0 | 0.0248 | 0.0253 | 0.1865 |
| inversa2 | muestra | TASA_HOMICIDIOS | 0.0993 | 0.0359 | 0.0058 | 0.0997 | 0.0358 | 0.0054 | 0.0004 | 0.0116 | 0.1865 |
| inversa2 | completa | Intercepto | 9.1908 | 0.979 | 0.0 | 9.3938 | 1.0975 | 0.0 | 0.2029 | 0.2073 | 0.6069 |
| inversa2 | completa | TASA_HOMICIDIOS | 0.0993 | 0.0359 | 0.0058 | 0.0985 | 0.0349 | 0.0047 | -0.0007 | -0.0206 | 0.6069 |


## Celda 12

```python
%md
## 6. ¿Está identificado ρ?

Para cada ρ de una rejilla se maximiza la log-verosimilitud REML sobre σ²_u. Una curva
plana indica que los datos casi no informan sobre la autocorrelación espacial. La línea
punteada (−1.92) es el corte del intervalo de verosimilitud perfilada del 95 %.
```


## Celda 13

```python
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
```

**Salida:**

| escenario | rho_maximo | ganancia_max_vs_rho0 | IC95_rho_min | IC95_rho_max |
|---|---|---|---|---|
| knn3 | 0.35 | 0.938 | -0.15 | 0.75 |
| knn5 | 0.2 | 0.132 | -0.7 | 0.8 |
| inversa1 | 0.9 | 0.162 | -0.9 | 0.95 |
| inversa2 | 0.6 | 0.619 | -0.55 | 0.95 |
![fig](fig/modelo__fay_herriot_espacial_c13_0.png)


## Celda 14

```python
%md
## 7. Validación dejar-un-dominio-fuera

Es la prueba más cercana al uso real: predecir un municipio **no visto**. Para cada uno
de los 23 dominios se re-estima el modelo sin él y se le predice como si no tuviera
encuesta, con (a) el sintético clásico, (b) el sintético del modelo espacial y (c) el
predictor espacial con efecto. El referente es la estimación directa del dominio, que tiene
ruido; por eso se reporta también el RMSE corregido restando la varianza directa.

Con n = 23 la diferencia entre predictores es una evidencia modesta, no una prueba.
```


## Celda 15

```python
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
```

**Salida:**

| escenario | estructura | predictor | RMSE | MAE | RMSE_corregido | sesgo_medio | Z_psi_media | Z_psi_sd | Z_pred_media | Z_pred_sd | Cobertura | Nivel_nominal | Habilidad_vs_nulo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| knn3 | muestra | pred_clasico | 2.5243 | 2.1261 | 2.5062 | -0.0676 | 0.9155 | 8.8297 | -0.0157 | 1.0494 | 1.0 | 0.95 | 0.1704 |
| knn3 | muestra | pred_sint_esp | 2.53 | 2.1247 | 2.5119 | -0.0197 | 1.068 | 8.8868 | 0.0043 | 1.0562 | 1.0 | 0.95 | 0.1667 |
| knn3 | completa | pred_clasico | 2.5243 | 2.1261 | 2.5062 | -0.0676 | 0.9155 | 8.8297 | -0.0157 | 1.0494 | 1.0 | 0.95 | 0.1704 |
| knn3 | completa | pred_sint_esp | 2.4834 | 2.0936 | 2.465 | -0.0735 | 0.858 | 8.699 | -0.0176 | 1.0822 | 1.0 | 0.95 | 0.1971 |
| knn3 | completa | pred_espacial | 2.3464 | 1.9902 | 2.3269 | -0.0263 | 0.9009 | 8.2415 | 0.0055 | 1.0481 | 1.0 | 0.95 | 0.2832 |
| knn5 | muestra | pred_clasico | 2.5243 | 2.1261 | 2.5062 | -0.0676 | 0.9155 | 8.8297 | -0.0157 | 1.0494 | 1.0 | 0.95 | 0.1704 |
| knn5 | muestra | pred_sint_esp | 2.5297 | 2.1296 | 2.5116 | -0.0986 | 0.8066 | 8.8486 | -0.0277 | 1.0432 | 1.0 | 0.95 | 0.1669 |
| knn5 | completa | pred_clasico | 2.5243 | 2.1261 | 2.5062 | -0.0676 | 0.9155 | 8.8297 | -0.0157 | 1.0494 | 1.0 | 0.95 | 0.1704 |
| knn5 | completa | pred_sint_esp | 2.523 | 2.1208 | 2.5049 | -0.0746 | 0.8756 | 8.8468 | -0.02 | 1.052 | 1.0 | 0.95 | 0.1713 |
| knn5 | completa | pred_espacial | 2.5897 | 2.1967 | 2.572 | -0.022 | 1.0647 | 9.0738 | -0.0016 | 1.0954 | 1.0 | 0.95 | 0.1269 |
| inversa1 | muestra | pred_clasico | 2.5243 | 2.1261 | 2.5062 | -0.0676 | 0.9155 | 8.8297 | -0.0157 | 1.0494 | 1.0 | 0.95 | 0.1704 |
| inversa1 | muestra | pred_sint_esp | 2.4833 | 2.0744 | 2.4648 | -0.2478 | 0.2449 | 8.7077 | -0.05 | 0.9977 | 1.0 | 0.95 | 0.1972 |
| inversa1 | completa | pred_clasico | 2.5243 | 2.1261 | 2.5062 | -0.0676 | 0.9155 | 8.8297 | -0.0157 | 1.0494 | 1.0 | 0.95 | 0.1704 |
| inversa1 | completa | pred_sint_esp | 2.5671 | 2.1316 | 2.5493 | -0.0221 | 1.0671 | 8.9292 | 0.0697 | 0.7722 | 1.0 | 0.95 | 0.1421 |
| inversa1 | completa | pred_espacial | 2.6024 | 2.1619 | 2.5849 | 0.0191 | 1.2543 | 9.2398 | 0.0143 | 1.0975 | 1.0 | 0.95 | 0.1183 |
| inversa2 | muestra | pred_clasico | 2.5243 | 2.1261 | 2.5062 | -0.0676 | 0.9155 | 8.8297 | -0.0157 | 1.0494 | 1.0 | 0.95 | 0.1704 |
| inversa2 | muestra | pred_sint_esp | 2.5204 | 2.1249 | 2.5023 | -0.0284 | 1.0433 | 8.8311 | 0.003 | 1.0456 | 1.0 | 0.95 | 0.173 |
| inversa2 | completa | pred_clasico | 2.5243 | 2.1261 | 2.5062 | -0.0676 | 0.9155 | 8.8297 | -0.0157 | 1.0494 | 1.0 | 0.95 | 0.1704 |
| inversa2 | completa | pred_sint_esp | 2.5 | 2.1141 | 2.4817 | 0.1234 | 1.5575 | 8.8141 | 0.0552 | 1.055 | 1.0 | 0.95 | 0.1863 |
| inversa2 | completa | pred_espacial | 2.8587 | 2.256 | 2.8428 | 0.2416 | 2.1261 | 10.6924 | 0.1057 | 1.2568 | 0.913 | 0.95 | -0.0639 |
```
La validación deja un dominio fuera pero conserva las covariables del benchmark, que la selección eligió viendo a ese dominio: es optimista. Con el procedimiento completo, el clásico pasa de RMSE 2.08 a 3.08 (frente a 2.77 del modelo de solo intercepto), así que las diferencias entre predictores deben leerse como orden de magnitud con n = 23.

```


## Celda 16

```python
%md
### Cuadro comparativo: benchmark clásico vs. especificaciones espaciales

Resume en una sola tabla el ajuste (σ̂²_u, ρ̂, AIC, ΔAIC, LRT) y la validación
dejar-un-dominio-fuera (RMSE, RMSE corregido por el ruido de la directa, sesgo). La
primera fila es el benchmark clásico seleccionado; las demás, las ocho especificaciones
espaciales. Todas comparten las covariables.
```


## Celda 17

```python
df_cuadro = construir_cuadro_comparativo(df_comparacion, df_validacion, clasico, covars)
mostrar(df_cuadro.round(3))
```

**Salida:**

| Modelo | Tipo | Escenario_W | Estructura | Covariables | sigma2_u | rho | AIC | Delta_AIC | p_LRT | R2 | RMSE_sintetico | RMSE_con_efecto | RMSE_corregido | Sesgo_medio | Veredicto |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Clásico (benchmark) | CLASICO | — | — | TASA_HOMICIDIOS | 5.529 | None | 108.904 | 0.0 | None | 0.269 | 2.524 | None | 2.506 | -0.068 | Referencia |
| SEBLUP knn3 (muestra) | ESPACIAL | knn3 | muestra | TASA_HOMICIDIOS | 5.383 | 0.234 | 110.572 | -1.669 | 0.565 | 0.268 | 2.53 | None | 2.512 | -0.02 | No preferido (p(LRT) ≥ 0.05) |
| SEBLUP knn3 (completa) | ESPACIAL | knn3 | completa | TASA_HOMICIDIOS | 4.825 | 0.372 | 109.403 | -0.5 | 0.221 | 0.269 | 2.483 | 2.346 | 2.327 | -0.026 | No preferido (p(LRT) ≥ 0.05) |
| SEBLUP knn5 (muestra) | ESPACIAL | knn5 | muestra | TASA_HOMICIDIOS | 5.541 | 0.206 | 110.901 | -1.998 | 0.96 | 0.269 | 2.53 | None | 2.512 | -0.099 | No preferido (p(LRT) ≥ 0.05) |
| SEBLUP knn5 (completa) | ESPACIAL | knn5 | completa | TASA_HOMICIDIOS | 5.469 | 0.222 | 110.862 | -1.958 | 0.838 | 0.268 | 2.523 | 2.59 | 2.572 | -0.022 | No preferido (p(LRT) ≥ 0.05) |
| SEBLUP inversa1 (muestra) | ESPACIAL | inversa1 | muestra | TASA_HOMICIDIOS | 5.631 | 0.326 | 110.79 | -1.887 | 0.737 | 0.269 | 2.483 | None | 2.465 | -0.248 | No preferido (p(LRT) ≥ 0.05) |
| SEBLUP inversa1 (completa) | ESPACIAL | inversa1 | completa | TASA_HOMICIDIOS | 5.479 | 0.891 | 110.894 | -1.99 | 0.922 | 0.268 | 2.567 | 2.602 | 2.585 | 0.019 | No preferido (p(LRT) ≥ 0.05) |
| SEBLUP inversa2 (muestra) | ESPACIAL | inversa2 | muestra | TASA_HOMICIDIOS | 5.529 | 0.187 | 110.89 | -1.987 | 0.909 | 0.269 | 2.52 | None | 2.502 | -0.028 | No preferido (p(LRT) ≥ 0.05) |
| SEBLUP inversa2 (completa) | ESPACIAL | inversa2 | completa | TASA_HOMICIDIOS | 5.101 | 0.607 | 110.105 | -1.201 | 0.371 | 0.265 | 2.5 | 2.859 | 2.843 | 0.242 | No preferido (p(LRT) ≥ 0.05) |


## Celda 18

```python
%md
## 8. Decisión

Se toma como escenario espacial de referencia el de menor AIC con la estructura completa (la
única que produce efecto espacial en los objetivos) entre los que tienen ρ̂ interior
(|ρ̂| < 0.99; un ρ̂ pegado a la cota es un artefacto de verosimilitud plana). Se declara
**preferido el espacial** solo si la prueba de razón de verosimilitudes de ρ = 0 da
p(LRT) < 0.05 **en la estructura `muestra` de ese mismo escenario** (R-13, R-43): es la que usa
solo los dominios con dato. El ρ̂ de la estructura completa es condicional al conjunto de nodos
sin dato y no se interpreta (ver la sensibilidad más abajo). El resultado de la validación
dejar-uno-fuera se reporta como evidencia complementaria, no como criterio de decisión.
```


## Celda 19

```python
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
```

**Salida:**

```
Escenario espacial de referencia por AIC (estructura completa): knn3
  ρ̂ (completa, condicional a los nodos) = 0.372   σ̂²_u = 4.825 (clásico 5.529)
  Prueba de ρ = 0 (estructura muestra): ρ̂ = 0.234   LRT = 0.331   p(LRT) = 0.5648   (ΔAIC = LRT − 2 = -1.67)
  Validación dejar-uno-fuera, RMSE: clásico 2.524  vs  espacial con efecto 2.346
  → NO se cumple el criterio (p(LRT) < 0.05 en la estructura muestra): los datos no justifican ρ ≠ 0; se recomienda el Fay-Herriot clásico y el espacial queda como análisis de sensibilidad.

```


## Celda 20

```python
%md
### Residuos estandarizados por dominio (R-12)

Mismo dominio, misma escala de color: residuos estandarizados del clásico (÷ √(D_d + Â)) y del
SEBLUP del escenario de referencia (blanqueados con la Cholesky de V). Si el espacial capturara
dependencia que el clásico deja en los residuos, los colores agrupados del primer panel se
dispersarían en el segundo. El I de Moran de ambos está en la tabla de la sección 5.
```


## Celda 21

```python
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
```

**Salida:**

![fig](fig/modelo__fay_herriot_espacial_c21_1.png)


## Celda 22

```python
%md
### Sensibilidad de ρ̂ a la construcción de W (R-13, R-42)

* **Nodos sin dato (R-13).** ρ̂ de la estructura completa con todos los objetivos, solo los del
  Valle, solo los del Cauca y ninguno (que equivale a la estructura muestra). Si cambia de
  magnitud o de signo, el ρ̂ de la completa lo ponen los nodos sin dato y no los datos: no se
  interpreta su signo.
* **Centroide del A.M. (R-42).** El nodo de un dominio A.M. se ubica por defecto en su
  capital; aquí se compara con la media de las coordenadas de sus municipios miembro
  (`dim_dominio_geih`). Es una sensibilidad: la base sigue siendo la capital.
* **Valores de W.** k ∈ {3, 5} y potencia ∈ {1, 2} se justifican en `config.py`
  (`ESCENARIOS_W`); la conclusión se reporta sobre los cuatro, no sobre uno.
```


## Celda 23

```python
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
```

**Salida:**

```
ρ̂ de la estructura completa según los nodos sin dato incluidos:

```
| escenario | conjunto_objetivos | n_objetivos | A_hat | rho_hat | AIC | Delta_AIC | p_LRT |
|---|---|---|---|---|---|---|---|
| knn3 | todos | 81 | 4.825 | 0.372 | 109.403 | -0.5 | 0.221 |
| knn5 | todos | 81 | 5.469 | 0.222 | 110.862 | -1.958 | 0.838 |
| inversa1 | todos | 81 | 5.479 | 0.891 | 110.894 | -1.99 | 0.922 |
| inversa2 | todos | 81 | 5.101 | 0.607 | 110.105 | -1.201 | 0.371 |
| knn3 | solo Valle | 40 | 4.867 | 0.398 | 109.451 | -0.547 | 0.228 |
| knn5 | solo Valle | 40 | 5.448 | 0.273 | 110.83 | -1.927 | 0.787 |
| inversa1 | solo Valle | 40 | 5.452 | 0.99 | 110.892 | -1.988 | 0.913 |
| inversa2 | solo Valle | 40 | 4.997 | 0.69 | 110.079 | -1.175 | 0.364 |
| knn3 | solo Cauca | 41 | 5.247 | 0.262 | 110.328 | -1.424 | 0.448 |
| knn5 | solo Cauca | 41 | 5.524 | 0.157 | 110.899 | -1.996 | 0.947 |
| inversa1 | solo Cauca | 41 | 5.565 | 0.589 | 110.897 | -1.994 | 0.938 |
| inversa2 | solo Cauca | 41 | 5.466 | 0.275 | 110.789 | -1.886 | 0.735 |
| knn3 | ninguno | 0 | 5.383 | 0.234 | 110.572 | -1.669 | 0.565 |
| knn5 | ninguno | 0 | 5.541 | 0.206 | 110.901 | -1.998 | 0.96 |
| inversa1 | ninguno | 0 | 5.631 | 0.326 | 110.79 | -1.887 | 0.737 |
| inversa2 | ninguno | 0 | 5.529 | 0.187 | 110.89 | -1.987 | 0.909 |
```

ρ̂ y AIC con el nodo del A.M. en la capital frente a la media de sus municipios:

```
| escenario | estructura | rho_capital | rho_alternativo | Delta_rho | AIC_capital | AIC_alternativo | Delta_AIC_alt_menos_cap | p_LRT_capital | p_LRT_alternativo |
|---|---|---|---|---|---|---|---|---|---|
| knn3 | muestra | 0.234 | 0.234 | 0.0 | 110.572 | 110.572 | 0.0 | 0.565 | 0.565 |
| knn3 | completa | 0.372 | 0.372 | -0.0 | 109.403 | 109.444 | 0.041 | 0.221 | 0.227 |
| knn5 | muestra | 0.206 | 0.278 | 0.071 | 110.901 | 110.816 | -0.085 | 0.96 | 0.767 |
| knn5 | completa | 0.222 | 0.353 | 0.131 | 110.862 | 110.493 | -0.369 | 0.838 | 0.522 |
| inversa1 | muestra | 0.326 | 0.403 | 0.077 | 110.79 | 110.831 | 0.041 | 0.737 | 0.788 |
| inversa1 | completa | 0.891 | 0.911 | 0.02 | 110.894 | 110.89 | -0.005 | 0.922 | 0.906 |
| inversa2 | muestra | 0.187 | 0.239 | 0.053 | 110.89 | 110.848 | -0.042 | 0.909 | 0.814 |
| inversa2 | completa | 0.607 | 0.616 | 0.009 | 110.105 | 110.044 | -0.061 | 0.371 | 0.354 |


## Celda 24

```python
%md
## 9. Predicción en los municipios objetivo

Se reajusta el mejor escenario espacial con el **bootstrap paramétrico** del MSE
(Morales et al., §18.2.3, p. 494): en cada réplica se simulan los efectos SAR y los
errores de muestreo, se re-estiman σ²_u y ρ y se acumula el error del predictor frente a
la verdad simulada, de modo que el MSE incluye la incertidumbre de ρ̂.

La tabla compara tres predictores por municipio:
* `PRED_CLASICO`: sintético del Fay-Herriot clásico, con su MSE `x'Cov(β̂)x + Â` (p. 441).
* `PRED_SINT_ESPACIAL`: `Xβ̂` con el β̂ del modelo espacial.
* `PRED_ESPACIAL`: `Xβ̂ + û_r`, con el efecto espacial predicho desde los dominios cercanos.

**Subáreas de un A.M. (R-14).** Cali y Yumbo no son nodos: se predicen como
`x_m'β̂ + û_D`, con el efecto espacial predicho del nodo «Cali A.M.», y se les aplica
`benchmark_nivel2` con los mismos pesos de PET que el clásico, para que su promedio ponderado
reproduzca el SEBLUP del A.M. Antes, el EBLUP del espacial pasa por el benchmarking de nivel 1
(mismo valor de referencia que el clásico: la directa del conjunto de los 23 dominios). Su
MSE es el del sintético, `x'Cov(β̂)x + Â`; el de los demás nodos es el del bootstrap.

**Extrapolación y calidad (R-15).** `ESTADO_EXTRAPOLACION` (B20) se calcula con la
covarianza de β̂ del espacial, no con la del clásico, y la calidad reportada (B21) agrega
«condicional al modelo» y «extrapolado» como en la tabla final del clásico.

`RECOMENDADO` indica cuál usar según la decisión del paso anterior.
```


## Celda 25

```python
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
```

**Salida:**

```
Escenario knn3: ρ̂ = 0.372, σ̂²_u = 4.825; réplicas bootstrap válidas: 500 de 500
λ₁ del espacial = 0.999315 (referencia 10.8340 %)
Subáreas ajustadas a su dominio A.M. (nivel 2): 2

```
| CODIGO_DEPARTAMENTO | CODIGO_MUNICIPIO | MUNICIPIO | CODIGO_DOMINIO_PADRE | LATITUD | LONGITUD | PRED_CLASICO | CV_CLASICO_PCT | PRED_SINT_ESPACIAL | CV_SINT_ESPACIAL_PCT | EFECTO_ESPACIAL | PRED_ESPACIAL | MSE_ESPACIAL | FUENTE_MSE_ESPACIAL | CV_ESPACIAL_PCT | DIF_ESPACIAL_VS_CLASICO | KM_DOMINIO_CERCANO | PESO_N2 | LAMBDA_N2_ESPACIAL | PRED_ESPACIAL_BENCHMARK | PRED_CLASICO_BENCHMARK | ESTADO_EXTRAPOLACION | COVARIABLE_PRINCIPAL | APORTE_EXTRAPOLADO_PP | EXTRAPOLA | FUERA_DE_RANGO_CLASICO | FUERA_DE_RANGO_ESPACIAL | RECOMENDADO | CONFIABILIDAD_RECOMENDADO | CALIDAD_REPORTADA_RECOMENDADO | PER | MES |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 19 | 19022 | Almaguer | None | 1.913 | -76.856 | 14.571 | 18.146 | 14.628 | 18.577 | -0.039 | 14.589 | 7.504 | BOOTSTRAP | 18.778 | 0.018 | 67.1 | 14007.0 | 1.0 | 14.589 | 14.571 | DENTRO_DEL_RANGO |  | -0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 19 | 19050 | Argelia | None | 2.257 | -77.249 | 20.96 | 19.931 | 21.176 | 20.83 | -0.01 | 21.166 | 19.599 | BOOTSTRAP | 20.916 | 0.206 | 75.6 | 18894.0 | 1.0 | 21.166 | 20.96 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 4.741 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 19 | 19075 | Balboa | None | 2.041 | -77.216 | 16.715 | 18.252 | 16.825 | 18.58 | -0.076 | 16.749 | 10.082 | BOOTSTRAP | 18.957 | 0.034 | 82.81 | 15641.0 | 1.0 | 16.749 | 16.715 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 0.391 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 19 | 19100 | Bolívar | None | 1.838 | -76.966 | 15.452 | 18.071 | 15.531 | 18.708 | -0.389 | 15.142 | 8.728 | BOOTSTRAP | 19.51 | -0.31 | 77.717 | 29613.0 | 1.0 | 15.142 | 15.452 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 19 | 19110 | Buenos Aires | None | 3.015 | -76.642 | 16.769 | 18.266 | 16.881 | 18.466 | -0.009 | 16.872 | 9.772 | BOOTSTRAP | 18.527 | 0.103 | 46.279 | 22421.0 | 1.0 | 16.872 | 16.769 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 0.447 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 19 | 19130 | Cajibío | None | 2.623 | -76.571 | 12.971 | 18.96 | 12.988 | 18.383 | -0.111 | 12.878 | 5.885 | BOOTSTRAP | 18.837 | -0.093 | 18.483 | 30080.0 | 1.0 | 12.878 | 12.971 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 19 | 19137 | Caldono | None | 2.798 | -76.484 | 10.434 | 23.338 | 10.388 | 22.798 | -0.002 | 10.386 | 5.762 | BOOTSTRAP | 23.113 | -0.048 | 39.741 | 26711.0 | 1.0 | 10.386 | 10.434 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19142 | Caloto | None | 3.035 | -76.409 | 17.742 | 18.561 | 17.878 | 18.798 | -0.037 | 17.841 | 11.324 | BOOTSTRAP | 18.861 | 0.099 | 43.968 | 22165.0 | 1.0 | 17.841 | 17.742 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 1.444 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 19 | 19212 | Corinto | None | 3.174 | -76.262 | 31.174 | 24.095 | 31.643 | 24.721 | -0.038 | 31.605 | 60.587 | BOOTSTRAP | 24.628 | 0.431 | 39.253 | 19143.0 | 1.0 | 31.605 | 31.174 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 15.209 | True | False | False | CLASICO | No confiable | No confiable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 19 | 19256 | El Tambo | None | 2.451 | -76.811 | 17.664 | 18.534 | 17.798 | 18.515 | -0.111 | 17.686 | 10.456 | BOOTSTRAP | 18.283 | 0.023 | 23.518 | 40124.0 | 1.0 | 17.686 | 17.664 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 1.363 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 19 | 19290 | Florencia | None | 1.683 | -77.073 | 13.007 | 18.928 | 13.026 | 18.697 | -0.433 | 12.593 | 6.096 | BOOTSTRAP | 19.607 | -0.415 | 57.088 | 3968.0 | 1.0 | 12.593 | 13.007 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 19 | 19300 | Guachené | None | 3.134 | -76.392 | 18.274 | 18.758 | 18.423 | 17.926 | -0.1 | 18.324 | 10.984 | BOOTSTRAP | 18.087 | 0.05 | 34.23 | 14794.0 | 1.0 | 18.324 | 18.274 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 1.989 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 19 | 19318 | Guapi | None | 2.571 | -77.888 | 10.988 | 21.937 | 10.957 | 22.234 | -0.005 | 10.952 | 6.003 | BOOTSTRAP | 22.372 | -0.036 | 143.685 | 17650.0 | 1.0 | 10.952 | 10.988 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19355 | Inzá | None | 2.549 | -76.064 | 9.879 | 25.059 | 9.819 | 25.901 | 0.322 | 10.142 | 6.312 | BOOTSTRAP | 24.772 | 0.263 | 60.356 | 19512.0 | 1.0 | 10.142 | 9.879 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19364 | Jambaló | None | 2.778 | -76.324 | 10.86 | 22.234 | 10.825 | 21.027 | 0.011 | 10.837 | 5.205 | BOOTSTRAP | 21.053 | -0.023 | 46.78 | 12010.0 | 1.0 | 10.837 | 10.86 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19392 | La Sierra | None | 2.179 | -76.763 | 11.961 | 20.131 | 11.954 | 20.539 | -0.004 | 11.95 | 6.173 | BOOTSTRAP | 20.793 | -0.012 | 36.094 | 8165.0 | 1.0 | 11.95 | 11.961 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19397 | La Vega | None | 2.002 | -76.779 | 10.406 | 23.416 | 10.36 | 23.776 | 0.039 | 10.399 | 6.191 | BOOTSTRAP | 23.927 | -0.007 | 54.672 | 18576.0 | 1.0 | 10.399 | 10.406 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19418 | López | None | 2.847 | -77.248 | 15.067 | 18.079 | 15.137 | 17.307 | -0.017 | 15.12 | 6.994 | BOOTSTRAP | 17.491 | 0.053 | 83.909 | 11083.0 | 1.0 | 15.12 | 15.067 | DENTRO_DEL_RANGO |  | -0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 19 | 19450 | Mercaderes | None | 1.789 | -77.164 | 16.191 | 18.144 | 16.288 | 18.297 | -0.437 | 15.851 | 9.142 | BOOTSTRAP | 19.075 | -0.34 | 65.392 | 17461.0 | 1.0 | 15.851 | 16.191 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 19 | 19455 | Miranda | None | 3.255 | -76.229 | 15.837 | 18.096 | 15.926 | 18.102 | -0.043 | 15.883 | 8.434 | BOOTSTRAP | 18.284 | 0.046 | 36.983 | 23913.0 | 1.0 | 15.883 | 15.837 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 19 | 19473 | Morales | None | 2.755 | -76.629 | 11.491 | 20.911 | 11.471 | 20.238 | -0.018 | 11.454 | 5.541 | BOOTSTRAP | 20.553 | -0.037 | 32.973 | 27035.0 | 1.0 | 11.454 | 11.491 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19513 | Padilla | None | 3.221 | -76.313 | 12.187 | 19.813 | 12.186 | 20.006 | -0.116 | 12.069 | 6.172 | BOOTSTRAP | 20.584 | -0.118 | 31.506 | 7606.0 | 1.0 | 12.069 | 12.188 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 19 | 19517 | Paéz | None | 2.646 | -75.971 | 10.708 | 22.607 | 10.67 | 22.76 | 0.058 | 10.727 | 6.067 | BOOTSTRAP | 22.96 | 0.019 | 72.839 | 28298.0 | 1.0 | 10.728 | 10.708 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19532 | Patía | None | 2.116 | -76.981 | 20.504 | 19.721 | 20.709 | 20.287 | -0.006 | 20.703 | 17.789 | BOOTSTRAP | 20.372 | 0.199 | 57.094 | 27622.0 | 1.0 | 20.703 | 20.504 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 4.274 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 19 | 19533 | Piamonte | None | 1.118 | -76.328 | 11.444 | 20.997 | 11.424 | 20.952 | 0.452 | 11.876 | 5.947 | BOOTSTRAP | 20.535 | 0.432 | 97.29 | 5805.0 | 1.0 | 11.876 | 11.444 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19548 | Piendamó | None | 2.642 | -76.529 | 11.136 | 21.613 | 11.108 | 21.7 | -0.008 | 11.101 | 5.999 | BOOTSTRAP | 22.065 | -0.036 | 21.777 | 30756.0 | 1.0 | 11.101 | 11.136 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19573 | Puerto Tejada | None | 3.233 | -76.418 | 24.456 | 21.524 | 24.759 | 20.589 | -0.681 | 24.078 | 25.025 | BOOTSTRAP | 20.777 | -0.378 | 23.129 | 31375.0 | 1.0 | 24.078 | 24.456 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 8.324 | True | False | False | CLASICO | No confiable | No confiable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 19 | 19585 | Puracé | None | 2.342 | -76.497 | 9.191 | 27.712 | 9.114 | 27.196 | -0.105 | 9.009 | 6.392 | BOOTSTRAP | 28.063 | -0.182 | 17.398 | 12473.0 | 1.0 | 9.009 | 9.191 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | -0.413 | True | False | False | CLASICO | No confiable | No confiable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 19 | 19622 | Rosas | None | 2.261 | -76.74 | 12.651 | 19.265 | 12.661 | 20.37 | -0.034 | 12.627 | 6.92 | BOOTSTRAP | 20.834 | -0.024 | 27.082 | 8969.0 | 1.0 | 12.627 | 12.651 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 19 | 19693 | San Sebastián | None | 1.838 | -76.769 | 10.097 | 24.341 | 10.043 | 24.1 | 0.057 | 10.1 | 6.033 | BOOTSTRAP | 24.32 | 0.003 | 71.612 | 8576.0 | 1.0 | 10.1 | 10.097 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19698 | Santander de Quilichao | None | 3.015 | -76.485 | 15.212 | 18.072 | 15.285 | 18.598 | -0.017 | 15.268 | 8.112 | BOOTSTRAP | 18.654 | 0.056 | 44.513 | 83195.0 | 1.0 | 15.268 | 15.212 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 19 | 19701 | Santa Rosa | None | 1.701 | -76.573 | 11.05 | 21.8 | 11.02 | 21.333 | 0.367 | 11.387 | 5.616 | BOOTSTRAP | 20.813 | 0.337 | 84.416 | 3796.0 | 1.0 | 11.387 | 11.05 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19743 | Silvia | None | 2.612 | -76.38 | 9.191 | 27.712 | 9.114 | 28.404 | 0.048 | 9.162 | 6.886 | BOOTSTRAP | 28.641 | -0.029 | 29.698 | 26324.0 | 1.0 | 9.162 | 9.191 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | -0.413 | True | False | False | CLASICO | No confiable | No confiable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 19 | 19760 | Sotará | None | 2.253 | -76.613 | 11.327 | 21.222 | 11.304 | 21.574 | -0.033 | 11.27 | 6.205 | BOOTSTRAP | 22.103 | -0.057 | 23.013 | 10532.0 | 1.0 | 11.27 | 11.327 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19780 | Suárez | None | 2.96 | -76.694 | 16.658 | 18.239 | 16.767 | 18.239 | -0.007 | 16.76 | 9.445 | BOOTSTRAP | 18.337 | 0.102 | 53.973 | 22767.0 | 1.0 | 16.76 | 16.658 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 0.333 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 19 | 19785 | Sucre | None | 2.038 | -76.926 | 11.283 | 21.309 | 11.259 | 21.284 | -0.002 | 11.257 | 5.812 | BOOTSTRAP | 21.416 | -0.026 | 59.287 | 7279.0 | 1.0 | 11.257 | 11.283 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19807 | Timbío | None | 2.35 | -76.684 | 11.429 | 21.025 | 11.408 | 20.657 | -0.113 | 11.295 | 5.782 | BOOTSTRAP | 21.289 | -0.134 | 15.455 | 27132.0 | 1.0 | 11.295 | 11.429 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19809 | Timbiquí | None | 2.777 | -77.668 | 14.515 | 18.158 | 14.571 | 18.472 | -0.005 | 14.566 | 7.299 | BOOTSTRAP | 18.547 | 0.051 | 123.797 | 15556.0 | 1.0 | 14.566 | 14.515 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 19 | 19821 | Toribío | None | 2.953 | -76.27 | 10.6 | 22.885 | 10.559 | 22.773 | -0.008 | 10.551 | 5.963 | BOOTSTRAP | 23.144 | -0.049 | 58.316 | 24676.0 | 1.0 | 10.551 | 10.6 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19824 | Totoró | None | 2.51 | -76.404 | 11.212 | 21.454 | 11.186 | 20.654 | 0.034 | 11.22 | 5.535 | BOOTSTRAP | 20.968 | 0.008 | 22.462 | 16895.0 | 1.0 | 11.22 | 11.212 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 19 | 19845 | Villa Rica | None | 3.178 | -76.458 | 17.345 | 18.429 | 17.471 | 17.789 | -0.227 | 17.244 | 9.506 | BOOTSTRAP | 17.88 | -0.101 | 27.174 | 15579.0 | 1.0 | 17.244 | 17.345 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 1.037 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 76 | 76001 | Cali | 76001 | 3.414 | -76.521 | 14.355 | 18.198 | 14.407 | 17.143 | -2.837 | 11.57 | 6.1 | SINTETICO_SUBAREA | 21.347 | -2.785 | 0.0 | 1769861.0 | 1.0 | 11.566 | 11.596 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76020 | Alcalá | None | 4.675 | -75.78 | 13.426 | 18.617 | 13.455 | 17.749 | 0.559 | 14.014 | 5.319 | BOOTSTRAP | 16.457 | 0.588 | 15.914 | 10458.0 | 1.0 | 14.014 | 13.426 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76036 | Andalucía | None | 4.172 | -76.168 | 17.597 | 18.511 | 17.73 | 19.153 | 0.003 | 17.732 | 11.502 | BOOTSTRAP | 19.126 | 0.135 | 67.512 | 17002.0 | 1.0 | 17.732 | 17.597 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 1.295 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 76 | 76041 | Ansermanuevo | None | 4.795 | -75.992 | 20.0 | 19.492 | 20.192 | 18.297 | 0.028 | 20.22 | 13.781 | BOOTSTRAP | 18.359 | 0.22 | 30.192 | 12553.0 | 1.0 | 20.22 | 20.0 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 3.758 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 76 | 76054 | Argelia | None | 4.727 | -76.12 | 20.226 | 19.594 | 20.423 | 18.815 | 0.285 | 20.708 | 14.682 | BOOTSTRAP | 18.504 | 0.482 | 45.187 | 3906.0 | 1.0 | 20.708 | 20.226 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 3.989 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 76 | 76100 | Bolívar | None | 4.338 | -76.184 | 16.006 | 18.116 | 16.099 | 18.112 | 0.022 | 16.121 | 8.511 | BOOTSTRAP | 18.097 | 0.115 | 59.937 | 11491.0 | 1.0 | 16.121 | 16.006 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76109 | Buenaventura | None | 3.876 | -77.011 | 12.122 | 19.902 | 12.118 | 20.649 | -0.0 | 12.118 | 6.271 | BOOTSTRAP | 20.664 | -0.004 | 74.759 | 198421.0 | 1.0 | 12.118 | 12.122 | DENTRO_DEL_RANGO |  | -0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76111 | Guadalajara de Buga | None | 3.901 | -76.299 | 14.717 | 18.119 | 14.777 | 18.255 | -0.0 | 14.777 | 7.258 | BOOTSTRAP | 18.231 | 0.061 | 59.513 | 100404.0 | 1.0 | 14.777 | 14.717 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76113 | Bugalagrande | None | 4.208 | -76.157 | 15.721 | 18.085 | 15.807 | 18.846 | 0.018 | 15.825 | 8.93 | BOOTSTRAP | 18.884 | 0.104 | 64.13 | 18518.0 | 1.0 | 15.825 | 15.721 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76122 | Caicedonia | None | 4.335 | -75.831 | 15.734 | 18.086 | 15.82 | 18.187 | 0.707 | 16.527 | 8.217 | BOOTSTRAP | 17.344 | 0.793 | 27.861 | 22212.0 | 1.0 | 16.527 | 15.734 | DENTRO_DEL_RANGO |  | -0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76126 | Calima | None | 3.934 | -76.484 | 11.939 | 20.164 | 11.931 | 20.114 | -0.0 | 11.931 | 5.759 | BOOTSTRAP | 20.114 | -0.008 | 57.966 | 13613.0 | 1.0 | 11.931 | 11.939 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 76 | 76130 | Candelaria | None | 3.408 | -76.347 | 15.568 | 18.075 | 15.65 | 16.55 | -0.635 | 15.015 | 6.691 | BOOTSTRAP | 17.227 | -0.553 | 19.413 | 69708.0 | 1.0 | 15.015 | 15.568 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76147 | Cartago | None | 4.742 | -75.924 | 12.555 | 19.368 | 12.562 | 19.342 | -0.36 | 12.202 | 5.879 | BOOTSTRAP | 19.871 | -0.353 | 23.729 | 107996.0 | 1.0 | 12.202 | 12.555 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76233 | Dagua | None | 3.657 | -76.689 | 11.855 | 20.293 | 11.845 | 19.662 | -0.0 | 11.844 | 5.428 | BOOTSTRAP | 19.669 | -0.01 | 32.857 | 36742.0 | 1.0 | 11.844 | 11.855 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 76 | 76243 | El Águila | None | 4.906 | -76.043 | 27.017 | 22.593 | 27.383 | 22.06 | 0.269 | 27.652 | 35.486 | BOOTSTRAP | 21.543 | 0.636 | 37.518 | 6411.0 | 1.0 | 27.652 | 27.017 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 10.949 | True | False | False | CLASICO | No confiable | No confiable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 76 | 76246 | El Cairo | None | 4.761 | -76.222 | 10.641 | 22.779 | 10.601 | 22.793 | 0.287 | 10.887 | 5.9 | BOOTSTRAP | 22.31 | 0.246 | 55.83 | 4966.0 | 1.0 | 10.887 | 10.641 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 76 | 76248 | El Cerrito | None | 3.684 | -76.312 | 16.046 | 18.122 | 16.14 | 18.464 | -0.018 | 16.122 | 8.831 | BOOTSTRAP | 18.433 | 0.076 | 38.011 | 42476.0 | 1.0 | 16.122 | 16.046 | DENTRO_DEL_RANGO |  | -0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76250 | El Dovio | None | 4.51 | -76.237 | 13.659 | 18.48 | 13.693 | 18.762 | 0.011 | 13.705 | 6.599 | BOOTSTRAP | 18.745 | 0.046 | 61.73 | 6212.0 | 1.0 | 13.704 | 13.658 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76275 | Florida | None | 3.324 | -76.234 | 12.305 | 19.662 | 12.306 | 19.162 | -0.128 | 12.178 | 5.781 | BOOTSTRAP | 19.744 | -0.127 | 33.392 | 43184.0 | 1.0 | 12.178 | 12.305 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76306 | Ginebra | None | 3.724 | -76.268 | 9.191 | 27.712 | 9.114 | 27.98 | -0.003 | 9.111 | 6.519 | BOOTSTRAP | 28.024 | -0.08 | 44.52 | 17295.0 | 1.0 | 9.111 | 9.191 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | -0.413 | True | False | False | CLASICO | No confiable | No confiable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 76 | 76318 | Guacarí | None | 3.762 | -76.331 | 19.359 | 19.207 | 19.535 | 19.349 | -0.002 | 19.533 | 14.233 | BOOTSTRAP | 19.315 | 0.174 | 44.103 | 24721.0 | 1.0 | 19.533 | 19.359 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 3.101 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 76 | 76364 | Jamundí | None | 3.259 | -76.538 | 15.648 | 18.08 | 15.732 | 16.372 | -0.819 | 14.912 | 6.544 | BOOTSTRAP | 17.154 | -0.735 | 17.333 | 120685.0 | 1.0 | 14.912 | 15.648 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76377 | La Cumbre | None | 3.649 | -76.568 | 11.016 | 21.875 | 10.985 | 22.089 | -0.0 | 10.985 | 5.904 | BOOTSTRAP | 22.119 | -0.031 | 26.704 | 12819.0 | 1.0 | 10.985 | 11.016 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 76 | 76400 | La Unión | None | 4.534 | -76.1 | 14.745 | 18.114 | 14.807 | 18.095 | 0.009 | 14.816 | 7.214 | BOOTSTRAP | 18.128 | 0.07 | 46.432 | 25636.0 | 1.0 | 14.816 | 14.745 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76403 | La Victoria | None | 4.524 | -76.037 | 15.713 | 18.085 | 15.799 | 18.343 | 0.015 | 15.814 | 8.423 | BOOTSTRAP | 18.352 | 0.101 | 39.457 | 9608.0 | 1.0 | 15.814 | 15.713 | DENTRO_DEL_RANGO |  | -0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76497 | Obando | None | 4.576 | -75.975 | 14.835 | 18.102 | 14.899 | 18.025 | -0.041 | 14.858 | 7.182 | BOOTSTRAP | 18.037 | 0.023 | 32.878 | 9097.0 | 1.0 | 14.858 | 14.835 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76520 | Palmira | None | 3.532 | -76.299 | 13.624 | 18.499 | 13.658 | 18.709 | -0.136 | 13.521 | 6.589 | BOOTSTRAP | 18.983 | -0.102 | 27.956 | 270947.0 | 1.0 | 13.522 | 13.624 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76563 | Pradera | None | 3.42 | -76.242 | 15.028 | 18.081 | 15.097 | 17.472 | -0.151 | 14.946 | 6.934 | BOOTSTRAP | 17.619 | -0.082 | 31.035 | 35712.0 | 1.0 | 14.946 | 15.028 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76606 | Restrepo | None | 3.821 | -76.523 | 11.784 | 20.405 | 11.773 | 20.652 | -0.0 | 11.772 | 5.934 | BOOTSTRAP | 20.693 | -0.012 | 45.331 | 11334.0 | 1.0 | 11.772 | 11.784 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 76 | 76616 | Riofrío | None | 4.157 | -76.288 | 11.744 | 20.471 | 11.731 | 22.335 | 0.001 | 11.732 | 6.843 | BOOTSTRAP | 22.298 | -0.012 | 79.461 | 11453.0 | 1.0 | 11.732 | 11.744 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 76 | 76622 | Roldanillo | None | 4.414 | -76.152 | 11.619 | 20.682 | 11.603 | 20.995 | 0.021 | 11.624 | 5.962 | BOOTSTRAP | 21.006 | 0.005 | 54.01 | 28175.0 | 1.0 | 11.624 | 11.619 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 76 | 76670 | San Pedro | None | 3.995 | -76.229 | 13.292 | 18.707 | 13.318 | 19.797 | 0.0 | 13.318 | 6.941 | BOOTSTRAP | 19.782 | 0.026 | 72.344 | 12591.0 | 1.0 | 13.318 | 13.292 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76736 | Sevilla | None | 4.271 | -75.932 | 11.546 | 20.81 | 11.528 | 21.373 | 0.14 | 11.668 | 6.098 | BOOTSTRAP | 21.163 | 0.122 | 40.539 | 32567.0 | 1.0 | 11.668 | 11.546 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 76 | 76823 | Toro | None | 4.608 | -76.077 | 18.701 | 18.928 | 18.861 | 18.978 | 0.06 | 18.92 | 12.764 | BOOTSTRAP | 18.883 | 0.219 | 44.627 | 10759.0 | 1.0 | 18.92 | 18.701 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 2.426 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 76 | 76828 | Trujillo | None | 4.212 | -76.319 | 11.256 | 21.363 | 11.231 | 23.105 | 0.003 | 11.234 | 6.733 | BOOTSTRAP | 23.096 | -0.022 | 79.382 | 13940.0 | 1.0 | 11.234 | 11.256 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 76 | 76834 | Tuluá | None | 4.085 | -76.198 | 13.905 | 18.359 | 13.945 | 17.806 | 0.002 | 13.948 | 6.178 | BOOTSTRAP | 17.82 | 0.043 | 76.129 | 164952.0 | 1.0 | 13.948 | 13.905 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76845 | Ulloa | None | 4.704 | -75.738 | 12.824 | 19.093 | 12.838 | 18.42 | 0.649 | 13.486 | 5.334 | BOOTSTRAP | 17.125 | 0.663 | 11.448 | 4081.0 | 1.0 | 13.486 | 12.824 | DENTRO_DEL_RANGO |  | -0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |
| 76 | 76863 | Versalles | None | 4.575 | -76.199 | 11.924 | 20.186 | 11.916 | 21.345 | 0.048 | 11.964 | 6.573 | BOOTSTRAP | 21.43 | 0.039 | 57.627 | 5456.0 | 1.0 | 11.964 | 11.924 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 76 | 76869 | Vijes | None | 3.699 | -76.442 | 9.97 | 24.752 | 9.913 | 24.328 | -0.002 | 9.911 | 5.837 | BOOTSTRAP | 24.378 | -0.059 | 32.897 | 9668.0 | 1.0 | 9.911 | 9.97 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 76 | 76890 | Yotoco | None | 3.861 | -76.383 | 11.05 | 21.8 | 11.02 | 22.086 | -0.0 | 11.019 | 5.956 | BOOTSTRAP | 22.147 | -0.03 | 52.089 | 12090.0 | 1.0 | 11.02 | 11.05 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | No confiable | No confiable · condicional al modelo | 2018 | 12 |
| 76 | 76892 | Yumbo | 76001 | 3.54 | -76.5 | 16.959 | 18.315 | 17.075 | 17.28 | -2.837 | 14.238 | 8.706 | SINTETICO_SUBAREA | 20.723 | -2.721 | 14.256 | 82360.0 | 1.0 | 14.233 | 13.698 | FUERA_DEL_RANGO | TASA_HOMICIDIOS | 0.641 | True | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 2018 | 12 |
| 76 | 76895 | Zarzal | None | 4.393 | -76.071 | 14.399 | 18.186 | 14.452 | 17.859 | 0.106 | 14.558 | 6.739 | BOOTSTRAP | 17.831 | 0.159 | 46.079 | 32001.0 | 1.0 | 14.558 | 14.399 | DENTRO_DEL_RANGO |  | 0.0 | False | False | False | CLASICO | Aceptable | Aceptable · condicional al modelo | 2018 | 12 |


## Celda 26

```python
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
```

**Salida:**

```
Resumen (puntos porcentuales de la tasa de desempleo):

```
| clásico | sintético espacial | espacial con efecto |
|---|---|---|
| 83.0 | 83.0 | 83.0 |
| 14.244 | 14.293 | 14.214 |
| 3.923 | 4.02 | 3.99 |
| 9.191 | 9.114 | 9.009 |
| 11.378 | 11.356 | 11.341 |
| 13.426 | 13.455 | 13.486 |
| 15.922 | 16.012 | 15.867 |
| 31.174 | 31.643 | 31.605 |
```
Efecto espacial: media -0.079, rango [-2.837, 0.707]; |efecto| > 0.5 pp en 8 de 83 municipios.
CV mediano: clásico 19.5 %, espacial 19.9 %
Municipios que extrapolan (covariables fuera de la nube de la muestra o combinación atípica): 21 de 83; tasas fuera de [0, 100]: clásico 0, espacial 0.
Calidad reportada del predictor recomendado:
Aceptable · condicional al modelo                                       33
No confiable · condicional al modelo                                    29
Aceptable · condicional al modelo · extrapolado (fuera del rango)       15
No confiable · condicional al modelo · extrapolado (fuera del rango)     6

```
![fig](fig/modelo__fay_herriot_espacial_c26_2.png)
![fig](fig/modelo__fay_herriot_espacial_c26_3.png)
![fig](fig/modelo__fay_herriot_espacial_c26_4.png)


## Celda 27

```python
%md
## 10. Exportar

Se escriben las tablas `tesis.modelo.fhe_*` (modo `overwrite`; no se tocan las tablas del
modelo clásico). El detalle de la validación cruzada se guarda para el escenario elegido.
```


## Celda 28

```python

def escribir(df_pandas: pd.DataFrame, tabla: str) -> None:
    """Escribe un DataFrame de pandas como tabla Delta, sobrescribiendo.

    Args:
        df_pandas (pd.DataFrame): Datos a escribir.
        tabla (str): Nombre completo `catalogo.esquema.tabla`.

    Returns:
        None: no devuelve nada; el efecto es la tabla Delta escrita.

    Example:
        >>> escribir(df_cuadro, 'tesis.modelo.fhe_cuadro_comparativo')  # doctest: +SKIP
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
```

**Salida:**

```
Tabla escrita: tesis.modelo.fhe_moran (20 filas)
Tabla escrita: tesis.modelo.fhe_vecindad (2 filas)
Tabla escrita: tesis.modelo.fhe_comparacion_modelos (8 filas)
Tabla escrita: tesis.modelo.fhe_cuadro_comparativo (9 filas)
Tabla escrita: tesis.modelo.fhe_perfil_rho (152 filas)
Tabla escrita: tesis.modelo.fhe_validacion_cruzada_metricas (20 filas)
Tabla escrita: tesis.modelo.fhe_validacion_cruzada (23 filas)
Tabla escrita: tesis.modelo.fhe_coeficientes (2 filas)
Tabla escrita: tesis.modelo.fhe_prediccion_objetivo (83 filas)
Tabla escrita: tesis.modelo.fhe_coeficientes_comparacion (16 filas)
Tabla escrita: tesis.modelo.fhe_sensibilidad_centroide (8 filas)
Tabla escrita: tesis.modelo.fhe_sensibilidad_rho_objetivos (16 filas)

```


## Celda 29

```python
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
```

**Salida:**

```
{"escenario_referencia": "knn3", "rho_hat": 0.3724, "A_hat_espacial": 4.8251, "A_hat_clasico": 5.5288, "delta_aic": -0.5, "p_lrt": 0.2206, "p_lrt_muestra": 0.5648, "rmse_cv_clasico": 2.5243, "rmse_cv_espacial": 2.3464, "espacial_preferido": false, "bootstrap_validas": 500, "n_extrapola": 21, "n_fuera_de_rango": 0}
```
