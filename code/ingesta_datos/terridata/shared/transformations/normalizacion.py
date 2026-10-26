from pyspark.sql.functions import col

# Lista de expresiones de columna para la capa bronce.
# R-52: ya no se agregan DEPARTAMENTO_NORMALIZADO ni ENTIDAD_NORMALIZADO (sin tildes, en
# mayúsculas): ninguna etapa las leía (preprocesamiento solo las excluía) y la normalización
# ignoraba ñ y ü. Los cruces se hacen por CODIGO_DEPARTAMENTO / CODIGO_ENTIDAD.
CAMPOS_BRONCE = [
    # --- GEOGRAFÍA ---
    col("CODIGO_DEPARTAMENTO"),
    col("DEPARTAMENTO"),
    col("CODIGO_ENTIDAD"),
    col("ENTIDAD"),
    # --- CLASIFICACIÓN DEL INDICADOR ---
    col("DIMENSION"),
    col("SUBCATEGORIA"),
    col("INDICADOR"),
    col("CODIGO_INDICADOR"),
    # --- VALORES ---
    col("DATO_NUMERICO"),
    col("DATO_CUALITATIVO"),
    # --- TEMPORALIDAD ---
    col("ANO"),
    col("MES"),
    # --- METADATA ---
    col("FUENTE"),
    col("UNIDAD_MEDIDA"),
]
