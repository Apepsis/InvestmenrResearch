# Actualizar a V8.1: Worker, historial e IA gobernada

## 1. Subir los archivos

Sube el contenido del ZIP completo a la raíz del repositorio y permite que
GitHub reemplace los archivos existentes. No borres `scripts/`, `models/` ni
los ledgers de `public/data/`.

## 2. Volver a desplegar el Worker

El código que debe ejecutar Cloudflare está en:

```text
cloudflare-worker/worker.js
```

La V8.1 acepta los 33 activos, normaliza el origen de GitHub Pages y devuelve
diagnóstico adicional en `/health`. Si se usa Wrangler:

```bash
cd cloudflare-worker
npx wrangler deploy
```

En Cloudflare conserva estos secretos:

```text
ALPACA_API_KEY_ID
ALPACA_API_SECRET_KEY
```

Y esta variable normal:

```text
ALLOWED_ORIGINS=https://apepsis.github.io
```

Después de cualquier cambio pulsa **Deploy**. Una respuesta sana debe incluir
`alpacaConfigured: true` y `allowedSymbolCount: 33`.

## 3. Configurar GitHub Pages

En `Settings > Secrets and variables > Actions > Variables` crea o corrige:

```text
VITE_MARKET_API_URL=https://investment-market-api.TU-CUENTA.workers.dev
```

Usa solo la URL base: no agregues `/health`, `/quotes`, comillas ni espacios.
Ejecuta manualmente **Publicar aplicación en GitHub Pages** después del cambio.

La aplicación también permite corregir la URL en **Ajustes**. La V8.1 limpia
automáticamente `/health` o `/quotes` si se pegaron por accidente y muestra el
motivo exacto cuando falla la prueba.

## 4. Crear el historial de mediciones

Ejecuta una vez **Actualizar datos e investigación**. El pipeline conservará el
`backtest.json` existente y creará:

```text
public/data/backtest_history.json
```

Desde entonces, cada resultado matemáticamente distinto se archiva por SHA-256
y aparece en el selector **Medición** del Research Lab. Repetir exactamente el
mismo cálculo no crea copias falsas.

## 5. Interpretar la red neuronal

La red V8 ya está implementada cuando `neural_lab.json` aparece en modo `live`.
`Shadow challenger` significa que aprendió y fue evaluada, pero todavía no
obtuvo evidencia suficiente para reemplazar al Champion. Un Brier ligeramente
menor no basta: también debe superar controles de calibración, estabilidad por
horizonte y bloques temporales.

No se debe modificar el backtest para que todas las líneas superen a SPY. Una
estrategia de control de riesgo puede ganar menos y, aun así, ser útil si reduce
drawdown. Mostrar resultados negativos o mixtos forma parte de la auditoría.

## Seguridad

Si una clave de Alpaca apareció en una captura, repositorio, chat o video,
revócala y genera un par nuevo. Las claves nuevas deben existir únicamente como
secretos de Cloudflare; nunca dentro del código o de GitHub Pages.
