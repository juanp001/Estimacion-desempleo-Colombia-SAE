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
    """Suma de posiciones en AIC, BIC, MSE medio y RMSE-LOOCV para cada modelo.

    Requiere que cada modelo ya tenga `rmse_loocv` calculado (ver
    `ModeloAreaPequena.loocv()`), porque recalcularlo aquí sería costoso
    (reajusta el modelo n veces) y duplicaría trabajo ya hecho por el
    orquestador.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ya ajustados, con
            `rmse_loocv` asignado.

    Returns:
        list[int]: Puntaje de ranking compuesto (menor es mejor), mismo
            orden que `modelos`.

    Raises:
        AttributeError: Si algún modelo no tiene `rmse_loocv` asignado.
    """
    rk_aic   = _rank_by(modelos, lambda m: m.aic)
    rk_bic   = _rank_by(modelos, lambda m: m.bic)
    rk_mse   = _rank_by(modelos, lambda m: m.mse.mean())
    rk_loocv = _rank_by(modelos, lambda m: m.rmse_loocv)
    return [rk_aic[i] + rk_bic[i] + rk_mse[i] + rk_loocv[i] for i in range(len(modelos))]


def elegir_ganador(modelos: list, nombres_covars: list) -> ModeloAreaPequena:
    """Elige el modelo con menor ranking compuesto (AIC + BIC + MSE medio + RMSE-LOOCV).

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ya ajustados con
            `rmse_loocv` asignado.
        nombres_covars (list[list[str]]): Lista de covariables por modelo,
            mismo orden que `modelos` (solo se usa para mensajes).

    Returns:
        ModeloAreaPequena: El modelo ganador.

    Raises:
        AttributeError: Si algún modelo no tiene `rmse_loocv` asignado.
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
            `rmse_loocv` y `resultados` (resultado de `tabla_resultados()`)
            ya asignados.
        nombres_covars (list[list[str]]): Lista de covariables por modelo,
            mismo orden que `modelos`.

    Returns:
        pd.DataFrame: Una fila por modelo con R², media/SD de residuos,
            p-valor de Shapiro-Wilk, reducción media de CV, shrinkage
            promedio, % de dominios que mejoran el MSE, ratio MSE medio,
            p-valor de Wilcoxon y RMSE-LOOCV.

    Raises:
        AttributeError: Si algún modelo no tiene `rmse_loocv` o
            `resultados` asignados.
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
            "RMSE_LOOCV":      round(m.rmse_loocv, 4),
        })
    return pd.DataFrame(filas)


def tabla_seleccion(modelos: list, nombres_covars: list) -> pd.DataFrame:
    """Tabla de selección de modelo por ranking compuesto (Tabla 2 de la narrativa).

    Usa el mismo criterio de ranking que `elegir_ganador()` (suma de
    posiciones en AIC, BIC, MSE medio y RMSE-LOOCV), por lo que el modelo
    en la fila `Rank == 1` siempre coincide con el resultado de
    `elegir_ganador()`.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados, con
            `rmse_loocv` ya asignado.
        nombres_covars (list[list[str]]): Lista de covariables por modelo,
            mismo orden que `modelos`.

    Returns:
        pd.DataFrame: Una fila por modelo, ordenada por ranking, con AIC,
            BIC, MSE medio, RMSE-LOOCV y sus diferencias frente al mejor
            valor de cada métrica.

    Raises:
        AttributeError: Si algún modelo no tiene `rmse_loocv` asignado.
    """
    best_aic   = min(m.aic for m in modelos)
    best_bic   = min(m.bic for m in modelos)
    best_mse   = min(m.mse.mean() for m in modelos)
    best_loocv = min(m.rmse_loocv for m in modelos)

    puntajes = _ranking_compuesto(modelos)
    orden = sorted(range(len(modelos)), key=lambda i: puntajes[i])

    filas = []
    for rank, idx in enumerate(orden, 1):
        m = modelos[idx]
        mse_medio = m.mse.mean()
        filas.append({
            "Rank":          rank,
            "Modelo":        f"M{idx + 1}",
            "Covariables":   " + ".join(nombres_covars[idx]),
            "AIC":           round(m.aic, 4),
            "Delta_AIC":     round(m.aic - best_aic, 4),
            "BIC":           round(m.bic, 4),
            "Delta_BIC":     round(m.bic - best_bic, 4),
            "MSE_medio":     round(mse_medio, 6),
            "Delta_MSE":     round(mse_medio - best_mse, 6),
            "RMSE_LOOCV":    round(m.rmse_loocv, 4),
            "Delta_RMSE_CV": round(m.rmse_loocv - best_loocv, 4),
            "Ganador":       "←" if rank == 1 else "",
        })
    return pd.DataFrame(filas)
