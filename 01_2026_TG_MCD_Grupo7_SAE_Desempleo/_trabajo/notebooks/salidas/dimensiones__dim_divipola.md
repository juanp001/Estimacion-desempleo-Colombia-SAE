# dimensiones__dim_divipola


## Celda 0

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

## Nota sobre Códigos

Los códigos DIVIPOLA deben manejarse como **strings**, no como enteros:
* ✅ `"05"` (Antioquia)
* ❌ `5` (pierde el cero inicial)

Esto es crítico para joins correctos con tablas GEIH que usan la misma codificación.
```


## Celda 1



## Celda 2



## Celda 3



## Celda 4

