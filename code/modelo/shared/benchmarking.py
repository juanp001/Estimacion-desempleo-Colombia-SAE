"""Benchmarking (ajuste de consistencia) de las estimaciones del modelo Fay-Herriot.

Qué es
------
Las estimaciones basadas en modelos no cumplen, en general, la propiedad de *benchmarking*: al
agregarlas no reproducen la estimación directa de un territorio mayor que sí es confiable. Los
estimadores directos (Horvitz-Thompson, Hájek) la cumplen por construcción (Molina, 2019, CEPAL,
Estudios Estadísticos 97, PDF 26), pero los predictores basados en modelos «requieren un reajuste
para verificar la propiedad benchmarking» (Molina, 2019, PDF 78). El benchmarking hace ese reajuste.

Por qué se hace
---------------
1. Coherencia con las cifras oficiales. El DANE ajusta sus estimaciones municipales de áreas
   pequeñas para que, «al agregar las estimaciones municipales ponderadas por el tamaño
   poblacional de cada municipio, se reproduzcan exactamente las estimaciones departamentales,
   de ciudades principales y nacional» (DANE, 2025, Nota metodológica SAE de bienestar municipal,
   pobreza monetaria con la GEIH, PDF 25; también PDF 8 y 33). Es la práctica de las oficinas de
   estadística de la región: INE Chile, ENUSC 2018 (PDF 22-23); Ministerio de Desarrollo Social de
   Chile, pobreza comunal 2016 (PDF 6) y Casen 2024 (PDF 7).
2. Protección frente a errores de especificación. El benchmarking «puede proteger las
   estimaciones de posibles errores de especificación del modelo y reducir la sobre-contracción»
   de los estimadores de áreas pequeñas (Benedetti et al., 2024, Int. Stat. Review, p. 159, con
   cita a Pfeffermann y Tiller, 2006).
3. Yumbo. La GEIH pública no identifica el municipio dentro del área metropolitana, así que la
   muestra de Cali y Yumbo solo da la tasa de Cali A.M. Hay tres caminos: (a) el modelo anidado
   dominio-subdominio (Morales et al., 2021, p. 462), que necesita estimaciones directas por
   municipio y por tanto no es aplicable; (b) asignar a Yumbo la tasa de Cali A.M., que es el
   estimador sintético básico y es sesgado si Yumbo difiere de Cali (Morales et al., 2021, p. 42);
   (c) lo que hace el DANE: dar a cada municipio una estimación propia con el modelo y ajustarla
   para que el conjunto reproduzca la tasa de la ciudad A.M. Se sigue (c).

Cómo se hace: ajuste de razón de Fay y Herriot (1979)
-----------------------------------------------------
Para un territorio R con valor de referencia θ_R y unidades d ∈ R con estimaciones θ̂_d y pesos w_d:

    λ_R = θ_R / ( Σ_{d∈R} w_d θ̂_d / Σ_{d∈R} w_d ),      θ̂_d^B = λ_R · θ̂_d.

Es el «factor de consistencia» de la ENUSC 2018 (INE Chile, PDF 23), que sigue el ajuste propuesto
por Fay y Herriot (1979); el mismo cociente «estimación regional / suma de estimaciones comunales»
usan Chile pobreza 2016 (PDF 6) y Casen 2024 (PDF 7). Por construcción:
(i) Σ w_d θ̂_d^B / Σ w_d = θ_R exactamente; (ii) todas las unidades de R se multiplican por el mismo
λ_R, así que se conservan sus razones y su orden; (iii) el ajuste es proporcional, de modo que
nunca cambia el signo de una tasa. Como diagnóstico, «si el modelo es adecuado, el factor de ajuste
estará en torno a uno» (ENUSC, PDF 23): un λ alejado de 1 señala que el modelo no reproduce bien
ese territorio.

Los dos niveles del proyecto (en cascada, como el DANE: municipio → ciudad → total)
---------------------------------------------------------------------------------
Nivel 1: los 23 dominios (ciudades y ciudades A.M.) → «Total 23 ciudades y A.M.»
    * Unidades: el EBLUP de cada dominio.
    * Pesos: la PEA expandida del dominio (Σ de factores de expansión de la PEA, promedio del
      trimestre; ``PEA_EXPANDIDA`` de estimacion_directa). La tasa de desempleo de un conjunto de
      dominios es el promedio de sus tasas ponderado por la PEA.
    * Valor de referencia: la estimación directa del conjunto, Σ PEA_d·TD_d / Σ PEA_d. Por la
      propiedad de benchmarking del Hájek (Molina, 2019, PDF 26) es exactamente la estimación
      directa de las 23 ciudades juntas, un dominio que la GEIH publica cada trimestre (Metodología
      GEIH v9, PDF 10) y que coincide con la cifra oficial del DANE (anexo «Mercado laboral según
      proyecciones CNPV 2018», Total 23 ciudades y A.M.: 10.3251 % en Oct-Dic 2018). El notebook
      lo compara con ``datos_municipales`` y se detiene si difiere.
Nivel 2: municipios de un dominio A.M. → valor ya ajustado (nivel 1) de su dominio
    * Unidades: la predicción sintética x_m'β̂ de cada municipio (Cali y Yumbo en Cali A.M.).
    * Pesos: la población de 15 años y más del municipio (suma de los grupos quinquenales de edad de
      TerriData), aproximación de la PEA municipal, que no se publica. Es la PET de la serie GEIH con
      proyecciones CNPV 2018 (15 años y más, DANE, actualización de la serie 2007-2021, PDF 30). Es el mismo peso con el que se agregaron las covariables del
      dominio (preprocesamiento/shared/agregacion_dominios.py). Con pesos iguales, el promedio
      ponderado de los sintéticos municipales es exactamente el sintético del dominio,
      Σ w_m x_m'β̂ / Σ w_m = x̄_D'β̂, así que λ_D = θ_D / x̄_D'β̂: λ − 1 mide cuánto se separa el
      dominio de su predicción sintética (su efecto aleatorio más el error de muestreo).
    * Valor de referencia: el EBLUP ajustado del dominio (nivel 1), que es la cifra que se publica
      para Cali A.M. Así municipio, ciudad A.M. y total quedan coherentes entre sí.

Qué no se ajusta y por qué
--------------------------
Los municipios objetivo que no pertenecen a un dominio con estimación directa (81 de Cauca y Valle)
quedan con la predicción sintética pura. El ajuste exige un valor de referencia confiable que
contenga a las unidades: la ENUSC ajusta a regiones «cuyos tamaños muestrales se establecieron
para garantizar» la calidad de la estimación directa (PDF 22), y el DANE a estimaciones directas
oficiales (PDF 8). El único territorio de la GEIH que los contiene es el departamento, que solo es
representativo con datos anuales (Metodología GEIH v9, PDF 9), mientras que el proyecto estima
trimestres; además el proyecto decidió no usar los registros sin ``AREA`` (resto de cabeceras y
zona rural). Las 16 ciudades de un solo municipio tampoco tienen nivel 2: ajustarlas a su propia
estimación directa devolvería la directa y anularía la ganancia del Fay-Herriot.

Incertidumbre
-------------
Se trata λ como fijo: RMSE^B = λ · RMSE, y por tanto el CV no cambia (CV^B = RMSE^B / θ^B = CV).
Es una aproximación: ignora la variabilidad de λ, que depende de la estimación directa del
territorio de referencia. Con dominios de CV cercano al 5 % y λ cercano a 1 su efecto es pequeño.

Cómo se verifica (``verificar_benchmark``)
------------------------------------------
Siguiendo la presentación del DANE (tabla de diferencias antes del ajuste, PDF 19, y diferencias
prácticamente nulas después, PDF 25), por cada territorio de referencia se calcula el agregado
ponderado antes y después y se comprueba que: (a) después del ajuste el agregado iguala al valor
de referencia; (b) todas las unidades se multiplicaron por el mismo λ (razones conservadas);
(c) las tasas siguen en [0, 100]; (d) las unidades son exactamente los miembros del territorio
(un municipio ausente haría incorrecto el reparto). Si |λ − 1| supera el umbral se imprime un aviso.
"""

import numpy as np
import pandas as pd


def promedio_ponderado(valores, pesos) -> float:
    """Promedio ponderado Σ w·θ / Σ w.

    Args:
        valores (array-like): Estimaciones θ de las unidades (tasas en %).
        pesos (array-like): Pesos w ≥ 0 de las unidades, con suma positiva.

    Returns:
        float: Promedio ponderado de los valores.

    Raises:
        ValueError: Si los largos difieren, hay valores o pesos no finitos, algún peso es
            negativo o la suma de pesos no es positiva.

    Casos de uso:
        Agregado de los EBLUP de los dominios (pesos = PEA expandida) o de las predicciones
        sintéticas de los municipios de un A.M. (pesos = población de 15 años y más).

    Example:
        >>> promedio_ponderado([10.0, 20.0], [3.0, 1.0])
        12.5
    """
    valores = np.asarray(valores, dtype=float)
    pesos = np.asarray(pesos, dtype=float)
    if valores.shape != pesos.shape:
        raise ValueError("valores y pesos deben tener el mismo largo")
    if not (np.isfinite(valores).all() and np.isfinite(pesos).all()):
        raise ValueError("valores y pesos deben ser finitos")
    if (pesos < 0).any() or pesos.sum() <= 0:
        raise ValueError("los pesos deben ser no negativos y sumar más de cero")
    return float((pesos * valores).sum() / pesos.sum())


def factor_razon(estimaciones, pesos, objetivo: float) -> float:
    """Factor de consistencia de Fay y Herriot (1979): λ = objetivo / agregado ponderado.

    Args:
        estimaciones (array-like): Estimaciones θ̂_d de las unidades del territorio.
        pesos (array-like): Pesos w_d de las unidades.
        objetivo (float): Valor de referencia θ_R del territorio que las contiene.

    Returns:
        float: λ tal que Σ w_d λθ̂_d / Σ w_d = objetivo.

    Raises:
        ValueError: Si el agregado ponderado no es positivo (el ajuste de razón no estaría
            definido o cambiaría el signo de las tasas) o el objetivo no es finito.

    Casos de uso:
        Base de ``benchmark_nivel1`` y ``benchmark_nivel2``.

    Example:
        >>> factor_razon([10.0, 20.0], [3.0, 1.0], 15.0)
        1.2
    """
    if not np.isfinite(objetivo):
        raise ValueError("el valor de referencia del benchmarking no es finito")
    agregado = promedio_ponderado(estimaciones, pesos)
    if agregado <= 0:
        raise ValueError(
            f"agregado ponderado = {agregado}: el ajuste de razón exige un agregado positivo"
        )
    return objetivo / agregado


def benchmark_nivel1(estimaciones, pesos, objetivo: float) -> tuple:
    """Ajusta las estimaciones de los dominios para que reproduzcan el total de referencia.

    Args:
        estimaciones (array-like): EBLUP de los dominios.
        pesos (array-like): PEA expandida de cada dominio.
        objetivo (float): Tasa directa del conjunto de los dominios (Total 23 ciudades y A.M.).

    Returns:
        tuple[np.ndarray, float]: (estimaciones ajustadas λ·θ̂_d, factor λ).

    Raises:
        ValueError: Propagado de ``factor_razon``.

    Casos de uso:
        En ``fay_herriot.py`` sobre los EBLUP del modelo ganador, antes de la predicción
        sintética.

    Example:
        >>> ajustadas, lam = benchmark_nivel1([10.0, 20.0], [3.0, 1.0], 15.0)
        >>> ajustadas.tolist(), lam
        ([12.0, 24.0], 1.2)
    """
    lam = factor_razon(estimaciones, pesos, objetivo)
    return np.asarray(estimaciones, dtype=float) * lam, lam


def benchmark_nivel2(
    df: pd.DataFrame,
    col_pred: str,
    col_peso: str,
    col_padre: str,
    objetivos: dict,
) -> pd.DataFrame:
    """Ajusta las predicciones municipales al valor de su dominio padre, un λ por padre.

    Args:
        df (pd.DataFrame): Una fila por municipio objetivo.
        col_pred (str): Columna con la predicción sintética x_m'β̂.
        col_peso (str): Columna con el peso del municipio (población de 15 años y más).
        col_padre (str): Columna con el código del dominio padre (NULL si no tiene).
        objetivos (dict[str, float]): Valor de referencia por código de dominio padre (el
            EBLUP ajustado en el nivel 1).

    Returns:
        pd.DataFrame: Copia de ``df`` con ``LAMBDA_N2`` (1 en las filas sin padre),
            ``PRED_BENCHMARK`` (= λ·pred) y ``BENCHMARK`` (True si se ajustó).

    Raises:
        ValueError: Si un padre no tiene valor de referencia, si un municipio con padre no
            tiene peso o si el agregado de un padre no es positivo.

    Casos de uso:
        En ``fay_herriot.py`` para Cali y Yumbo (padre Cali A.M.). Los demás municipios
        objetivo pasan sin cambio.

    Example:
        >>> d = pd.DataFrame({"pred": [10.0, 20.0, 7.0], "w": [3.0, 1.0, 5.0],
        ...                   "padre": ["A", "A", None]})
        >>> benchmark_nivel2(d, "pred", "w", "padre", {"A": 15.0})["PRED_BENCHMARK"].tolist()
        [12.0, 24.0, 7.0]
    """
    salida = df.copy()
    salida["LAMBDA_N2"] = 1.0
    salida["BENCHMARK"] = False

    padres = salida[col_padre].dropna().unique()
    faltan = sorted(set(padres) - set(objetivos))
    if faltan:
        raise ValueError(f"Dominios padre sin valor de referencia: {faltan}")

    for padre in padres:
        filas = salida[col_padre] == padre
        if salida.loc[filas, col_peso].isna().any():
            raise ValueError(f"Municipios del dominio {padre} sin peso en {col_peso}")
        lam = factor_razon(
            salida.loc[filas, col_pred], salida.loc[filas, col_peso], objetivos[padre]
        )
        salida.loc[filas, "LAMBDA_N2"] = lam
        salida.loc[filas, "BENCHMARK"] = True

    salida["PRED_BENCHMARK"] = salida[col_pred] * salida["LAMBDA_N2"]
    return salida


def verificar_benchmark(
    df: pd.DataFrame,
    col_grupo: str,
    col_id: str,
    col_peso: str,
    col_antes: str,
    col_despues: str,
    objetivos: dict,
    miembros_esperados: dict = None,
    tasa_min: float = 0.0,
    tasa_max: float = 100.0,
    tolerancia: float = 1e-8,
    umbral_lambda: float = 0.20,
) -> pd.DataFrame:
    """Verifica un ajuste de razón y devuelve la tabla de diferencias antes y después.

    Comprueba, por cada territorio de referencia: (a) que el agregado ponderado después del
    ajuste iguala al valor de referencia; (b) que todas las unidades se multiplicaron por el
    mismo λ (razones y orden conservados); (c) que las tasas ajustadas están en
    [tasa_min, tasa_max]; (d) si se dan ``miembros_esperados``, que las unidades son exactamente
    esos miembros. Imprime un aviso si |λ − 1| > ``umbral_lambda`` (ENUSC 2018, PDF 23: con un
    modelo adecuado λ está en torno a uno).

    Args:
        df (pd.DataFrame): Una fila por unidad ajustada.
        col_grupo (str): Columna con el territorio de referencia de cada unidad.
        col_id (str): Columna que identifica la unidad (código de dominio o de municipio).
        col_peso (str): Columna de pesos del ajuste.
        col_antes (str): Estimación antes del ajuste.
        col_despues (str): Estimación después del ajuste.
        objetivos (dict[str, float]): Valor de referencia por territorio.
        miembros_esperados (dict[str, set] | None): Unidades que debe tener cada territorio.
        tasa_min (float): Límite inferior admisible de una tasa.
        tasa_max (float): Límite superior admisible de una tasa.
        tolerancia (float): Diferencia máxima admitida entre agregado y referencia (pp).
        umbral_lambda (float): Desvío de λ respecto de 1 a partir del cual se avisa.

    Returns:
        pd.DataFrame: Una fila por territorio con ``TERRITORIO``, ``N_UNIDADES``,
            ``REFERENCIA``, ``AGREGADO_ANTES``, ``DIF_ANTES_PP``, ``AGREGADO_DESPUES``,
            ``DIF_DESPUES_PP``, ``LAMBDA``, ``CONSISTENTE``, ``RAZONES_CONSERVADAS``,
            ``EN_RANGO``, ``MIEMBROS_COMPLETOS`` y ``OK``.

    Raises:
        ValueError: Si alguna comprobación (a)-(d) falla, con la lista de territorios.

    Casos de uso:
        Celda «Verificación del benchmarking» de ``fay_herriot.py``, una vez por nivel.

    Example:
        >>> d = pd.DataFrame({"g": ["A", "A"], "id": ["x", "y"], "w": [3.0, 1.0],
        ...                   "antes": [10.0, 20.0], "despues": [12.0, 24.0]})
        >>> bool(verificar_benchmark(d, "g", "id", "w", "antes", "despues", {"A": 15.0})["OK"].all())
        True
    """
    filas = []
    for grupo, sub in df.groupby(col_grupo, sort=True):
        referencia = float(objetivos[grupo])
        antes = promedio_ponderado(sub[col_antes], sub[col_peso])
        despues = promedio_ponderado(sub[col_despues], sub[col_peso])
        razones = (sub[col_despues] / sub[col_antes]).to_numpy(dtype=float)
        lam = float(razones[0])
        miembros_ok = (
            True
            if miembros_esperados is None
            else set(sub[col_id]) == set(miembros_esperados.get(grupo, set()))
        )
        fila = {
            "TERRITORIO": grupo,
            "N_UNIDADES": len(sub),
            "REFERENCIA": referencia,
            "AGREGADO_ANTES": antes,
            "DIF_ANTES_PP": antes - referencia,
            "AGREGADO_DESPUES": despues,
            "DIF_DESPUES_PP": despues - referencia,
            "LAMBDA": lam,
            "CONSISTENTE": abs(despues - referencia) <= tolerancia,
            "RAZONES_CONSERVADAS": bool(np.allclose(razones, lam, rtol=0, atol=1e-12)),
            "EN_RANGO": bool(
                ((sub[col_despues] >= tasa_min) & (sub[col_despues] <= tasa_max)).all()
            ),
            "MIEMBROS_COMPLETOS": miembros_ok,
        }
        fila["OK"] = (
            fila["CONSISTENTE"]
            and fila["RAZONES_CONSERVADAS"]
            and fila["EN_RANGO"]
            and fila["MIEMBROS_COMPLETOS"]
        )
        filas.append(fila)
        if abs(lam - 1) > umbral_lambda:
            print(
                f"⚠ AVISO: λ = {lam:.4f} en {grupo}: el modelo se aleja más de "
                f"{umbral_lambda:.0%} del valor de referencia en ese territorio."
            )

    tabla = pd.DataFrame(filas)
    fallas = tabla.loc[~tabla["OK"], "TERRITORIO"].tolist()
    if fallas:
        raise ValueError(f"El benchmarking no pasó la verificación en: {fallas}")
    return tabla
