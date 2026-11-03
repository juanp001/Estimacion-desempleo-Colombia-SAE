"""Mueve cinco tablas complementarias de resultados.tex a una sección nueva del apéndice.

Uso: python -I mover_tablas_apendice.py <carpeta chapters>  (se ejecuta una sola vez)
"""
import sys
from pathlib import Path

cap = Path(sys.argv[1])
r = (cap / "resultados.tex").read_text(encoding="utf-8")
a = (cap / "appendice.tex").read_text(encoding="utf-8")
BS = "\\"
etiquetas = {
    "tab:res_faltantes": ("Tratamiento de faltantes y atípicos", "sec:res_faltantes"),
    "tab:res_excluidas": ("Variables de la literatura sin dato utilizable", "sec:res_covariables"),
    "tab:res_agregacion_am": (
        "Sensibilidad de las covariables de las áreas metropolitanas a la regla de agregación",
        "sec:res_covariables",
    ),
    "tab:res_frecuencia": ("Frecuencia de selección en la validación con el procedimiento completo", "sec:res_validacion"),
    "tab:res_validacion_espacial": ("Validación dejar-un-dominio-fuera del modelo espacial", "sec:res_espacial"),
}
bloques = []
for lab, (titulo, sec) in etiquetas.items():
    i = r.index(BS + "label{" + lab + "}")
    ini = r.rindex(BS + "begin{table}", 0, i)
    fin = r.index(BS + "end{table}", i) + len(BS + "end{table}")
    bloque = r[ini:fin]
    r = r[:ini].rstrip("\n") + "\n\n" + r[fin:].lstrip("\n")
    bloques.append(
        f"{BS}subsection{{{titulo}}}\n\nComplementa la Sección~{BS}ref{{{sec}}}.\n\n{bloque}\n"
    )
sep = "%" + "-" * 86 + "\n"
nuevo = (
    sep + BS + "section{Material complementario de Resultados}\n" + BS + "label{app:resultados}\n\n"
    "Esta sección reúne tablas de apoyo de la Sección~" + BS + "ref{sec:resultados} que no responden por sí "
    "solas a un objetivo; cada una se cita desde la sección de Resultados que complementa.\n\n"
    + "\n".join(bloques) + "\n" + BS + "FloatBarrier\n\n"
)
k = a.index(sep + BS + "section{Repositorio de github}")
a = a[:k] + nuevo + a[k:]
(cap / "resultados.tex").write_text(r, encoding="utf-8")
(cap / "appendice.tex").write_text(a, encoding="utf-8")
print("ok")
