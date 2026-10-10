"""Diagnósticos del modelo Fay-Herriot.

- **Validación sin GVF.** Las varianzas de muestreo D_d son las varianzas bootstrap de la
  estimación directa, tratadas como conocidas (Morales et al., 2021, p. 427, primera
  alternativa); no se suavizan con una función de varianza generalizada, así que no hay
  figuras de GVF.
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


def explicacion_graficas() -> str:
    """Texto que explica qué observar en las gráficas de validación.

    Returns:
        str: Explicación lista para imprimir antes de `graficar_validacion()`.

    Example:
        >>> print(explicacion_graficas())
    """
    return (
        "Gráfica 1 (Efecto suavizador): compara el residuo del EBLUP (Yd − EBLUP)\n"
        "contra la estimación directa. Como Yd − EBLUP = (1 − γd)(Yd − x'β̂), se espera\n"
        "residuo negativo para Yd pequeños (el EBLUP sube la estimación) y positivo para\n"
        "Yd grandes (el EBLUP la baja). Es una descripción de la contracción hacia el\n"
        "predictor sintético, no una prueba de validez del modelo.\n"
        "Gráfica 2 (Histograma de residuos estandarizados): distribución de\n"
        "(Y − x'β̂)/√(Dd+Â). Bajo el supuesto de normalidad del modelo deben verse\n"
        "aproximadamente normales, centrados en 0 y con desviación ≈ 1; respalda\n"
        "visualmente el test de Shapiro-Wilk.\n"
    )


def interpretar_validacion(modelo: ModeloAreaPequena) -> str:
    """Interpretación cuantitativa de las dos gráficas de validación de un modelo ajustado.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `eblup` y `residuals`.

    Returns:
        str: Interpretación lista para imprimir junto a las figuras.

    Example:
        >>> print(interpretar_validacion(modelo))
    """
    corr, pval = stats.pearsonr(modelo.Y, modelo.Y - modelo.eblup)
    suaviza_ok = corr > 0 and pval < 0.05
    normal_ok = modelo.sw_pval > 0.05
    return (
        "INTERPRETACIÓN:\n"
        f"  Gráfica 1 (Efecto suavizador): corr(Yd, Yd−EBLUP)={corr:.3f} (p={pval:.4f})  "
        + (
            "✓ el EBLUP contrae los extremos hacia el predictor sintético"
            if suaviza_ok
            else "~ contracción débil (γ alto o buen ajuste del sintético)"
        )
        + "\n"
        f"  Gráfica 2 (Residuos estandarizados): media={modelo.residuals.mean():.3f}, "
        f"sd={modelo.residuals.std(ddof=1):.3f}, Shapiro-Wilk p={modelo.sw_pval:.4f}  "
        + ("✓ compatible con normalidad" if normal_ok else "✗ revisar normalidad")
    )


def graficar_validacion(modelo: ModeloAreaPequena) -> list:
    """Construye las dos figuras de validación: efecto suavizador e histograma de residuos.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `resultados` y `residuals`.

    Returns:
        list[matplotlib.figure.Figure]: [efecto suavizador, histograma de residuos], sin
            título.

    Example:
        >>> figs = graficar_validacion(modelo)
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
        >>> fig = figura_cv_directo_vs_eblup(ganador, df["NOMBRE_DOMINIO"].values)
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
        >>> print(interpretar_cv(ganador))
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
        >>> aviso = aviso_encuesta_sin_peso(modelo, 0.01)
        >>> if aviso: print(aviso)
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


def marca_extrapolacion(
    var_beta_nuevos: np.ndarray, modelo: ModeloAreaPequena
) -> np.ndarray:
    """Marca los dominios nuevos cuyas covariables quedan fuera de la nube de la muestra.

    Compara ``x_d'Cov(β̂)x_d`` de cada dominio sin encuesta (el término de la varianza del
    predictor sintético, Morales et al., p. 441) con el máximo de esa misma cantidad entre
    los dominios usados para ajustar el modelo. Si lo supera, la predicción es una
    extrapolación: el modelo no vio ningún dominio tan alejado del centro de los datos.

    Args:
        var_beta_nuevos (np.ndarray): ``x_d'Cov(β̂)x_d`` de cada dominio sin encuesta,
            shape (m,).
        modelo (ModeloAreaPequena): Modelo ajustado con el que se predijo.

    Returns:
        np.ndarray: Arreglo booleano shape (m,), True si el dominio extrapola.

    Example:
        >>> marca_extrapolacion(var_beta, ganador)
    """
    var_beta_muestra = np.einsum("ij,jk,ik->i", modelo.X, modelo.cov_beta, modelo.X)
    return np.asarray(var_beta_nuevos) > var_beta_muestra.max()
