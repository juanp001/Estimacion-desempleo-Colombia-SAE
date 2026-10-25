"""Figuras del componente espacial del Fay-Herriot (sin título: el título va en el documento).

Cada función recibe DataFrames ya calculados y devuelve una figura de matplotlib; no lee ni
escribe tablas. El notebook las muestra en pantalla y las guarda en el volumen de figuras con
el prefijo ``fhe_``.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def figura_perfil_rho(perfiles: dict) -> plt.Figure:
    """Log-verosimilitud REML perfilada en ρ, una curva por escenario de W.

    Una curva plana alrededor de ρ = 0 indica que los datos no distinguen el modelo espacial del
    clásico (ρ = 0); un máximo claramente separado de 0 indica dependencia espacial.

    Args:
        perfiles (dict[str, pd.DataFrame]): Nombre del escenario → salida de
            `FayHerriotEspacial.perfil_rho` (columnas `rho` y `delta_vs_rho0`).

    Returns:
        plt.Figure: Figura con el cambio de log-verosimilitud frente a ρ = 0.

    Example:
        >>> fig = figura_perfil_rho({"knn3": modelo.perfil_rho()})
    """
    fig, ax = plt.subplots(figsize=(7, 4))
    for nombre, perfil in perfiles.items():
        ax.plot(perfil["rho"], perfil["delta_vs_rho0"], marker="o", ms=3, label=nombre)
    ax.axhline(0, color="gray", lw=0.8)
    ax.axhline(-1.92, color="gray", lw=0.8, ls="--")
    ax.set_xlabel("ρ")
    ax.set_ylabel("log-verosimilitud REML − valor en ρ = 0")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def figura_validacion(cv: pd.DataFrame, columnas: dict) -> plt.Figure:
    """Predicho frente a observado en la validación dejar-un-dominio-fuera.

    Args:
        cv (pd.DataFrame): Salida de `validacion_dejar_uno_fuera` (columna `y` y las de
            predicción).
        columnas (dict[str, str]): Etiqueta del panel → nombre de la columna de predicción.

    Returns:
        plt.Figure: Un panel por predictor, con la diagonal de 45° como referencia.

    Example:
        >>> figura_validacion(cv, {"Clásico": "pred_clasico", "Espacial": "pred_espacial"})
    """
    fig, ejes = plt.subplots(
        1, len(columnas), figsize=(4.2 * len(columnas), 4), sharey=True
    )
    ejes = np.atleast_1d(ejes)
    lim = [cv["y"].min() - 1, cv["y"].max() + 1]
    for ax, (etiqueta, col) in zip(ejes, columnas.items()):
        ax.scatter(cv["y"], cv[col], s=22)
        ax.plot(lim, lim, color="gray", lw=0.8)
        ax.set_xlabel("Estimación directa")
        ax.text(0.03, 0.96, etiqueta, transform=ax.transAxes, fontsize=10, va="top")
        ax.grid(alpha=0.3)
    ejes[0].set_ylabel("Predicción dejando el dominio fuera")
    fig.tight_layout()
    return fig


def figura_mapa_prediccion(
    objetivo: pd.DataFrame, dominios: pd.DataFrame, columna: str, etiqueta: str
) -> plt.Figure:
    """Dispersión geográfica (longitud/latitud) de una predicción en los municipios objetivo.

    Los dominios con encuesta se dibujan como cuadrados con su estimación directa, en la misma
    escala de color, para ver si la predicción es coherente con las ciudades cercanas.

    Args:
        objetivo (pd.DataFrame): Municipios objetivo con `LONGITUD`, `LATITUD` y `columna`.
        dominios (pd.DataFrame): Dominios con encuesta con `LONGITUD`, `LATITUD` y `Y`.
        columna (str): Columna de `objetivo` a colorear.
        etiqueta (str): Texto de la barra de color.

    Returns:
        plt.Figure: Figura con el recorte geográfico de Cauca y Valle del Cauca.

    Example:
        >>> figura_mapa_prediccion(pred, dom, "PRED_ESPACIAL", "Tasa de desempleo (%)")
    """
    vmin = min(objetivo[columna].min(), dominios["Y"].min())
    vmax = max(objetivo[columna].max(), dominios["Y"].max())
    caja = (
        dominios["LONGITUD"].between(
            objetivo["LONGITUD"].min() - 0.6, objetivo["LONGITUD"].max() + 0.6
        )
    ) & (
        dominios["LATITUD"].between(
            objetivo["LATITUD"].min() - 0.6, objetivo["LATITUD"].max() + 0.6
        )
    )
    fig, ax = plt.subplots(figsize=(5.5, 6))
    sc = ax.scatter(
        objetivo["LONGITUD"],
        objetivo["LATITUD"],
        c=objetivo[columna],
        s=45,
        vmin=vmin,
        vmax=vmax,
        cmap="viridis",
    )
    ax.scatter(
        dominios.loc[caja, "LONGITUD"],
        dominios.loc[caja, "LATITUD"],
        c=dominios.loc[caja, "Y"],
        s=110,
        marker="s",
        vmin=vmin,
        vmax=vmax,
        cmap="viridis",
        edgecolor="black",
    )
    for _, f in dominios[caja].iterrows():
        ax.annotate(
            f["NOMBRE"],
            (f["LONGITUD"], f["LATITUD"]),
            fontsize=7,
            xytext=(4, 4),
            textcoords="offset points",
        )
    fig.colorbar(sc, ax=ax, label=etiqueta)
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def figura_mapa_residuos(dominios: pd.DataFrame, residuos: dict) -> plt.Figure:
    """Residuos estandarizados por dominio sobre longitud/latitud, un panel por modelo (R-12).

    Todos los paneles comparten la escala de color, simétrica alrededor de cero, para que los
    residuos del clásico y del espacial sean comparables a simple vista. Una agrupación de
    colores iguales entre dominios próximos indicaría dependencia espacial no modelada.

    Args:
        dominios (pd.DataFrame): Dominios con encuesta, con `LONGITUD`, `LATITUD` y `NOMBRE`.
        residuos (dict[str, np.ndarray]): Etiqueta del panel → residuos estandarizados por
            dominio, en el orden de `dominios`.

    Returns:
        plt.Figure: Figura con un panel por entrada de `residuos`.

    Example:
        >>> figura_mapa_residuos(dom, {"Clásico": r_clasico, "Espacial": r_espacial})  # doctest: +SKIP
    """
    limite = max(float(np.abs(np.asarray(r)).max()) for r in residuos.values())
    fig, ejes = plt.subplots(1, len(residuos), figsize=(5.2 * len(residuos), 6.2))
    ejes = np.atleast_1d(ejes)
    for ax, (etiqueta, valores) in zip(ejes, residuos.items()):
        sc = ax.scatter(
            dominios["LONGITUD"],
            dominios["LATITUD"],
            c=np.asarray(valores),
            s=90,
            cmap="coolwarm",
            vmin=-limite,
            vmax=limite,
            edgecolor="black",
        )
        for nombre, lon, lat, v in zip(
            dominios["NOMBRE"], dominios["LONGITUD"], dominios["LATITUD"], valores
        ):
            if abs(v) >= 1.0:
                ax.annotate(
                    nombre,
                    (lon, lat),
                    fontsize=7,
                    xytext=(4, 4),
                    textcoords="offset points",
                )
        ax.set_xlabel("Longitud")
        ax.text(0.03, 0.96, etiqueta, transform=ax.transAxes, fontsize=10, va="top")
        ax.grid(alpha=0.3)
    ejes[0].set_ylabel("Latitud")
    fig.colorbar(sc, ax=list(ejes), label="Residuo estandarizado", shrink=0.8)
    return fig
