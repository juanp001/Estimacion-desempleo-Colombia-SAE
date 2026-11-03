# preprocesamiento__dominios_sin_encuesta


## Celda 0

```python
%md
# Municipios objetivo sin estimación directa propia

Construye la tabla de covariables **municipales** de los municipios de Cauca y Valle del Cauca
que recibirán una estimación sintética, es decir, los que no tienen una estimación directa
propia de la GEIH.

## Por qué existe este notebook

La predicción sintética del modelo necesita las covariables de los municipios que no
tienen estimación directa. Para que el paso sea reproducible desde el código y no
quede acoplado a un conjunto concreto de covariables (de modo que un cambio en la
selección no lo rompa), la tabla se deriva de las fuentes con **todas** las
covariables que superaron el pre-filtrado y conservando los códigos de indicador. El
notebook del modelo toma después las que necesite y las renombra, de forma que la
predicción sintética funciona con cualquier conjunto seleccionado.

## Definición de los municipios objetivo

Los dominios con estimación directa son ciudades o ciudades con su área metropolitana
(`tesis.dim.dim_dominio_geih`). Un municipio tiene estimación directa **propia** solo si él
solo forma un dominio con muestra (Popayán). Los municipios de un área metropolitana (Cali y
Yumbo en Cali A.M.) **no** la tienen: la GEIH pública no identifica el municipio dentro del
A.M., así que su muestra solo da la tasa del conjunto.

Por eso la tabla contiene:

* los municipios de los departamentos objetivo presentes en TerriData para el período, menos
  los que forman por sí solos un dominio con estimación directa;
* todos los miembros de cualquier dominio de varios municipios con estimación directa que toque
  los departamentos objetivo, con `CODIGO_DOMINIO_PADRE` igual al código de ese dominio.

Yumbo no se excluye ni recibe la tasa de Cali A.M.: el DANE da estimación propia a cada
municipio de un A.M. y la hace coherente con la de la ciudad mediante benchmarking (nota SAE
2024, PDF 25); el modelo anidado (Morales et al., p. 462) exigiría estimaciones directas por
municipio, que no existen, y asignarle la tasa del A.M. sería el sintético básico, sesgado si
Yumbo difiere de Cali (Morales et al., p. 42). Los miembros con padre se ajustan al valor de su
dominio en el benchmarking de nivel 2 del modelo, que exige que estén **todos**.

Las covariables son las del municipio (sin agregar): el modelo predice con x_m'β̂.

## Período (R-26)

El año y el mes salen de `covariables_prefiltradas`, que trae el período de la estimación
directa. Los widgets `anio_estimacion` / `mes_estimacion` solo se comparan con él: si no
coinciden, el notebook se detiene en vez de escribir objetivos de otro período.

## Salida

* `tesis.preprocesamiento.municipios_sin_encuesta`
```


## Celda 1

```python
import os
import sys

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

# R-61: nombres explícitos en vez de «import *»
from preprocesamiento.shared.config import (
    DEPARTAMENTOS_OBJETIVO,
    METADATA_COLS,
    TBL_DIM_DOMINIO,
    TBL_PREFILTRADAS,
    TBL_SIN_ENCUESTA,
    TBL_TERRIDATA,
    resolver_periodo,
)

# Período del widget / parámetro del job; abajo se compara con el de las estimaciones (R-26).
PER_WIDGET, MES_WIDGET = resolver_periodo(dbutils)
```


## Celda 2

```python
df_prefiltradas = spark.table(TBL_PREFILTRADAS)
codigos_prefiltrados = [c for c in df_prefiltradas.columns if c not in METADATA_COLS]

# R-26: el período sale de las estimaciones (covariables_prefiltradas trae PER/MES de la
# estimación directa), no del widget. Si se corre a mano con el valor por defecto (2018-12)
# después de estimar otro período, los objetivos quedarían de otro año: se detiene.
periodos = df_prefiltradas.select("PER", "MES").distinct().collect()
if len(periodos) != 1:
    raise ValueError(
        f"{TBL_PREFILTRADAS} debe tener un solo período y tiene {len(periodos)}: {periodos}"
    )
PER_ESTIMACION, MES_ESTIMACION = int(periodos[0]["PER"]), int(periodos[0]["MES"])
if (PER_WIDGET, MES_WIDGET) != (PER_ESTIMACION, MES_ESTIMACION):
    raise ValueError(
        f"El período del widget ({PER_WIDGET}-{MES_WIDGET:02d}) no coincide con el de las "
        f"estimaciones ({PER_ESTIMACION}-{MES_ESTIMACION:02d}). Corra con el mismo período o "
        "vuelva a correr estimacion_directa y el pre-filtrado."
    )
print(f"Período de las estimaciones: {PER_ESTIMACION}-{MES_ESTIMACION:02d}")

dominios_con_encuesta = {
    fila["CODIGO_DOMINIO"]
    for fila in df_prefiltradas.select("CODIGO_DOMINIO").distinct().collect()
}

print(f"Covariables pre-filtradas: {len(codigos_prefiltrados)}")
print(f"Dominios con estimación directa: {len(dominios_con_encuesta)}")
```

**Salida:**

```
Período de las estimaciones: 2018-12
Covariables pre-filtradas: 497
Dominios con estimación directa: 23

```


## Celda 3

```python
# Para cada municipio de un dominio con encuesta: si el dominio tiene un solo municipio, ese
# municipio ya tiene estimación directa propia y se excluye; si tiene varios, el municipio necesita
# estimación propia y queda con el dominio como padre del benchmarking de nivel 2.
df_miembros = spark.table(TBL_DIM_DOMINIO).filter(
    F.col("CODIGO_DOMINIO").isin(list(dominios_con_encuesta))
)
n_por_dominio = df_miembros.groupBy("CODIGO_DOMINIO").agg(
    F.count("*").alias("N_MUNICIPIOS")
)
df_miembros = df_miembros.join(n_por_dominio, on="CODIGO_DOMINIO")

municipios_con_directa_propia = [
    fila["CODIGO_MUNICIPIO"]
    for fila in df_miembros.filter(F.col("N_MUNICIPIOS") == 1)
    .select("CODIGO_MUNICIPIO")
    .collect()
]

df_padres = df_miembros.filter(F.col("N_MUNICIPIOS") > 1).select(
    "CODIGO_MUNICIPIO", F.col("CODIGO_DOMINIO").alias("CODIGO_DOMINIO_PADRE")
)

# Dominios de varios municipios que tocan los departamentos objetivo: entran todos sus miembros,
# aunque alguno estuviera en otro departamento, para que el benchmarking de nivel 2 sea completo.
padres_objetivo = [
    fila["CODIGO_DOMINIO"]
    for fila in df_miembros.filter(
        (F.col("N_MUNICIPIOS") > 1)
        & F.col("CODIGO_DEPARTAMENTO").cast("int").isin(DEPARTAMENTOS_OBJETIVO)
    )
    .select("CODIGO_DOMINIO")
    .distinct()
    .collect()
]
miembros_padres_objetivo = [
    fila["CODIGO_MUNICIPIO"]
    for fila in df_padres.filter(F.col("CODIGO_DOMINIO_PADRE").isin(padres_objetivo))
    .select("CODIGO_MUNICIPIO")
    .collect()
]

print(
    f"Municipios con estimación directa propia (excluidos): {sorted(municipios_con_directa_propia)}"
)
print(
    f"Dominios de varios municipios en los departamentos objetivo: {sorted(padres_objetivo)}"
)
```

**Salida:**

```
Municipios con estimación directa propia (excluidos): ['11001', '13001', '15001', '18001', '19001', '20001', '23001', '27001', '41001', '44001', '47001', '50001', '52001', '63001', '70001', '73001']
Dominios de varios municipios en los departamentos objetivo: ['76001']

```


## Celda 4

```python
df_terridata = spark.table(TBL_TERRIDATA)

df_objetivo = (
    df_terridata.filter(F.col("ANO") == PER_ESTIMACION)
    .filter(F.col("MES") == MES_ESTIMACION)
    .filter(
        F.col("CODIGO_DEPARTAMENTO").cast("int").isin(DEPARTAMENTOS_OBJETIVO)
        | F.col("CODIGO_ENTIDAD").isin(miembros_padres_objetivo)
    )
    # TerriData incluye, junto a los municipios, una fila agregada por departamento cuyo
    # código DIVIPOLA termina en 000 (19000 para Cauca, 76000 para Valle del Cauca). No es un
    # dominio de estimación y se excluye; de lo contrario aparecería entre las estimaciones
    # sintéticas como si fuera un municipio más.
    .filter(F.col("CODIGO_ENTIDAD").cast("int") % 1000 != 0)
    .filter(~F.col("CODIGO_ENTIDAD").isin(municipios_con_directa_propia))
    .join(
        df_padres.withColumnRenamed("CODIGO_MUNICIPIO", "CODIGO_ENTIDAD"),
        on="CODIGO_ENTIDAD",
        how="left",
    )
    .select(
        F.col("ANO").alias("PER"),
        F.col("MES"),
        F.col("CODIGO_DEPARTAMENTO"),
        F.col("DEPARTAMENTO"),
        F.col("CODIGO_ENTIDAD").alias("CODIGO_MUNICIPIO"),
        F.col("ENTIDAD").alias("MUNICIPIO"),
        F.col("CODIGO_DOMINIO_PADRE"),
        # try_cast: un texto en un indicador queda NULL y se reporta como faltante abajo.
        *[F.expr(f"try_cast(`{c}` AS DOUBLE)").alias(c) for c in codigos_prefiltrados],
    )
)

n_objetivo = df_objetivo.count()
print(f"Municipios objetivo sin estimación directa propia: {n_objetivo}")

if n_objetivo == 0:
    raise ValueError(
        f"No se encontraron municipios objetivo para ANO={PER_ESTIMACION}, "
        f"MES={MES_ESTIMACION} en los departamentos {DEPARTAMENTOS_OBJETIVO}. "
        f"Verificar el período disponible en {TBL_TERRIDATA}."
    )

# Todos los miembros de cada padre deben estar: el benchmarking de nivel 2 reparte la tasa del
# dominio entre sus municipios y un miembro ausente lo haría incorrecto.
con_padre = {
    fila["CODIGO_MUNICIPIO"]
    for fila in df_objetivo.filter(F.col("CODIGO_DOMINIO_PADRE").isNotNull())
    .select("CODIGO_MUNICIPIO")
    .collect()
}
faltan_miembros = sorted(set(miembros_padres_objetivo) - con_padre)
if faltan_miembros:
    raise ValueError(
        f"Miembros de dominios A.M. sin fila en TerriData para el período: {faltan_miembros}. "
        f"El benchmarking de nivel 2 necesita todos los municipios del dominio."
    )

print(f"  con dominio padre (benchmarking de nivel 2): {len(con_padre)}")
display(
    df_objetivo.select(
        "CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO", "CODIGO_DOMINIO_PADRE"
    ).orderBy("CODIGO_MUNICIPIO")
)
```

**Salida:**

```
Municipios objetivo sin estimación directa propia: 83
  con dominio padre (benchmarking de nivel 2): 2

```
| CODIGO_MUNICIPIO | DEPARTAMENTO | MUNICIPIO | CODIGO_DOMINIO_PADRE |
|---|---|---|---|
| 19022 | Cauca | Almaguer | None |
| 19050 | Cauca | Argelia | None |
| 19075 | Cauca | Balboa | None |
| 19100 | Cauca | Bolívar | None |
| 19110 | Cauca | Buenos Aires | None |
| 19130 | Cauca | Cajibío | None |
| 19137 | Cauca | Caldono | None |
| 19142 | Cauca | Caloto | None |
| 19212 | Cauca | Corinto | None |
| 19256 | Cauca | El Tambo | None |
| 19290 | Cauca | Florencia | None |
| 19300 | Cauca | Guachené | None |
| 19318 | Cauca | Guapi | None |
| 19355 | Cauca | Inzá | None |
| 19364 | Cauca | Jambaló | None |
| 19392 | Cauca | La Sierra | None |
| 19397 | Cauca | La Vega | None |
| 19418 | Cauca | López | None |
| 19450 | Cauca | Mercaderes | None |
| 19455 | Cauca | Miranda | None |
| 19473 | Cauca | Morales | None |
| 19513 | Cauca | Padilla | None |
| 19517 | Cauca | Paéz | None |
| 19532 | Cauca | Patía | None |
| 19533 | Cauca | Piamonte | None |
| 19548 | Cauca | Piendamó | None |
| 19573 | Cauca | Puerto Tejada | None |
| 19585 | Cauca | Puracé | None |
| 19622 | Cauca | Rosas | None |
| 19693 | Cauca | San Sebastián | None |
| 19698 | Cauca | Santander de Quilichao | None |
| 19701 | Cauca | Santa Rosa | None |
| 19743 | Cauca | Silvia | None |
| 19760 | Cauca | Sotará | None |
| 19780 | Cauca | Suárez | None |
| 19785 | Cauca | Sucre | None |
| 19807 | Cauca | Timbío | None |
| 19809 | Cauca | Timbiquí | None |
| 19821 | Cauca | Toribío | None |
| 19824 | Cauca | Totoró | None |
| 19845 | Cauca | Villa Rica | None |
| 76001 | Valle del Cauca | Cali | 76001 |
| 76020 | Valle del Cauca | Alcalá | None |
| 76036 | Valle del Cauca | Andalucía | None |
| 76041 | Valle del Cauca | Ansermanuevo | None |
| 76054 | Valle del Cauca | Argelia | None |
| 76100 | Valle del Cauca | Bolívar | None |
| 76109 | Valle del Cauca | Buenaventura | None |
| 76111 | Valle del Cauca | Guadalajara de Buga | None |
| 76113 | Valle del Cauca | Bugalagrande | None |
| 76122 | Valle del Cauca | Caicedonia | None |
| 76126 | Valle del Cauca | Calima | None |
| 76130 | Valle del Cauca | Candelaria | None |
| 76147 | Valle del Cauca | Cartago | None |
| 76233 | Valle del Cauca | Dagua | None |
| 76243 | Valle del Cauca | El Águila | None |
| 76246 | Valle del Cauca | El Cairo | None |
| 76248 | Valle del Cauca | El Cerrito | None |
| 76250 | Valle del Cauca | El Dovio | None |
| 76275 | Valle del Cauca | Florida | None |
| 76306 | Valle del Cauca | Ginebra | None |
| 76318 | Valle del Cauca | Guacarí | None |
| 76364 | Valle del Cauca | Jamundí | None |
| 76377 | Valle del Cauca | La Cumbre | None |
| 76400 | Valle del Cauca | La Unión | None |
| 76403 | Valle del Cauca | La Victoria | None |
| 76497 | Valle del Cauca | Obando | None |
| 76520 | Valle del Cauca | Palmira | None |
| 76563 | Valle del Cauca | Pradera | None |
| 76606 | Valle del Cauca | Restrepo | None |
| 76616 | Valle del Cauca | Riofrío | None |
| 76622 | Valle del Cauca | Roldanillo | None |
| 76670 | Valle del Cauca | San Pedro | None |
| 76736 | Valle del Cauca | Sevilla | None |
| 76823 | Valle del Cauca | Toro | None |
| 76828 | Valle del Cauca | Trujillo | None |
| 76834 | Valle del Cauca | Tuluá | None |
| 76845 | Valle del Cauca | Ulloa | None |
| 76863 | Valle del Cauca | Versalles | None |
| 76869 | Valle del Cauca | Vijes | None |
| 76890 | Valle del Cauca | Yotoco | None |
| 76892 | Valle del Cauca | Yumbo | 76001 |
| 76895 | Valle del Cauca | Zarzal | None |


## Celda 5

```python
# Una covariable con faltantes en los dominios objetivo no puede usarse para predecir en
# ellos, aunque estuviera completa en los dominios con encuesta. Se reporta aquí para que
# la etapa de selección pueda tenerlo en cuenta si el conjunto elegido resulta afectado.
conteos = (
    df_objetivo.select(
        [F.sum(F.col(c).isNull().cast("int")).alias(c) for c in codigos_prefiltrados]
    )
    .collect()[0]
    .asDict()
)

incompletas = {k: v for k, v in conteos.items() if v > 0}
print(
    f"Covariables con faltantes en los dominios objetivo: {len(incompletas)} de "
    f"{len(codigos_prefiltrados)}"
)
if incompletas:
    ejemplos = list(incompletas.items())[:15]
    print("  ejemplos (código: n.º de municipios sin dato):")
    for codigo, n in ejemplos:
        print(f"    {codigo}: {n}")
```

**Salida:**

```
Covariables con faltantes en los dominios objetivo: 19 de 497
  ejemplos (código: n.º de municipios sin dato):
    050020003: 13
    050020006: 4
    050020014: 9
    060010013: 3
    060010014: 3
    060010016: 18
    060020002: 1
    060020003: 2
    060020004: 4
    060020005: 4
    060020006: 7
    060020007: 7
    060020013: 23
    060020014: 20
    060020017: 46

```


## Celda 6

```python
(
    df_objetivo.write.mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TBL_SIN_ENCUESTA)
)

print(f"Tabla escrita: {TBL_SIN_ENCUESTA}  ({n_objetivo} municipios)")
```

**Salida:**

```
Tabla escrita: tesis.preprocesamiento.municipios_sin_encuesta  (83 municipios)

```
