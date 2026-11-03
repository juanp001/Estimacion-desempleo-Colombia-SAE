# dimensiones__dim_dominio_geih


## Celda 0

```python
%md
# Tabla dimensional de dominios GEIH (ciudad y ciudad A.M.)

Crea `tesis.dim.dim_dominio_geih`, que asigna cada municipio de las 32 ciudades GEIH al
**dominio de estimación** al que pertenece. Una fila por municipio miembro.

## Por qué existe

En los microdatos públicos de la GEIH (marco 2005) el campo `AREA` identifica la **ciudad con su
área metropolitana**, no el municipio: los hogares de Yumbo llegan con `AREA = 76`, igual que los
de Cali. `geih_oro` traduce ese código al de la capital, así que la estimación directa de
«Cali» es en realidad la de **Cali A.M.** (coincide con la cifra publicada por el DANE). Para que
las covariables describan el mismo territorio que la tasa, hay que agregarlas sobre todos los
municipios del A.M.; esta tabla define esa membresía.

## Fuente de la membresía

DANE, Metodología General GEIH v9 (abr. 2016), PDF 9: lista de las 13 grandes ciudades con sus
áreas metropolitanas. Nota 1 del PDF 3: «para la GEIH se entiende por área metropolitana de la
ciudad aquellos municipios que entran en la selección de la muestra». Se usa **estrictamente** la
lista de la GEIH, no el área metropolitana legal:

| Dominio | Municipios |
|---|---|
| Medellín A.M. | Valle de Aburrá: Medellín, Barbosa, Bello, Caldas, Copacabana, Envigado, Girardota, Itagüí, La Estrella, Sabaneta |
| Barranquilla A.M. | Barranquilla, Soledad |
| Bucaramanga A.M. | Bucaramanga, Floridablanca, Girón, Piedecuesta |
| Cali A.M. | Cali, Yumbo |
| Manizales A.M. | Manizales, Villamaría |
| Pereira A.M. | Pereira, Dosquebradas, La Virginia |
| Cúcuta A.M. | Cúcuta, Villa del Rosario, Los Patios, El Zulia |

Las otras 25 capitales (Bogotá, Pasto, Ibagué, Villavicencio, Montería, Cartagena, las 11
ciudades intermedias y las 8 capitales de los nuevos departamentos) son dominios de un solo
municipio. San Andrés y las 8 capitales nuevas no tienen muestra en los microdatos que se
ingieren; figuran para que la partición esté completa, pero no generan estimación directa.

## Columnas

* `CODIGO_DOMINIO`: código DIVIPOLA de la capital (identifica el dominio; es el código que
  `geih_oro` asigna a la muestra del `AREA`)
* `NOMBRE_DOMINIO`: nombre con el que el DANE publica el dominio («Cali A.M.», «Popayán»)
* `TIPO_DOMINIO`: `CIUDAD_AM` (más de un municipio) o `CIUDAD`
* `CODIGO_MUNICIPIO`, `MUNICIPIO`, `CODIGO_DEPARTAMENTO`, `DEPARTAMENTO`: municipio miembro
* `ES_CAPITAL`: `True` en la fila de la capital

`DOMINIOS_GEIH` es la **única** lista de las 32 capitales del proyecto (R-24):
`dim_geih_divipola` toma de esta tabla las filas `ES_CAPITAL`.

## Limitación conocida

En el marco 2005 el `AREA` solo aparece en los registros de cabecera (CLASE = 1): los dominios de
ciudad son **urbanos**, mientras que los indicadores de TerriData son municipales (incluyen la
zona rural). La parte rural de estos municipios pertenece al subuniverso «resto» de la GEIH
(v9, PDF 11), que el proyecto no usa.
```


## Celda 1

```python
import os
import sys

# R-67: `code/` en sys.path para importar `comun` (el notebook está en code/ingesta_datos/<carpeta>/)
_ruta_nb = (
    dbutils.notebook.entry_point.getDbutils()
    .notebook()
    .getContext()
    .notebookPath()
    .get()
)
sys.path.insert(
    0, "/Workspace" + os.path.dirname(os.path.dirname(os.path.dirname(_ruta_nb)))
)

from pyspark.sql import Row
from pyspark.sql.functions import col

from comun.spark_utils import escribir_tabla
from shared.config.dim_config import TBL_DIM_DIVIPOLA, TBL_DIM_DOMINIO
```


## Celda 2

```python
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
```


## Celda 3

```python
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

df_divipola = spark.table(TBL_DIM_DIVIPOLA).select(
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
```

**Salida:**

```
Dominios: 32  |  municipios miembro: 52
Dominios con área metropolitana: 7 (27 municipios)

```
| CODIGO_DOMINIO | NOMBRE_DOMINIO | TIPO_DOMINIO | CODIGO_MUNICIPIO | MUNICIPIO | CODIGO_DEPARTAMENTO | DEPARTAMENTO | ES_CAPITAL |
|---|---|---|---|---|---|---|---|
| 05001 | Medellín A.M. | CIUDAD_AM | 05001 | MEDELLÍN | 05 | ANTIOQUIA | True |
| 05001 | Medellín A.M. | CIUDAD_AM | 05079 | BARBOSA | 05 | ANTIOQUIA | False |
| 05001 | Medellín A.M. | CIUDAD_AM | 05088 | BELLO | 05 | ANTIOQUIA | False |
| 05001 | Medellín A.M. | CIUDAD_AM | 05129 | CALDAS | 05 | ANTIOQUIA | False |
| 05001 | Medellín A.M. | CIUDAD_AM | 05212 | COPACABANA | 05 | ANTIOQUIA | False |
| 05001 | Medellín A.M. | CIUDAD_AM | 05266 | ENVIGADO | 05 | ANTIOQUIA | False |
| 05001 | Medellín A.M. | CIUDAD_AM | 05308 | GIRARDOTA | 05 | ANTIOQUIA | False |
| 05001 | Medellín A.M. | CIUDAD_AM | 05360 | ITAGÜÍ | 05 | ANTIOQUIA | False |
| 05001 | Medellín A.M. | CIUDAD_AM | 05380 | LA ESTRELLA | 05 | ANTIOQUIA | False |
| 05001 | Medellín A.M. | CIUDAD_AM | 05631 | SABANETA | 05 | ANTIOQUIA | False |
| 08001 | Barranquilla A.M. | CIUDAD_AM | 08001 | BARRANQUILLA | 08 | ATLÁNTICO | True |
| 08001 | Barranquilla A.M. | CIUDAD_AM | 08758 | SOLEDAD | 08 | ATLÁNTICO | False |
| 11001 | Bogotá | CIUDAD | 11001 | BOGOTÁ, D.C. | 11 | BOGOTÁ, D.C. | True |
| 13001 | Cartagena | CIUDAD | 13001 | CARTAGENA DE INDIAS | 13 | BOLÍVAR | True |
| 15001 | Tunja | CIUDAD | 15001 | TUNJA | 15 | BOYACÁ | True |
| 17001 | Manizales A.M. | CIUDAD_AM | 17001 | MANIZALES | 17 | CALDAS | True |
| 17001 | Manizales A.M. | CIUDAD_AM | 17873 | VILLAMARÍA | 17 | CALDAS | False |
| 18001 | Florencia | CIUDAD | 18001 | FLORENCIA | 18 | CAQUETÁ | True |
| 19001 | Popayán | CIUDAD | 19001 | POPAYÁN | 19 | CAUCA | True |
| 20001 | Valledupar | CIUDAD | 20001 | VALLEDUPAR | 20 | CESAR | True |
| 23001 | Montería | CIUDAD | 23001 | MONTERÍA | 23 | CÓRDOBA | True |
| 27001 | Quibdó | CIUDAD | 27001 | QUIBDÓ | 27 | CHOCÓ | True |
| 41001 | Neiva | CIUDAD | 41001 | NEIVA | 41 | HUILA | True |
| 44001 | Riohacha | CIUDAD | 44001 | RIOHACHA | 44 | LA GUAJIRA | True |
| 47001 | Santa Marta | CIUDAD | 47001 | SANTA MARTA | 47 | MAGDALENA | True |
| 50001 | Villavicencio | CIUDAD | 50001 | VILLAVICENCIO | 50 | META | True |
| 52001 | Pasto | CIUDAD | 52001 | PASTO | 52 | NARIÑO | True |
| 54001 | Cúcuta A.M. | CIUDAD_AM | 54001 | SAN JOSÉ DE CÚCUTA | 54 | NORTE DE SANTANDER | True |
| 54001 | Cúcuta A.M. | CIUDAD_AM | 54261 | EL ZULIA | 54 | NORTE DE SANTANDER | False |
| 54001 | Cúcuta A.M. | CIUDAD_AM | 54405 | LOS PATIOS | 54 | NORTE DE SANTANDER | False |
| 54001 | Cúcuta A.M. | CIUDAD_AM | 54874 | VILLA DEL ROSARIO | 54 | NORTE DE SANTANDER | False |
| 63001 | Armenia | CIUDAD | 63001 | ARMENIA | 63 | QUINDÍO | True |
| 66001 | Pereira A.M. | CIUDAD_AM | 66001 | PEREIRA | 66 | RISARALDA | True |
| 66001 | Pereira A.M. | CIUDAD_AM | 66170 | DOSQUEBRADAS | 66 | RISARALDA | False |
| 66001 | Pereira A.M. | CIUDAD_AM | 66400 | LA VIRGINIA | 66 | RISARALDA | False |
| 68001 | Bucaramanga A.M. | CIUDAD_AM | 68001 | BUCARAMANGA | 68 | SANTANDER | True |
| 68001 | Bucaramanga A.M. | CIUDAD_AM | 68276 | FLORIDABLANCA | 68 | SANTANDER | False |
| 68001 | Bucaramanga A.M. | CIUDAD_AM | 68307 | GIRÓN | 68 | SANTANDER | False |
| 68001 | Bucaramanga A.M. | CIUDAD_AM | 68547 | PIEDECUESTA | 68 | SANTANDER | False |
| 70001 | Sincelejo | CIUDAD | 70001 | SINCELEJO | 70 | SUCRE | True |
| 73001 | Ibagué | CIUDAD | 73001 | IBAGUÉ | 73 | TOLIMA | True |
| 76001 | Cali A.M. | CIUDAD_AM | 76001 | SANTIAGO DE CALI | 76 | VALLE DEL CAUCA | True |
| 76001 | Cali A.M. | CIUDAD_AM | 76892 | YUMBO | 76 | VALLE DEL CAUCA | False |
| 81001 | Arauca | CIUDAD | 81001 | ARAUCA | 81 | ARAUCA | True |
| 85001 | Yopal | CIUDAD | 85001 | YOPAL | 85 | CASANARE | True |
| 86001 | Mocoa | CIUDAD | 86001 | MOCOA | 86 | PUTUMAYO | True |
| 88001 | San Andrés | CIUDAD | 88001 | SAN ANDRÉS | 88 | ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA | True |
| 91001 | Leticia | CIUDAD | 91001 | LETICIA | 91 | AMAZONAS | True |
| 94001 | Inírida | CIUDAD | 94001 | INÍRIDA | 94 | GUAINÍA | True |
| 95001 | San José del Guaviare | CIUDAD | 95001 | SAN JOSÉ DEL GUAVIARE | 95 | GUAVIARE | True |
| 97001 | Mitú | CIUDAD | 97001 | MITÚ | 97 | VAUPÉS | True |
| 99001 | Puerto Carreño | CIUDAD | 99001 | PUERTO CARREÑO | 99 | VICHADA | True |


## Celda 4

```python
escribir_tabla(df_dominio, TBL_DIM_DOMINIO)
print(f"Tabla escrita: {TBL_DIM_DOMINIO}")
```

**Salida:**

```
Tabla escrita: tesis.dim.dim_dominio_geih

```
