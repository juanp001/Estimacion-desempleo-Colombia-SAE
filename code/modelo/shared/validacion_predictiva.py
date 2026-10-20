"""Validación predictiva del benchmark: dejar-un-dominio-fuera (LOAO) con dos ejercicios (G7-B19).

El modelo se usa para predecir municipios **sin estimación directa**, donde el predictor es
solo el sintético x'β̂ (Benedetti et al., 2024, p. 144; Morales et al., p. 441). Ninguna cifra
del ajuste con los 23 dominios dice qué tan bien predice así: el EBLUP de un dominio con
encuesta se apoya en su propia estimación directa. La validación imita el uso real. Para cada
dominio d:

1. se retira d y se ajusta el modelo con los demás (reestimando Â y β̂);
2. se predice d como si no tuviera encuesta, con x_d'β̂(-d);
3. se compara la predicción con la estimación directa y_d.

Se hacen **dos ejercicios** que responden preguntas distintas:

* **Covariables fijas (M2)**: la especificación del benchmark se mantiene y solo se reajustan
  los coeficientes. Mide el error de predicción de *ese modelo*, pero es optimista: las
  covariables se escogieron viendo a los 23 dominios, también al retirado.
* **Procedimiento completo**: en cada iteración se repite todo lo que llevó al benchmark con
  los 22 dominios que quedan: la selección de covariables (Fay-Herriot univariado con
  ψ_d, control de falsos descubrimientos, robustez, redundancia, parsimonia y VIF; la misma
  de `eda_seleccion_covariables`, en `analisis/shared/seleccion.seleccionar_covariables`) y la
  elección de la especificación (conjunto, dejar-una-fuera, significancia, AIC y parsimonia;
  `seleccion_modelo.elegir_ganador`). Mide el error de predicción **del procedimiento**, que
  es lo que se reporta cuando la selección se hizo con los mismos datos. La diferencia entre
  los dos errores es el costo de haber seleccionado con los datos.

Además de la RMSE se reportan errores **estandarizados**, porque la estimación directa y_d no
es el valor verdadero sino una medida con varianza ψ_d, y ψ_d cambia mucho entre dominios:

* ``Z_psi = (pred − y_d)/√ψ_d``: el error medido en unidades del ruido de muestreo de y_d. Un
  |Z_psi| grande es un error que el ruido de la directa no alcanza a explicar.
* ``Z_pred = (pred − y_d)/√(ψ_d + x'Cov(β̂)x + Â)``: el error medido contra su desviación
  esperada si el modelo fuera correcto. Debe tener media cercana a 0, varianza cercana a 1 y
  cobertura cercana al nivel nominal; si no, el MSE sintético subestima (o sobrestima) el error.

También se reporta el error corregido por ruido, ``√media(e² − ψ_d)``, la comparación con un
modelo sin covariables (solo intercepto, con el mismo procedimiento de validación) y el error
dentro de muestra, para mostrar cuánto optimismo hay en el ajuste con los 23 dominios.

Alcance: es un análisis propio. Morales et al. (2021) no desarrollan la validación cruzada por
área para el Fay-Herriot; sí respaldan su lectura (en un área fuera de muestra el predictor es
x'β̂, p. 441; el MSE sintético es condicional al modelo, p. 3). Con n = 23, 23 predicciones
dan métricas de baja precisión y deben leerse como orden de magnitud. El pre-filtrado
(completitud y variabilidad de TerriData) no depende de la respuesta y no se repite.
"""

import contextlib
import io

import numpy as np
import pandas as pd
from scipy import stats

from shared.fay_herriot import FayHerriotClasico
from shared.seleccion_modelo import elegir_ganador, variantes_dejar_una_fuera

EJERCICIO_FIJAS = "COVARIABLES_FIJAS"
EJERCICIO_COMPLETO = "PROCEDIMIENTO_COMPLETO"
EJERCICIO_NULO = "SIN_COVARIABLES"
ETIQUETAS_EJERCICIO = {
    EJERCICIO_FIJAS: "Covariables de M2 fijas",
    EJERCICIO_COMPLETO: "Procedimiento completo",
    EJERCICIO_NULO: "Sin covariables (referencia)",
}


def ajustar_benchmark(
    df: pd.DataFrame,
    covars_eda: list,
    y_col: str,
    se_col: str,
    delta_aic: float,
    alfa: float,
) -> FayHerriotClasico:
    """Repite la elección del benchmark: conjunto del EDA, dejar-una-fuera y regla de parsimonia.

    Es la misma secuencia del notebook del modelo (celdas 2, 3 y 8): genera el conjunto y sus
    variantes sin una covariable, las ajusta y aplica `elegir_ganador`. Sin covariables
    ajusta el modelo de solo intercepto.

    Args:
        df (pd.DataFrame): Dominios de entrenamiento, con las covariables, `y_col` y `se_col`.
        covars_eda (list[str]): Covariables que dejó la selección (EC1). Puede estar vacío.
        y_col (str): Columna de la estimación directa.
        se_col (str): Columna del error estándar de la directa.
        delta_aic (float): Diferencia de AIC que define especificaciones equivalentes.
        alfa (float): Nivel de significancia exigido a las covariables.

    Returns:
        FayHerriotClasico: El benchmark ajustado (con `covars`).

    Example:
        >>> m = ajustar_benchmark(df_tr, ["A", "B"], "TASA", "SE", 2.0, 0.05)
        >>> m.covars
        ['A']
    """
    if not covars_eda:
        modelo = FayHerriotClasico([], df, y_col, se_col)
        modelo.ajustar()
        return modelo
    variantes = variantes_dejar_una_fuera(list(covars_eda))
    modelos = []
    for covars in variantes:
        modelo = FayHerriotClasico(covars, df, y_col, se_col)
        modelo.ajustar()
        modelos.append(modelo)
    if len(modelos) == 1:
        return modelos[0]
    with contextlib.redirect_stdout(io.StringIO()):
        return elegir_ganador(modelos, variantes, delta_aic=delta_aic, alfa=alfa)


def _fila_prediccion(
    ejercicio: str,
    d: int,
    df: pd.DataFrame,
    modelo: FayHerriotClasico,
    y_col: str,
    se_col: str,
    columnas_id: list,
    alias: dict,
) -> dict:
    """Predice el dominio retirado con el modelo ajustado sin él y arma su fila de resultados.

    Args:
        ejercicio (str): Etiqueta del ejercicio (`EJERCICIO_*`).
        d (int): Posición (0 … n−1) del dominio retirado en `df`.
        df (pd.DataFrame): Todos los dominios.
        modelo (FayHerriotClasico): Modelo ajustado con los dominios restantes.
        y_col (str): Columna de la estimación directa.
        se_col (str): Columna del error estándar de la directa.
        columnas_id (list[str]): Columnas de `df` que identifican el dominio.
        alias (dict): Mapa código → alias para mostrar las covariables.

    Returns:
        dict: Una fila con identificación, directa, ψ_d, predicción, RMSE sintético, errores
            (pred − directa) y estandarizados, y las covariables y Â del ajuste sin d.
    """
    fila_d = df.iloc[d]
    x = np.concatenate([[1.0], fila_d[list(modelo.covars)].to_numpy(dtype=float)])
    pred = float(x @ modelo.beta_hat)
    var_sintetica = float(x @ modelo.cov_beta @ x + modelo.A_hat)
    y_d = float(fila_d[y_col])
    psi = float(fila_d[se_col]) ** 2
    error = pred - y_d
    sd_pred = float(np.sqrt(psi + var_sintetica))
    return {
        "Ejercicio": ejercicio,
        **{c: fila_d[c] for c in columnas_id},
        "Directa": y_d,
        "Psi": psi,
        "SE_directa": float(np.sqrt(psi)),
        "Prediccion": pred,
        "RMSE_sintetico": float(np.sqrt(var_sintetica)),
        "Error": error,
        "Error_abs": abs(error),
        "Z_psi": error / float(np.sqrt(psi)),
        "Z_pred": error / sd_pred,
        "A_hat": float(modelo.A_hat),
        "N_covariables": len(modelo.covars),
        "Covariables": " + ".join(alias.get(c, c) for c in modelo.covars) or "—",
    }


def loao_covariables_fijas(
    covars: list,
    df: pd.DataFrame,
    y_col: str,
    se_col: str,
    columnas_id: list,
    alias: dict = None,
    ejercicio: str = EJERCICIO_FIJAS,
) -> pd.DataFrame:
    """Ejercicio 1: dejar-un-dominio-fuera con las covariables del benchmark fijas.

    Para cada dominio se reajusta el modelo (con Â reestimada) sin él y se predice con el
    sintético x_d'β̂(-d). Con `covars=[]` es el modelo de solo intercepto, la referencia.

    Args:
        covars (list[str]): Covariables del benchmark (M2); vacío para la referencia.
        df (pd.DataFrame): Los n dominios con encuesta.
        y_col (str): Columna de la estimación directa.
        se_col (str): Columna del error estándar de la directa.
        columnas_id (list[str]): Columnas de `df` que identifican el dominio en la salida.
        alias (dict | None): Mapa código → alias para el texto de las covariables.
        ejercicio (str): Etiqueta del ejercicio en la salida.

    Returns:
        pd.DataFrame: Una fila por dominio (ver `_fila_prediccion`).

    Example:
        >>> cv = loao_covariables_fijas(m2.covars, df, "TASA", "SE", ["NOMBRE_DOMINIO"])
        >>> float(np.sqrt((cv["Error"] ** 2).mean()))
    """
    alias = alias or {}
    filas = []
    for d in range(len(df)):
        entrenamiento = df.drop(index=df.index[d]).reset_index(drop=True)
        modelo = FayHerriotClasico(list(covars), entrenamiento, y_col, se_col)
        modelo.ajustar()
        filas.append(
            _fila_prediccion(
                ejercicio, d, df, modelo, y_col, se_col, columnas_id, alias
            )
        )
    return pd.DataFrame(filas)


def loao_procedimiento_completo(
    df: pd.DataFrame,
    y_col: str,
    se_col: str,
    columnas_id: list,
    selector,
    delta_aic: float,
    alfa: float,
    alias: dict = None,
) -> tuple:
    """Ejercicio 2: dejar-un-dominio-fuera repitiendo la selección completa en cada iteración.

    En cada iteración, con los n−1 dominios que quedan: (1) `selector` repite la selección de
    covariables (EC1) y (2) `ajustar_benchmark` repite la elección de la especificación
    (conjunto y dejar-una-fuera, significancia, AIC y parsimonia). Con ese benchmark se predice
    el dominio retirado. Si el selector no deja ninguna covariable, el modelo es de solo
    intercepto.

    Args:
        df (pd.DataFrame): Los n dominios, con **todas** las candidatas, `y_col` y `se_col`.
        y_col (str): Columna de la estimación directa.
        se_col (str): Columna del error estándar de la directa.
        columnas_id (list[str]): Columnas de `df` que identifican el dominio; la última es el
            nombre, que rotula cada iteración en la tabla de selección.
        selector (callable): ``selector(df_entrenamiento) -> list[str]`` con las covariables
            que elige el procedimiento de selección con esos dominios.
        delta_aic (float): Diferencia de AIC que define especificaciones equivalentes.
        alfa (float): Nivel de significancia exigido a las covariables.
        alias (dict | None): Mapa código → alias para el texto de las covariables.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: (`detalle`, `seleccion`). `detalle` tiene la fila de
            predicción por dominio. `seleccion` tiene una fila por iteración con
            `Dominio_excluido`, `Seleccion_EDA` (EC1 de esa iteración), `Benchmark` (la
            especificación elegida) y los conjuntos como listas en `_Seleccion_EDA` y
            `_Benchmark`.

    Example:
        >>> detalle, seleccion = loao_procedimiento_completo(
        ...     df, "TASA", "SE", ["NOMBRE_DOMINIO"], selector, 2.0, 0.05)
    """
    alias = alias or {}

    def texto(covars):
        return " + ".join(alias.get(c, c) for c in covars) or "—"

    filas, filas_sel = [], []
    for d in range(len(df)):
        entrenamiento = df.drop(index=df.index[d]).reset_index(drop=True)
        seleccion_eda = list(selector(entrenamiento))
        modelo = ajustar_benchmark(
            entrenamiento, seleccion_eda, y_col, se_col, delta_aic, alfa
        )
        filas.append(
            _fila_prediccion(
                EJERCICIO_COMPLETO, d, df, modelo, y_col, se_col, columnas_id, alias
            )
        )
        filas_sel.append(
            {
                "Dominio_excluido": str(df.iloc[d][columnas_id[-1]]),
                "Seleccion_EDA": texto(seleccion_eda),
                "Benchmark": texto(modelo.covars),
                "_Seleccion_EDA": seleccion_eda,
                "_Benchmark": list(modelo.covars),
            }
        )
    return pd.DataFrame(filas), pd.DataFrame(filas_sel)


def metricas_validacion_cruzada(
    detalle: pd.DataFrame, rmse_dentro_muestra: float = np.nan, nivel: float = 0.95
) -> pd.DataFrame:
    """Resume cada ejercicio: error de predicción, errores estandarizados y comparación con la referencia.

    Todos los errores son ``predicción − directa``. Columnas por ejercicio: `N`; `RMSE`,
    `MAE`, `Sesgo_medio`; `RMSE_corregido` (``√media(e² − ψ_d)``, NaN si la media es
    negativa); `Z_psi_media`, `Z_psi_sd` y `Z_psi_cuad_medio` (media de Z_psi²); `Z_pred_media`,
    `Z_pred_sd`, `Z_pred_cuad_medio`, `Z_pred_max_abs` y `Cobertura` (proporción con
    |Z_pred| ≤ cuantil normal de `nivel`); `RMSE_dentro_muestra` (error del ajuste con todos
    los dominios, compartido por los ejercicios) e `Inflacion_vs_dentro` (RMSE/RMSE dentro);
    y, si el detalle trae el ejercicio sin covariables, `Habilidad_vs_nulo`
    (``1 − MSE/MSE_nulo``: positiva si mejora al modelo de solo intercepto).

    Args:
        detalle (pd.DataFrame): Concatenación de las salidas de los ejercicios.
        rmse_dentro_muestra (float): RMSE de ``x'β̂ − y`` con los n dominios (benchmark), para
            medir el optimismo del ajuste dentro de muestra.
        nivel (float): Nivel nominal de la cobertura de ``Z_pred``.

    Returns:
        pd.DataFrame: Una fila por ejercicio, en el orden en que aparecen en `detalle`.

    Example:
        >>> metricas_validacion_cruzada(pd.concat([cv_fijas, cv_completo, cv_nulo]), 1.1)
    """
    corte = float(stats.norm.ppf(0.5 + nivel / 2))
    filas = []
    for ejercicio, g in detalle.groupby("Ejercicio", sort=False):
        e = g["Error"].to_numpy()
        corregido = float(np.mean(e**2 - g["Psi"].to_numpy()))
        filas.append(
            {
                "Ejercicio": ejercicio,
                "Descripcion": ETIQUETAS_EJERCICIO.get(ejercicio, ejercicio),
                "N": len(g),
                "RMSE": float(np.sqrt(np.mean(e**2))),
                "MAE": float(np.mean(np.abs(e))),
                "Sesgo_medio": float(e.mean()),
                "RMSE_corregido": (
                    float(np.sqrt(corregido)) if corregido > 0 else np.nan
                ),
                "Z_psi_media": float(g["Z_psi"].mean()),
                "Z_psi_sd": float(g["Z_psi"].std(ddof=1)),
                "Z_psi_cuad_medio": float((g["Z_psi"] ** 2).mean()),
                "Z_pred_media": float(g["Z_pred"].mean()),
                "Z_pred_sd": float(g["Z_pred"].std(ddof=1)),
                "Z_pred_cuad_medio": float((g["Z_pred"] ** 2).mean()),
                "Z_pred_max_abs": float(g["Z_pred"].abs().max()),
                "Cobertura": float((g["Z_pred"].abs() <= corte).mean()),
                "Nivel_nominal": nivel,
            }
        )
    tabla = pd.DataFrame(filas)
    esquema = tabla["Ejercicio"] != EJERCICIO_NULO
    tabla["RMSE_dentro_muestra"] = np.where(esquema, rmse_dentro_muestra, np.nan)
    tabla["Inflacion_vs_dentro"] = tabla["RMSE"] / tabla["RMSE_dentro_muestra"]
    if (tabla["Ejercicio"] == EJERCICIO_NULO).any():
        mse_nulo = float(
            tabla.loc[tabla["Ejercicio"] == EJERCICIO_NULO, "RMSE"].iloc[0] ** 2
        )
        tabla["Habilidad_vs_nulo"] = np.where(
            esquema, 1 - tabla["RMSE"] ** 2 / mse_nulo, np.nan
        )
    return tabla


def frecuencia_seleccion(
    seleccion: pd.DataFrame, covars_m2: list, alias: dict = None
) -> pd.DataFrame:
    """Con qué frecuencia el procedimiento elige cada covariable al retirar un dominio.

    Una covariable que entra en casi todas las iteraciones es estable frente al dominio que se
    deja fuera; una que entra en pocas depende de qué dominios estén. Se reportan dos etapas:
    la selección de covariables (EC1) y la especificación final (benchmark).

    Args:
        seleccion (pd.DataFrame): Segundo elemento de `loao_procedimiento_completo`.
        covars_m2 (list[str]): Covariables del benchmark con los n dominios.
        alias (dict | None): Mapa código → alias.

    Returns:
        pd.DataFrame: Una fila por covariable que aparece en alguna iteración o en M2, con
            `Frecuencia_EDA`, `Frecuencia_benchmark` (proporciones de las n iteraciones) y
            `En_M2`; ordenada por `Frecuencia_benchmark` descendente.

    Example:
        >>> frecuencia_seleccion(seleccion, m2.covars, ALIAS)
    """
    alias = alias or {}
    n = len(seleccion)
    codigos = sorted(
        {c for fila in seleccion["_Seleccion_EDA"] for c in fila}
        | {c for fila in seleccion["_Benchmark"] for c in fila}
        | set(covars_m2)
    )
    filas = [
        {
            "Covariable": alias.get(c, c),
            "Codigo": c,
            "Frecuencia_EDA": sum(c in fila for fila in seleccion["_Seleccion_EDA"])
            / n,
            "Frecuencia_benchmark": sum(c in fila for fila in seleccion["_Benchmark"])
            / n,
            "En_M2": "sí" if c in covars_m2 else "no",
        }
        for c in codigos
    ]
    return pd.DataFrame(filas).sort_values(
        ["Frecuencia_benchmark", "Covariable"], ascending=[False, True]
    )


def resumen_seleccion(seleccion: pd.DataFrame, covars_m2: list) -> dict:
    """Cuántas veces el procedimiento reproduce la especificación M2 al retirar un dominio.

    Args:
        seleccion (pd.DataFrame): Segundo elemento de `loao_procedimiento_completo`.
        covars_m2 (list[str]): Covariables del benchmark con los n dominios.

    Returns:
        dict: `n_iteraciones`, `n_igual_m2` (mismo conjunto), `n_distintos_conjuntos` (conjuntos
            de benchmark diferentes entre iteraciones), `n_sin_covariables` y la mediana del
            índice de Jaccard con M2.

    Example:
        >>> resumen_seleccion(seleccion, m2.covars)["n_igual_m2"]
    """
    m2 = set(covars_m2)

    def jaccard(otro):
        union = m2 | set(otro)
        return len(m2 & set(otro)) / len(union) if union else 1.0

    benchmarks = [set(b) for b in seleccion["_Benchmark"]]
    return {
        "n_iteraciones": len(seleccion),
        "n_igual_m2": sum(b == m2 for b in benchmarks),
        "n_distintos_conjuntos": len({frozenset(b) for b in benchmarks}),
        "n_sin_covariables": sum(len(b) == 0 for b in benchmarks),
        "jaccard_mediano": float(np.median([jaccard(b) for b in benchmarks])),
    }


def interpretar_validacion(
    metricas: pd.DataFrame,
    detalle: pd.DataFrame,
    resumen_sel: dict = None,
    umbral_z: float = 1.96,
) -> str:
    """Redacta la lectura de la validación calculada desde las métricas.

    No presupone el resultado: compara los ejercicios entre sí y contra la referencia sin
    covariables, y señala si los errores estandarizados son compatibles con el MSE sintético.

    Args:
        metricas (pd.DataFrame): Salida de `metricas_validacion_cruzada`.
        detalle (pd.DataFrame): Detalle por dominio de todos los ejercicios.
        resumen_sel (dict | None): Salida de `resumen_seleccion`.
        umbral_z (float): |Z_pred| a partir del cual se nombra un dominio.

    Returns:
        str: Texto con una línea por ejercicio, los dominios peor predichos y la advertencia
            sobre n = 23.

    Example:
        >>> print(interpretar_validacion(metricas, detalle, resumen_sel))
    """
    m = metricas.set_index("Ejercicio")
    lineas = []
    for ejercicio, f in m.iterrows():
        partes = [
            f"{f['Descripcion']}: RMSE {f['RMSE']:.2f} pp, MAE {f['MAE']:.2f}, sesgo "
            f"{f['Sesgo_medio']:+.2f}"
        ]
        if not np.isnan(f["RMSE_corregido"]):
            partes.append(f"RMSE corregido por ruido {f['RMSE_corregido']:.2f}")
        partes.append(
            f"Z_psi: media {f['Z_psi_media']:+.2f}, media de Z² {f['Z_psi_cuad_medio']:.2f}"
        )
        partes.append(
            f"Z_pred: media {f['Z_pred_media']:+.2f}, sd {f['Z_pred_sd']:.2f}, "
            f"cobertura {100 * f['Cobertura']:.0f} % (nominal {100 * f['Nivel_nominal']:.0f} %)"
        )
        if ejercicio != EJERCICIO_NULO and not np.isnan(
            f.get("Habilidad_vs_nulo", np.nan)
        ):
            partes.append(
                f"habilidad frente a solo intercepto {f['Habilidad_vs_nulo']:+.2f}"
            )
        lineas.append("- " + "; ".join(partes) + ".")

    if EJERCICIO_FIJAS in m.index and EJERCICIO_COMPLETO in m.index:
        r_fijas, r_comp = (
            m.loc[EJERCICIO_FIJAS, "RMSE"],
            m.loc[EJERCICIO_COMPLETO, "RMSE"],
        )
        lineas.append(
            f"- Costo de seleccionar con los mismos datos: la RMSE pasa de {r_fijas:.2f} "
            f"(covariables fijas) a {r_comp:.2f} (procedimiento completo), {r_comp / r_fijas:.2f} "
            "veces."
        )
    dentro = m["RMSE_dentro_muestra"].dropna()
    if len(dentro):
        lineas.append(
            f"- Error dentro de muestra del ajuste con todos los dominios: {dentro.iloc[0]:.2f} pp."
        )
    if resumen_sel:
        lineas.append(
            f"- El procedimiento completo reproduce M2 en {resumen_sel['n_igual_m2']} de "
            f"{resumen_sel['n_iteraciones']} iteraciones; obtiene {resumen_sel['n_distintos_conjuntos']} "
            f"conjuntos distintos (sin covariables en {resumen_sel['n_sin_covariables']}); "
            f"Jaccard mediano con M2 {resumen_sel['jaccard_mediano']:.2f}."
        )
    for ejercicio in (EJERCICIO_FIJAS, EJERCICIO_COMPLETO):
        g = detalle[
            (detalle["Ejercicio"] == ejercicio) & (detalle["Z_pred"].abs() > umbral_z)
        ]
        if len(g):
            nombre = [c for c in g.columns if c.startswith("NOMBRE")][0]
            lineas.append(
                f"- {ETIQUETAS_EJERCICIO[ejercicio]}: |Z_pred| > {umbral_z} en "
                + ", ".join(
                    f"{r[nombre]} ({r['Z_pred']:+.2f})" for _, r in g.iterrows()
                )
                + "."
            )
    lineas.append(
        "\nCon 23 dominios son 23 predicciones: las métricas tienen baja precisión y se leen "
        "como orden de magnitud. La directa es una estimación con ruido ψ_d, por eso se "
        "reportan los errores estandarizados y el RMSE corregido. El pre-filtrado de "
        "covariables no se repitió (no depende de la respuesta)."
    )
    return "\n".join(lineas)


def figura_validacion(detalle: pd.DataFrame, columna_nombre: str = "NOMBRE_DOMINIO"):
    """Figura de la validación: predicción contra directa y error estandarizado por dominio.

    Panel izquierdo: predicción fuera de muestra (eje vertical) frente a la estimación directa
    (horizontal) con la diagonal; los segmentos horizontales son ±1.96 √ψ_d de la directa.
    Panel derecho: Z_pred por dominio para los dos ejercicios del benchmark, con las líneas
    ±1.96.

    Args:
        detalle (pd.DataFrame): Detalle por dominio de los ejercicios.
        columna_nombre (str): Columna con el nombre del dominio.

    Returns:
        matplotlib.figure.Figure: Figura de dos paneles.

    Example:
        >>> fig = figura_validacion(pd.concat([cv_fijas, cv_completo]))
    """
    import matplotlib.pyplot as plt

    colores = {EJERCICIO_FIJAS: "#1f6fb2", EJERCICIO_COMPLETO: "#d95f02"}
    ejercicios = [e for e in colores if (detalle["Ejercicio"] == e).any()]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    lim = [
        float(min(detalle["Directa"].min(), detalle["Prediccion"].min())) - 1,
        float(max(detalle["Directa"].max(), detalle["Prediccion"].max())) + 1,
    ]
    ax1.plot(lim, lim, color="gray", linestyle="--", linewidth=1)
    for ejercicio in ejercicios:
        g = detalle[detalle["Ejercicio"] == ejercicio]
        ax1.errorbar(
            g["Directa"],
            g["Prediccion"],
            xerr=1.96 * g["SE_directa"],
            fmt="o",
            color=colores[ejercicio],
            alpha=0.75,
            markersize=4,
            elinewidth=0.8,
            label=ETIQUETAS_EJERCICIO[ejercicio],
        )
    ax1.set_xlabel("Estimación directa (%)")
    ax1.set_ylabel("Predicción sintética sin el dominio (%)")
    ax1.legend(fontsize=8)

    base = detalle[detalle["Ejercicio"] == ejercicios[0]]
    orden = base.sort_values("Directa")[columna_nombre].tolist()
    posicion = {nombre: i for i, nombre in enumerate(orden)}
    desfase = {
        e: (k - (len(ejercicios) - 1) / 2) * 0.25 for k, e in enumerate(ejercicios)
    }
    for ejercicio in ejercicios:
        g = detalle[detalle["Ejercicio"] == ejercicio]
        ax2.scatter(
            [posicion[n] + desfase[ejercicio] for n in g[columna_nombre]],
            g["Z_pred"],
            color=colores[ejercicio],
            s=22,
            label=ETIQUETAS_EJERCICIO[ejercicio],
        )
    for nivel in (-1.96, 0, 1.96):
        ax2.axhline(
            nivel, color="gray", linestyle="--" if nivel else "-", linewidth=0.8
        )
    ax2.set_xticks(range(len(orden)))
    ax2.set_xticklabels(orden, rotation=90, fontsize=7)
    ax2.set_ylabel("Z_pred = (pred − directa)/√(ψ + x'Cov(β̂)x + Â)")
    ax2.legend(fontsize=8)
    plt.tight_layout()
    return fig
