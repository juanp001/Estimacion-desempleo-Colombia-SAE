"""Arranque común de los notebooks: rutas de importación (R-67).

Cada notebook calcula `code/` con `dbutils` (solo existe en Databricks) y lo agrega a `sys.path`
antes de importar este módulo; lo que se repetía entre notebooks vive aquí.
"""

import os
import sys


def agregar_rutas(code_dir: str, *subcarpetas: str) -> None:
    """Agrega `code/` y, si se piden, sus subcarpetas al inicio de `sys.path`.

    Args:
        code_dir (str): Ruta absoluta del directorio `code/` del repositorio.
        *subcarpetas (str): Nombres de subcarpetas de `code/` que también deben poder
            importarse con la forma corta, p. ej. `"modelo"` para `from shared.config import ...`.

    Returns:
        None

    Example:
        >>> import sys
        >>> agregar_rutas("/tmp/code", "modelo")
        >>> sys.path[0], os.path.basename(sys.path[1])
        ('/tmp/code', 'modelo')

    Casos de uso:
        - Los notebooks de `modelo/`, que importan su `shared/` por la forma corta y
          `preprocesamiento.shared…` por la completa.
    """
    rutas = [code_dir] + [os.path.join(code_dir, sub) for sub in subcarpetas]
    for ruta in reversed(rutas):
        if ruta in sys.path:
            sys.path.remove(ruta)
        sys.path.insert(0, ruta)
