# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Ingesta de Datos TerriData - Capa Bronce
# MAGIC
# MAGIC Este notebook realiza la ingesta y carga inicial de los datos de **TerriData** en la capa bronce del lakehouse, aplicando transformaciones básicas de normalización de texto.
# MAGIC
# MAGIC ## ¿Qué es TerriData?
# MAGIC
# MAGIC **TerriData** es el sistema de información geográfica y estadística del **Departamento Nacional de Planeación (DNP)** de Colombia que consolida indicadores sociales, económicos y demográficos a nivel territorial (departamentos y municipios).
# MAGIC
# MAGIC ### Características de TerriData:
# MAGIC * **Cobertura**: Todos los departamentos y municipios de Colombia
# MAGIC * **Temáticas**: Más de 1,000 indicadores organizados por dimensiones
# MAGIC * **Fuentes**: Consolida datos de múltiples entidades (DANE, MinSalud, MinEducación, etc.)
# MAGIC * **Temporalidad**: Series históricas por año y mes
# MAGIC
# MAGIC ### Dimensiones Típicas:
# MAGIC * Educación
# MAGIC * Salud
# MAGIC * Vivienda y servicios públicos
# MAGIC * Demografía y población
# MAGIC * Economía y mercado laboral
# MAGIC * Seguridad y justicia
# MAGIC * Medio ambiente
# MAGIC * Infraestructura
# MAGIC
# MAGIC ## Propósito del Notebook
# MAGIC
# MAGIC Cargar archivos consolidados de TerriData desde volúmenes de Unity Catalog y aplicar **normalización de texto** para facilitar:
# MAGIC * **Búsquedas y filtros**: Sin preocuparse por tildes o mayúsculas/minúsculas
# MAGIC * **Joins consistentes**: Con otras tablas que usen texto normalizado
# MAGIC * **Análisis de texto**: Comparaciones case-insensitive
# MAGIC
# MAGIC ## Estructura de Datos de Entrada
# MAGIC
# MAGIC **Ubicación**: `/Volumes/tesis/terridata/terridata_archivos/consolidado/`
# MAGIC
# MAGIC **Formato**: Parquet (columnar, optimizado para análisis)
# MAGIC
# MAGIC ### Campos de Entrada (supuestos):
# MAGIC
# MAGIC | Campo | Descripción |
# MAGIC |-------|-------------|
# MAGIC | `CODIGO_DEPARTAMENTO` | Código DIVIPOLA del departamento |
# MAGIC | `DEPARTAMENTO` | Nombre del departamento (con tildes) |
# MAGIC | `CODIGO_ENTIDAD` | Código del municipio o entidad |
# MAGIC | `ENTIDAD` | Nombre de la entidad/municipio (con tildes) |
# MAGIC | `DIMENSION` | Categoría temática del indicador |
# MAGIC | `SUBCATEGORIA` | Subcategoría dentro de la dimensión |
# MAGIC | `INDICADOR` | Nombre del indicador |
# MAGIC | `CODIGO_INDICADOR` | Código único del indicador |
# MAGIC | `DATO_NUMERICO` | Valor numérico del indicador |
# MAGIC | `DATO_CUALITATIVO` | Valor cualitativo del indicador |
# MAGIC | `ANO` | Año del dato |
# MAGIC | `MES` | Mes del dato |
# MAGIC | `FUENTE` | Fuente de información |
# MAGIC | `UNIDAD_MEDIDA` | Unidad de medida del indicador |
# MAGIC
# MAGIC ## Transformaciones Aplicadas
# MAGIC
# MAGIC ### 1. Normalización de Texto
# MAGIC
# MAGIC Se crean **campos normalizados** para entidad y departamento:
# MAGIC * **Eliminación de tildes**: `á → a`, `é → e`, `í → i`, `ó → o`, `ú → u`
# MAGIC * **Conversión a mayúsculas**: Consistencia en el formato
# MAGIC
# MAGIC **Ejemplos**:
# MAGIC * `"Bogotá D.C."` → `"BOGOTA D.C."`
# MAGIC * `"Medellín"` → `"MEDELLIN"`
# MAGIC * `"Cúcuta"` → `"CUCUTA"`
# MAGIC * `"San Andrés"` → `"SAN ANDRES"`
# MAGIC
# MAGIC ### 2. Campos Agregados
# MAGIC
# MAGIC * `DEPARTAMENTO_NORMALIZADO`: Versión sin tildes y en mayúsculas del departamento
# MAGIC * `ENTIDAD_NORMALIZADO`: Versión sin tildes y en mayúsculas de la entidad
# MAGIC
# MAGIC ### 3. Preservación de Datos Originales
# MAGIC
# MAGIC Los campos originales con tildes se mantienen:
# MAGIC * Para presentación legible al usuario final
# MAGIC * Para cumplir con formatos oficiales
# MAGIC * Los campos normalizados se usan internamente para joins y filtros
# MAGIC
# MAGIC ## Estructura de Salida
# MAGIC
# MAGIC **Tabla destino**: `tesis.terridata.terridata_bronce`
# MAGIC
# MAGIC ### Orden de Campos:
# MAGIC 1. **Geografía**: CODIGO_DEPARTAMENTO, DEPARTAMENTO, DEPARTAMENTO_NORMALIZADO
# MAGIC 2. **Entidad**: CODIGO_ENTIDAD, ENTIDAD, ENTIDAD_NORMALIZADO
# MAGIC 3. **Clasificación**: DIMENSION, SUBCATEGORIA, INDICADOR, CODIGO_INDICADOR
# MAGIC 4. **Valores**: DATO_NUMERICO, DATO_CUALITATIVO
# MAGIC 5. **Temporalidad**: ANO, MES
# MAGIC 6. **Metadata**: FUENTE, UNIDAD_MEDIDA
# MAGIC
# MAGIC ## Uso de Campos Normalizados
# MAGIC
# MAGIC ### Búsqueda flexible:
# MAGIC ```sql
# MAGIC -- Buscar departamento sin preocuparse por tildes o mayúsculas
# MAGIC SELECT * 
# MAGIC FROM tesis.terridata.terridata_bronce
# MAGIC WHERE DEPARTAMENTO_NORMALIZADO = 'BOGOTA D.C.'
# MAGIC ```
# MAGIC
# MAGIC ### Joins consistentes:
# MAGIC ```sql
# MAGIC -- Join con otras tablas usando versión normalizada
# MAGIC SELECT t.*, g.*
# MAGIC FROM tesis.terridata.terridata_bronce t
# MAGIC JOIN tesis.geih_oro.mercado_laboral g 
# MAGIC   ON t.DEPARTAMENTO_NORMALIZADO = UPPER(g.DEPARTAMENTO)
# MAGIC ```
# MAGIC
# MAGIC ### Agregación sin duplicados por variaciones de texto:
# MAGIC ```sql
# MAGIC SELECT 
# MAGIC   DEPARTAMENTO_NORMALIZADO,
# MAGIC   COUNT(*) as total_indicadores
# MAGIC FROM tesis.terridata.terridata_bronce
# MAGIC GROUP BY DEPARTAMENTO_NORMALIZADO
# MAGIC -- No habrá duplicados por "Bogotá" vs "BOGOTA" vs "bogotá"
# MAGIC ```
# MAGIC
# MAGIC ## Patrón de Ingesta: Parquet → Bronze
# MAGIC
# MAGIC ```
# MAGIC Archivos Parquet Consolidados
# MAGIC   ↓
# MAGIC [Este Notebook]
# MAGIC   ↓
# MAGIC Tabla Bronce (tesis.terridata.terridata_bronce)
# MAGIC   ↓
# MAGIC [Notebooks Silver/Gold]
# MAGIC   ↓
# MAGIC Tablas Analíticas
# MAGIC ```
# MAGIC
# MAGIC ## Dependencias
# MAGIC
# MAGIC **Prerrequisito**: Archivos parquet consolidados en `/Volumes/tesis/terridata/terridata_archivos/consolidado/`
# MAGIC
# MAGIC **Siguiente paso**: Procesamiento en capa plata (filtros, validaciones, enriquecimiento)
# MAGIC
# MAGIC ## Notas Técnicas
# MAGIC
# MAGIC ### Función `translate()`:
# MAGIC * Es más eficiente que múltiples `replace()` para remover tildes
# MAGIC * Reemplaza caracteres uno a uno según mapeo
# MAGIC * Soporta tanto minúsculas como mayúsculas con tildes
# MAGIC
# MAGIC ### Campos Originales Preservados:
# MAGIC * Se mantienen los nombres originales con tildes para:
# MAGIC   * Reportes y dashboards (presentación al usuario)
# MAGIC   * Cumplimiento de estándares oficiales
# MAGIC   * Trazabilidad de datos
# MAGIC
# MAGIC ### Performance:
# MAGIC * Parquet es formato columnar optimizado para lectura
# MAGIC * La normalización es una operación ligera (no requiere UDFs)
# MAGIC * Modo overwrite asegura datos actualizados en cada ejecución

# COMMAND ----------

# DBTITLE 1,Importar librerias
# Importar funciones de PySpark necesarias para normalización de texto
from pyspark.sql.functions import (
    col,        # Referenciar columnas en transformaciones
    upper,      # Convertir texto a mayúsculas
    translate   # Reemplazar caracteres (usado para eliminar tildes)
)

# COMMAND ----------

# DBTITLE 1,Leer archivo
# ============================================================================
# LECTURA DE DATOS TERRIDATA CONSOLIDADOS
# ============================================================================
# Lee archivos parquet consolidados de TerriData desde volumen de Unity Catalog
# - Formato: Parquet (columnar, optimizado para análisis)
# - Ubicación: /Volumes/tesis/terridata/terridata_archivos/consolidado/
# - Contenido: Indicadores territoriales de Colombia (departamentos y municipios)

df = spark.read.parquet("/Volumes/tesis/terridata/terridata_archivos/consolidado/")

# COMMAND ----------

# DBTITLE 1,Normalizar campos
# ============================================================================
# NORMALIZACIÓN DE CAMPOS DE TEXTO
# ============================================================================
# Objetivo: Crear versiones normalizadas de ENTIDAD y DEPARTAMENTO para:
# - Búsquedas case-insensitive
# - Joins consistentes con otras tablas
# - Eliminación de duplicados por variaciones de texto (tildes, mayúsculas)
#
# Transformación aplicada:
# 1. translate(): Reemplaza caracteres con tilde por equivalentes sin tilde
#    - á,é,í,ó,ú → a,e,i,o,u (minúsculas)
#    - Á,É,Í,Ó,Ú → A,E,I,O,U (mayúsculas)
# 2. upper(): Convierte todo a mayúsculas
#
# Ejemplos:
# - "Bogotá D.C." → "BOGOTA D.C."
# - "Medellín" → "MEDELLIN"
# - "Cúcuta" → "CUCUTA"

df_terri_normalizado = (
    df
    # Crear campo ENTIDAD_NORMALIZADO (municipio/entidad sin tildes en mayúsculas)
    .withColumn(
        "ENTIDAD_NORMALIZADO",
        upper(translate(col("ENTIDAD"), "áéíóúÁÉÍÓÚ", "aeiouAEIOU"))
    )
    # Crear campo DEPARTAMENTO_NORMALIZADO (departamento sin tildes en mayúsculas)
    .withColumn(
        "DEPARTAMENTO_NORMALIZADO",
        upper(translate(col("DEPARTAMENTO"), "áéíóúÁÉÍÓÚ", "aeiouAEIOU"))
    )
    # Seleccionar y reordenar campos: originales + normalizados
    .select(
        # --- GEOGRAFÍA ---
        "CODIGO_DEPARTAMENTO",              # Código DIVIPOLA del departamento
        "DEPARTAMENTO",                      # Nombre original con tildes
        "DEPARTAMENTO_NORMALIZADO",         # Nombre sin tildes, en mayúsculas (para joins/filtros)
        "CODIGO_ENTIDAD",                    # Código de la entidad/municipio
        "ENTIDAD",                           # Nombre original con tildes
        "ENTIDAD_NORMALIZADO",              # Nombre sin tildes, en mayúsculas (para joins/filtros)
        
        # --- CLASIFICACIÓN DEL INDICADOR ---
        "DIMENSION",                         # Categoría temática (Educación, Salud, etc.)
        "SUBCATEGORIA",                      # Subcategoría dentro de la dimensión
        "INDICADOR",                         # Nombre descriptivo del indicador
        "CODIGO_INDICADOR",                  # Código único del indicador
        
        # --- VALORES ---
        "DATO_NUMERICO",                     # Valor numérico del indicador (ej: tasa, porcentaje, cantidad)
        "DATO_CUALITATIVO",                  # Valor cualitativo/texto del indicador
        
        # --- TEMPORALIDAD ---
        "ANO",                               # Año del dato
        "MES",                               # Mes del dato
        
        # --- METADATA ---
        "FUENTE",                            # Fuente de información (DANE, MinSalud, etc.)
        "UNIDAD_MEDIDA"                      # Unidad de medida del indicador (%, pesos, personas, etc.)
    )
)

# COMMAND ----------

# DBTITLE 1,Escribir dataframe
# ============================================================================
# PERSISTENCIA EN CAPA BRONCE
# ============================================================================
# Guardar DataFrame normalizado en Unity Catalog
# - Esquema: tesis.terridata (catálogo.esquema para datos TerriData)
# - Tabla: terridata_bronce (capa bronce del lakehouse)
# - mode("overwrite"): Reemplaza la tabla existente completamente
# - overwriteSchema: Permite cambios en la estructura de la tabla
#
# Resultado: Tabla con campos originales + campos normalizados (_NORMALIZADO)
# listos para procesamiento en capas plata/oro

df_terri_normalizado.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.terridata.terridata_bronce"
)