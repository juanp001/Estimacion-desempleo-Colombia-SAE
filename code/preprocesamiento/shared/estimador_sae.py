from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from pyspark.sql import functions as F
from tqdm import tqdm


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
            >>> estimador.validar_columnas(df, ["FEX", "DESOCUPADO", "MUNICIPIO"])
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
    ) -> None:
        """Exporta el último resultado calculado a una tabla de Unity Catalog.

        Usa un crossJoin con la(s) tabla(s) origen para registrar el lineage
        en Unity Catalog: al incluirlas en el plan de ejecución, UC detecta
        la dependencia y la muestra en la pestaña Lineage.

        Args:
            tabla_destino (str): Nombre calificado catalog.schema.tabla
                (ej. "tesis.modelo.tasa_desempleo_municipal").
            tabla_origen (str | list[str] | None): Tabla(s) fuente para lineage.
            modo (str): Modo de escritura Spark ("overwrite", "append", etc.).

        Raises:
            RuntimeError: Si se llama antes de ejecutar estimar().

        Example:
            >>> estimador.exportar(
            ...     "tesis.modelo.tasa_desempleo_municipal",
            ...     tabla_origen="tesis.geih_oro.mercado_laboral",
            ... )
        """
        if self._resultado is None:
            raise RuntimeError("Ejecuta estimar() antes de exportar.")

        print(f"Exportando {len(self._resultado)} filas a {tabla_destino}...")
        resultado_spark = self.spark.createDataFrame(self._resultado)

        if tabla_origen:
            tablas = [tabla_origen] if isinstance(tabla_origen, str) else list(tabla_origen)
            print(f"Preservando lineage desde {len(tablas)} tabla(s)...")
            df_marker = (
                self.spark.table(tablas[0])
                .limit(1)
                .select(F.lit(1).alias("_lineage_marker"))
            )
            for t in tablas[1:]:
                df_marker = df_marker.union(
                    self.spark.table(t).limit(1).select(F.lit(1).alias("_lineage_marker"))
                )
            resultado_spark = (
                resultado_spark
                .crossJoin(df_marker.limit(1))
                .drop("_lineage_marker")
            )

        resultado_spark.write.mode(modo).option("overwriteSchema", "true").saveAsTable(tabla_destino)
        print(f"✔ Exportación completada → {tabla_destino}")

    @property
    def resultado(self) -> pd.DataFrame | None:
        """Último resultado calculado (None si no se ha llamado estimar())."""
        return self._resultado


# COMMAND ----------

class EstimacionDirecta(EstimadorSAE):
    """Estimador directo con bootstrap simple usando el estimador de Hájek.

    Calcula la tasa de desempleo por dominio como θ̂ = Σ(w·y)/Σ(w) e infiere
    SE e IC mediante bootstrap naive (remuestreo de individuos con reemplazo).

    Warning:
        Ignora el diseño muestral complejo (estratificación, conglomeración),
        por lo que subestima los errores estándar. Usar solo como baseline SAE
        o para exploración; no publicar como resultado oficial.

    Example:
        >>> est = EstimacionDirecta(spark, num_replicas=2000, seed=42)
        >>> resultado = est.estimar(df, grupo_cols=["PER", "MES", "MUNICIPIO"])
        >>> est.exportar(
        ...     "tesis.modelo.tasa_desempleo_municipal",
        ...     tabla_origen="tesis.geih_oro.mercado_laboral",
        ... )
    """

    def estimar(
        self,
        dataframe,
        grupo_cols: list,
        agregacion_anual: bool = False,
    ) -> pd.DataFrame:
        """Calcula estimación directa con bootstrap simple.

        Args:
            dataframe: DataFrame de Spark con columnas FEX, DESOCUPADO
                y las listadas en grupo_cols.
            grupo_cols (list[str]): Columnas que definen los dominios.
            agregacion_anual (bool): Si True, elimina "MES" de grupo_cols
                para producir estimaciones anuales (más muestra → menor CV).

        Returns:
            pd.DataFrame: Columnas de agrupación más TASA_DESEMPLEO_PCT,
                SE_BOOTSTRAP_PCT, IC_INF_PCT, IC_SUP_PCT, AMPLITUD_IC
                y CV_PORCENTAJE.

        Raises:
            ValueError: Si faltan columnas requeridas en el dataframe.

        Example:
            >>> resultado = est.estimar(df, ["PER", "MES", "MUNICIPIO"])
        """
        grupo_cols_final = self._ajustar_grupo_cols(grupo_cols, agregacion_anual)
        self.validar_columnas(dataframe, list(set(grupo_cols_final + ["FEX", "DESOCUPADO"])))

        print("Convirtiendo a Pandas...")
        df_pd = dataframe.select(*set(grupo_cols_final + ["FEX", "DESOCUPADO"])).toPandas()
        n_dominios = df_pd[grupo_cols_final].drop_duplicates().shape[0]
        print(f"Datos: {len(df_pd):,} filas — {n_dominios} dominios")

        resultado_bootstrap = self._bootstrap_hajek(df_pd, grupo_cols_final)

        columnas_resultado = grupo_cols_final + [
            "TASA_DESEMPLEO_PCT",
            "SE_BOOTSTRAP_PCT",
            "IC_INF_PCT",
            "IC_SUP_PCT",
            "AMPLITUD_IC",
            "CV_PORCENTAJE",
        ]
        self._resultado = (
            resultado_bootstrap[columnas_resultado]
            .sort_values(grupo_cols_final)
            .reset_index(drop=True)
        )

        print("\n⚠ Bootstrap naive — diseño muestral ignorado. Solo usar como baseline SAE.")
        return self._resultado

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _ajustar_grupo_cols(self, grupo_cols: list, agregacion_anual: bool) -> list:
        """Elimina MES de grupo_cols cuando se solicita agregación anual.

        Args:
            grupo_cols (list[str]): Lista original de columnas.
            agregacion_anual (bool): Si True, remueve "MES".

        Returns:
            list[str]: Lista ajustada (copia, no modifica el original).
        """
        if agregacion_anual and "MES" in grupo_cols:
            print("Agregación anual: removiendo MES de la agrupación.")
            return [c for c in grupo_cols if c != "MES"]
        return grupo_cols.copy()

    def _calcular_hajek_pandas(self, df: pd.DataFrame, grupo_cols: list) -> pd.DataFrame:
        """Calcula el estimador de Hájek por grupo: θ̂ = Σ(w·y) / Σ(w).

        Args:
            df (pd.DataFrame): Datos con columnas grupo_cols, FEX y DESOCUPADO.
            grupo_cols (list[str]): Columnas de agrupación.

        Returns:
            pd.DataFrame: grupo_cols + TASA_DESEMPLEO (proporción 0–1).
        """
        return (
            df.groupby(grupo_cols)
            .apply(
                lambda g: pd.Series({
                    "TASA_DESEMPLEO": (g["DESOCUPADO"] * g["FEX"]).sum() / g["FEX"].sum()
                })
            )
            .reset_index()
        )

    def _bootstrap_hajek(self, df: pd.DataFrame, grupo_cols: list) -> pd.DataFrame:
        """Genera B réplicas bootstrap y calcula SE, IC y CV por dominio.

        Args:
            df (pd.DataFrame): Datos con columnas grupo_cols, FEX y DESOCUPADO.
            grupo_cols (list[str]): Columnas de agrupación.

        Returns:
            pd.DataFrame: Estimador original más SE_BOOTSTRAP, IC_INF_PCT,
                IC_SUP_PCT, AMPLITUD_IC, CV_PORCENTAJE y versiones _PCT.
        """
        n = len(df)
        np.random.seed(self.seed)

        estimador_original = self._calcular_hajek_pandas(df, grupo_cols)

        replicas = []
        for _ in tqdm(range(self.num_replicas), desc="Bootstrap"):
            idx = np.random.choice(n, size=n, replace=True)
            replicas.append(self._calcular_hajek_pandas(df.iloc[idx], grupo_cols))

        df_replicas = pd.concat(replicas, ignore_index=True)

        stats = (
            df_replicas.groupby(grupo_cols)["TASA_DESEMPLEO"]
            .agg([
                ("MEDIA_BOOTSTRAP", "mean"),
                ("VAR_BOOTSTRAP",   "var"),
                ("SE_BOOTSTRAP",    "std"),
                ("IC_INF_2.5",  lambda x: np.percentile(x, 2.5)),
                ("IC_SUP_97.5", lambda x: np.percentile(x, 97.5)),
            ])
            .reset_index()
        )

        resultado = estimador_original.merge(stats, on=grupo_cols, how="left")
        resultado["TASA_DESEMPLEO_PCT"] = resultado["TASA_DESEMPLEO"] * 100
        resultado["SE_BOOTSTRAP_PCT"]   = resultado["SE_BOOTSTRAP"]   * 100
        resultado["IC_INF_PCT"]         = resultado["IC_INF_2.5"]     * 100
        resultado["IC_SUP_PCT"]         = resultado["IC_SUP_97.5"]    * 100
        resultado["AMPLITUD_IC"]        = (resultado["IC_SUP_97.5"] - resultado["IC_INF_2.5"]) * 100
        resultado["CV_PORCENTAJE"]      = (resultado["SE_BOOTSTRAP"] / resultado["TASA_DESEMPLEO"]) * 100

        print(f"\n✔ Bootstrap: {self.num_replicas:,} réplicas — {len(resultado)} dominios estimados")
        return resultado
