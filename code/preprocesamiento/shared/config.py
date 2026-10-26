"""Parámetros del preprocesamiento, el análisis descriptivo y la selección de covariables.

Reúne las tablas fuente y destino, las columnas de metadatos, los parámetros de la estimación
directa, los umbrales de calidad, los criterios de pre-filtrado y los de diagnóstico y
selección de covariables.
"""

# ── Tablas fuente ─────────────────────────────────────────────────────────────
TBL_MERCADO_LABORAL = "tesis.geih_oro.mercado_laboral"
TBL_TERRIDATA = "tesis.terridata.terridata_extendido_plata"
# Formato largo (una fila por indicador, entidad y período); da el mes de corte de cada indicador.
TBL_TERRIDATA_BRONCE = "tesis.terridata.terridata_bronce"
TBL_DIM_INDICADORES = "tesis.dim.dim_indicadores"
# Membresía municipio → dominio (ciudad o ciudad A.M.), ver dimensiones/dim_dominio_geih.py.
TBL_DIM_DOMINIO = "tesis.dim.dim_dominio_geih"
# Capitales GEIH con su código AREA (CODIGO_AREA_GEIH), ver dimensiones/dim_geih_divipola.py.
TBL_DIM_GEIH_DIVIPOLA = "tesis.dim.dim_geih_divipola"
# Cifras oficiales del DANE por dominio (validación de la estimación directa).
TBL_DATOS_MUNICIPALES = "tesis.geih_bronce.datos_municipales"
NOMBRE_TOTAL_23 = "Total 23 ciudades y A.M."
# Cifras anuales oficiales de los agregados (Total 13 y Total 10 ciudades, entre otros); el anexo no
# publica la serie anual por ciudad (ver analisis/sensibilidad_ventana_temporal.py).
TBL_DATOS_ANUALES = "tesis.geih_bronce.datos_anuales"
NOMBRE_TOTAL_13_ANUAL = "Total 13 ciudades y áreas metropolitanas"
NOMBRE_TOTAL_10 = "Total 10 ciudades"
# Las 13 grandes ciudades con sus A.M. (GEIH v9, PDF 9), con los nombres del anexo DANE: su suma
# reconstruye el «Total 13 ciudades y áreas metropolitanas».
CIUDADES_13_AM = [
    "Bogotá",
    "Medellín A.M.",
    "Cali A.M.",
    "Barranquilla A.M.",
    "Bucaramanga A.M.",
    "Manizales A.M.",
    "Pasto",
    "Pereira A.M.",
    "Cúcuta A.M.",
    "Ibagué",
    "Montería",
    "Cartagena",
    "Villavicencio",
]

# ── Tablas destino ────────────────────────────────────────────────────────────
TBL_ESTIMACION_DIRECTA = "tesis.preprocesamiento.tasa_desempleo_municipal"
TBL_COVARIABLES = "tesis.preprocesamiento.tasa_desempleo_covariables"
# Regla con la que se agregó cada covariable del catálogo a los dominios A.M. (trazabilidad).
TBL_REGLAS_AGREGACION = "tesis.preprocesamiento.reglas_agregacion_covariables"
# Auditoría de la correspondencia geográfica tasa–covariables de cada dominio (G7-B1).
TBL_AUDITORIA_DOMINIOS = "tesis.preprocesamiento.auditoria_dominios"
TBL_PREFILTRADAS = "tesis.preprocesamiento.covariables_prefiltradas"
TBL_CASCADA = "tesis.preprocesamiento.cascada_prefiltrado"
TBL_SENSIBILIDAD = "tesis.preprocesamiento.sensibilidad_variabilidad"
TBL_SIN_ENCUESTA = "tesis.preprocesamiento.municipios_sin_encuesta"
TBL_CATALOGO = "tesis.preprocesamiento.catalogo_literatura"
TBL_DESCRIPTIVO_UNI = "tesis.preprocesamiento.descriptivo_univariado"
TBL_DESCRIPTIVO_BI = "tesis.preprocesamiento.descriptivo_bivariado"
TBL_DIAGNOSTICOS = "tesis.preprocesamiento.diagnosticos_covariables"
TBL_REDUNDANCIA = "tesis.preprocesamiento.redundancia_covariables"
TBL_DECISION = "tesis.preprocesamiento.decision_covariables"
# R-02: soporte de cada candidata en los municipios objetivo.
TBL_SOPORTE = "tesis.preprocesamiento.soporte_covariables"
TBL_VERIFICACION = "tesis.preprocesamiento.verificacion_seleccion"
TBL_TRAZABILIDAD = "tesis.preprocesamiento.trazabilidad_covariables"
TBL_SELECCIONADAS = "tesis.preprocesamiento.covariables_seleccionadas"
# G7-B12: selección con y sin las covariables de signo contrario al esperado.
TBL_SENSIBILIDAD_SIGNO = "tesis.preprocesamiento.sensibilidad_signo_covariables"
# Sensibilidad de la estimación directa a la ventana temporal (G7-B2).
TBL_SENSIBILIDAD_VENTANA = "tesis.preprocesamiento.sensibilidad_ventana_temporal"
TBL_RESUMEN_VENTANA = "tesis.preprocesamiento.resumen_ventana_temporal"
TBL_VALIDACION_ANUAL = "tesis.preprocesamiento.validacion_anual_totales"

# ── Volumen para las figuras destinadas al documento ──────────────────────────
VOLUMEN_FIGURAS = "/Volumes/tesis/preprocesamiento/figuras_eda"

# ── Parámetros de estimación directa ──────────────────────────────────────────
BOOTSTRAP_REPLICAS = 2000
BOOTSTRAP_SEED = 42
# Período por defecto: ventana de N_MESES_VENTANA meses que CIERRA en (PER_ESTIMACION,
# MES_ESTIMACION); con 2018-12 y 12 meses es el año calendario 2018 (G7-B2). En un job se sobrescriben
# con los parámetros anio_estimacion, mes_estimacion y n_meses_ventana (ver `resolver_periodo` y
# `resolver_ventana`).
PER_ESTIMACION = 2018
MES_ESTIMACION = 12
MESES_TRIMESTRE = 3
# Ventana de la estimación directa (G7-B2): 12 = año calendario (por defecto; exige cierre en
# diciembre para coincidir con el corte anual de TerriData) o 3 = trimestre móvil (opcional).
N_MESES_VENTANA = 12
VENTANAS_PERMITIDAS = (MESES_TRIMESTRE, 12)
# Ventanas de la sensibilidad G7-B2 (analisis/sensibilidad_ventana_temporal.py): número de meses
# que cierran en (PER_ESTIMACION, MES_ESTIMACION). Con cierre en diciembre, ANIO es el año calendario.
VENTANAS_TEMPORALES = {"MES": 1, "TRIMESTRE": 3, "ANIO": 12}


def meses_ventana(per: int, mes: int, n_meses: int) -> list:
    """Lista los meses de la ventana de `n_meses` que termina en el mes indicado.

    La ventana se identifica por su mes de cierre y puede cruzar el año, igual que los trimestres
    móviles del anexo DANE.

    Args:
        per (int): Año del mes de cierre.
        mes (int): Mes de cierre, entre 1 y 12.
        n_meses (int): Número de meses de la ventana (1 = mes, 3 = trimestre, 12 = año).

    Returns:
        list[tuple[int, int]]: `n_meses` pares `(año, mes)` en orden cronológico.

    Casos de uso:
        Ventanas de la sensibilidad temporal (`VENTANAS_TEMPORALES`).

        >>> meses_ventana(2018, 12, 1)
        [(2018, 12)]
        >>> meses_ventana(2019, 1, 3)
        [(2018, 11), (2018, 12), (2019, 1)]
        >>> meses_ventana(2018, 12, 12)[0], len(meses_ventana(2018, 12, 12))
        ((2018, 1), 12)
    """
    meses = []
    for desfase in range(n_meses - 1, -1, -1):
        indice = per * 12 + (mes - 1) - desfase
        meses.append((indice // 12, indice % 12 + 1))
    return meses


def resolver_periodo(dbutils) -> tuple:
    """Resuelve el período a estimar a partir de los widgets del notebook o del job.

    El período es el mes de cierre de la ventana de estimación (ver `meses_ventana` y
    `resolver_ventana`).
    Declara los widgets `anio_estimacion` y `mes_estimacion` con `PER_ESTIMACION` y
    `MES_ESTIMACION` como valores por defecto y los lee. Un parámetro de job con el mismo
    nombre reemplaza el valor del widget.

    Args:
        dbutils: Objeto `dbutils` del notebook (se pasa explícitamente porque un módulo
            importado no tiene acceso a él).

    Returns:
        tuple: `(per, mes)`, ambos `int`, con `mes` entre 1 y 12.

    Raises:
        ValueError: Si el año o el mes no son enteros, o si el mes está fuera de 1-12.

    Casos de uso:
        En `estimacion_directa.py` y `dominios_sin_encuesta.py`:
        `PER_ESTIMACION, MES_ESTIMACION = resolver_periodo(dbutils)`. En ejecución
        interactiva sin parámetros devuelve `(2018, 12)`.
    """
    dbutils.widgets.text("anio_estimacion", str(PER_ESTIMACION), "Año a estimar")
    dbutils.widgets.text("mes_estimacion", str(MES_ESTIMACION), "Mes a estimar (1-12)")
    anio = dbutils.widgets.get("anio_estimacion").strip()
    mes = dbutils.widgets.get("mes_estimacion").strip()
    try:
        per, mes = int(anio), int(mes)
    except ValueError:
        raise ValueError(
            f"anio_estimacion y mes_estimacion deben ser enteros; se recibió "
            f"anio_estimacion={anio!r}, mes_estimacion={mes!r}."
        )
    if not 1 <= mes <= 12:
        raise ValueError(f"mes_estimacion debe estar entre 1 y 12; se recibió {mes}.")
    return per, mes


def resolver_ventana(dbutils, mes: int) -> int:
    """Resuelve el número de meses de la ventana de estimación (widget o parámetro de job).

    Declara el widget `n_meses_ventana` con `N_MESES_VENTANA` por defecto y lo lee. Solo se admiten
    las ventanas de `VENTANAS_PERMITIDAS`: el año (12, por defecto) y el trimestre móvil (3). El
    año exige cierre en diciembre: 12 meses con otro cierre no son un año calendario y no se
    alinean con los indicadores de TerriData, que son anuales con corte a diciembre.

    Args:
        dbutils: Objeto `dbutils` del notebook.
        mes (int): Mes de cierre ya resuelto con `resolver_periodo`.

    Returns:
        int: Número de meses de la ventana (12 o 3).

    Raises:
        ValueError: Si el valor no es entero, no está en `VENTANAS_PERMITIDAS` o es 12 con un
            mes de cierre distinto de diciembre.

    Casos de uso:
        En `estimacion_directa.py`: `N_MESES = resolver_ventana(dbutils, MES_ESTIMACION)`. Sin
        parámetros devuelve 12 (año 2018 con el período por defecto); con
        `--params n_meses_ventana=3` estima el trimestre móvil.
    """
    dbutils.widgets.text(
        "n_meses_ventana", str(N_MESES_VENTANA), "Meses de la ventana (12 o 3)"
    )
    return validar_ventana(dbutils.widgets.get("n_meses_ventana").strip(), mes)


def validar_ventana(valor, mes: int) -> int:
    """Valida el número de meses de la ventana frente al mes de cierre.

    Args:
        valor (str | int): Número de meses recibido (texto del widget o entero).
        mes (int): Mes de cierre, entre 1 y 12.

    Returns:
        int: El número de meses como entero.

    Raises:
        ValueError: Si no es entero, no está en `VENTANAS_PERMITIDAS` o es 12 con un mes de
            cierre distinto de diciembre.

    Casos de uso:
        Lógica de `resolver_ventana`, separada para probarla sin `dbutils`.

        >>> validar_ventana("12", 12), validar_ventana(3, 6)
        (12, 3)
        >>> validar_ventana("12", 6)
        Traceback (most recent call last):
        ...
        ValueError: La ventana anual exige cierre en diciembre (mes_estimacion=12); se recibió mes_estimacion=6.
        >>> validar_ventana("1", 12)
        Traceback (most recent call last):
        ...
        ValueError: n_meses_ventana debe ser uno de (3, 12); se recibió '1'.
    """
    try:
        n_meses = int(valor)
    except ValueError:
        n_meses = None
    if n_meses not in VENTANAS_PERMITIDAS:
        raise ValueError(
            f"n_meses_ventana debe ser uno de {VENTANAS_PERMITIDAS}; se recibió {str(valor)!r}."
        )
    if n_meses == 12 and mes != 12:
        raise ValueError(
            "La ventana anual exige cierre en diciembre (mes_estimacion=12); se recibió "
            f"mes_estimacion={mes}."
        )
    return n_meses


# Columnas de agrupación para estimación directa. El dominio es la ciudad con su área metropolitana
# tal como la identifica el campo AREA de la GEIH (ver dim_dominio_geih); CODIGO_DOMINIO es el código
# DIVIPOLA de la capital.
GRUPO_COLS = [
    "PER",
    "MES",
    "CODIGO_DEPARTAMENTO",
    "DEPARTAMENTO",
    "CODIGO_DOMINIO",
    "NOMBRE_DOMINIO",
    "TIPO_DOMINIO",
]

# Columnas que NO son covariables (identificación, ventana, conteos muestrales y estimaciones)
METADATA_COLS = [
    "PER",
    "MES",
    "PERIODO",
    "N_MESES_VENTANA",
    "CODIGO_DEPARTAMENTO",
    "DEPARTAMENTO",
    "CODIGO_DOMINIO",
    "NOMBRE_DOMINIO",
    "TIPO_DOMINIO",
    "N_MUNICIPIOS",
    "N_PEA",
    "N_DESOCUPADOS",
    "PEA_EXPANDIDA",
    "TASA_DESEMPLEO_PCT",
    "SE_BOOTSTRAP_PCT",
    "IC_INF_PCT",
    "IC_SUP_PCT",
    "AMPLITUD_IC",
    "CV_PORCENTAJE",
    # G7-B3: control analítico de la varianza y número de viviendas (conglomerados del bootstrap)
    "SE_TAYLOR_PCT",
    "N_VIVIENDAS",
    # R-58: TD del DANE de la misma ventana y diferencia con la directa (las calcula
    # estimacion_directa; NULL si el anexo no cubre el período)
    "TD_DANE_PCT",
    "DIF_TD_PP",
]

# Columnas a excluir de TerriData al hacer el join: las de identificación ya existen en las
# estimaciones o no son indicadores (no se pueden agregar al dominio). Las *_NORMALIZADO salieron
# de TerriData en R-52.
COLUMNAS_EXCLUIR_JOIN = [
    "CODIGO_DEPARTAMENTO",
    "DEPARTAMENTO",
    "CODIGO_ENTIDAD",
    "ENTIDAD",
    "ANO",
    "MES",
]

# Variable respuesta
VARIABLE_OBJETIVO = "TASA_DESEMPLEO_PCT"

# Población de 15 años y más: la población en edad de trabajar (PET) de la serie GEIH con
# proyecciones CNPV 2018 («toman PET de 15 años y más», DANE, actualización de la serie
# 2007-2021, PDF 30), aproximación de la PEA municipal, que no se publica. Es el peso del
# benchmarking de nivel 2 en el modelo (modelo/shared/benchmarking.py) y el peso por defecto
# (peso «PET») de los indicadores fuera del catálogo al agregarlos a un dominio de varios
# municipios; los del catálogo usan su propio denominador (shared/reglas_agregacion.py).
# Se suman los grupos quinquenales por sexo de 15-19 a 80 y más de TerriData (02001xxxx hombres,
# 02002xxxx mujeres; 0004 = 15-19 … 0017 = 80+). No se usa «población total − 0 a 14» porque la
# población total (010010009) viene de otra fuente y no cuadra con la suma de los grupos de edad.
COLS_PESO_POBLACION = [
    f"0200{sexo}0{grupo:03d}" for sexo in ("1", "2") for grupo in range(4, 18)
]
# Expresión SQL del peso: NULL si a un municipio le falta cualquier grupo de edad.
EXPR_PESO_POBLACION = " + ".join(
    f"try_cast(`{c}` AS DOUBLE)" for c in COLS_PESO_POBLACION
)

# ── Umbrales de calidad del CV (G7-B7) ───────────────────────────────────────
# Regla única del proyecto: confiable si CV < 5 %, aceptable si 5 % ≤ CV < 20 %, no confiable si
# CV ≥ 20 %. La usan la estimación directa, el EBLUP y la predicción sintética (y deben coincidir
# con CV_CONFIABLE / CV_ACEPTABLE de modelo/shared/config.py).
# - 5 %: es la precisión con la que el DANE dimensionó la muestra de la GEIH: error estándar
#   relativo de la tasa de desempleo no mayor al 5 % para una tasa del 10 %, con el deff de cada
#   dominio (DANE, Metodología GEIH v9, 2016, PDF 12; meta de precisión en PDF 15 y 18). CV < 5 %
#   se lee como «alcanza la precisión de diseño de la GEIH».
# - 20 %: no hay un límite universal, pero varios institutos nacionales de estadística declaran
#   «no publicable» un dato con CV > 20 % (Molina, 2019, CEPAL, PDF 16-17).
# Para una tasa del 10 %, un CV del 5 % da un IC95 de ≈ [9,0; 11,0] y uno del 20 % ≈ [6,1; 13,9].
# No se usa 15 %/30 %: 15 % no tiene respaldo en la bibliografía del proyecto, y el 30 % aparece
# solo como ejemplo para proporciones pequeñas (ENUSC 2018, PDF 21) o como filtro de entrada con
# el CV logarítmico, que es otra medida (DANE, nota SAE 2024, PDF 11 y 22: CVLOG ≤ 30).
CV_CONFIABLE = 5.0  # CV < 5 %   → confiable
CV_ACEPTABLE = 20.0  # CV < 20 %  → aceptable; >= 20 % → no confiable

# ── Pre-filtrado (independiente de la variable respuesta) ─────────────────────
# Umbral de coeficiente de variación por debajo del cual la columna se considera
# constante a efectos prácticos. Es invariante a las unidades del indicador.
CV_MINIMO = 0.001
# Proporción máxima de dominios que puede acumular el valor modal.
PROP_MODAL_MAXIMA = 0.90
# Magnitud de correlación a partir de la cual dos covariables se consideran duplicadas.
UMBRAL_DUPLICADO = 0.999

# ── Diagnóstico y selección ──────────────────────────────────────────────────
# Magnitud de correlación a partir de la cual dos candidatas se consideran redundantes y
# solo una de ellas puede entrar al modelo.
UMBRAL_REDUNDANCIA = 0.80
# Cambio máximo tolerado en la correlación con la respuesta al excluir un dominio.
UMBRAL_DELTA_LOO = 0.10
# Cota de parsimonia (R-07): observaciones por parámetro. Con 23 dominios, la regla habitual de
# regresión de 10 a 20 observaciones por parámetro da 1 o 2 covariables, y Morales et al. (2021,
# p. 453) piden no sobreparametrizar cuando se predice fuera de la muestra, como aquí. El 10 es el
# extremo permisivo de esa regla: es una convención externa al libro, no un valor que él fije.
OBS_POR_PARAMETRO = 10


def cota_covariables(
    n_dominios: int, obs_por_parametro: int = OBS_POR_PARAMETRO
) -> int:
    """Número máximo de covariables que admite un conjunto de `n_dominios` dominios.

    Se calcula desde n en lugar de fijarse (antes ``P_MAXIMO = 4``, «n/5» sin referencia): con 23
    dominios da 2 y con 22 (un dominio retirado en la validación cruzada) también 2. Siempre se
    admite al menos una.

    Args:
        n_dominios (int): Número de dominios con estimación directa.
        obs_por_parametro (int): Observaciones exigidas por covariable.

    Returns:
        int: ``max(1, n_dominios // obs_por_parametro)``.

    Example:
        >>> cota_covariables(23), cota_covariables(22), cota_covariables(5)
        (2, 2, 1)
    """
    return max(1, int(n_dominios) // int(obs_por_parametro))


# Soporte en los municipios objetivo (R-02): proporción mínima de objetivos dentro del rango
# [mín, máx] de los dominios por debajo de la cual la ficha advierte que usar la covariable
# obliga a extrapolar. Convención del proyecto (Morales et al., pp. 441 y 453, solo motivan la
# revisión); es advertencia, no filtro.
SOPORTE_MINIMO = 0.80
# Umbral de multicolinealidad para el conjunto finalmente seleccionado.
VIF_MAXIMO = 5.0
# Nivel de confianza del intervalo de Fisher para la correlación con la respuesta.
ALFA_IC_CORRELACION = 0.05
# Tasa de falsos descubrimientos (Benjamini-Hochberg) con la que se declara elegible una
# candidata, sobre la familia de todas las candidatas (G7-B9).
Q_FDR_ELEGIBILIDAD = 0.10
# Réplicas del remuestreo de dominios para la estabilidad de la elegibilidad (G7-B9, descriptiva).
REPLICAS_ESTABILIDAD = 1000

# ── Dominios objetivo sin cobertura muestral ─────────────────────────────────
# Códigos DIVIPOLA de los departamentos del estudio: Cauca (19) y Valle del Cauca (76).
DEPARTAMENTOS_OBJETIVO = [19, 76]
