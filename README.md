# Estimación de Desempleo en Colombia — SAE (Small Area Estimation)

Repositorio de tesis de maestría. Implementa un modelo **Fay-Herriot** para estimar la tasa de desempleo a nivel municipal en Colombia, combinando microdatos de la GEIH con información auxiliar de TerriData sobre una plataforma **Databricks** (Unity Catalog, PySpark).

---

## Arquitectura de datos

El pipeline sigue el modelo medallón **Bronce → Plata → Oro**:

| Capa | Descripción |
|------|-------------|
| **Bronce** | Ingesta raw desde volúmenes de Unity Catalog (CSV / Parquet) |
| **Plata** | Limpieza, normalización y estandarización de campos |
| **Oro** | Tablas analíticas desnormalizadas, listas para modelado |

---

## Estructura del repositorio

```
code/
├── ingesta_datos/
│   ├── geih/
│   │   ├── geih_bronce.py          # Carga de módulos GEIH (fuerza de trabajo, ocupados, no ocupados, etc.)
│   │   ├── geih_plata.py           # Consolidación y estandarización (marcos antiguo/nuevo, secciones geográficas)
│   │   └── geih_oro.py             # Tabla analítica final: mercado laboral con todos los indicadores laborales
│   ├── terridata/
│   │   ├── terridata_bronce.py     # Ingesta de TerriData (DNP) con normalización de texto
│   │   ├── terridata_plata.py      # Pivote formato largo → ancho (~1.582 indicadores como columnas)
│   │   └── terridata_oro.py        # Filtro de calidad: variables con ≥70% de completitud
│   ├── censo_nal/
│   │   └── censo_bronce.py         # Ingesta del Censo Nacional (personas, hogares, viviendas, fallecidos)
│   └── dimensiones/
│       ├── dim_divipola.py         # Dimensión geográfica completa (~1.100 municipios, con coordenadas)
│       ├── dim_geih_divipola.py    # Subconjunto DIVIPOLA para las 32 ciudades cubiertas por la GEIH
│       └── dim_tiempo.py           # Dimensión de tiempo (2000–2050, granularidad diaria)
└── modelo/
│   ├── estimacion_directa.py       # Estimador Hájek con bootstrap (600 réplicas) por municipio
│   └── adicion_covariables.py      # Join entre estimaciones directas y covariables de TerriData
└── analisis/
    ├── Metodologia Selecicon covariables Ver 2.0.py  # Marco teórico comparativo de metodologías SAE
    └── Análisis exploratorio.py    # EDA sobre las 16 covariables con respaldo en literatura
```

---

## Flujo metodológico

```
GEIH (microdatos)
    └─► Bronce → Plata → Oro (mercado_laboral)
            └─► estimacion_directa.py
                    └─► Tasa de desempleo municipal + SE bootstrap
                            └─► adicion_covariables.py
                                    ┌─► TerriData Plata (~1.582 indicadores)
                                    └─► tasa_desempleo_covariables

tasa_desempleo_covariables
    └─► Selección de covariables (PCA + Stepwise AICc)
            └─► 9 componentes principales ortogonales
                    └─► Modelo Fay-Herriot
```

### Selección de covariables (resumen)

1. **Filtro de completitud**: se retienen variables sin NAs en los 23 dominios (1.582 → 530).
2. **Filtro de varianza**: se eliminan variables constantes (530 → 523).
3. **PCA por bloques temáticos**: se aplica PCA independiente por cada dimensión de TerriData; se retienen componentes con eigenvalue > 1 o que acumulen ≥ 80 % de varianza (523 → 59 componentes).
4. **Stepwise AICc**: selección bi-direccional optimizada para muestras pequeñas (n = 23) → modelo final con **9 componentes**, R² ajustado = 0.90.

---

## Fuentes de datos

| Fuente | Descripción |
|--------|-------------|
| **GEIH** (DANE) | Gran Encuesta Integrada de Hogares — microdatos mensuales de mercado laboral |
| **TerriData** (DNP) | +1.000 indicadores socioeconómicos territoriales por municipio |
| **Censo Nacional** (DANE) | Módulos de personas, hogares y viviendas |
| **DIVIPOLA** (DANE) | Codificación político-administrativa de Colombia |

---

## Plataforma

- **Databricks** sobre Azure (Unity Catalog)
- **PySpark** para procesamiento distribuido
- **Python** (pandas, scikit-learn, statsmodels) para análisis estadístico
- Catálogo: `tesis` — esquemas: `geih_bronce`, `geih_plata`, `geih_oro`, `terridata`, `censo_nal`, `modelo`, `dim`
