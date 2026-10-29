"""Modelo Fay-Herriot clásico (efectos aleatorios independientes por dominio).

Â se estima por REML, β̂ por mínimos cuadrados generalizados, el AIC con la verosimilitud ML
(más su corrección de muestra pequeña, AICc, como complemento: con pocos dominios el AIC
tiende a favorecer modelos con demasiados parámetros) y el MSE del EBLUP con el estimador de Prasad-Rao para REML de Datta y Lahiri (2000; Morales
et al., 2021, p. 440).
"""

import numpy as np
from scipy import stats
from scipy.optimize import minimize_scalar

from shared.modelo_area_pequena import ModeloAreaPequena

# Tolerancia, en escala log, para decir que Â quedó en una cota del optimizador (R-41). El
# optimizador acotado de scipy converge a 1e-5 en log A; 1e-3 equivale a Â a menos de 0.1 % de
# la cota.
TOLERANCIA_COTA_LOG = 1e-3


def _cotas_log_A(Y: np.ndarray) -> tuple:
    """Cotas de log A para el optimizador: [log 1e-6, log(10·var(Y))].

    Args:
        Y (np.ndarray): Variable objetivo, shape (n,).

    Returns:
        tuple[float, float]: (cota inferior, cota superior) de log A.

    Example:
        >>> [round(float(c), 3) for c in _cotas_log_A(np.array([1.0, 3.0]))]
        [-13.816, 2.303]
    """
    return np.log(1e-6), np.log(np.var(Y) * 10)


def en_cota(
    log_A: float, cotas: tuple, tolerancia: float = TOLERANCIA_COTA_LOG
) -> bool:
    """True si log Â quedó a menos de `tolerancia` de alguna cota del optimizador (R-41).

    Un Â en la cota inferior (1e-6) es el caso Â ≈ 0 (el EBLUP se reduce al sintético); en la
    superior, el optimizador no encontró un máximo interior. En ambos casos el ajuste no es
    un máximo regular de la verosimilitud y conviene avisarlo.

    Args:
        log_A (float): Logaritmo de Â devuelto por el optimizador.
        cotas (tuple[float, float]): Cotas de log A (`_cotas_log_A`).
        tolerancia (float): Distancia máxima, en escala log.

    Returns:
        bool: Si Â está en una cota.

    Example:
        >>> en_cota(np.log(1e-6) + 1e-6, (np.log(1e-6), 2.0))
        True
        >>> en_cota(0.0, (np.log(1e-6), 2.0))
        False
    """
    return bool(min(abs(log_A - cotas[0]), abs(log_A - cotas[1])) < tolerancia)


def _vi_xtvi_xtvix(A: float, X: np.ndarray, Di: np.ndarray) -> tuple:
    """Componentes comunes de GLS bajo V = diag(Di + A): V⁻¹, X'V⁻¹ y X'V⁻¹X.

    Args:
        A (float): Varianza de los efectos aleatorios (debe ser >= 0).
        X (np.ndarray): Matriz de diseño, shape (n, p).
        Di (np.ndarray): Varianza directa por dominio, shape (n,).

    Returns:
        tuple: (Vi, XtVi, XtViX) — Vi es la diagonal de V⁻¹ (shape (n,)),
            XtVi tiene shape (p, n) y XtViX tiene shape (p, p).

    Uso:
        Auxiliar de `_gls_beta` y de las log-verosimilitudes; no se llama desde los notebooks.
    """
    Vi = 1.0 / (Di + A)
    XtVi = X.T * Vi
    XtViX = XtVi @ X
    return Vi, XtVi, XtViX


def _gls_beta(A: float, Y: np.ndarray, X: np.ndarray, Di: np.ndarray) -> tuple:
    """Estimación GLS de beta: β̂ = (X'V⁻¹X)⁻¹X'V⁻¹Y, con V = diag(Di + A).

    Args:
        A (float): Varianza de los efectos aleatorios.
        Y (np.ndarray): Variable objetivo, shape (n,).
        X (np.ndarray): Matriz de diseño, shape (n, p).
        Di (np.ndarray): Varianza directa por dominio, shape (n,).

    Returns:
        tuple: (beta, XtVi, XtViX). `beta` tiene shape (p,).

    Raises:
        numpy.linalg.LinAlgError: Si X'V⁻¹X es singular.

    Uso:
        Auxiliar de `_estimar_beta_gls` y de `_neg_reml_loglik`; no se llama desde los notebooks.
    """
    Vi, XtVi, XtViX = _vi_xtvi_xtvix(A, X, Di)
    beta = np.linalg.solve(XtViX, XtVi @ Y)
    return beta, XtVi, XtViX


def _neg_reml_loglik(
    log_A: float, Y: np.ndarray, X: np.ndarray, Di: np.ndarray
) -> float:
    """Log-verosimilitud REML negativa bajo V = diag(Di + A); usada para estimar A.

    Args:
        log_A (float): Logaritmo de la varianza de efectos aleatorios
            (se optimiza en escala log para garantizar A > 0).
        Y (np.ndarray): Variable objetivo, shape (n,).
        X (np.ndarray): Matriz de diseño, shape (n, p).
        Di (np.ndarray): Varianza directa por dominio, shape (n,).

    Returns:
        float: Negativo de la log-verosimilitud REML (1e10 si X'V⁻¹X es
            singular, para que el optimizador descarte ese punto).

    Uso:
        Función objetivo de `minimize_scalar` en `_estimar_varianza_aleatoria`.
    """
    A = np.exp(log_A)
    Vi, Vi_X, Q = _vi_xtvi_xtvix(A, X, Di)
    try:
        Qinv = np.linalg.inv(Q)
    except np.linalg.LinAlgError:
        return 1e10
    PY = Vi * Y - (Vi_X.T @ (Qinv @ (Vi_X @ Y)))
    log_det_V = np.sum(np.log(Di + A))
    log_det_Q = np.linalg.slogdet(Q)[1]
    reml_ll = -0.5 * (log_det_V + log_det_Q + Y @ PY)
    return -reml_ll


def _neg_ml_loglik(log_A: float, Y: np.ndarray, X: np.ndarray, Di: np.ndarray) -> float:
    """Log-verosimilitud ML negativa bajo V = diag(Di + A); usada para el AIC.

    A diferencia de REML, ML no penaliza por la pérdida de grados de
    libertad al estimar beta, por lo que sus valores no son comparables
    entre sí para distintos A, pero sí lo son entre modelos con distinto
    número de covariables (lo que requiere el AIC).

    Args:
        log_A (float): Logaritmo de la varianza de efectos aleatorios.
        Y (np.ndarray): Variable objetivo, shape (n,).
        X (np.ndarray): Matriz de diseño, shape (n, p).
        Di (np.ndarray): Varianza directa por dominio, shape (n,).

    Returns:
        float: Negativo de la log-verosimilitud ML (1e10 si X'V⁻¹X es
            singular).

    Uso:
        Función objetivo de `minimize_scalar` en `_calcular_aic`.
    """
    A = np.exp(log_A)
    Vi, XtVi, XtViX = _vi_xtvi_xtvix(A, X, Di)
    try:
        beta = np.linalg.solve(XtViX, XtVi @ Y)
    except np.linalg.LinAlgError:
        return 1e10
    n = len(Y)
    resid = Y - X @ beta
    log_det_V = np.sum(np.log(Di + A))
    quadratic = np.sum(Vi * resid**2)
    ml_ll = -0.5 * (n * np.log(2 * np.pi) + log_det_V + quadratic)
    return -ml_ll


class FayHerriotClasico(ModeloAreaPequena):
    """Modelo Fay-Herriot clásico (efectos aleatorios independientes por dominio).

    Asume V = diag(Di + A): cada dominio tiene un efecto aleatorio i.i.d.
    con varianza A común, independiente entre dominios. Es el modelo de
    áreas pequeñas más simple de la familia Fay-Herriot; la variante
    espacial (matriz de proximidad, `FayHerriotEspacial` en
    `fay_herriot_espacial.py`) vive en un módulo separado que hereda de
    `ModeloAreaPequena` pero con su propia estructura de V. No hay variante
    temporal en el proyecto.

    Args / Raises: ver `ModeloAreaPequena`.

    Además del contrato de `ModeloAreaPequena`, `ajustar()` deja tres banderas de
    convergencia (R-41): `convergio_reml` y `convergio_ml` (`res.success` del optimizador de
    REML y de ML) y `A_en_cota` (Â en una cota del optimizador). `avisos_ajuste()` las resume.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"x": [1.0, 2, 3, 4, 5, 6], "y": [2.1, 3.9, 6.2, 8.1, 9.8, 12.3],
        ...                    "se": [0.5] * 6})
        >>> modelo = FayHerriotClasico(["x"], df, "y", "se")
        >>> modelo.ajustar()
        >>> modelo.convergio_reml, modelo.avisos_ajuste()
        (True, ['Â en la cota del optimizador'])
    """

    def _estimar_varianza_aleatoria(self) -> float:
        """Estima A maximizando la log-verosimilitud REML.

        Guarda `convergio_reml` (éxito del optimizador) y `A_en_cota` (Â en una cota, R-41).

        Returns:
            float: Â, la varianza estimada de los efectos aleatorios.

        Uso:
            Paso interno de `ajustar()`; se obtiene Â con `modelo.A_hat` después de ajustar.
        """
        cotas = _cotas_log_A(self.Y)
        res = minimize_scalar(
            _neg_reml_loglik,
            bounds=cotas,
            method="bounded",
            args=(self.Y, self.X, self.Di),
        )
        self.convergio_reml = bool(res.success)
        self.A_en_cota = en_cota(float(res.x), cotas)
        return float(np.exp(res.x))

    def _estimar_beta_gls(self, A: float) -> tuple:
        """Estima beta por GLS e infiere su matriz de covarianza y p-valores.

        Args:
            A (float): Varianza de efectos aleatorios estimada por REML.

        Returns:
            tuple: (beta, se_beta, t_stats, p_vals, cov_beta).

        Uso:
            Paso interno de `ajustar()`; los resultados quedan en `modelo.beta`, `modelo.p_vals`, etc.
        """
        beta, _, XtViX = _gls_beta(A, self.Y, self.X, self.Di)
        cov_beta = np.linalg.inv(XtViX)
        se_beta = np.sqrt(np.diag(cov_beta))
        t_stats = beta / se_beta
        p_vals = 2 * (1 - stats.norm.cdf(np.abs(t_stats)))
        return beta, se_beta, t_stats, p_vals, cov_beta

    def _calcular_eblup(self, A: float, beta: np.ndarray) -> tuple:
        """Calcula los pesos de shrinkage y el predictor EBLUP.

        Args:
            A (float): Varianza de efectos aleatorios.
            beta (np.ndarray): Coeficientes GLS, shape (p,).

        Returns:
            tuple: (gamma_i, mu_hat, eblup), cada uno shape (n,).

        Uso:
            Paso interno de `ajustar()`; los resultados quedan en `modelo.gamma_i` y `modelo.eblup`.
        """
        gamma_i = A / (A + self.Di)
        mu_hat = self.X @ beta
        eblup = gamma_i * self.Y + (1 - gamma_i) * mu_hat
        return gamma_i, mu_hat, eblup

    def _calcular_mse_prasad_rao(
        self, A: float, gamma_i: np.ndarray, cov_beta: np.ndarray
    ) -> np.ndarray:
        """Estimador de MSE del EBLUP: g1(Â) + g2(Â) + 2·g3(Â) (Morales et al., p. 440).

        - ``g1 = A·D/(A+D) = γ·D``: variabilidad del efecto aleatorio que no se predice.
        - ``g2 = (D/(A+D))² · x'Cov(β̂)x``: incertidumbre por estimar β.
        - ``g3 = D²/(A+D)³ · avar(Â)``, con ``avar(Â) = 2/Σ(A+D)⁻²`` para REML: incertidumbre
          por estimar A (Datta y Lahiri, 2000).

        g3 entra dos veces porque g1(Â) es un estimador sesgado hacia abajo de g1(A), con sesgo
        aproximado −g3(A); sumar un g3 adicional corrige ese sesgo.

        Args:
            A (float): Varianza de efectos aleatorios estimada (Â).
            gamma_i (np.ndarray): Pesos de contracción γ_d = A/(A+D_d), shape (n,).
            cov_beta (np.ndarray): Covarianza de β̂, shape (p, p).

        Returns:
            np.ndarray: MSE estimado del EBLUP por dominio, shape (n,).

        Example:
            >>> modelo._calcular_mse_prasad_rao(modelo.A_hat, modelo.gamma_i, modelo.cov_beta)  # doctest: +SKIP
        """
        varianza = self.Di + A
        g1 = gamma_i * self.Di
        g2 = (1 - gamma_i) ** 2 * np.einsum("ij,jk,ik->i", self.X, cov_beta, self.X)
        var_A = 2.0 / np.sum(varianza**-2.0)
        g3 = self.Di**2 / varianza**3 * var_A
        return g1 + g2 + 2 * g3

    def _diagnosticos_residuos(self, A: float, mu_hat: np.ndarray) -> tuple:
        """Residuos estandarizados, test de normalidad y R² del predictor sintético.

        Args:
            A (float): Varianza de efectos aleatorios.
            mu_hat (np.ndarray): Predictor sintético, shape (n,).

        Returns:
            tuple: (residuals, sw_stat, sw_pval, r2).

        Uso:
            Paso interno de `ajustar()`; los resultados quedan en `modelo.residuals` y `modelo.r2`.
        """
        residuals = (self.Y - mu_hat) / np.sqrt(self.Di + A)
        sw_stat, sw_pval = stats.shapiro(residuals)
        r2 = 1 - np.sum((self.Y - mu_hat) ** 2) / np.sum((self.Y - self.Y.mean()) ** 2)
        return residuals, sw_stat, sw_pval, r2

    def _calcular_aic(self) -> float:
        """AIC vía la log-verosimilitud ML (A se reoptimiza con ML, no REML).

        Guarda `convergio_ml` (éxito del optimizador de ML, R-41).

        Returns:
            float: AIC del modelo ajustado.

        Uso:
            Paso interno de `ajustar()`; el valor queda en `modelo.aic`.
        """
        res_ml = minimize_scalar(
            _neg_ml_loglik,
            bounds=_cotas_log_A(self.Y),
            method="bounded",
            args=(self.Y, self.X, self.Di),
        )
        self.convergio_ml = bool(res_ml.success)
        log_lik_ml = -res_ml.fun
        return -2 * log_lik_ml + 2 * (self.p + 1)  # p coefs + 1 para A

    # --- Complemento AICc (G7-B16): corrección de muestra pequeña del AIC ------------------
    def _calcular_aicc(self) -> float:
        """AICc = AIC + 2k(k+1)/(n−k−1), con k = p + 1 parámetros (p coeficientes y Â).

        Con n = 23 dominios y hasta 5 parámetros la corrección no es despreciable; el AICc
        se reporta como complemento del AIC y NO sustituye la regla de selección (ΔAIC ≤ 2
        con parsimonia), solo comprueba si la lectura de «soporte similar» se mantiene.

        Limitaciones: es una convención externa al libro de referencia y, en Fay-Herriot,
        una aproximación, porque la fórmula de corrección se deduce para regresión con
        errores iid y aquí las varianzas de muestreo D_i son heterogéneas. Criterios de
        información propios del modelo: Marhuenda, Morales y Pardo (2014) y Lombardía et al.
        (2017), citados en Morales et al. (2021, págs. 420 y 459).

        Returns:
            float: AICc del modelo ajustado; `np.nan` si n − k − 1 ≤ 0 (la corrección no
                está definida).

        Example:
            >>> modelo.ajustar()  # doctest: +SKIP
            >>> modelo.aicc - modelo.aic  # penalización adicional por muestra pequeña  # doctest: +SKIP
        """
        k = self.p + 1
        if self.n - k - 1 <= 0:
            return float("nan")
        return float(self.aic + 2 * k * (k + 1) / (self.n - k - 1))

    def avisos_ajuste(self) -> list:
        """Problemas de convergencia del ajuste (R-41); lista vacía si no hay ninguno.

        Returns:
            list[str]: Textos de aviso: optimizador REML o ML sin convergencia y Â en una cota.

        Raises:
            RuntimeError: Si se llama antes de `ajustar()`.

        Example:
            >>> modelo.avisos_ajuste()  # doctest: +SKIP
            []
        """
        if not hasattr(self, "convergio_ml"):
            raise RuntimeError("Llama a ajustar() antes de avisos_ajuste().")
        avisos = []
        if not self.convergio_reml:
            avisos.append("REML no convergió")
        if not self.convergio_ml:
            avisos.append("ML (AIC) no convergió")
        if self.A_en_cota:
            avisos.append("Â en la cota del optimizador")
        return avisos

    def ajustar(self) -> None:
        """Ajusta el modelo Fay-Herriot clásico completo.

        Orquesta la estimación de A por REML, beta por GLS, el predictor
        EBLUP, su MSE de Prasad-Rao, los diagnósticos de residuos y el
        AIC. Puebla todos los atributos del contrato documentado en
        `ModeloAreaPequena` y las banderas de convergencia (R-41).

        Returns:
            None: Los resultados quedan como atributos de la instancia.

        Example:
            >>> modelo = FayHerriotClasico(["IICA_CONFLICTO"], df, "TASA", "SE")  # doctest: +SKIP
            >>> modelo.ajustar()  # doctest: +SKIP

        Casos de uso:
            Especificaciones candidatas y reajustes del notebook del modelo, la validación
            predictiva y los escenarios de varianza.
        """
        self.A_hat = self._estimar_varianza_aleatoria()
        self.beta_hat, self.se_beta, self.t_stats, self.p_vals, self.cov_beta = (
            self._estimar_beta_gls(self.A_hat)
        )
        self.gamma_i, self.mu_hat, self.eblup = self._calcular_eblup(
            self.A_hat, self.beta_hat
        )
        self.mse = self._calcular_mse_prasad_rao(
            self.A_hat, self.gamma_i, self.cov_beta
        )
        self.rmse = np.sqrt(self.mse)
        self.cv = 100 * self.rmse / np.abs(self.eblup)
        self.residuals, self.sw_stat, self.sw_pval, self.r2 = (
            self._diagnosticos_residuos(self.A_hat, self.mu_hat)
        )
        self.aic = self._calcular_aic()
        # G7-B16: AICc como complemento del AIC (requiere self.aic, ya calculado arriba).
        self.aicc = self._calcular_aicc()
