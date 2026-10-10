"""Consolidación de las estimaciones por dominio (EBLUP) y por municipio (sintéticas)."""

import pandas as pd

from shared.config import CV_ACEPTABLE, CV_CONFIABLE


def clasificar_confiabilidad(cv: float) -> str:
    """Clasifica un coeficiente de variación con los umbrales de `config.py`.

    Args:
        cv (float): Coeficiente de variación en porcentaje.

    Returns:
        str: "Confiable" si cv < CV_CONFIABLE, "Aceptable" si
            CV_CONFIABLE <= cv < CV_ACEPTABLE, "No confiable" en otro caso.

    Example:
        >>> clasificar_confiabilidad(12.0)
        'Aceptable'
    """
    if cv < CV_CONFIABLE:
        return "Confiable"
    elif cv < CV_ACEPTABLE:
        return "Aceptable"
    return "No confiable"


# Columnas comunes de las dos tablas de entrada.
COLUMNAS_ESQUEMA = [
    "PER",
    "MES",
    "CODIGO",
    "TASA_DESEMPLEO_PCT",
    "TASA_SIN_AJUSTE_PCT",
    "LAMBDA",
    "CV_PCT",
    "TIPO",
]


def construir_tabla_final(
    tabla_dominios: pd.DataFrame,
    tabla_municipios: pd.DataFrame,
    dim_dominio: pd.DataFrame,
    dim_divipola: pd.DataFrame,
) -> pd.DataFrame:
    """Une las estimaciones de los dominios y de los municipios objetivo en una sola tabla.

    Hay dos niveles, que se distinguen en la columna NIVEL:

    * ``DOMINIO``: los 23 dominios con estimación directa (ciudad o ciudad A.M.), con el EBLUP
      ajustado al total de las 23 ciudades (benchmarking de nivel 1). ``CODIGO`` es el código
      del dominio (DIVIPOLA de la capital) y ``NOMBRE`` el nombre publicado («Cali A.M.»).
    * ``MUNICIPIO``: los municipios objetivo sin estimación directa propia, con la predicción
      sintética; los que pertenecen a un dominio A.M. (Cali y Yumbo) llevan además el ajuste
      al valor de su dominio (nivel 2) y ``CODIGO_DOMINIO_PADRE``.

    Un mismo código puede aparecer en los dos niveles (76001 es Cali A.M. y el municipio de
    Cali): la clave de una fila es NIVEL + CODIGO + PER + MES. Los nombres se toman por código
    de ``dim_dominio`` (dominios) y ``dim_divipola`` (municipios y departamentos), porque las
    fuentes escriben los nombres con distinto formato.

    Args:
        tabla_dominios (pd.DataFrame): Columnas de ``COLUMNAS_ESQUEMA`` (CODIGO = código del
            dominio).
        tabla_municipios (pd.DataFrame): Columnas de ``COLUMNAS_ESQUEMA`` más
            ``CODIGO_DOMINIO_PADRE`` (CODIGO = código del municipio).
        dim_dominio (pd.DataFrame): ``dim_dominio_geih`` con CODIGO_DOMINIO y NOMBRE_DOMINIO.
        dim_divipola (pd.DataFrame): Nomenclatura DIVIPOLA con CODIGO_MUNICIPIO, MUNICIPIO y
            DEPARTAMENTO (una fila por municipio).

    Returns:
        pd.DataFrame: Una fila por dominio y por municipio objetivo, ordenada por NIVEL y
            CODIGO, con NIVEL, PER, MES, DEPARTAMENTO, CODIGO, NOMBRE, CODIGO_DOMINIO_PADRE,
            TIPO, TASA_DESEMPLEO_PCT, TASA_SIN_AJUSTE_PCT, LAMBDA, CV_PCT y CONFIABILIDAD.

    Raises:
        ValueError: Si falta alguna columna del esquema o algún código no tiene nombre.

    Example:
        >>> df_final = construir_tabla_final(
        ...     tabla_dominios, tabla_municipios,
        ...     spark.table(TBL_DIM_DOMINIO).toPandas(), spark.table(TBL_DIM_DIVIPOLA).toPandas(),
        ... )
    """
    for nombre, tabla, extra in [
        ("tabla_dominios", tabla_dominios, []),
        ("tabla_municipios", tabla_municipios, ["CODIGO_DOMINIO_PADRE"]),
    ]:
        faltantes = set(COLUMNAS_ESQUEMA + extra) - set(tabla.columns)
        if faltantes:
            raise ValueError(f"Columnas faltantes en {nombre}: {sorted(faltantes)}")

    nombres_mun = dim_divipola[
        ["CODIGO_MUNICIPIO", "MUNICIPIO", "DEPARTAMENTO"]
    ].rename(columns={"CODIGO_MUNICIPIO": "CODIGO"})
    nombres_dom = (
        dim_dominio[["CODIGO_DOMINIO", "NOMBRE_DOMINIO"]]
        .drop_duplicates()
        .rename(columns={"CODIGO_DOMINIO": "CODIGO", "NOMBRE_DOMINIO": "NOMBRE"})
        .merge(nombres_mun[["CODIGO", "DEPARTAMENTO"]], on="CODIGO", how="left")
    )

    dominios = tabla_dominios[COLUMNAS_ESQUEMA].merge(
        nombres_dom, on="CODIGO", how="left", validate="many_to_one"
    )
    dominios["NIVEL"] = "DOMINIO"
    dominios["CODIGO_DOMINIO_PADRE"] = None

    municipios = (
        tabla_municipios[COLUMNAS_ESQUEMA + ["CODIGO_DOMINIO_PADRE"]]
        .merge(nombres_mun, on="CODIGO", how="left", validate="many_to_one")
        .rename(columns={"MUNICIPIO": "NOMBRE"})
    )
    municipios["NIVEL"] = "MUNICIPIO"

    tabla_final = pd.concat([dominios, municipios], ignore_index=True)
    sin_nombre = tabla_final.loc[tabla_final["NOMBRE"].isna(), ["NIVEL", "CODIGO"]]
    if len(sin_nombre):
        raise ValueError(
            f"Códigos sin nombre en las dimensiones: {sin_nombre.values.tolist()}"
        )

    tabla_final["CONFIABILIDAD"] = tabla_final["CV_PCT"].apply(clasificar_confiabilidad)
    orden = [
        "NIVEL",
        "PER",
        "MES",
        "DEPARTAMENTO",
        "CODIGO",
        "NOMBRE",
        "CODIGO_DOMINIO_PADRE",
        "TIPO",
        "TASA_DESEMPLEO_PCT",
        "TASA_SIN_AJUSTE_PCT",
        "LAMBDA",
        "CV_PCT",
        "CONFIABILIDAD",
    ]
    return (
        tabla_final[orden]
        .sort_values(["NIVEL", "PER", "MES", "CODIGO"])
        .reset_index(drop=True)
    )
