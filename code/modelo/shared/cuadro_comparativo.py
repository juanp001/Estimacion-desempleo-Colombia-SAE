"""Cuadro comparativo del objetivo 1: benchmark clásico frente a las especificaciones espaciales.

La comparación es entre el **benchmark seleccionado** del Fay-Herriot clásico (una de las
especificaciones candidatas EC1…ECk) y las especificaciones espaciales (SEBLUP) que resultan de
cruzar los escenarios de W con las estructuras `muestra` y `completa`. Todas usan las mismas
covariables, así que la única diferencia es la estructura de los efectos aleatorios.
"""

import numpy as np
import pandas as pd


def construir_cuadro_comparativo(
    df_comparacion: pd.DataFrame,
    df_validacion: pd.DataFrame,
    clasico,
    covars: list,
    etiqueta_benchmark: str = "Clásico (benchmark)",
) -> pd.DataFrame:
    """Une ajuste (AIC, LRT) y validación dejar-un-dominio-fuera en un solo cuadro.

    La primera fila es el benchmark clásico; después una fila por (escenario de W, estructura).
    El RMSE del clásico sale de `pred_clasico`, que es el mismo en todas las filas de
    `df_validacion`. Para la estructura `muestra` no hay predictor con efecto espacial
    (los objetivos reciben el sintético), así que `RMSE_espacial_con_efecto` queda en NaN.

    Args:
        df_comparacion (pd.DataFrame): Ajuste por escenario y estructura, con `escenario`,
            `estructura`, `A_hat`, `rho_hat`, `AIC`, `Delta_AIC`, `p_LRT`, `p_covariables`, `R2`
            y `espacial_preferido`.
        df_validacion (pd.DataFrame): Métricas de `metricas_validacion` con `escenario`,
            `estructura`, `predictor`, `RMSE`, `RMSE_corregido` y `sesgo_medio`.
        clasico: Modelo `FayHerriotClasico` ajustado (usa `A_hat`, `aic`, `r2`, `p_vals`).
        covars (list[str]): Covariables comunes a todos los modelos.
        etiqueta_benchmark (str): Nombre de la fila del clásico.

    Returns:
        pd.DataFrame: Una fila por modelo con columnas `Modelo`, `Tipo`, `Escenario_W`,
            `Estructura`, `Covariables`, `sigma2_u`, `rho`, `AIC`, `Delta_AIC`, `p_LRT`,
            `R2`, `RMSE_sintetico`, `RMSE_con_efecto`, `RMSE_corregido`, `Sesgo_medio` y
            `Veredicto`.

    Example:
        >>> cuadro = construir_cuadro_comparativo(comp, val, clasico, ["IICA", "VA"])  # doctest: +SKIP
        >>> cuadro.loc[0, "Tipo"]  # doctest: +SKIP
        'CLASICO'
    """
    val = df_validacion.set_index(["escenario", "estructura", "predictor"])
    cualquiera = df_validacion.iloc[0]
    clave_clasico = (cualquiera["escenario"], cualquiera["estructura"], "pred_clasico")
    filas = [
        {
            "Modelo": etiqueta_benchmark,
            "Tipo": "CLASICO",
            "Escenario_W": "—",
            "Estructura": "—",
            "Covariables": " + ".join(covars),
            "sigma2_u": clasico.A_hat,
            "rho": np.nan,
            "AIC": clasico.aic,
            "Delta_AIC": 0.0,
            "p_LRT": np.nan,
            "R2": clasico.r2,
            "RMSE_sintetico": val.loc[clave_clasico, "RMSE"],
            "RMSE_con_efecto": np.nan,
            "RMSE_corregido": val.loc[clave_clasico, "RMSE_corregido"],
            "Sesgo_medio": val.loc[clave_clasico, "sesgo_medio"],
            "Veredicto": "Referencia",
        }
    ]
    for _, fila in df_comparacion.iterrows():
        clave = (fila["escenario"], fila["estructura"])
        sint = val.loc[clave + ("pred_sint_esp",)]
        efecto = (
            val.loc[clave + ("pred_espacial",)]
            if clave + ("pred_espacial",) in val.index
            else None
        )
        # El predictor que se usaría en los objetivos: con efecto si existe, si no el sintético.
        usado = efecto if efecto is not None else sint
        filas.append(
            {
                "Modelo": f"SEBLUP {fila['escenario']} ({fila['estructura']})",
                "Tipo": "ESPACIAL",
                "Escenario_W": fila["escenario"],
                "Estructura": fila["estructura"],
                "Covariables": " + ".join(covars),
                "sigma2_u": fila["A_hat"],
                "rho": fila["rho_hat"],
                "AIC": fila["AIC"],
                "Delta_AIC": fila["Delta_AIC"],
                "p_LRT": fila["p_LRT"],
                "R2": fila["R2"],
                "RMSE_sintetico": sint["RMSE"],
                "RMSE_con_efecto": efecto["RMSE"] if efecto is not None else np.nan,
                "RMSE_corregido": usado["RMSE_corregido"],
                "Sesgo_medio": usado["sesgo_medio"],
                "Veredicto": (
                    "Preferido al clásico"
                    if fila["espacial_preferido"]
                    else "No preferido (p(LRT) ≥ 0.05)"
                ),
            }
        )
    return pd.DataFrame(filas)


def construir_cuadro_coeficientes(
    clasico, modelos_esp: dict, covars: list
) -> pd.DataFrame:
    """Coeficientes del clásico y del espacial lado a lado, por escenario y estructura (R-16).

    Responde cuánto cambia la lectura de cada covariable al agregar la dependencia espacial:
    la misma especificación, con β̂, error estándar y p del clásico y de cada SEBLUP, el cambio
    absoluto y el cambio medido en errores estándar del clásico (Δβ/EE). Los p-valores son
    descriptivos: las covariables y el conjunto salen de una selección sobre los mismos 23
    dominios (advertencia post-selección, G7-B17).

    Args:
        clasico: `FayHerriotClasico` ajustado (usa `beta_hat`, `se_beta`, `p_vals`).
        modelos_esp (dict): ``{(escenario, estructura): FayHerriotEspacial ajustado}``.
        covars (list[str]): Covariables comunes (sin intercepto).

    Returns:
        pd.DataFrame: Una fila por (escenario, estructura, parámetro) con `beta_clasico`,
            `EE_clasico`, `p_clasico`, `beta_espacial`, `EE_espacial`, `p_espacial`,
            `Delta_beta`, `Delta_beta_sobre_EE_clasico` y `rho_hat`.

    Example:
        >>> construir_cuadro_coeficientes(clasico, modelos_esp, covars)  # doctest: +SKIP
    """
    parametros = ["Intercepto"] + list(covars)
    filas = []
    for (escenario, estructura), modelo in modelos_esp.items():
        for j, parametro in enumerate(parametros):
            delta = float(modelo.beta_hat[j] - clasico.beta_hat[j])
            filas.append(
                {
                    "escenario": escenario,
                    "estructura": estructura,
                    "Parametro": parametro,
                    "beta_clasico": float(clasico.beta_hat[j]),
                    "EE_clasico": float(clasico.se_beta[j]),
                    "p_clasico": float(clasico.p_vals[j]),
                    "beta_espacial": float(modelo.beta_hat[j]),
                    "EE_espacial": float(modelo.se_beta[j]),
                    "p_espacial": float(modelo.p_vals[j]),
                    "Delta_beta": delta,
                    "Delta_beta_sobre_EE_clasico": delta / float(clasico.se_beta[j]),
                    "rho_hat": float(modelo.rho_hat),
                }
            )
    return pd.DataFrame(filas)
