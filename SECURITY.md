# Seguridad

## Nunca subas al repositorio

- Archivos de cuentas de servicio de Firebase.
- Claves privadas, frases semilla o tokens de brokers.
- Contrasenas o datos bancarios.
- Archivos `.env` reales.
- Contraseñas de aplicaciones de Gmail y correos configurados para alertas.

La configuracion web de Firebase identifica la aplicacion, pero las reglas de
Firestore controlan el acceso a los documentos. Mantiene `firestore.rules`
cerrado por UID y revisa las reglas despues de cada cambio.

Si expones una credencial privada, revocala en el proveedor; borrar solo el
ultimo commit no la elimina del historial del repositorio.

## Separación de datos

Los artefactos de `public/data/` son públicos. Solo contienen investigación de
mercado agregada. Las posiciones, vigilancia, diario, correo y UID permanecen
en Firebase y nunca deben copiarse al pipeline o al manifiesto público.

`scripts/validate_market_data.py` rechaza marcadores de posibles credenciales,
pero esa validación no reemplaza la revisión de secretos de GitHub.

Las alertas usan `ALERT_EMAIL_FROM`, `ALERT_EMAIL_TO` y
`GMAIL_APP_PASSWORD` únicamente dentro de GitHub Actions. `alerts.json` publica
solo el tipo de alerta y el estado de entrega. Una falla de Gmail no bloquea ni
borra los artefactos cuantitativos.
