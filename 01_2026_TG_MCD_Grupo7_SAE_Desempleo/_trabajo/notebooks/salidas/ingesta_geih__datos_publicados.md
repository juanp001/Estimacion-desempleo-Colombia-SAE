# ingesta_geih__datos_publicados


## Celda 0



## Celda 1



## Celda 2



## Celda 3



## Celda 4


**Salida:**

```
Ciudades detectadas (25): ['Bogotá', 'Medellín A.M.', 'Cali A.M.', 'Barranquilla A.M.', 'Bucaramanga A.M.', 'Manizales A.M.', 'Pasto', 'Pereira A.M.', 'Cúcuta A.M.', 'Ibagué', 'Montería', 'Cartagena', 'Villavicencio', 'Tunja', 'Florencia', 'Popayán', 'Valledupar', 'Quibdó', 'Neiva', 'Riohacha', 'Santa Marta', 'Armenia', 'Sincelejo', 'Total 10 ciudades', 'Total 23 ciudades y A.M.']
Agregados anuales detectados (5): ['Total Nacional', 'Total Cabeceras', 'Total Centros poblados y rural disperso', 'Total 13 ciudades y áreas metropolitanas', 'Total 10 ciudades']

```


## Celda 5


**Salida:**

```
[PASS] datos_nacionales: filas == 72 (real: 72)
[PASS] datos_nacionales: sin duplicados por ['ANIO', 'MES'] (duplicados: 0)
[PASS] datos_nacionales: TASA_DESEMPLEO en [0, 100] (fuera de rango: 0)
[PASS] datos_nacionales: PEA == EMPLEADOS + DESEMPLEADOS (incoherentes: 0)
[PASS] datos_municipales: filas == 1800 (real: 1800)
[PASS] datos_municipales: sin duplicados por ['CIUDAD', 'ANIO', 'MES'] (duplicados: 0)
[PASS] datos_municipales: TASA_DESEMPLEO en [0, 100] (fuera de rango: 0)
[PASS] datos_municipales: PEA == EMPLEADOS + DESEMPLEADOS (incoherentes: 0)
[PASS] datos_anuales: filas == 30 (real: 30)
[PASS] datos_anuales: sin duplicados por ['CONJUNTO', 'ANIO'] (duplicados: 0)
[PASS] datos_anuales: TASA_DESEMPLEO en [0, 100] (fuera de rango: 0)
[PASS] datos_anuales: PEA == EMPLEADOS + DESEMPLEADOS (incoherentes: 0)

```


## Celda 6


**Salida:**

```
Tabla cargada: tesis.geih_bronce.datos_nacionales
Tabla cargada: tesis.geih_bronce.datos_municipales
Tabla cargada: tesis.geih_bronce.datos_anuales

```
