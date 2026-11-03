"""Cálculos propios C1-C4 de la comparación entre el Fay-Herriot clásico y el espacial.

Uso: python -I comparacion_espacial.py <ruta_code> <carpeta_datos> <carpeta_salidas>

Entradas (CSV de solo lectura descargados con descargar_tablas.py):
    dominios.csv, objetivos.csv          (covariables_seleccionadas, municipios_sin_encuesta, dim_divipola)
    fay_herriot_resultados.csv           (EBLUP, MSE y gamma del benchmark)
    fhe_prediccion_objetivo.csv          (estimaciones clásica y espacial de los 83 municipios)
    estimaciones_finales.csv             (tabla final consolidada)

Cálculos:
    C1  SEBLUP, ECM bootstrap (500 réplicas, semilla 42), CV y gamma^S_d = [G V^-1]_dd de los
        23 dominios con el escenario de referencia (3 vecinos, estructura «completa»), con la
        clase FayHerriotEspacial del código (Morales et al., p. 494; ecs. eq:seblup, eq:gamma_esp).
    C2  Diferencia espacial − clásico en los 83 municipios: media, media absoluta, máximo
        absoluto, Pearson, Spearman y cambios de clase de CV (5 / 20 %).
    C3  Lo mismo en los 23 dominios (EBLUP frente a SEBLUP).
    C4  I de Moran de las 83 estimaciones finales con 3 vecinos más cercanos, W estandarizada por
        filas y 9,999 permutaciones (semilla 42).
No escribe en Databricks ni modifica el código.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

CODE = Path(sys.argv[1])
DATOS = Path(sys.argv[2])
SALIDAS = Path(sys.argv[3])
sys.path.insert(0, str(CODE / "modelo"))

from shared.fay_herriot import FayHerriotClasico  # noqa: E402
from shared.fay_herriot_espacial import FayHerriotEspacial  # noqa: E402
from shared.matriz_proximidad import (  # noqa: E402
    distancias_haversine,
    estandarizar_filas,
    moran_i,
    proximidad_knn,
    proximidad_total,
)

Y, SE, COV = "TASA_DESEMPLEO_PCT", "SE_BOOTSTRAP_PCT", ["TASA_HOMICIDIOS"]


def clase_cv(cv):
    """Clase de confiabilidad por CV (umbrales 5 y 20 %).

    Args:
        cv (array-like): coeficientes de variación en porcentaje.

    Returns:
        np.ndarray: etiquetas «Confiable», «Aceptable» o «No confiable».
    """
    cv = np.asarray(cv, dtype=float)
    return np.where(cv < 5, "Confiable", np.where(cv < 20, "Aceptable", "No confiable"))


def resumen_diferencias(a, b, cv_a, cv_b):
    """Resume la diferencia b − a entre dos estimaciones y los cambios de clase de CV.

    Args:
        a, b (array-like): estimación clásica y espacial (puntos porcentuales).
        cv_a, cv_b (array-like): CV de cada una (%).

    Returns:
        dict: n, media, media absoluta, máximo absoluto, Pearson, Spearman, cambios de clase.
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    ca, cb = clase_cv(cv_a), clase_cv(cv_b)
    cambios = pd.crosstab(pd.Series(ca, name="clasico"), pd.Series(cb, name="espacial"))
    return {
        "n": int(len(a)),
        "dif_media_pp": float(d.mean()),
        "dif_abs_media_pp": float(np.abs(d).mean()),
        "dif_abs_max_pp": float(np.abs(d).max()),
        "n_abs_mayor_0_5": int((np.abs(d) > 0.5).sum()),
        "pearson": float(stats.pearsonr(a, b)[0]),
        "spearman": float(stats.spearmanr(a, b)[0]),
        "cv_mediano_clasico": float(np.median(cv_a)),
        "cv_mediano_espacial": float(np.median(cv_b)),
        "n_cambia_clase": int((ca != cb).sum()),
        "tabla_clases": cambios.to_dict(),
    }


def main():
    """Ejecuta C1-C4 y guarda tablas CSV y un resumen JSON en la carpeta de salidas."""
    SALIDAS.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATOS / "dominios.csv", dtype={"CODIGO_DOMINIO": str})
    df = df.sort_values("CODIGO_DOMINIO").reset_index(drop=True)
    obj_todos = pd.read_csv(
        DATOS / "objetivos.csv", dtype={"CODIGO_MUNICIPIO": str, "CODIGO_DOMINIO_PADRE": str}
    ).sort_values("CODIGO_MUNICIPIO")
    obj = obj_todos[obj_todos["CODIGO_DOMINIO_PADRE"].isna()].reset_index(drop=True)
    n, r = len(df), len(obj)

    # ── C1: SEBLUP de los dominios ────────────────────────────────────────────
    clasico = FayHerriotClasico(COV, df, Y, SE)
    clasico.ajustar()
    lat = np.concatenate([df["LATITUD"].values, obj["LATITUD"].values])
    lon = np.concatenate([df["LONGITUD"].values, obj["LONGITUD"].values])
    D = distancias_haversine(lat, lon)
    P = proximidad_total(D, n, "knn", 3, "completa")
    esp = FayHerriotEspacial(
        COV, df, Y, SE, P, obj, estructura="completa", rho_limite=0.99, n_bootstrap=500, semilla=42
    )
    esp.ajustar()
    aj = esp._ajuste_gls(esp.Y, esp.theta_hat)
    gamma_s = np.diag(aj["G"][:n, :n] @ aj["Vi"])

    fhr = pd.read_csv(DATOS / "fay_herriot_resultados.csv", dtype={"CODIGO_DOMINIO": str})
    fhr = fhr.set_index("CODIGO_DOMINIO").loc[df["CODIGO_DOMINIO"]].reset_index()
    dom = pd.DataFrame(
        {
            "CODIGO_DOMINIO": df["CODIGO_DOMINIO"],
            "NOMBRE_DOMINIO": df["NOMBRE_DOMINIO"],
            "DIRECTA": df[Y],
            "PSI": df[SE] ** 2,
            "EBLUP": fhr["EBLUP"],
            "MSE_EBLUP": fhr["MSE_EBLUP"],
            "CV_EBLUP_PCT": fhr["CV_EBLUP_PCT"],
            "GAMMA": fhr["GAMMA_SHRINKAGE"],
            "SEBLUP": esp.eblup,
            "MSE_SEBLUP": esp.mse,
            "CV_SEBLUP_PCT": esp.cv,
            "GAMMA_S": gamma_s,
        }
    )
    dom["DIF_SEBLUP_EBLUP_PP"] = dom["SEBLUP"] - dom["EBLUP"]
    dom.to_csv(SALIDAS / "c1_seblup_dominios.csv", index=False)

    # ── C2 y C3 ────────────────────────────────────────────────────────────────
    fpo = pd.read_csv(DATOS / "fhe_prediccion_objetivo.csv", dtype={"CODIGO_MUNICIPIO": str})
    c2 = resumen_diferencias(
        fpo["PRED_CLASICO"], fpo["PRED_ESPACIAL"], fpo["CV_CLASICO_PCT"], fpo["CV_ESPACIAL_PCT"]
    )
    c3 = resumen_diferencias(dom["EBLUP"], dom["SEBLUP"], dom["CV_EBLUP_PCT"], dom["CV_SEBLUP_PCT"])
    fpo[
        ["CODIGO_MUNICIPIO", "MUNICIPIO", "PRED_CLASICO", "CV_CLASICO_PCT", "PRED_ESPACIAL",
         "CV_ESPACIAL_PCT", "EFECTO_ESPACIAL", "DIF_ESPACIAL_VS_CLASICO", "KM_DOMINIO_CERCANO"]
    ].assign(
        CLASE_CLASICO=clase_cv(fpo["CV_CLASICO_PCT"]), CLASE_ESPACIAL=clase_cv(fpo["CV_ESPACIAL_PCT"])
    ).to_csv(SALIDAS / "c2_diferencias_municipios.csv", index=False)

    # ── C4: Moran de las 83 estimaciones finales ──────────────────────────────
    fin = pd.read_csv(DATOS / "estimaciones_finales.csv", dtype={"CODIGO": str})
    mun = fin[fin["NIVEL"] == "MUNICIPIO"].merge(
        fpo[["CODIGO_MUNICIPIO", "LATITUD", "LONGITUD"]], left_on="CODIGO", right_on="CODIGO_MUNICIPIO"
    )
    Dm = distancias_haversine(mun["LATITUD"].values, mun["LONGITUD"].values)
    Wm = estandarizar_filas(proximidad_knn(Dm, 3))
    c4 = moran_i(mun["TASA_DESEMPLEO_PCT"].values, Wm, 9999, 42)
    c4_sin_ajuste = moran_i(mun["TASA_SIN_AJUSTE_PCT"].values, Wm, 9999, 42)
    c4_hom = moran_i(
        obj_todos.set_index("CODIGO_MUNICIPIO").loc[mun["CODIGO"], "TASA_HOMICIDIOS"].values,
        Wm, 9999, 42,
    )

    resumen = {
        "C1": {
            "rho_hat": esp.rho_hat,
            "sigma2_u_espacial": esp.A_hat,
            "sigma2_u_clasico": clasico.A_hat,
            "bootstrap_validas": esp.n_bootstrap_validas,
            "cv_seblup_mediano": float(np.median(esp.cv)),
            "cv_seblup_max": float(np.max(esp.cv)),
            "cv_eblup_mediano": float(dom["CV_EBLUP_PCT"].median()),
            "mse_seblup_medio": float(np.mean(esp.mse)),
            "mse_eblup_medio": float(dom["MSE_EBLUP"].mean()),
            "gamma_s_min": float(gamma_s.min()),
            "gamma_s_max": float(gamma_s.max()),
            "gamma_s_media": float(gamma_s.mean()),
            "gamma_media": float(dom["GAMMA"].mean()),
            "n_mse_seblup_menor_eblup": int((esp.mse < dom["MSE_EBLUP"]).sum()),
        },
        "C2_municipios": c2,
        "C3_dominios": c3,
        "C4_moran_final": c4,
        "C4_moran_sin_ajuste": c4_sin_ajuste,
        "C4_moran_homicidios": c4_hom,
    }
    (SALIDAS / "resumen_comparacion.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(json.dumps(resumen, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
