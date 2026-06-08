# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Estimación Directa de Tasa de Desempleo Municipal con Bootstrap
# MAGIC
# MAGIC Este notebook implementa **estimación directa de áreas pequeñas** (municipios) usando el **estimador de Hájek** con inferencia basada en **bootstrap simple**.
# MAGIC
# MAGIC ## Propósito
# MAGIC
# MAGIC Calcular estimaciones de **tasa de desempleo por municipio** a partir de microdatos de la GEIH, incluyendo:
# MAGIC * **Estimación puntual**: Tasa de desempleo (porcentaje)
# MAGIC * **Medidas de precisión**: Error estándar, intervalos de confianza 95%, coeficiente de variación
# MAGIC * **Inferencia estadística**: Basada en bootstrap simple (600 réplicas)
# MAGIC
# MAGIC ## ¿Qué es Estimación Directa?
# MAGIC
# MAGIC La **estimación directa** usa **solo los datos de la muestra del dominio de interés** (en este caso, el municipio) para calcular la estimación, sin "pedir prestada" información de otros dominios.
# MAGIC
# MAGIC ### Ventajas:
# MAGIC ✅ **Simple y transparente**: Usa solo datos locales
# MAGIC ✅ **Sin supuestos de modelo**: No asume relaciones con covariables
# MAGIC ✅ **Fácil de interpretar**: Es el estimador "natural"
# MAGIC
# MAGIC ### Desventajas:
# MAGIC ❌ **Alta variabilidad en áreas pequeñas**: Muestras chicas → errores grandes
# MAGIC ❌ **Intervalos de confianza amplios**: Poca precisión para municipios pequeños
# MAGIC ❌ **Coeficientes de variación altos**: CV > 30% son comunes en municipios pequeños
# MAGIC ❌ **Imposible estimar dominios con muestra cero**: Sin observaciones → sin estimación
# MAGIC
# MAGIC ### ¿Cuándo usar estimación directa?
# MAGIC
# MAGIC **Usar cuando**:
# MAGIC * El dominio tiene **muestra suficiente** (n ≥ 30 típicamente)
# MAGIC * El **CV es aceptable** (< 15% ideal, < 30% aceptable)
# MAGIC * Se requiere **transparencia metodológica**
# MAGIC * Es el **baseline** para comparar con métodos SAE
# MAGIC
# MAGIC **NO usar cuando**:
# MAGIC * El dominio tiene muestra muy pequeña (n < 10)
# MAGIC * El CV es muy alto (> 30%)
# MAGIC * Se requieren estimaciones para **todos** los municipios (incluso sin muestra)
# MAGIC
# MAGIC ## Estimador de Hájek
# MAGIC
# MAGIC ### Definición
# MAGIC
# MAGIC El **estimador de Hájek** es un estimador de **razón** que ajusta por los pesos muestrales:
# MAGIC
# MAGIC ```
# MAGIC θ̂ = Σ(w_i × y_i) / Σ(w_i)
# MAGIC ```
# MAGIC
# MAGIC Donde:
# MAGIC * `w_i`: Peso de expansión (FEX) de la observación i
# MAGIC * `y_i`: Variable binaria (1 = desocupado, 0 = ocupado)
# MAGIC * Σ: Suma sobre todas las observaciones del dominio
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC Es un **promedio ponderado** donde:
# MAGIC * Cada individuo contribuye según su peso de expansión
# MAGIC * El denominador normaliza para obtener una proporción
# MAGIC * Resultado: Tasa de desempleo estimada (0 a 1, o 0% a 100%)
# MAGIC
# MAGIC ### Propiedades
# MAGIC
# MAGIC **Para muestras grandes**:
# MAGIC * ✅ **Aproximadamente insesgado** para la proporción poblacional
# MAGIC * ✅ **Consistente**: converge al valor poblacional cuando n → ∞
# MAGIC * ✅ **Asintóticamente normal**: permite construir intervalos de confianza
# MAGIC
# MAGIC **Para muestras pequeñas** (áreas pequeñas):
# MAGIC * ⚠️ Puede tener **sesgo** (generalmente pequeño)
# MAGIC * ⚠️ **Alta variabilidad**: error estándar grande
# MAGIC * ⚠️ Normalidad asintótica puede **no aplicar** bien
# MAGIC
# MAGIC ## Bootstrap Simple (Naive Bootstrap)
# MAGIC
# MAGIC ### ¿Qué es bootstrap?
# MAGIC
# MAGIC **Bootstrap** es un método de **remuestreo** para estimar la distribución muestral de un estimador cuando la fórmula analítica es compleja o desconocida.
# MAGIC
# MAGIC ### Procedimiento:
# MAGIC
# MAGIC 1. **Muestra original**: Tenemos n observaciones
# MAGIC 2. **Remuestreo con reemplazo**: Crear B réplicas bootstrap
# MAGIC    * Para cada réplica b = 1, ..., B:
# MAGIC      - Extraer n observaciones **con reemplazo** de la muestra original
# MAGIC      - Calcular el estimador θ̂_b en la réplica b
# MAGIC 3. **Distribución bootstrap**: Las B estimaciones {θ̂_1, ..., θ̂_B} aproximan la distribución muestral de θ̂
# MAGIC 4. **Estadísticas**:
# MAGIC    * **Error estándar**: SE = desviación estándar de {θ̂_1, ..., θ̂_B}
# MAGIC    * **Intervalo de confianza 95%**: [percentil 2.5%, percentil 97.5%]
# MAGIC
# MAGIC ### Ejemplo visual:
# MAGIC
# MAGIC ```
# MAGIC Muestra original (n=100):  [obs₁, obs₂, ..., obs₁₀₀]
# MAGIC                                     ↓
# MAGIC               Remuestreo con reemplazo B=600 veces
# MAGIC                                     ↓
# MAGIC Réplica 1:  [obs₃, obs₁, obs₃, obs₅₀, ...]  → θ̂₁ = 0.089
# MAGIC Réplica 2:  [obs₁, obs₁, obs₂, obs₇₅, ...]  → θ̂₂ = 0.091
# MAGIC Réplica 3:  [obs₂, obs₄, obs₁, obs₁, ...]   → θ̂₃ = 0.087
# MAGIC    ...                                          ...
# MAGIC Réplica 600: [obs₉₉, obs₃, obs₁, obs₂, ...] → θ̂₆₀₀ = 0.092
# MAGIC                                     ↓
# MAGIC Estadísticas: SE = 0.012 (1.2%)
# MAGIC               IC 95% = [0.066, 0.114] → [6.6%, 11.4%]
# MAGIC ```
# MAGIC
# MAGIC ### Número de réplicas bootstrap
# MAGIC
# MAGIC En este notebook usamos **B = 5000 réplicas**:
# MAGIC * Literatura recomienda B ≥ 500 para error estándar
# MAGIC * B ≥ 1000 para intervalos de confianza
# MAGIC
# MAGIC ## Arquitectura del Código
# MAGIC
# MAGIC ### Clase Base: `EstimadorSAE`
# MAGIC
# MAGIC **Patrón de diseño**: Template Method + Strategy
# MAGIC
# MAGIC Define la **interfaz común** para todos los estimadores SAE:
# MAGIC * `estimar()`: Método abstracto que cada estimador implementa
# MAGIC * `validar_columnas()`: Validación de datos de entrada
# MAGIC * `exportar()`: Guardar resultados a Unity Catalog con lineage
# MAGIC * `resultado`: Propiedad para acceder al último resultado
# MAGIC
# MAGIC **Ventajas del diseño**:
# MAGIC ✅ **Extensibilidad**: Fácil agregar nuevos estimadores (Fay-Herriot, EBLUP, etc.)
# MAGIC ✅ **Reutilización**: Lógica común (validación, export) en un solo lugar
# MAGIC ✅ **Consistencia**: Todos los estimadores tienen la misma interfaz
# MAGIC ✅ **Testing**: Se puede mockear y testear independientemente
# MAGIC
# MAGIC ### Clase Concreta: `EstimacionDirecta`
# MAGIC
# MAGIC Implementa estimación directa específicamente:
# MAGIC 1. **Validación**: Verifica columnas necesarias (FEX, DESOCUPADO, grupos)
# MAGIC 2. **Conversión**: Spark → Pandas (bootstrap es más eficiente en pandas para este caso)
# MAGIC 3. **Bootstrap**: Genera B réplicas remuestreando individuos
# MAGIC 4. **Estadísticas**: Calcula SE, IC, CV desde la distribución bootstrap
# MAGIC 5. **Formateo**: Convierte a porcentajes y organiza columnas
# MAGIC
# MAGIC ## Flujo de Datos
# MAGIC
# MAGIC ```
# MAGIC ┌─────────────────────────────────────────────────────────┐
# MAGIC │  tesis.geih_oro.mercado_laboral                         │
# MAGIC │  (Todos los municipios × meses × años)                  │
# MAGIC └────────────────────┬────────────────────────────────────┘
# MAGIC                      │
# MAGIC                      │ filter(MUNICIPIO not null,
# MAGIC                      │        PEA == 1,
# MAGIC                      │        PER == 2018,
# MAGIC                      │        MES == 12)
# MAGIC                      ↓
# MAGIC ┌─────────────────────────────────────────────────────────┐
# MAGIC │  DataFrame filtrado                                      │
# MAGIC │  (~20K observaciones de PEA en 23 municipios)           │
# MAGIC └────────────────────┬────────────────────────────────────┘
# MAGIC                      │
# MAGIC                      │ EstimacionDirecta.estimar()
# MAGIC                      │   - Convierte a Pandas
# MAGIC                      │   - Bootstrap (600 réplicas)
# MAGIC                      │   - Calcula estadísticas
# MAGIC                      ↓
# MAGIC ┌─────────────────────────────────────────────────────────┐
# MAGIC │  pandas.DataFrame resultado                              │
# MAGIC │  (23 filas × 12 columnas)                               │
# MAGIC │  - Identificación: PER, MES, DPTO, MUN (6 cols)        │
# MAGIC │  - Estimaciones: Tasa, SE, IC, CV (6 cols)             │
# MAGIC └────────────────────┬────────────────────────────────────┘
# MAGIC                      │
# MAGIC                      │ exportar()
# MAGIC                      ↓
# MAGIC ┌─────────────────────────────────────────────────────────┐
# MAGIC │  tesis.modelo.tasa_desempleo_municipal                  │
# MAGIC │  (Tabla persistida en Unity Catalog)                    │
# MAGIC │  Lineage: mercado_laboral → tasa_desempleo_municipal   │
# MAGIC └─────────────────────────────────────────────────────────┘
# MAGIC ```
# MAGIC
# MAGIC ## Estructura de la Tabla de Salida
# MAGIC
# MAGIC ### `tesis.modelo.tasa_desempleo_municipal`
# MAGIC
# MAGIC **12 columnas** organizadas en 2 grupos:
# MAGIC
# MAGIC #### 1. Identificación (6 columnas)
# MAGIC
# MAGIC | Campo | Tipo | Descripción |
# MAGIC |-------|------|-------------|
# MAGIC | `PER` | int | Año de la estimación |
# MAGIC | `MES` | int | Mes de la estimación |
# MAGIC | `CODIGO_DEPARTAMENTO` | string | Código DIVIPOLA del departamento |
# MAGIC | `DEPARTAMENTO` | string | Nombre del departamento |
# MAGIC | `CODIGO_MUNICIPIO` | string | Código DIVIPOLA del municipio |
# MAGIC | `MUNICIPIO` | string | Nombre del municipio |
# MAGIC
# MAGIC #### 2. Estimaciones (6 columnas)
# MAGIC
# MAGIC | Campo | Tipo | Descripción | Rango |
# MAGIC |-------|------|-------------|-------|
# MAGIC | `TASA_DESEMPLEO_PCT` | double | Tasa de desempleo estimada | 0-100% |
# MAGIC | `SE_BOOTSTRAP_PCT` | double | Error estándar bootstrap | >0 |
# MAGIC | `IC_INF_PCT` | double | Límite inferior IC 95% | ≥0 |
# MAGIC | `IC_SUP_PCT` | double | Límite superior IC 95% | ≤100 |
# MAGIC | `AMPLITUD_IC` | double | Amplitud del intervalo (SUP - INF) | >0 |
# MAGIC | `CV_PORCENTAJE` | double | Coeficiente de variación (SE/Tasa × 100) | >0 |
# MAGIC
# MAGIC ### Interpretación del CV (Coeficiente de Variación)
# MAGIC
# MAGIC El CV mide la **precisión relativa** de la estimación:
# MAGIC
# MAGIC ```
# MAGIC CV = (SE / Estimación) × 100
# MAGIC ```
# MAGIC
# MAGIC **Criterios de calidad** (DANE, CEPAL):
# MAGIC * **CV < 15%**: Estimación **CONFIABLE** ✅ (Alta precisión)
# MAGIC * **15% ≤ CV < 30%**: Estimación **ACEPTABLE** ⚠️ (Usar con precaución)
# MAGIC * **CV ≥ 30%**: Estimación **NO CONFIABLE** ❌ (No publicar)
# MAGIC
# MAGIC **Ejemplo**:
# MAGIC * Municipio A: Tasa = 10%, SE = 1% → CV = 10% → **CONFIABLE**
# MAGIC * Municipio B: Tasa = 8%, SE = 2% → CV = 25% → **ACEPTABLE**
# MAGIC * Municipio C: Tasa = 5%, SE = 2.5% → CV = 50% → **NO CONFIABLE**
# MAGIC
# MAGIC ## Casos de Uso
# MAGIC
# MAGIC ### 1. Ranking de municipios por desempleo (solo confiables)
# MAGIC
# MAGIC ```sql
# MAGIC SELECT 
# MAGIC   MUNICIPIO,
# MAGIC   TASA_DESEMPLEO_PCT,
# MAGIC   CV_PORCENTAJE,
# MAGIC   IC_INF_PCT,
# MAGIC   IC_SUP_PCT
# MAGIC FROM tesis.modelo.tasa_desempleo_municipal
# MAGIC WHERE CV_PORCENTAJE < 15  -- Solo estimaciones confiables
# MAGIC ORDER BY TASA_DESEMPLEO_PCT DESC
# MAGIC ```
# MAGIC
# MAGIC ### 2. Identificar municipios con alta variabilidad
# MAGIC
# MAGIC ```sql
# MAGIC SELECT 
# MAGIC   MUNICIPIO,
# MAGIC   TASA_DESEMPLEO_PCT,
# MAGIC   CV_PORCENTAJE,
# MAGIC   AMPLITUD_IC,
# MAGIC   CASE 
# MAGIC     WHEN CV_PORCENTAJE < 15 THEN 'CONFIABLE'
# MAGIC     WHEN CV_PORCENTAJE < 30 THEN 'ACEPTABLE'
# MAGIC     ELSE 'NO CONFIABLE'
# MAGIC   END as CALIDAD
# MAGIC FROM tesis.modelo.tasa_desempleo_municipal
# MAGIC ORDER BY CV_PORCENTAJE DESC
# MAGIC ```
# MAGIC
# MAGIC ### 3. Preparar baseline para modelos SAE
# MAGIC
# MAGIC ```python
# MAGIC # Cargar estimaciones directas
# MAGIC df_directa = spark.table("tesis.modelo.tasa_desempleo_municipal")
# MAGIC
# MAGIC # Filtrar estimaciones con muestra suficiente (para entrenar modelo)
# MAGIC df_train = df_directa.filter(F.col("CV_PORCENTAJE") < 30)
# MAGIC
# MAGIC # Las estimaciones no confiables son candidatas para SAE
# MAGIC df_mejorar = df_directa.filter(F.col("CV_PORCENTAJE") >= 30)
# MAGIC
# MAGIC print(f"Estimaciones confiables: {df_train.count()}")
# MAGIC print(f"Estimaciones a mejorar con SAE: {df_mejorar.count()}")
# MAGIC ```
# MAGIC
# MAGIC ## Parámetros Configurables
# MAGIC
# MAGIC ### `num_replicas` (default: 5000)
# MAGIC
# MAGIC **¿Cuántas réplicas bootstrap?**
# MAGIC * Más réplicas → más precisión en SE e IC, pero más tiempo
# MAGIC * Menos réplicas → más rápido, pero menos precisión
# MAGIC
# MAGIC **Recomendaciones**:
# MAGIC * **B = 200-500**: Exploratorio (SE aproximado)
# MAGIC * **B = 500-1000**: Producción (SE estable)
# MAGIC * **B = 1000-2000**: Investigación (IC muy precisos)
# MAGIC
# MAGIC ### `seed` (default: 42)
# MAGIC
# MAGIC **Reproducibilidad**:
# MAGIC * Fija la semilla aleatoria para que los resultados sean **exactamente reproducibles**
# MAGIC * Cambiar la semilla → resultados ligeramente diferentes (pero estadísticamente equivalentes)
# MAGIC
# MAGIC ### `grupo_cols` (requerido)
# MAGIC
# MAGIC **Define los dominios de estimación**:
# MAGIC * Lista de columnas para agrupar
# MAGIC * Cada combinación única = un dominio = una estimación
# MAGIC
# MAGIC **Ejemplos**:
# MAGIC * Municipal mensual: `["PER", "MES", "CODIGO_MUNICIPIO", "MUNICIPIO"]`
# MAGIC * Municipal anual: `["PER", "CODIGO_MUNICIPIO", "MUNICIPIO"]`
# MAGIC * Departamental mensual: `["PER", "MES", "CODIGO_DEPARTAMENTO", "DEPARTAMENTO"]`
# MAGIC
# MAGIC ### `agregacion_anual` (default: False)
# MAGIC
# MAGIC **Nivel temporal**:
# MAGIC * `False`: Estimaciones **mensuales** (una por mes)
# MAGIC * `True`: Estimaciones **anuales** (agrega todos los meses del año)
# MAGIC
# MAGIC **Ventaja de anual**: Más muestra → menor variabilidad → CV más bajo
# MAGIC
# MAGIC ## Próximos Pasos
# MAGIC
# MAGIC Esta estimación directa sirve como:
# MAGIC
# MAGIC 1. **Baseline**: Comparar con métodos SAE
# MAGIC 2. **Diagnóstico**: Identificar dominios con alta variabilidad
# MAGIC 3. **Input**: Variable dependiente para modelos Fay-Herriot
# MAGIC 4. **Validación**: Evaluar si SAE realmente mejora
# MAGIC
# MAGIC **Siguientes notebooks**:
# MAGIC * `adicion_covariables`: Integrar covariables de TerriData
# MAGIC
# MAGIC ## Referencias
# MAGIC
# MAGIC * Hájek, J. (1971). "Comment on 'An essay on the logical foundations of survey sampling' by Basu, D." *Foundations of Statistical Inference*.
# MAGIC * Efron, B. & Tibshirani, R. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
# MAGIC * Rao, J.N.K. & Wu, C.F.J. (1988). "Resampling inference with complex survey data". *JASA*, 83(401), 231-241.
# MAGIC * DANE (2020). "Guía de calidad de estimaciones para encuestas de hogares".

# COMMAND ----------

# DBTITLE 1,Importar Liberías
# ============================================================================
# IMPORTS NECESARIOS PARA ESTIMACIÓN DIRECTA CON BOOTSTRAP
# ============================================================================

# --- PySpark ---
from pyspark.sql import functions as F  # Funciones de Spark SQL
                                         # Usado para filtrado inicial de datos

# --- Pandas & NumPy ---
import pandas as pd   # Manipulación de datos en memoria
                      # Bootstrap se ejecuta en pandas (más rápido para este caso)
                      
import numpy as np    # Operaciones numéricas y generación de números aleatorios
                      # Usado para: remuestreo, percentiles, estadísticas

# --- Barra de progreso ---
from tqdm import tqdm  # Barra de progreso para el loop de bootstrap
                       # Muestra progreso de las 5000 réplicas

# COMMAND ----------

# DBTITLE 1,Clase base EstimadorSAE
# ============================================================================
# CLASE BASE ABSTRACTA: EstimadorSAE
# ============================================================================
# Patrón de diseño: Template Method + Strategy
#
# Objetivo: Definir una interfaz común para TODOS los estimadores de
#           Small Area Estimation (SAE), facilitando:
#           - Extensibilidad: Fácil agregar nuevos métodos (Fay-Herriot, EBLUP)
#           - Reutilización: Lógica común (validación, export) en un solo lugar
#           - Consistencia: Misma interfaz para todos los estimadores
#           - Testing: Mockeable y testeable independientemente
#
# Estimadores que heredan de esta clase:
#   - EstimacionDirecta (este notebook)
#   - ModeloFayHerriot (notebook futuro)
#   - EBLUP (notebook futuro)
#   - ModelosJerarquicosBayesianos (notebook futuro)
# ============================================================================

from abc import ABC, abstractmethod  # Para crear clases abstractas
import pandas as pd
import numpy as np
from tqdm import tqdm

class EstimadorSAE(ABC):
    """
    Clase base abstracta para estimadores de Small Area Estimation (SAE).
    
    Esta clase define la interfaz común para todos los métodos de estimación
    de áreas pequeñas (estimación directa, sintética, Fay-Herriot, EBLUP, etc.).
    
    Atributos:
        spark: SparkSession activa
        num_replicas: número de réplicas bootstrap para cálculo de varianza
        seed: semilla aleatoria para reproducibilidad
    """
    
    def __init__(self, spark, num_replicas=1000, seed=42):
        """
        Inicializa el estimador base.
        
        Args:
            spark: SparkSession de Spark (necesario para leer/escribir tablas UC)
            num_replicas: número de réplicas bootstrap (default: 1000)
                         - Más réplicas → más precisión en SE/IC, pero más lento
                         - 1000 es un compromiso razonable entre precisión y velocidad
            seed: semilla aleatoria para reproducibilidad (default: 42)
                  - Garantiza que los resultados sean exactamente reproducibles
        """
        self.spark = spark                # SparkSession activa
        self.num_replicas = num_replicas  # Número de réplicas bootstrap
        self.seed = seed                  # Semilla para RNG
        self._resultado = None            # Cache del último resultado (pandas.DataFrame)
                                          # Se llena después de estimar()
    
    @abstractmethod
    def estimar(self, dataframe, grupo_cols, **kwargs):
        """
        Método abstracto que debe implementar cada estimador específico.
        
        Args:
            dataframe: DataFrame de Spark con los datos
            grupo_cols: lista de columnas para agrupar (dominios)
            **kwargs: argumentos adicionales específicos del estimador
        
        Returns:
            pandas.DataFrame con estimaciones y estadísticas
        """
        pass
    
    def validar_columnas(self, dataframe, columnas_requeridas):
        """
        Valida que las columnas requeridas existan en el DataFrame.
        
        Previene errores criptógrafos al intentar acceder a columnas inexistentes.
        Es llamado automáticamente por cada método estimar() antes de procesar.
        
        Args:
            dataframe: DataFrame de Spark a validar
            columnas_requeridas: lista de nombres de columnas necesarias
                                (ej: ['FEX', 'DESOCUPADO', 'MUNICIPIO'])
        
        Raises:
            ValueError: si alguna columna requerida no existe
                       Mensaje incluye:
                       - Lista de columnas faltantes
                       - Lista de columnas disponibles en el DataFrame
        """
        # Convertir a conjuntos para comparación eficiente
        columnas_df = set(dataframe.columns)
        columnas_faltantes = set(columnas_requeridas) - columnas_df
        
        if columnas_faltantes:
            raise ValueError(
                f"Columnas faltantes en el DataFrame: {sorted(columnas_faltantes)}\n"
                f"Columnas disponibles: {sorted(columnas_df)}"
            )
    
    def exportar(self, tabla_destino, tabla_origen=None, modo="overwrite"):
        """
        Exporta el último resultado calculado a una tabla de Unity Catalog.
        
        Este método:
        1. Convierte el resultado pandas a Spark DataFrame
        2. (Opcional) Preserva lineage con tabla(s) origen mediante crossJoin
        3. Guarda en Unity Catalog con overwriteSchema=true
        
        Args:
            tabla_destino: nombre completo de la tabla (catalog.schema.table)
                          Ejemplo: "tesis.modelo.tasa_desempleo_municipal"
            
            tabla_origen: (opcional) tabla(s) fuente para preservar lineage en UC
                         - String: una sola tabla
                           Ejemplo: "tesis.geih_oro.mercado_laboral"
                         - Lista: múltiples tablas
                           Ejemplo: ["tesis.geih_oro.mercado_laboral",
                                    "tesis.terridata.terridata_extendido_plata"]
            
            modo: modo de escritura de Spark
                 - 'overwrite' (default): Reemplaza tabla existente
                 - 'append': Añade filas a tabla existente
                 - 'error': Error si la tabla ya existe
                 - 'ignore': No hace nada si la tabla ya existe
        
        Raises:
            RuntimeError: si no hay resultados para exportar
                         (debe llamar estimar() primero)
        
        Nota sobre lineage:
            Unity Catalog rastrea automáticamente dependencias entre tablas.
            El lineage permite:
            - Entender qué tablas alimentan qué resultados
            - Análisis de impacto (si cambio tabla X, ¿qué se afecta?)
            - Auditoría y gobernanza de datos
            
            El crossJoin con limit(1) es un "truco" para forzar la dependencia
            sin modificar los datos (la columna _lineage_marker se elimina).
        """
        # --- Validar que hay resultados ---
        if self._resultado is None:
            raise RuntimeError("No hay resultados para exportar. Ejecuta estimar() primero.")
        
        # --- Convertir resultado pandas a Spark DataFrame ---
        print(f"Exportando {len(self._resultado)} filas a {tabla_destino}...")
        resultado_spark = self.spark.createDataFrame(self._resultado)
        
        # --- Preservar lineage si se proporciona tabla(s) origen ---
        # Unity Catalog rastrea dependencias cuando hacemos operaciones entre tablas
        if tabla_origen:
            # Normalizar a lista (soporta string o lista)
            tablas_origen = [tabla_origen] if isinstance(tabla_origen, str) else tabla_origen
            
            print(f"Preservando lineage desde {len(tablas_origen)} tabla(s) origen...")
            
            # --- Paso 1: Leer 1 fila de cada tabla origen ---
            # No necesitamos los datos, solo "tocar" las tablas para el lineage
            dfs_origen = []
            for tabla in tablas_origen:
                df_origen = (
                    self.spark.table(tabla)            # Leer tabla
                    .limit(1)                          # Solo 1 fila (eficiencia)
                    .select(F.lit(1).alias("_lineage_marker"))  # Columna dummy
                )
                dfs_origen.append(df_origen)
            
            # --- Paso 2: UNION de todas las tablas origen ---
            # Esto crea un DataFrame que "toca" todas las fuentes
            df_origen_union = dfs_origen[0]
            for df in dfs_origen[1:]:
                df_origen_union = df_origen_union.union(df)
            
            # --- Paso 3: crossJoin para forzar dependencia ---
            # crossJoin crea una dependencia en el plan de ejecución
            # Unity Catalog detecta esto y registra el lineage
            resultado_spark = resultado_spark.crossJoin(df_origen_union.limit(1))
            
            # --- Paso 4: Eliminar columna dummy ---
            # No queremos _lineage_marker en la tabla final
            resultado_spark = resultado_spark.drop("_lineage_marker")
        
        # --- Guardar en Unity Catalog ---
        resultado_spark.write.mode(modo).option("overwriteSchema", "true").saveAsTable(tabla_destino)
        # overwriteSchema=true: Permite cambiar esquema de tabla existente
        
        print(f"✔ Exportación completada")
        
        # --- Mensaje de confirmación de lineage ---
        if tabla_origen:
            tablas_str = ", ".join(tablas_origen)
            print(f"✔ Lineage preservado: [{tablas_str}] → {tabla_destino}")
            print(f"   (Rastreable en Unity Catalog UI → Pestaña 'Lineage')")
    
    @property
    def resultado(self):
        """Retorna el último resultado calculado."""
        return self._resultado

# COMMAND ----------

# DBTITLE 1,Ejecutar bootstrap simple
# ============================================================================
# CLASE CONCRETA: EstimacionDirecta
# ============================================================================
# Implementa estimación directa de tasa de desempleo usando:
#   - Estimador de Hájek (promedio ponderado por FEX)
#   - Bootstrap simple para inferencia (SE, IC, CV)
#
# Uso apropiado:
#   ✅ Análisis exploratorio
#   ✅ Baseline para comparar con métodos SAE
#   ✅ Prototipado rápido
# ============================================================================

class EstimacionDirecta(EstimadorSAE):
    """
    Estimador directo de áreas pequeñas usando bootstrap simple.
    
    Este estimador calcula la tasa de desempleo (u otra variable binaria) usando
    el estimador de Hájek por dominio, con inferencia basada en bootstrap simple.
    
    ADVERTENCIA: Este método ignora el diseño muestral complejo (estratificación,
    conglomeración) y probablemente subestima los errores estándar.
    
    Ejemplo:
        >>> estimador = EstimacionDirecta(spark, num_replicas=1000, seed=42)
        >>> resultado = estimador.estimar(
        ...     dataframe=df_desempleo,
        ...     grupo_cols=['PER', 'MES', 'NOMBRE_DPTO', 'NOMBRE_AREA'],
        ...     agregacion_anual=False
        ... )
        >>> estimador.exportar('tesis.geih_oro.tasa_desempleo_municipal')
    """
    
    def estimar(self, dataframe, grupo_cols, agregacion_anual=False):
        """
        Calcula estimación directa con bootstrap simple.
        
        Flujo del proceso:
        1. Ajustar columnas de agrupación (remover MES si es anual)
        2. Validar que existan columnas necesarias
        3. Convertir a Pandas (más eficiente para bootstrap)
        4. Ejecutar bootstrap (B réplicas)
        5. Calcular estadísticas (SE, IC, CV)
        6. Formatear y retornar resultado
        
        Args:
            dataframe: DataFrame de Spark con columnas:
                      - 'FEX': Factor de expansión (peso muestral)
                      - 'DESOCUPADO': Variable binaria (1=desocupado, 0=ocupado)
                      - Columnas en grupo_cols
            
            grupo_cols: lista de columnas para definir dominios de estimación
                       Cada combinación única = un dominio = una estimación
                       Ejemplos:
                       - ['PER', 'MES', 'CODIGO_MUNICIPIO', 'MUNICIPIO']
                       - ['PER', 'CODIGO_DEPARTAMENTO', 'DEPARTAMENTO']
            
            agregacion_anual: bool, si True remueve 'MES' de grupo_cols
                            - False (default): Estimaciones mensuales
                            - True: Estimaciones anuales (agrega todos los meses)
                            Ventaja de anual: más muestra → menor CV
        
        Returns:
            pandas.DataFrame con columnas:
                - Columnas de agrupación (dominios)
                - TASA_DESEMPLEO_PCT: tasa estimada en porcentaje [0-100]
                - SE_BOOTSTRAP_PCT: error estándar bootstrap en ptos porcentuales
                - IC_INF_PCT, IC_SUP_PCT: intervalo de confianza 95%
                - AMPLITUD_IC: amplitud del intervalo (IC_SUP - IC_INF)
                - CV_PORCENTAJE: coeficiente de variación (SE/Tasa × 100)
                  » CV < 15%: CONFIABLE
                  » 15% ≤ CV < 30%: ACEPTABLE
                  » CV ≥ 30%: NO CONFIABLE
        """
        # ========================================================================
        # PASO 1: AJUSTAR COLUMNAS DE AGRUPACIÓN SEGÚN AGREGACIÓN TEMPORAL
        # ========================================================================
        grupo_cols_final = self._ajustar_grupo_cols(grupo_cols, agregacion_anual)
        
        # ========================================================================
        # PASO 2: VALIDAR QUE EXISTAN LAS COLUMNAS NECESARIAS
        # ========================================================================
        # Combinar columnas de grupo + variables necesarias
        # set() elimina duplicados (por si FEX o DESOCUPADO ya están en grupo_cols)
        columnas_necesarias = list(set(grupo_cols_final + ['FEX', 'DESOCUPADO']))
        self.validar_columnas(dataframe, columnas_necesarias)
        # Si falta alguna columna, validar_columnas() lanza ValueError
        
        # ========================================================================
        # PASO 3: CONVERTIR A PANDAS
        # ========================================================================
        # ¿Por qué Pandas y no Spark para bootstrap?
        # - Bootstrap requiere remuestreo aleatorio repetido (5000 veces)
        # - Pandas + NumPy es MUCHO más rápido para este tipo de operación
        # - Para ~20K filas, Pandas cabe en memoria sin problema
        # - Para >1M filas, considerar Dask o PySpark MLlib
        
        print(f"\nConvirtiendo a Pandas...")
        df_pd = dataframe.select(*columnas_necesarias).toPandas()
        print(f"Datos cargados: {len(df_pd):,} filas")
        print(f"Dominios: {df_pd[grupo_cols_final].drop_duplicates().shape[0]}")
        
        # ========================================================================
        # PASO 4: EJECUTAR BOOTSTRAP
        # ========================================================================
        # Aquí ocurre la magia: 5000 réplicas de remuestreo
        # Esto es lo más demorado del proceso (~1-5 minutos)
        
        print(f"\nIniciando bootstrap con {self.num_replicas:,} réplicas...")
        resultado_bootstrap = self._bootstrap_hajek(df_pd, grupo_cols_final)
        # Ver método _bootstrap_hajek() abajo para detalles del algoritmo
        
        # ========================================================================
        # PASO 5: SELECCIONAR COLUMNAS FINALES Y ALMACENAR RESULTADO
        # ========================================================================
        # Ordenar columnas: primero identificación, luego estimaciones
        columnas_resultado = grupo_cols_final + [
            'TASA_DESEMPLEO_PCT',   # Estimación puntual
            'SE_BOOTSTRAP_PCT',      # Error estándar
            'IC_INF_PCT',            # Límite inferior IC 95%
            'IC_SUP_PCT',            # Límite superior IC 95%
            'AMPLITUD_IC',           # Amplitud del intervalo
            'CV_PORCENTAJE'          # Coeficiente de variación
        ]
        
        # Ordenar por dominios (facilita navegación)
        self._resultado = resultado_bootstrap[columnas_resultado].sort_values(grupo_cols_final)
        
        # ========================================================================
        # ADVERTENCIA FINAL
        # ========================================================================
        print("\n" + "="*70)
        print("⚠️  ADVERTENCIA: Bootstrap 'naive' - Diseño muestral ignorado")
        print("="*70)
        print("Este método NO considera:")
        print("  ❌ Estratificación")
        print("  ❌ Conglomeración (PSU, SSU)")
        print("  ❌ Calibración de pesos")
        print("\nConsecuencia: Errores estándar SUBESTIMADOS")
        print("              Intervalos de confianza ARTIFICIALMENTE estrechos")
        print("\nUsar solo para: Análisis exploratorio o baseline SAE")
        print("NO usar para: Publicación oficial")
        print("="*70 + "\n")
        
        return self._resultado
    
    # ========================================================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ========================================================================
    
    def _ajustar_grupo_cols(self, grupo_cols, agregacion_anual):
        """
        Ajusta las columnas de agrupación según el nivel temporal deseado.
        
        Si agregacion_anual=True, remueve 'MES' para estimar a nivel anual
        en lugar de mensual.
        
        Ventaja de agregación anual:
        - Más observaciones por dominio → menor variabilidad
        - CV más bajo → mayor probabilidad de estimaciones confiables
        
        Args:
            grupo_cols: lista original de columnas
            agregacion_anual: si True, remueve 'MES'
        
        Returns:
            lista ajustada de columnas (copia, no modifica original)
        """
        if agregacion_anual and 'MES' in grupo_cols:
            print("📅 Agregación anual: removiendo MES de la agrupación")
            print("   (Se agregarán todos los meses del año en cada dominio)")
            return [col for col in grupo_cols if col != 'MES']
        return grupo_cols.copy()  # .copy() para no modificar la lista original
    
    def _calcular_hajek_pandas(self, df, grupo_cols):
        """
        Calcula estimador de Hájek por grupo en pandas.
        
        Fórmula del estimador de Hájek (estimador de razón):
        
            θ̂ = Σ(w_i × y_i) / Σ(w_i)
        
        Donde:
            w_i = FEX (factor de expansión / peso muestral)
            y_i = DESOCUPADO (1 si desocupado, 0 si ocupado)
        
        Interpretación:
            Es un promedio ponderado de la variable binaria DESOCUPADO,
            donde cada individuo contribuye según su peso de expansión.
            Resultado = proporción de desocupados en la población (0 a 1).
        
        Args:
            df: pandas DataFrame con columnas grupo_cols, 'FEX', 'DESOCUPADO'
            grupo_cols: columnas para agrupar (define dominios)
        
        Returns:
            pandas DataFrame con columnas:
            - grupo_cols (identificadores del dominio)
            - TASA_DESEMPLEO (proporción 0-1)
        """
        result = df.groupby(grupo_cols).apply(
            lambda g: pd.Series({
                # Numerador: suma de (peso × desocupado)
                # Denominador: suma de pesos
                # Resultado: proporción ponderada de desocupados
                'TASA_DESEMPLEO': (g['DESOCUPADO'] * g['FEX']).sum() / g['FEX'].sum()
            }),
            include_groups=False  # No incluir grupo_cols en la columna de resultado
        ).reset_index()  # Convertir índice multi-nivel a columnas
        return result
    
    def _bootstrap_hajek(self, df, grupo_cols):
        """
        Bootstrap simple para estimador de Hájek.
        
        Algoritmo de bootstrap simple (naive):
        
        1. Calcular estimador original θ̂ en la muestra completa
        2. Para b = 1 hasta B réplicas:
           a. Remuestrear n observaciones CON REEMPLAZO de la muestra original
           b. Calcular estimador θ̂*_b en la réplica b
        3. Usar la distribución de {θ̂*_1, ..., θ̂*_B} para inferencia:
           - SE = desviación estándar de las réplicas
           - IC 95% = [percentil 2.5%, percentil 97.5%]
        
        ADVERTENCIA: Este método remuestrea INDIVIDUOS ignorando:
        - Estratos (debería remuestrear dentro de estratos)
        - PSUs (debería remuestrear PSUs, no individuos)
        - Calibración de pesos
        
        Consecuencia: SE subestimado (intervalos artificialmente estrechos)
        
        Args:
            df: pandas DataFrame con datos (columnas: grupo_cols, FEX, DESOCUPADO)
            grupo_cols: columnas para agrupar (define dominios)
        
        Returns:
            pandas DataFrame con columnas:
            - grupo_cols (identificadores del dominio)
            - TASA_DESEMPLEO (estimador original, proporción 0-1)
            - MEDIA_BOOTSTRAP (media de réplicas, debería ≈ TASA_DESEMPLEO)
            - VAR_BOOTSTRAP (varianza de réplicas)
            - SE_BOOTSTRAP (desviación estándar de réplicas)
            - IC_INF_2.5, IC_SUP_97.5 (percentiles 2.5% y 97.5%)
            - CV_PORCENTAJE (SE/Tasa × 100)
            - AMPLITUD_IC ((IC_SUP - IC_INF) × 100, en puntos porcentuales)
            - *_PCT (versiones en porcentaje 0-100)
        """
        print(f"🔄 Remuestreando {len(df):,} observaciones individuales\n")
        
        # ====================================================================
        # PASO 1: CALCULAR ESTIMADOR ORIGINAL (MUESTRA COMPLETA)
        # ====================================================================
        print("🎯 Calculando estimador original en muestra completa...")
        estimador_original = self._calcular_hajek_pandas(df, grupo_cols)
        print(f"   Dominios estimados: {len(estimador_original)}\n")
        
        # ====================================================================
        # PASO 2: GENERAR RÉPLICAS BOOTSTRAP
        # ====================================================================
        print("🔄 Ejecutando réplicas bootstrap...")
        print(f"   (Esto puede tomar ~1-5 minutos para {self.num_replicas} réplicas)\n")
        
        n = len(df)  # Tamaño de muestra original
        np.random.seed(self.seed)  # Fijar semilla para reproducibilidad
        
        replicas = []  # Acumular réplicas aquí
        
        # --- Loop principal de bootstrap ---
        for b in tqdm(range(self.num_replicas), desc="🔄 Bootstrap"):
            # --- Paso 2a: Remuestrear con reemplazo ---
            # np.random.choice selecciona n índices aleatoriamente CON REEMPLAZO
            # Esto significa que:
            #   - Algunas observaciones aparecerán múltiples veces
            #   - Otras observaciones no aparecerán
            # En promedio, ~63% de las observaciones únicas aparecerán
            indices = np.random.choice(n, size=n, replace=True)
            df_boot = df.iloc[indices]  # Muestra bootstrap b
            
            # --- Paso 2b: Calcular estimador en réplica b ---
            est_boot = self._calcular_hajek_pandas(df_boot, grupo_cols)
            est_boot['replica'] = b  # Marcar número de réplica
            replicas.append(est_boot)
        
        # ====================================================================
        # PASO 3: CONSOLIDAR TODAS LAS RÉPLICAS EN UN SOLO DATAFRAME
        # ====================================================================
        print("\n📦 Consolidando resultados...")
        # pd.concat apila todas las réplicas verticalmente
        # Resultado: DataFrame largo con (B × num_dominios) filas
        df_replicas = pd.concat(replicas, ignore_index=True)
        
        # ====================================================================
        # PASO 4: CALCULAR ESTADÍSTICAS BOOTSTRAP POR DOMINIO
        # ====================================================================
        # Agrupar por dominio y calcular estadísticas sobre la distribución
        # de las B estimaciones bootstrap
        
        stats = df_replicas.groupby(grupo_cols)['TASA_DESEMPLEO'].agg([
            # Media de las réplicas (debería ≈ estimador original)
            ('MEDIA_BOOTSTRAP', 'mean'),
            
            # Varianza de las réplicas
            ('VAR_BOOTSTRAP', 'var'),
            
            # Desviación estándar de las réplicas = ERROR ESTÁNDAR BOOTSTRAP
            # Esta es la medida de precisión del estimador
            ('SE_BOOTSTRAP', 'std'),
            
            # Percentil 2.5% = Límite inferior del IC 95%
            ('IC_INF_2.5', lambda x: np.percentile(x, 2.5)),
            
            # Percentil 97.5% = Límite superior del IC 95%
            ('IC_SUP_97.5', lambda x: np.percentile(x, 97.5))
        ]).reset_index()
        
        # ====================================================================
        # PASO 5: COMBINAR ESTIMADOR ORIGINAL CON ESTADÍSTICAS BOOTSTRAP
        # ====================================================================
        resultado = estimador_original.merge(stats, on=grupo_cols, how='left')
        # LEFT join para preservar todos los dominios del estimador original
        
        # ====================================================================
        # PASO 6: CALCULAR MÉTRICAS DERIVADAS
        # ====================================================================
        
        # --- Coeficiente de Variación (CV) ---
        # CV = (SE / Estimación) × 100
        # Mide precisión relativa (independiente de la escala)
        # CV < 15%: CONFIABLE, 15-30%: ACEPTABLE, >30%: NO CONFIABLE
        resultado['CV_PORCENTAJE'] = (
            (resultado['SE_BOOTSTRAP'] / resultado['TASA_DESEMPLEO']) * 100
        )
        
        # --- Amplitud del Intervalo de Confianza ---
        # Amplitud = IC_SUP - IC_INF (en puntos porcentuales)
        # Menor amplitud = mayor precisión
        resultado['AMPLITUD_IC'] = (
            (resultado['IC_SUP_97.5'] - resultado['IC_INF_2.5']) * 100
        )
        
        # ====================================================================
        # PASO 7: CONVERTIR PROPORCIONES A PORCENTAJES
        # ====================================================================
        # Multiplicar por 100 para pasar de escala [0, 1] a [0, 100]
        # Más intuitivo para interpretación ("10.5%" vs "0.105")
        
        resultado['TASA_DESEMPLEO_PCT'] = resultado['TASA_DESEMPLEO'] * 100
        resultado['SE_BOOTSTRAP_PCT'] = resultado['SE_BOOTSTRAP'] * 100
        resultado['IC_INF_PCT'] = resultado['IC_INF_2.5'] * 100
        resultado['IC_SUP_PCT'] = resultado['IC_SUP_97.5'] * 100
        
        # ====================================================================
        # RESUMEN FINAL
        # ====================================================================
        print("\n" + "="*60)
        print("✅ BOOTSTRAP COMPLETADO EXITOSAMENTE")
        print("="*60)
        print(f"Total réplicas procesadas: {self.num_replicas:,}")
        print(f"Total dominios estimados: {len(resultado)}")
        print(f"\nESTADÍSTICAS GENERADAS POR DOMINIO:")
        print(f"  • TASA_DESEMPLEO_PCT (estimación puntual)")
        print(f"  • SE_BOOTSTRAP_PCT (error estándar)")
        print(f"  • IC_INF_PCT, IC_SUP_PCT (intervalo 95%)")
        print(f"  • AMPLITUD_IC (ancho del intervalo)")
        print(f"  • CV_PORCENTAJE (precisión relativa)")
        print("="*60 + "\n")
        
        return resultado

# COMMAND ----------

# DBTITLE 1,Guardar resultado
# ============================================================================
# EJEMPLO DE USO: EstimacionDirecta
# ============================================================================
# Este ejemplo muestra el flujo completo de:
#   1. Cargar y filtrar datos de GEIH
#   2. Crear instancia del estimador
#   3. Ejecutar estimación directa con bootstrap
#   4. Visualizar resultados
#   5. Exportar a Unity Catalog con lineage
# ============================================================================

# ============================================================================
# PASO 1: CARGAR Y FILTRAR DATOS DE GEIH
# ============================================================================
# Tabla fuente: tesis.geih_oro.mercado_laboral
# Contiene microdatos de GEIH (Gran Encuesta Integrada de Hogares)

df_desempleo = spark.table("tesis.geih_oro.mercado_laboral").filter(
    # --- Filtro 1: Solo registros con municipio identificado ---
    (F.col("MUNICIPIO").isNotNull()) &
    
    # --- Filtro 2: Solo Población Económicamente Activa (PEA) ---
    # PEA = 1: personas ocupadas o desocupadas (excluye inactivos)
    # Necesario porque la tasa de desempleo se define sobre la PEA
    (F.col("PEA") == 1) &
    
    # --- Filtro 3: Año 2018 ---
    (F.col("PER") == 2018) &
    
    # --- Filtro 4: Mes de diciembre ---
    # Diciembre suele tener mayor muestra por fin de año
    (F.col("MES") == 12)
)

print(f"📁 Datos filtrados: {df_desempleo.count():,} observaciones de PEA")
print(f"📍 Municipios con muestra: {df_desempleo.select('CODIGO_MUNICIPIO').distinct().count()}")


# ============================================================================
# PASO 2: CREAR INSTANCIA DEL ESTIMADOR
# ============================================================================
# Configuración del estimador:
#   - num_replicas: 5000 (compromiso entre precisión y velocidad)
#   - seed: 42 (garantiza reproducibilidad exacta)

estimador = EstimacionDirecta(
    spark=spark,
    num_replicas=2000,  # Más réplicas → SE más preciso, pero más lento
                       # 1000 es adecuado para producción
                       # Para pruebas rápidas: 200-300
    
    seed=42            # Semilla aleatoria para reproducibilidad
                       # Con la misma semilla, los resultados serán idénticos
)

print("✅ Estimador creado exitosamente")


# ============================================================================
# PASO 3: EJECUTAR ESTIMACIÓN DIRECTA CON BOOTSTRAP
# ============================================================================
# Aquí ocurre el cálculo principal:
#   - Validación de columnas
#   - Conversión a Pandas
#   - 5000 réplicas bootstrap (~2-5 minutos)
#   - Cálculo de estadísticas (SE, IC, CV)

print("\n" + "="*60)
print("🚀 INICIANDO ESTIMACIÓN DIRECTA")
print("="*60 + "\n")

resultado = estimador.estimar(
    dataframe=df_desempleo,
    
    # --- Definir dominios de estimación ---
    # Cada combinación única de estas columnas = un dominio = una estimación
    # Aquí: nivel municipal mensual
    grupo_cols=[
        "PER",                  # Año
        "MES",                  # Mes
        "CODIGO_DEPARTAMENTO",  # Código DIVIPOLA del departamento
        "DEPARTAMENTO",         # Nombre del departamento
        "CODIGO_MUNICIPIO",     # Código DIVIPOLA del municipio (5 dígitos)
        "MUNICIPIO"             # Nombre del municipio
    ],
    
    # --- Agregación temporal ---
    agregacion_anual=False  # False: estimaciones MENSUALES (una por mes)
                            # True: estimaciones ANUALES (agrega todos los meses)
                            # Anual tiene ventaja de más muestra → menor CV
)

print("\n✅ Estimación completada exitosamente\n")


# ============================================================================
# PASO 4: VISUALIZAR RESULTADOS
# ============================================================================
# El resultado es un pandas.DataFrame con:
#   - 6 columnas de identificación (PER, MES, DPTO, MUN)
#   - 6 columnas de estimación (Tasa, SE, IC, CV)

print(f"\n📊 RESUMEN DE RESULTADOS:")
print(f"   Total de municipios estimados: {len(resultado)}")
print(f"   Período: {resultado['PER'].iloc[0]}-{resultado['MES'].iloc[0]:02d}")

# --- Mostrar primeras 20 filas ---
print("\n👁️  Primeros 20 municipios:\n")
display(resultado.head(20))

# --- Resumen de calidad de estimaciones ---
print("\n🎯 CALIDAD DE ESTIMACIONES (según CV):")
print(f"   CONFIABLES (CV < 15%):     {(resultado['CV_PORCENTAJE'] < 15).sum()} municipios")
print(f"   ACEPTABLES (15% ≤ CV < 30%): {((resultado['CV_PORCENTAJE'] >= 15) & (resultado['CV_PORCENTAJE'] < 30)).sum()} municipios")
print(f"   NO CONFIABLES (CV ≥ 30%):  {(resultado['CV_PORCENTAJE'] >= 30).sum()} municipios")

# --- Estadísticas descriptivas ---
print("\n📊 ESTADÍSTICAS DESCRIPTIVAS:")
print(f"   Tasa de desempleo:")
print(f"     - Promedio: {resultado['TASA_DESEMPLEO_PCT'].mean():.2f}%")
print(f"     - Mínimo:  {resultado['TASA_DESEMPLEO_PCT'].min():.2f}% ({resultado.loc[resultado['TASA_DESEMPLEO_PCT'].idxmin(), 'MUNICIPIO']})")
print(f"     - Máximo:  {resultado['TASA_DESEMPLEO_PCT'].max():.2f}% ({resultado.loc[resultado['TASA_DESEMPLEO_PCT'].idxmax(), 'MUNICIPIO']})")
print(f"\n   Coeficiente de Variación (CV):")
print(f"     - Promedio: {resultado['CV_PORCENTAJE'].mean():.1f}%")
print(f"     - Mínimo:  {resultado['CV_PORCENTAJE'].min():.1f}%")
print(f"     - Máximo:  {resultado['CV_PORCENTAJE'].max():.1f}%")


# ============================================================================
# PASO 5: EXPORTAR RESULTADOS A UNITY CATALOG
# ============================================================================
# Guardar resultados en tabla persistente con lineage preservado

print("\n" + "="*60)
print("💾 EXPORTANDO RESULTADOS A UNITY CATALOG")
print("="*60 + "\n")

# --- Opción 5a: Exportar con UNA tabla origen ---
# Caso típico: estimación directa solo depende de mercado_laboral
estimador.exportar(
    # Tabla destino en Unity Catalog
    tabla_destino="tesis.modelo.tasa_desempleo_municipal",
    
    # Tabla origen (string simple para una sola tabla)
    # Unity Catalog registrará la dependencia:
    #   mercado_laboral → tasa_desempleo_municipal
    tabla_origen="tesis.geih_oro.mercado_laboral"
)

print("\n✅ Tabla guardada: tesis.modelo.tasa_desempleo_municipal")
print("   Acceso: SELECT * FROM tesis.modelo.tasa_desempleo_municipal")
print("   Lineage visible en Unity Catalog UI → Pestaña 'Lineage'\n")

# --- Opción 5b: Exportar con MÚLTIPLES tablas origen (comentado) ---
# Ejemplo para modelos SAE que usan múltiples fuentes:
#   - Estimación directa (variable dependiente)
#   - Covariables del censo
#   - Covariables de TerriData
#   - etc.
#
# Unity Catalog registrará todas las dependencias:
#   [mercado_laboral + variables_municipales + tasa_desempleo_municipal] → resultado_fh

# estimador.exportar(
#     tabla_destino="tesis.modelo.tasa_desempleo_fh",
#     
#     # Lista de tablas origen (múltiples dependencias)
#     tabla_origen=[
#         "tesis.geih_oro.mercado_laboral",          # Microdatos de GEIH
#         "tesis.censo.variables_municipales",       # Covariables del censo
#         "tesis.modelo.tasa_desempleo_municipal"    # Estimación directa previa
#     ]
# )


# ============================================================================
# PASO 6: ACCEDER AL RESULTADO GUARDADO EN CACHE
# ============================================================================
# El estimador guarda el último resultado en memoria (self._resultado)
# Accesible mediante la propiedad .resultado

print("\n" + "="*60)
print("📋 ACCESO AL RESULTADO EN CACHE")
print("="*60)
print(f"\nResultado almacenado en memoria: {len(estimador.resultado)} dominios")
print(f"Tipo: {type(estimador.resultado)}")
print(f"Columnas: {list(estimador.resultado.columns)}")

# --- Usos del resultado en cache ---
print("\nútil para:")
print("  • Explorar resultados sin re-ejecutar bootstrap")
print("  • Filtrar/transformar antes de exportar")
print("  • Crear visualizaciones")
print("  • Comparar con otras estimaciones")

# --- Ejemplo: Filtrar solo estimaciones confiables ---
confiables = estimador.resultado[estimador.resultado['CV_PORCENTAJE'] < 15]
print(f"\nEjemplo - Municipios con CV < 15%: {len(confiables)}")

print("\n" + "="*60)
print("✅ PROCESO COMPLETADO")
print("="*60)
print("\nPróximos pasos sugeridos:")
print("  1. Agregar covariables de TerriData (notebook: adicion_covariables)")
print("  2. Implementar modelo Fay-Herriot para mejorar estimaciones")
print("  3. Validar mejora vs estimación directa (MSE, cobertura)")
print("  4. Generar visualizaciones y reportes")