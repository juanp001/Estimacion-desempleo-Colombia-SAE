"""Consolidación de las estimaciones por dominio (EBLUP) y por municipio (sintéticas).

Calidad reportada (G7-B21)
--------------------------
La categoría por CV (``clasificar_confiabilidad``) no significa lo mismo en los dos niveles:

* En un **dominio** el CV es el del EBLUP, que combina la estimación directa de la encuesta con el
  modelo, y el modelo se ajustó con esa misma directa.
* En un **municipio** el CV es el del sintético x_m'β̂, cuyo MSE x_m'Cov(β̂)x_m + Â se deriva
  suponiendo que el modelo es el verdadero también en ese municipio (Morales et al., p. 3 y
  p. 441). No incluye la incertidumbre por la selección del modelo, por una mala especificación
  ni por aplicar la recta fuera de los datos con que se estimó: el sintético es sesgado si el
  modelo no se cumple, aunque su varianza sea pequeña (Molina, 2019, PDF 37 y 41).

Por eso la tabla final lleva ``CALIDAD_REPORTADA``: la categoría por CV, más «condicional al
modelo» en todo municipio y «extrapolado» cuando ``ESTADO_EXTRAPOLACION`` (B20,
``shared/extrapolacion.py``) no es ``DENTRO_DEL_RANGO``. Todo se calcula con el modelo ganador y
los umbrales de ``config.py``: si cambian las covariables o los umbrales, la etiqueta cambia sola.
"""

import pandas as pd

from shared.config import CV_ACEPTABLE, CV_CONFIABLE
from shared.extrapolacion import ESTADO_COMBINACION, ESTADO_DENTRO, ESTADO_FUERA


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


# De dónde sale el CV en cada nivel de la tabla final (B21).
BASE_CV = {"DOMINIO": "EBLUP", "MUNICIPIO": "CONDICIONAL_AL_MODELO"}

# Texto que se agrega a la categoría de un municipio según su estado de extrapolación (B20).
SUFIJO_EXTRAPOLACION = {
    ESTADO_DENTRO: "",
    ESTADO_FUERA: " · extrapolado (fuera del rango)",
    ESTADO_COMBINACION: " · extrapolado (combinación atípica)",
}


def etiqueta_calidad(nivel: str, confiabilidad: str, estado: str) -> str:
    """Etiqueta de calidad que se publica en la tabla final (G7-B21).

    En un dominio es la categoría por CV tal cual. En un municipio se agrega siempre
    «condicional al modelo» (su CV supone que el modelo vale en el municipio) y, si su
    predicción es una extrapolación, el tipo de extrapolación. Así ningún municipio queda como
    «Confiable» o «Aceptable» a secas.

    Args:
        nivel (str): "DOMINIO" o "MUNICIPIO".
        confiabilidad (str): Salida de `clasificar_confiabilidad`.
        estado (str): ESTADO_EXTRAPOLACION de `shared/extrapolacion.py`.

    Returns:
        str: La etiqueta, p. ej. "Aceptable · condicional al modelo · extrapolado (fuera del
            rango)".

    Raises:
        ValueError: Si el nivel o el estado no se conocen (un estado nuevo en
            `extrapolacion.py` debe tener su texto en SUFIJO_EXTRAPOLACION), o si un dominio
            no está dentro del rango (los dominios son la muestra que lo define).

    Casos de uso:
        Columna CALIDAD_REPORTADA de `construir_tabla_final`.

    Example:
        >>> etiqueta_calidad("DOMINIO", "Confiable", "DENTRO_DEL_RANGO")
        'Confiable'
        >>> etiqueta_calidad("MUNICIPIO", "Aceptable", "DENTRO_DEL_RANGO")
        'Aceptable · condicional al modelo'
        >>> etiqueta_calidad("MUNICIPIO", "Aceptable", "FUERA_DEL_RANGO")
        'Aceptable · condicional al modelo · extrapolado (fuera del rango)'
        >>> etiqueta_calidad("MUNICIPIO", "No confiable", "COMBINACION_ATIPICA")
        'No confiable · condicional al modelo · extrapolado (combinación atípica)'
        >>> etiqueta_calidad("MUNICIPIO", "Aceptable", "OTRO")
        Traceback (most recent call last):
        ...
        ValueError: Estado de extrapolación sin etiqueta: 'OTRO'
    """
    if nivel not in BASE_CV:
        raise ValueError(f"Nivel desconocido: {nivel!r}")
    if estado not in SUFIJO_EXTRAPOLACION:
        raise ValueError(f"Estado de extrapolación sin etiqueta: {estado!r}")
    if nivel == "DOMINIO":
        if estado != ESTADO_DENTRO:
            raise ValueError(f"Un dominio no puede tener estado {estado!r}")
        return confiabilidad
    return f"{confiabilidad} · condicional al modelo{SUFIJO_EXTRAPOLACION[estado]}"


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

    La calidad (G7-B21) va en tres columnas: ``CONFIABILIDAD`` (solo por el CV), ``BASE_CV``
    (``EBLUP`` en los dominios, ``CONDICIONAL_AL_MODELO`` en los municipios) y
    ``CALIDAD_REPORTADA`` (`etiqueta_calidad`), que es la que debe citarse. Los dominios llevan
    ``ESTADO_EXTRAPOLACION = DENTRO_DEL_RANGO`` porque son la muestra que define el rango.

    Args:
        tabla_dominios (pd.DataFrame): Columnas de ``COLUMNAS_ESQUEMA`` (CODIGO = código del
            dominio).
        tabla_municipios (pd.DataFrame): Columnas de ``COLUMNAS_ESQUEMA`` más
            ``CODIGO_DOMINIO_PADRE`` y ``ESTADO_EXTRAPOLACION`` (CODIGO = código del municipio).
        dim_dominio (pd.DataFrame): ``dim_dominio_geih`` con CODIGO_DOMINIO y NOMBRE_DOMINIO.
        dim_divipola (pd.DataFrame): Nomenclatura DIVIPOLA con CODIGO_MUNICIPIO, MUNICIPIO y
            DEPARTAMENTO (una fila por municipio).

    Returns:
        pd.DataFrame: Una fila por dominio y por municipio objetivo, ordenada por NIVEL y
            CODIGO, con NIVEL, PER, MES, DEPARTAMENTO, CODIGO, NOMBRE, CODIGO_DOMINIO_PADRE,
            TIPO, TASA_DESEMPLEO_PCT, TASA_SIN_AJUSTE_PCT, LAMBDA, CV_PCT, CONFIABILIDAD,
            BASE_CV, ESTADO_EXTRAPOLACION y CALIDAD_REPORTADA.

    Raises:
        ValueError: Si falta alguna columna del esquema, algún código no tiene nombre o algún
            estado de extrapolación no tiene etiqueta.

    Example:
        >>> df_final = construir_tabla_final(
        ...     tabla_dominios, tabla_municipios,
        ...     spark.table(TBL_DIM_DOMINIO).toPandas(), spark.table(TBL_DIM_DIVIPOLA).toPandas(),
        ... )
    """
    for nombre, tabla, extra in [
        ("tabla_dominios", tabla_dominios, []),
        (
            "tabla_municipios",
            tabla_municipios,
            ["CODIGO_DOMINIO_PADRE", "ESTADO_EXTRAPOLACION"],
        ),
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
    dominios["ESTADO_EXTRAPOLACION"] = ESTADO_DENTRO

    municipios = (
        tabla_municipios[
            COLUMNAS_ESQUEMA + ["CODIGO_DOMINIO_PADRE", "ESTADO_EXTRAPOLACION"]
        ]
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
    tabla_final["BASE_CV"] = tabla_final["NIVEL"].map(BASE_CV)
    tabla_final["CALIDAD_REPORTADA"] = [
        etiqueta_calidad(n, c, e)
        for n, c, e in tabla_final[
            ["NIVEL", "CONFIABILIDAD", "ESTADO_EXTRAPOLACION"]
        ].itertuples(index=False)
    ]
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
        "BASE_CV",
        "ESTADO_EXTRAPOLACION",
        "CALIDAD_REPORTADA",
    ]
    return (
        tabla_final[orden]
        .sort_values(["NIVEL", "PER", "MES", "CODIGO"])
        .reset_index(drop=True)
    )


def resumen_calidad(df_pred: pd.DataFrame) -> pd.DataFrame:
    """Resume la predicción sintética por estado de extrapolación y categoría por CV (B21).

    Muestra por qué el CV no basta para juzgar un municipio: si la extrapolación infla la tasa
    predicha, el error (RMSE) sube, pero el CV = RMSE / tasa puede quedar igual.

    Args:
        df_pred (pd.DataFrame): Una fila por municipio con ESTADO_EXTRAPOLACION,
            CV_SINTETICO_PCT, PRED_SINTETICO, RMSE_SINTETICO y APORTE_EXTRAPOLADO_PP.

    Returns:
        pd.DataFrame: Una fila por (EXTRAPOLA, ESTADO_EXTRAPOLACION, CONFIABILIDAD) con
            N_MUNICIPIOS, CV_MEDIO_PCT, TASA_MEDIA_PCT, TASA_MAX_PCT, RMSE_MEDIO,
            APORTE_MEDIO_PP y APORTE_MAX_PP (los aportes en valor absoluto).

    Casos de uso:
        Celda 11a de `modelo/fay_herriot.py`; entrada de `interpretar_calidad`.

    Example:
        >>> df = pd.DataFrame({
        ...     "ESTADO_EXTRAPOLACION": ["DENTRO_DEL_RANGO", "FUERA_DEL_RANGO"],
        ...     "CV_SINTETICO_PCT": [16.0, 16.0], "PRED_SINTETICO": [10.0, 20.0],
        ...     "RMSE_SINTETICO": [1.6, 3.2], "APORTE_EXTRAPOLADO_PP": [0.0, -8.0]})
        >>> resumen_calidad(df)[["EXTRAPOLA", "CONFIABILIDAD", "RMSE_MEDIO", "APORTE_MAX_PP"]].values.tolist()
        [[False, 'Aceptable', 1.6, 0.0], [True, 'Aceptable', 3.2, 8.0]]
    """
    df = df_pred.assign(
        EXTRAPOLA=df_pred["ESTADO_EXTRAPOLACION"] != ESTADO_DENTRO,
        CONFIABILIDAD=df_pred["CV_SINTETICO_PCT"].apply(clasificar_confiabilidad),
        APORTE_ABS=df_pred["APORTE_EXTRAPOLADO_PP"].abs(),
    )
    return (
        df.groupby(["EXTRAPOLA", "ESTADO_EXTRAPOLACION", "CONFIABILIDAD"])
        .agg(
            N_MUNICIPIOS=("CV_SINTETICO_PCT", "size"),
            CV_MEDIO_PCT=("CV_SINTETICO_PCT", "mean"),
            TASA_MEDIA_PCT=("PRED_SINTETICO", "mean"),
            TASA_MAX_PCT=("PRED_SINTETICO", "max"),
            RMSE_MEDIO=("RMSE_SINTETICO", "mean"),
            APORTE_MEDIO_PP=("APORTE_ABS", "mean"),
            APORTE_MAX_PP=("APORTE_ABS", "max"),
        )
        .round(2)
        .reset_index()
    )


def interpretar_calidad(df_pred: pd.DataFrame) -> str:
    """Texto, calculado con los datos, que explica la calidad reportada de los municipios (B21).

    Compara los municipios extrapolados con los que están dentro del rango: cuántos quedan en
    cada categoría por CV, y su CV, tasa y RMSE medios. No usa cifras fijas: sirve para
    cualquier modelo ganador.

    Args:
        df_pred (pd.DataFrame): Mismas columnas que pide `resumen_calidad`.

    Returns:
        str: Párrafos en lenguaje simple, listos para imprimir.

    Casos de uso:
        Interpretación de la celda 11a de `modelo/fay_herriot.py`.

    Example:
        >>> df = pd.DataFrame({
        ...     "ESTADO_EXTRAPOLACION": ["DENTRO_DEL_RANGO", "FUERA_DEL_RANGO"],
        ...     "CV_SINTETICO_PCT": [16.0, 16.0], "PRED_SINTETICO": [10.0, 20.0],
        ...     "RMSE_SINTETICO": [1.6, 3.2], "APORTE_EXTRAPOLADO_PP": [0.0, 8.0]})
        >>> "1 de 1 municipios extrapolados" in interpretar_calidad(df)
        True
    """
    m = len(df_pred)
    extrapola = df_pred["ESTADO_EXTRAPOLACION"] != ESTADO_DENTRO
    categoria = df_pred["CV_SINTETICO_PCT"].apply(clasificar_confiabilidad)
    n_ext = int(extrapola.sum())
    lineas = [
        f"De {m} municipios, {n_ext} tienen una predicción extrapolada y {m - n_ext} "
        "quedan dentro del rango de los dominios.",
        "El CV de todo municipio es condicional al modelo base: supone que la relación "
        "estimada con los dominios también vale en el municipio (Morales et al., p. 441), y "
        "no incluye la incertidumbre por selección del modelo, mala especificación ni "
        "extrapolación. Por eso CALIDAD_REPORTADA dice «condicional al modelo» en todos.",
    ]
    if n_ext == 0:
        lineas.append(
            "Ningún municipio extrapola: la etiqueta solo agrega «condicional al modelo»."
        )
        return "\n".join(lineas)

    buenos = int((extrapola & categoria.isin(["Confiable", "Aceptable"])).sum())
    lineas.append(
        f"{buenos} de {n_ext} municipios extrapolados quedan como «Confiable» o "
        "«Aceptable» por su CV; su etiqueta agrega «extrapolado» para que esa categoría "
        "no se lea como una validación empírica."
    )
    if n_ext < m:
        dentro, fuera = df_pred[~extrapola], df_pred[extrapola]
        cv_d, cv_f = dentro["CV_SINTETICO_PCT"].mean(), fuera["CV_SINTETICO_PCT"].mean()
        r_d, r_f = dentro["RMSE_SINTETICO"].mean(), fuera["RMSE_SINTETICO"].mean()
        t_d, t_f = dentro["PRED_SINTETICO"].mean(), fuera["PRED_SINTETICO"].mean()
        lineas.append(
            f"Extrapolados frente a dentro del rango: CV medio {cv_f:.1f} % vs {cv_d:.1f} %, "
            f"RMSE medio {r_f:.2f} vs {r_d:.2f} pp ({r_f / r_d:.1f} veces) y tasa predicha "
            f"media {t_f:.1f} % vs {t_d:.1f} % ({t_f / t_d:.1f} veces)."
        )
        if r_f / r_d > cv_f / cv_d:
            lineas.append(
                "El error crece más que el CV porque el CV divide el error por la tasa "
                "predicha, que también sube cuando el municipio extrapola: un CV parecido "
                "no significa una estimación igual de buena."
            )
    aporte = df_pred.loc[extrapola, "APORTE_EXTRAPOLADO_PP"].abs()
    lineas.append(
        f"En los extrapolados, la parte de la predicción que viene de fuera del rango es en "
        f"promedio {aporte.mean():.1f} pp (máximo {aporte.max():.1f} pp); ver la celda 10a."
    )
    return "\n".join(lineas)
