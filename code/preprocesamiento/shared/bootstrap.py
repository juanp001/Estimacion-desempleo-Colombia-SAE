"""Varianza de la tasa de desempleo directa (razón de Hájek) por dominio (G7-B3).

La tasa de un dominio es la razón θ̂ = Σ w·y / Σ w (Hájek). Este módulo estima su varianza de dos
formas, ambas con el **dominio como estrato** y la **vivienda como conglomerado**:

- **Bootstrap**: en cada réplica se remuestrean, con reemplazo y dentro de cada dominio, tantas
  viviendas como tiene la muestra del dominio, y se recalcula θ̂ con todas las personas de las
  viviendas elegidas (Morales et al., 2021, p. 61: el bootstrap de una encuesta de fuerza laboral
  remuestrea conglomerados dentro de cada estrato y conserva todos los registros de las viviendas
  seleccionadas). Como θ̂ es una razón de totales, basta con los totales de cada vivienda
  a_k = Σ w·y y b_k = Σ w: θ̂* = Σ a*/Σ b*.
- **Linealización de Taylor** de la razón con la fórmula de conglomerados últimos (DANE,
  metodología GEIH v9, PDF 15; Shiferaw, 2025, PDF 10): v(θ̂) = n/(n−1)·Σ(z_k − z̄)² con
  z_k = (a_k − θ̂·b_k)/Σ b. Sirve de control analítico del bootstrap.

Por qué el dominio y la vivienda. Las áreas metropolitanas y las capitales son unidades de
inclusión forzosa con estimaciones separadas (GEIH v9, PDF 11), así que el dominio funciona como
estrato y su tamaño de muestra queda fijo en cada réplica. En la GEIH se encuesta el conglomerado
completo (todas las viviendas, hogares y personas del segmento, PDF 11): las personas de una misma
vivienda no son independientes y se remuestrean juntas.

Limitación. Los microdatos no traen el estrato interno ni el segmento (~10 viviendas contiguas),
que son las unidades de la varianza oficial (PDF 14-15). Esta varianza es una aproximación: no se
sabe si la varianza del diseño es mayor o menor, ni por cuánto. `modelo/sensibilidad_varianza.py`
muestra cómo responde el modelo si se equivoca.

Funciones puras numpy/pandas; los ejemplos se comprueban con
``python -m doctest preprocesamiento/shared/bootstrap.py``.
"""

import numpy as np
import pandas as pd

# Réplicas que se generan a la vez: limita la memoria a tam_lote × n enteros por dominio.
TAM_LOTE = 100


def totales_por_conglomerado(
    df: pd.DataFrame,
    grupo_cols: list,
    col_conglomerado: str | None,
    col_peso: str = "FEX",
    col_y: str = "DESOCUPADO",
) -> pd.DataFrame:
    """Totales a_k = Σ w·y y b_k = Σ w de cada conglomerado dentro de cada dominio.

    Args:
        df (pd.DataFrame): Una fila por persona con `grupo_cols`, `col_peso`, `col_y` y, si se
            usa, `col_conglomerado`.
        grupo_cols (list[str]): Columnas que definen el dominio (estrato del remuestreo).
        col_conglomerado (str | None): Columna del conglomerado (p. ej. `ID_VIVIENDA`). Con `None`
            cada persona es su propio conglomerado (bootstrap de personas).
        col_peso (str): Factor de expansión.
        col_y (str): Variable indicadora (1 = desocupado).

    Returns:
        pd.DataFrame: Una fila por conglomerado con `grupo_cols`, `A` (Σ w·y), `B` (Σ w) y
            `N_PERSONAS`.

    Casos de uso:
        Paso previo de `varianza_por_dominio`; también permite contar viviendas por dominio.

    Example:
        >>> df = pd.DataFrame({"D": ["x", "x", "x"], "V": [1, 1, 2],
        ...                    "FEX": [2.0, 3.0, 5.0], "DESOCUPADO": [1, 0, 1]})
        >>> totales_por_conglomerado(df, ["D"], "V")
           D  V    A    B  N_PERSONAS
        0  x  1  2.0  5.0           2
        1  x  2  5.0  5.0           1
        >>> len(totales_por_conglomerado(df, ["D"], None))
        3

    Raises:
        ValueError: Si alguna columna de `grupo_cols` o el conglomerado tiene nulos (R-27):
            pandas descarta esas claves al agrupar y el dominio desaparecería sin aviso.
    """
    claves = grupo_cols + ([col_conglomerado] if col_conglomerado else [])
    nulos = {c: int(n) for c, n in df[claves].isna().sum().items() if n}
    if nulos:
        raise ValueError(f"Claves nulas en el dominio o el conglomerado: {nulos}")
    tmp = df[grupo_cols].copy()
    tmp["A"] = (df[col_peso] * df[col_y]).to_numpy(dtype=float)
    tmp["B"] = df[col_peso].to_numpy(dtype=float)
    tmp["N_PERSONAS"] = 1
    if col_conglomerado is None:
        return tmp.reset_index(drop=True)
    tmp[col_conglomerado] = df[col_conglomerado].to_numpy()
    return tmp.groupby(grupo_cols + [col_conglomerado], as_index=False, sort=True)[
        ["A", "B", "N_PERSONAS"]
    ].sum()


def replicas_razon(
    a: np.ndarray,
    b: np.ndarray,
    num_replicas: int,
    rng: np.random.Generator,
    tam_lote: int = TAM_LOTE,
) -> np.ndarray:
    """Réplicas bootstrap de la razón Σa/Σb remuestreando los n conglomerados con reemplazo.

    Cada réplica toma n índices uniformes con reemplazo (mismo tamaño que la muestra) y calcula
    Σ a*/Σ b*.

    Args:
        a (np.ndarray): Totales Σ w·y de cada conglomerado, shape (n,).
        b (np.ndarray): Totales Σ w de cada conglomerado, shape (n,).
        num_replicas (int): Número de réplicas B.
        rng (np.random.Generator): Generador aleatorio (fija la reproducibilidad).
        tam_lote (int): Réplicas que se generan a la vez.

    Returns:
        np.ndarray: Las B razones replicadas, shape (B,).

    Casos de uso:
        Varianza bootstrap de la tasa de un dominio:
        `np.var(replicas_razon(a, b, 2000, rng), ddof=1)`.

    Example:
        >>> rng = np.random.default_rng(0)
        >>> r = replicas_razon(np.array([1.0, 0.0]), np.array([1.0, 1.0]), 1000, rng)
        >>> r.shape, set(np.unique(r)) <= {0.0, 0.5, 1.0}
        ((1000,), True)
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    n = len(a)
    salida = np.empty(num_replicas)
    for inicio in range(0, num_replicas, tam_lote):
        k = min(tam_lote, num_replicas - inicio)
        idx = rng.integers(0, n, size=(k, n))
        salida[inicio : inicio + k] = a[idx].sum(axis=1) / b[idx].sum(axis=1)
    return salida


def varianza_taylor_razon(a: np.ndarray, b: np.ndarray) -> float:
    """Varianza de la razón Σa/Σb por linealización de Taylor (conglomerados últimos).

    v(θ̂) = n/(n−1)·Σ(z_k − z̄)², con z_k = (a_k − θ̂·b_k)/Σ b y θ̂ = Σa/Σb: la variable
    linealizada de la razón (GEIH v9, PDF 15) con muestreo de conglomerados con reemplazo
    dentro del estrato.

    Args:
        a (np.ndarray): Totales Σ w·y de cada conglomerado, shape (n,), n ≥ 2.
        b (np.ndarray): Totales Σ w de cada conglomerado, shape (n,).

    Returns:
        float: Varianza estimada de θ̂ (en proporción, no en porcentaje).

    Casos de uso:
        Control analítico del bootstrap: con muchos conglomerados ambos deben coincidir.

    Example:
        >>> round(varianza_taylor_razon(np.array([1.0, 0.0, 2.0, 1.0]), np.full(4, 2.0)), 6)
        0.041667
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    n = len(a)
    theta = a.sum() / b.sum()
    z = (a - theta * b) / b.sum()
    return float(n / (n - 1) * np.sum((z - z.mean()) ** 2))


def varianza_por_dominio(
    df: pd.DataFrame,
    grupo_cols: list,
    col_conglomerado: str | None,
    num_replicas: int,
    seed: int,
    col_peso: str = "FEX",
    col_y: str = "DESOCUPADO",
) -> pd.DataFrame:
    """Tasa de Hájek, varianza bootstrap e IC percentil y varianza de Taylor por dominio.

    El remuestreo es independiente en cada dominio (estrato) y conserva su número de
    conglomerados. Un solo generador `np.random.default_rng(seed)` recorre los dominios en orden,
    así que el resultado es reproducible.

    Args:
        df (pd.DataFrame): Una fila por persona (ver `totales_por_conglomerado`).
        grupo_cols (list[str]): Columnas que definen el dominio.
        col_conglomerado (str | None): Conglomerado del remuestreo; `None` = personas.
        num_replicas (int): Réplicas bootstrap B.
        seed (int): Semilla del generador.
        col_peso (str): Factor de expansión.
        col_y (str): Variable indicadora.

    Returns:
        pd.DataFrame: `grupo_cols` más `TASA_DESEMPLEO` (proporción), `MEDIA_BOOTSTRAP`,
            `VAR_BOOTSTRAP`, `SE_BOOTSTRAP`, `IC_INF_2.5`, `IC_SUP_97.5`, `VAR_TAYLOR`,
            `SE_TAYLOR`, `N_CONGLOMERADOS` y `N_PERSONAS` (personas que vio el remuestreo).

    Raises:
        ValueError: Si un dominio tiene menos de 2 conglomerados (R-27): la varianza de Taylor
            divide por n − 1 y el bootstrap no tendría variación.

    Casos de uso:
        `EstimacionDirecta` lo usa con `ID_VIVIENDA` (varianza del modelo) y la sensibilidad
        del modelo con `None` (personas) para comparar.

    Example:
        >>> rng = np.random.default_rng(1)
        >>> df = pd.DataFrame({"D": ["x"] * 400, "V": np.repeat(np.arange(200), 2),
        ...                    "FEX": 1.0, "DESOCUPADO": rng.integers(0, 2, 400)})
        >>> r = varianza_por_dominio(df, ["D"], "V", 500, 42)
        >>> int(r["N_CONGLOMERADOS"].iloc[0]), int(r["N_PERSONAS"].iloc[0])
        (200, 400)
        >>> bool(abs(r["SE_BOOTSTRAP"].iloc[0] / r["SE_TAYLOR"].iloc[0] - 1) < 0.15)
        True
    """
    totales = totales_por_conglomerado(
        df, grupo_cols, col_conglomerado, col_peso, col_y
    )
    rng = np.random.default_rng(seed)
    filas = []
    for clave, g in totales.groupby(grupo_cols, sort=True):
        a = g["A"].to_numpy()
        b = g["B"].to_numpy()
        if len(a) < 2:
            raise ValueError(
                f"El dominio {clave} tiene {len(a)} conglomerado(s): no se puede estimar su varianza"
            )
        replicas = replicas_razon(a, b, num_replicas, rng)
        var_taylor = varianza_taylor_razon(a, b)
        clave = clave if isinstance(clave, tuple) else (clave,)
        fila = dict(zip(grupo_cols, clave))
        fila.update(
            {
                "TASA_DESEMPLEO": a.sum() / b.sum(),
                "MEDIA_BOOTSTRAP": replicas.mean(),
                "VAR_BOOTSTRAP": replicas.var(ddof=1),
                "SE_BOOTSTRAP": replicas.std(ddof=1),
                "IC_INF_2.5": np.percentile(replicas, 2.5),
                "IC_SUP_97.5": np.percentile(replicas, 97.5),
                "VAR_TAYLOR": var_taylor,
                "SE_TAYLOR": np.sqrt(var_taylor),
                "N_CONGLOMERADOS": len(a),
                "N_PERSONAS": int(g["N_PERSONAS"].sum()),
            }
        )
        filas.append(fila)
    return pd.DataFrame(filas)
