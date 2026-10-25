"""Sensibilidad de la estimación directa a la ventana temporal (comentario G7-B2).

Compara la tasa de desempleo directa de cada dominio (ciudad o ciudad A.M.) calculada con tres
ventanas que cierran en el mismo mes: un mes, un trimestre móvil y un año. Para cada dominio y
ventana reporta la muestra, la tasa, su error estándar y la cifra oficial del DANE con la que se
puede contrastar. **Nada de este módulo modifica el pipeline**: la estimación que usa el modelo
sigue saliendo de `preprocesamiento/estimacion_directa.py`.

Dos decisiones de construcción:

- **PEA = OCUPADO + DESOCUPADO.** En `tesis.geih_oro.mercado_laboral` la bandera `PEA` estaba
  mal en enero-marzo de 2018 (todas las personas de 15+ quedaban como PEA porque la unión con
  inactivos no encontraba a nadie), lo que bajaba la tasa de esos meses entre 3 y 8 puntos.
  G7-B5 lo corrigió y hoy la bandera coincide con la identidad PEA = ocupados + desocupados en
  los 12 meses. Se conserva esta definición, que no depende de la bandera; `reconciliacion_pea`
  deja la diferencia a la vista (hoy cero).
- **TD anual oficial reconstruida.** El anexo DANE no publica la TD anual por ciudad. Como las
  cifras trimestrales son promedios de tres meses, la TD anual es la razón de las sumas de los
  cuatro trimestres que no se pisan: TD = Σ_q DS_q / Σ_q PEA_q. `validar_formula_anual` comprueba
  la fórmula contra los totales anuales que sí se publican (13 y 10 ciudades).
"""

import itertools

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyspark.sql import functions as F

from preprocesamiento.shared.config import (
    CIUDADES_13_AM,
    CV_ACEPTABLE,
    CV_CONFIABLE,
    NOMBRE_TOTAL_10,
    NOMBRE_TOTAL_13_ANUAL,
    NOMBRE_TOTAL_23,
    TBL_DIM_DOMINIO,
    TBL_MERCADO_LABORAL,
    meses_ventana,
)

# Etiqueta de la ventana, cierres trimestrales y TD oficial del DANE: viven en el preprocesamiento
# porque la estimación directa y el modelo también las usan; se re-exportan para este notebook.
from preprocesamiento.shared.ventana import (  # noqa: F401
    TOLERANCIA_PP,
    cierres_trimestrales,
    etiqueta_ventana,
    td_dane_ventana,
)

# Edad mínima de la población en edad de trabajar (igual que estimacion_directa.py).
EDAD_MINIMA = 15

# Columnas de la tabla detalle, en el orden en que se escriben.
COLUMNAS_DETALLE = [
    "VENTANA",
    "N_MESES_VENTANA",
    "PERIODO",
    "CODIGO_DOMINIO",
    "NOMBRE_DOMINIO",
    "TIPO_DOMINIO",
    "N_PERSONAS_15MAS",
    "N_PEA",
    "N_DESOCUPADOS",
    "N_MESES",
    "PEA_EXPANDIDA",
    "TASA_DESEMPLEO_PCT",
    "SE_BOOTSTRAP_PCT",
    "IC_INF_PCT",
    "IC_SUP_PCT",
    "CV_PORCENTAJE",
    "TD_DANE",
    "DIF_PP",
]


def _condicion_meses(meses: list):
    """Arma la condición Spark que selecciona una lista de pares (año, mes).

    Args:
        meses (list[tuple[int, int]]): Pares `(año, mes)` de la ventana.

    Returns:
        pyspark.sql.Column: Condición booleana sobre las columnas `PER` y `MES`.
    """
    condicion = None
    for anio, mes in meses:
        c = (F.col("PER") == anio) & (F.col("MES") == mes)
        condicion = c if condicion is None else (condicion | c)
    return condicion


def preparar_datos_ventana(spark, per: int, mes: int, n_meses: int) -> tuple:
    """Filtra la GEIH a una ventana y arma la PEA por dominio y sus conteos muestrales.

    Replica el filtro de `estimacion_directa.py` (personas de 15+, meses de la ventana, INNER JOIN
    con la fila de la capital en `dim_dominio_geih`, `FEX := FEX_C18`, PER/MES = mes de cierre),
    con una diferencia: la PEA es `OCUPADO + DESOCUPADO == 1` (ver el docstring del módulo).

    Args:
        spark: SparkSession activa.
        per (int): Año del mes de cierre.
        mes (int): Mes de cierre, entre 1 y 12.
        n_meses (int): Número de meses de la ventana (1, 3 o 12).

    Returns:
        tuple: `(df_pea, conteos, meses_presentes)` donde
            - `df_pea` (pyspark DataFrame): personas de la PEA con `FEX`, `DESOCUPADO`, `PER`,
              `MES` (= cierre) y las columnas de dominio; entrada de `EstimacionDirecta.estimar`.
            - `conteos` (pd.DataFrame): por `CODIGO_DOMINIO`, `N_PERSONAS_15MAS`, `N_PEA`,
              `N_DESOCUPADOS`, `N_MESES` y `PEA_EXPANDIDA` (Σ FEX de la PEA / meses con datos).
            - `meses_presentes` (list[tuple[int, int]]): meses de la ventana con datos.

    Casos de uso:
        `df_pea, conteos, meses = preparar_datos_ventana(spark, 2018, 12, 12)` para el año 2018.
    """
    meses = meses_ventana(per, mes, n_meses)
    dominios_capital = (
        spark.table(TBL_DIM_DOMINIO)
        .filter(F.col("ES_CAPITAL"))
        .select("CODIGO_MUNICIPIO", "CODIGO_DOMINIO", "NOMBRE_DOMINIO", "TIPO_DOMINIO")
    )
    base = (
        spark.table(TBL_MERCADO_LABORAL)
        .filter((F.col("EDAD") >= EDAD_MINIMA) & _condicion_meses(meses))
        .join(dominios_capital, on="CODIGO_MUNICIPIO", how="inner")
        .withColumn("FEX", F.col("FEX_C18"))
        .withColumn("EN_PEA", F.col("OCUPADO") + F.col("DESOCUPADO"))
    )
    meses_presentes = sorted(
        (r["PER"], r["MES"]) for r in base.select("PER", "MES").distinct().collect()
    )
    n_presentes = max(len(meses_presentes), 1)

    conteos = (
        base.groupBy("CODIGO_DOMINIO")
        .agg(
            F.count("*").alias("N_PERSONAS_15MAS"),
            F.sum(F.when(F.col("EN_PEA") == 1, 1).otherwise(0)).alias("N_PEA"),
            F.sum(F.when(F.col("EN_PEA") == 1, F.col("DESOCUPADO")).otherwise(0)).alias(
                "N_DESOCUPADOS"
            ),
            F.countDistinct("PER", "MES").alias("N_MESES"),
            (
                F.sum(F.when(F.col("EN_PEA") == 1, F.col("FEX")).otherwise(0))
                / n_presentes
            ).alias("PEA_EXPANDIDA"),
        )
        .toPandas()
    )
    df_pea = (
        base.filter(F.col("EN_PEA") == 1)
        .withColumn("PER", F.lit(per))
        .withColumn("MES", F.lit(mes))
    )
    return df_pea, conteos, meses_presentes


def reconciliacion_pea(spark, meses: list) -> pd.DataFrame:
    """Compara, mes a mes, la bandera `PEA` de la tabla oro con `OCUPADO + DESOCUPADO`.

    Args:
        spark: SparkSession activa.
        meses (list[tuple[int, int]]): Pares `(año, mes)` a revisar.

    Returns:
        pd.DataFrame: Por `PER`, `MES`: `N_PERSONAS_15MAS`, `N_PEA_BANDERA` (Σ PEA),
            `N_OCUPADOS_MAS_DESOCUPADOS`, `N_DIFERENCIA` y `TD_BANDERA_PCT` / `TD_OC_DS_PCT`
            (tasas expandidas de los dominios GEIH con cada definición de PEA).

    Casos de uso:
        Comprobación posterior a G7-B5: antes de la corrección, en Ene-Mar 2018
        `N_DIFERENCIA` era igual a los inactivos y la tasa con la bandera quedaba subestimada;
        hoy la diferencia es cero en los 12 meses.
    """
    dominios_capital = (
        spark.table(TBL_DIM_DOMINIO)
        .filter(F.col("ES_CAPITAL"))
        .select("CODIGO_MUNICIPIO")
    )
    return (
        spark.table(TBL_MERCADO_LABORAL)
        .filter((F.col("EDAD") >= EDAD_MINIMA) & _condicion_meses(meses))
        .join(dominios_capital, on="CODIGO_MUNICIPIO", how="inner")
        .groupBy("PER", "MES")
        .agg(
            F.count("*").alias("N_PERSONAS_15MAS"),
            F.sum("PEA").alias("N_PEA_BANDERA"),
            F.sum(F.col("OCUPADO") + F.col("DESOCUPADO")).alias(
                "N_OCUPADOS_MAS_DESOCUPADOS"
            ),
            (
                100
                * F.sum(F.col("DESOCUPADO") * F.col("FEX_C18"))
                / F.sum(F.col("PEA") * F.col("FEX_C18"))
            ).alias("TD_BANDERA_PCT"),
            (
                100
                * F.sum(F.col("DESOCUPADO") * F.col("FEX_C18"))
                / F.sum((F.col("OCUPADO") + F.col("DESOCUPADO")) * F.col("FEX_C18"))
            ).alias("TD_OC_DS_PCT"),
        )
        .withColumn(
            "N_DIFERENCIA", F.col("N_PEA_BANDERA") - F.col("N_OCUPADOS_MAS_DESOCUPADOS")
        )
        .orderBy("PER", "MES")
        .toPandas()
    )


def validar_formula_anual(
    df_municipales: pd.DataFrame, df_anuales: pd.DataFrame, per: int
) -> pd.DataFrame:
    """Comprueba la reconstrucción de la TD anual contra los totales anuales publicados.

    Reconstruye el «Total 13 ciudades» sumando los cuatro trimestres de las 13 ciudades
    (`CIUDADES_13_AM`) y el «Total 10 ciudades» desde su propio bloque trimestral, y los compara
    con la hoja «Anuales» del anexo (`tesis.geih_bronce.datos_anuales`).

    Args:
        df_municipales (pd.DataFrame): `datos_municipales` (trimestre móvil por ciudad).
        df_anuales (pd.DataFrame): `datos_anuales` (columnas `ANIO`, `CONJUNTO`, `TASA_DESEMPLEO`).
        per (int): Año calendario a validar (ventana Ene-Dic).

    Returns:
        pd.DataFrame: Una fila por total con `CONJUNTO`, `TD_RECONSTRUIDA`, `TD_PUBLICADA`,
            `DIF_PP` y `COINCIDE` (|DIF_PP| ≤ `TOLERANCIA_PP`).

    Casos de uso:
        Si los dos totales coinciden, la misma fórmula da la TD anual oficial de cada ciudad.
    """
    cierres = cierres_trimestrales(per, 12, 12)
    claves = list(zip(df_municipales["ANIO"], df_municipales["MES"]))
    trimestres = df_municipales[[c in cierres for c in claves]]

    def razon(df):
        """TD = Σ DS / Σ PEA × 100 de un subconjunto (pd.DataFrame → float)."""
        return 100 * df["DESEMPLEADOS"].sum() / df["PEA"].sum()

    reconstruidas = {
        NOMBRE_TOTAL_13_ANUAL: razon(
            trimestres[trimestres["CIUDAD"].isin(CIUDADES_13_AM)]
        ),
        NOMBRE_TOTAL_10: razon(trimestres[trimestres["CIUDAD"] == NOMBRE_TOTAL_10]),
    }
    publicadas = df_anuales[df_anuales["ANIO"] == per].set_index("CONJUNTO")[
        "TASA_DESEMPLEO"
    ]
    filas = []
    for conjunto, td in reconstruidas.items():
        pub = float(publicadas.get(conjunto, np.nan))
        dif = td - pub
        filas.append(
            {
                "CONJUNTO": conjunto,
                "ANIO": per,
                "TD_RECONSTRUIDA": td,
                "TD_PUBLICADA": pub,
                "DIF_PP": dif,
                "COINCIDE": bool(abs(dif) <= TOLERANCIA_PP),
            }
        )
    return pd.DataFrame(filas)


def agregado_dominios(detalle_ventana: pd.DataFrame) -> float:
    """Tasa del conjunto de dominios: Σ PEA_EXPANDIDA · TD / Σ PEA_EXPANDIDA.

    Es exactamente el Hájek del conjunto (propiedad de benchmarking de los directos, Molina 2019,
    PDF 26) y se compara con el «Total 23 ciudades y A.M.» del DANE.

    Args:
        detalle_ventana (pd.DataFrame): Filas de una ventana con `PEA_EXPANDIDA` y
            `TASA_DESEMPLEO_PCT`.

    Returns:
        float: Tasa agregada, en %.
    """
    peso = detalle_ventana["PEA_EXPANDIDA"]
    return float((peso * detalle_ventana["TASA_DESEMPLEO_PCT"]).sum() / peso.sum())


def resumen_ventanas(detalle: pd.DataFrame, total_23_dane: dict) -> pd.DataFrame:
    """Resume por ventana la precisión, la muestra y la validación contra el DANE.

    Args:
        detalle (pd.DataFrame): Tabla detalle (una fila por ventana y dominio, `COLUMNAS_DETALLE`).
        total_23_dane (dict): Ventana → TD oficial del «Total 23 ciudades y A.M.» (None si no
            hay cifra publicada o reconstruible para esa ventana).

    Returns:
        pd.DataFrame: Una fila por ventana con número de dominios, mínimo y mediana de `N_PEA`,
            mínimo de `N_DESOCUPADOS`, mediana del SE, mediana y máximo del CV, dominios por
            categoría de CV, dominios con cifra DANE y cuántos la reproducen, y la tasa agregada
            frente al total 23 del DANE.

    Casos de uso:
        Tabla `tesis.preprocesamiento.resumen_ventana_temporal`.
    """
    filas = []
    for ventana, g in detalle.groupby("VENTANA", sort=False):
        cv = g["CV_PORCENTAJE"]
        con_dane = g["TD_DANE"].notna()
        agregado = agregado_dominios(g)
        total = total_23_dane.get(ventana)
        filas.append(
            {
                "VENTANA": ventana,
                "N_MESES_VENTANA": int(g["N_MESES_VENTANA"].iloc[0]),
                "PERIODO": g["PERIODO"].iloc[0],
                "N_DOMINIOS": len(g),
                "N_PEA_MIN": int(g["N_PEA"].min()),
                "N_PEA_MEDIANA": float(g["N_PEA"].median()),
                "N_DESOCUPADOS_MIN": int(g["N_DESOCUPADOS"].min()),
                "SE_MEDIANA_PP": float(g["SE_BOOTSTRAP_PCT"].median()),
                "CV_MEDIANA": float(cv.median()),
                "CV_MAXIMO": float(cv.max()),
                "N_CONFIABLES": int((cv < CV_CONFIABLE).sum()),
                "N_ACEPTABLES": int(((cv >= CV_CONFIABLE) & (cv < CV_ACEPTABLE)).sum()),
                "N_NO_CONFIABLES": int((cv >= CV_ACEPTABLE).sum()),
                "N_CON_CIFRA_DANE": int(con_dane.sum()),
                "N_COINCIDEN_DANE": int(
                    (g.loc[con_dane, "DIF_PP"].abs() <= TOLERANCIA_PP).sum()
                ),
                "TD_AGREGADA_PCT": agregado,
                "TD_TOTAL_23_DANE": np.nan if total is None else float(total),
                "DIF_AGREGADO_PP": np.nan if total is None else agregado - float(total),
            }
        )
    return pd.DataFrame(filas)


def comparar_ventanas(detalle: pd.DataFrame) -> pd.DataFrame:
    """Compara pares de ventanas: concordancia de la tasa y ganancia de precisión.

    La razón de errores estándar se contrasta con la que predice el tamaño de muestra,
    √(n_B / n_A): si se parecen, la ganancia de precisión viene de la muestra adicional y no de un
    cambio en el nivel de la tasa.

    Args:
        detalle (pd.DataFrame): Tabla detalle con `VENTANA`, `CODIGO_DOMINIO`,
            `TASA_DESEMPLEO_PCT`, `SE_BOOTSTRAP_PCT` y `N_PEA`.

    Returns:
        pd.DataFrame: Una fila por par (A, B) con la correlación de Pearson de la tasa entre
            dominios, la diferencia absoluta media y máxima (pp), la mediana de SE_A/SE_B y la
            mediana de √(N_PEA_B/N_PEA_A).

    Casos de uso:
        `comparar_ventanas(detalle)` → ¿cambia el ordenamiento de los dominios al pasar del
        trimestre al año? ¿cuánto baja el error?
    """
    ancho = detalle.pivot(
        index="CODIGO_DOMINIO",
        columns="VENTANA",
        values=["TASA_DESEMPLEO_PCT", "SE_BOOTSTRAP_PCT", "N_PEA"],
    )
    ventanas = list(dict.fromkeys(detalle["VENTANA"]))
    filas = []
    for a, b in itertools.combinations(ventanas, 2):
        td_a, td_b = ancho["TASA_DESEMPLEO_PCT"][a], ancho["TASA_DESEMPLEO_PCT"][b]
        dif = (td_a - td_b).abs()
        filas.append(
            {
                "VENTANA_A": a,
                "VENTANA_B": b,
                "CORRELACION_TD": float(np.corrcoef(td_a, td_b)[0, 1]),
                "DIF_ABS_MEDIA_PP": float(dif.mean()),
                "DIF_ABS_MAX_PP": float(dif.max()),
                "RAZON_SE_MEDIANA": float(
                    (
                        ancho["SE_BOOTSTRAP_PCT"][a] / ancho["SE_BOOTSTRAP_PCT"][b]
                    ).median()
                ),
                "RAZON_SE_ESPERADA": float(
                    np.sqrt(ancho["N_PEA"][b] / ancho["N_PEA"][a]).median()
                ),
            }
        )
    return pd.DataFrame(filas)


def figura_ventanas(detalle: pd.DataFrame, orden_por: str = "TRIMESTRE"):
    """Tasa con su IC 95 % y CV por dominio, con las ventanas lado a lado.

    Args:
        detalle (pd.DataFrame): Tabla detalle (`VENTANA`, `NOMBRE_DOMINIO`,
            `TASA_DESEMPLEO_PCT`, `IC_INF_PCT`, `IC_SUP_PCT`, `CV_PORCENTAJE`, `TD_DANE`).
        orden_por (str): Ventana por cuya tasa se ordenan los dominios. Por defecto «TRIMESTRE».

    Returns:
        matplotlib.figure.Figure: Panel izquierdo con la tasa (punto) y el IC (barra) de cada
            ventana, y la cifra DANE (×) cuando existe; panel derecho con el CV y las líneas de
            los umbrales de confiabilidad.

    Casos de uso:
        `fig = figura_ventanas(detalle); guardar_figura(fig, "ventana_sensibilidad", VOLUMEN_FIGURAS)`.
    """
    ventanas = list(dict.fromkeys(detalle["VENTANA"]))
    orden = (
        detalle[detalle["VENTANA"] == orden_por]
        .sort_values("TASA_DESEMPLEO_PCT")["NOMBRE_DOMINIO"]
        .tolist()
    )
    posicion = {nombre: i for i, nombre in enumerate(orden)}
    desfase = np.linspace(-0.25, 0.25, len(ventanas))
    colores = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    fig, (ax_td, ax_cv) = plt.subplots(
        1,
        2,
        figsize=(13, 0.38 * len(orden) + 1.5),
        sharey=True,
        gridspec_kw={"width_ratios": [3, 2]},
    )
    for k, ventana in enumerate(ventanas):
        g = detalle[detalle["VENTANA"] == ventana]
        y = g["NOMBRE_DOMINIO"].map(posicion) + desfase[k]
        ax_td.errorbar(
            g["TASA_DESEMPLEO_PCT"],
            y,
            xerr=[
                g["TASA_DESEMPLEO_PCT"] - g["IC_INF_PCT"],
                g["IC_SUP_PCT"] - g["TASA_DESEMPLEO_PCT"],
            ],
            fmt="o",
            ms=4,
            capsize=2,
            color=colores[k],
            label=f"{ventana} ({g['PERIODO'].iloc[0]})",
        )
        con_dane = g["TD_DANE"].notna()
        ax_td.scatter(
            g.loc[con_dane, "TD_DANE"],
            y[con_dane],
            marker="x",
            s=22,
            color="black",
            zorder=3,
        )
        ax_cv.scatter(g["CV_PORCENTAJE"], y, s=18, color=colores[k])
    ax_td.scatter([], [], marker="x", color="black", label="DANE")
    ax_td.set_yticks(range(len(orden)))
    ax_td.set_yticklabels(orden)
    ax_td.set_xlabel("Tasa de desempleo (%) e IC 95 %")
    ax_td.legend(loc="lower right", fontsize=8)
    for umbral in (CV_CONFIABLE, CV_ACEPTABLE):
        ax_cv.axvline(umbral, color="grey", linestyle="--", linewidth=1)
    ax_cv.set_xlabel("Coeficiente de variación (%)")
    fig.tight_layout()
    return fig


def interpretar_ventanas(resumen: pd.DataFrame, comparacion: pd.DataFrame) -> str:
    """Lectura de la sensibilidad a la ventana temporal, calculada desde las tablas.

    Args:
        resumen (pd.DataFrame): Salida de `resumen_ventanas`.
        comparacion (pd.DataFrame): Salida de `comparar_ventanas`.

    Returns:
        str: Interpretación lista para imprimir junto a la figura.

    Casos de uso:
        `print(interpretar_ventanas(resumen, comparacion))` al final del notebook.
    """
    lineas = ["INTERPRETACIÓN:"]
    for _, r in resumen.iterrows():
        validacion = (
            f"reproduce la cifra DANE en {r['N_COINCIDEN_DANE']} de {r['N_CON_CIFRA_DANE']} dominios"
            if r["N_CON_CIFRA_DANE"]
            else "sin cifra DANE por dominio contra la cual validar"
        )
        lineas.append(
            f"  {r['VENTANA']} ({r['PERIODO']}): PEA muestral mínima {r['N_PEA_MIN']:,} y mediana "
            f"{r['N_PEA_MEDIANA']:,.0f}; desocupados muestrales mínimo {r['N_DESOCUPADOS_MIN']:,}. "
            f"CV mediano {r['CV_MEDIANA']:.1f} % (máx. {r['CV_MAXIMO']:.1f} %): "
            f"{r['N_CONFIABLES']} confiables, {r['N_ACEPTABLES']} aceptables, "
            f"{r['N_NO_CONFIABLES']} no confiables. {validacion.capitalize()}."
        )
    for _, c in comparacion.iterrows():
        lineas.append(
            f"  {c['VENTANA_A']} vs {c['VENTANA_B']}: correlación de la tasa entre dominios "
            f"r = {c['CORRELACION_TD']:.2f}; diferencia media {c['DIF_ABS_MEDIA_PP']:.2f} pp "
            f"(máx. {c['DIF_ABS_MAX_PP']:.2f}); el SE de {c['VENTANA_A']} es "
            f"{c['RAZON_SE_MEDIANA']:.2f} veces el de {c['VENTANA_B']} (la muestra predice "
            f"{c['RAZON_SE_ESPERADA']:.2f})."
        )
    lineas.append(
        "  Lectura: el diseño GEIH solo hace representativa por ciudad la ventana trimestral o "
        "mayor (GEIH v9, PDF 9), así que el mes queda como referencia de precisión. Entre el "
        "trimestre y el año, la elección se apoya en la ganancia de precisión de esta tabla, en "
        "la validación contra el DANE y en que las covariables de TerriData son anuales con corte "
        "a diciembre."
    )
    return "\n".join(lineas)
