# dimensiones__dim_divipola


## Celda 0

```python
%md
# Tabla Dimensional DIVIPOLA - División Político-Administrativa de Colombia

Este notebook crea la **tabla dimensional de geografía** basada en la codificación DIVIPOLA (División Político-Administrativa) del DANE, que contiene la estructura administrativa de Colombia con departamentos, municipios y sus coordenadas geográficas.

## Propósito
Generar la tabla `tesis.dim.dim_divipola` que sirve como **dimensión geográfica** para los análisis de la GEIH, permitiendo:
* Mapear códigos de departamento/municipio a nombres legibles
* Obtener coordenadas geográficas (latitud/longitud) para visualizaciones
* Clasificar entidades por tipo (Municipio, Isla, Área no municipalizada)

## ¿Qué es DIVIPOLA?

**DIVIPOLA** es la codificación estándar del DANE (Departamento Administrativo Nacional de Estadística) para identificar unidades político-administrativas en Colombia:

* **Código de Departamento**: 2 dígitos (ej: 05 = Antioquia, 11 = Bogotá D.C.)
* **Código de Municipio**: 5 dígitos (código departamento + 3 dígitos del municipio)
  - Ejemplo: 05001 = Medellín (05 = Antioquia, 001 = capital departamental)
  - Ejemplo: 11001 = Bogotá D.C.

## Fuente de Datos

**Ubicación**: `/Volumes/tesis/dim/divipola/*.csv`

**Formato**: CSV con delimitador coma (`,`)

**Estructura del archivo fuente**:
```
Código Departamento,Nombre Departamento,Código Municipio,Nombre Municipio,Tipo,longitud,Latitud
05,ANTIOQUIA,05001,MEDELLÍN,Municipio,-75.5635932,6.2476376
11,BOGOTÁ D.C.,11001,BOGOTÁ D.C.,Municipio,-74.0817500,4.6097100
```

## Campos de Salida

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `CODIGO_DEPARTAMENTO` | string | Código DIVIPOLA del departamento (2 dígitos) |
| `DEPARTAMENTO` | string | Nombre del departamento |
| `CODIGO_MUNICIPIO` | string | Código DIVIPOLA del municipio (5 dígitos) |
| `MUNICIPIO` | string | Nombre del municipio |
| `DIMENSION` | string | Tipo de entidad: Municipio, Isla, Área no municipalizada |
| `LONGITUD` | double | Coordenada de longitud (grados decimales) |
| `LATITUD` | double | Coordenada de latitud (grados decimales) |

## Transformaciones Aplicadas

1. **Renombrado de columnas**: Mapeo de nombres originales a nombres estandarizados en mayúsculas sin espacios
2. **Normalización de coordenadas**:
   - Reemplazo de comas (`,`) por puntos (`.`) en valores numéricos
   - Conversión a tipo `double` para latitud y longitud
3. **Preservación de tipos**: Códigos se mantienen como `string` (importante: 05 ≠ 5)

## Uso en el Pipeline GEIH

Esta tabla dimensional se une con las tablas de la capa ORO para:
* **Enriquecer datos de mercado laboral** con nombres geográficos legibles
* **Habilitar análisis espaciales** usando coordenadas
* **Permitir agregaciones** por departamento o municipio

### Ejemplo de Join:
`geih_oro` la usa para el nombre del departamento y usa `tesis.dim.dim_geih_divipola`
(derivada de esta, ver `dim_geih_divipola.py`) para el municipio, porque esa trae
`CODIGO_AREA_GEIH`:
```python
# En geih_oro:
# 1. Nombre del departamento, desde esta tabla (R-24: todos los departamentos)
.join(departamentos.alias("div_dep"),
      col("CODIGO_DPTO") == col("div_dep.CODIGO_DEPARTAMENTO"))

# 2. Municipio, desde dim_geih_divipola (solo las 32 capitales)
.join(geih_div.alias("div_mun"),
      col("CODIGO_AREA") == col("div_mun.CODIGO_AREA_GEIH"))
```

## Nota sobre Códigos

Los códigos DIVIPOLA deben manejarse como **strings**, no como enteros:
* ✅ `"05"` (Antioquia)
* ❌ `5` (pierde el cero inicial)

Esto es crítico para joins correctos con tablas GEIH que usan la misma codificación.
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

# Importar funciones de PySpark necesarias para la transformación
from pyspark.sql.functions import (
    col,  # Referenciar columnas para renombrado y transformaciones
    regexp_replace,  # Reemplazar patrones de texto (comas por puntos en coordenadas)
)

from comun.spark_utils import escribir_tabla
from shared.config.dim_config import RUTA_DIVIPOLA_CSV, TBL_DIM_DIVIPOLA
```


## Celda 2

```python
# ============================================================================
# MAPEO DE COLUMNAS: NOMBRES ORIGINALES → NOMBRES ESTANDARIZADOS
# ============================================================================
# Diccionario que mapea los nombres de columnas del CSV fuente (con espacios
# y caracteres especiales) a nombres estandarizados para la base de datos:
# - Todo en mayúsculas
# - Sin espacios (se reemplazan por guiones bajos)
# - Sin tildes en nombres de campo (aunque los valores sí las conservan)
# - Nombres descriptivos y concisos

col_map = {
    "Código Departamento": "CODIGO_DEPARTAMENTO",  # Código DIVIPOLA del departamento (2 dígitos)
    "Nombre Departamento": "DEPARTAMENTO",  # Nombre completo del departamento
    "Código Municipio": "CODIGO_MUNICIPIO",  # Código DIVIPOLA del municipio (5 dígitos)
    "Nombre Municipio": "MUNICIPIO",  # Nombre completo del municipio
    "Tipo: Municipio / Isla / Área no municipalizada": "DIMENSION",  # Clasificación administrativa
    "longitud": "LONGITUD",  # Coordenada de longitud (grados decimales)
    "Latitud": "LATITUD",  # Coordenada de latitud (grados decimales)
}
```


## Celda 3

```python
# ============================================================================
# LECTURA Y TRANSFORMACIÓN DE DATOS DIVIPOLA
# ============================================================================

# --- PASO 1: LEER ARCHIVO CSV ---
# Lee archivo CSV de DIVIPOLA desde volumen de Unity Catalog
# - header="true": Primera fila contiene nombres de columnas
# - delimiter=",": Archivo separado por comas
# - /*.csv: Lee todos los archivos CSV en el directorio
df = spark.read.option("header", "true").option("delimiter", ",").csv(RUTA_DIVIPOLA_CSV)

# --- PASO 2: RENOMBRAR COLUMNAS ---
# Crear lista de expresiones para renombrar todas las columnas
# según el diccionario col_map definido anteriormente
map_select = [col(column).alias(col_map.get(column)) for column in df.columns]

# --- PASO 3: APLICAR RENOMBRADO Y NORMALIZAR COORDENADAS ---
# 1. Seleccionar todas las columnas con sus nuevos nombres
# 2. Normalizar LATITUD: reemplazar comas por puntos y convertir a double
#    Ejemplo: "6,2476376" → "6.2476376" → 6.2476376 (double)
# 3. Normalizar LONGITUD: mismo proceso que latitud
#    Ejemplo: "-75,5635932" → "-75.5635932" → -75.5635932 (double)
df_select = (
    df.select(*map_select)
    .withColumn("LATITUD", regexp_replace(col("LATITUD"), ",", ".").cast("double"))
    .withColumn("LONGITUD", regexp_replace(col("LONGITUD"), ",", ".").cast("double"))
)
```


## Celda 4

```python
# ============================================================================
# PERSISTENCIA DE TABLA DIMENSIONAL
# ============================================================================
# Guardar tabla dimensional DIVIPOLA en Unity Catalog
# - Esquema: tesis.dim (catálogo.esquema para tablas dimensionales)
# - Tabla: dim_divipola
# - mode("overwrite"): Reemplaza la tabla existente completamente
# - overwriteSchema: Permite cambios en la estructura de la tabla
#
# Resultado: Tabla dimensional lista para joins con tablas de hechos (GEIH)

escribir_tabla(df_select, TBL_DIM_DIVIPOLA)
```
