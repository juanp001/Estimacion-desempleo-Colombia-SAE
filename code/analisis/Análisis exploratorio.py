# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC # Análisis exploratorio
# MAGIC
# MAGIC Tras completar las etapas de limpieza, validación y construcción de covariables, se realizó un análisis exploratorio sobre el conjunto reducido de indicadores seleccionados mediante la `Metodología de Selección de Covariables Ver 2.0`. Se aplicó como criterio un umbral de correlación directa con la tasa de desempleo superior a 0.4, lo que inicialmente arrojó 84 variables seleccionadas. Sin embargo, tras una revisión detallada, se identificó que solo 16 de ellas cuentan con respaldo en la literatura respecto a su causalidad con la tasa de desempleo, por lo que serán las utilizadas en el análisis exploratorio.
# MAGIC
# MAGIC El objetivo de esta fase es caracterizar las distribuciones de dichas covariables, identificar patrones relevantes y evaluar su pertinencia como insumo para el modelo. Este análisis se concibe como un diagnóstico preliminar que busca garantizar la estabilidad numérica y la interpretabilidad de los resultados, además de servir como filtro adicional para depurar redundancias y prevenir problemas de multicolinealidad.

# COMMAND ----------

# DBTITLE 1,Cell 2
# Leer la tabla de tasa de desempleo de covariables para las ciudades capitales
from pyspark.sql import functions as F

df = spark.table("tesis.modelo.tasa_desempleo_covariables")

# Obtener nombres de columnas de la tercera a la catorce
cols_3_14 = df.columns[2:14]

# Lista de variables adicionales
vars_adicionales = [
    "080010011", "030010002", "310010017", "040010009", "310010020", "070120028",
    "040010028", "070120035", "070010019", "140010004", "310010014", "070120020",
    "260020003", "080030004", "310010008", "060010001"
]

# Unir y eliminar duplicados
cols_final = list(dict.fromkeys(cols_3_14 + vars_adicionales))

# Quitar DEPARTAMENTO y MUNICIPIO si están en la lista
cols_final = [col for col in cols_final if col not in ["DEPARTAMENTO", "MUNICIPIO","TASA_DESEMPLEO_PCT","SE_BOOTSTRAP_PCT","IC_INF_PCT","IC_SUP_PCT","AMPLITUD_IC","CV_PORCENTAJE"]]

# Seleccionar columnas requeridas
df_nueva = df.select(cols_final)

# Convertir la columna 060010001 a tipo numérico
df_nueva = df_nueva.withColumn("060010001", F.col("060010001").cast("double"))

display(df_nueva)

# COMMAND ----------

# MAGIC %md
# MAGIC # Etapa 1 del análisis exploratorio
# MAGIC ## Dimensiones
# MAGIC El dataset utilizado para este análisis exploratorio cuenta con 23 filas y 20 columnas.
# MAGIC ## Tipo de variables
# MAGIC De las 20 variables, 16 son numéricas y 4 categóricas. Entre las categóricas se encuentran el código del departamento, el código del municipio, el departamento normalizado y la entidad normalizada, las cuales permiten ubicar la observación a analizar y no serán incluidas en el análisis exploratorio de variables.
# MAGIC ## Valores faltantes y duplicados
# MAGIC No se encontró ningun tipo de valor faltante o duplicado en el dataset seleccionado

# COMMAND ----------

# Obtener dimensiones del DataFrame df_nueva
num_filas = df_nueva.count()  # Número de filas en el DataFrame
num_columnas = len(df_nueva.columns)  # Número de columnas en el DataFrame

# Contar variables numéricas y categóricas
tipos = dict(df_nueva.dtypes)  # Diccionario con los tipos de datos de cada columna
num_numericas = sum(1 for t in tipos.values() if t in ["int", "bigint", "double", "float", "decimal"])  # Variables numéricas
num_categoricas = num_columnas - num_numericas  # Variables categóricas

# Identificación de valores faltantes por columna
valores_faltantes = df_nueva.select([F.count(F.when(F.col(c).isNull(), c)).alias(c) for c in df_nueva.columns])
display(valores_faltantes)

# Identificación de filas duplicadas
num_duplicados = df_nueva.count() - df_nueva.dropDuplicates().count()

# Mostrar dimensiones, conteo de variables por tipo, valores faltantes y duplicados
print(f"Filas: {num_filas}, Columnas: {num_columnas}")
print(f"Variables numéricas: {num_numericas}, Variables categóricas: {num_categoricas}")
print(f"Filas duplicadas: {num_duplicados}")

# COMMAND ----------

# MAGIC %md
# MAGIC # Etapa 2 del análisis exploratorio
# MAGIC ## Outliers
# MAGIC
# MAGIC Tras la visualización de las variables numéricas mediante boxplots y el análisis de los valores extremos, se identificaron patrones relevantes en la presencia de datos atípicos para algunas de las covariables seleccionadas. A continuación, se destacan los puntos representativos:
# MAGIC
# MAGIC ### Posición nacional en gestión
# MAGIC Esta variable mide la eficiencia y capacidad de las alcaldías para movilizar y ejecutar recursos, lo que se traduce en la garantía de inversión pública en los territorios. Considerando que la base de datos Terridata abarca información de 1102 municipios y 32 departamentos, es natural observar una alta dispersión y variabilidad en los resultados, especialmente al trabajar con una muestra reducida como la utilizada en este análisis. Esta dispersión puede deberse tanto a diferencias estructurales entre municipios como a factores coyunturales. Sin embargo, a pesar de que la variable muestra una correlación directa significativa con la tasa de desempleo, la falta de estabilidad y la alta variabilidad observada en la muestra justifican su exclusión del modelo, priorizando la robustez y la interpretabilidad de los resultados.
# MAGIC
# MAGIC ### Cobertura de energía eléctrica rural
# MAGIC En el caso de la cobertura de energía eléctrica rural, se identificaron valores atípicos con coberturas inferiores al 80%, llegando incluso a mínimos cercanos al 44% (Riohacha). Esta amplia variabilidad refleja de manera fiel las problemáticas estructurales presentes en los territorios rurales, donde el acceso a servicios básicos sigue siendo un desafío. A diferencia de la variable anterior, la presencia de estos valores extremos no distorsiona el análisis, sino que aporta información valiosa sobre las condiciones reales que enfrentan los municipios. Por ello, se considera pertinente mantener esta variable en el modelo, ya que su inclusión puede mejorar la capacidad explicativa y la adaptabilidad del modelo a contextos diversos, evidenciando la relación entre la falta de oportunidades y el aumento en las tasas de desempleo.
# MAGIC
# MAGIC ### Índice de Ecosistemas Estratégicos
# MAGIC Esta variable refleja la proporción de áreas naturales protegidas o estratégicas dentro del territorio municipal. La presencia de tres valores atípicos indica una marcada heterogeneidad ambiental entre municipios, donde algunos concentran grandes extensiones de ecosistemas estratégicos mientras otros presentan degradación o escasa cobertura vegetal. Esta dispersión es esperable dada la diversidad geográfica del país y aporta información relevante sobre la relación entre sostenibilidad ambiental y desarrollo económico.
# MAGIC
# MAGIC ### Porcentaje de inversión - Transporte
# MAGIC El único valor atípico identificado sugiere un municipio con una asignación presupuestal inusualmente alta en infraestructura vial y transporte público. Este comportamiento puede deberse a decisiones coyunturales de inversión o a la ejecución de proyectos estratégicos. Este dato extremo podría generar cierta distorsión.
# MAGIC
# MAGIC ### Tasa de tránsito inmediata a la educación superior
# MAGIC El valor extremo observado corresponde a un municipio con una tasa de transición educativa significativamente superior al promedio nacional. Este comportamiento puede asociarse a territorios con mayor oferta universitaria o políticas locales de fomento educativo.
# MAGIC
# MAGIC ### Porcentaje de inversión - Desarrollo comunitario
# MAGIC Los cuatro valores atípicos identificados corresponden a municipios con niveles de inversión comunitaria altos. Este patrón refleja desigualdades en la asignación de recursos para programas sociales y participación ciudadana. Aunque la variabilidad es alta, la variable aporta información sobre la capacidad institucional para promover cohesión social y desarrollo local.
# MAGIC
# MAGIC ### Ingresos corrientes per cápita
# MAGIC El valor atípico superior evidencia un municipio con ingresos fiscales muy por encima del promedio, siendo Bogotá un centro urbano con alta actividad económica. Este comportamiento extremo es coherente con la concentración de recursos en territorios más desarrollados y no representa un error, sino una característica estructural del sistema fiscal. 
# MAGIC
# MAGIC ### Índice de pobreza multidimensional (IPM)
# MAGIC El outlier identificado corresponde a un municipio con niveles de pobreza significativamente más altos que el resto. Este valor extremo es relevante para el análisis, ya que evidencia territorios con condiciones socioeconómicas críticas. 
# MAGIC
# MAGIC ### Índice de Pobreza
# MAGIC Similar al IPM, el valor extremo refleja concentración de pobreza en un territorio específico. Este comportamiento es esperado en contextos de desigualdad regional y aporta información complementaria sobre vulnerabilidad social. 
# MAGIC
# MAGIC ### Índice de Incidencia del Conflicto Armado - IICA
# MAGIC Los tres valores atípicos corresponden a municipios con alta exposición histórica al conflicto armado (Cucuta, Cali y Quibdo). Este patrón es coherente con la realidad territorial y aporta información sobre factores estructurales que afectan el mercado laboral. 
# MAGIC
# MAGIC ### Índice de Productividad
# MAGIC Los tres valores extremos representan municipios con niveles de productividad notablemente superiores (Bogotá, Medellín y Barranquilla), siendo polos industriales con alta eficiencia económica. Aunque la dispersión es elevada, esta variable es esencial para explicar la capacidad de generación de empleo y crecimiento local.
# MAGIC
# MAGIC ### Tasa de hurto a personas por cada 100.000 habitantes
# MAGIC El valor atípico superior refleja un municipio con incidencia delictiva muy elevada (Bogotá), siendo una zona urbana con alta densidad poblacional. Este comportamiento extremo es informativo, pues la inseguridad puede afectar la estabilidad laboral y la inversión. 
# MAGIC
# MAGIC ### Demás variables
# MAGIC Variables como el índice de ciencia, la cobertura neta en educación secundaria, el porcentaje de inversión - Educación y la seguridad, no presenta información con datos faltantes.
# MAGIC
# MAGIC ### Conclusiones
# MAGIC La selección de las covariables `Cobertura de energía eléctrica rural`, `Tasa de tránsito inmediata a la educación superior`, `Índice de pobreza multidimensional (IPM)` e `Índice de Productividad` responde a criterios metodológicos que integran relevancia conceptual, estabilidad estadística y capacidad explicativa frente a la tasa de desempleo.
# MAGIC
# MAGIC En primer lugar, estas variables representan dimensiones complementarias del desarrollo territorial: infraestructura básica, capital humano, condiciones socioeconómicas y desempeño económico. Su inclusión permite capturar de manera integral los factores estructurales que inciden en la dinámica del mercado laboral.
# MAGIC
# MAGIC En segundo lugar, aunque presentan valores atípicos, estos reflejan realidades territoriales diferenciadas y aportan contraste analítico sin comprometer la robustez del modelo. 

# COMMAND ----------

# DBTITLE 1,o
import matplotlib.pyplot as plt
import numpy as np

# Identificar variables numéricas
tipos = dict(df_nueva.dtypes)
vars_numericas = [col for col, tipo in tipos.items() if tipo in ["int", "bigint", "double", "float", "decimal"]]

# Obtener nombres descriptivos de las variables numéricas desde tesis.dim.dim_indicadores
df_indicadores = spark.table("tesis.dim.dim_indicadores")
indicadores_dict = {row["CODIGO_INDICADOR"]: row["INDICADOR"] for row in df_indicadores.select("CODIGO_INDICADOR", "INDICADOR").collect()}

outliers_info = []

for col in vars_numericas:
    nombre_variable = indicadores_dict.get(col, col)
    # Convertir a pandas y extraer valores como array
    data = df_nueva.select(col).dropna().toPandas()[col].values
    # Calcular Q1, Q3 y IQR
    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers = data[(data < lower_bound) | (data > upper_bound)]
    outliers_info.append({
        "Variable": nombre_variable,
        "Cantidad_Outliers": len(outliers),
        "Valores_Outliers": outliers.tolist()
    })
    # Crear boxplot
    plt.figure(figsize=(6, 4))
    plt.boxplot(data)
    plt.title(f"Boxplot de {nombre_variable}")
    plt.ylabel("Valores")
    plt.show()

# Crear DataFrame Spark con la información de outliers
outliers_df = spark.createDataFrame(outliers_info)
display(outliers_df)

# Mostrar tabla con títulos descriptivos de las variables numéricas y ENTIDAD_ESTADARIZADO
cols_descriptivos = [indicadores_dict.get(col, col) for col in vars_numericas]
df_nueva_descriptivo = df_nueva.select(["ENTIDAD_NORMALIZADO"] + vars_numericas)
for i, col in enumerate(vars_numericas):
    df_nueva_descriptivo = df_nueva_descriptivo.withColumnRenamed(col, cols_descriptivos[i])
display(df_nueva_descriptivo)

# COMMAND ----------

# MAGIC %md
# MAGIC # Etapa 3 Análisis exploratorio
# MAGIC ## Análisis descriptivo
# MAGIC ### Cobertura de energía eléctrica rural
# MAGIC La cobertura eléctrica rural presenta una media alta (90%) y una mediana superior (96,42%), lo que indica que la mayoría de municipios tienen niveles elevados de electrificación. Sin embargo, la desviación estándar de 13.8942 y un rango cercano a 56 puntos porcentuales evidencian una heterogeneidad significativa: mientras algunos municipios alcanzan casi el 100% de cobertura, otros se mantienen en niveles críticos (cercanos al 44%). Este comportamiento refleja desigualdades estructurales en el acceso a servicios básicos, lo cual es un factor explicativo relevante para la tasa de desempleo en zonas rurales.
# MAGIC ### Tasa de tránsito inmediato a la educación superior
# MAGIC La tasa de tránsito a educación superior muestra una distribución relativamente estable, con media y mediana muy cercanas (47 y 46,22). La desviación estándar baja (7.2001) y el rango moderado (31) sugieren que la mayoría de municipios se concentran en torno a valores similares, aunque existen diferencias notables entre territorios con baja transición (36,6%) y aquellos con tasas superiores al 53%. Esta variable es clave para explicar la empleabilidad futura, pues refleja la capacidad de los jóvenes para acceder a educación superior, un factor directamente asociado a la reducción del desempleo estructural.
# MAGIC ### índice de pobreza multidimensional - IPM
# MAGIC El IPM presenta una media de 21 y una mediana más baja (17,4), lo que indica una asimetría hacia valores altos: algunos municipios concentran niveles de pobreza multidimensional muy superiores al promedio. La desviación estándar de 9.6272 y el rango de 36.1 puntos muestran una dispersión considerable, reflejando la heterogeneidad socioeconómica del país. Este comportamiento es consistente con la literatura, que señala la pobreza como un determinante estructural del desempleo, y justifica plenamente su inclusión como covariable.
# MAGIC ### índice de Productividad
# MAGIC La productividad municipal presenta una media de 49 y una mediana inferior (44,09), lo que sugiere la existencia de municipios con niveles de productividad muy elevados que elevan el promedio. La desviación estándar (9.9255) y el rango (36,5) confirman una distribución heterogénea, donde polos industriales y urbanos (Bogotá, Medellín, Barranquilla) destacan frente a municipios con menor capacidad productiva. Esta variable es esencial para explicar la absorción laboral y las diferencias regionales en el desempleo.

# COMMAND ----------

# Seleccionar solo las variables requeridas para el análisis descriptivo
vars_seleccionadas = [
    "ENTIDAD_NORMALIZADO",  # Entidad normalizada
    "030010002",  # Cobertura de energía eléctrica rural
    "040010028",  # Tasa de tránsito inmediata a la educación superior
    "140010004",  # Índice de pobreza multidimensional (IPM)
    "310010008"   # Índice de Productividad
]

# Crear DataFrame base solo con las variables seleccionadas
df_base_seleccionada = df_nueva.select(vars_seleccionadas)
display(df_base_seleccionada)

# Calcular y mostrar estadísticas descriptivas de las variables numéricas seleccionadas
import matplotlib.pyplot as plt
import numpy as np

# Obtener nombres descriptivos de las variables desde la tabla de indicadores
df_indicadores = spark.table("tesis.dim.dim_indicadores")
indicadores_dict = {row["CODIGO_INDICADOR"]: row["INDICADOR"] for row in df_indicadores.select("CODIGO_INDICADOR", "INDICADOR").collect()}

# Filtrar solo variables numéricas para el análisis
vars_numericas = [v for v in vars_seleccionadas if v != "ENTIDAD_NORMALIZADO"]

stats_info = []
for col in vars_numericas:
    nombre_variable = indicadores_dict.get(col, col)
    # Extraer datos como array para cálculos estadísticos
    data = df_base_seleccionada.select(col).dropna().toPandas()[col].values
    # Calcular estadísticas descriptivas
    media = np.mean(data)
    mediana = np.median(data)
    std = np.std(data)
    rango = np.max(data) - np.min(data)
    percentiles = np.percentile(data, [10, 25, 50, 75, 90])
    stats_info.append({
        "Variable": nombre_variable,
        "Media": float(media),
        "Mediana": float(mediana),
        "Desviacion_Estandar": float(std),
        "Rango": float(rango),
        "Percentil_10": float(percentiles[0]),
        "Percentil_25": float(percentiles[1]),
        "Percentil_50": float(percentiles[2]),
        "Percentil_75": float(percentiles[3]),
        "Percentil_90": float(percentiles[4])
    })
    # Graficar histograma de la variable
    plt.figure(figsize=(8, 4))
    plt.hist(data, bins=10, color='skyblue', edgecolor='black')
    plt.title(f"Histograma de {nombre_variable}")
    plt.xlabel("Valores")
    plt.ylabel("Frecuencia")
    plt.grid(True)
    plt.show()
    # Graficar boxplot de la variable
    plt.figure(figsize=(6, 4))
    plt.boxplot(data)
    plt.title(f"Boxplot de {nombre_variable}")
    plt.ylabel("Valores")
    plt.show()

# Crear DataFrame Spark con las estadísticas descriptivas calculadas
stats_df = spark.createDataFrame(stats_info)
display(stats_df)

# COMMAND ----------

# MAGIC %md
# MAGIC # Etapa 4 análisis exploratorio
# MAGIC ## Correlaciones
# MAGIC ### Cobertura de energía eléctrica rural
# MAGIC La cobertura eléctrica rural muestra correlaciones negativas moderadas con la tasa de tránsito a la educación superior (-0.33) y con el índice de pobreza multidimensional (-0.61), además de una correlación positiva débil con la productividad (0.21). Este comportamiento evidencia que los municipios con menor acceso a energía eléctrica tienden a presentar mayores niveles de pobreza y menor acceso educativo, lo que refleja una clara brecha estructural entre zonas rurales y urbanas. La relación positiva con la productividad, aunque débil, sugiere que la electrificación contribuye al desarrollo económico local. En conjunto, esta variable captura una dimensión de infraestructura crítica para explicar las desigualdades territoriales que inciden en el desempleo.
# MAGIC ### Tasa de tránsito inmediata a la educación superior
# MAGIC La tasa de tránsito educativa presenta correlaciones débiles con las demás variables: positiva con el IPM (0.08) y negativa con la productividad (-0.06). Estas asociaciones indican que el acceso a educación superior no depende exclusivamente de las condiciones económicas o productivas del territorio, sino también de factores institucionales y culturales. La baja magnitud de las correlaciones confirma que esta variable aporta información diferenciada al modelo, representando el componente de capital humano y formación profesional, esencial para comprender las dinámicas de empleabilidad en el largo plazo.
# MAGIC ### Índice de pobreza multidimensional (IPM)
# MAGIC El IPM mantiene correlaciones negativas con la cobertura eléctrica (-0.61) y con la productividad (-0.53), lo que refleja una coherencia estructural: los municipios con mayor pobreza presentan menor infraestructura y menor capacidad productiva. Estas relaciones son consistentes con la teoría del desarrollo económico, que vincula la pobreza con la falta de oportunidades laborales y la baja inversión pública. La magnitud moderada de las correlaciones indica que el IPM es una covariable robusta y estable, capaz de capturar las condiciones socioeconómicas que explican la persistencia del desempleo en territorios vulnerables.
# MAGIC ### Índice de Productividad
# MAGIC La productividad municipal presenta correlaciones débiles o moderadas con las demás variables, siendo negativa con el IPM (-0.53) y positiva con la cobertura eléctrica (0.21). Este patrón confirma que los territorios más productivos tienden a tener mejores condiciones de infraestructura y menores niveles de pobreza. La baja correlación con la tasa de tránsito educativa (-0.06) sugiere que la productividad depende más de factores estructurales que de la formación académica inmediata. En términos de modelamiento, esta variable aporta una dimensión económica sólida que complementa las variables sociales y de infraestructura, fortaleciendo la capacidad explicativa del modelo frente a la tasa de desempleo.

# COMMAND ----------

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Obtener nombres descriptivos de las variables desde la tabla de indicadores
df_indicadores = spark.table("tesis.dim.dim_indicadores")
indicadores_dict = {row["CODIGO_INDICADOR"]: row["INDICADOR"] for row in df_indicadores.select("CODIGO_INDICADOR", "INDICADOR").collect()}

# Filtrar solo variables numéricas
vars_numericas = [col for col in df_base_seleccionada.columns if col != "ENTIDAD_NORMALIZADO"]
vars_numericas_desc = [indicadores_dict.get(col, col) for col in vars_numericas]

# Extraer datos como pandas DataFrame para análisis de correlación
data_pd = df_base_seleccionada.select(vars_numericas).dropna().toPandas()
data_pd.columns = vars_numericas_desc  # Renombrar columnas a nombres descriptivos

# Calcular matriz de correlación
corr_matrix = data_pd.corr()

# Mostrar matriz de correlación como DataFrame Spark
corr_info = []
for i, col1 in enumerate(vars_numericas_desc):
    for j, col2 in enumerate(vars_numericas_desc):
        if i <= j:  # Solo una vez cada par
            corr_info.append({
                "Variable_1": col1,
                "Variable_2": col2,
                "Correlacion": float(corr_matrix.loc[col1, col2])
            })
corr_df = spark.createDataFrame(corr_info)
display(corr_df)

# Graficar matriz de correlación
plt.figure(figsize=(8, 6))
sns.heatmap(corr_matrix, annot=True, cmap="coolwarm", fmt=".2f", xticklabels=vars_numericas_desc, yticklabels=vars_numericas_desc)
plt.title("Matriz de correlación entre variables numéricas")
plt.show()

# Graficar scatterplots de cada par de variables
for i, col1 in enumerate(vars_numericas_desc):
    for j, col2 in enumerate(vars_numericas_desc):
        if i < j:
            plt.figure(figsize=(6, 4))
            sns.scatterplot(x=data_pd[col1], y=data_pd[col2])
            plt.xlabel(col1)
            plt.ylabel(col2)
            plt.title(f"Scatterplot: {col1} vs {col2}")
            plt.grid(True)
            plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC # Base final con las variables seleccionadas

# COMMAND ----------

# Seleccionar las primeras 14 variables más las variables adicionales especificadas
vars_adicionales = ["030010002", "040010028", "140010004", "310010008"]
cols_seleccionadas = df.columns[:14] + [v for v in vars_adicionales if v not in df.columns[:14]]
df_seleccionado = df.select(cols_seleccionadas)
display(df_seleccionado)

# Guardar la base en la carpeta tesis.modelo con el nombre tasa_desempleo_covariables_seleccionadas
df_seleccionado.write.mode("overwrite").saveAsTable("tesis.modelo.tasa_desempleo_covariables_seleccionadas")

# COMMAND ----------

# DBTITLE 1,Crear tabla con join sin duplicados
# Importar la tabla terridata_extendido_plata de la base tesis y filtro para tener los valle y cauca

df_terridata = spark.table("tesis.terridata.terridata_extendido_plata")
df_terridata_filtrado = df_terridata.filter(
    (df_terridata.CODIGO_DEPARTAMENTO.isin([19, 76])) & 
    (df_terridata.ANO == 2018) & 
    (df_terridata.MES == 12) &
    (~df_terridata.CODIGO_ENTIDAD.isin([19000, 76000]))
)
display(df_terridata_filtrado)

# COMMAND ----------

# Importar la tabla de personas del censo nacional de la base tesis
df_personas = spark.table("tesis.censo_nal.personas")

# Filtrar personas de los departamentos 19 (cauca) y 76 (Valle del cauca)
df_personas_filtrado = df_personas.filter(df_personas.U_DPTO.isin([19, 76]))

# Crear columna PET: personas en edad de trabajar (mayores del 4 quinquenio es decir de 15 años)
df_personas_filtrado = df_personas_filtrado.withColumn(
    "PET",
    F.when(df_personas_filtrado.P_EDADR > 3, F.lit(1)).otherwise(F.lit(None))
)

# Crear columna PEA: personas económicamente activas (trabajo 1-4 y PET=1)
df_personas_filtrado = df_personas_filtrado.withColumn(
    "PEA",
    F.when(
        (df_personas_filtrado.P_TRABAJO.isin([1, 2, 3, 4])) & (df_personas_filtrado.PET == 1),
        F.lit(1)
    ).otherwise(F.lit(None))
)

# Crear columna OCUPADOS: personas con trabajo (1, 2, 3)
df_personas_filtrado = df_personas_filtrado.withColumn(
    "OCUPADOS",
    F.when(df_personas_filtrado.P_TRABAJO.isin([1, 2, 3]), F.lit(1)).otherwise(F.lit(None))
)

# Crear columna DESOCUPADOS: personas buscando trabajo (4)
df_personas_filtrado = df_personas_filtrado.withColumn(
    "DESOCUPADOS",
    F.when(df_personas_filtrado.P_TRABAJO == 4, F.lit(1)).otherwise(F.lit(None))
)

# Crear columna INACTIVOS: personas fuera de la fuerza laboral (no 1-4)
df_personas_filtrado = df_personas_filtrado.withColumn(
    "INACTIVOS",
    F.when(~df_personas_filtrado.P_TRABAJO.isin([1, 2, 3, 4]), F.lit(1)).otherwise(F.lit(None))
)

# Crear columna CODIGO_MUNICIPIO: concatenar departamento y municipio
df_personas_filtrado = df_personas_filtrado.withColumn(
    "CODIGO_MUNICIPIO",
    F.concat(F.col("U_DPTO").cast("string"), F.col("U_MPIO").cast("string"))
)

# Agrupar por municipio y sumar cada indicador
df_personas_agrupado = df_personas_filtrado.groupBy("CODIGO_MUNICIPIO").agg(
    F.sum("PEA").alias("PEA"),
    F.sum("PET").alias("PET"),
    F.sum("OCUPADOS").alias("OCUPADOS"),
    F.sum("DESOCUPADOS").alias("DESOCUPADOS"),
    F.sum("INACTIVOS").alias("INACTIVOS")
)

# Calcular tasa de desempleo por municipio
df_personas_agrupado = df_personas_agrupado.withColumn(
    "TASA_DESEMPLEO",
    (F.col("DESOCUPADOS") / F.col("PEA")) * 100
)

# Mostrar el resultado final
display(df_personas_agrupado)