"""Figuras del componente espacial del Fay-Herriot (sin título: el título va en el documento).

Cada función recibe DataFrames ya calculados y devuelve una figura de matplotlib; no lee ni
escribe tablas. El notebook las muestra en pantalla y las guarda en el volumen de figuras con
el prefijo ``fhe_``.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from comun.estilo_figuras import (
    ANCHO_FIGURA,
    CMAP_DIVERGENTE,
    CMAP_SECUENCIAL,
    GRIS,
    GRIS_OSCURO,
    PALETA,
    etiquetar_puntos,
)
from shared.config import ETIQUETA_ESCENARIO_W


def figura_perfil_rho(perfiles: dict) -> plt.Figure:
    """Log-verosimilitud REML perfilada en ρ, una curva por escenario de W.

    Una curva plana alrededor de ρ = 0 indica que los datos no distinguen el modelo espacial del
    clásico (ρ = 0); un máximo claramente separado de 0 indica dependencia espacial.

    Las curvas se rotulan con el nombre de cada escenario (`ETIQUETA_ESCENARIO_W`, D-10): los
    de vecinos más cercanos en azul y los de distancia inversa en naranja, con trazo continuo
    o discontinuo según el parámetro.

    El intervalo de verosimilitud perfilada del 95 % de cada escenario son los ρ cuya
    log-verosimilitud queda a menos de 1.92 (= χ²₁;0.95 / 2) de su propio máximo. Por eso cada
    curva lleva su segmento horizontal grueso a la altura máx − 1.92, entre los extremos de su
    intervalo (la misma regla que `resumen_perfil` en el notebook). No se dibuja una línea
    común en −1.92: el eje mide la diferencia frente a ρ = 0, no frente al máximo (M1).

    Args:
        perfiles (dict[str, pd.DataFrame]): Nombre del escenario → salida de
            `FayHerriotEspacial.perfil_rho` (columnas `rho` y `delta_vs_rho0`).

    Returns:
        plt.Figure: Figura con el cambio de log-verosimilitud frente a ρ = 0 y el intervalo
            del 95 % de cada escenario.

    Example:
        >>> fig = figura_perfil_rho({"knn3": modelo.perfil_rho()})  # doctest: +SKIP
    """
    fig, ax = plt.subplots(figsize=(ANCHO_FIGURA, 4.2))
    vistos = {}
    for nombre, perfil in perfiles.items():
        familia = 0 if nombre.startswith("knn") else 1
        estilo = ["-", "--", ":"][vistos.get(familia, 0) % 3]
        vistos[familia] = vistos.get(familia, 0) + 1
        ax.plot(
            perfil["rho"],
            perfil["delta_vs_rho0"],
            marker="o",
            ms=3,
            color=PALETA[familia],
            linestyle=estilo,
            label=ETIQUETA_ESCENARIO_W.get(nombre, nombre),
        )
        corte = perfil["delta_vs_rho0"].max() - 1.92
        dentro = perfil.loc[perfil["delta_vs_rho0"] >= corte, "rho"]
        ax.hlines(
            corte,
            dentro.min(),
            dentro.max(),
            color=PALETA[familia],
            lw=3,
            alpha=0.45,
        )
    ax.plot([], [], color=GRIS, lw=3, alpha=0.45, label="Intervalo del 95 % (máx − 1.92)")
    ax.axhline(0, color=GRIS, lw=0.8)
    ax.set_xlabel("ρ")
    ax.set_ylabel("Log-verosimilitud REML − valor en ρ = 0")
    ax.legend()
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
        >>> figura_validacion(cv, {"Clásico": "pred_clasico", "Espacial": "pred_espacial"})  # doctest: +SKIP
    """
    fig, ejes = plt.subplots(
        1,
        len(columnas),
        figsize=(min(ANCHO_FIGURA, 3.5 * len(columnas) + 0.4), 3.6),
        sharey=True,
    )
    ejes = np.atleast_1d(ejes)
    lim = [cv["y"].min() - 1, cv["y"].max() + 1]
    for k, (ax, (etiqueta, col)) in enumerate(zip(ejes, columnas.items())):
        ax.scatter(cv["y"], cv[col], s=22, color=PALETA[k % 2])
        ax.plot(lim, lim, color=GRIS, lw=0.8)
        ax.set_xlabel("Estimación directa (%)")
        ax.text(0.03, 0.96, etiqueta, transform=ax.transAxes, va="top")
    ejes[0].set_ylabel("Estimación sin el dominio (%)")
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
        >>> figura_mapa_prediccion(pred, dom, "PRED_ESPACIAL", "Tasa de desempleo (%)")  # doctest: +SKIP
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
        cmap=CMAP_SECUENCIAL,
        edgecolor=GRIS,
        linewidth=0.4,
    )
    ax.scatter(
        dominios.loc[caja, "LONGITUD"],
        dominios.loc[caja, "LATITUD"],
        c=dominios.loc[caja, "Y"],
        s=110,
        marker="s",
        vmin=vmin,
        vmax=vmax,
        cmap=CMAP_SECUENCIAL,
        edgecolor=GRIS_OSCURO,
    )
    for _, f in dominios[caja].iterrows():
        ax.annotate(
            f["NOMBRE"],
            (f["LONGITUD"], f["LATITUD"]),
            fontsize=8,
            xytext=(4, 4),
            textcoords="offset points",
        )
    fig.colorbar(sc, ax=ax, label=etiqueta, pad=0.03)
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
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
    fig, ejes = plt.subplots(
        1,
        len(residuos),
        figsize=(ANCHO_FIGURA, 5.0),
        sharey=True,
        layout="constrained",
    )
    ejes = np.atleast_1d(ejes)
    # Margen alrededor de los puntos para que las etiquetas quepan dentro de cada panel (M10).
    lon, lat = dominios["LONGITUD"].to_numpy(), dominios["LATITUD"].to_numpy()
    for ax, (etiqueta, valores) in zip(ejes, residuos.items()):
        sc = ax.scatter(
            lon,
            lat,
            c=np.asarray(valores),
            s=55,
            cmap=CMAP_DIVERGENTE,
            vmin=-limite,
            vmax=limite,
            edgecolor=GRIS_OSCURO,
        )
        ax.set_xlim(lon.min() - 1.6, lon.max() + 1.6)
        ax.set_ylim(lat.min() - 0.8, lat.max() + 1.2)
        ax.set_xlabel("Longitud")
        # Rótulo del panel encima del marco, fuera del área de datos.
        ax.text(0.0, 1.02, etiqueta, transform=ax.transAxes, va="bottom", ha="left")
    ejes[0].set_ylabel("Latitud")
    fig.colorbar(sc, ax=list(ejes), label="Residuo estandarizado", shrink=0.8)
    # Las etiquetas se colocan después de fijar la barra de color, cuando el tamaño de cada
    # panel ya es el final, con la colocación sin superposición del estilo común.
    for ax, valores in zip(ejes, residuos.values()):
        marca = np.abs(np.asarray(valores)) >= 1.0
        etiquetar_puntos(
            ax,
            lon[marca],
            lat[marca],
            dominios["NOMBRE"].to_numpy()[marca],
            tamano=7,
            radio_punto=8,
        )
    return fig
