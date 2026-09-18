"""Análisis descriptivo univariado, bivariado y multivariado.

Este módulo cubre la etapa de caracterización de los datos previa al modelamiento: su
propósito es comprender cómo se comportan la variable respuesta, su medida de precisión y
las covariables candidatas, y cómo se relacionan entre sí. **Ninguna de estas funciones
descarta covariables.** Las decisiones de selección se toman en `seleccion.py`, a partir de
los diagnósticos de `diagnosticos.py`.

La separación es deliberada: una covariable asimétrica no se elimina por ser asimétrica, y
un valor extremo no se elimina por ser extremo. La descripción identifica patrones; el
diagnóstico posterior determina si esos patrones tienen consecuencias metodológicas.
"""

import os

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from scipy import stats
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform

matplotlib.rcParams["axes.grid"] = True
matplotlib.rcParams["grid.linestyle"] = ":"
matplotlib.rcParams["grid.alpha"] = 0.4


def guardar_figura(fig, nombre: str, directorio: str = None) -> str:
    """Guarda una figura en el directorio de salida y devuelve su ruta.

    Args:
        fig (matplotlib.figure.Figure): Figura a guardar.
        nombre (str): Nombre del archivo, sin extensión.
        directorio (str | None): Directorio destino. Si es None, la figura no se guarda y
            se devuelve una cadena vacía (útil para ejecuciones exploratorias).

    Returns:
        str: Ruta del archivo escrito, o cadena vacía si no se guardó.

    Example:
        >>> guardar_figura(fig, "desc_respuesta", VOLUMEN_FIGURAS)
    """
    if not directorio:
        return ""
    os.makedirs(directorio, exist_ok=True)
    ruta = os.path.join(directorio, f"{nombre}.png")
    fig.savefig(ruta, dpi=200, bbox_inches="tight")
    print(f"  figura guardada: {ruta}")
    return ruta


# ══════════════════════════════════════════════════════════════════════════════
# 1. ANÁLISIS UNIVARIADO
# ══════════════════════════════════════════════════════════════════════════════


def resumen_univariado(
    df: pd.DataFrame,
    columnas: list,
    etiquetas: dict = None,
    incluir_cv: bool = True,
) -> pd.DataFrame:
    """Calcula los estadísticos descriptivos univariados de un conjunto de variables.

    Reporta recuento, faltantes, tendencia central, dispersión, posición, forma y una
    identificación descriptiva de valores extremos por el criterio del rango
    intercuartílico. El coeficiente de variación se calcula únicamente cuando la variable
    es estrictamente positiva, que es la condición bajo la cual tiene interpretación como
    dispersión relativa.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Columnas a caracterizar.
        etiquetas (dict | None): Mapa columna → nombre legible para la tabla.
        incluir_cv (bool): Si es False, omite el coeficiente de variación.

    Returns:
        pd.DataFrame: Una fila por variable con n, faltantes, media, mediana, desviación,
            mínimo, Q1, Q3, máximo, rango intercuartílico, coeficiente de variación,
            asimetría y número de valores extremos según el criterio del rango
            intercuartílico.

    Raises:
        ValueError: Si alguna columna no existe en `df`.

    Example:
        >>> resumen_univariado(df, ["TASA_DESEMPLEO_PCT", "SE_BOOTSTRAP_PCT"])
    """
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        raise ValueError(f"Columnas faltantes en df: {faltantes}")

    etiquetas = etiquetas or {}
    filas = []

    for col in columnas:
        serie = pd.to_numeric(df[col], errors="coerce")
        datos = serie.dropna().values
        n_val = len(datos)

        q1, q3 = np.percentile(datos, [25, 75])
        iqr = q3 - q1
        limites = (q1 - 1.5 * iqr, q3 + 1.5 * iqr)
        n_extremos = int(((datos < limites[0]) | (datos > limites[1])).sum())

        media = float(np.mean(datos))
        desv = float(np.std(datos, ddof=1))
        cv = (
            (100 * desv / media)
            if (incluir_cv and n_val and (datos > 0).all())
            else np.nan
        )

        filas.append(
            {
                "Variable": etiquetas.get(col, col),
                "Codigo": col,
                "N": n_val,
                "Faltantes": int(serie.isna().sum()),
                "Faltantes_pct": round(100 * serie.isna().sum() / len(serie), 2),
                "Media": round(media, 4),
                "Mediana": round(float(np.median(datos)), 4),
                "Desv_Std": round(desv, 4),
                "Minimo": round(float(np.min(datos)), 4),
                "Q1": round(float(q1), 4),
                "Q3": round(float(q3), 4),
                "Maximo": round(float(np.max(datos)), 4),
                "IQR": round(float(iqr), 4),
                "CV_pct": round(cv, 2) if not np.isnan(cv) else None,
                "Asimetria": round(float(stats.skew(datos, bias=False)), 3),
                "N_extremos_IQR": n_extremos,
            }
        )

    return pd.DataFrame(filas)


def dominios_extremos(
    df: pd.DataFrame, columnas: list, etiquetas_dominio: np.ndarray, alias: dict = None
) -> pd.DataFrame:
    """Identifica qué dominios quedan fuera del rango intercuartílico de cada variable.

    La detección es descriptiva: nombrar el territorio permite juzgar si un valor extremo
    es un error de medición o una característica sustantiva del dominio. No implica
    ninguna exclusión.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Columnas a examinar.
        etiquetas_dominio (np.ndarray): Nombre de cada dominio, en el orden de las filas.
        alias (dict | None): Mapa columna → alias legible.

    Returns:
        pd.DataFrame: Una fila por variable con el número de dominios extremos y su lista.

    Example:
        >>> dominios_extremos(df_cand, codigos, entidades, alias)
    """
    alias = alias or {}
    filas = []
    for col in columnas:
        datos = pd.to_numeric(df[col], errors="coerce").values
        q1, q3 = np.percentile(datos, [25, 75])
        iqr = q3 - q1
        mascara = (datos < q1 - 1.5 * iqr) | (datos > q3 + 1.5 * iqr)
        nombres = [etiquetas_dominio[i] for i in np.where(mascara)[0]]
        filas.append(
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "N_extremos": len(nombres),
                "Dominios": ", ".join(nombres) if nombres else "—",
            }
        )
    return pd.DataFrame(filas)


def figura_respuesta(
    y: np.ndarray,
    se: np.ndarray,
    nombre_y: str = "Tasa de desempleo (%)",
    nombre_se: str = "Error estándar (puntos porcentuales)",
):
    """Panel descriptivo de la variable respuesta y de su medida de precisión.

    Cuatro paneles: histograma y diagrama de caja de la estimación directa, y los mismos
    dos para su error estándar. La caracterización del error estándar es tan necesaria como
    la de la respuesta, porque su cuadrado es la varianza de muestreo que el modelo
    Fay-Herriot toma como conocida.

    Args:
        y (np.ndarray): Estimación directa por dominio.
        se (np.ndarray): Error estándar de la estimación directa por dominio.
        nombre_y (str): Etiqueta del eje para la respuesta.
        nombre_se (str): Etiqueta del eje para el error estándar.

    Returns:
        matplotlib.figure.Figure: Figura con los cuatro paneles.

    Example:
        >>> fig = figura_respuesta(Y, SE)
    """
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))

    for fila, (datos, etiqueta) in enumerate([(y, nombre_y), (se, nombre_se)]):
        axes[fila][0].hist(datos, bins=8, color="steelblue", edgecolor="white")
        axes[fila][0].axvline(
            np.mean(datos),
            color="firebrick",
            linestyle="--",
            linewidth=1.5,
            label=f"Media = {np.mean(datos):.2f}",
        )
        axes[fila][0].axvline(
            np.median(datos),
            color="darkgreen",
            linestyle=":",
            linewidth=1.5,
            label=f"Mediana = {np.median(datos):.2f}",
        )
        axes[fila][0].set_xlabel(etiqueta, fontsize=10)
        axes[fila][0].set_ylabel("N.º de dominios", fontsize=10)
        axes[fila][0].legend(fontsize=8)

        axes[fila][1].boxplot(
            datos,
            vert=False,
            patch_artist=True,
            boxprops=dict(facecolor="lightsteelblue", color="steelblue"),
            medianprops=dict(color="navy", linewidth=2),
        )
        axes[fila][1].set_xlabel(etiqueta, fontsize=10)
        axes[fila][1].set_yticks([])

    plt.tight_layout()
    return fig


def figura_territorial(
    y: np.ndarray,
    etiquetas_dominio: np.ndarray,
    nombre_y: str = "Tasa de desempleo (%)",
):
    """Distribución territorial de la variable respuesta, ordenada por magnitud.

    Descripción territorial, no contraste espacial: muestra qué dominios se sitúan en cada
    extremo, sin evaluar hipótesis alguna sobre dependencia entre vecinos. El modelo
    Fay-Herriot clásico del proyecto supone efectos independientes por dominio, de modo que
    no se realiza ningún contraste de autocorrelación espacial.

    Args:
        y (np.ndarray): Estimación directa por dominio.
        etiquetas_dominio (np.ndarray): Nombre de cada dominio.
        nombre_y (str): Etiqueta del eje.

    Returns:
        matplotlib.figure.Figure: Figura de barras horizontales ordenadas.

    Example:
        >>> fig = figura_territorial(Y, entidades)
    """
    orden = np.argsort(y)
    fig, ax = plt.subplots(figsize=(8, 0.32 * len(y) + 1.5))
    ax.barh(np.arange(len(y)), y[orden], color="steelblue", edgecolor="white")
    ax.axvline(
        np.mean(y),
        color="firebrick",
        linestyle="--",
        linewidth=1.5,
        label=f"Media nacional de los dominios = {np.mean(y):.2f}",
    )
    ax.set_yticks(np.arange(len(y)))
    ax.set_yticklabels([etiquetas_dominio[i] for i in orden], fontsize=8)
    ax.set_xlabel(nombre_y, fontsize=10)
    ax.legend(fontsize=9)
    plt.tight_layout()
    return fig


def figura_panel_boxplots(df: pd.DataFrame, columnas: list, alias: dict = None):
    """Panel compacto de diagramas de caja de las covariables, en escala estandarizada.

    Estandarizar permite comparar la forma de las distribuciones en un solo eje, sin
    generar una figura por covariable. La estandarización es exclusivamente gráfica: no
    modifica los datos que entran al modelo.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a graficar.
        alias (dict | None): Mapa columna → alias legible.

    Returns:
        matplotlib.figure.Figure: Figura con un diagrama de caja por covariable.

    Example:
        >>> fig = figura_panel_boxplots(df_cand, codigos, alias)
    """
    alias = alias or {}
    datos = [
        (df[c].values - df[c].values.mean()) / df[c].values.std(ddof=1)
        for c in columnas
    ]
    etiquetas = [alias.get(c, c) for c in columnas]

    fig, ax = plt.subplots(figsize=(9, 0.45 * len(columnas) + 2))
    ax.boxplot(
        datos,
        vert=False,
        patch_artist=True,
        labels=etiquetas,
        boxprops=dict(facecolor="lightsteelblue", color="steelblue"),
        medianprops=dict(color="navy", linewidth=2),
        flierprops=dict(
            marker="o",
            markersize=4,
            markerfacecolor="firebrick",
            markeredgecolor="firebrick",
        ),
    )
    ax.axvline(0, color="dimgray", linewidth=1)
    ax.set_xlabel(
        "Desviaciones estándar respecto a la media del indicador", fontsize=10
    )
    ax.tick_params(labelsize=9)
    plt.tight_layout()
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 2. ANÁLISIS BIVARIADO
# ══════════════════════════════════════════════════════════════════════════════


def tabla_bivariada(
    df: pd.DataFrame,
    columnas: list,
    y: np.ndarray,
    alias: dict = None,
    umbral_divergencia: float = 0.10,
) -> pd.DataFrame:
    """Describe la relación de cada covariable con la variable respuesta.

    Reporta el coeficiente de Pearson y el de Spearman e indica **cuál de los dos es el
    adecuado** para cada covariable, en lugar de presentar ambos indistintamente. El
    criterio es explícito: si la covariable presenta valores extremos según el rango
    intercuartílico y las dos medidas discrepan más de `umbral_divergencia`, la asociación
    lineal está condicionada por esos puntos y la medida interpretable es la de rangos; en
    cualquier otro caso ambas coinciden y se interpreta Pearson, que es la que corresponde
    a la forma lineal que el modelo Fay-Herriot supone en su componente sintético.

    Los coeficientes son descriptivos. No se usan aquí para incluir ni excluir covariables.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar.
        y (np.ndarray): Variable respuesta.
        alias (dict | None): Mapa columna → alias legible.
        umbral_divergencia (float): Discrepancia entre Pearson y Spearman a partir de la
            cual se considera que los valores extremos condicionan la asociación lineal.

    Returns:
        pd.DataFrame: Una fila por covariable con ambos coeficientes, la discrepancia, el
            número de valores extremos y la medida recomendada con su motivo.

    Example:
        >>> tabla_bivariada(df_cand, codigos, Y, alias)
    """
    alias = alias or {}
    filas = []

    for col in columnas:
        x = pd.to_numeric(df[col], errors="coerce").values
        r_p = float(stats.pearsonr(x, y)[0])
        r_s = float(stats.spearmanr(x, y)[0])

        q1, q3 = np.percentile(x, [25, 75])
        iqr = q3 - q1
        n_extremos = int(((x < q1 - 1.5 * iqr) | (x > q3 + 1.5 * iqr)).sum())

        discrepancia = abs(r_p - r_s)
        if n_extremos > 0 and discrepancia > umbral_divergencia:
            medida, motivo = (
                "Spearman",
                "valores extremos condicionan la relación lineal",
            )
        else:
            medida, motivo = (
                "Pearson",
                "relación aproximadamente lineal, sin punto dominante",
            )

        filas.append(
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "Pearson_r": round(r_p, 3),
                "Spearman_rho": round(r_s, 3),
                "Discrepancia": round(discrepancia, 3),
                "N_extremos_IQR": n_extremos,
                "Medida_interpretable": medida,
                "Motivo": motivo,
            }
        )

    return pd.DataFrame(filas).sort_values("Pearson_r", key=abs, ascending=False)


def figura_panel_dispersion(
    df: pd.DataFrame,
    columnas: list,
    y: np.ndarray,
    alias: dict = None,
    nombre_y: str = "Tasa de desempleo (%)",
    ncols: int = 3,
):
    """Panel de diagramas de dispersión de cada covariable frente a la respuesta.

    Un solo panel en lugar de una figura por covariable, con la recta de mínimos cuadrados
    como referencia visual de la tendencia. Los diagramas son descriptivos: muestran la
    forma de la relación y si hay dominios que se apartan del patrón general.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a graficar.
        y (np.ndarray): Variable respuesta.
        alias (dict | None): Mapa columna → alias legible.
        nombre_y (str): Etiqueta del eje vertical.
        ncols (int): Número de columnas del panel.

    Returns:
        matplotlib.figure.Figure: Figura con un diagrama por covariable.

    Example:
        >>> fig = figura_panel_dispersion(df_cand, codigos, Y, alias)
    """
    alias = alias or {}
    nfilas = (len(columnas) + ncols - 1) // ncols
    fig, axes = plt.subplots(nfilas, ncols, figsize=(4.2 * ncols, 3.4 * nfilas))
    axes = np.atleast_1d(axes).flatten()

    for idx, col in enumerate(columnas):
        ax = axes[idx]
        x = pd.to_numeric(df[col], errors="coerce").values
        ax.scatter(x, y, color="steelblue", edgecolors="white", s=45, zorder=3)
        pendiente, intercepto = np.polyfit(x, y, 1)
        rejilla = np.linspace(x.min(), x.max(), 50)
        ax.plot(rejilla, pendiente * rejilla + intercepto, "r--", linewidth=1.3)
        r_p = stats.pearsonr(x, y)[0]
        r_s = stats.spearmanr(x, y)[0]
        ax.set_title(
            f"{alias.get(col, col)}\nr = {r_p:.2f}   ρ = {r_s:.2f}", fontsize=9
        )
        ax.set_ylabel(nombre_y, fontsize=8)
        ax.tick_params(labelsize=7)

    for idx in range(len(columnas), len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 3. ANÁLISIS MULTIVARIADO
# ══════════════════════════════════════════════════════════════════════════════


def orden_por_agrupamiento(df: pd.DataFrame, columnas: list) -> list:
    """Ordena las covariables por agrupamiento jerárquico sobre su matriz de correlación.

    Usa ``1 - |r|`` como distancia y enlace promedio, de modo que las covariables que miden
    aspectos parecidos del territorio queden contiguas. El resultado es un orden de
    presentación: no agrupa dominios ni transforma los datos.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a ordenar.

    Returns:
        list[str]: Las mismas covariables, reordenadas.

    Example:
        >>> orden_por_agrupamiento(df_cand, codigos)
    """
    if len(columnas) < 3:
        return list(columnas)
    corr = df[columnas].corr().abs()
    distancia = 1 - corr.values
    np.fill_diagonal(distancia, 0.0)
    distancia = (distancia + distancia.T) / 2
    enlace = linkage(squareform(distancia, checks=False), method="average")
    return [columnas[i] for i in leaves_list(enlace)]


def figura_correlacion_agrupada(
    df: pd.DataFrame, columnas: list, alias: dict = None, titulo: str = None
):
    """Mapa de calor de la matriz de correlación entre covariables, reordenado por bloques.

    Responde a una pregunta que el análisis por pares no contesta: qué grupos de
    covariables miden conjuntamente el mismo aspecto del territorio. Es la caracterización
    multivariada del conjunto de candidatas, y alimenta el criterio de redundancia que se
    aplica después en la selección.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a incluir.
        alias (dict | None): Mapa columna → alias legible.
        titulo (str | None): Título de la figura.

    Returns:
        tuple[matplotlib.figure.Figure, list]: La figura y el orden de covariables usado.

    Example:
        >>> fig, orden = figura_correlacion_agrupada(df_cand, codigos, alias)
    """
    alias = alias or {}
    orden = orden_por_agrupamiento(df, columnas)
    corr = df[orden].corr()
    etiquetas = [alias.get(c, c) for c in orden]

    fig, ax = plt.subplots(figsize=(1.0 * len(orden) + 3, 0.85 * len(orden) + 2.5))
    imagen = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)

    ax.set_xticks(np.arange(len(orden)))
    ax.set_yticks(np.arange(len(orden)))
    ax.set_xticklabels(etiquetas, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(etiquetas, fontsize=8)
    ax.grid(False)

    for i in range(len(orden)):
        for j in range(len(orden)):
            valor = corr.values[i, j]
            ax.text(
                j,
                i,
                f"{valor:.2f}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if abs(valor) > 0.6 else "black",
            )

    fig.colorbar(imagen, ax=ax, shrink=0.75, label="Correlación de Pearson")
    if titulo:
        ax.set_title(titulo, fontsize=11, fontweight="bold", pad=12)
    plt.tight_layout()
    return fig, orden


def tabla_pares_correlacionados(
    df: pd.DataFrame, columnas: list, alias: dict = None, umbral: float = 0.80
) -> pd.DataFrame:
    """Lista los pares de covariables cuya correlación supera un umbral de magnitud.

    Resume en forma de tabla lo que el mapa de calor muestra gráficamente, para que la
    evidencia de redundancia quede tabulada y sea citable desde el documento.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar.
        alias (dict | None): Mapa columna → alias legible.
        umbral (float): Magnitud mínima de correlación para listar el par.

    Returns:
        pd.DataFrame: Una fila por par, ordenada por magnitud descendente.

    Example:
        >>> tabla_pares_correlacionados(df_cand, codigos, alias, umbral=0.80)
    """
    alias = alias or {}
    corr = df[columnas].corr()
    filas = []
    for i, a in enumerate(columnas):
        for b in columnas[i + 1 :]:
            valor = float(corr.loc[a, b])
            if abs(valor) >= umbral:
                filas.append(
                    {
                        "Variable_1": alias.get(a, a),
                        "Variable_2": alias.get(b, b),
                        "Correlacion": round(valor, 3),
                    }
                )
    return (
        pd.DataFrame(filas)
        .sort_values("Correlacion", key=abs, ascending=False)
        .reset_index(drop=True)
    )


# ══════════════════════════════════════════════════════════════════════════════
# 4. INTERPRETACIÓN DE LAS FIGURAS
# ══════════════════════════════════════════════════════════════════════════════
#
# Cada función calcula, a partir de los mismos datos que se grafican, las cantidades que
# el lector necesita para leer la figura y las traduce en una lectura concreta. Se sigue
# el patrón de `interpretar_validacion()` en `modelo/shared/diagnosticos_plot.py`: el texto
# se genera desde los datos, de modo que no queda desactualizado si cambian.


def _nombres(indices, etiquetas_dominio: np.ndarray) -> str:
    """Une los nombres de dominio de una lista de índices en una cadena legible."""
    return ", ".join(str(etiquetas_dominio[i]) for i in indices)


def interpretar_respuesta(
    y: np.ndarray, se: np.ndarray, etiquetas_dominio: np.ndarray
) -> str:
    """Lectura de la figura de distribución de la respuesta y de su error estándar.

    Cuantifica lo que los cuatro paneles muestran: rango y forma de la tasa de desempleo,
    rango y forma de su error estándar, qué dominios ocupan los extremos de ambos, y cuánto
    se relacionan entre sí. La relación entre error estándar y nivel de la tasa importa
    porque el modelo Fay-Herriot contrae más las estimaciones con mayor varianza de
    muestreo: si el error crece con la tasa, los dominios de mayor desempleo serán los más
    suavizados.

    Args:
        y (np.ndarray): Estimación directa por dominio.
        se (np.ndarray): Error estándar de la estimación directa.
        etiquetas_dominio (np.ndarray): Nombre de cada dominio, en el orden de las filas.

    Returns:
        str: Interpretación lista para imprimir junto a la figura.

    Example:
        >>> print(interpretar_respuesta(Y, SE, entidades))
    """
    asim_y = float(stats.skew(y, bias=False))
    asim_se = float(stats.skew(se, bias=False))
    r_se_y = float(stats.pearsonr(y, se)[0])
    orden_y = np.argsort(y)
    orden_se = np.argsort(se)
    cv_dir = 100 * se / np.abs(y)

    def forma(asim):
        if abs(asim) < 0.5:
            return "aproximadamente simétrica"
        lado = (
            "derecha (cola hacia valores altos)"
            if asim > 0
            else "izquierda (cola hacia valores bajos)"
        )
        grado = "moderadamente" if abs(asim) < 1 else "marcadamente"
        return f"{grado} asimétrica hacia la {lado}"

    lineas = [
        "INTERPRETACIÓN DE LA FIGURA:",
        f"  Tasa de desempleo: entre {y.min():.1f} % ({_nombres(orden_y[:1], etiquetas_dominio)}) y "
        f"{y.max():.1f} % ({_nombres(orden_y[-1:], etiquetas_dominio)}); media {y.mean():.1f} %, "
        f"mediana {np.median(y):.1f} %.",
        f"  Forma de la distribución de la tasa: {forma(asim_y)} (asimetría {asim_y:.2f}). "
        + (
            "Media y mediana casi coinciden: no hay un grupo de dominios que arrastre el promedio."
            if abs(asim_y) < 0.5
            else "La separación entre media y mediana señala que unos pocos dominios extremos arrastran el promedio."
        ),
        f"  Error estándar: entre {se.min():.2f} y {se.max():.2f} puntos porcentuales; los dominios con "
        f"estimación menos precisa son {_nombres(orden_se[-3:][::-1], etiquetas_dominio)}, y los más "
        f"precisos {_nombres(orden_se[:3], etiquetas_dominio)}.",
        f"  Forma de la distribución del error estándar: {forma(asim_se)} (asimetría {asim_se:.2f}).",
        f"  Coeficiente de variación de la estimación directa: entre {cv_dir.min():.1f} % y {cv_dir.max():.1f} %; "
        f"{int((cv_dir >= 15).sum())} de {len(y)} dominios superan el 15 % que define una estimación confiable.",
        f"  Correlación entre error estándar y tasa: r = {r_se_y:.2f}. "
        + (
            "El error crece con la tasa, de modo que los dominios de mayor desempleo son también los menos "
            "precisos y serán los que el modelo contraiga con más fuerza hacia el predictor sintético."
            if r_se_y > 0.3
            else "La precisión no depende del nivel de la tasa; la contracción del modelo la fijará el "
            "tamaño de muestra de cada dominio, no su nivel de desempleo."
        ),
    ]
    return "\n".join(lineas)


def interpretar_territorial(y: np.ndarray, etiquetas_dominio: np.ndarray) -> str:
    """Lectura de la figura de barras ordenadas de la tasa de desempleo por dominio.

    Args:
        y (np.ndarray): Estimación directa por dominio.
        etiquetas_dominio (np.ndarray): Nombre de cada dominio.

    Returns:
        str: Interpretación lista para imprimir junto a la figura.

    Example:
        >>> print(interpretar_territorial(Y, entidades))
    """
    orden = np.argsort(y)
    media = y.mean()
    sobre_media = int((y > media).sum())
    brecha = y.max() - y.min()
    lineas = [
        "INTERPRETACIÓN DE LA FIGURA:",
        f"  Dominios con mayor tasa: {_nombres(orden[-3:][::-1], etiquetas_dominio)} "
        f"({y[orden[-1]]:.1f}, {y[orden[-2]]:.1f} y {y[orden[-3]]:.1f} %).",
        f"  Dominios con menor tasa: {_nombres(orden[:3], etiquetas_dominio)} "
        f"({y[orden[0]]:.1f}, {y[orden[1]]:.1f} y {y[orden[2]]:.1f} %).",
        f"  {sobre_media} de {len(y)} dominios están por encima de la media ({media:.1f} %); la brecha entre "
        f"el máximo y el mínimo es de {brecha:.1f} puntos porcentuales, es decir, el dominio más alto "
        f"{'duplica' if y.max() >= 2 * y.min() else 'supera en más de la mitad a'} el más bajo.",
        "  Lectura: es la heterogeneidad territorial que el modelo debe explicar con las covariables. Que un "
        "dominio ocupe un extremo lo convierte en candidato a dominio influyente en el diagnóstico de robustez, "
        "no en un dato a corregir.",
    ]
    return "\n".join(lineas)


def interpretar_boxplots(resumen: pd.DataFrame, alias: dict = None) -> str:
    """Lectura del panel de diagramas de caja de las covariables candidatas.

    Usa la tabla de `resumen_univariado()` para nombrar las covariables más asimétricas,
    las que concentran más valores extremos y las de mayor dispersión relativa, que son
    exactamente los rasgos que el panel estandarizado deja ver.

    Args:
        resumen (pd.DataFrame): Salida de `resumen_univariado()` sobre las candidatas.
        alias (dict | None): Mapa código → alias legible; si la tabla ya trae `Alias` se usa.

    Returns:
        str: Interpretación lista para imprimir junto a la figura.

    Example:
        >>> print(interpretar_boxplots(desc_covariables))
    """
    alias = alias or {}
    tabla = resumen.copy()
    if "Alias" not in tabla.columns:
        tabla["Alias"] = [alias.get(c, c) for c in tabla["Codigo"]]

    asimetricas = tabla.reindex(
        tabla["Asimetria"].abs().sort_values(ascending=False).index
    ).head(3)
    con_extremos = tabla[tabla["N_extremos_IQR"] > 0].sort_values(
        "N_extremos_IQR", ascending=False
    )
    simetricas = tabla[tabla["Asimetria"].abs() < 0.5]
    con_cv = tabla.dropna(subset=["CV_pct"]).sort_values("CV_pct", ascending=False)

    lineas = [
        "INTERPRETACIÓN DE LA FIGURA:",
        f"  Covariables con distribución aproximadamente simétrica (|asimetría| < 0.5): "
        f"{len(simetricas)} de {len(tabla)}"
        + (f" ({', '.join(simetricas['Alias'])})." if len(simetricas) else "."),
        "  Covariables más asimétricas: "
        + "; ".join(
            f"{fila['Alias']} ({fila['Asimetria']:+.2f}, cola hacia valores {'altos' if fila['Asimetria'] > 0 else 'bajos'})"
            for _, fila in asimetricas.iterrows()
        )
        + ".",
        f"  Covariables con valores extremos por el criterio del rango intercuartílico: {len(con_extremos)}"
        + (
            "; las que más acumulan son "
            + ", ".join(
                f"{fila['Alias']} ({int(fila['N_extremos_IQR'])})"
                for _, fila in con_extremos.head(3).iterrows()
            )
            + "."
            if len(con_extremos)
            else "."
        ),
    ]
    if len(con_cv):
        lineas.append(
            "  Mayor dispersión relativa (coeficiente de variación): "
            + ", ".join(
                f"{fila['Alias']} ({fila['CV_pct']:.0f} %)"
                for _, fila in con_cv.head(3).iterrows()
            )
            + "; menor: "
            + ", ".join(
                f"{fila['Alias']} ({fila['CV_pct']:.0f} %)"
                for _, fila in con_cv.tail(2).iterrows()
            )
            + "."
        )
    lineas.append(
        "  Lectura: una covariable asimétrica o con extremos no se descarta por serlo. Lo que importa es si esos "
        "puntos determinan por sí solos su relación con el desempleo, y eso se comprueba en el diagnóstico de "
        "robustez de la etapa de selección."
    )
    return "\n".join(lineas)


def interpretar_dispersion(bivariado: pd.DataFrame, signo_esperado: dict = None) -> str:
    """Lectura del panel de dispersión de cada candidata frente a la tasa de desempleo.

    Resume la tabla de `tabla_bivariada()`: asociaciones más fuertes y su dirección,
    cuáles requieren leerse con Spearman por estar condicionadas por valores extremos, cuáles
    son prácticamente nulas y, si se aporta el signo esperado del catálogo, cuáles lo
    contradicen.

    Args:
        bivariado (pd.DataFrame): Salida de `tabla_bivariada()`.
        signo_esperado (dict | None): Mapa código → `"+"`, `"-"` o `"±"` del catálogo.

    Returns:
        str: Interpretación lista para imprimir junto a la figura.

    Example:
        >>> print(interpretar_dispersion(bivariado, SIGNO))
    """
    signo_esperado = signo_esperado or {}
    tabla = bivariado.copy()
    tabla["r_interp"] = np.where(
        tabla["Medida_interpretable"] == "Spearman",
        tabla["Spearman_rho"],
        tabla["Pearson_r"],
    )
    tabla = tabla.reindex(tabla["r_interp"].abs().sort_values(ascending=False).index)

    fuertes = tabla[tabla["r_interp"].abs() >= 0.5]
    moderadas = tabla[
        (tabla["r_interp"].abs() >= 0.3) & (tabla["r_interp"].abs() < 0.5)
    ]
    debiles = tabla[tabla["r_interp"].abs() < 0.3]
    spearman = tabla[tabla["Medida_interpretable"] == "Spearman"]

    def lista(df):
        return ", ".join(
            f"{fila['Alias']} ({fila['r_interp']:+.2f})" for _, fila in df.iterrows()
        )

    lineas = [
        "INTERPRETACIÓN DE LA FIGURA:",
        f"  Asociación fuerte (|r| >= 0.5): {len(fuertes)}"
        + (f" — {lista(fuertes)}." if len(fuertes) else "."),
        f"  Asociación moderada (0.3 <= |r| < 0.5): {len(moderadas)}"
        + (f" — {lista(moderadas)}." if len(moderadas) else "."),
        f"  Asociación débil o nula (|r| < 0.3): {len(debiles)}"
        + (f" — {lista(debiles)}." if len(debiles) else "."),
        f"  Covariables cuya relación lineal está condicionada por valores extremos (se lee Spearman): "
        f"{len(spearman)}"
        + (f" — {', '.join(spearman['Alias'])}." if len(spearman) else "."),
    ]
    if signo_esperado:
        contrarias = [
            fila["Alias"]
            for _, fila in tabla.iterrows()
            if signo_esperado.get(fila["Codigo"], "±") != "±"
            and np.sign(fila["r_interp"])
            != (1 if signo_esperado[fila["Codigo"]] == "+" else -1)
        ]
        lineas.append(
            f"  Covariables cuyo signo observado contradice el mecanismo del catálogo: {len(contrarias)}"
            + (f" — {', '.join(contrarias)}." if contrarias else ".")
        )
    lineas.append(
        "  Lectura: en la recta de referencia de cada panel se ve la dirección de la asociación; los puntos que se "
        "apartan del patrón son los dominios que después se examinan con la distancia de Cook. Ninguna "
        "covariable se incluye ni se excluye aquí por su coeficiente."
    )
    return "\n".join(lineas)


def interpretar_correlacion(
    pares: pd.DataFrame, orden: list, alias: dict = None, umbral: float = 0.80
) -> str:
    """Lectura del mapa de calor de correlaciones entre covariables.

    Args:
        pares (pd.DataFrame): Salida de `tabla_pares_correlacionados()`.
        orden (list[str]): Orden de covariables devuelto por `figura_correlacion_agrupada()`.
        alias (dict | None): Mapa código → alias legible.
        umbral (float): Umbral de redundancia usado para listar los pares.

    Returns:
        str: Interpretación lista para imprimir junto a la figura.

    Example:
        >>> print(interpretar_correlacion(pares, orden_agrupado, ALIAS))
    """
    alias = alias or {}
    lineas = ["INTERPRETACIÓN DE LA FIGURA:"]
    if pares.empty:
        lineas.append(
            f"  Ningún par de candidatas supera |r| = {umbral}: no hay bloques de covariables que midan lo "
            "mismo y el criterio de redundancia no descartará ninguna."
        )
    else:
        lineas.append(
            f"  Pares con |r| >= {umbral}: {len(pares)}. Los más fuertes: "
            + "; ".join(
                f"{fila['Variable_1']} – {fila['Variable_2']} ({fila['Correlacion']:+.2f})"
                for _, fila in pares.head(4).iterrows()
            )
            + "."
        )
        negativos = pares[pares["Correlacion"] < 0]
        if len(negativos):
            lineas.append(
                f"  {len(negativos)} de esos pares tienen correlación negativa: miden el mismo aspecto en sentido "
                "inverso (por ejemplo, una carencia y su cobertura)."
            )
        lineas.append(
            "  Lectura: en el mapa reordenado esos pares aparecen como bloques contiguos de color intenso. De "
            "cada bloque entrará una sola covariable al modelo; cuál, se decide en la etapa de selección."
        )
    lineas.append(
        "  Orden de presentación (covariables parecidas quedan juntas): "
        + " · ".join(alias.get(c, c) for c in orden)
        + "."
    )
    return "\n".join(lineas)
