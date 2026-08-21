# Activar las variables macro automáticas

La aplicación obtiene cinco series oficiales de FRED: tasa FED, inflación,
desempleo, índice dólar y petróleo WTI. La clave es gratuita y queda protegida
como secreto de GitHub; nunca se incorpora al sitio público.

## Configuración única

1. Inicia sesión o crea una cuenta en `https://fredaccount.stlouisfed.org/`.
2. Solicita una API key en `https://fredaccount.stlouisfed.org/apikeys`.
3. En el repositorio abre **Settings**.
4. Entra en **Secrets and variables > Actions**.
5. Abre la pestaña **Secrets** y pulsa **New repository secret**.
6. Usa exactamente este nombre: `FRED_API_KEY`.
7. Pega la clave como valor y guarda.
8. Abre **Actions > Actualizar datos e investigacion > Run workflow**.

## Automatización

El workflow se ejecuta cada día a las 22:20 UTC (17:20 en Perú). En cada
ejecución actualiza mercado, macro, backtest, riesgo, estudios de noticias y el
manifiesto de auditoría. Si FRED falla temporalmente, conserva el último valor
previamente verificado con su fecha y lo marca como atrasado; nunca inventa un
valor.

No publiques la clave en `.env`, el README, capturas ni archivos del
repositorio.
