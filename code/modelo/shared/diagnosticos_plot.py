import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D

from shared.modelo_area_pequena import ModeloAreaPequena


def explicacion_graficas() -> str:
    """Texto narrativo que explica qué observar en las 4 gráficas de validación.

    Returns:
        str: Explicación lista para imprimir antes de mostrar las figuras de
            `graficar_validacion()`.
    """
    return (
        "Gráfica 1 (Residuos GVF): dado que las varianzas directas suelen ser\n"
        "inestables, el modelo depende de una Función de Varianza Generalizada\n"
        "(GVF) ajustada como log(Di) = a + b·log(Y). Los residuos deben verse\n"
        "aleatorios alrededor de 0, sin patrones.\n"
        "Gráfica 2 (GVF predicha vs observada): valida el poder predictivo de la\n"
        "GVF; los puntos deben acercarse a la línea de identidad (y = x).\n"
        "Gráfica 3 (Efecto suavizador): compara el residuo del EBLUP (Yd − EBLUP)\n"
        "contra la estimación directa. Se espera que para valores pequeños de Yd\n"
        "el residuo sea negativo (el EBLUP sube la estimación) y para valores\n"
        "grandes sea positivo (el EBLUP la baja), confirmando que el modelo\n"
        "corrige los valores extremos inestables hacia la tendencia central.\n"
        "Gráfica 4 (Histograma de residuos estandarizados): distribución de\n"
        "(Y − ŷ_sintético)/√(Di+Â). Bajo el supuesto del modelo deben verse\n"
        "aproximadamente normales, centrados en 0 y con desviación ≈ 1 (línea\n"
        "de densidad normal de referencia superpuesta); es el respaldo visual\n"
        "del test de Shapiro-Wilk reportado en los diagnósticos.\n"
    )


def interpretar_validacion(modelo: ModeloAreaPequena) -> str:
    """Interpretación cuantitativa de las 3 gráficas de validación de un modelo ajustado.

    Calcula, a partir de los datos reales del modelo, las mismas
    cantidades que se grafican en `graficar_validacion()` y las traduce en
    una lectura concreta: bondad de ajuste de la GVF (gráficas 1 y 2) y
    si el EBLUP efectivamente contrae los dominios con estimación directa
    extrema hacia la tendencia central (gráfica 3).

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `eblup`
            asignado.

    Returns:
        str: Interpretación lista para imprimir junto a la figura de
            `graficar_validacion()`.

    Raises:
        AttributeError: Si el modelo no tiene `eblup` asignado.
    """
    Di_gvf_pred, mask_pos = _ajustar_gvf(modelo.Y, modelo.Di)
    resid_gvf = modelo.Di[mask_pos] - Di_gvf_pred[mask_pos]
    slope, intercept, r_value, _, _ = stats.linregress(
        np.log(modelo.Y[mask_pos]), np.log(modelo.Di[mask_pos])
    )

    resid_fh = modelo.Y - modelo.eblup
    corr_suavizador, corr_pval = stats.pearsonr(modelo.Y, resid_fh)

    gvf_ok = abs(resid_gvf.mean()) < resid_gvf.std()
    suaviza_ok = corr_suavizador > 0 and corr_pval < 0.05

    return (
        "INTERPRETACIÓN:\n"
        f"  Gráfica 1 (Residuos GVF): media={resid_gvf.mean():.4f}, "
        f"sd={resid_gvf.std():.4f}  "
        + ("✓ sin sesgo aparente" if gvf_ok else "✗ posible sesgo / patrón residual") + "\n"
        f"  Gráfica 2 (GVF predicha vs observada): pendiente b={slope:.3f}, "
        f"R²={r_value**2:.3f} en log(Di) = a + b·log(Y)  "
        + ("✓ buen poder predictivo" if r_value**2 >= 0.5 else "~ poder predictivo moderado/bajo") + "\n"
        f"  Gráfica 3 (Efecto suavizador): corr(Yd, Yd−EBLUP)={corr_suavizador:.3f} "
        f"(p={corr_pval:.4f})  "
        + ("✓ el EBLUP contrae los extremos hacia la tendencia central"
           if suaviza_ok else
           "✗ no se confirma estadísticamente el patrón esperado de contracción")
    )


def _annotate(ax, xs: np.ndarray, ys: np.ndarray, labels: np.ndarray) -> None:
    """Anota cada punto de un scatter con su etiqueta de municipio.

    Args:
        ax: Ejes de matplotlib donde dibujar.
        xs (np.ndarray): Coordenadas x de los puntos.
        ys (np.ndarray): Coordenadas y de los puntos.
        labels (np.ndarray): Etiqueta de texto por punto.
    """
    for xi, yi, lab in zip(xs, ys, labels):
        ax.annotate(lab, (xi, yi), textcoords="offset points",
                    xytext=(4, 3), fontsize=7, color="dimgray")


def _ajustar_gvf(Y: np.ndarray, Di: np.ndarray) -> tuple:
    """Ajusta la Función de Varianza Generalizada log(Di) = a + b·log(Y).

    Args:
        Y (np.ndarray): Estimación directa por dominio.
        Di (np.ndarray): Varianza directa por dominio.

    Returns:
        tuple: (Di_gvf_pred, mask_pos). `Di_gvf_pred` tiene NaN en los
            dominios excluidos (Y <= 0 o Di <= 0); `mask_pos` indica qué
            dominios se usaron para el ajuste.
    """
    mask_pos   = (Y > 0) & (Di > 0)
    slope, intercept, _, _, _ = stats.linregress(np.log(Y[mask_pos]), np.log(Di[mask_pos]))
    Di_gvf_pred = np.where(
        mask_pos,
        np.exp(intercept + slope * np.log(np.where(mask_pos, Y, 1))),
        np.nan,
    )
    return Di_gvf_pred, mask_pos


def _graficar_residuos_gvf(ax, Y: np.ndarray, resid_gvf: np.ndarray, municipios: np.ndarray) -> None:
    """Dibuja los residuos de la GVF (Di − D̂i) contra la estimación directa."""
    ax.axhline(0, color="red", linestyle="--", linewidth=1.2, label="Referencia 0")
    ax.scatter(Y, resid_gvf, color="steelblue", edgecolors="white", s=70, alpha=0.85, zorder=3)
    _annotate(ax, Y, resid_gvf, municipios)
    ax.set_xlabel("Estimación directa Yd  (%)", fontsize=10)
    ax.set_ylabel("Residuo GVF  (Di − D̂i)", fontsize=10)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
    ax.legend(fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.5)


def _graficar_gvf_pred_vs_obs(ax, Di: np.ndarray, Di_gvf_pred: np.ndarray,
                                mask_pos: np.ndarray, municipios: np.ndarray) -> None:
    """Dibuja la varianza GVF predicha contra la observada, con línea de identidad."""
    all_d   = np.concatenate([Di[mask_pos], Di_gvf_pred[mask_pos]])
    d_range = [all_d.min() * 0.9, all_d.max() * 1.1]
    ax.plot(d_range, d_range, "r--", linewidth=1.4, label="y = x")
    ax.scatter(Di, Di_gvf_pred, color="steelblue", edgecolors="white", s=70, alpha=0.85, zorder=3)
    _annotate(ax, Di, Di_gvf_pred, municipios)
    ax.set_xlim(d_range)
    ax.set_ylim(d_range)
    ax.set_xlabel("Varianza directa observada (Di)", fontsize=10)
    ax.set_ylabel("Varianza GVF predicha (D̂i)", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.5)


def _graficar_efecto_suavizador(ax, Y: np.ndarray, resid_fh: np.ndarray, municipios: np.ndarray) -> None:
    """Dibuja el residuo del EBLUP (Yd − EBLUP) contra la estimación directa."""
    ax.axhline(0, color="red", linestyle="--", linewidth=1.2, label="Referencia 0")
    colores = ["tomato" if r > 0 else "steelblue" for r in resid_fh]
    ax.scatter(Y, resid_fh, c=colores, edgecolors="white", s=70, alpha=0.85, zorder=3)
    _annotate(ax, Y, resid_fh, municipios)
    ax.set_xlabel("Estimación directa Yd  (%)", fontsize=10)
    ax.set_ylabel("Residuo FH  (Yd − EBLUP)", fontsize=10)
    leyenda = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="tomato", markersize=8,
               label="EBLUP < Yd  (suaviza hacia abajo)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="steelblue", markersize=8,
               label="EBLUP > Yd  (suaviza hacia arriba)"),
    ]
    ax.legend(handles=leyenda, fontsize=8)
    ax.grid(True, linestyle=":", alpha=0.5)


def _graficar_histograma_residuos(ax, residuals: np.ndarray) -> None:
    """Dibuja el histograma de los residuos estandarizados con curva normal de referencia."""
    ax.axvline(0, color="red", linestyle="--", linewidth=1.2, label="Referencia 0")
    ax.hist(residuals, bins=min(15, max(5, len(residuals) // 3)),
            color="steelblue", edgecolor="white", alpha=0.85, density=True, zorder=3)

    xs = np.linspace(residuals.min() - 1, residuals.max() + 1, 200)
    ax.plot(xs, stats.norm.pdf(xs, 0, 1), color="darkorange", linewidth=1.8,
            label="N(0,1) referencia")

    ax.set_xlabel("Residuo estandarizado  (Y − ŷ_sintético) / √(Di+Â)", fontsize=10)
    ax.set_ylabel("Densidad", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.5)


def graficar_validacion(modelo: ModeloAreaPequena, etiqueta: str) -> list:
    """Construye las 4 figuras individuales de validación de un modelo ajustado.

    Args:
        modelo (ModeloAreaPequena): Modelo ya ajustado, con `resultados`
            (salida de `tabla_resultados()`) y `residuals` asignados.
        etiqueta (str): Texto descriptivo del modelo para el título
            (p. ej. "Modelo 1: IND_PROD + IND_POB_MULT").

    Returns:
        list[matplotlib.figure.Figure]: Una figura por gráfica (residuos GVF,
            GVF predicha vs observada, efecto suavizador del EBLUP,
            histograma de residuos estandarizados), cada una independiente.

    Raises:
        AttributeError: Si el modelo no tiene `resultados` o `residuals` asignados.
    """
    municipios = modelo.resultados["MUNICIPIO"].values
    Di_gvf_pred, mask_pos = _ajustar_gvf(modelo.Y, modelo.Di)
    resid_gvf = modelo.Di - Di_gvf_pred
    resid_fh  = modelo.Y - modelo.eblup

    paneles = [
        (_graficar_residuos_gvf, (modelo.Y, resid_gvf, municipios)),
        (_graficar_gvf_pred_vs_obs, (modelo.Di, Di_gvf_pred, mask_pos, municipios)),
        (_graficar_efecto_suavizador, (modelo.Y, resid_fh, municipios)),
        (_graficar_histograma_residuos, (modelo.residuals,)),
    ]

    figuras = []
    for funcion_graficado, args in paneles:
        fig, ax = plt.subplots(figsize=(8, 6.5))
        funcion_graficado(ax, *args)
        plt.tight_layout()
        figuras.append(fig)

    return figuras
