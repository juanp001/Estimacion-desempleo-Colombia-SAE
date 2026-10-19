"""Extrapolación de la predicción sintética (B20): rangos, responsables y sensibilidad.

Qué problema documenta
----------------------
Un municipio sin estimación directa recibe la predicción sintética x_m'β̂, con β̂ estimado solo
con los dominios que tienen encuesta (Benedetti et al., 2024, p. 144: en un área fuera de muestra
el estimador es X_r β̂). Si las covariables del municipio quedan fuera del rango que tomaron en esos
dominios, la predicción supone que la recta sigue valiendo donde el modelo nunca vio datos. El libro
advierte que al predecir fuera de muestra se pueden obtener predicciones absurdas (Morales et al.,
2021, p. 453), y el CV del sintético no recoge ese riesgo: el estimador sintético es sesgado si el
modelo no se cumple y su varianza pequeña «induce erróneamente a pensar que el estimador tiene
calidad» (Molina, 2019, CEPAL, PDF 40-41).

Qué se calcula (todo con cualquier número de covariables)
---------------------------------------------------------
1. **Rango observado** de cada covariable en los dominios (mínimo, máximo y qué dominio fija cada
   borde) frente a los municipios (``rangos_covariables``).
2. **Estado de extrapolación** de cada municipio (``estado_extrapolacion``):
   * ``FUERA_DEL_RANGO``: alguna covariable queda por debajo del mínimo o por encima del máximo
     de los dominios.
   * ``COMBINACION_ATIPICA``: cada covariable está dentro de su rango, pero la combinación queda
     más lejos del centro de los datos que cualquier dominio: h_m = x_m'Cov(β̂)x_m (el término de
     la varianza del sintético por estimar β, Morales et al., p. 441) supera el máximo de la
     muestra. Solo puede pasar con dos o más covariables.
   * ``DENTRO_DEL_RANGO``: ninguno de los dos.
3. **Aporte extrapolado**: la predicción con las covariables recortadas al rango de los dominios,
   x̃_m'β̂, y la diferencia x_m'β̂ − x̃_m'β̂ en puntos porcentuales. Por covariable,
   β̂_j·(x_j − x̃_j); la que más aporta es la ``COVARIABLE_PRINCIPAL`` (``prediccion_acotada``).
4. **Sensibilidad «quitar un dominio»**: se reajusta el modelo sin cada dominio (reajuste completo,
   como ``seleccion_modelo.sensibilidad_cook``) y se predice de nuevo; la amplitud mín–máx muestra
   cuánto depende cada predicción de un solo dominio (``sensibilidad_quitar_dominio``).

La tasa publicada no cambia: la predicción acotada es solo un escenario de sensibilidad.

Las figuras no llevan título: el contexto lo da el notebook que las muestra.
"""

import contextlib
import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ESTADO_DENTRO = "DENTRO_DEL_RANGO"
ESTADO_FUERA = "FUERA_DEL_RANGO"
ESTADO_COMBINACION = "COMBINACION_ATIPICA"

# Tolerancia relativa para comparar h con el máximo de la muestra (evita marcar por redondeo).
_TOL_H = 1e-9


def _covariables(X) -> np.ndarray:
    """Quita la columna del intercepto de una matriz de diseño.

    Args:
        X (array-like): Matriz de diseño (n, p) con el intercepto en la primera columna.

    Returns:
        np.ndarray: Matriz (n, p − 1) con solo las covariables.
    """
    return np.asarray(X, dtype=float)[:, 1:]


def apalancamiento(X, cov_beta) -> np.ndarray:
    """h = x'Cov(β̂)x de cada fila de X.

    Es el término de la varianza del predictor sintético que se debe a estimar β (Morales et al.,
    2021, p. 441): crece a medida que x se aleja del centro de los datos de ajuste.

    Args:
        X (array-like): Matriz de diseño (n, p) con intercepto.
        cov_beta (array-like): Covarianza de β̂, (p, p).

    Returns:
        np.ndarray: h de cada fila, shape (n,).

    Example:
        >>> apalancamiento([[1.0, 2.0]], np.eye(2) * 0.1)
        array([0.5])
    """
    X = np.asarray(X, dtype=float)
    return np.einsum("ij,jk,ik->i", X, np.asarray(cov_beta, dtype=float), X)


def rangos_covariables(
    X_muestra, X_nuevos, covars: list, nombres_muestra
) -> pd.DataFrame:
    """Rango de cada covariable en los dominios de ajuste frente a los municipios a predecir.

    Args:
        X_muestra (array-like): Matriz de diseño de los dominios (n, p), con intercepto.
        X_nuevos (array-like): Matriz de diseño de los municipios (m, p), con intercepto.
        covars (list[str]): Nombres de las covariables, en el orden de las columnas 1..p−1.
        nombres_muestra (array-like): Nombre de cada dominio, en el orden de las filas.

    Returns:
        pd.DataFrame: Una fila por covariable con COVARIABLE, MIN_DOMINIOS, DOMINIO_MIN,
            MAX_DOMINIOS, DOMINIO_MAX, MIN_MUNICIPIOS, MEDIANA_MUNICIPIOS, MAX_MUNICIPIOS,
            N_DEBAJO, N_ENCIMA, N_MUNICIPIOS y PCT_FUERA (% de municipios fuera del rango).

    Casos de uso:
        Tabla de rangos de B20 en `modelo/fay_herriot.py` (celda 10a).

    Example:
        >>> Xm = [[1, 0.0], [1, 1.0], [1, 2.0]]
        >>> Xn = [[1, 1.5], [1, 3.0], [1, -1.0]]
        >>> r = rangos_covariables(Xm, Xn, ["X1"], ["A", "B", "C"])
        >>> r[["DOMINIO_MIN", "DOMINIO_MAX", "N_DEBAJO", "N_ENCIMA"]].values.tolist()
        [['A', 'C', 1, 1]]
    """
    Zm, Zn = _covariables(X_muestra), _covariables(X_nuevos)
    nombres = np.asarray(nombres_muestra)
    filas = []
    for j, covar in enumerate(covars):
        lo, hi = Zm[:, j].min(), Zm[:, j].max()
        debajo = int((Zn[:, j] < lo).sum())
        encima = int((Zn[:, j] > hi).sum())
        filas.append(
            {
                "COVARIABLE": covar,
                "MIN_DOMINIOS": float(lo),
                "DOMINIO_MIN": str(nombres[np.argmin(Zm[:, j])]),
                "MAX_DOMINIOS": float(hi),
                "DOMINIO_MAX": str(nombres[np.argmax(Zm[:, j])]),
                "MIN_MUNICIPIOS": float(Zn[:, j].min()),
                "MEDIANA_MUNICIPIOS": float(np.median(Zn[:, j])),
                "MAX_MUNICIPIOS": float(Zn[:, j].max()),
                "N_DEBAJO": debajo,
                "N_ENCIMA": encima,
                "N_MUNICIPIOS": len(Zn),
                "PCT_FUERA": round(100 * (debajo + encima) / len(Zn), 1),
            }
        )
    return pd.DataFrame(filas)


def prediccion_acotada(X_muestra, X_nuevos, beta) -> tuple:
    """Predicción con las covariables recortadas al rango de los dominios y aporte por covariable.

    Cada covariable x_j del municipio se reemplaza por x̃_j = min(max(x_j, mín_j), máx_j), donde
    mín_j y máx_j son el mínimo y el máximo en los dominios de ajuste. x̃'β̂ es lo que el modelo
    predice usando solo valores que observó; β̂_j·(x_j − x̃_j) es lo que añade salirse del rango.

    Args:
        X_muestra (array-like): Matriz de diseño de los dominios (n, p), con intercepto.
        X_nuevos (array-like): Matriz de diseño de los municipios (m, p), con intercepto.
        beta (array-like): Coeficientes β̂, shape (p,), con el intercepto primero.

    Returns:
        tuple[np.ndarray, np.ndarray]: (pred_acotada shape (m,), aportes shape (m, p − 1)). La
            suma de cada fila de aportes es x'β̂ − x̃'β̂.

    Casos de uso:
        Escenario de sensibilidad y aporte extrapolado de B20.

    Example:
        >>> acot, aportes = prediccion_acotada([[1, 0.0], [1, 2.0]], [[1, 1.0], [1, 3.0]], [1.0, 2.0])
        >>> acot.tolist(), aportes.ravel().tolist()
        ([3.0, 5.0], [0.0, 2.0])
    """
    Zm, Zn = _covariables(X_muestra), _covariables(X_nuevos)
    beta = np.asarray(beta, dtype=float)
    Z_acot = np.clip(Zn, Zm.min(axis=0), Zm.max(axis=0))
    pred_acot = beta[0] + Z_acot @ beta[1:]
    aportes = (Zn - Z_acot) * beta[1:]
    return pred_acot, aportes


def estado_extrapolacion(
    X_muestra, X_nuevos, cov_beta, beta, covars: list
) -> pd.DataFrame:
    """Estado de extrapolación, covariables responsables y aporte de cada municipio.

    Reglas (en este orden):

    * ``FUERA_DEL_RANGO`` si alguna covariable queda fuera del [mín, máx] de los dominios.
    * ``COMBINACION_ATIPICA`` si todas están dentro de su rango pero h = x'Cov(β̂)x supera el
      máximo de h en los dominios (Morales et al., p. 441): cada valor es habitual, la
      combinación no.
    * ``DENTRO_DEL_RANGO`` en otro caso.

    Args:
        X_muestra (array-like): Matriz de diseño de los dominios (n, p), con intercepto.
        X_nuevos (array-like): Matriz de diseño de los municipios (m, p), con intercepto.
        cov_beta (array-like): Covarianza de β̂ del modelo, (p, p).
        beta (array-like): Coeficientes β̂, shape (p,).
        covars (list[str]): Nombres de las covariables (columnas 1..p−1).

    Returns:
        pd.DataFrame: Una fila por municipio, en el orden de X_nuevos, con
            ESTADO_EXTRAPOLACION, N_COVARIABLES_FUERA, COVARIABLES_FUERA (nombres separados por
            coma, "" si ninguna), COVARIABLE_PRINCIPAL (la de mayor |aporte|, "" si el aporte es
            0), RAZON_H (h_m / máx h de los dominios), PRED_ACOTADA y APORTE_EXTRAPOLADO_PP.

    Casos de uso:
        Columnas de B20 en `fay_herriot_prediccion_sintetica`; `diagnosticos.marca_extrapolacion`
        la usa para que el modelo y `sensibilidad_varianza` marquen con el mismo criterio.

    Example:
        Una covariable: el municipio con x = 3 queda por encima del máximo (2).

        >>> Xm = np.array([[1, 0.0], [1, 1.0], [1, 2.0]])
        >>> C = np.linalg.inv(Xm.T @ Xm)
        >>> e = estado_extrapolacion(Xm, [[1, 1.5], [1, 3.0]], C, [1.0, 2.0], ["X1"])
        >>> e[["ESTADO_EXTRAPOLACION", "COVARIABLE_PRINCIPAL", "APORTE_EXTRAPOLADO_PP"]].values.tolist()
        [['DENTRO_DEL_RANGO', '', 0.0], ['FUERA_DEL_RANGO', 'X1', 2.0]]

        Dos covariables casi iguales en los dominios: (2, 0) tiene cada valor dentro de su rango,
        pero esa combinación nunca se observó.

        >>> Xm = np.array([[1, 0, 0], [1, 1, 1], [1, 2, 2], [1, 1, 1.2], [1, 0.2, 0]])
        >>> C = np.linalg.inv(Xm.T @ Xm)
        >>> e = estado_extrapolacion(Xm, [[1, 1, 1], [1, 2, 0]], C, [1, 1, 1], ["X1", "X2"])
        >>> e["ESTADO_EXTRAPOLACION"].tolist()
        ['DENTRO_DEL_RANGO', 'COMBINACION_ATIPICA']
    """
    Zm, Zn = _covariables(X_muestra), _covariables(X_nuevos)
    fuera = (Zn < Zm.min(axis=0)) | (Zn > Zm.max(axis=0))
    h_max = apalancamiento(X_muestra, cov_beta).max()
    razon_h = apalancamiento(X_nuevos, cov_beta) / h_max
    pred_acot, aportes = prediccion_acotada(X_muestra, X_nuevos, beta)

    estado = np.where(
        fuera.any(axis=1),
        ESTADO_FUERA,
        np.where(razon_h > 1 + _TOL_H, ESTADO_COMBINACION, ESTADO_DENTRO),
    )
    nombres = np.asarray(covars, dtype=object)
    covariables_fuera = [", ".join(nombres[f]) for f in fuera]
    principal = [
        str(nombres[np.argmax(np.abs(a))]) if a.size and np.abs(a).max() > 0 else ""
        for a in aportes
    ]
    pred = np.asarray(X_nuevos, dtype=float) @ np.asarray(beta, dtype=float)
    return pd.DataFrame(
        {
            "ESTADO_EXTRAPOLACION": estado,
            "N_COVARIABLES_FUERA": fuera.sum(axis=1).astype(int),
            "COVARIABLES_FUERA": covariables_fuera,
            "COVARIABLE_PRINCIPAL": principal,
            "RAZON_H": razon_h.round(3),
            "PRED_ACOTADA": pred_acot.round(4),
            "APORTE_EXTRAPOLADO_PP": (pred - pred_acot).round(4),
        }
    )


def sensibilidad_quitar_dominio(
    modelo, clase_modelo: type, X_nuevos, nombres_dominio
) -> tuple:
    """Reajusta el modelo sin cada dominio y mide cuánto cambian las predicciones sintéticas.

    Para cada dominio d se reajusta el modelo completo (Â y β̂) con los otros n − 1 dominios,
    igual que `seleccion_modelo.sensibilidad_cook` pero para todos los dominios, y se predice
    x_m'β̂_(−d) en cada municipio. Si la predicción de un municipio cambia mucho al quitar un solo
    dominio, depende de ese dominio, típicamente el que fija el borde del rango de una covariable.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado (el ganador), con `df`, `covars`, `y_col`,
            `se_col` y `beta_hat`.
        clase_modelo (type): Clase con la que reajustar (p. ej. `FayHerriotClasico`).
        X_nuevos (array-like): Matriz de diseño de los municipios (m, p), con intercepto.
        nombres_dominio (array-like): Nombre de cada dominio, en el orden de las filas del modelo.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]:
            - por_municipio (m filas, orden de X_nuevos): PRED_BASE, PRED_MIN_SIN_DOMINIO,
              PRED_MAX_SIN_DOMINIO, AMPLITUD_SIN_DOMINIO_PP, CAMBIO_MAX_PP (mayor |cambio|
              frente a la base) y DOMINIO_MAS_INFLUYENTE (el que produce ese cambio).
            - por_dominio (n filas): DOMINIO_EXCLUIDO, un β̂ por parámetro (Intercepto y cada
              covariable), A_HAT, CAMBIO_MEDIO_PP y CAMBIO_MAX_PP (|cambio| de las predicciones
              municipales), ordenado de mayor a menor cambio medio.

    Casos de uso:
        Sensibilidad de B20 en `modelo/fay_herriot.py` (celda 10a), con el ganador.
    """
    X_nuevos = np.asarray(X_nuevos, dtype=float)
    nombres = np.asarray(nombres_dominio).astype(str)
    base = X_nuevos @ modelo.beta_hat
    parametros = ["Intercepto"] + list(modelo.covars)

    preds, filas = [], []
    for i in range(len(modelo.df)):
        df_sin = modelo.df.drop(index=modelo.df.index[i]).reset_index(drop=True)
        reajuste = clase_modelo(modelo.covars, df_sin, modelo.y_col, modelo.se_col)
        with contextlib.redirect_stdout(io.StringIO()):
            reajuste.ajustar()
        pred = X_nuevos @ reajuste.beta_hat
        cambio = np.abs(pred - base)
        preds.append(pred)
        filas.append(
            {
                "DOMINIO_EXCLUIDO": nombres[i],
                **{p: float(b) for p, b in zip(parametros, reajuste.beta_hat)},
                "A_HAT": float(reajuste.A_hat),
                "CAMBIO_MEDIO_PP": float(cambio.mean()),
                "CAMBIO_MAX_PP": float(cambio.max()),
            }
        )

    preds = np.column_stack(preds)  # (m, n)
    cambios = np.abs(preds - base[:, None])
    por_municipio = pd.DataFrame(
        {
            "PRED_BASE": base.round(4),
            "PRED_MIN_SIN_DOMINIO": preds.min(axis=1).round(4),
            "PRED_MAX_SIN_DOMINIO": preds.max(axis=1).round(4),
            "AMPLITUD_SIN_DOMINIO_PP": (preds.max(axis=1) - preds.min(axis=1)).round(4),
            "CAMBIO_MAX_PP": cambios.max(axis=1).round(4),
            "DOMINIO_MAS_INFLUYENTE": nombres[cambios.argmax(axis=1)],
        }
    )
    por_dominio = (
        pd.DataFrame(filas)
        .sort_values("CAMBIO_MEDIO_PP", ascending=False)
        .reset_index(drop=True)
        .round(4)
    )
    return por_municipio, por_dominio


def figura_rangos(X_muestra, X_nuevos, covars: list):
    """Valores de cada covariable en los dominios y en los municipios, con el rango de los dominios.

    Un panel por covariable: arriba los dominios, abajo los municipios; la franja sombreada es el
    rango [mín, máx] de los dominios y los municipios fuera de ella se resaltan.

    Args:
        X_muestra (array-like): Matriz de diseño de los dominios (n, p), con intercepto.
        X_nuevos (array-like): Matriz de diseño de los municipios (m, p), con intercepto.
        covars (list[str]): Nombres de las covariables.

    Returns:
        matplotlib.figure.Figure | None: La figura, o None si el modelo no tiene covariables.

    Casos de uso:
        Figura de rangos de B20 (celda 10a de `modelo/fay_herriot.py`).
    """
    if not covars:
        return None
    Zm, Zn = _covariables(X_muestra), _covariables(X_nuevos)
    fig, axes = plt.subplots(
        len(covars), 1, figsize=(9, 1.9 * len(covars) + 0.4), squeeze=False
    )
    rng = np.random.default_rng(0)
    for j, (ax, covar) in enumerate(zip(axes[:, 0], covars)):
        lo, hi = Zm[:, j].min(), Zm[:, j].max()
        fuera = (Zn[:, j] < lo) | (Zn[:, j] > hi)
        ax.axvspan(lo, hi, color="tab:green", alpha=0.15, label="Rango de los dominios")
        ax.scatter(
            Zm[:, j],
            1 + rng.uniform(-0.12, 0.12, len(Zm)),
            color="tab:green",
            s=22,
            label="Dominios (con encuesta)",
        )
        ax.scatter(
            Zn[~fuera, j],
            rng.uniform(-0.12, 0.12, (~fuera).sum()),
            color="gray",
            s=18,
            label="Municipios dentro del rango",
        )
        ax.scatter(
            Zn[fuera, j],
            rng.uniform(-0.12, 0.12, fuera.sum()),
            color="tab:red",
            s=18,
            label="Municipios fuera del rango",
        )
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["Municipios", "Dominios"])
        ax.set_ylim(-0.5, 1.5)
        ax.set_xlabel(covar)
        ax.grid(axis="x", alpha=0.3)
    axes[0, 0].legend(
        loc="upper center", bbox_to_anchor=(0.5, 1.45), ncol=4, fontsize=8
    )
    fig.tight_layout()
    return fig


def figura_sensibilidad(df: pd.DataFrame, max_directa: float = None):
    """Predicción base, acotada y rango al quitar un dominio en los municipios que extrapolan.

    Args:
        df (pd.DataFrame): Una fila por municipio con MUNICIPIO, ESTADO_EXTRAPOLACION,
            PRED_SINTETICO, PRED_ACOTADA, PRED_MIN_SIN_DOMINIO y PRED_MAX_SIN_DOMINIO.
        max_directa (float, optional): Estimación directa más alta de los dominios, que se
            dibuja como referencia.

    Returns:
        matplotlib.figure.Figure | None: La figura, o None si ningún municipio extrapola.

    Casos de uso:
        Figura de sensibilidad de B20 (celda 10a de `modelo/fay_herriot.py`).
    """
    sub = df[df["ESTADO_EXTRAPOLACION"] != ESTADO_DENTRO].sort_values("PRED_SINTETICO")
    if sub.empty:
        return None
    y = np.arange(len(sub))
    fig, ax = plt.subplots(figsize=(9, 0.22 * len(sub) + 1.4))
    ax.hlines(
        y,
        sub["PRED_MIN_SIN_DOMINIO"],
        sub["PRED_MAX_SIN_DOMINIO"],
        color="tab:blue",
        lw=3,
        alpha=0.5,
        label="Mín–máx al quitar un dominio",
    )
    ax.scatter(
        sub["PRED_SINTETICO"], y, color="black", s=18, label="Predicción publicada"
    )
    ax.scatter(
        sub["PRED_ACOTADA"],
        y,
        color="tab:green",
        marker="D",
        s=18,
        label="Covariables acotadas al rango",
    )
    if max_directa is not None:
        ax.axvline(
            max_directa,
            color="gray",
            ls="--",
            lw=1,
            label="Directa más alta (dominios)",
        )
    ax.set_yticks(y)
    ax.set_yticklabels(sub["MUNICIPIO"], fontsize=7)
    ax.set_xlabel("Tasa de desempleo (%)")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return fig


def interpretar_extrapolacion(
    rangos: pd.DataFrame,
    df: pd.DataFrame,
    por_dominio: pd.DataFrame,
    max_directa: float = None,
) -> str:
    """Texto, calculado con los datos, que resume la extrapolación y su sensibilidad.

    Args:
        rangos (pd.DataFrame): Salida de `rangos_covariables`.
        df (pd.DataFrame): Una fila por municipio con MUNICIPIO, ESTADO_EXTRAPOLACION,
            PRED_SINTETICO, PRED_ACOTADA, APORTE_EXTRAPOLADO_PP, COVARIABLE_PRINCIPAL,
            AMPLITUD_SIN_DOMINIO_PP.
        por_dominio (pd.DataFrame): Segunda salida de `sensibilidad_quitar_dominio`.
        max_directa (float, optional): Estimación directa más alta de los dominios.

    Returns:
        str: Párrafos en lenguaje simple, listos para imprimir.

    Casos de uso:
        Interpretación de la celda 10a de `modelo/fay_herriot.py`.
    """
    m = len(df)
    lineas = ["Rango de las covariables (dominios con encuesta frente a municipios):"]
    for r in rangos.itertuples():
        lineas.append(
            f"  • {r.COVARIABLE}: dominios de {r.MIN_DOMINIOS:.4g} ({r.DOMINIO_MIN}) a "
            f"{r.MAX_DOMINIOS:.4g} ({r.DOMINIO_MAX}); municipios de {r.MIN_MUNICIPIOS:.4g} a "
            f"{r.MAX_MUNICIPIOS:.4g}. Fuera del rango: {r.N_DEBAJO} por debajo y "
            f"{r.N_ENCIMA} por encima ({r.PCT_FUERA:.0f} % de {r.N_MUNICIPIOS})."
        )

    conteo = df["ESTADO_EXTRAPOLACION"].value_counts()
    lineas.append(
        f"\nEstado de los {m} municipios: "
        f"{conteo.get(ESTADO_DENTRO, 0)} dentro del rango, "
        f"{conteo.get(ESTADO_FUERA, 0)} fuera del rango de alguna covariable y "
        f"{conteo.get(ESTADO_COMBINACION, 0)} con una combinación de covariables que el modelo "
        f"no vio (cada valor dentro de su rango)."
    )

    ext = df[df["ESTADO_EXTRAPOLACION"] != ESTADO_DENTRO]
    dentro = df[df["ESTADO_EXTRAPOLACION"] == ESTADO_DENTRO]
    if ext.empty:
        lineas.append(
            "Ningún municipio extrapola: todas las predicciones usan valores de covariables "
            "que el modelo observó."
        )
        return "\n".join(lineas)

    top = ext.sort_values("APORTE_EXTRAPOLADO_PP", key=np.abs, ascending=False).head(3)
    ejemplos = "; ".join(
        f"{t.MUNICIPIO}: {t.PRED_SINTETICO:.1f} %, de los cuales {t.APORTE_EXTRAPOLADO_PP:.1f} pp "
        f"vienen de {t.COVARIABLE_PRINCIPAL or 'la combinación'} (acotada: {t.PRED_ACOTADA:.1f} %)"
        for t in top.itertuples()
    )
    lineas.append(
        f"\nParte de la predicción que viene de salirse del rango, en los {len(ext)} municipios "
        f"que extrapolan: mediana {ext['APORTE_EXTRAPOLADO_PP'].abs().median():.1f} pp, máximo "
        f"{ext['APORTE_EXTRAPOLADO_PP'].abs().max():.1f} pp. Mayores: {ejemplos}."
    )
    if max_directa is not None:
        n_sobre = int((ext["PRED_SINTETICO"] > max_directa).sum())
        lineas.append(
            f"{n_sobre} de ellos tienen una predicción mayor que la directa más alta de los "
            f"dominios ({max_directa:.1f} %), un valor que el modelo nunca observó."
        )

    infl = por_dominio.iloc[0]
    texto_dentro = (
        f" frente a {dentro['AMPLITUD_SIN_DOMINIO_PP'].median():.2f} pp en los que están dentro"
        if len(dentro)
        else ""
    )
    lineas.append(
        f"\nAl quitar un dominio a la vez, la predicción de los municipios que extrapolan se "
        f"mueve en una franja de {ext['AMPLITUD_SIN_DOMINIO_PP'].median():.2f} pp (mediana; "
        f"máximo {ext['AMPLITUD_SIN_DOMINIO_PP'].max():.2f} pp){texto_dentro}. El dominio que más "
        f"cambia las predicciones es {infl['DOMINIO_EXCLUIDO']} (cambio medio "
        f"{infl['CAMBIO_MEDIO_PP']:.2f} pp, máximo {infl['CAMBIO_MAX_PP']:.2f} pp)."
    )
    lineas.append(
        "\nLectura: la tasa publicada no cambia, pero en los municipios marcados la predicción "
        "supone que la relación lineal sigue valiendo fuera de lo observado, y su CV no mide ese "
        "riesgo (Morales et al., 2021, p. 441 y 453; Molina, 2019, PDF 40-41)."
    )
    return "\n".join(lineas)
