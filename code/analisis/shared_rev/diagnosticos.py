"""Diagnósticos que sustentan decisiones sobre las covariables candidatas.

A diferencia de `descriptivos.py`, cuyo propósito es comprender los datos, cada función de
este módulo produce evidencia destinada a una decisión concreta:

* `influencia_por_covariable()` y `estabilidad_loo()` determinan si la asociación entre una
  covariable y la respuesta depende de un único dominio.
* `vif_conjunto()` verifica que el conjunto finalmente elegido no presente
  multicolinealidad.
* `moran_permutacion()` contrasta el supuesto de independencia entre dominios del modelo
  Fay-Herriot, sobre los residuos.

Respecto de la versión original se retiran dos procedimientos:

* El contraste de Shapiro-Wilk sobre las covariables. El modelo Fay-Herriot supone
  normalidad de los efectos aleatorios y de los errores de muestreo, no de las covariables,
  que pueden tener cualquier distribución; con 23 dominios el contraste además carece de
  potencia. No decidía nada y se sustituye por la asimetría y los diagramas de caja del
  análisis descriptivo.
* El índice de Moran sobre la tasa de desempleo sin ajustar. El supuesto de independencia
  del modelo es sobre los residuos, no sobre la respuesta cruda; calcularlo dos veces
  duplicaba el procedimiento sin añadir una decisión. La descripción territorial de la
  respuesta se conserva, en forma gráfica, dentro del análisis descriptivo.
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import cdist
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.outliers_influence import OLSInfluence, variance_inflation_factor
from statsmodels.tools import add_constant


def ic_bootstrap_pearson(x: np.ndarray, y: np.ndarray, n_replicas: int = 10000,
                         alfa: float = 0.05, semilla: int = 42) -> tuple:
    """Intervalo de confianza bootstrap percentil para el coeficiente de Pearson.

    Con 23 dominios el error estándar de una correlación es grande; el intervalo comunica
    esa incertidumbre, que un coeficiente puntual oculta.

    Args:
        x (np.ndarray): Covariable.
        y (np.ndarray): Variable respuesta.
        n_replicas (int): Número de remuestreos con reemplazo.
        alfa (float): Nivel de significancia; el intervalo es de ``1 - alfa``.
        semilla (int): Semilla del generador, para reproducibilidad.

    Returns:
        tuple[float, float]: Extremos inferior y superior del intervalo.

    Example:
        >>> ic_bootstrap_pearson(x, Y)
        (0.221, 0.803)
    """
    generador = np.random.default_rng(semilla)
    n = len(x)
    replicas = np.empty(n_replicas)
    for i in range(n_replicas):
        idx = generador.integers(0, n, n)
        replicas[i] = stats.pearsonr(x[idx], y[idx])[0]
    inferior, superior = np.percentile(replicas, [100 * alfa / 2, 100 * (1 - alfa / 2)])
    return float(inferior), float(superior)


def ic_fisher_pearson(x: np.ndarray, y: np.ndarray, alfa: float = 0.05) -> tuple:
    """Intervalo de confianza para el coeficiente de Pearson por transformación de Fisher.

    Se reporta junto al intervalo bootstrap como referencia independiente. El motivo es que
    el bootstrap de percentiles pierde fiabilidad cuando la relación está dominada por una
    única observación de gran influencia: al remuestrear, la anchura del intervalo pasa a
    depender de cuántas veces se extrae ese punto y puede resultar artificialmente estrecha,
    llegando a excluir el cero para correlaciones débiles. La transformación de Fisher no
    remuestrea y por tanto no presenta ese comportamiento, aunque supone normalidad bivariada.

    Cuando ambos intervalos discrepan de forma apreciable, la lectura correcta es que la
    incertidumbre del coeficiente no está bien caracterizada por ninguno de los dos, y la
    evidencia sobre esa covariable debe considerarse débil con independencia de su magnitud.

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
        raise ValueError("La transformación de Fisher requiere al menos cuatro observaciones.")
    r = float(np.corrcoef(x, y)[0, 1])
    z = np.arctanh(np.clip(r, -0.999999, 0.999999))
    error = stats.norm.ppf(1 - alfa / 2) / np.sqrt(n - 3)
    return float(np.tanh(z - error)), float(np.tanh(z + error))


def influencia_por_covariable(df: pd.DataFrame, columnas: list, y: np.ndarray,
                              etiquetas_dominio: np.ndarray, alias: dict = None) -> pd.DataFrame:
    """Distancia de Cook de cada dominio en la regresión simple covariable → respuesta.

    Mide cuánto cambia el vector de coeficientes al eliminar un dominio. Con 23
    observaciones un solo punto puede determinar la pendiente, de modo que este diagnóstico
    distingue una asociación sostenida por el conjunto de los dominios de una sostenida por
    uno solo. Se usa el umbral convencional ``D > 4/n``.

    Superar el umbral **no justifica eliminar el dominio**: los valores extremos observados
    corresponden a territorios reales, no a errores de medición. La consecuencia es sobre la
    covariable, no sobre la observación.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar.
        y (np.ndarray): Variable respuesta.
        etiquetas_dominio (np.ndarray): Nombre de cada dominio.
        alias (dict | None): Mapa columna → alias legible.

    Returns:
        pd.DataFrame: Una fila por covariable con la distancia de Cook máxima, el número de
            dominios que superan el umbral y su identificación.

    Example:
        >>> influencia_por_covariable(df_cand, codigos, Y, entidades, alias)
    """
    alias = alias or {}
    umbral = 4 / len(y)
    filas = []

    for col in columnas:
        x = pd.to_numeric(df[col], errors="coerce").values.reshape(-1, 1)
        modelo = OLS(y, add_constant(x)).fit()
        cook = OLSInfluence(modelo).cooks_distance[0]
        influyentes = [
            f"{etiquetas_dominio[i]} ({cook[i]:.3f})" for i in np.where(cook > umbral)[0]
        ]
        filas.append({
            "Alias":        alias.get(col, col),
            "Codigo":       col,
            "Cook_max":     round(float(cook.max()), 4),
            "Umbral":       round(umbral, 4),
            "N_influyentes": len(influyentes),
            "Dominios_influyentes": "; ".join(influyentes) if influyentes else "—",
        })

    return pd.DataFrame(filas)


def estabilidad_loo(df: pd.DataFrame, columnas: list, y: np.ndarray,
                    etiquetas_dominio: np.ndarray, alias: dict = None) -> pd.DataFrame:
    """Cambio en la correlación con la respuesta al excluir cada dominio, uno a uno.

    Recorre **todos** los dominios, no un subconjunto elegido a mano. La versión original
    evaluaba solo cinco territorios seleccionados por inspección de los diagramas de caja,
    lo que introducía una decisión manual difícil de reproducir y dependía de un cotejo de
    nombres propenso a fallar. Recorrer los 23 dominios cuesta lo mismo y elimina ambos
    problemas.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables a evaluar.
        y (np.ndarray): Variable respuesta.
        etiquetas_dominio (np.ndarray): Nombre de cada dominio.
        alias (dict | None): Mapa columna → alias legible.

    Returns:
        pd.DataFrame: Una fila por covariable con la correlación completa, el cambio máximo
            en valor absoluto, el dominio responsable y si la exclusión de algún dominio
            invierte el signo de la asociación.

    Example:
        >>> estabilidad_loo(df_cand, codigos, Y, entidades, alias)
    """
    alias = alias or {}
    n = len(y)
    filas = []

    for col in columnas:
        x = pd.to_numeric(df[col], errors="coerce").values
        r_completo = float(stats.pearsonr(x, y)[0])

        deltas = np.empty(n)
        signos_invertidos = []
        for i in range(n):
            mascara = np.ones(n, dtype=bool)
            mascara[i] = False
            r_loo = float(stats.pearsonr(x[mascara], y[mascara])[0])
            deltas[i] = r_loo - r_completo
            if np.sign(r_loo) != np.sign(r_completo):
                signos_invertidos.append(etiquetas_dominio[i])

        idx_max = int(np.argmax(np.abs(deltas)))
        filas.append({
            "Alias":        alias.get(col, col),
            "Codigo":       col,
            "r_completo":   round(r_completo, 3),
            "Delta_max":    round(float(deltas[idx_max]), 3),
            "Delta_max_abs": round(float(np.abs(deltas).max()), 3),
            "Dominio_critico": etiquetas_dominio[idx_max],
            "Invierte_signo": ", ".join(signos_invertidos) if signos_invertidos else "—",
        })

    return pd.DataFrame(filas)


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

    Raises:
        ValueError: Si `columnas` tiene menos de dos elementos.

    Example:
        >>> vif_conjunto(df_cand, seleccionadas, alias)
    """
    if len(columnas) < 2:
        raise ValueError("El factor de inflación de la varianza requiere al menos dos covariables.")

    alias = alias or {}
    matriz = add_constant(df[columnas].astype(float).values)
    return pd.DataFrame([
        {
            "Alias":  alias.get(col, col),
            "Codigo": col,
            "VIF":    round(float(variance_inflation_factor(matriz, i + 1)), 3),
        }
        for i, col in enumerate(columnas)
    ])


def matriz_pesos_distancia_inversa(coordenadas: np.ndarray) -> np.ndarray:
    """Matriz de pesos espaciales por distancia inversa, estandarizada por filas.

    Se prefiere la distancia inversa a la contigüidad porque los dominios con encuesta son
    ciudades dispersas por el territorio nacional que en su mayoría no comparten frontera:
    una matriz de contigüidad quedaría casi vacía.

    Args:
        coordenadas (np.ndarray): Latitud y longitud de cada dominio, shape (n, 2).

    Returns:
        np.ndarray: Matriz de pesos, shape (n, n), con diagonal nula y filas que suman uno.

    Example:
        >>> W = matriz_pesos_distancia_inversa(coords)
    """
    distancias = cdist(coordenadas, coordenadas)
    np.fill_diagonal(distancias, np.inf)
    pesos = 1.0 / distancias
    return pesos / pesos.sum(axis=1, keepdims=True)


def moran_i(valores: np.ndarray, pesos: np.ndarray) -> float:
    """Índice de Moran de una variable dada una matriz de pesos espaciales.

    Args:
        valores (np.ndarray): Variable sobre la que se mide la dependencia espacial.
        pesos (np.ndarray): Matriz de pesos espaciales.

    Returns:
        float: Índice de Moran observado.

    Example:
        >>> moran_i(residuos, W)
        -0.1253
    """
    n = len(valores)
    centrados = valores - valores.mean()
    return float(
        n * np.sum(pesos * np.outer(centrados, centrados))
        / (np.sum(pesos) * np.sum(centrados ** 2))
    )


def moran_permutacion(valores: np.ndarray, pesos: np.ndarray, n_permutaciones: int = 999,
                      semilla: int = 42) -> dict:
    """Contrasta la autocorrelación espacial por permutación de las etiquetas.

    Bajo la hipótesis nula de independencia el valor esperado del índice no es cero sino
    ``-1/(n-1)``; la distribución empírica de permutaciones incorpora esa referencia sin
    necesidad de corregirla analíticamente.

    Args:
        valores (np.ndarray): Variable a contrastar; normalmente los residuos del modelo.
        pesos (np.ndarray): Matriz de pesos espaciales.
        n_permutaciones (int): Número de reasignaciones aleatorias.
        semilla (int): Semilla del generador, para reproducibilidad.

    Returns:
        dict: `I_observado`, `E_bajo_H0`, `p_valor` y `I_permutado` (np.ndarray con la
            distribución nula, para graficarla).

    Example:
        >>> moran_permutacion(residuos, W)["p_valor"]
        0.035
    """
    generador = np.random.default_rng(semilla)
    i_observado = moran_i(valores, pesos)
    permutados = np.array([
        moran_i(generador.permutation(valores), pesos) for _ in range(n_permutaciones)
    ])
    return {
        "I_observado":  i_observado,
        "E_bajo_H0":    -1 / (len(valores) - 1),
        "p_valor":      float(np.mean(np.abs(permutados) >= abs(i_observado))),
        "I_permutado":  permutados,
    }


def figura_robustez(influencia: pd.DataFrame, estabilidad: pd.DataFrame,
                    umbral_delta: float = 0.10):
    """Sitúa cada covariable frente a los dos criterios de robustez, en un solo gráfico.

    El eje horizontal es la distancia de Cook máxima y el vertical el cambio máximo en la
    correlación al excluir un dominio. Las líneas marcan los umbrales: solo las covariables
    que quedan simultáneamente a la derecha y por encima se descartan, porque solo en ese
    cuadrante un dominio domina la regresión *y* su exclusión altera la asociación.

    Args:
        influencia (pd.DataFrame): Salida de `influencia_por_covariable()`.
        estabilidad (pd.DataFrame): Salida de `estabilidad_loo()`.
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
    descartadas = (unido["Cook_max"] > umbral_cook) & (unido["Delta_max_abs"] > umbral_delta)

    ax.scatter(unido.loc[~descartadas, "Cook_max"], unido.loc[~descartadas, "Delta_max_abs"],
               s=70, color="steelblue", edgecolors="white", zorder=3, label="No supera ambos umbrales")
    ax.scatter(unido.loc[descartadas, "Cook_max"], unido.loc[descartadas, "Delta_max_abs"],
               s=70, color="firebrick", edgecolors="white", zorder=3, label="Supera ambos umbrales")

    for _, fila in unido.iterrows():
        ax.annotate(fila["Alias"], (fila["Cook_max"], fila["Delta_max_abs"]),
                    textcoords="offset points", xytext=(5, 4), fontsize=7, color="dimgray")

    ax.axvline(umbral_cook, color="dimgray", linestyle="--", linewidth=1.2,
               label=f"Cook = 4/n = {umbral_cook:.3f}")
    ax.axhline(umbral_delta, color="dimgray", linestyle=":", linewidth=1.2,
               label=f"Cambio en la correlación = {umbral_delta}")
    ax.set_xlabel("Distancia de Cook máxima", fontsize=10)
    ax.set_ylabel("Cambio máximo en la correlación al excluir un dominio", fontsize=10)
    ax.legend(fontsize=9, loc="best")
    plt.tight_layout()
    return fig


def figura_moran(resultado: dict, titulo: str = "Contraste de autocorrelación espacial"):
    """Distribución nula por permutación del índice de Moran, con el valor observado.

    Args:
        resultado (dict): Salida de `moran_permutacion()`.
        titulo (str): Título de la figura.

    Returns:
        matplotlib.figure.Figure: Histograma de la distribución nula.

    Example:
        >>> fig = figura_moran(moran_permutacion(residuos, W))
    """
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.hist(resultado["I_permutado"], bins=40, color="lightsteelblue",
            edgecolor="steelblue", alpha=0.85)
    ax.axvline(resultado["I_observado"], color="firebrick", linewidth=2,
               label=f"I observado = {resultado['I_observado']:.4f}")
    ax.axvline(resultado["E_bajo_H0"], color="darkgreen", linestyle="--", linewidth=1.5,
               label=f"E[I] bajo independencia = {resultado['E_bajo_H0']:.4f}")
    ax.set_xlabel("Índice de Moran bajo permutación", fontsize=10)
    ax.set_ylabel("Frecuencia", fontsize=10)
    ax.set_title(f"{titulo}  (p = {resultado['p_valor']:.4f})", fontsize=11, fontweight="bold")
    ax.legend(fontsize=9)
    plt.tight_layout()
    return fig
