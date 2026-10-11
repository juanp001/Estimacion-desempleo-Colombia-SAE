"""Factor de expansión CNPV 2018 de la capa oro (comentario G7-B6).

Antes ``geih_oro`` tomaba ``FEX_C18`` de ``dim_fex`` con ``coalesce(..., 0)``: una persona
sin factor quedaba con peso 0 y desaparecía de las tasas sin aviso. Ahora:

* **Marco nuevo**: ``FEX`` de características generales ya es ``FEX_C18`` (el archivo trae el
  factor calibrado con las proyecciones del CNPV 2018), así que se usa tal cual.
* **Marco antiguo**: el ``FEX`` del archivo es ``FEX_C_2011``, calibrado con las proyecciones
  del censo 2005 y una PET de 10 años y más; mezclarlo con el factor 2018 (PET de 15 años y
  más) produce el salto de serie documentado por el DANE (``series_geih2005``, PDF 19 y 77).
  Por eso el factor sale solo de ``dim_fex`` y, si falta, queda nulo.

``verificar_factor_expansion`` detiene el notebook si alguna persona queda sin factor válido.
"""

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F


def factor_expansion_c18(marco: Column, fex_archivo: Column, fex_dim: Column) -> Column:
    """Expresión del factor de expansión CNPV 2018 según el marco de la fila.

    Args:
        marco (Column): Columna ``MARCO`` de plata (``"NUEVO"`` o ``"ANTIGUO"``).
        fex_archivo (Column): ``FEX`` de características generales (``FEX_C18`` en el marco
            nuevo, ``FEX_C_2011`` en el antiguo).
        fex_dim (Column): ``FEX_C18`` de ``tesis.geih_plata.dim_fex`` tras el LEFT JOIN.

    Returns:
        Column: ``fex_archivo`` en el marco nuevo y ``fex_dim`` en el antiguo; nulo si
        ``dim_fex`` no cubre a la persona (nunca 0 ni el factor del censo 2005).

    Casos de uso:
        En el ``select`` de ``geih_oro.py``:
        ``factor_expansion_c18(cg.MARCO, cg.FEX, fex["FEX_C18"]).alias("FEX_C18")``.
    """
    return F.when(marco == "NUEVO", fex_archivo).otherwise(fex_dim)


def personas_sin_factor(df: DataFrame) -> DataFrame:
    """Conteo, por marco y período, de personas sin factor de expansión válido.

    Args:
        df (DataFrame): Tabla con ``MARCO``, ``PER``, ``MES`` y ``FEX_C18`` (la de oro antes
            de escribirse).

    Returns:
        DataFrame: Una fila por ``MARCO``/``PER``/``MES`` con ``N_PERSONAS`` y
        ``N_SIN_FEX`` (``FEX_C18`` nulo o ≤ 0), ordenada por período.

    Casos de uso:
        Reporte previo a ``verificar_factor_expansion``; también sirve para auditar cuántos
        registros del período analítico habrían quedado con peso 0 con la regla anterior.
    """
    return (
        df.groupBy("MARCO", "PER", "MES")
        .agg(
            F.count("*").alias("N_PERSONAS"),
            F.count_if(F.col("FEX_C18").isNull() | (F.col("FEX_C18") <= 0)).alias(
                "N_SIN_FEX"
            ),
        )
        .orderBy("PER", "MES", "MARCO")
    )


def verificar_factor_expansion(conteo: DataFrame) -> None:
    """Imprime el conteo de personas sin factor y falla si hay alguna.

    Args:
        conteo (DataFrame): Salida de ``personas_sin_factor``.

    Returns:
        None. Imprime ``PASS`` con el total de personas revisadas.

    Raises:
        ValueError: Si alguna persona tiene ``FEX_C18`` nulo o ≤ 0; el mensaje lista los
            períodos afectados (p. ej. un mes del marco antiguo que ``dim_fex`` no cubre).

    Casos de uso:
        En ``geih_oro.py`` antes de ``escribir_tabla``, para que una tabla con pesos
        faltantes no llegue a la estimación directa.
    """
    pdf = conteo.toPandas()
    malos = pdf[pdf.N_SIN_FEX > 0]
    if not malos.empty:
        raise ValueError(
            "G7-B6: personas sin factor de expansión CNPV 2018 (FEX_C18 nulo o <= 0). "
            "Agregue el período a dim_fex o revise el archivo de origen:\n"
            + malos.to_string(index=False)
        )
    print(
        f"PASS: las {int(pdf.N_PERSONAS.sum()):,} personas tienen FEX_C18 > 0 "
        f"({pdf.PER.nunique()} años, {len(pdf)} marco-períodos)"
    )
