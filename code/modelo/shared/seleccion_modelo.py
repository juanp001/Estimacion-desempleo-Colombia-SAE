"""Selección entre especificaciones del modelo Fay-Herriot.

1. **Variantes dejar-una-fuera** del conjunto elegido por el análisis exploratorio: responden a
   la pregunta «¿aporta cada covariable?» sin recorrer docenas de especificaciones.
2. **Criterio de selección** basado en Morales et al. (2021, p. 453): cuando el modelo se usa
   para predecir fuera de muestra (aquí, la predicción sintética de municipios sin encuesta) no
   conviene sobreparametrizar y se recomienda que todas las covariables sean significativas
   (p < 0.05). Entre las variantes que lo cumplen se elige por AIC y, entre las equivalentes
   (ΔAIC ≤ 2), la de menos covariables.
3. **Distancia de Cook** como diagnóstico de robustez del modelo elegido (no entra en la
   decisión): con 23 dominios, un solo territorio puede sostener los coeficientes.
4. **Tabla de diagnósticos** por variante (ajuste, residuos, ganancia de precisión y efecto
   suavizador), informativa.

Distancia de Cook en el modelo Fay-Herriot
------------------------------------------
Con la varianza de efectos aleatorios ``Â`` estimada, el modelo es una regresión ponderada
con pesos conocidos ``w_i = 1/(D_i + Â)``. Para esa regresión:

    r_i  = (Y_i − x_i'β̂) / √(D_i + Â)              residuo estandarizado (ya calculado
                                                    por el modelo como `residuals`)
    h_ii = x_i' Cov(β̂) x_i / (D_i + Â)              apalancamiento
    D_i  = r_i² · h_ii / (p · (1 − h_ii)²)          distancia de Cook

que coincide con la definición ``(β̂ − β̂_(i))' X'WX (β̂ − β̂_(i)) / p`` cuando se refita sin
el dominio *i* manteniendo ``Â`` fijo. El umbral convencional es ``4/n``. No es un
diagnóstico del libro de referencia sino de regresión general; `sensibilidad_cook` completa la
lectura reajustando el modelo (con ``Â`` reestimado) sin el dominio más influyente.
"""

import numpy as np
import pandas as pd
from scipy import stats

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


def tabla_diagnosticos(modelos: list, nombres_covars: list) -> pd.DataFrame:
    """Tabla comparativa de diagnósticos por especificación (informativa).

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados, con `resultados` (salida de
            `tabla_resultados()`) ya asignado.
        nombres_covars (list[list[str]]): Covariables por modelo, mismo orden que `modelos`.

    Returns:
        pd.DataFrame: Una fila por modelo con R², media/SD de residuos, p-valor de
            Shapiro-Wilk, reducción media de CV, shrinkage promedio, % de dominios que
            mejoran el MSE, ratio MSE medio, p-valor de Wilcoxon y la correlación entre la
            estimación directa y la corrección del EBLUP (efecto suavizador) con su p-valor.

    Raises:
        AttributeError: Si algún modelo no tiene `resultados` asignado.

    Example:
        >>> tabla_diagnosticos(modelos, nombres_covars)
    """
    filas = []
    for i, m in enumerate(modelos, 1):
        validacion = m.validar_mse_directo()
        corr, corr_pval = stats.pearsonr(m.Y, m.Y - m.eblup)
        filas.append(
            {
                "Modelo": f"M{i}",
                "Covariables": " + ".join(nombres_covars[i - 1]),
                "R2": round(m.r2, 4),
                "Media_resid": round(m.residuals.mean(), 4),
                "SD_resid": round(m.residuals.std(), 4),
                "SW_pval": round(m.sw_pval, 4),
                "Delta_CV_pp": round(m.resultados["MEJORA_CV_PCT"].mean(), 2),
                "Gamma_prom": (
                    round(m.gamma_i.mean(), 4) if m.gamma_i is not None else None
                ),
                "Pct_dom_mejoran": round(validacion["dominios_mejoran"] * 100, 1),
                "Ratio_MSE_medio": round(validacion["mse_ratio"].mean(), 4),
                "Wilcoxon_pval": round(validacion["wil_pval"], 4),
                "Corr_suavizador": round(float(corr), 4),
                "Corr_suavizador_pval": round(float(corr_pval), 4),
            }
        )
    return pd.DataFrame(filas)


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


def todas_significativas(modelo: ModeloAreaPequena, alfa: float = 0.05) -> bool:
    """Indica si todas las covariables del modelo (sin el intercepto) tienen p-valor < alfa.

    Los p-valores son los de la prueba z con la distribución normal asintótica de β̂ REML,
    la misma que usa el libro de referencia (Morales et al., p. 272).

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `p_vals` poblado.
        alfa (float): Nivel de significancia.

    Returns:
        bool: True si todas las covariables son significativas al nivel `alfa`.

    Example:
        >>> todas_significativas(modelo, alfa=0.05)
    """
    return bool(np.all(modelo.p_vals[1:] < alfa))


def _indice_ganador(
    modelos: list, nombres_covars: list, delta_aic: float, alfa: float
) -> tuple:
    """Aplica el criterio de selección y devuelve el índice elegido y su contexto.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados.
        nombres_covars (list[list[str]]): Covariables por modelo, mismo orden que `modelos`.
        delta_aic (float): Diferencia de AIC que define variantes equivalentes.
        alfa (float): Nivel de significancia exigido a todas las covariables.

    Returns:
        tuple: (idx_ganador, candidatas, equivalentes, hay_candidatas). `candidatas` y
            `equivalentes` son listas de índices; `hay_candidatas` es False cuando ninguna
            variante tiene todas sus covariables significativas y se usaron todas.
    """
    candidatas = [i for i, m in enumerate(modelos) if todas_significativas(m, alfa)]
    hay_candidatas = bool(candidatas)
    if not hay_candidatas:
        candidatas = list(range(len(modelos)))
    mejor_aic = min(modelos[i].aic for i in candidatas)
    equivalentes = [i for i in candidatas if modelos[i].aic - mejor_aic <= delta_aic]
    idx_ganador = min(
        equivalentes, key=lambda i: (len(nombres_covars[i]), modelos[i].aic)
    )
    return idx_ganador, candidatas, equivalentes, hay_candidatas


def tabla_seleccion(
    modelos: list, nombres_covars: list, delta_aic: float = 2.0, alfa: float = 0.05
) -> pd.DataFrame:
    """Tabla de selección: significancia de las covariables, AIC y parsimonia.

    Solo las columnas `Todas_signif`, `AIC` y `N_covariables` intervienen en la decisión.
    `MSE_medio` y `Cook_max` se reportan como información (ganancia de precisión y
    robustez), sin rol en la elección.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados.
        nombres_covars (list[list[str]]): Covariables por modelo, mismo orden que `modelos`.
        delta_aic (float): Diferencia de AIC que define variantes equivalentes.
        alfa (float): Nivel de significancia exigido a todas las covariables.

    Returns:
        pd.DataFrame: Una fila por modelo con número de covariables, AIC, diferencia de AIC
            frente a la mejor candidata, p-valor máximo de las covariables, si todas son
            significativas, si es candidata, si es equivalente por AIC, si es la elegida, y
            las columnas informativas MSE_medio y Cook_max. Ordenada con las candidatas
            primero y, dentro de cada grupo, por AIC.

    Example:
        >>> tabla_seleccion(modelos, nombres_covars, delta_aic=2.0, alfa=0.05)
    """
    idx_ganador, candidatas, equivalentes, _ = _indice_ganador(
        modelos, nombres_covars, delta_aic, alfa
    )
    mejor_aic = min(modelos[i].aic for i in candidatas)

    filas = []
    for i, (modelo, covars) in enumerate(zip(modelos, nombres_covars)):
        filas.append(
            {
                "Modelo": f"M{i + 1}",
                "Covariables": " + ".join(covars),
                "N_covariables": len(covars),
                "AIC": round(float(modelo.aic), 4),
                "Delta_AIC": round(float(modelo.aic - mejor_aic), 4),
                "p_max_covariables": round(float(modelo.p_vals[1:].max()), 4),
                "Todas_signif": "sí" if todas_significativas(modelo, alfa) else "no",
                "Candidata": "sí" if i in candidatas else "no",
                "Equivalente_AIC": "sí" if i in equivalentes else "no",
                "Elegida": "sí" if i == idx_ganador else "",
                "MSE_medio": round(float(modelo.mse.mean()), 6),
                "Cook_max": round(float(distancia_cook(modelo).max()), 4),
            }
        )
    tabla = pd.DataFrame(filas)
    tabla["_orden"] = tabla["Candidata"].map({"sí": 0, "no": 1})
    return (
        tabla.sort_values(["_orden", "AIC"])
        .drop(columns="_orden")
        .reset_index(drop=True)
    )


def elegir_ganador(
    modelos: list, nombres_covars: list, delta_aic: float = 2.0, alfa: float = 0.05
) -> ModeloAreaPequena:
    """Elige la especificación por significancia, AIC y parsimonia (Morales et al., p. 453).

    1. Candidatas: variantes con todas sus covariables significativas (p < `alfa`). Si
       ninguna lo cumple, se usan todas y se imprime un aviso.
    2. Equivalentes: candidatas con AIC a lo sumo `delta_aic` por encima de la mejor.
    3. Ganadora: la equivalente con menos covariables; a igualdad, la de menor AIC.

    Args:
        modelos (list[ModeloAreaPequena]): Modelos ajustados.
        nombres_covars (list[list[str]]): Covariables por modelo, mismo orden que `modelos`.
        delta_aic (float): Diferencia de AIC que define variantes equivalentes.
        alfa (float): Nivel de significancia exigido a todas las covariables.

    Returns:
        ModeloAreaPequena: El modelo elegido.

    Raises:
        ValueError: Si `modelos` está vacío.

    Example:
        >>> ganador = elegir_ganador(modelos, nombres_covars, delta_aic=2.0, alfa=0.05)
    """
    if not modelos:
        raise ValueError("La lista de modelos está vacía.")

    idx_ganador, candidatas, equivalentes, hay_candidatas = _indice_ganador(
        modelos, nombres_covars, delta_aic, alfa
    )
    if hay_candidatas:
        print(
            f"Variantes con todas las covariables significativas (p < {alfa}): "
            + ", ".join(f"M{i + 1}" for i in candidatas)
        )
    else:
        print(
            f"⚠ AVISO: ninguna variante tiene todas sus covariables significativas "
            f"(p < {alfa}). Se elige entre todas por AIC y parsimonia, pero el modelo no "
            f"cumple la recomendación del libro para predecir fuera de muestra (p. 453)."
        )
    print(
        f"Equivalentes por AIC (ΔAIC ≤ {delta_aic}): "
        + ", ".join(f"M{i + 1}" for i in equivalentes)
    )
    print(
        f"Modelo ganador: M{idx_ganador + 1} ({' + '.join(nombres_covars[idx_ganador])})"
    )
    return modelos[idx_ganador]


def sensibilidad_cook(
    modelo: ModeloAreaPequena,
    clase_modelo: type,
    municipios: np.ndarray,
    alfa: float = 0.05,
) -> pd.DataFrame:
    """Reajusta el modelo sin el dominio de mayor distancia de Cook y compara los β̂.

    A diferencia de la distancia de Cook (que fija ``Â``), aquí se reestima todo el modelo,
    incluida la varianza de efectos aleatorios, así que el cambio refleja la influencia
    completa del dominio.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado (normalmente el ganador).
        clase_modelo (type): Clase con la que reajustar (p. ej. `FayHerriotClasico`).
        municipios (np.ndarray): Nombre de cada dominio, en el orden de las filas del modelo.
        alfa (float): Nivel de significancia para marcar cambios de significancia.

    Returns:
        pd.DataFrame: Una fila por parámetro (intercepto y covariables) con el dominio
            excluido, β̂ completo, β̂ sin el dominio, cambio relativo en %, si cambia el
            signo y si cruza el umbral `alfa` en cualquier sentido (`Cambio_signif`:
            "pierde", "gana" o "no"). Incluye una fila `A_hat`.

    Example:
        >>> sensibilidad_cook(ganador, FayHerriotClasico, df["MUNICIPIO"].values)
    """
    cook = distancia_cook(modelo)
    idx = int(np.argmax(cook))
    df_sin = modelo.df.drop(index=modelo.df.index[idx]).reset_index(drop=True)
    reajuste = clase_modelo(modelo.covars, df_sin, modelo.y_col, modelo.se_col)
    reajuste.ajustar()

    parametros = ["Intercepto"] + list(modelo.covars) + ["A_hat"]
    completo = np.append(modelo.beta_hat, modelo.A_hat)
    sin_dominio = np.append(reajuste.beta_hat, reajuste.A_hat)
    p_completo = np.append(modelo.p_vals, np.nan)
    p_sin = np.append(reajuste.p_vals, np.nan)

    return pd.DataFrame(
        {
            "Dominio_excluido": str(municipios[idx]),
            "Cook": round(float(cook[idx]), 4),
            "Parametro": parametros,
            "Valor_completo": completo.round(4),
            "Valor_sin_dominio": sin_dominio.round(4),
            "Cambio_pct": (100 * (sin_dominio - completo) / np.abs(completo)).round(1),
            "Cambia_signo": np.where(
                np.sign(sin_dominio) != np.sign(completo), "sí", "no"
            ),
            "p_completo": np.round(p_completo, 4),
            "p_sin_dominio": np.round(p_sin, 4),
            # Se marca el cruce del umbral en ambos sentidos: si ninguna covariable es
            # significativa en el modelo completo, «perder» significancia es imposible y
            # solo el caso «gana» revela dependencia de un dominio.
            "Cambio_signif": np.select(
                [
                    (p_completo < alfa) & (p_sin >= alfa),
                    (p_completo >= alfa) & (p_sin < alfa),
                ],
                ["pierde", "gana"],
                default="no",
            ),
        }
    )


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
        >>> fig = figura_cook([ganador], [ganador.covars], df["MUNICIPIO"].values)
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
        ax.set_ylabel("Cook", fontsize=9)
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True, axis="y", linestyle=":", alpha=0.4)

    axes[-1].set_xticks(np.arange(modelos[0].n))
    axes[-1].set_xticklabels(municipios, rotation=60, ha="right", fontsize=7)
    plt.tight_layout()
    return fig


def interpretar_cook(
    modelo: ModeloAreaPequena,
    municipios: np.ndarray,
    sensibilidad: pd.DataFrame,
    alfa: float = 0.05,
) -> str:
    """Lectura textual de la robustez del modelo elegido frente al dominio más influyente.

    El modelo se declara robusto solo si, sin el dominio más influyente, ninguna covariable
    cambia de signo ni cruza el umbral de significancia en ningún sentido. Si ninguna
    covariable era significativa en el modelo completo, la ausencia de pérdidas de
    significancia no demuestra nada, así que no se declara robustez: se informa el cambio
    relativo de cada coeficiente para que la estabilidad se juzgue por su magnitud.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado (normalmente el ganador).
        municipios (np.ndarray): Nombre de cada dominio.
        sensibilidad (pd.DataFrame): Salida de `sensibilidad_cook` para ese modelo.
        alfa (float): Nivel de significancia usado en `sensibilidad_cook`.

    Returns:
        str: Interpretación lista para imprimir junto a la figura y la tabla de sensibilidad.

    Example:
        >>> print(interpretar_cook(ganador, municipios, sensibilidad_cook(ganador, ...)))
    """
    cook = distancia_cook(modelo)
    umbral = 4 / modelo.n
    influyentes = municipios[cook > umbral]
    covars = sensibilidad[sensibilidad["Parametro"].isin(modelo.covars)]
    cambios_signo = covars.loc[covars["Cambia_signo"] == "sí", "Parametro"].tolist()
    perdidas = covars.loc[covars["Cambio_signif"] == "pierde", "Parametro"].tolist()
    ganancias = covars.loc[covars["Cambio_signif"] == "gana", "Parametro"].tolist()
    ninguna_signif = bool((covars["p_completo"] >= alfa).all())
    dominio = sensibilidad["Dominio_excluido"].iloc[0]

    lineas = [
        "INTERPRETACIÓN (robustez del modelo elegido):",
        f"  Dominios por encima del umbral 4/n = {umbral:.3f}: "
        + (", ".join(map(str, influyentes)) if len(influyentes) else "ninguno")
        + ".",
        f"  Dominio más influyente: {dominio} (Cook = {cook.max():.3f}). Cambio relativo "
        "de cada coeficiente al reajustar sin él: "
        + ", ".join(
            f"{fila.Parametro} {fila.Cambio_pct:+.1f} %" for fila in covars.itertuples()
        )
        + ".",
    ]

    hallazgos = []
    if cambios_signo:
        hallazgos.append(f"cambia el signo de {', '.join(cambios_signo)}")
    if perdidas:
        hallazgos.append(f"dejan de ser significativas {', '.join(perdidas)}")
    if ganancias:
        hallazgos.append(f"pasan a ser significativas {', '.join(ganancias)}")

    if hallazgos:
        lineas.append(
            "  ✗ Sin ese dominio "
            + "; ".join(hallazgos)
            + ": la significancia de las covariables depende de un solo territorio y "
            "debe reportarse como limitación."
        )
    elif ninguna_signif:
        lineas.append(
            f"  ⚠ Ninguna covariable es significativa (p < {alfa}) en el modelo completo, "
            "así que no puede perder significancia: esta prueba no permite afirmar "
            "robustez. La estabilidad se juzga por la magnitud de los cambios anteriores."
        )
    else:
        lineas.append(
            "  ✓ Sin ese dominio ninguna covariable cambia de signo ni cruza el umbral de "
            "significancia: las conclusiones no dependen de un solo territorio."
        )
    return "\n".join(lineas)
