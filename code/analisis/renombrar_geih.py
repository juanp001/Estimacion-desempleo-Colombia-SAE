# Databricks notebook source
# MAGIC %md
# MAGIC # Renombrador de archivos GEIH — DANE
# MAGIC
# MAGIC Convierte los nombres de archivos de la GEIH al formato estándar:
# MAGIC
# MAGIC ```
# MAGIC Cabecera - Fuerza de trabajo.csv                      ->  cabecera_fuerza_de_trabajo_01_2018.csv
# MAGIC Cabecera - Caracteristicas generales (Personas).csv   ->  cabecera_caracteristicas_generales_01_2018.csv
# MAGIC Cabecera - Desocupados.csv                            ->  cabecera_no_ocupados_01_2018.csv
# MAGIC ```
# MAGIC
# MAGIC **Estructura esperada de carpetas:**
# MAGIC ```
# MAGIC GEIH/
# MAGIC └── 2018/
# MAGIC     ├── Enero/
# MAGIC     ├── Febrero/
# MAGIC     └── ...
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Celda 1 — Importar librerias

# COMMAND ----------

import os
import re
from pathlib import Path

print('OK: Librerias cargadas.')

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Celda 2 — Parametros de configuracion
# MAGIC
# MAGIC > Edita aqui la ruta base y el anio antes de continuar.

# COMMAND ----------

# --- CONFIGURA AQUI ---
RUTA_BASE = r'./GEIH'   # Carpeta raiz que contiene la subcarpeta del anio
ANO       = '2018'      # Anio a procesar
DRY_RUN   = False        # True = solo simula | False = renombra en disco
# ----------------------

print('Ruta base :', RUTA_BASE)
print('Anio      :', ANO)
print('Modo      :', 'SIMULACION (dry run)' if DRY_RUN else 'ESCRITURA REAL')

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Celda 3 — Mapeo de meses, reglas de limpieza y funcion de normalizacion
# MAGIC
# MAGIC Transformaciones aplicadas en orden:
# MAGIC
# MAGIC 1. **Eliminar parentesis** — `(Personas)`, `(Hogares)`, etc.
# MAGIC 2. **Quitar tildes** — `caracteristicas` queda sin tilde
# MAGIC 3. **Reemplazos de terminos** — `desocupados` pasa a `no_ocupados` (extensible)

# COMMAND ----------

import unicodedata

MESES = {
    'enero':      '01',
    'febrero':    '02',
    'marzo':      '03',
    'abril':      '04',
    'mayo':       '05',
    'junio':      '06',
    'julio':      '07',
    'agosto':     '08',
    'septiembre': '09',
    'octubre':    '10',
    'noviembre':  '11',
    'diciembre':  '12',
}

# Agregar mas reemplazos aqui si es necesario
REEMPLAZOS_TERMINOS = {
    'desocupados': 'no_ocupados',
}


def quitar_tildes(texto):
    """Elimina tildes y diacriticos descomponiendo cada caracter (NFD)
    y descartando las marcas de acento (categoria Mn)."""
    normalizado = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in normalizado if unicodedata.category(c) != 'Mn')


def normalizar_nombre(nombre_sin_ext, mes_num, ano):
    # 1. Eliminar contenido entre parentesis
    nombre = re.sub(r'\s*\(.*?\)', '', nombre_sin_ext).strip()
    # 2. Minusculas
    nombre = nombre.lower()
    # 3. Quitar tildes
    nombre = quitar_tildes(nombre)
    # 4. Reemplazos de terminos
    for original, reemplazo in REEMPLAZOS_TERMINOS.items():
        nombre = re.sub(r'\b' + re.escape(original) + r'\b', reemplazo, nombre)
    # 5. Guiones y espacios a guion bajo
    nombre = re.sub(r'\s*-\s*', '_', nombre)
    nombre = re.sub(r'\s+', '_', nombre)
    # 6. Quitar caracteres no alfanumericos
    nombre = re.sub(r'[^\w]', '', nombre, flags=re.UNICODE)
    # 7. Colapsar guiones bajos multiples
    nombre = re.sub(r'_+', '_', nombre).strip('_')
    # 8. Sufijo mes y anio
    return nombre + '_' + mes_num + '_' + ano


# Prueba rapida
ejemplos = [
    'Cabecera - Fuerza de trabajo',
    'Resto - Fuerza de trabajo',
    'Cabecera - Características generales (Personas)',
    'Resto - Características generales (Personas)',
    'Cabecera - Desocupados',
    'Resto - Desocupados',
]
print('Prueba de normalizacion:')
for e in ejemplos:
    resultado = normalizar_nombre(e, '01', ANO)
    print('  Entrada :', e)
    print('  Salida  :', resultado)
    print()


# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Celda 4 — Verificar estructura de carpetas

# COMMAND ----------

ruta_ano   = Path(RUTA_BASE) / ANO
directorio = ruta_ano if ruta_ano.is_dir() else Path(RUTA_BASE)

if not directorio.is_dir():
    raise FileNotFoundError('No se encontro el directorio: ' + str(directorio))

subcarpetas = sorted([d for d in directorio.iterdir() if d.is_dir()])

print('Directorio:', directorio.resolve())
print('Subcarpetas encontradas:', len(subcarpetas))
print()

for sub in subcarpetas:
    mes_num  = MESES.get(sub.name.strip().lower())
    n_arch   = len(list(sub.iterdir()))
    estado   = ('-> mes ' + mes_num) if mes_num else 'NO RECONOCIDA'
    print(' ', sub.name.ljust(20), estado, '  (' + str(n_arch) + ' archivos)')

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Celda 5 — Generar plan de renombramiento
# MAGIC
# MAGIC Construye la lista completa de cambios **sin tocar ningun archivo** todavia.

# COMMAND ----------

plan = []

for subcarpeta in sorted(directorio.iterdir()):
    if not subcarpeta.is_dir():
        continue

    mes_clave = subcarpeta.name.strip().lower()
    mes_num   = MESES.get(mes_clave)

    if mes_num is None:
        m = re.match(r'^0?(\d{1,2})$', mes_clave)
        mes_num = m.group(1).zfill(2) if m else None

    if mes_num is None:
        print('[AVISO] Subcarpeta no reconocida como mes, omitida:', subcarpeta.name)
        continue

    for archivo in sorted(subcarpeta.iterdir()):
        if not archivo.is_file():
            continue

        nuevo_nombre = normalizar_nombre(archivo.stem, mes_num, ANO) + archivo.suffix
        ruta_nueva   = subcarpeta / nuevo_nombre

        if archivo.name == nuevo_nombre:
            estado = 'sin_cambio'
        elif ruta_nueva.exists():
            estado = 'ya_existe'
        else:
            estado = 'renombrar'

        plan.append({
            'mes':          subcarpeta.name,
            'mes_num':      mes_num,
            'nombre_orig':  archivo.name,
            'nombre_nuevo': nuevo_nombre,
            'ruta_orig':    archivo,
            'ruta_nueva':   ruta_nueva,
            'estado':       estado,
        })

total      = len(plan)
a_cambiar  = sum(1 for r in plan if r['estado'] == 'renombrar')
sin_cambio = sum(1 for r in plan if r['estado'] == 'sin_cambio')
conflictos = sum(1 for r in plan if r['estado'] == 'ya_existe')

print('Total de archivos analizados :', total)
print('  A renombrar                :', a_cambiar)
print('  Sin cambio                 :', sin_cambio)
print('  Conflictos (ya existe)     :', conflictos)

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Celda 6 — Previsualizar cambios

# COMMAND ----------

mes_actual = None

for r in plan:
    if r['estado'] != 'renombrar':
        continue
    if r['mes'] != mes_actual:
        mes_actual = r['mes']
        print()
        print('Carpeta:', mes_actual)
    print('  ', r['nombre_orig'])
    print('   ->', r['nombre_nuevo'])

if a_cambiar == 0:
    print('No hay archivos pendientes de renombrar.')

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Celda 7 — Ejecutar renombramiento
# MAGIC
# MAGIC > Esta celda **modifica archivos en disco**. Solo actua si `DRY_RUN = False` en la Celda 2.  
# MAGIC > Para aplicar los cambios, cambia `DRY_RUN = False` y vuelve a correr desde la Celda 2.

# COMMAND ----------

if DRY_RUN:
    print('Modo SIMULACION activo: ningun archivo fue modificado.')
    print('Cambia DRY_RUN = False en la Celda 2 para aplicar los cambios.')
else:
    ok     = 0
    fallos = 0

    for r in plan:
        if r['estado'] != 'renombrar':
            continue
        try:
            os.rename(r['ruta_orig'], r['ruta_nueva'])
            print('OK:', r['nombre_orig'], '->', r['nombre_nuevo'])
            ok += 1
        except OSError as e:
            print('ERROR al renombrar', r['nombre_orig'], ':', e)
            fallos += 1

    print()
    print('Renombrados exitosamente :', ok)
    if fallos:
        print('Errores                  :', fallos)