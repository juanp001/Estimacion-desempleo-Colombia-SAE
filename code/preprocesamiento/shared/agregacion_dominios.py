"""Agregación de los indicadores municipales de TerriData al dominio de estimación GEIH.

Por qué se agregan las covariables
----------------------------------
El campo ``AREA`` de la GEIH identifica la ciudad con su área metropolitana (DANE, Metodología
General GEIH v9, 2016, PDF 9), de modo que la tasa directa de «Cali» es la de **Cali A.M.** (Cali +
Yumbo). En el modelo Fay-Herriot el vector ``x_d`` contiene «los valores agregados (poblacionales)
de las variables auxiliares del área d» (Morales et al., 2021, p. 425): si la respuesta describe el
área metropolitana, las covariables también deben describirla. Unirlas solo con la capital mezclaría
la tasa de un territorio con las características de otro.

Cómo se agregan
---------------
Para cada dominio D y cada indicador x se usa el promedio ponderado

    x̄_D = Σ_{m∈D} w_m · x_m / Σ_{m∈D} w_m,

con ``w_m`` = población de 15 a 59 años del municipio (TerriData 020090014), aproximación de la PEA
municipal, que no se publica. El peso se elige por coherencia con la respuesta: la tasa de desempleo
del dominio es TD_D = Σ PEA_m · TD_m / Σ PEA_m. Si el modelo lineal vale en cada municipio,
μ_m = x_m'β + u_m, al promediar con los mismos pesos se obtiene μ_D = x̄_D'β + ū_D: el mismo β
sirve para el dominio y para sus municipios. Esa coherencia permite (i) ajustar el modelo con los
dominios y predecir municipios con x_m'β̂, y (ii) que el benchmarking de nivel 2 del modelo, que usa
los mismos pesos, tenga λ − 1 interpretable como el residuo del dominio
(ver ``modelo/shared/benchmarking.py``).

Se aplica la misma regla a todos los indicadores: los del catálogo de literatura son tasas,
porcentajes, índices o valores per cápita, para los que el promedio ponderado es la agregación
natural; los demás solo pasan por el pre-filtrado de variabilidad, que es invariante a la escala.

Datos faltantes
---------------
Si a algún municipio miembro le falta el indicador, el valor del dominio queda NULL en lugar de
promediar solo los municipios con dato: un promedio parcial describiría otro territorio. El filtro de
completitud del pre-filtrado descarta después esa columna. Un municipio miembro sin peso detiene la
ejecución, porque invalidaría todos los indicadores del dominio.

Limitación conocida
-------------------
En el marco 2005 el ``AREA`` solo aparece en los registros de cabecera (CLASE = 1): la tasa del
dominio es urbana y los indicadores de TerriData son municipales (incluyen la zona rural).
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def agregar_covariables_dominio(
    df_terridata: DataFrame,
    df_dim_dominio: DataFrame,
    columnas: list,
    col_peso: str,
    anio: int,
    mes: int,
) -> DataFrame:
    """Agrega indicadores municipales de TerriData a los dominios GEIH con promedio ponderado.

    Args:
        df_terridata (DataFrame): ``tesis.terridata.terridata_extendido_plata`` (formato ancho,
            una fila por entidad y período, con ``CODIGO_ENTIDAD``, ``ANO`` y ``MES``).
        df_dim_dominio (DataFrame): ``tesis.dim.dim_dominio_geih`` (una fila por municipio
            miembro, con ``CODIGO_DOMINIO`` y ``CODIGO_MUNICIPIO``).
        columnas (list[str]): Códigos de indicador a agregar (nombres de columna de TerriData).
        col_peso (str): Código del indicador usado como peso (población de 15 a 59 años).
        anio (int): Año (``ANO``) de TerriData que se agrega.
        mes (int): Mes (``MES``) de TerriData que se agrega.

    Returns:
        DataFrame: Una fila por dominio con ``CODIGO_DOMINIO``, ``ANO``, ``MES`` y una columna
            double por indicador. El valor es NULL si a algún municipio miembro le falta el dato.

    Raises:
        ValueError: Si algún municipio miembro no tiene el peso (o es ≤ 0) en el período.

    Casos de uso:
        En ``adicion_covariables.py``, antes de unir las covariables con las estimaciones
        directas por ``CODIGO_DOMINIO``. Para un dominio de un solo municipio el resultado es el
        valor del municipio; para Cali A.M. es el promedio de Cali y Yumbo ponderado por su
        población de 15 a 59 años.

    Example:
        >>> df_cov = agregar_covariables_dominio(
        ...     spark.table(TBL_TERRIDATA), spark.table(TBL_DIM_DOMINIO),
        ...     columnas_indicadores, COD_PESO_POBLACION, 2018, 12,
        ... )
    """
    # try_cast: algunos indicadores son texto (p. ej. la categoría municipal «Especial»); con el
    # modo ANSI un cast fallaría. Quedan NULL, igual que con pd.to_numeric(errors="coerce") del
    # pre-filtrado, y el filtro de completitud los descarta.
    df_periodo = df_terridata.filter(
        (F.col("ANO") == anio) & (F.col("MES") == mes)
    ).select(
        F.col("CODIGO_ENTIDAD").alias("CODIGO_MUNICIPIO"),
        F.expr(f"try_cast(`{col_peso}` AS DOUBLE)").alias("_PESO"),
        *[F.expr(f"try_cast(`{c}` AS DOUBLE)").alias(c) for c in columnas],
    )

    df_miembros = df_dim_dominio.select("CODIGO_DOMINIO", "CODIGO_MUNICIPIO").join(
        df_periodo, on="CODIGO_MUNICIPIO", how="left"
    )

    sin_peso = [
        fila["CODIGO_MUNICIPIO"]
        for fila in df_miembros.filter(F.col("_PESO").isNull() | (F.col("_PESO") <= 0))
        .select("CODIGO_MUNICIPIO")
        .collect()
    ]
    if sin_peso:
        raise ValueError(
            f"Municipios miembro sin peso ({col_peso}) en TerriData para ANO={anio}, "
            f"MES={mes}: {sorted(sin_peso)}. Sin peso no se puede agregar su dominio."
        )

    agregaciones = [
        F.when(
            F.sum(F.col(f"`{c}`").isNull().cast("int")) == 0,
            F.sum(F.col(f"`{c}`") * F.col("_PESO")) / F.sum("_PESO"),
        ).alias(c)
        for c in columnas
    ]

    return (
        df_miembros.groupBy("CODIGO_DOMINIO")
        .agg(*agregaciones)
        .withColumn("ANO", F.lit(anio))
        .withColumn("MES", F.lit(mes))
        .select("CODIGO_DOMINIO", "ANO", "MES", *[F.col(f"`{c}`") for c in columnas])
    )
