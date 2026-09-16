"""Catálogo de elegibilidad conceptual de las covariables auxiliares.

Define qué covariables de TerriData tienen un mecanismo documentado que las vincula con el
desempleo municipal, organizadas en siete dimensiones conceptuales. El catálogo es
**independiente de la variable respuesta**: se fija antes de calcular cualquier métrica
empírica, de modo que el criterio conceptual no pueda acomodarse a lo que digan los datos.

Este criterio es el que realiza la mayor reducción del espacio de covariables. Que sea
independiente de la respuesta es precisamente lo que permite que las correlaciones
calculadas después conserven su interpretación: a diferencia del pre-filtro por
correlación de la versión original, aquí las candidatas no fueron elegidas por parecerse a
la tasa de desempleo.

ADVERTENCIA SOBRE LAS FUENTES
----------------------------
El campo `fuente_declarada` recoge la atribución bibliográfica que los autores del
proyecto asignaron a cada mecanismo. Varias de esas fuentes **no están en la bibliografía
del documento** y no han podido verificarse contra el material disponible en el
repositorio. Por esa razón se mantienen separadas del campo `justificacion` —que describe
el mecanismo y se sostiene por sí mismo— y no deben citarse en el documento como respaldo
verificado hasta que se comprueben una por una. Ver el informe de revisión, sección de
alertas.
"""

import re

import pandas as pd

# Nivel de respaldo conceptual L, asignado antes de observar los datos:
#   3 = determinante documentado para Colombia con mecanismo directo
#   2 = documentado en economías en desarrollo con mecanismo claro
#   1 = mecanismo plausible o variable proxy
CATALOGO_LITERATURA = [
    # ── INFRAESTRUCTURA BÁSICA ────────────────────────────────────────────────
    {"codigo": "030010002", "busqueda": None,
     "dimension": "Infraestructura básica",
     "nivel_literatura": 2, "alias": "COB_ENER_RURAL",
     "fuente_declarada": "Galvis & Meisel (2010) [no verificada]",
     "justificacion": (
         "El acceso a energía eléctrica rural es condición necesaria para la actividad "
         "económica en zonas periféricas. Municipios con baja electrificación concentran "
         "mayor informalidad, menor productividad agrícola y desempleo estructural.")},

    # ── CAPITAL HUMANO ────────────────────────────────────────────────────────
    {"codigo": "040010028", "busqueda": None,
     "dimension": "Capital humano",
     "nivel_literatura": 2, "alias": "TASA_TRAN_EDU_SUP",
     "fuente_declarada": "Arango & Flórez (2012) [no verificada]",
     "justificacion": (
         "La tasa de tránsito inmediato a la educación superior mide la proporción de "
         "bachilleres que continúan en el nivel terciario, predictor del capital humano "
         "futuro del territorio. Mayor formación acorta el período de búsqueda de empleo "
         "y reduce el desempleo friccional.")},

    {"codigo": None, "busqueda": r"cobertura neta.*secundaria",
     "dimension": "Capital humano",
     "nivel_literatura": 2, "alias": "COB_NET_SEC",
     "fuente_declarada": "Mecanismo estándar de capital humano",
     "justificacion": (
         "La cobertura neta en educación secundaria es la base del sistema educativo "
         "local. Una baja cobertura limita la formación mínima requerida para acceder al "
         "mercado laboral formal y perpetúa la informalidad.")},

    {"codigo": None, "busqueda": r"ciencia",
     "dimension": "Capital humano",
     "nivel_literatura": 1, "alias": "IND_CIENCIA",
     "fuente_declarada": "Mecanismo plausible, sin fuente asignada",
     "justificacion": (
         "El índice de ciencia e innovación captura la capacidad del territorio para "
         "generar conocimiento aplicado, determinante de la productividad total de los "
         "factores y de la demanda de trabajo calificado.")},

    {"codigo": None, "busqueda": r"inversión.*educaci",
     "dimension": "Capital humano",
     "nivel_literatura": 1, "alias": "INV_EDUCACION",
     "fuente_declarada": "Mecanismo plausible, sin fuente asignada",
     "justificacion": (
         "La inversión pública en educación es el mecanismo mediante el cual el municipio "
         "mejora la calidad del capital humano disponible, reduciendo el desempleo "
         "estructural en el mediano y largo plazo.")},

    # ── CONDICIONES SOCIOECONÓMICAS ───────────────────────────────────────────
    {"codigo": "140010004", "busqueda": None,
     "dimension": "Condiciones socioeconómicas",
     "nivel_literatura": 3, "alias": "IND_POB_MULT",
     "fuente_declarada": "DANE/CEPAL (2016) [no verificada]",
     "justificacion": (
         "El índice de pobreza multidimensional sintetiza privaciones en educación, "
         "salud, vivienda y condiciones laborales. Territorios con valores elevados "
         "presentan menor participación laboral y mayor desempleo de larga duración.")},

    {"codigo": None, "busqueda": r"índice de pobreza(?!.*multidimensional)",
     "dimension": "Condiciones socioeconómicas",
     "nivel_literatura": 2, "alias": "IND_POB_MON",
     "fuente_declarada": "Complemento del índice multidimensional",
     "justificacion": (
         "El índice de pobreza monetaria complementa al multidimensional capturando la "
         "insuficiencia de ingresos, un mecanismo de exclusión laboral distinto al de las "
         "privaciones materiales.")},

    {"codigo": None, "busqueda": r"ingresos corrientes per cápita",
     "dimension": "Condiciones socioeconómicas",
     "nivel_literatura": 1, "alias": "ING_CORR_PC",
     "fuente_declarada": "Mecanismo plausible, sin fuente asignada",
     "justificacion": (
         "Los ingresos corrientes per cápita del municipio reflejan su capacidad fiscal "
         "para financiar servicios públicos generadores de empleo directo e indirecto.")},

    # ── DESEMPEÑO ECONÓMICO ───────────────────────────────────────────────────
    {"codigo": "310010008", "busqueda": None,
     "dimension": "Desempeño económico",
     "nivel_literatura": 3, "alias": "IND_PROD",
     "fuente_declarada": "MendozaZea2019 (variables auxiliares de desempeño económico)",
     "justificacion": (
         "El índice de productividad municipal mide el valor agregado por unidad de "
         "factor productivo. Mayor productividad implica mayor capacidad de absorción "
         "laboral del territorio.")},

    # ── SEGURIDAD Y CONFLICTO ─────────────────────────────────────────────────
    {"codigo": None, "busqueda": r"incidencia del conflicto armado|iica",
     "dimension": "Seguridad y conflicto",
     "nivel_literatura": 2, "alias": "IICA_CONFLICTO",
     "fuente_declarada": "Mecanismo documentado para el caso colombiano [sin clave bibliográfica]",
     "justificacion": (
         "El índice de incidencia del conflicto armado captura la exposición histórica a "
         "la violencia organizada, que genera desplazamiento forzado, destrucción de "
         "capital físico y disrupción de los mercados laborales locales.")},

    {"codigo": None, "busqueda": r"hurto a personas",
     "dimension": "Seguridad y conflicto",
     "nivel_literatura": 1, "alias": "TASA_HURTO",
     "fuente_declarada": "Mecanismo plausible, sin fuente asignada",
     "justificacion": (
         "La tasa de hurto a personas mide la inseguridad ciudadana cotidiana. Altos "
         "niveles desincentivan la inversión privada, reducen la movilidad de los "
         "trabajadores y aumentan la informalidad.")},

    # ── CAPACIDAD INSTITUCIONAL ───────────────────────────────────────────────
    {"codigo": None, "busqueda": r"posición nacional en gestión|gestión.*alcaldía",
     "dimension": "Capacidad institucional",
     "nivel_literatura": 1, "alias": "POS_GESTION",
     "fuente_declarada": "Mecanismo plausible, sin fuente asignada",
     "justificacion": (
         "La posición nacional en gestión municipal mide la eficiencia de las alcaldías "
         "para movilizar y ejecutar recursos de inversión pública, que se traduce en "
         "empleo directo y en servicios que reducen el costo de participar en el mercado "
         "laboral formal.")},

    {"codigo": None, "busqueda": r"inversión.*transporte",
     "dimension": "Capacidad institucional",
     "nivel_literatura": 1, "alias": "INV_TRANSPORTE",
     "fuente_declarada": "Mecanismo plausible, sin fuente asignada",
     "justificacion": (
         "La inversión en infraestructura de transporte reduce los costos de movilidad, "
         "conecta mercados laborales regionales y facilita el acceso a oportunidades de "
         "empleo fuera del municipio de residencia.")},

    {"codigo": None, "busqueda": r"inversión.*desarrollo comunitario",
     "dimension": "Capacidad institucional",
     "nivel_literatura": 1, "alias": "INV_DES_COMUN",
     "fuente_declarada": "Mecanismo plausible, sin fuente asignada",
     "justificacion": (
         "La inversión en desarrollo comunitario fortalece el capital social del "
         "territorio. Mayor cohesión social se asocia con menor desempleo de larga "
         "duración mediante redes de información sobre oportunidades laborales.")},

    # ── MEDIO AMBIENTE Y TERRITORIO ───────────────────────────────────────────
    {"codigo": None, "busqueda": r"ecosistemas estratégicos",
     "dimension": "Medio ambiente y territorio",
     "nivel_literatura": 1, "alias": "IND_ECOSIST",
     "fuente_declarada": "Mecanismo plausible, sin fuente asignada",
     "justificacion": (
         "El índice de ecosistemas estratégicos refleja la proporción de áreas naturales "
         "protegidas o de alta importancia ambiental, asociada con economías más "
         "extractivas, menor diversificación productiva y patrones diferenciados de "
         "empleo rural.")},
]


def resolver_catalogo(indicadores_dict: dict, columnas_disponibles: list) -> tuple:
    """Resuelve cada entrada del catálogo a un código de indicador concreto.

    Las entradas con `codigo` explícito se toman tal cual. Las que traen una expresión de
    búsqueda se resuelven contra el diccionario de indicadores de TerriData. Una entrada se
    considera activa solo si su código existe además entre las covariables disponibles
    tras el pre-filtrado.

    Args:
        indicadores_dict (dict): Mapa código → nombre del indicador (`dim_indicadores`).
        columnas_disponibles (list[str]): Códigos presentes en el conjunto pre-filtrado.

    Returns:
        tuple[list, pd.DataFrame]: (catalogo_activo, reporte). `catalogo_activo` son las
            entradas resueltas y disponibles; `reporte` tiene una fila por entrada del
            catálogo con su estado —`activa`, `sin correspondencia en el diccionario` o
            `no superó el pre-filtrado`— para dejar trazado por qué una entrada no llega a
            candidata.

    Example:
        >>> catalogo_activo, reporte = resolver_catalogo(indicadores_dict, list(df_pd.columns))
        >>> reporte["Estado"].value_counts()
    """
    disponibles = set(columnas_disponibles)
    filas, catalogo_activo = [], []

    for entrada in CATALOGO_LITERATURA:
        codigo = entrada["codigo"]
        if codigo is None:
            codigo = next(
                (cod for cod, nombre in indicadores_dict.items()
                 if re.search(entrada["busqueda"], str(nombre), re.IGNORECASE)),
                None,
            )

        if codigo is None:
            estado = "sin correspondencia en el diccionario"
        elif codigo not in disponibles:
            estado = "no superó el pre-filtrado"
        else:
            estado = "activa"
            catalogo_activo.append({**entrada, "codigo": codigo})

        filas.append({
            "Alias":     entrada["alias"],
            "Dimension": entrada["dimension"],
            "Codigo":    codigo if codigo is not None else "—",
            "Nombre":    indicadores_dict.get(codigo, "—"),
            "L":         entrada["nivel_literatura"],
            "Estado":    estado,
        })

    reporte = pd.DataFrame(filas)
    print(f"Catálogo de elegibilidad conceptual: {len(catalogo_activo)} de "
          f"{len(CATALOGO_LITERATURA)} entradas activas")
    for estado, n in reporte["Estado"].value_counts().items():
        print(f"  · {estado}: {n}")

    return catalogo_activo, reporte


def mapas_catalogo(catalogo_activo: list) -> tuple:
    """Construye los mapas auxiliares indexados por código de indicador.

    Args:
        catalogo_activo (list[dict]): Salida de `resolver_catalogo()`.

    Returns:
        tuple[list, dict, dict, dict]: (códigos, alias, nivel de literatura, dimensión).

    Example:
        >>> codigos, alias, L, dimension = mapas_catalogo(catalogo_activo)
    """
    codigos   = [e["codigo"] for e in catalogo_activo]
    alias     = {e["codigo"]: e["alias"] for e in catalogo_activo}
    literatura = {e["codigo"]: e["nivel_literatura"] for e in catalogo_activo}
    dimension = {e["codigo"]: e["dimension"] for e in catalogo_activo}
    return codigos, alias, literatura, dimension
