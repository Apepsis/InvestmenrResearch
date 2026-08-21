# Configurar alertas gratuitas por Gmail

La V5 puede enviar un resumen diario y, opcionalmente, alertas intradía cuando
detecta una anomalía crítica, una señal de riesgo o una oportunidad que supera
umbrales conservadores. El correo no ejecuta operaciones y no contiene secretos.

## 1. Preparar Gmail

1. En la cuenta que enviará los correos, activa la **Verificación en dos pasos**.
2. Abre la página oficial de [Contraseñas de aplicaciones de Google](https://support.google.com/accounts/answer/185833?hl=es).
3. Crea una contraseña para `Investment Research Agent`.
4. Copia los 16 caracteres. Esta contraseña no es la contraseña normal de la cuenta.

Google puede ocultar esta opción en cuentas administradas por una escuela o
empresa, cuentas con Protección Avanzada o cuentas cuya verificación en dos
pasos usa únicamente llaves de seguridad. En ese caso usa una cuenta personal
dedicada o deja el correo desactivado; el pipeline seguirá funcionando.

## 2. Guardar secretos en GitHub

En el repositorio abre **Settings → Secrets and variables → Actions**.

En **Secrets**, crea exactamente:

| Nombre | Valor |
| --- | --- |
| `ALERT_EMAIL_FROM` | Cuenta Gmail que enviará el resumen |
| `ALERT_EMAIL_TO` | Correo receptor; varios se separan con comas |
| `GMAIL_APP_PASSWORD` | Contraseña de aplicación de 16 caracteres |

En **Variables**, crea:

| Nombre | Valor |
| --- | --- |
| `ALERTS_ENABLED` | `true` |

Nunca añadas estos valores a `.env`, al código, a Firebase ni a un archivo
público. GitHub Actions los entrega solamente al proceso de correo.

## 3. Probar

1. Abre **Actions → Actualizar datos e investigación**.
2. Pulsa **Run workflow**.
3. Comprueba el paso `Ejecutar pipeline reproducible`.
4. Abre `public/data/alerts.json` y revisa `deliveryStatus`:

- `sent`: se envió un resumen.
- `no-new-alerts`: funciona, pero no existe una alerta nueva fuera del cooldown.
- `disabled`: `ALERTS_ENABLED` no es `true`.
- `misconfigured`: falta al menos un secreto.
- `failed`: Gmail rechazó temporalmente el envío; el pipeline no pierde los resultados.

No siempre llegará un correo durante la prueba: si ningún umbral se cumple, el
comportamiento correcto es no enviar spam.

## 4. Activar el monitor intradía

Sube `.github/workflows/intraday-alerts.yml` y
`scripts/monitor_intraday_alerts.py`. El workflow consulta el Worker de Alpaca
cada cinco minutos de lunes a viernes durante la franja que cubre el horario
regular de Estados Unidos. Utiliza la variable existente
`VITE_MARKET_API_URL`; no necesita copiar las claves de Alpaca a GitHub.

El monitor no recalcula el backtest ni reentrena el modelo. Solo combina una
cotización IEX reciente con la última predicción diaria publicada. Si no hay
alerta, no cambia archivos ni genera commits. Si envía un correo, registra el
evento y su cooldown en `public/data/alerts.json`.

Reglas intradía iniciales:

- SPY cae 3% o más respecto de la referencia diaria.
- Una acción cae 6% o sube 8% o más.
- Una acción cae 3.5% o más y las probabilidades auditadas de 20 y 60 sesiones
  continúan fuertes: se marca como dislocación para investigar.
- Una acción cae 4% o más y el modelo de corto plazo es débil: se marca riesgo
  de tesis.

Los cooldowns intradía son de 4 a 24 horas. GitHub Actions puede retrasar una
ejecución, por lo que este monitor es de respuesta rápida, no tiempo real al
segundo.

## Reglas de alerta publicadas

- **Integridad crítica:** cobertura menor a 80%, datos con más de 72 horas o drift de 3σ.
- **Oportunidad de investigación:** probabilidad ≥66% a 20 sesiones, ≥60% a 60 sesiones y límite inferior de la banda de 20 sesiones ≥50%.
- **Riesgo:** probabilidad ≤25% a 5 sesiones y ≤35% a 20 sesiones.
- **Promoción de modelo:** el challenger se vuelve champion después de tres ejecuciones calificadas.

Los cooldowns diarios son 24–72 horas según la alerta. La variante intradía
reduce la latencia de precios a aproximadamente cinco minutos, sujeta a las
colas de GitHub Actions y a la cobertura IEX gratuita de Alpaca.
