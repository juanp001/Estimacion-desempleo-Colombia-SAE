# Datos de entrada para reproducir el pipeline

Este directorio empaqueta los **insumos crudos** que el proyecto lee desde los volúmenes de Unity Catalog
(`/Volumes/tesis/...`) en Databricks, para que terceros puedan reproducir la corrida.

- **Fecha de la copia:** 2026-11-25, tomada de los volúmenes del proyecto en Databricks.
- **Contenido:** 9 archivos `.zip` (uno por volumen, todos de menos de 95 MB, sin divisiones), 147 archivos
  originales en total.
- **Integridad:** `MANIFIESTO.csv` lista cada archivo (zip, volumen de destino, ruta relativa, tamaño en bytes y
  SHA-256 calculado sobre los originales descargados). Los hashes se verificaron extrayendo cada zip con `tar -xf`.
- No se incluyen los volúmenes de salida (`preprocesamiento/figuras_eda` y `modelo/figuras`), que se generan al
  correr el pipeline.

## Cómo usarlos

Las rutas internas de cada zip son **relativas a la raíz del volumen**. Para cada zip:

1. Extraerlo en una carpeta vacía (`tar -xf <zip>` o cualquier descompresor).
2. Crear el volumen administrado (ver `databricks.yml` / recursos del bundle) y subir el **contenido** de la
   carpeta a la ruta de destino de la tabla de abajo, conservando la estructura de subcarpetas.

## Zips y volúmenes de destino

| Zip | Volumen de destino | Contenido |
|-----|--------------------|-----------|
| `dim__divipola.zip` | `/Volumes/tesis/dim/divipola` | `DIVIPOLA_codigos_municipios.csv` |
| `geih_bronce__caracteristicas_generales.zip` | `/Volumes/tesis/geih_bronce/caracteristicas_generales` | Módulo características generales: `marco_antiguo/{area,cabecera,resto}/` (2018) y `marco_nuevo/` (ene-feb 2025) |
| `geih_bronce__fuerza_de_trabajo.zip` | `/Volumes/tesis/geih_bronce/fuerza_de_trabajo` | Módulo fuerza de trabajo, mismo esquema `marco_antiguo/` + `marco_nuevo/` |
| `geih_bronce__ocupados.zip` | `/Volumes/tesis/geih_bronce/ocupados` | Módulo ocupados, mismo esquema |
| `geih_bronce__no_ocupados.zip` | `/Volumes/tesis/geih_bronce/no_ocupados` | Módulo no ocupados, mismo esquema |
| `geih_bronce__inactivos.zip` | `/Volumes/tesis/geih_bronce/inactivos` | Módulo inactivos, solo `marco_antiguo/` (el marco nuevo lo integra en fuerza de trabajo) |
| `geih_bronce__fex.zip` | `/Volumes/tesis/geih_bronce/fex` | `Fex_proyeccion_CNPV_2018.csv` (factores de expansión actualizados, DANE) |
| `geih_bronce__datos_publicados.zip` | `/Volumes/tesis/geih_bronce/datos_publicados` | `anexo-mercado-laboral-segun-proyecciones-CNPV2018.xlsx` |
| `terridata__terridata_archivos.zip` | `/Volumes/tesis/terridata/terridata_archivos` | `consolidado/TerriData_consolidado.parquet` |

## Convenciones de nombres de archivo

- **Marco antiguo (2018, marco 2005):** `<seccion>_<modulo>_<MM>_<AAAA>.csv`, con `<seccion>` en
  {`area`, `cabecera`, `resto`}, `<modulo>` en {`caracteristicas_generales`, `fuerza_de_trabajo`, `ocupados`,
  `no_ocupados`, `inactivos`}, `MM` el mes de dos dígitos (01 a 12) y `AAAA` = 2018. Ejemplo:
  `marco_antiguo/cabecera/cabecera_ocupados_03_2018.csv`. Estos nombres los produce
  `code/analisis/renombrar_geih.py` a partir de los nombres originales del DANE. El pipeline solo carga
  `cabecera` y `resto`; `area` se conserva por fidelidad con el volumen original.
- **Marco nuevo (enero y febrero de 2025, marco 2018):** un archivo por módulo y mes, sin partición, con la
  forma `<modulo>_<mes>_2025.csv` (por ejemplo `marco_nuevo/ocupados_enero_2025.csv`). Se respetan los nombres
  tal como están en el volumen (incluida la mayúscula inicial de `Caracteristicas_generales_febrero_2025.csv`).

## Fuentes oficiales

- **GEIH, microdatos:** DANE, Archivo Nacional de Datos, <https://microdatos.dane.gov.co/>. Se usó la GEIH 2018
  (marco 2005) y enero-febrero de 2025 (marco 2018).
- **Anexo de mercado laboral según proyecciones CNPV 2018 (cifras publicadas):** DANE,
  <https://www.dane.gov.co/files/investigaciones/boletines/ech/nuevo-enfoque-conceptual-metodologico-2018/anexo-mercado-laboral-segun-proyecciones-CNPV2018.xlsx>
  (constante `URL_FUENTE_DATOS_PUBLICADOS` en `code/ingesta_datos/geih/shared/config/geih_config.py`).
- **Factores de expansión actualizados (`Fex_proyeccion_CNPV_2018.csv`):** DANE, factores de expansión de la GEIH
  recalibrados con las proyecciones del CNPV 2018.
- **TerriData:** Departamento Nacional de Planeación (DNP), <https://terridata.dnp.gov.co/>. El Parquet
  consolidado (`TerriData_consolidado.parquet`) se produjo **fuera de este repositorio** a partir de la descarga
  masiva de TerriData; aquí se distribuye tal como lo lee `terridata_bronce.py`.
- **DIVIPOLA:** DANE, geoportal,
  <https://geoportal.dane.gov.co/geovisores/territorio/consulta-divipola-division-politico-administrativa-de-colombia/>
  (referencia `DANE_DIVIPOLA` en `01_2026_TG_MCD_Grupo7_SAE_Desempleo/refs.bib`).

## Aviso de uso

Los datos son **públicos** y se redistribuyen aquí únicamente para facilitar la reproducibilidad de la tesis.
Quien los use debe respetar los términos de uso y las condiciones de citación del DANE y del DNP, y citar a las
entidades como fuente. Para versiones actualizadas o autorizadas, acudir a las fuentes oficiales anteriores.
