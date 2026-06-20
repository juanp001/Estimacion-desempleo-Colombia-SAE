from pyspark.sql.functions import col, upper, translate

_TILDES_IN  = "áéíóúÁÉÍÓÚ"
_TILDES_OUT = "aeiouAEIOU"


def _normalizar(columna: str):
    """Elimina tildes y convierte a mayúsculas."""
    return upper(translate(col(columna), _TILDES_IN, _TILDES_OUT))


# Lista de expresiones de columna para la capa bronce.
# Incluye los campos originales y añade DEPARTAMENTO_NORMALIZADO / ENTIDAD_NORMALIZADO.
CAMPOS_BRONCE = [
    # --- GEOGRAFÍA ---
    col("CODIGO_DEPARTAMENTO"),
    col("DEPARTAMENTO"),
    _normalizar("DEPARTAMENTO").alias("DEPARTAMENTO_NORMALIZADO"),
    col("CODIGO_ENTIDAD"),
    col("ENTIDAD"),
    _normalizar("ENTIDAD").alias("ENTIDAD_NORMALIZADO"),

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
