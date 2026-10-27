"""Diagnósticos del modelo Fay-Herriot.

- **Validación sin GVF.** Las varianzas de muestreo D_d son las varianzas bootstrap por
  viviendas de la estimación directa, tratadas como conocidas (Morales et al., 2021, p. 427,
  primera alternativa); no se suavizan con una función de varianza generalizada. La GVF se
  ajusta y evalúa solo como escenario de sensibilidad (`shared/sensibilidad_varianza.py`).
- **Ganancia de precisión.** CV directo frente a CV del EBLUP por dominio, ordenados por D_d,
  como en las figuras de RMSE directo vs EBLUP del libro (Fig. 17.2, Tabla 19.5).
- **Avisos**: encuesta sin peso en el EBLUP (Â ≈ 0), tasas fuera de [0, 100] y extrapolación
  de la predicción sintética.

Las figuras no llevan título: el contexto lo da el notebook que las muestra.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy import stats

from shared.config import CV_ACEPTABLE, CV_CONFIABLE
from shared.extrapolacion import ESTADO_DENTRO, estado_extrapolacion
from shared.modelo_area_pequena import ModeloAreaPequena


def _annotate(ax, xs: np.ndarray, ys: np.ndarray, labels: np.ndarray) -> None:
    """Anota cada punto de un scatter con su etiqueta de dominio.

    Args:
        ax (matplotlib.axes.Axes): Ejes donde dibujar.
        xs (np.ndarray): Coordenadas x de los puntos.
        ys (np.ndarray): Coordenadas y de los puntos.
        labels (np.ndarray): Etiqueta de texto por punto.

    Returns:
        None
    """
    for xi, yi, lab in zip(xs, ys, labels):
        ax.annotate(
            lab,
            (xi, yi),
            textcoords="offset points",
            xytext=(4, 3),
            fontsize=7,
            color="dimgray",
        )


def _graficar_efecto_suavizador(
    ax, Y: np.ndarray, resid_fh: np.ndarray, nombres_dominio: np.ndarray
) -> None:
    """Dibuja el residuo del EBLUP (Yd − EBLUP) contra la estimación directa.

    Args:
        ax (matplotlib.axes.Axes): Ejes donde dibujar.
        Y (np.ndarray): Estimación directa por dominio, shape (n,).
        resid_fh (np.ndarray): Yd − EBLUP por dominio, shape (n,).
        nombres_dominio (np.ndarray): Nombre de cada dominio, para anotar los puntos.

    Returns:
        None
    """
    ax.axhline(0, color="red", linestyle="--", linewidth=1.2, label="Referencia 0")
    colores = ["tomato" if r > 0 else "steelblue" for r in resid_fh]
    ax.scatter(Y, resid_fh, c=colores, edgecolors="white", s=70, alpha=0.85, zorder=3)
    _annotate(ax, Y, resid_fh, nombres_dominio)
    ax.set_xlabel("Estimación directa Yd  (%)", fontsize=10)
    ax.set_ylabel("Residuo FH  (Yd − EBLUP)", fontsize=10)
    leyenda = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="tomato",
            markersize=8,
            label="EBLUP < Yd  (suaviza hacia abajo)",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="steelblue",
            markersize=8,
            label="EBLUP > Yd  (suaviza hacia arriba)",
        ),
    ]
    ax.legend(handles=leyenda, fontsize=8)
    ax.grid(True, linestyle=":", alpha=0.5)


def _graficar_histograma_residuos(ax, residuals: np.ndarray) -> None:
    """Dibuja el histograma de los residuos estandarizados con curva normal de referencia.

    Args:
        ax (matplotlib.axes.Axes): Ejes donde dibujar.
        residuals (np.ndarray): Residuos estandarizados (Y − x'β̂)/√(Dd+Â), shape (n,).

    Returns:
        None
    """
    ax.axvline(0, color="red", linestyle="--", linewidth=1.2, label="Referencia 0")
    ax.hist(
        residuals,
        bins=min(15, max(5, len(residuals) // 3)),
        color="steelblue",
        edgecolor="white",
        alpha=0.85,
        density=True,
        zorder=3,
    )

    xs = np.linspace(residuals.min() - 1, residuals.max() + 1, 200)
    ax.plot(
        xs,
        stats.norm.pdf(xs, 0, 1),
        color="darkorange",
        linewidth=1.8,
        label="N(0,1) referencia",
    )

    ax.set_xlabel("Residuo estandarizado  (Y − ŷ_sintético) / √(Di+Â)", fontsize=10)
    ax.set_ylabel("Densidad", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.5)


# G7-B22 (R-10): cómo leer los diagnósticos de normalidad. Con 23 residuos marginales, que
# mezclan u_d y e_d y no son independientes, Shapiro-Wilk tiene poca potencia: no rechazar no
# demuestra normalidad. La normalidad de u_d y e_d es un supuesto del modelo (Morales et al.,
# 2021, p. 426); el DANE redacta igual la prueba («no hay evidencia estadística suficiente para
# rechazar», nota SAE FIES 2024, PDF 14). Redacción de la revisión del Grupo 7, sec. 5.22.
LECTURA_NORMALIDAD = (
    "los diagnósticos no muestran evidencia fuerte contra la aproximación normal, dentro de "
    "la limitada potencia disponible con 23 áreas"
)
LECTURA_NORMALIDAD_RECHAZA = (
    "Shapiro-Wilk rechaza la normalidad: revisar la aproximación normal de u_d y e_d"
)
# La media de los residuos estandarizados es ≈ 0 por construcción: con intercepto, el GLS cumple
# Σ (y_d − x_d'β̂)/(ψ_d + Â) = 0. No informa sobre el sesgo del predictor.
NOTA_MEDIA_RESIDUOS = (
    "≈ 0 por construcción del GLS con intercepto; no informa sobre sesgo"
)


def lectura_normalidad(sw_pval: float, alfa: float = 0.05) -> str:
    """Lectura del p-valor de Shapiro-Wilk sin afirmar normalidad (G7-B22, R-10).

    Args:
        sw_pval (float): p-valor de Shapiro-Wilk de los residuos estandarizados.
        alfa (float): Nivel de la prueba.

    Returns:
        str: `LECTURA_NORMALIDAD` si no se rechaza; `LECTURA_NORMALIDAD_RECHAZA` si se rechaza.

    Example:
        >>> lectura_normalidad(0.31).startswith("los diagnósticos no muestran")
        True
        >>> lectura_normalidad(0.01).startswith("Shapiro-Wilk rechaza")
        True

    Casos de uso:
        Diagnósticos por especificación en `fay_herriot.py` e `interpretar_validacion`.
    """
    return LECTURA_NORMALIDAD if sw_pval > alfa else LECTURA_NORMALIDAD_RECHAZA


def explicacion_graficas() -> str:
    """Texto que explica qué observar en las gráficas de validación.

    Returns:
        str: Explicación lista para imprimir antes de `graficar_validacion()`.

    Example:
        >>> print(explicacion_graficas())  # doctest: +SKIP
    """
    return (
        "Gráfica 1 (Efecto suavizador): compara el residuo del EBLUP (Yd − EBLUP)\n"
        "contra la estimación directa. Como Yd − EBLUP = (1 − γd)(Yd − x'β̂), se espera\n"
        "residuo negativo para Yd pequeños (el EBLUP sube la estimación) y positivo para\n"
        "Yd grandes (el EBLUP la baja). Es una descripción de la contracción hacia el\n"
        "predictor sintético, no una prueba de validez del modelo.\n"
        "Gráfica 2 (Histograma de residuos estandarizados): distribución de\n"
        "(Y − x'β̂)/√(Dd+Â). Bajo el supuesto de normalidad del modelo se verían\n"
        "aproximadamente normales y con desviación ≈ 1; la media es ≈ 0 por construcción\n"
        "del GLS con intercepto. Con 23 residuos marginales (mezclan u_d y e_d) ni el\n"
        "histograma ni Shapiro-Wilk pueden demostrar normalidad: solo mostrar si hay\n"
        "evidencia fuerte en contra.\n"
    )


def interpretar_validacion(modelo: ModeloAreaPequena) -> str:
    """Interpretación cuantitativa de las dos gráficas de validación de un modelo ajustado.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `eblup` y `residuals`.

    Returns:
        str: Interpretación lista para imprimir junto a las figuras.

    Example:
        >>> print(interpretar_validacion(modelo))  # doctest: +SKIP
    """
    corr, pval = stats.pearsonr(modelo.Y, modelo.Y - modelo.eblup)
    suaviza_ok = corr > 0 and pval < 0.05
    return (
        "INTERPRETACIÓN:\n"
        f"  Gráfica 1 (Efecto suavizador): corr(Yd, Yd−EBLUP)={corr:.3f} (p={pval:.4f})  "
        + (
            "✓ el EBLUP contrae los extremos hacia el predictor sintético"
            if suaviza_ok
            else "~ contracción débil (γ alto o buen ajuste del sintético)"
        )
        + "\n"
        f"  Gráfica 2 (Residuos estandarizados): media={modelo.residuals.mean():.3f} "
        f"({NOTA_MEDIA_RESIDUOS}), sd={modelo.residuals.std(ddof=1):.3f}, "
        f"Shapiro-Wilk p={modelo.sw_pval:.4f}: {lectura_normalidad(modelo.sw_pval)}"
    )


def graficar_validacion(modelo: ModeloAreaPequena) -> list:
    """Construye las dos figuras de validación: efecto suavizador e histograma de residuos.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `resultados` y `residuals`.

    Returns:
        list[matplotlib.figure.Figure]: [efecto suavizador, histograma de residuos], sin
            título.

    Example:
        >>> figs = graficar_validacion(modelo)  # doctest: +SKIP
    """
    nombres_dominio = modelo.resultados["NOMBRE_DOMINIO"].values
    paneles = [
        (
            _graficar_efecto_suavizador,
            (modelo.Y, modelo.Y - modelo.eblup, nombres_dominio),
        ),
        (_graficar_histograma_residuos, (modelo.residuals,)),
    ]
    figuras = []
    for funcion_graficado, args in paneles:
        fig, ax = plt.subplots(figsize=(8, 6.5))
        funcion_graficado(ax, *args)
        plt.tight_layout()
        figuras.append(fig)
    return figuras


def figura_cv_directo_vs_eblup(modelo: ModeloAreaPequena, nombres_dominio: np.ndarray):
    """CV de la estimación directa frente al CV del EBLUP, dominios ordenados por D_d.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `resultados` (contiene
            `CV_PORCENTAJE` y `CV_EBLUP_PCT`).
        nombres_dominio (np.ndarray): Nombre de cada dominio, en el orden de las filas del modelo.

    Returns:
        matplotlib.figure.Figure: Puntos del CV directo y del CV EBLUP por dominio, unidos
            por un segmento, de menor a mayor varianza directa, con las líneas de los
            umbrales de confiabilidad.

    Example:
        >>> fig = figura_cv_directo_vs_eblup(ganador, df["NOMBRE_DOMINIO"].values)  # doctest: +SKIP
    """
    orden = np.argsort(modelo.Di)
    cv_dir = modelo.resultados["CV_PORCENTAJE"].values[orden]
    cv_eb = modelo.resultados["CV_EBLUP_PCT"].values[orden]
    x = np.arange(modelo.n)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.vlines(x, cv_eb, cv_dir, color="lightgray", linewidth=2, zorder=1)
    ax.scatter(x, cv_dir, color="dimgray", s=45, label="CV directo", zorder=3)
    ax.scatter(x, cv_eb, color="steelblue", s=45, label="CV EBLUP", zorder=3)
    ax.axhline(CV_CONFIABLE, color="seagreen", linestyle="--", linewidth=1)
    ax.axhline(CV_ACEPTABLE, color="darkorange", linestyle="--", linewidth=1)
    ax.text(x[-1] + 0.4, CV_CONFIABLE, f"{CV_CONFIABLE}%", va="center", fontsize=8)
    ax.text(x[-1] + 0.4, CV_ACEPTABLE, f"{CV_ACEPTABLE}%", va="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(nombres_dominio[orden], rotation=60, ha="right", fontsize=7)
    ax.set_xlabel("Dominios, de menor a mayor varianza directa Dd", fontsize=10)
    ax.set_ylabel("Coeficiente de variación (%)", fontsize=10)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    plt.tight_layout()
    return fig


def interpretar_cv(modelo: ModeloAreaPequena) -> str:
    """Lectura de la ganancia de precisión del EBLUP frente a la estimación directa.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `resultados`.

    Returns:
        str: Interpretación lista para imprimir junto a `figura_cv_directo_vs_eblup`.

    Example:
        >>> print(interpretar_cv(ganador))  # doctest: +SKIP
    """
    res = modelo.resultados
    orden = np.argsort(modelo.Di)
    tercio = max(1, modelo.n // 3)
    mejora = res["MEJORA_CV_PCT"].values
    mejora_baja = mejora[orden[:tercio]].mean()
    mejora_alta = mejora[orden[-tercio:]].mean()
    confiables_dir = int((res["CV_PORCENTAJE"] < CV_CONFIABLE).sum())
    confiables_eb = int((res["CV_EBLUP_PCT"] < CV_CONFIABLE).sum())
    return (
        "INTERPRETACIÓN (ganancia de precisión del modelo elegido):\n"
        f"  Reducción media del CV en el tercio de menor Dd: {mejora_baja:.2f} pp; "
        f"en el tercio de mayor Dd: {mejora_alta:.2f} pp.\n"
        f"  Dominios con CV < {CV_CONFIABLE}%: {confiables_dir} con la estimación directa, "
        f"{confiables_eb} con el EBLUP (de {modelo.n}).\n"
        "  Lectura: la ganancia se concentra donde la varianza directa es grande; donde la "
        "muestra es grande el MSE del EBLUP tiende a Dd y el EBLUP casi coincide con la "
        "estimación directa (Morales et al., p. 440). Que MSE_EBLUP < Dd es lo esperado por "
        "construcción (g1 = γd·Dd < Dd), no una validación independiente del modelo."
    )


def aviso_encuesta_sin_peso(modelo: ModeloAreaPequena, umbral_gamma: float) -> str:
    """Devuelve un aviso si la encuesta prácticamente no pesa en el EBLUP (Â ≈ 0).

    Si Â es casi cero, γ_d = Â/(Â + D_d) ≈ 0 en todos los dominios y el EBLUP coincide con
    el predictor sintético x'β̂: la estimación directa no influye en el resultado.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `gamma_i` y `A_hat`.
        umbral_gamma (float): Valor de γ por debajo del cual se considera que la encuesta
            no pesa (se compara con el γ máximo entre dominios).

    Returns:
        str: Texto del aviso, o cadena vacía si el γ máximo supera el umbral.

    Example:
        >>> aviso = aviso_encuesta_sin_peso(modelo, 0.01)  # doctest: +SKIP
        >>> if aviso: print(aviso)  # doctest: +SKIP
    """
    gamma_max = float(np.max(modelo.gamma_i))
    if gamma_max >= umbral_gamma:
        return ""
    return (
        f"⚠ AVISO: Â = {modelo.A_hat:.2e} y γ máximo = {gamma_max:.4f} < {umbral_gamma}: "
        "la estimación directa no pesa en el EBLUP, que coincide con el predictor "
        "sintético x'β̂. Reportarlo: el modelo no detecta variación entre dominios más "
        "allá del error de muestreo."
    )


def marca_fuera_de_rango(
    valores: np.ndarray, minimo: float, maximo: float
) -> np.ndarray:
    """Marca los valores fuera del rango admisible de una tasa.

    Args:
        valores (np.ndarray): Tasas estimadas (EBLUP o sintéticas), en %.
        minimo (float): Valor mínimo admisible (0 para una tasa).
        maximo (float): Valor máximo admisible (100 para una tasa en %).

    Returns:
        np.ndarray: Arreglo booleano, True donde el valor está fuera de [minimo, maximo].

    Example:
        >>> marca_fuera_de_rango(np.array([-1.0, 12.5]), 0.0, 100.0)
        array([ True, False])
    """
    valores = np.asarray(valores, dtype=float)
    return (valores < minimo) | (valores > maximo)


def marca_extrapolacion(X_nuevos: np.ndarray, modelo: ModeloAreaPequena) -> np.ndarray:
    """Marca los municipios cuya predicción sintética es una extrapolación (B20).

    Usa el criterio de `shared/extrapolacion.estado_extrapolacion`: extrapola si alguna
    covariable queda fuera del rango [mín, máx] de los dominios de ajuste o si, con todas
    dentro, ``x_m'Cov(β̂)x_m`` (el término de la varianza del predictor sintético, Morales et
    al., p. 441) supera el máximo de esa cantidad en los dominios. El umbral no es de Morales:
    es el criterio de extrapolación oculta de Montgomery, Peck y Vining (sec. 3.8) (R-66).

    Args:
        X_nuevos (np.ndarray): Matriz de diseño de los municipios (m, p), con intercepto.
        modelo (ModeloAreaPequena): Modelo ajustado con el que se predijo.

    Returns:
        np.ndarray: Arreglo booleano shape (m,), True si el municipio extrapola.

    Example:
        >>> marca_extrapolacion(X_new, ganador)  # doctest: +SKIP
    """
    estado = estado_extrapolacion(
        modelo.X, X_nuevos, modelo.cov_beta, modelo.beta_hat, list(modelo.covars)
    )
    return (estado["ESTADO_EXTRAPOLACION"] != ESTADO_DENTRO).to_numpy()
