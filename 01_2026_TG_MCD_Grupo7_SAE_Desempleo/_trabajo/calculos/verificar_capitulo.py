"""Verifica un capítulo LaTeX: refs, citas, formato y estimación de páginas.

Uso: python -I verificar_capitulo.py <carpeta del documento> <capitulo.tex> [<capitulo.tex> ...]

Comprueba: cada \\ref/\\eqref tiene su \\label en algún .tex del documento; cada \\cite tiene
entrada en refs.bib; ausencia de '---', \\textbf, [H], enumerate, '\\\\' como separador de
párrafo, \\par y nombres en formato de código (\\texttt, guiones bajos en mayúsculas). Estima
páginas: 400 palabras de texto por página, 0.5 por tabla o figura pequeña, 1 por longtable o
tabla con tabularx, 0.12 por ecuación mostrada.
"""

import glob
import os
import re
import sys

raiz = sys.argv[1]
capitulos = sys.argv[2:]
todos = glob.glob(os.path.join(raiz, "chapters", "*.tex")) + [os.path.join(raiz, "main.tex")]
labels = set()
for f in todos:
    labels |= set(re.findall(r"\\label\{([^}]+)\}", open(f, encoding="utf-8").read()))
bib = open(os.path.join(raiz, "refs.bib"), encoding="utf-8").read()
claves = set(re.findall(r"@\w+\{([^,]+),", bib))

for cap in capitulos:
    txt = open(os.path.join(raiz, "chapters", cap), encoding="utf-8").read()
    sin_coment = "\n".join(l for l in txt.splitlines() if not l.lstrip().startswith("%"))
    refs = set(re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", sin_coment))
    rotas = sorted(r for r in refs if r not in labels)
    cites = set()
    for grupo in re.findall(r"\\cite(?:\[[^\]]*\])?\{([^}]+)\}", sin_coment):
        cites |= {c.strip() for c in grupo.split(",")}
    sin_bib = sorted(c for c in cites if c not in claves)
    problemas = {
        "---": sin_coment.count("---"),
        "\\textbf": sin_coment.count("\\textbf"),
        "[H]": sin_coment.count("[H]"),
        "enumerate": sin_coment.count("enumerate"),
        "\\par ": len(re.findall(r"\\par\b", sin_coment)),
        "\\\\ fuera de tablas": 0,
        "\\texttt": sin_coment.count("\\texttt"),
        "MAYUS_CON_GUION": len(re.findall(r"\b[A-Z]{2,}_[A-Z_0-9]+\b", sin_coment)),
        "comentarios %-XXXX": txt.count("%-XXXX"),
    }
    # '\\' fuera de entornos tabulares y de ecuaciones alineadas
    cuerpo = re.sub(
        r"\\begin\{(tabular\*?|tabularx|longtable|aligned|array|cases)\}.*?\\end\{\1\}",
        "",
        sin_coment,
        flags=re.S,
    )
    problemas["\\\\ fuera de tablas"] = len(re.findall(r"\\\\(?!\w)", cuerpo))
    # Estimación de páginas
    texto = re.sub(r"\\begin\{(table|figure|equation)\}.*?\\end\{\1\}", " ", sin_coment, flags=re.S)
    texto = re.sub(r"\\[a-zA-Z]+(\[[^\]]*\])?(\{[^}]*\})?", " ", texto)
    texto = re.sub(r"\$[^$]*\$", " x ", texto)
    palabras = len(re.findall(r"\w+", texto))
    tablas = re.findall(r"\\begin\{table\}.*?\\end\{table\}", sin_coment, flags=re.S)
    grandes = sum(1 for t in tablas if "tabularx" in t or t.count("\\\\") > 12)
    pequenas = len(tablas) - grandes + len(re.findall(r"\\begin\{figure\}", sin_coment))
    grandes += len(re.findall(r"\\begin\{longtable\}", sin_coment))
    ecuaciones = len(re.findall(r"\\begin\{equation\}", sin_coment))
    paginas = palabras / 400 + 0.5 * pequenas + 1.0 * grandes + 0.12 * ecuaciones
    print(f"== {cap}")
    print(f"  refs: {len(refs)}  rotas: {rotas}")
    print(f"  citas: {sorted(cites)}")
    print(f"  citas sin entrada bib: {sin_bib}")
    print(f"  formato: {problemas}")
    print(
        f"  palabras≈{palabras}  tablas/figuras pequeñas={pequenas}  grandes={grandes}  "
        f"ecuaciones={ecuaciones}  páginas≈{paginas:.1f}"
    )
