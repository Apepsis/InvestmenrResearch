# V5 · Predicciones verificables, riesgo y alertas

## Qué cambia

La V5 no reemplaza el backtest ni recalcula el pasado. Agrega una capa operativa
que publica predicciones nuevas y conserva su evidencia original.

1. Predicciones para 5, 20 y 60 sesiones.
2. Ledger append-only con precio, probabilidad, incertidumbre, versión y hash.
3. Evaluación automática cuando cada horizonte madura.
4. Challenger con máximo 20% por posición, objetivo de volatilidad, proxy de CVaR, filtro SMA 200 y efectivo.
5. Champion–challenger con promoción después de tres ejecuciones calificadas.
6. Monitoreo de cobertura, antigüedad, drift y desempeño realizado.
7. Universo de 32 acciones más SPY.
8. Alertas Gmail opcionales, deduplicadas y sin claves en el navegador.

## Archivos nuevos

```text
scripts/v5_core.py
scripts/generate_live_predictions.py
scripts/update_model_registry.py
scripts/monitor_model.py
scripts/send_alerts.py

tests/test_v5_predictions.py
tests/test_alerts.py

app/components/PredictionV5Lab.tsx

public/data/live_predictions.json          # creado por Actions
public/data/prediction_ledger.json         # creado y conservado por Actions
public/data/model_registry.json            # creado por Actions
public/data/model_monitoring.json          # creado por Actions
public/data/alerts.json                     # creado por Actions
```

## Cómo instalar

Sube el contenido completo del ZIP a la raíz del repositorio y confirma el
commit. No borres `public/data/*.json` que ya existan: el ledger necesita
conservar sus versiones futuras.

Después:

1. Configura Gmail siguiendo `CONFIGURAR_ALERTAS_GMAIL.md` si quieres correos.
2. Ejecuta manualmente **Actualizar datos e investigación** una vez.
3. Espera el despliegue **Publicar aplicación en GitHub Pages**.
4. Abre **Research Lab** y confirma que aparecen tres tarjetas para el ticker seleccionado.

La primera ejecución mostrará predicciones activas, pero todavía no resultados.
Las de 5 sesiones serán las primeras en madurar. Eso es evidencia metodológica,
no una falla.

## Archivos que nunca se suben

- Contraseña normal de Gmail.
- Contraseña de aplicación.
- Claves privadas de Alpaca.
- Credenciales de servicio de Firebase.

Las claves se guardan en GitHub Actions o Cloudflare, nunca en GitHub Pages.
