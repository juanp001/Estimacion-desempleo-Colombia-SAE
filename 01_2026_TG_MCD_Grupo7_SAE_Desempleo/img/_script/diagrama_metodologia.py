"""Diagrama de flujo general de la metodología (16 etapas en 4 fases).

No lee datos ni calcula cifras: solo dibuja los títulos de las etapas de `metodologia.tex`.
Uso: python diagrama_metodologia.py   (escribe img/met_flujo_general.png y .pdf)
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

SALIDA = Path(__file__).resolve().parents[1]

# Paleta del documento: tres colores base (azul, gris, naranja).
AZUL, GRIS, NARANJA = "#1f4e79", "#595959", "#c55a11"
RELLENO = {AZUL: "#dce6f2", GRIS: "#ededed", NARANJA: "#fbe5d6"}

FASES = [
    (
        "Datos",
        AZUL,
        [
            "1. Obtención\nde los datos",
            "2. Limpieza,\nestandarización\ny consolidación",
            "3. Faltantes y\nvalores atípicos",
            "4. Dominios y\ncorrespondencia\ngeográfica",
        ],
    ),
    (
        "Respuesta y\ncovariables",
        GRIS,
        [
            "5. Estimación\ndirecta",
            "6. Construcción y\nagregación de\ncovariables",
            "7. Pre-filtrado\nde covariables",
            "8. Análisis\ndescriptivo",
        ],
    ),
    (
        "Modelo clásico\n(benchmark)",
        AZUL,
        [
            "9. Selección de\ncovariables",
            "10. Ajuste y\nselección del\nFay-Herriot clásico",
            "11. Supuestos y\nsensibilidad",
            "12. Validación\npredictiva dejar-\nun-dominio-fuera",
        ],
    ),
    (
        "Espacial y\nmunicipios",
        NARANJA,
        [
            "13. Fay-Herriot\nespacial y\ncomparación",
            "14. Municipios sin\ncobertura muestral",
            "15. Benchmarking y\nconsolidación",
            "16. Patrones\nespaciales",
        ],
    ),
]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
fig, ax = plt.subplots(figsize=(11.2, 6.6))
ax.set_xlim(0, 11.2)
ax.set_ylim(0, 6.6)
ax.axis("off")

ANCHO, ALTO = 1.85, 1.0
X0, PASO_X = 2.85, 2.15
Y_FILAS = [5.55, 3.95, 2.35, 0.75]

centros = []
for (fase, color, etapas), y in zip(FASES, Y_FILAS):
    ax.text(0.95, y, fase, ha="center", va="center", fontsize=10.5, color=color, weight="bold")
    fila = []
    for j, etapa in enumerate(etapas):
        x = X0 + j * PASO_X
        ax.add_patch(
            FancyBboxPatch(
                (x - ANCHO / 2, y - ALTO / 2),
                ANCHO,
                ALTO,
                boxstyle="round,pad=0.02,rounding_size=0.08",
                linewidth=1.3,
                edgecolor=color,
                facecolor=RELLENO[color],
            )
        )
        ax.text(x, y, etapa, ha="center", va="center", fontsize=9.5)
        fila.append((x, y))
    centros.append(fila)


def flecha(p, q):
    """Dibuja una flecha recta entre dos puntos."""
    ax.add_patch(
        FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=12, linewidth=1.1, color=GRIS)
    )


for fila in centros:
    for (x1, y1), (x2, _) in zip(fila[:-1], fila[1:]):
        flecha((x1 + ANCHO / 2, y1), (x2 - ANCHO / 2, y1))
# Paso de una fase a la siguiente: del último cuadro de la fila al primero de la siguiente.
for fila, siguiente in zip(centros[:-1], centros[1:]):
    (xa, ya), (xb, yb) = fila[-1], siguiente[0]
    ax.add_patch(
        FancyArrowPatch(
            (xa, ya - ALTO / 2),
            (xb, yb + ALTO / 2),
            connectionstyle="arc3,rad=0.0",
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.1,
            color=GRIS,
            linestyle=(0, (4, 2)),
        )
    )

fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(SALIDA / f"met_flujo_general.{ext}", dpi=300, bbox_inches="tight")
print("ok:", SALIDA / "met_flujo_general.png")
