# Ajuste exclusivo del bloque de noticias

Este parche reemplaza solamente:

```text
app/globals.css
```

No cambia la grafica de precios, Firebase, Alpaca, el portafolio ni los
workflows.

## Subir a GitHub

1. Extrae el ZIP.
2. En GitHub abre **Code > Add file > Upload files**.
3. Arrastra la carpeta `app` extraida.
4. Pulsa **Commit changes**.
5. Espera a que termine **Publicar aplicacion en GitHub Pages**.
6. Recarga la pagina con `Ctrl + F5`.

El bloque de Noticias dinamicas tendra una altura de 425 px en escritorio, 410
px en tablet y 380 px en celular. Al usar una altura definida, el contenido de
TradingView puede ocupar correctamente el contenedor y desaparece el gran
espacio oscuro inferior.

