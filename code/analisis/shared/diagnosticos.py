"""Diagnósticos que sustentan decisiones sobre las covariables candidatas.

A diferencia de `descriptivos.py`, cuyo propósito es comprender los datos, cada función de
este módulo produce evidencia destinada a una decisión concreta:

* `ic_fisher_pearson()` acota la incertidumbre de la correlación con la respuesta; un
  intervalo que contiene el cero indica que la evidencia no determina siquiera el signo.
  Desde G7-B8 es **descriptivo**: no decide.
* `fh_univariado()` ajusta, por covariable, el modelo Fay-Herriot univariado con la varianza
  de muestreo ψ_d de cada dominio (G7-B8). Su p-valor ajustado por Benjamini-Hochberg sobre
  todas las candidatas decide la elegibilidad (G7-B9); `estabilidad_bootstrap()` la
  acompaña como lectura descriptiva.
* `influencia_fh()` y `estabilidad_fh()` determinan, sobre ese mismo modelo, si la
  asociación depende de un único dominio.
* `forma_funcional()` y `figura_residuos_parciales()` examinan si la forma lineal es
  adecuada antes de fijar el predictor (G7-B13): curvatura, escala logarítmica y residuos
  parciales del conjunto elegido. Son diagnósticos; no transforman covariables.
* `vif_conjunto()` verifica que el conjunto finalmente elegido no presente
  multicolinealidad.

Por qué el Fay-Herriot univariado (G7-B8)
-----------------------------------------
La respuesta es una estimación directa con error heterocedástico, ``θ̂_d = θ_d + e_d`` con
``Var(e_d) = ψ_d``. Pearson, Spearman y la regresión por mínimos cuadrados ordinarios dan el
mismo peso a todos los dominios. El modelo univariado ``θ̂_d = β0 + β1·x_d + u_d + e_d``,
con ``Var(u_d) = A`` estimada por REML, pesa cada dominio por ``1/(A + ψ_d)``, que es la
estructura del modelo que después se ajusta. Así la decisión se alinea con el modelo y las
correlaciones quedan como descripción.

Todos son diagnósticos de estadística básica, elegidos porque su lectura es directa y se
sostiene con 23 dominios. El índice de Moran no se calcula aquí, sobre las covariables ni
sobre la respuesta: el proyecto sí admite el contraste, pero se aplica a los residuos del
benchmark y de las variantes espaciales en `modelo/fay_herriot_espacial.py`, donde informa
la decisión entre el Fay-Herriot clásico y el espacial. Tampoco se contrasta la normalidad
de las covariables, que el modelo no supone.
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize_scalar
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools import add_constant


def ic_fisher_pearson(x: np.ndarray, y: np.ndarray, alfa: float = 0.05) -> tuple:
    """Intervalo de confianza para el coeficiente de Pearson por transformación de Fisher.

    Con 23 dominios el error estándar de una correlación es grande y un coeficiente
    puntual comunica más certeza de la que hay. El intervalo de Fisher es analítico, no
    remuestrea y es el procedimiento estándar de los textos de estadística básica, de modo
    que su interpretación se sostiene sin explicaciones adicionales.

    Args:
        x (np.ndarray): Covariable.
        y (np.ndarray): Variable respuesta.
        alfa (float): Nivel de significancia; el intervalo es de ``1 - alfa``.

    Returns:
        tuple[float, float]: Extremos inferior y superior del intervalo.

    Raises:
        ValueError: Si hay menos de cuatro observaciones.

    Example:
        >>> ic_fisher_pearson(x, Y)
        (0.038, 0.723)
    """
    n = len(x)
    if n < 4:
        raise ValueError(
            "La transformación de Fisher requiere al menos cuatro observaciones."
        )
    r = float(np.corrcoef(x, y)[0, 1])
    z = np.arctanh(np.clip(r, -0.999999, 0.999999))
    error = stats.norm.ppf(1 - alfa / 2) / np.sqrt(n - 3)
    return float(np.tanh(z - error)), float(np.tanh(z + error))


def tabla_ic_correlacion(
    df: pd.DataFrame,
    columnas: list,
    y: np.ndarray,
    alias: dict = None,
    alfa: float = 0.05,
) -> pd.DataFrame:
    """Correlación de Pearson con la respuesta y su intervalo de Fisher, por covariable.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar.
        y (np.ndarray): Variable respuesta.
        alias (dict | None): Mapa columna → alias legible.
        alfa (float): Nivel de significancia del intervalo.

    Returns:
        pd.DataFrame: Una fila por covariable con `Pearson_r`, `IC_inf`, `IC_sup` y
            `IC_contiene_cero` (`"sí"`/`"no"`), ordenada por |r| descendente.

    Example:
        >>> tabla_ic_correlacion(df_cand, codigos, Y, alias)
    """
    alias = alias or {}
    filas = []
    for col in columnas:
        x = pd.to_numeric(df[col], errors="coerce").values
        inferior, superior = ic_fisher_pearson(x, y, alfa=alfa)
        r = float(np.corrcoef(x, y)[0, 1])
        filas.append(
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "Pearson_r": round(r, 3),
                "IC_inf": round(inferior, 3),
                "IC_sup": round(superior, 3),
                "IC_contiene_cero": "sí" if inferior <= 0 <= superior else "no",
            }
        )
    return pd.DataFrame(filas).sort_values("Pearson_r", key=abs, ascending=False)


def _ajuste_fh(x: np.ndarray, y: np.ndarray, psi: np.ndarray) -> tuple:
    """Fay-Herriot univariado: A por REML y (β0, β1) por mínimos cuadrados generalizados.

    Args:
        x (np.ndarray): Covariable, shape (n,).
        y (np.ndarray): Estimación directa, shape (n,).
        psi (np.ndarray): Varianza de muestreo de cada dominio, shape (n,).

    Returns:
        tuple: (A, beta, cov_beta). `beta` tiene shape (2,) y `cov_beta` shape (2, 2).
    """
    return _ajuste_fh_matriz(np.column_stack([np.ones_like(x), x]), y, psi)


def _ajuste_fh_matriz(X: np.ndarray, y: np.ndarray, psi: np.ndarray) -> tuple:
    """Fay-Herriot con matriz de diseño `X`: A por REML y β por mínimos cuadrados generalizados.

    Es la misma formulación de `modelo/shared/fay_herriot.FayHerriotClasico` (log-verosimilitud
    REML optimizada en escala logarítmica en ``[1e-6, 10·Var(y)]``, β̂ = (X'V⁻¹X)⁻¹X'V⁻¹y con
    ``V = diag(A + ψ_d)``), reescrita aquí para que el análisis no dependa del paquete del
    modelo. Con los datos del proyecto ambas coinciden: β̂ hasta 1e-11 y Â hasta 5e-5,
    la tolerancia del optimizador acotado.

    Args:
        X (np.ndarray): Matriz de diseño con el intercepto, shape (n, p).
        y (np.ndarray): Estimación directa, shape (n,).
        psi (np.ndarray): Varianza de muestreo de cada dominio, shape (n,).

    Returns:
        tuple: (A, beta, cov_beta). `beta` tiene shape (p,) y `cov_beta` shape (p, p).
    """

    def menos_reml(log_a):
        vi = 1.0 / (psi + np.exp(log_a))
        xtvi = X.T * vi
        q = xtvi @ X
        py = vi * y - xtvi.T @ np.linalg.solve(q, xtvi @ y)
        return 0.5 * (np.sum(np.log(1.0 / vi)) + np.linalg.slogdet(q)[1] + y @ py)

    res = minimize_scalar(
        menos_reml, bounds=(np.log(1e-6), np.log(np.var(y) * 10)), method="bounded"
    )
    a = float(np.exp(res.x))
    xtvi = X.T / (psi + a)
    cov_beta = np.linalg.inv(xtvi @ X)
    return a, cov_beta @ (xtvi @ y), cov_beta


def _loglik_ml(X: np.ndarray, y: np.ndarray, psi: np.ndarray) -> float:
    """Log-verosimilitud ML maximizada del Fay-Herriot con matriz de diseño `X`.

    Es la verosimilitud con la que el notebook del modelo calcula el AIC (A reoptimizado por
    ML, no por REML), de modo que dos especificaciones con distinta X son comparables.

    Args:
        X (np.ndarray): Matriz de diseño con el intercepto, shape (n, p).
        y (np.ndarray): Estimación directa, shape (n,).
        psi (np.ndarray): Varianza de muestreo de cada dominio, shape (n,).

    Returns:
        float: Log-verosimilitud ML en su máximo.
    """

    def menos_ml(log_a):
        v = psi + np.exp(log_a)
        xtvi = X.T / v
        residuo = y - X @ np.linalg.solve(xtvi @ X, xtvi @ y)
        return 0.5 * (
            len(y) * np.log(2 * np.pi) + np.sum(np.log(v)) + np.sum(residuo**2 / v)
        )

    res = minimize_scalar(
        menos_ml, bounds=(np.log(1e-6), np.log(np.var(y) * 10)), method="bounded"
    )
    return float(-res.fun)


def correlacion_ponderada(x: np.ndarray, y: np.ndarray, pesos: np.ndarray) -> float:
    """Coeficiente de Pearson con pesos por dominio.

    Con pesos ``1/(Â + ψ_d)`` es la pendiente del Fay-Herriot univariado expresada en
    desviaciones estándar ponderadas: tiene la escala de una correlación (entre −1 y 1) y el
    mismo signo que β̂1.

    Args:
        x (np.ndarray): Covariable.
        y (np.ndarray): Respuesta.
        pesos (np.ndarray): Peso de cada dominio (no necesitan sumar uno).

    Returns:
        float: Correlación ponderada.

    Example:
        >>> correlacion_ponderada(x, Y, 1 / (A_hat + psi))
    """
    w = pesos / pesos.sum()
    dx, dy = x - w @ x, y - w @ y
    return float((w @ (dx * dy)) / np.sqrt((w @ dx**2) * (w @ dy**2)))


def fh_univariado(
    df: pd.DataFrame,
    columnas: list,
    y: np.ndarray,
    psi: np.ndarray,
    alias: dict = None,
    alfa: float = 0.05,
) -> pd.DataFrame:
    """Modelo Fay-Herriot univariado por covariable, con la varianza de muestreo ψ_d (G7-B8).

    Ajusta ``θ̂_d = β0 + β1·x_d + u_d + e_d`` con ``Var(u_d) = A`` (REML) y
    ``Var(e_d) = ψ_d``, y reporta la pendiente con su intervalo de Wald al ``1 - alfa``, el
    mismo que usa el notebook del modelo para los coeficientes. A diferencia de la
    correlación, el modelo pesa cada dominio por ``1/(Â + ψ_d)``: un dominio con estimación
    directa menos precisa pesa menos.

    `Razon_pesos` (peso máximo / peso mínimo) muestra cuánto se aparta el ajuste de uno con
    pesos iguales: cuando ``Â`` es mucho mayor que ψ_d, los pesos casi no varían y el modelo
    reproduce la regresión ordinaria.

    Multiplicidad (G7-B9): `p_FH` es el p-valor de Wald de β1 y `q_FH` su ajuste de
    Benjamini-Hochberg sobre **todas** las columnas evaluadas, que forman la familia de
    contrastes. Un intervalo al 95 % sin cero equivale a ``p_FH < 0.05`` repetido en cada
    candidata sin corrección; `q_FH` controla en cambio la proporción esperada de falsos
    descubrimientos entre las declaradas elegibles.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar (la familia completa de candidatas).
        y (np.ndarray): Estimación directa de la respuesta.
        psi (np.ndarray): Varianza de muestreo de cada dominio (SE²).
        alias (dict | None): Mapa columna → alias legible.
        alfa (float): Nivel de significancia del intervalo.

    Returns:
        pd.DataFrame: Una fila por covariable con `A_hat_FH`, `Razon_pesos`, `r_ponderada`,
            `Beta_FH`, `SE_FH`, `IC_FH_inf`, `IC_FH_sup`, `IC_FH_contiene_cero`
            (`"sí"`/`"no"`), `p_FH` y `q_FH`, ordenada por |r_ponderada| descendente.

    Example:
        >>> fh_univariado(df_cand, codigos, Y, SE**2, alias)
    """
    alias = alias or {}
    y = np.asarray(y, dtype=float)
    psi = np.asarray(psi, dtype=float)
    z = stats.norm.ppf(1 - alfa / 2)
    filas = []
    for col in columnas:
        x = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        a, beta, cov_beta = _ajuste_fh(x, y, psi)
        pesos = 1.0 / (a + psi)
        se = float(np.sqrt(cov_beta[1, 1]))
        inferior, superior = beta[1] - z * se, beta[1] + z * se
        filas.append(
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "A_hat_FH": round(a, 4),
                "Razon_pesos": round(float(pesos.max() / pesos.min()), 4),
                "r_ponderada": round(correlacion_ponderada(x, y, pesos), 3),
                "Beta_FH": float(beta[1]),
                "SE_FH": se,
                "IC_FH_inf": float(inferior),
                "IC_FH_sup": float(superior),
                "IC_FH_contiene_cero": "sí" if inferior <= 0 <= superior else "no",
                "p_FH": float(2 * stats.norm.sf(abs(beta[1] / se))),
            }
        )
    tabla = pd.DataFrame(filas)
    tabla["q_FH"] = multipletests(tabla["p_FH"], method="fdr_bh")[1]
    return tabla.sort_values("r_ponderada", key=abs, ascending=False)


def estabilidad_bootstrap(
    df: pd.DataFrame,
    columnas: list,
    y: np.ndarray,
    psi: np.ndarray,
    alias: dict = None,
    replicas: int = 1000,
    semilla: int = 42,
    alfa: float = 0.05,
) -> pd.DataFrame:
    """Estabilidad de la elegibilidad ante el remuestreo de dominios (G7-B9, descriptiva).

    En cada réplica se toman 23 dominios con reemplazo, cada uno con su ψ_d, se reajusta el
    Fay-Herriot univariado y se registra si el intervalo al ``1 - alfa`` de β1 excluye el cero
    **con el mismo signo** que en la muestra completa. La proporción de réplicas es la
    estabilidad. Todas las covariables usan las mismas réplicas. Las réplicas en que la
    covariable queda constante no permiten ajustar la pendiente: se omiten, la proporción
    se calcula sobre las réplicas válidas y `Replicas_omitidas` informa cuántas fueron
    (R-36).

    Complementa el control de falsos descubrimientos con una lectura que remuestrea los
    dominios en lugar de apoyarse solo en el p-valor de la muestra completa. No es una
    lectura libre de la aproximación normal: cada réplica usa un intervalo de Wald normal
    sin corrección. Una covariable elegible con estabilidad baja depende de qué dominios
    entren a la muestra. No decide; la ficha la reporta.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar.
        y (np.ndarray): Estimación directa de la respuesta.
        psi (np.ndarray): Varianza de muestreo de cada dominio (SE²).
        alias (dict | None): Mapa columna → alias legible.
        replicas (int): Número de réplicas bootstrap.
        semilla (int): Semilla del generador, para reproducir el resultado.
        alfa (float): Nivel del intervalo en cada réplica.

    Returns:
        pd.DataFrame: Una fila por covariable con `Estabilidad_boot` (entre 0 y 1, sobre las
            réplicas válidas; NaN si ninguna lo fue) y `Replicas_omitidas` (réplicas en que
            la covariable quedó constante).

    Example:
        >>> estabilidad_bootstrap(df_cand, codigos, Y, PSI, alias, replicas=1000)
    """
    alias = alias or {}
    y = np.asarray(y, dtype=float)
    psi = np.asarray(psi, dtype=float)
    z = stats.norm.ppf(1 - alfa / 2)
    generador = np.random.default_rng(semilla)
    muestras = [generador.integers(0, len(y), len(y)) for _ in range(replicas)]
    filas = []
    for col in columnas:
        x = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        _, beta, _ = _ajuste_fh(x, y, psi)
        exitos = 0
        validas = 0
        for idx in muestras:
            if np.ptp(x[idx]) == 0:
                continue
            validas += 1
            _, b, cov_b = _ajuste_fh(x[idx], y[idx], psi[idx])
            exitos += bool(
                abs(b[1]) > z * np.sqrt(cov_b[1, 1])
                and np.sign(b[1]) == np.sign(beta[1])
            )
        filas.append(
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "Estabilidad_boot": (
                    round(exitos / validas, 3) if validas else float("nan")
                ),
                "Replicas_omitidas": replicas - validas,
            }
        )
    return pd.DataFrame(filas)


def influencia_fh(
    df: pd.DataFrame,
    columnas: list,
    y: np.ndarray,
    psi: np.ndarray,
    etiquetas_dominio: np.ndarray,
    alias: dict = None,
) -> pd.DataFrame:
    """Distancia de Cook de cada dominio en el Fay-Herriot univariado de cada covariable (G7-B8).

    Usa la misma fórmula que `modelo/shared/seleccion_modelo.distancia_cook` para el modelo
    ajustado: ``D_d = r_d²·h_dd / (p·(1 - h_dd)²)``, con el residuo estandarizado
    ``r_d = (θ̂_d - x_d'β̂)/√(Â + ψ_d)`` y el apalancamiento ``h_dd = x_d'Cov(β̂)x_d/(Â + ψ_d)``,
    manteniendo ``Â`` fijo. Umbral convencional ``D > 4/n``.

    Superar el umbral **no justifica eliminar el dominio**: la consecuencia recae sobre la
    covariable.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar.
        y (np.ndarray): Estimación directa de la respuesta.
        psi (np.ndarray): Varianza de muestreo de cada dominio (SE²).
        etiquetas_dominio (np.ndarray): Nombre de cada dominio.
        alias (dict | None): Mapa columna → alias legible.

    Returns:
        pd.DataFrame: Una fila por covariable con `Cook_max`, `Umbral`, `N_influyentes` y
            `Dominios_influyentes`.

    Example:
        >>> influencia_fh(df_cand, codigos, Y, PSI, entidades, alias)
    """
    alias = alias or {}
    y = np.asarray(y, dtype=float)
    psi = np.asarray(psi, dtype=float)
    umbral = 4 / len(y)
    filas = []
    for col in columnas:
        x = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        a, beta, cov_beta = _ajuste_fh(x, y, psi)
        X = np.column_stack([np.ones_like(x), x])
        varianza = a + psi
        residuo = (y - X @ beta) / np.sqrt(varianza)
        apalancamiento = np.einsum("ij,jk,ik->i", X, cov_beta, X) / varianza
        cook = residuo**2 * apalancamiento / (2 * (1 - apalancamiento) ** 2)
        influyentes = [
            f"{etiquetas_dominio[i]} ({cook[i]:.3f})"
            for i in np.where(cook > umbral)[0]
        ]
        filas.append(
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "Cook_max": round(float(cook.max()), 4),
                "Umbral": round(umbral, 4),
                "N_influyentes": len(influyentes),
                "Dominios_influyentes": "; ".join(influyentes) if influyentes else "—",
            }
        )
    return pd.DataFrame(filas)


def estabilidad_fh(
    df: pd.DataFrame,
    columnas: list,
    y: np.ndarray,
    psi: np.ndarray,
    etiquetas_dominio: np.ndarray,
    alias: dict = None,
) -> pd.DataFrame:
    """Cambio en la correlación ponderada al excluir cada dominio y reajustar el FH (G7-B8).

    Por cada dominio se vuelve a ajustar el Fay-Herriot univariado sin él, **reestimando Â**,
    y se mide el cambio en la correlación ponderada (la pendiente en escala de correlación),
    de modo que el umbral `UMBRAL_DELTA_LOO` conserva su lectura. Se registra además si la
    exclusión invierte el signo de β̂1. Recorre los 23 dominios.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar.
        y (np.ndarray): Estimación directa de la respuesta.
        psi (np.ndarray): Varianza de muestreo de cada dominio (SE²).
        etiquetas_dominio (np.ndarray): Nombre de cada dominio.
        alias (dict | None): Mapa columna → alias legible.

    Returns:
        pd.DataFrame: Una fila por covariable con `r_completo` (correlación ponderada),
            `Delta_max`, `Delta_max_abs`, `Dominio_critico` e `Invierte_signo`.

    Example:
        >>> estabilidad_fh(df_cand, codigos, Y, PSI, entidades, alias)
    """
    alias = alias or {}
    y = np.asarray(y, dtype=float)
    psi = np.asarray(psi, dtype=float)
    n = len(y)
    filas = []
    for col in columnas:
        x = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        a, beta, _ = _ajuste_fh(x, y, psi)
        r_completo = correlacion_ponderada(x, y, 1.0 / (a + psi))

        deltas = np.empty(n)
        signos_invertidos = []
        for i in range(n):
            m = np.arange(n) != i
            a_i, beta_i, _ = _ajuste_fh(x[m], y[m], psi[m])
            deltas[i] = (
                correlacion_ponderada(x[m], y[m], 1.0 / (a_i + psi[m])) - r_completo
            )
            if np.sign(beta_i[1]) != np.sign(beta[1]):
                signos_invertidos.append(etiquetas_dominio[i])

        idx_max = int(np.argmax(np.abs(deltas)))
        filas.append(
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "r_completo": round(r_completo, 3),
                "Delta_max": round(float(deltas[idx_max]), 3),
                "Delta_max_abs": round(float(np.abs(deltas).max()), 3),
                "Dominio_critico": etiquetas_dominio[idx_max],
                "Invierte_signo": (
                    ", ".join(signos_invertidos) if signos_invertidos else "—"
                ),
            }
        )
    return pd.DataFrame(filas)


def forma_funcional(
    df: pd.DataFrame,
    columnas: list,
    y: np.ndarray,
    psi: np.ndarray,
    alias: dict = None,
    alfa: float = 0.05,
    delta_aic: float = 2.0,
) -> pd.DataFrame:
    """Examina si la forma lineal es adecuada para cada covariable (G7-B13).

    Dos contrastes sobre el Fay-Herriot univariado con ψ_d, el mismo modelo que decide la
    elegibilidad (G7-B8):

    * **Curvatura**: se agrega el término cuadrático de la covariable estandarizada y se
      contrasta su coeficiente con la prueba de Wald al nivel `alfa`.
    * **Escala logarítmica**: si la covariable es estrictamente positiva, se compara el AIC
      (verosimilitud ML) del modelo con ``log(x)`` frente al modelo con ``x``. Ambos tienen el
      mismo número de parámetros, de modo que la diferencia de AIC es la de verosimilitudes.

    El resultado es un **diagnóstico, no una transformación automática**: la covariable
    entra al modelo en su escala original. Si el contraste encuentra curvatura o un AIC
    menor en al menos `delta_aic` con el logaritmo, la ficha de decisión lo advierte para
    que se revise antes de fijar el predictor lineal. Transformar una covariable exigiría
    aplicar la misma transformación a los municipios objetivo en el notebook del modelo.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar.
        y (np.ndarray): Estimación directa de la respuesta.
        psi (np.ndarray): Varianza de muestreo de cada dominio (SE²).
        alias (dict | None): Mapa columna → alias legible.
        alfa (float): Nivel de la prueba de curvatura.
        delta_aic (float): Mejora mínima de AIC con el logaritmo para advertirla.

    Returns:
        pd.DataFrame: Una fila por covariable con `p_curvatura`, `Curvatura` (`"sí"`/`"no"`),
            `dAIC_log` (AIC con log menos AIC lineal; vacío si x no es positiva),
            `Log_mejora` (`"sí"`/`"no"`/`"—"`) y `Forma_funcional` (`"lineal adecuada"` o
            `"revisar"`).

    Example:
        >>> forma_funcional(df_cand, codigos, Y, PSI, alias)
    """
    alias = alias or {}
    y = np.asarray(y, dtype=float)
    psi = np.asarray(psi, dtype=float)
    uno = np.ones_like(y)
    filas = []
    for col in columnas:
        x = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        z = (x - x.mean()) / x.std()
        _, beta, cov_beta = _ajuste_fh_matriz(np.column_stack([uno, z, z**2]), y, psi)
        p_curva = float(2 * stats.norm.sf(abs(beta[2] / np.sqrt(cov_beta[2, 2]))))
        curvatura = p_curva < alfa
        if x.min() > 0:
            ll_lineal = _loglik_ml(np.column_stack([uno, x]), y, psi)
            ll_log = _loglik_ml(np.column_stack([uno, np.log(x)]), y, psi)
            d_aic = -2 * (ll_log - ll_lineal)
            log_mejora = "sí" if d_aic <= -delta_aic else "no"
        else:
            d_aic, log_mejora = np.nan, "—"
        filas.append(
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "p_curvatura": round(p_curva, 4),
                "Curvatura": "sí" if curvatura else "no",
                "dAIC_log": round(d_aic, 3) if not np.isnan(d_aic) else np.nan,
                "Log_mejora": log_mejora,
                "Forma_funcional": (
                    "revisar" if curvatura or log_mejora == "sí" else "lineal adecuada"
                ),
            }
        )
    return pd.DataFrame(filas)


def figura_residuos_parciales(
    df: pd.DataFrame,
    columnas: list,
    y: np.ndarray,
    psi: np.ndarray,
    alias: dict = None,
):
    """Residuos parciales de cada covariable en el Fay-Herriot con todo el conjunto (G7-B13).

    Para la covariable ``j`` el residuo parcial es ``θ̂_d - x_d'β̂ + β̂_j·x_dj``: la parte de la
    respuesta que queda tras descontar las demás covariables. Si la forma lineal es adecuada,
    los puntos siguen la recta de pendiente ``β̂_j``; una curva suavizada (lowess) que se
    aparta de ella de forma sistemática indica que el predictor lineal no recoge la relación.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables del conjunto (normalmente las seleccionadas).
        y (np.ndarray): Estimación directa de la respuesta.
        psi (np.ndarray): Varianza de muestreo de cada dominio (SE²).
        alias (dict | None): Mapa columna → alias legible.

    Returns:
        matplotlib.figure.Figure: Un panel por covariable.

    Example:
        >>> fig = figura_residuos_parciales(df_cand, SELECCIONADAS, Y, PSI, ALIAS)
    """
    import matplotlib.pyplot as plt
    from statsmodels.nonparametric.smoothers_lowess import lowess

    alias = alias or {}
    y = np.asarray(y, dtype=float)
    psi = np.asarray(psi, dtype=float)
    Xc = np.column_stack(
        [pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float) for c in columnas]
    )
    X = np.column_stack([np.ones_like(y), Xc])
    _, beta, _ = _ajuste_fh_matriz(X, y, psi)
    residuo = y - X @ beta

    fig, ejes = plt.subplots(
        1, len(columnas), figsize=(4.2 * len(columnas), 3.8), squeeze=False
    )
    for j, (col, ax) in enumerate(zip(columnas, ejes[0])):
        x = Xc[:, j]
        parcial = residuo + beta[j + 1] * x
        ax.scatter(x, parcial, s=30, color="steelblue", edgecolors="white", zorder=3)
        orden = np.argsort(x)
        ax.plot(
            x[orden],
            beta[j + 1] * x[orden] + (parcial - beta[j + 1] * x).mean(),
            color="dimgray",
            linestyle="--",
            linewidth=1.2,
            label="Recta del modelo",
        )
        suave = lowess(parcial, x, frac=0.8)
        ax.plot(
            suave[:, 0], suave[:, 1], color="firebrick", linewidth=1.4, label="Lowess"
        )
        ax.set_xlabel(alias.get(col, col), fontsize=9)
        ax.set_ylabel("Residuo parcial", fontsize=9)
        ax.tick_params(labelsize=8)
    ejes[0][0].legend(fontsize=8, loc="best")
    plt.tight_layout()
    return fig


def vif_conjunto(df: pd.DataFrame, columnas: list, alias: dict = None) -> pd.DataFrame:
    """Factor de inflación de la varianza de un conjunto de covariables.

    Se calcula sobre el conjunto que efectivamente podría entrar al modelo, no sobre el
    universo de candidatas: con 23 dominios, un sistema con muchas más covariables que
    grados de libertad produce un factor sin sentido. Para juzgar redundancia dentro del
    conjunto amplio de candidatas se usa la correlación por pares.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables del conjunto a verificar.
        alias (dict | None): Mapa columna → alias legible.

    Returns:
        pd.DataFrame: Una fila por covariable con su factor de inflación de la varianza.
            Con una sola covariable el factor es 1 por definición.

    Example:
        >>> vif_conjunto(df_cand, seleccionadas, alias)
    """
    alias = alias or {}
    if len(columnas) < 2:
        return pd.DataFrame(
            [{"Alias": alias.get(c, c), "Codigo": c, "VIF": 1.0} for c in columnas]
        )

    matriz = add_constant(df[columnas].astype(float).values)
    return pd.DataFrame(
        [
            {
                "Alias": alias.get(col, col),
                "Codigo": col,
                "VIF": round(float(variance_inflation_factor(matriz, i + 1)), 3),
            }
            for i, col in enumerate(columnas)
        ]
    )


def figura_robustez(
    influencia: pd.DataFrame, estabilidad: pd.DataFrame, umbral_delta: float = 0.10
):
    """Sitúa cada covariable frente a los dos criterios de robustez, en un solo gráfico.

    El eje horizontal es la distancia de Cook máxima y el vertical el cambio máximo en la
    correlación al excluir un dominio. Las líneas marcan los umbrales: solo las covariables
    que quedan simultáneamente a la derecha y por encima se descartan, porque solo en ese
    cuadrante un dominio domina la regresión *y* su exclusión altera la asociación.

    Args:
        influencia (pd.DataFrame): Salida de `influencia_fh()`.
        estabilidad (pd.DataFrame): Salida de `estabilidad_fh()`.
        umbral_delta (float): Umbral del eje vertical.

    Returns:
        matplotlib.figure.Figure: Figura del plano de robustez.

    Example:
        >>> fig = figura_robustez(df_cook, df_loo)
    """
    import matplotlib.pyplot as plt

    unido = influencia.merge(estabilidad, on="Codigo", suffixes=("", "_loo"))
    umbral_cook = float(unido["Umbral"].iloc[0])

    fig, ax = plt.subplots(figsize=(8.5, 6))
    descartadas = (unido["Cook_max"] > umbral_cook) & (
        unido["Delta_max_abs"] > umbral_delta
    )

    ax.scatter(
        unido.loc[~descartadas, "Cook_max"],
        unido.loc[~descartadas, "Delta_max_abs"],
        s=70,
        color="steelblue",
        edgecolors="white",
        zorder=3,
        label="No supera ambos umbrales",
    )
    ax.scatter(
        unido.loc[descartadas, "Cook_max"],
        unido.loc[descartadas, "Delta_max_abs"],
        s=70,
        color="firebrick",
        edgecolors="white",
        zorder=3,
        label="Supera ambos umbrales",
    )

    for _, fila in unido.iterrows():
        ax.annotate(
            fila["Alias"],
            (fila["Cook_max"], fila["Delta_max_abs"]),
            textcoords="offset points",
            xytext=(5, 4),
            fontsize=7,
            color="dimgray",
        )

    ax.axvline(
        umbral_cook,
        color="dimgray",
        linestyle="--",
        linewidth=1.2,
        label=f"Cook = 4/n = {umbral_cook:.3f}",
    )
    ax.axhline(
        umbral_delta,
        color="dimgray",
        linestyle=":",
        linewidth=1.2,
        label=f"Cambio en la correlación = {umbral_delta}",
    )
    ax.set_xlabel("Distancia de Cook máxima", fontsize=10)
    ax.set_ylabel("Cambio máximo en la correlación al excluir un dominio", fontsize=10)
    ax.legend(fontsize=9, loc="best")
    plt.tight_layout()
    return fig


def interpretar_robustez(
    influencia: pd.DataFrame, estabilidad: pd.DataFrame, umbral_delta: float = 0.10
) -> str:
    """Lectura textual del plano de robustez, calculada desde las tablas de diagnóstico.

    Args:
        influencia (pd.DataFrame): Salida de `influencia_fh()`.
        estabilidad (pd.DataFrame): Salida de `estabilidad_fh()`.
        umbral_delta (float): Umbral del cambio en la correlación.

    Returns:
        str: Interpretación lista para imprimir junto a la figura.

    Example:
        >>> print(interpretar_robustez(df_influencia, df_estabilidad))
    """
    unido = influencia.merge(estabilidad, on="Codigo", suffixes=("", "_loo"))
    umbral_cook = float(unido["Umbral"].iloc[0])
    apalancadas = unido[unido["Cook_max"] > umbral_cook]
    inestables = unido[
        (unido["Delta_max_abs"] > umbral_delta) | (unido["Invierte_signo"] != "—")
    ]
    ambas = unido[
        (unido["Cook_max"] > umbral_cook)
        & ((unido["Delta_max_abs"] > umbral_delta) | (unido["Invierte_signo"] != "—"))
    ]

    dominios = pd.Series(
        [
            d.split(" (")[0]
            for cadena in apalancadas["Dominios_influyentes"]
            for d in cadena.split("; ")
            if d != "—"
        ]
    )
    frecuentes = (
        ", ".join(f"{k} ({v})" for k, v in dominios.value_counts().head(3).items())
        if not dominios.empty
        else "—"
    )

    lineas = [
        "INTERPRETACIÓN DEL PLANO DE ROBUSTEZ:",
        f"  Covariables con un dominio que domina la regresión (Cook > {umbral_cook:.3f}): "
        f"{len(apalancadas)} de {len(unido)}",
        f"  Dominios que más veces resultan influyentes: {frecuentes}",
        f"  Covariables cuya correlación cambia más de {umbral_delta} o invierte el signo al excluir un dominio: "
        f"{len(inestables)}",
        f"  Covariables que cumplen ambas condiciones y se descartan: {len(ambas)}"
        + (f" ({', '.join(ambas['Alias'])})" if len(ambas) else ""),
    ]
    if len(apalancadas) and not len(ambas):
        lineas.append(
            "  Lectura: hay dominios extremos, pero ninguno altera por sí solo la asociación; las "
            "covariables se conservan porque la relación no depende de un único territorio."
        )
    return "\n".join(lineas)
