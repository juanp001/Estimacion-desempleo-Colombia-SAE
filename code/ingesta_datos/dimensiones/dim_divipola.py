# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Tabla Dimensional DIVIPOLA - División Político-Administrativa de Colombia
# MAGIC
# MAGIC Este notebook crea la **tabla dimensional de geografía** basada en la codificación DIVIPOLA (División Político-Administrativa) del DANE, que contiene la estructura administrativa de Colombia con departamentos, municipios y sus coordenadas geográficas.
# MAGIC
# MAGIC ## Propósito
# MAGIC Generar la tabla `tesis.dim.dim_divipola` que sirve como **dimensión geográfica** para los análisis de la GEIH, permitiendo:
# MAGIC * Mapear códigos de departamento/municipio a nombres legibles
# MAGIC * Obtener coordenadas geográficas (latitud/longitud) para visualizaciones
# MAGIC * Clasificar entidades por tipo (Municipio, Isla, Área no municipalizada)
# MAGIC
# MAGIC ## ¿Qué es DIVIPOLA?
# MAGIC
# MAGIC **DIVIPOLA** es la codificación estándar del DANE (Departamento Administrativo Nacional de Estadística) para identificar unidades político-administrativas en Colombia:
# MAGIC
# MAGIC * **Código de Departamento**: 2 dígitos (ej: 05 = Antioquia, 11 = Bogotá D.C.)
# MAGIC * **Código de Municipio**: 5 dígitos (código departamento + 3 dígitos del municipio)
# MAGIC   - Ejemplo: 05001 = Medellín (05 = Antioquia, 001 = capital departamental)
# MAGIC   - Ejemplo: 11001 = Bogotá D.C.
# MAGIC
# MAGIC ## Fuente de Datos
# MAGIC
# MAGIC **Ubicación**: `/Volumes/tesis/dim/divipola/*.csv`
# MAGIC
# MAGIC **Formato**: CSV con delimitador coma (`,`)
# MAGIC
# MAGIC **Estructura del archivo fuente**:
# MAGIC ```
# MAGIC Código Departamento,Nombre Departamento,Código Municipio,Nombre Municipio,Tipo,longitud,Latitud
# MAGIC 05,ANTIOQUIA,05001,MEDELLÍN,Municipio,-75.5635932,6.2476376
# MAGIC 11,BOGOTÁ D.C.,11001,BOGOTÁ D.C.,Municipio,-74.0817500,4.6097100
# MAGIC ```
# MAGIC
# MAGIC ## Campos de Salida
# MAGIC
# MAGIC | Campo | Tipo | Descripción |
# MAGIC |-------|------|-------------|
# MAGIC | `CODIGO_DEPARTAMENTO` | string | Código DIVIPOLA del departamento (2 dígitos) |
# MAGIC | `DEPARTAMENTO` | string | Nombre del departamento |
# MAGIC | `CODIGO_MUNICIPIO` | string | Código DIVIPOLA del municipio (5 dígitos) |
# MAGIC | `MUNICIPIO` | string | Nombre del municipio |
# MAGIC | `DIMENSION` | string | Tipo de entidad: Municipio, Isla, Área no municipalizada |
# MAGIC | `LONGITUD` | double | Coordenada de longitud (grados decimales) |
# MAGIC | `LATITUD` | double | Coordenada de latitud (grados decimales) |
# MAGIC
# MAGIC ## Transformaciones Aplicadas
# MAGIC
# MAGIC 1. **Renombrado de columnas**: Mapeo de nombres originales a nombres estandarizados en mayúsculas sin espacios
# MAGIC 2. **Normalización de coordenadas**:
# MAGIC    - Reemplazo de comas (`,`) por puntos (`.`) en valores numéricos
# MAGIC    - Conversión a tipo `double` para latitud y longitud
# MAGIC 3. **Preservación de tipos**: Códigos se mantienen como `string` (importante: 05 ≠ 5)
# MAGIC
# MAGIC ## Uso en el Pipeline GEIH
# MAGIC
# MAGIC Esta tabla dimensional se une con las tablas de la capa ORO para:
# MAGIC * **Enriquecer datos de mercado laboral** con nombres geográficos legibles
# MAGIC * **Habilitar análisis espaciales** usando coordenadas
# MAGIC * **Permitir agregaciones** por departamento o municipio
# MAGIC
# MAGIC ### Ejemplo de Join:
# MAGIC ```python
# MAGIC # En geih_oro, se une 2 veces:
# MAGIC # 1. Para obtener nombre del departamento
# MAGIC .join(dim_divipola.alias("div_dep"), 
# MAGIC       col("CODIGO_DPTO") == col("div_dep.CODIGO_DEPARTAMENTO"))
# MAGIC
# MAGIC # 2. Para obtener nombre del municipio  
# MAGIC .join(dim_divipola.alias("div_mun"), 
# MAGIC       col("CODIGO_AREA") == col("div_mun.CODIGO_AREA_GEIH"))
# MAGIC ```
# MAGIC
# MAGIC ## Nota sobre Códigos
# MAGIC
# MAGIC Los códigos DIVIPOLA deben manejarse como **strings**, no como enteros:
# MAGIC * ✅ `"05"` (Antioquia)
# MAGIC * ❌ `5` (pierde el cero inicial)
# MAGIC
# MAGIC Esto es crítico para joins correctos con tablas GEIH que usan la misma codificación.

# COMMAND ----------

# DBTITLE 1,Importar librerias
# Importar funciones de PySpark necesarias para la transformación
from pyspark.sql.functions import (
    col,             # Referenciar columnas para renombrado y transformaciones
    regexp_replace   # Reemplazar patrones de texto (comas por puntos en coordenadas)
)

# COMMAND ----------

# DBTITLE 1,Map de columnas
# ============================================================================
# MAPEO DE COLUMNAS: NOMBRES ORIGINALES → NOMBRES ESTANDARIZADOS
# ============================================================================
# Diccionario que mapea los nombres de columnas del CSV fuente (con espacios
# y caracteres especiales) a nombres estandarizados para la base de datos:
# - Todo en mayúsculas
# - Sin espacios (se reemplazan por guiones bajos)
# - Sin tildes en nombres de campo (aunque los valores sí las conservan)
# - Nombres descriptivos y concisos

col_map = {
    "Código Departamento": "CODIGO_DEPARTAMENTO",                        # Código DIVIPOLA del departamento (2 dígitos)
    "Nombre Departamento": "DEPARTAMENTO",                               # Nombre completo del departamento
    "Código Municipio": "CODIGO_MUNICIPIO",                              # Código DIVIPOLA del municipio (5 dígitos)
    "Nombre Municipio": "MUNICIPIO",                                     # Nombre completo del municipio
    "Tipo: Municipio / Isla / Área no municipalizada": "DIMENSION",     # Clasificación administrativa
    "longitud": "LONGITUD",                                              # Coordenada de longitud (grados decimales)
    "Latitud": "LATITUD"                                                 # Coordenada de latitud (grados decimales)
}

# COMMAND ----------

# DBTITLE 1,Leer archivo
# ============================================================================
# LECTURA Y TRANSFORMACIÓN DE DATOS DIVIPOLA
# ============================================================================

# --- PASO 1: LEER ARCHIVO CSV ---
# Lee archivo CSV de DIVIPOLA desde volumen de Unity Catalog
# - header="true": Primera fila contiene nombres de columnas
# - delimiter=",": Archivo separado por comas
# - /*.csv: Lee todos los archivos CSV en el directorio
df = spark.read.option("header", "true").option("delimiter", ",").csv("/Volumes/tesis/dim/divipola/*.csv")

# --- PASO 2: RENOMBRAR COLUMNAS ---
# Crear lista de expresiones para renombrar todas las columnas
# según el diccionario col_map definido anteriormente
map_select = [col(column).alias(col_map.get(column)) for column in df.columns]

# --- PASO 3: APLICAR RENOMBRADO Y NORMALIZAR COORDENADAS ---
# 1. Seleccionar todas las columnas con sus nuevos nombres
# 2. Normalizar LATITUD: reemplazar comas por puntos y convertir a double
#    Ejemplo: "6,2476376" → "6.2476376" → 6.2476376 (double)
# 3. Normalizar LONGITUD: mismo proceso que latitud
#    Ejemplo: "-75,5635932" → "-75.5635932" → -75.5635932 (double)
df_select = df.select(*map_select).withColumn(
    "LATITUD", regexp_replace(col("LATITUD"), ",", ".").cast("double")
).withColumn(
    "LONGITUD", regexp_replace(col("LONGITUD"), ",", ".").cast("double")
)

# COMMAND ----------

# DBTITLE 1,Guardar tabla dimensional
# ============================================================================
# PERSISTENCIA DE TABLA DIMENSIONAL
# ============================================================================
# Guardar tabla dimensional DIVIPOLA en Unity Catalog
# - Esquema: tesis.dim (catálogo.esquema para tablas dimensionales)
# - Tabla: dim_divipola
# - mode("overwrite"): Reemplaza la tabla existente completamente
# - overwriteSchema: Permite cambios en la estructura de la tabla
#
# Resultado: Tabla dimensional lista para joins con tablas de hechos (GEIH)

df_select.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.dim.dim_divipola"
)