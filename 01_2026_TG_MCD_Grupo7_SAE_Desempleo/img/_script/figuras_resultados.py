"""Figuras nuevas de Resultados con un estilo único (tres colores base, sin título interno).

Uso: python -I figuras_resultados.py <carpeta_datos> <carpeta_salidas_calculos> <carpeta_img>

Solo lee CSV ya descargados con consultas de solo lectura (`_trabajo/calculos/datos`) y la salida
del cálculo propio C1 (`_trabajo/calculos/salidas`); no recalcula ninguna cifra.

Figuras:
    res_espacial_estimaciones.png  ← tesis.modelo.fhe_prediccion_objetivo y salida C1
    res_mapa_municipios.png        ← tesis.modelo.fay_herriot_estimaciones_finales y
                                     tesis.modelo.fhe_prediccion_objetivo (coordenadas, efecto)
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

AZUL, NARANJA, GRIS = "#1f4e79", "#d9822b", "#8c8c8c"
plt.rcParams.update(
    {"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
)


def figura_estimaciones(fpo, dom, salida):
    """Dispersión de las estimaciones clásica y espacial (dominios y municipios) y sus diferencias.

    Args:
        fpo (pd.DataFrame): fhe_prediccion_objetivo.
        dom (pd.DataFrame): salida C1 por dominio (EBLUP, SEBLUP).
        salida (Path): archivo PNG.
    """
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.2))
    lim = [8, 33]
    ax[0].plot(lim, lim, color=GRIS, lw=1, ls="--")
    ax[0].scatter(fpo["PRED_CLASICO"], fpo["PRED_ESPACIAL"], s=22, color=AZUL, label="Municipios (83)")
    ax[0].scatter(dom["EBLUP"], dom["SEBLUP"], s=26, marker="s", color=NARANJA, label="Dominios (23)")
    ax[0].set_xlabel("Estimación clásica (%)")
    ax[0].set_ylabel("Estimación espacial (%)")
    ax[0].legend(frameon=False, loc="upper left")
    ax[1].axhline(0, color=GRIS, lw=1, ls="--")
    ax[1].scatter(fpo["KM_DOMINIO_CERCANO"], fpo["DIF_ESPACIAL_VS_CLASICO"], s=22, color=AZUL)
    for _, f in fpo[fpo["DIF_ESPACIAL_VS_CLASICO"].abs() > 0.5].iterrows():
        ax[1].annotate(f["MUNICIPIO"], (f["KM_DOMINIO_CERCANO"], f["DIF_ESPACIAL_VS_CLASICO"]),
                       fontsize=8, xytext=(4, 2), textcoords="offset points")
    ax[1].set_xlabel("Distancia al dominio con encuesta más cercano (km)")
    ax[1].set_ylabel("Espacial − clásica (pp)")
    fig.tight_layout()
    fig.savefig(salida, dpi=200)
    plt.close(fig)


def figura_mapas(fin, fpo, salida):
    """Tres paneles por coordenadas de cabecera: tasa final, CV y extrapolación, efecto espacial.

    Args:
        fin (pd.DataFrame): fay_herriot_estimaciones_finales (nivel municipio).
        fpo (pd.DataFrame): fhe_prediccion_objetivo (coordenadas y efecto espacial).
        salida (Path): archivo PNG.
    """
    m = fin.merge(fpo[["CODIGO_MUNICIPIO", "LATITUD", "LONGITUD", "EFECTO_ESPACIAL"]],
                  left_on="CODIGO", right_on="CODIGO_MUNICIPIO")
    fig, ax = plt.subplots(1, 3, figsize=(12, 5.2), sharey=True)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("azul", ["#dfe8f1", AZUL])
    sc = ax[0].scatter(m["LONGITUD"], m["LATITUD"], c=m["TASA_DESEMPLEO_PCT"], cmap=cmap, s=40,
                       edgecolor="k", lw=0.3)
    fig.colorbar(sc, ax=ax[0], fraction=0.05, label="Tasa de desempleo estimada (%)")
    ext = m["EXTRAPOLA"].astype(str).str.lower() == "true"
    noconf = m["CONFIABILIDAD"] == "No confiable"
    for mask, color, mk, lab in [
        (~ext & ~noconf, AZUL, "o", "Aceptable, dentro del rango"),
        (~ext & noconf, GRIS, "o", "No confiable, dentro del rango"),
        (ext & ~noconf, NARANJA, "^", "Aceptable, extrapolado"),
        (ext & noconf, NARANJA, "v", "No confiable, extrapolado"),
    ]:
        ax[1].scatter(m.loc[mask, "LONGITUD"], m.loc[mask, "LATITUD"], s=40, c=color, marker=mk,
                      edgecolor="k", lw=0.3, label=f"{lab} ({int(mask.sum())})")
    ax[1].legend(frameon=False, fontsize=8, loc="lower left")
    lim = np.abs(m["EFECTO_ESPACIAL"]).max()
    cmap2 = matplotlib.colors.LinearSegmentedColormap.from_list("div", [AZUL, "#f2f2f2", NARANJA])
    sc2 = ax[2].scatter(m["LONGITUD"], m["LATITUD"], c=m["EFECTO_ESPACIAL"], cmap=cmap2, vmin=-lim,
                        vmax=lim, s=40, edgecolor="k", lw=0.3)
    fig.colorbar(sc2, ax=ax[2], fraction=0.05, label="Efecto espacial (pp)")
    for a in ax:
        a.set_xlabel("Longitud")
    ax[0].set_ylabel("Latitud")
    fig.tight_layout()
    fig.savefig(salida, dpi=200)
    plt.close(fig)


def main():
    """Genera las figuras en la carpeta de imágenes."""
    datos, calc, img = map(Path, sys.argv[1:4])
    fpo = pd.read_csv(datos / "fhe_prediccion_objetivo.csv", dtype={"CODIGO_MUNICIPIO": str})
    dom = pd.read_csv(calc / "c1_seblup_dominios.csv", dtype={"CODIGO_DOMINIO": str})
    fin = pd.read_csv(datos / "estimaciones_finales.csv", dtype={"CODIGO": str})
    fin = fin[fin["NIVEL"] == "MUNICIPIO"]
    figura_estimaciones(fpo, dom, img / "res_espacial_estimaciones.png")
    figura_mapas(fin, fpo, img / "res_mapa_municipios.png")
    print("ok")


if __name__ == "__main__":
    main()
