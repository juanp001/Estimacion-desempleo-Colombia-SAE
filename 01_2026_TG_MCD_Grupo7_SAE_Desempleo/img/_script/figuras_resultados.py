"""Figuras de Resultados con el estilo del documento (tres colores base, sin título interno).

Uso:
    python -I figuras_resultados.py <carpeta_datos> <carpeta_salidas_calculos> <carpeta_img> [<carpeta_shp>]

Solo lee CSV ya descargados con consultas de solo lectura (`_trabajo/calculos/datos`) y, para el
mapa, los polígonos municipales del MGN 2018 (`data/poligonos_municipales/SHP_MGN2018_INTGRD_MPIO`
del repositorio); no recalcula ninguna cifra.

Figuras:
    res_espacial_estimaciones.png  <- tesis.modelo.fhe_prediccion_objetivo y la tabla del SEBLUP de
                                      los dominios (tesis.modelo.fhe_seblup_dominios si ya se
                                      descargó como fhe_seblup_dominios.csv; si no, la salida del
                                      cálculo propio C1, c1_seblup_dominios.csv)
    res_mapa_municipios.png        <- tesis.modelo.fay_herriot_estimaciones_finales y
                                      tesis.modelo.fhe_prediccion_objetivo, sobre los polígonos
                                      municipales de Cauca y Valle del Cauca

Las figuras se dibujan al ancho del texto del documento (5.3 pulgadas) para que el tamaño de letra
del archivo sea el que se lee en el PDF (9 puntos).
"""

import struct
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

# Paleta del documento (hoja de estilo de la revisión): azul, naranja y gris.
AZUL, NARANJA, GRIS = "#1F4E79", "#C55A11", "#7F7F7F"
AZUL_CLARO, NARANJA_CLARO, GRIS_CLARO = "#9DB7D2", "#E8B08C", "#D9D9D9"
ANCHO_TEXTO = 5.3  # pulgadas, \textwidth de la clase del documento
DPI = 300
DEPARTAMENTOS = ("19", "76")

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.labelsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#E6E6E6",
        "grid.linewidth": 0.6,
    }
)


def leer_poligonos(carpeta, departamentos=DEPARTAMENTOS):
    """Lee los polígonos municipales del MGN 2018 de los departamentos indicados.

    Lector mínimo del formato shapefile (tipo polígono) y de su tabla .dbf, para no depender de
    librerías geográficas.

    Args:
        carpeta (Path): carpeta con MGN_ANM_MPIOS.shp y MGN_ANM_MPIOS.dbf.
        departamentos (tuple[str]): códigos DIVIPOLA de los departamentos que se conservan.

    Returns:
        dict[str, list[np.ndarray]]: código DIVIPOLA de cinco dígitos → lista de anillos, cada uno
        un arreglo (n, 2) de longitud y latitud.

    Ejemplo:
        >>> pol = leer_poligonos(Path("data/poligonos_municipales/SHP_MGN2018_INTGRD_MPIO"))  # doctest: +SKIP
        >>> len([c for c in pol if c.startswith("76")])  # doctest: +SKIP
        42
    """
    carpeta = Path(carpeta)
    with open(carpeta / "MGN_ANM_MPIOS.dbf", "rb") as f:
        cab = f.read(32)
        n_reg = struct.unpack("<I", cab[4:8])[0]
        largo_cab = struct.unpack("<H", cab[8:10])[0]
        largo_reg = struct.unpack("<H", cab[10:12])[0]
        campos = []
        while True:
            d = f.read(32)
            if d[0] == 0x0D:
                break
            campos.append((d[:11].split(b"\0")[0].decode(), d[16]))
        f.seek(largo_cab)
        codigos = []
        for _ in range(n_reg):
            reg = f.read(largo_reg)
            pos, valores = 1, {}
            for nombre, largo in campos:
                valores[nombre] = reg[pos : pos + largo].decode("latin-1").strip()
                pos += largo
            codigos.append(valores["MPIO_CDPMP"])

    poligonos = {}
    with open(carpeta / "MGN_ANM_MPIOS.shp", "rb") as f:
        f.seek(100)
        for codigo in codigos:
            cab = f.read(8)
            if len(cab) < 8:
                break
            largo = struct.unpack(">i", cab[4:8])[0] * 2
            contenido = f.read(largo)
            if codigo[:2] not in departamentos:
                continue
            tipo = struct.unpack("<i", contenido[:4])[0]
            if tipo != 5:
                continue
            n_partes, n_puntos = struct.unpack("<2i", contenido[36:44])
            partes = list(struct.unpack(f"<{n_partes}i", contenido[44 : 44 + 4 * n_partes]))
            ini = 44 + 4 * n_partes
            puntos = np.frombuffer(contenido[ini : ini + 16 * n_puntos], dtype="<f8").reshape(-1, 2)
            limites = partes + [n_puntos]
            poligonos[codigo] = [puntos[a:b] for a, b in zip(limites[:-1], limites[1:])]
    return poligonos


def leer_dominios(datos, calc):
    """Lee el EBLUP y el SEBLUP de los 23 dominios.

    Usa la tabla del cuaderno espacial si ya se descargó y, si no, la salida del cálculo propio C1.

    Args:
        datos (Path): carpeta de CSV descargados de las tablas tesis.*.
        calc (Path): carpeta de salidas de los cálculos propios.

    Returns:
        pd.DataFrame: columnas EBLUP y SEBLUP, una fila por dominio.
    """
    tabla = Path(datos) / "fhe_seblup_dominios.csv"
    if tabla.exists():
        dom = pd.read_csv(tabla, dtype={"CODIGO_DOMINIO": str})
    else:
        dom = pd.read_csv(Path(calc) / "c1_seblup_dominios.csv", dtype={"CODIGO_DOMINIO": str})
    return dom[["EBLUP", "SEBLUP"]]


def figura_estimaciones(fpo, dom, salida):
    """Dispersión de las estimaciones clásica y espacial y diferencia según la distancia.

    Args:
        fpo (pd.DataFrame): fhe_prediccion_objetivo (83 municipios).
        dom (pd.DataFrame): EBLUP y SEBLUP de los 23 dominios.
        salida (Path): archivo PNG.

    Returns:
        None: escribe la figura en `salida`.
    """
    fig, ax = plt.subplots(1, 2, figsize=(ANCHO_TEXTO, 2.9))
    lim = [8, 33]
    ax[0].plot(lim, lim, color=GRIS, lw=0.8, ls="--")
    ax[0].scatter(fpo["PRED_CLASICO"], fpo["PRED_ESPACIAL"], s=12, color=AZUL, label="Municipios (83)")
    ax[0].scatter(dom["EBLUP"], dom["SEBLUP"], s=14, marker="s", color=NARANJA, label="Dominios (23)")
    ax[0].set_xlabel("Estimación clásica (%)")
    ax[0].set_ylabel("Estimación espacial (%)")
    ax[0].set_xlim(lim)
    ax[0].set_ylim(lim)
    ax[0].legend(frameon=False, loc="upper left", handletextpad=0.2)

    ax[1].axhline(0, color=GRIS, lw=0.8, ls="--")
    ax[1].scatter(fpo["KM_DOMINIO_CERCANO"], fpo["DIF_ESPACIAL_VS_CLASICO"], s=12, color=AZUL)
    grandes = fpo[fpo["DIF_ESPACIAL_VS_CLASICO"].abs() > 0.5].copy()
    # Cali y Yumbo comparten casi el mismo valor: se rotulan juntos.
    juntos = grandes["MUNICIPIO"].isin(["Cali", "Yumbo"])
    if juntos.sum() == 2:
        filas = grandes[juntos]
        ax[1].annotate(
            "Cali y Yumbo",
            (filas["KM_DOMINIO_CERCANO"].max(), filas["DIF_ESPACIAL_VS_CLASICO"].mean()),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
        )
        grandes = grandes[~juntos]
    # Los demás se rotulan en una columna a la derecha, con una línea guía a su punto.
    x_texto = 62.0
    for signo, y0, paso in ((1, 1.85, -0.3), (-1, -1.05, -0.3)):
        grupo = grandes[np.sign(grandes["DIF_ESPACIAL_VS_CLASICO"]) == signo]
        grupo = grupo.sort_values("DIF_ESPACIAL_VS_CLASICO", ascending=(signo < 0))
        for i, (_, f) in enumerate(grupo.iterrows()):
            ax[1].annotate(
                f["MUNICIPIO"],
                (f["KM_DOMINIO_CERCANO"], f["DIF_ESPACIAL_VS_CLASICO"]),
                xytext=(x_texto, y0 + i * paso),
                textcoords="data",
                va="center",
                arrowprops={"arrowstyle": "-", "color": GRIS, "lw": 0.5, "shrinkA": 0, "shrinkB": 2},
            )
    ax[1].set_ylim(-3.0, 2.05)
    ax[1].set_xlabel("Distancia al dominio más cercano (km)")
    ax[1].set_ylabel("Espacial menos clásica (pp)")
    fig.tight_layout(w_pad=1.2)
    fig.savefig(salida, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def dibujar(ax, poligonos, codigos, colores, borde="white", ancho=0.3):
    """Dibuja un conjunto de municipios rellenos con el color de cada uno.

    Args:
        ax (matplotlib.axes.Axes): eje de destino.
        poligonos (dict): salida de `leer_poligonos`.
        codigos (list[str]): códigos DIVIPOLA en el mismo orden que `colores`.
        colores (list): color de relleno de cada municipio.
        borde (str): color de los límites municipales.
        ancho (float): grosor de los límites.

    Returns:
        None
    """
    verts, caras = [], []
    for codigo, color in zip(codigos, colores):
        for anillo in poligonos.get(codigo, []):
            verts.append(anillo)
            caras.append(color)
    ax.add_collection(PolyCollection(verts, facecolors=caras, edgecolors=borde, linewidths=ancho))


def figura_mapas(fin, fpo, poligonos, salida):
    """Tres mapas municipales: tasa final, clase de CV con extrapolación y efecto espacial.

    Args:
        fin (pd.DataFrame): fay_herriot_estimaciones_finales, nivel municipio (83 filas).
        fpo (pd.DataFrame): fhe_prediccion_objetivo (efecto espacial).
        poligonos (dict): polígonos de Cauca y Valle del Cauca (`leer_poligonos`).
        salida (Path): archivo PNG.

    Returns:
        None: escribe la figura en `salida`.
    """
    m = fin.merge(fpo[["CODIGO_MUNICIPIO", "EFECTO_ESPACIAL"]], left_on="CODIGO", right_on="CODIGO_MUNICIPIO")
    sin_estimacion = [c for c in poligonos if c not in set(m["CODIGO"])]

    fig = plt.figure(figsize=(ANCHO_TEXTO, 4.6))
    gs = fig.add_gridspec(
        2, 3, height_ratios=[1, 0.05], hspace=0.06, wspace=0.10, left=0.03, right=0.97, top=0.99, bottom=0.20
    )
    ejes = [fig.add_subplot(gs[0, j]) for j in range(3)]
    todos = np.vstack([a for anillos in poligonos.values() for a in anillos])
    for ax in ejes:
        dibujar(ax, poligonos, sin_estimacion, [GRIS_CLARO] * len(sin_estimacion))
        ax.set_xlim(todos[:, 0].min() - 0.05, todos[:, 0].max() + 0.05)
        ax.set_ylim(todos[:, 1].min() - 0.05, todos[:, 1].max() + 0.05)
        ax.set_aspect("equal")
        ax.axis("off")

    # Panel 1: tasa de desempleo estimada.
    cmap = LinearSegmentedColormap.from_list("azul", ["#E3ECF5", AZUL])
    vmin, vmax = m["TASA_DESEMPLEO_PCT"].min(), m["TASA_DESEMPLEO_PCT"].max()
    norma = plt.Normalize(vmin, vmax)
    dibujar(ejes[0], poligonos, list(m["CODIGO"]), list(cmap(norma(m["TASA_DESEMPLEO_PCT"]))))
    cb = fig.colorbar(plt.cm.ScalarMappable(norma, cmap), cax=fig.add_subplot(gs[1, 0]), orientation="horizontal")
    cb.set_label("Tasa estimada (%)")

    # Panel 2: clase de CV y estado de extrapolación.
    ext = m["EXTRAPOLA"].astype(str).str.lower() == "true"
    noconf = m["CONFIABILIDAD"] == "No confiable"
    clases = [
        (~ext & ~noconf, AZUL, "Aceptable"),
        (~ext & noconf, AZUL_CLARO, "No confiable"),
        (ext & ~noconf, NARANJA, "Aceptable, extrapola"),
        (ext & noconf, NARANJA_CLARO, "No confiable, extrapola"),
    ]
    color_mun = pd.Series(GRIS_CLARO, index=m.index)
    for mascara, color, _ in clases:
        color_mun[mascara] = color
    dibujar(ejes[1], poligonos, list(m["CODIGO"]), list(color_mun))
    manejadores = [Patch(facecolor=c, label=f"{t} ({int(k.sum())})") for k, c, t in clases]
    manejadores.append(Patch(facecolor=GRIS_CLARO, label="Popayán, dominio con encuesta"))
    fig.legend(
        handles=manejadores,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.075),
        frameon=False,
        ncol=2,
        handlelength=1.0,
        columnspacing=1.5,
    )

    # Panel 3: efecto espacial (estimación espacial menos sintética).
    lim = float(np.abs(m["EFECTO_ESPACIAL"]).max())
    cmap2 = LinearSegmentedColormap.from_list("div", [AZUL, "#F2F2F2", NARANJA])
    norma2 = TwoSlopeNorm(vcenter=0.0, vmin=-lim, vmax=lim)
    dibujar(ejes[2], poligonos, list(m["CODIGO"]), list(cmap2(norma2(m["EFECTO_ESPACIAL"]))))
    cb2 = fig.colorbar(plt.cm.ScalarMappable(norma2, cmap2), cax=fig.add_subplot(gs[1, 2]), orientation="horizontal")
    cb2.set_label("Efecto espacial (pp)")
    for barra in (cb, cb2):
        barra.ax.grid(False)
        barra.outline.set_linewidth(0.5)

    fig.savefig(salida, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main():
    """Genera las dos figuras en la carpeta de imágenes.

    Returns:
        None
    """
    datos, calc, img = map(Path, sys.argv[1:4])
    raiz = Path(__file__).resolve().parents[3]
    shp = Path(sys.argv[4]) if len(sys.argv) > 4 else raiz / "data" / "poligonos_municipales" / "SHP_MGN2018_INTGRD_MPIO"
    fpo = pd.read_csv(datos / "fhe_prediccion_objetivo.csv", dtype={"CODIGO_MUNICIPIO": str})
    fin = pd.read_csv(datos / "estimaciones_finales.csv", dtype={"CODIGO": str})
    fin = fin[fin["NIVEL"] == "MUNICIPIO"].copy()
    figura_estimaciones(fpo, leer_dominios(datos, calc), img / "res_espacial_estimaciones.png")
    figura_mapas(fin, fpo, leer_poligonos(shp), img / "res_mapa_municipios.png")
    print("ok")


if __name__ == "__main__":
    main()
