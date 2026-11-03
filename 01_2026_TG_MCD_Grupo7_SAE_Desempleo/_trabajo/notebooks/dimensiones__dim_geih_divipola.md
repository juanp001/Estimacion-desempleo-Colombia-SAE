# dimensiones__dim_geih_divipola


## Celda 0

```python
%md
# Tabla Dimensional GEIH-DIVIPOLA - Traducción del AREA de la GEIH a municipio

Crea `tesis.dim.dim_geih_divipola`: una fila por cada una de las **32 capitales** de la GEIH,
con el código `CODIGO_AREA_GEIH` que trae la encuesta en el campo `AREA`.

## Qué es `CODIGO_AREA_GEIH`

En los microdatos de la GEIH el campo `AREA` es el código de **departamento** de la ciudad
(`76` = Cali A.M.), y cada departamento tiene una sola ciudad en la muestra. Por eso
`CODIGO_AREA_GEIH` es igual a `CODIGO_DEPARTAMENTO` de la capital, y el mapeo `AREA` → capital
es correcto: con él la estimación directa de los 23 dominios con muestra coincide con la que
publica el DANE (anexo «Mercado laboral según proyecciones CNPV 2018»).

## De dónde sale la lista de capitales (R-24)

Las capitales se definen **una sola vez**, en `DOMINIOS_GEIH` de `dim_dominio_geih.py` (DANE,
Metodología GEIH v9, PDF 9-10: 13 ciudades con A.M., 11 intermedias y 8 capitales nuevas).
Este notebook toma las filas `ES_CAPITAL` de `tesis.dim.dim_dominio_geih` y les agrega las
coordenadas de `tesis.dim.dim_divipola`; por eso en el job `dimensiones` corre después de
`dim_dominio_geih`. Antes la lista estaba escrita a mano en los dos notebooks.

Validaciones: 32 filas y un `CODIGO_AREA_GEIH` distinto por fila (si dos capitales
compartieran departamento, el join de `geih_oro` duplicaría personas).

## Columnas
* `CODIGO_DEPARTAMENTO`, `DEPARTAMENTO`: departamento de la capital
* `CODIGO_AREA_GEIH`: código `AREA` de la GEIH (= `CODIGO_DEPARTAMENTO`)
* `CODIGO_MUNICIPIO`, `MUNICIPIO`: la capital (Bogotá D.C. con `11001`; Yopal con `85001`)
* `LONGITUD`, `LATITUD`

## Uso
`geih_oro` la une por `CODIGO_AREA` para asignar `CODIGO_MUNICIPIO` y `MUNICIPIO` (constante
`TBL_DIM_GEIH_DIVIPOLA`). Fuera de estas 32 áreas `MUNICIPIO` queda NULL. El nombre del departamento
ya no sale de aquí sino de `dim_divipola` (R-24), así que no queda NULL en departamentos sin
capital en la lista (p. ej. Cundinamarca, 25). `preprocesamiento` la usa para traer el código
de área de cada dominio.
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

from pyspark.sql.functions import col

from comun.spark_utils import escribir_tabla
from shared.config.dim_config import (
    TBL_DIM_DIVIPOLA,
    TBL_DIM_DOMINIO,
    TBL_DIM_GEIH_DIVIPOLA,
)
```


## Celda 2

```python
N_CAPITALES = 32

capitales = (
    spark.table(TBL_DIM_DOMINIO).filter(col("ES_CAPITAL")).select("CODIGO_MUNICIPIO")
)

df_geih_divipola = (
    spark.table(TBL_DIM_DIVIPOLA)
    .join(capitales, "CODIGO_MUNICIPIO", "inner")
    .select(
        "CODIGO_DEPARTAMENTO",
        "DEPARTAMENTO",
        # El AREA de la GEIH es el código de departamento de la ciudad
        col("CODIGO_DEPARTAMENTO").alias("CODIGO_AREA_GEIH"),
        "CODIGO_MUNICIPIO",
        "MUNICIPIO",
        "LONGITUD",
        "LATITUD",
    )
)

n_filas = df_geih_divipola.count()
n_areas = df_geih_divipola.select("CODIGO_AREA_GEIH").distinct().count()
if n_filas != N_CAPITALES or n_areas != N_CAPITALES:
    raise ValueError(
        f"Se esperaban {N_CAPITALES} capitales con CODIGO_AREA_GEIH único; "
        f"hay {n_filas} filas y {n_areas} códigos de área"
    )
print(f"Capitales GEIH: {n_filas}  |  códigos de área distintos: {n_areas}")
```

**Salida:**

```
Capitales GEIH: 32  |  códigos de área distintos: 32

```


## Celda 3

```python
escribir_tabla(df_geih_divipola, TBL_DIM_GEIH_DIVIPOLA)
print(f"Tabla escrita: {TBL_DIM_GEIH_DIVIPOLA}")
```

**Salida:**

```
Tabla escrita: tesis.dim.dim_geih_divipola

```
