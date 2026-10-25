"""Reconciliación de la fuerza de trabajo de la GEIH (comentario G7-B5).

En el marco antiguo la PEA se deriva por ausencia: una persona de la PET es PEA si no aparece
en el módulo de inactivos. Esa regla solo vale si el nulo viene de la clasificación y no de un
fallo de unión. Este módulo da dos controles:

* ``llaves_sin_pareja``: por período y módulo, cuántas llaves no encuentran pareja en la tabla
  de referencia (características generales, o fuerza de trabajo para inactivos) y cuántas
  están duplicadas. Revisa las uniones en las dos direcciones (R-17): también los factores de
  ``dim_fex`` sin persona y las personas de 15 años y más que faltan en fuerza de trabajo.
* ``reconciliar_fuerza_trabajo``: por período y dominio, conteos de PET, PEA, PEI, OC y DS, y
  las personas que rompen las identidades PEA = OC + DS y PET = PEA + PEI.
"""

from functools import reduce

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def _resumen_llaves(nombre: str, df: DataFrame, referencia: DataFrame) -> DataFrame:
    """Cuenta llaves, duplicadas y sin pareja de un módulo frente a su tabla de referencia.

    Args:
        nombre (str): Nombre del módulo que se reporta en la columna ``MODULO``.
        df (DataFrame): Tabla del módulo con columnas ``PK``, ``PER`` y ``MES``.
        referencia (DataFrame): Tabla contra la que se buscan las llaves (columna ``PK``).

    Returns:
        DataFrame: Una fila por ``PER``/``MES`` con ``MODULO``, ``N_LLAVES``,
        ``N_DUPLICADAS`` y ``N_SIN_PAREJA``.

    Casos de uso:
        Uso interno de ``llaves_sin_pareja``.
    """
    llaves_ref = referencia.select("PK").distinct().withColumn("_EN_REF", F.lit(1))
    return (
        df.select("PK", F.col("PER").cast("int"), F.col("MES").cast("int"))
        .join(llaves_ref, "PK", "left")
        .groupBy("PER", "MES")
        .agg(
            F.count("*").alias("N_LLAVES"),
            (F.count("*") - F.countDistinct("PK")).alias("N_DUPLICADAS"),
            F.count_if(F.col("_EN_REF").isNull()).alias("N_SIN_PAREJA"),
        )
        .withColumn("MODULO", F.lit(nombre))
    )


def llaves_sin_pareja(
    cg: DataFrame,
    ft: DataFrame,
    no: DataFrame,
    oc: DataFrame,
    fex: DataFrame,
    inactivos: DataFrame,
) -> DataFrame:
    """Porcentaje de llaves sin pareja entre los módulos de la GEIH, por período.

    Fuerza de trabajo, no ocupados, ocupados y factores de expansión se buscan en
    características generales (la tabla base del LEFT JOIN de ``geih_oro``); inactivos se
    busca en fuerza de trabajo, porque esa es la unión que define la PEA en ``geih_plata``.
    Características generales del marco antiguo también se reporta frente a ``dim_fex``, que es
    de donde sale su ``FEX_C18`` (en el marco nuevo el factor viene en el archivo, G7-B6); una
    persona sin factor detiene ``geih_oro`` antes de escribir la tabla.

    Las uniones también se revisan en la dirección contraria (R-17), porque el LEFT JOIN de
    ``geih_oro`` no las ve:

    * ``FEX_SIN_CG``: registros de ``dim_fex`` sin persona en características generales del
      marco antiguo. No cambian la estimación (oro parte de características generales), pero
      muestran si el archivo de factores trae viviendas que la base no tiene. En 2018 son 9.866
      (unas 280 viviendas por mes, ``DIRECTORIO`` 4518316-4804436, ≈ 41 mil personas
      expandidas por mes), probablemente San Andrés, que la GEIH publica aparte (DANE,
      Metodología GEIH 2016, p. 10).
    * ``PET_SIN_FT``: personas de 15 años y más de características generales que no están en
      fuerza de trabajo. El LEFT JOIN de ``geih_oro`` les daría PET = 0 y PEA = 0 sin aviso, y
      ``reconciliar_fuerza_trabajo`` no las ve porque filtra ``PET = 1``. Se usa 15 años porque
      es la PET del marco nuevo y está contenida en la del antiguo (10 y 12 años).

    Args:
        cg (DataFrame): ``caracteristicas_generales_consolidado`` (``PK``, ``PER``, ``MES``,
            ``MARCO``, ``EDAD``).
        ft (DataFrame): ``fuerza_trabajo_consolidado``.
        no (DataFrame): ``no_ocupados_consolidado``.
        oc (DataFrame): ``ocupados_consolidado``.
        fex (DataFrame): ``dim_fex`` (``PK``, ``ANO``, ``MES``).
        inactivos (DataFrame): Módulo de inactivos del marco antiguo (``PK``, ``PER``, ``MES``).

    Returns:
        DataFrame: Una fila por ``MODULO``/``PER``/``MES`` con ``REFERENCIA``, ``N_LLAVES``,
        ``N_DUPLICADAS``, ``N_SIN_PAREJA`` y ``PCT_SIN_PAREJA``.

    Casos de uso:
        En ``geih_oro.py``, para reportar si alguna unión entre módulos pierde registros
        (por ejemplo, la PEA de Ene-Mar 2018 se infló porque inactivos no emparejaba).
    """
    fex = fex.withColumnRenamed("ANO", "PER")
    partes = [
        _resumen_llaves("FUERZA_TRABAJO", ft, cg).withColumn("REFERENCIA", F.lit("CG")),
        _resumen_llaves("NO_OCUPADOS", no, cg).withColumn("REFERENCIA", F.lit("CG")),
        _resumen_llaves("OCUPADOS", oc, cg).withColumn("REFERENCIA", F.lit("CG")),
        _resumen_llaves("INACTIVOS", inactivos, ft).withColumn(
            "REFERENCIA", F.lit("FT")
        ),
        _resumen_llaves(
            "CG_SIN_FEX", cg.filter(F.col("MARCO") == "ANTIGUO"), fex
        ).withColumn("REFERENCIA", F.lit("FEX")),
        # R-17: las mismas uniones vistas desde el otro lado
        _resumen_llaves(
            "FEX_SIN_CG", fex, cg.filter(F.col("MARCO") == "ANTIGUO")
        ).withColumn("REFERENCIA", F.lit("CG")),
        _resumen_llaves("PET_SIN_FT", cg.filter(F.col("EDAD") >= 15), ft).withColumn(
            "REFERENCIA", F.lit("FT")
        ),
    ]
    return (
        reduce(lambda a, b: a.unionByName(b), partes)
        .withColumn(
            "PCT_SIN_PAREJA",
            F.round(100 * F.col("N_SIN_PAREJA") / F.col("N_LLAVES"), 4),
        )
        .select(
            "MODULO",
            "REFERENCIA",
            "PER",
            "MES",
            "N_LLAVES",
            "N_DUPLICADAS",
            "N_SIN_PAREJA",
            "PCT_SIN_PAREJA",
        )
        .orderBy("PER", "MES", "MODULO")
    )


def reconciliar_fuerza_trabajo(mercado: DataFrame, dominios: DataFrame) -> DataFrame:
    """Reconciliación PET / PEA / PEI / OC / DS por período y dominio de estimación.

    Solo cuenta personas con ``PET = 1``. Las identidades que se verifican son:

    * ``PEA = OC + DS`` persona a persona (``N_PEA_DISTINTA_OC_DS``);
    * ``PET = PEA + PEI``: cada persona de la PET es activa o inactiva, no ambas ni ninguna
      (``N_PET_SIN_CLASE``);
    * nadie es ocupado y desocupado a la vez (``N_OC_Y_DS``).

    También compara la TD expandida con la bandera ``PEA`` (``TD_PEA_PCT``) y con
    ``OC + DS`` (``TD_OC_DS_PCT``): si coinciden, la derivación por ausencia es correcta.

    Args:
        mercado (DataFrame): ``tesis.geih_oro.mercado_laboral``.
        dominios (DataFrame): ``tesis.dim.dim_dominio_geih``; se usa la fila de la capital
            (``ES_CAPITAL``) para asignar el dominio por ``CODIGO_MUNICIPIO``. Las personas
            fuera de los 23 dominios quedan con ``NOMBRE_DOMINIO = 'FUERA DE DOMINIO'``.

    Returns:
        DataFrame: Una fila por ``PER``/``MES``/``CODIGO_DOMINIO`` con ``N_PET``, ``N_PEA``,
        ``N_PEI``, ``N_OCUPADOS``, ``N_DESOCUPADOS``, ``N_PEA_DISTINTA_OC_DS``,
        ``N_PET_SIN_CLASE``, ``N_OC_Y_DS``, ``TD_PEA_PCT``, ``TD_OC_DS_PCT`` y
        ``DIF_TD_PP``.

    Casos de uso:
        En ``geih_oro.py`` después de escribir ``mercado_laboral``; un período con
        ``N_PEA_DISTINTA_OC_DS > 0`` indica un fallo de unión o de lectura en plata.
    """
    capitales = dominios.filter(F.col("ES_CAPITAL")).select(
        "CODIGO_MUNICIPIO", "CODIGO_DOMINIO", "NOMBRE_DOMINIO"
    )
    oc_ds = F.col("OCUPADO") + F.col("DESOCUPADO")
    w = F.col("FEX_C18")
    return (
        mercado.filter(F.col("PET") == 1)
        .join(capitales, "CODIGO_MUNICIPIO", "left")
        .withColumn(
            "NOMBRE_DOMINIO", F.coalesce("NOMBRE_DOMINIO", F.lit("FUERA DE DOMINIO"))
        )
        .groupBy("PER", "MES", "CODIGO_DOMINIO", "NOMBRE_DOMINIO")
        .agg(
            F.count("*").alias("N_PET"),
            F.sum("PEA").alias("N_PEA"),
            F.sum("PEI").alias("N_PEI"),
            F.sum("OCUPADO").alias("N_OCUPADOS"),
            F.sum("DESOCUPADO").alias("N_DESOCUPADOS"),
            F.count_if(F.col("PEA") != oc_ds).alias("N_PEA_DISTINTA_OC_DS"),
            F.count_if(F.col("PEA") + F.col("PEI") != 1).alias("N_PET_SIN_CLASE"),
            F.count_if((F.col("OCUPADO") == 1) & (F.col("DESOCUPADO") == 1)).alias(
                "N_OC_Y_DS"
            ),
            # try_divide: un dominio sin PEA en el período da NULL en vez de error
            F.try_divide(
                100 * F.sum(F.col("DESOCUPADO") * w), F.sum(F.col("PEA") * w)
            ).alias("TD_PEA_PCT"),
            F.try_divide(100 * F.sum(F.col("DESOCUPADO") * w), F.sum(oc_ds * w)).alias(
                "TD_OC_DS_PCT"
            ),
        )
        .withColumn("DIF_TD_PP", F.col("TD_PEA_PCT") - F.col("TD_OC_DS_PCT"))
        .orderBy("PER", "MES", "CODIGO_DOMINIO")
    )
