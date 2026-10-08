"""Parámetros del preprocesamiento, el análisis descriptivo y la selección de covariables.

Reúne las tablas fuente y destino, las columnas de metadatos, los parámetros de la estimación
directa, los umbrales de calidad, los criterios de pre-filtrado y los de diagnóstico y
selección de covariables.
"""

# ── Tablas fuente ─────────────────────────────────────────────────────────────
TBL_MERCADO_LABORAL = "tesis.geih_oro.mercado_laboral"
TBL_TERRIDATA = "tesis.terridata.terridata_extendido_plata"
TBL_DIM_INDICADORES = "tesis.dim.dim_indicadores"
# Membresía municipio → dominio (ciudad o ciudad A.M.), ver dimensiones/dim_dominio_geih.py.
TBL_DIM_DOMINIO = "tesis.dim.dim_dominio_geih"
# Cifras oficiales del DANE por dominio (validación de la estimación directa).
TBL_DATOS_MUNICIPALES = "tesis.geih_bronce.datos_municipales"
NOMBRE_TOTAL_23 = "Total 23 ciudades y A.M."

# ── Tablas destino ────────────────────────────────────────────────────────────
TBL_ESTIMACION_DIRECTA = "tesis.preprocesamiento.tasa_desempleo_municipal"
TBL_COVARIABLES = "tesis.preprocesamiento.tasa_desempleo_covariables"
TBL_PREFILTRADAS = "tesis.preprocesamiento.covariables_prefiltradas"
TBL_CASCADA = "tesis.preprocesamiento.cascada_prefiltrado"
TBL_SENSIBILIDAD = "tesis.preprocesamiento.sensibilidad_variabilidad"
TBL_SIN_ENCUESTA = "tesis.preprocesamiento.municipios_sin_encuesta"
TBL_CATALOGO = "tesis.preprocesamiento.catalogo_literatura"
TBL_DESCRIPTIVO_UNI = "tesis.preprocesamiento.descriptivo_univariado"
TBL_DESCRIPTIVO_BI = "tesis.preprocesamiento.descriptivo_bivariado"
TBL_DIAGNOSTICOS = "tesis.preprocesamiento.diagnosticos_covariables"
TBL_ROBUSTEZ = "tesis.preprocesamiento.robustez_covariables"
TBL_REDUNDANCIA = "tesis.preprocesamiento.redundancia_covariables"
TBL_DECISION = "tesis.preprocesamiento.decision_covariables"
TBL_VERIFICACION = "tesis.preprocesamiento.verificacion_seleccion"
TBL_TRAZABILIDAD = "tesis.preprocesamiento.trazabilidad_covariables"
TBL_CANDIDATAS = "tesis.preprocesamiento.covariables_candidatas"
TBL_SELECCIONADAS = "tesis.preprocesamiento.covariables_seleccionadas"

# ── Volumen para las figuras destinadas al documento ──────────────────────────
VOLUMEN_FIGURAS = "/Volumes/tesis/preprocesamiento/figuras_eda"

# ── Parámetros de estimación directa ──────────────────────────────────────────
BOOTSTRAP_REPLICAS = 2000
BOOTSTRAP_SEED = 42
# Período por defecto: trimestre móvil que CIERRA en (PER_ESTIMACION, MES_ESTIMACION); 2018-12 es
# Oct-Dic 2018. En un job se sobrescribe con los parámetros anio_estimacion y mes_estimacion
# (ver `resolver_periodo`).
PER_ESTIMACION = 2018
MES_ESTIMACION = 12
MESES_TRIMESTRE = 3


def meses_trimestre_movil(per: int, mes: int) -> list:
    """Lista los tres meses del trimestre móvil que termina en el mes indicado.

    Sigue la convención del anexo DANE «areas trim movil»: el trimestre se identifica por su
    mes de cierre y puede cruzar el año (Nov-Ene, Dic-Feb).

    Args:
        per (int): Año del mes de cierre.
        mes (int): Mes de cierre, entre 1 y 12.

    Returns:
        list[tuple[int, int]]: Tres pares `(año, mes)` en orden cronológico.

    Casos de uso:
        `meses_trimestre_movil(2018, 12)` → `[(2018, 10), (2018, 11), (2018, 12)]`;
        `meses_trimestre_movil(2019, 1)` → `[(2018, 11), (2018, 12), (2019, 1)]`.
    """
    meses = []
    for desfase in range(MESES_TRIMESTRE - 1, -1, -1):
        indice = per * 12 + (mes - 1) - desfase
        meses.append((indice // 12, indice % 12 + 1))
    return meses


def etiqueta_trimestre_movil(per: int, mes: int) -> str:
    """Arma la etiqueta legible del trimestre móvil que termina en el mes indicado.

    Args:
        per (int): Año del mes de cierre.
        mes (int): Mes de cierre, entre 1 y 12.

    Returns:
        str: Etiqueta «Mes inicial-Mes final año(s)»; si el trimestre cruza el año incluye
            ambos años.

    Casos de uso:
        `etiqueta_trimestre_movil(2018, 12)` → `"Oct-Dic 2018"`;
        `etiqueta_trimestre_movil(2019, 1)` → `"Nov 2018-Ene 2019"`.
    """
    nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    (anio_ini, mes_ini), *_, (anio_fin, mes_fin) = meses_trimestre_movil(per, mes)
    if anio_ini == anio_fin:
        return f"{nombres[mes_ini - 1]}-{nombres[mes_fin - 1]} {anio_fin}"
    return f"{nombres[mes_ini - 1]} {anio_ini}-{nombres[mes_fin - 1]} {anio_fin}"


def resolver_periodo(dbutils) -> tuple:
    """Resuelve el período a estimar a partir de los widgets del notebook o del job.

    El período es el mes de cierre del trimestre móvil (ver `meses_trimestre_movil`).
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

# Columnas que NO son covariables (identificación + estimaciones)
METADATA_COLS = [
    "PER",
    "MES",
    "TRIMESTRE_MOVIL",
    "CODIGO_DEPARTAMENTO",
    "DEPARTAMENTO",
    "CODIGO_DOMINIO",
    "NOMBRE_DOMINIO",
    "TIPO_DOMINIO",
    "N_MUNICIPIOS",
    "PEA_EXPANDIDA",
    "TASA_DESEMPLEO_PCT",
    "SE_BOOTSTRAP_PCT",
    "IC_INF_PCT",
    "IC_SUP_PCT",
    "AMPLITUD_IC",
    "CV_PORCENTAJE",
]

# Columnas a excluir de TerriData al hacer el join: las de identificación ya existen en las
# estimaciones y las de texto normalizado no son indicadores (no se pueden agregar al dominio).
COLUMNAS_EXCLUIR_JOIN = [
    "CODIGO_DEPARTAMENTO",
    "DEPARTAMENTO",
    "CODIGO_ENTIDAD",
    "ENTIDAD",
    "ANO",
    "MES",
    "DEPARTAMENTO_NORMALIZADO",
    "ENTIDAD_NORMALIZADO",
]

# Variable respuesta
VARIABLE_OBJETIVO = "TASA_DESEMPLEO_PCT"

# Peso con el que se agregan las covariables municipales a un dominio de varios municipios:
# población de 15 a 59 años de TerriData («Población entre 15 y 59 años»), aproximación de la PEA
# municipal, que no se publica. Es el mismo peso del benchmarking de nivel 2 en el modelo (ver
# preprocesamiento/shared/agregacion_dominios.py y modelo/shared/benchmarking.py).
COD_PESO_POBLACION = "020090014"

# Umbrales de calidad de estimación (criterios DANE/CEPAL)
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
# Número máximo de covariables por parsimonia: n/5 con n = 23 dominios.
P_MAXIMO = 4
# Umbral de multicolinealidad para el conjunto finalmente seleccionado.
VIF_MAXIMO = 5.0
# Nivel de confianza del intervalo de Fisher para la correlación con la respuesta.
ALFA_IC_CORRELACION = 0.05

# ── Dominios objetivo sin cobertura muestral ─────────────────────────────────
# Códigos DIVIPOLA de los departamentos del estudio: Cauca (19) y Valle del Cauca (76).
DEPARTAMENTOS_OBJETIVO = [19, 76]
