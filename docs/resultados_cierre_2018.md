# Resultados del cierre 2018 (corrida vigente)

Cifras de la corrida de los jobs sobre la ventana **Ene-Dic 2018** (23 dominios con encuesta y 83 municipios
objetivo). Se movieron aquí desde `CLAUDE.md` (R-49), que conserva solo las reglas. Si cambian el período, la
selección o el modelo, estas cifras se regeneran con las tablas de `tesis.*` (son las fuentes de verdad).

## GEIH: reconciliación (G7-B5, `geih_oro.py`)
2018: 0 violaciones en los 12 meses y 0 llaves sin pareja o duplicadas en todos los módulos.

## Benchmark clásico (`modelo/fay_herriot.py`, R-05 y R-04)
Se cumple la regla de selección: EC3 = `TASA_HOMICIDIOS` (p = 0.006) frente a EC2 = `COB_ACUEDUCTO`
(ΔAIC = 0.92); EC1 (las dos) no cumple; EC0 (solo intercepto) queda en AIC 114.04 (ΔAIC = 5.14), fuera de la
zona de soporte similar (RMSE_LOAO: EC3 2.52, EC0 2.77).

## Validación predictiva dejar-un-dominio-fuera (G7-B19, R-04)
RMSE 2.52 (covariables fijas), 3.43 (procedimiento completo) y 2.77 (nulo), habilidad −0.54; el benchmark se
reproduce en 14 de 23 iteraciones, con 6 conjuntos distintos y 4 iteraciones sin covariables.

## Sensibilidad de la varianza de muestreo (`modelo/sensibilidad_varianza.py`, G7-B3, R-65)
ψ_viviendas/ψ_personas mediana 1.08 (1.00–1.17); bootstrap/Taylor 0.94–1.05; GVF R² 0.97 (A) y 0.976 (B,
pendientes ≈ +1 y −1 = forma binomial, deff implícito ≈ 1.2). En los 9 escenarios (corrida del bloque 06) el
ganador (`TASA_HOMICIDIOS`) y su significancia no cambian, Â/ψ̄ ≥ 19.5, γ ≥ 0.90, el EBLUP cambia ≤ 0.20 pp y la
predicción sintética ≤ 0.13 pp; Taylor y GVF A, ≤ 0.005 pp. Solo con ψ × 3 pasan 4 dominios de confiable a
aceptable.

## Componente espacial (`modelo/fay_herriot_espacial.py`)
Corrida del job `modelo` del 2026-10-27 (run `899936223549833`; 23 dominios, 83 objetivos = 81 nodos + las
subáreas Cali y Yumbo, R-44): **sin evidencia de dependencia espacial**.

- Benchmark clásico `TASA_HOMICIDIOS` (EC3, AIC 108.90, Â 5.529).
- Moran de los residuos del clásico p entre 0.33 y 0.65 y del SEBLUP entre 0.52 y 0.98.
- ρ̂ entre 0.19 y 0.33 (muestra) y entre 0.22 y 0.89 (completa), sin significancia (LRT p ≥ 0.22).
- ΔAIC entre −0.50 y −2.00 (el clásico tiene menor AIC en los 8 casos); perfil de ρ plano (ganancia ≤ 0.94).
- RMSE dejar-un-dominio-fuera: clásico 2.524 frente a 2.346 (`knn3`), 2.590, 2.602 y 2.859 del espacial con
  efecto; solo `knn3` mejora, sin respaldo en la verosimilitud.
- El efecto espacial en los 81 nodos objetivo es pequeño (media absoluta 0.13 pp; −2.84 pp en Cali y Yumbo) y
  21 de 83 objetivos extrapolan.

El modelo recomendado sigue siendo el clásico (benchmark). Detalle, tablas, comparación con el cierre anterior
y limitaciones en [fay_herriot_espacial.md](fay_herriot_espacial.md).
