"""Selección entre especificaciones del modelo Fay-Herriot — versión revisada.

Complementa a `shared/seleccion_modelo.py`, que no se modifica, con tres cosas:

1. **Distancia de Cook** de cada dominio en el ajuste por mínimos cuadrados generalizados
   del modelo, como diagnóstico de influencia. Con 23 dominios un solo territorio puede
   determinar los coeficientes; el criterio de selección debe penalizar las
   especificaciones que dependen de uno.
2. **Ranking compuesto ampliado**: suma de posiciones en AIC, error cuadrático medio del
   EBLUP y distancia de Cook máxima. El original sumaba solo las dos primeras.
3. **Variantes dejar-una-fuera** del conjunto elegido por el análisis exploratorio, que
   sustituyen a la lista fija de combinaciones y a la búsqueda por AIC: responden a la
   pregunta «¿aporta cada covariable?» sin recorrer docenas de especificaciones.

Distancia de Cook en el modelo Fay-Herriot
------------------------------------------
Con la varianza de efectos aleatorios ``Â`` estimada, el modelo es una regresión ponderada
con pesos conocidos ``w_i = 1/(D_i + Â)``. Para esa regresión:

    r_i  = (Y_i − x_i'β̂) / √(D_i + Â)              residuo estandarizado (ya calculado
                                                    por el modelo como `residuals`)
    h_ii = x_i' Cov(β̂) x_i / (D_i + Â)              apalancamiento
    D_i  = r_i² · h_ii / (p · (1 − h_ii)²)          distancia de Cook

que coincide con la definición ``(β̂ − β̂_(i))' X'WX (β̂ − β̂_(i)) / p`` cuando se refita sin
el dominio *i* manteniendo ``Â`` fijo. El umbral convencional es ``4/n``.
"""

import numpy as np
import pandas as pd

from shared.modelo_area_pequena import ModeloAreaPequena


def variantes_dejar_una_fuera(covars: list) -> list:
    """Genera el conjunto completo y sus variantes quitando una covariable cada vez.

    Args:
        covars (list[str]): Covariables del conjunto elegido por el análisis exploratorio.

    Returns:
        list[list[str]]: El conjunto completo en primer lugar y, si tiene al menos dos
            covariables, una variante por cada covariable excluida, en el mismo orden.

    Raises:
        ValueError: Si `covars` está vacío.

    Example:
        >>> variantes_dejar_una_fuera(["A", "B", "C"])
        [['A', 'B', 'C'], ['B', 'C'], ['A', 'C'], ['A', 'B']]
    """
    if not covars:
        raise ValueError("El conjunto de covariables está vacío.")
    variantes = [list(covars)]
    if len(covars) >= 2:
        variantes += [[c for c in covars if c != excluida] for excluida in covars]
    return variantes


def distancia_cook(modelo: ModeloAreaPequena) -> np.ndarray:
    """Distancia de Cook de cada dominio en el ajuste GLS del modelo Fay-Herriot clásico.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `X`, `Di`, `A_hat`, `cov_beta`
            y `residuals` poblados.

    Returns:
        np.ndarray: Distancia de Cook por dominio, shape (n,).

    Raises:
        RuntimeError: Si el modelo no ha sido ajustado.

    Example:
        >>> cook = distancia_cook(modelo)
        >>> (cook > 4 / modelo.n).sum()
    """
    if not hasattr(modelo, "cov_beta"):
        raise RuntimeError("Llama a ajustar() antes de calcular la distancia de Cook.")

    varianza = modelo.Di + modelo.A_hat
    apalancamiento = (
        np.einsum("ij,jk,ik->i", modelo.X, modelo.cov_beta, modelo.X) / varianza
    )
    return modelo.residuals**2 * apalancamiento / (modelo.p * (1 - apalancamiento) ** 2)


def tabla_cook(
    modelos: list, nombres_covars: list, municipios: np.ndarray
) -> pd.DataFrame:
    """Resumen de influencia por especificación.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados.
        nombres_covars (list[list[str]]): Covariables por modelo, mismo orden que `modelos`.
        municipios (np.ndarray): Nombre de cada dominio, en el orden de las filas del modelo.

    Returns:
        pd.DataFrame: Una fila por modelo con la distancia de Cook máxima, el dominio que
            la produce, el umbral 4/n, el número de dominios que lo superan y su lista.

    Example:
        >>> tabla_cook(modelos, nombres_covars, df["MUNICIPIO"].values)
    """
    filas = []
    for i, (modelo, covars) in enumerate(zip(modelos, nombres_covars), 1):
        cook = distancia_cook(modelo)
        umbral = 4 / modelo.n
        influyentes = np.where(cook > umbral)[0]
        filas.append(
            {
                "Modelo": f"M{i}",
                "Covariables": " + ".join(covars),
                "Cook_max": round(float(cook.max()), 4),
                "Dominio_Cook_max": str(municipios[int(np.argmax(cook))]),
                "Umbral": round(umbral, 4),
                "N_influyentes": int(len(influyentes)),
                "Dominios_influyentes": (
                    "; ".join(f"{municipios[j]} ({cook[j]:.3f})" for j in influyentes)
                    if len(influyentes)
                    else "—"
                ),
            }
        )
    return pd.DataFrame(filas)


def _rank_by(modelos: list, key_fn) -> dict:
    """Asigna un rango (1 = mejor) a cada modelo según una métrica donde menor es mejor.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados.
        key_fn (Callable[[ModeloAreaPequena], float]): Métrica a rankear.

    Returns:
        dict[int, int]: índice del modelo (posición en `modelos`) → rango (1-indexado).
    """
    orden = sorted(range(len(modelos)), key=lambda i: key_fn(modelos[i]))
    return {idx: rango for rango, idx in enumerate(orden, 1)}


def _ranking_compuesto(modelos: list) -> list:
    """Suma de posiciones en AIC, MSE medio y distancia de Cook máxima.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados.

    Returns:
        list[int]: Puntaje de ranking compuesto (menor es mejor), mismo orden que `modelos`.
    """
    rk_aic = _rank_by(modelos, lambda m: m.aic)
    rk_mse = _rank_by(modelos, lambda m: m.mse.mean())
    rk_cook = _rank_by(modelos, lambda m: distancia_cook(m).max())
    return [rk_aic[i] + rk_mse[i] + rk_cook[i] for i in range(len(modelos))]


def tabla_seleccion_rev(modelos: list, nombres_covars: list) -> pd.DataFrame:
    """Tabla de selección de modelo por ranking compuesto AIC + MSE medio + Cook máxima.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados.
        nombres_covars (list[list[str]]): Covariables por modelo, mismo orden que `modelos`.

    Returns:
        pd.DataFrame: Una fila por modelo, ordenada por ranking, con AIC, MSE medio, Cook
            máxima, sus diferencias frente al mejor valor de cada métrica, las posiciones
            parciales y el puntaje compuesto. `Rank == 1` es el primer puesto del ranking,
            que no coincide con la variante elegida cuando interviene el desempate por
            parsimonia de `elegir_ganador_rev()`.

    Example:
        >>> tabla_seleccion_rev(modelos, nombres_covars)
    """
    aics = [m.aic for m in modelos]
    mses = [m.mse.mean() for m in modelos]
    cooks = [distancia_cook(m).max() for m in modelos]
    rk_aic = _rank_by(modelos, lambda m: m.aic)
    rk_mse = _rank_by(modelos, lambda m: m.mse.mean())
    rk_cook = _rank_by(modelos, lambda m: distancia_cook(m).max())
    puntajes = _ranking_compuesto(modelos)
    orden = sorted(range(len(modelos)), key=lambda i: (puntajes[i], aics[i]))

    filas = []
    for rank, idx in enumerate(orden, 1):
        filas.append(
            {
                "Rank": rank,
                "Modelo": f"M{idx + 1}",
                "Covariables": " + ".join(nombres_covars[idx]),
                "N_covariables": len(nombres_covars[idx]),
                "AIC": round(aics[idx], 4),
                "Delta_AIC": round(aics[idx] - min(aics), 4),
                "MSE_medio": round(mses[idx], 6),
                "Delta_MSE": round(mses[idx] - min(mses), 6),
                "Cook_max": round(cooks[idx], 4),
                "Delta_Cook": round(cooks[idx] - min(cooks), 4),
                "Pos_AIC": rk_aic[idx],
                "Pos_MSE": rk_mse[idx],
                "Pos_Cook": rk_cook[idx],
                "Puntaje": puntajes[idx],
            }
        )
    return pd.DataFrame(filas)


def elegir_ganador_rev(
    modelos: list, nombres_covars: list, delta_aic: float = 2.0
) -> ModeloAreaPequena:
    """Elige la especificación ganadora por ranking compuesto con desempate por parsimonia.

    El ranking suma las posiciones en AIC, MSE medio y Cook máxima. Entre las variantes
    cuya diferencia de AIC frente a la mejor es menor o igual que `delta_aic` (equivalentes
    según la tabla de criterios de decisión del marco teórico) se elige la de menos
    covariables y, a igualdad, la mejor posicionada en el ranking.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados.
        nombres_covars (list[list[str]]): Covariables por modelo, mismo orden que `modelos`.
        delta_aic (float): Diferencia de AIC que define variantes equivalentes.

    Returns:
        ModeloAreaPequena: El modelo elegido.

    Raises:
        ValueError: Si `modelos` está vacío.

    Example:
        >>> ganador = elegir_ganador_rev(modelos, nombres_covars)
    """
    if not modelos:
        raise ValueError("La lista de modelos está vacía.")

    puntajes = _ranking_compuesto(modelos)
    posicion = {
        i: rango
        for rango, i in enumerate(
            sorted(range(len(modelos)), key=lambda i: (puntajes[i], modelos[i].aic)), 1
        )
    }
    idx_ranking = min(range(len(modelos)), key=lambda i: posicion[i])

    mejor_aic = min(m.aic for m in modelos)
    equivalentes = [i for i, m in enumerate(modelos) if m.aic - mejor_aic <= delta_aic]
    idx_ganador = min(equivalentes, key=lambda i: (len(nombres_covars[i]), posicion[i]))

    print(
        f"Primer puesto del ranking compuesto: M{idx_ranking + 1} ({' + '.join(nombres_covars[idx_ranking])})"
    )
    if idx_ganador != idx_ranking:
        print(
            f"Variantes equivalentes (diferencia de AIC <= {delta_aic}): {len(equivalentes)}"
        )
        print(
            f"  elegida por parsimonia: M{idx_ganador + 1} ({' + '.join(nombres_covars[idx_ganador])}, "
            f"{len(nombres_covars[idx_ganador])} covariables)"
        )
    print(
        f"Modelo ganador: M{idx_ganador + 1} ({' + '.join(nombres_covars[idx_ganador])})"
    )
    return modelos[idx_ganador]


def figura_cook(modelos: list, nombres_covars: list, municipios: np.ndarray):
    """Distancia de Cook por dominio, un panel por especificación.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados.
        nombres_covars (list[list[str]]): Covariables por modelo, mismo orden que `modelos`.
        municipios (np.ndarray): Nombre de cada dominio.

    Returns:
        matplotlib.figure.Figure: Figura con un panel de barras por modelo y la línea del
            umbral 4/n; las barras que lo superan se pintan en rojo.

    Example:
        >>> fig = figura_cook(modelos, nombres_covars, df["MUNICIPIO"].values)
    """
    import matplotlib.pyplot as plt

    n_modelos = len(modelos)
    fig, axes = plt.subplots(
        n_modelos, 1, figsize=(10, 2.6 * n_modelos + 1), sharex=True
    )
    axes = np.atleast_1d(axes)

    for ax, modelo, covars in zip(axes, modelos, nombres_covars):
        cook = distancia_cook(modelo)
        umbral = 4 / modelo.n
        colores = ["firebrick" if d > umbral else "steelblue" for d in cook]
        ax.bar(np.arange(modelo.n), cook, color=colores, edgecolor="white")
        ax.axhline(
            umbral,
            color="dimgray",
            linestyle="--",
            linewidth=1.2,
            label=f"4/n = {umbral:.3f}",
        )
        ax.set_title(" + ".join(covars), fontsize=9, loc="left")
        ax.set_ylabel("Cook", fontsize=9)
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True, axis="y", linestyle=":", alpha=0.4)

    axes[-1].set_xticks(np.arange(modelos[0].n))
    axes[-1].set_xticklabels(municipios, rotation=60, ha="right", fontsize=7)
    plt.tight_layout()
    return fig


def interpretar_cook(
    modelos: list, nombres_covars: list, municipios: np.ndarray
) -> str:
    """Lectura textual de la figura de distancia de Cook por especificación.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados.
        nombres_covars (list[list[str]]): Covariables por modelo.
        municipios (np.ndarray): Nombre de cada dominio.

    Returns:
        str: Interpretación lista para imprimir junto a la figura.

    Example:
        >>> print(interpretar_cook(modelos, nombres_covars, municipios))
    """
    tabla = tabla_cook(modelos, nombres_covars, municipios)
    recurrentes = pd.Series(
        [
            d.split(" (")[0]
            for cadena in tabla["Dominios_influyentes"]
            for d in cadena.split("; ")
            if d != "—"
        ]
    ).value_counts()
    mejor = tabla.loc[tabla["Cook_max"].idxmin()]
    peor = tabla.loc[tabla["Cook_max"].idxmax()]
    lineas = [
        "INTERPRETACIÓN DE LA FIGURA:",
        f"  Especificación con menor dependencia de un dominio: {mejor['Modelo']} "
        f"(Cook máxima {mejor['Cook_max']:.3f} en {mejor['Dominio_Cook_max']}).",
        f"  Especificación con mayor dependencia: {peor['Modelo']} "
        f"(Cook máxima {peor['Cook_max']:.3f} en {peor['Dominio_Cook_max']}).",
        "  Dominios que superan el umbral en más especificaciones: "
        + (
            ", ".join(
                f"{k} ({v} de {len(modelos)})" for k, v in recurrentes.head(3).items()
            )
            if len(recurrentes)
            else "ninguno"
        )
        + ".",
        "  Lectura: una covariable cuya inclusión eleva la Cook máxima está apoyando el ajuste en un solo "
        "territorio; el ranking compuesto penaliza esa especificación aunque su AIC sea algo menor.",
    ]
    return "\n".join(lineas)
