"""Elimina de refs.bib las entradas que ningún capítulo cita.

Uso: python -I limpiar_bib.py <refs.bib> <clave> [<clave> ...]
"""
import re
import sys

ruta, claves = sys.argv[1], set(sys.argv[2:])
texto = open(ruta, encoding="utf-8").read()
partes = re.split(r"(?=^@\w+\{)", texto, flags=re.M)
quedan = [p for p in partes if not (m := re.match(r"@\w+\{([^,]+),", p)) or m.group(1) not in claves]
open(ruta, "w", encoding="utf-8").write("".join(quedan))
print(len(partes) - len(quedan), "entradas eliminadas")
