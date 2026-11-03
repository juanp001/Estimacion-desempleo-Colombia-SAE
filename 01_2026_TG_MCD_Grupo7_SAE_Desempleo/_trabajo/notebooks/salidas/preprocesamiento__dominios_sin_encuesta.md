# preprocesamiento__dominios_sin_encuesta


## Celda 0



## Celda 1



## Celda 2


**Salida:**

```
Período de las estimaciones: 2018-12
Covariables pre-filtradas: 497
Dominios con estimación directa: 23

```


## Celda 3


**Salida:**

```
Municipios con estimación directa propia (excluidos): ['11001', '13001', '15001', '18001', '19001', '20001', '23001', '27001', '41001', '44001', '47001', '50001', '52001', '63001', '70001', '73001']
Dominios de varios municipios en los departamentos objetivo: ['76001']

```


## Celda 4


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


**Salida:**

```
Tabla escrita: tesis.preprocesamiento.municipios_sin_encuesta  (83 municipios)

```
