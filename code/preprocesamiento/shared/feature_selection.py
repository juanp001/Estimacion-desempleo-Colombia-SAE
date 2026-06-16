import pandas as pd
import numpy as np

# COMMAND ----------

def filtrar_columnas_sin_na(df: pd.DataFrame) -> pd.DataFrame:
    """Conserva solo las columnas sin ningún valor faltante.

    Descarta covariables con al menos un NA para garantizar que todos los
    dominios tengan información completa antes de calcular correlaciones
    o estimar modelos.

    Args:
        df (pd.DataFrame): DataFrame de covariables (filas = dominios,
            columnas = indicadores).

    Returns:
        pd.DataFrame: Subconjunto de df con solo las columnas sin NAs.

    Raises:
        ValueError: Si df está vacío.

    Example:
        >>> df_limpio = filtrar_columnas_sin_na(df_covariables)
        >>> print(df_limpio.shape)
    """
    if df.empty:
        raise ValueError("El DataFrame está vacío.")

    cols_sin_na = df.columns[df.isna().sum() == 0].tolist()
    n_eliminadas = df.shape[1] - len(cols_sin_na)
    print(f"Filtro NA: {df.shape[1]} → {len(cols_sin_na)} variables ({n_eliminadas} eliminadas)")
    return df[cols_sin_na]


def filtrar_varianza_cero(df: pd.DataFrame, umbral: float = 0.00001) -> pd.DataFrame:
    """Elimina columnas cuya varianza esté por debajo del umbral.

    Variables casi constantes producen singularidad en la matriz de diseño
    de los modelos de regresión (colinealidad con el intercepto). El umbral
    permite tolerar varianzas numéricamente pequeñas sin eliminar variables
    con tasas muy bajas pero con variación real.

    Args:
        df (pd.DataFrame): DataFrame de covariables numéricas.
        umbral (float): Varianza mínima aceptable. Columnas con var < umbral
            se descartan.

    Returns:
        pd.DataFrame: DataFrame sin las columnas de varianza casi cero.

    Raises:
        ValueError: Si df está vacío o no contiene columnas numéricas.

    Example:
        >>> df_filtrado = filtrar_varianza_cero(df_sin_na, umbral=0.00001)
        >>> print(df_filtrado.shape)
    """
    if df.empty:
        raise ValueError("El DataFrame está vacío.")

    varianzas = df.var()
    cols_con_varianza = varianzas[varianzas > umbral].index.tolist()
    cols_eliminadas = [c for c in df.columns if c not in cols_con_varianza]

    print(
        f"Filtro varianza (umbral={umbral}): {df.shape[1]} → {len(cols_con_varianza)} variables "
        f"({len(cols_eliminadas)} eliminadas: {cols_eliminadas})"
    )
    return df[cols_con_varianza]


def seleccionar_variables_por_correlacion(
    df_covariables: pd.DataFrame,
    df_metadata: pd.DataFrame,
    variable_objetivo: str,
    df_diccionario: pd.DataFrame,
    modo: str = "top_n",
    valor: float = 12,
) -> tuple[list, pd.DataFrame]:
    """Selecciona covariables según su correlación de Pearson con la variable objetivo.

    Soporta dos estrategias: elegir las N variables con mayor correlación
    absoluta ("top_n") o seleccionar todas las que superen un umbral ("threshold").

    Args:
        df_covariables (pd.DataFrame): Covariables candidatas post-filtros
            (filas = dominios, columnas = indicadores).
        df_metadata (pd.DataFrame): DataFrame original que contiene la
            variable objetivo (mismas filas que df_covariables).
        variable_objetivo (str): Nombre de la columna objetivo
            (ej. "TASA_DESEMPLEO_PCT").
        df_diccionario (pd.DataFrame): Diccionario de TerriData con columnas
            CODIGO_INDICADOR, INDICADOR y DIMENSION.
        modo (str): Estrategia de selección: "top_n" o "threshold".
        valor (float): Si modo="top_n", número de variables a seleccionar.
            Si modo="threshold", umbral mínimo de correlación absoluta.

    Returns:
        tuple[list, pd.DataFrame]: (variables_ganadoras, df_reporte)
            - variables_ganadoras: Códigos de las variables seleccionadas.
            - df_reporte: Tabla con Puesto, Código, Dimensión, Nombre,
              Correlación real y absoluta.

    Raises:
        ValueError: Si modo no es "top_n" ni "threshold".

    Example:
        >>> ganadoras, reporte = seleccionar_variables_por_correlacion(
        ...     df_covariables=df_filtrado,
        ...     df_metadata=df,
        ...     variable_objetivo="TASA_DESEMPLEO_PCT",
        ...     df_diccionario=df_diccionario,
        ...     modo="threshold",
        ...     valor=0.4,
        ... )
    """
    if modo not in ("top_n", "threshold"):
        raise ValueError(f"modo debe ser 'top_n' o 'threshold', recibido: '{modo}'")

    correlaciones = {
        col: df_covariables[col].corr(df_metadata[variable_objetivo])
        for col in df_covariables.columns
    }

    df_corr = (
        pd.DataFrame.from_dict(correlaciones, orient="index", columns=["Correlacion_Real"])
        .assign(Correlacion_Abs=lambda d: d["Correlacion_Real"].abs())
        .sort_values("Correlacion_Abs", ascending=False)
    )

    if modo == "top_n":
        variables_ganadoras = df_corr.index[: int(valor)].tolist()
        criterio = f"Top {int(valor)} variables con mayor |correlación|"
    else:
        variables_ganadoras = df_corr[df_corr["Correlacion_Abs"] >= valor].index.tolist()
        criterio = f"Variables con |r| >= {valor}"

    reporte = []
    for idx, codigo in enumerate(variables_ganadoras, 1):
        fila_dic = df_diccionario[df_diccionario["CODIGO_INDICADOR"] == codigo]
        reporte.append({
            "Puesto":            idx,
            "Código":            codigo,
            "Dimensión":         fila_dic["DIMENSION"].values[0]  if not fila_dic.empty else "N/A",
            "Nombre Indicador":  fila_dic["INDICADOR"].values[0]  if not fila_dic.empty else "No encontrado",
            "Corr. Real":        round(df_corr.loc[codigo, "Correlacion_Real"], 4),
            "Corr. Abs":         round(df_corr.loc[codigo, "Correlacion_Abs"],  4),
        })

    df_reporte = pd.DataFrame(reporte)

    print(f"Selección por correlación ({criterio}):")
    print(f"  Evaluadas: {df_covariables.shape[1]} variables")
    print(f"  Seleccionadas: {len(variables_ganadoras)}")

    return variables_ganadoras, df_reporte
