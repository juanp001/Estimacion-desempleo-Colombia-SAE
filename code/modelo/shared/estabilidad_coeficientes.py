"""Estabilidad de los coeficientes del benchmark seleccionado (análisis de sensibilidad).

Con n = 23 dominios, los mismos datos filtran covariables, seleccionan la especificación,
la comparan y luego calculan los p-valores de β̂. Por eso esos p-valores son descriptivos
y condicionales a la selección: **no son una demostración fuerte** de que las asociaciones
existan. Este módulo mide cuánto se mueven los coeficientes del benchmark (especificación
fija) al cambiar los dominios:

1. **Dejar un dominio fuera**: se reajusta el modelo completo (incluida Â) 23 veces.
2. **Bootstrap de dominios**: se remuestrean los dominios con reemplazo (cada uno con su
   estimación directa y su D_i) y se reajusta la misma especificación.

Alcance: ni el libro de referencia (Morales et al., 2021, §16.8.2, pp. 453-454) ni los
artículos espaciales consultados tratan la inferencia posterior a la selección ni la
estabilidad de β̂ con pocas áreas; esto es un análisis de sensibilidad propio. El bootstrap
mantiene la especificación **fija**: no repite el filtro ni la selección, así que subestima
la incertidumbre de haber escogido las covariables con estos mismos datos.
"""

import numpy as np
import pandas as pd

ADVERTENCIA_POST_SELECCION = (
    "Los p-valores de los coeficientes son descriptivos: los mismos dominios se usaron para "
    "filtrar, seleccionar, comparar especificaciones y estimar β̂, así que la significancia "
    "no es una demostración fuerte. Los coeficientes del benchmark se reportan como "
    "asociaciones preliminares, condicionales a la selección."
)


def _parametros(modelo) -> list:
    """Nombres de los parámetros de regresión: intercepto y covariables.

    Args:
        modelo (ModeloAreaPequena): Modelo con `covars`.

    Returns:
        list[str]: `["Intercepto", *covars]`.
    """
    return ["Intercepto"] + list(modelo.covars)


def dejar_uno_fuera_coeficientes(
    modelo, clase_modelo: type, nombres_dominio: np.ndarray, alfa: float = 0.05
) -> pd.DataFrame:
    """Reajusta el modelo quitando un dominio cada vez (con Â reestimada).

    Args:
        modelo (ModeloAreaPequena): Benchmark ya ajustado.
        clase_modelo (type): Clase con la que reajustar (`FayHerriotClasico`).
        nombres_dominio (np.ndarray): Nombre de cada dominio, en el orden de las filas.
        alfa (float): Nivel de significancia para marcar la pérdida de significancia.

    Returns:
        pd.DataFrame: Una fila por (dominio excluido, parámetro) con `Dominio_excluido`,
            `Parametro`, `Beta_completo`, `Beta_sin_dominio`, `Cambio_pct`,
            `Cambia_signo`, `p_completo`, `p_sin_dominio` y `Cruza_alfa` (True si el
            p-valor cambia de lado del umbral `alfa`). Los dominios cuyo reajuste falla
            se omiten.

    Example:
        >>> dejar_uno_fuera_coeficientes(ganador, FayHerriotClasico, nombres)
    """
    parametros = _parametros(modelo)
    filas = []
    for i in range(modelo.n):
        df_sin = modelo.df.drop(index=modelo.df.index[i]).reset_index(drop=True)
        try:
            ajuste = clase_modelo(modelo.covars, df_sin, modelo.y_col, modelo.se_col)
            ajuste.ajustar()
        except Exception:
            continue
        for j, parametro in enumerate(parametros):
            completo, sin = float(modelo.beta_hat[j]), float(ajuste.beta_hat[j])
            filas.append(
                {
                    "Dominio_excluido": str(nombres_dominio[i]),
                    "Parametro": parametro,
                    "Beta_completo": completo,
                    "Beta_sin_dominio": sin,
                    "Cambio_pct": 100 * (sin - completo) / abs(completo),
                    "Cambia_signo": bool(np.sign(sin) != np.sign(completo)),
                    "p_completo": float(modelo.p_vals[j]),
                    "p_sin_dominio": float(ajuste.p_vals[j]),
                    "Cruza_alfa": bool(
                        (modelo.p_vals[j] < alfa) != (ajuste.p_vals[j] < alfa)
                    ),
                }
            )
    return pd.DataFrame(filas)


def resumen_dejar_uno_fuera(detalle: pd.DataFrame, n_dominios: int) -> pd.DataFrame:
    """Resume el dejar-uno-fuera por parámetro.

    Args:
        detalle (pd.DataFrame): Salida de `dejar_uno_fuera_coeficientes`.
        n_dominios (int): Número de dominios del modelo completo (denominador de los conteos).

    Returns:
        pd.DataFrame: Una fila por parámetro con `Beta_completo`, `Beta_min`, `Beta_max`,
            `Cambio_pct_max_abs`, `N_cambia_signo`, `N_cruza_alfa`, `p_max` y `N_reajustes`.

    Example:
        >>> resumen_dejar_uno_fuera(detalle, 23)
    """
    filas = []
    for parametro, g in detalle.groupby("Parametro", sort=False):
        filas.append(
            {
                "Parametro": parametro,
                "Beta_completo": g["Beta_completo"].iloc[0],
                "Beta_min": g["Beta_sin_dominio"].min(),
                "Beta_max": g["Beta_sin_dominio"].max(),
                "Cambio_pct_max_abs": g["Cambio_pct"].abs().max(),
                "N_cambia_signo": int(g["Cambia_signo"].sum()),
                "N_cruza_alfa": int(g["Cruza_alfa"].sum()),
                "p_max": g["p_sin_dominio"].max(),
                "N_reajustes": len(g),
            }
        )
    resumen = pd.DataFrame(filas)
    resumen["N_dominios"] = n_dominios
    return resumen


def bootstrap_dominios(
    modelo, clase_modelo: type, replicas: int = 1000, semilla: int = 42
) -> pd.DataFrame:
    """Bootstrap no paramétrico de dominios con la especificación fija.

    En cada réplica se remuestrean con reemplazo los n dominios (con su estimación directa,
    su error estándar y sus covariables) y se reajusta el modelo. Las réplicas cuyo ajuste
    falla se descartan.

    Args:
        modelo (ModeloAreaPequena): Benchmark ya ajustado.
        clase_modelo (type): Clase con la que reajustar.
        replicas (int): Número de réplicas.
        semilla (int): Semilla de `np.random.default_rng`.

    Returns:
        pd.DataFrame: Una fila por réplica válida con `beta_<parámetro>`, `p_<parámetro>`
            y `A_hat`.

    Example:
        >>> bootstrap_dominios(ganador, FayHerriotClasico, replicas=1000, semilla=42)
    """
    rng = np.random.default_rng(semilla)
    parametros = _parametros(modelo)
    filas = []
    for _ in range(replicas):
        idx = rng.integers(0, modelo.n, modelo.n)
        df_b = modelo.df.iloc[idx].reset_index(drop=True)
        try:
            ajuste = clase_modelo(modelo.covars, df_b, modelo.y_col, modelo.se_col)
            ajuste.ajustar()
        except Exception:
            continue
        fila = {f"beta_{p}": float(b) for p, b in zip(parametros, ajuste.beta_hat)}
        fila.update({f"p_{p}": float(v) for p, v in zip(parametros, ajuste.p_vals)})
        fila["A_hat"] = float(ajuste.A_hat)
        filas.append(fila)
    return pd.DataFrame(filas)


def resumen_bootstrap(
    modelo, replicas_df: pd.DataFrame, alfa: float = 0.05, nivel: float = 0.95
) -> pd.DataFrame:
    """Resume el bootstrap de dominios por parámetro.

    Args:
        modelo (ModeloAreaPequena): Benchmark ajustado (aporta β̂ y su signo).
        replicas_df (pd.DataFrame): Salida de `bootstrap_dominios`.
        alfa (float): Umbral de significancia para `Prop_p_menor_alfa`.
        nivel (float): Nivel del intervalo percentil.

    Returns:
        pd.DataFrame: Una fila por parámetro con `Beta`, `EE_bootstrap`, `IC_inf`, `IC_sup`
            (percentiles), `Prop_mismo_signo` (réplicas con el signo de β̂),
            `Prop_p_menor_alfa`, `N_replicas` y `IC_incluye_cero`.

    Example:
        >>> resumen_bootstrap(ganador, replicas_df)
    """
    inferior, superior = 100 * (1 - nivel) / 2, 100 * (1 + nivel) / 2
    filas = []
    for j, parametro in enumerate(_parametros(modelo)):
        beta = replicas_df[f"beta_{parametro}"]
        lim_inf, lim_sup = np.percentile(beta, [inferior, superior])
        filas.append(
            {
                "Parametro": parametro,
                "Beta": float(modelo.beta_hat[j]),
                "EE_bootstrap": float(beta.std(ddof=1)),
                "IC_inf": float(lim_inf),
                "IC_sup": float(lim_sup),
                "IC_incluye_cero": bool(lim_inf <= 0 <= lim_sup),
                "Prop_mismo_signo": float(
                    np.mean(np.sign(beta) == np.sign(modelo.beta_hat[j]))
                ),
                "Prop_p_menor_alfa": float(
                    np.mean(replicas_df[f"p_{parametro}"] < alfa)
                ),
                "N_replicas": len(beta),
            }
        )
    return pd.DataFrame(filas)


def tabla_estabilidad(
    resumen_loo: pd.DataFrame, resumen_boot: pd.DataFrame
) -> pd.DataFrame:
    """Une el resumen de dejar-uno-fuera y el del bootstrap en una sola tabla.

    Args:
        resumen_loo (pd.DataFrame): Salida de `resumen_dejar_uno_fuera`.
        resumen_boot (pd.DataFrame): Salida de `resumen_bootstrap`.

    Returns:
        pd.DataFrame: Una fila por parámetro con las columnas de ambos análisis
            (las de bootstrap con sufijo `_boot` donde se repiten).

    Example:
        >>> tabla_estabilidad(resumen_loo, resumen_boot)
    """
    return resumen_loo.drop(columns="Beta_completo").merge(
        resumen_boot, on="Parametro", suffixes=("", "_boot")
    )


def interpretar_estabilidad(tabla: pd.DataFrame) -> str:
    """Redacta la lectura de la estabilidad calculada desde la tabla.

    Args:
        tabla (pd.DataFrame): Salida de `tabla_estabilidad`.

    Returns:
        str: Texto con una línea por covariable y la advertencia de selección.

    Example:
        >>> print(interpretar_estabilidad(tabla))
    """
    lineas = []
    for _, f in tabla[tabla["Parametro"] != "Intercepto"].iterrows():
        lineas.append(
            f"- {f['Parametro']}: β̂ = {f['Beta']:.3f}; dejar-uno-fuera entre "
            f"{f['Beta_min']:.3f} y {f['Beta_max']:.3f} (cambio máximo "
            f"{f['Cambio_pct_max_abs']:.0f} %, signo cambia en {f['N_cambia_signo']} de "
            f"{f['N_reajustes']}, cruza el umbral de significancia en "
            f"{f['N_cruza_alfa']}); bootstrap de dominios: IC "
            f"[{f['IC_inf']:.3f}, {f['IC_sup']:.3f}]"
            f"{' (incluye 0)' if f['IC_incluye_cero'] else ''}, mismo signo en "
            f"{100 * f['Prop_mismo_signo']:.0f} % y p < alfa en "
            f"{100 * f['Prop_p_menor_alfa']:.0f} % de las réplicas."
        )
    return "\n".join(lineas) + "\n\n" + ADVERTENCIA_POST_SELECCION
