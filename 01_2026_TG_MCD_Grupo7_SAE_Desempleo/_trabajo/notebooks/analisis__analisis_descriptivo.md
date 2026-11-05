# analisis__analisis_descriptivo


## Celda 0

```python
%md
# Análisis descriptivo de los datos previo al modelamiento

Responde al requerimiento de que, antes del modelamiento, exista una caracterización
descriptiva univariada, bivariada y multivariada de los datos. Cada figura va acompañada
de una guía de lectura y de una interpretación calculada desde los propios datos, de
modo que el texto no queda desactualizado si cambian.

## Qué hace y qué no hace

El propósito de este notebook es **comprender los datos**: cómo se distribuyen, qué
tan dispersos son, qué territorios se apartan del resto y cómo se relacionan entre sí.
No descarta ninguna covariable. Las decisiones de selección se toman en
`eda_seleccion_covariables`, a partir de los diagnósticos correspondientes.

La distinción es deliberada y se sostiene a lo largo de todo el flujo:

| | Análisis descriptivo | Selección de covariables |
|---|---|---|
| Pregunta | ¿Cómo son los datos y cómo se relacionan? | ¿Cuáles entran al modelo? |
| Salida | Tablas y figuras de caracterización | Un subconjunto de covariables |
| Una variable asimétrica | se describe como asimétrica | no se descarta por serlo |
| Un dominio extremo | se identifica y se nombra | no se elimina |

## Posición en el flujo

```
pre_filtrado_covariables   →  covariables_prefiltradas
       │
       ▼  elegibilidad conceptual (catálogo de literatura, independiente de la respuesta)
       │
       ▼  [ESTE NOTEBOOK]
       │   1. Univariado:    tasa de desempleo, su error estándar y su varianza de
       │                     muestreo, y las covariables candidatas
       │   2. Bivariado:     cada candidata frente a la tasa de desempleo
       │   3. Multivariado:  estructura conjunta de las candidatas
       │
       ▼  eda_seleccion_covariables  →  diagnóstico y selección cualitativa
       ▼  fay_herriot
```

## Sobre el tamaño muestral

El análisis trabaja con los 23 dominios que tienen estimación directa de la GEIH: 16
ciudades y 7 ciudades con su área metropolitana (Medellín, Cali, Barranquilla, Bucaramanga,
Manizales, Pereira y Cúcuta A.M.), porque el campo `AREA` de la GEIH no separa los municipios
del A.M. En esos 7 dominios las covariables son el promedio de los municipios miembro
ponderado con el denominador propio de cada indicador (valor agregado, población
total, superficie, etc.; G7-B1, `adicion_covariables`). Con
ese tamaño los estadísticos descriptivos son informativos pero los contrastes de
hipótesis tienen poca potencia. Por eso esta etapa no ejecuta ninguna prueba formal:
describe, y deja los diagnósticos que sí tienen consecuencia para la etapa de
selección.

## Salidas

* `tesis.preprocesamiento.catalogo_literatura`
* `tesis.preprocesamiento.descriptivo_univariado`
* `tesis.preprocesamiento.descriptivo_bivariado`
* Figuras en el volumen `figuras_eda`, con prefijo `desc_`.
```


## Celda 1

```python
import os
import sys

import numpy as np
import pandas as pd
from pyspark.sql import functions as F


# R-67: `code/` en sys.path (el notebook está en code/<carpeta>/); `comun.entorno` hace el resto
_ruta_nb = (
    dbutils.notebook.entry_point.getDbutils()
    .notebook()
    .getContext()
    .notebookPath()
    .get()
)
CODE_DIR = "/Workspace" + os.path.dirname(os.path.dirname(_ruta_nb))
sys.path.insert(0, CODE_DIR)

from preprocesamiento.shared.config import *
from analisis.shared import descriptivos as desc
from analisis.shared.datos_analisis import cargar_datos_analisis

# ── Carga (la misma que eda_seleccion_covariables, R-32) ─────────────────────
datos = cargar_datos_analisis(
    spark,
    TBL_PREFILTRADAS,
    TBL_DIM_INDICADORES,
    METADATA_COLS,
    VARIABLE_OBJETIVO,
    tabla_objetivos=TBL_SIN_ENCUESTA,
)
df_full = datos["df_full"]
indicadores_dict = datos["indicadores_dict"]
df_meta, df_pd = datos["df_meta"], datos["df_pd"]
# PSI = SE²: varianza de muestreo que el modelo toma como conocida.
Y, SE, PSI, entidades = datos["Y"], datos["SE"], datos["PSI"], datos["entidades"]

df_meta["VARIANZA_MUESTREO"] = PSI

print(f"Dominios de estimación: {len(Y)}")
print(f"Covariables pre-filtradas: {df_pd.shape[1]}")
```

**Salida:**

```
Catálogo de elegibilidad conceptual: 18 de 18 entradas activas (6 variables de la literatura excluidas o sin dato utilizable)
  · activa: 18
  · sin dato utilizable: sin dato en los dominios con encuesta para el período de estimación: 1
  · sin dato utilizable: la serie termina en 2016; no existe dato para 2018: 1
  · sin dato utilizable: solo se publica para departamentos y 23 ciudades principales; no existe en los municipios objetivo sin encuesta, por lo que no permite predicción sintética: 1
  · sin dato utilizable: solo se publica a nivel departamental: 1
  · sin dato utilizable: solo existe para 2022-2023; el IICA se evaluó como proxy y se excluyó (ver IICA_CONFLICTO), así que no tiene sustituto: 1
  · excluida del catálogo (R-01): mide la incidencia del conflicto en el propio municipio (expulsión, presencia armada), no la recepción de desplazados del argumento de Ibáñez (2008); en los 23 dominios es casi la tasa de homicidios (r = 0.92), solo toma 13 valores distintos por redondeo y Quibdó aporta cerca de la mitad de su suma de cuadrados; en los 83 municipios objetivo llega a 0.8 frente a un máximo de 0.1 en los dominios, donde la relación estimada en capitales urbanas no aplica (Morales et al., p. 454): 1
Dominios de estimación: 23
Covariables pre-filtradas: 497

```


## Celda 2

```python
%md
# 1. Elegibilidad conceptual de las covariables

El conjunto pre-filtrado es demasiado grande para describirse variable por variable.
Antes de caracterizarlo se aplica el criterio conceptual: se conservan únicamente las
covariables que la revisión de literatura del proyecto propone con una referencia
bibliográfica y un mecanismo que las vincula con el desempleo, resueltas contra el
diccionario de indicadores de TerriData.

Este criterio **no usa la variable respuesta**, lo que es esencial: las candidatas no
fueron elegidas por parecerse a la tasa de desempleo, de modo que las correlaciones que
se calculen después conservan su interpretación. Tampoco asigna un «nivel de respaldo»
numérico a cada entrada: o la variable tiene sustento en el documento o no entra.

El reporte deja constancia de todas las variables de la revisión, incluidas las que no
pueden usarse (sin dato para 2018, solo departamentales o ausentes en los municipios
objetivo sin encuesta), con su motivo. Cada entrada trae además el **signo esperado**
del coeficiente según el mecanismo declarado, que la etapa de selección contrasta con
el signo observado.
```


## Celda 3

```python
reporte_catalogo = datos["reporte_catalogo"]
CANDIDATAS, ALIAS, SIGNO, DIMENSION = (
    datos["CANDIDATAS"],
    datos["ALIAS"],
    datos["SIGNO"],
    datos["DIMENSION"],
)

df_cand = datos["df_cand"]
NOMBRES = {c: indicadores_dict.get(c, c) for c in CANDIDATAS}

display(spark.createDataFrame(reporte_catalogo))

(
    spark.createDataFrame(reporte_catalogo)
    .write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TBL_CATALOGO)
)
print(f"Tabla escrita: {TBL_CATALOGO}")
```

**Salida:**

| Alias | Dimension | Codigo | Nombre | Signo_esperado | Referencia | Estado |
|---|---|---|---|---|---|---|
| COB_NET_MEDIA | Educación | 040010010 | Cobertura neta en educación media | - | Castillo-Robayo, C. D.; García-Estévez, J. (2019). «Desempleo juvenil en Colombia: ¿la educación importa?», Revista Finanzas y Política Económica, 11(1), 101-127. DOI: 10.14718/revfinanzpolitecon.2019.11.1.7 | activa |
| COB_NET_SEC | Educación | 040010009 | Cobertura neta en educación secundaria | - | Castillo-Robayo, C. D.; García-Estévez, J. (2019). «Desempleo juvenil en Colombia: ¿la educación importa?», Revista Finanzas y Política Económica, 11(1), 101-127. | activa |
| SABER11_MAT | Educación | 040040001 | Puntaje promedio Pruebas Saber 11 - Matemáticas | - | Castillo-Robayo, C. D.; García-Estévez, J. (2019). Revista Finanzas y Política Económica, 11(1), 101-127. | activa |
| SABER11_LEC | Educación | 040040002 | Puntaje promedio Pruebas Saber 11 - Lectura crítica | - | Castillo-Robayo, C. D.; García-Estévez, J. (2019). Revista Finanzas y Política Económica, 11(1), 101-127. | activa |
| TASA_TRAN_EDU_SUP | Educación | 040010028 | Tasa de tránsito inmediato a la educación superior | - | Castillo-Robayo, C. D.; García-Estévez, J. (2019). Revista Finanzas y Política Económica, 11(1), 101-127 (mecanismo de capital humano). Conservada por decisión del equipo del proyecto. | activa |
| VA_PC | Economía | 120210002 | Valor agregado per cápita | - | Ramírez et al. (2021). «Determinantes económicos y sociales del desempleo y del empleo vulnerable», Redalyc (revista 4315), tabla 2. | activa |
| VA_PCT_PRIM | Economía | 120210008 | Porcentaje del valor agregado por actividades económicas - Actividades primarias | ± | Grupo de análisis del mercado laboral (2016). Reportes del Emisor No. 211, Banco de la República; Bonet, J. (2005). «Cambio estructural regional en Colombia», DTSERU No. 62. | activa |
| VA_PCT_SEC | Economía | 120210009 | Porcentaje del valor agregado por actividades económicas - Actividades secundarias | ± | Grupo de análisis del mercado laboral (2016). Reportes del Emisor No. 211, Banco de la República; Bonet, J. (2005). DTSERU No. 62. | activa |
| VA_PCT_TERC | Economía | 120210010 | Porcentaje del valor agregado por actividades económicas - Actividades terciarias | ± | Grupo de análisis del mercado laboral (2016). Reportes del Emisor No. 211, Banco de la República; Bonet, J. (2005). DTSERU No. 62. | activa |
| IND_POB_MULT | Pobreza | 140010004 | Índice de pobreza multidimensional - IPM | + | DANE (2018). Medida de Pobreza Multidimensional Municipal de fuente censal 2018. | activa |
| PCT_URBANA | Demografía y población | 020040003 | Porcentaje población urbana | + | DANE, Atlas estadístico (Tomo II Social), «7.4. Tasa de desempleo (TD)». | activa |
| DENS_POB | Demografía y población | 010010010 | Densidad poblacional | ± | DNP. «Orientaciones para realizar la Medición del Desempeño de las Entidades Territoriales» (EI-G01), sección 1.4.2. | activa |
| PCT_JOVENES | Demografía y población | 020090021 | Porcentaje de población de jóvenes entre 14 y 28 años | + | Tamayo, J. A. (2008). «La tasa natural de desempleo en Colombia y sus determinantes», Borradores de Economía No. 491, Banco de la República. DOI: 10.32468/be.491 | activa |
| IDF | Finanzas públicas | 070100007 | Indicador de desempeño fiscal | - | DNP (2023). «Índice de desempeño fiscal (IDF) municipal 2023 y fortalecimiento de las finanzas territoriales». | activa |
| ING_TRIB_PC | Finanzas públicas | 070010020 | Ingresos tributarios per cápita | - | Fundación Felipe González (2020). «Empleo público de emergencia en municipios y departamentos» (con datos de TerriData-DNP). | activa |
| TASA_HOMICIDIOS | Conflicto armado y seguridad ciudadana | 060010003 | Tasa de homicidios por cada 100.000 habitantes | + | Estudio de determinantes sociales, ambiente urbano y seguridad, Santiago de Cali 2015-2024, Revista Panamericana de Salud Pública (2024). | activa |
| COB_ACUEDUCTO | Vivienda y acceso a servicios públicos | 030010004 | Cobertura de acueducto (Censo) | - | DNP (2019). Cartilla 1 «Conceptos básicos para un mejor uso de TerriData», dimensión Vivienda y Acceso a Servicios Públicos. | activa |
| BANDA_ANCHA | Vivienda y acceso a servicios públicos | 030010003 | Penetración de banda ancha | - | DNP (2019). Cartilla 1 «Conceptos básicos para un mejor uso de TerriData», dimensión Vivienda y Acceso a Servicios Públicos. | activa |
| TASA_ANALFABETISMO | Educación | 040030003 | Tasa de Analfabetismo (Censo) | — | — | sin dato utilizable: sin dato en los dominios con encuesta para el período de estimación |
| DENS_EMPRESARIAL | Economía | 160080001 | Número de empresas generadoras de empleo formal por cada 10.000 habitantes | — | — | sin dato utilizable: la serie termina en 2016; no existe dato para 2018 |
| POBREZA_MONETARIA | Pobreza | 140060001 | Incidencia de la pobreza monetaria - Actualización metodológica | — | — | sin dato utilizable: solo se publica para departamentos y 23 ciudades principales; no existe en los municipios objetivo sin encuesta, por lo que no permite predicción sintética |
| GINI | Pobreza | 140010003 | Coeficiente de Gini | — | — | sin dato utilizable: solo se publica a nivel departamental |
| VICTIMAS_DESPLAZAMIENTO | Conflicto armado y seguridad ciudadana | 260030002 | Víctimas de Desplazamiento Forzado ubicadas | — | — | sin dato utilizable: solo existe para 2022-2023; el IICA se evaluó como proxy y se excluyó (ver IICA_CONFLICTO), así que no tiene sustituto |
| IICA_CONFLICTO | Conflicto armado y seguridad ciudadana | 260020003 | Índice de Incidencia del Conflicto Armado - IICA | — | — | excluida del catálogo (R-01): mide la incidencia del conflicto en el propio municipio (expulsión, presencia armada), no la recepción de desplazados del argumento de Ibáñez (2008); en los 23 dominios es casi la tasa de homicidios (r = 0.92), solo toma 13 valores distintos por redondeo y Quibdó aporta cerca de la mitad de su suma de cuadrados; en los 83 municipios objetivo llega a 0.8 frente a un máximo de 0.1 en los dominios, donde la relación estimada en capitales urbanas no aplica (Morales et al., p. 454) |
```
Tabla escrita: tesis.preprocesamiento.catalogo_literatura

```


## Celda 4

```python
%md
# 2. Análisis descriptivo univariado

Responde a la pregunta: **¿cómo se comporta cada variable por sí sola?**

Se caracterizan tres bloques, en este orden:

1. **La variable respuesta**, la tasa de desempleo estimada directamente por dominio.
2. **Su medida de precisión**: el error estándar bootstrap y la varianza de muestreo.
   Caracterizarla no es opcional: el modelo Fay-Herriot la toma como conocida y la
   usa para ponderar cuánto peso recibe la estimación directa de cada dominio frente
   al predictor sintético. Su dispersión determina cuánto suaviza el modelo.
3. **Las covariables candidatas**.

Los estadísticos se eligen según lo que cada variable admite: el coeficiente de
variación se calcula solo donde la variable es estrictamente positiva, que es la
condición bajo la cual expresa dispersión relativa.
```


## Celda 5

```python
etiquetas_respuesta = {
    VARIABLE_OBJETIVO: "Tasa de desempleo (%)",
    "SE_BOOTSTRAP_PCT": "Error estándar bootstrap por viviendas (p.p.)",
    "VARIANZA_MUESTREO": "Varianza de muestreo (p.p.²)",
    "CV_PORCENTAJE": "Coeficiente de variación de la estimación directa (%)",
}
desc_respuesta = desc.resumen_univariado(
    df_meta,
    [VARIABLE_OBJETIVO, "SE_BOOTSTRAP_PCT", "VARIANZA_MUESTREO", "CV_PORCENTAJE"],
    etiquetas=etiquetas_respuesta,
)
display(spark.createDataFrame(desc_respuesta))
```

**Salida:**

| Variable | Codigo | N | Faltantes | Faltantes_pct | Media | Mediana | Desv_Std | Minimo | Q1 | Q3 | Maximo | IQR | CV_pct | Asimetria | N_extremos_IQR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tasa de desempleo (%) | TASA_DESEMPLEO_PCT | 23 | 0 | 0.0 | 11.5373 | 11.3139 | 2.7107 | 8.1479 | 9.167 | 13.412 | 17.8131 | 4.245 | 23.5 | 0.67 | 0 |
| Error estándar bootstrap por viviendas (p.p.) | SE_BOOTSTRAP_PCT | 23 | 0 | 0.0 | 0.2973 | 0.2846 | 0.0536 | 0.2036 | 0.2635 | 0.3274 | 0.4397 | 0.0638 | 18.02 | 0.673 | 1 |
| Varianza de muestreo (p.p.²) | VARIANZA_MUESTREO | 23 | 0 | 0.0 | 0.0911 | 0.081 | 0.0339 | 0.0415 | 0.0694 | 0.1072 | 0.1933 | 0.0377 | 37.16 | 1.243 | 1 |
| Coeficiente de variación de la estimación directa (%) | CV_PORCENTAJE | 23 | 0 | 0.0 | 2.6234 | 2.6173 | 0.3342 | 2.0124 | 2.3372 | 2.837 | 3.2285 | 0.4998 | 12.74 | 0.184 | 0 |


## Celda 6

```python
%md
## 2.1 Distribución de la respuesta y de su error estándar

**Cómo leer la figura.** La fila superior describe la tasa de desempleo (histograma a
la izquierda, diagrama de caja a la derecha); la inferior, su error estándar. En cada
histograma la línea discontinua naranja es la media y la punteada gris la mediana: cuando
se separan, unos pocos dominios extremos arrastran el promedio. En el diagrama de caja,
la caja cubre el 50 % central de los dominios y los puntos aislados son los que quedan
a más de 1,5 rangos intercuartílicos.

Lo que importa para el modelo es la fila inferior: los dominios con mayor error
estándar son los que el Fay-Herriot contraerá con más fuerza hacia el predictor
sintético, porque su estimación directa es la menos precisa.
```


## Celda 7

```python
fig = desc.figura_respuesta(Y, SE)
desc.guardar_figura(fig, "desc_respuesta_precision", VOLUMEN_FIGURAS)
display(fig)
print(desc.interpretar_respuesta(Y, SE, entidades))
```

**Salida:**

```
  figura guardada: /Volumes/tesis/preprocesamiento/figuras_eda/desc_respuesta_precision.png

```
![fig](fig/analisis__analisis_descriptivo_c07_0.png)
```
INTERPRETACIÓN DE LA FIGURA:
  Tasa de desempleo: entre 8.1 % (Barranquilla A.M.) y 17.8 % (Quibdó); media 11.5 %, mediana 11.3 %.
  Forma de la distribución de la tasa: moderadamente asimétrica hacia la derecha (cola hacia valores altos) (asimetría 0.67). La separación entre media y mediana señala que unos pocos dominios extremos arrastran el promedio.
  Error estándar: entre 0.20 y 0.44 puntos porcentuales; los dominios con estimación menos precisa son Quibdó, Florencia, Cúcuta A.M., y los más precisos Barranquilla A.M., Santa Marta, Bogotá.
  Forma de la distribución del error estándar: moderadamente asimétrica hacia la derecha (cola hacia valores altos) (asimetría 0.67).
  Coeficiente de variación de la estimación directa: entre 2.0 % y 3.2 %; de 23 dominios, 23 son confiables (CV < 5 %), 0 aceptables y 0 no confiables (CV ≥ 20 %).
  Correlación entre error estándar y tasa: r = 0.86. El error crece con la tasa, de modo que los dominios de mayor desempleo son también los menos precisos y serán los que el modelo contraiga con más fuerza hacia el predictor sintético.

```
![fig](fig/analisis__analisis_descriptivo_c07_1.png)


## Celda 8

```python
%md
## 2.2 Distribución territorial de la tasa de desempleo

**Cómo leer la figura.** Cada barra es un dominio, ordenado de menor a mayor tasa; la
línea discontinua es la media de los 23 dominios. La figura muestra la magnitud de la
heterogeneidad territorial que las covariables deberán explicar y nombra qué ciudades
ocupan cada extremo.

Es una **descripción territorial**, no un contraste de dependencia espacial: no evalúa
si los territorios próximos entre sí tienen tasas parecidas. El contraste de
dependencia espacial (I de Moran) se aplica a los residuos del benchmark y de las
variantes espaciales en `modelo/fay_herriot_espacial.py`, no a la tasa cruda, que
hereda la autocorrelación de las covariables.
```


## Celda 9

```python
fig = desc.figura_territorial(Y, entidades)
desc.guardar_figura(fig, "desc_territorial_respuesta", VOLUMEN_FIGURAS)
display(fig)
print(desc.interpretar_territorial(Y, entidades))
```

**Salida:**

```
  figura guardada: /Volumes/tesis/preprocesamiento/figuras_eda/desc_territorial_respuesta.png

```
![fig](fig/analisis__analisis_descriptivo_c09_2.png)
```
INTERPRETACIÓN DE LA FIGURA:
  Dominios con mayor tasa: Quibdó, Cúcuta A.M., Armenia (17.8, 16.0 y 15.5 %).
  Dominios con menor tasa: Barranquilla A.M., Santa Marta, Cartagena (8.1, 8.3 y 8.3 %).
  10 de 23 dominios están por encima de la media (11.5 %); la brecha entre el máximo y el mínimo es de 9.7 puntos porcentuales, es decir, el dominio más alto duplica el más bajo.
  Lectura: es la heterogeneidad territorial que el modelo debe explicar con las covariables. Que un dominio ocupe un extremo lo convierte en candidato a dominio influyente en el diagnóstico de robustez, no en un dato a corregir.

```
![fig](fig/analisis__analisis_descriptivo_c09_3.png)


## Celda 10

```python
desc_covariables = desc.resumen_univariado(df_cand, CANDIDATAS, etiquetas=NOMBRES)
desc_covariables.insert(1, "Alias", [ALIAS[c] for c in desc_covariables["Codigo"]])
desc_covariables.insert(
    2, "Dimension", [DIMENSION[c] for c in desc_covariables["Codigo"]]
)
display(spark.createDataFrame(desc_covariables))
```

**Salida:**

| Variable | Alias | Dimension | Codigo | N | Faltantes | Faltantes_pct | Media | Mediana | Desv_Std | Minimo | Q1 | Q3 | Maximo | IQR | CV_pct | Asimetria | N_extremos_IQR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Cobertura neta en educación media | COB_NET_MEDIA | Educación | 040010010 | 23 | 0 | 0.0 | 48.3201 | 48.1 | 5.6286 | 33.8 | 45.6847 | 51.4989 | 57.01 | 5.8142 | 11.65 | -0.756 | 1 |
| Cobertura neta en educación secundaria | COB_NET_SEC | Educación | 040010009 | 23 | 0 | 0.0 | 83.7887 | 84.43 | 6.1794 | 75.1731 | 79.21 | 87.275 | 98.36 | 8.065 | 7.38 | 0.588 | 0 |
| Puntaje promedio Pruebas Saber 11 - Matemáticas | SABER11_MAT | Educación | 040040001 | 23 | 0 | 0.0 | 51.5564 | 52.04 | 3.2123 | 43.64 | 50.4785 | 53.2968 | 57.49 | 2.8183 | 6.23 | -0.648 | 2 |
| Puntaje promedio Pruebas Saber 11 - Lectura crítica | SABER11_LEC | Educación | 040040002 | 23 | 0 | 0.0 | 53.8678 | 54.4264 | 2.3302 | 47.89 | 53.0478 | 55.0528 | 57.67 | 2.005 | 4.33 | -0.996 | 2 |
| Tasa de tránsito inmediato a la educación superior | TASA_TRAN_EDU_SUP | Educación | 040010028 | 23 | 0 | 0.0 | 46.1631 | 46.22 | 7.3031 | 30.48 | 43.6665 | 49.88 | 61.48 | 6.2135 | 15.82 | -0.08 | 3 |
| Valor agregado per cápita | VA_PC | Economía | 120210002 | 23 | 0 | 0.0 | 15784533.328 | 14912392.01 | 5100896.6464 | 10000311.98 | 11470821.535 | 19006225.435 | 30632130.72 | 7535403.9 | 32.32 | 1.215 | 1 |
| Porcentaje del valor agregado por actividades económicas - Actividades primarias | VA_PCT_PRIM | Economía | 120210008 | 23 | 0 | 0.0 | 3.3509 | 2.98 | 2.7674 | 0.0238 | 0.985 | 4.448 | 9.54 | 3.463 | 82.59 | 0.81 | 0 |
| Porcentaje del valor agregado por actividades económicas - Actividades secundarias | VA_PCT_SEC | Economía | 120210009 | 23 | 0 | 0.0 | 18.0679 | 15.45 | 6.569 | 6.62 | 14.02 | 22.374 | 36.95 | 8.354 | 36.36 | 0.993 | 1 |
| Porcentaje del valor agregado por actividades económicas - Actividades terciarias | VA_PCT_TERC | Economía | 120210010 | 23 | 0 | 0.0 | 78.5851 | 78.74 | 6.0898 | 62.95 | 73.8073 | 83.665 | 86.41 | 9.8577 | 7.75 | -0.632 | 0 |
| Índice de pobreza multidimensional - IPM | IND_POB_MULT | Pobreza | 140010004 | 23 | 0 | 0.0 | 20.877 | 17.6 | 9.848 | 9.0 | 14.3508 | 26.3662 | 45.1 | 12.0154 | 47.17 | 1.281 | 2 |
| Porcentaje población urbana | PCT_URBANA | Demografía y población | 020040003 | 23 | 0 | 0.0 | 90.1886 | 92.4037 | 7.575 | 67.07 | 87.73 | 94.6915 | 99.8666 | 6.9615 | 8.4 | -1.462 | 1 |
| Densidad poblacional | DENS_POB | Demografía y población | 010010010 | 23 | 0 | 0.0 | 1339.7897 | 521.4279 | 1855.6747 | 42.03 | 227.09 | 1601.48 | 7769.6021 | 1374.39 | 138.5 | 2.32 | 2 |
| Porcentaje de población de jóvenes entre 14 y 28 años | PCT_JOVENES | Demografía y población | 020090021 | 23 | 0 | 0.0 | 25.7949 | 25.7473 | 1.4692 | 23.13 | 24.92 | 26.43 | 28.88 | 1.51 | 5.7 | 0.376 | 1 |
| Indicador de desempeño fiscal | IDF | Finanzas públicas | 070100007 | 23 | 0 | 0.0 | 76.8316 | 77.23 | 3.6314 | 68.79 | 74.14 | 78.7614 | 85.32 | 4.6214 | 4.73 | 0.016 | 0 |
| Ingresos tributarios per cápita | ING_TRIB_PC | Finanzas públicas | 070010020 | 23 | 0 | 0.0 | 424684.647 | 352173.66 | 214918.0228 | 108474.55 | 299081.985 | 551304.8297 | 1095947.75 | 252222.8447 | 50.61 | 1.471 | 1 |
| Tasa de homicidios por cada 100.000 habitantes | TASA_HOMICIDIOS | Conflicto armado y seguridad ciudadana | 060010003 | 23 | 0 | 0.0 | 23.5475 | 21.38 | 14.1245 | 4.06 | 15.595 | 24.4409 | 71.96 | 8.8459 | 59.98 | 2.257 | 2 |
| Cobertura de acueducto (Censo) | COB_ACUEDUCTO | Vivienda y acceso a servicios públicos | 030010004 | 23 | 0 | 0.0 | 90.3336 | 95.9427 | 15.8944 | 25.21 | 90.78 | 98.2014 | 99.48 | 7.4214 | 17.6 | -3.496 | 3 |
| Penetración de banda ancha | BANDA_ANCHA | Vivienda y acceso a servicios públicos | 030010003 | 23 | 0 | 0.0 | 17.2778 | 17.69 | 4.7123 | 7.59 | 13.6457 | 21.195 | 24.1113 | 7.5493 | 27.27 | -0.234 | 0 |


## Celda 11

```python
extremos = desc.dominios_extremos(df_cand, CANDIDATAS, entidades, alias=ALIAS)
display(spark.createDataFrame(extremos))
```

**Salida:**

| Alias | Codigo | N_extremos | Dominios |
|---|---|---|---|
| COB_NET_MEDIA | 040010010 | 1 | Riohacha |
| COB_NET_SEC | 040010009 | 0 | — |
| SABER11_MAT | 040040001 | 2 | Quibdó, Riohacha |
| SABER11_LEC | 040040002 | 2 | Quibdó, Riohacha |
| TASA_TRAN_EDU_SUP | 040010028 | 3 | Tunja, Santa Marta, Cali A.M. |
| VA_PC | 120210002 | 1 | Bogotá |
| VA_PCT_PRIM | 120210008 | 0 | — |
| VA_PCT_SEC | 120210009 | 1 | Cartagena |
| VA_PCT_TERC | 120210010 | 0 | — |
| IND_POB_MULT | 140010004 | 2 | Quibdó, Riohacha |
| PCT_URBANA | 020040003 | 1 | Riohacha |
| DENS_POB | 010010010 | 2 | Barranquilla A.M., Bogotá |
| PCT_JOVENES | 020090021 | 1 | Quibdó |
| IDF | 070100007 | 0 | — |
| ING_TRIB_PC | 070010020 | 1 | Bogotá |
| TASA_HOMICIDIOS | 060010003 | 2 | Quibdó, Cali A.M. |
| COB_ACUEDUCTO | 030010004 | 3 | Quibdó, Riohacha, Santa Marta |
| BANDA_ANCHA | 030010003 | 0 | — |


## Celda 12

```python
%md
Los dominios que aparecen en los extremos son territorios reales, no errores de
medición: capitales de gran tamaño, ciudades con historia de conflicto o periferias con
baja cobertura de servicios. Identificarlos es descriptivo. Si alguno de ellos está
además determinando por sí solo la relación entre una covariable y el desempleo es una
pregunta distinta, que se responde con el diagnóstico de influencia en la etapa
siguiente. Ninguna observación se elimina en este notebook ni en el siguiente.
```


## Celda 13

```python
%md
## 2.3 Panel de diagramas de caja de las candidatas

**Cómo leer la figura.** Cada fila es una covariable, estandarizada (media 0 y
desviación 1) solo para poder compararlas en un mismo eje; los datos que entran al
modelo no se transforman. Una caja desplazada respecto a la línea vertical del cero y
un bigote más largo hacia un lado indican asimetría; los puntos naranjas son los dominios
extremos según el rango intercuartílico. Las covariables con cajas estrechas y puntos
lejanos son las que concentran su variación en unos pocos territorios.
```


## Celda 14

```python
fig = desc.figura_panel_boxplots(df_cand, CANDIDATAS, alias=ALIAS)
desc.guardar_figura(fig, "desc_boxplots_candidatas", VOLUMEN_FIGURAS)
display(fig)
print(desc.interpretar_boxplots(desc_covariables))
```

**Salida:**

```
  figura guardada: /Volumes/tesis/preprocesamiento/figuras_eda/desc_boxplots_candidatas.png

```
![fig](fig/analisis__analisis_descriptivo_c14_4.png)
```
INTERPRETACIÓN DE LA FIGURA:
  Covariables con distribución aproximadamente simétrica (|asimetría| < 0.5): 4 de 18 (TASA_TRAN_EDU_SUP, PCT_JOVENES, IDF, BANDA_ANCHA).
  Covariables más asimétricas: COB_ACUEDUCTO (-3.50, cola hacia valores bajos); DENS_POB (+2.32, cola hacia valores altos); TASA_HOMICIDIOS (+2.26, cola hacia valores altos).
  Covariables con valores extremos por el criterio del rango intercuartílico: 13; las que más acumulan son TASA_TRAN_EDU_SUP (3), COB_ACUEDUCTO (3), SABER11_MAT (2).
  Mayor dispersión relativa (coeficiente de variación): DENS_POB (138 %), VA_PCT_PRIM (83 %), TASA_HOMICIDIOS (60 %); menor: IDF (5 %), SABER11_LEC (4 %).
  Lectura: una covariable asimétrica o con extremos no se descarta por serlo. Lo que importa es si esos puntos determinan por sí solos su relación con el desempleo, y eso se comprueba en el diagnóstico de robustez de la etapa de selección.

```
![fig](fig/analisis__analisis_descriptivo_c14_5.png)


## Celda 15

```python
%md
# 3. Análisis descriptivo bivariado

Responde a la pregunta: **¿cómo se relacionan las variables entre sí y, en particular,
con la tasa de desempleo?**

Se reportan el coeficiente de Pearson y el de Spearman, y se indica **cuál de los dos
es el interpretable** para cada covariable en lugar de presentar ambos por inercia. El
criterio es explícito: si la covariable tiene valores extremos y las dos medidas
discrepan, la asociación lineal está condicionada por esos puntos y la medida
pertinente es la de rangos; si coinciden, se interpreta Pearson, que es la forma que
supone el componente sintético del modelo.

Los coeficientes son descriptivos. Una asociación no implica causalidad, y ninguna
covariable se incluye ni se excluye aquí por la magnitud de su correlación. La tabla
incluye el signo esperado del catálogo para que la comparación con el observado quede
a la vista; la consecuencia de una discrepancia se decide en la etapa siguiente.
```


## Celda 16

```python
bivariado = desc.tabla_bivariada(df_cand, CANDIDATAS, Y, alias=ALIAS)
bivariado.insert(2, "Dimension", [DIMENSION[c] for c in bivariado["Codigo"]])
bivariado.insert(3, "Signo_esperado", [SIGNO[c] for c in bivariado["Codigo"]])
display(spark.createDataFrame(bivariado))
```

**Salida:**

| Alias | Codigo | Dimension | Signo_esperado | Pearson_r | Spearman_rho | Discrepancia | N_extremos_IQR | Medida_interpretable | Motivo |
|---|---|---|---|---|---|---|---|---|---|
| TASA_HOMICIDIOS | 060010003 | Conflicto armado y seguridad ciudadana | + | 0.519 | 0.393 | 0.125 | 2 | Spearman | valores extremos condicionan la relación lineal |
| COB_ACUEDUCTO | 030010004 | Vivienda y acceso a servicios públicos | - | -0.489 | -0.176 | 0.313 | 3 | Spearman | valores extremos condicionan la relación lineal |
| COB_NET_MEDIA | 040010010 | Educación | - | -0.476 | -0.513 | 0.037 | 1 | Pearson | relación aproximadamente lineal, sin punto dominante |
| IND_POB_MULT | 140010004 | Pobreza | + | 0.441 | 0.184 | 0.257 | 2 | Spearman | valores extremos condicionan la relación lineal |
| VA_PCT_PRIM | 120210008 | Economía | ± | 0.432 | 0.499 | 0.067 | 0 | Pearson | relación aproximadamente lineal, sin punto dominante |
| ING_TRIB_PC | 070010020 | Finanzas públicas | - | -0.421 | -0.489 | 0.068 | 1 | Pearson | relación aproximadamente lineal, sin punto dominante |
| COB_NET_SEC | 040010009 | Educación | - | -0.372 | -0.393 | 0.021 | 0 | Pearson | relación aproximadamente lineal, sin punto dominante |
| VA_PCT_SEC | 120210009 | Economía | ± | -0.367 | -0.286 | 0.081 | 1 | Pearson | relación aproximadamente lineal, sin punto dominante |
| VA_PC | 120210002 | Economía | - | -0.364 | -0.385 | 0.021 | 1 | Pearson | relación aproximadamente lineal, sin punto dominante |
| TASA_TRAN_EDU_SUP | 040010028 | Educación | - | 0.36 | 0.425 | 0.065 | 3 | Pearson | relación aproximadamente lineal, sin punto dominante |
| IDF | 070100007 | Finanzas públicas | - | -0.315 | -0.406 | 0.091 | 0 | Pearson | relación aproximadamente lineal, sin punto dominante |
| PCT_JOVENES | 020090021 | Demografía y población | + | 0.309 | 0.211 | 0.098 | 1 | Pearson | relación aproximadamente lineal, sin punto dominante |
| SABER11_LEC | 040040002 | Educación | - | -0.305 | -0.085 | 0.22 | 2 | Spearman | valores extremos condicionan la relación lineal |
| DENS_POB | 010010010 | Demografía y población | ± | -0.282 | -0.358 | 0.075 | 2 | Pearson | relación aproximadamente lineal, sin punto dominante |
| SABER11_MAT | 040040001 | Educación | - | -0.269 | -0.068 | 0.201 | 2 | Spearman | valores extremos condicionan la relación lineal |
| VA_PCT_TERC | 120210010 | Economía | ± | 0.2 | 0.138 | 0.061 | 0 | Pearson | relación aproximadamente lineal, sin punto dominante |
| BANDA_ANCHA | 030010003 | Vivienda y acceso a servicios públicos | - | -0.121 | -0.078 | 0.043 | 0 | Pearson | relación aproximadamente lineal, sin punto dominante |
| PCT_URBANA | 020040003 | Demografía y población | + | -0.017 | 0.052 | 0.069 | 1 | Pearson | relación aproximadamente lineal, sin punto dominante |


## Celda 17

```python
%md
## 3.1 Panel de dispersión de las candidatas frente a la respuesta

**Cómo leer la figura.** Cada panel enfrenta una covariable (eje horizontal) con la
tasa de desempleo (eje vertical); cada punto es un dominio y la recta discontinua es
el ajuste de mínimos cuadrados, la misma forma lineal que usa el componente sintético
del modelo. Cada panel trae Pearson (r) y Spearman (ρ_S): cuando difieren de forma
apreciable, la relación lineal depende de unos pocos puntos alejados. Conviene fijarse
en tres cosas: la pendiente de la recta (dirección de la asociación), cuánto se
dispersan los puntos alrededor de ella (fuerza) y si hay un dominio aislado que parece
sostener la pendiente por sí solo (candidato a influyente).
```


## Celda 18

```python
# D-12: con las 18 candidatas en una sola figura el texto quedaba ilegible; se parten en dos
# figuras de hasta nueve paneles (desc_dispersion_candidatas_1 y _2).
mitad = (len(CANDIDATAS) + 1) // 2
for parte, grupo in enumerate([CANDIDATAS[:mitad], CANDIDATAS[mitad:]], 1):
    if not grupo:
        continue
    fig = desc.figura_panel_dispersion(df_cand, grupo, Y, alias=ALIAS)
    desc.guardar_figura(fig, f"desc_dispersion_candidatas_{parte}", VOLUMEN_FIGURAS)
    display(fig)
print(desc.interpretar_dispersion(bivariado, SIGNO))
```

**Salida:**

```
  figura guardada: /Volumes/tesis/preprocesamiento/figuras_eda/desc_dispersion_candidatas_1.png

```
![fig](fig/analisis__analisis_descriptivo_c18_6.png)
```
  figura guardada: /Volumes/tesis/preprocesamiento/figuras_eda/desc_dispersion_candidatas_2.png

```
![fig](fig/analisis__analisis_descriptivo_c18_7.png)
```
INTERPRETACIÓN DE LA FIGURA:
  Asociación fuerte (|r| >= 0.5): 0.
  Asociación moderada (0.3 <= |r| < 0.5): 10 — COB_NET_MEDIA (-0.48), VA_PCT_PRIM (+0.43), ING_TRIB_PC (-0.42), TASA_HOMICIDIOS (+0.39), COB_NET_SEC (-0.37), VA_PCT_SEC (-0.37), VA_PC (-0.36), TASA_TRAN_EDU_SUP (+0.36), IDF (-0.32), PCT_JOVENES (+0.31).
  Asociación débil o nula (|r| < 0.3): 8 — DENS_POB (-0.28), VA_PCT_TERC (+0.20), IND_POB_MULT (+0.18), COB_ACUEDUCTO (-0.18), BANDA_ANCHA (-0.12), SABER11_LEC (-0.09), SABER11_MAT (-0.07), PCT_URBANA (-0.02).
  Covariables cuya relación lineal está condicionada por valores extremos (se lee Spearman): 5 — TASA_HOMICIDIOS, IND_POB_MULT, COB_ACUEDUCTO, SABER11_LEC, SABER11_MAT.
  Covariables cuyo signo observado contradice el mecanismo del catálogo: 2 — TASA_TRAN_EDU_SUP, PCT_URBANA.
  Lectura: en la recta de referencia de cada panel se ve la dirección de la asociación; los puntos que se apartan del patrón son los dominios que después se examinan con la distancia de Cook. Ninguna covariable se incluye ni se excluye aquí por su coeficiente.

```
![fig](fig/analisis__analisis_descriptivo_c18_8.png)
![fig](fig/analisis__analisis_descriptivo_c18_9.png)


## Celda 19

```python
%md
# 4. Análisis descriptivo multivariado

Responde a la pregunta: **¿qué estructura conjunta presentan las covariables que no se
aprecia al mirarlas de una en una o por pares?**

La caracterización multivariada es una matriz de correlación reordenada por
agrupamiento jerárquico, de modo que las covariables que miden aspectos parecidos del
territorio queden contiguas y los bloques se vean como tales. Es una técnica
descriptiva, sin parámetros que ajustar ni decisiones arbitrarias, y responde a una
pregunta que el proyecto necesita contestar: qué grupos de indicadores están midiendo
lo mismo. Esos bloques son el insumo del criterio de redundancia de la etapa siguiente.

**No se aplica análisis de componentes principales.** Introduciría componentes sin
interpretación territorial directa y una decisión adicional —cuántos componentes
retener— que esta etapa no necesita.

**Cómo leer la figura.** Naranja indica correlación positiva y azul negativa; la
intensidad, la magnitud. Se muestra el triángulo inferior, porque la matriz es
simétrica. Los bloques de color intenso junto a la diagonal son grupos de covariables
que miden lo mismo; un bloque azul intenso lejos de la diagonal señala dos indicadores
que miden lo mismo en sentido inverso.
```


## Celda 20

```python
fig, orden_agrupado = desc.figura_correlacion_agrupada(df_cand, CANDIDATAS, alias=ALIAS)
desc.guardar_figura(fig, "desc_correlacion_candidatas", VOLUMEN_FIGURAS)
display(fig)
```

**Salida:**

```
  figura guardada: /Volumes/tesis/preprocesamiento/figuras_eda/desc_correlacion_candidatas.png

```
![fig](fig/analisis__analisis_descriptivo_c20_10.png)
![fig](fig/analisis__analisis_descriptivo_c20_11.png)


## Celda 21

```python
pares = desc.tabla_pares_correlacionados(
    df_cand, CANDIDATAS, alias=ALIAS, umbral=UMBRAL_REDUNDANCIA
)
display(
    spark.createDataFrame(pares)
    if not pares.empty
    else spark.createDataFrame(
        pd.DataFrame([{"Mensaje": f"Ningún par supera |r| = {UMBRAL_REDUNDANCIA}"}])
    )
)
print(
    desc.interpretar_correlacion(
        pares, orden_agrupado, ALIAS, umbral=UMBRAL_REDUNDANCIA
    )
)
```

**Salida:**

| Variable_1 | Variable_2 | Correlacion |
|---|---|---|
| SABER11_MAT | SABER11_LEC | 0.97 |
| VA_PC | ING_TRIB_PC | 0.931 |
| VA_PCT_SEC | VA_PCT_TERC | -0.907 |
| SABER11_LEC | IND_POB_MULT | -0.85 |
| IND_POB_MULT | BANDA_ANCHA | -0.828 |
| IDF | ING_TRIB_PC | 0.813 |
```
INTERPRETACIÓN DE LA FIGURA:
  Pares con |r| >= 0.8: 6. Los más fuertes: SABER11_MAT – SABER11_LEC (+0.97); VA_PC – ING_TRIB_PC (+0.93); VA_PCT_SEC – VA_PCT_TERC (-0.91); SABER11_LEC – IND_POB_MULT (-0.85).
  3 de esos pares tienen correlación negativa: miden el mismo aspecto en sentido inverso (por ejemplo, una carencia y su cobertura).
  Lectura: en el mapa reordenado esos pares aparecen como bloques contiguos de color intenso. De cada bloque entrará una sola covariable al modelo; cuál, se decide en la etapa de selección.
  Orden de presentación (covariables parecidas quedan juntas): TASA_TRAN_EDU_SUP · VA_PCT_SEC · VA_PCT_TERC · PCT_URBANA · VA_PCT_PRIM · DENS_POB · IDF · VA_PC · ING_TRIB_PC · PCT_JOVENES · IND_POB_MULT · BANDA_ANCHA · COB_ACUEDUCTO · SABER11_MAT · SABER11_LEC · TASA_HOMICIDIOS · COB_NET_MEDIA · COB_NET_SEC.

```


## Celda 22

```python
%md
Estos pares señalan información potencialmente redundante. **Ninguna covariable se
descarta por aparecer aquí.** La decisión formal sobre cuál conservar de cada grupo se
toma en la etapa de selección, con un criterio de desempate explícito.
```


## Celda 23

```python
(
    spark.createDataFrame(
        pd.concat(
            [
                desc_respuesta.assign(
                    Bloque="Variable respuesta y precisión", Alias=None, Dimension=None
                ),
                desc_covariables.assign(Bloque="Covariables candidatas"),
            ],
            ignore_index=True,
        )
    )
    .write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TBL_DESCRIPTIVO_UNI)
)

(
    spark.createDataFrame(bivariado)
    .write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TBL_DESCRIPTIVO_BI)
)

print(f"Tablas escritas:\n  · {TBL_DESCRIPTIVO_UNI}\n  · {TBL_DESCRIPTIVO_BI}")
print(f"Candidatas caracterizadas: {len(CANDIDATAS)}")
```

**Salida:**

```
Tablas escritas:
  · tesis.preprocesamiento.descriptivo_univariado
  · tesis.preprocesamiento.descriptivo_bivariado
Candidatas caracterizadas: 18

```
