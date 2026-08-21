# V7 — Portada pública y acceso

Esta versión hace que el inicio de sesión deje de ser la pantalla principal.

## Qué cambia

- Portada pública de presentación del Research Lab.
- Encabezado simple con solamente **Iniciar sesión** y **Crear cuenta**.
- Acceso y registro en una pantalla independiente.
- Demostración pública accesible desde la portada.
- Nuevo personaje verde con sombrero como logotipo, favicon y marca del panel.
- Ilustración original para la portada y la pantalla de acceso.
- Diseño adaptable para computadora, tableta y teléfono.
- Se conserva la autenticación existente de Firebase con Google y correo/contraseña.

## Archivos principales modificados

- `app/components/InvestmentApp.tsx`
- `app/globals.css`
- `pages-entry/index.html`
- `public/manifest.webmanifest`
- `public/brand/*`

## Cómo subirlo a GitHub

1. Extrae el ZIP.
2. En la raíz de tu repositorio, elige **Add file → Upload files**.
3. Arrastra el contenido interno de la carpeta extraída, conservando las rutas.
4. Confirma que GitHub muestre los archivos modificados y los nuevos archivos de `public/brand`.
5. Escribe `feat: add public landing and redesigned authentication`.
6. Pulsa **Commit changes**.
7. Espera a que el flujo de GitHub Actions termine en verde.

## Firebase

No es necesario cambiar las variables de Firebase. Si están configuradas en GitHub Actions, la portada será pública y los botones de acceso abrirán Firebase Authentication. La demostración no exige iniciar sesión.

## Seguridad

El paquete no contiene claves privadas de Alpaca, contraseñas de Gmail ni secretos del Worker. Las credenciales deben continuar guardadas únicamente como Secrets de GitHub y Secrets de Cloudflare.
