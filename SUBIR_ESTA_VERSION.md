# Subir esta versión a GitHub

Esta entrega agrega el tercer ciclo automático y renueva la interfaz sin
cambiar la metodología oficial del modelo.

## Qué queda automatizado

| Proceso | Cadencia | Dónde corre |
| --- | --- | --- |
| Precio visible en panel y portafolio | 1 minuto con la pestaña abierta | Navegador + Cloudflare + Alpaca |
| Condiciones de alerta y correo | Cada 5 minutos | GitHub Actions |
| Titulares nuevos y señales rápidas | Cada 20 minutos | GitHub Actions |
| Fundamentales, macro, score, backtest y Research Lab | Una vez al día | GitHub Actions |

## Cómo subirla

1. Sube **el contenido de esta carpeta** a la raíz de `main`; no subas la
   carpeta contenedora como una subcarpeta adicional.
2. Confirma que aparezca
   `.github/workflows/refresh-fast-signals.yml`. La carpeta `.github` es oculta
   en Windows, pero GitHub sí la muestra después del commit.
3. Conserva los JSON reales que ya tengas en `public/data`. El único archivo
   nuevo obligatorio allí es `fast_signals.json`; el workflow reemplazará su
   muestra inicial por datos reales.
4. Haz el commit.
5. Ve a **Actions > Actualizar noticias y senales rapidas > Run workflow** y
   ejecútalo una vez.
6. Cuando termine en verde, ejecuta **Publicar aplicacion en GitHub Pages**.

Después de la primera ejecución manual, el workflow de noticias quedará
programado automáticamente. No hace falta dejar la página abierta.

## Universo opcional para el radar

De forma predeterminada se vigilan los activos presentes en `market.json`. Si
quieres limitar consumo, crea en GitHub:

`Settings > Secrets and variables > Actions > Variables > New variable`

- Nombre: `FAST_NEWS_SYMBOLS`
- Valor de ejemplo: `UBER,AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,SPY`

Esta variable no es un secreto. Las claves de Alpaca siguen únicamente en
Cloudflare y las credenciales de Gmail siguen en GitHub Secrets.

## Diseño nuevo

- Barra superior con el estado real de los cuatro ciclos.
- Radar animado de eventos y tarjetas de señales rápidas.
- Entrada progresiva de páginas y paneles.
- Curvas de backtest dibujadas al cargar.
- Barras y score con animación.
- Fondo técnico, profundidad, luces de estado y mejores estados hover.
- Modo reducido automático para usuarios con `prefers-reduced-motion`.

Las señales rápidas son informativas: no ejecutan compras ni cambian el score
oficial hasta la siguiente investigación profunda diaria.
