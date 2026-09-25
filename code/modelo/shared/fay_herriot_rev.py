"""Modelo Fay-Herriot clásico — versión revisada con el MSE de Prasad-Rao corregido.

`shared/fay_herriot.py` no se modifica (lo usa el flujo original). Allí el término g3 del MSE
se calcula como ``D²/(D+A)² · avar(Â)``; la expresión correcta para los estimadores ML y REML
(Datta y Lahiri, 2000; Morales et al., 2021, p. 440) es

    g3(A) = D² / (D + A)³ · avar(Â),      avar(Â) = 2 / Σ_d (A + D_d)⁻²

La versión original omite un factor ``1/(D+A)``: sus unidades son %⁴ en lugar de %², y con la
tasa en puntos porcentuales (``D + A > 1``) sobrestima g3 en un factor ``D + A``. Esta clase
hereda todo lo demás (REML, GLS, EBLUP, AIC por ML, residuos) y solo sustituye el MSE.
"""

import numpy as np

from shared.fay_herriot import FayHerriotClasico


class FayHerriotClasicoRev(FayHerriotClasico):
    """Fay-Herriot clásico con el estimador de MSE de Prasad-Rao de Datta y Lahiri (REML).

    Idéntico a `FayHerriotClasico` salvo por `_calcular_mse_prasad_rao`, que usa el término
    g3 del libro de referencia. Todos los atributos poblados por `ajustar()` son los mismos.

    Args:
        covars (list[str]): Covariables del modelo (sin intercepto).
        df (pd.DataFrame): Una fila por dominio con `covars`, `y_col` y `se_col`.
        y_col (str): Columna de la estimación directa.
        se_col (str): Columna del error estándar de la estimación directa.

    Raises:
        ValueError: Si alguna columna requerida no existe en `df`.

    Example:
        >>> modelo = FayHerriotClasicoRev(["COB_NET_SEC"], df, "TASA_DESEMPLEO_PCT",
        ...                               "SE_BOOTSTRAP_PCT")
        >>> modelo.ajustar()
        >>> modelo.mse  # g1 + g2 + 2·g3 con g3 de la p. 440
    """

    def _calcular_mse_prasad_rao(
        self, A: float, gamma_i: np.ndarray, cov_beta: np.ndarray
    ) -> np.ndarray:
        """Estimador de MSE del EBLUP: g1(Â) + g2(Â) + 2·g3(Â) (Morales et al., p. 440).

        - ``g1 = A·D/(A+D) = γ·D``: variabilidad del efecto aleatorio que no se predice.
        - ``g2 = (D/(A+D))² · x'Cov(β̂)x``: incertidumbre por estimar β.
        - ``g3 = D²/(A+D)³ · avar(Â)``, con ``avar(Â) = 2/Σ(A+D)⁻²`` para REML: incertidumbre
          por estimar A.

        g3 entra dos veces porque g1(Â) es un estimador sesgado hacia abajo de g1(A), con sesgo
        aproximado −g3(A); sumar un g3 adicional corrige ese sesgo (Datta y Lahiri, 2000).

        Args:
            A (float): Varianza de efectos aleatorios estimada (Â).
            gamma_i (np.ndarray): Pesos de contracción γ_d = A/(A+D_d), shape (n,).
            cov_beta (np.ndarray): Covarianza de β̂, shape (p, p).

        Returns:
            np.ndarray: MSE estimado del EBLUP por dominio, shape (n,).

        Example:
            >>> modelo._calcular_mse_prasad_rao(modelo.A_hat, modelo.gamma_i, modelo.cov_beta)
        """
        varianza = self.Di + A
        g1 = gamma_i * self.Di
        g2 = (1 - gamma_i) ** 2 * np.einsum("ij,jk,ik->i", self.X, cov_beta, self.X)
        var_A = 2.0 / np.sum(varianza**-2.0)
        g3 = self.Di**2 / varianza**3 * var_A
        return g1 + g2 + 2 * g3
