# ingesta_geih__geih_plata


## Celda 0

```python
%md
# Transformación de Datos GEIH - Capa Plata (Silver)

Consolida los datos bronce en tablas estandarizadas que unifican marco antiguo y
marco nuevo bajo una misma estructura de campos núcleo.

## Tablas generadas
| Tabla | Campos específicos |
|---|---|
| `caracteristicas_generales_consolidado` | SEXO, EDAD |
| `fuerza_trabajo_consolidado` | PEA, PEI, PET |
| `no_ocupados_consolidado` | DESOCUPADO |
| `ocupados_consolidado` | OCUPADO |
| `dim_fex` | ANO, MES, FEX_C18 |

## Diferencias entre marcos
* **Marco nuevo**: PERIODO, MES y FEX_C18 vienen directamente de bronce.
* **Marco antiguo**: PERIODO y PER se extraen del nombre de archivo con regex;
  FEX_C_2011 requiere reemplazar comas por puntos.

## Uniones y llave (R-22)
* Marco nuevo y antiguo se unen por nombre (`unionByName`), no por posición: reordenar
  `CAMPOS_NUCLEO_*` ya no puede correr columnas sin error.
* `FEX` se castea a double en los dos marcos y `FEX_C18` de `dim_fex` recibe el mismo
  reemplazo de comas.
* `PK` = `PERIODO_DIRECTORIO_SECUENCIA_P_ORDEN` (con separador), igual en `dim_fex`.

## Lógica especial — fuerza de trabajo marco antiguo
LEFT JOIN entre fuerza_trabajo e inactivos: PEA = 1 si la persona no aparece
en la tabla de inactivos (PEI es NULL o vacío).
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


from pyspark.sql.functions import col, when, expr, regexp_replace

from shared.config.geih_config import (
    TBL_CG_BRONCE,
    TBL_FT_BRONCE,
    TBL_NO_BRONCE,
    TBL_OC_BRONCE,
    TBL_FEX_BRONCE,
    TBL_CG_CAB_MA,
    TBL_CG_RESTO_MA,
    TBL_FT_CAB_MA,
    TBL_FT_RESTO_MA,
    TBL_IN_CAB_MA,
    TBL_IN_RESTO_MA,
    TBL_NO_CAB_MA,
    TBL_NO_RESTO_MA,
    TBL_OC_CAB_MA,
    TBL_OC_RESTO_MA,
    TBL_CG_PLATA,
    TBL_FT_PLATA,
    TBL_NO_PLATA,
    TBL_OC_PLATA,
    TBL_FEX_PLATA,
)
from shared.transformations.campos_nucleo import (
    CAMPOS_NUCLEO_MARCO_NUEVO,
    CAMPOS_NUCLEO_MARCO_ANTIGUO,
    llave_persona,
)
from comun.spark_utils import escribir_tabla
```


## Celda 2

```python
%md
# Características Generales
```


## Celda 3

```python
df_cg_plata = spark.table(TBL_CG_BRONCE).select(
    *CAMPOS_NUCLEO_MARCO_NUEVO,
    when(col("P3271") == 1, "MASCULINO")
    .when(col("P3271") == 2, "FEMENINO")
    .alias("SEXO"),
    col("P6040").cast("int").alias("EDAD"),
    # R-52: sin ANO_NACIMIENTO ni MES_NACIMIENTO, que no llegaban a oro
)
```


## Celda 4

```python
# En marco antiguo los códigos de sexo vienen como string ("1", "2")
# y los demás campos pueden traer valores inválidos — se usa try_cast
select_fields_cg_antiguo = [
    when(col("P6020") == "1", "MASCULINO")
    .when(col("P6020") == "2", "FEMENINO")
    .alias("SEXO"),
    expr("try_cast(P6040 as int)").alias("EDAD"),
]

df_cg_cabecera_plata = spark.table(TBL_CG_CAB_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, *select_fields_cg_antiguo
)
df_cg_resto_plata = spark.table(TBL_CG_RESTO_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, *select_fields_cg_antiguo
)

# Marco antiguo: solo cabecera y resto (R-21: la sección área no se carga en bronce)
df_cg_consolidado = df_cg_plata.unionByName(df_cg_cabecera_plata).unionByName(
    df_cg_resto_plata
)
escribir_tabla(df_cg_consolidado, TBL_CG_PLATA)
```


## Celda 5

```python
%md
# Fuerza de Trabajo
```


## Celda 6

```python
df_ft_plata = spark.table(TBL_FT_BRONCE).select(
    *CAMPOS_NUCLEO_MARCO_NUEVO,
    col("FT").alias("PEA"),
    col("FFT").alias("PEI"),
    col("PET"),
)
```


## Celda 7

```python
# El módulo FT solo trae personas de la PET: FT = "1" en todas las filas (en resto lo fija
# geih_bronce). R-21: en vez de normalizar "" → "1", se verifica que así sea.
df_ft_cabecera = spark.table(TBL_FT_CAB_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("FT").alias("PET")
)
df_ft_resto = spark.table(TBL_FT_RESTO_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("FT").alias("PET")
)
for nombre, df_ft in [("cabecera", df_ft_cabecera), ("resto", df_ft_resto)]:
    n_sin_pet = df_ft.filter(~col("PET").eqNullSafe("1")).count()
    if n_sin_pet:
        raise ValueError(
            f"Fuerza de trabajo {nombre}: {n_sin_pet} filas con FT distinto de '1'"
        )

df_i_cabecera = spark.table(TBL_IN_CAB_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("INI").alias("PEI")
)
df_i_resto = spark.table(TBL_IN_RESTO_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("INI").alias("PEI")
)

df_ft_ma = df_ft_cabecera.unionByName(df_ft_resto)
df_i_ma = df_i_cabecera.unionByName(df_i_resto)
```


## Celda 8

```python
# PEA = 1 si la persona NO aparece en inactivos (PEI es NULL o vacío)
df_ft_ma_plata = df_ft_ma.join(df_i_ma, "PK", "left").select(
    df_ft_ma["*"],
    df_i_ma["PEI"],
    when((df_i_ma["PEI"].isNull()) | (df_i_ma["PEI"] == ""), 1)
    .otherwise(0)
    .alias("PEA"),
)

df_ft_consolidado = df_ft_plata.unionByName(df_ft_ma_plata)
escribir_tabla(df_ft_consolidado, TBL_FT_PLATA)
```


## Celda 9

```python
%md
# No Ocupados
```


## Celda 10

```python
df_no_plata = spark.table(TBL_NO_BRONCE).select(
    *CAMPOS_NUCLEO_MARCO_NUEVO,
    col("DSI").alias("DESOCUPADO"),
)
```


## Celda 11

```python
df_no_cabecera_plata = spark.table(TBL_NO_CAB_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("DSI").alias("DESOCUPADO")
)
df_no_resto_plata = spark.table(TBL_NO_RESTO_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("DSI").alias("DESOCUPADO")
)

df_no_consolidado = df_no_plata.unionByName(df_no_cabecera_plata).unionByName(
    df_no_resto_plata
)
escribir_tabla(df_no_consolidado, TBL_NO_PLATA)
```


## Celda 12

```python
%md
# Ocupados
```


## Celda 13

```python
df_oc_plata = spark.table(TBL_OC_BRONCE).select(
    *CAMPOS_NUCLEO_MARCO_NUEVO,
    col("OCI").alias("OCUPADO"),
)
```


## Celda 14

```python
# Marco antiguo: solo cabecera y resto (R-21: la sección área no se carga en bronce)
df_oc_cabecera_plata = spark.table(TBL_OC_CAB_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("OCI").alias("OCUPADO")
)
df_oc_resto_plata = spark.table(TBL_OC_RESTO_MA).select(
    *CAMPOS_NUCLEO_MARCO_ANTIGUO, col("OCI").alias("OCUPADO")
)

df_oc_consolidado = df_oc_plata.unionByName(df_oc_cabecera_plata).unionByName(
    df_oc_resto_plata
)
escribir_tabla(df_oc_consolidado, TBL_OC_PLATA)
```


## Celda 15

```python
%md
# Factores de Expansión
```


## Celda 16

```python
df_fex = spark.table(TBL_FEX_BRONCE).select(
    # R-22: misma llave que características generales (TIME_FEXC es el PERIODO AAAAMM)
    llave_persona(
        col("TIME_FEXC"), col("DIRECTORIO"), col("SECUENCIA_P"), col("ORDEN")
    ).alias("PK"),
    "DIRECTORIO",
    "SECUENCIA_P",
    "ORDEN",
    col("Ano").cast("int").alias("ANO"),
    col("Mes").cast("int").alias("MES"),
    regexp_replace(col("FEX_C18"), ",", ".").cast("double").alias("FEX_C18"),
)

escribir_tabla(df_fex, TBL_FEX_PLATA)
```
