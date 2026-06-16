# =============================================================================
# VERIFICACIÓN MODELO FAY-HERRIOT EN R
# Fuente: fay_herriot.csv
# Objetivo: Corroborar la implementación Python en fay_herriot.py
# Paquete: sae (eblupFH)
# =============================================================================
# Dominio: PER + MES + DEPARTAMENTO + MUNICIPIO
# Variable objetivo: TASA_DESEMPLEO_PCT
# Varianza directa: SE_BOOTSTRAP_PCT^2
# Covariables: COB_ENER_RURAL, TASA_TRAN_EDU_SUP  (mismo set que Python)
# Método: REML
# =============================================================================

# Instalar paquete si no está disponible
if (!requireNamespace("sae", quietly = TRUE)) install.packages("sae")

library(sae)

# -----------------------------------------------------------------------------
# 1. CARGA DE DATOS
# -----------------------------------------------------------------------------
ruta_csv <- file.path(dirname(rstudioapi::getSourceEditorContext()$path), "fay_herriot.csv")

# Si no se corre desde RStudio, usar ruta relativa o absoluta:
# ruta_csv <- "code/modelo/fay_herriot.csv"

df <- read.csv(ruta_csv, stringsAsFactors = FALSE, encoding = "UTF-8")

df$DOMINIO <- paste(df$PER, df$MES, df$DEPARTAMENTO, df$MUNICIPIO, sep = "_")

cat("Dominios (municipios):", nrow(df), "\n")
cat("Columnas disponibles: ", paste(names(df), collapse = ", "), "\n\n")

# -----------------------------------------------------------------------------
# 2. DEFINICIÓN DE VARIABLES
# -----------------------------------------------------------------------------
# Varianza de muestreo conocida (Di = SE^2)
df$Di <- df$SE_BOOTSTRAP_PCT^2

# -----------------------------------------------------------------------------
# 3. MODELO FAY-HERRIOT CON eblupFH + mseFH (sae)
# -----------------------------------------------------------------------------
# eblupFH: estima A por REML, calcula beta GLS y devuelve el vector EBLUP.
# mseFH:   calcula el MSE (Prasad-Rao) dado el mismo modelo.
# Nota: eblupFH$eblup es un vector, NO una lista; acceder directo sin $eblup.

formula_fh <- TASA_DESEMPLEO_PCT ~ COB_ENER_RURAL + TASA_TRAN_EDU_SUP

fh_modelo <- eblupFH(
  formula   = formula_fh,
  vardir    = Di,
  method    = "REML",
  MAXITER   = 500,
  PRECISION = 1e-6,
  data      = df
)

fh_mse <- mseFH(
  formula   = formula_fh,
  vardir    = Di,
  method    = "REML",
  MAXITER   = 500,
  PRECISION = 1e-6,
  data      = df
)

# -----------------------------------------------------------------------------
# 4. PARÁMETROS DEL MODELO
# -----------------------------------------------------------------------------
A_hat <- fh_modelo$fit$refvar          # Varianza de efectos aleatorios estimada

cat(strrep("=", 55), "\n")
cat("ESTIMACIÓN DE PARÁMETROS DEL MODELO FAY-HERRIOT\n")
cat(strrep("=", 55), "\n\n")
cat(sprintf("Varianza de efectos aleatorios (Â):   %.6f\n", A_hat))
cat(sprintf("Desv. estándar de efectos aleatorios: %.6f\n\n", sqrt(A_hat)))

# Coeficientes
beta_hat <- fh_modelo$fit$estcoef$beta
se_beta  <- fh_modelo$fit$estcoef$std.error
z_vals   <- fh_modelo$fit$estcoef$tvalue
p_vals   <- 2 * (1 - pnorm(abs(z_vals)))

param_names <- c("Intercepto", "COB_ENER_RURAL", "TASA_TRAN_EDU_SUP")

cat("ESTIMACIÓN DE COEFICIENTES:\n")
cat(sprintf("%-22s %10s %10s %8s %10s\n", "Parámetro", "Coef", "SE", "z", "p-valor"))
cat(strrep("-", 62), "\n")
for (i in seq_along(param_names)) {
  signif_str <- ifelse(p_vals[i] < 0.01, "***",
                ifelse(p_vals[i] < 0.05, "** ",
                ifelse(p_vals[i] < 0.10, "*  ", "   ")))
  cat(sprintf("%-22s %10.4f %10.4f %8.3f %10.4f %s\n",
              param_names[i], beta_hat[i], se_beta[i], z_vals[i], p_vals[i], signif_str))
}
cat("Signif: *** p<0.01  ** p<0.05  * p<0.10\n")

# -----------------------------------------------------------------------------
# 5. RESULTADOS EBLUP Y MSE
# -----------------------------------------------------------------------------
# eblupFH$eblup es un vector directo; mseFH$mse es también un vector directo
eblup     <- fh_modelo$eblup
mse_eblup <- fh_mse$mse

# Gamma (shrinkage): A / (A + Di)
gamma_i <- A_hat / (A_hat + df$Di)

# Predictor sintético: Xβ̂
X <- model.matrix(~ COB_ENER_RURAL + TASA_TRAN_EDU_SUP, data = df)
mu_hat <- as.vector(X %*% beta_hat)

rmse_eblup <- sqrt(mse_eblup)
cv_eblup   <- 100 * rmse_eblup / abs(eblup)
mejora_cv  <- df$CV_PORCENTAJE - cv_eblup

resultados <- data.frame(
  DOMINIO          = df$DOMINIO,
  DEPARTAMENTO     = df$DEPARTAMENTO,
  MUNICIPIO        = df$MUNICIPIO,
  TASA_DIRECTA     = df$TASA_DESEMPLEO_PCT,
  SE_DIRECTO       = df$SE_BOOTSTRAP_PCT,
  CV_DIRECTO_PCT   = df$CV_PORCENTAJE,
  VARIANZA_DIRECTA = df$Di,
  GAMMA_SHRINKAGE  = round(gamma_i, 4),
  PRED_SINTETICO   = round(mu_hat, 4),
  EBLUP            = round(eblup, 4),
  MSE_EBLUP        = round(mse_eblup, 6),
  RMSE_EBLUP       = round(rmse_eblup, 4),
  CV_EBLUP_PCT     = round(cv_eblup, 2),
  MEJORA_CV_PCT    = round(mejora_cv, 2)
)

cat("\n", strrep("=", 55), "\n", sep = "")
cat("RESULTADOS EBLUP POR DOMINIO\n")
cat(strrep("=", 55), "\n")
print(resultados[, c("MUNICIPIO", "TASA_DIRECTA", "EBLUP",
                      "CV_DIRECTO_PCT", "CV_EBLUP_PCT",
                      "GAMMA_SHRINKAGE", "MEJORA_CV_PCT")],
      row.names = FALSE, digits = 4)

# -----------------------------------------------------------------------------
# 6. DIAGNÓSTICOS DEL MODELO
# -----------------------------------------------------------------------------
cat("\n", strrep("=", 55), "\n", sep = "")
cat("DIAGNÓSTICOS DEL MODELO\n")
cat(strrep("=", 55), "\n")

residuales <- (df$TASA_DESEMPLEO_PCT - mu_hat) / sqrt(df$Di + A_hat)

cat(sprintf("\nResiduales estandarizados:\n"))
cat(sprintf("  Media:      %.4f  (esperado ≈ 0)\n", mean(residuales)))
cat(sprintf("  Desv. std:  %.4f  (esperado ≈ 1)\n", sd(residuales)))

sw_test <- shapiro.test(residuales)
cat(sprintf("\nTest Shapiro-Wilk (normalidad de residuos):\n"))
cat(sprintf("  W = %.4f,  p-valor = %.4f\n", sw_test$statistic, sw_test$p.value))
if (sw_test$p.value > 0.05) {
  cat("  -> No se rechaza normalidad (p > 0.05) ✓\n")
} else {
  cat("  -> Se rechaza normalidad (p <= 0.05) — revisar supuestos ✗\n")
}

Y <- df$TASA_DESEMPLEO_PCT
ss_tot <- sum((Y - mean(Y))^2)
ss_res <- sum((Y - mu_hat)^2)
r2     <- 1 - ss_res / ss_tot
cat(sprintf("\nR² del predictor sintético (Xβ̂): %.4f\n", r2))

cat(sprintf("\nReducción media del CV:           %.2f puntos porcentuales\n",
            mean(mejora_cv)))
cat("  (positivo = el EBLUP mejora la precisión)\n")

cat(sprintf("\nPeso de shrinkage promedio (γ̄):  %.4f\n", mean(gamma_i)))
cat("  (cercano a 1 -> el modelo confía más en el modelo que en la directa)\n")

# -----------------------------------------------------------------------------
# 7. COMPARACIÓN DIRECTA CON PYTHON (valores clave)
# -----------------------------------------------------------------------------
cat("\n", strrep("=", 55), "\n", sep = "")
cat("VALORES CLAVE PARA COMPARAR CON PYTHON\n")
cat(strrep("=", 55), "\n")
cat("Comparar estos valores con la salida del script fay_herriot.py:\n\n")
cat(sprintf("  Â (varianza efectos aleatorios): %.6f\n", A_hat))
cat(sprintf("  β Intercepto:                   %.4f\n", beta_hat[1]))
cat(sprintf("  β COB_ENER_RURAL:               %.4f\n", beta_hat[2]))
cat(sprintf("  β TASA_TRAN_EDU_SUP:            %.4f\n", beta_hat[3]))
cat(sprintf("  γ̄ promedio:                     %.4f\n", mean(gamma_i)))
cat(sprintf("  R² predictor sintético:          %.4f\n", r2))
cat(sprintf("  EBLUP PASTO:                    %.4f\n",
            resultados$EBLUP[resultados$MUNICIPIO == "PASTO"]))
cat(sprintf("  CV_EBLUP PASTO:                 %.2f%%\n",
            resultados$CV_EBLUP_PCT[resultados$MUNICIPIO == "PASTO"]))
