# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Ingesta de Datos GEIH - Capa Bronce
# MAGIC
# MAGIC Este notebook realiza la ingesta y carga inicial de los datos de la **Gran Encuesta Integrada de Hogares (GEIH)** en la capa bronce del lakehouse.
# MAGIC
# MAGIC ## Propósito
# MAGIC Cargar archivos CSV desde volúmenes de Unity Catalog y transformarlos en tablas estructuradas en el catálogo `tesis.geih_bronce`, aplicando transformaciones básicas según la estructura de datos.
# MAGIC
# MAGIC ## Estructura de Datos
# MAGIC
# MAGIC La GEIH se organiza en diferentes **módulos** y **secciones**:
# MAGIC
# MAGIC ### Módulos
# MAGIC * **caracteristicas_generales**: Información demográfica y características de los hogares
# MAGIC * **fuerza_trabajo**: Información sobre población económicamente activa
# MAGIC * **ocupados**: Datos de personas ocupadas/empleadas
# MAGIC * **no_ocupados**: Datos de personas desocupadas/desempleadas
# MAGIC * **inactivos**: Población económicamente inactiva
# MAGIC * **fex**: Factores de expansión para proyecciones estadísticas
# MAGIC
# MAGIC ### Secciones Geográficas (solo marco antiguo)
# MAGIC * **cabecera**: Zonas urbanas principales
# MAGIC * **resto**: Zonas rurales y áreas no urbanas
# MAGIC * **area**: Consolidado de todas las áreas
# MAGIC
# MAGIC ### Marcos Muestrales
# MAGIC * **Marco antiguo**: Datos hasta cierto periodo con división por secciones
# MAGIC * **Marco nuevo**: Datos recientes sin división por secciones
# MAGIC
# MAGIC ## Transformaciones Aplicadas
# MAGIC
# MAGIC 1. **Extracción de metadata**: Se agrega columna `archivo_origen` con el nombre del archivo fuente
# MAGIC 2. **Normalización de campos**:
# MAGIC    - Columna `AREA` para sección "resto" (inicializada como NULL)
# MAGIC    - Columna `MES` extraída del nombre de archivo para módulos específicos
# MAGIC 3. **Ajustes específicos por módulo**:
# MAGIC    - Fuerza de trabajo + resto: Campo `FT` con valor "1"
# MAGIC    - Fuerza de trabajo + marco antiguo: Limpieza de valores vacíos en `fex_c_2011`
# MAGIC
# MAGIC ## Configuración
# MAGIC Las tablas y rutas se definen en el diccionario `tablas_config` que mapea cada combinación de módulo/sección/marco a su tabla destino y ruta de origen.

# COMMAND ----------

# DBTITLE 1,Importación de librerías
# Importar funciones de PySpark necesarias para transformaciones
from pyspark.sql.functions import (
    lit,             # Para crear columnas con valores literales
    regexp_extract,  # Para extraer patrones con expresiones regulares
    col,             # Para referenciar columnas
    when,            # Para expresiones condicionales
    trim             # Para eliminar espacios en blanco
)

# COMMAND ----------

# DBTITLE 1,Configuracion de tablas
# Configuración de tablas GEIH
# Define para cada tabla: nombre destino, ruta de archivos CSV origen,
# sección geográfica, módulo temático, si requiere extracción de mes,
# y marco muestral (antiguo/nuevo)
tablas_config = {
    "config":[
        # ========== MARCO ANTIGUO - CARACTERÍSTICAS GENERALES ==========
        {
            "table_name": "tesis.geih_bronce.caracteristicas_generales_area_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/caracteristicas_generales/marco_antiguo/area/*.csv",
            "seccion": "area",
            "modulo": "caracteristicas_generales",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        {
            "table_name": "tesis.geih_bronce.caracteristicas_generales_cabecera_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/caracteristicas_generales/marco_antiguo/cabecera/*.csv",
            "seccion": "cabecera",
            "modulo": "caracteristicas_generales",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        {
            "table_name": "tesis.geih_bronce.caracteristicas_generales_resto_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/caracteristicas_generales/marco_antiguo/resto/*.csv",
            "seccion": "resto",
            "modulo": "caracteristicas_generales",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        
        # ========== MARCO ANTIGUO - FUERZA DE TRABAJO ==========
        {
            "table_name": "tesis.geih_bronce.fuerza_trabajo_area_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/fuerza_de_trabajo/marco_antiguo/area/*.csv",
            "seccion": "area",
            "modulo": "fuerza_trabajo",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        {
            "table_name": "tesis.geih_bronce.fuerza_trabajo_cabecera_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/fuerza_de_trabajo/marco_antiguo/cabecera/*.csv",
            "seccion": "cabecera",
            "modulo": "fuerza_trabajo",
            "aplicar_mes":True,  # Extrae mes del nombre de archivo
            "marco":"antiguo"
        },
        {
            "table_name": "tesis.geih_bronce.fuerza_trabajo_resto_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/fuerza_de_trabajo/marco_antiguo/resto/*.csv",
            "seccion": "resto",
            "modulo": "fuerza_trabajo",
            "aplicar_mes":True,  # Extrae mes del nombre de archivo
            "marco":"antiguo"
        },
        
        # ========== MARCO ANTIGUO - OCUPADOS ==========
        {
            "table_name": "tesis.geih_bronce.ocupados_area_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/ocupados/marco_antiguo/area/*.csv",
            "seccion": "area",
            "modulo": "ocupados",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        {
            "table_name": "tesis.geih_bronce.ocupados_cabecera_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/ocupados/marco_antiguo/cabecera/*.csv",
            "seccion": "cabecera",
            "modulo": "ocupados",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        {
            "table_name": "tesis.geih_bronce.ocupados_resto_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/ocupados/marco_antiguo/resto/*.csv",
            "seccion": "resto",
            "modulo": "ocupados",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        
        # ========== MARCO ANTIGUO - INACTIVOS ==========
        {
            "table_name": "tesis.geih_bronce.inactivos_area_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/inactivos/marco_antiguo/area/*.csv",
            "seccion": "area",
            "modulo": "inactivos",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        {
            "table_name": "tesis.geih_bronce.inactivos_cabecera_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/inactivos/marco_antiguo/cabecera/*.csv",
            "seccion": "cabecera",
            "modulo": "inactivos",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        {
            "table_name": "tesis.geih_bronce.inactivos_resto_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/inactivos/marco_antiguo/resto/*.csv",
            "seccion": "resto",
            "modulo": "inactivos",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        
        # ========== MARCO ANTIGUO - NO OCUPADOS ==========
        {
            "table_name": "tesis.geih_bronce.no_ocupados_area_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/no_ocupados/marco_antiguo/area/*.csv",
            "seccion": "area",
            "modulo": "no_ocupados",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        {
            "table_name": "tesis.geih_bronce.no_ocupados_cabecera_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/no_ocupados/marco_antiguo/cabecera/*.csv",
            "seccion": "cabecera",
            "modulo": "no_ocupados",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        {
            "table_name": "tesis.geih_bronce.no_ocupados_resto_marco_antiguo",
            "path": "/Volumes/tesis/geih_bronce/no_ocupados/marco_antiguo/resto/*.csv",
            "seccion": "resto",
            "modulo": "no_ocupados",
            "aplicar_mes":None,
            "marco":"antiguo"
        },
        
        # ========== MARCO NUEVO (sin división por sección) ==========
        {
            "table_name": "tesis.geih_bronce.caracteristicas_generales",
            "path": "/Volumes/tesis/geih_bronce/caracteristicas_generales/marco_nuevo/*.csv",
            "seccion": None,
            "modulo": "caracteristicas_generales",
            "aplicar_mes":None,
            "marco":"nuevo"
        },
        {
            "table_name": "tesis.geih_bronce.fuerza_trabajo",
            "path": "/Volumes/tesis/geih_bronce/fuerza_de_trabajo/marco_nuevo/*.csv",
            "seccion": None,
            "modulo": "fuerza_trabajo",
            "aplicar_mes":None,
            "marco":"nuevo"
        },
        {
            "table_name": "tesis.geih_bronce.ocupados",
            "path": "/Volumes/tesis/geih_bronce/ocupados/marco_nuevo/*.csv",
            "seccion": None,
            "modulo": "ocupados",
            "aplicar_mes":None,
            "marco":"nuevo"
        },
        {
            "table_name": "tesis.geih_bronce.no_ocupados",
            "path": "/Volumes/tesis/geih_bronce/no_ocupados/marco_nuevo/*.csv",
            "seccion":None,
            "modulo": "no_ocupados",
            "aplicar_mes":None,
            "marco":"nuevo"

        },
        
        # ========== FACTORES DE EXPANSIÓN (FEX) ==========
        {
            "table_name": "tesis.geih_bronce.dim_fex",
            "path": "/Volumes/tesis/geih_bronce/fex/*.csv",
            "seccion":None,
            "modulo": "fex",
            "aplicar_mes":None,
            "marco": None
        }
    ]
}

# COMMAND ----------

# DBTITLE 1,Cargar tablas
def cargar_tablas_bronce(
    spark, 
    tablas_config: dict,
    table_number: int = None,  # Cargar solo una tabla específica por su índice (1-based)
    seccion: str = None,       # Filtrar por sección: "area", "cabecera", "resto"
    modulo: str = None         # Filtrar por módulo: "caracteristicas_generales", "fuerza_trabajo", etc.
):
    """
    Carga archivos CSV de la GEIH desde volúmenes hacia tablas bronce en Unity Catalog.
    
    Parámetros:
        spark: Sesión de Spark
        tablas_config: Diccionario con configuración de tablas
        table_number: (Opcional) Cargar solo tabla en posición específica
        seccion: (Opcional) Filtrar por sección geográfica
        modulo: (Opcional) Filtrar por módulo temático
    
    Transformaciones aplicadas:
        - Añade columna 'archivo_origen' con nombre del archivo fuente
        - Normaliza campo AREA para sección "resto"
        - Extrae mes del nombre de archivo cuando aplicar_mes=True
        - Añade campo FT="1" para fuerza_trabajo + resto
        - Limpia valores vacíos en fex_c_2011 para marco antiguo
    """
    for index, tabla in enumerate(tablas_config["config"]):
        # Aplicar filtros si se especificaron
        if table_number != None:
            if table_number != index + 1:
                continue
        
        if seccion != None:
            if seccion != tabla["seccion"]:
                continue
        
        if modulo != None:
            if modulo != tabla["modulo"]:
                continue

        # Información de progreso
        print(f"Cargando tabla {index + 1}")
        print(f"Cargando tabla {tabla['table_name']}")
        print(f"Path: {tabla['path']}")
    
        # Leer archivos CSV con delimitador punto y coma
        df = spark.read.option("header", "true").option("delimiter", ";").csv(tabla["path"])
        
        # Agregar metadata: nombre del archivo origen
        df = df.select("*", "_metadata.file_name").withColumnRenamed("file_name", "archivo_origen")
        
        # Normalización: sección "resto" no tiene columna AREA, se inicializa como NULL
        if tabla["seccion"] == "resto":
            df = df.withColumn("AREA", lit(None).cast("string"))
        
        # Extraer mes del nombre de archivo si es requerido
        # Ejemplo de patrón: resto_fuerza_de_trabajo_01_2018.csv -> extrae "01"
        if tabla["aplicar_mes"]:
            df = df.withColumn("MES", regexp_extract(col("archivo_origen"), r"_(\d{2})_\d{4}\.csv", 1))
        
        # Campo FT="1" para identificar registros de fuerza de trabajo en sección resto
        if tabla["modulo"] == "fuerza_trabajo" and tabla["seccion"] == "resto":
            df = df.withColumn("FT", lit("1"))
        
        # Limpieza: convertir strings vacíos a NULL en fex_c_2011 (marco antiguo)
        if tabla["marco"] == "antiguo" and tabla["modulo"] == "fuerza_trabajo":
            df = df.withColumn(
                "fex_c_2011",
                when(trim(col("fex_c_2011")) == "", lit(None).cast("string"))
                .otherwise(col("fex_c_2011"))
            )

        # Escribir tabla en Unity Catalog (modo overwrite)
        df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(tabla["table_name"])

        print("Tabla cargada")
        print("-" * 50)

# Ejecutar carga de todas las tablas configuradas
cargar_tablas_bronce(
    spark, 
    tablas_config
)