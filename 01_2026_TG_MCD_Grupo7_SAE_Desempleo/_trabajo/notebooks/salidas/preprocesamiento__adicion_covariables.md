# preprocesamiento__adicion_covariables


## Celda 0

x̄_D = Σ_{m∈D} z_m · x_m / Σ_{m∈D} z_m
```

Si `x = Y/Z`, el resultado es `ΣY/ΣZ`, el indicador calculado para la unión de los municipios
(Morales et al., 2021, p. 21 y 425). Ejemplos: participación sectorial del valor agregado →
peso = valor agregado; densidad → superficie; valores per cápita, IPM, homicidios → población
total; coberturas educativas y Saber 11 → población del grupo de edad (proxy). La regla de cada
variable del catálogo está en `shared/reglas_agregacion.py` y se guarda en
`tesis.preprocesamiento.reglas_agregacion_covariables`, que es la tabla de covariables del
documento (R-06): para cada una trae, además de la regla, la unidad, la fuente, el año y mes de
corte, la periodicidad, la geografía y los matices de su definición. Los indicadores fuera del catálogo usan
la población de 15 años y más. En los 16 dominios de un solo municipio el resultado es el valor
del municipio. Una celda compara, para los 7 dominios A.M., la regla por variable con la
regla anterior (todo ponderado por la población de 15 años y más).

## Auditoría de la correspondencia geográfica

La última celda guarda `tesis.preprocesamiento.auditoria_dominios`: una fila por dominio con
el código `AREA` de la GEIH, el nombre oficial del DANE (y si aparece en el anexo), la
geografía real de la tasa (cabeceras) y de las covariables (municipio completo), los
municipios integrantes con su DIVIPOLA, el DIVIPOLA usado en la unión, la regla de
construcción de `x_d` y la tasa directa frente a la publicada. Se detiene si un dominio no
aparece en la auditoría o si su nombre no está en las cifras oficiales del período.

## Corte de cada covariable del catálogo (R-19)

La plata de TerriData tiene una fila por entidad, año y mes de corte, y aquí solo se lee la del
mes estimado. Un indicador con otro corte ese año llega en NULL: en 2019 los puntajes Saber 11
(`040040001`, `040040002`) solo tienen corte en noviembre. Antes de agregar se verifica que
cada código del catálogo tenga dato en el mes estimado para algún municipio miembro; si no, el
notebook se detiene y dice en qué meses de ese año sí lo tiene (antes el pre-filtrado lo sacaba
por completitud sin decir por qué). Morales et al. (2021, p. 419): los x de registros
administrativos pueden no tener las mismas especificaciones que la encuesta.

## Estrategia de Join: LEFT JOIN

```
Estimaciones (23 dominios)
  LEFT JOIN TerriData agregada por dominio
  ON CODIGO_DOMINIO AND PER = ANO AND MES = MES
  → tesis.preprocesamiento.tasa_desempleo_covariables (23 filas × ~1,590 cols)
```

LEFT JOIN preserva todas las estimaciones aunque un dominio no tenga covariables en TerriData
(valores NULL en ese caso).

## Columnas excluidas de TerriData

Se descartan las de identificación, que ya existen en las estimaciones o no son indicadores:
`CODIGO_DEPARTAMENTO`, `DEPARTAMENTO`, `CODIGO_ENTIDAD`, `ENTIDAD`, `ANO` y `MES`.

## Interpretación del CV (columna heredada de estimación directa)

* CV < 5%: Estimación **confiable** ✅
* 5% ≤ CV < 20%: Estimación **aceptable** ⚠️
* CV ≥ 20%: Estimación **no confiable** ❌

## Referencias

* Morales, D., Esteban, M. D., Pérez, A. & Hobza, T. (2021). *A Course on Small Area Estimation and Mixed Models*. Springer
  (p. 21 y 425: agregación de x_d; p. 419: especificación de los registros administrativos).
* TerriData - DNP: https://terridata.dnp.gov.co/
```


## Celda 1



## Celda 2


**Salida:**

```
Leyendo estimaciones directas...
  23 filas — 23 columnas

Leyendo covariables TerriData...
  147026 filas — 1588 columnas

```


## Celda 3



## Celda 4


**Salida:**

```
Covariables seleccionadas de TerriData: 1582
✔ 2018-12: las 18 covariables del catálogo tienen dato en el mes estimado
Indicadores por peso de agregación:
  PET               1564  (Población de 15 años y más (suma de grupos quinquenales 15-19 a 80+))
  POBLACION_10_14      1  (Población de 10-14 años (hombres + mujeres))
  POBLACION_15_19      4  (Población de 15-19 años (hombres + mujeres))
  POBLACION_TOTAL      9  (Población total (010010009))
  SUPERFICIE           1  (Superficie implícita = población total / densidad (km²))
  VALOR_AGREGADO       3  (Valor agregado municipal (120210001))

```


## Celda 5


**Salida:**

```
Dominios con varios municipios (covariables agregadas): 7

```


## Celda 6


**Salida:**

```
Máxima diferencia relativa (%) entre la regla por variable y la regla PET (7 dominios A.M.):
            ALIAS            PESO  MAX_ABS_DIF_RELATIVA_PCT
         DENS_POB      SUPERFICIE                     67.67
       VA_PCT_SEC  VALOR_AGREGADO                     43.94
      VA_PCT_PRIM  VALOR_AGREGADO                     14.23
      VA_PCT_TERC  VALOR_AGREGADO                      8.04
    COB_NET_MEDIA POBLACION_15_19                      0.85
      ING_TRIB_PC POBLACION_TOTAL                      0.68
      COB_NET_SEC POBLACION_10_14                      0.57
TASA_TRAN_EDU_SUP POBLACION_15_19                      0.46
            VA_PC POBLACION_TOTAL                      0.43
      BANDA_ANCHA POBLACION_TOTAL                      0.32
     IND_POB_MULT POBLACION_TOTAL                      0.30
      SABER11_MAT POBLACION_15_19                      0.27
  TASA_HOMICIDIOS POBLACION_TOTAL                      0.21
      SABER11_LEC POBLACION_15_19                      0.18
       PCT_URBANA POBLACION_TOTAL                      0.10
      PCT_JOVENES POBLACION_TOTAL                      0.08
    COB_ACUEDUCTO POBLACION_TOTAL                      0.06
              IDF POBLACION_TOTAL                      0.03

```
| CODIGO_DOMINIO | ANO | MES | CODIGO_INDICADOR | VALOR_NUEVA | VALOR_PET | ALIAS | PESO | DIF_RELATIVA_PCT |
|---|---|---|---|---|---|---|---|---|
| 05001 | 2018 | 12 | 010010010 | 3319.0697509712822 | 6040.394420139974 | DENS_POB | SUPERFICIE | -45.05210222854339 |
| 17001 | 2018 | 12 | 010010010 | 521.427875812256 | 813.7240420741232 | DENS_POB | SUPERFICIE | -35.92079761055425 |
| 54001 | 2018 | 12 | 010010010 | 502.43185165832494 | 683.7453033068575 | DENS_POB | SUPERFICIE | -26.517688790201614 |
| 66001 | 2018 | 12 | 010010010 | 868.7519080402068 | 1289.2250060273168 | DENS_POB | SUPERFICIE | -32.61440757209458 |
| 68001 | 2018 | 12 | 010010010 | 849.7610678543408 | 2628.659902085498 | DENS_POB | SUPERFICIE | -67.67322135586402 |
| 76001 | 2018 | 12 | 010010010 | 2937.1480849609284 | 3875.7761986177675 | DENS_POB | SUPERFICIE | -24.217809944536672 |
| 05001 | 2018 | 12 | 120210008 | 0.5282260581850406 | 0.6000186438811858 | VA_PCT_PRIM | VALOR_AGREGADO | -11.96505915745533 |
| 08001 | 2018 | 12 | 120210008 | 0.023781313863491416 | 0.02655409206786416 | VA_PCT_PRIM | VALOR_AGREGADO | -10.441999663503347 |
| 17001 | 2018 | 12 | 120210008 | 3.610545100135358 | 4.2096193200786605 | VA_PCT_PRIM | VALOR_AGREGADO | -14.231078261302457 |
| 54001 | 2018 | 12 | 120210008 | 4.513188059455195 | 4.448627219188045 | VA_PCT_PRIM | VALOR_AGREGADO | 1.4512530964312578 |
| 66001 | 2018 | 12 | 120210008 | 3.094419821963467 | 2.898513681135722 | VA_PCT_PRIM | VALOR_AGREGADO | 6.758848236692925 |
| 68001 | 2018 | 12 | 120210008 | 4.382839120436711 | 4.476854374932533 | VA_PCT_PRIM | VALOR_AGREGADO | -2.1000293201906794 |
| 76001 | 2018 | 12 | 120210008 | 0.2876619194168909 | 0.2597824179728013 | VA_PCT_PRIM | VALOR_AGREGADO | 10.731866175411646 |
| 05001 | 2018 | 12 | 120210009 | 27.646535618856582 | 26.392981449035922 | VA_PCT_SEC | VALOR_AGREGADO | 4.749573943516903 |
| 08001 | 2018 | 12 | 120210009 | 23.434898394790558 | 23.09384667565271 | VA_PCT_SEC | VALOR_AGREGADO | 1.4768077571823963 |
| 17001 | 2018 | 12 | 120210009 | 23.95769474605163 | 23.155509746059053 | VA_PCT_SEC | VALOR_AGREGADO | 3.464337467799015 |
| 76001 | 2018 | 12 | 120210009 | 22.122744026027814 | 15.369568426229915 | VA_PCT_SEC | VALOR_AGREGADO | 43.93861566257669 |
| 05001 | 2018 | 12 | 120210010 | 71.83250549077907 | 73.01483502440347 | VA_PCT_TERC | VALOR_AGREGADO | -1.6193004246729201 |
| 76001 | 2018 | 12 | 120210010 | 77.5995940545553 | 84.38064915579729 | VA_PCT_TERC | VALOR_AGREGADO | -8.036267994006186 |


## Celda 7


**Salida:**

```
Resultado: 23 filas — 1605 columnas
  Identificación + estimación: 23
  Covariables TerriData: 1582

```


## Celda 8


**Salida:**

```
✔ Tabla creada: tesis.preprocesamiento.tasa_desempleo_covariables
  Acceso: SELECT * FROM tesis.preprocesamiento.tasa_desempleo_covariables

```


## Celda 9


**Salida:**

| CODIGO_INDICADOR | ALIAS | INDICADOR | PESO | DESCRIPCION_PESO | EXPRESION_PESO | TIPO | SUSTENTO | GEOGRAFIA | NOTA | UNIDAD_MEDIDA | FUENTE | ANO_CORTE | MES_CORTE | PERIODICIDAD | MESES_CON_DATO |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 040010010 | COB_NET_MEDIA | Cobertura neta en educación media | POBLACION_15_19 | Población de 15-19 años (hombres + mujeres) | try_cast(`020010004` AS DOUBLE) + try_cast(`020020004` AS DOUBLE) | proxy | Cobertura neta en media = matriculados de 15-16 años / población de 15-16 años. TerriData no publica la población de 15-16; se usa el grupo quinquenal 15-19. | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO | Se mide por la sede del colegio: la matrícula se asigna al municipio donde estudia el alumno, no donde vive. | Porcentaje (el valor está multiplicado por 100) | Ministerio de Educación Nacional | 2018 | 12 | anual | 12 |
| 040010009 | COB_NET_SEC | Cobertura neta en educación secundaria | POBLACION_10_14 | Población de 10-14 años (hombres + mujeres) | try_cast(`020010003` AS DOUBLE) + try_cast(`020020003` AS DOUBLE) | proxy | Cobertura neta en secundaria = matriculados de 11-14 años / población de 11-14 años. Se usa el grupo quinquenal 10-14. | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO | Se mide por la sede del colegio: la matrícula se asigna al municipio donde estudia el alumno, no donde vive. | Porcentaje (el valor está multiplicado por 100) | Ministerio de Educación Nacional | 2018 | 12 | anual | 12 |
| 040040001 | SABER11_MAT | Puntaje promedio Pruebas Saber 11 - Matemáticas | POBLACION_15_19 | Población de 15-19 años (hombres + mujeres) | try_cast(`020010004` AS DOUBLE) + try_cast(`020020004` AS DOUBLE) | proxy | Puntaje promedio Saber 11: el denominador es el número de evaluados, que TerriData no publica; se aproxima con la población de 15-19 años. | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Puntos | ICFES | 2018 | 12 | anual | 12 |
| 040040002 | SABER11_LEC | Puntaje promedio Pruebas Saber 11 - Lectura crítica | POBLACION_15_19 | Población de 15-19 años (hombres + mujeres) | try_cast(`020010004` AS DOUBLE) + try_cast(`020020004` AS DOUBLE) | proxy | Puntaje promedio Saber 11: el denominador es el número de evaluados, que TerriData no publica; se aproxima con la población de 15-19 años. | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Puntos | ICFES | 2018 | 12 | anual | 12 |
| 040010028 | TASA_TRAN_EDU_SUP | Tasa de tránsito inmediato a la educación superior | POBLACION_15_19 | Población de 15-19 años (hombres + mujeres) | try_cast(`020010004` AS DOUBLE) + try_cast(`020020004` AS DOUBLE) | proxy | Tránsito inmediato = bachilleres que ingresan a educación superior / bachilleres graduados. Los graduados no se publican; se aproximan con la población de 15-19. | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Porcentaje | Ministerio de Educación Nacional (MEN) | 2018 | 12 | anual | 12 |
| 120210002 | VA_PC | Valor agregado per cápita | POBLACION_TOTAL | Población total (010010009) | try_cast(`010010009` AS DOUBLE) | exacta | Valor per cápita: Σ numerador / Σ población = promedio ponderado por la población (Morales et al., p. 21). La población implícita (valor agregado / per cápita) coincide con 010010009. | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Pesos corrientes | DNP con información del DANE | 2018 | 12 | anual | 12 |
| 120210008 | VA_PCT_PRIM | Porcentaje del valor agregado por actividades económicas - Actividades primarias | VALOR_AGREGADO | Valor agregado municipal (120210001) | try_cast(`120210001` AS DOUBLE) | exacta | Participación sectorial: Σ VA del sector / Σ VA total = promedio ponderado por el valor agregado (Morales et al., p. 21). | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Porcentaje | DNP con información del DANE | 2018 | 12 | anual | 12 |
| 120210009 | VA_PCT_SEC | Porcentaje del valor agregado por actividades económicas - Actividades secundarias | VALOR_AGREGADO | Valor agregado municipal (120210001) | try_cast(`120210001` AS DOUBLE) | exacta | Participación sectorial: Σ VA del sector / Σ VA total = promedio ponderado por el valor agregado (Morales et al., p. 21). | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Porcentaje | DNP con información del DANE | 2018 | 12 | anual | 12 |
| 120210010 | VA_PCT_TERC | Porcentaje del valor agregado por actividades económicas - Actividades terciarias | VALOR_AGREGADO | Valor agregado municipal (120210001) | try_cast(`120210001` AS DOUBLE) | exacta | Participación sectorial: Σ VA del sector / Σ VA total = promedio ponderado por el valor agregado (Morales et al., p. 21). | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Porcentaje | DNP con información del DANE | 2018 | 12 | anual | 12 |
| 140010004 | IND_POB_MULT | Índice de pobreza multidimensional - IPM | POBLACION_TOTAL | Población total (010010009) | try_cast(`010010009` AS DOUBLE) | exacta | Porcentaje de personas: Σ personas con el atributo / Σ población = promedio ponderado por la población (Morales et al., p. 21). IPM: porcentaje de personas pobres (CNPV 2018). | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Porcentaje (el valor está multiplicado por 100) | DANE | 2018 | 12 | anual | 12 |
| 020040003 | PCT_URBANA | Porcentaje población urbana | POBLACION_TOTAL | Población total (010010009) | try_cast(`010010009` AS DOUBLE) | exacta | Porcentaje de personas: Σ personas con el atributo / Σ población = promedio ponderado por la población (Morales et al., p. 21). Equivale a Σ población urbana / Σ población total. | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Porcentaje (el valor está multiplicado por 100) | DANE - Proyecciones de población con base en el Censo 2018. Elaboración DNP | 2018 | 12 | anual | 12 |
| 010010010 | DENS_POB | Densidad poblacional | SUPERFICIE | Superficie implícita = población total / densidad (km²) | try_divide(try_cast(`010010009` AS DOUBLE), try_cast(`010010010` AS DOUBLE)) | exacta | Densidad = población / superficie: Σ población / Σ superficie = promedio ponderado por la superficie (Morales et al., p. 21). | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Hab/Km2 | DNP con información del IGAC y el DANE | 2018 | 12 | anual | 12 |
| 020090021 | PCT_JOVENES | Porcentaje de población de jóvenes entre 14 y 28 años | POBLACION_TOTAL | Población total (010010009) | try_cast(`010010009` AS DOUBLE) | exacta | Porcentaje de personas: Σ personas con el atributo / Σ población = promedio ponderado por la población (Morales et al., p. 21). Equivale a Σ jóvenes de 14-28 / Σ población total. | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Porcentaje | DANE - Proyecciones de población 2025 con base en el Censo 2018. Elaboración DNP | 2018 | 12 | anual | 12 |
| 070100007 | IDF | Indicador de desempeño fiscal | POBLACION_TOTAL | Población total (010010009) | try_cast(`010010009` AS DOUBLE) | convención | Índice compuesto de las finanzas de cada alcaldía; el A.M. no es una entidad fiscal y el índice no tiene un valor de la unión. Promedio ponderado por población. | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Puntos | DNP - DDDR | 2018 | 12 | anual | 12 |
| 070010020 | ING_TRIB_PC | Ingresos tributarios per cápita | POBLACION_TOTAL | Población total (010010009) | try_cast(`010010009` AS DOUBLE) | exacta | Valor per cápita: Σ numerador / Σ población = promedio ponderado por la población (Morales et al., p. 21). | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Pesos corrientes | DNP a partir de información del FUT y DANE | 2018 | 12 | anual | 12 |
| 060010003 | TASA_HOMICIDIOS | Tasa de homicidios por cada 100.000 habitantes | POBLACION_TOTAL | Población total (010010009) | try_cast(`010010009` AS DOUBLE) | exacta | Tasa por 100.000 habitantes: Σ homicidios / Σ población = promedio ponderado por la población (Morales et al., p. 21). | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Tasa por cada 100.000 habitantes | DNP, con datos de MinDefensa y DANE | 2018 | 12 | anual | 12 |
| 030010004 | COB_ACUEDUCTO | Cobertura de acueducto (Censo) | POBLACION_TOTAL | Población total (010010009) | try_cast(`010010009` AS DOUBLE) | proxy | Cobertura de acueducto del CNPV 2018; el denominador son viviendas o hogares, que TerriData no publica para 2018. Se aproxima con la población total. | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO |  | Porcentaje (el valor está multiplicado por 100) | DANE | 2018 | 12 | anual | 12 |
| 030010003 | BANDA_ANCHA | Penetración de banda ancha | POBLACION_TOTAL | Población total (010010009) | try_cast(`010010009` AS DOUBLE) | exacta | Penetración de banda ancha = accesos fijos por cada 100 habitantes (MinTIC): promedio ponderado por la población (Morales et al., p. 21). | Municipio completo (cabecera y resto); en los dominios A.M. se agrega con PESO | Trimestral: se usa el corte de diciembre (cuarto trimestre) frente a una tasa de desempleo que promedia los 12 meses. | Porcentaje (el valor está multiplicado por 100) | Ministerio de Tecnologías de la Información y las Comunicaciones | 2018 | 12 | trimestral | 03, 06, 09, 12 |
```
✔ Tabla creada: tesis.preprocesamiento.reglas_agregacion_covariables

```


## Celda 10


**Salida:**

```
Dominios auditados: 23 (7 A.M., 43 municipios) | máx |TD directa − TD DANE| = 0.0005 pp (NaN si el anexo no cubre el período)

```
| PER | MES | PERIODO | N_MESES_VENTANA | CODIGO_AREA_GEIH | NOMBRE_DOMINIO | EN_ANEXO_DANE | TIPO_DOMINIO | GEOGRAFIA_TASA | GEOGRAFIA_COVARIABLES | N_MUNICIPIOS | MUNICIPIOS_INTEGRANTES | DIVIPOLA_INTEGRANTES | CODIGO_DOMINIO | REGLA_X_D | TASA_DESEMPLEO_PCT | TD_DANE_PCT | DIF_TD_PP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | 12 | Ene-Dic 2018 | 12 | 05 | Medellín A.M. | True | CIUDAD_AM | Cabeceras de los 10 municipios del A.M. según la GEIH (AREA, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 10 | Medellín, Barbosa, Bello, Caldas, Copacabana, Envigado, Girardota, Itagüí, La Estrella, Sabaneta | 05001, 05079, 05088, 05129, 05212, 05266, 05308, 05360, 05380, 05631 | 05001 | x_d = Σ z_m·x_m / Σ z_m sobre los 10 municipios, z = denominador de cada indicador (catálogo: POBLACION_10_14 1, POBLACION_15_19 4, POBLACION_TOTAL 9, SUPERFICIE 1, VALOR_AGREGADO 3; ver reglas_agregacion_covariables); fuera del catálogo z = PET 15+ | 11.837792024340981 | 11.837783320635884 | 8.70370509709062e-06 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 08 | Barranquilla A.M. | True | CIUDAD_AM | Cabeceras de los 2 municipios del A.M. según la GEIH (AREA, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 2 | Barranquilla, Soledad | 08001, 08758 | 08001 | x_d = Σ z_m·x_m / Σ z_m sobre los 2 municipios, z = denominador de cada indicador (catálogo: POBLACION_10_14 1, POBLACION_15_19 4, POBLACION_TOTAL 9, SUPERFICIE 1, VALOR_AGREGADO 3; ver reglas_agregacion_covariables); fuera del catálogo z = PET 15+ | 8.147876963504446 | 8.147853101147122 | 2.3862357323878314e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 11 | Bogotá | True | CIUDAD | Cabecera municipal de Bogotá, D.C. (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Bogotá, D.C. | 11001 | 11001 | x_d = valor municipal de TerriData de Bogotá, D.C., sin agregar | 10.369891846009237 | 10.369894873040097 | -3.0270308606361596e-06 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 13 | Cartagena | True | CIUDAD | Cabecera municipal de Cartagena De Indias (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Cartagena De Indias | 13001 | 13001 | x_d = valor municipal de TerriData de Cartagena De Indias, sin agregar | 8.348479134679252 | 8.348511694053844 | -3.2559374592011636e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 15 | Tunja | True | CIUDAD | Cabecera municipal de Tunja (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Tunja | 15001 | 15001 | x_d = valor municipal de TerriData de Tunja, sin agregar | 11.31387295825135 | 11.313852210726902 | 2.074752444869432e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 17 | Manizales A.M. | True | CIUDAD_AM | Cabeceras de los 2 municipios del A.M. según la GEIH (AREA, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 2 | Manizales, Villamaría | 17001, 17873 | 17001 | x_d = Σ z_m·x_m / Σ z_m sobre los 2 municipios, z = denominador de cada indicador (catálogo: POBLACION_10_14 1, POBLACION_15_19 4, POBLACION_TOTAL 9, SUPERFICIE 1, VALOR_AGREGADO 3; ver reglas_agregacion_covariables); fuera del catálogo z = PET 15+ | 11.237104562268692 | 11.236977346196051 | 0.000127216072641545 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 18 | Florencia | True | CIUDAD | Cabecera municipal de Florencia (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Florencia | 18001 | 18001 | x_d = valor municipal de TerriData de Florencia, sin agregar | 12.940077494574945 | 12.94001027184473 | 6.722273021431135e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 19 | Popayán | True | CIUDAD | Cabecera municipal de Popayán (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Popayán | 19001 | 19001 | x_d = valor municipal de TerriData de Popayán, sin agregar | 10.67751322056855 | 10.67742014895555 | 9.307161299965117e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 20 | Valledupar | True | CIUDAD | Cabecera municipal de Valledupar (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Valledupar | 20001 | 20001 | x_d = valor municipal de TerriData de Valledupar, sin agregar | 14.450446813558157 | 14.450372598884815 | 7.421467334189913e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 23 | Montería | True | CIUDAD | Cabecera municipal de Montería (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Montería | 23001 | 23001 | x_d = valor municipal de TerriData de Montería, sin agregar | 9.467462710346696 | 9.467364988388754 | 9.772195794255367e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 27 | Quibdó | True | CIUDAD | Cabecera municipal de Quibdó (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Quibdó | 27001 | 27001 | x_d = valor municipal de TerriData de Quibdó, sin agregar | 17.81311521809962 | 17.812734308560156 | 0.0003809095394657902 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 41 | Neiva | True | CIUDAD | Cabecera municipal de Neiva (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Neiva | 41001 | 41001 | x_d = valor municipal de TerriData de Neiva, sin agregar | 11.533679893497528 | 11.533738472551269 | -5.85790537410702e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 44 | Riohacha | True | CIUDAD | Cabecera municipal de Riohacha (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Riohacha | 44001 | 44001 | x_d = valor municipal de TerriData de Riohacha, sin agregar | 13.883929931442381 | 13.8834343728831 | 0.000495558559281406 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 47 | Santa Marta | True | CIUDAD | Cabecera municipal de Santa Marta (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Santa Marta | 47001 | 47001 | x_d = valor municipal de TerriData de Santa Marta, sin agregar | 8.316388353479095 | 8.316445014591052 | -5.666111195701262e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 50 | Villavicencio | True | CIUDAD | Cabecera municipal de Villavicencio (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Villavicencio | 50001 | 50001 | x_d = valor municipal de TerriData de Villavicencio, sin agregar | 11.873324720682339 | 11.873280098689376 | 4.4621992962845525e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 52 | Pasto | True | CIUDAD | Cabecera municipal de Pasto (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Pasto | 52001 | 52001 | x_d = valor municipal de TerriData de Pasto, sin agregar | 8.815888010228242 | 8.815982104427576 | -9.409419933348317e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 54 | Cúcuta A.M. | True | CIUDAD_AM | Cabeceras de los 4 municipios del A.M. según la GEIH (AREA, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 4 | San José De Cúcuta, El Zulia, Los Patios, Villa Del Rosario | 54001, 54261, 54405, 54874 | 54001 | x_d = Σ z_m·x_m / Σ z_m sobre los 4 municipios, z = denominador de cada indicador (catálogo: POBLACION_10_14 1, POBLACION_15_19 4, POBLACION_TOTAL 9, SUPERFICIE 1, VALOR_AGREGADO 3; ver reglas_agregacion_covariables); fuera del catálogo z = PET 15+ | 15.983358846687304 | 15.983421647468186 | -6.280078088138907e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 63 | Armenia | True | CIUDAD | Cabecera municipal de Armenia (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Armenia | 63001 | 63001 | x_d = valor municipal de TerriData de Armenia, sin agregar | 15.491457817733293 | 15.491529966340583 | -7.214860728943506e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 66 | Pereira A.M. | True | CIUDAD_AM | Cabeceras de los 3 municipios del A.M. según la GEIH (AREA, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 3 | Pereira, Dosquebradas, La Virginia | 66001, 66170, 66400 | 66001 | x_d = Σ z_m·x_m / Σ z_m sobre los 3 municipios, z = denominador de cada indicador (catálogo: POBLACION_10_14 1, POBLACION_15_19 4, POBLACION_TOTAL 9, SUPERFICIE 1, VALOR_AGREGADO 3; ver reglas_agregacion_covariables); fuera del catálogo z = PET 15+ | 8.866599810615549 | 8.86655943825643 | 4.037235911802384e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 68 | Bucaramanga A.M. | True | CIUDAD_AM | Cabeceras de los 4 municipios del A.M. según la GEIH (AREA, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 4 | Bucaramanga, Floridablanca, Girón, Piedecuesta | 68001, 68276, 68307, 68547 | 68001 | x_d = Σ z_m·x_m / Σ z_m sobre los 4 municipios, z = denominador de cada indicador (catálogo: POBLACION_10_14 1, POBLACION_15_19 4, POBLACION_TOTAL 9, SUPERFICIE 1, VALOR_AGREGADO 3; ver reglas_agregacion_covariables); fuera del catálogo z = PET 15+ | 8.739145745214026 | 8.739146877486235 | -1.1322722084372572e-06 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 70 | Sincelejo | True | CIUDAD | Cabecera municipal de Sincelejo (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Sincelejo | 70001 | 70001 | x_d = valor municipal de TerriData de Sincelejo, sin agregar | 9.60566705797104 | 9.605441572832094 | 0.00022548513894626865 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 73 | Ibagué | True | CIUDAD | Cabecera municipal de Ibagué (AREA de la GEIH, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 1 | Ibagué | 73001 | 73001 | x_d = valor municipal de TerriData de Ibagué, sin agregar | 13.99413661480143 | 13.99411117357206 | 2.5441229370315455e-05 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 76 | Cali A.M. | True | CIUDAD_AM | Cabeceras de los 2 municipios del A.M. según la GEIH (AREA, solo CLASE = 1) | Municipio completo (cabecera y resto), TerriData | 2 | Santiago De Cali, Yumbo | 76001, 76892 | 76001 | x_d = Σ z_m·x_m / Σ z_m sobre los 2 municipios, z = denominador de cada indicador (catálogo: POBLACION_10_14 1, POBLACION_15_19 4, POBLACION_TOTAL 9, SUPERFICIE 1, VALOR_AGREGADO 3; ver reglas_agregacion_covariables); fuera del catálogo z = PET 15+ | 11.651373436219085 | 11.651373088505993 | 3.4771309209702395e-07 |
```
✔ Tabla creada: tesis.preprocesamiento.auditoria_dominios

```
