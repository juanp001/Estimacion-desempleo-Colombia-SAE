"""Estilo común de las figuras del análisis y del modelo (D-11 y D-12 de la revisión del documento).

Todas las figuras que llegan al documento salen de los notebooks, así que la paleta, la letra y
la resolución se fijan aquí una sola vez:

- **Paleta de tres colores base**: azul `AZUL` (serie principal), naranja `NARANJA` (lo que se
  resalta o se contrasta) y gris `GRIS` (referencias: rectas, umbrales, puntos de fondo), con
  sus versiones claras. Las secuencias usan degradados de azul (`CMAP_SECUENCIAL`,
  `tonos_azules`) y las magnitudes con signo, el degradado azul-blanco-naranja
  (`CMAP_DIVERGENTE`).
- **Letra**: 10 pt en ejes y 9 pt en marcas y leyendas, para que una figura de `ANCHO_FIGURA`
  pulgadas, insertada al ancho del texto, conserve el texto legible al 100 %.
- **Resolución**: `DPI` = 200 al guardar.
- Sin títulos internos: la descripción va en el caption del documento.

`aplicar_estilo()` se llama al importar los módulos de figuras (`analisis/shared/descriptivos.py`,
`modelo/shared/figuras.py`), de modo que basta con importarlos para que el notebook use este
estilo.
"""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from cycler import cycler
from matplotlib.colors import LinearSegmentedColormap

AZUL = "#1F4E79"
NARANJA = "#C55A11"
GRIS = "#7F7F7F"
AZUL_CLARO = "#9DC3E6"
NARANJA_CLARO = "#F4B183"
GRIS_CLARO = "#D9D9D9"
GRIS_OSCURO = "#404040"
PALETA = [AZUL, NARANJA, GRIS]

DPI = 200
TAMANO_LETRA = 10
TAMANO_MARCAS = 9
# Ancho de referencia (pulgadas) de una figura que ocupa el ancho del texto del documento.
ANCHO_FIGURA = 7.0

CMAP_SECUENCIAL = LinearSegmentedColormap.from_list(
    "tesis_secuencial", ["#F2F6FA", AZUL_CLARO, AZUL]
)
CMAP_DIVERGENTE = LinearSegmentedColormap.from_list(
    "tesis_divergente", [AZUL, "#F7F7F7", NARANJA]
)


def aplicar_estilo() -> None:
    """Fija en `matplotlib.rcParams` la paleta, la letra, la grilla y la resolución comunes.

    Es idempotente: llamarla varias veces deja el mismo estado.

    Returns:
        None: modifica la configuración global de matplotlib.

    Example:
        >>> aplicar_estilo()
        >>> matplotlib.rcParams["savefig.dpi"]
        200.0
        >>> matplotlib.rcParams["axes.prop_cycle"].by_key()["color"][:2]
        ['#1F4E79', '#C55A11']

    Casos de uso:
        Al importar los módulos de figuras del análisis y del modelo.
    """
    matplotlib.rcParams.update(
        {
            "font.size": TAMANO_LETRA,
            "axes.labelsize": TAMANO_LETRA,
            "axes.titlesize": TAMANO_LETRA,
            "xtick.labelsize": TAMANO_MARCAS,
            "ytick.labelsize": TAMANO_MARCAS,
            "legend.fontsize": TAMANO_MARCAS,
            "legend.frameon": False,
            "axes.prop_cycle": cycler(
                color=[AZUL, NARANJA, GRIS, AZUL_CLARO, NARANJA_CLARO, GRIS_OSCURO]
            ),
            "axes.grid": True,
            "grid.color": GRIS_CLARO,
            "grid.linestyle": "-",
            "grid.linewidth": 0.6,
            "grid.alpha": 1.0,
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": GRIS,
            "image.cmap": "tesis_secuencial",
            "savefig.dpi": DPI,
            "savefig.bbox": "tight",
        }
    )


def _registrar_mapas() -> None:
    """Registra los mapas de color propios para poder usarlos por nombre.

    Returns:
        None: agrega `tesis_secuencial` y `tesis_divergente` al registro de matplotlib si
            aún no están.

    Casos de uso:
        Se llama una vez al importar el módulo.
    """
    for cmap in (CMAP_SECUENCIAL, CMAP_DIVERGENTE):
        if cmap.name not in matplotlib.colormaps:
            matplotlib.colormaps.register(cmap)


def tonos_azules(n: int) -> list:
    """Devuelve `n` tonos de azul, de claro a oscuro, para series ordenadas.

    Args:
        n (int): Número de tonos.

    Returns:
        list[tuple]: Colores RGBA, del más claro al más oscuro.

    Example:
        >>> len(tonos_azules(4))
        4

    Casos de uso:
        Escenarios ordenados por magnitud (p. ej. ψ × k en la sensibilidad de la varianza).
    """
    if n <= 0:
        return []
    return [CMAP_SECUENCIAL(v) for v in np.linspace(0.35, 1.0, n)]


def guardar(fig, ruta: str) -> str:
    """Guarda una figura como PNG con la resolución común.

    Args:
        fig (matplotlib.figure.Figure): Figura a guardar.
        ruta (str): Ruta del archivo, con extensión.

    Returns:
        str: La misma ruta.

    Example:
        >>> import os, tempfile
        >>> fig, _ = plt.subplots()
        >>> os.path.basename(guardar(fig, os.path.join(tempfile.mkdtemp(), "x.png")))
        'x.png'

    Casos de uso:
        `guardar_figura` del análisis y del modelo.
    """
    fig.savefig(ruta, dpi=DPI, bbox_inches="tight")
    return ruta


def etiquetar_puntos(
    ax,
    xs,
    ys,
    etiquetas,
    tamano: int = 8,
    color: str = GRIS_OSCURO,
    lineas_h=(),
    lineas_v=(),
    obstaculos_ejes=(),
    radio_punto: float = 6.0,
):
    """Anota puntos de un diagrama de dispersión evitando que los textos se superpongan.

    Prueba, para cada etiqueta, varias posiciones alrededor del punto y elige la primera cuyo
    recuadro no choca con los ya colocados, con los puntos, con las líneas de referencia
    indicadas ni con los recuadros reservados. Si ninguna queda libre, usa la de menor
    superposición.

    Args:
        ax (matplotlib.axes.Axes): Ejes con el diagrama ya dibujado.
        xs (array-like): Coordenadas x de los puntos.
        ys (array-like): Coordenadas y de los puntos.
        etiquetas (array-like): Texto de cada punto.
        tamano (int): Tamaño de letra de las etiquetas, en puntos.
        color (str): Color del texto.
        lineas_h (iterable[float]): Valores y de líneas horizontales de referencia (umbrales)
            que el texto no debe tapar.
        lineas_v (iterable[float]): Valores x de líneas verticales de referencia.
        obstaculos_ejes (iterable[tuple]): Recuadros reservados en coordenadas de ejes
            (x0, y0, x1, y1, entre 0 y 1), por ejemplo la zona de una leyenda.
        radio_punto (float): Medio lado, en píxeles, del cuadrado que protege cada punto;
            conviene subirlo con marcadores grandes.

    Returns:
        list: Los objetos `matplotlib.text.Annotation` creados.

    Example:
        >>> fig, ax = plt.subplots()
        >>> _ = ax.scatter([0, 0.01, 1], [0, 0.01, 1])
        >>> len(etiquetar_puntos(ax, [0, 0.01, 1], [0, 0.01, 1], ["a", "b", "c"]))
        3

    Casos de uso:
        Nombres de dominios en el plano de robustez y en el efecto suavizador.
    """
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    desplazamientos = [
        (5, 3, "left", "bottom"),
        (5, -3, "left", "top"),
        (-5, 3, "right", "bottom"),
        (-5, -3, "right", "top"),
        (0, 8, "center", "bottom"),
        (0, -8, "center", "top"),
        (9, 0, "left", "center"),
        (-9, 0, "right", "center"),
        (5, 14, "left", "bottom"),
        (-5, -14, "right", "top"),
        (5, -14, "left", "top"),
        (-5, 14, "right", "bottom"),
    ]
    # Posiciones lejanas en ocho direcciones y tres distancias, con línea guía, para las
    # zonas con muchos puntos (M12).
    for r in (26, 42, 60):
        for ang in range(0, 360, 45):
            cx, cy = np.cos(np.radians(ang)), np.sin(np.radians(ang))
            ha = "left" if cx > 0.3 else ("right" if cx < -0.3 else "center")
            va = "bottom" if cy > 0.3 else ("top" if cy < -0.3 else "center")
            desplazamientos.append((round(r * cx), round(r * cy), ha, va))

    def _solape(a, b) -> float:
        """Área de la intersección de dos recuadros en píxeles."""
        return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(
            0.0, min(a[3], b[3]) - max(a[1], b[1])
        )

    # Obstáculos: los propios puntos (un cuadrado de ~6 px alrededor de cada uno).
    pixeles = ax.transData.transform(np.column_stack([xs, ys]).astype(float))
    radio = float(radio_punto)
    puntos = [(px - radio, py - radio, px + radio, py + radio) for px, py in pixeles]
    marco = ax.get_window_extent(renderer)
    area_marco = (marco.x0, marco.y0, marco.x1, marco.y1)
    # Líneas de referencia como franjas de ~3 px y recuadros reservados, en píxeles. Pesan
    # más que un choque con otro texto: una etiqueta cruzada por un umbral se lee mal.
    franja, peso_linea = 3.0, 25.0
    fijos = []
    for yv in lineas_h:
        py = ax.transData.transform((ax.get_xlim()[0], yv))[1]
        fijos.append((marco.x0, py - franja, marco.x1, py + franja))
    for xv in lineas_v:
        px = ax.transData.transform((xv, ax.get_ylim()[0]))[0]
        fijos.append((px - franja, marco.y0, px + franja, marco.y1))
    for x0, y0, x1, y1 in obstaculos_ejes:
        (a0, b0), (a1, b1) = ax.transAxes.transform([(x0, y0), (x1, y1)])
        fijos.append((a0, b0, a1, b1))

    colocadas, cajas = [], []
    for i, (x, y, texto) in enumerate(zip(xs, ys, etiquetas)):
        otros_puntos = puntos[:i] + puntos[i + 1 :]
        mejor, mejor_choque = None, None
        for dx, dy, ha, va in desplazamientos:
            anotacion = ax.annotate(
                texto,
                (x, y),
                textcoords="offset points",
                xytext=(dx, dy),
                ha=ha,
                va=va,
                fontsize=tamano,
                color=color,
                arrowprops=(
                    dict(arrowstyle="-", color=GRIS, lw=0.5, shrinkA=0, shrinkB=3)
                    if np.hypot(dx, dy) >= 20
                    else None
                ),
            )
            e = anotacion.get_window_extent(renderer)
            caja = (e.x0, e.y0, e.x1, e.y1)
            area = (e.x1 - e.x0) * (e.y1 - e.y0)
            # Choque con etiquetas ya puestas y con los puntos, más lo que salga de los ejes.
            choque = (
                sum(_solape(caja, c) for c in cajas)
                + sum(_solape(caja, p) for p in otros_puntos)
                + peso_linea * sum(_solape(caja, f) for f in fijos)
                + 2 * (area - _solape(caja, area_marco))
            )
            if mejor is None or choque < mejor_choque:
                if mejor is not None:
                    mejor[0].remove()
                mejor, mejor_choque = (anotacion, caja), choque
            else:
                anotacion.remove()
            if choque <= 0:
                break
        colocadas.append(mejor[0])
        cajas.append(mejor[1])
    return colocadas


_registrar_mapas()
aplicar_estilo()
