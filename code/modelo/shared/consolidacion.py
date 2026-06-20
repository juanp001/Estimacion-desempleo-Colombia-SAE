import pandas as pd

from shared.config import CV_ACEPTABLE, CV_CONFIABLE


def clasificar_confiabilidad(cv: float) -> str:
    """Clasifica un coeficiente de variación según el criterio DANE/CEPAL.

    Args:
        cv (float): Coeficiente de variación en porcentaje.

    Returns:
        str: "Confiable" si cv < CV_CONFIABLE, "Aceptable" si
            CV_CONFIABLE <= cv < CV_ACEPTABLE, "No confiable" en otro caso.
    """
    if cv < CV_CONFIABLE:
        return "Confiable"
    elif cv < CV_ACEPTABLE:
        return "Aceptable"
    return "No confiable"


def construir_tabla_final(tabla_entrenamiento: pd.DataFrame, tabla_sintetica: pd.DataFrame) -> pd.DataFrame:
    """Consolida estimaciones EBLUP (con encuesta) y sintéticas (sin encuesta).

    Si un dominio (identificado por la columna DOMINIO) aparece en ambas
    tablas, se conserva únicamente su fila EBLUP —más eficiente al usar la
    encuesta directa— y se descarta la fila sintética correspondiente.

    Args:
        tabla_entrenamiento (pd.DataFrame): Debe contener DOMINIO, PER,
            MES, DEPARTAMENTO, MUNICIPIO, TASA_DESEMPLEO_PCT, CV_PCT y
            TIPO="EBLUP".
        tabla_sintetica (pd.DataFrame): Mismo esquema, con TIPO="SINTETICO".

    Returns:
        pd.DataFrame: Tabla consolidada, ordenada por PER, MES,
            DEPARTAMENTO, MUNICIPIO, con una columna adicional
            CONFIABILIDAD.

    Raises:
        ValueError: Si falta la columna DOMINIO (u otra del esquema
            esperado) en alguna de las dos tablas.
    """
    columnas_esquema = ["DOMINIO", "PER", "MES", "DEPARTAMENTO", "MUNICIPIO",
                         "TASA_DESEMPLEO_PCT", "CV_PCT", "TIPO"]
    for nombre, tabla in [("tabla_entrenamiento", tabla_entrenamiento), ("tabla_sintetica", tabla_sintetica)]:
        faltantes = set(columnas_esquema) - set(tabla.columns)
        if faltantes:
            raise ValueError(f"Columnas faltantes en {nombre}: {sorted(faltantes)}")

    dominios_entrenamiento = set(tabla_entrenamiento["DOMINIO"])
    tabla_sintetica_filtrada = tabla_sintetica[~tabla_sintetica["DOMINIO"].isin(dominios_entrenamiento)]

    n_excluidos = len(tabla_sintetica) - len(tabla_sintetica_filtrada)
    if n_excluidos > 0:
        print(f"{n_excluidos} dominio(s) sin encuesta coinciden con el conjunto de "
              f"entrenamiento; se usa su EBLUP en lugar de la predicción sintética.")

    tabla_final = pd.concat(
        [tabla_entrenamiento[columnas_esquema], tabla_sintetica_filtrada[columnas_esquema]],
        ignore_index=True,
    )
    tabla_final["CONFIABILIDAD"] = tabla_final["CV_PCT"].apply(clasificar_confiabilidad)
    return tabla_final.sort_values(["PER", "MES", "DEPARTAMENTO", "MUNICIPIO"]).reset_index(drop=True)
