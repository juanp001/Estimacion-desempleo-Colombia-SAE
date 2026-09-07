import numpy as np
from scipy import stats
from scipy.optimize import minimize_scalar

from shared.modelo_area_pequena import ModeloAreaPequena


def _vi_xtvi_xtvix(A: float, X: np.ndarray, Di: np.ndarray) -> tuple:
    """Componentes comunes de GLS bajo V = diag(Di + A): V⁻¹, X'V⁻¹ y X'V⁻¹X.

    Args:
        A (float): Varianza de los efectos aleatorios (debe ser >= 0).
        X (np.ndarray): Matriz de diseño, shape (n, p).
        Di (np.ndarray): Varianza directa por dominio, shape (n,).

    Returns:
        tuple: (Vi, XtVi, XtViX) — Vi es la diagonal de V⁻¹ (shape (n,)),
            XtVi tiene shape (p, n) y XtViX tiene shape (p, p).
    """
    Vi    = 1.0 / (Di + A)
    XtVi  = X.T * Vi
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
    """
    Vi, XtVi, XtViX = _vi_xtvi_xtvix(A, X, Di)
    beta = np.linalg.solve(XtViX, XtVi @ Y)
    return beta, XtVi, XtViX


def _neg_reml_loglik(log_A: float, Y: np.ndarray, X: np.ndarray, Di: np.ndarray) -> float:
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
    """
    A = np.exp(log_A)
    Vi, Vi_X, Q = _vi_xtvi_xtvix(A, X, Di)
    try:
        Qinv = np.linalg.inv(Q)
    except np.linalg.LinAlgError:
        return 1e10
    PY        = Vi * Y - (Vi_X.T @ (Qinv @ (Vi_X @ Y)))
    log_det_V = np.sum(np.log(Di + A))
    log_det_Q = np.linalg.slogdet(Q)[1]
    reml_ll   = -0.5 * (log_det_V + log_det_Q + Y @ PY)
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
    """
    A = np.exp(log_A)
    Vi, XtVi, XtViX = _vi_xtvi_xtvix(A, X, Di)
    try:
        beta = np.linalg.solve(XtViX, XtVi @ Y)
    except np.linalg.LinAlgError:
        return 1e10
    n         = len(Y)
    resid     = Y - X @ beta
    log_det_V = np.sum(np.log(Di + A))
    quadratic = np.sum(Vi * resid ** 2)
    ml_ll     = -0.5 * (n * np.log(2 * np.pi) + log_det_V + quadratic)
    return -ml_ll


class FayHerriotClasico(ModeloAreaPequena):
    """Modelo Fay-Herriot clásico (efectos aleatorios independientes por dominio).

    Asume V = diag(Di + A): cada dominio tiene un efecto aleatorio i.i.d.
    con varianza A común, independiente entre dominios. Es el modelo de
    áreas pequeñas más simple de la familia Fay-Herriot; las variantes
    espacial (matriz de proximidad) y temporal (AR(1) por dominio) viven
    en módulos separados que heredan de `ModeloAreaPequena` pero con su
    propia estructura de V.

    Args / Raises: ver `ModeloAreaPequena`.

    Example:
        >>> modelo = FayHerriotClasico(["IND_PROD", "IND_POB_MULT"], df,
        ...                            "TASA_DESEMPLEO_PCT", "SE_BOOTSTRAP_PCT")
        >>> modelo.ajustar()
        >>> modelo.aic, modelo.r2
    """

    def _estimar_varianza_aleatoria(self) -> float:
        """Estima A maximizando la log-verosimilitud REML.

        Returns:
            float: Â, la varianza estimada de los efectos aleatorios.
        """
        res = minimize_scalar(
            _neg_reml_loglik,
            bounds=(np.log(1e-6), np.log(np.var(self.Y) * 10)),
            method="bounded",
            args=(self.Y, self.X, self.Di),
        )
        return float(np.exp(res.x))

    def _estimar_beta_gls(self, A: float) -> tuple:
        """Estima beta por GLS e infiere su matriz de covarianza y p-valores.

        Args:
            A (float): Varianza de efectos aleatorios estimada por REML.

        Returns:
            tuple: (beta, se_beta, t_stats, p_vals, cov_beta).
        """
        beta, _, XtViX = _gls_beta(A, self.Y, self.X, self.Di)
        cov_beta = np.linalg.inv(XtViX)
        se_beta  = np.sqrt(np.diag(cov_beta))
        t_stats  = beta / se_beta
        p_vals   = 2 * (1 - stats.norm.cdf(np.abs(t_stats)))
        return beta, se_beta, t_stats, p_vals, cov_beta

    def _calcular_eblup(self, A: float, beta: np.ndarray) -> tuple:
        """Calcula los pesos de shrinkage y el predictor EBLUP.

        Args:
            A (float): Varianza de efectos aleatorios.
            beta (np.ndarray): Coeficientes GLS, shape (p,).

        Returns:
            tuple: (gamma_i, mu_hat, eblup), cada uno shape (n,).
        """
        gamma_i = A / (A + self.Di)
        mu_hat  = self.X @ beta
        eblup   = gamma_i * self.Y + (1 - gamma_i) * mu_hat
        return gamma_i, mu_hat, eblup

    def _calcular_mse_prasad_rao(self, A: float, gamma_i: np.ndarray, cov_beta: np.ndarray) -> np.ndarray:
        """MSE de Prasad-Rao de primer orden para el EBLUP.

        g3i se multiplica por 2 porque la aproximación de primer orden de
        Prasad-Rao corrige el sesgo introducido al estimar A (en vez de
        conocerlo), y esa corrección entra al MSE duplicada.

        Args:
            A (float): Varianza de efectos aleatorios.
            gamma_i (np.ndarray): Pesos de shrinkage, shape (n,).
            cov_beta (np.ndarray): Covarianza de beta, shape (p, p).

        Returns:
            np.ndarray: MSE estimado por dominio, shape (n,).
        """
        g1i = gamma_i * self.Di
        g2i = np.array([(1 - gamma_i[i]) ** 2 * (self.X[i] @ cov_beta @ self.X[i])
                         for i in range(self.n)])
        sum_vi2 = np.sum(1.0 / (self.Di + A) ** 2)
        var_A   = 2.0 / sum_vi2 if sum_vi2 > 0 else 0.0
        g3i     = (self.Di / (self.Di + A)) ** 2 * var_A
        return g1i + g2i + 2 * g3i

    def _diagnosticos_residuos(self, A: float, mu_hat: np.ndarray) -> tuple:
        """Residuos estandarizados, test de normalidad y R² del predictor sintético.

        Args:
            A (float): Varianza de efectos aleatorios.
            mu_hat (np.ndarray): Predictor sintético, shape (n,).

        Returns:
            tuple: (residuals, sw_stat, sw_pval, r2).
        """
        residuals        = (self.Y - mu_hat) / np.sqrt(self.Di + A)
        sw_stat, sw_pval  = stats.shapiro(residuals)
        r2 = 1 - np.sum((self.Y - mu_hat) ** 2) / np.sum((self.Y - self.Y.mean()) ** 2)
        return residuals, sw_stat, sw_pval, r2

    def _calcular_aic(self) -> float:
        """AIC vía la log-verosimilitud ML (A se reoptimiza con ML, no REML).

        Returns:
            float: AIC del modelo ajustado.
        """
        res_ml = minimize_scalar(
            _neg_ml_loglik,
            bounds=(np.log(1e-6), np.log(np.var(self.Y) * 10)),
            method="bounded",
            args=(self.Y, self.X, self.Di),
        )
        log_lik_ml = -res_ml.fun
        return -2 * log_lik_ml + 2 * (self.p + 1)           # p coefs + 1 para A

    def ajustar(self) -> None:
        """Ajusta el modelo Fay-Herriot clásico completo.

        Orquesta la estimación de A por REML, beta por GLS, el predictor
        EBLUP, su MSE de Prasad-Rao, los diagnósticos de residuos y el
        AIC. Puebla todos los atributos del contrato documentado en
        `ModeloAreaPequena`.
        """
        self.A_hat = self._estimar_varianza_aleatoria()
        self.beta_hat, self.se_beta, self.t_stats, self.p_vals, self.cov_beta = (
            self._estimar_beta_gls(self.A_hat)
        )
        self.gamma_i, self.mu_hat, self.eblup = self._calcular_eblup(self.A_hat, self.beta_hat)
        self.mse  = self._calcular_mse_prasad_rao(self.A_hat, self.gamma_i, self.cov_beta)
        self.rmse = np.sqrt(self.mse)
        self.cv   = 100 * self.rmse / np.abs(self.eblup)
        self.residuals, self.sw_stat, self.sw_pval, self.r2 = (
            self._diagnosticos_residuos(self.A_hat, self.mu_hat)
        )
        self.aic = self._calcular_aic()
