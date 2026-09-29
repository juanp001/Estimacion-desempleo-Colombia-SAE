"""Consolidación de las estimaciones EBLUP (con encuesta) y sintéticas (sin encuesta)."""

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


def construir_tabla_final(
    tabla_entrenamiento: pd.DataFrame,
    tabla_sintetica: pd.DataFrame,
    dim_divipola: pd.DataFrame,
) -> pd.DataFrame:
    """Consolida estimaciones EBLUP (con encuesta) y sintéticas (sin encuesta).

    Los dominios se identifican por código DIVIPOLA (columna DOMINIO =
    PER_MES_CODIGO_MUNICIPIO), no por nombre: las dos fuentes escriben los
    nombres con distinto formato («CAUCA» frente a «Cauca»). Los nombres de
    departamento y municipio de la tabla final se toman de `dim_divipola` por
    CODIGO_MUNICIPIO, de modo que todos quedan con la nomenclatura oficial.

    Si un dominio aparece en ambas tablas, se conserva únicamente su fila EBLUP
    —más eficiente al usar la encuesta directa— y se descarta la sintética.

    Args:
        tabla_entrenamiento (pd.DataFrame): Debe contener DOMINIO, PER, MES,
            CODIGO_DEPARTAMENTO, CODIGO_MUNICIPIO, TASA_DESEMPLEO_PCT, CV_PCT y
            TIPO="EBLUP".
        tabla_sintetica (pd.DataFrame): Mismo esquema, con TIPO="SINTETICO".
        dim_divipola (pd.DataFrame): Nomenclatura DIVIPOLA con CODIGO_MUNICIPIO,
            DEPARTAMENTO y MUNICIPIO (una fila por municipio).

    Returns:
        pd.DataFrame: Tabla consolidada, ordenada por PER, MES y
            CODIGO_MUNICIPIO, con DEPARTAMENTO y MUNICIPIO oficiales y una
            columna adicional CONFIABILIDAD (ver `clasificar_confiabilidad`).

    Raises:
        ValueError: Si falta alguna columna del esquema esperado en las tablas
            de entrada, o si algún CODIGO_MUNICIPIO no existe en `dim_divipola`.

    Example:
        >>> df_final = construir_tabla_final(
        ...     tabla_entrenamiento, tabla_sintetica, spark.table(TBL_DIM_DIVIPOLA).toPandas()
        ... )
    """
    columnas_esquema = [
        "DOMINIO",
        "PER",
        "MES",
        "CODIGO_DEPARTAMENTO",
        "CODIGO_MUNICIPIO",
        "TASA_DESEMPLEO_PCT",
        "CV_PCT",
        "TIPO",
    ]
    for nombre, tabla in [
        ("tabla_entrenamiento", tabla_entrenamiento),
        ("tabla_sintetica", tabla_sintetica),
    ]:
        faltantes = set(columnas_esquema) - set(tabla.columns)
        if faltantes:
            raise ValueError(f"Columnas faltantes en {nombre}: {sorted(faltantes)}")

    dominios_entrenamiento = set(tabla_entrenamiento["DOMINIO"])
    tabla_sintetica_filtrada = tabla_sintetica[
        ~tabla_sintetica["DOMINIO"].isin(dominios_entrenamiento)
    ]

    n_excluidos = len(tabla_sintetica) - len(tabla_sintetica_filtrada)
    if n_excluidos > 0:
        print(
            f"{n_excluidos} dominio(s) sin encuesta coinciden con el conjunto de "
            f"entrenamiento; se usa su EBLUP en lugar de la predicción sintética."
        )

    tabla_final = pd.concat(
        [
            tabla_entrenamiento[columnas_esquema],
            tabla_sintetica_filtrada[columnas_esquema],
        ],
        ignore_index=True,
    )
    nombres = dim_divipola[["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO"]]
    tabla_final = tabla_final.merge(
        nombres, on="CODIGO_MUNICIPIO", how="left", validate="many_to_one"
    )
    sin_nombre = tabla_final.loc[tabla_final["MUNICIPIO"].isna(), "CODIGO_MUNICIPIO"]
    if len(sin_nombre):
        raise ValueError(
            f"Códigos sin correspondencia en dim_divipola: {sorted(sin_nombre)}"
        )

    tabla_final["CONFIABILIDAD"] = tabla_final["CV_PCT"].apply(clasificar_confiabilidad)
    orden = columnas_esquema[:5] + ["DEPARTAMENTO", "MUNICIPIO"] + columnas_esquema[5:]
    return (
        tabla_final[orden + ["CONFIABILIDAD"]]
        .sort_values(["PER", "MES", "CODIGO_MUNICIPIO"])
        .reset_index(drop=True)
    )
