# Seguridad

## Nunca subas al repositorio

- Archivos de cuentas de servicio de Firebase.
- Claves privadas, frases semilla o tokens de brokers.
- Contrasenas o datos bancarios.
- Archivos `.env` reales.

La configuracion web de Firebase identifica la aplicacion, pero las reglas de
Firestore controlan el acceso a los documentos. Mantiene `firestore.rules`
cerrado por UID y revisa las reglas despues de cada cambio.

Si expones una credencial privada, revocala en el proveedor; borrar solo el
ultimo commit no la elimina del historial del repositorio.
