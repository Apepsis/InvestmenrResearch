# Ajuste responsivo de graficas

Este parche modifica solamente dos archivos:

```text
app/globals.css
app/components/TradingViewWidgets.tsx
```

## Como subirlo

1. Extrae el ZIP.
2. En GitHub abre la pestana **Code**.
3. Pulsa **Add file > Upload files**.
4. Arrastra la carpeta `app` extraida.
5. GitHub reemplazara los dos archivos existentes dentro de sus rutas.
6. Pulsa **Commit changes**.
7. Espera a que finalice **Publicar aplicacion en GitHub Pages** en **Actions**.
8. Recarga la pagina con `Ctrl + F5` para evitar que el navegador muestre el
   CSS anterior guardado en cache.

## Que cambia

- La grafica de precio crece hasta llenar la tarjeta y elimina el gran espacio
  vacio inferior.
- La grafica conserva una altura minima legible en laptop, tablet y celular.
- El bloque de noticias usa una altura definida y responsiva para evitar el
  gran espacio vacio debajo de las historias.
- Los `iframe` de TradingView ocupan siempre el 100% de su contenedor.

No elimina ni modifica Firebase, Alpaca, el portafolio, los workflows o las
reglas de Firestore.
