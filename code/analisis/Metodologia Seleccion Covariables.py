# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC **METODOLOGÍA DE SELECCIÓN DE COVARIABLES** 
# MAGIC
# MAGIC Para pasar de miles de variables a un modelo óptimo sin caer en la maldición de la dimensionalidad ni en multicolinealidad, se parte de  una estrategia fundamentada en el Análisis de Componentes Principales (PCA).
# MAGIC
# MAGIC El proceso estandarizado se compone de tres etapas consecutivas:
# MAGIC
# MAGIC **Etapa 1 - Agrupación Temática y Filtro de Varianza**
# MAGIC
# MAGIC  Antes de correr cualquier algoritmo, las referencias utilizadas (Mendoza y Zea 2019, Zea u Ortiz 2018, CEPAL 2019 y DANE) sugieren limpiar la base de datos en este caso de aproximadamente 1.500 campos bajo criterios puramente técnicos:
# MAGIC  
# MAGIC  **1.1 Eliminación por datos faltantes:** Se descartan aquellas variables de TerriData que tengan valores ausentes (NA) para los dominios de estudio, ya que el modelo Fay-Herriot exige que la información auxiliar esté completa para el 100% de las observaciones.
# MAGIC  
# MAGIC  **1.2 Filtro de Varianza Cero:** Se eliminan las variables que presentan el mismo valor (o casi el mismo) en la mayoría de los departamentos, ya que no aportan capacidad de discriminación estadística.
# MAGIC  
# MAGIC  **1.3 Bloques Adimensionales:** Las variables restantes se agrupan en dimensiones teóricas del territorio (Demografía, Educación, Economía Local, etc).
# MAGIC  
# MAGIC  **Etapa 2 - Reducción de Dimensionalidad mediante Componentes Principales (PCA)** 
# MAGIC  
# MAGIC En lugar de seleccionar variables individuales "sueltas" (lo cual generaría multicolinealidad severa porque muchas variables de TerriData miden cosas parecidas), se transforman los datos:
# MAGIC  
# MAGIC  * Se aplica PCA sobre los bloques de variables altamente correlacionadas.
# MAGIC  
# MAGIC  * El PCA toma esas cientos de variables y las condensa en un número muy reducido de variables nuevas llamadas Componentes Principales.
# MAGIC  
# MAGIC  * **Criterio de Selección:** se seleccionan únicamente los primeros componentes principales que acumulen un porcentaje significativo de la varianza total (típicamente aquellos que expliquen más del 75% o 80% de la variabilidad de los datos originales, o aplicando el criterio de Kaiser de retener componentes con Eigenvalues $> 1$).
# MAGIC  
# MAGIC  Los componentes principales son ortogonales entre sí, lo que significa que su correlación es exactamente cero. Al usar los componentes como las nuevas "covariables", se garantizas matemáticamente que el modelo Fay-Herriot no sufra de multicolinealidad, un problema que destruye la estabilidad de los coeficientes de regresión si se usaran las variables de TerriData sin transformar.
# MAGIC  
# MAGIC  **Etapa 3 - Selección Final mediante Algoritmo Stepwise y Criterio AIC** 
# MAGIC  
# MAGIC  Una vez reducido el universo de 1.500 campos a un grupo pequeño de componentes principales (por ejemplo, 5 o 6 componentes candidatos), se procede a la sintonización fina del modelo lineal del Fay-Herriot, tal como lo describe la literatura de la CEPAL (Molina, 2019) y las notas del DANE:
# MAGIC  
# MAGIC  **3.1 Algoritmo Stepwise:** Se ejecuta un procedimiento de selección por pasos (hacia adelante y hacia atrás) donde el software introduce o remueve los componentes uno a uno.
# MAGIC  
# MAGIC  **3.2 Optimización por AIC (Criterio de Información de Akaike):** El algoritmo evalúa cada combinación de componentes y selecciona el modelo final que minimice el valor del AIC. El AIC actúa premiando la bondad de ajuste del modelo con el desempleo, pero penalizando el uso excesivo de parámetros, logrando un modelo parsimonioso (sencillo y altamente eficiente).
# MAGIC
# MAGIC
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC **ETAPA 1**
# MAGIC
# MAGIC *Paso 1.1 - Eliminación por datos faltantes*

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

# MAGIC %md
# MAGIC De las 1.582 variables originales, solo 530 variables están completamente llenas (0 registros faltantes) para los 23 departamentos. Las otras 1.052 variables se descartan de inmediato porque introducen vacíos de información que desestabilizan el cálculo.

# COMMAND ----------

# MAGIC %md
# MAGIC **ETAPA 1**
# MAGIC
# MAGIC *Paso 1.2 - Filtro de Varianza Cero*

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
# MAGIC **ETAPA 1**
# MAGIC
# MAGIC *Paso 1.3 - Bloques Adimensionales*

# COMMAND ----------

# 1. Cargar el diccionario de nombres de campos
df_spark = spark.read.table("`tesis`.`dim`.dim_indicadores")

# 2. Convertir a Pandas DataFrame para facilitar la manipulación matemática de las 1.500 columnas
df_spark_diccionario = df_spark.toPandas()

# 2. Obtener la lista de las 523 variables que sobrevivieron a la Etapa 1
# df_final_etapa1_2 es el DataFrame con las 523 columnas del paso anterior
variables_filtradas = df_final_etapa1_2.columns.tolist()

# 3. Filtrar el diccionario para quedarnos SOLO con las dimensiones de nuestras 523 variables
df_mapeo = df_spark_diccionario[df_spark_diccionario['CODIGO_INDICADOR'].isin(variables_filtradas)]

# 4. Mostrar cuántas variables reales te quedaron en cada Dimensión Oficial de TerriData
print("=== DISTRIBUCIÓN DE VARIABLES POR DIMENSIÓN OFICIAL ===")
distribucion = df_mapeo['DIMENSION'].value_counts()
print(distribucion)

# COMMAND ----------

# MAGIC %md
# MAGIC **ETAPA 2**
# MAGIC
# MAGIC *PCA sobre los bloques de variables altamente correlacionadas*

# COMMAND ----------

import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# =========================================================================
# 1. PREPARACIÓN Y CRUCE DE DIMENSIONES
# =========================================================================

# Cargar el diccionario de nombres de campos
df_spark = spark.read.table("`tesis`.`dim`.dim_indicadores")

# Convertir a Pandas DataFrame para facilitar la manipulación matemática de las 1.500 columnas
df_diccionario = df_spark.toPandas()

# Obtener las 523 variables definitivas de la Etapa 1
variables_filtradas = df_final_etapa1_2.columns.tolist()

# Filtrar el diccionario para mapear solo las variables sobrevivientes
df_mapeo = df_diccionario[df_diccionario['CODIGO_INDICADOR'].isin(variables_filtradas)]

# Agrupar por dimensión para identificar los bloques de procesamiento
dimensiones_unicas = df_mapeo['DIMENSION'].dropna().unique()

# Diccionario y listas para almacenar los resultados del PCA
componentes_finales_lista = []
reporte_pca = []

print(f"Se identificaron {len(dimensiones_unicas)} dimensiones conceptuales oficiales de TerriData para procesar.\n")

# =========================================================================
# 2. PROCESAMIENTO MIGRADO POR BLOQUES (PCA LOOP)
# =========================================================================

for dim in dimensiones_unicas:
    # Aislamos los códigos de variables que pertenecen a la dimensión actual
    codigos_dim = df_mapeo[df_mapeo['DIMENSION'] == dim]['CODIGO_INDICADOR'].tolist()
    
    # Nos aseguramos de que existan en nuestro DataFrame de datos
    codigos_dim = [c for c in codigos_dim if c in df_final_etapa1_2.columns]
    
    # Omitimos dimensiones si se quedaron con menos de 2 variables para hacer PCA
    if len(codigos_dim) < 2:
        if len(codigos_dim) == 1:
            # Si solo hay una, pasa directo como variable individual sin transformar
            df_comp = pd.DataFrame(df_final_etapa1_2[codigos_dim[0]])
            df_comp.columns = [f"COMP_{dim.replace(' ', '_')[:15]}_1"]
            componentes_finales_lista.append(df_comp)
        continue
        
    # Extraemos la matriz de datos del bloque actual
    X_bloque = df_final_etapa1_2[codigos_dim].values
    
    # === PASO CRÍTICO: Estandarizar (Media 0, Varianza 1) ===
    # TerriData mezcla escalas (tasas, pesos colombianos, personas). Es obligatorio escalar.
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_bloque)
    
    # Ejecutamos el PCA calculando todos los componentes posibles del bloque
    pca = PCA()
    pca.fit(X_scaled)
    
    # Calcular los Eigenvalues (Valores propios) para aplicar el Criterio de Kaiser
    eigenvalues = pca.explained_variance_
    
    # Calcular la varianza explicada acumulada
    varianza_acumulada = np.cumsum(pca.explained_variance_ratio_)
    
    # === CRITERIO DE SELECCIÓN (DANE / MENDOZA & ZEA) ===
    # Conservamos componentes con Eigenvalue > 1, O los necesarios para superar el 80% de varianza
    n_comp_elegidos = 0
    for idx, evalue in enumerate(eigenvalues):
        n_comp_elegidos += 1
        if evalue < 1.0 or varianza_acumulada[idx] >= 0.80:
            break
            
    # Re-entrenamos el PCA ajustado únicamente al número óptimo de componentes elegidos
    pca_optimo = PCA(n_components=n_comp_elegidos)
    X_pca = pca_optimo.fit_transform(X_scaled)
    
    # Crear un DataFrame con las puntuaciones (scores) de estos nuevos componentes
    nombres_componentes = [f"COMP_{dim.replace(' ', '_')[:15]}_{i+1}" for i in range(n_comp_elegidos)]
    df_comp_dim = pd.DataFrame(X_pca, columns=nombres_componentes)
    componentes_finales_lista.append(df_comp_dim)
    
    # Almacenar métricas para el reporte académico de la tesis
    reporte_pca.append({
        'Dimensión': dim,
        'Variables Originales': len(codigos_dim),
        'Componentes Retenidos': n_comp_elegidos,
        '% Varianza Explicada Tot.': round(varianza_acumulada[n_comp_elegidos-1] * 100, 2)
    })

# =========================================================================
# 3. CONSOLIDACIÓN DE LA NUEVA BASE DE COVARIABLES
# =========================================================================

# Concatenar todos los componentes de todas las dimensiones horizontalmente
df_covariables_pca = pd.concat(componentes_finales_lista, axis=1)

# Imprimir el reporte detallado por dimensión
df_reporte = pd.DataFrame(reporte_pca)
print("=== RESUMEN TÉCNICO DEL PROCESAMIENTO PCA POR BLOQUES ===")
# print(df_reporte.to_string(index=False))
print(f"\nDimensiones finales de la matriz de componentes: {df_covariables_pca.shape}")

# COMMAND ----------

display(df_reporte)

# COMMAND ----------

# MAGIC %md
# MAGIC las 523 variables auxiliares que superaron los filtros de varianza y consistencia de información fueron agrupadas en las 17 dimensiones conceptuales preestablecidas por TerriData, en línea con el protocolo de estratificación del Departamento Administrativo Nacional de Estadística (DANE). 
# MAGIC
# MAGIC Al aplicar el Análisis de Componentes Principales (PCA) de forma independiente para cada bloque, se logró mitigar de manera absoluta el fenómeno de la multicolinealidad mediante la extracción de factores ortogonales. El algoritmo condensó el volumen masivo de información en un conjunto óptimo de 59 componentes sintéticos independientes. 
# MAGIC
# MAGIC En todas las dimensiones analizadas, los componentes retenidos lograron explicar más del 80% de la varianza total de los datos originales del territorio. Esta nueva matriz reducida de dimensiones (23 $\times$ 59) preserva la riqueza informativa multidimensional del país y provee la estabilidad matemática requerida para la fase final de sintonización del modelo de áreas pequeñas.

# COMMAND ----------

# MAGIC %md
# MAGIC **ETAPA 3**
# MAGIC
# MAGIC *Paso 3.1 - Algoritmo Stepwise*

# COMMAND ----------

# MAGIC %pip install statsmodels

# COMMAND ----------

import pandas as pd
import numpy as np
import statsmodels.api as sm

# =========================================================================
# 1. CONSOLIDACIÓN DE LA MATRIZ DE ENTRENAMIENTO
# =========================================================================

# Variable objetivo: Tasa de Desempleo
y = df['TASA_DESEMPLEO_PCT'].values

# Matriz de características: Los 59 componentes principales de la Etapa 2
X_pool = df_covariables_pca.copy()

print(f"Iniciando selección con {X_pool.shape[1]} componentes candidatos para explicar la Tasa de Desempleo.\n")

# =========================================================================
# 2. ALGORITMO STEPWISE BI-DIRECCIONAL BASADO EN AIC
# =========================================================================

def stepwise_selection_aic(X, y):
    """
    Selección de variables bi-direccional (Forward/Backward) basada en el AIC.
    Argumentos:
        X: pandas.DataFrame con las covariables candidatas.
        y: array-like con la variable objetivo.
    Retorna:
        Lista de las variables seleccionadas que minimizan el AIC.
    """
    selected_features = []
    remaining_features = list(X.columns)
    
    # Ajustamos un modelo inicial solo con el intercepto para tener un AIC base
    X_constant_base = sm.add_constant(pd.DataFrame(np.ones((len(y), 1))))
    current_score = sm.OLS(y, X_constant_base).fit().aic
    best_score = current_score
    
    print(f"AIC del modelo base (solo intercepto): {round(best_score, 2)}")
    print("-" * 60)
    
    while remaining_features:
        scores_with_candidates = []
        
        # --- FASE FORWARD: Probar agregar una nueva variable ---
        for candidate in remaining_features:
            features_to_test = selected_features + [candidate]
            X_test = sm.add_constant(X[features_to_test])
            model = sm.OLS(y, X_test).fit()
            scores_with_candidates.append((model.aic, candidate))
        
        # Ordenar para encontrar el menor AIC al agregar
        scores_with_candidates.sort()
        best_candidate_score, best_candidate = scores_with_candidates[0]
        
        # Si agregar la mejor variable mejora (reduce) el AIC, la sumamos
        if best_candidate_score < current_score:
            remaining_features.remove(best_candidate)
            selected_features.append(best_candidate)
            current_score = best_candidate_score
            print(f"Agregado: {best_candidate:<35} | Nuevo AIC: {round(current_score, 2)}")
            
            # --- FASE BACKWARD: Probar si se puede eliminar alguna de las ya seleccionadas ---
            if len(selected_features) > 1:
                while True:
                    worst_score = current_score
                    feature_to_remove = None
                    
                    for feature in selected_features:
                        features_to_test = [f for f in selected_features if f != feature]
                        X_test = sm.add_constant(X[features_to_test])
                        model = sm.OLS(y, X_test).fit()
                        
                        if model.aic < worst_score:
                            worst_score = model.aic
                            feature_to_remove = feature
                    
                    # Si eliminar una variable reduce aún más el AIC, la sacamos
                    if feature_to_remove is not None:
                        selected_features.remove(feature_to_remove)
                        remaining_features.append(feature_to_remove)
                        current_score = worst_score
                        print(f"Eliminado: {feature_to_remove:<35} | Nuevo AIC: {round(current_score, 2)}")
                    else:
                        break
        else:
            # Si ninguna variable nueva reduce el AIC del modelo actual, el algoritmo se detiene
            break
            
    return selected_features

# Ejecutar el algoritmo Stepwise
componentes_optimos = stepwise_selection_aic(X_pool, y)

# =========================================================================
# 3. RESULTADO Y RESUMEN DEL MODELO FINAL
# =========================================================================

print("\n" + "="*60)
print("=== PROCESAMIENTO CONCLUIDO CON ÉXITO ===")
print(f"Componentes óptimos seleccionados de forma parsimoniosa: {len(componentes_optimos)}")
print("Componentes:", componentes_optimos)
print("="*60 + "\n")

# Ajustar el modelo final para verificar significancia y R-cuadrado
X_final = sm.add_constant(X_pool[componentes_optimos])
modelo_final = sm.OLS(y, X_final).fit()
print(modelo_final.summary())

# COMMAND ----------

# MAGIC %md
# MAGIC Observaciones:
# MAGIC
# MAGIC * R-squared: **1.000**: El modelo explica el 100.00% del desempleo, lo cual en datos reales es imposible.
# MAGIC
# MAGIC * Adj. R-squared: **nan** y std err: **inf**: Los errores estándar dieron infinito y el R-cuadrado ajustado no se pudo calcular.
# MAGIC
# MAGIC * Df Residuals: **0**: Los grados de libertad de los residuos son exactamente cero.
# MAGIC
# MAGIC el número de parámetros a estimar **k** debe ser estrictamente menor que el número de observaciones **n**. el algoritmo Stepwise agregó 22 variables para intentar predecir 23 puntos de datos, lo que deja con 0 Grados de Libertad. Esto significa que el modelo no está "aprendiendo" una relación macroeconómica, simplemente está memorizando los datos exactos. Al no haber residuos, la varianza del error es cero y los errores estándar se vuelven matemáticamente infinitos, lo que hace que los p-valores den **nan** y el modelo sea completamente inútil para predecir a nivel municipal.
# MAGIC
# MAGIC Opciones para solucionar esto:
# MAGIC
# MAGIC * Usar el Criterio de Información de Akaike Corregido (AICc)
# MAGIC * Forzar un límite máximo de variables.

# COMMAND ----------

# MAGIC %md
# MAGIC **Criterio de Información de Akaike Corregido (AICc)**

# COMMAND ----------

import pandas as pd
import numpy as np
import statsmodels.api as sm

y = df['TASA_DESEMPLEO_PCT'].values
X_pool = df_covariables_pca.copy()

def stepwise_selection_aicc(X, y):
    selected_features = []
    remaining_features = list(X.columns)
    n = len(y) # Número de observaciones (23)
    
    # Modelo base solo con intercepto
    X_constant_base = sm.add_constant(pd.DataFrame(np.ones((n, 1))))
    model_base = sm.OLS(y, X_constant_base).fit()
    k_base = 1 # Solo intercepto
    # Calcular AICc base
    current_score = model_base.aic + (2 * k_base * (k_base + 1)) / (n - k_base - 1)
    
    print(f"AICc del modelo base (solo intercepto): {round(current_score, 2)}")
    print("-" * 60)
    
    while remaining_features:
        scores_with_candidates = []
        
        for candidate in remaining_features:
            features_to_test = selected_features + [candidate]
            X_test = sm.add_constant(X[features_to_test])
            k = X_test.shape[1] # Número de parámetros incluyendo la constante
            
            # PROTECCIÓN: Si los grados de libertad van a ser menores o iguales a 2, no evaluar para evitar división por cero
            if (n - k - 1) <= 0:
                continue
                
            model = sm.OLS(y, X_test).fit()
            # Fórmula matemática del AICc (Castigo por muestra pequeña)
            aicc = model.aic + (2 * k * (k + 1)) / (n - k - 1)
            scores_with_candidates.append((aicc, candidate))
        
        if not scores_with_candidates:
            break
            
        scores_with_candidates.sort()
        best_candidate_score, best_candidate = scores_with_candidates[0]
        
        # Si el mejor AICc es menor que el actual, agregamos la variable
        if best_candidate_score < current_score:
            remaining_features.remove(best_candidate)
            selected_features.append(best_candidate)
            current_score = best_candidate_score
            print(f"Agregado: {best_candidate:<35} | Nuevo AICc: {round(current_score, 2)}")
            
            # Fase Backward con AICc
            if len(selected_features) > 1:
                while True:
                    worst_score = current_score
                    feature_to_remove = None
                    
                    for feature in selected_features:
                        features_to_test = [f for f in selected_features if f != feature]
                        X_test = sm.add_constant(X[features_to_test])
                        k = X_test.shape[1]
                        model = sm.OLS(y, X_test).fit()
                        aicc = model.aic + (2 * k * (k + 1)) / (n - k - 1)
                        
                        if aicc < worst_score:
                            worst_score = aicc
                            feature_to_remove = feature
                    
                    if feature_to_remove is not None:
                        selected_features.remove(feature_to_remove)
                        remaining_features.append(feature_to_remove)
                        current_score = worst_score
                        print(f"Eliminado: {feature_to_remove:<35} | Nuevo AICc: {round(current_score, 2)}")
                    else:
                        break
        else:
            break
            
    return selected_features

# Ejecutar el algoritmo corregido
componentes_optimos = stepwise_selection_aicc(X_pool, y)

print("\n=== PROCESAMIENTO CONCLUIDO CON AICc ===")
print(f"Componentes óptimos parsimoniosos seleccionados: {len(componentes_optimos)}")
print("Componentes:", componentes_optimos)

# Ver el resumen final corregido con errores estándar reales
X_final = sm.add_constant(X_pool[componentes_optimos])
modelo_final = sm.OLS(y, X_final).fit()
print(modelo_final.summary())

# COMMAND ----------

# MAGIC %md
# MAGIC Para la sintonización fina del componente lineal del modelo de áreas pequeñas, se implementó el Algoritmo Stepwise Bi-direccional optimizado mediante el Criterio de Información de Akaike Corregido (AICc), siguiendo las recomendaciones metodológicas para muestras pequeñas establecidas por Hurvich y Tsai (1989) y adoptadas en la literatura de la CEPAL (Molina, 2019). El uso del AICc evitó la sobreparametrización y la consecuente pérdida de grados de libertad asociada al AIC convencional en escenarios con un número reducido de dominios agregados (n = 23).El algoritmo convergió exitosamente al seleccionar un modelo parsimonioso compuesto por 9 componentes principales ortogonales. El modelo lineal resultante exhibe un ajuste sobresaliente, logrando explicar el 90.0% de la varianza de la tasa de desempleo departamental ($R^2 \text{ ajustado} = 0.900; F = 23.08; p < 0.001$). Asimismo, todos los predictores incorporados resultaron ser significativos al 5% ($\alpha = 0.05$). Finalmente, la estructura matemática del modelo es altamente estable, registrando un Número de Condición de 2.98, lo que confirma la ausencia absoluta de problemas de multicolinealidad estructural.
# MAGIC

# COMMAND ----------

# MAGIC %md
# MAGIC **Codigo para intepretar mejor cada componente**
# MAGIC
# MAGIC *Ejemplo con el 1er Componente de educacion (COMP_Educación_4 )*

# COMMAND ----------

import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Cargar el diccionario de nombres de campos
df_spark = spark.read.table("`tesis`.`dim`.dim_indicadores")

# Convertir a Pandas DataFrame para facilitar la manipulación matemática de las 1.500 columnas
df_diccionario = df_spark.toPandas()

df_diccionario['CODIGO_INDICADOR'] = df_diccionario['CODIGO_INDICADOR'].astype(str)

# =========================================================================
# CONFIGURACIÓN DE LA DIMENSIÓN A ANALIZAR
# =========================================================================
# Para revisar COMP_Educación_4, configuramos la dimensión "Educación" y el componente 4 (Índice 3 en Python)
dimension_interes = "Educación"
numero_componente = 4  
indice_componente = numero_componente - 1 

# 2. Aislar y estandardizar las variables exclusivas del bloque de Educación
codigos_edu = df_diccionario[df_diccionario['DIMENSION'] == dimension_interes]['CODIGO_INDICADOR'].tolist()
codigos_edu = [c for c in codigos_edu if c in df_final_etapa1_2.columns]

X_edu = df_final_etapa1_2[codigos_edu].values
scaler = StandardScaler()
X_edu_scaled = scaler.fit_transform(X_edu)

# 3. Entrenar el PCA específico para esta dimensión
pca_edu = PCA()
pca_edu.fit(X_edu_scaled)

# 4. Extraer los pesos (loadings) del componente número 4
loadings_componente = pca_edu.components_[indice_componente]

# 5. Obtener los nombres reales en español de cada código de indicador
nombres_variables = [
    df_diccionario[df_diccionario['CODIGO_INDICADOR'] == c]['INDICADOR'].values[0] 
    for c in codigos_edu
]

# 6. Consolidar el DataFrame de interpretación
df_interpretacion = pd.DataFrame({
    'Código Indicador': codigos_edu,
    'Nombre del Indicador (TerriData)': nombres_variables,
    'Peso Matemático (Loading)': loadings_componente
})

# Añadir valor absoluto para ordenar las variables por su verdadera fuerza de impacto
df_interpretacion['Impacto_Absoluto'] = df_interpretacion['Peso Matemático (Loading)'].abs()
df_interpretacion = df_interpretacion.sort_values(by='Impacto_Absoluto', ascending=False)

print(f"=== TOP VARIABLES QUE COMPONEN A: COMP_{dimension_interes}_{numero_componente} ===")
# print(df_interpretacion[['Nombre del Indicador (TerriData)', 'Peso Matemático (Loading)']].head(10).to_string(index=False))

# COMMAND ----------

display(df_interpretacion.head(10))

# COMMAND ----------

# MAGIC %md
# MAGIC  Para la selección de la información auxiliar proveniente de TerriData, se implementó una estrategia metodológica de reducción de dimensiones y selección de características validada en la literatura nacional de estimación de desempleo en áreas pequeñas (Zea & Ortiz, 2018; Mendoza & Zea, 2019). Debido a la alta dimensionalidad de la base inicial (~1.500 campos), en primera instancia se descartaron las variables con varianza cercana a cero o datos faltantes. Posteriormente, para mitigar los problemas de multicolinealidad inherentes a los registros administrativos, se realizó un Análisis de Componentes Principales (PCA) para extraer factores ortogonales que retuvieran la mayor variabilidad del territorio. Finalmente, siguiendo las recomendaciones de la CEPAL (Molina, 2019), se aplicó un algoritmo de selección stepwise guiado por el Criterio de Información de Akaike (AIC), garantizando la obtención de un conjunto óptimo y parsimonioso de covariables para el posterior entrenamiento del modelo Fay-Herriot.

# COMMAND ----------

# MAGIC %md
# MAGIC

# COMMAND ----------

# DBTITLE 1,Evaluación Metodológica
# MAGIC %md
# MAGIC ## Evaluación Crítica de la Metodología
# MAGIC
# MAGIC ### ✅ Fortalezas
# MAGIC
# MAGIC **1. Fundamentación Académica Sólida**
# MAGIC * Metodología respaldada por referencias de alto nivel: DANE, CEPAL, Mendoza & Zea (2019), Zea & Ortiz (2018)
# MAGIC * Uso apropiado del Análisis de Componentes Principales (PCA) como técnica estándar en Small Area Estimation
# MAGIC * Aplicación correcta del Criterio de Kaiser (eigenvalues > 1) para selección de componentes
# MAGIC
# MAGIC **2. Manejo Riguroso de Multicolinealidad**
# MAGIC * El PCA genera componentes ortogonales, eliminando completamente la correlación entre predictores
# MAGIC * Número de condición = 2.98 confirma ausencia de multicolinealidad estructural
# MAGIC * Estrategia coherente con la naturaleza de registros administrativos (variables altamente correlacionadas)
# MAGIC
# MAGIC **3. Corrección Metodológica Ejemplar**
# MAGIC * Detectaron el problema de sobreparametrización con AIC (22 variables para 23 observaciones)
# MAGIC * Auto-corrigieron implementando AICc (Hurvich & Tsai, 1989) diseñado específicamente para muestras pequeñas
# MAGIC * Demuestran comprensión profunda de la teoría estadística subyacente
# MAGIC
# MAGIC **4. Documentación Excepcional**
# MAGIC * Código altamente comentado con explicaciones matemáticas en cada paso
# MAGIC * Celdas markdown que contextualizan decisiones metodológicas
# MAGIC * Trazabilidad completa: de 1,582 variables → 530 (sin NAs) → 523 (con varianza) → 59 (PCA) → 9 (stepwise)
# MAGIC
# MAGIC **5. Estandarización Pre-PCA**
# MAGIC * Reconocen explícitamente que TerriData mezcla escalas (tasas, pesos colombianos, personas)
# MAGIC * Aplican StandardScaler obligatoriamente antes del PCA (práctica correcta)
# MAGIC
# MAGIC **6. Puente entre Estadística Clásica y Ciencia de Datos**
# MAGIC * PCA es reconocido como técnica de reducción de dimensionalidad en ML
# MAGIC * La estructura metodológica (limpieza → feature engineering → selección) sigue el pipeline estándar de ML
# MAGIC * Facilita la defensa en contextos académicos de ciencia de datos
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### ⚠️ Debilidades Críticas
# MAGIC
# MAGIC **1. Muestra Extremadamente Pequeña (n=23)**
# MAGIC * **Ratio parámetros/observaciones peligroso**: 9 predictores + intercepto = 10 parámetros para 23 datos
# MAGIC * Regla empírica en estadística: mínimo 10-15 observaciones por predictor → deberían tener 100-150 departamentos
# MAGIC * Grados de libertad residuales = 23 - 10 = 13 (muy bajo para inferencia robusta)
# MAGIC
# MAGIC **2. Alto Riesgo de Overfitting**
# MAGIC * **R² ajustado = 0.900 es sospechosamente alto** para datos socio-económicos reales
# MAGIC * Con tan pocos grados de libertad, el modelo puede estar memorizando ruido en lugar de capturar relaciones verdaderas
# MAGIC * En machine learning, este nivel de ajuste sin validación es señal de alarma
# MAGIC
# MAGIC **3. Ausencia Total de Validación**
# MAGIC * **No hay validación cruzada**: LOOCV (Leave-One-Out Cross-Validation) es esencial con n=23
# MAGIC * **No hay métricas de error de predicción**: RMSE, MAE, MAPE no fueron calculados
# MAGIC * **No verificaron supuestos de regresión**: normalidad de residuos, homocedasticidad, autocorrelación
# MAGIC * Sin validación, no hay garantía de que el modelo generalice a municipios
# MAGIC
# MAGIC **4. Limitada Interpretabilidad de Componentes PCA**
# MAGIC * Los componentes principales son combinaciones lineales abstractas difíciles de explicar causalmente
# MAGIC * Aunque intentan interpretar COMP_Educación_4 (positivo), cada componente mezcla múltiples indicadores con pesos variables
# MAGIC * Para stakeholders (ej. formuladores de política pública), "aumentar COMP_Salud_6" es menos accionable que "aumentar cobertura hospitalaria"
# MAGIC
# MAGIC **5. Decisiones Metodológicas Cuestionables**
# MAGIC * **PCA por bloques separados**: Al procesar cada dimensión independientemente, pierden información de correlaciones inter-dimensionales (ej. Educación-Salud-Economía)
# MAGIC * **Stepwise es inestable**: Conocido en literatura estadística por producir modelos diferentes con pequeños cambios en los datos
# MAGIC * **Criterio de Kaiser puede ser conservador**: Análisis paralelo (Horn, 1965) es más robusto que eigenvalue > 1
# MAGIC
# MAGIC **6. Falta de Análisis de Sensibilidad**
# MAGIC * ¿Qué pasa si se elimina un departamento? ¿El modelo selecciona las mismas variables?
# MAGIC * ¿Los coeficientes son estables o varían drásticamente?
# MAGIC * Sin bootstrap ni perturbación de datos, no conocen la incertidumbre de la selección
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### 🔧 Recomendaciones Urgentes
# MAGIC
# MAGIC **Prioridad 1: Validación Cruzada LOOCV**
# MAGIC ```python
# MAGIC # Para cada departamento i:
# MAGIC #   1. Entrenar modelo con los otros 22 departamentos
# MAGIC #   2. Predecir tasa de desempleo del departamento i
# MAGIC #   3. Calcular error = |predicho - real|
# MAGIC # Reportar: RMSE_CV, MAE_CV, R²_CV
# MAGIC ```
# MAGIC **Justificación para defensa de tesis**: "Aunque Fay-Herriot es un modelo de áreas pequeñas, la validación cruzada es estándar en ML y demuestra capacidad de generalización."
# MAGIC
# MAGIC **Prioridad 2: Diagnóstico de Residuos**
# MAGIC ```python
# MAGIC import scipy.stats as stats
# MAGIC import matplotlib.pyplot as plt
# MAGIC
# MAGIC # 1. Q-Q plot para normalidad
# MAGIC stats.probplot(modelo_final.resid, dist="norm", plot=plt)
# MAGIC
# MAGIC # 2. Test de Shapiro-Wilk
# MAGIC stats.shapiro(modelo_final.resid)
# MAGIC
# MAGIC # 3. Test de Breusch-Pagan para homocedasticidad
# MAGIC import statsmodels.stats.diagnostic as smd
# MAGIC smd.het_breuschpagan(modelo_final.resid, X_final)
# MAGIC
# MAGIC # 4. VIF para multicolinealidad residual
# MAGIC from statsmodels.stats.outliers_influence import variance_inflation_factor
# MAGIC ```
# MAGIC
# MAGIC **Prioridad 3: Bootstrap de Coeficientes**
# MAGIC ```python
# MAGIC # 1.000 iteraciones de bootstrap
# MAGIC # En cada iteración: resamplear 23 departamentos con reemplazo
# MAGIC # Verificar estabilidad de las 9 variables seleccionadas
# MAGIC # ¿Aparecen las mismas en >80% de las iteraciones?
# MAGIC ```
# MAGIC
# MAGIC **Prioridad 4: Comparar con Métodos Alternativos**
# MAGIC * **Ridge Regression**: Penaliza magnitud de coeficientes sin eliminar variables
# MAGIC * **Lasso Regression**: Selección automática de variables + regularización
# MAGIC * **Elastic Net**: Combina Ridge + Lasso
# MAGIC * Comparar AICc, BIC, y RMSE_CV entre métodos
# MAGIC
# MAGIC **Prioridad 5: Mejorar Interpretabilidad**
# MAGIC * Para cada componente seleccionado, crear tabla con las 3-5 variables originales de mayor peso (loading)
# MAGIC * Generar "perfiles conceptuales": ej. COMP_Educación_4 = "Transición educativa + calidad SABER"
# MAGIC * Visualizar heatmap de correlación entre los 9 componentes y las variables originales más importantes
# MAGIC
# MAGIC **Prioridad 6: Análisis de Sensibilidad**
# MAGIC ```python
# MAGIC # Caso 1: Eliminar departamentos atípicos (ej. Bogotá, Chocó)
# MAGIC # Caso 2: Variar umbral de varianza (0.00001 → 0.0001)
# MAGIC # Caso 3: Cambiar umbral PCA (80% → 85% varianza explicada)
# MAGIC # ¿El modelo final es robusto a estas perturbaciones?
# MAGIC ```
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### 📊 Pregunta Clave: ¿El Modelo Predice o Solo Selecciona?
# MAGIC
# MAGIC **Respuesta**: Actualmente **solo selecciona variables** mediante ajuste in-sample (los mismos 23 departamentos). El modelo NO ha demostrado capacidad predictiva porque:
# MAGIC * No se probó en datos nunca vistos (out-of-sample)
# MAGIC * No hay métricas de error de predicción
# MAGIC * R²=0.900 mide ajuste retrospectivo, no poder predictivo
# MAGIC
# MAGIC **Para convertirlo en modelo predictivo:**
# MAGIC 1. Validación cruzada LOOCV → Obtener RMSE predictivo
# MAGIC 2. Si el RMSE_CV es aceptable, usar el modelo para predecir tasas de desempleo municipales (el objetivo final de Fay-Herriot)
# MAGIC 3. Comparar predicciones municipales con estimaciones directas cuando estén disponibles
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### 🎯 Fortaleza Principal para Defensa de Tesis
# MAGIC
# MAGIC Esta metodología es **absolutamente defendible** si se complementa con validación. El uso de PCA + stepwise es estándar en SAE y tiene respaldo académico sólido. La corrección de AIC → AICc demuestra rigor metodológico. Con las recomendaciones implementadas, tendrán un trabajo robusto que conecta estadística clásica (Fay-Herriot) con ciencia de datos moderna (validación cruzada, métricas de ML).

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC **Resolviendo recomentdaciones**
# MAGIC
# MAGIC **Prioridad 1 - Validación Cruzada LOOCV** 
# MAGIC
# MAGIC Se sugiere LOOCV (Leave-One-Out Cross-Validation) porque estamos trabajando con una muestra pequeña (23 observaciones). Perfecta para demostrar "capacidad de generalización".
# MAGIC
# MAGIC Se debe tener en cuenta una distinción teórica, donde el Stepwise por AICc se corrio anteriormente, ya busca la generalización penalizando el exceso de variables. Desde una mirada de añguien experto en Machine Learning, es ideal e indispnesable ver el LOOCV. Desde una mirada de un estadístico de muestreo, podria decir que en Fay-Herriot lo que importa es la estimación del error cuadrático medio (MSE) analítico del modelo de áreas pequeñas, no la predicción lineal pura por fuera de la muestra.

# COMMAND ----------

from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import mean_squared_error, mean_absolute_error

loo = LeaveOneOut()
y_reales = []
y_predichos = []

# Iterar dejando un departamento por fuera cada vez
for train_index, test_index in loo.split(X_final):
    X_train, X_test = X_final.iloc[train_index], X_final.iloc[test_index]
    y_train, y_test = y[train_index], y[test_index]
    
    # Entrenar con los 22 departamentos sobrevivientes
    model_loo = sm.OLS(y_train, X_train).fit()
    
    # Predicción sobre el departamento excluido
    pred = model_loo.predict(X_test)
    
    y_reales.append(y_test[0])
    y_predichos.append(pred.values[0])

# Calcular métricas de validación cruzada
rmse_cv = np.sqrt(mean_squared_error(y_reales, y_predichos))
mae_cv = mean_absolute_error(y_reales, y_predichos)

print("=== MÉTRICAS DE VALIDACIÓN CRUZADA (LOOCV) ===")
print(f"RMSE CV (Error cuadrático medio): {round(rmse_cv, 4)}")
print(f"MAE CV (Error absoluto medio): {round(mae_cv, 4)}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Prioridad 2 - Diagnóstico de Residuos**
# MAGIC
# MAGIC En econometría y modelos Fay-Herriot, los residuos tienen que ser normales y homocedásticos (varianza constante). Si los residuos no son normales, los p-valores de los 9 componentes no son válidos y el modelo se cae conceptualmente.

# COMMAND ----------

import scipy.stats as stats
import matplotlib.pyplot as plt
import statsmodels.stats.diagnostic as smd
from statsmodels.stats.outliers_influence import variance_inflation_factor

print("=== DIAGNÓSTICO DE RESIDUOS DEL MODELO FINAL ===")

# 1. Test de Shapiro-Wilk (Normalidad de residuos)
shapiro_stat, shapiro_p = stats.shapiro(modelo_final.resid)
print(f"Test de Shapiro-Wilk: Estadística={round(shapiro_stat,4)}, p-valor={round(shapiro_p,4)}")
if shapiro_p > 0.05:
    print("-> RESULTADO: Los residuos son NORMALES (Excelente, se cumple el supuesto).")
else:
    print("-> ALERTA: Los residuos NO son normales.")

# 2. Test de Breusch-Pagan (Homocedasticidad)
bp_test = smd.het_breuschpagan(modelo_final.resid, X_final)
print(f"Test de Breusch-Pagan (p-valor): {round(bp_test[1], 4)}")
if bp_test[1] > 0.05:
    print("-> RESULTADO: Los residuos son HOMOCEDÁSTICOS (Varianza constante, perfecto).")
else:
    print("-> ALERTA: Hay heterocedasticidad.")

# 3. Cálculo de VIF (Verificar si realmente eliminamos la multicolinealidad)
print("\n=== FACTOR DE INFLACIÓN DE LA VARIANZA (VIF) ===")
vif_data = pd.DataFrame()
vif_data["Componente"] = X_final.columns
vif_data["VIF"] = [variance_inflation_factor(X_final.values, i) for i in range(X_final.shape[1])]
print(vif_data.to_string(index=False))

# 4. Graficar el Q-Q Plot para tu documento de tesis
plt.figure(figsize=(6, 4))
stats.probplot(modelo_final.resid, dist="norm", plot=plt)
plt.title("Gráfico Q-Q de Residuos (Validación de Normalidad)")
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC **Prioridad 3 - Bootstrap de Coeficientes**
# MAGIC
# MAGIC Hacer bootstrap sobre solo 23 observaciones para evaluar la estabilidad del Stepwise es estadísticamente inestable, ya que al resamplear con reemplazo una muestra tan pequeña se van a generar matrices singulares (columnas repetidas con varianza cero que harán colapsar el algoritmo del PCA o el OLS). El AICc ya resolvió el problema del sobreajuste de manera paramétrica formal.

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC **Prioridad 4 - Métodos Alternativos: Lasso / Ridge / Elastic Net**
# MAGIC
# MAGIC La sugerencia de probar Métodos es estándar en la analítica predictiva. No obstante, en nuestra metodología decidimos irnos por el camino institucional (PCA por bloques temáticos + Stepwise AICc). Esta ruta metodológica tiene una ventaja inmensa sobre Lasso, Ridge u otras metodologias para este proyecto: mantiene las fronteras conceptuales del DANE.
# MAGIC
# MAGIC Si usaramos Lasso sobre las 1.500 variables en bruto, el algoritmo podría seleccionar 3 variables sueltas: el recaudo de un impuesto, la tasa de mortalidad y el número de hectáreas de bosque, destruyendo cualquier posibilidad de análisis macroestructural organizado. Nuestro enfoque actual (PCA por bloques) es metodológicamente superior en términos de interpretación de políticas públicas. 
# MAGIC
# MAGIC ¿Consideran que igual deberiamos probar estos mocelos?