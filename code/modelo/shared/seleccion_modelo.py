import pandas as pd

from shared.modelo_area_pequena import ModeloAreaPequena


def _rank_by(modelos: list, key_fn) -> dict:
    """Asigna un rango (1 = mejor) a cada modelo según una métrica donde menor es mejor.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados.
        key_fn (Callable[[ModeloAreaPequena], float]): Métrica a rankear.

    Returns:
        dict[int, int]: índice del modelo (posición en `modelos`) -> rango (1-indexado).
    """
    orden = sorted(range(len(modelos)), key=lambda i: key_fn(modelos[i]))
    return {idx: rango for rango, idx in enumerate(orden, 1)}


def _ranking_compuesto(modelos: list) -> list:
    """Suma de posiciones en AIC y MSE medio para cada modelo.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ya ajustados.

    Returns:
        list[int]: Puntaje de ranking compuesto (menor es mejor), mismo
            orden que `modelos`.

    Raises:
        AttributeError: Si algún modelo no ha sido ajustado (sin `aic` o `mse`).
    """
    rk_aic = _rank_by(modelos, lambda m: m.aic)
    rk_mse = _rank_by(modelos, lambda m: m.mse.mean())
    return [rk_aic[i] + rk_mse[i] for i in range(len(modelos))]


def elegir_ganador(modelos: list, nombres_covars: list) -> ModeloAreaPequena:
    """Elige el modelo con menor ranking compuesto (AIC + MSE medio).

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ya ajustados.
        nombres_covars (list[list[str]]): Lista de covariables por modelo,
            mismo orden que `modelos` (solo se usa para mensajes).

    Returns:
        ModeloAreaPequena: El modelo ganador.

    Raises:
        AttributeError: Si algún modelo no ha sido ajustado.
        ValueError: Si `modelos` está vacío.
    """
    if not modelos:
        raise ValueError("La lista de modelos está vacía.")

    puntajes = _ranking_compuesto(modelos)
    idx_ganador = min(range(len(modelos)), key=lambda i: puntajes[i])
    print(f"Modelo ganador: {' + '.join(nombres_covars[idx_ganador])}")
    return modelos[idx_ganador]


def tabla_diagnosticos(modelos: list, nombres_covars: list) -> pd.DataFrame:
    """Tabla comparativa de diagnósticos por modelo (Tabla 1 de la narrativa).

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados, con
            `resultados` (resultado de `tabla_resultados()`) ya asignado.
        nombres_covars (list[list[str]]): Lista de covariables por modelo,
            mismo orden que `modelos`.

    Returns:
        pd.DataFrame: Una fila por modelo con R², media/SD de residuos,
            p-valor de Shapiro-Wilk, reducción media de CV, shrinkage
            promedio, % de dominios que mejoran el MSE, ratio MSE medio y
            p-valor de Wilcoxon.

    Raises:
        AttributeError: Si algún modelo no tiene `resultados` asignado.
    """
    filas = []
    for i, m in enumerate(modelos, 1):
        validacion = m.validar_mse_directo()
        filas.append({
            "Modelo":          f"M{i}",
            "Covariables":     " + ".join(nombres_covars[i - 1]),
            "R2":              round(m.r2, 4),
            "Media_resid":     round(m.residuals.mean(), 4),
            "SD_resid":        round(m.residuals.std(), 4),
            "SW_pval":         round(m.sw_pval, 4),
            "Delta_CV_pp":     round(m.resultados["MEJORA_CV_PCT"].mean(), 2),
            "Gamma_prom":      round(m.gamma_i.mean(), 4) if m.gamma_i is not None else None,
            "Pct_dom_mejoran": round(validacion["dominios_mejoran"] * 100, 1),
            "Ratio_MSE_medio": round(validacion["mse_ratio"].mean(), 4),
            "Wilcoxon_pval":   round(validacion["wil_pval"], 4),
        })
    return pd.DataFrame(filas)


def tabla_seleccion(modelos: list, nombres_covars: list) -> pd.DataFrame:
    """Tabla de selección de modelo por ranking compuesto (Tabla 2 de la narrativa).

    Usa el mismo criterio de ranking que `elegir_ganador()` (suma de
    posiciones en AIC y MSE medio), por lo que el modelo en la fila
    `Rank == 1` siempre coincide con el resultado de `elegir_ganador()`.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados.
        nombres_covars (list[list[str]]): Lista de covariables por modelo,
            mismo orden que `modelos`.

    Returns:
        pd.DataFrame: Una fila por modelo, ordenada por ranking, con AIC,
            MSE medio y sus diferencias frente al mejor valor de cada
            métrica.

    Raises:
        AttributeError: Si algún modelo no ha sido ajustado.
    """
    best_aic = min(m.aic for m in modelos)
    best_mse = min(m.mse.mean() for m in modelos)

    puntajes = _ranking_compuesto(modelos)
    orden = sorted(range(len(modelos)), key=lambda i: puntajes[i])

    filas = []
    for rank, idx in enumerate(orden, 1):
        m = modelos[idx]
        mse_medio = m.mse.mean()
        filas.append({
            "Rank":        rank,
            "Modelo":      f"M{idx + 1}",
            "Covariables": " + ".join(nombres_covars[idx]),
            "AIC":         round(m.aic, 4),
            "Delta_AIC":   round(m.aic - best_aic, 4),
            "MSE_medio":   round(mse_medio, 6),
            "Delta_MSE":   round(mse_medio - best_mse, 6),
            "Ganador":     "←" if rank == 1 else "",
        })
    return pd.DataFrame(filas)
