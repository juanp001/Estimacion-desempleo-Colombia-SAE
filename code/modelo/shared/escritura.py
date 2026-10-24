"""Escritura de las tablas del modelo en Unity Catalog (R-40, R-38).

Una sola forma de escribir: pandas → Spark, sobrescribiendo la tabla y su esquema. Las
tablas del notebook del modelo se acumulan en un `EscrituraDiferida` y se escriben todas al
final, después de las verificaciones (R-38): si una verificación falla, no se publica nada.
"""

import pandas as pd


def escribir_tabla(
    spark,
    df_pd: pd.DataFrame,
    tabla: str,
    periodo: dict = None,
    comentario: str = None,
) -> None:
    """Escribe un DataFrame de pandas en Unity Catalog (sobrescribe tabla y esquema).

    Args:
        spark (pyspark.sql.SparkSession): Sesión de Spark del notebook.
        df_pd (pd.DataFrame): Datos a escribir.
        tabla (str): Nombre calificado `catalogo.esquema.tabla`.
        periodo (dict | None): Columnas constantes a agregar antes de escribir, p. ej.
            `{"PER": 2018, "MES": 12}`.
        comentario (str | None): Comentario de la tabla en Unity Catalog (`COMMENT ON
            TABLE`), p. ej. su origen y estado (R-11).

    Returns:
        None

    Example:
        >>> escribir_tabla(spark, df, "tesis.modelo.fh_coeficientes")  # doctest: +SKIP

    Casos de uso:
        - Todas las tablas de `fay_herriot.py` (a través de `EscrituraDiferida`) y de
          `sensibilidad_varianza.py`.
    """
    if periodo:
        df_pd = df_pd.assign(**periodo)
    (
        spark.createDataFrame(df_pd)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(tabla)
    )
    if comentario:
        texto = comentario.replace("'", "\\'")
        spark.sql(f"COMMENT ON TABLE {tabla} IS '{texto}'")
    print(f"Tabla escrita: {tabla} ({len(df_pd)} filas)")


class EscrituraDiferida:
    """Acumula tablas y las escribe juntas al final del notebook (R-38).

    El notebook del modelo verifica el benchmarking y la tabla final en la celda 12. Si las
    tablas se escribieran a medida que se calculan, una verificación fallida dejaría publicada
    una versión errónea (el job no tiene transacciones). Con esta clase las celdas solo
    registran lo que van a escribir, y la última celda escribe todo cuando las verificaciones
    pasaron.

    Args:
        spark (pyspark.sql.SparkSession): Sesión de Spark del notebook.

    Example:
        >>> pendientes = EscrituraDiferida(spark=None)
        >>> pendientes.agregar(pd.DataFrame({"a": [1]}), "tesis.modelo.x")
        >>> pendientes.tablas()
        ['tesis.modelo.x']

    Casos de uso:
        - `fay_herriot.py`: cada celda llama a `agregar` y la celda 13 llama a `escribir_todas`.
    """

    def __init__(self, spark):
        """Guarda la sesión de Spark y una lista vacía de pendientes.

        Args:
            spark (pyspark.sql.SparkSession | None): Sesión de Spark (None solo en pruebas).
        """
        self.spark = spark
        self._pendientes = {}

    def agregar(
        self,
        df_pd: pd.DataFrame,
        tabla: str,
        periodo: dict = None,
        comentario: str = None,
    ) -> None:
        """Registra una tabla para escribirla al final (reemplaza un registro previo).

        Args:
            df_pd (pd.DataFrame): Datos a escribir (se guarda una copia).
            tabla (str): Nombre calificado de la tabla destino.
            periodo (dict | None): Columnas constantes a agregar (`{"PER": ..., "MES": ...}`).
            comentario (str | None): Comentario de la tabla en Unity Catalog.

        Returns:
            None
        """
        self._pendientes[tabla] = (df_pd.copy(), periodo, comentario)

    def tablas(self) -> list:
        """Nombres de las tablas registradas, en el orden en que se agregaron.

        Returns:
            list[str]: Tablas pendientes de escribir.
        """
        return list(self._pendientes)

    def escribir_todas(self) -> None:
        """Escribe todas las tablas registradas y vacía la lista.

        Returns:
            None
        """
        for tabla, (df_pd, periodo, comentario) in self._pendientes.items():
            escribir_tabla(self.spark, df_pd, tabla, periodo, comentario)
        self._pendientes = {}
