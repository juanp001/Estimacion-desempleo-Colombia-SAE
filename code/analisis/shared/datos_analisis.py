"""Carga común de los notebooks de análisis (R-32).

`analisis_descriptivo.py` y `eda_seleccion_covariables.py` partían de la misma tabla de
covariables pre-filtradas y repetían, línea por línea, la lectura, el casteo a numérico, la
separación de metadatos y la resolución del catálogo de literatura. Esta función es la única
implementación: un cambio en cómo se leen o resuelven las candidatas se aplica a ambos.
"""

import pandas as pd

from analisis.shared.catalogo_literatura import (
    CATALOGO_LITERATURA,
    mapas_catalogo,
    resolver_catalogo,
)
from analisis.shared.soporte_objetivos import columnas_incompletas


def cargar_datos_analisis(
    spark,
    tabla_prefiltradas: str,
    tabla_dim_indicadores: str,
    metadata_cols: list,
    variable_objetivo: str,
    tabla_objetivos: str = None,
) -> dict:
    """Lee las covariables pre-filtradas y resuelve el catálogo de candidatas.

    Las columnas de covariables llegan como texto desde la tabla ancha de TerriData y se
    castean a ``double``. Los metadatos (respuesta, error estándar, dominio) se separan de las
    covariables y se calcula ψ_d = SE² (G7-B8), la misma varianza de muestreo que usa el
    modelo Fay-Herriot.

    Args:
        spark (SparkSession): Sesión activa.
        tabla_prefiltradas (str): Tabla con las covariables pre-filtradas, una fila por dominio.
        tabla_dim_indicadores (str): Diccionario código → nombre descriptivo del indicador.
        metadata_cols (list[str]): Columnas de metadatos de la tabla (no son covariables).
        variable_objetivo (str): Columna con la tasa de desempleo directa.
        tabla_objetivos (str | None): Tabla de los municipios objetivo sin encuesta, con las
            mismas covariables a nivel municipal (`municipios_sin_encuesta`). Con ella, una
            candidata incompleta en los objetivos no entra al catálogo activo (condición (iii))
            y se devuelve `df_objetivos` para medir el soporte (R-02).

    Returns:
        dict: Con las claves `df_full` (Spark, tabla pre-filtrada completa),
            `indicadores_dict` (código → nombre), `df_meta` y `df_pd` (pandas: metadatos y
            covariables), `Y`, `SE`, `PSI` y `entidades` (arreglos por dominio),
            `catalogo_activo`, `reporte_catalogo`, `CANDIDATAS`, `ALIAS`, `SIGNO`,
            `DIMENSION`, `df_cand` (solo las candidatas, en pandas) y `df_objetivos` (los
            municipios objetivo con las candidatas en numérico; None sin `tabla_objetivos`).

    Example:
        >>> datos = cargar_datos_analisis(
        ...     spark, TBL_PREFILTRADAS, TBL_DIM_INDICADORES, METADATA_COLS, VARIABLE_OBJETIVO
        ... )  # doctest: +SKIP
        >>> datos["CANDIDATAS"]  # doctest: +SKIP
    """
    from pyspark.sql import functions as F

    df_full = spark.table(tabla_prefiltradas)
    indicadores_dict = {
        fila["CODIGO_INDICADOR"]: fila["INDICADOR"]
        for fila in spark.table(tabla_dim_indicadores)
        .select("CODIGO_INDICADOR", "INDICADOR")
        .collect()
    }

    cols_covariables = [c for c in df_full.columns if c not in metadata_cols]
    df_cov_spark = df_full.select(cols_covariables)
    for nombre in [
        f.name for f in df_cov_spark.schema.fields if str(f.dataType) == "StringType()"
    ]:
        df_cov_spark = df_cov_spark.withColumn(nombre, F.col(nombre).cast("double"))

    df_meta = df_full.select(metadata_cols).toPandas()
    df_pd = df_cov_spark.toPandas()

    Y = df_meta[variable_objetivo].values
    SE = df_meta["SE_BOOTSTRAP_PCT"].astype(float).values
    # Etiqueta de cada dominio: la ciudad o la ciudad con su área metropolitana («Cali A.M.»).
    entidades = df_meta["NOMBRE_DOMINIO"].values

    df_objetivos_crudo, incompletas = None, None
    if tabla_objetivos is not None:
        df_objetivos_crudo = spark.table(tabla_objetivos).toPandas()
        # Solo se revisan las columnas del catálogo que sobrevivieron al pre-filtrado; las demás
        # columnas pre-filtradas no son candidatas.
        del_catalogo = [
            e["codigo"] for e in CATALOGO_LITERATURA if e["codigo"] in df_pd.columns
        ]
        incompletas = columnas_incompletas(df_objetivos_crudo, del_catalogo)

    catalogo_activo, reporte_catalogo = resolver_catalogo(
        indicadores_dict, list(df_pd.columns), incompletas_objetivos=incompletas
    )
    CANDIDATAS, ALIAS, SIGNO, DIMENSION = mapas_catalogo(catalogo_activo)
    df_objetivos = None
    if df_objetivos_crudo is not None:
        df_objetivos = df_objetivos_crudo[CANDIDATAS].apply(
            pd.to_numeric, errors="coerce"
        )
    return {
        "df_full": df_full,
        "indicadores_dict": indicadores_dict,
        "df_meta": df_meta,
        "df_pd": df_pd,
        "Y": Y,
        "SE": SE,
        "PSI": SE**2,
        "entidades": entidades,
        "catalogo_activo": catalogo_activo,
        "reporte_catalogo": reporte_catalogo,
        "CANDIDATAS": CANDIDATAS,
        "ALIAS": ALIAS,
        "SIGNO": SIGNO,
        "DIMENSION": DIMENSION,
        "df_cand": df_pd[CANDIDATAS].copy(),
        "df_objetivos": df_objetivos,
    }
