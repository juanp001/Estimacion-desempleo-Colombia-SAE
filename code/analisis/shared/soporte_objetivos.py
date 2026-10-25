"""Soporte de las candidatas en los municipios objetivo (R-02).

El objetivo del modelo es predecir los municipios sin encuesta con ``x'β̂``, pero la selección de
covariables solo mira la asociación en los 23 dominios urbanos. Una covariable cuyos valores en
los objetivos quedan fuera del rango observado en los dominios obliga a **extrapolar**: la
varianza del predictor sintético, ``x'Cov(β̂)x + Â``, crece con la distancia de ``x`` a la muestra
(Morales et al., p. 441) y un buen ajuste dentro de la muestra puede dar predicciones absurdas
fuera de ella (p. 453).

Este módulo mide ese soporte **sin usar la variable respuesta**, para que se reporte en la ficha
de decisión y en la trazabilidad antes de que la asociación pueda decidir:

* ``Prop_en_rango``: proporción de los municipios objetivo dentro de [mín, máx] de los dominios.
  Es una **advertencia**, no un filtro (decisión del proyecto): la covariable sigue compitiendo y
  su motivo en la ficha lo dice.
* ``N_faltantes``: municipios objetivo sin dato. Esta sí es una condición del catálogo (iii): sin
  dato no hay predicción, así que la covariable no es candidata
  (`catalogo_literatura.resolver_catalogo`).
"""

import numpy as np
import pandas as pd


def columnas_incompletas(df_objetivos: pd.DataFrame, codigos: list) -> list:
    """Candidatas con algún dato faltante (o ausentes) en los municipios objetivo.

    Args:
        df_objetivos (pd.DataFrame): Municipios objetivo, una fila por municipio, con una columna
            por código de indicador (valores numéricos; un valor no numérico cuenta como faltante).
        codigos (list[str]): Códigos de indicador a revisar.

    Returns:
        list[str]: Códigos con al menos un faltante en los objetivos, o que no existen en la
            tabla de objetivos.

    Example:
        >>> o = pd.DataFrame({"A": [1.0, 2.0], "B": [1.0, None]})
        >>> columnas_incompletas(o, ["A", "B", "C"])
        ['B', 'C']
    """
    incompletas = []
    for codigo in codigos:
        if codigo not in df_objetivos.columns:
            incompletas.append(codigo)
        elif pd.to_numeric(df_objetivos[codigo], errors="coerce").isna().any():
            incompletas.append(codigo)
    return incompletas


def tabla_soporte(
    df_dominios: pd.DataFrame,
    df_objetivos: pd.DataFrame,
    codigos: list,
    alias: dict = None,
    minimo: float = 0.80,
) -> pd.DataFrame:
    """Soporte de cada candidata: qué parte de los objetivos cae dentro del rango de los dominios.

    Args:
        df_dominios (pd.DataFrame): Dominios con encuesta, con una columna por candidata.
        df_objetivos (pd.DataFrame): Municipios objetivo, con las mismas columnas.
        codigos (list[str]): Candidatas a evaluar.
        alias (dict | None): Mapa código → alias legible.
        minimo (float): Proporción dentro del rango por debajo de la cual se advierte. Es una
            convención del proyecto (`SOPORTE_MINIMO`), no un valor de Morales et al.

    Returns:
        pd.DataFrame: Una fila por candidata con `Alias`, `Codigo`, `N_objetivos`,
            `N_faltantes`, `Min_dominios`, `Max_dominios`, `N_fuera_rango`, `Prop_en_rango` y
            `Soporte` (``"completo"`` si ``Prop_en_rango >= minimo``, ``"advertencia"`` si no,
            ``"sin dato"`` si hay faltantes). Los faltantes cuentan como fuera de rango en
            `Prop_en_rango`.

    Example:
        >>> d = pd.DataFrame({"A": [0.0, 1.0, 2.0]})
        >>> o = pd.DataFrame({"A": [0.5, 3.0, 1.5, 4.0]})
        >>> t = tabla_soporte(d, o, ["A"])
        >>> t[["N_fuera_rango", "Prop_en_rango", "Soporte"]].values.tolist()
        [[2, 0.5, 'advertencia']]
    """
    alias = alias or {}
    filas = []
    for codigo in codigos:
        dom = pd.to_numeric(df_dominios[codigo], errors="coerce").to_numpy(dtype=float)
        obj = pd.to_numeric(df_objetivos[codigo], errors="coerce").to_numpy(dtype=float)
        minimo_dom, maximo_dom = float(np.nanmin(dom)), float(np.nanmax(dom))
        faltantes = int(np.isnan(obj).sum())
        dentro = (obj >= minimo_dom) & (obj <= maximo_dom)
        proporcion = float(dentro.sum() / len(obj))
        if faltantes:
            soporte = "sin dato"
        elif proporcion >= minimo:
            soporte = "completo"
        else:
            soporte = "advertencia"
        filas.append(
            {
                "Alias": alias.get(codigo, codigo),
                "Codigo": codigo,
                "N_objetivos": len(obj),
                "N_faltantes": faltantes,
                "Min_dominios": minimo_dom,
                "Max_dominios": maximo_dom,
                "N_fuera_rango": int(len(obj) - dentro.sum()),
                "Prop_en_rango": round(proporcion, 3),
                "Soporte": soporte,
            }
        )
    return pd.DataFrame(filas)
