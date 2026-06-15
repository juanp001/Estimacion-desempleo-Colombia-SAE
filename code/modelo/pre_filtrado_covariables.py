# Databricks notebook source
# 1. Leer la tabla de Databricks y cargarla en un DataFrame de PySpark
df_spark = spark.read.table("`tesis`.`modelo`.`tasa_desempleo_covariables`")

# 2. Convertir a Pandas DataFrame para facilitar la manipulación matemática de las 1.500 columnas
df = df_spark.toPandas()

# 3. Definir las columnas de control y métricas del mercado laboral
metadata_cols = [
    'PER', 'MES', 'CODIGO_DEPARTAMENTO', 'DEPARTAMENTO', 
    'CODIGO_MUNICIPIO', 'MUNICIPIO', 'TASA_DESEMPLEO_PCT', 
    'SE_BOOTSTRAP_PCT', 'IC_INF_PCT', 'IC_SUP_PCT', 
    'AMPLITUD_IC', 'CV_PORCENTAJE', 'DEPARTAMENTO_NORMALIZADO', 
    'ENTIDAD_NORMALIZADO'
]

# 4. Aislar únicamente las columnas que corresponden a covariables candidatas
covariables_cols = [col for col in df.columns if col not in metadata_cols]
df_covariables = df[covariables_cols].copy()

# 5. Homogenizar tipos de datos (Forzar a numérico y convertir textos extraños en NaN)
for col in df_covariables.select_dtypes(include=['object']).columns:
    import pandas as pd
    df_covariables[col] = pd.to_numeric(df_covariables[col], errors='coerce')

# =========================================================================
# ETAPA 1: CONTROL DE DATOS FALTANTES
# =========================================================================

# Contar cuántos valores faltantes tiene cada columna en los 23 registros
nas_por_columna = df_covariables.isna().sum()

# Filtrar y conservar solo las columnas que tengan exactamente cero (0) NAs
cols_sin_nas = nas_por_columna[nas_por_columna == 0].index.tolist()

# Crear el DataFrame que pasa este primer filtro institucional
df_filtrado_na = df_covariables[cols_sin_nas]

# Mostrar resultados en la consola de Databricks
print(f"Número de covariables candidatas iniciales: {len(covariables_cols)}")
print(f"Variables sobrevivientes sin ningún dato faltante (0 NAs): {len(cols_sin_nas)}")

# COMMAND ----------

# MAGIC %md
# MAGIC De las 1.582 variables originales, solo 530 variables están completamente llenas (0 registros faltantes) para los 23 departamentos. Las otras 1.052 variables se descartan de inmediato porque introducen vacíos de información que desestabilizan el cálculo.

# COMMAND ----------

# MAGIC %md
# MAGIC **Paso 1.2 - Filtro Variables con Varianza cero** 

# COMMAND ----------

# 1. Calcular la varianza para cada una de las 530 columnas sobrevivientes
varianzas_por_columna = df_filtrado_na.var()

# 2. Definir un umbral mínimo de varianza (en estadística, mayor a cero)
# Usamos un valor muy pequeño (0.00001) para evitar que variables constantes por redondeo numérico pasen el filtro
umbral_varianza = 0.00001

# 3. Filtrar y conservar solo los nombres de columnas cuya varianza supere el umbral
cols_con_varianza = varianzas_por_columna[varianzas_por_columna > umbral_varianza].index.tolist()

# 4. Encontrar cuáles fueron las 7 variables eliminadas (solo para saber por si se necesita mas adelante o simplemente por entender cuales fueron)
cols_eliminadas_varianza = [col for col in df_filtrado_na.columns if col not in cols_con_varianza]

# 5. Crear el DataFrame de esta Etapa 1.2
df_final_etapa1_2 = df_filtrado_na[cols_con_varianza]

# Mostrar resultados en la consola de Databricks
print(f"Variables recibidas del filtro de NAs: {df_filtrado_na.shape[1]}")
print(f"Variables eliminadas por tener varianza cero (constantes): {len(cols_eliminadas_varianza)}")
print(f"Códigos de las variables eliminadas por varianza: {cols_eliminadas_varianza}")
print(f"Variables definitivas y potencialmente útiles para la Etapa 2 (PCA): {len(cols_con_varianza)}")

# COMMAND ----------

# MAGIC %md
# MAGIC Introducir una variable constante en un modelo de regresión (como el componente lineal de un modelo Fay-Herriot) produce un error matemático severo llamado singularidad de la matriz. Esto ocurre porque la variable constante se vuelve colineal con el intercepto del modelo ($\beta_0$), haciendo imposible que el software estime los coeficientes de regresión.
# MAGIC
# MAGIC Al definir un filtro explícito de varianzas > 0.00001, se demuestra  un manejo riguroso del almacenamiento de datos. En TerriData hay variables de tasas muy pequeñas donde la varianza puede dar números extremadamente cercanos a cero (ej. 0.0000001); este código asegura que solo se eliminen aquellas que realmente no cambian en ningún departamento.

# COMMAND ----------

# DBTITLE 1,Cell 9
# MAGIC %md
# MAGIC **Paso 2** - Seleccionar las variables con mayor correlación directa con la variable objetivo
# MAGIC
# MAGIC Se implementa una **función unificada** que permite dos estrategias de selección:
# MAGIC * **Top N:** Selecciona las N variables con mayor correlación absoluta
# MAGIC * **Umbral:** Selecciona todas las variables que superen un umbral de correlación absoluta definido

# COMMAND ----------

# DBTITLE 1,Cell 10
# =========================================================================
# FUNCIÓN UNIFICADA - PASO 2: SELECCIÓN DE VARIABLES POR CORRELACIÓN
# =========================================================================

def seleccionar_variables_por_correlacion(
    df_covariables,
    df_metadata,
    variable_objetivo,
    df_diccionario,
    modo='top_n',
    valor=12
):
    """
    Selecciona variables con mayor correlación con la variable objetivo.
    
    Parámetros:
    -----------
    df_covariables : pd.DataFrame
        DataFrame con las covariables candidatas (post-filtros de NA y varianza)
    df_metadata : pd.DataFrame
        DataFrame original que contiene la variable objetivo
    variable_objetivo : str
        Nombre de la columna objetivo (ej: 'TASA_DESEMPLEO_PCT')
    df_diccionario : pd.DataFrame
        Diccionario de TerriData para traducir códigos a nombres
    modo : str, default='top_n'
        Estrategia de selección:
        - 'top_n': Selecciona las N variables con mayor correlación absoluta
        - 'threshold': Selecciona variables que superen un umbral de correlación absoluta
    valor : int o float
        - Si modo='top_n': número de variables a seleccionar (ej: 12)
        - Si modo='threshold': umbral mínimo de correlación absoluta (ej: 0.40)
    
    Retorna:
    --------
    tuple: (variables_ganadoras, df_reporte)
        - variables_ganadoras: lista de códigos de variables seleccionadas
        - df_reporte: DataFrame con el reporte detallado
    """
    
    # 1. Calcular correlaciones de Pearson
    dict_correlaciones = {}
    for col in df_covariables.columns:
        dict_correlaciones[col] = df_covariables[col].corr(df_metadata[variable_objetivo])
    
    # 2. Crear DataFrame de correlaciones
    df_corr = pd.DataFrame.from_dict(dict_correlaciones, orient='index', columns=['Correlacion_Real'])
    df_corr['Correlacion_Abs'] = df_corr['Correlacion_Real'].abs()
    
    # 3. Ordenar por correlación absoluta
    df_corr_ordenado = df_corr.sort_values(by='Correlacion_Abs', ascending=False)
    
    # 4. Aplicar estrategia de selección
    if modo == 'top_n':
        variables_ganadoras = df_corr_ordenado.index[:int(valor)].tolist()
        mensaje_criterio = f"Top {int(valor)} variables con mayor correlación absoluta"
    elif modo == 'threshold':
        df_filtrado = df_corr_ordenado[df_corr_ordenado['Correlacion_Abs'] >= valor]
        variables_ganadoras = df_filtrado.index.tolist()
        mensaje_criterio = f"Variables con |r| >= {valor}"
    else:
        raise ValueError("Modo debe ser 'top_n' o 'threshold'")
    
    # 5. Generar reporte con traducción de códigos
    reporte_ganadoras = []
    for idx, col_codigo in enumerate(variables_ganadoras, 1):
        coincidencia = df_diccionario[df_diccionario['CODIGO_INDICADOR'] == col_codigo]
        nombre_real = coincidencia['INDICADOR'].values[0] if not coincidencia.empty else "No encontrado en diccionario"
        dimension = coincidencia['DIMENSION'].values[0] if not coincidencia.empty else "N/A"
        
        corr_real = df_corr_ordenado.loc[col_codigo, 'Correlacion_Real']
        corr_abs = df_corr_ordenado.loc[col_codigo, 'Correlacion_Abs']
        
        reporte_ganadoras.append({
            'Puesto': idx,
            'Código': col_codigo,
            'Dimensión': dimension,
            'Nombre Indicador': nombre_real,
            'Corr. Real': round(corr_real, 4),
            'Corr. Abs': round(corr_abs, 4)
        })
    
    df_reporte = pd.DataFrame(reporte_ganadoras)
    
    # 6. Imprimir resumen
    print(f"=== PASO 2 CONCLUIDO ===")
    print(f"Se evaluaron {df_covariables.shape[1]} variables limpias de la Etapa 1.2.")
    print(f"Criterio: {mensaje_criterio}")
    print(f"Variables seleccionadas: {len(variables_ganadoras)}\n")
    
    return variables_ganadoras, df_reporte

# COMMAND ----------

# DBTITLE 1,Cell 11
# =========================================================================
# EJECUCIÓN: SELECCIONAR VARIABLES GANADORAS
# =========================================================================

# Cargar diccionario de TerriData
df_spark = spark.read.table("`tesis`.`dim`.dim_indicadores")
df_diccionario = df_spark.toPandas()
df_diccionario['CODIGO_INDICADOR'] = df_diccionario['CODIGO_INDICADOR'].astype(str)

# -------------------------------------------------------------------------
# OPCIÓN 1: Seleccionar Top N variables (descomenta para usar)
# -------------------------------------------------------------------------
#variables_ganadoras, df_reporte_paso = seleccionar_variables_por_correlacion(
#    df_covariables=df_final_etapa1_2,
#    df_metadata=df,
#    variable_objetivo='TASA_DESEMPLEO_PCT',
#    df_diccionario=df_diccionario,
#    modo='top_n',
#    valor=12  # Selecciona las 12 variables con mayor correlación
#)

# -------------------------------------------------------------------------
# OPCIÓN 2: Seleccionar por umbral (comenta la Opción 1 y descomenta esto)
# -------------------------------------------------------------------------
variables_ganadoras, df_reporte_paso = seleccionar_variables_por_correlacion(
     df_covariables=df_final_etapa1_2,
     df_metadata=df,
     variable_objetivo='TASA_DESEMPLEO_PCT',
     df_diccionario=df_diccionario,
     modo='threshold',
     valor=0.4  # Selecciona variables con |r| >= 0.40
 )

# Visualizar resultado
display(df_reporte_paso)