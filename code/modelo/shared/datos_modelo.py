"""Preparación de datos común a los notebooks del modelo (R-40).

`fay_herriot.py` y `sensibilidad_varianza.py` repetían la misma lectura del período, el mismo
mapa de alias de las covariables y la misma preparación de los municipios objetivo. Este
módulo deja una sola versión, con funciones de pandas puras (la lectura de Spark queda en el
notebook):

- `periodo_unico`: período (PER, MES, PERIODO, N_MESES_VENTANA) de la tabla de dominios, con
  error si hay más de uno (el benchmarking se define por período).
- `alias_desde_catalogo`: mapa código → alias desde el catálogo de literatura (R-63), en lugar
  de leer la tabla de documentación `trazabilidad_covariables`.
- `preparar_municipios`: renombra los códigos de indicador de los municipios objetivo a los
  alias del modelo, valida que no falte ninguna covariable y arma la matriz de diseño.
"""

import numpy as np
import pandas as pd

from analisis.shared.catalogo_literatura import CATALOGO_LITERATURA, mapas_catalogo


def periodo_unico(df: pd.DataFrame, tabla: str) -> dict:
    """Período único de la tabla de dominios del modelo.

    Args:
        df (pd.DataFrame): Dominios con las columnas `PER`, `MES`, `PERIODO` y
            `N_MESES_VENTANA` (salida de `covariables_seleccionadas`).
        tabla (str): Nombre de la tabla de origen, para el mensaje de error.

    Returns:
        dict: `{"PER": int, "MES": int, "PERIODO": str, "N_MESES_VENTANA": int}`.

    Raises:
        ValueError: Si la tabla trae más de un período o ninguno.

    Example:
        >>> df = pd.DataFrame({"PER": [2018, 2018], "MES": [12, 12],
        ...                    "PERIODO": ["Ene-Dic 2018"] * 2, "N_MESES_VENTANA": [12, 12]})
        >>> periodo_unico(df, "tabla")
        {'PER': 2018, 'MES': 12, 'PERIODO': 'Ene-Dic 2018', 'N_MESES_VENTANA': 12}

    Casos de uso:
        - Fijar la ventana del benchmarking de nivel 1 y la cifra DANE de control.
        - Agregar PER y MES a las tablas de diagnóstico que se escriben.
    """
    periodos = df[["PER", "MES", "PERIODO", "N_MESES_VENTANA"]].drop_duplicates()
    if len(periodos) != 1:
        raise ValueError(
            f"El modelo se define por período y hay {len(periodos)} períodos en {tabla}."
        )
    fila = periodos.iloc[0]
    return {
        "PER": int(fila["PER"]),
        "MES": int(fila["MES"]),
        "PERIODO": str(fila["PERIODO"]),
        "N_MESES_VENTANA": int(fila["N_MESES_VENTANA"]),
    }


def alias_desde_catalogo(catalogo: list = None) -> dict:
    """Mapa código de indicador → alias del catálogo de literatura (R-63).

    La tabla `covariables_seleccionadas` usa los alias del catálogo y `municipios_sin_encuesta`
    los códigos de indicador. El mapa sale del catálogo mismo (`mapas_catalogo`), no de la
    tabla de documentación `trazabilidad_covariables`, que así deja de estar en la cadena.

    Args:
        catalogo (list[dict] | None): Entradas con `codigo`, `alias`, `signo_esperado` y
            `dimension`. Por defecto `CATALOGO_LITERATURA` completo.

    Returns:
        dict: `{codigo: alias}`.

    Example:
        >>> alias_desde_catalogo([{"codigo": "001", "alias": "A", "signo_esperado": 1,
        ...                        "dimension": "x"}])
        {'001': 'A'}

    Casos de uso:
        - Reconocer qué columnas de `covariables_seleccionadas` son covariables.
        - Renombrar las covariables de los municipios objetivo a los alias del modelo.
    """
    _, alias, _, _ = mapas_catalogo(
        CATALOGO_LITERATURA if catalogo is None else catalogo
    )
    return alias


def preparar_municipios(
    df_new: pd.DataFrame, covars: list, alias_a_codigo: dict
) -> tuple:
    """Renombra, valida y arma la matriz de diseño de los municipios objetivo.

    Args:
        df_new (pd.DataFrame): Municipios objetivo (`municipios_sin_encuesta`), con las
            covariables con su código de indicador y la columna `MUNICIPIO`.
        covars (list[str]): Alias de las covariables del modelo, en el orden de β̂.
        alias_a_codigo (dict): Mapa alias → código de indicador.

    Returns:
        tuple[pd.DataFrame, np.ndarray]: (`df_new` con las covariables renombradas a su
            alias, matriz de diseño X con intercepto, shape (m, p), en float).

    Raises:
        ValueError: Si falta alguna covariable o algún municipio no tiene valor en ella
            (el mensaje lista los municipios).

    Example:
        >>> df_new = pd.DataFrame({"MUNICIPIO": ["a", "b"], "001": [1.0, 3.0]})
        >>> df_mun, X = preparar_municipios(df_new, ["A"], {"A": "001"})
        >>> list(df_mun.columns), X.tolist()
        (['MUNICIPIO', 'A'], [[1.0, 1.0], [1.0, 3.0]])

    Casos de uso:
        - Predicción sintética de los municipios con el benchmark (`fay_herriot.py`).
        - Escenarios de varianza de la especificación de referencia (`sensibilidad_varianza.py`).
    """
    df_new = df_new.rename(
        columns={
            alias_a_codigo[alias]: alias
            for alias in covars
            if alias_a_codigo.get(alias) in df_new.columns
        }
    )
    faltantes = [c for c in covars if c not in df_new.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en los municipios objetivo: {faltantes}")

    sin_dato = df_new[covars].isna().any(axis=1)
    if sin_dato.any():
        raise ValueError(
            f"{int(sin_dato.sum())} municipios objetivo no tienen valor para alguna covariable "
            f"del modelo y no admiten predicción sintética: "
            f"{df_new.loc[sin_dato, 'MUNICIPIO'].tolist()}. Revisar la completitud reportada "
            f"por dominios_sin_encuesta."
        )

    X = np.column_stack(
        [np.ones(len(df_new))] + [df_new[c].to_numpy(dtype=float) for c in covars]
    )
    return df_new, X
