# Worker de precios Alpaca

Este Worker protege las credenciales privadas de Alpaca y expone unicamente
las cotizaciones permitidas para la aplicacion de GitHub Pages.

## Rutas

- `/health` confirma que el servicio esta disponible y si las claves existen.
- `/quotes?symbols=UBER,AAPL` devuelve el ultimo precio del feed IEX.

## Secretos obligatorios

Configura estos dos secretos en Cloudflare; nunca los escribas en GitHub:

- `ALPACA_API_KEY_ID`
- `ALPACA_API_SECRET_KEY`

## Variables normales

`wrangler.jsonc` limita las solicitudes al origen de GitHub Pages y a los
simbolos utilizados por la aplicacion. Si cambia el usuario de GitHub, edita
`ALLOWED_ORIGINS`.

## Despliegue con Wrangler

```bash
npx wrangler@latest login
npx wrangler@latest secret put ALPACA_API_KEY_ID
npx wrangler@latest secret put ALPACA_API_SECRET_KEY
npx wrangler@latest deploy
```

Tambien se puede crear un Worker desde el panel de Cloudflare, pegar el
contenido de `worker.js` y agregar los secretos desde **Settings > Variables
and Secrets**.

La respuesta se conserva durante 45 segundos para evitar solicitudes
duplicadas. El navegador consulta nuevamente cada minuto mientras la pagina
esta abierta.
