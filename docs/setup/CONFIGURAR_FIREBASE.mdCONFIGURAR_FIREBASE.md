# Pega aqui tu configuracion de Firebase

Tu objeto normalmente se ve asi:

```js
const firebaseConfig = {
  apiKey: "...",
  authDomain: "...",
  projectId: "...",
  storageBucket: "...",
  messagingSenderId: "...",
  appId: "..."
};
```

No pegues ese bloque dentro del codigo. En GitHub abre:

**Repositorio > Settings > Secrets and variables > Actions > Variables > New repository variable**

Crea estas variables una por una:

| Nombre en GitHub | Valor que debes copiar |
| --- | --- |
| `VITE_FIREBASE_API_KEY` | valor de `apiKey` |
| `VITE_FIREBASE_AUTH_DOMAIN` | valor de `authDomain` |
| `VITE_FIREBASE_PROJECT_ID` | valor de `projectId` |
| `VITE_FIREBASE_STORAGE_BUCKET` | valor de `storageBucket` |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | valor de `messagingSenderId` |
| `VITE_FIREBASE_APP_ID` | valor de `appId` |

Despues:

1. En Firebase, habilita **Authentication > Email/Password** y **Google**.
2. Crea **Firestore Database**.
3. Copia `firestore.rules` en la pestana **Rules** de Firestore y publica.
4. En GitHub, ve a **Settings > Pages** y selecciona **GitHub Actions**.
5. Ejecuta los dos workflows desde la pestana **Actions**.

Para probar localmente, copia `.env.example` como `.env` y coloca los mismos
seis valores. El archivo `.env` esta excluido de Git para evitar subirlo por
accidente.
