"""Extrae los notebooks exportados de Databricks (HTML) a Markdown y figuras PNG.

Uso: python -I extraer_notebooks.py <carpeta_html> <carpeta_salida>

Cada HTML guarda el notebook en ``__DATABRICKS_NOTEBOOK_MODEL`` (base64 de un JSON
URL-codificado). Se escribe un ``.md`` por notebook (código y salidas de cada celda) y las
figuras ``image/png`` en ``<carpeta_salida>/fig/``.
"""

import base64
import html
import json
import re
import sys
import urllib.parse
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*m")
FENCE = "`" * 3


def bloque(texto):
    """Envuelve un texto en un bloque de código Markdown.

    Args:
        texto (str): contenido.

    Returns:
        str: bloque con cercas.
    """
    return FENCE + "\n" + texto + "\n" + FENCE


def guardar_png(b64, out, nombre, idx, figs):
    """Guarda una imagen PNG en base64 y devuelve el enlace Markdown.

    Args:
        b64 (str): imagen en base64.
        out (Path): carpeta de salida.
        nombre (str): nombre del notebook.
        idx (int): número de celda.
        figs (list): figuras ya guardadas (se le agrega la nueva).

    Returns:
        str: enlace Markdown a la figura.
    """
    f = f"{nombre}_c{idx:02d}_{len(figs)}.png"
    (out / "fig" / f).write_bytes(base64.b64decode(b64))
    figs.append(f)
    return f"![fig](fig/{f})"


def texto_resultado(res, out, nombre, idx, figs):
    """Convierte la salida de una celda en Markdown y guarda sus imágenes.

    Args:
        res (dict): salida de la celda (``results`` o un elemento de ``listResults``).
        out (Path): carpeta de salida.
        nombre (str): nombre del notebook.
        idx (int): número de celda.
        figs (list): acumulador de figuras.

    Returns:
        str: texto Markdown de la salida.
    """
    if not isinstance(res, dict):
        return ""
    partes = []
    data = res.get("data")
    tipo = res.get("type")
    if tipo == "table" and isinstance(data, list):
        cols = [c.get("name") for c in res.get("schema", [])]
        partes.append("| " + " | ".join(map(str, cols)) + " |")
        partes.append("|" + "---|" * len(cols))
        for fila in data[:400]:
            partes.append("| " + " | ".join(str(v) for v in fila) + " |")
        if len(data) > 400:
            partes.append(f"... ({len(data)} filas)")
    elif tipo == "mimeBundle" and isinstance(data, dict):
        if "image/png" in data:
            partes.append(guardar_png(data["image/png"], out, nombre, idx, figs))
        elif "text/html" in data:
            partes.append(texto_resultado({"type": "html", "data": data["text/html"]}, out, nombre, idx, figs))
        elif "text/plain" in data:
            partes.append(bloque(str(data["text/plain"])[:5000]))
    elif tipo == "image/png" and isinstance(data, str):
        partes.append(guardar_png(data, out, nombre, idx, figs))
    elif isinstance(data, str):
        if tipo in ("html", "htmlSandbox") or data.lstrip().startswith("<"):
            for m in re.finditer(r"data:image/png;base64,([A-Za-z0-9+/=]+)", data):
                partes.append(guardar_png(m.group(1), out, nombre, idx, figs))
            limpio = re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]+", "", data)
            limpio = re.sub(r"<style.*?</style>|<script.*?</script>", "", limpio, flags=re.S)
            limpio = re.sub(r"<br\s*/?>|</tr>|</p>|</div>", "\n", limpio)
            limpio = re.sub(r"</t[dh]>", " | ", limpio)
            limpio = html.unescape(re.sub(r"<[^>]+>", "", limpio))
            limpio = re.sub(r"\n\s*\n+", "\n", limpio).strip()
            if limpio:
                partes.append(bloque(limpio))
        else:
            partes.append(bloque(ANSI.sub("", data)))
    elif isinstance(data, list):
        for d in data:
            r = texto_resultado(d, out, nombre, idx, figs)
            if r:
                partes.append(r)
    err = res.get("error") or res.get("errorSummary")
    if err:
        partes.append(bloque("ERROR: " + ANSI.sub("", str(err))[:3000]))
    return "\n".join(partes)


def main():
    """Recorre los HTML de la carpeta de entrada y escribe su Markdown y figuras."""
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    (out / "fig").mkdir(parents=True, exist_ok=True)
    for ruta in sorted(src.glob("*.html")):
        h = ruta.read_text(encoding="utf-8")
        m = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", h)
        nb = json.loads(urllib.parse.unquote(base64.b64decode(m.group(1)).decode()))
        nombre = ruta.stem
        lineas = [f"# {nombre}\n"]
        figs = []
        comandos = sorted(nb["commands"], key=lambda c: c.get("position", 0))
        for i, cmd in enumerate(comandos):
            lineas.append(f"\n## Celda {i}\n")
            lineas.append("```python\n" + cmd.get("command", "") + "\n```\n")
            r = texto_resultado(cmd.get("results"), out, nombre, i, figs)
            if r:
                lineas.append("**Salida:**\n\n" + r + "\n")
        (out / f"{nombre}.md").write_text("\n".join(lineas), encoding="utf-8")
        print(nombre, len(comandos), "celdas,", len(figs), "figuras")


if __name__ == "__main__":
    main()
