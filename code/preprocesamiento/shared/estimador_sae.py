"""Estimadores de áreas pequeñas: interfaz común y estimador directo de Hájek.

``EstimadorSAE`` define la validación de columnas y la exportación a Unity Catalog;
``EstimacionDirecta`` calcula la tasa de desempleo por dominio con la varianza bootstrap de
``shared/bootstrap.py`` (vivienda como conglomerado dentro del dominio, G7-B3). Lo usan
``estimacion_directa.py`` (tabla ``tasa_desempleo_municipal``),
``analisis/sensibilidad_ventana_temporal.py`` y ``modelo/sensibilidad_varianza.py``.
"""

from abc import ABC, abstractmethod

import pandas as pd
from pyspark.sql import functions as F

from preprocesamiento.shared.bootstrap import varianza_por_dominio


class EstimadorSAE(ABC):
    """Interfaz base para estimadores de Small Area Estimation (SAE).

    Define validación de columnas, exportación a Unity Catalog y la firma
    de estimar() que cada estimador concreto debe implementar
    (patrón Template Method + Strategy).

    Args:
        spark: SparkSession activa.
        num_replicas (int): Réplicas bootstrap para cálculo de varianza.
        seed (int): Semilla aleatoria para reproducibilidad.
    """

    def __init__(self, spark, num_replicas: int = 1000, seed: int = 42):
        """Guarda la sesión y los parámetros del bootstrap.

        Args:
            spark: SparkSession activa.
            num_replicas (int): Réplicas bootstrap (el notebook usa `BOOTSTRAP_REPLICAS`=2000).
            seed (int): Semilla aleatoria (el notebook usa `BOOTSTRAP_SEED`=42).

        Example:
            >>> est = EstimacionDirecta(spark, num_replicas=2000, seed=42)
        """
        self.spark = spark
        self.num_replicas = num_replicas
        self.seed = seed
        self._resultado: pd.DataFrame | None = None

    @abstractmethod
    def estimar(self, dataframe, grupo_cols: list, **kwargs) -> pd.DataFrame:
        """Calcula estimaciones para los dominios definidos por grupo_cols.

        Args:
            dataframe: DataFrame de Spark con los datos fuente.
            grupo_cols (list[str]): Columnas que definen los dominios de estimación.
            **kwargs: Argumentos adicionales específicos del estimador.

        Returns:
            pd.DataFrame: Estimaciones y medidas de precisión por dominio.
        """

    def validar_columnas(self, dataframe, columnas_requeridas: list) -> None:
        """Verifica que las columnas requeridas existan en el DataFrame.

        Args:
            dataframe: DataFrame de Spark a validar.
            columnas_requeridas (list[str]): Nombres de columnas necesarias.

        Raises:
            ValueError: Si alguna columna requerida no existe en el DataFrame.

        Example:
            >>> estimador.validar_columnas(df, ["FEX", "DESOCUPADO", "CODIGO_DOMINIO"])
        """
        faltantes = set(columnas_requeridas) - set(dataframe.columns)
        if faltantes:
            raise ValueError(
                f"Columnas faltantes: {sorted(faltantes)}\n"
                f"Columnas disponibles: {sorted(dataframe.columns)}"
            )

    def exportar(
        self,
        tabla_destino: str,
        tabla_origen=None,
        modo: str = "overwrite",
        resultado: pd.DataFrame | None = None,
    ) -> None:
        """Exporta un resultado a una tabla de Unity Catalog.

        Usa un crossJoin con la(s) tabla(s) origen para registrar el lineage
        en Unity Catalog: al incluirlas en el plan de ejecución, UC detecta
        la dependencia y la muestra en la pestaña Lineage.

        Args:
            tabla_destino (str): Nombre calificado catalog.schema.tabla
                (ej. "tesis.preprocesamiento.tasa_desempleo_municipal").
            tabla_origen (str | list[str] | None): Tabla(s) fuente para lineage.
            modo (str): Modo de escritura Spark ("overwrite", "append", etc.).
            resultado (pd.DataFrame | None): Tabla a exportar. Por defecto el último resultado
                de estimar(); el notebook pasa el resultado con sus columnas adicionales (R-28:
                antes escribía el atributo privado ``_resultado``).

        Raises:
            RuntimeError: Si no hay resultado (no se ha llamado estimar()).
            ValueError: Si una tabla origen está vacía: el crossJoin del linaje escribiría
                0 filas sin error (R-28).

        Example:
            >>> estimador.exportar(
            ...     "tesis.preprocesamiento.tasa_desempleo_municipal",
            ...     tabla_origen="tesis.geih_oro.mercado_laboral",
            ... )
        """
        if resultado is None:
            resultado = self._resultado
        if resultado is None:
            raise RuntimeError("Ejecuta estimar() antes de exportar.")

        print(f"Exportando {len(resultado)} filas a {tabla_destino}...")
        resultado_spark = self.spark.createDataFrame(resultado)

        if tabla_origen:
            tablas = (
                [tabla_origen] if isinstance(tabla_origen, str) else list(tabla_origen)
            )
            print(f"Preservando lineage desde {len(tablas)} tabla(s)...")
            df_marker = (
                self.spark.table(tablas[0])
                .limit(1)
                .select(F.lit(1).alias("_lineage_marker"))
            )
            for t in tablas[1:]:
                df_marker = df_marker.union(
                    self.spark.table(t)
                    .limit(1)
                    .select(F.lit(1).alias("_lineage_marker"))
                )
            df_marker = df_marker.limit(1)
            if df_marker.count() != 1:
                raise ValueError(f"Tabla(s) origen vacía(s) para el linaje: {tablas}")
            resultado_spark = resultado_spark.crossJoin(df_marker).drop(
                "_lineage_marker"
            )

        resultado_spark.write.mode(modo).option("overwriteSchema", "true").saveAsTable(
            tabla_destino
        )
        print(f"✔ Exportación completada → {tabla_destino}")

    @property
    def resultado(self) -> pd.DataFrame | None:
        """Último resultado calculado (None si no se ha llamado estimar())."""
        return self._resultado


class EstimacionDirecta(EstimadorSAE):
    """Estimador directo de Hájek con varianza bootstrap por conglomerados dentro del dominio.

    Calcula la tasa de desempleo por dominio como θ̂ = Σ(w·y)/Σ(w). La varianza sale de un
    bootstrap que remuestrea **viviendas** (todas sus personas) con reemplazo **dentro de cada
    dominio**, con el número de viviendas de la muestra fijo (G7-B3; Morales et al., 2021, p. 61).
    Como control se calcula también la varianza por linealización de Taylor con las mismas
    unidades (ver `shared/bootstrap.py`).

    Warning:
        Los microdatos no traen el estrato interno ni el segmento de la GEIH, y los pesos no
        se recalibran en cada réplica como hace el DANE con el FEX (calibración por sexo y edad,
        GEIH v9, PDF 13-14; R-25). La varianza es una aproximación a la del diseño: no se sabe
        si esta es mayor o menor, ni por cuánto. No publicar como error de muestreo oficial.

    Example:
        >>> est = EstimacionDirecta(spark, num_replicas=2000, seed=42)
        >>> resultado = est.estimar(df, grupo_cols=["PER", "MES", "CODIGO_DOMINIO"])
        >>> est.exportar(
        ...     "tesis.preprocesamiento.tasa_desempleo_municipal",
        ...     tabla_origen="tesis.geih_oro.mercado_laboral",
        ... )
    """

    def estimar(
        self,
        dataframe,
        grupo_cols: list,
        col_conglomerado: str | None = "ID_VIVIENDA",
    ) -> pd.DataFrame:
        """Calcula la estimación directa y su varianza bootstrap por dominio.

        Args:
            dataframe: DataFrame de Spark con columnas FEX, DESOCUPADO, las listadas en
                grupo_cols y, si se usa, col_conglomerado.
            grupo_cols (list[str]): Columnas que definen los dominios (estratos del remuestreo).
                Para una ventana de varios meses, el notebook reescribe PER/MES con el cierre.
            col_conglomerado (str | None): Conglomerado que se remuestrea. Por defecto la
                vivienda (`ID_VIVIENDA` de `tesis.geih_oro.mercado_laboral`); con `None` se
                remuestrean personas (solo para comparar, en la sensibilidad del modelo).

        Returns:
            pd.DataFrame: Columnas de agrupación más TASA_DESEMPLEO_PCT,
                SE_BOOTSTRAP_PCT, IC_INF_PCT, IC_SUP_PCT, AMPLITUD_IC, CV_PORCENTAJE,
                SE_TAYLOR_PCT y, si hay conglomerado, N_VIVIENDAS.

        Raises:
            ValueError: Si faltan columnas requeridas, si el remuestreo no usó todas las
                personas o si algún dominio queda con tasa o SE igual a 0 (R-27).

        Example:
            >>> resultado = est.estimar(df, ["PER", "MES", "CODIGO_DOMINIO"])
            >>> por_personas = est.estimar(df, ["PER", "MES", "CODIGO_DOMINIO"], col_conglomerado=None)
        """
        grupo_cols_final = list(grupo_cols)
        columnas = list(
            dict.fromkeys(
                grupo_cols_final
                + ["FEX", "DESOCUPADO"]
                + ([col_conglomerado] if col_conglomerado else [])
            )
        )
        self.validar_columnas(dataframe, columnas)

        print("Convirtiendo a Pandas...")
        df_pd = dataframe.select(*columnas).toPandas()
        n_dominios = df_pd[grupo_cols_final].drop_duplicates().shape[0]
        unidad = f"conglomerado {col_conglomerado}" if col_conglomerado else "personas"
        print(
            f"Datos: {len(df_pd):,} filas — {n_dominios} dominios — remuestreo por {unidad}"
        )

        resultado = varianza_por_dominio(
            df_pd, grupo_cols_final, col_conglomerado, self.num_replicas, self.seed
        )
        # R-27: el remuestreo debe ver a todas las personas, y ninguna tasa ni SE puede ser 0
        # (ψ_d = 0 y CV infinito harían que el modelo tome la directa como exacta sin aviso)
        n_personas = int(resultado["N_PERSONAS"].sum())
        if n_personas != len(df_pd):
            raise ValueError(
                f"El bootstrap usó {n_personas:,} de {len(df_pd):,} personas"
            )
        degenerados = resultado[
            (resultado["TASA_DESEMPLEO"] == 0) | (resultado["SE_BOOTSTRAP"] == 0)
        ]
        if not degenerados.empty:
            raise ValueError(
                "Dominios con tasa o SE igual a 0:\n"
                + degenerados[grupo_cols_final].to_string(index=False)
            )
        resultado["TASA_DESEMPLEO_PCT"] = resultado["TASA_DESEMPLEO"] * 100
        resultado["SE_BOOTSTRAP_PCT"] = resultado["SE_BOOTSTRAP"] * 100
        resultado["IC_INF_PCT"] = resultado["IC_INF_2.5"] * 100
        resultado["IC_SUP_PCT"] = resultado["IC_SUP_97.5"] * 100
        resultado["AMPLITUD_IC"] = resultado["IC_SUP_PCT"] - resultado["IC_INF_PCT"]
        resultado["CV_PORCENTAJE"] = (
            resultado["SE_BOOTSTRAP"] / resultado["TASA_DESEMPLEO"] * 100
        )
        resultado["SE_TAYLOR_PCT"] = resultado["SE_TAYLOR"] * 100

        columnas_resultado = grupo_cols_final + [
            "TASA_DESEMPLEO_PCT",
            "SE_BOOTSTRAP_PCT",
            "IC_INF_PCT",
            "IC_SUP_PCT",
            "AMPLITUD_IC",
            "CV_PORCENTAJE",
            "SE_TAYLOR_PCT",
        ]
        if col_conglomerado:
            resultado["N_VIVIENDAS"] = resultado["N_CONGLOMERADOS"]
            columnas_resultado.append("N_VIVIENDAS")

        self._resultado = (
            resultado[columnas_resultado]
            .sort_values(grupo_cols_final)
            .reset_index(drop=True)
        )

        print(
            f"\n✔ Bootstrap: {self.num_replicas:,} réplicas por dominio — "
            f"{len(self._resultado)} dominios estimados"
        )
        print(
            "Aproximación a la varianza del diseño: no reproduce el estrato interno, el "
            "segmento ni la calibración del FEX de la GEIH (G7-B3, R-25)."
        )
        return self._resultado
