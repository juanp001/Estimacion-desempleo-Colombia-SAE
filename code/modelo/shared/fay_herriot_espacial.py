"""Modelo Fay-Herriot espacial (SEBLUP): efectos aleatorios con autocorrelación espacial SAR.

Extiende `FayHerriotClasico` cambiando un único supuesto: los efectos aleatorios de los dominios
ya no son independientes sino que siguen un proceso autorregresivo simultáneo de orden 1
(Morales et al., 2021, §18.2, pp. 490-494; Singh et al., 2005; Petrucci y Salvati, 2006;
Pratesi y Salvati, 2008):

    y = Xβ + u + e,    u = ρWu + v,    v ~ N(0, σ²_u·I),    e ~ N(0, diag(D_d))

de donde Cov(u) = G(σ²_u, ρ) = σ²_u·[(I − ρW)'(I − ρW)]⁻¹ y Cov(y) = V = G + diag(D). Con ρ = 0
se recupera el Fay-Herriot clásico. W es una matriz de proximidad estandarizada por filas, de
modo que ρ ∈ (−1, 1).

Dos formas de definir W, según el insumo (parámetro `estructura`):

- ``"muestra"`` (Petrucci-Salvati): W se define solo entre los dominios con encuesta. Los
  municipios sin encuesta solo reciben el predictor sintético Xβ̂.
- ``"completa"`` (Saei y Chambers, 2005; Benedetti et al., 2024, pp. 146-149): el SAR se impone
  sobre *todas* las unidades, con y sin encuesta, y la verosimilitud se evalúa solo sobre el
  bloque de las unidades con encuesta (verosimilitud marginal). Así un municipio sin encuesta
  recibe, además de Xβ̂, un efecto espacial predicho a partir de los dominios cercanos:
  û_r = G_rs·V⁻¹·(y − Xβ̂).

Las unidades se ordenan siempre igual: primero las n filas de `df` (con encuesta) y luego las
filas de `df_objetivo` (sin encuesta). La matriz de proximidad sigue ese orden.

Estimación: (σ²_u, ρ) por REML numérico (L-BFGS-B con varios puntos de partida; con n tan pequeño
la superficie puede ser plana en ρ, por eso también se ofrece `perfil_rho`); β por GLS; AIC con la
verosimilitud ML y p + 2 parámetros. MSE: bootstrap paramétrico de Morales et al. (§18.2.3,
p. 494), que re-estima (σ²_u, ρ) en cada réplica y por tanto incorpora su incertidumbre.
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize, minimize_scalar

from shared.fay_herriot import FayHerriotClasico
from shared.matriz_proximidad import estandarizar_filas
from shared.modelo_area_pequena import ModeloAreaPequena

_PENALIZACION = 1e10  # valor devuelto al optimizador cuando V no es definida positiva


def covarianza_sar(W: np.ndarray, A: float, rho: float) -> np.ndarray:
    """Covarianza de los efectos aleatorios SAR: G = A·[(I − ρW)'(I − ρW)]⁻¹.

    Se calcula como A·M⁻¹·M⁻ᵀ con M = I − ρW, equivalente a la expresión anterior pero sin
    formar M'M.

    Args:
        W (np.ndarray): Matriz de proximidad estandarizada por filas, shape (m, m).
        A (float): Varianza σ²_u de las innovaciones v (> 0).
        rho (float): Parámetro de autocorrelación espacial, en (−1, 1).

    Returns:
        np.ndarray: Matriz simétrica definida positiva (m, m).

    Raises:
        numpy.linalg.LinAlgError: Si I − ρW es singular (|ρ| demasiado cercano a 1).

    Example:
        >>> G = covarianza_sar(W, A=4.0, rho=0.5)
    """
    M_inv = np.linalg.inv(np.eye(W.shape[0]) - rho * W)
    return A * (M_inv @ M_inv.T)


class FayHerriotEspacial(ModeloAreaPequena):
    """Fay-Herriot con efectos aleatorios SAR (SEBLUP), con predicción para dominios sin encuesta.

    Args:
        covars (list[str]): Covariables del modelo (sin intercepto).
        df (pd.DataFrame): Dominios con encuesta, una fila por dominio, con `covars`, `y_col` y
            `se_col`.
        y_col (str): Columna con la estimación directa.
        se_col (str): Columna con el error estándar de la estimación directa.
        proximidad (np.ndarray): Proximidad cruda (sin estandarizar), simétrica, con diagonal nula,
            shape (n + r, n + r), en el orden [dominios con encuesta, dominios objetivo]. Con
            `estructura="muestra"` solo se usa el bloque n × n.
        df_objetivo (pd.DataFrame | None): Dominios sin encuesta (r filas) con `covars`. Requerido
            para predecir; con `estructura="completa"` determina el tamaño de W.
        estructura (str): ``"completa"`` o ``"muestra"`` (ver docstring del módulo).
        rho_limite (float): Cota |ρ| ≤ rho_limite del optimizador (< 1 para que I − ρW sea
            invertible).
        n_bootstrap (int): Réplicas del bootstrap paramétrico del MSE; 0 usa la aproximación de
            primer orden g1 + g2 (ignora la incertidumbre de σ²_u y ρ, por lo que subestima).
        semilla (int): Semilla del bootstrap.

    Attributes:
        Tras `ajustar()`: los del contrato de `ModeloAreaPequena` (sin `gamma_i`, que en el caso
        espacial no es un escalar por dominio) más `rho_hat`, `theta_hat`, `loglik_ml`,
        `mse_aprox`, `pred_objetivo`, `sintetico_objetivo`, `mse_objetivo`,
        `mse_sintetico_objetivo`, `n_bootstrap_validas` y `perfil_rho_` (si se llama).

    Raises:
        ValueError: Si `proximidad` no tiene el tamaño esperado, `estructura` no es válida o
            faltan covariables en `df_objetivo`.

    Example:
        >>> m = FayHerriotEspacial(["VA_PCT_PRIM"], df, "TASA", "SE", P, df_obj, n_bootstrap=500)
        >>> m.ajustar()
        >>> m.rho_hat, m.aic
    """

    def __init__(
        self,
        covars,
        df,
        y_col,
        se_col,
        proximidad,
        df_objetivo=None,
        estructura="completa",
        rho_limite=0.99,
        n_bootstrap=0,
        semilla=42,
    ):
        """Construye X, D, W estandarizada y la matriz de diseño de los dominios objetivo.

        Args:
            covars (list[str]): Covariables (sin intercepto).
            df (pd.DataFrame): Dominios con encuesta.
            y_col (str): Columna de la estimación directa.
            se_col (str): Columna del error estándar directo.
            proximidad (np.ndarray): Proximidad cruda, shape (n + r, n + r).
            df_objetivo (pd.DataFrame | None): Dominios sin encuesta.
            estructura (str): ``"completa"`` o ``"muestra"``.
            rho_limite (float): Cota del optimizador para |ρ|.
            n_bootstrap (int): Réplicas del bootstrap del MSE (0 = aproximación g1 + g2).
            semilla (int): Semilla del bootstrap.

        Raises:
            ValueError: Si la estructura no es válida, W no tiene el tamaño esperado o faltan
                covariables en `df_objetivo`.
        """
        super().__init__(covars, df, y_col, se_col)
        if estructura not in ("completa", "muestra"):
            raise ValueError("`estructura` debe ser 'completa' o 'muestra'.")
        r = 0 if df_objetivo is None else len(df_objetivo)
        if proximidad.shape != (self.n + r, self.n + r):
            raise ValueError(
                f"`proximidad` debe ser ({self.n + r}, {self.n + r}) = n + r; "
                f"se recibió {proximidad.shape}."
            )
        self.estructura = estructura
        self.rho_limite = rho_limite
        self.n_bootstrap = n_bootstrap
        self.semilla = semilla
        self.r = r
        self.X_obj = None
        if r:
            faltantes = set(covars) - set(df_objetivo.columns)
            if faltantes:
                raise ValueError(
                    f"Faltan covariables en df_objetivo: {sorted(faltantes)}"
                )
            self.df_objetivo = df_objetivo
            self.X_obj = np.column_stack(
                [np.ones(r)] + [df_objetivo[c].values for c in covars]
            )
        if estructura == "completa":
            self.W = estandarizar_filas(proximidad)
            self.X_total = self.X if not r else np.vstack([self.X, self.X_obj])
        else:
            self.W = estandarizar_filas(proximidad[: self.n, : self.n])
            self.X_total = self.X
        self.m = self.W.shape[0]

    # ── Verosimilitud y estimación de (σ²_u, ρ) ──────────────────────────────
    def _G(self, theta: np.ndarray) -> np.ndarray:
        """Covarianza SAR de todas las unidades para θ = (log σ²_u, ρ).

        Args:
            theta (np.ndarray): [log σ²_u, ρ], shape (2,).

        Returns:
            np.ndarray: G, shape (m, m).
        """
        return covarianza_sar(self.W, float(np.exp(theta[0])), float(theta[1]))

    def _log_verosimilitud(self, theta, Y, reml: bool, con_constante: bool) -> float:
        """Log-verosimilitud (ML o REML) de los dominios con encuesta, perfilando β por GLS.

        Con la estructura completa, V = G[:n, :n] + diag(D) es el bloque marginal de las unidades
        con encuesta (verosimilitud marginal de Benedetti et al., 2024, p. 147, ec. 18-19).

        Args:
            theta (np.ndarray): [log σ²_u, ρ].
            Y (np.ndarray): Estimaciones directas, shape (n,).
            reml (bool): True usa la verosimilitud restringida (resta ½·log|X'V⁻¹X|).
            con_constante (bool): True incluye −(n/2)·log(2π) (necesario para el AIC).

        Returns:
            float: Log-verosimilitud, o −1e10 si V no es definida positiva.
        """
        n = self.n
        try:
            V = self._G(theta)[:n, :n] + np.diag(self.Di)
            L = np.linalg.cholesky(V)
        except np.linalg.LinAlgError:
            return -_PENALIZACION
        Vi_X = np.linalg.solve(V, self.X)
        Q = self.X.T @ Vi_X
        beta = np.linalg.solve(Q, self.X.T @ np.linalg.solve(V, Y))
        resid = Y - self.X @ beta
        log_det_V = 2.0 * np.sum(np.log(np.diag(L)))
        ll = -0.5 * (log_det_V + resid @ np.linalg.solve(V, resid))
        if reml:
            ll -= 0.5 * np.linalg.slogdet(Q)[1]
        if con_constante:
            ll -= 0.5 * n * np.log(2 * np.pi)
        return float(ll)

    def _estimar_theta(self, Y, reml=True, inicios=None) -> tuple:
        """Maximiza la log-verosimilitud en (log σ²_u, ρ) con L-BFGS-B y varios inicios.

        Args:
            Y (np.ndarray): Estimaciones directas, shape (n,).
            reml (bool): REML (True) o ML (False).
            inicios (list[np.ndarray] | None): Puntos de partida. Por defecto ρ ∈ {0, 0.5, 0.9}
                con σ²_u = var(Y)/2.

        Returns:
            tuple: (theta, log_verosimilitud_sin_constante) del mejor inicio.
        """
        if inicios is None:
            logA0 = np.log(max(np.var(Y) / 2, 1e-3))
            inicios = [np.array([logA0, r0]) for r0 in (0.0, 0.5, 0.9)]
        limites = [
            (np.log(1e-6), np.log(max(np.var(Y) * 10, 1e-3))),
            (-self.rho_limite, self.rho_limite),
        ]
        mejor = None
        for x0 in inicios:
            res = minimize(
                lambda t: -self._log_verosimilitud(t, Y, reml, False),
                np.clip(x0, [l[0] for l in limites], [l[1] for l in limites]),
                method="L-BFGS-B",
                bounds=limites,
            )
            if mejor is None or res.fun < mejor.fun:
                mejor = res
        return mejor.x, float(-mejor.fun)

    def perfil_rho(self, rejilla: np.ndarray = None) -> pd.DataFrame:
        """Log-verosimilitud REML perfilada en ρ: máximo sobre σ²_u para cada ρ de la rejilla.

        Sirve para ver si ρ está identificado: una curva plana indica que los datos casi no
        informan sobre la autocorrelación espacial. Guarda el resultado en `perfil_rho_`.

        Args:
            rejilla (np.ndarray | None): Valores de ρ. Por defecto de −0.9 a 0.95 cada 0.05.

        Returns:
            pd.DataFrame: Columnas `rho`, `A_hat`, `loglik_reml`, `delta_vs_rho0` (diferencia con
                ρ = 0, que corresponde al Fay-Herriot clásico).

        Example:
            >>> modelo.perfil_rho().sort_values("loglik_reml").tail(3)
        """
        if rejilla is None:
            rejilla = np.round(np.arange(-0.9, 0.96, 0.05), 2)
        cota = (np.log(1e-6), np.log(max(np.var(self.Y) * 10, 1e-3)))
        filas = []
        for rho in rejilla:
            res = minimize_scalar(
                lambda la: -self._log_verosimilitud(
                    np.array([la, rho]), self.Y, True, False
                ),
                bounds=cota,
                method="bounded",
            )
            filas.append((float(rho), float(np.exp(res.x)), float(-res.fun)))
        perfil = pd.DataFrame(filas, columns=["rho", "A_hat", "loglik_reml"])
        ref = perfil.loc[(perfil["rho"] - 0.0).abs().idxmin(), "loglik_reml"]
        perfil["delta_vs_rho0"] = perfil["loglik_reml"] - ref
        self.perfil_rho_ = perfil
        return perfil

    # ── Predicción ───────────────────────────────────────────────────────────
    def _ajuste_gls(self, Y, theta) -> dict:
        """GLS y predictor lineal para un vector de datos Y dado θ.

        Args:
            Y (np.ndarray): Estimaciones directas, shape (n,).
            theta (np.ndarray): [log σ²_u, ρ].

        Returns:
            dict: `beta`, `cov_beta`, `V`, `Vi`, `G`, `resid` (Y − Xβ̂) y `pred` (shape (m,)):
                Xβ̂ + G[:, :n]·V⁻¹·(Y − Xβ̂), que es el EBLUP en las n primeras unidades y la
                predicción con efecto espacial en las restantes.
        """
        n = self.n
        G = self._G(theta)
        V = G[:n, :n] + np.diag(self.Di)
        Vi = np.linalg.inv(V)
        cov_beta = np.linalg.inv(self.X.T @ Vi @ self.X)
        beta = cov_beta @ (self.X.T @ Vi @ Y)
        resid = Y - self.X @ beta
        pred = self.X_total @ beta + G[:, :n] @ (Vi @ resid)
        return {
            "beta": beta,
            "cov_beta": cov_beta,
            "V": V,
            "Vi": Vi,
            "G": G,
            "resid": resid,
            "pred": pred,
        }

    # ── Bootstrap paramétrico del MSE ────────────────────────────────────────
    def _bootstrap_mse(self) -> tuple:
        """Bootstrap paramétrico del MSE (Morales et al., §18.2.3, p. 494).

        En cada réplica: (1) simula u* ~ N(0, G(θ̂)) para todas las unidades y e* ~ N(0, D);
        (2) construye y* = Xβ̂ + u*_s + e*; (3) re-estima (σ²_u, ρ) por REML desde θ̂ y recalcula
        el predictor; (4) acumula el error cuadrado frente a la verdad simulada
        μ* = Xβ̂ + u*. El MSE es el promedio de esos errores. Con estructura completa también
        se obtiene el MSE de las unidades objetivo (con efecto espacial y sintético).

        Returns:
            tuple: (mse_pred, mse_sintetico_obj, n_validas). `mse_pred` tiene shape (m,);
                `mse_sintetico_obj` shape (r,) (o None si no hay objetivos o la estructura es
                "muestra"); `n_validas` es el número de réplicas que convergieron.
        """
        rng = np.random.default_rng(self.semilla)
        n, m = self.n, self.m
        G = self._G(self.theta_hat)
        L = np.linalg.cholesky(G + 1e-10 * np.eye(m))
        media = self.X_total @ self.beta_hat
        err = np.zeros(m)
        err_sint = np.zeros(max(m - n, 0))
        validas = 0
        for _ in range(self.n_bootstrap):
            u = L @ rng.standard_normal(m)
            mu = media + u
            Y_b = mu[:n] + np.sqrt(self.Di) * rng.standard_normal(n)
            try:
                theta_b, _ = self._estimar_theta(Y_b, True, [self.theta_hat])
                aj = self._ajuste_gls(Y_b, theta_b)
            except np.linalg.LinAlgError:
                continue
            err += (aj["pred"] - mu) ** 2
            if m > n:
                err_sint += (self.X_total[n:] @ aj["beta"] - mu[n:]) ** 2
            validas += 1
        if validas == 0:
            raise RuntimeError("Ninguna réplica del bootstrap convergió.")
        return err / validas, (err_sint / validas if m > n else None), validas

    # ── Ajuste completo ──────────────────────────────────────────────────────
    def ajustar(self) -> None:
        """Ajusta el SEBLUP: (σ²_u, ρ) por REML, β por GLS, EBLUP, MSE, diagnósticos y AIC.

        Puebla el contrato de `ModeloAreaPequena` más los atributos espaciales descritos en el
        docstring de la clase. Si hay `df_objetivo` y la estructura es completa, calcula también
        la predicción de los dominios sin encuesta con efecto espacial.
        """
        n = self.n
        self.theta_hat, self.loglik_reml = self._estimar_theta(self.Y, reml=True)
        self.A_hat = float(np.exp(self.theta_hat[0]))
        self.rho_hat = float(self.theta_hat[1])

        aj = self._ajuste_gls(self.Y, self.theta_hat)
        self.beta_hat = aj["beta"]
        self.cov_beta = aj["cov_beta"]
        self.se_beta = np.sqrt(np.diag(self.cov_beta))
        self.t_stats = self.beta_hat / self.se_beta
        self.p_vals = 2 * (1 - stats.norm.cdf(np.abs(self.t_stats)))
        self.mu_hat = self.X @ self.beta_hat
        self.eblup = aj["pred"][:n]

        # MSE de primer orden: g1 = diag(G − G V⁻¹ G), g2 = incertidumbre de β̂.
        G_ss = aj["G"][:n, :n]
        A_mat = self.X - G_ss @ aj["Vi"] @ self.X
        g1 = np.diag(G_ss - G_ss @ aj["Vi"] @ G_ss)
        g2 = np.einsum("ij,jk,ik->i", A_mat, self.cov_beta, A_mat)
        self.mse_aprox = g1 + g2

        if self.r and self.estructura == "completa":
            self.pred_objetivo = aj["pred"][n:]
            self.sintetico_objetivo = self.X_obj @ self.beta_hat
        elif self.r:
            self.pred_objetivo = None
            self.sintetico_objetivo = self.X_obj @ self.beta_hat

        if self.n_bootstrap > 0:
            mse_pred, mse_sint, self.n_bootstrap_validas = self._bootstrap_mse()
            self.mse = mse_pred[:n]
            if self.r and self.estructura == "completa":
                self.mse_objetivo = mse_pred[n:]
                self.mse_sintetico_objetivo = mse_sint
        else:
            self.mse = self.mse_aprox
            self.n_bootstrap_validas = 0
        self.rmse = np.sqrt(self.mse)
        self.cv = 100 * self.rmse / np.abs(self.eblup)

        # Residuos estandarizados con la factorización de Cholesky de V (≈ N(0, 1)).
        L = np.linalg.cholesky(aj["V"])
        self.residuals = np.linalg.solve(L, aj["resid"])
        self.sw_stat, self.sw_pval = stats.shapiro(self.residuals)
        self.r2 = 1 - np.sum((self.Y - self.mu_hat) ** 2) / np.sum(
            (self.Y - self.Y.mean()) ** 2
        )

        # AIC con la verosimilitud ML: p coeficientes + σ²_u + ρ.
        theta_ml, ll_sin_cte = self._estimar_theta(self.Y, reml=False)
        self.theta_ml = theta_ml
        self.loglik_ml = self._log_verosimilitud(theta_ml, self.Y, False, True)
        self.aic = -2 * self.loglik_ml + 2 * (self.p + 2)


def reordenar_proximidad(P: np.ndarray, orden) -> np.ndarray:
    """Reordena filas y columnas de una matriz de proximidad según `orden`.

    Args:
        P (np.ndarray): Matriz cuadrada (m, m).
        orden (array-like): Permutación (o subconjunto) de posiciones.

    Returns:
        np.ndarray: P[orden][:, orden].

    Example:
        >>> reordenar_proximidad(P, [1, 0, 2])
    """
    orden = list(orden)
    return P[np.ix_(orden, orden)]


def validacion_dejar_uno_fuera(
    covars,
    df,
    y_col,
    se_col,
    proximidad,
    df_objetivo,
    estructura="completa",
) -> pd.DataFrame:
    """Validación dejar-un-dominio-fuera: ¿predice mejor el modelo espacial que el clásico?

    Es la prueba más cercana al uso real del modelo (predecir un municipio sin encuesta). Para
    cada dominio d con encuesta: se ajusta el modelo sin d (re-estimando todos los parámetros),
    se trata a d como un dominio sin encuesta y se predice con (a) el sintético clásico x_d'β̂,
    (b) el sintético del modelo espacial x_d'β̂_esp y (c) el predictor espacial con efecto
    û_d = G_dS·V⁻¹·(y − Xβ̂). El referente es la estimación directa y_d, que tiene ruido D_d, por
    lo que se reporta también el error corregido por ese ruido.

    Args:
        covars (list[str]): Covariables del modelo.
        df (pd.DataFrame): Dominios con encuesta.
        y_col (str): Columna de la estimación directa.
        se_col (str): Columna del error estándar directo.
        proximidad (np.ndarray): Proximidad cruda (n + r, n + r) en el orden [df, df_objetivo].
        df_objetivo (pd.DataFrame): Municipios objetivo reales (permanecen como unidades sin
            encuesta en el SAR, igual que en el ajuste final).
        estructura (str): ``"completa"`` o ``"muestra"``. Con ``"muestra"`` el predictor (c) no
            existe y se devuelve NaN.

    Returns:
        pd.DataFrame: Una fila por dominio con `y`, `D`, `pred_clasico`, `pred_sint_esp`,
            `pred_espacial`, `rho_hat` y `A_hat` del ajuste sin ese dominio.

    Example:
        >>> cv = validacion_dejar_uno_fuera(cov, df, "TASA", "SE", P, df_obj)
        >>> np.sqrt(((cv.y - cv.pred_clasico) ** 2).mean())
    """
    n = len(df)
    r = len(df_objetivo)
    filas = []
    for d in range(n):
        entrenamiento = [i for i in range(n) if i != d]
        df_tr = df.iloc[entrenamiento].reset_index(drop=True)
        df_obj_d = pd.concat([df.iloc[[d]], df_objetivo], ignore_index=True)
        orden = entrenamiento + [d] + list(range(n, n + r))
        P = reordenar_proximidad(proximidad, orden)

        clasico = FayHerriotClasico(covars, df_tr, y_col, se_col)
        clasico.ajustar()
        x_d = np.concatenate([[1.0], df.iloc[d][covars].values.astype(float)])

        esp = FayHerriotEspacial(
            covars, df_tr, y_col, se_col, P, df_obj_d, estructura=estructura
        )
        esp.ajustar()
        filas.append(
            {
                "indice": d,
                "y": float(df.iloc[d][y_col]),
                "D": float(df.iloc[d][se_col] ** 2),
                "pred_clasico": float(x_d @ clasico.beta_hat),
                "pred_sint_esp": float(esp.sintetico_objetivo[0]),
                "pred_espacial": (
                    float(esp.pred_objetivo[0])
                    if esp.pred_objetivo is not None
                    else np.nan
                ),
                "rho_hat": esp.rho_hat,
                "A_hat": esp.A_hat,
            }
        )
    return pd.DataFrame(filas)


def metricas_validacion(cv: pd.DataFrame) -> pd.DataFrame:
    """Resume la validación dejar-uno-fuera: RMSE, MAE y RMSE corregido por el ruido de y_d.

    El referente y_d es una estimación con varianza D_d, así que el error cuadrático observado
    sobrestima el verdadero en promedio D_d; el RMSE corregido resta ese ruido
    (sqrt(media(e² − D)), NaN si la media es negativa).

    Args:
        cv (pd.DataFrame): Salida de `validacion_dejar_uno_fuera`.

    Returns:
        pd.DataFrame: Una fila por predictor (`pred_clasico`, `pred_sint_esp`, `pred_espacial`)
            con `RMSE`, `MAE`, `RMSE_corregido` y `sesgo_medio`.

    Example:
        >>> metricas_validacion(cv)
    """
    filas = []
    for col in ["pred_clasico", "pred_sint_esp", "pred_espacial"]:
        e = cv[col] - cv["y"]
        if e.isna().all():
            continue
        corregido = float(np.mean(e**2 - cv["D"]))
        filas.append(
            {
                "predictor": col,
                "RMSE": float(np.sqrt(np.mean(e**2))),
                "MAE": float(np.mean(np.abs(e))),
                "RMSE_corregido": (
                    float(np.sqrt(corregido)) if corregido > 0 else np.nan
                ),
                "sesgo_medio": float(e.mean()),
            }
        )
    return pd.DataFrame(filas)
