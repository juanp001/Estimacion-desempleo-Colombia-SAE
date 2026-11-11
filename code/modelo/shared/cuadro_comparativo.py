"""Cuadro comparativo del objetivo 1: benchmark clásico frente a las especificaciones espaciales.

La comparación es entre el **benchmark seleccionado** del Fay-Herriot clásico (una de las
especificaciones candidatas EC1…ECk) y las especificaciones espaciales (SEBLUP) que resultan de
cruzar los escenarios de W con las estructuras `muestra` y `completa`. Todas usan las mismas
covariables, así que la única diferencia es la estructura de los efectos aleatorios.
"""

import numpy as np
import pandas as pd
from scipy import stats

from shared.consolidacion import clasificar_confiabilidad
from shared.matriz_proximidad import (
    distancias_haversine,
    estandarizar_filas,
    moran_i,
    proximidad_knn,
)


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


# ── Comparación de las estimaciones (D-07) ──────────────────────────────────────────────────
# Antes estos cálculos vivían fuera del pipeline (cálculo propio del documento); ahora salen del
# notebook espacial y se persisten en tesis.modelo.fhe_seblup_dominios,
# fhe_diferencias_estimaciones y fhe_moran_estimaciones.


def tabla_seblup_dominios(dominios: pd.DataFrame, clasico, espacial) -> pd.DataFrame:
    """EBLUP del clásico y SEBLUP del espacial en los dominios con encuesta, lado a lado.

    Para cada dominio reporta la estimación directa y su varianza ψ_d, el EBLUP, su MSE de
    Prasad-Rao, su CV y el factor de contracción γ_d del benchmark clásico, y el SEBLUP, su MSE
    (bootstrap paramétrico, Morales et al., p. 494, si el modelo se ajustó con réplicas), su CV y
    el peso del dato directo γ^S_d = [G V⁻¹]_dd del espacial. Las clases de confiabilidad usan la
    misma regla de CV que la tabla final (`clasificar_confiabilidad`).

    Args:
        dominios (pd.DataFrame): Dominios en el mismo orden con que se ajustaron los modelos, con
            `CODIGO_DOMINIO` y `NOMBRE_DOMINIO`.
        clasico: `FayHerriotClasico` ajustado (usa `Y`, `Di`, `eblup`, `mse`, `cv`, `gamma_i`).
        espacial: `FayHerriotEspacial` ajustado (usa `eblup`, `mse`, `cv`, `gamma_espacial`).

    Returns:
        pd.DataFrame: Una fila por dominio con `CODIGO_DOMINIO`, `NOMBRE_DOMINIO`, `DIRECTA`,
            `PSI`, `EBLUP`, `MSE_EBLUP`, `CV_EBLUP_PCT`, `GAMMA`, `CLASE_EBLUP`, `SEBLUP`,
            `MSE_SEBLUP`, `CV_SEBLUP_PCT`, `GAMMA_S`, `CLASE_SEBLUP` y `DIF_SEBLUP_EBLUP_PP`.

    Raises:
        ValueError: Si el número de dominios no coincide con el de los modelos.

    Casos de uso:
        Celda 9b de `fay_herriot_espacial.py` (tabla `fhe_seblup_dominios`).

    Example:
        >>> class _M:
        ...     pass
        >>> c, e = _M(), _M()
        >>> c.Y, c.Di = np.array([10.0, 12.0]), np.array([0.1, 0.2])
        >>> c.eblup, c.mse = np.array([10.1, 11.9]), np.array([0.09, 0.15])
        >>> c.cv, c.gamma_i = np.array([3.0, 3.3]), np.array([0.98, 0.97])
        >>> e.eblup, e.mse = np.array([10.2, 11.9]), np.array([0.1, 0.16])
        >>> e.cv, e.gamma_espacial = np.array([3.1, 21.0]), np.array([0.97, 0.96])
        >>> dom = pd.DataFrame({"CODIGO_DOMINIO": ["05001", "08001"],
        ...                     "NOMBRE_DOMINIO": ["Medellín A.M.", "Barranquilla A.M."]})
        >>> t = tabla_seblup_dominios(dom, c, e)
        >>> t[["CLASE_EBLUP", "CLASE_SEBLUP"]].values.tolist()
        [['Confiable', 'Confiable'], ['Confiable', 'No confiable']]
        >>> round(float(t["DIF_SEBLUP_EBLUP_PP"].iloc[0]), 2)
        0.1
    """
    n = len(dominios)
    if len(clasico.eblup) != n or len(espacial.eblup) != n:
        raise ValueError(
            f"Los modelos tienen {len(clasico.eblup)} y {len(espacial.eblup)} dominios; "
            f"la tabla tiene {n}."
        )
    tabla = pd.DataFrame(
        {
            "CODIGO_DOMINIO": dominios["CODIGO_DOMINIO"].to_numpy(),
            "NOMBRE_DOMINIO": dominios["NOMBRE_DOMINIO"].to_numpy(),
            "DIRECTA": np.asarray(clasico.Y, dtype=float),
            "PSI": np.asarray(clasico.Di, dtype=float),
            "EBLUP": np.asarray(clasico.eblup, dtype=float),
            "MSE_EBLUP": np.asarray(clasico.mse, dtype=float),
            "CV_EBLUP_PCT": np.asarray(clasico.cv, dtype=float),
            "GAMMA": np.asarray(clasico.gamma_i, dtype=float),
            "SEBLUP": np.asarray(espacial.eblup, dtype=float),
            "MSE_SEBLUP": np.asarray(espacial.mse, dtype=float),
            "CV_SEBLUP_PCT": np.asarray(espacial.cv, dtype=float),
            "GAMMA_S": np.asarray(espacial.gamma_espacial, dtype=float),
        }
    )
    tabla["CLASE_EBLUP"] = tabla["CV_EBLUP_PCT"].apply(clasificar_confiabilidad)
    tabla["CLASE_SEBLUP"] = tabla["CV_SEBLUP_PCT"].apply(clasificar_confiabilidad)
    tabla["DIF_SEBLUP_EBLUP_PP"] = tabla["SEBLUP"] - tabla["EBLUP"]
    orden = [
        "CODIGO_DOMINIO",
        "NOMBRE_DOMINIO",
        "DIRECTA",
        "PSI",
        "EBLUP",
        "MSE_EBLUP",
        "CV_EBLUP_PCT",
        "GAMMA",
        "CLASE_EBLUP",
        "SEBLUP",
        "MSE_SEBLUP",
        "CV_SEBLUP_PCT",
        "GAMMA_S",
        "CLASE_SEBLUP",
        "DIF_SEBLUP_EBLUP_PP",
    ]
    return tabla[orden]


def resumen_diferencias(
    nivel: str,
    clasica,
    espacial,
    cv_clasica,
    cv_espacial,
    umbral_pp: float = 0.5,
) -> dict:
    """Resume la diferencia espacial − clásica entre dos juegos de estimaciones.

    Describe, sin pruebas inferenciales (con 23 dominios las diferencias se reportan, no se
    prueban), cuánto se separan las dos estimaciones en puntos porcentuales, qué tan parecido es
    su orden (Pearson y Spearman) y cuántas unidades cambian de clase de confiabilidad con la
    regla de CV de la tabla final.

    Args:
        nivel (str): Etiqueta del nivel (``"DOMINIO"`` o ``"MUNICIPIO"``).
        clasica (array-like): Estimación del Fay-Herriot clásico (EBLUP o sintético), en %.
        espacial (array-like): Estimación del espacial (SEBLUP o predictor espacial), en %.
        cv_clasica (array-like): CV de la estimación clásica, en %.
        cv_espacial (array-like): CV de la estimación espacial, en %.
        umbral_pp (float): Diferencia absoluta, en puntos porcentuales, que se cuenta aparte.

    Returns:
        dict: `NIVEL`, `N`, `DIF_MEDIA_PP`, `DIF_ABS_MEDIA_PP`, `DIF_ABS_MAX_PP`,
            `N_DIF_ABS_MAYOR_UMBRAL`, `UMBRAL_PP`, `PEARSON`, `SPEARMAN`, `CV_MEDIANO_CLASICO`,
            `CV_MEDIANO_ESPACIAL`, `N_CAMBIA_CLASE` y un conteo `N_<clase clásica>_A_<clase
            espacial>` por cada combinación observada de clases.

    Raises:
        ValueError: Si los cuatro vectores no tienen el mismo largo o hay menos de tres unidades.

    Casos de uso:
        Celda 9b de `fay_herriot_espacial.py` (tabla `fhe_diferencias_estimaciones`).

    Example:
        >>> r = resumen_diferencias("DOMINIO", [10, 12, 14], [10.2, 11.9, 14.6],
        ...                         [3, 6, 21], [3, 4, 19])
        >>> r["N_CAMBIA_CLASE"], round(r["DIF_ABS_MAX_PP"], 2), r["N_DIF_ABS_MAYOR_UMBRAL"]
        (2, 0.6, 1)
        >>> r["N_ACEPTABLE_A_CONFIABLE"]
        1
    """
    a = np.asarray(clasica, dtype=float)
    b = np.asarray(espacial, dtype=float)
    cv_a = np.asarray(cv_clasica, dtype=float)
    cv_b = np.asarray(cv_espacial, dtype=float)
    if not (len(a) == len(b) == len(cv_a) == len(cv_b)):
        raise ValueError(
            "Las estimaciones y los CV deben tener el mismo número de unidades."
        )
    if len(a) < 3:
        raise ValueError(
            "Se necesitan al menos tres unidades para resumir las diferencias."
        )
    d = b - a
    clase_a = np.array([clasificar_confiabilidad(v) for v in cv_a])
    clase_b = np.array([clasificar_confiabilidad(v) for v in cv_b])
    resumen = {
        "NIVEL": nivel,
        "N": int(len(a)),
        "DIF_MEDIA_PP": float(d.mean()),
        "DIF_ABS_MEDIA_PP": float(np.abs(d).mean()),
        "DIF_ABS_MAX_PP": float(np.abs(d).max()),
        "N_DIF_ABS_MAYOR_UMBRAL": int((np.abs(d) > umbral_pp).sum()),
        "UMBRAL_PP": float(umbral_pp),
        "PEARSON": float(stats.pearsonr(a, b)[0]),
        "SPEARMAN": float(stats.spearmanr(a, b)[0]),
        "CV_MEDIANO_CLASICO": float(np.median(cv_a)),
        "CV_MEDIANO_ESPACIAL": float(np.median(cv_b)),
        "N_CAMBIA_CLASE": int((clase_a != clase_b).sum()),
    }
    pares = pd.Series([f"{x}|{y}" for x, y in zip(clase_a, clase_b)])
    for par, conteo in pares.value_counts().sort_index().items():
        ca, cb = par.split("|")
        clave = f"N_{ca}_A_{cb}".upper().replace(" ", "_")
        resumen[clave] = int(conteo)
    return resumen


def tabla_diferencias(resumenes: list) -> pd.DataFrame:
    """Une los resúmenes de `resumen_diferencias` en una tabla con columnas homogéneas.

    Las columnas de conteo de clases que no aparecen en un nivel quedan en 0, para que la tabla
    tenga el mismo esquema en todas sus filas.

    Args:
        resumenes (list[dict]): Salidas de `resumen_diferencias`, una por nivel.

    Returns:
        pd.DataFrame: Una fila por nivel.

    Casos de uso:
        Celda 9b de `fay_herriot_espacial.py` (tabla `fhe_diferencias_estimaciones`).

    Example:
        >>> a = resumen_diferencias("DOMINIO", [1, 2, 3], [1, 2, 3.1], [3, 3, 3], [3, 3, 3])
        >>> b = resumen_diferencias("MUNICIPIO", [1, 2, 3], [1, 2, 3], [9, 9, 30], [9, 25, 30])
        >>> tabla_diferencias([a, b])["N_CONFIABLE_A_CONFIABLE"].tolist()
        [3, 0]
    """
    tabla = pd.DataFrame(resumenes)
    conteos = [c for c in tabla.columns if c.startswith("N_") and "_A_" in c]
    tabla[conteos] = tabla[conteos].fillna(0).astype(int)
    return tabla


def moran_estimaciones(
    latitud,
    longitud,
    variables: dict,
    k: int = 3,
    n_perm: int = 9999,
    semilla: int = 42,
) -> pd.DataFrame:
    """I de Moran global de las estimaciones municipales y de otras variables de esos municipios.

    Construye la W de los municipios objetivo con sus `k` vecinos más cercanos (distancia de
    Haversine entre centroides, estandarizada por filas, como en `matriz_proximidad`) y calcula
    el I de Moran con p por permutaciones de cada variable. Sirve para el objetivo 3: si las
    estimaciones finales muestran autocorrelación, se compara con la de la covariable del
    benchmark, porque la estimación sintética hereda el patrón de x'β̂.

    Args:
        latitud (array-like): Latitud de cada municipio, en grados.
        longitud (array-like): Longitud de cada municipio, en grados.
        variables (dict[str, array-like]): Etiqueta → valores por municipio, en el mismo orden
            que las coordenadas.
        k (int): Vecinos más cercanos de la W.
        n_perm (int): Permutaciones de `moran_i`.
        semilla (int): Semilla de las permutaciones.

    Returns:
        pd.DataFrame: Una fila por variable con `variable`, `n`, `k_vecinos`, `I`, `esperado`,
            `z_perm` y `p_valor`.

    Raises:
        ValueError: Si alguna variable no tiene el mismo largo que las coordenadas.

    Casos de uso:
        Celda 9b de `fay_herriot_espacial.py` (tabla `fhe_moran_estimaciones`).

    Example:
        >>> lat = np.array([3.0, 3.1, 3.2, 4.0, 4.1, 4.2])
        >>> lon = np.array([-76.0, -76.1, -76.0, -75.0, -75.1, -75.0])
        >>> t = moran_estimaciones(lat, lon, {"tasa": [1, 1, 1, 9, 9, 9]}, k=2, n_perm=99)
        >>> bool(t["I"].iloc[0] > 0.5), int(t["n"].iloc[0])
        (True, 6)
    """
    latitud = np.asarray(latitud, dtype=float)
    longitud = np.asarray(longitud, dtype=float)
    W = estandarizar_filas(proximidad_knn(distancias_haversine(latitud, longitud), k))
    filas = []
    for etiqueta, valores in variables.items():
        valores = np.asarray(valores, dtype=float)
        if len(valores) != len(latitud):
            raise ValueError(
                f"La variable {etiqueta} tiene {len(valores)} valores y hay "
                f"{len(latitud)} municipios."
            )
        filas.append(
            {
                "variable": etiqueta,
                "n": int(len(valores)),
                "k_vecinos": int(k),
                **moran_i(valores, W, n_perm, semilla),
            }
        )
    return pd.DataFrame(filas)
