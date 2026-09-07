from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from scipy import stats


class ModeloAreaPequena(ABC):
    """Interfaz base para modelos de estimación de áreas pequeñas (SAE) tipo Fay-Herriot.

    Centraliza lo que es común a cualquier variante (clásica, espacial,
    temporal): construcción de la matriz de diseño, comparación del MSE
    contra la varianza directa y el armado de la tabla de resultados por
    dominio. La construcción de la matriz de varianzas V, la
    log-verosimilitud y el MSE de Prasad-Rao difieren entre variantes y
    quedan a cargo de `ajustar()` en cada subclase concreta (patrón
    Template Method).

    Tras llamar a `ajustar()`, la subclase debe poblar los siguientes
    atributos de instancia: `A_hat` (float), `beta_hat`, `se_beta`,
    `t_stats`, `p_vals` (np.ndarray, shape (p,)), `cov_beta` (np.ndarray,
    shape (p, p)), `mu_hat`, `eblup`, `mse`, `rmse`, `cv`, `residuals`
    (np.ndarray, shape (n,)), `sw_stat`, `sw_pval`, `r2` y `aic`
    (float). `gamma_i` (np.ndarray, shape (n,)) es opcional: solo aplica a
    variantes con shrinkage escalar por dominio (la clásica lo tiene; una
    variante espacial con matriz de covarianza completa puede omitirlo).

    Args:
        covars (list[str]): Nombres de las covariables a incluir (sin
            intercepto).
        df (pd.DataFrame): Datos con una fila por dominio; debe contener
            `covars`, `y_col` y `se_col`.
        y_col (str): Columna con la estimación directa de la variable
            objetivo.
        se_col (str): Columna con el error estándar de la estimación
            directa (se eleva al cuadrado para obtener la varianza Di).

    Raises:
        ValueError: Si `covars`, `y_col` o `se_col` no existen en `df`.

    Example:
        >>> class FayHerriotClasico(ModeloAreaPequena):
        ...     def ajustar(self):
        ...         pass  # ver shared/fay_herriot.py
        >>> modelo = FayHerriotClasico(["IND_PROD"], df, "TASA_DESEMPLEO_PCT", "SE_BOOTSTRAP_PCT")
        >>> modelo.ajustar()
    """

    def __init__(self, covars: list, df: pd.DataFrame, y_col: str, se_col: str):
        columnas_requeridas = set(covars) | {y_col, se_col}
        faltantes = columnas_requeridas - set(df.columns)
        if faltantes:
            raise ValueError(f"Columnas faltantes en df: {sorted(faltantes)}")

        self.covars = covars
        self.df     = df
        self.y_col  = y_col
        self.se_col = se_col

        self.Y  = df[y_col].values
        self.Di = df[se_col].values ** 2
        self.X  = np.column_stack([np.ones(len(df))] + [df[c].values for c in covars])
        self.n  = len(self.Y)
        self.p  = self.X.shape[1]

    @abstractmethod
    def ajustar(self) -> None:
        """Ajusta el modelo: varianza de efectos aleatorios, coeficientes por
        GLS, predictor EBLUP y su MSE.

        Cada subclase implementa esto según la estructura de su matriz de
        varianzas V. Debe poblar los atributos documentados en el
        docstring de la clase.
        """

    def validar_mse_directo(self) -> dict:
        """Compara el MSE del predictor contra la varianza directa Di.

        Returns:
            dict: `mse_ratio` (np.ndarray, Di/mse), `pct_mejora_mse`
                (np.ndarray, % de reducción), `dominios_mejoran` (float,
                fracción de dominios con mse < Di), `wil_stat` y
                `wil_pval` (float, test de Wilcoxon Di > mse).

        Raises:
            RuntimeError: Si se llama antes de `ajustar()`.
        """
        if not hasattr(self, "mse"):
            raise RuntimeError("Llama a ajustar() antes de validar_mse_directo().")

        mse_ratio        = self.Di / self.mse
        pct_mejora_mse   = 100 * (self.Di - self.mse) / self.Di
        dominios_mejoran = float(np.mean(self.mse < self.Di))
        wil_stat, wil_pval = stats.wilcoxon(self.Di - self.mse, alternative="greater")
        return {
            "mse_ratio":        mse_ratio,
            "pct_mejora_mse":   pct_mejora_mse,
            "dominios_mejoran": dominios_mejoran,
            "wil_stat":         wil_stat,
            "wil_pval":         wil_pval,
        }

    def tabla_resultados(self, dominio_col: str = "DOMINIO", metadata_cols: list = None) -> pd.DataFrame:
        """Construye la tabla de resultados por dominio.

        Args:
            dominio_col (str): Columna identificadora del dominio en
                `self.df`.
            metadata_cols (list[str] | None): Columnas de identificación a
                conservar (departamento, municipio, periodo). Si es None,
                usa `["PER", "MES", "DEPARTAMENTO", "MUNICIPIO"]`.

        Returns:
            pd.DataFrame: Una fila por dominio con la estimación directa,
                EBLUP, MSE/RMSE/CV del EBLUP, shrinkage y las métricas de
                mejora frente a la varianza directa.

        Raises:
            RuntimeError: Si se llama antes de `ajustar()`.
            ValueError: Si `dominio_col`, `metadata_cols` o `CV_PORCENTAJE`
                no existen en `self.df`.
        """
        if not hasattr(self, "eblup"):
            raise RuntimeError("Llama a ajustar() antes de tabla_resultados().")

        metadata_cols = metadata_cols or ["PER", "MES", "DEPARTAMENTO", "MUNICIPIO"]
        columnas_base = [dominio_col, *metadata_cols, self.y_col, self.se_col, "CV_PORCENTAJE"]
        faltantes = set(columnas_base) - set(self.df.columns)
        if faltantes:
            raise ValueError(f"Columnas faltantes en df: {sorted(faltantes)}")

        validacion = self.validar_mse_directo()
        gamma = getattr(self, "gamma_i", None)

        res_df = self.df[columnas_base].copy()
        res_df["VARIANZA_DIRECTA"] = self.Di
        if gamma is not None:
            res_df["GAMMA_SHRINKAGE"] = gamma.round(4)
        res_df["PRED_SINTETICO"]  = self.mu_hat.round(4)
        res_df["EBLUP"]           = self.eblup.round(4)
        res_df["MSE_EBLUP"]       = self.mse.round(6)
        res_df["RMSE_EBLUP"]      = self.rmse.round(4)
        res_df["CV_EBLUP_PCT"]    = self.cv.round(2)
        res_df["MEJORA_CV_PCT"]   = (res_df["CV_PORCENTAJE"] - res_df["CV_EBLUP_PCT"]).round(2)
        res_df["RATIO_MSE"]       = validacion["mse_ratio"].round(4)
        res_df["MEJORA_MSE_PCT"]  = validacion["pct_mejora_mse"].round(2)
        res_df["MEJORA_MSE"]      = np.where(self.mse < self.Di, "✓", "✗")
        return res_df
