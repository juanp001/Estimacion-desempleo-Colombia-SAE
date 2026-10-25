"""Predicción espacial en los municipios que son parte de un dominio A.M. (R-14).

Cali y Yumbo pertenecen al dominio «Cali A.M.», que ya es un nodo del SAR. Si además entraran
como nodos propios, su territorio quedaría contado dos veces en W (unidades superpuestas) y
Yumbo sería, a la vez, el vecino más cercano del nodo del que forma parte. Por eso los
municipios con `CODIGO_DOMINIO_PADRE` **no son nodos**: se predicen como subáreas de su
dominio, ``x_m'β̂ + û_D``, donde ``û_D = EBLUP_D − x_D'β̂`` es el efecto espacial predicho del
nodo. Después se les aplica el benchmarking de nivel 2 (`shared/benchmarking.benchmark_nivel2`)
con los mismos pesos de PET que el modelo clásico.

El MSE de una subárea es el del sintético, ``x_m'Cov(β̂)x_m + Â`` (Morales et al., p. 441): no usa
información propia del municipio, así que es conservador respecto del del nodo.
"""

import numpy as np
import pandas as pd


def efectos_dominio(modelo) -> np.ndarray:
    """Efecto espacial predicho de cada dominio con encuesta: EBLUP − x'β̂.

    Args:
        modelo: `FayHerriotEspacial` ajustado.

    Returns:
        np.ndarray: Vector (n,) con el efecto de cada dominio, en puntos porcentuales.

    Example:
        >>> efectos_dominio(final)  # doctest: +SKIP
    """
    return np.asarray(modelo.eblup, dtype=float) - np.asarray(
        modelo.mu_hat, dtype=float
    )


def predecir_subareas(
    df_sub: pd.DataFrame,
    covars: list,
    modelo,
    codigos_dominio,
    col_padre: str = "CODIGO_DOMINIO_PADRE",
) -> pd.DataFrame:
    """Predice los municipios de un dominio A.M. como subáreas de su nodo.

    Args:
        df_sub (pd.DataFrame): Municipios con `covars` y `col_padre` (código del dominio).
        covars (list[str]): Covariables del modelo, en el orden de `modelo.beta_hat[1:]`.
        modelo: `FayHerriotEspacial` ajustado.
        codigos_dominio (array-like): Código de cada dominio con encuesta, en el orden de `df`
            con el que se ajustó el modelo.
        col_padre (str): Columna con el dominio que contiene al municipio.

    Returns:
        pd.DataFrame: Mismo índice que `df_sub`, con `PRED_SINT_ESPACIAL` (x'β̂),
            `MSE_ESPACIAL` (x'Cov(β̂)x + Â), `EFECTO_ESPACIAL` (efecto del nodo padre) y
            `PRED_ESPACIAL` (suma de los dos).

    Raises:
        ValueError: Si algún padre no es un dominio con encuesta.

    Example:
        >>> predecir_subareas(cali_yumbo, covars, final, df["CODIGO_DOMINIO"])  # doctest: +SKIP
    """
    efecto_por_codigo = dict(zip(codigos_dominio, efectos_dominio(modelo)))
    faltan = sorted(set(df_sub[col_padre]) - set(efecto_por_codigo))
    if faltan:
        raise ValueError(f"Dominios padre sin nodo en el modelo: {faltan}")
    X = np.column_stack(
        [np.ones(len(df_sub))] + [df_sub[c].to_numpy(dtype=float) for c in covars]
    )
    sintetico = X @ modelo.beta_hat
    mse = np.einsum("ij,jk,ik->i", X, modelo.cov_beta, X) + modelo.A_hat
    efecto = df_sub[col_padre].map(efecto_por_codigo).to_numpy(dtype=float)
    return pd.DataFrame(
        {
            "PRED_SINT_ESPACIAL": sintetico,
            "MSE_ESPACIAL": mse,
            "EFECTO_ESPACIAL": efecto,
            "PRED_ESPACIAL": sintetico + efecto,
        },
        index=df_sub.index,
    )
