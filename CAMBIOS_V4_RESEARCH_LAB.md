# Actualización V4 — Research Lab auditable

## Qué se agregó

- Research Lab con backtest walk-forward contra SPY.
- Cuatro modelos bajo el mismo protocolo.
- Explicación waterfall del score y rango de incertidumbre.
- Event studies de noticias a 1, 5 y 20 sesiones.
- VaR, CVaR, beta, correlaciones y pruebas de estrés del portafolio.
- Tabla de procedencia de datos.
- Run ID, versión, commit y hashes SHA-256.
- Página del proceso de construcción y experimentos fallidos.
- Nueve pruebas automáticas.
- Workflows actualizados para Node 24.

## Cómo subir esta versión

No elimines Firebase, Firestore, Cloudflare ni tus variables de GitHub.

1. Extrae el ZIP.
2. Abre tu repositorio en GitHub y entra a **Code**.
3. Presiona **Add file > Upload files**.
4. Arrastra **todo el contenido extraído**, no el ZIP y no la carpeta exterior.
5. Confirma que también se cargó la carpeta `.github`.
6. Escribe `feat: agregar Research Lab V4` y confirma el commit.
7. Abre **Actions**.
8. Ejecuta manualmente **Actualizar datos e investigacion**.
9. Espera el check verde. Ese workflow generará los resultados reales y hará
   un nuevo commit automáticamente.
10. Espera después **Publicar aplicacion en GitHub Pages** y recarga con
    `Ctrl + F5`.

## Primera ejecución

Antes de la primera ejecución, las nuevas secciones muestran una estructura de
demostración claramente identificada. Después del workflow deben aparecer:

- periodo real del backtest;
- métricas reales;
- curvas de capital;
- correlaciones;
- event studies disponibles;
- manifiesto con hash y cobertura.

Si una variable macro falla, la interfaz mostrará `No disponible` o reutilizará
el último valor verificado con su fecha. Nunca debe mostrar un número inventado.
