"""Tabla de auditoría de la correspondencia geográfica respuesta–covariables (G7-B1).

Una fila por dominio con estimación directa. Documenta, para cada uno, de dónde sale la tasa de
desempleo y de dónde salen sus covariables, para que se pueda comprobar que ambas describen el
mismo territorio:

* ``CODIGO_AREA_GEIH``: valor del campo ``AREA`` de los microdatos GEIH (marco 2005). Es el código
  del departamento de la ciudad (``76`` = Cali A.M.); ``geih_oro`` lo traduce al DIVIPOLA de la
  capital con ``tesis.dim.dim_geih_divipola``.
* ``NOMBRE_DOMINIO``: nombre con el que el DANE publica el dominio (anexo «Mercado laboral según
  proyecciones CNPV 2018»); ``EN_ANEXO_DANE`` indica si ese nombre aparece en las cifras oficiales
  del período y ``TD_DANE_PCT`` / ``DIF_TD_PP`` comparan la tasa directa con la publicada.
* ``GEOGRAFIA_TASA`` y ``GEOGRAFIA_COVARIABLES``: territorio real que cubre cada lado. La tasa solo
  cubre cabeceras (el ``AREA`` solo está en CLASE = 1); TerriData es municipal (cabecera y resto).
* ``MUNICIPIOS_INTEGRANTES`` / ``DIVIPOLA_INTEGRANTES``: membresía de la GEIH (Metodología GEIH v9,
  PDF 9), capital primero.
* ``CODIGO_DOMINIO``: DIVIPOLA con el que se unen la tasa y las covariables.
* ``REGLA_X_D``: cómo se construye ``x_d``. En los dominios de un municipio es el valor municipal; en
  los A.M., ``Σ z_m x_m / Σ z_m`` con el denominador de cada indicador (``reglas_agregacion.py``).
"""

import pandas as pd

GEOGRAFIA_TASA_CIUDAD = (
    "Cabecera municipal de {capital} (AREA de la GEIH, solo CLASE = 1)"
)
GEOGRAFIA_TASA_AM = (
    "Cabeceras de los {n} municipios del A.M. según la GEIH (AREA, solo CLASE = 1)"
)
GEOGRAFIA_COVARIABLES = "Municipio completo (cabecera y resto), TerriData"
REGLA_CIUDAD = "x_d = valor municipal de TerriData de {capital}, sin agregar"
REGLA_AM = (
    "x_d = Σ z_m·x_m / Σ z_m sobre los {n} municipios, z = denominador de cada indicador "
    "(catálogo: {resumen}; ver reglas_agregacion_covariables); fuera del catálogo z = PET 15+"
)


def resumen_pesos(pesos_catalogo: dict) -> str:
    """Resume cuántas variables del catálogo usan cada peso de agregación.

    Args:
        pesos_catalogo (dict): Código de indicador → nombre del peso (``PESOS_AGREGACION``).

    Returns:
        str: Pesos en orden alfabético con su número de variables, separados por coma.

    Casos de uso:
        Texto de la columna ``REGLA_X_D`` de los dominios A.M.

    >>> resumen_pesos({"a": "SUPERFICIE", "b": "POBLACION_TOTAL", "c": "POBLACION_TOTAL"})
    'POBLACION_TOTAL 2, SUPERFICIE 1'
    """
    conteo = pd.Series(list(pesos_catalogo.values())).value_counts().sort_index()
    return ", ".join(f"{peso} {n}" for peso, n in conteo.items())


def tabla_auditoria_dominios(
    df_miembros: pd.DataFrame,
    df_estimaciones: pd.DataFrame,
    df_publicados: pd.DataFrame,
    pesos_catalogo: dict,
) -> pd.DataFrame:
    """Construye la tabla de auditoría de la correspondencia geográfica de cada dominio.

    Args:
        df_miembros (pd.DataFrame): Una fila por municipio miembro, con ``CODIGO_DOMINIO``,
            ``NOMBRE_DOMINIO``, ``TIPO_DOMINIO``, ``CODIGO_MUNICIPIO``, ``MUNICIPIO``,
            ``ES_CAPITAL`` y ``CODIGO_AREA_GEIH`` (``AREA`` de la capital; NULL en los demás
            miembros). Sale de ``dim_dominio_geih`` unida a ``dim_geih_divipola``.
        df_estimaciones (pd.DataFrame): Estimación directa por dominio con ``PER``, ``MES``,
            ``TRIMESTRE_MOVIL``, ``CODIGO_DOMINIO`` y ``TASA_DESEMPLEO_PCT``.
        df_publicados (pd.DataFrame): Cifras DANE del período con ``CIUDAD`` y
            ``TASA_DESEMPLEO`` (puede estar vacío si el anexo no cubre el período).
        pesos_catalogo (dict): Código de indicador del catálogo → nombre del peso.

    Returns:
        pd.DataFrame: Una fila por dominio y período, ordenada por ``CODIGO_AREA_GEIH``.

    Raises:
        ValueError: Si un dominio no tiene exactamente una capital o su capital no tiene
            ``CODIGO_AREA_GEIH``.

    Casos de uso:
        Auditoría de G7-B1 en ``adicion_covariables.py``; insumo de la tabla de la tesis.

    >>> miembros = pd.DataFrame({
    ...     "CODIGO_DOMINIO": ["76001", "76001", "19001"],
    ...     "NOMBRE_DOMINIO": ["Cali A.M.", "Cali A.M.", "Popayán"],
    ...     "TIPO_DOMINIO": ["CIUDAD_AM", "CIUDAD_AM", "CIUDAD"],
    ...     "CODIGO_MUNICIPIO": ["76001", "76892", "19001"],
    ...     "MUNICIPIO": ["CALI", "YUMBO", "POPAYÁN"],
    ...     "ES_CAPITAL": [True, False, True],
    ...     "CODIGO_AREA_GEIH": ["76", None, "19"]})
    >>> est = pd.DataFrame({"PER": [2018, 2018], "MES": [12, 12],
    ...     "TRIMESTRE_MOVIL": ["Oct-Dic 2018"] * 2, "CODIGO_DOMINIO": ["76001", "19001"],
    ...     "TASA_DESEMPLEO_PCT": [10.0, 12.0]})
    >>> pub = pd.DataFrame({"CIUDAD": ["Cali A.M."], "TASA_DESEMPLEO": [10.004]})
    >>> t = tabla_auditoria_dominios(miembros, est, pub, {"x": "SUPERFICIE"})
    >>> t[["CODIGO_AREA_GEIH", "NOMBRE_DOMINIO", "DIVIPOLA_INTEGRANTES", "EN_ANEXO_DANE"]]
      CODIGO_AREA_GEIH NOMBRE_DOMINIO DIVIPOLA_INTEGRANTES  EN_ANEXO_DANE
    0               19        Popayán                19001          False
    1               76      Cali A.M.         76001, 76892           True
    >>> round(float(t.loc[1, "DIF_TD_PP"]), 3)
    -0.004
    """
    filas = []
    for codigo, grupo in df_miembros.groupby("CODIGO_DOMINIO", sort=False):
        capital = grupo[grupo["ES_CAPITAL"]]
        if len(capital) != 1 or pd.isna(capital["CODIGO_AREA_GEIH"].iloc[0]):
            raise ValueError(
                f"El dominio {codigo} no tiene una única capital con CODIGO_AREA_GEIH"
            )
        cap = capital.iloc[0]
        orden = pd.concat(
            [capital, grupo[~grupo["ES_CAPITAL"]].sort_values("MUNICIPIO")]
        )
        n = len(orden)
        es_am = cap["TIPO_DOMINIO"] == "CIUDAD_AM"
        nombre_cap = str(cap["MUNICIPIO"]).title()
        filas.append(
            {
                "CODIGO_AREA_GEIH": cap["CODIGO_AREA_GEIH"],
                "NOMBRE_DOMINIO": cap["NOMBRE_DOMINIO"],
                "TIPO_DOMINIO": cap["TIPO_DOMINIO"],
                "GEOGRAFIA_TASA": (
                    GEOGRAFIA_TASA_AM.format(n=n)
                    if es_am
                    else GEOGRAFIA_TASA_CIUDAD.format(capital=nombre_cap)
                ),
                "GEOGRAFIA_COVARIABLES": GEOGRAFIA_COVARIABLES,
                "N_MUNICIPIOS": n,
                "MUNICIPIOS_INTEGRANTES": ", ".join(orden["MUNICIPIO"].str.title()),
                "DIVIPOLA_INTEGRANTES": ", ".join(orden["CODIGO_MUNICIPIO"]),
                "CODIGO_DOMINIO": codigo,
                "REGLA_X_D": (
                    REGLA_AM.format(n=n, resumen=resumen_pesos(pesos_catalogo))
                    if es_am
                    else REGLA_CIUDAD.format(capital=nombre_cap)
                ),
            }
        )

    publicados = dict(zip(df_publicados["CIUDAD"], df_publicados["TASA_DESEMPLEO"]))
    tabla = df_estimaciones[
        ["PER", "MES", "TRIMESTRE_MOVIL", "CODIGO_DOMINIO", "TASA_DESEMPLEO_PCT"]
    ].merge(pd.DataFrame(filas), on="CODIGO_DOMINIO", how="inner")
    tabla["EN_ANEXO_DANE"] = tabla["NOMBRE_DOMINIO"].isin(publicados.keys())
    tabla["TD_DANE_PCT"] = tabla["NOMBRE_DOMINIO"].map(publicados).astype(float)
    tabla["DIF_TD_PP"] = tabla["TASA_DESEMPLEO_PCT"] - tabla["TD_DANE_PCT"]
    columnas = [
        "PER",
        "MES",
        "TRIMESTRE_MOVIL",
        "CODIGO_AREA_GEIH",
        "NOMBRE_DOMINIO",
        "EN_ANEXO_DANE",
        "TIPO_DOMINIO",
        "GEOGRAFIA_TASA",
        "GEOGRAFIA_COVARIABLES",
        "N_MUNICIPIOS",
        "MUNICIPIOS_INTEGRANTES",
        "DIVIPOLA_INTEGRANTES",
        "CODIGO_DOMINIO",
        "REGLA_X_D",
        "TASA_DESEMPLEO_PCT",
        "TD_DANE_PCT",
        "DIF_TD_PP",
    ]
    return (
        tabla[columnas]
        .sort_values(["PER", "MES", "CODIGO_AREA_GEIH"])
        .reset_index(drop=True)
    )
