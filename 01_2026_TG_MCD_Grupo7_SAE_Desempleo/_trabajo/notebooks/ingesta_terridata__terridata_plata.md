# ingesta_terridata__terridata_plata


## Celda 0

```python
%md
# Transformación TerriData - Capa Plata: Formato Largo → Formato Ancho (Pivoteado)

Este notebook transforma los datos de **TerriData** desde la capa bronce (formato largo) hacia la capa plata (formato ancho/pivoteado), facilitando análisis multidimensionales y consultas eficientes por indicador.

## Propósito

Convertir la estructura **normalizada** (formato largo) de TerriData en una estructura **desnormalizada** (formato ancho) donde:
* Cada **fila** representa una combinación única de: `ENTIDAD × AÑO × MES`
* Cada **columna** representa un indicador específico (~1,582 indicadores)
* Los valores están correctamente tipificados según su naturaleza (numérico vs cualitativo)

## Tablas de entrada y salida

| Dirección | Tabla |
|-----------|-------|
| Entrada   | `tesis.terridata.terridata_bronce` |
| Salida    | `tesis.terridata.terridata_extendido_plata` |
| Dimensión | `tesis.dim.dim_indicadores` |

## Proceso

1. **Preparar datos base**: unificar `DATO_NUMERICO` y `DATO_CUALITATIVO` → campo `VALOR`
2. **Clasificar indicadores**: `numerico` si ≥ 95 % de valores vienen de `DATO_NUMERICO`, si no `cualitativo`
3. **Pivot dinámico**: `groupBy + pivot + agg(max)` sobre ~1,582 indicadores. Antes se
   exige que (entidad, año, mes, indicador) sea única en bronce (R-20): `max` sobre texto
   elegiría mal si hubiera dos filas; con la llave única solo hay un valor que tomar.
4. **Aplicar tipos**: `try_cast` a `double` para numéricos; mantener `string` para cualitativos
5. **Guardar tabla pivoteada** y **tabla dimensional** de metadatos
6. **Verificaciones de integridad** sobre las tablas Delta ya escritas
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

from pyspark.sql.functions import (
    col,
    when,
    lit,
    max as spark_max,
    expr,
    sum as spark_sum,
)

from shared.config.terridata_config import (
    TBL_BRONCE,
    TBL_PLATA,
    TBL_DIM_INDICADORES,
    COLUMNAS_ID,
    UMBRAL_CLASIFICACION_NUMERICO,
    UMBRAL_RIESGO_CASTEO,
)
from comun.spark_utils import escribir_tabla
from shared.utils.verification_utils import (
    verificar_conservacion_registros,
    verificar_duplicados,
    verificar_llave_unica_bronce,
    verificar_integridad_muestra,
    verificar_calidad_casteo,
    verificar_reclasificacion_indicadores,
    verificar_valores_no_nulos,
)
```


## Celda 2

```python
# False → solo se ejecutan validaciones ligeras (siempre activas)
# True  → además se ejecuta la verificación de conservación de valores no nulos
#          (~10-15 min en tablas de ~30M registros)
EJECUTAR_VALIDACIONES_PESADAS = False
```


## Celda 3

```python
# Leer tabla bronce
df_datos_unificados = spark.table(TBL_BRONCE)

# Eliminar filas donde ambos campos de valor son NULL
df_datos_unificados = df_datos_unificados.filter(
    col("DATO_NUMERICO").isNotNull() | col("DATO_CUALITATIVO").isNotNull()
)

# Unificar DATO_NUMERICO y DATO_CUALITATIVO → campo VALOR (string)
# Prioridad: DATO_NUMERICO sobre DATO_CUALITATIVO
df_datos_unificados = df_datos_unificados.select(
    "CODIGO_DEPARTAMENTO",
    "DEPARTAMENTO",
    "CODIGO_ENTIDAD",
    "ENTIDAD",
    col("ANO").cast("int").alias("ANO"),
    col("MES").cast("int").alias("MES"),
    "CODIGO_INDICADOR",
    "INDICADOR",
    "DIMENSION",
    "SUBCATEGORIA",
    "UNIDAD_MEDIDA",
    when(col("DATO_NUMERICO").isNotNull(), col("DATO_NUMERICO").cast("string"))
    .when(col("DATO_CUALITATIVO").isNotNull(), col("DATO_CUALITATIVO"))
    .otherwise(lit(None))
    .alias("VALOR"),
)
```


## Celda 4

```python
# Criterio: si >= UMBRAL_CLASIFICACION_NUMERICO % de valores vienen de DATO_NUMERICO → "numerico"
# "preliminar" en DATO_CUALITATIVO se ignora (es anotación de calidad, no valor real)

df_bronce = spark.table(TBL_BRONCE)

df_clasificacion = (
    df_bronce.filter(
        col("DATO_NUMERICO").isNotNull() | col("DATO_CUALITATIVO").isNotNull()
    )
    .groupBy("CODIGO_INDICADOR")
    .agg(
        spark_sum(when(col("DATO_NUMERICO").isNotNull(), 1).otherwise(0)).alias(
            "count_numerico"
        ),
        spark_sum(
            when(
                col("DATO_CUALITATIVO").isNotNull()
                & (col("DATO_CUALITATIVO") != "preliminar"),
                1,
            ).otherwise(0)
        ).alias("count_cualitativo"),
    )
)

df_clasificacion = (
    df_clasificacion.withColumn(
        "total_valores", col("count_numerico") + col("count_cualitativo")
    )
    .withColumn(
        "porcentaje_numerico", col("count_numerico") / col("total_valores") * 100
    )
    .withColumn(
        "TIPO_DATO",
        when(
            col("porcentaje_numerico") >= UMBRAL_CLASIFICACION_NUMERICO, lit("numerico")
        ).otherwise(lit("cualitativo")),
    )
)

print("Clasificación de indicadores:")
print("=" * 60)
display(df_clasificacion.groupBy("TIPO_DATO").count().orderBy("TIPO_DATO"))

# Un único collect() evita releer bronce en Paso 4 y en las verificaciones
clasificacion_completa = df_clasificacion.collect()

tipo_indicador_dict = {
    row.CODIGO_INDICADOR: row.TIPO_DATO for row in clasificacion_completa
}

# DataFrame para el LEFT JOIN de metadatos en Paso 5 (construido desde Python, sin releer bronce)
df_tipo_indicador = spark.createDataFrame(
    [(row.CODIGO_INDICADOR, row.TIPO_DATO) for row in clasificacion_completa],
    ["CODIGO_INDICADOR", "TIPO_DATO"],
)
```

**Salida:**

```
Clasificación de indicadores:
============================================================

```
| TIPO_DATO | count |
|---|---|
| cualitativo | 130 |
| numerico | 1452 |


## Celda 5

```python
df_indicadores = (
    df_datos_unificados.select("CODIGO_INDICADOR")
    .distinct()
    .orderBy("CODIGO_INDICADOR")
)

indicadores = [row.CODIGO_INDICADOR for row in df_indicadores.collect()]

print(f"Total de indicadores a pivotar: {len(indicadores)}")
```

**Salida:**

```
Total de indicadores a pivotar: 1582

```


## Celda 6

```python
print(f"Pivotando {len(indicadores)} indicadores...")
print("Este proceso puede tomar varios minutos...")

# R-20: con la llave única en bronce, max(VALOR) toma el único valor de cada celda
verificar_llave_unica_bronce(df_datos_unificados)

df_pivoteado = (
    df_datos_unificados.groupBy(*COLUMNAS_ID)
    .pivot("CODIGO_INDICADOR", indicadores)
    .agg(spark_max("VALOR"))
)

# Aplicar tipos de datos correctos: double para numéricos, string para cualitativos
print("\nAplicando tipos de datos a columnas de indicador...")

columnas_con_tipo = [col(c) for c in COLUMNAS_ID]

count_numerico = 0
count_cualitativo = 0

for col_name in df_pivoteado.columns:
    if col_name not in COLUMNAS_ID:
        tipo = tipo_indicador_dict.get(col_name, "cualitativo")
        if tipo == "numerico":
            columnas_con_tipo.append(
                expr(f"try_cast(`{col_name}` as double)").alias(col_name)
            )
            count_numerico += 1
        else:
            columnas_con_tipo.append(col(f"`{col_name}`"))
            count_cualitativo += 1

df_pivoteado = df_pivoteado.select(columnas_con_tipo)

print(f"\n✅ Tipos aplicados:")
print(f"  - Numéricos (double con try_cast): {count_numerico}")
print(f"  - Cualitativos (string):           {count_cualitativo}")
print(
    f"\n⚠️  Valores no numéricos en columnas numéricas (ej: 'preliminar') → NULL con try_cast."
)
```

**Salida:**

```
Pivotando 1582 indicadores...
Este proceso puede tomar varios minutos...
✅ Llave (entidad, año, mes, indicador) única en bronce: el pivote es inequívoco

Aplicando tipos de datos a columnas de indicador...

✅ Tipos aplicados:
  - Numéricos (double con try_cast): 1452
  - Cualitativos (string):           130

⚠️  Valores no numéricos en columnas numéricas (ej: 'preliminar') → NULL con try_cast.

```


## Celda 7

```python
n_cols = len(df_pivoteado.columns)

escribir_tabla(df_pivoteado, TBL_PLATA)

n_filas = spark.table(TBL_PLATA).count()

print("\n" + "=" * 60)
print("✅ TABLA PIVOTEADA GUARDADA EXITOSAMENTE")
print("=" * 60)
print(f"\nTabla: {TBL_PLATA}")
print(f"\nESTADÍSTICAS:")
print(f"  - Filas:    {n_filas:,}")
n_id = len(COLUMNAS_ID)
print(
    f"  - Columnas: {n_cols}  ({n_id} de identificación + {n_cols - n_id} indicadores)"
)
```

**Salida:**

```

============================================================
✅ TABLA PIVOTEADA GUARDADA EXITOSAMENTE
============================================================

Tabla: tesis.terridata.terridata_extendido_plata

ESTADÍSTICAS:
  - Filas:    147,026
  - Columnas: 1588  (6 de identificación + 1582 indicadores)

```


## Celda 8

```python
# Las verificaciones ligeras SIEMPRE se ejecutan — leen desde las tablas Delta ya escritas.
# La verificación pesada se controla con EJECUTAR_VALIDACIONES_PESADAS (celda de configuración).

df_bronce_v = spark.table(TBL_BRONCE)
df_plata_v = spark.table(TBL_PLATA)

resultados = {
    "Conservación de registros": verificar_conservacion_registros(df_bronce_v, n_filas),
    "Duplicados en plata": verificar_duplicados(df_plata_v, n_filas),
    "Integridad de muestra": verificar_integridad_muestra(df_bronce_v, df_plata_v),
    "Calidad de casteo": verificar_calidad_casteo(clasificacion_completa),
    "Reclasificación": verificar_reclasificacion_indicadores(
        spark, tipo_indicador_dict
    ),
}

if EJECUTAR_VALIDACIONES_PESADAS:
    df_largo_v = (
        spark.table(TBL_BRONCE)
        .filter(col("DATO_NUMERICO").isNotNull() | col("DATO_CUALITATIVO").isNotNull())
        .select(
            when(col("DATO_NUMERICO").isNotNull(), col("DATO_NUMERICO").cast("string"))
            .when(col("DATO_CUALITATIVO").isNotNull(), col("DATO_CUALITATIVO"))
            .otherwise(lit(None))
            .alias("VALOR")
        )
    )
    resultados["Valores no nulos"] = verificar_valores_no_nulos(df_largo_v, df_plata_v)
else:
    print("ℹ️  Verificación pesada omitida (EJECUTAR_VALIDACIONES_PESADAS = False)\n")

print("\n" + "=" * 60)
print("RESUMEN DE VERIFICACIONES")
print("=" * 60)
for nombre, resultado in resultados.items():
    estado = "✅ PASS" if resultado else "❌ FAIL"
    print(f"  {estado}  {nombre}")

if all(resultados.values()):
    print("\n✅ TODAS LAS VERIFICACIONES PASARON")
else:
    fallidas = [n for n, r in resultados.items() if not r]
    print(f"\n❌ FALLARON: {', '.join(fallidas)}")
```

**Salida:**

```
============================================================
VERIFICACIÓN 1: CONSERVACIÓN DE REGISTROS
============================================================
Combinaciones únicas con valor en BRONCE: 147,026
Filas en PLATA:                           147,026
✅ CORRECTO: El número de registros se conservó
============================================================
VERIFICACIÓN 2: DUPLICADOS EN PLATA
============================================================
Total filas:   147,026
Claves únicas: 147,026
✅ CORRECTO: No hay duplicados
============================================================
VERIFICACIÓN 3: INTEGRIDAD DE MUESTRA ALEATORIA
============================================================
Verificando 10 combinaciones aleatorias...

  ✅ 05004 / 2000-0 / 010010001: '05004'
  ✅ 95200 / 2000-0 / 010010001: '95200'
  ✅ 19364 / 2000-0 / 010010003: 'Oriente'
  ✅ 44078 / 2000-0 / 010010006: '6'
  ✅ 68322 / 2018-12 / 010010006: '6'
  ✅ 50318 / 2018-12 / 010010006: '6'
  ✅ 05042 / 2018-12 / 010010006: '5'
  ✅ 05658 / 2019-12 / 010010006: '6'
  ✅ 08372 / 2019-12 / 010010006: '6'
  ✅ 18592 / 2021-12 / 010010006: '6'

✅ CORRECTO: Las 10 muestras coinciden
============================================================
VERIFICACIÓN 4: CALIDAD DE CASTEO NUMÉRICO
============================================================
Indicadores numéricos:                          1452
  Con valores cualitativos (→ NULL tras cast):  11
  Valores en riesgo: 261 de 10,809,352 (0.002%)

Top 10 indicadores con más valores en riesgo:
  - 120100001: 33 valores (2.9%)
  - 120100002: 33 valores (2.9%)
  - 120140001: 33 valores (2.9%)
  - 120140002: 33 valores (2.9%)
  - 120140003: 33 valores (2.9%)
  - 120140004: 33 valores (2.9%)
  - 120100003: 31 valores (2.7%)
  - 120100004: 29 valores (2.5%)
  - 050010004: 1 valores (0.0%)
  - 070130012: 1 valores (0.0%)

✅ CORRECTO: Riesgo (0.002%) dentro del umbral (5.0%)
============================================================
VERIFICACIÓN 5: RECLASIFICACIÓN DE INDICADORES
============================================================
Indicadores nuevos:             0
Indicadores eliminados:         0
Indicadores que cambiaron tipo: 0

✅ CORRECTO: Ningún indicador cambió de tipo
ℹ️  Verificación pesada omitida (EJECUTAR_VALIDACIONES_PESADAS = False)


============================================================
RESUMEN DE VERIFICACIONES
============================================================
  ✅ PASS  Conservación de registros
  ✅ PASS  Duplicados en plata
  ✅ PASS  Integridad de muestra
  ✅ PASS  Calidad de casteo
  ✅ PASS  Reclasificación

✅ TODAS LAS VERIFICACIONES PASARON

```


## Celda 9

```python
df_metadatos = (
    df_datos_unificados.select(
        "CODIGO_INDICADOR", "INDICADOR", "DIMENSION", "SUBCATEGORIA", "UNIDAD_MEDIDA"
    )
    .distinct()
    .join(df_tipo_indicador, on="CODIGO_INDICADOR", how="left")
    .orderBy("CODIGO_INDICADOR")
)

print(f"Total de indicadores documentados: {df_metadatos.count()}")
display(df_metadatos.groupBy("TIPO_DATO").count().orderBy("TIPO_DATO"))

escribir_tabla(df_metadatos, TBL_DIM_INDICADORES)

print(f"\n✅ Tabla dimensional guardada: {TBL_DIM_INDICADORES}")
```

**Salida:**

```
Total de indicadores documentados: 1582

```
| TIPO_DATO | count |
|---|---|
| cualitativo | 130 |
| numerico | 1452 |
```

✅ Tabla dimensional guardada: tesis.dim.dim_indicadores

```
