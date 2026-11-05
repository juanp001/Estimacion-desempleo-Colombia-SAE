"""Diagrama de flujo general de la metodología (16 etapas en 4 fases).

No lee datos ni calcula cifras. Toma los títulos de las etapas directamente de los
`\\section{...}` de `chapters/metodologia.tex`, para que el diagrama use los mismos nombres
completos que el capítulo y que Resultados (ajuste D-42).

Uso:
    python -I diagrama_metodologia.py   (escribe img/met_flujo_general.png y .pdf)

La figura se dibuja al ancho del texto del documento (5.3 pulgadas), de modo que el tamaño de
letra del archivo es el que se lee en el PDF.
"""

import re
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

DOCUMENTO = Path(__file__).resolve().parents[2]
SALIDA = DOCUMENTO / "img"
N_ETAPAS = 16

# Paleta del documento: azul, naranja y gris, con rellenos claros de cada uno.
AZUL, NARANJA, GRIS = "#1F4E79", "#C55A11", "#7F7F7F"
RELLENO = {AZUL: "#DCE6F2", GRIS: "#EDEDED", NARANJA: "#FBE5D6"}

FASES = [
    ("Datos", AZUL),
    ("Respuesta y covariables", GRIS),
    ("Modelo clásico (benchmark)", AZUL),
    ("Modelo espacial y municipios", NARANJA),
]


def titulos_etapas(ruta, n=N_ETAPAS):
    """Lee los títulos de las etapas de la Metodología.

    Args:
        ruta (Path): archivo `metodologia.tex`.
        n (int): número de etapas que se toman, en orden de aparición.

    Returns:
        list[str]: los `n` primeros títulos de sección del capítulo.

    Ejemplo:
        >>> titulos_etapas(DOCUMENTO / "chapters" / "metodologia.tex")[0]  # doctest: +SKIP
        'Obtención de los datos'
    """
    texto = Path(ruta).read_text(encoding="utf-8")
    titulos = re.findall(r"^\\section\{(.+?)\}\s*$", texto, flags=re.MULTILINE)
    if len(titulos) < n:
        raise ValueError(f"Se esperaban {n} etapas y metodologia.tex tiene {len(titulos)}")
    return titulos[:n]


def flecha(ax, p, q, discontinua=False):
    """Dibuja una flecha entre dos puntos.

    Args:
        ax (matplotlib.axes.Axes): eje de destino.
        p (tuple[float, float]): origen.
        q (tuple[float, float]): destino.
        discontinua (bool): si es True, la línea es discontinua (paso entre fases).

    Returns:
        None
    """
    ax.add_patch(
        FancyArrowPatch(
            p,
            q,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=0.8,
            color=GRIS,
            linestyle=(0, (3, 2)) if discontinua else "-",
            shrinkA=0,
            shrinkB=0,
        )
    )


def main():
    """Dibuja el diagrama y lo guarda en PNG y PDF.

    Returns:
        None
    """
    titulos = titulos_etapas(DOCUMENTO / "chapters" / "metodologia.tex")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

    ancho_fig, alto_fig = 5.3, 7.2
    fig, ax = plt.subplots(figsize=(ancho_fig, alto_fig))
    ax.set_xlim(0, ancho_fig + 0.05)
    ax.set_ylim(0, alto_fig)
    ax.axis("off")

    margen = 0.20
    ancho, alto = 1.17, 1.12
    paso_x = (ancho_fig - margen - 4 * ancho) / 3 + ancho
    x0 = margen + ancho / 2
    alto_fila = alto_fig / 4
    centros = []
    for i, (fase, color) in enumerate(FASES):
        y_titulo = alto_fig - i * alto_fila - 0.12
        ax.text(margen, y_titulo, fase, ha="left", va="top", fontsize=9, color=color, weight="bold")
        y = y_titulo - 0.30 - alto / 2
        fila = []
        for j in range(4):
            k = 4 * i + j
            x = x0 + j * paso_x
            ax.add_patch(
                FancyBboxPatch(
                    (x - ancho / 2, y - alto / 2),
                    ancho,
                    alto,
                    boxstyle="round,pad=0.0,rounding_size=0.06",
                    linewidth=1.0,
                    edgecolor=color,
                    facecolor=RELLENO[color],
                )
            )
            texto = f"{k + 1}. " + titulos[k]
            # El nombre del procedimiento se parte solo después de «dejar-un-».
            texto = texto.replace("dejar-un-dominio-fuera", "dejar-un- dominio-fuera")
            lineas = textwrap.wrap(texto, 15, break_on_hyphens=False, break_long_words=False)
            lineas = [linea.replace("un- ", "un-") for linea in lineas]
            ax.text(x, y, "\n".join(lineas), ha="center", va="center", fontsize=8, linespacing=1.15)
            fila.append((x, y))
        centros.append(fila)

    sep = paso_x - ancho
    for fila in centros:
        for (x1, y1), (x2, _) in zip(fila[:-1], fila[1:]):
            flecha(ax, (x1 + ancho / 2, y1), (x1 + ancho / 2 + sep, y1))
    # Paso de una fase a la siguiente: baja del último cuadro, cruza por el margen izquierdo y
    # entra por el lado al primer cuadro de la fila siguiente.
    for fila, siguiente in zip(centros[:-1], centros[1:]):
        (xa, ya), (xb, yb) = fila[-1], siguiente[0]
        y_medio = ya - alto / 2 - 0.10
        x_margen = margen / 2
        ax.plot(
            [xa, xa, x_margen, x_margen],
            [ya - alto / 2, y_medio, y_medio, yb],
            color=GRIS,
            lw=0.8,
            ls=(0, (3, 2)),
        )
        flecha(ax, (x_margen, yb), (xb - ancho / 2, yb), discontinua=True)

    for ext in ("png", "pdf"):
        fig.savefig(SALIDA / f"met_flujo_general.{ext}", dpi=300, bbox_inches="tight")
    print("ok:", SALIDA / "met_flujo_general.png")


if __name__ == "__main__":
    main()
