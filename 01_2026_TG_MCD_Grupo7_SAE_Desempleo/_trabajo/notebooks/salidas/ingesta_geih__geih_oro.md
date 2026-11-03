# ingesta_geih__geih_oro


## Celda 0

```


## Celda 1



## Celda 2



## Celda 3


**Salida:**

```
  MARCO  PER  sum(N_PERSONAS)  sum(N_SIN_FEX)
ANTIGUO 2018           762753               0
  NUEVO 2025           135810               0
PASS: las 898,563 personas tienen FEX_C18 > 0 (2 años, 14 marco-períodos)

```


## Celda 4


**Salida:**

```
                N_LLAVES  N_DUPLICADAS  N_SIN_PAREJA  PCT_SIN_PAREJA
MODULO                                                              
CG_SIN_FEX        762753             0             0           0.000
FEX_SIN_CG        772619             0          9866           1.277
FUERZA_TRABAJO    736992             0             0           0.000
INACTIVOS         238426             0             0           0.000
NO_OCUPADOS        93023             0             0           0.000
OCUPADOS          405543             0             0           0.000
PET_SIN_FT        696589             0             0           0.000
PASS: CG_SIN_FEX sin llaves huérfanas ni duplicadas
AVISO: FEX_SIN_CG tiene llaves huérfanas o duplicadas
    MODULO REFERENCIA  PER  MES  N_LLAVES  N_DUPLICADAS  N_SIN_PAREJA  PCT_SIN_PAREJA
FEX_SIN_CG         CG 2018    1     63424             0           766          1.2077
FEX_SIN_CG         CG 2018    2     64943             0           825          1.2703
FEX_SIN_CG         CG 2018    3     64716             0           812          1.2547
FEX_SIN_CG         CG 2018    4     65892             0           796          1.2080
FEX_SIN_CG         CG 2018    5     66672             0           824          1.2359
FEX_SIN_CG         CG 2018    6     63522             0           839          1.3208
FEX_SIN_CG         CG 2018    7     64739             0           841          1.2991
FEX_SIN_CG         CG 2018    8     65452             0           856          1.3078
FEX_SIN_CG         CG 2018    9     63463             0           916          1.4434
FEX_SIN_CG         CG 2018   10     64051             0           832          1.2990
FEX_SIN_CG         CG 2018   11     64085             0           853          1.3310
FEX_SIN_CG         CG 2018   12     61660             0           706          1.1450
PASS: FUERZA_TRABAJO sin llaves huérfanas ni duplicadas
PASS: INACTIVOS sin llaves huérfanas ni duplicadas
PASS: NO_OCUPADOS sin llaves huérfanas ni duplicadas
PASS: OCUPADOS sin llaves huérfanas ni duplicadas
PASS: PET_SIN_FT sin llaves huérfanas ni duplicadas

```


## Celda 5


**Salida:**

```
PASS: PEA = OC + DS en todos los períodos y dominios
PASS: PET = PEA + PEI en todos los períodos y dominios
PASS: nadie es OC y DS a la vez en todos los períodos y dominios

```
