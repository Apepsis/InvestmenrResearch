# Configurar Alpaca + Cloudflare sin exponer claves

Esta guia conecta precios recientes al panel, la vigilancia y el portafolio.
No permite comprar ni vender. Las claves de Alpaca se guardan como secretos en
Cloudflare y nunca llegan al navegador.

## Resultado final

- La aplicacion consulta el precio una vez por minuto mientras esta abierta.
- Al volver a una pestana que estaba en segundo plano, consulta de inmediato.
- Si Alpaca no responde, usa el ultimo precio disponible o el precio diario.
- El score profundo, los fundamentales, noticias clasificadas y macro se
  recalculan una vez al dia con GitHub Actions.

## Parte 1: obtener las dos claves gratuitas de Alpaca

1. Abre <https://app.alpaca.markets/signup> y crea una cuenta gratuita.
2. Puedes usar una cuenta **Paper**: no necesitas depositar dinero ni operar.
3. En el panel de Alpaca busca **API Keys**.
4. Pulsa **Generate New Keys**.
5. Guarda temporalmente estos dos valores en un lugar privado:
   - API Key ID
   - Secret Key

Alpaca solo vuelve a mostrar el secreto cuando lo generas. Si se pierde,
regenera las claves. No pegues ninguno de esos valores en GitHub, Firebase, la
aplicacion ni un mensaje de chat.

## Parte 2: crear el Worker gratuito en Cloudflare

1. Abre <https://dash.cloudflare.com/> y crea o inicia una cuenta.
2. Entra en **Workers & Pages**.
3. Pulsa **Create application**.
4. Elige la plantilla **Hello World** y desplegala con el nombre
   `investment-market-api`.
5. Abre el Worker creado y pulsa **Edit code**.
6. Borra el codigo de ejemplo.
7. Abre el archivo `cloudflare-worker/worker.js` de este proyecto, copia todo
   su contenido y pegalo en el editor de Cloudflare.
8. Pulsa **Deploy**.

## Parte 3: agregar los secretos

En Cloudflare abre tu Worker y ve a **Settings > Variables and Secrets**.
Pulsa **Add** y crea exactamente estas dos entradas con tipo **Secret**:

| Nombre | Valor |
| --- | --- |
| `ALPACA_API_KEY_ID` | API Key ID de Alpaca |
| `ALPACA_API_SECRET_KEY` | Secret Key de Alpaca |

Despues crea estas dos entradas con tipo **Text** o variable normal:

| Nombre | Valor |
| --- | --- |
| `ALLOWED_ORIGINS` | `https://apepsis.github.io` |
| `ALLOWED_SYMBOLS` | `UBER,AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,SPY` |

Pulsa **Deploy** para aplicar los cambios.

## Parte 4: comprobar que funciona

Cloudflare mostrara una direccion parecida a esta:

```text
https://investment-market-api.TU-SUBDOMINIO.workers.dev
```

Abre en el navegador esa direccion seguida de `/health`:

```text
https://investment-market-api.TU-SUBDOMINIO.workers.dev/health
```

Debe aparecer algo parecido a:

```json
{"ok":true,"service":"investment-market-api","alpacaConfigured":true}
```

Si `alpacaConfigured` aparece como `false`, los dos secretos no tienen el
nombre exacto o todavia no se desplegaron.

Tambien puedes probar:

```text
https://investment-market-api.TU-SUBDOMINIO.workers.dev/quotes?symbols=UBER
```

Debe devolver un precio dentro de `quotes.UBER.price`. Fuera del horario de
mercado sera el ultimo trade disponible.

## Parte 5: conectar el Worker a la aplicacion

1. Abre tu aplicacion publicada en GitHub Pages.
2. Inicia sesion.
3. Entra en **Ajustes**.
4. Busca **Precio interno · Alpaca**.
5. Pega la URL del Worker, sin `/health` ni `/quotes`.
6. Pulsa **Guardar y probar**.

Cuando todo este bien aparecera **Alpaca IEX activo**. La URL publica del
Worker no es un secreto; las claves privadas siguen protegidas en Cloudflare.
Si iniciaste sesion, la aplicacion guarda esa URL en tus preferencias de
Firebase. En modo demo se guarda solo en ese navegador.

## Parte 6: subir esta V3 a tu repositorio

1. Extrae el ZIP.
2. En GitHub abre la pestana **Code** de tu repositorio.
3. Pulsa **Add file > Upload files**.
4. Arrastra el contenido que esta dentro de la carpeta
   `Investment_Research_Agent`, no la carpeta exterior completa.
5. Acepta reemplazar los archivos con el mismo nombre y crea el commit.
6. Espera a que termine **Publicar aplicacion en GitHub Pages** en **Actions**.

La carpeta `.github` puede ocultarse en Windows. Como ya existe en tu
repositorio, para asegurar la actualizacion diaria entra en GitHub a:

```text
.github > workflows > update-market-data.yml
```

Pulsa el lapiz y confirma que la linea del horario sea:

```yaml
- cron: "20 22 * * *"
```

Eso ejecuta el analisis profundo todos los dias. No necesitas crear un workflow
de un minuto: el navegador consulta directamente al Worker cada 60 segundos.

## Si aparece un error

### `Origen no autorizado`

Confirma que `ALLOWED_ORIGINS` sea exactamente:

```text
https://apepsis.github.io
```

No agregues una barra final.

### `El Worker todavia no tiene configuradas las claves`

Revisa los nombres de los dos secretos y vuelve a pulsar **Deploy**.

### `No se pudieron obtener las cotizaciones`

Regenera las claves en Alpaca y reemplaza ambos secretos en Cloudflare. Tambien
confirma que estas usando claves de una cuenta habilitada para Market Data.

### El precio no cambia

Fuera del horario de mercado puede no haber un trade nuevo. Durante una sesion
abierta, la aplicacion vuelve a consultar cada minuto; eso no significa que el
mercado vaya a producir un precio diferente cada minuto.

