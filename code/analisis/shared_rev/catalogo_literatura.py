"""Catálogo de elegibilidad conceptual de las covariables auxiliares.

Define qué indicadores de TerriData tienen un mecanismo documentado en la literatura que
los vincula con el desempleo municipal. El catálogo es **independiente de la variable
respuesta**: se fija antes de calcular cualquier métrica empírica, de modo que el criterio
conceptual no pueda acomodarse a lo que digan los datos.

Fuente del catálogo
-------------------
Las entradas provienen de la revisión de literatura del proyecto (documento *Covariables de
TerriData para un estimador sintético de la tasa de desempleo, corte 2018*), que propone
diecisiete covariables con referencia bibliográfica verificable. Cada entrada conserva la
cita tal como aparece en esa revisión, en el campo `referencia`, y describe el mecanismo en
`justificacion`. Solo se incluyen variables con ese respaldo; no se admite ninguna por
plausibilidad sin fuente.

Correspondencia con TerriData
-----------------------------
Cada variable del documento se resolvió contra `tesis.terridata.terridata_bronce`
(campo `INDICADOR`) para obtener su código de indicador. El campo `indicador` conserva el
nombre textual con el que aparece en TerriData. Una variable entra al catálogo activo solo
si (i) tiene dato para el año de estimación, (ii) superó el pre-filtrado sobre los dominios
con encuesta y (iii) está completa en los municipios objetivo sin encuesta, condición
necesaria para la predicción sintética. Las variables del documento que incumplen alguna de
esas condiciones quedan registradas en `CATALOGO_EXCLUIDAS` con el motivo, para que la
trazabilidad del documento sea completa.

Dos decisiones del proyecto se documentan explícitamente:

* El Índice de Incidencia del Conflicto Armado (IICA) sustituye a «víctimas de
  desplazamiento forzado», que en TerriData solo existe para 2022-2023. Es un proxy de la
  misma dimensión y se justifica con la misma referencia.
* La tasa de tránsito inmediato a la educación superior se conserva bajo el mecanismo de
  capital humano del documento, por decisión del equipo del proyecto.

No existe un «nivel de respaldo» numérico: la versión anterior asignaba un valor L de 1 a 3
por entrada, que resultaba arbitrario y complicaba el análisis sin aportar una decisión.
"""

import pandas as pd

# Signo esperado del coeficiente sobre la tasa de desempleo, según el mecanismo declarado:
#   "+"  la covariable se asocia con mayor desempleo
#   "-"  la covariable se asocia con menor desempleo
#   "±"  la literatura no fija una dirección única
CATALOGO_LITERATURA = [
    # ── EDUCACIÓN (capital humano) ────────────────────────────────────────────
    {
        "codigo": "040010010",
        "alias": "COB_NET_MEDIA",
        "dimension": "Educación",
        "indicador": "Cobertura neta en educación media",
        "signo_esperado": "-",
        "referencia": (
            "Castillo-Robayo, C. D.; García-Estévez, J. (2019). «Desempleo juvenil en "
            "Colombia: ¿la educación importa?», Revista Finanzas y Política Económica, "
            "11(1), 101-127. DOI: 10.14718/revfinanzpolitecon.2019.11.1.7"
        ),
        "justificacion": (
            "El capital humano determina la empleabilidad. La cobertura neta en educación "
            "media mide la proporción de jóvenes en edad de cursar los últimos grados que "
            "efectivamente lo hacen; su déficit alimenta el desajuste de competencias que "
            "los autores identifican como factor principal del desempleo juvenil."
        ),
    },
    {
        "codigo": "040010009",
        "alias": "COB_NET_SEC",
        "dimension": "Educación",
        "indicador": "Cobertura neta en educación secundaria",
        "signo_esperado": "-",
        "referencia": (
            "Castillo-Robayo, C. D.; García-Estévez, J. (2019). «Desempleo juvenil en "
            "Colombia: ¿la educación importa?», Revista Finanzas y Política Económica, "
            "11(1), 101-127."
        ),
        "justificacion": (
            "La cobertura neta en secundaria es la base del sistema educativo local. Una "
            "baja cobertura limita la formación mínima para acceder al mercado laboral "
            "formal; el documento la propone junto a la cobertura en media."
        ),
    },
    {
        "codigo": "040040001",
        "alias": "SABER11_MAT",
        "dimension": "Educación",
        "indicador": "Puntaje promedio Pruebas Saber 11 - Matemáticas",
        "signo_esperado": "-",
        "referencia": (
            "Castillo-Robayo, C. D.; García-Estévez, J. (2019). Revista Finanzas y "
            "Política Económica, 11(1), 101-127."
        ),
        "justificacion": (
            "La calidad educativa, y no solo la cobertura, incide en la productividad y la "
            "empleabilidad. La brecha de competencias es determinante del desempleo "
            "estructural juvenil."
        ),
    },
    {
        "codigo": "040040002",
        "alias": "SABER11_LEC",
        "dimension": "Educación",
        "indicador": "Puntaje promedio Pruebas Saber 11 - Lectura crítica",
        "signo_esperado": "-",
        "referencia": (
            "Castillo-Robayo, C. D.; García-Estévez, J. (2019). Revista Finanzas y "
            "Política Económica, 11(1), 101-127."
        ),
        "justificacion": (
            "Segunda medida de calidad educativa propuesta por el documento; captura "
            "competencias de comprensión que el mercado laboral formal exige."
        ),
    },
    {
        "codigo": "040010028",
        "alias": "TASA_TRAN_EDU_SUP",
        "dimension": "Educación",
        "indicador": "Tasa de tránsito inmediato a la educación superior",
        "signo_esperado": "-",
        "referencia": (
            "Castillo-Robayo, C. D.; García-Estévez, J. (2019). Revista Finanzas y "
            "Política Económica, 11(1), 101-127 (mecanismo de capital humano). "
            "Conservada por decisión del equipo del proyecto."
        ),
        "justificacion": (
            "Mide la proporción de bachilleres que continúan al nivel terciario, predictor "
            "del capital humano futuro del territorio. Mayor formación acorta la búsqueda "
            "de empleo y reduce el desempleo friccional."
        ),
    },
    # ── ECONOMÍA ──────────────────────────────────────────────────────────────
    {
        "codigo": "120210002",
        "alias": "VA_PC",
        "dimension": "Economía",
        "indicador": "Valor agregado per cápita",
        "signo_esperado": "-",
        "referencia": (
            "Ramírez et al. (2021). «Determinantes económicos y sociales del desempleo y "
            "del empleo vulnerable», Redalyc (revista 4315), tabla 2."
        ),
        "justificacion": (
            "El valor agregado per cápita se asocia negativamente con el desempleo: mayor "
            "actividad económica genera demanda laboral. En el panel latinoamericano de "
            "los autores, el desempleo disminuye al incrementar el producto per cápita."
        ),
    },
    {
        "codigo": "120210008",
        "alias": "VA_PCT_PRIM",
        "dimension": "Economía",
        "indicador": "Porcentaje del valor agregado por actividades económicas - Actividades primarias",
        "signo_esperado": "±",
        "referencia": (
            "Grupo de análisis del mercado laboral (2016). Reportes del Emisor No. 211, "
            "Banco de la República; Bonet, J. (2005). «Cambio estructural regional en "
            "Colombia», DTSERU No. 62."
        ),
        "justificacion": (
            "La composición sectorial determina la absorción de empleo: los cambios "
            "sectoriales son determinante de la tasa de desempleo estructural. Un "
            "predominio agrícola se asocia a dinámicas de desempleo distintas."
        ),
    },
    {
        "codigo": "120210009",
        "alias": "VA_PCT_SEC",
        "dimension": "Economía",
        "indicador": "Porcentaje del valor agregado por actividades económicas - Actividades secundarias",
        "signo_esperado": "±",
        "referencia": (
            "Grupo de análisis del mercado laboral (2016). Reportes del Emisor No. 211, "
            "Banco de la República; Bonet, J. (2005). DTSERU No. 62."
        ),
        "justificacion": (
            "Participación de la industria y la construcción en el valor agregado; "
            "segunda componente de la estructura sectorial propuesta por el documento."
        ),
    },
    {
        "codigo": "120210010",
        "alias": "VA_PCT_TERC",
        "dimension": "Economía",
        "indicador": "Porcentaje del valor agregado por actividades económicas - Actividades terciarias",
        "signo_esperado": "±",
        "referencia": (
            "Grupo de análisis del mercado laboral (2016). Reportes del Emisor No. 211, "
            "Banco de la República; Bonet, J. (2005). DTSERU No. 62."
        ),
        "justificacion": (
            "Economías terciarizadas de baja productividad presentan dinámicas propias de "
            "desempleo e informalidad. Las tres participaciones suman cien; el control de "
            "multicolinealidad del conjunto final impide que entren juntas."
        ),
    },
    # ── POBREZA ───────────────────────────────────────────────────────────────
    {
        "codigo": "140010004",
        "alias": "IND_POB_MULT",
        "dimension": "Pobreza",
        "indicador": "Índice de pobreza multidimensional - IPM",
        "signo_esperado": "+",
        "referencia": (
            "DANE (2018). Medida de Pobreza Multidimensional Municipal de fuente censal "
            "2018."
        ),
        "justificacion": (
            "El IPM incluye la dimensión de trabajo (desempleo de larga duración y trabajo "
            "informal); los territorios con mayor IPM concentran privaciones laborales."
        ),
    },
    # ── DEMOGRAFÍA Y POBLACIÓN ────────────────────────────────────────────────
    {
        "codigo": "020040003",
        "alias": "PCT_URBANA",
        "dimension": "Demografía y población",
        "indicador": "Porcentaje población urbana",
        "signo_esperado": "+",
        "referencia": (
            "DANE, Atlas estadístico (Tomo II Social), «7.4. Tasa de desempleo (TD)»."
        ),
        "justificacion": (
            "El grado de urbanización cambia la estructura del desempleo: el desempleo "
            "abierto es predominantemente urbano, mientras la ruralidad se asocia más al "
            "subempleo."
        ),
    },
    {
        "codigo": "010010010",
        "alias": "DENS_POB",
        "dimension": "Demografía y población",
        "indicador": "Densidad poblacional",
        "signo_esperado": "±",
        "referencia": (
            "DNP. «Orientaciones para realizar la Medición del Desempeño de las Entidades "
            "Territoriales» (EI-G01), sección 1.4.2."
        ),
        "justificacion": (
            "Aproxima economías de aglomeración, que afectan la formación de mercados "
            "laborales y el emparejamiento entre oferta y demanda; el DNP la usa como "
            "variable de capacidades iniciales municipales."
        ),
    },
    {
        "codigo": "020090021",
        "alias": "PCT_JOVENES",
        "dimension": "Demografía y población",
        "indicador": "Porcentaje de población de jóvenes entre 14 y 28 años",
        "signo_esperado": "+",
        "referencia": (
            "Tamayo, J. A. (2008). «La tasa natural de desempleo en Colombia y sus "
            "determinantes», Borradores de Economía No. 491, Banco de la República. "
            "DOI: 10.32468/be.491"
        ),
        "justificacion": (
            "La participación de jóvenes en la fuerza laboral es determinante central de "
            "la tasa natural de desempleo, junto con los costos laborales no salariales."
        ),
    },
    # ── FINANZAS PÚBLICAS ─────────────────────────────────────────────────────
    {
        "codigo": "070100007",
        "alias": "IDF",
        "dimension": "Finanzas públicas",
        "indicador": "Indicador de desempeño fiscal",
        "signo_esperado": "-",
        "referencia": (
            "DNP (2023). «Índice de desempeño fiscal (IDF) municipal 2023 y "
            "fortalecimiento de las finanzas territoriales»."
        ),
        "justificacion": (
            "La capacidad fiscal y la inversión pública dinamizan el empleo local; el IDF "
            "sintetiza autofinanciación, deuda, dependencia de transferencias, recursos "
            "propios, magnitud de la inversión y ahorro."
        ),
    },
    {
        "codigo": "070010020",
        "alias": "ING_TRIB_PC",
        "dimension": "Finanzas públicas",
        "indicador": "Ingresos tributarios per cápita",
        "signo_esperado": "-",
        "referencia": (
            "Fundación Felipe González (2020). «Empleo público de emergencia en municipios "
            "y departamentos» (con datos de TerriData-DNP)."
        ),
        "justificacion": (
            "Mayor recaudo financia infraestructura y empleo, incluido el empleo público "
            "de emergencia, reduciendo el desempleo local."
        ),
    },
    # ── CONFLICTO ARMADO Y SEGURIDAD CIUDADANA ────────────────────────────────
    {
        "codigo": "260020003",
        "alias": "IICA_CONFLICTO",
        "dimension": "Conflicto armado y seguridad ciudadana",
        "indicador": "Índice de Incidencia del Conflicto Armado - IICA",
        "signo_esperado": "+",
        "referencia": (
            "Ibáñez, A. M. (2008). El desplazamiento forzoso en Colombia: un camino sin "
            "retorno hacia la pobreza, Universidad de los Andes. Proxy: la serie de "
            "víctimas de desplazamiento de TerriData solo existe para 2022-2023."
        ),
        "justificacion": (
            "El conflicto armado genera desplazamiento forzado, que produce un choque de "
            "oferta laboral y una integración económica fallida que eleva el desempleo y "
            "el subempleo en los municipios receptores. El IICA mide la exposición del "
            "territorio a ese conflicto."
        ),
    },
    {
        "codigo": "060010003",
        "alias": "TASA_HOMICIDIOS",
        "dimension": "Conflicto armado y seguridad ciudadana",
        "indicador": "Tasa de homicidios por cada 100.000 habitantes",
        "signo_esperado": "+",
        "referencia": (
            "Estudio de determinantes sociales, ambiente urbano y seguridad, Santiago de "
            "Cali 2015-2024, Revista Panamericana de Salud Pública (2024)."
        ),
        "justificacion": (
            "La inseguridad deteriora la inversión y la actividad económica local, con "
            "efectos indirectos sobre el empleo; se usa como covariable en análisis "
            "ecológicos territoriales junto al IPM y la escolaridad."
        ),
    },
    # ── VIVIENDA Y ACCESO A SERVICIOS PÚBLICOS ────────────────────────────────
    {
        "codigo": "030010004",
        "alias": "COB_ACUEDUCTO",
        "dimension": "Vivienda y acceso a servicios públicos",
        "indicador": "Cobertura de acueducto (Censo)",
        "signo_esperado": "-",
        "referencia": (
            "DNP (2019). Cartilla 1 «Conceptos básicos para un mejor uso de TerriData», "
            "dimensión Vivienda y Acceso a Servicios Públicos."
        ),
        "justificacion": (
            "La infraestructura básica es proxy del desarrollo local y facilita la "
            "actividad productiva; el DNP la emplea como indicador territorial de "
            "bienestar."
        ),
    },
    {
        "codigo": "030010003",
        "alias": "BANDA_ANCHA",
        "dimension": "Vivienda y acceso a servicios públicos",
        "indicador": "Penetración de banda ancha",
        "signo_esperado": "-",
        "referencia": (
            "DNP (2019). Cartilla 1 «Conceptos básicos para un mejor uso de TerriData», "
            "dimensión Vivienda y Acceso a Servicios Públicos."
        ),
        "justificacion": (
            "La conectividad facilita la actividad productiva y el emparejamiento "
            "laboral (búsqueda y publicación de vacantes)."
        ),
    },
]

# Variables propuestas por la revisión de literatura que no pueden usarse. Se conservan en
# el catálogo para que el documento explique por qué no entran, con el código de TerriData
# que se examinó en cada caso.
CATALOGO_EXCLUIDAS = [
    {
        "codigo": "040030003",
        "alias": "TASA_ANALFABETISMO",
        "dimension": "Educación",
        "indicador": "Tasa de Analfabetismo (Censo)",
        "motivo": "sin dato en los dominios con encuesta para el período de estimación",
    },
    {
        "codigo": "160080001",
        "alias": "DENS_EMPRESARIAL",
        "dimension": "Economía",
        "indicador": "Número de empresas generadoras de empleo formal por cada 10.000 habitantes",
        "motivo": "la serie termina en 2016; no existe dato para 2018",
    },
    {
        "codigo": "140060001",
        "alias": "POBREZA_MONETARIA",
        "dimension": "Pobreza",
        "indicador": "Incidencia de la pobreza monetaria - Actualización metodológica",
        "motivo": (
            "solo se publica para departamentos y 23 ciudades principales; no existe en "
            "los municipios objetivo sin encuesta, por lo que no permite predicción sintética"
        ),
    },
    {
        "codigo": "140010003",
        "alias": "GINI",
        "dimension": "Pobreza",
        "indicador": "Coeficiente de Gini",
        "motivo": "solo se publica a nivel departamental",
    },
    {
        "codigo": "260030002",
        "alias": "VICTIMAS_DESPLAZAMIENTO",
        "dimension": "Conflicto armado y seguridad ciudadana",
        "indicador": "Víctimas de Desplazamiento Forzado ubicadas",
        "motivo": "solo existe para 2022-2023; se sustituye por el IICA como proxy",
    },
]


def resolver_catalogo(indicadores_dict: dict, columnas_disponibles: list) -> tuple:
    """Resuelve cada entrada del catálogo contra el diccionario y el conjunto pre-filtrado.

    Una entrada se considera activa si su código existe en el diccionario de indicadores
    de TerriData y además está entre las covariables disponibles tras el pre-filtrado. Las
    variables excluidas de antemano (`CATALOGO_EXCLUIDAS`) se añaden al reporte con su
    motivo, de modo que la tabla resultante cubra la totalidad de la revisión de literatura.

    Args:
        indicadores_dict (dict): Mapa código → nombre del indicador (`dim_indicadores`).
        columnas_disponibles (list[str]): Códigos presentes en el conjunto pre-filtrado.

    Returns:
        tuple[list, pd.DataFrame]: (catalogo_activo, reporte). `catalogo_activo` son las
            entradas activas (dicts del catálogo); `reporte` tiene una fila por variable de
            la revisión de literatura con columnas `Alias`, `Dimension`, `Codigo`, `Nombre`,
            `Signo_esperado`, `Referencia` y `Estado`, donde `Estado` es `activa`,
            `no está en el diccionario`, `no superó el pre-filtrado` o
            `sin dato utilizable: <motivo>`.

    Example:
        >>> catalogo_activo, reporte = resolver_catalogo(indicadores_dict, list(df_pd.columns))
        >>> reporte["Estado"].value_counts()
    """
    disponibles = set(columnas_disponibles)
    filas, catalogo_activo = [], []

    for entrada in CATALOGO_LITERATURA:
        codigo = entrada["codigo"]
        if codigo not in indicadores_dict:
            estado = "no está en el diccionario"
        elif codigo not in disponibles:
            estado = "no superó el pre-filtrado"
        else:
            estado = "activa"
            catalogo_activo.append(dict(entrada))

        filas.append(
            {
                "Alias": entrada["alias"],
                "Dimension": entrada["dimension"],
                "Codigo": codigo,
                "Nombre": indicadores_dict.get(codigo, entrada["indicador"]),
                "Signo_esperado": entrada["signo_esperado"],
                "Referencia": entrada["referencia"],
                "Estado": estado,
            }
        )

    for entrada in CATALOGO_EXCLUIDAS:
        filas.append(
            {
                "Alias": entrada["alias"],
                "Dimension": entrada["dimension"],
                "Codigo": entrada["codigo"],
                "Nombre": indicadores_dict.get(entrada["codigo"], entrada["indicador"]),
                "Signo_esperado": "—",
                "Referencia": "—",
                "Estado": f"sin dato utilizable: {entrada['motivo']}",
            }
        )

    reporte = pd.DataFrame(filas)
    print(
        f"Catálogo de elegibilidad conceptual: {len(catalogo_activo)} de "
        f"{len(CATALOGO_LITERATURA)} entradas activas "
        f"({len(CATALOGO_EXCLUIDAS)} variables de la literatura sin dato utilizable)"
    )
    for estado, n in reporte["Estado"].value_counts().items():
        print(f"  · {estado}: {n}")

    return catalogo_activo, reporte


def mapas_catalogo(catalogo_activo: list) -> tuple:
    """Construye los mapas auxiliares indexados por código de indicador.

    Args:
        catalogo_activo (list[dict]): Salida de `resolver_catalogo()`.

    Returns:
        tuple[list, dict, dict, dict]: (códigos, alias, signo esperado, dimensión), cada
            mapa con el código de indicador como clave.

    Example:
        >>> codigos, alias, signo, dimension = mapas_catalogo(catalogo_activo)
    """
    codigos = [e["codigo"] for e in catalogo_activo]
    alias = {e["codigo"]: e["alias"] for e in catalogo_activo}
    signo = {e["codigo"]: e["signo_esperado"] for e in catalogo_activo}
    dimension = {e["codigo"]: e["dimension"] for e in catalogo_activo}
    return codigos, alias, signo, dimension
