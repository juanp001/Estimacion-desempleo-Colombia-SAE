"""Diagnósticos del modelo Fay-Herriot.

- **Validación sin GVF.** Las varianzas de muestreo D_d son las varianzas bootstrap por
  viviendas de la estimación directa, tratadas como conocidas (Morales et al., 2021, p. 427,
  primera alternativa); no se suavizan con una función de varianza generalizada. La GVF se
  ajusta y evalúa solo como escenario de sensibilidad (`shared/sensibilidad_varianza.py`).
- **Ganancia de precisión.** CV directo frente a CV del EBLUP por dominio, ordenados por D_d,
  como en las figuras de RMSE directo vs EBLUP del libro (Fig. 17.2, Tabla 19.5).
- **Supuestos (D-20).** Además del histograma, el gráfico cuantil-cuantil normal de los
  residuos estandarizados y los residuos frente a los valores ajustados x'β̂ del benchmark.
- **Avisos**: encuesta sin peso en el EBLUP (Â ≈ 0), tasas fuera de [0, 100] y extrapolación
  de la predicción sintética.

Las figuras no llevan título: el contexto lo da el notebook que las muestra.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy import stats

from comun.estilo_figuras import (
    ANCHO_FIGURA,
    AZUL,
    GRIS,
    GRIS_CLARO,
    NARANJA,
    etiquetar_puntos,
)
from shared.config import CV_ACEPTABLE, CV_CONFIABLE
from shared.extrapolacion import ESTADO_DENTRO, estado_extrapolacion
from shared.modelo_area_pequena import ModeloAreaPequena


def _annotate(ax, xs: np.ndarray, ys: np.ndarray, labels: np.ndarray) -> None:
    """Anota cada punto de un scatter con su etiqueta de dominio, sin superponer textos.

    Args:
        ax (matplotlib.axes.Axes): Ejes donde dibujar.
        xs (np.ndarray): Coordenadas x de los puntos.
        ys (np.ndarray): Coordenadas y de los puntos.
        labels (np.ndarray): Etiqueta de texto por punto.

    Returns:
        None

    Uso:
        Auxiliar de `_graficar_efecto_suavizador` y de los gráficos de supuestos; se llama con
        los ejes de un scatter ya dibujado (D-12: `etiquetar_puntos` evita las etiquetas
        encimadas).
    """
    etiquetar_puntos(ax, xs, ys, labels, tamano=8)


def _graficar_efecto_suavizador(
    ax, Y: np.ndarray, resid_fh: np.ndarray, nombres_dominio: np.ndarray
) -> None:
    """Dibuja el residuo del EBLUP (θ̂_d − EBLUP) contra la estimación directa θ̂_d.

    Args:
        ax (matplotlib.axes.Axes): Ejes donde dibujar.
        Y (np.ndarray): Estimación directa por dominio, shape (n,).
        resid_fh (np.ndarray): θ̂_d − EBLUP por dominio, shape (n,).
        nombres_dominio (np.ndarray): Nombre de cada dominio, para anotar los puntos.

    Returns:
        None

    Uso:
        Auxiliar de la figura de validación del modelo; se llama con uno de los ejes de la cuadrícula.
    """
    ax.axhline(0, color=GRIS, linestyle="--", linewidth=1.2)
    colores = [NARANJA if r > 0 else AZUL for r in resid_fh]
    ax.scatter(Y, resid_fh, c=colores, edgecolors="white", s=60, zorder=3)
    ax.set_xlabel(r"Estimación directa $\hat{\theta}_d$ (%)")
    ax.set_ylabel(r"$\hat{\theta}_d$ − EBLUP (puntos porcentuales)")
    leyenda = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=NARANJA,
            markersize=8,
            label=r"EBLUP < $\hat{\theta}_d$ (contrae hacia abajo)",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=AZUL,
            markersize=8,
            label=r"EBLUP > $\hat{\theta}_d$ (contrae hacia arriba)",
        ),
    ]
    ax.legend(handles=leyenda)
    _annotate(ax, Y, resid_fh, nombres_dominio)


def _graficar_histograma_residuos(ax, residuals: np.ndarray) -> None:
    """Dibuja el histograma de los residuos estandarizados con curva normal de referencia.

    Args:
        ax (matplotlib.axes.Axes): Ejes donde dibujar.
        residuals (np.ndarray): Residuos estandarizados (θ̂_d − x'β̂)/√(ψ_d + σ̂²_u), shape (n,).

    Returns:
        None

    Uso:
        Auxiliar de la figura de validación del modelo; se llama con uno de los ejes de la cuadrícula.
    """
    ax.axvline(0, color=GRIS, linestyle="--", linewidth=1.2)
    ax.hist(
        residuals,
        bins=min(15, max(5, len(residuals) // 3)),
        color=AZUL,
        edgecolor="white",
        density=True,
        zorder=3,
    )

    xs = np.linspace(residuals.min() - 1, residuals.max() + 1, 200)
    ax.plot(
        xs,
        stats.norm.pdf(xs, 0, 1),
        color=NARANJA,
        linewidth=1.8,
        label="Densidad N(0, 1)",
    )

    ax.set_xlabel(
        r"Residuo estandarizado $(\hat{\theta}_d - x_d'\hat{\beta})"
        r"/\sqrt{\psi_d + \hat{\sigma}^2_u}$"
    )
    ax.set_ylabel("Densidad")
    ax.legend()


def _graficar_qq(ax, residuals: np.ndarray, nombres_dominio: np.ndarray) -> None:
    """Gráfico cuantil-cuantil normal de los residuos estandarizados (D-20).

    Cada punto es un dominio: en el eje horizontal, el cuantil teórico de la N(0, 1) que le
    corresponde por su posición; en el vertical, su residuo estandarizado. Bajo el supuesto de
    normalidad los puntos siguen la recta y = x; la banda gris es la envolvente puntual del
    95 % de los estadísticos de orden de una muestra normal del mismo tamaño, una guía visual
    (no una prueba) para juzgar desvíos con solo 23 residuos. Se anotan los dominios fuera de
    la banda.

    Args:
        ax (matplotlib.axes.Axes): Ejes donde dibujar.
        residuals (np.ndarray): Residuos estandarizados, shape (n,).
        nombres_dominio (np.ndarray): Nombre de cada dominio, en el orden de `residuals`.

    Returns:
        None

    Uso:
        Auxiliar de `graficar_supuestos`.
    """
    residuals = np.asarray(residuals, dtype=float)
    n = len(residuals)
    orden = np.argsort(residuals)
    probabilidades = (np.arange(1, n + 1) - 0.375) / (n + 0.25)
    teoricos = stats.norm.ppf(probabilidades)
    # Envolvente del 95 % de cada estadístico de orden: cuantiles de una Beta(i, n − i + 1).
    i = np.arange(1, n + 1)
    banda_inf = stats.norm.ppf(stats.beta.ppf(0.025, i, n - i + 1))
    banda_sup = stats.norm.ppf(stats.beta.ppf(0.975, i, n - i + 1))
    ax.fill_between(
        teoricos, banda_inf, banda_sup, color=GRIS_CLARO, label="Banda del 95 %"
    )
    limite = [teoricos.min() - 0.3, teoricos.max() + 0.3]
    ax.plot(limite, limite, color=GRIS, linestyle="--", linewidth=1.2, label="y = x")
    observados = residuals[orden]
    fuera = (observados < banda_inf) | (observados > banda_sup)
    ax.scatter(teoricos[~fuera], observados[~fuera], color=AZUL, s=40, zorder=3)
    if fuera.any():
        ax.scatter(
            teoricos[fuera],
            observados[fuera],
            color=NARANJA,
            s=40,
            zorder=3,
            label="Fuera de la banda",
        )
        _annotate(
            ax,
            teoricos[fuera],
            observados[fuera],
            np.asarray(nombres_dominio)[orden][fuera],
        )
    ax.set_xlabel("Cuantil teórico de la N(0, 1)")
    ax.set_ylabel("Residuo estandarizado")
    ax.legend(loc="upper left")


def _graficar_residuos_ajustados(
    ax, ajustados: np.ndarray, residuals: np.ndarray, nombres_dominio: np.ndarray
) -> None:
    """Residuos estandarizados frente a los valores ajustados x_d'β̂ (D-20).

    Si el modelo de enlace es adecuado, los puntos se reparten alrededor de cero sin forma
    (sin curvatura ni embudo). Las líneas en ±2 marcan los dominios con residuo grande, que se
    anotan.

    Args:
        ax (matplotlib.axes.Axes): Ejes donde dibujar.
        ajustados (np.ndarray): Valor ajustado x_d'β̂ (estimación sintética del dominio), en %.
        residuals (np.ndarray): Residuos estandarizados, shape (n,).
        nombres_dominio (np.ndarray): Nombre de cada dominio.

    Returns:
        None

    Uso:
        Auxiliar de `graficar_supuestos`.
    """
    ajustados = np.asarray(ajustados, dtype=float)
    residuals = np.asarray(residuals, dtype=float)
    ax.axhline(0, color=GRIS, linestyle="--", linewidth=1.2)
    for limite in (-2, 2):
        ax.axhline(limite, color=GRIS, linestyle=":", linewidth=1)
    grandes = np.abs(residuals) > 2
    ax.scatter(ajustados[~grandes], residuals[~grandes], color=AZUL, s=40, zorder=3)
    if grandes.any():
        ax.scatter(
            ajustados[grandes],
            residuals[grandes],
            color=NARANJA,
            s=40,
            zorder=3,
            label="|residuo| > 2",
        )
        _annotate(
            ax,
            ajustados[grandes],
            residuals[grandes],
            np.asarray(nombres_dominio)[grandes],
        )
        ax.legend(loc="upper left")
    ax.set_xlabel(r"Valor ajustado $x_d'\hat{\beta}$ (%)")
    ax.set_ylabel("Residuo estandarizado")


def graficar_supuestos(modelo: ModeloAreaPequena) -> list:
    """Gráficos de supuestos del benchmark: Q-Q normal y residuos frente a ajustados (D-20).

    Con 23 residuos el histograma de siete barras casi no informa; el gráfico cuantil-cuantil
    muestra la forma de la distribución punto por punto y el de residuos frente a ajustados
    revela si queda estructura que el modelo de enlace no recoge. Como Shapiro-Wilk, son
    lecturas de los residuos marginales (mezclan u_d y e_d): no demuestran normalidad.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `residuals`, `mu_hat` y
            `resultados` (columna `NOMBRE_DOMINIO`).

    Returns:
        list[matplotlib.figure.Figure]: [Q-Q normal, residuos frente a ajustados], sin título.

    Example:
        >>> figs = graficar_supuestos(ganador)  # doctest: +SKIP
    """
    nombres = modelo.resultados["NOMBRE_DOMINIO"].values
    figuras = []
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    _graficar_qq(ax, modelo.residuals, nombres)
    plt.tight_layout()
    figuras.append(fig)
    fig, ax = plt.subplots(figsize=(ANCHO_FIGURA, 4.4))
    _graficar_residuos_ajustados(ax, modelo.mu_hat, modelo.residuals, nombres)
    plt.tight_layout()
    figuras.append(fig)
    return figuras


def interpretar_supuestos(modelo: ModeloAreaPequena) -> str:
    """Lectura cuantitativa de los gráficos de supuestos (D-20).

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `residuals` y `mu_hat`.

    Returns:
        str: Cuántos residuos quedan fuera de la banda del 95 % del Q-Q y con |residuo| > 2,
            y la correlación de Spearman entre |residuo| y el valor ajustado (un embudo daría
            una correlación alta).

    Example:
        >>> class _M:
        ...     residuals = np.array([-1.2, 0.3, 0.1, 2.5, -0.4, 0.2])
        ...     mu_hat = np.array([8.0, 9.0, 10.0, 11.0, 12.0, 13.0])
        >>> "1 de 6" in interpretar_supuestos(_M())
        True
    """
    r = np.asarray(modelo.residuals, dtype=float)
    n = len(r)
    i = np.arange(1, n + 1)
    banda_inf = stats.norm.ppf(stats.beta.ppf(0.025, i, n - i + 1))
    banda_sup = stats.norm.ppf(stats.beta.ppf(0.975, i, n - i + 1))
    ordenados = np.sort(r)
    fuera = int(((ordenados < banda_inf) | (ordenados > banda_sup)).sum())
    grandes = int((np.abs(r) > 2).sum())
    rho, p = stats.spearmanr(np.abs(r), modelo.mu_hat)
    return (
        "INTERPRETACIÓN (supuestos, D-20):\n"
        f"  Q-Q normal: {fuera} de {n} residuos fuera de la banda del 95 %.\n"
        f"  Residuos frente a ajustados: {grandes} de {n} con |residuo| > 2; Spearman entre "
        f"|residuo| y x'β̂ = {rho:.3f} (p = {p:.3f}), {'sin' if p >= 0.05 else 'con'} "
        "indicio de que la dispersión cambie con el nivel ajustado.\n"
        "  Lectura: con 23 residuos marginales estos gráficos solo muestran si hay evidencia "
        "fuerte en contra de los supuestos; no los demuestran."
    )


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
        "Gráfica 1 (Efecto suavizador): compara el residuo del EBLUP (θ̂_d − EBLUP)\n"
        "contra la estimación directa. Como θ̂_d − EBLUP = (1 − γd)(θ̂_d − x'β̂), se espera\n"
        "residuo negativo para θ̂_d pequeños (el EBLUP sube la estimación) y positivo para\n"
        "θ̂_d grandes (el EBLUP la baja). Es una descripción de la contracción hacia el\n"
        "predictor sintético, no una prueba de validez del modelo.\n"
        "Gráfica 2 (Histograma de residuos estandarizados): distribución de\n"
        "(θ̂_d − x'β̂)/√(ψ_d + σ̂²_u). Bajo el supuesto de normalidad del modelo se verían\n"
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
        f"  Gráfica 1 (Efecto suavizador): corr(θ̂_d, θ̂_d−EBLUP)={corr:.3f} (p={pval:.4f})  "
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
        fig, ax = plt.subplots(figsize=(ANCHO_FIGURA, 5.2))
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

    fig, ax = plt.subplots(figsize=(ANCHO_FIGURA, 4.6))
    ax.vlines(x, cv_eb, cv_dir, color=GRIS_CLARO, linewidth=2, zorder=1)
    ax.scatter(x, cv_dir, color=GRIS, s=36, label="CV directo", zorder=3)
    ax.scatter(x, cv_eb, color=AZUL, s=36, label="CV EBLUP", zorder=3)
    ax.axhline(CV_CONFIABLE, color=GRIS, linestyle="--", linewidth=1)
    ax.axhline(CV_ACEPTABLE, color=NARANJA, linestyle="--", linewidth=1)
    ax.text(x[-1] + 0.4, CV_CONFIABLE, f"{CV_CONFIABLE}%", va="center", fontsize=9)
    ax.text(x[-1] + 0.4, CV_ACEPTABLE, f"{CV_ACEPTABLE}%", va="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(nombres_dominio[orden], rotation=60, ha="right")
    ax.set_xlabel(r"Dominios, de menor a mayor varianza directa $\psi_d$")
    ax.set_ylabel("Coeficiente de variación (%)")
    ax.legend(loc="upper left")
    ax.grid(axis="x", visible=False)
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
        f"  Reducción media del CV en el tercio de menor ψ_d: {mejora_baja:.2f} pp; "
        f"en el tercio de mayor ψ_d: {mejora_alta:.2f} pp.\n"
        f"  Dominios con CV < {CV_CONFIABLE}%: {confiables_dir} con la estimación directa, "
        f"{confiables_eb} con el EBLUP (de {modelo.n}).\n"
        "  Lectura: la ganancia se concentra donde la varianza directa es grande; donde la "
        "muestra es grande el MSE del EBLUP tiende a ψ_d y el EBLUP casi coincide con la "
        "estimación directa (Morales et al., p. 440). Que MSE_EBLUP < ψ_d es lo esperado por "
        "construcción (g1 = γd·ψ_d < ψ_d), no una validación independiente del modelo."
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
