"""Agregación de los indicadores municipales de TerriData al dominio de estimación GEIH.

Por qué se agregan las covariables
----------------------------------
El campo ``AREA`` de la GEIH identifica la ciudad con su área metropolitana (DANE, Metodología
General GEIH v9, 2016, PDF 3 y 9), de modo que la tasa directa de «Cali» es la de **Cali A.M.** (Cali +
Yumbo). En el modelo Fay-Herriot el vector ``x_d`` contiene «los valores agregados (poblacionales)
de las variables auxiliares del área d» (Morales et al., 2021, p. 425): si la respuesta describe el
área metropolitana, las covariables también deben describirla. Unirlas solo con la capital mezclaría
la tasa de un territorio con las características de otro.

Cómo se agregan
---------------
Cada indicador x se agrega con su propio peso ``z`` (ver ``reglas_agregacion.py``):

    x̄_D = Σ_{m∈D} z_m · x_m / Σ_{m∈D} z_m.

Si x es una razón ``Y/Z`` y ``z`` es su denominador, ``x̄_D = Σ Y_m / Σ Z_m`` es exactamente el
indicador calculado para la unión de los municipios (Morales et al., 2021, §2.4, p. 21): el
valor agregado para la participación sectorial del valor agregado, la superficie para la densidad,
la población para los valores per cápita. Así ``x_D`` y ``x_m`` son **el mismo indicador** sobre
territorios distintos, lo que también sostiene la predicción sintética municipal ``x_m'β̂``: esta
supone que el modelo de enlace estimado con los dominios vale para los municipios (Morales et al.,
p. 441), y ese supuesto solo tiene sentido si las covariables significan lo mismo en ambos niveles.

La tasa de desempleo, en cambio, se agrega con la PEA (es su denominador): en el benchmarking de
nivel 2 del modelo los municipios se ponderan por la población de 15 años y más, aproximación de la
PEA municipal (ver ``modelo/shared/benchmarking.py``).

Datos faltantes
---------------
Si a algún municipio miembro le falta el indicador, el valor del dominio queda NULL en lugar de
promediar solo los municipios con dato: un promedio parcial describiría otro territorio. El filtro de
completitud del pre-filtrado descarta después esa columna. Un municipio miembro sin alguno de los
pesos usados detiene la ejecución, porque invalidaría todos los indicadores que dependen de ese peso.

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
    pesos_por_columna: dict,
    expresiones_peso: dict,
    anio: int,
    mes: int,
) -> DataFrame:
    """Agrega indicadores municipales de TerriData a los dominios GEIH, cada uno con su peso.

    Args:
        df_terridata (DataFrame): ``tesis.terridata.terridata_extendido_plata`` (formato ancho,
            una fila por entidad y período, con ``CODIGO_ENTIDAD``, ``ANO`` y ``MES``).
        df_dim_dominio (DataFrame): ``tesis.dim.dim_dominio_geih`` (una fila por municipio
            miembro, con ``CODIGO_DOMINIO`` y ``CODIGO_MUNICIPIO``).
        pesos_por_columna (dict[str, str]): Código de indicador → nombre de su peso (p. ej.
            ``{"120210008": "VALOR_AGREGADO"}``; ver ``reglas_agregacion.regla_de``). Define las
            columnas que se agregan y su orden.
        expresiones_peso (dict[str, str]): Nombre del peso → expresión SQL sobre las columnas de
            TerriData (``reglas_agregacion.PESOS_AGREGACION[...]["expresion"]``). Debe dar NULL si
            falta un componente.
        anio (int): Año (``ANO``) de TerriData que se agrega.
        mes (int): Mes (``MES``) de TerriData que se agrega.

    Returns:
        DataFrame: Una fila por dominio con ``CODIGO_DOMINIO``, ``ANO``, ``MES`` y una columna
            double por indicador. El valor es NULL si a algún municipio miembro le falta el dato.

    Raises:
        ValueError: Si algún municipio miembro no tiene (o tiene ≤ 0) alguno de los pesos usados.

    Casos de uso:
        En ``adicion_covariables.py``, antes de unir las covariables con las estimaciones
        directas por ``CODIGO_DOMINIO``. Para un dominio de un solo municipio el resultado es el
        valor del municipio; para Cali A.M. la participación del sector secundario es
        Σ VA_sec / Σ VA de Cali y Yumbo. Con todas las columnas en ``"PET"`` sirve como
        escenario de sensibilidad (regla anterior).

    Example:
        >>> pesos = {c: regla_de(c)["peso"] for c in columnas_indicadores}
        >>> expresiones = {p: PESOS_AGREGACION[p]["expresion"] for p in set(pesos.values())}
        >>> df_cov = agregar_covariables_dominio(
        ...     spark.table(TBL_TERRIDATA), spark.table(TBL_DIM_DOMINIO),
        ...     pesos, expresiones, 2018, 12,
        ... )
    """
    columnas = list(pesos_por_columna)
    nombres_peso = sorted(set(pesos_por_columna.values()))
    faltantes = [p for p in nombres_peso if p not in expresiones_peso]
    if faltantes:
        raise ValueError(f"Pesos sin expresión SQL: {faltantes}")

    # try_cast: algunos indicadores son texto (p. ej. la categoría municipal «Especial»); con el
    # modo ANSI un cast fallaría. Quedan NULL, igual que con pd.to_numeric(errors="coerce") del
    # pre-filtrado, y el filtro de completitud los descarta.
    df_periodo = df_terridata.filter(
        (F.col("ANO") == anio) & (F.col("MES") == mes)
    ).select(
        F.col("CODIGO_ENTIDAD").alias("CODIGO_MUNICIPIO"),
        *[F.expr(expresiones_peso[p]).alias(f"_PESO_{p}") for p in nombres_peso],
        *[F.expr(f"try_cast(`{c}` AS DOUBLE)").alias(c) for c in columnas],
    )

    df_miembros = df_dim_dominio.select("CODIGO_DOMINIO", "CODIGO_MUNICIPIO").join(
        df_periodo, on="CODIGO_MUNICIPIO", how="left"
    )

    condicion_sin_peso = None
    for p in nombres_peso:
        cond = F.col(f"_PESO_{p}").isNull() | (F.col(f"_PESO_{p}") <= 0)
        condicion_sin_peso = (
            cond if condicion_sin_peso is None else (condicion_sin_peso | cond)
        )
    sin_peso = [
        (fila["CODIGO_MUNICIPIO"], p)
        for fila in df_miembros.filter(condicion_sin_peso).collect()
        for p in nombres_peso
        if fila[f"_PESO_{p}"] is None or fila[f"_PESO_{p}"] <= 0
    ]
    if sin_peso:
        raise ValueError(
            f"Municipios miembro sin peso válido en TerriData para ANO={anio}, MES={mes} "
            f"(municipio, peso): {sorted(sin_peso)}. Sin peso no se puede agregar su dominio."
        )

    agregaciones = []
    for c in columnas:
        peso = F.col(f"_PESO_{pesos_por_columna[c]}")
        agregaciones.append(
            F.when(
                F.sum(F.col(f"`{c}`").isNull().cast("int")) == 0,
                F.sum(F.col(f"`{c}`") * peso) / F.sum(peso),
            ).alias(c)
        )

    return (
        df_miembros.groupBy("CODIGO_DOMINIO")
        .agg(*agregaciones)
        .withColumn("ANO", F.lit(anio))
        .withColumn("MES", F.lit(mes))
        .select("CODIGO_DOMINIO", "ANO", "MES", *[F.col(f"`{c}`") for c in columnas])
    )
