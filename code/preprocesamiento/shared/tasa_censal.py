from pyspark.sql import DataFrame, functions as F


def calcular_tasa_desempleo_censal(
    df_personas: DataFrame,
    df_divipola: DataFrame,
    departamentos: list,
    per: int,
    mes: int,
) -> DataFrame:
    """Calcula la tasa de desempleo censal por municipio con su varianza y CV.

    La tasa es un conteo completo (censo), no una estimación muestral; la varianza se
    aproxima con la binomial p(1-p)/PEA, expresada en puntos porcentuales al cuadrado.

    Args:
        df_personas (pyspark.sql.DataFrame): Tabla de personas del censo con las columnas
            `U_DPTO`, `U_MPIO`, `P_EDADR` y `P_TRABAJO`.
        df_divipola (pyspark.sql.DataFrame): `dim_divipola` con `CODIGO_MUNICIPIO`,
            `MUNICIPIO` y `DEPARTAMENTO`.
        departamentos (list[int]): Códigos DIVIPOLA de departamento a conservar.
        per (int): Año que se asigna a la columna `PER` (período de las covariables).
        mes (int): Mes que se asigna a la columna `MES`.

    Returns:
        pyspark.sql.DataFrame: Una fila por municipio con `PER`, `MES`,
        `CODIGO_DEPARTAMENTO`, `CODIGO_MUNICIPIO`, `DEPARTAMENTO`, `MUNICIPIO`, `PET`, `PEA`,
        `OCUPADOS`, `DESOCUPADOS`, `INACTIVOS`, `TASA_DESEMPLEO_PCT`, `VARIANZA`, `SE_PCT`
        y `CV_PORCENTAJE`. Los municipios con PEA = 0 quedan con tasa nula.

    Example:
        >>> tasa = calcular_tasa_desempleo_censal(
        ...     spark.table("tesis.censo_nal.personas"),
        ...     spark.table("tesis.dim.dim_divipola"),
        ...     [19, 76], 2018, 12,
        ... )
    """
    p_trabajo = F.col("P_TRABAJO").cast("int")
    pet = F.col("P_EDADR").cast("int") > 3
    activo = p_trabajo.isin([1, 2, 3, 4])

    codigo_depto = F.lpad(F.col("U_DPTO").cast("int").cast("string"), 2, "0")
    codigo_mpio = F.lpad(F.col("U_MPIO").cast("int").cast("string"), 3, "0")

    df = (
        df_personas.filter(F.col("U_DPTO").cast("int").isin(departamentos))
        .withColumn("CODIGO_DEPARTAMENTO", codigo_depto)
        .withColumn("CODIGO_MUNICIPIO", F.concat(codigo_depto, codigo_mpio))
        .withColumn("PET", F.when(pet, 1).otherwise(0))
        .withColumn("PEA", F.when(pet & activo, 1).otherwise(0))
        .withColumn("OCUPADOS", F.when(p_trabajo.isin([1, 2, 3]), 1).otherwise(0))
        .withColumn("DESOCUPADOS", F.when(p_trabajo == 4, 1).otherwise(0))
        .withColumn("INACTIVOS", F.when(~activo, 1).otherwise(0))
    )

    agrupado = df.groupBy("CODIGO_DEPARTAMENTO", "CODIGO_MUNICIPIO").agg(
        *[
            F.sum(c).alias(c)
            for c in ["PET", "PEA", "OCUPADOS", "DESOCUPADOS", "INACTIVOS"]
        ]
    )

    p = F.col("DESOCUPADOS") / F.col("PEA")
    agrupado = (
        agrupado.withColumn("TASA_DESEMPLEO_PCT", 100 * p)
        .withColumn("VARIANZA", 10000 * p * (1 - p) / F.col("PEA"))
        .withColumn("SE_PCT", F.sqrt("VARIANZA"))
        .withColumn("CV_PORCENTAJE", 100 * F.col("SE_PCT") / F.col("TASA_DESEMPLEO_PCT"))
        .withColumn("PER", F.lit(per))
        .withColumn("MES", F.lit(mes))
    )

    divipola = df_divipola.select("CODIGO_MUNICIPIO", "MUNICIPIO", "DEPARTAMENTO")
    return agrupado.join(divipola, on="CODIGO_MUNICIPIO", how="left").select(
        "PER",
        "MES",
        "CODIGO_DEPARTAMENTO",
        "DEPARTAMENTO",
        "CODIGO_MUNICIPIO",
        "MUNICIPIO",
        "PET",
        "PEA",
        "OCUPADOS",
        "DESOCUPADOS",
        "INACTIVOS",
        "TASA_DESEMPLEO_PCT",
        "VARIANZA",
        "SE_PCT",
        "CV_PORCENTAJE",
    )
