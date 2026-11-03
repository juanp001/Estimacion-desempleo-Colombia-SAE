# ingesta_terridata__terridata_bronce


## Celda 0

```python
%md
# Ingesta de Datos TerriData - Capa Bronce

Este notebook realiza la ingesta y carga inicial de los datos de **TerriData** en la capa bronce del lakehouse, seleccionando los campos que usan las etapas siguientes.

## ¿Qué es TerriData?

**TerriData** es el sistema de información geográfica y estadística del **Departamento Nacional de Planeación (DNP)** de Colombia que consolida indicadores sociales, económicos y demográficos a nivel territorial (departamentos y municipios).

## Proceso

1. Lee archivos Parquet consolidados desde `/Volumes/tesis/terridata/terridata_archivos/consolidado/`
2. Selecciona los campos de `CAMPOS_BRONCE` (R-52: sin columnas `*_NORMALIZADO`, que nadie usaba)
3. Guarda la tabla resultante en `tesis.terridata.terridata_bronce`

## Tabla de salida: `tesis.terridata.terridata_bronce`

| Campo | Descripción |
|-------|-------------|
| `CODIGO_DEPARTAMENTO` | Código DIVIPOLA del departamento |
| `DEPARTAMENTO` | Nombre original con tildes |
| `CODIGO_ENTIDAD` | Código del municipio o entidad |
| `ENTIDAD` | Nombre original con tildes |
| `DIMENSION` | Categoría temática del indicador |
| `SUBCATEGORIA` | Subcategoría dentro de la dimensión |
| `INDICADOR` | Nombre descriptivo del indicador |
| `CODIGO_INDICADOR` | Código único del indicador |
| `DATO_NUMERICO` | Valor numérico del indicador |
| `DATO_CUALITATIVO` | Valor cualitativo del indicador |
| `ANO` | Año del dato |
| `MES` | Mes del dato |
| `FUENTE` | Fuente de información |
| `UNIDAD_MEDIDA` | Unidad de medida del indicador |
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


from shared.config.terridata_config import VOL_CONSOLIDADO, TBL_BRONCE
from shared.transformations.normalizacion import CAMPOS_BRONCE
from comun.spark_utils import leer_parquet, escribir_tabla
```


## Celda 2

```python
df = leer_parquet(spark, VOL_CONSOLIDADO)
df_normalizado = df.select(*CAMPOS_BRONCE)
```


## Celda 3

```python
escribir_tabla(df_normalizado, TBL_BRONCE)
```
