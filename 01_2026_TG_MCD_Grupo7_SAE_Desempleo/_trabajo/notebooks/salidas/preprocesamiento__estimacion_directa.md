# preprocesamiento__estimacion_directa


## Celda 0

θ̂ = Σ(w_i × y_i) / Σ(w_i)
```

Donde:
* `w_i`: Peso de expansión `FEX_C18` (factor 2018) de la observación i; solo personas de 15 años o más
* `y_i`: Variable binaria (1 = desocupado, 0 = ocupado)

Es una razón de dos totales estimados: si ambos son consistentes, θ̂ es aproximadamente
insesgado y, con muestra grande, su varianza se aproxima por linealización de Taylor (Morales
et al., 2021, pp. 21-22, Prop. 2.4).

## Bootstrap por viviendas dentro del dominio (G7-B3)

**Procedimiento** (`shared/bootstrap.py`):
1. Calcular θ̂ en la muestra original
2. Crear B réplicas: en cada dominio, remuestrear **con reemplazo** tantas viviendas
   (`ID_VIVIENDA`) como tiene la muestra del dominio, con todas sus personas, y calcular θ̂_b
3. SE = desv. estándar de {θ̂_1, ..., θ̂_B}
4. IC 95% = [percentil 2.5%, percentil 97.5%]

**Por qué así.** La GEIH encuesta conglomerados completos (todas las viviendas, hogares y
personas del segmento; metodología v9, PDF 11), así que las personas de una vivienda no son
independientes y se remuestrean juntas (Morales et al., 2021, p. 61). Las A.M. y capitales son
de inclusión forzosa con estimaciones separadas (PDF 11): cada dominio actúa como estrato y su
tamaño de muestra queda fijo en cada réplica.

**Control.** `SE_TAYLOR_PCT` es la varianza por linealización de Taylor de la razón con las
mismas unidades: una adaptación de la fórmula de la GEIH (PDF 15), que usa los segmentos dentro
de cada estrato, con la vivienda como conglomerado. Con miles de viviendas por dominio ambas
deben coincidir.

**Limitación.** La varianza oficial depende de rasgos del diseño que aquí no se reproducen:
* el estrato interno y el segmento (~10 viviendas contiguas), que son las unidades de la fórmula
  oficial y no vienen en los microdatos (PDF 14-15);
* la calibración del factor de expansión: el DANE ajusta el FEX por regresión generalizada
  (CLAN 97) a las proyecciones de población por sexo y edad (PDF 13-14), y la varianza oficial
  tiene en cuenta ese ajuste. Aquí los pesos quedan fijos en cada réplica, mientras que en los
  métodos de remuestreo para encuestas de fuerza laboral cada réplica se recalibra igual que la
  muestra (Morales et al., 2021, p. 61) (R-25).

La varianza es una aproximación: no se sabe si la del diseño es mayor o menor, ni por cuánto.
El notebook `modelo/sensibilidad_varianza.py` muestra cómo responde el modelo si se equivoca.

**Número de réplicas**: B = 2000 (ver `shared/config.py`). Con esa B el error Monte Carlo de
la varianza bootstrap es de ≈ √(2/B) ≈ 3 %; la celda de control lo compara con Taylor.

## Parámetros Configurables

Ver `shared/config.py`:
* `BOOTSTRAP_REPLICAS`: Número de réplicas (default 2000)
* `BOOTSTRAP_SEED`: Semilla aleatoria (default 42)
* `PER_ESTIMACION`, `MES_ESTIMACION`: Año y mes de **cierre** de la ventana (defaults 2018 / 12).
  Se cambian con los parámetros `anio_estimacion` y `mes_estimacion` del job (`resolver_periodo`)
* `N_MESES_VENTANA`: meses de la ventana, 12 (año, por defecto) o 3 (trimestre móvil). Se cambia con
  el parámetro `n_meses_ventana` (`resolver_ventana`); el año exige `mes_estimacion = 12`. Los
  trimestres pueden cruzar el año (2019 / 1 → Nov 2018 - Ene 2019), igual que la hoja «areas trim
  movil» del anexo DANE (`meses_ventana`)
* `GRUPO_COLS`: Columnas que definen los dominios

## Interpretación del CV

```
CV = (SE / Estimación) × 100
```

* **CV < 5%**: Estimación CONFIABLE ✅
* **5% ≤ CV < 20%**: Estimación ACEPTABLE ⚠️
* **CV ≥ 20%**: Estimación NO CONFIABLE ❌

Sustento (G7-B7, detalle en `shared/config.py`): 5 % es la precisión de diseño de la GEIH para
la tasa de desempleo (DANE, Metodología GEIH v9, PDF 12) y 20 % el límite de «no publicable»
de varios institutos de estadística (Molina, 2019, CEPAL, PDF 16-17).

## Flujo de Datos

```
tesis.geih_oro.mercado_laboral
  → filter(PEA == 1, EDAD >= 15, meses de la ventana que cierra en anio_estimacion/mes_estimacion)
  → INNER JOIN tesis.dim.dim_dominio_geih (fila de la capital) → CODIGO_DOMINIO, NOMBRE_DOMINIO, TIPO_DOMINIO
  → FEX := FEX_C18; PER, MES := año y mes de cierre de la ventana
  → EstimacionDirecta.estimar()   [bootstrap por viviendas, 2000 réplicas + Taylor]
  → + PERIODO, N_MESES_VENTANA, N_PEA, N_DESOCUPADOS, N_VIVIENDAS (muestra), PEA_EXPANDIDA
    (Σ FEX_C18 de la PEA / meses) y N_MUNICIPIOS del dominio
  → validación contra el DANE (año: TD reconstruida con los 4 trimestres; trimestre: publicada)
  → tesis.preprocesamiento.tasa_desempleo_municipal   (una fila por dominio)
```

`PEA_EXPANDIDA` es la PEA promedio mensual de la ventana que representa la muestra del dominio. Es el
peso del benchmarking de nivel 1 en `modelo/fay_herriot.py`: con él, el promedio ponderado de
las tasas directas de los dominios reproduce exactamente la tasa directa del conjunto (propiedad
de benchmarking de los estimadores directos, Molina 2019, CEPAL, PDF 26).

## Referencias

* Morales, D. et al. (2021). *A Course on Small Area Estimation and Mixed Models*. Springer
  (pp. 21-22: estimador de razón; p. 61: remuestreo en encuestas de fuerza laboral).
* DANE (2016). Metodología General GEIH v9 (PDF 9: dominios; PDF 11-15: diseño, calibración y
  varianza).
* Molina, I. (2019). *Desagregación de datos en encuestas de hogares: metodologías de estimación
  en áreas pequeñas*. CEPAL, Serie Estudios Estadísticos 97 (PDF 16-17: CV; PDF 26: benchmarking
  de los directos).
```


## Celda 1


**Salida:**

```
Período a estimar: Ene-Dic 2018 (12 meses con cierre en 2018-12)

```


## Celda 2


**Salida:**

```
Meses de la ventana: 2018-01, 2018-02, 2018-03, 2018-04, 2018-05, 2018-06, 2018-07, 2018-08, 2018-09, 2018-10, 2018-11, 2018-12
✔ Los 23 dominios tienen los 12 meses de la ventana
Observaciones PEA: 314,744
Dominios con muestra: 23

```


## Celda 3


**Salida:**

```
Convirtiendo a Pandas...
Datos: 314,744 filas — 23 dominios — remuestreo por conglomerado ID_VIVIENDA

✔ Bootstrap: 2,000 réplicas por dominio — 23 dominios estimados
Aproximación a la varianza del diseño: no reproduce el estrato interno, el segmento ni la calibración del FEX de la GEIH (G7-B3, R-25).

```


## Celda 4


**Salida:**

```
Dominios estimados: 23
  ciudades A.M.: 7
Período: Ene-Dic 2018 (cierre 2018-12)
Muestra: PEA mínima 8,997, desocupados mínimo 1,062

Calidad de estimaciones (CV):
  Confiables  (CV < 5.0%): 23
  Aceptables  (5.0% ≤ CV < 20.0%): 0
  No confiables (CV ≥ 20.0%): 0

```
| PER | MES | PERIODO | N_MESES_VENTANA | CODIGO_DEPARTAMENTO | DEPARTAMENTO | CODIGO_DOMINIO | NOMBRE_DOMINIO | TIPO_DOMINIO | TASA_DESEMPLEO_PCT | SE_BOOTSTRAP_PCT | IC_INF_PCT | IC_SUP_PCT | AMPLITUD_IC | CV_PORCENTAJE | SE_TAYLOR_PCT | N_VIVIENDAS | N_PEA | N_DESOCUPADOS | PEA_EXPANDIDA | N_MUNICIPIOS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | 12 | Ene-Dic 2018 | 12 | 05 | ANTIOQUIA | 05001 | Medellín A.M. | CIUDAD_AM | 11.837792024340981 | 0.2382233805694716 | 11.349424365236075 | 12.303094282043793 | 0.9536699168077174 | 2.012397076073261 | 0.2321531281890359 | 11274 | 21615 | 2548 | 2040764.1497329017 | 10 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 08 | ATLÁNTICO | 08001 | Barranquilla A.M. | CIUDAD_AM | 8.147876963504446 | 0.20364320313348963 | 7.758369144028984 | 8.539067924476932 | 0.7806987804479473 | 2.4993406754377596 | 0.20227860631932773 | 8765 | 20333 | 1732 | 938958.6916910572 | 2 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 11 | BOGOTÁ, D.C. | 11001 | Bogotá | CIUDAD | 10.369891846009237 | 0.23470569243768638 | 9.923013925606222 | 10.842821595503773 | 0.9198076698975512 | 2.2633379009445584 | 0.23779264282685864 | 9526 | 18637 | 1974 | 4333474.215495609 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 13 | BOLÍVAR | 13001 | Cartagena | CIUDAD | 8.348479134679252 | 0.2616260061808899 | 7.831033367314714 | 8.846062553114713 | 1.0150291857999987 | 3.13381637493835 | 0.2606218125063337 | 6965 | 13211 | 1146 | 403260.57932271744 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 15 | BOYACÁ | 15001 | Tunja | CIUDAD | 11.31387295825135 | 0.3258870132527561 | 10.699802124751084 | 11.955660713295213 | 1.255858588544129 | 2.8804195915518265 | 0.3364846488784757 | 5569 | 9801 | 1121 | 83439.43078171973 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 17 | CALDAS | 17001 | Manizales A.M. | CIUDAD_AM | 11.237104562268692 | 0.2842853489085462 | 10.677125697287714 | 11.766479884078391 | 1.0893541867906773 | 2.5298807831966186 | 0.2848882724745271 | 7307 | 12968 | 1467 | 236030.68581083228 | 2 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 18 | CAQUETÁ | 18001 | Florencia | CIUDAD | 12.940077494574945 | 0.37147473231937 | 12.194454102742279 | 13.654308492082206 | 1.4598543893399274 | 2.870730352852282 | 0.3645259854600956 | 5868 | 9796 | 1321 | 69607.81369492254 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 19 | CAUCA | 19001 | Popayán | CIUDAD | 10.67751322056855 | 0.29563369653389177 | 10.089364929882032 | 11.262680455663931 | 1.1733155257818986 | 2.768750461150448 | 0.299812301472087 | 6957 | 12701 | 1403 | 132019.3508940908 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 20 | CESAR | 20001 | Valledupar | CIUDAD | 14.450446813558157 | 0.32883821097383414 | 13.808108840333103 | 15.075758351899072 | 1.2676495115659687 | 2.2756265963022067 | 0.3366087407085093 | 6490 | 12703 | 1874 | 205750.73131105743 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 23 | CÓRDOBA | 23001 | Montería | CIUDAD | 9.467462710346696 | 0.2654040885773768 | 8.960236794390546 | 9.987294280335615 | 1.0270574859450683 | 2.8033285865211264 | 0.2717789915904437 | 6391 | 13713 | 1393 | 202389.90258019697 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 27 | CHOCÓ | 27001 | Quibdó | CIUDAD | 17.81311521809962 | 0.43966546604740253 | 16.965277330589636 | 18.65399710505331 | 1.6887197744636744 | 2.468212104756755 | 0.44078451237259886 | 5176 | 8997 | 1616 | 49680.683823311 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 41 | HUILA | 41001 | Neiva | CIUDAD | 11.533679893497528 | 0.3105304705479978 | 10.957320227344109 | 12.152495187147814 | 1.1951749598037047 | 2.6923798251334254 | 0.30900394115747837 | 6929 | 12725 | 1480 | 166938.4471683553 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 44 | LA GUAJIRA | 44001 | Riohacha | CIUDAD | 13.883929931442381 | 0.3222469880485139 | 13.244348539171455 | 14.499344763582675 | 1.2549962244112205 | 2.3210070177517537 | 0.32634787140688726 | 7288 | 13582 | 1957 | 58310.39000778933 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 47 | MAGDALENA | 47001 | Santa Marta | CIUDAD | 8.316388353479095 | 0.23289852902875874 | 7.862394844520332 | 8.765618289567136 | 0.9032234450468044 | 2.8004768311634636 | 0.23568482568403623 | 7740 | 14754 | 1249 | 219826.13831085642 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 50 | META | 50001 | Villavicencio | CIUDAD | 11.873324720682339 | 0.3195548786894929 | 11.256153798843128 | 12.509159080810065 | 1.2530052819669368 | 2.691368139985719 | 0.31960334391576795 | 6685 | 12177 | 1448 | 262642.13549784943 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 52 | NARIÑO | 52001 | Pasto | CIUDAD | 8.815888010228242 | 0.28462155223699975 | 8.243614039563761 | 9.37576973229564 | 1.132155692731878 | 3.2285068946744815 | 0.27993345521493146 | 6202 | 11830 | 1062 | 167862.90853465357 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 54 | NORTE DE SANTANDER | 54001 | Cúcuta A.M. | CIUDAD_AM | 15.983358846687304 | 0.36633003644268847 | 15.25287005567311 | 16.706657085403627 | 1.4537870297305169 | 2.291946517353039 | 0.37285390934612567 | 5926 | 11656 | 1875 | 446606.4078507225 | 4 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 63 | QUINDÍO | 63001 | Armenia | CIUDAD | 15.491457817733293 | 0.34182720974203185 | 14.842391474475553 | 16.1839066166701 | 1.341515142194547 | 2.206552887170744 | 0.34255752284685154 | 6798 | 12693 | 1996 | 158573.68096283954 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 66 | RISARALDA | 66001 | Pereira A.M. | CIUDAD_AM | 8.866599810615549 | 0.26887918331041705 | 8.343048715211525 | 9.390700217855924 | 1.047651502644399 | 3.0324948577074733 | 0.2674950783964665 | 7030 | 13033 | 1175 | 340084.0804418231 | 3 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 68 | SANTANDER | 68001 | Bucaramanga A.M. | CIUDAD_AM | 8.739145745214026 | 0.27610015993199827 | 8.23020348177573 | 9.311636656466158 | 1.081433174690428 | 3.1593495289079474 | 0.2706166200877431 | 6283 | 13778 | 1204 | 637258.9811706132 | 4 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 70 | SUCRE | 70001 | Sincelejo | CIUDAD | 9.60566705797104 | 0.25141368003718423 | 9.132009036096445 | 10.112102041572097 | 0.980093005475652 | 2.617347431676329 | 0.2494779390892907 | 7219 | 15737 | 1558 | 135144.64941063352 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 73 | TOLIMA | 73001 | Ibagué | CIUDAD | 13.99413661480143 | 0.3293502028833267 | 13.36433135640577 | 14.644770227091156 | 1.2804388706853853 | 2.353487120705803 | 0.3283163868737748 | 6579 | 12477 | 1788 | 273059.24838054465 | 1 |
| 2018 | 12 | Ene-Dic 2018 | 12 | 76 | VALLE DEL CAUCA | 76001 | Cali A.M. | CIUDAD_AM | 11.651373436219085 | 0.28404039180662977 | 11.073815873311904 | 12.205851595403628 | 1.1320357220917234 | 2.4378275519319548 | 0.2796511550000639 | 8182 | 15827 | 1808 | 1229927.9858649364 | 2 |


## Celda 5


**Salida:**

```
SE bootstrap / SE Taylor: mediana 1.000, mín 0.969, máx 1.026
Viviendas por dominio: mín 5,176, máx 11,274

```


## Celda 6


**Salida:**

```
[PASS] 23 de 23 dominios coinciden con el DANE en Ene-Dic 2018 (tolerancia 0.01 pp)
[PASS] agregado de los dominios 10.8340 vs «Total 23 ciudades y A.M.» 10.8340 (dif. +0.0000 pp)

```


## Celda 7


**Salida:**

```
Exportando 23 filas a tesis.preprocesamiento.tasa_desempleo_municipal...
Preservando lineage desde 1 tabla(s)...
✔ Exportación completada → tesis.preprocesamiento.tasa_desempleo_municipal

```
