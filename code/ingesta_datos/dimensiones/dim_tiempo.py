# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Tabla Dimensional de Tiempo - Calendario Gregoriano
# MAGIC
# MAGIC Este notebook crea una **tabla dimensional de tiempo precalculada** que contiene todas las fechas desde el año 2000 hasta el 2050, con sus componentes de fecha desglosados en múltiples formatos.
# MAGIC
# MAGIC ## Propósito
# MAGIC Generar la tabla `tesis.dim.dim_tiempo` que sirve como **dimensión temporal universal** para análisis de datos, permitiendo:
# MAGIC * Joins eficientes por fecha sin necesidad de extraer componentes en cada consulta
# MAGIC * Análisis temporales (agregaciones por año, mes, día)
# MAGIC * Rangos de fechas predefinidos (50 años de cobertura)
# MAGIC * Compatibilidad con diferentes formatos de fecha (string y numérico)
# MAGIC
# MAGIC ## ¿Qué es una Dimensión de Tiempo?
# MAGIC
# MAGIC En modelado dimensional (Data Warehouse), la **dimensión de tiempo** es una de las dimensiones más comunes. Contiene una fila por cada fecha en un rango específico, con atributos precalculados que describen esa fecha.
# MAGIC
# MAGIC ### Ventajas de una Tabla de Tiempo Precalculada:
# MAGIC
# MAGIC 1. **Performance**: 
# MAGIC    - Evita cálculos repetitivos de componentes de fecha (año, mes, día)
# MAGIC    - Joins rápidos por fecha
# MAGIC    - Índices optimizados
# MAGIC
# MAGIC 2. **Consistencia**:
# MAGIC    - Una única fuente de verdad para atributos temporales
# MAGIC    - Formato estandarizado en toda la organización
# MAGIC
# MAGIC 3. **Extensibilidad**:
# MAGIC    - Fácil agregar columnas calculadas (trimestre, semana, día de la semana, festivos)
# MAGIC    - Clasificaciones temporales personalizadas
# MAGIC
# MAGIC ## Cobertura Temporal
# MAGIC
# MAGIC **Rango**: 2000-01-01 hasta 2050-12-31
# MAGIC * **Total de fechas**: ~18,628 registros (51 años × 365.25 días/año)
# MAGIC * **Inicio**: 1 de enero de 2000
# MAGIC * **Fin**: 31 de diciembre de 2050
# MAGIC
# MAGIC ### ¿Por qué este rango?
# MAGIC * **2000-2024**: Datos históricos de GEIH y otras fuentes
# MAGIC * **2025-2050**: Capacidad para proyecciones y análisis futuros
# MAGIC
# MAGIC ## Estructura de la Tabla
# MAGIC
# MAGIC | Campo | Tipo | Formato | Descripción | Ejemplo |
# MAGIC |-------|------|---------|-------------|----------|
# MAGIC | `FECHA` | date | yyyy-MM-dd | Fecha completa | 2024-06-15 |
# MAGIC | `ANO` | string | yyyy | Año como string (4 dígitos) | "2024" |
# MAGIC | `MES` | string | MM | Mes como string con cero inicial (2 dígitos) | "06" |
# MAGIC | `DIA` | string | dd | Día como string con cero inicial (2 dígitos) | "15" |
# MAGIC | `ANO_N` | int | - | Año como entero | 2024 |
# MAGIC | `MES_N` | int | - | Mes como entero (1-12) | 6 |
# MAGIC | `DIA_N` | int | - | Día del mes como entero (1-31) | 15 |
# MAGIC
# MAGIC ### Formatos Duales: String vs Numérico
# MAGIC
# MAGIC La tabla proporciona **dos versiones** de cada componente:
# MAGIC
# MAGIC **Versión String** (ANO, MES, DIA):
# MAGIC * ✅ Mantiene ceros iniciales: "01", "02", "03"
# MAGIC * ✅ Útil para concatenación y formato de presentación
# MAGIC * ✅ Compatible con códigos de periodo: "202406" (YYYYMM)
# MAGIC
# MAGIC **Versión Numérica** (ANO_N, MES_N, DIA_N):
# MAGIC * ✅ Optimizada para cálculos matemáticos
# MAGIC * ✅ Facilita comparaciones y rangos
# MAGIC * ✅ Menor uso de almacenamiento
# MAGIC
# MAGIC ## Generación de Datos
# MAGIC
# MAGIC ### Método: Iteración con timedelta
# MAGIC
# MAGIC Se usa un bucle Python para generar todas las fechas:
# MAGIC
# MAGIC ```python
# MAGIC start_date = date(2000, 1, 1)
# MAGIC end_date = date(2050, 12, 31)
# MAGIC
# MAGIC current_date = start_date
# MAGIC while current_date <= end_date:
# MAGIC     date_list.append((current_date,))
# MAGIC     current_date += timedelta(days=1)  # Incrementar 1 día
# MAGIC ```
# MAGIC
# MAGIC ### Funciones de PySpark para Extracción:
# MAGIC
# MAGIC * `date_format()`: Convertir fecha a string con formato específico
# MAGIC * `year()`, `month()`, `dayofmonth()`: Extraer componentes como enteros
# MAGIC
# MAGIC ## Uso en el Pipeline de Datos
# MAGIC
# MAGIC Esta tabla dimensional se puede unir con cualquier tabla de hechos que tenga una columna de fecha:
# MAGIC
# MAGIC ### Ejemplo 1: Join por fecha completa
# MAGIC ```sql
# MAGIC SELECT 
# MAGIC     h.*, 
# MAGIC     t.ANO, 
# MAGIC     t.MES, 
# MAGIC     t.DIA
# MAGIC FROM hechos h
# MAGIC JOIN tesis.dim.dim_tiempo t ON h.fecha = t.FECHA
# MAGIC ```
# MAGIC
# MAGIC ### Ejemplo 2: Filtrado por rango temporal
# MAGIC ```sql
# MAGIC SELECT *
# MAGIC FROM tesis.dim.dim_tiempo
# MAGIC WHERE ANO_N BETWEEN 2020 AND 2024
# MAGIC   AND MES_N IN (1, 2, 3)  -- Primer trimestre
# MAGIC ```
# MAGIC
# MAGIC ### Ejemplo 3: Agregación por mes y año
# MAGIC ```sql
# MAGIC SELECT 
# MAGIC     t.ANO,
# MAGIC     t.MES,
# MAGIC     COUNT(v.id) as ventas_totales
# MAGIC FROM ventas v
# MAGIC JOIN tesis.dim.dim_tiempo t ON v.fecha_venta = t.FECHA
# MAGIC GROUP BY t.ANO, t.MES
# MAGIC ORDER BY t.ANO, t.MES
# MAGIC ```
# MAGIC
# MAGIC ## Extensibilidad Futura
# MAGIC
# MAGIC Esta tabla puede extenderse fácilmente agregando columnas calculadas:
# MAGIC
# MAGIC * **Trimestre**: `WHEN MES_N BETWEEN 1 AND 3 THEN 'Q1'`
# MAGIC * **Semestre**: `WHEN MES_N <= 6 THEN 'S1'`
# MAGIC * **Semana del año**: `weekofyear(FECHA)`
# MAGIC * **Día de la semana**: `dayofweek(FECHA)` → "Lunes", "Martes", etc.
# MAGIC * **Día laboral vs fin de semana**: `CASE WHEN dayofweek(FECHA) IN (1,7) THEN 'Fin de Semana'`
# MAGIC * **Festivos colombianos**: Join con tabla de festivos
# MAGIC * **Año fiscal**: Para organizaciones con año fiscal diferente al calendario
# MAGIC
# MAGIC ## Mantenimiento
# MAGIC
# MAGIC **¿Cuándo actualizar?**
# MAGIC * Cuando se acerque el año 2050: Extender el rango final
# MAGIC * Si se necesitan fechas anteriores a 2000: Ajustar fecha inicial
# MAGIC * Al agregar nuevas columnas calculadas
# MAGIC
# MAGIC **¿Cómo actualizar?**
# MAGIC * Modificar `start_date` o `end_date` en el código
# MAGIC * Agregar nuevas columnas en el `.select()`
# MAGIC * Reejecutar el notebook (modo overwrite)

# COMMAND ----------

# DBTITLE 1,Crear dimensión de tiempo
# ============================================================================
# IMPORTACIÓN DE LIBRERÍAS
# ============================================================================

# --- Funciones de PySpark ---
from pyspark.sql.functions import (
    col,           # Referenciar columnas
    date_format,   # Formatear fecha como string con patrón específico
    year,          # Extraer año como entero
    month,         # Extraer mes como entero (1-12)
    dayofmonth     # Extraer día del mes como entero (1-31)
)

# --- Módulo datetime de Python ---
from datetime import (
    date,          # Clase para manejar fechas (sin hora)
    timedelta      # Clase para representar duraciones (ej: 1 día)
)


# ============================================================================
# DEFINICIÓN DEL RANGO TEMPORAL
# ============================================================================
# Cobertura: 51 años (2000-2050)
# Total de fechas: ~18,628 registros

start_date = date(2000, 1, 1)    # Fecha inicial: 1 de enero de 2000
end_date = date(2050, 12, 31)    # Fecha final: 31 de diciembre de 2050


# ============================================================================
# GENERACIÓN DE SECUENCIA DE FECHAS
# ============================================================================
# Método: Iteración con incremento de 1 día usando timedelta
# Cada fecha se almacena como tupla de un elemento para crear DataFrame

date_list = []                    # Lista para acumular fechas
current_date = start_date         # Inicializar con fecha de inicio

# Bucle: generar todas las fechas del rango
while current_date <= end_date:
    date_list.append((current_date,))           # Agregar fecha como tupla
    current_date += timedelta(days=1)           # Incrementar 1 día


# ============================================================================
# CREACIÓN DE DATAFRAME CON COMPONENTES DE FECHA
# ============================================================================
# Proceso:
# 1. Crear DataFrame base desde la lista de fechas
# 2. Extraer componentes en formato string (con ceros iniciales)
# 3. Extraer componentes en formato numérico (enteros)

df_tiempo = (
    spark.createDataFrame(date_list, ["FECHA"])    # Crear DataFrame con columna FECHA
    .select(
        # --- FECHA BASE ---
        col("FECHA"),                                          # Fecha completa (tipo date)
        
        # --- COMPONENTES COMO STRING (con ceros iniciales) ---
        # Útil para presentación y concatenación de periodos
        date_format(col("FECHA"), "yyyy").alias("ANO"),      # Año: "2024"
        date_format(col("FECHA"), "MM").alias("MES"),        # Mes: "01", "02", ..., "12"
        date_format(col("FECHA"), "dd").alias("DIA"),        # Día: "01", "02", ..., "31"
        
        # --- COMPONENTES COMO NÚMERO (enteros) ---
        # Optimizado para cálculos, comparaciones y agregaciones
        year(col("FECHA")).alias("ANO_N"),                    # Año: 2024
        month(col("FECHA")).alias("MES_N"),                   # Mes: 1, 2, ..., 12
        dayofmonth(col("FECHA")).alias("DIA_N")               # Día: 1, 2, ..., 31
    )
)

# COMMAND ----------

# DBTITLE 1,Guardar tabla dimensional
# ============================================================================
# PERSISTENCIA DE TABLA DIMENSIONAL DE TIEMPO
# ============================================================================
# Guardar tabla dimensional en Unity Catalog
# - Esquema: tesis.dim (catálogo.esquema para tablas dimensionales)
# - Tabla: dim_tiempo
# - mode("overwrite"): Reemplaza la tabla existente completamente
# - overwriteSchema: Permite cambios en la estructura de la tabla
#
# Resultado: Tabla con ~18,628 registros (una fila por día desde 2000 hasta 2050)
# Tamaño estimado: Pequeño (~1-2 MB), ideal para broadcast joins

df_tiempo.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.dim.dim_tiempo"
)