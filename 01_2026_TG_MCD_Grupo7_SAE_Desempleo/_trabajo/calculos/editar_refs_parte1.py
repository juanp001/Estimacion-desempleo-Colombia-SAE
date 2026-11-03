"""Corrige entradas de refs.bib y agrega las fuentes nuevas de la parte 1 (ver auditoria_citas.md).

Uso: python -I editar_refs_parte1.py <ruta a refs.bib>
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


reemplazar("BernalGonzalez2017", r"""@mastersthesis{BernalGonzalez2017,
  author       = {Bernal Mu\~{n}oz, L. K.},
  title        = {Distribuci\'{o}n beta para modelar proporciones en \'{a}reas peque\~{n}as},
  school       = {Universidad Nacional de Colombia},
  address      = {Bogot\'{a}, Colombia},
  year         = {2017},
  type         = {Tesis de Maestr\'{\i}a en Ciencias, Bioestad\'{\i}stica},
  language     = {Spanish}
}""")
reemplazar("Montoya2019", r"""@mastersthesis{Montoya2019,
  author       = {V\'{e}lez Montoya, D.},
  title        = {Una adaptaci\'{o}n del procedimiento bootstrap en la estimaci\'{o}n del error cuadr\'{a}tico medio en \'{a}reas peque\~{n}as con aplicaci\'{o}n a datos colombianos},
  school       = {Universidad Nacional de Colombia},
  address      = {Bogot\'{a}, Colombia},
  year         = {2019},
  type         = {Tesis de Maestr\'{\i}a},
  language     = {Spanish}
}""")
reemplazar("GuerreroTrujillo2019", r"""@mastersthesis{GuerreroTrujillo2019,
  author       = {Guerrero G\'{o}mez, S. Y.},
  title        = {Estimaci\'{o}n de los coeficientes de regresi\'{o}n en \'{a}reas peque\~{n}as utilizando valores plausibles en muestras probabil\'{\i}sticas},
  school       = {Universidad Nacional de Colombia},
  address      = {Bogot\'{a}, Colombia},
  year         = {2019},
  type         = {Tesis de Maestr\'{\i}a en Ciencias, Estad\'{\i}stica},
  language     = {Spanish}
}""")
reemplazar("INEChile2016", r"""@techreport{INEChile2016,
  author       = {{Ministerio de Desarrollo Social de Chile}},
  title        = {Metodolog\'{\i}a actualizada de estimaci\'{o}n para \'{a}reas peque\~{n}as ({SAE}): anexo de programaci\'{o}n de la tasa de pobreza por ingresos a nivel comunal (2011--2013)},
  institution  = {Ministerio de Desarrollo Social},
  type         = {Serie Documentos Metodol\'{o}gicos},
  number       = {32},
  address      = {Santiago de Chile, Chile},
  year         = {2016},
  language     = {Spanish}
}""")
reemplazar("ColeyTellez2024", r"""@article{ColeyTellez2024,
  author  = {Jim\'{e}nez Coley, C. and Tellez Pi\~{n}erez, C. F.},
  title   = {Estimaci\'{o}n del rendimiento medio en las pruebas {PISA} 2018: un enfoque espacial desde la metodolog\'{\i}a en estimaci\'{o}n en \'{a}reas peque\~{n}as},
  journal = {Bolet\'{\i}n de Estad\'{\i}stica e Investigaci\'{o}n Operativa},
  volume  = {40},
  number  = {2},
  pages   = {7--17},
  year    = {2024},
  language = {Spanish}
}""")

NUEVAS = r"""
@techreport{DANE_GEIH_Metodologia2016,
  author       = {{Departamento Administrativo Nacional de Estad\'{\i}stica (DANE)}},
  title        = {Metodolog\'{\i}a general {Gran Encuesta Integrada de Hogares} ({GEIH})},
  institution  = {DANE},
  type         = {Documento metodol\'{o}gico},
  number       = {DSO-GEIH-MET-001, versi\'{o}n 9},
  address      = {Bogot\'{a}, Colombia},
  year         = {2016},
  month        = apr,
  note         = {Las p\'{a}ginas citadas son las del archivo PDF},
  language     = {Spanish}
}

@techreport{DANE_GEIH_Series2022,
  author       = {{Departamento Administrativo Nacional de Estad\'{\i}stica (DANE)}},
  title        = {Actualizaci\'{o}n de la serie de poblaciones e indicadores de mercado laboral 2007--2021 de la {GEIH} marco 2005 con factores de expansi\'{o}n de las retroproyecciones del {CNPV} 2018},
  institution  = {DANE},
  type         = {Presentaci\'{o}n metodol\'{o}gica},
  address      = {Bogot\'{a}, Colombia},
  year         = {2022},
  note         = {Las p\'{a}ginas citadas son las del archivo PDF},
  language     = {Spanish}
}

@techreport{DANE_Anexo_CNPV2018,
  author       = {{Departamento Administrativo Nacional de Estad\'{\i}stica (DANE)}},
  title        = {Anexo estad\'{\i}stico: mercado laboral seg\'{u}n proyecciones {CNPV} 2018},
  institution  = {DANE},
  type         = {Anexo de publicaci\'{o}n, Gran Encuesta Integrada de Hogares},
  address      = {Bogot\'{a}, Colombia},
  year         = {2022},
  language     = {Spanish}
}

@misc{DNP_TerriData,
  author       = {{Departamento Nacional de Planeaci\'{o}n (DNP)}},
  title        = {{TerriData}: sistema de estad\'{\i}sticas territoriales},
  url          = {https://terridata.dnp.gov.co},
  language     = {Spanish}
}

@misc{DANE_DIVIPOLA,
  author       = {{Departamento Administrativo Nacional de Estad\'{\i}stica (DANE)}},
  title        = {Codificaci\'{o}n de la divisi\'{o}n pol\'{\i}tico-administrativa de Colombia ({DIVIPOLA})},
  url          = {https://geoportal.dane.gov.co/geovisores/territorio/consulta-divipola-division-politico-administrativa-de-colombia/},
  language     = {Spanish}
}

@techreport{Casen2024,
  author       = {{Ministerio de Desarrollo Social y Familia de Chile}},
  title        = {Estimaciones comunales de inseguridad alimentaria, {Casen} 2024},
  institution  = {Ministerio de Desarrollo Social y Familia},
  type         = {Informe metodol\'{o}gico},
  address      = {Santiago de Chile, Chile},
  year         = {2024},
  note         = {Las p\'{a}ginas citadas son las del archivo PDF},
  language     = {Spanish}
}

@article{Benedetti2024,
  author  = {Benedetti, R. and Piersimoni, F. and Pratesi, M. and Salvati, N. and Suesse, T.},
  title   = {Handling Out-of-Sample Areas to Estimate the Unemployment Rate at Local Labour Market Areas in {Italy}},
  journal = {International Statistical Review},
  volume  = {94},
  number  = {1},
  pages   = {140--162},
  year    = {2026},
  doi     = {10.1111/insr.12596},
  note    = {Publicado en l\'{\i}nea en 2024}
}

@article{PratesiSalvati2008,
  author  = {Pratesi, M. and Salvati, N.},
  title   = {Small Area Estimation: The {EBLUP} Estimator Based on Spatially Correlated Random Area Effects},
  journal = {Statistical Methods and Applications},
  volume  = {17},
  pages   = {113--141},
  year    = {2008},
  doi     = {10.1007/s10260-007-0061-9}
}

@article{PetrucciSalvati2006,
  author  = {Petrucci, A. and Salvati, N.},
  title   = {Small Area Estimation for Spatial Correlation in Watershed Erosion Assessment},
  journal = {Journal of Agricultural, Biological, and Environmental Statistics},
  volume  = {11},
  number  = {2},
  pages   = {169--182},
  year    = {2006},
  doi     = {10.1198/108571106X110531}
}

@article{Diaz2016,
  author  = {D\'{\i}az, A. M.},
  title   = {Spatial Unemployment Differentials in {Colombia}},
  journal = {Desarrollo y Sociedad},
  number  = {76},
  pages   = {123--163},
  year    = {2016},
  doi     = {10.13043/DYS.76.3}
}

@book{MontgomeryPeckVining2012,
  author    = {Montgomery, D. C. and Peck, E. A. and Vining, G. G.},
  title     = {Introduction to Linear Regression Analysis},
  edition   = {5th},
  publisher = {John Wiley \& Sons},
  address   = {Hoboken, NJ, USA},
  year      = {2012}
}

@article{BenjaminiHochberg1995,
  author  = {Benjamini, Y. and Hochberg, Y.},
  title   = {Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing},
  journal = {Journal of the Royal Statistical Society: Series B (Methodological)},
  volume  = {57},
  number  = {1},
  pages   = {289--300},
  year    = {1995},
  doi     = {10.1111/j.2517-6161.1995.tb02031.x}
}

@article{ShapiroWilk1965,
  author  = {Shapiro, S. S. and Wilk, M. B.},
  title   = {An Analysis of Variance Test for Normality (Complete Samples)},
  journal = {Biometrika},
  volume  = {52},
  number  = {3--4},
  pages   = {591--611},
  year    = {1965},
  doi     = {10.1093/biomet/52.3-4.591}
}

@article{Cook1977,
  author  = {Cook, R. D.},
  title   = {Detection of Influential Observation in Linear Regression},
  journal = {Technometrics},
  volume  = {19},
  number  = {1},
  pages   = {15--18},
  year    = {1977},
  doi     = {10.1080/00401706.1977.10489493}
}

@article{Moran1950,
  author  = {Moran, P. A. P.},
  title   = {Notes on Continuous Stochastic Phenomena},
  journal = {Biometrika},
  volume  = {37},
  number  = {1--2},
  pages   = {17--23},
  year    = {1950},
  doi     = {10.2307/2332142}
}

@article{HurvichTsai1989,
  author  = {Hurvich, C. M. and Tsai, C.-L.},
  title   = {Regression and Time Series Model Selection in Small Samples},
  journal = {Biometrika},
  volume  = {76},
  number  = {2},
  pages   = {297--307},
  year    = {1989},
  doi     = {10.1093/biomet/76.2.297}
}
"""

if "DANE_GEIH_Metodologia2016" not in s:
    s = s.rstrip() + "\n" + NUEVAS
open(ruta, "w", encoding="utf-8").write(s)
print("entradas:", s.count("\n@"))
