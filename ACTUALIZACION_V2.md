# Actualizacion V2: grafica y noticias dinamicas

## Archivos que cambian

Reemplaza o crea exactamente estas rutas en el repositorio:

1. `app/components/InvestmentApp.tsx` — reemplazar.
2. `app/components/TradingViewWidgets.tsx` — crear.
3. `app/globals.css` — reemplazar.
4. `.github/workflows/update-market-data.yml` — reemplazar si aun conserva el
   horario antiguo o no vuelve a ejecutar el despliegue.
5. `README.md` — reemplazo opcional, solo documentacion.

## Que agrega

- Grafica dinamica por ticker con periodos e indicadores.
- Noticias externas filtradas por el activo seleccionado.
- Cambio automatico de simbolo al seleccionar UBER, AAPL, MSFT, NVDA, AMZN,
  GOOGL, META, TSLA o SPY.
- Avisos que separan la informacion visual reciente del score diario.
- Publicacion automatica despues de actualizar `market.json`.

## Publicar

1. Sube los archivos conservando sus carpetas.
2. Haz el commit en la rama `main`.
3. Abre **Actions > Publicar aplicacion en GitHub Pages**.
4. Espera el visto verde.
5. Abre la pagina y presiona `Ctrl + F5`.

No se necesita una nueva variable de Firebase ni una clave de TradingView.

## Seguridad

No agregues claves de Alpaca, brokers o cuentas de servicio como variables
`VITE_*`: todo valor con ese prefijo queda incorporado en los archivos visibles
del navegador. Una futura integracion en tiempo real debe proteger esas claves
en un servicio de servidor, como Cloudflare Workers.
