"""Genera filas LaTeX de las tablas de Resultados a partir de los CSV descargados (sin recalcular cifras).

Uso: python -I filas_latex.py  (desde _trabajo/calculos; escribe salidas/filas_*.tex)
"""
import sys
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
aud = pd.read_csv("datos/auditoria_dominios.csv", dtype={"CODIGO_DOMINIO": str})
fhr = pd.read_csv("datos/fay_herriot_resultados.csv", dtype={"CODIGO_DOMINIO": str})
dom = pd.read_csv("datos/dominios.csv", dtype={"CODIGO_DOMINIO": str})
c1 = pd.read_csv("salidas/c1_seblup_dominios.csv", dtype={"CODIGO_DOMINIO": str})
d = fhr.merge(aud[["CODIGO_DOMINIO", "TD_DANE_PCT"]], on="CODIGO_DOMINIO").merge(c1[["CODIGO_DOMINIO", "SEBLUP", "CV_SEBLUP_PCT", "GAMMA_S"]], on="CODIGO_DOMINIO")
d = d.sort_values("NOMBRE_DOMINIO")
f = []
for _, r in d.iterrows():
    f.append(f"{r.NOMBRE_DOMINIO} & {r.TASA_DESEMPLEO_PCT:.2f} & {r.SE_BOOTSTRAP_PCT:.2f} & {r.CV_PORCENTAJE:.2f} & {r.TD_DANE_PCT:.2f} & {r.TASA_DESEMPLEO_PCT - r.TD_DANE_PCT:.2f} \\\\")
open("salidas/filas_directa.tex", "w", encoding="utf-8").write("\n".join(f))
g = []
for _, r in d.iterrows():
    g.append(f"{r.NOMBRE_DOMINIO} & {r.TASA_DESEMPLEO_PCT:.2f} & {r.EBLUP:.2f} & {r.CV_EBLUP_PCT:.2f} & {r.GAMMA_SHRINKAGE:.3f} & {r.SEBLUP:.2f} & {r.CV_SEBLUP_PCT:.2f} & {r.GAMMA_S:.3f} & {r.EBLUP_BENCHMARK:.2f} \\\\")
open("salidas/filas_dominios_modelo.tex", "w", encoding="utf-8").write("\n".join(g))
fin = pd.read_csv("datos/estimaciones_finales.csv", dtype={"CODIGO": str})
fpo = pd.read_csv("datos/fhe_prediccion_objetivo.csv", dtype={"CODIGO_MUNICIPIO": str})
m = fin[fin.NIVEL == "MUNICIPIO"].merge(fpo[["CODIGO_MUNICIPIO", "PRED_ESPACIAL", "CV_ESPACIAL_PCT"]], left_on="CODIGO", right_on="CODIGO_MUNICIPIO")
m = m.sort_values(["DEPARTAMENTO", "NOMBRE"])
nombres = pd.read_csv("datos/objetivos.csv", dtype={"CODIGO_MUNICIPIO": str}).set_index("CODIGO_MUNICIPIO")["MUNICIPIO"]
h = []
for _, r in m.iterrows():
    dep = "Cauca" if r.DEPARTAMENTO.startswith("CAUCA") else "Valle"
    est = "fuera" if str(r.EXTRAPOLA).lower() == "true" else "dentro"
    h.append(f"{r.CODIGO} & {nombres[r.CODIGO]} & {dep} & {r.TASA_SIN_AJUSTE_PCT:.2f} & {r.TASA_DESEMPLEO_PCT:.2f} & {r.CV_PCT:.2f} & {r.CONFIABILIDAD} & {est} & {r.PRED_ESPACIAL:.2f} & {r.CV_ESPACIAL_PCT:.2f} \\\\")
open("salidas/filas_municipios.tex", "w", encoding="utf-8").write("\n".join(h))
print(len(f), len(g), len(h))
