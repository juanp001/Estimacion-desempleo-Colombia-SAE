"""Agrega y corrige las entradas de refs.bib que usa Antecedentes (ver auditoria_citas.md).

Uso: python -I editar_refs_antecedentes.py <ruta a refs.bib>
"""

import re
import sys

ruta = sys.argv[1]
s = open(ruta, encoding="utf-8").read()


def reemplazar(clave, nueva):
    """Sustituye la entrada `clave` completa por `nueva`."""
    global s
    m = re.search(r"@\w+\{" + clave + r",.*?\n\}\n", s, re.S)
    assert m, clave
    s = s[: m.start()] + nueva.strip() + "\n" + s[m.end():]


reemplazar("MendozaZea2019", r"""@misc{MendozaZea2019,
  author       = {Mendoza Castrill\'{o}n, D. and Zea, J. F.},
  title        = {Estimaci\'{o}n de la tasa de desempleo e ingreso medio del departamento de {Cundinamarca} utilizando {SAE}},
  howpublished = {Proyecto de grado, Facultad de Estad\'{\i}stica, Universidad Santo Tom\'{a}s},
  address      = {Bogot\'{a}, Colombia},
  year         = {2019},
  language     = {Spanish}
}""")
reemplazar("VargasLemusAlejo2018", r"""@misc{VargasLemusAlejo2018,
  author       = {Ram\'{\i}rez Vargas, N. and Lemus Polania, D. F. and Alejo, H. A.},
  title        = {Un modelo de \'{a}reas peque\~{n}as para la estimaci\'{o}n de la frecuencia de consumo de basuco al interior de las {UPZ} de {Bogot\'{a}}},
  howpublished = {Trabajo de grado, Maestr\'{\i}a en Estad\'{\i}stica Aplicada, Universidad Santo Tom\'{a}s},
  address      = {Bogot\'{a}, Colombia},
  year         = {2018},
  language     = {Spanish}
}""")
reemplazar("OrtizTellezRamirez2024", r"""@article{OrtizTellezRamirez2024,
  author  = {Ort\'{\i}z Rico, F. and Tellez Pi\~{n}erez, C. F. and Ram\'{\i}rez-Vargas, N.},
  title   = {A Review of the Use of Small Area Estimation in {Colombia}},
  journal = {Revista Colombiana de Estad\'{\i}stica},
  volume  = {47},
  number  = {2},
  pages   = {407--422},
  year    = {2024},
  doi     = {10.15446/rce.v47n2.112779}
}""")

NUEVAS = r"""
@techreport{Shiferaw2025,
  author       = {Shiferaw, Y. A.},
  title        = {Unravelling the Spatial Dynamics of Unemployment Rates in District Municipalities in {South Africa}: A Disaggregated Analysis for Informed Policymaking},
  institution  = {Economic Research Southern Africa (ERSA)},
  type         = {Working Paper},
  number       = {921},
  year         = {2025},
  note         = {Las p\'{a}ginas citadas son las del archivo PDF}
}

@article{Pereira2021,
  author  = {Pereira, S. and Turkman, K. F. and Correia, L. and Rue, H.},
  title   = {Unemployment Estimation: Spatial Point Referenced Methods and Models},
  journal = {Spatial Statistics},
  volume  = {41},
  pages   = {100345},
  year    = {2021},
  doi     = {10.1016/j.spasta.2019.01.001}
}

@article{Sikov2023,
  author  = {Sikov, A. and Cerda, J. and Haro, M.},
  title   = {¿Es posible obtener estimaciones confiables del porcentaje de anemia y retraso en el crecimiento en ni\~{n}os menores de cinco a\~{n}os en los distritos m\'{a}s pobres del {Per\'{u}}?},
  journal = {Apuntes},
  volume  = {50},
  number  = {95},
  pages   = {171--202},
  year    = {2023},
  language = {Spanish}
}

@mastersthesis{Haro2022,
  author       = {Haro Abanto, M. E.},
  title        = {Un modelo {Fay-Herriot} espacial para la predicci\'{o}n del porcentaje de ni\~{n}os con anemia y riesgo de retraso del crecimiento en distritos no encuestados y en distritos con pocas observaciones disponibles},
  school       = {Pontificia Universidad Cat\'{o}lica del Per\'{u}},
  address      = {Lima, Per\'{u}},
  year         = {2022},
  type         = {Tesis de Maestr\'{\i}a en Estad\'{\i}stica},
  language     = {Spanish}
}

@misc{RomeroLemus2018,
  author       = {Romero Romero, J. J. and Lemus Polania, D. F.},
  title        = {Un modelo {Fay-Herriot} espacial para estimar la tasa de embarazo adolescente en {Colombia}},
  howpublished = {Trabajo de grado, Maestr\'{\i}a en Estad\'{\i}stica Aplicada, Universidad Santo Tom\'{a}s},
  address      = {Bogot\'{a}, Colombia},
  year         = {2018},
  language     = {Spanish}
}

@mastersthesis{Duran2024,
  author       = {Dur\'{a}n Gil, A.},
  title        = {Aproximaci\'{o}n espacial sobre la pobreza monetaria en {Bogot\'{a}}: una aplicaci\'{o}n desde la estimaci\'{o}n en \'{a}reas peque\~{n}as},
  school       = {Universidad Santo Tom\'{a}s},
  address      = {Bogot\'{a}, Colombia},
  year         = {2024},
  type         = {Trabajo de grado},
  language     = {Spanish}
}

@techreport{GallegoMunoz2017,
  author       = {Gallego Ortiz, S. and Mu\~{n}oz Gonz\'{a}lez, E. J.},
  title        = {An\'{a}lisis espacial de la informalidad laboral a nivel intra-urbano. {El} caso de {Medell\'{\i}n}, {Colombia}},
  institution  = {Universidad EAFIT},
  address      = {Medell\'{\i}n, Colombia},
  year         = {2017},
  language     = {Spanish}
}
"""
if "Shiferaw2025" not in s:
    s = s.rstrip() + "\n" + NUEVAS
open(ruta, "w", encoding="utf-8").write(s)
print("entradas:", s.count("\n@"))
