# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Datos publicados DANE - Capa Bronce
# MAGIC
# MAGIC Carga las cifras **oficiales publicadas** del anexo «Mercado laboral según proyecciones CNPV 2018»
# MAGIC (DANE) desde el volumen de Unity Catalog hacia dos tablas en `tesis.geih_bronce`, para poder
# MAGIC contrastarlas con las estimaciones propias.
# MAGIC
# MAGIC ## Tablas
# MAGIC * `datos_nacionales`: total nacional, serie **mensual** 2016-2021 (pestaña `Tnal mensual`)
# MAGIC * `datos_municipales`: 23 ciudades y áreas metropolitanas, serie **trimestre móvil** 2016-2021
# MAGIC   (pestaña `areas trim movil`, filas 55-927; cada ciudad es un bloque de 38 filas)
# MAGIC
# MAGIC ## Transformaciones aplicadas
# MAGIC 1. Layout horizontal del Excel (12 columnas por año) convertido a formato largo
# MAGIC 2. Municipal: `ANIO`/`MES` corresponden al **mes de cierre** del trimestre móvil
# MAGIC    (``Dic 16 - Feb 17`` → 2017, 2), igual que `estimacion_directa.py`
# MAGIC 3. Población total, PEA, empleados y desempleados vienen en miles: se convierten a personas
# MAGIC 4. Las tasas (desempleo, empleo) se conservan en %
# MAGIC
# MAGIC Fuente: https://www.dane.gov.co/files/investigaciones/boletines/ech/nuevo-enfoque-conceptual-metodologico-2018/anexo-mercado-laboral-segun-proyecciones-CNPV2018.xlsx

# COMMAND ----------

# DBTITLE 1,Importación de librerías
import re

import pandas as pd
from pyspark.sql.types import (
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
)

from shared.config.geih_config import (
    ANIO_FIN_PUBLICADOS,
    ANIO_INICIO_PUBLICADOS,
    RUTA_DATOS_PUBLICADOS,
    TBL_DATOS_MUNICIPALES,
    TBL_DATOS_NACIONALES,
    URL_FUENTE_DATOS_PUBLICADOS,
)
from shared.utils.spark_utils import escribir_tabla

# COMMAND ----------

# DBTITLE 1,Constantes del Excel
HOJA_NACIONAL = "Tnal mensual"
HOJA_MUNICIPAL = "areas trim movil"

# Bloque de cada año: 12 columnas; el año 2001 empieza en la columna B (índice 1)
ANIO_BASE_EXCEL = 2001
COL_BASE_EXCEL = 1
COLUMNAS_POR_ANIO = 12

# Filas (1-based) de la pestaña nacional
FILAS_NACIONAL = {
    "TASA_EMPLEO": 16,
    "TASA_DESEMPLEO": 17,
    "POBLACION_TOTAL": 29,
    "PEA": 31,
    "EMPLEADOS": 32,
    "DESEMPLEADOS": 33,
}

# Desplazamiento de cada indicador respecto a la fila título de la ciudad
OFFSETS_CIUDAD = {
    "TASA_EMPLEO": 7,
    "TASA_DESEMPLEO": 8,
    "POBLACION_TOTAL": 20,
    "PEA": 22,
    "EMPLEADOS": 23,
    "DESEMPLEADOS": 24,
}
OFFSET_ETIQUETAS_CIUDAD = 4
FILA_INICIO_CIUDADES = 55
FILA_FIN_CIUDADES = 927

# Texto con que empieza la etiqueta de cada indicador en la columna A (validación del layout)
ETIQUETAS_ESPERADAS = {
    "TASA_EMPLEO": "TO",
    "TASA_DESEMPLEO": "TD",
    "POBLACION_TOTAL": "Población total",
    "PEA": "Fuerza de trabajo",
    "EMPLEADOS": "Ocupados",
    "DESEMPLEADOS": "Desocupados",
}

INDICADORES_EN_MILES = ["POBLACION_TOTAL", "PEA", "EMPLEADOS", "DESEMPLEADOS"]
INDICADORES = list(FILAS_NACIONAL.keys())

SCHEMA_NACIONAL = StructType(
    [
        StructField("ANIO", LongType()),
        StructField("MES", LongType()),
        StructField("TASA_DESEMPLEO", DoubleType()),
        StructField("TASA_EMPLEO", DoubleType()),
        StructField("POBLACION_TOTAL", LongType()),
        StructField("PEA", LongType()),
        StructField("EMPLEADOS", LongType()),
        StructField("DESEMPLEADOS", LongType()),
    ]
)

SCHEMA_MUNICIPAL = StructType(
    [
        StructField("ANIO", LongType()),
        StructField("MES", LongType()),
        StructField("TRIMESTRE_MOVIL", StringType()),
        StructField("CIUDAD", StringType()),
        StructField("TASA_DESEMPLEO", DoubleType()),
        StructField("TASA_EMPLEO", DoubleType()),
        StructField("POBLACION_TOTAL", LongType()),
        StructField("PEA", LongType()),
        StructField("EMPLEADOS", LongType()),
        StructField("DESEMPLEADOS", LongType()),
    ]
)

# COMMAND ----------


# DBTITLE 1,Funciones de extracción
def leer_hoja(ruta: str, hoja: str) -> pd.DataFrame:
    """Lee una pestaña del Excel sin cabecera, conservando la posición de filas y columnas.

    Args:
        ruta (str): Ruta del archivo ``.xlsx`` (ej. un archivo en ``/Volumes/...``).
        hoja (str): Nombre exacto de la pestaña.

    Returns:
        pd.DataFrame: Contenido crudo de la pestaña; la fila 1 del Excel es ``iloc[0]``
            y la columna A es ``iloc[:, 0]``.

    Raises:
        ValueError: Si la pestaña no existe en el archivo.

    Example:
        >>> hoja = leer_hoja(RUTA_DATOS_PUBLICADOS, HOJA_NACIONAL)
    """
    return pd.read_excel(ruta, sheet_name=hoja, header=None, engine="openpyxl")


def valor_celda(hoja: pd.DataFrame, fila: int, col: int):
    """Devuelve el valor de una celda indexada como en el Excel (fila 1-based, columna 0-based).

    Args:
        hoja (pd.DataFrame): Pestaña leída con ``leer_hoja``.
        fila (int): Número de fila de Excel (1-based).
        col (int): Índice de columna (0 = columna A).

    Returns:
        object: Valor de la celda, o ``None`` si está vacía o fuera de rango.

    Example:
        >>> valor_celda(hoja, 17, 181)  # TD nacional, Ene 2016
    """
    if fila - 1 >= hoja.shape[0] or col >= hoja.shape[1]:
        return None
    valor = hoja.iat[fila - 1, col]
    return None if pd.isna(valor) else valor


def validar_etiqueta(hoja: pd.DataFrame, fila: int, indicador: str) -> None:
    """Verifica que la fila apunte al indicador esperado (protege contra cambios de layout).

    Args:
        hoja (pd.DataFrame): Pestaña leída con ``leer_hoja``.
        fila (int): Fila de Excel (1-based) donde se espera el indicador.
        indicador (str): Clave de ``ETIQUETAS_ESPERADAS``.

    Raises:
        ValueError: Si la etiqueta de la columna A no empieza con el texto esperado.

    Example:
        >>> validar_etiqueta(hoja, 17, "TASA_DESEMPLEO")
    """
    etiqueta = str(valor_celda(hoja, fila, 0)).strip()
    if not etiqueta.startswith(ETIQUETAS_ESPERADAS[indicador]):
        raise ValueError(
            f"Fila {fila}: se esperaba '{ETIQUETAS_ESPERADAS[indicador]}' ({indicador}) "
            f"y se encontró '{etiqueta}'"
        )


def normalizar_etiqueta(texto) -> str:
    """Limpia la etiqueta de un trimestre móvil (espacios y asteriscos de nota).

    Args:
        texto (object): Etiqueta cruda de la celda (ej. ``"Abr - Jun "`` o ``"Mar*"``).

    Returns:
        str: Etiqueta sin ``*``, con espacios colapsados y recortada; ``""`` si no hay texto.

    Example:
        >>> normalizar_etiqueta("Ene -Mar ")
        'Ene -Mar'
    """
    if texto is None:
        return ""
    return re.sub(r"\s+", " ", str(texto).replace("*", "")).strip()


def convertir_valor(indicador: str, valor):
    """Convierte un valor del Excel al tipo y unidad de la tabla destino.

    Args:
        indicador (str): Nombre del indicador (clave de ``FILAS_NACIONAL``).
        valor (object): Valor numérico crudo de la celda, o ``None``.

    Returns:
        float | int | None: Tasa en % (float) o conteo en personas (int, miles × 1000);
            ``None`` si la celda está vacía o no es numérica.

    Example:
        >>> convertir_valor("PEA", 8385.007)
        8385007
    """
    if valor is None or isinstance(valor, str):
        return None
    if indicador in INDICADORES_EN_MILES:
        return int(round(float(valor) * 1000))
    return float(valor)


def extraer_registros(
    hoja: pd.DataFrame,
    filas: dict,
    fila_etiquetas: int,
    es_trimestre_movil: bool,
) -> list:
    """Recorre los bloques anuales de una serie y arma un registro por período.

    Args:
        hoja (pd.DataFrame): Pestaña leída con ``leer_hoja``.
        filas (dict): Mapa indicador → fila de Excel (1-based) con los 6 indicadores.
        fila_etiquetas (int): Fila de Excel con las etiquetas de mes / trimestre móvil.
        es_trimestre_movil (bool): Si es ``True``, ``ANIO``/``MES`` son el mes de cierre
            del trimestre (las columnas 10 y 11 de cada bloque cierran en enero y febrero del
            año siguiente); si es ``False`` la serie es mensual y ``MES`` es la posición 1-12.

    Returns:
        list[dict]: Registros con ``ANIO``, ``MES``, ``TRIMESTRE_MOVIL`` (cadena vacía en la
            serie mensual) y los seis indicadores, solo para años en
            [``ANIO_INICIO_PUBLICADOS``, ``ANIO_FIN_PUBLICADOS``]. Se omiten períodos sin datos.

    Example:
        >>> extraer_registros(hoja, FILAS_NACIONAL, 13, False)
    """
    primer_bloque = ANIO_INICIO_PUBLICADOS - (1 if es_trimestre_movil else 0)
    registros = []
    for anio_bloque in range(primer_bloque, ANIO_FIN_PUBLICADOS + 1):
        col_inicio = COL_BASE_EXCEL + COLUMNAS_POR_ANIO * (
            anio_bloque - ANIO_BASE_EXCEL
        )
        for c in range(COLUMNAS_POR_ANIO):
            if es_trimestre_movil:
                anio = anio_bloque + (c + 2) // 12
                mes = (c + 2) % 12 + 1
            else:
                anio, mes = anio_bloque, c + 1
            if not ANIO_INICIO_PUBLICADOS <= anio <= ANIO_FIN_PUBLICADOS:
                continue

            valores = {
                ind: convertir_valor(ind, valor_celda(hoja, fila, col_inicio + c))
                for ind, fila in filas.items()
            }
            if all(v is None for v in valores.values()):
                continue
            etiqueta = normalizar_etiqueta(
                valor_celda(hoja, fila_etiquetas, col_inicio + c)
            )
            registros.append(
                {"ANIO": anio, "MES": mes, "TRIMESTRE_MOVIL": etiqueta, **valores}
            )
    return registros


def cargar_nacional(ruta: str) -> list:
    """Extrae la serie nacional mensual de la pestaña ``Tnal mensual``.

    Args:
        ruta (str): Ruta del archivo ``.xlsx``.

    Returns:
        list[dict]: Un registro por mes entre 2016 y 2021 (ver ``extraer_registros``).

    Raises:
        ValueError: Si las filas del Excel no corresponden a los indicadores esperados.

    Example:
        >>> registros = cargar_nacional(RUTA_DATOS_PUBLICADOS)
    """
    hoja = leer_hoja(ruta, HOJA_NACIONAL)
    for indicador, fila in FILAS_NACIONAL.items():
        validar_etiqueta(hoja, fila, indicador)
    return extraer_registros(hoja, FILAS_NACIONAL, 13, es_trimestre_movil=False)


def cargar_municipal(ruta: str) -> list:
    """Extrae la serie de trimestre móvil de cada ciudad de la pestaña ``areas trim movil``.

    Detecta cada ciudad en las filas 55-927: es un título (columna A) cuya fila siguiente dice
    «Serie trimestre móvil». Los totales (10 / 23 ciudades) quedan fuera del rango.

    Args:
        ruta (str): Ruta del archivo ``.xlsx``.

    Returns:
        list[dict]: Registros por ciudad y trimestre móvil, con la clave extra ``CIUDAD``.

    Raises:
        ValueError: Si no se detecta ninguna ciudad o el layout de un bloque no coincide.

    Example:
        >>> registros = cargar_municipal(RUTA_DATOS_PUBLICADOS)
    """
    hoja = leer_hoja(ruta, HOJA_MUNICIPAL)
    registros = []
    ciudades = []
    for fila in range(FILA_INICIO_CIUDADES, FILA_FIN_CIUDADES + 1):
        titulo = valor_celda(hoja, fila, 0)
        siguiente = valor_celda(hoja, fila + 1, 0)
        if titulo is None or not str(siguiente).startswith("Serie trimestre"):
            continue
        filas = {ind: fila + off for ind, off in OFFSETS_CIUDAD.items()}
        for indicador, fila_ind in filas.items():
            validar_etiqueta(hoja, fila_ind, indicador)
        ciudad = str(titulo).strip()
        ciudades.append(ciudad)
        for registro in extraer_registros(
            hoja,
            filas,
            fila + OFFSET_ETIQUETAS_CIUDAD,
            es_trimestre_movil=True,
        ):
            registros.append({"CIUDAD": ciudad, **registro})
    if not ciudades:
        raise ValueError("No se detectó ninguna ciudad en la pestaña municipal")
    print(f"Ciudades detectadas ({len(ciudades)}): {ciudades}")
    return registros


# COMMAND ----------

# DBTITLE 1,Extracción desde el Excel
registros_nacional = cargar_nacional(RUTA_DATOS_PUBLICADOS)
registros_municipal = cargar_municipal(RUTA_DATOS_PUBLICADOS)

df_nacional = spark.createDataFrame(
    [tuple(r[f.name] for f in SCHEMA_NACIONAL.fields) for r in registros_nacional],
    schema=SCHEMA_NACIONAL,
)
df_municipal = spark.createDataFrame(
    [tuple(r[f.name] for f in SCHEMA_MUNICIPAL.fields) for r in registros_municipal],
    schema=SCHEMA_MUNICIPAL,
)

# COMMAND ----------


# DBTITLE 1,Validaciones (solo informativas)
def reportar(nombre: str, ok: bool, detalle: str = "") -> None:
    """Imprime el resultado de una validación sin detener la escritura.

    Args:
        nombre (str): Descripción de la validación.
        ok (bool): ``True`` si la validación pasó.
        detalle (str): Información adicional para el mensaje. Por defecto ``""``.

    Example:
        >>> reportar("Nacional = 72 filas", True, "72")
    """
    print(f"[{'PASS' if ok else 'FAIL'}] {nombre} {detalle}".rstrip())


def validar(df, claves: list, filas_esperadas: int, nombre: str) -> None:
    """Valida conteo, duplicados, rango de la tasa de desempleo y coherencia PEA.

    Args:
        df (DataFrame): Tabla a validar (nacional o municipal).
        claves (list[str]): Columnas que identifican de forma única un registro.
        filas_esperadas (int): Número de filas esperado si la serie está completa.
        nombre (str): Etiqueta de la tabla para los mensajes.

    Example:
        >>> validar(df_nacional, ["ANIO", "MES"], 72, "datos_nacionales")
    """
    n = df.count()
    reportar(
        f"{nombre}: filas == {filas_esperadas}", n == filas_esperadas, f"(real: {n})"
    )
    duplicados = n - df.dropDuplicates(claves).count()
    reportar(
        f"{nombre}: sin duplicados por {claves}",
        duplicados == 0,
        f"(duplicados: {duplicados})",
    )
    fuera = df.filter((df.TASA_DESEMPLEO < 0) | (df.TASA_DESEMPLEO > 100)).count()
    reportar(
        f"{nombre}: TASA_DESEMPLEO en [0, 100]",
        fuera == 0,
        f"(fuera de rango: {fuera})",
    )
    incoherentes = df.filter(
        (df.PEA - df.EMPLEADOS - df.DESEMPLEADOS > 2)
        | (df.PEA - df.EMPLEADOS - df.DESEMPLEADOS < -2)
    ).count()
    reportar(
        f"{nombre}: PEA == EMPLEADOS + DESEMPLEADOS",
        incoherentes == 0,
        f"(incoherentes: {incoherentes})",
    )


n_meses = (ANIO_FIN_PUBLICADOS - ANIO_INICIO_PUBLICADOS + 1) * 12
n_ciudades = df_municipal.select("CIUDAD").distinct().count()
validar(df_nacional, ["ANIO", "MES"], n_meses, "datos_nacionales")
validar(
    df_municipal, ["CIUDAD", "ANIO", "MES"], n_ciudades * n_meses, "datos_municipales"
)

# COMMAND ----------

# DBTITLE 1,Escritura y metadatos de las tablas
DESCRIPCION_COLUMNAS = {
    "ANIO": "Año calendario (en la serie de trimestre móvil, año del mes de cierre)",
    "MES": "Mes calendario 1-12 (en la serie de trimestre móvil, mes de cierre)",
    "TRIMESTRE_MOVIL": "Etiqueta del trimestre móvil tal como la publica el DANE",
    "CIUDAD": "Ciudad o área metropolitana tal como la publica el DANE",
    "TASA_DESEMPLEO": "Tasa de desempleo (TD), en %",
    "TASA_EMPLEO": "Tasa de ocupación (TO), en %",
    "POBLACION_TOTAL": "Población total, en personas (el anexo la publica en miles)",
    "PEA": "Población económicamente activa (fuerza de trabajo), en personas",
    "EMPLEADOS": "Población ocupada, en personas",
    "DESEMPLEADOS": "Población desocupada, en personas",
}

DESCRIPCION_TABLAS = {
    TBL_DATOS_NACIONALES: (
        "Cifras oficiales publicadas por el DANE del mercado laboral total nacional, serie "
        f"mensual {ANIO_INICIO_PUBLICADOS}-{ANIO_FIN_PUBLICADOS} (pestaña '{HOJA_NACIONAL}' del "
        "anexo Mercado laboral según proyecciones CNPV 2018). Tasas en %, poblaciones en "
        f"personas. Fuente: {URL_FUENTE_DATOS_PUBLICADOS}"
    ),
    TBL_DATOS_MUNICIPALES: (
        "Cifras oficiales publicadas por el DANE del mercado laboral de las 23 ciudades y áreas "
        f"metropolitanas, serie de trimestre móvil {ANIO_INICIO_PUBLICADOS}-{ANIO_FIN_PUBLICADOS} "
        f"(pestaña '{HOJA_MUNICIPAL}' del anexo Mercado laboral según proyecciones CNPV 2018). "
        "ANIO y MES son el mes de cierre del trimestre. Tasas en %, poblaciones en personas. "
        f"Fuente: {URL_FUENTE_DATOS_PUBLICADOS}"
    ),
}


def describir_tabla(tabla: str, df) -> None:
    """Agrega el comentario de tabla y de cada columna en Unity Catalog.

    Args:
        tabla (str): Nombre completo ``catalog.schema.table`` de una tabla ya escrita.
        df (DataFrame): DataFrame escrito; sus columnas determinan los comentarios de columna.

    Example:
        >>> describir_tabla(TBL_DATOS_NACIONALES, df_nacional)
    """
    descripcion = DESCRIPCION_TABLAS[tabla].replace("'", "")
    spark.sql(f"COMMENT ON TABLE {tabla} IS '{descripcion}'")
    for columna in df.columns:
        texto = DESCRIPCION_COLUMNAS[columna].replace("'", "")
        spark.sql(f"COMMENT ON COLUMN {tabla}.{columna} IS '{texto}'")


for tabla, df in [
    (TBL_DATOS_NACIONALES, df_nacional),
    (TBL_DATOS_MUNICIPALES, df_municipal),
]:
    escribir_tabla(df, tabla)
    describir_tabla(tabla, df)
    print(f"Tabla cargada: {tabla}")
