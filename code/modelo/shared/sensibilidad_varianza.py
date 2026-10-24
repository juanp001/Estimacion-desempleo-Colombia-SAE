"""Sensibilidad del modelo Fay-Herriot a la varianza de muestreo ψ_d y función de varianza generalizada (G7-B3).

El Fay-Herriot trata ψ_d (D_i en el código) como conocida (Morales et al., 2021, p. 427). Aquí
ψ_d es el bootstrap por viviendas dentro del dominio (`preprocesamiento/shared/bootstrap.py`), que
no reproduce el estrato interno ni el segmento de la GEIH. No se sabe si la varianza del diseño es
mayor o menor que ψ_d, así que este módulo mide cuánto cambian las conclusiones si ψ_d se equivoca.

Escenarios:

- **Alternativas medidas**: bootstrap por personas, Taylor con viviendas como conglomerado.
- **GVF** (función de varianza generalizada), dos formas ajustadas sobre la ψ_d base:
  A) ``log ψ = b0 + b1·y + b2·n`` (Morales et al., p. 427, ec. 16.6; ejemplo p. 454-455);
  B) ``log ψ = b0 + b1·log(p(1−p)) + b2·log n``, la forma del efecto de diseño
  ψ ≈ deff·p(1−p)/n (Téllez, 2020, p. 15; Chile pobreza 2016, PDF 4).
  La ψ suavizada se retransforma con el factor Δ = Σψ/Σexp(x'α̂), que conserva la media de las ψ
  (INE Chile, ENUSC 2018, PDF 15-16, Rivest y Belmonte); se reporta también la corrección
  lognormal exp(σ̂²/2) de Morales (p. 427/455). La GVF es solo un escenario: sirve para estabilizar
  ψ̂ inestables por muestras pequeñas (ENUSC, PDF 15; Molina, 2019, PDF 19), y aquí cada dominio
  tiene miles de viviendas.
- **Grilla multiplicativa** ψ_d × k con k ∈ {1/3, 1/2, 2/3, 1, 3/2, 2, 3}: simétrica en escala
  log, porque no se presume la dirección del error.

En cada escenario se reajustan todas las variantes (conjunto del EDA y dejar-una-fuera), se elige
el ganador con la misma regla del modelo (Morales, p. 453) y se comparan con el escenario base: el
ganador, Â frente a ψ̄ (Benedetti et al., 2024, p. 143: subestimar ψ pesa más cuando Â es pequeña
frente a ψ), γ, coeficientes y su significancia, EBLUP, CV y confiabilidad, λ₁ del benchmarking y
la predicción sintética de los municipios.

Las figuras no llevan título: el contexto lo da el notebook que las muestra.
"""

import contextlib
import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from shared.benchmarking import factor_razon, promedio_ponderado
from shared.consolidacion import clasificar_confiabilidad
from shared.diagnosticos import marca_extrapolacion
from shared.fay_herriot import FayHerriotClasico
from shared.modelo_area_pequena import prediccion_sintetica
from shared.seleccion_modelo import elegir_ganador, todas_significativas

# Factores multiplicativos de ψ_d, simétricos en escala log alrededor de 1.
FACTORES_PSI = [1 / 3, 1 / 2, 2 / 3, 1.0, 3 / 2, 2.0, 3.0]
# Columna con la que se pasa √ψ al modelo en cada escenario.
SE_ESCENARIO = "SE_ESCENARIO_PCT"
ESCENARIO_BASE = "BASE (bootstrap viviendas)"


def ajustar_gvf(psi, tasa_pct, n, forma: str) -> dict:
    """Ajusta por mínimos cuadrados una función de varianza generalizada sobre log ψ.

    Formas:
        - ``"A"``: log ψ = b0 + b1·y + b2·n (Morales et al., p. 427, ec. 16.6), con y la tasa en %.
        - ``"B"``: log ψ = b0 + b1·log(p(1−p)) + b2·log n, con p = y/100 (efecto de diseño).

    Args:
        psi (array-like): Varianza directa de cada dominio (en %²), shape (D,).
        tasa_pct (array-like): Tasa directa de cada dominio en %, shape (D,).
        n (array-like): Tamaño de muestra de cada dominio (personas de la PEA), shape (D,).
        forma (str): ``"A"`` o ``"B"``.

    Returns:
        dict: ``forma``, ``variables`` (nombres), ``coef``, ``se``, ``p_valor`` (prueba t),
            ``r2``, ``r2_ajustado``, ``sigma2`` (varianza residual), ``ajustado`` (log ψ
            predicho), ``residuos``, ``delta`` (factor Δ), ``psi_delta`` (exp(x'α̂)·Δ) y
            ``psi_lognormal`` (exp(x'α̂)·exp(σ̂²/2)).

    Raises:
        ValueError: Si la forma no es ``"A"`` ni ``"B"`` o hay menos dominios que parámetros + 1.

    Casos de uso:
        Suavizar ψ_d como escenario de sensibilidad y evaluar qué tan bien la explica el tamaño
        de muestra y la tasa.

    Example:
        >>> y = np.array([8.0, 10.0, 12.0, 15.0, 9.0]); n = np.array([9e3, 12e3, 15e3, 2e4, 1e4])
        >>> psi = np.exp(-1.0 + 0.1 * y - 5e-5 * n)
        >>> g = ajustar_gvf(psi, y, n, "A")
        >>> np.round(g["coef"], 6).tolist(), round(g["r2"], 6), round(g["delta"], 6)
        ([-1.0, 0.1, -5e-05], 1.0, 1.0)
    """
    psi = np.asarray(psi, dtype=float)
    y = np.asarray(tasa_pct, dtype=float)
    n = np.asarray(n, dtype=float)
    if forma == "A":
        variables = ["Intercepto", "TASA_PCT", "N_PEA"]
        X = np.column_stack([np.ones_like(y), y, n])
    elif forma == "B":
        p = y / 100
        variables = ["Intercepto", "LOG_P_1MENOSP", "LOG_N_PEA"]
        X = np.column_stack([np.ones_like(y), np.log(p * (1 - p)), np.log(n)])
    else:
        raise ValueError(f"Forma de GVF desconocida: {forma!r} (use 'A' o 'B')")
    d, k = X.shape
    if d <= k:
        raise ValueError(f"Se necesitan más de {k} dominios para ajustar la GVF")

    log_psi = np.log(psi)
    coef, *_ = np.linalg.lstsq(X, log_psi, rcond=None)
    ajustado = X @ coef
    residuos = log_psi - ajustado
    ssr = float(residuos @ residuos)
    sst = float(((log_psi - log_psi.mean()) ** 2).sum())
    sigma2 = ssr / (d - k)
    cov = sigma2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(se > 0, coef / se, np.inf)
    p_valor = 2 * stats.t.sf(np.abs(t), df=d - k)
    r2 = 1 - ssr / sst if sst > 0 else 1.0
    base = np.exp(ajustado)
    delta = float(psi.sum() / base.sum())
    return {
        "forma": forma,
        "variables": variables,
        "coef": coef,
        "se": se,
        "p_valor": p_valor,
        "r2": float(r2),
        "r2_ajustado": float(1 - (1 - r2) * (d - 1) / (d - k)),
        "sigma2": float(sigma2),
        "ajustado": ajustado,
        "residuos": residuos,
        "delta": delta,
        "psi_delta": base * delta,
        "psi_lognormal": base * np.exp(sigma2 / 2),
    }


def tabla_gvf(ajustes: list) -> pd.DataFrame:
    """Coeficientes y bondad de ajuste de una o más GVF.

    Args:
        ajustes (list[dict]): Salidas de `ajustar_gvf`.

    Returns:
        pd.DataFrame: Una fila por forma y parámetro con ``FORMA``, ``PARAMETRO``, ``COEF``,
            ``SE``, ``P_VALOR``, ``R2``, ``R2_AJUSTADO``, ``SIGMA2`` y ``DELTA``.

    Casos de uso:
        Tabla `tesis.modelo.gvf_ajuste` y su lectura en el notebook.
    """
    filas = []
    for g in ajustes:
        for nombre, c, s, p in zip(g["variables"], g["coef"], g["se"], g["p_valor"]):
            filas.append(
                {
                    "FORMA": g["forma"],
                    "PARAMETRO": nombre,
                    "COEF": float(c),
                    "SE": float(s),
                    "P_VALOR": float(p),
                    "R2": g["r2"],
                    "R2_AJUSTADO": g["r2_ajustado"],
                    "SIGMA2": g["sigma2"],
                    "DELTA": g["delta"],
                }
            )
    return pd.DataFrame(filas)


def figura_gvf(psi, ajustes: list, nombres_dominio):
    """Varianza observada vs. predicha por la GVF y residuos (como Morales et al., Fig. 16.1).

    Args:
        psi (array-like): ψ_d observada (en %²), shape (D,).
        ajustes (list[dict]): Salidas de `ajustar_gvf` (una por forma).
        nombres_dominio (array-like): Nombres de los dominios, para rotular los residuos grandes.

    Returns:
        matplotlib.figure.Figure: Izquierda, ψ predicha (Δ) contra la observada con la recta
            y = x; derecha, residuos de log ψ contra el valor ajustado.

    Casos de uso:
        Evaluar a la vista si la GVF reproduce la ψ de cada dominio.
    """
    psi = np.asarray(psi, dtype=float)
    nombres = np.asarray(nombres_dominio)
    colores = ["#1f77b4", "#d62728", "#2ca02c"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8))
    lim = [psi.min() * 0.85, psi.max() * 1.15]
    ax1.plot(lim, lim, color="gray", lw=1, ls="--")
    for g, c in zip(ajustes, colores):
        ax1.scatter(psi, g["psi_delta"], s=22, color=c, label=f"GVF {g['forma']}")
        ax2.scatter(
            g["ajustado"], g["residuos"], s=22, color=c, label=f"GVF {g['forma']}"
        )
        umbral = 2 * np.sqrt(g["sigma2"])
        for i in np.where(np.abs(g["residuos"]) > umbral)[0]:
            ax2.annotate(nombres[i], (g["ajustado"][i], g["residuos"][i]), fontsize=7)
    ax1.set_xlabel("ψ observada (bootstrap por viviendas, %²)")
    ax1.set_ylabel("ψ predicha por la GVF (%²)")
    ax1.legend(frameon=False)
    ax2.axhline(0, color="gray", lw=1, ls="--")
    ax2.set_xlabel("log ψ ajustado")
    ax2.set_ylabel("Residuo de log ψ")
    ax2.legend(frameon=False)
    fig.tight_layout()
    return fig


def escenarios_psi(psi_base, alternativas: dict, factores=FACTORES_PSI) -> dict:
    """Arma el diccionario escenario → ψ_d.

    Args:
        psi_base (array-like): ψ_d base (bootstrap por viviendas), shape (D,).
        alternativas (dict[str, array-like]): Otras ψ_d medidas o suavizadas, mismo orden.
        factores (list[float]): Multiplicadores de la grilla; el 1 se omite (es la base).

    Returns:
        dict[str, np.ndarray]: Base primero, luego las alternativas y la grilla ``ψ × k``.

    Casos de uso:
        Entrada de `ajustar_escenarios`.

    Example:
        >>> list(escenarios_psi([1.0, 2.0], {"GVF A": [1.5, 1.5]}, [0.5, 1.0, 2.0]))
        ['BASE (bootstrap viviendas)', 'GVF A', 'ψ × 0.5', 'ψ × 2']
    """
    psi_base = np.asarray(psi_base, dtype=float)
    salida = {ESCENARIO_BASE: psi_base}
    for nombre, psi in alternativas.items():
        salida[nombre] = np.asarray(psi, dtype=float)
    for k in factores:
        if not np.isclose(k, 1.0):
            salida[f"ψ × {k:.3g}"] = psi_base * k
    return salida


def _ajustar_silencioso(
    df: pd.DataFrame, nombres_covars: list, y_col: str, delta_aic, alfa
):
    """Ajusta todas las variantes y elige el ganador sin imprimir.

    Args:
        df (pd.DataFrame): Dominios con `y_col`, `SE_ESCENARIO` y las covariables.
        nombres_covars (list[list[str]]): Covariables de cada variante.
        y_col (str): Variable respuesta.
        delta_aic (float): ΔAIC de equivalencia.
        alfa (float): Nivel de significancia de la regla del ganador.

    Returns:
        tuple: (modelos ajustados, modelo ganador).
    """
    modelos = [FayHerriotClasico(c, df, y_col, SE_ESCENARIO) for c in nombres_covars]
    for m in modelos:
        m.ajustar()
    with contextlib.redirect_stdout(io.StringIO()):
        ganador = (
            elegir_ganador(modelos, nombres_covars, delta_aic=delta_aic, alfa=alfa)
            if len(modelos) > 1
            else modelos[0]
        )
    return modelos, ganador


def ajustar_escenarios(
    df: pd.DataFrame,
    escenarios: dict,
    nombres_covars: list,
    covars_referencia: list,
    y_col: str,
    pesos_nivel1,
    X_municipios: np.ndarray,
    delta_aic: float,
    alfa: float,
) -> tuple:
    """Reajusta el Fay-Herriot con cada ψ_d y resume los cambios frente al escenario base.

    En cada escenario se reajustan todas las variantes y se aplica la regla del ganador. Para
    que los escenarios sean comparables, los coeficientes, EBLUP, CV, λ₁ y la predicción
    sintética se calculan siempre con la **especificación de referencia** (el ganador del modelo
    con la ψ base); el ganador de cada escenario se reporta aparte.

    Args:
        df (pd.DataFrame): Dominios (una fila por dominio) con `y_col`, las covariables,
            `CODIGO_DOMINIO` y `NOMBRE_DOMINIO`.
        escenarios (dict[str, np.ndarray]): Salida de `escenarios_psi` (ψ en %², mismo orden
            que `df`). La primera entrada es la base.
        nombres_covars (list[list[str]]): Variantes a comparar (conjunto del EDA y dejar-una-fuera).
        covars_referencia (list[str]): Covariables del ganador base.
        y_col (str): Variable respuesta (tasa en %).
        pesos_nivel1 (array-like): PEA expandida de cada dominio (benchmarking de nivel 1).
        X_municipios (np.ndarray): Matriz de diseño (con intercepto) de los municipios sin
            estimación directa propia, con las columnas de `covars_referencia`.
        delta_aic (float): ΔAIC de equivalencia (`DELTA_AIC_EQUIVALENTE`).
        alfa (float): Nivel de significancia (`ALFA_SIGNIFICANCIA`).

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
            - resumen: una fila por escenario.
            - coeficientes: escenario × parámetro de la especificación de referencia.
            - dominios: escenario × dominio (ψ, γ, EBLUP, CV y confiabilidad).
            - municipios: escenario × municipio (predicción sintética, CV y extrapolación).

    Casos de uso:
        Notebook `modelo/sensibilidad_varianza.py`.
    """
    y = df[y_col].to_numpy(dtype=float)
    pesos = np.asarray(pesos_nivel1, dtype=float)
    referencia_n1 = promedio_ponderado(y, pesos)
    resumen, coeficientes, dominios, municipios = [], [], [], []
    base = None

    for nombre, psi in escenarios.items():
        datos = df.copy()
        datos[SE_ESCENARIO] = np.sqrt(psi)
        _, ganador = _ajustar_silencioso(datos, nombres_covars, y_col, delta_aic, alfa)
        ref = FayHerriotClasico(covars_referencia, datos, y_col, SE_ESCENARIO)
        ref.ajustar()

        lambda_n1 = factor_razon(ref.eblup, pesos, referencia_n1)
        pred_mun, _, cv_mun = prediccion_sintetica(
            X_municipios, ref.beta_hat, ref.cov_beta, ref.A_hat
        )
        extrapola = marca_extrapolacion(X_municipios, ref)
        confiab = [clasificar_confiabilidad(c) for c in ref.cv]

        if base is None:
            base = {
                "eblup": ref.eblup,
                "pred": pred_mun,
                "beta": ref.beta_hat,
                "signif": ref.p_vals[1:] < alfa,
                "ganador": tuple(ganador.covars),
                "confiab": confiab,
            }

        resumen.append(
            {
                "ESCENARIO": nombre,
                "PSI_MEDIA": float(np.mean(psi)),
                "PSI_MIN": float(np.min(psi)),
                "PSI_MAX": float(np.max(psi)),
                "A_HAT": float(ref.A_hat),
                "RAZON_A_PSI": float(ref.A_hat / np.mean(psi)),
                "GAMMA_MEDIA": float(ref.gamma_i.mean()),
                "GAMMA_MIN": float(ref.gamma_i.min()),
                "GAMMA_MAX": float(ref.gamma_i.max()),
                "GANADOR": " + ".join(ganador.covars),
                "MISMO_GANADOR": tuple(ganador.covars) == base["ganador"],
                "REF_TODAS_SIGNIF": todas_significativas(ref, alfa),
                "REF_MISMOS_SIGNOS": bool(
                    np.all(np.sign(ref.beta_hat) == np.sign(base["beta"]))
                ),
                "REF_MISMA_SIGNIF": bool(
                    np.all((ref.p_vals[1:] < alfa) == base["signif"])
                ),
                "REF_AIC": float(ref.aic),
                "MAX_DIF_EBLUP_PP": float(np.max(np.abs(ref.eblup - base["eblup"]))),
                "MEDIA_DIF_EBLUP_PP": float(np.mean(np.abs(ref.eblup - base["eblup"]))),
                "CV_EBLUP_MEDIANO": float(np.median(ref.cv)),
                "CV_EBLUP_MAX": float(np.max(ref.cv)),
                "N_CONFIABLE": confiab.count("Confiable"),
                "N_ACEPTABLE": confiab.count("Aceptable"),
                "N_NO_CONFIABLE": confiab.count("No confiable"),
                "N_CAMBIA_CONFIABILIDAD": int(
                    sum(a != b for a, b in zip(confiab, base["confiab"]))
                ),
                "LAMBDA_N1": float(lambda_n1),
                "MAX_DIF_SINTETICO_PP": float(np.max(np.abs(pred_mun - base["pred"]))),
                "CV_SINTETICO_MEDIANO": float(np.median(cv_mun)),
                "N_EXTRAPOLA": int(extrapola.sum()),
            }
        )
        for nombre_par, b, s, p in zip(
            ["Intercepto"] + list(covars_referencia),
            ref.beta_hat,
            ref.se_beta,
            ref.p_vals,
        ):
            coeficientes.append(
                {
                    "ESCENARIO": nombre,
                    "PARAMETRO": nombre_par,
                    "COEF": float(b),
                    "SE": float(s),
                    "P_VALOR": float(p),
                }
            )
        dominios.append(
            pd.DataFrame(
                {
                    "ESCENARIO": nombre,
                    "CODIGO_DOMINIO": df["CODIGO_DOMINIO"].to_numpy(),
                    "NOMBRE_DOMINIO": df["NOMBRE_DOMINIO"].to_numpy(),
                    "TASA_DIRECTA_PCT": y,
                    "PSI": psi,
                    "GAMMA": ref.gamma_i,
                    "EBLUP": ref.eblup,
                    "DIF_EBLUP_BASE_PP": ref.eblup - base["eblup"],
                    "CV_EBLUP_PCT": ref.cv,
                    "CONFIABILIDAD": confiab,
                }
            )
        )
        municipios.append(
            pd.DataFrame(
                {
                    "ESCENARIO": nombre,
                    "FILA_MUNICIPIO": np.arange(len(pred_mun)),
                    "PRED_SINTETICO": pred_mun,
                    "DIF_SINTETICO_BASE_PP": pred_mun - base["pred"],
                    "CV_SINTETICO_PCT": cv_mun,
                    "EXTRAPOLA": extrapola,
                }
            )
        )

    return (
        pd.DataFrame(resumen),
        pd.DataFrame(coeficientes),
        pd.concat(dominios, ignore_index=True),
        pd.concat(municipios, ignore_index=True),
    )


def figura_escenarios(dominios: pd.DataFrame, escenarios_mostrar: list):
    """Cambio del EBLUP frente a la base, por dominio y escenario.

    Args:
        dominios (pd.DataFrame): Tabla escenario × dominio de `ajustar_escenarios`.
        escenarios_mostrar (list[str]): Escenarios a dibujar (sin la base).

    Returns:
        matplotlib.figure.Figure: Una columna por dominio (ordenados por ψ base); cada punto es
            EBLUP(escenario) − EBLUP(base) en puntos porcentuales.

    Casos de uso:
        Ver si algún dominio es sensible a ψ (los de γ más bajo, es decir, ψ más alta).
    """
    base = dominios[dominios["ESCENARIO"] == dominios["ESCENARIO"].iloc[0]]
    orden = base.sort_values("PSI")["NOMBRE_DOMINIO"].tolist()
    posicion = {n: i for i, n in enumerate(orden)}
    cmap = plt.get_cmap("tab10")
    fig, ax = plt.subplots(figsize=(13, 4.8))
    ax.axhline(0, color="gray", lw=1, ls="--")
    for k, esc in enumerate(escenarios_mostrar):
        g = dominios[dominios["ESCENARIO"] == esc]
        x = (
            g["NOMBRE_DOMINIO"].map(posicion).to_numpy()
            + (k - len(escenarios_mostrar) / 2) * 0.06
        )
        ax.scatter(x, g["DIF_EBLUP_BASE_PP"], s=16, color=cmap(k % 10), label=esc)
    ax.set_xticks(range(len(orden)))
    ax.set_xticklabels(orden, rotation=60, ha="right", fontsize=8)
    ax.set_ylabel("EBLUP − EBLUP base (pp)")
    ax.set_xlabel("Dominios, de menor a mayor ψ base")
    ax.legend(frameon=False, fontsize=8, ncol=3)
    fig.tight_layout()
    return fig


def interpretar_sensibilidad(resumen: pd.DataFrame) -> str:
    """Lectura de la tabla resumen calculada desde los datos.

    Args:
        resumen (pd.DataFrame): Primera salida de `ajustar_escenarios`.

    Returns:
        str: Texto con el rango de Â/ψ̄ y de γ, si cambian el ganador, los signos, la
            significancia y la confiabilidad, y el mayor cambio en EBLUP y en la predicción
            sintética.

    Casos de uso:
        Celda final del notebook de sensibilidad.
    """
    base = resumen.iloc[0]
    otros = resumen.iloc[1:]
    lineas = [
        f"Base: Â = {base['A_HAT']:.4f}, ψ̄ = {base['PSI_MEDIA']:.4f} "
        f"(Â/ψ̄ = {base['RAZON_A_PSI']:.1f}); γ entre {base['GAMMA_MIN']:.3f} y "
        f"{base['GAMMA_MAX']:.3f}.",
        f"En los {len(otros)} escenarios alternativos Â/ψ̄ va de "
        f"{otros['RAZON_A_PSI'].min():.1f} a {otros['RAZON_A_PSI'].max():.1f} y el γ mínimo "
        f"de {otros['GAMMA_MIN'].min():.3f} a {otros['GAMMA_MIN'].max():.3f}.",
    ]
    cambia_ganador = otros.loc[~otros["MISMO_GANADOR"], "ESCENARIO"].tolist()
    lineas.append(
        "El modelo ganador es el mismo en todos los escenarios."
        if not cambia_ganador
        else f"El ganador cambia en: {', '.join(cambia_ganador)}."
    )
    signos = otros.loc[~otros["REF_MISMOS_SIGNOS"], "ESCENARIO"].tolist()
    signif = otros.loc[~otros["REF_MISMA_SIGNIF"], "ESCENARIO"].tolist()
    lineas.append(
        "Los coeficientes de la especificación de referencia conservan el signo"
        + (
            " en todos los escenarios"
            if not signos
            else f" salvo en: {', '.join(signos)}"
        )
        + " y la significancia"
        + (" en todos." if not signif else f" salvo en: {', '.join(signif)}.")
    )
    peor = otros.loc[otros["MAX_DIF_EBLUP_PP"].idxmax()]
    lineas.append(
        f"El mayor cambio de un EBLUP es {peor['MAX_DIF_EBLUP_PP']:.3f} pp "
        f"({peor['ESCENARIO']}); el de una predicción sintética municipal, "
        f"{otros['MAX_DIF_SINTETICO_PP'].max():.3f} pp."
    )
    cambia_conf = otros.loc[otros["N_CAMBIA_CONFIABILIDAD"] > 0, "ESCENARIO"].tolist()
    lineas.append(
        "Ningún dominio cambia de categoría de confiabilidad."
        if not cambia_conf
        else f"Algún dominio cambia de categoría de confiabilidad en: {', '.join(cambia_conf)}."
    )
    return "\n".join(lineas)
