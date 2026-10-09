"""Matrices de proximidad espacial y diagnóstico de dependencia espacial (I de Moran).

El Fay-Herriot espacial necesita una matriz W que diga qué tan cerca está cada par de
unidades (Morales et al., 2021, p. 491: la proximidad se define por contigüidad o por
distancia). Aquí se usa la **distancia** entre centroides, y no la contigüidad, por dos razones
documentadas en `docs/fay_herriot_espacial.md`:

1. Los 23 dominios con encuesta son ciudades o áreas metropolitanas dispersas por el país:
   casi ninguno comparte frontera con otro.
2. Los municipios objetivo (Cauca y Valle) tienen por vecinos contiguos a otros municipios
   objetivo, que tampoco tienen dato; con contigüidad pura no recibirían información de la
   encuesta.

El flujo es: coordenadas → matriz de distancias (`distancias_haversine`) → proximidad cruda
simétrica (`proximidad_knn` o `proximidad_inversa`) → estandarización por filas
(`estandarizar_filas`), que es la forma que exige el SAR para que ρ ∈ (−1, 1).
"""

import numpy as np

RADIO_TIERRA_KM = 6371.0


def distancias_haversine(latitud: np.ndarray, longitud: np.ndarray) -> np.ndarray:
    """Matriz de distancias en km sobre la esfera terrestre (fórmula de Haversine).

    Args:
        latitud (np.ndarray): Latitudes en grados decimales, shape (m,).
        longitud (np.ndarray): Longitudes en grados decimales, shape (m,).

    Returns:
        np.ndarray: Matriz simétrica (m, m) de distancias en kilómetros, con ceros en la
            diagonal.

    Raises:
        ValueError: Si las longitudes de `latitud` y `longitud` no coinciden o hay valores
            nulos.

    Example:
        >>> d = distancias_haversine(np.array([3.41, 2.46]), np.array([-76.52, -76.60]))
        >>> round(float(d[0, 1]))
        106
    """
    latitud = np.asarray(latitud, dtype=float)
    longitud = np.asarray(longitud, dtype=float)
    if latitud.shape != longitud.shape:
        raise ValueError("`latitud` y `longitud` deben tener la misma longitud.")
    if np.isnan(latitud).any() or np.isnan(longitud).any():
        raise ValueError("Hay unidades sin coordenadas; no se puede construir W.")
    lat = np.radians(latitud)
    lon = np.radians(longitud)
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat)[:, None] * np.cos(lat)[None, :] * np.sin(dlon / 2) ** 2
    )
    return 2 * RADIO_TIERRA_KM * np.arcsin(np.sqrt(a))


def proximidad_knn(distancias: np.ndarray, k: int) -> np.ndarray:
    """Proximidad binaria de los k vecinos más cercanos, simetrizada.

    Cada unidad queda conectada con sus k vecinos más cercanos; luego se simetriza (si i es
    vecino de j, j lo es de i) para que ninguna unidad quede aislada.

    Args:
        distancias (np.ndarray): Matriz (m, m) de distancias en km.
        k (int): Número de vecinos por unidad (1 <= k < m).

    Returns:
        np.ndarray: Matriz (m, m) con 1 donde hay vecindad y 0 en el resto, diagonal nula. Sin
            estandarizar: aplicar `estandarizar_filas` antes de usarla como W.

    Raises:
        ValueError: Si `k` no está entre 1 y m − 1.

    Example:
        >>> proximidad_knn(distancias, k=3).sum(axis=1).min() >= 3
        True
    """
    m = distancias.shape[0]
    if not 1 <= k < m:
        raise ValueError(f"k debe estar entre 1 y {m - 1}; se recibió {k}.")
    d = distancias.copy()
    np.fill_diagonal(d, np.inf)
    vecinos = np.argsort(d, axis=1)[:, :k]
    P = np.zeros((m, m))
    filas = np.repeat(np.arange(m), k)
    P[filas, vecinos.ravel()] = 1.0
    return np.maximum(P, P.T)


def proximidad_inversa(distancias: np.ndarray, potencia: float = 1.0) -> np.ndarray:
    """Proximidad densa de distancia inversa: w_ij = 1 / d_ij^potencia.

    A diferencia de kNN, conecta todas las unidades; el peso decae con la distancia, de modo
    que un municipio recibe sobre todo la influencia del dominio con encuesta más cercano
    pero no se la quita a los demás. Dos unidades en la misma coordenada (d = 0) reciben el
    peso de la distancia mínima positiva, para evitar divisiones por cero.

    Args:
        distancias (np.ndarray): Matriz (m, m) de distancias en km.
        potencia (float): Exponente de decaimiento (1 = suave, 2 = rápido).

    Returns:
        np.ndarray: Matriz (m, m) simétrica no negativa, diagonal nula, sin estandarizar.

    Example:
        >>> P = proximidad_inversa(distancias, potencia=2.0)
    """
    d = distancias.copy()
    positivas = d[d > 0]
    piso = positivas.min() if positivas.size else 1.0
    d = np.maximum(d, piso)
    P = 1.0 / d**potencia
    np.fill_diagonal(P, 0.0)
    return P


def estandarizar_filas(proximidad: np.ndarray) -> np.ndarray:
    """Estandariza por filas (cada fila suma 1), como exige el SAR (Morales et al., p. 491).

    Con W estocástica por filas, el parámetro de autocorrelación espacial ρ queda en (−1, 1).

    Args:
        proximidad (np.ndarray): Matriz (m, m) no negativa con diagonal nula.

    Returns:
        np.ndarray: Matriz (m, m) donde cada fila suma 1.

    Raises:
        ValueError: Si alguna fila suma cero (unidad sin vecinos).

    Example:
        >>> estandarizar_filas(proximidad_knn(distancias, 3)).sum(axis=1)
        array([1., 1., ...])
    """
    suma = proximidad.sum(axis=1, keepdims=True)
    if (suma == 0).any():
        raise ValueError("Hay unidades sin vecinos (fila de ceros) en la matriz W.")
    return proximidad / suma


def moran_i(valores: np.ndarray, W: np.ndarray, n_perm: int = 9999, semilla: int = 42):
    """I de Moran con p-valor por permutaciones.

    I = (n / S0) · (z'Wz) / (z'z), con z = valores − media y S0 = suma de todos los pesos.
    Valores positivos: los vecinos se parecen; cercanos a E[I] = −1/(n−1): independencia
    espacial. El p-valor (bilateral) compara |I − E[I]| con el de `n_perm` reordenamientos
    aleatorios de los valores entre las unidades, sin supuestos de normalidad, lo que importa con
    n tan pequeño.

    Args:
        valores (np.ndarray): Variable a evaluar (p. ej. residuos), shape (n,).
        W (np.ndarray): Matriz (n, n) de proximidad, ya estandarizada por filas.
        n_perm (int): Número de permutaciones.
        semilla (int): Semilla del generador aleatorio.

    Returns:
        dict: `I`, `esperado` (−1/(n−1)), `z_perm` (I estandarizado con la media y desviación de
            las permutaciones) y `p_valor`.

    Raises:
        ValueError: Si `valores` y `W` no tienen la misma dimensión.

    Example:
        >>> moran_i(residuos, estandarizar_filas(proximidad_knn(d, 3)))["p_valor"]
    """
    valores = np.asarray(valores, dtype=float)
    n = len(valores)
    if W.shape != (n, n):
        raise ValueError(f"W debe ser ({n}, {n}); se recibió {W.shape}.")
    z = valores - valores.mean()
    S0 = W.sum()
    denominador = z @ z
    observado = (n / S0) * (z @ W @ z) / denominador

    rng = np.random.default_rng(semilla)
    orden = np.argsort(rng.random((n_perm, n)), axis=1)
    Z = z[orden]
    simulados = (n / S0) * np.einsum("pi,ij,pj->p", Z, W, Z) / denominador

    esperado = -1.0 / (n - 1)
    extremos = np.sum(np.abs(simulados - esperado) >= abs(observado - esperado))
    return {
        "I": float(observado),
        "esperado": float(esperado),
        "z_perm": float((observado - simulados.mean()) / simulados.std(ddof=1)),
        "p_valor": float((1 + extremos) / (n_perm + 1)),
    }


def resumen_vecindad(distancias: np.ndarray, indices_origen, indices_destino) -> dict:
    """Distancia al dominio más cercano: describe qué tan útil es la información vecina.

    Args:
        distancias (np.ndarray): Matriz (m, m) de distancias en km.
        indices_origen (array-like): Posiciones de las unidades a describir (p. ej. objetivos).
        indices_destino (array-like): Posiciones de las unidades de referencia (dominios con
            encuesta).

    Returns:
        dict: `min_km`, `mediana_km`, `max_km` de la distancia al destino más cercano, y
            `n_a_50km`, `n_a_100km`: cuántos orígenes tienen un destino a ≤50 / ≤100 km.

    Example:
        >>> resumen_vecindad(d, range(23, 106), range(23))
    """
    cercana = distancias[np.ix_(list(indices_origen), list(indices_destino))].min(
        axis=1
    )
    return {
        "min_km": float(cercana.min()),
        "mediana_km": float(np.median(cercana)),
        "max_km": float(cercana.max()),
        "n_a_50km": int((cercana <= 50).sum()),
        "n_a_100km": int((cercana <= 100).sum()),
    }
