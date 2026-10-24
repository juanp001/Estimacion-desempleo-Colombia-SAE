"""Estabilidad de los coeficientes del benchmark seleccionado (análisis de sensibilidad, G7-B17).

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

G7-B18 (sensibilidad a dominios individuales, dejar-un-dominio-fuera o LOAO completo): el
dejar-uno-fuera de los coeficientes se complementa con (a) un cambio estandarizado
Δβ/EE(β̂) que no se infla cuando |β̂| es pequeño (el cambio porcentual sí), (b) el dominio que
produce el mínimo, el máximo y el mayor cambio de cada β_j, y (c) el efecto de cada exclusión en
las predicciones: EBLUP de los 22 dominios que quedan, predicción sintética del dominio excluido
(fuera de muestra), predicción sintética de los municipios objetivo, Â y la clase de
confiabilidad. Es el mismo reajuste completo (incluida Â) de la sensibilidad de Cook de
`seleccion_modelo.py` y de `extrapolacion.sensibilidad_quitar_dominio`, pero para los 23 dominios
y con las salidas pedidas por la revisión. Sustento y límites: la distancia de Cook y el
reajuste sin el dominio influyente son diagnósticos de regresión general (no del libro); el
LOAO de coeficientes y su efecto en predicciones es un análisis propio. Lo que sí respaldan las
fuentes es la lectura: en un área fuera de muestra el predictor es solo x'β̂
(Benedetti et al., 2024, p. 144; Morales et al., p. 441), de modo que un β̂ que depende de un
dominio mueve directamente las predicciones de los municipios.
"""

import numpy as np
import pandas as pd

from shared.consolidacion import clasificar_confiabilidad
from shared.modelo_area_pequena import prediccion_sintetica

# G7-B17: la significancia no es demostración fuerte (mismos 23 dominios filtran, seleccionan,
# comparan y calculan los p); este texto se imprime en el notebook y acompaña a la estabilidad.
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


def _reajustar_sin(modelo, clase_modelo: type, i: int):
    """Reajusta el modelo completo (incluida Â) sin la fila `i`.

    Args:
        modelo (ModeloAreaPequena): Benchmark ya ajustado.
        clase_modelo (type): Clase con la que reajustar (`FayHerriotClasico`).
        i (int): Posición (0 … n−1) del dominio que se retira.

    Returns:
        ModeloAreaPequena | None: Modelo ajustado con n−1 dominios, o None si el ajuste
            falla.

    Example:
        >>> ajuste = _reajustar_sin(ganador, FayHerriotClasico, 0)
    """
    df_sin = modelo.df.drop(index=modelo.df.index[i]).reset_index(drop=True)
    try:
        ajuste = clase_modelo(modelo.covars, df_sin, modelo.y_col, modelo.se_col)
        ajuste.ajustar()
    except Exception:
        return None
    return ajuste


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
            `Parametro`, `Beta_completo`, `Beta_sin_dominio`, `Cambio_pct` (NaN si
            β̂ completo es 0), `EE_completo` (error estándar de β̂ con todos los
            dominios), `Cambio_en_EE` (Δβ/EE, G7-B18), `Cambia_signo`, `p_completo`,
            `p_sin_dominio` y `Cruza_alfa` (True si el p-valor cambia de lado del umbral
            `alfa`). Los dominios cuyo reajuste falla se omiten.

    Example:
        >>> dejar_uno_fuera_coeficientes(ganador, FayHerriotClasico, nombres)
    """
    parametros = _parametros(modelo)
    filas = []
    for i in range(modelo.n):
        ajuste = _reajustar_sin(modelo, clase_modelo, i)
        if ajuste is None:
            continue
        for j, parametro in enumerate(parametros):
            completo, sin = float(modelo.beta_hat[j]), float(ajuste.beta_hat[j])
            ee = float(modelo.se_beta[j])
            filas.append(
                {
                    "Dominio_excluido": str(nombres_dominio[i]),
                    "Parametro": parametro,
                    "Beta_completo": completo,
                    "Beta_sin_dominio": sin,
                    "Cambio_pct": (
                        100 * (sin - completo) / abs(completo)
                        if completo != 0
                        else np.nan
                    ),
                    "EE_completo": ee,
                    "Cambio_en_EE": (sin - completo) / ee if ee > 0 else np.nan,
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
            `Dominio_beta_min`, `Dominio_beta_max` (dominios cuya exclusión da el mínimo y
            el máximo de β̂(-d)), `Cambio_pct_max_abs`, `Cambio_en_EE_max_abs`,
            `Dominio_max_cambio` (dominio de ese cambio estandarizado máximo),
            `N_cambia_signo`, `N_cruza_alfa`, `p_max` y `N_reajustes` (G7-B18).

    Example:
        >>> resumen_dejar_uno_fuera(detalle, 23)
    """
    filas = []
    for parametro, g in detalle.groupby("Parametro", sort=False):
        g = g.reset_index(drop=True)
        cambio_ee = g["Cambio_en_EE"].abs()
        filas.append(
            {
                "Parametro": parametro,
                "Beta_completo": g["Beta_completo"].iloc[0],
                "Beta_min": g["Beta_sin_dominio"].min(),
                "Dominio_beta_min": g.loc[
                    g["Beta_sin_dominio"].idxmin(), "Dominio_excluido"
                ],
                "Beta_max": g["Beta_sin_dominio"].max(),
                "Dominio_beta_max": g.loc[
                    g["Beta_sin_dominio"].idxmax(), "Dominio_excluido"
                ],
                "Cambio_pct_max_abs": g["Cambio_pct"].abs().max(),
                "Cambio_en_EE_max_abs": cambio_ee.max(),
                "Dominio_max_cambio": (
                    g.loc[cambio_ee.idxmax(), "Dominio_excluido"]
                    if cambio_ee.notna().any()
                    else None
                ),
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


# ── G7-B18: dejar-un-dominio-fuera (LOAO) completo y su efecto en las predicciones ──────────


def dejar_uno_fuera_predicciones(
    modelo,
    clase_modelo: type,
    nombres_dominio: np.ndarray,
    X_obj: np.ndarray = None,
    nombres_obj: np.ndarray = None,
) -> tuple:
    """Efecto de retirar cada dominio en las predicciones y en Â (G7-B18).

    Para cada dominio d se reajusta el modelo completo (incluida Â) sin d y se compara con el
    modelo con los 23 dominios:

    - **Dominios que quedan** (22): EBLUP completo frente a EBLUP sin d, y su CV.
    - **Dominio excluido**: su EBLUP completo frente a la predicción sintética fuera de muestra
      x_d'β̂(-d); es el error que cometería el modelo si d no tuviera encuesta.
    - **Municipios objetivo** (si se pasa `X_obj`): x_m'β̂ frente a x_m'β̂(-d), y su CV
      condicional al modelo (sqrt(x'Cov(β̂)x + Â)).
    - **Â**: varianza de efectos aleatorios con y sin d.

    Args:
        modelo (ModeloAreaPequena): Benchmark ya ajustado.
        clase_modelo (type): Clase con la que reajustar (`FayHerriotClasico`).
        nombres_dominio (np.ndarray): Nombre de cada dominio, en el orden de las filas.
        X_obj (np.ndarray | None): Matriz de diseño (con intercepto) de los municipios
            objetivo, shape (m, p). Si es None no se calcula el nivel municipal.
        nombres_obj (np.ndarray | None): Nombre de cada municipio (por defecto su posición).

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: (`detalle`, `por_dominio`). `detalle` tiene una fila
            por (dominio excluido, unidad) con `Nivel` (DOMINIO / DOMINIO_EXCLUIDO / MUNICIPIO),
            `Dominio_excluido`, `Unidad`, `Pred_completo`, `Pred_sin_dominio`, `Cambio_pp`,
            `CV_completo`, `CV_sin_dominio` y `Cambia_confiabilidad` (la clase por CV,
            `clasificar_confiabilidad`, cambia). `por_dominio` tiene una fila por dominio
            excluido con `A_completo`, `A_sin_dominio`, `Cambio_A_pct`. Los dominios cuyo
            reajuste falla se omiten.

    Example:
        >>> detalle, por_dominio = dejar_uno_fuera_predicciones(
        ...     ganador, FayHerriotClasico, nombres, X_obj, nombres_municipios
        ... )
    """
    if X_obj is not None:
        X_obj = np.asarray(X_obj, dtype=float)
        nombres_obj = (
            np.arange(len(X_obj)) if nombres_obj is None else np.asarray(nombres_obj)
        )
        pred_obj0, _, cv_obj0 = prediccion_sintetica(
            X_obj, modelo.beta_hat, modelo.cov_beta, modelo.A_hat
        )

    filas, filas_a = [], []
    for i in range(modelo.n):
        ajuste = _reajustar_sin(modelo, clase_modelo, i)
        if ajuste is None:
            continue
        excluido = str(nombres_dominio[i])
        resto = np.delete(np.arange(modelo.n), i)

        # Dominios que quedan: EBLUP completo (posiciones resto) vs. EBLUP del reajuste.
        for k, pos in enumerate(resto):
            filas.append(
                (
                    "DOMINIO",
                    excluido,
                    str(nombres_dominio[pos]),
                    float(modelo.eblup[pos]),
                    float(ajuste.eblup[k]),
                    float(modelo.cv[pos]),
                    float(ajuste.cv[k]),
                )
            )

        # Dominio excluido: EBLUP con todos vs. sintético fuera de muestra sin él.
        pred_i, _, cv_i = prediccion_sintetica(
            modelo.X[[i]], ajuste.beta_hat, ajuste.cov_beta, ajuste.A_hat
        )
        filas.append(
            (
                "DOMINIO_EXCLUIDO",
                excluido,
                excluido,
                float(modelo.eblup[i]),
                float(pred_i[0]),
                float(modelo.cv[i]),
                float(cv_i[0]),
            )
        )

        if X_obj is not None:
            pred_obj, _, cv_obj = prediccion_sintetica(
                X_obj, ajuste.beta_hat, ajuste.cov_beta, ajuste.A_hat
            )
            for m in range(len(X_obj)):
                filas.append(
                    (
                        "MUNICIPIO",
                        excluido,
                        str(nombres_obj[m]),
                        float(pred_obj0[m]),
                        float(pred_obj[m]),
                        float(cv_obj0[m]),
                        float(cv_obj[m]),
                    )
                )

        filas_a.append(
            {
                "Dominio_excluido": excluido,
                "A_completo": float(modelo.A_hat),
                "A_sin_dominio": float(ajuste.A_hat),
                "Cambio_A_pct": (
                    100 * (float(ajuste.A_hat) - float(modelo.A_hat)) / modelo.A_hat
                    if modelo.A_hat > 0
                    else np.nan
                ),
            }
        )

    detalle = pd.DataFrame(
        filas,
        columns=[
            "Nivel",
            "Dominio_excluido",
            "Unidad",
            "Pred_completo",
            "Pred_sin_dominio",
            "CV_completo",
            "CV_sin_dominio",
        ],
    )
    detalle["Cambio_pp"] = detalle["Pred_sin_dominio"] - detalle["Pred_completo"]
    detalle["Cambia_confiabilidad"] = [
        clasificar_confiabilidad(a) != clasificar_confiabilidad(b)
        for a, b in zip(detalle["CV_completo"], detalle["CV_sin_dominio"])
    ]
    return detalle, pd.DataFrame(filas_a)


def resumen_influencia_dominios(
    detalle_coef: pd.DataFrame,
    detalle_pred: pd.DataFrame,
    por_dominio: pd.DataFrame,
    municipios_extrapolan: dict = None,
    umbral_ee: float = 1.0,
    umbral_pp: float = 0.5,
) -> pd.DataFrame:
    """Resume la influencia de cada dominio en coeficientes y predicciones (G7-B18).

    Args:
        detalle_coef (pd.DataFrame): Salida de `dejar_uno_fuera_coeficientes`.
        detalle_pred (pd.DataFrame): Primer elemento de `dejar_uno_fuera_predicciones`.
        por_dominio (pd.DataFrame): Segundo elemento de `dejar_uno_fuera_predicciones`.
        municipios_extrapolan (dict | None): `{municipio: bool}`, True si su predicción es
            una extrapolación (ESTADO_EXTRAPOLACION distinto de DENTRO_DEL_RANGO). Si se
            pasa, separa el cambio máximo de municipios extrapolados y no extrapolados.
        umbral_ee (float): Cambio estandarizado Δβ/EE a partir del cual un coeficiente se
            considera movido (`LOAO_UMBRAL_CAMBIO_EE`).
        umbral_pp (float): Cambio en pp a partir del cual una predicción se considera movida
            (`LOAO_UMBRAL_PRED_PP`).

    Returns:
        pd.DataFrame: Una fila por dominio excluido, ordenada por `Cambio_en_EE_max_abs`
            descendente, con `Cambio_en_EE_max_abs` y `Parametro_max` (el coeficiente más
            movido), `N_coef_sobre_umbral`, `N_cambia_signo`, `N_cruza_alfa`,
            `Cambio_EBLUP_max_pp` y `Dominio_EBLUP_max` (entre los que quedan),
            `N_EBLUP_sobre_umbral`, `Cambio_propio_pp` (sintético sin el dominio − su
            EBLUP), `Cambio_sintetico_max_pp`, `Cambio_sintetico_medio_pp`, `Municipio_max`,
            `N_sintetico_sobre_umbral`, `Cambio_sintetico_max_extrapolan_pp` y
            `Cambio_sintetico_max_no_extrapolan_pp` (si se pasó `municipios_extrapolan`),
            `N_cambia_confiabilidad` (EBLUP + municipios), `A_completo`, `A_sin_dominio` y
            `Cambio_A_pct`.

    Example:
        >>> resumen_influencia_dominios(detalle_coef, detalle_pred, por_dominio)
    """
    param = detalle_coef[detalle_coef["Parametro"] != "Intercepto"]
    filas = []
    for dominio, g in param.groupby("Dominio_excluido", sort=False):
        g = g.reset_index(drop=True)
        abs_ee = g["Cambio_en_EE"].abs()
        fila = {
            "Dominio_excluido": dominio,
            "Cambio_en_EE_max_abs": abs_ee.max(),
            "Parametro_max": (
                g.loc[abs_ee.idxmax(), "Parametro"] if abs_ee.notna().any() else None
            ),
            "N_coef_sobre_umbral": int((abs_ee > umbral_ee).sum()),
            "N_cambia_signo": int(g["Cambia_signo"].sum()),
            "N_cruza_alfa": int(g["Cruza_alfa"].sum()),
        }
        p = detalle_pred[detalle_pred["Dominio_excluido"] == dominio]
        eb = p[p["Nivel"] == "DOMINIO"]
        if len(eb):
            k = eb["Cambio_pp"].abs().idxmax()
            fila["Cambio_EBLUP_max_pp"] = float(eb.loc[k, "Cambio_pp"])
            fila["Dominio_EBLUP_max"] = eb.loc[k, "Unidad"]
            fila["N_EBLUP_sobre_umbral"] = int(
                (eb["Cambio_pp"].abs() > umbral_pp).sum()
            )
        propio = p[p["Nivel"] == "DOMINIO_EXCLUIDO"]
        if len(propio):
            fila["Cambio_propio_pp"] = float(propio["Cambio_pp"].iloc[0])
        mun = p[p["Nivel"] == "MUNICIPIO"]
        if len(mun):
            k = mun["Cambio_pp"].abs().idxmax()
            fila["Cambio_sintetico_max_pp"] = float(mun.loc[k, "Cambio_pp"])
            fila["Municipio_max"] = mun.loc[k, "Unidad"]
            fila["Cambio_sintetico_medio_pp"] = float(mun["Cambio_pp"].abs().mean())
            fila["N_sintetico_sobre_umbral"] = int(
                (mun["Cambio_pp"].abs() > umbral_pp).sum()
            )
            if municipios_extrapolan is not None:
                marca = (
                    mun["Unidad"].map(municipios_extrapolan).fillna(False).astype(bool)
                )
                for etiqueta, sel in (("extrapolan", marca), ("no_extrapolan", ~marca)):
                    sub = mun.loc[sel, "Cambio_pp"].abs()
                    fila[f"Cambio_sintetico_max_{etiqueta}_pp"] = (
                        float(sub.max()) if len(sub) else np.nan
                    )
        fila["N_cambia_confiabilidad"] = int(
            p[p["Nivel"].isin(["DOMINIO", "MUNICIPIO"])]["Cambia_confiabilidad"].sum()
        )
        filas.append(fila)
    resumen = pd.DataFrame(filas).merge(por_dominio, on="Dominio_excluido", how="left")
    return resumen.sort_values("Cambio_en_EE_max_abs", ascending=False).reset_index(
        drop=True
    )


def top_dominios_por_parametro(detalle_coef: pd.DataFrame, k: int = 3) -> pd.DataFrame:
    """Los k dominios que más mueven cada coeficiente (G7-B18).

    Args:
        detalle_coef (pd.DataFrame): Salida de `dejar_uno_fuera_coeficientes`.
        k (int): Cuántos dominios mostrar por parámetro.

    Returns:
        pd.DataFrame: Hasta k filas por parámetro (sin intercepto), ordenadas por
            |Cambio_en_EE| descendente, con `Parametro`, `Dominio_excluido`,
            `Beta_completo`, `Beta_sin_dominio`, `Cambio_pct`, `Cambio_en_EE`,
            `Cambia_signo` y `Cruza_alfa`.

    Example:
        >>> top_dominios_por_parametro(detalle_coef, k=3)
    """
    d = detalle_coef[detalle_coef["Parametro"] != "Intercepto"].copy()
    d["_abs"] = d["Cambio_en_EE"].abs()
    d = d.sort_values(["Parametro", "_abs"], ascending=[True, False])
    d = d.groupby("Parametro", sort=False).head(k)
    columnas = [
        "Parametro",
        "Dominio_excluido",
        "Beta_completo",
        "Beta_sin_dominio",
        "Cambio_pct",
        "Cambio_en_EE",
        "Cambia_signo",
        "Cruza_alfa",
    ]
    return d[columnas].reset_index(drop=True)


def interpretar_influencia(
    resumen_loo: pd.DataFrame,
    influencia: pd.DataFrame,
    umbral_ee: float = 1.0,
    umbral_pp: float = 0.5,
) -> str:
    """Redacta la lectura del LOAO completo calculada desde las tablas (G7-B18).

    Args:
        resumen_loo (pd.DataFrame): Salida de `resumen_dejar_uno_fuera`.
        influencia (pd.DataFrame): Salida de `resumen_influencia_dominios`.
        umbral_ee (float): Umbral del cambio estandarizado Δβ/EE.
        umbral_pp (float): Umbral del cambio en predicciones, en pp.

    Returns:
        str: Texto con una línea por covariable, el balance de las predicciones y la
            advertencia de selección. Sin cifras fijas: todo sale de las tablas.

    Example:
        >>> print(interpretar_influencia(resumen_loo, influencia))
    """
    lineas = []
    for _, f in resumen_loo[resumen_loo["Parametro"] != "Intercepto"].iterrows():
        mov = "supera" if f["Cambio_en_EE_max_abs"] > umbral_ee else "no supera"
        lineas.append(
            f"- {f['Parametro']}: β̂ = {f['Beta_completo']:.3f}; al retirar un dominio queda "
            f"entre {f['Beta_min']:.3f} (sin {f['Dominio_beta_min']}) y {f['Beta_max']:.3f} "
            f"(sin {f['Dominio_beta_max']}); cambio máximo {f['Cambio_pct_max_abs']:.0f} % = "
            f"{f['Cambio_en_EE_max_abs']:.2f} EE (sin {f['Dominio_max_cambio']}), que "
            f"{mov} {umbral_ee:g} EE; signo cambia en {f['N_cambia_signo']} de "
            f"{f['N_reajustes']} y cruza la significancia en {f['N_cruza_alfa']}."
        )
    lineas.append("")
    top = influencia.iloc[0]
    lineas.append(
        f"Dominio más influyente en los coeficientes: {top['Dominio_excluido']} "
        f"({top['Cambio_en_EE_max_abs']:.2f} EE en {top['Parametro_max']}). "
        f"Dominios con algún coeficiente sobre {umbral_ee:g} EE: "
        f"{int((influencia['N_coef_sobre_umbral'] > 0).sum())} de {len(influencia)}."
    )
    if "Cambio_EBLUP_max_pp" in influencia:
        i = influencia["Cambio_EBLUP_max_pp"].abs().idxmax()
        lineas.append(
            f"EBLUP de los dominios que quedan: el mayor cambio es "
            f"{influencia.loc[i, 'Cambio_EBLUP_max_pp']:+.2f} pp en "
            f"{influencia.loc[i, 'Dominio_EBLUP_max']} al retirar "
            f"{influencia.loc[i, 'Dominio_excluido']}; "
            f"{int((influencia['N_EBLUP_sobre_umbral'] > 0).sum())} exclusiones mueven algún "
            f"EBLUP más de {umbral_pp:g} pp."
        )
    if "Cambio_propio_pp" in influencia:
        i = influencia["Cambio_propio_pp"].abs().idxmax()
        lineas.append(
            f"Predecir un dominio como si no tuviera encuesta (sintético sin él − su EBLUP): "
            f"el mayor error es {influencia.loc[i, 'Cambio_propio_pp']:+.2f} pp en "
            f"{influencia.loc[i, 'Dominio_excluido']}."
        )
    if "Cambio_sintetico_max_pp" in influencia:
        i = influencia["Cambio_sintetico_max_pp"].abs().idxmax()
        lineas.append(
            f"Predicción sintética de municipios: el mayor cambio es "
            f"{influencia.loc[i, 'Cambio_sintetico_max_pp']:+.2f} pp en "
            f"{influencia.loc[i, 'Municipio_max']} al retirar "
            f"{influencia.loc[i, 'Dominio_excluido']}; "
            f"{int((influencia['N_sintetico_sobre_umbral'] > 0).sum())} exclusiones mueven "
            f"algún municipio más de {umbral_pp:g} pp."
        )
        if "Cambio_sintetico_max_extrapolan_pp" in influencia:
            ex = influencia["Cambio_sintetico_max_extrapolan_pp"].abs().max()
            no = influencia["Cambio_sintetico_max_no_extrapolan_pp"].abs().max()
            lineas.append(
                f"  Máximo en municipios que extrapolan: {ex:.2f} pp; en los que no "
                f"extrapolan: {no:.2f} pp."
            )
    lineas.append(
        f"Cambios de clase de confiabilidad (CV) sumados sobre todas las exclusiones: "
        f"{int(influencia['N_cambia_confiabilidad'].sum())}. "
        f"Â cambia como máximo {influencia['Cambio_A_pct'].abs().max():.0f} %."
    )
    return "\n".join(lineas) + "\n\n" + ADVERTENCIA_POST_SELECCION


def figura_influencia(detalle_coef: pd.DataFrame):
    """Mapa de calor del cambio estandarizado Δβ/EE por dominio excluido y covariable.

    Args:
        detalle_coef (pd.DataFrame): Salida de `dejar_uno_fuera_coeficientes`.

    Returns:
        matplotlib.figure.Figure | None: Figura (sin título ni guardado, como las del modelo)
            o None si no hay covariables.

    Example:
        >>> fig = figura_influencia(detalle_coef); display(fig); plt.close(fig)
    """
    import matplotlib.pyplot as plt

    d = detalle_coef[detalle_coef["Parametro"] != "Intercepto"]
    if d.empty:
        return None
    m = d.pivot(index="Dominio_excluido", columns="Parametro", values="Cambio_en_EE")
    m = m.loc[m.abs().max(axis=1).sort_values(ascending=False).index]
    lim = max(float(np.nanmax(np.abs(m.values))), 1e-9)
    fig, ax = plt.subplots(figsize=(1.6 * m.shape[1] + 3, 0.28 * len(m) + 1.5))
    im = ax.imshow(m.values, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
    ax.set_xticks(range(m.shape[1]), m.columns, rotation=30, ha="right")
    ax.set_yticks(range(len(m)), m.index)
    for r in range(m.shape[0]):
        for c in range(m.shape[1]):
            ax.text(c, r, f"{m.values[r, c]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, label="Δβ / EE(β̂) al retirar el dominio")
    fig.tight_layout()
    return fig
