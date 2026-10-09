# Componente espacial del Fay-Herriot (SEBLUP)

Documento de método, código y resultados del componente espacial del modelo de área pequeña.
Código: `code/modelo/fay_herriot_espacial.py` (orquestador) y `code/modelo/shared/`
(`matriz_proximidad.py`, `fay_herriot_espacial.py`, `figuras_espacial.py`, parámetros en `config.py`).
Tablas de salida: `tesis.modelo.fhe_*`. Figuras: `docs/img/fhe_*.png`.

## 1. Conclusión

Con los datos disponibles **no hay evidencia de dependencia espacial** en los efectos aleatorios del
Fay-Herriot, y el componente espacial **no mejora** la predicción en municipios sin encuesta. El
modelo recomendado sigue siendo el **Fay-Herriot clásico**; el SEBLUP queda como análisis de
sensibilidad, que es un resultado legítimo de la tesis y no un fallo de implementación:

| Evidencia | Resultado |
|---|---|
| I de Moran de los residuos del clásico (4 escenarios de W) | −0.04 a −0.10, p entre 0.49 y 0.97: ninguno significativo |
| ρ̂ del SEBLUP (estructura completa) | −0.01 a −0.12 en los escenarios con ρ̂ interior; ninguno con ΔAIC > 2 a favor del espacial |
| Razón de verosimilitudes ρ = 0 | p entre 0.45 y 0.68 (completa) |
| Perfil de verosimilitud de ρ | Plano: la ganancia máxima frente a ρ = 0 es ≤ 0.10 unidades de log-verosimilitud |
| Validación dejar-un-dominio-fuera (RMSE) | Clásico 2.215; espacial con efecto 2.31-2.35 (peor en 3 de 4 escenarios, empate en el cuarto) |
| Efecto espacial predicho en los 82 objetivos | Entre −0.04 y +0.07 puntos porcentuales |

El hallazgo que más pesa sobre la calidad de las estimaciones no es espacial: **73 de los 82
municipios objetivo extrapolan** (sus covariables quedan fuera de la nube de la muestra) y 45 de 82
tienen CV ≥ 20 % (ver §6).

## 2. Qué es el modelo

Fay-Herriot clásico: `y_d = x_d'β + u_d + e_d`, con `u_d` independientes, `Var(u_d) = σ²_u` y
`Var(e_d) = D_d` conocida (la varianza bootstrap de la estimación directa).

Fay-Herriot espacial (Morales et al., 2021, §18.2, pp. 490-494): los efectos siguen un proceso
autorregresivo simultáneo, `u = ρWu + v`, con `v ~ N(0, σ²_u I)`. Entonces
`Cov(u) = σ²_u[(I − ρW)'(I − ρW)]⁻¹` y `Cov(y) = V = Cov(u) + diag(D)`. W es una matriz de
proximidad estandarizada por filas (cada fila suma 1), de modo que ρ ∈ (−1, 1). Con ρ = 0 se
recupera el modelo clásico, por lo que **la pregunta es si los datos justifican ρ ≠ 0**.

- **Estimación**: (σ²_u, ρ) por REML numérico (L-BFGS-B con tres puntos de partida, ρ ∈ {0, 0.5, 0.9});
  β por mínimos cuadrados generalizados; AIC con la verosimilitud ML y `p + 2` parámetros (coeficientes,
  σ²_u y ρ).
- **EBLUP**: `μ̂ = Xβ̂ + G V⁻¹ (y − Xβ̂)` (p. 491, ec. 18.9).
- **MSE**: bootstrap paramétrico (§18.2.3, p. 494). En cada réplica se simula `u*` y `e*`, se re-estiman
  σ²_u y ρ y se acumula el error frente a la verdad simulada; así el MSE incluye la incertidumbre de ρ̂.
  Se usaron 500 réplicas (las 500 convergieron).

## 3. Por qué la contigüidad no sirve aquí, y qué se hizo

Un hallazgo de la exploración (`fhe_vecindad`): los 23 dominios con encuesta son capitales o áreas
metropolitanas dispersas por el país, y los municipios objetivo de Cauca y Valle no son contiguos a ellos.

- Entre los dominios con encuesta, el vecino más cercano está a 30-158 km (mediana 106 km; 12 de 23 a más de 100 km).
- Los municipios objetivo tienen por vecinos contiguos a otros objetivos, sin dato.
- Cada objetivo tiene un dominio con encuesta a una mediana de 45 km (Cauca 46, Valle 45); 39 de 41 en
  Cauca y 41 de 41 en Valle están a ≤ 100 km (`fhe_vecindad`).

Decisiones:

1. **ρ se estima solo con los dominios con encuesta**: son los únicos con dato.
2. **W se define sobre todas las unidades** (23 con encuesta + 82 objetivo = 105) en la estructura
   `completa` (Saei y Chambers, 2005; Benedetti et al., 2024, pp. 146-149). La verosimilitud se evalúa
   sobre el bloque de los dominios con encuesta (verosimilitud marginal). Así un municipio sin encuesta
   recibe `x'β̂ + û_r`, con `û_r = G_rs V⁻¹ (y − Xβ̂)` calculado a partir de los dominios cercanos. La
   estructura `muestra` (Petrucci y Salvati, 2006) define W solo entre dominios con encuesta y deja a los
   objetivos con el sintético `x'β̂`.
3. **W por distancia entre centroides** (Haversine), no por contigüidad (Morales et al., p. 491 admite
   ambas). Cuatro escenarios: kNN con k = 3 y 5 (simetrizada) y distancia inversa con potencia 1 y 2.
   Siempre estandarizada por filas.
4. **Coordenada de cada dominio** = la de su municipio capital (`CODIGO_DOMINIO`). Es una simplificación:
   un área metropolitana agrupa varios municipios.
5. **Cali** (76001) aparece en `municipios_sin_encuesta` pero es un dominio con encuesta; se excluye de los
   objetivos (se usa su EBLUP), como en la tabla final del modelo clásico. Quedan 82 objetivos (41 por
   departamento). Yumbo, que pertenece al área metropolitana de Cali, se mantiene como objetivo, igual que
   en el flujo actual.

## 4. Pasos del notebook y qué hace cada pieza

| Paso | Qué hace | Código |
|---|---|---|
| 1 | Carga covariables del benchmark clásico seleccionado (`fh_coeficientes`), dominios, objetivos, coordenadas | notebook |
| 2 | Diagnóstico de vecindad (distancia de cada objetivo al dominio más cercano) | `resumen_vecindad` |
| 3 | Fay-Herriot clásico de referencia | `FayHerriotClasico` (existente) |
| 4 | I de Moran de residuos, por escenario de W | `moran_i`, `proximidad_knn`, `proximidad_inversa` |
| 5 | Ajuste del SEBLUP por escenario y estructura; AIC y LRT | `FayHerriotEspacial` |
| 6 | Perfil de verosimilitud de ρ | `FayHerriotEspacial.perfil_rho` |
| 7 | Validación dejar-un-dominio-fuera | `validacion_dejar_uno_fuera`, `metricas_validacion` |
| 8 | Decisión por criterio explícito | notebook |
| 9 | Predicción en objetivos con MSE bootstrap; marcas de extrapolación | `FayHerriotEspacial` |
| 10 | Escritura de tablas `fhe_*` y figuras `fhe_*` | notebook |

Detalles de implementación:

- `covarianza_sar(W, A, ρ)`: `G = A·M⁻¹M⁻ᵀ` con `M = I − ρW`.
- `FayHerriotEspacial._log_verosimilitud`: ML o REML perfilando β; en la estructura completa V es el bloque
  `G[:n,:n] + diag(D)`.
- `_estimar_theta`: L-BFGS-B sobre `(log σ²_u, ρ)` con `|ρ| ≤ 0.99`.
- `_bootstrap_mse`: simula sobre todas las unidades y devuelve el MSE de los dominios con encuesta, de los
  objetivos con efecto espacial y de los objetivos con sintético.
- `moran_i`: p-valor por 9 999 permutaciones, sin supuestos de normalidad.
- Clase hija de `ModeloAreaPequena`: respeta el contrato (A_hat, beta_hat, mse, cv, aic, …). `gamma_i` no se
  define: en el caso espacial no hay un peso escalar por dominio.

**Validación dejar-un-dominio-fuera**: para cada uno de los 23 dominios se re-estima el modelo sin él, se le
trata como dominio sin encuesta y se predice con (a) el sintético clásico, (b) el sintético del modelo
espacial y (c) el predictor espacial con efecto. El referente es la estimación directa, que tiene ruido
`D_d`; por eso también se reporta el RMSE corregido por ese ruido. Con n = 23 es evidencia modesta.

**Criterio de decisión**: el espacial es preferido solo si `ΔAIC > 2` (AIC clásico − AIC espacial) y la
prueba de razón de verosimilitudes de ρ = 0 tiene p < 0.05. Un escenario con ρ̂ pegado a la cota (|ρ̂| =
0.99) no se usa como referencia: es un artefacto de una verosimilitud plana (le ocurrió a `inversa1`).

## 5. Resultados

Covariables: las del benchmark clásico, `VA_PCT_PRIM + IICA_CONFLICTO` (n = 23, r = 82). Clásico: Â = 4.188,
AIC = 104.916.

### 5.1 I de Moran (`fhe_moran`)

W solo entre los 23 dominios. Residuos del clásico `y − Xβ̂`:

| Escenario | I | Esperado | p |
|---|---|---|---|
| knn3 | −0.094 | −0.045 | 0.745 |
| knn5 | −0.042 | −0.045 | 0.970 |
| inversa1 | −0.078 | −0.045 | 0.494 |
| inversa2 | −0.096 | −0.045 | 0.640 |

La tasa cruda tampoco muestra autocorrelación (p de 0.71 a 0.88). Con n = 23 la potencia es baja: un Moran no
significativo no demuestra independencia, solo que los datos no la contradicen.

### 5.2 SEBLUP frente al clásico (`fhe_comparacion_modelos`)

| Escenario | Estructura | σ̂²_u | ρ̂ | AIC | ΔAIC | p(LRT) |
|---|---|---|---|---|---|---|
| knn3 | completa | 4.145 | −0.084 | 106.72 | −1.81 | 0.66 |
| knn3 | muestra | 3.941 | −0.279 | 105.96 | −1.04 | 0.33 |
| knn5 | completa | 4.184 | −0.012 | 106.75 | −1.83 | 0.68 |
| knn5 | muestra | 4.183 | −0.011 | 106.72 | −1.81 | 0.66 |
| inversa1 | completa | 4.022 | −0.990 (cota) | 106.34 | −1.43 | 0.45 |
| inversa1 | muestra | 3.566 | −0.990 (cota) | 104.87 | +0.04 | 0.15 |
| inversa2 | completa | 4.163 | −0.121 | 106.72 | −1.80 | 0.65 |
| inversa2 | muestra | 3.904 | −0.354 | 105.75 | −0.84 | 0.28 |

ΔAIC = AIC clásico − AIC espacial; positivo favorece al espacial. En ningún caso supera 2 y el máximo es +0.04.
Las dos filas con ρ̂ en −0.99 son artefactos de verosimilitud plana. Todos los ρ̂ son negativos o ≈ 0, el
signo contrario al esperado si el desempleo se pareciera entre vecinos. La referencia que eligió el notebook
es `inversa2` con estructura completa (menor AIC entre los ρ̂ interiores).

### 5.3 Perfil de ρ (`fhe_perfil_rho`, `docs/img/fhe_perfil_rho.png`)

| Escenario | ρ del máximo | Ganancia máxima vs ρ = 0 | Rango de ρ con caída ≤ 1.92 |
|---|---|---|---|
| knn3 | −0.1 | 0.021 | −0.9 a 0.55 |
| knn5 | 0.0 | 0.000 | −0.9 a 0.75 |
| inversa1 | −0.9 | 0.103 | −0.9 a 0.95 |
| inversa2 | −0.1 | 0.008 | −0.9 a 0.95 |

Las curvas son prácticamente planas: **ρ no está identificado**. El intervalo de verosimilitud perfilada
cubre casi todo el rango y llega al límite inferior de la rejilla (−0.9). Con 23 dominios dispersos los datos
no informan sobre la autocorrelación espacial.

![Perfil de ρ](img/fhe_perfil_rho.png)

### 5.4 Validación dejar-un-dominio-fuera (`fhe_validacion_cruzada_metricas`)

Estructura completa:

| Escenario | RMSE clásico | RMSE sintético espacial | RMSE espacial con efecto |
|---|---|---|---|
| knn3 | 2.215 | 2.247 | 2.330 |
| knn5 | 2.215 | 2.225 | 2.312 |
| inversa1 | 2.215 | 2.220 | 2.215 |
| inversa2 | 2.215 | 2.245 | 2.348 |

El clásico predice igual o mejor que el espacial en los cuatro escenarios. Sesgos medios ≤ 0.09 pp. El RMSE
corregido por el ruido de la estimación directa lleva a la misma conclusión (clásico 2.136; espacial con
efecto 2.135-2.274).

![Validación](img/fhe_validacion.png)

### 5.5 Predicción en los 82 municipios objetivo (`fhe_prediccion_objetivo`)

Escenario de referencia `inversa2` (ρ̂ = −0.121, σ̂²_u = 4.163, 500 de 500 réplicas válidas).

| Indicador | Valor |
|---|---|
| Tasa predicha (clásico): mínimo / mediana / máximo | 10.75 / 21.47 / 68.68 % |
| Efecto espacial `û_r` | entre −0.036 y +0.070 pp |
| Diferencia absoluta espacial − clásico: media / máxima | 0.208 / 0.587 pp |
| CV mediano: clásico / sintético espacial / espacial con efecto | 20.5 / 20.4 / 20.1 % |
| Recomendado | CLÁSICO |

Los efectos espaciales son prácticamente nulos, y por eso las dos predicciones son casi idénticas y los mapas
son visualmente indistinguibles.

![Mapa espacial](img/fhe_mapa_espacial.png)
![Mapa clásico](img/fhe_mapa_clasico.png)

## 6. Advertencias que no son espaciales

- **Extrapolación**: 73 de 82 municipios objetivo tienen `x'Cov(β̂)x` mayor que el máximo de la muestra
  (`EXTRAPOLA = true`). El coeficiente de `IICA_CONFLICTO` (≈ 66) multiplica un indicador que en varios
  municipios objetivo toma valores muy por encima de los de las 23 ciudades, lo que explica una mediana
  predicha de 21.5 % frente a tasas directas de 7 a 17 %, y un máximo de 68.7 %. Conviene revisar esas
  predicciones antes de interpretarlas.
- **Confiabilidad**: con el predictor recomendado (clásico), 37 municipios son aceptables (CV 5-20 %) y 45 no
  confiables (CV ≥ 20 %); ninguno es confiable.
- **Significancia**: `VA_PCT_PRIM` tiene p ≈ 0.057-0.074 según el modelo; el benchmark clásico ya lo admitía por
  la regla de respaldo, no por significancia.

## 7. Limitaciones

- n = 23 dominios: potencia baja y ρ sin identificar. Que no aparezca dependencia espacial no prueba que no
  exista.
- Un dominio metropolitano se representa por una sola coordenada.
- La contigüidad real (geometrías del Marco Geoestadístico Nacional) no se probó: el proyecto solo tiene
  centroides. Con contigüidad el resultado probablemente sea peor (más islas), pero no está verificado.
- Las predicciones comparten covariables con muy pocos puntos de apoyo (§6).
- Los efectos espaciales en los objetivos dependen de que ρ̂ esté bien estimado; con perfil plano, no lo está.

## 8. Cómo reproducir

```bash
databricks bundle deploy -t dev
databricks bundle run modelo -t dev
```

El job `modelo` ejecuta `fay_herriot` y luego `fay_herriot_espacial` (tarea agregada a `dab/resources/modelo.yml`).
El notebook lee `fh_coeficientes` (benchmark clásico), por lo que debe correr después de `fay_herriot.py`. Escribe
`tesis.modelo.fhe_*` con `overwrite` y las figuras `fhe_*.png` en `/Volumes/tesis/preprocesamiento/figuras_eda`.
Parámetros (escenarios de W, `RHO_LIMITE`, permutaciones, réplicas, semilla, `ALFA_LRT`) en
`code/modelo/shared/config.py`.

## 9. Referencias

- Morales, Esteban, Pérez y Hobza (2021), *A Course on Small Area Estimation and Mixed Models*, cap. 18
  (§18.2, pp. 490-494) y §16.
- Petrucci y Salvati (2006), *JABES* 11(2); Pratesi y Salvati (2008), *Stat. Methods & Applications* 17:113-141.
- Benedetti et al. (2024), *Int. Statistical Review*: verosimilitud marginal para áreas fuera de muestra (pp. 146-149).
- Saei y Chambers (2005), citado en Benedetti et al. (2024).

Nota: las páginas del libro y de Benedetti se verificaron con el texto de los PDF indexados; la consulta
semántica no estuvo disponible durante la sesión (error 402 de la API de HuggingFace), así que solo se
citan páginas leídas directamente.
