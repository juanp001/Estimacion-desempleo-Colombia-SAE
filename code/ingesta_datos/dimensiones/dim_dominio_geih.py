# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Tabla dimensional de dominios GEIH (ciudad y ciudad A.M.)
# MAGIC
# MAGIC Crea `tesis.dim.dim_dominio_geih`, que asigna cada municipio de las 32 ciudades GEIH al
# MAGIC **dominio de estimación** al que pertenece. Una fila por municipio miembro.
# MAGIC
# MAGIC ## Por qué existe
# MAGIC
# MAGIC En los microdatos públicos de la GEIH (marco 2005) el campo `AREA` identifica la **ciudad con su
# MAGIC área metropolitana**, no el municipio: los hogares de Yumbo llegan con `AREA = 76`, igual que los
# MAGIC de Cali. `geih_oro` traduce ese código al de la capital, así que la estimación directa de
# MAGIC «Cali» es en realidad la de **Cali A.M.** (coincide con la cifra publicada por el DANE). Para que
# MAGIC las covariables describan el mismo territorio que la tasa, hay que agregarlas sobre todos los
# MAGIC municipios del A.M.; esta tabla define esa membresía.
# MAGIC
# MAGIC ## Fuente de la membresía
# MAGIC
# MAGIC DANE, Metodología General GEIH v9 (abr. 2016), PDF 9: lista de las 13 grandes ciudades con sus
# MAGIC áreas metropolitanas. Nota 1 del PDF 3: «para la GEIH se entiende por área metropolitana de la
# MAGIC ciudad aquellos municipios que entran en la selección de la muestra». Se usa **estrictamente** la
# MAGIC lista de la GEIH, no el área metropolitana legal:
# MAGIC
# MAGIC | Dominio | Municipios |
# MAGIC |---|---|
# MAGIC | Medellín A.M. | Valle de Aburrá: Medellín, Barbosa, Bello, Caldas, Copacabana, Envigado, Girardota, Itagüí, La Estrella, Sabaneta |
# MAGIC | Barranquilla A.M. | Barranquilla, Soledad |
# MAGIC | Bucaramanga A.M. | Bucaramanga, Floridablanca, Girón, Piedecuesta |
# MAGIC | Cali A.M. | Cali, Yumbo |
# MAGIC | Manizales A.M. | Manizales, Villamaría |
# MAGIC | Pereira A.M. | Pereira, Dosquebradas, La Virginia |
# MAGIC | Cúcuta A.M. | Cúcuta, Villa del Rosario, Los Patios, El Zulia |
# MAGIC
# MAGIC Las otras 25 capitales (Bogotá, Pasto, Ibagué, Villavicencio, Montería, Cartagena, las 11
# MAGIC ciudades intermedias y las 8 capitales de los nuevos departamentos) son dominios de un solo
# MAGIC municipio. San Andrés y las 8 capitales nuevas no tienen muestra en los microdatos que se
# MAGIC ingieren; figuran para que la partición esté completa, pero no generan estimación directa.
# MAGIC
# MAGIC ## Columnas
# MAGIC
# MAGIC * `CODIGO_DOMINIO`: código DIVIPOLA de la capital (identifica el dominio; es el código que
# MAGIC   `geih_oro` asigna a la muestra del `AREA`)
# MAGIC * `NOMBRE_DOMINIO`: nombre con el que el DANE publica el dominio («Cali A.M.», «Popayán»)
# MAGIC * `TIPO_DOMINIO`: `CIUDAD_AM` (más de un municipio) o `CIUDAD`
# MAGIC * `CODIGO_MUNICIPIO`, `MUNICIPIO`, `CODIGO_DEPARTAMENTO`, `DEPARTAMENTO`: municipio miembro
# MAGIC * `ES_CAPITAL`: `True` en la fila de la capital
# MAGIC
# MAGIC ## Limitación conocida
# MAGIC
# MAGIC En el marco 2005 el `AREA` solo aparece en los registros de cabecera (CLASE = 1): los dominios de
# MAGIC ciudad son **urbanos**, mientras que los indicadores de TerriData son municipales (incluyen la
# MAGIC zona rural). La parte rural de estos municipios pertenece al subuniverso «resto» de la GEIH
# MAGIC (v9, PDF 11), que el proyecto no usa.

# COMMAND ----------

# DBTITLE 1,Importación de librerías
from pyspark.sql import Row
from pyspark.sql.functions import col

# COMMAND ----------

# DBTITLE 1,Definición de los dominios
# Capital → (nombre publicado por el DANE, municipios adicionales del A.M. según la GEIH).
# Los nombres de los 23 dominios con muestra son los del anexo «Mercado laboral según proyecciones
# CNPV 2018» (pestaña «areas trim movil»), de modo que la estimación directa puede validarse contra
# tesis.geih_bronce.datos_municipales por nombre.
DOMINIOS_GEIH = {
    # 13 grandes ciudades (v9, PDF 9)
    "11001": ("Bogotá", []),
    "05001": (
        "Medellín A.M.",
        # Valle de Aburrá
        [
            "05079",
            "05088",
            "05129",
            "05212",
            "05266",
            "05308",
            "05360",
            "05380",
            "05631",
        ],
    ),
    "76001": ("Cali A.M.", ["76892"]),  # Yumbo
    "08001": ("Barranquilla A.M.", ["08758"]),  # Soledad
    "68001": (
        "Bucaramanga A.M.",
        ["68276", "68307", "68547"],
    ),  # Floridablanca, Girón, Piedecuesta
    "17001": ("Manizales A.M.", ["17873"]),  # Villamaría
    "52001": ("Pasto", []),
    "66001": ("Pereira A.M.", ["66170", "66400"]),  # Dosquebradas, La Virginia
    "73001": ("Ibagué", []),
    "54001": (
        "Cúcuta A.M.",
        ["54874", "54405", "54261"],
    ),  # Villa del Rosario, Los Patios, El Zulia
    "50001": ("Villavicencio", []),
    "23001": ("Montería", []),
    "13001": ("Cartagena", []),
    # 11 ciudades intermedias (v9, PDF 9)
    "15001": ("Tunja", []),
    "18001": ("Florencia", []),
    "19001": ("Popayán", []),
    "20001": ("Valledupar", []),
    "27001": ("Quibdó", []),
    "41001": ("Neiva", []),
    "44001": ("Riohacha", []),
    "47001": ("Santa Marta", []),
    "63001": ("Armenia", []),
    "70001": ("Sincelejo", []),
    "88001": ("San Andrés", []),
    # 8 capitales de los nuevos departamentos (v9, PDF 9-10)
    "81001": ("Arauca", []),
    "85001": ("Yopal", []),
    "86001": ("Mocoa", []),
    "91001": ("Leticia", []),
    "94001": ("Inírida", []),
    "95001": ("San José del Guaviare", []),
    "97001": ("Mitú", []),
    "99001": ("Puerto Carreño", []),
}

N_FILAS_ESPERADAS = sum(1 + len(miembros) for _, miembros in DOMINIOS_GEIH.values())

# COMMAND ----------

# DBTITLE 1,Construcción y validación de la tabla
filas = []
for capital, (nombre, miembros) in DOMINIOS_GEIH.items():
    tipo = "CIUDAD_AM" if miembros else "CIUDAD"
    for municipio in [capital] + miembros:
        filas.append(
            Row(
                CODIGO_DOMINIO=capital,
                NOMBRE_DOMINIO=nombre,
                TIPO_DOMINIO=tipo,
                CODIGO_MUNICIPIO=municipio,
                ES_CAPITAL=municipio == capital,
            )
        )

df_membresia = spark.createDataFrame(filas)

codigos = [f.CODIGO_MUNICIPIO for f in filas]
duplicados = sorted({c for c in codigos if codigos.count(c) > 1})
if duplicados:
    raise ValueError(f"Municipios asignados a más de un dominio: {duplicados}")

df_divipola = spark.table("tesis.dim.dim_divipola").select(
    "CODIGO_DEPARTAMENTO", "DEPARTAMENTO", "CODIGO_MUNICIPIO", "MUNICIPIO"
)

df_dominio = df_membresia.join(df_divipola, on="CODIGO_MUNICIPIO", how="left").select(
    "CODIGO_DOMINIO",
    "NOMBRE_DOMINIO",
    "TIPO_DOMINIO",
    "CODIGO_MUNICIPIO",
    "MUNICIPIO",
    "CODIGO_DEPARTAMENTO",
    "DEPARTAMENTO",
    "ES_CAPITAL",
)

sin_divipola = [
    f.CODIGO_MUNICIPIO
    for f in df_dominio.filter(col("MUNICIPIO").isNull())
    .select("CODIGO_MUNICIPIO")
    .collect()
]
if sin_divipola:
    raise ValueError(
        f"Códigos sin correspondencia en dim_divipola: {sorted(sin_divipola)}"
    )

n_filas = df_dominio.count()
if n_filas != N_FILAS_ESPERADAS:
    raise ValueError(
        f"Se esperaban {N_FILAS_ESPERADAS} filas y se obtuvieron {n_filas}"
    )

print(f"Dominios: {len(DOMINIOS_GEIH)}  |  municipios miembro: {n_filas}")
print(
    f"Dominios con área metropolitana: "
    f"{df_dominio.filter(col('TIPO_DOMINIO') == 'CIUDAD_AM').select('CODIGO_DOMINIO').distinct().count()}"
    f" ({df_dominio.filter(col('TIPO_DOMINIO') == 'CIUDAD_AM').count()} municipios)"
)
display(
    df_dominio.orderBy("CODIGO_DOMINIO", col("ES_CAPITAL").desc(), "CODIGO_MUNICIPIO")
)

# COMMAND ----------

# DBTITLE 1,Guardar tabla dimensional
df_dominio.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.dim.dim_dominio_geih"
)
print("Tabla escrita: tesis.dim.dim_dominio_geih")
