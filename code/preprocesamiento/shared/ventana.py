"""Ventana temporal de la estimación directa (G7-B2): etiquetas y cifras oficiales del DANE.

La estimación directa se calcula sobre una ventana de `n_meses` que cierra en `(per, mes)`: el año
calendario (12 meses con cierre en diciembre, ventana por defecto) o el trimestre móvil (3). Este
módulo da la etiqueta legible de la ventana y la tasa de desempleo oficial con la que se valida.

**TD anual oficial reconstruida.** El anexo DANE «Mercado laboral según proyecciones CNPV 2018» no
publica la TD anual por ciudad (`datos_anuales` solo trae los totales de 13 y de 10 ciudades). Como
las cifras trimestrales son promedios de tres meses, la TD anual es la razón de las sumas de los
cuatro trimestres que no se pisan: TD = Σ_q DS_q / Σ_q PEA_q. La fórmula reproduce los dos totales
anuales publicados (`analisis/shared/ventana_temporal.validar_formula_anual`, ≈ 1e-5 pp).

Lo usan `estimacion_directa.py` y `adicion_covariables.py` (validación y auditoría), el benchmarking
de nivel 1 de `modelo/fay_herriot.py` (Total 23 de la ventana) y la sensibilidad de
`analisis/sensibilidad_ventana_temporal.py`.
"""

import pandas as pd

from preprocesamiento.shared.config import MESES_TRIMESTRE, meses_ventana

# Diferencia máxima, en puntos porcentuales, para dar por reproducida una cifra del DANE.
TOLERANCIA_PP = 0.01


def etiqueta_ventana(per: int, mes: int, n_meses: int) -> str:
    """Etiqueta legible de una ventana de `n_meses` que cierra en `(per, mes)`.

    Args:
        per (int): Año del mes de cierre.
        mes (int): Mes de cierre, entre 1 y 12.
        n_meses (int): Número de meses de la ventana.

    Returns:
        str: «Dic 2018», «Oct-Dic 2018», «Ene-Dic 2018» o, si cruza el año, «Nov 2018-Ene 2019».

    Casos de uso:
        Columna `PERIODO` de la tabla de sensibilidad.

        >>> etiqueta_ventana(2018, 12, 1)
        'Dic 2018'
        >>> etiqueta_ventana(2018, 12, 12)
        'Ene-Dic 2018'
        >>> etiqueta_ventana(2019, 1, 3)
        'Nov 2018-Ene 2019'
    """
    nombres = "Ene Feb Mar Abr May Jun Jul Ago Sep Oct Nov Dic".split()
    meses = meses_ventana(per, mes, n_meses)
    (a_ini, m_ini), (a_fin, m_fin) = meses[0], meses[-1]
    if n_meses == 1:
        return f"{nombres[m_fin - 1]} {a_fin}"
    if a_ini == a_fin:
        return f"{nombres[m_ini - 1]}-{nombres[m_fin - 1]} {a_fin}"
    return f"{nombres[m_ini - 1]} {a_ini}-{nombres[m_fin - 1]} {a_fin}"


def cierres_trimestrales(per: int, mes: int, n_meses: int) -> list:
    """Meses de cierre de los trimestres que no se pisan y cubren la ventana.

    Args:
        per (int): Año del mes de cierre de la ventana.
        mes (int): Mes de cierre de la ventana.
        n_meses (int): Número de meses de la ventana; debe ser múltiplo de 3.

    Returns:
        list[tuple[int, int]]: Pares `(año, mes)` de cierre, en orden cronológico.

    Raises:
        ValueError: Si `n_meses` no es múltiplo de 3.

    Casos de uso:
        >>> cierres_trimestrales(2018, 12, 12)
        [(2018, 3), (2018, 6), (2018, 9), (2018, 12)]
        >>> cierres_trimestrales(2018, 12, 3)
        [(2018, 12)]
    """
    if n_meses % MESES_TRIMESTRE:
        raise ValueError(f"n_meses={n_meses} no es múltiplo de {MESES_TRIMESTRE}")
    meses = meses_ventana(per, mes, n_meses)
    return meses[MESES_TRIMESTRE - 1 :: MESES_TRIMESTRE]


def td_dane_ventana(
    df_municipales: pd.DataFrame, per: int, mes: int, n_meses: int
) -> pd.DataFrame:
    """Tasa de desempleo oficial del DANE por ciudad para una ventana.

    - Trimestre: la tasa publicada del trimestre móvil que cierra en `(per, mes)`.
    - Múltiplo de 3 mayor que 3 (el año): Σ DESEMPLEADOS / Σ PEA de los trimestres que no se pisan
      (`cierres_trimestrales`); solo ciudades con todos los trimestres.
    - Un mes: el anexo no publica cifras mensuales por ciudad; devuelve una tabla vacía.

    Args:
        df_municipales (pd.DataFrame): `tesis.geih_bronce.datos_municipales` (columnas `ANIO`,
            `MES`, `CIUDAD`, `TASA_DESEMPLEO`, `PEA`, `DESEMPLEADOS`).
        per (int): Año del mes de cierre.
        mes (int): Mes de cierre.
        n_meses (int): Número de meses de la ventana.

    Returns:
        pd.DataFrame: Columnas `CIUDAD` y `TD_DANE` (en %). Incluye los agregados del anexo
            («Total 10 ciudades», «Total 23 ciudades y A.M.»).

    Casos de uso:
        Validación de la ventana anual: `td_dane_ventana(df_mun, 2018, 12, 12)`.

        >>> mun = pd.DataFrame({"ANIO": [2018] * 5, "MES": [3, 6, 9, 11, 12],
        ...     "CIUDAD": ["Popayán"] * 5, "TASA_DESEMPLEO": [10.0, 12.0, 8.0, 9.0, 10.0],
        ...     "PEA": [100.0, 100.0, 100.0, 100.0, 200.0],
        ...     "DESEMPLEADOS": [10.0, 12.0, 8.0, 9.0, 20.0]})
        >>> td_dane_ventana(mun, 2018, 12, 3).values.tolist()
        [['Popayán', 10.0]]
        >>> float(td_dane_ventana(mun, 2018, 12, 12)["TD_DANE"].iloc[0])
        10.0
        >>> td_dane_ventana(mun, 2018, 12, 1).empty
        True
    """
    vacio = pd.DataFrame(columns=["CIUDAD", "TD_DANE"])
    if n_meses % MESES_TRIMESTRE:
        return vacio
    if n_meses == MESES_TRIMESTRE:
        filtro = (df_municipales["ANIO"] == per) & (df_municipales["MES"] == mes)
        return (
            df_municipales.loc[filtro, ["CIUDAD", "TASA_DESEMPLEO"]]
            .rename(columns={"TASA_DESEMPLEO": "TD_DANE"})
            .reset_index(drop=True)
        )
    cierres = cierres_trimestrales(per, mes, n_meses)
    claves = list(zip(df_municipales["ANIO"], df_municipales["MES"]))
    trimestres = df_municipales[[c in cierres for c in claves]]
    suma = trimestres.groupby("CIUDAD").agg(
        DS=("DESEMPLEADOS", "sum"), PEA=("PEA", "sum"), N=("MES", "count")
    )
    suma = suma[suma["N"] == len(cierres)]
    return pd.DataFrame(
        {"CIUDAD": suma.index, "TD_DANE": 100 * suma["DS"] / suma["PEA"]}
    ).reset_index(drop=True)
