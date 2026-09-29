"""Diagnósticos que sustentan decisiones sobre las covariables candidatas.

A diferencia de `descriptivos.py`, cuyo propósito es comprender los datos, cada función de
este módulo produce evidencia destinada a una decisión concreta:

* `ic_fisher_pearson()` acota la incertidumbre de la correlación con la respuesta; un
  intervalo que contiene el cero indica que la evidencia no determina siquiera el signo.
* `influencia_por_covariable()` y `estabilidad_loo()` determinan si la asociación entre una
  covariable y la respuesta depende de un único dominio.
* `vif_conjunto()` verifica que el conjunto finalmente elegido no presente
  multicolinealidad.

Todos son diagnósticos de estadística básica, elegidos porque su lectura es directa y se
sostiene con 23 dominios. No se calcula el índice de Moran: el modelo Fay-Herriot clásico
supone efectos aleatorios independientes por dominio y el proyecto no ajusta variantes
espaciales, de modo que el contraste no tiene consecuencia sobre ninguna decisión. Tampoco
se contrasta la normalidad de las covariables, que el modelo no supone.
"""

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.outliers_influence import OLSInfluence, variance_inflation_factor
from statsmodels.tools import add_constant


def ic_fisher_pearson(x: np.ndarray, y: np.ndarray, alfa: float = 0.05) -> tuple:
    """Intervalo de confianza para el coeficiente de Pearson por transformación de Fisher.

    Con 23 dominios el error estándar de una correlación es grande y un coeficiente
    puntual comunica más certeza de la que hay. El intervalo de Fisher es analítico, no
    remuestrea y es el procedimiento estándar de los textos de estadística básica, de modo
    que su interpretación se sostiene sin explicaciones adicionales.

    Args:
        x (np.ndarray): Covariable.
        y (np.ndarray): Variable respuesta.
        alfa (float): Nivel de significancia; el intervalo es de ``1 - alfa``.

    Returns:
        tuple[float, float]: Extremos inferior y superior del intervalo.

    Raises:
        ValueError: Si hay menos de cuatro observaciones.

    Example:
        >>> ic_fisher_pearson(x, Y)
        (0.038, 0.723)
    """
    n = len(x)
    if n < 4:
        raise ValueError(
            "La transformación de Fisher requiere al menos cuatro observaciones."
        )
    r = float(np.corrcoef(x, y)[0, 1])
    z = np.arctanh(np.clip(r, -0.999999, 0.999999))
    error = stats.norm.ppf(1 - alfa / 2) / np.sqrt(n - 3)
    return float(np.tanh(z - error)), float(np.tanh(z + error))


def tabla_ic_correlacion(
    df: pd.DataFrame,
    columnas: list,
    y: np.ndarray,
    alias: dict = None,
    alfa: float = 0.05,
) -> pd.DataFrame:
    """Correlación de Pearson con la respuesta y su intervalo de Fisher, por covariable.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar.
        y (np.ndarray): Variable respuesta.
        alias (dict | None): Mapa columna → alias legible.
        alfa (float): Nivel de significancia del intervalo.

    Returns:
        pd.DataFrame: Una fila por covariable con `Pearson_r`, `IC_inf`, `IC_sup` y
            `IC_contiene_cero` (`"sí"`/`"no"`), ordenada por |r| descendente.

    Example:
        >>> tabla_ic_correlacion(df_cand, codigos, Y, alias)
    """
    alias = alias or {}
    filas = []
    for col in columnas:
        x = pd.to_numeric(df[col], errors="coerce").values
        inferior, superior = ic_fisher_pearson(x, y, alfa=alfa)
        r = float(np.corrcoef(x, y)[0, 1])
        filas.append(
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "Pearson_r": round(r, 3),
                "IC_inf": round(inferior, 3),
                "IC_sup": round(superior, 3),
                "IC_contiene_cero": "sí" if inferior <= 0 <= superior else "no",
            }
        )
    return pd.DataFrame(filas).sort_values("Pearson_r", key=abs, ascending=False)


def influencia_por_covariable(
    df: pd.DataFrame,
    columnas: list,
    y: np.ndarray,
    etiquetas_dominio: np.ndarray,
    alias: dict = None,
) -> pd.DataFrame:
    """Distancia de Cook de cada dominio en la regresión simple covariable → respuesta.

    Mide cuánto cambia el vector de coeficientes al eliminar un dominio. Con 23
    observaciones un solo punto puede determinar la pendiente, de modo que este diagnóstico
    distingue una asociación sostenida por el conjunto de los dominios de una sostenida por
    uno solo. Se usa el umbral convencional ``D > 4/n``.

    Superar el umbral **no justifica eliminar el dominio**: los valores extremos observados
    corresponden a territorios reales, no a errores de medición. La consecuencia es sobre la
    covariable, no sobre la observación.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar.
        y (np.ndarray): Variable respuesta.
        etiquetas_dominio (np.ndarray): Nombre de cada dominio.
        alias (dict | None): Mapa columna → alias legible.

    Returns:
        pd.DataFrame: Una fila por covariable con la distancia de Cook máxima, el número de
            dominios que superan el umbral y su identificación.

    Example:
        >>> influencia_por_covariable(df_cand, codigos, Y, entidades, alias)
    """
    alias = alias or {}
    umbral = 4 / len(y)
    filas = []

    for col in columnas:
        x = pd.to_numeric(df[col], errors="coerce").values.reshape(-1, 1)
        modelo = OLS(y, add_constant(x)).fit()
        cook = OLSInfluence(modelo).cooks_distance[0]
        influyentes = [
            f"{etiquetas_dominio[i]} ({cook[i]:.3f})"
            for i in np.where(cook > umbral)[0]
        ]
        filas.append(
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "Cook_max": round(float(cook.max()), 4),
                "Umbral": round(umbral, 4),
                "N_influyentes": len(influyentes),
                "Dominios_influyentes": "; ".join(influyentes) if influyentes else "—",
            }
        )

    return pd.DataFrame(filas)


def estabilidad_loo(
    df: pd.DataFrame,
    columnas: list,
    y: np.ndarray,
    etiquetas_dominio: np.ndarray,
    alias: dict = None,
) -> pd.DataFrame:
    """Cambio en la correlación con la respuesta al excluir cada dominio, uno a uno.

    Recorre **todos** los dominios, no un subconjunto elegido a mano. La versión original
    evaluaba solo cinco territorios seleccionados por inspección de los diagramas de caja,
    lo que introducía una decisión manual difícil de reproducir y dependía de un cotejo de
    nombres propenso a fallar. Recorrer los 23 dominios cuesta lo mismo y elimina ambos
    problemas.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar.
        y (np.ndarray): Variable respuesta.
        etiquetas_dominio (np.ndarray): Nombre de cada dominio.
        alias (dict | None): Mapa columna → alias legible.

    Returns:
        pd.DataFrame: Una fila por covariable con la correlación completa, el cambio máximo
            en valor absoluto, el dominio responsable y si la exclusión de algún dominio
            invierte el signo de la asociación.

    Example:
        >>> estabilidad_loo(df_cand, codigos, Y, entidades, alias)
    """
    alias = alias or {}
    n = len(y)
    filas = []

    for col in columnas:
        x = pd.to_numeric(df[col], errors="coerce").values
        r_completo = float(stats.pearsonr(x, y)[0])

        deltas = np.empty(n)
        signos_invertidos = []
        for i in range(n):
            mascara = np.ones(n, dtype=bool)
            mascara[i] = False
            r_loo = float(stats.pearsonr(x[mascara], y[mascara])[0])
            deltas[i] = r_loo - r_completo
            if np.sign(r_loo) != np.sign(r_completo):
                signos_invertidos.append(etiquetas_dominio[i])

        idx_max = int(np.argmax(np.abs(deltas)))
        filas.append(
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "r_completo": round(r_completo, 3),
                "Delta_max": round(float(deltas[idx_max]), 3),
                "Delta_max_abs": round(float(np.abs(deltas).max()), 3),
                "Dominio_critico": etiquetas_dominio[idx_max],
                "Invierte_signo": (
                    ", ".join(signos_invertidos) if signos_invertidos else "—"
                ),
            }
        )

    return pd.DataFrame(filas)


def vif_conjunto(df: pd.DataFrame, columnas: list, alias: dict = None) -> pd.DataFrame:
    """Factor de inflación de la varianza de un conjunto de covariables.

    Se calcula sobre el conjunto que efectivamente podría entrar al modelo, no sobre el
    universo de candidatas: con 23 dominios, un sistema con muchas más covariables que
    grados de libertad produce un factor sin sentido. Para juzgar redundancia dentro del
    conjunto amplio de candidatas se usa la correlación por pares.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables del conjunto a verificar.
        alias (dict | None): Mapa columna → alias legible.

    Returns:
        pd.DataFrame: Una fila por covariable con su factor de inflación de la varianza.
            Con una sola covariable el factor es 1 por definición.

    Example:
        >>> vif_conjunto(df_cand, seleccionadas, alias)
    """
    alias = alias or {}
    if len(columnas) < 2:
        return pd.DataFrame(
            [{"Alias": alias.get(c, c), "Codigo": c, "VIF": 1.0} for c in columnas]
        )

    matriz = add_constant(df[columnas].astype(float).values)
    return pd.DataFrame(
        [
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "VIF": round(float(variance_inflation_factor(matriz, i + 1)), 3),
            }
            for i, col in enumerate(columnas)
        ]
    )


def figura_robustez(
    influencia: pd.DataFrame, estabilidad: pd.DataFrame, umbral_delta: float = 0.10
):
    """Sitúa cada covariable frente a los dos criterios de robustez, en un solo gráfico.

    El eje horizontal es la distancia de Cook máxima y el vertical el cambio máximo en la
    correlación al excluir un dominio. Las líneas marcan los umbrales: solo las covariables
    que quedan simultáneamente a la derecha y por encima se descartan, porque solo en ese
    cuadrante un dominio domina la regresión *y* su exclusión altera la asociación.

    Args:
        influencia (pd.DataFrame): Salida de `influencia_por_covariable()`.
        estabilidad (pd.DataFrame): Salida de `estabilidad_loo()`.
        umbral_delta (float): Umbral del eje vertical.

    Returns:
        matplotlib.figure.Figure: Figura del plano de robustez.

    Example:
        >>> fig = figura_robustez(df_cook, df_loo)
    """
    import matplotlib.pyplot as plt

    unido = influencia.merge(estabilidad, on="Codigo", suffixes=("", "_loo"))
    umbral_cook = float(unido["Umbral"].iloc[0])

    fig, ax = plt.subplots(figsize=(8.5, 6))
    descartadas = (unido["Cook_max"] > umbral_cook) & (
        unido["Delta_max_abs"] > umbral_delta
    )

    ax.scatter(
        unido.loc[~descartadas, "Cook_max"],
        unido.loc[~descartadas, "Delta_max_abs"],
        s=70,
        color="steelblue",
        edgecolors="white",
        zorder=3,
        label="No supera ambos umbrales",
    )
    ax.scatter(
        unido.loc[descartadas, "Cook_max"],
        unido.loc[descartadas, "Delta_max_abs"],
        s=70,
        color="firebrick",
        edgecolors="white",
        zorder=3,
        label="Supera ambos umbrales",
    )

    for _, fila in unido.iterrows():
        ax.annotate(
            fila["Alias"],
            (fila["Cook_max"], fila["Delta_max_abs"]),
            textcoords="offset points",
            xytext=(5, 4),
            fontsize=7,
            color="dimgray",
        )

    ax.axvline(
        umbral_cook,
        color="dimgray",
        linestyle="--",
        linewidth=1.2,
        label=f"Cook = 4/n = {umbral_cook:.3f}",
    )
    ax.axhline(
        umbral_delta,
        color="dimgray",
        linestyle=":",
        linewidth=1.2,
        label=f"Cambio en la correlación = {umbral_delta}",
    )
    ax.set_xlabel("Distancia de Cook máxima", fontsize=10)
    ax.set_ylabel("Cambio máximo en la correlación al excluir un dominio", fontsize=10)
    ax.legend(fontsize=9, loc="best")
    plt.tight_layout()
    return fig


def interpretar_robustez(
    influencia: pd.DataFrame, estabilidad: pd.DataFrame, umbral_delta: float = 0.10
) -> str:
    """Lectura textual del plano de robustez, calculada desde las tablas de diagnóstico.

    Args:
        influencia (pd.DataFrame): Salida de `influencia_por_covariable()`.
        estabilidad (pd.DataFrame): Salida de `estabilidad_loo()`.
        umbral_delta (float): Umbral del cambio en la correlación.

    Returns:
        str: Interpretación lista para imprimir junto a la figura.

    Example:
        >>> print(interpretar_robustez(df_influencia, df_estabilidad))
    """
    unido = influencia.merge(estabilidad, on="Codigo", suffixes=("", "_loo"))
    umbral_cook = float(unido["Umbral"].iloc[0])
    apalancadas = unido[unido["Cook_max"] > umbral_cook]
    inestables = unido[
        (unido["Delta_max_abs"] > umbral_delta) | (unido["Invierte_signo"] != "—")
    ]
    ambas = unido[
        (unido["Cook_max"] > umbral_cook)
        & ((unido["Delta_max_abs"] > umbral_delta) | (unido["Invierte_signo"] != "—"))
    ]

    dominios = pd.Series(
        [
            d.split(" (")[0]
            for cadena in apalancadas["Dominios_influyentes"]
            for d in cadena.split("; ")
            if d != "—"
        ]
    )
    frecuentes = (
        ", ".join(f"{k} ({v})" for k, v in dominios.value_counts().head(3).items())
        if not dominios.empty
        else "—"
    )

    lineas = [
        "INTERPRETACIÓN DEL PLANO DE ROBUSTEZ:",
        f"  Covariables con un dominio que domina la regresión (Cook > {umbral_cook:.3f}): "
        f"{len(apalancadas)} de {len(unido)}",
        f"  Dominios que más veces resultan influyentes: {frecuentes}",
        f"  Covariables cuya correlación cambia más de {umbral_delta} o invierte el signo al excluir un dominio: "
        f"{len(inestables)}",
        f"  Covariables que cumplen ambas condiciones y se descartan: {len(ambas)}"
        + (f" ({', '.join(ambas['Alias'])})" if len(ambas) else ""),
    ]
    if len(apalancadas) and not len(ambas):
        lineas.append(
            "  Lectura: hay dominios extremos, pero ninguno altera por sí solo la asociación; las "
            "covariables se conservan porque la relación no depende de un único territorio."
        )
    return "\n".join(lineas)
