# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC **METODOLOGÍA DE SELECCIÓN DE COVARIABLES Ver 2.0** 
# MAGIC
# MAGIC Metodologias mas comunmente utilizadas para la seleccion de variables auxiliares en en proyectos de estimación en áreas pequeñas (SAE) aplicados a la tasa de desempleo o indicadores similares:
# MAGIC
# MAGIC **1. Algoritmos de Selección Automática (Stepwise)**
# MAGIC
# MAGIC Es la metodología más citada para filtrar grandes conjuntos de datos administrativos.
# MAGIC
# MAGIC * **Procedimiento:** Se utiliza comúnmente el algoritmo stepwise (hacia adelante o hacia atrás) que selecciona variables basándose en criterios de optimización estadística (Zea y Ortiz 2019), (DANE metodologia-estimaciones-pobreza-alimentaria-fies-modelo-sae-2022-y-2024)
# MAGIC * **Criterios de decisión:** La selección se rige principalmente por el Criterio de Información de Akaike (AIC) o el Criterio de Información Bayesiano (BIC), buscando el modelo más parsimonioso que maximice la capacidad predictiva. (Chile 2024),(Montoya 2019),(DANE metodologia-estimaciones-pobreza-alimentaria-fies-modelo-sae-2022-y-2024)
# MAGIC * **Uso práctico:** En aplicaciones del DANE, se parte de una base robusta (ej. 208 variables) y se emplea la librería bigstep de R para identificar las covariables más relevantes para el municipio. (DANE metodologia-estimaciones-pobreza-alimentaria-fies-modelo-sae-2022-y-2024)
# MAGIC
# MAGIC
# MAGIC **2. Análisis de Componentes Principales (ACP)**
# MAGIC
# MAGIC Esta técnica se utiliza cuando existe una alta dimensionalidad o correlación entre las posibles variables auxiliares (multicolinealidad).
# MAGIC
# MAGIC * **Procedimiento:** Se transforman las variables originales en un conjunto menor de variables no correlacionadas (componentes). (Mendoza y Zea 2019)
# MAGIC
# MAGIC * **Uso práctico:** Se seleccionan las coordenadas de los primeros componentes que capturan la mayor variabilidad (ej. 80%) y que presentan alta correlación con el indicador de desempleo o ingreso (Mendoza y Zea 2019)(Tellez 2020). Esto permite aprovechar la información de muchas variables sin saturar el modelo Fay-Herriot.
# MAGIC
# MAGIC
# MAGIC **3. Algoritmos de Aprendizaje Automático (Random Forests)**
# MAGIC
# MAGIC Se menciona como una técnica moderna para identificar el "poder predictivo" antes de ajustar el modelo final.
# MAGIC
# MAGIC * **Procedimiento:** El algoritmo de Random Forests clasifica las covariables según su importancia en el incremento relativo del error cuadrático medio (MSE) (Chile 2024).
# MAGIC
# MAGIC * **Uso práctico:** Ayuda a discriminar cuáles variables tienen una relación más fuerte con la variable objetivo en entornos de datos complejos, antes de proceder al modelamiento paramétrico (Chile 2024).
# MAGIC
# MAGIC **4. Selección Basada en Coherencia Temática y Literatura**
# MAGIC
# MAGIC Los documentos enfatizan que la selección no debe ser puramente estadística.
# MAGIC
# MAGIC * **Procedimiento:** Se eligen variables que tengan una relación conceptual establecida con el desempleo (ej. educación, infraestructura, dinámica económica) y se verifica que el signo del coeficiente sea el esperado (Chile 2024), (Mendoza y Zea 2019) y (Montoya 2019).
# MAGIC
# MAGIC * **Variables comunes:** Se suelen incluir tasas de ocupación, niveles educativos (primaria, secundaria, universitaria), índices de necesidades básicas insatisfechas (NBI), y registros administrativos de servicios públicos o seguridad (Mendoza y Zea 2019), (Montoya 2019) y (Zea y Ortiz 2019).
# MAGIC
# MAGIC
# MAGIC **Tratamiento y Transformación de las Covariables**
# MAGIC
# MAGIC Una vez seleccionadas, las variables se someten a procesos para cumplir con los supuestos del modelo:
# MAGIC
# MAGIC * **Transformaciones:** Se aplica el logaritmo neperiano para variables de ingresos o tasas asimétricas, y la transformación arcoseno para proporciones, con el fin de estabilizar la varianza y aproximar la normalidad (Chile 2024), (Chile 2016) y (DANE metodologia-estimaciones-pobreza-alimentaria-fies-modelo-sae-2022-y-2024).
# MAGIC
# MAGIC * **Variables Dummy:** Se utilizan variables indicadoras para controlar efectos de áreas mayores (regiones o departamentos) o para gestionar valores atípicos (outliers) que podrían sesgar la estimación. (Chile 2024) y (DANE metodologia-estimaciones-pobreza-alimentaria-fies-modelo-sae-2022-y-2024)
# MAGIC
# MAGIC * **Validación de multicolinealidad:** Se descartan variables con correlaciones extremadamente altas entre sí (ej. > 90%) para evitar errores en la estimación de los coeficientes (Coley y Tellez (2024) y Ortiz y Muñoz (2017).
# MAGIC
# MAGIC En resumen, la práctica recomendada consiste en integrar un análisis exploratorio previo (ACP o correlaciones), aplicar un algoritmo de selección (Stepwise/AIC) y validar la elección final mediante el juicio temático y pruebas de diagnóstico del modelo (análisis de residuales y distancia de Cook)

# COMMAND ----------

# MAGIC %md
# MAGIC **Metodologia Seleccionada**
# MAGIC
# MAGIC * **Paso 1** - Limpieza de los datos (quitar variables con datos faltantes) y aquellas que presentan varianza cero.
# MAGIC * **Paso 2** - Seleccionar las variables con mayor correlación directa con la variable objetivo (máximo 10 ~ 15 o aquellas que pasen el umbral definido) 
# MAGIC                
# MAGIC     * **Nota:** se deja el codigo para las 2 formas (Top N o umbrar de correlacion absoluta, pero se debe correr solo 1) 
# MAGIC * **Paso 3** - Hacerles a esas variables un análisis descriptivo previo - Sera posterior porque lo hará Samuel
# MAGIC * **Paso 4** - *Opcion A:* Se dejan las variables "ganadoras" y se aplica PCA a esas variables u *Opcion B* tambien se deja el top N variables y al resto se les aplica PCA
# MAGIC
# MAGIC     * **Nota:** se deja el codigo para las 2 opciones pero en este caso se crea una tabla para el resultado de cada opcion
# MAGIC
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC **Paso 1.1** - Limpieza de los datos (quitar variables con datos faltantes)

# COMMAND ----------

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

# MAGIC
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

# MAGIC %md
# MAGIC * **Paso 2** - Seleccionar las variables con mayor correlación directa con la variable objetivo (TOP N - máximo 10 ~ 15, aquellas que pasen el umbral definido)
# MAGIC
# MAGIC **Nota:** se deja el codigo para seleccionar el Top N de variables con mayor correlacion (absoluta) y tambien el codigo para encontrar las variables que superen un umbral de correlacion (absoluta definido). en ultimas se debe correr solo 1 de los 2

# COMMAND ----------

# =========================================================================
# METODOLOGÍA ALTERNATIVA - PASO 2: SELECCIÓN POR CORRELACIÓN DIRECTA SEGUN "TOP N"
# =========================================================================

# 1. Extraer la variable objetivo directamente del DataFrame original de metadatos (df)
y = df['TASA_DESEMPLEO_PCT'].values

# 2. Tus covariables candidatas son las 523 variables que sobrevivieron a la varianza
X_candidatas = df_final_etapa1_2.copy()

# 3. Calcular la correlación de Pearson para cada variable limpia con la tasa de desempleo
dict_correlaciones = {}
for col in X_candidatas.columns:
    dict_correlaciones[col] = X_candidatas[col].corr(df['TASA_DESEMPLEO_PCT'])

# 4. Convertir a DataFrame para ordenar por la fuerza de la relación (valor absoluto)
df_corr_analisis = pd.DataFrame.from_dict(dict_correlaciones, orient='index', columns=['Correlacion_Real'])
df_corr_analisis['Correlacion_Abs'] = df_corr_analisis['Correlacion_Real'].abs()

# 5. Ordenar de mayor a menor impacto absoluto
df_corr_ordenado = df_corr_analisis.sort_values(by='Correlacion_Abs', ascending=False)

# 6. Definir el número máximo de variables deseadas (Top 12)
n_ganadoras = 12
variables_ganadoras = df_corr_ordenado.index[:n_ganadoras].tolist()

# =========================================================================
# IMPRESIÓN DE RESULTADOS Y TRADUCCIÓN CON DICCIONARIO
# =========================================================================

print(f"=== PASO 2 CONCLUIDO ===")
print(f"Se evaluaron {X_candidatas.shape[1]} variables limpias de la Etapa 1.2.")
print(f"Se seleccionaron las {n_ganadoras} variables con mayor correlación absoluta con el Desempleo.\n")

# Cargar diccionario para mostrar los nombres reales en el reporte de Databricks
df_spark = spark.read.table("`tesis`.`dim`.dim_indicadores")
df_diccionario = df_spark.toPandas()

df_diccionario['CODIGO_INDICADOR'] = df_diccionario['CODIGO_INDICADOR'].astype(str)

# Filtrar e imprimir el TOP de ganadoras con su nombre oficial
print("=== TOP VARIABLES GANADORAS POR CORRELACIÓN DIRECTA ===")
reporte_ganadoras = []
for idx, col_codigo in enumerate(variables_ganadoras, 1):
    # Buscar correspondencia en el diccionario de TerriData
    coincidencia = df_diccionario[df_diccionario['CODIGO_INDICADOR'] == col_codigo]
    nombre_real = coincidencia['INDICADOR'].values[0] if not coincidencia.empty else "No encontrado en diccionario"
    dimension = coincidencia['DIMENSION'].values[0] if not coincidencia.empty else "N/A"
    
    corr_w = df_corr_ordenado.loc[col_codigo, 'Correlacion_Real']
    corr_a = df_corr_ordenado.loc[col_codigo, 'Correlacion_Abs']
    
    reporte_ganadoras.append({
        'Puesto': idx,
        'Código': col_codigo,
        'Dimensión': dimension,
        'Nombre Indicador': nombre_real,
        'Corr. Real': round(corr_w, 4),
        'Corr. Abs': round(corr_a, 4)
    })

df_reporte_paso2 = pd.DataFrame(reporte_ganadoras)

# COMMAND ----------

df_reporte_paso2 = pd.DataFrame(reporte_ganadoras)

# En lugar de usar print(), usamos la función nativa display() de Databricks
display(df_reporte_paso2)

# COMMAND ----------

# MAGIC %md
# MAGIC **Nota** Codigo para hacer lo mismo del paso anterior pero seleccionando las variables a partir de un umbrarl de correlacion definido.

# COMMAND ----------

# =========================================================================
# METODOLOGÍA ALTERNATIVA - PASO 2: SELECCIÓN POR UMBRAL DE CORRELACIÓN SEGUN UMBRAL DEFINIDO
# =========================================================================

# 1. Extraer la variable objetivo (y)
y = df['TASA_DESEMPLEO_PCT'].values

# 2. Tus covariables candidatas
X_candidatas = df_final_etapa1_2.copy()

# 3. Calcular la correlación de Pearson para cada variable limpia con el desempleo
dict_correlaciones = {}
for col in X_candidatas.columns:
    dict_correlaciones[col] = X_candidatas[col].corr(df['TASA_DESEMPLEO_PCT'])

# 4. Convertir a DataFrame para análisis
df_corr_analisis = pd.DataFrame.from_dict(dict_correlaciones, orient='index', columns=['Correlacion_Real'])
df_corr_analisis['Correlacion_Abs'] = df_corr_analisis['Correlacion_Real'].abs()

# =========================================================================
# FILTRADO POR UMBRAL DEFINIDO
# =========================================================================
# MODIFICACIÓN: Definir el umbral mínimo de correlación absoluta (Ej: 0.40)
umbral_definido = 0.40

# Filtrar las filas que superen el umbral y ordenar de mayor a menor fuerza
df_corr_filtrado = df_corr_analisis[df_corr_analisis['Correlacion_Abs'] >= umbral_definido]
df_corr_ordenado = df_corr_filtrado.sort_values(by='Correlacion_Abs', ascending=False)

# Extraer la lista de variables ganadoras que cumplieron la condición
variables_ganadoras = df_corr_ordenado.index.tolist()

# =========================================================================
# IMPRESIÓN DE RESULTADOS Y TRADUCCIÓN CON DICCIONARIO
# =========================================================================

print(f"=== PASO 2 CONCLUIDO (FILTRADO POR UMBRAL) ===")
print(f"Se evaluaron {X_candidatas.shape[1]} variables limpias.")
print(f"Variables que superaron el umbral de |r| >= {umbral_definido}: {len(variables_ganadoras)}\n")

# Cargar diccionario de TerriData
df_spark = spark.read.table("`tesis`.`dim`.dim_indicadores")
df_diccionario = df_spark.toPandas()

df_diccionario['CODIGO_INDICADOR'] = df_diccionario['CODIGO_INDICADOR'].astype(str)

# Construir el reporte conceptual
reporte_ganadoras = []
for idx, col_codigo in enumerate(variables_ganadoras, 1):
    coincidencia = df_diccionario[df_diccionario['CODIGO_INDICADOR'] == col_codigo]
    nombre_real = coincidencia['INDICADOR'].values[0] if not coincidencia.empty else "No encontrado en diccionario"
    dimension = coincidencia['DIMENSION'].values[0] if not coincidencia.empty else "N/A"
    
    corr_w = df_corr_ordenado.loc[col_codigo, 'Correlacion_Real']
    corr_a = df_corr_ordenado.loc[col_codigo, 'Correlacion_Abs']
    
    reporte_ganadoras.append({
        'Puesto': idx,
        'Código': col_codigo,
        'Dimensión': dimension,
        'Nombre Indicador': nombre_real,
        'Corr. Real': round(corr_w, 4),
        'Corr. Abs': round(corr_a, 4)
    })

df_reporte_paso2 = pd.DataFrame(reporte_ganadoras)

# Visualización interactiva en Databricks
display(df_reporte_paso2)

# COMMAND ----------

# MAGIC %md
# MAGIC * **Paso 3** - Hacerles a esas un análisis descriptivo previo
# MAGIC
# MAGIC Espacio para dejar todo el analisis descriptivo previo de las variables seleccionadas por correlacion, ya sea estableciendo un TOP N o por el umbrar de correlacion definido 

# COMMAND ----------

# MAGIC %md
# MAGIC * **Paso 4** - Se dejan las variables "ganadoras" y se les aplica PCA a esas variables o tambien se dejan esas 10 ~ 15 variables y al resto se les aplica PCA 
# MAGIC
# MAGIC **Opción A** PCA solo a a las varaibles ganadoras segun metodo utilizado (TOP N o umbral de correlaciondefinido)

# COMMAND ----------

# =========================================================================
# METODOLOGÍA ALTERNATIVA - PASO 3: OPCIÓN A (PCA A LAS VARIABLES GANADORAS)
# =========================================================================

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# 1. Verificar que existan variables ganadoras del paso anterior
if 'variables_ganadoras' not in locals() or len(variables_ganadoras) == 0:
    print("ALERTA: Primero debes ejecutar la celda del Paso 2 para identificar las variables ganadoras.")
else:
    # 2. Aislar la matriz de características (X) únicamente con las variables que superaron el umbral
    X_ganadoras_raw = df_final_etapa1_2[variables_ganadoras].values
    
    # 3. Estandarizar los datos (Media = 0, Varianza = 1)
    # Este paso es crucial porque las variables de TerriData vienen en diferentes escalas (tasas, porcentajes, recuentos)
    scaler_a = StandardScaler()
    X_ganadoras_scaled = scaler_a.fit_transform(X_ganadoras_raw)
    
    # 4. Ajustar el PCA completo inicial para evaluar la varianza de las ganadoras
    pca_inicial_a = PCA()
    pca_inicial_a.fit(X_ganadoras_scaled)
    
    # 5. Calcular la varianza acumulada para decidir el número óptimo de componentes
    varianza_acumulada = np.cumsum(pca_inicial_a.explained_variance_ratio_)
    
    # Definimos institucionalmente retener el 80% de la información (0.80)
    umbral_varianza_pca = 0.80
    n_componentes_optimos = np.argmax(varianza_acumulada >= umbral_varianza_pca) + 1
    
    # 6. Entrenar el PCA definitivo con el número de componentes optimizado
    pca_definitivo_a = PCA(n_components=n_componentes_optimos)
    componentes_extraidos = pca_definitivo_a.fit_transform(X_ganadoras_scaled)
    
    # 7. Crear el nuevo DataFrame con los componentes comprimidos
    # Conservamos el índice original (departamentos) para poder unirlo después a la tasa de desempleo
    nombres_nuevos_componentes = [f"COMP_GANADORAS_{i+1}" for i in range(n_componentes_optimos)]
    df_variables_pca_opcion_a = pd.DataFrame(
        componentes_extraidos, 
        columns=nombres_nuevos_componentes,
        index=df_final_etapa1_2.index
    )
    
    # =========================================================================
    # REPORTE DE CONVERGENCIA Y REDUCCIÓN DE DIMENSIONALIDAD
    # =========================================================================
    print("=== PASO 3: OPCIÓN A CONCLUIDO CON ÉXITO ===")
    print(f"Número de variables en bruto recibidas del Paso 2: {len(variables_ganadoras)}")
    print(f"Número de componentes sintéticos generados: {n_componentes_optimos}")
    print(f"Porcentaje de información (varianza) total preservada: {round(varianza_acumulada[n_componentes_optimos-1] * 100, 2)}%\n")
    
    print("=== DISTRIBUCIÓN DE LA VARIANZA POR COMPONENTE ===")
    for i, var_ratio in enumerate(pca_definitivo_a.explained_variance_ratio_, 1):
        print(f"Componente {i}: Explica el {round(var_ratio * 100, 2)}% de la varianza (Acumulado: {round(varianza_acumulada[i-1] * 100, 2)}%)")
        
    print("\n" + "="*70)
    print("NUEVO DATASET DISPONIBLE PARA MODELAR: 'df_variables_pca_opcion_a'")
    print(f"Dimensiones actuales: {df_variables_pca_opcion_a.shape[0]} filas (departamentos) x {df_variables_pca_opcion_a.shape[1]} columnas.")
    print("="*70)
    
    # Mostrar las primeras filas de la nueva matriz compacta en Databricks
    display(df_variables_pca_opcion_a.head(10))

# COMMAND ----------

# MAGIC %pip install statsmodels

# COMMAND ----------

# =========================================================================
# EVALUACIÓN DEL MODELO FINAL - METODOLOGÍA ALTERNATIVA (OPCIÓN A)
# =========================================================================
import statsmodels.api as sm

# 1. Asegurar que agregamos la constante (intercepto) a nuestros dos componentes
X_modelo_a = sm.add_constant(df_variables_pca_opcion_a)

# 2. Correr la regresión lineal frente a la Tasa de Desempleo
modelo_final_opcion_a = sm.OLS(y, X_modelo_a).fit()

# 3. Imprimir el resumen estadístico
print(modelo_final_opcion_a.summary())

# COMMAND ----------

# =========================================================================
# GENERACIÓN DE TABLA RESUMEN DE CARGAS (LOADINGS) - OPCIÓN A
# =========================================================================

# 1. Obtener la matriz de componentes (loadings) del PCA entrenado
# La matriz tiene dimensiones: (n_componentes, n_variables_originales)
loadings_matriz = pca_definitivo_a.components_

# 2. Cargar los nombres reales desde el diccionario de TerriData
df_spark = spark.read.table("`tesis`.`dim`.dim_indicadores")
df_diccionario = df_spark.toPandas()

df_diccionario['CODIGO_INDICADOR'] = df_diccionario['CODIGO_INDICADOR'].astype(str)

# 3. Construir la lista de nombres e indicadores para las variables ganadoras
nombres_variables = []
dimensiones_variables = []
for c in variables_ganadoras:
    coincidencia = df_diccionario[df_diccionario['CODIGO_INDICADOR'] == c]
    nombres_variables.append(coincidencia['INDICADOR'].values[0] if not coincidencia.empty else "No encontrado")
    dimensiones_variables.append(coincidencia['DIMENSION'].values[0] if not coincidencia.empty else "N/A")

# 4. Crear el DataFrame consolidado de Loadings
df_loadings_resumen = pd.DataFrame({
    'Código': variables_ganadoras,
    'Dimensión': dimensiones_variables,
    'Indicador TerriData': nombres_variables,
    'Peso Comp 1': loadings_matriz[0],   # Cargas del Componente 1
    'Peso Comp 2': loadings_matriz[1]    # Cargas del Componente 2
})

# 5. Crear columnas auxiliares de valor absoluto para facilitar el ordenamiento visual
df_loadings_resumen['Abs_Comp_1'] = df_loadings_resumen['Peso Comp 1'].abs()

# Ordenar la tabla por las variables que más impactan al Componente 1
df_loadings_resumen = df_loadings_resumen.sort_values(by='Abs_Comp_1', ascending=False)

# Eliminar las columnas absolutas para la visualización final de la tesis
df_final_tabla = df_loadings_resumen.drop(columns=['Abs_Comp_1'])

print("=== TABLA DE CARGAS FACTORIALES (LOADINGS) GENERAL ===")
print("Nota: Los valores cercanos a 1 o -1 indican un fuerte impacto en el componente.\n")

# Mostrar la tabla interactiva y estética en Databricks
display(df_final_tabla)

# COMMAND ----------

# Renombrar las columnas de df_final_tabla para evitar caracteres especiales y espacios
df_final_tabla.columns = [
    col.replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i")
       .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
       .replace("(", "").replace(")", "").replace(".", "")
       .replace(",", "").replace("-", "_").replace("/", "_")
       .replace("¿", "").replace("?", "").replace(":", "")
       .replace(";", "").replace("¡", "").replace("!", "")
       .replace("'", "").replace('"', "").replace("__", "_")
       .upper()
    for col in df_final_tabla.columns
]

# COMMAND ----------

# Convertir df_final_tabla en una tabla de Databricks SQL
df_spark_tabla = spark.createDataFrame(df_final_tabla)
df_spark_tabla.write.format("delta").mode("overwrite").saveAsTable("tesis.modelo.cargas_pca_ganadoras_opcion_a")

# COMMAND ----------

# MAGIC %md
# MAGIC * **Paso 4** - Se dejan las variables "ganadoras" y se les aplica PCA a esas variables o tambien se dejan esas 10 ~ 15 variables y al resto se les aplica PCA 
# MAGIC
# MAGIC **Opción B** - Dejar variables libres segun metodo de seleccion (TOP N o umbral de correlacion definido) y aplicar PCA al resto de la base
# MAGIC

# COMMAND ----------

# =========================================================================
# METODOLOGÍA ALTERNATIVA - PASO 4: OPCIÓN B (TOP N GANADORAS + PCA AL RESTO)
# =========================================================================

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# 1. Verificar que existan variables ganadoras del Paso 2
if 'variables_ganadoras' not in locals() or len(variables_ganadoras) == 0:
    print("ALERTA: Primero debes ejecutar la celda del Paso 2 para identificar las variables ganadoras.")
else:
    # 2. Separar la base de datos en dos bloques:
    # Bloque 1: Las variables ganadoras en bruto
    df_ganadoras_raw = df_final_etapa1_2[variables_ganadoras].copy()
    
    # Bloque 2: Todas las variables restantes (las ~511 variables que no pasaron el umbral)
    variables_restantes = [col for col in df_final_etapa1_2.columns if col not in variables_ganadoras]
    df_resto_raw = df_final_etapa1_2[variables_restantes].copy()
    
    # 3. Estandarizar ÚNICAMENTE el bloque de las variables restantes antes de aplicar el PCA
    scaler_b = StandardScaler()
    X_resto_scaled = scaler_b.fit_transform(df_resto_raw.values)
    
    # 4. Ajustar un PCA sobre el resto de la base
    # Para no saturar el modelo y mantener grados de libertad, extraeremos solo los 3 componentes principales dominantes
    n_componentes_control = 3
    pca_resto = PCA(n_components=n_componentes_control)
    componentes_resto_extraidos = pca_resto.fit_transform(X_resto_scaled)
    
    # Calcular la varianza explicada acumulada por estos componentes de control
    var_acumulada_resto = np.sum(pca_resto.explained_variance_ratio_) * 100
    
    # 5. Crear un DataFrame para los componentes del resto de la base
    nombres_componentes_resto = [f"COMP_CONTROL_RESTO_{i+1}" for i in range(n_componentes_control)]
    df_componentes_resto = pd.DataFrame(
        componentes_resto_extraidos,
        columns=nombres_componentes_resto,
        index=df_final_etapa1_2.index
    )
    
    # 6. CONSOLIDACIÓN: Unir las variables ganadoras en bruto con los componentes de control
    # Usamos reset_index() temporalmente para asegurar una fusión limpia por eje horizontal
    df_matriz_opcion_b = pd.concat([df_ganadoras_raw, df_componentes_resto], axis=1)
    
    # =========================================================================
    # REPORTE DE CONSOLIDACIÓN DE LA MATRIZ OPCIÓN B
    # =========================================================================
    print("=== PASO 3: OPCIÓN B CONCLUIDO CON ÉXITO ===")
    print(f"Variables 'Estrella' conservadas en bruto (Filtro Correlación): {df_ganadoras_raw.shape[1]}")
    print(f"Variables restantes comprimidas mediante PCA: {df_resto_raw.shape[1]}")
    print(f"Componentes de control generados a partir del resto: {n_componentes_control}")
    print(f"Varianza explicada por los {n_componentes_control} componentes del resto de la base: {round(var_acumulada_resto, 2)}%\n")
    
    print("="*70)
    print("NUEVO DATASET DISPONIBLE PARA MODELAR: 'df_matriz_opcion_b'")
    print(f"Dimensiones actuales: {df_matriz_opcion_b.shape[0]} filas (departamentos) x {df_matriz_opcion_b.shape[1]} columnas.")
    print("="*70)
    
    # Mostrar las primeras filas de la matriz combinada en Databricks
    display(df_matriz_opcion_b.head())

# COMMAND ----------

# =========================================================================
# EVALUACIÓN DEL MODELO FINAL - METODOLOGÍA ALTERNATIVA (OPCIÓN B)
# =========================================================================
import statsmodels.api as sm

# 1. Agregar la constante (intercepto) a la matriz combinada
X_modelo_b = sm.add_constant(df_matriz_opcion_b)

# 2. Correr la regresión lineal frente a la Tasa de Desempleo (y)
modelo_final_opcion_b = sm.OLS(y, X_modelo_b).fit()

# 3. Imprimir el resumen estadístico
print(modelo_final_opcion_b.summary())

# COMMAND ----------

# =========================================================================
# GENERACIÓN DE TABLA RESUMEN DE CARGAS (LOADINGS) - OPCIÓN B DEFINITIVA
# =========================================================================
import pandas as pd

# 1. Obtener las cargas factoriales a partir del objeto entrenado en tu celda anterior
loadings_resto_definitivo = pca_resto.components_

# 2. Cargar el diccionario oficial de TerriData
df_spark = spark.read.table("`tesis`.`dim`.dim_indicadores")
df_diccionario = df_spark.toPandas()
df_diccionario['CODIGO_INDICADOR'] = df_diccionario['CODIGO_INDICADOR'].astype(str)

reporte_final_opcion_b = []

# 3. PARTE I: Mapear las variables Ganadoras que dejaste en bruto
for c in variables_ganadoras:
    coincidencia = df_diccionario[df_diccionario['CODIGO_INDICADOR'] == c]
    nombre = coincidencia['INDICADOR'].values[0] if not coincidencia.empty else "No encontrado en diccionario"
    dimension = coincidencia['DIMENSION'].values[0] if not coincidencia.empty else "N/A"
    
    fila = {
        'Código': c,
        'Dimensión': dimension,
        'Indicador TerriData': nombre,
        'Tratamiento en el Modelo': 'CONSERVADA EN BRUTO (Impacto Directo)'
    }
    # Para estas variables, su peso en los componentes de control es lógicamente cero
    for j in range(n_componentes_control):
        fila[f'Peso COMP_CONTROL_RESTO_{j+1}'] = 0.0
        
    reporte_final_opcion_b.append(fila)

# 4. PARTE II: Mapear las variables Restantes que comprimió el PCA
for idx_var, c in enumerate(variables_restantes):
    coincidencia = df_diccionario[df_diccionario['CODIGO_INDICADOR'] == c]
    nombre = coincidencia['INDICADOR'].values[0] if not coincidencia.empty else "No encontrado en diccionario"
    dimension = coincidencia['DIMENSION'].values[0] if not coincidencia.empty else "N/A"
    
    fila = {
        'Código': c,
        'Dimensión': dimension,
        'Indicador TerriData': nombre,
        'Tratamiento en el Modelo': 'COMPRIMIDA EN PCA (Control Territorial)'
    }
    # Asignar la carga correspondiente de la matriz 'loadings_resto_definitivo'
    for j in range(n_componentes_control):
        fila[f'Peso COMP_CONTROL_RESTO_{j+1}'] = round(loadings_resto_definitivo[j][idx_var], 4)
        
    reporte_final_opcion_b.append(fila)

# 5. Consolidar el DataFrame
df_tabla_cargas_opcion_b = pd.DataFrame(reporte_final_opcion_b)

# 6. Ordenar para agrupar visualmente (Primero las directas, luego las comprimidas por dimensión)
df_tabla_cargas_opcion_b = df_tabla_cargas_opcion_b.sort_values(
    by=['Tratamiento en el Modelo', 'Dimensión'], 
    ascending=[True, True]
)

print(f"=== TABLA MAESTRA DE COVARIABLES - MATRIZ HÍBRIDA 'df_matriz_opcion_b' ===")
print(f"Sincronizado con {n_componentes_control} componentes fijos de control.\n")

# 7. Renderizar la tabla interactiva en Databricks
display(df_tabla_cargas_opcion_b)

# COMMAND ----------

# Renombrar las columnas de df_tabla_cargas_opcion_b para evitar caracteres especiales y espacios
df_tabla_cargas_opcion_b.columns = [
    col.replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i")
       .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
       .replace("(", "").replace(")", "").replace(".", "")
       .replace(",", "").replace("-", "_").replace("/", "_")
       .replace("¿", "").replace("?", "").replace(":", "")
       .replace(";", "").replace("¡", "").replace("!", "")
       .replace("'", "").replace('"', "").replace("__", "_")
       .upper()
    for col in df_tabla_cargas_opcion_b.columns
]

# COMMAND ----------

df_spark_tabla_b = spark.createDataFrame(df_tabla_cargas_opcion_b)
df_spark_tabla_b.write.format("delta").mode("overwrite").saveAsTable("tesis.modelo.cargas_pca_ganadoras_opcion_b_hibrida")