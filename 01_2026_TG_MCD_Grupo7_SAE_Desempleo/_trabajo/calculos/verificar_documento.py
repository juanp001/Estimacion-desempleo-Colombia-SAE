"""Verificación global del documento LaTeX (sin compilar).

Uso: python -I verificar_documento.py <carpeta del documento>

Comprueba en todos los .tex que main.tex carga (y en docs/): cada \\ref tiene \\label; cada \\cite tiene
entrada en refs.bib; entradas de refs.bib sin citar; etiquetas duplicadas; tablas, figuras y ecuaciones
con etiqueta que nunca se citan; '---', \\textbf, [H], enumerate, \\par, '\\\\' fuera de entornos
tabulares, \\texttt fuera del apéndice, bloques %-XXXX; títulos de Metodología y Resultados idénticos;
\\includegraphics que apuntan fuera de img/ o a archivos inexistentes; páginas estimadas por capítulo.
"""

import re
import sys
from collections import Counter
from pathlib import Path

doc = Path(sys.argv[1])
main = (doc / "main.tex").read_text(encoding="utf-8")
archivos = [doc / (m + ".tex") for m in re.findall(r"\\input\{(chapters/[^}]+)\}", main)]
archivos += [doc / "docs" / "sommario.tex"]


def limpiar(t):
    """Quita comentarios de una línea.

    Args:
        t (str): texto LaTeX.

    Returns:
        str: texto sin comentarios.
    """
    return re.sub(r"(?<!\\)%.*", "", t)


textos = {a.name: a.read_text(encoding="utf-8") for a in archivos}
sinc = {k: limpiar(v) for k, v in textos.items()}
todo = "\n".join(sinc.values())
labels = re.findall(r"\\label\{([^}]+)\}", todo)
refs = set()
for grupo in re.findall(r"\\(?:ref|eqref|autoref)\{([^}]+)\}", todo):
    refs |= {x.strip() for x in grupo.split(",")}
cites = set()
for grupo in re.findall(r"\\cite[a-z]*(?:\[[^\]]*\])?\{([^}]+)\}", todo):
    cites |= {x.strip() for x in grupo.split(",")}
bib = (doc / "refs.bib").read_text(encoding="utf-8")
claves = re.findall(r"@\w+\{([^,]+),", bib)

print("Referencias rotas:", sorted(refs - set(labels)))
print("Etiquetas duplicadas:", [k for k, v in Counter(labels).items() if v > 1])
sin_citar = [l for l in labels if l.split(":")[0] in ("tab", "fig", "eq") and l not in refs]
print("Tablas/figuras/ecuaciones sin citar:", sin_citar)
print("Citas sin entrada:", sorted(cites - set(claves)))
print("Entradas bib sin citar:", sorted(set(claves) - cites))
for k, t in sinc.items():
    sin_tab = re.sub(r"\\begin\{(tabular\*?|tabularx|longtable|array|align\*?|equation\*?|cases)\}.*?\\end\{\1\}", "", t, flags=re.S)
    prob = {
        "---": t.count("---"),
        "textbf": t.count("\\textbf"),
        "[H]": t.count("[H]"),
        "enumerate": t.count("enumerate"),
        "par": len(re.findall(r"\\par\b", t)),
        "\\\\ fuera de tablas": len(re.findall(r"\\\\\s*$", sin_tab, flags=re.M)),
        "texttt": t.count("\\texttt") if k != "appendice.tex" else 0,
        "%-XXXX": textos[k].count("%-XXXX"),
    }
    prob = {a: b for a, b in prob.items() if b}
    if prob:
        print("Formato", k, prob)
    for g in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", t):
        if not g.startswith("img/") or not (doc / g).exists():
            print("Imagen problemática en", k, g)
for k, t in sinc.items():
    for titulo in re.findall(r"\\(?:chapter|section|subsection|subsubsection)\*?\{([^}]+)\}", t):
        if any(w[:1].isupper() and not w.isupper() for w in titulo.split()[1:]):
            print("Título con mayúscula intermedia en", k, "|", titulo)
m = re.findall(r"\\section\{([^}]+)\}", sinc["metodologia.tex"])
r = re.findall(r"\\section\{([^}]+)\}", sinc["resultados.tex"])
print("Títulos Metodología = Resultados:", m == r, len(m), len(r))
print("\nPáginas estimadas (400 palabras/página, 0.5 por tabla o figura pequeña, 1 por tabularx o longtable):")
for k, t in sinc.items():
    palabras = len(re.sub(r"\\[a-zA-Z]+|[{}$\\&]", " ", re.sub(r"\\begin\{(table|figure)\}.*?\\end\{\1\}", "", t, flags=re.S)).split())
    grandes = len(re.findall(r"\\begin\{(tabularx|longtable)\}", t))
    peque = len(re.findall(r"\\begin\{(table|figure)\}", t)) - len(re.findall(r"\\begin\{tabularx\}", t))
    ecs = len(re.findall(r"\\begin\{(equation|align)", t))
    print(f"  {k:30s} {palabras:6d} palabras  {palabras / 400 + 0.5 * max(peque, 0) + grandes + 0.12 * ecs:5.1f} págs.")
