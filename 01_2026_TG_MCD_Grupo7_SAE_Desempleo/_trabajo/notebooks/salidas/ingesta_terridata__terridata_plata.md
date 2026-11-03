# ingesta_terridata__terridata_plata


## Celda 0



## Celda 1



## Celda 2



## Celda 3



## Celda 4


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


**Salida:**

```
Total de indicadores a pivotar: 1582

```


## Celda 6


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
