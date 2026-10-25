"""Guardado común de las figuras del modelo (R-45).

El Fay-Herriot clásico (`fay_herriot.py`, prefijo ``fh_``) y el espacial
(`fay_herriot_espacial.py`, prefijo ``fhe_``) siguen la misma regla: cada figura se muestra en el
notebook y se guarda como PNG en el volumen `VOLUMEN_FIGURAS_MODELO` del esquema ``modelo``
(que el bundle no crea: debe existir antes de correr el job). Las figuras del análisis
(`analisis/`) van aparte, al volumen de preprocesamiento.
"""

import os


def guardar_figura(fig, nombre: str, prefijo: str, volumen: str) -> str:
    """Guarda una figura de matplotlib como PNG; si no puede, avisa y sigue.

    La falta del volumen no debe detener un job de modelado: la figura se muestra de todos
    modos en el notebook.

    Args:
        fig (matplotlib.figure.Figure): Figura a guardar.
        nombre (str): Nombre del archivo sin extensión.
        prefijo (str): Prefijo del archivo (``"fh_"`` clásico, ``"fhe_"`` espacial).
        volumen (str): Carpeta destino (un volumen de Unity Catalog).

    Returns:
        str: Ruta del PNG escrito, o cadena vacía si no se pudo guardar.

    Example:
        >>> import tempfile, matplotlib
        >>> matplotlib.use("Agg")
        >>> import matplotlib.pyplot as plt
        >>> fig, _ = plt.subplots()
        >>> ruta = guardar_figura(fig, "prueba", "fh_", tempfile.mkdtemp())
        >>> os.path.basename(ruta)
        'fh_prueba.png'
    """
    ruta = os.path.join(volumen, f"{prefijo}{nombre}.png")
    try:
        fig.savefig(ruta, dpi=150, bbox_inches="tight")
    except Exception as error:
        print(f"(figura {nombre} no guardada: {type(error).__name__})")
        return ""
    return ruta
