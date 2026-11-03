# modelo__fay_herriot


## Celda 0



## Celda 1



## Celda 2



## Celda 3


**Salida:**

```
Dominios: 23 (7 ciudades con área metropolitana)
Columnas disponibles:  ['PER', 'MES', 'PERIODO', 'N_MESES_VENTANA', 'CODIGO_DEPARTAMENTO', 'DEPARTAMENTO', 'CODIGO_DOMINIO', 'NOMBRE_DOMINIO', 'TIPO_DOMINIO', 'N_MUNICIPIOS', 'N_PEA', 'N_DESOCUPADOS', 'PEA_EXPANDIDA', 'TASA_DESEMPLEO_PCT', 'SE_BOOTSTRAP_PCT', 'IC_INF_PCT', 'IC_SUP_PCT', 'AMPLITUD_IC', 'CV_PORCENTAJE', 'SE_TAYLOR_PCT', 'N_VIVIENDAS', 'TD_DANE_PCT', 'DIF_TD_PP', 'TASA_HOMICIDIOS', 'COB_ACUEDUCTO', 'DOMINIO']


```


## Celda 4


**Salida:**

```
Conjunto elegido por el análisis exploratorio: TASA_HOMICIDIOS + COB_ACUEDUCTO
Especificaciones candidatas del modelo base Fay-Herriot clásico (4):
  EC1: TASA_HOMICIDIOS + COB_ACUEDUCTO  (conjunto completo)
  EC2: COB_ACUEDUCTO  (sin TASA_HOMICIDIOS)
  EC3: TASA_HOMICIDIOS  (sin COB_ACUEDUCTO)
  EC0: intercepto  (solo intercepto, R-04)

```


## Celda 5


**Salida:**

```

Ajustando 4 especificación(es) candidata(s)...


```


## Celda 6


**Salida:**

```
=================================================================
EC1: TASA_HOMICIDIOS + COB_ACUEDUCTO — RESULTADOS EBLUP POR DOMINIO
=================================================================

```
| NOMBRE_DOMINIO | TASA_DESEMPLEO_PCT | EBLUP | CV_PORCENTAJE | CV_EBLUP_PCT | GAMMA_SHRINKAGE | MEJORA_CV_PCT |
|---|---|---|---|---|---|---|
| Medellín A.M. | 11.837792024340981 | 11.8311 | 2.012397076073261 | 2.01 | 0.9899 | 0.0 |
| Barranquilla A.M. | 8.147876963504446 | 8.1711 | 2.4993406754377596 | 2.49 | 0.9926 | 0.01 |
| Bogotá | 10.369891846009237 | 10.3715 | 2.2633379009445584 | 2.25 | 0.9902 | 0.01 |
| Cartagena | 8.348479134679252 | 8.3844 | 3.13381637493835 | 3.11 | 0.9878 | 0.02 |
| Tunja | 11.31387295825135 | 11.287 | 2.8804195915518265 | 2.87 | 0.9813 | 0.01 |
| Manizales A.M. | 11.237104562268692 | 11.2315 | 2.5298807831966186 | 2.52 | 0.9857 | 0.01 |
| Florencia | 12.940077494574945 | 12.9021 | 2.870730352852282 | 2.85 | 0.9758 | 0.02 |
| Popayán | 10.67751322056855 | 10.6837 | 2.768750461150448 | 2.75 | 0.9845 | 0.02 |
| Valledupar | 14.450446813558157 | 14.386 | 2.2756265963022067 | 2.27 | 0.9809 | 0.01 |
| Montería | 9.467462710346696 | 9.4901 | 2.8033285865211264 | 2.78 | 0.9875 | 0.02 |
| Quibdó | 17.81311521809962 | 17.8016 | 2.468212104756755 | 2.47 | 0.9664 | -0.0 |
| Neiva | 11.533679893497528 | 11.5286 | 2.6923798251334254 | 2.68 | 0.983 | 0.01 |
| Riohacha | 13.883929931442381 | 13.8693 | 2.3210070177517537 | 2.31 | 0.9817 | 0.01 |
| Santa Marta | 8.316388353479095 | 8.3505 | 2.8004768311634636 | 2.78 | 0.9903 | 0.02 |
| Villavicencio | 11.873324720682339 | 11.8643 | 2.691368139985719 | 2.67 | 0.982 | 0.02 |
| Pasto | 8.815888010228242 | 8.8394 | 3.2285068946744815 | 3.2 | 0.9856 | 0.03 |
| Cúcuta A.M. | 15.983358846687304 | 15.8799 | 2.291946517353039 | 2.29 | 0.9764 | 0.0 |
| Armenia | 15.491457817733293 | 15.4111 | 2.206552887170744 | 2.2 | 0.9794 | 0.01 |
| Pereira A.M. | 8.866599810615549 | 8.8966 | 3.0324948577074733 | 3.01 | 0.9872 | 0.02 |
| Bucaramanga A.M. | 8.739145745214026 | 8.7656 | 3.1593495289079474 | 3.13 | 0.9865 | 0.03 |
| Sincelejo | 9.60566705797104 | 9.6202 | 2.617347431676329 | 2.6 | 0.9888 | 0.02 |
| Ibagué | 13.99413661480143 | 13.9319 | 2.353487120705803 | 2.35 | 0.9809 | 0.0 |
| Cali A.M. | 11.651373436219085 | 11.6727 | 2.4378275519319548 | 2.43 | 0.9857 | 0.01 |
```
=================================================================
EC2: COB_ACUEDUCTO — RESULTADOS EBLUP POR DOMINIO
=================================================================

```
| NOMBRE_DOMINIO | TASA_DESEMPLEO_PCT | EBLUP | CV_PORCENTAJE | CV_EBLUP_PCT | GAMMA_SHRINKAGE | MEJORA_CV_PCT |
|---|---|---|---|---|---|---|
| Medellín A.M. | 11.837792024340981 | 11.8292 | 2.012397076073261 | 2.01 | 0.9902 | 0.0 |
| Barranquilla A.M. | 8.147876963504446 | 8.167 | 2.4993406754377596 | 2.49 | 0.9928 | 0.01 |
| Bogotá | 10.369891846009237 | 10.3737 | 2.2633379009445584 | 2.25 | 0.9905 | 0.01 |
| Cartagena | 8.348479134679252 | 8.3826 | 3.13381637493835 | 3.11 | 0.9882 | 0.02 |
| Tunja | 11.31387295825135 | 11.3048 | 2.8804195915518265 | 2.86 | 0.9819 | 0.02 |
| Manizales A.M. | 11.237104562268692 | 11.2347 | 2.5298807831966186 | 2.52 | 0.9862 | 0.01 |
| Florencia | 12.940077494574945 | 12.9063 | 2.870730352852282 | 2.85 | 0.9766 | 0.02 |
| Popayán | 10.67751322056855 | 10.683 | 2.768750461150448 | 2.75 | 0.985 | 0.02 |
| Valledupar | 14.450446813558157 | 14.3989 | 2.2756265963022067 | 2.27 | 0.9816 | 0.01 |
| Montería | 9.467462710346696 | 9.4943 | 2.8033285865211264 | 2.78 | 0.9879 | 0.02 |
| Quibdó | 17.81311521809962 | 17.7852 | 2.468212104756755 | 2.47 | 0.9675 | -0.0 |
| Neiva | 11.533679893497528 | 11.5247 | 2.6923798251334254 | 2.68 | 0.9835 | 0.01 |
| Riohacha | 13.883929931442381 | 13.8737 | 2.3210070177517537 | 2.31 | 0.9823 | 0.01 |
| Santa Marta | 8.316388353479095 | 8.3555 | 2.8004768311634636 | 2.78 | 0.9907 | 0.02 |
| Villavicencio | 11.873324720682339 | 11.8645 | 2.691368139985719 | 2.67 | 0.9826 | 0.02 |
| Pasto | 8.815888010228242 | 8.8442 | 3.2285068946744815 | 3.2 | 0.9861 | 0.03 |
| Cúcuta A.M. | 15.983358846687304 | 15.8759 | 2.291946517353039 | 2.29 | 0.9772 | 0.0 |
| Armenia | 15.491457817733293 | 15.3985 | 2.206552887170744 | 2.2 | 0.9801 | 0.01 |
| Pereira A.M. | 8.866599810615549 | 8.8917 | 3.0324948577074733 | 3.01 | 0.9876 | 0.02 |
| Bucaramanga A.M. | 8.739145745214026 | 8.7729 | 3.1593495289079474 | 3.13 | 0.9869 | 0.03 |
| Sincelejo | 9.60566705797104 | 9.6261 | 2.617347431676329 | 2.6 | 0.9891 | 0.02 |
| Ibagué | 13.99413661480143 | 13.9393 | 2.353487120705803 | 2.35 | 0.9815 | 0.0 |
| Cali A.M. | 11.651373436219085 | 11.6399 | 2.4378275519319548 | 2.43 | 0.9862 | 0.01 |
```
=================================================================
EC3: TASA_HOMICIDIOS — RESULTADOS EBLUP POR DOMINIO
=================================================================

```
| NOMBRE_DOMINIO | TASA_DESEMPLEO_PCT | EBLUP | CV_PORCENTAJE | CV_EBLUP_PCT | GAMMA_SHRINKAGE | MEJORA_CV_PCT |
|---|---|---|---|---|---|---|
| Medellín A.M. | 11.837792024340981 | 11.8337 | 2.012397076073261 | 2.01 | 0.9898 | 0.0 |
| Barranquilla A.M. | 8.147876963504446 | 8.1743 | 2.4993406754377596 | 2.48 | 0.9926 | 0.02 |
| Bogotá | 10.369891846009237 | 10.3723 | 2.2633379009445584 | 2.25 | 0.9901 | 0.01 |
| Cartagena | 8.348479134679252 | 8.3858 | 3.13381637493835 | 3.1 | 0.9878 | 0.03 |
| Tunja | 11.31387295825135 | 11.2815 | 2.8804195915518265 | 2.87 | 0.9812 | 0.01 |
| Manizales A.M. | 11.237104562268692 | 11.2317 | 2.5298807831966186 | 2.52 | 0.9856 | 0.01 |
| Florencia | 12.940077494574945 | 12.9005 | 2.870730352852282 | 2.85 | 0.9756 | 0.02 |
| Popayán | 10.67751322056855 | 10.686 | 2.768750461150448 | 2.75 | 0.9844 | 0.02 |
| Valledupar | 14.450446813558157 | 14.3795 | 2.2756265963022067 | 2.27 | 0.9808 | 0.01 |
| Montería | 9.467462710346696 | 9.4871 | 2.8033285865211264 | 2.78 | 0.9874 | 0.02 |
| Quibdó | 17.81311521809962 | 17.7631 | 2.468212104756755 | 2.46 | 0.9662 | 0.01 |
| Neiva | 11.533679893497528 | 11.533 | 2.6923798251334254 | 2.67 | 0.9829 | 0.02 |
| Riohacha | 13.883929931442381 | 13.8587 | 2.3210070177517537 | 2.31 | 0.9816 | 0.01 |
| Santa Marta | 8.316388353479095 | 8.3452 | 2.8004768311634636 | 2.78 | 0.9903 | 0.02 |
| Villavicencio | 11.873324720682339 | 11.865 | 2.691368139985719 | 2.67 | 0.9819 | 0.02 |
| Pasto | 8.815888010228242 | 8.8392 | 3.2285068946744815 | 3.2 | 0.9856 | 0.03 |
| Cúcuta A.M. | 15.983358846687304 | 15.8847 | 2.291946517353039 | 2.28 | 0.9763 | 0.01 |
| Armenia | 15.491457817733293 | 15.4223 | 2.206552887170744 | 2.2 | 0.9793 | 0.01 |
| Pereira A.M. | 8.866599810615549 | 8.901 | 3.0324948577074733 | 3.01 | 0.9871 | 0.02 |
| Bucaramanga A.M. | 8.739145745214026 | 8.7622 | 3.1593495289079474 | 3.13 | 0.9864 | 0.03 |
| Sincelejo | 9.60566705797104 | 9.6171 | 2.617347431676329 | 2.6 | 0.9887 | 0.02 |
| Ibagué | 13.99413661480143 | 13.9313 | 2.353487120705803 | 2.35 | 0.9808 | 0.0 |
| Cali A.M. | 11.651373436219085 | 11.692 | 2.4378275519319548 | 2.42 | 0.9856 | 0.02 |
```
=================================================================
EC0: intercepto — RESULTADOS EBLUP POR DOMINIO
=================================================================

```
| NOMBRE_DOMINIO | TASA_DESEMPLEO_PCT | EBLUP | CV_PORCENTAJE | CV_EBLUP_PCT | GAMMA_SHRINKAGE | MEJORA_CV_PCT |
|---|---|---|---|---|---|---|
| Medellín A.M. | 11.837792024340981 | 11.8354 | 2.012397076073261 | 2.01 | 0.9922 | 0.0 |
| Barranquilla A.M. | 8.147876963504446 | 8.1672 | 2.4993406754377596 | 2.49 | 0.9943 | 0.01 |
| Bogotá | 10.369891846009237 | 10.3787 | 2.2633379009445584 | 2.25 | 0.9924 | 0.01 |
| Cartagena | 8.348479134679252 | 8.3784 | 3.13381637493835 | 3.11 | 0.9906 | 0.02 |
| Tunja | 11.31387295825135 | 11.317 | 2.8804195915518265 | 2.86 | 0.9855 | 0.02 |
| Manizales A.M. | 11.237104562268692 | 11.2403 | 2.5298807831966186 | 2.52 | 0.9889 | 0.01 |
| Florencia | 12.940077494574945 | 12.9135 | 2.870730352852282 | 2.86 | 0.9812 | 0.01 |
| Popayán | 10.67751322056855 | 10.6877 | 2.768750461150448 | 2.75 | 0.988 | 0.02 |
| Valledupar | 14.450446813558157 | 14.4072 | 2.2756265963022067 | 2.27 | 0.9852 | 0.01 |
| Montería | 9.467462710346696 | 9.4874 | 2.8033285865211264 | 2.79 | 0.9903 | 0.01 |
| Quibdó | 17.81311521809962 | 17.649 | 2.468212104756755 | 2.47 | 0.9739 | -0.0 |
| Neiva | 11.533679893497528 | 11.5336 | 2.6923798251334254 | 2.68 | 0.9868 | 0.01 |
| Riohacha | 13.883929931442381 | 13.8505 | 2.3210070177517537 | 2.31 | 0.9858 | 0.01 |
| Santa Marta | 8.316388353479095 | 8.3404 | 2.8004768311634636 | 2.78 | 0.9925 | 0.02 |
| Villavicencio | 11.873324720682339 | 11.8685 | 2.691368139985719 | 2.68 | 0.986 | 0.01 |
| Pasto | 8.815888010228242 | 8.846 | 3.2285068946744815 | 3.2 | 0.9889 | 0.03 |
| Cúcuta A.M. | 15.983358846687304 | 15.9019 | 2.291946517353039 | 2.29 | 0.9817 | 0.0 |
| Armenia | 15.491457817733293 | 15.4282 | 2.206552887170744 | 2.2 | 0.984 | 0.01 |
| Pereira A.M. | 8.866599810615549 | 8.893 | 3.0324948577074733 | 3.01 | 0.9901 | 0.02 |
| Bucaramanga A.M. | 8.739145745214026 | 8.7683 | 3.1593495289079474 | 3.14 | 0.9895 | 0.02 |
| Sincelejo | 9.60566705797104 | 9.6224 | 2.617347431676329 | 2.6 | 0.9913 | 0.02 |
| Ibagué | 13.99413661480143 | 13.9576 | 2.353487120705803 | 2.35 | 0.9852 | 0.0 |
| Cali A.M. | 11.651373436219085 | 11.65 | 2.4378275519319548 | 2.43 | 0.9889 | 0.01 |


## Celda 7


**Salida:**

```
=================================================================
EC1: TASA_HOMICIDIOS + COB_ACUEDUCTO — GRÁFICAS DE VALIDACIÓN
=================================================================
Gráfica 1 (Efecto suavizador): compara el residuo del EBLUP (Yd − EBLUP)
contra la estimación directa. Como Yd − EBLUP = (1 − γd)(Yd − x'β̂), se espera
residuo negativo para Yd pequeños (el EBLUP sube la estimación) y positivo para
Yd grandes (el EBLUP la baja). Es una descripción de la contracción hacia el
predictor sintético, no una prueba de validez del modelo.
Gráfica 2 (Histograma de residuos estandarizados): distribución de
(Y − x'β̂)/√(Dd+Â). Bajo el supuesto de normalidad del modelo se verían
aproximadamente normales y con desviación ≈ 1; la media es ≈ 0 por construcción
del GLS con intercepto. Con 23 residuos marginales (mezclan u_d y e_d) ni el
histograma ni Shapiro-Wilk pueden demostrar normalidad: solo mostrar si hay
evidencia fuerte en contra.


```
![fig](fig/modelo__fay_herriot_c07_0.png)
![fig](fig/modelo__fay_herriot_c07_1.png)
```
INTERPRETACIÓN:
  Gráfica 1 (Efecto suavizador): corr(Yd, Yd−EBLUP)=0.816 (p=0.0000)  ✓ el EBLUP contrae los extremos hacia el predictor sintético
  Gráfica 2 (Residuos estandarizados): media=0.002 (≈ 0 por construcción del GLS con intercepto; no informa sobre sesgo), sd=0.954, Shapiro-Wilk p=0.3906: los diagnósticos no muestran evidencia fuerte contra la aproximación normal, dentro de la limitada potencia disponible con 23 áreas

=================================================================
EC2: COB_ACUEDUCTO — GRÁFICAS DE VALIDACIÓN
=================================================================
Gráfica 1 (Efecto suavizador): compara el residuo del EBLUP (Yd − EBLUP)
contra la estimación directa. Como Yd − EBLUP = (1 − γd)(Yd − x'β̂), se espera
residuo negativo para Yd pequeños (el EBLUP sube la estimación) y positivo para
Yd grandes (el EBLUP la baja). Es una descripción de la contracción hacia el
predictor sintético, no una prueba de validez del modelo.
Gráfica 2 (Histograma de residuos estandarizados): distribución de
(Y − x'β̂)/√(Dd+Â). Bajo el supuesto de normalidad del modelo se verían
aproximadamente normales y con desviación ≈ 1; la media es ≈ 0 por construcción
del GLS con intercepto. Con 23 residuos marginales (mezclan u_d y e_d) ni el
histograma ni Shapiro-Wilk pueden demostrar normalidad: solo mostrar si hay
evidencia fuerte en contra.


```
![fig](fig/modelo__fay_herriot_c07_2.png)
![fig](fig/modelo__fay_herriot_c07_3.png)
```
INTERPRETACIÓN:
  Gráfica 1 (Efecto suavizador): corr(Yd, Yd−EBLUP)=0.869 (p=0.0000)  ✓ el EBLUP contrae los extremos hacia el predictor sintético
  Gráfica 2 (Residuos estandarizados): media=0.002 (≈ 0 por construcción del GLS con intercepto; no informa sobre sesgo), sd=0.978, Shapiro-Wilk p=0.3167: los diagnósticos no muestran evidencia fuerte contra la aproximación normal, dentro de la limitada potencia disponible con 23 áreas

=================================================================
EC3: TASA_HOMICIDIOS — GRÁFICAS DE VALIDACIÓN
=================================================================
Gráfica 1 (Efecto suavizador): compara el residuo del EBLUP (Yd − EBLUP)
contra la estimación directa. Como Yd − EBLUP = (1 − γd)(Yd − x'β̂), se espera
residuo negativo para Yd pequeños (el EBLUP sube la estimación) y positivo para
Yd grandes (el EBLUP la baja). Es una descripción de la contracción hacia el
predictor sintético, no una prueba de validez del modelo.
Gráfica 2 (Histograma de residuos estandarizados): distribución de
(Y − x'β̂)/√(Dd+Â). Bajo el supuesto de normalidad del modelo se verían
aproximadamente normales y con desviación ≈ 1; la media es ≈ 0 por construcción
del GLS con intercepto. Con 23 residuos marginales (mezclan u_d y e_d) ni el
histograma ni Shapiro-Wilk pueden demostrar normalidad: solo mostrar si hay
evidencia fuerte en contra.


```
![fig](fig/modelo__fay_herriot_c07_4.png)
![fig](fig/modelo__fay_herriot_c07_5.png)
```
INTERPRETACIÓN:
  Gráfica 1 (Efecto suavizador): corr(Yd, Yd−EBLUP)=0.879 (p=0.0000)  ✓ el EBLUP contrae los extremos hacia el predictor sintético
  Gráfica 2 (Residuos estandarizados): media=0.002 (≈ 0 por construcción del GLS con intercepto; no informa sobre sesgo), sd=0.977, Shapiro-Wilk p=0.3567: los diagnósticos no muestran evidencia fuerte contra la aproximación normal, dentro de la limitada potencia disponible con 23 áreas

=================================================================
EC0: intercepto — GRÁFICAS DE VALIDACIÓN
=================================================================
Gráfica 1 (Efecto suavizador): compara el residuo del EBLUP (Yd − EBLUP)
contra la estimación directa. Como Yd − EBLUP = (1 − γd)(Yd − x'β̂), se espera
residuo negativo para Yd pequeños (el EBLUP sube la estimación) y positivo para
Yd grandes (el EBLUP la baja). Es una descripción de la contracción hacia el
predictor sintético, no una prueba de validez del modelo.
Gráfica 2 (Histograma de residuos estandarizados): distribución de
(Y − x'β̂)/√(Dd+Â). Bajo el supuesto de normalidad del modelo se verían
aproximadamente normales y con desviación ≈ 1; la media es ≈ 0 por construcción
del GLS con intercepto. Con 23 residuos marginales (mezclan u_d y e_d) ni el
histograma ni Shapiro-Wilk pueden demostrar normalidad: solo mostrar si hay
evidencia fuerte en contra.


```
![fig](fig/modelo__fay_herriot_c07_6.png)
![fig](fig/modelo__fay_herriot_c07_7.png)
```
INTERPRETACIÓN:
  Gráfica 1 (Efecto suavizador): corr(Yd, Yd−EBLUP)=0.939 (p=0.0000)  ✓ el EBLUP contrae los extremos hacia el predictor sintético
  Gráfica 2 (Residuos estandarizados): media=0.002 (≈ 0 por construcción del GLS con intercepto; no informa sobre sesgo), sd=1.002, Shapiro-Wilk p=0.1393: los diagnósticos no muestran evidencia fuerte contra la aproximación normal, dentro de la limitada potencia disponible con 23 áreas


```


## Celda 8


**Salida:**

```
=================================================================
EC1: TASA_HOMICIDIOS + COB_ACUEDUCTO
=================================================================

Varianza de efectos aleatorios (Â):   5.563634
Desv. estándar de efectos aleatorios: 2.358736

COEFICIENTES (prueba z con la normal asintótica de β̂, Morales et al. p. 272):

```
| Parametro | Coef | SE | z | p_valor | Signif |
|---|---|---|---|---|---|
| Intercepto | 13.7584 | 4.9973 | 2.753 | 0.0059 | *** |
| TASA_HOMICIDIOS | 0.0663 | 0.0505 | 1.311 | 0.1898 |  |
| COB_ACUEDUCTO | -0.0419 | 0.045 | -0.932 | 0.3512 |  |
```
Signif: *** p<0.01  ** p<0.05  * p<0.10

DIAGNÓSTICOS:
  R² predictor sintético:       0.2994
  Media residuos estand.:       0.0017  (≈ 0 por construcción del GLS con intercepto; no informa sobre sesgo)
  Desv. std residuos estand.:   0.9540  (≈ 1 si ψ_d y Â son adecuadas)
  Shapiro-Wilk: W=0.9562, p=0.3906: los diagnósticos no muestran evidencia fuerte contra la aproximación normal, dentro de la limitada potencia disponible con 23 áreas
  Reducción media del CV:       0.01 pp
  Shrinkage promedio (γ̄):       0.9839
  Distancia de Cook máxima:     0.5260 en Cali A.M.  (umbral 4/n = 0.1739; 2 dominio(s) lo superan: Quibdó, Cali A.M.)

GANANCIA DE PRECISIÓN (descriptiva: MSE_EBLUP < Di es lo esperado, p. 440):
  Reducción media del MSE:      1.07%
  Ratio Di/MSE medio:           1.0108  (>1 indica ganancia)
  Ratio Di/MSE mediana:         1.0109

  Detalle por dominio (Di vs MSE_EBLUP):

```
| NOMBRE_DOMINIO | VARIANZA_DIRECTA | MSE_EBLUP | RATIO_MSE | MEJORA_MSE_PCT | MEJORA_MSE |
|---|---|---|---|---|---|
| Medellín A.M. | 0.05675037904994729 | 0.056311 | 1.0078 | 0.77 | ✓ |
| Barranquilla A.M. | 0.04147055418246772 | 0.041242 | 1.0055 | 0.55 | ✓ |
| Bogotá | 0.05508676206265383 | 0.054677 | 1.0075 | 0.74 | ✓ |
| Cartagena | 0.06844816711016304 | 0.0678 | 1.0096 | 0.95 | ✓ |
| Tunja | 0.10620234540680203 | 0.104849 | 1.0129 | 1.27 | ✓ |
| Manizales A.M. | 0.08081815960405384 | 0.079925 | 1.0112 | 1.1 | ✓ |
| Florencia | 0.13799347675174758 | 0.135375 | 1.0193 | 1.9 | ✓ |
| Popayán | 0.08739928252629321 | 0.08635 | 1.0122 | 1.2 | ✓ |
| Valledupar | 0.10813456899647185 | 0.106591 | 1.0145 | 1.43 | ✓ |
| Montería | 0.07043933023358807 | 0.069767 | 1.0096 | 0.95 | ✓ |
| Quibdó | 0.19330572203467966 | 0.193295 | 1.0001 | 0.01 | ✓ |
| Neiva | 0.09642917313876094 | 0.095166 | 1.0133 | 1.31 | ✓ |
| Riohacha | 0.10384312130633908 | 0.10252 | 1.0129 | 1.27 | ✓ |
| Santa Marta | 0.05424172482375958 | 0.053869 | 1.0069 | 0.69 | ✓ |
| Villavicencio | 0.10211532049425652 | 0.100675 | 1.0143 | 1.41 | ✓ |
| Pasto | 0.08100942799779919 | 0.080133 | 1.0109 | 1.08 | ✓ |
| Cúcuta A.M. | 0.13419769560010145 | 0.131754 | 1.0185 | 1.82 | ✓ |
| Armenia | 0.11684584132002303 | 0.115137 | 1.0148 | 1.46 | ✓ |
| Pereira A.M. | 0.07229601521767685 | 0.071591 | 1.0098 | 0.97 | ✓ |
| Bucaramanga A.M. | 0.07623129831447502 | 0.075469 | 1.0101 | 1.0 | ✓ |
| Sincelejo | 0.06320883850983965 | 0.06268 | 1.0084 | 0.84 | ✓ |
| Ibagué | 0.10847155613928848 | 0.106876 | 1.0149 | 1.47 | ✓ |
| Cali A.M. | 0.08067894417766375 | 0.080431 | 1.0031 | 0.31 | ✓ |
```

=================================================================
EC2: COB_ACUEDUCTO
=================================================================

Varianza de efectos aleatorios (Â):   5.756795
Desv. estándar de efectos aleatorios: 2.399332

COEFICIENTES (prueba z con la normal asintótica de β̂, Morales et al. p. 272):

```
| Parametro | Coef | SE | z | p_valor | Signif |
|---|---|---|---|---|---|
| Intercepto | 19.0532 | 2.9938 | 6.364 | 0.0 | *** |
| COB_ACUEDUCTO | -0.0833 | 0.0326 | -2.551 | 0.0107 | ** |
```
Signif: *** p<0.01  ** p<0.05  * p<0.10

DIAGNÓSTICOS:
  R² predictor sintético:       0.2392
  Media residuos estand.:       0.0017  (≈ 0 por construcción del GLS con intercepto; no informa sobre sesgo)
  Desv. std residuos estand.:   0.9775  (≈ 1 si ψ_d y Â son adecuadas)
  Shapiro-Wilk: W=0.9517, p=0.3167: los diagnósticos no muestran evidencia fuerte contra la aproximación normal, dentro de la limitada potencia disponible con 23 áreas
  Reducción media del CV:       0.01 pp
  Shrinkage promedio (γ̄):       0.9845
  Distancia de Cook máxima:     1.2966 en Quibdó  (umbral 4/n = 0.1739; 1 dominio(s) lo superan: Quibdó)

GANANCIA DE PRECISIÓN (descriptiva: MSE_EBLUP < Di es lo esperado, p. 440):
  Reducción media del MSE:      1.10%
  Ratio Di/MSE medio:           1.0111  (>1 indica ganancia)
  Ratio Di/MSE mediana:         1.0108

  Detalle por dominio (Di vs MSE_EBLUP):

```
| NOMBRE_DOMINIO | VARIANZA_DIRECTA | MSE_EBLUP | RATIO_MSE | MEJORA_MSE_PCT | MEJORA_MSE |
|---|---|---|---|---|---|
| Medellín A.M. | 0.05675037904994729 | 0.056323 | 1.0076 | 0.75 | ✓ |
| Barranquilla A.M. | 0.04147055418246772 | 0.041243 | 1.0055 | 0.55 | ✓ |
| Bogotá | 0.05508676206265383 | 0.054687 | 1.0073 | 0.73 | ✓ |
| Cartagena | 0.06844816711016304 | 0.067822 | 1.0092 | 0.92 | ✓ |
| Tunja | 0.10620234540680203 | 0.10472 | 1.0142 | 1.4 | ✓ |
| Manizales A.M. | 0.08081815960405384 | 0.07995 | 1.0109 | 1.07 | ✓ |
| Florencia | 0.13799347675174758 | 0.135455 | 1.0187 | 1.84 | ✓ |
| Popayán | 0.08739928252629321 | 0.086385 | 1.0117 | 1.16 | ✓ |
| Valledupar | 0.10813456899647185 | 0.106573 | 1.0147 | 1.44 | ✓ |
| Montería | 0.07043933023358807 | 0.069775 | 1.0095 | 0.94 | ✓ |
| Quibdó | 0.19330572203467966 | 0.193128 | 1.0009 | 0.09 | ✓ |
| Neiva | 0.09642917313876094 | 0.095197 | 1.0129 | 1.28 | ✓ |
| Riohacha | 0.10384312130633908 | 0.102554 | 1.0126 | 1.24 | ✓ |
| Santa Marta | 0.05424172482375958 | 0.05386 | 1.0071 | 0.7 | ✓ |
| Villavicencio | 0.10211532049425652 | 0.100722 | 1.0138 | 1.36 | ✓ |
| Pasto | 0.08100942799779919 | 0.080144 | 1.0108 | 1.07 | ✓ |
| Cúcuta A.M. | 0.13419769560010145 | 0.131802 | 1.0182 | 1.79 | ✓ |
| Armenia | 0.11684584132002303 | 0.115053 | 1.0156 | 1.53 | ✓ |
| Pereira A.M. | 0.07229601521767685 | 0.071605 | 1.0097 | 0.96 | ✓ |
| Bucaramanga A.M. | 0.07623129831447502 | 0.075454 | 1.0103 | 1.02 | ✓ |
| Sincelejo | 0.06320883850983965 | 0.062673 | 1.0086 | 0.85 | ✓ |
| Ibagué | 0.10847155613928848 | 0.106912 | 1.0146 | 1.44 | ✓ |
| Cali A.M. | 0.08067894417766375 | 0.079821 | 1.0107 | 1.06 | ✓ |
```

=================================================================
EC3: TASA_HOMICIDIOS
=================================================================

Varianza de efectos aleatorios (Â):   5.528840
Desv. estándar de efectos aleatorios: 2.351348

COEFICIENTES (prueba z con la normal asintótica de β̂, Morales et al. p. 272):

```
| Parametro | Coef | SE | z | p_valor | Signif |
|---|---|---|---|---|---|
| Intercepto | 9.1908 | 0.979 | 9.388 | 0.0 | *** |
| TASA_HOMICIDIOS | 0.0993 | 0.0359 | 2.761 | 0.0058 | *** |
```
Signif: *** p<0.01  ** p<0.05  * p<0.10

DIAGNÓSTICOS:
  R² predictor sintético:       0.2689
  Media residuos estand.:       0.0019  (≈ 0 por construcción del GLS con intercepto; no informa sobre sesgo)
  Desv. std residuos estand.:   0.9774  (≈ 1 si ψ_d y Â son adecuadas)
  Shapiro-Wilk: W=0.9542, p=0.3567: los diagnósticos no muestran evidencia fuerte contra la aproximación normal, dentro de la limitada potencia disponible con 23 áreas
  Reducción media del CV:       0.02 pp
  Shrinkage promedio (γ̄):       0.9838
  Distancia de Cook máxima:     0.6009 en Quibdó  (umbral 4/n = 0.1739; 2 dominio(s) lo superan: Quibdó, Cali A.M.)

GANANCIA DE PRECISIÓN (descriptiva: MSE_EBLUP < Di es lo esperado, p. 440):
  Reducción media del MSE:      1.16%
  Ratio Di/MSE medio:           1.0117  (>1 indica ganancia)
  Ratio Di/MSE mediana:         1.0110

  Detalle por dominio (Di vs MSE_EBLUP):

```
| NOMBRE_DOMINIO | VARIANZA_DIRECTA | MSE_EBLUP | RATIO_MSE | MEJORA_MSE_PCT | MEJORA_MSE |
|---|---|---|---|---|---|
| Medellín A.M. | 0.05675037904994729 | 0.056301 | 1.008 | 0.79 | ✓ |
| Barranquilla A.M. | 0.04147055418246772 | 0.04123 | 1.0058 | 0.58 | ✓ |
| Bogotá | 0.05508676206265383 | 0.054673 | 1.0076 | 0.75 | ✓ |
| Cartagena | 0.06844816711016304 | 0.067795 | 1.0096 | 0.95 | ✓ |
| Tunja | 0.10620234540680203 | 0.104807 | 1.0133 | 1.31 | ✓ |
| Manizales A.M. | 0.08081815960405384 | 0.07992 | 1.0112 | 1.11 | ✓ |
| Florencia | 0.13799347675174758 | 0.135356 | 1.0195 | 1.91 | ✓ |
| Popayán | 0.08739928252629321 | 0.086338 | 1.0123 | 1.21 | ✓ |
| Valledupar | 0.10813456899647185 | 0.106538 | 1.015 | 1.48 | ✓ |
| Montería | 0.07043933023358807 | 0.069752 | 1.0099 | 0.98 | ✓ |
| Quibdó | 0.19330572203467966 | 0.191612 | 1.0088 | 0.88 | ✓ |
| Neiva | 0.09642917313876094 | 0.095135 | 1.0136 | 1.34 | ✓ |
| Riohacha | 0.10384312130633908 | 0.102387 | 1.0142 | 1.4 | ✓ |
| Santa Marta | 0.05424172482375958 | 0.053831 | 1.0076 | 0.76 | ✓ |
| Villavicencio | 0.10211532049425652 | 0.100665 | 1.0144 | 1.42 | ✓ |
| Pasto | 0.08100942799779919 | 0.080128 | 1.011 | 1.09 | ✓ |
| Cúcuta A.M. | 0.13419769560010145 | 0.131706 | 1.0189 | 1.86 | ✓ |
| Armenia | 0.11684584132002303 | 0.114971 | 1.0163 | 1.6 | ✓ |
| Pereira A.M. | 0.07229601521767685 | 0.071567 | 1.0102 | 1.01 | ✓ |
| Bucaramanga A.M. | 0.07623129831447502 | 0.07545 | 1.0104 | 1.03 | ✓ |
| Sincelejo | 0.06320883850983965 | 0.062665 | 1.0087 | 0.86 | ✓ |
| Ibagué | 0.10847155613928848 | 0.106866 | 1.015 | 1.48 | ✓ |
| Cali A.M. | 0.08067894417766375 | 0.080008 | 1.0084 | 0.83 | ✓ |
```

=================================================================
EC0: intercepto
=================================================================

Varianza de efectos aleatorios (Â):   7.208863
Desv. estándar de efectos aleatorios: 2.684933

COEFICIENTES (prueba z con la normal asintótica de β̂, Morales et al. p. 272):

```
| Parametro | Coef | SE | z | p_valor | Signif |
|---|---|---|---|---|---|
| Intercepto | 11.527 | 0.5634 | 20.461 | 0.0 | *** |
```
Signif: *** p<0.01  ** p<0.05  * p<0.10

DIAGNÓSTICOS:
  R² predictor sintético:       -0.0000
  Media residuos estand.:       0.0019  (≈ 0 por construcción del GLS con intercepto; no informa sobre sesgo)
  Desv. std residuos estand.:   1.0016  (≈ 1 si ψ_d y Â son adecuadas)
  Shapiro-Wilk: W=0.9349, p=0.1393: los diagnósticos no muestran evidencia fuerte contra la aproximación normal, dentro de la limitada potencia disponible con 23 áreas
  Reducción media del CV:       0.01 pp
  Shrinkage promedio (γ̄):       0.9875
  Distancia de Cook máxima:     0.2499 en Quibdó  (umbral 4/n = 0.1739; 1 dominio(s) lo superan: Quibdó)

GANANCIA DE PRECISIÓN (descriptiva: MSE_EBLUP < Di es lo esperado, p. 440):
  Reducción media del MSE:      0.98%
  Ratio Di/MSE medio:           1.0099  (>1 indica ganancia)
  Ratio Di/MSE mediana:         1.0088

  Detalle por dominio (Di vs MSE_EBLUP):

```
| NOMBRE_DOMINIO | VARIANZA_DIRECTA | MSE_EBLUP | RATIO_MSE | MEJORA_MSE_PCT | MEJORA_MSE |
|---|---|---|---|---|---|
| Medellín A.M. | 0.05675037904994729 | 0.056404 | 1.0061 | 0.61 | ✓ |
| Barranquilla A.M. | 0.04147055418246772 | 0.041286 | 1.0045 | 0.45 | ✓ |
| Bogotá | 0.05508676206265383 | 0.054761 | 1.006 | 0.59 | ✓ |
| Cartagena | 0.06844816711016304 | 0.067945 | 1.0074 | 0.73 | ✓ |
| Tunja | 0.10620234540680203 | 0.104994 | 1.0115 | 1.14 | ✓ |
| Manizales A.M. | 0.08081815960405384 | 0.080117 | 1.0087 | 0.87 | ✓ |
| Florencia | 0.13799347675174758 | 0.135959 | 1.015 | 1.47 | ✓ |
| Popayán | 0.08739928252629321 | 0.08658 | 1.0095 | 0.94 | ✓ |
| Valledupar | 0.10813456899647185 | 0.106882 | 1.0117 | 1.16 | ✓ |
| Montería | 0.07043933023358807 | 0.069907 | 1.0076 | 0.76 | ✓ |
| Quibdó | 0.19330572203467966 | 0.189328 | 1.021 | 2.06 | ✓ |
| Neiva | 0.09642917313876094 | 0.095433 | 1.0104 | 1.03 | ✓ |
| Riohacha | 0.10384312130633908 | 0.102688 | 1.0112 | 1.11 | ✓ |
| Santa Marta | 0.05424172482375958 | 0.053926 | 1.0059 | 0.58 | ✓ |
| Villavicencio | 0.10211532049425652 | 0.100998 | 1.0111 | 1.09 | ✓ |
| Pasto | 0.08100942799779919 | 0.080305 | 1.0088 | 0.87 | ✓ |
| Cúcuta A.M. | 0.13419769560010145 | 0.132273 | 1.0146 | 1.43 | ✓ |
| Armenia | 0.11684584132002303 | 0.115385 | 1.0127 | 1.25 | ✓ |
| Pereira A.M. | 0.07229601521767685 | 0.071735 | 1.0078 | 0.78 | ✓ |
| Bucaramanga A.M. | 0.07623129831447502 | 0.075608 | 1.0082 | 0.82 | ✓ |
| Sincelejo | 0.06320883850983965 | 0.06278 | 1.0068 | 0.68 | ✓ |
| Ibagué | 0.10847155613928848 | 0.107212 | 1.0118 | 1.16 | ✓ |
| Cali A.M. | 0.08067894417766375 | 0.079981 | 1.0087 | 0.87 | ✓ |
```


```


## Celda 9


**Salida:**

```
=================================================================
TABLA 1 — DIAGNÓSTICOS POR ESPECIFICACIÓN CANDIDATA (informativa)
=================================================================

```
| Modelo | Covariables | R2 | Media_resid | SD_resid | SW_pval | Delta_CV_pp | Gamma_prom | Ratio_MSE_medio | Corr_suavizador | Corr_suavizador_pval | Cook_max | N_influyentes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EC1 | TASA_HOMICIDIOS + COB_ACUEDUCTO | 0.2994 | 0.0017 | 0.954 | 0.3906 | 0.01 | 0.9839 | 1.0108 | 0.8164 | 0.0 | 0.526 | 2 |
| EC2 | COB_ACUEDUCTO | 0.2392 | 0.0017 | 0.9775 | 0.3167 | 0.01 | 0.9845 | 1.0111 | 0.8689 | 0.0 | 1.2966 | 1 |
| EC3 | TASA_HOMICIDIOS | 0.2689 | 0.0019 | 0.9774 | 0.3567 | 0.02 | 0.9838 | 1.0117 | 0.8789 | 0.0 | 0.6009 | 2 |
| EC0 |  | -0.0 | 0.0019 | 1.0016 | 0.1393 | 0.01 | 0.9875 | 1.0099 | 0.9388 | 0.0 | 0.2499 | 1 |
```
  SW_pval: p-valor de Shapiro-Wilk; p > 0.05 no demuestra normalidad, solo que no hay evidencia fuerte en contra con 23 áreas
  Media_resid: ≈ 0 por construcción del GLS; SD_resid con ddof = 1
  Ratio_MSE_medio: ganancia de precisión (Di/MSE)
    del EBLUP frente a la estimación directa (descriptiva, p. 440)
  Cook_max / N_influyentes: distancia de Cook máxima y dominios que superan 4/n

=================================================================
TABLA 2 — SELECCIÓN DEL BENCHMARK (significancia + AIC + parsimonia)
=================================================================

```
| Modelo | Covariables | N_covariables | AIC | Delta_AIC | AICc | Delta_AICc | p_max_covariables | Todas_signif | Candidata | Equivalente_AIC | Elegida | Criterio | MSE_medio | Cook_max | RMSE_LOAO | N_LOAO |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EC3 | TASA_HOMICIDIOS | 1 | 108.9036 | 0.0 | 110.1668 | 0.0 | 0.0058 | sí | sí | sí | sí | regla estricta: todas las covariables con p < alfa (Morales p. 453) | 0.089987 | 0.6009 | 2.5243249659229865 | 23 |
| EC2 | COB_ACUEDUCTO | 1 | 109.8218 | 0.9182 | 111.0849 | 0.9182 | 0.0107 | sí | sí | sí |  | regla estricta: todas las covariables con p < alfa (Morales p. 453) | 0.090081 | 1.2966 | 2.599361163525286 | 23 |
| EC0 |  | 0 | 114.0417 | 5.1381 | 114.6417 | 4.475 | None | sí | sí | no |  | regla estricta: todas las covariables con p < alfa (Morales p. 453) | 0.090108 | 0.2499 | 2.7715364261213886 | 23 |
| EC1 | TASA_HOMICIDIOS + COB_ACUEDUCTO | 2 | 109.9261 | 1.0225 | 112.1483 | 1.9816 | 0.3512 | no | no | no |  | regla estricta: todas las covariables con p < alfa (Morales p. 453) | 0.090108 | 0.526 | 2.5517333717717405 | 23 |
```
  Candidata: todas las covariables con p < 0.05 (Morales et al., p. 453: no sobreparametrizar al predecir fuera de muestra; p. 454 admite una covariable con p > 0.05 si es interpretable, a reportar aparte)
  Criterio: regla estricta o respaldo (ninguna cumple la regla: compiten todas y el benchmark se reporta como excepción, R-05)
  Equivalente_AIC: ΔAIC ≤ 2.0 frente a la mejor candidata; entre ellas se elige la de menos covariables
  MSE_medio y Cook_max: informativas, no intervienen en la decisión
  EC0: modelo de solo intercepto (R-04). Sin covariables cumple la regla de forma trivial; gana solo si ninguna especificación con covariables lo supera en AIC por más de 2.0 (Morales et al., p. 453: no sobreparametrizar al predecir fuera de muestra)
  RMSE_LOAO: error de predecir cada dominio retirado con x'β̂(-d), covariables fijas (R-04). Descriptiva: optimista para las especificaciones con covariables, porque se eligieron viendo a todos los dominios; no interviene en la decisión
  AICc / Delta_AICc: AIC con corrección de muestra pequeña (n = 23 dominios), complemento que no interviene en la decisión

```


## Celda 10


**Salida:**

```
Especificaciones con todas las covariables significativas (p < 0.05): EC2, EC3, EC0
Equivalentes por AIC (ΔAIC ≤ 2.0): EC2, EC3
Benchmark seleccionado (Fay-Herriot clásico): EC3 (TASA_HOMICIDIOS)
Equivalentes por AICc (ΔAICc ≤ 2.0, complemento): EC2, EC3

AVISO: el benchmark seleccionado no coincide con el conjunto completo (EC1) elegido por el análisis
exploratorio: alguna covariable no es significativa o no aporta ajuste suficiente.
Ambas cifras deben reportarse y la diferencia explicarse en el documento.
  conjunto del EDA: TASA_HOMICIDIOS + COB_ACUEDUCTO
  benchmark:        TASA_HOMICIDIOS

NOTA SOBRE LA INFERENCIA: Los p-valores de los coeficientes son descriptivos: los mismos dominios se usaron para filtrar, seleccionar, comparar especificaciones y estimar β̂, así que la significancia no es una demostración fuerte. Los coeficientes del benchmark se reportan como asociaciones preliminares, condicionales a la selección.

REDACCIÓN SUGERIDA PARA EL DOCUMENTO:
Compitieron las 3 de 4 especificaciones con todas sus covariables significativas (p < 0.05; Morales et al., p. 453). EC3 fue seleccionado, entre varias especificaciones con soporte similar (ΔAIC ≤ 2: EC2, EC3), mediante la regla de parsimonia predefinida (menor número de covariables); no es claramente superior a las demás. Como complemento, con n = 23 dominios se calculó el AICc: EC3 queda a ΔAICc = 0.00 de la mejor de las que compitieron y 2 de 3 tienen soporte similar (ΔAICc ≤ 2). La lectura se mantiene con AICc.

```


## Celda 11


**Salida:**

```
Reajustes dejar-un-dominio-fuera: 23 ajustes: 0 fallidos (matriz singular), 0 sin convergencia, 0 con Â en la cota.

```


## Celda 12



## Celda 13


**Salida:**

![fig](fig/modelo__fay_herriot_c13_8.png)
```
INTERPRETACIÓN (ganancia de precisión del modelo elegido):
  Reducción media del CV en el tercio de menor Dd: 0.02 pp; en el tercio de mayor Dd: 0.01 pp.
  Dominios con CV < 5.0%: 23 con la estimación directa, 23 con el EBLUP (de 23).
  Lectura: la ganancia se concentra donde la varianza directa es grande; donde la muestra es grande el MSE del EBLUP tiende a Dd y el EBLUP casi coincide con la estimación directa (Morales et al., p. 440). Que MSE_EBLUP < Dd es lo esperado por construcción (g1 = γd·Dd < Dd), no una validación independiente del modelo.

```


## Celda 14



## Celda 15


**Salida:**

![fig](fig/modelo__fay_herriot_c15_9.png)
| Dominio_excluido | Cook | Parametro | Valor_completo | Valor_sin_dominio | Cambio_pct | Cambia_signo | p_completo | p_sin_dominio | Cambio_signif |
|---|---|---|---|---|---|---|---|---|---|
| Quibdó | 0.6009 | Intercepto | 9.1908 | 9.9341 | 8.1 | no | 0.0 | 0.0 | no |
| Quibdó | 0.6009 | TASA_HOMICIDIOS | 0.0993 | 0.0613 | -38.2 | no | 0.0058 | 0.2555 | pierde |
| Quibdó | 0.6009 | A_hat | 5.5288 | 5.5557 | 0.5 | no | None | None | no |
```
INTERPRETACIÓN (robustez del modelo elegido):
  Dominios por encima del umbral 4/n = 0.174: Quibdó, Cali A.M..
  Dominio más influyente: Quibdó (Cook = 0.601). Cambio relativo de cada coeficiente al reajustar sin él: TASA_HOMICIDIOS -38.2 %.
  ✗ Sin ese dominio dejan de ser significativas TASA_HOMICIDIOS: la significancia de las covariables depende de un solo territorio y debe reportarse como limitación.

```


## Celda 16



## Celda 17


**Salida:**

```
Bootstrap de dominios: 1000 ajustes: 0 fallidos (matriz singular), 0 sin convergencia, 0 con Â en la cota.

```
| Parametro | Beta_min | Dominio_beta_min | Beta_max | Dominio_beta_max | Cambio_pct_max_abs | Cambio_en_EE_max_abs | Dominio_max_cambio | N_cambia_signo | N_cruza_alfa | p_max | N_reajustes | N_dominios | Beta | EE_bootstrap | IC_inf | IC_sup | IC_incluye_cero | Prop_mismo_signo | Prop_p_menor_alfa | N_replicas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Intercepto | 8.75 | Cali A.M. | 9.9341 | Quibdó | 8.0873 | 0.7593 | Quibdó | 0 | 0 | 0.0 | 23 | 23 | 9.1908 | 1.0656 | 7.2289 | 11.2852 | False | 1.0 | 0.998 | 1000 |
| TASA_HOMICIDIOS | 0.0613 | Quibdó | 0.1249 | Cali A.M. | 38.1963 | 1.0546 | Quibdó | 0 | 1 | 0.2555 | 23 | 23 | 0.0993 | 0.0468 | 0.0108 | 0.1909 | False | 0.986 | 0.704 | 1000 |
```
- TASA_HOMICIDIOS: β̂ = 0.099; dejar-uno-fuera entre 0.061 y 0.125 (cambio máximo 38 %, signo cambia en 0 de 23, cruza el umbral de significancia en 1); bootstrap de dominios: IC [0.011, 0.191], mismo signo en 99 % y p < alfa en 70 % de las réplicas.

Los p-valores de los coeficientes son descriptivos: los mismos dominios se usaron para filtrar, seleccionar, comparar especificaciones y estimar β̂, así que la significancia no es una demostración fuerte. Los coeficientes del benchmark se reportan como asociaciones preliminares, condicionales a la selección.

```


## Celda 18



## Celda 19


**Salida:**

```
Ventana de las estimaciones directas: Ene-Dic 2018 (12 meses)
Valor de referencia (directa del conjunto): 10.8340 %  |  DANE «Total 23 ciudades y A.M.» Ene-Dic 2018: 10.8340 %  (dif. +0.0000 pp)
λ₁ = 0.999745  (agregado de los EBLUP antes del ajuste: 10.8368 %)

```


## Celda 20


**Salida:**

```

Predicciones sintéticas para 83 municipios sin estimación directa propia
Municipios cuya predicción es una extrapolación: 21 de 83: Argelia, Ansermanuevo, Yumbo, Balboa, Andalucía, Caloto, Puerto Tejada, Toro, Patía, Ginebra, El Águila, Puracé, Suárez, Silvia, Villa Rica, Guacarí, Buenos Aires, Guachené, Argelia, Corinto, El Tambo

```


## Celda 21


**Salida:**

| COVARIABLE | MIN_DOMINIOS | DOMINIO_MIN | MAX_DOMINIOS | DOMINIO_MAX | MIN_MUNICIPIOS | MEDIANA_MUNICIPIOS | MAX_MUNICIPIOS | N_DEBAJO | N_ENCIMA | N_MUNICIPIOS | PCT_FUERA |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TASA_HOMICIDIOS | 4.06 | Tunja | 71.96 | Quibdó | 0.0 | 42.67 | 221.47 | 3 | 18 | 83 | 25.3 |
![fig](fig/modelo__fay_herriot_c21_10.png)
```
Sensibilidad al quitar cada dominio (de mayor a menor cambio medio de las predicciones):

```
| DOMINIO_EXCLUIDO | Intercepto | TASA_HOMICIDIOS | A_HAT | CAMBIO_MEDIO_PP | CAMBIO_MAX_PP |
|---|---|---|---|---|---|
| Quibdó | 9.9341 | 0.0613 | 5.5557 | 1.3056 | 7.6534 |
| Cali A.M. | 8.75 | 0.1249 | 5.2823 | 0.9265 | 5.2486 |
| Armenia | 9.1577 | 0.0942 | 5.2205 | 0.2931 | 1.1645 |
| Cúcuta A.M. | 9.0719 | 0.0963 | 4.9091 | 0.2712 | 0.7811 |
| Tunja | 8.8979 | 0.1081 | 5.6392 | 0.2637 | 1.6609 |
| Valledupar | 8.8555 | 0.1063 | 5.0841 | 0.2057 | 1.2136 |
| Barranquilla A.M. | 9.3174 | 0.1008 | 5.1419 | 0.2046 | 0.4659 |
| Ibagué | 8.8903 | 0.1056 | 5.2434 | 0.187 | 1.1098 |
| Riohacha | 9.2063 | 0.0959 | 5.708 | 0.1561 | 0.7264 |
| Bucaramanga A.M. | 9.3791 | 0.0946 | 5.6559 | 0.1348 | 0.8332 |
| Pasto | 9.3703 | 0.0949 | 5.6709 | 0.1289 | 0.797 |
| Pereira A.M. | 9.3112 | 0.0993 | 5.4394 | 0.1227 | 0.1304 |
| Cartagena | 9.3511 | 0.0984 | 5.3212 | 0.1155 | 0.1603 |
| Santa Marta | 9.3683 | 0.0975 | 5.3485 | 0.1001 | 0.2182 |
| Sincelejo | 9.2918 | 0.097 | 5.7566 | 0.0662 | 0.4012 |
| Montería | 9.307 | 0.0974 | 5.6827 | 0.0601 | 0.2997 |
| Florencia | 9.0981 | 0.1001 | 5.6702 | 0.055 | 0.0927 |
| Manizales A.M. | 9.1594 | 0.0999 | 5.8028 | 0.0184 | 0.1061 |
| Popayán | 9.2251 | 0.0989 | 5.7953 | 0.0184 | 0.0518 |
| Villavicencio | 9.1673 | 0.0994 | 5.7982 | 0.0169 | 0.0236 |
| Bogotá | 9.2151 | 0.0987 | 5.8088 | 0.0157 | 0.0944 |
| Medellín A.M. | 9.1705 | 0.0994 | 5.8028 | 0.0153 | 0.0203 |
| Neiva | 9.1892 | 0.0993 | 5.8097 | 0.0009 | 0.0018 |
```
Municipios que extrapolan, de mayor a menor aporte de fuera del rango:

```
| PER | MES | CODIGO_DEPARTAMENTO | DEPARTAMENTO | CODIGO_MUNICIPIO | MUNICIPIO | ESTADO_EXTRAPOLACION | COVARIABLES_FUERA | COVARIABLE_PRINCIPAL | RAZON_H | PRED_SINTETICO | CV_SINTETICO_PCT | PRED_ACOTADA | APORTE_EXTRAPOLADO_PP | PRED_MIN_SIN_DOMINIO | PRED_MAX_SIN_DOMINIO | AMPLITUD_SIN_DOMINIO_PP | CAMBIO_MAX_PP | DOMINIO_MAS_INFLUYENTE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | 12 | 19 | Cauca | 19212 | Corinto | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 15.523 | 31.1739 | 24.09 | 16.3336 | 14.8404 | 23.5205 | 36.4225 | 12.902 | 7.6534 | Quibdó |
| 2018 | 12 | 76 | Valle del Cauca | 76243 | El Águila | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 9.678 | 27.0169 | 22.59 | 16.3336 | 10.6834 | 20.9513 | 31.1896 | 10.2383 | 6.0656 | Quibdó |
| 2018 | 12 | 19 | Cauca | 19573 | Puerto Tejada | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 6.765 | 24.456 | 21.52 | 16.3336 | 8.1224 | 19.3686 | 27.9659 | 8.5974 | 5.0875 | Quibdó |
| 2018 | 12 | 19 | Cauca | 19050 | Argelia | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 3.637 | 20.9601 | 19.93 | 16.3336 | 4.6265 | 17.2079 | 23.5652 | 6.3573 | 3.7521 | Quibdó |
| 2018 | 12 | 19 | Cauca | 19532 | Patía | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 3.301 | 20.5045 | 19.72 | 16.3336 | 4.1709 | 16.9264 | 22.9917 | 6.0653 | 3.5781 | Quibdó |
| 2018 | 12 | 76 | Valle del Cauca | 76054 | Argelia | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 3.104 | 20.2255 | 19.59 | 16.3336 | 3.892 | 16.754 | 22.6406 | 5.8866 | 3.4716 | Quibdó |
| 2018 | 12 | 76 | Valle del Cauca | 76041 | Ansermanuevo | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 2.949 | 20.0002 | 19.49 | 16.3336 | 3.6667 | 16.6147 | 22.3569 | 5.7422 | 3.3855 | Quibdó |
| 2018 | 12 | 76 | Valle del Cauca | 76318 | Guacarí | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 2.531 | 19.359 | 19.21 | 16.3336 | 3.0254 | 16.2184 | 21.5498 | 5.3313 | 3.1406 | Quibdó |
| 2018 | 12 | 76 | Valle del Cauca | 76823 | Toro | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 2.135 | 18.7009 | 18.93 | 16.3336 | 2.3674 | 15.8117 | 20.7214 | 4.9097 | 2.8892 | Quibdó |
| 2018 | 12 | 19 | Cauca | 19300 | Guachené | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 1.897 | 18.2741 | 18.76 | 16.3336 | 1.9405 | 15.5479 | 20.1841 | 4.6362 | 2.7262 | Quibdó |
| 2018 | 12 | 19 | Cauca | 19142 | Caloto | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 1.621 | 17.7421 | 18.56 | 16.3336 | 1.4085 | 15.2191 | 19.5143 | 4.2953 | 2.523 | Quibdó |
| 2018 | 12 | 19 | Cauca | 19256 | El Tambo | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 1.583 | 17.6636 | 18.53 | 16.3336 | 1.3301 | 15.1706 | 19.4156 | 4.245 | 2.493 | Quibdó |
| 2018 | 12 | 76 | Valle del Cauca | 76036 | Andalucía | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 1.55 | 17.5971 | 18.51 | 16.3336 | 1.2636 | 15.1295 | 19.3319 | 4.2024 | 2.4676 | Quibdó |
| 2018 | 12 | 19 | Cauca | 19845 | Villa Rica | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 1.43 | 17.345 | 18.43 | 16.3336 | 1.0115 | 14.9737 | 19.0145 | 4.0408 | 2.3713 | Quibdó |
| 2018 | 12 | 76 | Valle del Cauca | 76892 | Yumbo | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 1.256 | 16.9589 | 18.32 | 16.3336 | 0.6253 | 14.7351 | 18.5285 | 3.7934 | 2.2238 | Quibdó |
| 2018 | 12 | 19 | Cauca | 19110 | Buenos Aires | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 1.175 | 16.7693 | 18.27 | 16.3336 | 0.4358 | 14.6179 | 18.2898 | 3.6719 | 2.1514 | Quibdó |
| 2018 | 12 | 76 | Valle del Cauca | 76306 | Ginebra | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 0.292 | 9.1908 | 27.71 | 9.5938 | -0.403 | 8.75 | 9.9341 | 1.1841 | 0.7433 | Quibdó |
| 2018 | 12 | 19 | Cauca | 19585 | Puracé | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 0.292 | 9.1908 | 27.71 | 9.5938 | -0.403 | 8.75 | 9.9341 | 1.1841 | 0.7433 | Quibdó |
| 2018 | 12 | 19 | Cauca | 19743 | Silvia | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 0.292 | 9.1908 | 27.71 | 9.5938 | -0.403 | 8.75 | 9.9341 | 1.1841 | 0.7433 | Quibdó |
| 2018 | 12 | 19 | Cauca | 19075 | Balboa | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 1.152 | 16.7147 | 18.25 | 16.3336 | 0.3812 | 14.5842 | 18.2211 | 3.637 | 2.1306 | Quibdó |
| 2018 | 12 | 19 | Cauca | 19780 | Suárez | FUERA_DEL_RANGO | TASA_HOMICIDIOS | TASA_HOMICIDIOS | 1.129 | 16.6581 | 18.24 | 16.3336 | 0.3246 | 14.5492 | 18.1499 | 3.6007 | 2.109 | Quibdó |
![fig](fig/modelo__fay_herriot_c21_11.png)
```
Rango de las covariables (dominios con encuesta frente a municipios):
  • TASA_HOMICIDIOS: dominios de 4.06 (Tunja) a 71.96 (Quibdó); municipios de 0 a 221.5. Fuera del rango: 3 por debajo y 18 por encima (25 % de 83).

Estado de los 83 municipios: 62 dentro del rango, 21 fuera del rango de alguna covariable y 0 con una combinación de covariables que el modelo no vio (cada valor dentro de su rango).

Parte de la predicción que viene de salirse del rango, en los 21 municipios que extrapolan: mediana 1.4 pp, máximo 14.8 pp. Mayores: Corinto: 31.2 %, de los cuales 14.8 pp vienen de TASA_HOMICIDIOS (acotada: 16.3 %); El Águila: 27.0 %, de los cuales 10.7 pp vienen de TASA_HOMICIDIOS (acotada: 16.3 %); Puerto Tejada: 24.5 %, de los cuales 8.1 pp vienen de TASA_HOMICIDIOS (acotada: 16.3 %).
10 de ellos tienen una predicción mayor que la directa más alta de los dominios (17.8 %), un valor que el modelo nunca observó.

Al quitar un dominio a la vez, la predicción de los municipios que extrapolan se mueve en una franja de 4.30 pp (mediana; máximo 12.90 pp) frente a 0.79 pp en los que están dentro. El dominio que más cambia las predicciones es Quibdó (cambio medio 1.31 pp, máximo 7.65 pp).

Lectura: la tasa publicada no cambia, pero en los municipios marcados la predicción supone que la relación lineal sigue valiendo fuera de lo observado, y su CV no mide ese riesgo (Morales et al., 2021, p. 441 y 453; Molina, 2019, PDF 40-41).

```


## Celda 22



## Celda 23


**Salida:**

```
Cada coeficiente: mínimo y máximo de β̂(-d) y dominio responsable

```
| Parametro | Beta_completo | Beta_min | Dominio_beta_min | Beta_max | Dominio_beta_max | Cambio_pct_max_abs | Cambio_en_EE_max_abs | Dominio_max_cambio | N_cambia_signo | N_cruza_alfa |
|---|---|---|---|---|---|---|---|---|---|---|
| Intercepto | 9.1908 | 8.75 | Cali A.M. | 9.9341 | Quibdó | 8.0873 | 0.7593 | Quibdó | 0 | 0 |
| TASA_HOMICIDIOS | 0.0993 | 0.0613 | Quibdó | 0.1249 | Cali A.M. | 38.1963 | 1.0546 | Quibdó | 0 | 1 |
```
Los 3 dominios que más mueven cada coeficiente:

```
| Parametro | Dominio_excluido | Beta_completo | Beta_sin_dominio | Cambio_pct | Cambio_en_EE | Cambia_signo | Cruza_alfa |
|---|---|---|---|---|---|---|---|
| TASA_HOMICIDIOS | Quibdó | 0.0993 | 0.0613 | -38.1963 | -1.0546 | False | True |
| TASA_HOMICIDIOS | Cali A.M. | 0.0993 | 0.1249 | 25.8808 | 0.7146 | False | False |
| TASA_HOMICIDIOS | Tunja | 0.0993 | 0.1081 | 8.8879 | 0.2454 | False | False |
![fig](fig/modelo__fay_herriot_c23_12.png)
```
Influencia de cada dominio en coeficientes y predicciones (de mayor a menor):

```
| Dominio_excluido | Cambio_en_EE_max_abs | Parametro_max | N_coef_sobre_umbral | N_cambia_signo | N_cruza_alfa | Cambio_EBLUP_max_pp | Dominio_EBLUP_max | N_EBLUP_sobre_umbral | Cambio_sintetico_max_pp | Municipio_max | Cambio_sintetico_medio_pp | N_sintetico_sobre_umbral | Cambio_sintetico_max_extrapolan_pp | Cambio_sintetico_max_no_extrapolan_pp | N_cambia_confiabilidad | A_completo | A_sin_dominio | Cambio_A_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Quibdó | 1.0546 | TASA_HOMICIDIOS | 1 | 0 | 1 | -0.0184 | Cali A.M. | 0 | -7.6534 | Corinto (19212) | 1.3056 | 51 | 7.6534 | 1.9304 | 48 | 5.5288 | 5.5557 | 0.485 |
| Cali A.M. | 0.7146 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0474 | Quibdó | 0 | 5.2486 | Corinto (19212) | 0.9265 | 45 | 5.2486 | 1.3708 | 7 | 5.5288 | 5.2823 | -4.459 |
| Tunja | 0.2454 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0123 | Quibdó | 0 | 1.6609 | Corinto (19212) | 0.2637 | 10 | 1.6609 | 0.3292 | 2 | 5.5288 | 5.6392 | 1.9969 |
| Valledupar | 0.1945 | TASA_HOMICIDIOS | 0 | 0 | 0 | -0.0123 | Cúcuta A.M. | 0 | 1.2136 | Corinto (19212) | 0.2057 | 3 | 1.2136 | 0.2868 | 6 | 5.5288 | 5.0841 | -8.0438 |
| Ibagué | 0.1771 | TASA_HOMICIDIOS | 0 | 0 | 0 | -0.0085 | Cúcuta A.M. | 0 | 1.1098 | Corinto (19212) | 0.187 | 3 | 1.1098 | 0.2563 | 4 | 5.5288 | 5.2434 | -5.1634 |
| Armenia | 0.1421 | TASA_HOMICIDIOS | 0 | 0 | 0 | -0.0172 | Quibdó | 0 | -1.1645 | Corinto (19212) | 0.2931 | 10 | 1.1645 | 0.3933 | 4 | 5.5288 | 5.2205 | -5.5769 |
| Bucaramanga A.M. | 0.1283 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0038 | Tunja | 0 | -0.8332 | Corinto (19212) | 0.1348 | 3 | 0.8332 | 0.1563 | 5 | 5.5288 | 5.6559 | 2.2988 |
| Pasto | 0.1226 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0039 | Cúcuta A.M. | 0 | -0.797 | Corinto (19212) | 0.1289 | 2 | 0.797 | 0.149 | 5 | 5.5288 | 5.6709 | 2.5686 |
| Riohacha | 0.0932 | TASA_HOMICIDIOS | 0 | 0 | 0 | -0.0059 | Quibdó | 0 | -0.7264 | Corinto (19212) | 0.1561 | 2 | 0.7264 | 0.2207 | 8 | 5.5288 | 5.708 | 3.2406 |
| Cúcuta A.M. | 0.0832 | TASA_HOMICIDIOS | 0 | 0 | 0 | -0.0187 | Quibdó | 0 | -0.7811 | Corinto (19212) | 0.2712 | 3 | 0.7811 | 0.3298 | 8 | 5.5288 | 4.9091 | -11.2094 |
| Sincelejo | 0.0631 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0047 | Cúcuta A.M. | 0 | -0.4012 | Corinto (19212) | 0.0662 | 0 | 0.4012 | 0.0852 | 7 | 5.5288 | 5.7566 | 4.1188 |
| Montería | 0.0522 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0041 | Cúcuta A.M. | 0 | -0.2997 | Corinto (19212) | 0.0601 | 0 | 0.2997 | 0.1031 | 4 | 5.5288 | 5.6827 | 2.7821 |
| Santa Marta | 0.0497 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0031 | Pasto | 0 | -0.2182 | Corinto (19212) | 0.1001 | 0 | 0.2182 | 0.1651 | 6 | 5.5288 | 5.3485 | -3.2624 |
| Barranquilla A.M. | 0.0426 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0062 | Cali A.M. | 0 | 0.4659 | Corinto (19212) | 0.2046 | 0 | 0.4659 | 0.2346 | 10 | 5.5288 | 5.1419 | -6.9994 |
| Cartagena | 0.025 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0032 | Cali A.M. | 0 | 0.1603 | Ginebra (76306) | 0.1155 | 0 | 0.1603 | 0.1541 | 6 | 5.5288 | 5.3212 | -3.7555 |
| Florencia | 0.0231 | TASA_HOMICIDIOS | 0 | 0 | 0 | -0.0018 | Cartagena | 0 | -0.0927 | Ginebra (76306) | 0.055 | 0 | 0.0927 | 0.087 | 4 | 5.5288 | 5.6702 | 2.5562 |
| Manizales A.M. | 0.0173 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0042 | Cúcuta A.M. | 0 | 0.1061 | Corinto (19212) | 0.0184 | 0 | 0.1061 | 0.0271 | 6 | 5.5288 | 5.8028 | 4.9559 |
| Bogotá | 0.0149 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0049 | Cúcuta A.M. | 0 | -0.0944 | Corinto (19212) | 0.0157 | 0 | 0.0944 | 0.0206 | 7 | 5.5288 | 5.8088 | 5.0632 |
| Popayán | 0.0108 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.005 | Cúcuta A.M. | 0 | -0.0518 | Corinto (19212) | 0.0184 | 0 | 0.0518 | 0.0316 | 6 | 5.5288 | 5.7953 | 4.8189 |
| Villavicencio | 0.0037 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.004 | Cúcuta A.M. | 0 | -0.0236 | Ginebra (76306) | 0.0169 | 0 | 0.0236 | 0.0226 | 6 | 5.5288 | 5.7982 | 4.8717 |
| Medellín A.M. | 0.0028 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0042 | Cúcuta A.M. | 0 | -0.0203 | Ginebra (76306) | 0.0153 | 0 | 0.0203 | 0.0196 | 6 | 5.5288 | 5.8028 | 4.9551 |
| Pereira A.M. | 0.0013 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0034 | Quibdó | 0 | 0.1304 | Corinto (19212) | 0.1227 | 0 | 0.1304 | 0.1235 | 4 | 5.5288 | 5.4394 | -1.6176 |
| Neiva | 0.0004 | TASA_HOMICIDIOS | 0 | 0 | 0 | 0.0046 | Cúcuta A.M. | 0 | 0.0018 | Corinto (19212) | 0.0009 | 0 | 0.0018 | 0.0015 | 6 | 5.5288 | 5.8097 | 5.0803 |
```
- TASA_HOMICIDIOS: β̂ = 0.099; al retirar un dominio queda entre 0.061 (sin Quibdó) y 0.125 (sin Cali A.M.); cambio máximo 38 % = 1.05 EE (sin Quibdó), que supera 1 EE; signo cambia en 0 de 23 y cruza la significancia en 1.

Dominio más influyente en los coeficientes: Quibdó (1.05 EE en TASA_HOMICIDIOS). Dominios con algún coeficiente sobre 1 EE: 1 de 23.
EBLUP de los dominios que quedan: el mayor cambio es +0.05 pp en Quibdó al retirar Cali A.M.; 0 exclusiones mueven algún EBLUP más de 0.5 pp.
Predicción sintética de municipios: el mayor cambio es -7.65 pp en Corinto (19212) al retirar Quibdó; 10 exclusiones mueven algún municipio más de 0.5 pp.
  Máximo en municipios que extrapolan: 7.65 pp; en los que no extrapolan: 1.93 pp.
Cambios de clase de confiabilidad (CV) sumados sobre todas las exclusiones: 175. Â cambia como máximo 11 %.

Los p-valores de los coeficientes son descriptivos: los mismos dominios se usaron para filtrar, seleccionar, comparar especificaciones y estimar β̂, así que la significancia no es una demostración fuerte. Los coeficientes del benchmark se reportan como asociaciones preliminares, condicionales a la selección.

```


## Celda 24



## Celda 25


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
Selección repetida con los 23 dominios = conjunto del análisis (EC1): PASS  (['TASA_HOMICIDIOS', 'COB_ACUEDUCTO'])
Benchmark repetido con los 23 dominios = benchmark seleccionado: PASS

Métricas de predicción fuera de muestra (error = predicción − directa):

```
| Ejercicio | Descripcion | N | RMSE | MAE | Sesgo_medio | RMSE_corregido | Z_psi_media | Z_psi_sd | Z_psi_cuad_medio | Z_pred_media | Z_pred_sd | Z_pred_cuad_medio | Z_pred_max_abs | Cobertura | Nivel_nominal | RMSE_dentro_muestra | Inflacion_vs_dentro | Habilidad_vs_nulo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| COVARIABLES_FIJAS | Covariables del benchmark fijas | 23 | 2.5243 | 2.1261 | -0.0676 | 2.5062 | 0.9155 | 8.8297 | 75.4113 | -0.0157 | 1.0494 | 1.0537 | 1.8986 | 1.0 | 0.95 | 2.2668 | 1.1136 | 0.1704 |
| PROCEDIMIENTO_COMPLETO | Procedimiento completo | 23 | 3.4346 | 2.9059 | -0.4079 | 3.4213 | -0.1534 | 11.8144 | 133.5342 | -0.1697 | 1.4357 | 2.0004 | 3.1721 | 0.8696 | 0.95 | 2.2668 | 1.5152 | -0.5357 |
| SIN_COVARIABLES | Sin covariables (referencia) | 23 | 2.7715 | 2.2306 | -0.0102 | 2.755 | 1.2981 | 9.2278 | 83.1352 | -0.0189 | 1.0676 | 1.0905 | 2.6629 | 0.9565 | 0.95 | None | None | None |
```
Selección en cada iteración (qué elige el procedimiento al retirar cada dominio):

```
| Dominio_excluido | Seleccion_EDA | Benchmark |
|---|---|---|
| Medellín A.M. | TASA_HOMICIDIOS + COB_ACUEDUCTO | TASA_HOMICIDIOS |
| Barranquilla A.M. | TASA_HOMICIDIOS | TASA_HOMICIDIOS |
| Bogotá | TASA_HOMICIDIOS + ING_TRIB_PC | TASA_HOMICIDIOS + ING_TRIB_PC |
| Cartagena | TASA_HOMICIDIOS | TASA_HOMICIDIOS |
| Tunja | TASA_HOMICIDIOS + COB_ACUEDUCTO | TASA_HOMICIDIOS |
| Manizales A.M. | TASA_HOMICIDIOS + COB_ACUEDUCTO | TASA_HOMICIDIOS |
| Florencia | — | — |
| Popayán | TASA_HOMICIDIOS + COB_ACUEDUCTO | TASA_HOMICIDIOS |
| Valledupar | TASA_HOMICIDIOS + COB_ACUEDUCTO | TASA_HOMICIDIOS |
| Montería | TASA_HOMICIDIOS + COB_ACUEDUCTO | TASA_HOMICIDIOS |
| Quibdó | — | — |
| Neiva | TASA_HOMICIDIOS + VA_PCT_PRIM | TASA_HOMICIDIOS + VA_PCT_PRIM |
| Riohacha | — | — |
| Santa Marta | COB_ACUEDUCTO + TASA_HOMICIDIOS | COB_ACUEDUCTO |
| Villavicencio | TASA_HOMICIDIOS + COB_ACUEDUCTO | TASA_HOMICIDIOS |
| Pasto | — | — |
| Cúcuta A.M. | COB_ACUEDUCTO + TASA_HOMICIDIOS | COB_ACUEDUCTO |
| Armenia | COB_NET_MEDIA + COB_ACUEDUCTO | COB_NET_MEDIA |
| Pereira A.M. | TASA_HOMICIDIOS | TASA_HOMICIDIOS |
| Bucaramanga A.M. | TASA_HOMICIDIOS + COB_ACUEDUCTO | TASA_HOMICIDIOS |
| Sincelejo | TASA_HOMICIDIOS + COB_ACUEDUCTO | TASA_HOMICIDIOS |
| Ibagué | TASA_HOMICIDIOS + COB_ACUEDUCTO | TASA_HOMICIDIOS |
| Cali A.M. | TASA_HOMICIDIOS + COB_NET_MEDIA | TASA_HOMICIDIOS |
```
Frecuencia con que entra cada covariable:

```
| Covariable | Codigo | Frecuencia_EDA | Frecuencia_benchmark | En_benchmark |
|---|---|---|---|---|
| TASA_HOMICIDIOS | 060010003 | 0.783 | 0.696 | sí |
| COB_ACUEDUCTO | 030010004 | 0.565 | 0.087 | no |
| COB_NET_MEDIA | 040010010 | 0.087 | 0.043 | no |
| ING_TRIB_PC | 070010020 | 0.043 | 0.043 | no |
| VA_PCT_PRIM | 120210008 | 0.043 | 0.043 | no |
```
Detalle por dominio (benchmark con covariables fijas y procedimiento completo):

```
| Ejercicio | NOMBRE_DOMINIO | Directa | SE_directa | Prediccion | RMSE_sintetico | Error | Z_psi | Z_pred | Covariables |
|---|---|---|---|---|---|---|---|---|---|
| COVARIABLES_FIJAS | Medellín A.M. | 11.838 | 0.238 | 11.417 | 2.464 | -0.421 | -1.766 | -0.17 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Barranquilla A.M. | 8.148 | 0.204 | 11.867 | 2.32 | 3.719 | 18.265 | 1.597 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Bogotá | 10.37 | 0.235 | 10.628 | 2.491 | 0.258 | 1.099 | 0.103 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Cartagena | 8.348 | 0.262 | 11.545 | 2.36 | 3.196 | 12.216 | 1.346 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Tunja | 11.314 | 0.326 | 9.337 | 2.549 | -1.977 | -6.067 | -0.769 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Manizales A.M. | 11.237 | 0.284 | 10.841 | 2.477 | -0.396 | -1.393 | -0.159 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Florencia | 12.94 | 0.371 | 11.238 | 2.437 | -1.702 | -4.582 | -0.69 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Popayán | 10.678 | 0.296 | 11.246 | 2.465 | 0.569 | 1.923 | 0.229 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Valledupar | 14.45 | 0.329 | 10.525 | 2.324 | -3.926 | -11.938 | -1.673 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Montería | 9.467 | 0.265 | 11.112 | 2.446 | 1.645 | 6.198 | 0.669 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Quibdó | 17.813 | 0.44 | 14.349 | 3.643 | -3.465 | -7.88 | -0.944 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Neiva | 11.534 | 0.311 | 11.494 | 2.465 | -0.039 | -0.127 | -0.016 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Riohacha | 13.884 | 0.322 | 12.42 | 2.474 | -1.464 | -4.542 | -0.587 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Santa Marta | 8.316 | 0.233 | 11.418 | 2.367 | 3.102 | 13.318 | 1.304 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Villavicencio | 11.873 | 0.32 | 11.394 | 2.463 | -0.48 | -1.501 | -0.193 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Pasto | 8.816 | 0.285 | 10.553 | 2.473 | 1.737 | 6.104 | 0.698 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Cúcuta A.M. | 15.983 | 0.366 | 11.62 | 2.269 | -4.363 | -11.911 | -1.899 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Armenia | 15.491 | 0.342 | 11.964 | 2.349 | -3.527 | -10.318 | -1.486 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Pereira A.M. | 8.867 | 0.269 | 11.653 | 2.386 | 2.786 | 10.363 | 1.161 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Bucaramanga A.M. | 8.739 | 0.276 | 10.566 | 2.469 | 1.827 | 6.616 | 0.735 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Sincelejo | 9.606 | 0.251 | 10.688 | 2.479 | 1.083 | 4.307 | 0.435 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Ibagué | 13.994 | 0.329 | 10.525 | 2.361 | -3.469 | -10.532 | -1.455 | TASA_HOMICIDIOS |
| COVARIABLES_FIJAS | Cali A.M. | 11.651 | 0.284 | 15.402 | 2.654 | 3.75 | 13.204 | 1.405 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Medellín A.M. | 11.838 | 0.238 | 11.417 | 2.464 | -0.421 | -1.766 | -0.17 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Barranquilla A.M. | 8.148 | 0.204 | 11.867 | 2.32 | 3.719 | 18.265 | 1.597 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Bogotá | 10.37 | 0.235 | 5.392 | 2.972 | -4.978 | -21.211 | -1.67 | TASA_HOMICIDIOS + ING_TRIB_PC |
| PROCEDIMIENTO_COMPLETO | Cartagena | 8.348 | 0.262 | 11.545 | 2.36 | 3.196 | 12.216 | 1.346 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Tunja | 11.314 | 0.326 | 9.337 | 2.549 | -1.977 | -6.067 | -0.769 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Manizales A.M. | 11.237 | 0.284 | 10.841 | 2.477 | -0.396 | -1.393 | -0.159 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Florencia | 12.94 | 0.371 | 11.464 | 2.793 | -1.476 | -3.975 | -0.524 | — |
| PROCEDIMIENTO_COMPLETO | Popayán | 10.678 | 0.296 | 11.246 | 2.465 | 0.569 | 1.923 | 0.229 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Valledupar | 14.45 | 0.329 | 10.525 | 2.324 | -3.926 | -11.938 | -1.673 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Montería | 9.467 | 0.265 | 11.112 | 2.446 | 1.645 | 6.198 | 0.669 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Quibdó | 17.813 | 0.44 | 11.244 | 2.428 | -6.569 | -14.942 | -2.663 | — |
| PROCEDIMIENTO_COMPLETO | Neiva | 11.534 | 0.311 | 14.352 | 2.616 | 2.818 | 9.076 | 1.07 | TASA_HOMICIDIOS + VA_PCT_PRIM |
| PROCEDIMIENTO_COMPLETO | Riohacha | 13.884 | 0.322 | 11.42 | 2.759 | -2.464 | -7.645 | -0.887 | — |
| PROCEDIMIENTO_COMPLETO | Santa Marta | 8.316 | 0.233 | 12.815 | 2.341 | 4.499 | 19.316 | 1.912 | COB_ACUEDUCTO |
| PROCEDIMIENTO_COMPLETO | Villavicencio | 11.873 | 0.32 | 11.394 | 2.463 | -0.48 | -1.501 | -0.193 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Pasto | 8.816 | 0.285 | 11.65 | 2.743 | 2.835 | 9.959 | 1.028 | — |
| PROCEDIMIENTO_COMPLETO | Cúcuta A.M. | 15.983 | 0.366 | 11.042 | 2.265 | -4.942 | -13.49 | -2.153 | COB_ACUEDUCTO |
| PROCEDIMIENTO_COMPLETO | Armenia | 15.491 | 0.342 | 8.48 | 2.184 | -7.011 | -20.51 | -3.172 | COB_NET_MEDIA |
| PROCEDIMIENTO_COMPLETO | Pereira A.M. | 8.867 | 0.269 | 11.653 | 2.386 | 2.786 | 10.363 | 1.161 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Bucaramanga A.M. | 8.739 | 0.276 | 10.566 | 2.469 | 1.827 | 6.616 | 0.735 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Sincelejo | 9.606 | 0.251 | 10.688 | 2.479 | 1.083 | 4.307 | 0.435 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Ibagué | 13.994 | 0.329 | 10.525 | 2.361 | -3.469 | -10.532 | -1.455 | TASA_HOMICIDIOS |
| PROCEDIMIENTO_COMPLETO | Cali A.M. | 11.651 | 0.284 | 15.402 | 2.654 | 3.75 | 13.204 | 1.405 | TASA_HOMICIDIOS |
![fig](fig/modelo__fay_herriot_c25_13.png)
```
- Covariables del benchmark fijas: RMSE 2.52 pp, MAE 2.13, sesgo -0.07; RMSE corregido por ruido 2.51; Z_psi: media +0.92, media de Z² 75.41; Z_pred: media -0.02, sd 1.05, cobertura 100 % (nominal 95 %); habilidad frente a solo intercepto +0.17.
- Procedimiento completo: RMSE 3.43 pp, MAE 2.91, sesgo -0.41; RMSE corregido por ruido 3.42; Z_psi: media -0.15, media de Z² 133.53; Z_pred: media -0.17, sd 1.44, cobertura 87 % (nominal 95 %); habilidad frente a solo intercepto -0.54.
- Sin covariables (referencia): RMSE 2.77 pp, MAE 2.23, sesgo -0.01; RMSE corregido por ruido 2.76; Z_psi: media +1.30, media de Z² 83.14; Z_pred: media -0.02, sd 1.07, cobertura 96 % (nominal 95 %).
- Costo de seleccionar con los mismos datos: la RMSE pasa de 2.52 (covariables fijas) a 3.43 (procedimiento completo), 1.36 veces.
- Error dentro de muestra del ajuste con todos los dominios: 2.27 pp.
- El procedimiento completo reproduce el benchmark en 14 de 23 iteraciones; obtiene 6 conjuntos distintos (sin covariables en 4); Jaccard mediano con el benchmark 1.00.
- Procedimiento completo: |Z_pred| > 1.96 en Quibdó (-2.66), Cúcuta A.M. (-2.15), Armenia (-3.17).

Con 23 dominios son 23 predicciones: las métricas tienen baja precisión y se leen como orden de magnitud. La directa es una estimación con ruido ψ_d, por eso se reportan los errores estandarizados y el RMSE corregido. El pre-filtrado de covariables no se repitió (no depende de la respuesta).

⚠ ADVERTENCIA (R-04): repitiendo la selección en cada iteración, el procedimiento predice peor que el modelo de solo intercepto (RMSE 3.43 frente a 2.77 pp; habilidad -0.54). Con las covariables del benchmark fijas la RMSE es 2.52, pero ese ejercicio es optimista porque la selección vio al dominio retirado. El benchmark cambia entre iteraciones: se reproduce en 14 de 23, aparecen 6 conjuntos distintos y en 4 no queda ninguna covariable. La regla del benchmark no cambia (significancia, AIC y parsimonia; Morales et al., p. 453), pero la predicción de los municipios sin encuesta es sintética (Benedetti et al., 2024, p. 141) y esta falta de capacidad predictiva fuera de la muestra se reporta como limitación en el documento.

```


## Celda 26


**Salida:**

```
Municipios ajustados a su dominio A.M.: 2

```
| CODIGO_DOMINIO_PADRE | MUNICIPIO | PESO_N2 | PRED_SINTETICO | LAMBDA_N2 | PRED_BENCHMARK | CV_SINTETICO_PCT | CV_BENCHMARK_PCT |
|---|---|---|---|---|---|---|---|
| 76001 | Yumbo | 82360.0 | 16.9589 | 0.807749 | 13.6985 | 18.32 | 30.03 |
| 76001 | Cali | 1769861.0 | 14.3553 | 0.807749 | 11.5955 | 18.2 | 29.96 |
| CODIGO_DOMINIO | SINTETICO_DOMINIO | AGREGADO_MUNICIPIOS | BRECHA_PP | EBLUP_AJUSTADO |
|---|---|---|---|---|
| 76001 | 14.475 | 14.4711 | -0.0039 | 11.689 |


## Celda 27


**Salida:**

```

Tabla final consolidada: 23 dominios + 83 municipios (2 ajustados a su dominio A.M.)

```
| NIVEL | PER | MES | DEPARTAMENTO | CODIGO | NOMBRE | CODIGO_DOMINIO_PADRE | TIPO | TASA_DESEMPLEO_PCT | TASA_SIN_AJUSTE_PCT | LAMBDA | CV_PCT | CONFIABILIDAD | BASE_CV | ESTADO_EXTRAPOLACION | CALIDAD_REPORTADA | MODELO_FUENTE | ESTADO_RESULTADO | FUERA_DE_RANGO | EXTRAPOLA | APORTE_EXTRAPOLADO_PP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DOMINIO | 2018 | 12 | ANTIOQUIA | 05001 | Medellín A.M. | None | EBLUP_BENCHMARK | 11.8307 | 11.8337 | 0.999745 | 2.01 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | ATLÁNTICO | 08001 | Barranquilla A.M. | None | EBLUP_BENCHMARK | 8.1723 | 8.1743 | 0.999745 | 2.48 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | BOGOTÁ, D.C. | 11001 | Bogotá | None | EBLUP_BENCHMARK | 10.3696 | 10.3723 | 0.999745 | 2.25 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | BOLÍVAR | 13001 | Cartagena | None | EBLUP_BENCHMARK | 8.3837 | 8.3858 | 0.999745 | 3.11 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | BOYACÁ | 15001 | Tunja | None | EBLUP_BENCHMARK | 11.2786 | 11.2815 | 0.999745 | 2.87 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | CALDAS | 17001 | Manizales A.M. | None | EBLUP_BENCHMARK | 11.2288 | 11.2317 | 0.999745 | 2.52 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | CAQUETÁ | 18001 | Florencia | None | EBLUP_BENCHMARK | 12.8972 | 12.9005 | 0.999745 | 2.85 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | CAUCA | 19001 | Popayán | None | EBLUP_BENCHMARK | 10.6832 | 10.686 | 0.999745 | 2.75 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | CESAR | 20001 | Valledupar | None | EBLUP_BENCHMARK | 14.3758 | 14.3795 | 0.999745 | 2.27 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | CÓRDOBA | 23001 | Montería | None | EBLUP_BENCHMARK | 9.4847 | 9.4871 | 0.999745 | 2.78 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | CHOCÓ | 27001 | Quibdó | None | EBLUP_BENCHMARK | 17.7586 | 17.7631 | 0.999745 | 2.46 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | HUILA | 41001 | Neiva | None | EBLUP_BENCHMARK | 11.5301 | 11.533 | 0.999745 | 2.67 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | LA GUAJIRA | 44001 | Riohacha | None | EBLUP_BENCHMARK | 13.8552 | 13.8587 | 0.999745 | 2.31 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | MAGDALENA | 47001 | Santa Marta | None | EBLUP_BENCHMARK | 8.343 | 8.3452 | 0.999745 | 2.78 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | META | 50001 | Villavicencio | None | EBLUP_BENCHMARK | 11.862 | 11.865 | 0.999745 | 2.67 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | NARIÑO | 52001 | Pasto | None | EBLUP_BENCHMARK | 8.8369 | 8.8392 | 0.999745 | 3.2 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | NORTE DE SANTANDER | 54001 | Cúcuta A.M. | None | EBLUP_BENCHMARK | 15.8806 | 15.8847 | 0.999745 | 2.28 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | QUINDÍO | 63001 | Armenia | None | EBLUP_BENCHMARK | 15.4184 | 15.4223 | 0.999745 | 2.2 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | RISARALDA | 66001 | Pereira A.M. | None | EBLUP_BENCHMARK | 8.8987 | 8.901 | 0.999745 | 3.01 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | SANTANDER | 68001 | Bucaramanga A.M. | None | EBLUP_BENCHMARK | 8.76 | 8.7622 | 0.999745 | 3.13 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | SUCRE | 70001 | Sincelejo | None | EBLUP_BENCHMARK | 9.6147 | 9.6171 | 0.999745 | 2.6 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | TOLIMA | 73001 | Ibagué | None | EBLUP_BENCHMARK | 13.9277 | 13.9313 | 0.999745 | 2.35 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| DOMINIO | 2018 | 12 | VALLE DEL CAUCA | 76001 | Cali A.M. | None | EBLUP_BENCHMARK | 11.689 | 11.692 | 0.999745 | 2.42 | Confiable | EBLUP | DENTRO_DEL_RANGO | Confiable | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19022 | ALMAGUER | None | SINTETICO | 14.5707 | 14.5707 | 1.0 | 18.15 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19050 | ARGELIA | None | SINTETICO | 20.9601 | 20.9601 | 1.0 | 19.93 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 4.6265 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19075 | BALBOA | None | SINTETICO | 16.7147 | 16.7147 | 1.0 | 18.25 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 0.3812 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19100 | BOLÍVAR | None | SINTETICO | 15.4521 | 15.4521 | 1.0 | 18.07 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19110 | BUENOS AIRES | None | SINTETICO | 16.7693 | 16.7693 | 1.0 | 18.27 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 0.4358 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19130 | CAJIBÍO | None | SINTETICO | 12.9706 | 12.9706 | 1.0 | 18.96 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19137 | CALDONO | None | SINTETICO | 10.4335 | 10.4335 | 1.0 | 23.34 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19142 | CALOTO | None | SINTETICO | 17.7421 | 17.7421 | 1.0 | 18.56 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 1.4085 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19212 | CORINTO | None | SINTETICO | 31.1739 | 31.1739 | 1.0 | 24.09 | No confiable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | No confiable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 14.8404 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19256 | EL TAMBO | None | SINTETICO | 17.6636 | 17.6636 | 1.0 | 18.53 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 1.3301 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19290 | FLORENCIA | None | SINTETICO | 13.0074 | 13.0074 | 1.0 | 18.93 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19300 | GUACHENÉ | None | SINTETICO | 18.2741 | 18.2741 | 1.0 | 18.76 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 1.9405 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19318 | GUAPI | None | SINTETICO | 10.9884 | 10.9884 | 1.0 | 21.94 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19355 | INZÁ | None | SINTETICO | 9.8787 | 9.8787 | 1.0 | 25.06 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19364 | JAMBALÓ | None | SINTETICO | 10.8604 | 10.8604 | 1.0 | 22.23 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19392 | LA SIERRA | None | SINTETICO | 11.9612 | 11.9612 | 1.0 | 20.13 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19397 | LA VEGA | None | SINTETICO | 10.4058 | 10.4058 | 1.0 | 23.42 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19418 | LÓPEZ DE MICAY | None | SINTETICO | 15.067 | 15.067 | 1.0 | 18.08 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19450 | MERCADERES | None | SINTETICO | 16.1906 | 16.1906 | 1.0 | 18.14 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19455 | MIRANDA | None | SINTETICO | 15.8373 | 15.8373 | 1.0 | 18.1 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | -0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19473 | MORALES | None | SINTETICO | 11.4907 | 11.4907 | 1.0 | 20.91 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19513 | PADILLA | None | SINTETICO | 12.1875 | 12.1875 | 1.0 | 19.81 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19517 | PÁEZ | None | SINTETICO | 10.7085 | 10.7085 | 1.0 | 22.61 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19532 | PATÍA | None | SINTETICO | 20.5045 | 20.5045 | 1.0 | 19.72 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 4.1709 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19533 | PIAMONTE | None | SINTETICO | 11.444 | 11.444 | 1.0 | 21.0 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19548 | PIENDAMÓ - TUNÍA | None | SINTETICO | 11.1363 | 11.1363 | 1.0 | 21.61 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19573 | PUERTO TEJADA | None | SINTETICO | 24.456 | 24.456 | 1.0 | 21.52 | No confiable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | No confiable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 8.1224 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19585 | PURACÉ | None | SINTETICO | 9.1908 | 9.1908 | 1.0 | 27.71 | No confiable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | No confiable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | -0.403 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19622 | ROSAS | None | SINTETICO | 12.651 | 12.651 | 1.0 | 19.26 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | -0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19693 | SAN SEBASTIÁN | None | SINTETICO | 10.0971 | 10.0971 | 1.0 | 24.34 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19698 | SANTANDER DE QUILICHAO | None | SINTETICO | 15.2119 | 15.2119 | 1.0 | 18.07 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19701 | SANTA ROSA | None | SINTETICO | 11.05 | 11.05 | 1.0 | 21.8 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19743 | SILVIA | None | SINTETICO | 9.1908 | 9.1908 | 1.0 | 27.71 | No confiable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | No confiable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | -0.403 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19760 | SOTARÁ - PAISPAMBA | None | SINTETICO | 11.3269 | 11.3269 | 1.0 | 21.22 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19780 | SUÁREZ | None | SINTETICO | 16.6581 | 16.6581 | 1.0 | 18.24 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 0.3246 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19785 | SUCRE | None | SINTETICO | 11.2832 | 11.2832 | 1.0 | 21.31 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | -0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19807 | TIMBÍO | None | SINTETICO | 11.4291 | 11.4291 | 1.0 | 21.03 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19809 | TIMBIQUÍ | None | SINTETICO | 14.5151 | 14.5151 | 1.0 | 18.16 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19821 | TORIBÍO | None | SINTETICO | 10.6003 | 10.6003 | 1.0 | 22.89 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19824 | TOTORÓ | None | SINTETICO | 11.2117 | 11.2117 | 1.0 | 21.45 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | CAUCA | 19845 | VILLA RICA | None | SINTETICO | 17.345 | 17.345 | 1.0 | 18.43 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 1.0115 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76001 | SANTIAGO DE CALI | 76001 | SINTETICO_BENCHMARK | 11.5955 | 14.3553 | 0.807749 | 29.96 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76020 | ALCALÁ | None | SINTETICO | 13.4262 | 13.4262 | 1.0 | 18.62 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76036 | ANDALUCÍA | None | SINTETICO | 17.5971 | 17.5971 | 1.0 | 18.51 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 1.2636 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76041 | ANSERMANUEVO | None | SINTETICO | 20.0002 | 20.0002 | 1.0 | 19.49 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 3.6667 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76054 | ARGELIA | None | SINTETICO | 20.2255 | 20.2255 | 1.0 | 19.59 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 3.892 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76100 | BOLÍVAR | None | SINTETICO | 16.006 | 16.006 | 1.0 | 18.12 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76109 | BUENAVENTURA | None | SINTETICO | 12.122 | 12.122 | 1.0 | 19.9 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76111 | GUADALAJARA DE BUGA | None | SINTETICO | 14.7166 | 14.7166 | 1.0 | 18.12 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76113 | BUGALAGRANDE | None | SINTETICO | 15.7211 | 15.7211 | 1.0 | 18.09 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76122 | CAICEDONIA | None | SINTETICO | 15.734 | 15.734 | 1.0 | 18.09 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76126 | CALIMA | None | SINTETICO | 11.9393 | 11.9393 | 1.0 | 20.16 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76130 | CANDELARIA | None | SINTETICO | 15.5683 | 15.5683 | 1.0 | 18.08 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76147 | CARTAGO | None | SINTETICO | 12.5547 | 12.5547 | 1.0 | 19.37 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76233 | DAGUA | None | SINTETICO | 11.8549 | 11.8549 | 1.0 | 20.29 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76243 | EL ÁGUILA | None | SINTETICO | 27.0169 | 27.0169 | 1.0 | 22.59 | No confiable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | No confiable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 10.6834 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76246 | EL CAIRO | None | SINTETICO | 10.641 | 10.641 | 1.0 | 22.78 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76248 | EL CERRITO | None | SINTETICO | 16.0457 | 16.0457 | 1.0 | 18.12 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76250 | EL DOVIO | None | SINTETICO | 13.6585 | 13.6585 | 1.0 | 18.48 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76275 | FLORIDA | None | SINTETICO | 12.3046 | 12.3046 | 1.0 | 19.66 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76306 | GINEBRA | None | SINTETICO | 9.1908 | 9.1908 | 1.0 | 27.71 | No confiable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | No confiable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | -0.403 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76318 | GUACARÍ | None | SINTETICO | 19.359 | 19.359 | 1.0 | 19.21 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 3.0254 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76364 | JAMUNDÍ | None | SINTETICO | 15.6477 | 15.6477 | 1.0 | 18.08 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76377 | LA CUMBRE | None | SINTETICO | 11.0162 | 11.0162 | 1.0 | 21.87 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76400 | LA UNIÓN | None | SINTETICO | 14.7454 | 14.7454 | 1.0 | 18.11 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76403 | LA VICTORIA | None | SINTETICO | 15.7132 | 15.7132 | 1.0 | 18.08 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76497 | OBANDO | None | SINTETICO | 14.8347 | 14.8347 | 1.0 | 18.1 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76520 | PALMIRA | None | SINTETICO | 13.6238 | 13.6238 | 1.0 | 18.5 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76563 | PRADERA | None | SINTETICO | 15.0283 | 15.0283 | 1.0 | 18.08 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76606 | RESTREPO | None | SINTETICO | 11.7845 | 11.7845 | 1.0 | 20.4 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76616 | RIOFRÍO | None | SINTETICO | 11.7438 | 11.7438 | 1.0 | 20.47 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76622 | ROLDANILLO | None | SINTETICO | 11.6187 | 11.6187 | 1.0 | 20.68 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76670 | SAN PEDRO | None | SINTETICO | 13.2922 | 13.2922 | 1.0 | 18.71 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76736 | SEVILLA | None | SINTETICO | 11.5463 | 11.5463 | 1.0 | 20.81 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76823 | TORO | None | SINTETICO | 18.7009 | 18.7009 | 1.0 | 18.93 | Aceptable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 2.3674 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76828 | TRUJILLO | None | SINTETICO | 11.2564 | 11.2564 | 1.0 | 21.36 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76834 | TULUÁ | None | SINTETICO | 13.9047 | 13.9047 | 1.0 | 18.36 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76845 | ULLOA | None | SINTETICO | 12.8237 | 12.8237 | 1.0 | 19.09 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76863 | VERSALLES | None | SINTETICO | 11.9244 | 11.9244 | 1.0 | 20.19 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76869 | VIJES | None | SINTETICO | 9.97 | 9.97 | 1.0 | 24.75 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76890 | YOTOCO | None | SINTETICO | 11.05 | 11.05 | 1.0 | 21.8 | No confiable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | No confiable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76892 | YUMBO | 76001 | SINTETICO_BENCHMARK | 13.6985 | 16.9589 | 0.807749 | 30.03 | No confiable | CONDICIONAL_AL_MODELO | FUERA_DEL_RANGO | No confiable · condicional al modelo · extrapolado (fuera del rango) | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | True | 0.6253 |
| MUNICIPIO | 2018 | 12 | VALLE DEL CAUCA | 76895 | ZARZAL | None | SINTETICO | 14.399 | 14.399 | 1.0 | 18.19 | Aceptable | CONDICIONAL_AL_MODELO | DENTRO_DEL_RANGO | Aceptable · condicional al modelo | FH_CLASICO_BENCHMARK_NO_ESPACIAL | PRELIMINAR | False | False | 0.0 |


## Celda 28



## Celda 29


**Salida:**

| EXTRAPOLA | ESTADO_EXTRAPOLACION | CONFIABILIDAD | N_MUNICIPIOS | CV_MEDIO_PCT | TASA_MEDIA_PCT | TASA_MAX_PCT | RMSE_MEDIO | APORTE_MEDIO_PP | APORTE_MAX_PP |
|---|---|---|---|---|---|---|---|---|---|
| False | DENTRO_DEL_RANGO | Aceptable | 33 | 18.48 | 14.36 | 16.19 | 2.65 | 0.0 | 0.0 |
| False | DENTRO_DEL_RANGO | No confiable | 29 | 21.79 | 11.13 | 11.96 | 2.42 | 0.0 | 0.0 |
| True | FUERA_DEL_RANGO | Aceptable | 15 | 18.85 | 18.36 | 20.96 | 3.47 | 2.03 | 4.63 |
| True | FUERA_DEL_RANGO | No confiable | 6 | 25.22 | 18.37 | 31.17 | 4.42 | 5.81 | 14.84 |
```
Etiquetas publicadas en la tabla final (CALIDAD_REPORTADA):

```
| NIVEL | BASE_CV | CALIDAD_REPORTADA | N |
|---|---|---|---|
| DOMINIO | EBLUP | Confiable | 23 |
| MUNICIPIO | CONDICIONAL_AL_MODELO | Aceptable · condicional al modelo | 32 |
| MUNICIPIO | CONDICIONAL_AL_MODELO | Aceptable · condicional al modelo · extrapolado (fuera del rango) | 14 |
| MUNICIPIO | CONDICIONAL_AL_MODELO | No confiable · condicional al modelo | 30 |
| MUNICIPIO | CONDICIONAL_AL_MODELO | No confiable · condicional al modelo · extrapolado (fuera del rango) | 7 |
```
De 83 municipios, 21 tienen una predicción extrapolada y 62 quedan dentro del rango de los dominios.
El CV de todo municipio es condicional al modelo base: supone que la relación estimada con los dominios también vale en el municipio (Morales et al., p. 441), y no incluye la incertidumbre por selección del modelo, mala especificación ni extrapolación. Por eso CALIDAD_REPORTADA dice «condicional al modelo» en todos.
15 de 21 municipios extrapolados quedan como «Confiable» o «Aceptable» por su CV; su etiqueta agrega «extrapolado» para que esa categoría no se lea como una validación empírica.
Extrapolados frente a dentro del rango: CV medio 20.7 % vs 20.0 %, RMSE medio 3.74 vs 2.54 pp (1.5 veces) y tasa predicha media 18.4 % vs 12.8 % (1.4 veces).
El error crece más que el CV porque el CV divide el error por la tasa predicha, que también sube cuando el municipio extrapola: un CV parecido no significa una estimación igual de buena.
En los extrapolados, la parte de la predicción que viene de fuera del rango es en promedio 3.1 pp (máximo 14.8 pp); ver la celda 10a.

```


## Celda 30



## Celda 31


**Salida:**

```
NIVEL 1 — dominios → «Total 23 ciudades y A.M.» (pesos: PEA expandida)

```
| TERRITORIO | N_UNIDADES | REFERENCIA | AGREGADO_ANTES | DIF_ANTES_PP | AGREGADO_DESPUES | DIF_DESPUES_PP | LAMBDA | CONSISTENTE | RAZONES_CONSERVADAS | EN_RANGO | MIEMBROS_COMPLETOS | OK |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Total 23 ciudades y A.M. | 23 | 10.834004965581581 | 10.836765032304132 | 0.0027600667225513575 | 10.834004965581585 | 3.552713678800501e-15 | 0.9997453052904328 | True | True | True | True | True |
| TERRITORIO | CODIGO_DOMINIO | NOMBRE_DOMINIO | PESO | DIRECTA | EBLUP | EBLUP_BENCHMARK | DIF_EBLUP_DIRECTA_PP | CAMBIO_AJUSTE_PP |
|---|---|---|---|---|---|---|---|---|
| Total 23 ciudades y A.M. | 05001 | Medellín A.M. | 2040764.1497 | 11.8378 | 11.8337 | 11.8307 | -0.0041 | -0.003 |
| Total 23 ciudades y A.M. | 08001 | Barranquilla A.M. | 938958.6917 | 8.1479 | 8.1743 | 8.1723 | 0.0265 | -0.0021 |
| Total 23 ciudades y A.M. | 11001 | Bogotá | 4333474.2155 | 10.3699 | 10.3723 | 10.3696 | 0.0024 | -0.0026 |
| Total 23 ciudades y A.M. | 13001 | Cartagena | 403260.5793 | 8.3485 | 8.3858 | 8.3837 | 0.0374 | -0.0021 |
| Total 23 ciudades y A.M. | 15001 | Tunja | 83439.4308 | 11.3139 | 11.2815 | 11.2786 | -0.0324 | -0.0029 |
| Total 23 ciudades y A.M. | 17001 | Manizales A.M. | 236030.6858 | 11.2371 | 11.2317 | 11.2288 | -0.0054 | -0.0029 |
| Total 23 ciudades y A.M. | 18001 | Florencia | 69607.8137 | 12.9401 | 12.9005 | 12.8972 | -0.0396 | -0.0033 |
| Total 23 ciudades y A.M. | 19001 | Popayán | 132019.3509 | 10.6775 | 10.686 | 10.6832 | 0.0084 | -0.0027 |
| Total 23 ciudades y A.M. | 20001 | Valledupar | 205750.7313 | 14.4504 | 14.3795 | 14.3758 | -0.071 | -0.0037 |
| Total 23 ciudades y A.M. | 23001 | Montería | 202389.9026 | 9.4675 | 9.4871 | 9.4847 | 0.0197 | -0.0024 |
| Total 23 ciudades y A.M. | 27001 | Quibdó | 49680.6838 | 17.8131 | 17.7631 | 17.7586 | -0.05 | -0.0045 |
| Total 23 ciudades y A.M. | 41001 | Neiva | 166938.4472 | 11.5337 | 11.533 | 11.5301 | -0.0007 | -0.0029 |
| Total 23 ciudades y A.M. | 44001 | Riohacha | 58310.39 | 13.8839 | 13.8587 | 13.8552 | -0.0252 | -0.0035 |
| Total 23 ciudades y A.M. | 47001 | Santa Marta | 219826.1383 | 8.3164 | 8.3452 | 8.343 | 0.0288 | -0.0021 |
| Total 23 ciudades y A.M. | 50001 | Villavicencio | 262642.1355 | 11.8733 | 11.865 | 11.862 | -0.0083 | -0.003 |
| Total 23 ciudades y A.M. | 52001 | Pasto | 167862.9085 | 8.8159 | 8.8392 | 8.8369 | 0.0233 | -0.0023 |
| Total 23 ciudades y A.M. | 54001 | Cúcuta A.M. | 446606.4079 | 15.9834 | 15.8847 | 15.8806 | -0.0987 | -0.004 |
| Total 23 ciudades y A.M. | 63001 | Armenia | 158573.681 | 15.4915 | 15.4223 | 15.4184 | -0.0692 | -0.0039 |
| Total 23 ciudades y A.M. | 66001 | Pereira A.M. | 340084.0804 | 8.8666 | 8.901 | 8.8987 | 0.0344 | -0.0023 |
| Total 23 ciudades y A.M. | 68001 | Bucaramanga A.M. | 637258.9812 | 8.7391 | 8.7622 | 8.76 | 0.0231 | -0.0022 |
| Total 23 ciudades y A.M. | 70001 | Sincelejo | 135144.6494 | 9.6057 | 9.6171 | 9.6147 | 0.0115 | -0.0024 |
| Total 23 ciudades y A.M. | 73001 | Ibagué | 273059.2484 | 13.9941 | 13.9313 | 13.9277 | -0.0629 | -0.0035 |
| Total 23 ciudades y A.M. | 76001 | Cali A.M. | 1229927.9859 | 11.6514 | 11.692 | 11.689 | 0.0406 | -0.003 |
```

NIVEL 2 — municipios → su dominio A.M. (pesos: población de 15 años y más)

```
| TERRITORIO | N_UNIDADES | REFERENCIA | AGREGADO_ANTES | DIF_ANTES_PP | AGREGADO_DESPUES | DIF_DESPUES_PP | LAMBDA | CONSISTENTE | RAZONES_CONSERVADAS | EN_RANGO | MIEMBROS_COMPLETOS | OK |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 76001 | 2 | 11.689006072872079 | 14.471079002722707 | 2.782072929850628 | 11.68900607287208 | 1.7763568394002505e-15 | 0.8077494477552651 | True | True | True | True | True |
```

Tabla final, nivel 1: agregado 10.8340 vs referencia 10.8340 → PASS
Tabla final, nivel 2 (76001): agregado 11.6890 vs dominio 11.6890 → PASS

```


## Celda 32


**Salida:**

```
Tablas a escribir: 17
Tabla escrita: tesis.modelo.fh_diagnosticos_variantes (4 filas)
Tabla escrita: tesis.modelo.fh_cook (4 filas)
Tabla escrita: tesis.modelo.fh_seleccion_modelo (4 filas)
Tabla escrita: tesis.modelo.fh_coeficientes (2 filas)
Tabla escrita: tesis.modelo.fh_estabilidad_coeficientes (2 filas)
Tabla escrita: tesis.modelo.fay_herriot_resultados (23 filas)
Tabla escrita: tesis.modelo.fh_rangos_covariables (1 filas)
Tabla escrita: tesis.modelo.fh_sensibilidad_extrapolacion (83 filas)
Tabla escrita: tesis.modelo.fh_loao_coeficientes (46 filas)
Tabla escrita: tesis.modelo.fh_loao_predicciones (2415 filas)
Tabla escrita: tesis.modelo.fh_loao_dominios (23 filas)
Tabla escrita: tesis.modelo.fh_validacion_cruzada (69 filas)
Tabla escrita: tesis.modelo.fh_validacion_cruzada_metricas (3 filas)
Tabla escrita: tesis.modelo.fh_validacion_cruzada_seleccion (23 filas)
Tabla escrita: tesis.modelo.fh_validacion_cruzada_frecuencia (5 filas)
Tabla escrita: tesis.modelo.fay_herriot_prediccion_sintetica (83 filas)
Tabla escrita: tesis.modelo.fay_herriot_estimaciones_finales (106 filas)

```
